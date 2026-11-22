# NFR Requirements 問題檔 — `U6 embedding-port`

> Stage：`nfr-requirements`（3.2）　Unit：`U6 embedding-port`（`library`，M）
> Depth：**Minimal**　Review：advisory（1 輪）　建立時間：2026-10-04　作答完成：2026-10-04T21:09:51Z（`date -u` 取值）
>
> `produces_kinds` 把 performance／scalability／reliability／observability 四項排除在
> `library` 之外，故本站只產出 `security-requirements.md`、`tech-stack-decisions.md`、
> `traceability.json` 三件。

---

## 〇、已由上游定案、**不重問**（每項皆可引用出處）

| 已定案 | 出處 |
|---|---|
| 四個提供者、`EMBEDDING_PROVIDER` 切換、無預設、大聲失敗 | ADR-008；K-01 |
| `embed` 與 `model_id` 的簽章、sync、不重試、不讀 DB、不碰授權 | K-06 |
| `fulltext` ⇒ 無 Port；`model_id` 回模型身分；啟動驗設定／首呼驗連線；`fastembed` 選用 lazy import | `functional-design` 的 `[Q1]`–`[Q4]`（本單元同站已核可） |
| PBT 六個性質與其可驗範圍 | `functional-design/functional-spec.md §五` |
| ollama 服務對外暴露面為零、不得 publish port | K-01 `images_and_services`；`deploy/.env.example` |

## 〇·二、出題前的唯讀查證（**非來源**）

- `NFR7` 逐字：「episodic memory 為 by-user 的對話歷程，屬個人可識別的使用歷程，
  **其靜態儲存與傳輸的加密要求須於設計階段明確**。」
- `deploy/.env.example:120` 的 `OLLAMA_BASE_URL=http://ollama:11434` → **明文 HTTP**；
  `:119` 的註解逐字「它的 HTTP API **零認證**，網段隔離是它唯一的存取控制」。
- `K-06` **沒有指定任何 timeout**。而本 repo 既有實務是每個外部 httpx 呼叫都帶
  timeout：`diagram_builder.py:1860` 為 `5.0`、`review_router.py:425` 為 `90.0`、
  `review_orchestrator.py` 與 `wa_score_service.py` 用具名常數 `LENS_AGENT_TIMEOUT_SEC`。
- `NFR10` 逐字把落點指向 `nfr-requirements`（3.2），並寫「若該站被 skip，本工作流程
  **沒有自然承接站**」——但它講的是**路由層**模型（`U11 intent-router`），不是 embedding 模型。
- `backend/requirements.txt` 無 `fastembed`、無 lockfile；`fastapi`／`pydantic` 以外皆未 pin。

---

## Q1 `NFR7` 的傳輸加密要求：記憶文字以**明文 HTTP** 送到 ollama

`NFR7` 明文要求「傳輸的加密要求須於設計階段明確」。本單元是唯一把記憶文字送出
backend 行程的元件——`ollama` 實作把待向量化的文字（即使用者的對話與設計決策內容）
以明文 HTTP 送到 `http://ollama:11434`，而該服務**零認證**。

- **A（建議）— 接受明文，但把「網段隔離是唯一控制」寫成具名需求與具名殘餘風險。**
  要求：(i) `OLLAMA_BASE_URL` 的主機名必須是 compose 內部服務名，啟動時驗證它
  **不是** `localhost`／`127.0.0.1`／公開 IP；(ii) ollama 服務不得 publish port，
  此為 `U1` 的交付但由本單元在 `security-requirements.md` 具名為依賴前提；
  (iii) 明文傳輸列為**具名殘餘風險**，不寫成「不適用」。
  理由：同主機 compose 內部網段，TLS 的威脅模型收益低而維運成本（憑證、輪替）高；
  且這與 Redis 在同一個 stack 的處置一致。代價：若日後 ollama 移到另一台主機，
  這個決定立即失效——該條件必須寫進需求本文，不能只存在於這段理由裡。
- **B — 要求 TLS。** 對 ollama 端點強制 https。代價：ollama 容器需自簽憑證與憑證
  掛載，`U1` 已交付的 compose 與 `render-env.sh` 都要改（跨單元），而威脅模型是
  同主機內部網段——防的是已經能進入該網段的攻擊者。
- **C — 要求先在本機遮罩／摘要再送出。** 不把原文送給 ollama。代價：embedding 的
  輸入就是語意本身，遮罩會直接破壞檢索品質——這等於廢掉 `FR4.1`。
- **D — 判為不適用，因為 ollama 在同一台主機。** 代價：`NFR7` 逐字要求「明確」，
  判不適用而不寫明控制手段，等於把 hard constraint 以一句話帶過（`project.md` 明文
  禁止「僅以『已有 ADR-0006』帶過」）。

[Answer]: A

## Q2 換 embedding 模型會讓既有記憶**靜默**檢索不到

`BR3.5` 要求 `model_id` 隨向量空間改變而改變，`BR3.4` 要求檢索只比對同一
`embeddingModel` 的列。兩者合起來的後果是：**把 `OLLAMA_EMBED_MODEL` 換掉之後，
先前寫入的全部記憶會被過濾掉**——不是回錯答案，是**查不到**，而且不報錯。
這比 ADR-008 原本要防的「回垃圾」輕，但它仍然是靜默的。ADR-008 沒有處理這一面。

