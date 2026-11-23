"""
work_orchestrator_capabilities.py — `U12 work-orchestrator` 對既有能力的呼叫

**契約（`work_orchestrator.py` 依賴，請勿變更）**

本模組是 `U12` 碰到既有 A1／A3／C1 能力的**唯一**位置，而它碰的方式只有一種：
經 HTTP、走同一個 FastAPI app 的 ASGI 傳輸、帶**使用者本人**的 bearer token
（`BR51.1`；`X-01`／`X-02`）。請求因此完整走過既有端點的 FastAPI dependency
（`require_story_action`／`require_arch_action`），授權照常執行——本模組**不做**
任何授權判定，也**不 import** 任何既有能力的 service 層（`NFR12.8`，由
`test_work_orchestrator_boundaries.py` 以 AST 鎖住）。

## 呼叫的端點（逐字對齊既有 router）

| 能力 | 請求 | 出處 |
|---|---|---|
| 讀圖 | `GET /api/collab/diagrams/{id}` → `title`、`xml_data`、`updated_at` | `collab_router.get_diagram` |
| A1 產圖 | `POST /api/architecture/generate`（`messages`、`current_xml`），SSE | `agent_router.chat_and_generate` |
| 存圖 | `PUT /api/collab/diagrams/{id}`（`xml_data`、`title`、`finalize`） | `collab_router.update_diagram` |
| 建草稿 | `POST /api/collab/diagrams`（`xml_data`、`title`、`system_id`、`as_draft=true`；261116-brain-create-diagram） | `collab_router.create_diagram` |
| A3 檢視 | `POST /api/architecture/reviews`（`diagram_id`、`save_diagram=false`），SSE | `review_router.create_review` |
| C1 估價表 | `GET /api/cost/v1/sets?page=&page_size=` | `cost/estimate_intake_router.list_estimate_sets` |
| C1 建議快照 | `GET /api/cost/v1/sets/{id}/advice` | `cost/estimate_intake_router.get_advice_snapshot` |

## ASGI 傳輸一律收齊才交回（`BR51.1`／`BR56.5`／`NFR12.29`）

`httpx` 的 `ASGITransport` 把 `http.response.body` 累積到 app 結束才回傳，故 SSE
在這裡只是一個**完整的本體**。A1／A3 的結果一律在回應結束後由 `judge_a1`／
`judge_a3` 判定，不依賴任何中途事件；`httpx` 未來改成真串流時，判定仍然正確
（它本來就只看完整本體）。

## 錯誤不洩漏（`BR58.4`／`NFR12.6`／`NFR12.10`）

`CapabilityError` 只帶**類別**（`http`／`transport`）、HTTP 狀態碼與底層例外的
**類別名**——不帶 `str(exc)`（`httpx` 的例外訊息含請求 URL，傳輸層的錯誤可能含
標頭）、不帶回應本體。原例外以 `from None` 截斷，不留在 `__cause__` 鏈上。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import httpx

from models import ARCH_FORBIDDEN_DETAIL_PREFIX, DRAFT_REJECTED_DETAIL

#: ASGI 傳輸不出行程；主機名只是 httpx 組 URL 用的佔位，不會被解析。
BASE_URL = "http://brain.internal"

#: `cost/estimate_intake_service.LIST_PAGE_SIZE_MAX`（50）。**不 import** 該模組
#: （`NFR12.8`），故以數值沿用；它變小時 C1 會回 422，本單元依 `BR56.4` 失敗。
COST_LIST_PAGE_SIZE = 50

#: 翻頁的硬上限：`total` 失真時不至於無限翻頁（50 × 200 = 一萬份估價表）。
COST_LIST_MAX_PAGES = 200

KIND_HTTP = "http"
KIND_TRANSPORT = "transport"

#: `cost/advice_orchestrator.TIMEOUT`（5 分鐘）。快照端點**不回收**過期的
#: `generating` 列（只有串流端點會），故本單元以 `started_at` 自行判定
#: （`BR57.4`）。同樣以數值沿用、不 import 該模組（`NFR12.8`）。
COST_ADVICE_STALE_AFTER = timedelta(minutes=5)

ADVICE_GENERATING = "generating"
ADVICE_COMPLETED = "completed"
ADVICE_FAILED = "failed"
ADVICE_TIMEOUT = "timeout"


class CapabilityError(Exception):
    """對既有能力的一次呼叫失敗。**不含任何使用者內容或憑證。**"""

    def __init__(
        self,
        kind: str,
        *,
        status_code: Optional[int] = None,
        error_class: Optional[str] = None,
        draft_rejected: bool = False,
        arch_forbidden: bool = False,
    ) -> None:
        self.kind = kind
        self.status_code = status_code
        self.error_class = error_class
        #: 261116-brain-create-diagram 契約 C4：409 且回應 detail **等於**
        #: `DRAFT_REJECTED_DETAIL` 常數時為真。只保存這個布林值，不保存回應內容。
        self.draft_rejected = draft_rejected
        #: 修訂 1（FR4.1）：403 且回應 detail 以 `ARCH_FORBIDDEN_DETAIL_PREFIX` 開頭時為真
        #: （缺架構編輯權）；K2、擁有權與帳號狀態的 403 為假。同樣只保存布林值。
        self.arch_forbidden = arch_forbidden
        super().__init__(
            f"capability_error kind={kind} status={status_code} class={error_class}"
            f" draft_rejected={draft_rejected} arch_forbidden={arch_forbidden}"
        )


def _is_draft_rejection(response: httpx.Response) -> bool:
    """409 的回應 detail 是否恰為草稿被拒的固定常數（契約 C4）。

    只做等值比較，不回傳也不保存 detail 本身：其他 409 的 detail 可能含使用者內容。
    """
    if response.status_code != 409:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    return isinstance(body, dict) and body.get("detail") == DRAFT_REJECTED_DETAIL


def _is_arch_forbidden(response: httpx.Response) -> bool:
    """403 的回應 detail 是否為「缺架構權限」（`rbac.require_arch_action` 的固定前綴）。

    修訂 1（FR4.1）：建圖端點的 403 有多個來源——架構權限、帳號尚未授權、K2 edit——只有
    前者該回「需要架構編輯權」。只做前綴比對，不回傳也不保存 detail（其中含角色名）。
    """
    if response.status_code != 403:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    detail = body.get("detail") if isinstance(body, dict) else None
    return isinstance(detail, str) and detail.startswith(ARCH_FORBIDDEN_DETAIL_PREFIX)


# ---------------------------------------------------------------------------
# SSE 本體的解析與判定（純函式）
# ---------------------------------------------------------------------------


def parse_sse(body: str) -> list:
    """完整的 SSE 本體 → 事件 dict 清單（只取 `data:` 行，非 JSON 的事件略過）。"""
    events: list = []
    for block in (body or "").replace("\r\n", "\n").split("\n\n"):
        data_lines = [
            line[5:].lstrip() for line in block.split("\n") if line.startswith("data:")
        ]
        if not data_lines:
            continue
        try:
            event = json.loads("\n".join(data_lines))
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


@dataclass(frozen=True)
class A1Result:
    """A1 一次產圖的判定結果（`BR56.5`）。

    `failure` 為 `None` 表示成功；否則為 `"a1_failed"`（有 error 事件）或
    `"a1_no_xml"`（結束時沒有 xml）。`message_text` 是全部 `message` 事件依序
    串接的文字（`BR58.3`：收齊後一次轉送）。
    """

    xml: Optional[str]
    message_text: str
    failure: Optional[str]


@dataclass(frozen=True)
class A3Result:
    """A3 一次檢視的判定結果（`BR56.5`／`BR56.2`）。"""

    overall_score: Any
    findings_count: int
    failure: Optional[str]


def judge_a1(events: Iterable[dict]) -> A1Result:
    """任一 error → 失敗；有 xml → 取最後一份；無 xml → 失敗並保留說明文字。"""
    xml: Optional[str] = None
    messages: list = []
    has_error = False
    for event in events:
        kind = event.get("type")
        content = event.get("content")
        if kind == "error":
            has_error = True
        elif kind == "xml" and isinstance(content, str) and content.strip():
            xml = content
        elif kind == "message" and isinstance(content, str):
            messages.append(content)
    text = "\n".join(m for m in messages if m.strip())
    if has_error:
        return A1Result(xml=None, message_text=text, failure="a1_failed")
    if xml is None:
        return A1Result(xml=None, message_text=text, failure="a1_no_xml")
    return A1Result(xml=xml, message_text=text, failure=None)


def judge_a3(events: Iterable[dict]) -> A3Result:
    """任一 error → 失敗；有 complete → 成功；結束時沒有 complete → 失敗。"""
    complete: Optional[dict] = None
    for event in events:
        kind = event.get("type")
        if kind == "error":
            return A3Result(overall_score=None, findings_count=0, failure="a3_failed")
        if kind == "complete":
            complete = event
    if complete is None:
        return A3Result(overall_score=None, findings_count=0, failure="a3_incomplete")
    findings = complete.get("findings")
    return A3Result(
        overall_score=complete.get("overall_score"),
        findings_count=len(findings) if isinstance(findings, list) else 0,
        failure=None,
    )


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def judge_advice_snapshot(snapshot: dict, now: datetime) -> str:
    """C1 建議快照 → `generating`／`completed`／`failed`／`timeout`（`BR57.3`／`BR57.4`）。

    - `failed` 且 `unavailable_reasons.timed_out` 為真 → `timeout`；其他 `failed` → `failed`。
    - `generating` 且 `started_at` 距 `now` 已超過 5 分鐘 → `timeout`（不等本單元的
      360 秒上限）。
    - 未知的 status 視為 `failed`（不猜它的意思）。
    """
    status = snapshot.get("status")
    if status == ADVICE_COMPLETED:
        return ADVICE_COMPLETED
    if status == ADVICE_FAILED:
        reasons = snapshot.get("unavailable_reasons")
        if isinstance(reasons, dict) and reasons.get("timed_out"):
            return ADVICE_TIMEOUT
        return ADVICE_FAILED
    if status == ADVICE_GENERATING:
        started = _parse_iso(snapshot.get("started_at"))
        if started is not None and now - started > COST_ADVICE_STALE_AFTER:
            return ADVICE_TIMEOUT
        return ADVICE_GENERATING
    return ADVICE_FAILED


# ---------------------------------------------------------------------------
# 用戶端
# ---------------------------------------------------------------------------


class CapabilityClient:
    """以 ASGI 傳輸、帶使用者 token 呼叫既有端點。**每次使用新建、用完即關。**

    不建全域共用的 client：`Authorization` 標頭是 client 層級的設定，共用即可能
    讓一個使用者的 token 被另一個使用者的請求帶出去（`security-design.md` 第二節）。

    用法::

        async with CapabilityClient(app, token) as client:
            diagram = await client.get_diagram(12)
    """

    def __init__(self, app: Any, bearer_token: str) -> None:
        if not bearer_token:
            raise ValueError("bearer_token 不得為空（BR51.1：一律帶使用者本人的 token）")
        self._app = app
        self._token = bearer_token
        self._client: Optional[httpx.AsyncClient] = None
        #: 測試觀測用：本 client 讀過幾頁估價表清單（`NFR12.4`）。
        self.cost_pages_read = 0

    async def __aenter__(self) -> "CapabilityClient":
        self._client = httpx.AsyncClient(
            # raise_app_exceptions=False：app 內未處理的例外變成 500 回應，
            # 與「能力暫時無法使用」同一條路徑，不讓例外原文進入本單元。
            transport=httpx.ASGITransport(app=self._app, raise_app_exceptions=False),
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=None,
        )
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("CapabilityClient 必須以 async with 使用")
        try:
            response = await self._client.request(method, path, **kwargs)
        except Exception as exc:  # noqa: BLE001 - 整合邊界：只保留類別名
            raise CapabilityError(KIND_TRANSPORT, error_class=type(exc).__name__) from None
        if not 200 <= response.status_code < 300:
            raise CapabilityError(
                KIND_HTTP,
                status_code=response.status_code,
                draft_rejected=_is_draft_rejection(response),
                arch_forbidden=_is_arch_forbidden(response),
            )
        return response

    async def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._request(method, path, **kwargs)
        try:
            return response.json()
        except ValueError:
            raise CapabilityError(KIND_TRANSPORT, error_class="InvalidJSON") from None

    # -- 架構圖 -----------------------------------------------------------

    async def get_diagram(self, diagram_id: int) -> dict:
        data = await self._json("GET", f"/api/collab/diagrams/{int(diagram_id)}")
        return {
            "title": data.get("title"),
            "xml_data": data.get("xml_data"),
            "updated_at": data.get("updated_at"),
        }

    async def put_diagram(
        self, diagram_id: int, *, title: str, xml_data: str, finalize: bool = False
    ) -> None:
        """寫回架構圖。`finalize=True` 把草稿轉正式（契約 C2；大腦產圖存回成功時傳）。"""
        await self._request(
            "PUT",
            f"/api/collab/diagrams/{int(diagram_id)}",
            json={"xml_data": xml_data, "title": title, "finalize": bool(finalize)},
        )

    async def create_diagram(self, *, title: str, xml_data: str, system_id: int) -> int:
        """以使用者 token 經 C1 建立一張**草稿**（固定 `as_draft=true`），回新圖 id。

        261116-brain-create-diagram 契約 C7。失敗即 `CapabilityError`，**呼叫端不得重試**：
        傳輸錯誤或逾時時結果未知（可能已建立），重試會多出一張圖。
        """
        data = await self._json(
            "POST",
            "/api/collab/diagrams",
            json={
                "xml_data": xml_data,
                "title": title,
                "system_id": int(system_id),
                "as_draft": True,
            },
        )
        try:
            return int(data["id"])
        except (KeyError, TypeError, ValueError):
            raise CapabilityError(KIND_TRANSPORT, error_class="InvalidJSON") from None

    async def generate_architecture(
        self, request_text: str, current_xml: Optional[str]
    ) -> A1Result:
        response = await self._request(
            "POST",
            "/api/architecture/generate",
            json={
                "messages": [{"role": "user", "content": request_text}],
                "current_xml": current_xml,
            },
        )
        return judge_a1(parse_sse(response.text))

    # -- 架構檢視 ---------------------------------------------------------

    async def start_review(self, diagram_id: int) -> A3Result:
        response = await self._request(
            "POST",
            "/api/architecture/reviews",
            json={"diagram_id": int(diagram_id), "save_diagram": False},
        )
        return judge_a3(parse_sse(response.text))

    # -- 成本 -------------------------------------------------------------

    async def find_latest_estimate_set(self, diagram_ids: Iterable[int]) -> Optional[dict]:
        """依建立時間新到舊翻頁，回第一份 `diagram_id ∈ diagram_ids` 的估價表摘要。

        找到即停止翻頁（`NFR12.4`）；`diagram_id` 為空的估價表一律不採用（`BR56.3`）。
        """
        targets = {int(d) for d in diagram_ids}
        page = 1
        while page <= COST_LIST_MAX_PAGES:
            data = await self._json(
                "GET",
                "/api/cost/v1/sets",
                params={
                    "include_history": "true",
                    "page": page,
                    "page_size": COST_LIST_PAGE_SIZE,
                },
            )
            self.cost_pages_read += 1
            items = data.get("items") or []
            for item in items:
                diagram_id = item.get("diagram_id")
                if diagram_id is not None and int(diagram_id) in targets:
                    return item
            total = int(data.get("total") or 0)
            if not items or page * COST_LIST_PAGE_SIZE >= total:
                return None
            page += 1
        return None

    async def get_advice_snapshot(self, set_id: int) -> dict:
        return await self._json("GET", f"/api/cost/v1/sets/{int(set_id)}/advice")


__all__ = [
    "ADVICE_COMPLETED",
    "ADVICE_FAILED",
    "ADVICE_GENERATING",
    "ADVICE_TIMEOUT",
    "COST_ADVICE_STALE_AFTER",
    "A1Result",
    "A3Result",
    "BASE_URL",
    "COST_LIST_MAX_PAGES",
    "COST_LIST_PAGE_SIZE",
    "CapabilityClient",
    "CapabilityError",
    "KIND_HTTP",
    "KIND_TRANSPORT",
    "judge_a1",
    "judge_a3",
    "judge_advice_snapshot",
    "parse_sse",
]
