# Functional Design — U-7 對帳 workflow（問題與裁定）

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## CONDITIONAL 適用性判定

| 條款 | 適用 | 理由 |
| --- | --- | --- |
| New data models | ✅ | `ReconcileReport` 在本站被補入新欄位 `undecidable`（缺口 G-1） |
| Complex business logic | ✅ | 一致率的分母／分子定義、兩類排除、批次上限與「今天沒處理到」的可辨識性 |
| Business rules need design | ✅ | 六份清單的成員身分互斥性、`undecidable` 與 `unparseable` 為何不能互相頂替 |
| Skip if simple logic changes | ❌ | 不適用——本單元是新建的排程 workflow |

> **這個判定曾經有落空的風險，值得寫下來。** G-1 由 units-generation 指派給 `functional-design`，而該 stage 是 **CONDITIONAL 且 per-unit**——本單元這一輪若被判「無新資料模型」而 skip，G-1 的修補會連帶被跳過且無人察覺。這正是 `project.md` 的 `units-generation:260822-ug-L2` 要求「指派 CONDITIONAL stage 時必須註明可能被 skip 的風險」的實例。

## 本站裁定（**未經人工提問**）

**授權來源**：使用者在本 session 中止一次 AskUserQuestion 並輸入「continue」，指示不再逐題提問、由 conductor 自行判斷。**以下各項均非人工裁決。**

### G-1. `ReconcileReport` 補入 `undecidable: [intent_id]`

**這不是本站發明的需求，是 units-generation 標出並指派本站的缺口。** [US:S-2 AC 4] 要求對帳報告有「無法判定」清單，而 [ad:component-methods.md] §C-7 的 `ReconcileReport` 只有 `unparseable`。

**為何不能用 `unparseable` 頂替**：兩者的 `reason_code` 不同，指向的處置也不同——`unparseable` 是 record 讀不懂（要修 record），`undecidable` 是訊號不落在對照表任一列（要修對照表或補判定）。合併會讓「該修哪裡」在報告上消失。

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T15:00:03Z（讀自 date -u） -->

### R-3.4. 超出批次上限而未處理的 intent 必須可被辨識

**問題**：[req:FR-D3] 的批次上限之下，「今天沒處理到」與「今天處理了且一致」在報告上長得一樣。

**裁定**：報告須讓兩者可分辨（`deferred: [intent_id]` 欄位或等價形式）。**本站不裁定具體形式**——它取決於 PRE-1 第 2 項實測 C-T5 之後，批次上限是否真的會被觸發；但把交界寫下來，不讓它變成沒人知道的預設。

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T15:00:03Z（讀自 date -u） -->

## 送審前自檢（`project.md ## Mandated` 的六項）

| # | 項目 | 結果 |
| --- | --- | --- |
| 1 | 可達性 | 本單元無「偵測 X 狀態」型規則。`undecidable` 是分類結果而非待偵測狀態，其可達性由 U-1 的對照表非總函式性保證 |
| 2 | 狀態欄位三問 | 本單元**不持有跨輪狀態**——`ReconcileReport` 每輪重新產生，無誰清的問題 |
| 3 | 引用逐字核對 | `ReconcileReport` 欄位、兩類排除、C-7 簽章均已開檔核對 |
| 4 | 檔案集合一致性 | **本檔即為此項的產物**——自檢發現本單元缺此慣例檔 |
| 5 | 跨檔傳播 | `undecidable` 在本單元三檔均已一致（清單表、資料流圖、邊界情形表） |
| 6 | 數字重算 | 報告的清單欄位數：原五份 ＋ `undecidable` ＝ **六份**（已實數）。注意與 [US:S-9 AC 2] 的「三份**具名**清單」是不同的量，不可混用 |

## 與上游的對應

`reconcile` 的契約與 `ReconcileReport` 引自 [ad:component-methods.md] §C-7；兩類排除與 `aborted` 引自 [ad:decisions.md] ADR-A5；[req:FR-D1]～[FR-D4] 引自 `requirements.md`；[US:S-2 AC 4] 與 [US:S-9 AC 2] 引自 `stories.md`；缺口 G-1 的指派與「CONDITIONAL 可能被 skip」的風險註記引自 [ug:unit-of-work.md] 與 `project.md` 的 `units-generation:260822-ug-L2`；C-T5 與 PRE-1 引自 `delivery-planning/`。

## Q6（iteration 4 新增）：排程觸發的分支落點

**背景**：iteration 4 Group A 的 M-1 推翻了 lead 先前的 blocking 宣稱——`commit_and_push` 的「只推觸發分支」是**呼叫方式的描述、不是方法的內建限制**（U-4 `business-rules.md:49` 已定案，也正是 U-8 推自建 `aidlc-sync/reverse/*` 分支合法的前提）。所以推送落點從來就有。

**真正的問題**是 GitHub 的 `schedule` **只在預設分支觸發**，而本 repo 的預設分支經 `git symbolic-ref refs/remotes/origin/HEAD` 實測為 **`main`**。這帶來一個 reviewer 指出、lead 先前沒想到的**反向風險**：本單元會讀到 `main` 上的 record，而 `main` 落後於整合主幹 `ut` ⇒ **對帳會拿過期的 record 去比看板**，一致率與補平判定全部失真。

**選項**：

A. **`actions/checkout` 明訂 `ref: ut`**：workflow 定義仍由預設分支讀取（GitHub 的硬限制，無法繞過），但讀寫的 record 全部是 `ut` 的，推送也推到從 `ut` 分叉的自建分支（比照 U-8）。與 `main` 的關係只剩「從它讀 YAML」。代價：需在規則層寫死 `ref: ut` 並加一條斷言，否則 `actions/checkout` 的預設行為會靜默讀到 `main`。

B. **把預設分支改成 `ut`**：從根本上讓 schedule 在 `ut` 觸發。代價最大且超出本 intent：會動到 PR 預設 base、branch protection、`ci.yml`／`deploy.yml` 的觸發條件、以及所有現有 gh-aw workflow 的排程基準，需別開 ADR。

C. **不用 `schedule`，改外部觸發**（`repository_dispatch`／`workflow_dispatch`）：可指定 ref，從頭到尾不碰 `main`。代價：引入一個 repo 外的排程來源（新的外部依賴與憑證），而 `external-dependency-map.md` 的 E-1〜E-4 目前不含它。

[Answer]: A  <!-- 2026-08-30T01:31:09Z（讀自 date -u）· 人工裁決；使用者原話「不應該在main上跑」 -->

**承載**：`components.md` 的 reconcile 元件鏈修訂與本項的分支落點由 **ADR-0015 §13** 承載。**同樣適用於 U-8**（反向同步亦為 `schedule` 觸發，同一個硬限制）。
