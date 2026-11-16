**Collaborator:** aidlc-developer-agent

## Contribution（修訂 1 輪：US11／US12／US13）

本檔每一項事實都是本輪在 worktree `chiton`（branch `danniel/docs/orchestration-brain-ideation`，
HEAD `9130b80`）實際開檔或實跑取得。計數類皆以 `grep -c` 或腳本實算，不目測。**不轉引
codekb，不轉引 requirements.md 的既有斷言**——下面有兩處與上游記載不一致，皆附證據。

我的透鏡只有一個：**每一條 AC 的 Given 在本 repo 的自動化環境裡構造得出來嗎，Then 真的
會因為實作錯誤而失敗嗎。** 下面 13 項發現按這個順序排：先是「這條 AC 的 Then 在正確實作
之後仍然會失敗」（最嚴重），再是「Given 不可達」，最後是「Then 永遠通過」。

---

## 第一部分：FR13 的實證複驗（問題一、問題二）

### V-01（Critical）FR13.1 指定的鍵（`thread_id`）無法讓 FR13.2 的斷言在修好之後通過

**這是本輪最嚴重的一項：按 FR13.1 的字面實作完成之後，依 FR13.2 寫的測試仍然會紅燈。**

FR13.1 逐字寫「該狀態須先改為 **per-key**（鍵為 session 或 `thread_id`）」。我逐一查了
`run_design_agent` 的**全部**三個呼叫點與它的簽章：

```
$ grep -rn "run_design_agent" backend/ frontend/
backend/test_agent.py:5:from services.design_agent import run_design_agent
backend/test_agent.py:41:            async for event in run_design_agent(messages, thread_id=thread_id):
backend/services/wa_collab_orchestrator.py:18:from services.design_agent import run_design_agent
backend/services/wa_collab_orchestrator.py:79:    async for event in run_design_agent(messages, current_xml):
backend/services/design_agent.py:171:async def run_design_agent(
backend/services/agent_router.py:33:from services.design_agent import run_design_agent
backend/services/agent_router.py:125:        async for event in run_design_agent(payload, request.current_xml, thread_id=f"user-{current_user.id}-design")
```

簽章（`design_agent.py:171–175`，實讀）：

```python
async def run_design_agent(
    messages: list[dict[str, str]],
    current_xml: str | None = None,
    thread_id: str = "default-thread",
) -> AsyncIterator[dict[str, str]]:
```

於是 `thread_id` 在兩個生產呼叫點的實際基數是：

| 呼叫點 | 傳入的 `thread_id` | 以它為鍵能隔離什麼 |
|---|---|---|
| `agent_router.py:125`（A1 產圖 SSE） | `f"user-{current_user.id}-design"` | 只隔離**不同使用者**。**同一個使用者開兩個分頁＝同一個鍵**，仍然互踩 |
| `wa_collab_orchestrator.py:79`（A4 共編） | **不傳**，落回 `"default-thread"` | **什麼都不隔離**。全站所有 A4 請求共用一個鍵 |

**結論**：以 `thread_id` 為鍵，A4 路徑的隔離度是 1 個鍵（即完全沒有隔離），A1 路徑是
per-user（不是 per-request）。FR13.2 的 Then 是「兩個併發請求各自只收到自己產生的事件」
——它在這兩種鍵之下都**仍然會失敗**。而 FR13.1 的另一個選項「session」在
`run_design_agent` 的簽章裡**根本不存在**，沒有任何參數承載它。

**建議的 AC（請把鍵的來源寫進 AC，不要留在 FR 的括號裡）**：

| AC | Given / When / Then |
|---|---|
| **AC13.1.1** | **Given** 同一位使用者的兩個分頁同時送出產圖請求（兩者的 `thread_id` 相同），**When** 兩個請求重疊執行，**Then** 兩邊各自收到**非空**的事件集合，且兩個集合**無交集** `[FR13.1][FR13.2]` |
| **AC13.1.2** | **Given** 兩位不同使用者同時觸發 A4 共編（`wa_collab_orchestrator.py:79` 路徑，兩者皆無 `thread_id`），**When** 兩個請求重疊執行，**Then** 兩邊各自收到非空且無交集的事件集合 `[FR13.1][FR13.2]` |

`AC13.1.1` 與 `AC13.1.2` 合起來才把「鍵不得由 `thread_id` 推導」釘死：**只要鍵是
`thread_id`，這兩條就都過不了**。這比在 FR 裡寫一句「鍵為 session 或 thread_id」有用，
因為後者照字面做出來是錯的。對應的實作形狀是：鍵在 `run_design_agent` **進入時就地鑄造**
（每次呼叫一個新 token），不從呼叫者傳進來的任何值推導。

---

### V-02（Critical）FR13.2 **可以**在本 repo 的 harness 寫出來——我寫了也跑了，而它失敗的方式不是 FR13.3 描述的那一種

**先回答問題一的後半：可以構造，零新依賴，不需要 LLM，不需要網路。** 構造方式與現成前例：

- 前例就在 repo 裡：`backend/tests/test_langgraph_migration.py` 用
  `unittest.IsolatedAsyncioTestCase`，`@patch("services.design_agent.ChatAnthropic")` ＋
  `get_design_model_name` ＋ `configure_provider_env` 三個 patch，直接驅動真的
  `build_graph().compile(checkpointer=memory)`。所以「驅動 design_agent 的圖」在本 repo
  已經有人做過，不是新路。
