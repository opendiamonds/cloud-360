# Unit Test Instructions — `U11 intent-router`

> Test strategy: **standard**（每元件 5–8 個測試 ＋ 關鍵邊界的整合測試）。
> Methodology: **test-after**（每層實作完成後，寫並跑該層的測試）。
> 兩者皆來自 `code-generation-plan.md` 內嵌的 Testing Contract，**不得在此重新解讀**。

## 一、測試框架（既成事實，零新依賴）

| 項目 | 內容 | 來源 |
|---|---|---|
| 框架 | Python 內建 **`unittest`**（**不是 pytest**） | `team.md` Testing Posture 既成事實 |
| Property-based | **`hypothesis`**（已在 `backend/requirements.txt`） | 同上 |
| 替身 | `unittest.mock`（標準庫） | 同上 |
| 測試 DB | 不需要。本單元不碰 DB——它只透過 `MemoryFacade` 讀，而該 facade 在測試中以替身取代 | 本單元 `SEC-2`／`NFR6.60` |
| 新增依賴 | **零** | `nfr-requirements/tech-stack-decisions.md` 的 `TS-5` |

**每個新測試檔的第一行 import 必須是**（`team.md` 既成事實，避免真實 DB driver 被載入）：

```python
import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import
```

## 二、本單元的測試執行指令（**scoped，不得用專案層指令**）

```bash
cd backend
python3 -m unittest -v \
  tests.test_intent_routing_predicate \
  tests.test_intent_routing_parser \
  tests.test_intent_routing_context \
  tests.test_intent_routing_port \
  tests.test_intent_routing_structure
```

**三點說明：**

1. **`python3`，不是 `python`** —— 本機 `python` 不在 PATH 上（本 session 實測）。
2. **指令已 scoped 到本單元的五個測試模組**。stage 檔逐字禁止 `npm test` 這類
   專案層指令：`build-and-test` 會對**每個單元**各跑一次它的指令，未 scoped 的
   指令會讓整套測試被重跑 N 次。
3. **這個指令在第一個測試步驟之前就必須可執行**（Testing Contract 的
   `runner_ready_before_first_test: true`）。本 repo 是 brownfield，runner 已存在
   ——Plan 的 Step 2 是**驗證**它可跑，不是建立它。

### 驗證 runner 可用（Step 2 的具體動作）

```bash
cd backend
python3 -m unittest -v tests.test_langgraph_runtime
```

既有測試檔，應全綠。綠燈即證明 runner、`tests.helpers` 的 stub、import 路徑都正常。

### 合併前必修第 5、13 項（Request Changes 修訂，計畫 §五之一）

本機一律以 `backend/.venv/bin/python`（系統 Python 套件版本與 `requirements.txt` 不一致），並加 `PYTHONDONTWRITEBYTECODE=1`。

| 項 | 落點 | 案例（通過條件） |
|---|---|---|
| #5 | `tests/test_intent_routing_predicate.py` 或 `_context`（產生端） | 澄清判定附帶的行程內對照：每個候選 id 對應的 `Intent` 含原 `referent`；其他已確定槽位的 `Intent` 齊備；同輸入兩次結果相同（決定性） |
| #5 | `brain-gateway` 既有測試檔（`_on_select`） | 單槽位選定 → 派送的 `Intent` 帶原 `referent`；多槽位選定 → 兩個意圖都被派送且順序與原句一致；`candidateId=None` 仍安靜結束；非候選 id 仍 `INVALID_REQUEST` |
| #13 | `tests/test_intent_routing_context.py` | facade 拋 `MemoryForbidden` → 向上傳遞、不降級；拋一般例外 → `memory_degraded` 為真 |
| #13 | `brain-gateway` 既有測試檔 | 記憶授權拒絕 → 本輪以授權類錯誤碼結束、不派送；日誌不含輸入原文 |

突變（每項先 `grep -c` 確認寫入、還原後為 0）：`_on_select` 還原為 `Intent(capability, None)` → #5 案例紅；`MemoryForbidden` 併回 `except Exception` → #13 案例紅。完整套件：`cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests`。

