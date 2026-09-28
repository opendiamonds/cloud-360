# ADR 0016: 憑證拓樸由組織層 GitHub App 改為擁有者帳號 token，及 PRE-1 實測揭出的上游修訂集

- Status: Accepted
- Date: 2026-08-30（本檔建立於 2026-08-30T15:54:48Z，讀自 `date -u`）
- Amended: 2026-08-30T23:31:09Z（PRE-1 第六輪：**§7 的「收斂手段已耗盡」被自己的補測推翻**，新增 PRE-1-c；Alternatives B 的否決理由由「未經實測」改為實測結果，且其原文對 fine-grained PAT 權限清單的描述**是錯的**，一併更正；ADR-0006 的 IAM 面判定同步改寫）
- Amended: 2026-08-31T00:37:44Z（就地指標落地至全部 Amends 目標；§4.1 的來源引用經 grep 實測為誤並更正；§10 由一條 AC 增為兩條；**E-1 的外部依賴性判定為已消失**）
- 節數：**10**
- Amends: **`inception/decisions/0015-...md`** 的 §8（權限集合的「組織層」前提）、**`inception/requirements-analysis/requirements.md`** 的 NFR-S1／A-3／OQ-1、**`inception/user-stories/stories.md`** 的 §故事依賴與排序 PRE-1 列、**`inception/delivery-planning/bolt-plan.md`** 的 PRE-1 表第 1 項、**PRE-1-a 的前提措辭**、**新增 PRE-1-c 一列與其註記**、**Bolt 1 的 DoD**、Bolt 0 留痕檔名與項數（五→七）、**`inception/application-design/decisions.md`** 的 ADR-A3、**`inception/delivery-planning/`** 的 `external-dependency-map.md`（E-1）／`team-allocation.md`／`risk-and-sequencing-rationale.md`、**`construction/U-3-board-client/functional-design/`** 的 `business-logic-model.md` 與 `business-rules.md`、**`README.md`**（U-11 已交付）。各原文皆維持，本 ADR 只更正其中被本文點名的部分。

## Context

`construction/PRE-1-results.md` 的五輪實測推翻了一個貫穿全部上游的傳遞假設：**`opendiamonds` 是組織**。

證據鏈（第三輪，三項獨立來源一致）：`GET /users/opendiamonds` 回 `type: User`；`GET /repos/opendiamonds/cloud-360` 回 `owner.type: User`；`GET /orgs/opendiamonds` 回 **404**。Project #16 的網址為 `github.com/users/opendiamonds/projects/16`。

這使 ADR-0015 §8 所要求的四項權限中的第一項（**組織層** Projects 讀寫）**無從授予**——GitHub App 的 installation 權限清單裡 `organization_projects` 只涵蓋組織的 Projects v2，沒有對應個人帳號 Projects v2 的項目。App 設定裡 `organization_projects: write` 確實存在（`GET /app` 實測），但 installation 的已授予權限始終沒有它：**不是沒批准，是授予目標不存在**。

第三輪據此結論「這條路不通」，該結論**本身有一個方法上的缺陷**，由第四輪推翻：當時使用的 token 根本沒有 `project` scope。GraphQL 對「缺權限」回 `NOT_FOUND`、對「缺 scope」回 `INSUFFICIENT_SCOPES`，第三輪只看到前者就結案，沒有換 token 做對照，因此把「這顆 token 不行」讀成「這條路不行」。第四、五輪換上帶 `project` scope 的擁有者 token 後，Project #16 的讀寫**都成立**。

**本 ADR 是這些修訂唯一有效的承載形式。** 先例為同一 intent 的 ADR-0014 與 ADR-0015：在單元產出或 stage 記錄裡寫「指派 X」，對已定稿的上游而言是一張沒有收件人的便條。

## Decision

### 1. 憑證身分改為**擁有者帳號 token**，GitHub App 路徑退場

同步機制的寫入身分為 `opendiamonds` 帳號的 token，需帶 `project` scope（涵蓋個人帳號 Projects v2）與 `repo` scope。實測已確認該 token 現有 scopes 為 `admin:public_key, gist, project, read:org, repo, workflow`。

