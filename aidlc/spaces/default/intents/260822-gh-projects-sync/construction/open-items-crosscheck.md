# open-items.md 逐項交叉核對（唯讀）

**建立時間**：2026-09-05T18:42:16Z（`date -u`）
**範圍**：`construction/functional-design/open-items.md`（222 行）的**每一個**登錄條目 × 已交付的實作（U-1／U-2／U-3／U-4／U-5／U-6／U-7／U-8／U-10a／U-11）
**性質**：唯讀。本次未修改任何實作檔、上游 artifact 或既有 code-summary，只新增本檔。
**未採信任何 code-summary 的自陳**——每一項都回實作檔或上游檔實測。

---

## 1. 撈取方式與總項數（證明沒漏前綴）

### 1.1 三種載體，分別機械撈取

`open-items.md` 的項目分散在**三種**結構載體，只掃其中一種必漏：

| # | 載體 | 撈取指令 | 結果 |
| --- | --- | --- | --- |
| 1 | Markdown 表格列 | `grep -nE '^\| ' open-items.md`（再扣除表頭與 `\| --- \|` 分隔列） | **47 列**，其中頂部「新引入／既存漏審/新設計問題」統計表 3 列非項目 ⇒ **項目型表格列 44** |
| 2 | 條列項目 | `grep -nE '^- \*\*' open-items.md` | **12 條**（`### 其餘（code-generation 承接）` 8 條 ＋ `### 已於本輪關閉` 4 條） |
| 3 | `###` 級獨立登錄 | `grep -nE '^### ' open-items.md`（扣除純敘述小節） | **3 節**（`B:M-1`／`CG:OPEN-1`／`CG:OPEN-2`） |
| 4 | 散文中的關閉登錄 | `open-items.md:38` 的「附帶關閉」段 | **1 段**（涵蓋 4 個 id） |

**可追蹤條目總數 = 44 ＋ 12 ＋ 3 ＋ 1 = 60。**

### 1.2 前綴普查（這一步正是 orchestrator 漏掉的環節）

```
grep -oE '\*?\*?(A|B|N|CG):[A-Za-z]+-[0-9]+[a-z]?(\([AB]\))?|\*?\*?[CMm]-[0-9]+\.[0-9]+' open-items.md \
  | tr -d '*' | sort -u
```

實測回出 **57 個相異識別字**，落在 **7 個前綴族**：

| 前綴族 | 實際出現的 id |
| --- | --- |
| `A:` | A:C-1〜3、A:M-1〜10、A:m-2〜m-9 |
| `B:` | B:C-1、B:M-1〜5、B:m-1〜m-7、B:m-9 |
| `N:` | N:C-1、N:C-1(A)、N:C-2、N:C-3、N:M-1〜6、N:M-1(B)、N:M-2(B)、N:M-4(B) |
| `C-` | C-6.2（引用）、C-7.1、C-7.2 |
| `M-` | M-7.1、M-7.2 |
| `m-` | m-7.1 |
| **`CG:`** | **CG:MIN-1（流程註記）、CG:OPEN-1、CG:OPEN-2** |

> **任務簡述寫的是「六種前綴」——實測是七種。** 第七種 `CG:` 是 code-generation 自己在本檔追加的登錄（`open-items.md:197`／`:203`／`:216`），其中 `CG:OPEN-1` 與 `CG:OPEN-2` 是**尚未關閉的 open item**。用「六種前綴」當清單去掃，會恰好漏掉 code-generation 自己留下的兩筆待辦。

無 id 的**聚合列**另有 3 筆（`Major ×4`、`Minor ×4`、`Minor ×6`），共承載 14 個子項，其中 **1 個（iteration 6 的 Major 第 4 項，原文只寫「等」）從未被具名**。

### 1.3 本檔自身的計數誤差（順帶查出）

`open-items.md:116` 寫「其餘 **20 項**」，而 `:108` 的「Bolt 開工前處理」列 5 項。5 ＋ 20 = 25，但六張分組表實際有 **28 列**（29 個 id，因 `A:m-2／B:m-7` 共用一列）。**本檔自己少算 3 項**——這是它作為清單被使用時的第二個結構性風險（第一個是前綴族的多樣性）。

### 1.4 三類計數

逐段點算第 2 節的判定欄（每一個條目恰好一個判定），結果如下：

| 判定 | 條目數 | 逐段來源 |
| --- | --- | --- |
| **已被涵蓋**（含 5 項「實作已涵蓋｜文件殘留」） | **30** | 2.1:4／2.2:4／2.3:2／2.4:1／2.5:3／2.6:1／2.7:3／2.8:4／2.9:1／2.10a:1／2.10b:2／2.10c:1／2.11:2／2.12:1 |
| **未被涵蓋** | **26** | 2.2:4／2.3:2／2.4:1／2.5:2／2.6:2／2.7:3／2.8:1／2.10a:2／2.10c:7／2.12:2 |
| **不適用** | **1** | 2.11 的「reviewer 複查四項未成立」（記的是不成立的發現，非待辦） |
| **無法判定** | **3** | 2.1 的 m-8 命名衝突／2.9 的 `Major ×4` 第四項未具名／2.11 的送審前自檢兩缺口 |
| 合計 | **60** | |

**兩條聚合列的歸類規則**（否則上表不可複算）：
- 2.9 的 `Minor ×4` 自標「已處理」⇒ 計為 **已被涵蓋**。
- 2.10c 的 `Minor ×6` 內含 2 已涵蓋／3 未涵蓋／1 無法判定 ⇒ 依多數計為 **未被涵蓋**（子項判定見該列）。

> 第 3.4 節列的是 **6 個無法判定的子問題**；其中 3 個落在上表的 3 個「無法判定」條目內，另 3 個是「已被涵蓋／未被涵蓋」條目**內部**的次要不確定（Minor ×6 的 (b)(e)、A:m-5 的第二處），不另計為條目。

「已被涵蓋」中有 **5 項屬「實作已涵蓋｜文件殘留」**（A:M-3、A:M-2、B:m-3、B:M-3、C-7.2）——執行期行為正確，但被 open item 點名的那句設計文字一字未改。這一類在第 4 節單獨列出，因為它們對**下一個讀設計文件動手的人**仍是活的陷阱。

---

## 2. 逐項判定

判定用語：
- **已被涵蓋** — 實作或上游檔已解決，附檔名:行號或測試名
- **已涵蓋(實作)｜文件殘留** — 執行期正確，但被點名的設計文字未改
- **未被涵蓋** — 仍開著，附後果
- **無法判定** — 說明卡在哪

