# Code Summary — `U22 progress-channel`（`library`）

<!-- Stage: code-generation（Construction 3.5）· Unit: progress-channel · kind: library -->

方法論為 **`test-after`**（`AIDLC-TESTING-CONTRACT: sha256:1f0b6822…`）：先實作該層，
再寫並跑該層的測試。十二個計畫步驟全部執行完畢，計畫檔內的核取方塊已逐項勾選。

**本單元不新增任何使用者可見的功能。** 它把一個共用的格子換成一組各自獨立的格子，
使兩件已經在發生的壞事停止：一位使用者收到另一位使用者的架構圖，以及一個請求結束時
把另一個還在跑的請求弄崩。

---

## 一、檔案清單（7 個應用程式來源路徑）

`source-manifest.json` 為正式來源；本表與 `git status --porcelain -- backend/` 的集合
**實測相等**（7 = 7，雙向差集皆為空）。

### 新建（3）

| 路徑 | 行數 | 為什麼 |
|---|---|---|
| `backend/services/progress_channel.py` | 346 | 本單元的全部實作：`RequestKey`／`ProgressEvent`／`_Channel`／`ProgressChannelRegistry` ＋ 私有同步 `_admit`。模組層單例公開名為 `ProgressChannel`，使四個操作的呼叫形狀與 `functional-spec.md` 的 `ProgressChannel.<op>(key)` 逐字一致 |
| `backend/tests/test_progress_channel.py` | 432 | 行為測試：計畫核可的 7 個 ＋ **1 個整合邊界測試**（見第五節，計畫外新增並附理由） |
| `backend/tests/test_progress_channel_contract.py` | 429 | 5 個契約閘門（讀原始碼文字與 AST 並斷言）。形狀沿用 `backend/tests/test_hierarchy_migration.py` 的 `test_schema_rbac_sql_matches_migration_ddl` |

### 修改（4）

| 路徑 | +／− | 改了什麼 |
|---|---|---|
| `backend/services/design_agent.py` | +105／−36 | 刪兩個模組層全域、刪「把全域設回 None」那一行、`_drain_progress` 改收 `request_key`、`run_design_agent` 新增必填關鍵字參數 `request_key`、工具本體改以注入的 `RunnableConfig` 取鍵、**兩個例外原文洩漏點改為固定字串**、移除已無用的 `import asyncio` |
| `backend/services/agent_router.py` | +38／−3 | 呼叫點 1（**使用者路徑的真實 SSE 入口**）：鑄造鍵、`open` 在 generator 內、`close` 在 `finally`、**`B-1` 的 `DuplicateChannelKey` handler** |
| `backend/services/wa_collab_orchestrator.py` | +44／−23 | 呼叫點 2：鑄造鍵、`open`／`close`、handler；remap 迴圈本體因包進 `try` 而整段縮排 |
| `backend/test_agent.py` | +19／−2 | 呼叫點 3（CLI 工具）：同一套鑄造規則，每輪輸入各自鑄造新鍵 |

### 刪除（0）

### 刻意**沒有**改的檔案，以及為什麼重要

| 路徑 | 為什麼沒改 |
|---|---|
| `backend/requirements.txt` | **零新依賴**（`collections.deque`／`dict`／`asyncio`／`unittest` 皆標準庫）。實測 `git diff` 為空 |
| `.github/workflows/ci.yml` | **零 CI 設定變更**。兩支新測試檔放進 `backend/tests/` 即被既有的 `python -m unittest discover -s tests` 撿到——這是 `[Q1]`=A 的全部價值 |
| `deploy/*`、三個 `.env.example`、`render-env.sh` | `SEC-4`：零環境變數、零 compose 服務。實測 `git status` 對這些路徑為空；`validate_env_contract.py` 通過 |
| `schema_rbac.sql`、`DEPLOY.md` | 本單元無任何資料表（`project.md` blocking 規則的五個觸發條件逐項皆未命中） |
| `design_agent.py` 的 `memory = MemorySaver()` | LangGraph checkpointer 的模組層單例，不是外洩路徑。計畫明文要求保留 |

---

## 二、關鍵實作決定

### 之一、鍵如何抵達工具：LangGraph 的 `RunnableConfig` 注入（計畫未指定機制）

