# RAID Log — 統一入口大腦

Risks（可能發生、需要緩解）、Assumptions（相信為真但未驗證）、
Issues（已經發生、需要處置）、Dependencies（依賴他方才能完成）。

依 `project.md` 的 `feasibility:c6`，本階段對已識別的實作層風險**只記載風險
本身與緩解方向，不預選具體手段**；選定手段是設計階段的必答項。

來源定義見 `feasibility-questions.md` 的 `## Sources`（S1–S13）與各題作答；
上游決定見 `<record>/ideation/intent-capture/intent-statement.md`。

## Risks

| ID | 風險 | 可能性 | 影響 | 緩解方向（非選定手段） | 來源 |
|---|---|---|---|---|---|
| R-1 | **既有架構圖遷入新階層時破壞既有頁面或遺失歸屬**。既有圖直接掛在使用者底下，而新階層要求它們歸屬到系統；`schema_rbac.sql` 只在空 volume 執行，既有 staging 的遷移必須手動 | 中 | 高 | 本站未以試探消除，改為對 application-design／functional-design 的明確指派：產出遷移步驟與回復方式。方向包含「可重跑的遷移腳本」與「遷移前後的既有頁面相容驗證」，由設計階段擇定 | [Q5][S10][F10] |
| R-2 | **LangGraph 無法乾淨包住既有以 SSE 回應的 agent 端點**。這是整個架構的地基，假設錯誤會使後續設計全部建立在錯的前提上 | 中 | 高 | 以技術試探先行回答（用完即丟，不進正式程式碼） | [S3][S6][F6] |
| R-3 | **記憶層資料模型與向量檢索的前置代價被低估**。現用資料庫映像不含 pgvector，取得向量檢索需換映像或自建映像 | 中 | 中 | 以技術試探先行回答，含換映像的實際代價 | [S9][F6] |
| R-4 | **外部成本上限觸發時，系統當下的行為未定**。上限由 OpenRouter 後台承載，本專案不掌握其數值；觸發後供應商會開始拒絕請求 | 中 | 中 | 方向為「明確的降級行為而非靜默失敗」——例如可辨識的錯誤回覆或切換到較便宜的模型。手段由設計階段擇定 | [F11][F13] |
| R-5 | **兩種串流機制並存造成前端與維運的分歧**。大腦改用 WebSocket，既有 3 個端點維持 SSE | 高 | 低 | 方向為「明確劃定哪些路徑走哪一種」並寫入設計產出，使並存是刻意而非偶然 | [S3][S4][F4] |
| R-6 | **新增 Redis 容器的環境變數未被同批寫入**，導致服務啟動但功能靜默降級。此失敗模式在本 repo 有前例（n8n 憑證從未被寫入，架構圖 icons 長期靜默退回佔位圖） | 中 | 中 | 由既有的 blocking 規則承載（`render-env.sh` 與 `.env.example` 同批更新）；設計階段須確認該規則被實際套用而非僅被引用 | [S8][F2] |
| R-7 | **記憶層的刪除權與稽核需求互相抵消**。使用者可自行刪除自己的記憶，而管理者的「誰改了什麼」需求正由長期記憶承載 | 中 | 中 | 方向為「刪除動作本身留下稽核紀錄」，使刪除可被稽核而內容被移除。手段由設計階段擇定 | [F5][Q10] |
| R-8 | **兩份 LangGraph／OpenRouter 執行層並存後各自漂移**。大腦自建 runtime，既有 `services/langgraph_runtime.py` 供成本 agent 使用；兩份 OpenRouter 客戶端與兩套串流事件語意並存，任一份改動（模型別名、逾時、重試、事件型別）不會自動反映到另一份 | 高 | 中 | 方向為「鎖住兩者一致性的驗證」，依 `team.md ## Code Style` 單一真實來源規則所要求。手段不在本站預選；設計階段須指定落點並說明驗證什麼。**此為使用者知情後的選擇（Q13=B 的代價已於作答時揭露），不是疏漏** | [Q13][V8] |
| R-9 | **成本 job 的兩種終態（`timeout`／`failed`）在大腦側無對應訊息而靜默**。成本端明確送出這兩種事件，若大腦只處理 `progress` 與 `completed`，使用者會停在最後一則進度訊息，無法分辨「還在跑」與「已失敗」 | 中 | 中 | 方向為「每一種終態事件都有對應的使用者可見訊息」。具體文案屬下游 | [V-F1][F15] |


