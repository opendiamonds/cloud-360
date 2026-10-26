# CI/CD — `U9 memory-purge`

> 本單元的交付物**本身就是兩個 workflow**，故本檔的主體不是「要讓哪些既有閘門綠燈」
> （那只有一小節），而是**這兩個 workflow 自己的形狀**。

## 一、既有管線的機械事實（沿用前站的實測，不重新推導）

`ci.yml` 有 6 個 job；除 `gate` 外的 5 個全部且僅 `needs: gate`，故彼此並行。
`ut` **沒有任何必要狀態檢查**，`main` 只有一個（`Repository contract`）。
故下文所說的「閘門」在合併進 `ut` 這條路徑上是**訊號而非阻擋**
（完整查證見 `construction/membership-service/infrastructure-design/cicd-pipeline.md §一之二`）。

**對本單元的意義**：本單元交付的兩個 workflow **不是 `ci.yml` 的 job**
——它們是獨立的排程 workflow，不進 PR 閘門、不影響任何 PR 的綠紅。

## 二、本單元要讓綠燈的既有閘門（只有兩項）

| # | 閘門 | 本單元的義務 | 漏了會怎樣 |
|---|---|---|---|
| 1 | **`repo-contract`**（`validate_repo_contract.py` ＋ `validate_env_contract.py`） | 本單元宣稱零新部署設定（`NFR8.10`）；且 `schema_rbac.sql` 的 seed 變更須同步 `DEPLOY.md` | CI 紅燈（會被抓到） |
| 2 | **`backend` 的 `unittest`** | 本單元**不新增 Python 程式**，但 `[ND1]`=A 的系統 actor seed 會讓 `users` 多一列——須確認既有測試不因此失敗 | 見 §二之一 |

**本單元不觸發**：OpenAPI drift（零新端點）、前端型別漂移（零前端面）、
`docker-build`（零 image 變更）、`memory-schema` job 的 `P1`–`P14`（零新 schema 物件）。

### 2.1 系統 actor seed 對既有測試的影響：已查證無回歸

| 查證項 | 結果 |
|---|---|
| 既有「最後一位可編輯角色的全域管理員」守門是否會被多出的列影響 | **不會**：`user_router.py` 的 `admin_edit_count` 迴圈過濾 `is_active == True`，而系統 actor 是 `FALSE` |
| e2e 回歸測試的「測試環境只有 admin 一個已核准帳號」假設 | **不受影響**：同上，系統 actor 不被計入 |
| `/api/auth/list` 的 `total` | **會 +1**（`db.query(User).count()` 無過濾）——這是 `OPEN-ND9-1` 的已知後果，非本站新發現 |
| in-memory SQLite 的測試路徑會不會看到這一列 | **不會**：`make_session()` 以 `Base.metadata.create_all()` 建表，**不執行 `schema_rbac.sql` 的 seed**。故既有單元測試完全不受 seed 影響 |

**最後一列是重點**：seed 只存在於 `schema_rbac.sql` 路徑，而既有測試走 `create_all()`
——這意味著**既有測試不會驗證系統 actor 存在**。若清除的稽核 INSERT 要有測試保護，
那個測試必須走真實 PostgreSQL（`memory-schema` job 或 `U19` 新建的 `tests_pg/`）。
記為 `OPEN-ID9-3`。

## 三、清除 workflow 的形狀（`memory-retention-purge.yml`）

| 項目 | 設計 | 理由 |
|---|---|---|
| `runs-on` | `[self-hosted, linux, x64, cloud360]` | `[N1]`=A；`db` 無 host port |
| 觸發 | `on: schedule`（每日 UTC 離峰）＋ `workflow_dispatch` | `FR4.5` 要求自動；手動供驗證與補跑 |
| `permissions` | **`contents: read`**（最小） | 它不需要寫任何東西到 repo |
| `concurrency` | 設一個固定 group 且 `cancel-in-progress: false` | 兩次清除同時跑會爭用同一批列。沿用 `deploy.yml` 的 `cancel-in-progress: false` 形狀（清除中不可被新 run 打斷） |
| `timeout-minutes` | **必須明確設定** | 一個卡住的 `psql` 會佔住自架 runner，而那台 runner 也負責部署 |
| 資料庫存取 | `docker compose exec -T db psql`，身分為 `POSTGRES_USER` | `-T` 必要（該 runner 無 TTY）；身分見 `[ND2]`=A 的更正 |
| SQL 的位置 | 字面存在於 workflow 或版控的 `.sql` 檔 | `NFR7.14`：決定性邏輯放純 Actions 步驟 |
| 失敗行為 | **非零碼結束**，不重試 | 清除冪等且自我收斂（`nfr-design/security-design.md §三之三`） |

### 3.1 三個步驟與兩個交易（承 `nfr-design` 的設計，此處只記 CI 面）

