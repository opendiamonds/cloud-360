"""
work_orchestrator.py — `U12 work-orchestrator`：把路由結果落成工作項並執行

**契約（`U13 brain-gateway` 同進程依賴，請勿變更；契約 `K-11` 與 functional-spec 2.1 的增量）**

| 方法 | 用途 |
|---|---|
| `dispatch(principal, session, decision, *, utterance, segment_id, turn_id, bearer_token, sink)` | 每個意圖建一個工作項、**先回覆**（本輪 turnId）、再在背景執行；回傳建立當下的集合 |
| `correct(principal, session_key, work_item_id, *, bearer_token, sink)` | 逐項停掉（`BR55`） |
| `list_items(principal, session_key, *, bearer_token, sink)` | 先做復原掃描（`BR56.7`）再回傳集合 |

`sink` 由 `U13` 實作三個方法（可為同步或 async）：`emit_session(WorkItemsPayload)`
（非輪次，turnId 為 null）、`emit_in_turn(turn_id, [TokenPayload…])`（使用者本輪）、
`emit_turn([TokenPayload|CostCardPayload…])`（伺服器發起的新輪次，`U13` 產生
turnId 並以 `done` 終止；`BR58.5`）。本模組送出的**每一則**訊息都先以
`brain_ws_contract` 的模型驗證過（`NFR12.27`），sink 收到的一律是模型實例。

## 本模組的禁令（皆有測試鎖住）

1. **不直呼既有能力**（`BR51.1`；`X-01`／`X-02`；`NFR12.8`）：A1／A3／C1 一律經
   `work_orchestrator_capabilities.CapabilityClient`——同進程 ASGI 傳輸、帶使用者
   本人的 token、完整走過既有端點的授權 dependency。不 import `main`
   （`app` 由 `U13` 傳入）。
2. **不呼叫任何 LLM**（`[WO1]`=A；`NFR12.5`）：回覆一律取自
   `work_orchestrator_rules.PHRASES`。
3. **token 不落地**（`BR51.2`；`NFR12.6`）：只以參數傳遞，不進工作項、不進 log。
   log 只記 workItemId、能力、狀態、dispatchStage 與失敗類別（`NFR12.24`–`NFR12.26`），
   不記 `requestText`、label 或例外原文。

## 正確性的三個機制

- **比對後寫入**（`BR52.7`）：每一次更新都比對 `status` 與 `dispatchStage`，以
  **補丁**合併（`SessionStore.update_work_item`）。所有寫入經 `_cas`；寫入結果
  未知（連線錯誤）時重讀確認（帶入項 19）。
- **先記錄、再送出**（`NFR12.21`）：送出 A1／A3／PUT 之前，先把要進入的
  `dispatchStage` 寫成功；寫不進去（被停掉或被搶先）就不送。
- **寫入成功者才有副作用**（`NFR12.13`）：所有「推進並啟動」經 `_advance`，只有
  比對後寫入回 True 的呼叫者才建 task、送訊息。

## 時間

`clock`（回 aware UTC `datetime`）與 `sleep` 由建構子注入（帶入項 13、20）。三種
能力的牆鐘上限一律以 `clock() >= deadlineAt` 自行判定：背景執行由 `_run` 的看門
迴圈以 `sleep` 切片檢查，不用 `asyncio.wait_for`（它用的是事件迴圈的單調時鐘，
測試無法推進）。成本輪詢每圈先比對同一個 `deadlineAt`；每次快照 GET 計一次輪詢。

## 在途存檔（`BR55.7`；帶入項 1、11、18、23）

PUT 與其後的收尾包成 `_finish_persist`，以 `asyncio.shield` 保護、**自建獨立的
`CapabilityClient`**、自有最外層例外處理與 60 秒 PUT 上限。`correct` 或逾時取消
`_run` 時，收尾照常跑完，並依當下儲存的狀態如實記錄（`reliability-design.md`
第二節的四列）。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Optional
from uuid import uuid4

from models import User
from services.brain_ws_contract import (
    CostCardPayload,
    TokenPayload,
    WorkItem,
    WorkItemsPayload,
)
from services.hierarchy_facade import (
    HierarchyFacade,
    HierarchyForbidden,
    HierarchyNotFound,
    mint_principal,
)
from services.intent_routing_types import ROUTABLE_CAPABILITIES
from services.memory_facade import MemoryFacade
from services.session_errors import SessionBackendUnavailable
from services.work_orchestrator_capabilities import (
    ADVICE_COMPLETED,
    ADVICE_TIMEOUT,
    ADVICE_FAILED,
    KIND_HTTP,
    CapabilityClient,
    CapabilityError,
    judge_advice_snapshot,
)
from services import work_orchestrator_rules as R

logger = logging.getLogger("cloud360.work_orchestrator")

#: `correct` 比對失敗時的重讀重算上限（帶入項 24）。
MAX_CAS_ATTEMPTS = 5
#: `BR57.1`：成本輪詢間隔。
POLL_INTERVAL_SECONDS = 2.0
#: 看門迴圈的切片長度（只影響判定逾時的解析度，不影響上限本身）。
WATCHDOG_TICK_SECONDS = 0.5
#: 在途存檔的 PUT 上限（帶入項 23）。
PERSIST_TIMEOUT_SECONDS = 60.0
#: `BR52.6`：`requestText` 取原句前 2000 字。
REQUEST_TEXT_MAX_CHARS = 2000
#: `BR51.4`：變更紀錄的需求摘要取前 200 字。
CHANGE_SUMMARY_MAX_CHARS = 200
#: `BR53.1` 的封閉集合沿用路由層的能力清單，不另抄一份。
_ROUTABLE = frozenset(ROUTABLE_CAPABILITIES)


class WorkItemNotFound(LookupError):
    """`BR55.6`：指定的工作項不在該工作階段。"""

    def __init__(self, work_item_id: str) -> None:
        super().__init__(f"找不到工作項 {work_item_id}")
        self.work_item_id = work_item_id


class _UserDisabled(Exception):
    """`BR51.7`：重新自 DB 取使用者時，使用者不存在或已停用。"""


class _StepAborted(Exception):
    """比對後寫入回 False：工作項已被停掉或被別人推進，整條背景執行中止（`BR55.3`）。"""


class _Failed(Exception):
    """背景執行的一步失敗：帶固定句型的原因與失敗類別（`observability-design.md`）。"""

    def __init__(self, reason: str, category: str, *, side_effect: Optional[str] = None) -> None:
        super().__init__(category)
        self.reason = reason
        self.category = category
        self.side_effect = side_effect


@dataclass(frozen=True)
class _Ctx:
    """一條背景執行的上下文。token 只存在這裡（記憶體），用完即棄（`BR51.2`）。"""

    session_key: str
    item_id: str
    user_id: int
    token: str
    sink: Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _public(item: dict) -> dict:
    """伺服器內部欄位不送前端：只取 `brain_ws_contract.WorkItem` 的七個欄位。"""
    return {
        "workItemId": item["workItemId"],
        "label": item["label"],
        "status": item["status"],
        "capability": item["capability"],
        "waitingOn": item.get("waitingOn"),
        "failureReason": item.get("failureReason"),
        "sideEffect": item.get("sideEffect") or R.SIDE_EFFECT_NONE,
    }


def _sorted(items: Iterable[dict]) -> list:
    return sorted(items, key=lambda i: (i.get("createdAt") or "", i.get("dispatchIndex") or 0))


def _diagram_name(item: dict) -> str:
    return R.diagram_display_name(item.get("targetDiagramTitle"), item.get("targetDiagramId"))


class WorkOrchestrator:
    """`K-11` 的落點。每個 `U13` 進程一個實例；狀態全在 Redis，實例只持有 task 參考。"""

    def __init__(
        self,
        app: Any,
        session_store: Any,
        *,
        clock: Callable[[], datetime] = _utc_now,
        sleep: Callable[[float], Any] = asyncio.sleep,
        session_factory: Optional[Callable[[], Any]] = None,
        hierarchy_facade_factory: Callable[[Any], Any] = HierarchyFacade,
        memory_facade_factory: Callable[[Any], Any] = MemoryFacade,
        mint: Callable[[Any], Any] = mint_principal,
        user_model: Any = User,
        capability_client_factory: Callable[[Any, str], Any] = CapabilityClient,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        watchdog_tick: float = WATCHDOG_TICK_SECONDS,
        persist_timeout: float = PERSIST_TIMEOUT_SECONDS,
    ) -> None:
        self._app = app
        self._store = session_store
        self._clock = clock
        self._sleep = sleep
        self._session_factory = session_factory
        self._hierarchy_factory = hierarchy_facade_factory
        self._memory_factory = memory_facade_factory
        self._mint = mint
        self._user_model = user_model
        self._client_factory = capability_client_factory
        self._poll_interval = poll_interval
        self._tick = watchdog_tick
        self._persist_timeout = persist_timeout
        #: workItemId → `_run` task（`performance-design.md` 第一節）。
        self._tasks: dict = {}
        #: 在途存檔的收尾 task（被 shield 保護，獨立於 `_run`）。
        self._persist_tasks: set = set()

    # ==================================================================
    # 公開方法
    # ==================================================================

    async def dispatch(
        self,
        principal: Any,
        session: Any,
        decision: Any,
        *,
        utterance: str,
        segment_id: str,
        turn_id: str,
        bearer_token: str,
        sink: Any,
    ) -> list:
        """交辦（functional-spec 3.1）。**不等待任何能力**即回傳（`NFR12.1`）。"""
        session_key = session.session_key
        user_id = principal.user_id
        await self._recover(session_key, user_id, bearer_token, sink)
        if decision.below_threshold:
            return []  # BR52.1：反問由 U11／U13 處理
        segment = (session.segments or {}).get(segment_id)
        if segment is None:
            raise ValueError(f"段 {segment_id!r} 不在這個工作階段內（BR52.6）")
        capabilities = [intent.capability for intent in decision.intents]
        unknown = [c for c in capabilities if c not in _ROUTABLE]
        if unknown:
            raise ValueError(f"不可路由的能力：{unknown}")

        items = self._build_items(
            session_key, segment, segment_id, capabilities, (utterance or "")
        )
        for item in items:
            if not self._store.put_work_item(session_key, item):
                # BR52.4：key 已到期——由 U13 依既有的工作階段失效路徑處理。
                raise ValueError("工作階段已到期，無法建立工作項（BR52.4）")
            self._log_transition(item, None, item["status"])

        await self._push_items(sink, session_key)
        texts = []
        for item in items:
            if item["status"] == R.STATUS_WAITING:
                texts.append(
                    R.PHRASES["waiting"].format(
                        label=item["label"], waiting_label=item["waitingOn"]
                    )
                )
            else:
                texts.append(
                    R.PHRASES["created"].format(
                        capability=R.capability_name(item["capability"]),
                        target=item["targetDisplay"],
                    )
                )
        await self._emit("in_turn", sink, turn_id, [self._token(t) for t in texts])

        for item in items:
            if item["status"] == R.STATUS_PROCESSING:
                self._start(
                    _Ctx(session_key, item["workItemId"], user_id, bearer_token, sink)
                )
        return [WorkItem.model_validate(_public(i)) for i in items]

    async def correct(
        self,
        principal: Any,
        session_key: str,
        work_item_id: str,
        *,
        bearer_token: str,
        sink: Any,
    ) -> WorkItem:
        """逐項停掉（functional-spec 3.2；`BR55`）。"""
        user_id = principal.user_id
        await self._recover(session_key, user_id, bearer_token, sink)
        for _attempt in range(MAX_CAS_ATTEMPTS):
            item = self._store.load_work_items(session_key).get(work_item_id)
            if item is None:
                raise WorkItemNotFound(work_item_id)
            if item["status"] in R.TERMINAL_STATUSES:
                return WorkItem.model_validate(_public(item))  # BR55.2：no-op
            new_status = R.transition(item["status"], R.EV_USER_CORRECTED)
            patch = {
                "status": new_status,
                "sideEffect": R.side_effect_on_stop(
                    item["capability"], item["dispatchStage"], diagram_name=_diagram_name(item)
                ),
                "deadlineAt": None,
                "waitingOn": None,
                "dependsOn": None,
            }
            if self._cas(session_key, item, R.ACTIVE_STATUSES, patch):
                break
        else:
            logger.warning("work_item=%s correct_cas_exhausted", work_item_id)
            current = self._store.load_work_items(session_key).get(work_item_id)
            if current is None:
                raise WorkItemNotFound(work_item_id)
            return WorkItem.model_validate(_public(current))

        self._log_transition(item, item["status"], new_status)
        task = self._tasks.get(work_item_id)
        if task is not None:
            # 已送出的請求無法取消，由 sideEffect 揭露；在途存檔被 shield 保護。
            task.cancel()
        updated = {**item, **patch}
        await self._push_items(sink, session_key)
        await self._emit(
            "turn", sink, [self._token(R.PHRASES["stopped"].format(label=item["label"]))]
        )
        ctx = _Ctx(session_key, work_item_id, user_id, bearer_token, sink)
        await self._advance_dependents(ctx, updated)
        return WorkItem.model_validate(_public(updated))

    async def list_items(
        self, principal: Any, session_key: str, *, bearer_token: str, sink: Any
    ) -> list:
        """先做復原掃描（`BR56.7`），再回傳集合。"""
        await self._recover(session_key, principal.user_id, bearer_token, sink)
        items = self._store.load_work_items(session_key)
        return [WorkItem.model_validate(_public(i)) for i in _sorted(items.values())]

    # ==================================================================
    # 建立
    # ==================================================================

    def _build_items(self, session_key, segment, segment_id, capabilities, utterance) -> list:
        waits = R.plan_waits(capabilities)
        now = self._clock()
        target = R.target_display(segment.diagram_id, segment.system_id, segment.project_id)
        items: list = []
        for index, capability in enumerate(capabilities):
            wait_index = waits[index]
            waiting = wait_index is not None
            depended = items[wait_index] if waiting else None
            items.append(
                {
                    "workItemId": str(uuid4()),
                    "sessionKey": session_key,
                    "label": R.make_label(capability, target),
                    "status": R.STATUS_WAITING if waiting else R.STATUS_PROCESSING,
                    "capability": capability,
                    "waitingOn": depended["label"] if waiting else None,
                    "failureReason": None,
                    "sideEffect": R.SIDE_EFFECT_NONE,
                    "createdAt": _iso(now),
                    "estimateSetId": None,
                    "dependsOn": depended["workItemId"] if waiting else None,
                    "targetDiagramId": segment.diagram_id,
                    "targetSystemId": segment.system_id,
                    "targetDiagramTitle": None,
                    "targetDisplay": target,
                    "segmentId": segment_id,
                    "deadlineAt": None if waiting else self._deadline_iso(capability, now),
                    "dispatchStage": R.STAGE_NOT_DISPATCHED,
                    "requestText": utterance[:REQUEST_TEXT_MAX_CHARS],
                    "dispatchIndex": index,
                }
            )
        return items

    def _deadline_iso(self, capability: str, now: Optional[datetime] = None) -> str:
        base = now if now is not None else self._clock()
        return _iso(base + timedelta(seconds=R.DEADLINE_SECONDS[capability]))

    # ==================================================================
    # 比對後寫入與推進（`BR52.7`；`NFR12.13`；帶入項 19）
    # ==================================================================

    def _cas(self, session_key: str, item: dict, statuses, patch: dict) -> bool:
        """以 `item` 的 `dispatchStage` 為預期值比對後寫入。

        寫入時遇 `SessionBackendUnavailable`（結果未知）：重讀該項，若補丁的每個
        欄位都已是目標值，視為成功；讀不到則**不做副作用**並記 WARNING。
        """
        try:
            return self._store.update_work_item(
                session_key,
                item["workItemId"],
                list(statuses),
                item["dispatchStage"],
                patch,
            )
        except SessionBackendUnavailable:
            try:
                current = self._store.load_work_items(session_key).get(item["workItemId"])
            except SessionBackendUnavailable:
                logger.warning("work_item=%s cas_result_unknown", item["workItemId"])
                return False
            applied = current is not None and all(
                current.get(name) == value for name, value in patch.items()
            )
            if not applied:
                logger.warning("work_item=%s cas_result_unknown_not_applied", item["workItemId"])
            return applied

    async def _advance(
        self, session_key: str, item: dict, statuses, patch: dict, then=None
    ) -> bool:
        """所有「推進並啟動」的唯一入口：**只有寫入成功者**才執行 `then`。"""
        ok = self._cas(session_key, item, statuses, patch)
        if ok and then is not None:
            await then()
        return ok

    # ==================================================================
    # 復原掃描（`BR56.7`）與等待者推進（`BR53.2`–`BR53.4`）
    # ==================================================================

    async def _recover(self, session_key: str, user_id: int, token: str, sink: Any) -> None:
        now = self._clock()
        items = self._store.load_work_items(session_key)
        for item in _sorted(items.values()):
            deadline = _parse_iso(item.get("deadlineAt"))
            if item["status"] != R.STATUS_PROCESSING or deadline is None or now < deadline:
                continue
            ctx = _Ctx(session_key, item["workItemId"], user_id, token, sink)
            await self._fail_item(
                ctx,
                item,
                R.PHRASES["expired_on_recovery"],
                "expired_on_recovery",
                advance_dependents=False,  # 第 (2) 步統一處理孤兒等待
                cancel_run=True,  # 外部呼叫者：本行程若還有它的背景執行，一併停掉
            )
        items = self._store.load_work_items(session_key)
        for waiter in _sorted(items.values()):
            if waiter["status"] != R.STATUS_WAITING:
                continue
            dependency = items.get(waiter.get("dependsOn"))
            dependency_status = dependency["status"] if dependency else R.STATUS_FAILED
            if dependency_status not in R.TERMINAL_STATUSES:
                continue
            ctx = _Ctx(session_key, waiter["workItemId"], user_id, token, sink)
            await self._advance_waiter(ctx, waiter, dependency_status, dependency)

    async def _advance_dependents(self, ctx: _Ctx, item: dict) -> None:
        """`item` 剛轉為終態：推進等待它的工作項。"""
        items = self._store.load_work_items(ctx.session_key)
        for waiter in _sorted(items.values()):
            if waiter["status"] != R.STATUS_WAITING or waiter.get("dependsOn") != item["workItemId"]:
                continue
            waiter_ctx = _Ctx(ctx.session_key, waiter["workItemId"], ctx.user_id, ctx.token, ctx.sink)
            await self._advance_waiter(waiter_ctx, waiter, item["status"], item)

    async def _advance_waiter(
        self, ctx: _Ctx, waiter: dict, dependency_status: str, dependency: Optional[dict]
    ) -> bool:
        event = R.event_for_dependency_terminal(waiter["capability"], dependency_status)
        new_status = R.transition(R.STATUS_WAITING, event)
        dependency_label = (dependency or {}).get("label") or waiter.get("waitingOn") or ""
        cleared = {"waitingOn": None, "dependsOn": None}

        if new_status == R.STATUS_PROCESSING:
            patch = {"status": new_status, "deadlineAt": self._deadline_iso(waiter["capability"]), **cleared}

            async def then():
                self._log_transition(waiter, R.STATUS_WAITING, new_status)
                await self._push_items(ctx.sink, ctx.session_key)
                self._start(ctx)

        elif new_status == R.STATUS_FAILED:
            reason = R.PHRASES["dependency_failed"].format(dependency_label=dependency_label)
            patch = {
                "status": new_status,
                "failureReason": reason,
                "sideEffect": R.SIDE_EFFECT_NONE,
                "deadlineAt": None,
                **cleared,
            }

            async def then():
                self._log_transition(waiter, R.STATUS_WAITING, new_status)
                logger.warning("work_item=%s failure=%s", waiter["workItemId"], "dependency_failed")
                await self._push_items(ctx.sink, ctx.session_key)
                await self._emit("turn", ctx.sink, [self._token(
                    R.PHRASES["failed"].format(label=waiter["label"], reason=reason)
                )])

        else:  # 已停掉：被等待者停掉而本項為檢視（BR53.4）
            patch = {
                "status": new_status,
                "sideEffect": R.SIDE_EFFECT_NONE,
                "deadlineAt": None,
                **cleared,
            }

            async def then():
                self._log_transition(waiter, R.STATUS_WAITING, new_status)
                await self._push_items(ctx.sink, ctx.session_key)
                await self._emit("turn", ctx.sink, [self._token(
                    R.PHRASES["skipped"].format(
                        label=waiter["label"], dependency_label=dependency_label
                    )
                )])

        return await self._advance(ctx.session_key, waiter, [R.STATUS_WAITING], patch, then)

    # ==================================================================
    # 背景執行（functional-spec 3.3）
    # ==================================================================

    def _start(self, ctx: _Ctx) -> None:
        task = asyncio.create_task(self._run(ctx))
        self._tasks[ctx.item_id] = task

        def _forget(done: asyncio.Task) -> None:
            if self._tasks.get(ctx.item_id) is done:
                self._tasks.pop(ctx.item_id, None)

        task.add_done_callback(_forget)

    def _all_tasks(self) -> list:
        return list(self._tasks.values()) + list(self._persist_tasks)

    async def _wait_slice(self, task: asyncio.Task) -> None:
        """等 `task` 結束或一個 `sleep` 切片過去，先到者為準。"""
        ticker = asyncio.ensure_future(self._sleep(self._tick))
        try:
            await asyncio.wait({task, ticker}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            if not ticker.done():
                ticker.cancel()

    async def _run(self, ctx: _Ctx) -> None:
        """看門迴圈：以注入的 `clock` 判定 `deadlineAt`（`BR56.6`；帶入項 20）。"""
        inner: Optional[asyncio.Task] = None
        try:
            item = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
            if item is None or item["status"] != R.STATUS_PROCESSING:
                return
            deadline = _parse_iso(item.get("deadlineAt"))
            inner = asyncio.ensure_future(self._execute(ctx, item))
            while not inner.done():
                if deadline is not None and self._clock() >= deadline:
                    # 每次越過 deadline 先重讀（審查 R-03）：項目已因完成／失敗的比對後
                    # 寫入離開處理中時，內層正在做收尾（記憶、推送、訊息、推進等待者），
                    # 不得取消它——不再設 deadline，等它自己結束。
                    latest = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
                    if latest is None or latest["status"] != R.STATUS_PROCESSING:
                        deadline = None
                        continue
                    inner.cancel()
                    await asyncio.gather(inner, return_exceptions=True)
                    current = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
                    if current is not None and current["status"] == R.STATUS_PROCESSING:
                        await self._fail_item(
                            ctx,
                            current,
                            self._timeout_reason(current["capability"]),
                            "timeout",
                        )
                    return
                await self._wait_slice(inner)
            inner.result()
        except asyncio.CancelledError:
            if inner is not None and not inner.done():
                inner.cancel()
            raise
        except Exception as exc:  # noqa: BLE001 - 背景 task 的最外層：不得留下未處理例外
            logger.error("work_item=%s run_failed error=%s", ctx.item_id, type(exc).__name__)
            await self._fail_current(ctx, "unavailable_fallback")

    @staticmethod
    def _timeout_reason(capability: str) -> str:
        if capability == R.CAP_COST:
            return R.PHRASES["cost_timeout"]
        return R.PHRASES["timeout"].format(capability=R.capability_name(capability))

    async def _fail_current(self, ctx: _Ctx, _kind: str) -> None:
        """最外層例外的收尾：工作項失敗「〈能力名稱〉暫時無法使用」。失敗也只記 log。"""
        try:
            current = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
            if current is not None and current["status"] == R.STATUS_PROCESSING:
                await self._fail_item(
                    ctx,
                    current,
                    R.PHRASES["unavailable"].format(
                        capability=R.capability_name(current["capability"])
                    ),
                    "capability_failed",
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("work_item=%s fail_unrecorded error=%s", ctx.item_id, type(exc).__name__)

    async def _execute(self, ctx: _Ctx, item: dict) -> None:
        try:
            capability = item["capability"]
            if capability == R.CAP_ARCHITECTURE:
                await self._execute_architecture(ctx, item)
            elif capability == R.CAP_REVIEW:
                await self._execute_review(ctx, item)
            else:
                await self._execute_cost(ctx, item)
        except _StepAborted:
            return
        except _Failed as failed:
            current = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
            if current is not None and current["status"] == R.STATUS_PROCESSING:
                await self._fail_item(
                    ctx, current, failed.reason, failed.category, side_effect=failed.side_effect
                )

    # -- 能力：架構設計（`BR56.1`）---------------------------------------

    async def _execute_architecture(self, ctx: _Ctx, item: dict) -> None:
        capability = item["capability"]
        diagram_id = await self._resolve_single_diagram(ctx, item)
        try:
            async with self._client_factory(self._app, ctx.token) as client:
                diagram = await client.get_diagram(diagram_id)
                title = diagram.get("title") or ""
                item = self._step(
                    ctx,
                    item,
                    {
                        "dispatchStage": R.STAGE_REQUEST_SENT,
                        "targetDiagramId": diagram_id,
                        "targetDiagramTitle": title,
                    },
                )
                result = await client.generate_architecture(
                    item.get("requestText") or "", diagram.get("xml_data")
                )
                if result.message_text.strip():
                    # BR58.3：A1 的說明文字在回應結束後一次轉送。
                    await self._emit("turn", ctx.sink, [self._token(result.message_text)])
                if result.failure:
                    raise _Failed(R.PHRASES[result.failure], "capability_failed")
                again = await client.get_diagram(diagram_id)
                if again.get("updated_at") != diagram.get("updated_at"):
                    raise _Failed(R.PHRASES["diagram_modified"], "capability_failed")
        except CapabilityError as exc:
            raise self._capability_failure(capability, exc) from None

        # 存回之前再次確認使用者仍有效（BR51.7；NFR12.9 的第一案）。
        try:
            await self._call_facade(ctx.user_id, lambda principal, db: None)
        except _UserDisabled:
            raise _Failed(
                R.PHRASES["forbidden"].format(capability=R.capability_name(capability)),
                "forbidden",
            ) from None

        item = self._step(ctx, item, {"dispatchStage": R.STAGE_PERSISTING})
        persist = asyncio.ensure_future(
            self._finish_persist(ctx, item, diagram_id, title, result.xml)
        )
        self._persist_tasks.add(persist)
        persist.add_done_callback(self._persist_tasks.discard)
        await asyncio.shield(persist)

    def _step(self, ctx: _Ctx, item: dict, patch: dict) -> dict:
        """先記錄、再送出（`NFR12.21`）：寫不進去即中止，不送請求。"""
        if not self._cas(ctx.session_key, item, [R.STATUS_PROCESSING], patch):
            raise _StepAborted()
        return {**item, **patch}

    async def _finish_persist(
        self, ctx: _Ctx, item: dict, diagram_id: int, title: str, xml: str
    ) -> None:
        """在途存檔的收尾（`reliability-design.md` 第二節的四列）。被 shield 保護。"""
        try:
            outcome, status_code = await self._put_with_timeout(ctx, diagram_id, title, xml)
            name = R.diagram_display_name(title, diagram_id)
            if outcome is True:
                recorded = await self._record_change(ctx, item, diagram_id)
                side = R.PHRASES["side_effect_persisted"].format(name=name)
                if not recorded:
                    side = R.PHRASES["side_effect_change_record_missing"].format(side_effect=side)
                await self._settle_persisted(ctx, side)
            elif outcome is False:
                await self._settle_put_failed(ctx, status_code)
            else:
                await self._settle_put_unknown(ctx)
        except Exception as exc:  # noqa: BLE001 - 收尾自有的最外層例外處理（帶入項 23）
            logger.error("work_item=%s persist_failed error=%s", ctx.item_id, type(exc).__name__)

    async def _put_with_timeout(self, ctx: _Ctx, diagram_id: int, title: str, xml: str):
        """自建獨立的 client（帶入項 18）；PUT 上限以注入的 clock 判定。

        回傳 `(True, None)` 成功、`(False, status)` 明確失敗、`(None, None)` 結果未知。
        """

        async def put() -> None:
            async with self._client_factory(self._app, ctx.token) as client:
                await client.put_diagram(diagram_id, title=title, xml_data=xml)

        task = asyncio.ensure_future(put())
        deadline = self._clock() + timedelta(seconds=self._persist_timeout)
        while not task.done():
            if self._clock() >= deadline:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                logger.warning("work_item=%s persist_put_timeout", ctx.item_id)
                return None, None
            await self._wait_slice(task)
        try:
            task.result()
        except CapabilityError as exc:
            if exc.kind == KIND_HTTP:
                return False, exc.status_code
            return None, None
        return True, None

    async def _settle_persisted(self, ctx: _Ctx, side_effect: str) -> None:
        for _attempt in range(MAX_CAS_ATTEMPTS):
            current = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
            if current is None or current["dispatchStage"] != R.STAGE_PERSISTING:
                return
            status = current["status"]
            patch = {"dispatchStage": R.STAGE_RESULT_PERSISTED, "sideEffect": side_effect}
            if not self._cas(ctx.session_key, current, [status], patch):
                continue
            updated = {**current, **patch}
            if status == R.STATUS_PROCESSING:
                await self._complete(
                    ctx,
                    updated,
                    {},
                    [self._token(R.PHRASES["done"].format(label=current["label"]))],
                )
            else:
                # BR55.7（含逾時判失敗後 PUT 才成功）：狀態不改、不寫記憶、不送完成訊息。
                await self._push_items(ctx.sink, ctx.session_key)
            return

    async def _settle_put_failed(self, ctx: _Ctx, status_code: Optional[int]) -> None:
        current = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
        if current is None:
            return
        if current["status"] == R.STATUS_PROCESSING:
            reason, category = R.failure_for_status(current["capability"], status_code)
            await self._fail_item(ctx, current, reason, category, side_effect=R.SIDE_EFFECT_NONE)
            return
        if self._cas(ctx.session_key, current, [current["status"]], {"sideEffect": R.SIDE_EFFECT_NONE}):
            await self._push_items(ctx.sink, ctx.session_key)

    async def _settle_put_unknown(self, ctx: _Ctx) -> None:
        current = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
        if current is not None and current["status"] == R.STATUS_PROCESSING:
            await self._fail_item(ctx, current, self._timeout_reason(current["capability"]), "timeout")
        # 已停掉／已失敗：sideEffect 已是「可能已存回…」，如實維持。

    async def _record_change(self, ctx: _Ctx, item: dict, diagram_id: int) -> bool:
        """`BR51.4`：寫一列變更紀錄；失敗（含存回後停用、非擁有者）只記 log。"""
        summary = (item.get("requestText") or "")[:CHANGE_SUMMARY_MAX_CHARS] or item["label"]

        def write(principal, db):
            self._hierarchy_factory(db).record_diagram_change(
                principal,
                diagram_id=diagram_id,
                requirement_summary=summary,
                requirement_label=item["label"],
                actor_user_id=principal.user_id,
            )

        try:
            await self._call_facade(ctx.user_id, write)
            return True
        except Exception as exc:  # noqa: BLE001 - BR51.4／BR51.8 的 violation_behaviour
            logger.warning("work_item=%s change_record_failed error=%s", ctx.item_id, type(exc).__name__)
            return False

    # -- 能力：架構檢視（`BR56.2`）---------------------------------------

    async def _execute_review(self, ctx: _Ctx, item: dict) -> None:
        capability = item["capability"]
        diagram_id = await self._resolve_single_diagram(ctx, item)
        item = self._step(
            ctx, item, {"dispatchStage": R.STAGE_REQUEST_SENT, "targetDiagramId": diagram_id}
        )
        try:
            async with self._client_factory(self._app, ctx.token) as client:
                result = await client.start_review(diagram_id)
        except CapabilityError as exc:
            raise self._capability_failure(capability, exc) from None
        if result.failure:
            raise _Failed(R.PHRASES[result.failure], "capability_failed")
        summary = R.PHRASES["done_review"].format(
            score=result.overall_score, count=result.findings_count
        )
        await self._complete(
            ctx,
            item,
            {
                "dispatchStage": R.STAGE_RESULT_PERSISTED,
                "sideEffect": R.PHRASES["side_effect_review_created"],
            },
            [self._token(summary)],
        )

    # -- 能力：成本分析（`BR56.3`／`BR57`）-------------------------------

    async def _execute_cost(self, ctx: _Ctx, item: dict) -> None:
        capability = item["capability"]
        deadline = _parse_iso(item.get("deadlineAt"))
        diagram_ids = await self._resolve_diagram_set(ctx, item)
        try:
            async with self._client_factory(self._app, ctx.token) as client:
                found = await client.find_latest_estimate_set(diagram_ids)
                if found is None:
                    raise _Failed(R.PHRASES["cost_no_estimate"], "target_unresolved")
                set_id = int(found["id"])
                item = self._step(ctx, item, {"estimateSetId": set_id})
                if found.get("advice_status") == "none":
                    raise _Failed(
                        R.PHRASES["cost_no_advice"].format(path=R.cost_page_url(set_id)),
                        "target_unresolved",
                    )
                snapshot = await self._poll_advice(client, set_id, deadline)
        except CapabilityError as exc:
            raise self._capability_failure(capability, exc) from None

        card = CostCardPayload.model_validate(
            {
                "estimateSetId": item["estimateSetId"],
                "savingText": snapshot.get("saving_text"),
                "comparisonText": snapshot.get("comparison_text"),
                "qualityText": snapshot.get("quality_text"),
                "unavailableReasons": snapshot.get("unavailable_reasons"),
                "costPageUrl": R.cost_page_url(item["estimateSetId"]),
            }
        )
        await self._complete(
            ctx,
            item,
            {},
            [self._token(R.PHRASES["done_cost"].format(label=item["label"])), card],
        )

    async def _poll_advice(self, client: Any, set_id: int, deadline: Optional[datetime]) -> dict:
        """`BR57.1`／`BR57.2`／`BR57.4`：每 2 秒讀一次快照；生成中不推送、不送訊息。"""
        consecutive_failures = 0
        while True:
            if deadline is not None and self._clock() >= deadline:
                raise _Failed(R.PHRASES["cost_timeout"], "timeout")
            try:
                snapshot = await client.get_advice_snapshot(set_id)
            except CapabilityError as exc:
                if exc.kind == KIND_HTTP and exc.status_code in (401, 403):
                    raise
                if exc.kind == KIND_HTTP and exc.status_code == 404:
                    raise _Failed(R.PHRASES["cost_not_found"], "not_found") from None
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    raise _Failed(R.PHRASES["connection_lost"], "connection_lost") from None
                await self._sleep(self._poll_interval)
                continue
            consecutive_failures = 0
            verdict = judge_advice_snapshot(snapshot, self._clock())
            if verdict == ADVICE_COMPLETED:
                return snapshot
            if verdict == ADVICE_TIMEOUT:
                raise _Failed(R.PHRASES["cost_timeout"], "timeout")
            if verdict == ADVICE_FAILED:
                raise _Failed(R.PHRASES["cost_failed"], "capability_failed")
            await self._sleep(self._poll_interval)

    # -- 目標圖解析 ------------------------------------------------------

    async def _list_system_diagrams(self, ctx: _Ctx, item: dict, system_id: int) -> list:
        def read(principal, db):
            return self._hierarchy_factory(db).list_diagrams_of_system(principal, system_id=system_id)

        try:
            return await self._call_facade(ctx.user_id, read)
        except _UserDisabled:
            raise _Failed(
                R.PHRASES["forbidden"].format(capability=R.capability_name(item["capability"])),
                "forbidden",
            ) from None
        except (HierarchyNotFound, HierarchyForbidden):
            # BR51.8：被擁有者範圍拒絕 → 依 BR56.1 的「找不到可用的圖」失敗。
            raise _Failed(R.PHRASES["system_no_diagram"], "target_unresolved") from None

    async def _resolve_single_diagram(self, ctx: _Ctx, item: dict) -> int:
        plan = R.plan_target(item.get("targetDiagramId"), item.get("targetSystemId"))
        if plan.kind == R.TARGET_DIAGRAM:
            return plan.diagram_id
        if plan.kind == R.TARGET_NONE:
            raise _Failed(R.PHRASES["no_target"], "target_unresolved")
        diagrams = await self._list_system_diagrams(ctx, item, plan.system_id)
        diagram_id, error = R.pick_single_diagram(diagrams)
        if error is not None:
            raise _Failed(R.PHRASES[error], "target_unresolved")
        return diagram_id

    async def _resolve_diagram_set(self, ctx: _Ctx, item: dict) -> set:
        plan = R.plan_target(item.get("targetDiagramId"), item.get("targetSystemId"))
        if plan.kind == R.TARGET_DIAGRAM:
            return {plan.diagram_id}
        if plan.kind == R.TARGET_NONE:
            raise _Failed(R.PHRASES["no_target"], "target_unresolved")
        diagrams = await self._list_system_diagrams(ctx, item, plan.system_id)
        if not diagrams:
            raise _Failed(R.PHRASES["system_no_diagram"], "target_unresolved")
        return {int(d[0]) for d in diagrams}

    @staticmethod
    def _capability_failure(capability: str, exc: CapabilityError) -> _Failed:
        status_code = exc.status_code if exc.kind == KIND_HTTP else None
        reason, category = R.failure_for_status(capability, status_code)
        return _Failed(reason, category)

    # ==================================================================
    # 終態寫入
    # ==================================================================

    async def _fail_item(
        self,
        ctx: _Ctx,
        item: dict,
        reason: str,
        category: str,
        *,
        side_effect: Optional[str] = None,
        advance_dependents: bool = True,
        cancel_run: bool = False,
    ) -> bool:
        """處理中 → 失敗。sideEffect 預設取 `side_effect_on_stop`（`BR56.6`／`BR56.7`）。

        `cancel_run` 只給**外部**呼叫者（復原掃描）用。背景執行自己走到失敗時（`_Failed`
        路徑、看門迴圈、在途存檔收尾）**不得**取消 `_run`：`_run` 是本條執行鏈的外層，
        取消它會在下一個讓出事件迴圈的 await 截斷本方法剩下的推送、失敗訊息與等待者推進
        （審查 R-01）。內層在本方法返回後本來就會結束。若要取消，也延到所有副作用之後。
        """
        current = item
        for _attempt in range(MAX_CAS_ATTEMPTS):
            if current is None or current["status"] != R.STATUS_PROCESSING:
                return False
            new_status = R.transition(R.STATUS_PROCESSING, R.EV_CAPABILITY_FAILED)
            patch = {
                "status": new_status,
                "failureReason": reason,
                "sideEffect": side_effect
                if side_effect is not None
                else R.side_effect_on_stop(
                    current["capability"], current["dispatchStage"], diagram_name=_diagram_name(current)
                ),
                "deadlineAt": None,
            }
            if self._cas(ctx.session_key, current, [R.STATUS_PROCESSING], patch):
                updated = {**current, **patch}
                self._log_transition(current, R.STATUS_PROCESSING, new_status)
                logger.warning("work_item=%s failure=%s", ctx.item_id, category)
                await self._push_items(ctx.sink, ctx.session_key)
                await self._emit("turn", ctx.sink, [self._token(
                    R.PHRASES["failed"].format(label=current["label"], reason=reason)
                )])
                if advance_dependents:
                    await self._advance_dependents(ctx, updated)
                if cancel_run:
                    task = self._tasks.get(ctx.item_id)
                    if task is not None and task is not asyncio.current_task():
                        task.cancel()
                return True
            current = self._store.load_work_items(ctx.session_key).get(ctx.item_id)
        logger.warning("work_item=%s fail_cas_exhausted", ctx.item_id)
        return False

    async def _complete(self, ctx: _Ctx, item: dict, extra: dict, messages: list) -> None:
        """處理中 → 完成；寫 procedure 記憶（`BR51.5`）→ 送完成訊息 → 推進等待者。"""
        new_status = R.transition(R.STATUS_PROCESSING, R.EV_CAPABILITY_COMPLETED)
        patch = {"status": new_status, "deadlineAt": None, **extra}
        if not self._cas(ctx.session_key, item, [R.STATUS_PROCESSING], patch):
            raise _StepAborted()
        updated = {**item, **patch}
        self._log_transition(item, R.STATUS_PROCESSING, new_status)
        await self._write_procedure_memory(ctx, updated)
        await self._push_items(ctx.sink, ctx.session_key)
        await self._emit("turn", ctx.sink, messages)
        await self._advance_dependents(ctx, updated)

    async def _write_procedure_memory(self, ctx: _Ctx, item: dict) -> None:
        content = f"{R.capability_name(item['capability'])}（{item['label']}）"

        def write(principal, db):
            self._memory_factory(db).write(principal, "procedure", content)

        try:
            await self._call_facade(ctx.user_id, write)
        except Exception as exc:  # noqa: BLE001 - BR51.5：失敗不影響工作項
            logger.warning("work_item=%s memory_write_failed error=%s", ctx.item_id, type(exc).__name__)

    # ==================================================================
    # 同進程 facade（`BR51.7`；`NFR12.2`／`NFR12.9`）
    # ==================================================================

    async def _call_facade(self, user_id: int, fn: Callable[[Any, Any], Any]) -> Any:
        """離開事件迴圈執行；每次開獨立的 DB session、重新取使用者並鑄造 Principal。"""
        return await asyncio.to_thread(self._facade_sync, user_id, fn)

    def _facade_sync(self, user_id: int, fn: Callable[[Any, Any], Any]) -> Any:
        factory = self._session_factory
        if factory is None:
            from database import SessionLocal  # 延遲取得：測試以建構子注入替身

            factory = SessionLocal
        db = factory()
        try:
            user = db.get(self._user_model, user_id)
            # 停用判定由本單元自寫：mint_principal 不檢查 is_active（帶入項 5、10）。
            if user is None or not getattr(user, "is_active", False):
                raise _UserDisabled()
            return fn(self._mint(user), db)
        finally:
            db.close()

    # ==================================================================
    # 訊息出口（`BR52.5`／`BR56.8`／`BR58.5`；`NFR12.27`）
    # ==================================================================

    @staticmethod
    def _token(text: str) -> TokenPayload:
        return TokenPayload.model_validate({"text": text})

    async def _push_items(self, sink: Any, session_key: str) -> None:
        items = self._store.load_work_items(session_key)
        payload = WorkItemsPayload.model_validate(
            {"items": [_public(i) for i in _sorted(items.values())]}
        )
        await self._emit("session", sink, payload)

    async def _emit(self, kind: str, sink: Any, *args: Any) -> None:
        """唯一的 sink 出口。訊息必須已是契約模型；sink 失敗只記 log（`BR56.8`）。"""
        allowed = {
            "session": (WorkItemsPayload,),
            "in_turn": (TokenPayload,),
            "turn": (TokenPayload, CostCardPayload),
        }[kind]
        payloads = [args[0]] if kind == "session" else list(args[-1])
        for payload in payloads:
            if not isinstance(payload, allowed):
                raise TypeError(f"{kind} 只能送契約模型，收到 {type(payload).__name__}")
            # 往返重驗只是確認實例沒有在建構後被改動；**不是**額外的契約防線——
            # 真正的防線是上面的型別檢查加上建構時的 `model_validate`（審查 R-04）。
            type(payload).model_validate(payload.model_dump())
        if kind != "session" and not payloads:
            return
        method = {"session": "emit_session", "in_turn": "emit_in_turn", "turn": "emit_turn"}[kind]
        try:
            result = getattr(sink, method)(*args)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:  # noqa: BLE001 - BR56.8：sink 失敗不擴散
            logger.warning("sink_failed method=%s error=%s", method, type(exc).__name__)

    @staticmethod
    def _log_transition(item: dict, old: Optional[str], new: str) -> None:
        logger.info(
            "work_item=%s capability=%s %s->%s stage=%s",
            item["workItemId"],
            item["capability"],
            old,
            new,
            item.get("dispatchStage"),
        )


__all__ = [
    "CHANGE_SUMMARY_MAX_CHARS",
    "MAX_CAS_ATTEMPTS",
    "PERSIST_TIMEOUT_SECONDS",
    "POLL_INTERVAL_SECONDS",
    "REQUEST_TEXT_MAX_CHARS",
    "WorkItemNotFound",
    "WorkOrchestrator",
]
