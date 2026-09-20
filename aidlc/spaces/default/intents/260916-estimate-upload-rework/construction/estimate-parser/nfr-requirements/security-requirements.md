# Security Requirements — estimate-parser

> Unit: `estimate-parser`（U1）· kind: **library**  
> 上游：`requirements.md` NFR3／NFR4／NFR6／NFR7、FR1.3–1.4（U2 擋檔）、FR2.3–2.4、FR9.6、ADR-0006；澄清 Q1–Q6=A。

## ADR-0006 四面向

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **不適用** | 無雲端憑證、無帳號權限；純函式處理呼叫端傳入的 `bytes`。 |
| **Encryption** | **不適用（無靜態密鑰）** | 不持有／不持久化估價表原文（FR1.6 屬 U2）；本 unit 不新增加密欄位。 |
| **Network exposure** | **不適用** | 無入站／出站；禁止 `httpx`／`requests`（FR2.3）。 |
| **Audit logging** | **不適用（事件稽核）** | 事件層稽核屬 U2（NFR5）。錯誤訊息不洩路徑／堆疊見 **NFR3.2**（屬錯誤面契約，非 audit event）。 |

## NFR3.1 — 解析資源界限（Q1=A）

繼承 **NFR3**（上傳面安全的「解析過程資源界限」落點）。

- U2 已執行 FR1.3（5 MB）與 FR1.4（副檔名／魔數）；本 unit 仍須防記憶體內膨脹。
- **硬上限（可機械驗證）**：
  - 資料列數 ≤ **50_000**
  - **位元組上限 32 MiB**，量測定義：
    - **CSV**：解碼後 UTF-8 文字的 byte 長度（`len(text.encode("utf-8"))`）
    - **XLSX**：workbook ZIP 內所有 entry **未壓縮大小加總**（`ZipInfo.file_size` 之和）≤ 32 MiB；不以「cell 個數×常數」換算
- 超出任上限：回傳 `detection.status=ambiguous` 且 `lines=[]`（或等價空結果），**不得** raise 使進程崩潰。
- **通過條件**：以超量 fixture 呼叫 `parse` 時不 OOM／不無限迴圈；回傳符合上列形狀。

## NFR3.2 — 錯誤訊息不洩路徑／堆疊（Q2=A）

繼承 **NFR3**。

- 公開 API（`parse`／`validate`）拋出的例外訊息**不得**含本機絕對路徑或 traceback 字串；允許短語意代碼或短中文說明。
- 回傳資料結構（`ParseResult`／`MechanicalCheckResult`）**不得**攜帶堆疊。
- 驗証方式歸 code-generation／測試（本 NFR 訂行為契約，不指名測試檔路徑）。

## NFR4.1 — Property-based testing 下限（Q3=A）

繼承 **NFR4**／**FR2.4**／ADR-0006。

- code-gen 須產出至少 **三條** Hypothesis 性質，涵蓋：
  1. 同輸入同輸出（確定性）
  2. 合法執行不觸發禁 import 路徑副作用（與 FR2.3／邊界腳本一致）
  3. BR4 機械檢查／對帳容差（或等價 deterministic 性質）
- example-based 可輔佐，**不得**取代上述 PBT 下限。

## NFR6.1 — 純函式邊界與 CI 閘門（Q4=A）

繼承 **NFR6**／**FR2.3**／**FR9.6**。

- 模組不得 import `httpx`、`requests`、`sqlalchemy`、`fastapi`。
- `scripts/validate_cost_calculator_boundary.py`（及 CI 呼叫）改掃：
  - `backend/cost/estimate_parser.py`
  - `backend/cost/estimate_validator.py`
  - parser 直接 import 的同套件讀取器模組（若拆檔）
- **通過條件**：上述路徑命中禁 import → 腳本非 0；clean tree → 0。

## NFR7.1 — 可測試性義務邊界（Q6=A）

繼承 **NFR7**。

- 本 stage **不**手寫 TCMS markdown。
- code-gen 自動化測試須可被 `python -m unittest discover -s tests` 撿到。
- TCMS 手動／同步義務歸後續 `tcms-test-cases` stage。

## 明確不在本 unit

| 項目 | 歸屬 |
|---|---|
| 上傳大小／魔數／副檔名拒絕 HTTP | U2 |
| 進度 UI、端到端 3–5 分鐘 | NFR1／NFR2 → U2／U7 |
| 事件稽核、分享授權 | U2 |
| agent 品質檢查建議 | U7 |
| openpyxl 以外的新基礎設施 | 不做（見 tech-stack） |

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
