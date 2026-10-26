# Functional Design 問題檔 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M，**本輪新增的唯一可平行根**）
> Stage：`functional-design`（3.1）　Depth：`Minimal`　Review class：`advisory`（單輪、兩種結論皆終局）
> 建立時間：2026-10-03T14:59:12Z

---

## 前言：本站**不重問**的已定案事項

下列皆已由上游核可，本站逐一引用其出處，不再出成題目：

| 已定案 | 出處（逐字） |
|---|---|
| 鍵必須是 **per-request** | `components.md:680-681`：「鍵必須是 **per-request**，不得用 `thread_id`（per-user）或不存在的『session』（`[V-01]`）」 |
| 形狀沿用 per-key dict，但**不照抄** `threading.Lock` | `components.md:682-686`：「形狀沿用 `backend/cost/advice_orchestrator.py:23-24` 的 per-key dict……**但不照抄它的 `threading.Lock`**：那支檔案用 Lock 是因為它有 `ThreadPoolExecutor`，而本元件在單執行緒的 asyncio 事件迴圈上跑，`threading.Lock` 在那裡是 cargo cult」 |
| 請求結束時**必須**移除該鍵 | `components.md:687-688`（`ADR-014`）：「只寫不刪會把跨使用者錯送換成無上界的記憶體成長，即修掉一個失敗模式換來另一個」 |
| 兩個併發請求各自只收到自己的事件，且各自**非空** | `components.md:689-690`（`FR13.2`）：「非空那一半是必要的，否則空集合會讓互斥斷言真空成立」 |
| 通道不存在時的讀取**不得崩潰**，且對外錯誤為**固定訊息、不含例外原文** | `components.md:691-693`（`FR13.3`）：「`_drain_progress` 對 `None` 呼叫 `get_nowait()` 拋 `AttributeError`，且**該例外原文被送進 SSE 給使用者**——內部例外文字外洩是獨立的 ADR-0006 面」 |
| 併發測試**不得以 `sleep` 製造**交錯 | `unit-of-work.md:400-402`：「以 `asyncio.Event` barrier 釘住交錯順序……`playwright.config.ts:17` 與 `ui-regression` 都容忍 flaky，一個 flaky 的併發測試等於沒有測試」 |
| `wa_collab_orchestrator.py:79` 須補傳 per-request 的鍵 | `unit-of-work.md:398` |
| 依賴邊：本單元無出邊（葉），入邊為 `U13 brain-gateway` 與 `U12 work-orchestrator` | `components.md:742-749`、`:770-771`，皆 `style: sync` |

---

## 缺陷現狀（本站開工前的實地查證，非來源登錄）

以下為我在 HEAD 上逐行讀出的事實，供題幹與選項引用。**不是**上游來源，不得被當成已核可決定：

- `backend/services/design_agent.py:31`　`_progress_queue: asyncio.Queue[dict[str, str]] | None = None` —— **模組層全域**。
- 寫入端四處（`:81`、`:84`、`:96`、`:101`）全部讀**模組全域**，不是區域變數。
- `:183` 指派 `_progress_queue = asyncio.Queue()`；`:218` 指派回 `None`。
- 讀取端 `:203`／`:211` 呼叫 `_drain_progress(_progress_queue)`——**引數在呼叫當下才取全域值**。
- `_drain_progress`（`:160-165`）以 `get_nowait()` 迴圈取到 `asyncio.QueueEmpty` 為止，屬**破壞性讀取**。
- 消費端 `wa_collab_orchestrator.py:79` 的呼叫為 `run_design_agent(messages, current_xml)`——**沒有任何 per-request 參數**。

**由此推得的三個失敗模式**（與 `FR13.1`／`FR13.2`／`FR13.3` 一致）：

