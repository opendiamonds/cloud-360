# Security Requirements — credential-pipeline

> Unit: `credential-pipeline`（U4／B3）· kind: **packaging**  
> 上游：`requirements.md` NFR8／NFR9、FR5.8–5.9、FR11、ADR-0006；澄清 Q1–Q5=A。  
> **阻擋前提**：ADR-0018 未成文前，本文件所定策略不得進入 deploy／contract 實作。

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **適用 —— 本 unit 核心（注入範圍）** | 平台統一一組目錄價憑證；AWS 僅 `pricing:GetProducts` 等 Price List Query 所需動作；GCP API key 限 Cloud Billing Catalog。帳單／用量類 API 權限**不得**出現在此管線（FR5.7、NFR9）。執行期最小權限強制屬 U5；本 unit 負責 Secrets→env 傳遞不超標（FR5.9）。 |
| **Encryption** | **沿用既有** | 密鑰僅存 GitHub Secrets 與執行期 `deploy/.env`（不進版控）；傳輸沿用既有 HTTPS／Tunnel。本 unit 不新增欄位級加密。 |
| **Network exposure** | **不適用（無新入站）** | 不開新埠；憑證只供**出站**目錄價呼叫（U5）。 |
| **Audit logging** | **契約層適用** | 本 unit 規定：log／HTTP detail／traceback **不得**出現 secret **值**；變數名可出現（Q3=A）。執行期遮罩實作屬 U5。 |

## NFR9.1 — 版控與 contract：值樣式偵測（Q1=A）

繼承 **NFR9**。

- `scripts/validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS` **不得**再以「出現變數名 `AWS_SECRET_ACCESS_KEY`」為失敗條件（FR11.2／OQ7）。
- 改為攔「像真金鑰」的賦值（具體 regex，回應審閱 R-01）：
  - AWS：`AWS_SECRET_ACCESS_KEY\s*=\s*([A-Za-z0-9/+=]{40})`
  - GCP：`GCP_BILLING_API_KEY\s*=\s*(AIza[0-9A-Za-z\-_]{35})`
  - `BEGIN PRIVATE KEY` 維持字串禁令
- 範本（`backend/.env.example`、`deploy/.env.example`）與 `render-env.sh` 可寫**空值**或註解變數名；shell `${AWS_SECRET_ACCESS_KEY:-}` 通過。
- **通過條件（可機械驗證）**：含變數名但無密鑰值的受版控檔通過；含上列疑似密鑰賦值的檔失敗。

## NFR9.2 — 注入路徑與最小權限文件（FR11.1、FR11.3、FR5.9）

繼承 **NFR9**。

- 傳遞鏈：GitHub Secrets → `deploy/render-env.sh` → `deploy/.env` → `docker-compose.deploy.yml`（FR5.8、FR11.1）。
- 變數名沿用既有：`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_DEFAULT_REGION`、`GCP_BILLING_API_KEY`。
- `DEPLOY.md`／`LOCAL-DEV.md` 須載明：最小權限範圍、缺憑證可啟動（FR11.3、FR11.4）。
- IAM high-risk 三項（plan／impact／rollback）在 **ADR-0018** 與本 unit code-gen 一併寫入；本 NFR 定案：憑證僅目錄價存取方式，風險低於帳單類 API（NFR9 論據）。

## NFR9.3 — 日誌與錯誤訊息禁洩密鑰值（Q3=A）

繼承 **NFR9**。

- 契約：任何由本管線觸及的文件與 contract 測試須聲明——secret **值**不得出現在 log、HTTP detail、traceback；變數名允許。
- 本 unit **不**另加 CI grep 掃描 `echo`／`set -x`（Q3 否決 B）；執行期遮罩歸 U5。

## NFR8.1 — 無憑證可啟動；CI 永不注入真密鑰（Q2=A）

繼承 **NFR8**（部署環境可用性）與 **FR11.4**。

- `docker-compose.test.yml` 與 CI **不**注入 AWS／GCP 密鑰。
- 缺憑證時服務須可啟動；查價降級／略過屬 U5（FR5.10），本 unit 只保證注入為可選。
- **通過條件**：本機／test stack 在未設定上述變數時，backend 進程可完成啟動（不因 KeyError／必填 env 崩潰）。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| 目錄價 HTTP 客戶端、降級、遮罩實作 | U5 `pricing-lookup-port` |
| 每使用者自帶憑證 | 不做（FR5.8） |
| Vault／外部 secret manager | 不做（Q4=A） |
| 帳單／用量類 API 憑證 | 禁止（FR5.7） |

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
