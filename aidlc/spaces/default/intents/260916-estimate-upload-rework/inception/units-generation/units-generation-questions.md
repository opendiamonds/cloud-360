# Units Generation 問答：C1 估價表上傳

**本站只決定拓樸，不決定實作順序。** 「先做哪個」「哪條是關鍵路徑」「value-first 怎麼排」全部屬於下一站 delivery-planning 的經濟判斷，本站不問也不答（stage 檔開頭的 NOTE 明文禁止）。本站問的是：單元怎麼切、誰能依賴誰、哪些邊界需要正式契約。

## Sources

- **[S1]** `domain-design/components.md`：十一個元件（九個新建或改造、兩個既有不改動）、八個實體、十三條相依邊，有向無環。
- **[S2]** `domain-design/decisions.md` ADR-006：新解析器落在 `backend/cost/estimate_parser.py`，維持 `main.py:13` 的單一進入邊（C6）。這條約束限制了單元不能把 `backend/cost/` 拆成多個對外套件。
- **[S3]** `requirements.md` FR9：退場面涵蓋 9 個端點、4 張資料表（DDL 雙軌，`database.py::_ensure_cost_schema()` 與 `schema_rbac.sql` 須同時處理）、Playwright 三模組加兩支 spike、`warm_aws_pricing_cache.py` 修正、e2e 回歸段落、`openapi.json` 與型別重產、孤兒 prompt 檔。
- **[S4]** `requirements.md` FR11：憑證管線重建涉及 `.github/workflows/deploy.yml`、`deploy/render-env.sh`、`deploy/docker-compose.deploy.yml`，外加 `validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS` 調整。ADR-0018 §6 已標示後者為高風險。
- **[S5]** `requirements.md` FR5.10：查價端點的憑證缺漏或呼叫失敗時必須降級，**不得使建議產生流程失敗**。這意味著建議能力在沒有查價工具時仍可運作。
- **[S6]** `intent-backlog.md`：PU-3（退場）與 PU-4（新頁面）**不得分批部署**——本專案是 deploy-on-merge，分兩批會讓 `/cost` 在中間有一次部署是死的。此為部署約束，不是相依邊。
- **[S7]** codekb `architecture.md`：部署拓樸為單一 FastAPI process 加單一 React SPA，同一個 docker-compose，合併進 `ut` 即觸發部署。**沒有任何單元能獨立部署。**
- **[S8]** `approval-handoff` AH-2：有兩人以上可平行作業；ideation 已認定解析器、退場、LangGraph 骨架三項技術工作可同時起跑。
- **[S9]** `org.md` `## Way of Working`：Construction 的 worktree base 與合併目標皆為 `ut`，**squash-merge**，一個 Bolt 一個 commit。兩個單元若改到同一個檔案，會在 worktree 合併時真實衝突。

## 草案（供作答時對照，非既定結論）

| ID | 單元 | kind | 直接相依 | 承載 |
|---|---|---|---|---|
| U1 | `estimate-parser` | library | 無 | EstimateParser、EstimateValidator（純函式、PBT、CI 邊界腳本） |
| U2 | `estimate-intake-api` | service | U1 | EstimateIntakeService、EstimateAccessControl、EstimateAuditLog 與五個實體的 schema |
| U3 | `legacy-cost-retirement` | service | 無 | FR9 的退場與工具鏈修正 |
| U4 | `credential-pipeline` | packaging | 無 | FR11 憑證管線與 repo contract 調整 |
| U5 | `pricing-lookup-port` | library | U4 | PricingLookup |
| U6 | `langgraph-runtime` | library | 無 | LangGraph 執行骨架與 OpenRouter 接入 |
| U7 | `cost-advice-agent` | service | U6、U2 | CostAdviceAgent 三類建議、AdviceOrchestrator 背景工作與 SSE |
| U8 | `estimate-workspace-ui` | ui | U2 | 上傳、明細、檢查結果、歷史抽屜、分享 |
| U9 | `advice-presentation-ui` | ui | U8、U7 | 建議區、SSE 訂閱、進度指示 |