**R-10（本輪合併 `ut` 時查出）— 大腦路由目標的下游相依缺口，六道 CI 閘門結構性抓不到。**
D-8／D-9 的三處缺口全是**函式內 import**：`backend/main.py` 的 import smoke 只驗模組層，
398 個測試不走那些路徑，兩道契約漂移檢查只看 `openapi.json`／`ws-contract.json` 的形狀。
四者皆綠而功能仍壞，屬 `project.md` 記載的三塊結構性盲區之一（「所有 LLM 路徑」）。
**緩解**：把 D-8／D-9 列為能力 10 與 Assessment 路由的**外部驗收前置條件**，在排驗收
順序時先確認它們已修，不要等到 demo 當天。本分支的程式**與這三隻零耦合**（47 個改動檔
中 0 個、10 個關鍵字 grep 全 0 命中，且設計刻意選擇自建 runtime 而非重用
`langgraph_runtime`），故不阻擋開發與合併。

**R-11（併入 `ut` 時實測查出，已於 2026-10-01 修復）— `LLM_PROVIDER=cli` 已失效，
且是靜默失敗。**
`services/llm_provider.py` 的 cli 模式會從環境**刪除** `ANTHROPIC_AUTH_TOKEN`／
`ANTHROPIC_BASE_URL`——這在 claude-agent-sdk 時代是正確的（當時由 `claude` CLI 自行
認證）。但 A3 遷移之後 `design_agent.py:118` 直接讀這兩個變數建構 `ChatAnthropic`，
刪掉即取到**空金鑰**，而 `llm_auth_ready()` 仍回 `True`。**已實測**：設
`LLM_PROVIDER=cli` 並給定兩個變數後呼叫 `configure_provider_env()`，`api_key` 為空
字串、`base_url` 為 `None`、`llm_auth_ready()` 為 `True`——健康檢查回報正常而功能在
呼叫時才失敗。全樹已無任何子行程呼叫（`create_subprocess_exec`／`Popen` 皆 0 命中），
故 cli 模式已無可認證的對象。

**可能性的評估已更正**：初次記載時評為「低（預設為 openrouter，須手動改設才會踩
到）」，**這是錯的**。`backend/.env.example` 第 23 行的預設值**就是**
`LLM_PROVIDER=cli`——照文件複製出的 `.env` 會直接踩到。更正後為**高**（照文件做就會
中）；影響維持**中**（靜默失敗，且 `llm_auth_ready()` 回 True 會把排查方向帶往錯的
地方）。這個誤判的來源是我只讀了程式沒讀範本檔，而範本檔才是使用者實際會照做的
那一份。

**處置：[H8]=D —— 本 intent 直接修。** 使用者於 approval-handoff 修訂 3 選 D（AI 推薦
A「指派 `ut` 側」）。三種修法評估後選**移除 cli 模式**：全樹已無子行程，它不是壞了，
是它要服務的東西不存在了；另兩種修法（讓它不再刪變數／只讓 `llm_auth_ready()` 回
False）分別會把它變成無作用的別名、或把靜默失敗改成大聲失敗但仍不可用。

**落實內容**（`llm_provider.py` 由 237 行縮為 178 行）：
- `cli` 保留**辨識**但標為退役——設它會退回 `openrouter` 並記一行 **ERROR**（不是
  WARNING，與「不是有效值」的 typo 訊息刻意區分；既有設定不是打錯字）。
- 不拒絕啟動：本模組自己的契約是「一個選填變數的錯值不該讓整個 API 起不來」，且
  openrouter 路徑已有明確可行動的「金鑰未設定」錯誤。拒絕啟動會把一行過期設定變成停機。
- 刪除 `_configure_cli_env()`、`_CLI_*` 變數族、cli 專屬模型預設與 slug 過濾分支。
- `llm_auth_ready()` 的 cli 分支移除——它不再對任何情況回報未經查證的 `True`。
- `auth_error_message()` 不再把 cli 模式當成另一條出路。
- `backend/.env.example` 預設值改為 `openrouter`，並寫明舊預設就是 cli 這件事；
  順手合併該檔原本重複兩次且敘述不一致的 `DESIGN_LLM_MODEL` 區塊。
- `LOCAL-DEV.md` 與 `backend/main.py` 的敘述同步。
- `tests/test_llm_provider.py` 改寫（23 個測試全綠），新增 `RetiredCliMode` 類別直接
  鎖住這個缺陷：`test_no_longer_deletes_credentials`、`test_auth_ready_no_longer_lies`。
  **已做突變驗證**：把兩處行為改回原本的靜默失敗，該兩個測試即紅燈；還原後全綠。

**殘留**：`cli` 這個字串仍留在 `llm_provider.py` 的 `_RETIRED_PROVIDERS` 與檔頭散文、
`.env.example` 的退役說明中——這是刻意保留，移除它會讓既有設定退化成「打錯字」訊息。
**協調事項**：`llm_provider.py` 屬 `ut` 側（tina）正在改動的範圍，本次修改可能在她下次
碰同一支時產生衝突。此代價於 [H8] 選項原文已向使用者揭露。