### 2.1 已修的 4 個 Critical（複驗實作是否真的承接）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| A:C-1 | Critical | (已修) | **已被涵蓋** | R-6.8 修復路徑落地：`aidlc-sync-reconcile-impl.yml:820-829` 的 patch 含 `managed_block_hash` ＋ `last_synced_at`；`run-reconcile-tests.py:610` 斷言六欄集合。R-6.2 已限定為補平路徑（同檔 `:702`） |
| A:C-2 | Critical | (已修) | **已被涵蓋** | R-3.0 確實在分流之前：`aidlc-sync-forward-impl.yml:452-495` 的排除閘門 `return 0` 早於 `:497` 的 `create_item` 首建路徑。`business-rules.md:42` 為規則正本 |
| A:C-3 | Critical | (已修) | **已被涵蓋** | R-5.12 逐欄回寫：`forward-impl.yml:786-792` 以 `$sw`／`$fw`／`$bw` 三個獨立旗標構成 patch，非全有全無 |
| B:C-1 | Critical | (已修) | **已被涵蓋（常數改名）** | 標記語法在 U-2 定義：`block.sh:99-101`（`MARKER_SIGIL`／`MARKER_BEGIN_PREFIX`／`MARKER_END`）；U-3 **從 block.sh 萃取而不複製字面**：`board.sh:334-363`（`extract_marker`）＋ 形狀驗證 `:357-363`；R-6.6 標記損壞處置 `board.sh:955-961`。**注意**：ADR 修法寫的名稱 `MANAGED_BLOCK_BEGIN`／`MANAGED_BLOCK_END` 在整個實作中**零命中**（全樹 grep）——名稱不同、互鎖語意等價，但依名字比對會誤判為未實作 |
| 附帶關閉段（`:38`：A:M-1／B:M-2／兩組 m-8） | — | (已修) | **無法判定（登錄矛盾）** | `:38` 稱「兩組的 m-8（ADR-0015 §13 未代入的 `%s` 佔位符）」已關閉——實測 ADR-0015 全文 `%s` 命中數為 **0**，該項確實關閉。**但 `:57` 的 `A:m-8` 是另一件事**（「表內序數倒置」）且仍列為 open。同一個 id 在同一份檔案裡指兩件事，只有人工裁決能解。本核對以 `:57` 的表格列為準（見 2.2） |

### 2.2 Open items — U-6 forward-workflow（8 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| A:M-3 | Major | code-generation | **已涵蓋(實作)｜文件殘留** | 實作走回讀路徑：`forward-impl.yml:715-740`（寫入後 `read_item` 取 `managed_block_hash`）。殘留未改：`U-4/domain-entities.md:18`「由 U-2 的 `content_hash` 產生」、`U-6/business-rules.md:227`「（供 R-5.4 回寫）」。**實質危害低**——`board.sh:520` 註明 hash 由 U-2 的 `parse`＋`hash` 產出，故 U-4 那句與回讀路徑不矛盾 |
| **A:M-4** | Major | code-generation | **未被涵蓋（後半段）** | 前半「僅回寫 `SyncState` 語意未定義」**已涵蓋**：`forward-impl.yml:469-474` 明確定為三欄，並就地揭露與 R-5.8 的衝突、指派 Bolt 1 gate。**後半仍完全開著**：R-3.0 的排除閘門在 `:455-495` 就 `return 0`，而 `notice_due` 遲至 `:541` 才計算 ⇒ **`unparseable ∩ reverse_rejected` 的 intent 永遠拿不到 [US:S-6 AC 5] 的告示**。詳見第 3 節 |
| A:M-7 | Major | code-generation | **已被涵蓋** | `notify.sh:149` `FAILURE_CODES="ExternalError Rejected Aborted CannotCreate Failed"`（五個，依「Plan Approval 裁決 2」），與 U-6 R-6.1b 的五個一致；U-6 呼叫端 `forward-impl.yml:655`／`:711` 確以 `Failed` 通報。設計檔 `U-5/domain-entities.md:13` 仍列四種（文件殘留） |
| A:M-8 | Major | code-generation | **已被涵蓋** | 「本輪處理成功」在實作中就是 `INTENT_OK`，六個賦值點全部可查：`forward-impl.yml:365`／`:382`（重置）、`:492`（R-3.0 排除路徑）、`:563`／`:574`（無漂移／深度防禦）、`:807`（完整寫入鏈成功）；R-6.1b 的消費點在 `:851-861`。歧義由「無寫入路徑亦計為成功」明確消解 |
| **A:M-10** | Major | code-generation（純結構） | **未被涵蓋** | `U-6/business-rules.md` 的 `render` 列**仍重複兩次**（`:216` 與 `:227`）；`Context` 表（`:218-226`）仍把 R-7 方法表切斷。以腳本偵測「續表無表頭」得 `224 → 227`，確認斷裂仍在 |
| A:m-3 | Minor | ADR-0015 §14／Bolt 1 gate | **已被涵蓋** | ADR-0015 `:134`（§14）逐字寫明前綴四選一且「`suppressed`（`frozen: `）皆有對應」，上游 `component-methods.md:56` 與 `decisions.md:89` 亦列該集合 ⇒ `frozen: ` 的指派有上游來源。實作 `map.sh:453` 沿用；`undecidable` 依 §14 **不猜前綴**（`map.sh:416-421`），矛盾消除 |
| **A:m-7** | Minor | Bolt 1 gate | **未被涵蓋** | `U-6/business-rules.md` 全檔對「次日對帳／每次 push 一則／時間界」零命中——R-5.11 的假 `Aborted` 通報**仍未寫下時間界**。實務衝擊被 U-5 的去重吸收（`notify` 為「開或追加」，同鍵只有一則 issue），但登錄本身未關 |
| **A:m-8** | Minor | code-generation | **未被涵蓋** | 序數仍倒置：`U-6/business-rules.md` R-5.12@`:122`、R-5.13@`:123`、**R-5.11@`:124`**。純結構、無執行期影響 |

### 2.3 Open items — U-7 reconcile-workflow（4 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| A:M-5 | Major | 需新 ADR 節或改掛 Bolt 3 gate | **已被涵蓋** | U-8 **主動接住了**：`aidlc-sync-reverse-impl.yml:125` 逐字寫「與 U-7 的 R-7.1 同一條規則（**A:M-5 的承接**）」，`:132` `ref: ${{ inputs.trunk_ref }}`，`aidlc-sync-reverse.yml:93` `trunk_ref: ut`。`run-reverse-tests.py` 的 `test_checkout_pins_the_trunk_ref` 通過（38 tests／237 checks／0 failures） |
| A:M-6 | Major | ADR-0015 需新增一節 | **已被涵蓋** | ADR-0015 `:123`（§13）已逐字列出「R-7.3 把 `ut` HEAD SHA 寫進報告以便事後查核」——**指標存在**，只是落在既有的 §13 而非新開一節。實作 `reconcile-impl.yml:946`／`:646` 輸出該值 |
| **A:m-4** | Minor | code-generation | **未被涵蓋** | `U-7/business-logic-model.md:116` 仍逐字寫「一致率的兩類排除、`reconcile` 的簽章、單一 intent 失敗不中止整輪**一字未改**」 |
| **A:m-9** | Minor | code-generation | **未被涵蓋** | `U-7/business-logic-model.md:26` 的序列圖仍寫「`SyncState`（**三欄 ＋ binding**）」，與 U-4 的七欄 schema（`U-4/domain-entities.md:15-21` ＋ `pending_reverse`）不符 |

### 2.4 Open items — U-4 binding-store（2 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| A:M-2 | Major | code-generation | **已涵蓋(實作)｜文件殘留** | 實作定案為 R-7.2 那一側：`aidlc-sync-reconcile.yml:74` `reconcile_branch_prefix: aidlc-sync/reconcile`、`reconcile-impl.yml:248` `PUSH_BRANCH="…/$(date -u +%Y-%m-%d)"`、`record.sh:189` `PROTECTED_BRANCHES="ut main"` 擋直推。殘留未改：`U-4/business-rules.md:38`「對帳（U-7）推**其排程觸發分支**」、`:47` 仍稱 ADR「不裁定」。**但這個修法連帶開出一個新缺口**——見第 3 節 (U7-3) |
| **A:m-5** | Minor | code-generation（純結構） | **未被涵蓋（至少一處）** | 以腳本偵測「續表無表頭」，`U-4/business-rules.md` 仍有 `38 → 50` 一處斷裂。原登錄稱「兩處」，第二處未被本次偵測命中（偵測器只認「續表無分隔列」這一種形狀），故只能確認**至少一處仍在** |

