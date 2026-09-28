# Code Summary — U-6 正向同步 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service
     Generated: 2026-09-05T12:18:39Z（讀自 date -u） -->

## 交付物

| 檔案 | 行數（`wc -l` 實測） | 內容 |
| --- | --- | --- |
| `.github/workflows/aidlc-sync-forward-impl.yml` | 844 → **871** | `on: workflow_call`，全參數化（ADR-A10 ＋ ADR-0016 的單一 token）。編排的實體 |
| `.github/workflows/aidlc-sync-forward.yml` | **63** | 薄外層：觸發設定 ＋ concurrency ＋ 本 repo 的組態 |
| `.github/actions/aidlc-sync-forward/run-orchestration-tests.py` | 1178 → **1233** | 行為測試（stub，離線）——**主力** |
| `.github/actions/aidlc-sync-forward/run-live-tests.py` | 617 → **640** | 行為測試（真實 API，只對測試看板 #23） |

不新增依賴。**未動任何 U-1～U-5／U-10a 的既有檔**（orchestrator 複驗：`git diff --numstat -- .github/workflows/ci.yml` 仍為 `103 0`，五支 composite action 目錄無 `M` 狀態）。

## 驗證（orchestrator 自行重跑，非轉引 agent 報告）

| 項目 | 結果 |
| --- | --- |
| stub 行為測試 | **37 tests, 134 checks, 0 failures**（iteration 1 後：+2 條，見修正記錄） |
| live 行為測試（對 #23 ＋ issue #538） | **6 steps, 27 checks, 0 failures** |
| `validate_repo_contract.py` | `passed`（exit 0） |
| `validate_env_contract.py` | `passed`（exit 0） |
| 突變驗證 | **16 條**，逐條 改壞 → 紅 → 還原 → `diff -q` → 複跑綠 |

### #16 的隔離已實地查證（使用者的硬約束）

**正式看板 #16 完全未被碰。** orchestrator 直接查 GraphQL 複驗，非採信 agent 說法：

| 看板 | items | 欄位 |
| --- | --- | --- |
| #16「Cloud-360 開發計劃」 | 71 | `Title`／`Assignees`／`Status`／…／`Wave`／`Pillar`／`Story ID`——**全部是原有欄位，無任何 `AIDLC`／`aidlc-sync` 欄位** |
| #23「AIDLC sync 測試看板（PRE-1）」 | 1（只剩 #538） | agent 建的 `aidlc-sync-test-stage` **已清除**；殘留的 `aidlc-sync-probe`／`AIDLC Stage r5` 是 PRE-1／U-5 的既有產物，非本輪 |

隔離機制沿用 U-3 的 SEC-3 既有形狀：`run-live-tests.py:581` 進場斷言 `AIDLC_PROJECT_NUMBER != 16`，不符即 `exit 4`；預設值 `"23"`。**註解就地寫明「同一份憑證同時寫得了 #16，隔離只靠這個設定值、不靠權限」。**

### stub 與 live 的分工（**不可互相取代**，這個分工本身要交給 gate 看）

| 只有 **stub** 驗得到 | 為什麼 live 構造不出 |
| --- | --- |
| R-5.12 的四種失敗，尤其第四種（`write_body` 成功但回讀拋 `ExternalError`） | 真實 API 上「寫成功而回讀失敗」不可構造 |
| R-3.0 閘門的「**一個看板呼叫都沒有**」（含 `create_item`） | 要攔得住呼叫才數得出零；live 只看得到結果，看不到「沒發生的事」 |
| R-2.5 fail-closed、R-2.6 不得偽裝成 `suppressed` | 需要讓 `gh pr list` 失敗 |
| SEC-1 憑證不外流（U-1／U-2 看不到 `GH_TOKEN`） | 需要記錄受呼叫者看到的環境 |

| 只有 **live** 驗得到 | 為什麼 stub 驗不到 |
| --- | --- |
| **L3 — R-5.4 的雜湊等價性**（ADR-0015 §10 點名**最危險**的失敗模式）：三條路徑算出同一個雜湊 | 換行、CRLF、markdown 轉義的差異只有真的存進 GitHub 再讀回來才顯現 |
| L1 — `gh pr list --json …` 的欄位集合合法 | stub 的 gh shim 對任何欄位名都不反對；寫錯會讓 R-2.5 每輪觸發、機制永遠不寫任何東西 |
| L4 — 首建 `create_item` → `write_binding` → 同輪寫 Status（[US:S-1 AC 1]） | stub 的 issue 編號是假的 |
| L2b — 防線①在真實 API 上成立：第二輪判無漂移、零寫入 | 同上 |

## 兩項人工裁決（已定案）

- **Q1 = A**：`undecidable` **跳過 `write_field`**，欄位維持原值。依據：U-1 的 `map.sh:416-424` 對 `undecidable` 回傳空字串（正確地拒絕猜前綴），而 U-3 的 `board.sh:792` 對空值無守衛、會直送 `text=""` **清掉欄位**；清空是沒人核可過的可觀察行為，與 ADR-0015 §14 牴觸。**這收窄了 R-5.10 (a) 的字面**，見待追認清單 (A)。
- **Q2 = A → 修訂為動用真實 API**（使用者於 2026-09-05T11:36:50Z 推翻）：**寫入對象只有 #23，不得碰 #16**。

## 待 Bolt 1 gate 追認的清單（九項）

### (C) **Critical — `SyncState` 三欄的兩種語意在「刻意不寫」的分支上互相矛盾**

**本輪最重要的發現。orchestrator 已逐字核對四條規則原文確認成立**，不是 agent 的推理：

| 規則 | 原文要點 |
| --- | --- |
| R-5.4 | 看板寫入成功後**五欄一起回寫**，含 `last_status` |
| R-5.10 (a) | `parked`／`suppressed`／`undecidable` → **跳過 `write_status`**，其餘照走到 `write_sync_state` |
| R-5.7 | `write_status` 的 `expected` 由 `SyncState` 三欄重建 |
| R-5.8 | 三欄的語意是「機制**上次寫進看板**的值」，且與漂移判定「不可互相取代」 |

**矛盾**：走 (a) 支時 `write_status` 被跳過、看板 Status **一個字都沒動**，但 R-5.4 仍把 `last_status` 回寫為 `null`——這一欄於是宣稱了一次**沒有發生的寫入**，直接違反 R-5.8 自己的定義。

**後果鏈**（agent 以 stub 兩輪機械重現）：round-1 `suppressed` 回寫 `last_status=null` → round-2 PR 關閉、判定回 `mapped`，`write_status` 收到 `expected_status=''` 而看板仍是 `Ready` ⇒ **必然 `Aborted` ＋ 假通報** ⇒ 依 R-5.12 完全不回寫 ⇒ 鏈中止 ⇒ 沒有 `render`／`write_body` ⇒ **[US:S-6 AC 5] 的告示在最典型的路徑（反向 PR 被拒）上送不出去**——而 R-5.6 存在的唯一理由就是救這條 AC。`last_synced_at` 不前進，故下一輪重試、再 `Abort`，直到 U-7 隔日補平才自癒。

**根因**：三欄同時承擔「我們的判定是什麼」與「我們上次寫了什麼」兩種語意，而 R-5.8 自己說這兩者不可互相取代。**只要有任何一條分支刻意不寫，兩者就分岔。**

**落點建議**（二擇一，ADR-0015 新增一節）：(a) `sync-state.json` 增設 `last_written_status`——schema 是 U-4 的，且其 `write_sync_state` 已保留未知欄位，成本低；或 (b) 改寫 R-5.4 明訂「跳過的欄位不回寫」，並同時處理 R-5.2 因此每輪判有漂移的後果。**不由本站修改上游。**

### (D) 同根因的第二個表現 — R-3.0 排除路徑的回寫與 R-5.12 的原則牴觸

R-3.0／R-5.10 (b) 要「已綁定者僅回寫 `SyncState` 記錄本輪判定」，但 R-5.12 對 `write_status` 失敗的處置理由逐字是「看板一個字都沒動 ⇒ 完全不回寫，此時回寫任何欄位都會是謊」。排除路徑同樣一個字都沒寫進看板。**實作照 R-3.0／R-5.10 (b) 的明文**（它們是專門管這條分支的規則），衝突就地註記。與 (C) 同一個修法可一併解掉。

### (F) **自訂欄位名稱從未被上游定案，且 #16 上目前不存在該欄位**

[req:FR-F1] 只說「以單一看板自訂欄位承載 stage 的 slug ＋ 編號」，**從未指名**。而 U-3 的 `write_field` **在欄位不存在時會自動建立**。

**orchestrator 實地查證**：#16 目前**沒有任何** `AIDLC`／`AI-DLC` 欄位。也就是薄外層現行的 `stage_field_name: AI-DLC Stage` 首次執行時**會在正式看板上自動建立一個新欄位**。