**R-12（修訂 2 查證查出）— 既有 agent 的工具脈絡是模組層全域，併發時跨使用者
錯送內容。**
`design_agent.py` 的 `_progress_queue` 是模組層全域（第 31／183／203／211／218
行），工具與入口**都讀當下的模組全域**。**已實測**：兩個重疊請求共用最後一個被
建立的佇列，使用者 A 收到使用者 B 產生的架構圖 XML，B 什麼都沒收到；第 218 行
先結束者把全域設為 `None` 後，另一請求其後的 progress／xml／error 事件被
**靜默丟棄**。兩個生產呼叫點皆可達（`agent_router.py:125` 每個 HTTP 請求、
`wa_collab_orchestrator.py:79`）。`thread_id` 是 per-user 的（`agent_router.py:125`
用 `f"user-{current_user.id}-design"`），但那只餵 checkpointer，不管佇列。
**可能性**高（任何兩個使用者同時用 A1 即觸發；本專案的大腦會增加併發路徑）；
**影響**高（跨使用者資料暴露 ＋ 靜默遺失，且兩者在單一使用者的驗收下都不會出現）。
**緩解**：`[F17]`=A 定為能力 1／8 的實作前置，沿用 `cost/advice_orchestrator.py:23-24`
的 per-key dict ＋ `threading.Lock` 形狀——本 repo 自己的正解，不需發明新模式。
記為約束 **C-R3**。既有缺陷而非本 intent 引入，但本 intent 的編排與串流會放大它。

**R-13（修訂 2）— MCP 的 token 傳遞路徑若設計錯誤，憑證會進入模型輸入且不可撤回。**
`[F16]`=B 選擇真的導入 MCP server ＋ client。MCP server 是獨立進程，而 `[S13]`=A
要求「底下走 HTTP 帶使用者 token」——若 token 以**工具參數**傳遞，它會(1)進入 LLM
的 context、(2)被 LangGraph checkpointer 寫進訊息歷史並持久化、(3)出現在任何記錄
`tool_calls` 的 log。三者皆無法事後撤回。
**可能性**中（工具參數是最直觀的傳法，不明文禁止就很可能被這樣寫）；**影響**高
（憑證洩漏且不可撤回）。
**緩解**：已寫成硬約束 **C-T11**——token 必須由傳輸層或 session 承載，工具的 JSON
schema 內不得出現任何憑證欄位。本站不預選傳輸形式（stdio 或 HTTP／SSE），那屬設計
階段；但「不得進入 LLM context」這條不是設計選項。
**附帶**：MCP server 是本 intent 的**第二個**新增進程邊界（第一個是 Redis），本身
亦為新增依賴與新技術層——`[F16]` 的選項原文已逐字揭露此代價，使用者知情選擇。

## Assumptions

| ID | 假設 | 驗證者 | 來源 |
|---|---|---|---|
| A-1 | 兩個技術試探各自可在半天到兩天內得到結論 | 執行試探時即可驗證 | [F6] |
| A-2 | 語意記憶採向量檢索 | 設計階段確認；若不採用，C-T5 與 R-3 即不成立 | [S9] |
| A-3 | ~~LangGraph 與 CI 的 Python 3.12 相容~~ **已由事實取代，不再是假設** | 已驗證：`langgraph==1.2.11` 已釘選於 `backend/requirements.txt` 並隨既有成本 agent 通過 CI 與部署 [V8]。本項於修訂 1 由假設升為既成事實，不需試探驗證 | [S7][F6][V8] |
| A-4 | 「盡量省」的設計原則足以守住 OpenRouter 後台的成本上限 | **無法驗證**——本專案不掌握該上限數值 | [F11][F13] |
| A-5 | 記憶層內建的最小權限模型（擁有者、可見範圍）足以讓介接的應用系統映射自身角色，不需要記憶層理解各系統的角色語意 | 設計階段確認 | [F9] |
| A-6 | 三個成功指標的門檻值可在 requirements-analysis 定出，不需要先有實測基準 | requirements-analysis 確認 | [F7] |
| **A-7** | **MCP 的 Python server／client 生態可在本 repo 的 Python 3.12 ＋ LangGraph 1.2.11 環境下運作，且其工具定義能被 `ChatAnthropic` 以 tool-calling 消費。** 本站**未實測**——`[F16]`=B 的選擇是在「repo 內零前例」的事實被揭露後做的，故這是真實的待驗假設，不是形式記載 | `domain-design` 的技術試探（比照 P-1／P-2） | 修訂 2 [F16]=B |

## Issues

