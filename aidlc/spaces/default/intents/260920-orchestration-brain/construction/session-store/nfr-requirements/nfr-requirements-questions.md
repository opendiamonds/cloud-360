# NFR Requirements 問題檔 — `U10 session-store`

> depth 為 **Minimal**。本檔只問三題，三題都是「預設錯了會造成真實重工或真實資料遺失」
> 的那種。下方「上游已定案、不重問」逐項列出被省略的事項與其定案出處。

## 本站的指派來源

`ADR-016`（`decisions.md:664`）逐字把一件事指派給本站：
「**保存期限與筆數上限本站同樣不定數值**，但明訂三件事：① 它是 `SessionContext`
的職責…③ **數值由 `nfr-requirements` 決定**」。
`unit-of-work.md:479` 逐字確認轉移條件未觸發：「`DG-5`（對話歷史的保存期限與筆數）
的轉移條件是「`nfr-requirements` 被 skip」，而它在本工作流程是 **EXECUTE**…故它
**留在 `nfr-requirements`**，本站不假裝接手」。

**本站就是那一站。** 而要定那兩個數值時，查出了下面兩個先決問題。

## 編號配置（避免跨單元撞號）

實測既有 12 個單元的 `nfr-requirements` 產出已用掉的子編號：
`NFR3` 用到 24、`NFR4` 用到 23、`NFR5` 用到 7、`NFR6` 用到 21、`NFR7` 用到 34、
`NFR8` 用到 20、`NFR12` 用到 29。本單元一律自 **`.40`** 起編，與任何既有編號不重疊。

---

## [N1] 對話歷史要存多久——而這之前有一個先決矛盾要先解

**已核可的兩邊互相矛盾，而且是機械可驗的：**

| 邊 | 逐字出處 | 它要求什麼 |
|---|---|---|
| 畫面 | `mockups.md:833-836`（`M16`）畫出 `今天` 與 `7 天內` 兩個分組；`interaction-spec.md:736` 的 `default` 狀態逐字「依時間分組（今天／**7 天內**／**30 天內**）」 | 對話歷史至少要活 **30 天** |
| 儲存 | `ADR-005` 逐字「TTL 24 小時…TTL 到期三者一起消失」；`ADR-016` 逐字「對話歷史的**實體落點**為既有的 `SessionContext`」 | 對話歷史 **24 小時**後消失 |

**後果可機械推導**：`7 天內` 與 `30 天內` 兩個分組**永遠不可達**。這與
`refined-mockups` 自己在 `memory.md:44` 記下的 `RecentConversations.hidden`
不可達問題**完全同形**——「狀態存在但永不可達」。

**而且還有一個更根本的事實，是我在本站查出來的**：

> **`RecentConversations` 沒有任何單元擁有它。** 以 `grep -rl` 掃全 record，
> 它只出現在 `refined-mockups` 的四份產出、`domain-design/decisions.md`
> （`ADR-016` 的理由段）、以及我自己的 `functional-design` 問題檔。
> **`units-generation`／`contract-design`／`delivery-planning` 三處合計 0 命中。**
> `U14 entry-page-ui` 的交付清單逐字為「BrainChat／ContextBar／WorkItemDock／
> ClarifyCandidates／CostAnswerCard／StreamingMessage ＋ DefaultRedirect」
> （`unit-of-work.md:180`）——**沒有 `RecentConversations`**。
>
> 另：全部 FR 與全部 AC 之中，**沒有任何一條**要求「列出最近的對話」。
> 它是一個有線框、有互動規格、但**沒有需求、沒有單元、沒有契約**的元件。

### 選項

- **A（建議）— 維持 24 小時，並把畫面的兩個分組回報為不可滿足。** 對話歷史留在
  `SessionContext` 的單一 key 之下、隨 24h TTL 一起消失；本站把「`7 天內`／`30 天內`
  兩個分組在現行儲存設計下永不可達」與「`RecentConversations` 無擁有單元」兩項
  一併回報給 `refined-mockups`／`units-generation`，由產品決定是刪掉那兩個分組、
  還是把該元件正式納入某個單元的範圍。
  - **好處**：零新儲存體、零 schema 變更、`ADR-005` 與 `ADR-016` 都不動。而且它
    對齊證據——**沒有任何 FR 或 AC 要求這個元件**，為一個沒人要求、沒人擁有、
    沒有契約的畫面元素新建持久層，是在加沒人要的範圍。
  - **代價**：已核可線框的一個可見元素被標為部分不可滿足，須回報上游。
