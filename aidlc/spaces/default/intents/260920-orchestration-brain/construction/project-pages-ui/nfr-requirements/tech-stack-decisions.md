# Tech Stack Decisions — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T22:52:51Z（`date -u` 取值）。識別字規則同 `performance-requirements.md` 前言。

## 〇、選型（皆沿用既有，本站不重選）

| 層 | 選型 | 依據 |
|---|---|---|
| 前端 | React 19 ＋ TypeScript ＋ Vite ＋ `react-router-dom` 7 ＋ Tailwind 4 | `codekb/chiton/technology-stack.md:97-107`；`project.md ## Tech Stack` |
| 前端型別 | `openapi-typescript 7.13.0` 由 `openapi.json` 產生 `src/types/api.d.ts` | 同上 `:106`（唯一精確 pin）；`BR87.4` 要求重 dump 與重產 |
| 後端 | Python ／ FastAPI ／ SQLAlchemy（既有 `hierarchy_*`、`membership_*` 模組） | `project.md ## Tech Stack` |
| 後端測試 | `unittest` ＋ `starlette.testclient.TestClient` ＋ `ast`（靜態鎖） | `team.md ## Testing Posture`（非 pytest；B 規則） |
| 前端測試 | **僅** Playwright e2e（chromium 單一 project） | `team.md`（D 項不採）；`codekb/chiton/technology-stack.md:119` |
| 資料庫 | PostgreSQL；DDL 正本 `schema_rbac.sql` | `project.md ## Tech Stack` |

## 一、決定

| ID | 決定 | 理由 | 檢查 |
|---|---|---|---|
| **`NFR8.100`** | 本單元**零新環境變數、零 compose 變更**；若 code-generation 發現需要任何環境變數，`NFR8` 與 `project.md` 的三處同步（`render-env.sh`、`deploy/.env.example`、`backend/.env.example`）完整適用 | 父條 `NFR8`（新增元件的部署設定完整性，`requirements.md:537`）：失敗模式無聲，故把「零」寫成可檢查的宣告而非默認 | `python3 scripts/validate_env_contract.py` 通過；`git diff --stat` 中 `deploy/`、`*.env.example` 零變更 |
| **`PPN-21`** | 前端並行佇列（`PPN-01`）**自寫**，不引入 `p-limit` 等套件 | `team.md` Code Style：零新前端依賴；一個「在途數 < 4 才取下一個」的佇列約二十行，且要配合 `PPN-04` 的卸載取消與 `BR88.1` 的兩層抓取形狀，套件反而要包一層 | `frontend/package.json` 的 `dependencies` 與 `devDependencies` 在本單元前後**鍵集合相同**（`jq '.dependencies, .devDependencies \| keys'` 比對） |
| **`PPN-22`** | 伺服器 SQL 語句計數（`PPN-06`）用 SQLAlchemy 內建的 `event.listen(engine, "before_cursor_execute", …)` | SQLAlchemy 已是依賴；不需 `pytest-*` 外掛 | `backend/requirements.txt` 在本單元前後內容不變 |
| **`PPN-23`** | 新增測試全部放在 `backend/tests/` 與既有 Playwright 目錄，由既有 CI 指令撿到 | `team.md`：`python -m unittest discover -s tests` 與 `ui-regression` 為現行閘門 | 不新增任何 CI job；`.github/workflows/ci.yml` 不因本單元變動（`git diff --stat` 於 code-generation 確認） |
| **`PPN-24`** | `openapi.json` 與 `api.d.ts` 隨 docstring 改寫一併重產（`BR87.4`） | CI 的 OpenAPI drift 檢查（`team.md ## Deployment`）會擋「改了 docstring 沒重 dump」 | `backend/scripts/dump_openapi.py --check` 與 `npm run check:types` 於 code-generation 跑綠 |
| **`PPN-25`**（`[PPN1]`=A） | 新索引以 `CREATE INDEX IF NOT EXISTS` 寫進 `schema_rbac.sql`，ORM 以 `Index("ix_project_members_user_id", "user_id")` 宣告於 `ProjectMember.__table_args__` | `project.md ## Mandated`：DDL／seed 變更須同步 `schema_rbac.sql` ＋ `DEPLOY.md`（blocking）；`test_membership_data.py:139` 的 `test_M3` 要求兩邊名稱集合相等 | 同 `PPN-07`；`DEPLOY.md` 的「這支 SQL 會建立的表／欄位」表新增一列與一條 `psql` 驗證指令（如 `\di ix_project_members_user_id`） |

## 二、刻意不採用

