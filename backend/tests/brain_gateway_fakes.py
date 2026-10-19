"""`U13 brain-gateway` 測試共用的替身與組裝（**不是測試檔**，故不以 `test` 起首）。

替身的限制（揭露於 code-summary）：
- Redis 走既有 `WorkItemFakeRedis`（行程內、同步）——**證明不了真實原子性與真實網路逾時**；
- WebSocket 走 `starlette.testclient`：「不 accept」表現為關閉碼 1000，真實 uvicorn 為 HTTP 403；
- 嵌入替身拋**實際**例外型別 `EmbeddingProviderUnavailable`（`raise … from httpx.ReadTimeout`），
  但不經真 httpx 與 Ollama，Ollama 冷載時實際拋出哪一種 httpx 例外只能在部署 stack 複核。

授權走**真實**的 `get_user_from_token`、`user_can`、`mint_principal`（SQLite ＋ 播種），不 mock `user_can`。
"""

from __future__ import annotations

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import asyncio
import queue
import threading
import uuid
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from services import brain_gateway as G
from services import brain_gateway_rules as rules
from services.auth import create_access_token
from services.brain_ws_contract import TokenPayload, WorkItem, WorkItemsPayload
from services.hierarchy_facade import (
    PROJECT_NOT_FOUND_DETAIL,
    SYSTEM_NOT_FOUND_DETAIL,
    HierarchyForbidden,
    HierarchyNotFound,
)
from services.intent_routing_types import ClarifyCandidate, Intent, IntentDecision
from services.redis_gateway import RedisGateway
from services.session_store import SessionStore
from services.work_orchestrator import WorkItemNotFound
from tests.helpers import close_session, make_session, make_user
from tests.test_session_store_behaviour import FAKE_ERROR_TYPES, StubClock
from tests.work_orchestrator_fakes import WorkItemFakeRedis

WS_PATH = "/api/brain/ws"


# ---------------------------------------------------------------------------
# 時間
# ---------------------------------------------------------------------------


class FakeTiming:
    """可推進的單調時鐘。`sleep` 阻塞到測試以 `advance` 推過目標時刻（可跨執行緒推進）。

    `expire_once`：`{timeout 值: 次數}`——對應的下一次 `wait_for` 立即取消被等待者並拋
    `TimeoutError`（模擬逾時，不真的等）。其餘 `wait_for` 照常等待，但以 10 秒為安全上限，
    使失敗的測試不會卡死。
    """

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start
        self._lock = threading.Lock()
        self._sleepers: list = []
        self.wait_for_calls: list = []
        self.expire_once: Dict[float, int] = {}

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        with self._lock:
            self._sleepers.append((self.now + seconds, loop, fut))
        await fut

    def advance(self, seconds: float) -> None:
        with self._lock:
            self.now += seconds
            due = [s for s in self._sleepers if s[0] <= self.now]
            self._sleepers = [s for s in self._sleepers if s[0] > self.now]
        for _, loop, fut in due:
            loop.call_soon_threadsafe(_resolve, fut)

    def sleeper_count(self) -> int:
        with self._lock:
            return len(self._sleepers)

    async def wait_for(self, aw, timeout):
        self.wait_for_calls.append(timeout)
        with self._lock:
            remaining = self.expire_once.get(timeout, 0)
            if remaining:
                self.expire_once[timeout] = remaining - 1
        if remaining:
            if asyncio.iscoroutine(aw):
                aw.close()
            elif isinstance(aw, asyncio.Future):
                aw.cancel()
            self.now += timeout
            raise TimeoutError()
        return await asyncio.wait_for(aw, 10)

    def timing(self) -> G.GatewayTiming:
        return G.GatewayTiming(monotonic=self.monotonic, sleep=self.sleep, wait_for=self.wait_for)


def _resolve(fut) -> None:
    if not fut.done():
        fut.set_result(None)


# ---------------------------------------------------------------------------
# U11／U12／U7／U8 的替身
# ---------------------------------------------------------------------------