### 2.5 Open items — U-1 map-parse-action（5 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| B:M-1 | Major | code-generation | **已被涵蓋** | 實測 `U-1/functional-design/business-rules.md` 現為 `## R-6 群：scope_note …`（`:74`）與 `## R-7：總函式性`（`:107`），**同檔不再有兩個 `## R-6`** |
| B:m-3 | Minor | code-generation | **已涵蓋(實作)｜文件殘留** | 實作有該步驟：`map.sh:332` `scope_note="$(compute_scope_note)"`，落在 `list_stages` 之後、分支之前；純函式在 `:199-212`。設計檔未補：`U-1/business-logic-model.md:47-52` 的主流程圖只有「步驟 1 parse／步驟 2 map」，`:62` 的 parse 演算法段對 `scope_note` 零命中 |
| **B:m-4** | Minor | code-generation | **未被涵蓋** | `U-1/domain-entities.md:102` 仍寫「本檔新增而上游沒有的**有兩項**」。行號已由原登錄的 `:98` 位移到 `:102`（該檔上方被編輯過），計數是否過期未被重算 |
| B:m-5 | Minor | 需設計判斷；Bolt 1 gate | **已被涵蓋（待 gate 追認）** | `map.sh:346-348` 逐字引用 B:m-5，採 R-6.5 的字面（非空的雙 `none`）而非新裁決，並標明落點 Bolt 1 gate。**附帶查證**：該值在今日的資料流下**到不了受管區塊**——`unparseable` 會被 R-3.0（`forward-impl.yml:455`）在 `render` 之前擋下，故它只影響 composite action 的 output 契約 |
| **B:m-6** | Minor | Bolt 1 gate | **未被涵蓋** | `forward-impl.yml:536-539` 的漂移判定確實只比三欄（`status`／`field_value`／`reason_code`），`scope_note` 不在其中；而 `block.sh:287` 把它渲染進區塊、`content_hash` 涵蓋它。後果與登錄一致：**非當前 stage 的 scope 變動不觸發重寫**，受管區塊的範圍註記無限期陳舊，且不會產生假反向 PR（兩端同為舊值），故**無任何紅燈** |

### 2.6 Open items — U-2 managed-block（3 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| B:M-4 | Major | nfr-requirements gate | **已被涵蓋** | `open-items.md:192` 記其於 nfr-requirements 輪關閉；U-2 的 SEC-5 已重判（`U-2/security-requirements.md:61`）。**但重判沒有傳播到寫入點**——那是 N:M-1(B)，仍開著（見 2.10） |
| **B:m-1** | Minor | code-generation | **未被涵蓋（3 處中僅 1 處已改）** | 已改：`U-2/domain-entities.md:23`（「churn 隱憂只作用在不寫分支上」）。未改：`U-2/business-rules.md:36`（「兩次語意相同的判定會有不同的 `decided_at` ⇒ 不同雜湊」，無分支限定）、`U-2/domain-entities.md:109`（同）。實作側正確：`block.sh:255-262`，`mapped` 支 `BLOCK_DECIDED_AT=""` |
| **B:m-2** | Minor | code-generation | **未被涵蓋** | `U-2/business-rules.md:14` 的 R-1.2 仍寫「兩個只在此處不同的 `Decision`」，而 `scope_note` 依 `U-1/domain-entities.md:32` 明訂**不進 `Decision`**——可判定方式的主詞仍然錯的 |

### 2.7 Open items — U-5 notifier／跨檔（6 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| B:M-3 | Major | code-generation | **已涵蓋(實作)｜文件殘留** | `aidlc-sync-reverse-impl.yml:308-311` 逐字引用 B:M-3 並宣告「本單元**不呼叫** `resolve_if_open`」，實作亦無該呼叫。殘留未改：`U-5/business-logic-model.md:82` 仍把 U-8 列為「呼叫」，而同檔 `:142` 的複核又寫 U-8「明記不呼叫」——同一份檔案自相矛盾 |
| B:M-5 | Major | nfr-requirements gate | **已被涵蓋** | 指標已補齊：`U-1/nfr-requirements/security-requirements.md:13`（逐字標明「此為 `open-items.md` 的 B:M-5……於 2026-08-30T05:10:02Z 補上」）、`U-5/nfr-requirements/security-requirements.md` 同有 §8 指標 |
| **A:M-9** | Major | Bolt 1 gate（登錄遺漏） | **未被涵蓋** | `bolt-plan.md:65` 的 Bolt 1 DoD 只有「**〔ADR-0015 §2 增列兩條〕**」；全檔對 `§14` **零命中**。ADR-0015 §14 自己寫「**確認人為 Bolt 1 的 gate**」，而該 gate 的 DoD 沒有這一條 ⇒ 一個 blocking 項不在它該被檢查的清單上 |
| **A:m-2／B:m-7** | Minor | code-generation | **未被涵蓋** | ADR-0015 `:7` 的 `Amends:` 行仍以截斷片段結尾：「……指標補於 …。**以下原文：** 對照表、**`application-design/component-methods.md`** 的 `parse` 簽章與 §C-7 …」——「以下原文」之後接的是半句話，無法履行比對用途 |
| **A:m-6** | Minor | Bolt 2 gate | **未被涵蓋** | `bolt-plan.md:79` 的 §13 條目仍吞掉 Bolt 2 的基線 DoD 本文：「……規則落點為 U-7 的 R-6／R-7 群。&nbsp;&nbsp;U-7 完成判準通過；PRE-1 第 2 項……」——基線 DoD 沒有自己的項目符號，讀起來像 §13 的一部分 |
| B:m-9 | Minor | ADR-0015／Bolt 2 gate | **已被涵蓋** | `U-7/domain-entities.md:17` 已有 `undecidable: [intent_id]` 欄；`component-methods.md:179` 有 G-1 的指標並註明「已於 U-7 關閉」；實作 `reconcile-impl.yml:949` 輸出 `undecidable=`、`:937` 明寫兩者不可互看 |

### 2.8 iteration 7 的發現（5 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| **C-7.1** | Critical | Bolt 1 開工前 | **已被涵蓋** | 補平路徑的 patch 恰為四欄、**不含 `last_synced_at`**：`aidlc-sync-reconcile-impl.yml:753-757`；`run-reconcile-tests.py:572`（`@purpose` 逐字引 C-7.1）與 `:605` 斷言。同檔 `:715-751` 完整記載缺陷、可達性與修法。**條目內的但書「三個寫者只對兩個做了語意對齊」亦已收斂**：R-5.4（`forward-impl.yml:790`，只在 `$bw==1` 時寫）／R-6.1（不寫）／R-6.8（`reconcile-impl.yml:827`，寫，理由為「已確認區塊存在於看板上」）三者語意一致 |
| **C-7.2** | Critical | Bolt 1 開工前 | **已涵蓋(實作)｜設計文件四處全數殘留** | 實作正確：`forward-impl.yml:790` `(if $bw == 1 then (.last_synced_at = $ts \| .managed_block_hash = …) else . end)`。**被點名的四處一處也沒改**：`U-6/business-logic-model.md:53`（序列圖仍只寫「`managed_block_hash` 維持原值」）、`:66`（fallback 仍寫「對應的**那一欄**維持原值」，單數）、`U-3/business-rules.md:129`（原 `:104`，仍寫「`managed_block_hash` 維持原值、**其餘欄位照常回寫**」）、`U-3/domain-entities.md:50`（同一句逐字）。詳見第 3 節 |
| M-7.1 | Major | code-generation | **已被涵蓋** | `forward-impl.yml:722-737`：R-5.4 的回讀 `rc != 0` 有明確出口，走 R-5.12 第四種「完全不回寫」並通報 `ExternalError` |
| M-7.2 | Major | code-generation | **已被涵蓋** | `forward-impl.yml:786-792` 以獨立旗標構成 patch ⇒「同輪兩步皆失敗」時 `last_synced_at` 與 `managed_block_hash` 皆不寫，字面互斥消失 |
| **m-7.1** | Minor | code-generation | **未被涵蓋** | `U-4/domain-entities.md:19` 仍寫「上一次**成功寫入**的時刻」，未收斂為 R-5.13 的「上一次**受管區塊**成功寫入的時刻」。該行有 iteration 3 的補註但未含 R-5.13 的限定 |

