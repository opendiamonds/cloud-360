"""
membership_service.py — `U19 membership-service` 的服務層（資料存取 ＋ 業務邏輯）

**本層沒有授權檢查**（誠實宣告而非遺漏）：授權判定只有一份，在
`membership_facade.MembershipFacade`。那是契約 `K-16` 的 `sole_entry` 選的模型，
與 `U7` 的 `hierarchy_service` 同形。後果：同進程直呼本模組的函式會**完整繞過
per-project 授權**，且繞過是**靜默的**——不會有錯誤，只會沒有檢查。
`BR1.1` 的「facade 是唯一入口」**無機械強制**（承接 `K-07` 的 `OQ-N2`／
`OPEN-FD19-3`），本檔不宣稱已守住。

錯誤處理形狀沿用 `team.md` 的既有慣例：DB／驗證錯誤**直接 raise 領域例外**，
不以 `try/except` 吞掉；`try/except` 只用在外部依賴邊界，而**本模組沒有任何
外部依賴邊界**（零 LLM、零 webhook、零 HTTP 出口），故也沒有熔斷器或降級路徑的
落點（`reliability-design.md §四`）。

兩件本模組刻意**不**做的事
--------------------------

1. **不快取 per-project 角色**（`NFR12.9`）：快取授權結論會引入「權限已撤銷但
   快取未失效」的窗口，而撤銷（`remove_member`／`change_role`）正是本單元的核心
   功能。一個索引命中的單列查詢不值得用授權正確性去換。
2. **不新增索引**（`performance-design.md §二之二`、`scalability-design.md §三`）：
   `resolve_project_role` 的 `WHERE project_id = ? AND user_id = ?` 由
   `uq_project_members_project_user`（以 `project_id` 為前導欄）完全覆蓋。
   聚合守門以 `role` 過濾而沒有任何索引含 `role`（`OPEN-ND19-3`），變更紀錄
   查詢也無可用索引（`OPEN-ND19-4`，`[FD3]`=A 的衍生後果）——兩者都寫下來了，
   但「以後可能要」不是現在建的依據，而每專案成員數受人工邀請速度限制。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from sqlalchemy import exists, select, text, union
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from models import Project, ProjectMember, ReselectionEvent, User
from services.membership_errors import (
    LastAdminGuard,
    MembershipLockTimeout,
    MembershipNotFound,
    MissingGlobalPermission,
    NoQualifiedSuccessor,
)
from services.membership_selection import select_successor
from services.membership_types import (
    GuardedProjectRef,
    MemberSnapshot,
    MemberView,
    ProjectRole,
)
from services.rbac import user_can

logger = logging.getLogger("cloud360.membership")

# ---------------------------------------------------------------------------
# 模組層常數
# ---------------------------------------------------------------------------

ROLE_PROJECT_ADMIN = ProjectRole.PROJECT_ADMIN.value
ROLE_MEMBER = ProjectRole.MEMBER.value

CAUSE_AUTO_RESELECTION = "auto_reselection"
CAUSE_MANUAL_ROLE_CHANGE = "manual_role_change"

MEMBERSHIP_STORY_ID = "K3"
"""`K3`（專案成員管理）。`rbac_seed_data.py` 已含全部 11 個角色的 `K3` 列，
故本單元**不改 `role_permissions` seed**（`U3 rbac-story-ids` 已交付）。"""

REQUIRED_INVITEE_STORY_ID = "K3"
REQUIRED_INVITEE_ACTION = "view"
"""`BR3.2`／`FR12.6a`：受邀者須具備的**全域**功能權限。

取 `K3.view` 而非 `K3.edit`：被邀請成為一般成員的人只需要看得到成員這件事，
`edit` 是**執行**成員管理動作才需要的。以 `edit` 當門檻會讓 `SRE`／`Ops_Lead`
之外的唯讀角色（`Developer`／`FinOps_Analyst`／`Security_Reviewer`／
`Platform_Owner`，`K3` view=True／edit=False）全部無法被邀請，而沒有任何
已核可需求要求那樣。"""

# 四個 log 事件名定為**模組層常數**而非散落的字面字串（`observability-design.md
# §一之一`／`monitoring-design.md §五之三`）。repo 的既有 log 是自由格式字串，
# **沒有穩定的事件名就沒有任何東西能把這四類事件從一般 log 中篩出來**——而
# `NFR12.6`–`NFR12.29` 的全部價值在於事後找得到它們。
#
# **這四個名字是一個沒有擁有者的契約端點**（`OPEN-ID19-7`，如實記載）：誰寫＝
# 本單元；誰讀＝維運者以 `docker logs` ＋ 字串篩選，**沒有任何程式讀它們**；
# 誰保證它們不被改名＝**沒有人**。改名之後什麼都不會壞——沒有編譯錯誤、沒有
# 紅燈、沒有執行期錯誤，壞掉的是「事後找得到它們」這個唯一的價值。
# 集中成常數使改名至少是一個可被 grep 到的集中動作。
# **刻意不為它們寫測試**：一條「斷言常數等於某個字面字串」的測試驗的是它自己，
# 不是任何行為（`project.md` 記過恆真斷言的形狀）。
EVENT_DENIED = "membership.denied"
EVENT_LOCK_WAIT = "membership.lock_wait"
EVENT_RESELECTED = "membership.reselected"
EVENT_RESELECT_SKIPPED = "membership.reselect_skipped"

LOCK_WAIT_WARN_MS = 250.0
"""取鎖等待超過此毫秒數即記一筆 WARN（`NFR12.27`）。

**刻意是模組層常數而不是環境變數**（`OPEN-ND19-6` 的定案）：`project.md` 的
環境設定契約要求任何 compose 消費的變數都要同步 `render-env.sh`、
`deploy/.env.example` 與 compose 三處，而一個 log 門檻不值得那個同步成本。

250 ms 這個值沒有競爭資料支撐（`performance-requirements.md §三` 逐字「設一個
逾時值需要競爭資料，而我們沒有」）。它的作用不是一個效能目標，而是**讓一個
退化的鎖競爭情況留下痕跡**——鎖等待的失敗模式是**延遲而非錯誤**，請求會成功，
只是慢，所以沒有這個 log 就沒有任何痕跡。選一個明顯高於正常單列鎖取得時間、
又低於人會察覺的延遲的量級。"""

LOCK_TIMEOUT_MS = 5000
"""取專案列鎖的**等待上限**（合併前必修第 16 項，使用者 2026-10-20 裁決 5 秒）。

