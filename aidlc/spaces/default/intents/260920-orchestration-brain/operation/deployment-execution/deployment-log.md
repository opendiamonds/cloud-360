# 部署紀錄（PR #650 → `ut` → staging）

時間皆為 UTC，取自 GitHub Actions run 的 `createdAt`／`updatedAt`。

## 時間軸

| 時間 | 事件 | 證據 |
|---|---|---|
| 2026-11-14 | 本機演練：模擬 staging 現況（`postgres:16-alpine` 加上 `ut` 現行 schema）→ dump → 在新 volume 起 PG 18 並還原 → `REINDEX` → 兩支遷移 → 後端 `init_db()` 與成員回填，全部通過；舊 volume 仍可用 PG 16 啟動 | 本 intent 的 build-and-test 紀錄；`DEPLOY.md` §5.4 第三條硬條件 |
| 同上 | 演練中發現部署 compose 的 PG 18 掛載路徑錯誤：PG 18 映像拒絕掛在 `/var/lib/postgresql/data` 的 volume，連空 volume 也一樣。已修正並推上 PR #650 | commit `2bab8fa` |
| 同上 | 使用者建立 `MEMORY_DB_PASSWORD`，以 `gh api` 只列名稱查證存在於 secrets、不在 variables | — |
| 15:42:23 | 推送一次性分支 `danniel/chore/pg18-upgrade-run`，在 staging runner 執行升版與兩支遷移 | run 43611607694 |
| 15:42:35 | 預檢：DBSIZE 66,476,657 bytes；Docker 根目錄可用空間遠高於需求 | 同上 |
| 15:42:37 | 停 backend；dump 1,027,881 bytes，權限 600；隨後停掉舊資料庫（**網站開始停機**） | 同上 |
| 15:42:57 | PG 18 還原完成並 `REINDEX`：`users=4 diagrams=4` | 同上 |
| 15:44:21 | `run_hierarchy_migration.py` 結束碼 0：處理 2 位使用者，建立 2 組預設專案／系統 | 同上 |
| 15:44:32 | `run_meta_schema_migration.py` 結束碼 0；收掉臨時容器，新 volume `cloud360_db_pg18` 保留 | 同上 |
| 15:45:24 | PR #650 轉為 ready，以 merge commit 合併進 `ut`（`186f3a6`） | `gh pr view 650` |
| 15:45:27–15:49:06 | `deploy.yml` 執行成功，`rollback` job 未觸發（skipped）。last-good 記為 `186f3a6`（**網站恢復**） | run 43611880032 |
| 15:45:29–15:49:3x | 第二個 deploy run 由另一個 PR（`danniel/fix/postgres-driver-psycopg3`，#669）的 `closed` 事件觸發。該 PR 的 commit 已包含在 #650 中，GitHub 也把它算成已合併。這個 run 用的是該 PR 自己的舊版 `deploy.yml`，沒有傳入 `MEMORY_DB_PASSWORD`，在 `render-env.sh` 產生設定檔時就失敗，**沒有碰到任何容器**。它觸發的 rollback 用的是同一份舊 workflow，同樣在產生設定檔時失敗；自動 revert #669 時遇到衝突而沒有開出 revert PR；最後把失敗交給 Deploy Doctor | run 43611882868；Deploy Doctor run 43612250696 |

## 結果

- staging 目前執行的是 `186f3a6`，也就是 `ut` 的 HEAD，即第一次成功部署的版本。
- 第二個 run 是**誤報**：它失敗的原因是舊 workflow 少了新的 secret 對應，不是本次發佈的程式或資料有問題。Deploy Doctor 若提出任何修改或 revert 的建議，都不應採納。
- 實際停機時間約 7 分鐘（15:42:37 到 15:49:06）。

## 保留中的回退資源（`DEPLOY.md` §5.8）

- 舊 volume：`cloud360_cloud360_db`（PG 16）。
- dump：staging runner 帳號的 `$HOME/cloud360-upgrade/cloud360-dump-*.sql`（權限 600）。
- 建議驗證通過後保留約 7 天再刪除，並記錄刪除時間。

## 待收尾

- 一次性分支 `danniel/chore/pg18-upgrade-run` 不合併，驗證完成後刪除。
- 使用者在 TCMS 把案例 id 27、28 設為停用。
