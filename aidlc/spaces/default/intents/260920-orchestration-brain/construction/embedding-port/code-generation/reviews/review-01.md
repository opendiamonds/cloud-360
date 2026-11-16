## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-20T08:49:01Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/embedding_port.py > FastembedAdapter._load_model（`TextEmbedding(model_name=self._selection.model_id)`）；LOCAL-DEV.md > 「第三個：本機向量檢索的 fastembed」下載來源一條 | 本機向量檢索路徑傳給 fastembed 的名稱是裸字串 `multilingual-e5-large`（`DEFAULT_FASTEMBED_MODEL`，`:74`）。我所知 fastembed 的支援清單用的是 `intfloat/multilingual-e5-large`，且 ONNX 權重約 2 GB 而非文件寫的「約 1 GB」。我無法在本機核對（未安裝 fastembed，且本審查不得執行安裝），所以這是未驗證的風險而非已證實的缺陷。若名稱確實不被接受，`LOCAL-DEV.md` 叫開發者本機走 fastembed 的整條路徑會在第一次 embed 以「模型載入失敗」收場，而本單元自認該路徑 CI 零覆蓋，沒有任何閘門會先攔下。 | 在拋棄式 venv 裝 `fastembed>=0.7,<0.8`，實測 `TextEmbedding(model_name="multilingual-e5-large")` 能否載入，並查實際權重大小。名稱不被接受就改 `DEFAULT_FASTEMBED_MODEL` 與 `MEMORY_RECORD_EMBEDDING_MODELS` 的對應（兩者須同步，現有雙向測試會要求）；大小與文件不符就同步改 `LOCAL-DEV.md:75` 與 `embedding_port.py:654` 的 docstring。無法當輪驗證則把這兩項在 `LOCAL-DEV.md` 本文標為未驗證，不要只放在 code-summary。 | New |
| R-02 | Minor | LOCAL-DEV.md:10 與 :30 | 本輪把 `:30` 標題改為「三個」，但同一節的 `:10` 導言仍寫「有兩個依賴不在任何依賴宣告檔裡」，是這次編輯新造的矛盾。另外表格（`:23`、`:24`）本身已把 pgvector 與 Redis 列為不在 requirements 的硬依賴，「三個」這個數字本身也對不上。「第三個」小節沒有 H 編號，而 `:599` 另有一個 H3 指不同事物。 | 讓 `:10` 與 `:30` 說同一個數字，或改成不帶數字的說法（例如「以下幾個」），並替新小節取不與 `:599` 相撞的稱呼。 | New |
| R-03 | Minor | LOCAL-DEV.md:76 快取位置一條 | `FASTEMBED_CACHE_PATH` 與預設 `fastembed_cache` 目錄取自記憶，未在本機核對；code-summary 末尾有寫「未實地驗證」，但 LOCAL-DEV 本文把它寫成斷言。看 LOCAL-DEV 的開發者讀不到那段免責，若變數名不對，他們設了不會有任何作用，且沒有錯誤訊息。 | 驗證同上一列；驗證不了就在該條加一句「未實測，以 fastembed 實際行為為準」。 | New |

### 逐項核對（重點 a–e）

- (a) merge-blockers 19 項，本單元 0 項成立。第 13 項（intent-router 吞記憶讀取錯誤）落點是 `intent_routing.py`，本單元只提供 `embed` 與 `resolve_embedding_port`；第 18 項是 Redis 容量，與 embedding 無關；第 19 項的 OPENROUTER 守門不在本單元的 render-env 行。
- (b) 抽查的格皆成立：`main.py` 內 `configure_provider_env()` → `configure_embedding_env()` → … → `init_db()` 次序仍在，`ci.yml:175-176` 的驗證器步驟仍在，`docker-compose.deploy.yml:124` 為無 fallback，`render-env.sh:138` 與 `deploy/.env.example:136` 同步，`embedding_port.py:736` 的 `configure_embedding_env` 存在。
- (c) 見上三列。`LOCAL-DEV.md` 其餘 embedding 敘述（ollama 本機啟動會過但第一次 embed 連不上、localhost／IP／FQDN 啟動即拒）與 `_validate_ollama_endpoint` 實作吻合。
- (d) 後續單元（U13、U20、U21、U14）改動共用檔，但本單元的行仍在，判準未失效。
- (e) ADR-0006：network exposure 以 `_validate_ollama_endpoint` 拒 localhost、IP 字面值與含點的 FQDN，僅放行單段服務名，吻合；明文 HTTP 到同網段 ollama 的風險已在設計中具名。IAM、audit logging 對本單元不適用（無授權判定、無稽核寫入）。encryption 的明文傳輸取捨已是既有裁決。fastembed 路徑的供應鏈風險已寫入 LOCAL-DEV，但見上方 Major 對其前提的疑慮。

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 測試與驗證器 | 未執行 | 本審查禁止執行測試與腳本（會產生快取使收據無法登記）。結論僅依讀檔、grep 與 git diff。 |

### Summary

本單元程式與共用檔落點在後續單元改動後仍然成立，19 項必修無一落在本單元，ADR-0006 的 network exposure 限制實作正確。唯一需要處理的是本輪新補的 LOCAL-DEV 小節：它對 fastembed 的模型名、權重大小與快取變數的敘述都未經實測，且與同節導言的「兩個」互相矛盾。這些是文件與未驗證路徑的問題，不阻擋判定。