工具 `draw_architecture_diagram` 由 `ToolNode` 呼叫，只拿得到 LLM 給的四個業務參數
——它**無法**從簽章收到 `request_key`。計畫指定了「鍵要傳下去」但沒指定用什麼機制，
故這是本站的決定。三個候選：

| 候選 | 判定 |
|---|---|
| `contextvars.ContextVar` | 可行（per-task，不會跨請求共享），但是**環境式狀態**：工具與入口端之間沒有顯式契約 |
| `build_graph(request_key)` 的閉包 | 結構最強（鍵被語彙捕獲），但 `build_graph()` 目前無參數，而 `backend/tests/test_langgraph_migration.py:24` 逐字呼叫 `build_graph()`——加必填參數會弄壞既有測試（違反 scope floor）；加預設值則又多一條靜默路徑 |
| **`config["configurable"]`（採用）** | 鍵隨 invocation 傳遞，工具以注入的 `config: RunnableConfig` 讀回。`build_graph()` 簽章不變，既有測試不受影響 |

**實測確認**（寫下之前先驗）：`langchain-core 1.6.6` 下 `draw_architecture_diagram.args`
只含四個業務參數，`config` **不在 LLM 看到的 schema 內**；以 `ToolNode` 實跑一次，工具
內讀到的 `config["configurable"]["request_key"]` 與傳入值相符。

欄位名以 `REQUEST_KEY_CONFIG_FIELD` 常數表達，使「誰寫、誰讀」是同一個識別字而不是
兩處各寫一次字面值。

### 之二、`request_key` 是**必填關鍵字參數**，刻意沒有預設值

`S-2` 把兩種失敗都寫下來了：「新參數若必填則該端點直接壞，若選填則它的事件全部走
`BR3.2` 的記 log 丟棄」。兩者都源於呼叫點忘了傳，但**可觀察性相差極大**：必填 →
`TypeError`，在入口端就炸；選填 → 畫面上只是沒有進度訊息，使用者看不到任何錯誤。
本單元存在的全部理由就是修安靜的失敗，所以選必填。

### 之三、`is_open` 不是死狀態——它有一個讀者

`close()` 把鍵從 registry `pop` 掉，所以從外部永遠觀察不到 `is_open == False`。乍看
`is_open` 就是本單元正在退場的那個「寫了從不讀」的形狀。**它的讀者是 in-flight 的
`drain` 迭代器**：一個已經在跑的 `drain` 仍持有 `_Channel` 物件的參照（registry 裡那一筆
已被移除），靠這個旗標停止吐事件。少了它，被放棄的請求的 in-flight drain 會繼續讀一條
已死的通道。此理由寫進該欄位的程式註解。

### 之四、`message` 的丟棄語意（`BR4.1` 沒有交代的那一格）

`BR4.1` 只點名 `progress` 可丟、`xml` 與 `error` 永不丟，**對 `message` 沒有規定**。
`functional-spec.md` 的 `WF-4` 三列也只涵蓋那兩類。本實作把 `message` 歸入**不可丟棄**
（`DROPPABLE_EVENT_TYPES` 只含 `progress`），理由是丟掉模型對使用者的回覆與丟掉 `xml`
同級。現狀 `message` 由 `run_design_agent` 主迴圈直接 yield 而不經通道，故這個判讀在當下
**不可達**；但它必須有一個定義，而留白會讓下一個人自行猜。已記入 `traceability.json`
的 `BR4.1` 列。

### 之五、`ProgressEvent` 的型別驗證在建構時快速失敗

未知的 `type` 是程式錯誤（四個寫入端都用字面值），而它的下游後果是 `wa_collab` 的 remap
走到 `else` 分支把事件原樣送出去——那是安靜的。故 `__post_init__` 對未知類別 raise
`ValueError`。**不是** `HTTPException`：本模組是 library，不碰 HTTP。

### 之六、`DuplicateChannelKey` 的訊息刻意不含鍵

鍵是這條通道唯一的可見性機制，不應出現在任何可能被轉述的字串裡。鍵以 `.key` 屬性提供給
需要記 log 的呼叫端。測試 4 斷言 `assertNotIn("dup", str(exception))`。

### 之七、`open()` 放在 `event_generator` **內**而非外

鍵的壽命必須與 generator 等長，`finally` 才真的涵蓋它。放在外面則 `StreamingResponse`
還沒開始迭代就已佔用一個鍵，而客戶端若從未連上就不會有人去 `close`——那正是 `BR2.3`
要防的殘留。

