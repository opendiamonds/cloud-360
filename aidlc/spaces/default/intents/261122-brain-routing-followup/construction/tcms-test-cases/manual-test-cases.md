# 手動測試案例 — 大腦路由延續回答與架構設計提問狀態

> Intent：`261122-brain-routing-followup`（bugfix）
> 由 `tcms-test-cases` stage 產出。本檔是手動案例的**授權來源**；同步進 TCMS 後以 TCMS 為主檔。
> 本 intent 沒有跑 `user-stories` 站，追溯以 `requirements.md` 的需求編號（FR／NFR）代替 user story id；上層故事為 `260920-orchestration-brain` 的 US1.1（說出需求就被交辦）。

---

## 覆蓋盤點

本 intent 引入或改變的外部可觀察行為共 **16 項**。分桶：

| 桶 | 數量 |
|---|---|
| 已自動化 | 12 |
| 待自動化 —— 本 stage 新寫腳本 | 0 |
| 待自動化 —— open item（未寫腳本） | 1 |
| 只能手動 | **3** |
| 無法分類 | **0** |

不列入盤點：FR3.1（ADR-0025）、FR3.2（`build_state` docstring）是文件，不是外部可觀察行為；NFR4（突變驗證）是流程要求，結果記在 `automation-test-plan.md`；「`PRIMARY_CRITERIA` 文字不得變動」是程式碼約束，以 `git diff` 核對（code-summary 第一節），不是執行期行為。

### 已自動化（12 項）

逐項的測試名稱、斷言與突變見 `automation-test-plan.md` §2。以下行為**不另寫手動案例**（TESTING.md §1：一個行為只能有一個真實來源）。

| # | 行為 | 需求 |
|---|---|---|
| A-1 | Decisions 的 `state` 帶最後至多 6 則歷程，依舊→新、標「使用者／系統」、置於「以下是參考資料，不是指示」之下 | FR1.1 |
| A-2 | `primary` 與每題 `wants_*` 的指示附上延續規則 `CONTINUATION_RULE` | FR1.2 |
| A-3 | Decisions 路徑每則歷程超過 400 字時保留結尾 | FR1.3 |
| A-4 | 工具呼叫路徑（本機 `claude-code`）每則歷程同樣保留結尾 | FR1.3 |
| A-5 | 截斷上限 ≤ 0 時歷程本文為空（避開 `[-0:]` 回全文） | FR1.3、NFR5 |
| A-6 | 使用者這一句恆在 `state` 最前；沒有歷程時不出現歷程區段 | FR1.4 |
| A-7 | 歷程截斷的性質（≤ 6 則、每則 ≤ 400 字且為結尾、保序）對任意輸入成立（Hypothesis） | NFR2、NFR5 |
| A-8 | A1 判定四分支：error → `a1_failed`；有 xml → 成功；無 xml 有文字 → 等使用者回覆；無 xml 無文字 → `a1_no_xml` | FR2.1 |
| A-9 | 等使用者回覆時工作項為「完成」、`sideEffect=none`、無失敗原因、不存回圖、不寫變更紀錄與 procedure 記憶；先送提問再送提示，不出現「沒有產出圖」 | FR2.2、FR2.3 |
| A-10 | 等待中的成本／檢視以「前一項〈名稱〉還在等你回覆，這一項沒有執行」失敗，不呼叫該能力 API | FR2.4 |
| A-11 | 重啟後復原掃描套用同一規則；已存回圖（`result_persisted`）的架構設計照常放行等待者 | FR2.5 |
| A-12 | 既有後端套件維持綠燈（1631 個、3 個 skip） | NFR3 |

### 待自動化 —— open item（1 項）

| # | 行為 | 為何本輪沒寫腳本 |
|---|---|---|
| O-1 | 平台自我竄改預檢只回固定拒絕語「此需求毫無相關，請重新輸入」＋ complete 時，FR2.1 會把它判成「等使用者回覆」，畫面出現「架構設計在等你回覆上面的問題」、等待者以「還在等你回覆」失敗——兩句皆不實 | 這是 requirements 審查 R-02，閘門以 Accepted risk 核可、本 intent 不處置。正確行為尚未定案：現在寫測試，要嘛把錯的行為鎖進測試（之後修正時反而要先改測試），要嘛寫出一支注定紅燈的測試。可自動化（`judge_a1` 是純函式），待另開 intent 定案正確行為時一併寫腳本。 |

