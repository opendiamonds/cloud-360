# 手動測試案例 — 260920-orchestration-brain（大腦統一入口）

> 只收「只能手動」桶的行為。分桶依據與全部外部可觀察行為的盤點見同目錄的
> `automation-test-plan.md`。本檔每一案都落在 repo 的三塊結構性盲區之一（所有 LLM 路徑、
> 本機環境殘值、部署環境狀態）：`ui-regression` 的 stack 刻意不設任何模型金鑰
> （`deploy/docker-compose.test.yml` 註解「LLM path stays untouched」），後端測試的路由層一律是
> 替身（`FakeRouter`），所以「真實模型實際判斷了什麼」在 CI 裡沒有任何斷言。
>
> 共用環境（以下各案的前置條件會引用）：
>
> - **本機 stack**：依 `LOCAL-DEV.md` 第 0 節備妥 PostgreSQL（含 pgvector，已套用 `schema_rbac.sql`）與
>   Redis（`REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD`），後端 `cd backend && uvicorn main:app --reload --port 8010`、
>   前端 `cd frontend && npm run dev`。**改了 `backend/.env` 一定要重啟後端**——`--reload` 只監看 `.py`。
> - **模型**：本機 `backend/.env` 設 `APP_ENV=local`、`LLM_PROVIDER=claude-code`、`BRAIN_ROUTER_TIMEOUT_SEC=60`，
>   且 `claude -p "回一個字：好"` 有回應；或設 `LLM_PROVIDER=openrouter` 與有效的 `OPENROUTER_API_KEY`。
>   **每跑一次都會花費模型用量。**
> - **帳號**：本機 `admin`／`admin123`（`APP_ENV=local` 且未設 `CLOUD360_BOOTSTRAP_ADMIN_PASSWORD` 時由
>   `init_db()` 建立）。

## TC: 真實模型下單一意圖的句子被交辦到正確的能力

- plan: 260920 大腦入口：真實模型路徑（手動）
- priority: P1

### 目的

驗證真實模型的意圖路由把三類單一意圖（架構設計、架構檢視、成本分析）各交給對的能力，而不是交錯能力或改為反問。路由錯一類，使用者就會看到別的功能在處理他的需求。

### 背景

後端的路由測試（`test_intent_routing_*`、`test_brain_gateway_turn.py`）全部以 `FakeRouter` 指定「模型回了什麼」，驗的是「模型回了 X 之後系統怎麼做」；e2e 的入口頁（`entry-page.spec.ts`）以 `routeWebSocket` 攔截整條 WS。兩層都**不經過真實模型**，所以「模型會不會把成本問題判成架構設計」在任何 CI 閘門上都沒有斷言。`stories.md`「目前沒有自動化承載層的 AC」一節逐字記載：模型判斷的**品質**不由 e2e 驗。本案是 `NFR1` 的 ≥ 50 筆標註集（`M-1`）落地之前，唯一對真實模型的抽樣檢查。

### 受測介面

- UI: `/` — 大腦入口頁：對話輸入框、脈絡列（作業對象）、工作項卡片
- UI: `/projects/:projectId` — 專案頁：建立系統
- API: `GET /api/hierarchy/projects` → 200 — 脈絡列的專案清單
- 外部相依: LLM 供應商（`claude` CLI 或 OpenRouter）

### 前置條件

1. 本機 stack 與模型依檔頭「共用環境」備妥，以 `admin`／`admin123` 登入。
2. 在 `/projects` 建立專案「電商」，在其下建立系統「電商前台系統」。
3. 在 `/workspace` 開一張任意架構圖並存檔、掛到「電商前台系統」（系統頁「系統的架構圖」區的下拉選該圖）。
4. 回到 `/`，脈絡列選定 專案「電商」／系統「電商前台系統」。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 在入口頁輸入「幫我把這個系統的架構圖加一個 Redis 快取層」並送出 | 出現一張工作項卡片，文字以「已交給架構設計處理」開頭、狀態為「處理中」；**不得**出現「我不確定你指的是哪一件事」 |
| 2 | 等工作項結束 | 卡片狀態變為「完成」或「沒有完成：…」之一；**不得**停在處理中超過 300 秒（`DEADLINE_SECONDS` 架構設計的牆鐘上限） |
| 3 | 輸入「幫我做 Well-Architected 評核，看這張架構圖」並送出 | 出現一張以「已交給架構檢視處理」開頭的卡片；結束時文字為「檢視完成：整體分數」接一個數字與「項發現」 |
| 4 | 輸入「這個系統每個月大概要花多少錢？」並送出 | 出現一張以「已交給成本分析處理」開頭的卡片；**不得**是「已交給架構設計」或「已交給架構檢視」 |
| 5 | 等第 4 步的卡片結束（本機未上傳估價表時） | 卡片文字為「成本分析沒有完成：這張圖尚無估價表，可到成本頁上傳（/cost）」或「成本分析完成…」；**不得**是「你沒有使用成本分析的權限」 |
| 6 | 檢視後端 log | 三輪都**不得**出現 `Traceback` 或 `ERROR`；**不得**出現 `MalformedRouting` |

