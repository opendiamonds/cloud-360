

# User Stories - Cloud-360

> 本文件列出 Cloud-360 的使用者故事，嚴格依據 `cloud-360-srs.md` 與 `personas.md`，將架構支柱（Pillars A-H）細分為 3~4 個具體情境（共 24 個 User Stories）。每個故事皆包含使用者需求/目標、多角色協作細節、詳細列點的驗收標準、首頁登入操作流程、正負向系統畫面回饋與引導、AI 重置/人工微調機制，以及 BDD 劇本。
> This document lists the user stories for Cloud-360, strictly based on `cloud-360-srs.md` and `personas.md`, breaking down architecture pillars (A-H) into 3-4 specific scenarios each (24 User Stories total). Each story includes user goals, multi-role collaboration details, detailed acceptance criteria, homepage login flows, highly detailed positive/negative UI feedback with Call-To-Actions, AI reset mechanisms, and BDD scenarios.

### A. 架構設計 (AI-Driven Architecture Design)

#### A1. 自然語言轉架構與草圖產出

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Alex (雲端架構師, `Project_Architect`), Ian (開發者, `Developer`)
  - **協作細節**: Alex 負責輸入自然語言並提供業務與技術需求；AI 會先進行 AWS vs GCP 評估分析並推薦最適合 the cloud 平台；Alex 確認後，AI 產出對應雲平台的初始高階架構；Ian (開發者) 可以即時檢視生成的草圖，並透過對話或「局部重置」調整元件，AI 會更新圖面並動態向 n8n 取得 AWS 或 GCP 的服務圖示。
- **使用者需求/目標 (User Goal)**: 希望透過自然語言輸入需求，讓 AI 評估最適合的雲端平台（AWS 或 GCP），並快速轉換為具體且具備對應圖示的雲端架構藍圖，節省手動評選與繪圖時間。
- **驗收標準 (Acceptance Criteria)**:
  1. 系統在收集完需求後，能進行 AWS 與 GCP 的優缺點評估，並向使用者推薦最適合的雲端平台。
  2. 系統能精準識別自然語言中的 AWS 雲端服務 (如 WAF, Aurora) 與 GCP 服務 (如 Cloud Armor, Cloud SQL) 以及高可用性 (HA) 關鍵字。
  3. 產出的圖表必須為相容 `.drawio` 格式，且能透過 n8n webhook 動態取得正確的 AWS 或 GCP 標準服務圖示 (SVG)。
  4. 圖面必須包含清晰的邏輯連線、對應選定平台的網路邊界 (VPC/AZ 或 GCP Project/VPC/Subnet) 與資料流向。
  5. ✅ **增量**：工作區畫布提供「下載 .drawio」，將目前圖面匯出為 diagrams.net／draw.io 可開啟的檔案（有圖即可；唯讀／檢視亦可下載）。
  6. ✅ **增量（A1↔A3 Multi-Agent）**：Workspace 聊天產圖**自動**啟動 Design↔WA Review 雙 agent 對話（最多 2 輪）；以 lens 總分 ≥80 為硬門檻；過程顯示 transcript，產圖**直接呈現於畫布**；未達標標示失敗並需人工調整。
- **操作流程**: 1. 從首頁登入 Desktop Web，進入專案。 2. 在 AI Chat 輸入架構需求，與 AI 進行平台評估。 3. 確認推薦的平台後，AI 自動產出對應草圖並與 Review Agent 對話優化，圖面直接呈現。 4. **AI重置/人工微調**: 未達標或對圖不滿意可手動改參數／對話重試。 5. 需要離線編輯時點「下載 .drawio」。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: transcript 顯示 Design／Review 發言與分數；達 ≥80 時提示成功，架構圖已在畫布。**後續引導**：IaC 或正式 Well-Architected 評估。下載成功時取得 `.drawio` 檔。
  - **失敗 (Failure)**: 兩輪後仍 ＜80 時提示未達標與剩餘 findings，目前最佳圖仍寫入畫布。產圖／評核錯誤時紅色提示並可重試。無圖時下載按鈕停用。
- **BDD**: `Given` Alex 在輸入頁面 `When` 提出需求並產圖 `Then` 系統自動跑 Design↔Review 協作且達標或明確失敗，圖面直接呈現。
  `Given` 畫布已有架構圖 `When` 點擊「下載 .drawio」 `Then` 取得可用 diagrams.net 開啟的檔案。

#### A2. AI + draw.io 畫布協同編輯

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Alex (雲端架構師, `Project_Architect`), Hannah (工程主管, `Project_Editor`)
  - **協作細節**: Alex 在畫布上調整底層網路層時，Hannah 同時在畫布上框選應用程式層請 AI 優化。兩人可即時看到對方的游標與 AI 生成的變更，避免衝突。
- **使用者需求/目標 (User Goal)**: 透過 AI 協作快速微調架構，避免頻繁手動查閱雲端供應商文檔，並將編輯結果與個人帳號綁定，確保下次登入時能無縫接續編輯。
- **驗收標準 (Acceptance Criteria)**:
  1. 允許使用者在畫布上框選特定節點群組，並要求 AI 進行針對性修改。
  2. AI 在替換或新增節點時，必須自動保留或重新接上原有的邏輯連線。
  3. 支援追蹤多人的修改歷史，允許一鍵還原 (Undo) 任何變更。
  4. 提供「儲存架構圖」功能，將畫布 XML 寫入資料庫，並於下次進入工作區時自動載入最新草稿。
- **操作流程**: 1. 從首頁進入架構畫布（系統自動載入歷史草稿）。 2. 框選特定區域請 AI 優化。 3. 點擊右上角「儲存架構圖」將結果同步至資料庫。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 點擊儲存後出現綠色 Toast 提示「架構圖儲存成功」。**後續引導**：出現懸浮按鈕引導「匯出架構圖」或「查看預估成本」。
  - **失敗 (Failure)**: 儲存失敗或節點元件不相容時出現錯誤提示。**後續引導**：提示「請檢查網路連線後重試」或「點擊查閱雲端相容性官方文件」。
- **BDD**: `Given` 畫布已有基礎架構並存檔 `When` 使用者重新登入並進入工作區 `Then` 系統自動從資料庫載入該使用者最後一次儲存的畫布 XML 狀態。

#### A3. 自動化 Well-Architected 評核與模擬

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Hannah (工程主管, `Project_Editor`), Fiona (資安審查員, `Security_Reviewer`)；Alex（`Project_Architect`）可於產圖後發起
  - **協作細節（✅ 本期 MVP）**: Hannah 發起評核後，與 Fiona **在同一份評核結果**中分別關注不同支柱／發現（例如可靠性 vs 安全性），無需各跑一次。
  - **協作細節（✅ 2026-07-26 增量）**: 具 A3.**審核**（`can_review`）者（預設含 Fiona／`Security_Reviewer`）在評估儀表板維護 Offline Lens **五大柱審核標準**；其他人發起之**新**評核自動套用最新標準。
  - **協作細節（⏳ 下期）**: Hannah 發起 HA／DR／SPOF 模擬；Fiona 確認修復未引入新資安風險。
