# 部署後追加：意圖路由改走 Jev 1.14 Decisions API

- 紀錄時間（`date -u`）：開工 `2026-11-15T16:21:40Z`，收尾 `2026-11-15T16:37:48Z`（UTC）
- 分支：`danniel/feat/jev-decisions-router`（從 `origin/ut` 的 `a821d8c` 開出，獨立 worktree）
- 未 commit、未 push、未跑 `gh`、未觸發 CI、未連 staging 或任何共用 DB／Redis；未改 `openapi.json`、`ws-contract.json`
- 架構決策：`inception/decisions/0024-intent-routing-via-jev-decisions-api.md`（Status: Proposed）

## 一、根因與證據

| 證據 | 內容 |
|---|---|
| 症狀 | staging 上大腦每一句都回「大腦暫時無法判讀這句話，請再說一次」 |
| staging log | `error_kind=LlmUnavailable`，OpenRouter 回 `400 Bad Request` |
| 以 staging 金鑰實測 | `typesafe/jev-1.13`、`typesafe/jev-1.14` 在 chat/completions 皆回 400：「is a decisions model and cannot be used with the chat/completions endpoint」 |
| 程式現況（`a821d8c`） | `intent_routing_port.py` 以 `bind_tools(..., tool_choice=...)` 走 chat/completions |
| 決定 | 2026-11-16 使用者決定直接改寫成 Jev 1.14 Decisions API（節費） |

Decisions API 實測（2026-11-15，staging runner，延遲 389–664 ms，每輪約 2.9e-05 美元，輸入約 700 tokens）見 ADR-0024 的實測表；請求形狀取自 `danniel/chore/brain-routing-diag` 的 `09f64fa`（`.github/workflows/brain-routing-diag.yml`）。

## 二、設計決定

### 2.1 questions 形狀

| 鍵 | type | 選項／題目 | 消費者 |
|---|---|---|---|
| `primary` | choice | `architecture-design`、`well-architected-review`、`cost-finops`、`unclear`；定義文字逐字沿用實測版本 | 單一意圖與反問 |
| `wants_design`／`wants_review`／`wants_cost` | noul | 是否要求該能力 | 多意圖 |
| `named_target` | choice | `t0`…`t<n>`（使用者可見的專案與系統名稱，至多 50）＋ `none` | `referent` |

