"""
membership_selection.py — `select_successor`：自動改選的挑選規則（**純函式**）

**本模組刻意只有一個函式，而且刻意是獨立的一支檔案。**

`BR4.1` 要求 `select_successor` 是純函式、不讀 DB。那不是風格偏好：違反它會讓
ADR-0006 的 **property-based testing hard constraint 失去作用對象**
——`hypothesis` 無法對一個需要資料庫 session 的函式生成輸入。而 PBT 在本單元是
**blocking 而非 N/A**（前三個單元都是 DDL、沒有任何函式，本單元有，且上游已經
點名了哪一個：`unit-of-work.md:448`、`K-16` 的 `select_successor`）。

把它放進自己的模組，使「純」這件事成為**可機械檢查**的事實而非宣稱——
以 `ast` 解析本檔，import 集合**恰為三項**：`__future__`、`typing`、
`services.membership_types`。`sqlalchemy`／`Session`／`httpx`／`HTTPException`
在**程式行**（docstring 與註解除外）的命中數皆為 **0**。
（注意：對本檔跑裸 `grep` 會各命中一次——就是上面這段散文自己。
量測純度要看 import 集合與程式行，不是整個檔案的字串命中。）
形狀與 `team.md` 對 cost 功能域立下的同一條結構前提一致
（`scripts/validate_cost_calculator_boundary.py` 守的是同一件事）。

**可失敗的性質是排列不變性**，不是「同一組輸入選出同一人」——後者對純函式
恆真，是恆真斷言（`project.md` 記過那個形狀）。
"""

from __future__ import annotations

from typing import Sequence

from services.membership_types import MemberSnapshot


def select_successor(members: Sequence[MemberSnapshot]) -> MemberSnapshot:
    """挑選自動改選的接手人：**最早加入者**，平手時以 `user_id` 決定性 tie-break。

    `BR4.2`：排序鍵為 `(joined_at, user_id)`，取最小者。形狀沿用 repo 既有的
    `best_clouds`（`backend/cost/estimate_readers.py:247-251`，
    `key=lambda item: (-item[1], item[0])`）——同一個「把 tie-break 欄位放進
    排序鍵」的手法。

    **`user_id` 進入排序鍵是 `AC12.4.2` 的全部理由**：只以 `joined_at` 排序時，
    兩位成員的加入時間完全相同就**沒有穩定順序**——結果取決於資料庫回傳順序，
    每次改選可能選出不同人，而這是**靜默的**：沒有錯誤，只有不穩定的結果。

    純度（`BR4.1`）：不讀 DB、不連外、不讀任何模組級狀態、不就地修改輸入。

    前置條件：`members` 非空，且其 `joined_at` 的**時區感知性一致**
    （全部 aware 或全部 naive）。唯一的呼叫端把同一次查詢的列轉成 snapshot，
    故該前提自然成立；混用 aware 與 naive 會由 Python 的比較本身 raise
    `TypeError`，而那是**大聲失敗**，比靜默挑錯人好。

    Raises:
        ValueError: `members` 為空。空集合沒有接手人可選，而呼叫端的冪等檢查
            （`BR4.3`）本來就該在這之前擋下——所以這裡大聲失敗而非回 `None`，
            回 `None` 會把一個邏輯錯誤變成一個要在下游解包的 Optional。
    """
    if not members:
        raise ValueError(
            "select_successor 不接受空成員集合：自動改選的呼叫端須先確認"
            "該專案另有成員（BR4.4），冪等檢查（BR4.3）也在這之前"
        )
    return min(members, key=lambda snapshot: (snapshot.joined_at, snapshot.user_id))


__all__ = ["select_successor"]
