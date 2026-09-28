**Collaborator:** aidlc-developer-agent

## Contribution

視角：可實作性與故事尺寸。以下每一項都回 repo 實測過，證據附 `file:line`；未實測者一律標明。**沒有一項是背書。**

---

### 1. S-2 AC 11 與已核可的 C-T7 直接矛盾（Critical，必須改寫）

AC 11 寫「**該次執行**未發出任何對語言模型的呼叫」。這條把 requirements 的 FR-B2（其 AC 是「對照表的**實作**可在不呼叫任何 LLM 的情況下對給定的 record 輸出唯一 Status」）從「判定邏輯」擴大到「整次 workflow 執行」。後果是它**單方面刪掉了 C-T7 明文允許的一個承載選項**：

> C-T7 本站處置（`requirements.md`）：「FR-B2 的『決定性邏輯』須落在純 Actions 步驟**或 gh-aw 的非 LLM 環節**」

gh-aw 編譯出的 workflow 必然含 agent 執行步驟（`engine: copilot`，見 `.github/workflows/ui-regression.md:13`），`pre-agent-steps`（`:40`）只是它之前的確定性前置步驟——**同一次執行仍會呼叫 LLM**。所以在 AC 11 的字面下，「gh-aw 的非 LLM 環節」這個選項為 0，只剩純 Actions。這是 inception 階段新增了上游沒有的需求，違反 `phases/inception.md` 的 Traceability（「Do not introduce new requirements in inception without documenting their origin」）。

順帶一提，這個承載選項本來也有實測上的減分項，值得寫進 artifact 供 application-design 引用：**gh-aw v0.81.6 會在編譯 `pre-agent-steps` 時靜默剝除 `timeout-minutes` 且回報 0 errors / 0 warnings**（`.github/workflows/ui-regression.md:23-28`），該檔同時記載 PR #510 因此燒掉約 7 小時 runner 時間、零測試執行（`:17-21`）。但「這個選項比較差」與「這個選項被一條 AC 悄悄刪掉」是兩件事，後者才是缺陷。

**另有分類問題**：AC 11 是**artifact 層的靜態性質**（workflow 定義檔裡有沒有 agent step），不是執行期黑箱可觀察的行為。draft 在 S-2 的切線註記寫「本站不建議把 AC 11 單獨切出——它是①的執行方式約束，沒有自己的可展示成果」，這與 `project.md ## Corrections`（`units-generation:c6`）正好相反：該條說的正是「執行期契約」與「建置期資產」不得併入同一單元，因為「這個單元完成了嗎」會同時指涉兩種不可互相替代的判準。AC 11 的失敗模式（有人把映射邏輯搬進 gh-aw prompt）由**CI 對 workflow 檔的靜態檢查**抓，與 AC 1–7 的 dry-run fixture 不同類。

**建議改寫**（把一條擴權且錯位的 AC 拆成兩條各自可判的）：

- **S-2 AC 11（改）**：**Given** 同一個 record 輸入，**When** 映射判定連續執行 3 次，**Then** 三次輸出的 Status 完全相同（判定為決定性，無執行間變異）。[req:FR-B2]
- **S-10 新增 AC 5**：**Given** 承載對照表判定的 job 定義，**When** 檢視該 job 的步驟清單，**Then** 其中不含任何代理式引擎步驟（`engine:` 宣告或編譯後的 agent step）；把該步驟改為由 agent 產生 Status 時，此斷言失敗。[req:FR-B2]

第二條同時滿足 `user-stories:c4`（恆真的 AC 改寫而非刪除，把它移到碰得到真實失敗面的層次）與 S-10 既有 AC 3 的突變驗證形狀。

---

### 2. S-2 AC 7 的 oracle 不存在（Critical）

AC 7 的 Then 是「讀到的值**與 AI-DLC 引擎 `getField()` 讀到的值相同**」。要斷言「相同」，必須能機械地取得引擎那一側的值。實測**取不到**：

- `getField` 只在 `.claude/tools/aidlc-lib.ts:2676` 匯出為函式，沒有任何 CLI 把它的結果印出來。`aidlc-utility.ts` 的子命令表（`:5347-5434`）只有 `status`／`doctor`／`config-get`／`scope-table`／`stage-table` 等，沒有讀取任意 state 欄位的入口；`aidlc-runtime.ts:1420` 明列合法子命令僅 `compile, read, summary, fragment-fork, fragment-merge`，`read` 讀的是 `runtime-graph.json` 不是 `aidlc-state.md`。
- 就算改成「測試時直接 import `aidlc-lib.ts`」，也撞上 ADR-0012 §6 的硬約束（`0012-...md:103`：「同步機制不得修改 AI-DLC 主流程，也不得在 `.claude/` 下新增任何檔案」）與其升級韌性理由（`:105`）。把驗證層綁死在會被 upstream 整批覆蓋的檔案上，等於在下一次 `/aidlc` 升級時無聲失效。

