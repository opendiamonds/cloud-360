# NFR Requirements — 釐清問題（pricing-lookup-port）

> Unit: `pricing-lookup-port`（U5）· kind: **library**  
> Stage: nfr-requirements · 適用產物：security-requirements、tech-stack-decisions、traceability  
> （performance／scalability／reliability／observability 對 library **多為 N/A**；本 unit 僅釘目錄價 Port 的安全／逾時／邊界／tech）  
> 作答：在每題 `[Answer]:` 後填選項字母（例如 `A`）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 公開入口 `fetch_hourly`；文件稱 PricingLookup | FD Q1=A、BR5.1 |
| 保留 24h 磁碟 offer 快取；不重建 Postgres `pricing_cache` | FD Q2=A、BR5.6、FR9.2 |
| AWS SDK 可啟用；無憑證／失敗 → Bulk → miss；不讓 U7 崩潰 | FD Q3=A、BR5.4、FR5.10 |
| 盤點 warm／死引用並修或刪 | FD Q4=A、BR5.10、FR9.7 |
| CI：intake 不得 import Port；他處不得直打 Pricing host | FD Q5=A、BR5.7–5.8 |
| 僅 GCP Catalog、Azure Retail；禁帳單 API | FD Q6=A、BR5.3、FR5.7 |
| 憑證注入管線屬 U4；ADR-0018 已 Accepted | U4 CG、FR11 |
| 端到端 3–5 分鐘（NFR1）、進度 UI（NFR2）、事件稽核（NFR5）非本 unit 獨責 | requirements／U7／U2 |
| NFR7 TCMS 為 intent 級 blocking；本 stage 是否手寫測案另問 | project.md Mandated |

---

## Questions

### Question 1
**出站逾時怎麼釘？**（Bulk／Catalog／Retail 的 httpx；SDK 另見既有 `COST_PRICING_SDK_TIMEOUT`）

A. **維持既有 YAML／env**：connect 預設 3s；read 預設 180s，可用 `COST_PRICING_OFFER_READ_TIMEOUT` 覆寫。逾時視為暫時失敗 → 降級／Miss，**不**拋未處理例外中止建議。**（建議）**

B. **收緊 read 預設為 30s**（仍可 env 覆寫）；其餘同 A。

C. **不設逾時**——完全交給 httpx／boto3 預設。

X) Other

[Answer]: A — 維持 connect 3s／read 180s（可 env 覆寫）；逾時降級／Miss，不中止建議

---

### Question 2
**暫時性失敗的重試？**

A. **本 unit 不做額外自動重試迴圈**；一次失敗即走既有降級鏈（SDK→Bulk→Miss）。避免與 U7 編排雙重重試。**（建議）**

B. **有限重試**：同一端點最多 2 次、短退避，再降級。

C. **無限重試直到總逾時**（不建議）。

X) Other

[Answer]: A — 不另做重試迴圈；失敗走 SDK→Bulk→Miss 降級鏈

---

### Question 3
**憑證／金鑰在錯誤與日誌的紅線（NFR9 執行期面，U4 已定管線）？**

A. **契約**：例外訊息、回傳結構、應用 log **不得**含 `AWS_SECRET_ACCESS_KEY`／`GCP_BILLING_API_KEY` 值；可含變數名、HTTP／botocore 錯誤碼。unittest 至少一條突變／斷言覆蓋。磁碟 offer 快取只存 hourly／timestamp，不存憑證。**（建議）**

B. **僅文件載明**；不要求專用測試斷言。

X) Other

[Answer]: A — 例外／log／回傳不含密鑰值；有測試；快取無憑證

---

### Question 4
**`COST_PRICING_USE_SDK` 預設與啟用語意（FR9.4）？**

A. **預設 `auto`（或未設＝可啟用）**：有 IAM 時可走 SDK；顯式 `0`／`false`／`no` 關閉。與現有 `pricing_sdk.use_sdk_enabled()` 對齊並寫進 tech-stack／DEPLOY。**（建議）**

B. **預設強制 `0`（僅 Bulk）**；須顯式 `1` 才啟用 SDK。

C. **移除開關**，永遠嘗試 SDK。

X) Other

[Answer]: A — 預設 auto／可啟用；顯式 0 關閉；對齊既有 use_sdk_enabled

---

### Question 5
**邊界 CI 腳本範圍（BR5.7–5.8）？**

A. **兩項檢查**：(1) intake 寫入模組（`estimate_intake_*`／`estimate_access`／`estimate_audit` 或等價）不得 import `pricing_client`／`pricing_sdk`；(2) `backend/` 內非 `pricing_*` 存活集不得以 httpx／requests 直打 allowlist 定價 host。命中即 CI 失敗。**（建議）**

B. **只做 (1) intake import 禁令**；直打 host 靠 code review。

C. **掃整個 repo**（含 frontend／scripts）禁任何定價 host 字串（過寬）。

X) Other

[Answer]: A — intake import 禁令 + 非存活集禁直打 allowlist host

---

### Question 6
**本 stage 是否產出 TCMS 手寫測案？**（NFR7）

A. **否**——歸後續 `tcms-test-cases` stage；本 unit 以 unittest＋mock／邊界腳本滿足可測試性。**（建議；與 U1／U6 一致）**

B. **是**——本 stage 另寫 TCMS 案例草稿。

X) Other

[Answer]: A — 本 stage 不寫 TCMS；歸 tcms-test-cases

---

## Consolidated Summary Confirmation

**U5 `pricing-lookup-port` NFR 定案**

| 項 | 定案 |
|---|---|
| 逾時 | connect 3s／read 180s（可 env）；逾時→降級／Miss（Q1=A） |
| 重試 | 不另做重試；走 SDK→Bulk→Miss（Q2=A） |
| 密鑰紅線 | 例外／log／回傳不含值；快取無憑證；有測試（Q3=A） |
| SDK 開關 | 預設 auto／可啟用；顯式 0 關（Q4=A） |
| 邊界 CI | intake 禁 import＋禁 Port 外直打 host（Q5=A） |
| TCMS | 本 stage 不手寫；歸 `tcms-test-cases`（Q6=A） |

**將產出**：security-requirements.md、tech-stack-decisions.md、traceability.json（library：performance／scalability／reliability／observability 標 N/A）。

**後果**：code-gen 須落地邊界腳本、密鑰遮罩測試、warm／死引用盤點；不新建 `pricing_cache` 表。

[Answer]: Looks correct

確認後產出 security／tech-stack／traceability。