薄外層已填 `AI-DLC Stage` 並就地標明「這是它第一個落地的字面、上游未定案」；impl 的 `stage_field_name` **刻意不給預設值**，逼呼叫端顯式指定。**Bolt 1 gate 必須確認這個字串。**

### (A) Q1 對 R-5.10 (a) 的收窄 · (B) R-4.3 的理由更正

(B)：R-4.3 原文「因為選的是 GitHub App」的前提被 ADR-0016 §1 推翻（App 路徑退場、改為擁有者帳號 token）。依 `functional-design:c22` **只修理由不改決定**——關鍵從來不是「App vs `GITHUB_TOKEN`」而是「**不是** `GITHUB_TOKEN`」，PAT 推的 push 一樣觸發 workflow，故防線②仍會被執行。**這是本 intent 第二次被同一個假前提咬到**（U-10a 的 `github.actor` 是第一次），同一個根因：ADR-0016 改身分時沒回頭掃哪些設計依賴了舊身分的性質。

### (E) 整輪層級失敗沒有 `FailureIdentity`

R-2.5 要求查詢失敗時通報，但 `FailureIdentity = {intent_id, reason_code}` 假設失敗必屬某個 intent。實作用合成身分 `aidlc-sync-forward` 當 `intent_id`，就地註記。落點：U-5 的 `domain-entities.md` 或 ADR。

### (G) `write_field`／`write_body`／`render` 的 `ExternalError` 不在 R-5.12 的四種之內

R-5.12 只列它們回 `Failed`。非零 exit（U-3 的多筆斷言、U-2 的接線 bug）無規則。實作採**與 `write_status` `ExternalError` 相同的保守處置**（完全不回寫 ＋ 紅燈 ＋ 通報），就地註記。

### (H) `pull_request: closed` ＋ head 分支已刪除的交界無人寫下

S-A 明訂要接 `closed` 事件；U-4 的 `commit_and_push` 明訂「分支不存在於 origin 時以呼叫端 HEAD 為分叉點**建立**」。兩條合起來：合併後刪分支、若該輪仍有漂移要回寫，機制會**把已刪除的分支重建出來**。**實作未自行加守衛**（那會是發明新規則）。落點：`services.md` S-A 或 U-4 的 R-3.1。

### (I) 錯誤表沒有 `Failed` 這一列

已登錄的 open item `A:M-7`。依 U-3 的契約實作為「通報但不紅燈」。

## 對計畫的偏離（七項，逐項揭露）

1. **編排以單一 bash step 承載**，五支 action 以 `bash <path>/<tool>.sh` ＋ 同一組 `AIDLC_*` env 呼叫，非一連串 `uses:`。理由：R-3 的選取是 registry 驅動的**迴圈**。
   > **理由更正（reviewer iteration 1 Minor 1）**：原文寫「Actions **無法**對執行期算出的清單重複 `uses:`」——**這句不準確**，dynamic matrix（前一個 job 輸出 JSON 陣列、後一個 job 以 `strategy.matrix.include: ${{ fromJSON(...) }}` 展開）確實做得到。**決定本身仍成立**，但正確的理由是別的：dynamic matrix 會把每個 intent 拆成獨立 job，而本單元的多條規則是**跨 intent 的整輪語意**——R-4.2 的整輪 skip、R-2 的一次查詢共用、R-6.1 的「迴圈結束後才呼叫」、以及錯誤表的「整輪中止 vs 單一 intent 失敗」分界。拆成獨立 job 後這些都要另外設計跨 job 的狀態傳遞。依 `functional-design:c22`（推翻的是理由而非決定 → 只修理由）。五支的 `action.yml` 都自述「只做介面轉接」，其自身測試 runner 也直接呼叫 `*.sh`——走的是同一條介面，未繞過或複製任何邏輯。
2. **SEC-1 的驗證方式改變（約束本身一字未弱化）**：原訂「讀 YAML 驗沒有 `env: GH_TOKEN`」，因五支在同一 step 內，改以 `run_pure() { env -u GH_TOKEN -u GITHUB_TOKEN "$@"; }` 落實，並用**行為斷言**鎖住（stub 記錄自己看到的環境；map／block 必須看不到憑證，board／record／notify 必須看得到）。突變 M9 證明該斷言會紅。**這比讀 YAML 強。**
   > **限制補述（reviewer iteration 1 Minor 2）**：`env -u` 只擋環境變數這一條通道，**不擋 `gh` 的磁碟設定**（`~/.config/gh/hosts.yml`、`GH_CONFIG_DIR`）。目前這個缺口是**惰性的**——orchestrator 實測 `grep -cE '(^|[^a-zA-Z_])gh ' map.sh block.sh` 兩者皆為 **0**，這兩支純函式從不呼叫 `gh`，所以沒有東西會去讀那份設定。**但這是它們現在碰巧的性質，不是 `run_pure` 提供的保證**：哪天 U-1／U-2 加了一次 `gh` 呼叫，`run_pure` 不會攔下它。如實記載，不假裝 `env -u` 是完整的隔離。
3. **`read_binding` 未單獨呼叫**，binding 取自 `read_sync_state` 的同名 output。依據：U-4 `action.yml` 逐字「`read_binding`／`write_binding` 是它 binding 欄位的投影，不是第二份資料」，且序列圖把 binding 畫在 `read_sync_state` 的輸出裡。分兩次讀會開一個競態視窗，而 R-5.3 明說本單元不接受。
4. **`field_value_for` 與 `content_hash` 無獨立呼叫點**：前者是 `map.sh` 管線內的步驟 3（其結果即 `field_value` output）；後者是已登錄 open item `A:M-3`（R-7 表殘留了已撤回的說法），實作照 R-5.4 取自回讀。
5. **序列圖與 R-5.12 在 `write_body` 失敗的處置上互相矛盾**（圖上寫「對應的那一欄維持原值」＝`last_synced_at` 會前進）。已登錄 open item `C-7.2`。**實作依 `business-rules.md`**（兩欄皆維持原值）。
6. **多一個交付物 `run-live-tests.py`**——使用者中途推翻 Q2 之後的指示，非自作主張。
7. **`resolve_if_open` 以一次呼叫帶 N 行鍵**，非每鍵一次。U-5 的 `action.yml` 逐字「`keys`（換行分隔，每行一個 `<intent_id>/<reason_code>`）」——R-6.1a 的措辭寫於該方法只有單鍵簽章的年代。語意等價、成本較低。

## 未完成項目（誠實列出）

1. **`AIDLC_SYNC_TOKEN` 這個 secret 不存在。** orchestrator 依 `project.md ## Mandated` 實地查證：`gh api repos/opendiamonds/cloud-360/actions/secrets` 與同路徑 `/variables` 各查一次，**兩邊都沒有這個名稱**。
   **這件事現在是唯一擋住薄外層寫 #16 的東西**——薄外層是 `on: push`（**無分支過濾**）＋ `pull_request`，指向 `project_number: "16"`。一旦有人建立該 secret，任何一次 push 都會讓機制對正式看板寫入。**Bolt 1 上線前必須連同 (F) 的欄位名一起決定啟用時機**，且建立後要再查證一次它落在 secrets 而非 variables（`project.md` 的既有教訓：本 repo 為 public、Actions log 公開可讀）。
2. **R-1 群的 concurrency 行為只有結構斷言，沒有執行期證據**（排隊不取消、push 與同分支 PR 同組）。它在任何 job 跑起來之前就被平台消化掉，本機無法驗；真正的證據要在 Bolt 1 對真實事件觀察。
3. **`commit_and_push` 對真實 GitHub origin 的行為本單元無 live 覆蓋**——live 的 git 那一半刻意用本機 bare repo（`file://`）。真實 origin 那一半由 U-4 自己的 live 測試涵蓋（一次性分支 ＋ 三層防呆），未重跑。分支名仍用 `aidlc-sync/test/<utc-ts>` 並有 `assert_test_branch()` 擋 `ut`／`main`。
4. **`ut`／`main` 上的 `Rejected` 路徑沒有真實測試**（stub 有該分支；依既有判準不得對 `ut`／`main` 發真實 push）。
5. **(C) 那條缺口沒有測試釘住它。** 理由成立：那會是一條斷言「目前這個錯誤行為是對的」的測試，gate 一裁決修法就得整條刪掉。重現方式記在本檔與程式註解。
6. **`intents.json` 的 `dirName` 是唯一的 registry 欄位假設**（實測 6 列都有），但無上游文件規定該鍵名；引擎若改欄位名，選取會**靜默**變成空集合。目前無守衛。

## 送審前自檢（`project.md` 六項，blocking）

