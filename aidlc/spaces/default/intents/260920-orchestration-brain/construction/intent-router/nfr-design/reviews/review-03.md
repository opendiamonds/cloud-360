## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

nfr-design 的六份產出整體紮實，前次 review-01／02 的多數發現已落地（L0 fetch、`memory_degraded`、`V-3` 歸型、`label` 由程式附加），且已落地的 `intent_routing*.py` 與設計主張大致相符（`kinds` 常數、`MAX_SLOTS=4`、`temperature=None`）。但仍有三項 Major：前次 `R-04` 的修正沒有傳播到 `scalability-design.md`；ADR-0006 四面向中的 encryption 在本站沒有落點；`D-1` 的降級範圍未界定，已落地的程式以 `except Exception` 把授權拒絕也當成降級吞掉。三項 Major 超過 2 項，判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/intent-router/nfr-design/scalability-design.md §四 表格第二列（約第 55 行） | 前次 review-02 `R-04` 已在 `performance-design.md` §三 把槽位超界改正為 `V-3`／`MalformedRouting`，並明言誤引 `BR2.4` 會污染 `NFR3.74` 的分型失敗率；但同一站的 `scalability-design.md` 仍逐字寫「輸出超過 `maxItems` 8 或槽位超過 4 → 走 `BR2.4` 失敗路徑」。`BR2.4` 是「候選清單為空」（`EmptyCandidates`），與 `reliability-design.md` §二 的 `V-3` 互相矛盾。另外「單槽位候選超過 8」在 `reliability-design.md` 的 V-1～V-5 中沒有任何一道驗證負責，該列等於引用了一道不存在的檢查。前次 review-02 `R-04` 已提，修正未跨檔傳播（`security-design.md` §六 處置表自稱「已更正」）。 | 將該列改為：槽位超界走 `V-3`（`MalformedRouting`）；並在 `reliability-design.md` §二 明定「單槽位候選數 > 8」歸哪一道驗證與哪個失敗型別（已落地的 `intent_routing_parser.py` 需對照確認），再同步兩檔。 | New |
| R-02 | Major | construction/intent-router/nfr-design/security-design.md（全檔；§二、§五 STRIDE） | `project.md` 要求 ADR-0006 四面向逐項判定。本站 IAM（`SEC-1`）、network exposure（`SEC-2`）、audit logging（`SEC-3`～`SEC-5`）都有落點，但 encryption 面零落點：`grep -in "encrypt\|TLS\|https"` 在 nfr-design 六檔只命中 `performance-design.md` 談連線重用的 TLS 握手成本。本單元是 intent 內唯一把使用者自由文字送出平台的新路徑（`security-design.md` §一 自己寫明），傳輸加密（OpenRouter 端點必須為 https、不得降級為明文）與憑證處理（OpenRouter 金鑰只經環境變數、不進 `RoutingObservation`／prompt／日誌）應有設計層的明確判定與可檢查項。 | 在 `security-design.md` 新增四面向判定表（含 encryption：傳輸加密與金鑰處理的設計與檢查方式，或附理由的不適用）；若判定由 `langgraph_runtime` 承擔，須寫明並指出驗證點。 | New |
| R-03 | Major | construction/intent-router/nfr-design/logical-components.md §三「`U8` 不可用時：降級而非失敗」；已落地 backend/services/intent_routing.py:192-229（`_memory_notes`） | `D-1` 只定義「`U8` 不可用 → 降級」，未界定哪些失敗屬「不可用」。已落地的程式以 `except Exception` 一網打盡，連 `MemoryFacade`（`SEC-1` 所述授權由它承擔）拋出的授權拒絕、參數錯誤等程式缺陷也被降級並僅記 WARN。後果：IAM 面的拒絕被轉成「無記憶但繼續分類」，且 `memory_degraded` 無法區分「服務掛了」與「被拒絕／我方 bug」，`D-1` 賴以成立的「降級可被觀測」條件因此失真。授權拒絕不是外部依賴失敗，與 `team.md`「try/except 只用在外部依賴邊界」的精神不符。哪邊對：設計有缺口，程式依缺口實作。 | 在 `logical-components.md` §三 補一條：降級僅適用於可預期的依賴不可用型別（逾時、連線、後端不可用）；授權拒絕與非預期例外須向上傳遞（或至少以獨立 `error_kind` 計數）。同步調整 `intent_routing.py` 的例外範圍（程式修正屬 code-generation 交接）。 | New |
| R-04 | Minor | construction/intent-router/nfr-design/logical-components.md §三 失敗域表格（`U10` 不可用、`U8` 不可用兩列） | 前次 `R-01` 把 I/O 移到新增的 L0 fetch，並把圖與 §二 改過，但 §三 兩列仍寫「L2 取不到上下文」「L2 取不到記憶」。同一份檔仍殘留舊的 L2 做 I/O 的說法，與本檔 §二「L2 為純函式」矛盾，正是前次 `R-01` 要消除的形狀。 | 兩列的「L2」改為「L0」。 | New |
| R-05 | Minor | construction/intent-router/nfr-design/observability-design.md §二 標題「五個訊號」 | 標題稱五個訊號，表格實列六列（含修訂 1 加入的記憶降級率）。 | 改為「六個訊號」，並檢查他檔是否沿用「五個」。 | New |
| R-06 | Minor | construction/intent-router/nfr-design/security-design.md §四 factory 範例；已落地 backend/services/intent_routing_port.py:230-253 | 設計範例是無參數 `router_chat_model()` 內自讀 `os.environ["BRAIN_ROUTER_MODEL"]`；已落地版本改為接收 `RoutingConfig`，並額外傳 `max_retries`。落地版本是對的（設定單一落點、`BR6.3` 可設定），設計範例已過時；SEC-1 結構檢查範例指向單檔 `intent_router.py`，實際模組為 `intent_routing*.py` 多檔（設計已註明暫定，故僅為文件落差）。 | 在 security-design 範例旁註明落地版以 `RoutingConfig` 為參數，或更新範例。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep -in "encrypt\|TLS\|https" nfr-design 六檔 | 僅 performance-design.md 兩行命中，且與加密設計無關 | 證實 R-02 |
| grep -n "BR2.4" nfr-design 六檔 | scalability-design.md:55 仍把槽位超界指向 BR2.4 | 證實 R-01 |
| 實讀 intent_routing.py:192-229、intent_routing_port.py:230-253、intent_routing_types.py:77-82、intent_routing_parser.py:216 | kinds 常數、MAX_SLOTS=4、temperature=None 與設計一致；except Exception 範圍過寬；factory 簽章與設計範例不同 | 支持 R-03、R-06；其餘設計主張與落地相符 |
| 未執行測試或 lint | brief 禁止產生快取 | 僅靜態審查 |
