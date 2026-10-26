# Code Summary — `U10 session-store`

> 方法論為 `test-after`（`standard`），由計畫內嵌的 `## Testing Contract`
> （`contract_sha256:1f0b6822…`）決定，**未重新解析**。每一層先實作再測：
> Step 3 → 4、Step 5 → 6、Step 7 → 8。

## 一、一句話結果

`SessionContext` 已落地：單一 Redis key 的 Hash 之下**至多三段**對話
（`shared`／`workspace`／`assessment`），每段各自帶訊息歷程與三層作業對象；
追加與分段切換各以一支 Lua 原子完成；TTL 24 小時、五個方法全部續期。
**零對外端點、零 schema 變更、零前端面。**

## 二、交付物（19 個檔：9 新、10 改）

### 新增（9）

| 檔案 | 行數 | 角色 |
|---|---|---|
| `backend/services/session_types.py` | 390 | 純資料形狀、封閉集合、Hash 欄位編碼、`BR3.4` 修剪的**參考實作**（PBT 標的） |
| `backend/services/session_errors.py` | 106 | `SessionBackendUnavailable(reason=…)`、**`SessionMessageTooLong`**、三個原因碼 |
| `backend/services/redis_gateway.py` | 498 | 連線池、逾時、重試、三種原因碼分類、**日誌白名單簽章**、Lua 載入 |
| `backend/services/session_store.py` | 474 | `K-09` 的五個方法；委派 `K-07` 做作業對象授權 |
| `backend/services/session_scripts/append_message.lua` | 64 | 追加＋`sequence`＋`BR3.4` 修剪＋續期，原子 |
| `backend/services/session_scripts/switch_to_isolated.lua` | 70 | 建段＋複製作業對象＋改 `pageModes`＋續期，原子（`EC3`） |
| `backend/tests/test_session_types.py` | 217 | 18 測試（**3 個 `@given`**）＋封閉集合＋序列化往返 |
| `backend/tests/test_session_contract.py` | 375 | 20 測試，**全部為 AST 靜態斷言**（零執行） |
| `backend/tests/test_session_store_behaviour.py` | 955 | **44** 測試 ＋ 手寫 in-memory Redis 替身 |

### 修改（10）

`backend/main.py`（startup 驗設定）、`backend/requirements.txt`（**唯一新依賴** `redis`）、
`backend/.env.example`、`deploy/.env.example`、`deploy/render-env.sh`、
`deploy/docker-compose.deploy.yml`（`noeviction` ＋ 新變數）、
`deploy/docker-compose.test.yml`（新變數，內嵌預設）、
`.github/workflows/deploy.yml`（部署後還原驗證）、`LOCAL-DEV.md`、`DEPLOY.md`。

### 計畫列了 20 個檔，實際 19 —— 差的那一個

計畫的第 16 項是「`docker-compose.yml`（repo 根，本機 dev）**若它起 backend**，
傳入新變數」。**實讀該檔：它只起 `db` 與 `adminer` 兩個服務，沒有 backend**
（檔頭逐字「Local-development helpers only: a Postgres a developer can reach with
psql/GUI and Adminer」）。故該條件不成立，未改動它；本機 dev 的 backend 是
bare-metal `uvicorn`，讀 `backend/.env`，而該檔已加上新變數。

## 三、刻意不動的四項——驗證結果

| 不動 | 驗證方式 | 結果 |
|---|---|---|
| `openapi.json`（**repo 根**，不是 `backend/`） | `git diff -- openapi.json \| grep -icE "session\|redis\|brain_session"` | **0 命中**。另 `python3 backend/scripts/dump_openapi.py --check` → 「規格檔與後端程式碼一致」 |
| `frontend/src/types/api.d.ts` | 同形 grep | **0 命中** |
| `backend/database.py` | `git diff --stat` | **零行**（完全未動） |
| `schema_rbac.sql` | 同形 grep | **1 命中，且不屬本單元**——是 `U4`／`U12` 的欄位註解提到「session owner」。本單元零 schema 變更，故 `project.md` 的 schema 同步 blocking 規則**不觸發** |

> ⚠ **第一次做這項檢查時我查了 `backend/openapi.json`，那個路徑不存在，於是得到
> 一個假的「EMPTY DIFF ✓」。** 真實路徑是 repo 根的 `openapi.json`。
> 工作樹裡 `openapi.json`（42 → 55 paths）、`api.d.ts`、`schema_rbac.sql` 三者
> **確實有 diff**，但全部來自本 intent 較早的單元（`U5`／`U7`／`U8`／`U19`…）；
> 本單元對它們的貢獻是上表的 grep 結果。**「沒有 diff」與「我的 diff 是空的」
> 在一個累積了多個單元的工作樹上是兩件事**，而前者在這裡是假的。

## 四、`nfr-design` 審查 `R-01` 的對齊（Step 1.3）

`tech-stack-decisions.md:59` 寫「儲存結構留 `code-generation` 決定」，而
`nfr-design` 的 `[D1]`=A 已經決定了（Hash ＋ Lua）。**本站不重新決定**：
結構即 Hash ＋ 兩支 Lua，欄位命名空間為 `seg:`／`tgt:`／`meta`。

## 五、承接上游的七項——逐項結果

| 來源 | 本站落點 | 結果 |
|---|---|---|
| `infrastructure-design` `R-01`（**Critical**） | 還原驗證的等待條件改為**以 app ACL 身分實際讀回 fixture 成功**，重試上限 60 × 2s = 120s 總逾時；**完全不用 healthcheck** | ✅ `deploy.yml` 的新步驟第 4 段 |
| `infrastructure-design` `R-02`（Major） | **刪掉假緩解**。步驟說明逐字寫「THIS STEP INTERRUPTS LIVE SESSIONS, and that is not mitigated」，並指名 `up -d --build --remove-orphans` **無** `--force-recreate` 故未變更的 redis 不會被重建 | ✅ 同步驟的檔頭註解 ＋ DEPLOY.md |
| `nfr-requirements` `R-02` ＋ `nfr-design` `R-02`（Major ×2） | 新增 `SessionMessageTooLong`，入口檢查長度 | ✅ `session_errors.py` ＋ `session_store.append_message`（突變 M5 驗證） |
| `nfr-requirements` `R-01`（Major） | 日誌白名單做成**建構函式簽章**（七個 keyword-only 參數、無 `*args`／`**kwargs`）＋ 執行期守衛 | ✅ `redis_gateway.session_log_fields`（突變 M6 驗證） |
| `nfr-design` `R-01`（Major） | 不重決儲存結構 | ✅ 見第四節 |
| `infrastructure-design` `R-03`（Minor） | `traceability.json` 的 id 來源為上游 `traceability.json` **∪** markdown | ✅ 實算：json 68 ＋ md 122 → **聯集 131**；**9 個 id 只存在於上游 json**（`AC2.1.1`／`AC2.1.2`／`AC2.2.1`／`AC2.2.2`／`AC6.1.2`／`AC9.1.2`／`AC9.1.3`／`AC9.1.4`／`NFR9`），只掃 markdown 會把它們丟掉——這正是 `R-03` 指出的形狀 |

## 六、測試結果

| 指令（自 `backend/`） | 測試數 | 結果 |
|---|---|---|
| `python3 -m unittest tests.test_session_types` | **18**（含 3 個 `@given`） | OK |
| `python3 -m unittest tests.test_session_contract` | **20** | OK |
| `python3 -m unittest tests.test_session_store_behaviour` | **44** | OK |
| `python3 -m unittest discover -s tests`（全套回歸） | **656** | OK（本單元前的基準為 **574**，故新增 **82**） |

`python3 scripts/validate_repo_contract.py` ✅／`python3 scripts/validate_env_contract.py` ✅／
`python3 backend/scripts/dump_openapi.py --check` ✅

> **指令用 `python3` 而非 `python`**：本機 `PATH` 上沒有 `python`
> （`which python` 無結果，只有 `python3`）。`unit-test-instructions.md §二` 寫的是
> `python`，CI（`ci.yml`）用的也是 `python`——**模組路徑與參數逐字相同，只有解譯器
> 名不同**。這是本機環境事實，不是對指令的改寫。

## 七、六項突變驗證（全部實際跑過，每項都看到紅燈再還原）

每一項的程序都是：先確認該測試在未突變時為綠 → 套用突變 → 跑**指定**測試 →
跑整個模組看連帶影響 → 還原 → **複驗為綠**。

