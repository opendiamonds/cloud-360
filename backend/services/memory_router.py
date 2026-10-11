"""
memory_router.py — `U8 memory-service` 的 HTTP 表面

**契約（前端依賴，請勿變更）**

每個 handler 只做三件事：**取身分 → 呼叫 facade → 轉譯例外**。

**本層不做任何授權判定**（`logical-components.md §1.1`）。違反它會壞掉的是：
授權就有了第二份實作，而 `K-08` 的 `sole_entry` 保證失效，兩份實作遲早分歧。
故本檔**不 import `memory_service`**，也**不含任何角色名稱**——角色集合的唯一
落點是 `memory_types.SCOPE_WIDENING_ROLES`，由 `MemoryFacade` 讀它。
`tests/test_memory_contract.py` 的 `C3` 機械斷言這件事。

## 授權掛在哪一層：與 `U19` 刻意不同

`membership_router` 把全域那一層掛在 `require_story_action("K3", ...)` 這個
dependency 上，因為 `K-16` 有「兩層串聯」且指名了第一層的承載者。

**`K-08` 沒有那一條**，而且它逐字寫下了相反的事：

> 路由守衛：`/memory` 走 `ProtectedRoute` 但**不包** `CapabilityRoute`
> （前例 `App.tsx:37–44`），把關的是**擁有者欄位而非角色**，
> 故**不需新 story id**（`[DM:D1]`=C 的查證）。

故本檔的 dependency 只有 `get_current_user`（任何已認證使用者），
**沒有** `require_story_action`。記憶的把關全在 facade：擁有者模型用列的欄位、
角色模型讀 `principal.role`——兩者都不經 `role_permissions` 矩陣。

## `DELETE` 沒有 403，而那是刻意的（`[D1]`=A）

`K-08` 的 OpenAPI 半邊宣告 `DELETE` 有 `403` 與 `404`。
`nfr-design/security-design.md §二` 的 `[D1]`=A 把「非擁有者」收斂進 404，
故**刪除路徑的 403 不再可達**，`responses` 也因此不宣告它。

理由：`schema_rbac.sql` 的 `id SERIAL PRIMARY KEY` 是連續整數，403／404 的差異
讓任何已認證使用者得以走訪 `1..N` 取得整張表哪些 id 存在。

**這是對已核可契約的偏離，已記為 `D8-1`**（下一輪契約修訂追認）；
`openapi.json` 的回應集合變更已記為 `D8-2`。本單元**不改已核可的契約檔**。

## 本檔有五條路由，不是六條

`functional-spec.md §〇` 的表有六列，但第 2 列（`MemoryFacade.search`）的 HTTP
欄逐字是「—（同進程，`U11` 消費）」，而
`infrastructure-design/cicd-pipeline.md §三之一` 再次確認「`search` 有 HTTP
端點嗎 → **沒有**」。故對外是五條；`code-generation-plan.md` Step 5.5 的
「六條路由」數到的是那六個 facade 方法。**不為 `search` 開端點**——那會同時
牴觸上述兩處已核可敘述，並讓它落進「四條端點 allow/deny」之外的新測試桶。

## 掛在既有 `/api/` 之下，不新增監聽埠

`deploy/nginx.conf` 只反向代理 `/api/`，而本單元零新進程、零新環境變數、
**不改 `deploy/` 任何檔案**（`NFR8.20`）。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.auth import get_current_user
from services.embedding_port import EmbeddingProviderUnavailable
from services.memory_errors import (
    MemoryForbidden,
    MemoryInvalidInput,
    MemoryNotFound,
)
from services.memory_facade import MemoryFacade, mint_principal
from services.memory_types import MEMORY_KINDS, MemoryAuditEventView, MemoryView

logger = logging.getLogger("cloud360.memory_router")

router = APIRouter(tags=["memory"])

FORBIDDEN_RESPONSE = {status.HTTP_403_FORBIDDEN: {"description": "授權未通過"}}
NOT_FOUND_RESPONSE = {status.HTTP_404_NOT_FOUND: {"description": "找不到該記憶"}}
UNPROCESSABLE_RESPONSE = {
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "輸入不合封閉集合或欄位約束"}
}
UNAVAILABLE_RESPONSE = {
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "embedding 提供者不可用"}
}


class MemoryCreateRequest(BaseModel):
    """`POST /api/memory/records` 的酬載（`BR7.3`／`[FD4]`=A）。

    ## `model_config` 刻意**不**設 `extra="forbid"`

    `BR1.2`／`NFR7.20` 要求酬載中任何意圖指定擁有者的欄位**被忽略且不回報
    錯誤**。`extra="forbid"` 會讓它回 422，直接違反該規則；而回 422 會讓呼叫端
    以為「換個欄位名就能指定」，**忽略使該能力不存在**。

    同理 `visibilityScope` 也不是本模型的欄位（`NFR7.21`）：新記憶的可見範圍
    一律為最窄，放寬是獨立的、需授權的操作（`BR5.1`）。

    故本模型**只有兩個欄位**，而這個「少」是規則本身，不是未完成。
    `test_memory_authz` 第 11 條驗的正是帶了那兩欄仍**回成功而非 422**。
    """

    model_config = ConfigDict(extra="ignore")

    kind: str = Field(
        description="三種記憶之一：" + "｜".join(MEMORY_KINDS),
        examples=[MEMORY_KINDS[0]],
    )
    content: str = Field(description="記憶的文字內容；去除前後空白後須非空")


class MemoryScopeRequest(BaseModel):
    """`PUT /api/memory/records/{memoryId}/scope` 的酬載（`BR5.2`）。"""

    model_config = ConfigDict(extra="ignore")

    visibility_scope: str = Field(
        description="目標可見範圍。只接受比現行**更寬**的值（放寬只有一個方向）"
    )


def _translate(exc: Exception) -> HTTPException:
    """把領域例外轉成 HTTP。**這是唯一的轉譯點。**

    `MemoryNotFound` → 404 這一列承載 `[D1]`=A：刪除路徑的「非擁有者」也走
    這裡，故它與「不存在」得到**同一個** 404。`detail` 來自例外本身，而該例外
    刻意不帶任何查到的欄位——若兩種情境的 `detail` 不同，枚舉 oracle 就從
    狀態碼搬到了回應本體裡，收斂等於沒做。
    """
    if isinstance(exc, MemoryForbidden):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, MemoryNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, MemoryInvalidInput):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    if isinstance(exc, EmbeddingProviderUnavailable):
        # 外部依賴邊界：大聲失敗並把可選值帶給呼叫端（`NFR7.32`／`NFR4.22`）。
        # **不降級為其他提供者**——靜默降級會讓整批記憶以錯的提供者寫入而
        # 無人察覺，之後 `BR3.2` 的分群使它們永久不可被檢索到。
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    raise exc


# ---------------------------------------------------------------------------
# 1：建立（**本站唯一的契約增量**，`[FD4]`=A）
# ---------------------------------------------------------------------------


@router.post(
    "/records",
    response_model=MemoryView,
    status_code=status.HTTP_201_CREATED,
    responses={**UNPROCESSABLE_RESPONSE, **UNAVAILABLE_RESPONSE},
)
def create_memory(
    payload: MemoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手動建立一則記憶（`semantic` 的唯一來源，`BR7.3`）。

    **這個端點是 `AC4.1.3` 得以成立的原因**：少了它，`semantic` 永遠沒有資料，
    該 AC 的 Given「三種記憶各有資料」對 `semantic` 那一份不可構造
    （`rules.md` 的 `BR7.3` note）。

    `episodic` 與 `procedure` 的正常寫入端是 `U13`／`U12` 的**同進程**呼叫
    （`BR7.1`／`BR7.2`），不經本端點；本端點不限制 `kind`，因為
    `[FD4]`=A 逐字「`kind` 由使用者指定且限於封閉集合」。
    """
    facade = MemoryFacade(db)
    try:
        return facade.write(
            mint_principal(current_user),
            kind=payload.kind,
            content=payload.content,
        )
    except Exception as exc:
        raise _translate(exc)


