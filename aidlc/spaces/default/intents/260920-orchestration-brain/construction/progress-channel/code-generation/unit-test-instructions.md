# 單元測試指示 — `U22` `progress-channel`

> Stage：`code-generation`（3.5）　Test strategy：**`standard`**（每元件 5–8 測試 ＋
> 關鍵邊界的整合測試）　Methodology：**`test-after`**（實作每一層，然後寫並跑該層的測試）
>
> 兩者皆由 `bun .claude/tools/aidlc-testing-posture.ts render` 的 Testing Contract 決定，
> 完整 JSON 逐字貼於 `code-generation-plan.md`。

---

## §一 Runner 就緒（第一個可執行測試步驟之前必須完成）

**本單元是 brownfield，runner 已存在，故本節是「驗證」而非「建置」。**

**精確的 unit-scoped 指令**（寫進本檔是 Testing Contract 的要求）：

```bash
cd backend && python -m unittest tests.test_progress_channel -v
```

**全套指令**（CI 跑的那個，`ci.yml` 的 `backend` job 步 7）：

```bash
cd backend && python -m unittest discover -s tests -v
```

**驗證要點**（在寫第一個測試之前確認）：

1. `backend/tests/` 下的新檔會被 `discover` 自動撿到——**無需任何 CI 設定變更**。
   這是 `[Q1]`=A（`infrastructure-design`）的全部價值。
2. 框架是 Python 內建 `unittest`，**不是 pytest**（`team.md` `## Testing Posture` 的既成事實）。
3. 併發測試用 `unittest.IsolatedAsyncioTestCase`。前例：
   `backend/tests/test_langgraph_migration.py`（patch `ChatAnthropic`／`build_graph`／
   `build_system_prompt`／`format_user_prompt`）——US13 DoD 逐字「**不需新 seam**」。
4. 讀原始碼文字的契約測試前例：`backend/tests/test_hierarchy_migration.py:454` 的
   `test_schema_rbac_sql_matches_migration_ddl`（由 `U4` 交付、現在就在跑）。
5. **零新依賴**：`collections.deque`、`dict`、`unittest`、`asyncio` 皆標準庫；
   `backend/requirements.txt` 不變。

---

## §二 測試檔與測試清單

兩支新檔。數量按 `standard` 策略的每元件 5–8 測試。

### `backend/tests/test_progress_channel.py` — 行為測試（7 個）

| # | 測試 | 斷言 | 承載 |
|---|---|---|---|
| 1 | `test_two_overlapping_requests_get_disjoint_and_nonempty_event_sets` | 以 `asyncio.Event` barrier 釘住交錯順序；A 與 B 的事件集合**互斥且各自非空** | `AC13.1.1`、`U22-V1`、`BR1.3` |
| 2 | `test_the_other_request_still_receives_its_events_after_one_closes` | B 先 `close`，A 的工具其後 `publish`，A 仍取得自己的事件 | `AC13.1.2`、`BR2.4` |
| 3 | `test_drain_on_a_missing_key_returns_an_empty_iterator` | 不存在的鍵 `drain` 回空迭代器、**不拋例外**；已關閉與從未存在**行為不可區分** | `BR2.4` |
| 4 | `test_open_on_an_existing_key_raises_duplicate_channel_key` | 同鍵重複 `open` 拋 `DuplicateChannelKey`，且**不覆寫**既有通道（原通道的事件仍可取出） | `BR1.2` |
| 5 | `test_close_is_idempotent` | 對已關閉或不存在的鍵重複 `close` 視為成功 | `BR2.2` |
| 6 | `test_an_abandoned_request_leaves_no_key_behind` | 關閉回應 generator 而非跑完，斷言 registry 不含該鍵 | `AC13.1.2` 的異常路徑、`BR2.3`、`U22-V2` |
| 7 | `test_capacity_pressure_drops_oldest_progress_but_never_xml_or_error` | buffer 滿載時丟最舊的 `progress`；`xml` 與 `error` **永不丟棄**；丟棄留下 WARN log | `BR4.1`、`BR4.2`、`U22-D6` |

**關鍵紀律（`BR5.2`）**：交錯順序一律以 `asyncio.Event` barrier 釘住，**不得以 `sleep`
製造**。品質 agent 已實測 `sleep` 版本**會通過**（假綠燈），而
`frontend/playwright.config.ts:17` 的 `retries` 與 `ui-regression` 都容忍 flaky
——一個 flaky 的併發測試等於沒有測試。

**測試 1 的「各自非空」不可省**：開發者實跑顯示現狀下 A 的事件集合為**空**而 B 收到
A 的產出，於是「互斥」在壞碼上**真空成立**——只斷言互斥會通過。

### `backend/tests/test_progress_channel_contract.py` — 契約閘門（5 個）

讀原始碼文字並斷言。形狀沿用 `test_hierarchy_migration.py:454`。

