# Domain Design 問題：C1 估價表上傳的元件邊界

本檔為 inception domain-design 的提問與作答紀錄。元件＝**要寫程式碼的邏輯構件**；資料庫、快取、第三方服務是元件的 `external_dependencies`，不是元件本身。部署拓樸不在本站決定（那是 units-generation）。

本站另負責結案 `requirements.md` 明文指派給 domain-design 的兩個開放問題（OQ3 架構圖綁定語意、OQ4 授權來源），以及 requirements 審閱 R-06 被作者裁定延後至本站的新解析器模組命名。

## Sources

- **[S1]** 既有相依方向為 `main → cost → services` 單向，`backend/services/` 之中**沒有任何模組** import `cost.*`。C6 要求維持此單向不被破壞。
- **[S2]** 既有分享模型為**關聯表**：`diagram_shares` 為 secondary table，`UserDiagram.shared_users` 以 `relationship(secondary=diagram_shares)` 表達多對多。FR6.6 要求沿用此模型。
- **[S3]** FR7.3 要移除的跨模組私有函式引用在 `cost_service.py:43`：`from services.collab_router import _user_can_access_diagram, _visible_diagrams`，使用點在 `:50` 與 `:474`。`collab_router.py` 內**與授權有關的函式全部是底線開頭的私有函式**（`_user_can_access_diagram:97`、`_visible_diagrams:130`、`_get_accessible_diagram:148`、`_arch_can_view:113` 等），該模組沒有公開的授權介面可用。
- **[S4]** **本 repo 已有長時 LLM 回應的既成模式**：`services/agent_router.py`（A1）與 `services/review_router.py`（A3）皆以 `StreamingResponse` + `media_type="text/event-stream"` 回傳 SSE。兩者都在正式部署上穿過同一條 Cloudflare Tunnel 運作，因此 SSE 在本部署環境是**已驗證可行**的。
- **[S5]** 既有 `cost_calculator.py` 是唯一零相依的純函式模組，`scripts/validate_cost_calculator_boundary.py` 以**硬編碼路徑**指向它、檔案不存在即 `return 1`（CI 紅燈）。FR9.6 要求改指向新解析器模組，因此**新模組的路徑必須在本站定案**。
- **[S6]** 既有 `cost_pricing_agent.py:43-49` 以 in-process MCP server 暴露 3 個 tool，是 agent 介面的唯一契約定義。FR10.1 要遷移至 LangGraph。
- **[S7]** `pricing_client` 之下有 GCP／Azure／offer parser／boto3 SDK 四條支線，全部收斂到 `pricing_units`。FR9.4、FR9.5 定義了其最小存活集合。
- **[S8]** `backend/` 是 flat module 而非 Python package，以 `sys.path` 為根 import（C4）。
- **[S9]** `requirements.md` 未規定 agent 建議是否持久化。FR6.2 要求每次上傳建立新紀錄且舊紀錄保留，FR6.3 要求可檢視單一舊版的明細——但「明細」是否包含當時的建議，文件沒說。

---

## Q1 — 三朵雲解析器的分解方式

FR1.2 規定每朵雲一種格式（AWS CSV、Azure XLSX、GCP CSV）。FR2.3 要求解析器為純函式，FR2.4 要求 property-based test 覆蓋。

- **A.** 單一 `EstimateParser` 元件，內含三個格式處理分支，對外只有一個 parse 入口
- **B.** 三個獨立元件（`AwsEstimateParser`、`AzureEstimateParser`、`GcpEstimateParser`），各自被服務層直接呼叫
- **C.** 一個 `EstimateParser` 元件（負責雲別判定與正規化），三個格式讀取器為其內部實作，不是獨立元件
- **D.** 兩個元件：`CloudFormatDetector`（雲別判定，FR1.5）與 `EstimateParser`（解析，三格式內含）
- **X.** Other (please specify)

[Answer]: C — 一個 `EstimateParser`（雲別判定＋正規化），三個格式讀取器為其內部實作

## Q2 — 確定性機械檢查的歸屬

