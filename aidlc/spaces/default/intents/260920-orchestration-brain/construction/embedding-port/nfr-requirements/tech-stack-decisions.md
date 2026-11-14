# Tech Stack Decisions — `U6 embedding-port`（`library`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: embedding-port · kind: library -->

## 〇、本檔的範圍

本單元是 `library`，**不選框架、不選資料庫、不選基礎設施**——那些在 `U1 brain-infra`
已交付（pgvector image、ollama 服務、模型快取 volume、四個環境變數）。

本檔要定的只有三件事：**用哪些既有依賴**、**新增什麼**、以及**改動面有多大**。
最後一項是 `code-generation` 會直接讀的那一項，所以它必須完整——
`rbac-story-ids` 的 `SEC-4` 已經示範過「改動範圍擴大但沒寫進本檔」會造成什麼。

## 一、技術選擇

| 項目 | 選擇 | 理由 | 新增依賴？ |
|---|---|---|---|
| HTTP 客戶端（`ollama` 實作） | **既有 `httpx`** | 已在 `backend/requirements.txt`（實測）。`BR6.2` 禁止為此新增第二個 HTTP 客戶端 | **否** |
| 行程內推論（`fastembed` 實作） | **`fastembed`，選用、lazy import、不進 `requirements.txt`** | `[Q4]`=A（`functional-design`）。三個環境中只有「本機且無 Ollama」會選它：`backend/.env.example:119` 預設 `fulltext`、`deploy/.env.example:116` 為 `ollama`、`docker-compose.test.yml:18` 為 `stub` | **否**（使用者自裝） |
| 決定性替身（`stub` 實作） | **純標準庫** | 需求只有「決定性」與「1024 維」。用 `hashlib` ＋ 標準庫即可，不需任何套件 | **否** |
| Property-based 測試 | **既有 `hypothesis`** | 已在 `requirements.txt`（實測）。ADR-0006 的 PBT hard constraint 落點 | **否** |
| 測試框架 | **既有 `unittest`** | `team.md ## Testing Posture` 的既成事實：**不是 pytest**；CI 跑 `python -m unittest discover -s tests -v` | **否** |
| logger | **`logging.getLogger("cloud360.<module>")`** | `team.md ## Code Style` 的既成慣例：新模組一律此形式（既有 5 支用 `__name__` 的是已知不一致，不效法） | **否** |

**`backend/requirements.txt` 的淨變更：零。** 這是刻意的結果，不是巧合——
`[Q4]`=A 與 `BR6.2` 兩個決定都指向它。

## 二、新增的環境變數

| 變數 | 由誰定 | 必填性 | 預設 | 三處同步 |
|---|---|---|---|---|
| embedding 呼叫的 timeout（秒） | 本站 `[Q3]`=A、`NFR3.2` | 選填 | **10** | `deploy/render-env.sh` 寫它、`deploy/.env.example` 列它、`backend/.env.example` 列它，**並同步更新 `LOCAL-DEV.md`** |

**這是 `project.md ## Mandated` 的 blocking 規則**（`NFR8.1`）。失敗模式無聲：
無 fallback 的變數缺值時只會變成空字串，服務照常啟動但功能降級。
本變數**有**預設值（10），所以缺值不會變成空字串災難——但它仍須被列出，
否則沒有人知道它可以調。

本單元**消費但不新增**的四個既有變數（`U1` 已交付）：
`EMBEDDING_PROVIDER`、`OLLAMA_BASE_URL`、`OLLAMA_EMBED_MODEL`、`FASTEMBED_MODEL`。

## 三、改動面（`code-generation` 直接讀這一節）

| # | 檔案 | 性質 | 範圍 |
|---|---|---|---|
| 1 | `backend/services/embedding_port.py`（新） | 新檔 | Port 介面 ＋ 選擇器 ＋ 三個實作 ＋ `EmbeddingProviderUnavailable` |
| 2 | `backend/tests/test_embedding_port.py`（新） | 新檔 | 六個 PBT 性質（`P1`–`P6`）＋ 啟動驗證測試 ＋ 逾時路徑測試 ＋ 憑證遮罩測試 |
| 3 | `backend/.env.example` | 既有檔，新增一行 | timeout 變數 ＋ 其註解 |
| 4 | `deploy/.env.example` | 既有檔，新增一行 | 同上 |
| 5 | `deploy/render-env.sh` | 既有檔，新增一行 | 寫出 timeout 變數 |
| 6 | `LOCAL-DEV.md` | 既有檔 | **兩項**：(a) timeout 變數（第 3–5 項觸發的 blocking 同步）；(b) `fastembed` 的帶版本安裝指令 ＋ HuggingFace 下載說明 ＋「此路徑不經 CI」警語（`SEC-3`） |

**本單元不改**：`backend/requirements.txt`、任一 compose 檔、`schema_rbac.sql`、
`DEPLOY.md`、`backend/database.py`、`backend/models.py`。

**`LOCAL-DEV.md` 的隱性硬依賴由 2 個變 3 個**（`claude` CLI、n8n webhook、
**`fastembed`**）——這是 `[Q4]`=A 的直接後果，必須寫進該檔而不只是記在這裡。

## 四、不在本單元、但本單元依賴的既有交付

| 依賴 | 誰交付 | 本單元的依賴形式 |
|---|---|---|
| ollama 服務（第 6 個容器）＋ 模型快取 volume ＋ `ollama pull` 步驟 | `U1 brain-infra` | `ollama` 實作的執行前提；`NFR7.2` 具名其「不得 publish port」為安全前提 |
| pgvector image ＋ `vector(1024)` 欄位 | `U1`（image）／`U5`（欄位） | **本單元不碰**——它只產生 `list[float]`，寫入是 `U8` 的事 |
| 四個 embedding 環境變數的 `render-env.sh`／`.env.example` 落地 | `U1` | 本單元是它們的**第一個執行期讀取者**（`NFR8.2`） |

## 五、本站未選、且刻意不預選的事

| 事項 | 為什麼不在本站定 |
|---|---|
| 向量是否 L2 正規化 | 度量選擇屬 `U8` 的檢索設計；K-06 未要求。`functional-design` 已記為 `OQ-E3` |
| `ollama` 的重試次數上限 | K-06 逐字「本 Port 自身不重試，重試次數上限由呼叫方依 `[C9]` 的上限設定」。本站只定 timeout（`NFR3.2`），不定重試 |
| 路由層模型（`typesafe/jev-1.13`） | `NFR10` 講的是**路由層**，承載為 `U11 intent-router`。見 `security-requirements.md` 的 `RR-3`——該項的承接狀態需要確認，不得靜默落空 |
| 重新 embed 的批次作業 | `[Q2]` 選項 C 的拒絕理由：那是 `U8`／`U9` 的範圍，且 `project.md` 禁止以 repo 內程式承載無人值守的流程自動化 |
