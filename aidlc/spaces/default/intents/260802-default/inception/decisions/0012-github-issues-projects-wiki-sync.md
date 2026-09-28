# ADR 0012: AI-DLC 與 GitHub Issues／Projects／Wiki 的雙向同步

- Status: Accepted，**部分經 ADR-0013 修訂（2026-08-23）** —— 第 1 點的映射層級、第 5 點的承載形式與提權論證、以及「分階段落地」表已被修訂；第 2、3、4、6 點與其餘 Consequences 維持有效。閱讀本 ADR 時必須併讀 `../../260822-gh-projects-sync/inception/decisions/0013-aidlc-projects-sync-scoping.md`。
- Date: 2026-08-16
- Related: ADR-0011（採用 AI-DLC v2）、ADR-0008（Construction↔Operations 連續模型）、ADR-0009（文件一律繁體中文）、`.github/workflows/spec-sync.md`、`.github/workflows/issue-triage.md`

### Context

AI-DLC 的工作狀態目前**只存在於 repo 內**：intent 的進度在 `<record>/aidlc-state.md`，需求在 `stories.md`，實作單元在 `unit-of-work.md`，決策在 `decisions/`。這對走 AI-DLC 流程的人夠用，但有兩個實際問題：

1. **協作者看不到進度**。不看 repo 的人（PM、QA、其他團隊）無從得知某個需求做到哪、誰在做、卡在哪。GitHub 的 Issues 與 Projects 正是為此存在，但目前完全沒有承載 AI-DLC 的內容。
2. **在 GitHub 上做的事回不到 repo**。有人在 issue 上補充需求、在看板上拖動卡片、在 Wiki 上修文件，AI-DLC 這邊一無所知，下一輪流程會用過期的認知繼續推進。

現況盤點（2026-08-16）：

- **既有 11 個 gh-aw workflows**，其中兩個已觸及此領域：`spec-sync`（spec 變更 → 開 issue 列出要改的 code）與 `issue-triage`（新 issue → 分類、貼標籤、問缺的細節）。兩者都是**單向且唯讀**（`permissions: issues: read`），寫入透過 gh-aw 的 safe-outputs 由框架代理。
- **Issues 有 200+ 筆**，絕大多數是 `daily-digest` 每日自動產生的。同步進來的 issue 會混在這個池子裡。
- **Wiki `has_wiki=true` 但 wiki 的 git repo 不存在** —— 從未初始化。GitHub 要先手動建立第一頁，`<repo>.wiki.git` 才會生成。
- **Projects 已啟用**，尚未有 AI-DLC 內容。

技術約束（實測確認）：

- **gh-aw 的 `safe-outputs` 只支援 `create-issue`／`close-issue`／`add-comment`／`add-labels`／`push-to-pull-request-branch`。** 沒有「更新 issue 標題或內文」，沒有 Projects 操作，沒有 Wiki 操作。這是 gh-aw 刻意的安全設計：agent 不持有寫入權限，寫入由框架以受限的形狀代理。
- 因此「自動增刪**修**議題內容及狀態」與 Projects 同步**無法只靠 safe-outputs 完成**，必須提權讓 workflow 直接呼叫 `gh` CLI／GraphQL。

方法論約束：

- AI-DLC 的 artifacts 有 **approval gate**。`stories.md` 的驗收標準是經過人工核可的產物，`decisions/` 是架構決策紀錄。
- 本專案已在 `test-case-management-plan.md` 與 `TESTING.md` 建立「**每種資料只能有一個真實來源**」的紀律。雙向同步天然與這條紀律衝突，除非把真實來源切得夠細。

### Decision

#### 1. 分層映射

| AI-DLC | GitHub | 依據 |
|---|---|---|
| intent（`intents.json` 的一列） | **Project (v2)** 一個 | intent 是一整個需求的生命週期，對應看板剛好 |
| user story（`stories.md` 的 `## US-n`） | **Issue** 一則 | story 是可分派、可討論、可驗收的最小需求單位 |
| unit of work（`unit-of-work.md`） | Issue 的 **子任務**（task list item） | 實作單元屬於某個 story，不該與 story 平級競爭注意力 |
| Bolt（`bolt-plan.md`） | Project 的 **iteration 欄位** | Bolt 是交付批次，是看板的時間維度而非工作項 |
| 已核可 artifacts + 根層文件 | **Wiki 頁面** | 見第 3 點 |

同步進來的 issue 一律帶 `aidlc` 標籤與 `intent:<slug>` 標籤，與 `daily-digest` 產生的噪音區隔開。

#### 2. 真實來源逐欄位切分

這是本 ADR 的核心決定。**不是整個物件歸誰，是每個欄位歸誰**：

