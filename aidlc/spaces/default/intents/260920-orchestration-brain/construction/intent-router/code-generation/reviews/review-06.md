## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-02 | Still applies | Minor | `IntentDecision.resolution` 仍是行程內欄位（`backend/services/intent_routing_types.py:260`，`compare=False`、`repr=False`，註解 `:247` 明寫不是 K-10 欄位）。新收據與上一份收據中 `intent_routing_types.py` 逐位元相同。追認仍待 `contract-summary.md` 的 K-10 下一次修訂，`merge-blockers.md` 第 54 列已登記承接，不阻擋。 |
| R-03 | Still applies | Minor | `brain_gateway.py` 的 `memory_forbidden` 路徑（`:1357`）與契約句子未動，該檔 sha256 與上一輪收據相同。已登記於 `merge-blockers.md` 第 54 列，由 brain-ws-contract／brain-gateway 釐清契約字面。 |
| R-05 | Still applies | Minor | `_PrefetchForbidden` 仍以正常回傳通過 `MemoryWorker`（`brain_gateway.py:1710`、`:1717`），熔斷器 `on_success()` 在 `:466`。程式未動，仍是已知限制。 |
| R-06 | Still applies | Minor | 選定後仍走 `_resolve_and_dispatch(..., scan=True)`（`brain_gateway.py:1629`），`referent` 不參與對象解析。程式與測試未動。 |
| R-07 | Still applies | Minor | 授權被拒前仍先寫入歷程（`brain_gateway.py` 的 `memory_forbidden` 記錄在 `:1357` 之後）。程式未動，仍是已知縱深缺口。 |
| R-08 | Still applies | Minor | `_on_select` 重建判定仍為 `below_threshold=False` 且 `confidence` 取候選分數（`brain_gateway.py:1622`）。程式未動，無讀取端受影響。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | backend/services/review_agent.py:181 與 backend/services/wa_lens_engine.py:614（連同 backend/tests/test_a3_langgraph_migration.py:35、:43） | 兩處原始碼各加了一行註解，內含字串 `openrouter_chat_model`，使 test_a3_langgraph_migration.py 的兩條 `assertIn("openrouter_chat_model", source)` 仍綠。這兩條斷言現在驗的是註解，不是呼叫：把 `chat_model(model=model_name)` 改回直打任何東西、只要留著註解，它們都不會紅。開發者已自述這一點，且 `test_claude_code_chat.py` 的 `test_every_call_site_goes_through_the_factory`（以 AST 掃呼叫）承擔了實質約束，所以不構成缺口；但那行註解是為了讓舊斷言過關而存在，之後沒有人會知道可以拿掉。 | 在 build-and-test 把那兩條斷言改成 `chat_model`，改完後刪掉兩處註解，並把這件事寫進 build-and-test 的回補項，避免註解變成永久的測試遷就。 |
| Minor | backend/tests/test_claude_code_chat.py（整檔）與 backend/services/review_agent.py:190 | claude-code 路徑下，review_agent 的 `compiled.astream(stream_mode="messages")` 與 wa_lens 的 JSON 取出沒有任何測試用 `ClaudeCodeChatModel` 實際跑過（五個呼叫點只有路由、design_agent 工具迴圈、cost 單次呼叫被真正執行；review 與 lens 只被 AST 掃描確認接了 factory）。`claude_code_chat.py` 模組 docstring 宣稱「`stream_mode="messages"` 會拿到整段一次的結果」，這個行為取決於 langgraph 對不串流模型的處理，沒有測試鎖住，code-summary 也寫明這兩條只跑過假 CLI 或未跑。 | 在 build-and-test 補兩個以假 `claude` 驅動的測試：review_agent 在 claude-code 下串流出完整文字、wa_lens 在 claude-code 下解出 answers；或在 LOCAL-DEV.md 的限制清單明寫 A3 路徑未經驗證。 |
| Minor | backend/services/claude_code_chat.py:413 與 :454（`cwd=tempfile.gettempdir()`）；LOCAL-DEV.md 新小節 | 子行程的工作目錄是共用的系統暫存目錄。在多人共用主機上，其他使用者可在該目錄預先放 `.claude/` 或 `CLAUDE.md`；目前能擋住它的只有 `--safe-mode` 這一個旗標，而該旗標的行為是開發者以 `claude --help` 確認的、repo 內沒有測試能驗證它真的不載入 cwd 的設定。風險限於本機開發，且 prompt 含使用者的架構圖。 | 改用每次呼叫（或每個行程）自建的私有暫存目錄（`tempfile.mkdtemp`，權限 0700）當 cwd，使保護不單靠一個外部旗標；或在 LOCAL-DEV.md 明寫此依賴與其適用前提（單人開發機）。 |
| Minor | backend/services/claude_code_chat.py:317-322 `_kill_process_group` 與 :414、:454 `start_new_session=True` | 逾時終止依賴 POSIX 專有的 `os.killpg` 與 `signal.SIGKILL`。Windows 上 `signal.SIGKILL` 不存在，會在逾時處理裡拋 `AttributeError`（`_kill_process_group` 只接 `ProcessLookupError` 與 `PermissionError`），遮蓋 `ClaudeCodeTimeout` 並可能留下子行程；LOCAL-DEV.md 的前置條件沒有寫明只支援 macOS／Linux。 | 在 LOCAL-DEV.md 前置條件寫明「只支援 macOS／Linux」，或在 `_kill_process_group` 對無 `killpg` 的平台退回 `process.kill()`。 |
| Minor | backend/services/claude_code_chat.py:325-346 `_result_text`、與 backend/services/review_agent.py:49 | 非零 exit 與 `is_error` 的固定訊息一律寫「可能尚未登入，請先執行 claude」。但 exit 非零也會來自無效的 `--model` 別名、CLI 用法錯誤或 CLI 自身故障，使用者會被導向錯誤的排查方向，而 stderr 與 result 原文刻意不外洩，所以無處得知真因。另 review_agent.py:49 的備援文字在 claude-code 下仍說「請確認已設定 OPENROUTER_API_KEY」（開發者已自述，未動）。 | 訊息改成不斷言原因（例如「CLI 執行失敗，請在終端機直接執行 claude -p 檢查」），並讓 review_agent.py:49 的備援文字依 `get_provider()` 分流；兩者都可併入 build-and-test 的回補項。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 以 `shasum -a 256` 對最新收據 `reviewed-source-477e51f29ffa.tsv`（35 列）逐列比對（awk -F tab 取欄位） | 35 列全部相同，0 變動 | 最新收據是 REVIEW_REQUESTED 當下的快照，目前工作樹與其逐位元一致，審查對象即現況。 |
| 以同法對上一份收據 `reviewed-source-ac865b241904.tsv` 比對 | 4 變：`LOCAL-DEV.md`、`backend/.env.example`、`backend/services/intent_routing_port.py`、`backend/services/langgraph_runtime.py` | 與 conductor 重算結果一致。`git diff HEAD` 顯示四檔的改動全部屬於第七節的 claude-code provider：`intent_routing_port.py` 只多一個類別名常數、`classify_transport_failure` 多一個分支、`router_chat_model` 改經 factory；`langgraph_runtime.py` 只新增 `chat_model`。未碰 L0 至 L5 的路由邏輯與 `brain_gateway.py`（後者 sha256 不變）。 |
| `git diff HEAD` 對 `code-generation-plan.md` | 唯一差異是檔尾新增「七、本機開發用 Claude Code provider」一節，第 283 行之前沒有任何差異 | 既有 48 格完全同 HEAD（含勾選字元）；新節七格為本輪新增。`grep -c` 實算 `[x]` 55、`[ ]` 0，與 code-summary 檔尾回復節宣稱相符，沒有未勾格需要判斷理由是否過時。 |
| 讀碼推演：非 local 是否一定退回 openrouter | 通過 | `get_provider()` 要求 `LLM_PROVIDER=claude-code` 且 `APP_ENV` 去空白轉小寫後恰為 `local`，未設定與空字串皆退回並記 ERROR；`configure_provider_env`、`llm_auth_ready`、`auth_error_message`、`chat_model` 四處都經它判斷，沒有旁路。部署側再有兩道獨立防線：`deploy/render-env.sh:119` 把 `LLM_PROVIDER` 釘死為 openrouter，`validate_env_contract.py` 新檢查禁止部署範本、renderer 與任一 compose 出現該值；`backend/.dockerignore` 排除 `.env`，所以開發者的 `.env`（載入時 override=True）不會被打進映像。 |
| 讀碼推演：openrouter 路徑是否逐位元不變 | 通過 | `chat_model` 在非 claude-code 時，無 builder 則 `openrouter_chat_model(**kwargs)` 原樣轉發，有 builder 則呼叫 builder。五個呼叫點：路由的 `model`／`timeout_seconds`／`temperature=None`／`max_retries` 原樣；review 與 lens 的 `model=model_name` 原樣；cost 的無引數呼叫原樣；design_agent 的 `ChatAnthropic` 引數（model、temperature=0.2、api_key、base_url）在 lambda 內未動，`bind_tools(tools)` 未動，`timeout_seconds=300` 只在 claude-code 分支被讀。`openrouter_chat_model` 本體未改；既有測試以 `patch("services.langgraph_runtime.openrouter_chat_model")` 攔截，因 `chat_model` 於呼叫時才查模組全域，攔截仍有效。 |
| 讀碼推演：子行程安全 | 通過 | 參數清單呼叫、不經 shell；prompt 與整段對話只走 stdin（`--system-prompt` 為固定字串）；環境為白名單且不含 `OPENROUTER_API_KEY`、`ANTHROPIC_*`、`JWT_SECRET`、`DATABASE_URL`；逾時時對整個行程群組送 SIGKILL 並回收，同步與非同步兩條路徑都有，`BaseException`（含取消）也會 kill；log 只記筆數、字元數、exit code、耗時，例外訊息為固定字串，`json.loads` 失敗的訊息不含內容。 |
| 讀碼推演：工具呼叫解析 | 通過 | `tool_choice` 指定或為 any 時，回應不含該工具（純文字、空陣列、只呼叫別的工具）一律拋 `ClaudeCodeMalformedToolCall`，路由層經類別名比對對應到 `MalformedRouting`；`tool_choice` 為空時幻想出的工具名也拋錯，不會變成 ToolNode 會執行的呼叫；整包任一筆形狀不對即不接受。`classify_transport_failure` 先判斷類別名，再判斷用量字樣，固定訊息不含用量字樣，所以 CLI 失敗對應 `LlmUnavailable`、逾時（亦為 `TimeoutError`）對應 `LlmUnavailable`。design_agent 迴圈中，AIMessage 的 tool_calls、ToolMessage 與 tool 名稱都有被序列化進下一輪 stdin。唯一未覆蓋的邊角：`bind_tools([], tool_choice="any")` 會在 `_ai_message` 回純文字，實務上不可達。 |
| 本審查未執行測試 | 未執行 | 依指示不跑測試、python 或任何寫檔指令；code-summary 宣稱的 36 個新測試、1433 全套與四個突變的紅燈結果，本審查以讀碼確認其斷言與突變目標一致，但數字本身未獨立重跑。 |

