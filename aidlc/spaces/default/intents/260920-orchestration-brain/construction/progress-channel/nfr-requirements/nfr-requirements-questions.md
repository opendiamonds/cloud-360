# NFR Requirements 問題檔 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）
> Stage：`nfr-requirements`（3.2）　Depth：`Minimal`　Review class：`advisory`（單輪、兩種結論皆終局）
> 建立時間：2026-10-03T15:52:14Z
>
> `produces_kinds` 使 `performance-requirements`／`scalability-requirements`／
> `reliability-requirements`／`observability-requirements` 四份對 `library` 不適用，
> 本站實際產出為 `security-requirements.md`、`tech-stack-decisions.md`、`traceability.json`。

---

## 前言：本站**不重問**的已定案事項

| 已定案 | 出處 |
|---|---|
| 鍵為 per-request、由入口端鑄造並顯式傳遞 | 本單元 `functional-design` 的 `[Q1]`=A、`BR1.1` |
| 清除由呼叫端 `try/finally` 擁有，並須有「被放棄的請求結束後鍵已消失」的測試 | `[Q2]`=A、`BR2.1`／`BR2.3` |
| `drain` 為破壞性，不支援重播 | `[Q3]`=A、`BR1.3` |
| buffer **有**上界、丟棄有優先序（`progress` 可丟、`xml`／`error` 永不丟）、丟棄留痕 | `[Q4]`=A、`BR4.1`／`BR4.2` |
| 併發測試以 `asyncio.Event` barrier 釘住，不得以 `sleep` 製造 | US13 DoD、`BR5.2` |
| logger 名稱為 `"cloud360.progress_channel"` | `team.md` `## Code Style` 逐字「新模組一律 `"cloud360.<module>"` 形式」（本檔不出成題目——既有 `design_agent.py:27` 用 `__name__` 是 `team.md` 已記載的 5 個不一致之一，新模組不沿用它） |
| 零新依賴 | `asyncio` 與 `collections.deque` 皆為標準庫；`backend/requirements.txt` 不需新增任何一行（本檔不出成題目） |
| 模組落點為 `backend/services/progress_channel.py` | `team.md` 的既成命名慣例（`snake_case.py`）；本單元不是 router 故無 `*_router.py` 後綴 |

## 本站開工前的實地查證（非來源登錄）

- **backend 完全沒有 metrics／可觀測性基礎設施**。對 `prometheus`／`statsd`／
  `opentelemetry`／`OTEL` 全樹搜尋只命中兩處，且都是**字串常值**——
  `wa_rule_engine.py:375` 與 `wa_lens_engine.py:416` 在檢查「使用者的架構圖裡有沒有
  提到監控工具」，不是本系統自己的 metrics。
  **後果：`BR4.2` 要求的「可觀察痕跡」目前只能是一行 Python `logging`，沒有計數器
  可以匯出，也沒有儀表板會顯示它。**
- `backend/requirements.txt` 無任何 metrics 或佇列套件。
- 既有 logger 命名：`advice_orchestrator.py:17` 為 `"cloud360.advice_orchestrator"`、
  `wa_collab_orchestrator.py:26` 為 `"cloud360.wa_collab"`、
  `design_agent.py:27` 為 `logging.getLogger(__name__)`。

---

## Q1 — buffer 上界的數值由誰、在何時定？

`functional-design` 的 `OQ-P1` 把數值留給 `code-generation`，理由是它取決於 agent 的
步數而該站沒有依據可算。但容量是 NFR，本站是它的自然落點，所以把這個指派重新攤開。

- **A（建議）— 本站不定數值，但把「定值前必須先量」寫成可驗證的需求。** 內容：
  `code-generation` 在定值前須實跑一次典型產圖並記下 `progress` 事件的實際則數，
  上界取該數的某個倍數，且**該測量值與倍數都要寫進程式註解**。好處：避免本站憑空
  寫一個數字（`project.md` 的「可以被計算的數字先算再寫」正是在說這件事），同時把
  `OQ-P1` 從「待辦」升級為「有驗收條件的待辦」。代價：上界在 `code-generation` 之前
  仍是未知，`BR4.1` 的測試要等到那時才能寫出確切的邊界案例。
