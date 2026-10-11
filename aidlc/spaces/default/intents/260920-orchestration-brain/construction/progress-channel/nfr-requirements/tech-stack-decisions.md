# 技術選擇 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）　Stage：`nfr-requirements`（3.2）
> 本檔記錄本單元的技術決定。**全部沿用既有事實，零新依賴**——下表的每一列都附
> 它所依據的既成慣例或實測。

---

## §一 決定清單

| id | 決定 | 依據 | 是否出成題目 |
|---|---|---|---|
| `U22-D1` | 模組落點 `backend/services/progress_channel.py` | `team.md` `## Code Style` 的既成命名慣例：Python 檔名 `snake_case.py`；router 才有 `*_router.py` 後綴，本單元不是 router | **否**——有既成慣例可依 |
| `U22-D2` | logger 名稱 `logging.getLogger("cloud360.progress_channel")` | `team.md` 逐字「新模組一律 `"cloud360.<module>"` 形式」。既有 `design_agent.py:27` 用 `logging.getLogger(__name__)`，而 `team.md` 把它列為 5 個已知不一致之一——**新模組不沿用它**。既有正確形狀的實例：`advice_orchestrator.py:17` 的 `"cloud360.advice_orchestrator"`、`wa_collab_orchestrator.py:26` 的 `"cloud360.wa_collab"` | **否**——規則明文 |
| `U22-D3` | **零新依賴**：`collections.deque` ＋ `dict`，皆標準庫 | `backend/requirements.txt` 不需新增任何一行（已逐行讀過該檔）。`deque` 的 `append`／`popleft` 皆 O(1) 且**同步**，這是 `U22-V4`（無 `await`）能成立的結構前提 | **否**——無替代方案值得權衡 |
| `U22-D4` | **不加鎖** | `contract-summary.md` K-18 `shape_precedent.do_not_follow` 逐字：不照抄 `advice_orchestrator.py:24` 的 `threading.Lock`，因為那支檔案用 Lock 是為了它的 `ThreadPoolExecutor`（`:21` 的 `_executor`，本站已實地核對該行確為 `_executor: Optional[ThreadPoolExecutor] = None`），而本單元跑在單執行緒 asyncio 事件迴圈上 | **是**——`[Q3]`，因為審查 `R-07` 指出它對 `await` 縫隙是安靜失效；定案為 A（以需求規定不得有 `await`，不加 `asyncio.Lock`） |
| `U22-D5` | buffer 上界**有**、數值在 `code-generation` 定，且定值前須先量 | `[Q1]`=A。見 `security-requirements.md` 的 `S-1` | **是**——`[Q1]` |
| `U22-D6` | log 分級：容量丟棄 WARN、通道不存在 ERROR | `[Q2]`=A。依據之一是本站實測**backend 完全沒有 metrics 層**，故 WARN 在無補償機制下實務上沒人看 | **是**——`[Q2]` |
| `U22-D7` | 鍵由密碼學安全隨機來源產生（`uuid4` 或 `secrets.token_urlsafe`） | `[Q4]`=A。見 `SEC-1`。**鑄造在 `U13`／`U12`，不在本模組**（`U22-V5`） | **是**——`[Q4]` |
| `U22-D8` | 測試框架 Python 內建 `unittest`（**不是 pytest**），併發測試用 `IsolatedAsyncioTestCase` | `team.md` `## Testing Posture` 的既成事實：CI 跑 `python -m unittest discover -s tests -v`。前例 `backend/tests/test_langgraph_migration.py`，US13 DoD 逐字「**不需新 seam**」 | **否**——既成事實 |

---

## §二 為什麼 `deque` 而不是 `asyncio.Queue`

現狀用的是 `asyncio.Queue`（`design_agent.py:31`）。換成 `deque` 不是偏好，是三個
需求各自逼出來的：

1. **`U22-V4`（無 `await`）**：`asyncio.Queue.put` 是 coroutine，`maxsize` 滿載時它會
   **await** 直到有空位——那正是 `[Q4]` 選項 C（阻塞生產者）被否決的行為，而生產者是
   agent 的熱路徑。`deque.append` 是同步的。
2. **`BR4.1`（選擇性丟棄）**：丟棄「最舊的 `progress` 類」需要**掃描並從中間移除**，
   `asyncio.Queue` 沒有這個操作；`deque` 可以。
3. **`BR4.1` 的「`xml`／`error` 永不丟棄」**：需要在寫入時依類別分流，`Queue` 的
   `put_nowait` 在滿載時只能拋 `QueueFull`，無法表達「這一則不准丟、擠出別的」。

**代價**：`deque` 不提供任何等待語意，所以 `drain` 必須是「取到空就停」的輪詢形狀
——而這正是現狀 `_drain_progress`（`:160-165`）已經在做的事（`get_nowait()` 迴圈到
`asyncio.QueueEmpty`），所以消費端的形狀**不變**，只是換掉例外型別。

---

## §三 本單元**不**做的技術決定

如實記載，以免下游把沉默讀成已決：

| 項 | 不做的理由 | 誰做 |
|---|---|---|
| SSE／WebSocket 的傳輸形式與重連協定 | `[Q3]`=A 已定 `drain` 為破壞性、不支援重播；「斷線重連要不要補事件」是對外協定決定 | `U13 brain-gateway` |
| `thread_id` 的分區語意與 `MemorySaver()` 單例 | `FR13.4` 是與進度通道**無關**的第二個缺陷（對話記憶的共用）。`BR5.1` 刻意只鎖進度鍵那一半 | `code-generation`，見 `functional-design` 的 `OQ-P2` |
| `NFR3` 的各單元延遲子預算 | `NFR3` 是端到端門檻；切成子預算需要全鏈資料，本站沒有。本站只要求「不引入 I/O 與 `await`」這個可檢查的必要條件 | `build-and-test`（3.6，`ALWAYS`）的量測 |
| 事件 `type` 的取值集合是否該擴充 | 四種（`progress`／`xml`／`message`／`error`）沿用既有程式，改名會讓 `wa_collab_orchestrator.py:80-90` 的 remap 失效 | 不改；若 `U13` 需要新類別，由該單元提出 |

---

## §四 `project.md` blocking 規則對照

| 觸發條件 | 命中？ | 理由 |
|---|---|---|
| 新增／刪除／更名表、欄位、索引、約束、外鍵 | **否** | 本單元無資料表（`SEC-4`） |
| seed／預設資料語意變更 | **否** | 不碰 `role_permissions`；本單元無受保護操作故無新 story id |
| ORM／啟動補丁引入新 DDL | **否** | 不碰 `models.py`／`database.py` |
| 新增 compose 消費的環境變數 | **否** | `SEC-4` 明文禁止；`[Q1]`=A 刻意避開選項 C 正是為了不觸發這一條 |
| 異動 `database.py` schema 補丁／`deploy/nginx.conf`／任一 `.env.example`／`render-env.sh` | **否** | 同上，故 `LOCAL-DEV.md` 同步義務不適用 |

**五項皆未命中**，故 `schema_rbac.sql` ＋ `DEPLOY.md` 與 `LOCAL-DEV.md` 的 blocking
同步皆不適用於本單元。

`team.md` 的三條測試底線對照：規則 A（`role_permissions` 變更需 allow/deny 雙向）
**不適用**（不改矩陣）；規則 B（HTTP 端點需 `TestClient`）**不適用**（無端點）；
規則 C（前端資料形狀變更需 e2e）**不適用**（不碰前端）。本單元的測試義務全部來自
`U22-V1`–`U22-V6`。
