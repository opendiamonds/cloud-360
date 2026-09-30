from __future__ import annotations
import asyncio
import logging
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

from services.diagram_builder import build_mxgraph_xml
from services.llm_limits import truncate_text_for_llm, agent_sdk_env
from services.llm_provider import (
    auth_error_message,
    configure_provider_env,
    get_design_model_name,
    llm_auth_ready,
)

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "cloud_architecture_system_prompt.md"

_progress_queue: asyncio.Queue[dict[str, str]] | None = None
_last_xml: str | None = None

def load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"找不到 system prompt：{PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8").strip()

def build_system_prompt(current_xml: str | None = None) -> str:
    prompt = load_system_prompt()
    if current_xml:
        xml_block = truncate_text_for_llm(current_xml, label="架構 XML")
        prompt += (
            "\n\n【目前的架構草稿】\n"
            "使用者目前畫布上的 XML 內容如下，請在呼叫工具時，基於此內容進行「修改」或「擴充」：\n"
            f"```xml\n{xml_block}\n```\n"
        )
    return prompt

def format_user_prompt(messages: list[dict[str, str]]) -> str:
    lines: list[str] = ["以下是與使用者的對話歷史，請依 system 指示回應：\n"]
    for msg in messages:
        role = msg.get("role", "user")
        label = "使用者" if role == "user" else "助理"
        lines.append(f"{label}：{msg.get('content', '')}")
    lines.append(
        "\n若需求已足夠明確，請呼叫 draw_architecture_diagram 工具產圖；"
        "否則先用文字釐清需求。"
        "回覆使用者時請用一般口語對答，不要使用 Markdown（不要 #、**、- 清單、程式碼區塊等）。"
    )
    return "\n".join(lines)


@tool
async def draw_architecture_diagram(provider: str, groups: list[dict[str, Any]], nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    """當架構需求釐清後，呼叫此工具來產生雲端架構圖。
    
    Args:
        provider: 雲端供應商平台 ("AWS", "GCP", "Azure")
        groups: 架構圖上的框架/區域陣列。每個物件包含：
            - id: 框架唯一識別碼 (如 "g_cloud", "g_vpc", "g_az1", "g_pub1", "g_priv1")
            - name: 框架顯示名稱 (如 "AWS Cloud", "VPC", "Availability Zone 1", "Public Subnet 1", "Private Subnet 1", "DB Subnet 1")
            - type: 框架類型（必須對齊模板樣式，AWS: "aws_cloud", "vpc", "az", "public_subnet", "private_subnet"; GCP: "gcp_cloud", "gcp_region", "gcp_zone", "gcp_vpc", "gcp_subnet"; Azure: "azure_cloud", "azure_vnet", "azure_az", "azure_subnet", "azure_resource_group"）
            - x, y, width, height: 絕對座標與尺寸
        nodes: 要畫在圖表上的雲端元件節點陣列。每個物件包含 id, name (官方全名), x, y
        edges: 節點間的連線陣列。每個物件包含 source (起點 node id), target (終點 node id)
    """
    global _last_xml

    async def on_progress(msg: str) -> None:
        if _progress_queue is not None:
            await _progress_queue.put({"type": "progress", "content": msg})

    if _progress_queue is not None:
        await _progress_queue.put({"type": "progress", "content": "🧠 正在規劃進階架構拓樸..."})

    try:
        xml_data = await build_mxgraph_xml(
            groups=groups or [],
            nodes=nodes or [],
            edges=edges or [],
            on_progress=on_progress,
            provider=provider,
        )
        _last_xml = xml_data
        if _progress_queue is not None:
            await _progress_queue.put({"type": "xml", "content": xml_data})
        return "架構圖已成功產生並送往畫布。請用簡短繁中告知使用者參考右側畫面。"
    except Exception as e:
        logger.exception("draw_architecture_diagram 失敗")
        if _progress_queue is not None:
            await _progress_queue.put({"type": "error", "content": "產圖發生錯誤"})
        return f"產圖失敗：{e}"


class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def build_graph() -> StateGraph:
    tools = [draw_architecture_diagram]
    tool_node = ToolNode(tools)

    import os
    configure_provider_env()
    model_name = get_design_model_name()
    
    # LangChain Anthropic requires api_key. Use ANTHROPIC_AUTH_TOKEN set by llm_provider
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENROUTER_API_KEY") or ""
    base_url = os.environ.get("ANTHROPIC_BASE_URL")
    
    llm = ChatAnthropic(
        model=model_name, 
        temperature=0.2,
        api_key=api_key,
        base_url=base_url
    ).bind_tools(tools)

    async def call_model(state: GraphState):
        msgs = state["messages"]
        system_msgs = [m for m in msgs if isinstance(m, SystemMessage)]
        non_system_msgs = [m for m in msgs if not isinstance(m, SystemMessage)]
        
        # Anthropic API requires at most one system message at the top of the conversation.
        # When using memory checkpoints across turns, use the latest system prompt.
        if system_msgs:
            formatted_msgs = [system_msgs[-1]] + non_system_msgs
        else:
            formatted_msgs = non_system_msgs

        response = await llm.ainvoke(formatted_msgs)
        return {"messages": [response]}

    def should_continue(state: GraphState):
        last_msg = state["messages"][-1]
        if last_msg.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(GraphState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    return workflow


async def _drain_progress(queue: asyncio.Queue[dict[str, str]]) -> AsyncIterator[dict[str, str]]:
    while True:
        try:
            event = queue.get_nowait()
            yield event
        except asyncio.QueueEmpty:
            break

# Shared memory saver for the POC
memory = MemorySaver()

async def run_design_agent(
    messages: list[dict[str, str]],
    current_xml: str | None = None,
    thread_id: str = "default-thread",
) -> AsyncIterator[dict[str, str]]:
    global _progress_queue, _last_xml

    configure_provider_env()
    if not llm_auth_ready():
        yield {"type": "error", "content": auth_error_message()}
        return

    _progress_queue = asyncio.Queue()
    _last_xml = None

    system_prompt = build_system_prompt(current_xml)
    user_prompt = format_user_prompt(messages)
    
    graph = build_graph().compile(checkpointer=memory)

    initial_state = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
    }
    
    config = {"configurable": {"thread_id": thread_id}}

    try:
        async for event in graph.astream(initial_state, config=config, stream_mode="values"):
            # yield any queued events from the tools
            async for q_event in _drain_progress(_progress_queue):
                yield q_event

            last_message = event["messages"][-1]
            if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                yield {"type": "message", "content": last_message.content}
        
        # drain one last time
        async for q_event in _drain_progress(_progress_queue):
            yield q_event
            
    except Exception as e:
        logger.exception("Design Agent 執行失敗")
        yield {"type": "error", "content": f"發生未預期錯誤：{e}"}
    finally:
        _progress_queue = None
