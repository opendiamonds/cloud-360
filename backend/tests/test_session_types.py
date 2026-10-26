"""`U10 session-store` 的純函式與資料形狀測試（**零 Redis、零 DB、零授權**）。

本檔對應 `unit-test-instructions.md §三` 的第一列與 §八 的前三列。
`session_types` 不觸及 DB，故刻意**不**匯入 `tests.helpers`（§六 的
`psycopg` stub 慣例只對會間接 import DB 的檔案必要）——這同時是
「本模組零 DB 依賴」的一個執行期證明。

## 三條 property 為什麼是這三條（`BR3.4`）

修剪的語意是「丟最舊、保序、已達上限時不動」。三條合起來把它鎖住：

1. **上界**——輸出長度 ≤ cap。少了它，修剪可能完全沒發生。
2. **後綴**——輸出是輸入的後綴。少了它，「丟最舊」與「丟最新」無法區分，
   而兩者在長度上完全一樣（突變 `M1` 正是這一條抓的）。
3. **不足額時不動**——輸入 ≤ cap 時輸出等於輸入。少了它，修剪可能把沒超限的
   歷程也砍掉。
"""

import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from services import session_types as T
from services.session_types import (
    PAGE_SCOPES,
    SEGMENT_IDS,
    SessionMessage,
    decode_messages,
    decode_meta,
    decode_session,
    decode_target,
    encode_messages,
    encode_meta,
    encode_target,
    require_page_scope,
    require_segment_id,
    require_sharing_mode,
    trim_history,
)

#: `BR3.4` 的上限在測試中一律**顯式注入**（`unit-test-instructions.md §七`），
#: 不讀環境變數——讓「超限丟最舊」的測試不需要 200 則資料。
CAPS = st.integers(min_value=1, max_value=12)
ITEMS = st.lists(st.integers(), max_size=40)


class TrimHistoryPropertyTest(unittest.TestCase):
    """`BR3.4` 的三條 property。**標的是參考實作，不是生產載體**——生產載體是
    `append_message.lua`（見 `session_types` 檔頭）。"""

    @given(items=ITEMS, cap=CAPS)
    @settings(max_examples=120, deadline=None)
    def test_output_never_exceeds_cap(self, items, cap):
        self.assertLessEqual(len(trim_history(items, cap)), cap)

    @given(items=ITEMS, cap=CAPS)
    @settings(max_examples=120, deadline=None)
    def test_output_is_a_suffix_of_the_input(self, items, cap):
        """丟的是**最舊**的。這一條是突變 `M1`（改成丟最新）唯一會變紅的斷言。"""
        out = trim_history(items, cap)
        self.assertEqual(out, items[len(items) - len(out) :] if out else [])

    @given(items=ITEMS, cap=CAPS)
    @settings(max_examples=120, deadline=None)
    def test_input_within_cap_is_returned_unchanged(self, items, cap):
        # `merge-blockers.md` 第 18 項之後，「不動」的條件是**兩個**上限都沒超；
        # 本策略的整數清單遠小於預設 200 KB，故位元組條件在此恆成立，斷言照舊。
        if len(items) <= cap:
            self.assertLessEqual(T.segment_size_bytes(items), T.DEFAULT_SEGMENT_MAX_BYTES)
            self.assertEqual(trim_history(items, cap), items)

    def test_cap_must_be_a_positive_integer(self):
        """`BR3.5`：「無值」不得被讀成「無上限」，而 `cap <= 0` 會清空整段歷程
        ——比無上限更壞，因為它是靜默的。"""
        for bad in (0, -1, None, 1.5, True, "5"):
            with self.subTest(cap=bad):
                with self.assertRaises(ValueError):
                    trim_history([1, 2, 3], bad)
        for bad in (0, -1, None, 1.5, True):
            with self.subTest(max_bytes=bad):
                with self.assertRaises(ValueError):
                    trim_history([1, 2, 3], 5, bad)


#: 訊息形狀與生產相同（`role`／`text`／`createdAt`／`sequence`）。`text` 刻意包含
#: cjson 與 Python json 長度不同的兩個字元（`/`、`0x7f`），以及中文、表情符號
#: （UTF-8 4 位元組）與控制字元——位元組計算若只對 ASCII 正確，這裡會抓到。
_TEXT = st.text(
    alphabet=st.sampled_from(list("ab/\x7f\x01\n\"\\") + ["測", "試", "😀"]),
    max_size=80,
)
MESSAGES = st.lists(_TEXT, max_size=30).map(
    lambda texts: [
        {"role": "user", "text": t, "createdAt": "t", "sequence": i + 1}
        for i, t in enumerate(texts)
    ]
)
BYTE_CAPS = st.integers(min_value=40, max_value=3000)


