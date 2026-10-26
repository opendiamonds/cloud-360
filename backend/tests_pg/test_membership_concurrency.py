"""`U19 membership-service` 的併發測試（`C1`–`C4`）——**只在真實 PostgreSQL**。

`C4`（取鎖等待上限）是合併前必修第 16 項加的；`C1`–`C3` 的說明見下。

對應 `unit-test-instructions.md §三` 的第四列（併發，**3** 個）。
三個而不是五到八個，因為它只有三個斷言面，而硬湊到 5 個會製造恆真測試。

為什麼只有這裡驗得到
====================

`[N1]`=A 選的 `FOR UPDATE` 在 SQLite dialect 下**被靜默丟棄**（編譯出的 SQL
無鎖子句、無錯誤、無警告），故這三條在既有測試路徑上會在**完全沒有鎖**的情況下
通過。隔離的理由與機制見 `tests_pg/__init__.py`。

交錯順序以 barrier 釘住，**不用 `sleep`**（`NFR12.4`）
======================================================

`unit-of-work.md` 對 `U22` 已記過「一個 flaky 的併發測試等於沒有測試」，而
`playwright.config.ts` 與 `ui-regression` 都容忍 flaky——所以這裡的順序不能靠
時間。

本檔的機制是**一個 barrier、兩種相反的預期結果**，而那正好對應「鎖存在」與
「鎖不該存在」兩類斷言：

- `C1`（同一專案）：兩個執行緒各自取鎖之後在 barrier 會合。
  **鎖真的存在 ⇒ 第二個執行緒到不了 barrier**（它卡在取鎖）⇒ barrier 逾時
  破損，而那是**預期**的通過條件。鎖不存在 ⇒ 兩者都到得了 ⇒ barrier 成立 ⇒
  **紅燈**。
- `C2`（不同專案）：同一個 barrier **必須成立**——兩個不同專案的鎖同時被持有。
- `C3`（`assert_can_deactivate` 不取鎖）：一個執行緒持有鎖，另一個執行緒跑
  守門查詢；守門若取鎖就卡住 ⇒ barrier 破損 ⇒ 紅燈。守門不取鎖 ⇒ 成立。

`Barrier.wait(timeout)` 是**有界的條件等待**，不是 `sleep`：
`C2`／`C3` 的正常路徑在兩方到齊的瞬間就返回（零等待），只有「鎖確實擋住了」
那一條會真的等到逾時——而那一條的逾時**就是它的通過訊號**。

失敗時的診斷
============

每個執行緒把自己走到的步驟寫進 `self.steps`（`before_lock`／`holding_lock`／
`at_barrier`／`committed`／`guard_raised`／`error:<...>`），而每條斷言失敗時都把
兩個執行緒的步驟一起印出來。**只印 `assertEqual` 失敗對診斷無用**
（`monitoring-design.md §六`）——併發測試最常見的失敗是「卡住」而不是
「斷言不成立」，而「卡在哪一步」才是唯一有用的資訊。
"""

from __future__ import annotations

import threading
import time
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from tests_pg import require_pg_url

from models import Project, ProjectMember, ReselectionEvent, User
import services.membership_service as membership_service
from services.hierarchy_facade import mint_principal
from services.membership_errors import LastAdminGuard
from services.membership_facade import MembershipFacade
from services.membership_types import ProjectRole

# 兩方到齊即返回，故「必須成立」的路徑實際等待趨近於零。給 CI 充裕的餘裕。
BARRIER_SATISFY_TIMEOUT_S = 15.0
# 「必須破損」的路徑會真的等到這個時間——它就是「鎖確實擋住了」的證明。
BARRIER_BREAK_TIMEOUT_S = 3.0
# 執行緒 join 的上界。超過它代表測試自己卡住了，而卡住必須是紅燈而非掛著。
JOIN_TIMEOUT_S = 60.0

UNIQUE_TAG = "u19pg"


@dataclass(frozen=True)
class _Actor:
    """`mint_principal` 的最小輸入：它只讀 `.id` 與 `.role`。

    刻意**不是** ORM 的 `User`——見 `_user()` 的 docstring（`schema_rbac.sql`
    的 `users` 比 ORM 窄一欄）。
    """

    id: int
    role: str