| # | 突變 | 指定測試 | 結果 | 整模組連帶 |
|---|---|---|---|---|
| M1 | `trim_history` 改成丟最新（`items[:cap]`） | `TrimHistoryPropertyTest.test_output_is_a_suffix_of_the_input` | **紅 ✓** | 1／18 |
| M2 | `append_message` 省略段識別、預設寫 `shared` | `AppendMessageTest.test_segment_id_is_required_and_never_defaults_to_shared` | **紅 ✓** | 1／38 |
| M3 | `set_work_target` 寫入呼叫方的原始識別碼 | `WorkTargetAuthorizationTest.test_resolved_result_is_stored_not_the_caller_supplied_ids` | **紅 ✓** | 1／38 |
| M4 | `switch_to_isolated` 改回三次獨立寫入 | `SharingModeTest.test_switch_to_isolated_is_a_single_script_call_not_three_writes` | **紅 ✓** | **3／38** |
| M5 | 長度檢查移除 | `AppendMessageTest.test_too_long_message_raises_message_too_long_not_backend_unavailable` | **紅 ✓** | 1／38 |
| M6 | 日誌建構函式改為接受 `**kwargs` | `LogWhitelistIsASignatureTest.test_log_field_builder_accepts_no_arbitrary_kwargs` | **紅 ✓** | 1／20 |
| **M7** | 把 ERROR 日誌的 `sessionKey` 移除（即**修正前的實際缺陷形態**） | `LogWhitelistRuntimeTest.test_every_public_gateway_method_threads_the_session_key_into_its_log` | **紅 ✓**（八個公開方法逐一紅） | 1／41 |

| **M8** | 從 `set_sharing_mode` 移除 `_ensure_meta`（即**審查 `R-01` 的缺陷形態**） | `FirstWriteEstablishesTheSharedSegmentTest.test_every_write_entry_point_creates_the_shared_segment` | **紅 ✓**（另一條 `test_isolated_first_write_satisfies_ec1_and_ec3_together` 一併紅） | 2／44 |

M7 與 M8 不在計畫的六項之內，是**審查指出 `NFR4.61` 與 `EC1` 未被守住之後補上的回歸守衛**（見第十四、十五節）。

**M4 的前提被 `R-01` 的修法改動過，已重驗**：`R-01` 的修法讓 `set_sharing_mode` 在第一次寫入時正當地發出兩次 `HSET`（`meta` ＋ `seg:shared`），而 M4 的斷言原本是「切換路徑的 `HSET` 次數為 **0**」。處置是在該測試內**先讓 session 存在**（`append_message` 一次）使 `_ensure_meta` 成為 no-op，再 clear calls——如此 `HSET == 0` 仍精確指向「切換本身不發直接寫入」。**刻意不改成斷言 `HSET == 2`**：那會把 `_ensure_meta` 的內部實作寫進斷言，在它多寫一個欄位時假性紅燈。改完後 M4 重跑仍為**紅 ✓**，且連帶變紅的測試由 1 條增為 3 條。

### M4 的誠實限定（計畫點名它可能偵測不到——它偵測到了，但偵測到的不是原子性）

計畫 §五 逐字：「in-memory 替身能否區分『一次 Lua』與『三次寫入』取決於替身的
實作粒度。若不能，**記為替身的限制**。」

**它能區分**，因為替身記錄每一個指令名，所以「只發一次 `EVALSHA`／`EVAL`、
**零次**直接 `HSET`」是可機械判定的。但必須寫清楚它判定的是**呼叫形狀**：

- ✅ **能證明**：切換路徑走的是腳本，而不是三次獨立的 Hash 寫入。
- ❌ **不能證明**：腳本在真實 Redis 上**不會被打斷**。替身是單執行緒 Python
  物件，「原子」在它身上是免費的——它對任何實作都會回報原子。

**真正的原子性只能在真實 Redis 上驗，而那是 `[I1]`=B 的部署後步驟的範圍。**
不得把 M4 的紅燈讀成「`EC3` 的不變量已被驗證」。

## 八、本單元**無法**在 CI 驗證的三項（如實記載，非遺漏）

| 項目 | 為什麼 | 真正的驗證點 |
|---|---|---|
| Lua 的實際行為與原子性 | backend 測試不連 Redis（走 in-memory 替身）；新增連 Redis 的 CI job 已於 `[I1]` 否決 | 部署後驗證 ＋ staging 實跑 |
| `noeviction` 的 OOM 行為 | 需要把 Redis 灌到 256MB。`REDIS_OOM` 的測試驗的是**分類邏輯**（替身被設定為回 `OOM …`），不是 Redis 的真實行為 | 不驗。`NFR4.60` 的使用率訊號是替代偵測面——而它本身是開放項，見第九節 |
| 重啟還原五項（`NFR4.53`–`NFR4.57`） | CI 測試 stack 無 AOF、無 named volume（**實讀 `docker-compose.test.yml` 第 121 行的註解**確認） | `[I1]`=B 的部署後步驟 |

**三項都不是「忘了測」，是測不到。** 故 `traceability.json` 把
`NFR4.53`–`NFR4.57` 與 `BR7.1` 記為 **`PARTIAL`** 而非 `OK`——
「三個指令全綠」不得被讀成「Redis 行為已驗證」。

## 九、本站新引入或未關閉的開放項（**需要下游處置**）

| # | 項目 | 狀態與理由 |
|---|---|---|
| 1 | **`NFR4.60` 的 `MEMORY STATS` 採集點未實作** | 記為 `OPEN`。它不在 `K-09` 的五個方法內（那是一個獨立的低頻採集點），且 `OPEN-N10-4` 已記明**沒有任何告警管道消費它**。本單元不自行發明一個採集迴圈——那會是一個沒有消費者的新機制。**承接：需要人工裁決落點** |
| 2 | **單則訊息長度上限的數值（4000 字元）是本站選的** | `security-design.md §三` 逐字把數值留給下游並註明「若數值須由產品決定，該站須重新提交使用者」。本站選 4000（給 `scalability-requirements.md` 的每則平均 500 B **假設值** 8 倍餘裕），**但它無法同時滿足 `NFR4.40`**：最壞情況 3 × 200 × 4000 字元遠大於以平均值算出的 300 KB／session，故「300 個同時存活」只在**平均**假設下成立。`NFR4.41` 要的「**可計算的**硬上界」已滿足（上界存在且可算）。**刻意不為它新增第二個環境變數**（本計畫只授權一個）。**承接：產品面確認該數值** |
| 3 | **`meta.userId` 沒有寫入端** | `entities.md` 宣告 `userId` `required: true`，但 `K-09` 的凍結介面裡**只有 `set_work_target` 帶身分**（`principal`）；`append_message`／`set_sharing_mode`／`touch` 都沒有。故一個只被 `append_message` 建立的 session，其 `userId` 為 `null` 直到第一次 `set_work_target`。本站**不自行猜它**。緩解：`sessionKey` 本身由使用者 id 推導（`x-session-key-derivation`），讀取端可自行解析。**這是契約端點三問「誰寫」那一腿的缺口**。**Owner：`U13 brain-gateway` 的 code-generation**（它是握手端、也是推導 session key 的那一方，故它是唯一能在不改 `K-09` 介面的前提下補上 `userId` 的單元）。若它判定需要改 `K-09` 的介面，則須循 `OQ-N4` 的形式另取授權 |
| 4 | `OPEN-N10-3`／`OPEN-N10-7` | 承接 `U12`（工作項集合共用同一個 key，不在本單元的記憶體上界內；其 Hash 欄位名不得與 `seg:`／`tgt:`／`meta` 衝突）。本站的 `decode_session` **忽略未知前綴欄位**，為它預留了空間 |
| 5 | `OPEN-N10-1`／`OPEN-N10-2`／`OPEN-N10-4` | **無自然承接站**，已於前站閘門重新提交，本站不改變其狀態 |
| 6 | `tcms-test-cases`（`project.md ## Mandated` 的 **blocking** stage） | 至今未對本 intent 任何單元執行過。本單元未改變這個事實 |
| 7 | `security-design.md §二` 的 **`EVAL` ACL 部署時查核** | 該檔把「app 使用者（`+@all -@admin -@dangerous`）能否執行 `EVAL`」列為依文件推理、**非實地執行**，並指派本站做部署時查核。本站**未新增**一個獨立的 `EVAL` 探測步驟——新的還原驗證步驟會在 `restart` 後實際讀寫 fixture，但它用的是 `HSET`／`HGETALL`，**不是 `EVAL`**。故該查核仍未關閉——若 ACL 真的拒絕 `EVAL`，失敗會發生在**每一次** `append_message` 上。**Owner：`deployment-execution`**（首次把本單元部署到 staging 的那一次），具體動作是以 app ACL 身分實跑一次 `EVAL`（例如 `EVAL "return 1" 0`）確認不被 `NOPERM` 拒絕。**本單元的還原驗證步驟不能代替它**：該步驟用的是 `HSET`／`HGETALL` |

