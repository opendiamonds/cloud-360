# GitHub 同步實作藍圖 — Cloud-360

- Status: Design（ADR-0012 已 Accepted；實作尚未開始）
- Date: 2026-08-16
- 決策依據：[ADR-0012](../inception/decisions/0012-github-issues-projects-wiki-sync.md)
- 關聯：`.github/workflows/spec-sync.md`、`.github/workflows/issue-triage.md`、`test-case-management-plan.md`

> 本檔是 ADR-0012 的實作細節。ADR 說**為什麼這樣設計**，本檔說**怎麼做**。
> 兩者有出入時以 ADR 為準。

---

## 0. 隔離邊界（最重要的實作約束）

**同步機制的任何檔案都不得放進 `.claude/`。** 依據見 [ADR-0012 Decision 第 6 點](../inception/decisions/0012-github-issues-projects-wiki-sync.md)：upstream 升級會把 `dist/claude/` 整批複製到 `.claude/`，而 AI-DLC 的 plugin 機制**不提供**檔案系統層級的隔離（`plugin:` 只是啟用開關，stage 檔仍須放在 upstream 目錄）。

允許動到的位置，全部在升級範圍之外：

```
.github/workflows/aidlc-sync-*.md        同步 workflow（gh-aw 來源）
.github/workflows/aidlc-sync-*.lock.yml  gh aw compile 的產物
scripts/aidlc_sync_*.py                  解析與渲染的實作
<record>/.aidlc-sync-state.json          同步狀態（進版控）
aidlc/spaces/*/memory/project.md         規則層的一條說明
```

**禁止動到**：`.claude/` 下的任何路徑（stages、hooks、skills、tools、settings.json）。

### 升級韌性的驗收方式

不是宣稱，是可執行的檢查。實作完成後跑一次：

```bash
# 1. 同步機制沒有任何檔案落在 .claude/
git log --oneline --name-only -20 -- .claude/ | grep -i sync   # 應無輸出

# 2. 模擬升級：暫時移走 .claude/ 的 stage 與 hook，同步腳本仍可獨立執行
mv .claude /tmp/claude-backup
python3 scripts/aidlc_sync_push.py --dry-run                    # 應正常執行
mv /tmp/claude-backup .claude
```

第 2 項是關鍵：**同步腳本不得 import 或讀取 `.claude/` 下的任何東西**。它讀的是 `aidlc/` 工作區的 artifact（那是永不被覆蓋的區域）與 GitHub API。

### 觸發方式：git push，不是 stage

AI-DLC 產出 artifact → commit → push → `on: push` 的 paths 過濾觸發同步。AI-DLC 對同步一無所知。

代價是同步時機為「commit 之後」而非「stage 完成的當下」。artifact 本來就要進版控才算數，所以這個延遲沒有實際損失。

---

## 0.1 前置條件（實作前必須先完成）

| # | 項目 | 怎麼做 | 沒做會怎樣 |
|---|---|---|---|
| P1 | **初始化 Wiki** | 在 GitHub UI 建立第一頁（任意內容） | `<repo>.wiki.git` 不存在，階段 4 無法 clone |
| P2 | **Projects v2 token** | 建立 GitHub App 或 classic PAT，scope `project`；存為 secret `GH_PROJECTS_TOKEN` | 階段 3 的 GraphQL 寫入全部 401；`GITHUB_TOKEN` **不涵蓋** Projects v2 |
| P3 | **本機 gh scope** | `gh auth refresh -s read:project,project` | 開發時無法查證看板現況 |
| P4 | **建立 label** | `aidlc`、`intent:<slug>`、`story`、`sync-conflict` | issue 混在 200+ 筆 digest 噪音中無法篩選 |
| P5 | **確認 `issue-triage` 的排除規則** | 讓它跳過帶 `aidlc` 標籤的 issue | 兩個 workflow 互相改標籤，來回震盪 |

---

## 1. 映射細節

### 1.1 intent → Project

| Project 欄位 | 來源 | 方向 |
|---|---|---|
| Project 名稱 | `intents.json` 的 `slug` | repo → GH（建立時） |
| Project 描述 | `<record>/aidlc-state.md` 的 intent 摘要 | repo → GH |
| Status 欄位選項 | AI-DLC 的 phase（ideation／inception／construction／operation） | repo → GH（建立時） |
| Iteration 欄位 | `bolt-plan.md` 的 Bolt 序列 | repo → GH |
| 卡片所在欄位 | — | **GH → repo** |