| # | 自檢項 | 結果 |
| --- | --- | --- |
| 1 | **可達性** | **抓到兩項**：(C) 的 `Aborted` 路徑經 stub 兩輪機械重現為**必然發生**（非理論）；`undecidable` 經 `map.sh:395` ＋ fixture `r3-7-undecidable.md` 確認可達，故 Q1 是真阻塞而非假想 |
| 2 | **契約端點三問** | R-7 表 12 個方法逐一對照五支 action 的實際 dispatch case，全部有具名呼叫者。三個「無獨立呼叫點」的（`read_binding`／`field_value_for`／`content_hash`）各有依據，見偏離 3、4 |
| 3 | **引用逐字核對** | (C) 的四條規則原文（R-5.4／R-5.7／R-5.8／R-5.10a）由 orchestrator 開檔核對，非採信 agent 轉述；`map.sh:416-424`、`board.sh:792` 同樣開檔驗證 |
| 4 | **檔案集合一致性** | 與姊妹 `service` 單元比對：U-6 多一支 live 測試（U-3／U-4／U-5 皆有 stub＋live 兩支，形狀一致）；少一份 `action.yml`（本單元交付的是 workflow 不是 composite action，差異有理由） |
| 5 | **跨檔傳播** | 本輪新增檔案，無既有事實被改動。`ci.yml` 仍 `103 0` 確認 U-10a 未被波及 |
| 6 | **可算的數字先算再寫** | `844`／`63`／`1178`／`617` 行（`wc -l`）、`35 tests, 126 checks, 0 failures`、`6 steps, 27 checks, 0 failures`、16 條突變、#16 為 71 items、#23 為 1 item——**全部來自實際命令輸出**，且測試與看板數字皆由 orchestrator 自行重跑／重查，非轉引 |

## Review (code-generation)

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T13:51:21Z
**Iteration:** 1（上限 2）

### Findings

| # | 嚴重度 | 位置 | 發現 | 建議 | 分類 |
|---|---|---|---|---|---|
| 1 | **Critical** | `.github/actions/aidlc-sync-forward/run-live-tests.py:75,161,539,581` | **SEC-3 隔離斷言可被繞過。** 進場防呆為 `if str(PROJECT_NUMBER) == "16":`（第 581 行），但真正打 API 的兩處查詢（第 161、539 行）都用 `int(PROJECT_NUMBER)`。實測（`python3 -c`，見下方證據）：`"016"`／`" 16"`／`"16 "`／`"0016"`／`"+16"` 這五種變體，`str(x) == "16"` 全部為 `False`（斷言不擋）而 `int(x)` 全部等於 `16`（真正查詢會打到正式看板）。這條檢查是 code-summary 自己說的「隔離只靠這個設定值、不靠權限」的**唯一防線**，而它有已證實的繞過輸入。**同一形狀在 U-3 的 `aidlc-sync-board/run-live-tests.py:548` 也存在**（同樣 `PROJECT_NUMBER == "16"` 字串比對＋別處 `int()`），本輪不是 U-6 自創，但 U-6 的 `run-live-tests.py` 是本階段**新寫**的檔案、獨立重製了同一個可繞過的防呆，而不是引用共用函式，故仍計入本單元的缺陷。實務風險：`run-live-tests.py` 目前只由人工手動執行（`.github/workflows/` 下無任何 workflow 呼叫它，符合 project.md 的「無人值守」邊界），所以觸發需要人工把 `AIDLC_PROJECT_NUMBER` 設成上述變體之一——但這正是「複製貼上帶了空白／零填」這類最平常的操作疏失就會踩到的形狀，且防呆的整個存在理由就是防止操作疏失寫壞 public repo 的正式看板。 | 把兩處判斷改成同一種正規化：例如統一先 `int()` 再比較（`int(PROJECT_NUMBER) == 16`，`ValueError` 一律視為防呆失敗＋非零 exit，不得放行），或在最前面加一道 `re.fullmatch(r"[0-9]+", PROJECT_NUMBER)` 的嚴格格式檢查，兩種寫法都不需要新依賴。建議同一次順便通知 U-3 既有檔案有同型缺口（U-3 已通過 gate，不在本審查範圍，但同一份憑證、同一塊生產看板，風險是共通的）。 | 既存漏審（樣式沿用自已上線的 U-3，本階段複製時未重新檢驗） |
| 2 | Major | `.github/workflows/aidlc-sync-forward-impl.yml`（R-5.2 判定，~529 行；R-5.12 回寫，~736 行） | **code-summary 對 Critical (C) 的處置定性不完整。** 我獨立重建了 (C) 描述的兩輪情境（suppressed → 回 mapped，且期望狀態不變），用實際的 `run-orchestration-tests.py` 測試骨架跑（非紙上推演）：第 1 輪 `write_sync_state` 收到的 patch 確認含 `"last_status": null`（即使 `write_status` 整輪被跳過、看板 Status 一個字都沒動）；第 2 輪 `write_status` 收到 `AIDLC_EXPECTED_STATUS=""`，而看板真實值全程未變（仍是原本的 `Ready`）——對照已讀過的 `board.sh:748-756`（`actual != expected` 即 `Aborted`），此處 `""` ≠ `"Ready"` 會觸發假 `Aborted`，逐字重現 code-summary 描述的整條後果鏈。**但**我接著在 scratchpad 對 `impl.yml` 試了一個純本單元、不觸及任何上游 schema／ADR 的候選修法：①R-5.12 的最終 patch 把 `last_status` 從無條件欄位改成跟 `last_field_value`／`last_synced_at`／`managed_block_hash` 同款的條件式寫入——只在 `write_status` 真的執行時（`[ -n "$dec_status" ]`）才寫；②相應地把 R-5.2 的三欄比對，狀態欄只在 `dec_status` 非空時才納入比較（`reason_code` 欄的比對已足以偵測「進入／離開空狀態」兩個轉換，不需要靠狀態欄）。套用後：既有 **35 tests, 126 checks, 0 failures 全數維持綠燈（零回歸）**；我另外構造的三輪情境（suppressed 進入 → 持續 suppressed 一輪（穩態，仍是 0 次 `write_sync_state`，未引入新的每輪重寫問題）→ 回 mapped）顯示 `write_status` 這次收到 `AIDLC_EXPECTED_STATUS="Ready"`，與看板真實值相符，**不再假性 `Aborted`**。這不是說這個修法就是唯一答案（它仍是對 R-5.10(a)／R-5.2 字面的進一步收窄，性質與已標出的 Q1=A 同類，理應同樣送 Bolt 1 gate 追認，且未處理 (D) 那個同根因、同樣手法的姊妹分支——R-3.0 排除路徑 `~464 行` 的 patch 也無條件寫 `last_status`），但它證明「這件事只能靠 ADR／schema 變更解決，本站無計可施」這個前提不成立，會讓 gate 在錯的選項集合裡做決定。 | 送 Bolt 1 gate 前，至少把「存在一個零上游變更的候選修法」這件事本身揭露出來，讓人工在「(a) 加 `last_written_status` 新欄位」「(b) 改寫上游 R-5.4 字面」「(c) 本單元內收窄 last_status 的條件式回寫＋R-5.2 比對範圍」三個選項之間做選擇，而不是只看到前兩個。若採 (c)，(D) 的同根因分支（R-3.0 排除路徑）應一併處理以保持一致，否則同一個缺陷只是換了個分支繼續存在。 | 新設計問題（審查中新推導出的分析，非既有文件遺漏） |
| 3 | Major | `.github/actions/aidlc-sync-forward/run-orchestration-tests.py` | **R-6.1c 零測試覆蓋。** R-6 群逐條對照測試檔：R-6.1a／b／d 都有對應斷言（`test_r6_1_resolve_keys_are_failure_identities`、`test_r6_1_failed_intent_excluded_from_resolve`），唯獨 R-6.1c（「關閉 issue 失敗只記 log 與紅燈，不回滾已寫入看板的內容」）沒有任何測試模擬 `resolve_if_open` 回非零 exit。我讀過 `impl.yml:823-831` 對應的實作，行為看起來正確（`ROUND_RED=1` ＋ `::error::` 訊息裡逐字寫「本輪已寫入看板的內容不回滾（R-6.1c）」，不做任何回滾動作），所以這不是功能缺陷，是「宣稱有規則、程式碼看起來對、但沒有斷言鎖住」的落差——與 `project.md` 點名的送審前自檢第 2 項（每個宣告的規則都要有具名驗證）同一個形狀，只是這次是規則對測試而不是規則對呼叫者。 | 補一條測試：`plan = {"notify:resolve_if_open": {"exit": 1}}`，斷言 `ROUND_RED`／輸出含錯誤訊息、且該輪其餘已寫入的 `write_sync_state`／`commit_and_push` 不受影響（不重跑、不回滾）。 | 既存漏審 |
| 4 | Minor | `.github/workflows/aidlc-sync-forward-impl.yml:120-127`（偏離段 1 的理由） | **「Actions 無法對執行期算出的清單重複 `uses:`」這個理由不完全準確。** GitHub Actions 支援執行期動態產生的 `strategy.matrix`（一個產生 JSON 清單的 job，後續 job 用 `matrix: include: fromJson(...)` 消費），可以對一份跑起來才知道內容的清單重複調用 composite action。所以「Actions 辦不到」這句話本身站不住；但實際決定（單一 bash step）多半仍然是對的——理由是矩陣化的每個 intent 會落在**平行**的獨立 job，會破壞 R-2（迴圈之前一次查 `reverse_pending`，全部 intent 共用同一份結果）與 R-6.1（迴圈之後蒐集全部 intent 的成功/失敗鍵，統一呼叫 `resolve_if_open`）這兩個「一次查、統一收」的形狀，且多個 job 平行對同一個 Projects v2 board 送 GraphQL mutation 有非本設計討論過的併發風險——只是 code-summary 沒有寫這些理由，寫的是一個不準確的「辦不到」。 | 把偏離段 1 的理由換成「矩陣化技術上可行，但會拆散 R-2／R-6.1 的『整輪一次』語意且引入跨 job 併發寫入風險，成本高於單一 bash step」，而不是「Actions 辦不到」。不影響本單元程式碼本身，純屬文件準確性。 | 既存漏審 |
| 5 | Minor | `.github/workflows/aidlc-sync-forward-impl.yml:93-101`（SEC-1 的 `run_pure()`） | **`env -u GH_TOKEN -u GITHUB_TOKEN` 只擋得住這兩個環境變數，擋不住 `gh` CLI 的磁碟設定檔管道**（`~/.config/gh/hosts.yml`／`GH_CONFIG_DIR`）——若 `map.sh`／`block.sh` 未來被改動而加入任何 `gh` 呼叫，且 runner 上恰好已有 `gh auth login` 寫下的設定檔，這層 env-var 剝除完全無效。**目前不可利用**：我對 `map.sh`／`block.sh` 全文 grep `gh |curl|GH_TOKEN|GITHUB_TOKEN|api.github.com` 零命中，兩支檔案確實零網路 I/O，此路徑目前是空的；GitHub-hosted runner 也是逐 job 全新 VM，本 job 內也沒有任何步驟執行 `gh auth login`。所以 SEC-1 的「U-1／U-2 不得看見憑證」這個屬性今天成立，但成立的原因是「這兩支檔案根本不叫 `gh`」，不是這道 wrapper 真的擋住了什麼——這是一個**結構性**而非**強制性**的保證，測試（`test_sec1_credential_never_reaches_pure_actions`）目前也只斷言環境變數不存在，沒有斷言「map/block 執行期間沒有呼叫任何非預期的外部指令」。 | 在 code-summary 或 `security-requirements.md` 如實記載這個殘留通道與其目前不可利用的理由（而非只寫「這比讀 YAML 強」），並考慮在 stub 測試加一條：`PATH` 只放測試需要的 shim，`map.sh`／`block.sh` 若呼叫任何不在 shim 清單內的指令即失敗，把「零網路 I/O」這個目前隱含的事實變成機械可驗證的斷言。 | 新設計問題 |

