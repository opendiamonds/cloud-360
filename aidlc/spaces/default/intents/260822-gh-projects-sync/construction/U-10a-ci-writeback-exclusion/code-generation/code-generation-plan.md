# Code Generation Plan — U-10a `ci.yml` 的回寫排除

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-10a-ci-writeback-exclusion · kind: packaging
     Created: 2026-09-05T04:36:23Z（讀自 date -u） -->

## 交付物與落點

**對 `.github/workflows/ci.yml` 的修改**，不新增任何檔案、不新增依賴。複雜度 **XS**。

`ci.yml` 的檔名是 load-bearing（在 `validate_repo_contract.py` 的 `REQUIRED_FILES` 內，改名會讓 contract 紅燈）——只改內容，不動檔名。

## 本站查證推翻的上游前提（**最重要，先讀這一節**）

nfr-requirements 的 Q（code-generation 前補問）選了選項 A：「`concurrency` 加 `github.actor` ＋ 四個 job 加 `if:`」，其中第一半的**唯一依據**逐字為：

> 同步以 bot 身分推送，`github.actor` 與開發者不同 ⇒ 落在不同 group ⇒ `cancel-in-progress` 取消不到開發者的 run

**這個前提為假。** 本站實測（`gh api repos/opendiamonds/cloud-360/actions/workflows/ci.yml/runs`）：

| 誰 | `github.actor` | 依據 |
| --- | --- | --- |
| 開發者推 code（`push`／`pull_request` 皆同） | `opendiamonds` | 實測最近 8 次 `ci.yml` run，全部為 `opendiamonds` |
| 同步機制 | `opendiamonds` | ADR-0016 §1 定案身分為**擁有者帳號 token**；本站以該 token 手動觸發 workflow 實測 `actor=opendiamonds` |

**兩者相同**，`github.actor` 無法區分。

**為什麼上游會寫錯**：兩份已核可產出**各自都對，合起來才錯**——nfr-requirements 寫那道題時，憑證身分還是 GitHub App（App 有獨立的 `[bot]` 身分）；ADR-0016 後來把身分改成擁有者 token 且明文記載「稽核紀錄中機制身分與人工身分混同」，但**沒有回頭檢查哪些設計依賴了「身分可區分」**。

**另一個被混為一談的事實**：U-4 的 SEC-4 要求顯式設定同步身分（`aidlc-sync` / `aidlc-sync@users.noreply.github.com`），那是 **commit 的 author**；`github.actor` 由**推送用的憑證**決定，與 commit author 無關。兩者不是同一件事。

## 逐事件的可解性（本站推導，人工裁決的依據）

| 觸發事件 | 同步回寫會觸發？ | 事件酬載能判斷是同步 commit？ | AC 7(a) 不被取消 | AC 7(b) 不跑四個 job |
| --- | --- | --- | --- | --- |
| `push`（`main`／`ut`／`danniel/**`／`chore/**`） | 會 | **可以**——`github.event.head_commit.message` | **可解**：`paths-ignore` 讓 run 根本不建立 | 同左（run 不存在，四個 job 自然不跑） |
| `pull_request`（該分支已開 PR，synchronize） | 會 | **不行**——酬載無 commit 訊息，`actor` 又相同 | **結構性無解** | **可解**：前置 gate job checkout 後讀 commit 訊息 |

**(a) 在 `pull_request` 側無解的理由**：要分辨「這次 synchronize 是同步機器造成的還是人造成的」，所需資訊（commit 訊息或不同身分）**都不在事件酬載裡**，而 `concurrency` 是 workflow 層、在任何 job 執行之前就決定。

## 人工裁決（2026-09-05）

**選定：接受 `pull_request` 側會被取消。** 被否決的三案與其代價：

| 方案 | 為什麼不選 |
| --- | --- |
| PR 的 concurrency group 加 head SHA | 每次 synchronize 獨立分組 ⇒ (a) 成立，但**廢掉 PR 上的節流**：連推三次會同時跑三份 CI（12 個 job）。改變既有行為，與 NFR-C1「既有四道關卡不得因本變更而破壞」的精神相違 |
| 另鑄機器帳號 token | `github.actor` 就分得出來、原方案完全成立。但 ADR-0016 剛把身分從 GitHub App 改成擁有者 token（因 App 走不通），再引入第二個帳號等於推翻它；且需新帳號、新憑證、新權限管理 |
| 同步不推有 PR 的分支（改推自建分支開 PR） | 問題從根源消失、`ci.yml` 一字不改。但推翻 U-4／U-6 已核可的回寫設計，每次同步多一則 PR，範圍遠大於本單元 |

