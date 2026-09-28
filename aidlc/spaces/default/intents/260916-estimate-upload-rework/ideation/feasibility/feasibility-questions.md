# Feasibility 提問：C1 成本估算改版（上傳估價表）

## Sources

出題前的唯讀查證結果（依 `project.md ## Corrections` 的 feasibility 慣例登錄；題幹與選項引用這些編號）。

- [S1] `backend/cost/` 共 31 個檔。既有估價路徑為「讀架構圖 XML → `diagram_extractor` → `sku_mapper` / `sku_ai_resolver` 對 SKU → `pricing_client` / `pricing_azure` / `pricing_gcp` 取公開價目，或 `azure_calculator_runner` / `gcp_calculator_runner` 以 Playwright 自動填官方 Calculator 並匯出」。
- [S2] `backend/cost/cost_router.py` 有 9 個端點，全部掛在 `/diagrams` 之下：`GET /diagrams`、`GET /diagrams/{id}`、`GET /diagrams/{id}/calculator-export/xlsx`、`GET /diagrams/{id}/calculator-export/csv`、`PUT /diagrams/{id}/region`、`PUT /diagrams/{id}/lines/{mxcell_id}/hours`、`PUT .../sku`、`PUT .../override`、`GET /diagrams/{id}/audit`。
- [S3] `backend/models.py` 有四張 cost 相關資料表：`diagram_cost`、`diagram_cost_line`、`pricing_cache`、`cost_audit_event`。四張都以 diagram 為主鍵關聯基礎。
- [S4] 全 repo 目前**沒有任何檔案上傳端點**：`backend/` 內無 `UploadFile`、無 `File(...)`、無 multipart 處理。唯一的 `zipfile` 使用在 `azure_calculator_runner.py`，是產生 stub xlsx 的輸出路徑，不是讀取使用者檔案。
- [S5] `backend/requirements.txt` 無任何試算表解析套件（無 openpyxl、無 pandas）；亦無 langchain／langgraph。現有 LLM 依賴只有 `claude-agent-sdk`。
- [S6] `backend/services/llm_provider.py` 支援兩種 provider：`openrouter`（設定 `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` 指向 OpenRouter）與 `cli`（用本機 `claude` CLI 登入）。兩者都是驅動 `claude-agent-sdk`，非直接呼叫 HTTP API。
- [S7] 部署路徑為 Cloudflare Tunnel → 自有主機（ADR-0007）。`deploy/` 下**沒有 nginx 設定檔**，因此沒有專案自訂的請求體大小上限；上限由 Cloudflare 與 uvicorn 預設決定。
- [S8] 上游 `intent-statement.md` 已定案且不重問：問題為自動取價太慢或太常失敗；產品邊界為「完全取代」；三種角色共用同一畫面；三類建議（省錢／跨雲比較／品質檢查）皆為必備且不分先後；成功指標為「從上傳到看到建議的時間」；成本 agent 改用 LangGraph，其餘五個模組另開 intent。
- [S9] `project.md ## Mandated` 的 ADR-0006 security baseline 四面向（IAM、encryption、network exposure、audit logging）為 hard constraint，須在本 stage 產出中逐項判定。

---

## Q1. 三朵雲的官方估價表，要支援哪些匯出格式？

三家的官方估價工具匯出格式不同，且各自有多種選項。這題決定解析層的工作量與 [S5] 需要引入哪些新依賴。

- A. 各雲只支援一種主格式（AWS CSV、Azure XLSX、GCP CSV），其餘格式不收
- B. 各雲支援官方提供的所有機器可讀格式（含 JSON、CSV、XLSX），PDF 不收
- C. 連 PDF 也要能讀（需 OCR 或 PDF 文字抽取）
- D. 尚未定義：這輪先確認方向，格式清單留待設計階段逐一確認
- X. Other (please specify)

[Answer]: A

## Q2. 上傳的估價表檔案要不要留存？留多久？

[S4] 顯示這是本系統第一個檔案上傳面。檔案可能含客戶名稱、專案代號、內部服務命名。這題同時決定 ADR-0006 的 encryption 與 audit logging 兩個面向要怎麼判定（[S9]）。

- A. 不留存原始檔：解析完即丟，只存解析後的結構化資料
- B. 留存原始檔一段期間（例如 30 天）供重新解析與稽核，到期自動刪除
- C. 永久留存原始檔，直到使用者主動刪除
- D. 尚未定義
- X. Other (please specify)

[Answer]: A

## Q3. 上傳的估價表內容會不會送進 LLM？

agent 要給三類建議（[S8]），最直接的做法是把解析後的品項送給模型。但估價表可能含可識別客戶的字串，而 [S6] 顯示現行 LLM 呼叫會經過 OpenRouter（第三方）或本機 CLI。

- A. 送完整解析結果：品項、規格、數量、金額全部給模型
- B. 送去識別化後的內容：金額與規格照送，但先移除或遮罩名稱類欄位
- C. 不送內容給模型：建議由規則引擎產生，LLM 只負責把結果寫成自然語言
- D. 尚未定義
- X. Other (please specify)