跨帳號的 `Dannielchung` 路徑（第四輪為突破阻塞而暫用）**退場**：寫入身分回到單一擁有者，不引入跨帳號依賴。

### 2. 權限集合的表述——「組織層」前提作廢，且**四項不再是可分別授予的四項**

ADR-0015 §8 把權限集合更正為四項（組織層 Projects 讀寫、repo 內容寫入、Issues 寫入、Pull requests 寫入），該更正的**分項判斷仍然正確**，但它預設的授予機制（GitHub App 的細緻權限勾選）已不適用。

改述為：

- **Projects 讀寫** — 由 token 的 `project` scope 承載（**個人帳號層**，非組織層）。
- **repo 內容寫入、Issues 寫入、Pull requests 寫入** — 由 token 的 `repo` scope **整包**承載，**無法分別授予或分別收斂**。

`requirements.md` NFR-S1 的驗收判準**字面**為「憑證實際被授予的權限集合等於上述**兩項**，無額外授予」（ADR-0014 已把集合改為三項、ADR-0015 §8 再改為四項並下達「同步改為四項」的指令，但 `requirements.md` 該欄的判準字串**本身從未被編輯**）。無論取兩項、三項或四項，該判準**在新拓樸下都結構性不可滿足**——`repo` scope 必然帶來遠多於四項的權限。判準改為：**憑證所需的 scope 集合為 `project` ＋ `repo` 兩項，且不含 `admin:*`、`delete_repo`、`workflow` 以外的額外 scope**；`repo` 的過度授予改列為**已知殘餘風險**（見 §7），不再偽裝成可通過的驗收項。

同步修訂 `bolt-plan.md` PRE-1 表第 1 項與 `stories.md` §故事依賴與排序的 PRE-1 列（「組織層看板寫入權」→「個人帳號 Projects v2 寫入權」）。

### 3. ADR-A3 的「獨立測試 Project」增列**兩個**限定條件

原文只要求「獨立於 #16」。實測顯示不足：

1. **必須與 repo 同擁有者**。掛在別的帳號底下的測試 Project 碰不到 `Issue.projectItems`——它會穩定回 `0`，看起來像 `read_item` 壞了。更糟的形狀是反過來：實作為了讓測試過而把 `0` 當成正常分支，那個分支在正式組態下永遠走不到。實證來自 `linkProjectV2ToRepository` 的錯誤訊息逐字：`Only projects owned by the same owner as the repository can be linked.`
2. **Status 欄位的選項名稱必須與 #16 一致**（`Backlog／Nice to have／Ready／In progress／In review／Done`）。新建 Project 的預設值是 `Todo／In Progress／Done`；照預設值測，U-3 的映射邏輯會對著一組正式環境不存在的選項名被驗證通過。

現行測試看板為 **#23「AIDLC sync 測試看板（PRE-1）」**（`opendiamonds` 名下），選項已以 `updateProjectV2Field` 對齊 #16。**但兩邊的 option id 不同**——對齊是組態上的補救，不是設計上的保證，故本節把它升格為 ADR-A3 的限定條件。

### 4. U-3 的三處實作修正

| # | 落點 | 原設計 | 改為 |
| --- | --- | --- | --- |
| 4.1 | U-3 的 functional-design 產出（GraphQL 查詢根） | **未指定**〔本列於 2026-08-31T00:37:44Z 更正：初版寫「原設計為 `organization(login:...)`」，該宣稱**經 grep 實測為誤**——`organization(` 在 `U-3-board-client/` 全樹**零命中**。誤述源自 `PRE-1-results.md` 第三輪，未經核對即傳播至第四、五輪與本 ADR 初版〕 | **須指定為 `user(login:...)`**。性質是**缺口待補**而非「改為」——設計從未指定查詢根，去找 `organization(login:)` 來改的人會找不到東西 |
| 4.2 | 單選欄位寫入 | 隱含可依名稱寫入 | **必須 per-project 在執行期解析 name→id**，不得寫死 id（#16 與 #23 的 option id 不同）。實測：`value:{text:"In progress"}` 回 `VALIDATION: Did not receive a single select option Id...`；`value:{singleSelectOptionId:"07486f86"}` 成功；大小寫變體回 `VALIDATION: The single select option Id does not belong to the field` |
| 4.3 | 錯誤碼對應 | 未定 | **`NOT_FOUND` 不得逕自對應成「這張卡不在板上」**——它同時涵蓋「不存在」與「無權限」，第三輪已因此誤判過一次。誤對應的後果是權限退化時靜默走上補建分支，**不會紅燈** |

