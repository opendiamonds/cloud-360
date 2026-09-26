# Contract Design — 問題檔

<!-- Stage: contract-design（Inception 2.8）· Record: 260920-orchestration-brain
     lead: aidlc-architect-agent · support: aidlc-aws-platform-agent -->

## 這一站在決定什麼

`units-generation` 定出 **17 個單元、25 條依賴邊**。本站不重新切單元，只做一件事：
把每一條邊上的**正式契約**釘死——什麼資料過邊界、什麼形狀、走什麼機制、出錯時
怎麼辦——好讓多個單元能平行開工而不在整合時翻車。

**CONDITIONAL 適用性判定：執行。** stage 檔的 condition 為「跨單元邊界（多於一個
單元須整合）**或** 有對外消費的 public/external API」。本 intent 25 條跨單元邊使
第一條成立；`U13 brain-gateway` 的新 WebSocket 是本 intent 唯一新增的對外網路面，
第二條亦成立。

---

## 上游已定案、本站不重問

逐項核對過**具體選項或原文**（依 `scope-definition:260822-c5`：引用不出來就代表它
沒被定案，應補問而非推論）：

| 事項 | 已定案於 | 不重問的依據 |
|---|---|---|
| WS 傳輸機制為 WebSocket、既有 5 個 SSE 端點不動 | `[RA:FR8.2]` | 逐字「傳輸機制為 **WebSocket**；既有 5 個 SSE 端點不在本次變更範圍」 |
| WS 必須掛 `/api/` 之下 | `[RA:FR8.3]` | 逐字，理由為 `location /` 走 `try_files` 會回 HTML |
| token 不得放 query string，走 `Sec-WebSocket-Protocol` 或握手後首則訊息 | `[RA:FR8.5]` | 逐字 |
| 握手須以 `record=True` 呼叫 `get_user_from_token` | `[RA:FR8.4]` | 逐字，可測不變量已寫明 |
| 對外訊息型別至少含 `clarify`／`work_items`／`cost_card`／`token`／`done`／`error` | `components.md` `BrainGateway.behaviour` | 逐字列舉 |
| `clarify` 候選帶 `id`／`label`／`capability`，信心值為**選填且不得列為必填** | `components.md` 同段 ＋ `mockups.md` H-2 | 逐字；H-2 只把「正式契約」指派本站，欄位語意已定 |
| 呼叫既有 C1 一律走 HTTP 帶使用者 token，不得同進程直呼 service 層 | `[RA:FR10.2]` | 逐字，理由為 `estimate_intake_service` 內無第二道角色檢查 |
| 不得對成本做 token 級巢狀串流轉送 | `[RA:FR10.8]` | 逐字，來源端沒有逐字可轉 |
| 成本五種狀態事件（`progress`／`completed`／`failed`／`timeout`／`heartbeat`）要轉譯進大腦訊息流 | `[RA:FR10.4]` | 逐字列舉 |
| `projects`／`systems` 的讀建改刪一律經 `require_story_action` | `[RA:FR9.5]` | 逐字，含「不得有任何繞過該 dependency 的路徑（含同進程直呼 service 層）」 |
| 工作項狀態值不得少於五個、須帶 `sideEffect`（`none`／`unknown`／說明文字） | `components.md` `WorkOrchestrator.behaviour` | 逐字，`unknown` 為合法值 |
| 每列記憶存 `embeddingModel`，檢索只比對同一 model id | `decisions.md` ADR-008 | 逐字 |

---

## 出題前的唯讀查證（**非來源**，供題幹與選項引用）

依 `project.md` 的 `feasibility:c4`／`intent-capture:c3`：下列是本站為了把問題問對
所做的唯讀查證，**不是需求來源**，不進任何 artifact 的來源標籤。

| # | 查證項 | 結果（皆為實讀，附檔名行號） |
|---|---|---|
| V-1 | 既有 OpenAPI 漂移閘門的形狀 | 兩道 gate：backend job 跑 `python scripts/dump_openapi.py --check`（`ci.yml:260`，後端程式碼為真實來源，不一致 `exit 1`）；frontend job 跑 `npm run check:types`（`ci.yml:198`），該腳本把 `openapi.json` 重產型別到暫存檔再與 committed 的 `src/types/api.d.ts` 比對。腳本自己的註解逐字寫明為何需要第二道：「規格檔的 gate 只保證『規格檔 == 後端程式碼』……若重新 dump 了規格卻忘了重產型別檔……那條路徑會靜默通過，前端在執行期拿到未定義值」 |
| V-2 | WebSocket 是否在 `openapi.json` 內 | **否**。實算 `openapi.json` 有 **42** 個 path，無任何 WebSocket path（FastAPI 不登錄 websocket route）。既有 `/api/collab/ws/{workspace_id}`（`collab_router.py:266`）確實不在其中 |
| V-3 | 既有 WS 前例的握手認證 | `collab_router.py:270` 為 `websocket.query_params.get("token")`——**token 在 query string**，正是 `[RA:FR8.5]` 要禁止的形狀。本站的新契約不得照抄 |
| V-4 | `langgraph_runtime.py` 到底是什麼 | **一層泛用 helper，不是擁有圖的 runtime**。`invoke_graph`／`stream_graph`／`astream_graph`（`:101–150`）三者都接受**呼叫端自行編譯的 graph**，只對它呼叫 `.invoke`／`.stream`／`.astream`，把結果包成 `InvokeOutcome(state)`／`StreamEvent(kind, data)` |
| V-5 | 誰在用它 | 生產程式碼中**只有一個呼叫端**：`cost_advice_agent.py:134–156`（自己 `StateGraph(dict)` 編譯後傳入）。A1 `design_agent` 與 A3 `review_agent` 走 **Anthropic Agent SDK**，與 LangGraph 無關，全樹不 import 該模組 |
| V-6 | `configure_provider_env` 的耦合範圍 | `openrouter_chat_model()` 的 docstring 逐字為「**Does not mutate `llm_provider` environment semantics.**」，實作只讀 `OPENROUTER_API_KEY` 後建 `ChatOpenAI`，不碰 env。行程級改寫存在於 `llm_provider.configure_provider_env()`（`:103–111`）這條路徑（A1／A3 用），**不在 `langgraph_runtime` 這條** |
| V-7 | 路由層模型可否與功能 agent 不同 | **可以**。`openrouter_chat_model(model=..., timeout_seconds=..., temperature=...)`（`:71`）支援逐次呼叫覆寫；預設常數 `DEFAULT_OPENROUTER_MODEL = "google/gemini-3.7-flash"`（`:17`） |
| V-8 | 成本 `completed` 事件是否帶估價 id | **從來不帶**。`advice_stream_router._snapshot()`（`:32–47`）的 payload 只有 `status`／`saving_text`／`comparison_text`／`quality_text`／`unavailable_reasons`／`started_at`／`completed_at`。`set_id` 是**路徑參數**（`@router.get("/sets/{set_id}/advice/stream")`，`:161`），呼叫端本來就持有 |
| V-9 | 成本事件的完整集合 | 實測 `advice_stream_router.py` 的 `"type":` 出現處為 `progress`（三處分支）／`completed`／`timeout`／`failed`／`heartbeat`，與 `[RA:FR10.4]` 列舉的五種相符 |