## 十、ADR-0006 四面向：程式落點（**不改任何判定**）

| 面向 | 判定 | 本單元的程式落點 |
|---|---|---|
| **IAM** | 適用（最重的一格） | `session_store.set_work_target` 的「解析在前、寫入解析結果」（突變 M3 驗證）；allow/deny 雙向測試**對第二段也各跑一次**（`BR4.7`）；`redis_gateway.build_redis_client` 拒絕 `default` 身分（`NFR4.44`）。**未新增任何 story id** |
| **Encryption** | 適用，無增量 | 不新增儲存體；憑證沿用 `U1` 的 ACL 路徑（`REDIS_USER`／`REDIS_PASSWORD`）。**不寫「不適用」** |
| **Network exposure** | 適用，**零增量** | 不開任何埠、不註冊任何 router；`openapi.json` 的 grep 為 0 命中即其機械證據（第三節） |
| **Audit logging** | 適用 | `session_log_fields` 的白名單**簽章**（七個 keyword-only 參數）＋ `log_session_event` 的執行期守衛；兩支 Lua 都不呼叫 `redis.log` |

**四面向皆適用，無不適用項。**

## 十一、公開 repo 的輸出禁令——落實與驗證

本單元持有**個人對話內容**，而本 repo 為 public、Actions log 公開可讀。

| 禁令 | 落點 | 驗證 |
|---|---|---|
| 日誌不得含 `text`／整個段／整個 session | `session_log_fields` 的**簽章**（白名單，非黑名單） | `test_session_contract.py::LogWhitelistIsASignatureTest`（4 條，含「不得把 session 物件格式化進 logger 呼叫」的 AST 掃描）＋ `test_session_store_behaviour.py` 的執行期字串比對 |
| Lua 的 `ARGV` 內容不得被記錄 | 兩支腳本都不呼叫 `redis.log` | `test_session_contract.py::test_scripts_are_static_files_with_a_dispatch_marker`（**只比對非註解行**——見下方） |
| 部署後驗證的 fixture 不得含真實樣貌的對話文字 | `deploy.yml` 的 fixture 一律 `fixture-msg-N` | 人工核對 ＋ 步驟內註解逐字說明理由 |
| 錯誤訊息不得回傳他人 session 的任何欄位 | `SessionBackendUnavailable` 只帶 `reason`／`method`；`SessionMessageTooLong` 只帶長度數字 | `test_too_long_message_…` 斷言例外訊息不含被拒的文字 |

> **我在寫第二條的測試時就踩了它要防的那個陷阱。** 第一版斷言是
> `assertNotIn("redis.log", source)` 對**整個檔案**比對——而兩支腳本的檔頭都逐字
> 寫著「本腳本不呼叫 `redis.log`」，所以它必然紅燈，而唯一的「修法」會是把那句
> 說明刪掉。這正是 `test_memory_contract.py` 檔頭記過的同一個陷阱
> （「量測純度要看程式行，不是整個檔案的字串命中」）。改成只比對非註解行。

## 十二、實作中發現並修掉的三個自己的錯（如實記載）

1. **`deploy.yml` 的 `echo` 字串裡有未轉義的反引號。** 我寫
   `echo "...pageModes inside \`meta\` -- ..."`，而反引號在 bash 的雙引號內是
   **命令替換**——它會去執行一個叫 `meta` 的指令。以 `yaml.safe_load` 取出
   `run:` 全文再跑 `bash -n` 才抓到；改掉之後複驗「剩下的 10 個反引號**全部**
   落在 shell 註解行」。
2. **兩條測試的前提本身是錯的**（不是程式有 bug）：
   (a) 我斷言 `load` 回傳的剩餘 TTL 小於滿額，但 `BR1.3` 要求 `load` **自己也
   續期**，所以續期後的剩餘期本來就是滿額——改為斷言「它來自 Redis 的 `TTL`
   回覆而不是行程內算出來的」，並寫明「少於滿額」只有在重啟情境下才有意義。
   (b) deny 面我斷言 `tgt:workspace` **不存在**，但它在 `switch_to_isolated`
   時就已由 `BR4.2` 的初始化複製寫入了（那正是 `BR4.7` 唯一的例外）——改為
   斷言「被拒的那次呼叫**沒有改動它**」。這一條修完比原版更有力。
3. **一條靜態斷言把唯一正確的實作判為違規。** 「logger 呼叫的引數不得出現
   `fields`」會命中 `log_session_event` 自己——而它是**唯一被授權**的輸出點，
   且它收到的 dict 已過白名單守衛。改為排除該函式的行號範圍。

## 十三、計畫步驟完成度

| Step | 狀態 |
|---|---|
| 1（結構與設定骨架） | ✅ 1.1 ✅ 1.2 ✅ 1.3（本檔第四節） |
| 2（執行器 ＋ 例外型別） | ✅ 2.1 ✅ 2.2 |
| 3（資料模型實作） | ✅ 3.1 ✅ 3.2 ✅ 3.3 |
| 4（資料模型測試） | ✅ 4.1 ✅ 4.2 ✅ 4.3 |
| 5（儲存層實作） | ✅ 5.1 ✅ 5.2 ✅ 5.3 ✅ 5.4 ✅ 5.5 |
| 6（儲存層測試） | ✅ 6.1 ✅ 6.2 ✅ 6.3 ⚠ 6.4 **見下方說明** |
| 7（商業邏輯 ＋ Lua） | ✅ 7.1 ✅ 7.2 ✅ 7.3 ✅ 7.4 ✅ 7.5 ✅ 7.6 |
| 8（商業邏輯測試） | ✅ 8.1 ✅ 8.2 ✅ 8.3 ✅ 8.4 ✅ 8.5 ✅ 8.6 ✅ 8.7 ✅ 8.8 |
| 9（部署驗證） | ✅ 9.1 ✅ 9.2 ✅ 9.3 ✅ 9.4 ✅ 9.5 |
| 10（前端） | ➖ 不適用（計畫明訂），**零前端檔案** |
| 11（環境／建置） | ✅ 11.1（第 16 項見第二節末）✅ 11.2 ✅ 11.3 ✅ 11.4 ✅ 11.5 |
| 12（文件與追溯） | ✅ 12.1 ✅ 12.2 ✅ 12.3 ✅ 12.4 |

### Step 6.4 的時序偏離（如實記載）

計畫把 `redis_gateway` 與 `session_store` 兩個元件的測試放在**同一個檔**
（`§三` 的表格如此切分），所以 Step 6.4 的指令
`python -m unittest tests.test_session_store_behaviour` 在 Step 7 之前**無法執行**
——該檔會 import 尚不存在的 `session_store` 而在載入階段失敗。

**實際執行順序**：Step 6 的替身與 gateway 測試**先寫完**（在 `session_store.py`
存在之前），Step 7 實作，然後該檔跑第一次並涵蓋 6.4 與 8.x。
**`test-after` 的「每層先實作再測」對兩層都成立**（gateway 的實作在它的測試之前、
store 的實作在它的測試之前），偏離的只是「6.4 這次指令執行的時點」。
不把它記成 ✅，因為那次指令並沒有在計畫指定的位置跑過。


---

## 十四、審查指出的三項缺陷——修正紀錄

協調者對本單元的產出查出三項，**三項我都獨立複驗過，三項都成立**。

### 缺陷 1：`traceability.json` 從未跑過 traceability sensor

我寫完該檔就交付了，**沒有執行**
`bun .claude/tools/aidlc-sensor-traceability.ts --output-path <該檔>`。
實際執行的結果是 `pass:false`、**63 項發現**（7 項 `invalid_entries` ＋ 56 項
`invalid_targets`）。兩個根因，都是我沒讀 sensor 就自創格式：

1. **狀態字彙不是我以為的那組。** 合法值恰為
   `OK`／`GAP`／`ORPHAN`／`Deferred`／`N/A`（`aidlc-sensor-traceability.ts:10`），
   而我用了 `PARTIAL`（×6）與 `OPEN`（×1）。
