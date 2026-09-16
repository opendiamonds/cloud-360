# Unit of Work — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: units-generation（Inception 2.7）· Record: 260822-gh-projects-sync
     來源標籤：[ad:*] 指 application-design 五份產出；[req:*] 指 requirements.md；
     [US:S-n AC m] 指 stories.md；[Qn] 指本站問題檔。
     **本檔只描述單元是什麼、擁有什麼、怎麼驗**；依賴拓撲在 unit-of-work-dependency.md，
     故事對應在 unit-of-work-story-map.md。**不含實作順序或關鍵路徑**——那是 2.8 的經濟決策。 -->

## 上游輸入

本分解的每一個單元都可追溯到下列已核可產出：

- **application-design 五份**（reviewer iteration 3 判 READY）：`components.md` 的 7 個元件（C-1～C-7）與 4 支 workflow 及其可重用性形狀；`component-methods.md` 的方法簽章、共用型別與 7 種 `reason_code`；`services.md` 的 4 個執行單元（S-A～S-D）、concurrency 配置與服務契約；`component-dependency.md` 的依賴矩陣、共享資源競爭點與 55 條 FR／NFR 雙向對照；`decisions.md` 的 ADR-A1～A10、ADR-0006 四面向重跑、CAP-11 可行性補評估與 PRE-1-a。
- **requirements.md**（Revision 1）：40 FR、15 NFR、6 約束、8 假設。
- **stories.md**（Revision 1）：11 則故事、65 條 AC、全域 DoD、PRE-1，以及三處已定案的同批次約束。

## 切分判準

依 `project.md ## Corrections`：**工作單元的切分判準是「驗證方式與失敗模式是否同類」，不是元件該怎麼分配**（[Q1=A]）。

本設計實際有**六種不可互相替代的驗證方式**。同一個單元內只允許一種——這使「這個單元完成了嗎」永遠只有一個判準：

| 類 | 驗證方式 | 失敗長什麼樣 | 落在哪些單元 |
| --- | --- | --- | --- |
| ① | 純文字 fixture 斷言（零 I/O、零 API） | 輸出錯的 Status、讀到錯的欄位值 | U-1 |
| ② | 純文字渲染與雜湊（零 I/O） | 雜湊誤判使反向同步全面誤報 | U-2 |
| ③ | 真實 Projects v2 API 讀寫（需憑證、網路、測試看板） | API 錯誤碼、item 狀態不符、分頁漏讀 | U-3 |
| ④ | git 與 repo 行為（需分支、分支保護、CI 觀察） | push 被拒、既有 CI run 被取消 | U-4 |
| ⑤ | Issues REST 行為（搜尋、建立、去重） | 重複開 issue、找不到既有 issue | U-5 |
| ⑥ | workflow 執行期行為（真實事件、佇列、排程、CI 紅綠） | 事件沒觸發、並行取消、排程撞期、斷言沒紅 | U-6～U-9 |

> **U-10a／U-10b 屬「建置與觸發設定」**，不在上述六類之內——它們觀察的是「觸發有沒有發生」而非執行期行為。Revision 1 把原 U-10 依**失敗模式**拆開（開發者的 CI 被取消 vs 反向 PR 燒 runner），兩者的消費端也不同（U-4 vs U-8）。

**第⑥類拆成四個單元而非一個**：四支 workflow 的失敗模式彼此不同（事件觸發 vs 排程產報告 vs 開 PR 防迴圈 vs CI 紅綠），合併會讓單一單元的完成判準同時指涉四種情境。這是 12 個單元高於 [Q2=A] 的 8–10 的**兩個原因之一**（另一個是 Revision 1 把 U-10 拆為 U-10a／U-10b，見該節），如實記載而非硬併。

## 單元定義

### U-1 — 映射與解析 composite action