### V-8 直接解決上游的 H-6，故該項不出成題目

`mockups.md` 的 **H-6** 問「成本 `completed` 回應是否一定帶估價 id，決定
`CostAnswerCard` 的 `no-estimate-id` 是防禦性死碼還是真實態」。V-8 的答案是
**從來不帶，且不需要帶**——`set_id` 由大腦自己在發起 job 時持有並保存於工作項，
卡片的連結由它組出。故 `no-estimate-id` 的可達性**完全由大腦自己的實作決定**，
不受外部 API 影響；本站的契約直接把「工作項必須保存 `set_id`」寫成不變量。
依 `requirements-analysis:260822-ra-c5`：單一可行解不出成假選擇，改為在下方
摘要確認揭露。

---

## 問題

### C1. 三條同進程邊的授權形式（domain-design 的 R-01 已接受風險，在本站變成必須選的契約）

`components.md` 的 `ProjectHierarchy.behaviour` 逐字寫「讀、建立、修改、刪除一律經
`require_story_action`（story id K2），**不得有任何繞過該 dependency 的路徑，含同進程
直呼 service 層**」。但同一份檔的機讀目錄把 `SessionContext → ProjectHierarchy` 與
`WorkOrchestrator → ProjectHierarchy` 宣告為 `style: sync`（同進程）。domain-design
的審查以 **R-01（Major）** 標出這個自相矛盾，使用者在該站選擇 Approve，故它是**已接受
的風險**並指派 `functional-design`（CONDITIONAL）。

**但機制選擇正是本站的職責**（stage 檔：「Choose the integration mechanism per
boundary」），而 `functional-design` 是 CONDITIONAL、可能被 skip。受影響的是三條邊：
`U10 session-store → U7`、`U12 work-orchestrator → U7`、`U11 intent-router → U8`
（`MemoryStore` 有自己的擁有者／可見範圍授權模型，形狀同構）。

- A. **同進程呼叫，但被呼叫端自己做授權**：在 `U7`／`U8` 的 service 層入口收一個
  已驗證的 principal 物件，並在該層**自己呼叫**權限判定，不倚賴 FastAPI dependency。
  契約寫成「service 函式簽章的第一個參數是 principal，且該函式必自行驗權」。
  代價：`require_story_action` 的邏輯要能脫離 dependency 被呼叫；多一份必須與
  dependency 保持一致的授權呼叫點。
- B. **HTTP loopback 帶使用者 token**：三條邊一律走 `httpx` 打自己的
  `/api/...` 端點並帶原 token，`require_story_action` 原封不動照常執行。
  契約就是 `U7`／`U8` 的 OpenAPI。代價：每次都多一次本機網路往返與一次
  JWT 解碼；且 WebSocket handler 內發同步 HTTP 需留意不阻塞事件迴圈。
- C. **一層授權門面（authorized facade）**：`U7`／`U8` 對內只暴露一個 facade 模組，
  該 facade 在委派給 service 前自己呼叫 `require_story_action` 的底層判定函式；
  FastAPI router 與同進程呼叫端**共用這一個入口**，故只有一份授權呼叫點。
  代價：多一層模組；facade 必須是唯一入口，繞過它的直呼要靠 review 擋。
- D. 維持現狀：本站不定案，原樣把 R-01 傳給 `functional-design`，並接受它 skip 時
  轉 `code-generation`（ALWAYS）——即由寫 code 的人決定授權形式。
- X. Other（請說明）

[Answer]: C
<!-- 作答時間 2026-09-26T04:04:02Z（`date -u`）。選 C（授權門面）。後續契約據此撰寫：`U7`／`U8`
     對內只暴露一個 facade 模組，FastAPI router 與同進程呼叫端共用該入口，
     授權呼叫點只有一份。本站須在契約中明寫 facade 為唯一入口，並記下
     「繞過它的直呼只能靠 review 擋、無機械強制」這個殘留缺口。 -->

---

### C2. WS 訊息契約的真實來源與 CI 閘門形狀（承 `components.md` H-4／`[RA:NFR5]`／N-1）

`[RA:NFR5]` 要求「一份前後端共用的訊息型別契約來源」＋「一個 CI 檢查斷言兩端一致」。
V-2 證實既有的兩道漂移閘門對 WebSocket **完全無效**（WS 不在 `openapi.json` 的 42 個
path 內），所以這道閘門要新建。

- A. **鏡射既有 OpenAPI 的兩道 gate 形狀**：後端 Pydantic 模型為真實來源 →
  `scripts/dump_ws_contract.py --check` 在 backend job 比對 committed 的
  `ws-contract.json`（形狀同 `dump_openapi.py`）→ frontend job 由該 JSON 重產 TS
  型別並與 committed 的型別檔比對（形狀同 `check-api-types.mjs`）。兩道 gate 的
  職責分工與既有那組逐字相同（V-1）。
- B. **JSON Schema／AsyncAPI 為真實來源**，Python 與 TS 兩邊都由它產生，CI 檢查
  兩邊產物皆為最新。代價：引入一個 repo 目前沒有的產生器與其版本釘選；後端模型
  變成衍生物而非來源，與既有「後端程式碼是真實來源」的慣例相反。
- C. **TypeScript 為真實來源**，後端由它產生 Pydantic 模型。與既有方向相反，
  且後端是授權與驗證的所在，讓它成為衍生物風險較高。
- D. **只做單向檢查**：後端 dump 規格，前端型別由人工維護，CI 只擋「規格檔與後端
  程式碼不一致」。代價：V-1 的腳本註解逐字說明過這條路徑會**靜默通過**，前端在
  執行期拿到未定義值——即 `[RA:NFR5]` 要防的正是這個。
- X. Other（請說明）

[Answer]: A
<!-- 作答時間 2026-09-26T04:08:02Z（`date -u`）。選 A（後端 Pydantic 為真實來源，兩道 gate 鏡射既有形狀）。
     本題第一次提問時使用者反問「什麼叫衍生物?」，依 stage-protocol §1 的 Other-escape
     處置：先說明「衍生物＝由別的東西自動產生、不該手改的檔案」並以本 repo 現成的
     三層關係（後端 Pydantic → `openapi.json` → `src/types/api.d.ts`）舉例，再把四個
     選項原樣重新呈現後取得作答。**選項本文未改動**，只補了說明。 -->

---

### C3. 大腦的 LLM 執行層：重用既有 `langgraph_runtime` 還是自建（承 `[RA:C-S7]`／`OQ-7`／initiative-brief 的 R-8）

**先說明為什麼這題不照上游的措辭問。** 上游逐字寫「大腦自建 LangGraph 執行層，
與既有 `services/langgraph_runtime.py` **並行**」，風險 R-8 為「兩份 OpenRouter
客戶端／兩套串流事件語意漂移」。V-4／V-5／V-6 的實讀推翻了這個前提的三處：

1. `langgraph_runtime.py` **不是一個擁有圖的 runtime**，是接受呼叫端自編圖的泛用
   helper（`invoke_graph(graph, state)`）。所謂「自建執行層」在這個架構下其實只是
   「自己編一張 `StateGraph` 再傳進去」——那是既有呼叫端 `cost_advice_agent` 本來
   就在做的事。
2. 生產程式碼中它**只有一個呼叫端**；A1／A3 走 Anthropic Agent SDK，根本不是
   LangGraph 家族。所謂「三份 OpenRouter 客戶端」在 LangGraph 這條路徑上只有一份。
3. `OQ-7` 點名的 `configure_provider_env` 行程級 env 改寫，對
   `openrouter_chat_model` 這條路徑**不適用**（其 docstring 逐字排除）。

- A. **重用既有 `langgraph_runtime`**：大腦自行編譯 `StateGraph`，經
   `openrouter_chat_model(model=<路由層模型>)` 取得 client，走同一個
   `invoke_graph`／`astream_graph`。結果是**一個模組、兩個呼叫端**，
   `StreamEvent(kind, data)` 即共用事件形狀，R-8 的漂移在結構上不可能發生。
   NFR10（路由層模型須可與功能 agent 不同）由 V-7 的逐次 `model=` 覆寫滿足。
   本站的契約內容隨之變成「`langgraph_runtime` 的公開介面即契約」＋ 一條鎖住
   `StreamEvent.kind` 合法值集合的測試。
- B. **自建獨立執行層 ＋ 一致性契約測試**：照上游原本設想，大腦有自己的 runtime
   模組，另寫一份契約測試鎖住兩者的事件語意與 client 設定一致。代價：`team.md`
   的「單一真實來源」規則要求新增副本的**同一個 PR** 必須一併新增鎖住一致性的
   測試；而兩份 runtime 的一致性測試本身就是要長期維護的東西。
- C. **自建，但共用 `openrouter_chat_model` 一個函式**：只有圖的執行部分分家，
   client 建構共用。折衷，但兩套事件語意仍各自存在。
- D. **不用 LangGraph**：大腦的路由層直接呼叫 `ChatOpenAI`，不引入圖。代價是
   多意圖拆解與多輪狀態要自己管，且與 `cost_advice_agent` 的既有形狀不一致。
- X. Other（請說明）

[Answer]: B
<!-- 作答時間 2026-09-26T04:04:02Z（`date -u`）。選 B（自建獨立執行層 ＋ 一致性契約測試）。

     **本站對自己推薦 A 的更正（提問後查證，作答前補記）**：我推薦 A 時漏查一點，
     而該點支持 B。`stream_graph`（`:130`）與 `astream_graph`（`:149`）兩者都把
     `StreamEvent` 的 `kind` **硬寫為 `"updates"`**，不隨 `stream_mode` 改變；
     既有測試 `test_langgraph_runtime.py:90,105` 亦逐字斷言 `kind == "updates"`。
     大腦要做 `[RA:FR8.1]` 的逐字串流須傳 `stream_mode="messages"`，屆時 payload
     是訊息 token 而事件仍標為 `updates`——**標籤與內容不符**。要讓 A 正確，必須
     改動這支共用 helper（讓 `kind` 由 `stream_mode` 推導），而那會動到既有成本
     路徑與其已 commit 的測試斷言。B 不需要動它。

     故 B 的成立依據不只是「照上游設想」，而是這個可查證的介面缺口。
     `team.md ## Code Style`「單一真實來源」要求新增副本的同一個 PR 必須一併新增
     鎖住兩者一致的測試——B 已內含該測試，故合規。本站的契約須明寫該測試鎖住
     什麼（見產出的 `langgraph-consistency` 契約）。 -->

---

### C4. WS 契約的版本與破壞性變更政策

本 repo 是 deploy-on-merge 到單一 staging，且前後端在**同一次部署**一起上線
（`docker-build` 建兩個 image、`deploy.yml` 一次帶起整個 compose）。這使「舊前端
碰到新後端」的視窗在正常路徑下不存在——但瀏覽器分頁可能開著舊 bundle 跨越一次部署。

- A. **不設版本欄位，採 additive-only ＋「消費端忽略未知欄位」**：破壞性變更的
   協調方式是「前後端在同一個 PR 內一起改」，由 C2 的 CI 閘門擋住只改一邊。
   跨部署的舊分頁以既有的 WS 斷線重連處理（見 C5）。
- B. **訊息帶 `v` 欄位 ＋ 伺服器端拒絕不支援的版本**：握手時比對，不相容即以
   明確錯誤關閉連線，前端提示重新整理。代價：多一組版本常數要維護，而單一部署
   單元下它多數時候恆等。
- C. **以 `Sec-WebSocket-Protocol` 承載版本**（該標頭已被 `[RA:FR8.5]` 用來帶 token，
   可再帶一個版本 token）。代價：把兩件事塞進同一個標頭，且該標頭的透傳性
   `OQ-8` 尚未實測。
- X. Other（請說明）

[Answer]: B
<!-- 作答時間 2026-09-26T04:21:00Z（`date -u`）。選 B（訊息帶 `v` 欄位，握手時比對，不相容即以明確
     錯誤關閉連線）。

     **本站的建構性解讀（非新定案，記此以免下游誤讀）**：`[RA:FR8.5]` 已定 token 走
     `Sec-WebSocket-Protocol` 標頭或握手後首則訊息，而使用者**未**選 C（版本走同一個
     標頭）。兩者相加後唯一自洽的形狀是：token 走 `Sec-WebSocket-Protocol`、版本走
     **握手後的首則訊息**（`hello`），伺服器以 `ready` 或版本錯誤關閉回應。因此
     「握手時比對」在本契約中指的是**首則訊息的比對**，不是 HTTP upgrade 階段。
     此為兩個已定案相加後的唯一解，非本站另作選擇。

     與 C2=A 的銜接：`v` 欄位是 Pydantic 模型的一部分，故自動進入 `ws-contract.json`
     與前端型別，由兩道 gate 保護。
     與 C5=B 的區分：版本不相容是**握手階段的拒絕**，與 C5 處理的「串流中途斷線」
     是兩件事，契約須分開描述。 -->

---

### C5. WS 邊界的失敗行為：串流中途斷線

`SessionContext` 的狀態在 Redis、TTL 24 小時（`[DD:E6]`=A），所以斷線後 session
本身還在。要釘死的是**那一則未完成的回覆**怎麼算。

- A. **重連後從 session 狀態接續，未完成的那則標記為中斷並可重試**：前端重連、
   伺服器由 session 找回該工作項，畫面顯示「連線中斷，已保留進度」並提供重試。
   代價：工作項需有「串流中斷」這個可觀察狀態；`WorkItem.status` 的五值集合
   （`[DD]` 定案「不得少於五個」）需確認能否表達它，或由 `sideEffect` 承載。
- B. **重連即為新的一輪，未完成的那則捨棄並明確告知**：畫面把該則標為未完成、
   不自動重試，使用者自行重問。最簡單，且與 `sideEffect: unknown` 的誠實立場一致。
- C. **伺服器緩衝並在重連後重播**：保證不漏字。代價：要在 Redis 存部分回覆，
   且重播與冪等性要處理。
- X. Other（請說明）

[Answer]: B
<!-- 作答時間 2026-09-26T04:21:00Z（`date -u`）。選 B（重連即為新的一輪；未完成的那則明確標示、
     不自動重試）。理由與 domain-design 已定的 `sideEffect: unknown` 誠實立場一致：
     系統不承諾停掉時不留半成品，也就不該假裝能完美接續。
     與 C6 的銜接：C6 明定「若連線中斷而未收到終止事件，依 C5 標為未完成，
     不自動重試」——兩題的答案互相引用且一致。 -->

---

### C6. 大腦的串流可否以零內容結束（承 `mockups.md` H-7）

`refined-mockups` 自檢查出 `StreamingMessage.empty-stream` 這個狀態**可達性未驗證**，
並指派本站。注意 `[RA:FR1.5]` 的 `prompt_guard` 命中回的是**固定訊息**，那是有內容
的，不走此態。所以問題是：除了 guard 之外，大腦是否可能一個 token 都沒送就 `done`。

- A. **契約保證至少一個內容 token 才能送 `done`**：零內容的情況一律改送 `error`
   並帶原因碼。`empty-stream` 因此成為不可達的防禦性死碼，應從畫面規格移除或
   明標為不可達。這讓「畫面空白」在執行期無法發生。
- B. **允許零內容 `done`，但必須帶一個原因碼**（如 `no_answer`），畫面據此顯示
   具體訊息而非空白。`empty-stream` 為真實態並有明確觸發條件。
- C. 維持現狀：不在契約層規定，留給實作。代價是 `project.md` 的 `functional-design:c10`
   警告的形狀——文件上看起來已解決，實際上那個狀態的可達性沒人驗證過。
- X. Other（請說明）

[Answer]: X — 使用者以自訂規格作答（逐字收錄於下）
<!-- 作答時間 2026-09-26T04:21:00Z（`date -u`）。使用者未選 A／B／C，改給出完整規格。以下為
     **使用者原文逐字**，不改寫、不摘要（依 `team.md`「不得摘要或代答使用者輸入」）： -->

> `done` 代表已成功產出可呈現的回覆。純文字回覆必須包含非空白文字；內部推理、
> 控制事件與空白不算內容。上游結束但未產出有效回覆時，後端必須送出
> `error(code: EMPTY_RESPONSE)`，不得送出 `done`。每次回覆最多只能有一個終止事件
> （`done` 或 `error`）；終止後不得再送內容。若連線中斷而未收到終止事件，依 C5
> 標為未完成，不自動重試。前端收到 `EMPTY_RESPONSE` 時顯示明確錯誤提示；若收到
> 零內容的 `done`，視為契約違規，顯示備援提示並記錄異常，不呈現空白成功態。
> H-7 改為描述這兩種情境。`prompt_guard` 命中的固定訊息屬於有效回覆，正常以
> `done` 結束。

<!-- 本站對這份規格的理解（供產出撰寫，不取代原文）：它比選項 A 嚴格且更完整——
     A 只說「empty-stream 成為不可達的死碼」，使用者的規格額外要求**前端仍須有
     備援處置並記錄異常**。也就是：契約上零內容 `done` 不可能發生，但前端不假設
     對方守約，收到就當契約違規處理而非渲染空白成功態。這是「契約保證」與
     「防禦性實作」兩件事分開，比單純刪掉那個狀態更強。
     `mockups.md` 的 H-7 依使用者指示改為描述 `EMPTY_RESPONSE` 與「零內容 done ＝
     契約違規」兩種情境——**本站不回改已核可的 `mockups.md`**，依
     `project.md` `units-generation:260822-ug-L2` 的形狀：標出缺口、寫明落點與具體
     修法，指派下游。 -->

---

### C7. 同進程邊界的契約要寫到什麼程度

25 條邊中，多數兩端都在**同一個 FastAPI process**（`unit-of-work.md` 的部署模型欄：
除 `U9`／`U17` 跑在 GitHub Actions 外皆為 embedded）。對這些邊寫 OpenAPI 沒有意義，
但完全不寫又失去「多單元平行開工」的價值——而那正是本站存在的理由。

- A. **模組公開介面 ＋ 資料形狀**：每條同進程邊寫出被依賴方的公開函式簽章
   （名稱、參數、回傳型別、會 raise 什麼）與跨邊界的資料結構，以
   ```yaml shared-schema``` 區塊承載。跨行程的邊（WS、HTTP、DB schema、env）
   才用 OpenAPI／AsyncAPI／DDL。
- B. **只寫資料形狀，不寫函式簽章**：介面留給實作，契約只鎖跨邊界的資料結構。
   代價：平行開工時兩邊對「怎麼呼叫」沒有共識，整合時才發現。
- C. **全部邊都寫成 HTTP 契約**（配合 C1 選 B 時）：形式統一，但會把不需要網路
   往返的邊也逼成網路呼叫。
- X. Other（請說明）

[Answer]: X — 使用者以自訂規格作答（逐字收錄於下）
<!-- 作答時間 2026-09-26T04:21:00Z（`date -u`）。使用者未選 A／B／C，改給出完整規格。以下為
     **使用者原文逐字**： -->

> 同進程邊界以「公開介面、資料形狀、必要行為語意」定義契約。每條邊列出被依賴方的
> 公開函式名稱、參數、回傳型別、同步／非同步形式，以及呼叫方必須處理的例外；
> 跨邊界資料結構以 shared-schema 區塊承載。必要行為語意包含授權責任、可觀察副作用，
> 以及重試或冪等性限制；不限定內部實作細節。C1 的授權門面明訂為受保護操作的唯一
> 授權入口，並定義身分與資源上下文如何傳入、拒絕時如何回報，以及授權未通過時不得
> 執行受保護操作。各類邊界使用符合實際機制的描述：HTTP 使用 OpenAPI；WS 沿用 C2 的
> Pydantic → JSON 契約 → TS 型別與兩道 CI gate；資料庫使用 DDL／migration；環境變數
> 列出名稱、型別、必填性、預設值與驗證規則。同進程介面不轉成 HTTP。

<!-- 本站對這份規格的理解：它是選項 A 的擴充版，多了三項 A 沒有的要求——
     (1) 每條邊要標明**同步／非同步形式**；(2) 行為語意要含**重試或冪等性限制**；
     (3) **環境變數也是一類契約**，須列名稱／型別／必填性／預設值／驗證規則
     （這正好讓 `U1 brain-infra` → `U5`／`U6`／`U10` 三條邊有了契約形式，並與
     `project.md ## Mandated` 的 `render-env.sh` ＋ `.env.example` 同步規則接上）。
     末句「同進程介面不轉成 HTTP」明確排除選項 C，與 C1=C 一致。 -->

---

### C8. 大腦的 LLM 邊界是否提供測試注入接縫，以及它算不算契約的一部分

**這題是本站的覆蓋檢查補上的，不在原本七題內。** `user-stories` 的
quality-agent 貢獻檔 §10 把「**注入接縫與 12 條 B3 級 AC 的落點**」指派給本站，
我第一版出題時漏了它。該檔把 62 條 AC 分桶，其中 **B3（需要真實模型回應 →
目前無任何層可測）共 12 條**：`AC1.1.1`、`AC1.1.4`、`AC1.3.2`、`AC1.3.3`、
`AC2.2.2`、`AC3.1.3`、`AC5.1.1`、`AC5.1.3`、`AC6.1.1`、`AC6.1.2`、`AC6.1.3`、
`AC10.1.1`。另有 **B1 的兩條**（`AC1.1.2`、`AC1.2.2`）逐字寫明「沒有接縫會滑進 B3」。

它逐字的建議是抄既有前例 `backend/cost/advice_orchestrator.py:28–30`：

```python
# Injected by tests
_run_agent: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None
_session_factory: Optional[Callable[[], Session]] = None
```

而 `backend/tests/test_cost_advice_agent.py:35,42,45,46` 是它的使用與還原樣板
（`setUp` 指派 lambda、`tearDown` 設回 `None`）。**本站已實讀這兩處，形狀屬實。**

`C3`=B（大腦自建執行層）之後，接縫的落點就是大腦自己的 runtime 模組。問題是
它要不要被寫進**契約**——寫進去代表它是被依賴方對呼叫方（測試）的正式承諾，
改它要當成破壞性變更；不寫進去則它只是實作細節，下一個人重構時可以無聲拿掉。

- A. **接縫是契約的一部分，形狀抄既有前例**：大腦的 runtime 模組宣告模組層
  `_run_agent`（與 `_session_factory`，若它需要 DB），契約明寫其型別簽章、
  「`None` 表示走真實路徑」的語意，以及測試必須在 `tearDown` 還原。
  12＋2 條 AC 因此落在 backend `unittest`（B1 桶），不進手動桶。
  代價：接縫是公開承諾，之後不能無聲移除；且它是生產程式碼裡的測試用鉤子。
- B. **提供接縫但不列入契約**：實作時照做，但契約不記載，視為實作細節。
  代價：下一個人重構大腦 runtime 時沒有任何東西告訴他這 14 條 AC 靠它活著——
  拿掉即靜默失去自動化覆蓋，而 CI 不會紅燈（測試會被改掉或跳過）。
- C. **不用模組層接縫，改用依賴注入**：路由層的 LLM 呼叫經建構子或參數注入，
  測試傳替身進去。較乾淨，但與 `advice_orchestrator` 的既有形狀不一致，
  且大腦的呼叫點在 WebSocket handler 深處，注入鏈較長。
- D. **不設接縫**：那 12＋2 條 AC 歸「只能手動」桶。代價：`project.md` 的
  tcms 必做 1 逐字禁止「預設丟給手動」，這會是一次明知故犯的例外，
  須在 `tcms-test-cases` 站說明理由。
- X. Other（請說明）

[Answer]: X — 使用者以自訂規格作答（逐字收錄於下）
<!-- 作答時間 2026-09-26T04:26:03Z（`date -u`）。使用者未選 A／B／C／D，改給出完整規格。以下為
     **使用者原文逐字**： -->

> 大腦 runtime 必須提供可替換的 LLM 執行介面，列入內部契約，明訂輸入、串流事件型別、
> 完成、錯誤與取消語意。正式環境組裝真實實作；測試可在 runtime 建立處注入替身，
> 不呼叫外部 LLM。測試替身須能確定性地模擬正常串流、零內容、部分輸出後失敗，
> 以及延遲／取消。若 session 建立涉及外部依賴，也應提供獨立的替換介面。替換作用域
> 以 runtime 實例或單次測試為限，避免共享可變全域狀態。契約承諾替換能力與行為語意，
> 不固定 `_run_agent`、`_session_factory` 等私有名稱，也不要求以 `None` 表示真實路徑。
> 既有模組層鉤子可作為過渡實作，但測試必須可靠還原，並避免並行測試互相污染。
> 14 條 AC 逐條對應自動化測試與 CI 執行項目；依驗證範圍分配至單元、WS 整合或前端測試，
> 不因提供 LLM 接縫就一律歸為 backend unittest。

<!-- 本站對這份規格的理解（供產出撰寫，不取代原文）：它比選項 A 強，且**明確否掉
     A 的兩處**——(1) 不釘 `_run_agent`／`_session_factory` 這兩個私有名稱；
     (2) 不要求以 `None` 表示真實路徑。契約承諾的是**替換能力與行為語意**，
     不是特定符號。另外三項是 A 沒有的要求：
     (a) **替換作用域限於 runtime 實例或單次測試**，不得共享可變全域狀態——這直接
         指出既有前例 `advice_orchestrator` 的模組層鉤子是**過渡實作**而非目標形狀
         （模組層變數就是共享可變全域狀態，並行測試會互相污染）；
     (b) 測試替身須能確定性模擬**四種**情境：正常串流、零內容、部分輸出後失敗、
         延遲／取消。前兩者正好對應 C6 的 `EMPTY_RESPONSE` 契約，第三者對應 C5 的
         串流中途斷線——三題的答案互相咬合；
     (c) **14 條 AC 依驗證範圍分配**至單元／WS 整合／前端，不一律歸 backend unittest。
         這修正了 quality-agent 貢獻檔的假設（它逐字寫「上述 12 條的行為面可以在
         backend unittest 決定性地測」）與本站選項 A 的同一假設。本站的產出須逐條
         列出這 14 條的分配，不得概括。 -->

---

### C9. C3=B 的「一致性契約測試」到底鎖什麼（`OQ-7` 的字面主題：一致性驗證**範圍**）

**這題由 C8 逼出來，是本站一致性檢查的結果。** C3=B 的選項文字說「另寫一份契約
測試鎖住兩者的**事件語意**與 client 設定一致」。但 C8 的規格要求大腦 runtime
「明訂輸入、**串流事件型別**、完成、錯誤與取消語意」——也就是大腦**本來就有自己的
事件型別**，而那正是 C3 選 B 的理由（`stream_graph`／`astream_graph` 把 `kind`
硬寫為 `"updates"`，無法表達 token 級串流）。

**所以「鎖住事件型別一致」在邏輯上不可能**：若兩者事件型別相同，就沒有分家的理由；
既然分家了，就不能再要求相同。`OQ-7` 逐字問的是「一致性驗證**範圍**」，這一題把它
定下來。

**一個必須先說的查證結果**：`OpenRouterSettings` 這個 dataclass（`:52`）看起來是
現成的「設定物件」，但全樹**沒有任何地方建構或讀取它**——`openrouter_chat_model`
直接讀模組層常數（`:85–98`：`DEFAULT_OPENROUTER_BASE_URL`／
`DEFAULT_OPENROUTER_MODEL`／`DEFAULT_TIMEOUT_SECONDS`）。它只出現在自己的定義與
`__all__`（`:158`）裡，是**死碼**。因此「用 `OpenRouterSettings` 鎖設定一致」這個
最直觀的答案行不通；真正的共用面是那三個常數 ＋ `max_retries=0` ＋
`RuntimeAuthError.code`。

- A. **共用 client factory ＋ 宣告事件語彙對照表**：大腦只分家「圖的執行與事件
  型別」，client 一律經既有的 `openrouter_chat_model()` 取得（可帶 `model=` 覆寫
  路由層模型）。測試斷言兩件事：(1) 大腦**不自建** `ChatOpenAI`；(2) 契約內的
  事件語彙對照表涵蓋雙方**全部**事件種類，任一方新增事件而對照表未更新即紅燈。
  **請注意**：這在 client 那一半等於 C3 的選項 C（「自建但共用 client」），
  我如實指出這個重疊，不假裝它是 B 的原樣。
- B. **不共用 factory，改鎖連線常數與憑證錯誤碼** ＋ 事件語彙對照表：大腦建自己的
  client，測試斷言它的 base_url／憑證環境變數名／預設逾時／`max_retries` 與既有
  常數逐項相同，且憑證缺失時拋出同一個 `code`。代價：四個常數各有兩份，靠測試綁住；
  常數本身仍可能被兩邊各自改。
- C. **最小範圍：只鎖憑證來源與 base_url**：兩者必須讀同一個 `OPENROUTER_API_KEY`
  並打同一個 base_url，其餘（逾時、重試、事件語彙）各自自由。代價：`OQ-7` 想防的
  「兩套語意漂移」基本上不防，只防「打到不同的服務」。
- D. **不做一致性測試，改以 ADR 記載刻意分家的理由**：把 R-8 從「要驗證的風險」
  改為「已接受的設計決定」。代價：`team.md ## Code Style`「單一真實來源」逐字要求
  新增副本的**同一個 PR** 必須一併新增鎖住一致性的測試，且「無法寫測試的副本不新增」
  ——選 D 需要一條明確的例外理由，而非默默不做。
- X. Other（請說明）

[Answer]: X — 使用者以自訂規格作答（逐字收錄於下）。**本題主旨未被回答，另見下方 C10／C11**
<!-- 作答時間 2026-09-26T04:38:25Z（`date -u`）。以下為**使用者原文逐字**： -->

> 大腦採按需呼叫策略：可由程式規則、既有狀態或明確指令決定的流程，不呼叫模型。
> 需要分類或路由時才使用 Jev；若文字 LLM 本身即可直接完成任務，不額外增加 Jev
> 前置判斷。只有需要生成自然語言回答時才呼叫文字 LLM。Jev 僅接收決策所需的最少
> 上下文；同一狀態下互不相依的判斷合併請求。限制文字模型的上下文與輸出長度，
> 設定每輪模型呼叫次數、重試次數與用量上限，避免無限升級或重試。C8／C9 的一般 CI
> 使用可注入替身，不呼叫付費模型。真實模型品質以獨立、小樣本且有預算上限的評估驗證。
> client 設定各自在 provider adapter 集中管理；本階段不建通用多模型框架，也不因
> 可擴充性預先加入額外模型。

