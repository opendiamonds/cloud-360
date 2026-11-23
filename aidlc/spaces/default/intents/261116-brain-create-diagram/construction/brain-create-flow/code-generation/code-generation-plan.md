# Code Generation Plan — U2 brain-create-flow

## Summary

- Builds: 大腦建圖元件（判定、取名、建草稿、變更紀錄）、路由多問一題、閘道新建流程與四種可點選反問、CapabilityClient 建圖與轉正式、409 傳到工作項
- Touches: 新增 backend/services/brain_diagram_creation.py；services/{brain_gateway,brain_gateway_rules,brain_ws_contract,intent_routing*,work_orchestrator_capabilities,work_orchestrator_rules}.py、ws-contract.json
- Tests: 36 個後端測試（純函式 18，含 6 個 @given；流程 18）＋ 同步既有測試

> 本檔是已核可的 stage 層級計畫 `../../code-generation/code-generation-plan.md` 中屬於本單元的步驟，**逐字摘出、未改寫**（含完成勾選）；Testing Contract、準備步驟（Step 1～2）與收尾步驟（Step 18～19）見該檔。三個單元同一批合入 `ut`。

## Steps

### U2 brain-create-flow

- [x] **Step 10 — 純函式（實作）**：`brain_diagram_creation.py` 新增 `decide(p, t, target_kind, has_diagrams, has_drafts)`（FR2.2 判定表＋FR6.3a 優先序）與 `make_title(text, system_name, existing_titles)`（指令詞清單、30 個可見字元、去控制字元、空主題退回「<系統名> 架構圖」、重名加「（n）」）；不讀 DB、不連外、不拋 `HTTPException`。〔FR2.1～FR2.4、FR5.1～FR5.4、FR6.3a〕
- [x] **Step 11 — 純函式（測試，PBT）**：hypothesis 鎖住 FR2.3 四項性質（互斥、不明一定反問、對 p 單調、決定性）與取名性質（長度上限、不含控制字元、不切斷組合字元、與既有名稱不重複）；另以例子測試判定表每一格與 FR6.3a 的優先序。〔FR2.3、FR5、ADR-0006 PBT〕
- [x] **Step 12 — 路由與 I/O（實作）**：`intent_routing_decisions.build_questions` 加 `wants_new_diagram` 題，併入同一次請求、結果留在行程內；路由觀測事件加判定類別（不含原文與圖名）；`CapabilityClient.create_diagram`（固定 `as_draft=true`）與 `put_diagram(finalize=...)`；`CapabilityError.draft_rejected`、`PHRASES["draft_rejected"]` 與 `failure_for_status` 的 409 分支；工作編排產圖存回時傳 `finalize=True`；BrainDiagramCreation 的 I/O 函式（建草稿、寫變更紀錄，失敗只記 log）。〔FR2.2、FR1.1、FR6.2、FR6.4a、FR7.1、NFR2、NFR4、C4、C7〕
- [x] **Step 13 — 路由與 I/O（測試）**：路由請求只發一次且帶新題；`draft_rejected` 只在 409 且 detail 等於常數時為 true，回應內容不被保存；`PHRASES["draft_rejected"] == DRAFT_REJECTED_DETAIL`；建圖逾時不重試且不交辦；產圖成功後圖轉正式、失敗則維持草稿。〔FR6.2、FR6.3、C4、C5 錯誤表〕
- [x] **Step 14 — 閘道（實作）**：`brain_ws_contract.py` 的 `ClarifyPayload.kind` 加四個值、`ClarifyCandidate` 加選填 `systemId`／`diagramId`／`action`；重跑 `dump_ws_contract`；閘道新建流程：`user_can_arch(edit)` 預檢 → 判定 → 建草稿 → `TargetRef.diagram_id` 經 `_set_target_confirmed` 切換 → 交辦；`_reread_target` 比對加入 `diagram_id`；四種反問的候選（上限 10＋新建、排序依 C6）存入 `PendingClarify`，點選時先比對候選集合（`brain_gateway.py:1672`）再經 HierarchyService 重新驗證；名下沒有系統時回覆專案頁路徑。〔FR1.1～FR1.5、FR3.1～FR3.6、FR4.1、FR4.3、FR6.3a、C6、C7〕
- [x] **Step 15 — 閘道（測試）**：只有系統沒有圖 → 建一張草稿、作業對象切到它、工作項完成後轉正式（FR1.5）；同一工作項重試、復原掃描、再說一次接著畫皆不建第二張（NFR3 三案）；無架構編輯權 → 不建、回說明（NFR5 deny）；四種反問各一案（含點選失效的候選被拒並重列）；`_reread_target` 對圖目標的比對；候選超過 10 筆只列 10 筆並附說明。〔FR1.4、FR1.5、FR3、FR4.1、NFR3、NFR5〕
