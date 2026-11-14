## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U6 embedding-port 的設計大致自洽：六個值物件的三問可指名，30 條規則的來源與類別清楚，四個 ADR-0006 面向與 PBT 都有落點，且 `rules.md` 的 BR 與 `services/embedding_port.py` 的實作逐項對得上。主要問題有兩個：（一）設計對 `ModelId` 值域同時說「封閉三值」與「開放」，已落地的程式選了封閉對應表，交接事項 `H-E1` 仍建議 U5 依「開放」設計，兩邊不一致，程式那一側才正確；（二）K-01 對 `OLLAMA_BASE_URL` 的「主機名須為 compose 內部服務名」約束，設計的網路暴露一格拿它當緩解，卻沒有任何 BR 把它變成可驗證的規則（BR1.3 只管非空）。Major 兩項，未超過 2 項，判 READY；其餘為 Minor。前次 review-01 的 R-01、R-02 已在凍結產出中處置，本次不重提。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/embedding-port/functional-design/entities.md` ModelId 的 `entity_constraints`（第 166 行）、`rules.md` BR3.5、`functional-spec.md` §九 A-E2、`entities.md` §三 H-E1；對照 `backend/services/embedding_port.py` `PROVIDER_LEGAL_MODEL_IDS` 與 `resolve_provider_selection` 結尾的 `model_id not in legal_for_provider` 檢查 | 設計對 `ModelId` 值域自相矛盾。`allowed_values: [bge-m3, multilingual-e5-large, stub-v1]` 與 BR3.1「預設值域」並列，但第 166 行寫「本值域在那兩格是開放的：設了別的 1024 維模型，`model_id()` 就該回那個新值」，A-E2 把「維持可設定」當假設，H-E1 據此建議 U5 的 schema「不應寫成封閉枚舉」。已落地的程式卻是封閉的：`OLLAMA_EMBED_MODEL` 或 `FASTEMBED_MODEL` 設成預設以外的任何值，啟動直接 `ValueError`（`PROVIDER_LEGAL_MODEL_IDS` 每個提供者只有一個合法值）。以實際行為判斷，程式是對的：開放值域加上 BR3.3 只驗「預設設定」，會讓執行期出現 S 之外的 `embeddingModel` 而無任何測試察覺，與 BR3.3 想防的漂移同形。問題在設計沒有承認這個收斂，下游（U5 的 schema 約束形式、U8 的過濾）仍會讀到「開放」這個已被推翻的前提。 | 以對齊修正（明記非本站新定案、不回改上游）更正 `entities.md` 第 166 行、BR3.5 的理由、A-E2 與 H-E1：值域為封閉，換模型須同步更新對應表與既有列的遷移。H-E1 對 U5 的建議（是否仍不寫封閉 CHECK）須在此一併重新判定並寫明理由。 | New |
| R-02 | Major | `construction/embedding-port/functional-design/functional-spec.md` §七 Network exposure 與 Encryption 兩列、`rules.md` BR1.3；對照 `backend/services/embedding_port.py` `_validate_ollama_endpoint` | 設計的網路暴露緩解建立在 K-01 的「`OLLAMA_BASE_URL` 主機名須為 compose 內部服務名」上，並在 Encryption 一格明說「緩解是網段隔離」。但全部 30 條 BR 沒有一條要求或驗證該約束：BR1.3 只規定 `ollama` 時 URL 必填，W1 第 3 步同。結果是設計層面 `OLLAMA_BASE_URL=http://example.com` 或 `http://localhost:11434` 都合規，而記憶文字會以明文 HTTP 送出去。程式後來加了 `_validate_ollama_endpoint`（拒 localhost、IP 字面值、FQDN），顯示缺口真實存在，只是靠後續階段補上，沒有回到本站規則。 | 在 `rules.md` 新增一條 validation 規則（或擴充 BR1.3），規定主機名須為單一 DNS label 的服務名、拒絕 localhost／IP／FQDN，並同步 `functional-spec.md` W1 與 §七。或明確在交接事項中註記該約束由哪個站的哪份產出承接，且寫明其可驗證形式。 | New |
| R-03 | Minor | `functional-spec.md` W2、`rules.md` BR2.x | 設計沒有任何一條規則限制 `ollama` 呼叫的逾時，也沒規定超長輸入的處置。BR2.6 只說不重試。W2 第 3 步在服務掛住（連線接受但不回應）時可無限期阻塞，且 U8 的寫入路徑是同步呼叫。程式另外加了 `EMBEDDING_TIMEOUT_SEC` 與依提供者字元上限截斷（`PROVIDER_CONTEXT_LIMIT_CHARS`），並以 WARN 記錄，這兩項行為都屬於可觀察的契約（截斷會靜默降低檢索品質），設計卻未宣告。 | 在規則中補入逾時上界（具名常數、逾時歸入 `EmbeddingProviderUnavailable`）與超長輸入的處置（截斷並 WARN，或拒絕），並說明對 P4（分批不變性）的影響。 | New |
| R-04 | Minor | `functional-spec.md` §二 狀態機與其下的「四個狀態，三條說明」 | 圖中有六個方框（未解析、啟動失敗、已解析／無 Port、已解析／有 Port、Port 已就緒、Port 不可用），文字卻說「四個狀態」。且「Port 已就緒」被標為終態，但實際上就緒之後 ollama 隨時可能停掉，下一次 `embed` 會拋 `EmbeddingProviderUnavailable`；圖只畫了 Port 不可用到再試的回路，沒有就緒到不可用的轉移，與說明第 2 點「下次呼叫可再試」也互相矛盾。 | 把「Port 已就緒」改為非終態，補上就緒到不可用的轉移，並更正狀態數。 | New |
| R-05 | Minor | `rules.md` BR1.1、`entities.md` EmbeddingProviderName；對照 `embedding_port.py` `resolve_provider_selection` 開頭 | 設計規定值「須在 {ollama, fastembed, fulltext, stub} 內」，未說明大小寫與前後空白。程式以 `.strip().lower()` 正規化，因此 `OLLAMA` 與 ` ollama ` 都被接受，而 `deploy/render-env.sh` 寫出的值若帶大寫，也能通過；此行為沒有被規則承載，也沒有測試性質對應。 | 在 BR1.1 明寫正規化規則（或明寫嚴格比對），使行為可被斷言。 | New |
| R-06 | Minor | `rules.md` BR3.3、`functional-spec.md` W4、§九 OQ-E1；對照 `embedding_port.py` `MEMORY_RECORD_EMBEDDING_MODELS` | BR3.3 的 S 側（`embeddingModel` 合法值集合）在設計中沒有擁有者。設計把 S 描述為「資料層認得的集合」，並把 schema 約束形式留給 U5，但 U6 的程式實際把 S 寫成本模組內的字面常數，等於在 U5 落地前先立了一份副本；U5 之後會有第三份（schema 或 U5 常數）。這違反 `team.md` 的「單一真實來源」：新增第二份副本的同一個 PR 須有鎖住兩者一致的測試，而該測試目前只鎖 U6 內部的 I 與 S。 | 在設計中指名 S 的唯一擁有者（U5 或 U6），並在 H-E1 寫明 U5 落地時須有測試鎖住 schema 側與此常數一致。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀取檔案（`rules.md`、`entities.md`、`functional-spec.md`、`traceability.json`、`reviews/review-01.md`） | 完成 | 規則 id BR1.1 至 BR7.2 共 30 條、群組 7 個與 `functional-spec.md` §六 的計數一致；`traceability.json` 三個 AC 的 `Deferred`／`N/A` 處置與 story map 對 US4.1 的三單元共享一致 |
| 設計對照 `backend/services/embedding_port.py`（唯讀） | 已抽查 | BR1.4、BR1.5、BR2.4、BR2.5、BR2.6、BR3.5、BR3.6、BR4.1 至 BR4.4、BR6.1、BR6.2 與程式相符；矛盾處見 R-01 至 R-06 |
| 測試、lint、建置 | 未執行 | 依 brief 禁止產生快取或寫檔 |
