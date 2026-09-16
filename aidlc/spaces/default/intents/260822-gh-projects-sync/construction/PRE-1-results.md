# PRE-1 實測結果（第一輪）

<!-- 產生於 2026-08-30T13:10:08Z（讀自 date -u）。CAP-9 要求的「可追溯證據」。
     實測方式：本機以 App 私鑰鑄 installation token 後直接呼叫 GitHub API。
     憑證：aidlc-sync App（APP_ID 4688634），私鑰檔名 aidlc-sync.2026-08-22.private-key —
     檔名日期與本 intent（260822）吻合，確認是為本 intent 鑄的。 -->

## 結論：**憑證不足，四項權限缺三項。U-3 之後的寫入路徑目前全部不可行。**

## 實測數據

**App 安裝狀態**：已安裝，`installation id = 155851205`（`GET /repos/opendiamonds/cloud-360/installation` → 200）。

**GitHub 回報的權限**（`installation.permissions`，非文件敘述）：

```
contents: read
issues:   write
metadata: read
```

**對照 ADR-0015 §8 要求的四項**：

| 權限 | 需要 | 實際 | 判定 |
| --- | --- | --- | --- |
| Projects（**組織層**） | read & write | **完全沒有** | ❌ |
| Issues | write | write | ✅ |
| Contents | write | **read** | ❌ |
| Pull requests | write | **完全沒有** | ❌ |

## 兩項排除替代解釋的驗證

先前的 Projects 查詢回 `NOT_FOUND: Could not resolve to an Organization with the login of 'opendiamonds'`。**這個錯誤訊息會誤導**——它看起來像 org 名稱打錯，實際是權限不足（GraphQL 對無權限的資源回 `NOT_FOUND` 而非 `403`，這是 GitHub 刻意的設計，避免洩漏資源存在與否）。逐項排除：

1. **org 名稱正確嗎？** `GET /repos/opendiamonds/cloud-360/installation` → **200**，證明 org 與 repo 名稱都對。
2. **是不是只有那一個 Project 看不到？** `GET /orgs/opendiamonds` → **404**，連組織本身都讀不到。`projectV2(number: 16)`（正式看板）同樣 `NOT_FOUND`。

⇒ **App 目前是 repo-scoped 安裝，不具任何組織層權限。** 而 Project #16 是組織層資源。

## 這正是 PRE-1 存在的理由

`stories.md` §PRE-1 第 1 項逐字要求「以最小可行呼叫實測，**不得以文件敘述代替驗證**」；ADR-0014 進一步要求「三項權限各至少一次真實呼叫，其中**必須包含一次開 issue**」，並在「被否決的替代方案」裡點名：

> **K-1：把 Issues 寫入視為 `Contents` 的一部分而不更正宣告。** 不成立——GitHub App 的權限模型中兩者是不同項目，鑄憑證時必須分別勾選。把它當成「已包含」正是會讓 PRE-1 通過而 Bolt 1 失敗的那個誤解。

本輪實測抓到的比那個更大：**不只 Issues／Contents 的區分問題，而是組織層權限整組不存在**。

**一個佐證**：`APP_PRIVATE_KEY` 與 `APP_ID` 在整個 `.github/` 下**零消費**（實測 grep）——這組憑證從未被任何 workflow 使用過，所以在本輪之前**沒有任何機會**暴露這個缺口。若照設計直接寫 U-3，缺口會在 Bolt 1 首次真實呼叫時才炸。

## 要改什麼（第二輪實測的前置）

在 GitHub App（`aidlc-sync`）的設定頁：

1. **Repository permissions**
   - `Contents`：Read → **Read and write**
   - `Pull requests`：無 → **Read and write**
   - `Issues`：已是 Read and write ✅
2. **Organization permissions**
   - `Projects`：無 → **Read and write**
3. **安裝範圍**：確認 App 安裝於 **organization**（`opendiamonds`）而非僅單一 repo——組織層 Projects 權限只在組織層安裝下生效。
4. **重新授權**：權限變更後 GitHub 會要求組織管理者批准（`external-dependency-map.md` 的 E-1 已標為外部依賴，變更需組織管理者操作）。批准前舊 token 仍是舊權限。

## 尚未執行的項目（權限修好後補做）

| # | 項目 | 為什麼還沒做 |
| --- | --- | --- |
| 1b | **開一次 issue**（ADR-0014 明文要求） | `issues: write` 是唯一宣告可用的寫入權，但其餘三項既已確定缺失、權限勢必要重設並重新授權，屆時 token 會換。此刻開 issue 只會留下一個要清理的痕跡，證據價值等權限齊備後一次取得 |
| 2 | 單次操作上限的**實際值**與超限行為 | 需連續呼叫壓測，且要能真的寫入才有意義。**「靜默略過」是最壞情形——它不會紅燈** |
| 3 | `createProjectV2Field` 是否可用（決定 [US:S-5 AC 2] 走哪一支） | 需要 Projects 權限 |
| 4 | A-1／A-2／A-3／A-8 四個未驗證假設 | 同上 |
| PRE-1-a | Repository Rulesets 的 file-path restriction | 獨立項，不依賴本憑證。**若不可行，[US:S-10 AC 5] 的第二個例子在現行設計下無機制可產生**，該 AC 需回 user-stories 改寫 |

## 對排程的影響

`stories.md:323` 把 PRE-1 列為**技術依賴**並寫明「憑證確實帶組織層看板寫入權未經實測前，**任何寫入路徑都無法完成**」。本輪結果使該句從假設變成**已證實的阻塞**：U-3（看板客戶端）與其下游 U-4／U-5／U-6／U-7／U-8 全部無法驗證完成判準。

