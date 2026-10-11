# Code Summary — `U11 intent-router`

> **本檔的每一個數字都由腳本從檔案與 `unittest` 輸出實算後代入**，不手寫。
> 計數在最後一次內容改動**之後**才跑（`project.md` 的 `user-stories:78fff...`：
> 計數腳本是收尾動作，不是中途動作）。

## 一、交付了什麼

把一句使用者自然語言變成 `IntentDecision`：過 `prompt_guard` → 讀該段作業對象／
歷程與語意／程序記憶 → 組最少上下文的 prompt → 對 `typesafe/jev-1.13` 發出
**恰一次** tool call → 在我方還原成**槽位 × 候選**兩層並跑五道驗證 → 對每個槽位
求 `can_single_out`、以 AND 聚合成整句判定。

**本單元不建立任何 HTTP 端點、不寫任何持久層、不建立工作項。**

### 八個新模組（8 個，共 2304 行）

| 模組 | 行數 |
|---|---|
| `backend/services/intent_routing.py` | 485 |
| `backend/services/intent_routing_config.py` | 212 |
| `backend/services/intent_routing_context.py` | 194 |
| `backend/services/intent_routing_errors.py` | 111 |
| `backend/services/intent_routing_parser.py` | 270 |
| `backend/services/intent_routing_port.py` | 426 |
| `backend/services/intent_routing_predicate.py` | 245 |
| `backend/services/intent_routing_types.py` | 275 |

**檔名刻意避開 `_router.py` 字尾**：`team.md` 的既成慣例裡該字尾專指「建立
`APIRouter` 並被 `main.py` include」的 HTTP 路由模組，而本單元的 `SEC-2` 明寫它
**沒有** `APIRouter`。類別名 `IntentRouter` 維持不變（`K-10` 契約）。

### 三個既有檔的改動

| 檔 | 改了什麼 |
|---|---|
| `backend/services/langgraph_runtime.py` | `openrouter_chat_model` 的 `temperature` 由 `float = 0.0` 改為 `float \| None = 0.0`，`None` 時**不放進 kwargs**（`TS-3a`／`D-3`） |
| `backend/main.py` | startup hook 加一行 `configure_intent_routing_env()`，與既有的 `configure_embedding_env()`／`configure_session_env()` 並列 |
| `backend/.env.example`／`deploy/.env.example`／`deploy/render-env.sh`／`deploy/docker-compose.deploy.yml`／`deploy/docker-compose.test.yml`／`LOCAL-DEV.md` | 五個 `BRAIN_ROUTER_*` 變數 |

## 二、測試結果

> **本節的每一個數字由腳本在最後一次內容改動之後重跑產生**（審查 `R-06`）：逐檔的 `Ran N` 來自五次獨立的 `unittest` 執行，不是手寫的加總；追溯的四個計數由 `traceability.json` 實算。

### 本單元（scoped 指令，77 個測試全綠）

```
cd backend
python3 -m unittest -v \
  tests.test_intent_routing_predicate \
  tests.test_intent_routing_parser \
  tests.test_intent_routing_context \
  tests.test_intent_routing_port \
  tests.test_intent_routing_structure
```

| 測試檔 | 測試數 | 行數 | 結果 |
|---|---|---|---|
| `backend/tests/test_intent_routing_context.py` | **6** | 156 | OK |
| `backend/tests/test_intent_routing_parser.py` | **18** | 351 | OK |
| `backend/tests/test_intent_routing_port.py` | **18** | 487 | OK |
| `backend/tests/test_intent_routing_predicate.py` | **15** | 647 | OK |
| `backend/tests/test_intent_routing_structure.py` | **20** | 609 | OK |
| **scoped 指令一次跑完** | **77** | **2250** | **OK** |

**`@given` 裝飾器數：7**（`P1`–`P7`），全部落在
`intent_routing_predicate`——`ADR-0006` 對 **agent routing** 的 PBT hard
constraint 落點。

> **這個數字第一次算出來是 8，而它是錯的。** 原腳本用 `re.findall(r"@given")`
> 掃全文，把 docstring 裡的「七條全部 `@given`」那一句也算進去。只數**裝飾器行**
> （`^\s*@given\(`）才是 7。如實記在這裡，因為 `project.md` 記過同形的失誤三次。

### 既有測試套件（`python3 -m unittest discover -s tests`）

**733 個測試，全綠**（`discover` 的總數**含**本單元的 77 個）——本單元**沒有打破任何既有測試**。
其中與 `temperature` 改動直接相關的六個檔（`test_langgraph_runtime`／
`test_a3_langgraph_migration`／`test_langgraph_migration`／`test_cost_advice_agent`／
`test_review_agent`／`test_design_agent`，共 **34** 個）另單獨跑過一次確認（`D-3` 的驗收條件）。

