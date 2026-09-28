# Security Requirements — legacy-cost-retirement

> Unit: `legacy-cost-retirement`（U3）· kind: **service**（退場）  
> 上游：FR9.*、FD BR9.*、澄清 Q1–Q6=A。

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **不適用（本 unit）** | 不新增雲端 IAM；目錄價憑證屬 U4／U5。退場不得放寬既有禁令。 |
| **Encryption** | **適用（靜態資料）** | `archive_*` 表可能含歷史成本列；與 live 表相同的 DB 靜態加密／主機防護沿用既有 Postgres 佈署，本 unit 不降級。 |
| **Network exposure** | **適用（縮減）** | 移除舊 `/api/cost` diagrams 等入站面，**減少**攻擊面；不得另開 archive 查詢 API（Q1=A）。 |
| **Audit logging** | **薄適用** | 業務稽核事件表 `cost_audit_event` 改名 archive 後不再由應用寫入；新稽核屬 U2。退場 PR 應在 DEPLOY／變更說明記載 rename 與到期日。 |

## NFR9.x — archive_* 存取（Q1=A）

- 應用程式碼（ORM／router／service）**零讀寫** `archive_*`。
- 僅 DBA／維運經受控 DB 連線查詢。
- **通過條件**：code-gen 後 repo 內不得有映射 `archive_diagram_cost` 等之應用查詢（測試允許字串斷言「不得出現」）。

## NFR — 憑證與 env（Q4=A）

- 刪除舊 C1 stub／calculator 相關環境變數讀取與範本項（如 `COST_PRICING_STUB` 等退場清單）；**保留** U4 已注入的目錄價憑證變數。
- 變更後 `validate_env_contract.py` 必須綠。
- 不得把金鑰真值寫進版控（既有 contract）。

## NFR7.1 — 可測試性（Q6=A）

- 本 stage **不**手寫 TCMS。
- code-gen：unittest／contract／e2e 刪改覆蓋退場；TCMS 歸 `tcms-test-cases`。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| 新 `/api/cost/v1` 授權 | U2 |
| 目錄價 IAM 執行期 | U5 |
| archive 到期 DROP | chore／operation（Q5=A） |

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
