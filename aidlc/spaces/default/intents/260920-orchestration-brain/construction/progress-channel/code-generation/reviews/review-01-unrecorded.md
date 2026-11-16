<!-- 這份副本在稽核紀錄上沒有 REVIEW_COMPLETED 收據，而原因是 conductor 的流程錯，
     不是審查本身有問題。審查確實跑過（NOT-READY，0 Critical／3 Major／2 Minor），
     逐項發現全部有效，且它讀的是**當前**位元。

     發生了什麼：conductor 在 2026-10-04T04:42:57Z 記錄 REVIEW_REQUESTED，當時
     developer agent 還沒跑完——conductor 看到 code-summary.md 出現就誤判它結束了。
     該 agent 在 8 秒後（04:43:05Z）又改了兩個檔（progress_channel.py 的一處 docstring
     更正、code-summary.md 的一處註記），於是 output documents 在請求之後變了，引擎
     正確地拒絕記錄議決：「Cannot record the verdict ... because its output documents
     changed after review iteration 1 started.」

     為什麼不照引擎建議的「還原被派工時的位元」：審查在 04:54:35Z 完成，讀的是編輯
     **之後**的狀態。還原到 04:42:57Z 的位元會讓收據綁到審查沒讀過的內容——比缺收據更糟。

     為什麼沒有 iteration 2：`Review Override: advisory` 把本站上限設為 1 次審查，
     引擎回 REVIEW_BUDGET_EXHAUSTED，唯一授權的補救是重啟整站（requiresHuman）。

     使用者裁決：保留為未收據副本、發現帶進閘門，不花重啟整站的代價。本 intent 已有
     同形先例（hierarchy-data/nfr-design/reviews/review-01-unrecorded.md），上次的裁決相同。
     檔名帶 -unrecorded 是刻意的，避免被誤讀成正式收據的副本。

     conductor 的教訓已記入 construction/code-generation/memory.md：這是本 session
     第三次踩「送審請求與產出變更的時序」，前兩次記的是「請求之後不得改產出」，
     這一次的新形狀是**請求之前要先確認派工的 agent 真的結束了**——它的中間產物出現
     不等於它完成。可執行判準：只在收到 agent 的完成通知之後才記錄 REVIEW_REQUESTED。 -->

## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-04T04:54:35Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `backend/services/progress_channel.py` > `ProgressChannelRegistry.publish`，條件 `if channel is None or not channel.is_open:` | `not channel.is_open` 這一支**可證明不可達**。`close()` 先 `self._channels.pop(key)` 再設 `channel.is_open = False`，兩者在同一個**同步**函式內、中間無 await 點；`open()` 建立的通道一律 `is_open=True`。因此 `self._channels.get(key)` 取回的通道必定 `is_open is True`，該子句永不為真。這是一個新的「寫了但這個讀取點讀不到」分支，而本單元的完成判準有一半正是退場同類形狀；`team.md` 另把「零死碼」列為應保護的既有紀律。附帶：`traceability.json` 的 `BR3.2` 列 note 逐字引用這個複合條件作為該規則已實作的證據 | 把 `publish` 的條件收斂為 `if channel is None:`，並把 `is_open` 的註解限定為「唯一讀者是 in-flight 的 `drain` 迭代器」；或若認為此分支有可達路徑，寫出那條路徑並補一個使它為真的測試 | New |
| R-02 | Major | `backend/services/progress_channel.py` > `ProgressChannelRegistry.drain`，`while channel.is_open and channel.buffer:`；`code-summary.md` §二之三 | `is_open` 作為 `drain` 迴圈守衛**沒有任何測試涵蓋**。我實測：同時把 `drain` 的 `while channel.is_open and` 與 `publish` 的 `not channel.is_open` 一併移除，`python3 -m unittest discover -s tests` 仍為 **Ran 432 tests — OK**。`code-summary.md` §二之三 以「它的讀者是 in-flight 的 drain 迭代器」把 `is_open` 與本單元正在退場的死狀態區分開——該敘述在字面上成立（程式確實讀它），但**沒有任何測試或突變能分辨它在或不在**，而本單元對其餘五個「某物不存在」的宣稱都做了突變驗證。缺口形狀與 `R-03` 同類：宣稱已覆蓋、實際無人驗 | 補一個行為測試：一個 in-flight 的 `drain` 在兩次 `yield` 之間被 `close(key)` 之後必須停止吐事件（`anext` 一次 → `close` → 斷言後續為空）；或在 `code-summary.md` §八 如實記為「已實作、未驗證」並同步 `traceability.json` | New |
| R-03 | Major | `backend/services/progress_channel.py` > `publish` 的 `logger.error`；`traceability.json` > `coverage` 的 `BR3.2` 列 | `BR3.2` 的「**不靜默**」那一半未被驗證。我實測：把 `publish` 內整段 `logger.error(...)` 刪除（只留 `return`），全套測試仍為 **Ran 432 tests — OK**。`traceability.json` 把 `BR3.2` 記為 `OK`，其 note 只引用程式位置；對照之下 `BR4.2` 列明確引用測試 7 的 `assertLogs`，兩者的證據強度不同卻同記 `OK`。要緊之處在於 `code-summary.md` 自己指出 `M7a` 的生產症狀就是「每一則事件都走 `BR3.2` 被記 ERROR 丟棄」——這行 ERROR log 是清除契約被違反後**唯一**的痕跡，而它自己沒有痕跡 | 以 `with self.assertLogs("cloud360.progress_channel", level="ERROR")` 對「publish 到從未存在的鍵」與「publish 到已 close 的鍵」各補一個斷言（並斷言 log 不含 `content`，與測試 7 同形）；或把 `BR3.2` 的 status 由 `OK` 改為部分覆蓋並說明未覆蓋的是哪一半 | New |
| R-04 | Minor | `backend/tests/test_progress_channel_contract.py` > `RunDesignAgentCallSiteTest.MINIMUM_KNOWN_CALL_SITES` 與 `_is_test_fixture` | 測試 10 的夾具排除**只擋「移出」不擋「移入」**。下限守衛（排除夾具後 ≥ 3）會在產品入口端被搬進 `tests/` 時紅燈，我已實測現值恰為 3（`backend/test_agent.py`、`agent_router.py:150`、`wa_collab_orchestrator.py:96`），守衛有效。但一個**新增**的產品入口端若直接寫在 `tests/` 目錄之下，非夾具計數仍為 3、測試仍綠，該入口端的鑄造來源靜默脫離閘門。排除本身的理由（鑄造要求針對產品入口端、夾具刻意用固定可讀鍵）是對的，`code-summary.md` §八 也已寫下界線——缺的是守衛的方向只有一邊 | 把守衛改為「非夾具呼叫點數 == 全部呼叫點數 − 已知夾具檔數」，並把已知夾具檔以明寫清單表達，使新增夾具必須被人為登記一次 | New |
| R-05 | Minor | `code-summary.md` §一「新建（3）」表 > `backend/services/progress_channel.py` 的行數欄 | 該欄記 `346`，實測 `wc -l backend/services/progress_channel.py` 為 **351**（同表另兩列 432／429 皆與實測相符）。本 record 的 `project.md` 已有「可以被計算的數字先算再寫」與「計數腳本是收尾動作」兩條規則，此處屬同形的收尾漂移 | 改為 351，或改以指令輸出代入 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `cd backend && python3 -m unittest discover -s tests` | **Ran 432 tests — OK** | 與 dispatch 的量測一致。我在本輪共套用並還原 5 項突變，每次還原後皆複驗，最終狀態亦為 432 綠 |
| `python3 -m unittest tests.test_progress_channel tests.test_progress_channel_contract` | **Ran 13 tests — OK** | 證實 `432 = 419 + 13`，`code-summary.md` §六 的基準數正確 |
| 突變 `M2`（只改 `wa_collab_orchestrator` 的呼叫，另兩處保持正確）| **RED → 還原 GREEN** | 紅燈訊息逐字為 `'request_key' not found in set() : backend/services/wa_collab_orchestrator.py:96 …`，**逐點指名該呼叫點**。這證實測試 9 是逐點斷言而非 grep；單元的主要宣稱成立 |
| 突變 `M6`（新增一個帶綁定、且**無任何插值**的 `except Exception as e` 區塊）| **RED → 還原 GREEN** | `AssertionError: 1 != 0 …綁定名 ['e']`。我刻意讓該區塊只含 `logger.exception`，故第一子句抓不到它——紅燈完全來自第二子句，證實 `C-5` 的「只有 AST 層才能完整」為假、一條 canary 已足 |
| 突變 `M7a`（移除 `config["configurable"]` 內的鍵欄位）| **RED（整合測試，10.018s）→ 還原 GREEN** | 逾時失敗訊息指名了兩個可能斷點。**更關鍵的複驗**：在 `M7a` 之下單獨跑已核可的 12 個測試回 **Ran 12 tests — OK**，實證「接線斷掉時 12 個測試全綠而生產靜默丟棄全部事件」——偏離 2 指出的計畫缺口是真的 |
| 突變（我自行新增）：同時移除 `drain` 與 `publish` 的 `is_open` 守衛 | **GREEN（432）** | 支撐 `R-01`／`R-02` |
| 突變（我自行新增）：刪除 `publish` 的 `logger.error` | **GREEN（432）** | 支撐 `R-03` |
| AST 複驗 `design_agent.py` | `except` handler 2 個、`except ... as` 綁定 **0** 個 | 與測試 12 釘住的 `EXPECTED_EXCEPTION_BINDINGS = 0` 一致 |
| AST 複驗 `_admit` | `FunctionDef`（非 `AsyncFunctionDef`）、`ast.Await` 節點 **0** 個 | `U22-V4` 的語法層保證成立 |
| AST 枚舉 `run_design_agent` 呼叫點（全 repo）| **4** 個，全部帶 `request_key`：`backend/test_agent.py:53`、`backend/tests/test_progress_channel.py:363`、`agent_router.py:150`、`wa_collab_orchestrator.py:96` | 與 `code-summary.md` §六 的「4 個／3 個非夾具」逐字相符 |
| 退場符號純文字掃描 | 兩個舊全域名、`{e}`／`{exc}`／`str(e)`／`repr(e)` 皆 **0** 命中 | `BR5.1`、`BR3.1`／`SEC-2`／`AC13.1.3` 的可 grep 條件成立 |
| `memory = MemorySaver()` | 命中 1 次（現位於 `design_agent.py:211`，原契約引用的 `:169` 為改動前行號）| `K-18` 的 `保留` disposition 已遵守 |
| LangChain 工具 schema 實測 | `draw_architecture_diagram.args` == `['edges','groups','nodes','provider']` | `config` 確實**不在** LLM 看到的 schema 內，`code-summary.md` §二之一 的實測宣稱可複驗 |
| `git diff --stat backend/` | `41` / `141` / `67` / `21` 行變動 | 與 §一 修改表的 `+38/−3`、`+105/−36`、`+44/−23`、`+19/−2` 四組逐一加總完全相符（亦同時證明我的突變已完全還原）|
| `md5` 比對（`design_agent.py`、`progress_channel.py`、`wa_collab_orchestrator.py`）| 與突變前備份**逐位元相同** | 本輪所有突變已完全還原 |
| 零新依賴／零 CI 變更 | `git status --short -- backend/requirements.txt .github/ deploy/ schema_rbac.sql DEPLOY.md LOCAL-DEV.md` 為**空** | `project.md` 的 blocking 同步規則五個觸發條件逐項未命中，判定正確；`progress_channel.py` 的 import 僅 `logging`／`collections.deque`／`collections.abc`／`dataclasses`／`__future__`，皆標準庫 |
| `threading` 與 `sleep` 掃描 | `progress_channel.py` 無 `import threading`（2 處命中皆在 docstring 的「刻意不照抄」說明內）；兩支測試檔的 `sleep` 3 處命中皆在 docstring | `K-18` 的 `do_not_follow`（不照抄 `threading.Lock`）與 `BR5.2`（不得以 `sleep` 製造交錯）皆成立 |
| logger 命名 | `logging.getLogger("cloud360.progress_channel")` | 符合 `team.md` 的「新模組一律 `cloud360.<module>`」，未沿用 `design_agent.py` 的 `__name__` |
| `MAX_BUFFERED_EVENTS` 實測載入值 | **144** = `18 × 8`，且 `diagram_builder.py:2023-2031` 實為「每個 node 的 icon 取得前發一則」 | 上界的推導式與實測依據（`len(nodes) + 1`）皆可複驗，非編造 |
| `K-18` 四個方法的 `form` 實測 | `open`／`close` 非 coroutine（sync）；`publish` 為 coroutine；`drain` 為 async generator，回 `AsyncIterator[ProgressEvent]`；registry 為 per-key `dict` | 契約逐條相符 |
| `traceability.json` 雙向比對 | `upstream_ids` 36、`coverage` 36；雙向差集皆為空；34 `OK`／1 `Deferred`（`OQ-P2`）／1 `GAP`（`S-10`）| 無孤兒、無漏列。`S-10` 刻意記為 `GAP` 使 sensor 回 `pass: false`，是誠實而非缺陷 |
| `FR13.4`／`thread_id` 語意 | `agent_router.py:153` 仍為 `f"user-{current_user.id}-design"`；`wa_collab_orchestrator.py:96` 仍不傳 `thread_id`（沿用 `"default-thread"`）；`test_agent.py:54` 仍傳 `thread_id` | **未夾帶** `FR13.4` 的分區決定，符合計畫 §四 |