def decision(capability: str = "architecture-design", referent: Optional[str] = None, *more: Intent) -> IntentDecision:
    return IntentDecision(intents=(Intent(capability, referent),) + tuple(more), confidence=0.9, below_threshold=False)


def low_confidence(*labels: str) -> IntentDecision:
    cands = tuple(
        ClarifyCandidate(id=f"c{i}", label=label, capability="architecture-design", confidence=0.4)
        for i, label in enumerate(labels or ("建一張架構圖",), start=1)
    )
    return IntentDecision(intents=(), confidence=0.4, below_threshold=True, candidates=cands)


class FakeRouter:
    """`IntentRouter.classify` 的替身。結果由 `script[utterance]` 決定（值可為例外實例）。

    呼叫時也像真的 `U11` 一樣經注入的轉接器取記憶（`memory_facade.search`），把結果或例外記下，
    用來驗證預取經 `ContextVar` 交給 `U11`。
    """

    def __init__(self, shared: "RouterScript", segment: str, adapter: Any) -> None:
        self._shared = shared
        self.segment = segment
        self._adapter = adapter

    async def classify(self, principal, session, utterance, *, turn_id: str = ""):
        shared = self._shared
        shared.calls.append(
            SimpleNamespace(segment=self.segment, utterance=utterance, turn_id=turn_id, thread=threading.get_ident())
        )
        try:
            hits = self._adapter.search(principal, utterance, kinds=("semantic", "procedure"), limit=5)
            shared.memory_seen.append(("hits", len(hits)))
        except Exception as exc:  # 與 U11 同形：轉接器拋出即降級
            shared.memory_seen.append(("degraded", type(exc).__name__))
        if shared.before_return is not None:
            await shared.before_return()
        outcome = shared.script.get(utterance, shared.default)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class RouterScript:
    def __init__(self) -> None:
        self.script: Dict[str, Any] = {}
        self.default: Any = decision()
        self.calls: list = []
        self.memory_seen: list = []
        self.before_return: Optional[Callable[[], Any]] = None


class FakeOrchestrator:
    """`U12 WorkOrchestrator` 的替身：工作項寫進同一個 Redis 替身（經真 `SessionStore`）。"""

    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self.dispatch_calls: list = []
        self.correct_calls: list = []
        self.list_calls: list = []
        self.list_hook: Optional[Callable[[Any], Any]] = None
        self.dispatch_hook: Optional[Callable[[Any, str], Any]] = None
        self.dispatch_error: Optional[BaseException] = None
        self.reply_texts = ["已交辦：建立架構圖"]
        self.sinks: list = []

    def _public(self, key: str) -> list:
        items = self.store.load_work_items(key)
        return [
            WorkItem.model_validate(
                {k: i.get(k) for k in ("workItemId", "label", "status", "capability", "waitingOn", "failureReason", "sideEffect")}
            )
            for i in sorted(items.values(), key=lambda i: i.get("createdAt") or "")
        ]

    async def list_items(self, principal, session_key, *, bearer_token, sink):
        self.list_calls.append(SimpleNamespace(key=session_key, token=bearer_token))
        self.sinks.append(sink)
        if self.list_hook is not None:
            await self.list_hook(sink)
        return self._public(session_key)

    async def dispatch(self, principal, session, decision, *, utterance, segment_id, turn_id, bearer_token, sink):
        self.dispatch_calls.append(
            SimpleNamespace(
                principal=principal, decision=decision, utterance=utterance, segment_id=segment_id,
                turn_id=turn_id, token=bearer_token, session=session,
            )
        )
        self.sinks.append(sink)
        if self.dispatch_error is not None:
            raise self.dispatch_error
        if decision.below_threshold:
            return []
        if segment_id not in (session.segments or {}):
            raise ValueError("段不在這個工作階段內")
        key = session.session_key
        for intent in decision.intents:
            wid = uuid.uuid4().hex[:12]
            self.store.put_work_item(
                key,
                {
                    "workItemId": wid, "label": "建立架構圖", "status": "處理中", "capability": intent.capability,
                    "waitingOn": None, "failureReason": None, "sideEffect": "none", "segmentId": segment_id,
                    "createdAt": wid, "dispatchStage": "created",
                },
            )
        await sink.emit_session(WorkItemsPayload(items=[i.model_dump() for i in self._public(key)]))
        if self.dispatch_hook is not None:
            await self.dispatch_hook(sink, turn_id)
        if self.reply_texts:
            await sink.emit_in_turn(turn_id, [TokenPayload(text=t) for t in self.reply_texts])
        return self._public(key)

    async def correct(self, principal, session_key, work_item_id, *, bearer_token, sink):
        self.correct_calls.append(SimpleNamespace(key=session_key, work_item_id=work_item_id, sink=sink))
        if work_item_id not in self.store.load_work_items(session_key):
            raise WorkItemNotFound(work_item_id)
        await sink.emit_turn([TokenPayload(text="已停掉")])
        return None


