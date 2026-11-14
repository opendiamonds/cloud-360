## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-26T00:51:48Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md 容量表（單一 session 的工作項最壞上界、300 個 session 的 79% 與 303 個）；aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-summary.md 第八節「容量重算」 | 所謂「最壞值」其實不是上界：進行中 8062 B 與已結束 2662 B 都以每字 3 B（中文）計算，requestText 2000 字佔 6000 B。但同一個 repo 的 session_store.py 的 MAX_ENCODED_BYTES_PER_CHAR 已承認序列化後每字最多 6 B（控制字元會變成 u00XX），而 utterance 並沒有任何控制字元過濾（brain_gateway 與 session_store 都查無）。我重算：只要把 4 B 的字元（emoji）填滿 requestText 與圖名，5 筆進行中約 52 KB、20 筆已結束約 65 KB，每 session 合計約 731,950 B，204.8 MiB 只容得下約 293.7 個 session，已低於「承諾 ≥ 300」；若是 6 B 控制字元，約 275 個。原算式的 303 對 300 只有約 1% 餘裕，所以這個假設差距足以翻轉承諾，而文件把它寫成「最壞值」並要求「調高上限前先重算」，讀者會誤以為已經是保守上界。其餘算術（93,550 B、707,950 B、303.3、79.1%）我重算皆正確。 | 二選一並寫進 DEPLOY.md 與 code-summary：（a）改以每字 6 B 重算工作項最壞值，並據此調整 5 或 20 或 200 字截斷，使 80% 的 maxmemory 仍容得下至少 300 個 session；（b）保留現行數字，但把該列改標為「中文為主的最壞值，非位元組上界」，並明寫 4 B 與 6 B 字元下的實際承載量（約 294 與約 275 個），讓 NFR4.40 的 300 個承諾被如實降級或明確接受。 | Resolved (reviewer) |
| R-02 | Minor | backend/services/work_orchestrator_rules.py 第 48 至 50 行的註解；aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-generation-plan.md 第六節 Step 17；aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md 第 18 列 | 舊的容量數字仍留在三處：work_orchestrator_rules.py 註解寫「5 × 約 7.5 KiB ＋ 20 × 約 2.1 KiB ≈ 80 KiB」，而且說明這個常數是上限正本，與 DEPLOY.md 的 91.4 KiB 直接矛盾；計畫 Step 17 勾選為完成的敘述仍是「80 KiB、300 個 ≈ 199 MiB ≈ 78%」；merge-blockers 第 18 列同一格同時含舊的「≈ 349 個、176 MiB、69%」與新的 303 個、79%。DEPLOY.md 的舊值有明確標示為歷史，屬可接受，但程式註解是會被當成現況閱讀的。 | 把 work_orchestrator_rules.py 註解改為 91.4 KiB（或改成只指向 DEPLOY.md 的容量表，不再抄數字）；計畫 Step 17 與 merge-blockers 第 18 列在舊數字旁加上「已被實測取代」的標註。 | Resolved (reviewer) |
| R-03 | Minor | backend/services/brain_gateway_rules.py ERROR_MESSAGES["work_capacity"]；backend/services/work_orchestrator.py dispatch 預檢（active_now ＋ 本批 > 上限） | 固定訊息是「目前進行中的工作已達 5 項」，但預檢的觸發條件是「現有進行中 ＋ 本批筆數 > 5」。計畫自己的測試情境（已有 4 筆進行中、交辦 2 個意圖）就會對使用者說「已達 5 項」，與畫面上看到的 4 項不符，使用者會以為系統壞了。 | 訊息改成不含數字的事實，例如「目前進行中的工作加上這次的交辦會超過 5 項，請等其中一項完成後再交辦」，並同步更新鎖住字串的測試。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/unit-test-instructions.md 第四之一節；.github/workflows/ci.yml | Lua 的上限檢查與終態修剪（本次合併前必修第 18 項的核心）在 CI 完全不會執行：CI 沒有 Redis 服務，單元測試走的是 ref_put_work_item／ref_update_work_item，三項 Lua 突變（MB1a、MB3a、MB4a）只被 opt-in 的 tests_redis 抓到。code-summary 第八節有如實寫出，但 unit-test-instructions 只寫「opt-in」、merge-blockers 第 18 列標為「已修正」也沒有同樣的但書，下一個人讀到這兩份會以為有閘門。 | 在 unit-test-instructions 第四之一節與 code-summary 開放項補一句「Lua 路徑只有 tests_redis 覆蓋，CI 不跑」，並列出承擔者或後續（例如 CI 加 redis 服務），不要只留在偏離揭露段。 | Resolved (reviewer) |
| R-05 | Minor | backend/services/session_scripts/put_work_item.lua 第 50 行；backend/services/session_scripts/update_work_item.lua 第 53 行 | 兩支腳本都用 HGETALL 讀整個 session hash，其中包含最多 3 × 200 KiB 的對話段落，只為了篩出 5 至 25 個 wi: 欄位。每次交辦的每一筆寫入與每次轉終態都會在 Redis 單執行緒內複製約 600 KiB 並跑迴圈。規模下可接受，但容量文件已把 600 KiB 當成常態最壞值，這是可避免的成本。 | 改為 HKEYS 篩出 wi: 開頭的欄位名後再逐一 HGET，或在程式註解記載此取捨與預期的最大延遲。 | Unresolved |
| R-06 | Minor | backend/services/work_orchestrator.py correct()（約第 336 至 345 行）；code-summary.md 第八節「交接給 U14」 | 終態項被修剪後，用戶端若仍持有舊清單並對該項送 correct_work_item，會得到 WorkItemNotFound，而不是 BR55.2 對終態項的 no-op。交接段只談清單只剩 20 筆，沒有提到這個行為差異。前端以整批取代工作項清單（useBrainConnection 的 work_items 處理）所以平常不會發生，屬競態下的邊角。 | 在交接段補一句此行為，或在 correct() 對「找不到且非進行中」改為回 no-op；擇一並以測試鎖住。 | Unresolved |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/traceability.json（第 392 至 398 行附近的容量條目）；code-generation-plan.md Step 17 | 計畫 Step 17 未勾選，code-summary「重做」段也承認 `traceability.json` 沒有新增 `backend/tests/test_work_orchestrator_capacity.py`（8 案，承接位元組上界與 NFR4.40 的 300 個承諾）的條目，且「已由其他測試檔條目覆蓋」是未逐一核對的說法。該測試檔目前還是 git 未追蹤。容量承諾的唯一機械守門員因此不在追溯表上，也可能漏進 commit。 | 在 `traceability.json` 補上對應位元組上界與 300 個承諾的需求識別字到該測試檔的條目，勾選 Step 17；commit 時確認該測試檔已加入。 | New |
| R-08 | Minor | backend/services/session_types.py `cjson_encoded_size`；backend/tests/test_work_orchestrator_capacity.py | 整個容量上界建立在 Python 的 `cjson_encoded_size` 與 Redis 內建 cjson 的 `cjson.encode` 逐位元組相同。我實測 400 組字串確認一致，但 CI 只比對 Python 對 Python，這個等價性目前只靠 `tests_redis`（opt-in、不在 CI）與一次性手動量測守住。若 Redis 升級改了跳脫行為（例如對 U+2028 的處理），位元組上界會無聲失準，而 DEPLOY.md 只有約 2.9% 餘裕。 | 在 `tests_redis` 增一案，以真實 `cjson.encode` 量對抗字元集合並與 `cjson_encoded_size` 比對；並在 DEPLOY.md 容量表註明升級 Redis 大版本時要重跑該案。 | New |

