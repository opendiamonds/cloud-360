"""Cost advice agent — LangGraph/OpenRouter via U6; optional U5 pricing."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("cloud360.cost_advice_agent")

_MAX_INVOKES = 3


def _optional_price_notes(clouds: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    try:
        from cost.pricing_client import fetch_hourly
    except Exception:  # noqa: BLE001
        return ["pricing_port_unavailable"]

    for cloud_block in clouds:
        cloud = cloud_block.get("cloud")
        if not isinstance(cloud, str):
            continue
        for line in cloud_block.get("lines") or []:
            sku = line.get("sku")
            region = line.get("region") or "us-east-1"
            if not sku:
                continue
            try:
                result = fetch_hourly(cloud, str(sku), str(region))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "pricing lookup skipped cloud=%s err=%s",
                    cloud,
                    type(exc).__name__,
                )
                notes.append(f"{cloud}:{sku}:error")
                continue
            kind = getattr(result, "kind", None)
            if kind == "hit":
                notes.append(f"{cloud}:{sku}:hit:{result.hourly}")
            elif kind == "miss":
                notes.append(f"{cloud}:{sku}:miss")
            else:
                notes.append(f"{cloud}:{sku}:unsupported")
            # One sample per cloud is enough for Must path budget
            break
    return notes


def _build_prompt(payload: dict[str, Any], price_notes: list[str]) -> str:
    clouds = payload.get("clouds") or []
    body = {
        "estimate_set_id": payload.get("estimate_set_id"),
        "clouds": clouds,
        "catalog_price_notes": price_notes,
        "instructions": (
            "你是雲端成本顧問。請只輸出一個 JSON 物件（不要包在程式碼區塊裡），鍵為："
            "saving_text（必填）、comparison_text（選填）、quality_text（選填）、"
            "unavailable_reasons（物件）。"
            "三個 *_text 欄位必須全部使用繁體中文（台灣用語），禁止簡體中文、禁止英文段落"
            "（專有名詞如 AWS／RI／CUD 可保留原文）。"
            "禁止使用 Markdown：不要用 #、*、-、>、```、**粗體**、_斜體_、[連結](url)、表格。"
            "排版只用換行：每一點建議獨立一行，段落之間空一行；可用「1.」「2.」或「・」開頭。"
            "saving_text 寫省錢與用量優化建議（至少兩段或兩點）；"
            "comparison_text 寫跨雲比較，若少於兩朵雲則省略並在 unavailable_reasons.comparison 說明；"
            "quality_text 寫資料品質／完整性檢查。"
            "不得捏造目錄牌價；若 catalog_price_notes 沒有 hit，請在內文或 "
            "unavailable_reasons 說明無法對照現價。"
        ),
    }
    return json.dumps(body, ensure_ascii=False)


_MD_HEADING = re.compile(r"(?m)^#{1,6}\s+")
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_MD_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")
_MD_CODE_FENCE = re.compile(r"```[\s\S]*?```")
_MD_INLINE_CODE = re.compile(r"`([^`]+)`")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MD_BLOCKQUOTE = re.compile(r"(?m)^>\s?")
_MD_UL = re.compile(r"(?m)^(?:[\-\*\+]|•)\s+")
_MD_HR = re.compile(r"(?m)^(?:-{3,}|\*{3,}|_{3,})\s*$")


def strip_markdown(text: str) -> str:
    """Normalize advice to plain Traditional-Chinese-friendly layout (no Markdown)."""
    if not text:
        return ""
    out = str(text).replace("\r\n", "\n").replace("\r", "\n")
    out = _MD_CODE_FENCE.sub(lambda m: m.group(0).strip("`").strip(), out)
    out = _MD_IMAGE.sub(r"\1", out)
    out = _MD_LINK.sub(r"\1", out)
    out = _MD_HEADING.sub("", out)
    out = _MD_BLOCKQUOTE.sub("", out)
    out = _MD_HR.sub("", out)
    out = _MD_BOLD.sub(lambda m: m.group(1) or m.group(2) or "", out)
    out = _MD_ITALIC.sub(lambda m: m.group(1) or m.group(2) or "", out)
    out = _MD_INLINE_CODE.sub(r"\1", out)
    out = _MD_UL.sub("・", out)
    # Collapse 3+ blank lines to one spacer
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _normalize_advice_field(value: Any) -> str | None:
    if value is None:
        return None
    text = strip_markdown(str(value)).strip()
    return text or None


def _parse_llm_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {"saving_text": text[:4000], "unavailable_reasons": {"parse": "non_json"}}


def _invoke_once(prompt: str) -> str:
    """One LLM call via U6 helpers (counts toward ≤3 budget)."""
    from services.langgraph_runtime import (
        InvokeOutcome,
        invoke_graph,
        openrouter_chat_model,
    )

    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("langgraph_missing") from exc

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        model = openrouter_chat_model()
        msg = model.invoke([{"role": "user", "content": state["prompt"]}])
        content = getattr(msg, "content", None) or str(msg)
        return {**state, "text": content}

    graph = StateGraph(dict)
    graph.add_node("generate", _node)
    graph.set_entry_point("generate")
    graph.add_edge("generate", END)
    compiled = graph.compile()
    outcome = invoke_graph(compiled, {"prompt": prompt})
    if not isinstance(outcome, InvokeOutcome):
        raise TypeError("unexpected_invoke_outcome")
    state = outcome.state
    if isinstance(state, dict) and "text" in state:
        return str(state["text"])
    return str(state)


def generate_advice(
    payload: dict[str, Any],
    *,
    on_phase: Callable[[str, str | None], None] | None = None,
) -> dict[str, Any]:
    """Produce advice texts. Never fabricates catalog prices (BR7.3)."""

    def _phase(phase: str, message: str | None = None) -> None:
        if on_phase is not None:
            on_phase(phase, message)

    clouds = payload.get("clouds") or []
    unavailable: dict[str, Any] = {}
    _phase("pricing", "正在查詢目錄價對照")
    price_notes = _optional_price_notes(clouds)
    if not any(":hit:" in n for n in price_notes):
        unavailable["catalog_price"] = "unavailable"

    cloud_ids = {c.get("cloud") for c in clouds if isinstance(c, dict)}
    if len(cloud_ids) < 2:
        unavailable["comparison"] = "insufficient_clouds"

    prompt = _build_prompt(payload, price_notes)
    invokes = 0
    _phase("llm", "正在呼叫 AI 產生建議")
    try:
        raw = _invoke_once(prompt)
        invokes += 1
        parsed = _parse_llm_json(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("advice llm failed err=%s", type(exc).__name__)
        # Deterministic fallback so Must path can still complete offline/tests
        saving = (
            "根據上傳估價表，建議先核對用量與承諾折扣（CUD／RI／Savings Plan）是否已反映。\n\n"
            "目錄價僅供參考，本次未能取得可靠現價對照，請以雲端帳單或官方計算器再確認。"
            if "catalog_price" in unavailable
            else "根據上傳估價表，建議優先檢視高金額品項與未使用容量。\n\n"
            "請人工核對用量假設與區域設定後再調整。"
        )
        parsed = {
            "saving_text": saving,
            "comparison_text": None,
            "quality_text": None,
            "unavailable_reasons": {
                **unavailable,
                "llm": type(exc).__name__,
            },
        }

    saving = _normalize_advice_field(parsed.get("saving_text")) or ""
    if not saving:
        saving = "建議產出不完整，請稍後重試或人工檢視估價表。"

    comparison = _normalize_advice_field(parsed.get("comparison_text"))
    quality = _normalize_advice_field(parsed.get("quality_text"))
    reasons = dict(unavailable)
    extra = parsed.get("unavailable_reasons") or {}
    if isinstance(extra, dict):
        reasons.update(extra)
    if "comparison" in reasons:
        comparison = comparison or None
    if invokes > _MAX_INVOKES:
        reasons["llm_budget"] = "exceeded"

    return {
        "saving_text": saving,
        "comparison_text": comparison,
        "quality_text": quality,
        "unavailable_reasons": reasons,
        "invokes": invokes,
    }