### 兩支 validator

| 指令 | 結果 |
|---|---|
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| `python3 backend/scripts/dump_openapi.py --check` | `規格檔與後端程式碼一致。`（`SEC-2` 的後果：沒有端點就沒有 schema 可漂移） |

### 追溯覆蓋（`traceability.json`，實算）

129 列、129 個上游識別碼：**OK 104**、Deferred 14、N/A 10、**GAP 1**（唯一的 `GAP` 是 `AC1.1.5`，見 §五 #8）。`Partial` 這個狀態已不存在於檔內——sensor 的合法狀態不含它，原本四列已改為 `Deferred` 並在 note 逐字保留未覆蓋的部分。

## 三、關鍵實作決定

### 1. `confidence` 的 `pending` 型別：`derive_contract_confidence()`

`entities.md` 把 `IntentDecision.confidence` 標為 `pending`、改寫權屬
`nfr-requirements`，並要求實作時「以契約型別 `float` 為準並讓缺值成為一個
**顯式的失敗點**，而不是悄悄放寬成 nullable」。

**處置**：型別維持 `float`（非 nullable），缺值集中在一個具名、可觀測、單一
落點的推導裡。推導方式讓 `K-10` 自己宣告的
`below_threshold: "bool —— confidence < threshold"` 在**兩個分支都逐字成立**：

- **有分數**：取各槽位最高分的**最小值**。`BR4.2` 的 AND 聚合
  ⟺ `all(top_i >= t)` ⟺ `min(top_i) >= t`，兩個方向都一致。
- **無分數**：回**能讓同一個關係維持為真的最小資訊量**——可交辦時回門檻本身
  （`threshold < threshold` 為偽），不可交辦時回 `0.0`。

`0.0` 這個取值要求門檻嚴格大於 0，所以 `resolve_confidence_threshold` 把值域
收為 `0 < t <= 1`（下界開區間另有獨立理由：門檻 0 會讓反問路徑永不觸發）。

**這個值不是信心度**，同一輪的 `RoutingObservation.scores_available` 為假即為
標記——**而那個標記只存在於日誌裡**：`RoutingObservation` 是日誌白名單型別，
不是 `IntentDecision` 的欄位，所以 `U13` 與 `build-and-test` 的 `NFR1` 量測作業
**都取不到它**（審查 `R-04`）。亦即合成值 `0.7` 與一個真的落在邊界的量測值在
`IntentDecision` 上**完全無法區分**，而 `NFR1` 的準確率校正會在一個有時是常數的
欄位上計算。本單元**不自行擴充 `K-10`**（無授權），該缺口列在 §五。
可減輕的事實（審查已查證）：`refined-mockups/interaction-spec.md:228` 逐字
「`clarify` 訊息刻意不帶信心數值上畫面」，故合成值不直達使用者。
`OQ-10` 定案後本函式與 `K-10` 的欄位語意須一併重檢。

### 1b. `referent_state == "unresolved"` 的讀取端（審查 `R-01`，Critical）

`referent_state` 原本有寫入端（parser）、有 schema（port）、有 prompt 指示
（context），**卻沒有任何讀取端**。可構造的執行期路徑：模型回單一候選、
`tied_with_next=false`、無分數、`referent_state="unresolved"` ⇒ `can_single_out`
為真 ⇒ 交辦一個 `referent=None` 的 `Intent`。而 `AC6.1.2`（Must 故事的 AC）的
Then 逐字「系統走 `US1.2` 的反問路徑，**不擅自挑一個**」。`Intent` 的欄位集合由
`K-10` 固定為 `{capability, referent}`，該狀態**也不跨契約邊界**，所以 `U13`
同樣補不了這個判斷。

**處置**：`can_single_out` 新增**第一道條件**——`has_unresolved_referent(ranking)`
為真即回 `False`，不論分數多高。兩個判斷要點：

- **只有 `unresolved` 強制反問。** `absent`（這句話本來就沒有指涉詞，例如
  「幫我畫一張架構圖」）是**完全正常**的情形。把它一併擋下會讓每一句不帶指涉詞的
  輸入都被反問，`FR1.1` 直接不可用——那是一個比原缺口更大的回歸，所以它有一條
  專屬的測試（`test_absent_is_normal_and_must_not_be_dragged_in`）。
- **看全部候選而不只看 `rank == 1`。** `BR5.2` 的 `logic` 逐字「IF **指涉詞**不可
  唯一解析 THEN `can_single_out` 為假」——不可唯一解析是**這個槽位**的性質，不是
  某一個讀法的性質；欄位之所以掛在候選上，只因為 `[D1]`=A 的扁平 schema 把一切都
  掛在候選上。兩種錯的代價不對稱：多問一次是一次互動，少問一次是 `FR1.3` 逐字要防
  的那件事。`test_an_unresolved_candidate_outside_rank_one_also_asks_back` 守這一半。