### Summary

**程式本身是可出貨的，五項發現沒有一項會造成使用者可見的缺陷；三項 Major 全部是「宣稱已覆蓋、實際無人驗」或「新引入的不可達分支」，落在本單元自己最嚴的那條紀律上。** 我獨立複驗了 dispatch 表列的七項事實，全部成立；另實跑 `M2`、`M6`、`M7a` 三項既有突變與兩項自創突變，全部與 `code-summary.md` 的記載一致（含紅燈訊息逐字），並在每次還原後以 md5 與 432 綠雙重確認。突變驗證**站得住**——`M2` 的紅燈逐字指名 `wa_collab_orchestrator.py:96` 這一個呼叫點，那是「逐點斷言而非 grep」的直接證據，也是本單元主要宣稱的承載者。

四項揭露偏離逐一判定：**偏離 1（綁定數釘 0 而非計畫的 2）成立且確實更嚴**——釘 2 只在第三個綁定出現時才紅，釘 0 在第一個就紅，而我的 `M6` 刻意寫成無插值的 handler，紅燈完全由第二子句產生，證實它不是放鬆而是收緊；它的盲點已被誠實記載（`.format(e)`／`% e`／`{e.args}` 能從第一子句逃掉），但另有一處未記下的盲點：第二子句防不住**零綁定**的洩漏（`traceback.format_exc()`／`sys.exc_info()`），且整道閘門的作用域只含 `design_agent.py`，`agent_router.py` 與 `wa_collab_orchestrator.py` 新增的兩個 handler 不在其中（兩者目前皆為固定訊息，已逐一讀過）。**偏離 2 是四項裡最有價值的一項，而且是真的**：整合測試的替身只到 LLM 與佈局引擎，`config` 寫入 → `ToolNode` 注入 → 工具取鍵 → `publish` → `drain` 整段是真實程式（我以 `draw_architecture_diagram.args` 實測確認 `config` 不在 LLM schema 內、確為注入），而我在 `M7a` 之下單跑那 12 個已核可測試回 12 綠——計畫缺口的證明無可爭辯。**偏離 3 的逾時處置正確且其宣稱有收斂**：程式註解只把逾時限定在「接線斷掉」這個失敗模式，而我驗證兩處 `asyncio.Event` 等待都走同一個 `_await_barrier`、`M7a`／`M7b` 兩端皆轉為指名的 10 秒失敗；它**不**涵蓋 `graph.astream` 自身卡住這類非 barrier 的懸掛，但程式與摘要都沒有宣稱到那麼廣，故不記為發現。**偏離 4 的排除方向是對的**（鑄造要求針對產品入口端、夾具需要固定可讀的鍵才能斷言），下限守衛也真的有效，但守衛只有一邊，見 `R-04`。