1. 請求 B 在 `:183` 覆寫全域後，請求 A 於 `:203` 取到的是 **B 的 queue** —— A 會收到 B 的 `xml`。這比「A 收不到」嚴重：A 拿到的是另一位使用者的架構圖內容。
2. 先結束的請求在 `:218` 把全域設為 `None`，另一個請求的 `_drain_progress(None)` 於 `get_nowait()` 拋 `AttributeError`。
3. 該 `AttributeError` 的原文被送進 SSE 給使用者（內部例外文字外洩）。

---

## Q1 — per-request 的鍵由誰產生、怎麼傳下去？

上游已鎖定「鍵是 per-request」，但**沒有**定案由誰鑄造、以什麼形式傳遞。這決定了 `run_design_agent` 的簽章要不要改，以及併發測試能不能把鍵釘死。

- **A（建議）— 呼叫端鑄造不透明 token，經參數顯式傳遞。** `U13`／`U12` 在請求入口產生一個不透明識別字（如 `uuid4().hex`），以新參數傳入 `run_design_agent(...)`，再傳給通道的建立／寫入／讀取三端。本元件**不自行推導**鍵。代價：`run_design_agent` 與 `wa_collab_orchestrator.py:79` 的簽章要改（後者上游已要求改）。好處：鍵在測試裡可直接指定，`asyncio.Event` barrier 測試能精確斷言「A 的鍵只收到 A 的事件」；且沒有任何環境隱含狀態——而隱含狀態正是本缺陷的成因。
- **B — 通道鑄造並回傳 handle 物件。** 呼叫端 `with channel.open() as ch:` 取得 handle，寫入與讀取都經該 handle，鍵對外不可見。好處：清除端可綁在 context manager 上，較難忘記。代價：handle 要穿過三層呼叫（`brain-gateway` → `work-orchestrator` → `design_agent`），且測試要從 handle 反推鍵才能做互斥斷言。
- **C — 用 `contextvars.ContextVar` 承載，簽章完全不動。** 好處：`run_design_agent` 與 `wa_collab_orchestrator.py:79` 都不必改。代價：**這正是造成本缺陷的那種環境隱含狀態的另一種形式**；且 `ContextVar` 在 `asyncio.create_task` 邊界會複製而非共享，一旦寫入端跑在另一個 task 上，寫到的是副本——這個失敗模式與現狀同樣安靜。另：上游 `unit-of-work.md:398` 已明文要求改 `wa_collab_orchestrator.py:79`，選 C 等於否決那一項。
- **D — 由 `thread_id` 加單調計數器推導。** 代價：`thread_id` 是 per-user（上游 `[V-01]` 明文否決它作為鍵），加計數器後雖然唯一，但鍵的語意變成「某使用者的第 n 次」，同一使用者兩個併發請求的測試要依賴計數器的實作細節才能寫。

`[Answer]`: A <!-- 人工作答 2026-10-03T15:30:31Z（`date -u` 實取）。選項文字與下方選單逐字一致。 -->

---

## Q2 — 請求**異常**結束時，誰保證鍵被移除？

`ADR-014` 要求「請求結束時必須移除該鍵」，但**沒有**定案「請求被中途放棄」時的保證。現狀的 `:218` 在 `except Exception` 之後，SSE 被客戶端中斷時是否執行並不明顯。

- **A（建議）— 呼叫端 `try/finally` 擁有移除，並加一個斷言「被放棄的請求結束後鍵已消失」的測試。** 理由：Starlette 在客戶端斷線時會關閉回應 generator，`finally` 因此會跑；但「因此會跑」是推論而不是證據，所以把它變成一條測試而不是一句假設。代價：要寫一個模擬中途放棄的測試。
- **B — 只靠 `finally`，不另外驗證。** 代價：若 generator 被 GC 而非顯式 `aclose()`，`finally` 的執行時機不保證，而洩漏是安靜的（記憶體成長，無錯誤）。
- **C — 加一道 TTL 清掃（背景 task 定期移除逾時的鍵）。** 好處：任何洩漏路徑最終都會被收。代價：引入一個背景 task 與一個新的時間參數；且 TTL 選太短會砍掉還在跑的長請求，選太長等於沒有上界——而長請求的時間上界本單元沒有依據可定。
- **D — 以存活通道數上界取代時間上界：超過上限即拒絕建立並大聲失敗。** 好處：洩漏從「安靜的記憶體成長」變成「可觀察的失敗」，與 `project.md` 的「Errors must be surfaced」一致，且不需要時間參數。代價：上限值本身需要依據；設太低會在正常併發下誤擋。

