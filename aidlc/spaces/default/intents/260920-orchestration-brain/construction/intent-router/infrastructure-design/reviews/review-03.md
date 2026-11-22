## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U11 intent-router 的 infrastructure-design 產出整體自洽：「不新增基礎設施」的主張經實測成立（五個 BRAIN_ROUTER_* 變數已在 render-env.sh:140-144、deploy/.env.example:159-163、docker-compose.deploy.yml:143-147、backend/.env.example 四處同步，且 docker-compose.test.yml:121-125 也有）；前次 review-01、review-02 的三項發現（traceability 的 Deferred 狀態、I-1 的 CONDITIONAL-skip 註記、job 並行措辭）在凍結產出中皆已處置。剩餘問題有兩項 Major：其一，產出把 NFR1／NFR3.60 的唯一量測路徑押在一條 routing-accuracy workflow_dispatch job 上，但該 job 在 repo 內不存在、沒有標註集與量測 harness 的擁有者，且未說明 workflow_dispatch 須先存在於預設分支；其二，monitoring-design 的 prompt_guard 告警以「單一 principal」為條件，而白名單型別 RoutingObservation 沒有任何可識別使用者的欄位，該告警在設計上無法計算。另有三項 Minor。零 Critical、2 Major，判 READY，但關卡上建議人工留意 R-01、R-02。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | cicd-pipeline.md 第二節（routing-accuracy job）；traceability.json 的 NFR3.60 列（status OK，note 寫「落 workflow_dispatch 的 routing-accuracy job」） | 實測 grep routing-accuracy 於 .github、backend/tests、scripts 全為零命中，該 job 並不存在；產出只有一段 11 行的 YAML 片段。NFR1（準確率）、NFR3.60（P50）、NFR3.73（槽位分佈）、OQ-10 的唯一量測路徑因此沒有落地物，也沒有人被指名擁有「標註集檔案格式」與「讀標註集、呼叫真實 classify、輸出準確率與 P50／P95 的 harness」。另外 workflow_dispatch 只有在 workflow 檔存在於預設分支時才能被手動觸發，而本 repo 預設分支是 main、整合主幹是 ut（org.md：main 只接收 ut 的合併），產出完全沒提這個前置，導致在 ut 上做 build-and-test 時可能根本無法觸發。前次 review-02 已核實「不跑這個 job，build-and-test 會自己紅燈」，這代表該 job 缺席的後果是流程停擺，不是小缺口。traceability 把 NFR3.60 標 OK 與此矛盾，應為 Deferred 或 GAP 並指名承接站。 | 把 NFR3.60 的 traceability 狀態改為 Deferred（或 GAP），target 指名具體承接站（code-generation 或 build-and-test）；在 cicd-pipeline.md 補三句：(1) job 與 harness 由哪一站交付；(2) 標註集的格式與存放位置的擁有者；(3) workflow_dispatch 須先合併到預設分支才可觸發，並說明在 ut 上如何達成（例如先把 workflow 檔合進 main，或以 push 到 ut 的路徑條件觸發作替代）。 | New |
| R-02 | Major | monitoring-design.md 第一節「prompt_guard 命中數」列與第二節「prompt_guard 命中突增」列；backend/services/intent_routing_types.py 第 222-247 行 RoutingObservation | 告警條件寫「單一 principal 短時間多次」，但 RoutingObservation 的欄位只有 turn_id、slot_count、capability_ranks、scores_available、can_single_out、elapsed_ms、error_kind、memory_degraded，沒有任何使用者或 principal 欄位，而日誌白名單（SEC-3／SEC-5）又以型別禁止新增。以此日誌無法判斷「同一個人」，只能數總命中數。產出也沒有說明要靠 turn_id 去 join 閘道端 U13 的日誌取得使用者身分，更沒有指名那份日誌是否有該欄位。這同時是 ADR-0006 稽核面向的缺口：安全事件（平台自我竄改嘗試）不可歸屬到使用者，事後無法追查。連帶地，「記憶持續降級」列的「連續 N 輪」中 N 也沒有數值，也沒有說明連續是以全域日誌順序還是以使用者為單位。 | 二選一並寫明：(a) 把告警條件改成實際可算的「總命中數在窗口內超過門檻」，並移除 principal 字樣；(b) 明確宣告以 turn_id join U13 閘道日誌取得使用者，指名 U13 日誌中對應欄位，並承認此 join 屬跨單元依賴，列為交接事項。同時補上 N 的數值與「連續」的計算單位。 | New |
| R-03 | Minor | cicd-pipeline.md 第三節「這個失敗模式仍有一道既有的網」 | 文中寫該網是 deploy.yml:130 的 curl 127.0.0.1:8090/ 健康檢查。實際該步驟在 deploy.yml:131-145（curl 在第 135 行），且它只打 frontend 的靜態首頁，而 docker-compose.deploy.yml:360 的 frontend 只有 depends_on backend（預設 service_started），backend crash-loop 時這一步會通過。真正攔住的是 deploy.yml:313 起的「Probe the data plane through /api」（期望 /api/auth/login 回 401），它經 nginx 到 backend，backend 掛掉會得到 502 而失敗。結論（部署失敗並自動回滾，非靜默壞掉）成立，但引用的機制與行號是錯的，下一個依此推論「crash-loop 會被首頁檢查擋下」的人會被誤導。 | 把引用改為 deploy.yml:313 起的 data-plane probe，並移除對首頁 curl 的依賴說法；rollback 側同理指向 :695 起的合併探測。 | New |
| R-04 | Minor | infrastructure-specification.md 第一節 Networking 出站列、第二節 OpenRouter 列；全部三份產出 | ADR-0006 的四個面向沒有逐項判定表。IAM（本單元零新增，唯讀 Redis 與 PostgreSQL 的權限邊界由上游承載）與稽核（見 R-02）有間接落點，但 encryption 在三份產出中零命中：對 OpenRouter 的新增邏輯呼叫走 HTTPS、API key 的承載（secret 經 render-env.sh 注入、不進日誌）都只靠上游 security-design 默示。project.md 要求此類 hard constraint 以逐項判定表呈現，不得僅以「已有上游」帶過。 | 在 infrastructure-specification.md 補一張四面向小表，每格附判定與理由（可引用 security-design 的條款編號），特別寫明 encryption in transit 與金鑰處置。 | New |
| R-05 | Minor | monitoring-design.md 第三節 SLI 表「路由層首段延遲」列；第一節「classify 耗時 P50」列 | 表中「線上滾動」量測 P50，但唯一的資料來源是 intent_routing.py:269-296 的單行 INFO 日誌，且產出自述「無 dashboard、無告警通道、人工查詢日誌」，也沒有給出從日誌算分位數的查詢方式，同時沿用的容器日誌輪替上限是 50m x 5（docker-compose.deploy.yml 的 json_file_bounded），高流量時保留窗口短。因此「線上滾動 P50」在現況下只是可手算，不是可持續觀測的 SLI。產出已誠實聲明無通道，故只列 Minor。 | 在 SLI 表加註「現況為人工以日誌計算」與保留窗口限制，或把線上量測欄改為 observability-setup 承接前的「未提供」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep BRAIN_ROUTER_* 於 deploy／backend/.env.example／backend/services | 五變數在 render-env.sh:140-144、deploy/.env.example:159-163、docker-compose.deploy.yml:143-147、docker-compose.test.yml:121-125、backend/.env.example 皆存在 | 產出的五變數三處同步主張成立；required-no-default 僅門檻一個，與 intent_routing_config.py 檔頭一致 |
| grep routing-accuracy／workflow_dispatch 於 .github、backend/tests、scripts | routing-accuracy 零命中；既有 workflow_dispatch 僅 aidlc-sync-pull 與 agentics-maintenance | 確認 R-01：量測 job 不存在 |
| 讀 deploy.yml:131-145 與 :313-350，docker-compose.deploy.yml:353-365 | 首頁 curl 只打 frontend 靜態頁；data-plane probe 才經 /api/auth/login 到 backend | 確認 R-03 |
| 讀 intent_routing_types.py:222-247 | RoutingObservation 無使用者欄位 | 確認 R-02 |
| traceability.json 檢視（開頭至 NFR3.63） | NFR1.60 已為 Deferred；NFR3.60 為 OK | 前次 R-01 已處置；NFR3.60 狀態與 R-01 矛盾 |
| 前次 review-01／review-02 發現複核 | 三項（Deferred 狀態、I-1 的 CONDITIONAL-skip 註記、job 並行措辭）皆已在凍結產出中修正 | 無需重列 |