class MembershipConcurrencyTest(unittest.TestCase):
    """真實 PostgreSQL 上的三條併發斷言。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(require_pg_url())
        # 前置查證：兩張表必須存在。缺表時給可讀訊息，而不是讓每個測試各丟一次
        # 生的 UndefinedTable。
        with cls.engine.connect() as conn:
            missing = [
                name
                for name in ("projects", "project_members", "reselection_events")
                if not conn.execute(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = :t"
                    ),
                    {"t": name},
                ).scalar()
            ]
            if missing:
                raise RuntimeError(
                    "前置條件不足：public schema 缺少 "
                    + "、".join(missing)
                    + "。請先對目標資料庫套用 schema_rbac.sql"
                    "（CI 的 concurrency job 會做這件事；本機見 LOCAL-DEV.md 第 2 節）"
                )
            # `cause` 是 `[FD3]`=A 回補的第 9 欄；缺它則 change_role 的稽核寫入
            # 會以 NotNullViolation 失敗，而那個訊息看不出根因。
            if not conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='reselection_events' "
                    "AND column_name='cause'"
                )
            ).scalar():
                raise RuntimeError(
                    "reselection_events 缺少 cause 欄（U19/[FD3]=A 回補的第 9 欄）。"
                    "目標資料庫套用的是舊版 schema_rbac.sql"
                )
        # 合併前必修第 1 ＋ 4 項起，停用守門的合格接手人判定會讀
        # `users.authorization_status`，而 `schema_rbac.sql` 的 `users` 沒有這一欄
        # ——它由後端啟動時的 `_ensure_j5_schema()` 補上（見 `_user()` 的 docstring）。
        # CI 的 concurrency job 只套用 DDL、不啟動後端，故這裡呼叫**同一支**補丁，
        # 而不是在測試裡另寫一份 DDL。`database.engine` 讀的是同一個 DATABASE_URL。
        import database

        database._ensure_j5_schema()
        with cls.engine.connect() as conn:
            if not conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='users' "
                    "AND column_name='authorization_status'"
                )
            ).scalar():
                raise RuntimeError(
                    "users 缺少 authorization_status 欄，且 _ensure_j5_schema() 沒有補上"
                    "（它會吞掉失敗，請看上面的 WARNING）"
                )
        cls.Session = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    # -- fixtures ---------------------------------------------------------

    def setUp(self) -> None:
        self.steps: dict[str, str] = {}
        self.db = self.Session()
        self.user_ids: list[int] = []
        self.project_ids: list[int] = []
        self.alice = self._user("alice")
        self.bob = self._user("bob")
        self.carol = self._user("carol")

    def tearDown(self) -> None:
        # 真實 DB 不會每次重建，故每個測試清理自己建的列。
        # 順序：reselection_events（**對 projects 無外鍵**，不會被 CASCADE 帶走）
        # → projects（其成員列由 ON DELETE CASCADE 帶走）→ users。
        try:
            self.db.rollback()
            if self.project_ids:
                self.db.query(ReselectionEvent).filter(
                    ReselectionEvent.project_id.in_(self.project_ids)
                ).delete(synchronize_session=False)
                self.db.query(Project).filter(
                    Project.id.in_(self.project_ids)
                ).delete(synchronize_session=False)
            if self.user_ids:
                self.db.query(ReselectionEvent).filter(
                    ReselectionEvent.promoted_user_id.in_(self.user_ids)
                ).delete(synchronize_session=False)
                self.db.query(User).filter(
                    User.id.in_(self.user_ids)
                ).delete(synchronize_session=False)
            self.db.commit()
        finally:
            self.db.close()

    def _user(self, label: str) -> _Actor:
        """以 **raw SQL** 建立使用者列，刻意不走 ORM。

        理由是本站實測出來的：`schema_rbac.sql` 的 `A)` 區塊給的 `users` 表比
        ORM 的 `User` model **窄一欄**——`authorization_status` 不在 DDL 裡，
        它由 `backend/database.py` 的 `_ensure_j5_schema()` 在**後端啟動時**
        補上。於是在一個只套用過 `schema_rbac.sql` 的資料庫（正是本測試的 CI
        job 所建的那種）上，`db.add(User(...))` 會以
        `UndefinedColumn: column "authorization_status" ... does not exist` 失敗。

        這個落差是**既存**的，與本單元無關（`users` 不是本單元的表，`A)` 區塊
        屬 baseline），故本測試**不試圖修它**，只繞開它：本測試的受測對象是
        `projects` 列鎖，不是 `users` 的 schema。改走 raw SQL 也讓本測試在
        「已跑過啟動補丁的本機 DB」與「只套過 DDL 的 CI DB」上行為一致。

        回傳一個只帶 `id` 與 `role` 的輕量物件——`mint_principal` 只讀這兩個
        欄位，而帶一個半載入的 ORM 實體進來只會讓它在別處觸發 lazy load。
        """
        row = self.db.execute(
            text(
                "INSERT INTO users (username, password_hash, role, is_active) "
                "VALUES (:username, 'unused', :role, true) RETURNING id"
            ),
            {
                "username": f"{UNIQUE_TAG}-{label}-{id(self)}",
                # K2 view+edit、K3 view+edit（`rbac_seed_data.py` 實算）
                "role": "Project_Architect",
            },
        ).scalar_one()
        self.db.commit()
        self.user_ids.append(int(row))
        return _Actor(id=int(row), role="Project_Architect")

    def _project_with_two_admins(self, name: str) -> Project:
        project = Project(
            name=f"{UNIQUE_TAG}-{name}-{id(self)}",
            owner_user_id=self.alice.id,
            is_default=False,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        self.project_ids.append(project.id)
        now = datetime.now(timezone.utc)
        for index, user in enumerate((self.alice, self.bob)):
            self.db.add(
                ProjectMember(
                    project_id=project.id,
                    user_id=user.id,
                    role=ProjectRole.PROJECT_ADMIN.value,
                    joined_at=now + timedelta(seconds=index),
                )
            )
        self.db.commit()
        return project

    def _admin_count(self, project_id: int) -> int:
        return (
            self.db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectRole.PROJECT_ADMIN.value,
            )
            .count()
        )

    def _diag(self, headline: str) -> str:
        lines = [headline, "兩個執行緒各自卡在／走到的步驟："]
        for name in sorted(self.steps):
            lines.append(f"  {name}: {self.steps[name]}")
        return "\n".join(lines)

    # -- C1：FOR UPDATE 真的存在 -------------------------------------------

    def test_C1_same_project_member_changes_are_serialised(self):
        """`C1`／`NFR12.1`／`BR2.1`：同一專案的成員變更被序列化，守門不被繞過。

        競態軌跡（`security-requirements.md §一`）：某專案有兩位管理者
        `alice`／`bob`；alice 降 bob、bob 同時降 alice。兩個交易各自讀到管理者數
        2 → 都判定「移除後剩 1」→ 都放行 → 各自更新**不同列** → PostgreSQL 的
        快照隔離只在**同一列**上報寫寫衝突 → commit 後**管理者數 = 0**。

        突變驗證（`unit-test-instructions.md §七` 第 2 列）：移除
        `membership_service.lock_project` 裡的 `.with_for_update()` 必須讓本測試
        紅燈——兩個執行緒都會到得了 barrier（它成立而非破損），而這裡斷言它
        **必須破損**。

        三個斷言一起才構成「鎖存在」：
          (a) 第二個執行緒**到不了** barrier（它卡在取鎖）；
          (b) 它之後的守門**看得到**第一個執行緒的變更，故 raise `LastAdminGuard`；
          (c) 結束時該專案的管理者數**仍 ≥ 1**。
        """
        project = self._project_with_two_admins("c1")
        barrier = threading.Barrier(2)
        results: dict[str, object] = {}

        def worker(name: str, actor: _Actor, target: _Actor) -> None:
            session = self.Session()
            self.steps[name] = "before_lock"
            try:
                # 以 facade 跑完整路徑（授權 → 取鎖 → 守門 → 寫入 → commit），
                # 只在**取鎖之後**插入一次 barrier 會合。
                original = membership_service.lock_project

                def locked(db, *, project_id):
                    original(db, project_id=project_id)
                    self.steps[name] = "holding_lock"
                    try:
                        self.steps[name] = "at_barrier"
                        barrier.wait(timeout=BARRIER_BREAK_TIMEOUT_S)
                        # 兩方都到齊了——這**只有在沒有鎖的時候**才可能。
                        results[f"{name}_barrier"] = "satisfied"
                    except threading.BrokenBarrierError:
                        results[f"{name}_barrier"] = "broken"
                    self.steps[name] = "holding_lock"

                facade = MembershipFacade(session)
                # 以 monkeypatch 注入 barrier：被包起來的是**真正的**取鎖函式，
                # 故本測試驗的仍是 facade 的實際路徑，不是一個複製品。
                membership_service.lock_project = locked
                try:
                    facade.change_role(
                        mint_principal(actor),
                        project_id=project.id,
                        user_id=target.id,
                        role=ProjectRole.MEMBER.value,
                    )
                    self.steps[name] = "committed"
                    results[name] = "ok"
                except LastAdminGuard:
                    self.steps[name] = "guard_raised"
                    results[name] = "guard"
                finally:
                    membership_service.lock_project = original
            except Exception as exc:  # noqa: BLE001 - 測試診斷用
                self.steps[name] = f"error:{type(exc).__name__}: {exc}"
                results[name] = "error"
            finally:
                session.close()

        t1 = threading.Thread(
            target=worker, args=("T1", self.alice, self.bob), name="T1"
        )
        t2 = threading.Thread(
            target=worker, args=("T2", self.bob, self.alice), name="T2"
        )
        t1.start()
        t2.start()
        for thread in (t1, t2):
            thread.join(timeout=JOIN_TIMEOUT_S)
            self.assertFalse(
                thread.is_alive(), self._diag(f"{thread.name} 在 join 逾時後仍在跑")
            )

        # (a) barrier **必須破損**：第二個執行緒卡在取鎖，到不了會合點。
        self.assertNotIn(
            "satisfied",
            [results.get("T1_barrier"), results.get("T2_barrier")],
            self._diag(
                "兩個執行緒同時持有同一專案的鎖——`FOR UPDATE` 不存在或沒生效。"
                "這正是 with_for_update() 在 SQLite 下被靜默丟棄的那個形狀，"
                "而在真實 PostgreSQL 上它代表鎖語句真的不見了（NFR12.1）"
            ),
        )
        # (b) 一個成功、一個被守門擋下。
        outcomes = sorted([results.get("T1"), results.get("T2")])
        self.assertEqual(
            outcomes,
            ["guard", "ok"],
            self._diag(
                f"預期一個成功一個被守門擋下，實際 {outcomes}。兩個都成功 ⇒ "
                "守門被繞過（BR2.1 的不變量在併發下為假）"
            ),
        )
        # (c) 不變量仍然成立。
        self.db.expire_all()
        self.assertGreaterEqual(
            self._admin_count(project.id),
            1,
            self._diag("該專案已失去最後一位管理者——BR2.1 被繞過"),
        )

    # -- C2：不同專案不互相阻塞 --------------------------------------------

    def test_C2_different_projects_do_not_block_each_other(self):
        """`C2`／`NFR12.13`：鎖的範圍限於**單一專案**。

        這是 `[N1]`=A 相對 `SERIALIZABLE` 的主要擴展優勢：序列化的粒度是專案，
        而非整個成員關係子系統。斷言方式與 `C1` 相反——同一個 barrier
        **必須成立**：兩個不同專案的鎖被同時持有。

        若實作改成表級鎖、或 `FOR UPDATE` 漏了 `WHERE`（`NFR12.13` 的二元判準
        逐字禁止這兩者），本測試會紅：第二個執行緒到不了 barrier。
        """
        left = self._project_with_two_admins("c2a")
        right = self._project_with_two_admins("c2b")
        barrier = threading.Barrier(2)
        results: dict[str, object] = {}

        def worker(name: str, project_id: int) -> None:
            session = self.Session()
            self.steps[name] = "before_lock"
            try:
                membership_service.lock_project(session, project_id=project_id)
                self.steps[name] = "holding_lock"
                self.steps[name] = "at_barrier"
                try:
                    barrier.wait(timeout=BARRIER_SATISFY_TIMEOUT_S)
                    results[name] = "concurrent"
                except threading.BrokenBarrierError:
                    results[name] = "blocked"
                session.commit()
                self.steps[name] = "committed"
            except Exception as exc:  # noqa: BLE001
                self.steps[name] = f"error:{type(exc).__name__}: {exc}"
                results[name] = "error"
            finally:
                session.close()

        t1 = threading.Thread(target=worker, args=("T1", left.id), name="T1")
        t2 = threading.Thread(target=worker, args=("T2", right.id), name="T2")
        t1.start()
        t2.start()
        for thread in (t1, t2):
            thread.join(timeout=JOIN_TIMEOUT_S)
            self.assertFalse(
                thread.is_alive(), self._diag(f"{thread.name} 在 join 逾時後仍在跑")
            )

        self.assertEqual(
            [results.get("T1"), results.get("T2")],
            ["concurrent", "concurrent"],
            self._diag(
                "不同專案的成員變更互相阻塞了——鎖的範圍不是單一專案"
                "（表級鎖，或 FOR UPDATE 漏了 WHERE；NFR12.13 的二元判準"
                "逐字禁止這兩者）"
            ),
        )

    # -- C3：守門不取鎖 ----------------------------------------------------

    def test_C3_assert_can_deactivate_takes_no_lock(self):
        """`C3`／`NFR12.3`：`assert_can_deactivate` **不取鎖**。

        它是**跨專案**的唯讀掃描；取鎖會讓一次停用請求鎖住該使用者的**全部**
        專案，把一個管理者動作變成一次廣域鎖。

        斷言方式：T1 持有該專案的鎖不放，T2 跑守門查詢。守門若取鎖就卡在那裡
        → barrier 破損 → 紅燈。守門不取鎖 → 它跑完、到 barrier 會合 → 成立。

        **同時驗它真的有在判定**（否則一個「永遠直接 return」的實作也會通過
        本測試的第一半）：該專案只有 alice 一位管理者時守門必須 raise。
        """
        project = self._project_with_two_admins("c3")
        # 讓 alice 成為唯一的成員，使守門有東西可報。合併前必修第 1 ＋ 4 項起守門
        # 只擋「無合格接手人」：bob 是 `Project_Architect`（`K3.edit`、啟用），
        # 把他降為一般成員仍是合格接手人、守門會放行，故這裡把他整列移出。
        self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == self.bob.id,
        ).delete(synchronize_session=False)
        self.db.commit()

        barrier = threading.Barrier(2)
        results: dict[str, object] = {}

        def holder() -> None:  # noqa: D401
            session = self.Session()
            self.steps["T1"] = "before_lock"
            try:
                membership_service.lock_project(session, project_id=project.id)
                self.steps["T1"] = "holding_lock"
                self.steps["T1"] = "at_barrier"
                try:
                    barrier.wait(timeout=BARRIER_SATISFY_TIMEOUT_S)
                    results["T1"] = "released_after_rendezvous"
                except threading.BrokenBarrierError:
                    results["T1"] = "barrier_broken"
                session.rollback()
                self.steps["T1"] = "committed"
            except Exception as exc:  # noqa: BLE001
                self.steps["T1"] = f"error:{type(exc).__name__}: {exc}"
                results["T1"] = "error"
            finally:
                session.close()

        def guard() -> None:
            session = self.Session()
            self.steps["T2"] = "before_lock"
            try:
                facade = MembershipFacade(session)
                try:
                    facade.assert_can_deactivate(
                        mint_principal(self.bob), target_user_id=self.alice.id
                    )
                    results["T2"] = "passed"
                except LastAdminGuard as exc:
                    results["T2"] = "guard"
                    results["T2_projects"] = [p.project_id for p in exc.projects]
                self.steps["T2"] = "guard_raised"
                self.steps["T2"] = "at_barrier"
                try:
                    barrier.wait(timeout=BARRIER_SATISFY_TIMEOUT_S)
                    results["T2_barrier"] = "satisfied"
                except threading.BrokenBarrierError:
                    results["T2_barrier"] = "broken"
                session.rollback()
                self.steps["T2"] = "committed"
            except Exception as exc:  # noqa: BLE001
                self.steps["T2"] = f"error:{type(exc).__name__}: {exc}"
                results["T2"] = "error"
            finally:
                session.close()

        t1 = threading.Thread(target=holder, name="T1")
        t1.start()
        t2 = threading.Thread(target=guard, name="T2")
        t2.start()
        for thread in (t1, t2):
            thread.join(timeout=JOIN_TIMEOUT_S)
            self.assertFalse(
                thread.is_alive(), self._diag(f"{thread.name} 在 join 逾時後仍在跑")
            )

        self.assertEqual(
            results.get("T2_barrier"),
            "satisfied",
            self._diag(
                "守門在另一個執行緒持有該專案鎖的期間卡住了——它取鎖了"
                "（NFR12.3 明文它不得取鎖：取鎖會讓一次停用鎖住該使用者的"
                "全部專案）"
            ),
        )
        # 第二半：它真的在判定，不是直接 return。
        self.assertEqual(
            results.get("T2"), "guard", self._diag("守門沒有判定出唯一管理者")
        )
        self.assertEqual(results.get("T2_projects"), [project.id], self._diag("守門回報的專案不對"))

    # -- C4：取鎖等待有上限（合併前必修第 16 項）---------------------------

    def test_C4_lock_wait_times_out_after_the_configured_limit(self):
        """
        @purpose 一筆交易卡住專案鎖時，其他人等待取鎖的時間必須有上限（約 5 秒），逾時拋 MembershipLockTimeout（端點轉 503），而不是無限期佔用連線
        @given 真實 PostgreSQL；T1 對專案 c4 取鎖後不放
        @step T1 取鎖後設定 held 事件 | T1 停在 holding_lock
        @step T2 等到 held 後對同一專案呼叫 lock_project | 約 LOCK_TIMEOUT_MS 後拋 MembershipLockTimeout，project_id 為該專案
        @step T2 rollback 後在同一個 session 執行 SELECT 1 | 成功（連線未被卡住）
        @pass 逾時例外、等待時間落在 [0.8×上限, 上限＋10 秒]、連線可再用
        @story US12.3
        """
        from services.membership_errors import MembershipLockTimeout

        project = self._project_with_two_admins("c4")
        held = threading.Event()
        done = threading.Event()
        results: dict[str, object] = {}

        def holder() -> None:
            session = self.Session()
            self.steps["T1"] = "before_lock"
            try:
                membership_service.lock_project(session, project_id=project.id)
                self.steps["T1"] = "holding_lock"
                held.set()
                # 有界的條件等待（不是 sleep）：T2 結束就放鎖。
                done.wait(timeout=JOIN_TIMEOUT_S)
                session.rollback()
                self.steps["T1"] = "committed"
            except Exception as exc:  # noqa: BLE001
                self.steps["T1"] = f"error:{type(exc).__name__}: {exc}"
                held.set()
            finally:
                session.close()

        def waiter() -> None:
            session = self.Session()
            self.steps["T2"] = "before_lock"
            try:
                if not held.wait(timeout=BARRIER_SATISFY_TIMEOUT_S):
                    results["T2"] = "holder_never_locked"
                    return
                self.steps["T2"] = "waiting_for_lock"
                started = time.monotonic()
                try:
                    membership_service.lock_project(session, project_id=project.id)
                    results["T2"] = "acquired"
                except MembershipLockTimeout as exc:
                    results["T2"] = "timed_out"
                    results["T2_project"] = exc.project_id
                results["T2_elapsed"] = time.monotonic() - started
                session.rollback()
                results["T2_reusable"] = session.execute(text("SELECT 1")).scalar()
                session.rollback()
                self.steps["T2"] = "committed"
            except Exception as exc:  # noqa: BLE001
                self.steps["T2"] = f"error:{type(exc).__name__}: {exc}"
                results["T2"] = "error"
            finally:
                done.set()
                session.close()

        t1 = threading.Thread(target=holder, name="T1")
        t2 = threading.Thread(target=waiter, name="T2")
        t1.start()
        t2.start()
        for thread in (t2, t1):
            thread.join(timeout=JOIN_TIMEOUT_S)
            self.assertFalse(
                thread.is_alive(), self._diag(f"{thread.name} 在 join 逾時後仍在跑")
            )

        limit_s = membership_service.LOCK_TIMEOUT_MS / 1000.0
        self.assertEqual(
            results.get("T2"),
            "timed_out",
            self._diag(
                "第二個交易沒有在取鎖逾時——lock_timeout 沒有生效（SET LOCAL 沒送出，"
                "或 55P03 沒被轉成 MembershipLockTimeout）"
            ),
        )
        self.assertEqual(results.get("T2_project"), project.id, self._diag("逾時例外的專案不對"))
        elapsed = results.get("T2_elapsed")
        self.assertGreaterEqual(elapsed, limit_s * 0.8, self._diag(f"等待 {elapsed:.2f}s 遠短於上限"))
        self.assertLessEqual(elapsed, limit_s + 10.0, self._diag(f"等待 {elapsed:.2f}s 遠超過上限"))
        self.assertEqual(results.get("T2_reusable"), 1, self._diag("逾時之後連線不可再用"))


if __name__ == "__main__":
    unittest.main()
