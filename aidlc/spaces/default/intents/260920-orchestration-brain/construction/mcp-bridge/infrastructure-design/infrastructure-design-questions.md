# Infrastructure Design 問題檔 — `U21 mcp-bridge`

> 撰寫時間 2026-10-14T23:41:11Z（`date -u` 取值）。**本站出題數為 0。**
>
> 本單元的部署形狀在上游已被三層定案夾住：`brain-infra` 的 `[I6]`=A（`internal` 網段上的第七個 compose 服務、HTTP、不發佈
> `ports:`）與 `[I7]`=A（產生器 ＋ allowlist ＋ 漂移閘門）定了「有沒有、長什麼樣」；`functional-spec.md` §八 H-1–H-12 與 nfr-design
> 六份產出定了服務定義的每個鍵、CI 的兩條依賴路線與 `stop_grace_period`；使用者 2026-10-14T23:02:07Z 與 23:34:57Z 兩次裁決收掉了
> 明文 JWT 與 SDK 路線兩題（`../carried-review-items.md:25`、`:44`）。本站逐項查過剩下的基礎設施選擇，每一項都落在下列兩種之一：
> (1) 已核可字面只容許一種做法；(2) 是 compose／workflow 的一個鍵或一個步驟的取值，預設錯了是一行 diff，**不構成重工、不改寫任何
> 已核可字面、也不改變網路暴露面或 IAM**。依派工，只有「預設錯了會造成真實重工、改寫已核可字面、或涉及網路暴露／IAM 的高風險變更」
> 才出題，故 0 題。所有預設與其後果於核可關卡揭露（`infrastructure-specification.md` 第十節）。
>
> 先例：`U13 brain-gateway` 同站出 1 題（`IG1`），是因為「空金鑰要不要擋部署」會改變**整個 staging 會不會更新**；本站唯一形狀相近的
> 選擇（下表 #1，部署後 bridge 健康檢查）刻意取**不改變部署結果**的那一側，故不構成同類題。

## 〇、上游已定案、本站不重問（附出處）

| 事項 | 定案處 |
|---|---|
| 第七個 compose 服務、HTTP（streamable HTTP）、`networks: [internal]`、不發佈 `ports:` | `brain-infra` `[I6]`=A（`../../brain-infra/infrastructure-design/infrastructure-design-questions.md:297`） |
| 工具宣告一律自 `openapi.json` 產生、allowlist 預設拒絕、產物進版控 ＋ CI `--check` | `brain-infra` `[I7]`=A（同檔 `:366`）；漂移閘門落 `backend` job（`BR72.9`、`NFR21.31`、H-4） |
| 明文使用者 JWT 於 `internal` 網段 | 使用者 2026-10-14T23:02:07Z 經選單**接受**，沿用 `[G2]`=A（`../carried-review-items.md:25`）；殘留「同主機任一容器被攻破即可竊聽」已揭露 |
| SDK 路線（直接註冊 `CallToolRequest` 處理函式優先、做不到才接受 `isError` 形狀） | 使用者 2026-10-14T23:34:57Z 裁決（`../carried-review-items.md:44`），由 `code-generation` 第一步實測 |
| 依賴路線順序（第一順位 → 較舊 `mcp` → 獨立 virtualenv → 升 FastAPI 須另開題） | `../functional-design/functional-spec.md` §十二 第 1 步；第二退路的 CI 與映像形狀見 `../nfr-design/reliability-design.md` §6.3 |
| 零環境變數、設定全走命令列參數 | `BR71.1`、`NFR21.17`、H-6 |
| `--host` 預設 `127.0.0.1`、compose `command` 明列 `--host 0.0.0.0` | functional-design `R-18`、`NFR21.16` ①② |
| `stop_grace_period: 15s` | `../nfr-design/reliability-design.md` §八（nfr-requirements `R-09` 第 2 點的 Required action 二擇一之一） |
| 不加入 CI test stack（`deploy/docker-compose.test.yml`） | `brain-infra` `cicd-pipeline.md:351`（第 26 項）、H-9 |
| 記憶體上限以公開基準設暫定值、`DEPLOY.md` 標記未量測並限期複量 | `brain-infra` `[I2]`=C ＋ `[I2b]` 反轉後版本（`infrastructure-design-questions.md:222`） |
| healthcheck 不得用需要認證的端點；`/healthz` 在全部閘門之外 | `brain-infra` `monitoring-design.md` §七 界限 1；`BR71.3`；`../nfr-design/logical-components.md` §二 |
| `depends_on: [backend]` 不帶 `condition` | `BR71.4`、`NFR21.25`、`NFR21.32` |

## 一、刻意不出成題目的設計選擇（附「為何預設錯了不構成重工、不改寫已核可字面、不涉網路暴露／IAM」）