由構造成立的附帶後果：**可交辦槽位其 rank 1 的 `referent` 必然不是「解析失敗」**
——要嘛是一個解析成功的字串、要嘛是 `absent` 的 `None`。

### 2. `tied_with_next`：`BR3.3` 的唯一輸入，而上游沒有給它一個欄位

`BR3.3` 逐字「rank 1 與 rank 2 之間存在**分類器宣告的**嚴格優先」，而 `[D1]`=A
的選項文字列的欄位是 `slot`／`capability`／`referent`／`score`／`label`——
**沒有一個能承載「有沒有嚴格優先」**。

不能用 `rank` 代替：`rank` 依 `V-4` 永遠是 1、2、3…，用它判定等於永遠「嚴格」，
於是無分數時述詞退化成永遠可單選，`FR1.3` **靜默永不觸發**——`FR1.6` 逐字警告
的那個後果。

**處置**：schema 新增一個 **required** 的 `tied_with_next: boolean`，
`CandidateIntent` 上**刻意無預設值**，parser 缺它即 `MalformedRouting`。
「預設不並列」與「預設並列」兩個預設都是壞的（一個永不反問、一個永遠反問），
所以不給預設。形狀的新增落在 `[D1]`=A 已經開的那一扇門內（`slot_labels`
也是 `nfr-design` 審查 `R-06` 以同一方式加進扁平 schema 的）。

### 3. `OPEN-IR11-1`（兩種 `null`）：`referent_state` 封閉列舉

`EC3` 只鎖定「必須可區分」、把形狀留給本站。選的是一個**顯式的狀態欄位**
（`absent`／`unresolved`／`resolved`）而不是 sentinel 字串——sentinel 會被當成
真的 `referent` 值往下游傳。parser 另檢查狀態與值**互相一致**。

### 4. `prompt_guard` 命中怎麼離開一個 `-> IntentDecision` 的簽章

`K-10` 把 `returns` 固定為 `IntentDecision`，而固定拒絕訊息**不是**一個
`IntentDecision`：`EC4`／`EC5` 要求 `intents` 與 `candidates` 恰有一邊非空，
兩邊皆空會違反 `EC5`。設計層（`W2`）只說「回固定拒絕訊息」，沒有指定回傳形狀。

**處置**：`PlatformSelfModificationRefused`，**刻意不繼承** `IntentRoutingError`
失敗基底，`message` 預填 `prompt_guard.REFUSAL_MESSAGE`（不另抄一份字串），
docstring 明寫呼叫端義務（`BR1.3`：以 `done` 而非 `error` 結束）。

### 5. `session` 不經 `SessionStore` 再讀一次

`K-10` 把 `classify` 的第二個參數固定為 `session: BrainSession`——session 已由
`U13` 載入並傳進來。故本單元對 `U10` 的「讀取」是讀傳進來的物件，
**零 Redis 往返、且連 `session_store` 都不 import**。

這是 `BR7.4` 的最強形式（`SessionStore.load` 會順帶續期 TTL，再呼叫一次等於多
一個副作用且多餘），也讓 `logical-components.md` §三 的「`U10` 不可用……本單元
不處理，它向上傳遞」由構造成立。**計畫 Step 4 的字面是「經 `SessionStore` 讀」
——這是一處偏離，見下。**

### 6. `P-4`（連線重用）放在**實例**上而不是模組層

`performance-design.md` §二 的 P-4 要求 HTTP client「建立一次並重用」，理由是每
輪一次 TLS 握手會吃掉 800 ms 預算的一部分，並把它寫成「模組層的 factory」。
本站改放在 `IntentRouter` **實例**上（一個行程一個 router）：效果相同，但
**完全不產生模組層狀態**——`NFR3.67` 的結構斷言因此不需要為它開白名單例外。

為此另有兩處連帶改動：`_CAPABILITY_HINTS` 由模組層 `dict` 改為 tuple of pairs、
tool schema 由模組層常數改為 `routing_tool_spec()` 函式。結果是
`NoModuleLevelMutableStateTest` 可以斷言**零例外（除 `__all__`）**，比計畫預期
的「白名單排除 client factory」更緊。

### 7. 未識別的例外**原樣傳遞**，不被標成供應商故障

