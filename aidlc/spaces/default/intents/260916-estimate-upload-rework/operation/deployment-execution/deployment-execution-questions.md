# Deployment Execution Questions — C1 估價上傳改版

> Intent：`260916-estimate-upload-rework` · `deployment-pipeline`／`environment-provisioning` 皆 **SKIP**；沿用既有 staging 管線（ADR-0007）。

## Q1. 是否在本 stage 對 staging 執行完整 redeploy？

A) **否** — 僅記錄既有管線、對現行 `cloud360.danniel.cc` 做健康／煙霧檢查；完整 C1 映像待 worktree 合併進 `ut` 後由 `deploy.yml` 觸發（建議）

B) 是 — 立即 `gh workflow run deploy.yml`（需乾淨已推送 commit）

C) 跳過整個 deployment-execution stage

[Answer]:A

## Q2. 資料庫 schema 遷移策略？

A) 依既有 `schema_rbac.sql`／startup patch；本輪不另開手動 migration（建議）

B) 部署前先手工跑 SQL

[Answer]:A

## Q3. 部署窗口？

A) 非尖峰、可隨時（staging）

B) 需另行排程

[Answer]:A

---

## Consolidated Summary Confirmation

本 stage 決定：不強制 redeploy；對 `https://cloud360.danniel.cc` 做基線健康檢查（根路徑 200）；完整 C1 上線待合併 `ut` 後由 `deploy.yml` 執行。

[Answer]: Looks correct
