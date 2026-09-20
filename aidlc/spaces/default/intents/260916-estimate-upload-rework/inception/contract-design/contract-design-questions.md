# Contract Design 問答：C1 估價表上傳

Units-generation Q7=A 已定案本期正式化三類邊界：**對外 HTTP API**、**SSE 事件格式**、**解析器輸出結構**。查價結果結構（U5→U7）本期不強制正式化。本站只釘契約形狀與所有權，不決定 Bolt 順序。

## Sources

- **[S1]** `unit-of-work-dependency.md` 整合點表：U1→U2 解析器輸出；U2→U8／U7 HTTP；U7→U9 SSE；U7→U2 授權查詢（可落 functional-design）；U5→U7 查價本期不正式化。
- **[S2]** 既有 `openapi.json` 的 `/api/cost/*` 九個 operations 將隨 U3 退場；新頁仍用 `/cost`（FR3.3），但 API 路徑未定。
- **[S3]** A1／A3 SSE 先例：`text/event-stream`，`data:` 行為 JSON（`agent_router.py` 註解：`{type, content}`）；須加 heartbeat（units U7）。
- **[S4]** FR1.3–1.4／NFR1：上傳 5MB×3；建議 3–5 分鐘、逾時後明細仍可用。
- **[S5]** repo 以單一 `openapi.json` 為 API 契約真實來源，CI drift 閘門強制。

---

## Q1 新對外 HTTP API 的路徑前綴

舊 `/api/cost/diagrams/...` 整組退場。新資源是估價批次（`EstimateSet`），不再掛在架構圖下。

- **A.** `/api/estimates` — 新前綴，語意貼合；OpenAPI 與舊路徑並存期間較清晰
- **B.** 沿用 `/api/cost` 但換成新 operations（例如 `/api/cost/sets`）— 前端改動較小，語意仍叫 cost
- **C.** `/api/cost/estimates` — 折衷：保留 cost 命名空間、子路徑標明估價表
- **X.** Other (please specify)

[Answer]: B — 沿用 `/api/cost` 但換成新 operations（例如 `/api/cost/sets`）

---

## Q2 契約清單怎麼切

草案四份契約（對應 Q7=A + 審閱 R-01 的授權邊界是否列入見 Q5）：

| # | Provider | Consumer | Mechanism |
|---|---|---|---|
| C1 | U1 `estimate-parser` | U2 | shared-schema（解析結果） |
| C2 | U2 `estimate-intake-api` | External: SPA（U8／U9）與 U7 | OpenAPI（REST） |
| C3 | U7 `cost-advice-agent` | External: SPA（U9） | AsyncAPI（SSE） |
| C4? | U2 | U7 | 授權查詢（見 Q5） |

- **A.** 三份：C1＋C2＋C3（授權查詢留給 functional-design）
- **B.** 四份：加上 C4，把 U7→U2 授權簽章也寫進 contract-summary
- **C.** 兩份：合併 C2＋C3 為單一「對外 API」文件（REST＋SSE 同檔）
- **X.** Other (please specify)

[Answer]: A — 三份：C1＋C2＋C3（授權查詢留給 functional-design）—— **與 Q5=B 衝突，見追問 F1**

---

## Q3 版本與破壞性變更政策

本系統目前無對外公開 API 版號慣例；消費者主要是自家 SPA。

- **A.** 無 URL 版號；破壞性變更須同批改 SPA（deploy-on-merge）。契約檔以欄位 `x-cloud360-stability: draft|stable` 標示
- **B.** URL 帶 `/v1`，破壞性變更開 `/v2` 並重疊服務一個 Bolt 週期
- **C.** 僅 OpenAPI `info.version` 遞增；破壞性變更靠 PR 檢討，無執行期並存
- **X.** Other (please specify)

[Answer]: B — URL 帶 `/v1`，破壞性變更開 `/v2` 並重疊服務一個 Bolt 週期

---

## Q4 錯誤與逾時行為（對外 REST／SSE）