- **B — 對話歷史與 session 狀態分家，存進既有 PostgreSQL，保存 30 天。**
  `SessionContext` 的 Redis key 只留作用中那一段的工作歷程與作業對象／模式，
  TTL 24h 不變；跨日的對話列表改由新表承載。
  - **好處**：`7 天內`／`30 天內` 真的可達，已核可線框完全成立；不新增服務
    （用既有 DB）。
  - **代價**：① 新增一張表 ⇒ **觸發 `project.md ## Mandated` 的 blocking 規則**
    （`schema_rbac.sql` 與 `DEPLOY.md` 必須在同一個 PR 同步）；② 需要一條讀取
    路徑給 `RecentConversations`，而**沒有單元擁有它**，須先指派；③ `ADR-016`
    逐字的「實體落點為 `SessionContext`，**不新建元件**」須以新 ADR 修訂；
    ④ 跨日保存的對話內容是個人資料，會帶出一條本 intent 目前沒有的保存／刪除
    義務（`NFR7` 的 90 天只管 episodic memory，不管這個）。
- **C — 把 session key 的 TTL 由 24 小時拉長到 30 天。**
  - **代價**：**直接推翻 `ADR-005` 的核心論證**。它的 Consequences 逐字說 24h
    到期讓 `no-object` 狀態「**真的可達（不只首次使用）**，`ContextBar` 宣告的
    該狀態不再是死碼」——拉到 30 天等於讓 `G-2`（作業對象無人清回未選定）復活。
    且 30 天不活動的 session 仍佔 Redis 記憶體，與 `[N2]`／`[N3]` 的記憶體上限
    直接衝突。**不建議。**
- **D — 本站不定案。**
  - **代價**：`ADR-016` 與 `unit-of-work.md:479` 兩處逐字都把它釘在本站，且
    `unit-of-work.md:479` 明寫其他站「不假裝接手」。再轉一次沒有承接者。

[Answer]: A（維持 24 小時，並把畫面的兩個分組與 RecentConversations 的無主狀態回報上游）
<!-- answered 2026-10-09T13:48:52Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## [N2] 每一段的對話訊息筆數上限訂多少

`rules.md` 的 `BR3.4` 已定**每段獨立計算**、超限丟最舊；`BR3.5` 已定參數缺值時
**服務不得啟動**（不得解讀為無上限）。本題只定數值。

**記憶體算式（實測參數，非估計）**：`deploy/docker-compose.deploy.yml:232-235`
逐字 `--maxmemory 256mb`。段數上界為 3（`entities.md` 的 `EC4`）。故

```
單一 session 的歷程上界 ≈ 3 段 × N 則 × 每則平均位元組
256MB ÷ 單一 session 上界 = 可同時存活的 session 數上界
```

**每則平均位元組本站無實測值**，以 **500 bytes**（含中文訊息與中繼欄位）作為
**明示的假設**代入——它是假設不是量測，下游若有實測應重算：

| N（每段上限） | 單一 session 歷程上界 | 256MB 可容納的 session 數 |
|---|---|---|
| 50 | 75 KB | 約 3,400 |
| 200 | 300 KB | 約 850 |
| 500 | 750 KB | 約 340 |

### 選項

- **A（建議）— 200 則／段。** 約 850 個同時存活 session，對一台自有 staging
  （`192.168.10.10`，production 不在範圍內）有數量級以上的餘裕；而 200 則足以
  涵蓋一段長對話，`FR6.1` 的「第 N−1 輪」更是遠在其內。
- **B — 50 則／段。** 記憶體餘裕最大（約 3,400 session），但一段 50 則的對話
  並不罕見；超限丟最舊之後，較早輪次的指涉詞解析會失效——而那是 `FR6.1` 的
  能力本身，不是邊緣情境。
- **C — 500 則／段。** 幾乎不會截斷，但 session 容量降到約 340，且把
  `[N3]` 的淘汰風險推得更近。
- **D — 不設筆數上限，只靠 TTL。** 與 `BR3.5` 已定的「缺值不得視為無上限」直接
  牴觸，且單一 key 可無上界成長至觸發 `[N3]` 的淘汰。**不建議。**

[Answer]: A（200 則／段）
<!-- answered 2026-10-09T13:48:52Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## [N3] Redis 的淘汰策略——目前的設定會讓 `NFR4` 在容量壓力下**無聲**失效

**實測**：`deploy/docker-compose.deploy.yml:234-235` 逐字
`--maxmemory-policy allkeys-lru`。

`allkeys-lru` 在記憶體用滿時會淘汰**任何** key，包含**尚未到期的活躍 session**。
而 `NFR4` 的可測不變量逐字是「**重啟 backend 後，既有對話的脈絡與作業對象仍可
完整還原**」——淘汰發生時這條不成立，且：

> `U1` 自己在同一份 compose 的註解逐字記載：「An eviction is countable —— **but
> NOT via `INFO evicted_keys`**（review R-01）：`INFO` is @slow @dangerous, so
> **NEITHER configured identity can run it**」。可用的替代只有應用端的
> `MEMORY STATS` 與主機端的 `docker stats`。

**所以淘汰對應用層是不可見的**，而被淘汰的使用者看到的畫面，與 TTL 正常到期
（`W7`）**完全相同**——這正是 `BR6.1` 要防的那一類無聲失敗，只是成因由「服務故障」
換成「容量壓力」。