### 通過條件

- 第 1、3、4 步的卡片前綴分別為「已交給架構設計處理」「已交給架構檢視處理」「已交給成本分析處理」，三者全對才算通過；任一句改為反問或交給別的能力即失敗。
- 第 6 步後端 log 的 `ERROR` 與 `Traceback` 皆為 0 筆。

### 失敗徵兆與對應肇因

| 徵兆 | 可能肇因 |
|---|---|
| 三句都出現「我不確定你指的是哪一件事」 | 模型沒回 `capability` 分數，信心值退化（`OQ-10`）；或 `BRAIN_ROUTER_TIMEOUT_SEC` 過小，路由逾時 |
| 卡片文字是「找不到名為「…」的系統或專案」 | 指涉對象解析回歸，改跑「回歸：已選作業對象時說「評核這個系統」或「那張圖」仍交辦到目前對象」 |
| log 有 `claude CLI 非零結束` | 本機 `claude` 未登入，先跑 `claude` 登入 |

### 追溯

- 實作：`backend/services/intent_routing.py`、`backend/services/intent_routing_context.py`、`backend/services/brain_gateway.py`、`backend/services/work_orchestrator_rules.py`
- 自動化對應：`backend/tests/test_work_orchestrator_flow.py`（替身路由，只驗「模型回了 X 之後」）；`frontend/tests/e2e/entry-page.spec.ts`（攔截層）
- PR／commit：PR #650（head `48f6349`）
- User story：US1.1（AC1.1.1、AC1.1.2）、US10.1（AC10.1.1）；`NFR1`／`M-1` 的抽樣

## TC: 真實模型下語意不明的句子改為反問並列出候選，不建立工作項

- plan: 260920 大腦入口：真實模型路徑（手動）
- priority: P1

### 目的

驗證真實模型面對判不出意圖的句子時，系統改為反問、列出可選的候選，且在使用者回答前不建立任何工作項；以及按「都不是」之後不產生任何結果。

### 背景

`AC1.2.1` 的自動化（`test_brain_gateway_turn.py::ClarifyTest`、`entry-page.spec.ts` E19）以替身直接送出「低於門檻的分數」，驗的是門檻之後的行為。真實模型對一句模糊的話**會不會**給出低分、給出的候選**是否合理**（例如列出三個不相干的能力，或把同一個能力列兩次），需要人的判斷，CI 無從斷言。本機驗證（2026-11-10）曾以「幫我看一下這個」觀察到正確反問並列三個候選。

### 受測介面

- UI: `/` — 大腦入口頁：反問提示、候選按鈕、「都不是，我再講一次」按鈕、工作項區
- 外部相依: LLM 供應商（`claude` CLI 或 OpenRouter）

### 前置條件

1. 本機 stack 與模型依檔頭「共用環境」備妥，以 `admin`／`admin123` 登入。
2. 脈絡列為「尚未選定」（重新整理入口頁後若有先前的作業對象，從脈絡列清除）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 輸入「幫我看一下這個」並送出 | 出現提示「我不確定你指的是哪一件事」與 2 個以上的候選，每個候選旁有「就是這個」按鈕 |
| 2 | 逐一閱讀候選說明 | 每個候選都對應一個不同的能力；**不得**有兩個候選說的是同一件事 |
| 3 | 檢視工作項區 | 工作項數為 0；**不得**出現「已交給」開頭的卡片 |
| 4 | 按「都不是，我再講一次」 | 反問提示消失；工作項數仍為 0；脈絡列仍顯示「尚未選定」（作業對象不變）；**不得**出現任何錯誤訊息 |
| 5 | 輸入「請幫我畫一張電商網站的雲端架構圖」並送出 | 出現以「已交給架構設計處理」開頭的卡片，或改問「你指的是哪一個？」要求選對象；**不得**再出現「我不確定你指的是哪一件事」 |