_NO_NAMES = {"projectName": None, "systemName": None, "diagramName": None}


class FakeHierarchy:
    """`HierarchyFacade` 的替身（只實作本單元用到的四個方法）。

    `U14`（ADR-0022）起四個讀取方法都接受並**套用** `project_visible`，語意與真實 facade 相同：
    列舉排除不可見專案、`list_systems` 對不可見專案拋 `HierarchyNotFound`、
    `resolve_work_target` 依 D-4 兩分支、`describe_work_target` 依 D-2（明確指定且任一所屬
    專案不可見 → 三名稱 null；只有圖 → 不判可見性、只留圖名）。
    """

    def __init__(self) -> None:
        self.projects: List[tuple] = []          # (id, name)
        self.systems: Dict[int, List[tuple]] = {}  # pid -> [(sid, name)]
        self.diagrams: Dict[int, Optional[int]] = {}  # did -> 所屬 sid（None ＝ 孤兒圖）
        self.list_projects_calls = 0
        self.list_systems_calls = 0
        self.forbidden_list = False
        self.forbidden_ids: set = set()
        self.threads: list = []
        # describe_work_target：(pid, sid, did) -> {"projectName", "systemName", "diagramName"}
        self.names_by_triple: Dict[tuple, dict] = {}
        self.describe_raises: Optional[BaseException] = None
        self.describe_calls: list = []

    def factory(self, db):
        return self

    def _project_of_system(self, system_id):
        for pid, systems in self.systems.items():
            if any(sid == system_id for sid, _ in systems):
                return pid
        return None

    def list_projects(self, principal, *, project_visible):
        self.threads.append(threading.get_ident())
        self.list_projects_calls += 1
        if self.forbidden_list:
            raise HierarchyForbidden(story_id="K2", action="view")
        return [SimpleNamespace(id=pid, name=name) for pid, name in self.projects if project_visible(pid)]

    def list_systems(self, principal, *, project_id, project_visible):
        self.list_systems_calls += 1
        if not project_visible(project_id):
            raise HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)
        return [SimpleNamespace(id=sid, name=name) for sid, name in self.systems.get(project_id, [])]

    def resolve_work_target(self, principal, *, project_visible, project_id=None, system_id=None, diagram_id=None):
        self.threads.append(threading.get_ident())
        if project_id in self.forbidden_ids:
            raise HierarchyForbidden(story_id="K2", action="view")
        known = {pid for pid, _ in self.projects}
        if project_id is not None and project_id not in known:
            raise HierarchyNotFound("查不到")
        resolved = {"projectId": project_id, "systemId": system_id, "diagramId": diagram_id}
        if system_id is not None and self._project_of_system(system_id) is not None:
            resolved["projectId"] = self._project_of_system(system_id)
        if diagram_id is not None and self.diagrams.get(diagram_id) is not None:
            resolved["systemId"] = self.diagrams[diagram_id]
            resolved["projectId"] = self._project_of_system(self.diagrams[diagram_id])
        pid = resolved["projectId"]
        if pid is None or project_visible(pid):
            return resolved
        if project_id is not None or system_id is not None:
            raise HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL if project_id is not None else SYSTEM_NOT_FOUND_DETAIL)
        return {"projectId": None, "systemId": None, "diagramId": diagram_id}

    def describe_work_target(self, principal, *, project_visible, project_id=None, system_id=None, diagram_id=None):
        self.threads.append(threading.get_ident())
        self.describe_calls.append((project_id, system_id, diagram_id))
        if self.describe_raises is not None:
            raise self.describe_raises
        names = dict(self.names_by_triple.get((project_id, system_id, diagram_id), _NO_NAMES))
        explicit = project_id is not None or system_id is not None
        if not explicit:
            return {"projectName": None, "systemName": None, "diagramName": names.get("diagramName")}
        pids = {p for p in (project_id, self._project_of_system(system_id) if system_id is not None else None) if p is not None}
        if diagram_id is not None and self.diagrams.get(diagram_id) is not None:
            dp = self._project_of_system(self.diagrams[diagram_id])
            if dp is not None:
                pids.add(dp)
        if any(not project_visible(p) for p in pids):
            return dict(_NO_NAMES)
        return names