`classify_transport_failure()` 只對應得出的失敗（402 → budget；逾時／HTTP 4xx
5xx／連線層類別名 → unavailable），其餘**原樣回傳**。一個
`except Exception: raise LlmUnavailable` 的 catch-all 會把本單元自己的
`TypeError` 計進「供應商掛了」那條曲線，而分型（`NFR3.74`）的全部價值就是分出
「是供應商的事」與「是我們的事」。

**代價如實記載**：`classify` 可能拋出 `K-10` 的 `raises` 清單之外的例外。
`test_our_own_bug_is_not_relabelled_as_a_provider_outage` 是它的正向斷言。
同理 `RuntimeAuthError`（金鑰缺失）**刻意不被轉型**。

### 8. `tool schema` 的實際 JSON

OpenAI function 形式，`bind_tools([spec], tool_choice="emit_routing_decision")`。
`parameters` 為 `{candidates: array<object>, slot_labels: array<string>}`，
`candidates.items.required` 為
`[slot, rank, capability, label, tied_with_next, referent_state]`，
`capability.enum` 為封閉列舉、`slot.maximum` 為 `MAX_SLOTS - 1`、
`candidates.maxItems` 為 `MAX_SLOTS * MAX_CANDIDATES_PER_SLOT`。
**schema 的上界是提示，我方的 `V-3`／`V-4` 才是閘門**——模型不保證遵守 schema，
所以兩邊都要有（`test_the_tool_schema_carries_the_closed_enum_and_the_upper_bounds`）。

## 四、與計畫的偏離（逐項）

| # | 偏離 | 理由 |
|---|---|---|
| 1 | **Step 4 寫「經 `SessionStore` 讀該段作業對象與歷程」，實作改為讀傳進來的 `BrainSession`** | `K-10` 的簽章把 `session` 固定為參數，再 `load` 一次是多餘且會續期 TTL（`BR7.4` 禁 `touch`）。連帶 Step 5 的「`U10` 失敗」測試改為**斷言本層不吞掉 session 讀取失敗**（`test_session_read_failure_propagates_untouched`）——那正是 `logical-components.md` §三 要的行為 |
| 2 | **Step 11 列三處同步，實作同步了四處** | 另加 `deploy/docker-compose.test.yml`（以 `:-` 預設）。理由：本站依 `reliability-design.md` §四 把門檻做成 startup 失敗，而 `ui-regression` 的短生命週期 stack 沒有 `deploy/.env` 也沒有 renderer——不加這一處，**每個 PR 的 `ui-regression` 都會紅**。既有前例逐字同形（`BRAIN_SESSION_HISTORY_MAX` 在該檔就是 `${...:-200}`） |
| 3 | **Step 11 未列 `backend/main.py`，實作改了它** | `NFR8.60`／`BR3.4`／`reliability-design.md` §四（「啟動期檢查是另一回事，而它有」）要求門檻缺值即啟動失敗。不掛進 startup hook，那條需求沒有載體 |
| 4 | **`intent_routing_predicate` 的測試數 15、`structure` 20，高於策略指引的每元件 5–8** | `unit-test-instructions.md` 自己就指派了 7 條 property ＋ 2 條 example-based（predicate）與 8 條禁令 ＋ 3 條 L0 斷言（structure），本站另補了下方第 8 列那兩條。向上偏離，**不降低任何目標** |
| 5 | **predicate 多了 `StrategyReachesEveryBranchTest`** | 不在指引裡。加它的理由：七條 property 在前提為假時**恆真**，所以「全綠」不保證那兩個硬性要求（`scoresAvailable` 顯式驅動、`len(slots)` 涵蓋 1 與 ≥2）真的被滿足。它以 `hypothesis.find` 對八個組合各找一個實例——把宣稱變成斷言 |
| 6 | **`P3` 限定在無分數分支** | `functional-spec.md` §五 的 `P3` 逐字是「候選數為 1 ⇒ 為真」，而有分數時單一低分候選為**假**——那是 `BR3.2` 的正確行為。不限定就會是一條必然失敗、而且失敗得有道理的 property。`P3` 的來源是 `BR3.3` 的 `(slot 候選數 == 1)` 這個 disjunct |
| 7 | **`ClassificationResult` 多一個 `slot_labels` 欄位、`CandidateIntent` 多 `tied_with_next` 與 `referent_state`** | 三者分別來自 `nfr-design` 審查 `R-06`（`slot_labels`）、`BR3.3` 的「分類器宣告」（`tied_with_next`）、`OPEN-IR11-1`（`referent_state`）。`entities.md` 的 YAML 未列前兩者，但 `K-10` 的**線上形狀**一字未動 |
| 8 | **`structure` 檔多了 `RouterModelIsItsOwnVariableTest` 兩條（`NFR10.60`）** | 不在指引的八條禁令裡。加它的理由：`TS-2` 的驗證方式逐字是「`grep` 斷言本單元不讀 `LLM_MODEL`」，而**裸 `grep` 在本單元會命中 1 處**（`intent_routing_config.py:48` 的註解正好寫著「不得沿用 `LLM_MODEL`」）。改以 AST 斷言它不作為程式字串出現，並反向斷言 `BRAIN_ROUTER_MODEL` 真的被讀——否則「寫死模型名」也會通過 |
| 9 | **計畫 Step 6 逐字「簽章只收（作業對象名稱、最後 K 則歷程、**能力清單**、使用者文字）」，而 `build_routing_prompt` 不收能力清單** | 它是模組內的 `_CAPABILITY_HINTS`（已依偏離 #6 改為 tuple of pairs）＋ `ROUTABLE_CAPABILITIES`。理由是封閉列舉需要**單一真實來源**：讓呼叫端傳進來，就等於允許呼叫端送一份與 `V-2` 的驗收集合不同的清單，而那個不一致不會有任何測試擋得住。方向是向上偏離、不降低任何目標，但偏離表的判準是「計畫寫了什麼、實作做了什麼」（審查 `R-09`） |
| 10 | **計畫 Step 7 寫 `test_intent_routing_context.py`「五個」，實際 6 個**（本輪後為 6） | 第 6 條是 `test_an_unset_work_target_is_stated_rather_than_omitted`——「脈絡列顯示尚未選定」是 `AC1.1.5` 的**前提**而不是異常，把那一行整段省略會讓模型無從分辨「沒有作業對象」與「我忘了給」。向上偏離（審查 `R-09`） |