| 欄位類 | 真實來源 | 理由 |
|---|---|---|
| **狀態**：open/closed、看板欄位、assignee、labels、iteration | **GitHub** | 人在看板上拖卡片、指派、關閉 issue，本來就是正式操作。要求他們改 repo 才算數，等於否定看板的存在意義 |
| **內容**：story 標題與敘述、驗收標準、unit 定義、決策內文 | **repo** | 這些經過 AI-DLC 的 approval gate。若任何人在 issue 上改 AC 就能覆寫回 repo，那個 gate 形同虛設 |
| **討論**：issue comments | **GitHub**（單向，不回寫 repo） | 討論是過程，不是 artifact。要納入 artifact 必須經由 AI-DLC 流程重新產出 |

於是同步是**非對稱**的：

```
repo  ──內容──▶  GitHub      （AI-DLC 流程觸發，覆寫 issue 內文的受管區塊）
repo  ◀──狀態──  GitHub      （定時 workflow 拉取，寫進 github-status.md）
```

**issue 內文分兩區**：`<!-- aidlc:managed -->` 與 `<!-- /aidlc:managed -->` 之間由 repo 覆寫；標記之外的內容是人寫的，同步永不觸碰。這讓「內容 repo 贏」不至於吃掉協作者在 issue 上補充的脈絡。

#### 3. Wiki 只放已核可的成品

同步範圍限定：

- **已核可 artifacts**：SRS、architecture、ADR、user stories
- **根層文件**：`README.md`、`DEPLOY.md`、`LOCAL-DEV.md`、`TESTING.md`

不同步中間過程文件（各 stage 的 questions、memory diary、reviewer contributions）——它們是流程的工作痕跡，對 Wiki 的讀者是噪音。

Wiki 是**單向鏡像**（repo → Wiki），不回寫。Wiki 頁首自動加註「本頁由 `<來源路徑>` 自動同步，請勿直接編輯」。這與第 2 點的「內容 repo 贏」一致，也避開了 Wiki 沒有 PR review 的問題。

> Wiki 必須先在 GitHub UI 手動建立第一頁，`<repo>.wiki.git` 才存在。這是實作的前置條件。

#### 4. 防迴圈

雙向同步的必然風險：repo 寫 GitHub → 定時任務讀回 → 寫 repo → 觸發 workflow → 又寫 GitHub。三道防線：

1. **內容雜湊比對**：同步前先算受管區塊的雜湊，與上次同步記錄的雜湊相同就跳過寫入。
2. **來源標記**：所有由同步產生的 commit 訊息帶 `[aidlc-sync]`；反向同步的觸發條件排除這類 commit。
3. **狀態欄位單向**：狀態只從 GitHub 流向 repo，repo 不寫 GitHub 的狀態欄位（除了建立 issue 時的初始值）。單向的欄位不可能來回震盪。

同步狀態記錄於 `<record>/aidlc-sync-state.json`（需進版控才能跨 runner 比對，因此放在 record 內並隨同步 commit 一起更新）。**檔名刻意不以 `.aidlc-` 開頭**：AI-DLC 出貨的 `.gitignore` 有 `aidlc/spaces/*/intents/*/.aidlc-*`（排除機器本地暫存），實作時實測會把這個檔擋掉。

#### 5. 權限：明確提權，範圍最小

`safe-outputs` 不足以完成「修改」與 Projects 操作，因此同步 workflow 需要：

- `issues: write`（更新 issue 內文與 labels）
- `contents: write`（回寫 repo 的狀態與 Wiki 推送）
- Projects v2 需要 **classic PAT 或 GitHub App token**（`GITHUB_TOKEN` 不涵蓋 Projects v2 的 GraphQL 寫入）

這是對既有安全模型的**實質放寬**，因此：

- 同步 workflow **與其他 agentic workflow 分離**，不共用 token。
- 反向同步（GitHub → repo）**一律開 PR，不直接推 `ut`**。人審過才進 trunk，保住 approval gate 的精神。
- Projects token 存為獨立 secret，不重用既有的。

#### 6. 與 AI-DLC 主流程零耦合（硬約束）

**同步機制不得修改 AI-DLC 主流程，也不得在 `.claude/` 下新增任何檔案。**

這條的由來是升級韌性：upstream 升級的動作是「把 `dist/claude/` 重新複製到 `.claude/`」，任何放在該目錄下的東西都在覆蓋範圍內。

查證後確認 **AI-DLC 的 plugin 機制不提供檔案系統層級的隔離**：

