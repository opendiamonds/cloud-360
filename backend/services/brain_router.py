"""大腦的 WebSocket gateway —— **DEMO SCOPE，非 U13 的正式交付**。

範圍聲明（請先讀，這決定了你該怎麼看這支檔）
------------------------------------------------
本檔是為了**今晚的成果展示**而寫的最小垂直切片，**不屬於任何已核可的 AI-DLC 工作單元**。
大腦本體的正式交付是 `U11 intent-router`（意圖路由）、`U13 brain-gateway`（本端點）與
`U14 entry-page-ui`（入口頁），三者都還沒開始。

**它刻意實作的**（都來自 `brain-ws-contract` 已完成的 functional-design）：
  * 訊息封包 `{v, type, turnId, payload}`，`v` 為字面值 1
  * 握手：token 走 `Sec-WebSocket-Protocol`（**不是** query string）、`record=True`
  * 版本協商：`hello {v}` → `ready {protocolVersion}`，不符以 4400 關閉並帶 expected／received
  * 九種伺服器訊息裡的 `ready`／`token`／`clarify`／`work_items`／`done`／`error`
  * 六種客戶端訊息裡的 `hello`／`user_message`／`select_clarify_candidate`／`set_work_target`
  * 終止語意：零內容不得以 `done` 結束，一律走 `error(EMPTY_RESPONSE)`
  * `error.code` 的封閉四值

**它刻意沒有實作的**（留給正式單元，不要誤以為缺漏）：
  * Redis session 持久化 → `U10 session-store`（本檔用行程內 dict，故重啟即失憶；
    `K-12` 已記載「單一後端行程」這個假設，本檔沿用它）
  * 真正的意圖路由與信心值模型 → `U11`（本檔用關鍵詞計分，見 `_classify`）
  * 專案／系統／架構圖三層階層 → `U7 hierarchy-service`
  * 三層記憶 → `U5`／`U8`／`U9`
  * `cost_card`／`sharing_mode` 兩種訊息、多連線扇出、`correct_work_item`
  * `ws-contract.json` 與型別檔的兩道 CI 漂移閘門 → `U2` 的 code-generation

**替代方式**：`U13` 落地時**整支取代本檔**（而不是逐段改寫）。本檔不被任何既有模組 import，
移除它只需刪檔並移除 `main.py` 的一行 `include_router`。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from fastapi import APIRouter, WebSocket
from fastapi.exceptions import HTTPException
from starlette.websockets import WebSocketDisconnect

from database import SessionLocal
from services.auth import get_user_from_token
from services.prompt_guard import is_platform_self_modification

logger = logging.getLogger("cloud360.brain_router")

router = APIRouter()

# --- 契約常數（與 functional-design 的 entities.md 一致）-----------------------

PROTOCOL_VERSION = 1

CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_VERSION_MISMATCH = 4400
CLOSE_INTERNAL = 1011

ERROR_CODES = ("EMPTY_RESPONSE", "INTERNAL_ERROR", "UNAUTHORIZED", "INVALID_REQUEST")

# 非輪次訊息的 turnId 必為 null；輪次訊息必為非 null（BR1.6）
NON_TURN_TYPES = frozenset({"ready", "sharing_mode", "work_target", "work_items"})

MAX_TEXT_CHARS = 4000


# --- session 狀態（DEMO：行程內；正式落點 U10 session-store）-------------------


@dataclass
class _Session:
    """一個使用者一個 session（`[DD:E6]`=A 的單一 key 模型）。"""

    project_id: str | None = None
    system_id: str | None = None
    diagram_id: str | None = None
    pending_candidates: dict[str, dict[str, Any]] = field(default_factory=dict)
    work_items: list[dict[str, Any]] = field(default_factory=list)


_SESSIONS: dict[str, _Session] = {}


def _session_for(user_id: int) -> _Session:
    """session key 由已驗證使用者 id 推導（`K-12` x-session-key-derivation）。"""
    key = f"brain:{user_id}"
    if key not in _SESSIONS:
        _SESSIONS[key] = _Session()
    return _SESSIONS[key]


# --- 意圖分類（DEMO：關鍵詞計分；正式落點 U11 intent-router）-------------------

_CAPABILITIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "architecture-design",
        "架構設計",
        ("架構", "畫圖", "圖", "drawio", "diagram", "設計", "元件", "vpc", "部署圖"),
    ),
    (
        "well-architected-review",
        "架構評核",
        ("評核", "檢查", "review", "well-architected", "風險", "建議", "改善"),
    ),
    (
        "cost-finops",
        "成本與 FinOps",
        ("成本", "費用", "價格", "報價", "cost", "預算", "省錢", "finops", "估價"),
    ),
)


def _classify(text: str) -> list[dict[str, Any]]:
    """回傳依信心值排序的候選判讀。

    信心值定義域 0–1（`AC1.2.4`），容許為 None（`BR2.3`：`confidence` 選填）。
    **這是 DEMO 的計分法，不是 U11 的模型**：命中一個關鍵詞得 0.45，第二個起每個 +0.25，
    上限 0.95。刻意讓「單一模糊詞」落在 0.7 門檻之下，使 `clarify` 路徑可被展示。
    """
    lowered = text.lower()
    scored: list[dict[str, Any]] = []
    for cap_id, label, keywords in _CAPABILITIES:
        hits = sum(1 for k in keywords if k in lowered)
        if hits == 0:
            continue
        confidence = min(0.95, 0.45 + 0.25 * (hits - 1))
        scored.append(
            {
                "id": f"{cap_id}:{uuid.uuid4().hex[:8]}",
                "label": label,
                "capability": cap_id,
                "confidence": round(confidence, 2),
            }
        )
    scored.sort(key=lambda c: c["confidence"], reverse=True)
    return scored


CONFIDENCE_THRESHOLD = 0.7


# --- 回應器：有 LLM key 走真模型，沒有走本機確定性回應 ------------------------


def _llm_available() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY", "").strip())


async def _respond(capability: str, text: str) -> AsyncIterator[str]:
    """產生回覆的 token 串流。

    **零內容是允許的結果**——呼叫端據此送 `error(EMPTY_RESPONSE)` 而非 `done`（`BR2.6`）。
    """
    if _llm_available():
        try:
            async for chunk in _respond_via_llm(capability, text):
                yield chunk
            return
        except Exception as exc:  # 外部依賴邊界：降級並記 log，不靜默
            logger.warning("大腦 LLM 路徑失敗，降級為本機回應器: %s", exc)

    async for chunk in _respond_locally(capability, text):
        yield chunk


async def _respond_via_llm(capability: str, text: str) -> AsyncIterator[str]:
    """真模型串流（僅在有 `OPENROUTER_API_KEY` 時走此路）。"""
    from services.langgraph_runtime import astream_graph, openrouter_chat_model

    model = openrouter_chat_model()
    prompt = (
        f"你是 Cloud-360 的編排大腦。使用者的需求被判定為「{capability}」。"
        f"請以繁體中文用三到五句話說明你會如何處理，不要條列。\n\n需求：{text}"
    )
    async for event in astream_graph(model, prompt):
        piece = getattr(event, "text", None) or getattr(event, "content", None)
        if piece:
            yield piece


_LOCAL_SCRIPTS: dict[str, tuple[str, ...]] = {
    "architecture-design": (
        "收到，", "我把這件事交給", "架構設計 agent。", "它會先讀取目前的作業對象，",
        "再產生 draw.io 的元件與連線，", "完成後你會在架構圖頁看到結果。",
    ),
    "well-architected-review": (
        "收到，", "我交給架構評核 agent。", "它會依 Well-Architected 的六個支柱評分，",
        "把風險與建議逐條列出，", "並標出哪些是高優先。",
    ),
    "cost-finops": (
        "收到，", "我交給成本與 FinOps agent。", "它會讀取你上傳的官方估價表，",
        "算出每月與年度費用，", "並把可省的部分整理成建議。",
    ),
}


async def _respond_locally(capability: str, text: str) -> AsyncIterator[str]:
    """本機確定性回應器——無外部依賴，使展示在沒有 LLM key 時仍成立。"""
    for piece in _LOCAL_SCRIPTS.get(capability, ("我目前還沒有能處理這個需求的能力。",)):
        await asyncio.sleep(0.12)  # 讓串流在畫面上看得出來是逐段到達的
        yield piece


# --- 封包構造（BR1.1／BR1.2／BR1.6）------------------------------------------


def _envelope(msg_type: str, payload: dict[str, Any], turn_id: str | None) -> str:
    """構造一則伺服器訊息。

    `BR1.6`：非輪次訊息的 `turnId` 必為 null，輪次訊息必為非 null。本函式**強制**它，
    而不是信任呼叫端——契約不變量由構造點守住比由呼叫點守住可靠。
    """
    if msg_type in NON_TURN_TYPES:
        turn_id = None
    elif turn_id is None:
        raise ValueError(f"輪次訊息 {msg_type} 必須帶 turnId（BR1.6）")
    return json.dumps(
        {"v": PROTOCOL_VERSION, "type": msg_type, "turnId": turn_id, "payload": payload},
        ensure_ascii=False,
    )


async def _send(ws: WebSocket, msg_type: str, payload: dict[str, Any], turn_id: str | None = None) -> None:
    await ws.send_text(_envelope(msg_type, payload, turn_id))


async def _send_error(ws: WebSocket, code: str, message: str, turn_id: str) -> None:
    assert code in ERROR_CODES, f"error.code 必須取自封閉四值（BR2.8）: {code}"
    await _send(ws, "error", {"code": code, "message": message, "turnId": turn_id}, turn_id)


# --- 端點 ---------------------------------------------------------------------


@router.websocket("/ws")
async def brain_ws(websocket: WebSocket) -> None:
    """大腦的唯一 WebSocket 端點（掛在 `/api/brain/ws`）。

    三項硬約束（`K-12` x-hard-constraints）本檔逐條遵守：
      * 掛在 `/api/` 之下 —— nginx 只對該 location 帶 Upgrade 標頭
      * token 走 `Sec-WebSocket-Protocol`，**不得**放 query string（既有前例
        `collab_router.py:270` 正是 query string，本檔不照抄）
      * 握手以 `record=True` 呼叫 `get_user_from_token`，使帳號活動稽核不失效
    """
    # --- 握手 step 1：token 走 subprotocol 標頭 ---
    offered = websocket.headers.get("sec-websocket-protocol", "")
    token = ""
    for part in (p.strip() for p in offered.split(",")):
        if part.startswith("bearer."):
            token = part[len("bearer.") :]
            break

    if not token:
        await websocket.close(code=CLOSE_UNAUTHORIZED, reason="缺少憑證")
        return

    db = SessionLocal()
    try:
        user = get_user_from_token(token, db, record=True)  # record=True：AC8.1.2
        user_id, username = user.id, user.username
    except HTTPException:
        await websocket.close(code=CLOSE_UNAUTHORIZED, reason="憑證無效或已過期")
        return
    except Exception as exc:
        logger.warning("大腦握手失敗: %s", exc)
        await websocket.close(code=CLOSE_INTERNAL, reason="握手失敗")
        return
    finally:
        db.close()

    # subprotocol 必須回送客戶端提供的那一個，否則瀏覽器會拒絕連線
    await websocket.accept(subprotocol=f"bearer.{token}")
    session = _session_for(user_id)
    logger.info("大腦連線建立 user=%s", username)

    try:
        # --- 握手 step 2–3：版本協商（首則訊息必須是 hello）---
        first = json.loads(await websocket.receive_text())
        if first.get("type") != "hello":
            await _send_error(websocket, "INVALID_REQUEST", "首則訊息必須是 hello", "handshake")
            await websocket.close(code=CLOSE_VERSION_MISMATCH, reason="首則訊息必須是 hello")
            return

        received = first.get("payload", {}).get("v")
        if received != PROTOCOL_VERSION:
            await websocket.close(
                code=CLOSE_VERSION_MISMATCH,
                reason=f"協定版本不相容 expected={PROTOCOL_VERSION} received={received}",
            )
            return

        await _send(websocket, "ready", {"protocolVersion": PROTOCOL_VERSION})
        # 連線建立時推送當前作業對象，使脈絡列立即正確（K-12 on_connect）
        await _send(
            websocket,
            "work_target",
            {
                "projectId": session.project_id,
                "systemId": session.system_id,
                "diagramId": session.diagram_id,
            },
        )

        # --- 訊息迴圈 ---
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(websocket, "INVALID_REQUEST", "訊息不是合法 JSON", "malformed")
                continue

            if "turnId" in msg and msg["turnId"] is not None:
                # BR2.13：客戶端不得攜帶 turnId
                await _send_error(
                    websocket, "INVALID_REQUEST", "客戶端訊息不得攜帶 turnId", "protocol"
                )
                continue

            kind = msg.get("type")
            payload = msg.get("payload") or {}

            if kind == "set_work_target":
                session.project_id = payload.get("projectId")
                session.system_id = payload.get("systemId")
                session.diagram_id = payload.get("diagramId")
                await _send(
                    websocket,
                    "work_target",
                    {
                        "projectId": session.project_id,
                        "systemId": session.system_id,
                        "diagramId": session.diagram_id,
                    },
                )
                continue

            if kind == "select_clarify_candidate":
                candidate_id = payload.get("candidateId")
                if candidate_id is None:
                    # BR2.14：null ＝「都不是」→ 結束該輪，不送任何狀態訊息與終止事件
                    session.pending_candidates.clear()
                    continue
                candidate = session.pending_candidates.get(candidate_id)
                if candidate is None:
                    await _send_error(
                        websocket, "INVALID_REQUEST", "候選不存在或已失效", "select"
                    )
                    continue
                session.pending_candidates.clear()
                await _run_turn(websocket, session, candidate["capability"], candidate["text"])
                continue

            if kind == "user_message":
                text = (payload.get("text") or "").strip()
                if not text:
                    await _send_error(websocket, "INVALID_REQUEST", "需求不可為空", "input")
                    continue
                if len(text) > MAX_TEXT_CHARS:
                    await _send_error(websocket, "INVALID_REQUEST", "需求過長", "input")
                    continue

                # 平台自我竄改預檢（project.md ## Mandated：命中則不呼叫 LLM）
                if is_platform_self_modification(text):
                    turn_id = uuid.uuid4().hex
                    await _send(
                        websocket, "token", {"text": "此需求毫無相關，請重新輸入"}, turn_id
                    )
                    await _send(websocket, "done", {"turnId": turn_id}, turn_id)
                    continue

                candidates = _classify(text)
                top = candidates[0] if candidates else None

                if top is None or top["confidence"] < CONFIDENCE_THRESHOLD:
                    # AC1.2.1：信心不足 → 不建立任何工作項，列候選反問
                    turn_id = uuid.uuid4().hex
                    shown = candidates or [
                        {
                            "id": f"{cap}:{uuid.uuid4().hex[:8]}",
                            "label": label,
                            "capability": cap,
                            "confidence": None,
                        }
                        for cap, label, _ in _CAPABILITIES
                    ]
                    session.pending_candidates = {
                        c["id"]: {"capability": c["capability"], "text": text} for c in shown
                    }
                    await _send(websocket, "clarify", {"candidates": shown}, turn_id)
                    continue

                await _run_turn(websocket, session, top["capability"], text)
                continue

            await _send_error(websocket, "INVALID_REQUEST", f"未知的訊息型別: {kind}", "protocol")

    except WebSocketDisconnect:
        logger.info("大腦連線中斷 user=%s", username)
    except Exception as exc:
        logger.exception("大腦連線異常 user=%s: %s", username, exc)
        try:
            await websocket.close(code=CLOSE_INTERNAL, reason="伺服器內部錯誤")
        except Exception:
            pass


async def _run_turn(
    websocket: WebSocket, session: _Session, capability: str, text: str
) -> None:
    """跑一輪：回報工作項 → 串流 token → 終止事件。"""
    turn_id = uuid.uuid4().hex
    label = next((lb for cid, lb, _ in _CAPABILITIES if cid == capability), capability)

    work_item = {
        "workItemId": uuid.uuid4().hex[:8],
        "label": f"{label}：{text[:24]}",
        "status": "處理中",
        "capability": capability,
        "waitingOn": None,
        "failureReason": None,
        "sideEffect": "none",
    }
    session.work_items = [work_item]
    await _send(websocket, "work_items", {"items": session.work_items})

    produced = False
    try:
        async for piece in _respond(capability, text):
            if piece and piece.strip():  # BR2.1：空白 token 不算內容
                produced = True
                await _send(websocket, "token", {"text": piece}, turn_id)
    except Exception as exc:
        logger.exception("大腦回應失敗: %s", exc)
        work_item["status"] = "失敗"
        work_item["failureReason"] = "回應產生失敗"
        work_item["sideEffect"] = "unknown"  # 誠實：不承諾沒有半成品
        await _send(websocket, "work_items", {"items": session.work_items})
        await _send_error(websocket, "INTERNAL_ERROR", "回應產生失敗", turn_id)
        return

    if not produced:
        # BR2.6：零內容不得以 done 結束
        work_item["status"] = "失敗"
        work_item["failureReason"] = "未產出有效回覆"
        await _send(websocket, "work_items", {"items": session.work_items})
        await _send_error(websocket, "EMPTY_RESPONSE", "這一輪沒有產出可呈現的回覆", turn_id)
        return

    work_item["status"] = "完成"
    await _send(websocket, "work_items", {"items": session.work_items})
    await _send(websocket, "done", {"turnId": turn_id}, turn_id)
