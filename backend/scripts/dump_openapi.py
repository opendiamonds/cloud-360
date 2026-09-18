#!/usr/bin/env python3
"""把 FastAPI 應用的 OpenAPI 規格 dump 成 repo 根目錄的 `openapi.json`（C-8）。

**為何規格檔在 repo 根而不在 `frontend/public/`**：`frontend/nginx.conf` 是
`root /usr/share/nginx/html` + `try_files $uri`，而 Vite 會把 `public/` 原樣複製
進 `dist/`。規格檔落在那裡等於把完整的 API 地圖（含全部使用者管理與權限端點）
對未認證訪客公開。目前後端自帶的規格端點在公網不可達（nginx 只反向代理
`/api/`），本腳本不得破壞這個既有狀態。

**為何從程式碼而非 live 端點取得**：CI 的 frontend job 是獨立的，後端不在該 job
中運行。規格可在不啟動服務、不連資料庫的前提下取得（連線引擎為惰性建立）。

**決定性**：同一組依賴版本下輸出為位元決定性；跨版本會飄，故 `requirements.txt`
對 `fastapi` 與 `pydantic` 採**精確等值**釘選。升版這兩支時必須在同一個 PR 內
重新 dump 並 commit。

用法（於 `backend/` 目錄）：
    python scripts/dump_openapi.py           # 寫入 ../openapi.json
    python scripts/dump_openapi.py --check   # 只比對，不一致則 exit 1（CI 用）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SPEC_PATH = REPO_ROOT / "openapi.json"

# 與 tests/helpers.py 相同的前置：CI 與部分主機沒有 psycopg2 驅動，而本腳本
# 只需要 import 應用、不需要真的連線。
sys.modules.setdefault("psycopg2", MagicMock())
for path in (BACKEND_DIR, BACKEND_DIR / "services"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def render_spec() -> str:
    from main import app

    # sort_keys 讓輸出與 dict 插入順序無關；ensure_ascii=False 讓中文 description
    # 以原字元存放（diff 可讀）；結尾換行符合一般文字檔慣例。
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="只比對 committed 的規格檔與重新產生的結果，不寫入",
    )
    args = parser.parse_args()

    rendered = render_spec()

    if not args.check:
        SPEC_PATH.write_text(rendered, encoding="utf-8")
        print(f"已寫入 {SPEC_PATH.relative_to(REPO_ROOT)}")
        return 0

    if not SPEC_PATH.exists():
        print(
            f"規格檔不存在：{SPEC_PATH.relative_to(REPO_ROOT)}\n"
            "請於 backend/ 執行 `python scripts/dump_openapi.py` 並 commit 產出。",
            file=sys.stderr,
        )
        return 1

    committed = SPEC_PATH.read_text(encoding="utf-8")
    if committed == rendered:
        print("規格檔與後端程式碼一致。")
        return 0

    print(
        f"規格檔已漂移：{SPEC_PATH.relative_to(REPO_ROOT)} 與後端程式碼不一致。\n"
        "後端的 API 形狀改了但規格檔沒重新產生。請於 backend/ 執行\n"
        "  python scripts/dump_openapi.py\n"
        "並把產出與**重新產生的前端型別檔**一併 commit（見 frontend 的 gen:types）。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
