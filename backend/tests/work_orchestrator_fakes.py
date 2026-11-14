"""`U12 work-orchestrator` 測試共用的替身（**不是**測試模組，`discover` 不會收它）。

替身的範圍（如實記載，沿用 `test_session_store_behaviour.py` 檔頭的口徑）：

- `WorkItemFakeRedis` 以 `session_types.ref_put_work_item`／`ref_update_work_item`
  模擬兩支 Lua 的效果。它是單執行緒 Python 物件，**證明不了 Lua 在真實 Redis
  上的原子性**；那一項由 `backend/tests_redis/`（opt-in，不在 CI）承擔。
- `FakeCapabilityApp` 是一個 ASGI app，**一次回傳完整的回應本體**（與
  `httpx.ASGITransport` 的緩衝行為同形，`NFR12.29`）；路徑與事件形狀逐字對齊
  既有端點（`agent_router.py`、`review_router.py`、`collab_router.py`、
  `cost/estimate_intake_router.py`）。
- `FakeClock` 是可推進的牆鐘；`FakeClock.sleep` 推進時間後讓出事件迴圈一次，
  使「以注入的 clock 判定逾時」可以在測試內被驅動（`NFR12.19`／帶入項 13、20）。
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from services.redis_gateway import RedisGateway
from services.session_store import SessionStore
from services import session_types as T
from services import work_orchestrator_rules as _R
from services.brain_ws_contract import CostCardPayload, TokenPayload, WorkItemsPayload
from tests.test_session_store_behaviour import FAKE_ERROR_TYPES, FakeRedis, StubClock


class WorkItemFakeRedis(FakeRedis):
    """在既有替身上加兩支工作項腳本（以參考實作模擬）。"""

    def __init__(self) -> None:
        super().__init__()
        #: 每次 `update_work_item` 腳本被執行前呼叫一次（測試用來注入交錯）。
        self.before_update: Optional[Callable[[list, list], None]] = None

    def _script_put_work_item(self, keys, argv):
        key = keys[0]
        result, updated = T.ref_put_work_item(self.hashes.get(key), *argv)
        if updated is not None:
            self.hashes[key] = updated
        return result

    def _script_update_work_item(self, keys, argv):
        if self.before_update is not None:
            hook, self.before_update = self.before_update, None
            hook(keys, argv)
        key = keys[0]
        result, updated = T.ref_update_work_item(self.hashes.get(key), *argv)
        if updated is not None:
            self.hashes[key] = updated
        return result


SESSION_KEY = "brain:session:u-test"

#: 測試直接呼叫 `ref_update_work_item` 時的最後兩個 ARGV（已結束保留數、終態集合），
#: 與 `SessionStore.update_work_item` 送給 Lua 的值同源。
UPDATE_CAPACITY_ARGS = (
    str(_R.MAX_TERMINAL_WORK_ITEMS),
    json.dumps(sorted(_R.TERMINAL_STATUSES), ensure_ascii=False, separators=(",", ":")),
)


def make_store(client: Optional[WorkItemFakeRedis] = None, *, create_key: bool = True):
    """回傳 `(store, client)`；`create_key=True` 時先建立一個存活的 session key。"""
    client = client if client is not None else WorkItemFakeRedis()
    clock = StubClock()
    gateway = RedisGateway(
        client,
        error_types=FAKE_ERROR_TYPES,
        clock=clock,
        sleep=clock.sleep,
        jitter=lambda: 0.0,
    )
    store = SessionStore(gateway, hierarchy_facade=object(), history_max=5)
    if create_key:
        store.append_message(SESSION_KEY, "shared", "user", "hi")
        client.ttls[SESSION_KEY] = 86400
    return store, client


class FakeClock:
    """可推進的牆鐘（aware UTC datetime）。"""

    def __init__(self, start: Optional[datetime] = None) -> None:
        self.now = start or datetime(2026, 10, 12, 8, 0, 0, tzinfo=timezone.utc)
        self.sleeps: list = []

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.advance(seconds)
        await asyncio.sleep(0)


class RecordingSink:
    """記錄 sink 收到的訊息；**只接受契約模型**（`NFR12.27`／帶入項 16）。

    **每次 emit 先讓出事件迴圈一次**（審查 R-02）：真實的 WebSocket sink 一定會讓出，
    而從不讓出的替身會讓「先取消、後完成」「部分完成後被取消」這類交錯不可能發生
    （R-01 就藏在那裡）。`on_emit` 掛勾在讓出之後、記錄之前呼叫，供測試注入交錯。
    """

    def __init__(self, *, fail: bool = False) -> None:
        self.session: list = []
        self.in_turn: list = []
        self.turns: list = []
        self.fail = fail
        self.on_emit = None

    async def _yield(self, kind, payloads):
        await asyncio.sleep(0)
        if self.on_emit is not None:
            await self.on_emit(kind, payloads)

    @staticmethod
    def _require(models, allowed):
        for model in models:
            if not isinstance(model, allowed):
                raise TypeError(f"sink 只接受契約模型，收到 {type(model).__name__}")

    async def emit_session(self, payload):
        self._require([payload], (WorkItemsPayload,))
        await self._yield("session", [payload])
        if self.fail:
            raise ConnectionError("socket closed")
        self.session.append(payload)

    async def emit_in_turn(self, turn_id, payloads):
        self._require(payloads, (TokenPayload,))
        await self._yield("in_turn", payloads)
        if self.fail:
            raise ConnectionError("socket closed")
        self.in_turn.append((turn_id, list(payloads)))

    async def emit_turn(self, payloads):
        self._require(payloads, (TokenPayload, CostCardPayload))
        await self._yield("turn", payloads)
        if self.fail:
            raise ConnectionError("socket closed")
        self.turns.append(list(payloads))

    def all_texts(self) -> list:
        texts = []
        for _, payloads in self.in_turn:
            texts += [p.text for p in payloads]
        for payloads in self.turns:
            texts += [p.text for p in payloads if isinstance(p, TokenPayload)]
        return texts

    def dump(self) -> str:
        parts = [p.model_dump_json() for p in self.session]
        parts += [p.model_dump_json() for _, ps in self.in_turn for p in ps]
        parts += [p.model_dump_json() for ps in self.turns for p in ps]
        return "\n".join(parts)


def sse(events) -> bytes:
    return "".join(
        f"data: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events
    ).encode("utf-8")


class FakeCapabilityApp:
    """一次回傳完整本體的 ASGI app。行為以屬性設定，請求記錄在 `calls`。"""

    def __init__(self) -> None:
        self.calls: list = []
        self.auth_headers: list = []
        self.diagram = {"title": "訂單系統", "xml_data": "<mxGraphModel/>", "updated_at": "t1"}
        self.diagram_updated_at_seq: Optional[list] = None
        self.a1_events = [
            {"type": "message", "content": "已依需求加上快取層"},
            {"type": "xml", "content": "<mxGraphModel><root/></mxGraphModel>"},
        ]
        self.a3_events = [
            {"type": "rules_done"},
            {"type": "complete", "overall_score": 82, "findings": [{"id": 1}, {"id": 2}]},
        ]
        self.status_overrides: dict = {}
        self.estimate_pages: list = [
            [{"id": 7, "diagram_id": 12, "advice_status": "completed"}],
        ]
        self.advice_snapshots: list = [
            {"status": "completed", "saving_text": "可省 10%", "comparison_text": None,
             "quality_text": None, "unavailable_reasons": None, "started_at": None},
        ]
        self.advice_errors: list = []
        self.hang: set = set()
        self.release = asyncio.Event()
        self.put_started = asyncio.Event()
        self.put_release: Optional[asyncio.Event] = None
        self.raise_in: dict = {}
        self.thread_ids: list = []
        #: 請求抵達時（回應之前）呼叫的掛勾：`{"METHOD /path 前綴": callable}`。
        self.hooks: dict = {}

    def count(self, prefix: str) -> int:
        return sum(1 for c in self.calls if c.startswith(prefix))

    async def __call__(self, scope, receive, send):
        assert scope["type"] == "http"
        method = scope["method"]
        path = scope["path"]
        key = f"{method} {path}"
        self.calls.append(key)
        headers = dict(scope.get("headers") or [])
        self.auth_headers.append(headers.get(b"authorization", b"").decode())
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body"):
                break
        for prefix, hook in list(self.hooks.items()):
            if key.startswith(prefix):
                hook()
        if key in self.raise_in:
            raise self.raise_in[key]
        for prefix in self.hang:
            if key.startswith(prefix):
                await self.release.wait()
        status, payload, content_type = self._route(method, path, body)
        override = self.status_overrides.get(key) or self.status_overrides.get(method + " *")
        if override is not None:
            status, payload, content_type = override, b'{"detail":"x"}', b"application/json"
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", content_type)]})
        await send({"type": "http.response.body", "body": payload})

    def _route(self, method, path, body):
        js = b"application/json"
        if method == "POST" and path == "/api/architecture/generate":
            return 200, sse(self.a1_events), b"text/event-stream"
        if method == "POST" and path == "/api/architecture/reviews":
            return 200, sse(self.a3_events), b"text/event-stream"
        if path.startswith("/api/collab/diagrams/"):
            if method == "GET":
                diagram = dict(self.diagram)
                if self.diagram_updated_at_seq:
                    diagram["updated_at"] = self.diagram_updated_at_seq.pop(0)
                return 200, json.dumps(diagram).encode(), js
            if method == "PUT":
                return 200, b'{"status":"success"}', js
        if method == "GET" and path == "/api/cost/v1/sets":
            return 200, b"", js  # 由 query 決定，見 _route_query
        if method == "GET" and path.startswith("/api/cost/v1/sets/") and path.endswith("/advice"):
            if self.advice_errors:
                status = self.advice_errors.pop(0)
                if status is not None:
                    return status, b'{"detail":"x"}', js
            snap = self.advice_snapshots[0] if len(self.advice_snapshots) == 1 else self.advice_snapshots.pop(0)
            return 200, json.dumps(snap).encode(), js
        return 404, b'{"detail":"Not found"}', js


class CostListApp(FakeCapabilityApp):
    """`GET /api/cost/v1/sets` 依 `page` query 回對應頁。"""

    async def __call__(self, scope, receive, send):
        if scope["method"] == "GET" and scope["path"] == "/api/cost/v1/sets":
            self.calls.append("GET /api/cost/v1/sets")
            if any("GET /api/cost/v1/sets".startswith(prefix) for prefix in self.hang):
                await self.release.wait()
            query = dict(
                part.split("=", 1) for part in scope.get("query_string", b"").decode().split("&") if part
            )
            override = self.status_overrides.get("GET /api/cost/v1/sets")
            if override is not None:
                await send({"type": "http.response.start", "status": override,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"detail":"x"}'})
                return
            page = int(query.get("page", "1"))
            page_size = int(query.get("page_size", "20"))
            flat = [item for chunk in self.estimate_pages for item in chunk]
            items = flat[(page - 1) * page_size: page * page_size]
            body = json.dumps({"items": items, "page": page,
                               "page_size": page_size, "total": len(flat)}).encode()
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})
            return
        if scope["method"] == "PUT" and self.put_release is not None:
            self.calls.append(f"PUT {scope['path']}")
            self.put_started.set()
            await self.put_release.wait()
            for prefix, hook in list(self.hooks.items()):
                if f"PUT {scope['path']}".startswith(prefix):
                    hook()
            await send({"type": "http.response.start", "status": self.status_overrides.get("PUT", 200),
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"status":"success"}'})
            return
        await super().__call__(scope, receive, send)


class FakeUser:
    def __init__(self, user_id=1, role="Project_Architect", is_active=True):
        self.id = user_id
        self.role = role
        self.is_active = is_active
        self.authorization_status = "approved"


class FakeDb:
    """`session_factory()` 的替身：只支援 `get(User, id)` 與 `close()`。"""

    def __init__(self, users: dict, log: list) -> None:
        self._users = users
        self._log = log

    def get(self, _model, user_id):
        self._log.append(("get", threading.get_ident()))
        return self._users.get(user_id)

    def close(self):
        self._log.append(("close", threading.get_ident()))


class FakeHierarchy:
    """`HierarchyFacade` 的替身：記錄呼叫、可設定行為。"""

    def __init__(self, recorder: "FacadeRecorder") -> None:
        self._r = recorder

    def list_diagrams_of_system(self, principal, *, system_id):
        self._r.calls.append(("list_diagrams_of_system", principal.user_id, system_id))
        self._r.threads.append(threading.get_ident())
        if self._r.list_error is not None:
            raise self._r.list_error
        return list(self._r.system_diagrams.get(system_id, []))

    def record_diagram_change(self, principal, *, diagram_id, requirement_summary,
                              requirement_label, actor_user_id):
        self._r.threads.append(threading.get_ident())
        if self._r.change_error is not None:
            raise self._r.change_error
        self._r.changes.append({
            "diagram_id": diagram_id, "summary": requirement_summary,
            "label": requirement_label, "actor": actor_user_id,
            "principal": principal.user_id,
        })


class FakeMemory:
    def __init__(self, recorder: "FacadeRecorder") -> None:
        self._r = recorder

    def write(self, principal, kind, content, **_ignored):
        self._r.threads.append(threading.get_ident())
        if self._r.memory_error is not None:
            raise self._r.memory_error
        self._r.memories.append((principal.user_id, kind, content))


class FacadeRecorder:
    def __init__(self) -> None:
        self.calls: list = []
        self.threads: list = []
        self.changes: list = []
        self.memories: list = []
        self.system_diagrams: dict = {}
        self.list_error = None
        self.change_error = None
        self.memory_error = None
        self.db_log: list = []
        self.users = {1: FakeUser()}
        #: 測試用：在 `record_diagram_change` 之前改變使用者狀態。
        self.before_change: Optional[Callable[[], None]] = None

    def session_factory(self):
        return FakeDb(self.users, self.db_log)

    def hierarchy_factory(self, db):
        if self.before_change is not None:
            hook, self.before_change = self.before_change, None
            hook()
        return FakeHierarchy(self)

    def memory_factory(self, db):
        return FakeMemory(self)


def fake_principal(user_id: int = 1):
    """測試用 principal：只需要 `user_id`（`WorkOrchestrator` 只讀它）。"""

    class _P:
        pass

    p = _P()
    p.user_id = user_id
    return p


def fake_mint(user):
    return fake_principal(user.id)


async def drain(orchestrator, *, rounds: int = 50) -> None:
    """等背景 task（含它們再啟動的 task）全部結束。以 gather 等待，不靠真實時間。"""
    for _ in range(rounds):
        pending = [t for t in orchestrator._all_tasks() if not t.done()]
        if not pending:
            await asyncio.sleep(0)
            if not [t for t in orchestrator._all_tasks() if not t.done()]:
                return
            continue
        await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=5)
    raise AssertionError("背景 task 未結束")
