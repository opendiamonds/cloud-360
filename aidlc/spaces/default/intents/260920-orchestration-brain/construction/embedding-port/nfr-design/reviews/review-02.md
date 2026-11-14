## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元（U6 embedding-port，library）的 nfr-design 產出自洽，且與已落地的 `backend/services/embedding_port.py`、`backend/main.py` 一致：D-1（startup hook 順序）、D-4（截斷加 WARN）、D-5（每次 embed 一條 INFO 含耗時）、D-6（具名 timeout 常數，`EMBEDDING_TIMEOUT_SEC`）、D-7（剝除 userinfo）、D-8（Port 不記 ERROR）、D-9（以原始碼字串斷言守住 SEC-1）、D-10 皆可在程式中找到落點。前次 review-01 的 R-01（traceability.json 殘留「21 個」）已處置：`nfr-design/traceability.json:66` 現不複製該數字；R-02（timeout 變數名）已由 H-N4 承接並落地於 `render-env.sh:138`。ADR-0006 四面向各有判定並與上游一致。僅有三項 Minor：設計主張與落地行為的細節差異，不阻擋。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Minor | `construction/embedding-port/nfr-design/logical-components.md` 第三節「爆炸半徑」第一列、第五節 Timeout 列；實作 `backend/services/embedding_port.py:610` | 設計寫「每次 embed 在 timeout（預設 10 秒）後拋 EmbeddingProviderUnavailable」，隱含 10 秒是整體上界。實作為 `httpx.Client(timeout=EMBEDDING_TIMEOUT_SEC)`（單一 float），httpx 的語意是 connect／read／write／pool 四個階段各自 10 秒，而非總時限。單次 `/api/embed` 為非串流，read 階段實務上接近總時限，風險小，但「首字回應路徑」的最壞延遲（NFR3.1／RR-4）不是 10 秒。設計已把此缺口交給 build-and-test，但未寫明這個語意差。 | 在 code-generation 的註解或 build-and-test 的量測計畫中，把 timeout 語意改寫為「每階段」，或改用 `httpx.Timeout` 明列各階段；設計文字同步更正。 | New |
| R-02 | Minor | `construction/embedding-port/nfr-design/security-design.md` D-6；實作 `backend/services/embedding_port.py:241-277` | D-6 只定了具名常數與預設值，未定義壞值（非數字、非正數）的行為。實作在模組 import 時求值，壞值僅記 WARN 並退回預設 10 秒，且不經過 startup 驗證。這與同單元對 provider 設定「大聲失敗」（BR1.6、ADR-008）的取向不同；若刻意如此，設計沒有寫明，下一位讀者會以為漏驗。另 import 時求值使測試無法在不重載模組下覆寫。 | 在 D-6 補一句：timeout 壞值刻意採「WARN 後取預設」並說明理由（它不影響記憶正確性，只影響延遲上界），或改由 `configure_embedding_env()` 一併驗證。 | New |
| R-03 | Minor | `construction/embedding-port/nfr-design/security-design.md` D-4、H-N3；實作 `backend/services/embedding_port.py:119-123` | D-4 與 H-N3 說截斷到「提供者的 context 上限」，上限單位是模型的 token；實作的 `PROVIDER_CONTEXT_LIMIT_CHARS` 以字元截斷（ollama 8192、fastembed 512），註解卻寫「context 為 8192／512 token」。字元數 ≤ token 數的前提只在 CJK 近似一字一 token 時偏保守；對英文則會截得過多（fastembed 的 512 字元遠小於 512 token），靜默降低檢索品質，僅靠 WARN 提示。H-N3 已指派 code-generation 查實際值，但落地的單位換算沒有被記錄為決定。 | 在設計或程式註解明寫「以字元為保守近似，非 token 精確」，並說明對英文輸入的品質代價；或改用該模型 tokenizer 計數。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 直接開檔核對（`main.py` 52-72、`embedding_port.py` 119-123／241-277／440-520／596-650／296-345） | D-1／D-4／D-5／D-6／D-7／D-8／D-10 皆有對應實作 | 設計與落地無矛盾；僅 R-01 至 R-03 的語意細節 |
| `test_embedding_port.py:471-501` 檢視 | 讀原始碼斷言 DB／RBAC／router 符號零命中（`@story SEC-1、D-9、BR2.7`） | D-9 的機械保證已落地 |
| `grep` `traceability.json` 的「21」殘留 | 無（第 66 行改為不複製數字） | 前次 review-01 R-01 已處置 |
| `grep` `EMBEDDING_TIMEOUT_SEC` 於 `render-env.sh` | `deploy/render-env.sh:138` 有寫入 | 前次 review-01 R-02（H-N4）已落地 |
