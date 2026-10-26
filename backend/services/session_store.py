"""session_store.py — `U10 session-store` 的商業邏輯（契約 `K-09`）

**契約（同進程呼叫端 `U11`／`U12`／`U13` 依賴，請勿變更）**

一個 session、**至多三段**、每段自帶歷程與作業對象、每頁指向自己要讀的那一段。
全部狀態在 Redis 的**單一 key** 之下（`BR1.2`：不得放行程記憶體）。
TTL 24 小時，**五個方法全部續期**（`BR1.3`）。

## 本模組的三條禁令（`NFR4.46`／`BR5.1`–`BR5.3`，皆為靜態可檢查的形狀）

1. **不自行判權**（`BR5.1`）。作業對象的授權**全部**委派給 `K-07` 的
   `HierarchyFacade.resolve_work_target`；本模組不讀 `role_permissions`、
   不呼叫 `require_story_action`。
2. **不自行從請求取身分**（`BR5.2`）。`principal` 一律由**參數**傳入；本模組
   不 import 任何 request／websocket 型別，也不讀模組層狀態。自取身分會讓
   同進程呼叫者得以用別人的身分寫入。
3. **不暴露任何 HTTP 或 WebSocket 端點**（`BR5.3`）。對外面一律經 `U13` 的既有
   端點；本模組不註冊 router。新增對外面會繞過 `U13` 的握手與身分驗證。

`test_session_contract.py` 以 AST 斷言這三項，**不是**靠本段散文。

## 為什麼 `K-07` 的 facade 是**鴨子型別**注入的

本模組刻意**不 import** `hierarchy_facade`：那會把 `sqlalchemy` 與 `models` 拉進
本模組的 import 集合，而 `NFR4.46` 的靜態斷言要驗的正是「本模組的 import 集合
裡沒有 DB／request 型別」。facade 由建構子注入，型別需求只有一個方法：

    resolve_work_target(principal, *, project_id, system_id, diagram_id) -> dict

`HierarchyForbidden`／`HierarchyNotFound` **原樣向上傳遞**（`BR4.6` 逐字）——
本模組不 catch 它們，故也不需要 import 它們。`hierarchy_facade.py:277-281`
逐字：「這是同進程路徑，**沒有任何 router 層會替它補上範圍檢查**。」

## `set_work_target` 寫的是**解析結果**，不是呼叫方傳入的原始識別碼

`security-design.md §一` 第 2 點：若寫入原始值，`K-07` 的檢查就只是一道裝飾。
`BR4.7`：**每一段各自驗證**——`[S3]`=A 把作業對象從一組變成每段一組，驗證若仍
只跑一次，段數一多就有 N−1 組未驗的值。唯一例外是 `BR4.2` 的初始化複製
（來源是已驗證的共享段值），該例外在 `switch_to_isolated.lua` 的檔頭逐字寫出。

## 失效行為（`BR6.1`）

Redis 不可用時 **raise `SessionBackendUnavailable` 向上傳遞**——不降級、不退回
行程記憶體、**不回傳空的 `BrainSession`**。回空 session 會讓畫面看起來「只是
脈絡被清掉了」，而那與 TTL 到期在使用者眼中完全相同：一個是正常行為、一個是
基礎設施故障，兩者不可區分即等於故障不可偵測。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from services.redis_gateway import (
    SCRIPT_APPEND_MESSAGE,
    SCRIPT_SWITCH_TO_ISOLATED,
    SESSION_TTL_SECONDS,
    RedisGateway,
    log_session_event,
    session_log_fields,
)
from services.session_errors import SessionMessageTooLong
from services.session_types import (
    DEFAULT_SEGMENT_MAX_BYTES,
    META_FIELD,
    SEGMENT_SHARED,
    SHARING_ISOLATED,
    BrainSession,
    decode_meta,
    decode_session,
    decode_work_items,
    default_page_modes,
    encode_messages,
    encode_meta,
    encode_target,
    require_page_scope,
    require_segment_id,
    require_sharing_mode,
    segment_field,
    target_field,
    work_item_field,
)
import enum
import json as _json

# 工作項容量的**正本**在 `U12` 的純函式層（零 I/O、只依賴 `intent_routing_types`），
# 本模組只把它們經 `ARGV` 交給 Lua，不抄第二份（`team.md`「單一真實來源」）。
from services import work_orchestrator_rules as _work_rules

logger = logging.getLogger("cloud360.session_store")

#: `U12 work-orchestrator` 的兩支 Lua（`session_scripts/` 內同名檔）。名稱放在
#: 本模組而非 `redis_gateway`：gateway 不認識 session 語意，而它以名稱從
#: `scripts_dir` 讀檔，不需要先登錄。
SCRIPT_PUT_WORK_ITEM = "put_work_item"
SCRIPT_UPDATE_WORK_ITEM = "update_work_item"


class WorkItemPutResult(enum.Enum):
    """`put_work_item` 的三種結果（合併前必修第 18 項）。

    `bool(result)` 只在 `WRITTEN` 時為真，故既有的「`if not put_work_item(...)`」
    寫法語意不變；需要區分「已到期或重複」與「已達上限」的呼叫端（`U12` 的
    `dispatch`）直接比對成員。
    """

    WRITTEN = "written"
    #: key 不存在（工作階段已到期）或同一個 workItemId 已存在。
    REJECTED = "rejected"
    #: 同一工作階段的進行中（處理中＋等待中）工作項已達上限。
    CAPACITY_EXCEEDED = "capacity_exceeded"

    def __bool__(self) -> bool:
        return self is WorkItemPutResult.WRITTEN


def _terminal_statuses_json() -> str:
    # 排序後編碼：ARGV 內容決定性，便於與參考實作逐位元比對。
    return _json.dumps(
        sorted(_work_rules.TERMINAL_STATUSES), ensure_ascii=False, separators=(",", ":")
    )

#: `NFR8.40`：每段訊息筆數上限的**具名環境變數**，**無預設值**。
HISTORY_MAX_ENV = "BRAIN_SESSION_HISTORY_MAX"

#: `OPEN-N10-6` 的單則訊息長度上限（字元）。
#:
#: **這個數值是本站選的，`security-design.md §三` 逐字把數值留給下游**，並註明
#: 「若數值須由產品決定，該站須重新提交使用者」。本站選 4000 的依據與它**無法**
#: 同時滿足的那一項，都如實記在 `code-summary.md` 的開放項：
#:
#:   * 選 4000 的理由：`scalability-requirements.md` 的每則平均 **500 B** 是
#:     *假設值*，4000 字元給它 8 倍餘裕，不會拒絕現實中的訊息。
#:   * **它單獨封不住容量**：3 段 × 200 則 × 4000 字元遠大於以平均值算出的
#:     300 KB／session。這一項由**每段 200 KB 的位元組上限**
#:     （`session_types.DEFAULT_SEGMENT_MAX_BYTES`，`merge-blockers.md` 第 18 項）
#:     關掉：修剪取「筆數上限」與「位元組上限」較嚴者，最壞情況因此是
#:     對話 3 × 200 KiB ≈ 600 KiB／session；加上同 key 的 `U12` 工作項（進行中
#:     ≤ 5、已結束 ≤ 20，每筆以序列化後位元組封頂，最壞 81,000 B ≈ 79.1 KiB）
#:     合計 695,400 B ≈ 679.1 KiB，對 `maxmemory 256mb` 的 80% 約 308.8 個 session
#:     （`NFR4.40` 要求 ≥ 300；常數在 `work_orchestrator_rules.py`，算式見 `DEPLOY.md`）。
#:
#: 刻意**不**為它新增第二個環境變數：`NFR8.41`／本計畫只授權一個新依賴與一個
#: 新環境變數，而把產品面的輸入長度限制偷偷變成運維設定會讓它更難被看見。
DEFAULT_MESSAGE_MAX_CHARS = 4000

#: 單則訊息序列化後每個字元**最多**佔的位元組數。UTF-8 一個碼點最多 4 位元組，
#: 但 cjson 對控制字元與 `0x7f` 輸出 `\u00XX`（6 位元組），故取 6。
MAX_ENCODED_BYTES_PER_CHAR = 6

#: 單則訊息除 `text` 以外的封套（`role`、`createdAt`、`sequence` 與鍵名、引號）
#: 的保留量。`role` 由 `U13` 依對話協定給值（不是使用者輸入），1 KB 綽綽有餘。
MESSAGE_ENVELOPE_RESERVE_BYTES = 1024


def resolve_history_max(env: Optional[Any] = None) -> int:
    """讀取並驗證 `BRAIN_SESSION_HISTORY_MAX`（`BR3.5`／`NFR8.40`）。

    **缺值即大聲失敗，不得把「無值」解讀為「無上限」**——以無上限啟動會讓單一
    Redis key 無上界成長，而那是無聲的。既有前例是 `ADR-008`／`K-01` 的
    `EMBEDDING_PROVIDER`（逐字「刻意無預設：偵測不到選定提供者時須大聲失敗」）。
    """
    source = os.environ if env is None else env
    raw = (source.get(HISTORY_MAX_ENV) or "").strip()
    if not raw:
        raise RuntimeError(
            f"{HISTORY_MAX_ENV} 未設定。它**刻意無預設值**（BR3.5／NFR8.40）："
            "把缺值讀成「無上限」會讓單一 Redis key 無上界成長，而那是無聲的。"
            "請在 backend/.env（本機）或 deploy/.env（部署，由 "
            "deploy/render-env.sh 產生）設定它；建議值 200。"
        )
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"{HISTORY_MAX_ENV} 必須是正整數，收到 {raw!r}（BR3.5）"
        ) from exc
    if value < 1:
        raise RuntimeError(
            f"{HISTORY_MAX_ENV} 必須是正整數，收到 {value}（BR3.5）"
        )
    return value


def configure_session_env(env: Optional[Any] = None) -> int:
    """啟動時驗證本單元的設定，記一條 INFO（`BR3.5`）。

    由 `backend/main.py` 的 startup hook 呼叫，與 `configure_embedding_env()`
    並列、形狀刻意相同：**失敗即拋**。掛在 startup hook 而非 import 時，是為了
    讓既有測試（完全不設定本變數、且以 `TestClient(app)` 不觸發本 hook）不受
    影響——既有測試全綠本身就是這個選擇的驗證。
    """
    history_max = resolve_history_max(env)
    logger.info(
        "session store 設定已解析：每段歷程上限 %s 則且 %s 位元組、TTL %s 秒、"
        "單則訊息上限 %s 字元",
        history_max,
        DEFAULT_SEGMENT_MAX_BYTES,
        SESSION_TTL_SECONDS,
        DEFAULT_MESSAGE_MAX_CHARS,
    )
    return history_max


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    """契約 `K-09` 的五個方法。

    `history_max` 與 `message_max_chars` 是**建構子參數**而非模組常數，讓測試
    以 5 則／短字串驅動「超限丟最舊」與「訊息太長」，不需要 200 則資料
    （`unit-test-instructions.md §七`）。
    """

    def __init__(
        self,
        gateway: RedisGateway,
        *,
        hierarchy_facade: Any,
        history_max: Optional[int] = None,
        message_max_chars: int = DEFAULT_MESSAGE_MAX_CHARS,
        segment_max_bytes: int = DEFAULT_SEGMENT_MAX_BYTES,
        ttl_seconds: int = SESSION_TTL_SECONDS,
        now: Callable[[], str] = _utc_now_iso,
    ) -> None:
        # 前提（`merge-blockers.md` 第 18 項）：**單則訊息不可能超過每段位元組上限**，
        # 故修剪不需要「單則超限」分支。以算式確認而不是假設——不成立時拒絕建構，
        # 而不是讓修剪在剩一則時停下、默默放行一個超限的段。用 `raise` 而非
        # `assert`：`python -O` 會拿掉 `assert`。
        worst_single = (
            message_max_chars * MAX_ENCODED_BYTES_PER_CHAR
            + MESSAGE_ENVELOPE_RESERVE_BYTES
            + 2  # 整段只有這一則時的 `[` `]`
        )
        if worst_single > segment_max_bytes:
            raise ValueError(
                f"單則訊息最壞 {worst_single} 位元組超過每段上限 "
                f"{segment_max_bytes} 位元組：修剪無法保證段在上限內"
            )
        self._gateway = gateway
        # `K-07` 的 facade。鴨子型別，見模組 docstring：本模組不 import
        # `hierarchy_facade`，故 import 集合裡沒有 DB 型別。
        self._hierarchy = hierarchy_facade
        self._history_max = (
            history_max if history_max is not None else resolve_history_max()
        )
        self._message_max_chars = message_max_chars
        self._segment_max_bytes = segment_max_bytes
        self._ttl_seconds = ttl_seconds
        self._now = now

    # -- `load`／`touch` ---------------------------------------------------

    def load(self, session_key: str) -> Optional[BrainSession]:
        """`BR1.6`：key 不存在回 `None` 而非錯誤——那是新 session 的合法起點。

        把「新使用者第一次進入」當成錯誤處理會讓首次使用不可用。

        `BR1.3`：**無論哪一種結果都續期 TTL**（`W1` 第 4 步）。key 不存在時
        `EXPIRE` 是 no-op，刻意仍然發出——讓「五個方法全部續期」這句話在程式
        上沒有例外分支，少一個分支就少一個會漏續期的地方。
        """
        method = "load"
        self._require_session_key(session_key)
        fields = self._gateway.hgetall(method, session_key)
        self._gateway.expire(method, session_key, self._ttl_seconds)
        if not fields:
            return None
        session = decode_session(session_key, fields)
        remaining = self._gateway.ttl(method, session_key)
        return BrainSession(
            session_key=session.session_key,
            user_id=session.user_id,
            page_modes=session.page_modes,
            segments=session.segments,
            expires_at_seconds=remaining,
        )

    def touch(self, session_key: str) -> None:
        """`BR1.3` 的續期。`K-09` 逐字 `returns: None`。"""
        self._require_session_key(session_key)
        self._gateway.expire("touch", session_key, self._ttl_seconds)

    # -- `append_message`（`BR3.1`：**必須**帶段識別）-----------------------

    def append_message(
        self, session_key: str, segment_id: str, role: str, text: str
    ) -> None:
        """追加一則訊息到**指定的段**（`BR3.1`）。

        `segment_id` 是**必填位置參數**，沒有預設值——`OQ-N4` 逐字指出
        「`append_message(session_key, role, text)` 沒有任何參數說這則訊息屬於
        哪一段」，而預設為共享段正是它點名的兩種壞結果之一（「附加進同一份歷程
        → `FR3.2` 在切回時被違反」）。這個參數的**位置**就是修法。

        長度檢查在**入口**（`OPEN-N10-6`／`security-design.md §三`）：拒絕要能
        帶出一個明確的錯誤給呼叫方，而 Lua 的錯誤是字串、不利於型別化處置。
        超限的行為是**拒絕**，不是截斷——截斷會讓使用者的訊息被默默改掉。

        `BR6.2`：本方法**非冪等**，故 gateway 不重試它。重試會製造第二則訊息。
        """
        method = "append_message"
        self._require_session_key(session_key)
        require_segment_id(segment_id)
        if not role:
            raise ValueError("role 不得為空（SessionMessage.role required）")
        if text is None:
            raise ValueError("text 不得為 None（SessionMessage.text required）")
        if len(text) > self._message_max_chars:
            # 例外**不帶被拒的文字**，只帶長度（`BR3.6`：長度是中繼資料）。
            raise SessionMessageTooLong(
                limit=self._message_max_chars, actual=len(text)
            )

        self._ensure_meta(method, session_key)
        # `sequence` 刻意**不由 Python 指定**：它由 `append_message.lua` 以該段
        # 當下的最後一筆 +1 計算，與追加同在一支腳本內。Python 端算它需要先讀
        # 一次（讀→改→寫），而那正是 `[D1]`=A 用 Lua 取代的三次 round-trip，
        # 且兩個並行追加會算出同一個序號。
        payload = _json.dumps(
            {"role": role, "text": text, "createdAt": self._now()},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        result = self._gateway.eval_script(
            method,
            SCRIPT_APPEND_MESSAGE,
            [session_key],
            [
                segment_field(segment_id),
                payload,
                self._history_max,
                self._ttl_seconds,
                self._segment_max_bytes,
            ],
            idempotent=False,
            segment_id=segment_id,
        )
        dropped = int(result[1]) if isinstance(result, (list, tuple)) and len(result) > 1 else 0
        if dropped:
            # `BR3.4` 的丟棄。**只記數量，不記被丟棄的內容**（`NFR4.63`）。
            log_session_event(
                logging.DEBUG,
                "session_history_trimmed",
                session_log_fields(
                    sessionKey=session_key, segmentId=segment_id, droppedCount=dropped
                ),
            )

    # -- `set_sharing_mode`（`BR2.2`／`BR2.3`／`BR2.4`／`BR2.5`）-------------

    def set_sharing_mode(self, session_key: str, scope: str, mode: str) -> BrainSession:
        """切換**單一頁面**的共享模式（`[S1]`=A 的逐頁模式）。

        `BR2.2`：以**入口頁**為範圍呼叫一律被拒——入口頁恆讀共享段，而「恆為」
        不是狀態機的一個狀態，是沒有狀態。`require_page_scope` 的封閉集合
        （`{workspace, assessment}`）就是這道拒絕。

        `BR2.3`：只改 `pageModes[scope]`，其餘頁面不動——改動其他頁會讓
        `AC3.1.1` 的「入口頁的脈絡不受影響」不成立。

        切到 `isolated` 走 `switch_to_isolated.lua`（建段＋複製＋改模式，**原子**，
        `EC3`）；切回 `shared` **只改 `pageModes`**，`segments[scope]` 原樣保留
        直到 TTL 到期（`BR2.5`）——刪除即違反已核可的
        `unit-of-work.md:133`「保留」，而兩段之間**沒有任何合併路徑**（`BR2.6`）。
        """
        method = "set_sharing_mode"
        self._require_session_key(session_key)
        require_page_scope(scope)
        require_sharing_mode(mode)

        # `EC1`：`segments` **必含** `shared`。本方法與 `append_message`／
        # `set_work_target` 一樣可能是這個 key 的**第一次寫入**——使用者開了
        # `/workspace` 之後、在送出任何訊息或選定作業對象**之前**就切換模式，
        # 走的就是這條路。少了這一行：
        #   * 切 `shared`  → 整個 session 只有 `meta`，`segments == {}`；
        #   * 切 `isolated` → `segments == {"workspace": …}` 而**沒有** `shared`。
        # 兩者都讓 `EC1` 為假。後續對 `shared` 的寫入會因 Lua 的 `HGET` 回 nil
        # 退路而自癒，所以它不是資料毀損——但「共享段永遠存在」這個下游據以
        # 推論的不變量在那段時間內是不成立的，而那正是不變量的意義所在。
        self._ensure_meta(method, session_key)

        if mode == SHARING_ISOLATED:
            created = self._gateway.eval_script(
                method,
                SCRIPT_SWITCH_TO_ISOLATED,
                [session_key],
                [
                    segment_field(scope),
                    target_field(scope),
                    target_field(SEGMENT_SHARED),
                    META_FIELD,
                    scope,
                    self._now(),
                    self._ttl_seconds,
                    encode_messages(()),
                    encode_target(None, None, None),
                    self._default_meta(),
                ],
                idempotent=True,
                segment_id=scope,
            )
            if isinstance(created, (list, tuple)) and created and int(created[0]) == 1:
                log_session_event(
                    logging.INFO,
                    "session_segment_created",
                    session_log_fields(sessionKey=session_key, segmentId=scope),
                )
        else:
            # 寫 `meta` 與續期同一個交易（`merge-blockers.md` 第 12 項，與
            # `set_work_target` 同形）。讀→改→寫本身仍是兩次 round-trip，見
            # `code-summary.md` 對並行寫入的記載。
            meta = self._load_meta(method, session_key)
            meta["pageModes"][scope] = mode
            self._write_meta_and_expire(method, session_key, meta)

        return self._reload(method, session_key)

    # -- `set_work_target`（`BR4.3`／`BR4.6`／`BR4.7`：**逐段**驗證）---------

    def set_work_target(
        self,
        session_key: str,
        segment_id: str,
        principal: Any,
        project_id: Optional[int] = None,
        system_id: Optional[int] = None,
        diagram_id: Optional[int] = None,
    ) -> BrainSession:
        """設定**某一段**的三層作業對象。

        **解析在前、寫入在後，且寫入的是解析結果**（`security-design.md §一`
        第 2 點）。若寫入呼叫方傳入的原始識別碼，`K-07` 的檢查就只是一道裝飾。

        `BR4.6`：`HierarchyForbidden`／`HierarchyNotFound` **原樣向上傳遞**——
        本方法刻意**不** catch 它們，故解析失敗時**不會有任何寫入落地**。

        `BR4.5`：解析結果某層為 `null` 時**原樣儲存 null**，不推導、不補齊、
        不拒絕（`EC7`：`OPEN-H11` 的新圖沒有系統歸屬，而 `K-07` 刻意不拒絕它）。
        `EC8`：不重驗三層之間的階層一致性——那是 `U7` 的責任。
        """
        method = "set_work_target"
        self._require_session_key(session_key)
        require_segment_id(segment_id)
        if principal is None:
            # `BR5.2`：身分一律由參數傳入。本模組沒有第二個取得身分的途徑，
            # 故 `None` 是呼叫錯誤而不是「匿名」。
            raise ValueError("principal 不得為 None（BR5.2：身分一律由參數傳入）")

        resolved = self._hierarchy.resolve_work_target(
            principal,
            project_id=project_id,
            system_id=system_id,
            diagram_id=diagram_id,
        )

        self._ensure_meta(method, session_key)
        # 寫入與續期以**同一個交易**送出（`merge-blockers.md` 第 12 項）：分開送時
        # 兩者之間中斷，或 key 恰好在兩者之間到期而被 `HSET` 重建，都會留下一個
        # 沒有 TTL 的 key。
        self._gateway.hset_fields_and_expire(
            method,
            session_key,
            {
                target_field(segment_id): encode_target(
                    resolved.get("projectId"),
                    resolved.get("systemId"),
                    resolved.get("diagramId"),
                )
            },
            self._ttl_seconds,
            idempotent=True,
            segment_id=segment_id,
        )
        return self._reload(method, session_key)

    # -- 工作項（`U12 work-orchestrator` 的跨單元新增；`BR52.4`／`BR52.7`）----
    #
    # 三個方法**都不續期 TTL**：工作項隨工作階段既有的到期時間到期（`U12` 的
    # `BR52.4`）。這是對本類別「五個方法全部續期」的**刻意例外**——續期的語意
    # 是「使用者有互動」，而背景執行推進工作項不是使用者互動；若它續期，一個
    # 背景輪詢就能讓使用者早已離開的 session 無限延長。
    #
    # 兩個寫入方法皆為 Lua、皆以 `idempotent=False` 執行（傳輸層不自動重送）：
    # 比對後寫入不是冪等的，重送可能在第一次已成功時把第二次判為「比對不符」，
    # 呼叫端便誤以為被別人搶先。連線錯誤時的結果未知由呼叫端重讀確認。

    def load_work_items(self, session_key: str) -> dict:
        """讀出所有 `wi:*` 欄位 → `{workItemId: 工作項 dict}`。key 不存在回 `{}`。"""
        self._require_session_key(session_key)
        return decode_work_items(self._gateway.hgetall("load_work_items", session_key))

    def put_work_item(self, session_key: str, item: dict) -> WorkItemPutResult:
        """新建一個工作項欄位，回 `WorkItemPutResult`（`bool` 只在已寫入時為真）。

        - key 不存在或欄位已存在 → `REJECTED`，不寫入；
        - 進行中（非終態）已達 `MAX_ACTIVE_WORK_ITEMS` → `CAPACITY_EXCEEDED`，不寫入
          （合併前必修第 18 項；計數與寫入在同一支 Lua 內，併發交辦不會一起越線）。

        **不得以 `HSET`／`HSETNX` 直接寫**：key 已到期時那會重建一個沒有到期
        時間、沒有 `meta` 的 key（`U12` 的 `NFR12.18`）。
        """
        method = "put_work_item"
        self._require_session_key(session_key)
        field = work_item_field(item.get("workItemId"))
        payload = _json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        result = int(
            self._gateway.eval_script(
                method,
                SCRIPT_PUT_WORK_ITEM,
                [session_key],
                [
                    field,
                    payload,
                    str(_work_rules.MAX_ACTIVE_WORK_ITEMS),
                    _terminal_statuses_json(),
                ],
                idempotent=False,
            )
            or 0
        )
        if result == 1:
            return WorkItemPutResult.WRITTEN
        if result == -1:
            return WorkItemPutResult.CAPACITY_EXCEEDED
        return WorkItemPutResult.REJECTED

    def update_work_item(
        self,
        session_key: str,
        work_item_id: str,
        expected_statuses,
        expected_dispatch_stage: str,
        patch: dict,
    ) -> bool:
        """比對 `status ∈ expected_statuses` 且 `dispatchStage ==
        expected_dispatch_stage` 後，以**補丁**合併寫入（`U12` 的 `BR52.7`）。

        `patch` 只含要改的欄位；值為 `None` 即設為 null，未出現的欄位不動——
        故呼叫端不可能以過期副本覆寫別人剛寫入的欄位（例如 `estimateSetId`）。

        補丁使該項由非終態轉為終態時，腳本在同一次原子執行內把終態項修剪到
        `MAX_TERMINAL_WORK_ITEMS` 筆（刪最舊的**其他**終態項；進行中項永不刪；
        合併前必修第 18 項）。
        """
        method = "update_work_item"
        self._require_session_key(session_key)
        statuses = list(expected_statuses)
        if not statuses:
            raise ValueError("expected_statuses 不得為空")
        if not isinstance(patch, dict) or not patch:
            raise ValueError("patch 必須是非空的 dict")
        result = self._gateway.eval_script(
            method,
            SCRIPT_UPDATE_WORK_ITEM,
            [session_key],
            [
                work_item_field(work_item_id),
                _json.dumps(statuses, ensure_ascii=False, separators=(",", ":")),
                expected_dispatch_stage,
                _json.dumps(patch, ensure_ascii=False, separators=(",", ":")),
                str(_work_rules.MAX_TERMINAL_WORK_ITEMS),
                _terminal_statuses_json(),
            ],
            idempotent=False,
        )
        return int(result or 0) == 1

    # -- 內部 --------------------------------------------------------------

    @staticmethod
    def _require_session_key(session_key: Any) -> None:
        """`BR1.1`：本單元**不產生** session key，它由 `U13` 在握手成功後提供。

        未提供即拒絕；**不自行推導、不自行產生**。
        """
        if not isinstance(session_key, str) or not session_key:
            raise ValueError(
                "session key 必須由呼叫方提供（BR1.1）：本單元不自行推導、不自行產生"
            )

    def _default_meta(self) -> str:
        return encode_meta(
            user_id=None, page_modes=default_page_modes(), created_at={}
        )

    def _load_meta(self, method: str, session_key: str) -> dict:
        return decode_meta(self._gateway.hget(method, session_key, META_FIELD))

    def _write_meta_and_expire(self, method: str, session_key: str, meta: dict) -> None:
        self._gateway.hset_fields_and_expire(
            method,
            session_key,
            {
                META_FIELD: encode_meta(
                    user_id=meta.get("userId"),
                    page_modes=meta.get("pageModes") or default_page_modes(),
                    created_at=meta.get("createdAt") or {},
                )
            },
            self._ttl_seconds,
            idempotent=True,
        )

    def _ensure_meta(self, method: str, session_key: str) -> None:
        """首次寫入時建立 `meta` 與共享段（`EC1`：`segments` 必含 `shared`）。

        `functional-spec.md §2.2` 的狀態機只有兩個狀態，轉換是「`load` 回『無』
        ＋**首次寫入**」——`K-09` 沒有 `create` 方法，故建立就發生在這裡。

        ⚠ **`meta.userId` 在此為 `null`**：`K-09` 的凍結介面裡，唯一帶身分的
        方法是 `set_work_target`（它有 `principal`），而 `append_message`／
        `set_sharing_mode`／`touch` 都沒有。`entities.md` 宣告 `userId`
        `required: true`，但契約**沒有給它寫入端**。這個缺口如實記在
        `code-summary.md`，處置是：`set_work_target` 會把它補上，而
        `sessionKey` 本身就是由使用者 id 推導的（`x-session-key-derivation`），
        故讀取端在它為 `null` 時仍可自行解析。**不自行從任何地方猜它。**

        **建立與 TTL 同一個交易**（`merge-blockers.md` 第 12 項，裁決 MULTI／EXEC）：
        原本是兩次獨立 `HSET`、TTL 要等呼叫端下一個指令才設；兩者之間行程中止就
        留下一個**永不過期**的 key。現在 `meta`、`seg:shared` 與 `EXPIRE` 一起
        EXEC——EXEC 之前中斷則 key 根本不存在，下一次寫入會重新建立它。

        **並行的第一次寫入以 `HSETNX` 收斂**：`EXISTS` 與交易之間不是原子的，
        兩個並行的第一次寫入都可能看到「不存在」。預設值因此以 `only_if_absent`
        （`HSETNX`）寫入——後到者不會把先到者剛追加的 `seg:shared` 蓋回 `[]`，
        只會續期 TTL。`EXISTS` 保留為快速路徑（常態下省一次交易）。
        """
        if self._gateway.exists(method, session_key):
            return
        self._gateway.hset_fields_and_expire(
            method,
            session_key,
            {
                META_FIELD: self._default_meta(),
                segment_field(SEGMENT_SHARED): encode_messages(()),
            },
            self._ttl_seconds,
            idempotent=True,
            only_if_absent=True,
        )

    def _reload(self, method: str, session_key: str) -> BrainSession:
        fields = self._gateway.hgetall(method, session_key)
        session = decode_session(session_key, fields)
        return BrainSession(
            session_key=session.session_key,
            user_id=session.user_id,
            page_modes=session.page_modes,
            segments=session.segments,
            expires_at_seconds=self._gateway.ttl(method, session_key),
        )


__all__ = [
    "DEFAULT_MESSAGE_MAX_CHARS",
    "MAX_ENCODED_BYTES_PER_CHAR",
    "MESSAGE_ENVELOPE_RESERVE_BYTES",
    "SCRIPT_PUT_WORK_ITEM",
    "SCRIPT_UPDATE_WORK_ITEM",
    "HISTORY_MAX_ENV",
    "SessionStore",
    "WorkItemPutResult",
    "configure_session_env",
    "resolve_history_max",
]