### 之八、同一個形狀踩了四次：「檢查某字串不存在，而說明該檢查就會引入那個字串」

本單元的五個閘門檢查的都是「某個東西不存在」。四次實際發生：

| 次 | 我寫的註解／文件 | 會讓哪個閘門永遠紅 |
|---|---|---|
| 1 | `design_agent.py` 的退場註解逐字寫出兩個舊符號名 | 測試 8 |
| 2 | 同檔的註解引用舊的插值字串 | 測試 12 第一子句 |
| 3 | 「本函式不得代為 close——原本的 `<舊符號> = None`……」 | 測試 8 |
| 4 | `progress_channel.py` 模組 docstring 寫「也不 import uuid／secrets／random」 | 測試 11（我當時多加的文字層檢查） |

前三次的處置是**改寫註解使其不含那些識別字**，並在 `design_agent.py` 內明寫
「兩個舊名刻意不寫在本檔內（連註解也不寫），完整說明見 code-summary.md」——一個指名
已不存在符號的註解本身就是腐化風險。第四次的處置不同：設計逐字規定的是「無 uuid／
secrets／random 的 **import**」，而我多加的原始碼文字層檢查**比設計更嚴**，代價是本模組
的說明文件不能提到自己不該 import 什麼。故閘門 2 改為純 AST 層（import 清單 ＋ `Name`／
`Attribute` 引用），它忽略註解與 docstring，但抓得到 `uuid.uuid4` 這類屬性存取。

---

## 三、Step 4 的 buffer 上界：實測值與倍數

計畫要求「先實測、上界取該數的倍數、**把測量值與倍數寫進程式註解**」，不得編一個數字。

**量法**：以 `backend/prompts/cloud_architecture_system_prompt.md` 內**它自己的官方 JSON
呼叫範例**（那是 LLM 被要求遵循的形狀，所以「典型」有依據而不是我估的）走真實的
`build_mxgraph_xml` 路徑，數 `on_progress` 的實際呼叫次數，再加上工具開頭另發的一則
「🧠 正在規劃進階架構拓樸...」。

| 範例 | nodes | `on_progress` | 一次工具呼叫的 progress 總數 |
|---|---|---|---|
| AWS | 11 | 11 | 12 |
| Azure | 17 | 17 | **18（最大）** |
| GCP | 15 | 15 | 16 |
| Azure（第二個） | 16 | 16 | 17 |

結構上 progress 則數 = `len(nodes) + 1`（`diagram_builder.py` 在每個 node 的 icon 取得
**之前**發一則），所以它隨節點數線性成長。

**上界 = 18 × 8 = 144**，在程式裡以 `_MEASURED_MAX_PROGRESS_PER_TOOL_CALL *
_BUFFER_HEADROOM_MULTIPLIER` 的**計算式**表達，使數字不可能與它的推導漂移。倍數 8 的理由
寫在註解裡：buffer 只累積尚未被 drain 取走的事件，讀取端在 graph 的每一步都會 drain，
故常態下只壓著一次工具呼叫的量；這個上界防的是**慢的或已斷線的消費者**，8 給它約八次
工具呼叫的餘裕，遠高於實務上的 1–3 次。

> 附帶一個自己的錯誤如實記下：第一版量測腳本的收尾 `print` 寫死了「三個官方範例」，而
> 它實際抽出的是 **4** 個。數字本身（18）由腳本輸出、未受影響，但那句話是手寫的。
> 寫進程式註解時用的是四筆逐列數據，不是那句話。

---

## 四、八項突變驗證的逐項結果

五個閘門檢查的都是「某個字串不存在」，而這類檢查最容易寫成恆真（pattern 寫錯就永遠找
不到，於是永遠綠）。每一項都做了：**改回錯的行為 → 跑測試 → 確認紅燈 → 還原 → 複驗
綠燈**。`M1`–`M6` 為計畫指定；`M7a`／`M7b` 為本站新增的整合測試而加（見第五節）。

**所有八項在閘門變更後都重跑過一次**（測試 9／10 的作用域在中途改過，而作用域變更正是
可能讓閘門變恆真的那種改動）。