## 五、發現但未處置的缺口

| # | 缺口 | 處置 |
|---|---|---|
| 1 | **`nfr-design/scalability-design.md` §四 仍寫「輸出超過 `maxItems` 8 或槽位超過 4 → 走 `BR2.4` 失敗路徑」** | 那是 `performance-design.md` 修訂 1（審查 `R-04`）已更正掉的誤引：`BR2.4` 逐字只講空清單，而 `reliability-design.md` 的 `V-3` 正確分類為 `MalformedRouting`。**三份已核可產出有兩份對、一份錯**，而已核可的計畫逐字站在對的那一邊（「超界即 `MalformedRouting`，不截斷（審查 `R-04`：不是 `BR2.4`）」），故實作照計畫。**本站不回改上游**，如實記在這裡 |
| 2 | **`work_target_hint` 是三層識別的文字呈現，不是人話名稱** | `performance-design.md` 的 P-1 寫「當前作業對象（三層識別的**人話名稱**）」，而人話名稱需要 `K-07` 的 `HierarchyFacade`，**DAG 裡沒有 `U11 → U7` 的邊**（`unit-of-work.md:160` 只有 `U8`、`U10`）。這與 `OPEN-IR11-4` 同根。本站**不新增 DAG 邊**（那要送 `delivery-planning`），改以 `專案 #3／架構圖 #12` 呈現。對分類品質的影響未量測 |
| 3 | **`BR5.2` 的執行面已落地，剩下的是「模型願不願意說」** | **本輪已補上讀取端**（審查 `R-01`）：`can_single_out` 的第一道條件讓 `referent_state == "unresolved"` 強制該槽位走反問，故「填 `unresolved` ⇒ 反問」現在是程式事實而不是一句描述——上一版這裡寫「靠的是模型把它們列成並列候選**或填 `unresolved`**」，而後半句當時在程式裡不成立（審查逐字點名這一句）。**殘留的是另一半**：我方無法強制模型在它該填 `unresolved` 的時候真的填它，也無法強制它把多個可能對象列成並列候選。`referent` 只能照模型宣告的狀態填、不得由我方推斷（parser 的一致性檢查），但「模型自己就誤以為解析成功了」這一種沒有任何機制擋得住，而 `OQ-10` 未定案前也沒有分數可以當第二道判準 |
| 4 | **`CallBudget` 用 `LlmBudgetExceeded` 承載「本地每輪上限」** | `reliability-design.md` §一 把該型別定義為「**供應商**回報用量上限」。本地上限被打到代表我方有 bug（圖被呼叫了第二次），兩者混在同一個 `error_kind` 會讓 `NFR3.74` 的那條曲線不純。訊息可區分（本地的含 `BRAIN_ROUTER_MAX_CALLS_PER_TURN`），但**型別不行** |
| 5 | **`NFR1.60` 的「與準確率同時呈現」無法由本單元滿足** | 準確率的標註集與量測 job 屬 `build-and-test`；本 intent **無任何 dashboard 或告警通道**（`OPEN-N10-4`）。本站只確保訊號存在——**不把「有指標」寫成「有監控」** |
| 6 | **`TS-6`：`OPENROUTER_API_KEY` 仍未配置** | `[ -f backend/.env ]` 為否。本單元的 77 個測試**全部不需要它**，故它不阻擋本站；它阻擋的是 `build-and-test` 的 `NFR1`／`NFR10`／`OQ-10`。**只有使用者能滿足它** |
| 7 | **Jev 對本 schema 的實際行為從未被驗證** | 無金鑰，無法先驗（`[D1]` 的 `V5` 已登記）。`TS-3b` 的四種畸形回應都以替身覆蓋，但「它到底會不會照這個 schema 吐」要到第一次真的打 API 才知道 |
| 8 | **`AC1.1.5` 是本單元追溯表唯一刻意保留的 `GAP`** | Then 有兩個子句：「工作項針對它建立」由本單元供 `referent` ＋ `U12` 承載；**「脈絡列更新為該系統」沒有任何已指派的寫入端**，且 `Intent.referent` 是不透明字串、對不上 `set_work_target` 要的三層識別。判定沿用 `functional-spec.md §六 OPEN-IR11-4` 的同一標準（逐字「記成 `OK` 會讓一條 **Must** 故事的 AC 在追溯表上看起來已覆蓋」）。**承接：`U12 work-orchestrator` 的 `code-generation`（3.5，`ALWAYS`）**，與 `U10` 的 `OPEN-S10-1` 同一落點（兩者是同一個缺口的兩面）。本列是審查 `R-06` 補的——它原本只存在於 `traceability.json`，而**關卡讀的是摘要** |
| 9 | **`P-4` 的生命週期義務落在 `U13` 身上，而 `K-10` 一字未提** | `performance-design.md:35` 逐字要求**模組層** factory，本單元改成 `IntentRouter` **實例層**快取（理由見 §三.6）。後果：`P-4` 只在「**一個行程一個 `IntentRouter`**」時成立。**若 `U13` 每個請求建一個 router，每輪多付一次 TLS 握手**，而 `performance-design.md:41` 逐字警告那會「直接吃掉 800 ms 預算的一部分」。`K-10`（`contract-summary.md:745-800`）對 `IntentRouter` 的生命週期一字未提，而 `U13` 尚未實作。**指名承接：`U13 brain-gateway` 的 `code-generation`**——建立 router 的那一處必須是 app 層的單一實例（形狀比照 `main.py` 建立其他長生命週期物件的方式），不得在 request handler 內 `IntentRouter(...)`。本單元守得到的那一半已有會失敗的斷言（`test_the_client_and_graph_are_built_once_not_once_per_turn` 計數 factory 與 builder 各須為 1）；`U13` 那一半本單元守不到（審查 `R-03`）|
| 10 | **無分數時合成的 `confidence` 在線上形狀上與量測值無法區分** | 算式與 `K-10` 的 `below_threshold ⟺ confidence < threshold` 在兩分支都逐字成立（審查已逐分支代入驗算，**不改算式**）。不成立的是**可分辨性**：唯一的旗標 `scores_available` 在 `RoutingObservation`（日誌白名單型別）裡，不是 `IntentDecision` 的欄位，`U13` 與 `build-and-test` 的 `NFR1` 量測作業都讀不到——於是 `NFR1` 的準確率校正會在一個**有時是常數**的欄位上計算。本單元**不自行擴充 `K-10`**（無授權）。**指名承接：`nfr-requirements`／`build-and-test` 在定案 `OQ-10` 時一併處理「`scores_available` 是否要上線上形狀」**。可減輕的事實：`interaction-spec.md:228` 逐字「`clarify` 訊息刻意不帶信心數值上畫面」，故合成值不直達使用者（審查 `R-04`）|
| 11 | **`max_retries` 接上之後，「每輪最多 1 次呼叫」與「重試可設定」變成兩個互不知情的旋鈕**（本輪新發現，`R-02` 的副作用） | `CallBudget` 數的是**我方發出的圖呼叫**，而 `max_retries` 是 `ChatOpenAI` **內部**的重試——兩者不在同一層。於是 `BRAIN_ROUTER_MAX_RETRIES=3` 會讓一輪實際發出最多 4 次 HTTP 請求，而 `CallBudget` 仍然只看到 1 次、`test_the_model_is_called_exactly_once` 這類替身測試也仍然綠。**出貨行為未變**（預設 0，故 `NFR3.62` 目前成立），這是一個**由設定可達**的張力：`NFR3.62`（每輪最多 1 次模型呼叫）與 `BR6.3`（重試必須可設定）在 `max_retries` 被寫死為 0 的時候不會相遇，接上之後才會。上游沒有任何一處寫過「重試算不算一次呼叫」。**本單元不自行裁決**（那會是替 `NFR3.62` 的語意做一個沒有授權的決定）：指名 `nfr-requirements`／`build-and-test` 在處理 `N-18`（每輪呼叫次數／重試／用量上限的**數值**）時一併定案，並考慮是否該讓 `max_retries > 0` 在啟動期就被拒絕。**可減輕**：`langgraph_runtime` 的預設與 `TS-4` 的預設都是 0，且 `backend/.env.example`／`deploy/.env.example` 寫的都是 0 |