2. **`target` 是一個路徑欄位，不是敘述欄位。** sensor 對 `status == "OK"` 的列
   會 `existsSync(resolve(projectRoot, target))`（`:513-533`），而我把多個路徑
   用 `；`／`＋` 串成散文，於是整串被當成一個檔名、56 列全部回報「檔案不存在」。

**處置**：`target` 改為**單一存在的路徑**，敘述全部移進新增的 `note` 欄位
（`validateEntry` 不拒絕額外欄位，`:111-127`）。現在
**`pass:true`、`findings_count: 0`**。

修正過程中又學到兩條 sensor 規則，記在這裡以免下一個人重走：

- **`N/A` 也要求 `target` 非空**（`:583`）。而 `N/A` 依定義沒有程式路徑可指，
  故依上游 `infrastructure-design/traceability.json` 的既有慣例放**簡短的真實
  理由**，完整理由在 `note`。兩者由同一段程式推導，不會各自漂移。
- **`GAP` 一律計入 `findings_count`**（`:619-626`），所以任何 `GAP` 都讓
  sensor 永遠紅。

### ~~⚠ 一個需要協調者裁決的判斷：那兩項我選了 `Deferred` 而不是 `GAP`~~

> **🔴 已被推翻（2026-10-10）。兩項皆已改為 `GAP`，見下方第十五節。**
>
> **以下原文刻意保留、不改寫。** 本專案的紀律是「這個決定曾經是另一個樣子」
> 本身就是後來的讀者需要的證據（與被推翻的作答保留原文並加 supersession 註記
> 同一個理由）。純比對兩版文件的人若看到它被整段替換，會以為從頭就選了 `GAP`,
> 而真正該被看見的是**我當時的論證在哪裡失效**——那才是下一個人會重犯的部分。
>
> **原論證失效的那一處**（`NFR4.40`）：我拿本單元強制的上界去對照「上游以
> **平均值**推導出的 300 KB」，然後因為那個平均假設沒變就說該條不變。
> 但該條要求的是「**≥300 個已填滿上界的** session」，而「已填滿上界」只能以
> **實際強制的上界**解讀。我手上已經有 3 × 200 × 4000 這個數字，卻沒有把它
> 除進 256 MB——除下去就是 ~106 個（CJK ~35 個），對 ≥300 直接不成立。
> **我算到了一半就停下來，而停下來的位置剛好讓結論變成我想要的那個。**

`NFR4.60` 與 `NFR4.40` 我一度標為 `GAP`（= 真的沒有覆蓋），sensor 因此仍然紅。
最後改為 `Deferred`，理由與**我沒有把它當成「為了讓 sensor 變綠」**的說明：

| id | 為什麼不是 `GAP` |
|---|---|
| `NFR4.60` | 缺的是**實作**，不是設計：形狀已由 `observability-design.md §四` 指定（`MEMORY STATS`、不放熱路徑的低頻採集點、35%／100% 門檻）。`Deferred` 的 `target` 指向該檔，`note` 寫明 `OPEN-N10-4` 記載它**無告警管道消費、無自然承接站**，故承接方式是**在閘門上重新提交使用者**，不指派一個看起來合理的站 |
| `NFR4.40` | **本單元對它的影響是改善而非劣化**。本單元引入單則 4000 字元上限**之前**，`messageHistory` 的位元組量根本**沒有上界**（那正是 `nfr-requirements` `R-02` 查出的缺口），所以「已填滿上界的 session」在此之前不是一個有限的量；之後它有限了。該條的 `300 × 300 KB = 90 MB` 算式**一直**建立在該檔自己宣告為「假設，非量測」的每則 500 B 平均值上，而 `maxmemory 256mb` 由 `U1` 擁有、本單元未改動。待辦的具體形狀是「以**實測**的每則位元組數重算那兩條算式」，owner 與單則長度上限的數值同一個（第九節開放項 2） |

**如果協調者認為這兩項應該是 `GAP`**（代價是 sensor 永遠紅，但訊號更強），
請直接告知，我改回去並把 sensor 的紅燈連同理由帶進閘門。

### 缺陷 2：`NFR4.61` 宣稱 OK 而 `sessionKey` 實際沒有被記錄

該條逐字要求「每次拋出都須產生一筆 **ERROR** 級日誌，**含 `sessionKey`** 與
失敗的方法名」。我的 traceability 列照抄了這句話，而程式**沒有做到**：
`RedisGateway._call` 根本收不到 key，所以 `session_log_fields(...)` 只傳了
`method`／`reason`／`elapsedMs`／`segmentId`。測試輸出裡就看得見——
`session_backend_unavailable {"elapsedMs": 0, "method": "load", "reason": "redis_unreachable"}`
——而我每跑一次測試都看著它，沒有把它和那條需求對照。

**為什麼既有的測試擋不住**：白名單斷言驗的是「**不得多**」（不出現 `text`／整個
session），沒有任何一條驗「**不得少**」。一個把全部欄位都拿掉的實作會通過當時
所有的測試。

**修法不是改宣稱，是改程式**：`_call`／`_command`／`eval_script` 都加上
`session_key`，八個公開方法把自己已經收到的 `key` 傳下去。

**同一個缺陷的第二個入口**（協調者只點名了 ERROR 那一處）：
`observability-design.md §二` 對 `session_retry`（WARN）列的欄位也含 `sessionKey`，
而它同樣漏了。依 `functional-design:c34` 的形狀——先盤點這個缺陷共有幾個入口，
再修——兩處一併修掉。

**補上的三條回歸斷言**（`test_session_store_behaviour.py`）：

1. `test_error_log_carries_the_session_key`——解析 ERROR 紀錄的 JSON，斷言
   `sessionKey`／`method`／`reason` 三個欄位的值。
2. `test_retry_log_carries_the_session_key`——WARN 紀錄的同一條。
3. `test_every_public_gateway_method_threads_the_session_key_into_its_log`——
   **八個**公開方法逐一驗，不只我想到的那兩個。

突變驗證 **M7**：把修正逆轉回缺陷形態 → 第 3 條的八個 subTest 全紅 → 還原 → 綠。

### 缺陷 3：32 列 `N/A` 共用一條與它們無關的理由

那句「應用層／其他單元的面向，非本單元落點；本 repo 無 APM，延遲量測落在
build-and-test」**只對 `NFR3.40`／`NFR3.43` 這類延遲條款成立**，而我把它掛在
`BR1`–`BR7`（群組標籤）、`NFR4.40`（容量下限）、`NFR4.41`（記憶體硬上界）、
`NFR5.40`（WebSocket 契約閘門）上——其中 `NFR4.41` 更直接與本檔自己的敘述矛盾：
第九節說 4000 字元上限讓它成立，而該列卻標 `N/A`。

**處置**：

- `NFR4.41` 改為 **`OK`**，target `backend/services/session_store.py`，
  note 寫出完整的上界算式（段數 3 × 每段筆數上限 × 每則字元上限，`pageModes`
  固定 2 鍵）與**明確在上界之外**的那一項（同 key 的工作項集合屬 `U12`，
  `OPEN-N10-3`）。
- `BR1`–`BR7` 各自寫明它們是**群組標籤、不是 `rules.md` 的規則 id**
  （該檔的規則一律帶子編號），出現在本表是因為群組標題引用了它們。
- `NFR5.40` 寫明閘門由 `U2` 擁有，而**本單元未改動 `K-02` 的任何 payload**
  （`ws-contract.json` 與 `brain_ws_contract.py` 都不在本單元的
  `source-manifest.json` 內），故不觸發它。
- 每一個上層 NFR 標題（`NFR1`–`NFR12`）、每一條 `NFR2.4x`／`NFR3.x`／`NFR4.1`／
  `NFR4.2` 各自一條真實理由。
- **`AC`／`FR`／`US` 的 32 列改為機械推導**：掃 `rules.md` 的每一個 `BR` 區塊，
  找出**條文逐字引用該 id** 的規則當作它在本單元的承載（例如 `AC3.1.3` →
  `BR4.2`、`FR6.1` → `BR3.3`）。掃描結果為空的 19 列**如實寫「`rules.md`
  沒有任何 BR 引用它，承載完全在消費端」**，不硬指一條 BR 充數。

結果：66 列 `N/A` 的 `target` 由 2 條共用文字變成 **39 條**、`note` **48 條**。
仍有重複的 7 組，但每一組的那句話對它的每一個成員都**為真**（例如「`rules.md`
無任何 BR 引用它」是逐 id 機械掃描的結果），這與原本「把延遲的理由掛在容量條款
上」是不同性質的事。

### 這一輪我自己在修正過程中抓到的一個錯

