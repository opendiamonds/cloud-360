# Domain Entities — U-8 反向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## R-1.1 的比對基準：`managed_block_hash`

本單元的 R-1.1 拿「`sync-state.json` 記錄的雜湊」與看板現況比對。該欄位為 **`SyncState.managed_block_hash`**（schema 由 U-4 的 `domain-entities.md` 宣告，本單元不新增）。

**它的三個角色，先前只有兩個到位**（reviewer iteration 1 Critical）：

| 角色 | 誰 |
| --- | --- |
| 產生 | U-3 讀看板時，由 **U-2**（C-6 `managed-block`）的 `parse` ＋ `content_hash` 算進 `ItemState`。**先前誤標為「U-6」**——同一單元的 `business-rules.md` R-4c 已正確標為 C-6，兩處不一致（reviewer iteration 2 Major，2026-08-29T16:20:29Z） |
| 儲存 | U-4（`write_sync_state`） |
| **寫入** | **先前無人** → 現由 **U-6 的 R-5.4** 承接：看板寫入成功後**再呼叫一次 `read_item`**，取其回傳 `ItemState` 的 `managed_block_hash` 欄位回寫 |
| 讀取 | **本單元**（R-1.1） |

> **「寫入」列的雜湊來源已更正（送審前自檢，2026-08-29T23:42:35Z）。** 先前寫「把剛渲染並寫進看板那個 `Block` 的 `content_hash` 一併回寫」——那是 R-5.4 的**舊版**寫法，已於 2026-08-29T16:19:47Z 因 reviewer iteration 2 的 Critical 被撤回（型別不成立：`render` 回 `string` 而 `content_hash` 吃 `Block`；更要緊的是等價性）。
>
> **這一處尤其不能留舊說法**：本單元是該雜湊的**讀取端**，R-1.1 拿它當「有沒有人改過看板」的比對基準。等價性不變式（U-6 記錄的值與本單元日後 `read_item → parse → content_hash` 算出的值必須逐位元組相等）正是由「兩端走同一條回讀路徑」在構造上保證的——若本檔仍宣稱寫入端走的是 render 捷徑，讀本檔的人會據此實作出一條與 U-6 不同的路徑，而該不變式失效的後果是**每天為每個受管 intent 各開一則反向 PR**（[ad:decisions.md] ADR-A6 點名的最危險失效模式）。該不變式已登錄於 **ADR-0015 §10**。

**沒有寫者時本單元會怎麼壞**：儲存值恆為 `null`，與看板現況永遠不同 ⇒ 本單元每輪判定「有人改過」⇒ **為每個已綁定 intent 各開一則反向 PR，每天一次**。這不是漏一層保護，是機制自己製造垃圾。

**U-7 的補平不影響本欄位**：reconcile 的元件集合（[ad:components.md]）不含 C-6，只寫 Status 欄位而不重寫受管區塊，故區塊雜湊不變。詳見 U-6 的 R-5 群。

## `pending_reverse`（缺口 N-1 的落點）

[req:FR-G2] 要求反向同步「只寫入**同步專用檔案**」但未指名該檔。**裁定為 `<record>/sync-state.json` 的新欄位**（E-1）：

| 欄位 | 型別 | 語意 |
| --- | --- | --- |
| `pending_reverse.observed_status` | `Status` | 人在看板上改成的值 |
| `pending_reverse.observed_at` | ISO 8601 | 偵測到該變更的時刻 |
| `pending_reverse` 整體 | 物件 \| `null` | `null` = 無未處理的反向紀錄 |

**它記的是「人做了什麼」，不是「機制該做什麼」**——後者由 PR 的合併／關閉決定（[req:FR-G3]：PR 關閉或合併後恢復覆寫）。

**已由 U-4 承接**：`pending_reverse` 現列於 U-4 `domain-entities.md` 的 `sync-state.json` schema 表，依 [Q2=A] 的相容規則（只增不改）演進，且刻意在 `schema_version` 1 就存在（代價是 Bolt 1、2 期間有一個讀得到卻沒人寫的欄位，換得不必為它做一次版本演進）。**先前此處寫「指派 U-4」，但 U-4 早已接住——措辭於送審前自檢更正，2026-08-29T23:42:35Z：兄弟單元之間的指派若已落地卻仍寫成待辦，讀的人會去找一個不存在的缺口。確認人維持 Bolt 3 的 gate**——U-4 在 Bolt 1、U-8 在 Bolt 3，這是**跨 Bolt 的 schema 依賴**（見 `functional-design-questions.md` 的 E-1 警示）。

## 反向 PR 的識別標記（承接 U-6 的 D-1）

| 元素 | 值 | 本單元的責任 |
| --- | --- | --- |
| 分支 | `aidlc-sync/reverse/<intent_id>-<date>` | **產生時設定** |
| label | `aidlc-sync-reverse` | **開 PR 時掛上** |
| base | `ut` | [req:FR-G1]：不得直接推 `ut` |

**分支名含 `<intent_id>`** 是 E-2（一個 intent 一個 PR）的直接後果——它讓分支本身就標示了對象，且多個同日的反向 PR 不會撞名。

> **三個單元依賴這組標記**（U-8 產生、U-6 讀、U-10b 排除），且**它們之間沒有 DAG 邊**。這條契約只存在於文件裡，改動任一處都必須三處同步。U-6 的 `domain-entities.md` 已記載同一件事。

## 本單元不新增其他型別

看板現況由 U-3 的 `ItemState` 提供、受管區塊雜湊由 U-2 的 `content_hash` 產生、判定由 U-1 的 `map()` 產出。**本單元是編排與 PR 生命週期，不是資料模型。**

## 與上游的對應

[req:FR-G1]／[FR-G2]／[FR-G3] 與 C-N1／C-N3 引自 `requirements.md`；S-C 的生命週期與寫入邊界引自 [ad:services.md]；`ItemState` 引自 U-3 的 `domain-entities.md`、`content_hash` 引自 U-2、`sync-state.json` 的 schema 與相容規則引自 U-4 的 `domain-entities.md`；D-1 的標記契約引自 U-6 的 `domain-entities.md`；over-suppression 的風險記載引自 [ug:unit-of-work.md] 的 U-8 與 [ad:decisions.md] 的 CAP-11 補評估；[US:S-6] 引自 `stories.md`；元件分層引自 [ad:components.md]。
