# Domain Entities — U-3 看板客戶端

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-3-board-client · kind: library -->

## `ItemState`

[ad:component-methods.md] 給了欄位名 `{ status, field_value, managed_block_hash, issue_number, issue_state }`，本檔補語意與取得路徑。

| 欄位 | 值域 | 語意與取得 |
| --- | --- | --- |
| `status` | `Status` \| `null` | 看板上該 item 的 Status 欄位**現值**。`null` 代表欄位未設值（不是「決定不寫」——那是 `Decision` 的語意，兩者不可混同） |
| `field_value` | 字串 \| `null` | 自訂欄位現值。`null` 與空字串的區分在此**有意義**：[Q6=A] 定「自訂欄位為空的 item 不由本機制維護」 |
| `managed_block_hash` | sha256 \| `null` | 由 issue body 經 U-2 的 `parse` ＋ `content_hash` 得出；`parse` 回 `null` 時此欄為 `null`（該 item 不受管） |
| `issue_number` | 整數 | 即 `binding` |
| `issue_state` | `"open"` \| `"closed"` | [US:S-9 AC 5] 的 issue 開關偵測 |

**`managed_block_hash` 不是本元件算的**——它由 U-2 的兩個純函式產生，本元件只負責把 issue body 取回來並轉交。這個分工必須寫明：若本元件自己算雜湊，U-2 的格式知識就會有第二份物化，違反 `team.md` 的「單一真實來源」。

## `binding` 與 Projects v2 item 的關係（[Q1=A] 定案）

| 概念 | 是什麼 | 誰持有 |
| --- | --- | --- |
| `binding` | issue 編號（整數） | record 目錄（U-4 寫入與讀取） |
| Projects v2 item id | 看板上那張卡的 node id | **不落地任何地方**——每次由 issue 反查 |

[Q1=A] 定案以 GraphQL 的 `Issue.projectItems` 從 issue 反查它所屬的 project item，**不列舉整個 Project**。三個直接後果：

1. 單次同步的成本與 Project 的 item 總數**無關**。
2. `read_item` 的介面不暴露分頁（[ad:component-methods.md] 的既有設計）因此**自然成立**，不是刻意隱藏了一個分頁迴圈。
3. item id **不需要被快取**，因此 `sync-state.json` 的 schema 不需擴充——那是 U-4 的地盤，本單元不碰。

> **這條路徑本站未實測**（repo 無 Projects v2 先例，本站不呼叫外部 API）。[Q1=A] 的選項本文已載明此代價：**它必須被加進 PRE-1 的實測清單**。見 `business-rules.md` R-1.0。

## 需要分頁的地方（縮到最小，但不是零）

[Q1=A] 消掉了 `read_item` 的分頁，但**沒有消掉全部**：

| 操作 | 是否需分頁 | 說明 |
| --- | --- | --- |
| `read_item` | **否** | [Q1=A] 的直接效果 |
| `ensure_field` / 欄位 id 解析 | **是** | 需列舉 Project 的欄位定義。規模小（欄位數而非 item 數），但仍需處理 |
| C-7 對帳的 item 列舉 | **是** | 不在本單元——那是 U-7 |

## 錯誤型別

| 型別 | 何時 | 呼叫端的處置 |
| --- | --- | --- |
| `ExternalError { http_status }` | API 呼叫失敗 | **紅燈 ＋ 通報**（[ad:services.md] 明列的兩種紅燈之一） |
| `Aborted { actual, expected }` | 回讀不符 | **不紅燈**——[req:FR-C1] 的主動中止，屬機制的正常判斷 |
| `Failed { http_status, message }` | `write_field` **或 `write_body`** 失敗 | **不影響 Status 寫入**（[US:S-5 AC 2] 的不連坐）。`write_body` 失敗時該輪受管區塊未更新，呼叫端依 U-6 的 R-5.12 **維持 `managed_block_hash` 原值、其餘欄位照常回寫**（2026-08-30T02:47:00Z（依檔案 mtime 重建；原填 09:55:00Z 為未經 `date -u` 的編造值，已更正） 隨 R-5.12 由「全有全無」改為「逐欄」而同步；原補上 `write_body` 於 2026-08-30T01:31:09Z，reviewer iteration 4 Group B M-4） |
| `CannotCreate` | `ensure_field` 三種失敗前提之一 | 交 C-5 通報「需人工建立欄位」 |

四者在 [ad:component-methods.md] 已定義，本檔只補「呼叫端的處置」一欄，其來源是 [ad:services.md] 的失敗語意表。

## 與上游的對應

七個方法（含 ADR-0015 §11 增設的 `write_body`）的簽章、錯誤處理與權限邊界引自 [ad:component-methods.md] §C-3；元件職責與分層引自 [ad:components.md]；紅燈／不紅燈的語意引自 [ad:services.md]；`Decision` 與 `Block` 的型別引自 U-1／U-2 的同名檔案；FR-C1／FR-A1／FR-A2／FR-F2 與 NFR-I4 引自 `requirements.md`；單元邊界、完成判準與「無 Projects v2 先例」引自 [ug:unit-of-work.md] 的 U-3；承接的 AC 引自 [ug:unit-of-work-story-map.md]（S-3 AC 1、2 與 S-5 AC 2）；獨立測試 Project 的決定引自 [ad:decisions.md] ADR-A3。
