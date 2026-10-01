# 手動測試案例 — C1 估價上傳改版

> Intent：`260916-estimate-upload-rework`  
> 由 `tcms-test-cases` stage 產出。本檔是手動案例的**授權來源**。

---

## 覆蓋盤點

外部可觀察行為（本 intent 引入／變更）共 **21 項**。分桶：

| 桶 | 數量 |
|---|---|
| 已自動化 | 17 |
| 待自動化 —— 本 stage 新寫腳本 | 0 |
| 待自動化 —— 本輪 open item | 0 |
| 只能手動 | **4** |
| 無法分類 | **0** |

### 已自動化（17 項）

| # | 行為 | 斷言落點 |
|---|---|---|
| A-1 | 估價表上傳／列表／刪除／RBAC | `backend/tests/test_estimate_intake_api.py` |
| A-2 | CSV／XLSX 解析與無法辨識列 | `tests.test_estimate_parser`／`test_estimate_validator` |
| A-3 | 解析器邊界（無 httpx／sqlalchemy／fastapi） | `scripts/validate_cost_calculator_boundary.py` |
| A-4 | 定價埠邊界 | `scripts/validate_pricing_lookup_boundary.py`＋`tests.test_pricing_*` |
| A-5 | LangGraph runtime（mock） | `tests.test_langgraph_runtime` |
| A-6 | cost advice agent（mock） | `tests.test_cost_advice_agent` |
| A-7 | 舊 cost HTTP／Calculator 退役 | boundary scripts＋discover suite |
| A-8 | secret／contract patterns | `tests.test_repo_contract_secret_patterns` |
| A-9 | `/cost` SPA 上傳→明細工作區 | `frontend/tests/e2e/estimate-workspace.spec.ts` |
| A-9b | 官方估價教學彈窗（FR12） | `frontend/tests/e2e/estimate-workspace.spec.ts`「官方估價教學彈窗顯示截圖與官方連結」 |
| A-10 | 建議面板三態（mock／fixture 路徑） | 同上 e2e＋`EstimateAdvicePanel` 配線 |
| A-16 | SKU 形狀判斷與描述 enrich（mock） | `backend/tests/test_sku_catalog.py`；明細含 `spec_description` 鍵見 `test_estimate_intake_api` |
| A-11–A-15 | repo／env contract、OpenAPI、frontend build | CI `repo-contract`／`unittest`／`npm run build` |

> 不上手動案例覆寫以上行為（TESTING.md §1）。

### 只能手動（4 項）

| # | 行為 | 為何不能自動化 |
|---|---|---|
| M-1 | 真實 OpenRouter 金鑰下 SSE 建議串流跑完 | 每跑一次花錢（LLM） |
| M-2 | 本機缺 OpenRouter 金鑰時 UI／API 降級可讀 | 依賴真實 `.env` 殘值／缺值 |
| M-3 | 定價憑證缺漏時建議流程不整段失敗（FR5.10） | 需真實環境缺憑證；CI mock 遮住此路徑 |
| M-4 | 官方匯出檔上的真實目錄 SKU 解讀成可讀規格（FR13） | 依賴各雲目錄價 API 與憑證；CI mock 不打真端點 |

---

## TC: 真實 OpenRouter 金鑰下 SSE 成本建議串流完整結束

- plan: Cloud-360 C1 Estimate Upload Rework
- priority: P1

### 目的

保護 FR5 真實 LLM 路徑：有有效 OpenRouter 金鑰時，`/cost` 工作區的建議面板必須經 SSE 收到可讀建議並結束，不得永久停在「產生中」。

### 背景

1. 症狀：建議面板一直顯示「產生中」或空白，使用者以為系統當掉。  
2. 錯誤訊息：可能出現瀏覽器 Network 中 `advice/stream` 連線中斷，或面板顯示具體錯誤字串（依實作）。  
3. 既有自動化層為何沒抓到：`ui-regression`／Playwright 與 unittest 皆 mock LLM，**刻意不打真實 OpenRouter**（避免費用與外網 flaky）。

### 受測介面

- API: `POST /api/auth/login` → 200 — 取得 JWT
- API: `POST /api/cost/v1/sets` → 201 — 上傳估價表建立 set
- API: `GET /api/cost/v1/sets/{set_id}/advice/stream` → 200 — SSE 建議串流
- UI: `/cost` — 估價工作區與建議面板

### 前置條件