| 項目 | 內容 |
| --- | --- |
| `kind` | `library`（被呼叫的可重用碼，無獨立執行期） |
| 擁有 | [ad:C-1 `sync-map`] 的七條判定順序與對照表、[ad:C-2 `record-reader`] 的 `getField()` 語意複製與 stage 清單逐檔解析、自訂欄位值的格式與 50 字元截斷規則 |
| 交付 | `.github/actions/aidlc-sync-map/action.yml` ＋ 其 fixture 集 |
| 驗證方式 | ①純文字 fixture 斷言。**不得**在此單元的驗證中出現任何網路或檔案系統 I/O——那會摧毀它被 fixture 驅動的能力（[US:S-10 AC 1] 的前提） |
| 完成判準 | 給定 record 文字，輸出的 `Decision` 三元組正確；`get_field` 的四條行為（第一個 match／存在但空／缺席／縮排不算）各有反例通過；對照表為總函式（[US:S-2 AC 15]） |
| 複雜度 | **M** |
| 實作註記 | 本 repo **無 composite action 先例**（`.github/actions/` 不存在），此為首例；且 `validate_repo_contract.py` 的 `REQUIRED_FILES` 不涵蓋它，被改名或刪除時無機制攔截（[ad:ADR-A1] 已記為已知缺口） |

### U-2 — 受管區塊渲染與雜湊

| 項目 | 內容 |
| --- | --- |
| `kind` | `library` |
| 擁有 | [ad:C-6 `managed-block`] 的 `render`／`parse`／`content_hash`；受管區塊必載的四項內容（Status 與對照表列或不寫的原因類別＋時間戳、`[S]`／`— SKIP` 差別、OOS-2 說明、「空欄位＝不受管」說明） |
| 交付 | 渲染與解析模組 ＋ 其 fixture |
| 驗證方式 | ②純文字渲染與雜湊 |
| 完成判準 | 相同輸入產生相同雜湊；格式變更使雜湊改變；`parse` 對無標記的 issue body 回 `null` |
| 複雜度 | **S** |
| 實作註記 | **[ad:ADR-A6]：格式一旦上線即為契約，是本設計最不易反轉的決定。**改格式而不重新基準化雜湊，會讓下一輪反向同步把全部受管 item 誤判為人為變更。ADR-A6 已把「設計一個機制（而非流程紀律）使格式變更與重新基準化不能脫鉤」指派 functional-design |

### U-3 — 看板客戶端

| 項目 | 內容 |
| --- | --- |
| `kind` | `library` |
| 擁有 | [ad:C-3 `board-client`] 的六個方法、Projects v2 GraphQL 呼叫、欄位 id 解析、分頁、寫入前回讀比對、首建專屬檢查、重複建立防護 |
| 交付 | 看板存取模組 |
| 驗證方式 | ③真實 Projects v2 API 讀寫，對**獨立測試 Project**（[ad:ADR-A3]，[Q4=A] 於 application-design） |
| 完成判準 | 回讀不符時回 `Aborted` 且**不送出寫入**；重複執行首建不產生第二則 issue；範圍外寫入回 403（**僅「直推保護分支」半邊**——另一半見下方註記） |
| 複雜度 | **L** |
| 實作註記 | 本 repo 無 Projects v2 先例，分頁／欄位 id／錯誤碼全新寫。**[US:S-10 AC 5] 的第二個例子（改 record 目錄以外的檔案應回 403）在本設計下無機制可產生**——候選為 Repository Rulesets 的 file-path restriction，已列 **PRE-1-a** 實測；不可行時該 AC 需回 user-stories 改寫 |

### U-4 — record 回寫與同步狀態

| 項目 | 內容 |
| --- | --- |
| `kind` | `library` |
| 擁有 | [ad:C-4 `binding-store`] 的綁定編號讀寫、`<record>/sync-state.json`、`commit_and_push`（只推觸發分支、訊息含 `[aidlc-sync]`、路徑限 record 目錄下兩檔） |
| 交付 | record 側持久狀態模組 |
| 驗證方式 | ④git 與 repo 行為 |
| 完成判準 | 推 `ut`／`main` 被分支保護拒絕回 `Rejected`；回寫只落在觸發分支且僅涉 record 目錄下的綁定編號與 `sync-state.json`；commit 訊息含 `[aidlc-sync]` |
| **不**擁有 | **[US:S-1 AC 7]（回寫 commit 不得取消既有 `ci.yml` run）歸 U-10a**。理由：讓那件事為真的機制是 `ci.yml` 的 `paths-ignore`，不是本單元的回寫行為。若兩處都掛，U-4 需要 U-10 才驗得完、U-10 需要 U-4 才有 commit 可測——**依賴圖會出現環**，而 edge block 必須無環 |
| 複雜度 | **M** |
| 實作註記 | `sync-state.json` 的 schema 需含版本欄位（[ad:services.md] 的服務契約：跨輪相容性必須維持，舊格式在新版讀取時不得崩潰） |