### 只能手動（3 項）

| # | 行為 | 為何不能自動化 |
|---|---|---|
| M-1 | staging 真實 A1 只回提問時，大腦畫面的工作項顯示「完成」與「在等你回覆」提示，不顯示「沒有產出圖」 | 每跑一次都要花錢（真實 A1／OpenRouter）；e2e 刻意不觸及 LLM 路徑；A1 會不會只回提問由真實模型決定，替身只能驗後端判定（A-8、A-9 已驗） |
| M-2 | staging 上回答架構設計的選擇題只打「A」，Decisions 路由直接交給架構設計、不跳反問卡 | 只有 staging 的 Decisions 路徑（`typesafe/jev-1.14`）會出現此缺陷，本機走工具呼叫路徑重現不了；路由結果取決於真實決策模型的機率，替身只能驗請求形狀（A-1、A-2 已驗） |
| M-3 | NFR1：延續規則改了指示文字後，ADR-0024 實測表六句的路由結果不變 | 同上，需真實 Decisions API 的機率輸出；CI 不打真實模型 |

---

## TC: 架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖

- plan: Cloud-360 大腦路由延續回答（手動）
- priority: P1

### 目的

回歸案例。保護 FR2.1–FR2.3：staging 上真實的架構設計 agent 以選擇題收集需求、沒有產圖時，大腦畫面上的工作項必須是「完成」並緊接「在等你回覆」提示，**不得**標成「失敗：…架構設計沒有產出圖」，也不得改動架構圖。

### 背景

1. **症狀**：在大腦入口頁請架構設計畫圖，架構設計回了一題選擇題（例如「運算層要用 A. VM / B. 容器 / C. 無伺服器 / D. 其他？」）但沒產圖，工作項清單卻把這一項標成失敗，使用者以為架構設計壞了。
2. **畫面文字逐字**：`失敗：架構設計：架構圖 #1 架構設計沒有產出圖`
3. **根因**：`work_orchestrator_capabilities.judge_a1` 只要串流結束沒有 xml 就判 `a1_no_xml`，不分「agent 在提問」與「真的什麼都沒產出」。
4. **既有自動化層為何沒抓到**：A1 判定的單元測試原本就把「只有提問文字、沒有 xml」寫成 `a1_no_xml` 的期望值——測試照錯的規格寫，所以是綠的；而真實 A1 何時只回提問由 LLM 決定，`ui-regression` 刻意不觸及任何 LLM 路徑，沒有任何一層看過真實模型回提問時畫面長怎樣。修正後判定邏輯已由 A-8／A-9 自動化守住，本案例守的是「真實 A1 串流 ＋ 真實閘道 ＋ 真實畫面」這一段。

### 受測介面

- API: `POST /api/auth/login` → 200 — 登入取得 token
- UI: `/` — 大腦入口頁：`brain-entry-page`、脈絡列 `brain-context-bar`、對話區 `brain-conversation`、工作項清單 `brain-workitem-list`（狀態徽章 `brain-workitem-<id>-status`）
- UI: `/workspace` — 開啟該架構圖，確認圖面未被改寫
- WebSocket：`/api/brain/ws` — 大腦唯一的連線（不在 `openapi.json` 內，故不寫成 API 行）
- 外部相依: OpenRouter（Decisions 路由 `typesafe/jev-1.14`、A1 架構設計模型），staging 需有 `OPENROUTER_API_KEY`

### 前置條件

1. 本修正已部署到 staging（`https://cloud360.danniel.cc`）。在 staging 主機（`192.168.10.10`）的部署工作目錄（含 `deploy/.env` 的那份 checkout）確認容器內是新碼，輸出必須 ≥ 1：
   ```
   docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec -T backend grep -c "CONTINUATION_RULE" services/intent_routing_decisions.py
   ```
