"""合併前必修第 33 列 (e) 的 `query` 半部：`MemoryFacade.search` 截斷到 4000 字元。

2026-10-31 使用者裁決：`query` 超過 4000 字元時只取前 4000 字元去做 embedding 與搜尋，
**不報錯**；兩個同進程呼叫端（`intent_routing.py`、`brain_gateway.py` 的預取）不改。

以一個只記錄輸入的 Port 注入 facade（`embed` 回空串列，使 search 在取向量後即結束，
不碰 SQLite 上不存在的向量運算）——驗的是「送進 embedding 的是什麼」，那正是截斷的
全部可觀察後果。

**突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
  M1 拿掉截斷 → 案例 2、3 紅；
  M2 截斷改成拒絕（raise MemoryInvalidInput）→ 案例 2、3 紅；
  M3 上限改為 3999 → 案例 1–3 紅。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from services.embedding_port import EmbeddingPort
from services.hierarchy_facade import mint_principal
from services.memory_facade import MEMORY_QUERY_MAX_CHARS, MemoryFacade
from tests.helpers import close_session, make_session, make_user


class RecordingPort(EmbeddingPort):
    def __init__(self) -> None:
        self.inputs: list = []

    def model_id(self) -> str:
        return "recording-v1"

    def embed(self, texts):
        self.inputs.append(list(texts))
        return []


class MemoryQueryTruncationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.user = make_user(self.db, username="alice", role="Developer")
        self.port = RecordingPort()
        self.facade = MemoryFacade(self.db, port=self.port)
        self.principal = mint_principal(self.user)

    def tearDown(self) -> None:
        close_session(self.db)

    def embedded(self) -> str:
        self.assertEqual(len(self.port.inputs), 1)
        (text,) = self.port.inputs[0]
        return text

    def test_query_of_exactly_4000_chars_is_passed_unchanged(self):
        """
        @purpose 恰為上限的 query 原樣送進 embedding（邊界內側）；上限常數為裁決值
        @given 已核准使用者、記錄輸入的 Port
        @step search(query = 4000 個字元)
        @pass 不拋例外；送進 embed 的字串與原 query 逐字相同
        @story US4.1
        """
        self.assertEqual(MEMORY_QUERY_MAX_CHARS, 4000)
        query = "q" * 4000
        self.assertEqual(self.facade.search(self.principal, query), [])
        self.assertEqual(self.embedded(), query)

    def test_query_over_4000_chars_is_truncated_not_rejected(self):
        """
        @purpose 超過上限的 query 不報錯，只取前 4000 字元
        @given 已核准使用者、記錄輸入的 Port
        @step search(query = 4000 個 a ＋ 10 個 b)
        @pass 不拋例外；送進 embed 的是前 4000 個 a，後段的 b 不在其中
        @story US4.1
        """
        query = "a" * 4000 + "b" * 10
        self.facade.search(self.principal, query)
        self.assertEqual(self.embedded(), "a" * 4000)

    def test_truncation_counts_characters_not_bytes(self):
        """
        @purpose 截斷以字元計：4001 個中文字被截成 4000 個中文字（不是切在位元組中間）
        @given 已核准使用者、記錄輸入的 Port
        @step search(query = 4001 個「記」)
        @pass 送進 embed 的是 4000 個「記」
        @story US4.1
        """
        self.facade.search(self.principal, "記" * 4001)
        self.assertEqual(self.embedded(), "記" * 4000)


if __name__ == "__main__":
    unittest.main()