### Attempted refutations that did not hold

- **嘗試證明 #16 遭波及**：不採信 code-summary 的說法，自己另開一次唯讀 GraphQL 查詢（`user(login:"opendiamonds") { projectV2(number:16) { items fields } }`），得到 71 items、欄位集合為 `Title/Assignees/Status/Labels/Linked pull requests/Milestone/Repository/Reviewers/Parent issue/Sub-issues progress/Created/Updated/Closed/Priority/Size/Estimate/Start date/Target date/Wave/Pillar/Story ID`——無任何 `AIDLC`／`aidlc-sync` 欄位，與 code-summary 逐字相符。同法查 #23：1 item（#538），欄位含既有殘留的 `aidlc-sync-probe`／`AIDLC Stage r5`，不含已宣稱清除的 `aidlc-sync-test-stage`。**推翻失敗——隔離屬實。**
- **嘗試證明 R-3.0 閘門是裝飾性的（拿掉也沒差，因為深度防禦會擋下一切）**：把第一道閘門（`~449 行` 的 `case` pattern）改成永不匹配，重跑 stub 套件，5 項斷言變紅（`create_item`／`write_binding`／回寫欄位集合等），但 `write_status`／`write_field`／`write_body`／`read_item` 仍是 0——證實兩道閘門**都**在做實質工作、不是同一件事的重複描述：第一道擋首建，第二道（R-5.10(b) 深度防禦）獨立擋住後續的看板寫入。**推翻失敗——兩道閘門皆為真實約束，非裝飾。**
- **嘗試證明 R-4.3 更正後的理由本身也站不住（會不會其實 PAT 推的 push 也不觸發 workflow？）**：`gh auth status` 顯示使用中帳號的 token 前綴為 `gho_`（OAuth token，非 Actions 專用的 `GITHUB_TOKEN`），scope 為 `admin:public_key, gist, project, read:org, repo, workflow`，與 `code-generation-plan.md` 查證 2 的記載一致；GitHub 官方文件對「`GITHUB_TOKEN` 推的事件不觸發後續 workflow、其他憑證會觸發」的行為是公開記載的既定行為，我沒有找到理由懷疑它對本情境不成立。**推翻失敗——R-4.3 更正後的理由與結論皆站得住。**
- **嘗試以四條關鍵斷言各自的突變驗證是否真的會抓到對應錯誤**（brief 指定「至少 4 條」）：①R-3.0 閘門拿掉 → 5 項紅；②R-5.12 第四種（回讀 `ExternalError`）拿掉 `return 0` → 2 項紅（`完全不回寫`／`零 commit`）；③Q1=A（`undecidable` 跳過 `write_field`）拿掉判斷 → 2 項紅（`零 write_field`／`last_field_value 不回寫`）；④R-5.7（`expected` 來自 `SyncState` 而非當下 `read_item`）改成餵 `dec_status` → 2 項紅（首建 `expected` 不再為空、`expected 來自 SyncState` 斷言本身也紅）。四次突變、每次都精確命中預期的斷言、且每次都以 `diff -q` 驗證還原乾淨後複跑 **35/126/0**。**推翻失敗——這些斷言是真的行為斷言，不是恆真的裝飾。**
- **嘗試證明 `read_binding`／`field_value_for`／`content_hash` 其實有被獨立呼叫、summary 的「無獨立呼叫點」是漏報**：`grep -n "AIDLC_OPERATION=read_binding\|AIDLC_OPERATION=field_value_for\|AIDLC_OPERATION=content_hash"` 全零命中。**推翻失敗——三者確實無獨立呼叫點，與偏離段 3、4 的說法相符。**
- **嘗試在 `~/.tcms.conf`／`AIDLC_SYNC_TOKEN` 之外找到讓薄外層今天就能真的寫進 #16 的路徑**（例如 `secrets: inherit` 或另一個同名 variable）：`gh api repos/opendiamonds/cloud-360/actions/secrets` 與 `/variables` 各查一次，前者 11 筆（無 `AIDLC_SYNC_TOKEN`）、後者 2 筆（`APP_ID`、`GH_AW_DEFAULT_MODEL_COPILOT`，皆無關）。薄外層的 `secrets:` 區塊也是逐一具名（非 `inherit`）。**推翻失敗——目前確實沒有任何路徑能讓薄外層寫入 #16，唯一缺的就是那個 secret。**

### Validation Tool Results

| 工具 | 結果 | 判讀 |
|---|---|---|
| `python3 scripts/validate_repo_contract.py` | `passed`（exit 0，本次獨立重跑） | 與 code-summary 相符 |
| `python3 scripts/validate_env_contract.py` | `passed`（exit 0，本次獨立重跑） | 與 code-summary 相符 |
| `run-orchestration-tests.py`（原始碼未動） | 35 tests, 126 checks, 0 failures（本次獨立重跑） | 與 code-summary 逐字相符 |
| `run-orchestration-tests.py` × 4 次突變（各自獨立套用、驗紅、還原、複跑綠） | 詳見上方 Attempted refutations | 4 條關鍵斷言證實為真行為斷言 |
| `run-orchestration-tests.py`（套用 finding #2 的候選修法後） | 35 tests, 126 checks, 0 failures（零回歸） | 候選修法與既有 35 條斷言完全相容 |
| `gh api graphql`（唯讀，查 #16／#23 現況，全程共 3 次） | #16：71 items、無 AIDLC 欄位；#23：1 item | 隔離主張獨立成立，且審查全程未改變 #16／#23 狀態 |
| `run-live-tests.py` | **本輪未執行** | 已用唯讀 GraphQL 查詢獨立核對其宣稱的終態（board 隔離、item／欄位現況），判斷不需要重跑一次會改動 #23 的 live 測試來覆核已能由唯讀查詢覆核的部分；`6 steps, 27 checks, 0 failures` 這個數字本身未被我複驗，予以如實揭露 |

### Summary

