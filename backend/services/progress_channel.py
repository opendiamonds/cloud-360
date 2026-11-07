"""
progress_channel.py — 每請求一條的進度事件通道（U22，行程內狀態容器）

職責：
  - 以 per-request 的不透明鍵隔離進度事件，取代 design_agent.py 的模組層全域
    `_progress_queue`（一個格子、所有請求共用）
  - 四個操作：open（同步）／publish（async）／drain（async）／close（同步）
  - 容量上界與丟棄優先序：滿載時丟最舊的 progress；xml／error／message 永不丟棄
  - 不做授權判定、不碰 DB、不連外、不新增任何設定面或進程邊界

它取代什麼（U22 的完成判準有一半在「舊符號消失」）：
  - `design_agent.py` 的 `_progress_queue`（模組層全域）→ 本模組的 per-key registry
  - `design_agent.py` 的 `_last_xml`（死狀態，從未被讀取）→ 刪除，不再有對應物
  - `design_agent.py` 的 `_drain_progress(queue)` → 改為呼叫 `ProgressChannel.drain(key)`

契約（呼叫端依賴，請勿變更）：
  ProgressChannel.open(key)            -> None         鍵已存在即 raise DuplicateChannelKey
  await ProgressChannel.publish(key, event) -> None    鍵不存在／已關閉則記 ERROR 並丟棄
  async for ev in ProgressChannel.drain(key)           鍵不存在／已關閉回空迭代器
  ProgressChannel.close(key)           -> None         冪等

  鍵的生命週期由**呼叫端**擁有：入口端鑄造鍵、`open`，並在 `try/finally` 的
  `finally` 內 `close`（BR2.1／BR2.3）。本模組不鑄造鍵、不自行清除。

執行前提（A-P2 / nfr-design S-4，失效是安靜的）：
  **本模組假設它跑在單執行緒的 asyncio 事件迴圈上，故不加鎖。** 這個假設由
  `_admit` 是**同步函式**來承擔——臨界區段（容量檢查 ＋ 丟棄 ＋ 寫入）整段不可
  被其他協程插入，因為同步函式裡沒有 await 點（在其中寫 `await` 是 SyntaxError）。
  若未來有任何路徑把 `publish` 丟到 `run_in_executor` 或另一條 thread 上，這個
  前提即失效，而失效不會有任何錯誤訊息——只會偶爾多出或少掉一則事件。

  刻意**不**照抄 `backend/cost/advice_orchestrator.py:23-24` 的 `threading.Lock`：
  那支檔案用 Lock 是因為它有 `ThreadPoolExecutor`（同檔 `:21` 的 `_executor`），
  而在單執行緒事件迴圈上 `threading.Lock` 是 cargo cult，且會在 await 邊界給出
  錯誤的安全感。沿用的只有它的 per-key dict 形狀。

本模組刻意**沒有**的東西：
  - 沒有任何鑄造鍵的函式，也不 import uuid／secrets／random（U22-V5）。鍵一律由
    參數傳入——鍵的不可猜性是這條通道唯一的可見性機制，鑄造端在入口端（SEC-1）。
  - 沒有授權判定（K-18 逐字「無受保護操作」）。
  - 沒有持久化、沒有跨行程可見性、沒有環境變數（SEC-4）。

追溯：U22-D1／U22-D2／U22-D3、BR1.1–BR5.1、SEC-1／SEC-3／SEC-4、U22-V4–U22-V6。
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

# U22-D2：新模組一律 "cloud360.<module>" 形式。**不沿用** design_agent.py:27 的
# logging.getLogger(__name__)——team.md 把那一行列為 5 個已知不一致之一。
logger = logging.getLogger("cloud360.progress_channel")


# ---------------------------------------------------------------------------
# RequestKey（value object）
# ---------------------------------------------------------------------------

#: 單一請求的進度通道識別字。不透明字串，由入口端鑄造並以顯式參數一路傳遞
#: （BR1.1）。與 `thread_id` **並存且語意分離**：`thread_id` 承載 LangGraph
#: checkpointer 的對話記憶分區（per-user），本鍵只承載進度通道的隔離
#: （per-request）。禁止以 `thread_id` 當鍵——它在 agent_router 是
#: `f"user-{current_user.id}-design"`，是 per-user，照它實作完隔離仍會紅燈。
RequestKey = str


# ---------------------------------------------------------------------------
# ProgressEvent（value object，不可變）
# ---------------------------------------------------------------------------

#: 事件類別的允許集合。**沿用 design_agent.py 既有的四種，不新增也不改名**
#: ——改名會讓 wa_collab_orchestrator.py 的 remap（xml → xml_preview、
#: message 加 speaker=design）失效。
EVENT_TYPES: frozenset[str] = frozenset({"progress", "xml", "message", "error"})

#: 容量壓力下**可以**被丟棄的類別。只有 progress（BR4.1）：它的價值是
#: 「還在動」，舊的那一則已無資訊。
DROPPABLE_EVENT_TYPES: frozenset[str] = frozenset({"progress"})


@dataclass(frozen=True)
class ProgressEvent:
    """一則要串流給使用者的事件。

    不可變：容量壓力下的處置是**丟棄整則**，不是截斷或改寫 content（BR4.1）。

    `content` **不得含內部例外原文**（BR3.1／AC13.1.3）。本類別無法強制這一點
    ——它是呼叫端的義務，由 `design_agent.py` 的單一出口結構（原文只進
    `logger.exception`）與契約測試的形狀級 grep 承擔。
    """

    type: str
    content: str

    def __post_init__(self) -> None:
        # 快速失敗：未知類別是程式錯誤（四個寫入端都用字面值），而它的下游後果
        # 是 wa_collab 的 remap 走到 else 分支把事件原樣送出去——那是安靜的。
        if self.type not in EVENT_TYPES:
            raise ValueError(
                f"未知的進度事件類別：{self.type!r}；允許值為 {sorted(EVENT_TYPES)}"
            )

    def as_dict(self) -> dict[str, str]:
        """轉成 SSE 既有的 wire 形狀 `{"type": ..., "content": ...}`。

        這是 wire 形狀的**唯一**定義處。agent_router.py 的契約區塊逐字寫
        「response: text/event-stream，data 為 JSON {type, content}」，而
        wa_collab_orchestrator 以 `event.get("type")` 分流——兩者都依賴這個形狀。
        """
        return {"type": self.type, "content": self.content}


class DuplicateChannelKey(Exception):
    """同一個鍵已有存活通道（BR1.2）。

    **不靜默覆寫**：覆寫會讓前一個請求「已寫入但還沒被讀走」的事件憑空消失，
    而那正是本單元要消除的失敗模式（`design_agent.py` 原本直接指派
    `_progress_queue = asyncio.Queue()`）。覆寫比錯送更難察覺——使用者只是少
    收到東西，沒有任何錯誤。

    例外訊息**刻意不含鍵本身**：鍵是這條通道唯一的可見性機制，不應出現在任何
    可能被轉述的字串裡。

    鍵改以 `.key` 屬性攜帶，供需要它的呼叫端取用而不必解析訊息字串。
    **如實記載目前的讀者**：產品程式裡沒有——兩個入口端的 handler 只呼叫
    `logger.exception`，因為 `open()` 在 raise 之前已經記過一次帶鍵的 ERROR，
    再記一次是重複。現有讀者是契約測試（它斷言訊息不含鍵、而鍵在這個屬性上）。
    """

    def __init__(self, key: RequestKey) -> None:
        super().__init__("進度通道的鍵已存在")
        self.key = key


# ---------------------------------------------------------------------------
# buffer 上界（S-1 / B-4：實測值 ＋ 倍數，兩者都要寫在這裡）
# ---------------------------------------------------------------------------

#: **實測值。** 一次 `draw_architecture_diagram` 工具呼叫產生的 progress 則數。
#: 量法：以 `backend/prompts/cloud_architecture_system_prompt.md` 內**它自己的
#: 四個官方 JSON 呼叫範例**（LLM 被要求遵循的形狀，所以「典型」有依據而不是
#: 估的）走真實的 `build_mxgraph_xml` 路徑，數 `on_progress` 的實際呼叫次數，
#: 再加上 design_agent 在工具開頭另發的一則「🧠 正在規劃進階架構拓樸...」。
#: 實測結果（2026-10-04，HEAD 的 diagram_builder）：
#:     AWS   11 nodes -> 11 + 1 = 12
#:     Azure 17 nodes -> 17 + 1 = 18   <- 最大
#:     GCP   15 nodes -> 15 + 1 = 16
#:     Azure 16 nodes -> 16 + 1 = 17
#: 結構上 progress 則數 = len(nodes) + 1（diagram_builder.py 在每個 node 的
#: icon 取得之前發一則），所以這個數字隨架構圖的節點數線性成長。
_MEASURED_MAX_PROGRESS_PER_TOOL_CALL = 18

#: **倍數。** 單一請求的 LangGraph 迴圈可以多次呼叫產圖工具（agent → tools →
#: agent → tools），而 buffer 只累積「尚未被 drain 取走」的事件；讀取端在
#: graph 的每一步都會 drain，所以常態下 buffer 只壓著一次工具呼叫的量。
#: 這個上界防的是**慢的或已斷線的消費者**，倍數 8 給它約八次工具呼叫的餘裕
#: ——遠高於實務上的 1–3 次，而記憶體成本仍有界。
#: 選 8 而不是「無上界」的理由：現狀 `asyncio.Queue()` 無上界，一個斷線的
#: 消費者可以讓該請求的事件無限累積（BR4.1）。
_BUFFER_HEADROOM_MULTIPLIER = 8

#: 單一通道的事件上界。以計算式表達，使數字不可能與它的推導漂移。
#: **軟上界**：xml／error／message 在滿載時仍會寫入，故 buffer 可暫時超過它
#: （BR4.1 逐字「必要時 buffer 暫時超過上界」）。
MAX_BUFFERED_EVENTS = (
    _MEASURED_MAX_PROGRESS_PER_TOOL_CALL * _BUFFER_HEADROOM_MULTIPLIER
)


# ---------------------------------------------------------------------------
# _Channel（ProgressChannel 實體的私有實作）
# ---------------------------------------------------------------------------


@dataclass
class _Channel:
    """單一請求的事件通道。生命週期與該請求等長。

    這是 `entities.md` 的 `ProgressChannel` 實體（屬性 key／buffer／is_open）的
    私有實作；公開名 `ProgressChannel` 保留給下方的 registry 單例，因為
    `functional-spec.md` 的四個操作全部寫成 `ProgressChannel.<op>(key)`。
    """

    key: RequestKey
    buffer: deque[ProgressEvent] = field(default_factory=deque)
    #: `close` 後為假。**它有讀者**：一個已經在跑的 `drain` 迭代器仍持有本物件
    #: 的參照（registry 裡的那一筆已被 `close` 移除），靠這個旗標停止吐事件。
    #: 少了它，被放棄的請求的 in-flight drain 會繼續讀一條已死的通道。
    is_open: bool = True
    #: 累計因容量被丟棄的則數。BR4.2 要求 WARN log 帶它。
    dropped_count: int = 0


def _index_of_oldest_droppable(buffer: deque[ProgressEvent]) -> int | None:
    """自最舊端起找第一則可丟棄（progress）的事件，回它的 index；沒有則回 None。"""
    for idx, event in enumerate(buffer):
        if event.type in DROPPABLE_EVENT_TYPES:
            return idx
    return None


def _admit(channel: _Channel, event: ProgressEvent) -> None:
    """容量檢查 ＋ 丟棄 ＋ 寫入。

    **同步函式——在這裡寫 `await` 是 SyntaxError。** 這不是風格偏好，是本模組
    不加鎖的全部依據：整段臨界區段（讀 len、決定丟誰、改 buffer）沒有 await
    點，所以其他協程不可能插進中間看到半套狀態（U22-V4 / nfr-design [Q1]=A）。
    任何把這個函式改成 `async def` 的修改都會默默拿掉這個保證。

    丟棄優先序（BR4.1）：
      - 未滿 → 直接寫入
      - 滿載 ＋ 新事件不可丟棄（xml／error／message）→ **一律寫入**，必要時
        buffer 暫時超過上界。丟 xml 會讓使用者看到一次「成功但沒有圖」的產圖；
        丟 error 會讓一次失敗變成無聲無息。
      - 滿載 ＋ 新事件是 progress → 自最舊端找第一則 progress 丟棄後寫入
      - 滿載 ＋ 新事件是 progress ＋ 已無 progress 可丟 → **拒絕寫入新的
        progress**，且不丟棄任何 xml／error／message
    每一次丟棄或拒絕都記 WARN（BR4.2），且**不含 content**（SEC-3：xml 類的
    content 是使用者的架構圖內容，寫進 log 等於把本單元要修的跨帳號外洩換個
    出口重演一次）。
    """
    if len(channel.buffer) < MAX_BUFFERED_EVENTS:
        channel.buffer.append(event)
        return

    if event.type not in DROPPABLE_EVENT_TYPES:
        # xml／error／message 永不丟棄，也不因滿載而被拒。
        channel.buffer.append(event)
        return

    victim_index = _index_of_oldest_droppable(channel.buffer)
    if victim_index is None:
        # buffer 全是不可丟棄的事件：拒絕寫入這一則 progress。
        channel.dropped_count += 1
        logger.warning(
            "進度通道滿載且無可丟棄事件，拒絕寫入 key=%s type=%s 累計丟棄=%d",
            channel.key,
            event.type,
            channel.dropped_count,
        )
        return

    del channel.buffer[victim_index]
    channel.dropped_count += 1
    logger.warning(
        "進度通道滿載，丟棄最舊的可丟棄事件 key=%s dropped_type=%s 累計丟棄=%d",
        channel.key,
        "progress",
        channel.dropped_count,
    )
    channel.buffer.append(event)


# ---------------------------------------------------------------------------
# ProgressChannelRegistry
# ---------------------------------------------------------------------------


class ProgressChannelRegistry:
    """全部存活通道的集合，以 RequestKey 為鍵。

    **這個結構本身就是隔離。** 現狀的洩漏不是「檢查寫錯了」，是根本沒有可檢查
    的東西——一個模組層全域，兩個請求指向同一個物件，所以「A 不該看到 B 的
    事件」在資料結構上無從表達。改成 per-key dict 之後，`drain(kA)` 能取到的
    集合由 `_channels[kA]` 界定，**跨鍵取值需要一個不存在的操作**。這是為什麼
    處置是隔離而非加授權：兩位使用者各自都有產圖的權限，壞的是事件去錯了地方。

    本集合的大小**必須隨請求結束而下降**（BR2.1）。只寫不刪會把跨使用者錯送
    換成無上界的記憶體成長，即修掉一個失敗模式換來另一個——而後者更難發現：
    沒有錯誤訊息，只有緩慢的記憶體曲線。
    """

    def __init__(self) -> None:
        self._channels: dict[RequestKey, _Channel] = {}

    # -- 建立與關閉（同步；由入口端的 try/finally 擁有）--------------------

    def open(self, key: RequestKey) -> None:
        """建立一條通道。鍵已存在即 `raise DuplicateChannelKey`，**不覆寫**（BR1.2）。"""
        if key in self._channels:
            logger.error("進度通道的鍵重複，拒絕覆寫既有通道 key=%s", key)
            raise DuplicateChannelKey(key)
        self._channels[key] = _Channel(key=key)

    def close(self, key: RequestKey) -> None:
        """移除一條通道。**冪等**（BR2.2）：鍵不存在或已關閉皆視為成功。

        冪等是必要的而非方便：BR2.1 把 `close` 放在 `finally`，而「正常路徑已
        關閉 ＋ 異常路徑再關一次」會讓非冪等的實作拋出第二個例外，覆蓋掉原始
        失敗原因。
        """
        channel = self._channels.pop(key, None)
        if channel is not None:
            # in-flight 的 drain 迭代器仍持有這個物件，靠旗標讓它停止。
            channel.is_open = False

    # -- 寫入 ---------------------------------------------------------------

    async def publish(self, key: RequestKey, event: ProgressEvent) -> None:
        """把一則事件寫進該鍵的通道。

        鍵不存在或已關閉時：記一筆 **ERROR** 並丟棄該事件，**不崩潰也不靜默
        成功**（BR3.2）。崩潰會讓一個已經結束的請求把還在跑的請求弄壞（那正是
        現狀：`_drain_progress(None)` 對 None 呼叫 `get_nowait()` 拋
        AttributeError）；靜默成功則讓「事件寫去哪了」完全無跡可循，而那正是
        清除契約被違反後最可能的症狀，必須留得下痕跡才查得到。

        log 含鍵與事件類別，**不含 content**（SEC-3）。
        """
        channel = self._channels.get(key)
        if channel is None or not channel.is_open:
            logger.error(
                "publish 到不存在或已關閉的進度通道，事件已丟棄 key=%s type=%s",
                key,
                event.type,
            )
            return
        # 以下為臨界區段，整段在同步函式內完成，不可被其他協程插入。
        _admit(channel, event)

    # -- 讀取 ---------------------------------------------------------------

    async def drain(self, key: RequestKey) -> AsyncIterator[ProgressEvent]:
        """取出並移除該鍵目前已緩衝的全部事件。

        **破壞性讀取**：事件一經取出即自 buffer 移除，不保證重放。斷線重連是否
        補事件屬對外協定（U13），不是本模組的決定。

        鍵不存在或已關閉時回**空迭代器、不拋例外**（BR2.4）。**已關閉與從未
        存在在對外行為上刻意不可區分**——可區分的話，呼叫端就能探知某個鍵曾經
        存在，而鍵的不可猜性是這條通道唯一的可見性機制。

        `form` 是 async（契約 K-18），但**迴圈本體內沒有任何 `await`、沒有
        I/O**：它是純粹的 deque 取出，複雜度 O(取出則數)。這承載 U22-V6——
        進度事件經本方法流向使用者，所以本方法在 NFR3 的首字路徑上，一旦阻塞
        或做 I/O 就會直接計入那個量測。
        """
        channel = self._channels.get(key)
        if channel is None:
            return
        while channel.is_open and channel.buffer:
            yield channel.buffer.popleft()


#: 行程內的單例。公開名為 `ProgressChannel`，使四個操作的呼叫形狀與
#: `functional-spec.md` 的 `ProgressChannel.open(key)` ／ `.publish` ／ `.drain`
#: ／ `.close` 逐字一致。
ProgressChannel = ProgressChannelRegistry()
