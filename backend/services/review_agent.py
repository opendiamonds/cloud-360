"""
review_agent.py — A3 Review Agent（Anthropic Agent SDK + OpenRouter）

快速路徑：不掛 MCP／工具（減少多回合），壓縮 findings 輸入，短輸出。
串流：即時 yield AssistantMessage TextBlock → SSE suggestion_delta。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from services.llm_provider import (
    auth_error_message,
    configure_provider_env,
    get_review_model_name,
    llm_auth_ready,
)
from services.llm_limits import agent_sdk_env

logger = logging.getLogger("cloud360.review_agent")

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "wa_review_system_prompt.md"
)

SEVERITY_ORDER = {"critical": 0, "high": 1, "warn": 2, "info": 3}
MAX_FINDINGS = 8
MAX_NODE_LABELS = 30


def load_review_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8").strip()
    return (
        "你是 AWS Well-Architected 顧問。依 findings 用繁中寫出精簡改善建議。"
        "不要推翻規則判定；引用 finding code。直接回覆，勿呼叫工具。"
    )


def fallback_suggestions_from_findings(findings: list[dict[str, Any]] | None) -> str:
    """Deterministic suggestions when LLM unavailable — keeps Assessment UX usable."""
    items = findings or []
    if not items:
        return (
            "備援建議\n\n"
            "本次無法呼叫 Review Agent，且沒有規則發現可供擴寫。"
            "請確認已設定 OPENROUTER_API_KEY 後重試建議。"
        )
    lines = [
        "備援建議（依規則發現自動產生）",
        "",
        "Review Agent 暫時不可用；以下依 findings 整理，請人工複核。",
        "",
    ]
    ordered = sorted(
        items,
        key=lambda f: SEVERITY_ORDER.get(str(f.get("severity") or ""), 9),
    )
    for i, f in enumerate(ordered, start=1):
        code = f.get("code") or "—"
        title = f.get("title") or code
        sev = f.get("severity") or "info"
        hint = (f.get("recommendation_hint") or f.get("message") or "").strip()
        lines.append(f"{i}. [{sev}] {code} — {title}")
        lines.append(hint or "（無建議細節）")
        lines.append("")
    return "\n".join(lines).strip()


def _compact_payload(
    diagram_summary: dict[str, Any],
    rule_result: dict[str, Any],
) -> dict[str, Any]:
    findings = list(rule_result.get("findings") or [])
    findings.sort(
        key=lambda f: SEVERITY_ORDER.get(str(f.get("severity") or ""), 9)
    )
    compact_findings = []
    for f in findings[:MAX_FINDINGS]:
        compact_findings.append(
            {
                "code": f.get("code"),
                "pillar": f.get("pillar"),
                "severity": f.get("severity"),
                "title": f.get("title"),
                "hint": f.get("recommendation_hint") or f.get("message"),
            }
        )
    nodes = diagram_summary.get("nodes") or []
    labels = []
    for n in nodes[:MAX_NODE_LABELS]:
        lab = (n.get("label") or "").strip()
        if lab:
            labels.append(lab[:80])
    return {
        "overall_score": rule_result.get("overall_score"),
        "pillar_scores": rule_result.get("pillar_scores"),
        "findings": compact_findings,
        "node_labels": labels,
        "node_count": diagram_summary.get("node_count") or len(nodes),
    }


async def run_review_agent(
    diagram_summary: dict[str, Any],
    rule_result: dict[str, Any],
) -> AsyncIterator[str]:
    """
    Yield suggestion text chunks for SSE. Raises RuntimeError on hard failure.
    """
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        TextBlock,
    )

    configure_provider_env()
    if not llm_auth_ready():
        raise RuntimeError(auth_error_message())

    payload = _compact_payload(diagram_summary, rule_result)
    user_prompt = (
        "依下列評核摘要，直接寫出繁中改善建議（精簡、可執行）。"
        "若有 high_risk_findings／high_risk_count>0，必須優先說明如何消除每一項 HIGH_RISK；"
        "若 overall_score < 80，亦須提出可提升分數至 ≥ 80 的改圖建議。"
        "使架構圖不再含高風險且分數達標；其餘 findings 次之。"
        "勿呼叫任何工具：\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    )
    # Prefers a faster model; override with REVIEW_LLM_MODEL.
    model_name = get_review_model_name()
    options = ClaudeAgentOptions(
        system_prompt=load_review_system_prompt(),
        model=model_name,
        tools=[],
        allowed_tools=[],
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
        max_turns=2,
        env=agent_sdk_env(),
    )

    streamed_parts: list[str] = []
    logger.info("review_agent start model=%s findings=%s", model_name, len(payload["findings"]))

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock) and block.text:
                            streamed_parts.append(block.text)
                            yield block.text

        if not "".join(streamed_parts).strip():
            raise RuntimeError("ReviewAgent 未產出 suggestions（模型未回覆文字）")
    except Exception:
        logger.exception("ReviewAgent runtime failure")
        raise