class FakeVisibility:
    """`MembershipFacade(db)` 的替身：只提供 `project_visibility`（語意同真實閉包：不在 `invisible` 即可見）。"""

    def __init__(self) -> None:
        self.invisible: set = set()
        self.factory_calls = 0

    def factory(self, db):
        self.factory_calls += 1
        return self

    def project_visibility(self, principal):
        invisible = self.invisible
        return lambda pid: pid not in invisible


class FakeMemory:
    """`MemoryFacade(db)` 的替身。`search_behaviour`／`write_behaviour` 可為 list、例外、或 callable。"""

    def __init__(self) -> None:
        self.search_calls: list = []
        self.write_calls: list = []
        self.search_behaviour: Any = []
        self.write_behaviour: Any = None
        self.threads: list = []

    def factory(self, db):
        return self

    def _run(self, behaviour, *args):
        if callable(behaviour) and not isinstance(behaviour, BaseException):
            return behaviour(*args)
        if isinstance(behaviour, BaseException):
            raise behaviour
        return behaviour

    def search(self, principal, query, kinds=None, limit=None):
        self.threads.append(threading.current_thread().name)
        self.search_calls.append(SimpleNamespace(principal=principal, query=query, kinds=tuple(kinds or ()), limit=limit))
        return self._run(self.search_behaviour, principal, query)

    def write(self, principal, kind, content):
        self.threads.append(threading.current_thread().name)
        self.write_calls.append(SimpleNamespace(principal=principal, kind=kind, content=content))
        return self._run(self.write_behaviour, principal, kind)


def memory_hit(kind: str = "semantic", content: str = "術語") -> SimpleNamespace:
    return SimpleNamespace(kind=kind, content=content)


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------


