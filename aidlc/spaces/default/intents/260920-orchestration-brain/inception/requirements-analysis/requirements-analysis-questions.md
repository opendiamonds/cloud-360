# Requirements Analysis Questions — 統一入口大腦

<!-- Stage: requirements-analysis（Inception 2.3）· Record: 260920-orchestration-brain
     本站把已核可的 10 項能力轉成可驗收的 FR／NFR。依 `requirements-analysis:c20`，
     上游已鎖定的產品決策不重問；本站只補 codekb 證明仍缺的可測不變量，
     加上 approval-handoff 明確指派給本站的四項。 -->

## 消費的上游輸入

| 產出 | 來源 |
|---|---|
| `intent-statement.md`、`scope-document.md` | ideation（已核可） |
| `initiative-brief.md` 的交接表 | approval-handoff（已核可） |
| `business-overview.md`、`architecture.md`、`code-structure.md` | codekb `cloud-360`（2026-09-24 重建，基準 `dc4b687`） |
| `constraint-register.md`、`raid-log.md` | feasibility（已核可） |

**codekb 的深度限制**：本輪為 Full rescan（廣度）＋ `kind: partial`（深度）。
33 個路徑實讀、27 支 backend 模組僅取簽章、37 支測試檔未讀內容。引用 codekb
的事實時，證據標記（`[讀]`／`[簽]`／`[算]`／`[未驗]`）一併帶進 requirements。

## 不重問的事項（附可引用的依據）

依 `scope-definition:260822-c5`，宣稱「已由上游定案」必須能引用具體選項字母或
原文。逐項如下：

| 不問的事 | 依據 |
|---|---|
| 產品邊界、10 項能力的集合 | `[Q9]`＝A（沿用工作計畫，不增不減） |
| 分級與交付序 | `[S9]`＝G,J → `[S11]`＝A（9 Must／1 Should）；`[S10]`＝A（風險優先＋技術依賴序） |
| 成本能力的編排方式 | `[Q12]`＝A（路由到既有 `/api/cost/v1`）、`[F14]`＝A（HTTP 帶使用者 token）、`[F15]`＝A（狀態事件轉譯進訊息流） |
| 成本答案呈現位置 | `[Q14]`＝A（就地在入口頁） |
| 編排層落點 | `[Q13]`＝B（大腦自建獨立 runtime，與既有並行） |
| Redis 形式 | `[F2]`＝A（新增第 5 個容器） |
| 記憶層落點 | `[F3]`＝B（同一 database、獨立 schema） |
| 記憶層授權模型 | `[F9]`＝B（記憶層內建最小權限模型） |
| 串流機制 | `[F4]`＝B（改用 WebSocket，既有 3＋2 個 SSE 端點不動） |
| episodic 的保存政策 | `[F5]`＝C（設保存期限 ＋ 使用者可自行刪除）——**只差期限數字，見 R2** |
| 共享工作階段的頁面範圍 | `[Q7]`＝A（入口頁 ＋ `/workspace` ＋ `/assessment`） |
| 作業對象階層 | `[Q5]`＝B（本次一併建立專案 → 系統 → 架構圖） |
| 成本上限 | `[F13]`＝A（由 OpenRouter 後台承載）、`[F11]`＝B（無硬數字，原則「盡量省」） |
| 遷移風險的處置 | `[F10]`＝A（不做試探，交設計階段）、`[H3]`＝A（落點 `domain-design`） |
| 技術試探的執行站 | `[H1]`＝A（併入 `domain-design`） |
| R-8 一致性驗證落點 | `[H4]`＝A（`contract-design`） |
| Go/No-Go 與殘留風險 | `[H5]`＝A（GO，三項全帶進 Inception） |
| 畫面與互動決定 | `[R1]`–`[R8]`（rough-mockups 已核可） |

## 本站新問的 8 題

**四題是 approval-handoff 明確指派給本站的**（`initiative-brief.md` 交接表第
2、3、4、12 列）：推播的觸發情境與接收對象、episodic memory 保存期限值、三個
成功指標的門檻值、能力 3／5／6 的可測不變量。

