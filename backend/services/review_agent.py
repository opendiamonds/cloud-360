"""
review_agent.py — A3 Review Agent（LangGraph + OpenRouter）

快速路徑：獨立 compiled Review graph，壓縮 findings 輸入，短輸出。
串流：model／graph messages stream → SSE suggestion_delta。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TypedDict

from services.llm_provider import (
    auth_error_message,
    configure_provider_env,
    get_review_model_name,
)

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


def _message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


class _ReviewState(TypedDict, total=False):
    user_prompt: str
    text: str


def _compile_review_graph(model: Any, system_prompt: str):
    from langchain_core.messages import HumanMessage, SystemMessage
    from langgraph.graph import END, StateGraph

    async def generate(state: _ReviewState) -> _ReviewState:
        msg = await model.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state["user_prompt"]),
            ]
        )
        return {**state, "text": _message_text(getattr(msg, "content", None))}

    # Must match node annotation: StateGraph(dict) + TypedDict param yields
    # empty state under stream_mode="messages" with ChatOpenAI (KeyError user_prompt).
    graph = StateGraph(_ReviewState)
    graph.add_node("generate", generate)
    graph.set_entry_point("generate")
    graph.add_edge("generate", END)
    return graph.compile()


async def run_review_agent(
    diagram_summary: dict[str, Any],
    rule_result: dict[str, Any],
) -> AsyncIterator[str]:
    """
    Yield suggestion text chunks for SSE. Raises RuntimeError on hard failure.
    """
    from services.langgraph_runtime import RuntimeAuthError, openrouter_chat_model

    configure_provider_env()
    payload = _compact_payload(diagram_summary, rule_result)
    user_prompt = (
        "依下列評核摘要，直接寫出繁中改善建議（精簡、可執行）。"
        "若有 high_risk_findings／high_risk_count>0，必須優先說明如何消除每一項 HIGH_RISK；"
        "若 overall_score < 80，亦須提出可提升分數至 ≥ 80 的改圖建議。"
        "使架構圖不再含高風險且分數達標；其餘 findings 次之。"
        "勿呼叫任何工具：\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    )
    model_name = get_review_model_name()
    logger.info(
        "review_agent start model=%s findings=%s",
        model_name,
        len(payload["findings"]),
    )

    try:
        try:
            model = openrouter_chat_model(model=model_name)
        except RuntimeAuthError as exc:
            raise RuntimeError(auth_error_message()) from exc

        system_prompt = load_review_system_prompt()
        compiled = _compile_review_graph(model, system_prompt)
        streamed_parts: list[str] = []

        async for item in compiled.astream(
            {"user_prompt": user_prompt},
            stream_mode="messages",
        ):
            msg_chunk = item[0] if isinstance(item, tuple) else item
            text = _message_text(getattr(msg_chunk, "content", None))
            if text:
                streamed_parts.append(text)
                yield text

        if not "".join(streamed_parts).strip():
            raise RuntimeError("ReviewAgent 未產出 suggestions（模型未回覆文字）")
    except RuntimeError:
        raise
    except Exception:
        logger.exception("ReviewAgent runtime failure")
        raise
