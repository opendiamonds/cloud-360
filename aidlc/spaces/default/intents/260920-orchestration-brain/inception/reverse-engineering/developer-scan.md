# Developer Scan — reverse-engineering link 1

> 本檔為 reverse-engineering pipeline 的 link 1（developer）掃描結果。
> **link 2（architect）據此寫 9 份 codekb artifact**；本檔本身不是 codekb。
> 本輪完全重寫，取代 2026-09-24 的同名檔。

## 掃描元資料

| 欄位 | 值 |
|---|---|
| 執行時刻（UTC） | `2026-10-01T23:14:53Z`（`date -u`，**實跑**） |
| Worktree | `/Users/jiangzhengdao/orca/workspaces/cloud-360/chiton` |
| 分支 | `danniel/docs/orchestration-brain-ideation` |
| HEAD | `34aeef38350b0f2865b025446528bd32143804bf`（short `34aeef3`，**實跑** `git rev-parse HEAD`） |
| Intent | `260920-orchestration-brain` |
| 模式 | Focused merge；**canonical store 改為 `codekb/cloud/`** |
| 深度 | 三項優先項為 deep（逐行讀＋行號複驗）；其餘為 medium／shallow，逐節標明 |

### 證據標記（全檔通用，逐條必附）

| 標記 | 意義 |
|---|---|
| `[讀]` | 本輪實際開檔讀內容，行號為本輪複驗值 |
| `[算]` | 本輪只做 grep／計數／解析，未讀全文 |
| `[跑]` | 本輪實際執行指令，附輸出 |
| `[承:cloud-360@2026-09-24]` | 沿用 `codekb/cloud-360/` 的既有記載，**本輪未複驗** |
| `[承:cloud@2026-10-01]` | 沿用 `codekb/cloud/` 的既有記載，**本輪未複驗** |
| `[未掃]` | 本輪完全沒碰 |

---

## 0. 給 link 2 的最重要訊息：兩個 store 都漏了一整塊

`codekb/cloud/`（canonical）的 `analyzed.paths` 共 22 條，**完全不含** `brain_router.py`、
`brain_ws_contract.py`、`hierarchy_migration.py`、`BrainPage.tsx`、`ws-contract.json`。
`codekb/cloud-360/` 同樣不含（它的掃描 commit `dc4b687` 早於這些檔落地）。

**但這三塊在 HEAD 上是真實存在的程式**，而且其中一塊（brain）正好是本 intent 的題目本身。
詳見 §4。這不是本輪三項優先項之一，但它的嚴重性不低於那三項——**本 intent 的正式單元
`U11`／`U13`／`U14` 還沒開始，而 repo 裡已經有一支自稱 demo-scope 的大腦 WS gateway 在跑**，
下游若不知道它存在，會把它當成「要從零開始」或反過來當成「已經做完了」。

---

## 1. 優先項一：MCP — repo 內零 MCP 基礎設施（**已查證**）

### 查證結果

`[跑]` `grep -rni "mcp" backend/ --include='*.py'`（排除 `__pycache__`）→ **命中數 1**：

```
backend/services/user_router.py:85:    "H3": "MCP／Skill 生命週期",
```

`[讀]` 讀該行上下文（`backend/services/user_router.py:80–92`），它落在一個
`story_id → 中文顯示名` 的字典裡，鄰居是 `"G1": "CSPM 持續合規"`、`"H1": "內部 API 註冊"`、
`"H2": "Agent 存取邊界"`、`"J3a": "使用者設定"`。緊接其後是
`CATALOG_EXCLUDED_STORIES = frozenset({"J1"})`。

**判定**：這是 **RBAC 權限矩陣的 story 標籤**（權限頁上那一欄的顯示名），不是任何實作。
`H3` 是一個 story id，和 `G1`／`H1`／`J3a` 同級。

### 其他查證點

| 查證 | 方法 | 結果 |
|---|---|---|
| `backend/requirements.txt` 有無 MCP 套件 | `[讀]` 全檔逐行＋`[跑]` `grep -in "mcp\|model.context"` | **零命中**。宣告的 18 項裡沒有任何 MCP 相關套件 |
| 有無 MCP server／client 程式 | `[算]` 全 `backend/` grep | 零。沒有 `mcp` 檔名、模組、類別 |

### 現行的「agent 對 LLM 暴露工具」機制是什麼

`[讀]` `backend/services/design_agent.py`，本輪複驗行號：

| 行 | 內容 |
|---|---|
| `:9–12` | `from langgraph.graph import StateGraph, START, END` / `add_messages` / `MemorySaver` / `from langgraph.prebuilt import ToolNode` |
| `:15` | `from langchain_core.tools import tool` |
| `:64` | `@tool` 裝飾器（`draw_architecture_diagram`） |
| `:111` | `tool_node = ToolNode(tools)` |

**即：LangChain `@tool` ＋ LangGraph `ToolNode`，同進程、同一個 Python 物件圖，
沒有任何跨進程協定。**

### 為什麼這件事要寫準

上游 `[F16]=B`（取代 `[S13]=A`）要求**真的導入 MCP server ＋ client，跑獨立進程**。
本 repo 的起點是：

1. **零 MCP 套件**——`requirements.txt` 要新增依賴，而本 repo 除 `fastapi`／`pydantic`
   兩支外全無 pin、無 lockfile（§8），新增依賴即新增一條各環境解析結果可能不同的邊。
2. **零跨進程 agent 通道**——現有唯一的工具暴露法是同進程 `ToolNode`；獨立進程是全新形狀。
3. **`MCP` 這個字在本 repo 已被佔用**，語意是 RBAC story `H3`。
   **link 2 必須在 codekb 寫明這個雙重語意**，否則下一個人 grep `MCP` 命中 `user_router.py:85`
   就會得到「已經有了」的反向結論。這正是 `project.md` 已記過的那條教訓
   （grep 命中名稱不等於該能力存在）的同型陷阱。

**兩個 store 的現況**：`cloud/` 與 `cloud-360/` 皆**未記載** MCP 現況（無論正確或錯誤）。
這是**新增**內容，不是修正。

---

## 2. 優先項二：`design_agent.py` 的模組級全域狀態 — 併發不安全（**已查證，行號全數複驗**）

### 2.1 狀態的生命週期（逐行複驗）

`[跑]` `grep -n "_progress_queue" backend/services/design_agent.py` → 13 處命中。
`[讀]` 逐段開檔確認語意：

| 行 | 程式 | 角色 |
|---|---|---|
| `:31` | `_progress_queue: asyncio.Queue[dict[str, str]] \| None = None` | **模組層宣告**（檔案最外層，非函式內） |
| `:32` | `_last_xml: str \| None = None` | **第二個同型全域**（見 §2.5） |
| `:176` | `global _progress_queue, _last_xml` | `run_design_agent` 宣告改寫全域 |
| `:183` | `_progress_queue = asyncio.Queue()` | **每個請求重新指派同一個模組全域** |
| `:184` | `_last_xml = None` | 同上 |
| `:203` | `async for q_event in _drain_progress(_progress_queue):` | 串流迴圈內讀取（**讀的是當下的模組全域**） |
| `:211` | `async for q_event in _drain_progress(_progress_queue):` | 收尾 drain，同樣讀當下的模組全域 |
| `:218` | `_progress_queue = None`（在 `finally:` 內） | **先結束者把它設回 `None`** |

工具端（`draw_architecture_diagram`，`@tool` at `:64`）的寫入點：

| 行 | 程式 |
|---|---|
| `:81–82` | `if _progress_queue is not None:` / `await _progress_queue.put({"type": "progress", ...})`（`on_progress` callback 內） |
| `:84–85` | `if _progress_queue is not None:` / `await _progress_queue.put({"type": "progress", "content": "🧠 正在規劃進階架構拓樸..."})` |
| `:96–97` | `if _progress_queue is not None:` / `await _progress_queue.put({"type": "xml", "content": xml_data})` |
| `:101–102` | `if _progress_queue is not None:` / `await _progress_queue.put({"type": "error", "content": "產圖發生錯誤"})` |

**關鍵**：工具函式（`:78–104`）**沒有**宣告 `global _progress_queue`，也**沒有**把 queue 當參數傳入——
它每次都解析**當下的模組全域**。入口的 `:203`／`:211` 同理（`:176` 的 `global` 讓那個名字綁到模組全域，
不是區域快照）。**兩端都讀「最後一個被建立的 queue」。**

### 2.2 併發危害（兩種，都是靜默的）

設 A、B 兩個請求重疊，B 晚於 A 進入 `:183`：

**危害一 — 跨使用者內容錯送。** B 的 `:183` 覆寫全域後，A 的工具執行到 `:97` 會
`put` 到 **B 的 queue**；而 A 的串流迴圈 `:203` 也讀 **B 的 queue**。
實際後果是 **A 的架構圖 XML 送進 B 的 SSE 串流**（或反之，取決於誰的工具先完成）。
這不是「看不到進度」，是**使用者 A 收到使用者 B 產生的架構圖 XML**。

**危害二 — 事件靜默丟棄。** 誰先走到 `:218` 的 `finally`，就把全域設成 `None`。
之後另一個請求的工具寫入全部撞上 `:81`／`:84`／`:96`／`:101` 的 `if ... is not None:` 守衛，
**條件為假 → 整個 `put` 被跳過 → 沒有例外、沒有 log、沒有任何痕跡**。
`progress`／`xml`／`error` 三類事件一律消失。注意 `error` 也在內：連「出錯了」這件事都送不出去。

### 2.3 兩個生產呼叫點，都可達

`[跑]` `grep -rn "run_design_agent" backend/`：