## 三、每個元件的測試範圍（standard：5–8 個／元件）

### `test_intent_routing_predicate.py` —— L5 純函式（**ADR-0006 的 PBT 落點**）

**這是本單元唯一的 hard-constraint 測試檔。** `ADR-0006` 逐字點名 **agent routing**
須有 property-based 測試，而 `contract-summary.md:797-799` 的 `pbt_note` 指定受測
對象是「門檻比較這個純函式」。

七條 property（`functional-spec.md` §五），**全部用 `@given`**：

| # | Property | 備註 |
|---|---|---|
| `P1` | `can_single_out` 為假 ⇒ `intents` 空且 `candidates` 非空 | 不涉分數 |
| `P2` | 為真 ⇒ `intents` 非空且 `candidates` 空 | 不涉分數 |
| `P3` | 單一候選 ⇒ 為真 | 不涉分數 |
| `P4` | `scoresAvailable` 為真時，提高最高分不使述詞由真變假（單調） | **僅在有分數分支** |
| `P5` | 對任何合法 ranking 回傳布林值，不 raise | `BR8.3` |
| `P6` | 每槽位皆可單選 ⇒ `len(intents) == len(slots)`，第 i 個取第 i 槽位 `rank == 1` | `EC7`／`BR4.4` |
| `P7` | 任一槽位不可單選 ⇒ `intents` 空，且 `candidates` 含每個失敗槽位至少一個候選 | `EC8`／`BR4.5` |

**生成策略的兩個硬性要求**（`nfr-design/performance-design.md` §五，審查 `R-06`）：

- `scoresAvailable` **必須由 `st.booleans()` 顯式驅動**，不得讓「分數存不存在」
  隨機浮現。否則 `BR3.3`（無分數分支）與 `P3` 可能長期零覆蓋而無人察覺——
  Hypothesis **不會**因為某個分支從未被抽到而報錯。
- `len(slots)` **必須顯式涵蓋 1 與 ≥2 兩種情形**，否則 `P6`／`P7` 只會在單槽位上
  被驗證，而多意圖正是 `functional-design` 審查 `R-01` 的失敗情境所在。

另加 example-based：`BR3.2` 的門檻邊界（恰等於門檻時為真）、`BR3.3` 的並列判定。

### `test_intent_routing_parser.py` —— L4 純函式

五道驗證各至少一個 negative case ＋ 一個 happy path：

| 測試 | 斷言 |
|---|---|
| `V-1` 空候選 | raise `EmptyCandidates`（**不是** `MalformedRouting`） |
| `V-2` `capability` 不在封閉列舉 | raise `MalformedRouting` |
| `V-3` `slot` 不從 0 連續／超過上界 | raise `MalformedRouting`（**不得截斷**） |
| `V-4` 組內 `rank` 不從 1 連續或重複 | raise `MalformedRouting` |
| `V-5` 部分候選有分數 | **不 raise**；整張清單 `scoresAvailable=False`（降級到 `BR3.3`，不是失敗） |
| happy path | 扁平 2 槽位 × 2 候選 → 還原成 `ClassificationResult` 且分組正確 |

**`V-5` 與前四者的差別必須被測出來**：它是降級不是失敗，而那是 `[IR1]`=A 的設計收益。

### `test_intent_routing_context.py` —— L2 純函式（**無需 mock**）

| 測試 | 斷言 |
|---|---|
| 最少上下文 | 組出的 prompt **不含**完整 `messageHistory`（只含最後 K 則） |
| `BR5.3` 優先序 | 輸入中點名的對象出現在 prompt 中且優先於 session 當前值 |
| 能力清單 | 封閉列舉完整出現 |
| 長度上界 | 超長歷程被截到 K 則，且 prompt 長度不隨歷程線性成長 |
| 型別邊界 | 函式簽章**不接受** `BrainSession` 整個物件（`NFR9.60`：拿不到就送不出去） |

**它是純函式，所以這五個測試一個 mock 都不需要**——這正是 `logical-components.md`
§二 把 I/O 放在 L0 的理由，`R-01` 修訂後的分層使它成立。