| 不採用 | 理由 |
|---|---|
| 前端 unit／component 測試框架（Vitest 等） | `team.md` D 項不採；佇列行為以 e2e 計數斷言（`PPN-01`–`PPN-04`） |
| 前端資料快取庫（React Query、SWR） | 新依賴；且清單是授權結果，不得快取（`performance-requirements.md` §五） |
| 新增批次 API | `BR87.4`／`[PP1]` 已定路徑不變 |
| property-based 測試框架用於本單元 | `security-requirements.md` §七：PBT hard constraint 不適用；`hypothesis` 雖已存在，本單元不以它取代五身分窮舉 |

## 三、為什麼本單元不產出 scalability／reliability／observability

`produces_kinds` 把三份限定為 `[service]`，本單元為 `ui`；但本單元有後端變更，故逐份確認「後端變更是否使它們有實質內容」：

| 文件 | 若產出，內容會是 | 判定 |
|---|---|---|
| scalability | 「請求數隨 P、S 線性增長」與「成員表全表掃描隨成員總數增長」 | **已在 `performance-requirements.md` §三與 `PPN-07` 表達**；另立一份只會重複並在修訂時漂移 |
| reliability | 失敗態的行為（清單 error、列級「系統清單讀取失敗」、儲存後重讀失敗） | 已是功能規則（`BR81.3`、`BR81.4`、`BR85.6`），本單元**沒有新增進程、佇列服務、重試或外部依賴**，無可用性目標可設；比照 `U24`（`ui`，同樣未產出） |
| observability | 新 log、metric、trace | 本單元**不新增任何 log**（`security-requirements.md` §五 的拒絕 log 決定）、無 metric 機制可接；`PPN-18` 管的是「不得輸出」而非「要輸出」 |

## 四、與上游的落差（如實記載）

- **`[PP3]` 選項 A 原文的「零 schema 變更」由 `[PPN1]`=A 取代**（`[PPN1]` 作答 2026-10-15T22:59:34Z，`nfr-requirements-questions.md:89`）：`functional-design-questions.md:172` 與 `functional-spec.md` §二 的該句改讀為「零資料表／欄位變更，新增一個索引 `ix_project_members_user_id`」。此變更屬 `project.md ## Mandated` 的「索引變更」觸發條件，**觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步**（未完成不得標示 code-generation 完成），另須同步 `models.py` 的 `Index`、`test_membership_data.py:145` 的「刻意不建」說明，並改寫 `schema_rbac.sql:608-615` 的註解。設計檔不回改；本站產出與 code-generation 的 code-summary 為準。
- `rules.md` `BR87.6` 與 `OPEN-PP23-10` 的「本單元不改寫入路徑」已被 R-01 裁決取代（`security-requirements.md` §〇）。

## 五、送審前自檢（七項；四份產出共用）

> 全部產出寫完後實算，指令與值並列；未執行任何測試（本站限制）。