| 呼叫點 | 行 | 形狀 | `thread_id` |
|---|---|---|---|
| `backend/services/agent_router.py` | `:125` | `async for event in run_design_agent(payload, request.current_xml, thread_id=f"user-{current_user.id}-design")` ——**每個 HTTP 請求一次**，包在 `StreamingResponse`（`:129`，`media_type="text/event-stream"`） | per-user |
| `backend/services/wa_collab_orchestrator.py` | `:79` | `async for event in run_design_agent(messages, current_xml)` ——**未傳 `thread_id`** | 落回預設值 |
| `backend/test_agent.py` | `:41` | 手動 smoke 腳本，非生產路徑 | — |

`[讀]` `backend/services/design_agent.py:171–175`，簽章為
`async def run_design_agent(messages, current_xml=None, thread_id: str = "default-thread")`。
**故 `wa_collab_orchestrator.py:79` 走 `"default-thread"`**——這是個額外發現：A4 共編路徑的
所有使用者共用同一個 checkpointer thread。

### 2.4 `thread_id` 不是解法

`agent_router.py:125` 的 `thread_id=f"user-{current_user.id}-design"` **確實是 per-user**，但
`[讀]` `:198` 顯示它只進到 `config = {"configurable": {"thread_id": thread_id}}`，
再傳給 `graph.astream(...)`（`:201`）——**它餵的是 LangGraph checkpointer（`MemorySaver`，`:169`）**，
與 `_progress_queue` 毫無關係。把 `thread_id` 做對不會修掉這個缺陷。
（而且就算它有用，`wa_collab_orchestrator.py:79` 根本沒傳。）

### 2.5 附帶：`_last_xml` 是同一個形狀的第二個全域

`[讀]` `:32` 宣告、`:78` `global _last_xml`、`:95` `_last_xml = xml_data`、`:184` 重設為 `None`。
同樣是模組層單槽，同樣被兩個重疊請求共用。本輪未實測它的外部可觀察後果
（需找出讀取端），但**結構與 `_progress_queue` 完全同型**，link 2 應一併記載。

### 2.6 **repo 內已有正確作法**（這是最有用的一半）

`[讀]` `backend/cost/advice_orchestrator.py:1–82`：

| 行 | 程式 |
|---|---|
| `:7` | `import threading` |
| `:22` | `_executor_lock = threading.Lock()` |
| `:23` | `_progress: dict[int, dict[str, Any]] = {}` ← **以 `set_id` 為鍵的字典，不是單槽** |
| `:24` | `_progress_lock = threading.Lock()` |
| `:26` | `_inflight: set[int] = set()` |
| `:61–72` | `def set_progress(set_id, **fields)` → `with _progress_lock:` 內讀改寫 |
| `:75–77` | `def get_progress(set_id)` → `with _progress_lock: return dict(_progress.get(set_id, {}))`（**回傳副本**） |
| `:80–82` | `def clear_progress(set_id)` → `with _progress_lock: _progress.pop(set_id, None)` |

**即：per-job 鍵、鎖保護、三個封裝好的存取函式（寫／讀／清），且讀取回傳副本。**
`_progress` 在整個檔內只被那三個函式碰到（`[算]` `grep -n "_progress"` 的 14 處命中裡，
除宣告與三個函式本體外，其餘 9 處都是 `set_progress(...)` 呼叫）。

**給 link 2**：記載時要把「缺陷」與「同 repo 內的正解」寫在一起。修法不需要發明——
把 `design_agent.py` 的單槽換成 `dict[<per-request key>, asyncio.Queue]` ＋ 鎖＋三個存取函式，
形狀已經在 `advice_orchestrator.py` 跑著。（注意 `advice_orchestrator` 用 `threading.Lock`
因為它走 `ThreadPoolExecutor`；`design_agent` 是純 async，對應的是 `asyncio.Lock` 或
在單一 event loop 下免鎖的 dict——這個取捨留給設計站，不在 codekb 預選。）

### 2.7 兩個 store 的現況

- `cloud/`（canonical）：`design_agent.py` 在其 `analyzed.paths` 內（deep），但本輪未見其記載此缺陷。
  **link 2 應把 §2 整段寫進 `cloud/`。**
- `cloud-360/`：其 `code-quality-assessment.md` 有一條 `T-3 單行程假設散佈在三處狀態容器` `[承:cloud-360@2026-09-24]`。
  **這條是相關的，但不等於本缺陷**——「單行程假設」講的是水平擴充時會壞；
  本缺陷在**單一行程內**、兩個並行請求就會壞。link 2 應保留 T-3 並**另立**本項，不要合併。

---

## 3. 優先項三：`llm_provider.py` 本 session 重寫（**已查證**）

### 3.1 檔案現況

`[跑]` `wc -l backend/services/llm_provider.py` → **178 行**（brief 稱 237 → 178，與現況一致）。
`[讀]` 全檔 178 行逐行。

### 3.2 `LLM_PROVIDER=cli` 已退役

`[讀]` 逐行複驗：

| 行 | 事實 |
|---|---|
| `:42–43` | `OPENROUTER = "openrouter"` / `_VALID_PROVIDERS = (OPENROUTER,)` ← **有效值只剩一個** |
| `:45–47` | 註解「Recognised, but no longer selectable」/ `_RETIRED_PROVIDERS = ("cli",)` |
| `:65` | `raw = os.environ.get("LLM_PROVIDER", "").strip().lower()` |
| `:66–67` | 空值 → `return OPENROUTER` |
| `:68–78` | `if raw in _RETIRED_PROVIDERS:` → `logger.error(...)` 後 `return OPENROUTER`。**ERROR 級，不 raise** |
| `:79–86` | 不在有效值內（打錯字）→ `logger.warning(...)` 後 `return OPENROUTER`。**WARNING 級** |

即：**退役值記 ERROR、打錯字記 WARNING、兩者都不擋啟動**，而且退役與打錯字在 log 上可區分
（這是刻意的：`:60–63` 的 docstring 寫明「A retired value logs at ERROR and a typo logs at
WARNING; neither raises」）。

`[讀]` `:69–77` 的 ERROR 訊息逐字（繁中）點名了原因：
「A3 遷移到 LangGraph／OpenRouter 之後已無 claude CLI 子行程可認證，而該模式會刪除
ANTHROPIC_AUTH_TOKEN／ANTHROPIC_BASE_URL——留著它會讓金鑰被清空而健康檢查仍回報正常（RAID R-11）」。

### 3.3 它修掉的是什麼（失敗機制，逐步查證）

`[讀]` `:1–33` 的模組 docstring 記載了完整因果，本輪**逐項獨立複驗**：

| 環節 | 查證 | 結果 |
|---|---|---|
| 舊 cli 模式會刪四個變數 | `[讀]` `:10–14` 的 docstring 自述（舊程式已不在檔內，無法直接讀） | 僅文件自述；**標為 `[讀]` 文件、非 `[讀]` 程式** |
| 遷移後無子行程 | `[跑]` `grep -rn "create_subprocess_exec\|Popen\|subprocess" backend/ --include='*.py'`（排除 `__pycache__`、`tests/`） | **零個實際呼叫**。命中 5 處全是字串／註解：`llm_provider.py:5,9,17,18`（docstring 自己在講這件事）、`llm_limits.py:52`（docstring 內的 "CLI subprocesses" 字樣）。**查證成立** |
| `design_agent.py` 直接讀那些變數 | `[讀]` `backend/services/design_agent.py:118–119` | 逐字為 `api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("OPENROUTER_API_KEY") or ""` 與 `base_url = os.environ.get("ANTHROPIC_BASE_URL")`。**查證成立，行號 `:118` 正確** |
| `llm_auth_ready()` 會說謊 | `[讀]` `:120–130` | `return bool(os.environ.get("OPENROUTER_API_KEY","").strip() or os.environ.get("ANTHROPIC_AUTH_TOKEN","").strip())`。cli 模式刪掉這兩個 → 現在會回 `False`；舊版本的「仍回 True」無法在現碼複驗，標為文件自述 |
| 空金鑰如何表現 | `[讀]` `design_agent.py:118` 的 `or ""` 兜底 | 金鑰為空字串仍把 `ChatAnthropic` 建起來（`:121`），失敗落在呼叫時。**機制成立** |

**結論**：失敗模式是「健康檢查說 ready，呼叫時才空金鑰」，即**靜默失敗**，記為 RAID R-11。

### 3.4 `.env.example` 的預設值已改

`[跑]` `grep -n "LLM_PROVIDER\|OPENROUTER" backend/.env.example`：

```
18:#   `LLM_PROVIDER=cli` 已退役（本檔原本的預設值就是它，所以照本檔複製出的
23:LLM_PROVIDER=openrouter
29:OPENROUTER_API_KEY=
```

**`:23` 現為 `openrouter`**；`:18` 的註解逐字承認**本檔原本的預設值就是 `cli`**——
所以凡照範本複製 `.env` 的人都會撞上。這一點對 `LOCAL-DEV.md` 的隱性前置條件有直接影響
（`project.md` 有 blocking 規則要求 `.env.example` 異動時同步 `LOCAL-DEV.md`；
**本輪未查證 `LOCAL-DEV.md` 是否已同步**，標為 `[未掃]`，link 2 可列為待查）。

### 3.5 `test_llm_provider.py` 已重寫

`[跑]` `wc -l` → **222 行**；`[跑]` `grep -c "def test"` → **23 個**（與 brief 一致）。
`[算]` 六個 `unittest.TestCase` 類別：

| 行 | 類別 | 測試數 |
|---|---|---|
| `:72` | `ProviderSelection` | 3 |
| `:88` | `RetiredCliMode` ← **新類別** | 5 |
| `:137` | `OpenRouterEnv` | 4 |
| `:165` | `AuthReadiness` | 4 |
| `:187` | `ModelNames` | 7 |