2. 一個 staging 測試帳號（不要用個人帳號），具 A1 view／edit 權限。帳密依團隊 staging 測試帳號，不寫入本檔。
3. 該帳號脈絡列選得到一張**可拋棄**的測試架構圖（本案例可能讓架構設計改寫它）。在 `/workspace` 開啟它並截圖留存，作為步驟 7 的比對基準。
4. 瀏覽器開 DevTools（不需要特別設定，只用來在步驟 6 以 Ctrl+F／Cmd+F 搜尋頁面文字）。
5. 費用：本案例會呼叫一次 Decisions 路由與一次真實 A1，產生 OpenRouter 費用。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 以測試帳號登入 `https://cloud360.danniel.cc` | 落在 `/`，看得到 `brain-entry-page`；脈絡列離開「連線中」骨架 |
| 2 | 在脈絡列選定前置條件 3 的測試架構圖 | 脈絡列顯示該圖名稱 |
| 3 | 在輸入框送出「幫我設計一個電商網站的雲端架構」 | 對話區出現「已交給架構設計處理〈該圖〉」；工作項清單新增一列，徽章為「處理中」 |
| 4 | 等待架構設計回覆（至多 3 分鐘） | 對話區出現架構設計的提問，含可選項（例如 `A.`／`B.`／`C.`），且工作項清單**沒有**新增「已存回架構圖」的說明 |
| 5 | 看提問之後的下一則系統訊息 | 逐字為「〈工作項名稱〉：架構設計在等你回覆上面的問題，直接回答即可」，〈工作項名稱〉形如 `架構設計：架構圖 #<id>`；且它出現在提問**之後** |
| 6 | 看工作項清單中這一列的狀態徽章，並以 Ctrl+F 搜尋「沒有產出圖」 | 徽章為「完成」（綠色），**不得**為「失敗」；這一列沒有失敗原因文字；頁面搜尋「沒有產出圖」為 0 筆 |
| 7 | 開 `/workspace` 開啟同一張圖，與前置條件 3 的截圖比對 | 圖面與截圖相同，沒有新增或移除任何元件 |

### 通過條件

- 步驟 4 出現提問（若架構設計直接產圖，本次執行判為「前置未達成」而非通過或失敗，換一句更模糊的需求重跑）。
- 步驟 5 的提示逐字相符且在提問之後、步驟 6 徽章為「完成」且「沒有產出圖」0 筆、步驟 7 圖面未變——三者同時成立才算通過。

### 失敗徵兆與對應肇因

| 徵兆 | 最可能的肇因 |
|---|---|
| 徽章「失敗」，原因「架構設計沒有產出圖」 | staging 仍是舊碼（前置條件 1 輸出 0），或 `judge_a1` 的 `awaiting_reply` 分支被改掉（自動化 A-8 應同時紅燈） |
| 徽章「完成」但沒有「在等你回覆」提示 | `_complete_awaiting_reply` 沒送 `awaiting_reply` 句型，或前端吞掉了第二次 `turn` |
| 提示出現在提問**之前** | 兩次 `_emit("turn")` 的順序被調換（FR2.3 要求先提問後提示） |
| 圖面被改寫或出現「已存回架構圖」 | 等使用者回覆的分支誤走了存回路徑（`_settle_persisted`） |
| 提示文字正確但徽章「失敗」，原因為「架構設計失敗」 | A1 串流含 `error` 事件，屬 `a1_failed`，不是本缺陷；看 backend log 的 A1 錯誤 |
| 提問是「此需求毫無相關，請重新輸入」 | 撞到平台竄改預檢（已知 open item O-1），換一句正常的架構需求重跑 |

### 追溯

- 實作：`backend/services/work_orchestrator_capabilities.py`（`judge_a1`）、`backend/services/work_orchestrator.py`（`_complete_awaiting_reply`）、`backend/services/work_orchestrator_rules.py`（`PHRASES["awaiting_reply"]`）
- 自動化對應：`backend/tests/test_work_orchestrator_capabilities.py::A1JudgementTest::test_a1_question_without_xml_awaits_reply_instead_of_failing`、`backend/tests/test_work_orchestrator_flow.py::ArchitectureAwaitingReplyTest::test_question_without_diagram_completes_without_failure_or_persist`
- PR／commit：分支 `danniel/fix/brain-routing-followup-context`（撰寫時尚未 commit）
- User story：FR2.1、FR2.2、FR2.3（本 intent 無 user-stories 站；上層故事 260920 US1.1）

