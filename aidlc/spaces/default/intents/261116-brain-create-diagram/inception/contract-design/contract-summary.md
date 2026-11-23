# Contract Summary — 讓大腦直接建立新的架構圖（修訂 2）

> 來源：`contract-design-questions.md` Q1～Q4（皆 A）；`inception/units-generation/unit-of-work.md`、`unit-of-work-dependency.md`（修訂 1）；`inception/domain-design/components.md`（修訂 1）、`decisions.md`；`inception/requirements-analysis/requirements.md`（修訂 2）。
> 本 intent 沒有系統外的 API；以下都是單元之間的邊界。三個單元同一批合入 `ut`（`unit-of-work.md` Assumptions）。
>
> **修訂 2（2026-11-17）**：依 `reviews/review-02.md` 五個 Minor 修正——寫死清單與讀取端點的既有欄位並加鍵集合測試、改正變更紀錄的行號、409 原因文字經 `PHRASES` 表、寫明估價綁圖的現況行為、K-07 修訂的指引位置。使用者選擇修完不再送審。
>
> **修訂 1（2026-11-17）**：依 `reviews/review-01.md` 修正——(1) 新欄位改名 `diagram_status`，避開既有回應的 `"status": "success"`；(2) 409 以固定常數辨識並經 `CapabilityError` 傳到大腦工作項；大腦的估價能力不會碰到 409，從大腦路徑移除；(3) 建圖／存檔／清單／讀取補 `response_model`，使 OpenAPI 漂移檢查真的涵蓋回應；(4) 補 C7 的 `_reread_target` 與 `put_diagram(finalize)`；(5) 估價綁圖改為單一入口並先確認擁有權；(6) C5 寫明回傳形狀變更、K-07 的處置與錯誤／重試政策；(7) C6 以 `brain_ws_contract.py` 的 Pydantic 模型為正本，並補每種新反問的 `capability`、排序與選定後行為。

## Contracts

| # | Provider Unit | Consumer | Mechanism | Owner |
|---|---|---|---|---|
| C1 | U1 diagram-drafts | U2（經 `CapabilityClient`）、U3 | HTTP：`POST /api/collab/diagrams` 可建立為草稿 | U1 |
| C2 | U1 diagram-drafts | U2、U3 | HTTP：`PUT /api/collab/diagrams/{id}` 的 `finalize` | U1 |
| C3 | U1 diagram-drafts | U2、U3 | HTTP：架構圖清單與讀取回傳 `diagram_status` | U1 |
| C4 | U1 diagram-drafts | U2（評核工作項）、U3 | HTTP：草稿被拒的 409 | U1 |
| C5 | U1 diagram-drafts | U2 | 同行程函式：`list_diagrams_of_system`、`record_diagram_change` | U1 |
| C6 | U2 brain-create-flow | U3 | WebSocket：新反問種類 | U2 |
| C7 | U2 brain-create-flow（內部） | U2 | 同行程：建圖呼叫、作業對象切到圖、路由多問一題 | U2 |

## 共用的回應型別（C1～C3）

既有四支端點都沒有 `response_model`，`openapi.json` 的 200 回應是 `{}`，前端 `MyDiagram`（`frontend/src/projects/projectsApi.ts:162`）是手寫的——所以 OpenAPI 漂移檢查**目前擋不住回應欄位**。本 intent 為這四支端點補上 `response_model`，讓 `diagram_status` 有機械保護：

