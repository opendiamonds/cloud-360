"""startup.py — 啟動時載入並自我驗證三份進版控檔（`BR71.5`；functional-design 審查 R-12 擇 (a)、nfr-design 審查 R-07）。

讀 `generated_tools.json`、`agents.json`、`allowlist.json`（本套件唯一的 `open(`）。任何 I/O、編碼、JSON 解析或
結構錯誤，以及 `validate_tool_specs` 的違規，一律包成 `StartupConfigError(subject)`：`subject` 只是違規的
工具名、agent 名或檔名常數，不含其他內容。設定錯誤是致命錯誤——不得帶病上線（與 `BR71.4` 刻意不同）。

本模組不 import `mcp`、`httpx`；不讀環境變數。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agents import AgentRegistry
from .generator import (
    Allowlist, AllowlistFormatError, GeneratorError, ToolSpec, load_specs, parse_allowlist,
    validate_tool_specs,
)

PACKAGE_DIR = Path(__file__).resolve().parent
GENERATED_TOOLS_FILE = "generated_tools.json"
AGENTS_FILE = "agents.json"
ALLOWLIST_FILE = "allowlist.json"


class StartupConfigError(Exception):
    """致命的啟動設定錯誤；`subject` 為工具名、agent 名或檔名常數。"""

    def __init__(self, subject: str) -> None:
        super().__init__(subject)
        self.subject = subject


@dataclass(frozen=True)
class LoadedConfig:
    tool_specs: tuple[ToolSpec, ...]
    registry: AgentRegistry
    allowlist: Allowlist


def _read_json(config_dir: Path, filename: str) -> Any:
    try:
        with open(config_dir / filename, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise StartupConfigError(filename) from exc


def load_and_validate(config_dir: Path = PACKAGE_DIR) -> LoadedConfig:
    config_dir = Path(config_dir)
    tools_doc = _read_json(config_dir, GENERATED_TOOLS_FILE)
    agents_doc = _read_json(config_dir, AGENTS_FILE)
    allowlist_doc = _read_json(config_dir, ALLOWLIST_FILE)
    try:
        allowlist = parse_allowlist(allowlist_doc)
    except AllowlistFormatError as exc:
        raise StartupConfigError(str(exc) or ALLOWLIST_FILE) from exc
    try:
        specs = load_specs(tools_doc)
    except ValueError as exc:
        raise StartupConfigError(GENERATED_TOOLS_FILE) from exc
    try:
        validate_tool_specs(specs, allowlist)
    except GeneratorError as exc:
        raise StartupConfigError(exc.tool_name) from exc
    try:
        registry = AgentRegistry.from_mapping(agents_doc)
    except ValueError as exc:
        raise StartupConfigError(str(exc) or AGENTS_FILE) from exc
    return LoadedConfig(tool_specs=specs, registry=registry, allowlist=allowlist)
