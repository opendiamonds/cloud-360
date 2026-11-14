"""session_types.py — `U10 session-store` 的純資料形狀

**契約（同進程呼叫端依賴，請勿變更）**

本檔是 `entities.md` 三個實體（`BrainSession`／`ConversationSegment`／
`SessionMessage`）在程式層的落點，以及單一 Redis Hash 的欄位編碼。

硬約束：

- **零 I/O、零 Redis import、零 DB import。** 本檔是 property-based 測試的落點
  （`BR3.4` 的修剪語意），而 PBT 的前提是被測對象是純函式。
- `BR5.2`：本檔不 import 任何 request／websocket 型別。
- `BR3.6`：本檔的 `__repr__` 會含訊息文字（dataclass 預設），故**呼叫端不得把
  本檔的任何物件交給 logger**。白名單建構函式在 `redis_gateway.py`，它是唯一
  被允許組日誌欄位的地方。

## ⚠ `trim_history` 不是生產載體

`trim_history()` 是 `BR3.4` 的**參考實作**，存在的唯一目的是給 property-based
測試一個純函式標的。**生產環境的修剪在 `session_scripts/append_message.lua`
裡，Python 端一行都不跑。**

`performance-design.md §Lua 腳本的職責邊界` 逐字：「`BR3.4` 的修剪語意只能有
一個載體。Python 端**不得**另外實作一次修剪——兩份實作遲早分歧，而分歧的徵兆
是『筆數偶爾是 201』這種沒人會注意的東西。」

本檔保留這個函式，是因為 Lua 無法被 `hypothesis` 驅動；兩者的語意等價由
`test_session_contract.py` 以「Lua 是唯一生產載體」的靜態斷言 ＋ 替身以本函式
模擬腳本效果共同維持。**這是一個如實記載的取捨，不是雙份實作。**

## Hash 欄位的命名空間（`OPEN-N10-7`）

| 欄位 | 內容 |
|---|---|
| `seg:<segmentId>` | 該段的訊息陣列（JSON）。**欄位不存在即該段未建立**（`EC3`／`BR2.4`） |
| `tgt:<segmentId>` | 該段的三層作業對象（JSON，允許 `null`，`EC7`） |
| `meta` | `userId`、`pageModes`、各段 `createdAt`（`NFR4.56` 的 `pageModes` 刻意放這裡，使 `HGETALL` 一次帶回） |

`U12 work-orchestrator` 的工作項集合共用同一個 key，**其欄位名不得與以上三個
前綴衝突**（`OPEN-N10-7`，承接 `U12`）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

# ---------------------------------------------------------------------------
# 封閉集合（`EC2`／`EC4`／`BR2.1`／`BR2.8`）
# ---------------------------------------------------------------------------

#: 三處共享工作階段的那一段（`EC1`：永遠存在）。
SEGMENT_SHARED = "shared"
SEGMENT_WORKSPACE = "workspace"
SEGMENT_ASSESSMENT = "assessment"

#: `EC4`：段識別的**封閉**值域。段識別就是擁有它的頁面（共享段除外），故不需要
#: 額外的識別碼產生器，也使「重入同一段」（`[S2]`=A）由構造成立。
SEGMENT_IDS = (SEGMENT_SHARED, SEGMENT_WORKSPACE, SEGMENT_ASSESSMENT)

#: `EC2`：`pageModes` 的鍵集合**恰為**這兩頁，**不含入口頁**——`FR3.1` 逐字只
#: 允許 `/workspace` 與 `/assessment` 開啟獨立對話，入口頁恆讀共享段
#: （`BR2.2`）。`/cost` 與 `/admin/*` 也不在此（`BR2.8`）。
PAGE_SCOPES = (SEGMENT_WORKSPACE, SEGMENT_ASSESSMENT)

SHARING_SHARED = "shared"
SHARING_ISOLATED = "isolated"
SHARING_MODES = (SHARING_SHARED, SHARING_ISOLATED)

#: Hash 欄位前綴。
SEGMENT_FIELD_PREFIX = "seg:"
TARGET_FIELD_PREFIX = "tgt:"
META_FIELD = "meta"


def segment_field(segment_id: str) -> str:
    """`seg:<id>`。呼叫端必須先過 `require_segment_id`。"""
    return f"{SEGMENT_FIELD_PREFIX}{segment_id}"


def target_field(segment_id: str) -> str:
    """`tgt:<id>`。呼叫端必須先過 `require_segment_id`。"""
    return f"{TARGET_FIELD_PREFIX}{segment_id}"


# ---------------------------------------------------------------------------
# 驗證（`BR2.1`／`BR2.2`／`BR3.1`）
# ---------------------------------------------------------------------------


def require_segment_id(value: Any) -> str:
    """`BR2.1`：段識別不在封閉集合內即拒絕；**不自動建立未知段**。

    `BR3.1`：`None` 也被拒——「沒有段識別的追加是錯誤，**不得預設為共享段**」。
    預設為共享段正是 `OQ-N4` 逐字指出的兩種壞結果之一。
    """
    if value not in SEGMENT_IDS:
        raise ValueError(
            f"段識別 {value!r} 不在允許集合 {list(SEGMENT_IDS)} 內（BR2.1／BR3.1）"
        )
    return value


def require_page_scope(value: Any) -> str:
    """`BR2.2`／`EC2`：只有 `/workspace` 與 `/assessment` 有共享模式。

    入口頁恆為 `shared`，而「恆為」不是狀態機的一個狀態，是沒有狀態——
    故以入口頁為範圍呼叫 `set_sharing_mode` 一律被拒，不是靜默忽略。
    """
    if value not in PAGE_SCOPES:
        raise ValueError(
            f"頁面範圍 {value!r} 不在允許集合 {list(PAGE_SCOPES)} 內（BR2.2／EC2）："
            "入口頁恆讀共享段且不得切換模式"
        )
    return value


def require_sharing_mode(value: Any) -> str:
    if value not in SHARING_MODES:
        raise ValueError(
            f"共享模式 {value!r} 不在允許集合 {list(SHARING_MODES)} 內"
        )
    return value


# ---------------------------------------------------------------------------
# 實體（`entities.md`）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionMessage:
    """一則訊息。**值物件**——同角色、同內容、同序號者不可區分（`EC10`）。

    `frozen=True` 讓 `EC10` 的「不可就地修改」成為型別層事實：更正一則訊息的
    方式是追加新訊息，不是改寫舊的。能就地改寫會讓 `K-09` 宣告的
    「`append_message` **非冪等**」失去意義。

    `role` 的**值域不在本單元定案**——`K-09.append_message` 逐字 `role: str`
    （未約束），對話協定的擁有者是 `K-02`／`U13`。本檔只要求非空。
    """

    sequence: int
    role: str
    text: str
    created_at: str


@dataclass(frozen=True)
class ConversationSegment:
    """一段對話。由 `BrainSession` 組合擁有；**自己**持有歷程與作業對象。

    三個作業對象欄位**允許部分非空**（`EC7`），包含
    `{projectId: null, systemId: null, diagramId: 非空}`——`OPEN-H11` 的新建
    架構圖從未被指派系統歸屬，而 `hierarchy_service.resolve_work_target`
    刻意不拒絕它。本型別如實儲存部分三元組，**不推導、不補齊、不拒絕**
    （`BR4.5`）。

    `EC8`：本型別**不驗證**三層之間的階層一致性——那是 `U7` 的責任，重驗一次
    會形成兩套可能分歧的規則。
    """

    segment_id: str
    created_at: str
    messages: tuple = ()
    project_id: Optional[int] = None
    system_id: Optional[int] = None
    diagram_id: Optional[int] = None


@dataclass(frozen=True)
class BrainSession:
    """一個使用者的大腦工作階段。彙總根。

    `session_key` 由 `U13` 在握手成功後以已驗證使用者的 id 推導；**本單元不
    產生它，只接收**（`BR1.1`）。

    `expires_at_seconds` 是**剩餘 TTL 秒數**而非絕對時刻——`EC5` 要求它不得由
    呼叫方指定，而剩餘秒數是 Redis 唯一能直接回答的形式（`TTL` 指令）。
    `NFR4.57` 的重啟還原斷言也是對這個值做區間比對。
    """

    session_key: str
    user_id: Optional[int] = None
    page_modes: Mapping[str, str] = field(default_factory=dict)
    segments: Mapping[str, ConversationSegment] = field(default_factory=dict)
    expires_at_seconds: Optional[int] = None

    def segment(self, segment_id: str) -> Optional[ConversationSegment]:
        """`BR3.2`：一個段的讀取視圖**只含該段自己的**訊息。

        段隔離由這個形狀滿足，而不是靠執行期過濾——`AC3.1.2`（獨立段不含共享
        訊息）與 `AC6.1.3`（獨立段無法解析指向共享產出的指涉詞）兩條都是。
        """
        return self.segments.get(require_segment_id(segment_id))


def default_page_modes() -> dict:
    """新 session 的初始模式：兩鍵皆 `shared`（`W1` 第 5 步／`EC2`）。"""
    return {scope: SHARING_SHARED for scope in PAGE_SCOPES}


# ---------------------------------------------------------------------------
# `BR3.4` 修剪的**參考實作**（PBT 標的；**非生產載體**——見檔頭）
# ---------------------------------------------------------------------------


#: 每段**序列化後**的位元組上限（UTF-8 位元組，`merge-blockers.md` 第 18 項）。
#:
#: 與筆數上限（`BRAIN_SESSION_HISTORY_MAX`）**兩個條件取較嚴者**：超過任一個就
#: 從最舊的訊息開始丟，直到兩者都成立。筆數上限單獨無法封住容量——單則訊息可達
#: 4000 字元，3 段 × 200 則 × 4000 個中文字 ≈ 7 MB／session，`maxmemory 256mb`
#: 在最壞情況下約 35 個 session 就滿，而 `noeviction` 之下滿了就是**所有**
#: session 都不能寫。有了本上限，最壞情況是 3 × 200 KB ≈ 600 KB／session。
#:
#: **刻意不做環境變數**（使用者裁決，理由同 `OPEN-ND19-6`）：環境設定契約要求
#: `render-env.sh`、兩份 `.env.example` 與 compose 三處同步，而這個數值沒有
#: 依環境而異的理由。
DEFAULT_SEGMENT_MAX_BYTES = 200 * 1024


def cjson_encoded_size(item: Any) -> int:
    """`item` 經 Redis 內建 lua-cjson `cjson.encode` 之後的**位元組數**。

    生產載體（`append_message.lua`）以 `string.len(cjson.encode(...))` 計算段的
    大小，所以參考實作必須量**同一個東西**，否則兩邊在臨界值附近會丟不同筆數
    ——那正是本檔檔頭「兩份實作遲早分歧」所警告的形狀。

    Python 的 `json.dumps(ensure_ascii=False, separators=(",", ":"))` 與 cjson
    只有兩處長度不同（以 Redis 8.8 實測）：

    * cjson 把 `/` 跳脫成 `\\/`（多 1 位元組）；Python 不跳脫。
    * cjson 把 `0x7f`（DEL）跳脫成 `\\u007f`（6 位元組）；Python 原樣輸出 1 位元組。

    其餘（非 ASCII 原樣輸出 UTF-8、`"`／`\\`／控制字元的跳脫）兩者長度一致。
    鍵的順序不同但不影響長度。本函式的對象是訊息物件（字串與小整數）；超過
    14 位有效數字的整數 cjson 會改用科學記號，不在本函式的對象內。
    """
    text = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
    return len(text.encode("utf-8")) + text.count("/") + 5 * text.count("\x7f")


def segment_size_bytes(messages: Sequence) -> int:
    """整段 JSON 陣列（`[a,b,…]`）的位元組數：括號 2 ＋ 各則 ＋ 逗號 n−1。"""
    sizes = [cjson_encoded_size(item) for item in messages]
    return 2 + sum(sizes) + max(len(sizes) - 1, 0)


def trim_history(
    messages: Sequence, cap: int, max_bytes: int = DEFAULT_SEGMENT_MAX_BYTES
) -> list:
    """把一段的歷程修剪到「≤ `cap` 筆**且** ≤ `max_bytes` 位元組」，**自最舊端
    丟棄**（`BR3.4`；位元組條件為 `merge-blockers.md` 第 18 項）。

    ⚠ **這不是生產載體。** 生產環境的修剪在
    `session_scripts/append_message.lua` 的修剪迴圈。本函式只在兩個地方被呼叫：
    `test_session_types.py` 的 property，以及
    `test_session_store_behaviour.py` 的 in-memory Redis 替身（它以本函式模擬
    腳本效果，見 `unit-test-instructions.md §四`）。

    **`session_store.py` 與 `redis_gateway.py` 都不得呼叫它**——
    `test_session_contract.py` 以 AST 斷言這一點。

    Property（`test_session_types.py`）：

    1. 輸出長度 ≤ `cap`
    2. 輸出是輸入的**後綴**（丟的是最舊的，不是最新的）
    3. 輸入同時在兩個上限內時輸出**等於**輸入（已在上限內時不動）
    4. 輸出整段位元組數 ≤ `max_bytes`，且是**最長**的合格後綴（不多丟）

    **最新的一則永遠保留**：迴圈在剩一則時停止。單則訊息不可能超過 `max_bytes`
    （`session_store.SessionStore` 建構時以算式確認此前提並在不成立時拒絕啟動），
    故這條界線在生產上不會被觸發；它存在是為了讓「段被清空」——cjson 會把空表
    編成 `{}` 而非 `[]`——在任何設定下都不可能發生。

    `cap` 與 `max_bytes` 必須為正整數——`BR3.5` 禁止把「無值」解讀為「無上限」，
    而 `cap <= 0` 會讓整段歷程被清空，那是比無上限更壞的靜默行為。
    """
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
        raise ValueError(f"筆數上限必須是正整數，收到 {cap!r}（BR3.5）")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError(f"位元組上限必須是正整數，收到 {max_bytes!r}")
    items = list(messages)
    sizes = [cjson_encoded_size(item) for item in items]
    total = 2 + sum(sizes) + max(len(sizes) - 1, 0)
    start = 0
    while len(items) - start > 1 and (
        len(items) - start > cap or total > max_bytes
    ):
        total -= sizes[start] + 1
        start += 1
    return items[start:]


# ---------------------------------------------------------------------------
# 序列化：Hash 欄位 ↔ 型別（`Step 3.3`）
# ---------------------------------------------------------------------------


def encode_message(message: SessionMessage) -> dict:
    return {
        "sequence": message.sequence,
        "role": message.role,
        "text": message.text,
        "createdAt": message.created_at,
    }


def decode_message(raw: Mapping[str, Any]) -> SessionMessage:
    return SessionMessage(
        sequence=int(raw["sequence"]),
        role=str(raw["role"]),
        text=str(raw["text"]),
        created_at=str(raw["createdAt"]),
    )


def encode_messages(messages: Sequence) -> str:
    """JSON 陣列。順序**即寫入順序**（`BR3.3`）——陣列有序，故 `NFR4.54` 的
    重啟還原不會因設計而遺漏順序。"""
    return json.dumps(
        [encode_message(m) for m in messages], ensure_ascii=False, separators=(",", ":")
    )


def decode_messages(blob: Optional[str]) -> tuple:
    """欄位不存在（`None`）與空陣列是**不同**的意思：前者是「段未建立」
    （`EC3`），後者是「段存在但還沒有訊息」。本函式對 `None` 回空 tuple，
    段的存在性由呼叫端以欄位是否存在判定，**不是**由歷程長度判定。"""
    if not blob:
        return ()
    return tuple(decode_message(item) for item in json.loads(blob))


def encode_target(
    project_id: Optional[int], system_id: Optional[int], diagram_id: Optional[int]
) -> str:
    """`K-07` 的解析結果鍵名（`projectId`／`systemId`／`diagramId`）原樣沿用，
    不另造一組名字——`hierarchy_service.resolve_work_target` 回的就是這三個鍵。"""
    return json.dumps(
        {"projectId": project_id, "systemId": system_id, "diagramId": diagram_id},
        separators=(",", ":"),
    )


def decode_target(blob: Optional[str]) -> dict:
    """`EC7`：`null` 原樣帶回，**不補齊**。「尚未選定」是真正可達的狀態
    （`BR7.2`／`AC2.2.3`），不是缺值。"""
    if not blob:
        return {"projectId": None, "systemId": None, "diagramId": None}
    raw = json.loads(blob)
    return {
        "projectId": raw.get("projectId"),
        "systemId": raw.get("systemId"),
        "diagramId": raw.get("diagramId"),
    }


def encode_meta(
    *, user_id: Optional[int], page_modes: Mapping[str, str], created_at: Mapping[str, str]
) -> str:
    return json.dumps(
        {
            "userId": user_id,
            "pageModes": dict(page_modes),
            "createdAt": dict(created_at),
        },
        separators=(",", ":"),
    )


def decode_meta(blob: Optional[str]) -> dict:
    if not blob:
        return {"userId": None, "pageModes": default_page_modes(), "createdAt": {}}
    raw = json.loads(blob)
    modes = default_page_modes()
    for scope, mode in (raw.get("pageModes") or {}).items():
        if scope in PAGE_SCOPES and mode in SHARING_MODES:
            modes[scope] = mode
    return {
        "userId": raw.get("userId"),
        "pageModes": modes,
        "createdAt": dict(raw.get("createdAt") or {}),
    }


def decode_session(session_key: str, fields: Mapping[str, str]) -> BrainSession:
    """`HGETALL` 的結果 → `BrainSession`。一次 round-trip（`NFR3.40`）。

    `U12` 的工作項欄位共用同一個 key，故**未知前綴的欄位一律忽略**
    （`OPEN-N10-7`）——不是容錯，是刻意的所有權邊界：本單元不解讀別的單元的
    欄位，也不因為它們存在而失敗。
    """
    meta = decode_meta(fields.get(META_FIELD))
    segments: dict = {}
    for segment_id in SEGMENT_IDS:
        blob = fields.get(segment_field(segment_id))
        if blob is None:
            continue
        target = decode_target(fields.get(target_field(segment_id)))
        segments[segment_id] = ConversationSegment(
            segment_id=segment_id,
            created_at=str(meta["createdAt"].get(segment_id, "")),
            messages=decode_messages(blob),
            project_id=target["projectId"],
            system_id=target["systemId"],
            diagram_id=target["diagramId"],
        )
    return BrainSession(
        session_key=session_key,
        user_id=meta["userId"],
        page_modes=meta["pageModes"],
        segments=segments,
    )



# ---------------------------------------------------------------------------
# `U12 work-orchestrator` 的工作項欄位（跨單元新增；`OPEN-N10-7` 的承接）
# ---------------------------------------------------------------------------
#
# 工作項與 session 共用同一個 key，每項一個欄位 `wi:<workItemId>`（`U12` 的
# `BR52.4`）。前綴 `wi:` 不與 `seg:`／`tgt:`／`meta` 衝突；`decode_session`
# 對未知前綴一律忽略，故本段的新增不改變既有任何讀取路徑。
#
# 下面兩個 `ref_*` 函式是 `put_work_item.lua`／`update_work_item.lua` 的
# **參考實作**——與本檔的 `trim_history` 同一個定位：**不是生產載體**，只給
# in-memory 替身模擬腳本效果、以及 `tests_redis/` 對真實 Redis 逐案比對用。
# 它們是純函式：輸入一份 Hash 的欄位快照，回傳 `(寫入與否, 新快照)`，不改動
# 輸入。Hash 不存在以 `None`（或空 dict，Redis 沒有零欄位的 Hash）表示。

#: 工作項欄位前綴。
WORK_ITEM_FIELD_PREFIX = "wi:"


def work_item_field(work_item_id: str) -> str:
    """`wi:<workItemId>`。"""
    if not isinstance(work_item_id, str) or not work_item_id:
        raise ValueError("workItemId 必須是非空字串")
    return f"{WORK_ITEM_FIELD_PREFIX}{work_item_id}"


def decode_work_items(fields: Optional[Mapping[str, str]]) -> dict:
    """`HGETALL` 的結果 → `{workItemId: 工作項 dict}`。只讀 `wi:*` 欄位。"""
    items: dict = {}
    for name, blob in (fields or {}).items():
        if not name.startswith(WORK_ITEM_FIELD_PREFIX) or blob is None:
            continue
        item = json.loads(blob)
        items[str(item.get("workItemId") or name[len(WORK_ITEM_FIELD_PREFIX):])] = item
    return items


def _work_item_statuses(fields: Mapping[str, str]):
    """`(欄位名, status, createdAt)` 的序列；只看 `wi:*` 欄位（與兩支 Lua 的掃描同形）。"""
    for name, blob in fields.items():
        if not name.startswith(WORK_ITEM_FIELD_PREFIX) or blob is None:
            continue
        item = json.loads(blob)
        created = item.get("createdAt")
        yield name, item.get("status"), created if isinstance(created, str) else ""


def ref_put_work_item(
    fields: Optional[Mapping[str, str]],
    field_name: str,
    item_json: str,
    max_active: str,
    terminal_statuses_json: str,
) -> tuple:
    """`put_work_item.lua` 的參考實作。

    key 不存在 → `(0, None)`，**不建 key**；欄位已存在 → `(0, 原快照)`；
    非終態（進行中）的工作項已達 `max_active` 筆 → `(-1, 原快照)`，不寫入；
    否則 `(1, 新快照)`。不改 TTL（TTL 不在本函式的模型內）。引數與腳本的
    `ARGV` 逐一對應（`max_active` 為整數字串、終態集合為 JSON 陣列）。
    """
    if not fields:
        return 0, None
    if field_name in fields:
        return 0, dict(fields)
    terminal = set(json.loads(terminal_statuses_json))
    active = sum(1 for _, status, _ in _work_item_statuses(fields) if status not in terminal)
    if active >= int(max_active):
        return -1, dict(fields)
    updated = dict(fields)
    updated[field_name] = item_json
    return 1, updated


def ref_update_work_item(
    fields: Optional[Mapping[str, str]],
    field_name: str,
    expected_statuses_json: str,
    expected_dispatch_stage: str,
    patch_json: str,
    max_terminal: str,
    terminal_statuses_json: str,
) -> tuple:
    """`update_work_item.lua` 的參考實作（比對後以補丁合併寫入）。

    比對 `status ∈ 預期集合` **且** `dispatchStage == 預期值`；皆符合才把補丁
    合併進**讀到的當前值**（補丁值為 `null` 即設為 null，未出現的欄位不動）。
    補丁使本項由非終態轉為終態時，終態項（含本項）超過 `max_terminal` 筆即依
    `(createdAt, 欄位名)` 由舊到新刪除**其他**終態項（本項不在候選內），進行中項
    永不刪除——語意逐條見 `update_work_item.lua` 檔頭。引數與腳本的 `ARGV` 逐一
    對應（皆為字串），使替身與真實 Redis 走同一份編碼。
    """
    if not fields:
        return 0, None
    raw = fields.get(field_name)
    if raw is None:
        return 0, dict(fields)
    item = json.loads(raw)
    expected = json.loads(expected_statuses_json)
    if item.get("status") not in expected:
        return 0, dict(fields)
    if item.get("dispatchStage") != expected_dispatch_stage:
        return 0, dict(fields)
    terminal = set(json.loads(terminal_statuses_json))
    was_terminal = item.get("status") in terminal
    patch = json.loads(patch_json)
    item.update(patch)
    updated = dict(fields)
    updated[field_name] = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
    if not was_terminal and item.get("status") in terminal:
        keep = int(max_terminal)
        finished = [
            (created, name)
            for name, status, created in _work_item_statuses(updated)
            if status in terminal
        ]
        excess = len(finished) - keep
        if excess > 0:
            candidates = sorted(entry for entry in finished if entry[1] != field_name)
            for _, name in candidates[:excess]:
                del updated[name]
    return 1, updated


__all__ = [
    "BrainSession",
    "ConversationSegment",
    "DEFAULT_SEGMENT_MAX_BYTES",
    "cjson_encoded_size",
    "segment_size_bytes",
    "META_FIELD",
    "PAGE_SCOPES",
    "SEGMENT_ASSESSMENT",
    "SEGMENT_FIELD_PREFIX",
    "SEGMENT_IDS",
    "SEGMENT_SHARED",
    "SEGMENT_WORKSPACE",
    "SHARING_ISOLATED",
    "SHARING_MODES",
    "SHARING_SHARED",
    "SessionMessage",
    "TARGET_FIELD_PREFIX",
    "WORK_ITEM_FIELD_PREFIX",
    "decode_messages",
    "decode_meta",
    "decode_session",
    "decode_target",
    "decode_work_items",
    "default_page_modes",
    "encode_messages",
    "encode_meta",
    "encode_target",
    "require_page_scope",
    "require_segment_id",
    "ref_put_work_item",
    "ref_update_work_item",
    "require_sharing_mode",
    "segment_field",
    "target_field",
    "trim_history",
    "work_item_field",
]