> R-01 Reviewer note: 已改以序列化後位元組封頂：`work_orchestrator_rules.py` 的 `REQUEST_TEXT_MAX_BYTES=6000`、`TERMINAL_REQUEST_TEXT_MAX_BYTES=300`、`DIAGRAM_TITLE_MAX_BYTES=300`、`WORK_ITEM_ACTIVE_MAX_BYTES=7_800`、`WORK_ITEM_TERMINAL_MAX_BYTES=2_100`。我重算 DEPLOY.md 容量表：5×7800＋20×2100＝81,000 B，加 614,400 B 為 695,400 B，214,748,364÷695,400≈308.8，300 個佔 77.7%，皆正確。對抗字元（6 B 控制字元、4 B emoji、2 B 斜線）測試 `test_work_orchestrator_capacity.py` 通過。我另用一次性本機 Redis 8.8.0（127.0.0.1:6397，不存檔，已關閉並刪除）對 400 組隨機字串（含 U+0000 至 U+10FFFF 邊界、U+2028、U+2029、DEL）比對 `string.len(cjson.encode(...))` 與 Python `cjson_encoded_size`，零差異。舊值已在 DEPLOY.md 標為被取代。

> R-02 Reviewer note: `work_orchestrator_rules.py` 註解不再抄數字，改指向 DEPLOY.md 容量表與位元組上界段；merge-blockers 第 18 列已加「本段的數字取代本格前文所有容量數字」與已被取代的數字清單。計畫 Step 17 的文字（80 KiB、約 199 MiB、約 78%）與新值（79.1 KiB、199.0 MiB、77.7%）只差四捨五入，且 Step 17 尚未勾選，不再構成矛盾。