### Summary

第七節的 claude-code provider 在本審查的讀碼推演下成立：閘門以 `APP_ENV` 恰為 `local` 把關並有部署側兩道獨立防線，openrouter 路徑五個呼叫點的引數與行為都未改，子行程的 stdin、環境白名單、逾時終止與 log 無洩漏，強制工具呼叫未命中一定拋錯。七格勾選屬實，既有 48 格與 HEAD 無差異。沒有 Critical 或 Major；五項新 Minor 皆為測試遷就、未驗證的串流路徑、共用 cwd、POSIX 專有與誤導的錯誤訊息，建議併入 build-and-test 的回補項，六項前輪 Minor（R-02、R-03、R-05、R-06、R-07、R-08）因程式未動仍成立。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/traceability.json > MB-5 (status OK)；code-summary.md > 重新查驗與合併前必修第 5、13 項 > 二、殘留 | 兩個以上槽位都需澄清時，選定其一只交辦該槽位與已確定槽位，其餘不確定槽位不交辦且使用者不被告知（`intents_after_choice` 只取被選槽位）。這個殘留只寫在 §二 與 MB-5 的 note，沒進 §七 偏離與未驗項，MB-5 還標 `OK`。專案自己的規則說過：把有缺口的 AC 記成 OK 會讓追溯表看起來已覆蓋。靜默丟掉一件使用者說過的事，與「錯誤須浮出」的原則也有張力。 | 把它登記為指名承接站的 open item（產品取捨：逐槽位多輪反問，或交辦後明示「另一件事尚未處理」），放進 §七；MB-5 改為標示殘留的狀態，或拆出一列 GAP。 | Resolved (reviewer) |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/intent-router/code-generation/code-summary.md > 二、對 `K-10` 欄位集合的對齊紀錄 | `IntentDecision` 多了行程內欄位 `resolution`。我查證它不進任何序列化路徑：全 `backend/services` 無 `asdict`/`pickle` 用在判定物件，`PendingClarify` 只存在連線記憶體，`ClarifyCandidate` 仍逐欄組裝，`ws-contract.json` 未動。偏離如實記載，但只寫「下一輪契約修訂時追認」，沒有承接站。 | 在 §七 指名由哪一站在 `contract-summary.md` 的 `K-10` 追認「行程內附帶資料」，避免下一個讀契約的人以為欄位集合仍是四個。 | Unresolved |
| R-03 | Minor | backend/services/brain_gateway.py > `_on_user_message` 的 `memory_forbidden` 錯誤路徑；backend/ws-contract.json 與 frontend/src/types/ws-contract.d.ts > `turnId` 欄位說明 | 契約文字寫「連線建立後的 UNAUTHORIZED（BR2.8）turnId 為 null」，而本路徑的 UNAUTHORIZED 屬於某一輪、經 `_fail_turn` 帶該輪 turnId。程式合理，但契約的字面句子兩種讀法都成立；前端 `errorCategory` 只分類不依賴 turnId，所以今天不壞。 | 在 `code-summary.md` 明寫判讀（輪內授權錯誤帶 turnId），並交由 brain-gateway 單元於處理 #2 時一併把契約句子釐清，避免與 `_send_single_error` 的修法互相打架。 | Unresolved |
| R-04 | Minor | backend/tests/brain_gateway_fakes.py > `low_confidence`；backend/tests/test_brain_gateway_turn.py > #5 三個測試 | 閘道層的 #5 測試用手寫的 `resolution`，沒有經過真的 `decide`。候選 id 與對照 id 的配對，由 predicate 的 `@given` 測試單獨證明。兩段合起來成立，但沒有任何測試走過「真 `IntentRouter` 產生澄清判定、閘道選定、交辦意圖含 referent」整條線，將來有人改動 `_clarify_id` 或閘道取 id 的方式時，兩邊各自綠燈。 | 補一條以真 `decide` 結果餵給閘道的選定測試，或把配對責任寫成明確的結構性斷言；不阻擋。 | Resolved (reviewer) |
| R-05 | Minor | backend/services/brain_gateway.py > `_prefetch` 回傳 `_PrefetchForbidden` 的 OK 路徑；`MemoryWorker.run` | 授權拒絕以工作「成功回傳」的形式通過 `MemoryWorker`，所以熔斷器把它當成一次成功。這是想要的（不計入失敗），但副作用是：在熔斷半開狀態下，一個被拒絕的身分的探測會讓熔斷關閉，而實際上 facade 的資料庫可能仍不健康。 | 在 code-summary 補一句判斷與理由；若不想讓授權結果影響熔斷狀態，可在 `MemoryWorker` 對此型別不記成功。 | Unresolved |
| R-06 | Minor | backend/services/brain_gateway.py > `_on_select` 與 `_resolve_and_dispatch(scan=True)`（候選 3） | 第 5 項還原了被選候選的 `referent`，但選定後走的 `scan=True` 分支完全不讀 `decision.intents[*].referent`；全 backend 唯一讀 `referent` 的地方是 `scan=False` 分支的 `match_referent`（約 :1502-1520），`work_orchestrator` 也不讀。所以選定路徑上 `referent` 是只存在於 dispatch 參數裡的資料，不影響作業對象。若指涉詞是靠記憶解析出來的（原句不含目錄名稱，如 `test_select_keeps_the_referent_of_the_chosen_reading` 的情境），交辦會落在目前作業對象上，而高信心路徑會走 `match_referent` 設定或回報找不到對象。這不是本輪造成的退步（修前亦然），也符合 `BR64.13` 的原句掃描設計，但「#5 已解決」只在資料層成立，沒有行為層的測試鎖住「選定後對象如何決定」。 | 在 `code-summary.md` 或 open item 明寫「選定後 `referent` 不參與對象解析，僅靠原句掃描」，並指名由 `brain-gateway`／後續 intent 決定是否要對選定判定也跑 `match_referent`；補一條測試固定現行行為（記憶解析的 referent 不在原句 → 交辦於目前對象），避免日後誤以為已解析。 | New |
| R-07 | Minor | backend/services/brain_gateway.py > `_on_user_message`（候選 1） | 記憶授權被拒時，先 `append_message` 把使用者原文寫進該段歷程，再送 `UNAUTHORIZED`。若該段是共享段，一個已被撤銷核准的身分的原文會進入其他成員可見的歷程。此順序是 `BR64.6` 既有規則，本路徑只在核准於重驗與預取之間被撤銷時可達，窗口很窄，且握手與每則訊息重驗已先擋待核准帳號。 | 不阻擋；在 `code-summary.md` 記為已知縱深缺口，並建議後續讓「授權類錯誤」的輪次不寫入歷程，或至少不寫入共享段。 | New |
| R-08 | Minor | backend/services/brain_gateway.py:1621 `_on_select`（候選 2） | 選定後重建的 `IntentDecision` 為 `below_threshold=False`，但 `confidence` 取被選候選的分數（常低於門檻，無分數時為 `0.0`），與 `K-10`「`below_threshold` 等於 `confidence < threshold`」的關係不一致。全 backend 沒有任何程式讀 `decision.confidence` 或在 dispatch 前驗證該關係，故無實際影響；`IntentDecision` 也沒有執行期不變式檢查。 | 不阻擋。在 `code-summary.md` 註記這是「使用者確認後的判定」，`confidence` 僅供觀測；或改填門檻值以維持關係成立。 | New |

> R-02 Not re-checked this round

> R-03 Not re-checked this round

> R-05 Not re-checked this round

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round