`RetiredCliMode` 的五個測試名稱（`[算]`，逐行讀標題列）：
`test_resolves_to_openrouter`（`:91`）、`test_logs_at_error_not_as_a_typo`（`:95`）、
`test_no_longer_deletes_credentials`（`:105`）、`test_auth_ready_no_longer_lies`（`:122`）、
`test_alias_model_family_survives`（`:129`）。
**這組測試名稱本身就是這次修正的規格**，link 2 值得逐字引用。

### 3.6 PostgreSQL 驅動已換 psycopg v3

`[讀]` `backend/requirements.txt`：`psycopg[binary]`（**無 pin**），且檔內 `:14–22` 有一段
繁中註解說明「`psycopg` 與 `psycopg2-binary` 是兩個不同的套件」、
「SQLAlchemy 2.1 把隱含預設由 psycopg2 改為 psycopg(v3)」、
「顯式指定 driver 之後**不設版本上限**」。
`[算]` `grep -n "psycopg2" backend/requirements.txt` → **零**。

`[跑]` `grep -n "postgresql" backend/database.py`：

| 行 | 內容 |
|---|---|
| `:23` | 預設值 `"postgresql+psycopg://postgres:postgres@localhost:5432/cloud360"` |
| `:26–31` | 註解：裸 `postgresql://` 的相容改寫引入於 `ut` 的 `4194cd2`；**目標驅動由 psycopg2 改為 psycopg v3** |
| `:34–35` | `if db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"): db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)` |

`[讀]` `requirements.txt`：`sqlalchemy`（**無 pin，且刻意不設上限**；註解說明曾以
`sqlalchemy<2.1` 止血，已改為顯式指定 driver）。

