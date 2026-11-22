"""`U8 memory-service` 的純函式 property-based 測試（`NFR3.24`）。

本檔對應 `unit-test-instructions.md §4.2`。零 DB、零網路。

## PBT 在本單元是良好實踐，**不是** ADR-0006 的 hard constraint

`project.md ## Testing Posture` 點名三個落點（IaC generator、cost calculator、
agent routing）——`agent routing` 指 `U11 intent-router`，而本單元不是其中任何
一個。故 ADR-0006 的 PBT hard constraint 對本單元是 **N/A（非豁免、非違反）**。

**但 `NFR3.24` 的次級排序鍵是純函式**，而 `team.md` 記載 repo 已有 13 個
`@given` 先例、皆落在純函式模組，屬自發良好實踐。`security-design.md §八`
把它記為 `D8-3`。

## 性質的選擇：為什麼不是「同一輸入回同一結果」

「同一組輸入連續兩次回相同順序」對**任何**純函式都恆真，是恆真斷言
（`project.md` 記過那個形狀：「驗的是『沒有某個不存在的限制』」）。
真正會失敗的性質是**排列不變性**——而它只在次級排序鍵存在時成立。

`code-generation-plan.md` Step 9 的突變 5（移除次級排序鍵）正是靠它變紅。

## `allow_nan=False` 是刻意的

NaN 與任何值的比較皆為偽，故含 NaN 的鍵不再是全序，排列不變性會
**無意義地**失敗——那會是在測 Python 的浮點語意，不是測本函式。
而向量相似度不會產生 NaN（`<=>` 對非零向量回 `[0, 2]`）。

`allow_infinity` 保持預設（允許）：`±inf` 可排序，鍵仍是全序，故它是有效輸入。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import random
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from services.memory_ranking import rank_candidates
from services.memory_types import ScoredCandidate

#: `unit-test-instructions.md §4.2` 指定的生成域：`st.text()` 的識別字 ＋
#: `st.floats(allow_nan=False)` 的分數。以 `st.builds` 包成值物件，是因為
#: `rank_candidates` 讀的是屬性而非元組位置（形狀沿用 `MemberSnapshot`）。
candidates = st.lists(
    st.builds(
        ScoredCandidate,
        identifier=st.text(),
        score=st.floats(allow_nan=False),
    ),
    max_size=40,
)


class RankCandidatesPropertyTest(unittest.TestCase):
    """`NFR3.24`：三條性質，而第一條是本單元唯一會因缺少次級鍵而失敗的。"""

    @given(candidates, st.randoms(use_true_random=False))
    @settings(max_examples=200, deadline=None)
    def test_permutation_invariance(self, items, rng):
        """**性質 1**：同一個集合的任意排列，排序結果完全相同。

        這是三條裡唯一能抓到「移除次級排序鍵」的一條。少了 `identifier`，
        `sorted` 的穩定性會讓同分組內的順序**跟著輸入順序走**，於是打亂輸入
        就會得到不同的輸出——而那正是 `NFR3.24` 要防的靜默不穩定：沒有錯誤，
        只有每次可能不同的結果。

        比較的是 `(identifier, score)` 的序列而非物件身分：`ScoredCandidate`
        是 frozen dataclass，值相等即可互換，而排序關心的只有值。
        """
        shuffled = list(items)
        rng.shuffle(shuffled)

        first = [(c.identifier, c.score) for c in rank_candidates(items)]
        second = [(c.identifier, c.score) for c in rank_candidates(shuffled)]
        self.assertEqual(first, second)

    @given(candidates)
    @settings(max_examples=200, deadline=None)
    def test_scores_are_non_increasing(self, items):
        """**性質 2**：結果的分數序列非遞增（分數遞減為主鍵）。

        這一條守的是**方向**。`rank_candidates` 以 `-score` 為主鍵；若改成
        `sorted(..., reverse=True)`，排列不變性**仍然成立**（兩個鍵都反轉後
        依然是全序），所以性質 1 不會變紅——但同分時的識別字會變成遞減，
        而更要緊的是呼叫端若把距離直接當分數傳進來，最**不**相似的列會排在
        最前面且沒有任何東西察覺。

        `memory_service.scored_candidates` 的取負號（距離 → 分數）就是靠這條
        性質才有機械防線。
        """
        scores = [c.score for c in rank_candidates(items)]
        for earlier, later in zip(scores, scores[1:]):
            self.assertGreaterEqual(earlier, later)

    @given(candidates)
    @settings(max_examples=200, deadline=None)
    def test_ties_break_on_ascending_identifier(self, items):
        """**性質 3**：分數相同的相鄰兩筆，識別字遞增。

        這是次級鍵的**方向**斷言。`reverse=True` 的實作會讓它變紅，
        而性質 1、2 都抓不到那個改動——三條合起來才釘住
        「主鍵遞減 ＋ 次鍵遞增」這一個唯一的順序。
        """
        ranked = rank_candidates(items)
        for earlier, later in zip(ranked, ranked[1:]):
            if earlier.score == later.score:
                self.assertLessEqual(earlier.identifier, later.identifier)

    @given(candidates)
    @settings(max_examples=100, deadline=None)
    def test_is_a_permutation_and_does_not_mutate_input(self, items):
        """**附帶性質**：結果是輸入的重排，且輸入未被就地修改。

        不是 `NFR3.24` 要求的，但它守住純度的一半（不就地修改輸入）——
        而那是 `logical-components.md §1.1` 列的禁令之一。
        若少了它，一個「排序並順手去重」的實作會通過上面三條。
        """
        before = [(c.identifier, c.score) for c in items]
        ranked = rank_candidates(items)
        self.assertEqual(len(ranked), len(items))
        self.assertEqual(
            sorted(before), sorted((c.identifier, c.score) for c in ranked)
        )
        self.assertEqual(before, [(c.identifier, c.score) for c in items])


class RankCandidatesExampleTest(unittest.TestCase):
    """兩個具體例子。PBT 說明性質，這兩條說明**結果長什麼樣**。"""

    def test_known_tie_is_broken_deterministically(self):
        """`NFR3.24` 的判準逐字：「可以兩筆人造的同分列直接斷言」。"""
        a = ScoredCandidate(identifier="9", score=0.5)
        b = ScoredCandidate(identifier="10", score=0.5)
        # "10" < "9" 字典序——刻意用會讓「數字大小」直覺出錯的一對，
        # 以確認次級鍵比的是識別字字串本身（`memoryId` 是不透明識別字）。
        self.assertEqual(
            [c.identifier for c in rank_candidates([a, b])], ["10", "9"]
        )
        self.assertEqual(
            [c.identifier for c in rank_candidates([b, a])], ["10", "9"]
        )

    def test_higher_score_comes_first(self):
        low = ScoredCandidate(identifier="a", score=-1.5)
        high = ScoredCandidate(identifier="z", score=-0.2)
        self.assertEqual(
            [c.identifier for c in rank_candidates([low, high])], ["z", "a"]
        )

    def test_negative_zero_ties_with_positive_zero(self):
        """`-0.0 == 0.0` 為真，故兩者視為同分並落到識別字比較。

        寫下來是因為它是唯一一個「鍵看起來不同但其實相等」的浮點情境，
        而若它不成立，排列不變性會在 hypothesis 生成到這一對時紅燈。
        """
        ranked = rank_candidates(
            [
                ScoredCandidate(identifier="b", score=-0.0),
                ScoredCandidate(identifier="a", score=0.0),
            ]
        )
        self.assertEqual([c.identifier for c in ranked], ["a", "b"])


# ---------------------------------------------------------------------------
# 合併前必修第 22 項 (a)：以**真實距離**餵 `scored_candidates`
# ---------------------------------------------------------------------------

#: `<=>`（cosine 距離）對非零向量的值域是 `[0, 2]`。生成域照它取，且排除 NaN
#: ——理由同本檔開頭的 `allow_nan=False`。
distances = st.floats(min_value=0.0, max_value=2.0, allow_nan=False)


def _pairs(distance_by_id):
    """把 `{id: 距離}` 做成 `search_records` 回傳的 `(列, 距離)` 形狀。

    列是**未持久化**的 `MemoryRecord`：`scored_candidates` 只讀 `record.id`，
    不碰 session，所以這裡不需要資料庫。
    """
    from models import MemoryRecord

    return [
        (MemoryRecord(id=memory_id), distance)
        for memory_id, distance in distance_by_id.items()
    ]


class ScoredCandidatesRealDistanceTest(unittest.TestCase):
    """`scored_candidates` → `rank_candidates`：**距離較近者排在前面**。

    ## 為什麼上面的 PBT 驗不到這件事

    `RankCandidatesPropertyTest` 吃的是**手造分數**，從未經過
    `memory_service.scored_candidates`。把該函式的 `score=-distance` 改成
    `score=distance`，排序方向整個反過來（最不相似的排最前），而上面七條
    全部仍是綠的——那正是 `merge-blockers.md` 第 22 項 (a) 指出的缺口。

    本類別把兩個函式**照 `MemoryFacade.search` 的組合方式**串起來
    （`rank_candidates(memory_service.scored_candidates(pairs))`，
    `memory_facade.py` 的檢索路徑），餵入真實的距離值，斷言的是**距離**的順序
    而不是分數的順序——分數是被測對象自己產出的東西，拿它當依據等於循環論證。
    """

    @staticmethod
    def _rank(distance_by_id):
        import services.memory_service as memory_service

        return [
            c.identifier
            for c in rank_candidates(
                memory_service.scored_candidates(_pairs(distance_by_id))
            )
        ]

    def test_closer_candidate_ranks_first(self):
        """三個具體距離：近（0.05）、中（0.6）、遠（1.7）。

        輸入順序刻意打亂成「中、遠、近」，使「照輸入順序回傳」的實作也會紅。
        """
        ranked = self._rank({11: 0.6, 12: 1.7, 13: 0.05})
        self.assertEqual(
            ranked,
            ["13", "11", "12"],
            "距離越小越相似，必須排在越前面；順序反過來代表取負號不見了",
        )

    @given(st.dictionaries(st.integers(min_value=1, max_value=10_000), distances, min_size=2, max_size=30))
    @settings(max_examples=200, deadline=None)
    def test_ranking_is_non_decreasing_in_distance(self, distance_by_id):
        """**性質**：經 `scored_candidates` 後的排序結果，距離序列非遞減。

        以排序後的識別字**回查原始距離**再比較，依據的是輸入而非被測函式的
        輸出。同距離者的相對順序由次級鍵決定，與本性質無關（`<=` 而非 `<`）。
        """
        ranked = self._rank(distance_by_id)
        ordered = [distance_by_id[int(identifier)] for identifier in ranked]
        for nearer, farther in zip(ordered, ordered[1:]):
            self.assertLessEqual(nearer, farther)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