**我會放在人面前的第一項是 `R-02` ＋ `R-03` 合起來看的那件事**：這個單元的全部方法論是「每一條『某物不存在』的宣稱都要以突變證明不是恆真」，而它新引入的兩個狀態讀取點——`is_open` 守衛與 `BR3.2` 的 ERROR log——我各刪一次、432 測試都不動。`BR3.2` 那一條尤其值得一看：`code-summary.md` 自己說接線斷掉的生產症狀就是「每一則事件都走 `BR3.2` 被記 ERROR 丟棄」，所以那行 log 是清除契約被違反後唯一查得到的痕跡，而 `traceability.json` 以 `OK` 記它、憑的只是程式存在。補法是兩個 `assertLogs` 斷言與一個 in-flight drain 測試，成本小於本輪任一項突變驗證；`R-01` 則是一行條件的收斂。三項 Major 使機械判準落在 NOT-READY（本輪為 advisory，不構成閘門），但這是一份高品質的交付：上游四個設計站留下的三個 Critical（三個呼叫點只列一個、兩處例外原文洩漏點、`DuplicateChannelKey` 會經 `:216` 流向使用者）我逐一複驗為**已關閉**，`K-18` 的四個方法與六項 `replaced_existing_symbols` disposition 逐條相符，`project.md` 的 blocking 觸發條件判定為不適用也經實測成立。