class Harness:
    """一組可用的閘道：真 `SessionStore`（Redis 替身）、真認證（SQLite）、其餘以替身注入。"""

    def __init__(self, *, max_total: int = 200, max_per_key: int = 10, redis: Optional[WorkItemFakeRedis] = None, rate=None) -> None:
        self.db = make_session()
        self.Session = sessionmaker(bind=self.db._test_engine)
        self.timing = FakeTiming()
        self.redis = redis if redis is not None else WorkItemFakeRedis()
        clock = StubClock()
        self.hierarchy = FakeHierarchy()
        self.visibility = FakeVisibility()
        self.store = SessionStore(
            RedisGateway(self.redis, error_types=FAKE_ERROR_TYPES, clock=clock, sleep=clock.sleep, jitter=lambda: 0.0),
            hierarchy_facade=G._HierarchyResolver(
                self.Session, self.hierarchy.factory, membership_facade_factory=self.visibility.factory
            ),
            history_max=50,
        )
        self.memory = FakeMemory()
        self.router_script = RouterScript()
        self.orchestrator = FakeOrchestrator(self.store)
        self._limits = (max_total, max_per_key, rate)
        self.app = FastAPI()
        self.app.include_router(G.router, prefix="/api/brain")
        self.users: Dict[str, Any] = {}
        self.rebuild()

    def rebuild(self) -> None:
        """重建閘道元件（模擬行程重啟）：Redis 替身、DB、替身的狀態沿用，行程內狀態全部重來。"""
        old = getattr(self, "gw", None)
        if old is not None:
            old.shutdown()
        max_total, max_per_key, rate = self._limits
        self.registry = G.ConnectionRegistry(max_total=max_total, max_per_key=max_per_key)
        self.adapter = G.MemoryPrefetchAdapter()
        timing = self.timing.timing()
        self.gw = G.BrainGateway(
            store=self.store,
            routers={seg: FakeRouter(self.router_script, seg, self.adapter) for seg in ("shared", "workspace", "assessment")},
            orchestrator=self.orchestrator,
            session_factory=self.Session,
            timing=timing,
            memory_facade_factory=self.memory.factory,
            hierarchy_facade_factory=self.hierarchy.factory,
            membership_facade_factory=self.visibility.factory,
            registry=self.registry,
            rate_limiter=rate,
            memory_worker=G.MemoryWorker(timing),
            prefetch_adapter=self.adapter,
        )
        self.app.state.brain_gateway = self.gw

    def user(self, username: str = "alice", *, role: str = "Project_Architect", **kw) -> Any:
        user = make_user(self.db, username=username, role=role, **kw)
        self.users[username] = user
        return user

    @staticmethod
    def token(username: str) -> str:
        return create_access_token({"sub": username})

    def close(self) -> None:
        self.gw.shutdown()
        close_session(self.db)


def protocols(token: Optional[str]) -> list:
    out = [rules.PROTOCOL_NAME]
    if token is not None:
        out.append(rules.BEARER_PREFIX + token)
    return out


def recv(ws, timeout: float = 5.0) -> dict:
    """自 TestClient 的佇列取下一則；逾時拋 `queue.Empty`（避免測試卡死）。"""
    message = ws._send_queue.get(timeout=timeout)
    if isinstance(message, BaseException):
        raise message
    return message


def recv_json(ws, timeout: float = 5.0) -> dict:
    """取下一則並以 `WsEnvelope` 驗證——本單元送出的**每一則**都必須通過契約模型（NFR13.40）。"""
    import json

    from services.brain_ws_contract import WsEnvelope

    message = recv(ws, timeout)
    if message["type"] == "websocket.close":
        return {"__close__": message.get("code"), "reason": message.get("reason")}
    data = json.loads(message["text"])
    WsEnvelope.model_validate(data)
    return data


def nothing_more(ws, wait: float = 0.3) -> bool:
    try:
        ws._send_queue.get(timeout=wait)
        return False
    except queue.Empty:
        return True


def hello(ws) -> list:
    """送 hello 並讀到快照的 `work_items` 為止；回傳收到的全部訊息。"""
    ws.send_json({"v": 1, "type": "hello", "payload": {"v": 1}})
    out = []
    while True:
        msg = recv_json(ws)
        out.append(msg)
        if msg.get("type") == "work_items" or "__close__" in msg:
            return out


def user_message(ws, utterance: str, page: str = "entry") -> None:
    ws.send_json({"v": 1, "type": "user_message", "payload": {"text": utterance, "page": page}})


def read_turn(ws, timeout: float = 5.0) -> list:
    """讀到一輪的終止事件（done／error）或 clarify 為止。狀態訊息一併收下。"""
    out = []
    while True:
        msg = recv_json(ws, timeout)
        out.append(msg)
        if "__close__" in msg or msg.get("type") in ("done", "error", "clarify"):
            return out


def types_of(messages: list) -> list:
    return [m.get("type") or f"close:{m.get('__close__')}" for m in messages]