**四題來自 codekb 本輪查出、上游尚未吸收的缺口**（`architecture.md` 的約束二、
三、四、七）。它們不是實作細節，是會決定「這條需求能不能被驗證」的分岔。

**關於能力 5、6 的可測不變量**：這兩項的不變量沒有產品層的分岔，本站直接寫進
`requirements.md` 並於摘要確認時一併呈現——多意圖識別的不變量是「一句含 N 個
可分離意圖的輸入，產生 N 個各自帶可見狀態的工作項」；多輪對話的不變量是「第 N
輪可正確解析指向第 N−1 輪產出的指涉詞（『那個』『剛剛那張圖』）」。**只有能力 3
有真正的產品分岔**（另開新對話時作業對象怎麼辦），故成題為 R4。

---

## R1. 三個成功指標的門檻值要定在哪裡？

`[F7]`＝B 把門檻值指派到本站。難處是**目前沒有任何基準**：能力 1 尚未存在，
意圖識別準確率需要一組標註測試集才量得出來。選項已把「需要什麼才量得出來」
寫進去，請連同代價一起選。

- A. **保守初版門檻 ＋ 明寫校正條款**：意圖識別準確率 **≥ 80%**（對一組
  **≥ 50 筆人工標註的輸入**量測）、跨頁面上下文保留率 **≥ 95%**、首字回應時間
  **P50 ≤ 2 秒**。並在需求中明寫「第一版以建立量測機制為先，門檻於首次實測後
  得以校正」。代價：80% 這個數字現在沒有依據，是工程判斷。（建議）
- B. **較嚴格**：準確率 **≥ 90%**、保留率 **≥ 99%**、首字 **P50 ≤ 1 秒**。
  代價：≥ 90% 在沒有基準的情況下風險高，可能讓第一版反覆無法驗收；1 秒對
  「大腦先判意圖再交辦」的兩段式流程可能不可達。
- C. **只定量測方法，數值留到有實測基準後再定**。代價明確：驗收標準將無法
  二元可判，違反 `phases/inception.md` 的「requirements must be testable」，
  且這是第二次延後（`[F7]` 已延後過一次）。
- D. **只為首字回應時間定數值**（它是唯一不需要標註資料就能量測的），
  準確率與保留率只定量測方法與蒐集機制，數值留待實測。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T16:37:58Z | Mode: guided -->

## R2. episodic memory 的保存期限值定多久？

`[F5]`＝C 已定「設保存期限 ＋ 使用者可自行刪除」，只差數字。`C-R2` 另要求
刪除動作本身須留稽核紀錄（ADR-0006 audit logging 面向）。這是 by-user 的
對話歷程，屬個人可識別的使用歷程。

- A. **90 天**，逾期自動刪除。夠長到支撐「上次我們討論到哪」這類跨週回顧，
  又不會讓資料量無限成長。（建議）
- B. **30 天**。資料面最小化，但跨月的專案回顧會斷掉。
- C. **365 天**。保留最完整的歷程，代價是資料量與查詢效能在一年後才會顯現，
  屆時已難調整。
- D. **不設固定期限，改為每位使用者最多保留 N 則**（N 於設計階段定）。
  代價：與 `[F5]`＝C 的「保存期限」字面不符，屬對已核可決定的改寫。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T16:37:58Z | Mode: guided -->

## R3. 主動通知推播的觸發情境與接收對象？

能力 7 是唯一的 Should，`scope-document.md` 把這兩個參數列為上線前置依賴。
`[F4]`＝B 已定推播通道即 WebSocket。

- A. **只推「自己交辦的長時工作完成／失敗」，接收對象是交辦者本人**。
  範圍最小、語意最清楚，且與既有的成本 job 狀態事件天然對齊
  （`completed`／`failed`／`timeout` 三種終態）。（建議）
- B. **A ＋ 共編對象變更通知**：別人改了你正在看的架構圖時推播。
  代價：需要接上 A4 共編的既有 WebSocket 廣播，跨兩個 WS 通道。