| 步 | 動作 | 交易 |
|---|---|---|
| 1 | 對逾期記憶寫 `purged_by_retention` 稽核列 | **與步 2 同一交易** |
| 2 | 刪除逾期記憶列 | 同上 |
| 3 | 刪除逾期稽核列（`occurred_at < now() - 90 days`） | **獨立交易** |

**CI 面的要求**：步 1＋2 必須在**同一次 `psql` 呼叫**內（以單一 `BEGIN; ... COMMIT;`
或單一 `psql -c` 的隱含交易承載）。**分成兩個 Actions step 會變成兩個連線、兩個交易**
——那會打破 `nfr-design` 定下的交易邊界，而這個錯誤在 YAML 上看起來很自然
（「一個步驟做一件事」）。記為 `code-generation` 的 blocking 檢查項。

### 3.2 `RETURNING *` 禁令（本單元最危險的單字之差）

清除的 SQL **絕不得** `RETURNING *`——只能 `RETURNING id` 或僅取 `row_count`。
`RETURNING *` 會把記憶內容印進**公開可讀**的 Actions log。
詳見 `monitoring-design.md §五之一`。**CI 不會抓這個**。

## 四、監看 workflow 的形狀（`memory-retention-watchdog.yml`，`[ID1]`=A）

| 項目 | 設計 | 理由 |
|---|---|---|
| `runs-on` | **`ubuntu-latest`（GitHub 託管）** | 它必須在自架 runner 離線時仍能執行——這是它存在的全部理由 |
| 觸發 | `on: schedule`（每日）＋ `workflow_dispatch` | — |
| `permissions` | `contents: read`、**`actions: read`**（有先例）、**`issues: write`**（**無先例**） | 見 `monitoring-design.md §二之三` |
| 邏輯 | `gh api` 查清除 workflow 最後一次成功的 run；比對門檻（3 天）；逾期則先查有無同標題前綴的 open issue，無則 `gh issue create` | 純 Actions，不走 LLM 路徑（`NFR7.14` 的同一理由） |
| 認證 | 內建 `GITHUB_TOKEN` | **零新 secret**（`NFR7.12`） |
| 資料庫存取 | **無** | 這是設計的核心：它不碰資料庫，故不依賴那台主機 |
| 失敗行為 | 開 issue；workflow 本身**也**以非零碼結束（使 Actions 清單上同時可見） | 兩個可見面（issue ＋ 紅燈）比一個好，而它們的讀者不同 |

### 4.1 一個容易寫錯的細節：查「成功」而非「最後一次」

`gh api .../runs` 預設回**所有** run，含失敗的。
若只取最新一筆並看它的時間，則「每天都失敗」會被判為新鮮
——**而那正是最需要告警的狀況之一**。

**設計要求**：查詢必須帶 `status=success`（或等價過濾），
且「查不到任何成功 run」須視為**逾期**而非跳過。
記為 `code-generation` 的 blocking 檢查項。

## 五、部署與回滾

| 項目 | 值 |
|---|---|
| 部署方式 | 兩個 workflow 隨 merge 進 `ut` 即生效（workflow 檔不需部署步驟）。**但排程要到檔案進入預設分支後才會排入**——這是 GitHub 的既有行為，寫明以免被誤讀為「merge 後立刻會跑」 |
| `deploy.yml` 的變更 | **零** |
| 回滾 | 還原 workflow 檔即停止排程。**但已執行的清除不可回滾**——刪除的記憶與稽核列無法復原 |

### 5.1 回滾的不對稱：這是本單元唯一真正不可逆的操作

| 情境 | 可否回滾 |
|---|---|
| workflow 檔的變更 | 可（git revert） |
| 系統 actor seed | 可（但見 `OPEN-ND9-1`：刪掉它會讓後續清除的稽核 INSERT 失敗） |
| **已執行的清除** | **不可**。這是 `FR4.5` 的本意（逾期資料就該消失），但它意味著**一個排程設定錯誤會造成不可復原的資料損失** |

**故 `code-generation` 必須以 `workflow_dispatch` ＋ 一個 dry-run 模式先驗證
選取條件**（只 `SELECT count(*)`、不 DELETE），再啟用排程。
記為 `OPEN-ID9-4`——它不是測試建議，是**不可逆操作的前置驗證**。

## 六、`tcms-test-cases` 的前置提醒（blocking，但不在本站）

`project.md ## Mandated` 要求每個 intent 的 construction 必經 `tcms-test-cases`
並完成四項產出，**未完成不得進入部署階段**。本站只記前置與分桶**預判**：

| 桶 | 本單元的項目 |
|---|---|
| 待自動化 | 選取條件的正確性（哪些列該被選到）；稽核 INSERT 的五個事實；seed 的可重跑性。三者都需要**真實 PostgreSQL**（`OPEN-ID9-3`） |
| **只能手動** | **監看者的端到端行為**——驗證它會在清除漏跑時真的開 issue，需要製造「清除連續 3 天未成功」的狀態，而那在 CI 中無法合成 |
| 已自動化 | 0 |

**該 stage 至今未對本 intent 的任何單元執行過**，而它是 blocking。
