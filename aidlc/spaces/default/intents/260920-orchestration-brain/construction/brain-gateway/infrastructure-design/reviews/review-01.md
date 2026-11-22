## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-13T02:00:01Z
**Iteration:** 1

### Findings

| ID | Severity | Status | Location | Finding | Required action |
|---|---|---|---|---|---|
| R-01 | Major | New | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-gateway/infrastructure-design/infrastructure-specification.md 第二節 OpenRouter 列、5.3、第八節、第十一節處置表、第十二節；cicd-pipeline.md 開頭、第一節部署列、第五節 OPENROUTER_API_KEY 列；traceability.json | IG1=A、IG2=A 已於 2026-10-13T01:56:38Z 作答，但四份產出的 mtime 為 08:56 至 08:58（本機時間，早於作答 UTC 01:56 約 1 小時），內文仍寫「待使用者裁決」「本規格不改 render-env.sh、deploy.yml、deploy/.env.example」「擇一，屬合併策略，非本站決定」。grep IG2 於 spec、cicd、monitoring、traceability.json 命中 0 次。code-generation 讀這份規格不會知道要改 deploy.yml:71-91、render-env.sh:21 註解、deploy/.env.example:51、DEPLOY.md:24。另外 IG1=A 動到 render-env.sh 與 .env.example，依 project.md Mandated 必須同步 LOCAL-DEV.md，而 6.3 的六處清單未含此項。 | 把 IG1=A 寫成確定設計：列出 deploy.yml 必要檢查新增一項（不進 render-env.sh 拒絕清單）、四處文件改動、LOCAL-DEV.md 同步；把 IG2=A 寫成確定的同批約束並指定由哪個單元與 Bolt 承擔 DEMO 移除；刪除所有「待裁決」措辭並更新 traceability 與第十一節處置表。 |
| R-02 | Major | New | infrastructure-specification.md 5.2 DEMO 前端列「無 /brain 的 e2e」、5.2 DEMO 後端列、5.3；問題檔 IG2 | DEMO 觸點盤點不完整，且「無 /brain 的 e2e」為假。git grep 實證：frontend/tests/e2e/member-pages.spec.ts 有 8 處、memory-page.spec.ts 有 2 處以 page.goto('/brain') 作為免 CapabilityRoute 的落地頁（member-pages.spec.ts:244-252 的註解明說刻意選它隔離變數）；移除 BrainPage、App.tsx 的 /brain 路由與 Sidebar 連結後，ui-regression（真閘門）會紅。backend/tests/test_intent_routing_structure.py:62、:315-345 以 DEMO_GATEWAY_PATH 讀 brain_router.py 並在找不到 _CAPABILITIES 時斷言失敗，刪檔即紅，規格未列。另 eslint.config.js:32 與 intent_routing_types.py:48 的註解仍引用 DEMO。行號亦有誤：Sidebar.tsx 的 DEMO 區塊實為 211-217（212-219 越界到 U15 區塊）。IG2=A 因此不是單純刪三個檔：中間 Bolt 合併後 /brain 不存在，與這些 e2e 直接衝突。 | 補齊刪除清單與行號（含 test_intent_routing_structure.py 改鎖正式閘道或移除、兩支 e2e 改用其他落地頁、兩處註解）；更正「無 /brain e2e」；寫明 IG2=A 下中間 Bolt 的 /brain 落地頁替代方案，或改以「關掉 bearer 回送」（IG2 選項括號所述）作最小處置並比較兩者。 |
| R-03 | Major | New | infrastructure-specification.md 第八節；cicd-pipeline.md 第五節 OPENROUTER_API_KEY 列；.github/workflows/deploy.yml:71-91、:542-551 | IG1=A 缺上線順序。必要檢查在 deploy job 失敗時，rollback job 條件為 needs.deploy.result==failure 且 PR 已合併，會自動還原 last-good 並對整個合併開 revert PR（本分支領先 origin/ut 83 個 commit）。若合併時 repo 的 OPENROUTER_API_KEY secret 尚未設定或為空，新增的檢查會讓整批 intent 被自動 revert；deploy.yml:100-108 註解已記載同型風險。規格未要求合併前以 gh api 查證 secret 存在，也未說明檢查失敗與 rollback 觸發的關係。檢查本身落點正確：rollback 只經 render-env.sh（deploy.yml:617），不加進其拒絕清單是對的。 | 在規格寫入合併前置條件（以 gh api repos/.../actions/secrets 查證名稱存在，並依 project.md 同步查 variables 確認未誤存為明文）；寫明檢查失敗會觸發 rollback 與 revert PR 的後果，並決定檢查要放在合併前人工關卡還是接受此行為。 |
| R-04 | Minor | New | infrastructure-specification.md 第二節 backend 列、4.4 前置 2；traceability.json NFR13.39 | websockets 來源引用錯誤。規格稱 websockets 與 uvicorn[standard] 隨 fastapi[standard] 安裝，但 backend/requirements.txt:8-10 為 fastapi==0.111.0 與裸 uvicorn，不含 standard 也不含 websockets；本機環境中 websockets 僅被 langgraph-sdk、langsmith 要求。入口頁、探測腳本與預設 20 秒 ping 的假設都落在一個未釘版的間接依賴上，並非「不新增套件」的既有保證。 | 更正依賴來源；在 4.4 加一步 docker exec 內 python -c "import websockets" 的前置確認，並在 build-and-test 記錄 uvicorn 實際選用的 WebSocket 實作。 |
| R-05 | Minor | New | infrastructure-specification.md 4.5 L2 失敗列 | 回退建議在 location /api/ 加 proxy_set_header Sec-WebSocket-Protocol $http_sec_websocket_protocol，但 nginx 預設已透傳該請求標頭（4.2 自己的靜態判定），該指令幾乎等同空操作；回應方向亦無 proxy_hide_header。L2 失敗時真因必在別處，此修法會讓人誤以為已修復。 | 改為先診斷（nginx error_log debug、比對 L1 與 L2 的請求標頭）再決定修法，並移除或降級此建議。 |
| R-06 | Minor | New | infrastructure-specification.md 4.4 前置與 curl 補充檢查 | 實測操作的 token 衛生不足：未要求 export（docker exec -e BRAIN_PROBE_TOKEN 只傳已匯出的變數）、未說明如何不留 shell history 取得 token（可用 read -rs）、host 端 curl 的 -H 內插使 token 出現在 ps 的 argv（render-env.sh 檔頭自己點名此風險）；以 -D - 印出整段標頭作驗證，若有缺陷回送 token 會直接顯示在終端。 | 補 read -rs 加 export 的取得方式；curl 改用 -H @檔案或 --config 由 stdin 讀入；輸出先經 grep 過濾再顯示。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| validate_env_contract.py:87-89 與 :242-262 讀檔 | PY_ENV_READ 只匹配 os.environ.get 與 os.getenv，不匹配 os.environ["X"] | 規格的空轉揭露屬實 |
| LOCAL-DEV.md 行號 | :23、:24-25、:17-20、:26、:79、:593 內容與規格逐項相符 | 六處行號正確 |
| frontend/nginx.conf 與 frontend/Dockerfile:21-23 | location /api/ 僅 proxy_set_header，無 hide；upgrade map 存在 | nginx 一跳靜態透傳判定成立 |
| backend/Dockerfile:30 與兩份 compose 的 env_file、WORKERS 搜尋 | 無 --workers、無 env_file、無 WEB_CONCURRENCY | 單行程守門的部署面判定正確 |
| deploy.yml 與 ci.yml 引用行號（71-91、542、617、264-272、281-289、299-300、303-306） | 皆相符 | 引用定位無誤 |
| git rev-list 與 merge-base | 領先 83、落後 0；DEMO 的 f9c5bda 不在 origin/ut | 5.1 事實屬實 |
| traceability.json | 44 條與上游 id 集合相同，無缺漏重複；N/A 19 條判定合理 | 通過；但 IG1、IG2 未反映（見 R-01） |
| ADR-0006 四面向表（第十節） | 四面向皆有判定與依據，nginx access log 與 Cloudflare 日誌已標推論或未查證 | 通過 |

### Summary

共 6 項：Critical 0、Major 3、Minor 3。主要問題是產出早於 IG1／IG2 作答而未更新，且 IG2=A 的 DEMO 移除範圍漏列兩支 e2e 與一支後端結構測試（「無 /brain e2e」為假），IG1=A 又缺少防止合併即被自動 revert 的前置條件；逐跳透傳、LOCAL-DEV.md 六處、env contract 空轉揭露與單行程守門的判定皆屬實。
