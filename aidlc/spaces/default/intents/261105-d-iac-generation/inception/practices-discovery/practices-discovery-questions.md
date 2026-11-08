# Practices Discovery — 釐清問題（re-run）

> Stage: practices-discovery（Inception）· Depth: Standard · Scope: feature · Intent: `261105-d-iac-generation`
> 本輪為 **re-run**：`team.md` 五段已核可。只問草稿與三份盲評仍無法定案的項。
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。

## 已由既有 team.md／project.md／intent 定案、不重問

- Branch 命名 `<uploader>/<type>/<slug>`；commit／PR 中文 type（ADR-0010）
- 團隊預設 `skeleton: off`（逐案可開）
- 測試底線 A（RBAC allow/deny）／B（新 HTTP 用 TestClient）／C（前端資料形狀 e2e）；不引入前端單元測試框架
- Construction 與 Operations 連續、deploy-on-merge 至自有 staging
- 新模組走三層；純函式層不得 httpx／DB／`HTTPException`
- 平台不得代為 apply／direct production IaC；高風險操作須 plan＋impact＋rollback＋人工核准
- ADR-0006：IaC **generator** 落地後必須有 property-based tests（無模組時為 N/A，不是豁免）
- D1／D2／D3 各一 agent；UI 風格與 A／C Workspace 一致
- 規則 C 已定案：真 UI／資料形狀變更必須有 e2e——本輪不討論暫緩

## Sources

- [team] `aidlc/spaces/default/memory/team.md` 五段
- [project] `aidlc/spaces/default/memory/project.md`
- [codekb] `aidlc/spaces/default/codekb/cloud/`（Focused STALE merge）
- [draft] `team-practices.md`／`discovered-rules.md`／`evidence.md`
- [spoke] `contributions/aidlc-quality-agent.md`、`aidlc-developer-agent.md`、`aidlc-devsecops-agent.md`

## Q1. 本 intent 要不要先做一條薄的端到端骨架？

> 團隊預設不開。Walking skeleton＝先做一條能跑通全路徑的最小版本，用來證明元件接得上，再填真實功能。本輪會新增 IaC 產碼／掃描／Secret 與三個 agent，但仍是 FastAPI／React／既有 LangGraph 底座，不是新語言或新基礎設施。

A. 維持不開 — 第一個 Bolt 照常跑，不另開骨架儀式。
B. 本 intent 開啟 — 先做一條可產碼（或等價）的最小路徑並單獨 gate；不改團隊預設。
C. 現在不定 — 留給 delivery-planning 再決定。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q2. 第一個 D 柱 HTTP 端點的授權測試要多深？

> D1／D2／D3 權限種子已在矩陣裡；規則 A 只在「改種子」時觸發，規則 B 字母只要求 status＋欄位，可能只測 happy path 而漏 403。成本柱曾對第一個 C1 端點補過「有權 2xx／無權 403」。codekb 若寫「D 已比照 Q3」不可信——那是 C1 專屬定案。

A. D1／D2／D3 **任一**故事的第一個 HTTP 消費者落地時，即使種子未改，仍強制 allow／deny 雙向 TestClient（有權 → 2xx、無權 → 403）。
B. 不另立交叉規則；只在改 `role_permissions` 預設時走 A，新端點只滿足 B（status＋欄位）。
C. Not yet defined
X. Other (please specify)

[Answer]:A

## Q3. D2 靜態掃描的自動化落在哪裡？

> 現況 CI／相依對 checkov／tfsec／trivy／gitleaks 皆 0 命中。工具名不得未定案就寫進 Mandated。若日後引入外部 CLI，供應鏈（lockfile／image scan）也會變成風險面。

A. 本 intent 只要求 unittest 測「編排＋報告形狀」（工具／CLI 可 stub）；不新增 CI scan job。
B. 另增 CI job（**blocking**），工具於後續 ADR／實作點名；本站不預填工具名。
C. 另增 CI job（**report-only**），工具後續點名。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q4. D3 Secret 處理落地時，測試最低線？

> Contract 的值形 secret 掃描已能掃追蹤檔，但仍有通用／PEM／執行期洩漏面。產品路徑必須保證回應／log／artifact 不出現明文。

A. 強制負向測試＋redaction 突變驗證（注入明文樣式 → 輸出／log 不得出現該明文；拿掉遮罩 → 測試應紅）；contract 掃描作用域擴大另排、不阻塞這條。
B. 只做 example-based happy path；負向測試與掃描擴大都留待補清單。
C. Not yet defined
X. Other (please specify)