### U-5 — 通報

| 項目 | 內容 |
| --- | --- |
| `kind` | `library` |
| 擁有 | [ad:C-5 `notifier`] 的 `notify`／`resolve_if_open`、失敗身分 `(intent_id, reason_code)`、以既有 issue 為記憶的收斂演算法（[ad:ADR-A8]） |
| 交付 | 通報模組 |
| 驗證方式 | ⑤Issues REST 行為 |
| 完成判準 | 同一鍵連續失敗兩輪後，該鍵的開啟中通報 issue 數為 1 且 comment 數增加 1（[ad:ADR-A8] 補回 S-8 的二元 AC）；`reason_code` 為機制正常判斷者**不使 workflow 紅燈** |
| 複雜度 | **S** |
| 實作註記 | **不新增任何持久狀態**——記憶體是 GitHub issue 本身。`sync-state.json` 不承載失敗歷史 |

### U-6 — 正向同步 workflow

| 項目 | 內容 |
| --- | --- |
| `kind` | `service`（被執行的東西，有執行期行為、並行與觸發特性） |
| 擁有 | [ad:S-A] 的觸發設定、registry 驅動的選取與分流（無綁定者首建、已綁定者比對漂移）、分支界 concurrency group、`[aidlc-sync]` 的兩道整輪層級自我排除 |
| 交付 | `aidlc-sync-forward.yml` ＋ 其 `*-impl.yml`（`on: workflow_call`，全參數化，[ad:ADR-A10]） |
| 驗證方式 | ⑥workflow 執行期（真實事件、佇列） |
| 完成判準 | push 與同分支 PR 事件落在同一 concurrency group 且排隊不取消；新 intent 的 record 首次推送後看板出現 item 且 Status 為 `Ready`；`[aidlc-sync]` commit 不觸發任何看板寫入 |
| 複雜度 | **M** |
| 實作註記 | 選取為 registry 驅動 ⇒ **fixture 永不被選中**（不在 registry），這是 fixture 隔離在事件路徑上的保護（[ad:services.md]） |

### U-7 — 對帳 workflow 與編排器

| 項目 | 內容 |
| --- | --- |
| `kind` | `service` |
| 擁有 | [ad:S-B] 與 [ad:C-7 `reconciler`]——兩者是同一個東西的兩面，拆開後都無法獨立驗收；每日排程、處理量上限、`ReconcileReport` 的九個欄位、一致率、五份清單、延遲量測 **（G-1 修補後：補入 `undecidable`，清單數由五變六、欄位數隨之 +1；見 U-7 的 `functional-design/domain-entities.md`。本處原文維持）** |
| 交付 | `aidlc-sync-reconcile.yml` ＋ 其 `*-impl.yml` ＋ 編排邏輯 |
| 驗證方式 | ⑥workflow 執行期（排程、報告產出） |
| 完成判準 | 一致率分母＝已綁定−有未處理反向紀錄−`Parked` 非空（**維持上游兩類排除**，[ad:ADR-A5]）；三份清單各自獨立列出；補平計數等於實際補平數；`issue 與 Status 不相稱` 清單能抓到「issue 已關閉而 Status 不為 `Done`」 |
| 複雜度 | **L** |
| **已知上游契約缺口** | **[US:S-2 AC 4] 目前不可滿足。**該 AC 的 Then 要求「該 record 出現在對帳報告的**「無法判定」**清單中」，而 [ad:component-methods.md] 的 `ReconcileReport` 只有 `unparseable`（對應 `reason_code="unparseable"`，[req:FR-J3] 的「必要區塊缺失」），**沒有承接 `reason_code="undecidable"`（訊號不落在對照表任一列）的欄位**。兩者是不同的 `reason_code`（[ad:component-methods.md] 的七種列舉），不能互相頂替。此為 **application-design 的契約缺口，本站發現並標出，不逕自改上游已核可的型別**。指派 **functional-design**（Construction 的資料模型細化站）：在 `ReconcileReport` 增設 `undecidable: [intent_id]`，並確認 `sync-map` 的 `undecidable` 出口確實流向它 |
| 實作註記 | 補平成功**不使 workflow 紅燈**（[US:S-7 AC 5]，解掉「成功補平 ⇒ 紅燈」那條矛盾）；排程須避開三支既有 cron |