### 通過條件

- 第 1 步出現反問且候選數 ≥ 2；第 3、4 步工作項數為 0；第 5 步明確意圖不再被當成模糊句。四項全成立才算通過。
- 第 2 步若候選重複或與句子毫無關聯，記為失敗並附截圖（這是本案唯一需要判斷的步驟）。

### 追溯

- 實作：`backend/services/intent_routing_predicate.py`、`backend/services/brain_gateway.py`、`frontend/src/components/brain/ClarifyCandidates.tsx`
- 自動化對應：`backend/tests/test_brain_gateway_turn.py::ClarifyTest::test_intent_clarify_select_and_none`（替身路由）
- PR／commit：PR #650（head `48f6349`）
- User story：US1.2（AC1.2.1、AC1.2.3；AC1.2.2「選定候選後交辦」由自動化層承擔，本案不重複）

## TC: 真實模型下一句含兩件事時拆成兩個工作項

- plan: 260920 大腦入口：真實模型路徑（手動）
- priority: P2

### 目的

驗證真實模型能把一句含兩個需求的話拆成兩個意圖，畫面出現兩張各自的工作項卡片，而不是只處理其中一件或改為反問。

### 背景

`AC5.1.1` 的自動化（`test_work_orchestrator_flow.py::ReplyFirstTest`、`intent_routing_predicate` 的 `P6` property）在替身給出兩個槽位之後驗「兩個槽位 → 兩個工作項」。模型**會不會**把一句話切成兩個槽位只有真實模型能回答；本機驗證把「多意圖」列為未驗。

### 受測介面

- UI: `/` — 大腦入口頁：工作項卡片、常駐工作項區
- 外部相依: LLM 供應商（`claude` CLI 或 OpenRouter）

### 前置條件

1. 依「真實模型下單一意圖的句子被交辦到正確的能力」的前置條件 1–4 備妥（作業對象為已掛圖的「電商前台系統」）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 輸入「幫我把這張架構圖加上 CloudFront，然後估一下這個系統每個月要花多少錢」並送出 | 出現 2 張卡片：一張以「已交給架構設計處理」開頭、一張以「已交給成本分析處理」開頭 |
| 2 | 在架構設計那張卡片結束前，檢視成本那張卡片 | 狀態為「等待中」，文字包含「會在」與「完成後開始」（說明它在等架構設計）；**不得**只有 1 張卡片 |
| 3 | 等兩張卡片都結束 | 兩張卡片各自顯示自己的結束狀態（「完成」或「沒有完成：…」）；**不得**一張的失敗原因出現在另一張上 |

### 通過條件

- 第 1 步恰出現 2 張卡片且能力分別為架構設計與成本分析；只出現 1 張、出現反問或兩張同能力皆為失敗。
- 第 2 步成本卡片為「等待中」且說明在等什麼；若它直接開始處理，記為失敗並附截圖（依賴沒有被認出）。

### 追溯

- 實作：`backend/services/intent_routing_predicate.py`、`backend/services/work_orchestrator.py`
- 自動化對應：`backend/tests/test_work_orchestrator_flow.py`（替身路由）
- PR／commit：PR #650（head `48f6349`）
- User story：US5.1（AC5.1.1、AC5.1.2）

## TC: 回歸：已選作業對象時說「評核這個系統」或「那張圖」仍交辦到目前對象

- plan: 260920 大腦入口：真實模型路徑（手動）
- priority: P1

### 目的

回歸案例。驗證作業對象已選定、系統下也有圖時，使用者以指示詞（「這個系統」「那張圖」）或模型照抄脈絡句指涉目前對象，大腦都依目前對象交辦，而不是回「找不到」；同時指名一個真的不存在的系統仍要回「找不到」。

### 背景

本機驗證 F2（2026-11-10，2/2 次重現）：作業對象已選、系統下也有圖，評核與成本仍回

