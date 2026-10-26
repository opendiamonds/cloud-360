# Security Requirements — `U11 intent-router`

> **本檔是本站的 review artifact。** ID 帶 `.60+`（見 `performance-requirements.md` 的帶位說明）。

## 零、本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `construction/intent-router/functional-design/rules.md` | 本檔引用的每一條 `BR` 的正式來源——`BR5.5`（記憶不得用於解析指涉對象，含其 `logic_executable`／`reachability`／`residual_gap` 三欄）、`BR7.1`／`BR7.2`（不判權、不自取身分）、`BR7.3`／`BR7.4`（不建工作項、對 `SessionContext` 唯讀）、`BR1.1`／`BR1.2`（`prompt_guard` 前置）、`BR2.2`（`capability` 封閉列舉）、`BR6.1`（最少上下文）。**本檔把規則轉成可驗證的需求，不改寫規則本身**；兩者若有出入以 `rules.md` 為準 |
| `construction/intent-router/functional-design/functional-spec.md` | §五 的 ADR-0006 四面向判定（本檔是它的需求化）、§六 的 `OPEN-IR11-5`（`BR5.5` 的殘留缺口與可達性） |
| `inception/requirements-analysis/requirements.md` | `NFR6`／`NFR7`／`NFR8`／`NFR9` 的條文與其理由 |
| `inception/contract-design/contract-summary.md` | `K-10` 的 `behaviour_semantics`；`K-08` 的 `MemoryFacade.search` 簽章（`:617-618`）；`OQ-N2`（`:1434`）的殘留缺口記載形狀；`OQ-N3`（`:1432`）的記憶寫入端缺口 |

## 一、ADR-0006 Security Baseline 四面向（hard constraint，逐格填，無空白）

`project.md` 逐字要求「對每一項變更檢查 ADR-0006 的四個面向」，且「涉及 IAM／
權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出中明列 security 影響與處置，
**不得僅以『已有 ADR-0006』帶過**」。

| 面向 | 判定 | 本單元的落點與處置 |
|---|---|---|
| **IAM** | **適用** | 本單元**不自行判權**（`BR7.1`）、**不自行從請求取身分**（`BR7.2`，`principal` 由 `classify` 第一個參數傳入）。讀記憶的授權由 `K-08` 的 `MemoryFacade` 承擔。落為 `NFR6.60`／`SEC-1` |
| **Encryption** | **適用，且本 intent 的增量在這裡** | 本單元的 `external_dependencies` 含 **OpenRouter（third-party-api）**——**使用者的自然語言輸入會離開本平台**。`BR6.1` 的「最少上下文」因此不只是成本紀律，**也是資料外送的最小化**。落為 `NFR9.60`。傳輸加密由 OpenRouter 的 HTTPS 端點承擔（`langgraph_runtime.py:16` 的 `DEFAULT_OPENROUTER_BASE_URL`）。**本單元不新增任何靜態儲存**，故 at-rest 無增量 |
| **Network exposure** | **適用（入站零增量、出站有增量，分開陳述）** | **入站**：本單元不暴露任何對外端點（`K-10` 為 `in-process`，`BR7.2`）——零增量。**出站**：本單元**發起**一條對第三方 API 的外送連線。把兩者合併寫成「零增量」會漏掉後者，故本檔分列。落為 `SEC-2` |
| **Audit logging** | **適用，且本單元有一條他處沒有的禁令** | ① `prompt_guard` 命中是**安全事件**，應可被觀測（`SEC-4`），但**不得記錄觸發它的輸入文字**；② 本 repo 為 **public** 且 Actions log 公開可讀，而本單元處理使用者自由文字——**任何日誌不得含 `text`，也不得含候選的 `label`**。後者是本單元獨有的：`label` 由模型**從輸入生成**，可能複述輸入內容。落為 `SEC-3` |

**四面向皆適用，無不適用項。**

## 二之零、兩條沒有 inception `NFR` 親代的需求（`SEC-1`／`SEC-2`）

stage 檔逐字要求「每一條細部需求繼承它的 inception NFR ID 並加上子編號」。
本檔有**兩條做不到**，而硬掛一個親代會是錯的：