1. 依 `LOCAL-DEV.md` 啟動 backend＋frontend（或 `deploy/docker-compose.test.yml` 於 :8090）。  
2. `backend/.env`（或 deploy `.env`）設有**有效** `OPENROUTER_API_KEY`（或專案現行等價變數名），並**重啟** backend。  
3. 準備一份可解析的 AWS CSV 估價表（可用 `frontend/tests/e2e/fixtures/` 內樣本）。  
4. 測試帳號具備 C1 view／edit（例如 `admin`／`admin123`）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 登入後開啟 `/cost` | 看到上傳區與估價 set 清單（或空清單提示），頁面標題／側欄仍指向成本估算 |
| 2 | 上傳一份有效 CSV，等待解析完成 | 明細表出現至少一列品項與總額；Network 中 `POST /api/cost/v1/sets` 回 2xx |
| 3 | 在該 set 觸發／等待建議（建議面板） | 面板先進入進行中狀態；`GET .../advice/stream` 出現在 Network 且 status 為 200 |
| 4 | 等待串流結束（可觀察到最後一筆 SSE 或面板離開「產生中」） | 面板顯示至少一則省錢／檢查類建議文字（非空白）；不得無限「產生中」超過 3 分鐘 |

### 通過條件

- 在有效金鑰下，建議面板於 3 分鐘內離開「產生中」，並顯示非空建議文字；SSE 請求為 200。

### 追溯

- 實作：`frontend/src/components/cost/EstimateAdvicePanel.tsx`、`backend/cost/cost_advice_agent.py`、`backend/services/langgraph_runtime.py`
- 自動化對應：無
- PR／commit：本 intent construction
- User story：FR5

### 清理

- 可刪除本次上傳的估價 set（UI 刪除或 API DELETE，若帳號有權）。

---

## TC: 本機缺 OpenRouter 金鑰時建議降級訊息可讀

- plan: Cloud-360 C1 Estimate Upload Rework
- priority: P1

### 目的

保護本機環境殘值路徑：拿掉／未設定 OpenRouter 金鑰時，建議流程須給出可讀失敗或降級說明，不得空白卡住或回 5xx 堆疊頁。

### 背景

1. 症狀：本機開發者清掉金鑰後，建議面板空白或整頁白屏。  
2. 錯誤訊息：應出現面板內錯誤文案或明確「未設定金鑰／無法連線模型」類訊息（以畫面上實際字串為準）。  
3. 既有自動化層為何沒抓到：CI 與 unittest 注入 mock，不讀開發者本機 `.env` 缺值狀態。

### 受測介面

- API: `POST /api/auth/login` → 200 — 取得 JWT
- API: `GET /api/cost/v1/sets/{set_id}/advice/stream` — SSE（可能 4xx／串流內錯誤事件）
- UI: `/cost` — 建議面板錯誤／降級呈現

### 前置條件

1. 本機 backend 可啟動。  
2. 暫時**移除或註解** `OPENROUTER_API_KEY`（或等價變數），**重啟** backend（`--reload` 不監看 `.env`）。  
3. 已有至少一筆可開啟的估價 set（可先在有金鑰時上傳，再撤金鑰；或使用既有資料）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 確認環境變數未載入金鑰（例如後端啟動 log 或 `printenv` 不含該 key） | 金鑰確實缺席 |
| 2 | 登入並開啟 `/cost`，選一筆 set 觸發建議 | 建議面板**不得**永久空白無文案；須出現錯誤／降級說明文字，或明確「無法產生建議」 |
| 3 | 觀察 Network 的 `advice/stream` | 不得以未處理例外導致瀏覽器收到純 500 HTML 堆疊且面板無回饋；若為 4xx／SSE error event，面板須反映可讀訊息 |

### 通過條件

- 缺金鑰時，使用者在建議面板看得到可讀失敗／降級說明；畫面無未捕捉白屏。

### 追溯

- 實作：`frontend/src/components/cost/EstimateAdvicePanel.tsx`、`backend/cost/cost_advice_agent.py`、`backend/services/langgraph_runtime.py`
- 自動化對應：無
- PR／commit：本 intent construction
- User story：FR5

### 清理

- 還原 `.env` 金鑰並重啟 backend。

---

## TC: 定價憑證缺漏時建議流程不整段失敗

- plan: Cloud-360 C1 Estimate Upload Rework
- priority: P2

### 目的

保護 FR5.10：平台定價憑證（AWS／GCP 等）缺漏時，目錄價查詢須降級或略過，**不得**使整段建議產生失敗。

### 背景

1. 症狀：未設定定價憑證時，建議按鈕一無所出或 API 整段 5xx。  
2. 錯誤訊息：建議文字中可註記「目錄價略過／憑證缺漏」，但流程應結束。  
3. 既有自動化層為何沒抓到：pricing 測試以 mock／公開端點為主，不組合「真實缺憑證＋真實 LLM」雙缺狀態。

### 受測介面

