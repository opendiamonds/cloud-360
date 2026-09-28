# 需求規格：C1 成本估算改版（上傳估價表）

> Intent `260916-estimate-upload-rework`｜階段 inception / requirements-analysis｜深度 Standard
> 權威描述（`project-description` 工具逐字）：「C1 成本估算改版：改掉現行 agent 框架；使用者直接上傳 AWS／Azure／GCP 三朵雲的官方估價表，由 agent 解析後給成本建議」
> `FR{n}` 與 `NFR{n}` 為永久追溯鍵，下游階段必須原樣保留，不得重新編號或改以散文指涉。

## 意圖分析

使用者要達成的目標不是「換一種取價方式」，而是**反轉估價的真實來源**。

現行架構由系統自動向雲端公開價目端點取價，再據以產生估價。這條路徑產出的是**目錄價**——不含 CUD、RI、Savings Plan 等客戶專屬折扣，因此與實際帳單之間存在系統性落差，而這個落差無法靠改善取價精度消除。使用者上傳的官方估價表已經包含這些折扣，是更接近帳單的真相。

因此本次改版的核心價值是：**讓系統處理它真正有優勢的事（比對、檢查、建議），而把「價格是多少」這件事交還給已經握有正確答案的使用者。** agent 的職責從「算出價格」變成「看懂使用者給的價格並指出問題」。

次要目標是 agent 框架由 `claude-agent-sdk` 遷移至 LangGraph，本期僅涵蓋成本 agent（IC-12），其餘五個 agent 模組留待後續 intent。

### 與現況的落差

reverse-engineering 確認既有 C1 是完整可運行的功能域（`backend/cost/` 18 支 Python、6,382 行、9 個 HTTP operations、4 張資料表、`/cost` 前端頁、17 支後端測試）。本次不是新建，是**替換**，因此需求必須同時涵蓋新建與退場兩面。

---

## 功能需求

### FR1 — 估價表上傳

- **FR1.1** 系統須提供上傳介面，接受 AWS、Azure、GCP 三朵雲的官方估價表匯出檔。
- **FR1.2** 每朵雲只支援一種主格式：AWS 為 CSV、Azure 為 XLSX、GCP 為 CSV（FE-1）。
- **FR1.3** 單一檔案大小上限 5 MB，單次上傳最多 3 檔。
- **FR1.4** 只接受 `.csv` 與 `.xlsx` 副檔名，且須驗證檔案內容的魔數與副檔名相符；不符者拒絕並說明原因。
- **FR1.5** 系統須依檔案標頭欄位自動判定所屬雲別；判定不出來時才要求使用者指定，不得逕自拒絕。
- **FR1.6** 原始檔案在解析完成後即丟棄，不落地保存（FE-2）。

### FR2 — 解析

- **FR2.1** 解析器須自估價表擷取逐項資料：品項、規格、數量、金額，以及該表的總額與幣別。
- **FR2.2** 解析採寬鬆策略：能解析的列照常呈現，無法辨識的列須保留其原始文字並標示為「無法辨識」，不得整份失敗（FE-4）。**「無法辨識」的判定為：該列的金額或數量無法解析為數值。**品項名稱或規格文字缺漏但金額與數量完好者，不計入無法辨識——它仍可參與 FR4.3 的總額對帳。
- **FR2.3** 解析器須為純函式——模組內不得 import `httpx`、不得出現 DB session 型別、不得 raise `HTTPException`。ADR-0017 §2 將原 `cost_calculator` 的純函式約束改錨至此。**可執行檢查沿用 `scripts/validate_cost_calculator_boundary.py` 現行的判準形式**：以正規式比對模組內的 import 敘述，命中 `httpx`、`requests`、`sqlalchemy`、`fastapi` 任一即失敗（FR9.6 只改目標路徑，不改判準）。此判準涵蓋上述三項禁令——`sqlalchemy` 涵蓋 DB session，`fastapi` 涵蓋 `HTTPException`。
- **FR2.4** 解析器須受 property-based test 覆蓋（ADR-0006 hard constraint，隨純函式層一併移轉）。

### FR3 — 明細呈現