**選定方案的代價，如實記載**：開發者的 PR 測試**仍會被同步回寫取消一次**，需要重跑。且重疊機率不低——同步由 push／PR 事件觸發，發生在開發者剛推完 code 後幾十秒到幾分鐘內，而 CI 四個 job 要跑好幾分鐘。

## 對已核可上游的指派（不逕自修改）

> **本段的正式來源已移至 `code-summary.md` 的同名段落**（2026-09-05，reviewer iteration 2 Finding #2）。
>
> 原因：iteration 1 的修正把該清單由 2 處擴充為 **6 處**，但只改了 `code-summary.md`，
> 本檔沒跟著改——於是同一個 stage 目錄下兩份文件對「上游還欠什麼」給出不同答案（2 vs 6），
> 而 Bolt 1 gate 若開的是標題為「Plan」的這一份，看到的待辦只有 2 項。
>
> 這是 `project.md` 的 `units-generation:260822-ug-L1`（改動一個事實前，先問它在本站產出裡
> 有幾種表達形式，逐一開啟確認）在**姊妹檔層級**的再犯。
>
> **處置不是把表格複製過來**——那只會讓同一份清單有兩個副本，下次再漂移一次。改為
> 本檔不再自行維護該清單，一律以 `code-summary.md` 的「對已核可上游的指派」為單一來源。
> 摘要：待改寫的**事實有兩個**（A：既有 run 不被取消；B：`github.actor` 可區分身分），
> 散在**六個未歸檔落點**，確認人為 **Bolt 1 gate**。逐處的檔名、行號與定位方式見該檔。

## 計畫步驟

- [x] **Step 1 — `push` 側加 `paths-ignore`**：在 `on.push` 下加入 `paths-ignore: ["aidlc/spaces/*/intents/*/sync-state.json"]`。glob 必須**盡可能窄**（`security-requirements.md` SEC-1）：不得寫成 `aidlc/**`（會讓所有 AIDLC 產出繞過 CI）或 `**/*.json`（會讓 `package-lock.json`、`.github/aw/actions-lock.json` 這些**安全相關**的檔案繞過 CI）。`pull_request` 側**不加**——上游已證明它比對整個 PR diff、永不成立，加了是假保證。
  **追溯**：[US:S-1 AC 7]、SEC-1、`tech-stack-decisions.md` 的路徑集合表
- [x] **Step 2 — 新增前置 `gate` job**：`runs-on: ubuntu-latest`，`permissions: contents: read`，只做兩件事——`actions/checkout` 取 `fetch-depth: 2`，然後讀 HEAD commit 訊息判斷是否含 `[aidlc-sync]`，輸出 `is_sync`。**訊息來源分兩路**：`push` 事件優先用 `github.event.head_commit.message`（不需 checkout 即可得，較快也較不易出錯）；其餘事件（含 `pull_request`）用 `git log -1 --format=%B HEAD`。兩路都要，因為 `pull_request` 的 merge ref 的 HEAD 是合併結果、其 commit 訊息不是 PR 的 head commit——**須用 `github.event.pull_request.head.sha` 取那一顆**。
  **追溯**：[US:S-1 AC 7] 的第二半、`component-methods.md` §C-4 的 `[aidlc-sync]` 契約
- [x] **Step 3 — 四個既有 job 加 `needs` 與 `if:`**：`repo-contract`／`frontend`／`backend`／`docker-build` 各加 `needs: gate` 與 `if: needs.gate.outputs.is_sync != 'true'`。**四個 job 的內容、順序、失敗條件一字不動**（NFR-C1）。
  **追溯**：NFR-C1、[US:S-1 AC 7]
- [x] **Step 4 — `concurrency` 維持原樣**：**不加** `github.actor`（前提已證為假，加了是假保證且會讓下一個讀的人以為問題解決了）。在 `ci.yml` 就地加註解寫明：為什麼沒加、`pull_request` 側為什麼無解、AC 7 的哪一半因此待改寫。
  **追溯**：本站查證、人工裁決
