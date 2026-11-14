## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-23T01:07:55Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | backend/services/session_store.py > `set_work_target`（`_ensure_meta` 之後的 `hset_fields_and_expire`）、`_ensure_meta` 的 `EXISTS` 快速路徑 | 交易保證了「寫入與 TTL 同進同退」，但沒有處理「key 在 `_ensure_meta` 的 `EXISTS` 為真之後、`set_work_target` 的交易之前剛好到期」這個窗口：交易會重建一個**只有 `tgt:<seg>`、沒有 `meta` 與 `seg:shared`** 的 key，並替它設 TTL。之後每次呼叫 `_ensure_meta` 看到 `EXISTS` 為真就跳過，不會補建；`decode_session` 對沒有 blob 的段直接 `continue`，於是這個 session 在剩餘 24 小時內都沒有 `shared` 段，與 `EC1`「segments 必含 shared」不符。機率極低（需在 TTL 邊界的毫秒窗口），也比修正前（永不過期的殘缺 key）好得多，但「TTL 剛過期被重建」正是第 12 項要處理的情境，這一半只做到有 TTL、沒做到完整。 | 二擇一並寫進程式註解：（1）`set_work_target` 的交易內以 `only_if_absent` 形式另附 `meta` 與 `seg:shared` 的預設值（HSETNX 對已存在的欄位是 no-op）；或（2）在 `code-summary.md` 第九節開放項明列「到期邊界會重建殘缺 key」為已知殘留與其後果，不要讓文件讀起來像已完全關閉。 | New |
| R-02 | Minor | backend/services/session_store.py > `SessionStore.__init__` 的 `worst_single` 算式、`append_message` 的參數檢查 | 「單則訊息不可能超過每段 200 KB」的證明用 `MESSAGE_ENVELOPE_RESERVE_BYTES = 1024` 假設 `role` 很短（註解寫「由 U13 依對話協定給值」），但 `append_message` 對 `role` 只檢查非空，沒有長度或集合限制。若呼叫端傳入很長的 `role`，單則可超過上限；Lua 迴圈在剩一則時停止，會保留一個超限的段——而上限的整個目的是封住容量。建構時的算式檢查因此只證明了「`text` 部分」。 | 在 `append_message` 入口對 `role` 加長度上限（或限定為對話協定的封閉集合），讓 `MESSAGE_ENVELOPE_RESERVE_BYTES` 的假設由程式強制而不是由註解承諾；補一個對應的拒絕測試。 | New |
| R-03 | Minor | backend/services/session_scripts/append_message.lua > 修剪前的 `for i = 1, #arr` 迴圈；code-summary.md「新測試」「未驗項」 | 每次追加現在多做一輪對**全部既有訊息**的 `cjson.encode`（段滿時約 200 KB），加上原本的 decode 與最後整段 encode，腳本成本約為原本的兩到三倍。Redis 單執行緒，腳本期間阻塞其他所有指令；`NFR3.40` 的 P95 20 ms 與連線池算式（300 RPS）都沒有把這個成本算進去，產出也沒有任何量測。這不是正確性問題，也很可能在餘裕之內，但沒有數字。 | 在本機臨時 Redis 對「段已滿 200 KB」的狀態量一次 `EVAL` 耗時（實作方已有該環境），把數字寫進 code-summary；若接近毫秒級以上，改為只重新編碼新訊息並沿用既有訊息的位元組長度（例如修剪前先量原字串再加新訊息）。 | New |
| R-04 | Minor | backend/tests/test_session_store_behaviour.py > `RealRedisParityTest`；.github/workflows/ci.yml | 第 18 項的生產載體是 Lua 迴圈，而它在 CI 中只被兩條字串斷言（`while #arr > 1 and (#arr > cap or total > max_bytes) do`、`string.len(cjson.encode(arr[i]))`）覆蓋；位元組算式的 off-by-one（例如逗號數、剩一則的邊界）在 CI 不會變紅，M18L 突變也只由靜態斷言抓到。產出已如實記載這個限制，且與 `tests_redis/` 先例一致，故不阻擋；但這是本站唯一真正強制容量上界的程式碼。 | 在 code-summary 的開放項登記「CI 無 Redis，Lua 位元組修剪只有本機 opt-in 驗證」並指派承接站（build-and-test 或 CI 加 Redis service container）；staging 首次部署時以 app 身分跑一次含長訊息的 `EVAL` 並記錄結果。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/session-store/nfr-design/performance-design.md:68-69、infrastructure-design/infrastructure-specification.md:10；code-summary.md 第九節 | 移除 `POOL_MIN_SIZE`／`POOL_IDLE_TIMEOUT_SECONDS`／`POOL_MAX_LIFETIME_SECONDS` 是對的（redis-py 沒有對應參數，死碼），但上游兩份已核可設計仍寫「min 5 暖連線」「idle 10 分鐘」「max lifetime 30 分鐘」，`performance-design.md:79` 還拿「min 5 的暖連線」當連線逾時不在穩態路徑上的理由。這個偏離只記在 Step 5.1 的未勾註記裡，沒有進第九節的開放項，下游讀設計會以為暖連線存在。 | 把「連線池 min／idle／lifetime 未實作（函式庫不支援）」加進 code-summary 第九節開放項，標明上游設計的哪幾行不再成立、閒置後首次互動會吃到最多 2 秒的建立連線成本；Step 5.1 改記為「不可實作」而非單純未勾。 | New |
| R-06 | Minor | DEPLOY.md「`maxmemory 256mb` 的暫定依據」；deploy/.env.example:145-149 | 「≈349 個 session、300 個佔 69%、不觸及 `maxmemory`」只計算歷程值的位元組：不含同 key 的 `wi:*` 工作項（文件已聲明在上界之外，但工作項的筆數與單項大小目前沒有任何上限，所以整體上界仍是開的）、Hash 結構開銷、AOF 重寫與用戶端輸出緩衝（後者計入 `maxmemory`）。文件標題「承諾 ≥ 300」讀起來比實際能保證的強。 | 在該表下方加一句：349 是「歷程值」的下界估計，不含工作項與結構開銷；並在開放項登記「`U12` 工作項需要自己的筆數／大小上限，否則 `NFR4.41` 的硬上界只對歷程成立」。 | New |
| R-07 | Minor | backend/tests/test_session_store_behaviour.py > `RealRedisParityTest.test_real_pipeline_error_is_classified_and_stripped_of_written_values` | 該案例用很長的 key（`u10-parity:<32 hex>:<測試名>`）加上 redis-py 把指令截到 100 字元，值 `fixture-secret-value` 在未去值時也已被截掉，所以 `assertNotIn` 在真實 Redis 上無辨識力；M12S 變紅靠的是 `startswith("WRONGTYPE")` 那條。去值的辨識力只在替身案例（短 key）上成立。 | 真實 Redis 案例改用短 key（例如 `p:x`）使值落在前 100 字元內，讓 `assertNotIn` 在移除 `_strip_pipeline_annotation` 時也會紅。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 依派工限制未執行任何測試、lint、build 或 Python 命令 | N/A | 以讀檔、`git diff`、grep 查證；測試數字（100 條 OK、全套 1259 條）與突變結果取自 code-summary 的記載，未獨立複驗。 |