- **FR3.1** UI 須顯示完整逐項明細（品項、規格、數量、金額）加上總額（SD-2）。
- **FR3.2** 無法辨識的列須在明細中可見並明確標示，不得隱藏。
- **FR3.3** 新頁面沿用 `/cost` 路徑；`frontend/src/App.tsx:24` 的根導向邏輯與 `Sidebar.tsx:201` 的導覽項目維持不變，對使用者而言路徑無感。

### FR4 — 確定性機械檢查

不依賴 LLM 的檢查，與 FR5 的 agent 建議互為獨立義務（AH-7）。

- **FR4.1** 幣別一致性：單一估價表內的所有列須使用同一幣別；不一致時標示。
- **FR4.2** 數量正值：所有數量須為正數；否則標示。
- **FR4.3** 總額對帳：逐列金額加總與表上宣告總額比對，容差 0.5%。
- **FR4.4** 當該表存在任何「無法辨識」的列時，**跳過** FR4.3 的總額對帳，改為報告「因 N 列無法辨識，總額無法核對」。僅在全部列解析成功時才套用 0.5% 容差判定。
- **FR4.5** 機械檢查結果須與 agent 建議在 UI 上可區分，使用者須能分辨哪些結論來自確定性規則、哪些來自 LLM。

### FR5 — Agent 建議

- **FR5.1** 省錢建議為核心 Must（SD-1）。
- **FR5.2** 跨雲比較與品質檢查建議為 Should；尚未產生時以「產生中」狀態呈現，不得空白或假裝不存在。若該類建議在本期未交付，UI 須顯示明確的「本期未提供」而非停留在「產生中」——「產生中」僅適用於本次請求仍在處理的情形。
- **FR5.3** 跨雲比較至少需一朵雲的資料；僅上傳一朵雲時，跨雲比較須明示「資料不足」而非給出無依據的結論（FE-7）。
- **FR5.4** 送交 LLM 的內容為完整解析結果（品項、規格、數量、金額）（FE-3）。
- **FR5.5** agent 得經 `pricing_client` 呼叫各雲的**目錄價**端點確認現價。所得價格只寫入建議文字，**不得回寫明細表**（AH-6）。
- **FR5.6** 允許的端點為三類，含需帳號憑證者：
  - AWS：Price List **Query** API（boto3，走 IAM）與既有公開 Bulk Price List 皆可。
  - GCP：Cloud Billing **Catalog** API（需 API key）。
  - Azure：Retail Prices API（本即公開，不需憑證）。
- **FR5.7** 僅限**目錄價**端點。實際帳單與用量類 API——AWS Cost Explorer、Azure Cost Management、GCP Billing Export——**仍全面禁止**，不在本次解禁範圍。
- **FR5.8** 憑證採平台統一一組，經 GitHub Secrets → `deploy/render-env.sh` → `deploy/.env` 的既有管線注入；不採每使用者自帶憑證。
- **FR5.9** IAM 權限須為最小權限：AWS 端僅授與 `pricing:GetProducts` 等 Price List Query API 所需動作，不得包含任何帳戶資源或帳單資料的讀取權。GCP API key 須限用於 Cloud Billing Catalog API。
- **FR5.10** 憑證缺漏或呼叫失敗時，查價須降級回公開端點或略過，不得使建議產生流程失敗。

### FR6 — 資源生命週期與可見性

- **FR6.1** 估價表為獨立資源，可選擇性綁定架構圖（FE-6）。
- **FR6.2** 每次上傳建立一筆新紀錄，舊紀錄保留。
- **FR6.3** UI 須提供「顯示歷史上傳」的展開清單，可檢視單一舊版的明細。**不得提供並排比較功能**——歷史版本比較在 scope 中列為未承諾。
- **FR6.4** 使用者可手動刪除自己的上傳紀錄。
- **FR6.5** 估價表預設僅上傳者本人可見。
- **FR6.6** 上傳者可將特定估價表明確分享給指定使用者，沿用架構圖既有的分享模型。

### FR7 — 權限

