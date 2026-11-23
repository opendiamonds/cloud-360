"""261116-brain-create-diagram U2：BrainDiagramCreation 的純函式與變更紀錄。

追溯：FR2.2／FR2.3（判定表與四項性質，ADR-0006 agent routing PBT hard constraint）、
FR6.3a（草稿優先反問）、FR5.1～FR5.4（取名）、FR7.1（變更紀錄）。
純函式不經 HTTP，故無 `@api`／`@ui`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unicodedata
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from models import DiagramChangeRecord
from services import brain_diagram_creation as B
from services.hierarchy_facade import HierarchyFacade, mint_principal
from tests.helpers import close_session, make_diagram, make_session, make_user

PROBS = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
THRESHOLDS = st.floats(min_value=0.5, max_value=1.0, allow_nan=False, exclude_min=True)
KINDS = st.sampled_from(B.TARGET_KINDS)


class DecideTableTest(unittest.TestCase):
    """判定表（FR2.2）的每一格，以 t=0.7 的三個代表值。"""

    T = 0.7
    NEW, MOD, UNCLEAR = 0.9, 0.1, 0.5

    def check(self, kind, has_diagrams, has_drafts, expected):
        got = tuple(
            B.decide(p, self.T, kind, has_diagrams, has_drafts)
            for p in (self.NEW, self.MOD, self.UNCLEAR)
        )
        self.assertEqual(expected, got)

    def test_system_without_diagrams(self):
        """
        @purpose FR2.2 第一列：系統下沒有圖 → 新建／回覆沒圖可改（FR2.4）／新建
        @given 作業對象是系統、沒有圖
        @step 依 p 的三區判定 | (create, no_diagram_to_modify, create)
        @pass 三格皆符合
        @story FR2.2、FR2.4
        """
        self.check(B.TARGET_SYSTEM, False, False, (B.CREATE, B.NO_DIAGRAM_TO_MODIFY, B.CREATE))

    def test_system_with_ready_diagrams(self):
        """
        @purpose FR2.2 第二列：有圖 → 新建／修改／反問
        @given 作業對象是系統、有正式圖、沒有草稿
        @step 依 p 的三區判定 | (create, modify, new_or_modify)
        @pass 三格皆符合
        @story FR2.2
        """
        self.check(B.TARGET_SYSTEM, True, False, (B.CREATE, B.MODIFY, B.ASK_NEW_OR_MODIFY))

    def test_system_with_drafts_asks_first_even_when_p_is_high(self):
        """
        @purpose FR6.3a 優先於判定表第二列：系統下有草稿，即使 p ≥ t 也先反問；
                 只有草稿、沒有正式圖的系統同樣適用
        @given 作業對象是系統、系統下有草稿
        @step 依 p 的三區判定 | (resume_draft_or_new, modify, resume_draft_or_new)
        @pass 三格皆符合
        @story FR6.3a
        """
        self.check(B.TARGET_SYSTEM, True, True,
                   (B.ASK_RESUME_DRAFT, B.MODIFY, B.ASK_RESUME_DRAFT))

    def test_ready_diagram_target(self):
        """
        @purpose FR2.2 第三列：作業對象是某張正式圖
        @given 作業對象是正式圖
        @step 依 p 的三區判定 | (create, modify, new_or_modify)
        @pass 三格皆符合
        @story FR2.2
        """
        self.check(B.TARGET_DIAGRAM, True, False, (B.CREATE, B.MODIFY, B.ASK_NEW_OR_MODIFY))

    def test_draft_diagram_target_continues_the_same_draft(self):
        """
        @purpose FR6.3：作業對象仍是那張草稿時再說一次 → 接著畫同一張，不另建新圖
        @given 作業對象是草稿
        @step 依 p 的三區判定 | (modify, modify, new_or_modify)
        @pass p ≥ t 時也不新建
        @story FR6.3、FR6.3b
        """
        self.check(B.TARGET_DIAGRAM, True, True, (B.MODIFY, B.MODIFY, B.ASK_NEW_OR_MODIFY))

    def test_no_target_or_project_asks_for_a_system(self):
        """
        @purpose FR3.1：沒有作業對象或只是專案 → 反問要掛在哪個系統；明確修改沿用既有路徑
        @given 沒有作業對象、或作業對象是專案
        @step 依 p 的三區判定 | (pick_system, modify, pick_system)
        @pass 兩種對象結果相同
        @story FR3.1
        """
        for kind in (B.TARGET_NONE, B.TARGET_PROJECT):
            with self.subTest(kind=kind):
                self.check(kind, False, False, (B.ASK_PICK_SYSTEM, B.MODIFY, B.ASK_PICK_SYSTEM))

    def test_missing_probability_is_treated_as_unclear(self):
        """
        @purpose 本機工具呼叫路徑沒有這一題（p=None）時，不得被當成「要新的」
        @given 作業對象是有圖的系統
        @step p=None | new_or_modify
        @pass 結果為反問
        @story FR2.1
        """
        self.assertEqual(B.ASK_NEW_OR_MODIFY, B.decide(None, self.T, B.TARGET_SYSTEM, True, False))

    def test_invalid_inputs_raise_value_error_not_http(self):
        """
        @purpose 純函式的輸入錯誤以 ValueError 表示（不拋 HTTPException）
        @given 越界的 t、p 與未知的對象種類
        @step 各呼叫一次 | ValueError
        @pass 三者皆 ValueError
        @story FR2.3
        """
        for args in ((0.5, 0.5), (0.5, 1.1), (1.5, 0.7)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                B.decide(args[0], args[1], B.TARGET_SYSTEM, True, False)
        with self.assertRaises(ValueError):
            B.decide(0.5, 0.7, "galaxy", True, False)


class DecidePropertiesTest(unittest.TestCase):
    """FR2.3 四項性質（ADR-0006 PBT hard constraint）。"""

    @settings(max_examples=500)
    @given(p=PROBS, t=THRESHOLDS, kind=KINDS, has_d=st.booleans(), has_dr=st.booleans())
    def test_create_and_modify_are_mutually_exclusive_and_total(self, p, t, kind, has_d, has_dr):
        """
        @purpose 性質 1（修訂 1 改寫）：互斥直接斷言在判定結果上——要新的（p ≥ t）不得被判成修改，
                 要修改（p ≤ 1−t）不得被判成新建。唯一例外是偏差 #2：作業對象是草稿時 p ≥ t
                 也接著畫同一張（FR6.3b），由本性質明確框住、不再被恆真式掩蓋。
        @given 任意 p、t ∈ (0.5, 1]、對象與旗標
        @step 判定 | 結果屬於 DECISIONS
        @step p ≥ t | 結果不是 MODIFY／NO_DIAGRAM_TO_MODIFY（草稿作業對象除外，此時必為 MODIFY）
        @step p ≤ 1−t | 結果不是 CREATE
        @pass 不存在反例
        @story FR2.3、FR6.3b
        """
        result = B.decide(p, t, kind, has_d, has_dr)
        self.assertIn(result, B.DECISIONS)
        if p >= t:
            if kind == B.TARGET_DIAGRAM and has_dr:
                self.assertEqual(B.MODIFY, result)  # 偏差 #2（已於關卡接受）
            else:
                self.assertNotIn(result, (B.MODIFY, B.NO_DIAGRAM_TO_MODIFY))
        if p <= 1.0 - t:
            self.assertNotEqual(B.CREATE, result)

    @settings(max_examples=300)
    @given(p=PROBS, t=THRESHOLDS, has_dr=st.booleans(), kind=st.sampled_from((B.TARGET_SYSTEM, B.TARGET_DIAGRAM)))
    def test_unclear_zone_always_asks_when_the_target_has_diagrams(self, p, t, has_dr, kind):
        """
        @purpose 性質 2：作業對象有圖時，1−t < p < t 一定反問
        @given 有圖的系統或某張圖、p 落在不明區
        @step 判定 | 結果為反問種類之一
        @pass 不明區內絕不新建、也不修改
        @story FR2.3
        """
        if not (1.0 - t < p < t):
            return
        result = B.decide(p, t, kind, True, has_dr)
        self.assertIn(result, (B.ASK_NEW_OR_MODIFY, B.ASK_RESUME_DRAFT))

    @settings(max_examples=300)
    @given(p1=PROBS, p2=PROBS, t=THRESHOLDS, kind=KINDS, has_d=st.booleans(), has_dr=st.booleans())
    def test_monotonic_in_p(self, p1, p2, t, kind, has_d, has_dr):
        """
        @purpose 性質 3：p 增加不會使結果由「新建」變為「修改」
        @given 任意 p1 ≤ p2 與相同的其他輸入
        @step 分別判定 | 若 p1 為新建，p2 不得為修改
        @pass 不存在反例
        @story FR2.3
        """
        low, high = sorted((p1, p2))
        if B.decide(low, t, kind, has_d, has_dr) == B.CREATE:
            self.assertNotEqual(B.MODIFY, B.decide(high, t, kind, has_d, has_dr))
        self.assertFalse(
            B.decide(low, t, kind, has_d, has_dr) == B.CREATE
            and B.decide(high, t, kind, has_d, has_dr) in (B.MODIFY, B.NO_DIAGRAM_TO_MODIFY)
        )

    @settings(max_examples=500)
    @given(
        zone=st.sampled_from(("new", "modify", "unclear")),
        u1=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        u2=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        t=THRESHOLDS,
        kind=KINDS,
        has_d=st.booleans(),
        has_dr=st.booleans(),
    )
    def test_deterministic(self, zone, u1, u2, t, kind, has_d, has_dr):
        """
        @purpose 性質 4（修訂 1 改寫）：判定只由「p 落在哪一區」與其餘輸入決定——同一區的兩個 p
                 （不明區含 p=None）結果必定相同。原寫法對同一輸入呼叫兩次，不可能失敗；
                 本寫法在判定改用 t 以外的邊界、或對 None 與不明區的數值分開處理時會紅燈。
        @given 先抽區域，再於該區內依 t 構造兩個 p（以測試自己的區域定義，不借用被測模組）
        @step 兩個同區的 p 分別判定 | 結果相同
        @pass 不存在反例
        @story FR2.3
        """

        def p_in_zone(u):
            if zone == "new":
                return 1.0 if u is None else t + u * (1.0 - t)
            if zone == "modify":
                return 0.0 if u is None else u * (1.0 - t)
            if u is None:
                return None  # 沒有取得 p：屬不明區
            p = (1.0 - t) + u * (2.0 * t - 1.0)
            return p if 1.0 - t < p < t else None  # 端點落在別區時改用 None（同屬不明）

        p1, p2 = p_in_zone(u1), p_in_zone(u2)
        self.assertEqual(
            B.decide(p1, t, kind, has_d, has_dr), B.decide(p2, t, kind, has_d, has_dr)
        )


class MakeTitleTest(unittest.TestCase):
    def test_examples(self):
        """
        @purpose FR5.1／FR5.2／FR5.4 的例子：去頭尾指令詞、空主題退回系統名、重名加序號
        @given 幾句典型的畫圖請求
        @step 取名 | 符合預期
        @pass 每一句的名稱皆等於預期
        @story FR5.1、FR5.2、FR5.4
        """
        cases = [
            ("幫我畫一張電商網站的 AWS 架構圖", "電商網站的 AWS 架構圖"),
            ("請幫我畫一張新的電商架構圖。", "電商 架構圖"),
            ("幫我畫一張架構圖", "訂單系統 架構圖"),
            ("<b>**金流**</b> 架構圖", "金流 架構圖"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(expected, B.make_title(text, "訂單系統", ()))
        self.assertEqual(
            "電商 架構圖（3）",
            B.make_title("畫一張電商架構圖", "S", ["電商 架構圖", "電商 架構圖（2）"]),
        )

    def test_topic_is_truncated_without_splitting_combining_marks(self):
        """
        @purpose FR5.3：以可見字元截長且不切斷組合字元；控制字元去除
        @given 40 個「é」（e ＋ 組合重音）與一個控制字元
        @step 取名 | 主題恰 30 個可見字元，每個都帶重音
        @pass 沒有落單的組合記號、沒有控制字元
        @story FR5.3
        """
        text = "é" * 40 + "\x07"
        title = B.make_title(text, "S", ())
        topic = title[: -len(" 架構圖")]
        self.assertEqual(30, len(B.graphemes(topic)))
        self.assertTrue(all(g == "é" for g in B.graphemes(topic)))
        self.assertNotIn("\x07", title)

    @settings(max_examples=300)
    @given(
        text=st.text(max_size=200),
        system=st.text(max_size=60),
        existing=st.lists(st.text(max_size=40), max_size=6),
    )
    def test_title_properties(self, text, system, existing):
        """
        @purpose FR5 的取名性質：主題長度上限、不含控制字元、不切斷組合字元、與既有名稱不重複
        @given 任意文字、系統名與既有名稱
        @step 取名 | 名稱非空且以「架構圖」收尾（可帶序號）
        @pass 四項性質皆成立
        @story FR5.1、FR5.3、FR5.4
        """
        title = B.make_title(text, system, existing)
        self.assertNotIn(title, set(existing))
        self.assertTrue(title)
        self.assertFalse(any(unicodedata.category(ch) == "Cc" for ch in title))
        base = title
        if title.endswith("）"):
            head, _sep, tail = title[:-1].rpartition("（")
            if tail.isdigit() and head.endswith(B.TITLE_SUFFIX):
                base = head
        self.assertTrue(base.endswith(B.TITLE_SUFFIX))
        topic = base[: -len(B.TITLE_SUFFIX)].rstrip()
        self.assertLessEqual(len(B.graphemes(topic)), B.TITLE_TOPIC_MAX_GRAPHEMES)
        if topic:
            self.assertFalse(B._is_extender(topic[0]), "主題不得以落單的組合記號開頭")
        self.assertLessEqual(len(title), B.TITLE_MAX_CODEPOINTS)

    @settings(max_examples=300)
    @given(
        clusters=st.lists(
            st.tuples(
                st.sampled_from(("e", "a", "架", "👨", "👩")),
                st.sampled_from(("\u0301", "\u0308", "\ufe0f", "\U0001F3FB", "\u200d👧")),
                st.integers(min_value=0, max_value=120),
            ),
            min_size=1,
            max_size=40,
        ),
        system=st.text(alphabet=st.sampled_from(("S", "\u0301", "\u200d")), max_size=400),
        dup=st.integers(min_value=0, max_value=5),
    )
    def test_title_never_exceeds_the_endpoint_code_point_limit(self, clusters, system, dup):
        """
        @purpose 修訂 1（FR5.3，審查 R-05／R-09）：可見字元上限擋不住「一個可見字元帶上百個組合記號／ZWJ」
                 的輸入；名稱總碼位必須永遠不超過端點上限 200（含重名後綴），否則 POST 回 422、重說也一直失敗。
        @given 由基底字元＋大量組合記號／ZWJ／變體選擇器／膚色修飾組成的句子；同樣病態的系統名；
               既有名稱含本次取名結果的 0～5 個重名版本
        @step 取名 | 碼位數 ≤ TITLE_MAX_CODEPOINTS，且不以落單的組合記號開頭
        @pass 不存在反例
        @story FR5.3、FR5.4
        """
        text = "".join(base + mark * count for base, mark, count in clusters)
        first = B.make_title(text, system, ())
        existing = [first] + [f"{first}（{n}）" for n in range(2, 2 + dup)]
        title = B.make_title(text, system, existing if dup else ())
        self.assertLessEqual(len(title), B.TITLE_MAX_CODEPOINTS)
        self.assertFalse(B._is_extender(title[0]))

    def test_code_point_limit_equals_the_endpoint_limit(self):
        """
        @purpose 碼位上限在純函式模組與端點各有一份（純函式不 import router）；本案例鎖住兩者相等（team.md 單一真實來源）。
        @given brain_diagram_creation 與 collab_router 的常數
        @step 比較 | 相等
        @pass 相等
        @story FR5.3
        """
        from services.collab_router import MAX_DIAGRAM_TITLE_CHARS

        self.assertEqual(MAX_DIAGRAM_TITLE_CHARS, B.TITLE_MAX_CODEPOINTS)

    def test_one_huge_visible_character_falls_back_to_the_system_name(self):
        """
        @purpose 修訂 1（FR5.3）：單一可見字元本身就超過碼位預算時，不切斷它，而是不收入主題；
                 主題因此為空 → 退回「<系統名> 架構圖」（FR5.2）。
        @given 「e」後接 500 個組合重音
        @step 取名 | 「S 架構圖」
        @pass 相等且在上限內
        @story FR5.2、FR5.3
        """
        self.assertEqual("S 架構圖", B.make_title("e" + "\u0301" * 500, "S", ()))

    @settings(max_examples=100)
    @given(text=st.text(max_size=80), system=st.text(max_size=20))
    def test_title_is_deterministic(self, text, system):
        """
        @purpose 取名不呼叫模型、無隨機：相同輸入相同名稱
        @given 任意輸入
        @step 取名兩次 | 相同
        @pass 相等
        @story FR5.1
        """
        self.assertEqual(B.make_title(text, system, ()), B.make_title(text, system, ()))


class RecordCreationTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.alice = make_user(self.db, username="alice", role="Project_Architect")
        self.diagram = make_diagram(self.db, owner=self.alice, title="電商 架構圖")

    def tearDown(self):
        close_session(self.db)

    def test_writes_one_brain_row_with_the_contract_texts(self):
        """
        @purpose FR7.1／契約 C5：經大腦建立記一筆，source=brain_orchestration、摘要非空
        @given alice 的一張圖
        @step record_creation | 回 True
        @step 讀 diagram_change_records | 恰一列，摘要「經大腦建立「電商 架構圖」」、標籤「大腦建立架構圖」
        @pass 欄位逐一相符，actor 為 alice
        @story FR7.1
        """
        ok = B.record_creation(
            HierarchyFacade(self.db), mint_principal(self.alice),
            diagram_id=self.diagram.id, title="電商 架構圖",
        )
        self.assertTrue(ok)
        rows = self.db.query(DiagramChangeRecord).all()
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual(
            (row.diagram_id, row.source, row.requirement_summary, row.requirement_label, row.actor_user_id),
            (self.diagram.id, "brain_orchestration", "經大腦建立「電商 架構圖」", "大腦建立架構圖", self.alice.id),
        )

    def test_failure_is_logged_and_does_not_raise(self):
        """
        @purpose 契約 C5 錯誤表：變更紀錄寫入失敗只記 log，不影響後續交辦
        @given 一個會拋例外的 facade 替身
        @step record_creation | 回 False，不拋例外；log 不含圖名
        @pass 回傳 False 且 log 只含類別名
        @story FR7.1
        """
        class Boom:
            def record_diagram_change(self, *_a, **_k):
                raise RuntimeError("db down")

        with self.assertLogs("cloud360.brain_diagram_creation", level="ERROR") as logs:
            ok = B.record_creation(Boom(), mint_principal(self.alice), diagram_id=1, title="機密名稱")
        self.assertFalse(ok)
        self.assertNotIn("機密名稱", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