### U-8 — 反向同步 workflow

| 項目 | 內容 |
| --- | --- |
| `kind` | `service` |
| 擁有 | [ad:S-C] 的排程觸發、看板讀取、雜湊比對、開 PR、逐 intent 歸屬判定、防迴圈三道防線 |
| 交付 | `aidlc-sync-reverse.yml` ＋ 其 `*-impl.yml` |
| 驗證方式 | ⑥workflow 執行期（排程、開 PR、防迴圈） |
| 完成判準 | PR 的 diff **不含 `aidlc-state.md` 任何一行**；受管區塊雜湊未變時不產生 PR；PR 內含 intent X 而不含 Y 時，正向對 X 暫停、對 Y 照常寫（逐 intent，非全域） |
| 複雜度 | **M** |
| 實作註記 | **over-suppression 是本路徑的真正風險**（[ad:CAP-11 補評估]）：先例以 `--all-intents` 開單一 PR，在該形狀下「某 intent 有未處理反向紀錄」無法只從 PR 開關狀態判定。本設計以「讀 PR 的 diff 是否含該 intent 的 record 路徑」判定，**未實測** |

### U-9 — 自我測試 workflow

| 項目 | 內容 |
| --- | --- |
| `kind` | `service` |
| 擁有 | [ad:S-D] 的兩段式驗證（fixture 驅動的 dry-run ＋ 對獨立測試 Project 的端到端）、承載形式的靜態檢查（job 步驟不含代理式引擎步驟）、權限的 403 斷言 |
| 交付 | `aidlc-sync-selftest.yml` ＋ fixture 集的驅動端 |
| 驗證方式 | ⑥workflow 執行期（CI 紅綠、突變驗證） |
| 完成判準 | 把映射改壞（`[?]` → `In progress`）時 CI 紅燈且輸出指出預期與實得；把判定搬進 agent step 時靜態檢查失敗；憑證做範圍外寫入時回 403 |
| 複雜度 | **M** |
| 實作註記 | 測試 item 必須是**本次執行專屬**或位於獨立測試看板——常駐於 #16 會成為第 72 張卡進入 P3 視野，且並行 CI 寫同一 item 會觸發回讀不符而**自動增生 issue**（[ad:ADR-A3]） |

### U-10a — `ci.yml` 的回寫排除

| 項目 | 內容 |
| --- | --- |
| `kind` | `packaging`（建置與觸發設定，非新行為） |
| 擁有 | `ci.yml` 的 `paths-ignore` 或等價手段，使同步的回寫 commit 不觸發一輪 CI、也不取消既有 run（[US:S-1 AC 7]） |
| 交付 | 對 `.github/workflows/ci.yml` 的修改 |
| 驗證方式 | 建置與觸發設定（觀察觸發是否發生） |
| 完成判準 | 回寫 commit 推送後，該分支上既有的 `ci.yml` run 未被取消，且未新增一輪四個 job |
| 複雜度 | **XS** |
| 消費端 | **U-4**——是它的回寫行為需要這道排除 |
| 實作註記 | `ci.yml` 的檔名是 load-bearing（在 `REQUIRED_FILES` 內，改名會讓 contract 紅燈） |

### U-10b — 反向 PR 的高成本 workflow 排除

| 項目 | 內容 |
| --- | --- |
| `kind` | `packaging` |
| 擁有 | 高成本 `on: pull_request` workflow（至少 `ui-regression`）對反向同步 PR 的排除（[US:S-6 AC 7]） |
| 交付 | 對既有 gh-aw workflow 觸發條件的修改，或等價的 label 機制 |
| 驗證方式 | 建置與觸發設定 |
| 完成判準 | 反向 PR 開啟後，`ui-regression` 未對其執行 |
| 複雜度 | **XS** |
| 消費端 | **U-8**——是它的反向 PR 會啟動整組 gauntlet |
| 實作註記 | `ui-regression.md` 自述曾在單一 PR 燒掉約 6 小時 runner 時間、零測試執行 |

