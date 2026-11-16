## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U8 memory-service 的設計內部大致自洽，22 條規則與 12 條 AC 的對應可追溯，BR7.4 對上游矛盾的裁決正確。問題集中在四處。第一，設計寫的 delete 流程與已落地並較安全的程式相反（設計會重開枚舉 oracle）。第二，設計完全沒有「帳號未核准」的授權面向。第三，設計宣稱的 fulltext 退路在預設設定下無法寫入。第四，新增的兩條依賴邊仍停在已關閉的站，前次 review-01 已提的缺口沒有被處置。四項都有檔名與行號可核對，共 4 項 Major，依規則判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-service/functional-design/functional-spec.md 5.2 的 FD8-1；entities.md 2.1；rules.md BR7.1 與 BR7.2；inception/delivery-planning/bolt-plan.md:133；inception/contract-design/contract-summary.md 的 K-08 consumers、K-11 與 K-12 的 observable side effects | 前次 review-01 已提（R-01、R-02 合併重列）。BR7.1 與 BR7.2 讓 U13 與 U12 同進程呼叫 MemoryFacade.write，等於新增 U13 到 U8、U12 到 U8 兩條邊。FD8-1 把通知指向 delivery-planning（2.9），但該站已完成且在游標之前，無機制能接收。bolt-plan.md:133 是已核可計畫上仍未勾選的項目，逐字要求新邊必須回報該檔並重審 Bolt 順序、不得直接在實作中加邊。K-08 的 consumers 只列 U11 與 U15，U12 與 U13 各自的 side effects 清單也沒有記憶寫入，三份已核可契約都看不到這兩條邊。凍結的產出仍留著這個缺口。 | 在關卡上裁決：重開 delivery-planning，或直接在 bolt-plan.md 登記兩條邊並確認 Bolt 序仍成立。同時登記對 K-08、K-11、K-12 三份契約的修訂。FD8-1 的承接改為這一項具體動作，不再指向已關閉的站。 | New |
| R-02 | Major | functional-spec.md 1.4 步 2 與步 3；rules.md BR4.1 與 BR4.3；backend/services/memory_facade.py:364-416（delete） | 設計是先取列、不存在拋 MemoryNotFound，再比對擁有者、不符拋 MemoryForbidden(reason="owner")，對外為 404 與 403 兩種回應。同一份 functional-spec 的 1.5 自己說明這種 404 與 403 差異構成記憶存在性 oracle，因而放寬流程把角色檢查放在取列之前。已落地的程式（memory_facade.py:372-410）對不存在與非擁有者都回 MemoryNotFound，只在日誌區分，並註明此為 D1 決定、不得改回 MemoryForbidden。因為 id 是連續整數，設計版本讓任何已認證使用者可枚舉整張表存在哪些 id，屬 ADR-0006 的 IAM 面向。設計與程式矛盾，程式這一邊是對的。設計另未規範被拒絕的嘗試要寫應用日誌，程式有 log_denied，audit logging 面向在設計裡沒有落點。 | 修訂 1.4 與 BR4.1：非擁有者與不存在對外一律 MemoryNotFound，內部日誌保留 reason 區分，並補上拒絕事件的日誌要求。以程式為準。 | New |
| R-03 | Major | functional-spec.md 1.1 到 1.6 各流程的第 1 步；rules.md BR1 到 BR6；backend/services/memory_facade.py:187-203 與各公開方法首行 | 設計的每個流程只取「已驗證身分」，授權只有擁有者模型與角色模型兩套。已落地的程式在六個公開方法第一行都呼叫 _authorize_approved，帳號未核准一律回 403（REASON_PENDING），且判定先於取列。設計與規則沒有這個授權面向，也沒有對應 BR 或 AC，導致一條實際存在的 IAM 判定在設計上無來源可追。若重新依設計實作，pending 帳號可讀寫記憶。 | 新增一條規則（如 BR1.3 或獨立組）：未核准帳號對全部六個入口一律拒絕且先於任何取列，並登記驗證方式與 allow 與 deny 雙向測試。以程式為準。 | New |
| R-04 | Major | entities.md 的 embedding 與 embeddingModel 欄位說明；rules.md BR3.3 與 BR3.5；functional-spec.md 1.1 步 5 與步 6；backend/services/memory_facade.py:215-243（_require_port）；backend/.env.example:120 | 設計同時宣稱兩件互相衝突的事。其一，fulltext 模式寫入的列允許 embedding 為空，且這是「fulltext 退路」，不得補齊（BR3.3）。其二，embeddingModel 即使 embedding 為空也必填，且寫入一律先向 U6 取向量與模型識別字、提供者不可用就停止（步 5 與步 6）。fulltext 下 U6 不建立 Port、model_id 為 None，所以 fulltext 退路根本寫不出列。程式註記為 CG8-1 並在 fulltext 下寫入直接失敗，而 .env.example 的預設正是 fulltext，等於預設設定下記憶寫入入口全數失敗。設計沒有指出這個缺口，也沒有指派承接。 | 在設計中裁決 fulltext 之下 embeddingModel 該填什麼（或明確宣告 fulltext 不支援寫入），修正 BR3.3 的描述使其與 BR3.5 不矛盾，並指派承接單元與 stage。 | New |
| R-05 | Minor | inception/units-generation/unit-of-work.md 修訂 4 Assumptions；本站四份產出 | 前次 review-01 R-04 已提：unit-of-work 記錄 U23 的記憶摘要籤讀取依賴 U8，本站產出完全未提 U23，K-08 consumers 也沒有它，讀者容易誤以為 consumers 已窮盡。 | 補一行說明 U23 的讀取路徑不在本站範圍，並指派 U23 的 functional-design 補上 K-08 consumers。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| 人工比對 BR7.4 裁決 | 通過 | contract-summary.md 第 643 行與第 1386 行確為矛盾，action 封閉集合沒有建立值，採第 1386 行正確（前次 review 已逐字核過，本次未重驗） |
| 設計與 memory_facade.py 比對 | 3 處矛盾 | delete 的 404 與 403 流程（R-02）、未核准帳號判定（R-03）、fulltext 寫入（R-04）；程式一側皆較設計安全或較準確 |
| 自動化驗證工具與測試 | 未執行 | 本次審查規定不得執行會產生快取或寫檔的指令 |