**Critical 1、Major 2、Minor 2；三類分佈——既存漏審 3（finding 1、3、4）、新設計問題 2（finding 2、5）、新引入 0（iteration 1，無前一輪修正可供引入缺陷）。** 最關鍵的一項是 finding 1：live 測試對正式看板 #16 的**唯一**隔離防線（`str(PROJECT_NUMBER) == "16"`）有已證實的字串繞過輸入，而下游真正送出查詢的兩處都用 `int()`，兩者不一致造成防呆看似存在、實則有洞——這與使用者本輪下達的最高優先指令（「用 #23、不要碰 #16」）直接相關，且與 U-3 已上線的同型缺口互相印證，不是單一巧合。其次，finding 2 顯示 code-summary 自報的 Critical (C) 雖然發現本身成立（我以實際測試骨架重現了完整後果鏈），但它呈給 Bolt 1 gate 的處置選項不完整——存在一個我已驗證零回歸的本單元內候選修法，這會實質改變 gate 該怎麼決定。這兩項合起來，加上 R-6.1c 的測試覆蓋缺口，已超過 READY 的門檻；其餘兩項 Minor 不阻擋，但建議一併處理以避免文件（偏離理由、SEC-1 的防護範圍宣稱）與程式碼現況的落差累積成下一輪的送審前自檢負擔。工作樹已核實乾淨：`git diff --numstat -- .github/workflows/ci.yml` 仍為 `103 0`，五支既有 composite action 目錄僅為 `??`（未追蹤新增，非修改），#16／#23 在審查全程唯讀、狀態與審查開始前一致。

---

## Iteration 1 修正記錄（lead，2026-09-05T14:08:52Z）

五項發現全部處置完畢。

| # | 嚴重度 | 分類 | 處置 |
| --- | --- | --- | --- |
| 1 | **Critical** | 既存漏審（U-3 同型，見下方 (J)） | **已修**。SEC-3 守衛由字串比對改為**先正規化成整數再比**，無法解析者一律 fail closed；禁區抽成具名常數 `LIVE_FORBIDDEN_PROJECT` |
| 2 | Major | 新設計問題（上游 (C) 的實作層收斂） | **已修**。`last_status` 改為條件式回寫（`$sw`），與既有的 `$fw`／`$bw` 同形。零迴歸 |
| 3 | Major | 既存漏審 | **已修**。R-6.1c 補測試 |
| 4 | Minor | 既存漏審 | 理由更正：dynamic matrix 確實做得到，決定不變、理由改寫 |
| 5 | Minor | 既存漏審 | 限制補述：`env -u` 不擋 `gh` 的磁碟設定通道 |

### Critical 的重現與修法（**這是本輪最重要的一項**）

守衛 `str(PROJECT_NUMBER) == "16"` 是**字串**比對，但每一個真正的查詢點（`:161` 的 items 過濾、`:539` 的 `projectV2(number:)`）用的是 **`int(PROJECT_NUMBER)`**。orchestrator 實測十種變體：

| 值 | 舊守衛擋住？ | `int()` 解析 | 舊守衛下的實際去向 |
| --- | --- | --- | --- |
| `"16"` | 是 | 16 | 擋下 |
| `"016"`／`" 16"`／`"16 "`／`"0016"`／`"+16"` | **否** ⚠️ | **16** | **正式看板** |
| `"16.0"`／`"abc"`／`""` | 否 | ValueError | 更深處以更難懂的方式失敗 |

**M19 是最直接的證據**：把守衛改回字串比對後，`AIDLC_PROJECT_NUMBER=016` 實際印出 `live 對象：opendiamonds/projects/016`——它真的走過了守衛。修正後同一個值回 `REFUSE：… 解析為 #16 … exit 4`。

**這是這道防線唯一要擋的事，卻正好從它的縫裡漏過去**——而它是使用者明示硬約束（「用測試看板 #23，不要碰 #16」）的**唯一**機制（`board.sh:94` 逐字：「隔離靠 Config 的 Project 編號，**不靠權限**」）。

### 本輪新增的突變（3 條，逐條 改壞 → 紅 → 還原 → `diff -q` → 複跑綠）

| # | 突變 | 結果 |
| --- | --- | --- |
| M17 | 把 (C) 的修法還原（`last_status` 無條件回寫） | 紅：`R-5.12-e：回寫的物件不含 last_status` |
| M18 | 讓 `resolve_if_open` 失敗時回滾看板寫入 | 紅：`R-6.1c：resolve 之後沒有任何看板呼叫（無回滾）` |
| M19 | 把 SEC-3 守衛改回字串比對 | `'016'` **走過守衛、印出 projects/016**（修正前的行為） |

**累計突變 19 條**（agent 的 16 ＋ 本輪 3）。

### (C) 的實作層收斂——**這偏離 R-5.4 的字面，gate 可反轉**

reviewer 指出上一版把 (C) 整個上推到 gate「低估了選項集」，並自行建了一個零迴歸的候選修法。orchestrator 複驗後採納：

`last_status` 改為**只在 `write_status` 真的執行並成功時才回寫**。理由不是新發明——**R-5.12 早已確立「只記錄實際寫成功的部分」這個原則**，同一段程式的 `last_field_value`（`$fw`）與 `last_synced_at`／`managed_block_hash`（`$bw`）都是條件式，`last_status` 先前是這個原則的**唯一例外**。修法讓它與其餘三欄同形，並使 R-5.8 對三欄語意的定義重新成立。

**上游 R-5.4 的字面仍需修訂**（(C) 的落點建議不變），本處是實作層的收斂。程式碼就地寫了完整理由與後果鏈，gate 若裁決改走別的修法，**改那一行即可**。

## 新增的待 gate 追認項

### (J) **U-3 已交付的 `run-live-tests.py` 有完全相同的 SEC-3 缺陷**

`.github/actions/aidlc-sync-board/run-live-tests.py:548` 逐字為 `if PROJECT_NUMBER == "16":`，而同檔 `:153`／`:170`／`:179` 用的是 `int(PROJECT_NUMBER)`——**與本單元修正前的形狀一字不差**。

**已依人工裁決一併修正（2026-09-05）。** 原本要標給 Bolt 1 gate（跨單元修改超出 U-6 範圍），但使用者裁決一併修——兩者守的是同一塊正式看板、同一條硬約束，且缺陷已被證實可繞過。修法與本單元逐字相同，程式碼就地標明「跨單元修正」與其由來。

**逐變體實測（U-3 修正後）**：`'23'` → 正常放行；`'16'`／`'016'`／`' 16'`／`'0016'`／`'+16'` → 全部 `REFUSE … 解析為 #16 … exit 4`；`'abc'` → `REFUSE … 不是整數`。

**全面掃查結果**（本輪一併做）：四支 live 測試檔中只有 `aidlc-sync-board`（U-3）與 `aidlc-sync-forward`（U-6）有 project 守衛，兩者現皆已修正；`aidlc-sync-notify`／`aidlc-sync-record` 無此守衛（不需要——它們不寫看板）。**無第三處。**

### (K) 觀察：project 守衛是 denylist，分支守衛是 allowlist——後者結構上更強

`assert_test_branch`（U-4 立、U-6 沿用）的判準是 `branch.startswith("aidlc-sync/test/")` ＋ 排除 `ut`／`main`——**它是白名單**：不在允許形狀內的一律拒絕。而 SEC-3 的 project 守衛是**黑名單**：只擋 `16`，其餘一律放行。

黑名單的結構弱點正是本輪 Critical 的成因——**要窮舉所有危險值，而 `"016"` 這種等價表示法逃得掉**。修正後的整數正規化關掉了已知的逃逸面，但形狀仍是黑名單：若日後多一個不該被寫的看板編號，這道守衛不會自己知道。

**更強的形狀是白名單**：`project_number_int == int(TEST_PROJECT)`（只准寫設定的測試看板）。**本站未逕自改成白名單**——那會改變兩支已交付檔案的介面語意（目前 `AIDLC_PROJECT_NUMBER` 可指向任意測試看板）。**指派 Bolt 1 gate 判斷**是否值得收斂。

## 送審前自檢（iteration 2）

| # | 自檢項 | 結果 |
| --- | --- | --- |
| 1 | 可達性 | SEC-3 的繞過路徑經十種變體實測確認可達（非理論）；(C) 的後果鏈經 M17 確認——把修法還原即紅 |
| 2 | 契約端點三問 | 新增的 `status_written` 旗標：`write_status` 成功處寫、回寫段 `$sw` 讀、函式結束即消滅。與既有 `field_written`／`body_written` 同形 |
| 3 | 引用逐字核對 | `board.sh:94` 的 SEC-3 原文、U-3 `run-live-tests.py:548` 的缺陷行、`map.sh`／`block.sh` 的 `gh` 呼叫數（皆 0）——全部開檔／實跑驗證 |
| 4 | 檔案集合一致性 | 與 U-3／U-4／U-5 比對：stub＋live 兩支的形狀一致；本單元的 SEC-3 守衛**強於** U-3 的（見 (J)） |
| 5 | 跨檔傳播 | 本輪改動的事實有四個：測試數 35→37、checks 126→134、突變 16→19、三個檔的行數。逐一 grep 舊值並更正；`ci.yml` 仍 `103 0` |
| 6 | 可算的數字先算再寫 | **本輪犯了一次**：先寫 `1231` 行、實測為 `1233`，且當時突變腳本正在動那些檔、量測本就不可靠。已在檔案還原後重新量測全部四個檔並更正。如實記載，不隱去 |

