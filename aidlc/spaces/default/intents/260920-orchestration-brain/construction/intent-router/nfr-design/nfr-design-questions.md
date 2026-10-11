# NFR Design 問題檔 — `U11 intent-router`

> depth 為 **Minimal**。本站只問**一題**——它是唯一一個「在我們無法實測的情況下
> 必須先選一邊、而選錯會在 `code-generation` 才爆出來」的決定。其餘設計決定本站
> 自行定案並在產出寫明理由（清單見下方「本站自行定案、不提問」）。

## 本站查證的事實（供提問引用）

| # | 事實 | 取得方式 |
|---|---|---|
| V1 | **repo 內每一條 LLM 路徑都把呼叫包進 `StateGraph`，連單次呼叫也不例外**——`backend/cost/cost_advice_agent.py:135-165` 的 `_invoke_once` 是一個**單節點圖**（`add_node` → `set_entry_point` → `add_edge(END)` → `compile()` → `invoke_graph`） | `[讀]` 該檔 |
| V2 | 該寫法有一個**已知的 sharp edge 並有回歸測試釘住**：`backend/tests/test_a3_langgraph_migration.py:188` 逐字「Regression: `StateGraph(dict)`+TypedDict param emptied state under messages stream」，修法是改用具名的 TypedDict state（`review_agent.py:146` 的 `StateGraph(_ReviewState)`） | `[讀]` 兩檔 |
| V3 | **repo 內零結構化輸出前例**：`with_structured_output`／`response_format`／`JsonOutputParser`／`logprobs` 在 `backend/` 全樹 0 命中 | `[跑]` `grep -rn` |
| V4 | Jev 的 `supports_tool_choice` 四項（`none`／`auto`／`required`／`function`）皆為 `true`，`supported_parameters` 為**空陣列**，`output_modalities` 為 `["decisions"]` | `brain-infra` 的 `N13` 實測中繼資料 |
| V5 | **我們無法實測 Jev 對任意 schema 的處理**——`backend/.env` 不存在、`OPENROUTER_API_KEY` 未設（已列為 `tech-stack-decisions.md` 的 `TS-6` blocking 前置條件） | `[跑]` `[ -f backend/.env ]` |
| V6 | `NFR3.62` 定死**每輪最多 1 次模型呼叫**，所以 N 個槽位必須在**同一次**回應裡拿到，不能一槽一呼叫 | `nfr-requirements/performance-requirements.md` |

---

## [D1] 工具呼叫的回應 schema 要用哪一種形狀

`entities.md` 的網域模型是**兩層**的：`ClassificationResult.slots`（並存的 N 件事）
→ 每個槽位一張 `CandidateRanking.candidates`（互斥的讀法）。`EC6`／`EC7`／`EC8`
三條不變量都建立在這兩層分得開。

問題是：**要不要把這兩層原樣搬進送給 Jev 的 function schema**。
因為 V6，一次呼叫就要帶回全部槽位；因為 V5，我們**沒辦法先試一次**再決定。

### 選項

- **A（建議）— 扁平陣列 ＋ `slot` 索引欄位。** schema 回一個 `candidates` 陣列，
  每個元素帶 `slot`（整數，自 0 起）、`capability`、`referent`、`score`、`label`。
  兩層的還原在**我們這邊**做：依 `slot` 分組即得 `ClassificationResult.slots`。
  - **好處**：對模型而言是**最簡單的 schema 形狀**——一層物件陣列，沒有巢狀陣列。
    V3 顯示本 repo 沒有任何結構化輸出前例、V5 顯示我們無法先驗 Jev 的 schema 支援度，
    在這種雙重未知之下，**選對模型要求最低的形狀**是降低「到 `code-generation`
    才發現它吐不出來」的機率。
  - **代價**：`EC6`（槽位與候選是兩個軸）在**線上形狀**裡變成一個慣例（`slot` 欄位）
    而不是型別。分組邏輯與其驗證（`slot` 必須從 0 連續、每組至少一個候選）落在
    我們的解析層，要有自己的測試。
  - 附帶好處：`slot` 是整數欄位，**模型漏填或填錯時可以被我們擋下並走 `BR2.4`
    的失敗路徑**，而巢狀形狀下「少了一層」比較難判定。