- [x] **Step 5 — 測試**：本單元 `kind: packaging`，交付物是 YAML 設定，**沒有可單元測試的程式**。驗證方式為「建置與觸發設定（觀察觸發是否發生）」，故測試落在兩處：
  - **靜態檢查腳本** `.github/actions/aidlc-sync-ci-guard/check-ci-yml.py`（新增）：以 `yaml.safe_load` 解析 `ci.yml`，機械斷言六件事——(1) `on.push.paths-ignore` 恰含那一條 glob；(2) 該 glob **不**寬於 U-4 的 `paths` 白名單（SEC-1b 的二元可判約束）；(3) `on.pull_request` **沒有** `paths-ignore`；(4) 四個 job 皆有 `needs: gate` 與正確的 `if:`；(5) `concurrency.group` **不含** `github.actor`；(6) 四個 job 的 `steps` 與 `name` 與變更前逐字相同（NFR-C1，比對一份 golden 快照）。
  - **`act` 或真實觸發**：不採用。`act` 無法重現 `paths-ignore` 與 concurrency 的平台行為；真實觸發需要 push，屬 Bolt 1 的整合驗證範圍，**本單元的完成判準留到那時實測**（如實記載，不假裝已驗）。
- [x] **Step 6 — 突變驗證**：至少三條——(1) 把 glob 放寬成 `aidlc/**` → SEC-1 檢查紅；(2) 拿掉某個 job 的 `if:` → 檢查紅；(3) 在 `concurrency.group` 加回 `github.actor` → 檢查紅。每條改壞 → 紅 → 還原 → `diff -q` → 複跑綠。
- [x] **Step 7 — `code-summary.md`**（orchestrator 執筆）。2026-09-05T05:01:33Z 完成。

## Revision（2026-09-05T05:05Z，orchestrator）

**Step 5 的「機械斷言六件事」實際落地為七件**，多的是 `MARKER-1`（gate job grep 的標記須與 `record.sh` 的 `SYNC_MARKER` 同字串）。**Step 5 本文不回改**——它是已核可計畫的原文；本段為其承接處。

觸發來源是 Step 6 的突變驗證本身：新增的 M6（改 `record.sh` 的 `SYNC_MARKER`）在原版 guard 下**是綠的**，代表 U-4 改標記時 `ci.yml` 的硬編碼會悄悄失配，四道關卡照跑、無紅燈——本單元等於沒做。修法沿用 `SEC-1b` 已建立的「從 `record.sh` 推導而非自抄」形狀，M6／M8 雙向驗證。

Step 6 原訂「至少三條」突變，實際跑 **8 條**（M1–M8），逐條 改壞 → 紅 → 還原 → `diff -q` → 複跑綠。完整對照表與所有實測輸出見 `code-summary.md`。

## 需 Plan Approval 裁決的兩項介面判斷

1. **`gate` job 取 commit 訊息的方式**：`push` 事件用事件酬載（`github.event.head_commit.message`）；`pull_request` 事件用 `git log -1 --format=%B ${{ github.event.pull_request.head.sha }}`（**不是** HEAD——PR 的 merge ref 的 HEAD 是合併結果，訊息不是 PR head commit 的）。checkout 需 `fetch-depth: 2` 才拿得到 head commit。替代（一律 checkout 後讀 HEAD）在 PR 事件下會判錯。
2. **靜態檢查腳本的落點與是否進 CI**：放 `.github/actions/aidlc-sync-ci-guard/check-ci-yml.py`，**本輪只作為本單元的自我驗證，不接進 `ci.yml`**。理由：把它接進 `repo-contract` job 會讓 `ci.yml` 檢查自己，形成循環（改壞 `ci.yml` 的 `if:` 可能同時讓檢查跳過）；正確落點是 Bolt 1 的整合驗證或另一支獨立 workflow，屬本單元範圍外。**如實記載此缺口**。

## 已知的上游開放項（列入 summary）

- **上游六個落點待改寫**（事實 A 四處、事實 B 兩處），確認人 Bolt 1 gate。**逐處清單以 `code-summary.md` 的「對已核可上游的指派」為單一來源**，本檔不再自行維護（見上方該段的說明；原本這裡只寫 [US:S-1 AC 7] 與「nfr-requirements 那道題」兩項，是 iteration 2 Finding #2 抓到的姊妹檔漂移）。
- **本單元的完成判準無法在本 stage 實測**：需要真實推一個含 `[aidlc-sync]` 的 commit 到有 PR 的分支才觀察得到，屬 Bolt 1 整合驗證。
- **U-10a ＋ U-4 是真捆綁**（`unit-of-work-dependency.md`）：U-4 先上而本單元未上 ⇒ 每次回寫都取消開發者的 CI run。兩者必須同批次交付。