也就是說 AC 7 目前不是驗收標準，是一句宣稱。**修法是把 oracle 換成行為 fixture**——requirements FR-J6 本文已經把語意逐條寫出來了（行錨定、全檔搜尋、第一個 match 即回傳、找不到回 `null` 而非空字串），直接展開成四條二元可判的 AC 即可，全部可用純文字 fixture 驗，不需要引擎在場：

- **7a**：**Given** 一個在正式欄位之前另有一行 `- **Current Stage**: <舊值>` 的 record，**When** 機制解析該欄位，**Then** 讀到的是**第一個** match 的值（`<舊值>`），不是最後一個。
- **7b**：**Given** 一個欄位存在但值為空（`- **Parked**: ` 後無內容）的 record，**When** 解析，**Then** 讀到空值，而**不是**下一行的內容。（實測依據：`aidlc-lib.ts:2680-2682` 的註解明寫用 `[ \t]*` 而非 `\s*` 正是為了不跨行）
- **7c**：**Given** 一個完全沒有該欄位行的 record，**When** 解析，**Then** 結果為「不存在」，且與 7b 的「存在但空」走**不同**的後續分支。（此條直接保護 S-4 AC 1 的「`Parked` 非空」判定：本 record 的 `## Runtime State` 只有 `- **Revision Count**: 0`，`Parked` 是**缺席**不是空值，兩者混同會讓 park 特判永遠不觸發）
- **7d**：**Given** 一行縮排的 `  - **Current Stage**: X`，**When** 解析，**Then** 不視為 match（行錨定要求行首即 `- `）。

---

### 3. 對照表不是全函式——S-2 AC 1–4 有一個未定義的常駐狀態（Major）

實測本 space 的 6 個 record（`aidlc/spaces/default/intents/*/aidlc-state.md`），checkbox 分布與 `Status` 如下（`grep -oE "^- \[([ xSR?-])\] \S+ — (EXECUTE|SKIP)"` 逐檔統計）：

| record | `[x]` | `[?]` | `[S]` | `[ ]` | `Status` | 落在對照表哪一列 |
|---|---|---|---|---|---|---|
| `260802-default` | — | — | — | — | 無 `## Stage Progress` | S-3 AC 5（跳過）✅ |
| `260802-last-login-column` | 21 | 0 | 11 | 0 | `Completed` | Done ✅ |
| `260806-a1-a3-ux` | 6 | **1** | 0 | 25 | `Running` | In review ✅ |
| `260806-drawio-templates` | 7 | 0 | 0 | 25 | `Completed` | Done ✅ |
| `260816-production-path-check` | 8 | 0 | 0 | 25 | `Completed` | Done ✅ |
| `260822-gh-projects-sync` | 9 | 0 | 0 | 23（另有 1 個 `[-]`） | `Running` | In progress ✅ |

今日 5 個可解析 record 全部落在表內，這點 draft 沒說錯。但表**不是全函式**：「`Status` ≠ `Completed`，且沒有任何 EXECUTE stage 是 `[-]`／`[R]`／`[?]`，但已有 `[x]`」這個狀態在表上**沒有對應列**——第一列的前提是「尚無任何 in-scope stage 動過」，已經不成立。這是 gate 核可後到下一個 stage 起跑之間的窗口，也是 `--single` 模式的常態。S-2 AC 1–3 各自只約束「有某訊號時輸出什麼」，AC 4 只禁兩個值，所以在這個狀態下機制輸出任何東西（或什麼都不輸出）都能通過全部四條 AC。對 P3——沒有交叉驗證管道的那個人——這正是「看板說謊」的入口。

**建議新增 S-2 AC 12（總函式性）**：**Given** 任一可解析的 record（即未被 S-3 AC 5 跳過者），**When** 映射判定執行，**Then** 恰好輸出一個 Status 值，且該值可回溯到對照表的某一列；不存在「無對應列」而落到預設值或空輸出的輸入。