為 `AC`／`FR`／`US` 推導承載時，我第一版同時掃 `rules.md` 的 `BR` 與
`entities.md` 的 `EC`，結果 `AC3.1.2` 被對應到 `EC6`。開檔核對
`entities.md` 的 `EC6` 全文——它是「本實體的任何欄位都不得出現在任何 log」，
**完全沒有提到 `AC3.1.2`**。成因是我以縮排切 `EC` 區塊，而 `EC6` 的區塊一路
吃到了下一個實體。**若照它寫下去，追溯表會帶著一組憑空的對應關係**，而那種
錯誤看起來跟正確的對應一模一樣。處置：整個放棄 `EC` 推導，只保留切分可靠的
`BR` 推導。

---

## 十五、第二輪審查的裁決與兩項新發現（`R-01` Major、`R-02` Minor）

### 0. 這一輪的審查本身：收據缺失，且它看的是**已被推翻**的版本

本輪審查**確實執行過且結論有效**，但 `REVIEW_COMPLETED` 記不進 audit，
根因是引擎的 workspace source 指紋走訪 gitignored 路徑、而審查者自己跑
Hypothesis 就會重寫 `backend/.hypothesis/**`。
**完整記載見同目錄的 `reviews/review-01-unreceipted.md`，本節不重述。**

另有一項必須寫下來：**該次審查檢視的是 `NFR4.60`／`NFR4.40` 仍為 `Deferred`
的那一版位元**。本節的 `GAP` 改動發生在它之後，故它的 verdict 不涵蓋現在的
狀態——讀該審查紀錄時要連同本節一起讀。

### 1. `NFR4.60`／`NFR4.40` → `GAP`（裁決，我的 `Deferred` 被推翻）

兩條裁決理由我都接受，且第二條指出的是我的**推理錯誤**而非偏好差異。

| id | 裁決理由 |
|---|---|
| `NFR4.60` | `Deferred` 的語意是「稍後由某人覆蓋」，而 `OPEN-N10-4` 記明它**無消費者、無自然承接站**——**沒有 owner，「稍後」就沒有錨點**。本單元 `nfr-design/traceability.json` 的先例正好相反：它把 `NFR4.41` 標 `Deferred` **是因為該列指名了承接站並寫在列內**。**缺 owner 就是 gap 的定義** |
| `NFR4.40` | 我拿本單元強制的上界去對照上游**以平均值推導**的 300 KB，然後因平均假設未變就說該條不變。但該條要求「≥300 個**已填滿上界的** session」，而「已填滿上界」只能以**實際強制的上界**解讀 |

`NFR4.40` 的算式現已逐項寫進 `traceability.json` 該列的 `note`，**兩個分母都給**：

- 最壞情況／session＝3 段 × 200 則 × 4000 字元＝**2,400,000 字元**
  ＝**≈2.4 MB**（1 B/字元）；中文對話在 UTF-8 下 CJK 每字元 3 B，故真實最壞
  情況 **≈7.2 MB**。
- 對 `maxmemory 256mb`：**≈106 個**（ASCII）／**≈35 個**（CJK）。
- 對本條自己承諾的 **90 MB**（256 MB 的 35%，為 AOF 緩衝與 Redis 開銷保留）：
  **≈37 個**／**≈12 個**。
- **要求是 ≥300。**

**為什麼兩個分母都要寫**：90 MB 才是該列真正承諾的數字，只寫 256 MB 會讓這個
缺口看起來是建立在最寬鬆的選擇上。

**「本單元讓它變可見，而不是造成它」**——這句在裁決中被確認、但它**不等於**
「本條成立」：在本單元引入單則長度上限之前，`messageHistory` 的位元組量根本
沒有上界，所以「已填滿上界的 session」甚至不是一個有限的量。**把最壞情況變成
可計算的，正是讓這個容量下限的不成立浮現出來的那個動作。** 兩件事都是真的，
而只有後者是該列所斷言的。

**不以調整上界來讓它通過**：要讓 300 個成立需要每則 ≤500 B，而那會拒絕一段
正常長度的中文訊息（≈166 字），與 `FR1.1` 逐字接受的自由文字輸入牴觸。
`project.md` 明文：**目標不得為了讓步驟通過而被放寬。**

### 2. ⚠ traceability sensor 現在是**紅的，而且是刻意的**

```
{"pass":false,"gaps":["NFR4.40","NFR4.60"],...,"findings_count":2}
```

**`findings_count` 恰為 2，且兩項都是上述 `GAP`**——`invalid_entries`、
`invalid_targets`、`missing_from_table`、`missing_from_upstream_ids`、`orphans`
**全部為空**。即：**格式層已全綠，紅的只有兩個真實且已具名的缺口。**

這個紅燈**不得**被當成「追溯表沒做好」而去消除它。消除它的唯一誠實方式是
關掉那兩個缺口（實作採集點、重算容量算式），不是改狀態字。

### 3. `R-01`（**Major**，真實缺陷）：`set_sharing_mode` 不建共享段，`EC1` 為假

**我先自行複驗才動手**，用的是本單元自己的 `FakeRedis`／`make_store`：

| 第一次寫入 | 修正前的 `segments` | `EC1` |
|---|---|---|
| `set_sharing_mode(KEY, "workspace", "shared")` | `{}`（整個 session 只有 `meta`） | **假** |
| `set_sharing_mode(KEY, "workspace", "isolated")` | `{"workspace": …}`，**無** `shared`、無 `seg:shared`／`tgt:shared` | **假** |

AST 盤點確認成因：`append_message` 與 `set_work_target` **都**呼叫
`_ensure_meta`，`set_sharing_mode` **沒有**。

**可達路徑**：使用者開了 `/workspace` 或 `/assessment`，在送出任何訊息、
也還沒選定作業對象**之前**就切換模式。

**影響半徑有界但不是零**：下一次對 `shared` 的 `append_message`／
`set_work_target` 會因 Lua 的 `HGET` 回 nil 退路而自癒，故不是資料毀損；
但「共享段永遠存在」這個下游據以推論的不變量在那段時間內**不成立**，
而那正是不變量的意義。

**為什麼 79 條測試全都沒碰到**：每一條 `set_sharing_mode` 的測試都斷言
**模式與段內容**，沒有一條斷言「`shared` 段存在」；其他測試若先
`append_message` 就已順手建好 `shared`。缺的不是一個案例，是**一整類斷言**。

> **這與 `NFR4.61` 的 `sessionKey` 漏失是同一個形狀**，而那一項我在上一輪才剛
> 寫下根因。我驗了「**不得多**」（日誌不得含內容、被拒的呼叫不得留下寫入），
> **從來沒有系統性地驗「必須有」**。兩次都是同一個盲區，第二次發生在我已經
> 寫下它之後——所以可執行的補強不是「記得」，而是：**每一條 `EC`／不變量都要
> 有一條以「必須存在」為斷言的測試，而且要對全部寫入入口逐一枚舉**，不是只
> 對被點名的那一個。

**修法**：`set_sharing_mode` 在參數驗證之後、分支之前呼叫 `_ensure_meta`。

**反向界線也補了測試**：`load`／`touch` **不得**因此跟著建段——`BR1.6` 要求
`load` 對不存在的 key 回 `None`（那是新 session 的合法起點），若它們也建段，
`U13` 的 `W1` 第 5 步就變成死碼。`test_load_and_touch_do_not_create_a_session`
守住這條界線。

**新增 4 條測試**（`FirstWriteEstablishesTheSharedSegmentTest`），其中第一條
**逐一枚舉全部四個寫入入口**。突變 **M8** 驗證：移除修法 → 2 條紅 → 還原 → 綠。

**附帶：`R-01` 的修法改動了 M4 的前提，已重驗**——見第七節 M4 下方的說明。

### 4. `R-02`（Minor）：`BR4.4` 那一列的 `note` 描述了一個不存在的機制

該列原本寫「`decode_session` 逐段解碼，切回共享後讀 `tgt:shared`」，讀起來像是
`decode_session` 執行 page→segment 的路由。**它沒有**：AST 確認它的參數只有
`(session_key, fields)`，**沒有 page-scope 參數**，它只是把存在的段欄位逐一解碼。

已改寫為實情：該不變量由**資料形狀**滿足（`BR2.5` 不刪段 ＋ `BR2.6` 無合併
路徑 ⇒ 該頁讀到的歷程與作業對象必然與離開時相同），而**真正的 page→segment
選取在呼叫端**（讀 `pageModes[P]`，依 `functional-spec.md` 的 `W2` 第 2 步屬
`U13`）。

