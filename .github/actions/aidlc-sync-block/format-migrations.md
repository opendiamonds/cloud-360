# 受管區塊格式遷移登錄表

<!-- U-2-managed-block · [Q1=C] 定案的互鎖所讀的檔案（R-4.2／R-4.3／R-4.5 三道讀本檔；
     R-4.1 讀 golden 快照、R-4.4 讀 serialize-golden.txt）。2026-08-30T12:49:35Z 由三道擴為五道。
     機械解析者：run-fixtures.py 的 test_r4_2_* 與 test_r4_3_*。 -->

`block.sh` 的 `FORMAT_VERSION` 與受管區塊的格式是同一份契約。ADR-A6 把「**設計一個機制
（而非流程紀律）使格式變更與重新基準化不能脫鉤**」指派給 U-2，[Q1=C] 的定案是三道 CI
互鎖，本檔是其中兩道的資料來源：

| # | 檢查 | 觸發紅燈的情形 | 實作 |
| --- | --- | --- | --- |
| R-4.1 | golden fixture 快照與當前渲染器輸出逐位元一致 | 改了 `render` 而沒更新快照 | `run-fixtures.py` 的 `test_r4_1_golden_snapshots_byte_identical` |
| R-4.2 | `FORMAT_VERSION` 等於本表**最後一列**的版本 | 版本與本表脫節（例如手改了 `FORMAT_VERSION` 而未加列，或反之） | `run-fixtures.py` 的 `test_r4_2_format_version_matches_last_migration_row` |
| R-4.3 | 本表最後一列含**非空**的重新基準化說明與執行方式 | bump 了版本但沒加登錄 | `run-fixtures.py` 的 `test_r4_3_last_row_has_rebaseline_note` |

## 這個機制的天花板（誠實記載，不要試圖修掉）

五道互鎖保證作者**無法「忘記」**重新基準化，**不保證他「做了」**——本表可以被寫成
空殼：加一列、把說明欄填滿、但不真的去執行基準化。這是 [Q1=C] 選項本文即已載明的
取捨，不是缺陷。

唯一能保證「做了」的形狀是 [Q1=B]（格式指紋 ＋ 錯配時自動重新基準化），但它會把
ADR-A6 的「單一 PR 一次性遷移」改成「逐 item 惰性遷移」，屬對已核可 ADR 的**實質變更**。
兩者的取捨已在 Q1 呈現並由人裁定，實作端不重開。

## 改格式時要做的五件事

1. 改 `block.sh` 的格式常數或 `render_block`／`parse_v<n>`。
2. `FORMAT_VERSION` 加一；`KNOWN_VERSIONS` 保留舊版本，並為舊版本留下對應的
   `parse_v<n>`（遷移期間看板上新舊區塊必然並存，舊解析器不能刪）。
3. 重新產生 `fixtures/golden-*.md`（R-4.1）。
4. 在下表**新增一列**，說明要基準化什麼、以及**怎麼執行**（R-4.2／R-4.3）。

## 登錄表

<!-- 機械解析規則：**只讀 `## 登錄表` 這個標題之後**以 `|` 開頭的資料列（檔案上半部
     那張 R-4 對照表也以 `|` 開頭，不得被誤讀）。欄序為
     format_version | 生效日期 | golden_fingerprint | 變更內容 | 重新基準化說明 | 執行方式。
     最後一列即當前版本。新版本一律 append 在最後。 -->

| format_version | 生效日期 | golden_fingerprint | 變更內容 | 重新基準化說明 | 執行方式 |
| --- | --- | --- | --- | --- | --- |
| 1 | 2026-08-30 | `ca944c9478b2ca5a4795cdaf9586bd1da47b4a8b0eee36f7a84f102aee60a058` | 首版。含版本標記、Status／對照表列（或未寫入原因／判定時間）、範圍註記、`rejection_notice` 告示（ADR-0015 §12）、兩段固定說明。 | 首次上線，既有受管 item 數 0，無需基準化。ADR-0015 §12 把 `rejection_notice` 進 `Block` 定為一次 `format_version` bump，而「bump」在此沒有可重新基準化的對象——起始版本即含該欄位，等價於在**零成本時點**完成那次 bump（該節的論證本來就以「既有 item 是 0，這是最便宜的時點」為理由）。 | 不需執行任何遷移動作。首次正向同步會為每個 item 寫入 v=1 的區塊，並由 U-6 回讀取得 `managed_block_hash`（ADR-0015 §10），基準自然建立。 |