FR4 的三項檢查（幣別一致、數量正值、總額對帳）都是純計算，不需外部資源。FR4.5 要求其結果與 agent 建議在 UI 上可區分——這是呈現層的要求，不必然對應元件切分。

- **A.** 併入 `EstimateParser`，解析完順便產出檢查結果（同為純函式層，少一個元件）
- **B.** 獨立的 `EstimateValidator` 純函式元件，輸入為解析結果、輸出為檢查結論
- **C.** 併入服務層協調元件，因為它需要知道「有沒有無法辨識的列」才能決定是否跳過對帳（FR4.4）
- **X.** Other (please specify)

[Answer]: B — 獨立的 `EstimateValidator` 純函式元件，輸入解析結果、輸出檢查結論

## Q3 — agent 建議是否持久化

FR6.2／FR6.3 要求舊紀錄保留且可檢視，但 [S9] 指出文件未說明建議是否算在內。這決定了要不要有一個 `Advice` 實體。

- **A.** 建議隨估價表持久化。檢視舊版時看到的是當時產生的建議，不重新呼叫 LLM
- **B.** 建議不持久化，只存在於本次工作階段。檢視舊版只看得到明細與機械檢查結果，建議區顯示「未保存」
- **C.** 建議不持久化，但檢視舊版時**重新產生**建議（每次檢視都重新呼叫 LLM）
- **X.** Other (please specify)

[Answer]: A — 建議隨估價表持久化；檢視舊版看到當時的建議，不重呼 LLM

## Q4 — 建議產生的非同步機制

NFR1 容許 3–5 分鐘，NFR2 要求進度指示，refined-mockups Q3=A 定案為「明細先出、建議以骨架載入等待」。[S4] 指出本 repo 已有 SSE 的既成模式且在部署環境驗證可行。

- **A.** 沿用 SSE：上傳與解析為一般 HTTP，建議另開一條 `text/event-stream` 連線推送進度與結果
- **B.** 輪詢：建議產生為背景工作，前端定期查詢狀態端點。需要一個 `AdviceJob` 實體記錄狀態
- **C.** 單一同步請求，等到建議產生才回應（最簡單，但 3–5 分鐘的同步請求風險高）
- **D.** WebSocket，沿用 `collab_router` 既有的 WS 基礎設施
- **X.** Other (please specify)

[Answer]: A — 沿用 SSE：上傳解析走一般 HTTP，建議另開 `text/event-stream`

## Q5 — OQ3：估價表與架構圖的綁定語意

FR6.1 說估價表是獨立資源、可選擇性綁定架構圖，但綁定的行為從未定義。`requirements.md` OQ3 明列三個未決點：綁定是否影響可見性、解除綁定的行為、架構圖被刪除時估價表的去向。

- **A.** 純標籤：綁定只是一個可為空的外鍵，不影響可見性、不影響生命週期。架構圖被刪除時外鍵設為 NULL，估價表留存
- **B.** 綁定連動可見性：綁定後，能看該架構圖的人就能看該估價表（FR6.5 的例外）。架構圖刪除時估價表一併刪除
- **C.** 綁定連動可見性但不連動生命週期：可見性如 B，架構圖刪除時外鍵設為 NULL、估價表留存
- **D.** 本期不做綁定。FR6.1 降級為未來能力，`estimate` 不帶架構圖外鍵
- **X.** Other (please specify)

[Answer]: A — 純標籤：可為空的外鍵，不影響可見性與生命週期；架構圖刪除時設 NULL，估價表留存

## Q6 — OQ4：FR7.3 的替代授權來源

[S3] 指出 `collab_router` 沒有公開的授權介面可用，所以「改用公開介面」不是現成選項——得先造一個，或改為自有判斷。

