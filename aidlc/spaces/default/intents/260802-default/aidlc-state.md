# AI-DLC State Tracking

> Cloud-360 AI-DLC workflow state. Updated automatically by AI-DLC stages and manually by maintainers.

## Project Information

<!-- v2 的機器可讀欄位。flat-layout migration 只搬檔案、不升級 state schema，
     這一區是遷移時依 v2 模板補上的（ADR-0011）。工作流程控制欄位留空 —
     目前沒有進行中的 v2 workflow，值會在首次 /aidlc 執行時由引擎填入。
     下方「專案資訊」等區塊為 v1 時代累積的人類可讀狀態，原樣保留。 -->

- **Project**: Cloud-360
- **Project Type**: Brownfield
- **Scope**: feature
- **Start Date**: 2026-08-02
- **State Version**: 7
- **Active Agent**:
- **Worktree Path**:
- **Bolt Refs**:
- **Practices Affirmed Timestamp**:

### 專案資訊（人類可讀）

<!-- 本區為 v1 時代累積的敘述性狀態。欄位名稱刻意避開引擎的 state 命名空間
     （Project / Project Type / Scope / Current Stage / Status / Depth 等），
     否則 getField() 會把這裡的中文散文當成機器欄位讀走。新增欄位前請先確認
     名稱不在引擎讀取清單內。 -->

- **專案名稱**: Cloud-360
- **專案型態**: Brownfield（已有 SRS / architecture / user stories / ADR baseline）
- **AIDLC 版本**: v2 2.5.33（單一事實來源為 `.claude/tools/aidlc-version.ts` 的 `AIDLC_VERSION`，跑 `/aidlc --version` 可查）
- **AIDLC 啟用 PRs**: `feat/aidlc-framework-rules`（PR1）→ `feat/aidlc-docs-migration`（PR2）→ `Doreen`（目錄重組）→ `danniel/chore/aidlc-v2-migration`（v2 切換，ADR-0011）
- **規則來源**: `aidlc/spaces/default/memory/{org,team,project}.md`
- **Artifacts 位置**: 本 record（`aidlc/spaces/default/intents/260802-default/`）；扁平的 `aidlc-docs/` 已由 flat-layout migration 整棵搬入（ADR-0011）
- **v1 進度摘要**: **A1↔A3 Multi-Agent Code Gen** — branch `luojingting/feat/a1-ux-optimize`；摘要 `construction/a1/code-generation/a1-a3-multi-agent-summary.md`；待手動驗收

### Workspace State

- **Existing Code**: Yes（`backend/`、`frontend/`、`scripts/`、`deploy/`）
- **Programming Languages**: Python（FastAPI backend）、TypeScript（React frontend）、Markdown / Mermaid / draw.io（specs）
- **Build System**: Frontend Vite build + Backend FastAPI；CI 跑 validation。
- **Project Structure**: Spec-Driven repo + A1/A2 application code（Architecture Design 模組）
- **Workspace Root**: repo 根目錄（引擎以 `--project-dir` 解析，不寫死絕對路徑）

### Standing Constraints（常設約束）

正式來源為 `aidlc/spaces/default/memory/project.md` 與 `team.md`；本表為摘要。requirements-analysis 階段不需再次詢問。

| 約束 | 生效 | 決策來源 | 說明 |
|---|---|---|---|
| Security baseline | ✅ | ADR-0006 | Hard constraint，IAM／encryption／network exposure／audit logging |
| Property-based testing | ✅ | ADR-0006 | Hard constraint，IaC generator、cost calculator、agent routing |
| 文件語言：繁體中文 | ✅ | ADR-0009 | 取代 ADR-0005 的雙語規範；所有 record 文件一律繁中 |

### 已存在 Inception Artifacts

> 位置皆相對於本 record（`<record>/`）。目錄名已對齊 v2 stage slug，見 ADR-0011。

| Artifact | 位置 | History 來源 |
|---|---|---|
| SRS | `inception/requirements-analysis/cloud-360-srs.md` | git mv from `docs/srs/cloud-360-srs.md`（含 Doreen 強化版 A1/A2, B1/B2, C1/C2） |
| User Stories | `inception/user-stories/stories.md` | 由 `core-pillars.md` 拆分產出（含 26 個 stories） |
| User Personas | `inception/user-stories/personas.md` | 由 `core-pillars.md` 拆分產出（含 11 個 rich personas） |
| Application Design | `inception/application-design/system-architecture.md` | git mv from `docs/architecture/system-architecture.md` |
| ADR-0001 ~ ADR-0006 | `inception/decisions/` | git mv from `docs/adr/` + checkout from main |

### Phase Tracking

> Phase 名稱依 v2 的 `PHASES`（`initialization / ideation / inception / construction / operation`）。
> 條目名稱為 v2 stage slug；括號內為 record 相對路徑。

