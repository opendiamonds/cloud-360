"""
membership_backfill.py — 既有專案的擁有者成員列補齊（`U19`；合併前必修第 15 項）

**補齊邏輯只有這一份**：`backend/main.py` 的 startup（`init_db()` 之後）與手動
指令 `backend/scripts/backfill_project_members.py` 都呼叫本模組的
`run_backfill`，不各寫一份 SQL。

為什麼要補（`NFR12.24`／`NFR12.25`）
------------------------------------

`project_members` 是全新表，而既有專案全部由 `services/hierarchy_migration.py`
建立且**從未寫過任何成員列**。零成員列的專案，`resolve_project_role` 對任何人
（包括真正的擁有者）都回 `None` → 依 `BR1.6` 判為非成員 → 擁有者被擋在自己的
專案之外（需求籤、成員頁），而這是**無聲的**權限錯誤：沒有錯誤訊息，只有 403。

為什麼改成啟動時自動補（使用者 2026-10-20 裁決）
--------------------------------------------------

原設計是部署期的**手動**指令（`U18` 的 `[P1]`=A 形狀），代價是部署與對外開放
之間多一個**沒有任何機制強制**的手動步驟（`infrastructure-design` review-03
`R-01`、`OPEN-ID19-2`）——漏跑一次，所有擁有者都被擋在外面。改為在 startup 的
`init_db()` 之後自動執行，使「服務起得來」蘊含「已補齊」。

**刻意不放進 `backend/database.py`**（`NFR12.5`，計畫 §七 判準 3：該檔 diff 為空）。
那裡的 `_ensure_*` 補丁家族**全部吞掉失敗**（`except Exception` ＋
`logger.warning` 後繼續），而本補齊**必須大聲失敗**：記 ERROR 並讓啟動失敗
——擁有者被擋在自己專案外是無聲的權限錯誤，「服務照常啟動但沒補到」正是要防的形狀。
代價寫明：`restart: unless-stopped` 之下，一個持續性的失敗（例如某專案的
`owner_user_id` 指向不存在的使用者）會讓 backend 重啟迴圈；那是一個**看得見**的
失敗，而它的處置是修資料，不是讓服務在權限錯誤的狀態下運行。

形狀
----

- **冪等**：只對「該專案**無任何**成員列」的專案插入
  `(project_id, owner_user_id, 'project_admin', CURRENT_TIMESTAMP)`。不以
  `(project_id, owner_user_id)` 是否存在為條件——已有成員但擁有者不在其中，
  是**人為決定**的結果（擁有者被移出過），補齊不得把他加回去。
- **單一交易 ＋ 自我終檢**：COMMIT 之前斷言「零成員專案數 = 0」，不為 0 即拋出
  （交易回滾）。
- **前置條件**：`projects` 與 `project_members` 兩張表必須存在。startup 路徑上
  它們由 `init_db()` 的 `Base.metadata.create_all()` 建立（兩者都是 `models.Base`
  的 model），故**不加「表不存在就略過」的 guard**：表不存在代表 `init_db()`
  沒有完成，那應該是啟動失敗而不是略過。
- 時間用 `CURRENT_TIMESTAMP` 而非 `now()`：前者 PostgreSQL 與 SQLite 都支援
  （PostgreSQL 上兩者等價），使同一份 SQL 也能在測試的 in-memory SQLite 上跑。

**本模組不輸出 `DATABASE_URL` 或其任何片段**（`project.md` 的機敏資料禁令）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger("cloud360.membership_backfill")

REQUIRED_TABLES = ("projects", "project_members")

ROLE_PROJECT_ADMIN = "project_admin"
"""刻意以字面值而非 import `membership_types`：`project_members.role` 的 DDL CHECK
是它的權威來源。值若與那條 CHECK 不符，INSERT 會**當場失敗**而非靜默寫入壞資料，
所以這不是一份會無聲漂移的副本。"""

_MEMBER_LESS_PROJECTS_SQL = (
    "SELECT count(*) FROM projects p "
    "WHERE NOT EXISTS ("
    "  SELECT 1 FROM project_members m WHERE m.project_id = p.id"
    ")"
)

_BACKFILL_SQL = (
    "INSERT INTO project_members (project_id, user_id, role, joined_at) "
    "SELECT p.id, p.owner_user_id, :role, CURRENT_TIMESTAMP "
    "FROM projects p "
    "WHERE NOT EXISTS ("
    "  SELECT 1 FROM project_members m WHERE m.project_id = p.id"
    ")"
)


class BackfillPrerequisiteError(RuntimeError):
    """`projects`／`project_members` 不存在。"""


class BackfillVerificationError(RuntimeError):
    """自我終檢未通過：插入之後仍有零成員專案（交易已回滾）。"""


@dataclass(frozen=True)
class BackfillResult:
    before: int
    inserted: int
    dry_run: bool


class _DryRun(Exception):
    """以例外跳出 `engine.begin()` 使其回滾——`dry_run` 不留痕跡。"""


def assert_prerequisites(conn: Connection) -> None:
    inspector = inspect(conn)
    missing = [name for name in REQUIRED_TABLES if not inspector.has_table(name)]
    if missing:
        raise BackfillPrerequisiteError(
            "前置條件不足：缺少資料表 " + "、".join(missing) + "。"
            "project_members 由 U18 的腳本或後端啟動時的 create_all 建立"
            "（見 DEPLOY.md 第 2.2.9 節）"
        )


def count_member_less_projects(conn: Connection) -> int:
    """零成員專案數。終檢與事前報告共用同一個查詢，故兩者不可能對不起來。"""
    return int(conn.execute(text(_MEMBER_LESS_PROJECTS_SQL)).scalar() or 0)


def backfill(conn: Connection) -> int:
    """為每個零成員專案插入擁有者的 `project_admin` 列；回傳插入列數。

    `joined_at` 用補齊當下而非專案的 `created_at`：這一列記的是「他**何時成為
    成員**」，用 `created_at` 會讓 `BR4.2` 的「最早加入者」把補出來的成員排在
    所有真實邀請之前，而那不是事實。
    """
    result = conn.execute(text(_BACKFILL_SQL), {"role": ROLE_PROJECT_ADMIN})
    return int(result.rowcount or 0)


def run_backfill(engine: Engine, *, dry_run: bool = False) -> BackfillResult:
    """單一交易內：前置檢查 → 計數 → 插入 → **自我終檢** → COMMIT。

    終檢不為 0 時拋 `BackfillVerificationError`，`engine.begin()` 因而回滾。
    `dry_run=True` 只計數、不寫入（交易一律回滾）。
    """
    result: Optional[BackfillResult] = None
    try:
        with engine.begin() as conn:
            assert_prerequisites(conn)
            before = count_member_less_projects(conn)
            if dry_run:
                result = BackfillResult(before=before, inserted=0, dry_run=True)
                raise _DryRun()
            inserted = backfill(conn)
            # **自我終檢**（COMMIT 之前）：這一條就是「成功代表什麼」。
            remaining = count_member_less_projects(conn)
            if remaining != 0:
                raise BackfillVerificationError(
                    f"終檢未通過，已回滾（NFR12.24）：仍有 {remaining} 個零成員專案。"
                    "補齊只插入「零成員專案的擁有者」，插入後仍有零成員專案代表"
                    "插入與計數兩個查詢的條件不一致或補齊期間有並行寫入；請以 "
                    "scripts/backfill_project_members.py --dry-run 查看並人工處置。"
                    "（projects.owner_user_id 有外鍵，不會是孤兒擁有者。）"
                )
            result = BackfillResult(before=before, inserted=inserted, dry_run=False)
    except _DryRun:
        pass
    assert result is not None
    return result


def ensure_project_members_on_startup(engine: Optional[Engine] = None) -> BackfillResult:
    """`backend/main.py` 的 startup 在 `init_db()` 之後呼叫。**失敗即拋**。

    失敗時記 **ERROR**（帶 traceback）再重新拋出，使 uvicorn 的啟動失敗——
    不吞、不降級（見模組 docstring）。成功且真的補了列時記 INFO；沒有要補的
    （常態）時記 DEBUG，不在每次啟動都留一行雜訊。
    """
    if engine is None:
        from database import engine as default_engine

        engine = default_engine
    try:
        result = run_backfill(engine)
    except Exception:
        logger.exception(
            "membership.backfill_failed：既有專案的擁有者成員列補齊失敗，啟動中止"
            "（擁有者會被擋在自己的專案之外）。處置資料後重啟即可，補齊為冪等"
        )
        raise
    if result.inserted:
        logger.info(
            "membership.backfilled inserted=%d member_less_before=%d",
            result.inserted,
            result.before,
        )
    else:
        logger.debug("membership.backfill_noop member_less_before=%d", result.before)
    return result


__all__ = [
    "BackfillPrerequisiteError",
    "BackfillResult",
    "BackfillVerificationError",
    "ROLE_PROJECT_ADMIN",
    "assert_prerequisites",
    "backfill",
    "count_member_less_projects",
    "ensure_project_members_on_startup",
    "run_backfill",
]