（`getField`／`parseCheckboxes` 的語意見 `aidlc-lib.ts:2676`／`:2842`；後者的 regex `^- \[([ xSR?-])\] (\S+)\s*—\s*(.*)$` 要求 em-dash 分隔且 `default` 分支把未知標記一律當 `pending`，這也是為什麼「輸出恰好一個值」必須被明寫成 AC 而不是假設。）

DoD 側可補一句：本映射是純函式，適合以 property-based 測試斷言「對任意 checkbox 組合恰好輸出一個值」——`team.md ## Testing Posture` 記載本 repo 已有 8 個 `@given` 全落在純函式模組，落點慣例吻合。依 `user-stories:c3`，這句寫進 DoD，不寫進 AC。

---

### 4. S-4 AC 1 ＋ S-5 AC 3 的組合，重現 S-4 要消滅的失敗模式（Major）

- S-4 AC 1：`Parked` 非空 → **不發出任何 Status 寫入請求**（Status 停在最後已知值）。
- S-5 AC 3：自訂欄位無法自動建立時 → 開一則 issue，**且該次同步的 Status 寫入照常完成**（欄位失敗不連坐 Status）。

把兩條同時代入「欄位建立失敗 ＋ intent 被 park」：Status 因 AC 1 不寫（凍在 `In progress`），暫停事實因 AC 3 也不寫（欄位不存在）。看板上呈現的就是**一個持續顯示 `In progress` 的已暫停 intent**——逐字就是 S-4 註記自己寫的「不特判時被 park 的 intent 會被持續誤判為 `In progress`／`In review`，正是本 intent 要消滅的失敗模式在機制自己身上重演」。`phases/inception.md` 要求「Never carry forward unresolved contradictions between requirements; surface and resolve them explicitly」，這裡兩者都還沒做。

**建議**（surface ＋ resolve 一起做，形狀比照 `user-stories:c9`）：

- **S-4 AC 1 加適用前提**：「…**且 S-5 的自訂欄位可寫入時**，機制對該 item 不發出任何 Status 寫入請求」。
- **S-4 新增 AC 6**：**Given** 一個 `Parked` 非空、**且**自訂欄位不存在也無法建立的 intent，**When** 同步執行，**Then** 存在至少一個可讀取的位置（issue 受管區塊或通報 issue）明確載有該 intent 的暫停事實；不得同時既不寫 Status 也不寫任何暫停標示。
- 依賴表的 `S-5 → S-4` 理由改寫：不是「S-4 寫的是 S-5 建立的那個欄位」，而是「S-4 **繼承** S-5 AC 3 的失敗降級行為，兩者的降級路徑必須一起設計」。這讓它仍是技術依賴，但下游看得出真正的耦合點。

---

### 5. S-1 AC 5 與 S-6 AC 5 在身分未定之前不可證偽（Major）

兩條都是「某道防線關掉時應該會出事」型的斷言：

- S-1 AC 5：帶 `[aidlc-sync]` 的 commit 被推送 → 不執行任何看板寫入。
- S-6 AC 5：三道防線任一道關閉 → 存在可重現的迴圈情境。

但 GitHub 平台本身有一道**與這兩條無關的**迴圈防護：以 repo 預設 `GITHUB_TOKEN` 產生的 push／PR 事件**不會觸發新的 workflow run**。既有先例正是這樣跑的——`origin/danniel/feat/github-sync-phase1` 的 `.github/workflows/aidlc-sync-pull.yml` 用 `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` 做 `git push` 與 `gh pr create`。若同步身分是 `GITHUB_TOKEN`，`[aidlc-sync]` 這道防線根本不會被執行到，S-1 AC 5 恆真、S-6 AC 5 的「關閉此道即可重現迴圈」不成立；若身分是 GitHub App token（NFR-S1／OQ-1 傾向的方向），事件會照常觸發，兩條 AC 才有意義。**而身分正是 OQ-1，尚未定案。**

依 `user-stories:c4`（恆真的 AC 改寫而非刪除），建議把身分寫進 Given：

- **S-1 AC 5（改）**：**Given** 一個由**同步身分**（其產生的事件會觸發 workflow；若最終選用 `GITHUB_TOKEN`，本條改由平台行為承接並在 DoD 記明）推送、訊息含 `[aidlc-sync]` 的 commit，**When** 同步的觸發條件被評估，**Then** 不執行任何看板寫入。
- **S-6 AC 5** 同法加前提，並在 INVEST 的 Estimable 標 ⚠️ 指向 OQ-1。

---

### 6. A-5 與 A-6 的平台事實需要修正（Major）

