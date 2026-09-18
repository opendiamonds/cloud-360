# ADR 0011: 採用 AI-DLC v2，移除 v1 規則樹與 override 層

- Status: Accepted
- Date: 2026-08-02
- Related: ADR-0006（採用 AIDLC 框架）、ADR-0008（Construction↔Operations 連續模型）、ADR-0009（文件一律繁體中文）、ADR-0010（commit message 繁體中文）、`.claude/README-cloud360.md`

### Context

ADR-0006 導入的是 upstream [`awslabs/aidlc-workflows`](https://github.com/awslabs/aidlc-workflows) 的 v1（最終停在 `.aidlc/aidlc-rules/` 的 1.0.1）。v1 的形態是一批純 Markdown 規則檔，由 AI agent 自行讀取並遵循；專案專屬規則另立 `.aidlc-overrides/` 疊加層，靠「載入順序在後者勝出」的約定生效。

upstream v2 是一次架構重寫，不是版本號遞增：

- 交付物從「規則檔」變成**可執行的工作區**（`.claude/` 的 skills / agents / hooks / TypeScript 工具 + `aidlc/` 的 spaces / intents / memory）。
- 規則解析從「約定的載入順序」變成**引擎編譯的五層 strict-additive chain**（`org → team → project → phase → stage`），矛盾會在 §13 learning admission check 被實際擋下，而非仰賴 AI 自律。
- 產出從單一 `aidlc-docs/` 目錄改為 per-intent 的 record 目錄，並附 audit shard 與 state。
- 具備 `--doctor` 健康檢查、stage graph 編譯、sensor 驗證等確定性工具，可在 CI 驗證框架自身是否完整。

v2 已於 commit `4f2b626` 以**並行安裝**方式落地（v2.5.11，v1 暫留），本 ADR 處理後半段：把專案規則從 v1 的 override 層搬到 v2 的 memory 層，並移除 v1。並行狀態不能長期維持——兩套規則樹同時存在時，AI agent 會依入口檔（`CLAUDE.md`、`AGENTS.md`、`.cursor/rules/`、`.agents/`）讀到已經停止維護的那一套，規則來源分裂。

另有一項在遷移中浮現的落差：v2 `org.md` 的框架預設寫「trunk-based，base/target 為 `main`」，但本專案的實際整合主幹是 `ut`（`deploy.yml` 只在 `ut` 觸發部署，`main` 為對外發布線）。沿用預設會讓 Construction worktree 開在錯誤的 base 上。

### Decision

1. **採用 AI-DLC v2 為唯一的 AI-SDLC 框架**，版本以 `.claude/tools/aidlc-version.ts` 的 `AIDLC_VERSION` 為單一事實來源（本次同時自 2.5.11 升至 2.5.33）。
2. **專案規則移轉至 v2 memory 層**，`.aidlc-overrides/` 的六份規則依語意歸位到 `aidlc/spaces/default/memory/`：
   - `team.md`（團隊實踐）← `branch-naming.md`、`commit-message.md`、`traditional-chinese-docs.md`、`decisions-log.md`，加上舊 `CLAUDE.md` 第 6 章的工作模式（stage summary、問題格式、內容驗證）。
   - `project.md`（專案特化）← `schema-deploy-sync.md`、`continuous-delivery.md`（ADR-0008），加上 repo contract、範圍邊界、tech stack、pre-enabled 約束。
   - `org.md` 僅做**最小校正**：Way of Working 改為 `ut` 為整合主幹（`main` 為對外發布線、不接受直接 feature 工作），Deployment 改為「合併進 `ut` → 自動部署自有 staging」並載明雲端 production 在範圍外。
3. **移除 v1**：刪除 `.aidlc/aidlc-rules/` 與 `.aidlc-overrides/`。內容保留在 git 歷史，不做搬遷式保存。
4. **入口統一指向 v2**：`CLAUDE.md`、`AGENTS.md`、`.cursor/rules/ai-dlc.mdc`、`.agents/rules/*.md`、`.agents/workflows/*.md` 一律改為 `/aidlc` skill 入口與 memory 層路徑。
5. **`aidlc-docs/` 整棵搬進 record，順 upstream 設計**。執行 v2 內建的 flat-layout migration，把既有 SRS、ADRs、user stories、architecture、audit、decisions-log 全部移入 baseline record `aidlc/spaces/default/intents/260802-default/`；扁平的 `aidlc-docs/` 目錄不再存在。`audit.md` 依 v2 的 audit 模型轉為 `audit/<host>-<clone>.md` per-clone shard（內容原樣保留，僅 append 一筆搬遷事件）；`aidlc/.migrated` 為冪等標記。

   > 這一項在初版 ADR 中曾決定「續留不搬遷」。改判的原因是：v2 的 `aidlc-lib.ts` 內建 `FLAT_MIGRATION_ROOT` 偵測，只要「扁平 `aidlc-docs/aidlc-state.md` 存在 + 尚無 intent record + 無 `.migrated` 標記」三條件成立，**下一次 `/aidlc` 就會自動搬遷**。「續留」不是一個能守住的決定 —— 它沒有任何機制在執行，只是寫在文件上。與其被動觸發，不如主動執行並把周邊一次改齊。

6. **repo contract 改為動態解析 record**：`REQUIRED_FILES` / `REQUIRED_TEXT` 保留 repo 層路徑（v1 路徑換成 v2 入口 `.claude/CLAUDE.md`、`.claude/skills/aidlc/SKILL.md`、`.claude/tools/aidlc-version.ts` 與三個 memory 檔）；baseline artifacts 改以 record 相對路徑宣告在新的 `REQUIRED_RECORD_FILES` / `REQUIRED_RECORD_TEXT`，由 `resolve_baseline_record()` 在執行時比對 `aidlc/spaces/*/intents/*/`。record 目錄名由引擎鑄造（`<YYMMDD>-<label>`），**不得寫死**。後續 intent 的 record 天生沒有 baseline artifacts，因此判定規則是「**存在某個** record 具備完整 baseline 集合」，失敗時回報最接近候選者的缺口。
7. **memory 層的語言**：`team.md`、`project.md` 為本專案自有規則，依 ADR-0009 以繁體中文撰寫；`org.md` 與 `phases/*.md` 屬 upstream 框架檔，比照 ADR-0009 對 upstream 英文規則檔的既有豁免，維持英文。
8. **v1 的 extension 機制不再存在**，但 ADR-0006 決定的兩項 hard constraint（security baseline、property-based testing）以 memory 層規則延續，強制等級不變。相關敘述一律改稱 **Standing Constraints（常設約束）**，不再使用 v1 的 "extension" 詞彙。

9. **record 內部目錄對齊 v2 stage slug**。搬遷只把樹整棵移進 record，內部仍是 v1 佈局；v2 的 artifact 路徑是 `<record>/<phase>/<stage>/`，兩者不一致會讓 v2 stage 長出平行結構、舊內容變孤兒。已對齊：

   | v1 目錄 | v2 目錄 | 依據 |
   |---|---|---|
   | `operations/` | `operation/` | v2 `PHASES` 用單數 |
   | `operations/runbooks.md` | `operation/incident-response/runbooks.md` | `incident-response` 的 produces 就叫 `runbooks` |
   | `operations/observability/` | `operation/observability-setup/` | stage slug |
   | `operations/deployment/` | `operation/deployment-execution/` | stage slug |
   | `inception/requirements/` | `inception/requirements-analysis/` | stage slug |
   | `inception/plans/` | `inception/delivery-planning/` | stage slug |
   | `inception/application-design/unit-of-work*.md` | `inception/units-generation/` | `units-generation` 的 produces 精確對應 |
   | `construction/<unit>/code/` | `construction/<unit>/code-generation/` | stage slug |

   **未對齊且刻意保留**：`inception/decisions/`（v2 沒有任何 stage 產 ADR，這是本專案慣例）、`construction/<unit>/`（A1–A5、J 是 Cloud-360 的 unit-of-work 分組，非 stage）、`construction/plans/`。檔名一律不改 —— `cloud-360-srs.md` 不等於 v2 `requirements-analysis` 產出的 `requirements.md`，改名會把「這是某次 stage 執行的產物」這個不實資訊寫進 record。

10. **移除他專案樣板殘留**：`tools/`（`mcp/`、`skills/`）與 `workflows/`（`n8n/`）共 6 個檔案，內容為 "MCP Servers for awesome-firebase"、"Firebase × n8n Workflows" 與 2 個空檔，與 Cloud-360 及 AI-DLC 皆無關。

### Consequences

**正面**：

- 規則只有一個來源。AI agent 不再可能讀到已停止維護的 v1 規則。
- 規則衝突由引擎在編譯期擋下，不再依賴「override 永遠勝出」這種需要 AI 自律的約定。
- `/aidlc --doctor` 提供框架自身的確定性健康檢查（本次遷移後 43 項全過），可納入 CI。
- `ut` 主幹的落差被寫進 `org.md`，Construction worktree 會開在正確的 base 上。
- 升級路徑更清楚：`.claude/` 整批覆蓋、`aidlc/` 永不覆蓋，客製點集中在 `settings.json` 一處（見 `.claude/README-cloud360.md`）。

**負面 / 風險**：

- **所有既有的 `aidlc-docs/…` 路徑引用一次失效**。已同步修正的有：repo contract、`README.md`、`DEPLOY.md`、`CLAUDE.md`、memory 層、`.agents/`、以及五個 gh-aw workflow（`spec-sync` 的 `paths:` 觸發、`code-drift-alert` 的對照表、`contract-guard`、`pr-reviewer`、`issue-triage`）並以 `gh aw compile` 重編 lock。**未修正**：record 內歷史文件（舊 ADR、plans、reverse-engineering、audit shard）的內文自我引用 —— 那是寫下當時狀態的紀錄，改掉等於竄改。
- **record 目錄名進入了對外連結**：`README.md` 與 `DEPLOY.md` 直接連到 `aidlc/spaces/default/intents/260802-default/…`。若日後改名或換 baseline record，這些連結要一起改。contract 本身不受影響（它動態解析）。
- **`<record>/` 簡寫的認知成本**：規則層改用 `<record>/` 表示作用中 intent 的 record 目錄。對不熟 v2 的人，這比固定的 `aidlc-docs/` 難定位；`team.md` 表頭與 `CLAUDE.md` 第 2 章都有展開說明。
- **新依賴 `bun`**：v2 的工具與 hooks 以 TypeScript 撰寫，需要 `bun` 在非互動式 shell 的 PATH 上（`~/.zshenv` / `~/.bashrc`，非 `~/.zshrc`）。未安裝者 `/aidlc` 無法運作。
- **規則字面內容改變了措辭**：移轉時依 memory 層的 heading 結構重組，非逐字複製。語意等價，但 record 內歷史文件仍引用舊路徑，屬刻意保留的歷史紀錄。
- **backend 有一處既有死程式碼未處理**：`backend/services/user_router.py` 的 `_audit_append()` 硬寫某台開發機的絕對路徑指向舊 `aidlc-docs/audit.md`，被 `os.path.exists` 擋著永遠 no-op。這在本次遷移前就已失效，且「讓應用程式 runtime 寫入方法論 audit record」本身是個需要獨立決定的設計問題，不在本 ADR 範圍。
- **框架自身的規模**：v2 在 repo 內加入約 1900 行工具程式與大量 skill/agent 檔案，`.claude/` 成為需要隨 upstream 維護的資產，升級成本高於 v1 的純 Markdown 樹。

### Alternatives

**A. 維持 v1，不升級。** 成本最低，但 v1 已停止接收 upstream 更新，且其「AI 自律遵循規則檔」的模型在本專案已出現實際失效（規則存在但未被套用）。放棄。

**B. v1 / v2 長期並行。** 即 commit `4f2b626` 的現況延續。允許漸進遷移，但兩套規則樹同時存在時入口檔必須擇一，等於仍要做本 ADR 的決定，只是延後；期間規則來源分裂的風險持續累積。放棄。

**C. 升級到 v2 但保留 `.aidlc-overrides/` 作為第二規則層。** 保留既有檔案不動，成本最低。但 v2 引擎不認得該目錄，規則只能靠 `CLAUDE.md` 用自然語言請 AI 去讀，等於把已被引擎解決的問題退回人工約定，且與 memory 層形成兩個真實來源。放棄。

**D. 保留扁平的 `aidlc-docs/`，讓歷史與新產出並存。** 修改面最小，且歷史 artifacts 本來就不對應任何 v2 intent。但 v2 引擎內建的 flat-layout migration 會在下一次 `/aidlc` 主動搬遷，這個「保留」沒有執行機制 —— 要真的守住，得預先寫入 `aidlc/.migrated` 標記去騙過引擎的冪等檢查，等於長期與 upstream 設計對抗，且每次升級都要重新確認這個 hack 還有效。放棄。

**E. 寫 `aidlc/.migrated` 擋掉搬遷，維持現狀。** 即上述 D 的具體作法。優點是 repo contract 與三個 gh-aw workflow 完全不用動、`README.md` 連結不會斷。放棄的理由是它把一個 upstream 認定為「過渡狀態」的佈局永久化：`aidlc-docs/` 在 v2 沒有任何語意，只會讓之後每個讀 repo 的人（與 AI）都要先理解一次為什麼有兩套佈局。一次痛比長期困惑好。
