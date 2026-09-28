# RAID Log：C1 成本估算改版（上傳估價表）

R = Risks（風險）、A = Assumptions（假設）、I = Issues（已發生的問題）、D = Dependencies（依賴）。

## Risks

| ID | 風險 | 可能性 | 衝擊 | 緩解方向 | 負責階段 |
|---|---|---|---|---|---|
| RISK-01 | **解析靜默錯誤**：欄位對錯（月費當年費、數量對到單價、幣別誤判）不會報錯，畫面數字看似正常，agent 據以產生有自信的錯誤建議 | 中高 | 高 | **處置已於 2026-09-16 強化為兩層**：(1) agent 品質檢查 [Q10]，LLM 啟發式、無確定性保證；(2) approval-handoff AH-1 追加**確定性機械檢查**（總額對帳、幣別一致性、數量合理範圍），不需 SKU 對應，為必辦義務而非「評估是否」。注意 ADR-0017 §8 的 agent 按需查價**不算**第二層——它由 LLM 決定查什麼，不具確定性 | functional-design |
| RISK-02 | **3 分鐘預算不可達**：解析佔不到一秒，其餘全是 LLM 推論；三朵雲完整品項 × 三類建議可能超時。若新做法同樣因逾時失敗，改版沒有解決原本「太慢太常失敗」的問題，只是換了失敗點 | 中 | 高 | 設計階段做一次真實端到端量測；評估三類建議是否需分次產出或串流回傳；定義逾時後的降級行為 | nfr-requirements |
| RISK-03 | **完整估價內容送往第三方**：原始檔不留存但解析後完整內容送進 OpenRouter；估價表可能含客戶名稱、專案代號、內部服務命名 | 高（必然發生） | 中 | 使用者已知情並選擇此配置 [Q3][Q8]，屬已接受風險。設計階段應在 UI 明示資料將送往外部模型 | nfr-requirements |
| RISK-04 | **兩套 agent 框架並存**：本 intent 只遷成本 agent，其餘五模組另開 intent；期間兩套框架、兩條模型存取路徑的錯誤處理／逾時／重試／記錄形狀各異 | 高（必然發生） | 中 | 已是刻意的分階段決定 [Q12]。設計階段應定義兩套路徑的共用約定，降低後續五個模組遷移的成本 | nfr-requirements |
| RISK-05 | **匯出格式無預警改版**：三家官方工具的匯出格式可能在沒有通知的情況下變動，解析器在當天無聲失效 | 中 | 中 | 設計階段評估格式版本偵測（標頭欄位比對），失敗時明確報「格式不符」而非解析出垃圾 | functional-design |
| RISK-07 | **agent 查價把舊系統的脆弱處帶回來**（新增 2026-09-16，來源 ADR-0017 §8）：要查某品項的現價就得先做 SKU 對應——「asia-east1 的 e2-standard-4」對到目錄哪一筆。這正是舊自動估價最常失敗的環節 | 中高 | **低**（與舊架構的關鍵差異） | 衝擊評為低的理由：查價失敗是**非阻塞**的。舊架構下對不到 SKU 就估不出價，整件事停擺；新架構下對不到就是該筆「無法查證」，明細與建議照常產出。設計階段須明訂查不到時 agent 的行為（明說查不到，不得改用推測值） | functional-design |
| RISK-08 | **查得的目錄價與估價表的價格本來就不該相等**（新增 2026-09-16）：估價表可能含 CUD／RI／Savings Plan／區域或企業協議折扣，官方目錄價是定價。把兩者當同一種東西比較，會把正確的折扣價誤報為錯誤 | 高（必然發生） | 中 | ADR-0017 §8 已禁止以查得價格回寫明細，這條擋掉了最壞的後果。但 agent 的建議文字仍可能誤述「你的估價偏高」。設計階段須要求 agent 在引用現價時標明那是**未折扣定價** | functional-design |
| RISK-06 | **前端整頁改寫的範圍膨脹**：既有 Cost 頁繞著「選架構圖看成本」設計，新頁繞著「上傳看建議」設計，不是加欄位的程度 | 中 | 中 | 設計階段先定義頁面資訊架構再動工，避免邊做邊改 | functional-design |

## Assumptions

| ID | 假設 | 若不成立的後果 | 驗證時點 |
|---|---|---|---|
| ASSUM-01 | 三分鐘上限可達 | T7 需下修，或三類建議需改為分次產出 | 設計階段實測 |
| ASSUM-02 | 估價表不含個人資料，故 PCI／HIPAA／GDPR 均不觸發 | 若實際檔案含客戶聯絡人資訊，需重新做法規判定，且 RISK-03 的等級上升 | 取得真實樣本檔時 |
| ASSUM-03 | 「可選綁定架構圖」只是一個標籤，不需要一致性檢查（估價品項 vs 架構圖元件） | 若需要一致性檢查，工作量顯著增加 | domain-design |
| ASSUM-04 | 移除範圍以目前盤點為準（9 端點、4 表、runner 清單） | 若有隱性依賴，退場範圍需重新確認 | code-generation |
| ASSUM-05 | 各雲一種主格式足以覆蓋實際使用情境 | 使用者手上若是另一種格式則完全無法上傳 | 使用者實際試用時 |