### 1.2 user story → Issue

`stories.md` 的結構是 `## US-n <標題>`，其下 `### 驗收標準` 為 Given/When/Then 區塊。

| Issue 欄位 | 來源 | 方向 |
|---|---|---|
| 標題 | `US-n <標題>` | repo → GH |
| 內文的受管區塊 | story 敘述 + 驗收標準 + Definition of Done | repo → GH |
| 內文的受管區塊**之外** | 人手寫 | **不同步、永不觸碰** |
| labels `aidlc` / `intent:<slug>` / `story` | 固定 | repo → GH（建立時） |
| 其他 labels | 人／`issue-triage` | **GH → repo** |
| state（open/closed） | — | **GH → repo** |
| assignee | — | **GH → repo** |
| comments | — | 不同步（只在 GitHub） |

### 1.3 從 AI-DLC 流程看：什麼時候會動到 GitHub

**AI-DLC 流程本身零改動。** 33 個 stage 一個都不新增、不修改、不重排；沒有新 hook、沒有改 `settings.json`。同步只發生在「artifact 進版控之後」。

33 個 stage 裡，**只有 5 個的產出會觸發內容同步**；其餘 28 個對 GitHub 的內容毫無影響：

| Phase | Stage | 產出 | GitHub 上發生什麼 |
|---|---|---|---|
| inception | `requirements-analysis` | `requirements` | Wiki 新增／更新需求頁 |
| inception | `user-stories` | `stories` | **每個 `US-n` 建立或更新一則 Issue**（受管區塊） |
| inception | `application-design` | `decisions`（ADR） | Wiki 新增／更新 ADR 頁 |
| inception | `units-generation` | `unit-of-work` | 對應 story 的 Issue 內，task list 增減項目 |
| inception | `delivery-planning` | `bolt-plan` | Project 的 iteration 欄位建立／更新 |

另有一項與 stage 無關、但**每個 stage 完成時都會發生**：

| 觸發 | 來源 | GitHub 上發生什麼 |
|---|---|---|
| 任一 stage 完成 | `aidlc-state.md` 的 `Current Stage` / `Phase Progress` 更新 | Project 卡片的 **Status 欄位**移動到對應 phase |

也就是說，**看板上的卡片會隨流程推進自己移動**（ideation → inception → construction → operation），而 Issue 的內容只在上表那 5 個 stage 才變。這正是「狀態」與「內容」分屬不同真實來源的體現：狀態頻繁變動、內容經 gate 才變。

### 1.3.1 一個 intent 的完整時序

以 `feature` scope 為例，從頭到尾 GitHub 上依序看到的東西：

```
ideation（7 stages）
  └─ 每個 stage 完成 → Project 卡片停在「Ideation」欄
     GitHub 上還沒有任何 Issue —— 此時需求尚未成形，開 issue 只會是雜訊

inception
  ├─ requirements-analysis → Wiki 出現需求頁
  ├─ user-stories          → ★ Issues 大量出現（每個 US-n 一則）
  │                           卡片移到「Inception」欄
  ├─ application-design    → Wiki 出現 ADR 頁
  ├─ units-generation      → 既有 Issue 的 task list 被填入實作單元
  └─ delivery-planning     → Project 出現 iteration（Bolt 1、Bolt 2…）

construction（8 stages，含 tcms-test-cases）
  └─ 每個 stage 完成 → 卡片移到「Construction」欄
     Issue 內容不再變動（除非回頭修 stories 或 units）
     人在此期間勾 task list、關閉 issue、指派 assignee ← 這些會被反向同步拉回

operation（7 stages）
  └─ 卡片移到「Operation」欄
```

**Issue 出現的時機是 `user-stories` 完成之後**，不是 intent 一開始。ideation 階段的產出（intent statement、scope、feasibility）刻意不同步——那時需求還在成形，開 issue 只會製造需要回頭清理的雜訊。

### 1.3.2 反向同步與 stage 無關

反向同步（GitHub → repo）是**定時**的（每 6 小時），不掛在任何 stage 上。它在 intent 的任何階段都可能發生，包括 AI-DLC 完全沒在跑的時候——人在週末拖了卡片，週一的第一次同步就會產生 PR。

這是刻意的：協作者的操作不該等 AI-DLC 跑到某個 stage 才被承認。

### 1.4 unit of work → Issue 的子任務

`unit-of-work.md` 的每個單元渲染成受管區塊內的 task list：

