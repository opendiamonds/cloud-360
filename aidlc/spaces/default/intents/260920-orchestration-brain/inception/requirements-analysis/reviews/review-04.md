## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Iteration:** 1

**Date:** 2026-09-25T01:45:22Z

本輪為**定向終驗**（advisory）：只查 R-14、R-18、R-19 三項修法是否落地，以及這三項修法有沒有弄壞相鄰的內容。其餘已結territory 不重開。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-14 | Major | `aidlc/spaces/default/intents/260920-orchestration-brain/inception/requirements-analysis/requirements.md` > NFR2「量測機制（R-14 修正）」（第 296–318 行） | 已修正且引用逐字複驗成立。N 個情境改為「全部放在同一個 Playwright `test()` 之內、最後只對 `通過數 / N ≥ 0.95` 下一次斷言」，可實作。三處引用實測無誤：`.github/workflows/ui-regression.md:191` 逐字為 `run: timeout 15m npx playwright test`；同檔 281–284 行確為 `.stats.unexpected` 的讀取與判定（283–284 行為 `unexpected=$(jq '.stats.unexpected' pw-report.json)` 及其註解）；`frontend/playwright.config.ts` 確為單一 `chromium` project 且 `testDir: './tests/e2e'`，故「寫成獨立於該判定之外的一支測試」的收回是正確的。**NFR11 的豁免成立**：NFR11（第 409–420 行）的判定為「每個情境的切換次數都嚴格少於基準」，屬全體量化條件，任一情境未達即應整體失敗，因此逐情境 `test()` 在該處才是正確形狀，與本條的比率形狀不衝突，兩條 NFR 的量測形狀也已就地寫明不得互相套用。唯一殘存的實作歧義另記於 R-20 | 無 | Resolved |
| R-18 | Major | 同上 > 「人工確認範圍的落差與其處置（R-11）」（第 548–571 行）／`requirements-analysis-questions.md` 第 296–339 行／audit shard 第 8959–8969 行 | 已徹底修正，且自述未誇大。問題檔的 Consolidated Summary Confirmation 現已逐字列出**七項**回補交付物（第 315–323 行明寫「**七項**…（N-1 至 N-7）」並逐項點名，含 N-5 的 RBAC story id ＋ 兩條 blocking 規則、N-6 的 gh-aw workflow、N-7 的建立路徑），以及 FR1.7 的 `0.7`（第 328–331 行；`grep -c '0\.7'` 命中 **1**，前輪為 0）；`[Answer]: Looks correct` 就位。稽核憑據為真：shard 於 `2026-09-25T01:43:54Z` 有一則新的 `SUMMARY_CONFIRMATION_RECORDED`（`Details: Looks correct`，`Summary Authorization Id: aa74c54b…`），且其後兩份產出的 `ARTIFACT_UPDATED` 皆掛同一個授權 id。artifact 的三回合沿革（HTML 註解嘗試 → `SUMMARY_CONTENT_STALE` → 重取確認）與 shard 記載一致，未把重取說成無代價。前輪指出的「紀錄落點被 AI 單方面替換」已消除——紀錄現在就在使用者當初指定的那一份問答紀錄裡 | 無 | Resolved |
| R-19 | Minor | 同上 > 慣例表下方證據標記說明（第 38–41 行的 HTML 註解） | 已修正，且刪除是對的處置。`grep '25 處'` 命中 **0**，計數確實消失；移除註解所引的數字實算複驗**全部相符**——全檔 `[讀]`／`[簽]`／`[算]`／`[未驗]` 出現 **31** 次、扣除第 33–45 行說明段為 **26** 次，與註解逐字寫的「全檔 31、扣說明段 26」一致，且它如實把審查採較窄範圍得到的 22 與 21 一併記下。刪除優於挑一個範圍：四種合理算法各有不同答案，而該數字不被任何下游判讀使用，保留它只會讓下一個人再算一次 | 無 | Resolved |
| R-20 | Major | 同上 > NFR2 量測機制第二個子句（第 300–302 行）「以 **soft assertion 或自行計數**記錄每個情境的通過與否（**單一情境失敗不得中止該 test**）」 | R-14 的修法把兩種收集機制並列為等價，但其中一種會把它要消除的 100% 門檻整個裝回來。Playwright 的 `expect.soft()` **不中止**測試，卻仍會**把該 test 判為失敗**；因此若逐情境以 soft assertion 記錄，只要有一個情境未通過，該 test 即失敗、`pw-report.json` 的 `.stats.unexpected` 非 0、`ui-regression.md:281–284` 即 `exit 1`——比率斷言是否通過完全不影響結果，實際門檻回到 100%。只有「自行計數」（不對單一情境下任何 `expect`／`expect.soft`、僅累加布林結果）能真正讓 0.95 成為門檻。本條的約束句寫的是「不得中止該 test」，而真正需要的約束是「**不得使該 test 失敗**」——兩者在 Playwright 下不是同一件事，實作者照字面選 soft assertion 不算違反本條 | 把該子句的機制改為只允許「自行計數」（逐情境以 `try`／布林捕捉結果、不下 `expect.soft`），或保留 soft 選項但就地寫明「`expect.soft` 會使該 test 失敗、故不適用於本條」；同時把約束句由「單一情境失敗不得中止該 test」改為「單一情境失敗不得使該 test 被判為失敗」 | New |
| R-21 | Minor | 同上 > 第 550–552 行「**落差（複審 R-11 查出）**」段 | R-18 的修法留下一句現已為假的現在式陳述：該段寫「`0.7` 這個數字在問題檔零出現」，而重取確認後問題檔的 `0.7` 命中數為 **1**。同段的另一句（收據涵蓋四項）已由「修訂 1 的」限定為歷史事實，這一句沒有同樣的時態限定。第 565 行起的結語已正確聲明「本節不再是兩份文件不一致的解釋」，故讀者不致被實質誤導，但這一句本身與本檔第 565–571 行自述的現況直接相牴觸 | 為該句補上時態限定（例如「修訂 2 當時，`0.7` 在問題檔零出現」），或直接刪除該子句——現況已由同節第 3 點與結語承載 | New |

