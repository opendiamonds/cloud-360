# Code Generation 問題檔 — `U23 project-pages-ui`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（15 步，含其內嵌的 Testing Contract，`test-after`、`standard`）與 `unit-test-instructions.md`。明白揭露：

- **後端行為變更（U7）**：專案／系統清單改為「擁有者（僅零成員列時）∪ 成員」可見（PP1=A、PP3=A）；建立系統、刪除專案、刪除系統三條寫入路徑加可見性守門（被移出的建立者回 404）；既有 404 訊息改為不含 id 的固定訊息（狀態碼不變）；刪除成功多記刪除者使用者編號（PPD1=A）。
- **連帶刪除仍存在**：仍是成員的擁有者刪專案會清掉全部成員列、刪系統會清掉該系統所有需求欄位值，本單元不改。
- **schema 變更**：新增索引 `ix_project_members_user_id`（PPN1=A），同步 `schema_rbac.sql`、遷移腳本 `EXPECTED_INDEXES`（8→9）、`DEPLOY.md`（原「7 個索引」已錯，改 9）；`LOCAL-DEV.md` 不觸發。
- **部署後人工步驟**：合併後須在 staging 容器內重跑遷移腳本並以 `docker exec` 的 psql 驗證索引；漏跑不報錯，只是清單查詢變慢。
- **契約漂移**：`openapi.json` 兩支 operation 的 description 會變（PP1 選項原稱不漂移），需重 dump 並重產 `api.d.ts`。
- **跨單元測試檔**：U7、U12、U20、U21 的 4 支測試檔共 15 處補 `project_visible=ALWAYS_VISIBLE`，不改任何斷言。
- **帶入項**：`carried-review-items.md` 的 20 項（5＋6＋4＋5）全數對應到計畫步驟，0 項拒絕。
- **未處理的開放項**（會在核可後另行提交是否另開 intent）：`OPEN-PP23-1`、`OPEN-PP23-3`、`OPEN-PP23-4`、`OPEN-PP23-6` 第 ③ 項。

## Plan Approval

[Approval Fingerprint]: sha256:v3:e2095e17f74d91bed62d0734ac3b15c6934fc8e6208a1144ca567d4ae4b38b2c
[Planned Source]: d9e485915eca2f5ed77cc073676ff6087cb8b88a35acfb1d4b93059d47209fad
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan
