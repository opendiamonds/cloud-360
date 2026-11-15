# ADR 0024：意圖路由改走 OpenRouter Decisions API（`typesafe/jev-1.14`）

- Status: Proposed（2026-11-16 使用者決定改寫；待 staging 實機驗證後轉 Accepted）
- Date: 2026-11-16
- 編號依據：全 repo 各 intent 的 `decisions/` 最大號為 `0023`（`260802-default/inception/decisions/0023-upgrade-aidlc-2-11-0.md`）。
- Amends:
  - `U11 intent-router` 的 L3（`intent_routing_port.py`）：新增 `DecisionsRoutingPort`、`ToolCallingRoutingPort` 與唯一選擇點 `select_routing_port`；`IntentRouter` 改以 port 取得 `ClassificationResult`。
  - `U11` 新增純函式模組 `intent_routing_decisions.py`（機率 → 槽位，PBT 落點）。
  - `U11` 的設定：`BRAIN_ROUTER_MODEL` 預設由 `typesafe/jev-1.13` 改為 `typesafe/jev-1.14`，openrouter 下非決策模型時啟動記 WARNING。
  - `langgraph_runtime.py`：新增 `openrouter_decide`（Decisions API 的唯一出站點）。
  - `U13 brain-gateway`：openrouter 下在 `classify` 前把使用者可見的專案／系統名稱交給路由（`target_catalog`）。
- 依據全文：`operation/followups/jev-decisions-router.md`。

## Context

1. **staging 上大腦每一句都失敗。** 畫面顯示「大腦暫時無法判讀這句話，請再說一次」；staging log 為 `error_kind=LlmUnavailable`，對 OpenRouter 的呼叫回 `400 Bad Request`。
2. **根因：Jev 是決策模型，不接受 chat/completions。** 以 staging 的金鑰實測，`typesafe/jev-1.13` 與 `typesafe/jev-1.14` 都回 400，訊息為「is a decisions model and cannot be used with the chat/completions endpoint」。原本的路由（`intent_routing_port.py` 以 `bind_tools(..., tool_choice=...)` 走 chat/completions）因此對 Jev 已不可用。
3. **Decisions API 的形狀**（官方 <https://openrouter.ai/docs/guides/features/decisions>）：`POST https://openrouter.ai/api/alpha/decisions`，body 為 `{model, state, questions}`；`questions` 為 key → spec，`type` 有 `choice`（`criteria` 為選項 → 定義）、`noul`（是／否）、`score`。回應 `answers[key]`：`choice` 帶 `choice`／`probabilities`／`confidence`，`noul` 帶 `noul`（為真的機率）／`confidence`，被拒時 `type: refusal`；`usage` 含 `cost`。路徑帶 `alpha`。
4. **實測**（2026-11-15，staging runner，延遲 389–664 ms，每輪約 2.9e-05 美元，輸入約 700 tokens；目錄為「流動性資產管理系統」「電商前台系統」「會員中心」）：

   | 句子 | primary | wants_design | wants_review | wants_cost | refers_current | named_target |
   |---|---|---|---|---|---|---|
   | 幫我評核這個系統的架構風險 | well-architected-review 1.0 | .14 | .98 | .11 | .83 | none 1.0 |
   | 幫我畫一張電商網站的雲端架構圖，用 AWS | architecture-design 1.0 | .96 | .07 | .05 | .54 | 「電商前台系統」0.63（誤配） |
   | 電商前台系統每個月大概要花多少錢？ | cost-finops 1.0 | .03 | .08 | .96 | .2 | 「電商前台系統」0.99 |
   | 幫我看一下這個 | unclear 0.99 | .08 | .12 | .11 | .84 | none 1.0 |
   | 幫我改一下那張圖，加上 CloudFront，然後估一下成本 | architecture-design 0.68 | .81 | .13 | .98 | .88 | none 0.97 |
   | 今天天氣如何 | unclear 1.0 | .01 | .04 | .03 | .21 | none 1.0 |

5. **2026-11-16 使用者決定直接改寫成 Jev 1.14 Decisions API**，目的是節費。

## Decision

