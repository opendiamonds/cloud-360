## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U6 embedding-port 的 nfr-requirements 產出大致自洽：NFR 逐項承接或明確標 N/A，ADR-0006 四面向有逐格判定且與 K-06 一致，殘餘風險 RR-1 至 RR-4 具名並有失效條件，前次 review-01 的三項 Minor 皆已處置。但有兩項 Major：其一，改動面宣稱「不改任一 compose 檔」，而 `deploy/docker-compose.deploy.yml` 的 backend 用顯式 `environment:` 清單傳遞變數，新 timeout 變數若不加一行就到不了容器，實作已加（第 124 行）而設計未記；其二，NFR3.2 的「10 秒上界」在 httpx 的語意下是每階段各 10 秒而非整體期限，與 RR-4 的論證（timeout 是掛住保護）前提不完全吻合。其餘為 Minor。Major 兩項未超過兩項門檻，判 READY，供關卡人員權衡。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/embedding-port/nfr-requirements/tech-stack-decisions.md` 第三節「本單元不改：任一 compose 檔」與第二節「三處同步」；`security-requirements.md` `NFR8.1` | 設計寫明新增 `EMBEDDING_TIMEOUT_SEC` 只需 `render-env.sh`、`deploy/.env.example`、`backend/.env.example` 三處加一行，並宣稱不改任一 compose 檔。但 `deploy/docker-compose.deploy.yml` 的 backend 服務以顯式 `environment:` 逐一列出 embedding 變數（第 120 至 123 行為既有四個），新變數若不在該清單加一行，`.env` 寫了也進不了容器，timeout 會無聲退回預設 10，與 project.md 所述「新增 compose 消費的變數」的無聲降級失敗模式同形。實作已在該檔第 124 行加入 `EMBEDDING_TIMEOUT_SEC: ${EMBEDDING_TIMEOUT_SEC}`，可見設計的改動面清單與已落地程式矛盾，且正確的一邊是程式。 | 修正改動面表與 `NFR8.1`：把 `deploy/docker-compose.deploy.yml` 列為第 7 項改動（新增一行 environment 傳遞），並更新「本單元不改」清單；同時說明 `docker-compose.test.yml` 不傳遞時沿用預設 10 的取捨。 | New |
| R-02 | Major | `security-requirements.md` `NFR3.2` 與第二節末段（10 秒 timeout 的語意）；實作 `backend/services/embedding_port.py` 第 610 行 `httpx.Client(timeout=EMBEDDING_TIMEOUT_SEC)` | `NFR3.2` 與 `RR-4` 把 10 秒說成呼叫的「上界」，並據此推論「timeout 保護的是服務掛掉時不要無限期掛住」。但 httpx 傳單一浮點數時是 connect、read、write、pool 四個階段各自 10 秒，不是整體期限；最壞情況可達約 30 秒以上，且 read timeout 在持續收到位元組時會重置。對單一非串流的 `/api/embed` 請求影響有限，但設計沒有區分「每階段」與「整體」，而 `NFR3` 的首字預算是 2 秒，RR-4 的量化比較（「5 倍」）因此低估。另 `fastembed` 為行程內同步推論，完全不受此 timeout 約束，`NFR3.2` 未說明。 | 在 `NFR3.2` 明寫語意（每階段或整體）並據實修正 RR-4 的倍數；若要整體期限需指定機制（例如 `httpx.Timeout` 分階段設定加呼叫方期限）。同時註明 `fastembed` 路徑無逾時保護及其可接受理由。 | New |
| R-03 | Minor | `security-requirements.md` 第二節；`functional-design/functional-spec.md` | `embed` 是同步呼叫（實作為同步 `httpx.Client`），而它落在首字回應路徑上（`NFR3.1`）。全部產出沒有一處說明呼叫端（`U8`、`U11`）應以何種方式呼叫：若在 asyncio 事件迴圈中直接呼叫，一次 10 秒的逾時或 fastembed 的推論會阻塞同一行程內所有 WebSocket session。`RR-4` 只交接了延遲預算，未交接這個併發面。 | 在 `RR-4` 或 `U8-3` 交接項補一句：呼叫端須在執行緒或 executor 中呼叫同步 Port，並由 `U8`／`U11` 的 nfr-requirements 承接。 | New |
| R-04 | Minor | `tech-stack-decisions.md` 第一節表格（`backend/.env.example:119`、`deploy/.env.example:116`、`docker-compose.test.yml:18`）；`security-requirements.md` `NFR8.2`（`deploy/.env.example:96`）與 `NFR9.1`（`:115`） | 逐字核對現況行號：`EMBEDDING_PROVIDER=fulltext` 在 `backend/.env.example:120`；`deploy/.env.example` 的 `EMBEDDING_PROVIDER=ollama` 在第 120 行，「缺值會讓 backend 拒絕啟動」在第 100 行，「對外部 API 花費貢獻為零」在第 119 行；`docker-compose.test.yml` 的預設 `stub` 在第 102 行（第 18 行僅為註解）。事實全部成立，定位多數已偏移。部分偏移可能源於本單元後續新增行，但產出已凍結，下游照行號讀會讀到別處。 | 以現況行號更正，或改為引用變數名稱而非行號。 | New |
| R-05 | Minor | `security-requirements.md` `NFR3.2`；實作 `embedding_port.py` 第 241 至 277 行 | `NFR3.2` 只規定預設與可覆寫，未規定壞值（非數字、非正數）的行為。實作選擇記 WARN 並退回預設，這與同一單元 `BR1.6` 的「設定層錯誤一律終止啟動」及 ADR-008「不得靜默降級」的立場不一致，且該判斷只存在於程式而不在需求。此外該常數在 import 時計算，早於 logging 設定，WARN 可能不可見。 | 在 `NFR3.2` 明寫壞值處置（fail-fast 或降級）及其理由，與 `BR1.6` 對齊或說明為何例外。 | New |
| R-06 | Minor | `security-requirements.md` `NFR7.1` | 需求寫「不得為 localhost、127.0.0.1、或任何公開 IP／網域」，但單憑主機名字串無法判斷一個單標籤名稱是否為 compose 服務。實作靠格式規則拒絕 IP 字面值與 FQDN，單標籤的外部可解析名稱（例如 `/etc/hosts` 或 extra_hosts 對映）仍會通過。這是 `RR-1` 失效條件之外的第二條繞過路徑，產出未登記。 | 在 `RR-1` 的失效條件補一條：單標籤主機名被 extra_hosts 或 DNS search domain 解析到 compose 網路外；或明寫此為接受的殘餘。 | New |
| R-07 | Minor | `security-requirements.md` 第六節 `U5-1`；`traceability.json` 同 id | `U5-1` 稱「已實測 memory_records 尚未落地，遷移成本為零」。依 story map，`U5 memory-data` 與本單元為平行單元，該聲明是時間點事實，可能在本單元後續站已變。我依審查範圍規定未開啟 U5 的檔案，無法複驗。 | 由 U5 的承接站確認 `embeddingModel` 為可空且無封閉 CHECK，並把此聲明標註取得時間。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep 核對 `.env.example`、`render-env.sh`、`docker-compose.deploy.yml` 的 embedding 變數 | `EMBEDDING_TIMEOUT_SEC` 在三個設定檔與 deploy compose 第 124 行皆存在 | 支持 R-01（compose 為實際第四個同步點）與 R-04（行號偏移） |
| 讀取 `embedding_port.py` 的 import、逾時、端點驗證段落 | 無 DB 或授權 import；logger 為 `cloud360.embedding_port`；逾時為具名常數 | `SEC-1`、`NFR3.2` 的具名常數要求與程式一致；R-02 至 R-06 的依據 |
| 前次 review-01（nfr-requirements） | 三項 Minor 皆為 Resolved | 前次發現已處置，不重列 |
| 未執行測試與 lint | 依 brief 禁止產生快取或寫檔 | 無測試結果可引用 |

