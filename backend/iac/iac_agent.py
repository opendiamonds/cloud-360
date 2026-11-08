"""D1/D2/D3 agent port. Calls langgraph_runtime; tests inject ``invoke``."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from iac.iac_log import log_event

Invoke = Callable[[dict[str, Any]], str]


def run_story_agent(
    story: str,
    summary: dict[str, Any],
    *,
    invoke: Invoke | None = None,
    request_id: str = "",
    user_id: int | None = None,
    diagram_id: int | None = None,
) -> dict[str, Any]:
    """One short agent call. Summary is counts only — never HCL or a prompt dump."""
    caller = invoke or default_invoke
    payload = {
        "story": story,
        "resource_count": int(summary.get("resource_count") or 0),
        "diagram_id": summary.get("diagram_id"),
    }
    text = caller(payload)
    notes = str(text or "")[:400]
    log_event(
        "agent_end",
        request_id=request_id or None,
        user_id=user_id,
        diagram_id=diagram_id if diagram_id is not None else summary.get("diagram_id"),
        route=f"/api/iac/{story}",
        model=None if invoke is not None else "openrouter",
        token_est=max(1, len(notes) // 4) if notes else 0,
    )
    return {
        "notes": notes,
        "model": None if invoke is not None else "openrouter",
        "token_est": max(0, len(notes) // 4),
    }


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return ""


def _note_prompt(summary: dict[str, Any]) -> str:
    if summary.get("story") == "scan":
        return json.dumps(
            {
                "instructions": (
                    "用繁體中文寫兩段純文字，兩段之間空一行。"
                    "第一段用完整句子說明哪些檢查未通過，資源名稱直接寫在句子裡。"
                    "若沒有未通過的檢查，第一段說明這次掃描沒有未通過的項目。"
                    "若檢查清單是空的，第一段說明這份草稿沒有可套用的檢查。"
                    "第二段只寫使用前最該先處理的一件事。"
                    "不要使用 Markdown，不要標題、粗體、程式碼符號、表格、連結或清單符號。"
                    "不要貼回完整 HCL。不要複述密碼、金鑰或 token 的字面值。"
                ),
                "checks": summary.get("checks") or [],
            },
            ensure_ascii=False,
        )
    files = summary.get("files")
    if isinstance(files, list) and files:
        return json.dumps(
            {
                "instructions": (
                    "用繁體中文寫兩段純文字，兩段之間空一行。"
                    "第一段用完整句子說明這份草稿建立了哪些資源，資源名稱直接寫在句子裡。"
                    "第二段只寫使用前要注意的一件事。"
                    "不要使用 Markdown，不要標題、粗體、程式碼符號、表格、連結或清單符號。"
                    "不要貼回完整 HCL。若看到密碼、金鑰或 token 的字面值，只說應改成 Secret Manager 引用，不要複述那些值。"
                ),
                "files": files,
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "story": summary.get("story"),
            "resource_count": summary.get("resource_count", 0),
            "instructions": "Reply with a short module note. Do not include secrets.",
        }
    )


async def stream_default_invoke(summary: dict[str, Any]):
    """Yield each OpenRouter token. One SSE request, deltas flushed as they arrive."""
    import httpx

    from services.langgraph_runtime import (
        DEFAULT_OPENROUTER_BASE_URL,
        DEFAULT_OPENROUTER_MODEL,
        OPENROUTER_API_KEY_ENV,
    )

    api_key = os.environ.get(OPENROUTER_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError("missing_openrouter_api_key")
    model_name = os.environ.get("LLM_MODEL", "").strip() or DEFAULT_OPENROUTER_MODEL
    url = DEFAULT_OPENROUTER_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": model_name,
        "stream": True,
        "temperature": 0,
        "messages": [{"role": "user", "content": _note_prompt(summary)}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(90.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        break
                    continue
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = parsed.get("choices") or []
                if not choices or not isinstance(choices[0], dict):
                    continue
                delta = (choices[0].get("delta") or {}).get("content")
                if isinstance(delta, str) and delta:
                    yield delta


def default_invoke(summary: dict[str, Any]) -> str:
    """LangGraph + OpenRouter. No apply tools and no second attempt."""
    from langgraph.graph import END, StateGraph

    from services.langgraph_runtime import InvokeOutcome, invoke_graph, openrouter_chat_model

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        model = openrouter_chat_model(timeout_seconds=90)
        msg = model.invoke([{"role": "user", "content": state["prompt"]}])
        content = getattr(msg, "content", None) or str(msg)
        return {**state, "text": content}

    graph = StateGraph(dict)
    graph.add_node("draft", _node)
    graph.set_entry_point("draft")
    graph.add_edge("draft", END)
    outcome = invoke_graph(graph.compile(), {"prompt": _note_prompt(summary)})
    if not isinstance(outcome, InvokeOutcome):
        raise TypeError("unexpected_invoke_outcome")
    state = outcome.state
    if isinstance(state, dict):
        return str(state.get("text") or "")
    return str(state)