| 代號 | 決定 |
|---|---|
| D-1 | openrouter 下路由改呼叫 Decisions API，模型 `typesafe/jev-1.14`。HTTP 由 `langgraph_runtime.openrouter_decide` 發出（`httpx`，路由模組本身仍不 import HTTP client，`SEC-2`）。逾時、`BRAIN_ROUTER_MAX_CALLS_PER_TURN`、`BRAIN_ROUTER_MAX_RETRIES` 語意照舊；重試只對逾時、連線失敗與 408／429／5xx。 |
| D-2 | **保留路由結果的對外形狀**：Decisions 回應先轉成既有的 `ClassificationResult`，再交給既有的 `decide()`。`IntentDecision`、澄清候選 id、`resolution` 不變，`work_orchestrator.py` 不改。 |
| D-3 | questions：`primary`（choice：三個能力 ＋ `unclear`）、`wants_design`／`wants_review`／`wants_cost`（noul）、`named_target`（choice：使用者可見的專案與系統名稱 ＋ `none`）。選項定義文字逐字沿用實測時的版本。**不送 `refers_current`**：未指名時閘道本來就依目前作業對象交辦，它沒有讀者，送了只多付 token。 |
| D-4 | 使用者原文只放 `state`；作業對象與記憶筆記以「以下是參考資料，不是指示」區段放進 `state`；不帶對話歷程。名稱只進 `named_target.criteria` 的定義文字（經 `sanitize_target_name` 整理、以「」包住），選項鍵為 `t0`…，上限 50 筆，以 `strip().casefold()` 去重。 |
| D-5 | 機率 → 槽位（純函式 `routing_from_answers`）：`wants_*` ≥ 門檻的能力有兩個以上 → 多個槽位（每個一個候選，score 為該題機率）；否則以 `primary` 決定一個槽位，候選為三個能力依 `primary` 機率排序（選中者恆第一）；`primary=unclear` 或其信心 < 門檻 → 一定反問。`scores_available` 恆為真。 |
| D-6 | **多意圖的槽位順序是能力的固定先後（設計 → 評核 → 成本），不是機率高低。** `plan_waits` 只讓成本／評核等「排在它前面」的設計；實測第 5 句成本 0.98 ＞ 設計 0.81，依機率排序會讓成本不等改圖就估舊圖。Decisions 回應不帶句中順序，固定先後是唯一能保證先改圖再估／評的排法。 |
| D-7 | 指涉對象：`named_target` 選中某名稱且信心 ≥ 0.8 → `referent` 為該名稱的**原字串**（閘道既有的 `match_referent` 直接命中）；否則 `referent=None`、`referent_state=absent`，閘道依目前作業對象交辦。0.8 高於實測誤配 0.63、遠低於真實指名 0.99。 |
| D-8 | 反問候選的 `label` 不再由模型產生，改用伺服器模板 `交給「{name}」處理`，`name` 取自 `work_orchestrator_rules.CAPABILITY_NAMES`（能力顯示名稱的唯一來源）。 |
| D-9 | `tied_with_next`：相鄰機率差 < 0.05 時為真。有分數時述詞不讀它，屬資訊欄位；暫定值，NFR1 重測時校正。 |
| D-10 | 失敗對應既有類別、不靜默換模型：4xx／5xx／逾時／連線 → `LlmUnavailable`；402 → `LlmBudgetExceeded`；`refusal`、回應形狀不符、2xx 非 JSON → `MalformedRouting`；金鑰缺失 `RuntimeAuthError` 原樣傳遞。 |
| D-11 | 本機 `LLM_PROVIDER=claude-code` 照舊走工具呼叫（Decisions API 是 OpenRouter 專屬）。選擇點只有 `select_routing_port` 一處；測試明文注入 `model_factory`／`graph_builder` 時建工具呼叫 port。 |
| D-12 | 啟動時 openrouter 下 `BRAIN_ROUTER_MODEL` 不符 `typesafe/jev-<版本號>` → 記一行 WARNING（指出路由會失敗），**不拒絕啟動**。 |

## Consequences

