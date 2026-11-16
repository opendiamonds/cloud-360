"""dispatch.py — 一次 `tools/call` 的執行骨架（MB-W3 第 2–7 步；`BR73.1`、`BR74.3`、`BR75.4`、`BR76.1`、`BR77.1`）。

`run_tool_call` 是 `tool_call` 那一行 log 的**唯一寫出點**（在自己的 `finally` 中，恰一行）。所有分支——
未知工具、本地拒絕、backend 各狀態、回應過大、未預期例外——都經同一個 `finally`。

- 以 `except Exception` **總攔截**：未預期例外一律回 `internal_error`（固定訊息），log 只另記例外**型別名**。
  Step 1 實測（S-9）：SDK 2.3.0 在舊式協定版本下會把處理函式拋出的例外字串原樣送回 client，所以這道
  總攔截是唯一防線。`asyncio.CancelledError` 屬 `BaseException`，不攔，照常傳遞。
- 16-A（Step 1 的 K-6）：client 斷線不會取消處理函式，內層 ASGI 呼叫等處理函式完成才返回，故**不用**
  `asyncio.shield`；並行閘在 `finally` 歸還名額時交換已結束（CC-6）。
- 驗證順序固定：工具名 → 憑證 → agent → 參數 → 組請求；前四步任一失敗都不建立 `BackendCall`，
  「backend 收到 0 筆」由結構保證。
- `exchange` 以注入取得（`NFR21.29` 的替身可在主直譯器構造）。

本模組不 import `mcp`、`httpx`。
"""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence

from . import calls
from .agents import AgentNotDeclared, AgentRegistry, normalize_agent, resolve_agent
from .credentials import RequestCredential, parse_credential
from .generator import ToolSpec
from .observability import log_internal_failure, log_tool_call, normalize_tool
from .outcomes import (
    ExchangeResult, ToolOutcome, agent_not_declared, internal_error, invalid_argument, map_outcome,
    unauthenticated_local, unknown_tool,
)

Exchange = Callable[[calls.BackendCall, RequestCredential], Awaitable[ExchangeResult]]


async def run_tool_call(
    spec: Optional[ToolSpec],
    arguments: Any,
    authorization: Sequence[str],
    agent_header: Sequence[str],
    exchange: Exchange,
    *,
    registry: AgentRegistry,
    requested_name: object = None,
) -> ToolOutcome:
    """執行一次工具呼叫並寫出恰一行 `tool_call`。永不拋出 `Exception`。

    `requested_name` 是呼叫端送來的工具名原值；log 只記它的正規化結果（已宣告名或 `unknown`，
    nfr-requirements 審查 R-06），原值永不入 log。
    """
    started = time.monotonic()
    declared = (spec.name,) if spec is not None else ()
    tool = normalize_tool(spec.name if spec is not None else requested_name, declared)
    agent = normalize_agent(tuple(agent_header), registry)
    outcome: Optional[ToolOutcome] = None
    try:
        outcome = await _execute(spec, arguments, tuple(authorization), tuple(agent_header),
                                 exchange, registry)
        return outcome
    except Exception as exc:  # 總攔截：例外文字永不外流（`BR73.4`、`BR76.3`）
        log_internal_failure(type(exc).__name__)
        outcome = internal_error()
        return outcome
    finally:
        log_tool_call(
            tool=tool,
            agent=agent,
            outcome=outcome.outcome_label if outcome is not None else "internal_error",
            http_status=outcome.http_status if outcome is not None else None,
            duration_ms=int((time.monotonic() - started) * 1000),
        )


async def _execute(spec, arguments, authorization, agent_header, exchange,
                   registry) -> ToolOutcome:
    if spec is None:
        return unknown_tool()
    credential = parse_credential(authorization)
    if credential is None:
        return unauthenticated_local()
    try:
        resolution = resolve_agent(agent_header, registry, spec.requires_agent)
    except AgentNotDeclared:
        return agent_not_declared()
    try:
        accepted = calls.validate_arguments(spec, arguments)
        call = calls.build_backend_call(spec, accepted, resolution.group)
    except calls.ArgumentRejected as rejected:
        return invalid_argument(rejected.message)
    result = await exchange(call, credential)
    outcome = map_outcome(result)
    if outcome.ok:
        # 程式審查 R-05：先在總攔截之內確認成功本體可序列化（與 app 的轉換同一組參數），
        # 使「log 記 ok、client 卻拿到例外」不會發生；失敗即落到總攔截成為 internal_error。
        json.dumps(outcome.payload, ensure_ascii=False, sort_keys=True)
    return outcome


def declared_tool(specs_by_name: Mapping[str, ToolSpec], name: object) -> Optional[ToolSpec]:
    """依工具名找已載入的宣告；不是字串或未宣告回 `None`。"""
    return specs_by_name.get(name) if isinstance(name, str) else None