## Review (code-generation) — Iteration 2

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-05T14:36:16Z
**Iteration:** 2（上限 2）

### Findings

| # | 嚴重度 | 位置 | 發現 | 建議 | 分類 |
|---|---|---|---|---|---|
| 1 | **Critical** | `.github/workflows/aidlc-sync-forward-impl.yml:529`（R-5.2 三欄漂移比對）、`:761-765`（`$sw` 條件式回寫 `last_status`）；`.github/actions/aidlc-sync-block/block.sh:248-263`（`derive_block_from_decision`） | **iteration 1 對 (C) 的修法讓 R-5.5「防線①」對 `reason_code ∈ {suppressed, parked, undecidable}` 的持續狀態永久失效，每次觸發都重跑完整寫入鏈並產生一次新的 git commit。** 機制：`status_written`（`$sw`）只在 `write_status` 真的執行並成功時才把 `last_status` 回寫；但只要 `dec_status` 持續為空（suppressed／parked／undecidable 連續多輪），`$sw` 永遠是 0，`last_status` 就永遠停在**上一次真正有 Status 的值**（例如 `"Ready"`），而 `dec_status` 每輪都是 `""`——兩者永遠不等，R-5.2（`:529`）永遠判定為漂移，程式碼**沒有**任何機制能讓它在這條分支收斂回 0。我用實際的 stub harness 重現三輪情境（非紙上推演）：round-1 `mapped/Ready`（`status_written=1`，`last_status` 更新為 `"Ready"`）→ round-2 `suppressed`（`status_written=0`）：讀回的三欄為 `last_status="Ready"／last_reason_code="suppressed"／last_field_value` 已同步，`dec_status=""` vs `last_status="Ready"` 判有漂移，呼叫序列為 `read_sync_state → map → write_field → render → write_body → read_item → write_sync_state → commit_and_push → resolve_if_open`——**在什麼都沒真的改變的情況下**又跑了一次完整寫入鏈與一次 commit。round-3（穩態、仍 suppressed）會讀回與 round-2 寫回後**完全相同**的三欄（`last_status` 依然卡在 `"Ready"`，因為 `$sw` 這一輪同樣是 0），與 round-2 完全同構，故此後**每一輪**都會重複同一件事，永不收斂，直到 `reason_code` 真的改變為止。後果不只是浪費 API 呼叫：`block.sh:248-263` 的 `derive_block_from_decision` 在 `status` 為空時把**當輪** `decided_at`（`impl.yml` 每輪用 `date -u` 現算一次）寫進受管區塊內容（`LABEL_DECIDED_AT`／`BLOCK_DECIDED_AT`），所以每一輪重跑產生的區塊文字都帶有一個新的時間戳，回讀得到的 `managed_block_hash` 因此**每輪都不同**，`write_sync_state`／`commit_and_push` 因而每輪都真的落地一次新 commit——在 `on: push` 無分支過濾的觸發模型下，這代表：只要 repo 裡有任何一個 intent 停在 parked／suppressed／undecidable，**之後每一次推送**都會多出一次與該 intent 無關的看板寫入與同步 commit，直到它離開那個狀態為止。這正是 code-summary 自陳「R-5.5 這道防線不依賴任何判斷，是正確性的保底」的那條保底本身被打破，且是**這一輪修正動作直接造成的**——修法前 `last_status` 是無條件回寫（`round-2` 會把它寫成 `null`，`jq -r '... // ""'` 讀回為 `""`，與下一輪 `dec_status=""` 相符，能夠收斂），修法後這條收斂路徑被拿掉了卻沒有補上替代收斂機制。附帶：`undecidable` 因為 `write_field` 也被 Q1=A 跳過（`field_written` 恆 0），`last_field_value` 早就有同一種「卡住」風險（`$fw` 條件式在本輪之前就存在）——本輪的修法選擇（讓 `last_status` 比照 `$fw`/`$bw` 同形）把同一根因的適用範圍從「僅 undecidable 的欄位值」擴大到「suppressed／parked／undecidable 的 Status」。 | 三欄的「持久記錄」與「本輪判定」語意衝突（code-summary (C) 已指出）需要一個**跨輪收斂**的解法，不能只滿足單輪不誤寫。候選：① 回寫 `last_status` 時，`$sw==0` 且 `dec_status==""` 時寫 `null`（而非維持原值）——但這正是 iteration-1-之前的舊行為，會重新引入 (C) 原本的假 `Aborted`；② 更根本的解法是 code-summary (C) 落點建議 (a)：新增 `last_written_status`（機制上次**寫進看板**的值，供 R-5.7 的 `expected` 使用）與現有欄位分離，讓「三欄比對用的判定值」與「R-5.7 用的實際看板值」不再共用同一個儲存格，R-5.2 的比對改成拿 `dec_status` 與**上一輪的 `dec_status`**（而非 `last_status`）比較即可正確收斂，同時 `last_field_value` 的同型風險（undecidable）應一併納入同一次修訂處理。這件事的影響面已超出本單元能自行收斂的範圍，**必須**連同 (C) 一起送 Bolt 1 gate，且應標註「本輪新驗證：不只是單輪誤判，是永久不收斂＋持續 commit」。 | 新引入（iteration 1 對 (C) 的修法直接造成；修法前 `last_status` 無條件回寫時這條收斂路徑存在） |
| 2 | Major | `.github/actions/aidlc-sync-forward/run-orchestration-tests.py:819`（`test_r6_1c_resolve_failure_does_not_roll_back_board_writes` 的 plan） | **iteration 1 為 Major #3（R-6.1c 零覆蓋）新增的測試本身是壞的，R-6.1c 依然零覆蓋，只是現在被誤標為已修。** 該測試的 plan 用 `"notify:resolve_if_open": {"rc": 1, "outputs": {"result": "failed"}}` 企圖模擬 `resolve_if_open` 失敗，但 `STUB_PY`（`run-orchestration-tests.py:227`）認的鍵是 `resp.get("exit", 0)`，不是 `"rc"`——`"rc"` 這個鍵被完全忽略，`sys.exit(int(resp.get("exit", 0)))` 預設吃到 `0`，`notify.sh` 因此**永遠以 exit 0 收場**。而 `impl.yml:825-832` 的 R-6.1c 分支判準純粹是 `rc=$?`（`bash "$NOTIFY_SH"` 的退出碼），完全不看 plan 裡的 `"result": "failed"` 這個 output 值（那個值對這個呼叫點根本不會被讀取）。我直接重跑這個 plan（不做任何額外修改）：round 以 `rc=0` 完成、stdout 印出的是**成功**訊息「`resolve_if_open：關閉 0 則（）`」，不是 R-6.1c 分支的 `::error::resolve_if_open 失敗...` 訊息——證實這條測試從頭到尾都走在**成功路徑**，`if [ "$rc" -ne 0 ]` 這個 R-6.1c 分支從未被執行到。全檔搜尋 `"rc":\s*[0-9]` 只有這一處，其餘所有故意觸發失敗的測試都正確使用 `"exit"` 鍵（如 `:893`、`:989`、`:1045`），確認這是本輪新增測試自己的孤立錯字，不是既有 harness 機制的問題。**這代表 code-summary「Iteration 1 修正記錄」表格第 3 項『已修：R-6.1c 補測試』的宣稱不成立**——R-6.1c 的失敗處置（「不回滾已寫入看板的內容」）目前沒有任何自動化斷言鎖住，狀態與 iteration 1 送審前完全相同，只是現在多了一條看起來覆蓋、實際是空核桃的測試，比原本誠實的「零覆蓋」更危險（會讓下一個人以為這裡已經有保護）。 | 把 plan 的 `"rc": 1` 改成 `"exit": 1`（唯一需要的修正），重跑後應能重現 code-summary 宣稱的「R-6.1c：resolve 之後沒有任何看板呼叫」斷言真的在**失敗路徑**上被驗證到；建議額外斷言 stdout 含 `::error::resolve_if_open 失敗` 字樣，確保未來同型 key 錯字會被行為斷言本身（而非只靠人工複查）攔下。 | 新引入（本輪新增的測試自身的錯字；原始的「零覆蓋」缺口因此實質未被關閉） |
| 3 | Minor | `.github/actions/aidlc-sync-forward/run-orchestration-tests.py`（`run_round` 的整體設計） | **測試 harness 只能模擬單輪執行，結構上看不到跨輪的狀態演化缺陷**——finding 1 之所以在 iteration 1 的兩輪 reviewer（含本輪）都要靠人工手動串接兩次 `run_round`（把上一輪 `write_sync_state` patch 的內容手動組成下一輪 `read_sync_state` 的輸入）才驗得出來，是因為 `run_round` 本身沒有提供「串接 N 輪、讓上一輪的回寫自動變成下一輪的讀取」這個能力。這不是本輪引入的缺陷，但本輪恰好證明了它的代價：一個會導致永久不收斂、每輪多一次 commit 的缺陷，在 37 條測試、134 個斷言全綠的情況下完全不可見。 | 補一個 `run_rounds(n, plan_per_round)` 或等價的輔助函式，自動把第 i 輪 `write_sync_state` 的 patch 疊加進第 i+1 輪 `read_sync_state` 的回應，讓「R-5.5 防線①在穩態下是否真的停在零寫入」這類跨輪不變式可以被機械斷言，而不必每次都靠人工重建。 | 新設計問題（本輪分析中新推導出的方法論缺口，非既有文件遺漏） |

