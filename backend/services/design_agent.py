"""
design_agent.py — A1 Design Agent（Anthropic Agent SDK + OpenRouter）

職責：
  使用 claude-agent-sdk 與使用者對話；需求明確時呼叫 in-process MCP tool
  `draw_architecture_diagram`，再經 diagram_builder 產出 draw.io XML。

安全邊界：
  - allowed_tools 僅開放 mcp__cloud360-design__draw_architecture_diagram
  - 明確禁用 Bash / Read / Write / Edit 等檔案與終端工具（Web API 不可開）

供應商與環境變數：
  由 services.llm_provider 決定（LLM_PROVIDER=openrouter｜cli）。部署走
  OpenRouter，本機可改用已登入的 claude CLI；細節見該模組。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)

from services.diagram_builder import build_mxgraph_xml
from services.llm_limits import (
    agent_sdk_env,
    truncate_text_for_llm,
)
from services.llm_provider import (
    auth_error_message,
    configure_provider_env,
    get_model_name,
    llm_auth_ready,
)

logger = logging.getLogger(__name__)

# MCP server / tool 全名（Agent SDK 約定：mcp__{server}__{tool}）
MCP_SERVER_NAME = "cloud360-design"
DRAW_TOOL_NAME = "draw_architecture_diagram"
DRAW_TOOL_FQN = f"mcp__{MCP_SERVER_NAME}__{DRAW_TOOL_NAME}"

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "cloud_architecture_system_prompt.md"
)

# 執行期間由 run_design_agent 注入：進度佇列與最後產出的 XML
_progress_queue: asyncio.Queue[dict[str, str]] | None = None
_last_xml: str | None = None


def load_system_prompt() -> str:
    """載入文字座標繪圖指南（與重構前 system prompt 語意相同）。"""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"找不到 system prompt：{PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_system_prompt(current_xml: str | None = None) -> str:
    """組合 system prompt；若有畫布草稿則附加 current_xml（局部修改路徑）。"""
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
    """將多輪 messages 壓成單一 user prompt 供 Agent SDK query。"""
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


# ---------------------------------------------------------------------------
# MCP Tool：draw_architecture_diagram
# schema 對齊重構前 OpenRouter function tool 參數
# ---------------------------------------------------------------------------

DRAW_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "provider": {
            "type": "string",
            "enum": ["AWS", "GCP", "Azure"],
            "description": "雲端供應商平台，決定畫圖使用的元件與圖示風格（AWS, GCP 或 Azure）。"
        },
        "groups": {
            "type": "array",
            "description": "架構圖上的框架/區域",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {
                        "type": "string",
                        "description": "例如 VPC, AZ-1, Public Subnet 1, Azure VNet",
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "aws_cloud",
                            "vpc",
                            "az",
                            "public_subnet",
                            "private_subnet",
                            "gcp_cloud",
                            "gcp_vpc",
                            "gcp_subnet",
                            "azure_cloud",
                            "azure_vnet",
                            "azure_resource_group",
                            "azure_subnet",
                        ],
                    },
                    "x": {"type": "integer", "description": "絕對 X 座標"},
                    "y": {"type": "integer", "description": "絕對 Y 座標"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "required": ["id", "name", "type", "x", "y", "width", "height"],
            },
        },
        "nodes": {
            "type": "array",
            "description": "要畫在圖表上的雲端元件節點陣列（AWS, GCP 或 Azure）",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "節點唯一識別碼"},
                    "name": {
                        "type": "string",
                        "description": "雲端元件名稱，例如 EC2, GKE, AKS, Cloud SQL, Azure SQL Database",
                    },
                    "x": {"type": "integer", "description": "絕對 X 座標"},
                    "y": {"type": "integer", "description": "絕對 Y 座標"},
                },
                "required": ["id", "name", "x", "y"],
            },
        },
        "edges": {
            "type": "array",
            "description": "節點間的連線陣列",
            "items": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "起始節點/群組的 ID",
                    },
                    "target": {
                        "type": "string",
                        "description": "目標節點/群組的 ID",
                    },
                },
                "required": ["source", "target"],
            },
        },
    },
    "required": ["nodes"],
}


@tool(
    DRAW_TOOL_NAME,
    "當架構需求釐清後，呼叫此工具來產生雲端架構圖。",
    DRAW_INPUT_SCHEMA,
)
async def draw_architecture_diagram(args: dict[str, Any]) -> dict[str, Any]:
    """
    MCP tool handler：收到 groups/nodes/edges 後組 XML，
    並把 progress / xml 事件推入佇列供 SSE 消費。
    """
    global _last_xml

    async def on_progress(msg: str) -> None:
        if _progress_queue is not None:
            await _progress_queue.put({"type": "progress", "content": msg})

    if _progress_queue is not None:
        await _progress_queue.put(
            {"type": "progress", "content": "🧠 正在規劃進階架構拓樸..."}
        )

    try:
        xml_data = await build_mxgraph_xml(
            groups=args.get("groups") or [],
            nodes=args.get("nodes") or [],
            edges=args.get("edges") or [],
            on_progress=on_progress,
            provider=args.get("provider"),
        )
        _last_xml = xml_data
        if _progress_queue is not None:
            await _progress_queue.put({"type": "xml", "content": xml_data})
        return {
            "content": [
                {
                    "type": "text",
                    "text": "架構圖已成功產生並送往畫布。請用簡短繁中告知使用者參考右側畫面。",
                }
            ]
        }
    except Exception as e:
        logger.exception("draw_architecture_diagram 失敗")
        if _progress_queue is not None:
            await _progress_queue.put({"type": "error", "content": "產圖發生錯誤"})
        return {
            "content": [{"type": "text", "text": f"產圖失敗：{e}"}],
            "is_error": True,
        }


def _create_design_mcp_server():
    """建立 in-process MCP server（僅含產圖 tool）。"""
    return create_sdk_mcp_server(
        name=MCP_SERVER_NAME,
        version="1.0.0",
        tools=[draw_architecture_diagram],
    )


async def _drain_progress(
    queue: asyncio.Queue[dict[str, str]],
) -> AsyncIterator[dict[str, str]]:
    """非阻塞取出目前佇列中所有進度／xml／error 事件。"""
    while True:
        try:
            event = queue.get_nowait()
            yield event
        except asyncio.QueueEmpty:
            break


async def run_design_agent(
    messages: list[dict[str, str]],
    current_xml: str | None = None,
) -> AsyncIterator[dict[str, str]]:
    """
    執行 Design Agent，yield SSE 用事件：
      {"type": "message"|"progress"|"xml"|"error", "content": "..."}
    """
    global _progress_queue, _last_xml

    configure_provider_env()

    if not llm_auth_ready():
        yield {"type": "error", "content": auth_error_message()}
        return

    _progress_queue = asyncio.Queue()
    _last_xml = None
    message_replied = False

    system_prompt = build_system_prompt(current_xml)
    user_prompt = format_user_prompt(messages)
    model_name = get_model_name()

    mcp_server = _create_design_mcp_server()

    # tools=[]：不把 Claude Code 內建工具放進 context
    # allowed_tools：預先核准我們的 MCP 產圖 tool
    # disallowed_tools：雙重保險，禁止檔案／終端類工具
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=model_name,
        mcp_servers={MCP_SERVER_NAME: mcp_server},
        tools=[],
        allowed_tools=[DRAW_TOOL_FQN],
        disallowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"],
        permission_mode="bypassPermissions",
        max_turns=8,
        env=agent_sdk_env(),
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)

            async for msg in client.receive_response():
                # 先吐出 tool 執行中的 progress / xml
                async for event in _drain_progress(_progress_queue):
                    yield event

                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock) and block.text:
                            message_replied = True
                            yield {"type": "message", "content": block.text}

            # 結束後再清一次佇列
            async for event in _drain_progress(_progress_queue):
                yield event

            # tool 已產 XML 但模型沒說人話時，補一句（對齊舊行為）
            if _last_xml and not message_replied:
                yield {
                    "type": "message",
                    "content": "我已經為您產生了具備區域框架的架構圖，請參考右側畫面！",
                }

    except Exception as e:
        logger.exception("Design Agent 執行失敗")
        yield {"type": "error", "content": f"發生未預期錯誤：{e}"}
    finally:
        _progress_queue = None
