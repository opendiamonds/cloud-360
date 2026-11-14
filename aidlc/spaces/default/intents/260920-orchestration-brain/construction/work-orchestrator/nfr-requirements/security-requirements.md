# 安全需求 — `U12 work-orchestrator`

> `NFR12` 的 parent id 理由見 `performance-requirements.md` 檔頭。

## 〇、上游依據

| 依據 | 內容 |
|---|---|
| 本單元 functional-design | `BR51.1`–`BR51.8` 授權與呼叫、`BR58.4` 不洩內部錯誤；第七節 ADR-0006 四面向（修訂 2 的 IAM、Encryption 兩列） |
| `X-01`／`X-02` | 呼叫既有 C1／A1／A3 一律走 HTTP 帶使用者 token，不得同進程直呼既有 service 層 |
| `[RA:FR10.2]`／`FR11.6` | agent 不得做使用者不能做的事；稽核主體為使用者本人 |
| `team.md` 測試底線 A／B | 授權相關須 allow／deny 雙向；本單元**不新增 HTTP 端點**，故規則 B 不觸發，雙向測試以「經真實 app 的同進程呼叫」承載 |

## 一、資料分類

| 資料 | 分類 | 落地 | 處置 |
|---|---|---|---|
| 使用者 bearer token | **憑證** | 不落地，只在記憶體內傳遞（`BR51.2`） | `NFR12.6` |
| `requestText`（使用者原句，至多 2000 字） | **內部（使用者內容）** | Redis，隨工作階段 24 小時（`[WO3]`=A） | 靜態加密要求併入上游 `OQ-3`（指派 `nfr-design`）；本站不另定手段 |
| 變更紀錄的需求摘要（前 200 字） | 內部（使用者內容） | PostgreSQL `diagram_change_records` | 同上，併入 `OQ-3` |
| 工作項狀態、label、sideEffect | 內部 | Redis | 不含原句全文（`BR52.2`）、不含憑證 |

## 二、授權

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR12.6`** | token 不寫入工作項、工作階段或 log（`BR51.2`） | 以標記字串作 token 執行完整交辦：Redis 該 key 的所有欄位值與擷取到的 log 皆不含標記 |
| **`NFR12.7`** | 對既有能力的呼叫帶使用者本人的 token，走完整 HTTP dependency（`BR51.1`）。**allow／deny 雙向**：① 角色有 A1 edit → 架構設計工作項進入 `request_sent`；② 角色無 A1 權限 → 工作項失敗，原因為 `BR51.3` 的固定句型；③ token 過期 → 失敗為 `BR51.6` 的句型；④ C1 view 有／無各一案 | 以真實 app（ASGITransport）＋測試資料庫執行，四組各至少一案且全綠；突變驗證：把 Authorization 標頭改為固定的管理者 token 時 ② 變紅 |
| **`NFR12.8`** | 本單元模組不得 import 既有能力的 service 層（`X-01`／`X-02`） | 本單元新增模組對 `estimate_intake_service`、`advice_orchestrator`、`design_agent`、`review_orchestrator`、`collab_router` 的 import 數為 0（grep） |
| **`NFR12.9`** | facade 呼叫不沿用握手時的角色快照：每次呼叫重新自 DB 取使用者並以 `mint_principal` 鑄造（`BR51.7`）；**存回之前**使用者被停用 → 依 `BR51.3` 失敗；**存回之後**的 facade 失敗不改 status（帶入項 5） | 案例：A1 回應之前把使用者 `is_active` 設為假 → 工作項失敗且未 PUT；PUT 之後才停用 → 工作項狀態依 `BR51.4` 的 violation_behaviour |

## 三、輸出不洩漏

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR12.10`** | 送給使用者的訊息不含例外原文、內部錯誤或 token（`BR58.4`） | 讓能力替身拋出含標記字串的例外：sink 收到的所有訊息皆不含標記 |
| **`NFR12.11`** | log 不含 `requestText` 全文 | 以標記字串作使用者原句執行交辦（含失敗路徑）：擷取到的 log 不含標記 |

## 四、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 新的加密手段 | 本單元不新增傳輸路徑（ASGI 傳輸不出行程）；新增的兩處使用者內容落地併入上游 `OQ-3`，由 `nfr-design` 統一決定，不在單元層各自定 |
| 本單元自己的稽核事件 | `AC10.2.4` 的可觀察結果不存在（C1 讀取端點不寫稽核），處置已交使用者裁決（`OPEN-WO12-6`）；本站不預選 |