### 2.9 iteration 6 的殘留發現（2 個聚合列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| Major ×4 | Major | code-generation；標記語法兩項掛 Bolt 1 gate | **3 具名項已涵蓋、第 4 項無法判定** | (1) `parse` 對「BEGIN 有 END 無」→ **已涵蓋**：`block.sh:415-416`（`closed != 1` 回 null）＋ fixture `body-missing-end.md`；寫入端 `board.sh:958` 亦以 R-6.6 擋下。(2) 內嵌版本的跨版本比對 → **已涵蓋**：`block.sh:419-421`（`ver > FORMAT_VERSION` 回 null、未知版本回 null）＋ `format-migrations.md` 的五道互鎖 ＋ fixtures `body-future-version.md`／`body-corrupt-version.md`。(3) `U-4/domain-entities.md:39` → **已涵蓋**：現讀「`managed_block_hash` 有**兩個寫者**……修復路徑是 U-7 的 R-6.8」。(4) 原文只寫「**等**」，第四項**從未被具名** ⇒ **無法判定**，且沒有任何人能判定 |
| Minor ×4 | Minor | 已處理 | **不重驗（登錄自述已處理）** | 該列自標「已處理」；其中時間戳更正確可在 `U-6/business-rules.md:46` 見到（「原填 09:55:00Z 為未經 `date -u` 的編造值，已更正」） |

### 2.10 nfr-requirements 的發現登錄

#### Bolt 1 開工前必處理（3 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| **N:C-1** | Critical | Bolt 1 前重選機制 | **已被涵蓋** | 機制已重選，且正是登錄裡點名的候選：`ci.yml` 的 `paths-ignore` **只加在 `push` 側**（diff 顯示 `pull_request:` 上方有逐字說明「PR 的路徑過濾比對整個 PR 檔案集合……寫了會是假保證」）；`pull_request` 側改用新增的 `gate` job 讀 commit 訊息中的 `[aidlc-sync]` 標記，四個既有 job 加 `needs: gate` ＋ `if: needs.gate.outputs.is_sync != 'true'`。`run-probe-tests.py` 11 項行為測試 0 失敗。**AC 7 前半在 `pull_request` 事件下的結構性殘留已就地揭露並指派 Bolt 1 gate**（`ci.yml` concurrency 段的長註解） |
| **N:C-3** | Critical | Bolt 1 前更正檔名樣式 | **未被涵蓋（只改了一半）** | 已改：`U-9/nfr-requirements/performance-requirements.md:31` 與 `tech-stack-decisions.md:34`（2026-08-30T06:11:59Z 更正為 `.yml`）。**未改**：`U-9/functional-design/business-rules.md:25`（「檢 `.lock.yml` 而非 `.md`」）、`:29`（allowlist 仍寫 `aidlc-sync-*.md`／`.lock.yml`）、`business-logic-model.md:22`、`:83`。**functional-design 才是 U-9 的規則正本**，而更正只落在 nfr 層 ⇒ Bolt 4 照 business-rules.md 實作仍會指向不存在的檔案，唯一的機械化決定性閘門恆綠。詳見第 3 節 |
| **N:M-5／N:M-4(B)** | Major | Bolt 1（U-10b）／Bolt 3（U-8） | **未被涵蓋** | U-10b **完全未交付**：`.github/workflows/*.md` 與 `*.lock.yml` 對 `aidlc-sync` **零命中**，`git status` 顯示無任何 gh-aw 檔被改動。`gh aw compile` ＋ commit `.lock.yml` 這一步自然也不存在 |

#### 設計衝突（2 列）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| **N:C-2** | Critical | 需 ADR 或回退；Bolt 2／3 gate | **已被涵蓋（採回退）** | `aidlc-sync-reverse.yml:39-70` 用 32 行逐字引用 N:C-2、說明「本 intent 至今沒有為它開出 ADR」、並**回退**為 `group: aidlc-sync-reconcile-${{ github.repository }}`（與對帳同群）。`run-reverse-tests.py` 有靜態斷言鎖住該值，改動會紅燈。同段亦揭露「已核可計畫的查證 1 只盤點四項，N:C-2 與 N:M-5 都不在其中」——即任務簡述提到的第三次代價，實作端已自行更正 |
| **N:C-1(A)** | Critical | Bolt 2 gate | **已被涵蓋** | `reconcile-impl.yml:939` 逐字寫入報告：「`latency_samples` **刻意從缺**……在擁有權移轉（ADR-0015 §7）落地前本欄不填，且**不得以本輪執行耗時冒充**」。全檔對 `latency_samples` 只有這一處，無任何賦值 |

