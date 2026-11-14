# Performance Requirements — `U24 member-pages-ui`

> 單元類型 `ui`，故 `produces_kinds` 使本站只產出 performance／security／
> tech-stack／traceability 四份；**scalability／reliability／observability 三份為
> `[service]`，不適用本單元**（不是漏寫）。
>
> **識別字**：可繼承 inception NFR 的用 `NFR<parent>.80+`；**無法誠實繼承任何
> inception NFR 的，以 `UIP-n` 宣告為孤兒**並在 §三 逐項寫明理由。
> `.80+` 區段經實測為空（既有子號 1–74，`U11` 用 `.60+`）。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/member-pages-ui/functional-design/functional-spec.md` | W1–W6、三個狀態機、六個 API 消費點 |
| `construction/member-pages-ui/functional-design/rules.md` | `BR21.3`／`BR22.3`／`BR24.1`／`BR25.2` 的 observable |
| `inception/requirements-analysis/requirements.md` | `NFR1`–`NFR11` 的逐條原文（判定適用性的依據，見 `traceability.json`） |
| `inception/contract-design/contract-summary.md` | `K-16` 的四個 http 方法 |
| `codekb/chiton/technology-stack.md` | 前端技術棧現況 |

## 一、可繼承 inception NFR 的要求

| ID | 要求 | 目標 | 量測方式 | 父條與繼承理由 |
|---|---|---|---|---|
| `NFR11.80` | 改角色後**不得**發生頁面切換 | 切換次數 **0** | Playwright 計 `App.tsx` 路由變更次數 | `NFR11`（跨功能任務的頁面切換次數應嚴格少於基準）。`[F4]`=A 的就地更新使改角色的切換次數為 0；被否決的 `[F4]`=D（導回清單頁）會是 1。**這是本單元唯一與 `NFR11` 有實質連動的決定** |
| `NFR11.81` | 彙總橫幅的「查看成員」導向**被點選的**那一個專案 | 到達目標專案的切換次數 **1** | 同上；對第 N 個專案斷言 `projectId` 相符 | `NFR11`。導錯專案會讓使用者再切換一次以上（`BR26.2`） |

> **`NFR11` 的量測母體屬 `user-stories`（2.4），不是 `build-and-test`（3.6）。**
> `requirements.md:568-571` 逐字：「情境集合由 `user-stories`（2.4）與該站的故事
> 同源產生；`user-stories` 為 `CONDITIONAL`，**skip 時**義務轉移至
> `build-and-test`（3.6，`ALWAYS`）」——轉移是**條件式**的，而 `user-stories`
> **並未被 skip**（`stories.md:533` 以 `M-3` 逐列承接「跨功能任務情境集合 ＋
> 現行 UI 的切換次數基準」，`:535-537` 明寫轉移只在該站被 skip 時發生）。
> `build-and-test` 擁有的是**量測機制**（`requirements.md:577-579`），不是母體。
> **審查 `R-03` 更正**：原文把母體歸給 `build-and-test`，是誤置。
>
> 現行的具名情境是「改架構圖→取成本差額」這類**跨功能**任務，成員管理是單一功能，
> 故上面兩條目前**不在 `NFR11` 的計分母體內**；它們是本單元對該條的**正向貢獻**。
> **而「把成員管理類情境加進母體」目前無自然承接站**：`M-3` 只命名了交付物、
> 未列舉情境，而它的擁有者 `user-stories` 已完成且在游標之前。依 `project.md`
> 的指派規則，此處寫**無自然承接站**並於核可關卡提交使用者，不指向一個
> 並不擁有它的站——那正是「假的交叉引用讓缺口看起來有人接」。

## 二、本單元自有的效能要求（孤兒，無 inception 父條）

| ID | 要求 | 目標 | 量測方式 |
|---|---|---|---|
| `UIP-1` | 成員清單的列數上限 | **100 列**；超過時**不渲染清單**，改顯示「成員過多，請聯絡管理者」 | e2e：構造 101 位成員 → 斷言清單不存在且提示文字存在；構造 100 位 → 斷言清單存在 |
| `UIP-2` | 橫幅的 pending 查詢**不快取**，每次 `Layout` 掛載各一次 | 每次頁面掛載 **恰 1 次**請求；缺 `K3 view` 者 **0 次** | e2e：攔截 `GET /reselections/pending`，換頁 N 次後請求數為 N；以缺 `K3 view` 的角色換頁 N 次後為 0 |
| `UIP-3` | 邀請／改角色／移出成功後**不得**整份重抓成員清單 | `GET .../members` 的額外請求數 **0** | e2e：攔截該端點，執行三種操作後其請求數不增加 |
| `UIP-4` | 成員清單首次可互動前的請求數 | **1**（只有 `list_members`；`canManage` 由同一份回應推得，不另發請求） | e2e：進入成員頁後對 `/api/membership/**` 的請求數為 1 |

### 二之一、`UIP-1` 的 100 是怎麼來的（**不是憑空**）

提問時選項寫的是「例如 200 列」——那個數字我憑空給的。repo 對「一次回應最多
幾列」這個概念**已經有數字**：`backend/services/user_router.py:146-147` 逐字為
`DEFAULT_PAGE_SIZE = 20` 與 `MAX_PAGE_SIZE = 100`，而那是本 repo **唯一**的
清單端點先例（`/api/auth/list`，前端 `AdminPage.tsx` 以 `PaginationControl` 消費）。
取 **100** 使本單元的上限與既有先例一致，而不是另立一個沒有來源的門檻。

### 二之二、`UIP-1` 的已知代價（**不埋起來**）

`list_members`（`membership_router.py:164-178`）**實測沒有任何 `page`／`limit`／
`offset` 參數**，一次回傳全部成員。故 `UIP-1` 是**純前端的防護**：伺服器仍會傳
101 筆，前端只是不渲染。由此產生一個真實的功能邊界：

> **成員數超過 100 的專案，無法用成員頁管理成員**——而本單元是管理成員的**唯一入口**。

受影響的已核可 AC：`AC12.2.1`／`AC12.6.1`／`AC12.6.2` 都斷言「清單內容改變」，
在超過上限的專案上不可驗證。這不是缺陷而是 `[N1]`=A 的已揭露代價（選項文字逐字
寫明「超過上限的專案完全無法用成員頁管理成員」），列為 `OPEN-MP24-6` 並指派落點。

## 三、孤兒宣告（為什麼 `UIP-*` 沒有 inception 父條）

`inception/requirements-analysis/requirements.md` 的 11 條 inception NFR 中，
**沒有一條涵蓋前端渲染規模或前端請求數**——逐條核對：
`NFR1` 意圖識別準確率、`NFR2` 跨頁面上下文保留率（母體逐字限定為入口頁／
`/workspace`／`/assessment` 三處）、`NFR3` 首字回應時間（LLM 串流）、
`NFR4` 狀態外部化（Redis）、`NFR5` WebSocket 契約閘門、`NFR6` 記憶層 schema 隔離、
`NFR7` episodic memory 稽核、`NFR8` 新增元件的部署設定、`NFR9` 成本原則（LLM 花費）、
`NFR10` 路由層模型可替換性、`NFR11` 頁面切換次數。

把 `UIP-*` 掛到其中任何一條都會是**誤繼承**（例如掛 `NFR3` 會聲稱清單渲染是
LLM 首字延遲的子項）。依 `U11` 那站對 `SEC-1`–`SEC-5` 的同一處置：
**宣告為孤兒、寫明無父條、並在 `traceability.json` 的 `reverse` 段逐條解釋**，
而不是為了讓追溯看起來完整而掛一個假父條。

## 四、`OPEN-MP24-6` — 超過 100 位成員的專案無法管理

| 欄位 | 內容 |
|---|---|
| 缺口 | `UIP-1` 的 100 列上限之上，成員頁**不渲染清單**，而它是管理成員的唯一入口。故成員數 >100 的專案，其 `project_owner` 無法改任何人的角色、無法移出任何人。 |
| 性質 | **已揭露的代價，非未預見的缺陷**——`[N1]` 選項 A 的文字逐字寫明「超過上限的專案完全無法用成員頁管理成員」。 |
| 受影響的已核可 AC | `AC12.2.1`／`AC12.6.1`／`AC12.6.2`（皆斷言「清單內容改變」）在 >100 的專案上不可驗證。 |
| 本單元內可做的部分 | 提示文字與「不渲染半套清單」的行為。**落點 `code-generation`**（`execution: ALWAYS`、construction、在本單元游標之後，已查 `stage-graph.json`）。 |
| 本單元內**不**可做的部分 | 真正的修法是伺服器分頁（`list_members` 加 `page`／`limit`）。`U19` 的 `code-generation` **已完成且在游標之前**，故本 intent 內**無自然承接站**——與 `OPEN-MP24-1` 同一個形狀。依 `project.md` 的「指派事項找不到誠實的轉移目標時，寫『無自然承接站』並指定屆時判定的 conductor 重新提交給使用者」，此項不填假目標，於核可關卡向使用者揭露。 |
| 不採的做法 | 不在本站偷偷把上限調高到「實務上不會到」的數字來讓問題消失——那只是把同一個斷崖移到看不見的地方，且沒有任何來源支持那個數字（100 來自 `MAX_PAGE_SIZE`，更大的數字沒有先例）。 |

## 五、`OPEN-MP24-3` 的處置（上游**指派本站**定案的未定參數）

`functional-spec.md:291` 逐字把「變更紀錄的分頁與保存期限未定」指派給
**`U24` 的 `nfr-requirements`（3.2，下一站）**——即本站。它不是可以往下傳的項目，
故在此定案：

| ID | 要求 | 目標 | 量測方式 |
|---|---|---|---|
| `UIP-5` | 變更紀錄的列數上限與排序 | **最多 100 列、最新在前**；超過時**只渲染最新 100 列**並顯示「僅顯示最近 100 筆」 | e2e：構造 101 筆變更 → 斷言列數為 100、第一列為最新、提示文字存在 |

> **`UIP-5` 目前不可量測，而這是它自己的前置缺口造成的，不是參數沒定。** 它的 e2e
> 「構造 101 筆變更 → 斷言列數為 100」需要一條能把變更紀錄取回前端的路徑，而
> 下一節（§五之一）的查證顯示那條路徑不存在。參數在此定案（不往下傳），
> 可量測性則隨 `OPEN-MP24-7` 關閉才成立。兩件事分開記，不用「已定案」蓋掉「還不能驗」。

兩個參數的依據，各自可查：

- **100**：同 `UIP-1`，來自 `user_router.py:146-147` 的 `MAX_PAGE_SIZE`。不另立數字。
- **保存期限 = 不刪**，而這有**兩處**獨立依據（第二處由審查 `R-04` 的附帶發現補上，
  比第一處更直接）：
  - `schema_rbac.sql:679`（`reselection_events.acknowledged_at` 的 COMMENT）逐字
    「**the row is never deleted**」。
  - `schema_rbac.sql:663` 逐字「**There is deliberately NO retention period here**
    (unlike `memory.memory_audit_events`, NFR7.2) … the event row itself is never
    deleted. **Do NOT add a 90-day purge**」——它不只說不刪，還明文禁止為這張表
    加上 90 天清除，並點名它與記憶層那張表的差別。

  故「保存期限」這個問題的答案是**現況沒有、本單元也不新增**（上游還明文禁止新增）
  ——前端不刪資料，`UIP-5` 是**純顯示上限**。
  如實記載而非替它發明一個期限：訂一個前端看不到、也沒有任何機制執行的期限，
  等於把一條不會被實作的規則寫進需求。

### 五之一、**本站查出的阻塞缺口**：變更紀錄沒有任何端點可取

定案 `UIP-5` 的過程中逐一核對磁碟，發現 `OPEN-MP24-3` 的**前提不成立**：

| 查證 | 結果 |
|---|---|
| `membership_router.py` 的路由總數 | **6**（`:164`／`:192`／`:234`／`:270`／`:309`／`:328`），與 `functional-spec.md` §四 一致 |
| 其中讀取 `reselection_events` 的 | **只有 `GET /reselections/pending`**，而它逐字過濾 `cause = 'auto_reselection'` **且** `acknowledged_at IS NULL`，**且**只查自己（`principal.user_id`）——這是橫幅查詢，不是變更紀錄查詢 |
| `membership_facade.py` 的方法 | **17 個**（`grep -c '^    def '`；其中公開 **12**、`__init__` 與四個 `_` 前綴共 5），另模組層函式 **1**（`guard_report`）。**十七個全部核對過方法名與簽章，無任何** change-log／history 讀取方法——`:206` `list_members`（只回四欄的 `MemberView`）與 `:471` `list_my_pending_reselections`（過濾 `cause == auto_reselection` 且 `acknowledged_at IS NULL` 且限本人）為最接近者，皆不符。**審查 `R-04` 更正**：原寫「13 個」，那是 `grep -cE '^[[:space:]]{0,4}def [a-z]'`（＝公開 12 ＋ 模組層 1）的輸出，與同句的「方法」一詞不相稱，且會讓覆蓋宣稱少交代 5 個私有方法。審查獨立複驗同一結論，並補了一項更強的證據：`models.py` 的 `Index("ix_reselection_events_project_id", "project_id")` 註解逐字寫「成員詳情頁的變更紀錄讀取端」——**索引為該讀取而建，讀取端卻不存在** |
| `MemberView` 的欄位 | `user_id`／`display_name`／`role`／`joined_at`——**不含任何歷史** |

故 `AC12.2.2`（變更紀錄顯示誰／何時／原值／新值）在本單元**沒有可取得資料的路徑**。
`BR24.3` 約束的是「渲染時四項俱在」，它在資料取不到時不會紅燈——**這條規則目前
不可達**，與 `project.md` 記載的「新增『偵測 X 狀態』的規則前先推導 X 是否可達」
同一個形狀，只是方向相反：規則已核可，而讓它可達的前置不存在。

**不自行補救**：`U19/[FD3]=A` 已決定兩類變更都存進同一張表，正是為了讓
`AC12.2.2` 以**一個查詢**讀出變更紀錄——缺的只是把它開成端點。但那是 `U19` 的
契約擴充，而 `U19` 的 `code-generation` **已完成且在游標之前**。本 intent 內
**無自然承接站**（與 `OPEN-MP24-1` 同形）。列為 `OPEN-MP24-7`，於核可關卡
向使用者揭露，不填假目標、也不在本單元偷偷改 `U19`。