```
找不到名為「系統 #1」的系統或專案。請在上方脈絡列選定作業對象後再說一次。
```

另一次模型填出的對象是整句脈絡（「目前作業對象：專案 #1／系統 #1 下的架構圖」），同樣比不到。根因：路由 prompt 只給模型看得到 `#id` 代號，模型把它抄進 `referent`，閘道以名稱精確比對（`match_referent`）比不到就回找不到，不退回已選對象。修正後（`brain_gateway_rules.refers_to_current_target`）又查出「那張圖」不在指示詞清單、同樣回找不到（build-and-test 第三輪）。

**既有自動化層為何沒抓到**：閘道測試的 `FakeRouter` 由測試者決定 `referent` 填什麼，當時沒有人想到模型會填 `#id` 或照抄脈絡句——替身只會回測試者心中「合理」的值。修正後的 `test_referent_current_target.py` 已把本機觀察到的那幾種寫法收進例子與 property，但**真實模型還會填出什麼寫法**仍只有真實模型能回答；e2e 的攔截層完全不跑後端邏輯。

### 受測介面

- UI: `/` — 大腦入口頁：脈絡列、工作項卡片
- API: `GET /api/hierarchy/projects/{project_id}/systems` → 200 — 脈絡列的系統清單
- 外部相依: LLM 供應商（`claude` CLI 或 OpenRouter）

### 前置條件

1. 依「真實模型下單一意圖的句子被交辦到正確的能力」的前置條件 1–4 備妥。
2. 該系統下**恰好一張**架構圖（多張圖時第一輪會先請你選圖，本案的 Given 不成立）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 確認脈絡列顯示 專案「電商」／系統「電商前台系統」 | 脈絡列兩層都顯示名稱，**不得**是「系統 #」接數字 |
| 2 | 輸入「幫我做 Well-Architected 評核，評核這個系統」並送出 | 出現以「已交給架構檢視處理」開頭的卡片；**不得**出現「找不到名為」 |
| 3 | 等卡片結束 | 文字為「檢視完成：整體分數」接數字與「項發現」 |
| 4 | 輸入「把那張圖的資料庫改成 Multi-AZ」並送出 | 出現以「已交給架構設計處理」開頭的卡片；**不得**出現「找不到名為「那張圖」」 |
| 5 | 輸入「評核不存在的系統XYZ」並送出 | 回覆文字包含「找不到名為「」且包含「不存在的系統XYZ」或「系統XYZ」；**不得**建立工作項 |
| 6 | 檢視後端 log | 第 2、4 步**不得**有 `Traceback` |

### 通過條件

- 第 2、4 步建立了工作項且無「找不到名為」；第 5 步回「找不到名為」且未建立工作項。三者全成立才算通過。

### 失敗徵兆與對應肇因

| 徵兆 | 可能肇因 |
|---|---|
| 第 2 步回「找不到名為「系統 #1」…」 | prompt 又退回 `#id` 代號（`intent_routing_context.format_work_target`），或閘道判定沒認得 `#id` 形式 |
| 第 4 步回「找不到名為「那張圖」…」 | `DEICTIC_REFERENTS` 少了「那」系列 |
| 第 5 步建立了工作項 | 閘道判定被改成「比不到一律退回目前對象」，指名錯誤被靜默吞掉 |
| 第 1 步脈絡列顯示 `#id` | 名稱查詢失敗（`describe_work_target`），先查後端 log |

### 追溯

- 實作：`backend/services/brain_gateway_rules.py`（`refers_to_current_target`、`DEICTIC_REFERENTS`）、`backend/services/intent_routing_context.py`、`backend/services/brain_gateway.py`
- 自動化對應：`backend/tests/test_referent_current_target.py::GatewayCurrentTargetTest::test_naming_a_missing_object_still_not_found`；`backend/tests/test_followup_same_diagram.py::FollowUpSameDiagramTest::test_that_diagram_referent_acts_on_the_same_diagram`
- PR／commit：PR #650（`2fa972e`、head `48f6349`）；紀錄見 `aidlc/spaces/default/intents/260920-orchestration-brain/construction/build-and-test/local-verify-fixes.md`
- User story：US1.1（AC1.1.5）、US6.1（AC6.1.1）