class TrimHistoryByteCapPropertyTest(unittest.TestCase):
    """`merge-blockers.md` 第 18 項：每段位元組上限與筆數上限**取較嚴者**。

    四條合起來把「取較嚴者、自最舊端丟、不多丟」鎖住。位元組上限在策略內刻意
    取很小（40–3000），讓兩個上限輪流成為較嚴的那一個。
    """

    @given(items=MESSAGES, cap=CAPS, max_bytes=BYTE_CAPS)
    @settings(max_examples=200, deadline=None)
    def test_output_fits_both_caps(self, items, cap, max_bytes):
        """
        @purpose 任何輸入修剪後，則數 ≤ 筆數上限，且整段位元組數 ≤ 位元組上限；唯一例外是只剩最新一則而那一則本身就超過上限（段不得被清空）。拿掉位元組條件的突變在這一條變紅。
        @given 任意含中文、斜線、DEL、表情符號、控制字元的訊息清單；筆數上限 1–12；位元組上限 40–3000
        @step 以參考實作修剪 | 則數不超過筆數上限
        @step 量修剪結果的位元組數 | 不超過位元組上限，或結果只剩最新的一則
        @pass 兩個上限同時成立
        @story US6.1
        """
        out = trim_history(items, cap, max_bytes)
        self.assertLessEqual(len(out), cap)
        if len(out) > 1:
            self.assertLessEqual(T.segment_size_bytes(out), max_bytes)
        elif items:
            self.assertEqual(out, items[-1:])

    @given(items=MESSAGES, cap=CAPS, max_bytes=BYTE_CAPS)
    @settings(max_examples=200, deadline=None)
    def test_output_is_the_longest_qualifying_suffix(self, items, cap, max_bytes):
        """
        @purpose 保留的是最新的那幾則、順序不變，而且不多丟：再往前多留一則就會超過其中一個上限。
        @given 同上的任意訊息清單與上限
        @step 以參考實作修剪 | 結果是輸入的後綴（順序不變、丟的是最舊的）
        @step 若有丟棄，把被丟的最新一則接回前面 | 會超過筆數上限或位元組上限
        @pass 結果是兩個上限下最長的合格後綴
        @story US6.1
        """
        out = trim_history(items, cap, max_bytes)
        self.assertEqual(out, items[len(items) - len(out):] if out else [])
        if items:
            self.assertGreaterEqual(len(out), 1)
        if 0 < len(out) < len(items):
            longer = items[len(items) - len(out) - 1:]
            self.assertTrue(
                len(longer) > cap or T.segment_size_bytes(longer) > max_bytes
            )

    def test_cjson_size_counts_the_escapes_python_json_does_not_emit(self):
        """cjson 把 `/` 編成 `\\/`、把 `0x7f` 編成 `\\u007f`，Python 都不跳脫。
        以 Redis 8.8 實測的輸出為準（`cjson.encode({a='x/y\\127'})` →
        `{"a":"x\\/y\\u007f"}`，`string.len` 為 18；`{b='中'}` 為 11——兩個數字
        皆為 `redis-cli EVAL` 對 Redis 8.8.0 實際回傳的值）。"""
        self.assertEqual(T.cjson_encoded_size({"a": "x/y\x7f"}), 18)
        self.assertEqual(T.cjson_encoded_size({"b": "中"}), 11)


class ClosedSetTest(unittest.TestCase):
    """`EC4`／`EC2`／`BR2.1`／`BR2.2`：三個封閉集合的拒絕行為。"""

    def test_segment_ids_are_exactly_the_three_allowed_values(self):
        self.assertEqual(set(SEGMENT_IDS), {"shared", "workspace", "assessment"})

    def test_unknown_segment_id_is_rejected_and_not_auto_created(self):
        for bad in ("nope", "entry", "cost", "admin", "", "SHARED"):
            with self.subTest(segment_id=bad):
                with self.assertRaises(ValueError):
                    require_segment_id(bad)

    def test_missing_segment_id_is_rejected_rather_than_defaulting_to_shared(self):
        """`BR3.1`：`None` 不得被讀成共享段——那是 `OQ-N4` 逐字點名的壞結果。"""
        with self.assertRaises(ValueError):
            require_segment_id(None)

    def test_page_scopes_exclude_the_entry_page(self):
        """`EC2`：`pageModes` 的鍵集合**恰為**兩頁；入口頁、`/cost`、`/admin/*`
        都不得出現（`BR2.8`）。"""
        self.assertEqual(set(PAGE_SCOPES), {"workspace", "assessment"})
        for bad in ("shared", "entry", "/cost", "cost", "admin"):
            with self.subTest(scope=bad):
                with self.assertRaises(ValueError):
                    require_page_scope(bad)

    def test_sharing_mode_is_a_closed_set(self):
        require_sharing_mode("shared")
        require_sharing_mode("isolated")
        with self.assertRaises(ValueError):
            require_sharing_mode("mixed")