- `harness.json` 的 `plugins` 欄位只是一個**啟用 allowlist**，決定哪些 plugin 的 stage 生效。
- 沒有任何工具會從 `plugins/<name>/` 安裝東西；stage 檔仍然**只能**放在 `.claude/aidlc-common/stages/<phase>/`（`aidlc-graph.ts` 的 `stagesDir()` 只掃這一個目錄，`AIDLC_STAGES_DIR` 是測試 seam 而非安裝點）。
- 因此 `plugin:` 欄位給的是**邏輯**歸屬（標記擁有者、可整組停用），不是升級隔離。本 repo 的 `tcms-test-cases` 就是實例：它是 plugin stage，仍然得靠 repo contract 與 `README-cloud360.md` 登記才不會在升級時無聲消失。

所以「做成 plugin」**不足以**達成升級韌性。真正有效的做法是**完全不進 `.claude/`**：

| 元件 | 位置 | 升級影響 |
|---|---|---|
| 同步 workflows | `.github/workflows/aidlc-sync-*.md` | 無 —— upstream 不碰 `.github/` |
| 同步腳本 | `scripts/aidlc_sync_*.py` | 無 |
| 同步狀態 | `<record>/aidlc-sync-state.json` | 無 —— `aidlc/` 工作區永不被覆蓋 |
| 規則與說明 | `aidlc/spaces/*/memory/project.md` | 無 |

**觸發方式是 git push，不是 AI-DLC 的 stage 或 hook。** AI-DLC 產出 artifact 並 commit 之後，`on: push` 的 paths 過濾自然觸發同步。AI-DLC 對此一無所知，也不需要知道。這讓同步機制與框架版本完全解耦：升級 AI-DLC 不影響同步，停用同步不影響 AI-DLC。

代價是**同步的時機是「commit 之後」而不是「stage 完成的當下」**。實務上兩者相差一次 commit，而 AI-DLC 的 artifact 本來就要進版控才算數，這個延遲沒有實際損失。

若未來真的需要 stage 內的即時掛鉤（例如 stage 一完成就更新 Project 欄位而不等 commit），那才評估新增 plugin stage，且屆時必須比照 `tcms-test-cases` 的既有機制：列入 `REQUIRED_FILES`、登記於 `README-cloud360.md` 的升級步驟。**在那之前，不碰 `.claude/`。**

### Consequences

- **協作者不必讀 repo 就能看到進度**，這是本 ADR 的目的。代價是多一套需要維護的同步機制。
- **內容仍受 approval gate 保護**：在 issue 上改 AC 不會回寫 repo。這會讓習慣「在 issue 上討論就算數」的人感到摩擦——受管區塊的警語與 PR 化的反向同步是唯一的緩衝。
- **權限被實質放寬**。這是本 ADR 最大的風險項：一個能寫 issues 與 contents 的 agentic workflow，比目前任何一個既有 workflow 都有更大的作用面。反向同步 PR 化是主要的補償控制。
- **Projects v2 需要額外 token**，且它的 GraphQL API 與 REST 不同，實作成本高於 Issues。這是把 Projects 排在階段 3 的原因。
- **Wiki 是第二份副本**。即使有「請勿直接編輯」的警語，仍會有人編輯而後被覆蓋。單向設計讓資料不會遺失到無法追溯（Wiki 有自己的 git 歷史），但體驗上會是「我的修改不見了」。
- **既有的 `spec-sync` 與 `issue-triage` 需要重審**：新機制會建立大量帶 `aidlc` 標籤的 issue，`issue-triage` 對它們的分類行為要排除或特化，否則會互相干擾。
- **200+ 既有 issue 不回溯**。同步只作用於本 ADR 之後的 intent；歷史 issue 維持原狀。
- **升級 AI-DLC 不會影響同步，這是刻意換來的**（第 6 點）。代價是同步時機為 commit 之後而非 stage 完成的當下，且無法取得 stage 內部的中間狀態——同步看得到的只有進版控的 artifact。若日後證明這個粒度不夠，才需要重新評估是否值得為此新增 plugin stage 並承擔升級維護成本。

### Alternatives

**A. repo 永遠贏，GitHub 純鏡像。** 最簡單、無衝突、無迴圈。否決原因：等於告訴協作者「不要在 GitHub 上改任何東西」，而看板的價值正是讓人在上面操作。拖動卡片會被下次同步彈回原位，這比沒有同步更糟。

**B. GitHub 永遠贏，repo 跟隨。** 符合「GitHub 是團隊的協作中心」的直覺。否決原因：直接摧毀 approval gate——經人工核可的驗收標準會被任何有 issue 權限的人改掉，且 AI-DLC 的下一階段會照著改過的內容繼續推進，沒有任何地方會發出聲音。

