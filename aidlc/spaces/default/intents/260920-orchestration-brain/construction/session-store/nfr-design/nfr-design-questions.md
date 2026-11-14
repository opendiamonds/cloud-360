# NFR Design 問題檔 — `U10 session-store`

> depth 為 **Minimal**。本站只問兩題。上游已把大量設計決定鎖死
> （三層形狀、TTL、淘汰策略、筆數上限、授權委派、日誌白名單），
> 本檔只問**上游沒有涵蓋、而實作無法自行推導**的兩項。

## 本站可以自行決定、不出成題目的三項（附依據）

1. **連線池大小**。`nfr-design-patterns.md` 逐字給了公式
   `Pool size = (Requests per second) × (Average request duration in seconds) × 1.5`。
   以 `NFR3.40`／`NFR3.41` 的 P95 ≤ 20ms 代入，單一 session 的一輪互動約 2–3 次
   Redis 呼叫；即使同時 300 個 session 每秒各一次互動（遠高於自有 staging 的實際
   負荷），`300 × 0.02 × 1.5 = 9`。取 **min 5 / max 20** 並附此算式。有公式、有輸入，
   不需要人裁決。
2. **`set_work_target` 跨 PostgreSQL 與 Redis 的一致性**。`K-07` 的
   `resolve_work_target` 逐字「**唯讀且冪等**」（`hierarchy_facade.py:276`），故
   「K-07 讀成功、Redis 寫失敗」不留下任何不一致——沒有需要補償的交易。
   這是查證結果，不是取捨。
3. **本單元不設 SLO**。`reliability-requirements.md` 已定案並附理由（無告警管道、
   production 不在範圍）。本站不重開。

---

## [D1] Redis 內的值怎麼擺——以及**多分頁同時寫入時會不會靜默掉訊息**

**這是本站唯一真正危險的一題。** 上游已明文允許多條並存連線：
`x-concurrent-connections.multiple_allowed` 逐字「同一個 session key **允許多條
並存連線**（三個頁面、多個分頁）」。而 `K-09.behaviour_semantics` 逐字
「`append_message` **非冪等**」。

**若值是單一 JSON blob 且以「讀出→改→寫回」更新，兩個分頁同時追加訊息就會互相
覆蓋，而且是靜默的**——後寫的那一次帶著它讀到的舊陣列覆蓋先寫的那一次，使用者
只會看到自己那一則，另一則消失得無聲無息。上游沒有任何一條規則碰到這件事。

**ACL 前提（本站查證）**：app 使用者為 `+@all -@admin -@dangerous`
（`deploy/docker-compose.deploy.yml:246-248` 實讀）。依 Redis 文件的 ACL 分類，
`EVAL`／`EVALSHA` 屬 `@slow @scripting`、`WATCH`／`MULTI`／`EXEC` 屬 `@fast @transaction`，
**皆不在 `@admin` 或 `@dangerous` 內**，故下列選項在 ACL 上都可行。
**這是依文件推理、不是實地執行**（本機無該 Redis 實例），故列為 `code-generation`
的部署時查核項。

### 選項

- **A（建議）— Redis Hash，每段一個欄位，追加與修剪以 Lua 腳本原子完成。**
  單一 key（`ADR-005` 的要求不變）、key 之下是一個 Hash：每個段一個欄位（JSON 編碼
  的訊息陣列）、另有 `pageModes` 與 meta 欄位。`append_message` 走一支 Lua：
  讀該欄位 → 追加 → 依 `BR3.4` 修剪到 200 → 寫回 → 續期 TTL，**全部在伺服器端一次
  執行**。
  - **好處**：① 不同段的並發寫入**完全不衝突**（不同欄位）；② 同一段的並發寫入由
    Lua 的單執行緒執行序列化，**不會掉訊息**；③ 追加一則訊息只傳該段而非整個
    session；④ TTL 仍在 key 上，`BR1.4`（三者一起消失）不變。
  - **代價**：引入一支 Lua 腳本，它是**第二種語言**，要和 Python 的修剪邏輯保持
    一致——`BR3.4` 的語意會有兩個載體。處置是讓 Lua 成為**唯一**的載體，Python
    不自行修剪。
- **B — 單一 JSON blob ＋ 樂觀並行控制（`WATCH`／`MULTI`／`EXEC` ＋ 重試）。**
  - **好處**：結構最單純，一個 key 一個字串；不需要 Lua。
  - **代價**：① 每次寫入都要傳整個 session（三段各 200 則時約 300 KB），而
    `NFR3.41` 給 `append_message` 的預算是 P95 ≤ 20ms——**本選項讓那個預算與訊息
    累積量相關**，愈接近上限愈慢；② 衝突時要重試，而重試次數上限又是一個要定的
    參數；③ `WATCH` 的重試迴圈若寫錯會變成無限迴圈。
