# Project-Level Rules

> Project-specific specialisation and corrections. Loaded after `org.md` and
> `team.md` as strict-additive guidance; contradictions with broader policy
> are rejected. Populated by practices-discovery and the self-learning loop.
>
> Cloud-360 note: 本層為本專案自有規則（見 ADR-0011），以繁體中文撰寫。
> 識別字、路徑、指令維持原文。

## Way of Working

<!-- Project-specific specialisation. Example: -->
<!-- This monorepo requires package-scoped branch names and a package owner -->
<!-- review in addition to the team's normal merge policy. -->

- Sidebar 導覽依 user story 大類分層（例如 A、J）；故事層（A1／A3、J3a／J3b）為第二層。既有 A／J 先套用，後續功能比照。 (learned 2026-08-06) <!-- cid:reverse-engineering:c3 -->
## Walking Skeleton

<!-- Project-specific specialisation. Example: -->
<!-- The walking skeleton must exercise the legacy service adapter as well -->
<!-- as the new service boundary. -->

## Testing Posture

**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。

## Deployment

**Construction 與 Operations 是連續的，不是依序的兩個 phase**（ADR-0008）：

1. **build ↔ deploy 之間沒有 phase gate。** 從 PR → 合併進 `ut` → 部署到自有 staging（ADR-0007）是單一連續管線。「寫 code / build / test」與「部署 / 運行」屬於同一條流程，不是先後兩段。
2. **Operations 是持續的迴圈。** 內涵為「deploy + 觀測 + 應變」的持續循環，與 Construction 交織並行。任何 code 變更都同時是一次潛在的維運事件。
3. **不得以「Construction 尚未完成」為由延後 Operations 工作，反之亦然。**
4. **保留的邊界。** 本規則只改「Construction↔Operations 的關係模型」，不改**範圍邊界**（見 `## Scope Overrides`）。Operations 中尚未落地的維運學科（observability、incident playbooks、SLO/on-call）仍是真實待辦。

對 AI agent 的實務指示：規劃時把部署、回滾、觀測、告警視為與 code 實作同一條 pipeline 的環節；描述專案狀態時不要用「已進入 Construction / Operations 階段」這類線性 phase 語言，直接陳述具備哪些能力。

## Code Style

<!-- Project-specific specialisation. -->

- 架構圖連線不得與元件 icon 重疊時，優先在 `diagram_builder` 以 exit／entry 連接點與 waypoint 修正，而不是只靠前端 post-process。 (learned 2026-08-06) <!-- cid:reverse-engineering:c7 -->
## Tech Stack

- **Backend**：Python / FastAPI（`backend/`）
- **Frontend**：TypeScript / React / Vite（`frontend/`）
- **資料庫**：PostgreSQL；schema 以 repo 根目錄的 `schema.sql` 與 `schema_rbac.sql` 為可攜來源
- **Specs / 圖**：Markdown、Mermaid、draw.io
- **CI/CD**：GitHub Actions（`.github/workflows/ci.yml` 跑 repo contract、lint、build、Docker build；`deploy.yml` 在 `ut` 觸發部署）
- **Staging**：自有主機 `192.168.10.10`，經 Cloudflare Tunnel 對外為 `cloud360.danniel.cc`（ADR-0007）
- **測案管理**：自架 Kiwi TCMS（`tcms.danniel.cc`，於 `dc-infra` repo 維運）
- **雲端範圍**：AWS / GCP / Azure 三雲的架構與維運設計

## Decided

- DECIDED: 專案定位為 AI-native multi-cloud architecture & operations platform，方法論基礎為 Spec-Driven Development（SRS、user stories、architecture、ADRs）。(ADR-0001)
- DECIDED: `extensions/security/baseline/` 預設啟用，為 hard constraint（IAM、encryption、network exposure、audit logging）。requirements analysis 階段不需再詢問。(ADR-0006)
- DECIDED: `extensions/testing/property-based/` 預設啟用，為 hard constraint。requirements analysis 階段不需再詢問。(ADR-0006)
- DECIDED: 文件語言為繁體中文，取代 upstream bilingual-docs 與 ADR-0005 的雙語強制。(ADR-0009)
- DECIDED: commit message 與 PR 標題使用中文 type，branch 名稱維持英文 type。(ADR-0010)
- DECIDED: 採用 AI-DLC v2；專案規則層為 `aidlc/spaces/<space>/memory/`。(ADR-0011)
- DECIDED: 所有 AIDLC artifacts（含 v2 之前的歷史文件）都在作用中 intent 的 record 目錄 `<record>/` 下；baseline record 為 `aidlc/spaces/default/intents/260802-default/`。(ADR-0011)
- DECIDED: 專案狀態的細部來源為 `<record>/aidlc-state.md`。

- reverse-engineering 的 conductor 在派工前為守門決策所做的最小事實蒐集（僅統計數字，如 git diff --stat、檔案計數），不構成 stage 檔所禁止的「檢視應用原始碼／列舉 repo／預先計算檔案清單」；界線是不讀取原始碼內容、不產生檔案清單 (decided 2026-09-16) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:reverse-engineering:ceb610661b40115e9ffa91093a4fb885bba6cd6ac2327cd567943ee8b38a2ddf -->
- 退場／移除類需求採逐條可執行形式（含具體檔名與行號、指明「改寫」或「刪除」），不採概括敘述。理由：遺漏套件外掛鉤的後果是 CI 紅燈而非設計瑕疵，且 codekb 的盤點結果若不在需求固定下來，下游沒有第二次機會發現 (decided 2026-09-16) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:requirements-analysis:0fbe1955adaf68e9bfdce87558ee92df70822e24a46db6bf6c4c1e22bd9fe779 -->
## Scope Overrides

- ✅ **In scope**：SRS、architecture diagrams、user stories、ADRs、IaC generator design、agent routing design、MCP/skill management spec、validation scripts、baseline CI、自有 staging 的部署與維運。
- ❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。

## Forbidden

- NEVER 讓版控中**存在** path parts 含 `prod`、`production`、`secrets` 的檔案 — `scripts/validate_repo_contract.py` 的 `validate_no_production_config_added()` 會擋（CI 紅燈）。檢查方式是對 `git ls-files` 做**全域掃描**（不是 diff 基準），所以不限於本次新增的檔案：任何已納入版控的違規路徑都會讓檢查紅燈，且在 CI 的乾淨 checkout 下與本機行為一致（issue #509）。比對為 **path-part 精確比對**且不分大小寫，因此 `aidlc-product-agent.md`、`secrets-policy.md` 這類含子字串但非完整 path part 的檔名不受影響。
- NEVER commit 私鑰或 AWS / Azure / GCP 的 credential 字串。實際被擋的樣式列在 `scripts/validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS`（涵蓋私鑰 PEM 標頭與三雲的 secret 環境變數）。**不要把那些樣式照字面複製到任何 contract 檔案裡** — 掃描器不分辨「示範」與「洩漏」，會直接紅燈。
- NEVER 在未取得 human approval 的情況下執行 production write、IaC apply 或 IAM 變更。
- NEVER 直接編輯 `.claude/` 下的 upstream 框架檔來表達專案規則 — 專案規則一律寫在 `aidlc/spaces/<space>/memory/{team,project}.md`，否則下次升級會被整批覆蓋。

<!-- practices-discovery 2026-08-09：本節本次無新發現（affirm 紀錄，非規則）。 -->

- **NEVER** 呼叫需要雲端供應商帳號憑證的計價 API（Cost Explorer、Billing、Cost Management 等）作為 C1 價目來源；`pricing_client` 只准公開免帳號價目端點 (affirmed 2026-08-19；**ADR-0017 §3＋§8 改述**：估價一律來自使用者上傳的官方估價表，不得以自動取價產生估價；agent 產生建議時得呼叫**公開免帳號**價目端點確認現價，所得價格只寫入建議文字、不得回寫明細。需帳號憑證的端點——含走 IAM 的 boto3 Pricing Query API——仍全面禁止。**ADR-0018 §1 再改述**：**目錄價類**端點解禁，得使用帳號憑證——AWS Price List Query API（IAM）、GCP Cloud Billing Catalog API（API key）、Azure Retail Prices（本即免憑證）；**帳單與用量類**——Cost Explorer、Cost and Usage Report、Cost Management、Billing Export——**維持全面禁止**（§2）。「所得價格只寫入建議文字、不得回寫明細」的界線不變)
- **NEVER** 把 WA `COST-*` 啟發式 findings 當成已實作的 TCO／成本計算能力 (affirmed 2026-08-19)
- **NEVER** 把 Assessment 的雲端供應商下拉當成 pricing Manual Override (affirmed 2026-08-19)
- **NEVER** 把 RBAC 種子或權限頁的 C1 欄當成已有 cost router／Cost 頁 (affirmed 2026-08-19)
- **NEVER** 在既有 n8n／PNG 呼叫點用 httpx 直接打雲端 Pricing API；新計價呼叫必須走獨立 `pricing_client` (affirmed 2026-08-19；**ADR-0017 §8**：`pricing_client` 恢復效力，本條原樣有效——httpx 不得在任何位置直打雲端 Pricing API，一律走 `pricing_client`；**ADR-0018 §1**：`pricing_client` 可對接的端點集合擴大至目錄價類的需憑證端點，httpx 不得直打的規定不變)
- NEVER 以 repo 內新增的實作程式（例如 `scripts/` 下的 Python）承載**無人值守的**流程自動化與外部系統同步；此類機制一律以 gh-aw 或 GitHub Actions workflow 承載。**邊界以觸發來源判定**：由事件或排程觸發、無人在迴圈內的（`on: push`／`pull_request`／`schedule`／`workflow_dispatch` 等）屬本條禁止範圍；由 stage 檔或 slash command 觸發、須有人執行才會跑的工具**不在此限**——既有先例為 `tcms` plugin 的 `scripts/tcms_validate.py` 與 `scripts/tcms_sync.py`，兩者只被 `.claude/aidlc-common/stages/construction/tcms-test-cases.md` 呼叫，`.github/` 下無任何 workflow 呼叫它們。注意 gh-aw 是 LLM 驅動（`engine: copilot`），落在本 repo 三塊結構性盲區的「所有 LLM 路徑」那一塊，決定性的映射邏輯應優先放在純 Actions 步驟，判斷性的工作才交給 gh-aw (learned 2026-08-23；2026-08-24 收窄為「無人值守」並寫明觸發來源判準——原文的「與外部系統同步」會讓 `## Mandated` 強制要求的 tcms 流程技術性違反本條，該矛盾由使用者裁決收窄規則文字而非增列例外) <!-- cid:intent-capture:260822-c1 -->
## Mandated