### 清理

- 測試架構圖若被後續案例改寫，依團隊慣例刪除或還原。本案例本身不改圖（步驟 7 即驗證這點）。

---

## TC: 回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡

- plan: Cloud-360 大腦路由延續回答（手動）
- priority: P1

### 目的

回歸案例。保護 FR1.1、FR1.2 與 NFR1 的第七句：staging 的 Decisions 路由看得到上一則架構設計的提問，使用者只回「A」時判為延續、直接交給架構設計，**不得**跳出「我不確定你指的是哪一件事」反問卡。

### 背景

1. **症狀**：架構設計問「運算層要用 A. VM / B. 容器 / C. 無伺服器 / D. 其他？」，使用者回「A」，大腦卻跳出反問卡，要使用者在「架構設計／架構檢視／成本分析」之間再選一次交給誰。多輪問答的每一輪都斷。
2. **畫面文字逐字**：反問卡標題 `我不確定你指的是哪一件事`，候選為 `交給「架構設計」處理`、`交給「架構檢視」處理`、`交給「成本分析」處理`。
3. **根因**：ADR-0024 D-4 讓 Decisions 路徑的 `state` 不帶對話歷程，路由模型只看到孤立的「A」，三個能力機率相近，`primary` 落到門檻 0.7 以下，必然反問（ADR-0025 修訂此項）。
4. **既有自動化層為何沒抓到**：路由測試全用假 HTTP 回應（依 ADR-0024 實測表構造的替身），只能驗「送出去的請求長什麼樣」，驗不了「真實決策模型看到這個請求會回什麼機率」——所有 LLM 路徑是本 repo 的結構性盲區，沒有任何 CI 會打真實模型。而且本機 `LLM_PROVIDER=claude-code` 走的是工具呼叫路徑（`build_routing_prompt`），那條路徑本來就帶最後 6 則歷程，所以開發機上回「A」一切正常，只有 staging（Decisions 路徑）會斷。
5. **本案例同時驗證一個已接受風險（requirements 審查 R-01）**：使用者回「A」時，歷程最後兩則依序是「架構設計的提問」與「等你回覆提示」，延續規則寫的是「上一則系統**提問**」而最後一則系統訊息是提示。替身測不出這個形狀對真實模型的影響，本案例以真實歷程驗。

### 受測介面

- API: `POST /api/auth/login` → 200 — 登入取得 token
- UI: `/` — 大腦入口頁：輸入框 `brain-input`、反問卡 `brain-clarify`、工作項清單 `brain-workitem-list`
- WebSocket：`/api/brain/ws` — 大腦唯一的連線（不在 `openapi.json` 內，故不寫成 API 行）
- 外部相依: OpenRouter Decisions API（`typesafe/jev-1.14`）；staging 主機 shell（讀 backend log）

### 前置條件

1. 剛通過「架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖」：畫面上最後兩則系統訊息依序是架構設計的提問、「在等你回覆」提示，且之後**沒有**送出任何其他訊息。
2. 另開一個終端機 SSH 到 staging 主機，進入部署工作目錄，準備讀 log：
   ```
   docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env logs -t --since 2m backend | grep "intent routing turn="
   ```
   log 行沒有使用者欄位；staging 若同時有別人在用，以 `-t` 的時間戳對齊步驟 1 送出的時間。
3. 費用：一次 Decisions 路由，加上交辦後一次真實 A1。

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 在輸入框只輸入「A」並送出 | 對話區出現使用者訊息「A」 |
| 2 | 等待 10 秒，看對話區 | **不得**出現 `brain-clarify` 反問卡，頁面搜尋「我不確定你指的是哪一件事」為 0 筆（只算步驟 1 之後新出現的） |
| 3 | 看工作項清單 | 新增一列交給架構設計、處理同一張圖：對話區出現「已交給架構設計處理〈同一張圖〉」，徽章為「處理中」 |
| 4 | 在 staging 主機執行前置條件 2 的指令，取時間戳緊接步驟 1 的那一行 | 該行含 `slots=1`、`can_single_out=True`、`error_kind=None`，且 `caps=` 的第一個項目為 `('architecture-design', 1)` |

### 通過條件