```yaml
components:
  schemas:
    DiagramStatus:
      type: string
      enum: [draft, ready]
    DiagramCreated:          # POST /api/collab/diagrams
      required: [id, system_id, status, message, diagram_status]
      properties:
        id: {type: integer}
        system_id: {type: integer, nullable: true}
        status: {type: string, const: success}     # 既有，不變
        message: {type: string}                    # 既有，不變
        diagram_status: {$ref: DiagramStatus}      # 新增
    DiagramSaved:            # PUT /api/collab/diagrams/{id}
      required: [status, message, diagram_status]
      properties:
        status: {type: string, const: success}     # 既有，不變
        message: {type: string}                    # 既有，不變
        diagram_status: {$ref: DiagramStatus}      # 新增
    MyDiagramItem:           # GET /api/collab/diagrams 的每一筆（既有 5 欄，collab_router.py:352-358）
      required: [id, title, updated_at, is_owner, system_id, diagram_status]
      properties:
        id: {type: integer}
        title: {type: string}
        updated_at: {type: string, format: date-time, nullable: true}   # datetime 序列化為 ISO 8601
        is_owner: {type: boolean}
        system_id: {type: integer, nullable: true}   # 非擁有者為 null（既有行為）
        diagram_status: {$ref: DiagramStatus}      # 新增
    DiagramDetail:           # GET /api/collab/diagrams/{id}（既有 8 欄，collab_router.py:509-550）
      required: [id, title, xml_data, updated_at, is_owner, shared_user_ids, can_edit, can_review, diagram_status]
      properties:
        id: {type: integer}
        title: {type: string}
        xml_data: {type: string}
        updated_at: {type: string, format: date-time, nullable: true}
        is_owner: {type: boolean}
        shared_user_ids: {type: array, items: {type: integer}}
        can_edit: {type: boolean}
        can_review: {type: boolean}
        diagram_status: {$ref: DiagramStatus}      # 新增
```

- **欄位清單已寫死在上表**：FastAPI 在宣告 `response_model` 後會**靜默丟掉模型沒列的鍵**，所以上表必須涵蓋每支端點目前回傳的全部鍵；不得改名或刪除。code-generation 若發現實際回應有表外的鍵，先補進本契約再實作。
- 每支端點以 TestClient 斷言回應的**鍵集合**等於上表（`team.md` B 規則），讓漏列在 CI 上紅燈；前端 `MyDiagram` 目前只宣告清單 5 欄中的 4 欄，型別檢查抓不到漏欄，故不能依賴前端。
- 前端 `MyDiagram` 改為由產生的 `src/types/api.d.ts` 推導（U3），不再手寫。
- 須同步的既有測試：`backend/tests/test_diagram_system_attach.py:108` 鎖住建圖回應的鍵集合 `{"id","system_id","status","message"}`，改為加入 `diagram_status`。

## C1 — 建立為草稿

```yaml
openapi: 3.1.0
paths:
  /api/collab/diagrams:
    post:
      x-auth: require_arch_action("edit")   # 既有，不變（FR4.1）
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [xml_data]
              properties:
                xml_data: {type: string, minLength: 1, maxLength: 2097152}   # 既有（collab_router.py:42）
                title: {type: string, minLength: 1, maxLength: 200}          # 既有（:43）
                system_id: {type: integer, nullable: true}                   # 既有
                as_draft: {type: boolean, default: false}                    # 新增：true 建為草稿
      responses:
        "200": {content: {application/json: {schema: {$ref: DiagramCreated}}}}
```

- 既有呼叫端不送 `as_draft`，行為不變（建為正式）。
- 大腦新建時的 `xml_data` 為空白骨架 `<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>`，可通過 `_looks_like_diagram_xml` 與 `_validate_diagram_payload`（`collab_router.py:234-245`）（requirements OQ5）。
- 既有「設定最後開啟的圖」副作用照舊（FR1.3a）。

## C2 — 存檔是否轉為正式

```yaml
openapi: 3.1.0
paths:
  /api/collab/diagrams/{diagram_id}:
    put:
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [xml_data]
              properties:
                xml_data: {type: string, minLength: 1}   # 既有
                title: {type: string, minLength: 1}      # 既有
                finalize: {type: boolean, default: false}   # 新增
      responses:
        "200": {content: {application/json: {schema: {$ref: DiagramSaved}}}}
```

- `finalize: true` 把草稿轉為正式；`false`（預設）只寫內容、不改狀態；對已是正式的圖無作用。
- 送 `true` 的只有兩處：工作區「儲存架構圖」按鈕（U3）、大腦產圖並存回成功（U2，經 C7 的 `put_diagram(finalize=True)`）（FR6.2、Q2=A）。
- **預設語意（回應 units-generation review-02 的 Minor）**：工作區自動存檔（`WorkspacePage.tsx:269-286`）與評核前寫回（`:500`）不送此欄位，草稿不會因此轉正式；**U3 上線前的舊前端**連手動存檔也不會轉正式——這是三單元須同一批合入的理由之一。

