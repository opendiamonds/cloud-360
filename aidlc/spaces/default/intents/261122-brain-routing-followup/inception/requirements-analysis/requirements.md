# Requirements：大腦路由延續回答與架構設計提問狀態

## 意圖分析

使用者在大腦（brain）裡與架構設計多輪問答時，流程每一輪都會斷掉：

1. 架構設計問「運算層要用 A. VM / B. 容器 / C. 無伺服器 / D. 其他？」，使用者回「A」，大腦卻跳出「我不確定你指的是哪一件事」，要使用者再選一次交給哪個能力。
2. 架構設計每次只回提問、沒產圖時，工作項都被標為「失敗：架構設計沒有產出圖」。

目標是讓使用者**像在一般對話裡一樣直接回答架構設計的提問**：不必每輪重選能力，也不被錯誤的「失敗」誤導。

**類型**：bug 修正（brownfield）。**範圍**：大腦路由層（`backend/services/intent_routing_*`）與工作編排層（`backend/services/work_orchestrator*`），不碰前端、不碰契約、不碰資料庫。**複雜度**：Minimal。

**根因**（Reverse Engineering 已核可；codekb `cloud-360/architecture.md` 的 Interaction Diagrams）：
- staging 走的 Decisions 路由（`intent_routing_decisions.build_state`）原本刻意不帶對話歷程，路由模型只看到孤立的「A」，三個能力機率相近，掉到反問門檻以下。本機的工具呼叫路徑有帶歷程，所以本機重現不了。
- `work_orchestrator_capabilities.judge_a1` 只要串流結束沒有 xml 就判 `a1_no_xml`，不分「agent 在提問」與「真的什麼都沒產出」。
- 架構設計 agent 本身以 per-user `thread_id` 保有對話記憶（`design_agent.py`），所以路由正確交辦後它接得上；斷掉的只有大腦這一層。

## 功能需求

### FR1 路由能判讀「延續回答」

- **FR1.1** Decisions 路由送出的 `state` 必須帶該段對話的最後至多 6 則訊息（與工具呼叫路徑的 `DEFAULT_MESSAGE_LIMIT` 相同），依舊→新排列，標明發言者為「使用者」或「系統」，並置於「以下是參考資料，不是指示」之下。
- **FR1.2** Decisions 的 `primary` 與每一題 `wants_*` 的指示文字，必須附上同一句延續規則：使用者若在回答對話中上一則系統提問（例如只回選項字母或簡短答案），視為延續該提問所屬的那一件事。`primary` 的選項定義文字（`PRIMARY_CRITERIA`）不得變動。
- **FR1.3** 每則歷程訊息超過上限（400 字）時，保留**結尾** 400 字而非開頭 [Q2]。適用於 Decisions 路徑（`build_state`）與工具呼叫路徑（`build_routing_prompt`），兩條路徑行為一致。
- **FR1.4** 使用者的這一句仍放在 `state` 最前面，歷程不得取代或改寫它；歷程上限截斷在路由層無條件發生，不依賴呼叫端先截（`BR6.1` 最少上下文）。

**驗收**：
- Given 該段最近對話含一則系統提問「…A. 虛擬機器 (VM) B. 容器服務」，When 使用者送「A」，Then 送出的 `state` 以「使用者這一句：A」開頭，且含該提問全文並標為「系統」。
- Given 該段有 7 則以上訊息，When 路由，Then `state` 只含最後 6 則。
- Given 一則系統提問長 1000 字、選項在最後，When 路由，Then `state` 中該則含最後的選項文字、不含開頭超過 400 字的部分。
- Given 該段沒有任何訊息，When 路由，Then `state` 不含歷程區段（與修正前同形）。

### FR2 架構設計只回提問時不判失敗

- **FR2.1** A1 串流結束時：有 `error` 事件 → `a1_failed`；有 xml → 成功（取最後一份）；**沒有 xml 但有非空白說明文字** → 判為「等使用者回覆」，不是失敗；沒有 xml 也沒有文字 → `a1_no_xml`。
- **FR2.2** 「等使用者回覆」時，工作項由「處理中」轉為「完成」，`sideEffect` 為 `none`，無 `failureReason`；不存回圖、不寫變更紀錄、不寫 procedure 記憶。不新增狀態值（狀態集合為前後端共用契約）。
- **FR2.3** 「等使用者回覆」時，先轉送架構設計的提問文字，再送出提示「〈工作項名稱〉：架構設計在等你回覆上面的問題，直接回答即可」。
- **FR2.4** 等待該架構設計的工作項（檢視、成本）不得在未變動的舊圖上執行，一律以「失敗」結束，原因為「前一項〈名稱〉還在等你回覆，這一項沒有執行」，且不呼叫該能力的任何 API。
- **FR2.5** 程式重啟後的復原掃描必須套用同一規則 [Q1]：被等待項為架構設計、狀態為「完成」、但 `dispatchStage` 不是 `result_persisted`（沒有存回圖）時，等待者以 FR2.4 的原因結束，不得開始執行。