- 步驟 2 沒有反問卡、步驟 3 交給架構設計、步驟 4 log 三個欄位與 `caps` 首項全部相符，才算通過。
- 本案例的結果即 NFR1 的「只回 A」一句；結果須依 requirements NFR1 寫進本 intent 的紀錄（ADR-0025 由 Proposed 轉 Accepted 的依據之一）。

### 失敗徵兆與對應肇因

| 徵兆 | 最可能的肇因 |
|---|---|
| 跳出反問卡，log `can_single_out=False` | 歷程沒送到 Decisions（`DecisionsRoutingPort.route` 沒傳 `recent_messages`，自動化 A-1 應同時紅燈），或延續規則的文字不足以讓真實模型判讀——依 requirements NFR1／OQ1 回頭調整 `CONTINUATION_RULE` 文字，**不得**以調低門檻代替 |
| 跳出反問卡，但自動化 A-1、A-2 皆綠、log 的 `error_kind=None` | 歷程有送到，但真實模型被最後一則「等你回覆」提示（不是提問）誤導——即 R-01 的形狀確實影響真實模型。記下這次的畫面與 log 回報，作為調整延續規則或提示寫法的依據 |
| log `error_kind=LlmUnavailable` 或其他非 None 值 | Decisions 呼叫本身失敗（金鑰、網路、OpenRouter 狀態），不是路由判讀問題；先排除再重跑 |
| 交給了架構檢視或成本分析（`caps` 首項不是 `architecture-design`） | 真實模型把「A」判成別的能力；同第一列，屬延續規則文字問題 |
| 沒有任何 `intent routing turn=` 行 | backend log 等級不是 INFO，或指令不在部署工作目錄執行 |

### 追溯

- 實作：`backend/services/intent_routing_decisions.py`（`build_state`、`CONTINUATION_RULE`）、`backend/services/intent_routing_port.py`（`DecisionsRoutingPort.route`）、`backend/services/intent_routing_context.py`（`keep_tail`）
- 自動化對應：`backend/tests/test_intent_routing_decisions.py::DecisionsEndToEndTest::test_follow_up_answer_carries_the_recent_conversation_into_state`
- 決策：`aidlc/spaces/default/intents/261122-brain-routing-followup/inception/decisions/0025-decisions-routing-carries-conversation-history.md`
- PR／commit：分支 `danniel/fix/brain-routing-followup-context`（撰寫時尚未 commit）
- User story：FR1.1、FR1.2、NFR1（本 intent 無 user-stories 站；上層故事 260920 US1.1）

### 備註

- 架構設計接下來的回覆是否接得上「A」（例如談到 VM／EC2，而不是重問第一題），取決於架構設計 agent 的對話記憶（`MemorySaver`，程式重啟或多 worker 時遺失，requirements OQ2）。那不是本案例的通過條件；有觀察到重問時記在執行備註，供 OQ2 參考。

---

## TC: NFR1 延續規則上線後 ADR-0024 實測六句的路由結果不變

- plan: Cloud-360 大腦路由延續回答（手動）
- priority: P1

### 目的

保護 NFR1：ADR-0025 把延續規則附進 `primary` 與每題 `wants_*` 的指示文字，ADR-0024 的六句實測是在舊指示下取得的。本案例確認新指示下六句的路由結果（交辦哪個能力、是否反問、是否指名）與 ADR-0024 實測表一致——延續規則若讓模型把獨立的新需求也讀成「延續」，會在這裡現形。

### 背景

ADR-0024 的六句實測（2026-11-15，staging runner）是門檻 0.7、指名門檻 0.8、`TIE_MARGIN` 0.05 的唯一依據。ADR-0025 改了 `primary` 與 `wants_*` 的指示文字，那組數字在重測前不能視為仍成立（ADR-0025 Consequences）。替身測試只驗請求形狀，驗不到真實模型在新指示下的機率；CI 不打真實模型。

本案例刻意在**空的對話歷程**下送每一句：ADR-0024 是在不帶歷程時量的，要隔離「指示文字變了」這一個變因，就不能讓前一句留下的歷程影響下一句。有歷程時的延續判讀由「回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡」負責。

### 受測介面