## TC: 回歸：在工作區產生並存檔的新架構圖會掛到作業對象的系統，大腦找得到它

- plan: 260920 大腦入口：真實模型路徑（手動）
- priority: P1

### 目的

回歸案例。驗證在作業對象為某系統時，從工作區以 A1 產生的**新**圖存檔後會掛到該系統，大腦接著對「這個系統」做評核時能找到這張圖，而不是回「這個系統下沒有掛上的架構圖」。

### 背景

本機驗證 F1（2026-11-10，阻擋級）：新產的架構圖永遠不會掛到系統上，於是大腦的架構設計／評核／成本在任何新系統上都回

```
這個系統下沒有掛上的架構圖，請在脈絡列選定圖
```

入口頁自己的範例句「幫我畫一張電商網站的雲端架構圖」必定失敗。根因：存檔後 `user_diagrams.system_id` 為 NULL，全 backend 唯一寫入它的是一次性遷移。修正新增兩條寫入路徑（存檔帶 `system_id`、系統頁掛圖）。

**既有自動化層為何沒抓到**：後端測試各自以 fixture 直接建出「已掛在系統上的圖」，從來沒有一個測試走「使用者實際產圖 → 存檔 → 大腦讀」這條鏈；而產圖本身是 A1 的 LLM 路徑，`ui-regression` 刻意不碰。修正後 `test_diagram_system_attach.py` 已以同一個 facade 呼叫證明「存檔掛上後大腦讀得到」，e2e 以攔截層斷言存檔 POST 本體帶 `system_id`；但 e2e 樁掉了 draw.io 內嵌，「儲存架構圖」與成功提示「已掛到系統「…」」沒有被斷言（`local-verify-fixes.md` F1 未完成項 4），真實 A1 產圖接著存檔的整條鏈只有本案會走。

### 受測介面

- UI: `/workspace` — 工作區：A1 對話、「儲存架構圖」、存檔成功提示
- UI: `/` — 大腦入口頁：脈絡列、工作項卡片
- UI: `/projects/:projectId` — 專案總覽：「系統的架構圖」區
- API: `POST /api/collab/diagrams` → 200 — 存新圖，本體帶 `system_id`
- API: `GET /api/collab/diagrams` → 200 — 我的圖清單，每列帶 `system_id`
- 外部相依: LLM 供應商（A1 產圖與大腦路由）；n8n 圖示 webhook（圖示取不到時只影響圖面，不影響本案判定）

### 前置條件

1. 本機 stack 與模型依檔頭「共用環境」備妥，以 `admin`／`admin123` 登入。
2. 在 `/projects` 建立專案「掛圖測試」與其下新系統「訂單系統」——**新系統，下面沒有任何圖**。
3. 回到 `/`，脈絡列選定 專案「掛圖測試」／系統「訂單系統」。
4. 瀏覽器開發者工具的 Network 分頁保持開啟。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 進 `/workspace`，以 A1 對話產生一張「訂單 API ＋ RDS」的架構圖（依提示回答反問直到出圖） | 畫布出現架構圖 |
| 2 | 按「儲存架構圖」 | Network 中 `POST /api/collab/diagrams` 回 200，請求本體含 `"system_id":` 接「訂單系統」的 id；頁面出現提示含「已掛到系統「訂單系統」」 |
| 3 | 進 `/projects/<該專案 id>` 的總覽 | 「系統的架構圖」區的「訂單系統」列出第 2 步存的圖 |
| 4 | 回 `/`，輸入「幫我做 Well-Architected 評核，看這個系統的架構圖」並送出 | 出現以「已交給架構檢視處理」開頭的卡片 |
| 5 | 等卡片結束 | 文字為「檢視完成：整體分數」接數字與「項發現」；**不得**是「這個系統下沒有掛上的架構圖，請在脈絡列選定圖」 |

### 通過條件

- 第 2 步請求本體帶 `system_id` 且回 200；第 5 步得到檢視分數而非「這個系統下沒有掛上的架構圖」。兩者皆成立才算通過。

### 失敗徵兆與對應肇因

