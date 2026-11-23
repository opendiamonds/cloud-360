## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > HierarchyService.behaviour、DiagramListsUI.depends_on（HierarchyService）、ADR-005；traceability.json > FR6.4／FR6.4a | 設計把「專案頁的架構圖計數不含草稿」與「專案頁的系統架構圖清單」歸給 HierarchyService，並以 `list_diagrams_of_system(include_drafts)` 作為排除草稿的機制。實際查證：專案頁的清單與計數來自前端 `projectsApi.ts:171` 呼叫 `GET /api/collab/diagrams`（`collab_router.py:344`，沒有回應模型），再由 `OverviewTab.tsx` 在前端依 `system_id` 自行計數；`list_diagrams_of_system` 只有 `work_orchestrator.py:967` 一個呼叫端，`hierarchy_router.py` 沒有任何列圖或計數端點。照本設計實作，ADR-005 的必填參數鎖不到專案頁，草稿會被算進計數；且該端點沒有回應模型，`status` 欄位不會進 OpenAPI，需求 NFR5 的 TestClient「回應欄位集合」斷言無從落地。 | 把專案頁清單與計數的擁有者改為 DiagramStore（`GET /diagrams` 回 `status`）加 DiagramListsUI 的前端計數；移除 DiagramListsUI → HierarchyService 這條「專案頁清單與計數」的依賴描述（保留 FR6.4b 的刪除系統檢查部分）；在 components.md 的 Assumptions 明寫「此端點目前無回應模型，加 `status` 須同時補回應模型」交給 contract-design。同步修正 traceability 的 FR6.4／FR6.4a 對應。 | Resolved (reviewer) |
| R-02 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > BrainDiagramCreation.behaviour 末句、WorkOrchestrator.behaviour、BrainGateway.depends_on | 三個元件對「建圖成功後誰做什麼」互相矛盾，且含未宣告的反向呼叫：BrainDiagramCreation 寫「建圖成功即通知 WorkOrchestrator 記錄圖 id 並把作業對象切到新圖」，但 WorkOrchestrator 寫的是「先請 BrainDiagramCreation 建立草稿，把圖 id 寫進工作項」，目錄中只有 WorkOrchestrator → BrainDiagramCreation 這條邊，BrainDiagramCreation → WorkOrchestrator 沒有宣告；若補上就是環。另外「切換作業對象」實際只存在於 BrainGateway：`brain_gateway.py:1592` `_set_target_confirmed` 呼叫 `store.set_work_target` 並 `fanout` 推送 work_target；`work_orchestrator.py` 沒有任何 `set_work_target`。FR1.3 要求「建圖成功當下作業對象切到新圖」，而工作項在背景執行，WorkOrchestrator 要驅動閘道的扇出，目錄卻沒有 WorkOrchestrator → BrainGateway（或 session store）的邊，也沒有指名誰負責。 | 釐清並寫成單一方向：BrainDiagramCreation 只回傳新圖 id，由 WorkOrchestrator 寫入 `createdDiagramId`；明確指定「切作業對象與扇出」的擁有者與呼叫路徑（例如 WorkOrchestrator 經 session store 的 `set_work_target`，並說明如何觸發閘道的 work_target 扇出），在 depends_on／dependents 補上該邊並確認圖仍無環；刪除 BrainDiagramCreation 描述中的反向通知。 | Resolved (reviewer) |
| R-03 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/decisions.md > ADR-004；components.md > WorkOrchestrator.behaviour | FR1.4／NFR3 要求「同一工作項不得建立第二張圖」，但設計是先經 HTTP 在 PostgreSQL 建圖，再把 `createdDiagramId` 寫進 Redis 工作項，兩步非原子：建圖已提交但回應遺失、或寫 Redis 前行程中斷，重試與復原掃描讀到空欄位就會再建一張。ADR-004 否決選項 B 的理由正是「跨兩個儲存容易不一致」，但所選的 A 同樣跨 PostgreSQL 與 Redis，Consequences 只提到「工作項過期」，沒有處理這個窗口。 | 在 ADR-004 的 Consequences 明寫此窗口，並指定防線：例如建圖前先把「意圖建圖」記進工作項（或以 workItemId 作為可查詢的冪等鍵，重試時先查系統下是否已有對應草稿），或明確接受孤兒草稿並說明由 FR6.3a 反問承接。NFR3 的「重試／復原掃描」測試需涵蓋「建圖成功但未寫入 Redis」。 | Resolved (reviewer) |
| R-04 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > BrainGateway.behaviour（最後一句，FR4.1）、BrainGateway.depends_on | 設計要 BrainGateway 對「有 K1 但沒有架構編輯權」的使用者「不反問、不交辦，直接回覆需要架構編輯權」，但閘道與工作編排都沒有任何判斷架構編輯權的程式（`brain_gateway.py`、`work_orchestrator.py` 內查無 permission／require_arch 相關呼叫），目錄也沒有宣告提供權限判斷的依賴。實際的檢查在 `collab_router.py:556` 的 `require_arch_action("edit")`，只會在建圖時以 403 呈現；若沿用它，使用者會先被反問「掛在哪個系統」才在最後一步被拒，與 FR4.1「不反問」矛盾。 | 在 components.md 指定權限預檢的擁有者與依賴（例如 BrainGateway 依賴既有 RBAC 查詢，或明確改成「建圖 403 即回覆該說明」並刪除「不反問」），並同步調整 FR4.1 在 BrainGateway 的行為描述與 depends_on。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > HierarchyService.behaviour、traceability.json > FR6.4b | 「清除空的預設專案的判斷」被寫成 HierarchyService 的職責，實際在 `user_router.py:438`（另有 `user_router.py:651` 的刪除使用者前擁有圖檢查），不經 HierarchyService，且目錄沒有 user_router 這個元件。兩處目前是未過濾狀態的查詢，天然包含草稿，風險是日後有人為了排除草稿而加預設過濾。 | 在 FR6.4b 的落點註明這兩處屬 `user_router`，並指定測試保護（只有草稿的預設專案不被清除、仍擁有草稿的使用者不能被刪），或把 user_router 列入 Assumptions 作為受影響的既有程式。 | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > BrainDiagramCreation.behaviour、WorkOrchestrator.depends_on（DiagramStore 的互動說明） | 兩處提到「經 CapabilityClient／以使用者 token 呼叫建圖端點」，但 `work_orchestrator_capabilities.py` 的 `CapabilityClient` 只有 `get_diagram`、`put_diagram` 等，沒有 `create_diagram`，且 CapabilityClient 不是目錄中的元件。同時 BrainDiagramCreation 同一元件內既含「純函式」（判定、取名）又含 I/O（建圖、列圖），未說明模組邊界；`team.md` 的三層形狀要求純函式模組不得 import 任何 I/O。 | 在 Assumptions 補記需新增 `create_diagram` 能力方法與其持有者，並說明 BrainDiagramCreation 內純函式模組與 I/O 模組的拆分（供 PBT 的落點）。 | Unresolved |
| R-07 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > HierarchyService.entities（DiagramChangeRecord） | 屬性列為 `[diagramId, systemId, source, summary, createdAt]`，但 `models.py:461` 起的實際欄位是 `diagram_id`、`source`、`actor_user_id`（NOT NULL，`record_diagram_change` 刻意無預設值）、`requirement_summary`、`requirement_label`；沒有 `system_id` 欄位（系統是查詢時 join 取得），卻漏列必填的 `actor_user_id` 與 `requirement_label`。 | 以實際欄位修正屬性清單，並在 BrainDiagramCreation 的記錄呼叫說明中指名 actor 為使用者本人。 | Resolved (reviewer) |
| R-08 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > BrainGateway.entities（PendingClarify）、decisions.md > ADR-002 | 既有 `PendingClarify` 刻意只送不透明候選 id、伺服器端對照（`brain_gateway.py:1468-1487`，點選時以 `candidate_id not in pending.candidate_ids` 檢查）。本設計改為線上帶系統／圖識別碼，卻仍保留伺服器端 `candidateIds`／`candidateTargets` 對照，沒說明點選時依哪一個為準，也沒寫「點選值必須屬於當初提供的候選集合」；只做存在與擁有權重新驗證，客戶端可選到未被提供但自己擁有的系統或圖。另既有物件保存的是 `decision`（含路由結果），設計寫 `originalRequest`，續行時是否保留 p 與判定沒有交代。 | 在 ADR-002 補一句：點選必須同時符合候選集合成員與重新驗證；說明 PendingClarify 保存的是原始請求還是完整 decision。 | Resolved (reviewer) |
| R-09 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/traceability.json > upstream_ids／coverage | 只涵蓋 FR1～FR7，需求的 NFR1～NFR5（尤其 NFR3 冪等、NFR4 可觀測、NFR5 測試底線）沒有對應到任何元件或實體；且 FR6.4b 對應 HierarchyService、FR6.4／FR6.4a 對應與實際擁有者不符（見上）。 | 補上 NFR 的對應列，並隨前述修正更新 FR6.4／FR6.4a／FR6.4b 的 target。 | Resolved (reviewer) |
| R-10 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > component BrainGateway behaviour；decisions.md > ADR-008 Decision | 文件說「以既有的 _set_target_confirmed（brain_gateway.py:1592）把作業對象切到這張草稿」。實際上該方法只收專案與系統層的目標參照（TargetRef 只有 project_id、system_id），呼叫 set_work_target 時第六個參數（圖）固定傳 None，所以無法把圖設成作業對象。能設定圖的是另一條路徑 _on_set_work_target（約 :1706，使用者手動切換）。照現有說法實作會把對象停在系統層，交辦後工作編排看不到新草稿；同系統下若已有其他圖，還會落入 FR3.2 的反問。 | 在 components.md 與 ADR-008 明寫：切換作業對象需要擴充既有的設定方法使其能帶圖識別碼（或新增一個設定圖層級對象的方法），並指出它與 _on_set_work_target 的關係；同時確認新草稿掛在哪個系統（建圖時帶不帶 system_id），並讓 contract-design 的待辦清單涵蓋這個簽章。 | New |
| R-11 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > BrainDiagramCreation depends_on；Part B 元件圖 | 見 R-06。BrainDiagramCreation 的 I/O 模組使用 work_orchestrator_capabilities.CapabilityClient，目錄沒有這條邊；若之後有人把「呼叫建圖端點」放回工作編排模組，元件圖看不出差異。 | 在 depends_on 補一項對既有 CapabilityClient（或其所屬模組）的依賴，或說明把它視為共用的傳輸工具並列為外部依賴。 | New |
| R-12 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/domain-design/components.md > BrainGateway 持有的 DB 連線 | 預檢與候選查詢需要資料庫 session，閘道內是每次呼叫以 session_factory 建立（約 :679），預檢要在建草稿之前、候選查詢在反問之前，各自短暫取得。文件沒有說明這一點。 | 在 contract-design 待辦補一句：預檢與候選查詢沿用閘道的 session_factory，不長期持有連線。 | New |