| ID | 它真正的來源 | 為什麼不掛在任何 `NFR{n}` 之下 |
|---|---|---|
| `SEC-1`（`principal` 由參數傳入） | **ADR-0006 的 IAM 面**（`project.md` 的 hard constraint） | inception 的 `NFR1`–`NFR11` **沒有一條是 IAM**。逐條核對：準確率、上下文保留率、首字時間、狀態外部化、WS 契約閘門、記憶 schema 隔離、episodic 稽核、部署設定、成本、模型可替換性、頁面切換次數 |
| `SEC-2`（不暴露端點、不自行 `httpx` 直打） | **ADR-0006 的 network exposure 面** | 同上 |
| **`SEC-3`**（日誌不得含 `text`／`label`／`referent`） | **`project.md` 的公開 repo 輸出禁令 ＋ ADR-0006 的 Audit logging 面** | **修訂 1（審查 `R-03`，Major）新增。** 原本掛在 `NFR7` 之下 |
| **`SEC-4`**（`prompt_guard` 命中可觀測、紀錄不含輸入） | 同上 | 同上 |
| **`SEC-5`**（日誌欄位白名單，見 `observability-requirements.md`） | 同上 | 同上 |

> **修訂 1／`R-03`：我對同一個問題用了兩套相反的處置，而審查是對的。** 原本
> `SEC-1`／`SEC-2` 被判為孤兒（ADR-0006 的 IAM 與 network exposure 面沒有 NFR 親代），
> 但 `NFR7.60`／`.61`／`.63`（日誌禁令）卻被硬掛在 `NFR7` 之下——**而 `NFR7` 的逐字
> 主體是「episodic memory 的保存 90 天與刪除稽核……其靜態儲存與傳輸的加密要求」，
> 完全不提日誌內容限制**。我當時寫的親代論證（「把使用者輸入寫進日誌＝在 90 天保存
> 與刪除稽核之外製造不受控副本」）聽起來成立，但它推不出「所以它屬於 `NFR7`」——
> 它只推出「兩者都關心個人資料」。**實證**：本檔 §四 STRIDE 的 Information Disclosure
> 行已經把 `prompt_guard` 命中（與記憶完全無關的輸入）一併納入同一條日誌禁令，
> 亦即它們的實際適用範圍**比 `NFR7` 的字面寬**——這就是親代不成立的證據，而那個證據
> 在我自己的產出裡。三條已改為 `SEC-3`／`SEC-4`／`SEC-5`。
>
> **`NFR7.62` 留在 `NFR7` 之下不變**：它逐字就是在講情節記憶的讀取範圍，親代真實。

**這不是缺口**：ADR-0006 是由 `project.md` 承載的 hard constraint，不是由某條
inception `NFR` 承載的。把它們硬掛到 `NFR6`（記憶層 schema 隔離的 CI 驗證）之下
會製造一個**錯誤的親代**——而「引用錯層級會讓代價看起來比實際輕」正是本 intent
已記過的失誤形狀。故本檔給它們獨立前綴，並在 `traceability.json` 的 `reverse`
區塊逐條說明其來源。

## 二、需求

| ID | 需求 | 驗證方式 | 來源 |
|---|---|---|---|
| **`NFR6.60`** | 本單元讀記憶**只經 `K-08` 的 `MemoryFacade`**，**不得**直接讀 `memory` schema 或繞過 facade 的任何底層 service | 模組內 `import` 的結構斷言：禁止 import `memory_service`／`memory_types` 的底層查詢路徑 | `BR7.1`；`K-10` `behaviour_semantics.authorization_responsibility` 逐字 |
| **`SEC-1`** | `principal` **一律由參數傳入**，本單元不得自行從請求、context 或全域取身分 | 簽章斷言 ＋ 模組內無 `get_current_user`／`Request` 的 import | `BR7.2`；`K-10` 的 `classify(principal, session, text)` |
| **`SEC-2`** | 本單元**不註冊任何 FastAPI route／WebSocket 端點**。它的唯一對外面是出站的 OpenRouter 呼叫，且該呼叫**只經 `langgraph_runtime`**，不得自行 `httpx` 直打 | 模組內 `APIRouter`／`WebSocket` 0 命中；`httpx` 0 直接 import | `BR7.2`；`K-10` 的 `in-process` 宣告 |
| **`SEC-3`** | **日誌不得含使用者輸入文字（`text`）或候選標籤（`label`）。** 可記錄：`capability` 列舉值、`rank`、`score`、槽位數、述詞結果、耗時、錯誤型別 | 日誌格式的欄位白名單測試 | `project.md` 的公開 repo 輸出禁令；本站新定 |
| **`SEC-4`** | `prompt_guard` 命中**可被觀測**（計數或結構化事件），但該紀錄**不得含觸發它的輸入** | 斷言命中時有事件產生且事件欄位不含 `text` | `FR1.5`；`BR1.1`；ADR-0006 audit 面 |
| **`NFR7.62`** | 指涉詞解析呼叫 `MemoryFacade.search` 時，`kinds` 參數**不得含「情節」記憶**，只傳語意／程序 | **斷言 `kinds` 的實際傳值**（以替身捕捉呼叫參數） | `BR5.5` 的 `logic_executable`；`contract-summary.md:617-618` 的簽章；`components.md:179` 的三種記憶 |
| **`NFR9.60`** | 送往模型的請求**只帶判定意圖所需的最少上下文**；**不得**整段附上完整歷程 | 以替身捕捉請求 payload，斷言不含完整 `messageHistory` | `BR6.1`；ADR-0006 encryption 面（資料外送最小化） |