- **FR7.1** 保留 RBAC story id `C1`，語意改為「上傳與檢視估價表」。
- **FR7.2** 移除 `C1h`（每日時數）、`C1r`（估價區域）、`C1o`（SKU 與單價覆寫）、`C1b`（無程式引用的 budget 遺留）四組 story id，包含 `backend/services/rbac_seed_data.py` 中各 11 列的 seed 資料。
- **FR7.3** 授權判斷不得沿用 `cost_service.py:43` 跨模組引用 `services.collab_router` 私有函式（`_user_can_access_diagram`、`_visible_diagrams`）的作法；須改以公開介面或自有判斷取得。

### FR8 — 稽核

- **FR8.1** 須記錄事件層級的稽核軌跡：何人、何時、上傳了哪朵雲的估價表、解析出幾列、幾列無法辨識、何時產生了建議。
- **FR8.2** 稽核記錄**不含**金額與逐項明細。
- **FR8.3** 因原始檔不保存（FR1.6），稽核軌跡無法支援「重現當初那份檔案」的事後回溯；此為已知且接受的限制。

### FR9 — 既有實作退場

同一批部署完成退場與上線（SD-3）。退場邊界比表面的「9 個端點 + 4 張表」大得多，下列為 reverse-engineering 盤點出的完整掛鉤。

- **FR9.1** 移除 `/api/cost` 的 9 個 HTTP operations 與 `cost_router` 相關實作。
- **FR9.2** 移除 4 張資料表（`diagram_cost`、`diagram_cost_line`、`pricing_cache`、`cost_audit_event`）。DDL 為雙軌，須同時處理 `backend/database.py::_ensure_cost_schema()`（329-395 行）與 `schema_rbac.sql:169-212`，並同步更新 `DEPLOY.md:219-238` 的資料表對照表（`project.md` 的 schema↔deploy 同步為 blocking 規則）。
- **FR9.3** 移除 Playwright Calculator 自動化：`azure_calculator_runner.py`、`gcp_calculator_runner.py`、`gcp_calculator_product_resolver.py` 與兩支 spike script，以及 Python 端的 `playwright` 相依。
- **FR9.4** **保留** `pricing_sdk.py` 與 `boto3` 相依，作為 FR5.6 的 AWS Price List Query API 客戶端。`pricing_client.py:20` 與 `:280-283` 的 `use_sdk_enabled()` 分支保留，`COST_PRICING_USE_SDK` 預設值須由目前的 `0` 改回可啟用。`tests/test_pricing_sdk.py` 與 `tests/test_pricing_client.py:73-74`（patch 該兩個符號）一併保留。
- **FR9.5** 保留 `pricing_client` 及其最小存活集合作為 FR5.5 的查價 Port：`config.py` 與其 9 份 YAML、`pricing_units.py`、`pricing_offer_parser.py`、`pricing_gcp.py`、`pricing_azure.py`、`pricing_query_parser.py`（`pricing_sdk` 的解析相依）。
- **FR9.6** 改寫 `scripts/validate_cost_calculator_boundary.py`——它是 CI `repo-contract` job 的第三步，以硬編碼路徑指向 `backend/cost/cost_calculator.py`，**檔案不存在即 `return 1`**。須改為指向 FR2.3 的新解析器模組，並同步調整 `ci.yml`。**不得直接刪除。**
- **FR9.7** 修正 `scripts/warm_aws_pricing_cache.py`——它直接 import `cost.config`、`cost.price_cache`、`cost.pricing_client`；`price_cache.py` 隨 `pricing_cache` 表退場後此腳本會壞。
- **FR9.8** 增刪環境變數讀取點時，六個設定檔須一併修改：`backend/.env.example`（94-124 行）、`deploy/.env.example`、`deploy/render-env.sh:92`、`deploy/docker-compose.deploy.yml:57`、`deploy/docker-compose.test.yml:40`、`.github/workflows/deploy.yml:101,201`。`validate_env_contract.py` 會反向強制此一致性。本 intent 此處**同時有增有減**：C1 舊參數（`COST_PRICING_STUB` 等）移除，AWS 與 GCP 憑證變數（FR11）重新加入。