在 PostgreSQL 上以 `SET LOCAL lock_timeout` 套用於**當前交易**（交易結束即失效，
不影響同一連線之後的其他工作）；逾時時資料庫回 SQLSTATE `55P03`，本模組轉成
`MembershipLockTimeout`，router 轉 503。

與 `LOCK_WAIT_WARN_MS` 同樣**刻意不做環境變數**（理由同 `OPEN-ND19-6`：一個
逾時值不值得 `render-env.sh`／`deploy/.env.example`／compose 三處的同步成本）。

**SQLite 無此語意**：它沒有列鎖，也沒有 `lock_timeout` 這個設定，故
`lock_project` 以 dialect 判斷、在 SQLite 上略過。真實逾時行為只在
`backend/tests_pg/` 驗得到。"""

LOCK_TIMEOUT_SQLSTATE = "55P03"
"""PostgreSQL 的 `lock_not_available`。`lock_timeout` 到期時回的就是它。"""

SUCCESSOR_STORY_ID = "K3"
SUCCESSOR_ACTION = "edit"
"""合格接手人須持有的**全域**權限：`K3.edit`（`BR7.3`）。

與 `REQUIRED_INVITEE_ACTION`（`view`）刻意不同：被邀請成為一般成員只需看得到，
而被升為 `project_admin` 的人必須真的能**執行**成員管理動作——否則他成為管理者後
每個管理動作都被全域層擋成 403，而 `AC12.4.3` 的文案「系統自動把管理權交給你」
對他為假，且這條路徑沒有任何人按下按鈕可以被告知失敗。"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_denied(
    *, action: str, project_id: Optional[int], principal_user_id: int
) -> None:
    """`NFR12.6`：per-project 授權被拒時記一筆 **WARN 級**結構化 log。

    四個欄位（`story_id`／`action`／`project_id`／`principal`）齊備，
    且**只有這四個**：`NFR12.26` 禁止 token、密碼或任何憑證進入 log。
    `principal` 寫入的是**身分識別**（user id），不是其憑證。

    **不寫入 `reselection_events`、不新增任何表**（`NFR12.7`／`[N2]`=A）：
    拒絕不是角色變更（`previous_role`／`new_role` 對它無意義），且拒絕是**高頻
    事件**——每個非成員的每次嘗試都算一次，寫進資料庫會讓成員詳情頁的變更紀錄
    查詢被無關列拖慢。**殘留限制如實記載：拒絕紀錄 UI 讀不到**，而目前沒有任何
    AC 要求它可見。

    另一條界線（`OPEN-ND19-8`）：本 log 含 `project_id`，對一個**非成員**而言
    它證實了「存在一個 id 為 N 的專案」。目前不是洩漏——使用者讀不到 log，而
    `BR1.5` 的拒絕回應本身不含專案資訊。**但這條界線目前只由「沒有人把 log 接到
    使用者可見面」維持。**
    """
    logger.warning(
        "%s story_id=%s action=%s project_id=%s principal=%s",
        EVENT_DENIED,
        MEMBERSHIP_STORY_ID,
        action,
        project_id,
        principal_user_id,
    )


# ---------------------------------------------------------------------------
# 取鎖（`NFR12.1`–`NFR12.4`、`security-design.md §一`）
# ---------------------------------------------------------------------------


def _dialect_name(db: Session) -> str:
    """該 session 綁定的資料庫方言名（`postgresql`／`sqlite`）。"""
    return db.get_bind().dialect.name


def _is_lock_timeout(exc: DBAPIError) -> bool:
    """該 DBAPI 例外是否為 PostgreSQL 的 `lock_not_available`（SQLSTATE `55P03`）。

    psycopg v3 以 `.sqlstate` 帶它、psycopg2 以 `.pgcode`——本 repo 用 v3，
    但兩者都讀，使驅動切換不會讓逾時悄悄變成一般 500。
    """
    orig = getattr(exc, "orig", None)
    code = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return code == LOCK_TIMEOUT_SQLSTATE


def lock_project(db: Session, *, project_id: int) -> None:
    """鎖住該 `projects` 列，使同一專案的成員變更**序列化**（`NFR12.1`）。

    **鎖的對象是父 `projects` 列，不是 `project_members` 的任何一列**
    （`NFR12.2`）。鎖子列擋不住要關掉的那個競態——兩個交易改的本來就是不同
    子列，鎖它們不會互相阻塞。競態軌跡：某專案有兩位管理者 `A`／`B`，`A` 降 `B`、
    `B` 同時降 `A`；兩個交易各自讀到管理者數 2 → 都判定「移除後剩 1」→ 都放行
    → 各自更新**不同列** → PostgreSQL 的快照隔離只在**同一列**上報寫寫衝突
    → commit 後**管理者數 = 0**，而 `BR2.1` 的不變量正是 `[FD1]`=A 的全部理由。

    **鎖的範圍限於單一專案**（`NFR12.13`）：以單一 `projects.id` 為條件，
    非表級鎖、非無 `WHERE` 的 `FOR UPDATE`。不同專案的成員變更仍可並行。

    **這條鎖在 SQLite 上靜默消失。** 實測（`sqlalchemy 2.1.1`）：
    `with_for_update()` 在 SQLite dialect 下編譯出的 SQL 是
    `SELECT projects.id FROM projects WHERE projects.id = ?`——**鎖子句整段
    不見，且無錯誤、無警告**。故本函式的行為只能在真實 PostgreSQL 上驗證，
    驗證落點是 `backend/tests_pg/test_membership_concurrency.py`（新 `concurrency`
    CI job）。把那條測試寫在既有 SQLite 路徑上**比不寫更糟**：它會綠燈，
    因為鎖根本不存在，於是產生一個假的覆蓋證據。

    鎖必須在交易**內**取得、在交易結束時釋放（這是 `FOR UPDATE` 的語意），
    故**鎖的持有時間 = 交易的長度**，交易內不得有外部呼叫。本單元的五條路徑
    都沒有外部呼叫，所以這個約束自然成立——**但若日後有人在 `change_role` 裡
    加一個通知呼叫，鎖的持有時間就會變成那個呼叫的延遲**（設計約束，非待辦）。

    **等待有上限**（合併前必修第 16 項）：PostgreSQL 上於取鎖前
    `SET LOCAL lock_timeout`（`LOCK_TIMEOUT_MS`），逾時轉 `MembershipLockTimeout`。
    沒有上限時，一筆卡住的交易會讓排隊者各佔一條連線無限期等待。`SET LOCAL`
    只作用於當前交易，故不會漏到連線池中這條連線的下一個使用者。
    """
    if _dialect_name(db) == "postgresql":
        db.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT_MS}ms'"))
    started = time.monotonic()
    try:
        row = db.execute(
            select(Project.id).where(Project.id == project_id).with_for_update()
        ).first()
    except DBAPIError as exc:
        if not _is_lock_timeout(exc):
            raise
        logger.warning(
            "%s project_id=%s waited_ms=%.1f timeout_ms=%d outcome=timed_out",
            EVENT_LOCK_WAIT,
            project_id,
            (time.monotonic() - started) * 1000.0,
            LOCK_TIMEOUT_MS,
        )
        raise MembershipLockTimeout(project_id=project_id) from exc
    waited_ms = (time.monotonic() - started) * 1000.0
    if waited_ms >= LOCK_WAIT_WARN_MS:
        # `NFR12.27`：鎖等待的失敗模式是延遲而非錯誤，這是唯一的痕跡。
        # **不用資料庫的鎖等待統計**——那需要 `pg_stat_activity` 的輪詢，
        # 屬 metrics 範疇而本 repo 沒有 metrics 管線。
        logger.warning(
            "%s project_id=%s waited_ms=%.1f threshold_ms=%.1f",
            EVENT_LOCK_WAIT,
            project_id,
            waited_ms,
            LOCK_WAIT_WARN_MS,
        )
    if row is None:
        raise MembershipNotFound(f"查不到專案 {project_id}")