#### 其餘（code-generation 承接，8 條）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| **N:M-1** | Major | code-generation | **未被涵蓋，且已傳播進實作** | 錯誤的「26 次」被**逐字複製到交付物**：`aidlc-sync-reconcile.yml:63`「registry 目前 6 個 record，每個約 4 次 API 呼叫，**一輪上界 26 次**」。該數字正是 `reconcile_batch_size: "50"` 這個裁定的判斷基礎。應為 27（每日一次讀法）或 32（每 intent 一次讀法） |
| **N:M-2** | Major | code-generation | **未被涵蓋** | `U-7/nfr-requirements/tech-stack-decisions.md` 的缺口 M-1 段（`:9` 起）未見任何「兩條理由已被 ADR-0015 §13 代價段推翻」的更正註記 |
| **N:M-3** | Major | code-generation | **未被涵蓋** | 互斥仍在：`U-7/reliability-requirements.md:49`「一致率**是本機制唯一可長期追蹤的健康指標**」vs `U-7/tech-stack-decisions.md:28`「**但趨勢追蹤因此不可得**」 |
| **N:M-4** | Major | code-generation | **未被涵蓋（文件）** | `U-7/reliability-requirements.md` 全檔對「R-7.1 靜默失真」零命中（`:53` 只在來源清單提到 R-7.1）。**實作側已處理**：`reconcile-impl.yml:124-131` 有長註解並釘 `ref: ${{ inputs.trunk_ref }}` |
| N:M-6 | Major | code-generation | **已被涵蓋** | NFR-C1：`check-ci-yml.py:405-423` 第 8 項檢查 ＋ `ci-jobs-golden.json` 快照，鎖住四個既有 job 的 `name`／`runs-on`／`steps` 逐字不變。NFR-C2：三支 orchestration 測試各有斷言（`run-orchestration-tests.py:1229`、`run-reconcile-tests.py:1420-1421`、`run-reverse-tests.py:1494-1495`）。**實測**：`.github/workflows/*.yml` 的 21 個 `name:` 值全數唯一 |
| **N:M-1(B)** | Major | code-generation | **未被涵蓋** | `U-3/nfr-requirements/security-requirements.md:14` 仍寫「記錄落在**受管區塊**（U-2）與 workflow log」。**實測推翻**：`block.sh:277-285` 的 `mapped` 支（`BLOCK_STATUS` 非空）只渲染 Status ＋ 對照表列，**不渲染判定時間**（`LABEL_DECIDED_AT` 只在 else 支）。B:M-4 的重判確實沒傳到寫入點 |
| **N:M-2(B)** | Major | code-generation | **未被涵蓋（且已被交付物證實為假）** | `U-10b/security-requirements.md:14` 的補償控制寫「`ci.yml` 的 `repo-contract` job 在 push 到 `main`／`ut` 時仍會跑（U-10a 的 `paths-ignore` **同樣不阻止**合併後的 push 觸發）」。**實測不成立**：反向 PR 的寫入白名單只接受 `<record_path>/sync-state.json`（`reverse-impl.yml:559`、`record.sh` 的 `commit_and_push` 白名單），故合併回 `ut` 的 push **只改那一個檔**，恰好命中 `ci.yml` push 側的 `paths-ignore` glob ⇒ `ci.yml` 不會跑。殘餘風險低（`validate_repo_contract.py` 的禁止路徑檢查是 `git ls-files` 全域掃描，下一次 run 仍會抓），但**那句補償控制是錯的** |
| Minor ×6 | Minor | code-generation | **2 已涵蓋／3 未涵蓋／1 無法判定** | (a) `U-1` 四面向表被引文截斷 → **未涵蓋**（`U-1/security-requirements.md` 表列 `:11`，引文 `:13`，續表 `:14-16`）。(b) `U-3` 四項集合下的散文未隨 §8 重算 → **無法判定**（原登錄未指行號，該檔 `:14` 的 §8 指標已在，但「四項集合下的散文」定位不出唯一目標）。(c) `U-2` 的「兩處獨立佐證」實為同一個 commit → **未涵蓋**（`U-2/security-requirements.md:61` 仍寫「`sync-state.json` 的 `last_synced_at`……以及**該 commit 本身的時間戳**」——兩者在同一個 commit 裡，不獨立）。(d) `U-6` 標題「四項」而本文五項 → **未涵蓋**（`U-6/tech-stack-decisions.md:23` 仍為「承接 bash 的**四項**既有代價，本單元不新增第五項」）。(e) 5/25 檔對 `requirements.md` 零引用 → **已涵蓋（部分）**：實掃 42 份 `U-*/nfr-requirements/*.md` 得零引用 **4 份**（`U-2/nfr-requirements-questions.md`、`U-4/tech-stack-decisions.md`、`U-9/performance-requirements.md`、`U-9/reliability-requirements.md`），其中 2 份屬未交付的 U-9；分母與原登錄的 25 不同，無法逐一對應。(f) `U-7` SEC-2 揭露表未含 `ut HEAD SHA` → **未涵蓋**（`U-7/security-requirements.md:33-36` 仍為三列，無該欄；嚴重度實質為零——public repo 的 SHA 無敏感性） |

### 2.11 已於本輪關閉（4 條，複驗）

| 項目 | 判定 | 證據 |
| --- | --- | --- |
| U-1 Q2 的人工裁決紀錄矛盾 | **已被涵蓋** | `U-1/functional-design/functional-design-questions.md:58` 現為 `[Answer]: C`，`:60` 有完整的字母更正說明（2026-08-30T05:48:54Z） |
| B:M-4 ＋ B:M-5 | **已被涵蓋（但 B:M-4 的下游傳播失敗）** | B:M-5 指標已補（見 2.7）。B:M-4 的重判成立，**但 N:M-1(B) 顯示它沒傳到 U-3 的寫入點**——該登錄仍開著 |
| 送審前自檢的兩個真缺口 | **無法判定** | 原登錄未指出具體落點（只寫「U-2 SEC-2 白名單會擋掉 R-1.5 的告示、U-1 的 output 數」）；U-1 的 output 數確為 5（`U-1/domain-entities.md`、`map.sh` 五個 `emit`），該半可判定為已涵蓋；U-2 SEC-2 白名單那半定位不出唯一目標 |
| reviewer 複查四項未成立 | **不適用於本次核對** | 該條記的是「不成立的發現」，非待辦 |

### 2.12 `###` 級獨立登錄（3 條）

| 項目 | 嚴重度 | 落點 | 判定 | 證據或後果 |
| --- | --- | --- | --- | --- |
| B:M-1（已關閉節） | Major | code-generation | **已被涵蓋** | 見 2.5。`## R-6`／`## R-7` 已分開 |
| **CG:OPEN-1** | 需閘門裁決 | Bolt 1 gate | **未被涵蓋（依設計刻意保留）** | `aidlc-sync-map/action.yml:21-24` 仍保留 `intents_json` input 且註明「沒有一個 output 承載 binding……保留在介面上是為了不讓呼叫端在缺口補上後還要改簽章」；`map.sh` 五個 `emit` 中無 `binding`。裁決 (a)／(b) 尚未做出 |
| **CG:OPEN-2** | Minor | 已裁決不補 | **未被涵蓋（已知且已裁決）** | 實測 `validate_repo_contract.py` 解析後 `REQUIRED_TEXT['README.md']` = `('Cloud-360','AWS','GCP','Azure','draw.io','Mobile Web','Cloud Security Posture','human approval gate','MCP & Skill Management')`——**不含 `projects/16`**。`README.md:138-140` 的 `## Requirements Source` 段刪掉，contract 仍綠燈。與登錄的描述完全一致 |

---

## 3. 未被涵蓋的項目 —— 詳述

**26 個未被涵蓋的條目**按「會不會造成執行期後果」分層：3.1 有 3 項、3.2 有 5 項、3.3 的索引表含其餘 16 項（另有 2 項 —— `CG:OPEN-1`／`CG:OPEN-2` —— 性質為「已知且已指派閘門」，見 2.12 與第 5 節，不重複詳述）。**3 ＋ 5 ＋ 16 ＋ 2 = 26。**

**第 3.1 層是唯一會讓已核可 AC 在生產路徑上不可滿足的**。3.3 的索引表同時收錄第 4 節那 5 項「實作已涵蓋｜文件殘留」，因為對讀設計文件的人而言兩者的風險面相同——表內以判定欄區分。

### 3.1 執行期後果（3 項）

#### (1) A:M-4 後半 —— `unparseable ∩ reverse_rejected` 的 [US:S-6 AC 5] 告示永久靜默

**讓哪一條 AC 不可滿足**：[US:S-6 AC 5]（反向 PR 被拒後，受管區塊須載有一則記錄）。

**可達性推導**（逐步寫入路徑）：

1. 某 intent 已綁定、已有受管區塊（正常同步過）。
2. 協作者在看板上改了 Status → U-8 於次日開反向 PR → 該 PR 被關閉而未合併。
3. **在 U-6 下一輪之前**，該 record 的 `aidlc-state.md` 被改成解析不出必要欄位（例如 `Current Stage` 行被刪、`## Stage Progress` 區塊被移走）⇒ `map()` 回 `reason_code = unparseable`。
4. U-6 下一輪：`forward-impl.yml:455` 的 `case "$dec_reason_code" in unparseable|whitelisted)` 命中 ⇒ `:492 INTENT_OK=1; :493 return 0`。
5. **而 `notice_due` 的計算在 `:541`**——第 4 步已經 `return` 了，永遠算不到。
6. `last_synced_at` 不前進、`reverse_rejected` 集合每輪重新查詢仍含它 ⇒ 條件恆成立卻恆不被評估。**無紅燈、無通報、不進任何清單。**