- 本輪我用的切法（比上面那支更小）：patch 四個點——`llm_auth_ready`→`True`、
  `configure_provider_env`→no-op、`build_mxgraph_xml`→回傳每次呼叫唯一的假 XML、
  `build_graph`→一個假 workflow，它的 `compile()` 回傳一個假 compiled graph，而該
  graph 的 `astream` 是一個 async generator，在 `asyncio.Event` 閘門控制下**呼叫真的
  `draw_architecture_diagram.ainvoke(...)`**。
- **關鍵**：`run_design_agent` 的**整個函式本體**（`:176–218`，含 `:183` 的全域賦值、
  `:203`／`:211` 的 drain、`:218` 的 `None`）與**工具對模組全域的四處讀取**
  （`:81`／`:84`／`:96`／`:101`）全部是真的。被換掉的只有 LLM 邊界。缺陷正好落在沒被
  換掉的那一側，所以這個構造是有效的，不是在測 mock。

**實跑結果**（`python3` 直跑，`PYTHONPATH=backend`，`asyncio.run`；兩個請求 A／B 以
`asyncio.Event` 強制交錯：A 進入後停在工具前，B 才啟動）：

```
A stream: [{'type': 'error', 'content': "發生未預期錯誤：'NoneType' object has no attribute 'get_nowait'"}]
B stream: [{'type': 'progress', ...}, {'type': 'xml', 'content': "<mxGraphModel id='call1'/>"},
           {'type': 'progress', ...}, {'type': 'xml', 'content': "<mxGraphModel id='call2'/>"},
           {'type': 'message', 'content': 'done-B'}]
A xml: []
B xml: ["<mxGraphModel id='call1'/>", "<mxGraphModel id='call2'/>"]
ASSERT A non-empty  -> False
ASSERT B non-empty  -> True
ASSERT disjoint     -> True
```

伴隨的 traceback（來自 `design_agent.py:203` → `:163`）：

```
AttributeError: 'NoneType' object has no attribute 'get_nowait'
```

**三項要給 lead 的解讀，每一項都改變 AC 該怎麼寫：**

**(a) 內容真的跨請求交付了。** B 的串流裡有**兩個不同的** XML（`call1` 與 `call2`），
而 B 自己的工具只跑了一次。`call1` 是 **A 的工具產出，落進了 B 的串流**。這不是「事件
遺失」，是一個使用者的架構圖內容出現在另一個使用者的串流裡。FR13.2 與 FR13.3 都沒有
說出這一面——FR13.3 只寫「被**靜默丟棄**」。

**(b) 另一條路徑不是靜默的，是把 Python 內部例外字串送到瀏覽器。** A 收到的唯一事件是
`{'type': 'error', 'content': "發生未預期錯誤：'NoneType' object has no attribute
'get_nowait'"}`。機制：`:203` 的 `_drain_progress(_progress_queue)` 是**呼叫當下取全域
的值**，B 的 `finally`（`:218`）已先把全域設成 `None`，於是 A 把 `None` 傳進去，
`:163` 的 `queue.get_nowait()` 丟 `AttributeError`，被 `:214` 的
`except Exception` 捕獲並 `yield {"type": "error", "content": f"發生未預期錯誤：{e}"}`。
而 `agent_router.py:126–127` 把事件原封 `json.dumps` 塞進 SSE 的 `data:` 行——**這段
內部例外字串會送到使用者的瀏覽器**。`phases/construction.md` 的「Errors must be
surfaced」要的是錯誤不被吞掉，不是把 `AttributeError` 的 repr 給使用者看。

**(c) 「互斥」這個斷言單獨寫會在壞碼上通過。** 看最後三行：`disjoint -> True`，因為
A 的集合是空的，空集合與任何集合都互斥。**FR13.2 已經寫了「且各自非空」，這一點它寫
對了**，我要指出的是順序與補強：測試必須先斷言兩邊非空、再斷言互斥，且**還要斷言沒有
任何 `error` 事件**——否則「A 只拿到一則 error、B 拿到全部」這個今天就會發生的狀態，
在只看互斥的測試眼裡長得像通過。

**建議：把 FR13.3 的 Then 拆成兩條，因為它實際有兩個可達的終局：**

| AC | Given / When / Then |
|---|---|
| **AC13.2.1** | **Given** 兩個重疊的產圖請求，**When** 先結束的那個走完 `finally`，**Then** 另一個仍在進行的請求**不得**收到任何 `type == "error"` 的事件，且其 `content` 不得包含任何 Python 例外型別名（今日實測為 `AttributeError`）`[FR13.3]` |
| **AC13.2.2** | **Given** 同上，**When** 兩個請求都結束，**Then** 任一請求的 `xml` 事件內容**不得**出現在另一請求的事件集合中 `[FR13.2]` |

`AC13.2.2` 是把 (a) 寫成可判定形式；它在今天的程式上會紅燈（B 的集合含 `call1`），在
修好之後會綠燈，而且它**無法以「把事件丟掉」的方式作假**——丟掉事件會先讓「非空」那條
失敗。

**本輪與上游記載不一致的一處（請 lead 決定要不要改 FR13.2 的措辭）**：FR13.2 逐字寫
「**已實測**：A 收到 B 產生的架構圖 XML、B 收到空」。我實測到的是**反方向**：B 收到 A
的 XML、A 收到一則 error。兩者都是同一個缺陷的表現，**方向由交錯順序決定**，不是固定
的。把某一個方向寫成「已實測」的結論，會讓依它寫測試的人把斷言綁死在那個方向上，而那
個方向不保證重現。建議改寫為「已實測：事件會跨請求交付，方向依交錯順序而定；另一條路徑
是進行中的請求收到 `AttributeError` 字串」。