def lock_projects_in_id_order(db: Session, project_ids: Sequence[int]) -> List[int]:
    """多專案操作時**一律按 `projects.id` 遞增**逐一取鎖（`security-design.md §一之二`）。

    死鎖軌跡（上游未涵蓋，由 `nfr-design` 推導）：自動改選對**一位**被停用的
    owner 可能涉及**多個**專案。T1 鎖專案 7 再等 9、T2 鎖 9 再等 7 → 死鎖。
    PostgreSQL 會偵測並中止其中一個交易，故後果不是永久卡住而是**一個停用請求
    失敗**——但它是**不可重現的間歇失敗**，而這類失敗在容忍 flaky 的 CI 裡會被
    當成雜訊。

    **不用 `WHERE id IN (...) FOR UPDATE`**：它的取鎖順序由執行計畫決定、
    **不保證**；明確的排序迴圈才是決定性的。這不是發明的手法，是防死鎖的標準
    做法（全域一致的資源排序）；本函式的工作是**指名那個排序鍵**。

    **此排序無機械強制**（`OPEN-ND19-2`）：沒有任何工具會檢查「多專案操作是否
    按 id 遞增取鎖」，而違反它的後果是間歇性死鎖。
    """
    ordered = sorted(set(project_ids))
    for project_id in ordered:
        lock_project(db, project_id=project_id)
    return ordered


# ---------------------------------------------------------------------------
# 讀取（唯讀、冪等，**不取鎖**）
# ---------------------------------------------------------------------------


def resolve_project_role(
    db: Session, *, project_id: int, user_id: int
) -> Optional[str]:
    """per-project 角色判定（`BR1.6`）。**查無該列回 `None`，代表非成員。**

    `None` **不是**預設角色：把它當成 `member` 會讓**任何**具全域權限的人取得
    專案的一般成員權限，而 `AC12.5.2` 的 deny 側直接失效。

    **一次索引查詢，不得有 N+1**（`NFR12.8`）：查詢形狀為
    `WHERE project_id = ? AND user_id = ?`，覆蓋者是 `U18` 已交付的
    `uq_project_members_project_user`（以 `project_id` 為前導欄的 btree 唯一
    索引）。這是本單元最熱的路徑——每一次 per-project 授權判定都走它。
    """
    return db.execute(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    ).scalar_one_or_none()


def list_members(db: Session, *, project_id: int) -> List[MemberView]:
    """該專案的全部成員（`U24` 成員頁的唯一資料來源）。

    `display_name` 取 `users.username`——本 repo 的 `User` 沒有獨立的顯示名欄位
    （`UserSchema` 的欄位集合即全部：`id`／`username`／`role`／`is_active`／
    `authorization_status`／`requested_role`／`last_activity_at`／`is_overdue`），
    故 `username` 就是顯示名。

    排序為 `(joined_at, user_id)`——**與 `BR4.2` 的挑選鍵同一個**，故清單的第一
    列就是自動改選會選中的那一位，畫面與行為一致。沿用它也讓排序是決定性的
    （只以 `joined_at` 排序時，時間戳相同的兩列順序取決於資料庫回傳順序）。

    **回傳內容不含 per-project 判定以外的授權結論，也不含全域角色**——前端不得
    自行推導 per-project 權限（不變量 `I-5`），它只讀本元件給的結論。
    """
    rows = db.execute(
        select(
            ProjectMember.user_id,
            User.username,
            ProjectMember.role,
            ProjectMember.joined_at,
        )
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at, ProjectMember.user_id)
    ).all()
    return [
        MemberView(
            user_id=user_id,
            display_name=username,
            role=role,
            joined_at=joined_at,
        )
        for user_id, username, role, joined_at in rows
    ]