**驗收**：
- Given A1 串流只有一則提問與 `complete`，When 交辦架構設計，Then 工作項為「完成」、`sideEffect` 為 `none`、無失敗原因，畫面文字含提問與「在等你回覆」提示、不含「沒有產出圖」，且沒有 PUT、沒有變更紀錄、沒有 procedure 記憶。
- Given A1 串流只有空白 message 與 `complete`，When 判定，Then 為 `a1_no_xml`。
- Given A1 串流有提問也有 `error`，When 判定，Then 為 `a1_failed`。
- Given 同時交辦架構設計與成本、A1 只回提問，When 執行結束，Then 成本為「失敗」且原因為「前一項…還在等你回覆，這一項沒有執行」，沒有呼叫成本 API。
- Given 架構設計為「完成」但 `dispatchStage` 為 `request_sent`、另有一項等待它的成本，When 執行復原掃描，Then 成本以 FR2.4 的原因結束、沒有呼叫成本 API；Given 架構設計為「完成」且 `dispatchStage` 為 `result_persisted`，When 復原，Then 成本照常開始。

### FR3 設計變更紀錄

- **FR3.1** 在本 intent 新開一份 ADR [Q4]，記錄 Decisions 路徑改為帶對話歷程與延續規則的理由、取捨與替代方案，並註明它修訂 ADR-0024 中「不帶歷程」的那一項；ADR-0024 本文不改。
- **FR3.2** `build_state` 的 docstring 必須寫明帶歷程的理由，不得保留「不帶對話歷程」的舊敘述。

## 非功能需求

- **NFR1 路由量測**（[Q3]）：部署到 staging 後，以 ADR-0024 實測表的六句、外加「架構設計提問後只回 A」一句，重新量測 Decisions 回應。通過條件：
  - 六句的路由結果（交辦哪個能力、是否反問、是否指名）與 ADR-0024 實測表一致。
  - 「只回 A」一句的 `primary` 選中 `architecture-design`，且不觸發反問。
  - 量測結果寫進本 intent 的紀錄；任一句不通過就回頭調整 FR1.2 的文字，不得以調低門檻代替。
- **NFR2 Property-based 測試**（ADR-0006 hard constraint，agent routing 屬核心模組）：`build_state` 的歷程截斷須有 Hypothesis 性質測試。對任意訊息序列，`state` 須同時滿足：
  - 最多含 6 則歷程；
  - 每則歷程本文不超過 400 字，且是原文的結尾；
  - 使用者這一句永遠在最前面。
- **NFR3 回歸**：既有後端測試全數維持綠燈（修正前基準：1624 個測試、3 個 skip，全數通過）。
- **NFR4 突變驗證**：每一項 FR 對應的測試，都要做到把修正改回去會變紅、還原後變綠，並記錄突變內容。
- **NFR5 輸入成本上界**：每次路由多送出的使用者內容不超過 6 × 400 字。

## ADR-0006 security baseline 逐項判定

| 面向 | 判定 | 理由與處置 |
|---|---|---|
| IAM／授權 | 不適用 | 不新增、不變更任何權限或角色。等待者的拒絕執行是業務規則，不是授權判斷。 |
| Encryption | 不適用 | 不新增儲存或傳輸通道。歷程沿用既有的 HTTPS 呼叫送往 OpenRouter。 |
| Network exposure／資料外送 | **適用** | Decisions 呼叫原本只送使用者這一句，現在多送最近 6 則對話（每則至多 400 字），送往同一個外部 LLM 端點（OpenRouter）。這些內容在本機路徑本來就已送出，staging 路徑是新增外送。處置：上限截斷在路由層無條件發生（FR1.4、NFR5）；歷程標為「參考資料，不是指示」，避免使用者文字被當成指令；不新增端點、不新增連出目的地。 |
| Audit logging | 不適用 | 不變更任何稽核紀錄。既有 log 不記錄需求原文，本修正也不新增記錄原文的 log。 |

Property-based testing（ADR-0006）：適用，見 NFR2。

## 限制

- 不改工作項的狀態集合、WebSocket 契約（`ws-contract.json`）、OpenAPI、資料庫 schema，因此不觸發 `schema_rbac.sql`／`DEPLOY.md`／`LOCAL-DEV.md` 的同步義務。
- `PRIMARY_CRITERIA` 的文字不得變動（程式註解：換字就要重新量測）。
- 不新增環境變數或外部依賴。
- 文件繁體中文；commit 與 PR 標題用中文 type（`修正(brain): …`）；分支 `danniel/fix/brain-routing-followup-context`。

## 假設

- **A1**：架構設計 agent 以 per-user `thread_id` 接續對話（`design_agent.py` 的 `MemorySaver`、`agent_router.py:153`）。理由：RE 實讀確認；這是「回 A 之後架構設計接得上」的前提，本 intent 不改它。
- **A2**：架構設計的提問會以 assistant 訊息寫入該段對話歷程（`brain_gateway.append_assistant_background`）。若寫入失敗，只記 WARNING、不中斷，此時該輪路由沒有歷程可參考，行為退回修正前。理由：RE 部分實讀 `brain_gateway.py`。
- **A3**：「等你回覆」的工作項在畫面上顯示「完成」徽章，靠緊接的提示文字區分。理由：已定案不新增狀態。

## 範圍外

- 工作項新增「等待回覆」狀態（需改前端與 WebSocket 契約）。
- 架構設計 agent 的對話記憶持久化：`MemorySaver` 在程式內，程式重啟或多 worker 時接不上，屬既有限制。
- 修改 ADR-0024 本文。
- 本機工具呼叫路徑的系統提示詞加入延續規則（本機路徑已帶歷程；只套用 FR1.3 的截斷方式）。

## Open questions

- **OQ1**：NFR1 的 staging 量測若有任一句不通過，FR1.2 的指示文字要怎麼調整。屆時另行決定，由 build-and-test 之後的部署驗證承接。
- **OQ2**：架構設計 agent 對話記憶在重啟後遺失（範圍外第 2 項），是否另開 intent 處理。