---

### V-03（Major）FR13.4 **證實為真**，而且它是**另一個**缺陷，不是 `_progress_queue` 的同一個

**問題二的答案：FR13.4 成立，且它與 `_progress_queue` 的機制與影響面都不同，修好
`_progress_queue` 對它零作用。**

證據（三處逐行實讀）：

```
backend/services/wa_collab_orchestrator.py:79:    async for event in run_design_agent(messages, current_xml):
backend/services/design_agent.py:174:    thread_id: str = "default-thread",
backend/services/design_agent.py:168-169:  # Shared memory saver for the POC
                                            memory = MemorySaver()
backend/services/design_agent.py:189:    graph = build_graph().compile(checkpointer=memory)
```

所以：`:79` 不傳 `thread_id` → 落回 `:174` 的 `"default-thread"` → `:196` 的
`config = {"configurable": {"thread_id": thread_id}}` → 全站 A4 共編請求共用一個
checkpointer thread，而 checkpointer 是 `:169` 的**模組層單一 `MemorySaver()`**。
FR13.4 說的「可能使所有 A4 共編使用者共用同一個 checkpointer thread」——**成立，不是
「可能」**。

**它為什麼是另一個缺陷：**

| | `_progress_queue` | `thread_id="default-thread"` ＋ 共用 `MemorySaver` |
|---|---|---|
| 被污染的東西 | 事件**通道**（progress／xml／error） | LangGraph 的**對話狀態**（checkpoint 裡的 `messages`） |
| 生命週期 | 單一請求內（`finally` 清掉） | **跨請求累積**，行程生存期內永不清除 |
| 外洩途徑 | 事件被送到錯的串流 | `call_model`（`:131–140`）把 checkpoint 裡的歷史 `non_system_msgs` **一併送進 LLM**——別人的架構需求成為我這次請求的模型輸入 |
| 修 `_progress_queue` 有幫助嗎 | 是 | **否，完全無關** |

附帶一項 FR13.4 沒提的：`MemorySaver()` 是行程內無上限成長的，單一 thread 永不輪替，
`messages` 透過 `add_messages` 只增不減（`:1xx` 的 `Annotated[list[BaseMessage],
add_messages]`）。長時間運行後這條 thread 的歷史會把 LLM 的 context window 吃掉——
`services/llm_limits.py` 的 `truncate_text_for_llm` 是對單一文字截斷，不是對 checkpoint
歷史做視窗管理。

**FR13.4 目前標為「待查，非本輪斷言」——建議升為自己的 AC，不要併進 FR13.1 的修復範圍
註記裡。** 理由就是上表最後一列：它不是同一個修法，併進去會讓「FR13 做完了」被讀成兩個
問題都解了。

| AC | Given / When / Then |
|---|---|
| **AC13.3.1** | **Given** 兩位不同使用者各自觸發 A4 共編，**When** 第二位的請求執行，**Then** 送進模型的訊息序列中**不含**第一位使用者的任何訊息內容 `[FR13.4]` |
| **AC13.3.2** | **Given** A4 共編請求，**When** 觀察其 LangGraph `config`，**Then** `thread_id` **不得**為 `"default-thread"`，且不同使用者的值互異 `[FR13.4]` |

`AC13.3.2` 構造成本極低（patch `ChatAnthropic`、攔 `config`），`AC13.3.1` 可用
`test_langgraph_migration.py` 既有的 `graph.get_state(config)` 形狀斷言。兩者都不需 LLM。

---

### V-04（Minor，但應補）FR13 只點名 `_progress_queue`，同一支檔還有第二個同型全域沒被納入

```
$ grep -rn "_last_xml" backend/
backend/services/design_agent.py:32:_last_xml: str | None = None
backend/services/design_agent.py:78:    global _last_xml
backend/services/design_agent.py:95:        _last_xml = xml_data
backend/services/design_agent.py:176:    global _progress_queue, _last_xml
backend/services/design_agent.py:184:    _last_xml = None
```

`_last_xml` 與 `_progress_queue` 是**同一個形狀**：模組層全域、在 `run_design_agent`
入口重設（`:184`）、由工具寫入（`:95`）。差別是**它今天沒有任何讀取端**（上面五處命中
全在同一支檔，無一是讀取），所以是**潛伏**而非活的缺陷——我如實標為 Minor，不誇大。

但它與 FR13 相關：FR13.1 只寫「該狀態」（單數，指 `_progress_queue`）。若按字面只把
`_progress_queue` 改成 per-key，`_last_xml` 會留在原地，而下一個需要「取回上一張圖」的
功能（能力 1 的 xml 續編情境很可能就是）一讀它就重現同一個 bug。建議 FR13.1 把
「`design_agent.py` 內**所有**跨請求共享的模組層可變狀態」寫進範圍，並附一條可機械
執行的檢查：**該模組內 `global` 宣告數須為 0**（今天是 `:78` 與 `:176` 兩處）。

---

## 第二部分：FR12 的落點查證（問題四、問題五、問題六）

### V-05（Critical）FR12.5c 的理由是錯的——資料庫**不會**擋下 FR12.5 所指的那個動作

FR12.5c 逐字：「本條與資料庫現況一致：`schema_rbac.sql:330` 的 `owner_user_id` 為
`NOT NULL` 且無 `ON DELETE` 子句——**資料庫今天就會擋下該刪除**。」