- C. **A ＋ 成本異常**：估價結果超出某個門檻時推播。代價：本 intent 不建
  成本計量（`[Q12]`＝A），「異常」的判準沒有來源。
- D. **本版不交付推播，只保留通道**：WebSocket 建起來但不註冊任何推播情境，
  能力 7 明確延後。代價：Should 項目在第一版無可驗收行為。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T16:37:58Z | Mode: guided -->

## R4. 在子功能頁「另開新對話」時，作業對象怎麼處理？

能力 3 是 Must。`[R6]`＝B 已定入口由脈絡元件統一承載，但**新對話開啟後，
脈絡列上的專案／系統／架構圖要不要跟著帶過去**，上游沒有定案。這決定了
這條能力的可測不變量長什麼樣。

- A. **對話歷程獨立，作業對象沿用**：新對話不共享任何訊息歷程，但脈絡列
  仍指向同一個專案／系統／架構圖。不變量：新對話的第一則訊息即可指涉
  「這張圖」而不需重新指定。（建議）
- B. **兩者都獨立**：作業對象一併清空，使用者須重新指定。
  不變量：新對話的脈絡列顯示「尚未選定」。
- C. **繼承最後 N 則訊息作為起始脈絡**（N 於設計階段定）。
  代價：「獨立對話」的語意變模糊，與能力 2（共享脈絡）的邊界不再清楚。
- D. **獨立，但結束時可選擇合併回共享脈絡**。代價：新增一條上游未涵蓋的
  合併語意，且合併衝突的處理沒有來源。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T16:37:58Z | Mode: guided -->

## R5. 大腦的 WebSocket 契約要用什麼守住？

**codekb 本輪新發現**（`architecture.md` 約束二）：`/api/collab/ws/...` 存在於
程式但**不在 `openapi.json` 的 42 個 path 內**——FastAPI 不登錄 websocket route。
結論是 `dump_openapi.py --check` 與 `npm run check:types` 兩道漂移閘門
**對 WebSocket 完全無效**。能力 8（Must）整條騎在新 WS 上，目前一道機械閘門都沒有。

- A. **宣告一份前後端共用的 WS 訊息型別契約，並加一個 CI 檢查斷言兩端一致**。
  形狀比照既有的 `openapi.json` → `api.d.ts` 雙向閘門，但對象是 WS 訊息型別。
  代價：要新增一個 CI 檢查與一份契約來源。（建議）
- B. **把 WS 訊息型別手寫進 `openapi.json` 的 `components.schemas`**（不是 path），
  讓既有的 `npm run check:types` 產生前端型別。代價：`dump_openapi.py --check`
  會因為手寫內容與 dump 結果不符而紅燈，需要處理例外。
- C. **不加契約閘門，改以 Playwright e2e 斷言 WS 行為**。代價：只驗端到端行為，
  訊息型別本身仍無閘門；前端是本 repo 唯一能碰畫面的自動化層，但它抓不到
  型別漂移。
- D. **不加任何機械閘門，列為已接受風險**。代價：這是 `[H5]`＝A 之外**新增**的
  一項無早期訊號缺口，且它落在一個 Must 能力上。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T19:48:25Z | Mode: guided -->

## R6. 大腦的 WebSocket 要不要照抄既有前例的兩個行為？

**codekb 本輪新發現**（`architecture.md` 約束三）：既有 WS 前例
`collab_router.py:257` 呼叫 `get_user_from_token(..., record=False)`，
**跳過 `last_activity_at` 的更新**；且 token 放在 query string，會進 nginx 與
cloudflared 的 access log。兩者都觸及 ADR-0006（audit logging、network exposure）
——而 ADR-0006 是 hard constraint，每項變更都必須逐面向判定。

- A. **兩者都不照抄**：大腦的 WS 必須更新 `last_activity_at`；token 改走
  `Sec-WebSocket-Protocol` 標頭或握手後首則訊息，不進 query string。
  代價：與既有前例不一致，前端要寫兩種握手方式。（建議）
