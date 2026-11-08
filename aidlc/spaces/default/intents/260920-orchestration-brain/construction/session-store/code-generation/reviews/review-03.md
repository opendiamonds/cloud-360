## Review
**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/session_store.py > `set_work_target`（`_ensure_meta` 之後的 `hset_fields_and_expire`）、`_ensure_meta` 的 `EXISTS` 快速路徑 | 交易保證了「寫入與 TTL 同進同退」，但沒有處理「key 在 `_ensure_meta` 的 `EXISTS` 為真之後、`set_work_target` 的交易之前剛好到期」這個窗口：交易會重建一個**只有 `tgt:<seg>`、沒有 `meta` 與 `seg:shared`** 的 key，並替它設 TTL。之後每次呼叫 `_ensure_meta` 看到 `EXISTS` 為真就跳過，不會補建；`decode_session` 對沒有 blob 的段直接 `continue`，於是這個 session 在剩餘 24 小時內都沒有 `shared` 段，與 `EC1`「segments 必含 shared」不符。機率極低（需在 TTL 邊界的毫秒窗口），也比修正前（永不過期的殘缺 key）好得多，但「TTL 剛過期被重建」正是第 12 項要處理的情境，這一半只做到有 TTL、沒做到完整。 | 二擇一並寫進程式註解：（1）`set_work_target` 的交易內以 `only_if_absent` 形式另附 `meta` 與 `seg:shared` 的預設值（HSETNX 對已存在的欄位是 no-op）；或（2）在 `code-summary.md` 第九節開放項明列「到期邊界會重建殘缺 key」為已知殘留與其後果，不要讓文件讀起來像已完全關閉。 | Resolved (reviewer) |
| R-02 | Minor | backend/services/session_store.py > `SessionStore.__init__` 的 `worst_single` 算式、`append_message` 的參數檢查 | 「單則訊息不可能超過每段 200 KB」的證明用 `MESSAGE_ENVELOPE_RESERVE_BYTES = 1024` 假設 `role` 很短（註解寫「由 U13 依對話協定給值」），但 `append_message` 對 `role` 只檢查非空，沒有長度或集合限制。若呼叫端傳入很長的 `role`，單則可超過上限；Lua 迴圈在剩一則時停止，會保留一個超限的段——而上限的整個目的是封住容量。建構時的算式檢查因此只證明了「`text` 部分」。 | 在 `append_message` 入口對 `role` 加長度上限（或限定為對話協定的封閉集合），讓 `MESSAGE_ENVELOPE_RESERVE_BYTES` 的假設由程式強制而不是由註解承諾；補一個對應的拒絕測試。 | Unresolved |
| R-03 | Minor | backend/services/session_scripts/append_message.lua > 修剪前的 `for i = 1, #arr` 迴圈；code-summary.md「新測試」「未驗項」 | 每次追加現在多做一輪對**全部既有訊息**的 `cjson.encode`（段滿時約 200 KB），加上原本的 decode 與最後整段 encode，腳本成本約為原本的兩到三倍。Redis 單執行緒，腳本期間阻塞其他所有指令；`NFR3.40` 的 P95 20 ms 與連線池算式（300 RPS）都沒有把這個成本算進去，產出也沒有任何量測。這不是正確性問題，也很可能在餘裕之內，但沒有數字。 | 在本機臨時 Redis 對「段已滿 200 KB」的狀態量一次 `EVAL` 耗時（實作方已有該環境），把數字寫進 code-summary；若接近毫秒級以上，改為只重新編碼新訊息並沿用既有訊息的位元組長度（例如修剪前先量原字串再加新訊息）。 | Unresolved |
| R-04 | Minor | backend/tests/test_session_store_behaviour.py > `RealRedisParityTest`；.github/workflows/ci.yml | 第 18 項的生產載體是 Lua 迴圈，而它在 CI 中只被兩條字串斷言（`while #arr > 1 and (#arr > cap or total > max_bytes) do`、`string.len(cjson.encode(arr[i]))`）覆蓋；位元組算式的 off-by-one（例如逗號數、剩一則的邊界）在 CI 不會變紅，M18L 突變也只由靜態斷言抓到。產出已如實記載這個限制，且與 `tests_redis/` 先例一致，故不阻擋；但這是本站唯一真正強制容量上界的程式碼。 | 在 code-summary 的開放項登記「CI 無 Redis，Lua 位元組修剪只有本機 opt-in 驗證」並指派承接站（build-and-test 或 CI 加 Redis service container）；staging 首次部署時以 app 身分跑一次含長訊息的 `EVAL` 並記錄結果。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/session-store/nfr-design/performance-design.md:68-69、infrastructure-design/infrastructure-specification.md:10；code-summary.md 第九節 | 移除 `POOL_MIN_SIZE`／`POOL_IDLE_TIMEOUT_SECONDS`／`POOL_MAX_LIFETIME_SECONDS` 是對的（redis-py 沒有對應參數，死碼），但上游兩份已核可設計仍寫「min 5 暖連線」「idle 10 分鐘」「max lifetime 30 分鐘」，`performance-design.md:79` 還拿「min 5 的暖連線」當連線逾時不在穩態路徑上的理由。這個偏離只記在 Step 5.1 的未勾註記裡，沒有進第九節的開放項，下游讀設計會以為暖連線存在。 | 把「連線池 min／idle／lifetime 未實作（函式庫不支援）」加進 code-summary 第九節開放項，標明上游設計的哪幾行不再成立、閒置後首次互動會吃到最多 2 秒的建立連線成本；Step 5.1 改記為「不可實作」而非單純未勾。 | Resolved (reviewer) |
| R-06 | Minor | DEPLOY.md「`maxmemory 256mb` 的暫定依據」；deploy/.env.example:145-149 | 「≈349 個 session、300 個佔 69%、不觸及 `maxmemory`」只計算歷程值的位元組：不含同 key 的 `wi:*` 工作項（文件已聲明在上界之外，但工作項的筆數與單項大小目前沒有任何上限，所以整體上界仍是開的）、Hash 結構開銷、AOF 重寫與用戶端輸出緩衝（後者計入 `maxmemory`）。文件標題「承諾 ≥ 300」讀起來比實際能保證的強。 | 在該表下方加一句：349 是「歷程值」的下界估計，不含工作項與結構開銷；並在開放項登記「`U12` 工作項需要自己的筆數／大小上限，否則 `NFR4.41` 的硬上界只對歷程成立」。 | Resolved (reviewer) |
| R-07 | Minor | backend/tests/test_session_store_behaviour.py > `RealRedisParityTest.test_real_pipeline_error_is_classified_and_stripped_of_written_values` | 該案例用很長的 key（`u10-parity:<32 hex>:<測試名>`）加上 redis-py 把指令截到 100 字元，值 `fixture-secret-value` 在未去值時也已被截掉，所以 `assertNotIn` 在真實 Redis 上無辨識力；M12S 變紅靠的是 `startswith("WRONGTYPE")` 那條。去值的辨識力只在替身案例（短 key）上成立。 | 真實 Redis 案例改用短 key（例如 `p:x`）使值落在前 100 字元內，讓 `assertNotIn` 在移除 `_strip_pipeline_annotation` 時也會紅。 | Unresolved |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/session-store/code-generation/code-generation-plan.md > Step 9.3；.github/workflows/deploy.yml > 步驟「Verify sessions survive a Redis restart」的檔頭註解 | 候選 3 成立，定為 Minor。該步驟位於 U14 的阻擋步驟「Verify the brain WS subprotocol survives the tunnel」之前，而註解寫「placed LAST ... never adds an outage on top of a failing deploy」，現已為假：WS 檢查失敗時 Redis 已先被重啟。後果有限（AOF 保住資料、失敗後 rollback 本來就會重啟服務），所以不是 Major；但這是 deploy 檔案裡一句關於部署安全的錯誤陳述，且計畫該格維持未勾。修法很小 | 把該步驟移到 WS 驗證步驟之後、「Record this commit as the last-good deployment」之前，並重勾 9.3；或維持現序、改寫註解為事實並把 9.3 改記為已知偏離。擇一，不要留下與現況不符的「LAST」 | Unresolved |
| R-09 | Minor | .github/workflows/deploy.yml > 同一步驟 step 2 與 step 5（`hgetall "${KEY}"` 接 `sort`，前後比對 BEFORE 與 AFTER） | 候選 2 成立，定為 Minor。排序的是輸出的每一行，欄位名與值各占一行，排序後配對關係消失；兩個欄位的值互換，或 `tgt:shared`、`tgt:workspace` 的值對調，多重集合相同，比對會過。步驟註解宣稱逐欄位比對 `NFR4.53` 至 `NFR4.56`，實際弱於宣稱。AOF 重放造成值互換並不現實，所以不升級，但「每個 segment 自己的作業對象」正是 `NFR4.55` 要驗的 | 改成對 `hkeys` 排序後逐欄位 `hget` 比對（或把欄位與值串成一行再排序），並把註解的強度說成實際強度 | Unresolved |
| R-10 | Minor | .github/workflows/deploy.yml > 同一步驟的 `APP=(... redis-cli --user ... --pass "${REDIS_PASSWORD}" ...)`；同檔 `acl whoami` 步驟同形 | 候選 4 成立，定為 Minor。密碼出現在 `docker compose exec` 與容器內 `redis-cli` 的命令列，自架 runner 與容器內的任何本機使用者都能由程序清單看到。`REDIS_PASSWORD` 由 `deploy/.env` 以 grep 讀入、不是 Actions secret，所以不會被遮罩，日誌一旦誤印就等於公開（本 repo 為 public）。同一密碼在 redis-server 的 `command:` 也在命令列（U1 既有），故本步驟是延續既有形狀，不是新曝險面，且 staging 為單租戶自架機，因此不到 Major。ADR-0006 四面向：IAM 面向有此項 | 改用環境變數傳密碼（`export REDISCLI_AUTH`，並以 `docker compose exec -e REDISCLI_AUTH` 轉入容器），命令列只留 `--user`；讀入後加 `echo "::add-mask::..."`。兩個步驟一起改 | Unresolved |
| R-11 | Minor | DEPLOY.md >「`maxmemory 256mb` 的暫定依據」容量表；deploy/docker-compose.deploy.yml > redis 的 `--maxmemory` 旁註解 | 候選 1 的結論：算術正確（我重算 3 × 204,800 ＋ 81,000 ＝ 695,400 B；0.8 × 268,435,456 ÷ 695,400 ＝ 308.8；300 個 ＝ 77.7%），#18 的上限機制本身也成立（真實 Redis 上 Lua 與參考實作逐步一致、跑滿後段落 193 KB 不超過 200 KB）。但「308.8 個、80% 內、餘裕 2.9%」只以序列化位元組計，沒有量過配置器。若映像用 jemalloc（本機是 macOS 的配置器，不能代表 `redis:8-alpine`；我無法在此確認該映像的配置器），一個 204,810 B 的段值會落入 224 KiB（229,376 B）級距，每段多約 12%，300 個最壞 session 約佔 87%，80% 內只剩約 273 個；若是 libc 則差距很小。此外還有 Hash 欄位開銷與最多 20 條連線同時回傳約 0.7 MB 的 `HGETALL` 輸出緩衝（計入 `maxmemory`）。即使最壞，300 個仍低於 100%，所以 `NFR4.40`「不觸及 `maxmemory`」大概率成立，不到 Major；但 2.9% 這個精確餘裕沒有根據 | 在 DEPLOY.md 把 308.8 與 2.9% 明標為「序列化位元組的下界估計，不含配置器級距、欄位開銷與輸出緩衝」；staging 首次部署時以 app 身分對一個填滿的 fixture 執行 `MEMORY USAGE`（app ACL 可執行，本輪已驗）並把倍率寫回，再決定 80% 這個說法是否保留 | Unresolved |
| R-12 | Minor | backend/services/session_store.py > `set_sharing_mode` 切回 shared 分支（`_load_meta` 後 `_write_meta_and_expire`）；`_write_meta_and_expire` 旁註解 | 原子性缺口：切回 shared 是「讀 meta、改 pageModes、整份寫回」兩次往返，期間若另一頁的 `switch_to_isolated.lua` 已把它的 pageModes 設為 isolated，會被這次寫回蓋掉，該頁便讀共享段而使用者的獨立段被晾著（正是 `EC3` 要避免的「指示器與資料不一致」）。需要同一 session 兩頁在毫秒內分別切換，機率低。註解寫「見 `code-summary.md` 對並行寫入的記載」，但 code-summary 全文沒有這段記載（我 grep 過），是懸空引用 | 二擇一：把切回 shared 也做成與 `switch_to_isolated.lua` 對稱的 Lua（讀、改、寫、續期一支腳本）；或在 code-summary 第九節補上這段已知殘留並讓註解指向它 | Resolved (reviewer) |
| R-13 | Minor | backend/services/session_store.py > `_ensure_meta` docstring；aidlc/spaces/default/intents/260920-orchestration-brain/construction/session-store/code-generation/code-summary.md > 第九節第 3 項 | 兩處都寫「`set_work_target` 會把 `meta.userId` 補上」（第九節寫「`userId` 為 null 直到第一次 `set_work_target`」）。我讀 `set_work_target`，它只寫 `tgt:<segment>` 一個欄位，從不碰 `meta`；全 `backend/services` 也沒有任何讀取 `session.user_id` 的程式。實際狀態是 `userId` 永遠為 null，沒有寫入端也沒有讀取端。這是不實的文件陳述，會讓下游以為 U13 不必處理 | 更正 docstring 與第九節：`userId` 目前沒有寫入端，也沒有讀取端，是 U13 的待辦或應從實體移除；不要讓文字暗示 `set_work_target` 會補上 | Unresolved |
| R-14 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/session-store/code-generation/code-summary.md > 共用檔異動後的重新驗證 > 一、DEPLOY.md 容量表 hunk | 容量表 hunk（`:1802-1876`）被判為收據之前就存在，依據只是「依紀錄」（重做節寫於收據前一分鐘）。收據當時的 DEPLOY.md 無法重建，所以這個判定無法證實；實際 hunk 範圍 `+1802,34`、`+1837,41` 到 1877，也比寫的 1876 多一行。內容含 U12 的工作項數字（81,000 B），不是本單元寫的。逐行重讀的補強有效，結論不致錯，但敘述強度略高於證據。 | 在 code-summary 把該判定寫成「無法證實，已以逐行重讀補強」，行號改為 1802-1877。 | New |
| R-15 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/session-store/code-generation/unit-test-instructions.md > §二 現況註記 | 註記的指令只有 `cd backend && … .venv/bin/python -B -m unittest …`，在 repo 內照做會產生 `.hypothesis/`；副本指令需 `-P`、PYTHONPATH，且副本必須含 `backend/tests_redis`（只複製 `tests/` 時 test_session_store_behaviour 會因 `ModuleNotFoundError: tests_redis` 失敗，我第一次就遇到）。code-summary 用的副本指令與註記不一致。 | 註記改為副本指令全文，並註明需帶 `tests_redis/`。 | New |

