# 架構決策紀錄：C1 估價表上傳的元件設計

本檔為 domain-design 階段的決策紀錄，編號 `ADR-001` 起自成一系列，**與 repo 層級的 `ADR-0001`…`ADR-0018` 是不同序列**——後者位於 `inception/decisions/`，管的是專案層級的長期決策；本檔管的是本 intent 元件分解的設計選擇。引用時請以完整路徑或「domain-design ADR-00N」稱之，避免混淆。

`components.md` 的 Rationale 表是每個元件的速查理由；本檔記錄有取捨的決策及其落選項。

---

## ADR-001：解析器為單一元件，三種格式為其內部讀取器

**Context**

FR1.2 規定每朵雲一種格式：AWS CSV、Azure XLSX、GCP CSV。三者的檔案結構完全不同（兩種 CSV 方言加一種試算表），但下游需要的是同一種正規化結果。FR1.5 另要求依標頭欄位自動判定雲別。FR2.3 要求解析器為純函式並受 CI 的 import 比對機械強制，FR2.4 要求 property-based test 覆蓋。

問題在於：雲別判定與正規化這兩件事是三種格式共用的，而讀取是各自為政的。切在哪裡決定了共用邏輯會不會被複製三份。

**Decision**

單一 `EstimateParser` 元件，擁有雲別判定與正規化；三個格式讀取器為其**內部實作**，不是獨立元件。對外只有一個解析入口，回傳正規化後的逐項明細與雲別判定結果。

判定失敗時回傳 `ambiguous` 而非拋例外——**「判不出來就問使用者」（FR1.5）是協調層的互動，不是純函式的責任**。純函式不能做使用者互動，這條界線若模糊，FR2.3 的零相依約束會被破壞。

**Consequences**

正面：雲別判定與正規化只有一份實作；property-based test 有單一施力點；CI 的 import 比對只需守一個模組路徑。

負面：單一模組同時容納三種格式讀取器，行數會偏高。既有 repo 已有 `gcp_calculator_runner.py`（979 行）、`diagram_builder.py`（1,818 行）這類 god module 的前例，本決定有重蹈的風險。緩解方式是三個讀取器各自獨立成檔、由 `estimate_parser.py` 匯入——**元件邊界與檔案邊界不必一致**，一個元件由多個檔案組成完全合理。

**Alternatives Rejected**

- **三個獨立元件（`AwsEstimateParser` 等）**：雲別判定無處安放——它必須在選定讀取器之前執行，若放進任一解析器會產生循環或需要第四個元件。正規化邏輯也會被複製三份。
- **`CloudFormatDetector` + `EstimateParser` 兩元件**：判定與解析的變更節奏其實相同（雲端改匯出格式時，標頭欄位與內容結構會一起變），拆開只是增加一次跨元件呼叫而沒有換來獨立演化的能力。

---

## ADR-002：機械檢查為獨立的純函式元件

**Context**

FR4 的三項檢查——幣別一致（FR4.1）、數量正值（FR4.2）、總額對帳（FR4.3）——都是對解析結果的確定性計算，不需外部資源。FR4.4 規定存在無法辨識的列時跳過總額對帳。FR4.5 要求其結果與 agent 建議在 UI 上可區分。

曾考慮把它併進協調層，理由是「要知道有沒有無法辨識的列才能決定是否跳過對帳」。這個理由**不成立**：哪些列無法辨識已經在解析結果裡（`EstimateLineItem.parseStatus`），驗證器自己看得到，不需要向協調層詢問。

**Decision**

獨立的 `EstimateValidator` 純函式元件。輸入為解析結果，輸出為標明來源的檢查結論。與 `EstimateParser` 同受零相依約束。

**檢查結果不持久化。** 驗證器是純函式且輸入已持久化，檢視舊版時重算即可。

**Consequences**

正面：檢查結果與明細**永遠一致**——不存在「存下來的結論與現在算出來的不同」這種漂移。這類漂移只能靠人工比對發現，是最難察覺的一類缺陷。新增檢查規則時，舊資料自動套用新規則而不需資料遷移。

負面：每次讀取都重算。以單次上傳最多三份估價表、每份數十列的規模，成本可忽略。

FR4.5 的來源可區分是**呈現層**的要求，本決定不直接滿足它——但獨立元件讓「哪些結論來自確定性規則」在結構上就有明確答案，使 UI 分區有可依據的資料形狀。

**Alternatives Rejected**