- **使用者需求/目標 (User Goal)**: 確保設計出的架構符合雲端最佳實踐，提前發現並規避潛在風險；資安審查員可依組織標準調整評核題目。
- **雲端範圍**: ✅ **增量已實作**（`a3-upload-multicloud-requirements.md`）：aws／gcp／azure 皆可跑完整評核管線；支柱 UI **本期仍以 AWS WA 五支柱對照**並標註說明；**每雲一份 Active Lens**，規則包深度目標對齊 AWS。
- **驗收標準 (Acceptance Criteria)**:
  1. ✅ **本期**：對選定架構圖（`user_diagrams` XML）執行評核；**規則引擎**產出可重現之硬性發現，**LLM** 補建議文案（**必須與 A1 使用同一 Agent 框架**：Anthropic Agent SDK + OpenRouter）；畫面顯示分數（含支柱維度，可先子集）與發現清單。
  2. ✅ **本期**：評核結果**持久化**（可查歷史、重開詳情）；需具備 A3 RBAC（view／edit／review，見 `role_permissions`）。
  3. ✅ **本期入口**（三者皆須可用，權限足夠時）：(a) A1 產圖成功後引導 CTA「進行 Well-Architected 評估」；(b) 工作區「Well-Architected」按鈕（對目前選中圖）；(c) **評估儀表板**自有權限圖表列表選圖後執行。
  4. ✅ **本期（增量）**：具 A3.**審核**者可於 Assessment「Lens 標準」編輯五大柱題目文案、新增題（系統模板含預設 riskRules）、刪題（每柱 ≥1）；標準存 DB；**僅影響之後新評核**；無審核權者不可編輯。
  5. ✅ **本期（增量）**：具 A3.view 者可對完成報告**下載 PDF**（見 FR-A3-11）。
  6. ✅ **增量（上傳）**：Assessment 與 Workspace 可上傳 draw.io／mxGraph XML；可選「同時存成架構圖」；未建檔亦可評核並寫入歷史報告（`xml_snapshot`）。
  7. ✅ **增量（多雲）**：自動偵測 provider（可覆寫）；gcp／azure 不再 `unsupported`；各雲獨立 rule pack＋每雲 Active Lens；UI 標註以 AWS WA 五支柱對照。
  8. ✅ **增量（預覽／PDF 附圖）**：選圖或上傳後於 Assessment **預覽架構圖**；下載 PDF 時附**架構圖對照頁**（中文標題正常）。
  9. ✅ **增量（A1↔A3 Multi-Agent）**：Assessment 報告含 **HIGH_RISK** 時可點「優化」啟動 Design↔Review；無高風險或評核進行中反灰；協作目標為消除高風險。
  10. ⏳ **下期**：模擬單點故障 (SPOF) 或 AZ 級中斷，並估算 RPO／RTO；UI 手改 riskRules；lens 版本／歷史重跑；各雲官方框架支柱名稱切換；官方 WA API。
- **操作流程（✅ 本期）**: 1. 經上述任一入口選定圖並發起評核（或上傳後評核）。 2. 於預覽確認圖面後檢視分數與發現。 3. 可按「優化至 WA ≥ 80」啟動雙 agent 改圖。 4. 可於儀表板重開歷史評核。 5. Fiona 於「Lens 標準」依雲別調整題目並儲存。 6. 下載 PDF（含架構圖對照頁）。
- **系統回饋 (System Feedback)**:
  - **成功（✅ 本期）**: Toast／面板顯示評核完成與總分；列出發現與建議；Lens 儲存成功提示；預覽區顯示圖面；Multi-Agent 達標可套用改圖。**後續引導**：歷史、PDF，或返回畫布。
  - **失敗（✅ 本期）**: 規則或 LLM 階段錯誤時可讀提示；規則成功但 LLM 失敗時仍應保留規則發現；Lens 驗證失敗阻擋儲存；PDF 附圖失敗時仍可下載文字報告；Multi-Agent 兩輪未達 80 標示需人工。**後續引導**：重試或聯絡 SRE／管理員。
  - **失敗／風險標示（⏳ 下期）**: SPOF 節點跳動驚嘆號、撒花滿分徽章等進階動效。
- **BDD**:
  - ✅ `Given` Alex 剛完成 A1 產圖 `When` 點擊產圖後 Well-Architected CTA `Then` 系統對該圖發起評核並顯示分數與發現。
  - ✅ `Given` Hannah 在儀表板選取有權限之 diagram `When` 執行架構評估 `Then` 結果寫入歷史且 Fiona 可開啟同一報告檢視安全相關發現。
  - ✅ `Given` Fiona 開啟 Assessment「Lens 標準」並新增／修改一題後儲存 `When` Hannah 發起新評核 `Then` 新結果反映更新後標準，且既有歷史評核分數不變。
  - ✅ `Given` 使用者無 A3 審核權限 `When` 呼叫 Lens 寫入 API 或開啟編輯 UI `Then` 收到 403 或入口不可見。
  - ✅ `Given` Hannah 上傳合法 `.drawio` 且不勾建檔 `When` 執行評核 `Then` 產生可查歷史報告且未強制新增工作區圖檔。
  - ✅ `Given` 圖面含 GCP 服務關鍵字 `When` 系統偵測為 gcp（可覆寫）並評核 `Then` 使用 gcp rule pack 與 gcp Active Lens，狀態非 unsupported。
  - ✅ `Given` Hannah 已選圖或上傳 XML `When` 開啟 Assessment `Then` 可見架構圖預覽。
  - ✅ `Given` 評核已完成 `When` 下載 PDF `Then` 報告含架構圖對照頁且中文標題可讀。
  - ✅ `Given` Hannah 在 Assessment 有可評核 XML `When` 點「優化至 WA ≥ 80」`Then` 啟動 Design↔Review 協作並回傳預覽圖與分數結果。
  - ⏳ `Given` 掃出資料庫單點故障 `When` Hannah 人工補上備援並局部重置評分 `Then` 分數重新計算並達標（下期）。

#### A4. 重整後仍記得對話與上次開啟的架構圖

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Alex (雲端架構師, `Project_Architect`), Hannah (工程主管, `Project_Editor`)
  - **協作細節**: Alex 與 Hannah 各自在不同架構圖上與 AI 對話；重整瀏覽器或重新登入後，每人回到自己上次開啟的圖，並看到該圖對應的完整聊天紀錄，互不混淆。
- **使用者需求/目標 (User Goal)**: 重整重整或短暫離開後，仍能接續與 AI 的多輪對話，並自動回到上次編輯的架構圖，無需重述需求。
- **驗收標準 (Acceptance Criteria)**:
  1. 聊天紀錄必須持久化於後端資料庫，鍵值為 **使用者 × 架構圖 (`user_id` + `diagram_id`)**；不同圖表的對話互相隔離。
  2. 進入工作區（或重整頁面）時，系統必須自動選回該使用者**上次開啟的架構圖**，並載入其 XML 與對應聊天 `messages[]`。
  3. 每次使用者送出訊息或收到助理回覆後，聊天紀錄須寫回資料庫（至少在一輪對話結束後成功持久化）；切換 `diagramId` 時載入該圖的對話（無紀錄則顯示預設歡迎訊息）。
  4. 僅圖表擁有者與被分享且有權開啟該圖的使用者可讀寫對應聊天；未授權回傳 403。
  5. 工作區須提供「清空對話」按鈕：點擊並確認後，刪除**目前架構圖**對應的 `user × diagram` 聊天紀錄，畫布 XML 不變；清空後聊天區回到預設歡迎訊息。
- **操作流程**: 1. 登入並開啟某架構圖，與 AI 多輪對話。 2. 重整瀏覽器或重新登入進入工作區。 3. 系統自動選回上次圖表並還原聊天；可繼續追問（例如「再加上 WAF」）。 4. 若要重開話題，點「清空對話」→ 確認 → 僅該圖聊天被清除。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 進入工作區後聊天區顯示歷史訊息，畫布為上次圖表；可選 Toast「已還原上次對話」。清空成功時 Toast「✔ 已清空此架構圖的對話」。
  - **失敗 (Failure)**: 無法載入歷史時顯示預設歡迎訊息與提示「無法還原對話，請重新描述需求」；不阻擋產圖。清空失敗時紅色提示「無法清空對話，請重試」。
- **BDD**: `Given` Alex 在 diagram#12 已與 AI 對話三輪並重整頁面 `When` 再次進入工作區 `Then` 系統自動開啟 diagram#12 且聊天區顯示原先三輪訊息。
  `Given` Alex 在 diagram#12 有歷史對話 `When` 點擊清空對話並確認 `Then` 該圖聊天被刪除、顯示歡迎訊息，且 diagram#12 的 XML 仍在。

#### A5. 跨使用者架構圖分享與即時協同連線

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Alex (雲端架構師, `Project_Architect`), Hannah (工程主管, `Project_Editor`), Ian (開發者, `Developer`)
  - **協作細節**: Alex 發起架構圖分享，在彈出視窗勾選 Hannah（擁有編輯權限）與 Ian（僅檢視權限）。當 Hannah 進入工作區時，系統透過 WebSocket 自動建立協同編輯連線，其畫布操作與游標即時同步予 Alex。而當僅有檢視權限的 Ian 登入時，畫布自動鎖定且 AI 聊天區顯示「您目前為僅檢視權限，無法編輯或與 AI 對話」，同時其能即時看見 Alex 與 Hannah 的編輯進度。