| # | 突變內容 | 必須紅的測試 | 結果 | 紅燈訊息（節錄） |
|---|---|---|---|---|
| `M1` | 把那個共用進度佇列的宣告一行加回 `design_agent.py` | 測試 8 | **RED → 還原 GREEN** | `AssertionError: '_progress_queue' unexpectedly found in …` |
| `M2` | **只**把 `wa_collab_orchestrator` 的呼叫改回不傳新鍵（另兩處保持正確） | 測試 9 | **RED → 還原 GREEN** | `AssertionError: 'request_key' not found in set() : backend/services/wa_collab_orchestrator.py:96 的 run_design_agent 呼叫沒有傳入 request_key——該路徑的進度事件會被整批丟棄` |
| `M3` | 把 `agent_router` 的鑄造改為 `f"req-{counter}"` 形狀的遞增計數器 | 測試 10 | **RED → 還原 GREEN** | `AssertionError: False is not true : backend/services/agent_router.py:151 的鍵取值運算式 'f"req-{_mutation_counter}"' 沒有使用密碼學安全來源（允許 ('secrets.', 'uuid.uuid4', 'uuid4('…` |
| `M4` | 在 `progress_channel.py` 加一行 `import uuid` | 測試 11 | **RED → 還原 GREEN** | `AssertionError: 'uuid' unexpectedly found in {'__future__', 'logging', 'uuid', 'dataclasses', 'collections'} : progress_channel.py 不得 import uuid——本模組不鑄造鍵（U22-V5）` |
| `M5` | 把 `design_agent.py` 其中一處的固定字串改回插值形狀 | 測試 12 第一子句 | **RED → 還原 GREEN** | `AssertionError: '{e}' unexpectedly found in …` |
| `M6` | 在 `design_agent.py` 新增一個帶綁定的 `except` 區塊 | 測試 12 **第二子句** | **RED → 還原 GREEN** | `AssertionError: 1 != 0 : design_agent.py 的 'except ... as' 綁定數為 1（綁定名 ['e']），與釘住的 0 不符。…` |
| `M7a` | 拿掉 `config` dict 裡傳遞進度鍵的那一欄（接線斷在**寫入端**） | 整合測試 | **RED → 還原 GREEN** | `AssertionError: 等待「A 收到自己的 xml 事件」逾時（10 秒）。最可能的原因是 run_design_agent 一則 xml 事件都沒產出，也就是進度鍵的接線斷了…` |
| `M7b` | 把工具簽章的 `config` 改成有預設值（LangChain 因此不再注入，接線斷在**讀取端**） | 整合測試 | **RED → 還原 GREEN** | 同上 |

> **紅燈訊息內的行號是突變後的狀態。** `M3` 的訊息寫 `agent_router.py:151`，而
> clean state 的 AST `Call.lineno` 為 **150**——差的一行正是 `M3` 自己插入的
> `_mutation_counter = 0`。上表逐字引用紅燈輸出，故保留 151；要照行號去讀 clean
> state 的人請用 150。

### `M2` 與 `M6` 是這八項裡最重要的兩個

- **`M2`** 驗的是測試 9 那條「最容易寫成恆真」的斷言。若測試 9 被寫成「grep `request_key`
  有沒有出現」，`M2` **會過**（另兩處仍有該參數）。實際紅燈訊息逐字指名了
  `wa_collab_orchestrator.py:96` 這一個呼叫點——證明它是**逐點**斷言而非 grep。
- **`M6`** 是測試 12 第二子句存在的唯一理由。它新增的 handler 只有 `logger.exception`、
  沒有任何插值，所以**第一子句抓不到它**；只有第二子句（綁定數與綁定名被釘住）抓到。
  這正好證實 `C-5` 的判斷：「只有 AST 層才能完整」是假的，一條 canary 就夠。

### 突變殘留的機械複驗

八項全部還原後，以 `grep -rn "_mutation\|RunnableConfig | None = None" backend/services/
backend/test_agent.py` 掃描，**0 命中**；全套測試回到 432 綠。

---

## 五、與計畫的偏離（逐項，含兩項計畫缺陷）

### 偏離 1（**計畫缺陷**）：測試 12 第二子句的字面值 2 無法成立，釘在 **0**

計畫與 `cicd-pipeline.md` 逐字要求「`except ... as` 的綁定數等於 **2** 且兩者皆綁 `e`」，
依據是 `infrastructure-design` 實測 HEAD 當時恰有兩個 `except Exception as e`。