### U-11 — README 指路段落

| 項目 | 內容 |
| --- | --- |
| `kind` | （留空——五類皆不合，收完整設計矩陣） |
| 擁有 | [req:FR-H1]：`README.md` 增加一段含 Project #16 連結的文字，說明該看板是需求清單的正本 |
| 交付 | `README.md` 的一段新增文字 |
| 驗證方式 | 文字比對 |
| 完成判準 | 存在含 Project #16 連結的段落；`git diff --numstat` 對 `README.md` 的**刪除行數為 0**（只增不動，[US:S-11 AC 2]） |
| 複雜度 | **XS** |
| 實作註記 | 與全域 DoD 的 `validate_repo_contract.py`（其 `REQUIRED_TEXT` 已鎖住 README 關鍵字）有部分重疊，不需另設檢查 |

## 部署模型

依 [Q3=A]：**技術上各單元可獨立部署**（各自一個 PR，合併進 `ut` 即部署），**但有三處同批次約束**——它們寫在 `unit-of-work-dependency.md` 的獨立表格，**不是 DAG 邊**。

`library` 類單元（U-1～U-5）本身沒有觸發條件，合併後不會自己跑；它們的「部署」是被 `service` 類單元引用。這使它們可以先行合併而不產生任何可見的中間態——**但這是拓撲事實，不是建議的順序**（順序屬 2.8）。

## 不由任何單元承載的項目

| 項目 | 為什麼 | 落點 |
| --- | --- | --- |
| **PRE-1**（含 PRE-1-a） | 產出是一份實測結論，沒有可部署的東西（[Q5=A] 於 user-stories 定案） | 上線前置條件；其在 Construction 的留痕形式由 [US-OQ-2] 指派 delivery-planning |
| **US-OQ-1～7 的決定** | 已於 application-design 全部產出決定，不是待做的工作 | 已落在 `decisions.md` 的 ADR 與各單元的實作註記 |
| **[req:OQ-4]**（`.md` ↔ `.lock.yml` 漂移守門員） | 已指派 `ci-pipeline` 站 | 不在本 intent 的單元集合內 |

---

## Revision 1（2026-08-29T03:38:22Z，delivery-planning 的排序驗證觸發）

**觸發來源**：2.8 的 Step 4 以腳本對 yaml edge block 驗證候選 Bolt 序列時發現，原 U-10 同時被 [dp:Q1=C] 的「U-4 ＋ U-10 綁綁」與 DAG 的「U-10 依賴 U-8」拉扯，傳遞下去會逼出 8 單元的巨型 Bolt——正是 [dp:Q1] 已否決的形狀。使用者於 [dp:F1=A] 裁決回本站以 Modify 模式拆分。

**根因**：原 U-10 內含**兩個消費端不同的變更**。2.7 rev0 依「驗證方式」把它們併成一個單元（都是建置與觸發設定），但 `project.md` 的判準是「驗證方式**與失敗模式**是否同類」——兩者的失敗模式不同（開發者的 CI 被取消 vs 反向 PR 燒掉 6 小時 runner），消費端也不同（U-4 vs U-8）。**拆分後比 rev0 更符合本站自己的判準。**

**改動範圍**：僅 U-10 相關。其餘 10 個單元的定義、邊界、kind、複雜度**一字未動**；[Q1]～[Q4] 的原答案與 Step 5 的計畫核可不重取（拆分不改變切分軸、粒度區間的意圖、部署模型或 kind 標註原則）。

| 檔案 | 改動 |
| --- | --- |
| `unit-of-work.md` | U-10 拆為 U-10a／U-10b；總覽表拆列；單元數 11 → 12；六類驗證方式表補註「建置與觸發設定」不在六類內 |
| `unit-of-work-dependency.md` | yaml edge block 的 `U-10-existing-file-adjustments` 拆為兩個節點；散文邊表、整合契約、同批次表、平行機會、交付數字同步 |
| `unit-of-work-story-map.md` | [US:S-1 AC 7] → U-10a、[US:S-6 AC 7] → U-10b；覆蓋表拆列 |

**rev0 已歸檔**於 `archive/*.rev0.md`，供比對。
