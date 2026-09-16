# Functional Design — U-6 正向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| New data models | ✅ | 反向 PR 的識別標記（跨三個單元的契約）完全未定義 |
| Complex business logic | ✅ | registry 驅動的選取分流、兩道自我排除防線、`reverse_pending` 的取得 |
| Business rules need design | ✅ | 見下方兩項裁定 |
| Skip if simple logic changes | ❌ | 新 workflow |

**判定：EXECUTE**（`kind: service` → 三份產出）。

## 本站承接的上游指派

**缺口 F-4**（於 U-1 的 functional-design 標出並指派本單元）：「誰負責算出 `reverse_pending`？」

[Q2=A] 於 U-1 定案 `Config.reverse_pending` 由 workflow 層在逐 record 迴圈**之前**組出，來源是開啟中的反向同步 PR 的變更路徑（U-8 的偵測機制）。但**沒有任何上游 artifact 把這件事指派給任何單元**——U-8 擁有的是**產生**反向 PR，**讀取**它是正向同步（本單元）每一輪要做的事，而本單元的擁有清單裡沒有它。

**本站在此正式承接 F-4。** 兩項待決事項見下。

---

## 本站裁定（**未經人工提問**）

> **這兩項原本要提問，使用者中止提問並指示繼續。以下為本站依既有事實與已核可決定所作的裁定，理由完整記載以便覆核。它們不是人工裁決，不得被讀成使用者答過。**

### D-1. 反向同步 PR 的識別標記：**分支名前綴 ＋ label 並用**

**這是一個沒人擁有的跨單元契約**：U-8 產生它、U-6（本單元）要找到它算 `reverse_pending`、U-10b 要把它排除在高成本 workflow 之外。[ad:services.md] 的 S-C 只說「開 PR」，成本控制那列明寫「具體手段留 construction」。

**裁定：分支一律 `aidlc-sync/reverse/<date>`，且掛 label `aidlc-sync-reverse`。**

理由是兩者在技術上**不對稱**，各自解決不同的問題：

| 需求 | 分支名前綴 | label |
| --- | --- | --- |
| U-10b 的排除 | ❌ **不成立，見下方更正**（原寫「`branches-ignore` 讓 run 根本不被建立」） | ❌ **GitHub 沒有 `labels-ignore`**；label 只能用 job 層的 `if:`，而那仍會啟動 workflow、仍佔一個 run |
| U-6 的查找 | ⚠️ 需列出全部開啟中 PR 再本地比對前綴 | ✅ `gh pr list --label` 直接可用 |
| 人一眼分辨 | ⚠️ 要看分支名 | ✅ |

> **更正（2026-08-29T15:21:33Z，reviewer iteration 1 Major）。** 先前此處寫「單用 label 會讓 U-10b 做不到真正的排除——那是本項最強的約束，因此分支名前綴是**必要的**」。該論證的唯一支撐（`branches-ignore` 可排除反向 PR）**經查證不成立**：對 `pull_request` 事件，`branches`／`branches-ignore` 過濾的是 **base** 分支，而反向 PR 的 base 一律是 `ut`。U-10b 實際採用 `paths-ignore`。
>
> **裁定不改，理由降級**（`project.md` 的 `functional-design:c22`）：上表顯示 label 在「U-6 的查找」與「人一眼分辨」兩欄都優於分支前綴，而分支前綴原本唯一的強論證已消失。**分支前綴保留為「代價可接受的附加」**——它仍有兩項真實價值（人一眼分辨、`git branch` glob 可批次操作），且 U-8 已據以命名。**但它不再是「必要」，任何下游不得再以「U-10b 需要它」為由主張其必要性。**

[Answer]: 本站裁定，非人工裁決（理由已於本輪更正，裁定維持）  <!-- 2026-08-29T15:21:33Z（讀自 date -u） -->

**代價（記明）**：兩個標記要同時維護，且三個單元依賴它們——改慢一個就會斷掉。**且分支命名不符 `team.md` 的 `<uploader>/<type>/<slug>`**，需在規則層記明這是機器分支的例外（該規則本身已明文不適用於「自動產生的分支」，如 `dependabot/*`，本項屬同類）。

### D-2. `reverse_pending` 取不到時：**整輪中止，紅燈通報**（fail-closed）