- **使用者需求/目標 (User Goal)**: 能便捷地將所設計的架構圖分享予專案相關角色，實現多人在畫布上的即時共同編輯，或依其角色權限進行唯讀檢視與審核。
- **驗收標準 (Acceptance Criteria)**:
  1. 提供「分享架構圖」設定彈窗 (ShareModal), 擁有編輯權限的使用者或圖表擁有者可在此勾選並授權其他協作者。
  2. 當多名具備編輯權限的使用者同時開啟此分享圖表時，前端應能自動連線 WebSocket (`/api/collab/ws/{workspace_id}`), 使協作畫布操作能實時進行雙向廣播。
  3. 狀態列需能動態感應連線狀態，顯示「協作中」或「單機模式」標籤。
  4. 實施細粒度權限隔離與聊天室歡迎詞：編輯者 (can_edit) 聊天室呈現 `DEFAULT_WELCOME`；審核者 (can_review) 聊天室唯讀並呈現 `REVIEW_ONLY_WELCOME`；檢視者 (can_view) 聊天室唯讀並呈現 `VIEW_ONLY_WELCOME`。
- **操作流程**: 1. 從工作區點擊畫布右上角的「分享」按鈕。 2. 勾選欲分享之協作者角色，點擊「確定分享」儲存設定。 3. 被分享的使用者在其工作區開啟該圖表，WebSocket 連線成功建立。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 彈窗顯示「✔ 權限分享成功」，畫布右上角狀態轉變為綠色「協作中」。**後續引導**：提供「複製分享連結」按鈕。
  - **失敗 (Failure)**: 連線中斷時右上角標籤轉變為灰色「單機模式」。**後續引導**：提供「重試連線」或「點擊查看連線指南」按鈕。
- **BDD**: `Given` Alex 分享 diagram#12 給擁有編輯權限的 Hannah 與僅檢視權限的 Ian `When` 兩者登入並開啟 diagram#12 `Then` Hannah 能看見協同編輯游標且畫布可寫，Ian 畫布唯讀且聊天區渲染「僅檢視」警告，雙方皆可看見 WebSocket 連線狀態。

---

### B. 跨雲選型 (Cross-Cloud Component Selection)

#### B1. AI 驅動單一雲端評選決策

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Catherine (技術決策者, `Project_Admin`), David (FinOps 分析師, `FinOps_Analyst`)
  - **協作細節**: Catherine 關注效能與 SLA 權重；David 介入並切換為成本優先權重。雙方在同一個矩陣表上進行不同權重的沙盤推演，並將各自的分析結果整合進決策報告。
- **使用者需求/目標 (User Goal)**: 客觀評估不同雲端供應商，以快速找出最適合專案的雲端平台。
- **驗收標準 (Acceptance Criteria)**:
  1. 支援根據使用者設定的偏好權重自動排序雲端供應商推薦。
  2. 比較矩陣表格必須具備至少三個維度：SLA、硬體限制、計費模式。
  3. 能夠一鍵將對比結果與決策矩陣匯出為 PDF 報告。
- **操作流程**: 1. 從首頁進入選型模組。 2. 輸入專案業務特性。 3. **AI重置/人工微調**: 點擊「全部重置」切換權重，或人工點選隱藏 AWS 以專注看 GCP 與 Azure。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 產出帶有各雲端商 Logo 的動態對比圖表，最優選將高亮顯示。**後續引導**：引導點擊「套用此雲端商並開始架構設計」。
  - **失敗 (Failure)**: 儀表板顯示黃色「API 逾時」警示條，數據呈現灰色。**後續引導**：提示「請點擊重新整理按鈕」，若持續失敗則引導「提交工單聯絡平台維護團隊」。
- **BDD**: `Given` 跨雲對比表已生成 `When` 點擊局部重置要求更新 SLA，並人工隱藏 AWS `Then` 系統僅產出剩餘廠商的最新數據。

#### B2. 技術生態與相容性掃描

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Alex (雲端架構師, `Project_Architect`), George (運維負責人, `Ops_Lead`)
  - **協作細節**: Alex 匯入開發端的 CI/CD 堆疊；George 匯入維運端的監控工具 (如 Prometheus)。AI 綜合兩者的清單產出跨部門的相容性與移轉工時報告。
- **使用者需求/目標 (User Goal)**: 評估現有技術地端棧遷移至雲端的相容性，以準確預估重構成本。
- **驗收標準 (Acceptance Criteria)**:
  1. 能解析現有地端技術棧，並比對至各雲端對應之託管服務。
  2. 為每一項技術遷移提供精確的相容性分數 (0-100%)。
  3. 提供初步預估的遷移與代碼重構工時 (以天或小時為單位)。
- **操作流程**: 1. 從首頁進入相容性分析室。 2. 匯入現有技術棧。 3. **AI重置/人工微調**: 「局部重置」重新評估特定 DB，並人工標註「必定保留的 CI/CD 工具」。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 顯示環狀進度條 (如 85% 相容)，下方展開綠色的無縫轉移清單。**後續引導**：引導點擊「查看需要人工重構的代碼清單」。
  - **失敗 (Failure)**: 圖表卡在 0% 並彈出紅字「查無雲端替代方案」。**後續引導**：提示「請調整為 IaaS 虛擬機評估方案」，或「聯絡平台管理員新增支援服務」。
- **BDD**: `Given` 獲得初始相容報告 `When` 人工標註 Jenkins 必定保留，並局部重置 `Then` AI 重新評估整合風險並更新報告。

#### B3. 地緣合規與存取延遲優化

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Fiona (安全性審查員, `Security_Admin`), Catherine (技術決策者, `Project_Admin`)
  - **協作細節**: Catherine 輸入目標客群所在地以追求最低延遲；Fiona 則加入 GDPR 與當地資料落地法規限制。AI 在兩者的需求中找出交集，若有衝突則提示需取捨。
- **使用者需求/目標 (User Goal)**: 確保應用程式部署的區域符合當地法規，且對目標客群的存取延遲最低。
- **驗收標準 (Acceptance Criteria)**:
  1. 系統內建常見法規資料庫 (如 GDPR、HIPAA) 的資料落地要求與邊界。
  2. 根據目標客群位置，在地圖上直觀提供延遲最低的 Top 3 Region 建議。
  3. 若使用者強行選擇違反法規限制的區域，必須以紅字強烈阻擋並給出原因。
- **操作流程**: 1. 從首頁登入地緣合規設定區。 2. 輸入目標客群所在地。 3. **AI重置/人工微調**: 「全部重置」切換法規情境，並人工加入自定義限制。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 世界地圖上出現綠色光點標示最佳 Region，並附上法規核准打勾。**後續引導**：引導點擊「確認區域並鎖定專案設定」。
  - **失敗 (Failure)**: 地圖上的所選區域覆蓋紅色斜線，彈出「違反 GDPR」警告。**後續引導**：提示「請點擊系統推薦的替代 Region」，或「聯絡法務/資安團隊評估例外豁免」。
- **BDD**: `Given` 系統建議美東機房 `When` Fiona 人工勾選 GDPR 並局部重置 `Then` 系統重新推薦歐盟機房。

---

### C. 成本估算與 FinOps (Cost Estimation & FinOps)

#### C1. 專案 TCO 與流量預算預測

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: David (FinOps 分析師, `FinOps_Analyst`), Hannah (工程主管, `Project_Editor`)
  - **協作細節**: David 設定每月的預算上限；Hannah 在架構圖上新增機器時，系統會即時通知 David 預算變化，若超支則觸發警告給雙方。
- **使用者需求/目標 (User Goal)**: 精準掌握專案每月的總體擁有成本(TCO)與預算走勢，避免費用超支。
- **驗收標準 (Acceptance Criteria)**:
  1. 能根據架構圖自動擷取資源，並查詢最新雲端報價 API。
  2. 產出細至每項資源層級的動態成本拆解圓餅圖。
  3. 允許使用者輸入「每日運作時數」，系統需即時重新計算每月總費用。