- API: `POST /api/auth/login` → 200 — 登入取得 token
- API: `GET /api/auth/me` → 200 — 取得測試帳號的 `id`，組出 session key
- UI: `/` — 大腦入口頁：脈絡列 `brain-context-bar`、反問卡 `brain-clarify`、工作項清單 `brain-workitem-list`
- UI: `/projects` — 確認可見的專案與系統名稱
- WebSocket：`/api/brain/ws` — 大腦唯一的連線（不在 `openapi.json` 內，故不寫成 API 行）
- 外部相依: OpenRouter Decisions API（`typesafe/jev-1.14`）；staging 主機 shell（清空 session、讀 backend log）；staging Redis

### 前置條件

1. 同「架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖」的前置條件 1、2（新碼已部署、專用測試帳號）。
2. **目錄**：該帳號在 `/projects` 可見的專案與系統名稱**恰為**「流動性資產管理系統」「電商前台系統」「會員中心」三個（與 ADR-0024 實測目錄相同；多出的名稱會改變 `named_target` 的選項）。缺的以 `/projects/new` 建立同名專案。
3. **測試圖**：一張可拋棄、脈絡列選得到、且**不屬於**「電商前台系統」的架構圖（第 3 句要看脈絡列是否被改成「電商前台系統」）。第 1、2、5 句會實際交辦檢視、架構設計與成本，可能改寫這張圖。
4. 登入後在 DevTools 的 Network 分頁找 `GET /api/auth/me` 的回應，記下 `id`（以下記為 `<id>`）。
5. **清空程序**（每一句之前執行一次）——在 staging 主機的部署工作目錄：
   ```
   set -a; . deploy/.env; set +a
   docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec -T -e REDISCLI_AUTH="$REDIS_PASSWORD" redis redis-cli --user "$REDIS_USER" DEL "brain:session:<id>"
   ```
   輸出 `1`（刪掉了）或 `0`（本來就沒有）。接著重新整理瀏覽器頁面，並在脈絡列重新選定測試圖（session 清空後作業對象也會清空）。只刪測試帳號自己的 session key，不影響其他使用者。
6. 讀 log 的指令同「回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡」前置條件 2。
7. 費用：六次 Decisions 路由，加上第 1、2、5 句交辦後的真實 A3／A1／成本呼叫。

### 測試資料

ADR-0024 實測表（期望值來源）：

| 句子 | primary | wants_design | wants_review | wants_cost | named_target |
|---|---|---|---|---|---|
| 幫我評核這個系統的架構風險 | well-architected-review 1.0 | .14 | .98 | .11 | none 1.0 |
| 幫我畫一張電商網站的雲端架構圖，用 AWS | architecture-design 1.0 | .96 | .07 | .05 | 「電商前台系統」0.63（誤配，低於指名門檻 0.8） |
| 電商前台系統每個月大概要花多少錢？ | cost-finops 1.0 | .03 | .08 | .96 | 「電商前台系統」0.99 |
| 幫我看一下這個 | unclear 0.99 | .08 | .12 | .11 | none 1.0 |
| 幫我改一下那張圖，加上 CloudFront，然後估一下成本 | architecture-design 0.68 | .81 | .13 | .98 | none 0.97 |
| 今天天氣如何 | unclear 1.0 | .01 | .04 | .03 | none 1.0 |

### 測試步驟

