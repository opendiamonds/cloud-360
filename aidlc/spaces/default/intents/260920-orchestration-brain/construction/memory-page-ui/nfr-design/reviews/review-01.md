## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Critical | `construction/memory-page-ui/nfr-design/performance-design.md` §二（補償重抓）、§三、§五 | 背景重抓是由刪除的事件處理函式發出，不在 `useEffect` 內，所以 §三 與 §五 倚賴的 effect `cancelled` flag 管不到它。後果有三。(a) 重抓進行中使用者按「下一頁」，舊頁的重抓回應回來後「整頁以新陣列替換」，會用舊頁內容覆蓋新頁。(b) §五 寫「兩次背景重抓由 `cancelled` flag 保留最後一次」不成立：兩次重抓亂序到達時，先發的舊回應會蓋掉後發的新回應。(c) 較早發出的重抓回應若在第二次刪除的本地 `filter` 之後才到，會讓剛刪掉的那一則重新出現。本檔自稱「沿用 `AdminPage.tsx:198-203`，不另起語意」，但該先例實際靠 `requestSeq` ref 的序號比對防亂序（`AdminPage.tsx:124-131`：`const seq = (requestSeq.current += 1)` … `if (seq === requestSeq.current)`），不是 `cancelled` flag。設計沒有採用先例真正的防護機制。 | New |
| R-02 | Critical | `performance-design.md` §二「重抓失敗：保留就地移除後的畫面…下一次翻頁會自然拿到正確資料」 | 這句話為假，等於承認 R-01（offset 分頁跳列）在重抓失敗時仍然存在。以每頁 20 筆為例：第 1 頁刪一則後，伺服器端原第 21 筆已遞補進 offset 0–19，若重抓失敗，使用者按「下一頁」會以 `offset=20` 取得，原第 21 筆永遠不會出現，直到回到第 1 頁。而且是靜默的。先例 `AdminPage.tsx:128-130` 在失敗時至少有 toast：「清單同步失敗，畫面可能不是最新的」。本設計「靜默保留」比先例更弱，卻自稱沿用先例。另有兩個同樣沒有設計的情形：最後一頁刪除時是否仍發重抓；失敗後有無重試或標示。 | New |
| R-03 | Major | `performance-design.md` §二第 2 點 vs `functional-design/rules.md` `BR34.4`／`BR34.6` | `BR34.4` 的 logic 仍逐字寫「不發任何重抓請求」，`BR34.6` 的觸發條件是「本地移除後 `rendered === 0`」。本設計加入背景重抓，卻沒有在任何地方記錄這是對 `BR34.4` 的偏離，也沒有更正 `BR34.4`。依 `project.md` 的 `refined-mockups:c3`，下游對上游的對齊修正要明記，否則純比對兩份文件的人會把它讀成迴歸。更實質的問題是 `BR34.6` 與重抓的交互：刪掉最後一列時，本地規則立即 `page -= 1` 並重抓前一頁，同時對原頁的背景重抓也在途；後者回來為空且 `page > 1`，設計說「套用 `BR34.6`」，會再退一頁。page 3 可能被連退兩次到 page 1。需要定義：同一次刪除只能有一個頁次調整者，且背景重抓若頁次已被改動要丟棄。 | New |
| R-04 | Major | `performance-design.md` 全檔；`nfr-requirements/performance-requirements.md` `UIP-3` 驗證欄 | R-01（跳列）的修法沒有任何一條設計出來的驗證。`UIP-3` 的驗證只是「計刪除前後的請求，斷言沒有其他 kind 的 GET」，這驗的是請求預算，不驗跳列是否消失。可行的做法是 Playwright 以 `page.route` 模擬一個會位移 offset 的伺服器（刪除後後續 `offset=20` 回的列少了原第 21 筆），斷言重抓後第 1 頁有第 21 筆、翻到第 2 頁無漏列；以及「重抓進行中翻頁」「刪空頁」「重抓失敗」三情境。這些都是本設計新增的行為，卻沒有對應驗證。此單元無前端 unit test 框架（`team.md`），e2e 是唯一防線，更需要明列。 | New |
| R-05 | Major | `security-design.md` §四（pending 帳號修法方向） | 「在記憶 API 的 router 層加一個已核准 dependency」有三個沒處理的後果。(1) `memory_router.py` 檔頭與 `tests/test_memory_contract.py` 的 `C3` 都宣告「本層不做任何授權判定、授權全在 facade（K-08 sole_entry）」，router 層 dependency 與這個已核可契約直接衝突，應該放在 `MemoryFacade`／`mint_principal`，才能涵蓋所有進入點。(2) 現況已有進程內消費者：`services/intent_routing.py` 以 `memory_facade` 參數直接呼叫 facade，不經 HTTP；router 層 dependency 對它無效，pending 帳號若能走到大腦路徑，仍可讀到他人的 `platform` 記憶（本審查未查大腦端點是否另有核准檢查，列為待查）。(3) `memory_router.py` 的 `DELETE` 刻意不宣告 403（`[D1]`=A、`D8-1`／`D8-2`），加 dependency 後 pending 帳號 DELETE 會得到 403，需同步更新 `responses` 與 `openapi.json`（CI 的 drift 檢查會紅）。這三點本檔只以「供 code-generation 計畫採用或修正」帶過，沒有指出。既有先例可循：`rbac.py:135` 的 `user_is_approved` 與 `require_arch_action` 的狀態檢查（`rbac.py:205-210`）。 | New |
| R-06 | Minor | `performance-design.md` §二第 3 點 | 語意／程序區「滿 200 則時的計數標示（R-08）由 code-generation 決定」是把設計題丟下去。`BR32.4` 已規定滿載顯示「N+ 則」，刪除後就地移除會使 200 變 199，標題從「200+ 則」變成「199 則」，是一個錯的精確數，與 `BR32.4` 的 violation_behaviour 同形。這在本站即可定案（刪除後該區若原為滿載則保留「+」，因伺服器上可能仍有更多）。 | New |
| R-07 | Minor | `security-design.md` §二 `SEC-U15-5`、§三 XSS | 兩項驗證的偵測力有限。(1) XSS 的 e2e 以 `<img onerror>` 字串當文字節點渲染，在 React 預設行為下不可能失敗，只有改用 `dangerouslySetInnerHTML` 才會變紅，作為回歸網可以，但不是對缺陷的有效測試；建議明寫它的目的是「防止未來引入 `dangerouslySetInnerHTML`」，並以 grep 為主要驗證。(2) 「console 不含記憶內容」只涵蓋本單元自己寫的 log，瀏覽器對失敗 fetch 的自動 console 輸出（含 URL）不在掌控內，但 URL 不含內容，影響低。`data-owner-user-id` 把他人數值 id 放進 DOM，雖然 API 回應本來就有，仍應在 `SEC-U15-4` 註明這是刻意的取捨。 | New |
| R-08 | Minor | `nfr-design/nfr-design-questions.md` | 「零題」的合法性大致成立（兩處選擇皆由先例決定），但第 1 條的前提「沿用 `AdminPage` 先例不需任何新判斷」已被 R-01、R-02 證偽：設計其實偏離了先例（序號 vs `cancelled`、toast vs 靜默）。因此「零題」的理由不能照字面成立，建議在核可時把 R-01～R-03 列為待決。 | New |

