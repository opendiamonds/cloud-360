## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

這是補審。凍結的四份產出（entities、rules、functional-spec、traceability）與舊的 review-01／review-02 比對後，舊發現 R-01 至 R-11 在產出中全部仍在，沒有任何一項被修進文件。已落地的程式（`design_agent.py`、`agent_router.py`、`wa_collab_orchestrator.py`、`progress_channel.py`）在 R-01、R-02、R-07 上已經做對了，所以這幾項是「設計文件錯、程式對」，以程式為準。文件若逐字照做，主路徑（`agent_router.py`）不會被修，例外原文也仍會外洩。設計層的缺口是 BR5.1 漏列呼叫點與 catch-all、BR4.1 的上界在最壞情形無界、SM-2 少一個結果，以及紅燈表與自檢的計數不實。舊的 Critical 與多項 Major 仍在，故判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Critical | `construction/progress-channel/functional-design/rules.md` > `BR5.1` logic；`entities.md` > 「既有符號的退場」表；`functional-spec.md` > `WF-1` 步 1–3 | 前次 review-02 R-01 已提，產出未改。BR5.1 與退場表只列 `wa_collab_orchestrator.py:79` 一個 `run_design_agent` 呼叫點。實際有三個：`agent_router.py:150`、`wa_collab_orchestrator.py:96`、`backend/test_agent.py:53`。`agent_router.py` 才是 A1 產圖的 SSE 主路徑，也就是 AC13.1.1 與 AC13.1.2 描述的路徑。照文件實作，主路徑要嘛壞掉（參數必填），要嘛不開通道、全部事件被 BR3.2 丟棄，AC13.1.1 的「各自非空」必紅。程式已正確落地：`request_key` 是必填關鍵字參數（`design_agent.py:218`），`agent_router.py:131-162` 在 generator 內 `open` 並於 `finally` 內 `close`。**以程式為準，設計文件落後。** | 把 `agent_router.py` 主路徑（必做）與 `test_agent.py`（次要）補進 BR5.1 與退場表，各給 disposition（鑄造鍵、顯式傳入、`try/finally` 內 close），並說明 U12 與 U13 尚未落地時這些既有呼叫點即入口端。 | New |
| R-02 | Critical | `rules.md` > `BR3.1`（trigger「本單元任一操作」）與 `BR5.1` 符號清單 | 前次 review-02 R-02 已提，產出未改。例外原文送達使用者的唯一出口是 `run_design_agent` 的 catch-all（原 `design_agent.py:216`，f-string 插入例外），它不在 BR3.1 的射程內，也不在 BR5.1 的符號清單內。BR1.2 新增的 `DuplicateChannelKey` 會流經同一條路徑，設計自己開了新口。程式已修：現行 catch-all 改為 `logger.exception` 加固定字串「發生未預期錯誤，請稍後再試。」（`design_agent.py:286-291`）。**以程式為準；文件沒有任何一條規則要求這個修法。** | 擴寫 BR3.1 的 trigger 為「任何被呼叫端轉為對外事件的例外，含 DuplicateChannelKey」，並把 catch-all 與 `:103` 類的 `return f"產圖失敗：{e}"` 納入 BR5.1。同步更新 traceability 的 AC13.1.3 列。 | New |
| R-03 | Major | `rules.md` > `BR4.1` 第二分支；`functional-spec.md` > `WF-4` 第 3 列 | 前次 review-02 R-03 已提，未改。buffer 只因 drain 縮小，溢位的前提正是 drain 跟不上。buffer 全為 `xml`、`error` 時，後續每則 `xml` 都須寫入，則數由 agent 迴圈決定、無固定上限，所以「暫時超過上界」在最壞情形下並非上界。`[Q4]`=A 的選項原文是「設一個有限上界」。程式同樣如此（`progress_channel.py:231-235`，非可丟棄事件一律 append）。 | 補第二層硬上限與其處置（例如大聲失敗，或丟最舊的 `xml` 並記 WARN），或寫明 `xml`、`error` 的自然上界並給依據；兩者皆不可就升為具名 OQ，明寫本單元不提供上界保證。 | New |
| R-04 | Major | `functional-spec.md` > `SM-2`（含文字 fallback 與「三個終態」那句） | 前次 review-02 R-04 已提，未改。`publish` 有四種結果，狀態機只畫三種。BR4.1「已無 progress 可丟、拒絕寫入新的 progress」是第四種：通道存在（不是 `Dropped_NoChannel`），事件從未進入 buffer（不是 `Queued`，而 `Dropped_Capacity` 只有 `Queued` 一條入邊）。檔頭自稱此檔是狀態機的真實來源。程式有這條分支（`progress_channel.py:236-246`）。 | 補 `[*] --> Dropped_Capacity: publish（容量已滿且無 progress 可丟）` 或新增具名終態，同步更新文字 fallback。 | New |
| R-05 | Major | `rules.md` > 「哪幾條是現狀會讓它紅燈的」表；`functional-spec.md` > §六 自檢 1 | 前次 review-02 R-05 已提，未改。腳本解析該表只得 11 個 BR id，缺 `BR1.1` 與 `BR3.2`，而兩者現狀皆為紅（`BR3.2` 的現狀違反即原 `if _progress_queue is not None` 靜默跳過）。自檢 1 卻寫「逐條列於」該表並報通過，報得不實。 | 補兩條並各給現狀與修後判定，重算自檢 1 的「七條為紅」。 | New |
| R-06 | Major | `rules.md` > 紅燈表 `BR1.2` 列；`functional-spec.md` > 自檢 1 | 前次 review-02 R-06 已提，未改。BR1.2 被計為現狀紅，理由是「`:183` 直接指派」。那是覆寫另一請求佇列，屬 BR1.3 的違反面，不是「同鍵重複 open」。同表排除 BR2.2 的理由是「操作不存在」，而 `open()` 現狀同樣不存在，兩處理由互斥。這會讓人以為 AC13.1.1 的測試順帶涵蓋重複 open。 | 把 BR1.2 歸入與 BR2.2、BR5.2 同類（現狀無對應操作，以專屬測試驗證），指定一條具名的重複 open 測試，更正自檢計數。 | New |
| R-07 | Minor | `functional-spec.md` > `A-P2`；`entities.md` > `channels` constraints | 前次 review-02 R-07 已提。「單執行緒故不需鎖」只說了一半，缺「臨界區內不得有 await」這條使它成立的不變量。**程式已承載**：`_admit` 是同步函式，並以 docstring 明寫（`progress_channel.py:205-211`）。屬文件未跟上，降為 Minor。 | 把「publish 自容量判定到 buffer 變更不得有 await」寫進 BR4.1 或 A-P2，並指定 code-generation 以同步私有函式承載。 | New |
| R-08 | Minor | `functional-spec.md` > `WF-4` 第 3 列 vs `rules.md` > `BR4.1` 第一分支 | 前次 review-02 R-08 已提。同一輸入（buffer 滿、有 progress 可丟、新事件是 `xml`）兩處答案不同。BR4.1 第一分支寫先丟最舊 progress，WF-4 寫一律寫入。**程式採 WF-4 的行為**（`progress_channel.py:231-235`，新 `xml` 直接 append，不先丟 progress），故 BR4.1 的文字是錯的一邊。 | 修訂 BR4.1，說明非可丟棄新事件一律寫入且不先丟 progress，或明定要先丟並改程式，兩者擇一。 | New |
| R-09 | Minor | `entities.md` > 退場表末段；`functional-spec.md` > §六「本階段新增」 | 前次 review-02 R-09 已提。US13 DoD 要求清三個模組層可變狀態，本設計只清兩個，依 K-18 保留 `design_agent.py:169` 的 `MemorySaver()`。保留是對的，但 §六 宣稱全部落在 K-18 與 US13 DoD 範圍內，而這一處是契約推翻 DoD 字面要求。 | 在退場表或 §六 明寫與 US13 DoD 第 4 條字面不一致，並說明依 K-18 保留的理由。 | New |
| R-10 | Minor | `traceability.json` > `deferred[0]`（`FR13.4`） | 前次 review-02 R-10 已提。機讀檔寫 `status: "Deferred"`，同列 note 卻說上游已更正為 OK，這是「散文與機讀檔不一致」的同一形狀。`FR13.4` 也不在 `upstream_ids` 內。 | 改用能表達「本單元只承接一半」的狀態值，或移出 `deferred` 改列為指派 `OQ-P2`。 | New |
| R-11 | Minor | `functional-design-questions.md` > `## Assumptions & Open Questions` | 前次 review-02 R-11 已提。整節仍是佔位文字「（本站產出時填寫）」，而 functional-spec §六 實有 OQ-P1、OQ-P2、A-P1、A-P2 四項。問題檔會被讀成「本站沒有開放項」。 | 把四項或其摘要與落點填入該節。 | New |
| R-12 | Minor | `rules.md` > `BR2.4` logic「否則呼叫端能分辨……」；`functional-spec.md` > §五 IAM 格 | 前次 review-02 R-13 已提，未改。「可區分會洩漏『鍵曾存在』」需要能以任意鍵呼叫 `drain` 的不可信呼叫端，而本單元是 library，`drain` 只由 U13（同進程）呼叫。決定（空迭代器、不拋）正確，但理由撐不住放進 ADR-0006 IAM 格所隱含的強度。 | 把理由改錨到健壯性（呼叫端無法先驗知通道是否已 close，拋例外會重建 AC13.1.2 的崩潰面），不可猜性只保留為輔助說明，不作安全邊界主張。 | New |
| R-13 | Minor | `rules.md` > `BR1.1` logic；`functional-spec.md` > `WF-1` 步 1 與步 2 | 前次 review-02 R-12 已提，且已被程式落地為另一個答案。文件寫鑄造者為「U13 或 U12」二擇一，步 2 說由 U12 open。實際由 `agent_router.py:131` 的入口端用 `secrets.token_urlsafe(32)` 鑄造、`open` 也在同一 generator 內（`:138`）。**以程式為準**，文件的鑄造者與 open 的歸屬都已過期。 | 指名單一鑄造者與 open 的呼叫者，並寫明 U12、U13 落地前的入口端即 `agent_router.py`；更新 WF-1。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 比對凍結產出與 review-02 的 R-01 至 R-13 | 11 項（R-01 至 R-11）在產出中仍存在，無一被修進文件 | 舊發現未處置，對應本次 R-01 至 R-06、R-08 至 R-11、R-13 |
| `run_design_agent(` 呼叫點盤點（`backend/`，不含 tests） | 3 處：`agent_router.py:150`、`wa_collab_orchestrator.py:96`、`test_agent.py:53` | BR5.1 只列 1 處，確認 R-01 |
| 程式抽查 `design_agent.py`（`:213-231`、`:262-291`） | `request_key` 必填；catch-all 改為固定訊息加 `logger.exception`；已無 `_progress_queue` 與 `_last_xml` | R-01、R-02 的修法已在程式，文件落後 |
| 程式抽查 `agent_router.py:131-162` | 入口端鑄造鍵、generator 內 open、`finally` 內 close | 符合 BR2.1，與文件寫的鑄造者歸屬不同（R-13） |
| 程式抽查 `progress_channel.py:205-262` | `_admit` 為同步函式；非可丟棄事件在滿載時直接 append；全為不可丟棄時拒絕新 progress | 確認 R-03、R-04、R-07 的程式面；R-08 以程式的行為為準 |
| 本輪未執行測試、lint、建置 | 不適用 | 依派工限制不寫檔、不產生快取 |