**那個依據在本單元落地後不再成立。** 本單元把例外原文的出口收斂成只有
`logger.exception`，於是例外物件在 `design_agent.py` 內**完全沒有使用者**，兩個 handler
都成了裸 `except Exception:`——AST 實測綁定數為 **0**。

照字面把它釘在 2，就必須寫回 `except Exception as e:` 並讓 `e` 成為未被使用的變數
——**把這道閘門要監視的那個變數當成死碼重新引入**，而 `team.md` 記載「零 TODO／死碼」是
應該保護的既有紀律。

**處置**：實作這條 canary 的**不變量**而非它的字面數字，並釘在真實值 0：

1. 子句一（形狀級四個樣式零命中）原樣保留。
2. 子句二改為兩半：綁定數等於**釘住的值（0）**，且**每一個存在的綁定都必須是子句一的
   pattern 覆蓋得到的名字**（`e`／`exc`）——後者才是 canary 真正要保護的東西，因為一個
   改名的例外變數會從四個樣式底下逃掉。

**這不是把目標放寬，是放嚴**：釘在 0 在**第一個**新綁定就紅，而釘在 2 要等到第三個。
`M6` 實測證實它會紅。常數上附完整理由，使日後有人合法新增綁定時知道該確認什麼再改數字。

### 偏離 2（**計畫缺口**）：已核可的 12 個測試沒有一個走真實的呼叫路徑

計畫列舉的 12 個測試裡，7 個直接對 registry 操作、5 個讀原始碼文字。**沒有一個經過
`run_design_agent` → LangGraph `config` → 工具 → `ProgressChannel` → `drain` 這條路。**

後果可量測：若那段接線斷掉（例如拿掉工具簽章上的 `config`、或拿掉 config dict 裡的欄位），
**12 個測試全部仍綠**——library 的行為沒變、原始碼文字的 grep 也沒變。而生產環境的症狀是
每一則事件都走 `BR3.2` 被記 ERROR 丟棄，畫面上只是沒有進度訊息、使用者看不到任何錯誤。
**那正是本單元存在要消滅的那一類安靜失敗。**

Testing Contract 的 `standard` 策略逐字要求「Unit tests plus integration tests for key
boundaries」，而 `combination_rule` 逐字「Apply every selected-strategy obligation and
every scope-floor obligation; neither replaces the other」。這就是那個 key boundary。

**處置**：在計畫自己的檔案 `test_progress_channel.py` 內新增 1 個整合測試
（`RunDesignAgentIsolationIntegrationTest`），並以 `M7a`／`M7b` 兩項突變證明它不是恆真。
替身只到 LLM 與佈局引擎為止（前例 `test_langgraph_migration.py`，US13 DoD 逐字「不需新
seam」），**工具本體與取鍵那一段走真實程式**。測試總數因此為 **13**（12 核可 ＋ 1），
全套 **432**（基準 419 ＋ 13）。

### 偏離 3：整合測試的 barrier 必須有逾時（實跑突變時才發現）

`M7a` 第一次執行時測試**卡住**而不是紅燈：接線斷掉 → 沒有 xml 事件 → `signal` 永不被 set
→ 另一邊的 `wait()` 永久等待。**在 CI 上一個卡住的測試比一個紅燈的測試糟**：它燒掉整個
job 的 30 分鐘逾時而且不會說發生了什麼。處置是把兩處 barrier 等待包進 `asyncio.wait_for`
（10 秒），逾時即以一句指名可能原因的 `self.fail` 失敗。重跑後 `M7a`／`M7b` 皆為乾淨紅燈。

### 偏離 4：測試 10 的作用域排除 `backend/tests/` 下的夾具

**這件事是測試 9 的枚舉器自己抓出來的**，而且是它正確運作的證據：整合測試落地後，枚舉器
立刻把那支測試檔認成**第四個** `run_design_agent` 呼叫點並讓測試 10 紅燈（它的 `request_key`
是函式參數，追不到指派）。這正是 `B-2` 要的行為——第四個呼叫點不會靜默逃掉。

處置：**測試 9 的作用域仍含夾具**（一個忘了傳鍵的測試本身就是壞測試）；**測試 10（鑄造
來源）排除夾具**，因為「鑄造必須是密碼學安全來源」是對**產品入口端**的要求，而夾具刻意
用固定、可讀的鍵（`integ-key-A`）好讓失敗可重現、也好直接對特定鍵下斷言。

