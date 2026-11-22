## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-04 | Still applies | Minor | backend/services/embedding_port.py:669 仍寫「首次使用會從 HuggingFace 下載約 1GB 權重」，LOCAL-DEV.md:76 為約 2.24 GB，兩處數字仍不一致。位置描述正確，本輪刻意不修。 |
| R-05 | Still applies | Minor | LOCAL-DEV.md:704 仍寫「唯一寫下隱性前置條件（claude CLI 子行程、n8n webhook）」只列兩項，與 :10、:30 的「三個」矛盾。行號由 :675 平移為 :704 屬實（H7 小節插入 29 行）。本輪刻意不修。 |
| R-06 | Still applies | Minor | test_embedding_port.py:477 的 test_fastembed_registry_names_cover_every_legal_identity 仍只鎖鍵集合；ci.yml 與 requirements.txt 對 fastembed 零命中，CI 無實際載入檢查。已知且已告知的缺口，本輪刻意不修。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

- 四支本單元檔案的位元組：embedding_port.py、test_embedding_port.py、main.py、validate_embedding_provider_value.py 的 sha256 與最新收據 reviewed-source-c8b1b94a746d.tsv 逐字相同；git diff HEAD 對這四支皆無差異。宣稱成立。
- 共用檔 git diff HEAD 逐 hunk 核對（六支皆與收據不同）：
  - ci.yml：七個 hunk 全部在 :328 之後（PostgreSQL job 與 step 改名），本單元的 Validate embedding provider values step 仍在 :175-176，位於 repo-contract job 內，未觸及。
  - LOCAL-DEV.md：單一 hunk（新增於 :273 起，+29 行的 H7 小節）。fastembed 小節 :67-79 與 EMBEDDING_TIMEOUT_SEC（現 :431）未觸及。
  - backend/.env.example：單一 hunk +9 行（MEMORY_DB_PASSWORD），EMBEDDING_TIMEOUT_SEC 現 :202，值為 10，未變。
  - deploy/.env.example：單一 hunk +7 行，EMBEDDING_TIMEOUT_SEC 現 :143，未變。
  - deploy/docker-compose.deploy.yml：單一 hunk 在 :124 之後插入，EMBEDDING_TIMEOUT_SEC: ${EMBEDDING_TIMEOUT_SEC} 仍在 :124，無 fallback。
  - deploy/render-env.sh：四個 hunk 皆為 MEMORY_DB_PASSWORD 相關；EMBEDDING_TIMEOUT_SEC=10 現 :146，未變。
  - 結論：「本單元負責的行只平移、內容沒變」成立。
- main.py 呼叫順序實測：configure_provider_env() :60，configure_embedding_env() :65，init_db() :92，順序成立。
- 測試（scratchpad 的 rsync 副本，含 frontend，PYTHONDONTWRITEBYTECODE=1、-B、HYPOTHESIS_STORAGE_DIRECTORY 導向 scratchpad）：tests.test_embedding_port 為 Ran 32 tests、OK；全套為 Ran 1372 tests、OK (skipped=3)、exit 0。與宣稱完全相同。副本與 hyp 目錄已刪除。
- validator：validate_env_contract.py exit 0；validate_embedding_provider_value.py exit 0（3 份設定來源）；validate_repo_contract.py 因副本沒有 .git 而無法在副本跑（git ls-files 退出 128，屬環境因素），改在 repo 根以 -B 唯讀執行，exit 0。
- Step 12 五格皆有證據：共用檔重驗（上列 diff 與 sha256）、回歸（上列實跑）、三項 Accepted risk 現況（皆以 grep 行號確認）、勾選重設（計畫 grep 計得已勾 43、未勾 0；git diff HEAD 對計畫只增 10 行 Step 12 一節）、收尾（code-summary 末節存在，含 date -u 時間戳）。
- 次要觀察（不構成發現）：code-summary 稱 ci.yml 相對收據有五個 hunk，相對 HEAD 的 git diff 為七個；差異來自比較基準不同（收據版本 vs HEAD），結論不變。

### Summary

