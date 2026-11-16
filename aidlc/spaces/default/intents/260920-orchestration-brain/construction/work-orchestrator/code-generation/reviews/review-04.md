## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-05 | Fixed | Minor | 兩支 Lua 的 HGETALL 前已補取捨註解（put_work_item.lua 第 50 至 62 行、update_work_item.lua 第 53 至 63 行）。git diff 兩檔共新增 24 行，全為 Lua 註解行，演算法、回傳值、ARGV 介面未動。註解內容與行為一致：update 的 HGETALL 在 prune_terminal 內，而 prune_terminal 只在 run() 的 not was_terminal and terminal[item.status] 分支被呼叫（update_work_item.lua 第 124 至 126 行），所以「只在非終態轉終態那一次掃」成立，且更正了第 36 列原文「每次寫入」的說法。put 每次建項確實都掃。註解只指向 DEPLOY.md 容量表而未抄數字，沒有第二份數字漂移的風險。 |
| R-08 | Fixed | Minor | tests_redis/test_work_item_lua.py 第 252 行新增 test_cjson_encoded_size_matches_real_cjson_encode，以 EVAL 執行 string.len(cjson.encode(cjson.decode(ARGV[1])))，12 組輸入各自 subTest 與 T.cjson_encoded_size 比對；沿用該類別既有 skipIf，規格註解五項齊全。突變推演：M3 拿掉斜線加項時 slash、nested、work_item 三組必然長度不一致；M4 拿掉 DEL 加項時 del、nested、work_item 三組必然不一致，案例能失敗。DEPLOY.md 第 1931 至 1934 行已有「Redis 大版本升級後必須重跑」附註，滿足第二半要求，但見新發現 2。 |
| R-09 | Fixed | Minor | code-summary.md 本輪第四節第 1 點已寫出準確措辭：查無識別碼已有測試（flow 第 433 行，test_correct_is_a_no_op_on_terminal_items_and_rejects_unknown_ids 自第 426 行起），缺的是修剪後再送停掉的專屬案例，並指向新案第 441 行。merge-blockers 第 36 列同樣用此措辭。原文依計畫不刪改。殘留問題見新發現 1。 |
| R-10 | Fixed | Minor | 本輪第四節第 2 點已把「必為子集」更正為「無法證明為子集，故另以逐行重讀與重算補強」，並說明前輪確實逐行重讀重算。原文第 377 行依計畫保留。殘留問題見新發現 1。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/work-orchestrator/code-generation/code-summary.md 第八節「交接給 U14」2026-10-31 補記（第 338 行）與前輪第一節（第 377 行） | 兩處被更正的原句仍原樣留在原位，且原位沒有任何指向更正的標記。第 338 行仍寫「此行為未以測試鎖住」，第 377 行仍寫「必為其子集」。只讀第八節或只讀前輪第一節的人看不到更正（更正在檔案最末本輪第四節），仍會帶走已知不實的說法。這是計畫要求「不刪改原文」的直接代價。 | 在兩處原句後各追加一句不刪原文的指引，例如「（2026-11-08 更正見本檔『合併前必修第 36 列』第四節）」。 |
| Minor | DEPLOY.md 第 1931 至 1934 行（R-08 第二半的承載處） | R-08 要求的「升級 Redis 大版本須重跑」附註是工作樹內未 commit 的改動（git show HEAD:DEPLOY.md 無此段），由第 34 列處理時加入，本輪未改 DEPLOY.md。若第 34 列的 DEPLOY.md 變更與本單元不同批合併或被回退，R-08 的文件那一半會無聲消失，而本單元的紀錄與 merge-blockers 第 36 列卻宣稱已涵蓋。 | 在合併前確認 DEPLOY.md 該段與本單元的新測試案同批進入；或在 merge-blockers 第 36 列註明 (c) 的文件部分依賴第 34 列 DEPLOY.md 變更同批合併。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| git diff（兩支 Lua） | 兩檔 +13、+11，皆 `-- ` 註解行；HGETALL 行本身未動（put 第 63 行、update 第 64 行） | 確認只補註解 |
| 收據 shasum 比對（reviewed-source-6a096499e51a.tsv，30 檔） | 19 檔相同、11 檔不同 | 與 code-summary 七之二「19 相同／4 本輪／7 他列」逐檔吻合：本輪 4 檔為兩支 Lua、flow 測試、tests_redis 測試；他列 7 檔為 session_store.py、hierarchy_facade.py、DEPLOY.md、LOCAL-DEV.md、兩份 .env.example、docker-compose.deploy.yml |
| 收據與 HEAD 雜湊（session_store.py、hierarchy_facade.py、兩支 Lua） | 收據雜湊等於 HEAD；現況不同 | 以 git diff HEAD 作為「收據之後的改動」基準有效；session_store.py 的 +16／-2 為 role 長度上限與 docstring 更正，與工作項方法無涉 |
| 計畫 git diff | 只有 Step 17 勾選字元與新增的 §六之二、§六之三；全檔 29 已勾、0 未勾 | 內文未被改動；勾回有依據（沒有任何一格的證據檔變動到影響其結論） |
| 讀碼推演 M1、M2（flow 新案） | M1 拿掉替身修剪路徑則第 21 項後 before 含 21 筆，assertNotIn 與長度斷言失敗；M2 讓 correct 查無時不拋，assertRaises 失敗 | 案能失敗；修剪走真實轉終態路徑（dispatch、drain、_cas、update_work_item），未手刪欄位；先斷言最舊項在第 20 項時仍存在，排除空洞通過；dispatch 不對 turn_id 去重、FakeClock 推進 1 秒使建立時間可排序 |
| 規格註解與案名 | 兩新案 @purpose、@given、@step、@pass、@story 齊全；既有案名未改 | 符合 Mandated 必做 3b |
| 行號核對 | flow 第 441 行、tests_redis 第 252 行、work_orchestrator.py 第 338 至 340 行、brain_gateway_rules.py 第 311 行、DEPLOY.md 第 1931 行皆吻合 | 引用定位正確 |
| 測試、validator 執行 | 未執行（遵守唯讀限制） | 242／72／67 與四項突變的實跑結果只能依據開發者紀錄，本審查以讀碼推演補強，未獨立重跑 |

### Summary

第 36 列 (a) 至 (d) 皆如實完成：Lua 只增註解且註解與行為相符，兩個新測試案以讀碼推演確認能失敗，22 格重判的分類與勾回有收據雜湊與 git 基準支撐，R-05、R-08、R-09、R-10 皆判為 Fixed。僅留兩項 Minor 紀錄面問題（更正未在原句位置留指引、DEPLOY.md 附註依賴他列的未 commit 改動），不阻擋。

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

> R-05 Not re-checked this round

> R-08 Not re-checked this round

> R-09 Not re-checked this round

> R-10 Not re-checked this round
