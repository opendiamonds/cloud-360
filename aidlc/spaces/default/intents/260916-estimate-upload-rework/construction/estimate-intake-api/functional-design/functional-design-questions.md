# Functional Design 問答：U2 `estimate-intake-api`

本 Unit 是 **service（後端）**：新 `/api/cost/v1` 上傳／讀取／分享／刪除與持久化、授權、稽核，並在上傳成功後**觸發** U7 建議（不寫建議內容）。

**不含前端**：UI／`/cost` 頁面屬 **U8**（工作區）與 **U9**（建議呈現）。本站只釘後端行為與資料／HTTP 邊界。

## Sources

- **[S1]** U2：`unit-of-work.md` — EstimateIntakeService／AccessControl／AuditLog；實體 EstimateSet／Estimate／LineItem／Share／AuditEvent
- **[S2]** contract C2：`/api/cost/v1/sets*`；multipart 上傳；機械檢查每次重算不持久化；建議在 201 後背景執行
- **[S3]** domain：Q5=A 架構圖綁定＝純標籤；Q6=B 授權只看擁有者＋分享；Advice 由 U7 擁有、自帶 status
- **[S4]** FR1.*／FR6.*／FR7.*／FR8.*；NFR3／NFR6（`cost_router → cost_service → 純函式`）
- **[S5]** U1 已落地 `parse`／`validate`；U3 已移除舊 diagrams HTTP（v1 為本 Unit 新增）

---

## Q1 HTTP 模組落點（NFR6 三層形狀）

- **A.** 新建 `backend/cost/estimate_intake_router.py`＋`estimate_intake_service.py`（＋ access／audit 模組），由 `main.py` 掛載 prefix `/api/cost/v1`（建議；與已刪的舊 `cost_router` 檔名切開）
- **B.** 重建單一 `cost_router.py`，內含全部 v1 operations（沿用舊檔名）
- **C.** 路由放 `backend/services/`，cost 套件只留純函式／ORM
- **X.** Other (please specify)

[Answer]: A — 新建 estimate_intake_router／service（＋ access／audit），掛 `/api/cost/v1`
---

## Q2 上傳成功後如何觸發 U7（contract：201 後背景）

- **A.** `POST /sets` 在持久化成功後**同 request 內 enqueue**（例如 `BackgroundTasks`／執行緒池），立即回 201；失敗入佇列則寫 audit、Advice 可不建或建 `failed`（建議）
- **B.** 上傳只建批次；另開 `POST /sets/{id}/advice` 由前端／U8 明確觸發才產生
- **C.** 同步在上傳 request 內跑完整建議（違反「201 後背景」契約）
- **X.** Other (please specify)

[Answer]: A — POST 成功後同 request enqueue，立即 201
---

## Q3 `diagram_id` 綁定校驗（純標籤）

- **A.** 若有值：僅驗證為正整數；**不**查架構圖是否存在／可見（與 domain Q5=A／Q6=B 一致）（建議）
- **B.** 必須存在且上傳者對該圖有 view；否則 400／403
- **C.** 本 Unit 不接受 `diagram_id` 欄位（留給後續）
- **X.** Other (please specify)

[Answer]: A — 僅正整數標籤；不查圖存在／可見
---

## Q4 刪除語意（FR6.4）

- **A.** **硬刪**：擁有者 `DELETE` → 204；級聯刪除該 Set 下 Estimate／LineItem／Share／Audit（Advice 列若已存在一併刪或由 U7 約定級聯）
- **B.** 軟刪（`deleted_at`）；清單預設隱藏；無硬刪 API
- **C.** 硬刪批次與明細，但**保留** AuditEvent 列（僅清業務資料）
- **X.** Other (please specify)

[Answer]: A — 硬刪＋級聯（含 Advice 若存在）
---

## Q5 `GET /sets/{id}/advice` 快照誰實作（C2 路徑在 U2 命名空間）

- **A.** U2 提供薄代理：授權後讀 U7 擁有的 Advice 列／狀態；U7 未就緒時回 `advice_status=none` 或 404 短窗（建議，讓 OpenAPI 一次齊）
- **B.** 本 Unit **不實作**該 GET；僅上傳／list／get／delete／shares；advice 整段留給 U7 掛同 path
- **C.** U2 回固定 stub `{status:"none"}`，永不讀 DB
- **X.** Other (please specify)

[Answer]: A — U2 薄代理讀 Advice；未就緒則 none／短窗 404
---

## Q6 RBAC seed（FR7.1–7.2）是否在本 Unit 落地

- **A.** **是**：本 Unit 更新 `C1` 語意註解／權限用途，並移除 `C1h`／`C1r`／`C1o`／`C1b` seed 列；補 allow／deny 測試（team 測試底線 A）（建議）
- **B.** 本 Unit 只做 HTTP／表；seed 變更另開 chore／跟 U8 一起
- **C.** 只改 `C1` 語意、暫留 `C1h` 等列以免舊前端報錯（U3 已拆舊 API，風險較低）
- **X.** Other (please specify)

[Answer]: A — 本 Unit 改 C1 並移除 C1h～C1b；補 allow／deny 測
---

## Consolidated Summary Confirmation

**U2 `estimate-intake-api` 行為定案**

| 項 | 定案 |
|---|---|
| 範圍 | **僅後端**；無 frontend-components（U8／U9） |
| 模組 | `estimate_intake_router`／`service`／access／audit；掛 `/api/cost/v1`（Q1=A） |
| 建議觸發 | POST 持久化成功後同 request enqueue，立即 201（Q2=A） |
| diagram_id | 正整數純標籤；不查圖權限（Q3=A） |
| 刪除 | 硬刪＋級聯（Q4=A） |
| GET advice | U2 薄代理；U7 未就緒 → none／短窗 404（Q5=A） |
| RBAC | 本 Unit 更新 C1、移除 C1h～C1b＋allow／deny 測（Q6=A） |

**將產出**：entities.md、rules.md、functional-spec.md、traceability.json。

**後果**：code-gen 須落地 multipart 上傳、Parse／Validate 協調、表與 ORM、分享覆寫、稽核事件、Background enqueue 介面（U7 實作可後補）、OpenAPI 重產；不得做 SPA。

[Answer]: Looks correct