第 3 步是否需要人為破壞？不必然——`map.sh` 的 `list_stages` 在 `## Stage Progress` 區塊零行 match（rc=5）或區塊不存在（rc=4）時都回 unparseable，而 record 目錄結構在 intent 生命週期中會變。

**與 R-3.0 的張力**：[req:FR-J3] 逐字要求「機制**不對其產生任何看板寫入**」，而告示的載體就是受管區塊（一次看板寫入）。所以這不是「補一行」能解的——**兩條已核可的規則在這個交集上直接衝突**，需要裁決哪一條優先，或定義第三條路徑（例如只在該交集下允許寫受管區塊而不寫 Status／自訂欄位）。

**建議落點**：**Bolt 1 gate**（U-6 於 Bolt 1 交付）。不是 code-generation ——它需要對兩條已核可規則的優先序做裁決。

#### (2) B:m-6 —— scope_note 進雜湊卻不在漂移三欄

**讓哪一條需求不可滿足**：[req:FR-F3]／U-2 的 R-1.2（`[S]` 與 `— SKIP` 的差別必須在受管區塊上看得見）——**在變更發生後**看不見。

**可達性**：`forward-impl.yml:536-539` 的漂移判定只比 `status`／`field_value`／`reason_code`。若一次 `--stage` jump 把某個**非當前** stage 標成 `[S]`、或 scope 重組改變某 stage 的 EXECUTE／SKIP，而當前 stage 的判定三欄不變 ⇒ `drift=0`、`notice_due=0` ⇒ `:550` 走 R-5.5 的不寫分支 ⇒ 受管區塊的「範圍註記」無限期停在舊值。

**為什麼沒有紅燈**：受管區塊與 `managed_block_hash` 兩端**同時**陳舊，U-8 的 R-1.1 比對相等 ⇒ 不開反向 PR。這是「一致地錯」，比「不一致」更難發現。

**建議落點**：**Bolt 1 gate**。修法二選一：(a) 把 `scope_note` 加進漂移比對（成本：`forward-impl.yml:536-539` 加一個條件 ＋ `SyncState` 加一欄 `last_scope_note`，需 U-4 schema 變更）；(b) 明白裁定「scope 變動不即時反映，等下一次判定變化時順帶更新」並寫進 R-5.2 的但書。**不裁決就是預設 (b) 而沒有人知道。**

#### (3) N:C-3 —— U-9 的檢查對象只在 nfr 層更正，functional-design 未更正

**讓哪一條 AC 不可滿足**：[US:S-10 AC 1–5]（U-9 的機械化決定性閘門），以及「改同步 workflow 的 PR 觸發 U-9」這條保證。

**可達性**：U-9 於 Bolt 4 實作時，實作者讀的是 `U-9/functional-design/business-rules.md` —— `:25` 逐字「**檢 `.lock.yml` 而非 `.md`**」、`:29` 的 allowlist 為 `aidlc-sync-*.md`／`.lock.yml`。而四支 workflow 已全數定案為**純 Actions `.yml`**（`aidlc-sync-forward.yml` 等，本次交付確認），`.lock.yml` **不存在** ⇒ 靜態檢查找不到對象 ⇒ 恆綠；`paths:` allowlist 也不會被 `.yml` 的變更命中 ⇒ 改同步 workflow 的 PR 不觸發 U-9。

**為什麼會漏**：更正註記（`U-9/tech-stack-decisions.md:34`）自己寫「同一個錯誤也出現在 `performance-requirements.md` 的觸發 allowlist，**一併更正**」——只列了兩個檔，沒有回頭掃 functional-design 的四處。這正是 `project.md` 的 `units-generation:260822-ug-L1`（按事實掃、不按改過的字串掃）的又一次實例。

**建議落點**：**Bolt 1 前**（原登錄的落點，理由是 allowlist 影響每一個 PR），落點檔為 `U-9/functional-design/business-rules.md:25`／`:29` 與 `business-logic-model.md:22`／`:83`。

### 3.2 契約／登錄後果（5 項）

| 項目 | 讓什麼落空 | 可達性 | 建議落點 |
| --- | --- | --- | --- |
| **A:M-9** | ADR-0015 §14 自己寫「確認人為 Bolt 1 的 gate」，而 `bolt-plan.md:65` 的 Bolt 1 DoD **沒有這一條** ⇒ 一個 blocking 項不在被檢查的清單上，gate 通過時沒有人會查它 | 確定發生（`bolt-plan.md` 全檔 `§14` 零命中） | **Bolt 1 gate**：在 `bolt-plan.md:65` 增列「ADR-0015 §14 的 `undecidable` 前綴已定案或已明確延後」 |
| **N:M-5／N:M-4(B)** | U-10b 未交付 ⇒ 反向 PR 仍會發動四支 gh-aw workflow；U-8 兩處以不存在的 `.lock.yml` 複驗 | 確定發生（gh-aw 檔零改動） | **Bolt 1（U-10b）**：交付物須含 `gh aw compile` ＋ commit `.lock.yml`；**Bolt 3（U-8）**：改複驗對象 |
| **N:M-2(B)** | `U-10b/security-requirements.md:14` 的補償控制是假的 ⇒ 下一個人會據此認為 contract 仍被驗 | 確定（反向 PR 只改 `sync-state.json`，恰好命中 U-10a 的 push glob） | **Bolt 1（U-10b）**：改寫該句，或把 `[aidlc-sync]` gate 的邏輯也套到合併後 push |
| **N:M-1** | 錯誤的「26 次」已**傳播進交付物**（`aidlc-sync-reconcile.yml:63`），而它是 `reconcile_batch_size: "50"` 的判斷基礎 | 確定 | **code-generation**（改註解即可，一行）；數字本身待 PRE-1 實測 C-T5 |
| **N:M-1(B)** | `U-3/security-requirements.md:14` 宣稱受管區塊承載「什麼時間」，而 `mapped` 支不含時間戳 ⇒ ADR-0006 audit-logging 的判定依據錯誤 | 確定（`block.sh:277-285`） | **code-generation** 或 **Bolt 1 gate**：改述為「`mapped` 支的時間由 workflow log 與 commit 時間戳承載」 |

### 3.3 文件一致性後果 —— 殘留文字索引（19 列／21 個條目）

這些不影響執行期行為，但**每一列都會誤導下一個讀設計文件動手的人**。C-7.2 是其中最危險的——它的四處殘留描述的正是一個已被 iteration 6 判為 Critical 的行為。

判定欄的兩種值：`未涵蓋` ＝ 該條目在第 2 節判為未被涵蓋；`實作已對` ＝ 第 4 節那 5 項「實作已涵蓋｜文件殘留」。