---

## Q1 單元邊界策略

草案採**混合**：新建能力依 [S1] 的元件群組切，退場（U3）與憑證管線（U4）各自獨立成單元。後兩者不對應任何元件，但都是實打實的工作量且各有獨立的驗證方式。

- **A.** 混合（如草案）——新建能力按元件群組，退場與憑證管線獨立成單元
- **B.** 全部按元件群組——退場工作分散進各個承接它的新單元（例如舊 cost 端點的移除併進 `estimate-intake-api`）
- **C.** 按能力（CAP-1…CAP-11）切——每個能力一個單元
- **D.** 按交付層切——解析層、API 層、UI 層、基礎設施層各一個單元
- **X.** Other (please specify)

[Answer]: A — 混合（如草案）：新建能力按元件群組，退場與憑證管線獨立成單元

---

## Q2 單元粒度

草案為 9 個單元。粒度直接影響 worktree 數量與 [S9] 的合併衝突面。

- **A.** 如草案的 9 個（中等粒度）
- **B.** 更粗，5 個左右——合併 U1+U2（解析與 API 一起）、U6+U7（框架與 agent 一起）、U8+U9（整頁 UI 一起）
- **C.** 更細，11 個以上——每個元件一個單元，`EstimateValidator` 與 `EstimateParser` 分開、`AdviceOrchestrator` 與 `CostAdviceAgent` 分開
- **X.** Other (please specify)

[Answer]: A — 9 個單元（中等粒度）

---

## Q3 可降級的元件相依，是否要成為單元相依

[S1] 記載 `CostAdviceAgent → PricingLookup`，但 [S5] 規定查價失敗時必須降級、不得讓建議流程失敗。這代表 `cost-advice-agent` **技術上可以在沒有查價工具的情況下先完成**。

若把它設為單元相依，`credential-pipeline`（U4，含 [S4] 標為高風險的 repo contract 調整）就會擋在建議能力前面。若不設，兩者可各自獨立推進，查價工具後掛。

- **A.** 不設為單元相依——可降級的元件邊不升格為單元邊，`cost-advice-agent` 的相依為 U6、U2 兩者
- **B.** 設為單元相依——單元圖嚴格鏡射元件圖，`cost-advice-agent` 相依 U6、U2、U5
- **C.** 不設相依，但在 `cost-advice-agent` 的實作註記中明列「查價工具接上之前，建議文字不得出現任何現價宣稱」
- **X.** Other (please specify)

[Answer]: A — 不設為單元相依；`cost-advice-agent` 只相依 LangGraph 骨架與上傳 API。查價為可後掛的降級能力

---

## Q4 UI 是否拆成兩個單元

草案把「上傳與明細」（U8）和「建議呈現」（U9）拆開，讓明細路徑不必等建議路徑。

代價是兩個單元會改到同一批前端檔案——以 [S9] 的 squash-merge worktree 模式，這是真實的合併衝突面而非理論風險。

- **A.** 拆成兩個（如草案）——接受合併衝突面，換取兩條路徑的拓樸獨立
- **B.** 合併為一個 `estimate-workspace-ui`，相依 U2 與 U7——UI 只做一次，但整頁要等建議後端完成
- **C.** 拆成兩個，但以檔案邊界切乾淨：U9 只新增獨立的建議區元件檔，不修改 U8 產出的任何檔案
- **X.** Other (please specify)

[Answer]: A — 拆成兩個 UI 單元；接受 squash-merge worktree 下的合併衝突面，換取拓樸獨立

---

## Q5 退場工作是一個單元還是拆開

[S3] 的退場面橫跨後端模組、資料庫 DDL（雙軌）、Playwright 相依、CI 腳本、e2e 測試與 OpenAPI 重產。草案把它們合成一個 `legacy-cost-retirement`。

- **A.** 一個單元——退場是一件事，分開反而讓「刪乾淨了沒」難以驗證
- **B.** 拆兩個——「後端與資料庫退場」與「工具鏈及測試修正」（`warm_aws_pricing_cache.py`、e2e、OpenAPI、CI 腳本）
- **C.** 拆三個——後端模組、資料庫 DDL、工具鏈與測試
- **X.** Other (please specify)