### 審查範圍與驗證

- 開檔核對：`AdminPage.tsx:124-131,189-207`、`memory_router.py`（全檔）、`services/auth.py:87-96`、`services/rbac.py:135-141,196-215`、`intent_routing.py` 對 `memory_facade` 的使用、`deploy/docker-compose.test.yml:102`（`EMBEDDING_PROVIDER` 預設 `stub`，所以 CI 的 e2e 可經 `POST /api/memory/records` 種資料，種資料本身可行）。
- 未涵蓋：大腦 WebSocket／HTTP 端點是否另有 pending 檢查（屬他單元，不可讀）；`mint_principal` 本體未取得（grep 無輸出），R-05 的「放在 `mint_principal`」為建議，需 code-generation 確認其位置。
- 已知項目（`R-01`／`R-02`／`R-03` 前輪與 pending 後端缺口）的處置：本審查不重提「是否要做」，只指出設計中的做法有缺口。

### Summary

補償重抓是本單元唯一的新行為，但它的競態防護（以 effect 內 `cancelled` flag）管不到由事件處理函式發出的請求，失敗路徑還會靜默留下跳列，並與 `BR34.4`／`BR34.6` 未經對齊；pending 帳號的修法方向放在 router 層，與已核可的「授權全在 facade」契約衝突且漏掉進程內消費者。建議修訂 `performance-design.md` §二、§三、§五，並在 `security-design.md` §四指明 facade 層落點後再核可。