不受影響的是 **U-9**（selftest，fixture 驅動）、**U-10a／U-10b**（觸發設定）——但它們的設計依賴 U-3 的錯誤型別，先做的價值有限。

---

# PRE-1 實測結果（第二輪，2026-08-30T13:26:05Z）

## 進展：三項已好並實測，**剩 Projects 一項**

| 權限 | 需要 | 第一輪 | 第二輪 | 實測證據 |
| --- | --- | --- | --- | --- |
| Issues | write | write | write | **✅ 已實測**——開出 issue [#538](https://github.com/opendiamonds/cloud-360/issues/538)（ADR-0014 明文要求「必須包含一次開 issue」） |
| Contents | write | **read** | **write** | 宣告已正確；實測留待與 Projects 一併（實測會產生真實 commit，副作用大於開 issue） |
| Pull requests | write | **（無）** | **write** | 同上 |
| Projects（**組織層**） | read & write | （無） | **（仍無）** | ❌ `GET /orgs/opendiamonds` 仍為 **404**，`projectsV2` 查詢仍 `NOT_FOUND` |

## 為什麼 Projects 沒跟著改好——它不在同一個區塊

GitHub App 的設定頁把權限分成**兩個獨立區塊**，第二輪改到的是第一個：

- **Repository permissions** ← Contents、Issues、Pull requests 在這裡（已改好）
- **Organization permissions** ← **Projects（Projects v2，即 Project #16 這種組織層看板）在這裡**

**這與 ADR-0014 點名的誤解是同一種形狀**：看起來是同一個東西，實際是兩個獨立的權限項。ADR-0014 講的是「Issues 獨立於 Contents」，本輪揭露的是「組織層 Projects 獨立於全部 Repository permissions」。

注意 GitHub App 裡有**兩個都叫 Projects 的東西**：
- Repository permissions → `Projects`（**classic projects，repo 層**）——**不是**我們要的
- Organization permissions → `Projects`（**Projects v2，組織層**）——**這才是**

## 還要確認的第二件事：安裝範圍

`GET /orgs/opendiamonds` 回 **404** 而非 403。App 若僅安裝於單一 repo，即使勾了組織層權限也讀不到組織資源。請一併確認 App 安裝在 **organization** 層級（Install App → opendiamonds，All repositories 或至少組織層安裝）。

## 權限變更後必須重新授權

改動權限後 GitHub 會要求組織管理者**批准新權限**（`external-dependency-map.md` 的 E-1 已標為外部依賴）。**批准前，既有 installation 仍以舊權限運作**——這也是第二輪只看到三項變化的可能原因之一：若 Projects 是與其他三項同批送出的，而批准動作只涵蓋部分，結果就會是現在這樣。

## 下一輪要跑的（Projects 好了之後）

1. 組織層 Projects 讀取 → 列出可用 Project，選一個**非 #16** 的測試 Project（ADR-A3）
2. `createProjectV2Field` 是否可用 → 決定 [US:S-5 AC 2] 走哪一支
3. 單次操作上限的**實際值**與超限行為（**「靜默略過」是最壞情形，不會紅燈**）
4. Contents write 與 Pull requests write 的實測（會產生真實 commit／PR，與 Projects 一併做以免重複副作用）
5. A-1／A-2／A-3／A-8 四個未驗證假設
6. PRE-1-a：Repository Rulesets 的 file-path restriction（獨立項，不依賴本憑證）

## 待清理

- **issue #538** — 實測產物，可直接關閉。

---

# PRE-1 實測結果（第三輪，2026-08-30T13:31:56Z）— **推翻上游前提**

## 結論：`opendiamonds` 是個人帳號，Project #16 是 user-level project。**GitHub App 這條路對它不通。**

## 證據鏈

**第一層：帳號型別**（三項獨立來源一致）

| 查詢 | 結果 |
| --- | --- |
| `GET /users/opendiamonds` | `type: User` |
| `GET /repos/opendiamonds/cloud-360` | `owner.type: User` |
| `GET /orgs/opendiamonds` | **404**（不存在同名組織） |

**第二層：Project 的實際位置**——人工確認網址列為 `github.com/**users**/opendiamonds/projects/16`。

**第三層：App 憑證能否存取它**（含對照組）

| 測試 | 結果 | 意義 |
| --- | --- | --- |
| `user(login:"opendiamonds"){projectV2(number:16)}` | ❌ `NOT_FOUND: Could not resolve to a ProjectV2 with the number 16` | 看不到 |
| `viewer` | `aidlc-sync[bot]` | token 身分正確 |
| **對照組**：`repository(owner:"opendiamonds",name:"cloud-360")` | ✅ 讀到，462 個 issues | **token 有效，repo 層正常** |

對照組排除了「token 壞掉」這個解釋。失敗的原因是**權限模型的邊界**：GitHub App 的 installation 權限清單裡，`organization_projects` 只涵蓋**組織**的 Projects v2，**沒有**對應個人帳號 Projects v2 的項目。

**這也解釋了前兩輪的現象**：App 設定裡 `organization_projects: write` 確實存在（`GET /app` 實測），但 installation 的已授予權限始終沒有它——**授予目標（組織）不存在**。不是沒批准，是無從授予。

## 被推翻的上游主張

| 落點 | 原文 | 實測 |
| --- | --- | --- |
| **ADR-0015 §8** | 「Projects: read & write（**組織層**）」 | 沒有組織可授此權限 |
| `stories.md` §PRE-1 第 1 項 | 「憑證確實帶**組織層**看板寫入權」 | 同上 |
| **U-3 `business-logic-model.md`** | GraphQL 使用 `organization(login:...)` | 須改為 `user(login:...)` |
| **`README.md`**（U-11 交付） | 連結 `github.com/**orgs**/opendiamonds/projects/16` | 正確形狀是 `/users/` |

> **U-11 的 reviewer 為什麼沒抓到 README 那一項**：它核對的是「組織名經 `git remote -v` 屬實」——**只驗了名字，沒驗它是不是組織**；且它自己註明「專案編號本身因 `gh` token 缺 `read:project` scope 無法外部驗證」。這是一個**驗證了較弱命題卻結案**的形狀，值得記進學習。

## 尚未決定的事（需人工裁決，可能需開 ADR）

憑證策略必須改變，三條候選路徑各有代價：

1. **改用帶 `project` scope 的 classic PAT** — 能存取個人 Projects v2。代價：PAT 是個人憑證，沒有 App 的安裝範圍控制與細緻權限；`project.md ## Mandated` 的「新增憑證型 secret 後須實地查證落在 secrets 而非 variables」適用。
2. **改用 fine-grained PAT** — Account permissions 底下有 Projects 項。代價同上，但範圍控制較 classic 好。
3. **把看板搬到真正的組織** — 需先建組織並轉移 repo 或 project。代價最大，但保住 App 路徑與 ADR-0015 §8 的原始設計。

**本站不裁定**——這是設計層變更，落點在 ADR。依 `project.md` 的處置形狀：標出缺口、寫明它讓哪些主張不成立、指派落點，**不逕自修改已通過 reviewer 的上游產出**。

## 本輪已完成的實測

| # | 項目 | 結果 |
| --- | --- | --- |
| 1 | Issues 寫入 | ✅ 實測通過（issue #538，ADR-0014 明文要求的那一項） |
| 1 | Contents write／Pull requests write | 宣告已正確；實測未做（會產生真實 commit／PR） |
| 1 | Projects 讀寫 | ❌ **不可行**——見上 |
| 2 | 單次操作上限 | 未做（需能寫入才有意義） |
| 3 | `createProjectV2Field` | 未做（同上） |
| 4 | A-1／A-2／A-3／A-8 | 未做 |
| PRE-1-a | Rulesets file-path restriction | 未做（獨立項） |

---

# PRE-1 實測結果（第四輪，2026-08-30T15:33:32Z）— **阻塞解除，剩兩件需人工動手**

## 結論：第三輪的「GitHub App 這條路不通」成立，但**「個人 Projects v2 無路可走」不成立**

第三輪的證據鏈本身沒有錯（`opendiamonds` 是個人帳號、App 的 installation 權限清單無對應個人 Projects v2 的項目），但它少查了一層：**當時使用的 token 根本沒有 `project` scope**。本輪換一個帶 `project` scope 的 token 重測，Project #16 的讀寫**都成立**。

| 探查 | 結果 |
| --- | --- |
| `opendiamonds` token scopes | `admin:public_key, gist, read:org, repo, workflow` — **無 `project`** |
| `Dannielchung` token scopes | `gist, project, read:org, repo` |
| 以後者讀 `user(login:"opendiamonds").projectV2(number:16)` | ✅ `PVT_kwHOD75-tc4BXNPFzg…`「Cloud-360 開發計劃」，`public: false`，71 個 item |
| `viewerCanUpdate` on #16 | ✅ **true**（不只讀，帶寫入） |
| `Dannielchung` 對 repo 的權限 | `write` |

`public: false` 卻讀得到 ⇒ 是明確的**協作者授權**，不是公開資源。

> **一個方法上的教訓**：GraphQL 對「有沒有權限」與「有沒有 scope」的回應形狀不同——缺**權限**回 `NOT_FOUND`（第三輪看到的），缺 **scope** 回 `INSUFFICIENT_SCOPES`（本輪對照組看到的）。第三輪只看到前者就結案，沒有換一個 token 做對照，因此把「這顆 token 不行」讀成「這條路不行」。

## 實測結果逐項

### 追加項 — `Issue.projectItems` 反查（U-3 `read_item` 的核心路徑）

`business-rules.md:57` 的 R-1.0 指出它「必須先被 PRE-1 實測確認可用」，但**它不在 `bolt-plan.md` 的 PRE-1 五項表內**，且 Bolt 1 的 DoD 只檢查第 1／3／4 項——本輪主動補測。

| 測試 | 結果 |
| --- | --- |
| issue #487（確定在 #16 板上）反查 | ✅ `totalCount: 1`，回出 #16 的 item |
| issue #538 加進**我建的測試 project** 後反查 | ❌ `totalCount: 0`（`includeArchived` 亦同） |
| 對照組：從 project 側看該 item | ✅ `totalCount: 1`，item 確實存在 |

排除替代解釋後的原因：**測試 project 的擁有者（`Dannielchung`）與 repo 擁有者（`opendiamonds`）不同**。實證來自 `linkProjectV2ToRepository` 的錯誤訊息：

```
Only projects owned by the same owner as the repository can be linked.
```

> **這一項改變 ADR-A3 的可操作性**：ADR-A3 要求對「獨立測試 Project」驗證，而**掛在別的帳號底下的測試 Project 碰不到 `Issue.projectItems` 這條路徑**——它會穩定回 `0`，看起來像 `read_item` 壞了，實際是組態不同。若照這樣測，U-3 會收到一個假紅燈；更糟的形狀是反過來——實作為了讓測試過而把 `0` 當成正常分支，那個分支在正式組態下永遠走不到。**測試 Project 必須建在 `opendiamonds` 名下。**

### 第 3 項 — `createProjectV2Field` **可用**

| 型別 | 結果 |
| --- | --- |
| `TEXT` | ✅ 建出 `AIDLC Stage` |
| `SINGLE_SELECT`（含選項） | ✅ 建出 `AIDLC Phase`，選項 `Ideation`／`Construction` 各自拿到 option id |

⇒ **[US:S-5 AC 2] 走「可自動建立」那一支**。`requirements.md` A-5 的更正（「未支援」的主體是 gh-aw 而非平台）由實測支持；原本擔心的「AC 2 的失敗分支被實作成死碼」不會發生，但該分支的可達前提改為**權限不足**，不是平台不支援。

### 第 2 項 — C-T5 框架單次操作次數上限

| 測試 | 結果 |
| --- | --- |
| 序列 40 次 `updateProjectV2ItemFieldValue` | ✅ 40／40 成功 |
| 並發 30 次 | ✅ 30／30 成功 |
| 每次成本 | **恰為 1 點**（4975 → 4935 → 4905） |
| 主要上限 | `limit: 5000` 點／小時 |
| secondary rate limit | 未觸發 |

⇒ **在直接呼叫 GraphQL 的路徑下，C-T5 不成立**——沒有「單次執行的操作次數上限」這種東西，綁住的是 5000 點／小時。對照 `U-7-reconcile-workflow/performance-requirements.md:35` 算出的現況上界 **26 次**，距離 5000 有兩個數量級。

**但 C-T5 沒有被完全回答**：它的來源 `[ext:E3]` 指的是 **gh-aw safe-outputs 的 `max:`**（本 repo 現有值都是 1 或 3）。那條路徑的**超限行為**（截斷／報錯／靜默略過）**本輪無法判定**——enforcement 的程式碼不內嵌在 `.lock.yml` 裡，靜態讀不出來。它只在 OQ-7 裁決為「走 gh-aw 承載」時才需要回答；裁決為腳本／直接 GraphQL 則不需要。

### 第 4 項 — A-1／A-2／A-3／A-8

| 假設 | 判定 | 證據 |
| --- | --- | --- |
| **A-1**（組織政策是否阻擋 App 安裝） | **不適用** | 沒有 `opendiamonds` 組織（`GET /orgs/opendiamonds` → 404），無政策可阻擋。第三輪已確立 |
| **A-2**（變數名與文件描述不一致） | **未成立**（名實相符） | `APP_ID` 存於 Actions **variables**、`APP_PRIVATE_KEY` 存於 **secrets**；第一輪以 `APP_ID` 的值成功鑄出 installation token ⇒ 該變數承載的確實是**應用程式識別碼**，不是用戶端識別碼 |
| **A-3**（看板更新行為如文件所述） | **部分推翻** | 寫入與回讀成立（`AIDLC Stage` = `construction / code-generation`），但**「依欄位名稱設定單選欄位、名稱不分大小寫」在 GraphQL 層不成立**（見下） |
| **A-8**（同步身分對 feature 分支的寫入權是否受分支保護阻擋） | **不受阻擋** | branch protection 僅 `main`／`ut` 兩條 pattern，**無任何 pattern 涵蓋 feature 分支**；兩條的 `restrictsPushes` 皆 false、`restrictions` 為 `null`（無 push 白名單）；repo rulesets 為 `[]` |

**A-3 的推翻部分（實測）**：

```
value:{text:"Construction"} → VALIDATION: Did not receive a single select option Id
value:{singleSelectOptionId:"b34fbf33"} → ✅
value:{singleSelectOptionId:"B34FBF33"} → VALIDATION: option Id does not belong to the field
```

⇒ GraphQL **只吃 option id、且大小寫敏感**。「依名稱、不分大小寫」是**框架便利層**的行為，不是平台行為。走直接 GraphQL 時 U-3 必須自己做 name→id 解析，並自行決定大小寫政策——而那是每個欄位額外一次讀取呼叫，需計入操作次數。

> **A-8 的判定有一個保存期限**：它是**目前的設定狀態**，不是機制保證。任何人日後為 feature 分支加一條 pattern 就會翻轉它，而 `[US:S-1 AC 6]`（每 push 一次多一張卡的攔截）正是為那個情境而設，**應予保留**。

### 憑證權限的直接實測（第 1 項的補完）

| 權限 | 身分 | 結果 |
| --- | --- | --- |
| Issues write | App | ✅ 第二輪已測（issue #538） |
| Projects 讀寫 | `Dannielchung` PAT | ✅ 本輪（`viewerCanUpdate: true`、實際建欄位與寫值） |
| Contents write | `Dannielchung` PAT | ✅ 本輪：建分支 → 寫入 `.pre1-probe` → **刪除分支**，全程可移除，已確認 404 |
| Pull requests write | — | ⏸ **刻意未測**：開 PR 會留下永久編號，而寫入身分尚未定案，測了可能要以另一個身分重測 |

### PRE-1-a — Repository Rulesets 的 file-path restriction：**不可行**

```
POST /repos/opendiamonds/cloud-360/rulesets  (target: push, enforcement: disabled)
→ 422 Validation Failed
   "Source public repos cannot have push rules"
   "Source only org-owned repos can have push rules"
```

**兩個獨立理由**，各自單獨即足以否決：repo 是 **public**（`visibility: public`），且擁有者是 **User** 而非 org。

後果（`PRE-1-checklist.md` 步驟 5 已預告）：

1. **[US:S-10 AC 5] 的第二個例子（「改 record 目錄以外的檔案應回 403」）在現行設計下無機制可產生**，該 AC 需回 user-stories 改寫。
2. `requirements.md` 的 **OQ-1**（「如何把 repo 內容寫入權收斂到最小……收斂只能靠其他手段」）少掉一個候選手段——ruleset 這條確定不通。
3. **這一項也約束了憑證拓樸的選擇**：即使把 repo 搬進真正的組織，`Source public repos cannot have push rules` 仍然成立——除非同時轉為 private。「搬去 org 就能用 path restriction」是不成立的推論。

## 需要你動手的兩件事

| # | 事項 | 為什麼只能你做 |
| --- | --- | --- |
| 1 | 給 `opendiamonds` 帳號的 token 補 `project` scope（`gh auth refresh -h github.com -s project`），或鑄一顆帶 `project` 的 classic PAT | 正式寫入身分應是 repo 與 project 的擁有者；目前該帳號的 token 缺這個 scope |
| 2 | 在 **`opendiamonds` 名下**建一個測試 Project（ADR-A3 用） | 跨帳號的測試 project 碰不到 `Issue.projectItems`（見上），而只有該帳號本人能建自己名下的 project |

第 1 件完成後，`Dannielchung` 這條路可以退場，寫入身分回到單一擁有者，不必引入跨帳號依賴。

## 待清理

| 項目 | 位置 | 說明 |
| --- | --- | --- |
| issue #538 | `opendiamonds/cloud-360` | 第二輪的實測產物，可直接關閉 |
| 測試 project「PRE-1 sync 實測（可刪）」 | `github.com/users/Dannielchung/projects/2` | 本輪產物。**保留待你檢視證據**（含 `AIDLC Stage`／`AIDLC Phase` 兩個欄位與 issue #538 的 item）；確認後可整個刪除——它因擁有者不符而**不能**充當 ADR-A3 的測試 Project |
| 探針分支 | — | 已刪除並確認 404，無殘留 |

## 對上游的影響（標出缺口，不逕自改上游）

| 落點 | 需要的處置 | 指派 |
| --- | --- | --- |
| `stories.md` §PRE-1 第 1 項、ADR-0015 §8 | 「**組織層**看板寫入權」的前提不成立，須改為個人帳號 Projects v2 ＋ `project` scope | 新 ADR（憑證策略），第三輪已標出 |
| `U-3 business-logic-model.md` | GraphQL 由 `organization(login:)` 改為 `user(login:)` | code-generation 實作 U-3 時 |
| `README.md`（U-11 已交付） | 連結 `github.com/orgs/…` → `/users/…` | 同上 |
| **ADR-A3** | 「獨立測試 Project」須加上**同擁有者**的限定，否則測不到 `Issue.projectItems` | 新 ADR 或 ADR-A3 修訂 |
| **[US:S-10 AC 5]** 第二個例子 | 無機制可產生，須改寫 | user-stories（Modify 模式） |
| `requirements.md` A-3 | 「依名稱、不分大小寫」須限定為框架路徑的行為 | 同上或 code-generation 就地記載 |
| `bolt-plan.md` PRE-1 五項表 ＋ Bolt 1 DoD | 補入 `Issue.projectItems` 為第 6 項（R-1.0 要求過但從未被承接） | delivery-planning 或 Bolt 1 開工前 |

---

# PRE-1 實測結果（第五輪，2026-08-30T15:50:52Z）— **阻塞解除，PRE-1 的四項全部有答案**

第四輪指派給人工的兩件事都已完成：`opendiamonds` 帳號的 token 現帶 `project` scope（實測 `gh auth status`：`admin:public_key, gist, project, read:org, repo, workflow`），測試看板 **#23「AIDLC sync 測試看板（PRE-1）」建在 `opendiamonds` 名下**（`viewerCanUpdate: true`）。**寫入身分自本輪起為單一擁有者 `opendiamonds`，`Dannielchung` 這條跨帳號路徑退場。**

## 逐項結果

### 追加項 — `Issue.projectItems` 反查：**可用，且條件是「同擁有者」而非「已連結 repo」**

第四輪只能證明跨帳號時回 `0`，無法分辨真正的條件。本輪刻意分兩步測：

| 步驟 | 操作 | 反查結果 |
| --- | --- | --- |
| A | 把 issue #538 加進 #23，**尚未** `linkProjectV2ToRepository` | ✅ `totalCount: 1`，回出 #23 的 item |
| B | 隨後才執行 `linkProjectV2ToRepository` | ✅ 成功（`opendiamonds/cloud-360`） |

⇒ **R-1.0 成立，且 U-3 不需要自行確保 repo↔project 連結**——連結與否不影響 `read_item` 這條路徑。第四輪那個 `Only projects owned by the same owner as the repository can be linked.` 的解釋本輪得到正面確認：同擁有者時 link 直接成功。

### 附帶發現 — project 側列舉有**短暫傳播延遲**

加入 item 後同一時刻：`Issue.projectItems` 已回 `1`，而 project 側 `items` 仍回 `0`；約 2 秒後兩側一致（連測三次皆 `1`）。

> **對 U-7 的意義**：reconcile 若緊接在 forward 寫入之後觸發，可能讀到尚未傳播的 project 側狀態，而它的判定邏輯會把「板上沒有這張卡」讀成需要補建——**產生重複卡片**。這正是 [US:S-1 AC 6] 要攔的形狀，但來源不同（不是重複 push，是自己的寫入還沒傳播）。指派 U-7 實作時納入考量。

### 新發現 — 測試看板的 Status 選項與正式看板**不同**，且可程式化對齊

| 看板 | Status 選項 |
| --- | --- |
| #23（測試，預設值） | `Todo \| In Progress \| Done` |
| #16（正式） | `Backlog \| Nice to have \| Ready \| In progress \| In review \| Done` |

**這是第四輪那個缺陷的同一種形狀，只是落在欄位層**：測試組態與正式組態不符，會讓 U-3 的映射邏輯對著一組正式環境不存在的選項名被驗證通過。已以 `updateProjectV2Field` 把 #23 的六個選項對齊 #16（實測成功），**但兩邊的 option id 不同**（#23 的 `In progress` 是 `07486f86`）。

⇒ **U-3 必須 per-project 在執行期解析 name→id，不得寫死 id**；且 ADR-A3 的「獨立測試 Project」限定除了第四輪加的「同擁有者」，還要加上**「Status 選項需與正式看板同名」**，否則測試通過不代表正式環境可用。

### 第 3 項 — `createProjectV2Field`：**可用**（於 #23 覆核）

`SINGLE_SELECT`（含選項）建立成功，選項各自拿到 id。⇒ **[US:S-5 AC 2] 走「可自動建立」那一支**，與第四輪結論一致，但本輪是在**符合 ADR-A3 條件的測試看板**上取得。

附帶：`updateProjectV2Field` 亦可用（可改既有單選欄位的選項集）——第四輪未測過的能力。

### A-3 — 在正確身分與合格測試看板上**完整覆核**（結論同第四輪）

| 寫法 | 結果 |
| --- | --- |
| `value:{text:"In progress"}` | ❌ `VALIDATION: Did not receive a single select option Id to update a field of type single_select` |
| `value:{singleSelectOptionId:"07486f86"}` | ✅ 成功；回讀 `Status = In progress (07486f86)` |
| `value:{singleSelectOptionId:"07486F86"}` | ❌ `VALIDATION: The single select option Id does not belong to the field` |

⇒ 「依名稱、不分大小寫」確定是**框架便利層**行為，非平台行為。走直接 GraphQL 時，每個單選欄位需額外一次讀取做 name→id 解析。

### 新增 — 錯誤分類法（U-3 的錯誤碼對應，此前「全新寫」無實測依據）

| 情境 | `type` | `message`（逐字） |
| --- | --- | --- |
| node id 不解析（不存在或無權限） | `NOT_FOUND` | `Could not resolve to a node with the global id of '…'` |
| itemId 屬於別的 project | `VALIDATION` | `The item does not exist in the project` |
| 單選欄位給了文字值 | `VALIDATION` | `Did not receive a single select option Id to update a field of type single_select` |
| option id 不屬於該欄位（含大小寫變體） | `VALIDATION` | `The single select option Id does not belong to the field` |

> `NOT_FOUND` **同時涵蓋「不存在」與「無權限」**（第三輪已因此誤判過一次）。U-3 不得把 `NOT_FOUND` 逕自對應成「這張卡不在板上」——那會在權限退化時靜默走上補建分支。

### 新增 — 分頁游標實測（#16，71 items，唯讀）

`items(first:2)` → `hasNextPage: true`、`endCursor` 可用；以 `after:` 帶入取得第二頁，內容不重疊。⇒ 游標分頁形狀確認可用。

### 第 1 項憑證 — Contents write 以**最終身分**實測

建分支 `pre1-probe-r5-155039`（**刻意不符 `ci.yml` 的 `main`／`ut`／`danniel/**`／`chore/**` 觸發樣式，故不起 CI**）→ 寫入 `.pre1-probe-r5`（commit `13b1cd4e`，author `opendiamonds`）→ 刪除分支並確認 `404` → 確認 `ut` 的 SHA 未變。

### 尚未測 — Pull requests write

開 PR 會在 public repo 留下**永久編號**，需人工確認後才做。附帶一個本輪浮現的觀察：寫入身分由 GitHub App 改為擁有者 token 之後，`repo` scope **整包**涵蓋 contents／issues／PR 寫入，**沒有 App 那種細緻權限可收斂**。這使 `requirements.md` 的 **OQ-1**（如何把 repo 內容寫入權收斂到最小）更難回答——PRE-1-a 已確定 ruleset 路徑不通，本輪確定憑證路徑也無細緻分項。此為憑證策略 ADR 必須正面處理的代價。

## 對上游的影響（新增／更新，仍不逕自改上游）

| 落點 | 需要的處置 | 指派 |
| --- | --- | --- |
| **ADR-A3** | 「獨立測試 Project」的限定條件由「同擁有者」再加一項：**Status 選項須與正式看板同名** | 憑證策略 ADR 或 ADR-A3 修訂 |
| **U-3 `business-logic-model.md`** | ①`organization(login:)` → `user(login:)`；②name→id 需 per-project 執行期解析，不得寫死；③`NOT_FOUND` 不得對應成「卡不在板上」 | code-generation 實作 U-3 時 |
| **U-7 `business-logic-model.md`** | project 側列舉有 ~2 秒傳播延遲，reconcile 緊接 forward 寫入時可能誤判為需補建 | code-generation 實作 U-7 時 |
| `requirements.md` **OQ-1** | 擁有者 token 無細緻權限分項，與 PRE-1-a 的 ruleset 不可行合計，收斂手段幾乎耗盡 | 憑證策略 ADR |

## 待清理（更新）

| 項目 | 位置 | 狀態 |
| --- | --- | --- |
| issue #538 | `opendiamonds/cloud-360` | 仍開著；現同時是 #23 的測試 item，**建議留到 U-3 驗完再關** |
| 測試 project「PRE-1 sync 實測（可刪）」 | `users/Dannielchung/projects/2` | **已被 #23 取代，可刪** |
| `AIDLC Stage r5` 欄位、`aidlc-sync-probe` 欄位 | 測試看板 #23 | 測試殘留，U-3 驗完後一併清 |
| 探針分支 `pre1-probe-r5-155039` | — | 已刪除並確認 404 |

## 第五輪追補（2026-08-30T15:54:48Z）— **PRE-1-b 三項全測，並揭出 R-1.4 的可達性問題**

初次撰寫本輪時只涵蓋 PRE-1-b 的 (a)，回頭核對 `bolt-plan.md:28` 與 `U-3/business-rules.md:59` 的逐字要求後補測 (b)(c)。

| PRE-1-b 子項 | 要求逐字 | 實測 |
| --- | --- | --- |
| (a) | 該欄位存在且可查 | ✅ 見上（`totalCount: 1`，同擁有者即可，不需 link） |
| (b) | 回傳結果可依 Project id 過濾（R-1.2） | ✅ 每個 node 帶自己的 `project.id`／`project.number`，過濾可實作 |
| (c) | 一個 issue 屬多個 Project 時的回傳形狀符合 R-1.4 的假設 | ✅ **形狀符合**：把 #538 同時加進 #21 與 #23 後，`projectItems` 回 `totalCount: 2`，兩筆各帶自己的 project ⇒ **R-1.2 的過濾是必須的，不是防禦性程式碼**（`business-rules.md:15` 的判斷得到實測支持） |

### ⚠️ 新發現 — **R-1.4 的錯誤分支，在本機制自己使用的路徑上不可達**

`business-rules.md:13` 的 R-1.4 為「過濾後多於一筆 → `ExternalError`，不猜哪一筆」。要觸發它，需要**同一個 issue 在同一個 Project 內有兩筆 item**。實測：

```
addProjectV2ItemById(project #23, issue #538)  第一次 → PVTI_lAHOD75-tc4Bh6ySzg4ntPs
addProjectV2ItemById(project #23, issue #538)  第二次 → PVTI_lAHOD75-tc4Bh6ySzg4ntPs（相同 id）
#23 items totalCount → 1
```

⇒ **`addProjectV2ItemById` 是冪等的**，重複加入回既有 item 而不建第二筆。

**限定範圍，不過度宣稱**：本輪只證明「**本機制自己會用的那個 mutation** 產生不出兩筆」。其他路徑（草稿 item 轉換、尚未知的 API 形狀）未測。

**處置建議（不是刪掉 R-1.4）**：R-1.4 原本的理由逐字是「同一個 issue 在同一個 Project 內出現兩筆 item 代表看板狀態已經壞了，猜一筆會讓機制在一個它無法理解的狀態上繼續寫入」——這個理由**在實測後反而更強**：既然機制自己造不出這個狀態，那它一旦出現就確實是機制無法解釋的外部狀態。R-1.4 作為防禦性斷言應**保留**。

真正受影響的是**驗證方式**：U-3 的完成判準若要求為各條規則寫出可達的反例，**R-1.4 這條寫不出來**。應明記它為「防禦性斷言，無可構造的反例」，而不是留給實作者去發明一個假的觸發途徑——那會產生一個永遠走不到、卻看起來被測過的分支（`project.md` 的 `functional-design:c10` 正是這個形狀）。

### 附帶 — `bolt-plan.md` 指名的留痕檔名與實際不符

`bolt-plan.md:19` 明訂留痕形式為「寫入 `<record>/construction/pre-1-findings.md`」，而本檔實際為 **`PRE-1-results.md`**，且 `pre-1-findings.md` **不存在**。Bolt 1 的 DoD 逐字要求「PRE-1 第 1／3／4 項已綠」與「PRE-1-b 已綠」，核對者若照 `bolt-plan.md` 找檔案會找不到。二選一：改檔名，或修訂 `bolt-plan.md` 的指名。列入 ADR-0016。

---

# PRE-1 實測結果（第六輪，2026-08-30T23:31:09Z）— ADR-0016 替代方案 B 的補測

ADR-0016 對「改用 fine-grained PAT」的否決理由逐字為「**未經實測**」，人工裁決要求補測後再定案。

## 結論：**B 不可行**（三個獨立來源 ＋ 一項第一手佐證），但補測過程**撞出一個 ADR-0016 §7 漏掉的收斂手段**

### B 不可行的依據

| # | 來源 | 內容 | 證據強度 |
| --- | --- | --- | --- |
| 1 | GitHub 官方文件（Managing your personal access tokens） | 明列「Using fine-grained personal access token to access Projects owned by a user account」為已知缺口；Account permissions 表**無任何 Projects 條目**，唯一的 Projects 權限是**組織層**的 `organization_projects` | 官方文件 |
| 2 | GitHub Changelog（2023-04-27） | fine-grained PAT 的 **GraphQL 限制已解除** ⇒ 阻礙**不是** GraphQL 本身，而是缺少個人帳號 Projects 的權限項 | 官方文件 |
| 3 | community discussion #156512 | 2026-05 有人回「要到 **Organizations** 分頁才看得到 Projects」，另一人回「我沒有 Organizations 分頁，而 Account 底下沒有 Projects」；2026-06 仍有人回報未支援。**無官方回應** | 二手回報，但時效近（三個月內） |

> **來源 3 的第一則回覆本身就是本 intent 已經踩過的陷阱**：GitHub 介面裡**兩個都叫 Projects**（Repository／Organization 各一），而個人帳號 Projects v2 不屬於任何一個。第二輪的結論逐字記載過同一個形狀。

### 第一手佐證（本輪自行實測）

以**沒有** `project` scope 的 `openchung` token 打同一組查詢，看 GitHub **自己**要求什麼：

```
user(login:"opendiamonds").projectV2(number:16)
→ INSUFFICIENT_SCOPES: The 'projectV2' field requires one of the following scopes:
  ['read:project'] … Please modify your token's scopes at: https://github.com/settings/tokens

addProjectV2ItemById(...)
→ INSUFFICIENT_SCOPES: The 'addProjectV2ItemById' field requires one of the following scopes:
  ['project'] …
```

兩點：

1. GitHub 要求的是 **scope**（`read:project`／`project`）。**scope 是 classic PAT／OAuth 的概念，fine-grained PAT 不以 scope 表達權限**，它表達的是 permissions——而 permissions 清單裡沒有個人帳號 Projects 這一項。
2. 錯誤訊息把使用者導向 **`https://github.com/settings/tokens`（classic token 頁）**，不是 `/settings/personal-access-tokens`（fine-grained 頁）。這是 GitHub 自己的錯誤訊息指向 classic。

**誠實標定證據強度**：這是**強佐證，不是決定性反證**。決定性的第一手測試需要真的鑄一顆 fine-grained PAT 並失敗——而依 §「B 不可行」的三個來源，那顆 token 連要勾的權限項都不存在。**若要 100% 排除，只需 30 秒**：開 fine-grained PAT 建立頁，看 **Account permissions** 底下有沒有 Projects 條目。三個來源都說沒有。

## ⚠️ 本輪的真正收穫 — **ADR-0016 §7 宣稱「收斂手段已耗盡」下得太早**

第一手佐證揭露的 scope 粒度，引出一個先前**完全沒被考慮**的收斂手段。官方 scope 文件逐字：

| scope | 文件原文 |
| --- | --- |
| `repo` | 「Grants full access to **public and private** repositories…」 |
| `public_repo` | 「**Limits access to public repositories.** That includes read/write access to code, commit statuses, repository projects, collaborators, and deployment statuses for public repositories…」 |
| `project` | 「Grants read/write access to **user** and organization projects.」 |
| `read:project` | 「Grants **read only** access to user and organization projects.」 |

**`opendiamonds/cloud-360` 是 public repo**（第四輪 PRE-1-a 實測 `visibility: public`，當時是作為 ruleset 不可行的理由之一）。因此：

- 憑證可用 **`public_repo` 取代 `repo`**——爆炸半徑由「該帳號可存取的**全部** repo，含私有」縮到「**公開** repo」。這不是路徑層級的收斂（仍非單一 repo），但它是一個**真實且未被評估過**的收斂。
- Projects 側也可**依讀寫分離**（`read:project` vs `project`）——對只讀路徑（例如對帳的讀取階段）有意義。

**同一個事實在第四輪被用過一次、方向相反**：public 當時是「ruleset 不可行」的**理由**；本輪它是「`public_repo` 可用」的**前提**。同一個事實同時關掉一扇門、開啟另一扇，而第一次只被記到關門那一側。

### 但這是**候選手段，不是已確立的事實**——必須實測

`public_repo` 的文件原文列舉的是「code, commit statuses, repository projects, collaborators, and deployment statuses」，**沒有逐字寫 issues 與 pull requests**。本機制需要 contents 寫入、**Issues 寫入**、**PR 寫入**三者。依 `stories.md` §PRE-1「不得以文件敘述代替驗證」，**不得**憑「歷來 `public_repo` 應該涵蓋 issues」就採用——那正是 ADR-0014 點名的 K-1 誤解（把 Issues 當成 Contents 的一部分）換一個外衣。

**指派**：新增 **PRE-1-c**——鑄一顆 `public_repo` ＋ `project` 的 classic PAT，對測試看板 #23 與 repo 實測四條寫入路徑（Projects 寫入、contents 寫入、開 issue、開 PR）。任一條失敗即退回 `repo`，並如實記載「`repo` 為必要而非便宜行事」。

## 待清理（無新增）

本輪只做唯讀查詢與兩次必然失敗的 scope 探測，未產生任何副作用。

---

## 更正（2026-08-31T00:37:44Z）— 一則跨三輪傳播的錯誤引用

第三輪的「對上游影響」表逐字寫「**U-3 `business-logic-model.md`** | GraphQL 使用 `organization(login:...)` | 須改為 `user(login:...)`」。該宣稱**經實測為誤**：`grep -rn "organization(" construction/U-3-board-client/` **零命中**——U-3 的 functional-design 產出**從未指定 GraphQL 查詢根**。

**傳播路徑**：第三輪（`:162`）→ 第四輪（`:321`）→ 第五輪（`:408`）→ ADR-0016 §4.1 初版。**四次書寫，零次核對。**

**實質結論不變**（查詢根必須是 `user(login:)`），但**性質改變**：這是**缺口待補**，不是「改為」。差別不是措辭——照原文去 U-3 找 `organization(login:)` 來改的人會找不到任何東西，並可能因此以為這一項已經有人做過了。

ADR-0016 §4.1 已更正。歷史輪次的原文**不回改**（它們如實記載了當時的判斷），本節即為其更正。

**這是本 intent 對 `project.md` 「引用逐字核對——每個來源標籤開檔驗證，不憑印象」的又一次違反**，且形狀特別清楚：錯誤在第三輪產生時只是一個未核對的推測，之後三次書寫都是**從自己的前一份產出抄過來**，沒有任何一次回到被引用的檔案。