<!-- **本站的處置（如實記載，不代答）**：

     (1) **本題主旨未被回答。** C9 問的是「C3=B 的一致性契約測試斷言什麼」。上文唯一
         觸及該主旨的是「client 設定**各自**在 provider adapter 集中管理」——「各自」
         指向選項 B 的形狀（各自建 client、設定集中於自己的 adapter），但未說測試
         斷言什麼。故本題以 **C11** 重新提問，不由本站推定。

     (2) **與三條已核可需求牴觸，經逐字核對**：
         - `[RA:FR1.1]` 逐字「判定其意圖類別，並把工作交辦給對應的既有功能能力」，
           無條件適用於入口頁的每一次輸入。
         - `[RA:FR1.6]` 逐字「路由層**必須**輸出一個可與門檻比較的信心值，定義域 0–1。
           **這是一條獨立需求，不是 FR1.3 的前提句**——若實作出一個不輸出信心值的
           路由層，FR1.3 會**靜默永不觸發**」。
         - `[RA:FR1.3]` 逐字「當意圖判定的信心未達門檻時，系統**不得交辦、不得產生
           任何結果**」。
         上文的「若文字 LLM 本身即可直接完成任務，不額外增加 Jev 前置判斷」與
         「可由程式規則、既有狀態或明確指令決定的流程，不呼叫模型」會產生一條
         **未算過信心值就產生回覆**的路徑——正是 FR1.6 明文要防的失敗模式。
         處置：以 **C10** 把反轉範圍交給使用者界定（新增能力 vs 取代既有決定；
         就地修訂上游 vs 重跑受影響的 stage），依 `project.md`
         `260916-estimate-upload-rework:approval-handoff` 的規則，**不由本站吸收**。

     (3) **兩處超出本站範圍、如實標記為「本階段新增、已核可 scope 尚未涵蓋」**：
         - 點名 **Jev** 作為分類器，實質落地 `OQ-4`（路由層模型定案，
           `typesafe/jev-1.13` vs `gemini-3.7-flash`），而該項指派 `nfr-requirements`
           且上游標明**無自然承接站**。
         - 「設定每輪模型呼叫次數、重試次數與用量上限」超出 `[RA:NFR9]`，該條逐字
           寫「此為設計原則，**非可量測的門檻**」。上文要的是實際強制的上限。
         兩項皆記入產出的回補清單，不在本站定案。

     (4) **可直接採納、與上游無衝突的部分**（寫入契約）：Jev 僅接收決策所需的最少
         上下文；同一狀態下互不相依的判斷合併請求；限制文字模型的上下文與輸出長度；
         一般 CI 使用可注入替身、不呼叫付費模型（與 C8 一致，且解決 quality-agent
         指出的「`build-and-test` 沒有金鑰」缺口）；真實模型品質以獨立、有預算上限的
         評估驗證（與 `[RA:NFR1]` 的 ≥ 50 筆標註集相容——50 筆即小樣本）；
         client 設定集中於各自的 provider adapter；本階段不建通用多模型框架。 -->

---

### C10. 按需呼叫策略與已核可的 `FR1.1`／`FR1.3`／`FR1.6` 牴觸——反轉範圍由使用者界定

C9 的回答要求「可由程式規則、既有狀態或明確指令決定的流程，不呼叫模型」與
「若文字 LLM 本身即可直接完成任務，不額外增加 Jev 前置判斷」。這與三條已核可需求
直接牴觸（逐字見 C9 的處置註記）：`FR1.1` 無條件要求判定意圖類別；`FR1.6` 無條件
要求路由層輸出 0–1 信心值，並**明文指出**不這樣做會讓 `FR1.3` 靜默永不觸發；
`FR1.3` 要求信心不足時不得交辦、不得產生任何結果。

依 `project.md` 的規則，本站**不自行吸收**這個反轉，把範圍界定交給使用者。

- A. **新增一條「快路徑」，`FR1.6` 的信心值義務只約束走 LLM 分類的那條路**：
  規則／既有狀態／明確指令可決定者走快路徑，不呼叫模型、也不產生信心值；
  其餘照 `FR1.1`／`FR1.6`／`FR1.3` 原樣。契約須明訂**快路徑的判定條件是白名單式
  且可窮舉**（否則它會逐漸吃掉分類路徑，`FR1.3` 實質失效）。
  這是**新增能力**，不推翻既有決定；`requirements.md` 須回補一條 `FR1.9` 之類的
  條目描述快路徑及其邊界。
- B. **取代既有決定**：`FR1.1`／`FR1.6` 改為有條件適用，`FR1.3` 的觸發條件改寫。
  這推翻三條已核可需求，依協定須回跳 `requirements-analysis`（2.3，**ALWAYS**）
  以 Modify 模式修訂並重走其核可關卡，`user-stories`／`domain-design`／
  `units-generation` 受影響處一併重審。成本明確較高。
- C. **不採用按需呼叫策略的這一半**：保留 C9 中不衝突的部分（最少上下文、合併請求、
  長度與次數上限、CI 用替身、評估預算上限、adapter 集中設定），但**每一次入口頁輸入
  仍一律先過分類並產生信心值**。`FR1.1`／`FR1.3`／`FR1.6` 不動。省錢的效果靠
  「分類用便宜模型 ＋ 最少上下文」達成，而非靠跳過分類。
- X. Other（請說明）

[Answer]: C
<!-- 作答時間 2026-09-26T04:43:39Z（`date -u`）。選 C（不採「跳過分類」那一半）。後果：

     **`FR1.1`／`FR1.3`／`FR1.6` 三條原樣保留，不需回跳 `requirements-analysis`。**
     每一次入口頁輸入一律先過分類並產生 0–1 信心值；省成本靠「分類用便宜模型 ＋
     最少上下文」，不靠跳過分類。

     **C9 中保留並寫入契約的部分**（與三條需求無衝突）：Jev／分類器僅接收決策所需的
     最少上下文；同一狀態下互不相依的判斷合併請求；限制文字模型的上下文與輸出長度；
     設定每輪模型呼叫次數、重試次數與用量上限；一般 CI 使用可注入替身、不呼叫付費
     模型；真實模型品質以獨立、有預算上限的評估驗證；client 設定集中於各自的
     provider adapter；本階段不建通用多模型框架、不因可擴充性預先加入額外模型。

     **C9 中被本題排除的部分**：「可由程式規則、既有狀態或明確指令決定的流程，不呼叫
     模型」與「若文字 LLM 本身即可直接完成任務，不額外增加 Jev 前置判斷」——這兩句
     會產生未算信心值即回覆的路徑，已由本題排除。

     **仍未定案、不由本站定案者**：C9 點名 **Jev** 作為分類器。C10=C 只決定「一律
     先分類」，**不決定用哪個模型**。`OQ-4`（路由層模型定案：`typesafe/jev-1.13` vs
     `gemini-3.7-flash`）維持指派 `nfr-requirements`（CONDITIONAL、**無自然承接站**、
     skip 時須重新提交使用者）。本站把使用者對 Jev 的**偏好**如實記入產出的交接表，
     供該站權衡——記錄偏好不等於定案。

     **仍屬「本階段新增、已核可 scope 尚未涵蓋」者**：「每輪模型呼叫次數、重試次數
     與用量上限」超出 `[RA:NFR9]`（該條逐字「此為設計原則，**非可量測的門檻**」）。
     本站寫入契約的是這些上限**必須存在且可設定**，具體數值不在本站定案，記入回補
     清單。 -->