實測建立的錯誤分類法（逐字訊息）：

| 情境 | `type` | `message` |
| --- | --- | --- |
| node id 不解析（不存在或無權限） | `NOT_FOUND` | `Could not resolve to a node with the global id of '…'` |
| itemId 屬於別的 project | `VALIDATION` | `The item does not exist in the project` |
| 單選欄位給了文字值 | `VALIDATION` | `Did not receive a single select option Id to update a field of type single_select` |
| option id 不屬於該欄位 | `VALIDATION` | `The single select option Id does not belong to the field` |

另：`Issue.projectItems` 的反查條件是**同擁有者**，**不需要** `linkProjectV2ToRepository`——實測在未連結狀態下即回 `totalCount: 1`。U-3 因此**不需**自行確保 repo↔project 連結。

### 5. U-7 需處理 project 側列舉的**傳播延遲**

實測：把 item 加進 project 後，`Issue.projectItems` 已回 `1` 而 project 側 `items` 仍回 `0`，約 2 秒後兩側一致。

reconcile 若緊接在 forward 寫入之後觸發，會把「板上沒有這張卡」讀成需要補建而**產生重複卡片**。這與 [US:S-1 AC 6] 要攔的是同一種傷害，但來源不同（不是重複 push，是自己的寫入尚未傳播），故 AC 6 現有的攔截機制不必然涵蓋它。指派 U-7 的 code-generation 正面處理。

### 6. R-1.4 **保留**，但標記為「防禦性斷言，無可構造的反例」

`U-3/business-rules.md:13` 的 R-1.4（過濾後多於一筆 → `ExternalError`）需要「同一 issue 在同一 Project 內有兩筆 item」才會觸發。實測 `addProjectV2ItemById` **冪等**：對同一 (project, issue) 重複呼叫回**相同的 item id**，`totalCount` 維持 1。

**限定範圍**：只證明「本機制自己會用的那個 mutation 產生不出兩筆」，其他路徑未測。

R-1.4 原本的理由逐字為「兩筆代表看板狀態已經壞了，猜一筆會讓機制在一個它無法理解的狀態上繼續寫入」——實測後這個理由**更強**：既然機制自己造不出這個狀態，它一旦出現就確實是機制無法解釋的外部狀態。故**保留規則**，但 U-3 的完成判準須明記此條**無可構造的反例**，不得要求實作者發明一個假的觸發途徑。那會產生一個永遠走不到、卻看起來被測過的分支——`project.md` 的 `functional-design:c10` 正是這個形狀。

### 7. OQ-1 的收斂手段**尚未耗盡**——`repo` → `public_repo` 是未評估過的候選，須以 PRE-1-c 實測

> **本節於 2026-08-30T23:31:09Z 整節改寫。** 初版逐字宣稱「收斂手段**已耗盡**」，並據此把 OQ-1 降級為殘餘風險。該宣稱在**同一天稍後**被為了補測 Alternatives B 而做的 scope 探查推翻——推翻它的事實（repo 為 public）**第四輪就已實測記載**，只是當時只被記到「ruleset 不可行」那一側。初版的錯不在缺資料，在於**沒有把已有的事實往另一個方向再問一次**就下了「耗盡」這種終局定性。原文保留於下方表格，判定欄已更正。

`requirements.md` OQ-1 逐字為「**如何把 repo 內容寫入權收斂到最小**……GitHub App 無路徑層級的權限限制，故收斂只能靠其他手段」。候選手段逐一判定：