## 三、`NFR7.62` 是**現行防護**，不是前置護欄（修訂 1 推翻原判定，審查 `R-02`，Critical）

### 原本寫錯的是什麼

本節原文宣稱：「`MemoryFacade.write` **沒有任何呼叫者**（`contract-summary.md:1432`
的 `OQ-N3`，Critical，仍開著）。所以 `memory_records` 永不被填、`search` 永遠回空
——**`NFR7.62` 現在擋不到任何真實資料**」，並據此把它定性為**前置護欄**、把重檢
時機綁在 `OQ-N3` 關閉。

**這個前提已被現實推翻，而推翻它的東西就在這個 worktree 裡。**

### 實地查證（本輪複驗，非轉引）

| # | 事實 | 取得方式 |
|---|---|---|
| 1 | `backend/services/memory_router.py` **存在**，且是 `U8` 的 HTTP 層 | `[讀]` 該檔 |
| 2 | 它的 `@router.post`（`:158`）handler 直接呼叫 **`facade.write(...)`**（`:181-183`），參數含 `kind=payload.kind` | `[讀]` `:158-183` |
| 3 | 該端點 **不限制 `kind`**——docstring 逐字（`:176-177`）：「本端點**不限制** `kind`，因為 `[FD4]`=A 逐字『`kind` 由使用者指定且限於封閉集合』」，而那個封閉集合**含 `episodic`** | `[讀]` `:176-177`；`memory_types.py` 的 `MEMORY_KINDS` |
| 4 | `memory_router.py` 與 `memory_facade.py` 目前為**未受版控的新檔**（`git status` 回 `??`），由本 session 的 `U8` `code-generation` 產出 | `[跑]` `git status --short` |

### 這改變了什麼

**`OQ-N3` 問的是同進程寫入端（`U13`／`U12` 在 DAG 裡沒有 `→ U8` 的邊），而 `U8`
自己已經落地了一條 HTTP 寫入端。** 兩者是不同的缺口：`OQ-N3` 仍然開著（自動產生
記憶的路徑確實還沒有人擁有），但「記憶永遠是空的」**不再成立**——任何使用者今天
就可以 `POST /api/memory/records` 帶 `kind=episodic` 建一筆情節記憶。

**所以 `NFR7.62` 是現行防護**：若指涉詞解析在 `search` 呼叫中未真正排除 `episodic`，
那筆記憶**今天就能**被 `U11` 讀到，而 `AC6.1.3`（獨立對話無法解析共享對話的產出）
這條負向驗收會靜默失效。

| 項目 | 原判定 | **修訂後** |
|---|---|---|
| 可達性 | 不可達（死碼） | **可達**（`U8` 的 `POST /api/memory/records`，`kind` 不限） |
| 定性 | 前置護欄 | **現行防護** |
| 實作優先序 | 可等 `OQ-N3` 關閉 | **`code-generation` 第一輪就要實作斷言，不得遞延** |
| 重檢觸發 | `OQ-N3` 定案時 | **不需要觸發條件**——它現在就要成立；`OQ-N3` 關閉時只是**多一條**寫入路徑 |

### 兩處上游產出仍帶著這個已被推翻的說法（交接事項）

本站**不回改已完成單元的產出**（比照 `project.md` 的 `refined-mockups:c3`：
下游修正上游的內部瑕疵時，在本站明記是對齊修正、上游檔案本身不回改）。
但下列兩處會誤導實作者，必須在交接時點名：

