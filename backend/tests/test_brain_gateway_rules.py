"""`U13 brain-gateway` 的純函式與純狀態機測試（`backend/services/brain_gateway_rules.py`）。

五個 property-based 性質（`functional-spec.md` §七；`NFR13.42`）：一 `parse_subprotocol_offer`、二
`session_key_for`、三 `TurnLedger`、四 `resolve_segment`、五 `scan_targets_in_utterance`（以 `NFR13.28`／
`reliability-design.md` §7.4 改寫後、可失敗的 (a)(b)(c) 版本）；另有 `BreakerState` 與 `RateLimiter` 的狀態性質。
`error_for` 與 `match_referent` 以 example-based 覆蓋。

突變驗證時設 `HYPOTHESIS_NO_SHRINK=1`（本檔讀它以關閉 shrinking）。`@api`／`@ui` 刻意缺席：受測對象是純函式。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import json
import os
import string
import unittest

import httpx
from hypothesis import Phase, given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from services import brain_gateway_rules as R
from services.embedding_port import EmbeddingProviderUnavailable
from services.hierarchy_facade import HierarchyForbidden, HierarchyNotFound
from services.intent_routing_errors import EmptyCandidates, LlmBudgetExceeded, LlmUnavailable, MalformedRouting
from services.memory_errors import MemoryForbidden
from services.session_errors import SessionBackendUnavailable, SessionMessageTooLong
from services.work_orchestrator import WorkItemNotFound

_PHASES = tuple(p for p in Phase if not (os.environ.get("HYPOTHESIS_NO_SHRINK") and p is Phase.shrink))
PBT = settings(max_examples=200, deadline=None, phases=_PHASES)

# RFC 7230 tchar（去掉逗號；JWT 的 base64url 三段即屬此集）
_TCHAR = string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~"
_tokens = st.text(alphabet=_TCHAR, min_size=1, max_size=40)
_ws = st.text(alphabet=" \t", max_size=3)


class SubprotocolOfferTest(unittest.TestCase):
    """`BR61.2` — 性質一與三個 example。"""

    @PBT
    @given(token=_tokens, include_name=st.booleans(), others=st.lists(_tokens.filter(lambda t: not t.startswith("bearer.") and t != "cloud360.brain.v1"), max_size=3), order=st.randoms(), pad=_ws)
    def test_property_one_token_and_protocol_name_survive_any_order_and_spacing(self, token, include_name, others, order, pad):
        """
        @purpose 不論項目順序與項目間空白，解析都要取回同一個 token、正確判定是否提供協定名；
                 取錯段（例如 split('.') 取兩段）會讓每一個真實 JWT 的握手都 4401。
        @given t 取自非空、不含逗號、無前後空白的 tchar 字元集
        @step 以 [協定名?] ＋ bearer.t ＋ 其他項目的任意排列組出標頭，項目間插入任意空白 | 解析
        @pass bearerToken == t；hasProtocolName 等於是否放入協定名
        @story US8.1
        """
        items = ([R.PROTOCOL_NAME] if include_name else []) + [R.BEARER_PREFIX + token] + others
        order.shuffle(items)
        header = ",".join(pad + item + pad for item in items)
        offer = R.parse_subprotocol_offer(header)
        self.assertEqual(offer.bearer_token, token)
        self.assertEqual(offer.has_protocol_name, include_name)

    def test_examples_empty_bearer_blank_and_jwt_dots(self):
        """
        @purpose 空的 bearer、只有空白、整個標頭為空時 token 不存在；JWT 的兩個點不得切壞 token。
        @given 四種標頭
        @step 解析 "cloud360.brain.v1, bearer." | token 不存在、有協定名
        @step 解析 "   " 與 "" 與 None | token 不存在、無協定名
        @step 解析含 a.b.c 形狀的 JWT | token 原樣為 a.b.c
        @pass 四案皆如預期，且 token 不出現在 repr
        @story US8.1
        """
        self.assertIsNone(R.parse_subprotocol_offer("cloud360.brain.v1, bearer.").bearer_token)
        self.assertTrue(R.parse_subprotocol_offer("cloud360.brain.v1, bearer.").has_protocol_name)
        for header in ("   ", "", None):
            offer = R.parse_subprotocol_offer(header)
            self.assertIsNone(offer.bearer_token)
            self.assertFalse(offer.has_protocol_name)
        offer = R.parse_subprotocol_offer("bearer.aaa.bbb.ccc, cloud360.brain.v1")
        self.assertEqual(offer.bearer_token, "aaa.bbb.ccc")
        self.assertNotIn("aaa.bbb.ccc", repr(offer))


class SessionKeyTest(unittest.TestCase):
    """`BR62.3` — 性質二。"""

    @PBT
    @given(u=st.integers(min_value=1, max_value=10**12), v=st.integers(min_value=1, max_value=10**12))
    def test_property_two_round_trip_and_injective(self, u, v):
        """
        @purpose session key 必須可反推且單射；兩個使用者推導出同一鍵會互相看到對方的作業對象與歷程。
        @given 任意兩個正整數 u、v
        @step 推導再反推 | 得回 u
        @step 比較兩個鍵 | u != v ⇒ 鍵不同
        @pass 往返相等且不撞鍵
        @story US2.1
        """
        self.assertEqual(R.user_id_from_session_key(R.session_key_for(u)), u)
        if u != v:
            self.assertNotEqual(R.session_key_for(u), R.session_key_for(v))

    def test_invalid_inputs_raise(self):
        """
        @purpose 非正整數與格式不符的鍵不得被接受。
        @given 0、負數、bool、字串、錯形狀的鍵
        @step 逐一呼叫 | 皆拋 ValueError
        @pass 全部被拒
        @story US2.1
        """
        for bad in (0, -1, True, "1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                R.session_key_for(bad)
        for bad in ("brain:session:0", "brain:session:-1", "x:1", "brain:session:01", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                R.user_id_from_session_key(bad)


class ResolveSegmentTest(unittest.TestCase):
    """`BR62.5` — 性質四。"""

    @PBT
    @given(page=st.sampled_from(["entry", "workspace", "assessment"]), ws=st.sampled_from(["shared", "isolated"]), asm=st.sampled_from(["shared", "isolated"]))
    def test_property_four_entry_is_shared_and_result_is_shared_or_page(self, page, ws, asm):
        """
        @purpose 入口頁恆寫共享段；工作頁只會寫共享段或自己的段——寫錯段會讓獨立對話混進共享歷程。
        @given 任意頁面與兩頁的共享模式
        @step 解析段 | entry ⇒ shared；其餘 ∈ {shared, page}，且 isolated ⇔ 回 page
        @pass 對全部組合成立
        @story US3.1
        """
        modes = {"workspace": ws, "assessment": asm}
        seg = R.resolve_segment(page, modes)
        if page == "entry":
            self.assertEqual(seg, "shared")
        else:
            self.assertIn(seg, {"shared", page})
            self.assertEqual(seg == page, modes[page] == "isolated")

    def test_unknown_page_raises(self):
        """
        @purpose 契約三值以外的頁面不得被靜默當成入口頁。
        @given page="admin"
        @step 解析 | 拋 ValueError
        @pass 被拒
        @story US3.1
        """
        with self.assertRaises(ValueError):
            R.resolve_segment("admin", {})


_LEDGER_OPS = st.lists(st.sampled_from(["token", "cost_card", "clarify", "reopen", "finish", "fail", "end_silent"]), max_size=20)


class TurnLedgerTest(unittest.TestCase):
    """`BR64.7` — 性質三（`functional-spec.md` §4.2 的四條不變量）。"""

    @PBT
    @given(ops=_LEDGER_OPS)
    def test_property_three_at_most_one_terminal_and_done_iff_content(self, ops):
        """
        @purpose 任意操作序列下，每輪至多一個終止事件、終態後不放行任何訊息、done 若且唯若之前有內容、
                 clarify 不算內容——違反任一條，前端的狀態機就無法判定一輪是否結束。
        @given 任意長度 ≤ 20 的操作序列
        @step 依序套用並記錄 finish／fail 回傳的終止事件 | 終止事件 ≤ 1
        @step 每步後若已終態 | allows(*) 全為假
        @step finish 回 done 時 | 之前至少一次成功的 content
        @pass 四條不變量對全部序列成立
        @story US8.1
        """
        ledger = R.TurnLedger()
        terminals = 0
        content_seen = False
        for op in ops:
            if op in ("token", "cost_card"):
                if ledger.content(op):
                    content_seen = True
            elif op == "clarify":
                ledger.clarify()
            elif op == "reopen":
                ledger.reopen()
            elif op == "finish":
                result = ledger.finish()
                if result is not None:
                    terminals += 1
                    self.assertEqual(result == R.FINISH_DONE, content_seen)
            elif op == "fail":
                if ledger.fail():
                    terminals += 1
            elif op == "end_silent":
                ledger.end_silent()
            self.assertLessEqual(terminals, 1)
            if ledger.is_terminal:
                for kind in ("token", "cost_card", "clarify", "done", "error"):
                    self.assertFalse(ledger.allows(kind))

    def test_clarify_alone_ends_as_empty_response(self):
        """
        @purpose 只送過 clarify、選定後沒有任何內容的一輪，結束時必須是 EMPTY_RESPONSE 而非 done。
        @given 新的一輪
        @step clarify → reopen → finish | 回 EMPTY_RESPONSE
        @pass 不是 done
        @story US1.2
        """
        ledger = R.TurnLedger()
        self.assertTrue(ledger.clarify())
        self.assertTrue(ledger.reopen())
        self.assertEqual(ledger.finish(), R.FINISH_EMPTY)


class ErrorForTest(unittest.TestCase):
    """`BR67.1` — 封閉表（example-based）。"""

    def test_every_listed_exception_maps_to_closed_code_without_leaking(self):
        """
        @purpose 每一類例外對應到封閉表內的 code，且 message 永不含例外原文——原文可能帶 SQL、路徑或使用者輸入。
        @given 每類例外各一個，訊息內帶標記字串
        @step 呼叫 error_for | code 符合表、message ∈ ERROR_MESSAGES 的值、不含標記
        @pass 全部成立
        @story US8.1
        """
        marker = "LEAK-MARKER-42"

        class _Model(BaseModel):
            x: int

        try:
            _Model(x=marker)
        except ValidationError as exc:
            validation_error = exc
        cases = [
            (LlmUnavailable(marker), "INTERNAL_ERROR"),
            (LlmBudgetExceeded(marker), "INTERNAL_ERROR"),
            (EmptyCandidates(marker), "INTERNAL_ERROR"),
            (MalformedRouting(marker), "INTERNAL_ERROR"),
            (SessionBackendUnavailable("redis_unreachable", method=marker), "INTERNAL_ERROR"),
            (SessionMessageTooLong(limit=1, actual=2), "INVALID_REQUEST"),
            (HierarchyForbidden(story_id=marker, action="view"), "UNAUTHORIZED"),
            (MemoryForbidden(reason=marker), "UNAUTHORIZED"),  # 合併前必修第 13 項
            (HierarchyNotFound(marker), "INVALID_REQUEST"),
            (WorkItemNotFound(marker), "INVALID_REQUEST"),
            (validation_error, "INVALID_REQUEST"),
            (json.JSONDecodeError(marker, "doc", 0), "INVALID_REQUEST"),
            (R.RateLimited(marker), "INVALID_REQUEST"),
            (R.FrameTooLarge(marker), "INVALID_REQUEST"),
            (ValueError(marker), "INTERNAL_ERROR"),
            (RuntimeError(marker), "INTERNAL_ERROR"),
        ]
        for exc, code in cases:
            with self.subTest(exc=type(exc).__name__):
                got_code, message = R.error_for(exc)
                self.assertEqual(got_code, code)
                self.assertIn(message, set(R.ERROR_MESSAGES.values()))
                self.assertNotIn(marker, message)
        self.assertEqual(R.error_for(R.RateLimited())[1], "訊息太頻繁，請稍候再送出")


def _catalog(projects, systems=()):
    return R.TargetCatalog(projects=tuple(projects), systems=tuple(systems))


class MatchReferentTest(unittest.TestCase):
    """`BR64.9`／`BR64.11` — example-based。"""

    def test_unique_many_none_and_normalisation(self):
        """
        @purpose 高信心路徑只在唯一相符時更新作業對象；多筆反問、零筆請使用者指定。名稱比對去頭尾空白並 casefold，
                 但不動內部空白。
        @given 兩個專案，各含系統；其中兩個系統同名分屬不同專案
        @step 比對唯一的系統名 | unique
        @step 比對分屬兩個專案的同名系統 | many
        @step 比對不存在的名稱 | none
        @step 比對「 Orders 」與「orders」 | 結果相同；「訂 單」與「訂單」不同
        @pass 四案皆如預期
        @story US1.1
        """
        cat = _catalog([(1, "電商"), (2, "金流")], [(1, 10, "Orders"), (1, 11, "訂單"), (2, 20, "訂單")])
        self.assertEqual(R.match_referent("Orders", cat, None).kind, R.MATCH_UNIQUE)
        self.assertEqual(R.match_referent("訂單", cat, None).kind, R.MATCH_MANY)
        self.assertEqual(R.match_referent("不存在", cat, None).kind, R.MATCH_NONE)
        self.assertEqual(R.match_referent(" orders ", cat, None), R.match_referent("Orders", cat, None))
        self.assertEqual(R.match_referent("訂 單", cat, None).kind, R.MATCH_NONE)

    def test_selected_project_wins_and_unselected_unique_system_resolves(self):
        """
        @purpose 已選專案時先比對它的系統；脈絡列未選定、系統名在目錄中唯一時也必須解析得到（AC1.1.5 主情境）。
        @given 兩個專案各有一個「訂單」系統，另有唯一的「支付」系統
        @step 已選專案 2 時比對「訂單」 | unique，對象為專案 2 的系統
        @step 未選定時比對「支付」 | unique
        @pass 兩案皆 unique 且對象正確
        @story US1.1
        """
        cat = _catalog([(1, "電商"), (2, "金流")], [(1, 11, "訂單"), (2, 20, "訂單"), (2, 21, "支付")])
        picked = R.match_referent("訂單", cat, 2)
        self.assertEqual(picked.kind, R.MATCH_UNIQUE)
        self.assertEqual(picked.targets[0].key, (2, 20))
        self.assertEqual(R.match_referent("支付", cat, None).targets[0].key, (2, 21))

    def test_project_and_its_own_same_named_system_are_one_target(self):
        """
        @purpose 專案與它自己的系統同名時視為一個對象（該系統），BR64.9 不得把它算成兩筆而誤送反問（帶入項 2）。
        @given 專案「訂單」含系統「訂單」
        @step 比對「訂單」 | unique，對象帶 system_id
        @pass 唯一且為系統
        @story US1.1
        """
        cat = _catalog([(1, "訂單")], [(1, 10, "訂單")])
        result = R.match_referent("訂單", cat, None)
        self.assertEqual(result.kind, R.MATCH_UNIQUE)
        self.assertEqual(result.targets[0].key, (1, 10))


_NAME = st.text(alphabet="訂單ab", min_size=1, max_size=4)


@st.composite
def _catalogs(draw):
    n_projects = draw(st.integers(min_value=1, max_value=3))
    projects = [(pid, draw(_NAME)) for pid in range(1, n_projects + 1)]
    systems = []
    sid = 100
    for pid, _ in projects:
        for _ in range(draw(st.integers(min_value=0, max_value=3))):
            sid += 1
            systems.append((pid, sid, draw(_NAME)))
    return _catalog(projects, systems)


def _spans(u, name):
    out, start = [], 0
    while True:
        i = u.find(name, start)
        if i < 0:
            return out
        out.append((i, i + len(name)))
        start = i + 1


class ScanTargetsTest(unittest.TestCase):
    """`BR64.13`（帶入項 1、2、11 改寫）— 性質五 (a)(b)(c) 與 example。"""

    @PBT
    @given(catalog=_catalogs(), utterance=st.text(alphabet="訂單ab改系統的圖", max_size=12))
    def test_property_five_longest_complete_name(self, catalog, utterance):
        """
        @purpose 原句掃描只認最長完整名稱：被較長名稱完全覆蓋的較短名稱不得命中，否則「改訂單系統」會把專案「訂單」
                 也當成點名對象；同名的不同對象不互相覆蓋；系統命中吸收其所屬專案。
        @given 名稱字母表刻意小（製造包含關係）的任意目錄與原句
        @step (a) 結果中每個名稱是原句（casefold）的子字串 | 成立
        @step (b) 有未被支配區間、且不是已命中系統之所屬專案的條目必在結果內 | 成立
        @step (c) 結果中每個對象都有一個不被「名稱不同且較長」的區間完全覆蓋的出現區間 | 成立
        @pass 三條性質對全部輸入成立
        @story US1.2
        """
        u = utterance.casefold()
        result = R.scan_targets_in_utterance(utterance, catalog)
        entries = catalog.entries()
        all_spans = [(R.norm(e.name), s, t) for e in entries if len(R.norm(e.name)) >= 2 for (s, t) in _spans(u, R.norm(e.name))]

        def undominated(name):
            return [
                (s, t) for (s, t) in _spans(u, name)
                if not any(on != name and (oe - os_) > (t - s) and os_ <= s and t <= oe for (on, os_, oe) in all_spans)
            ]

        keys = {r.key for r in result}
        hit_system_projects = {r.project_id for r in result if r.system_id is not None}
        for r in result:  # (a)
            self.assertIn(R.norm(r.name), u)
        for e in entries:  # (b)
            name = R.norm(e.name)
            if len(name) < 2 or not undominated(name):
                continue
            if e.system_id is None and e.project_id in hit_system_projects:
                continue
            self.assertIn(e.key, keys)
        for r in result:  # (c)
            self.assertTrue(undominated(R.norm(r.name)))

    def test_examples_longest_name_absorption_and_same_name_in_two_projects(self):
        """
        @purpose 三個關鍵形狀的 example：較長名稱勝出、同名專案與系統收斂為系統、不同專案的同名系統兩者皆在。
        @given 三組目錄
        @step 專案「訂單」含「訂單系統」，原句「改訂單系統的圖」 | 只有「訂單系統」
        @step 專案「訂單」含系統「訂單」，原句「改訂單」 | 恰一個對象（該系統）
        @step 兩專案各有系統「訂單」，原句「改訂單」 | 兩個對象
        @pass 三案皆如預期
        @story US1.2
        """
        cat = _catalog([(1, "訂單")], [(1, 10, "訂單系統")])
        self.assertEqual([t.name for t in R.scan_targets_in_utterance("改訂單系統的圖", cat)], ["訂單系統"])
        cat = _catalog([(1, "訂單")], [(1, 10, "訂單")])
        self.assertEqual([t.key for t in R.scan_targets_in_utterance("改訂單", cat)], [(1, 10)])
        cat = _catalog([(1, "電商"), (2, "金流")], [(1, 10, "訂單"), (2, 20, "訂單")])
        self.assertEqual({t.key for t in R.scan_targets_in_utterance("改訂單", cat)}, {(1, 10), (2, 20)})

    def test_worst_case_input_is_bounded(self):
        """
        @purpose 掃描在事件迴圈上執行：最壞輸入（4000 字重複字元＋互為前綴的名稱「aa」「aaa」，約 8000 個重疊區間）
                 必須在有界時間內完成——兩兩比較約 6×10^7 次，會讓整個行程停擺數秒（審查 R-01）。
        @given 目錄含系統「aa」「aaa」與專案「aaaa」；原句為 4000 個 a
        @step 計時呼叫一次 | 1 秒內完成
        @step 檢視結果 | 只有最長的「aaaa」（專案）命中——它覆蓋了其餘兩者的每一個區間
        @pass 有界且結果正確
        @story US1.2
        """
        import time

        cat = _catalog([(1, "aaaa"), (2, "電商")], [(2, 20, "aa"), (2, 21, "aaa")])
        started = time.perf_counter()
        result = R.scan_targets_in_utterance("a" * 4000, cat)
        self.assertLess(time.perf_counter() - started, 1.0)
        self.assertEqual([t.key for t in result], [(1, None)])

    def test_only_the_first_scan_max_chars_are_scanned(self):
        """
        @purpose 句長上界沿用既有的單則訊息上限（4000 字）：超出部分不掃描，使最壞成本有固定上界。
        @given 目錄含系統「訂單」；原句為 4000 個 x 之後才出現「訂單」
        @step 掃描 | 無命中
        @step 原句改為 3998 個 x＋「訂單」 | 命中
        @pass 上界生效
        @story US1.2
        """
        cat = _catalog([(1, "電商")], [(1, 10, "訂單")])
        self.assertEqual(R.SCAN_MAX_CHARS, 4000)
        self.assertEqual(R.scan_targets_in_utterance("x" * 4000 + "訂單", cat), [])
        self.assertEqual([t.key for t in R.scan_targets_in_utterance("x" * 3998 + "訂單", cat)], [(1, 10)])


class TransientFailureTest(unittest.TestCase):
    """`NFR13.25` — 熔斷只認逾時與連線類（含被包住的 httpx 例外）。"""

    def test_wrapped_httpx_errors_open_but_config_errors_do_not(self):
        """
        @purpose 熔斷必須認得 EmbeddingProviderUnavailable 包住的 httpx 逾時／連線錯誤，但不得被 fulltext 的設定錯誤等
                 立即失敗打開——否則本機預設 fulltext 時熔斷永遠開著。
        @given 以 raise … from 構造的五種例外
        @step from httpx.ReadTimeout、from httpx.ConnectError、TimeoutError | 皆為暫時性
        @step from None 的設定錯誤、ValueError | 皆非暫時性
        @pass 判定全部正確
        @story US4.1
        """
        def wrapped(cause):
            try:
                try:
                    raise cause
                except Exception as inner:
                    raise EmbeddingProviderUnavailable("ollama", detail="x") from inner
            except EmbeddingProviderUnavailable as exc:
                return exc

        self.assertTrue(R.is_transient_memory_failure(wrapped(httpx.ReadTimeout("slow"))))
        self.assertTrue(R.is_transient_memory_failure(wrapped(httpx.ConnectError("down"))))
        self.assertTrue(R.is_transient_memory_failure(TimeoutError()))
        self.assertFalse(R.is_transient_memory_failure(EmbeddingProviderUnavailable("fulltext", detail="x")))
        self.assertFalse(R.is_transient_memory_failure(ValueError("x")))


_BREAKER_OPS = st.lists(
    st.tuples(st.sampled_from(["admit", "success", "transient", "permanent", "release", "tick"]), st.integers(min_value=0, max_value=40)),
    max_size=30,
)


class BreakerStateTest(unittest.TestCase):
    """`BR67.12` — 熔斷狀態機（含帶入項 18 的活性不變量）。"""

    @PBT
    @given(ops=_BREAKER_OPS)
    def test_breaker_invariants_including_liveness(self, ops):
        """
        @purpose 熔斷不得卡死：半開探測者在任何未執行出口都必須被清除，否則熔斷永久開啟、全體記憶停擺且無任何告警。
        @given 任意的 admit／成功／失敗／釋放探測者／推進時間 序列；以 in_flight 模擬「目前是否有探測在途」
        @step 每步後檢查 | skip 只在 open_until 非 None；非暫時性失敗不使關閉轉開啟
        @step 探測者以 success／failure／release 任一出口結束後 | probing 為假（無在途探測時 probing 必為假）
        @pass 不變量對全部序列成立
        @story US4.1
        """
        b = R.BreakerState(open_sec=30)
        now = 0.0
        probe_in_flight = False
        for op, n in ops:
            if op == "tick":
                now += n
                continue
            if op == "admit":
                was_open = b.open_until is not None
                got = b.admit(now)
                if got == R.ADMIT_SKIP:
                    self.assertTrue(was_open)
                if got == R.ADMIT_PROBE:
                    self.assertFalse(probe_in_flight)
                    probe_in_flight = True
            elif op == "success":
                b.on_success()
                probe_in_flight = False
            elif op == "transient":
                b.on_failure(TimeoutError(), now)
                probe_in_flight = False
            elif op == "permanent":
                was_closed = b.open_until is None
                b.on_failure(ValueError(), now)
                if was_closed:
                    self.assertIsNone(b.open_until)
                probe_in_flight = False
            elif op == "release":
                b.release_probe()
                probe_in_flight = False
            if not probe_in_flight:
                self.assertFalse(b.probing)


class RateLimiterTest(unittest.TestCase):
    """`NFR13.20` — 滑動窗性質與握手頻率。"""

    @PBT
    @given(events=st.lists(st.tuples(st.floats(min_value=0, max_value=5, allow_nan=False), st.booleans()), max_size=200))
    def test_window_never_admits_more_than_limits(self, events):
        """
        @purpose 任一 60 秒窗內放行的 user_message ≤ 20、全部訊框 ≤ 120；超過即拒，計費下游才有上界。
        @given 任意間隔（0–5 秒）的訊框序列，標記是否為 user_message
        @step 依序 admit 並記錄放行時刻 | 任一長度 60 秒的窗內放行計數不超過上限
        @pass 兩個上限皆成立
        @story US8.1
        """
        rl = R.RateLimiter()
        now = 0.0
        admitted_user, admitted_all = [], []
        for gap, is_user in events:
            now += gap
            if rl.admit("k", "c", is_user, now) is None:
                admitted_all.append(now)
                if is_user:
                    admitted_user.append(now)
        for t in admitted_all:
            self.assertLessEqual(sum(1 for x in admitted_all if t - 60 < x <= t), 120)
        for t in admitted_user:
            self.assertLessEqual(sum(1 for x in admitted_user if t - 60 < x <= t), 20)

    def test_handshakes_and_rejections_are_counted_per_window(self):
        """
        @purpose 握手也納入限流（帶入項 20）；被拒訊框計入關閉門檻（帶入項 29）。
        @given 預設上限
        @step 同一 key 在 60 秒內握手 31 次 | 第 31 次被拒；推進 60 秒後放行
        @step 同一連線記 20 次被拒 | 第 20 次回傳 20（達門檻）
        @pass 兩種計數皆依窗運作
        @story US8.1
        """
        rl = R.RateLimiter()
        results = [rl.admit_handshake("k", 0.0) for _ in range(31)]
        self.assertEqual(results.count(True), 30)
        self.assertFalse(results[-1])
        self.assertTrue(rl.admit_handshake("k", 61.0))
        counts = [rl.note_rejected("c", float(i)) for i in range(20)]
        self.assertEqual(counts[-1], R.REJECTED_FRAMES_CLOSE_THRESHOLD)


class HelloVersionTest(unittest.TestCase):
    """`BR61.8` — received 只會是整數或 invalid。"""

    def test_received_is_integer_or_invalid(self):
        """
        @purpose 4400 的關閉原因只回放整數版本或字面 invalid，不回放客戶端任意字串。
        @given 五種首則訊息
        @step hello v=1 | 相容
        @step hello v=2、hello v="1x"、非 hello、非物件 | 不相容，received 依序為 2、invalid、1、invalid
        @pass 判定與 received 正確，關閉原因 ASCII 且 ≤ 123 位元組
        @story US8.1
        """
        self.assertEqual(R.hello_version({"type": "hello", "v": 1}), (True, "1"))
        self.assertEqual(R.hello_version({"type": "hello", "v": 2}), (False, "2"))
        self.assertEqual(R.hello_version({"type": "hello", "v": "1x"}), (False, "invalid"))
        self.assertEqual(R.hello_version({"type": "user_message", "v": 1}), (False, "1"))
        self.assertEqual(R.hello_version(["x"]), (False, "invalid"))
        reason = R.close_reason_for_version("invalid")
        self.assertTrue(reason.isascii())
        self.assertLessEqual(len(reason.encode()), 123)


class WorkCapacityErrorTest(unittest.TestCase):
    """合併前必修第 18 項（`U12` 進行中上限）的跨單元對應：沿用既有代碼，不改 WS 契約。"""

    def test_work_capacity_exceeded_maps_to_invalid_request_with_fixed_message(self):
        """
        @purpose 進行中工作已達上限時，本輪以 INVALID_REQUEST 加固定句結束，而不是落到 INTERNAL_ERROR 的「處理時發生錯誤」
        @given `WorkCapacityExceeded(active=4, requested=2)`
        @step 呼叫 error_for | code＝INVALID_REQUEST、message 為固定句
        @step 比對固定句與 U12 的上限常數 | 句中數字等於 MAX_ACTIVE_WORK_ITEMS
        @pass code 與訊息逐字相符，且訊息不含例外原文
        @story US1.1
        """
        from services import work_orchestrator_rules as WR
        from services.brain_ws_contract import ErrorPayload
        from services.work_orchestrator import WorkCapacityExceeded

        exc = WorkCapacityExceeded(4, 2)
        code, message = R.error_for(exc)
        self.assertEqual(code, "INVALID_REQUEST")
        self.assertEqual(
            message, "同時進行中的工作最多 5 項，這次交辦會超過上限，請等其中一項完成後再交辦。"
        )
        self.assertIn(f"最多 {WR.MAX_ACTIVE_WORK_ITEMS} 項", message)
        # 4 筆進行中 ＋ 交辦 2 筆即觸發：句子不得宣稱「已達」上限（審查 R-03）。
        self.assertNotIn("已達", message)
        self.assertNotIn(str(exc), message)
        # 代碼在既有的封閉列舉內：WS 契約的 ErrorPayload 收得下它。
        ErrorPayload(code=code, message=message, turnId="t")


if __name__ == "__main__":
    unittest.main()