[Answer]: A — 退場為單一單元 `legacy-cost-retirement`

---

## Q6 共同部署約束

[S6] 已確認 U3（退場）與 U8（新頁面）不得分批部署。本題問的是**還有沒有別的**必須同批。

以 [S7] 的單一 process 部署與 deploy-on-merge，每一次合併都是一次真實部署，任何「中間狀態」都會真的被使用者看到。

- **A.** 只有 U3 與 U8 這一組
- **B.** 另加 U4 與 U5——憑證管線與查價 Port 同批，避免部署出「有憑證但沒人用」或「要查價但沒憑證」的中間態
- **C.** 另加 U2 與 U3——新端點與舊端點同批，避免兩套端點並存
- **D.** B 與 C 皆是
- **X.** Other (please specify)

[Answer]: A — 共同部署約束只有一組：`legacy-cost-retirement` 與 `estimate-workspace-ui`

---

## Q7 單元間契約的正式化範圍

下一站是 contract-design。本題決定它要處理哪些邊界。

- **A.** 對外 HTTP API ＋ SSE 事件格式 ＋ 解析器輸出結構三者都正式化——解析器輸出是 U1 與 U2 的交界，也是 U7 送進 LLM 的內容
- **B.** 只正式化對外 HTTP API（含 SSE）——解析器輸出屬單一套件內的 Python 型別，靠型別註記與測試即可
- **C.** A 再加上 PricingLookup 的查價結果結構——它是 U5 與 U7 的交界
- **X.** Other (please specify)

[Answer]: A — 正式化對外 HTTP API、SSE 事件格式，以及解析器輸出結構

---

## Consolidated Summary Confirmation

**Looks correct** 前請核對下列彙整。

**邊界與粒度（Q1=A、Q2=A）**：九個單元，混合策略——新建能力依元件群組，退場與憑證管線各自獨立。

| ID | 單元 | kind | 直接相依 |
|---|---|---|---|
| U1 | `estimate-parser` | library | 無 |
| U2 | `estimate-intake-api` | service | U1 |
| U3 | `legacy-cost-retirement` | service | 無 |
| U4 | `credential-pipeline` | packaging | 無 |
| U5 | `pricing-lookup-port` | library | U4 |
| U6 | `langgraph-runtime` | library | 無 |
| U7 | `cost-advice-agent` | service | U6、U2（**不含 U5**） |
| U8 | `estimate-workspace-ui` | ui | U2 |
| U9 | `advice-presentation-ui` | ui | U8、U7 |

**Q3=A 的後果**：元件圖上有 `CostAdviceAgent → PricingLookup`，但單元圖**不**設這條邊。查價失敗本就必須降級（FR5.10），建議能力可先完成；U4／U5 可獨立推進後掛。U7 實作時仍須遵守「查價未接上或失敗時，建議文字不得假裝有現價」——這是行為約束，不是單元相依。

**Q4=A 的後果**：兩個 UI 單元會改到同一批前端檔案，在 squash-merge worktree 下是真實合併衝突面。換得的是「明細路徑不必等建議後端」的拓樸獨立。

**Q5=A、Q6=A**：退場整包一個單元；共同部署約束**只有** U3 與 U8（舊 `/cost` 退場與新上傳／明細頁必須同批，避免中間一次部署讓路徑是死的）。U9 不在此約束內——建議區後補時 `/cost` 已有可用的上傳與明細。

**Q7=A**：下一站 contract-design 須正式化 (1) 對外 HTTP API (2) SSE 事件格式 (3) 解析器輸出結構（U1↔U2 交界，也是送進 LLM 的內容形狀）。

**本站不決定實作順序**——DAG 只描述「誰能依賴誰」；value-first／關鍵路徑屬 delivery-planning。

[Answer]: Looks correct

九單元草案確認，照此產生 unit-of-work 四份產出。