def project_ids_where_admin(db: Session, *, user_id: int) -> List[int]:
    """該使用者具 `project_admin` 的全部專案 id（遞增）。

    存在的理由有兩個，而第二個是本函式的主要價值：取鎖順序需要一個排好序的
    id 清單（`security-design.md §一之二`），以及 `NFR12.12` 的等價測試需要一個
    「逐專案呼叫判定函式」的參照實作所走訪的那個集合。
    """
    return sorted(
        db.execute(
            select(ProjectMember.project_id).where(
                ProjectMember.user_id == user_id,
                ProjectMember.role == ROLE_PROJECT_ADMIN,
            )
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------------------
# 專案可見性（`U23`，`BR87.1`／`BR87.3`；`[PP1]`=A、`[PP3]`=A）
#
# **可見性只有這一份定義**（`_visible_project_ids_select`）。列舉（專案清單、系統
# 清單）與寫入守門（`HierarchyFacade` 三條寫入路徑經注入的 `project_visible`）都
# 由下面兩支公開函式組出，而兩支都只呼叫它——`hierarchy_service`／
# `hierarchy_facade` 不得另寫一份（`PPN-14b`，靜態檢查見
# `tests/test_project_visibility_static.py`）。
#
# 可見集合 = {請求者有成員列的專案}
#          ∪ {請求者是擁有者、且該專案在 project_members 中**零列**的專案}
#
# 擁有者那一半只在零成員列時生效：新專案必有建立者的成員列（`[ND1]`=A），零成員列的
# 專案無人能邀請，而最後一位管理者不可被移除——故「有成員列而擁有者不在其中」只能由
# **擁有者被移出**產生，那正是 `AC12.6.2` 要求拒絕的狀態。零成員列只出現在回填未跑
# （`backfill_project_members.py`）時。
# ---------------------------------------------------------------------------


def _visible_project_ids_select(user_id: int):
    """唯一的可見性定義：回傳**一個** `UNION` 選取式（欄名 `project_id`）。

    **刻意寫成 `UNION` 而不是以 `projects` 驅動的 `OR`**（`performance-design.md`
    §二之一）：`WHERE EXISTS(成員列) OR (擁有者 AND NOT EXISTS(...))` 會逐列探測全部
    專案，成本隨**全部專案數**線性增加，`ix_project_members_user_id` 永遠用不上。
    拆成兩半後，成員那一半以 `user_id` 從 `project_members` 出發（`U23` 的新索引）、
    擁有者那一半走 `ix_projects_owner_user_id`，`NOT EXISTS` 走
    `uq_project_members_project_user`（`project_id` 前導）。

    不讀任何 state、不 commit；唯一呼叫端是下面兩支公開函式。
    """
    member_half = select(ProjectMember.project_id.label("project_id")).where(
        ProjectMember.user_id == user_id
    )
    owner_half = select(Project.id.label("project_id")).where(
        Project.owner_user_id == user_id,
        ~exists().where(ProjectMember.project_id == Project.id),
    )
    return union(member_half, owner_half)


def visible_project_ids(db: Session, *, user_id: int) -> List[int]:
    """請求者可見的全部專案 id（遞增）。**一條 SQL**，與可見專案數無關（`PPN-06`）。"""
    sub = _visible_project_ids_select(user_id).subquery()
    return sorted(
        int(pid) for pid in db.execute(select(sub.c.project_id)).scalars().all()
    )


def is_project_visible(db: Session, *, project_id: int, user_id: int) -> bool:
    """該專案是否在請求者的可見集合內。**一條 SQL**。

    `project_id` 條件放在外層：PostgreSQL 會把它推入兩個分支，成員那一半因而變成
    `(project_id, user_id)` 的唯一索引探測。**外層這個條件是本函式的全部意義**——
    拿掉它就退化成「請求者有任何可見專案」（`M6` 突變：「另一專案的成員」會被當成
    目標專案的可見者）。
    """
    sub = _visible_project_ids_select(user_id).subquery()
    row = db.execute(
        select(sub.c.project_id).where(sub.c.project_id == project_id)
    ).first()
    return row is not None


def admin_count_after(
    db: Session,
    *,
    project_id: int,
    changing_user_id: int,
    new_role: Optional[str],
) -> int:
    """**單專案判定函式**——`BR2.1` 的唯一謂詞（`NFR12.11`）。

    回傳「假設把 `changing_user_id` 的角色改成 `new_role` 之後」該專案的
    `project_admin` 數。`new_role=None` 表示把他**移出**專案。

    `remove_member` 與 `change_role` 都呼叫**這一個**函式。

    **停用路徑不再用它的集合版**（合併前必修第 1 ＋ 4 項，2026-10-20）：停用守門
    改以「無合格接手人」為判準（`projects_losing_last_admin` ＋
    `is_qualified_successor`），因為停用之後還有自動改選可以補位，而自我降級／
    自我移出沒有——這兩條路徑沒有任何後續會補上管理者，故仍以本函式擋下
    「管理者數歸零」。`NFR12.12` 的等價測試（`M7`）改為驗證停用守門的集合版與
    逐專案、逐成員套用 `is_qualified_successor` 的參照實作等價。

    **不另立「至少一位成員」的謂詞**（`BR2.2`）：`BR2.1` 成立 ⇒ 每個專案至少有
    一位管理者 ⇒ 至少有一位成員。成員那一面是**推論**，不是獨立規則；加上第二個
    謂詞會是一段永不獨立命中的死碼。
    """
    rows = db.execute(
        select(ProjectMember.user_id, ProjectMember.role).where(
            ProjectMember.project_id == project_id
        )
    ).all()
    count = 0
    for user_id, role in rows:
        effective = new_role if user_id == changing_user_id else role
        if effective == ROLE_PROJECT_ADMIN:
            count += 1
    return count


def is_qualified_successor(
    db: Session,
    *,
    is_active: bool,
    authorization_status: Optional[str],
    global_role: Optional[str],
    _cache: Optional[Dict[tuple, bool]] = None,
) -> bool:
    """**合格接手人**的唯一謂詞（合併前必修第 1 ＋ 4 項；`BR7.3` 的落地）。

    一位成員要能接手成為 `project_admin`，必須同時滿足三件事：

    1. 帳號**啟用中**（`users.is_active`）——停用帳號登入不了，升他等於沒升；
    2. J5 授權狀態為 `approved`——由 `user_can` 的 `authorization_status`
       參數承載（`rbac.py` 的 `user_can` 第一行即「未核准一律無權限」），
       **不在這裡另寫一份**；
    3. 全域角色持有 `K3.edit`——否則升為管理者後每個管理動作都被全域層擋成 403。

    「其他成員」（排除被停用者）這個條件**不在謂詞裡**，在集合版
    `qualified_successors` 的查詢條件裡——謂詞只判斷**一個人**。

    **守門與改選共用這一個謂詞**（`functional-design:c34`：修在單一入口會把違規
    挪位置而不是消除它）：`projects_losing_last_admin`（停用守門）與
    `reselect_for_project`（改選候選、冪等判定）都經 `qualified_successors`
    呼叫它。兩邊若各寫一份，就會出現「守門放行、改選卻挑不到人」的專案
    ——那正是本項要消除的狀態。

    `_cache` 以 `(global_role, authorization_status)` 為鍵，使同一次判定中
    `user_can` 的權限列查詢次數以**不同角色數**為上界（canonical role 共 11 個），
    而不隨成員數成長。
    """
    if not is_active:
        return False
    key = (global_role, authorization_status)
    if _cache is not None and key in _cache:
        return _cache[key]
    result = user_can(
        db,
        global_role,
        SUCCESSOR_STORY_ID,
        SUCCESSOR_ACTION,
        authorization_status=authorization_status,
    )
    if _cache is not None:
        _cache[key] = result
    return result


def qualified_successors(
    db: Session, *, project_ids: Sequence[int], excluding_user_id: int
) -> Dict[int, List[MemberSnapshot]]:
    """`is_qualified_successor` 的**集合版**：每個專案的合格接手人（排除指定者）。

    回傳 `{project_id: [MemberSnapshot, ...]}`，每個傳入的 `project_id` 都有一個
    鍵（沒有合格者時為空串列）；串列依 `user_id` 遞增，元素保留 per-project
    `role`，故呼叫端可再分辨「其中已有管理者」。

    **查詢次數有上界**：成員 ＋ 帳號狀態一次 join 查完（與專案數無關），
    之後的 `user_can` 以 `_cache` 收斂為「不同角色數」次——不是逐專案或逐成員的
    N+1（`NFR12.10` 的取捨見 `projects_losing_last_admin`）。
    """
    ids = sorted(set(project_ids))
    result: Dict[int, List[MemberSnapshot]] = {pid: [] for pid in ids}
    if not ids:
        return result
    rows = db.execute(
        select(
            ProjectMember.project_id,
            ProjectMember.user_id,
            ProjectMember.joined_at,
            ProjectMember.role,
            User.is_active,
            User.authorization_status,
            User.role,
        )
        .join(User, User.id == ProjectMember.user_id)
        .where(
            ProjectMember.project_id.in_(ids),
            ProjectMember.user_id != excluding_user_id,
        )
        .order_by(ProjectMember.project_id, ProjectMember.user_id)
    ).all()
    cache: Dict[tuple, bool] = {}
    for (
        project_id,
        user_id,
        joined_at,
        project_role,
        is_active,
        authorization_status,
        global_role,
    ) in rows:
        if is_qualified_successor(
            db,
            is_active=bool(is_active),
            authorization_status=authorization_status,
            global_role=global_role,
            _cache=cache,
        ):
            result[project_id].append(
                MemberSnapshot(user_id=user_id, joined_at=joined_at, role=project_role)
            )
    return result


def projects_losing_last_admin(
    db: Session, *, target_user_id: int
) -> List[GuardedProjectRef]:
    """`assert_can_deactivate` 的查詢核心（`[N3]`=C／`NFR12.10`；合併前必修第 1 ＋ 4 項）。

    **只回報沒有合格接手人的專案**（使用者 2026-10-20 裁決：有合格接手人就改選，
    沒有才擋；`BR7.3` 的第三種結果）。判準是：

        該使用者是此專案的 `project_admin`，且此專案除他以外**沒有任何合格成員**

    「沒有任何合格成員」同時涵蓋兩件事：沒有其他**合格的**管理者（否則改選冪等
    略過、專案仍有人管），也沒有可被升任的合格接手人。其他管理者若**不合格**
    （停用、待核准、只有 `K3.view`）不算數——他們無法執行任何管理動作，把他們
    算進去會讓守門放行一個停用後實際上無人能管的專案，而改選的冪等判定也只算
    合格者，兩邊才對得上。

    在此之前本函式擋下「最後一位管理者」的**全部**情況，而自動改選只在「沒有
    其他管理者」時執行——兩者互斥，`AC12.4.1` 的自動改選因此不可達
    （merge-blockers 第 1 項）。

    **查詢次數**：一次取得該使用者為管理者的專案（含名稱），一次 join 取得這些
    專案的其他成員與帳號狀態，再加上至多「不同全域角色數」次的權限列讀取
    （`user_can`，見 `is_qualified_successor` 的 `_cache`）。**與該使用者的專案數
    及成員數無關**——原本的單次 `GROUP BY ... HAVING count(*) = 1` 擴成這個形狀，
    是因為合格判定需要 `user_can`，而權限矩陣只有一份（在 `role_permissions`，
    由 `user_can` 讀），不在 SQL 裡另寫一份。
    不逐專案迴圈的理由：一位使用者的專案數目前**無上界**
    （`hierarchy_migration.py` 為每位持圖使用者建一個預設專案，之後可自由建立），
    逐專案會讓停用一個帳號的延遲隨其專案數線性成長。

    **本查詢不取鎖**（`NFR12.3`）：它是**跨專案**的唯讀掃描，取鎖會讓一次停用
    請求鎖住該使用者的**全部**專案，把一個管理者動作變成一個廣域鎖。它的回傳是
    **那一刻**的事實；真正的保護在被 `NFR12.1` 的鎖保護的寫入路徑上。

    **誠實的代價（`OPEN-N19-2`，承接而非關閉）**：本函式回「通過」之後、既有
    停用端點寫入 `is_active` 之前，理論上仍有一個窗口讓另一個交易改變該使用者的
    管理者身分。後果是**停用一個本應被擋下的帳號**，而它無法以本機制關閉——
    關閉它要把停用端點整支納入同一個鎖範圍，而那會跨越 `U19` 與既有
    `user_router` 的邊界。

    `LastAdminGuardReport` 需要專案**名稱**（只給 id 的話畫面無法告知使用者是
    哪個專案），故 join `projects`。
    """
    admin_rows = db.execute(
        select(Project.id, Project.name)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.user_id == target_user_id,
            ProjectMember.role == ROLE_PROJECT_ADMIN,
        )
        .order_by(Project.id)
    ).all()
    if not admin_rows:
        return []
    qualified = qualified_successors(
        db,
        project_ids=[project_id for project_id, _ in admin_rows],
        excluding_user_id=target_user_id,
    )
    return [
        GuardedProjectRef(project_id=project_id, name=name)
        for project_id, name in admin_rows
        if not qualified[project_id]
    ]


def assert_still_has_admin(
    db: Session,
    *,
    project_id: int,
    changing_user_id: int,
    new_role: Optional[str],
) -> None:
    """三條路徑的**共同上游守門**（`BR2.1`）：自我降級與自我移出都走這裡。

    第三條路徑（停用帳號）由 `projects_losing_last_admin` 承載（經
    `assert_can_deactivate` 呼叫），判準是「無合格接手人」而非「管理者數歸零」
    ——停用之後還有自動改選可補位，這兩條路徑沒有（合併前必修第 1 ＋ 4 項）。

    `functional-design:c34` 記過：修在單一入口會把違規從一個位置挪到另一個位置
    而不是消除它。故本函式位於**兩條寫入路徑的共同上游**，而第三條用的是同一個
    不變量的量化形式——不是三處各寫一次。
    """
    if admin_count_after(
        db,
        project_id=project_id,
        changing_user_id=changing_user_id,
        new_role=new_role,
    ) >= 1:
        return
    project = db.execute(
        select(Project.id, Project.name).where(Project.id == project_id)
    ).first()
    if project is None:
        raise MembershipNotFound(f"查不到專案 {project_id}")
    raise LastAdminGuard([GuardedProjectRef(project_id=project[0], name=project[1])])


# ---------------------------------------------------------------------------
# 稽核（`BR5.x`、`[FD3]`=A）
# ---------------------------------------------------------------------------


def write_role_change_audit(
    db: Session,
    *,
    project_id: int,
    cause: str,
    promoted_user_id: int,
    previous_owner_user_id: Optional[int],
    previous_role: Optional[str],
    new_role: str,
) -> ReselectionEvent:
    """寫一列 `ReselectionEvent`，五個事實齊備（`BR5.1`）。

    **不得只沿用 `user_router._audit_append`**（`BR5.2`）：那一支寫
    `logger.info`，**UI 讀不到**，而 `AC12.2.2` 斷言的是**使用者可見的**變更
    紀錄。兩個載體刻意不同：稽核列給使用者看（成員詳情頁），結構化 log 給維運者
    看（拒絕、鎖等待、改選的執行與跳過）。

    `cause` 區分兩種來源（`BR5.3`），而它改變兩欄的語意：
    `previous_owner_user_id` 在 `auto_reselection` 下是**被停用的 owner**、在
    `manual_role_change` 下是**執行變更的管理者**（`BR5.4`，兩者都回答「這次
    變更是誰造成的」）；`acknowledged_at` **只對 `auto_reselection` 有意義**
    （`BR5.5`），故本函式**一律不設它**——橫幅的「已讀」是使用者的動作，
    不是寫入時的狀態。

    **不 commit**：呼叫端擁有交易邊界（`NFR12.16`／`NFR12.17` 要求角色更新與
    稽核寫入同一交易——角色改了而稽核沒寫會讓 `AC12.2.2` 的變更紀錄漏一筆，
    而**沒有任何東西會報錯**，畫面只是少一列）。
    """
    if cause not in (CAUSE_AUTO_RESELECTION, CAUSE_MANUAL_ROLE_CHANGE):
        # 大聲失敗而非寫入一個 DDL CHECK 會擋下的值：這裡的訊息說得出哪裡錯了，
        # 資料庫丟出來的約束名不會。
        raise ValueError(f"不支援的稽核來源：{cause}")
    event = ReselectionEvent(
        project_id=project_id,
        cause=cause,
        promoted_user_id=promoted_user_id,
        previous_owner_user_id=previous_owner_user_id,
        previous_role=previous_role,
        new_role=new_role,
        occurred_at=_now(),
    )
    db.add(event)
    db.flush()
    return event


def list_unacknowledged_reselections(
    db: Session, *, user_id: int
) -> List[ReselectionEvent]:
    """橫幅查詢（`BR5.5`）：**必須同時過濾 `cause` 與 `acknowledged_at`。**

    漏掉 `cause = 'auto_reselection'` 這個條件會讓**每一次人工角色變更都彈出
    一則橫幅**，而橫幅的文案是「系統自動把管理權交給你」——對人工變更是錯的
    訊息。這是 `[FD3]`=A 引入的**新失敗面**（在它之前本表只記自動改選，過濾
    `acknowledged_at IS NULL` 就夠了），所以它有自己的規則與自己的測試。

    已讀狀態以**事件識別字**為鍵，不是 per-user 布林值（`BR5.6`）：後者會讓
    同一人**第二次**被改選時看不到橫幅，而那正是 `FR12.4c` 要防的情境；
    狀態在伺服器端故跨裝置一致（`AC12.4.4`）。

    覆蓋這個查詢的是 partial 索引 `ix_reselection_events_unack`
    （`ON (promoted_user_id) WHERE acknowledged_at IS NULL`）——它只含未確認的
    列，故索引大小是「目前未確認數」而非歷來總數。
    """
    return list(
        db.execute(
            select(ReselectionEvent)
            .where(
                ReselectionEvent.promoted_user_id == user_id,
                ReselectionEvent.cause == CAUSE_AUTO_RESELECTION,
                ReselectionEvent.acknowledged_at.is_(None),
            )
            .order_by(ReselectionEvent.occurred_at.desc(), ReselectionEvent.id.desc())
        )
        .scalars()
        .all()
    )


def acknowledge_reselection(db: Session, *, event_id: int, user_id: int) -> bool:
    """設定該**事件列**的 `acknowledged_at`（`BR5.6`）。回傳是否真的改到一列。

    以 `promoted_user_id` 限定，故一個使用者無法確認別人的橫幅。
    冪等：已確認的列不再改（`acknowledged_at IS NULL` 在 where 裡），
    重複呼叫回 `False` 而非報錯——重按一次「知道了」不是錯誤。
    """
    event = db.execute(
        select(ReselectionEvent).where(
            ReselectionEvent.id == event_id,
            ReselectionEvent.promoted_user_id == user_id,
            ReselectionEvent.cause == CAUSE_AUTO_RESELECTION,
            ReselectionEvent.acknowledged_at.is_(None),
        )
    ).scalar_one_or_none()
    if event is None:
        return False
    event.acknowledged_at = _now()
    db.flush()
    return True


# ---------------------------------------------------------------------------
# 成員生命週期（寫入路徑；呼叫端已取鎖並擁有交易邊界）
# ---------------------------------------------------------------------------


def add_member(
    db: Session,
    *,
    project_id: int,
    user_id: int,
    role: str,
    invited_by: Optional[int],
) -> MemberView:
    """寫入一列成員（`BR3.3`／`BR3.6`）。**非冪等**：已是成員即拒絕。

    `BR3.3`：重複邀請同一 `(project, user)` 必須被拒，**不得建立第二列**。
    `project_members` 的唯一約束會先擋下它，故真正的失敗是**錯誤訊息無意義**
    （資料庫層的唯一約束違反而非業務語意）——所以這裡先查再拒。

    `BR3.6`：**成功邀請是一級行為**，不是拒絕條款的反面。成功 ⇒ 成員清單
    必然多一列（只驗拒絕面會讓「邀請其實沒寫進去」通過全部測試）。

    **不 commit**：授權檢查、全域權限前置檢查與寫入必須在**單一交易**內
    （`NFR12.15`／`BR3.2`／`AC12.5.3`：被拒時成員清單不新增任何列）。
    """
    existing = resolve_project_role(db, project_id=project_id, user_id=user_id)
    if existing is not None:
        raise MembershipNotFound(
            f"使用者 {user_id} 已經是專案 {project_id} 的成員（目前角色 {existing}）"
        )
    row = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        joined_at=_now(),
        invited_by=invited_by,
    )
    db.add(row)
    db.flush()
    username = db.execute(
        select(User.username).where(User.id == user_id)
    ).scalar_one_or_none()
    if username is None:
        raise MembershipNotFound(f"查不到使用者 {user_id}")
    return MemberView(
        user_id=user_id,
        display_name=username,
        role=row.role,
        joined_at=row.joined_at,
    )