| 項目 | 判定 | 落點檔:行 | 殘留內容 |
| --- | --- | --- | --- |
| **C-7.2**（4 處） | 實作已對 | `U-6/business-logic-model.md:53`、`:66`、`U-3/business-rules.md:129`、`U-3/domain-entities.md:50` | 全數保留「`managed_block_hash` 維持原值、**其餘欄位照常回寫**」／「對應的**那一欄**維持原值」。實作已對，但**任何依這四處重寫或重審的人都會把 C-6.2 放回來** |
| A:M-3 | 實作已對 | `U-4/domain-entities.md:18`、`U-6/business-rules.md:227` | 已撤回的雜湊來源敘述 |
| A:M-2 | 實作已對 | `U-4/business-rules.md:38`、`:47` | 「推其排程觸發分支」；ADR「不裁定」 |
| B:m-3 | 實作已對 | `U-1/business-logic-model.md:47-52`、`:62` | 主流程圖與 parse 演算法無 `scope_note` 步驟 |
| B:M-3 | 實作已對 | `U-5/business-logic-model.md:82` | U-8 仍列為 `resolve_if_open` 的呼叫者（與同檔 `:142` 自相矛盾） |
| A:M-10 | 未涵蓋 | `U-6/business-rules.md:216` 與 `:227` | `render` 列重複兩次；Context 表切斷 R-7 表（腳本偵測 `224 → 227`） |
| A:m-7 | 未涵蓋 | `U-6/business-rules.md` R-5.11 | 假 `Aborted` 通報無時間界 |
| A:m-8 | 未涵蓋 | `U-6/business-rules.md:122-124` | R-5.12／R-5.13 排在 R-5.11 之前 |
| A:m-4 | 未涵蓋 | `U-7/business-logic-model.md:116` | 「一字未改」 |
| A:m-9 | 未涵蓋 | `U-7/business-logic-model.md:26` | 「SyncState（三欄 ＋ binding）」 |
| A:m-5 | 未涵蓋 | `U-4/business-rules.md:38→50` | 續表無表頭（至少一處） |
| B:m-4 | 未涵蓋 | `U-1/domain-entities.md:102` | 「有兩項」 |
| B:m-1（3 處中 2 處） | 未涵蓋 | `U-2/business-rules.md:36`、`U-2/domain-entities.md:109` | churn 敘述無分支限定 |
| B:m-2 | 未涵蓋 | `U-2/business-rules.md:14` | R-1.2 的主詞仍是 `Decision` |
| A:m-2／B:m-7 | 未涵蓋 | `ADR-0015:7` | `Amends:` 行的「以下原文」是截斷片段 |
| A:m-6 | 未涵蓋 | `bolt-plan.md:79` | §13 條目吞掉 Bolt 2 基線 DoD |
| m-7.1 | 未涵蓋 | `U-4/domain-entities.md:19` | `last_synced_at` 定義未隨 R-5.13 收斂 |
| N:M-2／N:M-3／N:M-4（3 個條目） | 未涵蓋 | `U-7/tech-stack-decisions.md` 缺口 M-1 段、`reliability-requirements.md:49` vs `tech-stack-decisions.md:28`、`reliability-requirements.md` 全檔 | 兩條理由被推翻未更正；一致率互斥；R-7.1 靜默失真缺席 |
| Minor ×6 之 (a)(c)(d)(f) | 未涵蓋 | `U-1/security-requirements.md:11-16`、`U-2/security-requirements.md:61`、`U-6/tech-stack-decisions.md:23`、`U-7/security-requirements.md:33-36` | 表被引文截斷；「兩處獨立佐證」實為同一 commit；「四項」vs 本文五項；SEC-2 揭露表缺 `ut HEAD SHA` |

**列數與條目數的關係**：19 列；其中 `N:M-2／N:M-3／N:M-4` 一列承載 3 個條目，其餘 18 列各 1 個 ⇒ **21 個條目**（16 個未涵蓋 ＋ 5 個實作已對），與 3 段開頭的 3 ＋ 5 ＋ 16 ＋ 2 = 26 相符。

### 3.4 無法判定（6 個子問題，對應 3 個條目 ＋ 3 個條目內部的次要不確定）

| 項目 | 卡在哪 |
| --- | --- |
| `open-items.md:38` 的「兩組的 m-8」 | 與 `:57` 的 `A:m-8` **同 id 不同內容**（前者是 ADR-0015 §13 的 `%s` 佔位符，實測已為 0；後者是表內序數倒置，仍在）。同一份登錄裡一個 id 指兩件事，只有人工能裁定 |
| iteration 6 的 Major 第 4 項 | 原文只寫「**等**」——**從未被具名**，無從查證。這是登錄本身的缺陷：一個被計入「Major ×4」的項目，沒有任何人知道它是什麼 |
| Minor ×6 之 (b)（`U-3` 四項集合下的散文） | 原登錄未給行號，`U-3/security-requirements.md` 中定位不出唯一目標 |
| Minor ×6 之 (e)（5/25 檔零引用） | 實掃 42 份 `U-*/nfr-requirements/*.md` 得零引用 4 份（含 2 份屬未交付的 U-9），**分母與原登錄的 25 不同**，無法逐一對應原登錄的那 5 份 |
| 「送審前自檢的兩個真缺口」之 U-2 SEC-2 白名單那半 | 原登錄未指落點；另一半（U-1 的 output 數）可判定為已涵蓋（五個 output，`map.sh` 五個 `emit`） |
| A:m-5 的第二處表格斷裂 | 偵測器只認「續表無分隔列」這一種形狀，只確認到一處（`U-4/business-rules.md:38→50`）。原登錄稱兩處，第二處未命中 |

---

## 4. 「實作已涵蓋、文件仍殘留」的 5 項（獨立列出的理由）

這一類在傳統的「已涵蓋／未涵蓋」二分下最容易被誤讀成「已完成」，但它們的風險方向不同：**執行期是對的，設計文件是錯的**，而下一個接手的人讀的是設計文件。

判為此類的 5 個條目：**A:M-3、A:M-2、B:m-3、B:M-3、C-7.2**。共同形狀是「code-generation 在寫程式時就地做對了、也在註解裡寫下理由，但沒有回頭改被 open item 逐字點名的那一行設計文字」。

另有兩項形狀相同但判定不同，一併提醒：**A:M-7**（判為已被涵蓋——`notify.sh:149` 依 Plan Approval 裁決 2 定為五碼，但 `U-5/domain-entities.md:13` 仍列四種）與 **N:M-4**（判為未被涵蓋——實作 `reconcile-impl.yml:124-131` 已釘 `ref`，但 `U-7/reliability-requirements.md` 全檔缺席）。

**C-7.2 是最危險的一個**：它的四處殘留描述的是一個已被 iteration 6 判為 Critical（C-6.2）的行為（`last_synced_at` 在 `write_body` 失敗時前進 ⇒ [US:S-6 AC 5] 永久靜默）。實作把它改對了，但四份設計檔仍逐字保留錯的版本。任何一次「照設計檔重寫／重審」都會把它放回來，而 open item 的落點寫的是「**Bolt 1 開工前**」——期限已過。

---

## 5. 建議 orchestrator 在 U-9／U-10b／`tcms-test-cases` 之前先處理的項目（按急迫性）

### 第 1 順位 —— 會讓已核可 AC 在生產路徑上不可滿足，且失效是靜默的