- **操作流程**: 1. 從首頁登入 FinOps 看板。 2. 匯入架構執行 TCO 計算。 3. **AI重置/人工微調**: 「全部重置」切換流量模型，並人工修改預設開機時數為 8 小時。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 中心出現動態更新的圓餅圖，綠色字體顯示總預算範圍內。**後續引導**：引導點擊「設定預算超支警報 (Billing Alarm)」。
  - **失敗 (Failure)**: 部分區塊顯示灰色並標示「定價無法獲取」。**後續引導**：提示「請手動輸入預估金額」，或引導「點擊聯絡 FinOps 分析師 (David) 確認合約價格」。
- **BDD**: `Given` 初始 TCO 為 $5000 `When` David 人工修改開機時數為 8 小時並局部重置 `Then` TCO 更新為 $2000，並標記 Manual Override。

#### C2. 專案資源優化與定價模型對比

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: David (FinOps 分析師, `FinOps_Analyst`), Ben (SRE, `SRE`)
  - **協作細節**: David 提議將一批機器轉為 Spot 實例以省錢；Ben 收到建議後，負責評估該服務是否為無狀態 (Stateless)，並由 Ben 人工決定「鎖定」不可轉換的核心節點。
- **使用者需求/目標 (User Goal)**: 透過轉換計費模型 (Spot/RI) 最大化節省雲端基礎設施開銷。
- **驗收標準 (Acceptance Criteria)**:
  1. 明確標示出架構中哪些無狀態 (Stateless) 資源適合轉為 Spot 實例。
  2. 精確計算轉換為 1-year/3-year RI 的預期節省百分比。
  3. 允許使用者人工排除特定核心機器，系統需動態重新計算剩餘資源的節省效益。
- **操作流程**: 1. 從首頁進入成本優化區。 2. 要求分析 Spot/RI 效益。 3. **AI重置/人工微調**: 「局部重置」僅看 Spot 實例建議，並人工鎖定某台資料庫拒絕修改。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 畫面浮出金幣動畫，並以大字體顯示「預估節省 30%」。**後續引導**：引導點擊「一鍵套用轉換變更單」。
  - **失敗 (Failure)**: 畫面提示「該架構不適用 Spot 實例」，建議清單為空。**後續引導**：提示「請嘗試解鎖核心機器再試一次」，或「聯絡維運團隊確認架構彈性」。
- **BDD**: `Given` AI 建議全上 Spot `When` David 人工鎖定 DB，並對 Web Tier 局部重置 Spot 效益 `Then` 系統重新算出正確的節省金額。

#### C3. Data Egress 隱性成本深度追蹤

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: David (FinOps 分析師, `FinOps_Analyst`), Alex (雲端架構師, `Project_Architect`)
  - **協作細節**: David 發現跨 AZ 連線產生高昂 Egress 費用，將熱點標記並 tag Alex。Alex 收到通知後調整架構減少跨區流量，David 即時看到費用下降。
- **使用者需求/目標 (User Goal)**: 追蹤與預測最難以察覺的跨區資料傳輸 (Data Egress) 成本。
- **驗收標準 (Acceptance Criteria)**:
  1. 能夠識別並計算跨 AZ 與跨 Region 的潛在網路傳輸費用。
  2. 產出流量熱點圖 (Heat Map)，直觀標示可能導致高昂費用的連線。
  3. 當使用者變更網路拓撲時，即時更新預估的 Egress 總費用。
- **操作流程**: 1. 從首頁登入網路成本追蹤區。 2. 檢視跨區流量預估。 3. **AI重置/人工微調**: 「局部重置」特定 AZ 流量計算，並人工將傳輸量改為 10TB。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 架構圖上的連線轉為粗細不同的藍色流向圖，標明費用。**後續引導**：引導點擊「匯出網路流量熱點分析報告」。
  - **失敗 (Failure)**: 無法解析網路路徑，彈出黃字「請確認網路設定」。**後續引導**：提示「請點擊 AI 檢查網路連線完整性」，或「聯絡網路工程師修復拓撲」。
- **BDD**: `Given` Egress 預測為 $100 `When` 局部重置並人工修改頻寬至 10TB `Then` Egress 費用飆升，並以紅字強烈標記。

---

### D. 標準化 IaC 生成與安全交付 (IaC Generation)

#### D1. 模板化 Terraform / OpenTofu 代碼自動產出

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Elena (平台工程師, `Platform_Engineer`), Ian (開發者, `Developer`)
  - **協作細節**: Elena 負責制定變數與模組 (Modules) 規範；Ian 在撰寫特定服務時生成代碼。系統確保 Ian 產出的代碼自動套用 Elena 設定的企業標籤。
- **使用者需求/目標 (User Goal)**: 自動化產生符合企業標準的 IaC 代碼，支援多雲架構並消除手動撰寫錯誤。
- **驗收標準 (Acceptance Criteria)**:
  1. 能根據畫布架構自動產出支援 `aws`, `google`, `azurerm` provider 對應的 Terraform / OpenTofu 模組代碼。
  2. 代碼目錄必須嚴格遵循企業標準，包含 `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf` 與 `modules/` 結構。
  3. 產出的代碼可直接通過 `terraform init` / `tofu init` 與 `validate` 語法檢查。
- **操作流程**: 1. 從首頁進入 IaC 工作區。 2. 將畫布轉換為代碼。 3. **AI重置/人工微調**: 對 `variables.tf` 點擊「局部重置」加上公司 prefix，並在 IDE 內人工編輯參數。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 編輯器右下角彈出綠色「✔ 轉換成功」，顯示完整 `.tf` 檔案樹。**後續引導**：引導點擊「進入安全靜態掃描」或「一鍵推送到 Git」。
  - **失敗 (Failure)**: 編輯器跳出紅色編譯錯誤提示，問題行數高亮標記。**後續引導**：提示「請點選 AI 自動修復錯誤語法」，若無法解決則「聯絡平台工程師 (Elena)」。
- **BDD**: `Given` AI 初稿生成完畢 `When` Elena 局部重置 prefix 規則並人工改寫 tag `Then` 代碼順利生成並保留人工修改。

#### D2. IaC 安全與合規自動靜態掃描

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Elena (平台工程師, `Platform_Engineer`), Fiona (資安審查員, `Security_Reviewer`)
  - **協作細節**: Elena 提交 IaC 代碼觸發掃描；若掃出漏洞，Fiona 會收到通知，她可以選擇批准風險 (Risk Acceptance) 或要求 AI 提供修復建議讓 Elena 套用。
- **使用者需求/目標 (User Goal)**: 在部署前透過多重掃描引擎攔截代碼中的資安弱點與合規性問題。
- **驗收標準 (Acceptance Criteria)**:
  1. 內建整合 tfsec、Trivy 與 Checkov，在匯出前強制進行深度靜態安全掃描。
  2. 發現 High 或 Critical 漏洞時，必須強制阻擋代碼下載與部署。
  3. 系統必須提供至少一個可直接套用的 AI 修復代碼片段。
- **操作流程**: 1. 從首頁登入安全審查區。 2. 觸發 tfsec/Checkov 綜合掃描。 3. **AI重置/人工微調**: 「局部重置」要求 AI 提供不同修復建議，人工選擇採納並套用。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 畫面中央出現滿版綠色的安全盾牌打勾動畫，標示「0 漏洞」。**後續引導**：引導點擊「核准並開始自動化部署」。
  - **失敗 (Failure)**: 畫面紅光閃爍，阻擋按鈕變灰，列出高危 CVE 漏洞清單。**後續引導**：提示「請點擊 AI 提供的安全修復代碼」，或點選「聯絡資安審查員 (Fiona) 申請特例豁免」。
- **BDD**: `Given` Checkov 掃描出 High 級別漏洞 `When` AI 產出三個修復方案，Elena 人工選擇其一並套用 `Then` 複掃通過，允許 Git Push。

#### D3. Sensitive Values 與 Secret Manager 整合

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Fiona (資安審查員, `Security_Reviewer`), Ian (開發者, `Developer`)
  - **協作細節**: 系統攔截到 Ian 提交的明文密碼；Fiona 接獲警報，強制要求轉為 Secret 引用。Ian 收到修復工單，透過 AI 一鍵替換為安全的 ARN。
