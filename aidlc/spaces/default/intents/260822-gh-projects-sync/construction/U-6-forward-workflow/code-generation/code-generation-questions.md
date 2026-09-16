# Code Generation Questions — U-6 正向同步 workflow

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## Q1（阻塞）— `undecidable` 的 `write_field` 行為

**Question**: R-5.10 (a) 逐字要求 `undecidable` 照走 `write_field`，但三項查證合起來使該字面不可照做：①ADR-0015 §14 明令「在它落地之前，`undecidable` 的自訂欄位行為未定義——實作不得自行猜一個前綴」，確認人 Bolt 1 gate；②U-1 已交付的 `map.sh:416-424` 正確遵守，對 `undecidable` 回傳**空字串**；③U-3 的 `board.sh:792` 對空值**無任何守衛**，最終 `-f text="$value"` 直送 GraphQL ⇒ 照字面實作會把自訂欄位**寫成空字串、清掉原有內容**。清空是一種可觀察行為，選它就是在猜。可達性已驗：`undecidable` 由 `map.sh:395` 產生，有 fixture `r3-7-undecidable.md` 與通過的測試，是真實路徑。

- **A. `undecidable` 跳過 `write_field`** — 其餘（`render`／`write_body`／回讀／回寫）照走，欄位維持原值。最貼近「不猜」；代價是 R-5.10 (a) 的字面被收窄，需標出並指派 Bolt 1 gate 追認
- B. 照字面走 `write_field`（寫空值＝清空）— 忠於規則字面，但清空是沒人核可過的行為，與 §14 實質牴觸
- C. 當場定案第五個前綴 — §14 說字面待實作期與 `format_version` bump 一併定，但會連帶觸發重新基準化，範圍遠大於本單元

[Answer]: A. 跳過 write_field <!-- 2026-09-05T11:23:44Z, via AskUserQuestion -->

## Q2 — 本 stage 是否動用真實 Projects API

**Question**: 憑證（`opendiamonds`，帶 `project`＋`repo` scope）與測試看板 #23 皆已就緒。本 stage 是否動用真實 API 取得執行期證據？

- **A. 不動用，留 Bolt 1** — 行為測試以 stub 取代五支 composite action，斷言呼叫序列與回寫欄位集合。U-6 的規則絕大多數是編排邏輯（分流、順序、四種失敗的不同回寫），stub 測得到且更完整——真實 API 反而構造不出四種失敗
- B. 動用，對 #23 跑一次端到端 — 較早取得 GraphQL 層證據，但會在 #23 留下 item 與可能的 issue，且測不到四種失敗分支

[Answer]: A. 不動用，留 Bolt 1 <!-- 2026-09-05T11:23:44Z, via AskUserQuestion -->

### Q2 修訂（2026-09-05T11:36:50Z）— 使用者推翻原答案

**新裁決**：**動用真實 API，但寫入對象只有測試看板 #23，不得碰正式看板 #16。** 使用者原文：「用測試看板 #23，不要碰 #16」。

原答案 A（不動用）**作廢**。這不是選項 B 的原樣採用——B 當時寫的是「對 #23 跑一次端到端」，新裁決同時附帶一條**明確的隔離約束**（#16 不得被碰），該約束在原選項中沒有出現，故記為修訂而非改選。

**落地形狀沿用姊妹單元的既有實作，不自創**（查證後確認 U-3 已把此模式實作過）：

| 項目 | 既有樣板 |
| --- | --- |
| 檔案分兩支 | stub（`run-orchestration-tests.py`，離線、主力）＋ live（`run-live-tests.py`）。U-3／U-4／U-5 皆此形狀 |
| 進場防呆 | `board.sh:94-95` 的 SEC-3 逐字：「隔離靠 Config 的 Project 編號，**不靠權限**……進場斷言 `AIDLC_PROJECT_NUMBER != 16`」；實作見 `aidlc-sync-board/run-live-tests.py:248-250`，不符即 `exit 4` |
| 預設值 | `os.environ.get("AIDLC_PROJECT_NUMBER", "23")` |
| 測畢還原 | U-3 記下 issue #538 的原始 Status 與 body 並還原，且先清前次殘留 |
| push 隔離 | 不得對 `ut`／`main` 發出真實 push（U-4 `run-live-tests.py:19-20`） |

**分工的理由**（要交給 gate 看的）：R-5.12 的四種失敗分支與 R-3.0 閘門**只有 stub 驗得到**（真實 API 構造不出那些失敗）；R-5.4 的雜湊等價性（ADR-0015 §10 點名最危險的失敗模式）**只有 live 驗得到**。兩支不可互相取代。

## Plan Approval

**Question**: `code-generation-plan.md` 已就緒（14 步驟；含開工前四項查證，其中查證 2 發現 R-4.3 的前提已被 ADR-0016 推翻——與 U-10a 的 `github.actor` 同一形狀，依 `functional-design:c22` 只修理由不改決定；查證 3 即 Q1 的阻塞）。測試策略吸取 U-10a 的教訓，以**行為測試為主**（stub 五支 action、斷言呼叫序列與回寫欄位集合），結構斷言為輔。是否核可此計畫並開始產生程式碼？

- **Approve Plan** — 依計畫開始產生程式碼
- Request Changes — 修訂計畫（請說明要改哪裡）

[Answer]: Approve Plan <!-- 2026-09-05T11:24:47Z, via AskUserQuestion -->
