# Code Generation Plan — U-7 對帳 workflow 與編排器

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service
     Created: 2026-09-05T15:14:57Z（讀自 date -u） -->

## 交付物與落點

| 檔案 | 內容 |
| --- | --- |
| `.github/workflows/aidlc-sync-reconcile-impl.yml` | `on: workflow_call`，全參數化（ADR-A10）。編排器 C-7 的實體 |
| `.github/workflows/aidlc-sync-reconcile.yml` | 薄外層：`on: schedule` ＋ `workflow_dispatch` ＋ concurrency |
| `.github/actions/aidlc-sync-reconcile/run-reconcile-tests.py` | 行為測試（stub，離線）——**主力** |

複雜度 **L**（目前最大；U-6 為 M）。不新增依賴——五支 composite action 已交付，介面沿用 U-6 已核對的那一份。

## 開工前查證（唯讀，結果供題幹與實作引用）

### 查證 1 — **U-6 的 schema 變更會讓 R-6 依字面實作時失效（Q1 的由來）**

R-6.1／R-6.5 逐字要求回寫 `last_status`／`last_field_value`／`last_reason_code`，語意寫明「**記錄「機制上次寫進看板的值」**」。

**但 U-6 已把該語意拆出去**（其 reviewer iteration 2 Critical 的修法）：`last_status` 改記「上一輪的**判定**」，新增 `last_written_status` 記「上次真的寫進看板的值」，而 **U-6 的 `expected` 讀的是後者**。

照字面實作 ⇒ 補平後不寫 `last_written_status` ⇒ U-6 下一輪 `expected` 仍是舊值 ⇒ **`Aborted` ＋ 假通報**——**正是 R-6 這一整群存在的唯一理由**（其背景段逐字：「補平愈成功、假通報愈多」）。

**人工裁決 Q1=A：兩欄都寫。** 補平時本單元確實寫了看板，故兩種語意在那一刻相同。**這擴充了 R-6.1／R-6.5 的字面**，須標出並指派 Bolt 1 gate 追認。

**這個缺口兩輪 reviewer 都沒抓到**——U-6 的審查只看單一單元，跨單元後果落在審查範圍外。記為本 intent 的一項方法論發現。

### 查證 2 — G-1 已由 functional-design 關閉

`domain-entities.md:17` 已補入 `undecidable: [intent_id]`，並在 `:21-28` 寫明它與 `unparseable` 不可互換（前者「讀得出來但訊號不落在對照表」、後者「必要區塊缺失」）。**清單數五→六、欄位數 +1**。`unit-of-work.md` 的 U-7 列仍是舊敘述（其「已知上游契約缺口」欄），屬**已被下游關閉的歷史記載**，不需回改。

### 查證 3 — 三個既有 cron（實測 `grep` 全 workflow）

| workflow | cron |
| --- | --- |
| `daily-digest` | `0 23 * * 1-5` |
| `agentics-maintenance` | `37 0 * * *` |
| `release-watch` | `39 16 * * 1` |

本單元的排程須避開這三個時間點（R-5，屬**建置期**檢查，可被靜態斷言鎖住）。

### 查證 4 — `expected` 的取法與 U-6 **刻意相反**

R-6.7：補平時 `write_status` 的 `expected` 取自**本輪剛做的 `read_item`**，不取自 `SyncState`。這與 U-6 的 R-5.7 方向相反，**不是矛盾**——兩者守的是不同的問題（U-6：我上次寫入之後有沒有別人動過；本單元：我讀到當下狀態到寫入之間有沒有人插隊，是單輪內的樂觀鎖）。實作**不得**把兩者「對齊」。

## 計畫步驟