本輪為回歸驗證，本單元四支檔案與收據位元組相同，六支共用檔的全部 hunk 皆屬其他單元（記憶專用角色、tests_pg step 命名），沒有一個觸及本單元負責的行；測試與 validator 結果我獨立重跑，與宣稱完全一致（32 與 1372 OK）。前輪 R-04、R-05、R-06 三項 Minor 依指示未修，位置描述均正確，仍然適用。Critical 0、Major 0、Minor 3（皆為前輪遺留），新發現 0，判定 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | backend/services/embedding_port.py > FastembedAdapter._load_model（`TextEmbedding(model_name=self._selection.model_id)`）；LOCAL-DEV.md > 「第三個：本機向量檢索的 fastembed」下載來源一條 | 本機向量檢索路徑傳給 fastembed 的名稱是裸字串 `multilingual-e5-large`（`DEFAULT_FASTEMBED_MODEL`，`:74`）。我所知 fastembed 的支援清單用的是 `intfloat/multilingual-e5-large`，且 ONNX 權重約 2 GB 而非文件寫的「約 1 GB」。我無法在本機核對（未安裝 fastembed，且本審查不得執行安裝），所以這是未驗證的風險而非已證實的缺陷。若名稱確實不被接受，`LOCAL-DEV.md` 叫開發者本機走 fastembed 的整條路徑會在第一次 embed 以「模型載入失敗」收場，而本單元自認該路徑 CI 零覆蓋，沒有任何閘門會先攔下。 | 在拋棄式 venv 裝 `fastembed>=0.7,<0.8`，實測 `TextEmbedding(model_name="multilingual-e5-large")` 能否載入，並查實際權重大小。名稱不被接受就改 `DEFAULT_FASTEMBED_MODEL` 與 `MEMORY_RECORD_EMBEDDING_MODELS` 的對應（兩者須同步，現有雙向測試會要求）；大小與文件不符就同步改 `LOCAL-DEV.md:75` 與 `embedding_port.py:654` 的 docstring。無法當輪驗證則把這兩項在 `LOCAL-DEV.md` 本文標為未驗證，不要只放在 code-summary。 | Resolved (reviewer) |
| R-02 | Minor | LOCAL-DEV.md:10 與 :30 | 本輪把 `:30` 標題改為「三個」，但同一節的 `:10` 導言仍寫「有兩個依賴不在任何依賴宣告檔裡」，是這次編輯新造的矛盾。另外表格（`:23`、`:24`）本身已把 pgvector 與 Redis 列為不在 requirements 的硬依賴，「三個」這個數字本身也對不上。「第三個」小節沒有 H 編號，而 `:599` 另有一個 H3 指不同事物。 | 讓 `:10` 與 `:30` 說同一個數字，或改成不帶數字的說法（例如「以下幾個」），並替新小節取不與 `:599` 相撞的稱呼。 | Resolved (reviewer) |
| R-03 | Minor | LOCAL-DEV.md:76 快取位置一條 | `FASTEMBED_CACHE_PATH` 與預設 `fastembed_cache` 目錄取自記憶，未在本機核對；code-summary 末尾有寫「未實地驗證」，但 LOCAL-DEV 本文把它寫成斷言。看 LOCAL-DEV 的開發者讀不到那段免責，若變數名不對，他們設了不會有任何作用，且沒有錯誤訊息。 | 驗證同上一列；驗證不了就在該條加一句「未實測，以 fastembed 實際行為為準」。 | Resolved (reviewer) |
| R-04 | Minor | backend/services/embedding_port.py > `FastembedAdapter` 類別 docstring（約 `:666`） | docstring 仍寫「從 HuggingFace 下載約 1GB 權重」。這次修正已實測為約 2.24 GB，並已更正 `LOCAL-DEV.md`，但程式碼內的敘述沒有同步，兩處數字不一致。 | 把 docstring 的大小改為約 2.24 GB，並與 `LOCAL-DEV.md:76` 的說法一致。 | New |
| R-05 | Minor | LOCAL-DEV.md:675 | 該句仍寫隱性前置條件只有兩個（`claude` CLI、n8n webhook），與同檔 `:10`、`:30` 的「三個」互相矛盾。code-summary 已承認並刻意未改。 | 把該句改為與前面一致的說法，或改成不帶數字的描述。 | New |
| R-06 | Minor | backend/tests/test_embedding_port.py > `test_fastembed_registry_names_cover_every_legal_identity` | 這個測試只鎖住鍵集合等於合法身分，無法驗證 fastembed 套件真的認得登錄名（套件刻意不在 requirements）。fastembed 升版改名時，只會在本機首次使用以「模型載入失敗」大聲失敗，這一點 code-summary 已如實記載，屬已知且有告知的缺口。 | 不需要現在動作；若日後 CI 願意裝可選依賴，再加一道實際載入檢查。 | New |

> R-04 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round
