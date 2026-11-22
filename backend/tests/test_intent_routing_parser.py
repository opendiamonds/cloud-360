"""`U11 intent-router` 的 **L4 解析層**測試：扁平 → 兩層 ＋ `V-1`～`V-5`。

本檔對應 `unit-test-instructions.md §三` 的第二列。**零 mock**——L4 是純函式，
給輸入驗輸出。

## 為什麼解析層需要自己的一組測試

`[D1]`=A 把兩層的還原放在**我方**（模型只回扁平陣列 ＋ `slot` 索引），
所以**驗證也在我方**。該選項的代價寫得很清楚：「`EC6`（槽位與候選是兩個軸）
在線上形狀裡變成一個慣例（`slot` 欄位）而不是型別。分組邏輯與其驗證
（`slot` 必須從 0 連續、每組至少一個候選）落在我們的解析層，**要有自己的
測試**。」本檔即是那組測試。

## `V-5` 與前四者的差別必須被測出來

`V-1`～`V-4` 是**失敗**，`V-5` 是**降級**。那個差別是 `[IR1]`=A 的設計收益：
模型只給部分分數時系統不壞，只是走無分數分支（`BR3.3`）。一個把 `V-5` 也
寫成失敗的實作會通過「畸形輸入要拋例外」這種籠統的測試，而它會讓一個
**可用**的回應被丟掉。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import unittest

from services.intent_routing_errors import EmptyCandidates, MalformedRouting
from services.intent_routing_parser import parse_classification
from services.intent_routing_types import (
    MAX_SLOTS,
    REFERENT_ABSENT,
    REFERENT_RESOLVED,
    REFERENT_UNRESOLVED,
)


def candidate(
    slot,
    rank,
    capability="architecture-design",
    label="改架構圖",
    tied_with_next=False,
    score=0.9,
    referent_state=REFERENT_ABSENT,
    referent=None,
):
    return {
        "slot": slot,
        "rank": rank,
        "capability": capability,
        "label": label,
        "tied_with_next": tied_with_next,
        "score": score,
        "referent_state": referent_state,
        "referent": referent,
    }


def payload(candidates, slot_labels=None):
    if slot_labels is None:
        count = len({c["slot"] for c in candidates}) or 1
        slot_labels = [f"第 {i} 件事" for i in range(count)]
    return {"candidates": candidates, "slot_labels": slot_labels}


class HappyPathTest(unittest.TestCase):
    def test_two_slots_of_two_candidates_restore_into_two_rankings(self):
        """`FR5.1` 的官方可測不變量：「改架構圖加 Redis 快取，然後估一下成本
        差額」應產生 **2 個**槽位——而**同一槽位內**的兩個候選是互斥的讀法。

        這兩個軸的區別是 `EC6`，也是 `functional-design` 審查 `R-01` 的全部
        重點。本測試斷言分組正確（2 × 2），而不是「總共拿到 4 個候選」。
        """
        result = parse_classification(
            payload(
                [
                    candidate(0, 1, label="改架構圖：加 Redis", score=0.91),
                    candidate(
                        0,
                        2,
                        capability="well-architected-review",
                        label="評核快取設計",
                        score=0.4,
                    ),
                    candidate(
                        1,
                        1,
                        capability="cost-finops",
                        label="估成本差額",
                        score=0.88,
                    ),
                    candidate(
                        1,
                        2,
                        capability="architecture-design",
                        label="畫成本比較圖",
                        score=0.2,
                    ),
                ],
                slot_labels=["改架構圖", "估成本差額"],
            )
        )
        self.assertEqual(len(result.slots), 2)
        self.assertEqual([len(s.candidates) for s in result.slots], [2, 2])
        self.assertEqual(result.slot_labels, ("改架構圖", "估成本差額"))
        self.assertTrue(result.scores_available)
        self.assertEqual(
            [c.rank for c in result.slots[0].candidates], [1, 2]
        )
        self.assertEqual(result.slots[1].candidates[0].capability, "cost-finops")

    def test_rank_order_is_restored_even_when_the_payload_is_shuffled(self):
        """模型沒有義務按順序吐——`rank` 是真實來源，陣列位置不是。

        `BR2.2` 要求 `candidates` 依 `rank` **遞增**排序，而 `BR3.2`／`BR3.3`
        的述詞讀的是 `candidates[0]`。若解析層沿用陣列順序，一個亂序的回應會
        讓述詞拿第二名去比門檻——而那不會拋任何例外。
        """
        result = parse_classification(
            payload(
                [
                    candidate(0, 3, label="第三", score=0.1),
                    candidate(0, 1, label="第一", score=0.9),
                    candidate(0, 2, label="第二", score=0.5),
                ]
            )
        )
        self.assertEqual(
            [c.label for c in result.slots[0].candidates], ["第一", "第二", "第三"]
        )

    def test_resolved_referent_is_carried_through(self):
        """`EC3`：三種 `referent_state` 都要能表達，而 `resolved` 必須帶值。"""
        result = parse_classification(
            payload(
                [
                    candidate(
                        0,
                        1,
                        referent_state=REFERENT_RESOLVED,
                        referent="訂單系統架構圖",
                    )
                ]
            )
        )
        top = result.slots[0].candidates[0]
        self.assertEqual(top.referent_state, REFERENT_RESOLVED)
        self.assertEqual(top.referent, "訂單系統架構圖")


class V1EmptyCandidatesTest(unittest.TestCase):
    def test_an_empty_list_is_a_failure_not_a_clarify(self):
        """`V-1`／`BR2.4`：空清單是**失敗**，不是「判不出來」。

        把失敗當成反問，會讓一個壞掉的分類器看起來像在謹慎發問——而
        `functional-spec.md` §二 的狀態機逐字要求 `failed` 與 `clarifying`
        不得共用出口。
        """
        with self.assertRaises(EmptyCandidates):
            parse_classification({"candidates": [], "slot_labels": []})

    def test_a_missing_candidates_key_is_malformed_not_empty(self):
        """**界線**：缺鍵是 `MalformedRouting`，存在但為空才是 `EmptyCandidates`。

        兩者混計會污染 `NFR3.74` 的分型失敗率——「供應商吐出壞掉的 JSON」與
        「供應商真的說它找不到候選」是兩件不同的事，而分型是本單元設計的主軸。
        """
        with self.assertRaises(MalformedRouting):
            parse_classification({"slot_labels": []})


class V2CapabilityEnumTest(unittest.TestCase):
    def test_a_capability_outside_the_closed_enum_is_malformed(self):
        """`V-2`／`BR2.2`：`capability` 的值域**不由本單元發明**。

        一個放行未知 `capability` 的解析層會把一個模型幻想出來的能力名交給
        `U12`，而 `U12` 找不到對應的能力——失敗點會離原因很遠。
        """
        with self.assertRaises(MalformedRouting):
            parse_classification(
                payload([candidate(0, 1, capability="database-migration")])
            )


class V3SlotIndexTest(unittest.TestCase):
    def test_non_contiguous_slots_are_malformed(self):
        """`V-3`：`slot` 必須自 **0 連續**。

        跳號代表模型心裡的槽位數與它實際吐出的不一致，而補齊（插一個空槽位）
        或重編號都是靜默修補。
        """
        with self.assertRaises(MalformedRouting):
            parse_classification(
                payload(
                    [candidate(0, 1), candidate(2, 1)],
                    slot_labels=["a", "b"],
                )
            )

    def test_exceeding_the_slot_upper_bound_fails_and_is_not_truncated(self):
        """`V-3`：超界即失敗，**不截斷**。

        截斷會靜默丟掉意圖——正是 `functional-design` 審查 `R-01` 查出的那個
        失敗模式。另：失敗型別是 `MalformedRouting` 而**不是** `BR2.4`
        （`performance-design.md` 修訂 1／審查 `R-04` 的更正）。

        **上界 4 本身是暫定值**（`D-7`），覆核工具是 `NFR3.73` 的槽位數分佈；
        本測試驗的是「超界的處置」而不是「4 這個數字對不對」。
        """
        over = MAX_SLOTS + 1
        with self.assertRaises(MalformedRouting):
            parse_classification(
                payload(
                    [candidate(i, 1) for i in range(over)],
                    slot_labels=[f"a{i}" for i in range(over)],
                )
            )

    def test_a_boolean_slot_is_malformed(self):
        """`True` 是 `int` 的實例——不明文排除，`slot: true` 會被當成 `slot 1`。"""
        with self.assertRaises(MalformedRouting):
            parse_classification(
                payload([candidate(0, 1), candidate(True, 1)], slot_labels=["a", "b"])
            )


class V4RankWithinASlotTest(unittest.TestCase):
    def test_duplicate_ranks_inside_one_slot_are_malformed(self):
        """`V-4`：組內 `rank` 自 1 連續且**唯一**。

        重複的 `rank` 1 讓「哪一個是第一名」無定義，而述詞讀的就是第一名。
        """
        with self.assertRaises(MalformedRouting):
            parse_classification(payload([candidate(0, 1), candidate(0, 1)]))

    def test_ranks_not_starting_at_one_are_malformed(self):
        with self.assertRaises(MalformedRouting):
            parse_classification(payload([candidate(0, 2), candidate(0, 3)]))

    def test_a_missing_tie_flag_is_malformed(self):
        """`tied_with_next` **必須存在**，缺它時不能取預設值。

        「預設不並列」會讓無分數時述詞退化成永遠可單選，`FR1.3` 於是靜默永不
        觸發；「預設並列」則讓系統永遠反問。**兩個預設都是壞的**，所以它是
        required 欄位。
        """
        broken = candidate(0, 1)
        del broken["tied_with_next"]
        with self.assertRaises(MalformedRouting):
            parse_classification(payload([broken]))


    def test_a_missing_referent_state_is_malformed(self):
        """`R-05`：`referent_state` 缺值即 `MalformedRouting`，與 `tied_with_next` 同形。

        schema 把它列為 required，而**模型不保證遵守 schema**。靜默取 `absent`
        會把「模型漏填」與「這句話沒有指涉詞」合併成同一件事——而那正是 `EC3`
        要分開的兩種情況，且合併的方向恰好是**較不安全**的那一邊：`absent`
        不觸發反問，`unresolved` 會（`BR5.2`／`AC6.1.2`）。一個漏填的回應於是
        會被當成「這句話沒有指涉詞」而照常交辦。

        同一份檔對兩個 required 欄位採不一致的嚴格度，而兩者的失敗形狀相同
        ——這是審查 `R-05` 的原文。
        """
        broken = candidate(0, 1)
        del broken["referent_state"]
        with self.assertRaises(MalformedRouting):
            parse_classification(payload([broken]))

    def test_an_explicit_absent_is_still_accepted(self):
        """反向斷言：**明寫** `absent` 仍是完全正常的輸入。

        只驗「缺值被擋」時，一個把 `absent` 也一併拒絕的實作也會通過，而那
        會讓每一句不帶指涉詞的輸入（「幫我畫一張架構圖」）都解析失敗。
        """
        result = parse_classification(
            payload([candidate(0, 1, referent_state=REFERENT_ABSENT)])
        )
        self.assertEqual(
            result.slots[0].candidates[0].referent_state, REFERENT_ABSENT
        )
        self.assertIsNone(result.slots[0].candidates[0].referent)


class V5PartialScoresDegradeTest(unittest.TestCase):
    def test_partial_scores_degrade_the_whole_list_instead_of_failing(self):
        """`V-5`：**這一條不是失敗，是降級**（`EC2`／`BR2.5`）。

        對混合清單只拿有分數的那幾個比門檻，會讓判定依賴「模型當下給了幾個
        分數」。整張清單視為無分數後，述詞走 `BR3.3` 分支——系統不壞。

        **它與前四者的差別是 `[IR1]`=A 的設計收益**，故本測試同時斷言
        「沒有拋例外」與「分數真的被整批清掉」兩件事。
        """
        result = parse_classification(
            payload(
                [
                    candidate(0, 1, score=0.95),
                    candidate(0, 2, score=None),
                    candidate(1, 1, capability="cost-finops", score=0.8),
                ],
                slot_labels=["改圖", "估成本"],
            )
        )
        self.assertFalse(result.scores_available)
        for slot in result.slots:
            for c in slot.candidates:
                self.assertIsNone(c.score)

    def test_a_score_outside_zero_to_one_is_malformed(self):
        """定義域 0–1（`entities.md` 的 `min`／`max`）。1.4 分不是「很有信心」，
        它是一個壞掉的回應——而它會讓門檻比較失去意義。
        """
        with self.assertRaises(MalformedRouting):
            parse_classification(payload([candidate(0, 1, score=1.4)]))


class SlotLabelsTest(unittest.TestCase):
    def test_slot_labels_must_be_the_same_length_as_the_slots(self):
        """`slot_labels` 不是裝飾欄位：它是 `EC8` 候選出處**唯一**的來源。

        `K-10` 的 `ClarifyCandidate` 沒有槽位欄位（本單元無權加），所以多槽位
        反問時長度不符就等於有一件事說不出名字。
        """
        with self.assertRaises(MalformedRouting):
            parse_classification(
                payload([candidate(0, 1), candidate(1, 1)], slot_labels=["只有一個"])
            )

    def test_an_unresolved_referent_must_not_carry_a_value(self):
        """`EC3` 的一致性：狀態說「解析不出來」卻帶了值，是自相矛盾的回應。

        放行它會讓 `AC6.1.2` 的觸發條件（指涉詞無法判定 ⇒ 反問）在資料層
        變得無法信任。
        """
        with self.assertRaises(MalformedRouting):
            parse_classification(
                payload(
                    [
                        candidate(
                            0,
                            1,
                            referent_state=REFERENT_UNRESOLVED,
                            referent="訂單系統",
                        )
                    ]
                )
            )


if __name__ == "__main__":
    unittest.main()
