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

## Scope Overrides

- ✅ **In scope**：SRS、architecture diagrams、user stories、ADRs、IaC generator design、agent routing design、MCP/skill management spec、validation scripts、baseline CI、自有 staging 的部署與維運。
- ❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。

## Forbidden

- NEVER 讓版控中**存在** path parts 含 `prod`、`production`、`secrets` 的檔案 — `scripts/validate_repo_contract.py` 的 `validate_no_production_config_added()` 會擋（CI 紅燈）。檢查方式是對 `git ls-files` 做**全域掃描**（不是 diff 基準），所以不限於本次新增的檔案：任何已納入版控的違規路徑都會讓檢查紅燈，且在 CI 的乾淨 checkout 下與本機行為一致（issue #509）。比對為 **path-part 精確比對**且不分大小寫，因此 `aidlc-product-agent.md`、`secrets-policy.md` 這類含子字串但非完整 path part 的檔名不受影響。
- NEVER commit 私鑰或 AWS / Azure / GCP 的 credential 字串。實際被擋的樣式列在 `scripts/validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS`（涵蓋私鑰 PEM 標頭與三雲的 secret 環境變數）。**不要把那些樣式照字面複製到任何 contract 檔案裡** — 掃描器不分辨「示範」與「洩漏」，會直接紅燈。
- NEVER 在未取得 human approval 的情況下執行 production write、IaC apply 或 IAM 變更。
- NEVER 直接編輯 `.claude/` 下的 upstream 框架檔來表達專案規則 — 專案規則一律寫在 `aidlc/spaces/<space>/memory/{team,project}.md`，否則下次升級會被整批覆蓋。

<!-- practices-discovery 2026-08-09：本節本次無新發現（affirm 紀錄，非規則）。 -->

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
- 在 Cursor harness 執行 AIDLC 核准閘時：因無 Claude Code UserPromptSubmit hook，conductor 在呼叫 `report --result approved` 前須先執行 `bun .claude/hooks/aidlc-mint-presence.ts`，確保 audit 有對應 HUMAN_TURN（使用者須已在對話中明確核准）。 (learned 2026-08-06) <!-- cid:requirements-analysis:c2 -->
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
- 手動測案數判定為 0 時，`manual-test-cases.md` 仍須逐項列出外部可觀察行為與分桶理由 — 空檔或一句「無手動案例」會被下一個人讀成漏寫而非判斷，而分桶本身才是這個 stage 的產出 (learned 2026-08-19) <!-- cid:tcms-test-cases:c1 -->
- 撰寫標準 §4.4 的規格註解隨語言換載體（TS 用 `/** */`、Python 用 docstring），但 `@api`／`@ui` 在受測對象既無端點也無 UI 時寧可缺、不得捏造 — 假端點會通過機械比對而無人察覺，並讓下一個改該 API 的人誤以為此案例與他有關 (learned 2026-08-19) <!-- cid:tcms-test-cases:c20 -->