- B. **更新 `last_activity_at`，token 仍走 query string**：只修無聲迴歸那一半，
  握手方式與既有一致。代價：token 繼續留在 access log 裡。
- C. **照抄既有前例**：不更新、token 在 query string。代價：使用者只要改用
  大腦互動，「最後活動時間」這個既有能力就對他靜默失效——無任何錯誤訊息。
- D. **token 不進 query string，但不更新 `last_activity_at`**：只修暴露面那一半。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T19:48:25Z | Mode: guided -->

## R7. 大腦的 session 與工作狀態可不可以放在行程記憶體？

**codekb 本輪查出**（`architecture.md` 約束四）：目前有三處行程內狀態容器
（`collab_router` 的連線字典、`advice_orchestrator` 的 `_executor`／`_progress`／
`_inflight`、`pricing_client` 的磁碟快取），它們成立**只因為** `backend/Dockerfile:36`
沒有 `--workers`，是單 worker 單行程。本 intent 要引入 Redis，這個假設是否延續
必須明寫，否則實作會兩邊各猜一半。

- A. **大腦的 session 與工作狀態一律放 Redis，不得放行程記憶體**；既有三處
  不在本 intent 範圍內，維持原狀。不變量：重啟 backend 後，既有對話的脈絡與
  作業對象仍可完整還原。（建議）
- B. **A ＋ 順手把 `advice_orchestrator` 的進度外部化到 Redis**，解除既有約束的
  一部分。代價：動到已上線的 C1 路徑，超出本 intent 的範圍邊界。
- C. **允許行程內快取，但必須能在冷啟動後從 Redis 重建**。代價：多一層一致性
  問題（快取與 Redis 何時失效），而本 intent 沒有多 worker 需求來換取它。
- D. **維持單 worker 假設，大腦也可放行程記憶體**。代價：Redis 變成可有可無，
  與 `[F2]`＝A「新增第 5 個容器」的決定實質矛盾。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T19:48:25Z | Mode: guided -->

## R8. 「獨立 schema」要怎麼被自動化驗證？

**codekb 本輪新發現**（`architecture.md` 約束七）：全樹零 `CREATE SCHEMA`、
零 `search_path`；而測試在 `tests/helpers.py` 以
`sys.modules.setdefault("psycopg2", MagicMock())` 換掉驅動、改走 **in-memory
SQLite**——SQLite 沒有 PostgreSQL 的 schema 概念。也就是說 `[F3]`＝B 選定的
跨 schema 行為，在現有測試基礎設施上**沒有任何路徑可以驗證**。

- A. **新增一個對真實 PostgreSQL 執行的 CI job**（`postgres:16-alpine` 作為
  service container），範圍只涵蓋記憶層的 schema 建立、grant 邊界與跨 schema
  查詢。代價：CI 多一個 job 與約一分鐘。（建議）
- B. **在既有 unittest 內以 testcontainers 之類起 PG**，不新增 CI job。
  代價：新增一個 Python 依賴，且 `backend/requirements.txt` 目前只有 5 項精確
  釘選、其餘未 pin，新依賴會擴大既有的版本漂移面。
- C. **不加自動化測試，改以部署後的 smoke check 驗證**。代價：錯誤要到部署後
  才會發現，而 `schema_rbac.sql` 只在空 volume 執行（約束六），既有 staging 的
  修復是手動的。
- D. **接受無自動化驗證，列為已知缺口**。代價：這會是 `[H5]`＝A 之外**新增**的
  無早期訊號缺口，且它落在能力 4（Must）的地基上。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T19:48:25Z | Mode: guided -->

## R9. 意圖識別準確率的標註測試集由誰產生、在什麼時候？（矛盾／覆蓋檢查加開）