def assert_invitee_has_global_permission(
    db: Session, *, user_id: int
) -> None:
    """`BR3.2`／`FR12.6a`：缺少對應全域功能權限的使用者**不得被邀請**。

    **主詞是受邀者，不是 principal**：`AC12.5.1` 要求「說明他缺什麼」，
    而訊息的對象是執行邀請的管理者。`AC12.5.3` 要求被拒時成員清單不新增任何列
    ——由呼叫端的單一交易保證（本函式在寫入之前）。

    半套狀態尤其危險：清單多一列而那個人實際上用不了專案。

    **帳號狀態也是前置條件**（合併前必修第 4 項）：待核准（J5
    `authorization_status != 'approved'`）由下面 `user_can` 的
    `authorization_status` 參數擋下；**已停用**帳號 `user_can` 不看，故在此
    另擋——停用帳號登入不了，加他為成員只會產生一列用不到的成員資格，而若之後
    他被自動改選選中（改選另有 `is_qualified_successor` 擋），風險更大。
    兩者都回 `MissingGlobalPermission`（422），訊息說明是帳號狀態而非角色。
    """
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise MembershipNotFound(f"查不到使用者 {user_id}")
    if not user.is_active:
        raise MissingGlobalPermission(
            user_id=user_id,
            story_id=REQUIRED_INVITEE_STORY_ID,
            action=REQUIRED_INVITEE_ACTION,
            reason="帳號已停用",
        )
    status_value = getattr(user, "authorization_status", "approved")
    if not user_can(
        db,
        user.role,
        REQUIRED_INVITEE_STORY_ID,
        REQUIRED_INVITEE_ACTION,
        authorization_status=status_value,
    ):
        # 判定只有上面那一處（`user_can`）；這裡只決定訊息怎麼說。
        raise MissingGlobalPermission(
            user_id=user_id,
            story_id=REQUIRED_INVITEE_STORY_ID,
            action=REQUIRED_INVITEE_ACTION,
            reason=(
                "帳號尚未通過授權核准"
                if status_value not in (None, "approved")
                else None
            ),
        )