- [ ] **Step 1 — impl 骨架與參數**：`on: workflow_call`，inputs 沿用 U-6 那一組 ＋ `reconcile_batch_size`；secret 為同步 token。**追溯**：ADR-A10、ADR-0016 §1
- [ ] **Step 2 — R-1 群：六份清單的成員身分**（G-1 後為六份，非五份）。**追溯**：R-1、`domain-entities.md`
- [ ] **Step 3 — R-2 群：一致率**。分母＝已綁定 − 有未處理反向紀錄 − `Parked` 非空（**維持上游兩類排除**，ADR-A5）。**追溯**：R-2、完成判準第一條
- [ ] **Step 4 — R-3 群：處理量上限**（`reconcile_batch_size`）。**追溯**：R-3
- [ ] **Step 5 — R-8 群：`read_issue_state` 的承接**——「issue 已關閉而 Status 不為 `Done`」的偵測。**追溯**：R-8、完成判準第四條
- [ ] **Step 6 — R-6 群：補平後回寫（含 Q1=A 的兩欄）**。三條路徑各不相同：<br>• R-6.1 補平路徑：寫四欄 ＋ **`last_written_status`（Q1=A）**，**不動 `managed_block_hash`**（R-6.2）<br>• R-6.5 修復路徑：三欄 ＋ **`last_written_status`（Q1=A）** ＋ **`managed_block_hash` 與 `last_synced_at`**（R-6.8，R-6.2 的唯一例外）<br>• R-6.3 未補平：不回寫（「跳過」與「補平失敗」兩種）<br>R-6.6：兩者共用**同一次** `commit_and_push`。**追溯**：R-6.1–R-6.8
- [ ] **Step 7 — R-6.7：`expected` 取自本輪 `read_item`**，與 U-6 相反（查證 4）。**追溯**：R-6.7
- [ ] **Step 8 — R-4 群：單一 intent 失敗不中止整輪**。**追溯**：R-4
- [ ] **Step 9 — R-7 群：排程觸發的分支落點**（Q6=A 定案）。**追溯**：R-7
- [ ] **Step 10 — 薄外層**：`schedule` 的 cron 避開查證 3 的三個時間點；`workflow_dispatch`；concurrency 自成一組（與 U-6 可並行，NFR-P3）。**追溯**：R-5、R-1.4（U-6）
- [ ] **Step 11 — 補平成功不使 workflow 紅燈**（[US:S-7 AC 5]）。**追溯**：實作註記
- [ ] **Step 12 — 測試**（見下節）
- [ ] **Step 13 — 突變驗證**（見下節）
- [ ] **Step 14 — `code-summary.md`**（orchestrator 執筆）

## 測試策略（**吸取 U-6 兩輪的教訓**）

U-6 在同一個 stage 被打回兩輪，第二輪的兩項發現**都是第一輪修正引入的**，且其中一項是「**測試用錯計畫鍵名、根本沒在測**」。三條可執行的紀律因此寫進本單元：

1. **行為測試為主**——本單元幾乎全是編排邏輯（六份清單的成員身分、三條回寫路徑各寫哪些欄、上限、失敗不中止）。stub 取代五支 action，斷言**呼叫序列**與**每次回寫的欄位集合**。
2. **每條測試都要有「前提斷言」**——確認該測試要製造的情境**真的發生了**（例：測「補平失敗不回寫」時，先斷言補平確實失敗）。U-6 的 Major #2 就是少了這一條，讓其餘斷言在空前提上恆真通過。**計畫鍵名一律用 `"exit"`，stub 不認 `"rc"`。**
3. **多輪測試**——U-7 的 R-6.5 修復路徑本質上是跨輪的（U-6 留下不一致 → U-7 修復 → U-6 下一輪應恢復正常）。**必須有一條把 U-6 與 U-7 串起來的多輪測試**，否則 Q1=A 的正確性沒有任何東西守著。U-6 的 `test_multi_round_suppressed_converges` 是可沿用的形狀。

**必測清單**：
- R-6 的**三條回寫路徑各自的欄位集合**（補平／修復／不回寫）——差異就是「哪幾欄」，只有行為測試分得出來
- **Q1=A 的跨單元串接**：U-6 留下 `last_written_status` 過期 → U-7 修復 → 斷言 `last_written_status` **確實被寫**
- R-2 一致率的**兩類排除**（分母正確性）
- R-5 的 cron 不碰撞（靜態斷言，可從 YAML 直接讀三個既有值比對）
- 補平成功**不紅燈**

**真實 API 不動用**（沿用 U-6 的 Q2 決定）；若後續需要 live，寫入對象只有 **#23**，SEC-3 守衛沿用 U-6／U-3 已修正的整數正規化形式。

## 突變驗證（Step 13 的必打點）

至少涵蓋：R-6 三條路徑的欄位集合各改一項、**Q1=A 的 `last_written_status` 拿掉**、一致率分母少扣一類、cron 改成碰撞值、補平成功改成紅燈、上限失效。**每條突變都要確認它讓「對應的那一條」測試紅，而不是讓別條紅**——U-6 的 M18 就是打中了別條而誤以為有效。