- **使用者需求/目標 (User Goal)**: 確保 IaC 代碼中絕不包含明文密碼，避免金鑰外洩風險。
- **驗收標準 (Acceptance Criteria)**:
  1. 精準掃描並找出代碼中任何 hardcoded 的明文金鑰、密碼。
  2. 自動將明文替換為對應雲端 (如 AWS Secrets Manager / Azure Key Vault) 的安全引用格式。
  3. 若無法提供有效的 Secret ARN，禁止將代碼 Push 至遠端存儲庫。
- **操作流程**: 1. 從首頁登入機密檢查區。 2. 掃描 hardcoded secrets。 3. **AI重置/人工微調**: 「全部重置」要求改用 Secrets 引用，人工填寫 Secret ARN。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 密碼明文以打字機特效安全轉換為 Provider 原生 Secret 變數。**後續引導**：引導點擊「儲存代碼並進入下一步」。
  - **失敗 (Failure)**: 跳出紅字「找不到對應的 Secret ARN，替換失敗」。**後續引導**：提示「請前往 Secrets Manager 創建新金鑰」，或「聯絡資安團隊尋求授權」。
- **BDD**: `Given` 代碼存在明文密碼 `When` 點擊局部重置轉換為 Secret 引用並人工填上 ARN `Then` 代碼變更為安全合規格式。

---

### E. 維運優化審查 (Proactive Operations Optimization)

#### E1. 基於行為的自動規模調整 (Right-sizing)

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: George (運維負責人, `Ops_Lead`), Hannah (工程主管, `Engineering_Manager`)
  - **協作細節**: George 收到 5 台機器的降級建議並派發給 Hannah。Hannah 審核業務影響，人工剔除 2 台核心服務，最後 George 執行剩下的 3 台降級指令。
- **使用者需求/目標 (User Goal)**: 根據實際系統負載動態縮減閒置資源，降低成本浪費。
- **驗收標準 (Acceptance Criteria)**:
  1. 連續分析過去 14 天的 CPU/Memory 負載，找出平均使用率過低之機器。
  2. 列出具體建議降級的目標實例型號與預估節省金額。
  3. 支援一鍵生成包含目標機器名單與降級腳本的維運變更單。
- **操作流程**: 1. 從首頁登入運維看板。 2. 查閱 Agent 降級清單。 3. **AI重置/人工微調**: 「局部重置」要求保留 50% 餘裕，人工排除核心機器。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 建議清單旁出現綠色的「建議採納」標章，並動態累加節省總額。**後續引導**：引導點擊「創建降級維運變更單 (CR)」。
  - **失敗 (Failure)**: 目標清單反灰並標示橘色的「受終止保護」。**後續引導**：提示「請前往雲端控制台解除保護狀態」，或「聯絡系統擁有者授權解鎖」。
- **BDD**: `Given` 降級 5 台機器的建議 `When` 人工剔除 2 台並要求 AI 局部重置剩餘 3 台 `Then` 變更單僅包含 3 台機器的安全降級。

#### E2. 雲端架構演進與現代化引導

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Alex (雲端架構師, `Project_Architect`), Catherine (技術決策者, `Project_Admin`)
  - **協作細節**: Alex 透過 AI 產出移轉至 Serverless 的技術分析；Catherine 專注檢視附帶的 ROI 財務報告。兩者在同一計畫案中進行技術與商業的權衡。
- **使用者需求/目標 (User Goal)**: 探索將傳統 Legacy 架構升級為 Serverless 的可行性與效益。
- **驗收標準 (Acceptance Criteria)**:
  1. 自動識別架構中老舊或維運成本過高的 IaaS 資源。
  2. 提供對應的 PaaS 或 Serverless 替代方案。
  3. 估算移轉所需的 ROI 與潛在的效能提升。
- **操作流程**: 1. 從首頁登入現代化評估區。 2. 分析 Legacy 架構。 3. **AI重置/人工微調**: 「全部重置」改以 Serverless 為主，人工勾選必須保留的 VM。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 畫面左右並排顯示「Legacy」與「Serverless」的綠色對比雷達圖，展示 ROI 提升。**後續引導**：引導點擊「匯出高階主管評估簡報」。
  - **失敗 (Failure)**: 畫面提示「技術棧過於老舊，無法自動轉換」。**後續引導**：提示「請嘗試使用 K8s 容器化作為過渡方案」，或「聯絡資深架構師進行人工專案評估」。
- **BDD**: `Given` 分析報告建議全上 K8s `When` 全部重置要求改看 Serverless 方案 `Then` AI 重新產出以 Lambda 為主的移轉計畫。

#### E3. 自動化維運劇本 (Runbooks) 生成

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Ben (SRE, `SRE`), George (運維負責人, `Ops_Lead`)
  - **協作細節**: Ben 透過 AI 生成資料庫重啟劇本並加入人工 Timeout 設定；生成後發送給 George 進行同行審查 (Peer Review)，確認無誤後標記供自動化調用。
- **使用者需求/目標 (User Goal)**: 確保在系統發生常見故障時，能有標準化腳本快速恢復服務。
- **驗收標準 (Acceptance Criteria)**:
  1. 根據目前架構自動產出常見故障 (如 DB 當機) 的應對劇本。
  2. 輸出格式必須為自動化工具 (如 AWS SSM) 可執行的 YAML/JSON。
  3. 劇本需包含明確的重啟指令、Timeout 與恢復驗證步驟。
- **操作流程**: 1. 從首頁進入 Runbook 庫。 2. 要求生成應對劇本。 3. **AI重置/人工微調**: 「局部重置」要求加入快照步驟，並人工修改 Timeout 數值。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 畫面以打字機特效生成完整的 YAML 腳本，右側出現「✔ 驗證通過」綠牌。**後續引導**：引導點擊「註冊腳本至自動化 Runbook 庫」。
  - **失敗 (Failure)**: 指令編輯區塊亮紅燈，顯示「解析錯誤：缺乏必要變數」。**後續引導**：提示「請點擊局部重置讓 AI 重新填寫變數」，或「聯絡 SRE (Ben) 協助編寫腳本」。
- **BDD**: `Given` 基礎重啟劇本 `When` 局部重置加入快照，並人工延長 Timeout 至 120s `Then` 劇本按新參數安全儲存。

---

### F. AI 多雲維運與審批 (AI Multi-Cloud Operations)

#### F1. 自然語言跨雲健康狀態查詢

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Ben (SRE, `SRE`), Hannah (工程主管, `Engineering_Manager`)
  - **協作細節**: Ben 查詢特定異常流量，並將產出的趨勢圖「釘選」分享給 Hannah。Hannah 點擊連結，能直接在圖表上看到 Ben 的標註與對話上下文。
- **使用者需求/目標 (User Goal)**: 透過自然語言快速掌握多雲環境的即時健康狀態與效能瓶頸。
- **驗收標準 (Acceptance Criteria)**:
  1. 正確解析自然語言中提及的特定雲端資源與確切時間範圍。
  2. 透過 MCP 抓取真實監控數據，繪製準確的時間趨勢圖表。
  3. 自動在圖表上標示出超過正常閾值的效能異常點。
- **操作流程**: 1. 從首頁打開 AI Chat。 2. 詢問「昨日跨雲資料庫延遲狀況」。 3. **AI重置/人工微調**: 「全部重置」改變時間範圍，並人工輸入 Tag 過濾。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 聊天視窗內平滑渲染出綠色時間趨勢圖，異常峰值以紅點醒目提示。**後續引導**：引導點擊「將圖表釘選至個人桌面」或「產生分享連結發送給主管」。
  - **失敗 (Failure)**: 圖表轉為雜訊狀態，彈出紅色「MCP 連線超時」。**後續引導**：提示「請點擊重試重新連線」，或「聯絡平台管理員 (Jack) 檢查 Agent 狀態」。
- **BDD**: `Given` 24h 流量圖 `When` 人工加入 `env:prod` tag 並局部重置 `Then` 圖表重新繪製僅顯示生產環境數據。

#### F2. 引導式變更計畫與回滾策略產出

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Ben (SRE, `SRE`), Elena (平台工程師, `Platform_Engineer`)
  - **協作細節**: Ben 產生擴容計畫與回滾腳本；Elena 負責檢視該腳本是否會影響底層 K8s 節點狀態。Elena 人工加入檢查點後，腳本才視為 Ready for Review。