**行號對了**（這一輪我逐行數過，`:327` 是 `CREATE TABLE IF NOT EXISTS projects (`、
`:328` 是 `id SERIAL PRIMARY KEY,`、`:329` 是 `name`、`:330` 是
`owner_user_id INTEGER NOT NULL REFERENCES users (id),`——上游先前的 `:328` 已更正，
這次無誤）。**但推論錯了，而且錯在關鍵處。**

FR12.5 要擋的動作逐字是「**停用動作本身須被擋下**」，FR12.5a 逐字把檢查掛在「**既有的
停用使用者端點**」上。那支端點是 `PUT /api/auth/{user_id}/active`
（`user_router.py:635`，`update_user_active`），它做的事是：

```python
backend/services/user_router.py:673:    target_user.is_active = request.is_active
backend/services/user_router.py:674:    db.commit()
```

**這是對 `users.is_active` 的 UPDATE。** `projects.owner_user_id` 上的
`NOT NULL REFERENCES users(id)` 外鍵對「更新 users 的某個非鍵欄位」**零效力**——它只在
`DELETE FROM users` 時才會擋。所以「資料庫今天就會擋下」這句話對**停用**不成立。

會被外鍵擋的是另一支端點：`DELETE /api/auth/{user_id}`（`user_router.py:679`，
`delete_user` → `:715` 的 `_hard_delete_user`）。而那支端點已經有前置條件：

```python
backend/services/user_router.py:690:    if target_user.is_active:
backend/services/user_router.py:691:        raise HTTPException(400, detail="請先停用帳號後再刪除")
```

另外，`schema_rbac.sql` 自己的 COMMENT 逐字否掉了「現況已定案」這個讀法：

```sql
COMMENT ON COLUMN projects.owner_user_id IS
  'U4: who owns this project. Deletion behaviour of the referenced user is deliberately
   NOT decided (OQ-H1, landing U7) — no ON DELETE clause, same as user_diagrams.user_id.';
```

「無 `ON DELETE` 子句」在這裡是**刻意未定案**的痕跡，不是一道已設計好的護欄。

**為什麼這是 Critical 而不是措辭問題**：FR12.5c 的結論（「不需放寬任何 schema 約束」）
剛好是對的，但它給的理由會讓實作者相信**存在一道資料庫層的 backstop**。實際上停用路徑
沒有任何 backstop，應用層的檢查是**唯一**的防線。相信有 backstop 的人會把應用層檢查寫
得比較鬆（例如只做在前端，或只在部分分支），而 FR12.5a 恰好有一句「不得只做在前端」
——兩句話放在一起會讓人以為那是雙層保險。

**附帶的真實缺口（FR12.5a 的範圍沒涵蓋到）**：FR12.5a 只把檢查掛在停用端點。對於**在
本功能上線前就已經是停用狀態**的帳號，停用那一關早就過了，`DELETE /api/auth/{user_id}`
可以直接打進去，`:690` 的前置條件也滿足（已停用），於是走到 `_hard_delete_user`，外鍵
丟 `IntegrityError` → **500，不是乾淨的 409**。建議 FR12.5a 的落點改為「停用端點**與**
刪除端點兩支」，或在 AC 明寫刪除端點的行為。

**建議的 AC：**

| AC | Given / When / Then |
|---|---|
| **AC12.5.1** | **Given** 某使用者是至少一個專案的唯一成員，**When** 管理者對他送出 `PUT /api/auth/{user_id}/active` 且 `is_active=false`，**Then** 回應為 **409**，`is_active` 在資料庫中**未改變**，且回應中列出那些專案的名稱 `[FR12.5][FR12.5a]` |
| **AC12.5.2** | **Given** 某**已停用**的使用者是至少一個專案的唯一成員，**When** 管理者對他送出 `DELETE /api/auth/{user_id}`，**Then** 回應為 **409** 並列出那些專案，**不得**是 500 或資料庫 `IntegrityError` `[FR12.5a]` |

`AC12.5.1` 的「`is_active` 在資料庫中未改變」這一句是刻意加的：沒有它，一個「先寫入再
回 409」的實作會通過。

---

### V-06（Critical）「唯一成員」在今天的資料模型下等於「每一位使用者」——照字面實作會讓停用端點永久失效

這一條與 V-05 相互獨立，而它更危險，因為它會**壞掉一個既有功能**。

兩個事實：

**(1) 不存在任何成員表。**

```
$ grep -ni "CREATE TABLE" schema_rbac.sql | grep -i "member\|project"
327:CREATE TABLE IF NOT EXISTS projects (
```

只有 `projects`。沒有 `project_members`、沒有任何 membership 表。所以「成員」今天唯一
可能的推導來源就是 `projects.owner_user_id`。

**(2) 遷移程序為每一位持有架構圖的使用者各建一個預設專案，並把他設為 owner。**

```
backend/services/hierarchy_migration.py:380: def _resolve_default_pair(
backend/services/hierarchy_migration.py:390:     `is_default` 的唯一寫入端。
backend/services/hierarchy_migration.py:411:                 owner_user_id=user_id,
backend/services/hierarchy_migration.py:412:                 is_default=True,
backend/services/hierarchy_migration.py:361: def _users_holding_diagrams(db: Session) -> list[tuple[int, str]]:
```

**合起來**：遷移跑完之後，每一位持有架構圖的使用者都是**至少一個專案的唯一「成員」**
（因為他是 owner，而 owner 是唯一可推導的成員關係）。於是 FR12.5a 照字面實作，
`PUT /api/auth/{user_id}/active` 的 409 分支會對**每一位這樣的使用者**命中——**停用功能
整支失效**，包含它既有的兩道保護（`:645` 不能停用自己、`:649–668` 不能停用最後一位
J3a.edit 管理員）也一併失去意義，因為根本到不了 `:673`。

