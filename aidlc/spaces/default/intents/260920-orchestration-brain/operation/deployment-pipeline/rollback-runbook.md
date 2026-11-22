# 發佈與回滾 runbook（PR #650）

> 本次發佈採用的升版窗口回滾處置：**B**（維持現況、出事時走本檔的手動回滾），使用者於 2026-11-14 選定，依 `DEPLOY.md` §5.4 排序不變量 2 記錄於此。
> 細節以 `DEPLOY.md` 為正本，本檔只排定順序、標明誰做，並列出驗證方式。指令中的 secret 一律不寫值。

## 一、合併前（使用者執行，順序不可對調）

**排序不變量**：先做資料轉換，再合併觸發自動部署。反過來做會**靜默成功**：首頁正常，但資料庫起不來（`DEPLOY.md` §5.4）。

| # | 步驟 | 誰 | 依據 | 完成判準 |
|---|---|---|---|---|
| 1 | 建立 GitHub secret `MEMORY_DB_PASSWORD`。在你自己的終端執行 `gh secret set MEMORY_DB_PASSWORD`，值用 `openssl rand -hex 32` 產生，不得含 `$` | 使用者 | `DEPLOY.md` 記憶專用角色段、§5.10 | `gh api repos/opendiamonds/cloud-360/actions/secrets --jq '.secrets[].name'` 有它，`.../actions/variables` 沒有 |
| 2 | 先過 `DEPLOY.md` §5.5 的磁碟門檻與 §5.6 的記憶體處置 | 使用者 | §5.5、§5.6 | 每個掛載點都在門檻內 |
| 3 | PG 16 → 18 升版，照 §5.4 的七步：量大小 → 停 backend → dump → 以新 volume 起 PG 18（不掛 initdb）→ restore 並 `REINDEX DATABASE cloud360;` → 啟 backend 並跑 §5.7 探測 → 保留舊 volume 與 dump | 使用者 | §5.3、§5.4、§5.7 | §5.7 探測回 401 才算通 |
| 4 | 在部署主機、以本分支的程式碼、`DATABASE_URL` 指向升級後的資料庫，依序執行 `cd backend && python scripts/run_hierarchy_migration.py`，再執行 `python scripts/run_meta_schema_migration.py` | 使用者 | §2.2.7、§2.2.9（「必須在含本變更的那次部署之前跑」） | 兩支結束碼皆 0；後者的後條件包含角色存在、對 `memory` 有 `USAGE`、讀不到 `public.users` |
| 5 | （選做）`python scripts/backfill_project_members.py --dry-run` 預覽成員回填。正式回填會在後端啟動時自動進行 | 使用者 | §2.2.10 | 預覽數字合理 |
| 6 | 告訴 conductor 前置已完成 | 使用者 | — | — |

## 二、合併（conductor 執行，需使用者明確同意）

1. 以 `gh api` 只列名稱，確認 `MEMORY_DB_PASSWORD` 存在且只在 secrets。
2. 推送本機尚未推送的 commit，確認 PR #650 檢查全綠。
3. PR #650 由 draft 轉為 ready，合併進 `ut`。一般 PR 用 merge commit（`team.md` Q2）。
4. 監看 `deploy.yml` 的 run 直到結束。

## 三、合併後驗證

| 檢查 | 方式 | 通過條件 |
|---|---|---|
| 部署 workflow | `gh run view <deploy run>` | `deploy` job 成功，`rollback` job 沒有執行 |
| 公開網址 | 開 `https://cloud360.danniel.cc` | 登入頁正常 |
| 大腦 WS | 入口頁送一句話 | 有回覆；部署 job 的 WS 子協定步驟已綠 |
| 記憶專用角色 | 我的記憶頁 | 正常載入，不回 503 |
| 手動測案 | TCMS 計畫「260920 大腦入口：真實模型路徑（手動）」與「本機與部署環境（手動）」 | MT-01～MT-07 依通過條件判定，結果記入 TCMS |
| 收尾 | `DEPLOY.md` §5.8 | 驗證通過後才刪除舊 volume 與 dump，並記錄 |

## 四、出事時

### 4.1 部署 job 失敗、自動回滾已觸發（升版窗口內）

處置 B 下會出現的狀態：`rollback` job 取出 last-good commit（PG 16 映像），重建時對著已升級為 PG 18 的 volume，postgres 拒絕啟動。**資料不會遺失**：舊 volume 與 dump 都還在（§5.4 步 7）。

1. 先看 `deploy` job 是哪一步失敗。常見原因：缺 secret、遷移沒跑導致「role cloud360_memory does not exist」、探測失敗。
2. 能就地修正前置（例如補 secret、補跑遷移）時：修正後以 `workflow_dispatch` 對 `ut` 重新部署。自動開出的 revert PR **不要合併**。
3. 要回到升版前的狀態時：照 §5.4 把 compose 指回**舊 volume** 並用 PG 16 映像啟動。也就是 last-good 的程式碼對上舊資料，兩者相容。
4. 回到可運作狀態後，記錄這次失敗與處置。

### 4.2 部署成功，但功能有問題

1. **只回程式碼**：合併 `rollback` job 開的 revert PR，或另開 revert PR 合併進 `ut`。注意：回到舊程式碼時，資料庫仍是 PG 18 與新 schema，舊程式碼的映像是 PG 16，兩者**不相容**。所以在升版窗口結束前，程式回滾一律要連同 4.1 第 3 步的資料回滾一起做。
2. **只回資料**：沒有這條路。新 schema 只增不減，舊資料可由升版前的 dump 還原。

### 4.3 不會自動處理的事

- `rollback` job 不還原 PGDATA，也不還原 `memory`／`projects` 等新表的內容。
- 沒有機械檢查「回滾取出的 commit，其映像主版本是否與目前 PGDATA 相容」（§5.4 不變量 3）。
