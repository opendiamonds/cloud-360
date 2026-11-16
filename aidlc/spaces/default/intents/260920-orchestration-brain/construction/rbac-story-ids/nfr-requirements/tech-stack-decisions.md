# Tech Stack Decisions — `U3 rbac-story-ids`（`spec`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: rbac-story-ids · kind: spec -->

## 一、結論：零新技術

本單元**不引入任何語言、框架、資料庫、服務、容器或套件**。它改的是既有
`role_permissions` 矩陣的預設值（308 → 352 列）與兩處既有程式的行為。

| 面向 | 決定 | 依據 |
|---|---|---|
| 語言 | 既有 Python（backend）。無前端改動。 | `project.md ## Tech Stack`；`functional-spec.md` §八′「本修訂明確不做的事」逐字排除任何前端檔案 |
| 資料庫 | 既有 PostgreSQL 的既有 `role_permissions` 表。**不建表、不加欄、不改型別或約束。** | `entities.md`（本單元不新增實體）；`functional-spec.md` §八′ |
| 新套件 | **零。** `backend/requirements.txt` 不變。 | 本單元的解析與測試只用標準庫（`ast`、`re`、`unittest`） |
| 新容器／服務 | **零。** `deploy/docker-compose.deploy.yml` 與 `docker-compose.test.yml` 皆不變。 | `SEC-2` |
| 新環境變數 | **零。** `deploy/render-env.sh` 與 `deploy/.env.example` 皆不變。 | `SEC-2`；`validate_env_contract.py` 通過即為其檢查 |
| 測試框架 | 既有 Python 內建 `unittest`（**不是 pytest**）。新測試檔放進 `backend/tests/` 即被 `python -m unittest discover -s tests` 撿到。 | `team.md ## Testing Posture` 的既成事實 |
| CI 設定 | **零變更。** 新測試由既有 `backend` job 的 `unittest discover` 自動撿到。 | 同上 |
| PBT（`hypothesis`） | **不使用**，判定 N/A（見 `security-requirements.md` §六）。`hypothesis` 已在 `requirements.txt`，故即使日後要用也不是新依賴。 | `rules.md` 修訂 1 的 PBT 判定段 |

## 二、改動面清單（`code-generation` 的範圍）

**這一節是本檔存在的主要理由**——本單元的改動面比「只改 seed 資料」更寬，
而寬出來的那部分是 `[Q2]`=A 的後果。不寫下來，`code-generation` 會以為
`rbac.py` 不在範圍內。

| # | 檔 | 改什麼 | 來源 |
|---|---|---|---|
| 1 | `backend/services/rbac_seed_data.py` | `DEFAULT_ROLE_PERMISSIONS` 末端插入 **44** 列（11 角色 × 4 個新 story id） | `BR3.4`′ |
| 2 | `schema_rbac.sql` | `INSERT INTO role_permissions` 區塊加同樣 44 列；**檔頭第 12 行**由「預設矩陣（308 列）」改為 352。**第 761 行是陷阱，不是第二處要改的數字**（審查 `R-01` 更正本列的初版描述）——它**現在就寫 `-- 352`** 而該檔 `INSERT` 區塊實算為 **308**，屬 `6f9227d`（2026-08-23，C1 FinOps）引入的**既存漂移**。本單元加完 44 列之後它會**碰巧變成正確**；`code-generation` 不得去找一個不存在的「308」，也不得因為「看起來沒壞」而認為那一行本來就對。既存漂移本身已具名 `RR-4`。 | `BR4.1`′ ＋ 審查 `R-01` |
| 3 | `DEPLOY.md` | **五處**「308」：`:577`、`:591`、`:596`、`:1259`、`:1270`（最後兩處在英文段落內） | `BR4.2`′ |
| 4 | `backend/services/user_router.py` | `STORY_FEATURE_LABELS` 補 **四** 個鍵；**不**加進 `CATALOG_EXCLUDED_STORIES` | `BR4.3`′、`BR4.5` |
| 5 | **`backend/services/rbac.py`** | `ensure_missing_role_permissions` 的 `logger.info`（`:110`）擴充為記錄插入了哪些 `(role, story_id)`。**這是 `[Q2]`=A 新增的改動面，2 行以內。** **既有的重複 log 點須一併知道**（審查 `R-04`）：`database.py:186` 在呼叫該函式之後**另外**記了一次幾乎相同的裸列數訊息，兩處今天都在。改完之後同一次 seed 事件會同時出現「詳細清單」（`rbac.py:110`）與「裸列數」（`database.py:186`）。這**不違反** `SEC-4` 的可驗證條件（詳細字串仍在），但實作者應知道這個重複不是他造成的。本單元**不收斂**它——動 `database.py` 的 log 超出 `[Q2]`=A 的範圍。 | `SEC-4` ＋ 審查 `R-04` |
| 6 | `backend/tests/`（新檔） | `SEC-5` 的兩份副本逐列等值測試 ＋ `U3-V1`–`U3-V5` 的 seed 不變量測試。**同一支檔**——兩者都只需解析 `DEFAULT_ROLE_PERMISSIONS`，分兩支檔會把同一份解析寫兩次。 | `SEC-5`、`U3-V*` |

