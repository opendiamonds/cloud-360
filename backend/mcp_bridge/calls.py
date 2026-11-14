"""calls.py — 工具參數驗證與 backend 請求計畫（`BR75.4`、`BR74.4`、`BR74.6`）。

- 不依賴 client 遵守 `inputSchema`：參數鍵集合 ⊆ 宣告集合、required 全在、型別皆為 string。
- 路徑段只由通過字元集白名單的值組成：`system_id` 須符合 `SYSTEM_ID_PATTERN`，其餘路徑參數
  （`agent_group`、`field`）須符合 `SEGMENT_PATTERN`——其字串與 `U20` 的鍵格式正本 `KEY_PATTERN`
  **逐字相同**（以測試鎖住，T-7）。一律以 `.fullmatch()` 判定（functional-design 審查 R-13：
  `$` 在結尾換行之前也能匹配，`.match()` 會放行 `"cost\\n"`）。
- 百分比編碼（`quote(s, safe="")`）只是縱深防禦；安全性來自白名單（審查 R-01：httpx 會正規化
  dot-segment）。
- `build_backend_call` 的輸出**不含 token**：純函式永遠看不到使用者憑證。
- 錯誤訊息是固定文字，只可提及**已宣告的**參數名，從不回顯值或未宣告的鍵。

純函式模組：不 import `mcp`、`httpx`、`sqlalchemy`、`fastapi`（`NFR21.40`）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import quote

from .generator import ToolSpec

#: 路徑段字元集白名單；字串必須等於 `requirement_field_definitions.KEY_PATTERN.pattern`。
SEGMENT_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
#: `system_id`：十進位整數字串（backend 在授權之後才判非整數為 404，bridge 提前擋）。
SYSTEM_ID_PATTERN = re.compile(r"^[0-9]{1,18}$")

#: 個別路徑參數（工具名）使用的樣式；未列者一律 `SEGMENT_PATTERN`。
PATH_PARAM_PATTERNS: Mapping[str, re.Pattern] = {"system_id": SYSTEM_ID_PATTERN}

MSG_UNDECLARED_ARGUMENT = "參數不被接受：含未宣告的參數"
MSG_BLANK_VALUE = "value 不得為空；要清空欄位請用 clear_requirement_field"


class ArgumentRejected(Exception):
    """參數不合格；`message` 為可直接回給 agent 的固定文字。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class BackendCall:
    """一次對 backend 的請求計畫；不含 `Authorization`。"""

    method: str
    path: str
    json_body: Optional[dict]
    query: tuple[tuple[str, str], ...] = ()


def _invalid(name: str) -> ArgumentRejected:
    return ArgumentRejected(f"參數不合格：{name}")


def validate_arguments(spec: ToolSpec, arguments: Any) -> dict[str, str]:
    """`BR75.4`／`BR74.6`：回傳通過驗證的參數；不合格拋 `ArgumentRejected`。"""
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, Mapping):
        raise ArgumentRejected(MSG_UNDECLARED_ARGUMENT)
    properties = spec.input_schema.get("properties", {})
    declared = set(properties)
    if not set(arguments) <= declared:
        raise ArgumentRejected(MSG_UNDECLARED_ARGUMENT)
    required = set(spec.input_schema.get("required", []))
    for name in sorted(required):
        if name not in arguments:
            raise _invalid(name)
    path_params = spec.binding["path_params"]
    body_params = spec.binding["body_params"]
    accepted: dict[str, str] = {}
    for name in sorted(arguments):
        value = arguments[name]
        if not isinstance(value, str):
            raise _invalid(name)
        if name in path_params:
            pattern = PATH_PARAM_PATTERNS.get(name, SEGMENT_PATTERN)
            if pattern.fullmatch(value) is None:
                raise _invalid(name)
        elif name in body_params:
            if name in required and not value.strip():
                if name == "value":
                    raise ArgumentRejected(MSG_BLANK_VALUE)
                raise _invalid(name)
        accepted[name] = value
    return accepted


def build_backend_call(spec: ToolSpec, arguments: Mapping[str, str],
                       agent_group: Optional[str]) -> BackendCall:
    """組請求計畫：路徑樣板代入（反向映射回 API 名，`BR72.5`）、本體與注入（`BR74.4`）。

    呼叫前必須已通過 `validate_arguments`；本函式再對路徑段做一次白名單檢查，
    使「未驗證即組路徑」在結構上不可能產生 dot-segment。
    """
    binding = spec.binding
    path = binding["path"]
    for tool_name, api_name in binding["path_params"].items():
        value = arguments[tool_name]
        pattern = PATH_PARAM_PATTERNS.get(tool_name, SEGMENT_PATTERN)
        if pattern.fullmatch(value) is None:
            raise _invalid(tool_name)
        path = path.replace("{" + api_name + "}", quote(value, safe=""))
    query = tuple(
        (api_name, arguments[tool_name])
        for tool_name, api_name in sorted(binding["query_params"].items())
        if tool_name in arguments
    )
    body: Optional[dict] = None
    if binding["body_params"] or binding["inject"]:
        body = {api_name: arguments[tool_name]
                for tool_name, api_name in binding["body_params"].items()
                if tool_name in arguments}
        for api_name, source in binding["inject"].items():
            if source != "agent_group_of_declared_agent" or agent_group is None:
                raise ArgumentRejected("缺少可注入的 agent 代寫組")
            body[api_name] = agent_group
    return BackendCall(method=binding["method"], path=path, json_body=body, query=query)
