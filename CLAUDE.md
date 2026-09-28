# CLAUDE.md — Cloud-360

> Project guidance for Claude Code and other AI coding agents working in this repository.
> 給在此 repo 工作的 Claude Code 與其他 AI coding agents 的專案指引。

---

### 1. 專案定位

Cloud-360 是 AI-native multi-cloud architecture & operations platform，支援 AWS / GCP / Azure。
專案以 **Spec-Driven Development (SDD)** 為方法論基礎（SRS、user stories、architecture、ADRs），開發與運維以連續流程進行，目前具備：
- 可運行的 backend（FastAPI）與 frontend（React / Vite）實作；
- 有 CI pipeline（repo contract、lint、build、Docker build）與自動化部署至自有 staging 環境（`192.168.10.10`，經 Cloudflare Tunnel 對外開放 `cloud360.danniel.cc`，見 ADR-0007）；
- 日常開發由一組 agentic workflows（gh-aw）輔助（contract 驗證、PR review、UI 回歸測試、部署失敗自癒、spec↔code 一致性、本機開發文件漂移等）；
- 測案管理走自架 Kiwi TCMS（`tcms.danniel.cc`，於 `dc-infra` repo 維運）。

各階段的細部狀態以作用中 intent 的 `<record>/aidlc-state.md` 為準（目前 baseline record 為 `aidlc/spaces/default/intents/260802-default/`）。**production**（雲端供應商正式環境）仍在範圍外，見第 5 章與 ADR-0007。

### 2. AI-SDLC 框架：AIDLC v2

本專案採用 [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows) 的 **v2** 作為主要 AI-SDLC 開發方法論。版本以 `.claude/tools/aidlc-version.ts` 的 `AIDLC_VERSION` 為準（`/aidlc --version` 可查）。

**啟動口令**：當 user 以 `Using AI-DLC, ...` 起頭、輸入 `/aidlc`，或要求做需求分析、設計、實作、IaC 產製、運維時，**必須**遵循 AIDLC 工作流程，而非預設工作流程。

**Entry point 與 rule loading 順序**：

1. Skill 入口 `.claude/skills/aidlc/SKILL.md`（`/aidlc` 觸發）；框架細節與工作區結構見 [`.claude/CLAUDE.md`](.claude/CLAUDE.md)。
2. 方法／規則層由引擎自 `aidlc/spaces/<active-space>/memory/` 解析，五層 **strict-additive**：`org → team → project → phase → stage`。
   - `org.md` — 框架預設與組織層護欄（upstream 檔，英文；本專案僅校正 trunk 與部署段落）
   - `team.md` — 本團隊實踐（branch 命名、commit message、文件語言、決議紀錄）
   - `project.md` — 專案專屬特化（repo contract、範圍邊界、schema/deploy 同步、tech stack）
   - `phases/<phase>.md` — ideation / inception / construction / operation 各階段護欄
3. 較窄的層**只能疊加**，不得與較寬的層矛盾；矛盾會在 §13 learning admission check 被擋下。**專案規則一律寫在 `team.md` / `project.md`**，不要改 `.claude/` 內的 upstream 檔（升級時會被整批覆蓋）。

**常用指令**：`/aidlc <描述>`（自動偵測 scope）、`/aidlc --status`、`/aidlc --doctor`、`/aidlc --version`、`/aidlc --stage <slug>`、`/aidlc compose "<task>"`。完整清單跑 `bun .claude/tools/aidlc-utility.ts help`。

**Phases**：v2 為 initialization → 💡 ideation → 🔵 inception → 🟢 construction → 🟡 operation。實際啟用的 stage 集合以編譯後的 `.claude/tools/data/stage-graph.json` 與 `/aidlc --doctor` 為準。注意 construction 與 operation 在本專案是**連續**的，不是依序交棒（ADR-0008，見 `project.md` 的 `## Deployment`）。

**Artifacts 輸出位置**：

- **所有 AIDLC 產出** → 作用中 intent 的 record 目錄 `aidlc/spaces/<active-space>/intents/<record>/`（簡寫 `<record>/`；單一團隊只會看到 `spaces/default/`）。
- **v2 之前的歷史 artifacts** 已由引擎的 flat-layout migration 整棵搬進 baseline record `aidlc/spaces/default/intents/260802-default/`（ADR-0011）。原本的扁平 `aidlc-docs/` 目錄已不存在。
- **Audit** → `<record>/audit/<host>-<clone>.md` 的 per-clone shard，由引擎寫入，不要手動編輯。
- 應用程式碼一律放 repo 根目錄既有結構（`backend/`、`frontend/`、`scripts/`、`tools/`、`workflows/`）。