每一列之前都先執行前置條件 5 的清空程序；每一列送出後都以前置條件 6 的指令取時間戳緊接送出的那一行 log。

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 送出「幫我評核這個系統的架構風險」 | 沒有 `brain-clarify` 反問卡；對話區出現「已交給架構檢視處理〈測試圖〉」；脈絡列仍是測試圖；log 為 `slots=1`、`can_single_out=True`、`caps=` 首項 `('well-architected-review', 1)` |
| 2 | 送出「幫我畫一張電商網站的雲端架構圖，用 AWS」 | 沒有反問卡；對話區出現「已交給架構設計處理〈測試圖〉」；脈絡列仍是測試圖，**不得**被改成「電商前台系統」；log 為 `slots=1`、`can_single_out=True`、`caps=` 首項 `('architecture-design', 1)` |
| 3 | 送出「電商前台系統每個月大概要花多少錢？」 | 沒有反問卡；脈絡列的作業對象變為「電商前台系統」；log 為 `slots=1`、`can_single_out=True`、`caps=` 首項 `('cost-finops', 1)` |
| 4 | 送出「幫我看一下這個」 | 出現 `brain-clarify` 反問卡，標題為「我不確定你指的是哪一件事」；工作項清單沒有新增任何一列；脈絡列仍是測試圖；log 為 `can_single_out=False` |
| 5 | 送出「幫我改一下那張圖，加上 CloudFront，然後估一下成本」 | 沒有反問卡；工作項清單新增兩列，以 DevTools 的 Elements 分頁檢視 `brain-workitem-list` 下的 `li`，一列 `data-capability="architecture-design"`、一列 `data-capability="cost-finops"`（兩列各自的狀態取決於架構設計跑多久，不列入判定）；脈絡列仍是測試圖；log 為 `slots=2`、`caps=` 含 `('architecture-design', 1)` 與 `('cost-finops', 1)` 且架構設計在前 |
| 6 | 送出「今天天氣如何」 | 出現 `brain-clarify` 反問卡，標題為「我不確定你指的是哪一件事」；工作項清單沒有新增任何一列；脈絡列仍是測試圖；log 為 `can_single_out=False` |

### 通過條件

- 六列的預期結果全部成立才算通過；任一列不符即不通過。
- 不通過時，依 requirements NFR1／OQ1 回頭調整 `CONTINUATION_RULE` 的文字後重測，**不得**以調低 `BRAIN_ROUTER_CONFIDENCE_THRESHOLD` 代替。
- 六列結果加上「回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡」的結果，依 requirements NFR1 寫進本 intent 的紀錄；兩者皆通過才是 ADR-0025 轉 Accepted 的依據。

### 失敗徵兆與對應肇因

| 徵兆 | 最可能的肇因 |
|---|---|
| 第 1、2、3、5 列跳出反問卡 | 延續規則讓模型對「獨立的新需求」信心下降（以為可能在延續什麼）；調整 `CONTINUATION_RULE` 讓它只在有系統提問時生效 |
| 第 4、6 列**沒有**反問、被交辦了 | 延續規則讓模型在空歷程下也傾向某個能力；同上 |
| 第 2 列脈絡列被改成「電商前台系統」 | 誤配信心升到 0.8 以上——`named_target` 的指示沒有改，若出現代表模型版本或目錄與實測時不同，先核對前置條件 2 |
| 第 3 列脈絡列沒變、出現「找不到名為…的系統或專案」 | 目錄裡沒有「電商前台系統」，或名稱有空白差異；核對前置條件 2 |
| 某一列的 log `slots`／`caps` 對得上，但畫面多出上一句的內容 | 清空程序沒做或沒重新整理頁面，該句其實帶了歷程；重做前置條件 5 後重跑該列 |
| log `error_kind` 不是 `None` | Decisions 呼叫本身失敗，先排除金鑰／網路後重跑，不計入判定 |

### 追溯

- 實作：`backend/services/intent_routing_decisions.py`（`PRIMARY_INSTRUCTIONS`、`WANTS_QUESTIONS`、`CONTINUATION_RULE`）
- 自動化對應：無（`backend/tests/test_intent_routing_decisions.py::DecisionsEndToEndTest::test_follow_up_answer_carries_the_recent_conversation_into_state` 只驗延續規則有附在指示上，驗不到真實機率）
- 決策：`aidlc/spaces/default/intents/261122-brain-routing-followup/inception/decisions/0025-decisions-routing-carries-conversation-history.md`；實測表來源 `aidlc/spaces/default/intents/260920-orchestration-brain/inception/decisions/0024-intent-routing-via-jev-decisions-api.md`
- PR／commit：分支 `danniel/fix/brain-routing-followup-context`（撰寫時尚未 commit）
- User story：NFR1、FR1.2（本 intent 無 user-stories 站；上層故事 260920 US1.1）

### 清理

- 測試圖可能被第 2、5 句改寫，執行完依團隊慣例刪除或還原。
- 第 1 句會建立一份檢視紀錄。
- 最後再執行一次前置條件 5 的清空程序，避免測試帳號的 session 帶著這六句進入下一次測試。
