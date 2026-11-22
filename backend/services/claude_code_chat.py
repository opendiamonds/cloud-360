"""claude_code_chat.py — 本機開發用的 LangChain chat model（走使用者已登入的 `claude` CLI）

**只在 `LLM_PROVIDER=claude-code` 且 `APP_ENV=local` 時會被建立**，閘門在
`services.llm_provider.get_provider`，factory 在 `services.langgraph_runtime.chat_model`。
部署 stack 的映像裡沒有 `claude`，`scripts/validate_env_contract.py` 也禁止部署設定
出現這個值。

**契約（呼叫端依賴，請勿變更）**

- 參數清單呼叫、不經 shell；prompt（含 system 內容）**一律走 stdin**，不上命令列
  ——命令列在 `ps` 看得到，而 system prompt 會夾帶使用者的架構圖。
  `--system-prompt` 傳的是本檔的固定字串，不含任何使用者內容。
- 子行程環境是**白名單**：只帶定位 CLI 登入狀態與網路所需的變數。
  `OPENROUTER_API_KEY`／`ANTHROPIC_*` 與後端自己的 `JWT_SECRET`／`DATABASE_URL` 等
  都不會傳下去；不靠逐項排除，新增的機密變數因此預設也傳不下去。
- `--tools ""` ＋ `--safe-mode`：CLI 在這裡只當模型用。沒有內建工具（prompt 含使用者
  輸入，不能讓它讀檔或跑指令），也不載入 CLAUDE.md、hook、MCP、plugin；工作目錄
  是系統暫存目錄，不是 repo。
- log 只記筆數、字元數、exit code、耗時；**不含 prompt 原文、不含 stderr 原文**。
  例外訊息是固定字串，因為 `review_agent`／`wa_lens_engine` 的 RuntimeError 會往上
  傳到回應裡。

**失敗分型**（對齊 `intent_routing_port.classify_transport_failure`，該函式不 import
本檔，以型別與類別名判斷）

| 情況 | 例外 | 路由層對應 |
|---|---|---|
| 逾時（子行程已被 kill） | `ClaudeCodeTimeout`（亦為 `TimeoutError`） | `LlmUnavailable` |
| 非零 exit、空輸出、非 JSON、CLI 回報錯誤 | `ClaudeCodeConnectionError` | `LlmUnavailable` |
| 強制工具呼叫但回應不含該工具 | `ClaudeCodeMalformedToolCall` | `MalformedRouting` |

訊息字串刻意避開用量字樣（`insufficient`／`quota`／`credit` 等）：那些字樣會讓
`classify_transport_failure` 判成 `LlmBudgetExceeded`。

**已知限制**：`temperature`／`max_retries` 在此路徑不起作用（CLI 沒有對應旗標，且
本類別不重試）；回應不串流，`stream_mode="messages"` 會拿到整段一次的結果。
含 `/` 的模型名（OpenRouter 的 `<vendor>/<model>` 格式）CLI 不認得，改用 CLI 預設
模型；要指定就設不含 `/` 的別名（例如 `LLM_MODEL=sonnet`）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool

logger = logging.getLogger("cloud360.claude_code_chat")

CLAUDE_EXECUTABLE: Final = "claude"

DEFAULT_TIMEOUT_SECONDS: Final = 60.0

#: `tool_choice` 正規化後代表「必須呼叫某個工具，哪個都可以」的值。
_ANY_TOOL: Final = "__any_tool__"

#: 取代 CLI 預設 system prompt 的固定字串。真正的 system 內容在 stdin 的 JSON 裡。
_CLI_SYSTEM_PROMPT: Final = (
    "You are a language model behind an API. You have no tools and no filesystem. "
    "Follow the instructions in the input exactly and reply with only what they ask for."
)

_PROMPT_INSTRUCTIONS: Final = (
    "Below is a conversation as a JSON array. Each item has a role "
    "(system, user, assistant or tool). Treat the system items as your instructions "
    "and write the next assistant turn."
)

_ENV_ALLOWLIST: Final = (
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "TMPDIR",
    "LANG",
    "TERM",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "XDG_STATE_HOME",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "SSL_CERT_FILE",
    "NODE_EXTRA_CA_CERTS",
    "CLAUDE_CONFIG_DIR",
)
_ENV_ALLOWED_PREFIXES: Final = ("LC_",)

_FENCED_BLOCK: Final = re.compile(r"^```[A-Za-z]*\s*(.*?)\s*```$", re.DOTALL)


class ClaudeCodeError(RuntimeError):
    """`claude` CLI 路徑的失敗。訊息是固定字串，可安全往上傳。"""


class ClaudeCodeTimeout(ClaudeCodeError, TimeoutError):
    """呼叫超過逾時上限；子行程已被 kill。"""


class ClaudeCodeConnectionError(ClaudeCodeError):
    """CLI 無法啟動、非零結束、輸出為空或不是預期的 JSON。"""


class ClaudeCodeMalformedToolCall(ClaudeCodeError):
    """要求呼叫工具，回應卻沒有該工具的呼叫（不得退成純文字）。"""


def _subprocess_env() -> dict[str, str]:
    """子行程環境：白名單，不是「複製後排除」（見模組 docstring）。"""
    return {
        key: value
        for key, value in os.environ.items()
        if key in _ENV_ALLOWLIST or key.startswith(_ENV_ALLOWED_PREFIXES)
    }


def _cli_model(model: Optional[str]) -> Optional[str]:
    """OpenRouter 格式的模型名 CLI 不認得，回 None 表示用 CLI 預設。"""
    name = (model or "").strip()
    if not name or "/" in name:
        return None
    return name


def _cli_args(executable: str, model: Optional[str]) -> list[str]:
    args = [
        executable,
        "-p",
        "--output-format",
        "json",
        "--safe-mode",
        "--no-session-persistence",
        "--tools",
        "",
        "--system-prompt",
        _CLI_SYSTEM_PROMPT,
    ]
    resolved = _cli_model(model)
    if resolved:
        args += ["--model", resolved]
    return args


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, Mapping) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return ""


def _message_payload(message: BaseMessage) -> dict[str, Any]:
    roles = {"system": "system", "human": "user", "ai": "assistant", "tool": "tool"}
    payload: dict[str, Any] = {
        "role": roles.get(message.type, message.type),
        "content": _content_text(message.content),
    }
    if isinstance(message, AIMessage) and message.tool_calls:
        payload["tool_calls"] = [
            {"name": call["name"], "args": call["args"]} for call in message.tool_calls
        ]
    if isinstance(message, ToolMessage):
        payload["tool_name"] = message.name
    return payload


def _tool_instructions(tools: Sequence[Mapping[str, Any]], tool_choice: Optional[str]) -> str:
    shape = '{"tool_calls":[{"name":"<tool name>","args":{...}}]}'
    if tool_choice == _ANY_TOOL:
        demand = "You MUST call one of the tools now."
    elif tool_choice:
        demand = f"You MUST call the tool named {tool_choice} now."
    else:
        demand = "Call a tool if the task needs one; otherwise reply in plain text."
    return (
        f"Available tools (OpenAI function format):\n{json.dumps(list(tools), ensure_ascii=False)}\n"
        f"{demand} To call a tool, reply with ONLY this JSON object and nothing else, "
        f"with args matching the tool's parameters: {shape}"
    )


def render_prompt(
    messages: Sequence[BaseMessage],
    tools: Optional[Sequence[Mapping[str, Any]]] = None,
    tool_choice: Optional[str] = None,
) -> str:
    """整段對話序列化成 stdin 內容。

    用 JSON 而不是角色標籤分隔：使用者內容裡出現任何看起來像標籤的字串都不會
    讓對話邊界錯位。
    """
    conversation = json.dumps(
        [_message_payload(message) for message in messages], ensure_ascii=False
    )
    sections = [_PROMPT_INSTRUCTIONS, conversation]
    if tools:
        sections.append(_tool_instructions(tools, tool_choice))
    return "\n\n".join(sections)


def _load_json_object(text: str) -> Any:
    stripped = text.strip()
    fenced = _FENCED_BLOCK.match(stripped)
    start, end = stripped.find("{"), stripped.rfind("}")
    candidates = [stripped]
    if fenced:
        candidates.append(fenced.group(1))
    if 0 <= start < end:
        candidates.append(stripped[start : end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def parse_tool_calls(text: str) -> Optional[list[dict[str, Any]]]:
    """解析 `{"tool_calls":[{"name":...,"args":{...}}]}`；不是這個形狀回 None。

    純函式，不讀環境、不連外（ADR-0006 的 property-based 測試落點）。整包任何一筆
    形狀不對就回 None，不做部分接受——只執行模型一半的工具呼叫比全部不執行更糟。
    """
    payload = _load_json_object(text)
    if not isinstance(payload, Mapping):
        return None
    raw_calls = payload.get("tool_calls")
    if not isinstance(raw_calls, list) or not raw_calls:
        return None
    calls: list[dict[str, Any]] = []
    for raw in raw_calls:
        if not isinstance(raw, Mapping):
            return None
        name, args = raw.get("name"), raw.get("args", {})
        if not isinstance(name, str) or not name.strip() or not isinstance(args, Mapping):
            return None
        calls.append({"name": name, "args": dict(args)})
    return calls


def _normalize_tool_choice(tool_choice: Any) -> Optional[str]:
    """None＝可不呼叫；`_ANY_TOOL`＝必須呼叫某個；其餘字串＝必須呼叫該工具。"""
    if tool_choice in (None, False, "auto", "none"):
        return None
    if tool_choice in (True, "any", "required"):
        return _ANY_TOOL
    if isinstance(tool_choice, str):
        return tool_choice
    if isinstance(tool_choice, Mapping):
        function = tool_choice.get("function")
        name = function.get("name") if isinstance(function, Mapping) else tool_choice.get("name")
        if isinstance(name, str) and name:
            return name
    raise ValueError(f"unsupported tool_choice: {tool_choice!r}")


def _tool_name(tool: Mapping[str, Any]) -> str:
    return str((tool.get("function") or {}).get("name") or "")


def _ai_message(
    text: str,
    tools: Optional[Sequence[Mapping[str, Any]]],
    tool_choice: Optional[str],
) -> AIMessage:
    if not tools:
        return AIMessage(content=text)
    calls = parse_tool_calls(text)
    if calls is None:
        if tool_choice is None:
            return AIMessage(content=text)
        raise ClaudeCodeMalformedToolCall("claude CLI 沒有回傳要求的工具呼叫")
    known = {_tool_name(tool) for tool in tools}
    wanted = known if tool_choice in (None, _ANY_TOOL) else {tool_choice}
    selected = [call for call in calls if call["name"] in wanted]
    if not selected:
        raise ClaudeCodeMalformedToolCall("claude CLI 沒有回傳要求的工具呼叫")
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": call["name"],
                "args": call["args"],
                "id": f"call_{uuid.uuid4().hex}",
                "type": "tool_call",
            }
            for call in selected
        ],
    )


def _kill_process_group(pid: int) -> None:
    """kill 整個行程群組：CLI 自己可能還有子行程，只 kill 它一個會留下孤兒。"""
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        logger.debug("claude CLI 行程群組已結束：pid=%s", pid)


def _result_text(returncode: int, stdout: bytes, stderr: bytes) -> str:
    if returncode != 0:
        logger.error(
            "claude CLI 非零結束：exit_code=%s stderr_bytes=%s", returncode, len(stderr)
        )
        raise ClaudeCodeConnectionError("claude CLI 執行失敗（可能尚未登入，請先執行 claude）")
    if not stdout.strip():
        logger.error("claude CLI 沒有輸出：stderr_bytes=%s", len(stderr))
        raise ClaudeCodeConnectionError("claude CLI 沒有回傳內容")
    try:
        payload = json.loads(stdout)
    except ValueError as exc:
        logger.error("claude CLI 輸出不是 JSON：stdout_bytes=%s", len(stdout))
        raise ClaudeCodeConnectionError("claude CLI 回傳了無法解析的內容") from exc
    result = payload.get("result") if isinstance(payload, Mapping) else None
    if isinstance(payload, Mapping) and payload.get("is_error"):
        logger.error("claude CLI 回報錯誤：subtype=%s", payload.get("subtype"))
        raise ClaudeCodeConnectionError("claude CLI 回報呼叫失敗（可能尚未登入，請先執行 claude）")
    if not isinstance(result, str) or not result.strip():
        logger.error("claude CLI 的 JSON 沒有文字結果：stdout_bytes=%s", len(stdout))
        raise ClaudeCodeConnectionError("claude CLI 沒有回傳內容")
    return result


class ClaudeCodeChatModel(BaseChatModel):
    """以 `claude -p` 當模型的 `BaseChatModel`（見模組 docstring）。"""

    cli_model: Optional[str] = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @property
    def _llm_type(self) -> str:
        return "claude-code-cli"

    def bind_tools(self, tools: Sequence[Any], *, tool_choice: Any = None, **kwargs: Any):
        if tool_choice == "none":
            return self.bind(**kwargs)
        formatted = [convert_to_openai_tool(tool) for tool in tools]
        normalized = _normalize_tool_choice(tool_choice)
        if normalized not in (None, _ANY_TOOL) and normalized not in {
            _tool_name(tool) for tool in formatted
        }:
            raise ValueError(f"tool_choice names an unbound tool: {normalized}")
        return self.bind(tools=formatted, tool_choice=normalized, **kwargs)

    def _executable(self) -> str:
        path = shutil.which(CLAUDE_EXECUTABLE)
        if path is None:
            logger.error("找不到 claude CLI")
            raise ClaudeCodeConnectionError("找不到 claude CLI，請確認它在後端行程的 PATH 上")
        return path

    def _finish(
        self,
        text: str,
        tools: Optional[Sequence[Mapping[str, Any]]],
        tool_choice: Optional[str],
        started: float,
        prompt_chars: int,
    ) -> ChatResult:
        message = _ai_message(text, tools, tool_choice)
        logger.info(
            "claude CLI 完成：prompt_chars=%s result_chars=%s tool_calls=%s elapsed_ms=%d",
            prompt_chars,
            len(text),
            len(message.tool_calls),
            (time.monotonic() - started) * 1000,
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> ChatResult:
        started = time.monotonic()
        prompt = render_prompt(messages, tools, tool_choice)
        try:
            process = subprocess.Popen(
                _cli_args(self._executable(), self.cli_model),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_subprocess_env(),
                cwd=tempfile.gettempdir(),
                start_new_session=True,
            )
        except OSError as exc:
            logger.error("claude CLI 無法啟動：%s", type(exc).__name__)
            raise ClaudeCodeConnectionError("claude CLI 無法啟動") from exc
        try:
            stdout, stderr = process.communicate(
                prompt.encode("utf-8"), timeout=self.timeout_seconds
            )
        except subprocess.TimeoutExpired as exc:
            _kill_process_group(process.pid)
            process.communicate()
            logger.error("claude CLI 逾時：timeout_seconds=%s", self.timeout_seconds)
            raise ClaudeCodeTimeout("claude CLI 呼叫逾時") from exc
        except BaseException:
            _kill_process_group(process.pid)
            process.wait()
            raise
        text = _result_text(process.returncode, stdout, stderr)
        return self._finish(text, tools, tool_choice, started, len(prompt))

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        tools: Optional[Sequence[Mapping[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> ChatResult:
        started = time.monotonic()
        prompt = render_prompt(messages, tools, tool_choice)
        try:
            process = await asyncio.create_subprocess_exec(
                *_cli_args(self._executable(), self.cli_model),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_subprocess_env(),
                cwd=tempfile.gettempdir(),
                start_new_session=True,
            )
        except OSError as exc:
            logger.error("claude CLI 無法啟動：%s", type(exc).__name__)
            raise ClaudeCodeConnectionError("claude CLI 無法啟動") from exc
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(prompt.encode("utf-8")), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            _kill_process_group(process.pid)
            await process.wait()
            logger.error("claude CLI 逾時：timeout_seconds=%s", self.timeout_seconds)
            raise ClaudeCodeTimeout("claude CLI 呼叫逾時") from exc
        except BaseException:
            # 含 CancelledError：SSE 用戶端斷線時不能留下一個還在跑的 CLI。
            _kill_process_group(process.pid)
            await process.wait()
            raise
        text = _result_text(process.returncode, stdout, stderr)
        return self._finish(text, tools, tool_choice, started, len(prompt))


__all__ = [
    "CLAUDE_EXECUTABLE",
    "ClaudeCodeChatModel",
    "ClaudeCodeConnectionError",
    "ClaudeCodeError",
    "ClaudeCodeMalformedToolCall",
    "ClaudeCodeTimeout",
    "parse_tool_calls",
    "render_prompt",
]