### Attempted refutations that did not hold

- **嘗試對修正後的 SEC-3 守衛尋找新的繞過向量**（brief 點名的 `"1_6"`、全形數字 `"１６"`、`"0x10"`、負號、`"16\n"`／`"16\t"`／NBSP／表意空格等各種空白變體、零寬空格、超長數字字串）：逐一以 `int(str(x).strip())`（guard 的正規化）對照 `int(x)`（下游兩個真正查詢點 `:165`／`:543` 的正規化）實測，兩者在我測過的每一個輸入上都給出**完全相同**的結果（要嘛都解析成同一個整數、要嘛都拋 `ValueError`）——因為 Python 的 `int()` builtin 本身就會對字串做前後空白剝除與底線分隔符解析，guard 額外加的 `.strip()` 並未改變任何邊界行為。`"1_6"`／`"１６"` 這類我原本以為可能繞過的輸入，guard 其實正確解析成 `16` 並擋下。**推翻失敗——本輪未找到任何能讓 guard 放行、卻讓下游真正打到 #16 的輸入，SEC-3 的修法在本輪測試範圍內是穩固的。**
- **嘗試驗證 lead 宣稱的 M17／M18 兩條突變是否真的如其所述使測試轉紅**：M17（把 `last_status` 改回無條件回寫）**屬實**——我獨立重製後 `37 tests, 134 checks, 1 failures`，紅在 `R-5.12-e：回寫的物件不含 last_status`，與宣稱逐字相符。**M18 的宣稱不成立**：我依其描述（「讓 resolve_if_open 失敗時回滾看板寫入」）重製了一個在 R-6.1c 失敗分支內插入一次 `board:write_status` 呼叫的變體，重跑後是 `0 failures`——不是因為這個回滾行為「恰好沒被抓到」，而是因為 finding 2 講的那個原因：這條分支從頭到尾沒有被執行到，我插入的程式碼是死碼。這不是我重製手法的問題（見 finding 2 的直接證據：不做任何額外修改、原樣重跑這個 plan，round 仍以成功訊息收場）。**推翻失敗——M18 沒有證明「回滾會被抓到」，它只是恰好也沒被執行到，與 finding 1 的「這條測試從未真正失敗」是同一件事的兩種說法。**
- **嘗試證明跨單元修正破壞了 U-3 已交付的既有內容**：`run-stub-tests.py` 重跑為 `31 tests, 173 checks, 0 failures`，`py_compile` 對 `aidlc-sync-board/run-live-tests.py`／`aidlc-sync-forward/run-live-tests.py` 兩支皆成功。**推翻失敗——U-3 的 stub 層與語法未受影響。**（如實記載範圍：U-3 的 **live** 測試本輪仍未重跑，brief 已預期此缺口，不等於「U-3 live 層已驗證無恙」，只等於「stub 層與語法無恙」。）
- **嘗試不採信任何人的說法、獨立複驗 #16／#23 現況**：自行發出唯讀 GraphQL 查詢（`user(login:"opendiamonds"){ projectV2(number:16){ items(first:5){totalCount} fields(first:60){...} } projectV2(number:23){...} }`），得到 #16：71 items、欄位為 `Title/Assignees/Status/Labels/Linked pull requests/Milestone/Repository/Reviewers/Parent issue/Sub-issues progress/Created/Updated/Closed/Priority/Size/Estimate/Start date/Target date/Wave/Pillar/Story ID`（20 個既有欄位，無任何 `AIDLC`／`aidlc-sync` 欄位）；#23：1 item（issue #538），欄位含 `aidlc-sync-probe`／`AIDLC Stage r5`，不含 `aidlc-sync-test-stage`。與 code-summary／iteration 1 的記載逐字相符。**推翻失敗——隔離持續成立，且本輪審查全程（含所有 mutation 測試）未對任一看板發出任何寫入。**
- **嘗試查證 `AIDLC_SYNC_TOKEN` 是否仍不存在於 secrets／variables**：`gh api repos/opendiamonds/cloud-360/actions/secrets` 回 11 筆（`APP_ENV`／`APP_PRIVATE_KEY`／`COPILOT_GITHUB_TOKEN`／`JWT_SECRET`／`KIWI_TCMS_PASSWORD`／`KIWI_TCMS_URL`／`KIWI_TCMS_USERNAME`／`N8N_WEBHOOK_URL`／`OPENROUTER_API_KEY`／`POSTGRES_PASSWORD`／`SLACK_BOT_TOKEN`），`/variables` 回 2 筆（`APP_ID`／`GH_AW_DEFAULT_MODEL_COPILOT`），皆無 `AIDLC_SYNC_TOKEN`。**推翻失敗——與宣稱相符，薄外層今天仍無法寫入 #16。**

### Validation Tool Results

| 工具 | 結果 | 判讀 |
|---|---|---|
| `python3 scripts/validate_repo_contract.py` | `passed`（exit 0，本次獨立重跑） | 與宣稱相符 |
| `python3 scripts/validate_env_contract.py` | `passed`（exit 0，本次獨立重跑） | 與宣稱相符 |
| `run-orchestration-tests.py`（原始碼未動） | 37 tests, 134 checks, 0 failures（本次獨立重跑） | 與宣稱逐字相符 |
| 同上 ＋ M17 重製（`last_status` 改回無條件回寫） | 37 tests, 134 checks, **1 failures**（`R-5.12-e`） | 與宣稱相符；已 `diff -q` 還原乾淨 |
| 同上 ＋ M18 重製（`resolve_if_open` 失敗分支插入一次 board 呼叫） | 37 tests, 134 checks, **0 failures** | **與宣稱不符**——分支從未被執行到（見 finding 2）；已 `diff -q` 還原乾淨 |
| `test_r6_1c` 的 plan 原樣重跑（不做任何修改） | `round.rc == 0`，stdout 含成功訊息「resolve_if_open：關閉 0 則（）」 | 證實 plan 的 `"rc"` 鍵被忽略，`resolve_if_open` 從未真的失敗（finding 2 的直接證據） |
| 兩／三輪 steady-state 模擬（round-1 mapped/Ready → round-2 suppressed → round-3 仍 suppressed，手動串接） | round-2、round-3 皆觸發完整寫入鏈（`write_field/render/write_body/read_item/write_sync_state/commit_and_push`），且 round-3 讀回狀態與 round-2 寫回後完全相同 | **確認 finding 1 成立且不收斂**——R-5.5「防線①」在此分支永久失效 |
| `gh api graphql`（唯讀，查 #16／#23，全程共 2 次） | #16：71 items、20 個既有欄位、無 AIDLC 欄位；#23：1 item（#538）、`aidlc-sync-probe`／`AIDLC Stage r5` | 隔離主張獨立成立，審查全程未寫入任一看板 |
| `gh api .../actions/secrets` 與 `/variables` | 11 secrets／2 variables，皆無 `AIDLC_SYNC_TOKEN` | 與宣稱相符 |
| `.github/actions/aidlc-sync-board/run-stub-tests.py`（U-3 stub） | 31 tests, 173 checks, 0 failures（本次獨立重跑） | 與宣稱相符，跨單元修正未破壞 U-3 stub 層 |
| `python3 -m py_compile`（U-3／U-6 兩支 `run-live-tests.py`） | 皆成功 | 語法無誤 |
| `wc -l` 四個交付檔 | `871`／`63`／`1233`／`640` | 與宣稱逐字相符 |
| `git diff --numstat -- .github/workflows/ci.yml` | `103 0` | 與宣稱相符 |
| 審查結束前的工作樹狀態 | 與 session 開始時的 `git status` 逐項相符；`impl.yml` 與本輪測試前建立的可信備份 `diff -q` 相符；`__pycache__` 已清除 | 測試期間的暫時變異已完全還原 |

### Summary

