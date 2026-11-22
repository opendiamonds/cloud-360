## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-12T23:30:39Z
**Iteration:** 1

### Findings

| ID | Severity | Status | Location | Finding | Required action |
|---|---|---|---|---|---|
| R-01 | Major | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR64.13 logic 與 BR64.8 kind=intent 分支；functional-spec.md > GW-W3 第三列、D-10 | 反問選定意圖後，以「長度 2 以上的名稱是原句子字串」掃描目錄，並在恰一個命中時走 BR64.9 的更新路徑直接 set_work_target。已知限制只揭露了漏判（代名詞、簡稱），沒有揭露誤判：中文專案或系統名稱常是兩字通用詞（例如「測試」「訂單」「成本」），原句「幫我測試這張圖」會讓名為「測試」的專案被當成句中點名的對象，靜默改掉作業對象後交辦。這正是 BR64.8 與 BR64.11 要防的「工作項建在使用者沒指的對象上」，只是入口換成子字串誤判。另有巢狀名稱問題：同專案下有系統「訂單」與「訂單系統」，使用者逐字講出唯一的完整名稱「訂單系統」，兩者都是原句子字串，結果為兩個不同對象，走 BR64.11 (c) 回「提到了不同的對象」，對使用者而言是錯誤的拒絕。此外同一句話在高信心路徑（referent 為 null 則不掃描、依當前對象交辦）與低信心反問後路徑（掃描並可能改對象）行為不同，沒有說明理由。實測依據：BR64.13 全文只列「代名詞或簡稱無法辨識」一項限制；hierarchy_service.create_system 只擋同專案同名（hierarchy_service.py:153-158），不阻止子字串包含。 | 至少做到其一：(1) 掃描只取最長不被其他命中包含的名稱，並對只靠兩字名稱的命中不自動切換對象，改走 BR64.11 (a) 的對象反問讓使用者確認；(2) 或明文揭露誤判為已知限制並由使用者裁決接受；(3) 說明低信心路徑為何比高信心路徑更積極地改作業對象。補測試：原句含兩字通用詞且恰為某專案名；巢狀名稱（完整名稱包含另一名稱）。 |
| R-02 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/functional-spec.md > 七 PBT 性質五；rules.md > BR64.13 與 BR64.9 | 性質五與 BR64.13 自相矛盾：性質五要求「目錄中任一長度 2 以上的名稱 n，若是原句子字串則 n 的對象在結果內」，而 BR64.13 同時規定「同一專案下系統命中時專案名的命中不另計」，兩者同時命中時專案不在結果內，性質不成立，照字面寫成 property-based 測試會紅燈或被迫排除。另外 BR64.9 對 referent 同時相符於專案與其自己的系統（專案與系統同名是常見命名）計為兩筆而走對象反問，BR64.13 對同樣情況卻去重為一個對象，兩條規則對同一個目錄給出相反結論；BR64.9 的「去空白」是去頭尾還是去除全部空白也未定。 | 把去重規則寫進性質五的前提或結果定義；統一 BR64.9 與 BR64.13 對「專案與其系統同名」的處置；寫明去空白的語意。 |
| R-03 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR63.2 排序保證、BR63.6；functional-spec.md > GW-W1 步驟 9 | 排序保證只在「暫存佇列送完後才改 phase」且「送佇列期間新到的訊息不遺失」時成立，但規則只寫「依序送出暫存佇列，最後把 phase 改為 ready」。送出是 await，期間另一協程的扇出仍看到 phase=loading 而附加到佇列；若實作對佇列取快照再迭代，或迭代結束到改 phase 之間有 await，新增的訊息會被丟失或卡住，客戶端停在舊狀態，BR63.2 宣稱的收斂失效。登錄在讀取之前的修正只覆蓋讀取期間，不覆蓋送出期間。測試只描述了在 load 與 list_items 之間注入，未涵蓋送出期間注入。 | 寫明：持續從佇列頭取出直到為空，在最後一次空檢查與 phase 改為 ready 之間不得有 await；補一個在快照或佇列送出期間注入 emit_session 的測試，斷言客戶端最後收到的狀態為最新。 |
| R-04 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR64.12 專案上限分支；traceability.json > AC1.1.5 | 專案數超過 50 時，目錄只含專案名稱不含系統名稱，AC1.1.5 的主情境（系統名稱）對這類使用者靜默失效，而使用者看到的是 BR64.11 (b) 的「找不到名為 X 的系統或專案」，這句話是不實的（系統存在，只是沒掃描），規則只記 INFO 計數。同理，U11 抽出的 referent 若與名稱不逐字相同（使用者說「訂單系統」而系統叫「訂單」），也走同一句不實的 (b)。traceability 把 AC1.1.5 標 OK，註記雖寫了前提，但沒有列出超過 50 個專案這個使 AC 失效的條件。已查證的部分：list_projects 只回擁有者專案、list_systems 先確認擁有（hierarchy_facade.py:275-288），目錄範圍與 K-07 一致，OPEN-GW13-16 的揭露誠實。 | 上限分支改用不暗示「不存在」的固定句型（例如請在脈絡列選定系統），或改為對前 N 個專案之後的名稱仍可由使用者指定；traceability 的 AC1.1.5 註記補上專案數上限與逐字相符兩項使 AC 不成立的條件。 |
| R-05 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR67.12 熔斷與等待上限；BR67.10 | 熔斷器是全域的，且任何一次預取或寫入的例外都會開啟 30 秒，包括只屬於單一使用者輸入的失敗（MemoryFacade.write 對 4000 字元原句加 4000 字元回覆做嵌入，過長內容可能讓提供者拒絕，memory_facade.py:246-285 先嵌入再寫列）。一位使用者的長訊息可讓所有使用者的記憶預取停 30 秒，U11 的註解自承記憶降級可能改變分類結果（intent_routing.py:192-215），所以影響面是全體使用者的分類品質而非僅記憶輔助。預取等待 3 秒也低於 Ollama 冷載模型的合理耗時，一次冷載即觸發熔斷。執行器工作佇列未設上限，4 條執行緒被慢嵌入佔滿時已逾時的工作仍留在佇列。對 U11 降級契約的相容性已查證：轉接器拋例外由 _memory_notes 的 except 降級，query 與 limit 一致，無相容問題。 | 熔斷只計入逾時與提供者不可用類例外，不計入輸入類例外；說明或調整 3 秒與冷載的關係；為執行器佇列加上限或在逾時時取消尚未開始的工作。 |
| R-06 | Minor | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/functional-design/rules.md > BR67.11 第 1 點；functional-spec.md > GW-W7 | 規格稱「本單元不新增環境變數，故無 LOCAL-DEV.md 同步義務」，但 REDIS_URL、REDIS_USER、REDIS_PASSWORD 從此成為後端啟動的必要條件（缺值 KeyError 使整個後端拒絕啟動，影響所有既有功能而不只是大腦）。LOCAL-DEV.md:23-24 現在把 Redis 描述為「session 相關功能不可用」的軟依賴，並且只把 BRAIN_SESSION_HISTORY_MAX 列為啟動拒絕條件，本變更後兩處都不實；舊的 backend/.env 若不含 REDIS_* 會整個起不來。LOCAL-DEV.md 是唯一記載隱性前置條件的文件，project.md 規定其過期即等於沒有。 | 把 LOCAL-DEV.md 的更新列為 code-generation 的交付條件（啟動必要變數表加入三個 REDIS 變數，並說明缺值會拒絕啟動）；更正 GW-W7 與 BR67.11 的免同步說法。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| review-02 R-01 複驗（referent 範圍） | 大致修好 | BR64.12 以 list_projects 加逐專案 list_systems 取目錄，未選定且系統名唯一時可解析，AC1.1.5 主情境可達；範圍限擁有者並已於 OPEN-GW13-16 揭露，與 hierarchy_service.resolve_work_target 的 owner_user_id 範圍一致。殘留見 R-04 |
| review-02 R-02 複驗（反問後選定） | 部分修好 | 已不再以 referent=None 直接交辦，但新增的子字串掃描引入新缺陷，見 R-01、R-02 |
| review-02 R-03 複驗（握手競態） | 大致修好 | 先登錄再讀取、佇列上限 256、溢位 1011，排序論證在讀取期間成立；送出期間的原子性缺口見 R-03 |
| review-02 R-04 複驗（契約衝擊） | 已修好 | test_ws_contract.py:283、288、290 與 :47、:61-62 行號與內容皆相符；全 backend 除契約檔外沒有其他構造這些模型的程式；get_args 取字面值的寫法與同檔既有形狀一致 |
| review-02 R-05 複驗（C-7 與 (b)(c)） | 已修好 | ClarifyPayload 於 brain_ws_contract.py:214，無 kind 欄位，增量合理；(b)(c) 明列不寫 episodic，與 BR67.7 窮舉一致 |
| review-02 R-06 複驗（startup） | 順序已修好，副作用未交代 | main.py:55-77 的順序與規格相符；build_redis_client 延遲連線屬實（redis_gateway.py:510-536）；LOCAL-DEV 說法見 R-06 |
| review-02 R-07 複驗（執行緒池） | 大致修好 | 專用 4 執行緒與熔斷隔離了共用池；熔斷範圍與佇列見 R-05 |
| 行號與內容分開抽查 | PASS | hierarchy_facade.py:275 與 :282、intent_routing_predicate.py:248-275 的 decide、intent_routing_types.py:183-195、main.py:56-77、dump_ws_contract.py:108-116 的白名單，定位與內容皆相符 |
| traceability.json | PASS | upstream_ids 八項，AC1.1.5 為 OK 且註記載明前提；AC8.1.1 Deferred 誠實；R-04 補充一項遺漏的失效條件 |
| 測試與他單元 | 未執行 | 依派工指示不跑測試；未開啟兄弟單元，U11 與 U12 僅以已交付程式核對 |

### Summary

Critical 0、Major 1、Minor 5，判定 NOT-READY（有未解的 Major）。review-02 的七項大多實質修好，契約測試清單與行號正確，但為關閉 review-02 R-02 而新增的原句子字串掃描（BR64.13）引入新的誤判路徑：兩字通用詞會靜默改掉作業對象，巢狀名稱會對完整名稱誤報歧義，且性質五與去重規則自相矛盾。新發現來源分類：修正新引入 3（R-01、R-02、R-04 的上限分支與不實句型）、既存漏審 2（R-05 的熔斷範圍、R-06 的 LOCAL-DEV 影響）、新設計問題 1（R-03 的送出期間原子性）。