**A-5（自動建立自訂欄位）**：requirements 寫「框架支援自動建立看板自訂欄位；**安全輸出清單中未見此型別**」——這句把「gh-aw 沒有這個 safe-output」誤述成「平台不支援」。ADR-0012 `:23` 是實測結論且說得很清楚：safe-outputs 只有 `create-issue`／`close-issue`／`add-comment`／`add-labels`／`push-to-pull-request-branch`，「沒有 Projects 操作」；`:24` 接著寫「必須提權讓 workflow 直接呼叫 `gh` CLI／GraphQL」。Projects v2 的欄位建立在 GraphQL 層有對應 mutation（`createProjectV2Field`）——**我未實測，這是待 PRE-1 確認的項目，此處只指出「未支援」的主體是 gh-aw 不是平台**。

後果：S-5 AC 3 的 Given（「該欄位不存在**且無法自動建立**」）在純 Actions 承載下，其可達觸發條件不是「框架不支援」，而是下列三者之一。不改寫的話，AC 3 是一條沒有可達前提的分支，會被實作成永遠走不到的死碼：

- **S-5 AC 3（改）Given**：憑證缺少組織層 Projects 寫入權、或同名欄位已存在但型別不同、或組織政策阻擋欄位建立——**任一情形下**，機制產生一則說明「需人工建立欄位」的 issue，且該次同步的 Status 寫入照常完成。

同時，這也讓 PRE-1 第 3 點（「順帶回答 A-5」）變成一個具體可測的動作，而不是「查文件」。

**A-6（反向 PR 的開關狀態可被正向同步讀取）**：開關狀態本身**不是問題**（`gh pr list --state open --search ...` 即可）。真正未驗證的是**逐 intent 歸屬**。先例 `origin/danniel/feat/github-sync-phase1` 的做法是 `python3 scripts/aidlc_sync_pull.py --all-intents` 一次處理全部 intent，然後開**一個** PR、分支名 `aidlc-sync/pull-$(date -u +%Y%m%d-%H%M%S)`。在這個形狀下，「某 intent 有未處理的反向紀錄」無法只從 PR 的 open/closed 狀態判定——一個開著的 PR 會讓**全部** intent 一起被暫停覆寫（over-suppression），而 FR-G3 要的是逐 intent。

**建議把 S-6 AC 3 改成含反例的版本**（目前的寫法通不過 over-suppression）：

- **S-6 AC 3（改）**：**Given** 一個開啟中的反向 PR，其變更含 intent X 的 record 路徑而**不含** intent Y 的，**When** 正向同步執行，**Then** 不對 X 的 item 送出 Status 寫入，**且照常**對 Y 的 item 寫入。[req:FR-G3]

A-6 的敘述同步改為「未驗證的是**逐 intent 歸屬的判定方式**（PR 內容 vs PR 狀態），不是 PR 狀態本身可否讀取」。

---

### 7. 「不得新增 repo 實作程式」與 S-10 AC 1 之間有一個未被提出的承載決策（Major）

`project.md ## Forbidden` 與 C-T7 把承載限定在 gh-aw 或 Actions workflow。加上第 1 點的結論（AC 11 事實上排除 gh-aw），映射解析（`getField` 語意 ＋ `parseCheckboxes` 語意 ＋ 對照表）與 Projects v2 GraphQL 呼叫全部得寫在 workflow YAML 的 `run:` 區塊裡。**但 S-10 AC 1 要求「對一組給定的 record 輸入斷言其輸出 Status」**——inline `run:` 區塊沒有任何測試層 import 得到。

實測 repo 現況：**沒有 `.github/actions/` 目錄**（不存在，非空目錄），也沒有任何 composite action／reusable workflow 先例；11 支 gh-aw workflow 的確定性工作全部寫在 `pre-agent-steps` 的 `run:` 裡。所以三條路各有代價，而**沒有一條是現成的**：

1. **Composite action**（`.github/actions/aidlc-sync-map/action.yml`）——邏輯仍在 `.github/` 下、非 `scripts/`，可被測試用 workflow 以 fixture 驅動；但這是本 repo 的新結構，且 `validate_repo_contract.py` 的 `REQUIRED_FILES` 不涵蓋它，改名／刪除無人擋。
2. **同一支 workflow 的 assertion job**：把 fixture 餵進同一段 `run:`，但這使 S-10 AC 1 的斷言與被測物耦合在同一個檔案的同一段字串上，改壞被測物與改壞斷言是同一個編輯動作。
3. **把邏輯複製一份到測試**：直接違反 `team.md ## Code Style`「單一真實來源」，且該條要求「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試」——這裡的兩份副本本身就是測試與被測物，鎖不起來。