- API: `POST /api/auth/login` → 200 — 取得 JWT
- API: `GET /api/cost/v1/sets/{set_id}/advice` → 200 — 建議快照（若實作提供）
- API: `GET /api/cost/v1/sets/{set_id}/advice/stream` → 200 — SSE
- UI: `/cost` — 建議面板

### 前置條件

1. OpenRouter 金鑰**有效**（與 M-1 相同），以便建議主流程可跑。  
2. **刻意不設** AWS IAM／GCP API key 等定價憑證（或設成無效值），重啟 backend。  
3. 已上傳至少一筆估價 set。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 確認定價相關 env 缺漏或無效 | 啟動環境無有效定價憑證 |
| 2 | 於 `/cost` 對該 set 觸發建議並等待結束 | 建議流程結束並顯示至少一般建議內容；不得因定價呼叫失敗而整段 5xx 或永久「產生中」 |
| 3 | 閱讀建議文字 | 若目錄價被略過，文字中可看到降級／略過說明，或建議仍只基於上傳明細（不要求必須含目錄價數字） |

### 通過條件

- 缺定價憑證時，建議仍能完成並在面板顯示非空結果；定價失敗不阻擋整段流程。

### 追溯

- 實作：`backend/cost/cost_advice_agent.py`、`backend/cost/pricing_client.py`、`frontend/src/components/cost/EstimateAdvicePanel.tsx`
- 自動化對應：無
- PR／commit：本 intent construction
- User story：FR5

---

## TC: 官方估價表目錄 SKU 顯示人類可讀規格

- plan: Cloud-360 C1 Estimate Upload Rework
- priority: P1

### 目的

保護 FR13：上傳含目錄形 SKU 的官方匯出檔後，規格欄須顯示目錄查到的描述（或明確仍為原始 SKU），且金額欄不得被目錄價覆寫。

### 背景

1. 症狀：規格欄只見 `2DA5-2C43-66E6`／`DZH…` 這類代碼，使用者無法對照服務。  
2. 錯誤訊息：無固定例外字串；失敗路徑應靜默保留原始 SKU，上傳仍 201。  
3. 既有自動化層為何沒抓到：`test_sku_catalog.py` 只 mock `_lookup`；CI 不呼叫 AWS／GCP／Azure 真實目錄端點，也沒有官方匯出樣本的外網 enrich。

### 受測介面

- API: `POST /api/auth/login` → 200 — 取得 JWT
- API: `POST /api/cost/v1/sets` → 201 — 上傳後明細含 `spec` 與 `spec_description`
- API: `GET /api/cost/v1/sets/{set_id}` → 200 — 讀回同一欄位
- UI: `/cost` — 雲別卡片規格欄
- 外部相依: AWS Price List／GCP Cloud Billing Catalog／Azure Retail Prices（視檔案雲別）

### 前置條件

1. 依 `LOCAL-DEV.md` 啟動 backend＋frontend（後端 :8001、前端 :5173）。  
2. 測試帳號具備 C1 view／edit（例如 `admin`／`admin123`）。  
3. 準備一份官方匯出檔，其中至少一列規格為目錄形 SKU（GCP `XXXX-XXXX-XXXX`、Azure `DZH*`／`Standard_*`、或 AWS 12–20 位英數 SKU，**不是** `m5.large`）。  
4. 若測 GCP，`backend/.env` 可有 `GCP_BILLING_API_KEY`；若測 AWS 可有 IAM。Azure 可不需憑證。改 `.env` 後**重啟** backend。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 登入後開啟 `/cost`，上傳該官方檔並完成解析 | `POST /api/cost/v1/sets` 回 201；明細出現該列 |
| 2 | 在 Network 展開 201 JSON，找該列 | `spec` 仍為檔案內 SKU；`spec_description` 若查到則為非空文字且**不是**數字單價；查不到則為 null |
| 3 | 看雲別卡片規格欄 | 有描述時主列為描述、下方灰色 `SKU …`；無描述時只顯示檔案規格。金額欄數字與上傳檔一致，不得被目錄 hourly 取代 |
| 4 | 再開 `GET /api/cost/v1/sets/{set_id}` | `spec`／`spec_description`／`amount` 與步驟 2 相同 |

### 通過條件

- 上傳為 201；原始 `spec` 與 `amount` 未被目錄價覆寫；查到描述時 UI 主列顯示該文字且副標為 SKU。

### 追溯

- 實作：`backend/cost/sku_catalog.py`、`backend/cost/estimate_intake_service.py`、`frontend/src/components/cost/EstimateCloudCard.tsx`
- 自動化對應：`backend/tests/test_sku_catalog.py`（mock，不替代本案）
- PR／commit：本 intent construction
- User story：FR13

### 清理

- 可刪除本次上傳的估價 set。