- **A.** 在 `services/` 新增一個公開的授權元件（例如 `diagram_access`），把 `_user_can_access_diagram`／`_visible_diagrams` 提升為其公開函式，`collab_router` 與新 cost 域都改呼叫它
- **B.** 新 cost 域自有判斷：估價表的可見性只看它自己的擁有者與分享名單，完全不查架構圖權限。若 Q5 選 A 或 D（綁定不影響可見性），這個選項就成立
- **C.** 維持引用但改為公開函式：只把 `collab_router` 的那兩個函式去掉底線，不新增元件
- **X.** Other (please specify)

[Answer]: B — 新 cost 域自有判斷：估價表可見性只看自己的擁有者與分享名單，不查架構圖權限

## Q7 — 新解析器模組的路徑（FR9.6 阻擋項）

[S5] 指出 `validate_cost_calculator_boundary.py` 是 CI `repo-contract` job 第三步，硬編碼路徑且檔案不存在即紅燈。requirements 審閱 R-06 把命名裁給本站。[S8] 提醒 `backend/` 是 flat module。

- **A.** `backend/cost/estimate_parser.py`——沿用既有 `cost` 套件，路徑最短，改動 CI 腳本一行
- **B.** `backend/cost/parsing/estimate_parser.py`——新開子目錄容納三個格式讀取器
- **C.** `backend/estimate/estimate_parser.py`——新開頂層套件，與退場中的 `cost` 明確切開
- **D.** `backend/cost/cost_calculator.py`——沿用原檔名與路徑，內容整個換掉，CI 腳本不必改
- **X.** Other (please specify)

[Answer]: A — `backend/cost/estimate_parser.py`，沿用既有 `cost` 套件，CI 腳本改一行

## Q8 — 查價 Port 的元件地位

FR5.5 規定 agent 得經 `pricing_client` 查目錄價，結果只寫入建議文字。[S7] 描述其內部結構，FR9.5 定義最小存活集合。

- **A.** `PricingLookup` 為獨立元件，agent 元件 `depends_on` 它。它同時可被未來其他消費者使用
- **B.** 併入 agent 元件，作為其內部的一個 LangGraph tool，不獨立列為元件
- **C.** 獨立元件，且明確標示為「唯讀查詢 Port」，其輸出不得進入估價明細的寫入路徑（把 AH-6 的界線編碼進元件職責）
- **X.** Other (please specify)

[Answer]: C — 獨立元件且明確標示為唯讀查詢 Port，其輸出不得進入明細寫入路徑

---

## 追問（作答後的歧異分析）

依 stage 檔 Step 3 的強制歧異掃描，Q1–Q8 的組合產生一處會改變元件清單的缺口。

## F1 — SSE 中斷時，建議是否存活

Q3=A 要求建議持久化，Q4=A 採 SSE。兩者在正常路徑上相容，但**客戶端中途斷線**時行為未定：SSE 的生命週期綁在 HTTP 請求上，FastAPI 在客戶端斷線時會取消 generator。若建議產生的工作就掛在該 generator 內，使用者關掉分頁等於丟掉已跑了兩分鐘的 LLM 工作，而 Q3=A 的持久化在中斷情境下形同虛設。

這決定了元件清單：選 A 不需要額外元件；選 B 或 C 需要一個獨立的背景工作元件與（可能的）工作狀態實體。

**附帶必辦事項（不論選哪個）**：A1／A3 的 SSE 是逐 token 持續輸出，本功能則可能靜默數分鐘才吐出結果。靜默的長連線會被反向代理或 Cloudflare 的 idle timeout 切斷，因此串流**必須**週期性送出 heartbeat 或階段進度事件。這同時也正好滿足 NFR2 的進度指示要求。此點寫入元件職責，不另設選項。

- **A.** 建議產生就掛在 SSE generator 內。客戶端斷線即中止，不持久化，使用者需重新觸發
- **B.** 建議產生為獨立背景工作，SSE 只是訂閱者。斷線後工作續跑並在完成時寫入；使用者重新進入頁面就看得到結果
- **C.** 同 B，且另設一個明確的工作狀態實體（`AdviceJob`），使重新進入的頁面能顯示「仍在產生中」而非空白
- **X.** Other (please specify)

