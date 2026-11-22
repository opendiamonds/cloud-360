# CI/CD Pipeline — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T23:44:13Z（`date -u` 取值）。
>
> 本單元對管線定義（`ci.yml`、`deploy.yml`、`ui-regression.lock.yml`、`package.json` scripts）的改動是 **0 行**，
> 但有三件事會被既有閘門強制要求、一件事**沒有任何閘門**會發現：部署後必須人工重跑遷移腳本建索引。
> 本檔把四者寫成下游可複驗的形式，並逐道判定既有閘門對本單元各失敗路徑有效與否。
> 本站未執行任何 CI 步驟或測試；判定皆依 workflow 原文與行號。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-design/logical-components.md` | §一 改動清單（四支新測試檔、15 處既有測試呼叫補參數、`openapi.json`／`api.d.ts` 重產）；§三 索引九項落點與完成條件 |
| `../nfr-design/security-design.md` | §二之五 突變 `G1`–`G7`、§三 `M1`–`M6`、§五之三 `[PPD1]` 的 `assertLogs` 測法 |
| `../nfr-design/performance-design.md` | §一之四 前端扇出的 e2e 測法、§二之二 語句計數測試 |
| `../functional-design/functional-spec.md` | §二之一（`openapi.json` 只漂移 description）、§八之一 第 1、6 項 |
| `../carried-review-items.md` | nfr-requirements `R-02` 使用者裁決（部署後重跑遷移腳本、不動啟動路徑） |
| `inception/contract-design/contract-summary.md` | `K-19`（`U17 a11y-gate` 會掃本單元三頁） |
| `inception/delivery-planning/bolt-plan.md` | `B13`（`:659`）、`B11`（`:572`）、`U17` 在 `B8` 而依賴 `U23`（`:479`） |

## 一、CI 閘門逐道影響

`ci.yml` 除 `gate` 外的每個 job 都只 `needs: gate`，故**並行**執行（`ci.yml:559` 的註解逐字）。

| Job／步驟 | 位置 | 對本單元的影響 | 本單元要做的事 |
|---|---|---|---|
| `repo-contract`：`validate_repo_contract.py`、`validate_env_contract.py` 等五支 | `ci.yml:141-176` | 無新必要檔、無新環境變數、無禁止路徑（新檔名不含 `prod`／`production`／`secrets` path part） | commit 前照 `project.md` 本機跑兩支 validator |
| `frontend`：`npm run lint` | `:197-198` | 新檔（三頁、`fanoutQueue.ts`）受 16 條 error 級 hook 規則約束；資料抓取須「純抓取函式 ＋ `.then` 更新 state ＋ `cancelled` flag」形狀（`team.md`） | 沿用既有形狀 |
| `frontend`：**API type contract drift**（`npm run check:types` → `node scripts/check-api-types.mjs`） | `:206-207`；`package.json:13` | 由 committed `openapi.json` 重產型別並與 committed `api.d.ts` 比對。重 dump 了 `openapi.json` 卻沒重產型別 → **紅** | 跑 `npm run gen:types`（`package.json:12`：`openapi-typescript ../openapi.json -o src/types/api.d.ts`）並 commit |
| `frontend`：WS contract type drift | `:218-219` | 不受影響：本單元零 WebSocket 變更 | — |
| `frontend`：`npm run build`（`tsc -b && vite build`） | `:222` | 新頁面的型別檢查 | — |
| `backend`：Import FastAPI app | `:269` | router 改委派 `MembershipFacade`；匯入錯誤會在此紅 | — |
| `backend`：**OpenAPI spec drift**（`python scripts/dump_openapi.py --check`） | `:286-294` | 兩支列舉 handler 的 docstring 改寫（`BR87.4`）→ operation `description` 變動 → 未重 dump 則**紅**。路徑、回應模型、狀態碼不變 | 改完 docstring 後重 dump `openapi.json` 並 commit；**順序必須是先 dump、再 `gen:types`** |
| `backend`：WS contract spec drift | `:304` | 不受影響 | — |
| `backend`：MCP tool spec drift（`gen_mcp_tools.py --check`） | `:313` | **不受影響**：allowlist 只含三條 `/api/requirements/*`（`backend/mcp_bridge/allowlist.json:7`／`:25`／`:36`），且產生器去掉 description（`generator.py:282`）。hierarchy 的 description 漂移不會讓它紅 | — |
| `backend`：Run unit tests（`python -m unittest discover -s tests -v`） | `:317-320` | 四支新測試檔放進 `backend/tests/` 即被撿到（`PPN-23`）；三個寫入方法的 `project_visible` 必填無預設，既有 15 處呼叫若漏補 → `TypeError` → **紅**（fail-closed） | 15 處補關鍵字參數（斷言不動） |
| `memory-schema`（真實 PostgreSQL） | `:322` 起 | ① 連套兩次 `schema_rbac.sql`（`:359-374`）→ 新 `CREATE INDEX IF NOT EXISTS` 的語法與可重跑性在真實 PG 上被驗；② P1–P12（`verify_meta_schema.sql`）對 `project_members` 只查欄位、外鍵與 CASCADE，不查索引集合，不受影響；③ U20 步驟 B 執行遷移腳本（`:435-447`），其後條件逐筆查 `EXPECTED_INDEXES` → 新增的那一筆在真實 PG 上被驗 | 見 §四 第 6、7 列 |
| `concurrency` | `:545` 起 | 不受影響 | — |
| `docker-build` | `:628` 起 | 不受影響（Dockerfile 不改） | — |
| **`ui-regression`**（gh-aw，Playwright e2e） | `ui-regression.lock.yml:558` 裸 `npx playwright test`；`frontend/playwright.config.ts:10` `testDir: './tests/e2e'` | 新 spec 丟進 `frontend/tests/e2e/` 即被撿到，管線零改動；`post-steps` 讀 `.stats.unexpected`，非 0 即失敗（`:1061`）。此 stack 屬全新資料庫（測試 compose `:57` 以 initdb 執行 `schema_rbac.sql`），索引自動存在 | `functional-spec.md` §八之一 第 6 項的 e2e；`RecentChanges` 逐字文案的斷言（`logical-components.md` §一之二） |

**這些紅燈是訊號，不是合併閘門**：`ut` 上沒有任何必要狀態檢查（`ci.yml:413-414`、`:557-562` 逐字，承 `OPEN-ID19-6`），
任一 job 紅燈都**不會擋住合併**。上表的「會紅」意思是「會被看見」，前提是合併者在合併前看了檢查結果。

### 一之一、本機產生順序（三步，順序不可換）

1. 改兩支 handler 的 docstring → `cd backend && python scripts/dump_openapi.py`（重寫 `openapi.json`）。
2. `cd frontend && npm run gen:types`（由**新的** `openapi.json` 重產 `src/types/api.d.ts`）。
3. 兩檔同一個 commit。先跑 2 再跑 1，`check:types` 比對的是舊 spec 產的型別，CI 照樣紅。

### 一之二、e2e 名稱穩定性（硬約束）

`ui-regression.lock.yml:568` 的 Kiwi 回報步驟逐字註解：`--summary-template '${name}'` 是 plugin 重用案例的鍵，
「changing it orphans the old cases」。本單元新 e2e 的 `describe › test` 字串在 code-generation 落地後即固定，
`tcms-test-cases` 站只做同步、不改名。

## 二、部署步驟

| # | 步驟 | 誰做 | 說明 |
|---|---|---|---|
| 1 | PR 合併進 `ut` | 人 | `deploy.yml` 於 PR closed（merge）觸發，跑在自架 runner，`concurrency: deploy-10-10`、不可中斷 |
| 2 | `render-env.sh` 產生 `deploy/.env` → `docker compose ... up -d --build --remove-orphans` | `deploy.yml:124`、`:129` | 本單元零新變數，此步不需任何改動。重建容器屬原地替換（非 blue-green），沿用既有的短暫中斷 |
| 3 | 冒煙：frontend `/`（`:135`）、`/api/auth/login` 預期 401（`:335-345`）、公開網址 `/`（`:362`） | `deploy.yml` | **不碰 `/api/hierarchy/*`**——專案頁壞掉不會讓部署失敗（`monitoring-design.md` §五） |
| 4 | 記錄 last-good（`:570-575`） | `deploy.yml` | — |
| 5 | **部署後人工：重跑遷移腳本** | **人**（staging 維運者） | `deploy.yml` 不呼叫任何遷移腳本（`grep` 0 命中；`DEPLOY.md:691`）。照 `DEPLOY.md` 2.2.9（`:660`）：`cd backend && python scripts/run_meta_schema_migration.py; echo "exit=$?"`，必須為 0。腳本只執行 `X`／`I`／`J` 三區塊、單一交易、`IF NOT EXISTS`，重跑安全 |
| 6 | **驗證** | 人 | `psql "$DATABASE_URL" -c "SELECT indexname FROM pg_indexes WHERE tablename='project_members' AND indexname='ix_project_members_user_id';"` → 應回 **1 列**（`logical-components.md` §三 #8 的同一條指令）。選擇性：對專案清單的可見集合查詢 `EXPLAIN`，成員半邊應出現 `ix_project_members_user_id` |

**不得以「重跑整支 `schema_rbac.sql`」取代第 5 步**：該檔 `C) RBAC` 區塊開頭的 `DELETE FROM role_permissions;` 會清掉
經 Admin UI 調整過的權限矩陣（`DEPLOY.md:988` 的明文更正）。遷移腳本只跑 `X`／`I`／`J`，不含 `C)`。

**遺漏第 5 步的後果與偵測**：

| 面向 | 內容 |
|---|---|
| 後果 | 功能完全正常；專案清單的成員半邊以循序掃描取代索引，`project_members` 列數小時差異不可感知，隨成員數成長才變慢。**無聲失敗**：沒有錯誤、沒有 log |
| 什麼不會發現 | `test_M3` 只比對檔案內的 DDL 與 ORM，不碰 staging；`memory-schema` job 跑的是 CI 的臨時 PG；部署冒煙不碰 hierarchy；無 metrics、無告警 |
| 唯一的偵測方式 | 第 6 步的人工查詢。建議 `tcms-test-cases` 站把它列入「只能手動」桶（`logical-components.md` §三 末段已列為手動桶候選） |
| 適用情形 | 依 `infrastructure-specification.md` §二之一：staging 在 `B11` 與 `B13` 分批合併時屬 (c) 類、必須跑；同批合併時 `create_all` 會連同索引建表，但 `DEPLOY.md` 2.2.9 對 `U18` 新表本來就要求跑一次，故第 5 步在兩種情形下都執行 |

## 三、合併順序約束

| # | 約束 | 性質 | 不遵守的後果 |
|---|---|---|---|
| 1 | docstring 改寫、`openapi.json`、`api.d.ts` **同一個 PR** | 技術（CI 漂移閘門） | OpenAPI drift 或 check:types 紅 |
| 2 | `schema_rbac.sql` 的 `CREATE INDEX`、`models.py` 的 `Index`、`test_M3` 的點名斷言 **同一個 PR** | 技術（`test_M3` 要求 ORM 與 DDL 索引名集合相等） | unittest 紅 |
| 3 | `EXPECTED_INDEXES` 與 `BLOCK_SENTINELS["J"]` 與上一列**同一個 PR**，`DEPLOY.md` 的步驟與計數（7 → 9）亦同 | 技術 ＋ blocking 規則（`project.md` schema ↔ deploy 同步） | 只加 SQL 不加 `EXPECTED_INDEXES`：**沒有任何閘門會紅**（見 §四 第 7 列）；只加 `EXPECTED_INDEXES` 不加 SQL：`memory-schema` 步驟 B 回滾並紅 |
| 4 | 三個寫入方法的簽章變更與 15 處既有測試呼叫、3 處 router 呼叫 **同一個 PR** | 技術（必填參數） | unittest `TypeError` 紅；若只改 router 不改測試亦同 |
| 5 | `U23` 晚於 `U19`（`B11`）上線 | 技術依賴（`MembershipFacade` 新方法寫在 `U19` 的模組、讀 `project_members`） | 表不存在 → 專案清單 500 |
| 6 | `B13` 內順序 `U20` → `U23` → `U21` | 依 `bolt-plan.md:659-660` | 需求籤的消費端（`K-17`）先於提供端 |
| 7 | `U17 a11y-gate`（`B8`）的掃描範圍會擴到本單元三頁（`K-19`），而執行順序上 `B13` 先於 `B8`（`bolt-plan.md` 的交錯序列） | 技術依賴，已由執行順序滿足 | 路由（`/projects`、`/projects/new`、`/projects/:projectId`）落地後不宜再改，否則 `U17` 的掃描標的要跟著改 |

**`delivery-planning:c6`（破壞性契約變更與消費端不得分批）不適用**的論證：(1) 觸發條件是**既有端點回應形狀**變更；
(2) 兩支列舉端點的路徑、`response_model`、狀態碼不變（`functional-spec.md` §二之一），變的是可見集合的語意（放寬）
與 description；三個寫入方法的簽章變更是**Python 內部 API**，不是 HTTP 契約；(3) 要防的失敗模式「舊消費端讀到新形狀而壞」
在此不存在——既有前端消費端讀到的仍是同一形狀，只是多看到被邀請的專案；(4) 反方向（前端先於後端）已被第 5 列的依賴擋住。
本站判定不適用，並提交核可關卡採納。

## 四、各失敗路徑由哪一道閘門抓（stage → gate 對照）

| # | 失敗路徑 | 抓得到的閘門 | 判定 |
|---|---|---|---|
| 1 | 改了 docstring 沒重 dump `openapi.json` | backend OpenAPI spec drift | ✅ |
| 2 | 重 dump 了沒重產 `api.d.ts` | frontend check:types | ✅ |
| 3 | 某處呼叫漏傳 `project_visible` | unittest（`TypeError`）＋ `security-design.md` §二之四 ast 靜態鎖 | ✅ |
| 4 | 守門順序錯（晚於 409、晚於 K2）或訊息仍帶 id | unittest（`security-design.md` §二之三 (e)(f)、§一之三 逐位元比較）＋ 突變 `G1`–`G7` | ✅（前提：突變驗證確實執行） |
| 5 | 可見性謂詞漏寫 `project_id` 關聯 | unittest（§三 的 ③、`M5`／`M6`） | ✅ |
| 6 | `CREATE INDEX` 寫成 `ON public.project_members` 或漏寫 | unittest `test_M3`（`ddl_indexes` 正規式，`test_membership_data.py:74-80`）；漏寫時 `memory-schema` 步驟 B 亦紅（`EXPECTED_INDEXES` 已列） | ✅ |
| 7 | **SQL 有索引、`EXPECTED_INDEXES` 漏列** | **無**：`test_M3` 不讀遷移腳本（`backend/tests/` 對 `EXPECTED_INDEXES` 0 命中）；步驟 B 只驗「列出者存在」，未列出者不驗 | ❌ → §四之一 補強 |
| 8 | `BLOCK_SENTINELS["J"]` 漏加 | 無；它只保護「未來有人把 DDL 移出 `J)` 區塊」，漏加的當下不壞任何東西 | ⚠️ 接受，以 code-summary 的 grep 完成條件涵蓋 |
| 9 | `DEPLOY.md` 未更新步驟或計數 | 無（`repo-contract` 不檢查 `DEPLOY.md` 內容） | ⚠️ 以 `logical-components.md` §三 的 `grep -c` 完成條件涵蓋 |
| 10 | staging 部署後沒跑遷移腳本 | 無 | ❌ 只能人工（§二 第 6 步） |
| 11 | 前端扇出退化為全發或截斷 | `ui-regression`（`performance-design.md` §一之四 的在途數斷言） | ✅ |
| 12 | `[PPD1]` 的 actor log 被拿掉 | unittest 的 `assertLogs`（`security-design.md` §五之三） | ✅ |
| 13 | 專案頁在 staging 壞掉 | 部署冒煙不碰 hierarchy | ❌ 已知，記入 `monitoring-design.md` §五 |

### 四之一、本站新增的補強（第 7 列）

在 code-generation 新增一條單元測試斷言：以**讀檔文字**（不 import，避免帶入 psycopg 依賴）確認
`backend/scripts/run_meta_schema_migration.py` 的 `EXPECTED_INDEXES` 區塊含 `"ix_project_members_user_id"`，
並把它放在 `test_M3` 旁。突變：從 `EXPECTED_INDEXES` 刪掉該列 → 紅。成本是一個 `assertIn`；它關閉的是
`run_meta_schema_migration.py:161-165` 的既有註解逐字警告的那個形狀（「只加 SQL 而不加這一列的後果是索引被建立但不被驗證」）。
這是本站的設計補強、不是上游定案；code-generation 採用或於 code-summary 記明拒絕理由，並於核可關卡揭露。

## 五、回滾

| 面向 | 內容 |
|---|---|
| 自動 | 部署失敗時 `rollback` job（`deploy.yml:596` 起）還原 last-good、開 revert PR、dispatch Deploy Doctor。本單元不改此 job |
| 手動 | `git revert` 本單元的合併 commit 即完整回滾程式；**索引不需處理**（`infrastructure-specification.md` §二之二） |
| 安全面代價 | 回滾使三條寫入路徑的守門消失，被移出的建立者重新取得 API 層寫入能力（`OPEN-PP23-10` 重開）。這不是阻擋回滾的理由，而是回滾時須知情的事實 |
| 資料 | 無資料遷移，無需反向遷移 |

## 六、CI/CD 中的 secrets

零新增。既有 secret（`POSTGRES_PASSWORD`、`JWT_SECRET`、`ui-regression` 的 Kiwi 帳密等）的用法不變；
`deploy.yml` 部署後清理 `deploy/.env` 的既有行為不變。CI 中的 `JWT_SECRET: ci_only_not_a_real_secret`（`ci.yml:293`、`:319` 等）
為既有的非機密佔位值。
