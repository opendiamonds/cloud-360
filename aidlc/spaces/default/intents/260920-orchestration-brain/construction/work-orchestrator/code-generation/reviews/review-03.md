## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | DEPLOY.md 容量表（單一 session 的工作項最壞上界、300 個 session 的 79% 與 303 個）；aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-summary.md 第八節「容量重算」 | 所謂「最壞值」其實不是上界：進行中 8062 B 與已結束 2662 B 都以每字 3 B（中文）計算，requestText 2000 字佔 6000 B。但同一個 repo 的 session_store.py 的 MAX_ENCODED_BYTES_PER_CHAR 已承認序列化後每字最多 6 B（控制字元會變成 u00XX），而 utterance 並沒有任何控制字元過濾（brain_gateway 與 session_store 都查無）。我重算：只要把 4 B 的字元（emoji）填滿 requestText 與圖名，5 筆進行中約 52 KB、20 筆已結束約 65 KB，每 session 合計約 731,950 B，204.8 MiB 只容得下約 293.7 個 session，已低於「承諾 ≥ 300」；若是 6 B 控制字元，約 275 個。原算式的 303 對 300 只有約 1% 餘裕，所以這個假設差距足以翻轉承諾，而文件把它寫成「最壞值」並要求「調高上限前先重算」，讀者會誤以為已經是保守上界。其餘算術（93,550 B、707,950 B、303.3、79.1%）我重算皆正確。 | 二選一並寫進 DEPLOY.md 與 code-summary：（a）改以每字 6 B 重算工作項最壞值，並據此調整 5 或 20 或 200 字截斷，使 80% 的 maxmemory 仍容得下至少 300 個 session；（b）保留現行數字，但把該列改標為「中文為主的最壞值，非位元組上界」，並明寫 4 B 與 6 B 字元下的實際承載量（約 294 與約 275 個），讓 NFR4.40 的 300 個承諾被如實降級或明確接受。 | Resolved (reviewer) |
| R-02 | Minor | backend/services/work_orchestrator_rules.py 第 48 至 50 行的註解；aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-generation-plan.md 第六節 Step 17；aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md 第 18 列 | 舊的容量數字仍留在三處：work_orchestrator_rules.py 註解寫「5 × 約 7.5 KiB ＋ 20 × 約 2.1 KiB ≈ 80 KiB」，而且說明這個常數是上限正本，與 DEPLOY.md 的 91.4 KiB 直接矛盾；計畫 Step 17 勾選為完成的敘述仍是「80 KiB、300 個 ≈ 199 MiB ≈ 78%」；merge-blockers 第 18 列同一格同時含舊的「≈ 349 個、176 MiB、69%」與新的 303 個、79%。DEPLOY.md 的舊值有明確標示為歷史，屬可接受，但程式註解是會被當成現況閱讀的。 | 把 work_orchestrator_rules.py 註解改為 91.4 KiB（或改成只指向 DEPLOY.md 的容量表，不再抄數字）；計畫 Step 17 與 merge-blockers 第 18 列在舊數字旁加上「已被實測取代」的標註。 | Resolved (reviewer) |
| R-03 | Minor | backend/services/brain_gateway_rules.py ERROR_MESSAGES["work_capacity"]；backend/services/work_orchestrator.py dispatch 預檢（active_now ＋ 本批 > 上限） | 固定訊息是「目前進行中的工作已達 5 項」，但預檢的觸發條件是「現有進行中 ＋ 本批筆數 > 5」。計畫自己的測試情境（已有 4 筆進行中、交辦 2 個意圖）就會對使用者說「已達 5 項」，與畫面上看到的 4 項不符，使用者會以為系統壞了。 | 訊息改成不含數字的事實，例如「目前進行中的工作加上這次的交辦會超過 5 項，請等其中一項完成後再交辦」，並同步更新鎖住字串的測試。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/unit-test-instructions.md 第四之一節；.github/workflows/ci.yml | Lua 的上限檢查與終態修剪（本次合併前必修第 18 項的核心）在 CI 完全不會執行：CI 沒有 Redis 服務，單元測試走的是 ref_put_work_item／ref_update_work_item，三項 Lua 突變（MB1a、MB3a、MB4a）只被 opt-in 的 tests_redis 抓到。code-summary 第八節有如實寫出，但 unit-test-instructions 只寫「opt-in」、merge-blockers 第 18 列標為「已修正」也沒有同樣的但書，下一個人讀到這兩份會以為有閘門。 | 在 unit-test-instructions 第四之一節與 code-summary 開放項補一句「Lua 路徑只有 tests_redis 覆蓋，CI 不跑」，並列出承擔者或後續（例如 CI 加 redis 服務），不要只留在偏離揭露段。 | Resolved (reviewer) |
| R-05 | Minor | backend/services/session_scripts/put_work_item.lua 第 50 行；backend/services/session_scripts/update_work_item.lua 第 53 行 | 兩支腳本都用 HGETALL 讀整個 session hash，其中包含最多 3 × 200 KiB 的對話段落，只為了篩出 5 至 25 個 wi: 欄位。每次交辦的每一筆寫入與每次轉終態都會在 Redis 單執行緒內複製約 600 KiB 並跑迴圈。規模下可接受，但容量文件已把 600 KiB 當成常態最壞值，這是可避免的成本。 | 改為 HKEYS 篩出 wi: 開頭的欄位名後再逐一 HGET，或在程式註解記載此取捨與預期的最大延遲。 | Unresolved |
| R-06 | Minor | backend/services/work_orchestrator.py correct()（約第 336 至 345 行）；code-summary.md 第八節「交接給 U14」 | 終態項被修剪後，用戶端若仍持有舊清單並對該項送 correct_work_item，會得到 WorkItemNotFound，而不是 BR55.2 對終態項的 no-op。交接段只談清單只剩 20 筆，沒有提到這個行為差異。前端以整批取代工作項清單（useBrainConnection 的 work_items 處理）所以平常不會發生，屬競態下的邊角。 | 在交接段補一句此行為，或在 correct() 對「找不到且非進行中」改為回 no-op；擇一並以測試鎖住。 | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/traceability.json（第 392 至 398 行附近的容量條目）；code-generation-plan.md Step 17 | 計畫 Step 17 未勾選，code-summary「重做」段也承認 `traceability.json` 沒有新增 `backend/tests/test_work_orchestrator_capacity.py`（8 案，承接位元組上界與 NFR4.40 的 300 個承諾）的條目，且「已由其他測試檔條目覆蓋」是未逐一核對的說法。該測試檔目前還是 git 未追蹤。容量承諾的唯一機械守門員因此不在追溯表上，也可能漏進 commit。 | 在 `traceability.json` 補上對應位元組上界與 300 個承諾的需求識別字到該測試檔的條目，勾選 Step 17；commit 時確認該測試檔已加入。 | Resolved (reviewer) |
| R-08 | Minor | backend/services/session_types.py `cjson_encoded_size`；backend/tests/test_work_orchestrator_capacity.py | 整個容量上界建立在 Python 的 `cjson_encoded_size` 與 Redis 內建 cjson 的 `cjson.encode` 逐位元組相同。我實測 400 組字串確認一致，但 CI 只比對 Python 對 Python，這個等價性目前只靠 `tests_redis`（opt-in、不在 CI）與一次性手動量測守住。若 Redis 升級改了跳脫行為（例如對 U+2028 的處理），位元組上界會無聲失準，而 DEPLOY.md 只有約 2.9% 餘裕。 | 在 `tests_redis` 增一案，以真實 `cjson.encode` 量對抗字元集合並與 `cjson_encoded_size` 比對；並在 DEPLOY.md 容量表註明升級 Redis 大版本時要重跑該案。 | Unresolved |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-summary.md 第八節「交接給 U14」下 2026-10-31 補記 | 補記寫「此行為未以測試鎖住」。實際上 test_work_orchestrator_flow.py 第 426 至 433 行的 test_correct_is_a_no_op_on_terminal_items_and_rejects_unknown_ids 已斷言「查無識別碼即拋 WorkItemNotFound」；沒有的只是「先被修剪、再送 correct」這個情境的專屬案例。說法過頭，會讓下一位讀者以為該錯誤路徑完全無測試 | 把這句改成「查無識別碼拋 WorkItemNotFound 已有測試（flow:433），缺的是修剪後再送 correct 的專屬案例」，或在併入 merge-blockers 時用同樣的準確措辭 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-summary.md 本輪第一節「變動檔判定」的超集論證 | 論證寫「收據之後的改動必為 git diff 624c170 7a50a40 的子集」。收據當下的 DEPLOY.md（雜湊 2608a131）不在任何 git 版本內，所以收據中曾存在、後來被移除而從未進過 git 的文字不會出現在該 diff，子集說法嚴格來說證不出來。這點不影響結論，因為開發者同時逐行重讀並重算了容量段（我獨立重算：81,000 B、695,400 B、308.8、199.0 MiB、77.7% 全部相符，常數 5／20／6000／300／300／7,800／2,100 與 session_types.py:220 的 200 KiB 一致），但文字上把「子集」寫成了已證事實 | 把「必為子集」改為「無法證明為子集，故另以逐行重讀與重算補強」，其餘不動 | New |