- **使用者需求/目標 (User Goal)**: 安全地執行複雜變更，確保每次維運操作都具備完整的回滾機制。
- **驗收標準 (Acceptance Criteria)**:
  1. 針對擴縮容等指令，產出詳細的變更計畫 (Plan)。
  2. 強制作為包裹產出對應的反向回滾腳本 (Rollback script)。
  3. 送審前，介面允許 SRE 人工覆寫指令或新增安全驗證步驟。
- **操作流程**: 1. 從首頁 AI Chat 發起擴容請求。 2. AI 產出 Plan 與 Rollback。 3. **AI重置/人工微調**: 「局部重置」回滾腳本加入安全檢查，並人工修改擴展上限。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 產生左右分欄的變更計畫 (Plan) 與帶有綠色防護盾的回滾腳本。**後續引導**：引導點擊「送出審批 (Submit for Approval)」。
  - **失敗 (Failure)**: 送出按鈕反灰鎖死，提示「回滾腳本邏輯有誤，無法保證系統安全」。**後續引導**：提示「請點擊局部重置要求 AI 重寫回滾邏輯」，或「邀請平台工程師同行審閱」。
- **BDD**: `Given` 基礎變更 Plan `When` 人工修改實例數至 10 並局部重置回滾邏輯 `Then` 新包裹包含更新的數字與增強的回滾腳本。

#### F3. 行動端高風險操作審批閘門

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Ben (SRE, `SRE`), Karen (平台擁有者, `Platform_Owner`)
  - **協作細節**: Ben 在桌面端送出刪除資料庫指令；Karen 隨即在手機端收到推播。Karen 發現影響太大，在手機端 Reject 並寫下「請改用備份替換」，Ben 即時收到退回理由。
- **使用者需求/目標 (User Goal)**: 讓高階主管能隨時隨地安全地審核高風險的基礎設施操作。
- **驗收標準 (Acceptance Criteria)**:
  1. 審批者能透過行動裝置推播於 Mobile Web 檢視變更影響分析。
  2. 強制要求手機端生物辨識 (如 FaceID) 進行二次授權。
  3. 支援 Reject 功能，並要求填寫退回理由以利後續修改。
- **操作流程**: 1. 手機端收到推播登入。 2. 檢視高風險變更內容。 3. **AI重置/人工微調**: Karen 可選擇 Reject，並人工在退回理由中寫下修改要求讓 Agent 重做。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 手機畫面顯示綠色大勾勾「授權成功」並伴隨短暫震動。**後續引導**：提示「點擊查看變更單即時執行進度」。
  - **失敗 (Failure)**: 手機畫面顯示紅叉「授權被拒」或「操作逾時失效」。**後續引導**：提示「請在意見框內填寫退回理由讓 SRE 重新調整」，或「致電 SRE 負責人說明原因」。
- **BDD**: `Given` 變更單 Pending `When` Karen 人工填寫「需補上離峰時段執行」並 Reject `Then` 變更取消，SRE 收到重置要求。

---

### G. 雲端安全態勢與策略顧問 (Cloud Security Posture & Policy Advisory)

#### G1. 全局安全態勢與合規持續檢視 (CSPM & Continuous Compliance)

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Fiona (資安審查員, `Security_Reviewer`), Alex (雲端架構師, `Project_Architect`)
  - **協作細節**: Fiona 觸發全域掃描，涵蓋 Network exposure、Storage access、Encryption 與 Audit logging 配置。系統產出 Remediation Plan 與 IaC patch，Alex 套用代碼後，由於涉及高風險修復，強制進入 Human Approval Gate 由 Fiona 審批。
- **使用者需求/目標 (User Goal)**: 持續監控雲端資源設定是否符合資安合規標準，並快速產出自動化修復計畫與代碼。
- **驗收標準 (Acceptance Criteria)**:
  1. 系統必須能深度檢視並報告 Network exposure (如 Public SG)、Storage access、Encryption (at rest/transit) 以及 Audit logging 是否正確啟用。
  2. 針對掃出的弱點，必須產出對應的 Remediation Plan 與具體可執行的 IaC Patch。
  3. 任何被標記為高風險 (High-Risk) 的修復執行前，強制必須通過 Human Approval Gate 審批機制。
- **操作流程**: 1. 登入全域安全看板。 2. 啟動合規性深度掃描。 3. **AI重置/人工微調**: 人工修改 IaC patch 的參數，重置修復計畫。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 顯示滿版綠盾牌與高分評分，產出防護清單。**後續引導**: 引導點擊「一鍵套用 IaC Patch 並送出高風險修復審批 (Human Approval Gate)」。
  - **失敗 (Failure)**: 亮紅燈警示掃描受阻或權限不足。**後續引導**: 提示「請點擊重新綁定 IAM Scanner Role」。
- **BDD**: `Given` 掃描發現 S3 bucket 缺乏加密 `When` AI 產生 IaC Patch 並由 SRE 點擊套用 `Then` 系統攔截部署，觸發 Human Approval Gate 等待 Fiona 審批。

#### G2. IAM / RBAC 與最小權限策略 (Least-Privilege & Identity Security)

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Fiona (資安審查員, `Security_Reviewer`), Ian (開發者, `Developer`)
  - **協作細節**: Fiona 掃描出 Ian 的專案中有過度授權的帳號。系統自動指派修復任務給 Ian；Ian 透過 AI 產出 Least-privilege 建議，修復單送交 Fiona 的 Approval Gate 確認。
- **使用者需求/目標 (User Goal)**: 嚴格審視 IAM 與 RBAC，找出過度授權的角色並落實最小權限原則。
- **驗收標準 (Acceptance Criteria)**:
  1. 深度檢視現有 IAM / RBAC 權限，找出過度授權 (Over-permissive) 的帳號或角色。
  2. 基於歷史存取紀錄自動產出極簡化的 Least-privilege Policy 建議。
  3. 若建議縮減的權限涉及核心運算資源存取，強制進入 Human Approval Gate 審核。
- **操作流程**: 1. 進入 IAM 審查區。 2. 執行過度授權分析。 3. **AI重置/人工微調**: 「局部重置」排除特定開發人員，人工加註安全標籤。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 清單過濾動畫完成，顯示綠色標語「已精簡為安全權限範圍」。**後續引導**: 引導點擊「生成 Least-Privilege Policy 並送出審批」。
  - **失敗 (Failure)**: 畫面跳出紅色對話框「讀取歷史存取紀錄權限不足」。**後續引導**: 提示「請點擊授權請求按鈕申請跨帳號權限」。
- **BDD**: `Given` 掃出 Action 為 "*" 的權限 `When` AI 產出 Least-privilege 建議並人工選擇套用 `Then` 修復行為被鎖定，等待 Fiona 透過 Human Approval Gate 核准。

#### G3. 自動化策略防護網 (Policy Guardrails & Policy-as-Code)

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Fiona (資安審查員, `Security_Reviewer`), Elena (平台工程師, `Platform_Engineer`)
  - **協作細節**: Fiona 用自然語言定義 Policy guardrails；AI 轉化為 Policy-as-Code (如 Rego)。Elena 負責將代碼整合進 CI/CD 中，雙方在 IDE 共同確保策略不會誤擋正常發布。
- **使用者需求/目標 (User Goal)**: 建立自動化的 Policy Guardrails 以防止違規部署，將資安規範代碼化。
- **驗收標準 (Acceptance Criteria)**:
  1. 支援將自然語言的合規要求轉化為 Policy-as-Code (OPA Rego 或 AWS Config)。
  2. 建立防禦性的 Policy Guardrails，在部署階段主動攔截不合規的 IaC 操作。
  3. 允許在 IDE 介面內由資安人員人工修改條件式與正則表達式。
- **操作流程**: 1. 進入 Guardrail 設定區。 2. 輸入防禦規則要求。 3. **AI重置/人工微調**: 「全部重置」改產出 AWS Config 規則，人工修改正則表達式。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 代碼編輯區塊右上角亮起綠燈，模擬終端機顯示 `PASS`。**後續引導**: 引導點擊「將此策略合併至防護網生效」。
  - **失敗 (Failure)**: 終端機報出紅色編譯錯誤，高亮提示語法不符之處。**後續引導**: 提示「請在 IDE 內人工修復語法」，或「點擊 AI 智能除錯」。
