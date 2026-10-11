#!/usr/bin/env python3
"""`U19 membership-service` 的一次性成員回填（既有專案的擁有者列）。

**部署期執行，不在啟動路徑上**（`NFR12.5`：`backend/database.py` 的 diff 為空）。

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
本單元的消費端都在後續 Bolt，而 `hierarchy_facade.list_projects` 目前是
**owner-scoped**（讀 `projects.owner_user_id`，不讀 `project_members`），故
既有的專案列表路徑不經本單元；零成員列時 `assert_can_deactivate` 的
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

logger = logging.getLogger("cloud360.membership_backfill")

REQUIRED_TABLES = ("projects", "project_members")

ROLE_PROJECT_ADMIN = "project_admin"
"""刻意以字面值而非 import `membership_types`：本腳本只需要一個字串，而
`project_members.role` 的 DDL CHECK 是它的權威來源。值若與那條 CHECK 不符，
INSERT 會**當場失敗**（而非靜默寫入壞資料），所以這不是一份會無聲漂移的副本。"""


def _scalar(conn, sql: str, params: dict | None = None):
    from sqlalchemy import text

    return conn.execute(text(sql), params or {}).scalar()


def assert_prerequisites(conn) -> None:
    missing = [
        name
        for name in REQUIRED_TABLES
        if not _scalar(
            conn,
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t",
            {"t": name},
        )
    ]
    if missing:
        raise RuntimeError(
            "前置條件不足：public schema 缺少 " + "、".join(missing) + "。"
            "project_members 由 U18 的腳本建立，故它必須先跑過："
            "cd backend && python scripts/run_meta_schema_migration.py"
            "（見 DEPLOY.md 第 2.2.9 節）"
        )


def count_member_less_projects(conn) -> int:
    """零成員專案數。終檢與事前報告共用同一個查詢，故兩者不可能對不起來。"""
    return int(
        _scalar(
            conn,
            "SELECT count(*) FROM projects p "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM project_members m WHERE m.project_id = p.id"
            ")",
        )
        or 0
    )


def backfill(conn) -> int:
    """為每個零成員專案插入一列 `(project_id, owner_user_id, project_admin, now())`。

    回傳插入的列數。

    **以「該專案無任何成員列」為條件**，不是以 `(project_id, owner_user_id)` 是否
    存在為條件。差別在一個真實情境：若某專案已有成員但 owner 不在其中
    （例如 owner 被移出過），那是一個**人為決定**的結果，回填不該把他加回去。
    唯一約束 `uq_project_members_project_user` 也因此不會被違反。

    `joined_at` 用 `now()` 而非專案的 `created_at`：這一列記的是「他**何時成為
    成員**」，而他是在回填的這一刻成為成員的。用 `created_at` 會讓
    `BR4.2` 的「最早加入者」挑選把一位回填出來的成員排在所有真實邀請之前，
    而那不是事實。
    """
    from sqlalchemy import text

    result = conn.execute(
        text(
            "INSERT INTO project_members (project_id, user_id, role, joined_at) "
            "SELECT p.id, p.owner_user_id, :role, now() "
            "FROM projects p "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM project_members m WHERE m.project_id = p.id"
            ")"
        ),
        {"role": ROLE_PROJECT_ADMIN},
    )
    return int(result.rowcount or 0)


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
        with engine.begin() as conn:
            assert_prerequisites(conn)
            before = count_member_less_projects(conn)
            print(f"回填前的零成員專案數：{before}", flush=True)

            if args.dry_run:
                print(
                    f"--dry-run：將插入 {before} 列 "
                    f"(project_id, owner_user_id, {ROLE_PROJECT_ADMIN}, now())，"
                    "本次不寫入。"
                )
                raise _DryRun()

            inserted = backfill(conn)
            print(f"已插入 {inserted} 列成員", flush=True)

            # **自我終檢**（COMMIT 之前）：這一條就是「結束碼 0 代表什麼」。
            remaining = count_member_less_projects(conn)
            if remaining != 0:
                raise RuntimeError(
                    f"終檢未通過，已回滾（NFR12.24）：仍有 {remaining} 個零成員"
                    "專案。可能原因是某些專案的 owner_user_id 指向一個不存在的"
                    "使用者，使 INSERT 的外鍵失敗——那是資料問題，須先處置而不是"
                    "讓回填回報成功"
                )
    except _DryRun:
        print("--dry-run 完成，交易已回滾。")
        return 0
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

    print("成員回填完成（U19）：")
    print(f"  插入列數            {inserted}")
    print("  終檢通過：projects 中零成員的專案數為 0（NFR12.24）。")
    print(
        "注意：本指令**不**處理「已有成員但 owner 不在其中」的專案"
        "——那是人為決定的結果，回填不得把他加回去。"
    )
    return 0


class _DryRun(Exception):
    """以例外跳出 `engine.begin()` 使其回滾——`--dry-run` 不留痕跡。"""


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
