# Phase Check — Inception → Construction

<!-- 產出於 delivery-planning（Inception 2.9）Step 5 · Record: 260920-orchestration-brain -->

## 判定：**PASS**

Inception 階段所有執行過的站，其 `traceability.json` **無 `GAP`、無 `ORPHAN`、
無 invalid target、無遺漏的 upstream id**。階段轉換不被阻擋。

---

## 逐檔結果

| 站 | 列數 | 狀態分佈 | `GAP`／`ORPHAN` | upstream_ids 未涵蓋 | coverage 多出 | 空白 target |
|---|---|---|---|---|---|---|
| `user-stories` | 70 | 61 `OK`／8 `Deferred`／1 `N/A` | 無 | 無 | 無 | 無 |
| `domain-design` | 20 | 20 `OK` | 無 | 無 | 無 | 無 |
| `units-generation` | 20 | 20 `OK` | 無 | 無 | 無 | 無 |

`contract-design`（2.8）**不產出 `traceability.json`**——它擁有的是正式契約，不是需求
覆蓋，故依 stage 檔規定不納入本次階段邊界檢查。

---

## 8 筆 `Deferred` 與 1 筆 `N/A` 的逐項處置

`Deferred` 與 `N/A` 是 `verification.md` 定義的**合法狀態**，不是未解決的發現——
但兩者都要求非空的 target 或理由，且本檢查已逐筆確認其 target 非空。逐項如下：

| id | 狀態 | 指向哪裡 | 該站會不會被 skip |
|---|---|---|---|
| `NFR1` | Deferred | `build-and-test`（3.6）——意圖識別準確率 ≥ 80% 的量測機制 | **ALWAYS，不會被 skip** |
| `NFR2` | Deferred | `build-and-test`（3.6）——脈絡保留率 ≥ 95% 的量測腳本 | **ALWAYS** |
| `NFR3` | Deferred | `build-and-test`（3.6）——首字 P50 的伺服器端計時 | **ALWAYS** |
| `NFR5` | Deferred | `contract-design`（2.8）——WS 訊息型別契約與 CI 一致性檢查 | **已執行並完成**（`K-02`），此項實質已交付 |
| `NFR6` | Deferred | `build-and-test`（3.6）——真實 PostgreSQL 的 CI job | **ALWAYS** |
| `NFR8` | Deferred | `infrastructure-design`（3.4）——Redis 連線設定與同批更新 | CONDITIONAL；但其內容已被 `bolt-plan.md` 的 **B1 完成判準**與 `external-dependency-map.md` 的 **E5** 承接 |
| `NFR10` | Deferred | `nfr-requirements`（3.2）——路由層模型定案 | CONDITIONAL，**無自然承接站**；見下方風險 |
| `NFR11` | Deferred | `build-and-test`（3.6）——頁面切換次數與基準比較 | **ALWAYS** |
| `NFR9` | **N/A** | 本 intent 不建自身 LLM 花費的計量機制（`[F13]`=A，上限由 OpenRouter 後台承載） | **已核可的範圍決定，不是缺口** |

**八筆 `Deferred` 中有五筆指向 `build-and-test`（ALWAYS，不會被 skip）**，一筆（`NFR5`）
已在 `contract-design` 實質交付，一筆（`NFR8`）已被本站的 Bolt 計畫承接。

---

## 一項必須隨階段轉換一起帶走的風險

**`NFR10`（路由層模型的可替換性）的落點沒有自然承接站。**

它指派 `nfr-requirements`（3.2，**CONDITIONAL**），而 `nfr-design`（3.3）的執行條件
依賴 `nfr-requirements` 已執行——**兩站會一併 skip**。同一條風險鏈上還有
`requirements.md` 的 `OQ-4`（路由層模型定案）與 `OQ-10`（路由層能否產出可比較的信心值），
兩者**必須一併決定，不得分開處理**。

這不只是一個未定的參數。`[RA:FR1.6]` 逐字寫：「若實作出一個不輸出信心值的路由層，
`FR1.3` 會**靜默永不觸發**，而文件上看起來已解決」。

**處置**：`bolt-plan.md` 已把它列為 **B5 的阻塞性進入條件**，並明寫「該站若被 skip，
須重新提交使用者裁決，**不得由實作者當場決定**」。`team-allocation.md` 亦把它列為
三類人工介入點之一。

**但這個處置沒有機械保證**——它依賴屆時判定 skip 的執行者記得重新提交。此事如實記載
於此，不宣稱已解決。

---

## 本次檢查沒有涵蓋的東西

階段邊界檢查驗的是**需求覆蓋的追溯完整性**，不是設計的正確性。下列事項**不在本檢查
範圍內**，但會隨階段轉換一起進入 Construction，逐項記載於 `contract-summary.md`
的 Open Questions 與 `bolt-plan.md` 的各 Bolt 進入條件：

- **`OQ-N3`（Critical）**：記憶功能沒有寫入端。四個單元（`U5`／`U8`／`U9`／`U15`）
  在它定案前做出來是惰性的，`FR4.1`／`FR4.5`／`FR4.6`／`FR4.7` 失去機制——
  **而 CI 會全綠**。已排入 **B1** 定案。
- **`OQ-N4`**：`BrainSession` 只有一個 `messageHistory`，撐不起 `[DD:E6]` 自己要求的
  「兩段」對話。必須在 **B4** 開工前有答案。
- **`OQ-13`**：90 天清除 workflow 如何取得資料庫連線。是 `U9` 的單元層級阻塞，
  落點與轉移目標**皆為 CONDITIONAL**。**B9 因此是條件式的**。
- `OQ-1`、`OQ-3`、`OQ-5`、`OQ-8`、`OQ-N1`、`OQ-N2`、`DG-1`、`DG-2`、`DG-3`、`H-3`
  ——各自的落點見 `contract-summary.md`。

**追溯是完整的，設計不是。** 這兩件事在本檢查裡要分開講：前者 PASS，後者有 15 條
已登錄、已指派落點的未決事項隨階段轉換一起進入 Construction。