---

### C11. 重問 C9 的主旨：一致性契約測試斷言什麼

C9 的回答只以「client 設定**各自**在 provider adapter 集中管理」觸及本題，該句指向
下方選項 B 的形狀，但未說測試斷言什麼。四個選項與 C9 提問時相同，僅依 C9 已表明的
「各自管理」與「不建通用多模型框架」兩點重排順序並就地標註。

- B. **各自 adapter ＋ 測試鎖連線常數與憑證錯誤碼 ＋ 事件語彙對照表**
  （**與 C9 的「client 設定各自在 provider adapter 集中管理」一致**）：
  大腦有自己的 provider adapter，測試斷言它的 base_url／憑證環境變數名／預設逾時／
  `max_retries` 與既有常數逐項相同，憑證缺失時拋出同一個 `code`；另有一份事件語彙
  對照表涵蓋雙方全部事件種類，任一方新增而對照表未更新即紅燈。
- A. **共用既有 `openrouter_chat_model()` factory ＋ 事件語彙對照表**：
  與 C9 的「各自管理」措辭不符，列此供比較。
- C. **最小範圍：只鎖憑證來源與 base_url**：其餘各自自由。`OQ-7` 想防的「兩套語意
  漂移」基本上不防。
- D. **不做一致性測試，改以 ADR 記載刻意分家的理由**：需要一條明確的例外理由來對抗
  `team.md ## Code Style`「單一真實來源」的「無法寫測試的副本不新增」。
- X. Other（請說明）

[Answer]: B
<!-- 作答時間 2026-09-26T04:43:39Z（`date -u`）。選 B（各自 provider adapter ＋ 測試鎖連線常數與憑證
     錯誤碼 ＋ 事件語彙對照表），與 C9 的「client 設定各自在 provider adapter 集中
     管理」一致。

     本站據此撰寫 `langgraph-consistency` 契約，斷言項逐條如下（皆為可機械判定）：
     1. 大腦 adapter 的 base_url == `DEFAULT_OPENROUTER_BASE_URL`（`langgraph_runtime.py:16`）
     2. 憑證環境變數名 == `OPENROUTER_API_KEY_ENV`（`:19`）
     3. 預設逾時 == `DEFAULT_TIMEOUT_SECONDS`（`:18`）
     4. `max_retries` == 0（`openrouter_chat_model` 內逐字，`:96`）
     5. 憑證缺失時拋出的錯誤帶同一個 `code`（`RuntimeAuthError.code`，
        預設 `"missing_openrouter_api_key"`，`:22–34`）
     6. 事件語彙對照表涵蓋雙方**全部**事件種類；任一方新增事件而對照表未更新即紅燈

     **不納入斷言的**：預設 model。`[RA:NFR10]` 明文要求路由層得與功能 agent 用不同
     模型，故 model 必須可以不同，鎖它會與 NFR10 衝突。
     **不使用 `OpenRouterSettings` 作為鎖定載體**：該 dataclass 全樹無人建構或讀取
     （只出現於自身定義與 `__all__`），是死碼；鎖它等於鎖一個沒有效力的物件。 -->

---

## Consolidated Summary Confirmation

<!-- 待所有問題作答後填入 -->

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- 作答時間 2026-09-26T10:11:21Z（以 `date -u` 取值）。redo jump 後第五次重取（修訂 4 的收據 ec7f24b2 已因站重置而失效）。

     **為什麼走到 redo jump（如實記載，這是我的流程失誤且是重複犯）**：
     閘門 Request Changes 後我報 `revised`，該報告把本站置為 `[R]`（revising）。
     之後我修完、取確認、請求審查、審查給 READY，報 `approved` 時以
     `REVIEW_EVIDENCE_MISSING` 被拒——因為站在 `[R]`，閘門從未開過，兩份 READY 收據
     （review-04 的 iteration 1、review-06 的復原審查 iteration 2）都掛在一個 revising
     的站上。**units-generation 那一站踩過完全相同的陷阱**，我當時寫下的檢查是
     「報 `awaiting-approval` 之後驗 checkbox」——但那個時點是錯的，正確時點是
     **請求審查之前**。redo jump 於 2026-09-26T10:08:41Z 完成，作答與產出皆保留。

     **產出內容自修訂 4 起未改動。** 本站歷程摘要：
     - 11 題定案（C1–C11），其中 C6／C7／C8／C9 為使用者自訂規格、逐字收錄。
     - 四輪完整審查 ＋ 一輪復原審查，findings 到 R-16。
     - R-01～R-13 全部 Resolved；R-16 Resolved；**R-14（Critical）與 R-15（Major）
       為 `Accepted risk`**——使用者在閘門逐字看過後選擇記成 open items，已寫成
       `OQ-N3`／`OQ-N4` ＋ 交接列 `J-14`／`J-15`。
     - 產出規模：17 條契約、19 個 fenced spec 區塊（19/19 合法 YAML）、
       `[C7]` 四項 17/17、9 項回補、15 項交接、15 條 Open Questions、兩支 sensor 綠。

     **帶進閘門的已知不足**：`OQ-N3`（記憶無寫入端，`U5`／`U8`／`U9`／`U15` 四單元惰性、
     四條 `FR4.*` 失去機制）、`OQ-N4`（`BrainSession` 撐不起「兩段」歷程）、
     `OQ-N1`（無人擁有「產生自然語言回覆」）、`OQ-N2`（facade 唯一性無機械強制）、
     `OQ-4`（路由層模型未定案且無自然承接站）、呼叫上限數值不在本站定案。 -->