這是**本站應該 surface 並指派的開放決策**，因為它決定 S-10 AC 1 存不存在得下去。建議加進「本站新增指派」表：

| US-OQ-3 | 決定性映射邏輯的承載形式（composite action／同 workflow 的 assertion job／其他），使 S-10 AC 1 的 dry-run 斷言有可驅動的對象 | **application-design** | 一個具體承載形式，並說明其在 `validate_repo_contract.py` 或 CI 上如何不被無聲刪除 |

---

### 8. OQ-7 沒有進依賴表，而它的三擇一會改變四則故事的實作形狀（Major）

問題檔 `:44` 記載 OQ-7「不阻擋本站，但會實質改變 construction 的工作量」，`stories.md` 只在文末以「仍待使用者裁決」帶過，**依賴表完全沒有它**。同時我實測發現 requirements 對它的事實描述與 repo 現況不符：

```
git merge-base --is-ancestor 6295c69 origin/ut   → 非 ancestor
git merge-base --is-ancestor 6295c69 origin/main → 非 ancestor
```

`scripts/aidlc_sync_{push,pull,buglist}.py` **只存在於 `origin/danniel/feat/github-sync-phase1`**，`git ls-files scripts/` 在 `ut`／`main`／本 HEAD 都只列出 `tcms_sync.py`／`tcms_validate.py`／`validate_env_contract.py`／`validate_repo_contract.py` 四支。requirements OQ-7 寫的「PR #508 **已合併**的三支腳本」與此不符（可能是未合併、或合併後被 revert）。**本站不回改上游**，但依賴表應如實記載：

- 依賴表新增一列：`OQ-7 → S-2、S-3、S-7、S-9`，性質 **技術依賴（外部裁決）**，說明「三擇一直接決定映射解析的承載形式：『既有豁免』下可用 Python 腳本，另兩者下必須落在 workflow YAML 或 composite action，兩種形狀的工作量與可測試性完全不同」。
- 同時把 S-2／S-3／S-7／S-9 的 INVEST **Estimable 由 ✅ 改為 ⚠️**，理由指向 OQ-7。目前四則標 Estimable ✅ 是不成立的：連承載語言都還沒定。

---

### 9. 依賴表逐列查核（含被點名的兩列）

| 表中的列 | 我的判定 | 依據 |
|---|---|---|
| `PRE-1 → S-1～S-9`（技術依賴） | **不完整**：應含 **S-10**。S-10 AC 2 是「對真實測試 item 實際寫入並讀回」，用的是同一組組織層 Projects 憑證 | S-10 AC 2 本文 |
| `S-1 → S-2/S-3/S-4/S-5/S-7`（技術依賴） | **不完整**：應含 **S-6**。S-6 AC 3 的逐 item 暫停需要綁定編號才知道停哪一則；AC 1 的反向 PR 也要知道回寫哪個 record | S-6 AC 1、AC 3 |
| `S-5 → S-4`（技術依賴） | **成立**，但理由要改（見第 4 點）：真正的耦合是 S-4 繼承 S-5 AC 3 的失敗降級路徑，不只是「欄位得先存在」 | — |
| `S-7 → S-9`（技術依賴） | **成立**，但**不完整**：S-9 AC 1 的分母要扣掉「有未處理反向紀錄者」，那是 S-6 的產物 → 應補 `S-6 → S-9`（技術依賴）。在 S-6 之前，AC 1 算得出一個**看起來合理但錯誤**的比率，比沒有更糟 | S-9 AC 1、S-6 AC 3 |
| `S-2 → S-3`（技術依賴） | **成立但性質被低估**：這同時是**同批次**約束，見第 10 點 | — |
| `S-6 → S-2`（避免重工） | **不同意，方向要拆**。S-2 先上、之後回頭加 FR-G3 分支 = 避免重工（可覆寫）；但**S-6 先上、S-2 尚無 FR-G3 分支 = 不可接受**：反向 PR 開著的整段期間，正向同步會把 P2 在看板上的改動輾回去——正是 S-6 存在的唯一理由。建議改寫為「**S-2 的 FR-G3 分支 → S-6：技術依賴（且同批次）**；S-2 其餘部分 → S-6：避免重工」 | S-6 故事本文的 benefit、FR-G3 |
| `S-10 → S-2`（避免重工） | **方向部分相反**。S-10 AC 1／AC 3 可 test-first（避免重工成立）；但 **AC 2 對 S-1／S-2 是技術依賴**（沒有寫入路徑就沒有端到端可跑），**AC 4 對 S-6 是技術依賴**。連帶 S-10 的 `Independent ✅（可先於被測對象存在）` **不成立** | S-10 AC 2、AC 4 |
| 缺列 | `S-7 → S-4`、`S-9 → S-4`：S-4 AC 5 要求「不出現在補平清單、出現在『已暫停』清單」——補平清單是 S-7 的產物，「已暫停」清單是 S-9 AC 2 的產物。兩者都是技術依賴，表中皆無 | S-4 AC 5、S-7、S-9 AC 2 |
| 缺列 | `S-2 → S-8`（技術依賴）：S-8 AC 1「一次寫入失敗」需要先有會失敗的寫入。連帶 **S-8 的 `Independent ✅` 不成立**（與 S-10 同型：沒有受測對象的驗證故事） | S-8 AC 1 |