**這一類錯誤的危險在於它看起來像已驗證過的描述**：事實（切回後狀態不變）是
對的，只有**機制的歸屬**是錯的，而照它去找 `decode_session` 裡的路由邏輯的人
會找不到東西，進而懷疑的是自己而不是這份文件。

---

## 重新查驗與合併前必修第 12、18 項

> 記錄時間：2026-10-23T00:56:07Z（`date -u` 取值）。來源：使用者對整站送出
> Request Changes，本單元承接 `construction/functional-design/merge-blockers.md`
> 第 12、18 項；裁決寫在計畫第十節（Step 13–15）與 `unit-test-instructions.md §2.1`。

### 一、Steps 1–12 重新查驗（引擎重設了勾選，逐格開檔查證後勾回）

| 結果 | 步驟 | 依據 |
|---|---|---|
| 勾回 | 1.1–1.3、2.1–2.2、3.1–3.3、4.1–4.3、5.2–5.5、6.1–6.3、7.1–7.6、8.1–8.8、9.1–9.5、11.1–11.5、12.1–12.4 | 逐一開檔：目錄與檔案存在、常數與方法存在、測試類別存在；三個測試模組本輪開工前實跑 **82 條 OK**（18＋20＋44，與第六節一致）、全套 **1241 條 OK**、兩支 validator 與 `dump_openapi.py --check` 綠 |
| **未勾（新發現）** | **5.1** | `redis_gateway.py:84-87` 宣告了 `POOL_MIN_SIZE=5`／`POOL_IDLE_TIMEOUT_SECONDS=600`／`POOL_MAX_LIFETIME_SECONDS=1800`，但全 `backend/` 對這三個常數**零使用**（只出現在宣告與 `__all__`）；`build_redis_client` 只把 `POOL_MAX_SIZE` 傳給 `ConnectionPool`（`max_connections`）。即 `max 20` 成立，`min 5`／idle 10m／lifetime 30m **沒有被套用**。redis-py 的 `ConnectionPool` 本身沒有這三個參數，要做須另寫機制。第十三節把它記成 ✅，那是不實的。本輪不修（不在第 12、18 項範圍），**需要裁決**：實作、或把三個常數與計畫該格改寫為「redis-py 不支援，不實作」 |
| 維持未勾 | **6.4** | 第十三節「Step 6.4 的時序偏離」：該指令在 Step 7 之前無法執行、實際於 Step 7 之後才首次跑。先前刻意未勾且有記載，維持 |

勾回時如實記錄的兩處**後續單元合法改動**：

- **9.3「步驟置於部署序列最後」**：`U14` 的步驟 6a（`deploy.yml` 的「Verify the brain WS subprotocol survives the tunnel」）已插在本單元的還原驗證之後，故它不再是**字面上**的最後一道驗證；它仍在全部既有健康檢查之後、記錄 last-good 之前，「中斷發生在服務已確認可用之後」的理由不受影響。
- **12.4「`openapi.json`、`api.d.ts` diff 為空」**：工作樹對 `HEAD` 有 diff（167／143 行），全部來自本 intent 其他單元；本單元的貢獻以 `git diff HEAD -- openapi.json frontend/src/types/api.d.ts | grep -icE "session_store|redis|brain_session|BrainSession"` 量為 **0**，`dump_openapi.py --check` 綠；`backend/database.py` 對 `HEAD` 零 diff。與第三節同一個解讀，字面的「diff 為空」在累積多單元的工作樹上不成立。

### 二、第 12 項：寫入與續期以 MULTI／EXEC 一次送出

**先判斷 Lua 承載者**：`append_message.lua` 在同一支腳本內 `HSET`＋`EXPIRE`（`:83-84`），`switch_to_isolated.lua` 同（`:67-68`），兩者已原子，**不動**。非原子的多指令寫入共三處，全部改走新方法：

| 位置 | 原本 | 現在 |
|---|---|---|
| `session_store.py:555-590` `_ensure_meta` | `EXISTS` → `HSET meta` → `HSET seg:shared`（TTL 等下一個指令才設） | `EXISTS` → 交易（`HSET meta`、`HSET seg:shared`、`EXPIRE`） |
| `session_store.py:433-446` `set_work_target` | `HSET tgt:<seg>` → `EXPIRE` | 交易（`HSET tgt:<seg>`、`EXPIRE`） |
| `session_store.py:540-553` `_write_meta_and_expire`（`set_sharing_mode` 切回 shared） | `HSET meta` → `EXPIRE` | 交易（`HSET meta`、`EXPIRE`）。**計畫未點名這一處**，依 Step 13 第二格「同形狀的多指令寫入一併改」納入 |

新方法 `redis_gateway.py:499-547` `RedisGateway.hset_fields_and_expire(method, key, fields, ttl_seconds, *, idempotent, segment_id=None)`：`pipeline(transaction=True)`、逐欄位 `HSET` ＋ 一個 `EXPIRE`、經既有 `_call`（原因碼、重試、日誌白名單不變），未新增任何可記錄內容的參數。

**實作中發現並處理的一個新洩漏面**：redis-py 的 `Pipeline.annotate_exception` 會把例外訊息改寫成 `Command # N (<指令全文，截到 100 字元>) of pipeline caused error: …`——**被寫入的值**（作業對象識別碼的組合、meta）會進入例外訊息，而 `SessionBackendUnavailable` 以 `raise … from exc` 帶著它；同時前綴讓 `OOM ` 字串退路失效。處置：`redis_gateway.py:286-308` `_strip_pipeline_annotation` 就地拿掉前綴（型別不變）。以真實 redis-py 8.1.0 實測：`annotate_exception` 與 `truncate_text(max_length=100)` 的原始碼如上述；WRONGTYPE 情境下未處理時訊息為 `Command # 1 (HSET u10-...) of pipeline caused error: WRONGTYPE …`（本例 key 很長，截斷後未含值；key＋欄位較短時值會落在前 100 字元內）。

**已知、未處理的既存窗口（不在第 12 項範圍）**：`_ensure_meta` 的 `EXISTS` 與交易之間不是原子的——兩個並行的第一次寫入都可能看到「不存在」，後到者的交易會把先到者剛追加的 `seg:shared` 蓋回 `[]`。這在本輪之前就存在（當時是兩次獨立 `HSET`），交易沒有讓它更好或更壞。修法候選是交易內改用 `HSETNX`，但那會改變計畫寫明的「多個 `HSET`」形狀，故未做，**需要裁決是否另開一項**。

### 三、第 18 項：每段 200 KB 位元組上限

| 位置 | 內容 |
|---|---|
| `session_types.py:220` | `DEFAULT_SEGMENT_MAX_BYTES = 200 * 1024`（非環境變數） |
| `session_types.py:223-241` `cjson_encoded_size` | 量「cjson 編碼後的位元組數」。**實測 Redis 8.8.0 的 cjson 與 Python json 只有兩處長度不同**：`/` → `\/`（＋1）、`0x7f` → `\u007f`（＋5）（`redis-cli EVAL "return cjson.encode({a='x/y\127', b='中'})"` 的 `od -c` 輸出；`string.len` 分別為 18、11）。不補這兩項，Lua 與參考實作在臨界值附近會丟不同筆數 |
| `session_types.py:244-247` `segment_size_bytes`、`:250-` `trim_history(messages, cap, max_bytes=DEFAULT_SEGMENT_MAX_BYTES)` | 兩條件取較嚴者，自最舊端丟；**剩一則時停止**（段不得被清空——cjson 會把空表編成 `{}`） |
| `append_message.lua:39`、`:58-81` | `ARGV[5]` 為位元組上限；每則 `string.len(cjson.encode(arr[i]))` 只編碼一次，整段 = 2 ＋ Σ ＋ (n−1)；迴圈 `while #arr > 1 and (#arr > cap or total > max_bytes)` |
| `session_store.py:119`、`:123`、`:202-213` | 「單則不可能超過段上限」的前提以算式確認、不成立即 `raise ValueError`（不用 `assert`，`-O` 會拿掉它）。**對計畫算式的更正**：計畫寫「4000 字元 × 最多 4 位元組 = 16 KB」，但 cjson 對控制字元與 `0x7f` 輸出 6 位元組的 `\u00XX`，最壞是 4000 × 6 ＋ 封套保留 1024 ＋ 2 = **25,026 B**，仍遠小於 204,800 B，前提成立、結論不變 |
| `session_store.py:306` | `append_message` 把 `self._segment_max_bytes` 傳為 `ARGV[5]` |

