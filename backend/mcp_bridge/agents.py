"""agents.py — agent 宣告與代寫組對照（`BR74.1`–`BR74.3`、`BR77.1`）。

agent 身分以每次請求的 `X-Cloud360-Agent` 標頭宣告；`agents.json` 是「agent 名 → 代寫組」的
白名單（`BR74.2`）。寫入與清空工具要求已登錄的宣告，讀取不要求（`BR74.3`）。**這不是授權**：
它只決定 `on_behalf_of` 填什麼，授權完全在 backend（`BR75.1`）。

log 的 `agent` 欄只取已登錄名、`undeclared`、`unregistered`，呼叫端的原值永不入 log（`BR77.1`）。

純函式模組：不 import `mcp`、`httpx`、`sqlalchemy`、`fastapi`（`NFR21.40`）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional, Sequence

from .calls import SEGMENT_PATTERN  # 代寫組就是路徑上的 agent_group，樣式同一份

#: `agents.json` 的鍵格式（`entities.md` `AgentRegistry`）。
AGENT_NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")

UNDECLARED = "undeclared"
UNREGISTERED = "unregistered"


class AgentNotDeclared(Exception):
    """寫入或清空時沒有已登錄的 agent 宣告。訊息固定，不含宣告值。"""

    def __init__(self) -> None:
        super().__init__("agent_not_declared")


@dataclass(frozen=True)
class AgentRegistry:
    """已登錄 agent 名 → 代寫組；不可變。"""

    agents: Mapping[str, str]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, str]) -> "AgentRegistry":
        """驗證並建立登錄表；不合格回 `ValueError`，訊息只含違規的 agent 名（已通過格式者）。"""
        if not isinstance(mapping, Mapping):
            raise ValueError("agents.json")
        checked = {}
        for name, group in mapping.items():
            if not isinstance(name, str) or AGENT_NAME_PATTERN.fullmatch(name) is None:
                raise ValueError("agents.json")
            if not isinstance(group, str) or SEGMENT_PATTERN.fullmatch(group) is None:
                raise ValueError(name)
            checked[name] = group
        return cls(agents=MappingProxyType(dict(sorted(checked.items()))))


@dataclass(frozen=True)
class AgentResolution:
    """`group` 為要填入 `on_behalf_of` 的代寫組（讀取未宣告時為 `None`）；`log_name` 供 log。"""

    group: Optional[str]
    log_name: str


def normalize_agent(values: Sequence[str], registry: AgentRegistry) -> str:
    """log 用：已登錄名、`undeclared`（缺標頭）或 `unregistered`（其餘一切）。"""
    if len(values) == 0:
        return UNDECLARED
    if len(values) == 1 and values[0] in registry.agents:
        return values[0]
    return UNREGISTERED


def resolve_agent(values: Sequence[str], registry: AgentRegistry,
                  requires_agent: bool) -> AgentResolution:
    """`BR74.3`：寫入與清空要求已登錄的宣告，否則拋 `AgentNotDeclared`。"""
    log_name = normalize_agent(values, registry)
    if log_name in (UNDECLARED, UNREGISTERED):
        if requires_agent:
            raise AgentNotDeclared()
        return AgentResolution(group=None, log_name=log_name)
    return AgentResolution(group=registry.agents[log_name], log_name=log_name)