> R-01 Reviewer note: 選項 2 已做：code-summary 第四節第 1 項明列「到期邊界會重建殘缺 key」及後果（meta 缺、segments 無 shared、自癒）。程式未改，`session_store.py:633` 的 EXISTS 快速路徑與 `:465` 的交易仍如描述，符合原要求的二擇一。

> R-02 Reviewer note: `session_store.py:309` 仍只有 `if not role`，`:155` 的 `MESSAGE_ENVELOPE_RESERVE_BYTES = 1024` 仍只是註解承諾。code-summary 第七節已交 conductor 開 merge-blockers 新列，屬登記中的已知限制，維持 Minor。

> R-03 Reviewer note: `append_message.lua:71-72` 仍對全部既有訊息逐則 cjson.encode。數字已補（審查實測 3.25 ms，review-02.md:29、:45 我核對屬實），但改 Lua 的動作尚未做，待新列。

> R-04 Reviewer note: code-summary 第四節第 2 項已登記「CI 無 Redis」並指派承接站 build-and-test，且保留 staging 首次部署實測。ci.yml 零 Redis 屬實，三條 RealRedisParityTest 在我的副本同樣跳過。

> R-05 Reviewer note: 第四節第 3 項寫明 min／idle／lifetime 不可實作，並列出 performance-design.md:68-69、:79 與 infrastructure-specification.md:10 不再成立，也寫了閒置後首次互動最多 2 秒的代價；`redis_gateway.py:88` 只有 POOL_MAX_SIZE = 20，屬實。5.1 維持未勾正確。

