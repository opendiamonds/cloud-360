## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-18T15:06:33Z
**Iteration:** 1

### Summary

本單元（U22 progress-channel，library）的 nfr-design 產出自洽，隔離結構（per-key dict）、錯誤出口單一化、ADR-0006 四面向判定皆有落點，且已落地的 `progress_channel.py` 與 `design_agent.py` 大體與設計一致（`design_agent.py` 內已無 `{e}` 插值）。有兩項 Major：一是設計對 `DuplicateChannelKey` 的出口描述與實際落地矛盾（程式是對的）；二是「臨界區段由語法保證」的宣稱過強，對應的驗證 grep 是同義反覆。其餘為 Minor。Major 共 2 項，未超過門檻，判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/progress-channel/nfr-design/security-design.md > §二 表格列「DuplicateChannelKey（BR1.2 新增）」 | 設計寫 `DuplicateChannelKey` 「會被 :214 的 except Exception 接住」，但實作中 `ProgressChannel.open` 在入口端（`backend/services/agent_router.py:138`、`backend/services/wa_collab_orchestrator.py:89`、`backend/test_agent.py:47`）呼叫，位於 `run_design_agent` 的 try 之外，不會被該 except 接住。`agent_router.py:141-150` 的註解自述「B-1：這個出口在三個設計站都沒有被設計」，未接住會讓 SSE 串流無聲中止。此處設計錯、程式對。另 §二 表格「不會因為修法而新增一個洩漏來源」的論證建立在錯誤的控制流上。 | 在閘門上標明：以程式為準，三個呼叫點各自 catch `DuplicateChannelKey` 並輸出固定字串。若有後續修訂機會，更正 §二 該列與 `logical-components.md` §四 的呼叫點交接，並加入「open 的呼叫端必須自行處理 DuplicateChannelKey」。 | New |
| R-02 | Major | construction/progress-channel/nfr-design/security-design.md > §三 與 logical-components.md > §三「臨界區段的原子性」列；traceability `U22-V4` | 設計稱臨界區段為「型別／語法保證（非規則）」，並稱 U22-V4 驗證為「`_admit` 內無 `await` 的 grep（而它是 `def` 故也不可能有）」。這是同義反覆：只要有人把 `_admit` 改成 `async def`（`backend/services/progress_channel.py:205` 的 docstring 自己也承認「任何把這個函式改成 async def 的修改都會默默拿掉這個保證」），語法保證即消失，而該 grep 不會失敗。保證只在函式維持 `def` 時成立，仍是靠人記得的規則。 | 將 U22-V4 的驗證改為斷言 `_admit` 是同步函式（例如 `inspect.iscoroutinefunction(_admit)` 為假的單元測試，或 grep `async def _admit` 零命中），並把 §三「語法保證」的措辭收斂為「在維持同步函式的前提下由語法保證」。 | New |
| R-03 | Minor | construction/progress-channel/nfr-design/logical-components.md > §二 表格「一個請求寫爆記憶體」 | 稱「單請求有上界（BR4.1）」，但 `progress_channel.py:136-170,205-260` 的上界是軟上界：xml／error／message 滿載時仍寫入，buffer 可無限超過 `MAX_BUFFERED_EVENTS`。設計文字只說 xml／error 永不丟，漏了 `message`，與程式的 `DROPPABLE_EVENT_TYPES` 不一致。 | 閘門上註明「上界僅限 progress，其餘類型無上界，實務上受單次產圖事件數限制」，並補列 `message` 類型。 | New |
| R-04 | Minor | construction/progress-channel/nfr-design/security-design.md > §四 Audit logging 列 | 設計以 SEC-3 禁止記錄 `content`，但未處理「鍵本身」的記錄。BR2.4 的設計論點是鍵的不可猜性是唯一的可見性機制；而 `progress_channel.py:284,315-320,238-253` 的 ERROR／WARN 全部把 `key=%s` 寫入 log。鍵目前不經外部端點出示，風險低，但設計沒有判定。 | 在閘門上判定鍵可記錄的理由（鍵僅在同進程使用、請求結束即失效），或改記雜湊／前綴。 | New |
| R-05 | Minor | construction/progress-channel/nfr-design/security-design.md > §五 `S-5`、`S-2`；`backend/services/design_agent.py:275-283` | 兩點：(a) `S-5` 的鑄造端驗證已由程式落地（三處皆 `secrets.token_urlsafe(32)`），可標為已解，但設計仍列為中風險待辦。(b) 設計未規定「最終 drain 與 close 的先後」以及例外路徑是否補 drain：`design_agent.py` 的 except 分支不再 drain，`close` 設 `is_open=False` 後 `drain` 迴圈立即停止（`progress_channel.py:326-343`），例外前最後一輪之後緩衝的 progress 會遺失；因 error 為固定字串且 progress 屬可丟棄類，影響低。 | 閘門上記錄 (a) 已解；(b) 在設計補一句「close 之後緩衝內容丟棄為刻意行為」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀檔核對 `progress_channel.py`、`design_agent.py`、`agent_router.py`、`wa_collab_orchestrator.py` | 完成；`{e}`／`str(e)` 插值已清除，`_admit` 為同步 `def`，`open`／`close` 於入口 try/finally 成對 | 設計主張大多與落地一致；R-01 為設計與程式矛盾（程式正確） |
| 測試／lint | 未執行 | 審查規則禁止產生快取或寫檔 |