| 候選手段 | 判定 | 依據 |
| --- | --- | --- |
| GitHub App 的路徑層級限制 | 不存在 | OQ-1 原文即已認定 |
| Repository Rulesets 的 file-path restriction | **不可行** | PRE-1-a 實測：`422 Source public repos cannot have push rules` ＋ `Source only org-owned repos can have push rules`。**兩個獨立理由各自單獨即足以否決**；即使搬進真組織，public 這一條仍成立——「搬去 org 就能用 path restriction」是不成立的推論 |
| App 的細緻權限分項 | **隨 §1 一併失效** | 擁有者 token 的 `repo` scope 整包涵蓋 contents／issues／PR 寫入 |
| 分支保護 | 不涵蓋 | 實測 branch protection 僅 `main`／`ut` 兩條 pattern，無 pattern 涵蓋 feature 分支（A-8） |
| **`public_repo` 取代 `repo`** | **候選，待 PRE-1-c 實測** | 官方 scope 文件逐字：`repo` 為「public **and private**」，`public_repo` 為「**Limits access to public repositories**」。本 repo 為 public（第四輪實測 `visibility: public`）⇒ 爆炸半徑可由「該帳號可存取的全部 repo，含私有」縮到「公開 repo」 |
| **Projects 側讀寫分離** | **候選，待 PRE-1-c 實測** | `read:project`（唯讀）與 `project`（讀寫）為兩個獨立 scope，本輪以 `INSUFFICIENT_SCOPES` 錯誤第一手確認：讀 `projectV2` 要 `read:project`，`addProjectV2ItemById` 要 `project` |

**處置**：OQ-1 **維持開放決策**，收斂目標由原本的「收斂到 record 目錄」（已確定無機制可達）改為**可達的次佳目標**：把憑證的爆炸半徑限制在公開 repo。

**新增 PRE-1-c（阻擋 Bolt 1）**：鑄一顆 **`public_repo` ＋ `project`** 的 classic PAT，對測試看板 #23 與本 repo 實測**四條寫入路徑**——Projects 寫入、contents 寫入、開 issue、開 PR。

> **為什麼不能直接採用**：`public_repo` 的文件原文列舉「code, commit statuses, repository projects, collaborators, and deployment statuses」，**沒有逐字寫 issues 與 pull requests**。憑「歷來應該有涵蓋」就採用，正是 ADR-0014 點名的 **K-1 誤解**（把 Issues 當成 Contents 的一部分）換一個外衣——而那個誤解的特性是**會讓 PRE-1 通過而 Bolt 1 失敗**。

任一條失敗即退回 `repo`，並如實記載「`repo` 為**必要**而非便宜行事」。**在 PRE-1-c 有結果之前，不得把 `repo` 的過度授予寫成「無可避免」。**

無論 PRE-1-c 結果為何，仍存在的殘餘風險：憑證對本 repo 具有完整寫入權，無機制可將其收斂到 record 目錄。緩解為偵測面（U-4 的 `Rejected` 紅燈與通報、每日對帳）與流程面（憑證存於 secrets 而非 variables，並依 `project.md ## Mandated` 實地查證）。

### 8. Bolt 0 的留痕檔名須與實際一致

`bolt-plan.md:19` 明訂留痕形式為「寫入 `<record>/construction/pre-1-findings.md`」，實際證據檔為 **`construction/PRE-1-results.md`**，而 `pre-1-findings.md` **不存在**。Bolt 1 的 DoD 逐字要求「PRE-1 第 1／3／4 項已綠」與「PRE-1-b 已綠」，核對者照 `bolt-plan.md` 找檔案會找不到。

**定案**：以 `PRE-1-results.md` 為正本，修訂 `bolt-plan.md:19` 的指名。理由是證據已在該檔累積五輪，改檔名會斷開既有引用。

### 9. `README.md` 的看板連結形狀

U-11 已交付的 `README.md` 連結為 `github.com/orgs/opendiamonds/projects/16`，正確形狀是 **`/users/`**。

> **U-11 的 reviewer 為什麼沒抓到**：它核對的是「組織名經 `git remote -v` 屬實」——**只驗了名字，沒驗它是不是組織**；且自陳「專案編號本身因 `gh` token 缺 `read:project` scope 無法外部驗證」。這是**驗證了較弱命題卻結案**的形狀，已列入本 intent 的學習候選。

### 10. 兩條已核可 AC 須回 user-stories 改寫（Modify 模式）