這正是「Then 會因為正確實作而失敗」的反面：這條 AC 寫成今天這樣，**一個完全忠於需求的
實作會把既有端點做壞**，而且 e2e 與 TestClient 測試都會看到 409 並以為那是對的。

**必須在 AC 層解掉，不能留給設計階段**，因為兩條路的驗收形狀不同：

- 路 A：「唯一成員」的定義排除 `is_default=TRUE` 的專案（那是遷移產物，不是使用者協作的
  專案）。AC 要寫出這個排除，否則測不出來。
- 路 B：「唯一成員」以 membership 表為準，而該表在 FR12.5a 可驗之前必須先存在——那就是一
  條**順序依賴**，必須寫進 Definition of Done，否則 FR12.5a 會在成員表落地前被標成完成。

**建議的 AC（路 A 的形狀，若 lead 選路 B 請改寫 Given）：**

| AC | Given / When / Then |
|---|---|
| **AC12.5.3** | **Given** 某使用者**只**擁有遷移產生的預設專案（`is_default = TRUE`）、不擁有也不屬於任何其他專案，**When** 管理者停用他，**Then** 停用**成功**——預設專案不構成 FR12.5 的「唯一成員」`[FR12.5]` |

這一條是**反向**斷言：它存在的唯一目的就是讓「把每個人都擋住」的實作紅燈。沒有它，V-06
描述的壞法會安靜通過。

---

### V-07（Major）FR12.4 的「最早加入的成員」依賴一張不存在的表，且挑選規則在平手時不是全函式

**(a) 沒有加入時間可讀。** 承 V-06 的證據：無成員表。`projects` 有 `created_at`
（`schema_rbac.sql:332`，`TIMESTAMPTZ NOT NULL DEFAULT now()`），但那是**專案**的建立
時間，不是**成員**的加入時間。所以 FR12.4 的 Given（「同樣的成員集合與加入時間」）今天
沒有任何資料來源。這本身對一則故事是可以的（表要新建），**但 AC 不能寫成好像它存在**，
否則 delivery-planning 會把 FR12.4 排在成員表之前。

**(b) FR12.4a 的 PBT 性質在平手時不成立。** FR12.4a 逐字：「挑選結果對同一組成員資料
**恆定**——同樣的成員集合與加入時間必然選出同一人。」兩位成員的加入時間相同時（同一個
批次邀請、同一個 transaction、`DEFAULT now()` 在同一個 statement 內會產生相同值），
「最早加入」有兩個答案，而 FR12.4 沒有給 tiebreak。**Hypothesis 會在幾十個 example 內
找到這個平手案例**——`project.md` 的 ADR-0006 PBT hard constraint 已經把這段挑選邏輯列
為 PBT 候選，所以這不是假想的風險，是這條 property 寫出來就會紅燈。

這一點值得強調：**這是一個「PBT 會抓到、example-based 永遠抓不到」的缺口**，正是
ADR-0006 存在的理由。補 tiebreak 的成本是一句話，不補的成本是 PBT 一上線就紅燈、然後有人
為了讓它綠而把 property 弱化成 example。

**建議**：FR12.4 的挑選規則補成「最早加入者；加入時間相同時取 `user_id` 最小者」，並把
FR12.4a 改寫為兩條可判定的 property：

| AC | Given / When / Then |
|---|---|
| **AC12.4.1** | **Given** 任一組成員（含加入時間完全相同的多位），**When** 對同一組輸入連續呼叫挑選函式兩次，**Then** 兩次結果相同（**全函式、無例外路徑**）`[FR12.4a]` |
| **AC12.4.2** | **Given** 一組成員中有兩位以上加入時間並列最早，**When** 執行挑選，**Then** 結果為其中 `user_id` 最小者 `[FR12.4]` |

`AC12.4.1` 是純函式層，落在不讀 DB 的模組——與 `team.md` 的三層形狀一致，也是 PBT 唯一
能真正施力的位置。

---

### V-08（Major）FR12.5b 點名的 OpenAPI 漂移閘門**不會**因為加一個 409 而啟動

FR12.5b 逐字：「同時觸發 CI 的 **OpenAPI 漂移閘門**，須在同一個 PR 內重 dump
`openapi.json`。」

**我實算了整份 `openapi.json`：**

```
$ python3 -c "...scan openapi.json..."
total paths: 42
status-code histogram across all operations: {'200': 53, '422': 45, '201': 1, '204': 1}
operations declaring any 4xx/5xx other than 422: []
```

**42 條 path、55 個 operation，宣告非 422 的 4xx／5xx 的有 0 個。** 而程式裡到處在 raise
400／403／404——單看 `update_user_active` 與 `delete_user` 兩支就有
`user_router.py:643`（404）、`:645`（400）、`:665`（400）、`:683`（404）、`:685`（400）、
`:690`（400）六處。再看目標端點自己：

```
PATH /api/auth/{user_id}/active
  PUT responses: ['200', '422'] -> {'200': UserSchema, '422': HTTPValidationError}
```

**它今天就會 raise 400 和 404，而 `openapi.json` 裡只有 200 與 422。** 原因是 FastAPI 只
把 **decorator 的 `responses=` 參數**寫進 spec，`raise HTTPException(409, ...)` 不會被
靜態發現。

**後果鏈（每一環都查過）**：
1. `raise HTTPException(409, ...)` → `openapi.json` 不變
2. → `backend/scripts/dump_openapi.py --check` 比對通過，CI 的該道 job 綠燈
3. → `frontend/package.json:12` 的 `gen:types`（`openapi-typescript ../openapi.json -o
   src/types/api.d.ts`）產不出 409 的型別