**所有行號為本站實測值，施工前必須重新核對。** 本 record 已有 27 個因上游修訂
而失效的行號實例，而本單元的 `functional-design` 修訂 1 自己就更正了三處
（`schema_rbac.sql` 759 → 761、`DEPLOY.md` 兩處 → 五處、
`database.py:171–175` → `:184`）。

## 三、不改動的既有決定（明確記載，避免下游誤讀）

- **不引入資料庫遷移框架**（Alembic 等）。本單元零 DDL，連 `_ensure_*` 補丁都
  不需要——`ensure_missing_role_permissions` 已存在且已被啟動路徑呼叫
  （`database.py:184`）。
- **不改 `ensure_role_permissions_seeded` 的行為**。它在表非空時整段 no-op
  （`rbac.py:63-65`），那是既有設計，本單元只是**不依賴它**（`BR3.2`）。
  `[Q2]`=A 改的是另一個函式的 log，不是這一個。
- **不引入 rate limiting**。`[Q1]`=A 定案把 `/roles/catalog` 的 DoS 面列為
  具名殘餘風險 `RR-1`。repo 內零 rate limiting 基礎設施，引入它是獨立的
  工具鏈決策，不由一個 seed 單元夾帶。
- **不建稽核表**。`[Q2]` 的選項 D 被否決，理由是本單元明文不建表，且使用者域
  目前沒有可讀的稽核表（`[US:Q-11]` 的 Critical 已記載）。

## 四、`technology-stack` 的 codekb 引用與一處路徑說明

本 stage 的 `consumes` 列出 `aidlc/spaces/default/codekb/chiton/technology-stack.md`
（`conditional_on: brownfield`）。codekb 的正本是
`aidlc/spaces/default/codekb/cloud/`——`project.md` 已記載其由來：
`codekb-path` 由 `basename(projectDir)` 推導，而本 worktree 名為 `chiton`，
故引擎指向 `codekb/chiton/`。

**但那個分歧已經被修掉了**（審查 `R-02` 更正本節的初版框架）：本站實測
`aidlc/spaces/default/codekb/chiton` 是一個 **symlink → `cloud`**（建於 2026-10-02），
兩條路徑解析到同一份檔案，**沒有任何內容分歧**。初版把它寫成「引擎指向一處、
團隊讀寫另一處」的待解問題，那個狀態在本 stage 執行之前就已經不存在。
（第三份 `codekb/cloud-360/` 仍在，是 `project.md` 記載的歷史副本，不再更新。）

本單元**不依賴 codekb 的任何推論**：它需要的技術棧事實（`unittest` 非 pytest、
`requirements.txt` 的內容、`CANONICAL_ROLES` 的 11 個角色、`role_permissions`
的 PK 形狀）全部由本站直接開檔與腳本解析取得，列於
`security-requirements.md` 與本檔的實測註記。故 codekb 的路徑分歧對本單元的
結論無影響——記在此處是為了讓下一個讀本檔的人不必重新發現它。