[Answer]: B — 建議產生為獨立背景工作，SSE 只是訂閱者；斷線後工作續跑並在完成時寫入

**F1=B 的連帶設計裁決**：B 不要獨立的 `AdviceJob` 實體，但「重新進入頁面時如何知道仍在產生中」仍須有答案。本站的處置是讓 `Advice` 實體**自帶狀態屬性**（產生中／完成／失敗），而非另設第二個實體。這取得 C 的效果卻不增加實體數——`Advice` 從一開始就以「產生中」狀態建立，完成時就地更新。

---

## Consolidated Summary Confirmation

**九個元件**，其中兩個為既有且本期不改（列入目錄僅為使跨元件參照合法）：

| # | 元件 | 層 | 性質 |
|---|---|---|---|
| 1 | `EstimateIntakeService` | 協調 | 新建。上傳、限制把關、解析與檢查的協調、持久化 |
| 2 | `EstimateParser` | 純函式 | 新建。雲別判定＋三格式讀取＋正規化（Q1=C） |
| 3 | `EstimateValidator` | 純函式 | 新建。FR4 三項機械檢查（Q2=B） |
| 4 | `EstimateAccessControl` | 協調 | 新建。擁有者與分享名單（Q6=B） |
| 5 | `AdviceOrchestrator` | 協調 | 新建。背景工作 + SSE 發布（Q4=A、F1=B） |
| 6 | `CostAdviceAgent` | 領域 | 新建。LangGraph 圖與提示（FR10.1） |
| 7 | `PricingLookup` | Port | 改造自 `pricing_client`。唯讀目錄價查詢（Q8=C） |
| 8 | `EstimateAuditLog` | 協調 | 新建。事件層級稽核（FR8） |
| 9 | `EstimateWorkspacePage` | 前端 | 新建。`/cost` 頁 |
| — | `IdentityAndRbac`、`Collaboration` | 既有 | **不改動**。僅因 `User`／`UserDiagram` 被參照而列入 |

**三個推導出來的結構決定，不是你直接選的，請特別看一下：**

**一、引入 `EstimateSet` 作為上傳批次。** 一次上傳最多三朵雲（FR1.3），而跨雲比較（FR5.3）跨越這三者、分享（FR6.6）分享的是整批而非單朵雲、歷史清單（FR6.3）列的也是「一次上傳」。若沒有批次概念，這三件事都沒有可掛載的對象。因此 `EstimateSet`（一次上傳）下轄最多三個 `Estimate`（一朵雲一個），`Advice` 與 `EstimateShare` 都掛在 `EstimateSet` 上。架構圖外鍵（Q5=A）也放在 `EstimateSet`。

**二、機械檢查結果不持久化，每次重算。** `EstimateValidator` 是純函式（Q2=B），輸入是已持久化的逐項明細，所以檢視舊版時直接重算即可，永遠與明細一致。持久化反而會製造「存的結果與現在算出來的不一致」這種只能靠人工發現的漂移。

**三、`Advice` 自帶狀態屬性而非另設 `AdviceJob`。** 見上方 F1 的連帶裁決。

**兩件需要你知道的後果：**

**後果一 —— `backend/cost/` 這個套件名會留下來，但裡面幾乎全換。** Q7=A 把新解析器放在 `backend/cost/estimate_parser.py`。好處是 `main.py:13` 的唯一進入邊不動、CI 腳本只改一行路徑。代價是套件名 `cost` 與新的職責（估價表上傳）語意已經不太貼合，日後讀 code 的人會困惑為什麼上傳功能在 `cost` 底下。

**後果二 —— `EstimateAccessControl` 完全不查架構圖權限（Q6=B），這讓 FR7.3 的跨模組私有函式引用自然消失，但也代表綁定架構圖純粹是個標籤。** 綁了圖的估價表，能看估價表的人不會因此能看圖、能看圖的人也不會因此能看估價表。這正是 Q5=A 的定義，兩題是配套的。

[Answer]: Looks correct

照此產生 components.md、decisions.md、traceability.json。