## Issues

| ID | 問題 | 狀態 | 處置 |
|---|---|---|---|
| ISSUE-01 | **規則衝突**：P1「完全取代自動估價」與 `project.md` M2「必須沿用 `pricing_client` 三層計價架構」直接牴觸，construction 會被擋 | **已解決 2026-09-16** | ~~需 ADR 明確廢止或改寫 M2~~ → ADR-0017 已於 scope-definition 核可後產出：`pricing_client` 強制要求廢止、三層形狀保留並把 ADR-0006 的 PBT 落點由 `cost_calculator` 改錨至估價表解析器；`project.md`／`team.md` 五處已就地加註。同 C-01、DEP-04、intent-capture 審查 R-02 |
| ISSUE-02 | **三類建議全必備無優先序**：若其中一類（特別是跨雲比較）技術上難產，沒有可放棄的順位 | **已解決 2026-09-16** | ~~設計階段若發現難度不均，需回頭與使用者確認優先序~~ → scope-definition Q1 定案 B：省錢建議為核心 Must，跨雲比較與品質檢查降為 Should。注意品質檢查是 RISK-01 的唯一防線，降級後果已寫入 `scope-document.md` CAP-5。同 intent-capture 審查 R-01 |
| ISSUE-03 | **repo contract 既有違規**：`deploy/render-env.sh` 含 `AWS_SECRET_ACCESS_KEY` 字串，新版 validator 全域掃描後暴露 | 已知、暫緩 | 非本 intent 引入，但會讓本 intent 的 CI 紅燈。construction 前需處理 |
| ISSUE-04 | **既有測試污染**：`test_cost_api.py` 於 import 時全域設定 `COST_PRICING_STUB=1`，導致 `test_pricing_azure` 失敗 | 已知、暫緩 | 該測試檔屬退場範圍 [R1]，本改版移除舊端點時會一併消失 |

## Dependencies

| ID | 依賴 | 類型 | 風險 |
|---|---|---|---|
| DEP-01 | OpenRouter 的 OpenAI 相容端點可用性與延遲 | 外部服務 | 直接決定 RISK-02 是否發生；無替代路徑 |
| DEP-02 | LangGraph 套件與現行 Python 版本、既有依賴相容 | 新增依賴 | `requirements.txt` 目前僅 `fastapi`／`pydantic` 精確釘選，相容性未驗證 |
| DEP-03 | 試算表解析套件（供 Azure XLSX） | 新增依賴 | 目前 repo 完全沒有；選型未定 |
| DEP-04 | ISSUE-01 的 ADR | 內部產出 | ~~**阻擋 construction 開始**~~ → **已解除 2026-09-16**，見 ADR-0017 |
| DEP-05 | `schema_rbac.sql` 與 `DEPLOY.md` 的同批更新 | 內部流程 | blocking 規則，漏了即 CI 紅燈 |
| DEP-06 | `openapi.json` re-dump 與前端型別同步 | 內部流程 | CI 有 drift 檢查 |
| DEP-07 | `tcms-test-cases` stage 的測案產出與 `/tcms-verify` 通過 | 內部流程 | blocking，每個 intent 必經 |
| DEP-08 | 三朵雲的**公開免帳號**價目端點（AWS Bulk Price List、Azure Retail Prices、GCP Cloud Billing Catalog）| 外部服務（新增 2026-09-16，來源 ADR-0017 §8）| 不可用時 agent 查價功能靜默失效。GCP 那支需 `GCP_BILLING_API_KEY`；AWS 的 IAM 版 Pricing Query API **禁用**，只准公開 Bulk（較慢）|

## Assumptions & Open Questions

- ~~[open] DEP-04 的 ADR 由哪個階段負責產出尚未指派。它阻擋 construction，越晚處理改寫成本越高。~~ → **已關閉 2026-09-16**：scope-definition Q4 定案「現在就開」，ADR-0017 已在該 stage 核可後立即產出。
- ~~[open] RISK-01 的緩解「是否要補機械檢查」尚未決定。~~ → **已關閉 2026-09-16**：approval-handoff AH-1 定案要補，且明確要求不依賴 LLM。但「成功指標裡沒有任何一項衡量正確性」這點**仍然成立**——機械檢查會抓到錯，卻沒有指標在衡量它抓到多少。
- [open] T2（不留存原始檔）與 ADR-0006 稽核要求的交互未釐清：使用者事後質疑解析結果時沒有原始檔可回溯，稽核記錄要記到什麼粒度未定。
- [open] DEP-02／DEP-03 的套件選型未做，相容性與授權條款均未確認。
