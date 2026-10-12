"""
requirement_field_router.py — `U20 requirement-field-service` 的 HTTP 表面

**契約（前端依賴，請勿變更）**

三條路由，掛在 `main.py` 的 `/api/requirements` 之下：

| 方法與路徑 | facade | 成功 | 錯誤 |
|---|---|---|---|
| `GET /systems/{system_id}/fields` | `read_fields` | 200 `FieldSetView` | 403／404／422 |
| `PUT /systems/{system_id}/fields/{agent_group}/{field_key}` | `write_field_from_body` | 200 `FieldView` | 403／404／422 |
| `DELETE /systems/{system_id}/fields/{agent_group}/{field_key}` | `clear_field` | 200 `FieldView` | 403／404／422 |

- **沒有「只回計數」的端點**（`BR44.4`／`NFR20.3`）：總覽籤與需求籤讀同一個 `GET` 的
  同一個回應。
- `DELETE` 回 200 與清空後的 `FieldView`，不回 204：清空不刪列（`ADR-015`），而呼叫端
  需要知道結果是 `cleared` 還是 no-op 後的 `never_filled`（`BR43.3`）。
- 寫入與清空的回應**只含單一 `FieldView`、不含計數**（`NFR20.5`）。畫面要的新計數由
  `U23` 重讀 `GET` 取得，不得在前端以本地加減推算（`OPEN-RF20-3`）。

每個 handler 只做三件事：**取身分 → 呼叫 facade → 轉譯例外**。**本層不做任何授權判定**，
也不 import `requirement_field_service`——facade 是唯一授權入口（`K-17`）。

## 為什麼這裡沒有 `require_story_action`（`BR41.2`）

全域層 `K4` 在 `RequirementFieldFacade` 內以 `user_can` 評估，因為 `U13 brain-gateway`
是同進程呼叫端、沒有 dependency 鏈。dependency 只有 `get_current_user`（取身分），
與 `memory_router` 同形、與 `membership_router` 刻意不同。

## 為什麼框架不驗證本體與 `system_id`（`BR41.5`／`BR46.4`／`NFR20.14`）

FastAPI 的請求驗證在 handler **之前**執行：讓它驗本體，待核准或無權限者送一個壞本體會先
得到 422 而不是 403（授權先於驗證的順序被破壞，拒絕 log 也不會寫），而且框架 422 的
`detail` 會回顯輸入值。所以：

- `system_id`、`agent_group`、`field_key` 都以**字串**接收；非整數的 `system_id` 由 facade
  在授權之後判為 404。
- `PUT` 本體以原始位元組讀入（`_read_raw_body`，非同步 dependency；handler 本身仍是同步的、
  跑在 threadpool），授權通過後才由 facade 解析。`requestBody` 以 `openapi_extra` 宣告
  `RequirementFieldWriteIn` 的 schema，使產生的型別檔仍有本體形狀。

於是本 router 的每一個 422 都來自領域例外。**`detail` 沿用既有 router 的固定字串形狀**
（`membership_router._translate`：`detail=str(exc)`），字串由 `requirement_field_errors`
從固定集合產生，不含欄位值、不含代寫標示的值（`BR46.3`）。三條路由一致宣告
403／404／422 並給 `RequirementFieldErrorOut` 為 model，覆寫框架預設的
`HTTPValidationError`——後者的形狀本 router 永遠不會回（`BR46.1`）。

**不改任何全域 exception handler**：那會改變其他既有端點的 422 形狀。

## 掛在既有 `/api/` 之下，不新增監聽埠

`deploy/nginx.conf` 只反向代理 `/api/`；本單元零新進程、零新環境變數（`NFR8.120`）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.auth import get_current_user
from services.hierarchy_facade import mint_principal
from services.requirement_field_errors import (
    RequirementFieldError,
    RequirementFieldForbidden,
    RequirementFieldNotFound,
    RequirementFieldValidationError,
    UnknownFieldKey,
)
from services.requirement_field_facade import RequirementFieldFacade
from services.requirement_field_types import (
    FieldSetView,
    FieldView,
    RequirementFieldWriteIn,
)

router = APIRouter(tags=["requirements"])


class RequirementFieldErrorOut(BaseModel):
    """403／404／422 的回應本體。`detail` 為固定文字，不含任何輸入值。"""

    detail: str


ERROR_RESPONSES = {
    status.HTTP_403_FORBIDDEN: {
        "model": RequirementFieldErrorOut,
        "description": (
            "授權未通過：帳號待核准、缺全域功能權限 K4（讀需 view、寫與清空需 edit），"
            "或不是該系統所屬專案的成員"
        ),
    },
    status.HTTP_404_NOT_FOUND: {
        "model": RequirementFieldErrorOut,
        "description": "查不到該系統（含非整數的 system_id）",
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "model": RequirementFieldErrorOut,
        "description": (
            "未宣告的 agent 組或欄位（含錯綁到別組）、代寫標示不是已宣告的組、"
            "值超過 2000 字、代寫路徑的空值，或請求本體形狀錯誤（含未宣告欄位如 "
            "updated_by）。只在授權通過之後才可能出現"
        ),
    },
}
"""`BR46.1`：必須顯式宣告，否則不進 `openapi.json` 與產生的型別檔，而 CI 保持綠燈。"""

_WRITE_BODY_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": RequirementFieldWriteIn.model_json_schema(),
            }
        },
    }
}


async def _read_raw_body(request: Request) -> bytes:
    """讀原始本體，不解析。解析在 facade 內、授權之後（`BR46.4`）。"""
    return await request.body()


def _translate(exc: RequirementFieldError) -> HTTPException:
    """把領域例外轉成 HTTP。**這是唯一的轉譯點。**"""
    if isinstance(exc, RequirementFieldForbidden):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, RequirementFieldNotFound):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, (UnknownFieldKey, RequirementFieldValidationError)):
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    else:  # pragma: no cover - 新增例外型別而未登錄時，寧可 500 也不猜狀態碼
        raise exc
    return HTTPException(status_code=code, detail=str(exc))


@router.get(
    "/systems/{system_id}/fields",
    response_model=FieldSetView,
    responses=ERROR_RESPONSES,
)
def read_requirement_fields(
    system_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """某系統的全部需求欄位：分組明細與未填數，同一次查詢（`US11.2`／`US11.3`）。"""
    try:
        return RequirementFieldFacade(db).read_fields(
            mint_principal(current_user), system_id=system_id
        )
    except RequirementFieldError as exc:
        raise _translate(exc) from exc


@router.put(
    "/systems/{system_id}/fields/{agent_group}/{field_key}",
    response_model=FieldView,
    responses=ERROR_RESPONSES,
    openapi_extra=_WRITE_BODY_OPENAPI,
)
def write_requirement_field(
    system_id: str,
    agent_group: str,
    field_key: str,
    body: bytes = Depends(_read_raw_body),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """寫入一個欄位。**冪等**：重送相同本體覆寫同一列（`NFR20.21`）。

    本體 `{ "value": str, "on_behalf_of": str | null }`。不帶 `on_behalf_of` 而值只有
    空白時視為清空（`BR43.2`）；帶 `on_behalf_of` 時空值被拒（`BR42.5`）。
    """
    try:
        return RequirementFieldFacade(db).write_field_from_body(
            mint_principal(current_user),
            system_id=system_id,
            agent_group=agent_group,
            field_key=field_key,
            body=body,
        )
    except RequirementFieldError as exc:
        raise _translate(exc) from exc


@router.delete(
    "/systems/{system_id}/fields/{agent_group}/{field_key}",
    response_model=FieldView,
    responses=ERROR_RESPONSES,
)
def clear_requirement_field(
    system_id: str,
    agent_group: str,
    field_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清空一個欄位（保留列、記清空時間與清空者，`ADR-015`）。**冪等**（`NFR20.22`）。"""
    try:
        return RequirementFieldFacade(db).clear_field(
            mint_principal(current_user),
            system_id=system_id,
            agent_group=agent_group,
            field_key=field_key,
        )
    except RequirementFieldError as exc:
        raise _translate(exc) from exc