- ALWAYS 在 commit 前執行 `python3 scripts/validate_repo_contract.py`。違反 repo contract = CI 紅燈。contract 涵蓋 repo 層必要文件（`REQUIRED_FILES`／`REQUIRED_TEXT`）、record 層 baseline artifacts（`REQUIRED_RECORD_FILES`／`REQUIRED_RECORD_TEXT`，執行時動態解析 record 目錄）、文件語言（record 內不得有 `## English Version`）、禁止路徑與禁止內容。
- ALWAYS 在變更**資料庫結構或部署必知的 schema／seed 行為**時同步更新部署資產（blocking，未完成不得標示相關 Construction／部署階段為完成）：
  - 觸發條件：新增／刪除／更名表；新增／刪除／更名／改型欄位；索引／唯一約束／外鍵變更；seed／預設資料語意變更（如 `role_permissions` 矩陣、預設帳號）；ORM／啟動補丁引入新 DDL（`models.py`、`database.py` 的 `_ensure_*_schema`）。
  - **不觸發**：僅資料內容／應用層 JSON 形狀變更（如 `scores_json`／`findings_json`）且無 DDL。
  - 必做 1 — `schema_rbac.sql`（repo 根目錄）：把對應 DDL 與必要 COMMENT 寫進適當區塊；使用 `IF NOT EXISTS` 等可重跑安全寫法；新增表／物件時更新檔頭涵蓋清單與驗證註解；僅改 seed 時標註重跑會覆寫的風險。
  - 必做 2 — `DEPLOY.md`（repo 根目錄）：更新「這支 SQL 會建立的表／欄位」表；新表與重要欄位補說明與建議的 `psql` 驗證指令；若影響既有環境升級，寫明「重跑 `schema_rbac.sql`」或與後端 `_ensure_*_schema` 的關係。
  - 建議一併更新（非 blocking）：`schema.sql`、`<record>/construction/plans/schema-rbac-notes.md`。
- ALWAYS 讓三個環境的設定保持**分離且各自完整**，並在 commit 前執行 `python3 scripts/validate_env_contract.py`（CI 的 `repo-contract` job 亦會執行）。三個範圍為：本機 dev（`backend/.env`、`frontend/.env`）、CI 測試（`docker-compose.test.yml` 內嵌）、部署（`deploy/.env`，由 `deploy/render-env.sh` 產生）。
  - **部署設定的唯一產生點是 `deploy/render-env.sh`**：`deploy.yml` 的 deploy 與 rollback 兩個 job 都呼叫它，不得任一 job 自行 `cat > deploy/.env`（此規則的由來：兩個 job 原本各有一份逐字重複的 heredoc）。
  - 不得把本機來源（`localhost`、`127.0.0.1`）寫進 `deploy/.env.example`，亦不得把部署專屬 key（`POSTGRES_*`、`PUBLIC_URL`、`FRONTEND_HOST_PORT`、`CLOUDFLARED_*`）寫進 dev 範本。
  - **新增 compose 消費的變數時**，同一個 PR 必須讓 `render-env.sh` 寫它、`deploy/.env.example` 列它。原因是失敗模式無聲：無 fallback 的變數缺值時只會變成空字串，服務照常啟動但功能降級（實例：`N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致每次部署的架構圖 icons 都靜默退回灰底佔位圖）。
  - **憑證不得含 `$`**：docker compose 會對 `--env-file` 的值做內插，`ab$cd` 會被無聲截斷成 `ab`，資料庫因此以遠弱於預期的密碼運行且無任何錯誤。`render-env.sh` 已對此擋下並要求改用 `openssl rand -hex 32`。
- ALWAYS 在異動 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`、任一 `.env.example` 或 `render-env.sh` 時同步更新 `LOCAL-DEV.md`。它是唯一寫下本機執行全部功能所需隱性前置條件（`claude` CLI 子行程、n8n webhook）的文件，過期即等於沒有。
  - 本規則由 `local-dev-drift` agentic workflow 在 PR 上提醒（非阻擋，只提問）。**本條是正式來源**；workflow 的觸發 paths 只是它的實作，兩者若不一致以本條為準，該修的是 workflow。
- ALWAYS 在任何 high-risk action（production write、IaC apply、IAM 變更）前先給 plan + impact + rollback，並通過 human approval gate。
- ALWAYS 讓引擎把 AIDLC 階段事件寫進 `<record>/audit/` 的 per-clone shard（不要手動編輯 shard）；架構級決策開 ADR 於 `<record>/inception/decisions/NNNN-*.md`。

- Design／generate 進 agent 前必須做平台自我竄改預檢（Cloud-360 的 DB／系統值／API key／金鑰等）；命中則不呼叫 LLM，回固定「此需求毫無相關，請重新輸入」；並以 system prompt 補強。 (learned 2026-08-06) <!-- cid:reverse-engineering:c8 -->
- 在 Cursor harness 執行 AIDLC 核准閘時：因無 Claude Code UserPromptSubmit hook，conductor 在呼叫 `report --result approved` 前須先執行 `bun .claude/hooks/aidlc-record-human-turn.ts`（2.7.0 起的檔名，2.5.x 為 `aidlc-mint-presence.ts`），確保 audit 有對應 HUMAN_TURN（使用者須已在對話中明確核准）。 (learned 2026-08-06) <!-- cid:requirements-analysis:c2 -->
- **ALWAYS 對每一項變更檢查 ADR-0006 security baseline 的四個面向（IAM、encryption、network exposure、audit logging）**；此為 hard constraint（`CLAUDE.md` 第 3 章「Standing Constraints」逐字列為 `Hard constraint（IAM、encryption、network exposure、audit logging）`）。原承載該約束的 v1 路徑 `extensions/security/baseline/` 已隨 v2 遷移（ADR-0011）從 repo 移除（全樹搜尋僅 `project.md` 的 `## Decided` 一行與兩份 ideation 文件引用它，無任何實體檔案），使這條 hard constraint 一度失去可執行形式。本條為其在 v2 規則層的重新落點（訪談 Q5 定案 A：補進本檔）。實務上：涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出（feasibility、scope、user-stories 等）中明列 security 影響與處置，不得僅以「已有 ADR-0006」帶過。 (affirmed 2026-08-09)
- ALWAYS 在每個 intent 的 construction 階段執行 `tcms-test-cases` stage 並完成其四項產出（**blocking**，未完成不得標示該 stage 為完成，亦不得進入部署階段）。此 stage 由 `tcms` plugin 提供，`execution: ALWAYS`、涵蓋全部 scope，stage 檔為 `.claude/aidlc-common/stages/construction/tcms-test-cases.md`，撰寫標準為 `aidlc/spaces/<space>/knowledge/aidlc-quality-agent/test-case-authoring.md`。
  - 必做 1 — **覆蓋盤點**：把本 intent 每一項外部可觀察的行為分類為「已自動化／待自動化／只能手動」三桶之一，計數寫進 stage summary。無法分類者列為未分類項並說明卡在哪，**不得預設丟給手動**（預設丟手動等於把問題藏進一份沒人會跑的文件）。
  - 必做 2 — **手動測案**：只為「只能手動」桶寫案例，產出 `<record>/construction/tcms-test-cases/manual-test-cases.md`。每案必須有目的、背景、前置條件、逐步驟表（操作 ↔ **可觀察的**預期結果）、通過條件、追溯。預期結果寫「正常」「成功」者不算步驟。回歸案例的背景必須寫出症狀、錯誤訊息逐字、以及**既有自動化層為何沒抓到**。
  - 必做 3 — **自動化腳本**：為「待自動化」桶**實際寫出腳本**並跑綠，不是列願望清單；落點依 `team.md` 的既成事實（backend `unittest`／`TestClient`／Playwright e2e，前端無 unit 測試框架）。每支腳本都必須做**突變驗證**——把修正改回錯的行為、確認測試紅燈、還原複驗——並把突變內容與結果寫進 `automation-test-plan.md`。未寫出腳本的項目列為 open item 並說明理由。
  - 必做 3b — **自動化案例的規格註解**：每個新增或改動的自動化測試，都要在 `test()` 前加結構化註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`，格式見撰寫標準 §4.4）。這是自動化案例在 TCMS 上唯一的描述來源——**不得直接在 TCMS 手寫描述**，因為會被改的是 code 那份，手抄的描述必定過期且無人察覺。
  - 必做 4 — **驗證關卡（blocking，同步之前）**：執行 `/tcms-verify`。第 1 層機械檢查 `python3 scripts/tcms_validate.py --all`，四類皆為可判定項——必填欄位與格式、空洞預期結果、追溯目標存在、API/UI 比對 `openapi.json` 與 `App.tsx`；**ERROR 一律阻擋，WARN 逐項判讀不得無視**。第 2 層語意審查逐案七點（目的是否指向真會失敗的行為、回歸案例是否說得出既有自動化層為何沒抓到、步驟能否被外人執行、受測介面是否漏列、通過條件是否二元可判、是否與自動化層重複、規格是否與 `stories.md` 的 AC 一致）。**未通過不得同步**——TCMS 上一份錯的案例會被當成已覆蓋的證據，錯誤的覆蓋感比沒有覆蓋更危險。例外：追溯指向尚未合併分支上的檔案時，該 ERROR 是真實的跨分支依賴，處置是說明依賴與確認合併順序，不得為了讓檢查過關而刪掉追溯。
  - **每個案例都必須有「受測介面」**：手動案例用 `- API: \`METHOD /path\` → status` 與 `- UI: \`/path\``；自動化案例用 `@api`／`@ui` 註解。兩者至少有一個，且會被機械比對——寫了不存在的端點或路徑會被擋下。
  - 必做 5 — **TCMS 同步（兩種來源分開跑）**：手動案例 `--file <manual-test-cases.md>`（建立＋更新）；自動化案例 `--spec <spec 檔>`（**只更新既有案例**，案例本身由 junit plugin 從測試結果建立，本工具不建立、不碰 `is_automated`）。兩者都先 `--dry-run` 預覽並在 gate 呈現，核可後才實際寫入，結果記入 `tcms-sync-report.md`。`~/.tcms.conf` 不存在時**不得靜默跳過**，記為未完成項並在 gate 說明。
  - TCMS 案例名稱是 `<describe> › <test>`，與 junit plugin 的 `--summary-template '${name}'` 一致；改動 describe／test 字串會讓既有案例變成沒有執行結果的孤兒。
  - **不得**為自動化層已斷言的行為另寫手動案例——`operation/test-case-management-plan.md` 定下「每種測案有單一真實來源」：自動化的主檔是 repo 的 spec code（TCMS 只存中繼資料與歷史結果），手動的主檔才是 TCMS。雙份維護必有一份悄悄過期。
  - 本規則的由來：本 repo 的自動化層有三塊**結構性**盲區（所有 LLM 路徑、n8n 圖示取得、本機環境殘值），實測證實六道 CI 閘門全綠時仍會放行這三類缺陷。 (affirmed 2026-08-16)

