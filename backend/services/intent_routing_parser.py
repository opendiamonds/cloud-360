"""intent_routing_parser.py — `U11 intent-router` 的 **L4**：扁平 → 兩層 ＋ 五道驗證

**契約（同進程呼叫端依賴，請勿變更）**

`[D1]`=A 決定模型回應是**扁平的 `candidates` 陣列 ＋ `slot` 整數索引**
（外加平行的 `slot_labels`），**兩層的還原在我方**。所以**驗證也在我方**。

硬約束
------

- **純函式**：零 I/O、零網路、零 DB。輸入是一個已解析的 mapping，輸出是
  `ClassificationResult` 或一個具名例外。
- **不截斷、不補齊。** 槽位結構錯了就是失敗——靜默修補正是
  `functional-design` 審查 `R-01` 查出的那個失敗模式（「`intents` 少了一個」
  完全通過原本的規則字面）。

五道驗證（`reliability-design.md` §二）
--------------------------------------

| # | 驗證 | 違反時 |
|---|---|---|
| `V-1` | `candidates` 非空 | `EmptyCandidates`（`BR2.4`） |
| `V-2` | 每個 `capability` 在封閉列舉內 | `MalformedRouting`（`BR2.2`） |
| `V-3` | `slot` 自 **0 連續**、最大值 ≤ `MAX_SLOT_INDEX` | `MalformedRouting` |
| `V-4` | 每個 slot 分組至少一個候選；組內 `rank` 自 1 連續且唯一 | `MalformedRouting` |
| `V-5` | `score` 全有或全無（**跨整張清單，非每組**） | **不是失敗**——整張清單視為無分數（`EC2`），降級到 `BR3.3` 分支 |

**`V-5` 刻意不是失敗**，這是 `[IR1]`=A 的設計收益：模型只給部分分數時系統
不壞，只是走無分數分支。**`V-3` 與 `V-4` 則必須是失敗**——它們壞掉代表槽位
結構錯了。

`EC8` **不在**這五道的射程內
---------------------------

V-1～V-5 全部作用於「解析 Jev 回應」這一步，而 `EC8` 約束的是**輸出構造**
（攤平時 `label` 要帶出處），落點是 L5（`intent_routing_predicate`）。
原設計曾宣稱「五道驗證缺一則 `EC6`–`EC8` 不成立」，那是過度宣稱
（`nfr-design` 審查 `R-06`）。

`EmptyCandidates` 與 `MalformedRouting` 的界線
---------------------------------------------

`candidates` **存在但為空** → `EmptyCandidates`（`BR2.4` 逐字「分類器回空
候選清單」）。`candidates` **缺鍵或不是陣列** → `MalformedRouting`
（`reliability-design.md` §一 逐字把「JSON 不合」歸在此）。兩者混計會污染
`NFR3.74` 的分型失敗率，而分型是本單元設計的主軸之一。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Final, Mapping, Optional, Sequence, Tuple

from services.intent_routing_errors import EmptyCandidates, MalformedRouting
from services.intent_routing_types import (
    MAX_CANDIDATES_PER_SLOT,
    MAX_SLOTS,
    MAX_SLOT_INDEX,
    REFERENT_RESOLVED,
    REFERENT_STATES,
    ROUTABLE_CAPABILITIES,
    CandidateIntent,
    CandidateRanking,
    ClassificationResult,
)

CANDIDATES_KEY: Final = "candidates"
SLOT_LABELS_KEY: Final = "slot_labels"


def _reject(reason: str) -> None:
    raise MalformedRouting(f"路由回應不合 schema：{reason}")


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _require_int(value: Any, field: str, position: int) -> int:
    """`bool` 是 `int` 的子型別，故必須明文排除——`True` 當成 `slot 1` 會過。"""
    if isinstance(value, bool) or not isinstance(value, int):
        _reject(f"候選 #{position} 的 {field} 必須是整數，收到 {value!r}")
    return int(value)


def _require_text(value: Any, field: str, position: int) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject(f"候選 #{position} 的 {field} 必須是非空字串，收到 {value!r}")
    return value.strip()


def _require_bool(value: Any, field: str, position: int) -> bool:
    """`tied_with_next` **必須存在**，而缺它時不能取一個預設值。

    「預設不並列」會讓無分數時述詞退化成永遠可單選，`FR1.3` 於是靜默永不
    觸發（`FR1.6` 逐字警告的後果）；「預設並列」則讓系統永遠反問。兩個預設
    都是壞的，所以它是 schema 的 required 欄位，缺值即 `MalformedRouting`。
    """
    if not isinstance(value, bool):
        _reject(f"候選 #{position} 的 {field} 必須是布林值，收到 {value!r}")
    return bool(value)


def _optional_score(value: Any, position: int) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _reject(f"候選 #{position} 的 score 必須是數字或 null，收到 {value!r}")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        _reject(f"候選 #{position} 的 score 必須落在 0–1，收到 {score}")
    return score


def _referent_pair(raw: Mapping[str, Any], position: int) -> Tuple[str, Optional[str]]:
    """`EC3`／`BR5.4`：「沒有指涉詞」與「有指涉詞但解析不出來」必須可區分。

    兩者都用 `None` 表達會讓 `AC6.1.2`（「指涉詞無法判定指哪一個 ⇒ 走反問
    路徑」）的觸發條件**不可構造**。本解析層因此要求 schema 明文帶一個狀態
    欄位，並檢查它與 `referent` 的值**互相一致**——狀態說解析成功卻沒有值，
    或狀態說沒有指涉詞卻帶了值，都是模型回了自相矛盾的輸出。

    **缺鍵即 `MalformedRouting`，與 `tied_with_next` 同形**：schema 把它列為
    required，而模型不保證遵守 schema。靜默取 `absent` 會把「模型漏填」與
    「這句話沒有指涉詞」合併成同一件事——而那正是 `EC3` 要分開的兩種情況，
    且合併的方向恰好是**較不安全**的那一邊（`absent` 不觸發反問，
    `unresolved` 會）。一個漏填 `referent_state` 的回應於是會被當成「這句話
    沒有指涉詞」而照常交辦。
    """
    if "referent_state" not in raw:
        _reject(
            f"候選 #{position} 缺少 referent_state（schema 的 required 欄位）。"
            "它刻意沒有預設值：靜默取 absent 會讓「模型漏填」與「這句話沒有"
            "指涉詞」合併，而後者不觸發反問（EC3／BR5.2）。"
        )
    state = raw.get("referent_state")
    if state not in REFERENT_STATES:
        _reject(
            f"候選 #{position} 的 referent_state 必須取自 {REFERENT_STATES}，"
            f"收到 {state!r}"
        )
    referent = raw.get("referent")
    if referent is not None and not isinstance(referent, str):
        _reject(f"候選 #{position} 的 referent 必須是字串或 null，收到 {referent!r}")
    cleaned = referent.strip() if isinstance(referent, str) else None
    if state == REFERENT_RESOLVED:
        if not cleaned:
            _reject(f"候選 #{position} 宣告 referent 已解析，但沒有給值")
        return state, cleaned
    if cleaned:
        _reject(
            f"候選 #{position} 的 referent_state 為 {state!r} 卻帶了值 {cleaned!r}"
        )
    return state, None


def parse_classification(payload: Any) -> ClassificationResult:
    """把一次 tool call 的回應還原成**兩層**的 `ClassificationResult`。

    順序是刻意的：先確認形狀（`MalformedRouting`），再判空（`EmptyCandidates`）
    ——一個缺 `candidates` 鍵的回應不是「分類器說它判不出來」，它是壞掉的
    回應，而兩者在 `NFR3.74` 的曲線上必須分得開。
    """
    if not isinstance(payload, Mapping):
        _reject(f"回應必須是物件，收到 {type(payload).__name__}")

    raw_candidates = payload.get(CANDIDATES_KEY)
    if not _is_sequence(raw_candidates):
        _reject(f"缺少 {CANDIDATES_KEY} 陣列（收到 {type(raw_candidates).__name__}）")
    if len(raw_candidates) == 0:
        # `V-1`：**存在但為空**才是 `BR2.4` 的「分類器回空候選清單」。
        raise EmptyCandidates(
            "分類器回了空候選清單：這是分類失敗，不是「判不出來」（BR2.4）"
        )

    parsed: list = []
    slots_seen: set = set()
    for position, raw in enumerate(raw_candidates):
        if not isinstance(raw, Mapping):
            _reject(f"候選 #{position} 必須是物件，收到 {type(raw).__name__}")
        slot = _require_int(raw.get("slot"), "slot", position)
        capability = _require_text(raw.get("capability"), "capability", position)
        if capability not in ROUTABLE_CAPABILITIES:  # `V-2`
            _reject(
                f"候選 #{position} 的 capability {capability!r} 不在封閉列舉 "
                f"{ROUTABLE_CAPABILITIES} 內"
            )
        rank = _require_int(raw.get("rank"), "rank", position)
        label = _require_text(raw.get("label"), "label", position)
        tied = _require_bool(raw.get("tied_with_next"), "tied_with_next", position)
        state, referent = _referent_pair(raw, position)
        parsed.append(
            (
                slot,
                CandidateIntent(
                    capability=capability,
                    rank=rank,
                    label=label,
                    tied_with_next=tied,
                    referent_state=state,
                    referent=referent,
                    score=_optional_score(raw.get("score"), position),
                ),
            )
        )
        slots_seen.add(slot)

    # `V-3`：`slot` 自 0 連續，且槽位數不超過上界。**超界即失敗，不截斷**
    # ——截斷會靜默丟掉意圖。失敗型別是 `MalformedRouting` 而**不是**
    # `BR2.4`（後者逐字只講空清單；混計會污染 `NFR3.74` 的分型）。
    slot_count = len(slots_seen)
    if slots_seen != set(range(slot_count)):
        _reject(
            f"slot 必須自 0 連續編號，收到 {sorted(slots_seen)}"
        )
    if slot_count > MAX_SLOTS:
        _reject(
            f"槽位數 {slot_count} 超過上界 {MAX_SLOTS}"
            f"（slot 最大值須 ≤ {MAX_SLOT_INDEX}）"
        )

    # `V-5`：跨**整張清單**的全有或全無。部分帶分數時整張清單視為無分數
    # ——**降級，不是失敗**（`EC2`／`BR2.5`）。對混合清單只拿有分數的那幾個
    # 比門檻，會讓判定依賴模型當下給了幾個分數。
    scores_complete = all(candidate.score is not None for _, candidate in parsed)
    if not scores_complete:
        parsed = [
            (slot, replace(candidate, score=None))
            for slot, candidate in parsed
        ]

    grouped: list = []
    for index in range(slot_count):
        members = [candidate for slot, candidate in parsed if slot == index]
        # `V-4`：每個分組至少一個候選，組內 `rank` 自 1 連續且唯一。
        if not members:
            _reject(f"slot {index} 沒有任何候選")
        if len(members) > MAX_CANDIDATES_PER_SLOT:
            _reject(
                f"slot {index} 的候選數 {len(members)} 超過上界 "
                f"{MAX_CANDIDATES_PER_SLOT}"
            )
        ranks = sorted(candidate.rank for candidate in members)
        if ranks != list(range(1, len(members) + 1)):
            _reject(f"slot {index} 的 rank 必須自 1 連續且唯一，收到 {ranks}")
        members.sort(key=lambda candidate: candidate.rank)
        grouped.append(CandidateRanking(candidates=tuple(members)))

    slot_labels = _parse_slot_labels(payload.get(SLOT_LABELS_KEY), slot_count)
    return ClassificationResult(slots=tuple(grouped), slot_labels=slot_labels)


def _parse_slot_labels(raw: Any, slot_count: int) -> Tuple[str, ...]:
    """`slot_labels` 與 `slots` **必須等長**。

    它不是裝飾性的欄位：`EC8` 要求攤平後的 `ClarifyCandidate.label` 寫出它
    屬於哪一件事，而 `K-10` 的 `ClarifyCandidate` 沒有槽位欄位——`slot_labels`
    是那個資訊**唯一**的來源。長度不符就等於多槽位反問時有一件事說不出名字，
    故它是 `MalformedRouting` 而不是一個可以忽略的缺漏。
    """
    if not _is_sequence(raw):
        _reject(
            f"缺少 {SLOT_LABELS_KEY} 陣列（收到 {type(raw).__name__}）；"
            "EC8 的候選出處沒有它就無從附加"
        )
    if len(raw) != slot_count:
        _reject(
            f"{SLOT_LABELS_KEY} 有 {len(raw)} 筆，但槽位數是 {slot_count}，必須等長"
        )
    labels = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or not value.strip():
            _reject(f"{SLOT_LABELS_KEY}[{index}] 必須是非空字串，收到 {value!r}")
        labels.append(value.strip())
    return tuple(labels)


__all__ = [
    "CANDIDATES_KEY",
    "SLOT_LABELS_KEY",
    "parse_classification",
]
