"""
requirement_field_facade.py — `U20 requirement-field-service` 的授權門面

**契約（前端與同進程呼叫端依賴，請勿變更）**

本模組是 `system_requirement_fields` 受保護操作的**唯一授權入口**（契約 `K-17` 的
`sole_entry`）。消費端：`U23 project-pages-ui`（HTTP，經 `requirement_field_router`）、
`U21 mcp-bridge`（獨立進程，經 HTTP 帶使用者 token）、`U13 brain-gateway`（**同進程**，
直接呼叫本類別）。三條路徑共用這一個入口，故授權判定只有一份呼叫點。

授權順序（`BR41.1`–`BR41.5`，任一步失敗即中止，之後的驗證與存取都不發生）
-----------------------------------------------------------------------------

1. **待核准帳號先拒**（`BR41.1`）：`principal.is_approved` 為 false → 403。
   `HierarchyFacade`／`MembershipFacade` 自身沒有這道檢查（`U15` 審查的 R-05），
   本 facade 不依賴它們擋待核准帳號。
2. **全域層在本 facade 內評估**（`BR41.2`）：讀需 `K4.view`、寫與清空需 `K4.edit`，
   以 `services.rbac.user_can` 判定。**router 不掛 `require_story_action`**——
   `U13` 是同進程呼叫端、沒有 dependency 鏈，掛在 router 會讓那條路徑只剩一層。
   這與 `K-17` 的 `own_responsibility`／`anti_double_check` 字面（「全域層由 router 的
   require_story_action 承擔」）不同，偏離已列入追認（`OPEN-RF20-5`）；`anti_double_check`
   要防的「同一層檢查兩次」仍成立——全域層在整條路徑上只評估這一次。
3. **系統存在與所屬專案**經 `HierarchyFacade.get_project_of_system`（`BR41.3`）；
   查不到、非整數的 `system_id`、或呼叫端缺 `K2.view` 一律 404。
4. **per-project 層**經 `MembershipFacade.resolve_project_role`（`BR41.4`，判定只有一份，
   `ADR-012`）：非成員 → 403；`project_admin` 與 `member` 都放行——寫入是否允許已由
   第 2 步的 `K4.edit` 決定（`[FD4]`=A）。

**依賴失敗即拒**（`NFR20.11`）：只把**已知的**領域例外轉成 404；其他例外一律不捕捉、
向上傳播成 500。不得寫成 `except Exception: allow`。

**代寫標示不授予權限**（`BR45.4`）：`on_behalf_of` 不參與上面任何一步。後果如實記下
（`OPEN-RF20-1`）：任何有寫入權的使用者都能把自己的寫入標成「由大腦代寫」；
`updated_by` 仍是本人，但標示本身可被自填。

請求本體在授權之後才解析（`BR46.4`）
-------------------------------------

`write_field_from_body` 給 HTTP 用：router 不讓框架驗證本體或 `system_id`，把原始位元組
交進來，本 facade **授權通過之後**才解析。於是任何 422 都晚於授權判定，且錯誤訊息是
`requirement_field_errors` 的固定文字、不回顯輸入。同進程呼叫端用 `write_field`。

交易與時間
----------

每次寫入或清空是**一個交易、一條寫入敘述**；失敗即 `rollback` 後重新拋出（`BR46.2`）。
時間戳由 `clock` 產生並傳入資料存取層（測試可注入固定時鐘；nfr-design `review-01` R-04）。

log（logger `"cloud360.requirement_fields"`，`observability-design.md`）
------------------------------------------------------------------------

`requirement_field.denied`（WARNING）、`requirement_field.written`／`.cleared`（INFO）。
欄位以 `extra=` 結構化帶入，並以**同一組白名單欄位**作為訊息參數（使容器 log 的預設
格式也看得到它們）——全部是整數或封閉集合的字串，**永不**含欄位值或代寫標示的值
（`NFR20.27`／`NFR20.28`）。no-op 清空不記 INFO（`NFR20.29`）。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Callable, Optional, Tuple

from pydantic import ValidationError
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from services.hierarchy_facade import (
    HierarchyFacade,
    HierarchyForbidden,
    HierarchyNotFound,
    Principal,
)
from services.membership_errors import MembershipNotFound
from services.membership_facade import MembershipFacade
from services.rbac import user_can
from services.requirement_field_definitions import (
    FIELD_GROUPS,
    GROUPS_BY_KEY,
    INPUT_HINT,
    MAX_VALUE_LENGTH,
    AgentFieldDefinition,
    AgentFieldGroup,
    find_group,
)
from services.requirement_field_errors import (
    STORY_ID,
    RequirementFieldForbidden,
    RequirementFieldNotFound,
    RequirementFieldValidationError,
    UnknownFieldKey,
)
import services.requirement_field_service as requirement_field_service
from services.requirement_field_types import (
    FieldGroupView,
    FieldSetView,
    FieldView,
    FilledState,
    RequirementFieldWriteIn,
)

logger = logging.getLogger("cloud360.requirement_fields")

#: `systems.id` 是 PostgreSQL 的 `SERIAL`（int4）。超出範圍的字串不可能是任何系統，
#: 直接當成「查不到」——否則它會一路走到資料庫並以 `integer out of range` 回 500。
MAX_SYSTEM_ID = 2_147_483_647
_SYSTEM_ID_PATTERN = re.compile(r"[0-9]{1,10}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def coerce_system_id(raw: object) -> Optional[int]:
    """把呼叫端給的 `system_id` 收斂成合法的整數；不可能是任何系統時回 `None`。

    接受 `int`（同進程呼叫端）與純數字字串（HTTP 路徑參數）。`bool` 雖是 `int`
    的子類別，但不是識別碼，一律拒絕。
    """
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str) and _SYSTEM_ID_PATTERN.fullmatch(raw):
        value = int(raw)
    else:
        return None
    return value if 0 <= value <= MAX_SYSTEM_ID else None


def derive_filled_state(row: Optional[Row]) -> FilledState:
    """`BR44.1`：對任何列（含無列與第四種列）都有定義的三態推導。"""
    if row is None:
        return FilledState.NEVER_FILLED
    if row.value is not None:
        return FilledState.FILLED
    if row.cleared_at is not None:
        return FilledState.CLEARED
    return FilledState.NEVER_FILLED


def build_field_view(
    group: AgentFieldGroup, definition: AgentFieldDefinition, row: Optional[Row]
) -> FieldView:
    """合成單一欄位的檢視。`never_filled` 的溯源欄位一律為 null（review-02 R-06）。"""
    state = derive_filled_state(row)
    view = FieldView(
        group_key=group.group_key,
        field_key=definition.field_key,
        label=definition.label,
        filled_state=state,
    )
    if state is FilledState.NEVER_FILLED:
        return view
    return view.model_copy(
        update={
            "value": row.value,
            "cleared_at": row.cleared_at,
            "updated_at": row.updated_at,
            "updated_by": row.updated_by,
            "updated_on_behalf_of": row.updated_on_behalf_of,
        }
    )


def compose_field_set(system_id: int, rows) -> FieldSetView:
    """由**同一份**列合成分組明細與全部計數（`BR44.2`–`BR44.6`，不變量 `I-4`）。

    以定義為主迴圈、列為查表：回應的欄位集合恆等於定義的欄位集合（`BR44.5`）；
    定義外的保留列不出現、不計數（`BR44.3`）。各組的 `filled_count` 與全體的
    `unfilled_count` 都由下面那一份 `views` 算出，不另查。
    """
    by_key = {(row.agent_group, row.field_key): row for row in rows}
    groups = []
    unfilled = 0
    for group in FIELD_GROUPS:
        views = [
            build_field_view(group, definition,
                             by_key.get((group.group_key, definition.field_key)))
            for definition in group.fields
        ]
        filled = sum(1 for view in views if view.filled_state is FilledState.FILLED)
        unfilled += len(views) - filled
        groups.append(
            FieldGroupView(
                group_key=group.group_key,
                title=group.title,
                filled_count=filled,
                total_count=len(views),
                fields=views,
            )
        )
    return FieldSetView(
        system_id=system_id,
        unfilled_count=unfilled,
        input_hint=INPUT_HINT,
        groups=groups,
    )


def parse_write_body(body: bytes) -> RequirementFieldWriteIn:
    """把 `PUT` 的原始本體解析成 `RequirementFieldWriteIn`（`BR46.4`）。

    錯誤一律轉成固定文字的 `RequirementFieldValidationError`；pydantic 的錯誤物件
    （含 `input`）不往外傳——`from None` 也讓它不出現在例外鏈裡。
    """
    try:
        return RequirementFieldWriteIn.model_validate_json(body or b"")
    except ValidationError as exc:
        field, problem = _classify_body_errors(
            exc.errors(include_input=False, include_url=False)
        )
    raise RequirementFieldValidationError(field, problem) from None


def _classify_body_errors(errors) -> Tuple[str, str]:
    kinds = [(error.get("type"), tuple(error.get("loc") or ())) for error in errors]
    if any(loc == () or kind in ("json_invalid", "json_type", "model_type")
           for kind, loc in kinds):
        return "body", "not_json_object"
    if any(kind == "extra_forbidden" for kind, _ in kinds):
        return "body", "unknown_field"
    if any(kind == "missing" for kind, _ in kinds):
        return "body", "missing_value"
    if any(loc[:1] == ("on_behalf_of",) for _, loc in kinds):
        return "on_behalf_of", "type"
    return "value", "type"


class RequirementFieldFacade:
    """受保護操作的唯一授權入口（契約 `K-17`）。"""

    def __init__(
        self, db: Session, *, clock: Optional[Callable[[], datetime]] = None
    ) -> None:
        self._db = db
        self._clock = clock or _utcnow

    # -- 授權（唯一一份，`BR41.1`–`BR41.5`）---------------------------------

    def _authorize(self, principal: Principal, system_id: object, action: str) -> int:
        """依序執行四步授權；通過回傳已驗證的整數 `system_id`。"""
        known_id = coerce_system_id(system_id)
        if not principal.is_approved:
            self._deny(principal, action, known_id, "pending")
        if not user_can(self._db, principal.role, STORY_ID, action):
            self._deny(principal, action, known_id, "global")
        if known_id is None:
            raise RequirementFieldNotFound()
        try:
            project_id = HierarchyFacade(self._db).get_project_of_system(
                principal, system_id=known_id
            )
        except (HierarchyNotFound, HierarchyForbidden) as exc:
            raise RequirementFieldNotFound(known_id) from exc
        try:
            role = MembershipFacade(self._db).resolve_project_role(
                principal, project_id=project_id
            )
        except MembershipNotFound as exc:
            raise RequirementFieldNotFound(known_id) from exc
        if role is None:
            self._deny(principal, action, known_id, "not_member")
        return known_id

    @staticmethod
    def _deny(
        principal: Principal, action: str, system_id: Optional[int], reason: str
    ) -> None:
        """`BR41.6`／`NFR20.27`：一行 WARNING，然後拒絕。不記值、不記代寫標示。"""
        logger.warning(
            "requirement_field.denied story_id=%s action=%s system_id=%s "
            "user_id=%s reason=%s",
            STORY_ID, action, system_id, principal.user_id, reason,
            extra={
                "story_id": STORY_ID,
                "action": action,
                "system_id": system_id,
                "user_id": principal.user_id,
                "reason": reason,
            },
        )
        raise RequirementFieldForbidden(
            action=action, reason=reason, system_id=system_id
        )

    @staticmethod
    def _resolve_field(
        agent_group: object, field_key: object
    ) -> Tuple[AgentFieldGroup, AgentFieldDefinition]:
        """`BR42.1`／`BR42.2`：組必須已宣告、key 必須在**該組**底下已宣告。"""
        group = find_group(agent_group)
        definition = group.find(field_key) if group is not None else None
        if group is None or definition is None:
            raise UnknownFieldKey(str(agent_group), str(field_key))
        return group, definition

    # -- 1. 讀取 -------------------------------------------------------------

    def read_fields(self, principal: Principal, *, system_id: object) -> FieldSetView:
        """`K-17` 的 `read_fields`：全部已宣告欄位的三態與計數，一次查詢（`BR44.4`）。"""
        known_id = self._authorize(principal, system_id, "view")
        rows = requirement_field_service.fetch_rows(self._db, system_id=known_id)
        return compose_field_set(known_id, rows)

    # -- 2. 寫入 -------------------------------------------------------------

    def write_field(
        self,
        principal: Principal,
        *,
        system_id: object,
        agent_group: str,
        field_key: str,
        value: object,
        on_behalf_of: object = None,
    ) -> FieldView:
        """`K-17` 的 `write_field`（同進程呼叫端用）。冪等：重送相同參數覆寫同一列。"""
        known_id = self._authorize(principal, system_id, "edit")
        group, definition = self._resolve_field(agent_group, field_key)
        return self._write_authorized(
            principal, known_id, group, definition, value, on_behalf_of
        )

    def write_field_from_body(
        self,
        principal: Principal,
        *,
        system_id: object,
        agent_group: str,
        field_key: str,
        body: bytes,
    ) -> FieldView:
        """HTTP 版的 `write_field`：本體在授權與定址驗證**之後**才解析（`BR46.4`）。"""
        known_id = self._authorize(principal, system_id, "edit")
        group, definition = self._resolve_field(agent_group, field_key)
        payload = parse_write_body(body)
        return self._write_authorized(
            principal, known_id, group, definition, payload.value, payload.on_behalf_of
        )

    def _write_authorized(
        self,
        principal: Principal,
        system_id: int,
        group: AgentFieldGroup,
        definition: AgentFieldDefinition,
        value: object,
        on_behalf_of: object,
    ) -> FieldView:
        if on_behalf_of is not None:
            if not isinstance(on_behalf_of, str):
                raise RequirementFieldValidationError("on_behalf_of", "type")
            if on_behalf_of not in GROUPS_BY_KEY:
                raise RequirementFieldValidationError("on_behalf_of", "unknown_group")
        if not isinstance(value, str):
            raise RequirementFieldValidationError("value", "type")

        stripped = value.strip()
        if not stripped:
            if on_behalf_of is not None:
                # BR42.5：代寫路徑的空值不是清空，是錯誤——否則使用者的值會被靜默清掉，
                # 而清空又會丟掉代寫標示，記成「本人清空」。
                raise RequirementFieldValidationError("value", "blank_on_behalf")
            return self._clear_authorized(principal, system_id, group, definition)
        if len(stripped) > MAX_VALUE_LENGTH:
            raise RequirementFieldValidationError("value", "too_long")

        try:
            row = requirement_field_service.upsert_value(
                self._db,
                system_id=system_id,
                agent_group=group.group_key,
                field_key=definition.field_key,
                value=stripped,
                updated_by=principal.user_id,
                on_behalf_of=on_behalf_of,
                now=self._clock(),
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._log_change(
            "requirement_field.written", "write", principal, system_id,
            group, definition, on_behalf=on_behalf_of is not None,
        )
        return build_field_view(group, definition, row)

    # -- 3. 清空 -------------------------------------------------------------

    def clear_field(
        self,
        principal: Principal,
        *,
        system_id: object,
        agent_group: str,
        field_key: str,
    ) -> FieldView:
        """`K-17` 的 `clear_field`。冪等：對從未填過或已清空的欄位為 no-op（`BR43.3`／`BR43.4`）。"""
        known_id = self._authorize(principal, system_id, "edit")
        group, definition = self._resolve_field(agent_group, field_key)
        return self._clear_authorized(principal, known_id, group, definition)

    def _clear_authorized(
        self,
        principal: Principal,
        system_id: int,
        group: AgentFieldGroup,
        definition: AgentFieldDefinition,
    ) -> FieldView:
        try:
            row = requirement_field_service.clear_if_filled(
                self._db,
                system_id=system_id,
                agent_group=group.group_key,
                field_key=definition.field_key,
                updated_by=principal.user_id,
                now=self._clock(),
            )
            changed = row is not None
            if not changed:
                row = requirement_field_service.fetch_row(
                    self._db,
                    system_id=system_id,
                    agent_group=group.group_key,
                    field_key=definition.field_key,
                )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        if changed:
            self._log_change(
                "requirement_field.cleared", "clear", principal, system_id,
                group, definition, on_behalf=False,
            )
        return build_field_view(group, definition, row)

    # -- log -----------------------------------------------------------------

    @staticmethod
    def _log_change(
        event: str,
        action: str,
        principal: Principal,
        system_id: int,
        group: AgentFieldGroup,
        definition: AgentFieldDefinition,
        *,
        on_behalf: bool,
    ) -> None:
        """`NFR20.28`：一行 INFO。`agent_group`／`field_key` 取自定義（封閉集合），不是輸入。"""
        logger.info(
            "%s system_id=%s agent_group=%s field_key=%s user_id=%s on_behalf=%s",
            event, system_id, group.group_key, definition.field_key,
            principal.user_id, on_behalf,
            extra={
                "system_id": system_id,
                "agent_group": group.group_key,
                "field_key": definition.field_key,
                "user_id": principal.user_id,
                "action": action,
                "on_behalf": on_behalf,
            },
        )


__all__ = [
    "MAX_SYSTEM_ID",
    "RequirementFieldFacade",
    "build_field_view",
    "coerce_system_id",
    "compose_field_set",
    "derive_filled_state",
    "parse_write_body",
]