| 檔案 | 它說了什麼 | 正確的讀法 |
|---|---|---|
| `construction/intent-router/functional-design/rules.md` 的 `BR5.5.reachability` | 「**目前不可達，刻意保留為前置護欄。** `MemoryFacade.write` 沒有任何呼叫者……本條現在擋不到任何真實資料」 | **該欄已失效。** `BR5.5` 是現行防護 |
| `construction/intent-router/functional-design/functional-spec.md` 的 `OPEN-IR11-5`（可達性那一列） | 同上，並訂「`OQ-N3` 定案時 `AC6.1.3` 必須重新檢視」 | 重檢**不必等** `OQ-N3`；`AC6.1.3` 的第二個入口現在就開著 |

**兩者都由 `U11` 的 `code-generation`（3.5，`ALWAYS`）消費**，故交接點明確。
`AC6.1.3` 在 `functional-design` 的 `traceability.json` 仍標 `OK`——**該標記依然正確**，
因為 `BR5.5` 確實覆蓋了這個入口；改變的只是「它現在就在擋」而不是「它在等」。

### 殘留缺口（維持，比照 `OQ-N2` 的形狀）

`kinds` 排除只關掉**情節記憶**這一個入口。語意記憶是「事實」，原則上仍可能載有
產出物名稱，而「用記憶理解術語」與「用記憶決定 `referent`」在**模型內部不可區分**
——這一半**無機械強制**。`contract-summary.md:1434` 的 `OQ-N2` 已立下先例：
「決定不加機制是可以的，不追蹤它不行」。

## 四、STRIDE（逐項，不跳過）

| 類別 | 本單元的攻擊面 | 處置 |
|---|---|---|
| **S** Spoofing | 同進程呼叫者若能自行構造 `principal`，即可用別人的身分分類與讀記憶 | `SEC-1`：`principal` 由參數傳入且本單元不自取；真正的身分取得在 `U13`，本單元信任呼叫端——這是 `in-process` 契約的既有信任邊界，不是本單元新增的 |
| **T** Tampering | 使用者輸入可嘗試操弄分類（prompt injection），使系統把危險請求路由到高權限能力 | `prompt_guard` 在**分類之前**（`BR1.1`），命中即不呼叫 LLM；`capability` 是**封閉列舉**（`BR2.2`），模型無法發明新能力；真正的授權在下游能力自己的 dependency 上 |
| **R** Repudiation | 使用者否認送出某個請求 | 本單元**不是**稽核的落點（它不持有狀態）。稽核由 `U10` 的訊息歷程與 `U12` 的工作項承擔。本單元只保證 `SEC-4` 的安全事件可觀測 |
| **I** Information Disclosure | ① 使用者自由文字外送第三方；② 日誌洩漏輸入；③ 記憶跨段洩漏 | ① `NFR9.60` 最小化＋既有實務（A1／A3 已如此，見問題檔 V8）；② `SEC-3`（**public repo，一次意外 echo 等同公開發布**）；③ `NFR7.62`＋其殘留缺口 |
| **D** Denial of Service | 大量請求打爆模型配額或拖垮延遲 | `NFR3.61`（5 秒硬逾時）＋`NFR3.62`（每輪 1 次呼叫）＋`NFR3.63`（0 重試）構成本單元側的上界。**帳戶層的花費上限由 OpenRouter 後台承載**（`NFR9`，`[F13]`），本 intent 不建計量機制——這是已核可的邊界，不是缺口 |
| **E** Elevation of Privilege | 分類結果把請求導向使用者無權使用的能力 | **本單元不執行任何能力**（`BR7.3`）。授權在 `U12` 交辦時與各能力自己的 dependency 上。本單元產出的 `capability` 是一個**建議**，不是一張通行證——這一點必須在 `U12` 的設計中成立，本檔記為對下游的依賴 |

## 五、對 `[N1]`=C（Jev）的安全面增量

| # | 事實 | 安全意涵 |
|---|---|---|
| 1 | 模型由 `google/gemini-3.7-flash` 改為 `typesafe/jev-1.13` | **出站目的地不變**（同為 OpenRouter 端點），故網路暴露面**零增量**。改變的是供應商內部路由，不在本平台的信任邊界內 |
| 2 | 型別化輸出走 tool/function calling | **降低**注入風險：回應被約束在我們宣告的 schema 內，模型無法回傳任意文字當作 `capability`。但 `BR2.2` 的封閉列舉驗證**仍須在本單元側做**——不得假設模型一定遵守 schema |
| 3 | `prompt` 計價 `$0.042/MTok`、`completion` 0 | 成本面的攻擊（大量長輸入）集中在 prompt 側，而 `NFR9.60` 的最少上下文正好壓制它。帳戶上限仍由 OpenRouter 後台承載 |