**容量重算（以 Python 實算，非手寫）**：

| 算式 | 值 |
|---|---|
| 一則 4000 個中文字的訊息（含封套） | 12,087 B；一段只放得下 **16** 則（193,409 B） |
| 單一 session 最壞 | 3 × 204,800 = 614,400 B ≈ 600 KB |
| 256 MiB 的 80% ÷ 600 KB | **349.5**（計畫以十進位概算寫 340；兩者都 ≥ 300） |
| 256 MiB ÷ 600 KB | 436.9 |
| 300 個最壞 session | 175.8 MiB ＝ `maxmemory` 的 **68.7%** |
| 對原算式自己承諾的 90 MB | 153.6 個 |

**一個須讓下游知道的落差（不是裁決製造的正確性問題，故未停下）**：`NFR4.40` 的要求是「≥ 300 個已填滿上界的 session **不觸及 `maxmemory`**」，以最壞值成立（68.7%）；但它的推導欄寫「90 MB，為 256 MB 的 35%，留 2.8 倍餘裕給 AOF 緩衝與 Redis 開銷」，以最壞值計餘裕只剩約 1.45 倍。另 `observability-design.md` 對 `NFR4.60` 定的 35% 門檻在最壞情況下約 150 個 session 就會觸發——`NFR4.60` 本身仍是 `GAP`（無採集點、無告警管道），故目前沒有實際後果。

文件同步（只改註解，未新增變數；`maxmemory 256mb` 與 `noeviction` 不變）：`deploy/.env.example:145-149`、`deploy/docker-compose.deploy.yml:259-267`（redis `command:` 的 `--maxmemory` 旁）、`DEPLOY.md`「`maxmemory 256mb` 的暫定依據」整段改以最壞值表達＋新增「`noeviction` 滿載時會發生什麼、怎麼觀察」（`MEMORY STATS` 以 app 身分執行的指令）。**偏離計畫的兩處擴充**：(1) `backend/.env.example:147-149` 有同一個過期事實（`≈ 300 KB／session`），一併改；(2) 依 `project.md` 規則「改任一 `.env.example` 要同步 `LOCAL-DEV.md`」，`LOCAL-DEV.md:357-359`（同一句的鏡像）與 `:647`（新增一列疑難排解：長訊息時不到 200 則就丟最舊——這是把行為當成判斷依據的那一類文件，不改會讓人把正常行為判成 bug）。

順帶修正一個本單元自己的過期引用：`deploy.yml:511` 寫 healthcheck 的說明在 `docker-compose.deploy.yml:258-261`，實際在 `:307-310`（本輪之前已過期；本輪在 compose 插入 9 行註解後更遠）。**未修**：`memory-retention-purge.yml:55` 引用 `docker-compose.deploy.yml:345`（`U9` 的檔，實際在 `:395`，同樣是本輪之前就過期）。

### 四、新測試

| 檔案 | 類別 | 條數 |
|---|---|---|
| `tests/test_session_store_behaviour.py:1040-` | `TransactionalWriteTest`（替身 MULTI／EXEC 語意、建立即帶 TTL、四入口在 EXPIRE 持續失敗時不留無 TTL key、`set_work_target` 與切回 shared 的單一交易、pipeline 例外訊息去值、空欄位拒絕） | 7 |
| 同檔 `:1203-` | `SegmentByteCapTest`（4000 字中文灌滿一段觸發位元組上限、短訊息仍由筆數上限截、前提不成立拒絕建構、上限確實傳入 Lua `ARGV[5]`） | 4 |
| 同檔 `:1311-` | `RealRedisParityTest`（**opt-in**，`REDIS_URL` 未設定即 skip 並印原因，判定沿用 `tests_redis.redis_skip_reason`）：Lua 與參考實作逐步一致、真實交易帶 TTL、真實 pipeline 錯誤去值 | 3（CI 中 skip） |
| `tests/test_session_types.py:102-` | `TrimHistoryByteCapPropertyTest`：2 條 `@given`（兩上限同時成立；最長合格後綴且順序不變）＋ cjson 長度實測值 1 條；另 `test_cap_must_be_a_positive_integer` 加位元組上限的拒絕案例、property ③ 改寫為「兩上限內不動」 | ＋3 |
| `tests/test_session_contract.py:283-298` | 迴圈條件斷言改為新的兩條件形狀 ＋ `string.len(cjson.encode(arr[i]))` | 0（改寫既有 1 條） |

替身（同檔 `FakeRedis`／新 `FakePipeline`）新增 `pipeline(transaction=True)`：EXEC 前只排佇列、EXEC 時依序全部套用；`fail_next`／新的 `fail_commands`（持續失敗，模擬行程在送出該指令時死掉）命中時在套用任何指令之前拋出。`WorkItemFakeRedis` 等子類別自動繼承。新增測試的規格註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`）以 docstring 承載；本單元無端點與 UI，故不寫 `@api`／`@ui`。

### 五、突變驗證（每項先 `grep -c` 確認寫入、跑測試看紅、還原、`grep -c` 為 0、複驗綠）

| # | 突變 | `grep -c` 寫入／還原 | 結果 |
|---|---|---|---|
| M12 | `hset_fields_and_expire` 改為逐條 `HSET`…`EXPIRE`（不用交易） | 3 ／ 0 | `test_interruption_before_exec_never_leaves_a_key_without_ttl` **4 個子案例全紅**（四入口皆留下無 TTL 的 key）；另 6 條交易形狀案例連帶紅（7 failures ＋ 1 error／58）。還原後 58 OK |
| M12S | 拿掉 `_strip_pipeline_annotation` 呼叫 | 1 ／ 0 | 替身案例 `test_pipeline_error_message_loses_the_written_values_but_keeps_the_reason` 紅；真實 Redis 案例 `test_real_pipeline_error_is_classified_and_stripped_of_written_values` 紅（訊息為 `Command # 1 (HSET u10-...) of pipeline caused error: WRONGTYPE …`） |
| M18 | 參考實作拿掉 `or total > max_bytes` | 1 ／ 0 | `TrimHistoryByteCapPropertyTest.test_output_fits_both_caps` 與 `SegmentByteCapTest.test_full_length_cjk_messages_hit_the_byte_cap_not_the_count_cap` 紅（2 failures／79） |
| M18L | Lua 拿掉 `or total > max_bytes` | 1 ／ 0 | CI 可見的只有 `test_the_lua_script_contains_the_trim_loop`（靜態）紅；真實 Redis `test_lua_trim_matches_the_reference_on_the_same_input` 15 個子案例紅（第 5 輪起分歧，即位元組上限開始觸發處） |
| M18C | `cjson_encoded_size` 拿掉 `/`、`0x7f` 的補正 | 1 ／ 0 | `test_cjson_size_counts_the_escapes_python_json_does_not_emit` 紅；真實 Redis 一致性案例自第 0 輪起紅（位元組數不相等） |

**誠實限定**：M18L 在 CI 只由一條字串靜態斷言抓到——Lua 的真實行為 CI 驗不到（第八節同一條限制）。M12 在替身上驗的是**呼叫形狀與語意模型**；真實 Redis 的交易原子性見下節本機實測，不在 CI。

### 六、本機真實 Redis 實測（scratchpad 臨時 `redis-server`，跑完已 `shutdown nosave`）

Redis 8.8.0（`/opt/homebrew/bin/redis-server`，未安裝新套件）、redis-py 8.1.0（`backend/.venv`）。

| 實測 | 結果 |
|---|---|
| `MULTI` → `HSET` → `HSET` → 斷線（不送 `EXEC`）（`scratchpad/redis/multi_abort_probe.py`） | `EXISTS = 0`、`TTL = -2`：交易整個被丟棄 |
| 對照組：逐條 `HSET`、`HSET`，在 `EXPIRE` 前停止 | `EXISTS = 1`、`TTL = -1`：**第 12 項描述的缺陷形態實際重現** |
| `--maxmemory 2mb --maxmemory-policy noeviction` 灌滿後呼叫 `hset_fields_and_expire`（`oom_probe.py`） | `reason = redis_oom`、cause 型別 `OutOfMemoryError`、訊息不含寫入值、key 未建立 |
| `REDIS_URL=redis://localhost:6397/15 … -m unittest tests.test_session_store_behaviour.RealRedisParityTest tests_redis.test_work_item_lua` | **8 tests OK**（本單元 3 ＋ `U12` 既有 5，確認 gateway 的改動沒有弄壞工作項腳本） |