> R-01 Reviewer note: 專案頁清單與計數已改歸 DiagramStore（GET /api/collab/diagrams，collab_router.py:344）與 DiagramListsUI（OverviewTab.tsx attachedCount，第 35 行）；list_diagrams_of_system 只剩 WorkOrchestrator 一個呼叫端（work_orchestrator.py:967）與新增的呼叫端，和程式相符。

> R-02 Reviewer note: 草稿改由 BrainGateway 在交辦前建立並切換（Q6=A，ADR-008），工作編排不建圖，自相矛盾與未宣告回呼已消除。但「以既有 _set_target_confirmed 切換」的說法與程式不符，見新發現第一列。

> R-03 Reviewer note: 建草稿發生在工作項存在之前，PostgreSQL 與 Redis 之間不再有重複建圖的缺口；建草稿後、切換前當機只會留下一張草稿，由 FR6.3a 反問承接，ADR-008 已寫明且需求有對應規則。

> R-04 Reviewer note: 權限預檢歸 BrainGateway，呼叫 user_can_arch(edit)（rbac.py:171，與 require_arch_action 同一函式），AccessControl 已進目錄並有 BrainGateway 依賴邊；ADR-009 一致。

> R-05 Reviewer note: 預設專案清除與刪除使用者檢查改歸新增的 UserAccounts（user_router.py:438、:651 起，已核對為直接查詢）。

