# 基礎設施規格 — `U7 hierarchy-service`

## 一、判定：零基礎設施變更

**逐項對照 `infrastructure-design` 的 condition**（逐字：「Infrastructure services
need mapping, deployment architecture required, or cloud resources needed.
**Skip if no infrastructure changes and infrastructure already defined.**」），
兩個條件皆成立，故本單元無基礎設施規格可產：

| condition 的子句 | 本單元的事實 | 依據 |
|---|---|---|
| no infrastructure changes | 零新服務、零新進程、零新監聽埠、零新環境變數、零新 volume | `unit-of-work.md:43` 逐字 `embedded（同一 FastAPI process 的新 router）`；`functional-spec.md` §七之三 Network exposure 列逐字「不新增任何對外進程邊界、不新增任何監聽埠」 |
| infrastructure already defined | `U1 brain-infra` 的 `infrastructure-design` 已交付並登記完成（含 compose、Redis、Ollama、nginx、監控） | `construction/brain-infra/infrastructure-design/` 四份產出 |

**對照組**：本 intent 中真正需要本站的是 `U1 brain-infra`（Redis ＋ Ollama 兩個新
服務）與 `U21 mcp-bridge`（`unit-of-work.md:309` 逐字 `standalone（獨立進程，
不在 FastAPI process 內；僅供同主機連接）`）。本單元不屬這兩類。

## 一之二、上游依據（逐一指名，避免本站看起來像憑印象判定）

本站的「零基礎設施變更」不是直覺，而是上游五份 NFR 設計與兩份契約文件
逐一指向同一結論：

| 上游產出 | 它說了什麼 | 對本站的意義 |
|---|---|---|
| `performance-design.md` | 無新延遲預算或吞吐目標；不設快取、分頁或索引設計 | 無需任何基礎設施層的效能元件（快取服務、CDN、讀寫分離） |
| `security-design.md` | 授權全部在 `HierarchyFacade`（應用層），底層 service 無第二道檢查 | 授權**不靠**基礎設施（無 API gateway 規則、無 WAF 規則、無網段隔離需求） |
| `scalability-design.md` | 非獨立擴展單位、進程內零狀態 | 無新的水平擴展單位、無 session affinity、無狀態同步元件 |
| `reliability-design.md` | 無外部依賴邊界；冪等語意已由 `K-07` 定案 | 無需 circuit breaker、重試代理或佇列 |
| `observability-design.md` | 不新增監控目標；logger 命名為沿用義務 | 無新的 metrics exporter、無新的 dashboard、無新的告警規則 |
| `logical-components.md` | 三層形狀全部在同一個 process 內（`hierarchy_router` → `HierarchyFacade` → `hierarchy_service`） | **三個邏輯元件對應零個新的部署單位** |
| `components.md` | `ProjectHierarchy` 的 external dependencies 為 PostgreSQL（主 schema）與既有 `user_diagrams` 表 | 兩者皆為既有基礎設施，非本單元新增 |
| `contract-summary.md` | `K-07` 的 `consumers.in_process` 為四個同進程呼叫端；HTTP 消費端為 `U16`／`U23` | 消費全部在同一個 process 或既有 HTTP 表面內，**無跨進程傳輸需求** |

**一句話**：八份上游產出沒有任何一份要求新的執行環境元件。

## 二、`NFR8.1` 的二元判準（本站的唯一可驗證產出）

上游 `nfr-requirements` 的 `NFR8.1` 要求本單元**不得新增任何部署設定**。
判準為機械可判，驗證落點在本單元的 `code-generation`：

1. `python3 scripts/validate_env_contract.py` 綠燈；
2. 本單元的 diff **不含** `deploy/`、`deploy/render-env.sh`、
   任一 `.env.example`、`deploy/docker-compose.*.yml`、`deploy/nginx.conf`。

**為什麼這一項要被寫下來**：`project.md` 的 blocking 規則逐字要求「新增 compose
消費的變數時，同一個 PR 必須讓 `render-env.sh` 寫它、`deploy/.env.example` 列它」，
而**失敗模式是無聲的**——無 fallback 的變數缺值時只會變成空字串，服務照常啟動
但功能降級（實例：`N8N_USER`／`N8N_PASSWORD` 從未被寫入，導致每次部署的架構圖
icons 都靜默退回灰底佔位圖）。本單元宣稱零新設定，故這條規則對它不觸發——
但那個宣稱本身需要上述兩項判準來守住。

## 三、`LOCAL-DEV.md` 的同步義務：本單元不觸發

`project.md` 逐字要求異動 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`、
任一 `.env.example` 或 `render-env.sh` 時必須同步更新 `LOCAL-DEV.md`。
本單元**四者都不動**（schema 屬已交付的 `U4`），故不觸發。
若 `code-generation` 期間發現必須動其中任一項，該規則即由不觸發轉為 blocking。