- **併入 `EstimateParser`**：兩者變更節奏不同。解析邏輯隨雲端匯出格式變動，檢查規則隨業務判準變動（例如 0.5% 容差日後可能調整）。合併會讓兩種無關的變更共用一個測試面。
- **併入協調層**：會破壞 FR2.3 的零相依約束——協調層要讀 DB、要拋 `HTTPException`，檢查邏輯一旦混進去，CI 的 import 比對就守不住它。

---

## ADR-003：引入 `EstimateSet` 作為上傳批次

**Context**

`requirements.md` 從未使用「批次」一詞，但三條需求的對象都不是單朵雲的估價表：

- FR5.3 跨雲比較——跨越同一次上傳的多朵雲
- FR6.3 歷史清單——列的是「一次上傳」，不是「一份估價表」
- FR6.6 分享——分享的是整組結果，不會只分享其中一朵雲

若資料模型只有 `Estimate`（一朵雲一份），這三件事都沒有可掛載的對象。跨雲比較的結果要存在哪一份 `Estimate` 上？分享三份要建三筆分享關聯而且可能不一致？歷史清單要怎麼把同一次上傳的三份聚在一起？

**Decision**

引入 `EstimateSet` 代表一次上傳（最多三朵雲），由 `EstimateIntakeService` 擁有。`Estimate` 從屬於它，同一批次內每朵雲至多一份。`Advice`、`EstimateShare` 與架構圖外鍵（`diagramId`）皆掛在 `EstimateSet` 上。

**Consequences**

正面：三條需求都有了明確的掛載點。分享的原子性自然成立——分享一次上傳就是分享它的全部內容，不會出現「分享了 AWS 但沒分享 Azure」的半調子狀態。歷史清單就是 `EstimateSet` 的列表。

負面：多一層間接。讀取單朵雲的明細要經 `EstimateSet → Estimate → EstimateLineItem` 三層。這是為了正確性付的合理代價。

另一個後果：**「重新上傳一朵雲」的語意變得需要定義**。使用者在已有批次的情況下再丟一個檔案，是加進現有批次還是開新批次？本站不決定（refined-mockups 的 M3 顯示「＋ 再上傳一份估價表」暗示加進現有批次），交由 functional-design。

**Alternatives Rejected**

- **不引入批次，以「同一時間戳的多份 `Estimate`」隱式分組**：時間戳分組是脆弱的——使用者間隔十秒上傳兩個檔案算不算同一批？這會變成一個永遠調不準的閾值。
- **把跨雲比較的結果存在「主要」那朵雲上**：需要定義「主要」是哪一朵，而任何定義都是武斷的。

---

## ADR-004：建議產生為背景工作，SSE 僅為訂閱者

**Context**

NFR1 容許 3–5 分鐘，NFR2 要求進度指示，refined-mockups 定案為「明細先出、建議以骨架載入等待」。本 repo 已有既成模式：A1（`agent_router.py`）與 A3（`review_router.py`）皆以 `StreamingResponse` + `text/event-stream` 回傳，且在正式部署穿過同一條 Cloudflare Tunnel 運作，因此 SSE 在本環境**已驗證可行**。

但 SSE 的生命週期綁在 HTTP 請求上。若建議產生的工作掛在 generator 內，客戶端斷線時 FastAPI 會取消它——使用者關掉分頁等於丟掉已跑兩分鐘的 LLM 工作，而「建議持久化」的決定在中斷情境下形同虛設。

**Decision**

建議產生為**獨立背景工作**，生命週期與 HTTP 請求解耦。SSE 只是訂閱者：斷線後工作續跑並在完成時寫入，使用者重新進入頁面即可看到結果。

不設獨立的工作狀態實體。`Advice` **自帶狀態屬性**（產生中／完成／失敗），於工作開始時即以「產生中」建立，完成或失敗時就地更新。這取得獨立工作實體的效果而不增加實體數。

**串流必須週期性送出 heartbeat 或階段進度事件。** A1／A3 因逐 token 輸出而天然保持連線活躍，本功能可能靜默數分鐘才吐出結果，靜默的長連線會被反向代理或 Cloudflare 的 idle timeout 切斷。此要求寫入 `AdviceOrchestrator` 的元件職責，同時滿足 NFR2。

**Consequences**

正面：使用者關掉分頁不會浪費 LLM 呼叫；重新進入頁面能看到「仍在產生中」而非空白；建議持久化在所有路徑上都有意義。

