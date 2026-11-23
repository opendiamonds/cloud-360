## Review
**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/units-generation/unit-of-work.md > U1「負責與交付」第 4 項與 U2「負責與交付」最後一項 | `list_diagrams_of_system` 改成必填參數（無預設值）歸 U1，U1 的說明並寫「現行呼叫端改為明示」；但現行呼叫端是 WorkOrchestrator（`work_orchestrator.py:967`），元件歸 U2，U2 又另寫「系統換成目標圖改為明示包含草稿」。同一處呼叫端改動寫在兩個單元，且 FR6.4c 只對應 U1。若 U1 先單獨完成並合併，U2 擁有的呼叫端會因缺必填參數而壞掉；若各改各的則責任不清。 | 在 unit-of-work.md 明寫呼叫端改動歸哪一個單元：建議 U1 負責參數與所有現行呼叫端（含 WorkOrchestrator 該行），U2 只負責新增呼叫端。同步更新 story map 的 FR6.4c「另涉單元」與依賴檔整合點表。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/units-generation/unit-of-work-story-map.md > FR7.1 列與「跨單元的項目」表；unit-of-work-dependency.md > 整合點表 | FR7.1「經大腦建立」的變更紀錄，components.md 明寫由 BrainDiagramCreation（U2）在建草稿後呼叫 HierarchyService 寫入，但 FR7.1 只對應 U1、無「另涉單元」，U2 的交付清單與整合點表也沒有 U2 呼叫 U1 紀錄函式這一項，跨單元介面漏列。 | 在 FR7.1 列補「另涉單元 U2」，跨單元表與整合點表補一列（U2 呼叫 U1 的變更紀錄寫入，同行程函式呼叫），U2 交付清單補上「建草稿後記錄經大腦建立」。 | Resolved (reviewer) |
| R-03 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/units-generation/unit-of-work.md > U1 與 U2 的 `Assumptions & Open Questions` 第 1 項 | 「三者應同一批合入 `ut`」只寫在假設裡，沒有點出具體風險：新反問種類（WebSocket 契約）與 U3 呈現不同批上線時，舊前端遇到未知反問種類的行為未被分析；U1 的回應新增欄位對舊前端無害，但 U2 的新種類不是。三者同批也意味著一次部署含 L 級單元，沒說明失敗時如何回滾。 | 在 Assumptions 補一句：U2 的新反問種類與 U3 的呈現必須同批；並請 contract-design 定案舊前端遇到未知反問種類的降級行為。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/units-generation/unit-of-work-dependency.md > 可平行開發的組合 | 「U1 沒有依賴，可最先或與其他工作並行開始」帶有開工順序的暗示，與本站不建議順序的規則有輕微衝突；另 U3 依賴 U2 其實只為了 WebSocket 契約形狀（文中自己說可依契約先行），依賴性質寫成「U2」而非「U2 的契約」，可能被下游當成必須等 U2 實作完成。 | 把「可最先」改為中性說法（U1 無前置依賴）；U3 對 U2 的依賴註明是契約形狀而非實作完成。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/units-generation/unit-of-work.md > 單元表與涵蓋元件 | components.md 的 AccessControl 沒有歸屬任何單元（U2 只寫「對 AccessControl 的新呼叫」）。該元件確實不改規則，但「每個元件歸一個單元」在文件上不成立。 | 在 U2 或單元表加一句註明 AccessControl 不改動、不屬任何單元，避免下游誤以為漏分。 | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/261116-brain-create-diagram/inception/units-generation/unit-of-work.md > U1 負責與交付（`list_diagrams_of_system` 條目）與 Assumptions 第二條 | U1 條目寫「U1 單獨合入也不會讓既有呼叫失效」，只對列圖參數成立。U1 同時改了存檔語意（手動存檔轉正式、只寫內容）與清單回傳，其預設行為若是「存檔即轉正式」，則在 U3 未上線前，自動存檔可能把草稿轉成正式；單元文件沒有寫明預設值。Assumptions 已要求三單元同批合入，所以風險可控，但這句保證寫得過寬。 | 把保證限縮為「列圖參數與其呼叫端」，並在契約定案時明寫存檔 API 的預設語意（預設只寫內容、轉正式需明示）。 | New |

> R-01 Reviewer note: 已實查程式：`list_diagrams_of_system` 只有 `hierarchy_service.py:288`、`hierarchy_facade.py:604` 兩個定義，唯一呼叫端是 `work_orchestrator.py:967`（經 facade）。`unit-of-work.md` U1 交付項已把參數與該呼叫端一併歸 U1，整合表與 story map 的 FR6.4c 也同步改為「參數與現行呼叫端都在 U1」，擁有者不再分裂。

> R-02 Reviewer note: `unit-of-work-story-map.md` 的 FR7.1 列補上另涉 U2，「跨單元的項目」表有 FR7.1 說明；`unit-of-work-dependency.md` 整合表新增「經大腦建立的變更紀錄」U1→U2 一列；U2 交付項也寫明寫入端在 U2。

> R-03 Reviewer note: `unit-of-work.md` Assumptions 已加入舊前端遇到未知反問種類的行為分析，並指派 contract-design 定案退路（以文字列出候選）。分析屬推導且已標示，足以帶進閘門。

> R-04 Reviewer note: 依賴檔寫明 U3 依賴 U2 的是 WebSocket 契約形狀而非實作；全檔無跨單元順序字句，story map 的「實作順序」僅限單元內部。

> R-05 Reviewer note: `unit-of-work.md` U2 涵蓋元件已列 AccessControl，並說明本 intent 不改其規則、只新增閘道的 `user_can_arch` 呼叫，歸屬理由成立。

### Summary
五項前次發現皆已修正，並已對照 `work_orchestrator.py:967`、`hierarchy_service.py:288`、`hierarchy_facade.py:604` 以及 story map 的 FR 計數驗證（U1 11、U2 29、U3 1，合計 41）。依賴圖無循環，可進入 contract-design。僅餘一項 Minor，是 U1 單獨合入保證的措辭過寬，不阻擋。