## C3 — 清單與讀取回傳狀態

- `GET /api/collab/diagrams` 每筆回傳 `diagram_status`（`MyDiagramItem`）；`GET /api/collab/diagrams/{id}` 回傳 `diagram_status`（`DiagramDetail`）。
- 前端依此標示草稿、專案頁計數排除草稿（FR6.4、FR6.4a）。
- 資料庫欄位 `user_diagrams.status`（`draft`／`ready`，預設 `ready`）；既有資料庫由 `hierarchy_migration._ensure_hierarchy_schema()` 補欄位（ADR-003），`schema_rbac.sql` 與 `DEPLOY.md` 同步。API 層一律以 `diagram_status` 對外，不直接暴露欄位名。

## C4 — 草稿被拒

```yaml
errorResponse:
  status: 409
  body:
    detail: 這張圖還是草稿，請先完成產圖     # 單一常數 DRAFT_REJECTED_DETAIL，定義在 U1，四處共用
  appliesTo:
    - POST /api/architecture/reviews、POST /api/architecture/reviews/commit-collab（評核；review_router.py:104、:176；main.py:109）
    - POST /api/architecture/generate-wa-collab（WA 共編；agent_router.py:167）
    - POST /api/cost/v1/sets 的 Form 欄位 diagram_id（估價綁圖；estimate_intake_router.py:116，唯一入口）
    - POST /api/collab/diagrams/{diagram_id}/share（分享；collab_router.py:626）
  behaviour: 不寫入任何資料
```

- **估價綁圖的判定順序**：現況下 `diagram_id` 原樣存入估價集、**完全不驗證**（`estimate_access.py:3` 逐字「diagram_id is never consulted」；`estimate_intake_router.py:116`、`:130`）。新增檢查只有一條：該圖存在、屬於呼叫者、且為草稿 → 409。圖不存在或不屬於呼叫者時**維持現況：原樣存入、不回錯誤**——本 intent 不改變這個既有行為，也因此不會成為探測他人圖狀態的管道。
- **大腦路徑上會碰到 409 的只有評核**：大腦交辦的能力是產圖（`/api/architecture/generate`，不帶 `diagram_id`，不受影響）、評核（`start_review`，會帶草稿的 `diagram_id`）、估價（`find_latest_estimate_set` 只讀既有估價集，不 POST 綁圖；草稿不可能綁過估價集，故走既有「沒有估價」路徑）。
- **409 如何傳到大腦工作項**（修正：既有 `CapabilityClient._request` 只保留狀態碼，`failure_for_status` 只特判 401／403，`work_orchestrator_capabilities.py:252-261`、`work_orchestrator_rules.py:428-435`）：
  - `CapabilityError` 新增 `draft_rejected: bool`；`_request` 在 409 時讀回應 JSON 的 `detail`，**僅當它等於 `DRAFT_REJECTED_DETAIL` 常數**時設為 true——不保存回應內容本身，維持「不含使用者內容」的既有約束（`:71-83`）。
  - `failure_for_status` 新增分支：`draft_rejected` 為 true → 原因文字取 `PHRASES["draft_rejected"]`、失敗類別 `draft_rejected`；其餘 409 照舊歸入 `capability_failed`。原因文字一律來自 `PHRASES` 表（`work_orchestrator_rules.py:349`），新增的鍵其值與 `DRAFT_REJECTED_DETAIL` 相同，並以一條測試鎖住兩者相等，避免文字分歧。

## C5 — 同行程函式（HierarchyService）

```yaml
sharedFunctions:
  - name: list_diagrams_of_system
    owner: U1
    signature: (db, *, system_id: int, owner_user_id: int, include_drafts: bool) -> list
    facade: (principal, *, system_id: int, include_drafts: bool) -> list
    returns: list of (diagram_id, title, diagram_status, updated_at)
    order: updated_at 降冪，相同時 diagram_id 降冪（新到舊）
    breaking: true   # 由 (diagram_id, title) 依 id 遞增，改為上列形狀與排序
    callers_to_update_in_U1:
      - backend/services/work_orchestrator.py:967（改為 include_drafts=True 並解構四元組）
      - backend/tests/test_work_orchestrator_store.py:416-426
      - backend/tests/work_orchestrator_fakes.py:336
      - backend/tests/test_work_orchestrator_flow.py、test_diagram_system_attach.py 中的相關斷言
  - name: record_diagram_change
    owner: U1
    facade_signature: (principal, *, diagram_id, requirement_summary, requirement_label, actor_user_id)   # 無 source 參數；service 版預設 brain_orchestration
    usage_for_creation:
      requirement_summary: 經大腦建立「<新圖名稱>」
      requirement_label: 大腦建立架構圖
      actor_user_id: principal.user_id
```