**C. 偵測到雙邊修改就開 issue 請人決定。** 最安全，不會遺失資料。否決原因：狀態欄位的雙邊修改是**常態**而非例外（人拖卡片的同時 AI-DLC 正在推進階段），衝突 issue 會迅速變成新的噪音來源，重演 `daily-digest` 淹沒 issue 列表的情況。逐欄位切分讓常態不成為衝突，只有真正罕見的情況才需要人介入。

**E. 做成 AI-DLC plugin stage（在流程內同步）。** 直覺上最「正統」：同步是流程的一環，就該是 stage。否決原因有二。其一，**plugin 不提供升級隔離**——stage 檔仍須放在 `.claude/aidlc-common/stages/`，upstream 升級照樣覆蓋；`plugin:` 欄位只是啟用開關與歸屬標記（見 Decision 第 6 點的查證）。其二，**同步不需要流程內的資訊**：它要的是 artifact 的最終內容，而 artifact 進版控本來就是流程的完成條件，`on: push` 拿得到一模一樣的東西。付出升級維護成本卻換不到額外能力。保留為未來選項：若出現「必須在 commit 之前取得 stage 中間狀態」的真實需求，再重新評估。

**D. 不做 Wiki，只做 Issues／Projects。** 合理的減法，GitHub 本來就能直接瀏覽 repo 內的 markdown。保留為可退回的選項：若 Wiki 的維護成本高於價值，階段 4 可以直接取消而不影響前三階段。

### 分階段落地

實作分四階段，每階段可獨立驗收、可獨立回退：

| 階段 | 範圍 | 出口條件 |
|---|---|---|
| **1** | repo → Issues 單向：intent 的 stories 建立／更新 issue（受管區塊） | 一個 intent 的所有 story 在 GitHub 有對應 issue，重跑不產生重複 |
| **2** | Issues → repo 反向：狀態（open/closed、assignee、labels）定時拉回，開 PR | 在 GitHub 關掉 issue，下次同步產生一個更新 `github-status.md` 的 PR |
| **2.5** | **bug 路徑 B（半自動）**：列出待修 bug，人選一個帶入 `/aidlc --scope bugfix` | 從 issue 挑一個 bug 到產出帶 `Closes #N` 的 PR，全程可在本機完成 |
| **3** | Projects v2：intent → Project、看板欄位 ↔ 階段狀態、Bolt → iteration | 看板反映真實進度；拖動卡片會回寫 repo |
| **3.5** | **bug 路徑 A（自動）**：`aidlc:auto` label 觸發，自架 runner 跑完並開 PR | 貼 label 後不需人介入即產出 PR，且 PR 說明揭露未經 stage gate |
| **4** | Wiki 單向鏡像 | 已核可 artifacts 與根層文件出現在 Wiki，頁首帶來源警語 |

階段 1 完成前不啟用階段 2 —— 沒有穩定的正向同步，反向同步沒有比對基準。
階段 2.5 先於 3.5 —— 半自動只用本機既有環境，自動路徑要先在自架 runner 上備妥 `bun`、`claude` CLI 與 LLM 憑證。先讓 issue → intent 的轉換被人工驗證過，再投資 CI 基礎設施。

#### 外部進入點：GitHub 上回報的 bug

`bugfix` scope 的 8 個 stage **不含 `user-stories`**，因此走 bugfix 的 intent 不產生 stories，Decision 第 1 點的 story → Issue 映射對它不適用。**bug issue 本身就是工作項**，不再產生第二則 issue 代表同一件事。

bug issue 是**回報者寫的**，因此：**不加受管區塊、內文永不被覆寫**。同步只做三件事——加進 Project 看板、在三個節點留言（已接受／PR 已開／合併時由 `Closes #N` 自動關）、以及 PR 合併後關閉。

兩條路徑並存，差別**只有 gate 的位置**：

| | 路徑 A（自動，label 觸發） | 路徑 B（半自動，終端機挑） |
|---|---|---|
| stage approval gate | **跳過** | 完整執行 |
| PR review | 有 | 有 |

**路徑 A 的 PR 必須在說明中揭露「本 PR 由自動路徑產生，未經 stage approval gate」。** 這是 reviewer 判斷該用多少力氣審的依據；少了它，自動路徑就是繞過方法論的後門。兩條路徑都以 PR 為最終關卡，PR 不自動合併，人的決定權完整保留。

此分界與 repo 既有實務一致：`deploy-doctor` 只診斷不修（明文寫「so a human can fix」），`lint-fix` 自動修但僅限機械性、零判斷的問題。bug 修復介於兩者之間，故保留自動路徑但把 gate 明確移到 PR。