### 3. Standing Constraints（常設約束）

下列三項是本專案**永遠生效的 hard constraint**，正式來源在 `aidlc/spaces/default/memory/project.md`（`## Testing Posture`、`## Decided`、`## Mandated`）與 `team.md`（`## Mandated`）。requirements-analysis 階段不需再次詢問 user：

| 約束 | 來源 | 強制等級 |
|---|---|---|
| Security baseline | ADR-0006 | Hard constraint（IAM、encryption、network exposure、audit logging） |
| Property-based testing | ADR-0006 | Hard constraint（IaC generator、cost calculator、agent routing 等核心模組） |
| 文件語言：繁體中文 | ADR-0009 | Hard constraint（見第 4、6 章） |
| TCMS 測試案例產出 | `project.md` `## Mandated` | **Blocking**（每個 intent 的 construction 必經 `tcms-test-cases` stage；見下方） |

**`tcms-test-cases` stage**（`tcms` plugin，`execution: ALWAYS`，涵蓋全部 scope）：每個 intent 都必須產出覆蓋盤點、手動測案、自動化腳本（含突變驗證）與 TCMS 同步報告，並通過 `/tcms-verify` 驗證關卡才能標示完成。**測試案例的格式契約在 [`TESTING.md`](TESTING.md)**（不限工具，Cursor／Antigravity 使用者也適用；必要欄位清單由該檔的 `required-sections` 標記定義，`scripts/tcms_validate.py` 直接讀取，文件與程式不會分歧）。撰寫方法論在 `aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md`，工具是 `scripts/tcms_validate.py`（驗證）與 `scripts/tcms_sync.py`（同步）。它存在的理由是本 repo 的自動化層有三塊**結構性**盲區——所有 LLM 路徑、n8n 圖示取得、本機環境殘值——實測證實六道 CI 閘門全綠時仍會放行這三類缺陷。stage 檔位於 `.claude/` 之下，升級時的處理見 [`.claude/README-cloud360.md`](.claude/README-cloud360.md) 調整 3。

### 4. Repository Contract（不可違反）

本 repo 受 `scripts/validate_repo_contract.py` 約束，CI 會跑此腳本：

- **必要文件**：列在 `REQUIRED_FILES`（包含 SRS、ADRs、user stories、architecture、AIDLC v2 entry 與 memory 層、CLAUDE.md 等）
- **必要文字**：列在 `REQUIRED_TEXT`（每個 contract 文件須包含特定關鍵字）
- **文件語言**：所有 record 內的 `*.md` 一律繁體中文（見 ADR-0009），不得夾帶英文版段落
- **禁止路徑**：版控中不得**存在** path parts 含 `prod`、`production`、`secrets` 的檔案（`git ls-files` 全域掃描、path-part 精確比對，不限本次新增）
- **禁止內容**：不得 commit 私鑰、AWS / Azure / GCP credential 字串

**違反 contract = CI 紅燈**。在 commit 前一律先跑 `python3 scripts/validate_repo_contract.py`。

**環境設定 contract（第二支腳本）**：`scripts/validate_env_contract.py` 同樣在 CI 的 `repo-contract` job 執行，管的是**三個環境的設定不得互相混用、也不得互相漏接**：

| 範圍 | 設定來源 | 消費者 |
|---|---|---|
| 本機 dev | `backend/.env`、`frontend/.env`（範本 `*.env.example`） | bare-metal uvicorn + vite |
| CI 測試 | `deploy/docker-compose.test.yml`（值全內嵌且有預設） | `ui-regression` 短生命週期 stack |
| 部署 | `deploy/.env`（由 `deploy/render-env.sh` 產生，範本 `deploy/.env.example`） | `deploy/docker-compose.deploy.yml` |

它檢查六件事：deploy workflow 不得繞過 `render-env.sh` 自行寫 `deploy/.env`；compose 無 fallback 的變數必須真的被寫入；部署範本必須完整；範本不得設定 compose 自行推導的值（`DATABASE_URL`、`VITE_API_BASE_URL`）；dev 與部署設定不得互相滲透（localhost 來源、`POSTGRES_*` 等）；backend 讀得到的環境變數都必須記載於 `backend/.env.example`。