# ---------------------------------------------------------------------------
# 2：列出（`NFR7.28` 分頁）
# ---------------------------------------------------------------------------


@router.get(
    "/records",
    response_model=List[MemoryView],
    responses={**FORBIDDEN_RESPONSE},
)
def list_memories(
    kind: Optional[List[str]] = Query(
        default=None, description="以 kind 收斂；未指定則三種皆納入"
    ),
    offset: int = Query(default=0, ge=0, description="分頁位移"),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        description="每頁筆數。**超過伺服器上限時收斂到上限而非照辦**",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出當前使用者可見的記憶（`BR2.2` 過濾）。

    **`limit` 的伺服器端上限在 service 層**（`memory_service.clamp_page_size`），
    不在這裡：`NFR7.29` 的判準是「以超大 `limit` 呼叫，回傳筆數不超過上限」，
    而把收斂寫成 `Query(le=...)` 會讓超大值得到 **422**——那是「照辦或拒絕」，
    不是「收斂」。`ge=1` 仍然宣告，因為負數與 0 是語意錯誤而非過大。

    **本路徑不回 404**：看不到別人的記憶不是錯誤狀態，只是較小的集合
    （`BR2.2` 的 `violation_behaviour` 逐字）。
    """
    facade = MemoryFacade(db)
    try:
        return facade.list_records(
            mint_principal(current_user),
            kinds=kind,
            offset=offset,
            page_size=limit,
        )
    except Exception as exc:
        raise _translate(exc)


# ---------------------------------------------------------------------------
# 3：刪除（`[D1]`=A：**無 403**）
# ---------------------------------------------------------------------------


@router.delete(
    "/records/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**NOT_FOUND_RESPONSE},
)
def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """刪除自己的記憶（留稽核，`BR4.2`）。

    **`memory_id` 宣告為 `str` 而非 `int`**，而這是 `[D1]`=A 的一部分：
    宣告 `int` 會讓 `DELETE /api/memory/records/abc` 回 **422**，而那等於告訴
    呼叫端「id 必須是整數」——`[D1]`=A 的整個目的就是不讓刪除路徑回答任何
    關於 id 空間的問題。`K-08` 的簽章逐字也是 `memory_id: str`
    （`entities.md`：「對外為不透明識別字」）。

    `responses` **刻意不含 403**：非擁有者收斂為 404（見檔頭）。
    """
    facade = MemoryFacade(db)
    try:
        facade.delete(mint_principal(current_user), memory_id)
    except Exception as exc:
        raise _translate(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 4：放寬可見範圍（角色模型；**有** 403）
# ---------------------------------------------------------------------------


@router.put(
    "/records/{memory_id}/scope",
    response_model=MemoryView,
    responses={**FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def widen_memory_scope(
    memory_id: str,
    payload: MemoryScopeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """放寬一則記憶的可見範圍（留稽核並帶前後值，`BR5.3`）。

    **本路徑保留 403**，與刪除路徑相反。差別不是不一致：facade 在此
    **先判角色、後取記憶**，故無權者在任何 id（含不存在的）上都得到同一個 403
    ——oracle 本來就不存在，不需要收斂（`security-design.md §三`）。
    """
    facade = MemoryFacade(db)
    try:
        return facade.widen_scope(
            mint_principal(current_user), memory_id, payload.visibility_scope
        )
    except Exception as exc:
        raise _translate(exc)


# ---------------------------------------------------------------------------
# 5：稽核查詢（角色模型）
# ---------------------------------------------------------------------------


@router.get(
    "/audit-events",
    response_model=List[MemoryAuditEventView],
    responses={**FORBIDDEN_RESPONSE},
)
def list_memory_audit_events(
    memory_id: Optional[str] = Query(
        default=None, description="以 memoryId 收斂；未指定則回全部"
    ),
    offset: int = Query(default=0, ge=0, description="分頁位移"),
    limit: Optional[int] = Query(
        default=None, ge=1, description="每頁筆數；超過伺服器上限時收斂"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """稽核事件查詢（`AC4.3.2`／`AC4.3.3`）。

    回傳元素帶 `memory_exists`：`memoryId` 指不到記憶的事件**仍然回傳**
    （`BR6.3`）。過濾掉它會讓 `FR4.7` 在 90 天後變成空話——稽核存在的全部
    理由就是記憶消失之後還答得出「誰刪的」。
    """
    facade = MemoryFacade(db)
    try:
        return facade.list_audit_events(
            mint_principal(current_user),
            memory_id=memory_id,
            offset=offset,
            page_size=limit,
        )
    except Exception as exc:
        raise _translate(exc)