- **B — 本站直接定一個數字（例如 1000）。** 好處：`BR4.1` 立刻可測。代價：這個數字
  沒有依據——我沒有量過一次產圖會產生幾則 `progress`，寫下來就是編的；而一個編的
  上界若太低會在正常使用下丟棄事件，太高則等於沒有上界。
- **C — 不設固定值，改為可由環境變數調整、預設值在 `code-generation` 定。** 好處：
  運維可在不改程式的情況下調整。代價：新增一個環境變數即觸發
  `scripts/validate_env_contract.py` 的連帶義務（`render-env.sh` 要寫它、
  `deploy/.env.example` 要列它、`backend/.env.example` 要記載它），而這是為一個
  **行程內記憶體上界**付的配置成本；且 `project.md` 明記這類遺漏的失敗模式是無聲的。
- **D — 以位元組數而非則數為上界。** 好處：直接對應記憶體這個真正要保護的資源，
  而 `xml` 事件的大小差異很大（一張架構圖的 XML 可能是幾十 KB）。代價：要在每次
  `publish` 量測事件大小，且「丟棄最舊的 `progress`」在位元組制下不保證能騰出
  足夠空間給一則大的 `xml`，規則會變複雜。

`[Answer]`: A <!-- 人工作答 2026-10-03T16:08:21Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Q2 — 丟棄一則事件要多大聲？

`BR4.2` 要求留下可觀察痕跡，而本站查證確認**系統沒有任何 metrics 層**，所以「可觀察」
目前只能是一行 log。問題是哪一種丟棄值得多大聲——丟 `progress` 與「因為 `BR2.1` 被
違反而整個通道不存在」是兩種嚴重度完全不同的事。

- **A（建議）— 分級：丟 `progress` 記 WARN；`publish` 到不存在的通道記 ERROR。** 理由：
  前者是設計預期內的降級（容量壓力下丟掉一則「還在動」的訊息），後者表示
  `BR2.1`／`BR2.3` 的清除契約被違反或鍵傳錯了——那是程式錯誤而非負載現象，而
  `construction.md` 逐字要求「Errors must be surfaced」。代價：ERROR 在高頻錯誤下
  會刷 log；但若它高頻出現，那本身就是要知道的事。
- **B — 兩者都記 WARN。** 好處：log 量可控、不會誤報。代價：把一個程式錯誤
  （鍵傳錯／通道提早關閉）降級成與負載現象同級，而這個系統沒有 metrics 可以補償
  ——WARN 在實務上沒人看。
- **C — 兩者都記 ERROR。** 好處：都不會被忽略。代價：容量丟棄在長請求下可能頻繁
  發生，把 ERROR 稀釋成噪音，之後真的 ERROR 就沒人理了。
- **D — 除了 log 之外，另外在通道物件上累計丟棄數，並在 `close` 時一次記總結。** 好處：
  一個請求丟了 50 則只會留一行而不是 50 行，且總數比單筆更有判斷價值。代價：要在
  通道上多一個欄位，且 `close` 的 log 與丟棄發生的時間點脫鉤（排查時要自己對時間）。

`[Answer]`: A <!-- 人工作答 2026-10-03T16:08:21Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Q3 — `await` 造成的檢查與變動之間的縫隙要怎麼處理？

本單元的設計假設（`A-P2`）是單執行緒 asyncio 事件迴圈，故**不需要鎖**。審查的 `R-07`
指出：這對 thread 是安全的，但若實作在「容量檢查」與「buffer 變動」之間插入任何
`await`，另一個協程就能在中間插進來——而**那個失效是安靜的**（不會拋例外，只會偶爾
多出或少掉一則事件）。