該例（「改 record 目錄以外的檔案應回 403」）在現行設計下**無機制可產生**——見 §7 的 ruleset 實測。`U-3/business-logic-model.md:89` 已記載此缺口（「介面不提供，但**產生不出 403**」）。改寫落點為 user-stories 的 Modify 模式，**非本 ADR 裁定內容**，此處只確立其必要性。

**第二條：[US:S-5 AC 2] 的 Given**（2026-08-31T00:37:44Z 增列）。該 Given 列三種「任一情形」，其中兩處待處理：①「憑證缺少**組織層** Projects 寫入權」的前提作廢，應讀作個人帳號 Projects v2；②「**組織政策阻擋**欄位建立」**不可達**——無組織即無組織政策。

**不阻擋實作**（Given 為「任一情形」，另兩支可達），但兩點值得記：U-3 的 `CannotCreate` 可達前提應由三種收斂為**兩種**（憑證缺 Projects 寫入權、同名欄位型別不同）；且本 AC 的改寫理由逐字寫著「不改寫的話……會被實作成永遠走不到的死碼」，而**改寫後的版本自己又帶進一條不可達分支**——同一種缺陷從修正動作本身再次進入。

## ADR-0006 Security Baseline 四面向判定

`project.md ## Mandated` 要求對每一項變更逐項判定，不得僅以「已有 ADR-0006」帶過。

| 面向 | 判定 | 理由與處置 |
| --- | --- | --- |
| **IAM** | **不合規，處置待 PRE-1-c** | 憑證由可細緻授權的 App 改為擁有者 token，權限**擴大**。**收斂手段未耗盡**——`public_repo` 取代 `repo` 可把爆炸半徑縮到公開 repo，待 PRE-1-c 實測（§7）。在該實測有結果之前，本列**不得**被讀成「已知並接受」的結案狀態 |
| **Encryption** | 合規 | 憑證存於 GitHub Actions secrets（靜態加密、log 中遮罩），不入版控。**必須依 `project.md ## Mandated` 實地查證它落在 secrets 而非 variables**——本 repo 為 public、Actions log 公開可讀 |
| **Network exposure** | N/A | 本變更不新增對外監聽端點，全部流量為對 GitHub API 的出向呼叫 |
| **Audit logging** | 合規且**改善** | 擁有者 token 的操作在 GitHub 稽核紀錄中歸屬於一個真實帳號。**但這正是 IAM 面代價的另一面**：機制的自動寫入與該帳號的人工操作在稽核紀錄中**難以區分**，不像 App 有獨立的 `[bot]` 身分。此為新引入的可觀測性損失，應在 U-5 的通報內容中以機制自己的標記補償 |

## Consequences

- **正面**：阻塞解除。PRE-1 的四項實測項加 PRE-1-a、PRE-1-b 共六項全部有答案，U-3 起的實作有實測依據而非文件推測。
- **正面**：`createProjectV2Field` 與 `updateProjectV2Field` 均實測可用 ⇒ [US:S-5 AC 2] 確定走「可自動建立」那一支。
- **正面**：C-T5（框架單次操作次數上限）在直接 GraphQL 路徑下不成立——序列 40 次與並發 30 次全成功，每次恰 1 點，上限是 5000 點／小時，對照 U-7 算出的現況上界 26 次差兩個數量級。
- **負面**：權限收斂能力**淨損失**。這是本 ADR 最實質的代價，且無技術緩解。
- **負面**：稽核紀錄中機制身分與人工身分混同（見上表）。
- **中性**：Pull requests write 仍未實測——開 PR 會在 public repo 留下永久編號。擁有者 token 的 `repo` scope 在機制上已涵蓋它，資訊價值遠低於 App 時期，故不強制在 Bolt 0 補測；若要補，落點為 Bolt 3（U-8）開工前。

## Alternatives Rejected

