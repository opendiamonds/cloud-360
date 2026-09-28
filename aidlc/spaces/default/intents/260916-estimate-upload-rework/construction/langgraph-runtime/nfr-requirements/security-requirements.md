# Security Requirements — langgraph-runtime

> Unit: `langgraph-runtime`（U6）· kind: **library**  
> 上游：FR10.1–10.3、NFR7–NFR9、FD BR10.*、澄清 Q1–Q6=A。

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **不適用** | 無雲端供應商 IAM；模型存取用平台既有 `OPENROUTER_API_KEY`（與 U4 目錄價憑證無關）。 |
| **Encryption** | **適用（傳輸中）** | 出站 HTTPS 至 `https://openrouter.ai/api/v1`；金鑰僅存環境變數，不得寫入版控／磁碟設定檔真值。 |
| **Network exposure** | **適用（出站）** | 僅允許對 OpenRouter OpenAI 相容端點的出站呼叫；無入站 listener；不得另開任意 URL 代理。 |
| **Audit logging** | **不適用（事件稽核）** | 業務事件稽核屬 U2／U7（NFR5）。金鑰不外洩見 **NFR9.1**（資料保護面，非 audit event）。 |

## NFR9.1 — 金鑰與錯誤面契約（Q5=A）

繼承 **NFR9** 精神（憑證不得進日誌／錯誤訊息）。

- 例外訊息、`StreamEvent`、`InvokeOutcome`、應用 log **不得**含 `OPENROUTER_API_KEY` 的值。
- 允許出現：環境變數**名**、HTTP status code、短語意錯誤碼。
- 缺金鑰：拋 `RuntimeAuthError`，訊息含變數名、不含值（FD BR10.4、entities.md `RuntimeAuthError`）。
- **通過條件**：unittest 至少一條斷言／突變覆蓋「回傳與例外字串不含金鑰值」。

## NFR9.2 — 呼叫資源界限（Q1=A、Q2=A）

- **預設逾時 60 秒**（HTTP／客戶端）；呼叫端可經 `config` 覆寫。
- **本 unit 不做自動重試**；暫時性失敗一次上拋，重試由 U7 編排（避免雙重重試放大費用）。
- 逾時／上游錯誤上拋可診斷訊息，仍遵守 NFR9.1。

## NFR8.1 — 部署可執行（無新瀏覽器／CLI 依賴）

繼承 **NFR8**。

- 新路徑僅依賴純 Python 套件（見 tech-stack）；**不得**為本 unit 引入 Playwright、本機 `claude` CLI 或 Node 以外的新執行期元件。
- `claude-agent-sdk`／Node 22 因 FR10.3 **保留**（其他 agent），但本 unit 執行路徑不呼叫它們。

## NFR7.1 — 可測試性義務邊界（Q6=A）

繼承 **NFR7**。

- 本 stage **不**手寫 TCMS markdown。
- code-gen：unittest＋mock 覆蓋成功／缺金鑰／逾時形狀；真實 OpenRouter 為選跑 smoke（FD BR10.6）。
- TCMS 義務歸後續 `tcms-test-cases` stage。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| 端到端 3–5 分鐘、進度 UI | NFR1／NFR2 → U7／前端 |
| 建議圖節點、提示詞、三類建議 | U7 |
| 目錄價 IAM／GCP key 管線 | U4／U5 |
| 其餘五個 agent 的 LangGraph 遷移 | FR10.4 範圍外 |

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
