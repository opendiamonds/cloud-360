# ADR 0013: AI-DLC ↔ GitHub Projects 同步的映射層級、承載形式與階段順序

- Status: Accepted
- Date: 2026-08-23
- Amends: **ADR-0012**（AI-DLC 與 GitHub Issues／Projects／Wiki 的雙向同步，Accepted 2026-08-16）——本 ADR 修訂其第 1、5 點與「分階段落地」表，其餘部分維持有效
- Related: ADR-0011（採用 AI-DLC v2）、ADR-0008（Construction↔Operations 連續模型）、ADR-0009（文件一律繁體中文）

## Context

intent `260822-gh-projects-sync` 於 2026-08-22 誕生，主題為「AI-DLC 各 stage 的進展同步到 opendiamonds 組織 Project #16」。該 intent 完整走完 IDEATION 四站並產出 32 項決策，**但全程未引用 ADR-0012**——一份六天前已核可、涵蓋同一主題且更廣的架構決策。缺口在 INCEPTION 第一站（reverse-engineering）開始前才被發現。

缺口的成因是方法性的：feasibility 階段的唯讀查證涵蓋了既有 workflows、gh-aw 官方文件、GitHub API 與 repo 現況，唯獨沒有查 `decisions/`。ADR 是本專案架構級決策的正式落點（`project.md` 明載），主題重疊的 intent 未查 ADR，等於在未知的既有決定上做設計。

比對後確認四處衝突，其中兩處源於 **ADR-0012 的前提已不成立**：

| # | ADR-0012 | 本 intent 的 IDEATION 決定 | 性質 |
|---|---|---|---|
| 1 | intent → 一整個 Project (v2)；user story → Issue | intent → Project #16 的一則 issue | 設計歧異 |
| 2 | 狀態的真實來源是 GitHub；反向同步為階段 2 | 反向同步列入 Won't Have | 設計歧異 |
| 3 | 同步腳本置於 `scripts/aidlc_sync_*.py` | 不得以 repo 內程式承載 | **ADR 前提已失效** |
| 4 | Projects 排在階段 3 | 直接做 Projects | 順序歧異 |

**失效的兩項前提**：

- ADR-0012 記載「gh-aw 的 `safe-outputs` 只支援 `create-issue`／`close-issue`／`add-comment`／`add-labels`／`push-to-pull-request-branch`……沒有 Projects 操作」，並據此推論「必須提權讓 workflow 直接呼叫 `gh` CLI／GraphQL」。2026-08-23 查證 gh-aw 官方文件確認，框架現已提供 **`update-project` safe-output**（可依欄位名稱設定單選欄位，如 `{"type":"update_project","content_type":"issue","content_number":N,"fields":{"Status":"In progress"}}`），另有 `create-project`、`create-project-status-update`，以及 `projects` toolset 供讀取。ADR-0012 第 5 點的提權論證因此不再成立。
- `project.md ## Forbidden` 於 2026-08-23 新增一條規則：不得以 repo 內新增的實作程式承載流程自動化與外部系統同步，此類機制一律以 gh-aw 或 GitHub Actions workflow 承載。該規則與 ADR-0012 指定的 `scripts/aidlc_sync_*.py` 直接衝突。

## Decision

### 1. 映射層級：intent → Project #16 的一則 issue

不採 ADR-0012 的「intent → 一整個 Project」。

理由：intent-capture 階段已定案 **Project #16 是需求清單的正本**，README 只保留一段指向它的文字。若每個 intent 各開一個 Project，#16 的「正本」地位消失，且 Project 數量會隨 intent 線性增長，看板從單一入口退化為需要先找對看板的目錄。

**`story → Issue` 保留為未來方向而非否決**。本次的映射不涉及 story 層；ADR-0012 對「story 才是可分派、可討論、可驗收的最小單位」的判斷仍然成立，只是不在本次落地。

### 2. 反向同步納入範圍

採納 ADR-0012 的論證，**推翻本 intent 原本把反向同步列入 Won't Have 的決定**。

ADR-0012 的反對理由具決定性且本 intent 的 IDEATION 未曾考慮：「repo 永遠贏、GitHub 純鏡像」等於告訴協作者不要在看板上操作，而**拖動卡片會被下次同步彈回原位，這比沒有同步更糟**。本 intent 的原設計實質上就是該被否決的方案 A。

同步方向的非對稱性沿用 ADR-0012 第 2 點不變：內容由 repo 贏、狀態由 GitHub 贏、討論單向不回寫。反向同步一律開 PR、不直接推 `ut`，亦沿用不變。

### 3. 承載形式：gh-aw safe-outputs，不建 `scripts/`

修訂 ADR-0012 第 5 點。既然 `update-project` 存在，Projects 的寫入不需提權直呼 GraphQL，改由框架的受管輸出代理。

保留 ADR-0012 第 6 點「與 AI-DLC 主流程零耦合」的硬約束不變：不得在 `.claude/` 下新增任何檔案，觸發方式為 `on: push` 而非 stage 或 hook。承載位置對照表因此修訂為：

| 元件 | ADR-0012 | 本 ADR |
|---|---|---|
| 同步 workflows | `.github/workflows/aidlc-sync-*.md` | 不變 |
| 同步腳本 | `scripts/aidlc_sync_*.py` | **移除**——改由 gh-aw safe-outputs 承載 |
| 同步狀態 | `<record>/.aidlc-sync-state.json` | 不變 |
| 規則與說明 | `aidlc/spaces/*/memory/project.md` | 不變 |