```markdown
- [ ] U-1 後端回應加入 last_activity_at 欄位
- [x] U-2 前端表格新增欄位與空態
```

勾選狀態是 **GH → repo**（人在 issue 上勾）；項目本身的增刪是 **repo → GH**。

> 為什麼不用 GitHub 的 sub-issue：sub-issue 會在 issue 列表產生大量條目，與 story 平級競爭注意力，且 200+ 筆的 issue 池已經夠吵。task list 在 story issue 內部，層級關係自然。

---

## 2. 受管區塊格式

Issue 內文的實際形狀：

```markdown
<!-- aidlc:managed intent=last-login-column story=US-1 hash=a1b2c3d4 -->

## 需求

作為 Security_Reviewer，我需要看到每個帳號的最後活動時間，以便判斷帳號是否仍在使用。

## 驗收標準

**AC-1.1**
- **Given** 一個帳號目前無活動紀錄
- **When** 該帳號以有效憑證發出任一需認證的請求
- **Then** 該帳號的最後活動時間被記錄為該請求發生的時刻

## 實作單元

- [ ] U-1 後端回應加入 last_activity_at 欄位
- [ ] U-2 前端表格新增欄位與空態

---
> 🤖 本區塊由 AI-DLC 自動同步自 `aidlc/spaces/default/intents/260802-last-login-column/inception/user-stories/stories.md`。
> **在此區塊內的修改會被下次同步覆蓋**；要改需求請走 AI-DLC 流程。
> 區塊之外的內容不會被觸碰，歡迎在下方補充討論與脈絡。

<!-- /aidlc:managed -->

（以下由人自由編寫，同步永不觸碰）
```

`hash` 是受管區塊內容的 SHA-256 前 8 碼，用於防迴圈（見第 4 節）。

---

## 3. 同步狀態檔

`<record>/.aidlc-sync-state.json`，**進版控**（不是 gitignored 的 per-clone 檔——跨 runner 比對需要它）：

```json
{
  "version": 1,
  "intent": "last-login-column",
  "project": { "number": 3, "node_id": "PVT_xxx", "last_synced": "2026-08-16T05:00:00Z" },
  "stories": {
    "US-1": {
      "issue": 502,
      "content_hash": "a1b2c3d4",
      "last_pushed": "2026-08-16T05:00:00Z",
      "last_pulled_state": { "state": "open", "assignees": ["danniel"], "labels": ["aidlc", "story"] }
    }
  }
}
```

- `content_hash`：上次推送的受管區塊雜湊。**相同就不推**。
- `last_pulled_state`：上次拉回的狀態快照。與現況相同就不開 PR。

---

## 4. 防迴圈（三道，缺一不可）

1. **內容雜湊**：推送前算受管區塊的 SHA-256，與 `content_hash` 相同就跳過。這擋掉「內容沒變卻反覆寫入」。
2. **commit 標記**：所有同步產生的 commit 訊息前綴 `[aidlc-sync]`。正向同步 workflow 的觸發條件排除這類 commit：
   ```yaml
   if: "!contains(github.event.head_commit.message, '[aidlc-sync]')"
   ```
3. **狀態欄位單向**：狀態只 GH → repo。repo 除了建立 issue 的初始值之外，**不寫**任何狀態欄位。單向的資料流不可能來回震盪。

> 三道防線針對不同的迴圈路徑：雜湊擋內容、commit 標記擋 workflow 觸發、單向性擋語意層的來回。只做其中一道都會留下活路。

---

## 5. 四個階段的 workflow 規格

### 階段 1：`aidlc-sync-push`（repo → Issues）

```yaml
on:
  push:
    branches: [ut]
    paths:
      - "aidlc/spaces/*/intents/*/inception/user-stories/stories.md"
      - "aidlc/spaces/*/intents/*/inception/units-generation/unit-of-work.md"
  workflow_dispatch:
permissions:
  contents: write   # 寫回 .aidlc-sync-state.json
  issues: write     # 建立與更新 issue
```

步驟：解析 `stories.md` 的 `## US-n` → 對每個 story 算受管區塊與雜湊 → 比對 `sync-state` → 不存在則建立 issue、雜湊不同則**只替換受管區塊**（保留區塊外的人寫內容）→ 更新 `sync-state` 並以 `[aidlc-sync]` commit。

**冪等性驗收**：連跑兩次，第二次的建立數與更新數皆為 0。

### 階段 2：`aidlc-sync-pull`（Issues → repo）