- 產圖成功後既有程式會再記一筆（摘要為使用者原句），同一張圖兩筆屬預期（FR7.1）。
- **K-07 的處置**：facade 的 docstring 宣告「`U12 work-orchestrator` 是唯一寫入端（契約 K-07）」。本 intent 新增第二個寫入端 BrainDiagramCreation（U2）；`source` 值仍為 `brain_orchestration`（兩者都是大腦委辦的變更，符合 `schema_rbac.sql:441` 該值的語意），不新增列舉值。K-07 修訂為「寫入端限大腦委辦路徑：工作編排與大腦建圖元件」，U1 同步更新 `hierarchy_facade.record_diagram_change` 的 docstring，並在其中寫明修訂出處（本檔 C5），讓讀原 K-07 的人找得到。

### 錯誤、逾時與重試（C1、C5、C7）

| 邊界 | 失敗情況 | 行為 |
|---|---|---|
| 建圖 `POST`（C1，經 C7） | 4xx（含 403） | 不重試、不交辦；回覆使用者對應原因（403 沿用既有權限文字） |
| 建圖 `POST` | 傳輸錯誤或逾時（結果未知） | **不重試**（可能已建立，重試會多出一張圖）；不交辦；回覆「新圖是否建立成功不確定，請到工作區確認後再試一次」 |
| 變更紀錄寫入（C5） | 任何例外 | 只記 log、不影響後續交辦（與既有 `_record_change` 相同：定義於 `work_orchestrator.py:848`，例外與 log 在 `:864-865`） |
| 切換作業對象（C7） | `HierarchyForbidden`／`NotFound` | 不交辦；草稿保留；回覆「無法切換到新圖」 |
| 存回並轉正式 `PUT`（C2） | 任何失敗 | 沿用既有存回失敗的處置；圖維持草稿（FR6.3） |

## C6 — WebSocket 新反問種類

**正本**是 `backend/services/brain_ws_contract.py` 的 Pydantic 模型（`_CONTRACT_CONFIG` 為 `extra="forbid"`），`dump_ws_contract` 由它產生 JSON Schema 與前端型別；下列 yaml 只是摘要。

```yaml
ClarifyPayload:                       # brain_ws_contract.py:216
  kind: Literal[intent, target, pick_system, pick_diagram, resume_draft_or_new, new_or_modify]   # 後四個為新增
  candidates: list[ClarifyCandidate]   # min_length=1（既有）；新種類 max 11
ClarifyCandidate:                     # :113
  id: str                              # 既有
  label: str                           # 既有
  capability: str                      # 既有，必填
  confidence: Optional[float]          # 既有
  systemId: Optional[str] = None       # 新增，僅供呈現
  diagramId: Optional[str] = None      # 新增，僅供呈現
  action: Optional[Literal[create, modify]] = None   # 新增
SelectClarifyCandidatePayload:        # :422，不變：只送 candidateId（可為 null＝回絕）
```

| 新種類 | 何時送 | 候選 | `capability` | 排序 | 選定後 |
|---|---|---|---|---|---|
| `pick_system` | 作業對象不是系統、使用者要新建 | 使用者可編輯的系統，最多 10 筆 | `CAP_ARCHITECTURE` | 系統名稱、再 id 升冪 | 以該系統為對象，進入新建流程 |
| `pick_diagram` | 要修改但系統下有多張圖 | 該系統的圖（含草稿），最多 10 筆 | `CAP_ARCHITECTURE` | C5 的順序（新到舊） | 作業對象切到該圖，交辦修改 |
| `resume_draft_or_new` | 系統下已有草稿 | 草稿（最多 10 筆）＋「新建一張」 | `CAP_ARCHITECTURE` | 草稿依 C5 的順序，「新建」在最後 | 選草稿＝切到該草稿並交辦；選新建＝建新草稿 |
| `new_or_modify` | 新建或修改的判定落在不確定區間 | 「新建一張」、「修改目前的圖」兩筆，`action` 分別為 create／modify | `CAP_ARCHITECTURE` | 新建在前 | 依 `action` 進入新建或修改 |