- **FR9.9** 更新既有 e2e 回歸 `frontend/tests/e2e/regression.spec.ts:492` 起的成本頁段落——它依賴 test stack 內嵌的 `COST_PRICING_STUB=1` 與硬編碼期望值 `$86.40 / 月`，兩者在新架構下都不存在。
- **FR9.10** 同一 PR 內重跑 `openapi.json` dump 與 `npm run gen:types`，否則 CI 的兩道 drift 閘門都會紅燈。
- **FR9.11** `backend/prompts/cost_pricing_agent_system.md` 以路徑載入，`cost_pricing_agent` 拆除後會成為孤兒檔，須一併處理。

### FR10 — Agent 框架遷移

- **FR10.1** 成本 agent 由 `claude_agent_sdk` 遷移至 LangGraph（IC-5、IC-12）。
- **FR10.2** 模型存取走 OpenRouter 的 OpenAI 相容端點（FE-8）。
- **FR10.3** **不得移除 `claude-agent-sdk` 相依**——`services/design_agent.py`、`services/review_agent.py`、`services/wa_lens_engine.py` 仍在使用。連帶 Dockerfile 的 Node 22 與 `@anthropic-ai/claude-code` 也不可拿掉。
- **FR10.4** 其餘五個 agent 模組的遷移不在本期範圍（IC-12）。

### FR11 — 憑證管線重建

本節推翻本 session 稍早為修復 repo contract 而執行的憑證清除。

> **阻擋前提**：FR5.6、FR9.4 與本節 FR11 全部與**目前仍生效**的規則直接矛盾——`project.md` `## Never`、`team.md` Q2、ADR-0017 §8 皆明文禁止 boto3 IAM 路徑並判定 `pricing_sdk.py` 確定刪除。**ADR-0018 未寫成並正式取代上述敘述之前，這三處需求不得進入實作**。此為 blocking 而非建議（詳見 OQ6）。

- **FR11.1** 重建 AWS 憑證傳遞：`.github/workflows/deploy.yml` 自 GitHub Secrets 讀取、`deploy/render-env.sh` 寫入 `deploy/.env`、`deploy/docker-compose.deploy.yml` 傳入容器。
- **FR11.2** `scripts/validate_repo_contract.py:224-228` 的 `FORBIDDEN_CONTENT_PATTERNS` 須調整——目前它對**任何**受版控檔案中出現 `AWS_SECRET_ACCESS_KEY` 字串即判定失敗（不分是否為實際金鑰），這會讓 FR11.1 直接觸發 CI 紅燈。調整須保留「禁止 commit 實際金鑰值」的原意，僅放行變數名的引用。
- **FR11.3** `DEPLOY.md` 與 `LOCAL-DEV.md` 須同步說明新增的憑證需求與最小權限範圍（`project.md` 的 schema↔deploy 同步為 blocking 規則）。
- **FR11.4** 憑證缺席時系統須可正常啟動並運作（搭配 FR5.10 的降級），本機開發不得被迫持有雲端憑證。

---

## 非功能需求

- **NFR1 — 回應時間**：自上傳完成至建議產出，目標 3 分鐘內，可接受上限 5 分鐘（FE-9、SD-6）。此為本 intent 的主要成功指標（IC-6）。
- **NFR2 — 進度可見**：處理期間須向使用者呈現進度指示，不得是無回饋的等待（FE-9）。
- **NFR3 — 上傳面安全**：這是本 repo 第一個未受信任的檔案輸入面。須落實 ADR-0006 安全基線——檔案型別驗證（FR1.4）、大小上限（FR1.3）、解析過程的資源界限，以及解析失敗不得洩漏內部路徑或堆疊資訊。
- **NFR4 — 解析正確性**：解析器受 property-based test 覆蓋（FR2.4）；成功解析但內容可疑的資料，由 agent 的品質檢查建議負責指出（FE-10）。
- **NFR5 — 可觀測性**：事件層級稽核記錄如 FR8.1。
- **NFR6 — 分層結構**：維持 `cost_router` → `cost_service` → 純函式層的三層形狀，純函式層改錨至估價表解析器（ADR-0017 §1–§2）。禁止把成本邏輯寫進 `user_router.py` 或 `wa_rule_engine.py`。
- **NFR7 — 可測試性**：新功能須產出 TCMS 測試案例，通過 `scripts/tcms_validate.py --all` 且無 ERROR（`project.md` `## Mandated`，blocking）。
- **NFR8 — 部署環境可用性**：新路徑不得依賴部署容器內不存在的執行期元件。`backend/Dockerfile` 未執行 `playwright install chromium`——這正是既有 Calculator 路徑在部署環境結構性不可用的原因，新設計不得重蹈。
- **NFR9 — 憑證安全**：ADR-0006 的 IAM hard constraint 適用於 FR11 的憑證管線。憑證不得出現在版控、日誌或錯誤訊息中；權限範圍限於 FR5.9 的最小集合。此處的風險輪廓明顯低於帳單類 API——`pricing:GetProducts` 這類動作讀不到帳戶內任何資源，回傳的是與公開 Bulk API 相同的目錄價，憑證僅為存取方式；此判斷是 OQ6 之 ADR 的核心論據，也是 FR5.7 維持禁止帳單類 API 的理由。