`[Answer]`: A <!-- 人工作答 2026-10-03T15:30:31Z（`date -u` 實取）。 -->

---

## Q3 — 讀取語意：破壞性 drain，或可重播？

現狀 `_drain_progress` 是破壞性的（`get_nowait()` 取完為止）。本站要決定新通道是否沿用。這影響 `U13 brain-gateway` 的斷線重連能不能補回已產生的事件。

- **A（建議）— 沿用破壞性 drain：單一消費者，事件取出即消失，不支援重播。** 理由：與現狀行為一致（不夾帶行為變更）、與 SSE 的單一消費者模型相符，而「斷線重連要不要補事件」是 `U13` 的對外協定決定，不是本元件的資料結構決定。代價：客戶端斷線重連會看不到斷線期間的進度事件（但仍會收到之後的，且最終結果不受影響）。
- **B — 非破壞性讀取加游標：事件保留，消費者自帶位置。** 好處：`U13` 之後若要做重連補事件，不必回頭改本元件。代價：事件要保留到請求結束，單一請求內的記憶體上界變成「該請求產生的全部事件」而非「尚未被讀走的事件」；且這是替一個尚未定案的需求（`U13` 的重連協定）先付成本。
- **C — 破壞性 drain，但保留最後 N 筆供重播。** 折衷。代價：N 是一個新參數且無依據；且「最後 N 筆」對使用者而言是部分重播，比完全不重播更難解釋。

`[Answer]`: A <!-- 人工作答 2026-10-03T15:30:31Z（`date -u` 實取）。 -->

---

## Q4 — 單一通道內的事件數有上界嗎？

寫入端（`design_agent` 的 `on_progress`）與讀取端（SSE 迴圈）速率不同。若消費者慢或停止讀取而生產者繼續寫，單一請求內的佇列會成長。上游只談了「跨請求的無上界成長」（鍵不刪），**沒有**談單一請求內的成長。

- **A（建議）— 設一個有限上界，滿了就丟棄最舊的進度事件，但 `xml`／`error` 類事件永不丟棄。** 理由：進度訊息是可丟的（它的價值是「還在動」，舊的那一則已無資訊），而 `xml` 是請求的實際產出、`error` 是失敗原因，丟掉任何一個都會讓使用者看到錯的結果。代價：要在通道裡區分事件類別，使它不再是一個純粹的 FIFO。
- **B — 不設上界（`asyncio.Queue()` 的現狀行為）。** 理由：單一請求的生命週期有限，生產者寫入的事件數由 agent 的步數決定，不是無上界。代價：若某次 agent 迴圈異常地長，記憶體成長無人擋；且「由 agent 步數決定」是一個沒有被量過的假設。
- **C — 設有限上界，滿了就**阻塞生產者**（`asyncio.Queue(maxsize=N)` 的原生行為）。** 好處：零事件遺失。代價：生產者是 agent 的執行路徑，阻塞它等於讓一個慢的／已斷線的消費者拖住產圖——把一個記憶體問題換成一個可用性問題。
- **D — 設有限上界，滿了就丟棄最舊的，不分類別。** 最簡單。代價：有機會丟掉 `xml`——那是請求的實際產出。

`[Answer]`: A <!-- 人工作答 2026-10-03T15:30:31Z（`date -u` 實取）。 -->

---

## Assumptions & Open Questions

（本站產出時填寫）