**裁定**：查詢開啟中反向 PR 失敗時，**不寫任何 Status**，整輪以 `ExternalError` 結束並通報。

理由：

1. `reverse_pending` 的用途就是「哪些 intent **不該**被覆寫」。算不出來 = 不知道該不該覆寫，而 [req:FR-C1] 的精神逐字是「拿不準時不寫」。
2. 選取是 **registry 驅動的漂移判定**（[ad:services.md] S-A），下一輪事件或隔日對帳會自然補上——**中止不造成遺漏，只造成延遲**。
3. **fail-open（視為空集合）正是我在 F-4 指派時明寫不得做的事**：暫停覆寫會靜默失效，協作者在看板上的改動被輾回去而無人察覺，[US:S-6] 的保護失效且不留痕跡。
4. 被否決的「視為全部 suppressed」雖然也是 fail-closed，但它**把一個真實故障偽裝成正常判斷**——受管區塊會記下「因反向 PR 而暫停」，而實際上根本沒有反向 PR。紀錄會說謊，而本設計的核心價值正是「看板不說謊」。

**代價**：一次短暫的 API 故障會讓整輪同步停擺並拉一次紅燈。這是刻意的——紅燈的定義就是「需要人看」，而「機制無法判斷該不該覆寫」確實需要人知道。

## Q5（iteration 3 新增）：`write_status` 的 `expected` 從哪裡取

**背景**：`write_status(binding, expected: ItemState, desired: Status)` 內部「必先回讀」並與 `expected` 比對，不符即回 `Aborted` 並開 issue（[ad:component-methods.md] §C-3、[req:FR-C1]）。前兩輪各選了一邊、各壞一邊，reviewer iteration 3 判為 Critical（C-1）：

- **iteration 2 之前取自 `SyncState` 三欄** → U-7 補平看板時無法回寫 `SyncState`（[ad:components.md] 給 reconcile 的元件鏈沒有 C-4）⇒ 三欄過期 ⇒ **每次正常補平都製造一則假通報**。
- **iteration 2 的 R-5.7 改取當下 `read_item`** → `expected` 就是幾百毫秒前剛讀的值 ⇒ 比對恆真 ⇒ **`Aborted` 不可達**。三份已核可上游直接反證：`stories.md:237`、`requirements.md:73`（FR-C3「後到者的回讀比對會偵測到前者已寫入的結果」）、`requirements.md:71`（FR-C1）。連帶 `ReconcileReport.aborted`、[US:S-9 AC 2] 的第三份清單、本單元錯誤表的 `Aborted` 列全部變死碼。

**選項**：

A. **`expected` 回到 `SyncState` 三欄，並讓 U-7 也回寫 `SyncState`**：給 reconcile 的元件鏈補上 C-4，U-7 補平看板後一併更新三欄。看得到的效果：守門恢復（真正的並行寫入會被偵測），過期問題從源頭消失，語意乾淨——誰寫看板誰就負責記錄自己寫了什麼。代價：reconcile 每日會多一次 commit+push；`deploy.yml` 只在 PR merge 進 `ut` 或手動觸發，故**不觸發部署**；會觸發的 `ci.yml` 已有 U-10a 為 `sync-state.json` 設計的 `paths-ignore` 可沿用。

B. **U-6 在 `actual != expected` 時多一層「已被補平」判定**：若 `actual == desired` 則不算 `Aborted`、照常更新三欄。看得到的效果：零上游變更、成本最低。代價：U-7 補平為 X' 後 record 又變成 X''，三者互異 ⇒ 仍是假 `Aborted`。

C. **U-7 不補平，只報告**：過期問題根本不存在。代價：直接推翻已核可的 Bolt 2 信心假說（「落差會被每天發現**並補平**」），[US:S-9] 與 FR-D 的補平要求都要回頭改。

[Answer]: A  <!-- 2026-08-30T00:57:28Z（讀自 date -u）· 人工裁決，非本站裁定 -->

**承載**：`components.md` 的 reconcile 元件鏈修訂由 **ADR-0015 §13** 承載（該檔為已核可上游，標出不逕改）。本單元的 R-5.7／R-5.8 依此改寫；U-7 增設回寫 `SyncState` 的規則。