R1＝A 定下「準確率 ≥ 80%，對一組 **≥ 50 筆人工標註的輸入**量測」，但
**沒有任何一站被指派去產生那組標註集**——`initiative-brief.md` 的 12 列交接表
沒有它，`scope-document.md` 的 10 項能力也沒有它。沒有標註集，這條 Must 級
NFR 不可驗證，與 R8 指出的是同一類缺口。

它產生的時機會直接改變驗收條件：若要等真實使用紀錄才生得出來，這條 NFR
就不能用來守第一版。

- A. **在 `user-stories`（2.4）產生**：該站本來就在為每則故事寫 Given/When/Then，
  標註集就是「典型輸入 → 應交辦給誰」的集合，與 AC 同源。第一版即可驗收。（建議）
- B. **在 Construction 的序 2（意圖識別）工作單元內產生**：實作者最清楚分類邊界。
  代價：標註集由實作者自己出，量測自己的實作，獨立性較弱。
- C. **在 `nfr-requirements`（3.2）產生**：與 Jev 模型候選的評估同站，一併決定。
  代價：該站為 CONDITIONAL，若被 skip 則標註集與準確率門檻一起落空。
- D. **不預先產生，第一版上線後由真實使用紀錄累積**。代價明確：準確率 NFR
  **無法作為第一版的驗收條件**，R1＝A 的門檻實質降為上線後的觀測目標。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-24T23:53:05Z | Mode: guided | 矛盾／覆蓋檢查加開 -->

---

## 作答後的矛盾與覆蓋檢查（本站於答案收齊後補記，非新問題）

### 矛盾偵測：無矛盾，但有一條需要寫進需求的連動

九題答案彼此不矛盾，亦與上游已核可決定不矛盾。逐項核對後有一條**連動關係**
必須寫進 `requirements.md`，否則下游看不到：

**R1＝A 的「首字回應時間 P50 ≤ 2 秒」幾乎全部被路由層的 LLM 呼叫吃掉。**
R7＝A 的 Redis 往返在同一個 compose 網路內約 1ms，可忽略；真正的成本是
「大腦先判意圖、再交辦」這個兩段式流程的第一段。因此這條 NFR 能不能達成，
實質上由**路由層的模型選擇**決定——而那正是 `initiative-brief.md` 交接表
第 11 列（`typesafe/jev-1.13`，指派 `nfr-requirements`）的主題。兩者必須互相
引用，不得各自獨立存在。

### 覆蓋檢查：R1＝A 逼出一個沒人負責的交付物 → 已由加開的 R9 收斂

R1＝A 要求對 ≥ 50 筆人工標註輸入量測準確率，但交接表 12 列與 `scope-document.md`
的 10 項能力都沒有這個標註集。加開 R9 定案由 `user-stories`（2.4）產生。

### 本階段新增、已核可 scope 尚未涵蓋的項目（**需回補**）

依 `project.md` 的 requirements 規則，本階段新增或推翻已核可 `scope-document.md`
的項目，必須逐處明標並要求回補，不得當成既有能力的自然延伸吸收。本站的答案
產生了**四項**這樣的東西——它們都是**驗證機制或交付物**，不是 10 項能力之一：

| # | 新增項 | 來源 | 為什麼不是既有能力的延伸 |
|---|---|---|---|
| N-1 | 一份前後端共用的 WS 訊息型別契約來源 ＋ 一個新的 CI 一致性檢查 | R5＝A | `scope-document.md` 的能力 8 是「串流式互動」，指的是使用者看到回覆逐步顯示；契約閘門是保護它的機制，不在能力清單內 |
| N-2 | 一個對真實 PostgreSQL 執行的新 CI job | R8＝A | 能力 4 是「長短期記憶」；跑 PG 的 CI job 是驗證它的機制，不在能力清單內 |
| N-3 | ≥ 50 筆人工標註的意圖測試集 | R1＝A ＋ R9＝A | 這是量測能力 1 所需的資料交付物，`user-stories` 的既有職責是寫故事與 AC，不含產生標註資料集 |
| N-4 | 一套與既有前例不同的 WS 握手認證方式 | R6＝A | 最接近能力 8，但既有前例（token 在 query string）是可直接沿用的；改變它是本站為了 ADR-0006 而新加的要求 |

