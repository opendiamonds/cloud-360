## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-04 | Still applies | Minor | backend/services/embedding_port.py 第 669 行 FastembedAdapter docstring 仍寫約 1GB，LOCAL-DEV.md 第 76 行已是約 2.24 GB。本單元自上次審查後無程式改動，故未變；僅文字不一致，不影響執行。 |
| R-05 | Still applies | Minor | LOCAL-DEV.md 第 704 行（原 675 行，已平移）仍寫隱性前置條件只有兩個，與同檔第 10 行及第 30 行的三個互相矛盾。code-summary 已承認並刻意未改。 |
| R-06 | Still applies | Minor | 登錄名測試仍只鎖鍵集合，無法驗證 fastembed 套件認得該名稱。屬已告知的缺口，無需動作。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum 對收據 10 列獨立重算 | 10 同、0 變 | 與 reviewed-source-d98abce18e4a.tsv 逐列一致，本單元的程式與設定檔自上次 READY 後未動。 |
| git diff HEAD 對 code-generation-plan.md | 零差異 | 勾選回復與 HEAD 版一致；實測 43 個已勾、0 個未勾，無需再判定未勾理由。 |
| code-summary.md 新節核對 | 屬實 | 新節所述收據 10 同、43 勾／0 未勾均與重算結果相符；檔尾差異僅為追加該節。 |
| 跨單元事實 | 未重複報告 | membership-service 的 C3 已知，不屬本單元。commit 33deb2e 與 merge-blockers 附加列未觸及本單元收據所列檔案。 |

### Summary

本單元程式與設定自上次 READY 審查後逐位元未變，計畫勾選與 HEAD 一致，code-summary 新節屬實。三項先前 Minor 仍開放但皆為文字或已知缺口，無新發現，不阻擋。

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