def delete_member(db: Session, *, project_id: int, user_id: int) -> None:
    """移出成員。**對「該使用者已不是成員」回成功**（冪等，`BR3.4`／`[FD2]`=A）。

    回成功而非 404 的價值：`U24` 因此不需要處理「404 其實是成功」，
    且競態下兩位管理者同時移除同一人時兩邊畫面一致。

    **不 commit**：呼叫端擁有交易邊界（它還要先取鎖並跑守門）。
    """
    db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).delete(synchronize_session=False)


def set_member_role(
    db: Session, *, project_id: int, user_id: int, role: str
) -> MemberView:
    """更新該列的 `role`。**不覆寫其他管理者**（`BR3.5`）。

    一個專案可同時有**多位** `project_admin`；指定第二位是**新增而非取代**
    ——角色不互斥。覆寫會讓第一位管理者**靜默失去權限**，而 `AC12.2.4` 刻意
    斷言「指定第二位後**兩位都能執行管理動作**」，使覆寫成為可觸發的紅燈。

    實作上這條規則的落實方式是**沒有任何額外動作**：本函式只 `UPDATE` 指名的
    那一列。寫下它是因為「順手把其他 admin 降級」是一個會通過所有只驗目標列的
    測試的實作（`BR3.5` 的 violation_behaviour 逐字）。

    **不 commit**：角色更新與稽核寫入必須同一交易（`NFR12.16`）。
    """
    row = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise MembershipNotFound(
            f"使用者 {user_id} 不是專案 {project_id} 的成員"
        )
    row.role = role
    db.flush()
    username = db.execute(
        select(User.username).where(User.id == user_id)
    ).scalar_one()
    return MemberView(
        user_id=user_id,
        display_name=username,
        role=row.role,
        joined_at=row.joined_at,
    )