負面：`AdviceOrchestrator` 成為唯一跨越 HTTP 請求邊界存活的元件，生命週期比其他元件複雜。**且部署拓樸是單一 FastAPI process**（codekb `architecture.md`）——process 重啟會遺失進行中的工作，`Advice` 的「產生中」狀態可能永久卡住。這需要逾時清理機制，已記入 `components.md` OQ-DD3 傳給下游。

**Alternatives Rejected**

- **工作掛在 SSE generator 內**：見 Context 的中斷問題。
- **單一同步請求等到建議產生**：3–5 分鐘的同步 HTTP 請求在反向代理與 Cloudflare 之下不可靠，且違反 refined-mockups「明細先出」的定案。
- **輪詢 + `AdviceJob` 實體**：輪詢在此場景沒有優於 SSE 之處，而 repo 已有 SSE 的既成模式與驗證。多一個實體也不划算。
- **WebSocket**：`collab_router` 雖有 WS 基礎設施，但那是雙向同步用的。單向推送用 SSE 更貼合，且與 A1／A3 一致。

---

## ADR-005：架構圖綁定為純標籤，估價表授權完全自足

**Context**

兩個問題在此合流。FR6.1 說估價表可選擇性綁定架構圖，但綁定語意從未定義（`requirements.md` OQ3 列出三個未決點：是否影響可見性、解除綁定行為、架構圖被刪時的去向）。FR7.3 要求移除 `cost_service.py:43` 對 `services.collab_router` 私有函式的跨模組引用（OQ4）。

查證發現：`collab_router` 中**與授權有關的函式全部是底線開頭的私有函式**（`_user_can_access_diagram:97`、`_visible_diagrams:130` 等），該模組沒有公開的授權介面可用。因此 FR7.3 說的「改用公開介面」不是現成選項——得先造一個，或改為自有判斷。

這兩個問題是同一件事的兩面：**只要估價表的可見性需要查架構圖權限，就必然需要某種跨模組的授權引用。**

**Decision**

綁定為**純標籤**：`EstimateSet.diagramId` 是可為空的外鍵，不影響可見性、不影響生命週期。架構圖被刪除時外鍵設為 NULL，估價批次留存。

授權**完全自足**：`EstimateAccessControl` 只看 `EstimateSet` 的擁有者與其分享名單，不查架構圖權限。RBAC 故事權限仍走既有 `services.rbac` 的公開介面。

**Consequences**

正面：FR7.3 的跨模組私有函式引用**自然消失**——不是改用別的引用，是根本不需要引用。C6 要求的單向相依（`services` 不得反向 import `cost`）維持不變，且新增的耦合為零。不需要新增 `services/diagram_access` 元件，改動面最小。

負面：綁定架構圖變成一個**幾乎沒有行為的欄位**。綁了圖的估價表，能看估價表的人不會因此能看圖、能看圖的人也不會因此能看估價表。使用者可能預期綁定有更多意義。

還有一個較細的後果：**若 A 能看到一個綁定了 B 的私有架構圖的估價批次，UI 會顯示該架構圖的存在**（至少是 id，可能是標題）。這洩漏了「B 有一張這個名字的圖」。緩解方式是 UI 只在呼叫者本身有權看該圖時才顯示圖的標題，否則顯示為「已綁定（無權檢視）」或直接隱藏。此點記入下游。

**Alternatives Rejected**

- **綁定連動可見性**：把兩個資源的授權耦合起來，且立刻需要跨模組的架構圖授權查詢——正是 FR7.3 要消除的東西。
- **綁定連動生命週期（架構圖刪除時估價表一併刪除）**：估價表包含使用者上傳的官方估價資料，其價值不依附於架構圖。因為刪圖而連帶刪除是資料遺失風險。
- **在 `services/` 新增公開授權元件**：技術上可行且是較乾淨的長期解，但本 intent 在自有判斷之下根本不需要它。為了不需要的能力去改動既有 `services` 套件，會擴大本次的改動面與回歸風險。此選項留作日後若真要連動可見性時的前置工作。
- **本期不做綁定**：FR6.1 是明文需求，直接不做需要推翻需求，代價高於保留一個低行為的欄位。

---

## ADR-006：新解析器沿用 `backend/cost/` 套件路徑

**Context**

