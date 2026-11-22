# Deployment Execution — 問題檔

> stage 檔要求的四題，答案都是本次部署前置的實際執行結果，附可查證的來源。不另外向使用者重問。執行方式（由 staging runner 代跑升版，成功後直接合併）由使用者於 2026-11-14 以選單選定「執行，成功後就合併」。

### Q1 — 部署前的檢查都通過了嗎？

- A. 是：PR #650 head `2bab8fa` 共 53 項檢查通過、1 項 skipped；`mergeable=MERGEABLE`、`state=CLEAN`；`MEMORY_DB_PASSWORD` 已在 repo secrets 且不在 variables
- B. 否

[Answer]: A <!-- 來源：`gh pr checks 650`、`gh pr view 650 --json mergeable,mergeStateStatus`、`gh api .../actions/secrets` 與 `/variables`（只列名稱），2026-11-14 -->

### Q2 — 需要資料庫遷移嗎？有測過嗎？

- A. 需要，而且合併前已在 staging 執行並通過：PG 16 → 18 dump／restore、`REINDEX`、`run_hierarchy_migration.py`、`run_meta_schema_migration.py`。之前已在本機以同樣的指令演練過
- B. 不需要

[Answer]: A <!-- 來源：workflow run 43611607694（分支 `danniel/chore/pg18-upgrade-run`，全部步驟 success）；本機演練紀錄見 DEPLOY.md §5.4 第三條硬條件 -->

### Q3 — 相依服務都可用且健康嗎？

- A. 是：部署 job 的 Redis ACL、Ollama 模型、資料面探測、tunnel、session 存活、大腦 WS 等驗證步驟全部 success
- B. 否

[Answer]: A <!-- 來源：deploy run 43611880032 的各步驟結果 -->

### Q4 — 部署窗口？

- A. 2026-11-14 15:42–15:49 UTC：15:42:23 開始升版、舊資料庫停止，15:49:06 部署完成（約 7 分鐘停機）
- B. 其他

[Answer]: A <!-- 來源：run 43611607694 與 43611880032 的 createdAt／updatedAt -->
