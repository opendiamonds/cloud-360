#!/usr/bin/env python3
"""`U19 membership-service` 的成員回填（既有專案的擁有者列）——**手動補跑用**。

**2026-10-20 起（合併前必修第 15 項，使用者裁決）後端啟動時會自動執行同一份
補齊**：`backend/main.py` 的 startup 在 `init_db()` 之後呼叫
`services/membership_backfill.ensure_project_members_on_startup()`，失敗即讓啟動
失敗。本指令保留為**手動補跑／事前檢查**用途（`--dry-run` 可在不寫入的情況下
報告零成員專案數），邏輯與啟動路徑是**同一份**（`services/membership_backfill.py`），
不各寫一份 SQL。仍**不動 `backend/database.py`**（`NFR12.5`）。

下面「為什麼是獨立腳本」一節是原設計的理由，保留作為歷史脈絡；它描述的
「不動啟動路徑」已被上述裁決取代。

為什麼非做不可（`NFR12.24`／`NFR12.25`）
----------------------------------------

`project_members` 是全新表（契約 `K-15` 的 `observable_side_effects` 逐字「不含
任何資料寫入」），而既有專案全部由 `services/hierarchy_migration.py` 建立且
**從未寫過任何成員列**。故**每一個既有專案今天都是零成員**。

後果鏈：`resolve_project_role` 對既有專案的任何使用者（**包括該專案真正的
owner**）查無列 → 回 `None` → `BR1.6` 要求當成拒絕 → 任何消費端
（`U20`／`U13`／`U21`／`U24`）上線時，既有專案的擁有者會被判定為**非成員**
而被拒絕存取自己的專案。

**第一次部署不會鎖人在外面**，而這一點必須寫清楚以免被誤讀成「不急」：
`U23` 落地後專案清單改讀成員列；擁有者只在零成員列時可見，故回填未跑時擁有者
仍看得到自己的專案，但需求籤與成員頁會拒絕他（`U23` 之前此處寫的是「`list_projects`
為 owner-scoped、既有列表路徑不經本單元」，已不成立）；零成員列時 `assert_can_deactivate` 的
`HAVING count(*) = 1` 找不到任何專案，故它**放行**（方向是過寬而非過嚴）。
**真正會鎖人在外面的時點是第一個消費端上線時**——這就是 `NFR12.25` 逐字要求
「回填必須在任何消費端上線之前」的理由（`OPEN-ID19-2`）。

為什麼是獨立腳本（沿用 `U18` 的 `[P1]`=A 先例）
----------------------------------------------

`database.py` 的 `_ensure_*` 補丁家族**全部吞掉失敗**（`except Exception` ＋
`logger.warning` 後繼續），照抄那個形狀的後果是「回填沒跑而服務照常啟動」。
把補丁改成 re-raise 也不行：`restart: unless-stopped` 之下任何失敗會變成
**重啟迴圈**。所以走獨立指令、**大聲失敗**（非零結束碼）、不動啟動路徑。

**刻意不與 `U18` 的 `run_meta_schema_migration.py` 合併**（`OPEN-N19-4` 的定案）：
那一支目前**純 DDL、無資料寫入**，而那正是它能單一交易並自我終檢的前提。
把資料動作混進去會讓「結束碼 0 代表什麼」這句話同時涵蓋兩種不同的保證。

用法（於 `backend/` 目錄，且 `DATABASE_URL` 已指向目標資料庫）::

    python scripts/backfill_project_members.py
    python scripts/backfill_project_members.py --dry-run   # 只報告，不寫入

**前置條件**：`U18` 的 `python scripts/run_meta_schema_migration.py` 必須**先**
跑過（`project_members` 要先存在）。本腳本會先檢查並以可讀訊息擋下，而不是丟
一個生的 `UndefinedTable`。完整的三步順序見 `DEPLOY.md` 第 2.2.10 節。

單一交易 ＋ 自我終檢，所以結束碼可被信任
----------------------------------------

    結束碼 0  ⟺  `projects` 中**沒有任何**零成員的專案

終檢在 COMMIT **之前**執行；不為 0 即 rollback ＋ 非零碼。
**冪等**（以「該專案無任何成員列」為條件），故重跑安全——`BR4.3` 以外的第二個
冪等落點，而它的理由相同：手動步驟一定會被重跑。

輸出的禁令
----------

**本腳本不得輸出 `DATABASE_URL` 或其任何片段**（`project.md` 的機敏資料禁令；
本 repo 為 public 且 Actions log 公開可讀）。要指出連線目標時只印**主機與
資料庫名**，與 `run_meta_schema_migration.py` 同一形狀。
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

for _path in (BACKEND_DIR, BACKEND_DIR / "services"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from database import engine  # noqa: E402
from services.membership_backfill import (  # noqa: E402
    ROLE_PROJECT_ADMIN,
    run_backfill,
)

logger = logging.getLogger("cloud360.membership_backfill")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="U19 一次性成員回填")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只報告零成員專案數，不寫入（交易一律回滾）",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    url = engine.url
    print(f"目標資料庫：host={url.host} database={url.database}", flush=True)

    try:
        # 前置檢查、計數、插入、**COMMIT 之前的自我終檢**全在 `run_backfill` 的
        # 單一交易內——與後端啟動時執行的是同一份程式。
        result = run_backfill(engine, dry_run=args.dry_run)
    except Exception as exc:
        # **不吞**：訊息與完整 traceback 都寫到 stderr，並以非零結束碼收場。
        # 這與 `backend/database.py` 的 `_ensure_*` 家族刻意相反。
        logger.error("成員回填失敗：%s", exc)
        traceback.print_exc(file=sys.stderr)
        print(
            "回填未完成，交易已回滾——資料庫維持本次執行之前的狀態。"
            "處置後重跑即可（以「無任何成員列」為條件，故重跑安全）。",
            file=sys.stderr,
        )
        return 1

    print(f"回填前的零成員專案數：{result.before}", flush=True)
    if result.dry_run:
        print(
            f"--dry-run：將插入 {result.before} 列 "
            f"(project_id, owner_user_id, {ROLE_PROJECT_ADMIN}, CURRENT_TIMESTAMP)，"
            "本次不寫入。"
        )
        print("--dry-run 完成，交易已回滾。")
        return 0

    print("成員回填完成（U19）：")
    print(f"  插入列數            {result.inserted}")
    print("  終檢通過：projects 中零成員的專案數為 0（NFR12.24）。")
    print(
        "注意：本指令**不**處理「已有成員但 owner 不在其中」的專案"
        "——那是人為決定的結果，回填不得把他加回去。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