**判別以目錄為準而非檔名前綴**，這一點是刻意的：`backend/test_agent.py` 是設計逐字點名的
三個呼叫點之一，以 `test_` 前綴判別會把這個**真實入口端**一起排除——正是這道閘門要防的
形狀。另加下限守衛：排除夾具後的呼叫點數必須仍 ≥ 3，所以若有產品入口端被搬進 `tests/`
之下，它會大聲紅而不是靜默脫離閘門。`M3` 在作用域改動後重跑仍為紅燈。

### 偏離 5：`source-manifest.json` 不在計畫的 12 步內，但 stage 要求它

`code-generation.md:73` 與 `:409` 逐字要求 review 之前寫出它，且「The engine refuses to
record the unit review without this manifest」。計畫的 Step 11／12 只列了 `code-summary.md`
與 `traceability.json`。已補寫，並以集合比對確認它與 `git status` 的變更集合相等（7 = 7）。

### 偏離 6：移除 `design_agent.py` 已無用的 `import asyncio`

本檔改完後不再使用 `asyncio`。`team.md` 記載「零死碼」是應該保護的既有紀律，故一併移除。
計畫沒有列這一項。

### 偏離 7（未偏離，但值得記）：`test_agent.py` 的 `except Exception as e` 未動

我一度把它改名為 `exc`，隨後**還原**——本單元的義務是補傳鍵，不是改這支 CLI 的錯誤處理；
那一行是印給開發者自己的終端機，不是使用者可見的回應，且測試 12 的作用域只含
`design_agent.py`。保持最小 diff。

---

## 六、測試結果與覆蓋率門檻的逐項回報

### 本單元專用指令

```
cd backend && python3 -m unittest tests.test_progress_channel -v        -> Ran 8 tests  OK
cd backend && python3 -m unittest tests.test_progress_channel_contract -v -> Ran 5 tests  OK
```

> **環境註記**：`ci.yml` 用 `python`，本機只有 `python3`（`python` 不存在於 PATH）。
> `unit-test-instructions.md §一` 記的是 `python`；兩者是同一個指令、不同的執行檔名，
> 不是偏離。

### 13 個測試逐項結果

| # | 測試 | 結果 |
|---|---|---|
| 1 | `test_two_overlapping_requests_get_disjoint_and_nonempty_event_sets` | PASS |
| 2 | `test_the_other_request_still_receives_its_events_after_one_closes` | PASS |
| 3 | `test_drain_on_a_missing_key_returns_an_empty_iterator` | PASS |
| 4 | `test_open_on_an_existing_key_raises_duplicate_channel_key` | PASS |
| 5 | `test_close_is_idempotent` | PASS |
| 6 | `test_an_abandoned_request_leaves_no_key_behind` | PASS |
| 7 | `test_capacity_pressure_drops_oldest_progress_but_never_xml_or_error` | PASS |
| 8 | `test_the_retired_module_level_state_is_gone` | PASS |
| 9 | `test_every_run_design_agent_call_site_supplies_a_request_key` | PASS（枚舉到 **4** 個呼叫點，逐點斷言） |
| 10 | `test_the_entry_points_mint_keys_from_a_cryptographic_source` | PASS（**3** 個非夾具呼叫點） |
| 11 | `test_progress_channel_contains_no_key_minting_function` | PASS |
| 12 | `test_no_exception_text_reaches_the_caller` | PASS（兩個子句） |
| +1 | `test_two_overlapping_run_design_agent_calls_keep_their_own_events`（整合，計畫外） | PASS |

### 全專案迴歸（`scope_floor` 的「Keep the existing test suite green」）

| 時點 | 指令 | 結果 |
|---|---|---|
| 改動**前**（基準） | `python3 -m unittest discover -s tests` | **Ran 419 tests — OK** |
| 改動**後** | 同上 | **Ran 432 tests — OK**（419 ＋ 13） |

`backend/tests/test_design_agent.py` 的既有 `@given`（property-based）測試**特別複驗**：
它們落在 `build_system_prompt`／`format_user_prompt` 兩個純函式上，而本單元改的是同一支檔的
模組層狀態與 `run_design_agent` 的簽章，未連帶破壞。`test_langgraph_migration.py` 的
`build_graph()` 無參數呼叫亦未受影響（這是「之一」選擇 `config` 注入而非閉包的直接理由）。

