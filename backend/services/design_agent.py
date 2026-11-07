from __future__ import annotations
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
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

from services.diagram_builder import build_mxgraph_xml
from services.progress_channel import ProgressChannel, ProgressEvent, RequestKey
from services.llm_limits import truncate_text_for_llm, agent_sdk_env
from services.llm_provider import (
    auth_error_message,
    configure_provider_env,
    get_design_model_name,
    llm_auth_ready,
)

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "cloud_architecture_system_prompt.md"

# U22：這裡原本有兩個模組層全域，兩者皆已退場，**不得以任何形式復活**。
#   1. 一個進度事件佇列：一個格子、所有併發請求共用。後到的請求覆寫它之後，
#      先到的請求讀到的是後到者的佇列——使用者 A 因此收到使用者 B 產生的架構
#      圖 XML。取代者是 services/progress_channel.py 的 per-request 通道。
#   2. 一個「最後一次產圖的 XML」：死狀態，寫入後從未被讀取。一併刪除，避免
#      下一個人沿用同一個形狀；XML 現在只經 ProgressChannel 的 `xml` 事件流向
#      讀取端。
# 進度事件的鍵由**入口端**鑄造並以 `request_key` 顯式傳遞（BR1.1）。
# 兩個舊名刻意不寫在本檔內（連註解也不寫）：契約測試以純 grep 斷言它們零命中，
# 寫出來會讓那道閘門永遠紅。退場的完整說明見本單元 record 的 code-summary.md。


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
async def draw_architecture_diagram(provider: str, groups: list[dict[str, Any]], nodes: list[dict[str, Any]], edges: list[dict[str, Any]], config: RunnableConfig) -> str:
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
    # `config` 由 LangGraph 注入，**不在 LLM 看到的工具 schema 內**（實測
    # `draw_architecture_diagram.args` 只含四個業務參數）。進度事件的鍵走這條
    # 路而不是模組層全域：鍵隨 invocation 傳遞，所以兩個併發請求的工具各自寫
    # 進自己的通道（BR1.3）。
    request_key = _request_key_from_config(config)

    async def on_progress(msg: str) -> None:
        await ProgressChannel.publish(request_key, ProgressEvent("progress", msg))

    await ProgressChannel.publish(
        request_key, ProgressEvent("progress", "🧠 正在規劃進階架構拓樸...")
    )

    try:
        xml_data = await build_mxgraph_xml(
            groups=groups or [],
            nodes=nodes or [],
            edges=edges or [],
            on_progress=on_progress,
            provider=provider,
        )
        await ProgressChannel.publish(request_key, ProgressEvent("xml", xml_data))
        return "架構圖已成功產生並送往畫布。請用簡短繁中告知使用者參考右側畫面。"
    except Exception:
        # 例外原文的**唯一**出口是這一行 log。回傳值會進入 LLM 的 context，而
        # LLM 的輸出直送使用者——那不是一道邊界，是「使用者可能看到，取決於
        # 模型當下的判斷」。故回傳固定字串（BR3.1／SEC-2／AC13.1.3）。
        # 同一個 except 區塊的 publish 早已是固定字串，這是消除同區塊內的不
        # 一致，不是新增限制。
        logger.exception("draw_architecture_diagram 失敗")
        await ProgressChannel.publish(
            request_key, ProgressEvent("error", "產圖發生錯誤")
        )
        return "產圖失敗，請稍後再試或調整需求描述。"


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


#: 進度鍵在 LangGraph `config["configurable"]` 裡的欄位名。工具與入口端共用
#: 這個常數，使「誰寫、誰讀」是同一個識別字而不是兩處各寫一次字面值。
REQUEST_KEY_CONFIG_FIELD = "request_key"


def _request_key_from_config(config: RunnableConfig | None) -> RequestKey:
    """自 LangGraph 的 config 取出本次請求的進度鍵。

    取不到時回空字串而非拋例外：拋例外會從工具內部冒上去、被下方的
    `except Exception` 接住並讓整個請求失敗，而缺鍵是**呼叫端**的程式錯誤。
    空鍵不在 registry 裡，所以事件會走 BR3.2 的「記 ERROR 並丟棄」——
    留得下痕跡且不弄壞請求。這是刻意在這一層選擇降級而非快速失敗：
    `run_design_agent` 的 `request_key` 是必填關鍵字參數，缺鍵在入口端就會是
    TypeError，到不了這裡。
    """
    return ((config or {}).get("configurable") or {}).get(
        REQUEST_KEY_CONFIG_FIELD, ""
    )


