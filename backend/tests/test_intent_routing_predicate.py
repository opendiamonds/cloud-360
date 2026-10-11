"""`U11 intent-router` 的 **L5 property-based 測試**——`ADR-0006` 的 hard constraint。

本檔對應 `unit-test-instructions.md §三` 的第一列，是本單元**唯一**的
hard-constraint 測試檔。

## PBT 在本單元是 blocking，不是 N/A

`project.md ## Testing Posture` 逐字點名三個落點（IaC generator、cost
calculator、**agent routing**），而本單元**就是** agent routing；
`contract-summary.md:797-799` 的 `pbt_note` 逐字指定受測對象是「門檻比較這個
純函式」。這與 `U8 memory-service` 那一輪的 N/A 判定**不同**，不得沿用。

## 生成策略的兩個硬性要求（`nfr-design/performance-design.md` §五）

1. **`scoresAvailable` 必須由 `st.booleans()` 顯式驅動**，不得讓「分數存不
   存在」隨機浮現。Hypothesis **不會**因為某個分支從未被抽到而報錯——若策略
   偏好生成帶分數的候選，`BR3.3`（無分數分支）可能長期零覆蓋而無人察覺，
   而 `BR3.3` 正是 `FR1.6` 逐字警告的「`FR1.3` 靜默永不觸發」的唯一防線。
2. **`len(slots)` 必須顯式涵蓋 1 與 ≥2 兩種情形**，否則 `P6`／`P7` 只會在
   單槽位上被驗證，而 `R-01` 的失敗情境恰好**只在多槽位出現**。

本檔的做法比「顯式驅動」更強一步：策略**連每個槽位可不可單選也是抽出來的**
（`flags`），所以每個 property 都有一組**已知的期望值**可比，而不是只斷言
一條在前提為假時恆真的蘊含式。

而「顯式驅動」本身也被**斷言**而不只是被宣稱：`StrategyReachesEveryBranchTest`
以 `hypothesis.find` 對 `有無分數 × 單／多槽位 × 可／不可交辦` 的**八個**
組合各找一個實例，找不到即 `NoSuchExample`。沒有這一條，上面那段話就只是
一個沒有證據的宣稱——而 property 在前提為假時是恆真的，所以「全綠」本身
並不保證那些分支被走過。

## `P3` 為什麼限定在無分數分支

`functional-spec.md` §五 的 `P3` 是「候選數為 1 ⇒ `can_single_out` 為真」，
而它的 why 欄寫「不涉及分數」。逐字代入 `BR3.2`：有分數時單一候選若分數
0.1、門檻 0.9，述詞為**假**——而那是**正確**行為。`P3` 的來源是 `BR3.3`
的 `(slot 候選數 == 1)` 這個 disjunct，故本檔把它限定在無分數分支。
不限定就會是一條必然失敗、而且失敗得有道理的 property。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest
from dataclasses import replace

from hypothesis import find, given, settings
from hypothesis import strategies as st

from services.intent_routing_predicate import (
    can_dispatch,
    can_single_out,
    has_unresolved_referent,
    clarify_candidates_for,
    decide,
    derive_contract_confidence,
    intents_for,
)
from services.intent_routing_types import (
    MAX_SLOTS,
    REFERENT_ABSENT,
    REFERENT_RESOLVED,
    REFERENT_UNRESOLVED,
    ROUTABLE_CAPABILITIES,
    CandidateIntent,
    CandidateRanking,
    ClassificationResult,
)

#: 門檻的生成域與 `intent_routing_config.resolve_confidence_threshold` 的
#: 驗收域一致（`0 < t <= 1`）。下界取 0.05 而非 0 的額外理由：策略需要
#: 「嚴格低於門檻」這個非空區間才能構造出不可單選的帶分數槽位。
thresholds = st.floats(
    min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False
)

capabilities = st.sampled_from(ROUTABLE_CAPABILITIES)
labels = st.text(min_size=1, max_size=16)


def _candidate(capability, rank, label, tied, score, referent_state=REFERENT_ABSENT):
    return CandidateIntent(
        capability=capability,
        rank=rank,
        label=label,
        tied_with_next=tied,
        referent_state=referent_state,
        referent="訂單系統架構圖" if referent_state == REFERENT_RESOLVED else None,
        score=score,
    )


#: 可單選的槽位**不得**含 `unresolved`（`BR5.2`／`AC6.1.2`）；另兩個狀態都正常。
#: **`absent` 必須在這裡**——它是「這句話沒有指涉詞」，例如「幫我畫一張架構圖」，
#: 把它排除會讓這一組測試誤以為不帶指涉詞的輸入也該被反問。
_SAFE_REFERENT_STATES = st.sampled_from((REFERENT_ABSENT, REFERENT_RESOLVED))

#: 槽位不可單選的**原因**。自 `R-01` 起有兩種（帶分數時）或三種（無分數時）
#: ——而它必須被**顯式抽樣**，理由與 `scoresAvailable` 相同：Hypothesis 不會
#: 因為某個失敗原因從未被抽到而報錯，而 `unresolved` 這個原因是本輪才補上
#: 讀取端的，最容易長期零覆蓋。
_SCORED_FAILURE_REASONS = st.sampled_from(("score", "unresolved"))
_UNSCORED_FAILURE_REASONS = st.sampled_from(("tie", "unresolved"))


def _mark_one_unresolved(draw, candidates):
    """把其中一個候選改標為 `unresolved`（位置也是抽的）。

    位置要抽，是因為 `can_single_out` 刻意看**全部**候選而不只看 `rank == 1`
    （見 `has_unresolved_referent` 的 docstring）——只把 rank 1 標成
    `unresolved` 的策略會讓「只檢查 rank 1」的實作也全綠。
    """
    index = draw(st.integers(min_value=0, max_value=len(candidates) - 1))
    target = candidates[index]
    return (
        candidates[:index]
        + (
            _candidate(
                target.capability,
                target.rank,
                target.label,
                target.tied_with_next,
                target.score,
                referent_state=REFERENT_UNRESOLVED,
            ),
        )
        + candidates[index + 1 :]
    )


@st.composite
def _scored_ranking(draw, threshold, single_out):
    """帶分數的槽位。`single_out` 為假時**原因也是抽的**（分數或指涉詞）。"""
    reason = None if single_out else draw(_SCORED_FAILURE_REASONS)
    size = draw(st.integers(min_value=1, max_value=4))
    if single_out or reason == "unresolved":
        # `unresolved` 的那一種刻意讓分數**高於門檻**：述詞必須照樣為假，
        # 否則「指涉詞解析不出來但模型很有信心」就會被交辦。
        top = draw(
            st.floats(
                min_value=threshold,
                max_value=1.0,
                allow_nan=False,
                allow_infinity=False,
            )
        )
    else:
        top = draw(
            st.floats(
                min_value=0.0,
                max_value=threshold,
                exclude_max=True,
                allow_nan=False,
                allow_infinity=False,
            )
        )
    rest = draw(
        st.lists(
            st.floats(
                min_value=0.0, max_value=top, allow_nan=False, allow_infinity=False
            ),
            min_size=size - 1,
            max_size=size - 1,
        )
    )
    scores = [top] + sorted(rest, reverse=True)
    out = []
    for index, score in enumerate(scores):
        out.append(
            _candidate(
                draw(capabilities),
                index + 1,
                draw(labels),
                index < len(scores) - 1 and draw(st.booleans()),
                score,
                referent_state=draw(_SAFE_REFERENT_STATES),
            )
        )
    candidates = tuple(out)
    if reason == "unresolved":
        candidates = _mark_one_unresolved(draw, candidates)
    return CandidateRanking(candidates=candidates)


@st.composite
def _unscored_ranking(draw, single_out):
    """無分數的槽位（`BR3.3` ＋ `BR5.2`）。

    `single_out` 為真時：候選數 1，**或** rank 1 未被標為與下一名並列；且
    **沒有任何候選是 `unresolved`**。

    為假時原因是抽的：
    * `tie` —— 候選數 ≥ 2 且 rank 1 被標為並列（`BR3.3` 唯一能讓述詞為假的構造）。
    * `unresolved` —— 任一候選宣告指涉詞解析不出來（`BR5.2`／`AC6.1.2`），
      此時並列與否**無關**，所以這一支刻意**不**順便製造並列。

    **單一候選時 `tied_with_next` 是抽的，而那是刻意的（`R-07`）**：原策略把它
    固定為 `False`，於是單一候選永遠由 `BR3.3` 的**第二個** disjunct
    （`not top.tied_with_next`）滿足，把第一個 disjunct（`len == 1`）從述詞裡
    刪掉 `P3` 仍會全綠——而檔頭逐字說 `P3` 的來源是第一個 disjunct。
    該輸入在產線可達：`V-4` 只檢查 `rank`，不要求單一候選的 `tied_with_next`
    為 `False`，所以「唯一候選卻被標為並列」會進到述詞。
    """
    reason = None if single_out else draw(_UNSCORED_FAILURE_REASONS)
    if single_out or reason == "unresolved":
        size = draw(st.integers(min_value=1, max_value=4))
        top_tied = draw(st.booleans()) if size == 1 else False
    else:
        size = draw(st.integers(min_value=2, max_value=4))
        top_tied = True
    out = []
    for index in range(size):
        tied = top_tied if index == 0 else (
            index < size - 1 and draw(st.booleans())
        )
        out.append(
            _candidate(
                draw(capabilities),
                index + 1,
                draw(labels),
                tied,
                None,
                referent_state=draw(_SAFE_REFERENT_STATES),
            )
        )
    candidates = tuple(out)
    if reason == "unresolved":
        candidates = _mark_one_unresolved(draw, candidates)
    return CandidateRanking(candidates=candidates)


@st.composite
def scenarios(draw, with_scores=None, min_slots=1, max_slots=MAX_SLOTS):
    """回 `(threshold, result, single_out_flags)`。

    `with_scores` 與 `slot_count` **都是抽出來的**（或由呼叫端釘住），每個
    槽位可不可單選、以及**不可單選的原因**也都是抽出來的——故每個 property
    都有已知期望值可比。
    """
    threshold = draw(thresholds)
    scores_available = draw(st.booleans()) if with_scores is None else with_scores
    slot_count = draw(st.integers(min_value=min_slots, max_value=max_slots))
    flags = draw(
        st.lists(st.booleans(), min_size=slot_count, max_size=slot_count)
    )
    slots = []
    for flag in flags:
        if scores_available:
            slots.append(draw(_scored_ranking(threshold, flag)))
        else:
            slots.append(draw(_unscored_ranking(flag)))
    result = ClassificationResult(
        slots=tuple(slots),
        slot_labels=tuple(draw(labels) for _ in range(slot_count)),
    )
    return threshold, result, tuple(flags)



class CanSingleOutPropertyTest(unittest.TestCase):
    """`functional-spec.md` §五 的 `P1`–`P7`，**七條全部 `@given`**。"""

    @given(scenarios())
    @settings(max_examples=300, deadline=None)
    def test_p1_not_dispatchable_means_no_intents_and_some_candidates(
        self, scenario
    ):
        """`P1`：述詞聚合為假 ⇒ `intents` 空且 `candidates` 非空（`EC4`）。

        `FR1.3` 逐字「不得交辦、**不得產生任何結果**」。兩個欄位任一不符即
        違反——只檢查 `intents` 空會放行一個同時附上候選與工作項的實作。
        """
        threshold, result, flags = scenario
        if all(flags):
            return
        decision = decide(result, threshold)
        self.assertTrue(decision.below_threshold)
        self.assertEqual(decision.intents, ())
        self.assertTrue(decision.candidates)

    @given(scenarios())
    @settings(max_examples=300, deadline=None)
    def test_p2_dispatchable_means_intents_and_no_candidates(self, scenario):
        """`P2`：聚合為真 ⇒ `intents` 非空且 `candidates` 為空（`EC5`）。

        `EC5` 是 `EC4` 的反向不變量。少了它，一個同時給出工作項與候選清單的
        回應會通過 `EC4`。
        """
        threshold, result, flags = scenario
        if not all(flags):
            return
        decision = decide(result, threshold)
        self.assertFalse(decision.below_threshold)
        self.assertTrue(decision.intents)
        self.assertFalse(decision.candidates)

    @given(_unscored_ranking(True), thresholds)
    @settings(max_examples=200, deadline=None)
    def test_p3_single_candidate_without_scores_can_be_singled_out(
        self, ranking, threshold
    ):
        """`P3`：**無分數、候選數為 1、且指涉詞不是解析失敗** ⇒ 述詞為真。

        `functional-spec.md` §五 的 `P3` 原文是「候選數為 1 ⇒ `can_single_out`
        為真」，而它**需要兩次收窄**，兩次的形狀相同（原文漏掉一個前提，而
        少了前提的版本是一條必然失敗、而且失敗得有道理的 property）：

        1. **限定在無分數分支**（`BR3.2`）：有分數時單一候選分數 0.1、門檻 0.7
           ⇒ 述詞為**假**，那是正確行為。`P3` 的來源是 `BR3.3` 的
           `(slot 候選數 == 1)` 這個 disjunct。
        2. **排除 `unresolved`**（`BR5.2`／`AC6.1.2`，**本輪新增**）：單一候選
           但指涉詞解析不出來時，述詞必須為假——`AC6.1.2` 的 Then 逐字
           「走 `US1.2` 的反問路徑，不擅自挑一個」。策略以
           `_SAFE_REFERENT_STATES` 承載這個前提，而本測試**另行斷言它**，
           因為「策略剛好沒生成它」與「這個前提是刻意的」在測試上長得一樣。

        **突變驗證（`R-07`）**：把 `len(ranking.candidates) == 1` 從
        `can_single_out` 刪掉之後本條會紅——前提是策略抽得出「單一候選且
        `tied_with_next=True`」，而那正是 `_unscored_ranking` 本輪的修正。
        """
        if len(ranking.candidates) != 1:
            return
        self.assertFalse(ranking.scores_available)
        self.assertNotEqual(
            ranking.candidates[0].referent_state, REFERENT_UNRESOLVED
        )
        self.assertTrue(can_single_out(ranking, threshold))

    @given(
        scenarios(with_scores=True),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False,
                  allow_infinity=False),
    )
    @settings(max_examples=300, deadline=None)
    def test_p4_raising_the_top_score_never_flips_true_to_false(
        self, scenario, raise_factor
    ):
        """`P4`：有分數時，**提高最高分不使述詞由真變假**（單調）。

        這是唯一一條在 `OQ-10` 結論為「無可用信心訊號」時前提會變成空集合的
        property——其餘六條都不涉及分數，這正是 `[IR1]`=A 的價值。

        **提高後的分數自 `[原分數, 1.0]` 抽，不是固定 `1.0`（`R-07`）**：
        `1.0 >= threshold` 對整個門檻值域恆真，所以固定 `1.0` 時 `after` 恆為
        真、`assertFalse(before and not after)` 幾乎不受實作影響——它測的是
        **單一端點**而不是單調性。以 `raise_factor` 在區間內線性插值之後，
        Hypothesis 可以落在任何中段值；該區間含兩個端點（`factor=0` 即不提高、
        `factor=1` 即提到滿分）。

        **突變驗證（`R-07`）**：在 `can_single_out` 的有分數分支插一段中段
        凹陷（例如 `and not (0.80 <= top.score < 0.85)`）之後本條會紅，而
        固定 `1.0` 的舊版不會。
        """
        threshold, result, _ = scenario
        for slot in result.slots:
            before = can_single_out(slot, threshold)
            top = slot.candidates[0]
            raised_score = top.score + (1.0 - top.score) * raise_factor
            raised = replace(
                slot,
                candidates=(replace(top, score=raised_score),)
                + slot.candidates[1:],
            )
            self.assertGreaterEqual(raised_score, top.score)
            after = can_single_out(raised, threshold)
            self.assertFalse(before and not after)

    @given(scenarios())
    @settings(max_examples=300, deadline=None)
    def test_p5_the_predicate_returns_a_bool_and_never_raises(self, scenario):
        """`P5`：對任何**合法** ranking 回傳布林值，不 raise（`BR8.3`／`NFR3.71`）。

        述詞會 raise 就不是純函式，PBT 的 property 也無法表述。
        """
        threshold, result, _ = scenario
        for slot in result.slots:
            self.assertIsInstance(can_single_out(slot, threshold), bool)
        self.assertIsInstance(can_dispatch(result, threshold), bool)
        self.assertIsInstance(
            derive_contract_confidence(
                result, threshold, can_dispatch(result, threshold)
            ),
            float,
        )

    @given(scenarios())
    @settings(max_examples=400, deadline=None)
    def test_p6_every_slot_singled_out_yields_one_intent_per_slot(self, scenario):
        """`P6`：每槽位皆可單選 ⇒ `len(intents) == len(slots)`，第 i 個取第 i
        槽位 `rank == 1`（`BR4.4`／`EC7`）。

        **這是 `R-01` 的可執行形式。** `P1`／`P2` 只斷言 `intents` 空或非空，
        而「非空但少了一個」完全通過——`FR5.1` 的官方可測不變量（改圖＋估成本
        ⇒ **2 個**）於是可以用 1 個 `Intent` 滿足，第二個請求被靜默丟棄而
        `US5.1` 在追溯表上仍標 `OK`。本條是一條**等式**，它把那件事變成可被
        Hypothesis 反覆打的斷言。
        """
        threshold, result, flags = scenario
        if not all(flags):
            return
        intents = intents_for(result)
        self.assertEqual(len(intents), len(result.slots))
        for index, intent in enumerate(intents):
            top = result.slots[index].candidates[0]
            self.assertEqual(top.rank, 1)
            self.assertEqual(intent.capability, top.capability)
            self.assertEqual(intent.referent, top.referent)

    @given(scenarios())
    @settings(max_examples=400, deadline=None)
    def test_p7_any_failed_slot_is_represented_in_the_candidates(self, scenario):
        """`P7`：任一槽位不可單選 ⇒ `intents` 空，且 `candidates` 含**每一個**
        失敗槽位至少一個候選（`BR4.5`／`EC8`）。

        只斷言「candidates 非空」會放行一個只攤平第一個失敗槽位的實作——
        而那時使用者看到的反問少問了一件事。

        **本輪起失敗原因有兩種（帶分數）或三種（無分數）**：分數低於門檻、
        rank 1 與 rank 2 並列、以及**指涉詞解析不出來**（`R-01` 新增的
        `BR5.2`／`AC6.1.2` 讀取端）。策略顯式抽樣原因，所以本條對三種原因
        **一律**斷言「該槽位的候選出現在攤平清單裡」——攤平的實作若只處理前
        兩種（例如用 `score < threshold` 判定失敗槽位而不是重呼述詞），
        `unresolved` 造成的失敗槽位就會從反問清單裡消失。
        """
        threshold, result, flags = scenario
        if all(flags):
            return
        decision = decide(result, threshold)
        self.assertEqual(decision.intents, ())
        flattened = clarify_candidates_for(result, threshold)
        self.assertEqual(decision.candidates, flattened)
        for index, flag in enumerate(flags):
            if flag:
                continue
            expected = {c.capability for c in result.slots[index].candidates}
            self.assertTrue(
                expected & {c.capability for c in flattened},
                f"失敗槽位 {index} 的候選完全沒有出現在攤平清單裡",
            )
            # 失敗槽位必須真的是失敗的——反向確認期望值不是憑旗標推來的。
            self.assertFalse(can_single_out(result.slots[index], threshold))
        self.assertEqual(len(decision.candidates), len({c.id for c in decision.candidates}))


class ThresholdBoundaryTest(unittest.TestCase):
    """兩條 example-based：`BR3.2` 的門檻邊界與 `BR3.3` 的並列判定。

    它們不是 property 的替代品，而是補上 property 不會特別去打的**單點**：
    邊界的「恰等於」與並列旗標的兩個值。
    """

    def test_br3_2_score_exactly_at_the_threshold_can_be_singled_out(self):
        """`FR1.7` 逐字「`信心值 < 0.7` 即進入 FR1.3 的反問路徑」——

        亦即**恰等於門檻時交辦**。寫成 `>` 會讓門檻的語意偏移一個邊界點，
        而那個偏移在隨機測試裡幾乎不會被抽到。
        """
        ranking = CandidateRanking(
            candidates=(
                _candidate("architecture-design", 1, "改架構圖", False, 0.7),
            )
        )
        self.assertTrue(ranking.scores_available)
        self.assertTrue(can_single_out(ranking, 0.7))
        self.assertFalse(
            can_single_out(
                CandidateRanking(
                    candidates=(
                        _candidate(
                            "architecture-design", 1, "改架構圖", False, 0.69
                        ),
                    )
                ),
                0.7,
            )
        )

    def test_br3_3_tie_without_scores_forces_a_clarify(self):
        """`BR3.3`：無分數時並列 ⇒ 不可單選；未並列 ⇒ 可單選。

        **少了 `tied_with_next` 這一個欄位，這條就不可能成立**：`rank` 依
        `V-4` 永遠是 1、2、3…，用它判定「有無嚴格優先」等於永遠「有」，
        於是 `FR1.3` 靜默永不觸發——`FR1.6` 逐字警告的那個後果。
        """
        tied = CandidateRanking(
            candidates=(
                _candidate("architecture-design", 1, "改架構圖", True, None),
                _candidate("well-architected-review", 2, "做評核", False, None),
            )
        )
        untied = CandidateRanking(
            candidates=(
                _candidate("architecture-design", 1, "改架構圖", False, None),
                _candidate("well-architected-review", 2, "做評核", False, None),
            )
        )
        self.assertFalse(tied.scores_available)
        self.assertFalse(can_single_out(tied, 0.7))
        self.assertTrue(can_single_out(untied, 0.7))


class UnresolvedReferentForcesAClarifyTest(unittest.TestCase):
    """`R-01` 的 example-based 閘門：審查構造出來的那一條執行期路徑。

    審查逐字給的可構造路徑是：「模型回單一候選、`tied_with_next=false`、
    `scores` 缺、`referent_state="unresolved"` ⇒ `can_single_out` 為真 ⇒
    `can_dispatch` 為真 ⇒ 交辦一個 `referent=None` 的 `Intent`」。
    本類別把那一條路徑逐欄寫成實例——property 會覆蓋它，但一條**具名的、
    逐欄對應審查原文**的測試讓下一個人知道這裡曾經壞過，以及壞成什麼樣。
    """

    def _ranking(self, state, *, tied=False, score=None, size=1):
        return CandidateRanking(
            candidates=tuple(
                _candidate(
                    "architecture-design",
                    index + 1,
                    "改架構圖",
                    tied if index == 0 else False,
                    score,
                    referent_state=state if index == 0 else REFERENT_ABSENT,
                )
                for index in range(size)
            )
        )

    def test_the_exact_path_the_review_constructed_now_asks_back(self):
        """單一候選 ＋ 未並列 ＋ 無分數 ＋ `unresolved` ⇒ **反問**。

        修正前這條路徑的三個條件（單一候選、未並列、無分數）合起來讓述詞為真，
        而第四個條件（`unresolved`）零讀取端。
        """
        ranking = self._ranking(REFERENT_UNRESOLVED)
        self.assertFalse(ranking.scores_available)
        self.assertEqual(len(ranking.candidates), 1)
        self.assertFalse(ranking.candidates[0].tied_with_next)
        self.assertFalse(can_single_out(ranking, 0.7))

        result = ClassificationResult(slots=(ranking,), slot_labels=("改架構圖",))
        decision = decide(result, 0.7)
        self.assertTrue(decision.below_threshold)
        self.assertEqual(decision.intents, ())
        self.assertTrue(decision.candidates)

    def test_a_confident_score_does_not_override_an_unresolved_referent(self):
        """分數 0.99、門檻 0.7，**仍然反問**。

        「指涉詞解析不出來但模型很有信心」是最該被擋下的那一種：信心高的是
        「要做哪件事」，不確定的是「對誰做」，而 `BR5.2` 管的是後者。
        """
        ranking = self._ranking(REFERENT_UNRESOLVED, score=0.99)
        self.assertTrue(ranking.scores_available)
        self.assertFalse(can_single_out(ranking, 0.7))

    def test_absent_is_normal_and_must_not_be_dragged_in(self):
        """**`absent` 不得連帶擋下**——這是 `R-01` 最容易做錯的地方。

        「幫我畫一張架構圖」句子裡本來就沒有指涉詞，`referent_state` 為
        `absent`。把它一併當成「解析不出來」會讓每一句不帶指涉詞的輸入都被
        反問，`FR1.1`（一句話交辦）直接不可用——那是一個比原缺口更大的回歸，
        而它不會有任何其他測試擋得住。
        """
        self.assertTrue(can_single_out(self._ranking(REFERENT_ABSENT), 0.7))
        self.assertTrue(can_single_out(self._ranking(REFERENT_RESOLVED), 0.7))

    def test_an_unresolved_candidate_outside_rank_one_also_asks_back(self):
        """`unresolved` 落在 rank 2 時**同樣**反問。

        理由見 `has_unresolved_referent` 的 docstring：不可唯一解析是**這句話**
        的性質，不是某一個讀法的性質。只檢查 `rank == 1` 的實作會通過上面三條
        而被這一條擋下。
        """
        ranking = CandidateRanking(
            candidates=(
                _candidate("architecture-design", 1, "改架構圖", False, None),
                _candidate(
                    "cost-finops", 2, "估成本", False, None,
                    referent_state=REFERENT_UNRESOLVED,
                ),
            )
        )
        self.assertFalse(can_single_out(ranking, 0.7))


class StrategyReachesEveryBranchTest(unittest.TestCase):
    """**把「生成策略涵蓋了那些分支」從宣稱變成斷言。**

    `performance-design.md` §五 的兩個硬性要求（`scoresAvailable` 顯式驅動、
    `len(slots)` 涵蓋 1 與 ≥2）之所以存在，是因為 Hypothesis **不會**因為某個
    分支從未被抽到而報錯。但「我寫了 `st.booleans()`」與「那兩個值真的都被
    生成過」仍是兩件事——而上面七條 property 在前提為假時是**恆真**的，所以
    它們全綠並不證明分支被走過。

    `hypothesis.find` 對每個組合實際找出一個實例，找不到就 `NoSuchExample`。
    """

    def test_every_combination_of_the_three_axes_is_reachable(self):
        axes = []
        for scores_available in (True, False):
            for multi_slot in (True, False):
                for dispatchable in (True, False):
                    axes.append((scores_available, multi_slot, dispatchable))
        for scores_available, multi_slot, dispatchable in axes:
            with self.subTest(
                scores=scores_available, multi=multi_slot, dispatch=dispatchable
            ):

                def matches(scenario):
                    _, result, flags = scenario
                    return (
                        result.scores_available is scores_available
                        and (len(result.slots) >= 2) is multi_slot
                        and all(flags) is dispatchable
                    )

                found = find(scenarios(min_slots=2 if multi_slot else 1), matches)
                self.assertTrue(matches(found))

    def test_the_unresolved_failure_reason_is_reachable_in_both_score_modes(self):
        """**`R-01` 的失敗原因也必須被證明生成得出來。**

        `unresolved` 是本輪才補上讀取端的，所以它是最容易長期零覆蓋的那個
        分支——而七條 property 在前提為假時恆真，全綠不保證它被走過。
        以 `hypothesis.find` 對「有分數」與「無分數」兩種模式各找一個
        **因 `unresolved` 而失敗**的實例。
        """
        for scores_available in (True, False):
            with self.subTest(scores=scores_available):

                def matches(scenario):
                    threshold, result, flags = scenario
                    if result.scores_available is not scores_available:
                        return False
                    for slot, flag in zip(result.slots, flags):
                        if flag:
                            continue
                        if not has_unresolved_referent(slot):
                            continue
                        # 該槽位確實因 unresolved 而失敗（而非順便也低分／並列）
                        return not can_single_out(slot, threshold)
                    return False

                found = find(scenarios(with_scores=scores_available), matches)
                self.assertTrue(matches(found))


if __name__ == "__main__":
    unittest.main()