- **BDD**: `Given` AI 生成 OPA Policy `When` Fiona 人工修改正則並點擊測試 `Then` 系統回報防護策略測試通過。

---

### H. MCP 與 Skill 管理 (MCP & Skill Management)

#### H1. 內部自定義 API 工具註冊與解析

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Elena (平台工程師, `Platform_Engineer`), Jack (平台管理員, `Platform_Admin`)
  - **協作細節**: Elena 貼上 API Schema 並透過 AI 縮減 Prompt；提交後，Jack 負責審查該 API 的呼叫頻率與資源消耗，確認無安全疑慮後才核准上架。
- **使用者需求/目標 (User Goal)**: 快速將內部自定義的 API 工具註冊為 AI Agent 可呼叫的 Skills。
- **驗收標準 (Acceptance Criteria)**:
  1. 能正確解析 OpenAPI Schema 或內部 API 規格檔案。
  2. 將 API 參數轉譯為 Agent 能準確理解的 System Prompt。
  3. 註冊前進行自動 Health Check，失敗則拒絕上架。
- **操作流程**: 1. 進入 MCP 目錄。 2. 貼上內部 API 端點。 3. **AI重置/人工微調**: 「全部重置」縮短 Prompt，人工編輯必填欄位備註。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 工具卡片轉為鮮豔的 `ACTIVE` 狀態，並打上綠色勾勾。**後續引導**：引導點擊「立即在 AI Chat 中進行測試呼叫」。
  - **失敗 (Failure)**: 卡片劇烈震動並顯示紅字「Schema 格式解析失敗」。**後續引導**：提示「請檢查 YAML/JSON 語法是否合規」，或「聯絡 API 開發者確認文件規格」。
- **BDD**: `Given` 500 字 Prompt `When` 點擊全部重置精簡並人工補上 `region` 限制 `Then` 成功註冊且解析正確。

#### H2. AI Agent 存取邊界與權限審核

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Jack (平台管理員, `Platform_Admin`), Ben (SRE, `SRE`)
  - **協作細節**: Jack 在後台將某危險工具強制設為 `Read-only`。當 Ben 的 Agent 試圖執行該工具的 Write 操作時，Agent 會提示 Ben 該操作已被 Jack 封鎖並留下紀錄。
- **使用者需求/目標 (User Goal)**: 嚴格控管 AI Agent 對各項工具的存取權限，避免越權操作。
- **驗收標準 (Acceptance Criteria)**:
  1. 平台管理員可於介面檢視每個工具的風險等級建議。
  2. 支援強制綁定全域最高權限邊界 (如僅限 Read-only)。
  3. 當 Agent 試圖超越權限呼叫工具時，阻擋並在 Audit Log 留下攔截紀錄。
- **操作流程**: 1. 登入後台審查區。 2. 檢視新註冊 MCP。 3. **AI重置/人工微調**: 「局部重置」要求重新判斷風險，或人工設定為 `Read-only`。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 畫面頂端彈出綠色橫幅「權限邊界已成功鎖定為全域生效」。**後續引導**：引導點擊「返回 MCP 目錄檢視其他工具」。
  - **失敗 (Failure)**: 跳出黃色警示框「該設定與現有全域安全策略衝突」。**後續引導**：提示「請檢視現有全域策略清單」，或「聯絡資安主管 (Fiona) 確認例外豁免條款」。
- **BDD**: `Given` AI 建議給予 Deploy 權限 `When` Jack 人工強制修改為 Read-only `Then` 所有 Agent 呼叫該工具時失去寫入能力。

#### H3. 全域 MCP 工具與 Skill 註冊生命週期管理 (MCP & Skill Lifecycle)

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Elena (平台工程師, `Platform_Engineer`), Jack (平台管理員, `Platform_Admin`)
  - **協作細節**: Elena 註冊新的 MCP server 與雲端連接器 (Connectors)，並設定其讀寫權限範圍。系統進行依賴性與健康檢查後，交由 Jack 進行啟用審批。審批通過後，該工具正式納入 Agent Routing Layer 供 AI 選用。
- **使用者需求/目標 (User Goal)**: 統一管理與配置 AI 依賴的所有外部工具與工作流，確保 Agent 只能在安全審批後的邊界內自動調用工具。
- **驗收標準 (Acceptance Criteria)**:
  1. 支援管理包含 MCP servers, Tools, AI Skills, Cloud provider connectors 以及 Reusable workflows 的完整生命週期 (註冊、啟用/停用、版本控管)。
  2. 內建自動化的相依性檢查 (Dependency Check) 與定期的健康檢查 (Health Check)，失效的工具將被標記並停用。
  3. 將所有合規工具納入 **Agent Routing Layer**，使 AI 能根據意圖自動且安全地選用合適工具，執行 read-only 分析或觸發經審批 (Human Approval Gate) 的維運操作。
- **操作流程**: 1. 進入 MCP 與 Skill 管理中心。 2. 新增或更新 MCP Server。 3. **AI重置/人工微調**: 人工調整工具權限邊界，限制其僅能執行 Read-only 動作。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 新工具卡片亮起綠燈顯示「ACTIVE」，並標示「Routing Layer 已接入」。**後續引導**: 引導點擊「在 Sandbox 測試 Agent 工具調用」。
  - **失敗 (Failure)**: 卡片亮紅燈顯示「Health Check 失敗」或「相依性缺失」。**後續引導**: 提示「請點擊檢視錯誤日誌」或「重新配置雲端連接器憑證」。
- **BDD**: `Given` Elena 註冊了一個具備修改權限的 Cloud Connector `When` AI 自動測試連線成功，但 Jack 人工在審批階段將其降級為 Read-only `Then` Agent 在 Routing Layer 呼叫該工具時僅能執行查詢動作。

### J. 身分認證與基於角色的權限管理 (Identity Authentication & Role-Based Access Control)

> **實作狀態標註**（Q1＝擴充需求）：✅ 已做｜⏳ 部分｜❌ 未做／下期。下列 AC 保留產品目標，並標明現況。

#### J1. 統一登入入口與安全憑證驗證

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: 平台內所有使用者 (如 Alex, Fiona, Ian 等), Jack (平台管理員, `Platform_Admin`)
  - **協作細節**: 所有使用者必須通過統一登入入口完成身分認證以獲取 JWT。Jack 負責平台身分政策（密碼複雜度、MFA 等屬下期強化）。
- **使用者需求/目標 (User Goal)**: 擁有一個安全的登入頁面，驗證身分並開始系統工作，保障帳戶與系統資料的安全。
- **驗收標準 (Acceptance Criteria)**:
  1. ✅ 提供獨立的 Desktop Web 登入頁面，支援帳號與密碼欄位輸入。
  2. ✅ 驗證失敗時回傳模糊錯誤提示（如「帳號或密碼錯誤」），降低列舉攻擊風險。
  3. ✅ 驗證成功後於瀏覽器儲存 JWT，並帶時效（Token Expiration）；逾時需重新登入。
  4. ❌ **下期**：密碼複雜度策略、MFA、自助「重設密碼」流程。
  5. ✅／⏳ 帳號被停用（`is_active=false`）時拒絕登入（403）；**待授權／無角色**帳號見 J5（可登入但功能全鎖或僅見「等待授權」頁——實作時二擇一，預設採「可登入＋等待授權畫面」）。
- **操作流程**: 1. 訪問平台登入頁。 2. 輸入帳號密碼並點擊「登入」。 3. 失敗時修正憑證或聯絡管理員（重設密碼屬下期）。
- **系統回饋 (System Feedback)**:
  - **成功 (Success)**: 綠色 Toast「✔ 登入成功，正在跳轉...」→ 有角色者進入工作區；無角色／待授權者進入「等待管理員授權」頁（J5）。
  - **失敗 (Failure)**: 紅色警告「✘ 登入失敗：帳號或密碼錯誤」或「該帳號已被停用」。
- **BDD**: `Given` 使用者未登入 `When` 輸入正確憑證點擊登入 `Then` 派發 JWT；若已有正式角色則導向工作區，若為待授權則導向等待授權頁。