**逐項查核摘要**

- 重點 (a)：`session_store.py` 的 `gateway.hset`／`gateway.expire` 呼叫已全數查過。寫入加續期的多指令路徑共三處（`_ensure_meta`、`set_work_target`、切回 shared 的 `_write_meta_and_expire`），皆已改走 `hset_fields_and_expire`；`append_message.lua` 與 `switch_to_isolated.lua` 本來就在單一腳本內 HSET＋EXPIRE。剩下的 `expire` 呼叫（`load` 與 `touch`）是續期、不建立 key。`HSETNX` 在 `EXISTS` 為假時只會跳過「剛被並行者建立」的欄位，不會讓應被重設的 meta 沒被寫；唯一殘留是上表第一列的到期邊界。`_strip_pipeline_annotation` 的正規式在 DOTALL 與貪婪匹配下，值內含相同字串時仍會匹配到最後（真正的）前綴；只動 `args[0]`、不改型別，`classify_client_error` 的型別優先判定不受影響，字串退路 `OOM ` 因此被修好。
- 重點 (b)：cjson 與 Python `json.dumps(ensure_ascii=False, separators=(",", ":"))` 的長度差只在 `/`（＋1）與 `0x7f`（＋5）；控制字元、`"`、`\`、非 ASCII、NUL 兩邊長度一致，已對照；整段位元組算式（2＋Σ＋(n−1)）在 Lua 與參考實作一致，Lua 對只剩一則時停止的界線與參考實作一致。段內量的是整個訊息陣列（Hash 內其他欄位 `meta`、`tgt:*` 為固定小欄位，工作項見上表）。容量數字：`deploy/.env.example`、`docker-compose.deploy.yml`、`DEPLOY.md`、`traceability.json` 皆為 349／600 KB／約 69%；只有計畫 Step 13 內寫的是 340，且 code-summary 已說明是十進位概算，兩者皆 ≥ 300，不構成分歧。
- 重點 (c)：同 key 的 `wi:*` 工作項在容量上界之外且無筆數與大小上限，文件已如實聲明（DEPLOY.md、code-summary 第九節第 4 列），嚴重度判為 Minor，建議登記為 `U12` 的上界義務（見上表第六列）。
- 重點 (d)：M12／M12S／M18／M18L／M18C／M12N 的設計都對應到真實缺陷形狀；M18L 在 CI 的覆蓋缺口已如實記載（見上表第四列與第七列的補強建議）。`RealRedisParityTest` 的輸入涵蓋 `/`、DEL、4 位元組表情符號、控制字元與中文，且斷言位元組上限確實被觸發。
- 重點 (e)：Steps 1–12 勾回的依據（類別、常數、方法皆存在；`TransactionalWriteTest`、`SegmentByteCapTest`、`RealRedisParityTest` 存在於測試檔）抽查成立。5.1 未勾的理由成立（見上表第五列的補強）。
- 重點 (f)：ADR-0006 的 audit logging 面向：`_strip_pipeline_annotation` 是本輪新增的關鍵防線，`fields` 的值不進日誌參數、`SessionBackendUnavailable` 的 cause 去值；network exposure 與 IAM 面向無變更（`maxmemory`／`noeviction`／ACL 不變）；encryption 無變更。

### Summary

第 12、18 項與兩項 conductor 處置在架構上成立：多指令寫入已全數進交易，位元組上限在 Lua 與參考實作的計算規則一致，容量算式與各份文件的數字相符，新增的去值防線補上了管線例外可能把 session 內容帶進日誌的洩漏面。無 Critical 與 Major；剩下的是到期邊界重建殘缺 key、`role` 長度未被強制、Lua 成本未量測、CI 對 Lua 修剪無覆蓋、上游設計的連線池敘述未同步、工作項無上界，皆為 Minor。