| # | 自檢 | 結果 |
|---|---|---|
| 1 | **可達性** | 逐條推導每個「偵測 X」判準的構造路徑：`PPN-01`／`PPN-03` 需 P≥5 或 2S≥5——e2e 前置以 API 建 6 個專案即可；`PPN-04` 以 `page.route` 延遲構造「佇列未清空時卸載」；`PPN-12` ④ 與 `PPN-14` (b) 的「被移出的擁有者」經 `U24` 移出流程（另有管理者時允許）或 `TestClient` 直接構造；`PPN-12` ⑤ 與 `PPN-14` (c) 的零成員列以 ORM 建專案不寫成員列構造；`PPN-14a` 的「有 `K2 view` 無 `K2 edit` 的非成員」——`rbac_seed_data.py:327-337` 實數 **7** 個角色符合（`sed -n 327,337p \| grep -c "False, False)"`）。**本輪查出一處原本不可達的判準**：`PPN-14` 的四案若用無 `K2 edit` 的角色，會先在 `PPN-14a` 的 403 停下、守門永遠測不到——已在 `PPN-14` 明定四案皆用具 `K2 edit` 的角色 |
| 2 | **契約端點三問**（範圍：四份產出 ＋ 問題檔） | **前端佇列**：寫＝`ProjectsListPage`／`ProjectDetailPage` 進頁時入列；讀＝佇列本身取下一個；清＝全部完成或卸載（`PPN-04`）。**注入的可見性判定**（`PPN-14a` 的非強制形狀）：擁有＝`MembershipFacade`（產生）；呼叫＝`HierarchyFacade` 三個寫入方法；若 code-generation 改選其他形狀，三問由 code-summary 重答。**`ix_project_members_user_id`**（`[PPN1]`=A）：寫＝code-generation 的 DDL 與 ORM；讀＝`visible_project_ids` 的查詢計畫；清＝無（隨表存在）。**SQL 語句計數監聽器**：寫＝測試 `setUp`；讀＝斷言；清＝`tearDown` 的 `event.remove`——**初稿漏了清除端**，已補進 `PPN-06`。出現在少於兩份產出的識別字逐一判定：`PPN-22`／`PPN-23` 只在本檔與 `traceability.json`，屬本檔內部決定，非孤兒 |
| 3 | **引用逐字核對（分開驗事實與定位）** | 以腳本逐一印出 27 處 `檔案:行號` 的當前內容比對（`database.py:37`、`Dockerfile:30`、`schema_rbac.sql:353`／`:596`／`:608`／`:615`、`hierarchy_router.py:54`／`:76`／`:152`／`:299`、`requirement_field_router.py:146`、`hierarchy_facade.py:47`／`:213`／`:240`、`rbac_seed_data.py:328`、`test_membership_data.py:139`／`:145`、`test_hierarchy_service.py:130`、`membershipApi.ts:282`、`models.py:380`／`:426`、`functional-design-questions.md:172`、`security-design.md:316`／`:329`、`requirements.md:430`／`:537`、`technology-stack.md:119`）。**查出並更正三處定位錯**：`hierarchy_facade.py:212-237` → `:213-240`、`requirement_field_facade.py:268-276` → `:268-283`（logger 呼叫實際到 `:283`）、`requirements.md:613-620` → `:610-622`。另查出 `PPN-14b` 原寫的 grep 範圍 `hierarchy_*.py` 會命中 `hierarchy_migration.py` 的 2 處既有內容，已收窄為兩支檔 |
| 4 | **檔案集合一致性** | 對照同為 `ui` 的 `member-pages-ui/nfr-requirements/`（不計 `reviews/`）：問題檔、performance、security、tech-stack、traceability 五份——**相同**。對照 `mcp-bridge`（`service`）多出 scalability／reliability／observability：本單元為 `ui`，`produces_kinds` 不含；因本單元有後端變更，逐份判定內容是否另有實質，結論與理由見本檔 §三 |
| 5 | **跨檔傳播（按事實）** | 逐事實 grep 五份檔：①「並行上限 4」——問題檔 2、performance 2、traceability 1，值一致；②「不設硬上界」——問題檔 1、performance 3、traceability 1；③「`[PPN1]`=A 定案」——作答後重跑：待定標記（「待…作答」「建議項暫定」兩種字樣，以 grep 掃）在四份產出的殘留為 **0**（本列刻意不寫出原字樣，避免自我命中）；`PPN-07`、`PPN-25`、performance 前言、security §〇、traceability 兩列皆寫「`[PPN1]`=A」；④「R-01 取代 `BR87.6`／`OPEN-PP23-10` 的『不改寫入』」——security §〇、tech-stack §四、traceability `PPN-14` 三處表述一致；⑤「零 schema 變更」——問題檔 3 處（題幹引用與選項文字，不改）；performance 前言、security §〇、tech-stack §四 各 1 處，皆寫明「由 `[PPN1]`=A 取代、觸發 `schema_rbac.sql` ＋ `DEPLOY.md` blocking 同步」；⑥「7 個角色有 view 無 edit」——security 與 traceability 一致。**本輪修正一處自相矛盾**：`PPN-01` 的推導原寫「在途數最多約 4＋3」卻接著說「常駐池 5 條之內可容納」，與 W3 的依序請求不符；改為「扇出期間 4＋1＝5」 |
| 6 | **可算的數字先算再寫** | `jq '.upstream_ids\|length'`＝**11**；`OK`＝**2**、`N/A`＝**9**（`jq '[.coverage[]\|select(.status=="OK")]\|length'`）；`jq '.reverse\|length'`＝**23**，與四份產出中以粗體定義的 `PPN-*` 集合以 `comm` 比對**零差異**；繼承子條 **4**（`NFR8.100`、`NFR11.100`–`.102`），皆出現在 `coverage` 的 target；需求總數 4＋23＝**27**。§三 的例算：1＋20＝21、⌈20÷4⌉＝5、2＋2×10＝22、⌈20÷4⌉＝5 |
| 7 | **ADR-0006 四面向 ＋ PBT** | 見 `security-requirements.md` §六、§七，逐格對照上游 `functional-spec.md` §九之一：IAM **擴充**（理由：R-01 裁決使範圍變大，非重判），Encryption、Network exposure、Audit logging 與上游**相同**；PBT 不適用、與上游一致。**IAM 有內容**：`PPN-11`–`PPN-16` 共 9 條（含 `PPN-14a`–`c`） |
