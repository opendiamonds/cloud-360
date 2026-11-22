## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-11-06T04:41:57Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `aidlc/spaces/default/intents/261105-d-iac-generation/inception/contract-design/contract-summary.md` > 操作與 RBAC 映射 > `GET /download` Story action 欄 | `GET /download` 的 Story action 欄記為「呼叫端須授權（不得以僅 `view` 放行執行語意；下載需成功草稿）」，但未命名具體的 D-story 與 action level（如 D1 `edit`）。表中其他所有路徑均明確列出（`D1 edit`、`D2 edit`、`D3 edit`、`D1 view`），此路徑留白。`stories.md` 的權限語意表格同樣寫「D1 成功草稿＋呼叫端授權（設計凍結；不得以 view 放行執行 API）」，仍未解析至具名 story action。Construction U1 開發者必須自行推斷，存在誤實作風險（例如以 D1 `view` 放行下載，違反「不得以僅 view 放行執行語意」的設計意圖）。 | 在操作表中為 `GET /download` 補上具名的 story action（如 D1 `edit`，或跨 story 的最低要求），或在 Open questions 表新增一筆並明確標出 Blocks 對象（U1 router 與 TestClient 雙向測試義務）。 | New |
| R-02 | Minor | `aidlc/spaces/default/intents/261105-d-iac-generation/inception/contract-design/contract-summary.md` > C1 > `/scan` 與 `/secrets/rewrite` requestBody 定義 | `POST /scan` 與 `POST /secrets/rewrite` 均宣告 `requestBody: required: false`，且其中的 `diagram_id` 未列入 `required` 陣列。然而 in-memory session 鍵為 `(user or session, diagram_id)`（components.md），省略 `diagram_id` 時伺服器無法確定操作哪一份 session/draft。`GateError.error.code` 枚舉（`missing_draft`、`missing_scan_report`、`stale_report_id`、`diagram_mismatch`、`invalid_diagram`）中亦無對應「session 無法解析」的錯誤碼。對比之下 `GET /session` 將 `diagram_id` 標為 required query param，存在明確的對稱缺口。Open questions 表未追蹤此問題，Construction U1 在 diagram_id 缺席時的行為沒有明確契約。 | 二選一：（A）在 `/scan` 與 `/secrets/rewrite` body schema 的 `required` 陣列加入 `diagram_id`，對齊 `/session` 的強制性；（B）在契約明文記載「省略 diagram_id 時伺服器以使用者 session 內最近一次活躍 diagram_id 解析」並在 `GateError.code` 枚舉加入對應的「無法解析」碼，同時追加至 Open questions 表並標出 Blocks。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 文本交叉驗證（Q1–Q5=A vs OpenAPI 路徑） | PASS | 能力動詞路徑（/generate、/scan、/secrets/rewrite、/session、/download）與 Q1=A 完全一致；無 URL 版號（Q4=A）；POST 無自動重試（Q5=A） |
| 閘碼對齊（stories.md US3.1/US4.1/US5.1） | PASS | US3.1 → missing_draft ✓；US4.1 → missing_draft ∧ missing_scan_report ✓；US5.1 → missing_draft ✓；HIGH/CRITICAL 確認明確交由 UI 且 API 不閘 ✓ |
| RBAC 403 vs 閘 422 分離 | PASS | 操作表與 OpenAPI 對每個路徑均區分 RBAC 403（缺 story action）與語意前置 422（GateError）；403 未出現在 GateError 枚舉內 |
| apply/destroy 排除 | PASS | 行為不變量明文「OpenAPI／工具清單靜態斷言：無 apply/destroy」；OpenAPI paths 中無 apply/destroy 操作 |
| Open questions 追蹤 | PASS（帶 R-01/R-02 保留意見） | 超時秒數、zip 目錄佈局、CLI 品牌、多雲標記慣例、PBT ADR 均有追蹤且明確標出 Blocks；/download story action（R-01）與 optional diagram_id（R-02）未追蹤 |
| unit-of-work + components 保真度 | PASS | session 行程內（ADR-002）、diagram_id-only（不擁有 Diagram）、三核心為同 process 模組、U1/U2 拓樸無依賴邊 — 皆與 unit-of-work.md 與 components.md 一致 |

### Summary

契約摘要的核心結構健全：契約一覽表清晰涵蓋 U2→U1 的跨 unit 邊界與所有權，inline OpenAPI 與 Q1–Q5=A 完全對齊，閘碼集合與 US3.1/US4.1/US5.1 的驗收標準吻合，RBAC 403 與語意前置 422 的分離乾淨，apply/destroy 排除明確，五個 Open questions 均有明確的 Blocks 對象且不阻擋契約核准路徑。兩項 Minor 發現供閘門人工斟酌：`GET /download` 的所需 story action 未命名（實作者缺乏明確依據），以及 `/scan`/`/secrets/rewrite` 允許省略 `diagram_id` 但未定義伺服器的解析行為（與 `/session` 的強制性形成不對稱，且 GateError 枚舉缺少對應錯誤碼）。