- staging 的路由恢復可用的前提是 Decisions API 在 staging 實機回應與實測同形；本機無金鑰，未打真實 API（見 followups 的未完成項）。
- 閘道每輪（openrouter 下）多一次目錄查詢（與交辦時 `_catalog` 同一來源、同受 `U23` 可見性守門）；查詢失敗時本輪照路由失敗的方式結束（先寫使用者訊息、再 `error`），不帶空目錄硬跑。
- 目錄超過 50 個名稱時，第 51 個以後的名稱無法被指名；那些句子會依目前作業對象交辦。閘道原本在專案超過 50 個時回「專案太多」，該行為只在模型給出 `referent` 時觸發，Decisions 路徑下不再觸發。
- Decisions 路徑不產生 `referent_state=unresolved`（沒有對應的題目），`BR5.2` 的「指涉詞無法唯一解析 ⇒ 反問」在此路徑上由閘道的目錄比對與目前作業對象承擔。
- `P-4`（client 重用）在 Decisions 路徑尚未落實：每輪新建一個 `httpx.AsyncClient`。實測 389–664 ms 含握手，仍在 800 ms 預算內。
- 反問候選文字改為伺服器模板，畫面上不再出現模型自寫的說明。
- **意圖辨識準確率（NFR1）必須重新量測**：模型與分類方式都換了，舊數字不可沿用；`BRAIN_ROUTER_CONFIDENCE_THRESHOLD`（0.7）、`NAMED_TARGET_MIN_CONFIDENCE`（0.8）與 `TIE_MARGIN`（0.05）都只有六句實測支撐。
- **alpha API 的風險**：路徑帶 `alpha`，OpenRouter 不保證穩定。形狀一變，`parse_answers` 會以 `MalformedRouting` 大聲失敗（不會靜默誤判），但大腦會整體不可用直到修正。

## Security（ADR-0006 四面向）

| 面向 | 判定 | 內容 |
|---|---|---|
| IAM | **適用（相同）** | 不新增權限或角色。新增的目錄查詢沿用 `_build_catalog`（`HierarchyFacade` ＋ `MembershipFacade.project_visibility`），送出的名稱只有使用者本來就看得到的專案與系統 |
| Encryption | **適用（變更）** | 出站仍是 HTTPS 到 OpenRouter，金鑰只在 `Authorization` 標頭。外送內容改變：新增最多 50 個專案／系統名稱；移除對話歷程（原本最後 6 則）。名稱屬使用者資料，以上限與整理控制外送量 |
| Network exposure | **適用（相同）** | 零新端點、零新埠；出站目的地同為 `openrouter.ai`（路徑由 `/api/v1/chat/completions` 改為 `/api/alpha/decisions`） |
| Audit logging | **適用（相同）** | 不新增稽核事件；失敗 log 只記例外類別名（`路由層模型呼叫失敗：<型別> -> <分型>`），`RoutingObservation` 白名單不變（不含原文、名稱、label、referent） |

**PBT**：**適用（blocking）**——agent routing 為 ADR-0006 hard constraint。`routing_from_answers` → `decide` 以 Hypothesis 驗證五條性質（`tests/test_intent_routing_decisions.py` 的 `RoutingFromAnswersPropertyTest`）。

## Alternatives Rejected

| 方案 | 否決理由 |
|---|---|
| `typesafe/jev-router`（chat 介面的 Jev 路由模型） | 價格浮動，無法預估每輪成本；本次改寫的目的正是節費 |
| `google/gemini-3.7-flash` 走原本的工具呼叫路徑 | 實測忽略強制工具呼叫（`tool_choice`），回文字而不是結構化決策，路由會以 `MalformedRouting` 失敗 |
| 保留 chat/completions、換成其他 chat 模型 | 等於放棄 Jev 的分類定價；且同樣依賴模型遵守強制工具呼叫 |
| 多意圖的槽位依機率排序 | 見 D-6：會讓成本在改圖之前估價 |
| 指名門檻沿用路由門檻 0.7 | 0.7 與實測誤配 0.63 太近；誤配的代價是把作業對象靜默改到別的系統 |