### Summary

三項修法**全部乾淨落地**：R-14 的比率量測現在是一個可實作的單一 `test()` 形狀，其三處工具鏈引用逐字實測無誤，NFR11 的豁免在邏輯上成立（全體量化條件 vs 比率條件，形狀不同且已就地禁止互套）；R-18 不再是替代紀錄而是真的修好了——問題檔的確認區塊已列出七項與 `0.7`，並有 `2026-09-25T01:43:54Z` 的新收據與後續產出的授權 id 鏈；R-19 的錯誤計數已刪除，移除註解自報的 31 與 26 我實算相符。

重新清點的七個數字**全部相符、零懸空**：FR 子需求定義 **49** 條（unique 49，**無重複 id**）、FR 群組 **10** 個（FR1–FR10；`NFR10`／`NFR11` 不是 FR 群組）、NFR **11** 條、N 項 **7** 項（N-1…N-7）、OQ **14** 個、假設 **7** 條；`FR`／`NFR`／`OQ-`／`N-`／`A-` 的全部交叉引用皆指向已定義 id。`python3 scripts/validate_repo_contract.py` PASS。

本輪唯二的新發現都是這三項修法自身的副作用，且都是字句層級：**R-20** 是 R-14 並列的兩種收集機制中，`expect.soft` 會使 test 失敗、因而把 95% 門檻退回 100%——正是該 finding 要消除的形狀，在一個選項裡存活下來；**R-21** 是 R-18 修法後遺留的一句現已為假的現在式陳述。兩者皆為就地改一句話即可收斂、不需重開任何已核可決定，故不阻擋；零 Critical。
