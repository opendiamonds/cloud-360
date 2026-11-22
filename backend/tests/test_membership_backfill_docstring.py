"""合併前必修第 31 列 (b)：回填失敗的歸因不得是「孤兒擁有者」（`U19`，2026-11-07）。

缺陷：`services/membership_backfill.py` 的模組 docstring 曾以「某專案的
`owner_user_id` 指向不存在的使用者」作為讓 backend 重啟迴圈的持續性失敗例子。
`projects.owner_user_id` 有外鍵指向 `users`，那種資料在資料庫層不可能存在；而
這段文字正是維運者面對重啟迴圈時會讀的判斷依據——照它去查孤兒資料只會查不到，
錯過真正的兩類原因（終檢剩餘數不為 0、`INSERT` 本身拋例外）。

**為什麼值得一則測試而不只改文字**：同一個歸因有三個載體——本模組 docstring、
`run_backfill` 的終檢錯誤訊息、`DEPLOY.md` §2.2.10——而 2026-10-31 的修正只改到後
兩者，docstring 是事後才被審查查出的殘留。本檔鎖住**本單元擁有的兩個載體**
（docstring 與執行期訊息）；`DEPLOY.md` 是多單元共用檔，不在本單元測試射程內，
以文件同步規則承擔。

判準刻意不是「全文不得出現『孤兒』」——更正後的文字本身就要**否定地**提到它
（「不要預設是……」），禁掉字串會逼人把那句警告拿掉。改為：凡提到該歸因的句子，
同一句必須帶明確的否定詞（「不要預設」「不可能」「不會是」）；舊句只帶一般的
「不是」（「不是讓服務在權限錯誤的狀態下運行」），故不算否定該歸因。

**突變驗證**（結果記於本單元 `code-summary.md` 的 2026-11-07 一節）：在 scratchpad
副本把 docstring 還原成舊句 → `test_B1` 紅；還原 → 綠。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import re
import unittest
from unittest.mock import patch

import services.hierarchy_service as hierarchy_service
import services.membership_backfill as membership_backfill
from tests.helpers import close_session, make_session, make_user

# 「孤兒擁有者」這個歸因的各種說法。
_ORPHAN_ATTRIBUTION = re.compile(r"指向不存在的使用者|孤兒")
# 足以否定該歸因的詞；刻意不含一般的「不是」（見模組 docstring）。
_NEGATION = re.compile(r"不要預設|不可能|不會是")


def _sentences(text: str) -> list[str]:
    """以句號、分號與空行切句；同一句內的否定才算否定該歸因。"""
    return [s for s in re.split(r"[。；]|\n\s*\n", text) if s.strip()]


def _unnegated_orphan_attributions(text: str) -> list[str]:
    return [
        " ".join(s.split())
        for s in _sentences(text)
        if _ORPHAN_ATTRIBUTION.search(s) and not _NEGATION.search(s)
    ]


class BackfillFailureAttributionTest(unittest.TestCase):
    def test_B1_module_docstring_does_not_blame_orphan_owners(self):
        """
        @purpose 維運者面對 backend 重啟迴圈時讀的模組說明，不得把失敗歸因於外鍵使其不可能存在的「孤兒擁有者」，且必須點名兩類實際原因
        @given services/membership_backfill.py 的模組 docstring
        @step 逐句找出提到「指向不存在的使用者」或「孤兒」的句子 | 每一句都同句帶「不要預設」「不可能」或「不會是」
        @step 檢查是否點名外鍵與兩類實際原因 | 含「外鍵」、「剩餘零成員專案數」與「INSERT」
        @pass 沒有未被否定的孤兒歸因，且三個關鍵詞皆在
        @story US12.1
        @note 舊句「一個持續性的失敗（例如某專案的 owner_user_id 指向不存在的使用者）」只帶一般的「不是」，會被判為未否定。
        """
        doc = membership_backfill.__doc__ or ""
        self.assertEqual(_unnegated_orphan_attributions(doc), [])
        for keyword in ("外鍵", "剩餘零成員專案數", "INSERT"):
            self.assertIn(keyword, doc)


class BackfillRuntimeMessageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.engine = self.db._test_engine
        alice = make_user(self.db, username="alice", role="Project_Architect")
        # 零成員專案：使終檢在插入被替換成 no-op 時必然不為 0。
        hierarchy_service.create_project(self.db, owner_user_id=alice.id, name="P")
        self.db.commit()

    def tearDown(self) -> None:
        close_session(self.db)

    def test_B2_self_check_failure_message_does_not_blame_orphan_owners(self):
        """
        @purpose 終檢失敗時的執行期訊息（寫進 log 的那一行）必須與模組說明一致：回報剩餘數、指明外鍵使孤兒擁有者不可能
        @given 一個零成員專案；插入步驟被替換成不寫任何列
        @step 呼叫 run_backfill(engine) | 拋 BackfillVerificationError
        @step 逐句檢查例外訊息 | 提到孤兒的句子同句帶否定詞，且訊息含「仍有 1 個零成員專案」與「外鍵」
        @pass 訊息回報實際剩餘數，且沒有未被否定的孤兒歸因
        @story US12.1
        """
        with patch.object(membership_backfill, "backfill", return_value=0):
            with self.assertRaises(membership_backfill.BackfillVerificationError) as ctx:
                membership_backfill.run_backfill(self.engine)
        message = str(ctx.exception)
        self.assertIn("仍有 1 個零成員專案", message)
        self.assertIn("外鍵", message)
        self.assertEqual(_unnegated_orphan_attributions(message), [])


if __name__ == "__main__":
    unittest.main()