| # | 項目 | 為什麼現在處理 | 誰處理 |
| --- | --- | --- | --- |
| 1 | **N:C-3** —— U-9 的檢查對象與 allowlist 在 functional-design 未更正 | **U-9 就是下一個要做的單元**。實作者一打開 `business-rules.md:25` 就會照著 `.lock.yml` 寫，而那個檔案不存在 ⇒ 唯一的機械化決定性閘門恆綠。改四行的成本，vs 一整個單元做在錯誤前提上 | U-9 的 code-generation 開工前，先改 `U-9/functional-design/business-rules.md:25`／`:29` 與 `business-logic-model.md:22`／`:83`（標明「這是對齊 nfr 層 2026-08-30T06:11:59Z 更正的傳播，非新裁決」） |
| 2 | **A:M-4 後半** —— `unparseable ∩ reverse_rejected` 的告示永久靜默 | 兩條已核可規則（FR-J3「不做任何看板寫入」vs S-6 AC 5「受管區塊須載有告示」）在這個交集上**直接衝突**，不是實作細節。U-6 已交付，缺陷已在程式碼裡 | **Bolt 1 gate**（需人工裁決優先序）；`tcms-test-cases` 應把它列為「只能手動」桶的一個案例，且回歸案例的背景要寫明「既有自動化層為何沒抓到」——答案是 `forward-impl.yml` 在 `:493` 就 return 了，測試也照同一條路徑走 |
| 3 | **N:M-5／N:M-4(B)** —— U-10b 完全未交付 | **U-10b 就是下一個要做的單元**，且它是 Bolt 1 的一部分。交付物必須含 `gh aw compile` ＋ commit `.lock.yml`（GitHub 執行的是 lock），漏了則排除完全不生效且無紅燈 | U-10b 的 code-generation |
| 4 | **N:M-2(B)** —— U-10b 的補償控制在交付後的 `ci.yml` 下不成立 | 與第 3 項同一個單元、同一次改動。不改就是把一句已被實測推翻的話留在 security-requirements 裡當保證 | U-10b 的 code-generation（同一個 PR） |

### 第 2 順位 —— 會讓 gate 檢查不到該檢查的東西

| # | 項目 | 為什麼 | 誰處理 |
| --- | --- | --- | --- |
| 5 | **A:M-9** —— ADR-0015 §14 未登錄 Bolt 1 DoD | Bolt 1 的 gate 快到了。§14 自己指名「確認人為 Bolt 1 的 gate」，而 DoD 沒有這一條 ⇒ gate 會在沒有人檢查它的情況下通過 | Bolt 1 gate 之前，補進 `bolt-plan.md:65` |
| 6 | **B:m-6** —— scope_note 不在漂移三欄 | 落點是 Bolt 1 gate，而 U-6 已交付。需要的是裁決（加進比對 vs 明白接受延遲），不是實作 | Bolt 1 gate |
| 7 | **CG:OPEN-1** —— `ParsedRecord.binding` 的來源上游兩處衝突 | 落點是 Bolt 1 gate。`intents_json` input 目前無消費者，裁決 (a) 移除 input 或 (b) 指定鍵名 ＋ 補第六個 output | Bolt 1 gate |
| 8 | **C-7.2 的四處文件殘留** | 期限（「Bolt 1 開工前」）**已過**，且殘留描述的是一個已判 Critical 的行為。`tcms-test-cases` 若照設計檔寫測案，會寫出一個斷言錯誤行為的案例 | `tcms-test-cases` 開工前，或併入下一次觸及 U-3／U-6 設計檔的動作 |

### 第 3 順位 —— `tcms-test-cases` 特別要注意的

| # | 項目 | 對 `tcms-test-cases` 的意義 |
| --- | --- | --- |
| 9 | **N:M-1** 的「26 次」已進交付物 | `aidlc-sync-reconcile.yml:63` 的數字錯了，而 `reconcile_batch_size: "50"` 的合理性論證建立在它上面。測案若要驗證批次上限，不能引用這個數字 |
| 10 | **N:M-1(B)** —— `mapped` 支不含時間戳 | 若照 `U-3/security-requirements.md:14` 寫一個「受管區塊可回答『什麼時間』」的測案，**它在 `mapped` 支必然失敗**（`block.sh:277-285`）。這正是撰寫標準要求的「目的要指向真會失敗的行為」的反例 |
| 11 | **A:M-4／B:m-6／N:C-3** 三項的共同性質 | 三者都是**靜默失效**（不紅燈、不通報、不進清單）。依 `project.md ## Mandated` 必做 1，它們應被分到「只能手動」桶並寫成回歸案例，而非丟給「待自動化」——因為要自動化它們，得先做完第 1／2 順位的裁決 |
| 12 | **A:m-8／A:M-10／A:m-5** 等純結構項 | 不需要測案，但若 `tcms-test-cases` 的追溯指向 `U-6/business-rules.md` 的規則編號，**要注意 R-5.11／R-5.12／R-5.13 的表列順序與編號順序不一致**，逐行引用時容易指錯 |

### 第 4 順位 —— 登錄本身的兩個結構性缺陷（建議一併修）

| # | 問題 | 建議 |
| --- | --- | --- |
| 13 | `open-items.md:38` 的 `m-8` 與 `:57` 的 `A:m-8` **同 id 不同內容** | 在 `:38` 加註「此處的 m-8 指 ADR-0015 §13 的 `%s` 佔位符，與 `:57` 表列的 A:m-8（序數倒置）**不是同一項**」 |
| 14 | iteration 6 的 Major 第 4 項只寫「**等**」，從未具名 | 這是一個被計入總數卻無人知道內容的項目。若原始 reviewer 輸出仍在（`U-*/functional-design/business-logic-model.md` 的 Review 段），回去補具名；補不出來就明白記為「已遺失」，不要讓它以「Major ×4」的形式繼續冒充已登錄 |
| 15 | `open-items.md:116` 的「其餘 20 項」實為 23 項（六張表 28 列 − Bolt 開工前 5 項） | 依 `project.md` 的 `delivery-planning:dp-L1`（可算的數字先算再寫）更正 |

---

## 6. 本次核對的執行證據

| 動作 | 結果 |
| --- | --- |
| `python3 .github/actions/aidlc-sync-map/run-fixtures.py` | 2707 斷言／0 失敗 |
| `python3 .github/actions/aidlc-sync-block/run-fixtures.py` | 550 斷言／0 失敗 |
| `python3 .github/actions/aidlc-sync-board/run-stub-tests.py` | 31 tests／173 checks／0 failures |
| `python3 .github/actions/aidlc-sync-record/run-stub-tests.py` | 31 tests／231 checks／0 failures |
| `python3 .github/actions/aidlc-sync-notify/run-stub-tests.py` | 35 tests／381 checks／0 failures |
| `python3 .github/actions/aidlc-sync-forward/run-orchestration-tests.py` | 39 tests／145 checks／0 failures |
| `python3 .github/actions/aidlc-sync-reconcile/run-reconcile-tests.py` | 37 tests／200 checks／0 failures |
| `python3 .github/actions/aidlc-sync-reverse/run-reverse-tests.py` | 38 tests／237 checks／0 failures |
| `python3 .github/actions/aidlc-sync-ci-guard/run-probe-tests.py` | 11 項行為測試／0 失敗 |
| `validate_repo_contract.py` 的 `REQUIRED_TEXT` 以 AST 解析 | `README.md` 鍵唯一，九個關鍵字，不含 `projects/16` |
| `.github/workflows/*.yml` 的 `name:` 唯一性 | 21 個值全數唯一（NFR-C2 成立） |
| 表格斷裂偵測（自寫腳本，續表無分隔列） | `U-4/business-rules.md 38→50`、`U-6/business-rules.md 224→227` |

**未執行**：任何真實 API 呼叫、任何 `git commit`／`push`、任何 live 測試（`run-live-tests.py` 需憑證，未跑）。

**唯讀確認**：本次只新增本檔一個檔案；`git status` 在核對前後對實作檔與上游 artifact 的差異集合相同。