## 六、審查處置表（`review-01.md`，六項，`VERDICT: NOT-READY`）

**六項全部接受。** 兩個 Critical 都是我宣稱「已查證」但查證範圍或時間點不足造成的。

| ID | 嚴重度 | 判定 | 處置 |
|---|---|---|---|
| `R-01` | Critical | **接受** | `NFR4.60` → **`NFR4.70`**（`reliability-requirements.md` 兩處 ＋ `traceability.json`）。**錯因是我自己的 regex**：碰撞檢查跑的是 `grep -rhoE "NFR(1\|3\|6\|7\|8\|9\|10)\.[0-9]+"`，**分支清單裡沒有 `4`**，於是 `NFR4` 從未被檢查，而 `session-store` 已擁有 `NFR4.60`–`.65`。檢查已改為不帶分支清單的全掃 |
| `R-02` | Critical | **接受，並推翻原判定** | §三整節重寫。`backend/services/memory_router.py:158-183` 的 `POST /api/memory/records` 已呼叫 `facade.write(kind=payload.kind)` 且 docstring 逐字「本端點**不限制** `kind`」——`NFR7.62` 由「前置護欄」改判為**現行防護**，實作優先序由「可等 `OQ-N3`」改為「`code-generation` 第一輪就要實作斷言」。另點名 `functional-design` 的 `rules.md`（`BR5.5.reachability`）與 `functional-spec.md`（`OPEN-IR11-5`）仍帶著這個已被推翻的說法，列為交接事項，**不回改已完成單元的產出** |
| `R-03` | Major | **接受** | `NFR7.60`／`.61`／`.63` → **`SEC-3`／`SEC-4`／`SEC-5`**，比照 `SEC-1`／`SEC-2` 記在 §二之零。審查的論點成立：我對同一個問題用了兩套相反的處置，而**我自己的 §四 STRIDE 就是親代不成立的證據**（它把與記憶無關的 `prompt_guard` 命中納入同一條日誌禁令）。`NFR7.62` 留在 `NFR7` 之下不變 |
| `R-04` | Major | **接受** | 刪除「加斷路器＝加回行程內狀態，與 `NFR3.67` 直接衝突」這個論證。`NFR3.67` 逐字只禁**行程內**狀態並**明文開放** Redis，所以 Redis-backed 斷路器不違反它。改為誠實的版本：三項已定參數讓收益變小，剩下的那一項不夠大到值得本單元多一個對 `U10` 的寫入方向 |
| `R-05` | Major | **接受** | `performance-requirements.md` 新增「預算切分的兩個歸因缺口」一節。(a) 交接膠水時間（`U13` 解包／授權 → `U12` 建項 → 分派）懸在兩個預算之間，**本站不自行替下游分配**，列為第三段並指派 `U13` 的 `nfr-requirements`；(b) `contract-summary.md:1128-1131` 逐字規定 C1 不做 token 級串流、其「串流」是每秒輪詢的狀態事件，故 1200 ms 的「首字」對這類下游須重新定義為第一個 `progress` 事件抵達 WS 的時刻 |
| `R-06` | Major | **接受** | 撤回「本站解掉了它」。新增 `tech-stack-decisions.md` 的 **`TS-6`**：`OPENROUTER_API_KEY` 列為 blocking 前置條件（只有使用者能滿足、最晚期限為 `build-and-test` 之前、未滿足即 `Unverified` 並觸發失敗升級），並在 `traceability.json` 的 `reverse` 追蹤。`build-and-test.md:144-146` 的逐字已複驗 |

**兩個 Critical 的共同形狀，值得記下來**：它們都不是判斷錯誤，是**查證的範圍或
時間點不夠**——`R-01` 是我在檢查用的 regex 裡列舉分支（把盲區設成自己的預期），
`R-02` 是我引用了一個**會隨旁支單元並行推進而變動**的事實（`OQ-N3` 在
`contract-design` 當時為真，而 `U8` 的 `code-generation` 已經推翻它）而沒有在
撰寫當下重新確認。第二種特別值得警惕：**在 per-unit 並行的 Construction 裡，
「某個東西還沒有人實作」這類事實的保鮮期很短。**
