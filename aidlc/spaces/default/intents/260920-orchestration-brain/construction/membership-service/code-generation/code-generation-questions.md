# Code Generation 問題檔 — `U19 membership-service`

本站只有一個關卡：Plan Approval。本單元的全部設計決定已在上游定案
（`[FD1]`／`[FD2]`／`[FD3]`／`[N1]`／`[N2]`／`[N3]`／`[ND1]`／`[ID1]` 八題），
故本站不新增設計問題。

## Plan Approval

核可對象為三份內容，三者**一併**核可：

1. `code-generation-plan.md` — 14 個步驟、61 個勾選項，依 Testing Contract 的
   `plan_profile.steps` 排序（**test-after**：先實作該層、再寫並跑該層的測試）。
2. 該計畫內嵌的 `## Testing Contract` JSON 區塊
   （`contract_sha256: sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77`）。
3. `unit-test-instructions.md` — 四個測試檔、26 個測試、兩條本單元專屬執行指令、
   五項突變驗證。

**計畫摘要**

| Step | 內容 |
|---|---|
| 1–2 | 例外型別與值物件骨架；驗證測試執行器並記錄本單元專屬指令 |
| 3–4 | 兩個 ORM model ＋ `cause` 欄回補 `U18` 的 DDL；ORM↔DDL 一致性測試（**含欄位名以外的三項**） |
| 5–6 | 資料存取（判定查詢、守門謂詞、聚合查詢、取鎖輔助）；等價測試 |
| 7–8 | `MembershipFacade` 七個方法、`select_successor` 純函式、自動改選、稽核與結構化 log；**PBT（blocking）** |
| 9–10 | `membership_router`、既有停用端點擴充（顯式 409）、`create_project_with_owner`、兩道漂移閘門；allow/deny 雙向 `TestClient` |
| 11 | 前端行為：**不適用**（成員頁是 `U24`；`frontend/src` 對 `projects` 命中數為 0） |
| 12 | 既有專案的回填腳本（獨立、冪等、自我終檢、非零碼） |
| 13 | 新 `concurrency` CI job ＋ 新測試根 `backend/tests_pg/` ＋ 三條併發斷言 |
| 14 | `DEPLOY.md §2.2.10`、`LOCAL-DEV.md`、`source-manifest.json`、`traceability.json`、`code-summary.md` |

**三件「違反後 CI 全綠」的事，各有對應步驟**

| # | 靜默失敗面 | 落點 |
|---|---|---|
| 1 | 漏宣告 409（FastAPI 不從 `raise HTTPException` 推導狀態碼） | Step 9d ＋ Step 10 |
| 2 | ORM 與 DDL 的約束／索引不一致（既有 `T25` 只比對欄位名） | Step 3 ＋ Step 4 |
| 3 | 併發守門被繞過（`with_for_update()` 在 SQLite 被**靜默丟棄**） | Step 13 |

**本計畫承接的 blocking 前置**

- **`OPEN-ND19-5`**：`U7` 的 `hierarchy_service.create_project`（`:98`）在 `:118`
  **自己 `db.commit()`**，故 `[ND1]`=A 的天真實作是兩個交易、失敗時留下零成員專案
  ——正是它要消除的狀態。處置在 Step 9a：交易邊界歸 `U19`，`U7` 的 service 層
  新增一個**不 commit 的變體**。**這會改到 `U7` 已交付的程式。**
- **`OPEN-ID19-2`**：回填與第一個消費端之間是**手動步驟邊**，不是依賴圖上的邊。
  處置在 Step 12 ＋ Step 14a，並交接 `delivery-planning`。

**`infrastructure-design` 的兩項 Minor 仍開放（本計畫不改那兩份凍結的檔案）**

`R-01`（「本站實查」用於尚未落地的 `assert_can_deactivate`）與
`R-02`（「覆蓋面不可能靜默消失」缺首次限定詞）。該 stage 只有一輪審查額度，
引擎逐字回覆「include the findings in the approval summary for the human」。
兩項皆為用詞精確度、不影響結論；就地編輯會使該 stage 的 READY 收據失效
而無額度可補，故隨本關卡呈現並記入 `code-summary.md`。

[Approval Fingerprint]: sha256:v3:eddb6e141582d6fe2751cd34d1bb80dfee2a2c5449ae458f1f404daa8e55c6da
[Planned Source]: 3b2c25dfabb67aa7e707b39e87cc29e75373dcb785ffc99987f1a7c7702ebbad

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