- **伺服器端規則**：點選時先確認 `candidateId` 屬於本次提供的候選（沿用 `brain_gateway.py:1672`），再以連線上保存的對照解析出系統或圖，經 HierarchyService 重新驗證存在與擁有權；不使用客戶端送來的 `systemId`／`diagramId`（FR3.5、Q1=A）。
- **退路**：舊前端（`ClarifyCandidates.tsx:14`）只對 `intent` 特別處理，其餘種類都列成可點的按鈕並只送 `candidateId`，故即使 U2 先於 U3 上線，使用者仍能點選。
- 候選超過 10 筆時只列前 10 筆，並在反問文字說明「其餘請用切換對象選取」（FR3.6）。
- 新增欄位皆選填；改動 Pydantic 模型後須重跑 `dump_ws_contract` 並更新前端型別（漂移檢查）。

## C7 — U2 內部接線

```yaml
internal:
  - name: CapabilityClient.create_diagram          # 新增
    signature: (title: str, xml_data: str, system_id: int) -> int
    notes: 以使用者 token 經 C1 建立，固定送 as_draft=true；形狀與既有 put_diagram 相同（work_orchestrator_capabilities.py:227-284）
  - name: CapabilityClient.put_diagram             # 既有，加參數
    signature: (diagram_id: int, *, title: str, xml_data: str, finalize: bool = False) -> None
    notes: 工作編排在產圖成功存回時傳 finalize=True
  - name: TargetRef.diagram_id                     # brain_gateway_rules.py:363，新增選填
    notes:
      - _set_target_confirmed 把它傳給 store.set_work_target(..., diagram_id=...)；set_work_target 已支援並在寫入前經 resolve_work_target 驗證（session_store.py:436-450）
      - _reread_target（brain_gateway.py:1617-1625）的比對加入 diagram_id，否則 Redis 失誤後會把「切到圖」誤判為已確認
  - name: gateway DB session
    notes: 權限預檢（user_can_arch）與候選查詢沿用閘道注入的 session_factory，於 asyncio.to_thread 內開關（與 resolve_work_target 的用法相同，brain_gateway.py:663-672）
  - name: Decisions question wants_new_diagram
    notes:
      - build_questions（intent_routing_decisions.py:129）新增一題 wants_new_diagram，與既有題目同一次請求送出
      - 結果以 new_diagram_probability 留在行程內的判定結果，不進 WebSocket
  - name: naming
    notes:
      - 主題最多 30 個可見字元（Q4=A）
      - 指令詞清單：幫我、請、麻煩、畫、做、建、一張、一個、新的、另一張、架構圖、的
```

## Contract Ownership Rules

- 提供端單元擁有規格：U1 擁有 C1～C5，U2 擁有 C6、C7。
- 對外回應與 WebSocket 訊息只做**新增選填欄位或新增列舉值**；既有欄位不改名、不刪除。新欄位一律命名為 `diagram_status`，不重用既有的 `status`。
- **唯一的破壞性變更**是 C5 `list_diagrams_of_system` 的回傳形狀與排序；它是同行程函式、呼叫端全在 U1 內一併修改（見 C5 清單），不會跨單元分批。
- 漂移檢查：`openapi.json`（`backend/scripts/dump_openapi.py --check`）——補上 `response_model` 之後才真正涵蓋 C1～C3 的回應；WebSocket 契約（`dump_ws_contract --check`）涵蓋 C6。提供端改規格須在同一個 PR 更新產生的檔案與前端型別。
- 三個單元同一批合入 `ut`：C2 的 `finalize` 與 C6 的新反問種類，都需要 U3 才能完整呈現給使用者。

## Open Questions

| Contract | Question | Blocks |
|---|---|---|
| C6 | 四種新反問的提示文字（例如「要接著畫哪一張草稿，或新建一張？」） | U2／U3 code-generation（文字，不影響形狀） |
