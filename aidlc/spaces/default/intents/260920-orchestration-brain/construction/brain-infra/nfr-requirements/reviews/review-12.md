## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

三份產出（security-requirements.md、tech-stack-decisions.md、traceability.json）自我審查相當紮實：ADR-0006 四面向逐項有判定、NFR8 的閘門作用域有誠實記載。但對照已落地的 deploy compose 與 deploy.yml，仍有三項實質缺口。(1) 上游 unit-of-work 明文把「是否為 mcp-bridge 新增第七個 compose 服務」交給 brain-infra，而三份產出對 mcp 的命中為 0（前次 review-11 R-55 已提，凍結產出中仍未處置）。(2) Ollama 模型快取的「誰寫」寫錯：設計稱 ollama 容器首次拉模型時寫入，實際官方 entrypoint 不拉模型，靠 deploy.yml 的部署後 `ollama pull` 步驟，該步驟與其對外連線需求不在設計的九處同步清單內。(3) 升版用的 pg_dumpall 備份檔與舊 volume 沒有存放、保護與清除的承載者，ADR-0006 的 encryption 與 IAM 面向在此落空。其餘為次要的版本策略與用語不一致。Major 共 3 項，依規則判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/brain-infra/nfr-requirements/security-requirements.md 全檔、tech-stack-decisions.md §三「服務數的變化」與 §四「九處部署資產同步」、traceability.json（前次 review-11 R-55 已提） | inception/units-generation/unit-of-work.md:545 逐字寫「U1 brain-infra 是否需要為它新增第七個 compose 服務，屬 infrastructure-design 的範圍」，且 :309 將 U21 mcp-bridge 定為 standalone 獨立進程、與 backend 同主機。三份產出對 mcp 的命中數為 0（grep -c 實測），服務數表只寫 4 到 6 或 5。已落地的 deploy/docker-compose.deploy.yml:4 與 :431 已有 mcp-bridge 與 internal: true 的 mcp 網路。NFR8 是本單元的核心職責，上游點名的開放問題在本站被完全略過；infrastructure-design 雖有處置，本站的服務數、網路暴露（NFR8.7／NFR8.8 是否涵蓋 mcp-bridge）與九處清單仍是殘缺的。落地的一側是對的，設計一側過時 | 以 corrections 檔或本站補充段落，明列 mcp-bridge 為第三個新增服務，並補上它的網路暴露判準（無 ports、僅限 mcp 網路）、日誌承載與 compose 同步點；或明確記載「此項由 infrastructure-design 承接」並指名落點與驗證方式 | New |
| R-02 | Major | construction/brain-infra/nfr-requirements/security-requirements.md `NFR4.3` Ollama 模型快取列 ＋ tech-stack-decisions.md §2.2「volume」列 ＋ §四 row 6 | 設計寫模型快取 volume 的「誰寫」是「ollama 容器（首次拉模型時）」。實際上官方 ollama/ollama 的 entrypoint 是 ollama serve 且不拉任何模型（deploy/docker-compose.deploy.yml:326-331 的註解逐字說明），模型靠 .github/workflows/deploy.yml:146-285 的部署後 ollama pull 步驟寫入。契約端點三問中「誰寫」被寫成錯的承載者。連帶缺口：(a) 該 workflow 步驟不在九處同步清單（row 6 只列 env 對照表）；(b) 拉模型需要對外連線，而設計反覆寫「僅限 compose 內部網路」，未區分「不對外發布 port」與「禁止出站」，若實作者據此設 internal: true 會使拉取失敗（compose 檔 :447-451 的註解正是為防這件事）；(c) 對外取得約 1.2GB 模型的來源與完整性（出站目的地、是否驗證）是 ADR-0006 network exposure 的出站面，判定表未提；(d) 健康檢查通過不代表模型存在，設計沒有「模型缺失時大聲失敗」的判準。已落地的程式是對的，設計是錯的 | 更正 NFR4.3 的「誰寫」為部署後 pull 步驟；把該步驟列入同步清單；在 NFR8.8 區分入站（無 ports）與出站（允許，僅限模型來源）；補上「模型缺失即部署失敗」的可測判準 | New |
| R-03 | Major | construction/brain-infra/nfr-requirements/security-requirements.md `NFR6.3(c)` 步驟 3 與步驟 7、`NFR4.3` 的 volume 清單、§一 ADR-0006 Encryption 與 IAM 列 | 升版程序要求 pg_dumpall 完整備份，內容含 users 密碼雜湊與全部資料，並要求備份與舊 volume 並存至「約定期限」。三份產出對備份檔的存放位置、檔案權限、靜態加密、傳輸路徑（「別處還原驗證」）與到期後由誰銷毀皆未規定（對 備份 與 權限、加密 的交叉 grep 無命中）。NFR4.3 的「誰清」表只涵蓋 Redis AOF 與 Ollama 兩個 volume，未涵蓋舊 volume（cloud360_cloud360_db，compose 檔 :50-51 提及）與備份檔；保留期限只說「寫進 DEPLOY.md」，沒有人負責到期刪除。ADR-0006 的 encryption 與 IAM 面向對這個本單元風險最高的資料副本沒有落點，且 project.md 要求這兩面向在 stage 產出中明列 | 在 NFR6.3 增補備份檔的存放位置、權限（僅部署者可讀）、加密或隨用即刪、驗證用「別處」的範圍；NFR4.3 補列舊 volume 與備份檔的誰寫、誰讀、誰清與期限上界；ADR-0006 判定表兩列引用之 | New |
| R-04 | Minor | construction/brain-infra/nfr-requirements/security-requirements.md `NFR4.1(b)`、(c) | 設計只要求「不得以 default 使用者連線」，未規定 default 使用者本身的處置，也未限制憑證在承載者上的暴露方式。已落地的 deploy/docker-compose.deploy.yml:255-290 以 command 參數承載：default 使用者為 nopass 並保留 +@connection，REDIS_USER 的密碼以 >${REDIS_PASSWORD} 寫在容器啟動參數，可由 docker inspect 或行程列表讀出。同一內部網路上任何容器可免密碼取得 default 的連線類指令。這是設計把承載者留給下游卻沒有給憑證處理約束的後果 | 補一條約束：default 使用者除健康檢查所需外須停用或最小化；憑證不得出現在可被 docker inspect 讀取的參數中，或明列接受此暴露的理由 | New |
| R-05 | Minor | construction/brain-infra/nfr-requirements/tech-stack-decisions.md §2.2「版本策略」列；已落地 deploy/docker-compose.deploy.yml:323 | 設計寫 Ollama「同 2.1：釘選明確版本，不用 latest」，已落地為 ollama/ollama:latest（compose 檔 :315-322 註解承認並標為 OPEN-10）。設計正確、落地偏離，且釘選的前置檢查（bge-m3 相容性）未在設計中指名由誰做 | 在設計側指名釘選的負責站與判準，並在關卡上確認 OPEN-10 的處置期限 | New |
| R-06 | Minor | construction/brain-infra/nfr-requirements/traceability.json NFR6 target ＋ tech-stack-decisions.md §2.3「範圍」 ＋ security-requirements.md `NFR6.1` | 同一事實出現三種數量：traceability 寫「其 service container 須與本單元的三處一致」，tech-stack 寫「image 四處必須全部一致」（含 N-2 job 自己），NFR6.1 寫「落點 1-4 image 值相同」，另有落點 5 volume 宣告。下游以計數核對時會判定不一致 | 統一為「本單元交付的三處 image（deploy、test、repo 根）加 N-2 job 共四處，另加 volume 宣告一處」並全檔同步 | New |
| R-07 | Minor | construction/brain-infra/nfr-requirements/ 三份產出的現況基準（前次 review-11 R-54 已提，該輪判 Critical） | 「現值 postgres:16-alpine」「服務數 4」「Redis 零基礎設施用途」及大量 file:line 引用描述的是落地前基準（codekb 基準 dc4b687），現已全部失真：compose 現為 pgvector/pgvector:pg18（deploy 檔 :40、test 檔 :51、repo 根 :17），deploy 檔已有 redis、ollama、mcp-bridge。就階段性文件而言記載落地前基準本身合理，且產出自己標明了基準，故我判為 Minor；但凍結產出沒有 as-built 註記，讀者無法分辨哪些「現值」仍成立 | 於產出頂部加一段基準時點與「已落地」對照說明，或由 corrections 檔取代；不需重寫各 NFR | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep -c mcp 於三份產出 | 0／0／0 | 證實 R-01：上游點名的開放問題未被本站提及 |
| grep ollama pull 於 deploy.yml 與 deploy compose | deploy.yml:146、257-285 有部署後 pull 步驟；compose 註解說明 entrypoint 不拉模型 | 證實 R-02：模型快取的寫入者與設計敘述不符 |
| grep 備份 與 權限、加密 的交叉搜尋於 security-requirements.md | 無命中 | 證實 R-03：備份檔無保護與清除承載者 |
| 已落地檔案抽查（render-env.sh:40-75、deploy compose :40、:184-300、:312-345、:431-480、test compose :51、:140、repo 根 compose :17、schema_rbac.sql:63、database.py:87-90） | pg18 映像四處一致；CREATE EXTENSION 兩處承載且 _ensure_vector_extension 在 create_all 之前；REDIS_PASSWORD 為唯一進環境的憑證、REDIS_USER 為 render-env 字面值 | 與設計的 NFR6.1、NFR6.2、NFR8.1、NFR4.1 主張相符；偏離僅見 R-02、R-04、R-05 |
| sensor／validate_env_contract.py | 未執行（本補審禁止會寫快取的指令） | 設計對該 validator 作用域的說法，已於 review-11 以開檔核對為一致，本輪未重複 |