---

### 10. 同批次檢查——draft 的「未發現同批次約束」不成立，至少三處（Critical）

draft 的理由是「本 intent 不變更任何既有端點的回應形狀」。但 `delivery-planning:c6` 的實質是「破壞性契約變更與其**消費端**」，而本 intent 的契約消費端不是 HTTP 端點，是**Project #16 這塊有活人在看的板子**（P2、P3）——每一個 Bolt 邊界都是一次真實部署，板子在那個中間態就是那個樣子給人看。把「每個故事邊界＝一次真實 staging 部署」代入後：

**G1（成立）— S-2 與 S-3 不得分批。** S-2 單獨上線 = 機制開始寫看板，但**沒有寫入前回讀比對**（S-3 AC 1）、**沒有分岔通報**（AC 4）、**沒有無法解析就跳過**（AC 5）。對 P3（`personas.md` 明記其「完全不接觸 repo 內容，看板是唯一資訊來源」）而言，這個中間態製造的正是 `intent-statement` 記載的既成缺陷（看板標 In review、issue 其實已關閉）。「寧可不寫、不可寫錯」是本 intent 的核心取捨，先上「會寫」再補「不寫錯」把取捨倒過來了。

**G2（成立）— S-6 與 S-2 的 FR-G3 分支不得分批。** 見第 9 點。

**G3（不同意 draft 對 S-1 的判定）— S-1 單獨上線並非「有效且不誤導」。**
draft 寫「S-1 單獨上線的中間態（看板出現卡片、停在 `Ready` 不動）是有效且不誤導的狀態」。實際上 S-1 AC 1 把 Status 設為 `Ready`，而 S-2 未上線 ⇒ 這張卡**永遠停在 `Ready`**，即使該 intent 已經跑到 `application-design`。對只看看板的 P3，一格寫著 `Ready` 而實際在跑，與寫著 `In review` 而實際已關閉是**同一類**的謊。這格不是「還沒開始更新」，它是「錯的」。

另有一條 draft 完全沒提的副作用：**S-1 AC 4 讓每一次觸發同步的 push 都在該分支上多產生一個 `[aidlc-sync]` commit**，而 `ci.yml` 的 push 觸發分支是 `main`／`ut`／`danniel/**`／`chore/**`（`.github/workflows/ci.yml:8-14`）。所以每個回寫 commit 都會多跑一輪四個 job（含 `docker-build` buildx 建兩個 image）。NFR-C1 只保證「既有 job 的**行為**與變更前相同」，不涵蓋**觸發量**，所以這條穿過了現有的全部需求。`deploy.yml` 幸好不受影響——它只在 `pull_request: types:[closed] branches:[ut]` 與 `workflow_dispatch` 觸發（`.github/workflows/deploy.yml:10-15`），純 push 不會部署。建議在 S-1 補一條 AC 或在全域 DoD 補一列：回寫 commit 不得使既有 CI 的觸發次數倍增（`paths-ignore` 或等價手段）。

**G4（不成立，但要寫成有條件的「尚未成立」而不是「無」）— S-5 單獨上線。**
今日不構成同批次約束：6 個 record 全部沒有設過 `Parked`（我逐檔 `grep "^- \*\*Parked\*\*"` 全落空，與 requirements Revision 1 的宣稱一致），所以 S-5 缺 S-4 的中間態碰不到 park 情境。但兩件事要寫清楚：(a) 這是**時間上的僥倖**，任何人第一次跑 `park` 就立刻變成 G1 級的問題，而沒有任何機制擋住那件事；(b) S-5 上線的那一刻，71 個既有未綁定 item 會立刻多出一個空欄位給 P2／P3 看見（A-7／OQ-8 尚未定案）——**OQ-8 的決定在 S-5 部署後就變成公開且不可撤回的**，這一點應該寫進 S-5 的註記，讓 delivery-planning 知道那個 gate 的實際期限。

