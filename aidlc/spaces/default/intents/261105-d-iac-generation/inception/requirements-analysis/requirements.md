# Requirements — Story D 標準化 IaC 生成與安全交付

<!-- Stage: requirements-analysis（Inception）· 來源標籤見 requirements-analysis-questions.md ## Sources。
     [Q<n>]／[F<n>] 指本 stage 問題檔；[intent]／[scope]／[rm]／[tp]／[kb] 指上游。 -->

## 上游輸入

- **intent-statement**：從既有架構圖產出 Terraform／OpenTofu（D1）＋靜態掃描（D2）＋Secret Manager 整合（D3）；對齊 A／C；平台不代 apply。
- **scope-document**：一次交付 D1＋D2＋D3、三 agent、RBAC／OpenAPI；依賴 D1→D2→D3；Won't：代 apply、production 憑證、商業 IaC 平台嵌入、自研掃描引擎。
- **business-overview／architecture／code-structure**（codekb）：Story D 現為 Coming Soon＋權限種子；無 `/api/iac*`、無 IaC 模組；可複用 `langgraph_runtime`／Workspace SSE。
- **team-practices／discovered-rules**：`backend/iac/`；PBT＝generator＋scanner／redactor；第一個 D HTTP allow／deny；D3 負向＋突變；禁產品代 apply；不新增 CI IaC scan job。
- **rough-mockups**：Workspace 入口、步驟式工作區、草稿為主畫面。

## 意圖分析

**目標**：讓架構師／平台／安全在同一 Workspace 語彙下，把**已選定的架構圖**變成可預覽、可下載的 HCL 草稿，並附帶靜態掃描回饋與密文改寫為 Secret Manager 參考語法；使用者下載後於 Cloud-360 **外**自行 apply。

這不是雲端代運維平台：不代 apply、不寫入雲端 Secret Manager、不嵌入 Terraform Cloud／Spacelift 類產品核心 [scope][tp Forbidden]。

## 功能需求

### FR1 入口、選圖與工作區殼（凍結 R-01）

| # | 需求 | 驗收標準 |
|---|---|---|
| FR1.1 | Workspace 將「生成 IaC」由 Coming Soon 改為可進入之入口（具 D1 相關權限者） | 有權使用者可見可點入口並進入 IaC 工作區；無權者行為見 FR7.1 [rm][Q8] |
| FR1.2 | 進入 IaC 工作區時**自動帶入** Workspace 當前活躍架構圖為預設脈絡 | 活躍圖存在時，工作區脈絡顯示該圖識別／標題，無需再確認一次即可開始 D1 [F1]=C |
| FR1.3 | 工作區內可改選同專案其他既有架構圖 | 下拉／列表切換後，脈絡更新為新圖；後續 D1 以新圖為輸入 [F1]=C [Q1] |
| FR1.4 | 工作區內可上傳／匯入 `.drawio`／`.xml`，建成 diagram 後作為脈絡 | 上傳成功後脈絡指向新建／匯入圖；格式與 Workspace 既有上傳一致 [F1]=C [kb:WorkspacePage] |
| FR1.5 | 無活躍圖、無可選圖、且使用者未上傳時，阻擋產生流程 | 全頁或主區阻擋文案＋回到 Workspace 的 CTA；不可呼叫 D1 產生 [Q8][F1] |
| FR1.6 | IaC 工作區沿用 A／C Workspace layout／元件語彙；步驟為生成／掃描／Secrets；草稿為主畫面 | 可見步驟導覽與草稿主區；非另開無關視覺系統 [rm][scope] |

### FR2 D1 — 從架構圖產生 HCL 草稿