**對 `team.md` 的影響**：`team.md` 的 Testing Posture 記載
「在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`」——
`psycopg2` 已不在相依裡，**這段記載可能已過時**。
`[算]` `backend/tests/helpers.py` 在本輪的 `git diff --name-only 5fd8f14 HEAD` 清單內（確實被改過），
但**本輪未讀其內容**，標為 `[未掃]`。link 2 應列為待查而非逕自改寫。

---

## 4. 本輪新發現：兩個 store 都沒有的三塊程式

`[跑]` `git log --oneline -1 -- <path>` 取得各檔的最後一次 commit：

| 檔 | LOC `[算]` | 落地 commit | 日期 |
|---|---|---|---|
| `backend/services/brain_router.py` | 455 | `f9c5bda` 功能(brain): demo-scope 的大腦垂直切片，供今晚展示用 | 2026-09-28 |
| `backend/services/brain_ws_contract.py` | 783 | `c619c3f` 功能(brain-ws-contract): WS 訊息型別契約與兩道 CI 型別閘門 | 2026-09-28 |
| `backend/services/hierarchy_migration.py` | 496 | `9e14145` 功能(hierarchy-data): projects／systems／diagram_change_records 三表與一次性遷移 | 2026-09-28 |
| `ws-contract.json` | 24252 bytes | `c619c3f` | 2026-09-28 |
| `frontend/src/types/ws-contract.d.ts` | — | `c619c3f` | 2026-09-28 |
| `frontend/src/pages/BrainPage.tsx` | 403 | （在 `5fd8f14..HEAD` 的變更清單內） | — |

### 4.1 大腦 WS gateway 是 **demo scope**，而且它自己說得很清楚

`[讀]` `backend/services/brain_router.py:1–31` 的模組 docstring。它逐字自述
「**DEMO SCOPE，非 U13 的正式交付**」「為了**今晚的成果展示**而寫的最小垂直切片，
**不屬於任何已核可的 AI-DLC 工作單元**」，並明列：

**刻意實作的**（來源為 `brain-ws-contract` 已完成的 functional-design）：
- 訊息封包 `{v, type, turnId, payload}`，`v` 字面值 1
- 握手：token 走 `Sec-WebSocket-Protocol`（**不是** query string）、`record=True`
- 版本協商：`hello {v}` → `ready {protocolVersion}`，不符以 **4400** 關閉並帶 expected／received
- 九種伺服器訊息裡的 `ready`／`token`／`clarify`／`work_items`／`done`／`error`
- 六種客戶端訊息裡的 `hello`／`user_message`／`select_clarify_candidate`／`set_work_target`
- 終止語意：零內容不得以 `done` 結束，一律走 `error(EMPTY_RESPONSE)`
- `error.code` 的封閉四值

**刻意沒實作的**（docstring 逐字，附它指派的正式單元）：
- Redis session 持久化 → `U10 session-store`（**本檔用行程內 dict，重啟即失憶**；沿用 `K-12` 的「單一後端行程」假設）
- 真正的意圖路由與信心值模型 → `U11`（**本檔用關鍵詞計分**，見 `_classify`）
- 專案／系統／架構圖三層階層 → `U7 hierarchy-service`
- 三層記憶 → `U5`／`U8`／`U9`
- `cost_card`／`sharing_mode` 兩種訊息、多連線扇出、`correct_work_item`
- `ws-contract.json` 與型別檔的兩道 CI 漂移閘門 → `U2` 的 code-generation

**替代方式**（docstring 逐字）：「`U13` 落地時**整支取代本檔**（而不是逐段改寫）。
本檔不被任何既有模組 import，移除它只需刪檔並移除 `main.py` 的一行 `include_router`。」

`[讀]` `backend/main.py:61–63` 證實該自述：
```
# DEMO SCOPE：大腦 gateway 的最小垂直切片，非 U13 的正式交付。
# 移除方式：刪 backend/services/brain_router.py 並移除下面兩行。
app.include_router(brain_router, prefix="/api/brain")
```
（註解說「下面兩行」但實際只有一行 `include_router`；`main.py:7` 的 import 是第二處。
**這是個小矛盾，但不影響可移除性。**）

`[算]` `grep -n "@router.websocket\|router = APIRouter\|def " brain_router.py` 的函式骨架：
`:51` `router = APIRouter()`、`:87` `_session_for(user_id)`、`:116` `_classify(text)`、
`:148` `_llm_available()`、`:152` `_respond(capability, text)`、`:169` `_respond_via_llm(...)`、
`:200` `_respond_locally(...)`、`:210` `_envelope(...)`、`:226` `_send(...)`、
`:230` `_send_error(...)`、**`:238` `@router.websocket("/ws")` → `:239` `async def brain_ws(websocket)`**、
`:411` `_run_turn(...)`。

**給 link 2 —— 這塊的記載必須同時傳三件事**，少任一件都會誤導：
1. 它**存在且掛在 `/api/brain/ws`**（不是待建）；
2. 它**不是 `U13`**，`U11`／`U13`／`U14` 仍未開始；
3. 它的**正式交付方式是整支取代**，所以不要把它的 `_classify` 關鍵詞計分
   當成「信心值模型已有雛形」——那正是 `OQ-10` 在質疑的東西。

### 4.2 WebSocket 不再只有一條

`[跑]` `grep -rn '@router.websocket' backend/`：

| 檔 | 行 | 路徑（含 prefix） |
|---|---|---|
| `backend/services/collab_router.py` | `:266` | `/api/collab/ws/{workspace_id}` |
| `backend/services/brain_router.py` | `:238` | `/api/brain/ws` |

**`codekb/cloud-360/architecture.md` 有一節標題為「交易三：A4 共編的 WebSocket 握手
（既有唯一 WS 前例）」`[承:cloud-360@2026-09-24]`——「唯一」在 HEAD 上已不成立。**
link 2 若從 `cloud-360/` 搬這一節，**必須改掉「唯一」這個字**。

### 4.3 階層三表已在 `schema_rbac.sql`，但**不在 ORM models**

`[跑]` `grep -n "CREATE TABLE" schema_rbac.sql`（篩 project／system／diagram_change）：

| 行 | 表 |
|---|---|
| `:327` | `CREATE TABLE IF NOT EXISTS projects (` |
| `:349` | `CREATE TABLE IF NOT EXISTS systems (` |
| `:393` | `CREATE TABLE IF NOT EXISTS diagram_change_records (` |

`[算]` `grep -n "__tablename__" backend/models.py` → 12 個表，**`projects`／`systems`／
`diagram_change_records` 皆不在內**（清單：`users`、`role_authorization_requests`、
`user_diagrams`、`user_diagram_chats`、`architecture_reviews`、`wa_lenses`、`role_permissions`、
`estimate_sets`、`estimates`、`estimate_line_items`、`estimate_shares`、`estimate_audit_events`、`advice`
——實為 13）。

`[算]` `grep -n "CREATE TABLE\|def " backend/services/hierarchy_migration.py` 的骨架：
`:204` `migrate_hierarchy(db) -> MigrationCounts`、`:269` `_ensure_hierarchy_schema(db)`、
`:361` `_users_holding_diagrams(db)`、`:380` `_resolve_default_pair(...)`、
`:458` `_assign_unassigned_diagrams(db, user_id, system_id)`、`:477` `_assert_no_unassigned_diagrams(db)`。
另有 `backend/scripts/run_hierarchy_migration.py`（`[算]` 3597 bytes）。

`[跑]` `grep -rln "system_id" backend/ --include='*.py'` → 僅 4 檔：
`tests/test_hierarchy_migration.py`、`services/hierarchy_migration.py`、
`scripts/run_hierarchy_migration.py`、`services/brain_router.py`。
**即：階層的 schema 與一次性遷移已落地，但應用程式碼（router／service／ORM）尚未消費它**
——除 `brain_router.py` 那支 demo 之外。

**這直接推翻一條上游前提。** `project.md` 記載 intent-capture 當時查到
「`schema_rbac.sql` 只有 users→user_diagrams，backend 全樹 `system_id` 命中 0 次」。
那在當時為真，**在 HEAD 上已不為真**。link 2 必須寫明這個轉變與它的確切邊界
（schema ＋ migration 有了；ORM model、router、service 還沒有），
否則下游會在兩個方向各錯一次。

`[跑]` 本輪 `python3 -m unittest discover -s tests` 的輸出尾段實際印出：
```
hierarchy migration 完成：
  處理的使用者數        users_processed       = 1
  新建的預設專案／系統組 default_pairs_created = 1
  改寫的架構圖數        diagrams_assigned     = 1
終檢通過：user_diagrams 中 system_id IS NULL 的列數為 0（AC9.1.4）。
```
**遷移有測試覆蓋且本輪跑綠**，並且它斷言的是一條編號 AC（`AC9.1.4`）。

---

## 5. Business overview

`[承:cloud-360@2026-09-24]` ＋ `[算]` 本輪由路由與 router 清單交叉確認。

Cloud-360 是 AI-native 多雲（AWS／GCP／Azure）架構與維運平台。使用者可見的功能主線
（`[讀]` `frontend/src/App.tsx` 的路由表，本輪複驗行號）：

| 路由 | 頁面 | 功能 |
|---|---|---|
| `/login`（`:36`） | `LoginPage.tsx` | 登入 |
| `/403`（`:37`） | `ForbiddenPage.tsx` | 無權限 |
| `/waiting-approval`（`:39`） | `WaitingApprovalPage.tsx` | 待核准 |
| `/workspace`（`:48`） | `WorkspacePage.tsx` | **A1 對話產圖**（draw.io 畫布＋聊天） |
| `/assessment`（`:61`） | `AssessmentPage.tsx` | **A3 架構評核**（Well-Architected） |
| `/cost`（`:74`） | `CostPage.tsx` | **C1 估價與成本建議** |
| `/brain`（`:88`） | `BrainPage.tsx` | **大腦入口（demo scope，見 §4.1）** |
| `/admin/users`（`:99`） | `AdminPage.tsx` | 帳號管理 |
| `/admin/authorization-requests`（`:112`） | `AuthorizationRequestsPage.tsx` | 授權申請 |
| `/admin/role-permissions`（`:125`） | `RolePermissionsPage.tsx` | 權限矩陣 |
| `/admin`（`:137`） | → redirect `/admin/users` | |
| `/`（`:139`） | | 首頁 |
| `*`（`:147`） | | catch-all |

**`/brain` 路由在 `cloud/` 與 `cloud-360/` 兩個 store 都沒有記載**（`cloud/` 的 `App.tsx`
雖在 deep 集合內，但掃描 commit `5fd8f14` 早於 BrainPage 的落地）。

既有規格文件（`[未掃]` 本輪未開檔）：SRS、user stories、architecture、ADRs，
位於各 intent record 下。`cloud-360/business-overview.md` 有完整的業務主線敘述
（主線一～五 ＋ 業務邊界 ＋ 詞彙表），**本輪未複驗其內容，但結構完整，建議 link 2 整段沿用
並補上 `/brain` 這一條**。

---

## 6. Architecture

### 6.1 App shell

`[讀]` `backend/main.py` 全 67 行。本輪複驗的 `include_router` 表：

| 行 | router | prefix |
|---|---|---|
| `:54` | `agent_router` | `/api/architecture` |
| `:55` | `review_router` | `/api/architecture` |
| `:56` | `lens_router` | `/api/architecture` |
| `:57` | `user_router` | `/api/auth` |
| `:58` | `collab_router` | `/api/collab` |
| `:59` | `estimate_intake_router` | `/api/cost/v1` |
| `:60` | `advice_stream_router` | `/api/cost/v1` |
| `:63` | `brain_router` | `/api/brain`（**demo scope**） |

**`codekb/cloud-360/api-documentation.md` 引用的是 `backend/main.py:52–58`
`[承:cloud-360@2026-09-24]`——在 HEAD 上該範圍是 `:54–63`，且少記了 `brain_router`。
link 2 必須更新這個行號與表格。**

其他 shell 事實（`[讀]`）：
- `:3` `from env_bootstrap import BACKEND_DIR, load_backend_dotenv`；`:25` `load_backend_dotenv(override=True)`
  ——`.env` **只從 `backend/.env` 載入**，不看行程啟動目錄（`:21–24` 註解說明這防的是什麼）
- `:29` 模組層呼叫 `configure_provider_env()`；`:48–52` `@app.on_event("startup")` 內**再呼叫一次**
  ＋ `init_db()`。`:27–28` 註解說明第二次呼叫的目的是讓退役的 `LLM_PROVIDER=cli` 在啟動時就記一行 ERROR
- `:35–45` CORS 由 `CORS_ORIGINS` 環境變數注入（預設 `http://localhost:5173,http://127.0.0.1:5173`）
- `:31` `app = FastAPI(title="Cloud-360 API")`
- `:65–67` `GET /` 回 `{"message": "Cloud-360 Backend is running"}`

### 6.2 後端分層依模組家族而異（既成事實，非待修違規）

`[承:cloud-360@2026-09-24]`，本輪以 LOC 與檔名 `[算]` 交叉確認其仍成立：

**三層清楚的家族** `review`／`lens`／`wa_*`：router → orchestrator/service → 純函式引擎 → model。
純函式引擎層不讀 DB、不連外，是 property-based 測試的實際落點：
`wa_rule_engine.py`（973 LOC）、`wa_lens_engine.py`（631）、`diagram_builder.py`（2080）。

**router 直寫商業邏輯的家族** `user`／`collab`：無 service 層。
`user_router.py` **892 LOC**（`[算]` `wc -l`；`cloud-360` store 與 `team.md` 記 831，**已增長**）、
`collab_router.py` **593 LOC**（`team.md` 記 527，**已增長**）。

**`backend/cost/` 的三層 ＋ 純函式邊界有 CI 強制**（見 §6.3）。

### 6.3 Cost 域（`backend/cost/`，21 支 `.py`，4266 LOC `[算]`）

`[算]` `wc -l backend/cost/*.py` 排序：

| 檔 | LOC | 角色（由檔名與 §6.3 的邊界檢查推斷） |
|---|---|---|
| `estimate_intake_service.py` | 686 | 估價上傳業務協調（可讀 DB） |
| `estimate_readers.py` | 384 | 估價表讀取（**純函式層**，CI 強制無 I/O） |
| `advice_orchestrator.py` | 358 | 建議 job 編排（**§2.6 的正解來源**） |
| `estimate_parser.py` | 322 | 估價表解析（**純函式層**，CI 強制） |
| `pricing_client.py` | 287 | 公開／目錄價 Port |
| `sku_catalog.py` | 265 | SKU 對照（**`:18` `import httpx`** ——它不在純函式層的三支之內，見下） |
| `cost_advice_agent.py` | 240 | LangGraph 建議 agent |
| `pricing_gcp.py` | 236 | GCP 計價 |
| `estimate_intake_router.py` | 235 | HTTP 入口（prefix `/api/cost/v1`） |
| `pricing_azure.py` | 219 | Azure Retail Prices |
| `pricing_sdk.py` | 203 | AWS Price List Query（boto3；ADR-0018 由「確定刪除」改為保留） |
| `advice_stream_router.py` | 179 | 建議 SSE（`:173` `media_type="text/event-stream"`） |
| `estimate_validator.py` | 122 | 估價驗證（**純函式層**，CI 強制） |
| `pricing_query_parser.py` | 120 | 查價參數解析 |
| `workload_context.py` | 106 | 工作負載情境 |
| `pricing_offer_parser.py` | 83 | offer 解析 |
| `estimate_audit.py` | 74 | 稽核事件 |
| `estimate_access.py` | 58 | 存取控制 |
| `pricing_units.py` | 47 | 單位換算 |
| `config.py` | 41 | 設定 |
| `__init__.py` | 1 | |

**兩道 import 邊界由 CI 強制，本輪實跑皆通過**：

`[跑]` `python3 scripts/validate_cost_calculator_boundary.py`（exit 0）：
```
OK: backend/cost/estimate_parser.py has no forbidden I/O imports
OK: backend/cost/estimate_readers.py has no forbidden I/O imports
OK: backend/cost/estimate_validator.py has no forbidden I/O imports
```
→ **純函式層的實際範圍是這三支**（`ADR-0017 §1–§2` 把 PBT hard constraint 由
`cost_calculator` 移錨到估價表解析器，這三支就是那個落點）。
`sku_catalog.py:18` 的 `import httpx` **不違反**，因為它不在這三支之內。

`[跑]` `python3 scripts/validate_pricing_lookup_boundary.py`（exit 0）：
```
OK: pricing-lookup boundary (intake=4 modules; survival=9)
```

兩支都在 CI 的 `repo-contract` job 內（`[讀]` `.github/workflows/ci.yml:161–167`）。

### 6.4 SSE 與 WebSocket 總覽

`[跑]` `grep -rn 'text/event-stream' backend/`（排除 tests）→ **5 個實際 SSE 端點**：

| 檔 | 行 |
|---|---|
| `backend/services/agent_router.py` | `:97`、`:129`、`:186`（三個） |
| `backend/services/review_router.py` | `:73` |
| `backend/cost/advice_stream_router.py` | `:173` |

（`agent_router.py:13` 另有一處是 docstring 內的契約說明，非端點。）

WebSocket：2 個，見 §4.2。

### 6.5 LLM 棧已全數收斂到 LangGraph ＋ OpenRouter（**這修正 `cloud/` store 的一項主張**）

`[跑]` `grep -rn "claude_agent_sdk\|claude-agent-sdk" backend/` → **零個實際 import**。
命中 5 處全是字串：
- `backend/tests/test_a3_langgraph_migration.py:7`（規格註解 `@step ... assert sources lack claude_agent_sdk`）、
  `:33`、`:40`（**兩個 `self.assertNotIn("claude_agent_sdk", source)` 斷言**）
- `backend/services/langgraph_runtime.py:3`、`backend/services/llm_provider.py:8`（註解在講歷史）

`[讀]` `backend/services/review_agent.py:1–30`，模組 docstring 逐字：
**「review_agent.py — A3 Review Agent（LangGraph + OpenRouter）」**，
imports 為 `from services.llm_provider import auth_error_message, configure_provider_env, get_review_model_name`。

`[讀]` `backend/services/langgraph_runtime.py:1–25`，docstring 逐字：
「LangGraph runtime helpers for OpenRouter (OpenAI-compatible) execution.
Parallel to `llm_provider` / `claude-agent-sdk` — this module does not modify CLI / Anthropic env semantics.
Cost-advice graph nodes and prompts belong to U7; this unit only builds the client and runs a
caller-supplied compiled graph.」常數：`:16` `DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"`、
`:17` `DEFAULT_OPENROUTER_MODEL = "google/gemini-3.7-flash"`、`:18` `DEFAULT_TIMEOUT_SECONDS = 60.0`。
`:23` `class RuntimeAuthError(Exception)`，docstring 註明「domain error, not HTTP」。

**→ `codekb/cloud/` 的「本輪重點發現索引」有兩列現已過時** `[承:cloud@2026-10-01]`：
1. 「Design＝LangGraph；**Review／Lens＝Claude Agent SDK**」——Review 已是 LangGraph（`b4f0cdc`），
   `claude_agent_sdk` 全樹零 import 且有測試斷言它不得回來。
2. 「缺 `langchain-openai`／**`claude-agent-sdk` pin**」——`claude-agent-sdk` 已**不在 `requirements.txt`**，
   談不上缺 pin；`langchain-openai` 確實在且確實無 pin（§8）。

**link 2 必須在 `cloud/` 改掉這兩項。** 這是本輪「兩個 store 哪個對」最明確的一處：
`cloud/` 是較新的 store，但**它在這一項上是錯的**，因為它的掃描 commit `5fd8f14`
早於 `b4f0cdc` 的 A3 遷移合併。

### 6.6 `_progress_queue` 之外的狀態容器

`[算]` 本輪確認的行程內共享狀態（供 `K-12`「單一後端行程」假設交叉參照）：

| 位置 | 容器 | 保護 |
|---|---|---|
| `design_agent.py:31` | `_progress_queue`（**單槽**） | **無**（§2） |
| `design_agent.py:32` | `_last_xml`（**單槽**） | **無**（§2.5） |
| `design_agent.py:169` | `memory = MemorySaver()`（LangGraph checkpointer，模組層單例） | 以 `thread_id` 分隔，但 `wa_collab_orchestrator.py:79` 未傳 → 共用 `"default-thread"` |
| `advice_orchestrator.py:23` | `_progress: dict[int, ...]` | `threading.Lock`（`:24`）✅ |
| `advice_orchestrator.py:21` | `_executor: ThreadPoolExecutor \| None`（`_MAX_WORKERS = 2`） | `_executor_lock`（`:22`）✅ |
| `advice_orchestrator.py:26` | `_inflight: set[int]` | `[未掃]` 本輪未確認其鎖 |
| `brain_router.py:87` | `_session_for(user_id)` 背後的行程內 dict（docstring 自述「重啟即失憶」） | `[未掃]` |

---

## 7. Code structure — 目錄地圖與檔案計數

全部 `[算]`（`find` ＋ `wc -l`，未讀內容）。

### Backend（103 支 `.py`，含 `__pycache__` 外）

```
backend/                       5 支 .py   —— database.py(656) models.py(348) main.py(67)
                                            test_agent.py(62) env_bootstrap.py(36)
backend/services/             26 支 .py   10936 LOC
backend/cost/                 21 支 .py    4266 LOC
backend/tests/                48 支 .py
backend/scripts/               3 支 .py   —— dump_openapi.py dump_ws_contract.py
                                            run_hierarchy_migration.py
backend/prompts/               0 支 .py   —— .md system prompts
backend/lenses/                0 支 .py   —— .yaml lens 定義
```

`backend/services/` LOC 排序（`[算]`，前 12）：
`diagram_builder.py` 2080、`wa_rule_engine.py` 973、`user_router.py` 892、
**`brain_ws_contract.py` 783**、`wa_lens_engine.py` 631、`collab_router.py` 593、
`wa_collab_orchestrator.py` 563、`review_orchestrator.py` 510、
**`hierarchy_migration.py` 496**、`review_router.py` 484、**`brain_router.py` 455**、
`rbac_seed_data.py` 317。

其餘：`rbac.py` 302、`design_agent.py` 218、`review_agent.py` 205、`lens_service.py` 203、
`agent_router.py` 186、`llm_provider.py` 178、`langgraph_runtime.py` 165、
`collab_suggestions.py` 147、`auth.py` 112、`lens_router.py` 108、`wa_score_service.py` 104、
`activity.py` 104、`llm_limits.py` 64、`prompt_guard.py` 63。

**`cloud-360/code-structure.md` 寫「`backend/services/` 的模組類型（23 支）」
`[承:cloud-360@2026-09-24]`——HEAD 是 26 支**（新增 `brain_router`、`brain_ws_contract`、
`hierarchy_migration`）。link 2 須更新。

### Frontend（`frontend/src/`）

```
frontend/src/              3 支 .ts*  —— App.tsx main.tsx vite-env.d.ts
frontend/src/pages/       10 支       5376 LOC
frontend/src/components/  12 支
frontend/src/components/cost/ 12 支   —— 10 個 .tsx ＋ types.ts ＋ workloadContext.ts
frontend/src/utils/        6 支
frontend/src/context/      2 支       —— AuthContext.tsx ＋ auth-context.ts（lint 規則強制拆兩檔）
frontend/src/types/        2 支       —— api.d.ts ＋ ws-contract.d.ts（兩者皆為產生檔）
frontend/src/cost/         2 支
frontend/src/config/       1 支       —— api.ts（apiUrl() / wsUrl()）
frontend/src/hooks/        1 支       —— useCollaboration.ts
frontend/src/lib/          1 支
frontend/src/assets/       0 支 .ts*
```

Pages LOC（`[算]`）：`AssessmentPage` 1861、`WorkspacePage` 1194、`RolePermissionsPage` 499、
`AdminPage` 426、**`BrainPage` 403**、`CostPage` 344、`LoginPage` 292、
`AuthorizationRequestsPage` 202、`WaitingApprovalPage` 120、`ForbiddenPage` 35。

`components/`：`ChatBox` `DiagramPreviewPanel` `DrawioCanvas` `LastActivityCell` `Layout`
`LensCriteriaEditor` `NavChromeContext` `PaginationControl` `RouteGuard` `ShareModal`
`Sidebar` `SuggestionRichText` ＋ `cost/` 子目錄。

`components/cost/`：`EstimateAdvicePanel` `EstimateCalculatorGuideModal` `EstimateChecksPanel`
`EstimateCloudCard` `EstimateHistoryDrawer` `EstimateOfficialCalculators` `EstimateSaveModal`
`EstimateShareModal` `EstimateUploadZone` `EstimateWorkloadForm` `types.ts` `workloadContext.ts`。

---

## 8. API documentation — 以 dump 為準

`[跑]` 以 Python 解析 `openapi.json`（**不手數 router**）：

| 指標 | 值 |
|---|---|
| OpenAPI 版本 | `3.1.0` |
| **path 數** | **42** |
| **operation 數** | **55** |
| `components.schemas` 數 | **39** |

per-prefix（`[跑]`，兩種算法並列以免混淆）：

| prefix | path 數 | operation 數 |
|---|---|---|
| `/` | 1 | 1 |
| `/api/architecture` | 13 | 16 |
| `/api/auth` | 15 | 16 |
| `/api/collab` | 7 | 12 |
| `/api/cost` | 6 | 10 |
| **合計** | **42** | **55** |

**`/api/brain` 不在 `openapi.json` 內**——因為它只有 WebSocket，而 WS 不出現在 OpenAPI。
同理 `/api/collab/ws/{workspace_id}` 也不在。**這是本 intent 必須知道的事實**：
既有的 OpenAPI 漂移閘門對 WebSocket **完全無效**。

**`codekb/cloud-360/api-documentation.md` 的 operation 數（`/api/cost/v1` 10、`/api/auth` 16、
`/api/architecture` 16、`/api/collab` 12＋1 WS）與 HEAD 的 operation 數逐欄相符** `[算]` 本輪實算核對。
**唯一要改的是「12 HTTP operation ＋ 1 個 WebSocket」裡那個「1」以及
`architecture.md` 的「既有唯一 WS 前例」**（見 §4.2），還有 `main.py:52–58` 的行號（見 §6.1）。

### WebSocket 契約有獨立的 dump 與閘門

`[算]`：
- `backend/scripts/dump_ws_contract.py`（13647 bytes）
- `ws-contract.json`（repo 根，24252 bytes）
- `frontend/src/types/ws-contract.d.ts`（由 `npm run gen:ws-types` 產生）
- `backend/services/brain_ws_contract.py`（783 LOC，契約定義本體）
- 測試：`backend/tests/test_dump_ws_contract.py`、`backend/tests/test_ws_contract.py`

兩道漂移閘門皆在 CI（`[讀]` `.github/workflows/ci.yml`）：
`:209–210` `npm run check:ws-types`（frontend job）、`:290–291` `python scripts/dump_ws_contract.py --check`（backend job）。
**注意**：`brain_router.py` 的 docstring 說兩道閘門「留給 `U2` 的 code-generation」，
但**閘門本身已經在 CI 裡跑了**（`c619c3f` 帶進來的）。
docstring 指的應是「`brain_router.py` 自己不受這兩道閘門約束」，不是閘門不存在。
**link 2 寫這一段要小心不要把兩件事混成一句。**

### OpenAPI 漂移閘門

`[讀]` `ci.yml:197–198` `npm run check:types`（frontend）、`:272–280` `python scripts/dump_openapi.py --check`（backend）、
`:223–224` 「Spec must not be served statically」。

---

## 9. Component inventory

`[算]`（由檔名、LOC 與本輪讀過的片段推斷；**未逐支讀全文**，故標 `[算]`，
除另註 `[讀]` 者）。

### Backend — app shell 與資料層

| 模組 | LOC | 責任 |
|---|---|---|
| `main.py` `[讀]` | 67 | FastAPI app、CORS、startup hook、8 條 `include_router` |
| `env_bootstrap.py` | 36 | 強制從 `backend/.env` 載入環境（不看 cwd） |
| `database.py` `[讀部分]` | 656 | engine／session、`DATABASE_URL` 正規化（`:23`、`:34–35`）、`init_db()`、`_ensure_*` 啟動補丁 |
| `models.py` `[算]` | 348 | 13 個 SQLAlchemy 表（§4.3 列出）。**階層三表不在內** |

### Backend — 認證／授權

| 模組 | LOC | 責任 |
|---|---|---|
| `services/auth.py` | 112 | JWT、`get_current_user`、`require_any_user`、`get_password_hash` |
| `services/rbac.py` | 302 | `CANONICAL_ROLES`（角色清單正本）、`require_story_action`、權限判定 |
| `services/rbac_seed_data.py` | 317 | `role_permissions` seed 資料。`[跑]` 測試輸出顯示本輪 seed **308 列** |
| `services/user_router.py` `[讀部分]` | 892 | `/api/auth` 全面。**`:80–88` 是 story_id → 中文名字典（§1 的 MCP 命中處）**；`:89` `CATALOG_EXCLUDED_STORIES = frozenset({"J1"})` |
| `services/activity.py` | 104 | 最後活動記錄 |
| `services/prompt_guard.py` | 63 | 平台自我竄改預檢（`agent_router.py:112–119` 的呼叫端 `[讀]`） |

### Backend — A1 產圖

| 模組 | LOC | 責任 |
|---|---|---|
| `services/agent_router.py` `[讀部分]` | 186 | `/api/architecture` 的三個 SSE 端點（`:97`／`:129`／`:186`）。`:121` `_ensure_llm_keys()`、`:125` 呼叫 design agent |
| `services/design_agent.py` `[讀]` | 218 | **LangGraph ＋ `@tool`／`ToolNode`**（§1）。**模組級全域併發缺陷（§2）** |
| `services/diagram_builder.py` | 2080 | mxGraph XML 產生（最大模組；純函式層，PBT 落點） |

### Backend — A3 評核／Lens

| 模組 | LOC | 責任 |
|---|---|---|
| `services/review_router.py` | 484 | 評核 HTTP ＋ SSE（`:73`） |
| `services/review_orchestrator.py` | 510 | 評核流程編排 |
| `services/review_agent.py` `[讀部分]` | 205 | **A3 Review Agent（LangGraph ＋ OpenRouter）**（§6.5） |
| `services/wa_rule_engine.py` | 973 | WA 規則引擎（純函式，PBT 落點） |
| `services/wa_lens_engine.py` | 631 | Lens 引擎（純函式） |
| `services/wa_score_service.py` | 104 | 評分 |
| `services/lens_router.py` / `lens_service.py` | 108 / 203 | Lens 管理 |

### Backend — A4 共編

| 模組 | LOC | 責任 |
|---|---|---|
| `services/collab_router.py` | 593 | `/api/collab`，含 **WS `:266`**。無 service 層 |
| `services/wa_collab_orchestrator.py` `[讀部分]` | 563 | `:70` `_remap_design_events` 把 design 事件改名；**`:79` 呼叫 design agent 未傳 `thread_id`** |
| `services/collab_suggestions.py` | 147 | 建議 |

### Backend — LLM gateway

| 模組 | LOC | 責任 |
|---|---|---|
| `services/llm_provider.py` `[讀]` | 178 | **provider 選擇（只剩 openrouter）＋ cli 退役（§3）** |
| `services/llm_limits.py` | 64 | token 上限寫入 env（`:52` docstring 仍提 "CLI subprocesses"，**措辭已過時**） |
| `services/langgraph_runtime.py` `[讀部分]` | 165 | OpenRouter LangGraph client builder。`:23` `RuntimeAuthError` |

### Backend — 大腦（**demo scope**）

| 模組 | LOC | 責任 |
|---|---|---|
| `services/brain_router.py` `[讀 docstring ＋ 函式骨架]` | 455 | `/api/brain/ws`（`:238`）。**demo scope，`U13` 落地時整支取代**（§4.1） |
| `services/brain_ws_contract.py` `[未掃內容]` | 783 | WS 訊息型別契約。產生 `ws-contract.json` ＋ 前端型別 |

### Backend — 階層

| 模組 | LOC | 責任 |
|---|---|---|
| `services/hierarchy_migration.py` `[算骨架]` | 496 | `projects`／`systems`／`diagram_change_records` 的 schema 保障（`:269`）＋一次性遷移（`:204`）＋終檢（`:477`） |
| `scripts/run_hierarchy_migration.py` `[未掃]` | — | 遷移 CLI 入口 |

### Backend — Cost 域

見 §6.3 的完整 21 支表。

### Frontend

見 §7 的檔案清單。**`[未掃]`**：本輪未讀任何前端元件的內容，只取路由表（`App.tsx` `[讀]`）
與檔案清單／LOC（`[算]`）。`cloud-360/code-structure.md` 的前端段落
`[承:cloud-360@2026-09-24]` 可沿用，但須補 `BrainPage.tsx` 與 `components/cost/` 的 12 支。

---

## 10. Technology stack

### Backend `[讀]` `backend/requirements.txt` 全檔

**宣告 18 項**，其中 **2 項精確 pin、1 項下限、15 項完全浮動、無 lockfile**：

| 套件 | 版本形式 | 備註 |
|---|---|---|
| `fastapi` | **`==0.111.0`** | **精確 pin**。檔內 `:1–8` 註解說明理由：OpenAPI 規格輸出在同版本下位元決定性、**跨版本會飄（實測換版產生 20 行差異）**，不釘會讓漂移檢查在無關 PR 上變紅且與真漂移不可區分。明言「相容釋出形式（`~=`）仍會浮動，形式選錯等於沒釘 —— 故用 `==`」 |
| `pydantic` | **`==2.13.4`** | **精確 pin**，同上理由 |
| `openpyxl` | `==3.1.5` | 精確 pin（XLSX 讀取） |
| `PyYAML` | `>=6.0` | 下限 |
| `uvicorn` | 無 | |
| `httpx` | 無 | |
| `python-dotenv` | 無 | |
| `sqlalchemy` | 無 | **刻意不設上限**（`:14–22` 註解；曾用 `sqlalchemy<2.1` 止血，改為顯式指定 driver 根治） |
| `psycopg[binary]` | 無 | **psycopg v3**（§3.6）。`psycopg2` 全檔零命中 |
| `passlib[bcrypt]` | 無 | |
| `bcrypt` | 無 | |
| `pyjwt` | 無 | |
| `langgraph` | 無 | |
| `langchain-core` | 無 | |
| `langchain-anthropic` | 無 | `design_agent.py:121` 的 `ChatAnthropic` |
| `langchain-openai` | 無 | OpenRouter（OpenAI 相容）路徑 |
| `hypothesis` | 無 | PBT |
| `boto3` | 無 | AWS Price List Query（`cost/pricing_sdk.py`；ADR-0018 保留） |

**`team.md` 記載的 `fastapi[standard]==0.141.1` 已過時**——HEAD 是 `fastapi==0.111.0`
（**無 `[standard]` extra、版本也不同**）。`[算]` 這一點對 `team.md` Testing Posture
那條「`requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，`TestClient` 前置條件已滿足」
**可能有影響**（`[standard]` extra 不在了，但 `httpx` 仍獨立宣告，而 `httpx` 是
`starlette.testclient` 的實際前置）。測試實跑通過（§11），**所以結論仍成立、理由要改寫**。
link 2 應記下這個落差並標為「規則文字待修」，不要逕自改規則檔。

**`cloud-360/technology-stack.md` 寫「17 項宣告」** `[承:cloud-360@2026-09-24]`——HEAD 是 **18 項**。

### Frontend `[讀]` `frontend/package.json` 全檔

`dependencies`（5）：`react ^19.2.6`、`react-dom ^19.2.6`、`react-router-dom ^7.18.2`、
`html2canvas ^1.4.1`、`jspdf ^4.2.1`。**無圖表套件**（圓餅自畫 SVG，與 `refined-mockups:c21` 一致）。

`devDependencies`（19）：`eslint ^10.3.0`、`@eslint/js ^10.0.1`、`typescript-eslint ^8.59.2`、
`eslint-plugin-react-hooks ^7.1.1`、`eslint-plugin-react-refresh ^0.5.2`、`globals ^17.6.0`、
`typescript ~6.0.2`、`vite ^8.0.12`、`@vitejs/plugin-react ^6.0.1`、
`tailwindcss ^4.3.0`、`@tailwindcss/postcss ^4.3.0`、`postcss ^8.5.15`、`autoprefixer ^10.5.0`、
`@playwright/test ^1.56.0`、`openapi-typescript 7.13.0`（**唯一精確 pin**）、
`@types/node ^24.12.3`、`@types/react ^19.2.14`、`@types/react-dom ^19.2.3`。

`overrides`：`openapi-typescript` 的 `typescript` 綁到 `$typescript`。

**`package-lock.json` 已 commit**（`[算]` 141247 bytes）。
**對照組**：frontend 有 lockfile ＋ `npm ci`；backend 無 lockfile。

`scripts`（8）：`dev` `build`（`tsc -b && vite build`）`lint`（`eslint .`，**無 `--max-warnings 0`**）
`preview` `test:e2e`（`playwright test`）`gen:types` `check:types` `gen:ws-types` `check:ws-types`。

**前端測試框架仍只有 Playwright**：`devDependencies` 無 vitest／jest／`@testing-library/*`。
`team.md` 的這條記載**本輪複驗仍成立**。

---

## 11. Code quality assessment — 誠實狀態

### 11.1 Backend 測試：**419 個，全綠**（`[跑]`）

`[跑]` 從 `backend/` 執行 `python3 -m unittest discover -s tests`，exit 0，輸出尾段逐字：

```
----------------------------------------------------------------------
Ran 419 tests in 28.557s

OK
```

（與 brief 的 419 一致。）

`[算]` `ls backend/tests/*.py | wc -l` → **48 支測試檔**
（`team.md` 記 21 支，`[承]` 於 HEAD `c3de2c8`——**已超過兩倍，嚴重過時**）。

執行過程中觀察到的附帶事實（`[跑]`，從輸出讀出）：
- `rbac_seed_data` 每個 session seed **308 列** `role_permissions`
- `TestClient` 確實在用（輸出有 `INFO:httpx:HTTP Request: GET http://testserver/api/auth/list "HTTP/1.1 200 OK"`、
  `PUT .../api/auth/2/active`、`PUT .../api/auth/2/role`）
- 權限稽核 log 實際運作（`INFO:cloud360.user_router:【權限稽核】User Privilege Re-assignment | ...`）
- 一個 `SAWarning`：`test_vector_extension_bootstrap.py:176` 的 `Base.metadata.drop_all(bind=engine)`
  因 `user_diagrams`／`users` 間有無法解析的 FK 循環而無法排序 DROP
- `wa_rule_engine` 有一條 `sanitized mxGraph XML after parse error` 的 INFO（測試刻意餵壞 XML）
- 階層遷移測試印出遷移計數與 `AC9.1.4` 終檢（§4.3）

### 11.2 Property-based testing

`[跑]` `grep -rln "@given" backend/tests/ | wc -l` → **16 支檔**
`[跑]` `grep -rn "@given" backend/tests/ | wc -l` → **48 處**

（`team.md` 記「7 個檔共 13 個 `@given`」`[承]` 於 `c3de2c8`——**已增至 16 檔／48 處**。）

ADR-0006 的 PBT hard constraint 落點：`ADR-0017 §1–§2` 把它由 `cost_calculator`
移錨到**估價表解析器**，而 §6.3 的 `validate_cost_calculator_boundary.py` 實跑確認
那三支（`estimate_parser.py`／`estimate_readers.py`／`estimate_validator.py`）
就是純函式層。`[未掃]` 本輪未核對這三支是否實際有 `@given` 覆蓋——
**link 2 應把這一項列為待查**，因為它是 hard constraint 的可執行檢查點。

### 11.3 覆蓋率：**完全無量測機制**（`[跑]`）

`[跑]` `ls .coveragerc` → No such file。
`[算]` `requirements.txt` 無 `coverage`／`pytest-cov`；`[讀]` `ci.yml` 無 coverage step。

**`org.md` 宣告的「最低 80% line coverage」目前既無法量測也無法強制。**
這與 `team.md` 的既有記載一致，本輪複驗仍成立。

### 11.4 Backend：零 linter／formatter／type checker（`[跑]`）

`[跑]` `ls pyproject.toml setup.cfg .ruff.toml ruff.toml mypy.ini backend/pyproject.toml`
→ **六個全部 No such file**。

**`org.md` 宣告的「Formatter: Black (Python)」「Linter: Ruff，CI 強制」在 backend 側不成立。**
本輪複驗仍成立。

### 11.5 Frontend ESLint：**0 errors, 2 warnings**（`[跑]`，與 `team.md` 的 3 不同）

`[跑]` 從 `frontend/` 執行 `npm run lint`，exit 0，輸出逐字：

```
/Users/.../frontend/src/pages/AssessmentPage.tsx
  365:6  warning  React Hook useEffect has a missing dependency: 'detectProviderFromXml'. ...  react-hooks/exhaustive-deps

/Users/.../frontend/src/pages/WorkspacePage.tsx
  302:6  warning  React Hook useEffect has a missing dependency: 'fetchDiagrams'. ...  react-hooks/exhaustive-deps

✖ 2 problems (0 errors, 2 warnings)
```

**與 `team.md` 的記載比對**（`team.md` 記 3 個：`AssessmentPage.tsx:365`、`LoginPage.tsx:36`、
`WorkspacePage.tsx:279`）：

| 項 | `team.md` | HEAD `[跑]` | 變化 |
|---|---|---|---|
| `AssessmentPage.tsx:365` | 有 | **有（行號相同）** | 不變 |
| `LoginPage.tsx:36` | 有 | **無** | **已修掉** |
| `WorkspacePage.tsx:279` | 有 | **`:302`** | **行號位移 23 行**（同一個 `fetchDiagrams` 警告） |

**無 `.prettierrc`**（`[跑]` `ls .prettierrc*` → no matches found）。

### 11.6 CI 管線（`[讀]` `.github/workflows/ci.yml`）

**5 個 job**，本輪複驗行號：

| 行 | job | 內容 |
|---|---|---|
| `:55` | `gate` — Sync write-back gate | 判斷是否來自 sync write-back（`:92` 有一段註解解釋 `set +e` 為何必要） |
| `:141` | `repo-contract` | `:154` `validate_repo_contract.py`、`:159` `validate_env_contract.py`、**`:162` `validate_cost_calculator_boundary.py`**、**`:167` `validate_pricing_lookup_boundary.py`** |
| `:169` | `frontend` | `:186` `npm ci`、`:189` `npm run lint`、**`:198` `npm run check:types`**、**`:210` `npm run check:ws-types`**、`:214` `npm run build`、`:224` Spec must not be served statically |
| `:233` | `backend` | `:250` `pip install -r requirements.txt`、`:263` import smoke（`python -c "import main; ..."`）、**`:280` `dump_openapi.py --check`**、**`:291` `dump_ws_contract.py --check`**、`:297` `python -m unittest discover -s tests -v` |
| `:299` | `docker-build` | |

**閘門數已由 6 增為 9**（`team.md` 記「六道現有 CI 閘門」`[承]`）。新增的三道是
`validate_cost_calculator_boundary.py`、`validate_pricing_lookup_boundary.py`、
`check:ws-types` ＋ `dump_ws_contract.py --check`（後兩者是同一個契約的兩端，算兩道則為 10）。
**link 2 應改寫這個數字並列出完整清單**，因為 `team.md` 的「六道全綠仍放行三類缺陷」
那段論證的基數變了（結論不一定變，但基數必須更新）。

### 11.7 `scripts/` 下的工具（`[算]` `ls scripts/`）

`aidlc_sync_buglist.py` `aidlc_sync_pull.py` `aidlc_sync_push.py` `smoke_langgraph_openrouter.py`
`tcms_sync.py` `tcms_validate.py` `validate_cost_calculator_boundary.py`
`validate_env_contract.py` `validate_pricing_lookup_boundary.py` `validate_repo_contract.py`。

### 11.8 本輪**未**執行的檢查（誠實列出）

`[未掃]`：`validate_repo_contract.py`、`validate_env_contract.py`、`npm run build`（`tsc -b`）、
Playwright e2e、`dump_openapi.py --check`、`dump_ws_contract.py --check`、`docker-build`。
**link 2 不得把這些記為「本輪通過」**；只有 §6.3 的兩支邊界檢查、§11.1 的 unittest、
§11.5 的 eslint 是本輪實跑。

---

## 12. Dependencies

### 12.1 LangGraph／LangChain 集合與各自的消費者

`[算]`（由 import grep 與模組 docstring 推得）：

| 套件 | 消費者 | 證據 |
|---|---|---|
| `langgraph` | `design_agent.py:9–12`（`StateGraph` `START` `END` `add_messages` `MemorySaver` `ToolNode`）`[讀]`；`review_agent.py` `[讀 docstring]`；`cost/cost_advice_agent.py` `[算]`；`services/langgraph_runtime.py` `[讀]` | |
| `langchain-core` | `design_agent.py:14–15`（`BaseMessage` `HumanMessage` `AIMessage` `SystemMessage` `ToolMessage`、`tool`）`[讀]` | |
| `langchain-anthropic` | `design_agent.py:121` `ChatAnthropic(...)` `[讀]` | 經 `base_url` 指向 OpenRouter |
| `langchain-openai` | `langgraph_runtime.py` 路徑（OpenAI 相容）`[算]` | `:16` `DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"` `[讀]` |
| `hypothesis` | 16 支測試檔的 48 處 `@given` `[跑]` | |
| `boto3` | `cost/pricing_sdk.py` `[算]` | AWS Price List Query（ADR-0018 保留） |
| `openpyxl` | 估價表 XLSX 讀取 `[算]` | |
| `psycopg[binary]` | `database.py:23`／`:34–35` `[讀]` | psycopg **v3** |

**兩個 OpenRouter 適配並存**（`cloud/` store 已記此事 `[承:cloud@2026-10-01]`，本輪部分複驗）：
- `llm_provider.py` 走 **Anthropic 相容**（`ANTHROPIC_BASE_URL = "https://openrouter.ai/api"`，`:49` `[讀]`）
- `langgraph_runtime.py` 走 **OpenAI 相容**（`"https://openrouter.ai/api/v1"`，`:16` `[讀]`）

**兩個 base URL 不同（一個有 `/v1` 一個沒有），而且是兩支不同模組各自寫死的。**
這正是 `team.md`「單一真實來源」規則關切的形狀。預設模型也各有一份：
`llm_provider.py:52–54`（`google/gemini-3.7-flash` ×2、`google/gemini-2.5-flash` ×1）
vs `langgraph_runtime.py:17`（`google/gemini-3.7-flash`）。

### 12.2 建置期耦合（契約 → 產生檔）

| 來源 | 工具 | 產出 | CI 閘門 |
|---|---|---|---|
| FastAPI app | `backend/scripts/dump_openapi.py` | `openapi.json`（repo 根） | `ci.yml:280` `--check` |
| `openapi.json` | `npm run gen:types`（`openapi-typescript 7.13.0`） | `frontend/src/types/api.d.ts` | `ci.yml:198` `check:types` |
| `brain_ws_contract.py` | `backend/scripts/dump_ws_contract.py` | `ws-contract.json`（repo 根） | `ci.yml:291` `--check` |
| `ws-contract.json` | `npm run gen:ws-types` | `frontend/src/types/ws-contract.d.ts` | `ci.yml:210` `check:ws-types` |

**兩條鏈，各兩道閘門。** 第二條（WS）是 `c619c3f` 新增的，兩個 store 都沒記。

### 12.3 外部執行期依賴（非套件）

`[承:cloud-360@2026-09-24]`，本輪**未複驗**：PostgreSQL、n8n webhook（架構圖 icons）、
OpenRouter API、draw.io（前端 iframe）、Cloudflare Tunnel（staging 對外）。
`[讀]` `backend/.env.example` 間接確認 OpenRouter 為必要憑證來源。

### 12.4 CI 強制的 import 邊界

見 §6.3 的兩支 validator（本輪實跑通過）。
**新模組必須先確認不會誤觸**——特別是 `backend/cost/` 下的新檔。

---

## 13. 給 link 2 的合併指示（逐項）

### 13.1 從 `cloud-360/` 搬進 `cloud/`（內容較完整，但須更新）

| 來源 | 動作 | 必改之處 |
|---|---|---|
| `business-overview.md` 全檔（主線一～五、業務邊界、詞彙表） | **整段沿用** | 補 `/brain` 路由（§5）；標 `[承:cloud-360@2026-09-24]` |
| `architecture.md` 的三張互動圖（C1 估價 SSE、登入 RBAC 鏈、A4 WS 握手） | 沿用 | **「既有唯一 WS 前例」→ 改為兩條之一**（§4.2） |
| `architecture.md` §「架構約束」（WebSocket 必須掛 `/api/` 之下 等） | 沿用 | 補 `/api/brain/ws` 為第二個實例 |
| `code-structure.md` 全檔 | 沿用 | **`backend/services/` 23 支 → 26 支**（§7）；補 `BrainPage.tsx`、`components/cost/` 12 支 |
| `component-inventory.md` 的深讀元件段 | 沿用 | 補 §9 的三組新元件（brain ×2、hierarchy ×1） |
| `api-documentation.md` 全檔（operation 數本輪實算相符） | 沿用 | **`main.py:52–58` → `:54–63` ＋ 補 `brain_router`**（§6.1）；補 WS 契約鏈（§8） |
| `technology-stack.md` | 沿用骨架 | **「17 項宣告」→ 18 項**；**`fastapi[standard]==0.141.1` → `fastapi==0.111.0`**；psycopg v3（§10） |
| `dependencies.md` §「兩套並存的 LLM 客戶端棧」 | 沿用 | 改寫為「兩個 OpenRouter 適配」（Agent SDK 已不存在，§6.5／§12.1） |
| `code-quality-assessment.md` 的 T-1／T-2／T-3 技術債 | 沿用 | **T-3 保留且另立 §2 的併發缺陷，不要合併**（§2.7） |

### 13.2 在 `cloud/` 中**改正**的既有主張

| 現有主張（`cloud/`） | 本輪查證 | 處置 |
|---|---|---|
| 「Design＝LangGraph；**Review／Lens＝Claude Agent SDK**」 | `claude_agent_sdk` 全樹零 import，且 `test_a3_langgraph_migration.py:33,40` 有兩個 `assertNotIn` 斷言它不得回來；`review_agent.py` docstring 逐字「LangGraph + OpenRouter」 | **改為全數 LangGraph**（§6.5） |
| 「缺 `langchain-openai`／**`claude-agent-sdk` pin**」 | `claude-agent-sdk` 已不在 `requirements.txt` | **刪掉後半**；`langchain-openai` 無 pin 仍成立（§10） |
| `llm_provider` 的模型預設與 env 契約（掃描於 `5fd8f14`） | 本檔已於 `34aeef3` 重寫（237→178 行） | **以 §3 整段取代** |
| `Depth: Minimal` ＋ `analyzed.paths` 22 條 | 本輪新增 deep 路徑 | 見 §13.4 |

### 13.3 **新增**內容（兩個 store 都沒有）

1. **MCP 現況：零基礎設施 ＋ `MCP` 這個字已被 RBAC story `H3` 佔用**（§1）
2. **`design_agent.py` 的模組級全域併發缺陷 ＋ `advice_orchestrator.py` 的 in-repo 正解**（§2）
3. **`llm_provider.py` 重寫、cli 退役、psycopg v3**（§3）
4. **brain demo-scope gateway（`/api/brain/ws`）＋ `/brain` 頁 ＋ WS 契約鏈**（§4.1、§4.2、§8）
5. **階層三表已在 `schema_rbac.sql` ＋ migration，但不在 ORM／router／service**（§4.3）
   ——**這推翻 intent-capture 當時「`system_id` 命中 0 次」的前提**
6. **CI 閘門由 6 道增為 9 道**（§11.6）
7. **`wa_collab_orchestrator.py:79` 未傳 `thread_id`，落回 `"default-thread"`**（§2.3）
8. **兩個 OpenRouter base URL 不一致（`/api` vs `/api/v1`）**（§12.1）

### 13.4 `Scope of Analysis` 建議值

**`kind: partial`**。理由（依 `project.md` 已記的規則：breadth 由使用者選、depth 由實際讀了什麼決定）：
本輪有多支模組只取簽章或 docstring，`backend/tests/` 48 支裡只讀了 `test_llm_provider.py` 的標題列，
前端完全沒讀內容——**任一條成立即為 partial**。

建議 `analyzed.paths`（本輪**真的深讀**者）：
```
backend/services/design_agent.py
backend/services/llm_provider.py
backend/main.py
backend/cost/advice_orchestrator.py        # 僅 1–82 行深讀，其餘 [算]
backend/requirements.txt
backend/.env.example                        # 僅 LLM_PROVIDER/OPENROUTER 段
frontend/src/App.tsx                        # 僅路由表
frontend/package.json
openapi.json                                # 以程式解析
.github/workflows/ci.yml                    # 僅 job/step 骨架
```

**不得寫進 `analyzed.paths`** 的（深度切分落在檔案內部，依 `project.md` 的規則
「寧可低報覆蓋」）：
- `backend/services/brain_router.py` —— 只讀 docstring（`:1–31`）＋函式骨架，**455 行的本體未讀**
- `backend/services/user_router.py` —— 只讀 `:80–92`，**892 行的本體未讀**
- `backend/services/agent_router.py` —— 只讀 `:115–135`
- `backend/services/wa_collab_orchestrator.py` —— 只讀 `:70–90`
- `backend/services/review_agent.py`／`langgraph_runtime.py` —— 只讀 `:1–30` / `:1–25`
- `backend/database.py` —— 只 grep `postgresql`
- `backend/cost/advice_orchestrator.py` 的 `:83–358`

`shallow.paths` 應含：`backend/services/`（其餘）、`backend/cost/`（其餘 20 支）、
`backend/tests/`（48 支）、`backend/models.py`、`backend/database.py`、
`backend/services/brain_ws_contract.py`、`backend/services/hierarchy_migration.py`、
`frontend/src/pages/`、`frontend/src/components/`、`frontend/src/utils/`、
`schema_rbac.sql`、`schema.sql`、`ws-contract.json`、`deploy/`、`.claude/`、`aidlc/`、
`LOCAL-DEV.md`、`DEPLOY.md`、`TESTING.md`、`README.md`。

**`codekb-scope-diff --compare` 的預期**：相對於 `cloud/` 於 `5fd8f14` 的 22 條 deep 集合，
本輪 deep 集合更小（9 條）但方向不同（新增 `advice_orchestrator.py`、
`.env.example`、`package.json`、`ci.yml`；失去多支 wa_*／review_*）。
**可能回 `NARROWER` 或 `UNKNOWN_SCOPE`**；若為後者，依 `project.md` 的規則
必須在核可關卡明講「coverage backstop 本輪未提供任何保證」，
**不得讓「沒出現 NARROWER」被讀成覆蓋已驗證**。

### 13.5 本輪未解、建議列為待查的項目

| 項 | 為什麼重要 |
|---|---|
| `backend/tests/helpers.py` 是否仍 mock `psycopg2` | `psycopg2` 已不在相依裡；`team.md` 的 Testing Posture 逐字記載那個 mock（§3.6） |
| `LOCAL-DEV.md` 是否已隨 `.env.example` 的 `LLM_PROVIDER` 預設值變更同步 | `project.md` 有 blocking 規則（§3.4） |
| `DEPLOY.md` 與 `schema_rbac.sql` 的階層三表是否已同步 | `project.md` 的 blocking 規則；三表已在 schema（§4.3） |
| 純函式三支（`estimate_parser`／`estimate_readers`／`estimate_validator`）是否實際有 `@given` 覆蓋 | ADR-0006 PBT hard constraint 的可執行檢查點（§11.2） |
| `brain_ws_contract.py` 783 行的實際契約內容（九種伺服器訊息、六種客戶端訊息的完整定義） | `U2`／`U13` 的直接輸入；本輪只從 `brain_router.py` docstring 得知其子集 |
| `_last_xml` 的讀取端在哪 | 判斷 §2.5 的外部可觀察後果 |
| `main.py:62` 註解說「下面兩行」但只有一行 `include_router` | 小矛盾，移除 brain 時別漏掉 `:7` 的 import（§4.1） |
| `deploy.yml`、agentic workflows、Playwright e2e 現況 | 本輪完全 `[未掃]` |