- **A.** REST：問題詳情用 RFC 7807 `application/problem+json`；上傳超過限制回 413／400 並含可顯示訊息。SSE：逾時（5 分鐘）送 `type=timeout` 事件後關閉串流；客戶端斷線不取消背景工作（F1=B）
- **B.** REST：沿用現況 FastAPI `{"detail": ...}`；SSE 同上
- **C.** REST 用 problem+json；SSE 逾時不送事件、只關閉連線，客戶端靠輪詢 Advice 狀態補洞
- **X.** Other (please specify)

[Answer]: B — REST 沿用 FastAPI `{"detail": ...}`；SSE：逾時送 `type=timeout` 後關閉；斷線不取消背景工作

---

## Q5 U7→U2 授權查詢是否納入本站契約

審閱 R-01：`AdviceOrchestrator` 呼叫 `EstimateAccessControl`。這是同 process 的 Python 呼叫，不是 HTTP。

- **A.** 不納入——僅在 contract-summary 的「非正式化邊界」附註列出，簽章由 functional-design 釘選
- **B.** 納入——以 shared-schema／函式簽章區塊正式化（輸入 estimateSetId＋user、輸出 allow/deny）
- **X.** Other (please specify)

[Answer]: B — 納入——以 shared-schema／函式簽章區塊正式化 —— **與 Q2=A 衝突，見追問 F1**

---

## Q6 解析器輸出（C1）的規格格式

- **A.** `shared-schema` YAML：定義 `ParseResult`／`LineItem`／`CloudDetection` 欄位、型別、必填與 `parseStatus` 枚舉
- **B.** 內嵌 JSON Schema（draft 2020-12）於 fenced block
- **C.** 只寫 TypeScript／Python 偽型別對照表，不寫 schema 方言
- **X.** Other (please specify)

[Answer]: A — `shared-schema` YAML：`ParseResult`／`LineItem`／`CloudDetection`

---

---

## 追問（作答後的歧異）

### F1 — Q2=A 與 Q5=B 衝突：授權查詢要不要算「正式契約」？

Q2 選「三份、授權留給 functional-design」，Q5 選「納入正式化」。兩者只能留一個。

- **A.** 採 Q5：改為**四份契約**（C1–C3 ＋ C4 授權簽章），推翻 Q2=A 的「三份」
- **B.** 採 Q2：維持三份；Q5 改為「只在附註列出，簽章由 functional-design 釘選」
- **X.** Other (please specify)

[Answer]: B — 採 Q2：維持三份契約；授權查詢只在附註列出，簽章由 functional-design 釘選

### F2 — `/api/cost`＋`/v1` 的拼法（Q1=B × Q3=B）

- **A.** `/api/cost/v1/...`（版本在 cost 命名空間內）
- **B.** `/api/v1/cost/...`（版本在全域 API 前綴）
- **X.** Other (please specify)

[Answer]: A — `/api/cost/v1/...`

---

## Consolidated Summary Confirmation

**四份定案後的契約計畫（F1 採三份）：**

| # | Provider | Consumer | Mechanism | Owner |
|---|---|---|---|---|
| C1 | U1 `estimate-parser` | U2 | shared-schema YAML | U1 |
| C2 | U2 `estimate-intake-api` | External: SPA（U8／U9）＋U7 | OpenAPI REST | U2 |
| C3 | U7 `cost-advice-agent` | External: SPA（U9） | AsyncAPI SSE | U7 |

**路徑**：`/api/cost/v1/...`（Q1=B × Q3=B × F2=A）。破壞性變更開 `/api/cost/v2`，與 v1 **重疊一個 Bolt 週期**後再撤 v1。

**錯誤／逾時（Q4=B）**：REST 沿用 `{"detail": ...}`；SSE 逾時送 `type=timeout` 後關閉串流；客戶端斷線**不**取消背景工作。

**解析器（Q6=A）**：C1 用 shared-schema 定義 `ParseResult`／`LineItem`／`CloudDetection`。

**不納入本站正式契約**：U7→U2 授權查詢（F1=B，附註＋functional-design）；U5→U7 查價結果（units Q7 已排除）。

**後果**：自家 SPA 是主要消費者，卻仍引入 `/v1`／`/v2` 重疊成本——換得的是未來若有第二個客戶端時的緩衝。本期幾乎只有 SPA，重疊期的雙軌維護是明確代價。

[Answer]: Looks correct

照此產生 contract-summary.md。