- **ALWAYS** 第一個 C1 HTTP 端點落地時，即使 `role_permissions` seed 未改，也須有 allow/deny 雙向 TestClient：有 C1 權限 → 2xx，無 C1 權限 → 403（不得只測 happy path） (affirmed 2026-08-19)
- **ALWAYS** cost 功能域採三層：`cost_router` → `cost_service` → 純函式 `cost_calculator`，另獨立 `pricing_client`；禁止把 cost 邏輯寫進 `user_router.py` 或 `wa_rule_engine.py`；`cost_calculator` 內禁止 httpx、DB session、`HTTPException` (affirmed 2026-08-19；**ADR-0017 §1–§2＋§8**：三層形狀與純函式禁令**保留**，純函式層由 `cost_calculator` 改錨至估價表解析器，ADR-0006 的 PBT hard constraint 隨之移轉——不是豁免。`pricing_client` 子句於 §1 廢止後由 §8 恢復，職責改為「包裝公開免帳號價目端點供 agent 按需查價」，非取價主路徑。可執行檢查：解析器模組內 `import httpx`、DB session 型別、`HTTPException` 三者 grep 結果須為零)
- ALWAYS 在新增任何憑證型 secret 後實地查證它落在 secrets 而非 variables（`gh api repos/<owner>/<repo>/actions/secrets` 與同路徑的 `/variables` 各查一次，比對名稱）。Actions variables 為明文、UI 可回讀、且在 workflow log 中不遮罩，而本 repo 為 public、Actions log 公開可讀——一次意外 echo 即等同公開發布。若憑證曾誤存為 variable，僅搬移到 secret 不足以結案，必須重新產生金鑰：「應該沒人看過」是沒有證據的假設 (learned 2026-08-23) <!-- cid:approval-handoff:260822-c4 -->
- ALWAYS 把 `<record>/inception/decisions/` 的既有 ADR 納入 intent 的唯讀查證範圍（含其他 intent record 下的 ADR），只要主題可能重疊——查 code、workflow、官方文件與 repo 現況都不能取代它。本 intent 即因 ideation 四站全未引用 ADR-0012，拖到 reverse-engineering 才發現六處衝突（四處為直接矛盾），必須回頭以 Modify 模式重走 approval-handoff 並新開 ADR-0013 才收斂 (learned 2026-08-23) <!-- cid:reverse-engineering:260822-re-c5 -->
- ALWAYS 把 codekb 寫進以 **repo** 命名的目錄，不隨 clone／worktree 目錄名開新庫——`codekb-path` 由 `basename(projectDir)` 推導，在名為 `chiton` 的 worktree 會為同一個 repo 開出第三份（已有 `codekb/cloud-360/` 與過期的 `codekb/cloud/`）；就地更新既有那份即滿足引擎對 `codekb/*/` 的 ANY-exists 完成檢查。且不得以手改 `intents.json` 補 repo 名來繞開，那會讓 swarm `prepare` 去找一個不存在的兄弟目錄 (learned 2026-08-23) <!-- cid:reverse-engineering:260822-re-c3 -->
- ALWAYS 在派 reviewer 之前跑完六項送審前自檢，並在 stage summary **逐項報告結果**（blocking，未報告不得派工）：(1) **可達性**——每條「偵測 X 狀態」的規則先驗 X 可達；(2) **契約端點三問**——每一個宣告的**欄位**（誰寫、誰讀、誰清）與**方法**（誰擁有、誰呼叫）都要能指名，缺一即缺口；**檢查範圍是整個 stage 的全部產出，不是本輪動過的檔**；(3) **引用逐字核對**——每個來源標籤開檔驗證，不憑印象；(4) **檔案集合一致性**——同類單元之間 diff 產出檔清單，缺一個就是一項發現；(5) **跨檔傳播**——列出改動的**事實**（非字串），每個事實用它的幾種表達形式各 grep 一次；(6) **可算的數字先算再寫**。由來：functional-design 跑了三輪 reviewer、約 41 分鐘 wall-clock，而六項發現**全部**是送審前可自行查出的，reviewer 沒有找到任何需要獨立視角才看得見的東西——問題不在輪數而在沒有自檢就送出。第 3、5、6 項在本輪之前已是規則但未被執行，故本條要求機械化報告而非僅列為指引。第 2 項的兩處擴充來自它第一次實跑的結果：**只跑動過的檔會漏掉最嚴重的一類**（functional-design 的八個單元並行審查中，四個 Critical／Major 都是「契約有一端懸空」——`managed_block_hash` 有讀者無寫者、`resolve_if_open` 有定義無呼叫者、`read_issue_state` 支撐一條 AC 卻無呼叫者、`parse` 的兩種 `null` 有語意差無區分者），而它們全部落在我那一輪沒有編輯的檔案裡。可執行做法：對 `component-methods.md` 的每個方法與每個共享狀態欄位，grep 全 stage 產出，**出現在少於兩個單元者逐一判定**是內部方法還是孤兒契約，判定結果寫進產出。目標是一輪送審一輪 READY，不是不送審 (learned 2026-08-29) <!-- cid:functional-design:user-1 -->
- **ALWAYS** 在 Cursor harness 執行 AIDLC 時，每次用檔案工具寫出 record 內的 artifact 之後，立即對每個檔案執行 `printf '{"tool_name":"Write","tool_input":{"file_path":"<abs>"}}' | bun .claude/hooks/aidlc-write-audit-log.ts` 補記 ARTIFACT_CREATED／UPDATED；Cursor 沒有 upstream 的 PostToolUse write hook，少了這步 `aidlc-log.ts review` 會以 "output document was not saved after the confirmed answers" 拒絕 reviewer 請求 (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:intent-capture:a3e03d80cabb2def88ac4c41cd56b4445316fe4077db7b5989545441875cc57f -->
- ALWAYS 當使用者在核可關卡提出推翻上游定案的要求時，先以追問界定反轉的確切範圍（是新增能力還是取代既有決定、影響哪幾條已核可的答案、是否觸及已發出的 ADR），再把「就地修訂上游產出 vs 重跑受影響的 stage」當成問題交給使用者裁決；不得由 AI 逕自判定為小幅澄清吸收掉，也不得逕自啟動重跑 (learned 2026-09-16) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:approval-handoff:e2923632dcb33245681c7470ddeb644702f15ea86478509b3f23a8125877b9ca -->
- ALWAYS 當使用者選的選項會製造新的正確性問題時，說出具體理由並請其重選，不得照單全收；理由須指名會壞掉的是什麼，而非只表達疑慮 (learned 2026-09-16；實例：以官方目錄價覆蓋上傳估價表的明細，會把含 CUD／RI／Savings Plan 折扣的正確價格改成未折扣定價) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:approval-handoff:91f49c7f17956d4aca9d3422f11aaa25778a1aa644b539681f116bf7ee284e50 -->
- ALWAYS 派長時間掃描或盤點任務給 subagent 時，在 brief 明寫「寧可在設定深度下寫出完整可用的輸出檔，也不要追求窮盡而未落地；時間不足時須據實記為 skimmed，不得宣稱 deep」；少了這句，agent 會把時間全花在讀取而不產出 (learned 2026-09-16；實例：reverse-engineering 首次 developer 派工跑 7 分鐘被中斷，handoff 零產出) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:reverse-engineering:0aac21419814052895a76b8998b78fb76e75535540fd112c23d0ebf7f908f12c -->
- ALWAYS codekb 以 kind: full 發布時，須在產出內明寫深度分佈（哪些路徑深讀、哪些僅盤點），不得讓 full 被下游讀成「處處都讀過」；深度切分跨越元件邊界時，拆分元件而非放寬覆蓋宣稱 (learned 2026-09-16) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:reverse-engineering:2608f768557e75d3aab19caf5ce98b809e44c34be808f4f35f663e6bb62de474 -->
- NEVER 對已有 reviewer 或其他 subagent 寫入內容的 artifact 做附加時，使用 index 字串切片截尾（如 s[:s.index("## Review")]）——會把下游寫入的整段內容刪掉，且 artifact 多半尚未進版控無法還原。一律以純 append 或錨定自己寫入的標記進行 (learned 2026-09-16；實例：requirements-analysis 誤刪 product-lead 的 ## Review 區段，需 resume reviewer 重寫) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:requirements-analysis:204c7209210b6fb6ccf8348a2f9af1e49cddf79d3a192473f555618f8c7a9f67 -->
- ALWAYS requirements 或後續階段新增／推翻了已核可 scope-document 的項目時，須在產出文件內逐處明標「本階段新增或推翻、scope 尚未涵蓋」並要求回補，不得當作既有 CAP 的自然延伸吸收；標記須在提問當下即向使用者揭露後果，非事後補記 (learned 2026-09-16) (learned 2026-09-16) <!-- cid:260916-estimate-upload-rework:requirements-analysis:ed182d6322d3545d0af1f58229ee65ae34e61f2255d2afaeb1770a47d0f8005e -->
## Corrections

<!-- Project-specific corrections from human feedback. -->
<!-- Format: NEVER/ALWAYS [behavior] (learned [date]) -->
- stage diary（memory.md）只能使用四個標準 H2（Interpretations / Deviations / Tradeoffs / Open questions），新增條目一律 append 到既有標題下，不得使用「（續）」等變體標題 — aidlc-learnings.ts surface 只認標準標題，變體下的條目不會進入學習候選 (learned 2026-08-02) <!-- cid:intent-capture:c1 -->
- 問授予權限的問題時，選項描述必須寫明授予後實際看得到／做得到什麼（涵蓋的頁面、欄位、操作），不能只寫 story id 或權限名 — 使用者無法從 id 評估權限邊界 (learned 2026-08-02) <!-- cid:intent-capture:c7 -->
- 在 artifact 掛 [Q<n>] 來源標籤前，必須回頭逐字核對該題的已選選項原文，不得憑印象引用 — claim-sources sensor 只驗標籤可解析性、不驗語意支持，誤掛的標籤只有人工核對能攔住 (learned 2026-08-02) <!-- cid:intent-capture:c11 -->
- 任何 artifact 的 Assumptions & Open Questions 有新增或刪除時，必須同步 reset 問題檔的 Assumption Confirmation 並重新取得人工確認 — 已確認集合與 artifact 現況不一致時 claim-sources sensor 必然失敗 (learned 2026-08-02) <!-- cid:intent-capture:c12 -->
- ideation 的「禁實作細節」約束的是 artifact 內容，不是查證行為：為了把問題問對，讀 code／schema／權限矩陣是必要且允許的，查證結果用於出題與選項設計，不寫進 ideation 產出 (learned 2026-08-02) <!-- cid:intent-capture:c8 -->
- 使用者以實作語彙（欄位、資料表、權限 id）回答 ideation 問題時，artifact 改寫到產品邊界高度（例：「稽核只需最後一次登入」而非「users 加 last_login_at」），保留決策約束力但不下沉到設計 (learned 2026-08-02) <!-- cid:intent-capture:c5 -->
- reviewer 的修正建議若會製造新的無來源主張，以 grounding contract 為準拒絕該建議並在 diary 記明理由 — 修正手段本身不得違反 stage 的來源規則 (learned 2026-08-02) <!-- cid:intent-capture:c19 -->
- 請使用者確認 workflow scope 時，一併揭露該 scope 的 stage 數與 approval gate 數 — 不揭露成本的確認不是知情確認 (learned 2026-08-02) <!-- cid:intent-capture:c6 -->
- CONDITIONAL stage 的適用性判定必須逐項對照該 stage 的 condition 條款（整合約束／法規要求／顯著技術不確定性）並把判定理由記入 stage diary，不得憑 feature 表面大小直覺 skip — 本次 feasibility 即因 RBAC seed 兩處同步與系統零既有紀錄而適用 (learned 2026-08-03) <!-- cid:feasibility:c1 -->
- stage 檔的範例問題清單是 guidance 不是 script：與當前 intent 無關的題目（例如僅觸及自有 staging 時的「AWS services and accounts」盤點）應省略，並在 diary 記明省略理由 (learned 2026-08-03) <!-- cid:feasibility:c2 -->
- 出題前以唯讀探查查證 code／schema／部署文件事實，查證結果登錄於問題檔的 ## Sources 供題幹與選項引用；產出 artifact 維持能力層表述，技術細節留在 Sources 登錄處 (learned 2026-08-03) <!-- cid:feasibility:c4 -->
- 使用者答案引發跨題語意衝突時（如記錄事件的選擇改變了欄位語意），寧可加開一致性追問當場定錨並回寫問題檔，不讓歧義流入下一階段 (learned 2026-08-03) <!-- cid:feasibility:c5 -->
- ideation 對已識別的實作層風險只記載風險本身與緩解方向（如節流／彙整／非同步），不預選具體手段；把「選定緩解手段」列為設計階段的必答項並登錄於 RAID log (learned 2026-08-03) <!-- cid:feasibility:c6 -->
- 使用者明確選擇不把某候選項列入 Won't Have 時，以「未承諾」狀態記入 scope 文件（不在範圍、不在排除清單、不推定未來去向），不得擅自補進排除清單或視為隱含範圍 (learned 2026-08-03) <!-- cid:scope-definition:c1 -->
- Must 能力含未定參數（如門檻 N）時，不視為矛盾也不降級該能力：把「參數於指定階段定案」升格為上線前置依賴，同步記入 assumptions 與 backlog 依賴 (learned 2026-08-03) <!-- cid:scope-definition:c2 -->
- stage 步驟文字提及、但 outputs 清單未列的產出（如 value stream map），併入既有 produces artifact 的段落表達，不自創檔案 — produces 清單是 artifact 集合的正式來源 (learned 2026-08-03) <!-- cid:scope-definition:c3 -->
- 上游 stage 已確認的事項（如「無時程阻塞」）不重問：省題並在問題檔前言與 diary 記明「已由上游定案、不重問」的清單 (learned 2026-08-03) <!-- cid:scope-definition:c4 -->
- 單一決策者、全 Must、依賴序已定的 backlog 不做 WSJF／RICE 數值評分 — 沒有真實輸入的相對分數是虛假精確；以 MoSCoW＋依賴序表達優先即足 (learned 2026-08-03) <!-- cid:scope-definition:c5 -->
- 下游 stage 的答案觸發 scope 擴充時，回跳上游 stage 以 Modify 模式疊加修訂（歸檔舊 artifact、既有答案與清單不動、修訂來源記入問題檔 Revision 段）並重走 approval gate；不得在下游 stage 擅自擴大已核可的範圍 (learned 2026-08-04) <!-- cid:scope-definition:rev1-c4 -->
- 下游 stage 的問答引發 scope 擴充時，先依協定回跳上游修訂重審，重返本 stage 後才產出 artifact — 本 stage 的 artifact 不得夾帶未經上游核可的範圍 (learned 2026-08-06) <!-- cid:rough-mockups:c1 -->
- ASCII 線框內的圖示一律以基本 ASCII 表達（如 (!)）；emoji 非基本 ASCII 字元，違反 stage-protocol 的線框字元標準，實作圖示樣式留設計細化階段 (learned 2026-08-06) <!-- cid:rough-mockups:c2 -->
- 加欄型 feature 的載入／錯誤態沿用既有頁面模式，不重新設計既有狀態呈現；重新設計屬改版範圍，需明確的 scope 決定支撐 (learned 2026-08-06) <!-- cid:rough-mockups:c3 -->
- 含 CJK 的 ASCII box 一律用腳本產生並驗證每行字元數一致後才寫入 artifact — 手寫 CJK 混排必然數錯（reviewer 實測證實） (learned 2026-08-06) <!-- cid:rough-mockups:c4 -->
- 剛擴充進 scope 的新範圍（如 PU-5）在首個呈現階段先給單一基準方案，讓 reviewer 與 gate 有具體對象；替代方案留下一階段探索，不在同輪並列多案 (learned 2026-08-06) <!-- cid:rough-mockups:c5 -->
- 彙整型 stage（如 approval-handoff）的範例題僅問未被上游定案的事項：已由各站 gate 核可、scope 跳過或上游問題檔確認的內容不重問，省略清單與理由記入問題檔前言與 diary (learned 2026-08-06) <!-- cid:approval-handoff:c1 -->
- 彙整 artifact 的 Assumptions 清單若與問題檔某題的已答清單逐字對應，該題作答即為人工確認，不另設重複的 Assumption Confirmation 關卡 (learned 2026-08-06) <!-- cid:approval-handoff:c2 -->
- dispatched agent 因 session 限額等外部因素中斷時，重跑的槓桿是控制「讀取方式」（先 glob／grep 掌握結構、只精讀關鍵檔），不是縮小掃描範圍 — 縮範圍會讓產出失去完整性 (learned 2026-08-08) <!-- cid:reverse-engineering:c5 -->
- pipeline 各環之間以 scratchpad 檔案傳遞大型中間結果並給下一環路徑，不把全文貼進 brief — 符合 stage-protocol §11 的 context budget（artifacts by path），也讓下一環能精讀而非被動接收 (learned 2026-08-08) <!-- cid:reverse-engineering:c6 -->
- practices-promote 是整段替換 team.md 的五個 section 而非合併：lead 起草 team-practices.md 時必須逐字保留既有非空段落（如 ADR-0010 的 branch 命名與中文 commit type 表），漏寫即等於刪除既有規則且會讓 contract 的 REQUIRED_TEXT 檢查紅燈 (learned 2026-08-09) <!-- cid:practices-discovery:c1 -->
- dispatch support／reviewer agent 時，brief 明訂「認真找碴而非背書」並要求自行回 repo 實測而非轉引 codekb — 轉引會讓上游誤差原樣傳進規則層，實測才會揭露 lead 與 codekb 都沒查到的事實 (learned 2026-08-09) <!-- cid:practices-discovery:c3 -->
- 撰寫「已由上游定案、不重問」清單時，每一項都必須回頭核對該事項在**最下游**的已核可 artifact 中的具體決定，不得引用較早階段的粗略措辭 — 較晚、較具體的決策會取代較早、較籠統的表述，憑舊措辭寫清單會讓需求與已核可設計直接矛盾 (learned 2026-08-09) <!-- cid:requirements-analysis:c2 -->
- 「缺一不可」型 hard constraint（如 ADR-0006 的四面向）在 artifact 中以逐項判定表呈現，不散在各處：表格讓「是否漏項」成為可一眼核對的事實；判定為不適用的項目一律附理由，不留空白 (learned 2026-08-09) <!-- cid:requirements-analysis:c4 -->
- 驗收標準描述系統行為（要能真的失敗），「須有某某測試」屬交付條件寫進 Definition of Done — 元層次 AC（Then 存在某測試）驗收的是有沒有寫測試而非功能對不對，且實測顯示照做也可能抓不到要防的缺陷 (learned 2026-08-09) <!-- cid:user-stories:c3 -->
- 查出恆真（不可能失敗）的驗收標準時改寫而非刪除：防禦意圖通常是真的，錯的是落點層次；把它移到碰得到真實失敗面的層次（例如由 UI 層移到 API 契約層）才保住原本的防禦價值 (learned 2026-08-09) <!-- cid:user-stories:c4 -->
- 合併或刪除故事時，必須逐條確認被併故事的每一條 AC 由誰承接 — 未承接的 AC 會連同故事一起靜默消失，使其獨有的需求覆蓋落空且不易察覺 (learned 2026-08-09) <!-- cid:user-stories:user-note-1 -->
- 設計 artifact 承認某個組合是「已知風險」時，必須把該最壞情境實際畫進範例再判定可否接受 — 只在 assumptions 以文字帶過，等於在沒看過的情況下先行放行；先確認該組合是否為系統真實可達的資料狀態，再以圖本身可驗證的依據下判斷 (learned 2026-08-09) <!-- cid:refined-mockups:c4 -->
- 下游修正上游已核可 artifact 的內部瑕疵（如順序不一致）時，必須在本站 artifact 明記「這是對齊修正、非本站新定案」並說明原瑕疵 — 否則純比對兩份文件會誤判為迴歸；上游檔案本身仍不回改 (learned 2026-08-09) <!-- cid:refined-mockups:c3 -->
- reviewer 輪次上限依缺陷來源判斷而非計數：某輪的 Critical 若是上一輪修正時新引入的（而非原始 findings 的殘留），不得以「iterations 用罄即 proceed」放行 — 那等於把自己製造的缺陷交給下游；驗證輪不計入原始上限 (learned 2026-08-09) <!-- cid:application-design:c4 -->
- 出選項前先實測既有結構（build context、CI job 分工、靜態服務範圍、啟動順序），否則無法判斷選項差別：條列出來的優缺點常在實測後整個翻轉 — 本站的型別檔存放位置即是，不查 build context 時兩個選項看起來差不多，查了才發現其一會讓三條建置路徑同時壞掉 (learned 2026-08-09) <!-- cid:application-design:c8 -->
- 工作單元的切分判準是「驗證方式與失敗模式是否同類」，不是「元件該怎麼分配」：兩個元件即使有資料關係，若一個是執行期契約（端點測試）、另一個是建置期資產（CI 檢查），併入同一單元會讓「這個單元完成了嗎」同時指涉兩種不可互相替代的判準 (learned 2026-08-09) <!-- cid:units-generation:c6 -->
- 修訂 artifact 後必須回頭同步所有由它衍生的數字與引用（統計欄、對應表、交叉引用），並逐字核對引用的上游識別碼 — 本站兩次失誤皆為機械性同步失敗而非判斷錯誤：把上游殘留項的 C-7 誤記為 C-2（讓真正有風險的單元收不到警告）、修訂後未更新依它計算的 AC 數表（而下游會拿該表做排序） (learned 2026-08-09) <!-- cid:units-generation:c6b -->
- 判斷兩個工作單元該不該合併進同一個 Bolt，看的是「分開後每個都能湊出有意義的信心假說嗎」，不是元件數量的平均分配 — 湊不出假說的 Bolt（例如「回應多了兩個欄位但沒有任何讀取端」「產出一個型別檔」）沒有可展示的成果，也就沒有部署它的理由 (learned 2026-08-09) <!-- cid:delivery-planning:c3 -->
- 驗收標準的 Then 子句必須逐字拆解到驗證項，不得以概括語轉述 — 本 stage 的 Critical 即源於此：AC 的 Then 寫著「帶有與資料庫一致的值……而非因構造遺漏而缺失或為 null」，那個「或為 null」正是回應模型自動補預設值的行為，上游已預見，轉譯成驗證強度表時被概括掉，導致整份設計沒有規劃任何值斷言 (learned 2026-08-09) <!-- cid:functional-design:c2 -->
- 宣告「本站新引入的缺口」前，必須先確認該缺口在機制上是否真的存在、以及上游是否已在追蹤 — 過度謹慎產生的假警報會誤導實作走上錯路（本站曾宣稱純 CSS 斷點需管理 aria-hidden 且工具鏈不會發現不一致，實際上 display:none 原生排除於無障礙樹、問題不存在，且該關切上游的無障礙檢查清單早已列項） (learned 2026-08-09) <!-- cid:functional-design:c16 -->
- 修訂 artifact 後必須以機械方式（grep）掃全檔的計數、序數與交叉引用，且 Revision 段的自述必須與實際改動一致 — 本 stage 同型失誤三次：狀態數由三擴為四後序數引用未同步，使同一詞在同一檔內指向兩個不同狀態；Revision 段宣稱選項描述「已更正」但選項本文未被編輯，等於把要消除的矛盾換個位置留著。既有的「同步衍生數字與引用」規則不夠具體，本條為其強化 (learned 2026-08-09) <!-- cid:functional-design:c17 -->
- 下游查證推翻的是選項的理由而非決定本身時，只修理由不改決定：以 Revision 段記錄落差的來源與拆解，原答案與選項本文均不改寫，並在不成立的句子就地標註 — 本 stage 四題適用此形狀（依據被推翻但決定仍正確） (learned 2026-08-09) <!-- cid:functional-design:c22 -->
- Proto-Unit／工作單元之間的排序約束必須區分「技術依賴」與「避免重工」兩種性質並明寫是哪一種 — 前者不可覆寫，後者可由下游在記明重工緩解方式的前提下覆寫；兩者在依賴圖上長得一樣，不區分會讓下游把經濟性排序當成不可動的 DAG 邊（本次 PU-6 分頁對 PU-5 卡片改造即為後者：分頁不需等任何前置，但卡片若先以「一次拿到全部」設計完成就要重做） (learned 2026-08-10) <!-- cid:scope-definition:rev2-c8 -->
- 改變 API 回應契約的能力不得被歸類為顯示類能力的完成條件 — 它有自己的驗收面（回應形狀、型別契約、各消費端的呈現）與失敗模式，埋進顯示類能力的 Definition of Done 會使它在單元切分時失去可追蹤的獨立身分，並低估其跨層影響（本次分頁看似「頁面怎麼呈現清單」，實際同時改序列化、型別產生與前端三層） (learned 2026-08-10) <!-- cid:scope-definition:rev2-c1 -->
- 新增的能力若與某個已列入 Won't Have 的項目同屬一個功能家族，必須在能力定義與排除項兩處都明寫「這是本次新增的唯一該家族互動」— 否則下游會把單一新增讀成整類已解禁而自行補上其餘項（本次分頁與「不做互動排序／篩選」即同屬清單互動家族，該排除項是 intent-capture 階段定案的） (learned 2026-08-10) <!-- cid:scope-definition:rev2-c2 -->
- 引用 intent 的核心價值來支撐任何設計主張前，必須回上游 artifact（intent-statement、scope-document）**逐字核對並掛上來源標籤** — 不得憑印象重述，更不得把**現行實作的副作用**誤認為產品需求（本次把「清單不分頁所以能一次看完」這個技術現況，寫成「核心價值是一眼看出哪些帳號逾期」，而上游實際記載的是**逐帳號**的稽核證據取得；該無來源主張隨即成為一整套「分頁損害核心價值、故需補償」論證的唯一基礎，並一度寫進本規則層） (learned 2026-08-11) <!-- cid:rough-mockups:rev1-c1 -->
- 判斷一項修改「是否需要重新取得人工確認」之前，必須先回頭確認**上次確認的內容本身是否自洽** — 若上次確認的集合內部已有矛盾，以「operative 內容未變」為由跳過重新確認是無效判準，因為那個比較基準本身不成立；修掉矛盾即構成實質變更（本次三條假設中第 1、2 條已改為「不採用」而第 3 條仍述其行為，確認是在該矛盾狀態下取得的） (learned 2026-08-10) <!-- cid:rough-mockups:rev1-c5 -->
- 修正若涉及已被逐字轉錄到他處、或已完成人工確認的內容，傳播範圍必須一路追到**最下游的確認點**，不能只改來源 — 否則矛盾會被鎖進已核可的紀錄（本次同一決策變更在三份檔案有七處落點，連續四輪審查每輪只補上其中幾處） (learned 2026-08-10) <!-- cid:rough-mockups:rev1-c10 -->
- 沿用既有 artifact 的格式或更正慣例前，必須先量測既有樣本的**實際**慣例，不得套用自己認為更正確的標準、也不得把別份檔案用過的手法搬過來（本次兩次違反：ASCII box 既有慣例是 len() 字元數而我用顯示寬度；更正標記既有慣例是區塊級 addendum 而我套用了別檔的行內刪除線） (learned 2026-08-10) <!-- cid:rough-mockups:rev1-c15 -->
- 上游範圍擴充後重審 Go/No-Go 或可行性判定時，不得因「範圍變大」就自動下修信心 — 須逐項對照可行性面向（是否引入新服務／新依賴／新基礎設施／新技術層）給出判定與理由（本次分頁改的是既有端點的回應契約與兩種佈局呈現，AD-5 維持成立，故 GO 不變） (learned 2026-08-10) <!-- cid:approval-handoff:rev1-c2 -->
- 引用程式碼行為作為需求或設計的前提時，必須逐一函式核對而非整批概括 —— 「這幾個操作都是 X」這種合併陳述是誤述的高發形狀（本次三個看似同類的前端操作，實際一個就地更新、兩個整份重抓）；讀過檔案不等於核對過，引用時一律附檔名與行號讓下游可機械複驗 (learned 2026-08-10) <!-- cid:requirements-analysis:c3 -->
- 同一則故事的兩條 AC 互相牴觸時，「把衝突記進 Assumptions 並指派下游決定」只做到 surface、沒做到 resolve（phases/inception.md 要求兩者皆須）—— 正確處置是在 AC 本文加上適用前提使字面不再衝突，同時把收斂手段明列為下游的**開放決策**而非被動記載的已知限制；兩者缺一都會讓下游把待決事項讀成已定案 (learned 2026-08-11) <!-- cid:user-stories:c9 -->
- 引用工具鏈設定值（Tailwind 尺度、lint 規則、建置參數）前，必須先確認**哪一份設定檔真的生效**再讀它 —— 本專案的 `frontend/tailwind.config.js` 在 Tailwind v4 下未被任何 `@config` 載入、是死碼，實際生效的是 `src/index.css` 的 `@theme`；能實際編譯驗證的數值（如 `min-w-11` 是否等於 44px）就直接編譯驗證，不停在假設 (learned 2026-08-11) <!-- cid:refined-mockups:c1 -->
- 為新行為指定「沿用既有機制」之前，必須先寫下該既有機制的副作用是否與新需求的意圖相容 —— 缺口的共同形狀是：交界沒被寫下來，於是預設沿用，而既有機制的副作用正好破壞新需求（本次：刪除後重抓若沿用既有的 fetchUsers()，會每刪一列閃一次整頁載入，字面通過 AC 但打斷工作流） (learned 2026-08-11) <!-- cid:application-design:c15 -->
- 引用「既有為 N 條」這類基準數時，那個 N **也要重數**，不能只重數本輪新增的部分 —— 本 intent 已在同型失誤上重複三次；另：箭頭鏈（A → B → C）是順序的語法，在禁止建議實作順序的 stage 用它說明「約束規模」等於在排序 (learned 2026-08-11) <!-- cid:units-generation:c9 -->
- deploy-on-merge 之下，破壞性契約變更與其消費端之間存在一條隱含的「同批次」約束，**它比 DAG 邊更強** —— DAG 只說先後，這條說不得分批。它不出現在依賴圖上，只有把「每個 Bolt 邊界都是一次真實部署」實際代入才會浮現；凡涉及既有端點回應形狀變更的 Bolt 切分，都必須先問這一句 (learned 2026-08-11) <!-- cid:delivery-planning:c6 -->
- 上游已定失敗路徑（如 API 缺價走 Manual Override）時，同類缺口（圖上無 SKU 對應）不另開題，預設走該路徑，並在日記註明視為同一失敗家族 (learned 2026-08-19) <!-- cid:feasibility:c3 -->
- feasibility 不重問 intent-capture 已核可的產品邊界（官方 API、本輪切片、覆寫規則、預算與警告、入口、不做的核准流、憑證禁令）；只問解鎖可行性的整合與權限張力 (learned 2026-08-19) <!-- cid:feasibility:c7 -->
- Standard 深度的 feasibility 優先問官方 API 存取策略、雲別覆蓋、既有驗收與本輪切片的張力、預算掛載粒度、誰能改數字、通知原語上限；可併入既有題之後果（如價目 freshness）不另開題 (learned 2026-08-19) <!-- cid:feasibility:c8 -->
- 「都要能報價／都能用」這類成語與存取策略（公開免帳號 vs 必須帶金鑰）衝突時，必須加開追問把成語定錨為「畫面可用」還是「官方 API 覆蓋」，不得讓兩題並存不明 (learned 2026-08-19) <!-- cid:feasibility:c9 -->
- ALWAYS 當 intent 含使用者可見的成本／估價畫面、Sidebar 入口、產圖後 CTA 或進產品橫幅時，判定 rough-mockups 的 user-facing UI condition 適用並執行，把判定理由記入 diary (learned 2026-08-19) <!-- cid:rough-mockups:c7 -->
- ALWAYS 在 rough-mockups 不重問上游已定案的產品能力（是否做圓餅、inbox、Sidebar 是否按故事大類分層）；已決項列在問題檔前言與 diary (learned 2026-08-19) <!-- cid:rough-mockups:c8 -->
- ALWAYS 當產品邊界已鎖時，rough-mockups 優先只問這六類：資訊層級、CTA 落點、超支畫面標示、覆寫操作、無障礙／裝置、第二段預算區塊位置 (learned 2026-08-19) <!-- cid:rough-mockups:c6 -->
- ALWAYS 權限種子或權限頁欄名可先於產品面存在（如 C1 view/edit）；codekb 與設計必須標明「矩陣領先實作」，不得把種子當成已有 router／頁／表 (learned 2026-08-19) <!-- cid:reverse-engineering:c9 -->
- Requirements Analysis 對上游已鎖定的產品決策（範圍增量、公開價目、未定價列、權限語意、橫幅、三層模組、測試底線）不重問；本站只補 codekb 證明仍缺的可測不變量 (learned 2026-08-19) <!-- cid:requirements-analysis:c20 -->
- 超支橫幅要求「每次進入產品都看到」且本輪無 inbox 時，估價／時數／覆寫／預算必須伺服器持久化；不得把跨登入橫幅建立在瀏覽器暫存上 (learned 2026-08-19) <!-- cid:requirements-analysis:c21 -->
- 可行性階段已鎖定的稽核（誰、何時、舊值、新值）在 Requirements Analysis 寫成可測 FR，不重問「要不要稽核」 (learned 2026-08-19) <!-- cid:requirements-analysis:c22 -->
- 估價區域與每日時數同屬架構假設：由架構師設定／修改，非該角色 API 403；變更權清單須與時數、預算、單價覆寫一併列入設計 OQ (learned 2026-08-19) <!-- cid:requirements-analysis:c23 -->
- 「跟圖走」的估價列以目前架構圖 XML 每次重擷取、以 mxCell id 對齊；該 id 的時數與 FinOps SKU／單價覆寫保留，已刪節點的列與覆寫移除 (learned 2026-08-19) <!-- cid:requirements-analysis:c24 -->
- 圓餅、CTA、C2／C3、inbox、核准流、價目憑證等 ideation 已定案題在 Requirements Analysis 省略；價目快取／重試手段留設計，不在本站預選 (learned 2026-08-19) <!-- cid:requirements-analysis:c25 -->
- 當既有擷取沒有 SKU／區域／時數預設時，Requirements Analysis 必須問出 calculator 不變量：SKU 對應、區域與幣別、預設時數、圓餅切法、多圖橫幅、時數換月費公式 (learned 2026-08-19) <!-- cid:requirements-analysis:c26 -->
- User Stories 必做：C1 是使用者可見功能、三個已確認 persona、兩段 Must 增量。不 skip (learned 2026-08-19) <!-- cid:user-stories:c30 -->
- 可參考 baseline C 柱時沿用 C1 編號與 Alex／David／Hannah；C2／C3 不進本輪 backlog。C1 內文以該 intent 的 requirements.md 覆寫，不照抄 baseline 的時數預設、流量模型或 inbox (learned 2026-08-19) <!-- cid:user-stories:c31 -->
- C1 入口故事過大時拆成入口擷取／官方價圓餅／產圖 CTA 三則 Must，其餘時數／覆寫／預算／超支順延編號；AC 前綴跟故事號走以免撞號 (learned 2026-08-19) <!-- cid:user-stories:c32 -->
- 每日時數合法值為整數 0–24（含）；空白／非數字／非整數／區間外不送出並有文字錯誤；Hypothesis 的 h domain 同步鎖定 (learned 2026-08-19) <!-- cid:user-stories:c33 -->
- User Stories reviewer 的 Minor 在 READY 後可折入：Sidebar 標籤以畫面實文為準、涵蓋欄補齊已測 FR、無公開端點雲的官方價呼叫次數寫進 DoD；稽核 HTTP 路徑可留 application-design (learned 2026-08-19) <!-- cid:user-stories:c34 -->
- Refined Mockups 在已有線框時不重問層級／CTA／超支標示／就地編輯／AA；只問線框未釘死的實作（圓餅依賴、時數控件、橫幅釘點、SKU 密度、視覺契約） (learned 2026-08-19) <!-- cid:refined-mockups:c20 -->
- C1 成本頁沿用既有 Tailwind 與 Layout；圓餅自畫 SVG 不新增圖表套件；建議路由與 test-id 可寫進 mockups，精確 path 留 application-design (learned 2026-08-19) <!-- cid:refined-mockups:c21 -->
- Refined Mockups reviewer 指出的畫面缺口（全未定價結構、多圖橫幅可見字串、區域控件是 select 還是 input）應在 READY 後補進 mockups／interaction-spec，不要只留在 Review 表 (learned 2026-08-19) <!-- cid:refined-mockups:c22 -->
- 已超支後要以與 A1／A3 相同路徑的 AI agent 提供修改建議；此為後續 intent，不得在已核可的 C1 橫幅範圍內夾帶 LLM 建議 (learned 2026-08-19) <!-- cid:refined-mockups:c23 -->
- Application Design 在已鎖定三層 cost 形狀時不重問風格；本站只凍結權限掛載、持久化表、價目快取、SKU 對照與稽核 HTTP (learned 2026-08-19) <!-- cid:application-design:c20 -->
- 新增 story id 時不得依賴 ensure_role_permissions_seeded(force=False)：該函式在表非空時整段 no-op，必須另做只插入缺失 (role, story_id) 的 ensure (learned 2026-08-19) <!-- cid:application-design:c21 -->
- 公開價目 Port 必須能區分「本輪無端點」（不發 HTTP、列未定價）與「有端點但失敗」（官方價取得失敗）；第一段不註冊超支橫幅路由 (learned 2026-08-19) <!-- cid:application-design:c22 -->
- Units Generation 在新 bounded context（新表、library、HTTP、頁、第二段 UI）時必做 DAG；本站只定拓樸與可平行根（depends_on: []），不推薦施工順序 (learned 2026-08-19) <!-- cid:units-generation:c20 -->
- 同時含第二段 HTTP 與 Layout DOM 的 unit 可省略 kind（完整設計矩陣）；API／UI 契約以 OpenAPI dump 與 generated api.d.ts 為準。初選手寫型別若與 CI drift 閘衝突，必須追問覆寫，不得讓兩種契約並存 (learned 2026-08-19) <!-- cid:units-generation:c21 -->
- units-generation 的 yaml 邊只列本 intent 待建 unit；已存在的 brownfield 模組寫在散文前提、不進 compiler。AC 數對上游標題列重數 (learned 2026-08-19) <!-- cid:units-generation:c22 -->
- 2.7 約束表須就地註明非 Bolt 順序；上游 AC 跳號在 story-map 註明且不回改已核可 stories；跨 unit DOM 擴充機制留給 functional-design (learned 2026-08-19) <!-- cid:units-generation:c23 -->
- Delivery Planning 不重問 practices-discovery 已核可的 walking-skeleton 立場。第一段可單獨上線的故事應把 OpenAPI 契約與 UI 消費端捆進同一 Bolt（deploy-on-merge 同批）；單拆 schema 或 library 若湊不出可展示的信心假說則不合閘 (learned 2026-08-20) <!-- cid:delivery-planning:c20 -->
- 手動測案數判定為 0 時，`manual-test-cases.md` 仍須逐項列出外部可觀察行為與分桶理由 — 空檔或一句「無手動案例」會被下一個人讀成漏寫而非判斷，而分桶本身才是這個 stage 的產出 (learned 2026-08-19) <!-- cid:tcms-test-cases:c1 -->
- 撰寫標準 §4.4 的規格註解隨語言換載體（TS 用 `/** */`、Python 用 docstring），但 `@api`／`@ui` 在受測對象既無端點也無 UI 時寧可缺、不得捏造 — 假端點會通過機械比對而無人察覺，並讓下一個改該 API 的人誤以為此案例與他有關 (learned 2026-08-19) <!-- cid:tcms-test-cases:c20 -->
- intent-capture 的 `## Sources` register 只接受 `[desc]`／`[scope]`／`[memory:M<n>]` 三種形式，且 stage 檔明文禁止登錄背景知識與推論；出題前的唯讀查證結果改放獨立區塊並標明非來源，供題幹與選項引用而不進 register。此為 intent-capture 專屬，與 feasibility 階段「查證結果登錄於問題檔 `## Sources`」那條並存，不互相取代 (learned 2026-08-23) <!-- cid:intent-capture:c3 -->
- stage 檔要求必填但未解的欄位寫成 `Unknown (open question) [assumption]`，但 claim-sources sensor 會把 `## Assumptions & Open Questions` 區塊外的 `[assumption]` 判為違規，兩者直接矛盾；處置是整列移除該筆並以 HTML comment 記錄省略理由與其無來源的事實，同時確認該缺口已由 Assumptions 區塊承接 (learned 2026-08-23) <!-- cid:intent-capture:c4 -->
- 答案收齊後除了矛盾偵測，還要做一次覆蓋檢查：把已定案的驗證計畫逐條對照已定案的最高風險失敗模式，確認兩者有交集。彼此不矛盾但合起來不足的組合（驗證計畫涵蓋不到最可能的失敗）不會被矛盾偵測抓到——本輪 Q6 的驗證計畫與 Q3 的靜默錯綁風險就是零交集，只有主動覆蓋檢查才問得出 Q10 (learned 2026-08-23) <!-- cid:feasibility:260822-c1 -->
- 宣稱某事「已由上游定案」並據此省略提問時，必須能引用該定案的具體選項字母或原文；引用不出來就代表它未被定案，應補問而非推論。既有那條「須逐字核對最下游的具體決定」講的是核對動作，這條講的是可引用性——後者是前者的可執行檢查，沒做到就會像本輪一樣把未選中的選項當成已定案 (learned 2026-08-23) <!-- cid:scope-definition:260822-c5 -->
- 修訂 artifact 時，既有的人工確認只涵蓋它作答當下存在的清單；修訂新增的項目必須另行取得確認，不得沿用舊確認寫成「已接受」。沿用等於讓 artifact 宣稱使用者接受了他從未看過的內容——這與「不得摘要或代答使用者輸入」是同一條紀律的兩面。判斷方式：逐項核對該確認題作答當下的清單，不在其中的即為新增項 (learned 2026-08-23) <!-- cid:approval-handoff:260823-rev1-c1 -->
- reverse-engineering 做定向重掃（非全 repo 重掃）時，`reverse-engineering-timestamp.md` 必須立新鮮度等級標記並在各 artifact 逐節標註——整份 codekb 呈現同一新鮮度，會讓下游把未重新推導的大半內容誤當成本輪結論 (learned 2026-08-23) <!-- cid:reverse-engineering:260822-re-c1 -->
- codekb 內每一項事實都必須標明取得方式與證據強度（實讀 diff／僅 diffstat 推得／靜態計數／實際執行結果），不得混列——本輪的「0 errors, 3 warnings」與兩支 validator「passed」實為沿用舊基準、本輪未複驗 (learned 2026-08-23) <!-- cid:reverse-engineering:260822-re-c2 -->
- 問題檔的某題選項數超過 harness 上限（AskUserQuestion 每題 4 個）時，先把問題檔本身收斂成 4 個並記明合併方式，再提問；不得提問時臨時換一組。問題檔是 stage 的正式來源，下游與 reviewer 都拿它複驗，若它寫 5 個而實際只問了其中 4 個，同一個 `[Answer]: A` 在兩份紀錄中指向不同內容且無人會察覺 (learned 2026-08-23) <!-- cid:requirements-analysis:260822-ra-c2 -->
- 某個結果若是多項已核可決定各自逼出的唯一解（本輪：CAP-1、Q6=A、ADR-0013 §2 三者都需要 repo 內容寫入權），不出成題目——那會是單一可行解的假選擇，讓紀錄看起來像有人選過而實際沒有。改為在 Consolidated Summary Confirmation 明白揭露其後果，含它比上游當時預期更大或更重的部分，讓使用者在按下 Looks correct 前看到 (learned 2026-08-23) <!-- cid:requirements-analysis:260822-ra-c5 -->
- 在 Consolidated Summary Confirmation 取得之後才作答的追問（典型來源是 reviewer findings 觸發的補問），其確認缺口是結構性的、不需要判斷——比對 `[Answer]` 註解與確認區塊的時間戳即可機械判定。處置是新增追問的同一個動作就補進確認清單並清空 `[Answer]:` 重新取得確認，不是等下一輪 reviewer 來抓。既有的 approval-handoff:260823-rev1-c1 講的是判斷原則，本條給它零判斷的觸發時機與機械檢查 (learned 2026-08-23) <!-- cid:requirements-analysis:260822-ra-L3 -->
- 寫入任何時間戳（`[Answer]:` 註解、artifact 內的 ISO 時間、決議紀錄）前一律執行 `date -u` 取值，不得憑感覺寫一個看起來合理的時間。本 stage 全程的作答時間戳皆為編造，其中一個落在當時真實時間之後 56 分鐘、且出現在一段目的正是聲明「這不是事後補授權」的註記裡，被 reviewer 以 audit shard、檔案 mtime 與 `date -u` 三項機械證據抓到。AIDLC 的整套 audit shard 與 `[Answer]` 時間戳都預設它們是真實時刻——編造值平常不會被發現，一旦被發現，污染的是稽核紀錄的可信度本身而不只是那一行 (learned 2026-08-24) <!-- cid:user-stories:260822-us-L1 -->
- 人工裁決一取得，就在同一個動作內寫回問題檔並執行 `aidlc-log.ts answer`，不得延後到整合完成之後。機械檢查：每次 AskUserQuestion 回來後，下一個工具呼叫必須是寫回＋log。既有的 `requirements-analysis:260822-ra-L3` 講的是「確認之後才新增的追問」，本條講更基本的「答案拿到了但整輪沒寫回」——本 session 已在 requirements-analysis 與 user-stories 各犯一次，且第二次的補救（用編造時間戳補記）比原缺口更糟 (learned 2026-08-24) <!-- cid:user-stories:260822-us-L2 -->
- 當人工輸入的底層事實為真、但因自己的疏失而在 artifact 上無法被證實時，正確處置是向使用者說明並當場重新取得一次可驗證的裁決，不是堅持既有說法。理由：從紀錄上看，「堅持」與「造假」無法區分；重取的成本遠低於讓下游繼承一份無法查證的授權。判斷方式：若 reviewer 或任何第三方只憑 artifact 與 audit 無法重建該授權，可驗證性即已損壞 (learned 2026-08-24) <!-- cid:user-stories:260822-us-L3 -->
- 改動任何已產出的 artifact 之前，先列出「本輪要改動的每一個主張」；改完逐一 `grep` **全部**產出檔確認無殘留、無新矛盾，而不是改完再回想哪裡可能提過。本站 reviewer iteration 2 的 6 項發現與 iteration 3 的 1 項新發現**全部**是跨檔傳播失敗（改 `decisions.md` 沒改 `components.md`／`component-methods.md`、改 `services.md` 的 concurrency 沒改 `components.md`、改選取演算法沒改另兩檔的資料流敘述、補標籤時沒注意同表下方已有排除說明），沒有一項是新的設計錯誤。既有的 `units-generation:c6b` 只涵蓋「同步衍生的數字與引用」，不涵蓋「跨檔案傳播同一個決定的改動」。附帶：掃查腳本本身也要驗——本站第一版有 shell 引號與 Python bug，且把表格簡寫（`FR-B1、B2、B3` 前綴只掛第一個）誤報為未覆蓋 (learned 2026-08-24) <!-- cid:application-design:260822-ad-L1 -->
- 當自己的修法偏離 reviewer 的建議時（例如以單一上游修法同時解掉它分別建議的兩項），在下一輪 brief 中主動點名該偏離並要求它最用力打。偏離建議本身沒問題，但**沒有揭露的偏離**會讓下一輪 reviewer 把它當成已驗證過的部分而略過。本站主動請它攻擊的結果，正好引出 lead 沒想到的問題（registry 驅動的選取把首建路徑排除，使 Must 級的 FR-A1 永不觸發） (learned 2026-08-24) <!-- cid:application-design:260822-ad-L2 -->
- 使用者對某題的回覆若是**重新框定**而非選項之一，先查證他提出的幾條路是否等價，再決定要直接採納還是追問。本站 Q1 的回覆是「AI-DLC extension/skill 或共用 gh-aw 都行」，查證後發現兩者落在剛收窄規則的兩側、且前者（人在迴圈內觸發）與已核可的 FR-B4（push／PR 觸發）與 NFR-P1（推送後 5 分鐘）直接牴觸——不是同一個產品的兩種包裝。若直接挑一條，等於替使用者做了一個他不知道自己在做的選擇 (learned 2026-08-24) <!-- cid:application-design:260822-ad-L3 -->
- 跨檔掃查要按**事實**列舉，不是按「本輪改過的字串」grep。改動一個事實前，先問「這個事實在本站產出裡有幾種表達形式」，把每一種的**定位方式**（表格名或欄位名，而非字串）列出來，逐一開啟確認。既有的 `application-design:260822-ad-L1` 已要求「改動前先列主張清單、改完逐一 grep 全部產出檔」，本站照做了仍漏——因為同一個事實在三張表用三種形式表達（主對照表寫「S-2 AC 4 → U-1 ＋ U-7」、跨單元表寫「S-2 橫跨 U-1、U-6」、覆蓋表寫「U-7 承載 S-2」），grep 改過的字串只命中第一種。這是本 intent 第三次同型失誤，且發生在既有教訓寫入之後，代表那條的可執行性不足，本條為其補強 (learned 2026-08-28) <!-- cid:units-generation:260822-ug-L1 -->
- 發現已核可上游的契約缺口時，處置形狀為：**標出缺口、寫明它讓哪一條 AC 目前不可滿足、指派具體落點與具體修法**，不逕自修改已通過 reviewer 的上游產出。**附帶必做的檢查**：若指派的目標 stage 為 `CONDITIONAL`，必須額外註明「該 stage 可能被 skip」的風險並指出誰要確認，否則指派會無聲落空。本站的實例是 [US:S-2 AC 4] 要求對帳報告有「無法判定」清單而 `ReconcileReport` 只有 `unparseable`（兩個 `reason_code` 不能互相頂替），指派 functional-design 增設 `undecidable: [intent_id]`——而 functional-design 恰好是 CONDITIONAL 且 per-unit (learned 2026-08-28) <!-- cid:units-generation:260822-ug-L2 -->
- 拆分、新增或刪除任何**被計數的實體**（單元、邊、故事、約束、選項）時，「總數」本身就是一個受影響事實，必須列進改動前的清單並逐一 grep。既有的 `application-design:260822-ad-L1` 要求列出「本輪要改動的每一個主張」、`units-generation:260822-ug-L1` 要求「按事實掃、不按改過的字串掃」——本輪兩條都照做了仍漏兩處，因為總數不是我**改的**主張，是改動的**衍生後果**，兩條規則的字面都沒涵蓋它。可執行檢查：改完後對每一類被計數的實體各跑一次「舊數字」的 grep，命中處若不在歷史敘述或他人引用段內即為殘留。本輪的兩個 Major（`unit-of-work.md` 的「11 個單元…唯一原因」、story map 的「無空單元——11 個單元」）皆屬此形，為本 intent 第四次同型失誤 (learned 2026-08-29) <!-- cid:units-generation:rev1-L1 -->
- 寫下任何**可以被計算的數字**之前先實際算一次，尤其是自己覺得「顯而易見」的那種。本站在修訂對照表寫「雙向讀法下仍是 8 個（U-10a 進該批、U-10b 移出，一進一出）」，union-find 實算是 **9**（兩者各自併入同一群組，都在裡面）。根因不是懶得算，是對「一進一出」有直覺就沒去驗——而直覺產生的數字與算出來的數字在文件上長得一模一樣，讀的人無從分辨。與 `units-generation:260822-ug-L1`（改動後要重掃衍生計數）同根但管不同時點：那條管「改完要重掃」，本條管「寫下去之前要先算」。可執行檢查：任何出現在 artifact 裡的數量、比例或集合大小，都要能指出它是由哪一段程式或哪一次命令算出來的；指不出來就是還沒算 (learned 2026-08-29) <!-- cid:delivery-planning:dp-L1 -->
- 新增任何「偵測 X 狀態」的規則之前，先推導 X 在該系統的資料流下**是否可達**——不可達的規則是死碼，卻在文件上長得像「已解決」，純比對規則文字的核對抓不到。可執行檢查：寫下該狀態成立所需的每一步寫入路徑；若其中任一步只能透過某個前置事件發生，把該事件代入規則的觸發條件，看兩個子句會不會自相矛盾。本輪實例：`pending_reverse` 的寫入騎在反向分支上，故它在 `ut` 上非 `null` 等價於「有一則反向 PR 合併過」，於是「非 `null` 且從未有過 PR」永不同真——而該規則當時已被指派給 U-7 實作。附帶：這個缺陷是**修正上一輪 Critical 時引入的**，所以修正動作本身也要過這道檢查 (learned 2026-08-29) <!-- cid:functional-design:c10 -->
- 判斷一個對抗式審查迴圈要不要再跑一輪，判準是「新缺陷從哪來」而不是「還剩幾個」——在 reviewer brief 中要求它對每項發現分類（新引入／既存漏審／新設計問題）並在 Summary 給三類計數。缺陷總數會因為審查挖得更深而上下震盪（本 stage 五輪為 4→6→8→4，看起來像收斂），但「由前一輪修正動作造成」的佔比才區分得出「審查在挖深」與「修正在製造」。該佔比若持續不降（本 stage 末輪為 26／38＝68%），再跑一輪的期望值是「修好 N 項、新增 0.7N 項」，應停止迴圈、把已定位的缺口寫成 open-items 登錄帶進閘門，而非繼續補丁。成本只是 brief 多兩句話，且停止判準應在該輪**開始前**與人商定，不要事後才決定 (learned 2026-08-30) <!-- cid:functional-design:c18 -->
- 修正一條已核可 AC 的違反時，先盤點「這條 AC 的違反面共有幾個入口」，不要只修 reviewer 引用的那一行——修在單一入口會把違規從一個位置挪到另一個位置而不是消除它。可執行做法：找出該 AC 所約束的行為（例如「不對其產生任何看板寫入」），列出程式流程中所有能產生該行為的分支，確認閘門位在**全部**分支的共同上游；若閘門所需的資訊（如判定結果）在某些分支尚未算出，那就是閘門放錯層，應把該資訊的計算上提，而不是在下游多加一條例外 (learned 2026-08-30) <!-- cid:functional-design:c34 -->
