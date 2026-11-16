#!/usr/bin/env python3
"""由 `openapi.json` ＋ `allowlist.json` 產生 MCP 工具宣告 `generated_tools.json`（`BR72.9`；`U21 mcp-bridge`）。

**讀取的輸入集合是封閉的**：作為產生器輸入讀取的檔案恰為 repo 根目錄的 `openapi.json` 與
`backend/mcp_bridge/allowlist.json`。`generated_tools.json` 是**輸出**：寫出模式以寫入開啟它，`--check` 模式
以讀取開啟它僅為逐位元比對，內容不回流成產生器的輸入。任何模式都不開啟 repo 根目錄的 `.mcp.json`
或其他 MCP 設定檔（`X-04` 的 scope_exclusion）。

本腳本只 import 純函式模組 `mcp_bridge.generator`：不 import `main`、`mcp`、`httpx`，不讀環境變數（CC-2）。
所以 CI 的漂移閘門紅燈只能代表「產物與輸入不一致」，不會因為別處壞掉而變紅。

用法（於 `backend/` 目錄）：
    python scripts/gen_mcp_tools.py           # 寫出 mcp_bridge/generated_tools.json
    python scripts/gen_mcp_tools.py --check   # 只比對，不一致則 exit 1（CI 用）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
OPENAPI_PATH = REPO_ROOT / "openapi.json"
ALLOWLIST_PATH = BACKEND_DIR / "mcp_bridge" / "allowlist.json"
OUTPUT_PATH = BACKEND_DIR / "mcp_bridge" / "generated_tools.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp_bridge.generator import (  # noqa: E402  sys.path 設定之後才能匯入
    AllowlistFormatError, GeneratorError, dump_specs, generate_tools, parse_allowlist,
)


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def render() -> str:
    openapi = _read_json(OPENAPI_PATH)
    allowlist = parse_allowlist(_read_json(ALLOWLIST_PATH))
    return dump_specs(generate_tools(openapi, allowlist))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="只比對 generated_tools.json 與重產結果，不一致則 exit 1")
    args = parser.parse_args(argv)
    try:
        expected = render()
    except GeneratorError as err:
        print(f"MCP 工具宣告產生失敗：{err.code}（{err.tool_name}）", file=sys.stderr)
        return 1
    except AllowlistFormatError as err:
        print(f"allowlist.json 結構不合：{err}", file=sys.stderr)
        return 1
    if args.check:
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
                current = handle.read()
        except FileNotFoundError:
            current = ""
        if current != expected:
            print("mcp_bridge/generated_tools.json 與 openapi.json ＋ allowlist.json 不一致。"
                  "請在 backend/ 執行 python scripts/gen_mcp_tools.py 後 commit。", file=sys.stderr)
            return 1
        print("MCP 工具宣告與輸入一致。")
        return 0
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(expected)
    print(f"已寫入 {OUTPUT_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