---

## 限制

- **C1** 文件語言一律繁體中文（ADR-0009）；程式碼、變數、API、識別字維持英文。
- **C2** 部署僅限自有 staging（ADR-0007）；雲端供應商 production 在範圍外（ADR-0001、ADR-0002）。
- **C3** ~~禁止呼叫需雲端供應商帳號憑證的計價 API；`pricing_client` 只准公開免帳號端點~~ —— **本 stage 推翻**（FR5.6）。改為：目錄價端點允許使用帳號憑證；實際帳單與用量類 API（Cost Explorer、Cost Management、Billing Export）仍全面禁止（FR5.7）。原規則載於 `project.md` `## Never`、`team.md` Q2、ADR-0017 §3 與 §8，三處均須依 OQ6 的新 ADR 修訂。
- **C4** `backend/` 是 flat module 而非 Python package，以 `sys.path` 為根 import；新模組須沿用此形式。
- **C5** repo contract 與 env contract 兩支腳本為 CI 閘門，commit 前須通過。
- **C6** `backend/cost/` 目前只有一條進入邊（`backend/main.py:13`），且 `backend/services/` 無任何模組反向 import `cost.*`。此單向相依是重寫時的有利條件，須維持不被破壞。

---

## 假設

- **A1** 三朵雲的官方估價表匯出格式在本期開發期間維持穩定。**依據**：均為各雲官方 Calculator 的既有匯出功能。**若不成立**：解析器需增修，屬 FR2.2 寬鬆策略可吸收的範圍。
- **A2** 使用者上傳的估價表已含其專屬折扣，因此比目錄價更接近帳單真相。**依據**：這是本次反轉估價來源的核心前提（見意圖分析）。
- **A3** 單一使用者 Danniel 代表架構師、FinOps／分析師、管理層三種角色進行驗收（SD-8）。
- **A4** OpenRouter 的既有 token 額度足以支撐本功能的 LLM 呼叫量。**若不成立**：需新申請 token（FE-8 已預留此選項）。

---

## 不在範圍

- **排除**：排程重新評估／重跑（SD-5 唯一明確排除項）。
- **未承諾**（不在範圍、不在排除、未來未定）：匯出建議、歷史版本**並排比較**、自動把建議套用到架構圖。
- **本期不做**：其餘五個 agent 模組的 LangGraph 遷移（FR10.4）。
- **範圍外**（除非新 ADR）：production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS／Android app。

---

## 開放問題

- **OQ1 — 本 stage 造成四處 scope-document 漂移，全部須回補。** 前兩處是**新增**能力：FR6.3（歷史清單檢視）與 FR6.6（分享，經使用者裁定為 **Must**）在 CAP-1 至 CAP-9 中均無對應項（來源 F2、F3）。後兩處是 F4 造成的**推翻**：
  - `scope-document.md:73`（CAP-7）明載「`pricing_sdk.py` **確定刪除**——它是 boto3 IAM 路徑，仍在禁用之列」，與 FR9.4 保留該檔的決定直接相反。
  - CAP-8 的四條界線之一為「只准公開端點」（`scope-document.md:134`），與 FR5.6 允許 IAM 與 API key 的決定直接相反。

  四處均須於 `scope-document.md` 與 `intent-backlog.md` 回補，其中後兩處須待 ADR-0018 成立後才有依據。scope-definition 的 drift 將增為四項。