**G5（新增，draft 未涵蓋）— S-6 的反向 PR 會啟動整組 PR gauntlet。**
S-6 AC 1 每次都開一個以 `ut` 為 base 的 PR。實測目前 `on: pull_request` 的 workflow 有：`ci.yml`（四個 job）＋ 6 支 gh-aw（`code-drift-alert`、`contract-guard`、`lint-fix`、`local-dev-drift`、`pr-reviewer`、`ui-regression`）。其中 `ui-regression` 是最貴的一支，該檔自己記載 PR #510 曾在單一 PR 上燒掉約 7 小時 runner 時間、零測試執行（`.github/workflows/ui-regression.md:17-21`）。反向同步若如先例每 6 小時一次、或如本 intent 每日一次，就是每天把只改同步狀態檔的 diff 送進一次完整 gauntlet（含 6 次 LLM 驅動的 agent 執行）。這既是成本，也是把 `project.md` 點名的「所有 LLM 路徑」盲區放大。建議 S-6 補一條 AC：

- **S-6 新增 AC 6**：**Given** 反向同步產生的 PR，其變更僅涉及同步專用檔案，**When** 既有 `on: pull_request` 的 workflow 評估觸發條件，**Then** 指定的高成本 workflow（至少 `ui-regression`）不對其執行。[req:NFR-C1]

---

### 11. 尺寸：S-2 的切線大致對，但 S-10 用了不同的尺（Major）

**S-2**：11 條 AC、Small ❌ 判斷正確。三條切線的評語：

- ①「映射判定（AC 1–7、11）」：**AC 11 要移出**（第 1 點），移出後 ① 剩 AC 1–7 ＋ 建議新增的 AC 12，全部可用純文字 fixture 驗，失敗模式同類（輸出錯的 Status／讀到錯的值），切線成立。
- ②「觸發與時效（AC 8–10）」：成立，但 **AC 8 應該搬走**（見下）。
- ③ draft 說「不建議把 AC 11 單獨切出」：**與 `units-generation:c6` 相反**，見第 1 點。

**AC 8（NFR-P1 的 5 分鐘）不能當每次執行的二元閘門。** GitHub-hosted runner 的排隊時間不受本 repo 控制，把「≤ 5 分鐘」寫成 per-run 斷言等於製造一個 flaky gate——而 `team.md` 已記載 `ui-regression` 的 `post-steps` 對 `.stats.unexpected` 是零容忍真閘門、只容忍 `stats.flaky`，把一個結構性 flaky 的斷言放進同一層會侵蝕那道閘門的可信度。`phases/operation.md` 要求 SLO 以百分比＋時間窗表達。建議：把 AC 8 改寫成量測型並移到 **S-9**（可觀測性那則）——「**Given** 連續 20 次事件觸發的同步，**When** 讀取其量測，**Then** 至少 19 次的 push→Status 更新間隔 ≤ 5 分鐘」——這樣它有明確的分母、不會單次紅燈，也給了 P4 一個真的能追的數字。

**S-10 用了不同的尺（不一致）。** S-10 的 4 條 AC 橫跨**三種完全不同的驗證機制**：AC 1／AC 3 是純文字 fixture 的 dry-run 斷言；AC 2 是對真實 Project item 的實寫讀回（需要憑證、需要網路、需要 S-1／S-2 存在）；AC 4 是反向路徑的判準（型式本身還由 OQ-2 待定）。依 `project.md ## Corrections` 的同一條判準（「驗證方式與失敗模式是否同類」），S-10 的內部異質度**高於** S-2 的 ①，卻標 `Small ✅` 且沒有任何切線註記。同一條規則在同一份文件裡套了兩把尺。建議 S-10 比照 S-2 補一段切線註記：①dry-run 映射斷言（AC 1、AC 3、＋建議新增的靜態 workflow 檢查 AC 5）②真實 item 端到端（AC 2）③反向路徑判準（AC 4，型式待 OQ-2）。