4. → 前端對 409 的處理沒有任何編譯期或 CI 期的檢查

**這與上一輪 `AC9.1.2`／`AC9.1.3` 是同一個形狀**：AC 把保證掛在一道不會對它開火的閘門
上。FR12.5b 不是寫錯字，它是在一個**不成立的機制假設**上寫了測試義務。

**建議**：FR12.5b 補一句可機械檢查的實作約束，並把它寫進 Definition of Done 而非 AC
（AC 驗行為，DoD 驗交付）：

> **DoD（US12 全群）**：`PUT /api/auth/{user_id}/active` 的 route decorator 必須顯式
> 宣告 `responses={409: {"model": <專案清單回應模型>}}`。**查證方式**：重 dump 之後
> `openapi.json` 中該 operation 的 responses 必須含 `409`。少了這一步，
> `dump_openapi.py --check` 不會察覺任何變化（本輪實算：55 個 operation 目前宣告非 422
> 的錯誤碼者為 0），FR12.5b 所依賴的漂移閘門不會啟動。

**附帶一項形狀衝突**：該端點是 `response_model=UserSchema`，而 409 要回「專案清單」。
`user_router.py` 的 29 處 `HTTPException` **全部**用純字串 `detail`。回一個清單等於引入
本 router 第一個非字串 `detail`——FastAPI 允許（`detail` 可為任意 JSON-able），但它不會
進 spec，所以前端拿到的是 `unknown`。這強化了上面那條 DoD：清單必須有宣告的 model，不能
只塞進 `detail`。

---

### V-09（Major）FR12.1 的「建立者自動成為 owner」今天**沒有任何寫入端**，而 AC 的可觀察形式預設了兩個不存在的東西

**(a) `projects.owner_user_id` 的唯一寫入端是遷移。**

```
$ grep -rn "owner_user_id" backend --include="*.py"
backend/services/hierarchy_migration.py:411:                owner_user_id=user_id,     ← projects 的唯一 INSERT
backend/cost/estimate_intake_service.py:356:        owner_user_id=owner.id,            ← EstimateSet，另一張表
backend/models.py:200:    owner_user_id = Column(                                       ← EstimateSet 的 ORM 欄
backend/database.py:443:          owner_user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,   ← estimate_sets
（其餘為 estimate_access.py 的讀取與 tests/）
```

注意 `database.py:443` 的那一個**有** `ON DELETE CASCADE`，但它屬於
`estimate_sets`，**不是** `projects`。這是一個很容易誤引的陷阱：同名欄位、兩張表、相反
的刪除語意。任何「`owner_user_id` 沒有 ON DELETE」的主張都必須指明是哪一張表。

**(b) 沒有建立專案的端點。**

```
$ grep -rn "projects" backend/services/*.py backend/main.py | grep -i "post\|insert\|create"
（0 筆）
```

**(c) `brain_router.py` 不碰 `projects`，而且它自己就說了。** 該檔第 1 行逐字
「**DEMO SCOPE，非 U13 的正式交付**」，第 24 行逐字把「專案／系統／架構圖三層階層」列在
「**它刻意沒有實作的**」清單裡並指向 `U7 hierarchy-service`。它唯一的路由是
`:238` 的 `@router.websocket("/ws")`。`grep` 該檔 `owner_user_id`／`INSERT` → 0 筆。
**所以它不能被當成 FR12.1 的既有實作證據**（brief 的提醒是對的，我實查後確認）。

**(d) 於是 FR12.1 的「可觀察形式」有兩個不存在的前提。** 它逐字寫「剛建立的專案，其**成員
清單**恰有一列、即建立者」——需要 ① 建立專案的路徑（不存在，由 FR11.1 建）② 成員清單
（不存在，無成員表，見 V-06／V-07）。這對一則故事完全正常，**問題只在 AC 的措辭讓它讀
起來像在既有畫面上加一列**。delivery-planning 會據此低估。

**建議**：FR12.1 的 AC 把兩個前提寫成 Given 的一部分，讓依賴顯性：

| AC | Given / When / Then |
|---|---|
| **AC12.1.1** | **Given** 建立專案的端點與成員清單已存在（**兩者皆為本 intent 新建，非既有**），**When** 我建立一個新專案，**Then** 該專案的成員清單恰有一列、即我自己，角色欄顯示為專案管理者，且**不需任何人執行指定動作** `[FR12.1]` |
| **AC12.1.2** | **Given** 一個剛建立的專案，**When** 查詢 `projects.owner_user_id`，**Then** 其值為建立者的 `user_id`（今日唯一寫入端是 `hierarchy_migration.py:411` 的遷移路徑，本 AC 要求新增一個使用者觸發的寫入端）`[FR12.1]` |

---

### V-10（Minor）FR12.4 的「帳號被移除」沒有指明是停用還是刪除，而這兩支端點的順序約束是載入性的

FR12.4 逐字「`project_owner` 的帳號**被移除**時」。本 repo 有兩個不同的「移除」：

- `PUT /api/auth/{user_id}/active`（`:635`）——停用，UPDATE
- `DELETE /api/auth/{user_id}`（`:679`）——刪除，且**前置條件是必須已停用**（`:690`）

兩者的 Given 不同、可達性不同、失敗模式不同。AC 不指名就測不出來，而且若指的是刪除，
**自動改選必須在 `_hard_delete_user`（`:715`）之前的同一個 transaction 內完成**——否則
外鍵先爆。這個順序是載入性的，屬於行為而非實作細節，應該在 AC 裡。