[Answer]: A

## Q4. 解析失敗或部分失敗時，系統要怎麼表現？

使用者上傳的檔案可能是舊版格式、被手動編輯過、或根本不是估價表。

- A. 嚴格：任一列解析不出來就整份拒收，明確告訴使用者哪一列有問題
- B. 寬鬆：能解析的照用，解析不出的列標記為「無法辨識」並列出，建議照樣產生
- C. 分層：關鍵欄位（金額、品項）缺失才拒收，次要欄位缺失放行
- D. 尚未定義
- X. Other (please specify)

[Answer]: B

## Q5. 既有的 cost 資料與端點要怎麼收尾？

[S2] 的 9 個端點與 [S3] 的 4 張資料表都以 diagram 為關聯基礎。產品邊界已定為「完全取代」（[S8]），但既有資料的處置是獨立問題。

- A. 全部移除：端點、資料表、Playwright runner 一次清掉，既有估價資料不保留
- B. 端點移除但資料表保留：不再寫入，舊資料留著備查，之後再決定
- C. 保留唯讀相容期：舊端點改為唯讀一段時間，新功能上線後再擇期移除
- D. 尚未定義
- X. Other (please specify)

[Answer]: A

## Q6. 上傳的估價表與架構圖還有沒有關係？

現行所有 cost 端點都掛在 `/diagrams/{id}` 之下（[S2]）。改為上傳之後，估價表可以是獨立資源，也可以仍然綁在某張架構圖上。

- A. 完全獨立：上傳的估價表自成一個資源，與架構圖無關聯
- B. 可選綁定：預設獨立，使用者可選擇把一組估價表關聯到某張架構圖
- C. 必須綁定：估價表一定要掛在一張架構圖底下，沿用現有的資源層級
- D. 尚未定義
- X. Other (please specify)

[Answer]: B

## Q7. 跨雲比較建議需要幾朵雲的估價表才成立？

三類建議中「跨雲比較」在只上傳一朵雲時無法成立（[S8]）。這題決定最小可用輸入。

- A. 三朵都要：沒有集滿三份就不產生任何建議
- B. 至少一朵即可：有幾朵就比幾朵，只有一朵時省錢建議與品質檢查照常，跨雲比較標示為資料不足
- C. 至少兩朵：單朵時只給省錢建議與品質檢查，兩朵以上才啟用比較
- D. 尚未定義
- X. Other (please specify)

[Answer]: B

## Q8. LangGraph 的模型存取要走哪條路？

[S6] 顯示現行兩條 provider 路徑都是驅動 `claude-agent-sdk`，不是一般的 HTTP API 呼叫。LangGraph 不吃這個介面，需要一條自己的模型存取路徑。

- A. 沿用 OpenRouter：LangGraph 走 OpenRouter 的 OpenAI 相容端點，共用既有的 `ANTHROPIC_AUTH_TOKEN` 或另設一把
- B. 直接對接 Anthropic API：新增 `ANTHROPIC_API_KEY`，LangGraph 走官方 SDK
- C. 兩條都要能切：沿用現行「provider 可切換」的形狀，讓 LangGraph 也支援兩種來源
- D. 尚未定義
- X. Other (please specify)

[Answer]: A

## Q9. 有沒有「從上傳到看到建議」的時間上限？

成功指標已定為這段時間（[S8]），但沒有數字。解析是本機運算（快），LLM 推論是外部呼叫（慢且不可控）。這題決定要不要設計非同步處理與進度回饋。

- A. 30 秒內：使用者原地等待，同步回應即可
- B. 3 分鐘內：需要進度指示，但仍可在同一個頁面等完
- C. 不設上限但要有進度：改為非同步任務，使用者可離開頁面稍後回來看
- D. 尚未定義：這輪不設時間目標
- X. Other (please specify)

[Answer]: B

## Q10.（覆蓋檢查追問）解析「對錯了」而不是「讀不出來」時，靠什麼發現？

Q4 的寬鬆策略處理的是解析**失敗**的列。但更危險的失敗模式是解析**成功但對錯欄位**——月費讀成年費、數量對到單價、幣別誤判。這類錯誤不會觸發任何錯誤訊息，畫面上的數字看起來完全正常，而 agent 會照著錯的數字給出有自信的建議。上游的成功指標是「時間」（[S8]），沒有任何一項涵蓋正確性。

- A. 顯示總額對帳：把解析出的總額與估價表自身的總計欄並列，不符即警示
- B. 讓使用者逐列確認：解析結果先以可核對的表格呈現，使用者確認後才送進 agent
- C. 交給品質檢查建議：由 agent 的「估價品質檢查」那一類建議去指出不合理的數字
- D. 不特別處理：接受這類風險，錯了由使用者自行發現
- X. Other (please specify)

[Answer]: C

## Consolidated Summary Confirmation

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