async def _drain_progress(request_key: RequestKey) -> AsyncIterator[dict[str, str]]:
    """取出該請求已緩衝的進度事件，轉成 SSE 的 wire 形狀。

    U22：原本的簽章收一個 `asyncio.Queue`，而呼叫端傳的是模組層全域——**引數
    在呼叫當下才取值**，於是後到的請求覆寫全域之後，先到的請求讀到的是後到者
    的佇列。另外當全域已被設回 `None` 時，`None.get_nowait()` 拋 AttributeError
    讓另一個還在跑的請求崩潰。現在改收 `request_key`，由 ProgressChannel 以鍵
    界定可取到的集合；鍵不存在或已關閉時它回空迭代器而不是崩潰（BR2.4）。
    """
    async for event in ProgressChannel.drain(request_key):
        yield event.as_dict()

# Shared memory saver for the POC
memory = MemorySaver()

async def run_design_agent(
    messages: list[dict[str, str]],
    current_xml: str | None = None,
    thread_id: str = "default-thread",
    *,
    request_key: RequestKey,
) -> AsyncIterator[dict[str, str]]:
    """執行 Design Agent，逐則 yield SSE 事件 `{type, content}`。

    `request_key` 是**必填關鍵字參數**，刻意沒有預設值：它是進度事件的隔離鍵，
    有預設值就等於多一條「忘了傳也能跑」的路，而那條路的症狀是全部 progress／
    xml 走 BR3.2 被記 log 丟棄——畫面上看起來只是沒有進度訊息，不會有錯誤。
    缺它現在是 TypeError，在入口端就會炸（fail fast）。

    它與 `thread_id` **並存且語意分離**，兩者不可互相替代：
      - `thread_id` 是 LangGraph checkpointer 的對話記憶分區，現狀是 per-user
        （`f"user-{id}-design"`）。改成 per-request 等於關掉對話記憶。
      - `request_key` 是進度通道的隔離鍵，必須 per-request。

    通道的 `open`／`close` 由**入口端**的 `try/finally` 擁有，不在本函式
    （BR2.1／BR2.3）——本函式只負責把鍵傳下去並讀取。
    """
    configure_provider_env()
    if not llm_auth_ready():
        yield {"type": "error", "content": auth_error_message()}
        return

    system_prompt = build_system_prompt(current_xml)
    user_prompt = format_user_prompt(messages)
    
    graph = build_graph().compile(checkpointer=memory)

    initial_state = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
    }
    
    # 兩個鍵並存於同一個 config：thread_id 給 checkpointer，request_key 給進度
    # 通道。工具以注入的 RunnableConfig 讀後者（見 _request_key_from_config）。
    config = {
        "configurable": {
            "thread_id": thread_id,
            REQUEST_KEY_CONFIG_FIELD: request_key,
        }
    }

    try:
        async for event in graph.astream(initial_state, config=config, stream_mode="values"):
            # yield any queued events from the tools
            async for q_event in _drain_progress(request_key):
                yield q_event

            last_message = event["messages"][-1]
            if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                yield {"type": "message", "content": last_message.content}

        # drain one last time
        async for q_event in _drain_progress(request_key):
            yield q_event

    except Exception:
        # 例外原文的**唯一**出口是這一行 log。這一則 yield 直送 SSE 給使用者，
        # 所以它必須是固定字串（BR3.1／SEC-2／AC13.1.3）。原本這裡把例外物件
        # 插進 f-string——它是把內部例外原文送到使用者眼前的那一行，而 BR1.2
        # 新增的 DuplicateChannelKey 若由此經過，會讓修法自己在它宣稱要封的那
        # 個面上開一個新口。（舊字串刻意不逐字寫在這裡：契約測試以形狀級 grep
        # 斷言那些插值樣式零命中。）
        logger.exception("Design Agent 執行失敗")
        yield {"type": "error", "content": "發生未預期錯誤，請稍後再試。"}
    # 注意：這裡**沒有** finally。通道的清除由入口端的 try/finally 擁有
    # （BR2.1），本函式不得代為 close——原本這裡把那個模組層全域設回 None，
    # 既非清除也非隔離（它沒有 per-key 可刪），而且正是它讓另一個還在跑的
    # 請求的 drain 崩潰（對 None 呼叫 get_nowait 拋 AttributeError）。