### 其他 CI 閘門（逐項實跑）

| 閘門 | 結果 |
|---|---|
| `python3 scripts/validate_repo_contract.py` | PASS |
| `python3 scripts/validate_env_contract.py` | PASS |
| `python3 scripts/validate_cost_calculator_boundary.py` | PASS |
| `python3 scripts/validate_pricing_lookup_boundary.py` | PASS |
| `backend/scripts/dump_openapi.py --check` | PASS（無新端點、回應契約未變） |
| `backend/scripts/dump_ws_contract.py --check` | PASS |
| `python3 -c "import main"`（import smoke） | PASS |

### `team.md` 三項二元可判規則的適用性

| 規則 | 判定 |
|---|---|
| A — `role_permissions` 變更需 allow／deny 雙向測試 | **不適用**：本單元不改權限矩陣，無新 story id |
| B — 新增或修改 HTTP 端點需 `TestClient` 測試 | **不適用**：無新端點；`agent_router.py` 的改動在既有端點的 generator 內部，`openapi.json` 的 drift 檢查通過即證明回應契約未變 |
| C — 前端資料形狀變更需 e2e 斷言 | **不適用**：不碰前端。SSE 的 wire 形狀 `{type, content}` 刻意保持逐字不變（`ProgressEvent.as_dict()` 是它的唯一定義處） |

### 80% 覆蓋率門檻

**不宣稱達成，也不以「已達成」記錄。** `org.md` 宣告「最低 80% line coverage」，而
`team.md` 如實記載本 repo **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／
`pytest-cov`、CI 無 coverage step）——該門檻目前**既無法量測也無法強制**。本單元
**不新增覆蓋率工具**（超出本單元範圍），故此項如實回報為**不可量測**，不是「通過」也不是
「未通過」。實際門檻是上表 A／B／C 三項，三項皆不適用，本單元的測試義務全部來自
`U22-V1`–`U22-V7`。

### PBT 判定

**不適用。** `requirements.md:630` 逐字「`FR13.2` 併發事件互斥 — **不適用 PBT**：它需要
併發編排而非輸入空間探索」。本單元四個操作全部是對共享可變狀態的操作，正確性由**交錯
順序**決定而非輸入值域，而 PBT 探索的是後者。ADR-0006 點名的三個 PBT 落點（IaC
generator、cost calculator、agent routing）皆不在本單元。

---

## 七、ADR-0006 安全基線四面向（實作層判定）

| 面向 | 判定 | 實作層的落點 |
|---|---|---|
| **IAM** | **適用——這是本單元存在的理由** | 本單元不新增受保護操作、不做授權判定。它修的缺陷本身是 IAM 面（`requirements.md:808` 的 IAM 列第 ④ 項逐字判為「跨使用者資料暴露而非單純競態」）。**處置是隔離而非加授權**：`_channels` per-key dict 使跨鍵取值需要一個不存在的操作。可見性由 `RequestKey` 的不可猜性承擔（`secrets.token_urlsafe(32)`，三個入口端皆由測試 10 斷言），`BR2.4` 的「已關閉與從未存在不可區分」是這個機制的連帶要求（測試 3 斷言兩者結果相等） |
| **Encryption** | **不適用** | 無持久化、無跨進程傳輸；事件只存在於單一行程記憶體，其後的傳輸加密屬 `U13`。本面向在本單元**沒有標的**，不是被豁免 |
| **Network exposure** | **不適用** | `library`，無獨立執行期；零 socket、零 port、零進程、零環境變數（`SEC-4`，實測 `deploy/` 與三個 `.env.example` 的 `git status` 為空）。本 intent 的兩個新增進程邊界是 Redis 與 `U21` 的 MCP server，**本單元不是其中之一** |
| **Audit logging** | **適用（三處）** | ① `publish` 到不存在／已關閉的通道記 **ERROR**（含鍵與事件類別）；② 容量丟棄或拒絕記 **WARN**（含鍵、類別、累計丟棄數）；③ 例外原文的**唯一**出口是 `logger.exception`。三處皆受 `SEC-3` 的反向約束：**不得記錄 `ProgressEvent.content`**（`xml` 是使用者的架構圖內容），測試 7 對此下斷言。如實記載：backend **無任何 metrics 基礎設施**，故「可觀察」只能是一行 Python `logging`，沒有計數器可匯出、沒有儀表板會顯示它 |