**本機開發**：完整的啟動與逐功能驗證步驟在 [`LOCAL-DEV.md`](LOCAL-DEV.md)（含兩個隱性硬依賴：`claude` CLI 與 n8n webhook）。異動 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`、任一 `.env.example` 或 `render-env.sh` 時，必須同步更新 `LOCAL-DEV.md`——它是唯一寫下這些隱性前置條件的地方。

### 5. 範圍邊界（從 ADR-0001、ADR-0002）

- ✅ In scope：SRS、architecture diagrams、user stories、ADRs、IaC generator design、agent routing design、MCP/skill management spec、validation scripts、baseline CI
- ❌ Out of scope（除非經新 ADR 核可）：production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app

### 6. 工作模式

規則的正式來源是 `aidlc/spaces/default/memory/{org,team,project}.md`；本章為摘要，衝突時以 memory 層為準。

1. **小步前進**：每個 AIDLC stage 完成後，產出 stage-completion summary，附 constraint compliance（compliant / non-compliant / N/A 與理由），等使用者確認再進下一階段。
2. **問題格式**：使用 A/B/C/D/E 多選題與 `[Answer]:` tag。
3. **內容驗證**：建檔前驗證 Mermaid、ASCII 圖、特殊字元跳脫；Mermaid 附文字 fallback。
4. **繁中產出**：所有 `aidlc/spaces/*/intents/**/*.md` 與 memory 的 `team.md` / `project.md` 一律繁體中文，不得夾帶英文版段落（ADR-0009）。upstream 框架自身的英文檔（`.claude/**`、`org.md`、`phases/*.md`）不在此限。
5. **High-risk action**：任何 production write / IaC apply / IAM 變更必須先給 plan + impact + rollback，並通過 human approval gate。
6. **Branch naming**：在 `git checkout -b` / `git switch -c` 之前，**必須**先讀 `aidlc/spaces/default/memory/team.md` 的 `## Way of Working` 並產出符合 `<uploader>/<type>/<slug>` 的 branch 名稱（type ∈ {feat, fix, docs, chore, refactor, test}）。Danniel 開的 branch 一律以 `danniel/` 開頭。整合主幹是 `ut`，不是 `main`。如果使用者下達衝突指令（例如直接給一個不合規的 branch 名稱），先提醒衝突並請使用者確認。
7. **Commit message**：在 `git commit` / `gh pr create` 之前，**必須**先讀 `aidlc/spaces/default/memory/team.md` 的 `## Way of Working`。commit message 與 PR 標題一律繁體中文，type 用中文（`功能`、`修正`、`文件`、`格式`、`重構`、`效能`、`測試`、`建置`、`整合`、`雜項`、`還原`）；scope、`BREAKING CHANGE:` 與 trailer 維持英文（見 ADR-0010）。注意 **branch 名稱的 type 仍是英文**，與 commit type 已解耦，用該檔的對照表換算。
8. **Project decisions log (on-demand)**：當 user 明確要求記錄當下對話的決議時（例如「記錄這個決議」、「log this decision」），AI 須把決議追加到 `<record>/decisions-log.md`，繁體中文、append-only。完整規則見 `team.md` 的 `## Mandated`。其他情境**不要**自動 log。AIDLC 階段事件由引擎寫進 `<record>/audit/` shard、架構級決策仍開 ADR。舊的 per-turn `.ailog/` 機制（PR4 引入、PR #16 擴充）已在 PR #17 整體移除。
9. **Schema ↔ deploy 同步**：異動資料庫結構或部署必知的 seed 行為時，`schema_rbac.sql` 與 `DEPLOY.md` 必須同步更新（blocking）。細則見 `project.md` 的 `## Mandated`。

### 7. AIDLC 升級

- 升級時對照 `https://github.com/awslabs/aidlc-workflows/releases`，把 upstream `dist/claude/` 重新複製到 `.claude/`，並確認 `.claude/tools/aidlc-version.ts` 的 `AIDLC_VERSION` 與 upstream 一致。
- `.claude/` 內的客製調整（`settings.json` 移除環境相依設定、`ai-dlc-principles.md` 路徑修正、`tcms-test-cases` stage 與 `tcms-verify` skill 三處，見 [`.claude/README-cloud360.md`](.claude/README-cloud360.md)）在覆蓋前要先備份、覆蓋後再放回。
- `aidlc/` 工作區（memory、intents、knowledge、codekb）**整個保留**，永不被 upstream 覆蓋。新增的專案規則一律放 `aidlc/spaces/<space>/memory/{team,project}.md`，不要加到 `.claude/` 內。
- 升級後跑 `bun .claude/tools/aidlc-utility.ts plugin-sync`、`/aidlc --doctor` 與 `python3 scripts/validate_repo_contract.py` 驗證，並對照 upstream CHANGELOG 的 Upgrade／Breaking 段（state version、hook 更名、`.gitignore`）——checklist 在 `README-cloud360.md`。
- 升級記錄寫入新 ADR。