- **C — 單一 JSON blob，後寫覆蓋（不做並行控制）。**
  - **代價**：**多分頁同時送訊息會靜默掉訊息**。這正是 `BR6.1` 整條規則要防的那類
    無聲失敗，只是成因由基礎設施換成並行。且上游**明文允許**多分頁。**不建議。**
- **D — 每段各一個 Redis key（List ＋ `LTRIM` 原生原子）。**
  - **好處**：追加與修剪是 Redis 原生操作，連 Lua 都不需要。
  - **代價**：**直接推翻 `ADR-005`**——它的 Alternatives Rejected 逐字拒絕「分成
    兩個 key」，理由是會出現中間態；而本選項是**最多四個** key。`BR1.4`「三者一起
    消失」要靠在每個 key 上各設 TTL 來近似，而那正是 `ADR-005` 不要的形狀。

[Answer]: A（Redis Hash，每段一個欄位，追加與修剪以 Lua 腳本原子完成）
<!-- answered 2026-10-09T14:15:14Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## [D2] Redis 呼叫的失效處置——逾時、重試、熔斷要用哪些

`nfr-design-guide.md` 逐字「**Timeout**：Every external call without exception」，
而 Redis 呼叫是外部呼叫。但 `BR6.1` 已定案「不降級、不退回行程記憶體」，
所以熔斷器在本單元**不能**帶來降級模式，只能讓失敗更快。

`K-09.behaviour_semantics.retry_and_idempotency` 已把方法分成兩類：
`load`／`touch`／`set_work_target`／`set_sharing_mode` **冪等可重試**；
`append_message` **非冪等**。這個分界是本題的基礎。

### 選項

- **A（建議）— 逾時 ＋ 冪等方法有界重試，`append_message` 不重試，不加熔斷器。**
  連線逾時 2 秒、指令逾時 1 秒；四個冪等方法重試至多 2 次、指數退避含抖動
  （`nfr-design-patterns.md` 逐字「**Always add jitter**」）；`append_message`
  **一次就好**，失敗即 `SessionBackendUnavailable`。
  - **好處**：完全對齊 `BR6.2` 已定的冪等分界；不引入新的失敗模式。不加熔斷器的
    理由是**它在這裡沒有可降級的對象**——`BR6.1` 禁止降級，所以熔斷器只是把
    「等 1 秒後失敗」變成「立刻失敗」，而 Redis 是同一台主機的內部服務，
    不存在熔斷器要防的「拖垮上游」情境。
  - **代價**：Redis 真的掛掉時，每一次呼叫都會各等一次逾時。
- **B — 逾時 ＋ 重試 ＋ 熔斷器。** 連續 5 次失敗後開路 30 秒。
  - **好處**：Redis 長時間不可用時不再每次都等逾時。
  - **代價**：引入一個**有狀態**的元件，而它的狀態放哪裡又是一個問題
    （放行程記憶體 ⇒ 與 `NFR4` 的精神衝突、多 worker 各有一份；放 Redis ⇒ 荒謬）。
    且開路期間的行為仍然是 `SessionBackendUnavailable`，**使用者感受不到差別**。
- **C — 只有逾時，完全不重試。**
  - **好處**：最少的活動元件；行為最可預測。
  - **代價**：一次短暫的網路抖動就會讓使用者看到錯誤，而 `load`／`touch` 這些
    冪等讀取重試一次幾乎零成本。把可救的失敗當成不可救的。
- **D — 本站不定案，留給 `code-generation`。**
  - **代價**：逾時與重試會直接影響 `NFR3.40`／`NFR3.41` 的 P95 預算（重試會把
    尾端延遲往上拉），而那兩條已經定案。不在本站定，等於讓實作去決定一個已核可
    預算能不能達成。

[Answer]: A（逾時 ＋ 冪等方法有界重試，append_message 不重試，不加熔斷器）
<!-- answered 2026-10-09T14:15:14Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## 上游已定案、不重問

| 事項 | 定案出處 |
|---|---|
| 三層形狀與純函式邊界 | `functional-design` 的 `entities.md`／`rules.md`（已核可） |
| TTL 24 小時、每次互動續期、到期整體消失 | `ADR-005`；`BR1.3`／`BR1.4` |
| 淘汰策略 `noeviction` | `[N3]`=A；`NFR4.50` |
| 每段 200 則上限、缺值不得啟動 | `[N2]`=A；`BR3.4`／`BR3.5`／`NFR8.40` |
| 不自行判權、不取身分、不對外暴露 | `BR5.1`–`BR5.3`；`NFR4.46` |
| 日誌白名單與內容禁令 | `BR3.6`；`NFR4.45`／`NFR4.63` |
| 不設 SLO、不做備份 | `reliability-requirements.md`（附理由） |
| 對話歷史保存期維持 24 小時 | `[N1]`=A |
