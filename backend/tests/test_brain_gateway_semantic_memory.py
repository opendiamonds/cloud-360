"""從對話寫入語意記憶（build-and-test 第二輪，2026-11-12）。

**本階段新增、已核可 scope 尚未涵蓋的寫入路徑**：FR4.1 要三種記憶，而 OQ-N3 只落地了情節記憶的
寫入端，語意記憶至今沒有任何寫入者（本機驗證 F3：「請記住：我們團隊偏好…」被路由成三選一反問、
語意記憶始終 0 則）。2026-11-12 使用者選定本輪補上。回補項：requirements 補語意記憶寫入 FR、
user-stories 補 AC；在那之前本檔的規格註解暫掛 `@story US4.1`（FR4.1 的承載故事），回補後改指新 AC。
程序記憶本輪不做。

驗的是四件事：
1. 只有明確的「記住／記下」句首進入本路徑；其餘句子照舊走 `U11` 路由（不退化）。
2. **寫入前必經使用者確認**：確認反問沿用 `clarify`（kind=intent、唯一候選）；取消、被新訊息取代皆不寫。
3. 擁有者恆為已驗證身分、可見範圍恆為最窄（FR4.3a／FR4.3b），句子裡寫什麼都改變不了。
4. 疑似憑證／個資拒寫、長度上限、fulltext 明確回錯，且 log 不含使用者原文。

`U11`／`U12` 以替身取代；記憶層在 G 類以 `FakeMemory`、在 A／P2 類以**真的** `MemoryFacade`
（`EMBEDDING_PROVIDER=stub`、in-memory SQLite）驗。**不呼叫任何 LLM**。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import logging
import os
import re
import unittest
from unittest import mock

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from starlette.testclient import TestClient

from models import MemoryAuditEvent, MemoryRecord
from services import brain_gateway_rules as R
from services.embedding_port import EmbeddingProviderUnavailable
from services.memory_errors import MemoryForbidden, MemoryNotFound
from services.memory_facade import MemoryFacade, mint_principal
from services.memory_router import MEMORY_CONTENT_MAX_CHARS
from services.memory_types import VISIBILITY_SCOPE_OWNER
from tests.brain_gateway_fakes import (
    WS_PATH,
    Harness,
    hello,
    nothing_more,
    protocols,
    read_turn,
    types_of,
    user_message,
)

KEY = "brain:session:1"
PREFERENCE = "我們團隊偏好把服務部署在 ap-northeast-1"
SELECT_CONFIRM = {"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": R.MEMORY_CONFIRM_CANDIDATE_ID}}
SELECT_CANCEL = {"v": 1, "type": "select_clarify_candidate", "payload": {"candidateId": None}}


# ---------------------------------------------------------------------------
# 規則（純函式）
# ---------------------------------------------------------------------------


class RememberParseTest(unittest.TestCase):
    def test_explicit_remember_phrasings_extract_the_content(self):
        """
        @purpose 只有句首明確要求記住的說法進入語意記憶路徑，並取出要記住的那句（去前導標點與外層引號）。
        @given 中英文多種說法
        @step 呼叫 parse_remember_request | 回傳去掉動詞與標點後的內容
        @pass 每一種說法都取出同一句偏好
        @story US4.1
        """
        for utterance in (
            f"請記住：{PREFERENCE}",
            f"記住，{PREFERENCE}",
            f"幫我記住「{PREFERENCE}」",
            f"麻煩記一下 {PREFERENCE}",
            f"請幫我記下來：{PREFERENCE}",
            f"  記住:{PREFERENCE}  ",
            f"Remember: {PREFERENCE}",
            f"please remember that {PREFERENCE}",
        ):
            with self.subTest(utterance=utterance):
                self.assertEqual(R.parse_remember_request(utterance), PREFERENCE)
        self.assertEqual(R.parse_remember_request("請記住"), "")

    def test_ordinary_sentences_and_questions_are_not_remember_requests(self):
        """
        @purpose 既有能力的句子與「記住了嗎」這類問句不得被攔進記憶路徑（否則既有路由退化）。
        @given 架構設計／評核／成本句、問句、句中才出現「記住」者
        @step 呼叫 parse_remember_request | 一律回 None
        @pass 全部不攔截
        @story US4.1
        """
        for utterance in (
            "幫我畫一張電商網站的雲端架構圖",
            "幫我做 Well-Architected 評核，看這張架構圖",
            "這個系統每個月大概要花多少錢？",
            "你記住了嗎？",
            "記住過這件事嗎",
            "我記得上次說過要部署在東京",
            "要記住我們偏好 ap-northeast-1",
            "remember when we chose Tokyo?",
            "",
        ):
            with self.subTest(utterance=utterance):
                self.assertIsNone(R.parse_remember_request(utterance))

    @settings(max_examples=200, deadline=None)
    @given(st.text(alphabet="我們團隊偏好服務部署東京區域規格選型abcxyz -", min_size=1, max_size=60))
    def test_P0_prefixed_content_round_trips(self, content):
        """
        @purpose 性質：任何不以問句字開頭的內容，加上「請記住：」後取回的就是它（去頭尾空白）。
        @given Hypothesis 產生的內容（字母表排除引號與問句字）
        @step parse_remember_request(f"請記住：{content}") | 等於 content 去頭尾空白與前導標點
        @pass 200 個例子全部成立
        @story US4.1
        """
        expected = re.sub(r"^[\s\-]+", "", content).strip()
        self.assertEqual(R.parse_remember_request(f"請記住：{content}"), expected)


class ContentGuardTest(unittest.TestCase):
    def test_credentials_are_rejected(self):
        """
        @purpose 疑似密碼、金鑰、token 的內容不得寫入可被檢索的記憶。
        @given 賦值形式的密碼／金鑰、已知金鑰形狀、長亂碼、私鑰標頭
        @step 呼叫 memory_content_rejection | 回 credential
        @pass 全部被擋
        @story US4.1
        """
        aws_like = "AKIA" + "ABCDEFGHIJKLMNOP"
        for content in (
            "我們的測試帳號密碼是 hunter2",
            "staging 的 api key: abcd1234",
            "token=whatever",
            "部署用的 access key 是 " + aws_like,
            "sk-" + "a1b2c3d4e5f6g7h8i9j0",
            "連線用這串 " + "Zx9" * 12,
            "-----BEGIN " + "RSA PRIVATE KEY-----",
        ):
            with self.subTest(content=content):
                self.assertEqual(R.memory_content_rejection(content), R.MEMORY_REJECT_CREDENTIAL)

    def test_personal_data_is_rejected(self):
        """
        @purpose 疑似個資（電子郵件、身分證字號、手機、卡號）不寫入。
        @given 四種形狀各一
        @step 呼叫 memory_content_rejection | 回 personal
        @pass 全部被擋
        @story US4.1
        """
        for content in (
            "有事找 alice@example.com",
            "負責人身分證 A123456789",
            "值班手機 0912-345-678",
            "公司卡 4111 1111 1111 1111",
        ):
            with self.subTest(content=content):
                self.assertEqual(R.memory_content_rejection(content), R.MEMORY_REJECT_PERSONAL)

    def test_ordinary_preferences_pass_and_limits_hold(self):
        """
        @purpose 一般偏好（含只提到「密碼」一詞但沒有值者、ARN）可寫；空白與超長被擋；上限不超過記憶層 HTTP 上限。
        @given 偏好句、空白、超長句
        @step 呼叫 memory_content_rejection | 偏好回 None、空白回 empty、超長回 too_long
        @pass 三類判定正確，SEMANTIC_MEMORY_MAX_CHARS ≤ MEMORY_CONTENT_MAX_CHARS
        @story US4.1
        """
        for content in (
            PREFERENCE,
            "我們偏好用 Secrets Manager 管理密碼",
            "IAM role 一律用 arn:aws:iam::123456789012:role/deploy 這種命名",
            "資料庫一律 Multi-AZ，t3.medium 起跳",
        ):
            with self.subTest(content=content):
                self.assertIsNone(R.memory_content_rejection(content))
        self.assertEqual(R.memory_content_rejection("   "), R.MEMORY_REJECT_EMPTY)
        self.assertEqual(R.memory_content_rejection("偏" * (R.SEMANTIC_MEMORY_MAX_CHARS + 1)), R.MEMORY_REJECT_TOO_LONG)
        self.assertIsNone(R.memory_content_rejection("偏" * R.SEMANTIC_MEMORY_MAX_CHARS))
        self.assertLessEqual(R.SEMANTIC_MEMORY_MAX_CHARS, MEMORY_CONTENT_MAX_CHARS)


# ---------------------------------------------------------------------------
# 閘道（FakeMemory）
# ---------------------------------------------------------------------------


class _Base(unittest.TestCase):
    #: 性質測試在同一個 Harness 上跑數十個例子；頻率限制不是被測性質，故放寬（其餘測試用預設值）。
    relaxed_rate = False

    def setUp(self):
        rate = R.RateLimiter(per_key=10**6, per_conn=10**6, handshakes_per_key=10**6) if self.relaxed_rate else None
        self.h = Harness(rate=rate)
        self.alice = self.h.user("alice")
        self.token = self.h.token("alice")

    def tearDown(self):
        self.h.close()

    def connect(self, client):
        return client.websocket_connect(WS_PATH, subprotocols=protocols(self.token))

    def history(self, segment="shared"):
        session = self.h.store.load(KEY)
        if session is None or segment not in session.segments:
            return []
        return [(m.role, m.text) for m in session.segments[segment].messages]


class ConfirmFlowTest(_Base):
    def test_remember_asks_first_then_writes_semantic_on_confirm(self):
        """
        @purpose 「請記住：…」不經路由、先以一個候選的反問呈現擬寫入的那句話；按下確認才寫一則語意記憶，擁有者為已驗證身分。
        @given alice 已連線；記憶層為替身
        @step 送「請記住：<偏好>」 | 收到 clarify（kind=intent），唯一候選 id=memory-confirm、label 含完整偏好；路由 0 次、寫入 0 次
        @step 選 memory-confirm | 同一 turnId 收到 token（含偏好）與 done
        @step 檢視記憶層與歷程 | 寫入恰 1 次：kind=semantic、content=偏好、principal.user_id=alice；歷程含 user 與 assistant 各一
        @pass 確認前不寫、確認後恰寫一次
        @story US4.1
        """
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, f"請記住：{PREFERENCE}")
            clarify = read_turn(ws)[-1]
            self.assertEqual((clarify["type"], clarify["payload"]["kind"]), ("clarify", "intent"))
            candidates = clarify["payload"]["candidates"]
            self.assertEqual([c["id"] for c in candidates], [R.MEMORY_CONFIRM_CANDIDATE_ID])
            self.assertIn(PREFERENCE, candidates[0]["label"])
            self.assertEqual(self.h.router_script.calls, [])
            self.assertEqual(self.h.memory.write_calls, [])
            ws.send_json(SELECT_CONFIRM)
            rest = read_turn(ws)
            self.assertEqual(types_of(rest), ["token", "done"])
            self.assertEqual({m["turnId"] for m in rest}, {clarify["turnId"]})
            self.assertIn(PREFERENCE, rest[0]["payload"]["text"])
        self.assertEqual(len(self.h.memory.write_calls), 1)
        call = self.h.memory.write_calls[0]
        self.assertEqual((call.kind, call.content, call.principal.user_id), ("semantic", PREFERENCE, self.alice.id))
        self.assertEqual([role for role, _ in self.history()], ["user", "assistant"])
        self.assertEqual(self.h.orchestrator.dispatch_calls, [])

    def test_cancel_or_superseding_message_writes_nothing(self):
        """
        @purpose 取消（「都不是」）或在等待確認時送出新訊息，都不得寫入記憶。
        @given alice 已連線
        @step 送「記住：A」後選「都不是」 | 之後沒有任何訊息
        @step 送「記住：B」後不選、改送「記住：C」再取消 | 只看到兩次 clarify
        @pass 寫入 0 次
        @story US4.1
        """
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "記住：偏好甲")
            read_turn(ws)
            ws.send_json(SELECT_CANCEL)
            self.assertTrue(nothing_more(ws))
            user_message(ws, "記住：偏好乙")
            read_turn(ws)
            user_message(ws, "記住：偏好丙")
            self.assertEqual(read_turn(ws)[-1]["type"], "clarify")
            ws.send_json(SELECT_CANCEL)
            self.assertTrue(nothing_more(ws))
        self.assertEqual(self.h.memory.write_calls, [])

    def test_ordinary_sentence_still_routes_and_dispatches(self):
        """
        @purpose 既有能力路由不退化：一般句子照舊經 U11 分類並交辦，不出現記憶確認。
        @given 路由替身回架構設計判定
        @step 送「幫我畫一張電商網站的雲端架構圖」 | work_items、token、done；路由 1 次、交辦 1 次
        @pass 語意記憶寫入 0 次（交辦後既有的情節記憶寫入照舊）、無 clarify
        @story US4.1
        """
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, "幫我畫一張電商網站的雲端架構圖")
            self.assertEqual(types_of(read_turn(ws)), ["work_items", "token", "done"])
        self.assertEqual(len(self.h.router_script.calls), 1)
        self.assertEqual(len(self.h.orchestrator.dispatch_calls), 1)
        self.assertEqual([c.kind for c in self.h.memory.write_calls if c.kind != "episodic"], [])


class GuardAndFailureTest(_Base):
    def test_credential_is_refused_without_asking_and_log_has_no_content(self):
        """
        @purpose 疑似密碼的內容直接拒寫並告知理由；不送確認、不寫入，且 log 不含使用者原文。
        @given alice 已連線；捕捉 cloud360.brain_gateway 的 log
        @step 送「記住：測試帳號密碼是 hunter2zz」 | token 為固定拒寫說明、done
        @step 檢視 | 寫入 0 次；log 不含 hunter2zz
        @pass 拒寫且未外洩
        @story US4.1
        """
        secret = "hunter2zz"
        with self.assertLogs("cloud360.brain_gateway", level="DEBUG") as logs:
            with TestClient(self.h.app) as client, self.connect(client) as ws:
                hello(ws)
                user_message(ws, f"記住：測試帳號密碼是 {secret}")
                turn = read_turn(ws)
        self.assertEqual(types_of(turn), ["token", "done"])
        self.assertEqual(turn[0]["payload"]["text"], R.MEMORY_REJECT_REPLIES[R.MEMORY_REJECT_CREDENTIAL])
        self.assertEqual(self.h.memory.write_calls, [])
        self.assertNotIn(secret, "\n".join(logs.output))
        self.assertIn("memory_write_rejected", "\n".join(logs.output))

    def _confirm_and_read(self, utterance=f"記住：{PREFERENCE}"):
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            user_message(ws, utterance)
            read_turn(ws)
            ws.send_json(SELECT_CONFIRM)
            return read_turn(ws)

    def test_fulltext_says_not_remembered_instead_of_pretending(self):
        """
        @purpose EMBEDDING_PROVIDER=fulltext 之下寫入不可能成功：回明確錯誤，不得回「已記住」。
        @given 記憶層 write 拋 EmbeddingProviderUnavailable("fulltext")
        @step 送「記住：…」並確認 | error，code=INTERNAL_ERROR、message 為 memory_fulltext 固定句
        @pass 沒有 token、沒有 done
        @story US4.1
        """
        self.h.memory.write_behaviour = EmbeddingProviderUnavailable("fulltext")
        turn = self._confirm_and_read()
        self.assertEqual(types_of(turn), ["error"])
        self.assertEqual(turn[0]["payload"]["code"], "INTERNAL_ERROR")
        self.assertEqual(turn[0]["payload"]["message"], R.ERROR_MESSAGES["memory_fulltext"])

    def test_forbidden_and_unexpected_failures_are_reported(self):
        """
        @purpose 記憶層拒絕（未核准帳號）回 UNAUTHORIZED；其他失敗回固定的寫入失敗句，兩者都不宣稱已記住。
        @given write 依序拋 MemoryForbidden、RuntimeError
        @step 各確認一次 | 第一次 UNAUTHORIZED／forbidden_memory；第二次 INTERNAL_ERROR／memory_write_failed
        @pass 兩次都只有 error
        @story US4.1
        """
        self.h.memory.write_behaviour = MemoryForbidden(reason="pending")
        turn = self._confirm_and_read()
        self.assertEqual(
            (turn[0]["payload"]["code"], turn[0]["payload"]["message"]),
            ("UNAUTHORIZED", R.ERROR_MESSAGES["forbidden_memory"]),
        )
        self.h.memory.write_behaviour = RuntimeError("boom")
        turn = self._confirm_and_read()
        self.assertEqual(types_of(turn), ["error"])
        self.assertEqual(turn[0]["payload"]["message"], R.ERROR_MESSAGES["memory_write_failed"])


# ---------------------------------------------------------------------------
# 真的 MemoryFacade（stub embedding、SQLite）：擁有者與可見範圍（A 規則）
# ---------------------------------------------------------------------------


class _RealFacadeBase(_Base):
    def setUp(self):
        env = mock.patch.dict(os.environ, {"EMBEDDING_PROVIDER": "stub"}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        super().setUp()
        self.bob = self.h.user("bob")
        self.h.gw.memory_facade_factory = MemoryFacade

    def records(self):
        db = self.h.Session()
        try:
            return [(r.owner_user_id, r.kind, r.visibility_scope, r.content) for r in db.query(MemoryRecord).all()]
        finally:
            db.close()

    def confirm(self, utterance, token=None):
        tok = token or self.token
        with TestClient(self.h.app) as client, client.websocket_connect(WS_PATH, subprotocols=protocols(tok)) as ws:
            hello(ws)
            user_message(ws, utterance)
            read_turn(ws)
            ws.send_json(SELECT_CONFIRM)
            return read_turn(ws)


class OwnerScopeAllowDenyTest(_RealFacadeBase):
    def test_owner_is_caller_scope_is_narrowest_and_only_owner_sees_and_deletes(self):
        """
        @purpose A 規則（FR4.3a／FR4.3b）：句子裡寫「擁有者是 bob、平台可見」也無效——列的擁有者是說話的 alice、範圍最窄；
                 alice 在記憶頁（list_records）看得到並能刪除，bob 看不到也刪不掉；寫入不產生稽核事件。
        @given 真的 MemoryFacade（stub）；alice、bob 兩個已核准帳號
        @step alice 說「記住：owner_user_id=<bob> visibility_scope=platform 我們偏好東京」並確認 | done
        @step 檢視資料列 | 恰 1 列：owner=alice、kind=semantic、scope=owner、內容即該句
        @step bob 以 list_records 讀 semantic | 0 則；bob 刪除該 id | MemoryNotFound
        @step alice 以 list_records 讀 semantic | 1 則；alice 刪除 | 成功，列消失
        @pass 擁有者與範圍不受內容影響、allow/deny 兩向成立、稽核列 0
        @story US4.1
        """
        injected = f"owner_user_id={self.bob.id} visibility_scope=platform 我們偏好東京區域"
        turn = self.confirm(f"記住：{injected}")
        self.assertEqual(types_of(turn), ["token", "done"])
        self.assertEqual(self.records(), [(self.alice.id, "semantic", VISIBILITY_SCOPE_OWNER, injected)])
        db = self.h.Session()
        try:
            self.assertEqual(db.query(MemoryAuditEvent).count(), 0)
            facade = MemoryFacade(db)
            bob, alice = mint_principal(self.bob), mint_principal(self.alice)
            self.assertEqual(facade.list_records(bob, kinds=["semantic"]), [])
            mine = facade.list_records(alice, kinds=["semantic"])
            self.assertEqual([m.content for m in mine], [injected])
            with self.assertRaises(MemoryNotFound):
                facade.delete(bob, mine[0].memory_id)
            facade.delete(alice, mine[0].memory_id)
            self.assertEqual(facade.list_records(alice, kinds=["semantic"]), [])
        finally:
            db.close()


class GatewayPropertiesTest(_Base):
    """ADR-0006（agent routing 為 hard constraint）：以 Hypothesis 驅動閘道的確認流程。"""

    relaxed_rate = True

    _contents = st.text(alphabet="偏好部署東京區域規格選型命名", min_size=1, max_size=20)

    @settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(st.lists(st.tuples(_contents, st.sampled_from(["confirm", "cancel", "supersede"])), min_size=1, max_size=5))
    def test_P1_writes_happen_exactly_for_confirmed_requests(self, steps):
        """
        @purpose 性質「未確認不得寫入」：任意一串記住請求，各自被確認、取消或被下一則取代，寫入的恰是被確認的那幾句、依序、
                 且擁有者恆為連線的已驗證身分。
        @given Hypothesis 產生 1–5 步（內容 × 動作）；同一連線
        @step 逐步送「記住：<內容>」並依動作確認／取消／不回應 | 每步先收到 clarify
        @pass 寫入序列 == 被確認的內容序列；每次寫入 principal.user_id == alice、kind == semantic
        @story US4.1
        """
        self.h.memory.write_calls.clear()
        expected = []
        with TestClient(self.h.app) as client, self.connect(client) as ws:
            hello(ws)
            for content, action in steps:
                user_message(ws, f"記住：{content}")
                self.assertEqual(read_turn(ws)[-1]["type"], "clarify")
                if action == "confirm":
                    ws.send_json(SELECT_CONFIRM)
                    self.assertEqual(types_of(read_turn(ws)), ["token", "done"])
                    expected.append(content)
                elif action == "cancel":
                    ws.send_json(SELECT_CANCEL)
        self.assertEqual([c.content for c in self.h.memory.write_calls], expected)
        self.assertTrue(all(c.principal.user_id == self.alice.id and c.kind == "semantic" for c in self.h.memory.write_calls))


class RealFacadePropertiesTest(_RealFacadeBase):
    relaxed_rate = True

    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        speaker=st.sampled_from(["alice", "bob"]),
        claimed=st.sampled_from(["alice", "bob", "999"]),
        scope_word=st.sampled_from(["platform", "project", "public", "所有人可見"]),
        tail=st.text(alphabet="偏好部署東京區域規格", min_size=1, max_size=12),
    )
    def test_P2_owner_always_equals_authenticated_speaker(self, speaker, claimed, scope_word, tail):
        """
        @purpose 性質「擁有者恆等於已驗證身分」：句子宣稱任何擁有者與可見範圍，寫入列的擁有者都是說話的帳號、範圍都是 owner。
        @given Hypothesis 產生說話者、宣稱的擁有者、宣稱的範圍字樣與內容；真的 MemoryFacade（stub）
        @step 說話者送「記住：擁有者 <claimed> 範圍 <scope> <tail>」並確認 | done
        @pass 新增的那一列 owner_user_id == 說話者 id、visibility_scope == owner
        @story US4.1
        """
        users = {"alice": self.alice, "bob": self.bob}
        before = len(self.records())
        claimed_id = users[claimed].id if claimed in users else claimed
        turn = self.confirm(f"記住：owner_user_id={claimed_id} visibility_scope={scope_word} {tail}", token=self.h.token(speaker))
        self.assertEqual(types_of(turn), ["token", "done"])
        rows = self.records()
        self.assertEqual(len(rows), before + 1)
        owner, kind, scope, _ = rows[-1]
        self.assertEqual((owner, kind, scope), (users[speaker].id, "semantic", VISIBILITY_SCOPE_OWNER))


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