| # | 測試 | 斷言 | 承載 |
|---|---|---|---|
| 8 | `test_the_retired_module_level_state_is_gone` | `design_agent.py` 內 `_progress_queue`／`_last_xml` 零命中；無「把全域設為 `None`」那一行 | `U22-V3`（1a–1c）、`BR5.1` |
| 9 | `test_every_run_design_agent_call_site_supplies_a_request_key` | **先以 repo 範圍搜尋枚舉出全部呼叫點**（不得硬寫路徑清單），再逐點斷言每一個都帶新參數 | `U22-V3`（1e）、`S-2`、**閘門 `B-2` 的修法** |
| 10 | `test_the_entry_points_mint_keys_from_a_cryptographic_source` | 全部三個呼叫點的鑄造端使用 `uuid4` 或 `secrets`，**不得**為遞增計數器／時間戳／`random`／由使用者 id 推導 | `SEC-1`、`U22-V7`、**閘門 `B-3` 的修法（含 `test_agent.py:41`）** |
| 11 | `test_progress_channel_contains_no_key_minting_function` | `progress_channel.py` 內無 `uuid`／`secrets`／`random` 的 import，無任何回傳新鍵的函式 | `U22-V5` |
| 12 | `test_no_exception_text_reaches_the_caller` | `design_agent.py` 內對 `{e}`／`{exc}`／`str(e)`／`repr(e)` 零命中；**並且** `except ... as` 的綁定數等於 **2** 且兩者皆綁 `e` | `SEC-2`、`S-7`、`AC13.1.3`、**閘門 `C-5` 的修法** |

**測試 9 是本組的實質內容，也最容易寫成恆真。** 寫法必須是「**枚舉後逐點斷言**」而非
「grep 新參數有沒有出現」——後者在只改一處時也會過。這是 `infrastructure-design`
審查 `R-02` 指出的空隙：原規格指定了形狀但沒指定「總數從哪裡來」，硬寫三個路徑則
第四個呼叫點會靜默逃掉。

**測試 12 的第二個子句是本計畫新增的**。`infrastructure-design` 的產出宣稱「只有 AST 層
檢查才能完整」——那是**假的**（審查 `R-07`）。斷言 `except ... as` 綁定數等於 2、且兩者
都綁 `e`，第三個 `except` 落地時閘門就會紅。把安靜腐化變成大聲腐化，成本為零。

---

## §三 突變驗證（本計畫的交付條件，`[Q2]`=A）

五組閘門測試檢查的都是「某個字串**不存在**」，而這類檢查最容易寫成恆真。每一項都必須
做突變驗證：**改回錯的行為 → 跑測試 → 確認紅燈 → 還原 → 複驗綠燈**，並把突變內容與
紅燈訊息寫進 `code-summary.md`。

| # | 突變 | 必須紅的測試 |
|---|---|---|
| M1 | 把 `_progress_queue: asyncio.Queue[dict[str, str]] \| None = None` 一行加回 `design_agent.py` | 測試 8 |
| M2 | **只**把 `wa_collab_orchestrator.py` 的呼叫改回不傳新鍵（另兩處保持正確） | 測試 9 |
| M3 | 把 `agent_router.py` 的鑄造改為 `f"req-{counter}"` | 測試 10 |
| M4 | 在 `progress_channel.py` 加一行 `import uuid` | 測試 11 |
| M5 | 把 `design_agent.py` 其中一處的固定字串改回 `f"...{e}"` | 測試 12（第一子句） |
| M6 | 在 `design_agent.py` 新增第三個 `except Exception as e:` 區塊 | 測試 12（**第二子句**） |

**M2 是最重要的一個**：它驗的正是測試 9 那條「最容易寫成恆真」的斷言。若測試 9 被寫成
「grep 新參數有沒有出現」，**M2 會過**（另兩處仍有該參數）——而那正是
`functional-design` 的 `BR5.1` 只列一個呼叫點所造成的缺口。驗不出 M2 的測試 9 等於沒有
測試 9。

**M6 同理**：它是測試 12 第二子句存在的唯一理由。若只有第一子句，M6 會過。

---

## §四 既有測試必須保持綠燈

Testing Contract 的 `scope_floor` 逐字：「Keep the existing test suite green.」

本單元改動 `design_agent.py`、`agent_router.py`、`wa_collab_orchestrator.py`、
`test_agent.py` 四支既有檔，故 `backend/tests/` 全套必須在改動前後各跑一次並比對。
**特別注意** `backend/tests/test_design_agent.py` 現有 `@given`（property-based）測試
——它們落在純函式模組，但本單元改的是同一支檔的模組層狀態，須確認未連帶破壞。

**覆蓋率**：`org.md` 宣告「最低 80% line coverage」，而 `team.md` 如實記載**本 repo 完全
沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）
——該門檻目前既無法量測也無法強制。本計畫**不宣稱達成它**，亦不以「已達成」記錄。
實際門檻是 `team.md` 的 A／B／C 三項規則，而本單元：
規則 A（`role_permissions` 變更）**不適用**、規則 B（HTTP 端點）**不適用**、
規則 C（前端資料形狀）**不適用**——本單元的測試義務全部來自 `U22-V1`–`U22-V7`。

---

## §五 PBT 判定

**不適用。** `requirements.md:630` 逐字：「`FR13.2` 併發事件互斥 — **不適用 PBT**：
它需要併發編排而非輸入空間探索。以兩個重疊請求的明確案例驗證即足。」

本單元無純計算函式——四個操作全部是對共享可變狀態的操作，正確性由**交錯順序**決定而非
輸入值域，而 PBT 探索的是後者。ADR-0006 點名的三個 PBT 落點（IaC generator、
cost calculator、agent routing）皆不在本單元。