| 徵兆 | 可能肇因 |
|---|---|
| 第 2 步請求本體沒有 `system_id` | `WorkspacePage.tsx` 存新圖時沒讀 `brain.target.systemId`（作業對象沒同步到工作區） |
| 第 2 步回 403／404 且沒有存檔 | 帳號不是該專案擁有者或缺 `K2 edit`——符合設計（不合格不建檔），換用擁有者帳號重跑 |
| 第 3 步看得到圖、第 5 步仍回「沒有掛上」 | 大腦讀取端 `list_diagrams_of_system` 與寫入端看的不是同一個欄位或可見範圍 |

### 追溯

- 實作：`backend/services/collab_router.py`（`CreateDiagramRequest`、`_attachable_system_or_raise`）、`backend/services/hierarchy_facade.py`、`frontend/src/pages/WorkspacePage.tsx`、`frontend/src/components/projects/SystemDiagrams.tsx`
- 自動化對應：`backend/tests/test_diagram_system_attach.py::DiagramSystemAttachTest::test_create_with_owned_system_attaches_and_brain_can_list_it`；`frontend/tests/e2e/object-picker.spec.ts`（攔截層，斷言存檔本體）
- PR／commit：PR #650（`2fa972e`、head `48f6349`）；紀錄見 `aidlc/spaces/default/intents/260920-orchestration-brain/construction/build-and-test/local-verify-fixes.md`
- User story：US9.1（暫掛；build-and-test 範圍新增 S-1，requirements／stories 待回補）

## TC: 本機 LLM_PROVIDER=claude-code 只在 APP_ENV=local 生效，且 A3 建議以已登入的 claude CLI 產出

- plan: 260920 大腦入口：本機與部署環境（手動）
- priority: P2

### 目的

驗證本機以 `claude` CLI 當模型時，A3 評核建議真的由 CLI 產出文字；`APP_ENV` 不是 `local` 時自動退回 `openrouter` 並記 ERROR；`claude` 不在 `PATH` 上時 lens 填答明確降級而不是靜默。

### 背景

`LLM_PROVIDER=claude-code` 是 code-generation 階段新增的本機開發 provider（scope 尚未涵蓋，traceability `LOCAL-LLM-PROVIDER`）。它依賴兩個 CI 永遠不會有的東西：已登入的 `claude` CLI，與開發者機器上的 `backend/.env`。`test_claude_code_chat.py` 與本站新增的 `test_claude_code_call_sites.py` 以假 CLI 驗證了閘門、子行程環境與兩個 A3 呼叫點的形狀，但**真實 CLI 的登入狀態、PATH、回應時間**只有在開發者機器上才存在。

### 受測介面

- UI: `/assessment` — A3 評核頁：建議串流區
- 外部相依: `claude` CLI（已登入）

### 前置條件

1. 本機 stack 依檔頭「共用環境」備妥；`claude -p "回一個字：好"` 有回應。
2. `backend/.env` 設 `APP_ENV=local`、`LLM_PROVIDER=claude-code`、`BRAIN_ROUTER_TIMEOUT_SEC=60`，**移除或清空** `OPENROUTER_API_KEY`。重啟後端。
3. 準備一張已存檔的架構圖（`/workspace` 任一張）。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 觀察後端啟動 log | **不得**出現 `只限本機開發（APP_ENV=local）` 這行 ERROR |
| 2 | 在 `/assessment` 對準備好的圖執行評核 | 出現整體分數；建議區在數十秒內**一次整段**出現繁中建議文字（claude-code 不串流） |
| 3 | 檢視後端 log | 出現 `review_agent start model=`；**不得**出現 `ReviewAgent 未產出 suggestions`、`claude CLI 非零結束` |
| 4 | 把 `backend/.env` 的 `APP_ENV=local` 那一行刪掉，重啟後端，觀察啟動 log 或第一次 LLM 呼叫時的 log | 出現 ERROR，內容包含 `LLM_PROVIDER=claude-code 只限本機開發（APP_ENV=local）` 與 `改用 openrouter` |
| 5 | 還原 `APP_ENV=local`；以 `PATH` 不含 `claude` 所在目錄的 shell 啟動後端，再執行一次評核 | 後端 log 出現 WARNING，內容包含 `A3 lens 改用規則啟發式（未呼叫 LLM）：找不到 claude 指令（LLM_PROVIDER=claude-code）` |

### 通過條件

- 第 2 步建議區有文字、第 4 步出現退回 openrouter 的 ERROR、第 5 步出現啟發式降級的 WARNING。三者皆成立才算通過。