## 六、本單元**刻意沒做**的事（與計畫 §四 一致）

不建 HTTP 端點（`SEC-2`）、不寫 `SessionContext`（`BR7.4`）、不建工作項與狀態機
（`BR7.3`）、不改 `schema_rbac.sql`／`DEPLOY.md`（**無 DDL、無 seed 語意變更，
blocking 規則不觸發**）、不建 circuit breaker、不設 fallback 模型、不引入 tracing
套件、不建 dashboard、不新增任何套件（`TS-5`：`backend/requirements.txt` 的 git diff **非空但完整屬於 `U10`**——新增 `redis` 的是 `session-store`，本單元一行都沒改它）、不新增任何 CI job（`[I1]` 的量測 job 屬 `build-and-test`）。

## 七、審查處置（`reviews/review-01.md`，`NOT-READY`，10 項）

審查為 **advisory、單輪、兩種 verdict 皆終局**，故無第二輪——本節是這一輪的
逐項處置。**`code-generation-plan.md` 與 `unit-test-instructions.md` 一個位元組
都沒有改**（含 task marker）：修正全部落在程式碼、測試與本檔／`traceability.json`。

| ID | 嚴重度 | 處置 |
|---|---|---|
| `R-01` | **Critical** | **接受，三項全做。** ① `can_single_out` 新增第一道條件 `has_unresolved_referent`（見 §三.1b）；② `AC6.1.2`／`EC3`／`BR5.4` 三列**維持 `OK`**，但 note 改為指向真正的讀取端與新測試——不再以「觸發條件可構造」當理由（可構造的只有 Given）。維持 `OK` 而非改 `GAP` 的依據是：`AC6.1.2` 的 Then 現在**有機制**，這與 `AC1.1.5`（Then 的一個子句**沒有任何已指派的寫入端**）性質不同，故兩者的判定標準並未不一致；③ §五 #3 的「或填 `unresolved`」已改寫（見該列） |
| `R-02` | Major | **接受，採選項 ①。** `openrouter_chat_model` 的 `max_retries` 改為參數、預設 0（形狀比照同輪的 `temperature`）；`router_chat_model` 傳 `config.max_retries`。`traceability.json` 的 `BR6.3` note 已刪掉「全部由 `RoutingConfig` 驅動，不寫死」那句並寫明它曾為假、與 `NFR3.63` 列互相矛盾；`NFR3.63` note 同步改為「0 是設定的預設值而不是寫死的字面值」 |
| `R-03` | Major | **接受，兩項全做，不回改成模組層。** ① §五 #9 新增**指名 `U13 brain-gateway` 的 `code-generation`** 的 open item，寫明「每個請求建一個 router ⇒ 每輪多付一次 TLS 握手」與 `performance-design.md:41` 的逐字警告，並給出具體要求（app 層單一實例，不得在 request handler 內建構）；② 測試改為計數 `model_factory`／`graph_builder` 的呼叫次數（兩輪各須為 1）——舊版只斷言 `model.calls == 2`，而 `model_factory` 每次回同一個替身，所以分辨不出來 |
| `R-04` | Major | **接受，不改算式。** §三.1 的標記句已補明「該標記只在日誌裡，`U13` 與 `build-and-test` 的 `NFR1` 量測作業都取不到」；§五 #10 新增該缺口並**指名 `nfr-requirements`／`build-and-test` 在定案 `OQ-10` 時一併處理「`scores_available` 是否要上線上形狀」**。**未自行擴充 `K-10`**（無授權） |
| `R-05` | Minor | **接受，與 `R-01` 一併。** `referent_state` 缺鍵即 `MalformedRouting`（與 `tied_with_next` 同形）＋ negative case ＋ 反向的「明寫 `absent` 仍被接受」 |
| `R-06` | Minor | **接受，三項全做。** ① 逐檔的 `Ran N` 與 ② 追溯的四個計數都由腳本在**最後一次內容改動之後**輸出（見 §二）；③ §五 #8 新增唯一的 `GAP`（`AC1.1.5`）及其承接站 |
| `R-07` | Minor | **接受，兩項全做 ＋ 突變驗證。** `P3`：`_unscored_ranking` 的單一候選改為**抽** `tied_with_next`（原本固定 `False`，所以第一個 disjunct 刪掉也全綠）；`P4`：提高後的分數改為自 `[原分數, 1.0]` 以 `raise_factor` 插值抽取（原本固定 `1.0`，而 `1.0 >= threshold` 恆真）。結果見 §八 |
| `R-08` | Minor | **不處置（依編排者指示）。** `scalability-design.md:55` 的誤引維持現狀、**不回改上游**；它已列在 §五 #1，由有權修它的站處置 |
| `R-09` | Minor | **接受。** 兩處偏離補進 §四 第 9、10 列 |
| `R-10` | Minor | **接受。** 三處 observer 呼叫全部改走 `IntentRouter._observe()`（捕 `Exception`、記 WARN、原始例外原樣向上）＋ 三條測試（失敗路徑、成功路徑、`prompt_guard` 命中路徑） |