### 選項

- **A（建議）— 改為 `noeviction`。** 本設計的**每一個** Redis key 都帶 TTL
  （`BR1.3`：五個方法全部續期；工作項集合同 key），故 `noeviction` 之下 session
  **只會因 TTL 消失，不會因容量消失**，`NFR4` 成為真的保證。記憶體用滿時寫入
  **大聲失敗**，循既有的 `SessionBackendUnavailable` 路徑（`BR6.1`）向上傳遞。
  - **代價**：改動 `U1 brain-infra` **已施工完成**的 compose 設定（與
    `functional-design` 的 `D-S10-1` 改 `K-02` 同型，須一併納入該輪的追認範圍）；
    且容量真的用滿時**所有人**同時寫入失敗，而不是**少數人**無聲失去 session。
    這是刻意的取捨：可偵測的全面失敗優於不可偵測的局部失敗。
- **B — 改為 `volatile-ttl`。** 只淘汰帶 TTL 的 key，且優先淘汰**最接近到期**的。
  - **好處**：不會全面失敗；丟失順序比 LRU 合理（快到期的先走）。
  - **代價**：**仍然是無聲的 session 遺失**——本設計所有 key 都帶 TTL，所以它與
    `allkeys-lru` 的差別只在「丟誰」，不在「會不會丟」。`NFR4` 仍不是保證。
- **C — 維持 `allkeys-lru`，但把風險寫成具名需求與偵測義務。** 不動 `U1`；本站
  產出一條 NFR 要求以 `MEMORY STATS` 建立使用率告警，在逼近 `maxmemory` 前先知道。
  - **代價**：`NFR4` 的「完整還原」在容量壓力下**仍然不成立**，只是變成「有機會
    事先知道」。告警的承載機制也要有人做，而本 intent 目前沒有告警管道。
- **D — 提高 `maxmemory`。** 只是把同一個問題往後推，且 `U1` 的註解逐字定下
  「container memory limit >= maxmemory × 1.5 + 256MB」的關係，改 `maxmemory`
  要連容器上限一起改。**不建議單獨採用。**

[Answer]: A（改為 noeviction）
<!-- answered 2026-10-09T13:48:52Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## 上游已定案、不重問（逐項附定案出處）

| 事項 | 定案（逐字出處） |
|---|---|
| Redis 的 `appendonly` | `deploy/docker-compose.deploy.yml:230-231` 已設 `yes`；`U1` 的註解逐字說明不設會讓 `NFR4.2` 無聲失敗 |
| Redis 的 ACL 與憑證 | `U1` 已完成：`REDIS_USER`／`REDIS_PASSWORD`，`default` 收窄為 `@connection`；`render-env.sh:121-123` 已寫三個變數 |
| Redis 不對外暴露 | `K-01` 逐字 `exposure: compose 內部網路only；不得 publish port`；deploy compose 無 `ports:` |
| 狀態放哪裡 | `NFR4` 逐字「一律放 Redis，不得放行程記憶體」 |
| TTL 長度與續期時機 | `ADR-005`：24 小時、每次互動續期（`[N1]` 的選項 C 才會碰它） |
| 本單元的授權模型 | `K-09` 逐字「本單元不自行判權」；`rules.md` 的 `BR5.1`–`BR5.3` |
| 首字回應時間的歸屬 | `NFR3` 逐字「這條預算幾乎全部被**路由層的 LLM 呼叫**吃掉……Redis 往返在同一個 compose 網路內約 1ms，可忽略」——本站只負責把那個「可忽略」變成可驗證的預算項，不重訂 P50 門檻 |
| 路由層模型（`NFR10`） | **不是本單元的**。`NFR10` 逐字指派 `nfr-requirements`（3.2），但本站是 **per-unit** 執行，而路由層屬 `U11 intent-router`——**本單元的這一輪不discharge 它**，見下方交接 |
| 意圖識別準確率（`NFR1`）、頁面切換次數（`NFR11`） | 量測落點皆為 `build-and-test`（3.6）；本單元是其機制的一部分，但不擁有門檻 |
| episodic memory 的 90 天（`NFR7`） | `U9 memory-purge` 已完成。`ADR-016` 逐字「對話歷史是 session 層，記憶是內容層」——兩者不是同一件事，不得互相套用 |

## 交接（本站不代決）

- **`NFR10`（路由層模型可替換性）**：其逐字落點是 `nfr-requirements`，而該站
  per-unit 執行。路由層屬 `U11 intent-router`，該單元**尚未跑過任何一站**
  （`construction/` 下無 `intent-router/`）。本輪**不**代它決定，並明記：
  若 `U11` 的 `nfr-requirements` 被判 skip，`NFR10` 逐字「**沒有自然承接站**」，
  屆時判定 skip 的執行者必須重新提交使用者裁決。
