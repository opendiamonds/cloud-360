"""`U12 work-orchestrator`：工作項位元組上界與容量承諾（code-generation 審查 review-01 R-01）。

上一版的容量表以「每字 3 B（中文）」算最壞值，但序列化後每字最多 6 B（控制字元經
cjson 跳脫成 `\\u00XX`），而使用者原句沒有任何控制字元過濾——那不是上界。本檔以
**對抗字元**（6 B 的控制字元、4 B 的 emoji、2 B 的 `/`）把每個可變長欄位填到程式允許
的最長，**經生產程式的建項與轉終態路徑**建出最壞的進行中項與已結束項，斷言：

1. 兩者序列化後（含欄位名 `wi:<uuid>`）不超過 `WORK_ITEM_ACTIVE_MAX_BYTES`／
   `WORK_ITEM_TERMINAL_MAX_BYTES`；
2. `614,400 ＋ 5 × 進行中上界 ＋ 20 × 已結束上界 ≤ maxmemory 的 80% ÷ 300`。

量測函式是 `session_types.cjson_encoded_size`（與 Lua 端 `cjson.encode` 同長度）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import string
import unittest
from types import SimpleNamespace

from hypothesis import given, settings
from hypothesis import strategies as st

from services import session_types as T
from services import work_orchestrator_rules as R
from services.work_orchestrator import CHANGE_SUMMARY_MAX_CHARS, REQUEST_TEXT_MAX_CHARS
from tests.test_work_orchestrator_flow import ARCH, COST, REVIEW, Harness
from tests.work_orchestrator_fakes import SESSION_KEY

#: PostgreSQL integer 的上限：識別碼欄位的最長十進位表示。
INT_MAX = 2**31 - 1
#: 最長的 session key（`brain_gateway_rules.session_key_for`）。
WORST_SESSION_KEY = "brain:session:" + str(INT_MAX)
#: 對抗字元：每個都是序列化後最貴的一類。
CONTROL = "\x01"  # cjson 跳脫為 \u0001：6 B
DEL = "\x7f"  # cjson 跳脫為 \u007f：6 B（Python json 不跳脫，cjson_encoded_size 已補）
EMOJI = "\U0001F600"  # UTF-8 4 B
SLASH = "/"  # cjson 跳脫為 \/：2 B

#: `_build_items` 建出的欄位全集。新增欄位而沒有把它算進最壞值，本檔即紅燈。
EXPECTED_FIELDS = {
    "workItemId", "sessionKey", "label", "status", "capability", "waitingOn",
    "failureReason", "sideEffect", "createdAt", "estimateSetId", "dependsOn",
    "targetDiagramId", "targetSystemId", "targetDiagramTitle", "targetDisplay",
    "segmentId", "deadlineAt", "dispatchStage", "requestText", "dispatchIndex",
}


def adversarial(n_chars: int) -> str:
    """6 B 控制字元與 4 B emoji 交錯，再補一些 6 B 的 DEL 與 2 B 的 `/`。"""
    pattern = CONTROL + EMOJI + DEL + SLASH
    return (pattern * (n_chars // len(pattern) + 1))[:n_chars]


def stored_size(item: dict) -> int:
    """一筆工作項在 Redis hash 的位元組：欄位名 ＋ cjson 值。"""
    return R.WORK_ITEM_FIELD_NAME_BYTES + T.cjson_encoded_size(item)


def worst_label() -> str:
    longest_name = max(R.CAPABILITY_NAMES.values(), key=lambda s: T.cjson_encoded_size(s))
    target = R.target_display(INT_MAX, None, None)
    for candidate in (R.target_display(None, INT_MAX, None), R.target_display(None, None, INT_MAX)):
        if T.cjson_encoded_size(candidate) > T.cjson_encoded_size(target):
            target = candidate
    return f"{longest_name}：{target}"


def worst_phrase(title: str) -> str:
    """`PHRASES` 每一個句型以最長的代入值格式化後最長者（failureReason／sideEffect 的上界）。

    `failed` 與 `side_effect_change_record_missing` 會再包一層其他句型：先算單層的
    最長者，再代入第二層——比實際可能的值更長，故是保守上界。
    """
    label = worst_label()
    longest_name = max(R.CAPABILITY_NAMES.values(), key=lambda s: T.cjson_encoded_size(s))
    values = {
        "label": label,
        "dependency_label": label,
        "waiting_label": label,
        "capability": longest_name,
        "target": R.target_display(INT_MAX, None, None),
        "path": R.cost_page_url(INT_MAX),
        "name": R.diagram_display_name(title, INT_MAX),
        "score": str(INT_MAX),
        "count": str(INT_MAX),
    }
    formatter = string.Formatter()
    nested = {"reason", "side_effect"}

    def fields(template):
        return {f for _, f, _, _ in formatter.parse(template) if f}

    first = [
        tpl.format(**values) for tpl in R.PHRASES.values() if not (fields(tpl) & nested)
    ]
    longest_first = max(first, key=T.cjson_encoded_size)
    second = [
        tpl.format(**values, reason=longest_first, side_effect=longest_first)
        for tpl in R.PHRASES.values()
        if fields(tpl) & nested
    ]
    return max(first + second + [R.SIDE_EFFECT_UNKNOWN], key=T.cjson_encoded_size)


def segment():
    return SimpleNamespace(diagram_id=INT_MAX, system_id=INT_MAX, project_id=INT_MAX)


def worst_overlay(item: dict, title: str) -> dict:
    """把建項之後才寫入、或只由識別碼組成的欄位一律設成最長可能值。

    `requestText` 不覆寫——它的長度正是要驗證的生產截斷結果。
    """
    phrase = worst_phrase(title)
    longest_status = max(R.STATUSES, key=T.cjson_encoded_size)
    longest_stage = max(R.DISPATCH_STAGES, key=T.cjson_encoded_size)
    longest_capability = max((ARCH, REVIEW, COST), key=T.cjson_encoded_size)
    longest_segment = max(T.SEGMENT_IDS, key=T.cjson_encoded_size)
    label = worst_label()
    return {
        **item,
        "sessionKey": WORST_SESSION_KEY,
        "label": label,
        "status": longest_status,
        "capability": longest_capability,
        "waitingOn": label,
        "failureReason": phrase,
        "sideEffect": phrase,
        "estimateSetId": INT_MAX,
        "dependsOn": item["workItemId"],
        "targetDiagramId": INT_MAX,
        "targetSystemId": INT_MAX,
        # 生產落點的同一個表示式（`_execute_architecture`）。
        "targetDiagramTitle": R.truncate_to_encoded_bytes(title, R.DIAGRAM_TITLE_MAX_BYTES),
        "targetDisplay": R.target_display(INT_MAX, None, None),
        "segmentId": longest_segment,
        "deadlineAt": item["createdAt"],
        "dispatchStage": longest_stage,
        "dispatchIndex": INT_MAX,
    }


def build_worst_items():
    """回傳 `(進行中最壞項, 已結束最壞項)`，兩者都經生產路徑產生 `requestText`。"""
    title = adversarial(2 * 200)  # 比 200 字的標題上限更長，交給截斷決定
    utterance = adversarial(4 * REQUEST_TEXT_MAX_CHARS)

    async def scenario():
        h = Harness()
        built = h.orchestrator._build_items(
            SESSION_KEY, segment(), "assessment", [ARCH, COST], utterance
        )
        assert set(built[1]) == EXPECTED_FIELDS, set(built[1]) ^ EXPECTED_FIELDS
        active = built[0]
        # 經 `_cas` 轉為已結束：瘦身由生產程式決定。
        h.store.put_work_item(SESSION_KEY, active)
        ok = h.orchestrator._cas(
            SESSION_KEY,
            active,
            R.ACTIVE_STATUSES,
            {"status": R.STATUS_FAILED, "failureReason": "x", "deadlineAt": None},
        )
        assert ok
        terminal = h.store.load_work_items(SESSION_KEY)[active["workItemId"]]
        await h.stop_all()
        return built[1], terminal

    active, terminal = asyncio.run(scenario())
    return worst_overlay(active, title), worst_overlay(terminal, title)


class TruncateToEncodedBytesTest(unittest.TestCase):
    def test_cuts_on_character_boundary_under_the_byte_cap(self):
        """
        @purpose 截斷依序列化後位元組計算，6 B 的控制字元與 4 B 的 emoji 不會讓結果超過上限，也不切壞字元
        @given 上限 10 B
        @step 截 5 個控制字元 | 剩 1 個（6 B），第 2 個會到 12 B
        @step 截 5 個 emoji | 剩 2 個（8 B）
        @step 截 20 個中文字 | 剩 3 個（9 B）
        @pass 每個結果都是原字串的前綴且序列化後 ≤ 10 B
        @story US1.1
        """
        self.assertEqual(R.truncate_to_encoded_bytes(CONTROL * 5, 10), CONTROL)
        self.assertEqual(R.truncate_to_encoded_bytes(EMOJI * 5, 10), EMOJI * 2)
        self.assertEqual(R.truncate_to_encoded_bytes("需" * 20, 10), "需" * 3)
        self.assertEqual(R.truncate_to_encoded_bytes("", 10), "")
        self.assertEqual(R.truncate_to_encoded_bytes(None, 10), "")
        self.assertEqual(R.truncate_to_encoded_bytes("abc", 0), "")

    def test_short_text_is_returned_unchanged(self):
        self.assertEqual(R.truncate_to_encoded_bytes("加上快取層", 6000), "加上快取層")

    @settings(max_examples=200, deadline=None)
    @given(st.text(max_size=300), st.integers(min_value=0, max_value=400))
    def test_result_is_the_longest_prefix_within_the_cap(self, text, cap):
        result = R.truncate_to_encoded_bytes(text, cap)
        self.assertTrue(text.startswith(result))
        self.assertLessEqual(T.cjson_encoded_size(result) - 2, cap)
        if len(result) < len(text):
            longer = text[: len(result) + 1]
            self.assertGreater(T.cjson_encoded_size(longer) - 2, cap)


class WorkItemByteBoundTest(unittest.TestCase):
    def test_worst_active_item_fits_the_documented_bound(self):
        """
        @purpose 進行中工作項的最壞大小是位元組上界：原句與圖名填滿 6 B 控制字元與 4 B emoji 也不超過文件宣告的值
        @given 一句 8000 字的對抗原句、一個 400 字的對抗圖名、所有識別碼取 int32 上限
        @step 經 `_build_items` 建項，其餘欄位取最長可能值 | 序列化後 ＋ 欄位名 ≤ WORK_ITEM_ACTIVE_MAX_BYTES
        @pass 上界對任何輸入字元都成立
        @story US1.1
        """
        active, _ = build_worst_items()
        self.assertLessEqual(
            T.cjson_encoded_size(active["requestText"]) - 2, R.REQUEST_TEXT_MAX_BYTES
        )
        self.assertLessEqual(stored_size(active), R.WORK_ITEM_ACTIVE_MAX_BYTES)

    def test_worst_terminal_item_fits_the_documented_bound(self):
        """
        @purpose 轉為已結束後的工作項最壞大小同樣是位元組上界（原句瘦身以位元組計）
        @given 同上的最壞進行中項
        @step 經 `_cas` 轉為失敗 | requestText ≤ TERMINAL_REQUEST_TEXT_MAX_BYTES
        @step 其餘欄位取最長可能值 | 序列化後 ＋ 欄位名 ≤ WORK_ITEM_TERMINAL_MAX_BYTES
        @pass 上界對任何輸入字元都成立
        @story US1.1
        """
        _, terminal = build_worst_items()
        self.assertLessEqual(
            T.cjson_encoded_size(terminal["requestText"]) - 2, R.TERMINAL_REQUEST_TEXT_MAX_BYTES
        )
        self.assertLessEqual(len(terminal["requestText"]), CHANGE_SUMMARY_MAX_CHARS)
        self.assertLessEqual(stored_size(terminal), R.WORK_ITEM_TERMINAL_MAX_BYTES)

    def test_chinese_request_text_keeps_the_first_2000_characters(self):
        """BR52.6：中文原句仍保留前 2000 字（6000 B 恰好容得下）。"""

        async def scenario():
            h = Harness()
            built = h.orchestrator._build_items(
                SESSION_KEY, segment(), "shared", [ARCH], "需" * 2500
            )
            await h.stop_all()
            return built[0]["requestText"]

        self.assertEqual(asyncio.run(scenario()), "需" * REQUEST_TEXT_MAX_CHARS)

    def test_diagram_display_name_is_byte_bounded(self):
        name = R.diagram_display_name(adversarial(1000), 1)
        self.assertLessEqual(
            T.cjson_encoded_size(name) - 2,
            R.DIAGRAM_TITLE_MAX_BYTES + T.cjson_encoded_size("〈〉") - 2,
        )


class CapacityCommitmentTest(unittest.TestCase):
    def test_three_hundred_worst_sessions_fit_in_80_percent_of_maxmemory(self):
        """
        @purpose NFR4.40：80% 的 maxmemory 內容得下至少 300 個填滿上界的 session
        @given 對話 3 × 200 KiB、進行中 5 筆、已結束 20 筆，每筆取位元組上界
        @step 計算單一 session 最壞值 | 614,400 ＋ 5 × 進行中上界 ＋ 20 × 已結束上界
        @step 乘以 300 | ≤ 256 MiB 的 80%
        @pass 承諾成立（算式與 DEPLOY.md 的容量表同源）
        @story US1.1
        """
        self.assertEqual(R.CONVERSATION_MAX_BYTES, 614_400)
        per_session = (
            614_400
            + R.MAX_ACTIVE_WORK_ITEMS * R.WORK_ITEM_ACTIVE_MAX_BYTES
            + R.MAX_TERMINAL_WORK_ITEMS * R.WORK_ITEM_TERMINAL_MAX_BYTES
        )
        self.assertEqual(per_session, R.session_worst_case_bytes())
        budget = R.REDIS_MAXMEMORY_BYTES * 80 // 100
        self.assertEqual(budget, 214_748_364)
        self.assertLessEqual(per_session * R.COMMITTED_SESSIONS, budget)
        self.assertLessEqual(per_session, budget / R.COMMITTED_SESSIONS)


if __name__ == "__main__":
    unittest.main()