- **OQ2 — 分享（FR6.6）在交付順序中的位置未定。** SD-7 的 value-first 排序是「先上傳與明細顯示、建議後補」，但分享是 Must。它排在建議之前或之後，留給 delivery-planning 決定。
- **OQ3 — FR6.1 的「可選綁定架構圖」綁定語意仍未定義。** 綁定後是否影響可見性（FR6.5 的例外）、解除綁定的行為、架構圖被刪除時估價表的去向，均未決。此為 ideation 遺留（`scope-document.md` 已記載），需在 domain-design 解決。
- **OQ4 — FR7.3 的替代授權來源未定。** 已知不得沿用跨模組私有函式引用，但改用公開介面或自有判斷，需在 domain-design 決定。
- **OQ5 — FR9.2 的既有資料處理方式。** FE-5 定案不保留歷史資料，但 4 張表在 staging 環境已有實際資料，移除時的操作步驟（直接 drop 或先備份）未定，屬 deployment-execution 範疇。
- **OQ6 — FR5.6 與 FR11 需要一份新 ADR（暫編 ADR-0018），且其影響面超出本 intent。** 需推翻的規則有三處：`project.md` `## Never` 的計價 API 條款、`team.md` Q2 計價 API 規範、ADR-0017 §3 與 §8。此外須判定「僅授 `pricing:GetProducts` 的唯讀 IAM 使用者」是否落入 ADR-0001／0002 所列的 production credentials 範圍外事項——若是，ADR-0001 亦須修訂。此決定於 requirements-analysis 階段由使用者裁定，時序上晚於 ADR-0017 的同日兩次修訂，ADR-0018 須明載它取代的是本 session 稍早的哪些敘述。
- **OQ7 — FR11.2 的 repo contract 調整方式未定。** 現行 `FORBIDDEN_CONTENT_PATTERNS` 以字串比對攔截 `AWS_SECRET_ACCESS_KEY`，不分變數名引用與實際金鑰值。要放行 FR11.1 又不失去防護，可行方向包括改為偵測金鑰值的樣式（如 40 字元 base64）、或對特定設定檔建立白名單。選擇哪一種需在 nfr-requirements 或 devsecops 路徑決定，並須確保調整後仍能攔下真正的金鑰外洩。
- **OQ8 — FR11 的工作量是否影響本期交付順序。** 憑證管線重建、contract 腳本調整、ADR-0018 撰寫是與上傳解析主線平行的一批工作。SD-7 的 value-first 排序（先上傳與明細、建議後補）未預期此項，其插入位置留給 delivery-planning。

## Review

**Reviewer:** aidlc-product-lead-agent
**Verdict:** READY
**Date:** 2026-09-16T10:50:04Z
**Iteration:** 1
**Request Challenge:** review:00540e487ed3ae5bd6d066fa2e2e0d2d

### Findings