- **A（建議）— 要求啟動時偵測並大聲說出來，但不自動重算。**
  啟動時比對「目前 `model_id`」與「記憶表中已存在的相異 `embeddingModel` 集合」，
  若目前這個不在其中且表非空，記一條 **WARN 等級以上**的訊息寫明
  「既有 N 列記憶以 `<舊 model>` 寫入，本次啟動為 `<新 model>`，那些記憶在
  重新 embed 之前不會被檢索到」。**不自動重算**——重算是一個會打外部服務 N 次的
  批次作業，不該在啟動路徑上。代價：這個偵測需要讀 DB，而 `BR2.7` 禁止本 Port 讀 DB
  ——故**偵測的落點必須是 `U8`，不是本單元**；本站只能把它寫成對 `U8` 的具名需求。
- **B — 要求啟動時失敗。** 模型與既有資料不一致即拒絕啟動。代價：換模型變成
  一個需要先做資料遷移才能啟動的操作，而本機開發者在 `fulltext`／`fastembed`／`ollama`
  之間切換是 `[Q4]` 已核可的常態用法——這會讓那個常態用法每次都卡住。
- **C — 要求提供一個重新 embed 的指令或腳本。** 根治。代價：那是一個新的批次
  作業（讀全部記憶、逐列呼叫 `embed`、寫回），屬 `U8`／`U9` 的範圍，不是一個
  library 單元能交付的；且 `project.md` 禁止以 repo 內程式承載無人值守的流程自動化。
- **D — 不處理，接受靜默。** 代價：「為什麼找不到我的記憶」正是 ADR-008 Decision
  逐字說要避免的那個無法除錯的問題。

[Answer]: A

## Q3 `embed` 呼叫的 timeout

`K-06` 沒有指定任何 timeout，而本 repo 的既有實務是**每個外部 httpx 呼叫都帶 timeout**
（`diagram_builder.py:1860` 為 `5.0`、`review_router.py:425` 為 `90.0`、
`review_orchestrator.py`／`wa_score_service.py` 用具名常數）。沒有 timeout 的
`ollama` 呼叫會讓記憶寫入或檢索無限期掛住，而那條路徑可能落在 `NFR3`
（首字回應 P50 ≤ 2 秒）的預算內。

- **A（建議）— 具名常數、預設 10 秒、可由環境變數覆寫，逾時即拋 `EmbeddingProviderUnavailable`。**
  形式沿用 `LENS_AGENT_TIMEOUT_SEC` 的既有形狀（具名常數而非字面值）。
  10 秒的依據：`bge-m3` 對短文字的本機推論通常在百毫秒級，10 秒是「服務掛了」
  而非「這批比較慢」的判準。逾時歸入既有的 `EmbeddingProviderUnavailable`，
  不新增第二種例外。代價：新增一個環境變數 → 觸發 `render-env.sh` ＋
  `deploy/.env.example` ＋ `LOCAL-DEV.md` 三處同步（`project.md` blocking）。
- **B — 固定 10 秒，不可設定。** 少一個環境變數、少三處同步。代價：批次較大或
  主機較慢時無法調整，只能改 code 重新部署。
- **C — 沿用 `diagram_builder` 的 5 秒。** 與既有最短的那個一致。代價：`bge-m3`
  第一次呼叫可能含模型載入（`ollama pull` 之後的首次 warm-up），5 秒可能不夠，
  而那會表現為「部署後第一次用記憶就失敗」。
- **D — 不設 timeout，由呼叫方 `U8` 以 `asyncio.wait_for` 包。** 代價：把一個
  外部呼叫的基本防護推給每一個呼叫端，而 `U8` 現在是唯一呼叫端、未來未必是；
  且與 repo 既有實務（在呼叫處設 timeout）不一致。

[Answer]: A

## Q4 `fastembed` 作為使用者自裝、未釘版的選用依賴，供應鏈要求怎麼定

`[Q4]`=A 已定案 `fastembed` 不進 `requirements.txt`、由開發者自行 `pip install`。
後果：版本不受控（repo 無 lockfile，`fastapi`／`pydantic` 以外皆未 pin），
且 `fastembed` 在首次使用時會**從 HuggingFace 下載模型權重**——那是一個
repo 完全沒有管控的外部下載。`security-guide.md` 的 OWASP #6（Vulnerable
Components）與 `devsecops-pipeline-patterns.md` 的依賴掃描都指向這一面。

- **A（建議）— 在 `LOCAL-DEV.md` 釘一個已驗證的版本區間並寫明模型下載來源，
  但不納入 CI 掃描範圍。** 要求：安裝指令寫成帶版本的形式；文件註明首次使用會
  從 HuggingFace 下載約 1GB 權重、下載來源與快取位置；並明寫**此路徑不經 CI，
  其供應鏈風險由使用它的開發者承擔**。理由：它只在「本機且無 Ollama」這一條
  路徑上，不進任何 image、不進 CI、不進 staging——把它拉進依賴掃描等於為一條
  開發者自選路徑建立 CI 基礎設施。代價：這是**具名接受風險**，不是消除風險。
- **B — 納入 `requirements.txt` 並 pin 版本，進 CI 依賴掃描。** 風險最低。
  代價：直接推翻 `functional-design` 的 `[Q4]`=A（該題選項 B 的拒絕理由是
  ONNX runtime 進每個 image 並放大既有的未 pin 風險）。選此項等於重開那個決定。
- **C — 放棄 `fastembed`。** 供應鏈面歸零。代價：推翻 ADR-008 的
  Alternatives Rejected（逐字「使用者亦明確要求保留 fastembed 這條路」）。
- **D — 不定任何要求。** 代價：`NFR7`／ADR-0006 之外，`security-guide.md` 的
  OWASP #6 是本站支援 agent 的明文檢查項；完全不提它等於本站沒做供應鏈這一面。

[Answer]: A