```yaml
on:
  schedule: [{ cron: "0 */6 * * *" }]   # 每 6 小時
  workflow_dispatch:
permissions:
  contents: write
  issues: read
  pull-requests: write   # 反向同步一律開 PR
```

步驟：讀 `sync-state` 的 issue 清單 → 抓現況（state／assignees／labels）→ 與 `last_pulled_state` 比對，無差異就結束 → 有差異則寫 `<record>/github-status.md` 與 `sync-state` → **開 PR**（不直接推 `ut`）。

> **不寫 `aidlc-state.md`（實作時修正的設計）。** 藍圖初稿寫「更新 `aidlc-state.md` 的狀態欄」，
> 實作時查證發現那個檔案是 **engine-owned**：`aidlc-state.ts:575` 明文拒絕外部的生命週期寫入，
> 且有 `aidlc-state-transition-guard` 與 `aidlc-validate-state` 兩個 hook 守著，格式也是引擎專用的
> checkbox 語法。外部寫入等於與引擎搶同一個檔案，遲早不一致。狀態鏡像因此自己一個檔
> （`github-status.md`），誰擁有誰就寫，不重疊。

腳本以**退出碼 10** 表示「有狀態變更」（0 = 無變更，其餘為錯誤），workflow 用它決定要不要開 PR——
無變更時完全不建立分支，避免產生空 PR 的噪音。

PR 標題：`整合(sync): 從 GitHub 拉回 <intent> 的狀態變更`。

**為什麼一律開 PR**：反向同步是唯一可能繞過 approval gate 的路徑，PR 化讓它必須經過人眼。

### 階段 3：`aidlc-sync-project`（Projects v2）

需 `GH_PROJECTS_TOKEN`。Projects v2 只有 GraphQL API，與 Issues 的 REST 不同，這是它排在第三的原因。雙向：欄位定義與卡片建立為 repo → GH；卡片所在欄位為 GH → repo（併入階段 2 的 PR）。

### 階段 4：`aidlc-sync-wiki`（單向鏡像）

```yaml
on:
  push:
    branches: [ut]
    paths:
      - "aidlc/spaces/*/intents/*/inception/decisions/**"
      - "aidlc/spaces/*/intents/*/inception/user-stories/stories.md"
      - "aidlc/spaces/*/intents/*/inception/requirements-analysis/**"
      - "aidlc/spaces/*/intents/*/inception/application-design/**"
      - "README.md"
      - "DEPLOY.md"
      - "LOCAL-DEV.md"
      - "TESTING.md"
```

clone `<repo>.wiki.git` → 渲染（頁首加來源警語與原始路徑連結）→ commit → push。**不回寫**。

---

## 6. 失敗處理

| 失敗 | 處置 |
|---|---|
| GitHub API 429／5xx | 指數退避重試 3 次；仍失敗則**保持 sync-state 不變**並讓 workflow 紅燈——寧可下次重來，不要留下 state 與現實不符 |
| issue 被人手動刪除 | 從 sync-state 移除該筆並重新建立；在 PR 說明中記載 |
| 受管標記被人刪掉 | **不自動修復**、不覆寫整個內文。開一則帶 `sync-conflict` 標籤的 issue 請人決定——自動重建會吃掉人寫的內容 |
| Wiki push 衝突 | 以 repo 為準強制覆蓋（Wiki 是單向鏡像），並在 workflow log 記載被覆蓋的 commit |

---

## 7. 外部進入點：GitHub 上回報的 bug

前面幾節處理的是 **AI-DLC → GitHub** 的產出同步。bug 的方向相反：它從 GitHub 進來，是外部進入點。

### 7.1 bug 不套用 story → Issue 映射

查證 stage graph 後確認：**`bugfix` scope 的 8 個 stage 裡沒有 `user-stories`**。

```
workspace-scaffold → workspace-detection → state-init → reverse-engineering
→ requirements-analysis → code-generation → build-and-test → tcms-test-cases
```

走 bugfix 的 intent 根本不產生 stories，所以 §1.2 的映射對它不適用。**bug issue 本身就是那個工作項**，AI-DLC 不該再產生第二則 issue 代表同一件事——那是重複，且會讓回報者的原 issue 變成孤兒。

### 7.2 兩類 issue 的所有權必須分清

| | 來源 | 受管區塊 | 內容誰的 |
|---|---|---|---|
| story issue | AI-DLC 產生 | 有 | repo 覆寫受管區塊 |
| **bug issue** | **人寫的** | **不得加** | **完全屬於回報者，永不覆寫** |

