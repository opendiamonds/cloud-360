"""
memory_facade.py — `U8 memory-service` 的授權門面

**契約（前端與同進程呼叫端依賴，請勿變更）**

本模組是契約 `K-08` 的 `sole_entry`：記憶的**全部授權判定只在這一層，
且各只有一份**。消費端有兩種，而這個事實決定了本層的禁令：

| 消費端 | 形式 |
|---|---|
| `U15 memory-page-ui` | HTTP（經 `memory_router`） |
| `U11 intent-router` | **同進程**（經 `K-10`，`classify` 時讀記憶） |

兩條禁令（`logical-components.md §1.1`）：

- **不得拋 `HTTPException`**。`U11` 不在 FastAPI 的 dependency 鏈上，拋 HTTP
  例外會讓它收到一個它無法處理、也無處可回的型別。
- **不得碰 DB**（經 `memory_service`）。本層是授權層，SQL 在下一層。

## 本 repo 的**第二套授權模型**，而它其實是兩套並存

| | 判定依據 | 承載的規則 | 拒絕時 |
|---|---|---|---|
| **擁有者模型** | 列的 `ownerUserId` 與呼叫者是否相同 | `BR2.2`（讀的過濾）、`BR4.1`（刪） | `reason="owner"` |
| **角色模型** | 呼叫者是否為 `Platform_Admin`／`Platform_Owner` | `BR5.1`（放寬）、`BR6.1`（稽核查詢） | `reason="scope"` |

**兩者不可互換。最容易出的錯是用角色模型判讀寫**：`Platform_Admin`
**不因其角色而能讀或刪**他人的記憶（`BR4.1` 的 note）。它被授予的只有兩件事
——放寬可見範圍與查稽核。`test_memory_authz` 的第 7 條就是這件事的證據
（`Platform_Admin` 有放寬權但**沒有**刪除權）。

**角色判定只實作一份**（`_authorize_role`），由 `BR5.1` 與 `BR6.1` 共用：
`[FD2]`=A 刻意把稽核讀取的角色集合與 `widen_scope` 對齊，故第二份沒有存在理由。

## 兩條路徑用**不同手法**關閉同一個 oracle，這不是不一致

| 路徑 | 手法 | 為什麼是這個 |
|---|---|---|
| 放寬、稽核查詢 | **先判角色、後取記憶**（`NFR7.22`） | 無權者在任何 id 上都得到同一個 403，oracle 本來就不存在 |
| 刪除 | **收斂回應**（`[D1]`=A） | 要知道擁有者**必須先取列**，所以上面那招用不了 |

`security-design.md §三` 逐字要求把這件事寫下來以免被讀成不一致。

## `Principal` 沿用 `hierarchy_facade` 的那一個

`K-08` 的 `identity_passing` 逐字「principal 為第一個參數，**同 `K-07`**」。
而 `team.md` 的「單一真實來源」要求新增第二份物化前先確認是否有既有型別可用
——有，且 `membership_facade` 已經沿用過同一個。附帶好處是 `_MINT` 令牌讓
「拿不到 principal 就呼叫不了 facade」成為型別層事實。

## 第三道判定：帳號是否已核准（`U15` 的 code-generation 補上）

自行註冊的帳號在 `authorization_status == "pending"` 時**已取得 token**，而
`memory_router` 的 dependency 只有 `get_current_user`。本層原本不看
`authorization_status`，於是 pending 帳號可讀到他人設為 `platform` 的記憶
（`U15` nfr-requirements 審查 `R-01`）。

**落點在本層，不在 router**：`memory_router` 檔頭宣告「本層不做任何授權判定」
且 `test_memory_contract` 的 `C3` 機械斷言它；而 `services/intent_routing.py`
**同進程**直呼本層，router 的 dependency 對它無效。故 `_authorize_approved`
是六個公開方法的**第一行**，先於任何取列——pending 帳號對任何 id（含不存在的）
都得到同一個 403，不形成存在性 oracle（與角色模型同一手法）。

判定本體沿用 `services.rbac.user_is_approved`（經 `mint_principal` 寫進
`Principal.is_approved`），本層不另寫一份。

## 殘留缺口，如實記載

「facade 是唯一入口」**無機械強制**（承接 `K-07` 的 `OQ-N2`）：任何人直接
`SELECT memory.memory_records` 就繞過了全部授權，而繞過是靜默的。
`U19` 的 `membership_facade` 檔頭記載過同形缺口。
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from services.embedding_port import (
    EmbeddingPort,
    EmbeddingProviderUnavailable,
    resolve_embedding_port,
)
from services.hierarchy_facade import Principal, mint_principal
from services.memory_errors import (
    MemoryError,
    MemoryForbidden,
    MemoryInvalidInput,
    MemoryNotFound,
)
from services.memory_ranking import rank_candidates
import services.memory_service as memory_service
from services.memory_types import (
    MEMORY_KINDS,
    SCOPE_WIDENING_ROLES,
    SCOPE_WIDTH,
    VISIBILITY_SCOPES,
    MemoryAuditEventView,
    MemoryView,
)

logger = logging.getLogger("cloud360.memory_facade")

REASON_OWNER = "owner"
REASON_SCOPE = "scope"
#: 帳號未核准（pending／rejected）。見 `_authorize_approved`。
REASON_PENDING = "pending"


def _as_view(record) -> MemoryView:
    """把一列轉成對外檢視。**不含 `embedding`**（見 `MemoryView` 的 docstring）。"""
    return MemoryView(
        memory_id=str(record.id),
        kind=record.kind,
        owner_user_id=record.owner_user_id,
        visibility_scope=record.visibility_scope,
        content=record.content,
        embedding_model=record.embedding_model,
        created_at=record.created_at,
        expires_at=record.expires_at,
    )


def _as_audit_view(event, memory_exists: bool) -> MemoryAuditEventView:
    return MemoryAuditEventView(
        audit_event_id=str(event.id),
        memory_id=str(event.memory_id),
        actor_user_id=event.actor_user_id,
        action=event.action,
        previous_scope=event.previous_scope,
        new_scope=event.new_scope,
        occurred_at=event.occurred_at,
        memory_exists=memory_exists,
    )


class MemoryFacade:
    """記憶的唯一授權入口（契約 `K-08` 的 `sole_entry`）。"""

    def __init__(self, db: Session, port: Optional[EmbeddingPort] = None) -> None:
        """`port` 可注入，但**不是**為了 mock `U6` 的內部。

        `unit-test-instructions.md §六` 逐字：「以 `stub` 提供者設定；
        **不 mock `U6` 的內部**——它有自己的契約（`K-06`）」。注入點存在是為了
        讓測試能傳一個**真正的** `StubAdapter`，而不是一個假的 `embed`。

        未注入時以 `resolve_embedding_port()` 解析，且**每次呼叫才解析**
        （見 `_require_port`）——在 `__init__` 解析會把設定值凍結在 facade 的
        生命週期上，而 `NFR4.20` 要求本單元不持有跨請求狀態。
        """
        self._db = db
        self._port = port

    # -- 授權判定（各只有一份）---------------------------------------------

    def _authorize_role(
        self, principal: Principal, memory_id: Optional[str] = None
    ) -> None:
        """角色模型：`BR5.1`／`BR6.1` **共用的唯一一份**實作。

        **判定先於任何取列**（`NFR7.22`／`functional-spec.md §1.5` 步 2）：
        先查角色再查記憶，使「記憶是否存在」不會洩漏給無權者——否則 404 與 403
        的差異又構成一個存在性 oracle。這是 `test_memory_authz` 第 10 條
        （非管理員放寬**不存在**的 id → **403** 而非 404）的全部依據。

        刻意不走 `require_story_action` 這個 FastAPI dependency：它拋
        `HTTPException`，而本層的拒絕必須是 `MemoryForbidden`，且同進程呼叫端
        根本沒有 dependency 鏈。

        `K-08` 的路由守衛逐字「`/memory` 走 `ProtectedRoute` 但**不包**
        `CapabilityRoute`……把關的是擁有者欄位而非角色，故**不需新 story id**」
        ——故本判定讀的是 `principal.role`，**不是** `role_permissions` 矩陣。
        """
        if principal.role not in SCOPE_WIDENING_ROLES:
            memory_service.log_denied(
                reason=REASON_SCOPE,
                memory_id=memory_id,
                principal_user_id=principal.user_id,
            )
            raise MemoryForbidden(reason=REASON_SCOPE, memory_id=memory_id)

    def _authorize_approved(
        self, principal: Principal, memory_id: Optional[str] = None
    ) -> None:
        """帳號必須已核准：六個公開方法的**第一行**都呼叫本方法。

        **判定先於任何取列**：與 `_authorize_role` 同形，使 pending 帳號在任何
        id（含不存在的）上都得到同一個 403，`DELETE` 不會因此重開 `[D1]`=A
        關掉的枚舉 oracle——這個 403 來自**身分**，不來自**列**。

        判定依據是 `principal.is_approved`，由 `mint_principal` 以
        `services.rbac.user_is_approved` 填入（單一真實來源）。
        """
        if not principal.is_approved:
            memory_service.log_denied(
                reason=REASON_PENDING,
                memory_id=memory_id,
                principal_user_id=principal.user_id,
            )
            raise MemoryForbidden(reason=REASON_PENDING, memory_id=memory_id)

    def _require_port(self) -> EmbeddingPort:
        """取得 embedding Port，或**大聲失敗**（`BR3.5`／`NFR4.22`）。

        `resolve_embedding_port()` 回 `None` 代表 `EMBEDDING_PROVIDER=fulltext`
        ——`K-06` 的語意是「**不建立** Port」而非「一個會算向量的實作」，
        故呼叫端以「有沒有拿到 Port」分流（`U6` 的 `BR1.4`／`D-10`）。

        ## 這裡是一個**上游契約缺口**，不是本層的設計選擇（`CG8-1`）

        `fulltext` 之下 `model_id` 為 `None`（`embedding_port.py:379` 逐字
        `model_id=None`），而 `memory_records.embedding_model` 是 **NOT NULL**
        且 `entities.md` 逐字「即使 `embedding` 為 NULL 本欄仍必填」。
        **兩者直接對撞**：沒有任何已核可來源說過 fulltext 之下該欄要填什麼。

        而 `backend/.env.example:120` 的預設**正是** `fulltext`，故這條路徑是
        本機開發的預設路徑，不是邊角。

        處置是**大聲失敗並說明兩個可行方向**，而不是自行發明一個哨兵值：
        `MEMORY_RECORD_EMBEDDING_MODELS` 是 `U6` 已交付的封閉集合
        （`("bge-m3", "multilingual-e5-large", "stub-v1")`），往裡面塞
        `"fulltext"` 會替一個跨單元契約做決定，且會在資料層產生第四個
        向量空間身分——而 `schema_rbac.sql` 的 COMMENT 逐字要求換模型身分
        必須同時規劃既有列的遷移方式（`ADR-008`）。
        """
        port = self._port or resolve_embedding_port()
        if port is None:
            raise EmbeddingProviderUnavailable(
                "fulltext",
                detail=(
                    "EMBEDDING_PROVIDER=fulltext 之下沒有向量 Port，而"
                    " memory_records.embedding_model 是 NOT NULL（entities.md"
                    "：即使 embedding 為 NULL 本欄仍必填）。上游未定 fulltext"
                    " 之下該欄要填什麼（CG8-1）。兩個方向：① 改設"
                    " EMBEDDING_PROVIDER=stub｜ollama｜fastembed；② 由後續"
                    " intent 擴充 U6 的 MEMORY_RECORD_EMBEDDING_MODELS 並規劃"
                    "既有列的遷移（ADR-008）。本單元不自行發明哨兵值。"
                ),
            )
        return port

    # -- 1：寫入（`functional-spec.md §1.1`）--------------------------------

    def write(
        self, principal: Principal, kind: str, content: str, **ignored: object
    ) -> MemoryView:
        """寫入一則記憶。擁有者由 `principal` 決定（`BR1.1`）。

        ## `**ignored` 是 `BR1.2` 的實作，不是偷懶

        `NFR7.20`／`NFR7.21` 要求酬載中任何意圖指定 `ownerUserId` 或
        `visibilityScope` 的欄位**被忽略且不回報錯誤**。

        **刻意靜默忽略而非回 422**（`BR1.2` 的 `violation_behaviour` 逐字）：
        回錯誤會讓呼叫端以為「換個欄位名就能指定」，而忽略使該能力不存在。
        用 `**ignored` 承接是為了讓「這些欄位被接受但無效」成為簽章上的事實
        ——若改成不接受，同進程呼叫端傳它會是 `TypeError`，那就是回報錯誤了。

        `test_memory_authz` 第 11 條驗的正是這一條：帶 `ownerUserId` 與
        `visibilityScope` 的請求**回成功（非 422）**，而兩欄為已驗證身分與 `owner`。

        ## 步 5–6 在步 7 之前（`functional-spec.md §1.1`）

        先取向量、後建立列。若先建列再取向量，提供者不可用時會留下一列**沒有
        向量且無人知道該不該重試**的記憶——而它與 fulltext 模式寫入的列在資料上
        不可區分。先取向量使失敗**不留痕跡**。

        **不產生稽核事件**（`BR7.4`）：`action` 的封閉集合沒有任何可用於建立的值。
        """
        self._authorize_approved(principal)
        if kind not in MEMORY_KINDS:
            raise MemoryInvalidInput("kind", kind, MEMORY_KINDS)
        if content is None or not str(content).strip():
            raise MemoryInvalidInput("content", content)

        # 步 5–6：先取向量。提供者不可用則在此停止，不降級（`BR3.5`）。
        port = self._require_port()
        embedding_model = port.model_id()
        vectors = port.embed([content])
        embedding = vectors[0] if vectors else None

        # 步 7–9：建立列。`ownerUserId` 與 `visibilityScope` 都不來自酬載。
        record = memory_service.create_record(
            self._db,
            owner_user_id=principal.user_id,
            kind=kind,
            content=content,
            embedding_model=embedding_model,
            embedding=embedding,
        )
        return _as_view(record)

    # -- 2：檢索（`functional-spec.md §1.2`）--------------------------------

    def search(
        self,
        principal: Principal,
        query: str,
        kinds: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryView]:
        """相似度檢索。只回該 principal 可見、且同一向量空間的列。

        **過濾在 facade 的責任內、在 SQL 的 `WHERE` 內**：`K-08` 的
        `authorization_responsibility` 逐字「可見範圍的過濾在 facade 內完成，
        呼叫端不得自行過濾」——而把條件下推到 SQL 是更強的形式，不是違反
        （`security-design.md §1.1`）。這一條是 `U15` 前端不自行過濾的依據。

        排序：SQL 已依距離遞增回傳，`rank_candidates` 再施加同分時的決定性
        次級鍵（`NFR3.24`）。**那一步刻意在純函式層**，因為純函式才寫得出
        property-based 測試。
        """
        self._authorize_approved(principal)
        port = self._require_port()
        embedding_model = port.model_id()
        vectors = port.embed([query])
        if not vectors:
            return []

        pairs = memory_service.search_records(
            self._db,
            principal_user_id=principal.user_id,
            query_vector=vectors[0],
            embedding_model=embedding_model,
            kinds=kinds,
            limit=limit,
        )
        if not pairs:
            return []

        by_id = {str(record.id): record for record, _ in pairs}
        ordered = rank_candidates(memory_service.scored_candidates(pairs))
        return [_as_view(by_id[candidate.identifier]) for candidate in ordered]

    # -- 3：列出（`functional-spec.md §1.3`）--------------------------------

    def list_records(
        self,
        principal: Principal,
        kinds: Optional[Sequence[str]] = None,
        offset: int = 0,
        page_size: Optional[int] = None,
    ) -> List[MemoryView]:
        """列出呼叫者可見的記憶（記憶頁的三區）。

        `BR2.2` 的過濾是**過濾而非拒絕**：「看不到別人的記憶」不是一個錯誤狀態，
        故本方法**不因可見範圍**拋授權例外，只回較小的集合。唯一的例外是
        帳號未核准（`_authorize_approved`）——那是身分判定，不是可見範圍判定。
        """
        self._authorize_approved(principal)
        records = memory_service.list_records(
            self._db,
            principal_user_id=principal.user_id,
            kinds=kinds,
            offset=offset,
            page_size=page_size,
        )
        return [_as_view(record) for record in records]

    # -- 4：刪除（`functional-spec.md §1.4` ＋ `[D1]`=A）--------------------

    def delete(self, principal: Principal, memory_id: str) -> None:
        """刪除自己的記憶。**非擁有者與不存在皆回 `MemoryNotFound`**（`[D1]`=A）。

        ## 三個情境、兩種對外回應、三種日誌

        | 情境 | 拋出 | 日誌 |
        |---|---|---|
        | 擁有者 | —（成功） | — |
        | **非擁有者** | `MemoryNotFound` | **含** `reason="owner"` |
        | **不存在** | `MemoryNotFound` | **不含** |

        第二與第三列的**對外回應刻意相同**（router 轉 404），差異只在日誌。
        這是 `[D1]`=A 關閉枚舉 oracle 的方式：`schema_rbac.sql` 的
        `id SERIAL PRIMARY KEY` 是連續整數，而 403／404 的差異讓任何已認證
        使用者得以走訪 `1..N` 取得**整張表哪些 id 存在**。

        **內部保留區分是這個設計的關鍵**（`security-design.md §二之二`）：
        若連日誌也收斂，營運端就無法分辨「使用者誤刪已刪除的記憶」與
        「有人在枚舉」——而後者是需要被看到的。`[D1]`=A 之後，**日誌是區分
        兩者的唯一手段**，故 `test_memory_authz` 的第 5、6 條必須同時斷言
        「狀態碼相同」與「日誌可區分」，**缺一不可**。

        **不產生稽核事件的兩個情境**：不存在（`BR4.3`——若產生，一個重試迴圈
        會為同一次刪除製造多筆稽核，使 `AC4.3.2` 的查詢結果失真）與非擁有者。

        **帳號未核准時回 403，且先於取列**（`_authorize_approved`）。這不違反
        `[D1]`=A：該 403 只取決於呼叫者身分，對任何 id 都相同，故不回答任何
        關於 id 空間的問題。
        """
        self._authorize_approved(principal, memory_id)
        parsed = memory_service.parse_memory_id(memory_id)
        record = (
            memory_service.get_record(self._db, parsed) if parsed is not None else None
        )
        if record is None:
            # 不存在：**不**寫 `reason="owner"` 日誌。這個「不寫」是第 6 條
            # 測試的斷言對象，不是省略。
            raise MemoryNotFound(memory_id)
        if record.owner_user_id != principal.user_id:
            memory_service.log_denied(
                reason=REASON_OWNER,
                memory_id=memory_id,
                principal_user_id=principal.user_id,
            )
            # **收斂**：對外與上面那一行完全相同（`[D1]`=A）。
            # 不得改回 `MemoryForbidden`——那會重開整張表的枚舉 oracle。
            raise MemoryNotFound(memory_id)

        memory_service.delete_with_audit(
            self._db, record=record, actor_user_id=principal.user_id
        )

    # -- 5：放寬可見範圍（`functional-spec.md §1.5`）------------------------

    def widen_scope(
        self, principal: Principal, memory_id: str, new_scope: str
    ) -> MemoryView:
        """放寬可見範圍。**僅 `Platform_Admin`／`Platform_Owner`**（`BR5.1`）。

        **擁有者本人不能放寬自己記憶的可見範圍**——那是刻意的：`FR4.3b` 把放寬
        定為「獨立的、需授權的操作」。

        步序與刪除**相反**（`NFR7.22`）：先判角色、後取記憶。故無權者在任何 id
        （含不存在的）上都得到 **403**，oracle 本來就不存在，不需要收斂。
        """
        self._authorize_approved(principal, memory_id)
        self._authorize_role(principal, memory_id)

        if new_scope not in VISIBILITY_SCOPES:
            raise MemoryInvalidInput("visibility_scope", new_scope, VISIBILITY_SCOPES)

        parsed = memory_service.parse_memory_id(memory_id)
        record = (
            memory_service.get_record(self._db, parsed) if parsed is not None else None
        )
        if record is None:
            raise MemoryNotFound(memory_id)

        current = record.visibility_scope
        # `BR5.2`：放寬只有一個合法方向。兩值集合使「哪個更寬」可判定
        # （`owner` < `platform`）。**收窄不在本操作的語意內**——`FR4.3b` 說的
        # 是「放寬」，收窄是否允許、由誰允許，上游未定（`FD8-4`）。
        if SCOPE_WIDTH.get(new_scope, -1) <= SCOPE_WIDTH.get(current, -1):
            raise MemoryInvalidInput(
                "visibility_scope",
                new_scope,
                tuple(
                    scope
                    for scope in VISIBILITY_SCOPES
                    if SCOPE_WIDTH[scope] > SCOPE_WIDTH.get(current, -1)
                ),
            )

        record = memory_service.widen_scope_with_audit(
            self._db,
            record=record,
            actor_user_id=principal.user_id,
            new_scope=new_scope,
        )
        return _as_view(record)

    # -- 6：稽核查詢（`functional-spec.md §1.6`）----------------------------

    def list_audit_events(
        self,
        principal: Principal,
        memory_id: Optional[str] = None,
        offset: int = 0,
        page_size: Optional[int] = None,
    ) -> List[MemoryAuditEventView]:
        """列出稽核事件。**僅 `Platform_Admin`／`Platform_Owner`**（`BR6.1`）。

        與 `BR5.1` **共用同一份角色判定**（`[FD2]`=A 刻意對齊）。
        擁有者**看不到**自己記憶的稽核事件——`[FD2]` 的選項 B 被否決的理由是
        它會讓同一個端點有兩種過濾語意，而 `AC4.3.3` 的「被拒絕」在擁有者身上
        會變成「回空集合」，兩者是不同的可觀察結果。

        **先判角色、後取事件**，與放寬同形（`NFR7.22`）。

        `memory_id` 指不到記憶的事件**仍然回傳**，並以 `memory_exists=False`
        讓呼叫端可分辨（`BR6.3`）。過濾掉它會讓 `FR4.7` 在 90 天後變成空話。
        """
        self._authorize_approved(principal, memory_id)
        self._authorize_role(principal, memory_id)
        parsed = (
            memory_service.parse_memory_id(memory_id) if memory_id is not None else None
        )
        if memory_id is not None and parsed is None:
            # 解析不出來的 id 不是錯誤：它只是收斂不到任何事件。
            # 在**已通過角色判定**之後，回空集合不洩漏任何東西。
            return []
        pairs = memory_service.list_audit_events(
            self._db, memory_id=parsed, offset=offset, page_size=page_size
        )
        return [_as_audit_view(event, exists) for event, exists in pairs]


__all__ = [
    "MemoryError",
    "MemoryFacade",
    "MemoryForbidden",
    "MemoryInvalidInput",
    "MemoryNotFound",
    "Principal",
    "REASON_OWNER",
    "REASON_PENDING",
    "REASON_SCOPE",
    "mint_principal",
]