| ID | 問題 | 狀態 | 處置 | 來源 |
|---|---|---|---|---|
| I-1 | `team.md ## Code Style` 記載「Backend 依賴 100% 未 pin、無 lockfile……11 個依賴無一有版本約束」，但實測 `requirements.txt` 已有兩項精確釘選 | 已記載，待更正 | 規則層敘述已過期，待下一輪 practices-discovery 更正；本 intent 以實測值為準 | [S2] |
| I-2 | 本 stage 的 F11 作答曾被轉錄錯誤（使用者實選 A，被記為 C），原因為提問時選項順序與問題檔不同而依位置對應 | 已更正 | 問題檔就地記錄更正與原因；最終答案為使用者其後改選的 B | [F11] |

## Dependencies

| ID | 依賴 | 阻擋什麼 | 來源 |
|---|---|---|---|
| D-1 | OpenRouter 後台的成本上限設定 | 不阻擋開發；但未設定時，成本無任何實際上限 | [F13] |
| D-2 | `deploy/render-env.sh` 與 `deploy/.env.example` 的同批更新 | 阻擋 Redis 容器在部署環境正確運作 | [S8][F2] |
| D-3 | `schema_rbac.sql` 與 `DEPLOY.md` 的同步更新 | 阻擋專案／系統階層與記憶層 schema 在部署環境落地 | [S8] |
| D-4 | application-design 或 functional-design 接下遷移步驟的指派 | 阻擋 R-1 的緩解；未接到則該風險無聲落空 | [F10] |
| D-5 | requirements-analysis 接下三個指標門檻的定案 | 阻擋成功與否的可判定性 | [F7][Q3] |
| D-6 | 設計階段接下 R-8 的一致性驗證落點指派 | 阻擋 R-8 的緩解；未接到則兩份 runtime 的漂移無任何偵測手段 | [Q13] |
| D-7 | 既有成本能力的 `/api/cost/v1` 契約維持穩定 | 大腦以 HTTP 呼叫它，該契約變動會直接打斷編排；但兩者同 repo 同部署，由 CI 的 OpenAPI drift 檢查承載 | [F14][V-F2] |
| D-8 | **tina 修復 `services/langgraph_runtime.py` 的 `langchain_openai` 相依** | 阻擋**能力 10 的端到端驗收**（不阻擋開發）。大腦的成本編排路由到 `/api/cost/v1`，該端點的建議流程走 `cost/estimate_intake_service.py:71` → `advice_orchestrator` → `cost_advice_agent._invoke_once` → `langgraph_runtime.openrouter_chat_model()` → `from langchain_openai import ChatOpenAI`，而 `langchain-openai` 已被 `#678` 自 `requirements.txt` 移除。乾淨 venv 實測：`ModuleNotFoundError: No module named 'langchain_openai'`。該 import 位於函式內，**CI 的 import smoke 與現有測試皆掃不到**，第一次真的問成本才會炸 | 本輪合併 `ut` 時查出 ｜ **已於 2026-10-01 解決**（`ut` 的 PR #683 把 `langchain-openai` 加回 `backend/requirements.txt`；併入後複驗 import 成立） |
| D-9 | **tina 修復 `services/review_agent.py` 與 `services/wa_lens_engine.py` 的 `claude_agent_sdk` 相依** | 阻擋 **Assessment 路由目標的端到端驗收**（不阻擋開發）。進入點 `run_review_agent()`（`review_agent.py:115`）與 `answer_lens_with_agent()`（`wa_lens_engine.py:469`），呼叫端為 `review_orchestrator.py:257`／`:336`／`:461` 與 `wa_score_service.py:16`，而 `claude-agent-sdk` 已被 `#678` 自 `requirements.txt` 移除。乾淨 venv 實測：`ModuleNotFoundError: No module named 'claude_agent_sdk'`。同樣是函式內 import，同樣掃不到 | 本輪合併 `ut` 時查出 ｜ **已於 2026-10-01 解決**（`ut` 的 `b4f0cdc` 把 Review／Lens 改走 LangGraph，兩支模組不再 import `claude_agent_sdk`；全樹僅剩回歸測試 `test_a3_langgraph_migration.py` 的斷言字串，該測試即鎖住此修復的機制） |

<!-- 修訂 1 存檔於 2026-09-21，對應 feasibility 的 Consolidated Summary
     Confirmation 收據。本檔的修訂範圍：新增風險 R-8（兩份 runtime 漂移）
     與 R-9（timeout／failed 終態靜默）、新增依賴 D-6／D-7、A-3 由假設升為
     既成事實。 -->

## Assumptions & Open Questions

- 本表的 R-1 至 R-7 皆未選定具體緩解手段，這是本階段的刻意限制而非遺漏；
  選定手段是設計階段的必答項。[assumption]
- A-4 是本表唯一**無法驗證**的假設：本專案不掌握外部成本上限的數值，因此
  「盡量省是否足夠」在本 intent 內沒有判定依據。[assumption]
