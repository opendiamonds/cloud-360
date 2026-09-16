# Stage Memory — Requirements Analysis

> 本 stage 執行期間的觀察日誌。四個標準 H2，新條目 append 到既有標題下。

## Interpretations

- 2026-08-17T00:30:00Z — bugfix scope 的 Minimal depth 解讀為「六個完整性維度仍逐一評估，但只對有實際不確定性的維度出題」。本 bug 的技術脈絡（比對基準）是唯一真正的未知，其餘五個維度（功能、非功能、使用者情境、業務脈絡、品質屬性）由 issue 內容與 `org.md` 的 bugfix 測試底線即可涵蓋，故只出兩題。
- 2026-08-17T00:30:30Z — 「移除 `team.md` 的落差記載」與該檔標頭「Edit at the gate, not directly」的張力，解讀為：該限制針對**規則的新增與修改**（政策變更），而本次移除的是一條**在修正後不再為真的事實記載**（事實更正）。兩者性質不同，故不需回頭走 practices-discovery。判斷依據已寫進 `requirements.md` 的引言框，供後續覆核。

## Deviations
- 2026-08-18T00:10:00Z — reviewer（aidlc-product-lead-agent）第一輪判 NOT-READY，1 Critical / 3 Major / 2 Minor 全數採納修正。**C-1 是本站最有價值的發現**：初版 requirements 的 NFR-1（不得改 `ci.yml`）與 DoD（測試須防缺陷靜默復發）互相拉扯，而 CI 唯一的測試探索是 `backend` job 的 `unittest discover -s tests`（只撿 `backend/tests/`）——一份放在 `scripts/tests/` 的測試會字面滿足 DoD 卻永不被執行，**與本 bug 的失敗形狀完全相同**。修法：新增 FR-8～FR-10 與 AC-6，明確指定落點與 CI 執行路徑。

- 2026-08-17T00:31:00Z — stage 檔 Step 7 說「PROACTIVE: Always generate clarifying questions unless requirements are exceptionally clear」。本站只出 2 題而非更多，因為出題前的唯讀查證（7 條 Sources）已把多數潛在問題轉為已知事實 —— 例如「要不要改 CI 的 fetch-depth」在 S-3、S-5 確認全域掃描可行後即不再是開放問題。**查證消除問題比出題詢問更有價值**。

## Tradeoffs
- 2026-08-18T00:40:00Z — reviewer 第二輪判 READY，但點出兩處「修訂後未同步衍生引用」的殘留，兩處都已修：(1) FR-7 只點名 `team.md` 段落的**收尾句**（「這兩項…」），漏了**開頭句**（「現有**兩條**規則…」）——刪掉一條 bullet 後兩句的複數指涉同時失效，是同型失誤；只有 AC-5 的「通篇重讀無內部矛盾」勉強兜住，但實作者照 FR-7 字面做事會漏掉。(2) `questions.md` Q1 選項 B 仍寫著「淺 clone 是 CI 效能的**刻意設定**」——這正是 Minor-1 點名的無來源斷言，`requirements.md` 的 NFR-1 已改、支援文件沒跟上，且與同檔 S-3（只說「預設為 1」）自相矛盾。**兩者都是本 intent 反覆記載的失敗形狀本身的重演**：改了主產出卻沒追到所有衍生落點。
- 2026-08-18T00:41:00Z — reviewer 順帶查出 DoD 的引用有歧義：突變測試的正式來源是 `test-case-authoring.md` §5，不是 `TESTING.md` §5（後者是 `tcms_validate.py` 的機械檢查）。原文把兩份文件並列寫成「依 `TESTING.md` 與 `test-case-authoring.md` §5」，易讀成 §5 同指兩者。已改為單一明確來源並註明兩者差異。

- 2026-08-18T00:11:00Z — reviewer M-2 指出「事實更正 vs 政策變更」的區分沒有處理「該段文字落在 gate 治理的五個 section 之一」這件事，質疑成立。經人工確認（Q3=A）後定案為**有意識的例外而非先例**：保留一條已知為假的記載，其代價（每個讀 `team.md` 的 stage 都取得錯誤認知）高於一次越界編輯的程序成本；且變更僅限刪除失效描述，不新增規則、不放寬約束。此判斷已完整寫入 `requirements.md`，不留隱含推論。

- 2026-08-17T00:31:30Z — Q1 選 A（全域掃描）而非 B（PR base 比對），代價是語意由「不得新增」變為「不得存在」，且未來若有正當的 `prod` path part 需求會缺乏豁免機制。接受此代價的依據：實測 0 命中（S-5），且 B 需要放棄 CI 的淺 clone 效能設定並在腳本內處理兩種事件的 base 差異（S-3、S-4），變更面與長期維護成本都明顯較高。豁免機制列為開放問題，待實際出現再處理，不預先設計。

## Open questions
- 2026-08-18T00:12:00Z — `team.md` 五個 gate 治理 section 內的**純事實記載**該由誰維護、如何更新，目前無規則可循。本次以例外處理，根本解法留待下次 practices-discovery。
- 2026-08-18T00:12:30Z — `discovered-rules.md` 第 4 項（同一缺陷）在本次修正後應標註為已解決，但它屬另一個 intent 的 record，本 intent 不逕行修改；已列入完成摘要的待辦。

- 2026-08-17T00:32:00Z — 語意轉為「不得存在」後的豁免機制未定義（例如第三方套件目錄含 `prod`）。目前 0 命中故不預先設計。
- 2026-08-17T00:32:30Z — `validate_no_obvious_secrets()` 的掃描範圍過窄（只讀 contract 清單內的檔案，看不到 `backend/`／`frontend/`）是同一支腳本內的另一個既知落差，但成因與修法都不同，已明確排除於本 intent 範圍外。它仍未被追蹤在任何 issue 上。