| # | 本站預設 | 不出題的理由 |
|---|---|---|
| 1 | `deploy.yml` 的 `deploy` job 新增一步「等 `mcp-bridge` 健康」，**失敗只發 `::warning::`、不讓部署失敗、不觸發 rollback** | `NFR21.32` 只要求「部署後實測健康狀態為 `healthy`」，未規定機制；本步驟讓這個實測每次部署都自動留下紀錄。擇非阻擋的理由：本版**沒有任何實際 client**（`OPEN-MB21-1`），bridge 失效對使用者的影響為 0（`../nfr-design/logical-components.md` §三），而阻擋會讓一個零影響的失效把 backend／frontend 的無關修正一併回滾——那是**改變部署結果**的選擇，才需要出題。改為阻擋是同一步驟最後一行的結束碼，不是重工；建議在大腦 client 落地的後續 intent 一併改為阻擋（第十節揭露） |
| 2 | 記憶體上限 `512m`（暫定、未量測） | `[I2b]` 已核可「先以公開基準設值、限期複量」；數值是 compose 的一個鍵。推導見 `infrastructure-specification.md` 第二節（納入 nfr-design 審查 `R-08` 的放大係數） |
| 3 | healthcheck `interval: 10s`、`timeout: 5s`、`retries: 3`、`start_period: 10s` | 四個 compose 鍵；`/healthz` 不經閘門、無 I/O，參數只影響偵測速度。與 `redis` 的 `10s` 同節奏 |
| 4 | 映像：`mcp-bridge` 與 `backend` 各自 `build:` **同一個** context（`../backend`），不另立 Dockerfile、不共用 `image:` 標籤 | H-1 已核可「`build: {context: ../backend}`（同 backend）」；兩個服務的映像層內容相同，BuildKit 快取命中、磁碟上的層以內容雜湊去重。改為共用標籤是 compose 的兩個鍵 |
| 5 | `ci.yml` 的 `backend` job 加 `timeout-minutes: 15` | nfr-design 審查 `R-09` 第 3 點指出該 job 無上限、子進程卡住會占住 runner 到預設 360 分鐘。15 與同檔既有先例相同（`ci.yml:557`）；本分支最近 4 次成功執行的 `backend` job 耗時 82／107／94／104 秒（`gh run view` 讀取，時間戳相減），15 分鐘約為最大值的 8.41 倍。一行 diff |
| 6 | 漂移閘門步驟名 `MCP tool spec drift`，放在 `WS contract spec drift`（`ci.yml:299-300`）之後、`Run unit tests`（`:303-306`）之前，**不帶 `env:` 區塊** | H-4 已核可落 `backend` job；`brain-infra` 第 23 項已論證閘門之間不需排序（`cicd-pipeline.md:338`）。不帶 `env:` 是因為 `gen_mcp_tools.py` 只 import 純函式 `mcp_bridge.generator`、不 import `main`（與 `:294-298` 的 WS 閘門同理由）。位置是一段 YAML 的上下移動 |
| 7 | 第二退路下 `LOCAL-DEV.md` 的更新由「建議」升為 `code-generation` 必做 | `project.md` 的同步規則以觸發檔案列舉（schema 補丁、`nginx.conf`、`.env.example`、`render-env.sh`），第二退路的改動不在其中；但同一條規則的由來是「`LOCAL-DEV.md` 是唯一寫下隱性前置條件的地方」，而第二退路使「本機跑測試需要先建 `.mcp-venv/`」成為新的隱性前置條件。這是嚴格疊加的處置，不改寫規則字面 |
| 8 | `mcp-bridge` 服務區塊**不寫 `environment:`、不寫 `env_file:`、`command` 內不含 `${…}`** | `BR71.1` 零環境變數的直接後果。`brain-infra` `cicd-pipeline.md:352` 寫「可直接寫在 compose 的 `environment:` 內」——那是在 bridge 讀環境變數的前提下；本單元已定為命令列參數，`environment:` 會是一個 bridge 不讀的死區塊。這是對上游一個條件式說法的落點，不改寫其結論（`render-env.sh`／`deploy/.env.example` 不改） |

## 二、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據（本站實查） |
|---|---|---|
| 部署策略 | **有標的**：第七個服務的完整定義、映像建構、部署後健康紀錄、回滾語意 | `deploy/docker-compose.deploy.yml` 現有 6 個服務（以 awk 列出 `services:` 區塊內的頂層鍵：db、backend、redis、ollama、frontend、cloudflared），無 `mcp-bridge`；`backend/mcp_bridge/` 不存在 |
| 運算／儲存／網路 | **有標的**：記憶體上限、`internal` 成員 4 → 5 的重算（`OPEN-MB21-12`）、host 可達面 | `deploy/docker-compose.deploy.yml:409-414` 註解逐字承認同網段 ICC 與 host 行程可達；無 volume |
| 監控 | **無新管線**；新增 log 查詢與部署後健康紀錄 | repo 無 metrics 管線（`project.md ## Deployment`）；`../nfr-design/observability-design.md` §七 |
| CI/CD | **有標的**：一個新閘門步驟、一個 job 上限、第二退路的 venv 步驟 | `ci.yml:242-306` 的 `backend` job 無 `timeout-minutes`、無 `gen_mcp_tools` |
| Secrets | **無標的**：不新增任何 secret 或 variable | bridge 不持有憑證，token 每請求由標頭帶入（`BR73.3`） |
| 擴縮 | **無標的**：單一副本；並行上限為應用層常數 16 | `NFR21.21`、`NFR21.23`；多實例能力存在但本版不部署第二副本 |

## 三、問題

（無。理由見檔頭與第一節；各預設的後果於 `infrastructure-specification.md` 第十節彙整，供核可關卡呈現。）