---

## 八、本單元**未能關閉**的項目（如實記載，不美化）

### `S-10`（**機讀檔內記為 `GAP`，刻意不以 OK 蓋過**）

閘門 3（形狀級例外檢查）的射程限制。第一子句的四個樣式抓不到 `"...".format(e)`、
`"..." % e`、`f"...{e.args}"` 與任何改名的例外變數；第二子句把綁定的名字與數量釘住，使
第一子句的完整性宣稱持續成立——**但它防的是「新增綁定」，不防「既有綁定被改名後仍落在
覆蓋集合內」**這類情形。要真正完整需要 AST 層的 taint 分析，成本遠高於本單元的規模，故
不做。

這是一個**已知會隨時間腐化**的閘門，而腐化是安靜的。`traceability.json` 的 `S-10` 列
狀態為 `GAP`，故 `traceability` sensor 回 `pass: false`、`findings_count: 1`、
`gaps: ["S-10"]`——**那是 sensor 正確地把一個刻意留下的限制攤出來，不是一個待修的錯誤**。
其餘五類檢查（`missing_from_table`／`missing_from_upstream_ids`／`invalid_entries`／
`invalid_targets`／`orphans`）皆為空。把 `S-10` 改成 `OK` 就能讓 sensor 變綠，而那會把
一個真實的限制從所有人的視野裡移除。

### `OQ-P2` / `FR13.4`（機讀檔內記為 `Deferred`）

`wa_collab_orchestrator` 不傳 `thread_id`，使所有 A4 共編使用者共用 `"default-thread"`。
那是**對話記憶**的共用，與進度事件錯送**是兩回事**。本單元只補進度鍵那一半，並在該呼叫點
的程式註解就地寫明另一半仍未處理及其理由。`design_agent.py` 的 `memory = MemorySaver()`
未動。**計畫明文要求刻意不夾帶這個決定**，故這不是遺漏。

### `SEC-1` 的作用域界線（非缺口，但必須寫下來）

測試 10 保證的是「**非夾具的**呼叫點都用密碼學安全來源」，不是「repo 內每一個 `request_key`
都是」。`backend/tests/` 下的夾具刻意用固定、可讀的鍵。這個界線由一條下限守衛保護（排除
夾具後的呼叫點數必須 ≥ 3），所以把產品入口端搬進 `tests/` 之下會讓測試紅燈。

### `U22-V4` 的保證範圍

`_admit` 是同步 `def`，所以「容量檢查與 buffer 變動之間無 `await`」是**語法層**保證。
它**不**保證的是：若未來有任何路徑把 `publish` 丟到 `run_in_executor` 或另一條 thread 上，
`A-P2`（單執行緒事件迴圈）這個前提即失效，**而失效是安靜的**——只會偶爾多出或少掉一則
事件。此前提寫在模組 docstring 的獨立段落內，但**沒有任何自動化會擋它**。

### 存活通道數沒有上界

單一請求的 buffer 有上界（144），**但 registry 內的存活通道數沒有**（`functional-design`
`[Q2]` 的選項 D 未被採用）。若清除契約被違反，成長由存活請求數而非單請求決定。這是一個
已知且被上游接受的殘餘面；清除契約本身由三個 `finally` ＋ 測試 6 承擔。

---

## 九、`project.md` blocking 規則的逐項對照

| 觸發條件 | 命中？ | 依據 |
|---|---|---|
| 新增／刪除／更名表 | **否** | 本單元無任何表 |
| 新增／刪除／更名／改型欄位 | **否** | 同上 |
| 索引／唯一約束／外鍵變更 | **否** | 同上 |
| seed／預設資料語意變更 | **否** | 不碰 `role_permissions`；無新 story id |
| ORM／啟動補丁引入新 DDL | **否** | 不碰 `models.py`／`database.py` 的 `_ensure_*` 家族 |
| 新增 compose 消費的環境變數 | **否** | `SEC-4`；`validate_env_contract.py` 通過 |
| 異動 `database.py` schema 補丁／`deploy/nginx.conf`／任一 `.env.example`／`render-env.sh` | **否** | 實測這些路徑的 `git status` 為空 |

**七項皆未命中**，故 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步與 `LOCAL-DEV.md`
的同步義務皆不適用於本單元。