# ---------------------------------------------------------------------------
# 自動改選（`BR4.x`；系統發起，無人按按鈕）
# ---------------------------------------------------------------------------


def project_ids_owned_by(db: Session, *, owner_user_id: int) -> List[int]:
    return sorted(
        db.execute(
            select(Project.id).where(Project.owner_user_id == owner_user_id)
        )
        .scalars()
        .all()
    )


def reselect_for_project(
    db: Session, *, project_id: int, deactivated_user_id: int
) -> Optional[ReselectionEvent]:
    """對**單一**專案執行一次自動改選。呼叫端已取鎖並擁有交易邊界。

    回傳寫入的稽核列，或 `None`（冪等命中）。無合格管理者也無合格接手人時
    拋 `NoQualifiedSuccessor`（不得無聲，合併前必修第 10 項）。

    **候選只含合格接手人**（合併前必修第 1 ＋ 4 項；`BR7.3`）：經
    `qualified_successors`，與停用守門共用 `is_qualified_successor` 這一個謂詞
    ——停用中、待核准、只有 `K3.view` 的成員一律不會被升為管理者。

    **冪等（`BR4.3`）**：該專案已有其他**合格的** `project_admin`（排除被停用者）
    則**不執行、不寫事件**。不合格的管理者不算：他無法執行任何管理動作，把他
    算進去會讓一個實際上無人能管的專案被判成「已有管理者」。部分失敗後的重跑若
    不冪等，會產生**第二次改選事件**，使橫幅重複出現且稽核多一筆不曾發生的變更。
    """
    candidates = qualified_successors(
        db, project_ids=[project_id], excluding_user_id=deactivated_user_id
    )[project_id]
    existing_admin = next(
        (s for s in candidates if s.role == ROLE_PROJECT_ADMIN), None
    )
    if existing_admin is not None:
        # `NFR12.29`：冪等檢查是一條**靜默的**分支——它什麼都不做。沒有 log 時，
        # 「改選沒跑」與「改選跑了但選錯人」在維運上無法區分。
        logger.info(
            "%s project_id=%s reason=already_has_admin existing_admin=%s",
            EVENT_RESELECT_SKIPPED,
            project_id,
            existing_admin.user_id,
        )
        return None
    if not candidates:
        # 守門已擋下「該使用者是管理者卻無合格接手人」的停用，故能走到這裡的是
        # 他**擁有但不管理**的專案，或停用之後才變得無人合格的專案。兩者的結果
        # 都是沒有人能管的專案，**不得無聲**（合併前必修第 10 項）：拋出，由
        # `run_auto_reselection` 計入 `failed_project_ids`、端點回 500。
        raise NoQualifiedSuccessor(project_id)

    successor = select_successor(candidates)
    previous_role = successor.role
    set_member_role(
        db,
        project_id=project_id,
        user_id=successor.user_id,
        role=ROLE_PROJECT_ADMIN,
    )
    event = write_role_change_audit(
        db,
        project_id=project_id,
        cause=CAUSE_AUTO_RESELECTION,
        promoted_user_id=successor.user_id,
        # `BR5.4`：`auto_reselection` 下這一欄是**被停用的人**——擁有者，或
        # （合併前必修第 1 項起）被停用的最後一位管理者。兩者都回答「這次變更
        # 是誰造成的」。
        previous_owner_user_id=deactivated_user_id,
        previous_role=previous_role,
        new_role=ROLE_PROJECT_ADMIN,
    )
    # `NFR12.28`
    logger.info(
        "%s project_id=%s promoted_user_id=%s previous_owner_user_id=%s",
        EVENT_RESELECTED,
        project_id,
        successor.user_id,
        deactivated_user_id,
    )
    return event