- 🔵 inception
  - workspace-detection: ✅
  - reverse-engineering: ✅（`inception/reverse-engineering/`：business-overview、architecture、code-structure、api-documentation、component-inventory、technology-stack、dependencies）
  - requirements-analysis: ✅（A, B, C 三模組已完成）
  - user-stories: ✅（A, B, C 三模組繁中版已完成；含 J 與 A4/A5）
  - delivery-planning: ✅（`inception/delivery-planning/execution-plan.md`）
  - application-design: ✅（baseline：`system-architecture.md`、`frontend-backend-specification.md`）
  - units-generation: ✅（A1／A2／**A3**／A4／A5／J → U-A1／U-A2／**U-A3**／U-A4／U-A5／U-J；見 `inception/units-generation/unit-of-work*.md`；B–H 尚未建 unit）
  - **A3 增量 Inception**: WD ✅ → RA ✅ → US ✅ → WP ✅ → AD ✅ → UG ✅
  - **A3／U-A3 Construction**: FD ✅ → NFR Req ✅ → NFR Design ✅ → Code Generation ✅ → Build&Test 🔄；**增量 Findings←Lens／PDF** Code Gen ✅
  - **A3 Lens Editor 增量 Inception**: RA ✅ → US ✅ → WP ✅ → UG（併 U-A3）✅
  - **A3 Lens Editor Construction**: FD ✅ → Code Gen ✅（待手動驗收）
- 🟢 construction
  - A1 Code Generation: ✅（舊版 httpx；已由 Agent SDK 路徑取代）
  - A1 Agent SDK Refactor & GCP Support: ✅ Phase 1 + Phase 2 done；GCP 畫圖與 AWS/GCP 需求評估機制已實作並通過 52 項單元測試（見 `doreen/feat/modify-a1-features`）
  - A4 Chat Persistence: ✅ Code done — 待手動驗收（見 `construction/plans/a4-chat-persistence-plan.md`、`construction/a4/code-generation/chat-persistence-summary.md`）
  - Role & Permission Redesign: ✅ Core done — A1/A2/A4 語意、Sidebar 隱藏、細項無 J；待 WebSocket JWT／手動 E2E（見 `construction/plans/role-permission-design.md`、`role-permission-construction-plan.md`）
  - A2 Code Generation: 🔄（核心功能已完成，部分 AC 待補 — 見下方驗收對照；summary：`construction/a2/code-generation/canvas-editing-summary.md`）
  - A5 Sharing & Collaboration: ✅ Core done — 待 cursor 廣播／WS JWT（summary：`construction/a5/code-generation/sharing-collab-summary.md`）
  - Pillar J Identity & RBAC: ✅ Core + **J5 done**（註冊 pending、授權申請頁、核准／拒絕、停用刪除；見 `construction/j/`）
  - Build and Test: 🔄（含 A3；backend **61** tests OK；frontend build OK；仍缺 HTTP 整合測／WS JWT／前端 UT）
- 🟡 operation: 🔄
  - Deployment: ✅ `.github/workflows/deploy.yml` — push 至 `ut` 觸發，於 192.168.10.10 的 self-hosted runner（`cloud360-10-10`）執行 `docker compose up -d --build`；對外經 Cloudflare Tunnel 開放 `cloud360.danniel.cc`（見 ADR-0007）
  - Agentic Automation: ✅ 十支 gh-aw workflow（contract-guard、pr-reviewer、issue-triage、spec-sync、code-drift-alert、release-watch、daily-digest、lint-fix、deploy-doctor、ui-regression）
  - Incident Playbooks: ✅ `operation/incident-response/runbooks.md`（SLO + 7 則 playbook）
  - Observability: 🔄 Prometheus + Grafana + blackbox 已建（`grafana.danniel.cc`，於 dc-infra 維運）；主動告警待 Telegram bot token
  - Deploy Notification: ✅ `deploy.yml` 的 `notify` job 以 Slack bot token（`SLACK_BOT_TOKEN`）發送成功／失敗／回滾結果至 `#nemoclaw`（`C0B5XEQDVR7`）；失敗與回滾帶 `<!here>`。跑在 GitHub-hosted runner，故 192.168.10.10 本身故障時仍可送達（需求釐清見 `operation/deployment-execution/deploy-slack-notification-questions.md`）

### Construction Unit 驗收（A2）

| AC / 場景 | 狀態 | 備註 |
|---|---|---|
| AI 局部編輯（基於現有 XML） | ✅ | `agent_router.py` Partial Updates + `current_xml` |
| 框選節點群組後送 AI | ⚠️ 部分 | 依賴 draw.io 手動框選 + 文字描述，未抽取 selection |
| 連線保留 | ✅ | system prompt + merge 邏輯 |
| 修改歷史 + 一鍵 Undo | ❌ | 未實作 AI 變更追蹤；僅 draw.io 內建 undo |
| 儲存架構圖至 DB | ✅ | `UserDiagram` + POST/PUT API |
| 多檔案管理 + 下拉切換 | ✅ | `WorkspacePage` diagram selector |
| 分享給其他使用者 | ✅ | `ShareModal` + `diagram_shares` |
| 多人即時共編（XML 同步） | ✅ | WebSocket `/api/collab/ws/{diagramId}` |
| 多人游標可見 | ❌ | WebSocket 僅廣播 XML，未實作 cursor |
| 進入工作區自動載入最新草稿 | ✅（A4） | bootstrap 還原 `last_opened_diagram_id` + 該圖聊天 |
