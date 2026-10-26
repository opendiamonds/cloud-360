## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站五類 NFR（NFR21.x 共 41 條）大致二元可判，ADR-0006 四面向逐格落點與上游 requirements.md:617-620 方向一致，PBT 落於 NFR21.39。補審確認前次 review-01 的兩項 Major 仍留在凍結產出裡（NFR21.21 誤用 uvicorn 連線數上限、NFR21.30 第二退路下不可構造）；已落地的程式實際上走了不同且較正確的做法，因此是「設計文字落後於程式」而非程式有缺陷。Critical 0、Major 2、Minor 5，依規則判 READY，但兩項 Major 的文字應在關卡上交給人裁決是否以勘誤處置。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-requirements/scalability-requirements.md > NFR21.21 與第二節算式 | 前次 review-01 R-01 已提，產出凍結未改。NFR21.21 規定以 uvicorn 的 limit_concurrency 實現「同時處理中請求上限」並由 uvicorn 回 503，且判準要求「放行後第四個請求成功」。uvicorn 該參數計的是已開啟連線（含閒置 keep-alive），判準構造不出來，且 /healthz 會與工具呼叫共用額度。已落地程式與設計相反：backend/mcp_bridge/guards.py 的 ConcurrencyGate（約 :175-196）自己計進行中請求，/healthz 由 PathRouter 置於全部閘門之外（guards.py:5），server.py 未傳 limit_concurrency。以程式為正確的一邊，設計文字為過期。 | 以勘誤或 corrections 檔改寫 NFR21.21：機制為應用層 ConcurrencyGate、/healthz 不受限，判準改為對應 guards.py 的測試；並註明 uvicorn limit_concurrency 不採用的理由。 | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-requirements/reliability-requirements.md > NFR21.30；tech-stack-decisions.md > NFR21.38、NFR21.41 | 前次 review-01 R-02 已提，產出凍結未改。第二退路（mcp 裝在獨立 virtualenv）的前提是 mcp 與 fastapi==0.111.0 的 Starlette 範圍衝突，此時主直譯器沒有 mcp、獨立 venv 沒有 backend app，而驗證拓樸需同一測試同時起 backend app 與 mcp client，NFR21.30 的判準不可構造。實況：backend/requirements.txt:71 已為 mcp==2.3.0，且註解（:67-70）說明 Python 小於 3.14 時與 fastapi 0.111.0 相容，即採第一順位，第二退路未啟用。 | 以勘誤標明已選第一順位、NFR21.30 的第二退路分支與 NFR21.41 的 Dockerfile 分支作廢；或補一句 Python 大於等於 3.14 時改走升版另開題，不得走獨立 venv。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-requirements/reliability-requirements.md > 五 優雅關閉（約 :47） | 前次 review-01 R-09 已提。文字寫 compose stop_grace_period 預設 10 秒「不另設」，與單次呼叫上限 10 秒貼邊。已落地 deploy/docker-compose.deploy.yml:430 為 15s，並有關係式註解（limits.py:9-15，13 加 1 小於 15）。程式正確，設計文字過期。同段仍缺「頻率無上限」的後果揭露（持有效 token 者在並發內可無限速率寫入）。 | 勘誤改為 stop_grace_period 15s 及其關係式；並在頻率關閉理由補上寫入速率無上限的後果，供關卡呈現。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-requirements/security-requirements.md > NFR21.16 ③ 與第六節 Network exposure | 前次 review-01 R-04 已提。允許清單「恰為」固定 :8080 三項，但驗證拓樸用隨機埠；標題「網路暴露面零新增」與上游 requirements.md:619「第二個新增進程邊界」措辭相反。internal 網段為一般 bridge，同網段容器皆可連 /mcp，已由 [G2]=A 接受。 | 改為 allowed_hosts 隨 --port 衍生；標題改為「新增一處，僅 internal 網段、無 ports:」，並明寫殘留風險。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-requirements/scalability-requirements.md > 第一節、第三節算式 | 前次 review-01 R-05 已提。最壞位元組數以每字元 6 位元組估，非 BMP 字元在 JSON 跳脫為 12 位元組，餘裕約 2.7 倍而非「5 倍以上」；結論 65536 仍夠用。 | 更正算式與倍數，或註明為保守估計。 | New |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-requirements/observability-requirements.md > NFR21.34、NFR21.36 | 前次 review-01 R-06 已提。tool 欄未規定正規化，呼叫端可控的工具名可注入換行；413／503 發生在 app 之前且存取 log 關閉。程式側 observability.py 已有 log_request_rejected（guards.py:187 呼叫），部分已緩解，但 NFR 文字未要求。 | NFR21.34 增列 tool 欄僅取已宣告工具名、其餘記 unknown；補 413／503 至少一行 WARNING 的需求。 | New |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/mcp-bridge/nfr-requirements/traceability.json > coverage 的 NFR4 列；performance-requirements.md > NFR21.3 | 前次 review-01 R-07、R-10 已提。NFR4（session 與工作狀態放 Redis）對無狀態 bridge 標 OK 與 NFR2 標 N/A 不一致；NFR21.3 的 50 ms 預算未達標時「由關卡裁決」不是二元判準，且 ASGITransport 與真實 uvicorn 往返的量測不對稱。 | NFR4 改 N/A 並同步計數（OK 42、N/A 10）；NFR21.3 改為「量測並記錄，超過時須留裁決紀錄」並說明偏差方向。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 nfr-requirements 全部產出與 reviews/review-01.md | 前次兩項 Major、八項 Minor 的文字皆仍在凍結產出中 | 前次發現未被產出修訂處置，僅由 carried-review-items.md 帶進 code-generation |
| 抽查 backend/mcp_bridge/guards.py、server.py、limits.py、cli.py | ConcurrencyGate 自計進行中請求、/healthz 在閘門外、未用 limit_concurrency | 程式已處置 R-01，設計文字落後 |
| 抽查 backend/requirements.txt:67-71、deploy/docker-compose.deploy.yml:426-430 | mcp==2.3.0 進主 requirements；stop_grace_period 15s | 程式已處置 R-02、R-03，設計文字落後 |
| 未執行測試、lint 或建置 | 依 brief 禁止寫檔 | 未獨立驗證 ConcurrencyGate 的測試覆蓋 |
