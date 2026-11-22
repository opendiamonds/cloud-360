"""
memory_ranking.py — `rank_candidates`：同分時的決定性次級排序鍵（**純函式**）

**本模組刻意只有一個函式，而且刻意是獨立的一支檔案。**

`NFR3.24` 要求相似度排序在**分數相同**時有決定性的次級排序鍵。
`logical-components.md §1.1` 逐字把「`memory_ranking` 不讀 DB、不拋
`HTTPException`」列為**結構前提而非風格偏好**，理由逐字是違反它
「**property-based 測試就寫不下去**」——`hypothesis` 無法對一個需要資料庫
session 的函式生成輸入。

把它放進自己的模組，使「純」這件事成為**可機械檢查**的事實而非宣稱。
形狀沿用 `services/membership_selection.py`（`U19` 的 `select_successor`）。

**量測純度要看 import 集合與程式行，不是整個檔案的字串命中。**
`membership_selection.py` 的檔頭逐字記下了這個陷阱，而它同樣適用於本檔：
上面這段散文自己就提到了 `HTTPException` 與 session，對本檔跑裸 `grep`
會命中它們。故 `test_memory_contract.py` 以 `ast` 解析 import 集合
（本檔恰為兩項：`__future__`、`typing`），而非字串比對。

## `NFR3.24` 為什麼是正確性而不是效能

`nfr-requirements/performance-requirements.md §1.1` 逐字「`NFR3.24` 本質是
正確性而非效能，列在本檔是因為它屬排序行為」。

沒有次級排序鍵時，兩筆同分的記憶**沒有穩定順序**——結果取決於資料庫回傳
順序，同一個查詢連續兩次可能回不同的順序，而這是**靜默的**：沒有錯誤，
只有不穩定的結果。`U19` 的 `select_successor` 踩的是同一個洞
（`AC12.4.2` 的「每次改選可能選出不同人」）。
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

_Candidate = TypeVar("_Candidate")


def rank_candidates(candidates: Sequence[_Candidate]) -> List[_Candidate]:
    """依 `(-score, identifier)` 排序：分數遞減為主鍵，同分時識別字遞增。

    形狀沿用 repo 既有的 `best_clouds`
    （`backend/cost/estimate_readers.py:247-251`，
    `key=lambda item: (-item[1], item[0])`）——同一個「把 tie-break 欄位放進
    排序鍵」的手法，而不是排序兩次或在排序後重排同分組。

    Args:
        candidates: 具 `identifier: str` 與 `score: float` 兩個屬性的元素序列。
            正常呼叫端傳的是 `memory_types.ScoredCandidate`；型別參數使本函式
            不依賴那個 dataclass，故 `memory_types` **不**出現在本模組的
            import 集合裡（純度檢查的射程因此不需要為它開例外）。

    Returns:
        **新的** list，依上述鍵遞增排序。輸入不被就地修改。

    純度（`logical-components.md §1.1`）：不讀 DB、不連外、不讀任何模組級狀態、
    不就地修改輸入、不拋 `HTTPException`。

    ## 可失敗的性質是**排列不變性**

    「同一組輸入連續兩次回相同順序」對任何純函式都恆真，是恆真斷言
    （`project.md` 記過那個形狀）。真正會失敗的性質是：**同一個集合的任意
    排列，排序結果完全相同**。少了 `identifier` 這個次級鍵時，
    `sorted` 的穩定性會讓結果跟著輸入順序走，該性質隨即失敗。

    ## `-score` 而不是 `reverse=True`

    `reverse=True` 會把**兩個**鍵都反轉，使同分時識別字變成**遞減**。
    那仍然是決定性的，所以 `NFR3.24` 字面上仍然滿足——但它與
    `unit-test-instructions.md §4.2` 的第 3 條性質（「同分時以識別字遞增」）
    相反，而那條性質是本單元唯一能看出次級鍵方向的斷言。

    浮點數的兩個邊界已查證，兩者都不破壞排列不變性：

    - `-0.0 == 0.0` 為真，故兩者視為同分並落到識別字比較（鍵仍是全序）。
    - `±inf` 可排序；`NaN` **不可**（任何與 NaN 的比較皆為偽，鍵不再是全序，
      排列不變性會無意義地失敗）。故測試的生成策略以
      `allow_nan=False` 排除它，而向量相似度不會產生 NaN。
    """
    return sorted(candidates, key=lambda c: (-c.score, c.identifier))


__all__ = ["rank_candidates"]