**S-9 的獨立性有疑慮（但我不主張合併）。** S-9 的四條 AC 全部是「S-7 的對帳輸出多出某個數值／某兩份清單」。單獨成為一個 Bolt 時可展示的成果是「報告多了一個比率與兩份清單」，勉強站得住；但 AC 1 的分母在 S-6 之前**算不對**（見第 9 點）。所以真正的處置不是合併，而是給 AC 1 加適用前提或補上 `S-6 → S-9`。

**其餘故事尺寸判定**：S-1（6 AC）、S-3（6 AC）、S-4（5→6 AC）、S-5（4 AC）、S-6（5→6 AC）、S-7（5 AC）、S-11（2 AC）在尺寸上沒有問題。S-11 的 AC 2（「既有結構與總覽敘述未被改動」）與全域 DoD 的 NFR-S3（`validate_repo_contract.py` 通過，其 `REQUIRED_TEXT` 已鎖住 README 的關鍵字）有重疊，不是缺陷，但可註明由 DoD 承接以免下游重複設計檢查。

## Positions

- AGREE: [Q3=A] 的粒度取捨與「S-2 Small ❌ 是已知並接受的代價」這個判斷本身正確——問題不在切不切，在切線的依據（AC 11 錯位、AC 8 誤入時效桶）與同一把尺沒套到 S-10。
- AGREE: S-3 承載「寧可不寫」、S-4 註記「機制存在但尚未發生不降低必要性」、以及 PRE-1 不立為故事（[Q5=A]）三處判斷成立，我逐項回 repo 查證後找不到推翻的依據。
- OBJECT: **「未發現同批次約束」不成立**——至少 S-2↔S-3、S-6↔S-2 的 FR-G3 分支兩處是真的不得分批，且 S-1 單獨上線並非「有效且不誤導」（Status 釘在 `Ready` 對 P3 就是一格謊，與 intent 要消滅的既成缺陷同類）。
- OBJECT: **S-2 AC 11 應予改寫**——它把 FR-B2 從「判定邏輯不由 LLM」擴大成「整次執行無 LLM 呼叫」，等於單方面刪掉 C-T7 明文允許的「gh-aw 的非 LLM 環節」選項（gh-aw 必含 agent step，見 `ui-regression.md:13/:40`），屬 inception 未記來源地新增需求。
- OBJECT: **S-2 AC 7 目前不是驗收標準**——`getField()` 沒有任何 CLI 可取值（`aidlc-utility.ts:5347-5434`、`aidlc-runtime.ts:1420`），且 ADR-0012 §6（`:103`）禁止依賴 `.claude/`，oracle 不存在；應改為 FR-J6 本文已寫出的四條行為 fixture。
- OBJECT: **S-8 與 S-10 的 `Independent ✅` 均不成立**——兩者都是沒有受測對象就湊不出信心假說的驗證型故事（S-8 AC 1 需要會失敗的寫入；S-10 AC 2／AC 4 需要 S-1／S-2／S-6）。
- OBJECT: **依賴表六處需修**——`S-6 → S-2` 不是純避免重工（反方向不可覆寫且同批次）、`S-10 → S-2` 方向部分相反、`PRE-1` 漏 S-10、`S-1` 漏 S-6、漏 `S-7 → S-4`／`S-9 → S-4`／`S-6 → S-9`／`S-2 → S-8`、以及 OQ-7 完全未進表。
- OBJECT: **S-4 AC 1 與 S-5 AC 3 的組合會重現 S-4 要消滅的失敗模式**（park ＋ 欄位建不出來 ⇒ 既不寫 Status 也不寫暫停標示，看板持續顯示 `In progress`），`phases/inception.md` 要求的 surface 與 resolve 兩者皆未做。
- OBJECT: **S-2／S-3／S-7／S-9 的 Estimable ✅ 不成立**——OQ-7 三擇一尚未裁決，連承載語言都未定；且 requirements 稱「PR #508 已合併」與 repo 現況不符（`scripts/aidlc_sync_*.py` 不在 `origin/ut`／`origin/main`，只在 `origin/danniel/feat/github-sync-phase1`）。
- OBJECT: **A-5 的敘述把「gh-aw 沒有這個 safe-output」誤述成「平台不支援」**（ADR-0012:23-24 已實測並指明須改走 `gh` CLI／GraphQL），使 S-5 AC 3 的觸發前提不可達；**A-6 誤指問題所在**——PR 開關狀態可讀，未驗證的是逐 intent 歸屬（先例 `--all-intents` 開單一 PR ⇒ FR-G3 會變成 over-suppression）。
