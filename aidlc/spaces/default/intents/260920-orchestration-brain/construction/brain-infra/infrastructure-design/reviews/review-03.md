## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站產出（infrastructure-specification、cicd-pipeline、monitoring-design）整體自洽，並已被 `deploy/docker-compose.deploy.yml` 忠實落地（redis、ollama、資源上限、logging、depends_on 拓樸皆與設計相符；前次 review-02 的 Critical 與多數 Major 已處置）。本輪補審找出兩項 Major 與兩項 Minor：(1) 修訂 1 的 `mcp-bridge` 網段設計與已落地程式矛盾，且落地的一邊較安全、較正確，使 §7.4 的 D-3 blast radius 重算表過期；(2) 前次 review-02 已提的 R-19（`deploy.yml` 行號引用漂移）仍留在凍結產出中。兩項 Major 未超過 2 項，且不影響任何已核可的架構決定，故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/brain-infra/infrastructure-design/infrastructure-specification.md` §7.1「網段與端口」、§7.3 Network exposure 與 Encryption 列、§7.4 blast radius 表；`cicd-pipeline.md` 改動清單第 25 項 | 設計寫 `mcp-bridge` 為 `networks: [internal]`，並據此算出 `internal` 成員 4 增為 5、`redis`／`ollama` 的 blast radius 由 3 增為 4（「D-3 效益部分侵蝕」）。已落地的 `deploy/docker-compose.deploy.yml:400-446`（mcp-bridge 服務）實際是 `networks: [mcp]`，`mcp` 為獨立且 `internal: true` 的網段，成員只有 `backend` 與 `mcp-bridge`，檔內註解明寫「not `internal`, not `edge`」。因此落地版 `internal` 成員仍是 4、`redis`／`ollama` blast radius 維持 3，D-3 並未被侵蝕，§7.4 的 4 是錯的；§7.3 Encryption 列「與 internal 上既有容器間流量同一姿態」也不適用於新網段。**落地的一邊是對的**（比設計更窄，且切斷 bridge 的對外路徑）。另設計未提第三個網段，三網段拓樸沒有任何一份設計產出描述。 | 在 §7.1／§7.3／§7.4 與 cicd 第 25 項補一個更正說明（凍結產出不回改正文，以修訂段承載）：mcp-bridge 在獨立 `mcp` 網段、internal 成員數不變、blast radius 表沿用 3；並把 `mcp` 網段寫入網路拓樸。 | New |
| R-02 | Major | `infrastructure-design/cicd-pipeline.md` §二「探測的重試窗口與 job 逾時的關係」表（第 62–64 行）；`infrastructure-specification.md` 第 352 行；前次 review-02 R-19 已提 | 對 `.github/workflows/deploy.yml` 的行號引用仍是舊座標：`rollback` 引為 `169–301`、`timeout-minutes: 20` 引為 `:177`，但現行檔 `rollback:` 起於 `:649`、`notify:` 起於 `:840`、`deploy` 的 `seq 1 24` 迴圈在 `:361`。引用的內容落點（哪個 job、哪些步驟）已指向無關程式碼，牆鐘上界不等式的推導因此無法機械複驗。注意：行號隨 workflow 持續變動，單靠改數字無法長期正確。 | 把行號引用改為步驟名稱或 job 名稱（不依賴行號），或在引用旁註明取得日期與 commit；至少更正上述四組座標。 | New |
| R-03 | Minor | `infrastructure-specification.md` §7.3 Encryption 列（前次 review-02 R-20 未處置） | Encryption 判定表只談 in-transit／at-rest，未交叉引用 §7.2「認證欄位處置：產生時剝除 `HTTPBearer`」，單獨讀此表看不到 `unit-of-work.md` 修訂 4 要求的「工具 schema 不得含 token／key／secret／authorization 欄位」已被處理。 | 在 Encryption 列補一句指向 §7.2 的交叉引用。 | New |
| R-04 | Minor | `infrastructure-design/monitoring-design.md` 第 177 行 `mcp-bridge` healthcheck 列 | 設計明寫 liveness 路徑「由 `U21` 的 code-generation 決定後**回寫本表**」。落地後實際為 `GET /healthz`、埠 8080（`docker-compose.deploy.yml` 的 mcp-bridge healthcheck），但三份產出對 `healthz` 零命中，回寫契約的「誰寫」一端沒有被履行。 | 以修訂段回寫實際路徑與埠，或明記此回寫已由 code-generation 的產出承接。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取 `deploy/docker-compose.deploy.yml` 服務與網段 | 7 個服務（db、backend、redis、ollama、frontend、cloudflared、mcp-bridge）；網段 edge、internal、mcp | 服務數與 §7.5 日誌上界（7 × 50m × 5 = 1.75GB）相符；網段與 §7.1 不符，見 R-01 |
| grep `deploy.yml` job 位置 | `deploy:` :25、`seq 1 24` :361、`rollback:` :649、`notify:` :840 | 與文件引用的 169–301、:177 不符，見 R-02 |
| grep `healthz` 於三份產出 | 皆為 0 命中 | 見 R-04 |
| 前次 review-02 發現處置抽查 | R-02、R-03、R-04、R-05 的落地內容（ollama pull、depends_on 拓樸、資源上限、logging 錨點）在 compose 與註解中可見 | 設計被忠實實作，Critical 已實質處置 |