| ID | 嚴重度 | 位置 | 問題 | 建議做法 | 狀態 |
|---|---|---|---|---|---|
| R-01 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > FR11`（節首段） | FR5.6、FR9.4 與 FR11 整節與現行規則直接矛盾，須在 ADR-0018 成文前不得進入實作 | 在 FR11 節首加入 blocking 前提 | Resolved |
| R-02 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > OQ1` | OQ1 須明列 F4 造成的兩處 scope-document 推翻（`pricing_sdk.py` 確定刪除 vs FR9.4 保留；CAP-8「只准公開端點」界線 vs FR5.6 允許 IAM） | 在 OQ1 補列四處 drift | Resolved |
| R-03 | Minor | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > NFR8 / NFR9` | NFR9（憑證安全）須在 NFR8（部署環境可用性）之後，因後者的 Playwright 說明是前者的脈絡基礎 | 調整 NFR9 順序置於 NFR8 之後 | Resolved |
| R-04 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > FR5.2` | FR5.2 須區分「產生中」（本次請求仍在處理）與「本期未提供」（功能本期未交付），以免「產生中」被當成永久佔位 | 在 FR5.2 內明寫兩種狀態的觸發條件與對應文字 | Resolved |
| R-05 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > FR2.2` | FR2.2「無法辨識」判定未定義，QA 無法撰寫測試 | 補充「無法辨識」的精確判定標準（至少指明哪個欄位的哪種失敗狀況） | Resolved |
| R-06 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > FR9.6` | FR9.6 要求 `scripts/validate_cost_calculator_boundary.py` 改為指向「FR2.3 的新解析器模組」，但該模組尚未命名；腳本現行邏輯為「目標路徑不存在即 `return 1`」，命名確定前 CI repo-contract job 第三步會一直紅燈 | 在 FR9.6 補充新解析器模組的預期路徑或一個佔位名稱，或明確標示此處依賴 domain-design 命名決定（並在 FR9.6 加一條「本項實作須待 domain-design 決定模組路徑後方可執行」的備註） | Rejected: 作者裁定模組命名屬 domain-design 職責，FR9.6 僅要求改指向新路徑而非直接刪除；CI 因路徑未定而紅燈的風險由 delivery-planning 的 unit 依賴序管控 |
| R-07 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > FR2.3` | FR2.3 的「純函式」約束若用行為描述而非可執行判準（import 層）表達，CI 無法自動稽核 | 將判準改為可執行的 import 層比對（`validate_cost_calculator_boundary.py` 現行形式），或明確指出要延用何種工具 | Resolved |
| R-08 | Major | `aidlc/spaces/default/intents/260916-estimate-upload-rework/inception/requirements-analysis/requirements.md > FR5.6` 與 `> C3`（約束區段） | FR5.6 以陳述式口吻列出 boto3 IAM 為允許端點（「AWS：Price List Query API（boto3，走 IAM）與既有公開 Bulk Price List 皆可」），C3 以「本 stage 推翻」語氣確認此方向，均未嵌入指向 FR11 阻擋前提的交叉引用。開發者讀 FR5 或 C3 時，無法從這兩處自身得知 boto3 IAM 路徑在 ADR-0018 成文之前不得實作——須主動跨節閱讀 FR11 才能獲知。若 construction 時 FR5 任務先被領取，implementer 可能在 ADR-0018 缺位的情況下開始 IAM 實作，直接違反現行 ADR-0017 §8 與更新後的 `project.md` 規則（「含走 IAM 的 boto3 Pricing Query API——仍全面禁止」），屆時回頭修改代價不低。 | 在 FR5.6 末尾或 FR5 節尾加一行提示，例如：「⚠ AWS IAM 路徑（FR5.6 第一項）與 pricing_sdk.py 保留（FR9.4）須待 ADR-0018 正式取代 ADR-0017 §8 後方可實作，詳見 FR11 阻擋前提。」C3 同理，在「三處均須依 OQ6 的新 ADR 修訂」後補一句「在此之前，C3 原禁令仍生效，不得以本條款已被「推翻」為由逕行實作。」 | New |

### 摘要

本文件在結構完整性與可追溯性上達到 inception requirements-analysis 的標準：全部功能需求有來源標記、NFR 有可測量目標、退場盤點細至行號、阻擋前提機制（FR11）設計正確。先前 R-01 至 R-07 七項中，六項已按修正意見處置（R-06 由作者以理由拒絕，立場可接受）。新增 R-08（Major）為**建議修正**：FR5.6 與 C3 在文字上呈現 boto3 IAM 為「已推翻禁令、本期允許」，但阻擋前提僅存於 FR11，兩處之間缺乏交叉引用，是唯一在核可後進入 construction 仍有實際被誤觸的路徑。建議在核可摘要中提醒：**ADR-0018 必須在 construction 的 FR5.6／FR9.4／FR11 任務被領取之前成文**；若 ADR-0018 確認後限定為「公開免帳號端點」（排除 boto3 IAM），FR5.6 須同步縮窄。