@dataclass
class ReselectionOutcome:
    """`run_auto_reselection` 的結果（合併前必修第 10 項）。

    在此之前它只回成功事件，失敗只記 log——呼叫端無從得知、也沒有人負責重跑，
    失敗的專案會永久沒有管理者。

    - `events`：本次真的寫入的改選稽核列；
    - `failed_project_ids`：改選失敗（已 rollback）的專案，遞增；
    - `lock_timeout_project_ids`：其中**因取鎖逾時**失敗者（`failed_project_ids`
      的子集）。全部失敗都是逾時時，停用端點回 503 而非 500。
    """

    events: List[ReselectionEvent] = field(default_factory=list)
    failed_project_ids: List[int] = field(default_factory=list)
    lock_timeout_project_ids: List[int] = field(default_factory=list)


def reselection_scope(db: Session, *, deactivated_user_id: int) -> List[int]:
    """改選要走訪的專案：**該使用者擁有的 ∪ 他是管理者的**，依 id 遞增。

    為什麼不只是擁有的（合併前必修第 1 項）：停用守門現在會放行「該使用者是
    最後一位管理者、但有合格接手人」的專案，而那個專案未必是他擁有的——只走訪
    擁有的專案，放行之後該專案就沒有管理者了。

    走訪他是管理者、但另有合格管理者的專案是安全的：`reselect_for_project` 的
    冪等判定會略過它（記一筆 `reselect_skipped`），不寫任何事件。
    """
    return sorted(
        set(project_ids_owned_by(db, owner_user_id=deactivated_user_id))
        | set(project_ids_where_admin(db, user_id=deactivated_user_id))
    )


def run_auto_reselection(
    db: Session, *, deactivated_user_id: int
) -> ReselectionOutcome:
    """`BR4.4`：停用帳號**成功之後**，對 `reselection_scope` 的每個專案各跑一次改選。

    **觸發條件是帳號被停用**，不是專案被刪除或成員離開。範圍是他擁有的專案
    與他是管理者的專案（見 `reselection_scope`）。
    次序與守門的關係：守門先判（可能擋下整個停用），改選在停用**成功之後**才跑
    ——次序反了會對一個其實沒被停用的帳號產生改選事件。

    **失敗會回報**（合併前必修第 10 項）：回傳 `ReselectionOutcome`，失敗的專案
    列在 `failed_project_ids`，由停用端點轉成 500／503。重送同一個停用請求會再跑
    一次本函式，冪等性（`BR4.3`）使已改好的專案不重複寫事件。

    **逐專案獨立交易，而非一個大交易**（`scalability-design.md §二`）：
    一個橫跨 N 個專案的交易會同時持有 N 個鎖，把一位 owner 的停用變成一次對
    N 個專案的全面阻塞。`BR4.3` 的冪等性讓逐專案獨立是安全的——部分成功後重跑
    只會補完剩下的。**代價寫明**：停用動作不再是全有全無，可能專案 7 改選成功
    而專案 9 失敗，**中間狀態是可觀察的**。這是刻意接受的。

    取鎖順序一律按 `projects.id` 遞增（`security-design.md §一之二`）；
    這裡以排序後的 id 清單逐一處理，故順序本身就是遞增的。
    """
    outcome = ReselectionOutcome()
    for project_id in reselection_scope(db, deactivated_user_id=deactivated_user_id):
        try:
            lock_project(db, project_id=project_id)
            event = reselect_for_project(
                db,
                project_id=project_id,
                deactivated_user_id=deactivated_user_id,
            )
            db.commit()
            if event is not None:
                outcome.events.append(event)
        except MembershipLockTimeout:
            # 取鎖逾時：另一筆交易正在改這個專案的成員。不是程式錯誤，重送即可。
            db.rollback()
            outcome.failed_project_ids.append(project_id)
            outcome.lock_timeout_project_ids.append(project_id)
            logger.error(
                "%s project_id=%s reason=lock_timeout", EVENT_RESELECT_SKIPPED, project_id
            )
        except Exception:
            # 這一個專案失敗不得讓其餘專案一起失敗（逐專案獨立交易）。
            # **不靜默**：記 ERROR 並帶 exc_info，**並回報給呼叫端**（第 10 項），
            # 而冪等性使重送可收斂。
            db.rollback()
            outcome.failed_project_ids.append(project_id)
            logger.exception(
                "%s project_id=%s reason=failed", EVENT_RESELECT_SKIPPED, project_id
            )
    return outcome


__all__ = [
    "CAUSE_AUTO_RESELECTION",
    "CAUSE_MANUAL_ROLE_CHANGE",
    "EVENT_DENIED",
    "EVENT_LOCK_WAIT",
    "EVENT_RESELECTED",
    "EVENT_RESELECT_SKIPPED",
    "LOCK_TIMEOUT_MS",
    "LOCK_WAIT_WARN_MS",
    "MEMBERSHIP_STORY_ID",
    "ROLE_MEMBER",
    "ROLE_PROJECT_ADMIN",
    "ReselectionOutcome",
    "acknowledge_reselection",
    "add_member",
    "admin_count_after",
    "assert_invitee_has_global_permission",
    "assert_still_has_admin",
    "delete_member",
    "is_qualified_successor",
    "list_members",
    "list_unacknowledged_reselections",
    "lock_project",
    "lock_projects_in_id_order",
    "log_denied",
    "project_ids_owned_by",
    "project_ids_where_admin",
    "projects_losing_last_admin",
    "qualified_successors",
    "reselect_for_project",
    "reselection_scope",
    "resolve_project_role",
    "run_auto_reselection",
    "select_successor",
    "set_member_role",
    "write_role_change_audit",
]