### 七、各命令實際數字（自 `backend/`，`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest …`）

| 指令 | 結果 |
|---|---|
| `tests.test_session_types` | 21 tests OK（原 18） |
| `tests.test_session_contract` | 20 tests OK |
| `tests.test_session_store_behaviour` | 58 tests OK（skipped=3，即 opt-in 真實 Redis 三條；原 44） |
| `discover -s tests`（全套） | **1258 tests OK（skipped=3）**；開工前 1241 OK，差 17 ＝ 3 ＋ 14 |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |
| `.venv/bin/python scripts/dump_openapi.py --check`（自 repo 根以 `backend/scripts/…`） | 規格檔與後端程式碼一致 |
| `bun .claude/tools/aidlc-sensor-traceability.ts --output-path …/traceability.json` | `pass:false`、`gaps:["NFR4.60"]`、`findings_count:1`（原為 2：`NFR4.40` 已由第 18 項關掉並改為 `OK`；`NFR4.60` 仍是刻意的真實缺口，見第十五節） |

### 八、追溯與清單

- `traceability.json`：新增 `MB-12`（`OK`，target `backend/services/redis_gateway.py`）、`MB-18`（`OK`，target `backend/services/session_scripts/append_message.lua`），兩者也加入 `upstream_ids`；`NFR4.40` 由 `GAP` 改 `OK`（note 保留原記載並寫明改狀態的依據與兩個仍須知道的落差）；`BR3.4`、`NFR4.41` 的 note 補上位元組上限。
- `source-manifest.json`：本輪動到的程式與文件路徑**全部已在既有 `writes` 內**，故未改動（`merge-blockers.md` 屬 record，不是 source）。
- `merge-blockers.md` 第 12、18 列「處置」欄已回填。
- `brain-infra` 的 `traceability.json`／計畫 Step 6 仍寫 `allkeys-lru` 的過期敘述：不屬本單元，由 `brain-infra` 的記錄承接（該處已記載）。

### 九、未驗項

- 真實 Redis 的交易原子性與 Lua 位元組修剪**不在 CI**：`ci.yml` 的 backend job 沒有 Redis，`RealRedisParityTest` 在 CI 中 skip。本機實測結果見第六節；staging 上首次部署時仍應以 app 身分跑一次 `EVAL`（第九節開放項 7 未變）。
- `noeviction` 在 256 MB 下的真實滿載行為未驗（只在 2 MB 的臨時實例上驗了分類路徑）。
- 容量算式的 Redis Hash 內部開銷（欄位超過 64 位元組即改用 hashtable 編碼）未量測；600 KB 是值的大小上界，不含結構開銷。

### conductor 處置實作方提出的兩項裁決請求（`2026-10-23T01:06:28Z`）

兩項皆屬工程判斷而非產品決定，conductor 直接處置：

| 項 | 處置 |
|---|---|
| `_ensure_meta` 的並行窗口（`EXISTS` 與交易之間非原子，後到者的預設值可把先到者剛追加的 `seg:shared` 蓋回 `[]`——資料遺失） | `redis_gateway.hset_fields_and_expire` 新增 `only_if_absent` 參數（改送 `HSETNX`）；`_ensure_meta` 以它建立預設值，後到者成為 no-op、只續期 TTL；`EXISTS` 保留為快速路徑。替身新增 `_cmd_hsetnx`。新測試 `test_concurrent_first_write_does_not_wipe_the_shared_segment`（把 `EXISTS` 替換為「不存在」重現競態窗口，斷言共享段與 meta 不變）；既有 `test_session_creation_writes_and_ttl_in_one_transaction` 的期望改為 `HSETNX, HSETNX, EXPIRE`。突變 M12N（改回 `HSET`；`grep -c` 確認為 1）→ 兩案紅；還原後為 0。屬第 12 項同一交易機制的延伸，在已核可計畫 Step 13 的意圖之內 |
| 計畫 Step 5.1 的連線池 min／idle／lifetime | redis-py 的 `ConnectionPool` 沒有對應參數，三個常數（`POOL_MIN_SIZE`／`POOL_IDLE_TIMEOUT_SECONDS`／`POOL_MAX_LIFETIME_SECONDS`）宣告卻從未生效，屬死碼（`team.md`：零死碼紀律）。已自 `redis_gateway.py` 與其 `__all__` 移除，註解改寫為事實；`git grep` 確認 repo（`aidlc/` 以外）無其他引用。Step 5.1 **維持未勾**——其字面要求在此函式庫上不可實作，而不是被做到 |

驗證：本單元三個測試模組 `Ran 100 tests` → `OK (skipped=3)`；完整套件（`backend/.venv`）`Ran 1259 tests` → `OK (skipped=3)`；`__all__` 中的名稱皆可解析。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T13:27:22Z -->

本輪只查驗、未改任何程式或測試。計畫 60 格勾選 58 格（機械計數：`[x]` 58、`[ ]` 2）。

| 格 | 未勾理由 |
|---|---|
| 5.1 連線池 | 只有 `max 20`（`redis_gateway.py:88`）；`min 5`／idle 10 分／lifetime 30 分在 redis-py `ConnectionPool` 上無對應參數，三個死碼常數已於前輪移除（見上節） |
| 9.3 步驟置於部署序列最後 | 已不成立：`deploy.yml:447` 的 Redis 重啟還原驗證之後，多了 U14 的阻擋步驟 `Verify the brain WS subprotocol survives the tunnel`（`:586`）。WS 檢查失敗時，使用者 session 已被重啟中斷才回滾；步驟註解 `:443-446` 的「placed LAST」與現況不符。宣告會中斷 session 與 TTL 區間判斷兩項仍成立 |

勾選但帶說明：6.4 本輪實跑全綠而勾（前輪刻意未勾的紀錄 `code-summary.md:496` 因此與計畫不一致）；Step 13、14 的突變紅燈引用既有紀錄，本輪未重跑；11.1 根目錄 `docker-compose.yml` 不起 backend，條件不觸發。

測試（`backend/.venv`、`-B`、`PYTHONDONTWRITEBYTECODE=1`）：本單元五個模組 112 OK（skipped 3，為需 `REDIS_URL` 的 `RealRedisParityTest`）；完整套件 1319 OK（skipped 3）。暫起本機 `redis-server` 8.8.0（127.0.0.1、不存檔）：`RealRedisParityTest` 3 ＋ `tests_redis.test_work_item_lua` 7 共 10 OK，已關閉並刪除資料。兩支 contract validator 與 `dump_openapi.py --check` 綠燈；repo 快取前後 mtime 不變。

合併前必修：
- **#12 屬實已解決**：`hset_fields_and_expire` 以 `pipeline(transaction=True)` 包住 HSET／HSETNX＋EXPIRE，`_ensure_meta`／`set_work_target`／切回 shared 皆經它；真實 Redis 補驗三個首寫入口皆帶 TTL 86400、EXEC 前斷線不留 key、`noeviction` 超限時 Lua 與交易路徑皆回 `reason=redis_oom` 且不留半成品、讀取照常。
- **#18 屬實已解決**：`DEFAULT_SEGMENT_MAX_BYTES = 200*1024`，Lua 與參考實作同語意取較嚴者，`SessionStore` 建構時以算式拒絕不可能的設定；`maxmemory 256mb`＋`noeviction` 未改。

已核可計畫／測試說明與程式的落差（不回改計畫）：交付物表 #11 寫 `BRAIN_SESSION_HISTORY_MAX`「無值」而 Step 11.1 寫「值 200」，程式照 11.1；Step 14 的「≈340 個 session」現行文件已為 308.8（U12 計入工作項，每 session 695,400 B，餘裕約 2.9%）；`unit-test-instructions.md` 的指令未帶 `-B` 與 `HYPOTHESIS_STORAGE_DIRECTORY`，照字面跑會留快取。

候選問題（未修，交審查與使用者判定）：(1) 308.8 以序列化位元組計，本機 `MEMORY USAGE` 多約 1.8%，staging 映像預設 jemalloc 依級距推算可能多約 14%（推算、未量測），「300 session 在 80% 以內」可能不成立；(2) 還原驗證 `hgetall | sort`（`deploy.yml:499/544`）抓不到兩欄位值互換；(3) 即上表 9.3 的順序；(4) `redis-cli --pass` 使密碼出現在 runner 程序清單；(5) `_ensure_meta` 的 `EXISTS` 與後續寫入間 key 到期，可重建出缺 `seg:shared` 或 `meta` 的 key（TTL 仍在）。
