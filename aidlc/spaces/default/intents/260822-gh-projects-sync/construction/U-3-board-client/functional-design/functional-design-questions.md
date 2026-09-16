# Functional Design — U-3 看板客戶端

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-3-board-client · kind: library -->

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| New data models | ✅ | `ItemState` 只給了欄位名，未給取得路徑；`binding` 與 Projects v2 的 item id 之間的關係完全未定義 |
| Complex business logic | ✅ | 七個方法（含 ADR-0015 §11 的 `write_body`）、回讀比對、首建重複防護、欄位 id 解析、分頁 |
| Business rules need design | ✅ | 回讀與寫入之間的競態、`ensure_field` 三種失敗前提的區分 |
| Skip if simple logic changes | ❌ | 本 repo **無 Projects v2 先例**，全新 |

**判定：EXECUTE**（`kind: library` → 三份產出）。本單元複雜度 **L**，與 U-7 並列為十二個單元中僅有的兩個 L 級（先前誤寫為「唯一」，已依 [ug:unit-of-work.md] 更正）。

## 已由上游定案、本站不重問

| 事項 | 出處 |
| --- | --- |
| **上游原有六個**方法的簽章與各自的錯誤處理（`read_item`／`create_item`／`write_status`／`write_field`／`ensure_field`／`read_issue_state`） | [ad:component-methods.md] §C-3 |
| **`write_body` 的簽章與錯誤處理**（第七個方法，本站未重問——單一可行解） | **ADR-0015 §11** |
| `write_status` **必先回讀**；`actual != expected` → 回 `Aborted`，不送出寫入、不開 issue | 同上（開 issue 是 C-5 的職責） |
| `create_item` 先檢查 record 是否已有綁定編號；有則不建、回既有值 | 同上（[US:S-1 AC 6]） |
| `write_field` 失敗**不影響** Status 寫入 | 同上（[US:S-5 AC 2] 的「欄位失敗不連坐」） |
| 本元件**不得**提供推 commit 到 `ut` 或改 record 目錄以外檔案的方法 | 同上 |
| [US:S-10 AC 5] 的第二個例子在本設計下**無機制可產生 403**，已列 PRE-1-a | ADR-A2、[ug:unit-of-work.md] U-3 實作註記 |
| 驗證對**獨立測試 Project** 進行 | ADR-A3、[Q4=A] |

---

## 問題

### Q1. `read_item` 怎麼從 `binding`（issue 編號）找到 Projects v2 的 item？

[ad:component-methods.md] 說「Projects v2 的 item 列舉與欄位 id 查詢都需分頁……但 `read_item` 的介面刻意不暴露分頁——呼叫端只給 binding」。**介面定了，取得路徑沒定**，而三條路的成本差很多。

A. **從 issue 反查它的 project items**（GraphQL 的 `Issue.projectItems`）：一次查詢就從 issue 拿到它所屬的 project item，**完全不需要列舉整個 Project**。看得到的效果：單次同步的成本與 Project 的 item 總數無關（O(1) 而非 O(n)），也不需要在 `read_item` 內處理分頁——上游「介面不暴露分頁」的設計因此變成自然成立而非刻意隱藏。代價：**本站無法實地驗證這條路徑存在且可用**（repo 無 Projects v2 先例，且本站不呼叫外部 API）。它必須被加進 PRE-1 的實測清單，否則是一個沒查證過的前提。

B. **列舉整個 Project 的 items 並在記憶體建索引**：分頁拉完全部 item，用 issue 編號建 `issue → item_id` 對照。看得到的效果：只依賴「列舉 items」這個上游已經確認需要的能力，不引入新的查詢形狀；且對帳（C-7）本來就要列舉全部，兩者可共用。代價：每次同步都拉全部 item，成本隨 Project 成長；[req:FR-I4] 的「框架單次操作次數上限」是已知未定值（PRE-1 第 2 項），列舉可能撞上它。

C. **把 item id 快取進 `sync-state.json`**：首建時記下 item id，之後直接用。看得到的效果：最省呼叫。代價：**多一份會漂移的物化狀態**——`team.md` 的「單一真實來源」要求新增副本的同一個 PR 必須有鎖住一致性的測試；而 item 被人為刪除再重建時 id 會變，快取失效的偵測與修復是額外機制。且 `sync-state.json` 是 U-4 的地盤，本單元不該擴充它的 schema。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T11:56:42Z（讀自 date -u）· 從 issue 反查 projectItems；須加進 PRE-1 實測 -->

### Q2. 回讀與寫入之間的競態怎麼處置？

`write_status` 的契約是「必先回讀；`actual != expected` → 回 `Aborted`」。但 Projects v2 **沒有 compare-and-swap**——回讀與寫入是兩次獨立呼叫，中間存在一個視窗：協作者正好在這期間改了看板，機制會用一個已經過期的比對結果送出寫入，把人家的改動蓋掉。

這正是 [US:S-6] 要防的事（「我在看板上表達的判斷會被送到人面前決定，而不是被機器直接輾掉」），只是發生在一個更窄的時間窗裡。

A. **接受視窗，由每日對帳與反向同步承接**：不做額外處理，明文記載視窗存在。看得到的效果：不引入額外呼叫；被蓋掉的改動會在下一輪反向同步被偵測（受管區塊雜湊比對）並開 PR 送人決定——**[US:S-6] 的保護仍然成立，只是慢一輪**。〔**就地標註（iteration 3 M-1，2026-08-30T00:05:00Z）：粗體這一句在 reviewer iteration 1 後已證實不成立**——反向同步結構上抓不到這個視窗。依 `project.md` 的 `functional-design:c22`，選項本文不改寫（決定仍正確，被推翻的是理由），故在此標註而非編輯；正確敘述見 `business-rules.md` 的 R-2.4 段與 ADR-0015 §2。〕代價：那一輪之間看板上顯示的是機制的值而非人的值；且這個視窗**不會有任何測試涵蓋**（需要精準的時序才能重現）。

B. **寫入後再回讀一次驗證**：寫完立刻讀回，若讀到的不是自己寫的值，代表期間有人動過，記為 `Aborted` 並開 issue。看得到的效果：視窗仍在，但**至少會被偵測到**而不是靜默通過；偵測到時的處置與回讀不符同路徑。代價：每次寫入多一次 API 呼叫（成本 ×1.5），而 [req:FR-I4] 的上限值未知；且它偵測到的時候**改動已經被蓋掉了**——只是知道發生過。

C. **以受管區塊雜湊作為樂觀鎖**：寫入前回讀時一併取得受管區塊的雜湊，寫入時把「預期雜湊」帶進同一次 mutation 的前置條件。看得到的效果：真正的 compare-and-swap 語意。代價：**Projects v2 的 mutation 不支援條件式更新**——這條路在平台層不成立，列出僅為完整性（與 application-design 對「單選欄位加預設值」的處理同形）。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T11:56:42Z（讀自 date -u）· 接受視窗，由反向同步承接 -->