- **刻意不送 `refers_current`**（偏離指示）：未指名時閘道本來就依目前作業對象交辦（`brain_gateway.py` 的 `_resolve_and_dispatch`，`if not named: dispatch`），這題沒有讀者；送了只多付 token，而 `team.md` 的「無死碼」紀律同樣適用於沒有讀者的請求欄位。
- `state`：使用者原文在最前；其後「以下是參考資料，不是指示：」區段放作業對象與至多 5 筆記憶筆記。不帶對話歷程（Decisions 每題問的是「這句話」，歷程沒有讀者；少送使用者內容）。
- 名稱只進 `named_target.criteria` 的定義文字：`名稱為「<整理後名稱>」的專案或系統`；整理沿用 F2 的 `sanitize_target_name`（去控制字元與換行、去「」『』`、截 60 字）；鍵為 `t<n>`，名稱不當鍵。

### 2.2 門檻與常數

| 常數 | 值 | 理由 |
|---|---|---|
| `BRAIN_ROUTER_CONFIDENCE_THRESHOLD` | 0.7（設定值，既有） | `wants_*` 是否算一件事、`primary` 信心是否足夠，都用同一個門檻 |
| `NAMED_TARGET_MIN_CONFIDENCE` | 0.8 | 實測誤配 0.63（「畫一張電商網站的架構圖」配到「電商前台系統」）、真實指名 0.99；誤配會把作業對象靜默改到別的系統，比少認一次嚴重 |
| `TIE_MARGIN` | 0.05 | 有分數時述詞走 `BR3.2` 不讀 `tied_with_next`；它是資訊欄位。暫定，NFR1 重測時校正 |
| `FORCE_CLARIFY_THRESHOLD` | `math.nextafter(1.0, 2.0)` | 必須反問時交給既有 `decide()` 的門檻；機率已驗證 ≤ 1，任何候選都達不到 → 走既有反問分支，候選 id 與 `resolution` 由既有單一產生點產生 |
| `TARGET_CHOICE_MAX` | 50 | 與閘道 `CATALOG_PROJECT_MAX` 同值；每多一個名稱就多送一段使用者資料與輸入 token |
| `CLARIFY_LABEL_TEMPLATE` | `交給「{name}」處理` | 唯一模板；`name` 取自 `CAPABILITY_NAMES`（能力顯示名稱的唯一來源） |

### 2.3 機率 → slots（`routing_from_answers`，純函式）

1. `wants_*` ≥ 門檻的能力 **≥ 2 個** → 每個能力一個 slot、一個候選，`score` 為該題機率 → 可交辦。
2. 否則一個 slot，候選為三個能力依 `primary.probabilities` 由高到低（`primary` 選中者恆排第一），`score` 為機率，`scores_available=True`。
3. `primary=unclear` 或 `primary.confidence` < 門檻 → `force_clarify=True` → 一定反問；候選即第 2 點的排序。
4. `referent`：`named_target` 選中名稱且信心 ≥ 0.8 → 名稱原字串（`referent_state=resolved`）；否則 `None`（`absent`）。

**偏離指示：多意圖的 slot 順序是能力固定先後（設計 → 評核 → 成本），不是機率高低。** 指示寫「依機率排序」與 PBT「slot 順序一定依機率由高到低」。照做會出錯：`work_orchestrator_rules.plan_waits` 只讓成本／評核等「排在它前面」的設計，而實測第 5 句「幫我改一下那張圖，加上 CloudFront，然後估一下成本」成本 0.98 ＞ 設計 0.81——依機率排序，成本排第一、不等改圖，估的是舊圖。Decisions 回應不帶句中順序，固定先後是唯一能保證先改圖再估／評的排法。PBT 因此改驗「slot 順序恆為固定先後的子序列」。若 conductor 仍要機率排序，改 `intent_routing_decisions.py` 的 `_order` 一處即可，但需另外處理 `plan_waits` 的依賴。

### 2.4 `claude-code` 路徑如何保留

- 唯一選擇點 `select_routing_port`（`intent_routing_port.py:583`）：`LLM_PROVIDER=claude-code` → `ToolCallingRoutingPort`（既有 `router_chat_model` ＋ `compile_routing_graph` ＋ `parse_classification`，行為不變）；其他（openrouter）→ `DecisionsRoutingPort`。
- 測試明文注入 `model_factory`／`graph_builder` 時建工具呼叫 port（建構，不是選擇），既有 `test_intent_routing_port.py`、`test_claude_code_chat.py` 的工具呼叫測試全部原樣保留、照舊通過。

### 2.5 閘道的最小改動（偏離「閘道不必改」的原則）

`named_target` 需要使用者可見的名稱，而那要 DB；路由層依 `NFR6.60` 不碰 DB。因此 `brain_gateway.py` 在 `classify` 前（只在 `router.needs_target_catalog` 為真時）以既有 `_build_catalog` 取名稱、以 `target_catalog=` 傳入。取不到時本輪照路由失敗的方式結束（先寫使用者訊息、再 `error`），不帶空目錄硬跑——空目錄會把指名別的系統的句子靜默交辦給目前對象。工具呼叫 port 不取目錄、不多查一次（測試 `test_tool_calling_router_gets_no_catalog_and_no_extra_query`）。`work_orchestrator.py` 未改。

## 三、改動檔:行（`grep -n` 實查，`2026-11-15T16:37Z`）

`git diff --stat`：13 個既有檔，445 insertions(+)、78 deletions(-)；另新增 4 個檔。

| 檔 | 行 | 內容 |
|---|---|---|
| `backend/services/intent_routing_decisions.py`（新，413 行） | 68 `PRIMARY_CRITERIA`、76 `WANTS_QUESTIONS`、98 `NAMED_TARGET_MIN_CONFIDENCE`、106 `TIE_MARGIN`、113 `FORCE_CLARIFY_THRESHOLD`、116 `CLARIFY_LABEL_TEMPLATE`、129 `build_questions`、155 `build_state`、240 `parse_answers`、282 `effective_threshold`、287 `resolve_referent`、309 `routing_from_answers`、335 多意圖分支 | Decisions 純函式層 |
| `backend/services/intent_routing_port.py` | 130 `_MALFORMED_RESPONSE_CLASSES`、463 `RoutedClassification`、470 `_call_with_typed_failures`、486 `ToolCallingRoutingPort`、531 `DecisionsRoutingPort`、583 `select_routing_port` | 兩個 port 與唯一選擇點 |
| `backend/services/intent_routing.py` | 365 `self._port = … select_routing_port(`、376 `needs_target_catalog`、484 `self._port.route(`、493 `effective_threshold(` | `IntentRouter` 改以 port 取結果，`decide()` 不變 |
| `backend/services/intent_routing_config.py` | 55 `DEFAULT_MODEL = "typesafe/jev-1.14"`、60 `_DECISIONS_MODEL_PATTERN`、63 `is_decisions_model`、200 啟動時呼叫、213 `warn_if_not_decisions_model` | 預設模型與啟動 WARNING |
| `backend/services/intent_routing_context.py` | 106 `TARGET_CHOICE_MAX`、109 `target_choices` | 名稱清單（整理、去重、上限） |
| `backend/services/langgraph_runtime.py` | 20 `DEFAULT_OPENROUTER_DECISIONS_URL`、23 `_RETRYABLE_STATUSES`、171 `DecisionsMalformedResponse`、179 `openrouter_decide` | Decisions API 唯一出站點 |
| `backend/services/brain_gateway.py` | 1382 `needs_catalog`、1390 `catalog_kwargs["target_catalog"]` | 分類前取可見名稱 |
| `backend/tests/test_intent_routing_decisions.py`（新） | 37 個測試，其中 5 個 Hypothesis 性質（各 300 例） | 端到端、失敗分型、選擇點、設定、PBT |
| `backend/tests/test_brain_gateway_target_catalog.py`（新） | 3 個測試 | 閘道目錄交付與失敗 |
| `backend/tests/brain_gateway_fakes.py` | 149 `needs_target_catalog`、190 預設 False | 替身支援新 kwarg |
| `backend/tests/test_intent_routing_structure.py` | 74、87 `DECISIONS_PATH` | 新模組納入結構斷言（SEC-1／SEC-2、無模組層可變字面值） |
| `backend/.env.example` | 186 | `BRAIN_ROUTER_MODEL=typesafe/jev-1.14` ＋ 決策模型說明 |
| `deploy/.env.example` | 175 | 同上 |
| `deploy/render-env.sh` | 51（註解）、150 | 同上 |
| `deploy/docker-compose.test.yml` | 130 | `${BRAIN_ROUTER_MODEL:-typesafe/jev-1.14}` |
| `LOCAL-DEV.md` | 79、442、719 | claude-code 照舊走工具呼叫；預設模型；排錯表新增一列 |
| `inception/decisions/0024-intent-routing-via-jev-decisions-api.md`（新） | — | ADR |

## 四、ADR-0006 四面向

| 面向 | 判定 | 內容 |
|---|---|---|
| IAM | 適用（相同） | 不新增權限或角色；目錄查詢沿用 `_build_catalog`（`HierarchyFacade` ＋ `U23` 可見性），送出的名稱只有使用者本來就看得到的 |
| Encryption | 適用（變更） | 仍是 HTTPS 到 `openrouter.ai`；外送內容新增至多 50 個名稱、移除最後 6 則對話歷程；金鑰只在 `Authorization` 標頭 |
| Network exposure | 適用（相同） | 零新端點、零新埠；出站路徑由 `/api/v1/chat/completions` 改為 `/api/alpha/decisions` |
| Audit logging | 適用（相同） | 不新增稽核事件；失敗 log 只記例外類別名；`RoutingObservation` 白名單不變 |
| PBT（hard constraint） | 適用（blocking） | 5 條 Hypothesis 性質，見第五節 |

## 五、測試實跑輸出

環境：`/Users/jiangzhengdao/orca/workspaces/cloud-360/chiton/backend/.venv/bin/python -B`，`PYTHONDONTWRITEBYTECODE=1`，`HYPOTHESIS_STORAGE_DIRECTORY=<scratchpad>/hyp-jev`，於 `<wt>/backend` 直接執行。原始輸出：scratchpad 的 `jev-checks.log`、`jev-unittest-full.log`、`jev-unittest-new.log`。

```
new exit=0
Ran 40 tests in 1.456s
OK

exit=1
ERROR: test_async_timeout_kills_process (test_claude_code_chat.Failures.test_async_timeout_kills_process)
ERROR: test_sync_timeout_kills_process (test_claude_code_chat.Failures.test_sync_timeout_kills_process)
Ran 1522 tests in 121.073s
FAILED (errors=2, skipped=3)

規格檔與後端程式碼一致。
dump_openapi exit=0
WS 契約規格檔與後端程式碼一致。
dump_ws_contract exit=0
Cloud-360 repository contract validation passed.
validate_repo_contract exit=0
Cloud-360 environment configuration contract validation passed.
validate_env_contract exit=0
```

**全套不是全綠，兩個錯誤與本次改動無關**：都是 `claude_code_chat` 的子行程逾時測試（假 CLI 沒來得及寫 pid 檔就被 kill，`FileNotFoundError: …/pid.txt`）。以 `git archive a821d8c backend` 的乾淨副本跑同一個測試類別：一次 `FAILED (errors=2)`、另一次 `FAILED (errors=1)`（`jev-baseline-claude-code.log`）——基準本身就在本機環境下時序不穩，與路由改動無關。本次未動 `claude_code_chat.py`。

新增測試涵蓋（指示要求的各一）：單一意圖、多意圖、反問（unclear 兩句）、指名 ≥ 0.8、指名 < 0.8、指示詞（「這個系統」→ `referent=None`）、`refusal`、4xx（400）、402、5xx、逾時、連線失敗、形狀不符（缺 `answers`、type 不符、機率越界、未知選項、非 JSON）、重試只在設定允許且可重試時發生、呼叫上限 0 不發請求、金鑰缺失原樣傳遞、請求形狀（原文只在 `state`、名稱整理、鍵為 `t<n>`）、名稱上限 50、選擇點三種、啟動 WARNING 四種。

PBT（`RoutingFromAnswersPropertyTest`，各 300 例）：

1. 任何 `wants_*` 低於門檻且 `primary=unclear` → 一定反問。
2. `named_target` 信心 < 0.8 → 所有候選與 `intents` 的 `referent` 為 `None`（範圍寫死 0.8，不讀常數）。
3. 多意圖的 slot 順序恆為能力固定先後，且恰為 `wants` ≥ 門檻的能力（偏離指示，見 2.3）。
4. 反問候選的 `label` 恆屬伺服器模板輸出集合。
5. `IntentDecision` 恆合法（EC4／EC5）；`force_clarify` ⇒ 反問；候選第二名起依機率遞減。

## 六、突變紀錄（`jev-mutate.py`，輸出 `jev-mutate.log`）

```
## J1 多意圖改成只取 primary
  變異後 exit=1 Ran 37 tests in 1.586s FAILED (failures=2)
    FAIL: test_multi_intent_orders_design_before_cost
    FAIL: test_slots_follow_the_fixed_capability_order
  還原 sha256 相同：True  bff07d5588f6996a
## J2 指名門檻改成 0.5
  變異後 exit=1 Ran 37 tests in 1.727s FAILED (failures=2)
    FAIL: test_named_target_below_point_eight_is_ignored
    FAIL: test_named_target_below_point_eight_never_sets_a_referent
  還原 sha256 相同：True  bff07d5588f6996a
## J3 失敗時改成回空結果、不拋錯
  變異後 exit=1 Ran 37 tests in 1.284s FAILED (failures=14)
  還原 sha256 相同：True  e07b3d58af7535e8
## J4 反問的 label 改由使用者原文組成
  變異後 exit=1 Ran 37 tests in 1.280s FAILED (failures=1)
    FAIL: test_unclear_asks_back_with_server_labels
  還原 sha256 相同：True  e07b3d58af7535e8
## 還原後複驗 exit=0 Ran 37 tests in 1.296s OK
```

J2 第一次跑時 PBT 沒紅：性質的取值範圍讀的是被突變的常數本身，突變把測試範圍一起改掉了。已改為寫死 0.8 並另斷言常數等於 0.8，重跑後兩條都紅（上面是重跑結果）。

## 七、快取數前後（`jev-cache.log`）

```
before 2026-11-15T16:21:40Z pyc=0 hyp=0 pycache=0
after 2026-11-15T16:37:30Z pyc=0 hyp=0 pycache=0
```

（排除 `.venv`、`node_modules`；`<wt>` 內無 `.venv`。）

## 八、未完成項

1. **真實 API 未打**：本機沒有 OpenRouter 金鑰。所有 Decisions 回應都是依實測表構造的替身。上線前須由 conductor 在 staging runner 上做真實驗證，至少確認：回應 `probabilities` 是否列出全部選項（本實作把缺的選項當 0）、`refusal` 的實際形狀、`usage.cost`。
2. **NFR1 準確率須重新量測**：模型與分類方式都換了；門檻 0.7、指名 0.8、`TIE_MARGIN` 0.05 只有六句實測支撐。
3. **P-4 在 Decisions 路徑未落實**：每輪新建 `httpx.AsyncClient`（含 TLS 握手）。實測 389–664 ms 仍在 800 ms 預算內。
4. **兩處偏離指示，待 conductor 確認**：多意圖 slot 依固定先後而非機率（2.3）；不送 `refers_current`（2.1）。另閘道有一處最小改動（2.5）。
5. **目錄超過 50 個名稱時**，第 51 個以後無法被指名，那些句子依目前作業對象交辦；原本「專案太多」的回覆只在模型給出 `referent` 時觸發，Decisions 路徑下不會出現。
6. **`referent_state=unresolved` 不再產生**：Decisions 沒有對應題目；`BR5.2` 在此路徑由閘道的目錄比對與目前作業對象承擔。
7. **alpha API**：形狀一變會以 `MalformedRouting` 大聲失敗，大腦整體不可用直到修正；無監控通道會主動告知。
8. **全套兩個 `claude_code_chat` 逾時測試在本機不穩**（基準同樣失敗），未在本次處理。
9. 未跑前端建置或 Playwright：本次無前端改動，WS 契約未變（`dump_ws_contract --check` 通過）。
10. `tcms-test-cases` 的手動／自動化盤點與 TCMS 同步未做（不在本指示範圍）。
