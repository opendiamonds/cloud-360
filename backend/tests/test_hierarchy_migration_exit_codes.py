"""`U4 hierarchy-data` 合併前必修第 28 列 (a)(b)：結束碼 2 與 `default_pairs_created` 低報。

本檔補的是 `test_hierarchy_migration.py` **沒有**涵蓋的三件事（逐一查過，不重複既有案例）：

1. 既有的 `test_standalone_command_exits_non_zero_when_the_final_check_fails` 只斷言
   未知參數回 2，**沒有**斷言「未執行任何事」——一個先跑完遷移再回 2 的實作也會通過。
   本檔的第一案斷言回 2 時 `SessionLocal` 與 `migrate_hierarchy` 皆未被呼叫。
2. 既有案例全部從「沒有任何預設專案」起跑，`default_pairs_created` 的值永遠與
   「專案是否新建」和「系統是否新建」同時成立，分不出兩者。本檔的第二案構造
   「預設專案在、預設系統缺」，把 docstring 所述的低報行為鎖住。
3. 兩處 docstring 是否寫了上述行為——防止文件再度落後程式（第 28 列的成因）。

`@api`／`@ui` 刻意缺席：受測對象是部署期指令與遷移模組，零端點、零畫面。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import text

from tests import helpers
from services.hierarchy_migration import (
    MigrationCounts,
    _PROJECTS,
    _ensure_hierarchy_schema,
    migrate_hierarchy,
)


def _count(db, sql: str, params: dict | None = None) -> int:
    return int(db.execute(text(sql), params or {}).scalar() or 0)


class TestStandaloneCommandBadInvocation(unittest.TestCase):
    def test_bad_invocation_returns_2_without_running_anything(self):
        """
        @purpose 合併前必修第 28 列 (a)：結束碼 2 的意義是「呼叫方式錯誤、未執行任何事」。
                 只斷言回 2 不夠——先跑完遷移再回 2 的實作也會回 2，而操作者據此
                 「修正呼叫方式後重跑」就會在不知情下跑第二次。
        @given 以 MagicMock 取代資料庫邊界 SessionLocal 與遷移入口 migrate_hierarchy
        @step 以未知參數 ["--dry-run"] 呼叫 main() | 回傳 2
        @step 檢查兩個 mock 的呼叫次數 | SessionLocal 0 次、migrate_hierarchy 0 次
        @step 以無參數呼叫 main() 作對照 | 回傳 0，且兩者各被呼叫 1 次
        @pass 帶參數時回 2 且兩者皆未被呼叫；無參數時兩者皆被呼叫（證明 mock 真的接在路徑上）
        @story US9.1
        @note 對照步驟不可省：若 mock 沒有接在 main() 實際使用的名稱上，「未被呼叫」
              會恆真。被 patch 的是模組層名稱 SessionLocal 與 migrate_hierarchy。
        """
        import scripts.run_hierarchy_migration as command

        fake_session = MagicMock(name="session")
        session_factory = MagicMock(name="SessionLocal", return_value=fake_session)
        fake_migrate = MagicMock(
            name="migrate_hierarchy", return_value=MigrationCounts(0, 0, 0)
        )
        with patch.object(command, "SessionLocal", session_factory), patch.object(
            command, "migrate_hierarchy", fake_migrate
        ):
            self.assertEqual(2, command.main(["--dry-run"]))
            self.assertEqual(0, session_factory.call_count)
            self.assertEqual(0, fake_migrate.call_count)

            self.assertEqual(0, command.main([]))
            self.assertEqual(1, session_factory.call_count)
            self.assertEqual(1, fake_migrate.call_count)
            fake_session.close.assert_called_once_with()


class TestDefaultPairsCreatedUnderReports(unittest.TestCase):
    def setUp(self):
        self.db = helpers.make_session()
        self.alice = helpers.make_user(
            self.db, username="alice", role="Project_Architect"
        )

    def tearDown(self):
        self.db.rollback()
        helpers.close_session(self.db)

    def test_split_pair_backfills_the_system_but_counts_zero(self):
        """
        @purpose 合併前必修第 28 列 (b)：`default_pairs_created` 只以預設專案是否新建
                 計數。「預設專案在、預設系統缺」時遷移會補建系統，但計數為 0。
                 本案把這個已在 docstring 揭露的低報行為鎖住，改動計數語意的人
                 必須同時改 docstring 與本案。
        @given alice 已有一個預設專案（is_default 為真）、其下沒有任何系統，
               並持有 1 張 system_id 為空的圖
        @step 執行遷移 | 回傳 MigrationCounts(1, 0, 1)
        @step 查該預設專案下的預設系統數 | 1（系統確實被補建）
        @step 查專案總數 | 仍為 1（沒有建第二個預設專案）
        @step 查該圖的 system_id | 等於被補建的那個預設系統
        @pass 計數為 (1, 0, 1) 且預設系統數由 0 變為 1
        @story US9.1
        @note 這個前置狀態只有人工介入才可達（遷移是 is_default 的唯一寫入端，
              兩者在同一交易內成對建立），所以本案不是在主張它會自然發生，
              而是在固定該狀態下的計數語意。
        """
        _ensure_hierarchy_schema(self.db)
        self.db.execute(
            _PROJECTS.insert().values(
                name="alice 的專案", owner_user_id=self.alice.id, is_default=True
            )
        )
        self.db.commit()
        project_id = _count(
            self.db,
            "SELECT id FROM projects WHERE owner_user_id = :o",
            {"o": self.alice.id},
        )
        diagram = helpers.make_diagram(self.db, owner=self.alice, title="a0")
        self.assertEqual(0, _count(self.db, "SELECT count(*) FROM systems"))

        counts = migrate_hierarchy(self.db)

        self.assertEqual(MigrationCounts(1, 0, 1), counts)
        self.assertEqual(
            1,
            _count(
                self.db,
                "SELECT count(*) FROM systems "
                "WHERE project_id = :p AND is_default = :t",
                {"p": project_id, "t": True},
            ),
        )
        self.assertEqual(1, _count(self.db, "SELECT count(*) FROM projects"))
        system_id = _count(
            self.db, "SELECT id FROM systems WHERE project_id = :p", {"p": project_id}
        )
        self.assertEqual(
            system_id,
            _count(
                self.db,
                "SELECT system_id FROM user_diagrams WHERE id = :i",
                {"i": diagram.id},
            ),
        )


class TestDocstringsStateTheBehaviour(unittest.TestCase):
    def test_main_docstring_states_all_three_exit_codes(self):
        """
        @purpose 合併前必修第 28 列 (a)：`main()` 的 docstring 曾寫「回傳 0 或 1」而
                 程式有三個結束碼；本案防止文件再度落後程式。
        @given scripts.run_hierarchy_migration.main
        @step 讀 main.__doc__ | 含 0、1、2 三個結束碼各自的意義
        @pass 三段說明（成功／遷移失敗且進度保留須重跑／呼叫方式錯誤且未執行任何事）皆在
        @story US9.1
        """
        import scripts.run_hierarchy_migration as command

        doc = command.main.__doc__ or ""
        self.assertIn("**0**", doc)
        self.assertIn("**1**", doc)
        self.assertIn("保留其進度", doc)
        self.assertIn("重跑", doc)
        self.assertIn("**2**", doc)
        self.assertIn("呼叫方式錯誤", doc)
        self.assertIn("未執行任何事", doc)
        self.assertNotIn("或 1（任何失敗）", doc)

    def test_migration_counts_docstring_discloses_the_under_report(self):
        """
        @purpose 合併前必修第 28 列 (b)：`MigrationCounts` 的 docstring 必須寫明
                 `default_pairs_created` 在「預設專案在、預設系統缺」時低報。
        @given services.hierarchy_migration.MigrationCounts
        @step 讀 MigrationCounts.__doc__ | 含低報說明與其觸發狀態
        @pass 「低報」「預設專案在、預設系統缺」「計數為 0」三段文字皆在
        @story US9.1
        """
        doc = MigrationCounts.__doc__ or ""
        self.assertIn("只以預設專案是否新建計數", doc)
        self.assertIn("低報", doc)
        self.assertIn("預設專案在、預設系統缺", doc)
        self.assertIn("計數為 0", doc)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