**本輪另外修了一處審查沒點名的**：`intent_routing_parser.py` 的 `REFERENT_ABSENT`
在 `R-05` 改完後已無使用端，已從 import 移除（repo 的零死碼紀律）。

## 八、突變驗證（`R-07` 要求，本輪一併涵蓋七項修正）

做法：把修正改回錯的行為、跑測試確認**紅燈**、還原後複驗**綠燈**。

| 突變 | 突變後 | 紅的是哪幾條 | 還原後 |
|---|---|---|---|
| M1 (R-01) 移除 unresolved 守衛 | **紅**，7 項失敗 | `test_a_confident_score_does_not_override_an_unresolved_referent`、`test_an_unresolved_candidate_outside_rank_one_also_asks_back`、`test_p1_not_dispatchable_means_no_intents_and_some_candidates`、`test_p7_any_failed_slot_is_represented_in_the_candidates`、`test_the_exact_path_the_review_constructed_now_asks_back`、`test_the_unresolved_failure_reason_is_reachable_in_both_score_modes` | 綠（15） |
| M2 (R-07/P3) 刪掉 `len(...) == 1` disjunct | **紅**，2 項失敗 | `test_p2_dispatchable_means_intents_and_no_candidates`、`test_p3_single_candidate_without_scores_can_be_singled_out` | 綠（15） |
| M3 (R-07/P4) 有分數分支插中段凹陷 | **紅**，2 項失敗 | `test_p2_dispatchable_means_intents_and_no_candidates`、`test_p4_raising_the_top_score_never_flips_true_to_false` | 綠（15） |
| M4 (R-05) referent_state 缺值改回靜默取 absent（第一次的突變不等價，已重做） | **紅**，1 項失敗 | `test_a_missing_referent_state_is_malformed` | 綠（33） |
| M5 (R-02) router_chat_model 不傳 max_retries | **紅**，1 項失敗 | `test_the_configured_retry_budget_reaches_the_client` | 綠（18） |
| M6 (R-03) 每輪重建 client 與圖 | **紅**，1 項失敗 | `test_the_client_and_graph_are_built_once_not_once_per_turn` | 綠（18） |
| M7 (R-10) 移除 observer 的 try/except | **紅**，3 項失敗 | `test_a_failing_observer_does_not_replace_the_routing_error`、`test_a_failing_observer_does_not_swallow_the_guard_refusal`、`test_a_failing_observer_does_not_turn_a_success_into_a_failure` | 綠（18） |
| M3b 舊版 P4（固定 1.0）＋ M3 的凹陷 | **紅**，1 項失敗 | `test_p2_dispatchable_means_intents_and_no_candidates` | 綠（15） |

**兩件必須如實說明的事：**

1. **`M4` 第一次的突變不等價，測試照樣綠——而那不是測試不夠強。**
   我先把守衛改成 `if False:`，但緊接的 `state = raw.get("referent_state")` 會回
   `None`，而 `None` 不在封閉列舉內，於是照樣被擋下。**重做**為整段還原
   `raw.get("referent_state", REFERENT_ABSENT)`（真正的原缺陷）之後
   `test_a_missing_referent_state_is_malformed` 紅。記在這裡是因為
   「突變後仍綠」有兩種可能（測試太弱／突變不等價），而只報第一個數字會讓讀者
   誤判是前者。

2. **`M3b` 是一組對照，它要證明的是 `P4` 自己的強度。** 把 `P4` 改回固定
   `1.0`、再插入同一個中段凹陷：失敗的只有 `P2`（凹陷讓一個本該可交辦的槽位
   變成不可交辦，與 `P4` 無關），**`P4` 本身沒有紅**。亦即凹陷這個缺陷會被整套
   測試抓到，但抓到它的不是那條宣稱在測單調性的 property——改成區間抽取之後
   `P4` 自己就紅了（見 `M3`）。
