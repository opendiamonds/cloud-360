# Security Requirements — estimate-intake-api

> Unit: `estimate-intake-api`（U2）· kind: **service**  
> 上游：FR1／FR7／FR8、NFR3／NFR9、FD BR2.*、澄清 Q1–Q6=A。

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **薄適用（應用 RBAC）** | JWT＋story `C1`（語意＝上傳與檢視估價表）；移除 `C1h`／`C1r`／`C1o`／`C1b` seed。雲端目錄價 IAM 屬 U4／U5，本 unit 不新增。 |
| **Encryption** | **沿用既有** | 估價明細存 Postgres；沿用部署既有靜態加密／主機防護，本 unit 不降級、不另開儲存。原始檔**不落地**（FR1.6）。 |
| **Network exposure** | **適用（新增受控面）** | 新增 `/api/cost/v1`（multipart＋JSON）；須魔數／大小／檔數驗證。不開 archive／內部 admin 旁路。不實作 SSE（U7）。 |
| **Audit logging** | **適用** | `EstimateAuditEvent`：upload／share_replace／delete／advice_enqueue（含失敗）；不含金額／明細／檔案（BR2.12、Q5=A）。 |

## NFR3 — 上傳面（Q1=A）

- 副檔名僅 `.csv`／`.xlsx`；魔數相符；單檔 ≤5 MB；單次 1–3 檔。
- 對外 HTTP `detail` **僅固定短語／錯誤碼**；不得含本機路徑、traceback、SQL、內部例外型別名。
- 日誌可記例外**型別**與 `estimate_set_id`／`user_id`；**禁止**檔案全文、金額、raw 列。
- 解析資源界限委 U1（列數／32MiB）；本 unit 在呼叫前完成 5MB／檔數擋下。

## NFR — 授權（FD BR2.5／BR2.10）

- 可見性＝擁有者 ∪ 分享名單；`diagram_id` 不參與授權。
- 不得 import `collab_router` 私有授權函式。
- code-gen 須 allow／deny 雙向 TestClient（C1 與分享邊界）。

## NFR9 — 憑證

- 本 unit **不**讀寫雲端目錄價金鑰；建議 enqueue 不把 secret 傳入 log。
- 錯誤／回應不得含 JWT 原文。

## NFR7.1 — 可測試性

- 本 stage **不**手寫 TCMS；歸 `tcms-test-cases`。
- code-gen：unittest＋TestClient 覆蓋上傳驗證、授權、刪除級聯、enqueue 失敗路徑。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| 進度 UI／SSE | U8／U9／U7 |
| 建議正文與查價 | U7／U5 |
| 目錄價 IAM 管線 | U4 |

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