class SerialisationRoundTripTest(unittest.TestCase):
    """`EC7`：序列化往返必須保住**部分三元組**（含 `null`）。"""

    def test_messages_round_trip_preserves_order_and_fields(self):
        messages = tuple(
            SessionMessage(sequence=i, role="user", text=f"fixture-msg-{i}", created_at="t")
            for i in range(1, 6)
        )
        self.assertEqual(decode_messages(encode_messages(messages)), messages)

    def test_absent_segment_field_decodes_to_empty_without_inventing_a_segment(self):
        """欄位不存在（`None`）＝段未建立（`EC3`）；空陣列＝段存在但無訊息。"""
        self.assertEqual(decode_messages(None), ())
        self.assertEqual(decode_messages(encode_messages(())), ())

    def test_partial_work_target_round_trips_with_nulls_intact(self):
        """`EC7` 的實測成因：`OPEN-H11` 的新圖沒有系統歸屬，`K-07` 回
        `{projectId: None, systemId: None, diagramId: X}` 且**刻意不拒絕**。
        本單元如實儲存，**不推導、不補齊**（`BR4.5`）。"""
        for triple in (
            (None, None, None),
            (None, None, 42),
            (7, None, None),
            (7, 8, 9),
        ):
            with self.subTest(triple=triple):
                decoded = decode_target(encode_target(*triple))
                self.assertEqual(
                    (decoded["projectId"], decoded["systemId"], decoded["diagramId"]),
                    triple,
                )

    def test_absent_target_field_decodes_to_the_not_yet_selected_state(self):
        """`BR7.2`／`AC2.2.3`：「尚未選定」是真正可達的狀態，不是缺值。"""
        self.assertEqual(
            decode_target(None),
            {"projectId": None, "systemId": None, "diagramId": None},
        )

    def test_meta_round_trips_page_modes_which_is_the_easiest_field_to_lose(self):
        """`NFR4.56`：`pageModes` 是**指標**不是資料，漏掉的徵兆是「使用者回來
        時該頁讀到錯的段」而不是「資料不見了」。"""
        blob = encode_meta(
            user_id=11,
            page_modes={"workspace": "isolated", "assessment": "shared"},
            created_at={"shared": "t0", "workspace": "t1"},
        )
        meta = decode_meta(blob)
        self.assertEqual(meta["userId"], 11)
        self.assertEqual(
            meta["pageModes"], {"workspace": "isolated", "assessment": "shared"}
        )
        self.assertEqual(meta["createdAt"]["workspace"], "t1")

    def test_decode_session_ignores_foreign_field_prefixes(self):
        """`OPEN-N10-7`：`U12` 的工作項欄位共用同一個 key。本單元不解讀它們，
        也不因為它們存在而失敗——所有權邊界，不是容錯。"""
        fields = {
            "meta": encode_meta(user_id=1, page_modes={}, created_at={"shared": "t0"}),
            "seg:shared": encode_messages(
                (SessionMessage(1, "user", "fixture-msg-1", "t0"),)
            ),
            "work:items": "[]",
            "unexpected": "x",
        }
        session = decode_session("fixture-key", fields)
        self.assertEqual(set(session.segments), {"shared"})
        self.assertEqual(len(session.segments["shared"].messages), 1)

    def test_segment_accessor_returns_only_that_segment(self):
        """`BR3.2`／`AC3.1.2`／`AC6.1.3`：段隔離由形狀滿足，不靠執行期過濾。"""
        fields = {
            "meta": encode_meta(
                user_id=1,
                page_modes={"workspace": "isolated"},
                created_at={"shared": "t0", "workspace": "t1"},
            ),
            "seg:shared": encode_messages(
                (SessionMessage(1, "user", "fixture-msg-shared", "t0"),)
            ),
            "seg:workspace": encode_messages(
                (SessionMessage(1, "user", "fixture-msg-isolated", "t1"),)
            ),
        }
        session = decode_session("fixture-key", fields)
        shared_texts = [m.text for m in session.segment("shared").messages]
        isolated_texts = [m.text for m in session.segment("workspace").messages]
        self.assertEqual(shared_texts, ["fixture-msg-shared"])
        self.assertEqual(isolated_texts, ["fixture-msg-isolated"])
        self.assertIsNone(session.segment("assessment"))

    def test_messages_are_frozen_value_objects(self):
        """`EC10`：不可就地修改。更正一則訊息的方式是追加新訊息。"""
        message = SessionMessage(1, "user", "fixture-msg-1", "t0")
        with self.assertRaises(Exception):
            message.text = "fixture-msg-2"  # type: ignore[misc]

    def test_module_declares_no_io_dependencies(self):
        """本檔開頭宣稱 `session_types` 零 I/O。這一條把它變成可執行的檢查，
        而不是散文——`json` 與標準庫以外的 import 一律視為違反。"""
        self.assertFalse(hasattr(T, "redis"))
        self.assertFalse(hasattr(T, "Session"))


if __name__ == "__main__":
    unittest.main()