`scripts/validate_cost_calculator_boundary.py` 是 CI `repo-contract` job 的第三步，以**硬編碼路徑**指向 `backend/cost/cost_calculator.py`，檢查它不得 import `httpx`／`requests`／`sqlalchemy`／`fastapi`，且**檔案不存在即 `return 1`**（CI 紅燈）。FR9.6 要求改指向新解析器模組且不得直接刪除該腳本。

requirements-analysis 的審閱 R-06 指出此處是 CI 阻擋項，作者裁定模組命名屬 domain-design 職責。

另有兩個約束：C4 指出 `backend/` 是 flat module 而非 Python package，以 `sys.path` 為根 import；C6 指出 `backend/cost/` 目前只有一條進入邊（`main.py:13`），此單向相依須維持不被破壞。

**Decision**

新解析器路徑為 **`backend/cost/estimate_parser.py`**。`validate_cost_calculator_boundary.py` 的硬編碼路徑改指向它（一行變更），`ci.yml` 同步調整。

**Consequences**

正面：`main.py:13` 的唯一進入邊不變，C6 的單向相依自動維持。CI 腳本只需改一行。三個格式讀取器可放在同套件下的獨立檔案，不增加進入邊。

負面：**套件名 `cost` 與新職責（估價表上傳）語意已不貼合**。日後讀 code 的人會困惑為什麼上傳功能在 `cost` 底下。這是承受的技術債，記於 `components.md` OQ-DD1，是否重新命名留給後續 intent。

**Alternatives Rejected**

- **`backend/estimate/`（新頂層套件）**：語意最貼切，但會新增第二條進入邊（`main.py` 要多 import 一個 router），破壞 C6 描述的單一進入邊。退場期間同時存在 `cost` 與 `estimate` 兩個套件也會讓「哪些該刪」更難判斷。
- **`backend/cost/parsing/estimate_parser.py`（子目錄）**：`backend/` 是 flat module，多一層子目錄的 import 形式與現況不一致（C4）。且三個讀取器放同層平檔已足夠。
- **沿用原檔名 `cost_calculator.py`，內容整個換掉**：CI 腳本完全不必改，但檔名會嚴重誤導——`cost_calculator` 意為「計算成本」，而新模組是「解析估價表」。本次改版的核心正是**不再計算成本**，沿用這個名字等於在最顯眼處保留被推翻的舊語意。

---

## ADR-007：查價 Port 以「唯讀」為職責定義

**Context**

FR5.5 規定 agent 得經 `pricing_client` 呼叫目錄價端點確認現價，**所得價格只寫入建議文字、不得回寫明細表**（AH-6）。這條界線是整個改版核心價值的守門員——本次改版的前提是「估價一律來自使用者上傳的官方估價表」，一旦查來的目錄價能回寫明細，就退回到系統自動取價的舊模式，而目錄價不含 CUD／RI／Savings Plan 折扣，會污染使用者上傳的真實數字。

**Decision**

`PricingLookup` 為獨立元件，且「**唯讀，其價格輸出不得進入估價明細的寫入路徑**」是它的**職責定義**，不是使用慣例。它只被 `CostAdviceAgent` 依賴，不被任何持有 `EstimateLineItem` 寫入權的元件依賴——這在相依圖上就能看出來。

**2026-09-26 後補（FR13）**：intake 得經獨立元件 `SkuCatalog` 查目錄 SKU 的**人類可讀描述**並寫入 `specDescription`。此例外不含 hourly／單價／小計。`EstimateIntakeService → SkuCatalog` 是允許的相依邊；`EstimateIntakeService → PricingLookup` 仍禁止。

僅限目錄價端點；帳單與用量類 API（Cost Explorer、Cost Management、Billing Export）全面禁止，此禁令是目錄價端點得以使用憑證的對價（ADR-0018 §2）。憑證缺漏或呼叫失敗時降級，不得使建議產生流程失敗。

**Consequences**

正面：AH-6 的價格界線仍有結構性載體。違反它需要新增一條相依邊（`EstimateIntakeService → PricingLookup`），這在 code review 與相依圖上都顯眼。描述查詢走另一條邊，不會被誤讀成「intake 可以取價」。

負面：多一個元件。但它本來就是既有 `pricing_client` 的改造，不是全新構件。

**Alternatives Rejected**

- **併入 `CostAdviceAgent` 作為內部的 LangGraph tool**：AH-6 的界線會退化為註解。日後有人想「順便把查到的現價存起來」時，沒有任何結構阻擋。
- **獨立但不標示唯讀**：與上者實質相同——沒有寫進職責的約束，在重構中會第一個消失。