> R-07 Reviewer note: `test_session_store_behaviour.py:1357、:1360` 仍用長 key，去值斷言在真實 Redis 上無辨識力。需改測試，已交 conductor。

> R-08 Reviewer note: `deploy.yml:452-455` 仍寫 placed LAST，而 `:596` 的 6a 步驟（brain_ws_probe）在本單元步驟（`:456`）之後。9.3 維持未勾正確。

> R-09 Reviewer note: `deploy.yml:508`、`:553` 仍是 `hgetall … \| sort`。

> R-10 Reviewer note: `deploy.yml:238` 與本單元步驟仍以 `--pass` 在命令列傳密碼；REDISCLI_AUTH 零命中。

> R-11 Reviewer note: `DEPLOY.md:1824` 仍寫「≈ 308.8 … 餘裕約 2.9%」，未標序列化位元組下界與配置器前提。

> R-12 Reviewer note: 第四節第 4 項補上並行寫入記載，並明說它就是 `session_store.py:415-416` 註解所指，懸空引用已有落點。

> R-13 Reviewer note: `session_store.py:619` docstring 仍寫「set_work_target 會把它補上」，程式檔未改；code-summary 第四節第 5 項已更正文件陳述，但原第九節第 3 項只是被取代而非修正，docstring 仍需改。