**回補請求**：上述四項應於下一次回到 `scope-definition` 時（或由
`delivery-planning` 在編 Bolt 時）明確納入工作量估算。本站不擅自把它們寫成
新能力，只如實標記其為本站新增且 scope 未涵蓋。

### 一項未經查證的前提（R6＝A 帶入）

R6＝A 選了「token 改走 `Sec-WebSocket-Protocol` 標頭或握手後首則訊息」。
**codekb 本輪未查證 nginx 與 cloudflared 是否會原樣透傳該標頭**——
`architecture.md` 約束一只確認了 `location /api/` 有設 `Upgrade` 與
`Connection`，沒有涵蓋其他握手標頭。此前提列為假設，須由設計階段實測，
不得當成已知事實。

---

## Consolidated Summary Confirmation

九題的定案摘要：

- **R1** 三個成功指標的門檻：意圖識別準確率 ≥ 80%（對 ≥ 50 筆人工標註輸入量測）、
  跨頁面上下文保留率 ≥ 95%、首字回應時間 P50 ≤ 2 秒，並明寫首次實測後得以校正
- **R2** episodic memory 保存 90 天，逾期自動刪除（使用者仍可自行提前刪除，刪除留稽核）
- **R3** 主動通知推播只推「自己交辦的長時工作完成／失敗」，接收對象為交辦者本人
- **R4** 子頁面另開新對話時：對話歷程獨立，作業對象（專案／系統／架構圖）沿用
- **R5** 新 WebSocket 以一份前後端共用的訊息型別契約 ＋ 一個新的 CI 一致性檢查守住
- **R6** 大腦的 WS 不照抄既有前例：必須更新 `last_activity_at`，且 token 不進 query string
- **R7** 大腦的 session 與工作狀態一律放 Redis，不得放行程記憶體；既有三處行程內狀態不動
- **R8** 「獨立 schema」以一個對真實 PostgreSQL 執行的新 CI job 驗證（範圍限記憶層的
  schema 建立、grant 邊界與跨 schema 查詢）
- **R9** 意圖識別準確率的 ≥ 50 筆標註測試集在 `user-stories`（2.4）產生，與 AC 同源

本站直接寫進 `requirements.md`、不另成題的兩條不變量：

- 能力 5（多意圖識別）：一句含 N 個可分離意圖的輸入，產生 N 個各自帶可見狀態的工作項
- 能力 6（多輪對話）：第 N 輪可正確解析指向第 N−1 輪產出的指涉詞（「那個」「剛剛那張圖」）

**七項**本階段新增、已核可 scope 尚未涵蓋、需回補的交付物（N-1 至 N-7，詳見
`requirements.md` 的該節）：WS 訊息型別契約 ＋ CI 檢查、真 PostgreSQL 的 CI job、
≥ 50 筆標註測試集 ＋ 三條 NFR 的量測機制、與既有前例不同的 WS 握手認證方式、
**新增一個 RBAC story id ＋ 權限矩陣項目（入口頁，觸發兩條 blocking 規則）**、
**一支承載 90 天清除的 gh-aw／GitHub Actions workflow**、
**專案／系統的建立路徑含其使用者可見面**。

（修訂 2／3 新增：原本只有四項 N-1 至 N-4；N-5、N-6 為兩輪審查逼出的「上游已核可
決定所隱含、但本站未落地的義務」，N-7 為 FR9.5 逼出的全新使用者可見面。）

**另有一個本站定下、但原確認範圍未涵蓋的數值**：FR1.7 的信心門檻初版值
**0.7**（判定為 `信心值 < 0.7` 即進入反問路徑）。它與 NFR1 的 80% 同屬無實證
基礎的工程判斷，且依 A-7 兩者必須一起校正、不得分開調。

一項未經查證的前提：nginx 與 cloudflared 是否原樣透傳 `Sec-WebSocket-Protocol`
（R6＝A 帶入，須由設計階段實測）。

Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