若日後遇到 safe-outputs 確實做不到的操作（例如建立看板自訂欄位），處置是回到本 ADR 重新評估，而非逕自新增腳本。

### 4. 階段順序重排

修訂 ADR-0012 的「分階段落地」表。本次直接實作 intent 層的 Projects 同步，**ADR-0012 的階段 1（repo → Issues，story 建 issue）不構成前置**——因為決定 1 已確立本次映射不涉及 story 層，階段 1 的產物不是本次的比對基準。

ADR-0012「階段 1 完成前不啟用階段 2」的約束，其理由是「沒有穩定的正向同步，反向同步沒有比對基準」。該理由在本次仍然成立，但比對基準改由本次的正向同步（intent → issue 狀態寫入）提供，而非階段 1。

修訂後的順序：

| 階段 | 範圍 | 狀態 |
|---|---|---|
| **本次** | intent ↔ Project #16 一則 issue 的雙向狀態同步（正向寫入 ＋ 反向拉回開 PR） | 本 intent |
| 後續 | story → Issue（ADR-0012 階段 1）、bug 路徑 A／B、Wiki 單向鏡像 | 未排程 |

## ADR-0012 中維持有效、本 ADR 未修訂的部分

- 第 2 點「真實來源逐欄位切分」：狀態歸 GitHub、內容歸 repo、討論單向。
- 第 2 點的 `<!-- aidlc:managed -->` 受管區塊機制。
- 第 4 點「防迴圈」三道防線：內容雜湊比對、`[aidlc-sync]` 來源標記、狀態欄位單向。
- 第 5 點的其餘控制：反向同步一律開 PR、Projects token 存為獨立 secret 不重用既有的、同步 workflow 與其他 agentic workflow 分離不共用 token。
- 第 6 點「與 AI-DLC 主流程零耦合」的全部內容，包括不碰 `.claude/`、觸發為 `on: push`、以及「若未來需要 stage 內即時掛鉤才評估新增 plugin stage」的保留條款。
- 第 3 點 Wiki 單向鏡像（不在本 intent 範圍內，但決定維持）。
- 「200+ 既有 issue 不回溯」與「既有 `spec-sync`／`issue-triage` 需要重審」兩項 Consequences。

## Consequences

- **本 intent 的範圍擴大**。反向同步從 Won't Have 移出，需要新增一條 GitHub → repo 的路徑、防迴圈機制與 PR 化流程。依 AI-DLC 協定，scope-definition 必須以 Modify 模式回跳修訂並重走 approval gate；approval-handoff 的交接包亦隨之失效需重製。
- **ADR-0012 不再可獨立閱讀**。其第 1、5 點與階段表已被本 ADR 修訂，讀者必須併讀兩份。這是修訂而非取代的固有代價；選擇修訂是因為 ADR-0012 有大量內容（防迴圈、逐欄位真實來源、零耦合論證）仍然有效且推理完整，整份取代會丟失它們。
- **本 intent 的 IDEATION artifacts 有一部分建立在未知既有決定的基礎上**。已核可的內容不回改（AI-DLC 的既有紀律），但 scope-definition 與 approval-handoff 的修訂會在其 Revision 段記明本 ADR 為修訂來源。
- **ADR-0012 的 Status 需加註**「Amended by ADR-0013」，否則往後讀者會把它當成現行完整決定。
- **憑證與權限的結論改變**。ADR-0012 因提權而要求「同步 workflow 與其他 agentic workflow 分離、不共用 token」；改用 safe-outputs 後提權幅度縮小，但該隔離要求仍維持——組織層 Projects 讀寫仍是本 repo 最大的單一權限授予。

## Alternatives Rejected

**A. 整份取代 ADR-0012。** 否決原因：其第 2、4、6 點的推理完整且與本次決定無衝突（逐欄位真實來源、防迴圈三道防線、零耦合的 plugin 查證）。整份取代會迫使本 ADR 重述那些內容，而重述必然產生兩份可能漂移的副本——這正是 `team.md` 記載的「單一真實來源」紀律要避免的形狀。

**B. 回跳 ideation 全面改為符合 ADR-0012。** 否決原因：ADR-0012 的兩項技術前提已被實測推翻（safe-outputs 現支援 Projects、`project.md` 新規則禁止 repo 內腳本），照它做等於依過期事實施工。且「intent → 一整個 Project」會摧毀 intent-capture 已核可的「Project #16 為需求清單正本」定位。

**C. 維持本 intent 原樣，把 ADR-0012 標為過期。** 否決原因：ADR-0012 對反向同步的論證（拖動卡片被彈回比沒有同步更糟）不因技術前提改變而失效，它是產品判斷而非技術判斷。忽略它就是重蹈它已經分析過的錯誤。

**D. 本 intent 暫停，先做 ADR-0012 的階段 1。** 否決原因：決定 1 確立本次不涉及 story 層映射，階段 1 的產物不是本次的比對基準；先做它並不會讓本次更安全，只會延後。

## References

- ADR-0012：`aidlc/spaces/default/intents/260802-default/inception/decisions/0012-github-issues-projects-wiki-sync.md`
- gh-aw Safe Outputs（`update-project` 契約）：<https://github.github.com/gh-aw/reference/safe-outputs/>
- gh-aw Authentication (Projects)：<https://github.github.com/gh-aw/reference/auth-projects/>
- GitHub Docs — Projects v2 需 PAT 或 GitHub App，`GITHUB_TOKEN` 不涵蓋：<https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects>
- 本 intent 的衝突發現紀錄：`../reverse-engineering/memory.md` 的 `## Open questions`
