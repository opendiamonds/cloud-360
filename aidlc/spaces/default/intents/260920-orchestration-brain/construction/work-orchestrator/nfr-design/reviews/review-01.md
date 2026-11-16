## Review
**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-12T06:12:33Z
**Iteration:** 1

### Findings

| ID | Severity | Status | Location | Finding | Required action |
|---|---|---|---|---|---|
| R-01 | Major | New | nfr-design/security-design.md 第二節；nfr-design/reliability-design.md 第二節 | 帶入項 1 的 shield 設計與 client 生命週期互相打架。security-design 第二節規定「每次 `_run` 建一個 AsyncClient，用完即關」；reliability-design 第二節要 `_finish_persist`（含 PUT）在外層 `_run` 被取消後照常跑完。若 PUT 使用 `_run` 的 client（設計沒說用哪一個），`_run` 被 correct 或牆鐘上限取消時 `async with` 先關閉 client，在途的 PUT 隨之失敗或遺失，變更紀錄不會寫、sideEffect 停在「可能已存回」。這正是 NFR12.20 要防的失敗，替身測試（PUT 延遲、期間 correct）用不關 client 的替身時還會綠燈。 | 明寫 `_finish_persist` 自己擁有 PUT 用的 AsyncClient（在協程內建立與關閉，token 以參數傳入），不借用 `_run` 的 client；NFR12.20 的測試替身須使用真的 AsyncClient＋ASGITransport，使「外層取消後 client 被關」可被觀察到。 |
| R-02 | Major | New | nfr-design/scalability-design.md 第一、二節；nfr-design/reliability-design.md 第一節 | 帶入項 7 只做了一半。設計把兩支 Lua 設為 `idempotent=False`，但 redis_gateway.py 的 `_call`（約 330-390 行）在非冪等路徑遇連線錯誤時直接拋 `SessionBackendUnavailable`，此時寫入可能已生效。`_advance` 只描述 `ok` 為真／假兩種結果，沒有第三種「寫入結果未知」。依 reliability 第一節「先寫再送」，例外傳回 `_run` 最外層會判工作項失敗，而實際可能已推進到 request_sent（卻從未送出請求）；之後復原掃描又以 `unknown` 標示，使用者看到的是不實的副作用。nfr-requirements review-01 R-01 明確要求「呼叫端以重讀確認而非盲目判定」，本站沒有承載。 | 在 scalability-design 第二節補第三種結果：捕捉 `SessionBackendUnavailable` → 重讀該工作項 → 若 status／dispatchStage 已等於目標值視為成功，否則視為失敗；寫明重讀本身再失敗時的處置（不送請求、工作項失敗，sideEffect 依重讀不到時的保守值）。測試判準採「寫入成功但回應連線錯誤」替身，斷言能力替身只被呼叫一次。 |
| R-03 | Major | New | nfr-design/performance-design.md 第二節；nfr-design/reliability-design.md（無牆鐘章節） | 帶入項 13（可注入時間）只對成本輪詢成立。設計把 `clock`／`_sleep` 注入並讓輪詢迴圈自己比對 `deadlineAt`，但 BR56.6 規定背景執行以 `asyncio.wait_for` 包住，`wait_for` 用事件迴圈的單調時鐘，不受注入的 clock 影響。NFR12.19 的判準（能力替身永不返回、假時鐘推進 300 秒）在 A1／A3 路徑上沒有可行做法：要嘛真等 300 秒，要嘛自行發明。同時 NFR12.3「至多 180 次」的計法（首次輪詢是否計入、deadline 比對在輪詢前或後）設計沒寫，t=0 立即輪詢加上 t=358 為第 180 次，t=360 才判逾時，需要明文。 | 把「逾時機制」也做成可注入的元件（例如建構參數 `timeout_runner`，預設 `asyncio.wait_for`），並規定 A1／A3 的逾時由它執行；寫明輪詢次數計法與 deadline 比對位置，使 NFR12.3 與 NFR12.19 各有可在毫秒內跑完的測試。 |
| R-04 | Major | New | nfr-design/security-design.md 第三節；nfr-design/performance-design.md 第三節 | 帶入項 14 的「import 圖檢查」不可實作且有繞過。(1) 走訪本模組 `__dict__` 的模組物件只會看到 `import x` 形式；`from cost.advice_orchestrator import f` 綁定的是函式，完全不出現。(2)「`sys.modules` 中由本模組觸發新載入的模組」在同一個 unittest 行程內無法定義，其他測試檔早已載入這些模組，差集恆為空，檢查恆真。(3) 禁止清單缺 `main`（BR51.1 明禁，nfr-requirements review-01 R-08 已指出）。(4) review-01 R-08 另要求的行為判準（AsyncClient 的唯一傳輸為 ASGITransport，其他出站請求使測試失敗）本站沒有承載；本單元合法持有 httpx，直接打 LLM 端點不會被 import 檢查發現。 | 改為兩種機械檢查：用 `ast` 解析本單元所有新模組的 `Import`／`ImportFrom`（含函式內），比對禁止清單（補 `main`）；另開全新子行程只匯入本單元模組，檢查其 `sys.modules` 完整閉包不含禁止清單。再加行為測試：把 `httpx.AsyncClient` 與 `socket` 層出站在測試中攔截，除 ASGITransport 外一律失敗。 |
| R-05 | Minor | New | nfr-design/security-design.md 第四節；nfr-design/logical-components.md 第一節 | 兩處可測性與整合點缺口。(1) `_call_facade` 內直接開 `SessionLocal()`（database.py:38，綁正式 engine），但 backend/tests/helpers.py 的測試 DB 是自建的 StaticPool sqlite；設計未讓 session 工廠可注入，NFR12.2（執行緒比對）與 NFR12.9 的「PUT 之後停用使用者」案例都需要在測試 DB 改 `is_active`，照字面實作的測試看不到該 DB。(2) `HierarchyFacade.list_diagrams_of_system` 目前在 backend/services/hierarchy_facade.py 不存在（grep 零命中），設計把它歸為 U7 擴充，但本站沒有標明這是跨單元的未交付依賴。 | 建構參數加入 `session_factory`（預設 `database.SessionLocal`）。logical-components 開放項增列「依賴 U7 尚未交付的 list_diagrams_of_system，U12 的 code-generation 須在其之後或與其同批」。 |
| R-06 | Minor | New | nfr-design/reliability-design.md 第二、五節 | `_finish_persist` 以 `_spawn` 另成 task 後，外層 `_run` 的「最外層 `except Exception`」不再涵蓋它：facade 拋 `_UserDisabled`、Redis 拋 `SessionBackendUnavailable` 時成為無人取回的 task 例外，違反 NFR12.22 的「事件迴圈無未處理例外」。PUT 本身在 shield 之內也不受牆鐘上限約束，設計沒有說明 httpx 的 timeout 設定。 | 寫明 `_finish_persist` 自帶最外層 try／except（記類別名，嘗試將 sideEffect 改為保守值）；為 PUT 指定 httpx timeout 常數。 |
| R-07 | Minor | New | nfr-design/scalability-design.md 第一節 | Lua 補丁合併的語意不完整。未寫明：補丁值為 JSON null 時是「設為 null」（cjson.null）還是「刪除欄位」，而不變量 (d)(e) 依賴「存在且為 null」；cjson 對空陣列會編回 `{}`（既有 append_message.lua 另有此隱患），WorkItem 若有清單欄位會被悄悄改型；呼叫端的預期 `dispatchStage` 讀自舊值，寫 estimateSetId 時若背景剛推進則 CAS 失敗，沒說明重讀重試的上限（correct 的重算迴圈同理）。模型測試所用的「Lua 的 Python 參考實作」放在哪個模組也未指名。 | 補三句：null 一律設為 cjson.null；清單欄位禁用或以包裝物件儲存；重讀重試次數上限與用盡後的處置；參考實作落在 `session_types`（與 U10 前例一致）。 |
| R-08 | Minor | New | nfr-design/logical-components.md 第四節 OPEN-WO12-9；nfr-design/reliability-design.md 第二節第三列 | 偏離揭露不完整。除了 BR56.7 的 sideEffect 文字，本站還有兩處偏離 functional-design：(1) 第二節第三列讓「失敗（逾時）且 PUT 為 2xx」也寫變更紀錄並改 sideEffect，BR55.7 只涵蓋已停掉，BR56.6 沒有此後處理；(2) 行程重啟時 `dispatchStage=persisting` 的孤兒只被復原掃描標為失敗「可能已存回」，若當時 PUT 已成功則圖被改寫而永遠沒有變更紀錄，這個 ADR-0006 稽核面的殘餘風險未在任何檔揭露。 | OPEN-WO12-9 增列 (1)；reliability-design 增一小節如實記載 (2)，並說明接受理由或指派處置。 |
| R-09 | Minor | New | nfr-design/traceability.json；nfr-design/nfr-design-questions.md | 追溯指向不準。NFR12.19（牆鐘上限）標為 reliability-design.md，但該檔沒有牆鐘章節，實際內容在 performance-design 第二節；NFR12.27、NFR12.29 的目標只是括號備註，logical-components 沒有任何設計內容（例如 CapabilityClient 如何以完整本體判定、如何保證訊息經模型建構）。nfr-design-questions 以「帶入清單 1–4、6–8、10–15」為依據，而本單元檔案中只有 1–6 有明列（reliability-requirements 第三節），7–17 的定義找不到檔案出處，無法核對本站是否漏項。 | 修正 NFR12.19 目標；為 NFR12.27、12.29 在 logical-components 補一小節做法；把 17 項帶入清單列成一張表放進 nfr-design（或指向其出處檔）。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 讀 backend/services/redis_gateway.py `_call`／`eval_script` | 非冪等路徑連線錯誤直接拋 `SessionBackendUnavailable`；`eval_script` 要求明傳 idempotent | 可行（R-02 的前提成立），但需要第三種結果處理 |
| 讀 backend/services/session_scripts/*.lua | 既有兩支腳本使用 cjson decode／encode 與 HSET；沒有 null 補丁或空陣列處理先例 | 補丁合併可行，細節見 R-07 |
| grep `list_diagrams_of_system` 於 backend/ | 零命中 | 屬 U7 未交付依賴（R-05） |
| 讀 backend/tests/helpers.py、database.py | 測試 DB 為自建 StaticPool sqlite；`SessionLocal` 綁正式 engine | 支持 R-05 |
| 讀 backend/services/auth.py get_user_from_token | 停用者 HTTP 路徑回 403；facade 停用判定仍須自寫（mint_principal 不檢查） | security-design 第四節方向正確 |
| 比對 NFR12.1–12.29 與 traceability.json | 29 項皆有列，無缺漏；部分目標不準 | R-09 |
| 測試 | 未執行 | 本站為設計文件 |

### Summary

Critical 0；Major 4（R-01 至 R-04）；Minor 5（R-05 至 R-09）。本站對帶入項 1（shield）、4（補丁合併 Lua）、2（_advance 寫入成功者才啟動）、10（自寫停用判定）方向正確且可實作，但 client 生命週期會讓 shield 失效（R-01）、非冪等寫入的未知結果沒有處置（R-02）、牆鐘逾時無法注入（R-03）、import 檢查恆真（R-04），這四項各自讓一個被宣稱已解的帶入項實際上仍會在實作時出錯。