| # | 需求 | 驗收標準 |
|---|---|---|
| FR2.1 | 對當前脈絡架構圖執行 D1，產出多檔模組樹 | 至少含 `main.tf`／`variables.tf`／`outputs.tf`（或經設計核准的等價拆分）；UI 檔案樹列出全部產出檔 [Q2]=A |
| FR2.2 | UI 提供 HCL 預覽（依目前選取檔） | 選檔後預覽區顯示該檔全文（或分頁載入之完整內容）[Q2] |
| FR2.3 | 語法目標為 OpenTofu／Terraform **相容** HCL，不強制單一品牌鎖死 | 產出副檔名／語法為 `.tf` HCL；文件與 UI 不宣稱僅支援單一商業發行版 [Q2] |
| FR2.4 | 雲端覆蓋：本輪 Must 優先完整支援 AWS；圖含 GCP／Azure 資源時仍產出對應草稿，可標「實驗性」，**不得靜默丟棄** | 含非 AWS 資源的測試圖：產出中可見對應資源或明確「實驗性」標記區；不得在無提示下省略 [Q3]=A |
| FR2.5 | D1 由專屬 agent 編排，決定性 generator 核心可離線斷言；agent 走 `langgraph_runtime`＋OpenRouter | 存在純函式 generator 模組路徑於 `backend/iac/`；無 Claude-SDK-only 路徑 [tp][scope] |
| FR2.6 | D1 失敗時步驟內錯誤＋重試；不清除已存在之上一步／既有草稿（若有） | 失敗後可見錯誤文案與重試；先前成功草稿仍可預覽（若本次覆蓋失敗策略由設計細化，預設保留最後成功快照）[Q8] |

### FR3 D2 — 靜態掃描結果

| # | 需求 | 驗收標準 |
|---|---|---|
| FR3.1 | 對當前 D1 成功草稿執行／呈現靜態掃描報告（整合既有 CLI，非自研引擎） | 報告含至少一則 finding 或明確「無 finding」；嚴重度以文字呈現（非僅色票）[scope][rm][Q7] |
| FR3.2 | 掃描為 **Advisory**：任何嚴重度不阻擋進入 D3 步驟畫面 | 有 HIGH／CRITICAL 時仍可進入 Secrets 步驟 UI [Q4]=A |
| FR3.3 | HIGH／CRITICAL 必須在 UI 醒目列出；下載前顯示摘要確認 | 下載流程出現摘要（含 HIGH／CRITICAL 計數或清單）後使用者才能完成下載確認 [Q4] |
| FR3.4 | 本 intent 不新增 CI IaC scan job；產品內掃描編排＋報告形狀須可 unittest（CLI 可 stub） | CI workflow 不因本 intent 新增 checkov／tfsec 等 job；存在報告形狀之自動化測試 [tp Q3] |
| FR3.5 | D2 agent 與決定性 scanner／報告形狀核心落在 `backend/iac/`；scanner 核心納 PBT | 同 PR 含 Hypothesis 覆蓋 scanner／報告形狀不變量 [tp Q5] |

### FR4 D3 — Secret 改寫（不寫入雲端）

| # | 需求 | 驗收標準 |
|---|---|---|
| FR4.1 | 偵測草稿中疑似密文／密鑰賦值，改寫為對應雲端 Secret Manager **資料來源／參考語法**（依資源所屬供應商） | 改寫後草稿不再含該明文賦值；改為 SM 參考形狀（設計指定各雲語法）[Q5]=A |
| FR4.2 | UI 列出「已改寫項目」；若無可改寫項，明確顯示該狀態 | 有改寫時清單筆數＝改寫數；無則可見「無可改寫項」類文案 [Q5][Q7] |
| FR4.3 | **不**代建立雲端 secret、**不**呼叫需帳號的 SM 寫入 API | 程式／設定無 SM Create／Put 類寫入整合作為本輪交付 [Q5][scope] |
| FR4.4 | 明文不得出現在 API 回應、log、下載物 | 負向測試：注入樣式明文後，回應／log sink／zip 內容不得出現該明文；redaction 路徑須突變驗證 [tp Q4] |
| FR4.5 | D3 agent＋redactor 純函式核心於 `backend/iac/`；redactor 納 PBT | 同 PR 含 Hypothesis [tp Q5] |

### FR5 下載與複製