> R-06 Reviewer note: 已改述為「沿用形狀並新增建圖呼叫」，純函式與 I/O 也拆成兩個模組；但 CapabilityClient 位於 work_orchestrator_capabilities.py，BrainDiagramCreation 要用它卻沒有對 WorkOrchestrator 模組的依賴邊，目錄的依賴圖因此少一條邊。

> R-07 Reviewer note: DiagramChangeRecord 屬性已不含 systemId，補上 actorUserId 與 requirementLabel，和 models.py:461-488 相符。

> R-08 Reviewer note: PendingClarify 已寫明點選先核對是本次提供的候選之一再重新驗證，並列出實體屬性。

> R-09 Reviewer note: traceability.json 已含 NFR1-NFR5，FR6.4、FR6.4a、FR6.4b、FR6.4c 的 target 與實際擁有者一致。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 手動解析 components.md 的 yaml 目錄與依賴邊 | 目錄內每個依賴都有對應元件；沒有環（BrainGateway 為唯一入口，其餘皆往下） | 結構上可行 |
| 對照程式（brain_gateway.py、collab_router.py、user_router.py、models.py、rbac.py、work_orchestrator*.py） | 九項前次發現多數與程式相符；一項新增的程式落差（_set_target_confirmed 無法帶圖） | 見新發現第一列 |

### Summary

九項前次發現中八項已修正，R-06 仍是 Minor；R-02 的修法方向（閘道在交辦前建草稿）正確，但引用的 _set_target_confirmed 不能設定圖層級的作業對象，需在文件中改明為擴充該方法或新增方法。只有這一項 Major，其餘為 Minor，故判 READY，建議核可前先補上這一點。