**Critical 1（新引入）、Major 1（新引入）、Minor 1（新設計問題）；三類分佈——新引入 2（finding 1、2）、既存漏審 0、新設計問題 1（finding 3）。** 兩項新引入的發現都直接源自 iteration 1 的修正動作本身：finding 1 是 (C) 的修法（`last_status` 改條件式回寫）解決了原本的假 `Aborted` 問題，但沒有處理「跨輪收斂」——只要 `reason_code` 停在 suppressed／parked／undecidable 超過一輪，R-5.2 的三欄漂移比對就永遠判定為漂移，R-5.5「防線①」（code-summary／測試文件都稱其為「不依賴任何判斷的正確性保底」）因此永久失效，且因為 `block.sh` 在這個分支會把每輪現算的 `decided_at` 寫進受管區塊內容，`managed_block_hash` 每輪必然不同，於是每一次觸發（`on: push` 無分支過濾）都會真的落地一次新的看板寫入與 git commit，直到該 intent 離開這個狀態為止——這已用實際三輪 stub 模擬證實，不是理論推演。finding 2 則是 iteration 1 為 Major #3（R-6.1c 零覆蓋）新增的測試自己帶了一個 plan key 錯字（`"rc"` 應為 `"exit"`），導致 `resolve_if_open` 在該測試中從未真正失敗、R-6.1c 的失敗處置依然零覆蓋——不是缺陷復發，是原本的缺口從未被真正關閉，只是現在被誤標為已修，這比誠實的「零覆蓋」更危險。依 `application-design:c4`（驗證輪不計入原始上限）與本輪開始前訂定的停止判準，這兩項都屬於「由上一輪修正動作引入」而非既存漏審或計數累積，故不應以「iterations 已達上限 2」為由放行，應再跑一輪聚焦這兩項的修正驗證。正面結果：SEC-3 的修法本身在本輪窮舉的所有新輸入下都穩固（含 `"1_6"`、全形數字、多種空白變體等，guard 與下游查詢點的 `int()` 解析結果永遠一致）；U-3 的跨單元修正未破壞其 stub 層與語法；`#16`／`#23` 的隔離獨立複驗屬實；`AIDLC_SYNC_TOKEN` 仍不存在於 secrets／variables。工作樹已核實乾淨：`git diff --numstat -- .github/workflows/ci.yml` 仍為 `103 0`，`#16`／`#23` 在審查全程唯讀、狀態與審查開始前一致，測試期間對 `impl.yml` 的暫時性修改（M17／M18 重製）皆已 `diff -q` 確認還原，`__pycache__` 已清除。

**VERDICT: NOT-READY**

---

## Iteration 2 修正記錄（lead，2026-09-05T14:52:48Z）

三項發現全部處置完畢。**兩項 Major 以上皆分類為「新引入」——是 iteration 1 的修正動作本身造成的。**

| # | 嚴重度 | 分類 | 處置 |
| --- | --- | --- | --- |
| 1 | **Critical** | **新引入** | **修法整個換掉**：`last_status` 與 `last_written_status` 兩欄分家 |
| 2 | Major | **新引入** | 測試鍵名 `"rc"` → `"exit"`，並加一條**前提斷言** |
| 3 | Minor | 方法論 | 補多輪收斂測試，關掉「harness 只模擬單輪」這個結構盲區 |

### Critical：前兩次修法各自壞在相反的方向

| 版本 | 誠實嗎 | 收斂嗎 | 後果 |
| --- | --- | --- | --- |
| 原版（無條件寫 `last_status`） | **否**——宣稱一次沒發生的寫入 | 是 | `suppressed`→`mapped` 轉換時必然 `Aborted`；[US:S-6 AC 5] 的告示送不出去 |
| iteration 1（`last_status` 條件式） | 是 | **否**——比對永遠不回零 | 每輪重跑整條寫入鏈；`block.sh` 在 status 為空時嵌入當輪新的 `decided_at` ⇒ 雜湊每輪不同 ⇒ **每次外部 push 產生一個真實 commit** |
| **現版（兩欄分家）** | **是** | **是** | — |

**根因**：`last_status` 一欄同時扛「上一輪的**判定**」與「上次**寫進看板**的值」兩種語意，而 R-5.8 逐字說這兩者「不可互相取代」。**一欄裝不下兩個值**——前兩次修法都在同一欄上調整條件，方向相反、各壞一邊。

**現在的形狀**（即 (C) 原本就列的**選項 (a)**）：

| 欄位 | 語意 | 用途 | 回寫條件 |
| --- | --- | --- | --- |
| `last_status` | 上一輪的**判定** | R-5.2 漂移比對 | **無條件**——`null` 也是一個判定，不寫它比對就不收斂 |
| `last_written_status` | 上次**真的寫進看板**的值 | R-5.7 的 `expected` | **條件式（`$sw`）**——`write_status` 真的跑過才前進 |

**不需改動 U-4**：`record.sh` 以 `jq '. + $patch'` 就地合併並**明文保留未知欄位**（`:24`／`:202`／`:452`，orchestrator 開檔核對）。舊狀態檔缺這一欄時讀取端回退到 `last_status`——本欄引入之前，`last_status` 記的就是「上次寫進看板的值」，**回退是正確的、不是將就**。

### Major #2 的教訓比缺陷本身重要

我補的 R-6.1c 測試用 `"rc": 1`，而 stub 只認 `"exit"`（`run-orchestration-tests.py:227`）——鍵名被**靜默忽略**，`resolve` 根本沒失敗，底下每一條「沒有回滾」的斷言**恆真通過**。

**而我還跑了 M18 突變「證明」它有效**——M18 是在 `resolve` 之後插入一個看板呼叫，那條斷言不管前提成不成立都會紅。**突變驗證了斷言，卻沒驗證前提。**

處置不只是改鍵名，而是加一條**前提斷言**（`r.rc != 0`）：若計畫的鍵名寫錯，這條會直接紅，不讓其餘斷言在空的前提上恆真通過。M20 突變確認。

**這是本 intent 同一個病的第四次**（U-10a 兩次、本單元兩次），形狀完全一致：**一條看起來在守、實際守不到的斷言**。

### 本輪新增的突變（2 條）

| # | 突變 | 結果 |
| --- | --- | --- |
| M20 | R-6.1c 的計畫鍵名改回 `"rc"` | 紅：`R-6.1c：**前提成立**——resolve 這一輪確實失敗` |
| **M21** | 把 (C) 的修法退回 iteration 1 的形式 | 紅：`test_multi_round_suppressed_converges` ＋ 3 條欄位集合斷言 |

**M21 是決定性的**——它證明多輪收斂測試**真的抓得到**那個 Critical，而不是又一條裝飾用的綠燈。**累計突變 21 條。**

### 本輪的機械證據（全部實跑）

| 項目 | 值 |
| --- | --- |
| stub 行為測試 | **39 tests, 145 checks, 0 failures**（iteration 1 後為 37/134） |
| `bash -n`（自 YAML 抽出的 orchestrate 腳本） | 通過 |
| `impl.yml` | 894 行（`orchestrate` 的 `run:` 佔 **782**） |
| `run-orchestration-tests.py` | 1317 行 |
| 兩支 contract validator | 皆 passed |
| `ci.yml` | 仍 `103 0` |
| U-3 stub（我跨單元改過它） | 31 tests, 173 checks, 0 failures |

### lead 在本輪自己造成的兩次破壞（如實記載）

1. **R-6.1c 的鍵名**（見上）——沒驗證前提就宣稱測試有效。
2. **改註解時 `s.index()` 抓錯錨點**：R-3.0 排除路徑也有一個同樣縮排的 `patch="$(jq -nc`，於是 `end < start`，splice **複製了 275 行**，`bash -n` 語法錯誤、56 條測試紅。已精準切除重複段並刪掉矛盾的舊註解。

**兩次同一個形狀：沒先驗證前提就動手。** 這也是本輪把「前提斷言」寫進測試的直接由來。

## lead 的建議與人工決定（**gate 必讀**）

**lead 建議再跑 iteration 3，人工決定為「收掉」。** 兩者的依據都記在這裡，不由 lead 片面選邊：

- **支持再跑**：iteration 2 的兩項 Major 以上**分類皆為「新引入」**，lead 於派工前訂定的判準（`project.md` 的 `application-design:c4`：驗證輪的 Critical／Major 若源自上一輪修正動作，不計入原始上限、須再跑一輪）**條件成立**。且本輪修法**動到狀態檔的 schema**（新增 `last_written_status`），比前一輪更深。
- **支持收掉**：本輪的信心有三道新的機械證據撐著（M21 證明多輪測試抓得到、M20 證明前提斷言抓得到、回退測試鎖住 schema 演進的相容性），且新增的兩條測試針對的是**「測試本身失效」這個元層次問題**，不是又一個補丁。

**lead 對自己這輪產出的信心來自 lead 自己寫的測試——這正是本輪反覆出問題的地方，gate 覆核時請把這一點納入考量。**

**未被第三輪對抗式審查覆蓋的部分**：兩欄分家的修法、三條新測試、以及回退邏輯，**只經過 lead 自己的驗證**。