- **A. 維持 GitHub App，把 Project #16 搬到真正的組織。** 保住 ADR-0015 §8 的原始設計與細緻權限收斂，是**唯一能改善 IAM 面**的選項。否決理由：需先建組織、再轉移 repo 與 project（71 個 item 的看板），涉及既有 issue、PR、CI secrets 與部署設定的連帶遷移，代價遠超本 intent 的範圍；且 §7 已證明**即使搬進組織，ruleset 路徑仍因 public 而不通**——它換不回 OQ-1 想要的那個收斂手段。**保留為未來獨立 intent 的候選。**
- **B. 改用 fine-grained PAT。** ~~Account permissions 底下有 Projects 項，範圍控制較 classic PAT 好。~~ **此描述為誤，於 2026-08-30T23:31:09Z 的補測更正：fine-grained PAT 的 Account permissions 清單裡\*\*沒有\*\*個人帳號 Projects 條目**，唯一的 Projects 權限是組織層的 `organization_projects`——而本帳號不是組織（§Context）。

  **否決理由（初版為「未經實測」，人工裁決要求補測後改寫）**：三個獨立來源一致——官方文件明列「以 fine-grained PAT 存取個人帳號擁有的 Projects」為已知缺口；2023-04-27 的 changelog 顯示 fine-grained PAT 的 GraphQL 限制**早已解除**，故阻礙不是 GraphQL 而是缺少該權限項；community discussion #156512 在 2026-05／06 仍有人回報未支援且無官方回應。**第一手佐證**：GitHub 對 `projectV2` 要求 scope `read:project`、對 `addProjectV2ItemById` 要求 scope `project`，而 **scope 是 classic PAT／OAuth 的概念，fine-grained PAT 不以 scope 表達權限**；該錯誤訊息並把使用者導向 classic token 頁。

  **證據強度誠實標定**：強佐證，非決定性反證。決定性測試需真的鑄一顆 fine-grained PAT 並失敗，但依上述三個來源，它連要勾的權限項都不存在。**30 秒即可 100% 排除**：開 fine-grained PAT 建立頁，看 Account permissions 底下有無 Projects 條目。

  **B 的補測有一個非預期的正面產出**：為了取得第一手佐證而做的 scope 探查，揭露了 `public_repo` 這個先前未評估的收斂手段，直接推翻本 ADR 初版 §7 的「已耗盡」定性。**這是「補測一個已幾乎確定會被否決的選項」所換到的東西**，記於此作為該裁決的價值證明。
- **C. 沿用第四輪的 `Dannielchung` 跨帳號 token。** 它已被證明可行。否決理由：寫入身分與 repo／project 擁有者不同，`Issue.projectItems` 對跨帳號 project 回 `0`（§3 第 1 點），且引入一個與專案所有權無關的個人依賴——該帳號的權限異動會無預警破壞機制。
- **D. 不改上游，讓 U-3 就地吸收落差。** 否決理由：落差橫跨 ADR-0015 §8、`requirements.md` NFR-S1／OQ-1、`stories.md`、`bolt-plan.md`、ADR-A3 五份已核可文件，其中三份彼此矛盾。`project.md` 明訂「發現已核可上游的契約缺口時，標出缺口、指派具體落點與具體修法，不逕自修改已通過 reviewer 的上游產出」——ADR 是那個承載形式。

## Risk

- **R1**：`opendiamonds` token 為 OAuth token（`gho_`），其有效期與撤銷由該帳號的授權狀態決定。憑證失效的症狀是全部寫入路徑同時失敗——**症狀明顯，不是靜默失效**，由 U-5 的通報承接。
- **R2**：§3 的兩個限定條件是**組態上的約束，無機制強制**。有人日後新建一個測試看板而未對齊 Status 選項，U-3 的測試會綠而正式環境會壞。緩解：U-9 的 selftest 應斷言測試看板的選項集與 #16 一致。**此項為本 ADR 新指派，落點 U-9 的 code-generation。**
- **R3**：A-8（feature 分支不受分支保護阻擋）是**目前的設定狀態，不是機制保證**。任何人日後為 feature 分支加一條 pattern 就會翻轉它。[US:S-1 AC 6] 正是為那個情境而設，**應予保留**。

## Reversibility

**中等。** 憑證身分是 config（一個 secret 的值與 workflow 中的引用），換回 App 只需重設 secret——但那要先有一個真正的組織，即 Alternatives A 的全部代價。§3〜§6 的實作修正是程式碼層，可隨時再改。
