# External Dependency Map — 統一入口大腦

<!-- Stage: delivery-planning（Inception 2.9）· Record: 260920-orchestration-brain -->

## 這份檔在做什麼

列出**不在這次建置範圍內、但會擋住某個 Bolt 的東西**——外部服務、資料可用性、
需要別人確認的事、跨團隊交接。每一項標明：它擋哪些單元、落在哪個 **Bolt**
（一次建置通過，做完一個或多個工作單元，結束時有東西能跑、能展示）、誰擁有它、
以及**它沒到位時該怎麼辦**。

本檔可獨立閱讀，不需先看 `bolt-plan.md`。

## 本 intent 的特殊之處：主要阻擋來自內部未決事項，不是外部

一般專案的這份檔是「等別的團隊給 API」。本 intent 不是——它只有一個 AI 執行者、
部署到自有主機、沒有外部團隊交接。**真正會擋住工作的是上游留下的未決事項**，
那些列在 `bolt-plan.md` 的各 Bolt 進入條件裡。

本檔列的五項是**真正的外部或環境相依**：兩項與自有主機有關、一項與 GitHub 的網路
可達性有關、兩項與既有部署設定有關。

---

## 五項外部相依

### E1 — `OPENROUTER_API_KEY` 在 CI 缺席

| 欄位 | 內容 |
|---|---|
| **現況** | staging 已有（既有 A1／A3／C1 在用）。但 `build-and-test` 跑的是 `ci.yml` 的 backend job，**那裡沒有金鑰** |
| **擋什麼** | `[RA:NFR1]`（意圖識別準確率 ≥ 80%）與 `[RA:NFR3]`（首字 P50 ≤ 2 秒）的量測——兩者**必然需要真實模型呼叫** |
| **落在哪個 Bolt** | B5（`U11` 路由層）的驗證面；量測機制本身落在 `build-and-test`（3.6，ALWAYS） |
| **誰擁有** | 你（repo 的 Actions secrets 設定者） |
| **沒到位時怎麼辦** | **不阻擋 B5 的交付**——B5 的功能面用可注入替身驗證（`[C8]` 定案：一般 CI 使用替身、不呼叫付費模型）。受影響的是**準確率與延遲的量測**，那需要一個帶金鑰、有預算上限的獨立評估，而**它是不是 PR 閘門是一個還沒被決定的問題**（若是，每個 PR 都付 LLM 費用；若否，它就是定期量測而非閘門） |
| **待決** | 該量測跑在哪裡、金鑰從哪來、是不是 PR 閘門。**本站不定案**，落點 `build-and-test`（3.6，**ALWAYS**，不會被 skip） |

**重要**：`project.md` 明文規定新增憑證型 secret 後必須實地查證它落在 **secrets 而非
variables**（`gh api repos/<owner>/<repo>/actions/secrets` 與同路徑的 `/variables` 各查
一次）。Actions variables 為明文、UI 可回讀、workflow log 中不遮罩，而**本 repo 為
public、Actions log 公開可讀**——一次意外 echo 即等同公開發布。

---

### E2 — Ollama 在自有 staging 主機的資源餘裕未實測

| 欄位 | 內容 |
|---|---|
| **現況** | `bge-m3` 模型約 1.2GB、Ollama runtime RAM 需求約 2GB。`domain-design` 的 Assumptions **逐字記明這兩個數字取自一般認知、未在該主機實測**，且 `DEPLOY.md`／`LOCAL-DEV.md` **未記載該主機的 RAM／CPU 餘裕** |
| **擋什麼** | `U1`（第 6 個服務與模型快取 volume）、`U6`（`ollama` 實作要能被驗證） |
| **落在哪個 Bolt** | **B1**——而且應該是 B1 的**第一件事** |
| **誰擁有** | 你（`192.168.10.10` 的管理者） |
| **沒到位時怎麼辦** | `EmbeddingPort` 有四個實作，`fastembed`（`multilingual-e5-large`，ONNX、行程內、**不拉 torch、不加服務**）與 `ollama` **同為 1024 維**，可作為退路。退到 `fastembed` 的代價是 embedding 在 FastAPI 行程內算，會吃該行程的 CPU 與記憶體——**但那是同一台主機的資源，不是省下來**，故退路只在「多一個容器裝不下、但行程內多一點記憶體放得下」時才成立 |
| **待決** | 主機實際餘裕。**B1 的驗證步驟就是量它** |

---

### E3 — GitHub Actions 連不連得到自架 staging 資料庫

| 欄位 | 內容 |
|---|---|
| **現況** | **未定**。這是 `requirements.md` 的 `OQ-13`：90 天清除 workflow 跑在 GitHub Actions 上，而資料庫在自架主機（`192.168.10.10`）後面 |
| **擋什麼** | `U9`（90 天清除）——這是**單元層級阻塞**，未定案前該單元無法完成 |
| **落在哪個 Bolt** | **B9**（條件式） |
| **誰擁有** | 你（網路與主機的管理者）。注意本 repo 已有**自架 runner**（`[self-hosted, linux, x64, cloud360]`，`deploy.yml` 在用），那可能是答案的一部分——自架 runner 跑在該網段內 |
| **沒到位時怎麼辦** | **B9 不執行**。`U9` 與 `[RA:FR4.5]`（情節記憶保存 90 天）列為本 intent 的**已知未交付項**，需明確告知而非靜默略過 |
| **待決** | `OQ-13`。落點 `infrastructure-design`（3.4，**CONDITIONAL**），轉移目標 `deployment-pipeline`（4.1，**亦 CONDITIONAL**）——**兩者都 skip 時須重新提交使用者** |