同步機制**永遠不寫 bug issue 的內文**。它只做三件事：加進 Project 看板、在關鍵節點留言、由 PR 的 `Closes #N` 關閉。

### 7.3 兩條路徑

**路徑 A — 自動（在 GitHub 上跑完）**

```
人貼 aidlc:auto label
  → workflow 觸發，在自架 runner 上跑 bugfix 流程
  → 產出修正 code + 測案 + AI-DLC record
  → 開 PR（帶 Closes #N）
  → 在 issue 留言「已接受、PR #M 已開」
  → 人 review 並合併  ← gate 在這裡
  → issue 自動關閉
```

**路徑 B — 半自動（人在終端機挑）**

```
人跑 scripts/aidlc_sync_buglist.py    列出待修的 bug（label=bug 且未被接受）
  → 選一個
  → /aidlc --scope bugfix（自動帶入該 issue 的標題與內文）
  → 正常的 AI-DLC 流程，含每個 stage 的 approval gate
  → 產出 PR（帶 Closes #N）
  → 同樣的留言與關閉機制
```

### 7.4 兩條路徑的差別只有一個：gate 在哪

| | 路徑 A（自動） | 路徑 B（半自動） |
|---|---|---|
| stage approval gate | **跳過** | 完整執行 |
| PR review | 有 | 有 |
| 適用 | 有明確重現步驟、影響面清楚的 bug | 需要判斷範圍或牽動設計的 bug |

**路徑 A 的 PR 必須在說明中揭露「本 PR 由自動路徑產生，未經 stage approval gate」。** 這句話不是形式——它是 reviewer 判斷該用多少力氣審的依據。少了它，自動路徑就成了繞過方法論的後門。

這條分界線與 repo 既有的自動化實務一致：`deploy-doctor` 只診斷不修（「so a human can fix」），`lint-fix` 會自動修但只限機械性、零判斷的 lint 問題。bug 修復介於兩者之間，所以保留自動路徑，但把 gate 明確地移到 PR。

### 7.5 進度回報：三個節點，不多不少

只在這三個時機於 issue 留言：

1. **已接受** —— intent 建立時：「已建立 bugfix intent `<slug>`，走路徑 A／B」
2. **修正 PR 已開** —— PR 編號與一句摘要
3. **已合併** —— 由 `Closes #N` 自動關閉時（GitHub 原生行為，不需額外留言）

bugfix scope 有 8 個 stage，若每個 stage 都留言會產生 8 則機器留言，把回報者的討論淹掉。細部進度看 Project 卡片。

### 7.6 技術前置（路徑 A 專屬）

路徑 A 要在 CI 裡跑 AI-DLC，不是跑 gh-aw 的 copilot engine：

| 需求 | 說明 |
|---|---|
| 執行環境 | 自架 runner（`[self-hosted, linux, x64, cloud360]`），需裝 `bun` 與 `claude` CLI |
| LLM 憑證 | runner 上的 `claude` CLI 需可認證（`LLM_PROVIDER` 的兩種模式擇一） |
| 權限 | `contents: write`（推分支）、`pull-requests: write`（開 PR）、`issues: write`（留言與標籤） |
| 隔離 | 同 §0：workflow 與腳本都不進 `.claude/` |

**路徑 B 沒有這些前置**——它在開發者自己的機器上跑，用的是既有的本機環境。所以實作順序是 **B 先於 A**：先讓半自動可用，確認 issue → intent 的轉換正確，再投資自動路徑的 CI 基礎設施。

## 8. 開放問題（實作前要有答案）

1. **一個 intent 的 stories 改名或刪除時**，對應的 issue 怎麼處理？關閉並加 `wontfix`？還是留著？（傾向：關閉並在受管區塊註記「此 story 已從需求移除」，不刪 issue——issue 編號是外部引用點。）
2. **`daily-digest` 每天產生 issue** 已使 issue 列表達 200+ 筆。是否該讓 digest 改用 discussion 或直接關閉舊的？這會影響同步進來的 issue 的可見度。
3. **多個 in-flight intent 同時同步**時，Project 是每個 intent 一個（可能很多）還是全部共用一個？目前設計是前者，需確認實際使用時的數量是否可接受。
4. **反向同步的 PR 由誰 review**？若無人 review 會堆積，若自動合併則失去它存在的意義。