| # | 需求 | 驗收標準 |
|---|---|---|
| FR5.1 | 提供當前草稿 **zip** 下載 | D1 成功後可下載；zip 內含模組樹檔案 [Q2][F2] |
| FR5.2 | 提供「複製目前檔」 | 複製後剪貼簿／UI 回饋對應目前預覽檔內容 [Q2] |
| FR5.3 | D2／D3 完成後之下載為當下快照（可含掃描摘要檔或 secrets 改寫後樹；設計指定打包清單） | 完成 D3 改寫後下載內容反映改寫後 HCL；若含掃描摘要則與 UI 報告一致 [Q6][F2] |
| FR5.4 | 無 D1 成功草稿時，下載控制項 disabled＋說明 | 不可產生空 zip 作為成功下載 [F2]=A |

### FR6 步驟導覽與執行前置條件

| # | 需求 | 驗收標準 |
|---|---|---|
| FR6.1 | 使用者可自由**檢視**生成／掃描／Secrets 各步驟 UI（不強制線性才能「看到」下一步畫面） | 無 D1 成功時仍可點開 D2／D3 步驟頁面查看空狀態或說明 [Q6]=C [F2]=A |
| FR6.2 | **執行 D2／D3** 須已有至少一份 D1 成功草稿，否則執行控制項 disabled＋說明 | 無草稿時呼叫執行 API → 4xx 且 UI 不進入 loading 成功態 [F2]=A |
| FR6.3 | 下載前置條件同 FR5.4；另遵守 FR3.3 下載前摘要確認 | 兩者同時成立 [Q4][F2] |

### FR7 授權、錯誤與空狀態

| # | 需求 | 驗收標準 |
|---|---|---|
| FR7.1 | 無權限：入口隱藏或 disabled，並說明缺 D1／D2／D3 哪一故事權限 | 無 D1.edit（或產品定義之產生權）時無法開始 D1；UI 不假裝有權 [Q8]=A |
| FR7.2 | 第一個 D1／D2／D3 HTTP 消費者落地時，即使 seed 未改，仍有 allow／deny TestClient（有權 2xx、無權 403） | CI unittest 覆蓋 [tp Q2] |
| FR7.3 | D1／D2／D3 失敗：步驟內錯誤＋重試；保留上一步產物；錯誤樣式語彙對齊 A／C Workspace | 見 FR2.6；不採「失敗即清空整次工作階段」[Q8]≠C |

### FR8 平台邊界與可演示路徑

| # | 需求 | 驗收標準 |
|---|---|---|
| FR8.1 | 產品 API／agent **不得**代使用者對雲端 apply／destroy | 無 apply／destroy 端點或 agent 工具；文件明示下載後自行 apply [tp Forbidden][intent] |
| FR8.2 | 可演示路徑：選圖／上傳 → D1 預覽／下載 → D2 報告（真實或 stub CLI）→ D3 改寫或「無可改寫項」→ 下載 | Staging 或本機可走完；LLM 可 stub／錄製，但 generator／scanner 報告形狀／redactor 有自動化測試護欄 [Q7]=A |
| FR8.3 | OpenAPI 與前端型別管線含本輪新增 IaC 相關 operations；RBAC 種子與真實能力一致標示（矩陣領先≠已交付） | OpenAPI drift CI 綠；文件不把種子當已有能力 [scope][tp] |

## 非功能需求

