"""C1 Pricing Agent — Azure Calculator 估價（ADR-C1-10）。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    tool,
)

from cost.azure_calculator_runner import (
    AzureCalculatorError,
    AzureCalculatorResult,
    run_azure_calculator_estimate,
)
from cost.config import CALCULATOR_AZURE_PRODUCTS, CALCULATOR_GCP_PRODUCTS
from cost.diagram_extractor import extract_priceable_cells
from cost.gcp_calculator_runner import GcpCalculatorError, run_gcp_calculator_estimate
from cost.pricing_client import PriceHit, PriceMiss, PriceUnsupported, fetch_hourly
from cost.sku_mapper import map_cell
from cost.sku_ai_resolver import infer_unmapped_cells, resolve_cell
from services.llm_limits import agent_sdk_env
from services.llm_provider import (
    auth_error_message,
    configure_provider_env,
    get_model_name,
    llm_auth_ready,
)

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "cloud360-cost"
LIST_TOOL = "list_mapped_resources"
FETCH_TOOL = "fetch_official_hourly"
AZURE_CALC_TOOL = "run_azure_calculator_estimate"
LIST_TOOL_FQN = f"mcp__{MCP_SERVER_NAME}__{LIST_TOOL}"
FETCH_TOOL_FQN = f"mcp__{MCP_SERVER_NAME}__{FETCH_TOOL}"
AZURE_CALC_TOOL_FQN = f"mcp__{MCP_SERVER_NAME}__{AZURE_CALC_TOOL}"

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "cost_pricing_agent_system.md"

_run_context: dict[str, Any] = {}
_last_estimate: AzureCalculatorResult | None = None


@dataclass
class CostEstimateResult:
    total_usd: Decimal | None
    pricing_source: str
    pricing_as_of: datetime | None
    agent_assumptions: list[str] = field(default_factory=list)
    line_items: list[dict[str, Any]] = field(default_factory=list)
    calculator_lines: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def pricing_agent_enabled() -> bool:
    return os.environ.get("COST_PRICING_AGENT", "").strip() == "1"


def skip_llm_planner() -> bool:
    """Stub／無 LLM 時用確定性 line_items 規劃。"""
    if os.environ.get("COST_PRICING_AGENT_SKIP_LLM", "").strip() == "1":
        return True
    if os.environ.get("COST_AZURE_CALCULATOR_STUB", "").strip() == "1":
        return True
    if os.environ.get("COST_GCP_CALCULATOR_STUB", "").strip() == "1":
        return True
    return False


def load_system_prompt() -> str:
    if PROMPT_PATH.is_file():
        return PROMPT_PATH.read_text(encoding="utf-8").strip()
    return (
        "你是 Cloud-360 FinOps 估價助理。依架構圖列出 Azure 資源，"
        "必要時用 fetch_official_hourly 對規格，最後必須呼叫 run_azure_calculator_estimate "
        "取得 Azure Pricing Calculator 的 Estimated monthly cost 作為整圖總價。"
    )


def plan_azure_line_items(
    xml_data: str, hours_by_mxcell: dict[str, int]
) -> tuple[list[dict[str, Any]], list[str]]:
    """確定性：diagram → calculator map_key + quantity（Agent tool 與 skip-LLM 共用）。"""
    items: list[dict[str, Any]] = []
    mapping_notes: list[str] = []
    cells = extract_priceable_cells(xml_data)
    llm_batch = infer_unmapped_cells(cells, cloud_hint="azure")

    for cell in cells:
        mapped, note = resolve_cell(
            cell.label_plain,
            cell.style,
            cloud_hint="azure",
            mxcell_id=cell.mxcell_id,
            llm_batch=llm_batch,
        )
        if note:
            mapping_notes.append(note)
        if mapped.kind != "unique" or not mapped.candidate:
            continue
        cand = mapped.candidate
        if cand.cloud != "azure":
            continue
        if cand.sku not in CALCULATOR_AZURE_PRODUCTS:
            continue
        hours = hours_by_mxcell.get(cell.mxcell_id, 24)
        default_qty = int(CALCULATOR_AZURE_PRODUCTS[cand.sku].get("default_quantity") or 1)
        unit = CALCULATOR_AZURE_PRODUCTS[cand.sku].get("quantity_unit", "")
        qty = _quantity_for_unit(unit, hours, default_qty)
        items.append(
            {
                "map_key": cand.sku,
                "quantity": qty,
                "mxcell_id": cell.mxcell_id,
                "label": cell.label_plain,
            }
        )
    return items, mapping_notes


def _quantity_for_unit(
    unit: str,
    hours: int,
    default_qty: int,
) -> int:
    if unit in (
        "vm_instance",
        "node",
        "gateway",
        "firewall",
        "vault",
        "account",
        "database",
        "workspace",
        "service",
    ):
        return max(1, (hours + 23) // 24)
    return default_qty


def plan_gcp_line_items(
    xml_data: str, hours_by_mxcell: dict[str, int]
) -> tuple[list[dict[str, Any]], list[str]]:
    """確定性：GCP diagram → calculator map_key + quantity。"""
    items: list[dict[str, Any]] = []
    mapping_notes: list[str] = []
    cells = extract_priceable_cells(xml_data)
    llm_batch = infer_unmapped_cells(cells, cloud_hint="gcp")

    for cell in cells:
        mapped, note = resolve_cell(
            cell.label_plain,
            cell.style,
            cloud_hint="gcp",
            mxcell_id=cell.mxcell_id,
            llm_batch=llm_batch,
        )
        if note:
            mapping_notes.append(note)
        if mapped.kind != "unique" or not mapped.candidate:
            continue
        cand = mapped.candidate
        if cand.cloud != "gcp":
            continue
        if cand.sku not in CALCULATOR_GCP_PRODUCTS:
            continue
        hours = hours_by_mxcell.get(cell.mxcell_id, 24)
        default_qty = int(CALCULATOR_GCP_PRODUCTS[cand.sku].get("default_quantity") or 1)
        unit = CALCULATOR_GCP_PRODUCTS[cand.sku].get("quantity_unit", "")
        qty = _quantity_for_unit(unit, hours, default_qty)
        items.append(
            {
                "map_key": cand.sku,
                "quantity": qty,
                "mxcell_id": cell.mxcell_id,
                "label": cell.label_plain,
            }
        )
    return items, mapping_notes


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
}


@tool(LIST_TOOL, "列出架構圖上已映射的 Azure 可估價資源。", LIST_SCHEMA)
async def list_mapped_resources(_args: dict[str, Any]) -> dict[str, Any]:
    xml_data = _run_context.get("xml_data") or ""
    hours_map = _run_context.get("hours_by_mxcell") or {}
    rows = plan_azure_line_items(xml_data, hours_map)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"resources": rows[0], "mapping_notes": rows[1]}, ensure_ascii=False, indent=2),
            }
        ]
    }


FETCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cloud": {"type": "string", "enum": ["aws", "gcp", "azure"]},
        "sku": {"type": "string"},
        "region": {"type": "string"},
    },
    "required": ["cloud", "sku", "region"],
}


@tool(
    FETCH_TOOL,
    "查官方 list 價（輔助對規格；不可取代 Calculator 總價）。",
    FETCH_SCHEMA,
)
async def fetch_official_hourly(args: dict[str, Any]) -> dict[str, Any]:
    cloud = str(args.get("cloud") or "")
    sku = str(args.get("sku") or "")
    region = str(args.get("region") or "")
    result = fetch_hourly(cloud, sku, region)
    if isinstance(result, PriceHit):
        payload = {
            "status": "hit",
            "hourly": float(result.hourly),
            "source": result.source,
        }
    elif isinstance(result, PriceUnsupported):
        payload = {"status": "unsupported"}
    else:
        payload = {"status": "miss"}
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]
    }


AZURE_CALC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "region": {"type": "string", "description": "Azure armRegionName，例如 eastus"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "map_key": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 1},
                    "mxcell_id": {"type": "string"},
                },
                "required": ["map_key"],
            },
        },
    },
    "required": ["region", "line_items"],
}


@tool(
    AZURE_CALC_TOOL,
    "在 Azure Pricing Calculator 模擬填寫並回傳 Estimated monthly cost。",
    AZURE_CALC_SCHEMA,
)
async def run_azure_calculator_estimate_tool(args: dict[str, Any]) -> dict[str, Any]:
    global _last_estimate
    region = str(args.get("region") or _run_context.get("region") or "")
    line_items = args.get("line_items") or []
    try:
        estimate = await asyncio.to_thread(
            run_azure_calculator_estimate,
            region,
            line_items,
        )
        _last_estimate = estimate
        payload = {
            "total_usd": float(estimate.total_usd),
            "currency": estimate.currency,
            "assumptions": estimate.assumptions,
            "source_url": estimate.source_url,
        }
        return {
            "content": [
                {"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}
            ]
        }
    except AzureCalculatorError as exc:
        return {
            "content": [{"type": "text", "text": f"Calculator 失敗：{exc}"}],
            "is_error": True,
        }


def _create_cost_mcp_server():
    return create_sdk_mcp_server(
        name=MCP_SERVER_NAME,
        version="1.0.0",
        tools=[list_mapped_resources, fetch_official_hourly, run_azure_calculator_estimate_tool],
    )


async def _run_llm_agent(
    *,
    xml_data: str,
    region: str,
    hours_by_mxcell: dict[str, int],
) -> CostEstimateResult:
    global _run_context, _last_estimate
    configure_provider_env()
    if not llm_auth_ready():
        return CostEstimateResult(
            total_usd=None,
            pricing_source="azure_calculator_failed",
            pricing_as_of=None,
            error=auth_error_message(),
        )

    _run_context = {
        "xml_data": xml_data,
        "region": region,
        "hours_by_mxcell": hours_by_mxcell,
    }
    _last_estimate = None

    user_prompt = (
        f"請為以下 Azure 架構圖估價。Region={region}。\n"
        "步驟：1) list_mapped_resources 2) 可選 fetch_official_hourly 3) 必須 run_azure_calculator_estimate。\n"
        "line_items 的 map_key 只能使用 list 回傳的 sku。"
    )

    options = ClaudeAgentOptions(
        system_prompt=load_system_prompt(),
        model=get_model_name(),
        mcp_servers={MCP_SERVER_NAME: _create_cost_mcp_server()},
        tools=[],
        allowed_tools=[LIST_TOOL_FQN, FETCH_TOOL_FQN, AZURE_CALC_TOOL_FQN],
        disallowed_tools=[
            "Bash",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "WebSearch",
            "WebFetch",
        ],
        permission_mode="bypassPermissions",
        max_turns=12,
        env=agent_sdk_env(),
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)
            async for _msg in client.receive_response():
                pass
    except Exception as exc:
        logger.exception("Pricing Agent 執行失敗")
        return CostEstimateResult(
            total_usd=None,
            pricing_source="azure_calculator_failed",
            pricing_as_of=None,
            error=str(exc),
        )
    finally:
        _run_context = {}

    if _last_estimate is None:
        return CostEstimateResult(
            total_usd=None,
            pricing_source="azure_calculator_failed",
            pricing_as_of=None,
            error="Agent 未呼叫 run_azure_calculator_estimate",
        )

    return CostEstimateResult(
        total_usd=_last_estimate.total_usd,
        pricing_source="azure_calculator",
        pricing_as_of=datetime.now(timezone.utc),
        agent_assumptions=_last_estimate.assumptions,
        line_items=_last_estimate.line_items,
        calculator_lines=_last_estimate.calculator_lines,
    )


def _run_deterministic_calculator(
    *,
    xml_data: str,
    region: str,
    hours_by_mxcell: dict[str, int],
) -> CostEstimateResult:
    line_items, mapping_notes = plan_azure_line_items(xml_data, hours_by_mxcell)
    if not line_items:
        return CostEstimateResult(
            total_usd=None,
            pricing_source="azure_calculator_failed",
            pricing_as_of=None,
            error="無可映射至 Calculator 的 Azure 資源",
            agent_assumptions=mapping_notes or None,
        )
    try:
        estimate = run_azure_calculator_estimate(region, line_items)
    except AzureCalculatorError as exc:
        return CostEstimateResult(
            total_usd=None,
            pricing_source="azure_calculator_failed",
            pricing_as_of=None,
            error=str(exc),
            agent_assumptions=mapping_notes or None,
        )
    except Exception as exc:
        logger.exception("Azure Calculator Playwright 執行失敗")
        return CostEstimateResult(
            total_usd=None,
            pricing_source="azure_calculator_failed",
            pricing_as_of=None,
            error=str(exc),
            agent_assumptions=mapping_notes or None,
        )
    assumptions = list(estimate.assumptions)
    if mapping_notes:
        assumptions.extend(["planner: sku inference"] + mapping_notes)
    else:
        assumptions.append("planner: deterministic")
    return CostEstimateResult(
        total_usd=estimate.total_usd,
        pricing_source="azure_calculator",
        pricing_as_of=datetime.now(timezone.utc),
        agent_assumptions=assumptions,
        line_items=estimate.line_items,
        calculator_lines=estimate.calculator_lines,
    )


async def run_cost_pricing_agent_async(
    *,
    xml_data: str,
    region: str,
    hours_by_mxcell: dict[str, int],
) -> CostEstimateResult:
    if skip_llm_planner():
        return _run_deterministic_calculator(
            xml_data=xml_data,
            region=region,
            hours_by_mxcell=hours_by_mxcell,
        )
    return await _run_llm_agent(
        xml_data=xml_data,
        region=region,
        hours_by_mxcell=hours_by_mxcell,
    )


def run_cost_pricing_agent(
    *,
    xml_data: str,
    region: str,
    hours_by_mxcell: dict[str, int],
) -> CostEstimateResult:
    """同步包裝（cost_service 用）。Live Calculator 走同步 Playwright，不 nest asyncio.run。"""
    if skip_llm_planner():
        return _run_deterministic_calculator(
            xml_data=xml_data,
            region=region,
            hours_by_mxcell=hours_by_mxcell,
        )
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        raise RuntimeError("run_cost_pricing_agent 不可在 running event loop 內同步呼叫")
    return asyncio.run(
        run_cost_pricing_agent_async(
            xml_data=xml_data,
            region=region,
            hours_by_mxcell=hours_by_mxcell,
        )
    )


def _run_deterministic_gcp_calculator(
    *,
    xml_data: str,
    region: str,
    hours_by_mxcell: dict[str, int],
) -> CostEstimateResult:
    line_items, mapping_notes = plan_gcp_line_items(xml_data, hours_by_mxcell)
    if not line_items:
        return CostEstimateResult(
            total_usd=None,
            pricing_source="gcp_calculator_failed",
            pricing_as_of=None,
            error="無可映射至 GCP Calculator 的資源",
            agent_assumptions=mapping_notes or None,
        )
    try:
        estimate = run_gcp_calculator_estimate(region, line_items)
    except GcpCalculatorError as exc:
        return CostEstimateResult(
            total_usd=None,
            pricing_source="gcp_calculator_failed",
            pricing_as_of=None,
            error=str(exc),
            agent_assumptions=mapping_notes or None,
        )
    except Exception as exc:
        logger.exception("GCP Calculator Playwright 執行失敗")
        return CostEstimateResult(
            total_usd=None,
            pricing_source="gcp_calculator_failed",
            pricing_as_of=None,
            error=str(exc),
            agent_assumptions=mapping_notes or None,
        )
    assumptions = list(estimate.assumptions)
    if mapping_notes:
        assumptions.extend(["planner: sku inference"] + mapping_notes)
    else:
        assumptions.append("planner: deterministic")
    return CostEstimateResult(
        total_usd=estimate.total_usd,
        pricing_source="gcp_calculator",
        pricing_as_of=datetime.now(timezone.utc),
        agent_assumptions=assumptions,
        line_items=estimate.line_items,
        calculator_lines=estimate.calculator_lines,
    )


def run_gcp_pricing_agent(
    *,
    xml_data: str,
    region: str,
    hours_by_mxcell: dict[str, int],
) -> CostEstimateResult:
    """GCP Pricing Calculator 估價（目前為確定性 + Playwright）。"""
    return _run_deterministic_gcp_calculator(
        xml_data=xml_data,
        region=region,
        hours_by_mxcell=hours_by_mxcell,
    )