> R-05 Reviewer note: put_work_item.lua 第 50 行與 update_work_item.lua 第 53 行仍是 HGETALL，兩檔仍無取捨註解。本輪未改程式，開發者已如實列為已知限制；merge-blockers.md 第 18 列已揭露「規模下接受，未改」，但沒有指定承擔者。不阻擋

> R-06 Reviewer note: 交接段已就地補記：已修剪的終態項送停掉會收到 WorkItemNotFound（work_orchestrator.py 第 338 至 340 行拋出，第 341 至 342 行才是終態 no-op；閘道對到「找不到這個工作項」，brain_gateway_rules.py 第 277、310 至 311 行），行號我逐一核對無誤。找不到項目就拋 WorkItemNotFound 這條路徑已由 test_work_orchestrator_flow.py 第 426 至 433 行（未知識別碼）鎖住，審查要求的「補一句交接」已達成

> R-07 Reviewer note: traceability.json 已新增 CG-MB18-BYTE-BOUND，指向 backend/tests/test_work_orchestrator_capacity.py；該檔 git ls-files 可列出；Step 17 已勾；該檔 8 個 test 方法與條目寫的 8 案相符

> R-08 Reviewer note: tests_redis/test_work_item_lua.py 仍只有 7 個 test 方法（第 123、136、146、162、201、216、267 行），沒有以真實 cjson.encode 比對 cjson_encoded_size 的案例；DEPLOY.md 第 1829、1833 行只提到 cjson，沒有 Redis 大版本升級須重跑的註記。merge-blockers.md 第 18 列與第 34 列都沒涵蓋（第 34 列 (g) 談的是 DEPLOY.md:1824 的 308.8 個要標下界，不同件）。不阻擋

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 收據 30 列逐檔 sha256（reviewed-source-2324b6d9533e.tsv，自行重算） | 只有 DEPLOY.md 不同（2608a131 對 d9b0571c），其餘 29 列相同；較新的 reviewed-source-6a096499e51a.tsv 與舊檔只差 DEPLOY.md 那一列 | 證實開發者宣稱的變動範圍；「讀整段 diff 取超集」在收據版本不可重建時是合理做法，且有直接重算補強，判斷站得住 |
| git diff 624c170 7a50a40 -- DEPLOY.md 全部 hunk | 與工作項相關的新增文字全落在容量段（約 1799 至 1880 行）；其餘 hunk 屬其他單元 | 與開發者分類一致 |
| 11 模組（我的副本，-B -P，無 REDIS_URL） | Ran 241，OK，skipped=3，0 失敗 0 錯誤 | 與宣稱相符 |
| 額外 4 模組（capacity、brain_gateway_rules、brain_gateway_turn、redis_gateway_noscript） | Ran 72，OK | 與宣稱相符 |
| tests_redis 真實 Lua 案例 | 未執行（需要 Redis，不連任何 Redis） | 兩支 Lua、session_types.py 與該測試檔自收據後逐位元相同，沿用 10-26 紀錄；可接受 |
| 計畫勾選格 | grep 實算已勾 22、未勾 0；對 HEAD 的計畫差異只有 Step 17 勾選與新增的六之二，內文未被改動 | 與宣稱相符；Step 17 的容量句字面（80 KiB、約 199 MiB、約 78%）對現況是四捨五入前的舊估計，已由 review-02 R-02 判定不構成矛盾 |
| traceability.json | 合法 JSON；reverse 11 條、coverage 49 條；新條目與兩條更正 note 指向的檔與行（rules.py:71-87、brain_gateway_rules.py:282）皆存在且內容相符 | 通過 |
| code-summary 行號與數字抽查 | HGETALL 兩處、work_orchestrator.py:338-342、brain_gateway_rules.py:277/281/282/310-314、rules.py 常數行、session_types.py:220、DEPLOY.md:1855、LOCAL-DEV.md:360-362、兩份 .env.example、compose:266-268、merge-blockers.md:27 與 :43、source-manifest.json:43 | 全部正確 |
| validate_repo_contract.py、validate_env_contract.py | 兩者皆 passed | 通過 |

### Summary

本輪只是重新驗證與紀錄補記，沒有改程式；收據失效只因共用檔 DEPLOY.md 的非本單元 hunk，容量段與程式常數逐項重算一致，測試數與開發者宣稱完全相符，22 格勾選皆有證據。三項需併入 merge-blockers 的限制（R-05、R-06 測試那一半、R-08 與 DEPLOY 升級註記）與既有第 18、34 列的對應判斷正確。新發現只有兩個措辭層級的 Minor，無 Critical、無 Major，故 READY。