**提醒**：`project.md` 禁止以 repo 內新增的實作程式承載**無人值守的**流程自動化，
此類機制一律以 gh-aw 或 GitHub Actions workflow 承載。且決定性的映射邏輯（算出哪些
列逾期、發出刪除）應放**純 Actions 步驟**，不交給 gh-aw 的 LLM 路徑——LLM 路徑是
本 repo 三塊結構性盲區之一。

---

### E4 — 資料庫 image 由 `postgres:16-alpine` 換為 `pgvector/pgvector:pg16`

| 欄位 | 內容 |
|---|---|
| **現況** | 記憶的 `vector(1024)` 欄位需要 pgvector 擴充，而該擴充來自這個 image。**兩個 compose 檔都要改**：`deploy/docker-compose.deploy.yml` 與 `deploy/docker-compose.test.yml` |
| **擋什麼** | `U5`（記憶資料）。`docker-compose.test.yml` 是 `ui-regression` 每個 PR 自動起的短生命週期 stack——**漏改它會讓每個 PR 的測試環境沒有 pgvector** |
| **落在哪個 Bolt** | **B1** |
| **誰擁有** | 本 intent 內部（不需外部協調），但它是一次**既有資料庫容器的換版**，有現存資料的相容性面 |
| **沒到位時怎麼辦** | 沒有退路——向量檢索是 `[RA:FR4]` 的承載方式。若 image 換版在 staging 出問題，`EmbeddingPort` 的 `fulltext` 實作（退回 PostgreSQL 全文檢索、向量欄位為 NULL）可讓功能降級運作，但**那不是 `[RA:FR4.6]` 要的相似度檢索** |

---

### E5 — Redis 作為第 5 個服務

| 欄位 | 內容 |
|---|---|
| **現況** | 新增服務 ＋ 新增環境變數（`REDIS_URL`、`REDIS_PASSWORD`）。依 `project.md ## Mandated`，新增 compose 消費的變數時，**同一個 PR** 必須讓 `deploy/render-env.sh` 寫它、`deploy/.env.example` 列它，並同步 `LOCAL-DEV.md` |
| **擋什麼** | `U1`（服務定義）、`U10`（session 狀態外部化） |
| **落在哪個 Bolt** | **B1** |
| **誰擁有** | 本 intent 內部 |
| **沒到位時怎麼辦** | 沒有退路——`[RA:NFR4]` 逐字要求 session **一律放 Redis、不得放行程記憶體**，可測不變量是「重啟 backend 後既有對話的脈絡與作業對象仍可完整還原」 |

**這一項的失敗模式是無聲的**：無 fallback 的變數缺值時只會變成空字串，服務照常啟動
但功能降級。既有實例逐字記載於 `project.md`：`N8N_USER`／`N8N_PASSWORD` 從未被寫入，
導致每次部署的架構圖 icons 都靜默退回灰底佔位圖。

**另一個無聲失敗**：憑證值**不得含 `$`**——docker compose 會對 `--env-file` 的值做內插，
`ab$cd` 會被無聲截斷成 `ab`，資料庫因此以遠弱於預期的密碼運行且無任何錯誤。
`render-env.sh` 已對此擋下並要求改用 `openssl rand -hex 32`。

---

## 對照表：哪個 Bolt 受哪幾項影響

| Bolt | 受影響的外部相依 |
|---|---|
| **B1** | **E2**（Ollama 餘裕，應為第一件事）、**E4**（pgvector 換版）、**E5**（Redis） |
| B2 | — |
| B3 | E4（承 B1 的換版結果） |
| B4 | E5（承 B1 的 Redis 設定） |
| **B5** | **E1**（金鑰——影響量測面，不影響交付面） |
| B6 | — |
| B7 | — |
| B8 | — |
| **B9** | **E3**（GitHub Actions 連不連得到 DB——**條件式，未定案則本 Bolt 不執行**） |

**B1 一個 Bolt 就承擔三項外部相依**，其中 E2 是唯一需要在主機上實地量測的。

---

## Assumptions & Open Questions

- 本檔的五項由本站盤點、經使用者確認為完整（`[D5]`=A：「五項都對，沒有漏的」） [assumption]
- **E1 與 E3 有真正的未決成分**：E1 的「量測跑在哪裡、是不是 PR 閘門」是
  `build-and-test`（ALWAYS）的待辦；E3 的 `OQ-13` 落點與轉移目標皆為 CONDITIONAL [assumption]
- 本檔**不含時程**（前置時間、交付日期）。沒有外部團隊交接，也沒有實證的工時基準 [assumption]
- 自架 runner 可能是 E3 的答案，但**本站未查證它的網路可達性與資料庫憑證是否具備**
  ——只指出它的存在供 `infrastructure-design` 參考 [assumption]