### Validation Tool Results
| Tool | Result | Interpretation |
|---|---|---|
| 在 scratchpad 副本（rv-ss）跑三個 session 測試模組，cwd = 副本 backend，`-B -P`、未設 REDIS_URL | `Ran 100 tests` → `OK (skipped=3)` | 與 code-summary 的 100／skipped=3 一致；跳過的是 RealRedisParityTest，屬預期。第一次少複製 `tests_redis` 出現 import 錯誤，補上後通過。 |
| `git diff 624c170 7a50a40` 對 deploy.yml 的 hunk | 8 個 hunk：`+35,9`、`+520`、`+596`、`+656`、`+798`、`+805`、`+889`、`+944` | 與 code-summary 表逐項吻合。只有 `+520`（一行註解）落在本單元步驟 `:456-584` 內，未碰 `acl whoami`（`:209-258`）。 |
| 同上對 DEPLOY.md | 18 個 hunk，與摘要所列行號相符；`:1883-1948`（noeviction 節、還原驗證節）零 hunk | 這兩節與 `acl whoami`、還原驗證步驟的文字未被改動。 |
| 計畫勾選計數 `grep -c` | 63 已勾、2 未勾（5.1、9.3） | 與摘要一致；兩格未勾都有仍成立的理由（R-05 不可實作、R-08 註解失實且 6a 在後）。 |
| 引用行號抽查（`session_store.py:633、:465、:478、:309、:155`、`redis_gateway.py:88`、`deploy.yml:238、:456、:508、:553、:596`、`DEPLOY.md:1824`） | 全部吻合 | 摘要沒有捏造行號或計數。 |

### Summary
(a) 超集判定（`624c170..7a50a40` 的全部 hunk）的推理成立：收據當時內容雖無法重建，現況等於 7a50a40，所以收據之後的任何改動必在該 diff 內；收據後新增的 hunk 全屬 U14 第 26 項與其他單元，沒有動到 Redis 重啟驗證的邏輯、`acl whoami`、noeviction 節。唯一的弱點是容量表那段「早於收據」只能靠紀錄推定。(b) 12 筆既有發現中 R-01、R-04、R-05、R-12 已由文件補記關閉，其餘 8 筆仍成立但都是 Minor 且已交 conductor 登記；(c) 勾選與兩個未勾格正確；(d) 摘要的數字與行號我抽查全部屬實。新增兩筆皆為 Minor，無 Critical 或 Major，判定 READY。