**建議**：FR12.4 指名為「停用」（與 FR12.5 的擋下動作同一支端點，語意一致），並補一條：

| AC | Given / When / Then |
|---|---|
| **AC12.4.3** | **Given** 某 `project_owner` 的專案另有其他成員，**When** 管理者**停用**該帳號（`PUT /{user_id}/active`，`is_active=false`），**Then** 停用成功，且在同一次請求結束後該專案已有一位新的 `project_admin`——不存在「帳號已停用但專案無管理者」的中間狀態 `[FR12.4][FR12.4b]` |

---

## 第三部分：FR11 的落點查證（問題三）

### V-11（Major）FR11.5 的 Given 今天不可構造，而且它的斷言形式是黑名單，必要但不充分

**(a) repo 內沒有任何 MCP server。**

```
$ grep -rni "mcp" backend --include="*.py"
backend/services/user_router.py:85:    "H3": "MCP／Skill 生命週期",
$ grep -rni "mcp" backend --include="*.py" | wc -l
       1
$ grep -rni "mcp" backend/requirements.txt frontend/package.json
（0 筆）
```

唯一那一筆是 `STORY_LABELS` 裡的 RBAC 故事標籤（`"H3"`），與通道毫無關係。brief 的預期
正確。

**(b) 根目錄的 `.mcp.json` 是 AI-DLC 框架自己的 MCP **client** 設定，不是應用的 server。**

```
$ python3 -c "import json;print(list(json.load(open('.mcp.json'))['mcpServers'].keys()))"
['context7', 'aws-mcp', 'aws-pricing', 'aws-iac', 'aws-serverless', 'mermaid']
```

這六個是給 `/aidlc` 會話用的外部工具伺服器。**它必須被明確排除**，否則下一個人看到
`.mcp.json` 就會以為「MCP 已經有了」——這正是 `project.md` 記過的那個形狀（把 RBAC 種子
或權限頁欄名當成已有 router／頁／表）。這裡的風險更高，因為 `MCP` 在本 repo 同時是一個
RBAC 故事標籤（H3）和一個待建機制，而 `.mcp.json` 讓它變成第三種含義。

**(c) 所以 FR11.5 的「可測形式」今天沒有受測對象。** 「對 MCP server 宣告的每一個工具
schema 做斷言」——沒有 server、沒有工具、沒有 schema。**這不是永久不可達**（server 一
落地就可達），但它是**今天不可構造**，而 FR11.5 現在的措辭（「**可測形式**：…」）讀起來
像一條現成的檢查。它會被安靜地延後，而延後不留痕跡。

**它什麼時候變成可寫的**：`FR11.4` 說 MCP server 跑獨立進程。只要該進程以程式碼宣告工具
（任何 MCP SDK 都是如此），工具清單就是一個行程內可取得的物件，`unittest` 可以 import
它並 introspect，**不需要啟動進程、不需要網路**。所以落點是「建立該 server 的同一個單元」，
不是另外一站。AC 必須寫出這件事，否則它會變成一條沒有主體的測試義務。

**(d) 黑名單形式必要但不充分。** 「properties 不含名稱匹配 `token`／`key`／`secret`／
`authorization`」——`auth`、`bearer`、`credential`、`jwt`、`sid`、甚至 `t` 都能過關。
一條不充分的安全斷言的壞處不是漏抓，是**它會被當成已覆蓋的證據**。白名單（properties
必須是宣告好的業務欄位集合的子集）是可判定、完整，且在「新增工具時忘記更新清單」時會
紅燈——後者正是我們要的那種失敗。

**建議的 AC：**

| AC | Given / When / Then |
|---|---|
| **AC11.5.1** | **Given** MCP server 的工具註冊表（與 server 同一個單元交付，可在 `unittest` 內 import、不需啟動進程），**When** 列舉每一個工具的 JSON schema 的 `properties`，**Then** 該集合是該工具**宣告的業務參數白名單**的子集——出現任何未宣告的欄位即失敗 `[FR11.5]` |
| **AC11.5.2** | **Given** 同上，**When** 檢查每一個工具 schema，**Then** 其中不含任何名稱匹配 `token`／`key`／`secret`／`authorization`／`auth`／`bearer`／`credential`／`jwt`（不分大小寫）的欄位 `[FR11.5]` |
| **AC11.5.3** | **Given** MCP server 向既有 API 發出的請求，**When** 檢查該請求，**Then** 使用者 token 位於 `Authorization` **標頭**，且**不出現**在任何工具參數、query string 或 request body 中 `[FR11.5][FR11.6]` |

`AC11.5.1` 是白名單（完整），`AC11.5.2` 保留原本的黑名單並擴充（便宜、額外一層），
`AC11.5.3` 補上 FR11.5／FR11.6 之間漏掉的那一面——**兩條 FR 都只說 token 不得走工具參數，
沒有一條說它該走哪裡**，而「該走哪裡」才是可以斷言的那一半。

---

### V-12（Minor）FR11.3 的 Then 寫成了實作性質，而本 repo 唯一能碰到它的層驗不出那個性質

FR11.3 逐字：「總覽籤的『未填需求欄位』計數，與需求籤的實際未填數**讀同一份狀態**。」

「讀同一份狀態」是實作性質。前端沒有 unit／component 測試框架（本輪複驗
`frontend/package.json`：`devDependencies` 只有 `@playwright/test`，`scripts` 只有
`test:e2e`），唯一能碰到頁面的層是 Playwright e2e，而 e2e **看不到**兩個元件是否共用同一
個 state——一個各自重抓的實作會通過。

