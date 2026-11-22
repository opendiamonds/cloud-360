## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

設計本身自洽，三項定案（逐頁、保留可重入、作業對象分段）與 K-02 最小改動集的論證站得住，ADR-0006 四面向皆有落點。但契約端點三問仍有三個缺口，其中兩個已被落地程式碼以設計沒有的方式填補，造成設計與實作矛盾：(1) 全新 session 由誰寫入（前次 review-01 的 R-01 仍留在凍結產出裡）；(2) userId 被宣告為必填卻沒有任何寫入端；(3) 設計明說同一使用者有多條存活連線，卻沒有任何並行寫入規則。三項 Major 超過兩項，判 NOT-READY。補審結果交由關卡人員裁決。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/session-store/functional-design/functional-spec.md 的 W1 第 5 步與 W7 第 4 步；rules.md 的 BR1.6；對照 backend/services/session_store.py 的 _ensure_meta（約 514-540 行） | 前次 review-01 已提 R-01，仍留在凍結產出裡。設計寫「U13 回無時建立新 session」，但 K-09 的五個方法沒有任何一個被指名負責把 EC1（shared 段存在）與 EC2（pageModes 預設）寫進 Redis。落地程式碼的做法是：set_sharing_mode、set_work_target、append_message 在首次寫入時由本單元內部的 _ensure_meta 隱式建立 meta 與 shared 段，docstring 還特別說明「K-09 沒有 create 方法，故建立就發生在這裡」。也就是實作與設計 W1 第 5 步的執行者（U13）相反。以程式碼為準是合理的（U13 無法建立 K-09 沒有的方法），錯的是設計文字。 | 在 functional-spec.md 的 W1／W7 與 rules.md 新增或改寫一條規則：session 的首次建立發生在本單元的首次寫入方法內（lazy create），並明訂 load 回無之後、首次寫入之前的窗口狀態，以及它與 BR1.3、BR2.4 的關係。 | New |
| R-02 | Major | construction/session-store/functional-design/entities.md 的 BrainSession.userId（required: true）；functional-spec.md §八自檢 2 的 userId 列；對照 session_store.py 的 _ensure_meta docstring | 契約端點三問的「誰寫」不成立。自檢表寫「userId：本單元於建立時自 principal 取」，但 K-09 裡只有 set_work_target 帶 principal；append_message、set_sharing_mode、touch 都沒有，而 session 的首次寫入可由這三者中的任何一個觸發（R-01）。落地程式碼因此讓 meta.userId 為 null，並在 docstring 自承「契約沒有給它寫入端」。結果是一個宣告為必填、被 U11／U12／U13 當作「免再解析」來源的欄位，在 session 的部分生命期內恆為 null。自檢表標示「通過」是錯的。 | 二選一並寫進產出：(a) 把 userId 降為非必填的衍生欄位，明寫讀取端須自 sessionKey 解析；或 (b) 指定一個保證帶 principal 的首次寫入入口，並要求其他方法在 userId 缺值時不得成為首次寫入。同時更正自檢 2 的判定。 | New |
| R-03 | Major | construction/session-store/functional-design/rules.md 的 BR2.3、BR6.2（無並行規則）；functional-spec.md 的 W1 第 6 步與 §六（同一 key 有多條存活連線）；對照 session_store.py 的 set_sharing_mode 切回 shared 分支（約 346-350 行） | 設計明確假設同一使用者同時有多條連線（BR2.7 扇出給全部存活連線），但全部規則只談冪等與重試，沒有任何並行寫入規則。落地程式碼的切回 shared 分支是「讀整個 meta、改一個頁面、整個寫回」，兩個分頁同時操作不同頁面（workspace 與 assessment）時，後寫者會把另一頁剛改的模式覆蓋回舊值，直接違反 BR2.3「只改該頁的模式，其餘頁面不動」。切到 isolated 走 Lua 腳本，兩條路徑的原子性不一致。BR6.2 只說這些方法冪等，冪等不等於並行安全。 | 在 rules.md 新增並行規則：對同一 session key 的寫入須為單頁欄位級原子更新（或明訂 compare-and-set），並要求 BR2.3 在並行下仍成立；補一條涵蓋雙連線不同頁面同時切換的驗收情境。 | New |
| R-04 | Minor | construction/session-store/functional-design/rules.md 的 BR4.6、BR4.7；functional-spec.md §七 IAM 格 | 前次 review-01 的 R-02 仍留在凍結產出裡：驗證只發生在寫入當下，讀取不重驗，撤權或實體被刪除後 session 內的識別碼會過期。BR4.7 的初始化路徑例外只論證了複製不放大風險，沒有明寫時效性邊界與消費端責任。 | 在 BR4.6 或 §七補一句：驗證為寫入時點驗證，本單元不做讀取時重驗，消費端動用識別碼時自行決定是否重驗。 | New |
| R-05 | Minor | construction/session-store/functional-design/rules.md 的 BR1.3、BR3.4、EC9；對照 session_store.py 的 message_max_chars 與 SessionMessageTooLong（約 182、254-257 行） | 設計只限制每段的筆數（EC9、BR3.4），沒有限制單則訊息的長度，而單一 Redis key 的大小是筆數乘以單則大小，上限因此並不真的有界。落地程式碼自行新增了 message_max_chars 與 SessionMessageTooLong，這是設計沒有的規則；以程式碼為準是對的，但設計產出沒有承載它，下一個讀設計的人會以為只有筆數上限。 | 在 rules.md 補一條單則訊息長度上限與超限行為（拒絕而非截斷），並與 BR3.5 同樣要求缺值時大聲失敗。 | New |
| R-06 | Minor | construction/session-store/functional-design/rules.md 的 BR1.3 與 K-09 方法清單；對照 session_store.py 的 load_work_items、put_work_item、update_work_item（約 421-480 行及其前方註解） | BR1.3 寫「K-09 的每一個方法都續期 TTL」，且設計把工作項集合視為「同 key 共存、U12 擁有」。落地程式碼新增三個工作項方法，並刻意不續期 TTL（註解理由：背景推進不是使用者互動，否則輪詢可無限延長 session），這是對 BR1.3 的有理由例外，但設計產出完全沒有這三個方法，也沒有記載例外。以程式碼的理由為準是對的，需要補的是設計。 | 在 BR1.3 補上「工作項方法不續期，因其非使用者互動」的例外與理由，並在 entities.md 的 WorkItem 關係註記這三個方法由本單元代管、語意由 U12 擁有。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 人工逐行核對 session_store.py 的 load、set_sharing_mode、set_work_target、_ensure_meta 與工作項方法 | 設計與程式碼在 session 建立者、userId 寫入端、並行安全、TTL 續期例外四處不一致 | 對應 R-01、R-02、R-03、R-05、R-06；其餘（BR2.2 入口頁拒絕、BR2.5 保留段、BR4.5 不拒絕部分三元組、BR4.6 例外原樣傳遞、BR6.1 大聲失敗）與設計一致 |
| 前次 review-01 對照 | 其 R-01（Major）與 R-02（Minor）在凍結產出中仍未處置 | 已併入本次 R-01 與 R-04 |
| 機械 sensor | 未執行（本補審禁止執行會寫檔的指令） | 無 |
