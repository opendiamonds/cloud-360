# Security Requirements — pricing-lookup-port

> Unit: `pricing-lookup-port`（U5）· kind: **library**  
> 上游：FR5.5–5.10、FR9.4–9.5、FR9.7、NFR7–NFR9、ADR-0006、ADR-0018、FD BR5.*、澄清 Q1–Q6=A。

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **適用 —— 執行期消費端** | 僅呼叫目錄價動作（如 `pricing:GetProducts`）；GCP API key 限 Cloud Billing Catalog。帳單／用量類 API **禁止**（FR5.7、BR5.3）。憑證注入屬 U4；本 unit 強制最小權限消費與降級（FR5.9、BR5.5）。 |
| **Encryption** | **適用（傳輸中）** | 出站 HTTPS 至 allowlist 定價 host；憑證僅環境變數，不得寫入磁碟 offer 快取或版控。 |
| **Network exposure** | **適用（出站）** | 僅允許對 YAML allowlist 目錄價端點的出站呼叫；無入站 listener；禁止新增帳單類客戶端。 |
| **Audit logging** | **不適用（業務事件稽核）** | 事件稽核屬 U2／U7（NFR5）。密鑰不外洩見 **NFR9.1**（資料保護面）。 |

## NFR9.1 — 執行期密鑰紅線（Q3=A）

繼承 **NFR9**（U4 已定管線與版控值樣式；本 unit 釘執行期）。

- 例外訊息、`PriceHit`／`PriceMiss`／`PriceUnsupported` 序列化結果、應用 log **不得**含 `AWS_SECRET_ACCESS_KEY`／`GCP_BILLING_API_KEY` 值。
- 允許：環境變數**名**、HTTP status、botocore error code、短語意說明。
- 磁碟 offer 快取（`.pricing_offer_cache`）僅存 `hourly`／`fetched_at`（及解析所需公開欄位）；**不得**寫入憑證。
- **通過條件**：unittest 至少一條斷言／突變覆蓋「失敗路徑字串不含密鑰值」。

## NFR9.2 — 目錄價邊界與降級（Q1=A、Q2=A、FR5.10）

繼承 **NFR9** 精神與 **FR5.10**。

- 出站逾時：connect 預設 3s；read 預設 180s（`COST_PRICING_OFFER_READ_TIMEOUT` 可覆寫）；SDK 逾時沿用 `COST_PRICING_SDK_TIMEOUT`。
- **不做**額外自動重試迴圈；失敗走 SDK→Bulk／Catalog／Retail→Miss／Unsupported。
- 缺憑證或呼叫失敗：**不得**拋未處理例外使建議流程失敗（BR5.4）。
- `COST_PRICING_USE_SDK` 預設可啟用（`auto`／未設）；顯式 `0`／`false`／`no` 關閉（Q4=A、FR9.4）。

## NFR9.3 — 唯讀與禁帳單 API（BR5.2、BR5.3）

- 查得**價格**不得進入估價明細寫入路徑（AH-6、BR5.2）。規格文字描述得經 `sku_catalog` 寫入 `spec_description`（FR13），不含 hourly。
- 禁止實作／呼叫 Cost Explorer、Cost Management、Billing Export 或等價帳單／用量 API（FR5.7）。

## NFR8.1 — 部署可執行；無憑證可啟動

繼承 **NFR8**、**FR11.4**。

- 新路徑僅依賴既有 Python 套件（`httpx`、`boto3` 等）；**不得**為本 unit 引入 Playwright 或本機 CLI 查價。
- 缺 IAM／GCP key 時應用仍可啟動；查價降級為公開 Bulk 或 Miss。
- warm／死腳本失敗不得阻止應用啟動（BR5.10）。

## NFR7.1 — 可測試性與邊界 CI（Q5=A、Q6=A）

繼承 **NFR7**。

- 本 stage **不**手寫 TCMS markdown。
- code-gen：unittest＋mock 覆蓋 hit／miss／unsupported、SDK 降級、密鑰遮罩；邊界腳本：
  1. intake 寫入模組不得 import `pricing_client`／`pricing_sdk`（得延遲 import `sku_catalog`）
  2. 非 `pricing_*` 存活集、且非 `cost/sku_catalog.py`，不得直打 allowlist 定價 host
- TCMS 義務歸後續 `tcms-test-cases` stage。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| Secrets→env 注入、contract 值樣式 | U4 |
| 建議正文／SSE、查價失敗時的 agent 文案 | U7 |
| 上傳／明細 API | U2 |
| 端到端 3–5 分鐘、進度 UI | NFR1／NFR2 → U7／前端 |

<!-- confirmed: Looks correct -->

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-19T20:00:00Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|

### Summary
NFR READY after GATE_REJECTED floor reset; empty findings.