- **B — 巢狀：`slots` 陣列，每個元素內含自己的 `candidates` 陣列。**
  - **好處**：與 `entities.md` 的網域模型**一比一對應**，`EC6` 在型別層就成立，
    解析層幾乎不用做事。讀 schema 的人一眼看懂兩層的意思。
  - **代價**：巢狀的「物件陣列中再含物件陣列」是各家模型 schema 支援度**差異最大**
    的形狀，而 V5 讓我們無法先驗 Jev。若它處理不好，發現的時機是 `code-generation`
    第一次真的打 API 的那一刻——而那時 `TS-6` 的金鑰前置條件才剛被滿足。
- **C — 兩種都實作，依設定切換。**
  - **代價**：兩條解析路徑、兩組測試，而其中一條註定是死碼（最後只會用一種）。
    `project.md` 記過這個形狀（「規則檔裡的死碼比程式裡的更難發現」）。
    真正的不確定性只有一次，不值得用一個永久的分支去對沖。
- **D — 本站不定，留給 `code-generation` 實測後決定。**
  - **代價**：`code-generation` 的 Plan Approval 需要一個確定的設計，而
    「schema 形狀未定」會讓它的計畫寫不出來。且 `logical-components.md` 要描述
    解析層的邊界，形狀未定時那一節只能空著。

[Answer]: A（扁平陣列 ＋ `slot` 索引欄位）
<!-- answered 2026-10-10T00:05:12Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## 本站自行定案、不提問（逐項附理由）

| # | 決定 | 理由 |
|---|---|---|
| 1 | **路由層的呼叫包進單節點 `StateGraph`**，沿用 V1 的既有形狀 | `project.md` 要求「指定沿用既有機制前，先寫下該機制的副作用是否與新需求相容」。副作用是 V2 的 `StateGraph(dict)`+TypedDict 通道 bug，**相容性處置是沿用 `review_agent.py:146` 的具名 TypedDict state**（`StateGraph(_RouterState)`），該修法已有回歸測試釘住。沿用的收益：`U13` 日後要把路由層當成更大圖的一個節點時不需改寫 |
| 2 | **不直接呼叫 `openrouter_chat_model`，改建一個路由層專用的 client factory** | `TS-3a`：Jev 的 `supported_parameters` 為空陣列，而 `openrouter_chat_model` **無條件傳 `temperature=0.0`**（`langgraph_runtime.py:95`）。直接沿用會把一個已知風險帶進第一次呼叫 |
| 3 | **不設 circuit breaker、不設 fallback 模型** | `nfr-requirements/reliability-requirements.md` 已定案並寫明理由（含修訂 1 對原錯誤論證的更正） |
| 4 | **`BRAIN_ROUTER_CONFIDENCE_THRESHOLD` 維持 required-no-default**，即使 `OQ-10` 結論為「無可用信心訊號」時它在執行期是惰性的 | `BR3.4` 逐字「缺值不得以預設值靜默啟動」。一個存在但惰性的設定，優於一個靜默沒有門檻的系統；而 `OQ-10` 定案前我們不知道它會不會被用到 |
| 5 | **SLI/SLO 定義齊備但明記無告警通道** | 沿用 `U10` 的 `OPEN-N10-4`，不開第二個同義缺口 |
| 6 | **交接膠水時間不在本站分配** | `nfr-requirements/performance-requirements.md` 已指派 `U13` 的 `nfr-requirements` |

## 上游已定案、不重問

| 事項 | 出處 |
|---|---|
| 路由層模型＝`typesafe/jev-1.13` | `OQ-4`（使用者 `2026-10-03T11:48:31Z`，本站 `nfr-requirements` 的 `[N1]`=C 再確認） |
| P50 ≤ 800 ms、硬逾時 5 秒、每輪 1 次呼叫、重試 0 次 | `nfr-requirements` 的 `[N2]`=A |
| `OQ-10` 承接 `build-and-test` | `nfr-requirements` 的 `[N3]`=A |
| `NFR7.62` 是**現行防護**（`U8` 的 `POST /api/memory/records` 已可建 `kind=episodic`） | `nfr-requirements/security-requirements.md` §三（審查 `R-02` 推翻原「死碼」判定） |
| 本單元對 `SessionContext` **唯讀** | `BR7.4` |
| 述詞是純函式，且是 ADR-0006 PBT 的落點 | `BR3.6`；`functional-spec.md` §五 |