> R-03 Reviewer note: `ERROR_MESSAGES["work_capacity"]` 已改為「同時進行中的工作最多 5 項，這次交辦會超過上限，請等其中一項完成後再交辦。」，不含現況數字；`test_brain_gateway_rules` 與 `test_brain_gateway_turn` 通過。

> R-04 Reviewer note: unit-test-instructions 開頭已寫明真實原子性只由 `tests_redis` 承擔、`ci.yml` 的 backend job 沒有 Redis 服務、不在 CI；merge-blockers 第 18 列也標了「opt-in、不在 CI」。承擔者仍是本機 opt-in，但已如實揭露，不會被讀成有閘門。

> R-05 Reviewer note: `put_work_item.lua` 第 50 行與 `update_work_item.lua` 第 53 行仍用 `HGETALL` 讀整個 hash（含最多 3×200 KiB 的對話段落），只為了篩 `wi:` 欄位；程式註解也沒有記載此取捨。容量文件仍把 600 KiB 當成常態最壞值，所以每次交辦與每次轉終態都在 Redis 單執行緒內複製約 600 KiB。

> R-06 Reviewer note: `work_orchestrator.py` `correct()` 對已被修剪的終態項仍拋 `WorkItemNotFound`，不是 no-op；code-summary 第七節交接 U13 只寫「`WorkItemNotFound` 對應 `INVALID_REQUEST`」，沒有說明「用戶端持有舊清單、對已被修剪的項送出停掉」會得到錯誤而不是靜默忽略。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `unittest`（work_orchestrator 的 store、capacity、flow、rules、model、authz、boundaries、capabilities，加 brain_gateway_rules、brain_gateway_turn、session_contract，共 194 案） | OK | 本單元與跨單元新增項在替身上全綠。 |
| `tests_redis.test_work_item_lua`（一次性本機 Redis 8.8.0，只綁 127.0.0.1，未存檔，已關閉並刪除） | 7 OK | 兩支 Lua 的上限與終態修剪與參考實作逐案一致；R-01 的位元組量測與真實 cjson 一致。 |
| source-manifest.json 列出的 33 個路徑 | 全部存在 | 先前漏列的容量測試檔已補列。 |

### Summary

前輪唯一的 Major（容量「最壞值」其實不是上界）已確實修正：改以序列化後位元組封頂，算式經我重算正確，且與真實 Redis 的 cjson 逐位元組一致；R-02 至 R-04 也已處理。仍開著的是兩個 Minor（兩支 Lua 的 HGETALL 成本、`correct()` 對被修剪項的行為未交接）以及兩個新的 Minor（容量測試檔未進追溯表且 Step 17 未勾選、cjson 等價性不在 CI）。無 Critical 與 Major，可以放行。