| # | 面向 | 需求 | 驗收標準 |
|---|---|---|---|
| NFR1 | 安全 | ADR-0006 security baseline（IAM、encryption、network exposure、audit logging）逐項檢查本輪變更 | 設計／實作檢核表四列皆有判定 [tp] |
| NFR2 | 正確性 | IaC generator、scanner、redactor 純函式核心須 PBT（Hypothesis），不得只有 example-based | 模組落地同 PR 含 `@given`；純函式層無 httpx／DB／HTTPException [tp] |
| NFR3 | 保密 | 密文不進入 log／回應／artifact；D3 負向＋突變測試 | 見 FR4.4 [tp] |
| NFR4 | 授權測試 | 規則 A／B／C 適用；第一個 D HTTP 含 403 | 見 FR7.2 [tp] |
| NFR5 | 無障礙 | 對齊 rough-mockups a11y：步驟、findings、下載可鍵盤操作；嚴重度不單靠顏色 | 桌面優先；對比與可讀文字 [rm] |
| NFR6 | 可維護性 | 新碼於 `backend/iac/` 領域套件；三層；檔名領域語彙；禁 `d1_*` 前綴；logger `cloud360.*` | code review／路徑約定 [tp] |
| NFR7 | 觀測 | Agent／API 錯誤可在步驟 UI 與伺服器 log（無密文）診斷 | 失敗可重試且有關聯錯誤碼或訊息 [Q8] |

## 約束

- 平台不代 apply；無 production credentials；不做 direct production IaC／destructive cloud ops（除非新 ADR）。
- 不做自研靜態掃描引擎；不嵌入商業 IaC 平台為產品核心。
- 本 intent 不新增 CI IaC scan job。
- 文件繁中；branch／commit 規則依 `team.md`。
- Construction 須過 `tcms-test-cases`（含 LLM 路徑分桶）。

## 假設

| ID | 假設 | 理由 | 驗證時機 |
|---|---|---|---|
| A1 | Workspace 既有 diagram 列表／上傳 API 足以支撐 FR1.3／FR1.4，無需新儲存後端 | codekb／WorkspacePage 已有 `.drawio`／`.xml` 上傳 | refined-mockups／contract-design |
| A2 | 「實驗性」GCP／Azure 產出可用同一 generator 管線加標記，無需本輪等權驗收深度 | [Q3]=A | D1 設計時定義標記方式 |
| A3 | Advisory 下載前摘要可用既有 modal／confirm 語彙實作 | [Q4]=A | refined-mockups |
| A4 | 各雲 SM 參考語法可在設計階段做成可測對照表（純函式） | [Q5]=A | functional-design |

## 範圍外

- 代 apply／plan 管線、寫入雲端 Secret Manager、代建 secret 資源。
- 自研掃描引擎；本輪新增 CI checkov／tfsec／gitleaks job。
- 商業 IaC 平台整包嵌入。
- production credentials、environment-specific secrets 進版控。
- 失敗時自動清空整次工作階段草稿（已否決）。

## 未決問題（留給後續 stage，不阻塞本檔 FR）

| ID | 問題 | 建議承接 |
|---|---|---|
| OQ1 | zip 是否內嵌掃描摘要檔格式（JSON／Markdown）與檔名 | functional-design／contract-design |
| OQ2 | D2 具體整合哪一套 CLI 與版本釘選 | delivery-planning／ADR（工具點名） |
| OQ3 | 「實驗性」非 AWS 資源的 UI 標記文案與是否計入成功演示 | refined-mockups／user-stories AC |
| OQ4 | D1 覆蓋寫入 vs 保留歷史草稿版本策略 | domain-design |
| OQ5 | Q5=B 擴大 PBT 至 scanner／redactor 之追認 ADR 編號 | construction 前開 ADR |

## 追溯摘要

| 決策 | FR／NFR |
|---|---|
| F1=C 選圖＋上傳＋活躍圖 | FR1.2–FR1.5 |
| Q2=A 多檔＋zip | FR2.1–FR2.3、FR5 |
| Q3=A AWS Must＋多雲不丟棄 | FR2.4 |
| Q4=A Advisory | FR3.2–FR3.3 |
| Q5=A 改寫不寫入 SM | FR4 |
| Q6=C＋F2=A 自由檢視／執行需草稿 | FR6、FR5.4 |
| Q7=A 演示深度 | FR8.2、NFR2 |
| Q8=A 錯誤／權限 | FR7 |
| practices PBT／iac 套件／禁 apply | NFR2、NFR6、FR8.1、FR2.5、FR3.5、FR4.5 |