[Answer]:A

## Q5. D 柱程式怎麼擺、PBT 蓋到哪？

> 新模組三層已定案。成本柱先例是 `backend/cost/` 領域套件，不是扁平 `services/cost_router.py`。ADR-0006 點名的 PBT 落點是 **IaC generator**，不是 scanner／secret-handler——若要擴大必須本輪 Affirm（或新 ADR），不能假裝已有 ADR。

A. 領域套件（建議 `backend/iac/`）：router → service → 純函式；三 agent 同套件；檔名用領域語彙（禁止 `d1_*` story-id 前綴）。PBT **僅** generator（執行既有 ADR-0006）。
B. 同 A 的套件形狀，但本輪 Affirm：scanner 與／或 redactor 也列為 PBT 核心（寫進本輪 discovered-rules／後續 ADR）。
C. 扁平放 `backend/services/`，仍守三層與純函式禁令；PBT 僅 generator。
D. Not yet defined
X. Other (please specify)

[Answer]:B

## Q6. 三個 agent 與「只能手動」桶怎麼切？

> LLM 對話路徑是結構性盲區；TCMS 要求分桶。底座是否強制既有 `langgraph_runtime`＋OpenRouter（與 A／C 對齊）也需釘死。

A. 每個故事先有可離線斷言的決定性核心（D1 generator 含 PBT；D2 報告形狀；D3 redactor）；LLM 編排進手動／TCMS。三 agent 一律走 `langgraph_runtime`＋OpenRouter，禁止再增 Claude-SDK-only 路徑。
B. 允許首個 Bolt 以 agent 編排為主，純函式核心可延後；底座仍強制 `langgraph_runtime`。
C. Not yet defined
X. Other (please specify)

[Answer]:A

## Q7. 產品級「不得代 apply」要不要寫進 Forbidden？

> 既有規則管「人工高風險操作須核准」。產品若做出一鍵 apply，人工核准閘擋不住產品能力本身。

A. 升格 — 寫進本輪 `discovered-rules.md` Forbidden：D 柱 API／agent **不得**代使用者對雲端執行 apply／destroy；產出與掃描報告即可。Affirm 後進 `project.md`／team 層。
B. 不升格 — 留在 intent／scope 敘述，不進 Forbidden。
C. Not yet defined
X. Other (please specify)

[Answer]:A

## Q8. Testing methodology 標籤與 team.md 範例修復？

> Lead 草稿標 `Methodology: custom`（A／B／C＋PBT 疊加）與 Ordering「同 PR 齊備」——尚未 Affirm。另：現行 `team.md` commit 範例 code fence 為空；草稿已自 cost-finops 核可稿還原，promote 時可一併修回。

A. 採用 `custom`＋該 Ordering；promote 時一併寫回 commit 範例 fence。
B. 改標 `test-after`；仍寫回 commit 範例 fence。
C. 刪除 Methodology／Ordering 標註（維持既有 A／B／C 敘述即可）；仍寫回 commit 範例 fence。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Assumption Confirmation

本檔無新增 assumption 清單需確認（re-run 沿用既有 team.md；上列為裁定項）。

[Answer]: N/A — 無新增 assumption

## Consolidated Summary Confirmation

依你的回答整理如下：

- **Walking skeleton**：本 intent 維持不開；第一個 Bolt 照常跑。[Q1]=A
- **D 授權測試**：D1／D2／D3 任一故事的第一個 HTTP 消費者，即使種子未改，仍強制 allow／deny 雙向 TestClient（2xx／403）。[Q2]=A
- **D2 掃描自動化**：本 intent 只要求 unittest 測編排＋報告形狀（CLI 可 stub）；不新增 CI scan job。[Q3]=A
- **D3 Secret 測試**：強制負向測試＋redaction 突變驗證；contract 掃描擴大另排。[Q4]=A
- **模組／PBT**：領域套件 `backend/iac/`（三層＋三 agent；禁 `d1_*` 前綴）；本輪 Affirm scanner 與／或 redactor 亦為 PBT 核心（不僅 generator）。[Q5]=B
- **Agent 分桶**：每故事先有決定性核心；LLM 編排進手動／TCMS；一律 `langgraph_runtime`＋OpenRouter。[Q6]=A
- **Forbidden**：D 柱 API／agent 不得代 apply／destroy；產出與掃描報告即可。[Q7]=A
- **Methodology**：採用 `custom`＋同 PR Ordering；promote 時寫回 team.md commit 範例 fence。[Q8]=A

Does this all look correct before I integrate the practices artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