FR11.3 的後半句其實已經寫對了（「在需求籤儲存後，總覽籤的計數須同步變化」），那一句是
可觀察的。建議 AC 只寫後半句，並補上「不重新載入頁面」這個限定——沒有它，一個靠整頁重抓
的實作也會通過，而那正是 `project.md` 記過的那條教訓（刪除後重抓會每次閃一次整頁載入）。

| AC | Given / When / Then |
|---|---|
| **AC11.3.1** | **Given** 詳情頁的總覽籤顯示未填需求欄位計數為 N，**When** 我切到需求籤填入一個欄位並儲存、再切回總覽籤（**過程中不重新載入頁面**），**Then** 計數為 N−1 `[FR11.3]` |

---

### V-13（Minor）FR12.6a 的「邀請動作須被拒絕」沒有邀請端點，也沒有說「對應的全域功能權限」是哪一個 story id

FR12.6a 逐字：「缺少對應全域功能權限的使用者不得被邀請加入專案；邀請動作須被拒絕並說明
原因。」兩個缺口：

- **沒有邀請端點**（承 V-09 的 grep：`projects` 相關的 POST／INSERT 為 0）。同 V-09，可以
  接受，但 AC 要寫出它是新建的。
- **「對應的全域功能權限」指哪一個 story id 沒有指名。** 本 repo 的權限檢查是
  `require_story_action("<story_id>", "<action>")`（例如 `user_router.py:638` 是
  `require_story_action("J3a", "edit")`），`user_can(db, role, story, action, ...)` 需要一個
  具體的 story id。FR11／FR12 新增的 story id 是什麼，`requirements.md` 的 OQ-14 還開著
  （我在 V-09 的查證過程中讀到 `stories.md:455` 逐字「具體的 story id 與角色集合見
  `requirements.md` 的 OQ-14」）。**沒有 story id，AC12.6.x 的 deny 案例寫不出來**——
  `team.md` 的 A 規則（allow/deny 雙向）需要指名「哪個角色對哪個 story 的哪個 action」。

**建議**：US12 的 Definition of Done 明寫「本群的 allow/deny 雙向測試以 `OQ-14` 定案的
story id 為前提；`OQ-14` 未定案前本群不得標示完成」。這是誠實的順序依賴，寫出來比讓它在
code-generation 當天才撞上便宜。

---

## 我沒有檢查的（請不要把沉默讀成已覆蓋）

1. **`personas.md` 與 US11／US12 的 persona 對應**——我沒讀 `personas.md`，所以沒有判斷
   新故事該掛 `[P-1]`／`[P-2]`／`[P-3]` 的哪一個，也沒檢查三個 persona 是否涵蓋「專案
   管理者」這個新角色。
2. **US1–US10 既有 20 則故事的 AC 是否因 FR11／FR12／FR13 而需要修改**——我只看了 `US9`
   （當模板）與 `US10.1`（看成本路徑的 AC 形狀）。特別是 **US1 與 US8 的 AC 是否該因
   FR13 而補前置條件**，我沒有逐條核對。FR13 自稱是能力 1 與 8 的實作前置，那意味著
   US1／US8 的某些 AC 在 FR13 修好之前是不可驗的——這一點我沒查。
3. **`traceability.json` 是否需要同步**——完全沒開。新增 US11／US12／US13 必然影響它，
   我不知道它的結構與既有覆蓋宣稱。
4. **rough-mockups 的 §22–§27 與 `[R10]`／`[R12]` 的畫面**——我沒讀任何 mockup 檔。所以
   FR11.1 的空狀態、FR11.2 的分組欄位、FR12.4c 的橫幅文案，我只從 `requirements.md` 的
   轉述判斷，**沒有回畫面逐字核對**。若畫面與 FR 措辭有落差，我抓不到。
5. **`ws-contract.json` 與 WebSocket 契約**——FR11／FR12 的畫面是否經由 WebSocket 取得
   資料，我沒查。若是，`openapi.json` 的漂移閘門對它無效（它不在 42 條 path 內），而
   V-08 的分析只涵蓋 HTTP。
6. **FR13 修好之後 `test_agent.py:41` 會不會壞**——該檔在 `backend/` 根而非
   `backend/tests/`，所以**不被 `python -m unittest discover -s tests` 撿到**（我注意到
   這一點但沒進一步確認它是不是死碼）。它傳 `thread_id=thread_id`，per-key 重構可能影響
   它的簽章假設。
7. **我的 FR13.2 實測有一處保真度邊界，明寫在此**：我 patch 掉了 `build_graph`，所以真正
   的 LangGraph `astream` 事件流與 `ToolNode` 的排程行為沒有被執行。我驗到的是
   `run_design_agent` 本體 ＋ 工具對模組全域的讀寫這一段的真實行為；**真實 LLM 之下的
   交錯時序可能產生我沒看到的第三種終局**。交錯是用 `asyncio.Event` 人工製造的，不是
   自然發生的競態——這證明了缺陷**可達**，不是量化它**多常發生**。
8. **NFR1–NFR11 全部沒看**（除了在讀 FR13 時掠過 NFR2 的 Playwright 計數形狀）。新故事
   是否影響 NFR 的量測母體，我沒判斷。
9. **`schema_rbac.sql` 與 `DEPLOY.md` 的 blocking 同步義務**——我確認了成員表不存在（這
   會觸發該規則），但**沒有檢查 `DEPLOY.md` 目前寫了什麼**，所以沒有判斷同步的工作量。