- **A（建議）— 以需求形式規定 `publish` 的檢查與變動之間不得有 `await`，並要求模組
  docstring 寫明此前提。** 理由：這是最小的機制——`deque.append`／`popleft` 都是同步
  操作，整段本來就不需要 `await`；把它寫成需求而不是靠實作者自己想到。代價：它是
  一條**靠人遵守**的規則，沒有自動化會擋。能做的補強是把它寫在最容易被看到的地方
  （函式本體的註解，而非只有模組 docstring）。
- **B — 加一個 `asyncio.Lock`。** 好處：機制保證，不靠人遵守。代價：契約的
  `shape_precedent.do_not_follow` 刻意否決了 `threading.Lock`，理由是單執行緒下它是
  cargo cult；`asyncio.Lock` 不是 cargo cult 但會讓每次 `publish` 變成 `await`，
  而 `publish` 在 agent 的熱路徑上。且它防的是一個「只要不寫 `await` 就不存在」的問題。
- **C — 把 `publish` 改成完全同步的函式（`def` 而非 `async def`）。** 好處：
  **型別層面就不可能有 `await`**——這是把 A 的人為規則變成編譯期（或至少 lint 期）
  約束。代價：契約 `K-18` 的 `public_interface` 逐字把 `publish` 的 `form` 寫成
  `async`，改它等於修訂一條已核可的契約；且呼叫端 `design_agent.py:82` 現狀是
  `await _progress_queue.put(...)`，改成同步要一併改呼叫端。
- **D — 維持現狀不處理，把它記成已接受的殘餘風險。** 代價：審查已指出它會安靜失效，
  而本單元存在的全部理由就是修一個安靜失效的缺陷。

`[Answer]`: A <!-- 人工作答 2026-10-03T16:08:21Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Q4 — `RequestKey` 的不可猜性要不要一條明文的安全需求？

這是本站 `security-requirements.md` 的核心問題。本單元**沒有授權判定**——
`contract-summary.md` K-18 逐字「進度事件的可見性由 `request_key` 的不可猜性保證，
不由授權判定」。也就是說，**鍵的產生方式就是這個單元唯一的存取控制機制**，而
`functional-design` 只寫了「不透明且不可猜」這五個字，沒有說用什麼產生。

- **A（建議）— 明文要求以密碼學安全的隨機來源產生，並禁止可預測來源。** 內容：
  `uuid4`（CPython 下走 `os.urandom`）或 `secrets.token_urlsafe` 皆可；**禁止**
  遞增計數器、時間戳、`random` 模組、以及任何由使用者 id 推導的值。理由：本單元的
  威脅模型只有一條路——猜到別人的鍵就能讀到別人的事件（`drain` 不做任何身分檢查）。
  把它寫成需求，`code-generation` 就不會「順手」用一個遞增 id。代價：無——兩個建議
  來源都是標準庫。
- **B — 不另立需求，沿用「不透明且不可猜」的描述。** 代價：`functional-design` 那五個
  字不是可驗證的需求。`[V-01]` 的教訓正好是這個形狀——`FR13.1` 寫「鍵為 session 或
  `thread_id`」，照字面實作完 AC 仍會紅燈，因為那句話沒有被檢查成立。
- **C — 比 A 更嚴：另外要求 `drain` 做呼叫端身分檢查。** 好處：縱深防禦，不只靠
  不可猜性。代價：`library` 單元**沒有身分**可檢查——它是行程內被同進程呼叫的，
  呼叫端就是自己的程式；要做身分檢查就得把使用者身分傳進來，那會讓這個 `library`
  開始承擔授權責任，與契約逐字的「無受保護操作」直接牴觸，且授權的真實落點是
  `U13`／`U12` 的 `require_story_action`。

`[Answer]`: A <!-- 人工作答 2026-10-03T16:08:21Z（`date -u` 實取）。選項文字與選單逐字一致。 -->

---

## Assumptions & Open Questions

（本站產出時填寫）