#### J2. 基於角色細項權限的頁面可見性控制

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Ian (`Developer`), David (`FinOps_Analyst`), Fiona (`Security_Reviewer`)
  - **協作細節**: 登入後 Sidebar／路由依 **角色 × Story 細項**（檢視／編輯／審核）動態計算；三旗標皆空則隱藏該功能。Ian 企圖進入無權限的 Admin 頁時被擋。
- **使用者需求/目標 (User Goal)**: 確保不同使用者僅能訪問與其職責相關的選單與工作區，落實 SoD 與最小權限。
- **驗收標準 (Acceptance Criteria)**:
  1. ✅ 側邊選單依 `/me` 回傳之 permissions map 動態顯示／隱藏（非僅硬編 Role 名稱）。
  2. ✅ 手動改 URL 繞過時，前端 RouteGuard 攔截並導向 403。
  3. ✅ 後端 API 以 `require_story_action`／`require_arch_action` 覆核，無權限回傳 403。
  4. ✅ 架構圖生成（A1／A2／A4）以 A1 為準、三者同步（見 J4／role-permission-design）。
  5. ❌ **下期**：待授權使用者（無正式角色）僅能看到「等待授權」與登出，不得進入任何業務模組。
- **操作流程**: 1. 登入進入主畫面。 2. 檢視左側選單。 3. 管理員調整細項矩陣後，使用者重新整理即可更新可見範圍。
- **系統回饋 (System Feedback)**:
  - **成功**: 僅渲染授權選單。
  - **失敗**: 「403 拒絕存取」；待授權則顯示等待授權說明。
- **BDD**: `Given` Ian 為 Developer 且對 J3a 三旗標皆空 `When` 修改 URL 訪問 `/admin/users` `Then` RouteGuard 與後端皆回 403。

#### J3. 管理員專屬的使用者管理（角色指派／啟停用／刪除／授權申請核准）

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Catherine (`Project_Admin`), Jack (`Platform_Admin`), Ian (`Developer`), 新註冊待授權使用者
  - **協作細節**: 管理員於「使用者設定」頁檢視名單、指派／變更正式角色、啟停用、**刪除使用者**，並處理 J5 的角色授權申請；異動寫入稽核紀錄供 Fiona 審查。
- **使用者需求/目標 (User Goal)**: 方便檢視所有帳戶，依職責調配權限，核准新註冊者之角色申請，並能移除不再需要的帳號。
- **驗收標準 (Acceptance Criteria)**:
  1. ✅ 管理員專屬面板列出使用者、目前角色、啟用狀態。
  2. ✅ 可變更使用者角色（allowlist 11 角色）；目標使用者重新整理後生效。
  3. ✅ 可啟用／停用帳號；停用後無法登入。
  4. ✅ 防護：不可移除最後一位具 J3a.edit 的管理員。
  5. ⏳ 稽核：後端已記錄角色變更等事件；❌ **下期** 完整 Audit Log 瀏覽 UI。
  6. ❌ **下期／本迭代目標**：管理員於 **「授權申請」** 專頁（`/admin/authorization-requests`）檢視待處理列表，可核准或拒絕（見 J5）；核准後才寫入正式 `role`。
  7. ❌ **下期／本迭代目標**：管理員可刪除使用者（須先停用、無擁有架構圖；見 `construction/j/functional-design/`）。
- **操作流程**: 1. 進入「使用者設定」或「授權申請」。 2. 指派角色／啟停用／核准或拒絕申請／刪除。 3. 確認提示後生效。
- **系統回饋 (System Feedback)**:
  - **成功**: 「✔ 使用者角色已更新為 SRE」／「✔ 已核准授權申請」／「✔ 已刪除使用者」。
  - **失敗**: 「✘ 不能將最後一位管理員降級或刪除」等。
- **BDD**: `Given` Jack 在授權申請頁看到待處理申請（申請角色＝SRE）`When` 點擊核准 `Then` 該使用者 `role` 變為 `SRE`，重新整理後 Sidebar 依矩陣更新；`Given` Jack 刪除已停用且無擁有圖之帳號 `When` 確認刪除 `Then` 該使用者無法再登入且列表不再出現。

#### J4. 細粒度角色-故事權限矩陣編輯與預設還原

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: Catherine (`Project_Admin`), Fiona (`Security_Reviewer`), Jack (`Platform_Admin`)
  - **協作細節**: 管理員編輯各角色對各 User Story 的檢視／編輯／審核；變更記錄稽核供 Fiona 審查。
- **使用者需求/目標 (User Goal)**: 靈活管控角色×功能細項權限，並能一鍵恢復設計預設。
- **驗收標準 (Acceptance Criteria)**:
  1. ✅ 提供 `RolePermissionsPage` 矩陣 UI。
  2. ✅ 可勾選並儲存 can_view／can_edit／can_review。
  3. ✅ **A1＝A2＝A4** 在 UI 合併為一欄「架構圖生成」，儲存時三列同步。
  4. ✅ Pillar J 在矩陣 UI **僅顯示 J3a（使用者設定）、J3b（細項設定）**；J1／J5 不進細項 UI（登入／申請流程另案）。
  5. ✅ 「還原為系統預設值」呼叫 `/api/auth/role-permissions/reset-defaults`。
  6. ✅ 儲存後使用者重新整理即依新矩陣生效。
- **操作流程**: 1. 進入「細項設定」。 2. 修改勾選後儲存。 3. 需要時還原預設。
- **系統回饋 (System Feedback)**:
  - **成功**: 「✔ 角色權限保存成功」或「✔ 權限已重置為預設值」。
  - **失敗**: 「✘ 儲存失敗，請檢查網路連線」。
- **BDD**: `Given` Catherine 在細項設定將 Developer 對某功能的 review 開啟並儲存 `When` 該 Developer 重新整理 `Then` `/me` permissions 反映新值。

#### J5. 自助註冊、角色介紹與授權申請（無預設角色）

- **多角色協作 (Multi-Role Collaboration)**:
  - **參與角色**: 新註冊使用者, Jack (`Platform_Admin`), Catherine (`Project_Admin`)
  - **協作細節**: 新使用者註冊時**不賦予任何正式角色**。註冊流程詢問申請角色並展示功能摘要；管理員於 **授權申請專頁** 核准後才生效；亦可刪除帳號。
- **使用者需求/目標 (User Goal)**: 能自助開通帳號並清楚選擇目標角色；在獲准前不誤用權限；管理員可把關授權與清理帳號。
- **驗收標準 (Acceptance Criteria)**:
  1. ❌ **下期／本迭代目標**：註冊 API／UI **不得**預設指派 `Developer` 或其他正式角色；帳號狀態為「待授權」（例如 `role` 空值或 `Pending`，且不在 11 角色 allowlist 生效集）。
  2. ❌ 註冊頁展示 11 個正式角色的**介紹**與**可使用功能摘要**（來源：personas + 預設矩陣摘要）。
  3. ❌ 使用者必選一個「申請角色」後才能提交註冊；系統建立帳號 + **授權申請單**（申請人、申請角色、時間、狀態＝pending）。
  4. ❌ 待授權使用者登入後僅見等待授權說明與登出；業務 API 一律 403。
  5. ❌ 管理員於 **授權申請** 專頁檢視待處理列表，可核准（寫入正式 role）或拒絕（刪除帳號）；核准後走 J2 可見性。
  6. ❌ Pending 期間可改選申請角色（見 Functional Design BR-03）。
  7. ⏳ 現況對照：目前 `/register` **會直接指派 `Developer` 且立即生效**——與本故事衝突，實作時需改掉。
- **操作流程**: 1. 開啟註冊頁 → 填帳密 → 選申請角色 → 送出。 2. 登入後「等待授權」頁。 3. Jack／Catherine 於 **授權申請** 頁核准或拒絕。
- **系統回饋 (System Feedback)**:
  - **成功（註冊）**: 「✔ 註冊成功，已送出角色授權申請，請等待管理員核准」。
  - **成功（核准）**: 申請人下次進入可見對應選單。
  - **失敗**: 「✘ 該帳號已存在」／「✘ 請選擇欲申請的角色」。
- **BDD**: `Given` 新使用者完成註冊並申請 `SRE` `When` 其立即登入 `Then` 無業務選單且 role 非正式角色；`When` Jack 核准後該使用者重新整理 `Then` role=`SRE` 且 Sidebar 依矩陣顯示。

---