### `test_intent_routing_port.py` —— L3（替身）

| 測試 | 斷言 |
|---|---|
| 逾時 | raise `LlmUnavailable` |
| 5xx | raise `LlmUnavailable` |
| 429 | raise `LlmUnavailable`（**不重試、不排隊**，`NFR9.62`） |
| 連線失敗 | raise `LlmUnavailable` |
| 零重試 | 替身被呼叫**恰一次**（`NFR3.63`） |
| 單次呼叫 | 一輪 `classify` 內模型被呼叫**恰一次**（`NFR3.62`） |
| `temperature` 省略 | 送出的 kwargs **不含** `temperature`（`TS-3a`：Jev 的 `supported_parameters` 為空陣列） |

### `test_intent_routing_structure.py` —— 結構斷言（跨層）

這些不是行為測試，是**把設計決定變成會紅的東西**：

| 測試 | 斷言 | 來源 |
|---|---|---|
| 禁 import（身分） | 模組原始碼不含 `get_current_user`／`Request`／`ContextVar` | `SEC-1` |
| 禁 import（記憶） | 不含 `memory_service`／DB session 型別 | `NFR6.60` |
| 無端點 | 不含 `APIRouter`、未被 `main.py` `include_router` | `SEC-2` |
| 不直打 httpx | 模組不 `import httpx` | `SEC-2` |
| 不寫 session | 不含 `set_work_target`／`append_message`／`set_sharing_mode`／`touch` | `BR7.4` |
| `kinds` 排除情節 | `MemoryFacade.search` 的實際傳值等於模組層常數，且不含 `episodic` | `NFR7.62`（**現行防護**） |
| 模組層無可變綁定 | AST 掃描：無 module-level `dict`／`list`／`set`（白名單排除 client factory） | `NFR3.67`／`S-3` |
| 日誌白名單 | `RoutingObservation` 的欄位集合**不含** `text`／`label`／`referent` | `SEC-3`／`SEC-5` |

## 四、覆蓋率目標

| 項目 | 目標 | 現況 |
|---|---|---|
| 行覆蓋率 | `org.md` 宣告 **80%** | **本 repo 無任何覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`、CI 無 coverage step）——`team.md` 逐字記載它「既無法量測也無法強制，是宣告而非閘門」 |
| 實際門檻 | `team.md` 的 A／B／C 三項規則 | **A** 不適用（本單元不改 `role_permissions`）；**B** 不適用（本單元無 HTTP 端點，`SEC-2`）；**C** 不適用（本單元無前端） |

**所以本單元的實際測試底線就是上面三節列出的具體測試**，不是一個無法量測的百分比。
**不得**為了讓某一步過關而調低任何目標——有缺口就寫出來（stage 檔 Critical Rules 逐字）。

## 五、Mocking／Stubbing 指引

| 對象 | 做法 |
|---|---|
| `MemoryFacade` | `unittest.mock.MagicMock`，並**斷言 `search` 的 `kinds` 引數** |
| `SessionStore` | `MagicMock`；另有一個測試斷言**沒有任何寫入方法被呼叫** |
| 模型 client | 替身取代 `router_chat_model` 的回傳；**不得真的打 OpenRouter**（會花錢且 CI 無金鑰） |
| L2／L4／L5 | **不 mock**——它們是純函式，直接給輸入驗輸出 |

**本單元的測試一律不需要 `OPENROUTER_API_KEY`**，與既有 LLM 測試的做法一致
（`test_a3_langgraph_migration.py:6` 檔頭逐字「Mock `ChatOpenAI` / compiled graph;
no real `OPENROUTER_API_KEY`」）。

## 六、測試資料管理

- 候選／槽位的測試資料以 **Hypothesis strategies** 產生（predicate 層）或**行內
  字面值**（parser／context 層），不建共用 fixture 檔——本單元的資料形狀簡單且
  各層需要的形狀不同，共用 fixture 會讓測試互相耦合。
- **不使用 DB、不使用 Redis、不使用網路。** 本單元的全部測試都是行程內的。
