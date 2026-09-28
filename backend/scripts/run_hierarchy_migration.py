#!/usr/bin/env python3
"""U4 `hierarchy-data` 的一次性遷移指令（部署期執行，**不在啟動路徑上**）。

為什麼是獨立指令而不是啟動副作用（`Q2=A`）
------------------------------------------

`backend/database.py` 的 `init_db()` 由 `main.py` 的 startup 事件同步呼叫，而它
整段包在 `except Exception: logger.error` 裡——遷移掛在那裡的話，失敗會變成一行
日誌加一個**看起來正常啟動**的服務。本指令的失敗以**非零結束碼**收場
（`U4-V4`），部署腳本因此擋得住。

用法（於 `backend/` 目錄，且 `DATABASE_URL` 已指向目標資料庫）::

    python scripts/run_hierarchy_migration.py

預期輸出為三個計數（`BR2.6`）；結束碼 0 表示終檢通過
（`user_diagrams` 中 `system_id IS NULL` 的列數為 0）。

**前置條件：應用不得在遷移期間接流量**（`U4-V6`）。現行
`.github/workflows/deploy.yml` 以單一 `up -d --build` 一次拉起整座 stack，
**沒有任何一點是 db 起來而 backend 沒起來的**，所以這個有序窗口目前**尚無承載
者**（`S-9`）。細節與手動操作步驟見 `DEPLOY.md` 第 2.2.7 節。

**重跑安全**：DDL 為 `IF NOT EXISTS` 形狀，資料面以 `system_id IS NOT NULL`
為冪等判準（`BR2.2`）。中途失敗留下的「部分使用者已遷移」是合法可恢復狀態，
重跑即補完（`S-8`）。
"""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
for _path in (BACKEND_DIR, BACKEND_DIR / "services"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from database import SessionLocal  # noqa: E402
from services.hierarchy_migration import migrate_hierarchy  # noqa: E402

logger = logging.getLogger("cloud360.hierarchy_migration")


def main(argv: list[str] | None = None) -> int:
    """執行遷移。回傳 0（成功）或 1（任何失敗）。

    `argv` 目前不接受任何選項；保留參數是為了讓測試能以同一個簽章呼叫，
    並讓未來新增 `--dry-run` 這類旗標時不改呼叫端。
    """
    if argv:
        print(f"未知的參數：{argv}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    db = SessionLocal()
    try:
        counts = migrate_hierarchy(db)
    except Exception as exc:
        # 不吞：訊息與完整 traceback 都寫到 stderr，並以非零結束碼收場（U4-V4）。
        # 這裡之所以攔下例外而不是讓它逃出 main()，只是為了輸出一行可讀的結論；
        # 資訊沒有任何損失。
        logger.error("hierarchy migration 失敗：%s", exc)
        traceback.print_exc(file=sys.stderr)
        print(
            "遷移未完成。已 commit 的使用者保留其進度，"
            "處置後重跑即補完（S-8）。",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    print("hierarchy migration 完成：")
    print(f"  處理的使用者數        users_processed       = {counts.users_processed}")
    print(f"  新建的預設專案／系統組 default_pairs_created = {counts.default_pairs_created}")
    print(f"  改寫的架構圖數        diagrams_assigned     = {counts.diagrams_assigned}")
    print("終檢通過：user_diagrams 中 system_id IS NULL 的列數為 0（AC9.1.4）。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