### 清理

- 還原 `backend/.env` 原本的 `LLM_PROVIDER`／`APP_ENV`／`OPENROUTER_API_KEY`，以原本的 shell 重啟後端。

### 追溯

- 實作：`backend/services/llm_provider.py`、`backend/services/claude_code_chat.py`、`backend/services/review_agent.py`、`backend/services/wa_lens_engine.py`
- 自動化對應：`backend/tests/test_claude_code_call_sites.py::ReviewAgentUnderClaudeCode::test_review_agent_streams_cli_text_as_suggestions`；`backend/tests/test_claude_code_chat.py::ProviderGate::test_only_app_env_local_enables_claude_code`
- PR／commit：PR #650（head `48f6349`）
- User story：無使用者故事（開發者工具；build-and-test 範圍新增 S-3，requirements 待回補 NFR）

## TC: 部署後記憶 API 以記憶專用角色運作，不回 503

- plan: 260920 大腦入口：本機與部署環境（手動）
- priority: P1

### 目的

驗證部署到 staging 後，記憶頁與記憶 API 經記憶專用資料庫角色 `cloud360_memory` 運作：`GET /api/memory/records` 回 200，而不是因為部署環境缺 `MEMORY_DB_PASSWORD` 而回 503。

### 背景

build-and-test 第三輪（MB-48）把所有記憶存取改走記憶專用連線，且**非本機環境未設 `MEMORY_DB_PASSWORD` 時一律不退回主連線**：HTTP 回 503「記憶儲存目前無法使用，請聯絡平台管理員。」，閘道的預取／寫入降級並記 `memory_db_unavailable`。`test-results.md` 記載 GitHub secret `MEMORY_DB_PASSWORD` 在當時**尚未建立**。

自動化層（`test_memory_db_session_ws.py`、`tests_pg/test_memory_role_ws_pg.py`）證明的是程式在「有設／沒設」兩種情況下的行為；**staging 實際有沒有設**是部署環境的狀態，CI 的 stack 自帶測試用密碼，永遠不會呈現這個缺口。若 secret 漏設，部署照常成功、頁面照常載入，只有記憶相關功能全部降級。

### 受測介面

- API: `GET /api/memory/records` → 200 — 我的記憶清單
- UI: `/memory` — 我的記憶頁：三種記憶的分區清單
- 外部相依: staging 主機的 `deploy/.env`（由 `deploy/render-env.sh` 產生）與 GitHub Actions secret `MEMORY_DB_PASSWORD`

### 前置條件

1. 該次部署已完成（`deploy.yml` 綠燈），且你有 staging 主機的 shell 權限。
2. 一個 staging 上可登入、具記憶頁權限的帳號。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 在 staging 主機執行 `grep -c '^MEMORY_DB_PASSWORD=.' deploy/.env`（只計數，不印值） | 輸出 `1` |
| 2 | 以該帳號登入 `https://cloud360.danniel.cc`，開 `/memory` | 頁面顯示三個分區；**不得**出現「記憶儲存目前無法使用，請聯絡平台管理員。」 |
| 3 | 開發者工具 Network 檢視 `GET /api/memory/records` | 回 200；**不得**是 503 |
| 4 | 在 staging 主機檢視後端容器 log（`docker compose -f deploy/docker-compose.deploy.yml logs backend`） | **不得**出現 `memory_db_unavailable`；**不得**出現 `memory_db_local_fallback` |
| 5 | 在入口頁 `/` 送出一句會交辦的需求，再回 `/memory` | 情節記憶區多出 1 則（或以上）新紀錄 |

### 通過條件

- 第 1 步輸出 `1`、第 3 步回 200、第 4 步兩個事件名皆 0 筆。三者皆成立才算通過。

### 追溯

- 實作：`backend/services/memory_router.py`（`memory_session_source`、`memory_session_scope`）、`backend/database.py`、`deploy/render-env.sh`
- 自動化對應：`backend/tests/test_memory_db_session_ws.py::GatewayMemorySessionTest::test_unset_non_local_never_hands_any_session_to_the_facade`；`backend/tests_pg/test_memory_role_ws_pg.py`
- PR／commit：PR #650（`2fa972e`、head `48f6349`）
- User story：US4.5（AC4.5.1、AC4.5.3）、US4.1
