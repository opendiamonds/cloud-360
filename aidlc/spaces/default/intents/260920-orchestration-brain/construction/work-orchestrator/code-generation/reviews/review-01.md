## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-23T14:00:00Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md 容量表（單一 session 的工作項最壞上界、300 個 session 的 79% 與 303 個）；aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-summary.md 第八節「容量重算」 | 所謂「最壞值」其實不是上界：進行中 8062 B 與已結束 2662 B 都以每字 3 B（中文）計算，requestText 2000 字佔 6000 B。但同一個 repo 的 session_store.py 的 MAX_ENCODED_BYTES_PER_CHAR 已承認序列化後每字最多 6 B（控制字元會變成 u00XX），而 utterance 並沒有任何控制字元過濾（brain_gateway 與 session_store 都查無）。我重算：只要把 4 B 的字元（emoji）填滿 requestText 與圖名，5 筆進行中約 52 KB、20 筆已結束約 65 KB，每 session 合計約 731,950 B，204.8 MiB 只容得下約 293.7 個 session，已低於「承諾 ≥ 300」；若是 6 B 控制字元，約 275 個。原算式的 303 對 300 只有約 1% 餘裕，所以這個假設差距足以翻轉承諾，而文件把它寫成「最壞值」並要求「調高上限前先重算」，讀者會誤以為已經是保守上界。其餘算術（93,550 B、707,950 B、303.3、79.1%）我重算皆正確。 | 二選一並寫進 DEPLOY.md 與 code-summary：（a）改以每字 6 B 重算工作項最壞值，並據此調整 5 或 20 或 200 字截斷，使 80% 的 maxmemory 仍容得下至少 300 個 session；（b）保留現行數字，但把該列改標為「中文為主的最壞值，非位元組上界」，並明寫 4 B 與 6 B 字元下的實際承載量（約 294 與約 275 個），讓 NFR4.40 的 300 個承諾被如實降級或明確接受。 | New |
| R-02 | Minor | backend/services/work_orchestrator_rules.py 第 48 至 50 行的註解；aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-generation-plan.md 第六節 Step 17；aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md 第 18 列 | 舊的容量數字仍留在三處：work_orchestrator_rules.py 註解寫「5 × 約 7.5 KiB ＋ 20 × 約 2.1 KiB ≈ 80 KiB」，而且說明這個常數是上限正本，與 DEPLOY.md 的 91.4 KiB 直接矛盾；計畫 Step 17 勾選為完成的敘述仍是「80 KiB、300 個 ≈ 199 MiB ≈ 78%」；merge-blockers 第 18 列同一格同時含舊的「≈ 349 個、176 MiB、69%」與新的 303 個、79%。DEPLOY.md 的舊值有明確標示為歷史，屬可接受，但程式註解是會被當成現況閱讀的。 | 把 work_orchestrator_rules.py 註解改為 91.4 KiB（或改成只指向 DEPLOY.md 的容量表，不再抄數字）；計畫 Step 17 與 merge-blockers 第 18 列在舊數字旁加上「已被實測取代」的標註。 | New |
| R-03 | Minor | backend/services/brain_gateway_rules.py ERROR_MESSAGES["work_capacity"]；backend/services/work_orchestrator.py dispatch 預檢（active_now ＋ 本批 > 上限） | 固定訊息是「目前進行中的工作已達 5 項」，但預檢的觸發條件是「現有進行中 ＋ 本批筆數 > 5」。計畫自己的測試情境（已有 4 筆進行中、交辦 2 個意圖）就會對使用者說「已達 5 項」，與畫面上看到的 4 項不符，使用者會以為系統壞了。 | 訊息改成不含數字的事實，例如「目前進行中的工作加上這次的交辦會超過 5 項，請等其中一項完成後再交辦」，並同步更新鎖住字串的測試。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/unit-test-instructions.md 第四之一節；.github/workflows/ci.yml | Lua 的上限檢查與終態修剪（本次合併前必修第 18 項的核心）在 CI 完全不會執行：CI 沒有 Redis 服務，單元測試走的是 ref_put_work_item／ref_update_work_item，三項 Lua 突變（MB1a、MB3a、MB4a）只被 opt-in 的 tests_redis 抓到。code-summary 第八節有如實寫出，但 unit-test-instructions 只寫「opt-in」、merge-blockers 第 18 列標為「已修正」也沒有同樣的但書，下一個人讀到這兩份會以為有閘門。 | 在 unit-test-instructions 第四之一節與 code-summary 開放項補一句「Lua 路徑只有 tests_redis 覆蓋，CI 不跑」，並列出承擔者或後續（例如 CI 加 redis 服務），不要只留在偏離揭露段。 | New |
| R-05 | Minor | backend/services/session_scripts/put_work_item.lua 第 50 行；backend/services/session_scripts/update_work_item.lua 第 53 行 | 兩支腳本都用 HGETALL 讀整個 session hash，其中包含最多 3 × 200 KiB 的對話段落，只為了篩出 5 至 25 個 wi: 欄位。每次交辦的每一筆寫入與每次轉終態都會在 Redis 單執行緒內複製約 600 KiB 並跑迴圈。規模下可接受，但容量文件已把 600 KiB 當成常態最壞值，這是可避免的成本。 | 改為 HKEYS 篩出 wi: 開頭的欄位名後再逐一 HGET，或在程式註解記載此取捨與預期的最大延遲。 | New |
| R-06 | Minor | backend/services/work_orchestrator.py correct()（約第 336 至 345 行）；code-summary.md 第八節「交接給 U14」 | 終態項被修剪後，用戶端若仍持有舊清單並對該項送 correct_work_item，會得到 WorkItemNotFound，而不是 BR55.2 對終態項的 no-op。交接段只談清單只剩 20 筆，沒有提到這個行為差異。前端以整批取代工作項清單（useBrainConnection 的 work_items 處理）所以平常不會發生，屬競態下的邊角。 | 在交接段補一句此行為，或在 correct() 對「找不到且非進行中」改為回 no-op；擇一並以測試鎖住。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 容量算式手算（5 × 8062 ＋ 20 × 2662、600 KiB、256 MiB 的 80%） | 93,550 B；707,950 B；303.3 個；300 個 ≈ 79.1% | 算術本身正確，與 DEPLOY.md、兩份 .env.example、compose、LOCAL-DEV、session_store 註解一致；問題在每字位元組假設（R-01） |
| 舊數字掃描（349、176 MiB、69%、199 MiB、78%、80 KiB） | DEPLOY.md 的舊值皆明標為歷史；work_orchestrator_rules.py 與 merge-blockers 第 18 列仍有舊值 | 見 R-02 |
| Lua 與 ref 參考實作逐行對照（put、update、ARGV 順序、終態集合、createdAt 與欄位名排序、排除剛轉終態者） | 語意一致；ARGV 位置與 ref 參數順序一致；終態數在所有轉終態路徑上收斂至 20 以內（唯一寫入口為 WorkOrchestrator._cas，七處呼叫皆經它）；舊資料超量時一次修剪到位 | 未發現分歧；Lua 本身 CI 不執行（R-04） |
| 依賴者與復原掃描對照（修剪終態項是否破壞等待中的項） | 進行中與等待中從不被刪；_advance_dependents 以傳入的 item 為準，不依賴 store 內是否仍有被等待者；只有「推進前行程中斷且之後又累積 20 筆」才會讓 _recover 把缺席的被等待者視為失敗 | 「已知限制」段的描述準確，且失敗方向安全（不誤執行） |
| 原子性與半批殘留（dispatch 預檢、_abandon_batch） | 迴圈內無 await，單行程內不會交錯；跨行程由 Lua 擋下；已寫入項經 _cas 轉失敗，未 _start；比對失敗只記 WARNING，殘留的處理中項仍有 deadlineAt 由 _recover 收斂 | 未發現半批仍在執行的路徑 |
| requestText 讀取點掃描 | 僅 work_orchestrator.py 三處（建立、進行中的架構請求、變更摘要），皆使用記憶體內快照，無終態後再讀取 store 全文者 | 截斷安全 |

### Summary

本輪對 Lua 與參考實作的語意、轉終態修剪的收斂性、整批預檢與併發回滾、requestText 截斷落點都未找到會導致錯誤的缺陷，已知限制的敘述也準確。唯一值得在核可前權衡的是容量「最壞值」的位元組假設：以每字 3 B 計算，但 repo 自己承認最壞是每字 6 B，且 4 B 的 emoji 就足以讓約 1% 餘裕的「≥ 300 個 session」承諾落到約 294 個，應在核可前改正算式或把承諾如實降級。其餘為文件殘留、訊息準確性與 CI 覆蓋的揭露問題。
