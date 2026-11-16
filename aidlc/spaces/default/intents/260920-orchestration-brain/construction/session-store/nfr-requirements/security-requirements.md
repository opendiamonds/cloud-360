# Security Requirements — `U10 session-store`

> 本檔是本站的 **review artifact**。
> 編號自 `.40` 起，與既有 12 個單元不重疊。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `requirements.md:500-508`（`NFR4`） | 「一律放 Redis，不得放行程記憶體」與重啟還原的可測不變量 |
| `requirements.md:537-545`（`NFR8`） | 新增元件的部署設定完整性，與「失敗模式無聲」的理由 |
| `rules.md`（本單元） | `BR3.6`（內容不得入 log）、`BR4.6`／`BR4.7`（授權委派與逐段驗證）、`BR5.1`–`BR5.3`（不判權、不取身分、不對外） |
| `functional-spec.md`（本單元） | `W6` 的授權路徑、`W8` 的失效路徑、§七的 ADR-0006 四面向 |
| `contract-summary.md:684-742`（`K-09`） | `authorization_responsibility` 逐字「本單元不自行判權」 |
| `deploy/docker-compose.deploy.yml:229-243` | Redis 的實際 ACL 與淘汰設定（實讀） |
| `codekb/chiton/technology-stack.md:206` | 逐字「**服務已佈建**（`redis:8-alpine`、AOF volume、ACL、healthcheck）；`REDIS_URL`／`REDIS_USER`／`REDIS_PASSWORD` 已由 `render-env.sh:121` 等寫入並列於兩份 `.env.example`…`test_render_env_redis.py` 已鎖住環境契約（`K-01`）」——故 `NFR4.44` 的 ACL 面**不是本單元要建立的，而是本單元不得繞過的** |

## 本單元的資料敏感度分級

| 資料 | 分級 | 理由 |
|---|---|---|
| `SessionMessage.text`（對話內容） | **Confidential** | 個人對話歷程。內容由使用者自由輸入，可能含任何東西 |
| 作業對象三層識別碼 | Internal | 本身是整數 id；但**組合起來會洩漏某人正在看哪個專案** |
| `sessionKey`／`userId` | Internal | 身分關聯鍵 |
| `pageModes`／`expiresAt` | Internal | 無敏感內容 |

**本 repo 為 public，Actions log 公開可讀**（`project.md` 逐字「一次意外 echo
即等同公開發布」）。本單元是本 intent 中**第一個常態持有 Confidential 級自由文字**
的執行期元件——`U8 memory-service` 持有記憶內容但有自己的授權模型與稽核；本單元
持有的是**尚未成為記憶**的原始對話。

## 需求

| ID | 需求 | 判定方式 | 來源 |
|---|---|---|---|
| **NFR4.44** | 本單元**只能**以 `REDIS_USER` 指定的 ACL 使用者連線，不得以 `default` 連線 | 連線字串以 `REDIS_USER`／`REDIS_PASSWORD` 組成；`default` 已被 `U1` 收窄為 `+@connection`（`deploy/docker-compose.deploy.yml:236-241` 實讀），故誤用 `default` 會在第一個資料指令上失敗——**這是 `U1` 已建立的保護，本條只要求本單元不繞過它** | `NFR4`；`U1` 的 `NFR4.1(b)/(c)` |
| **NFR4.45** | **任何** log、例外訊息或錯誤回應都不得包含 `SessionMessage.text`、整個 `ConversationSegment` 或整個 `BrainSession` 物件 | **靜態斷言**：掃本單元全部 log 呼叫的引數形狀，允許的欄位白名單為 `sessionKey`、`segmentId`、筆數、耗時；**白名單而非黑名單**（黑名單漏一個就等於沒有）。另於整合測試斷言 404／錯誤回應體不含 fixture 的訊息文字 | `BR3.6`；`EC6`；`project.md` 的公開 repo 禁令 |
| **NFR4.46** | 本單元不得自行判權、不得自行從請求取身分、不得暴露任何 HTTP 或 WebSocket 端點 | 靜態斷言三項：模組內 `require_story_action` 零命中、不 import request／websocket 型別、不註冊任何 router | `BR5.1`–`BR5.3`；`K-09.authorization_responsibility` 逐字 |
| **NFR4.47** | **每一段**的作業對象寫入各自經 `K-07` 的 `resolve_work_target` 驗證；唯一例外是 `BR4.2` 的初始化複製（來源為已驗證的共享段值） | allow/deny 雙向測試：具權限者寫入成功、無權限者得到 `HierarchyForbidden` 且**不落地**；並對**第二段**（非 `shared`）各跑一次——只測 `shared` 段會漏掉 `[S3]`=A 新引入的那一面 | `BR4.6`／`BR4.7`；`hierarchy_facade.py:277-281` 逐字「這是同進程路徑，沒有任何 router 層會替它補上範圍檢查」 |
| **NFR4.48** | 作業對象的驗證是**寫入時點**驗證；本單元**不做讀取時重驗**，此為明示的設計選擇而非遺漏 | 文件化即滿足；並要求在 `K-09` 的消費端文件中指出：識別碼的時效性風險（撤權、實體被刪除）由消費端在**真正動用**時自行決定是否重驗 | **審查 `R-02`（`functional-design` iteration 1）的處置**；`K-04` 的 `DG-2`（Project／System 刪除的 cascade）仍未定案 |

## STRIDE（逐類，不留空白）

| 類別 | 本單元的面 | 處置 |
|---|---|---|
| **S — Spoofing** | 呼叫方可傳入任意 `session_key` 與 `principal` | `BR1.1`：key 由 `U13` 自**已驗證**使用者 id 推導，本單元不產生也不接受推導以外的來源；`BR5.2`：`principal` 由呼叫方傳入而非自取。**本單元是同進程元件，其信任邊界就是呼叫方**——這一點明寫，不假裝本單元能自行驗證身分 |
| **T — Tampering** | Redis 內容被竄改 | ACL 使用者 ＋ 無對外埠（`K-01` 逐字 `compose 內部網路only；不得 publish port`）。**本單元不做應用層完整性校驗**——威脅模型假設 compose 內部網路已是信任邊界（同 `U1` 的 `security-design.md D-2 subject class 2`） |
| **R — Repudiation** | 誰改了作業對象、誰送了訊息 | **本單元刻意不寫稽核列**：session 狀態 24 小時即消失，與記憶層的稽核是兩件事（`ADR-016` 逐字 session 層 vs 內容層）。帳號活動稽核由 `U13` 握手以 `record=True` 承擔（`K-12` 的 `activity_record`）。**這是宣告，不是遺漏** |
| **I — Information Disclosure** | 對話內容外洩 | 三道：`NFR4.45`（不入 log）、`NFR4.44`（ACL）、`BR3.2`（段的讀取視圖只含本段——**跨段洩漏也是洩漏**，而 `AC6.1.3` 正是它的負向驗收） |
| **D — Denial of Service** | 單一使用者把 Redis 灌滿 | `BR3.4` 的每段筆數上限（`[N2]`=A：**200 則／段**）給出每個 session 的記憶體上界；`[N3]`=A 的 `noeviction` 使容量耗盡時**寫入大聲失敗**而非無聲淘汰別人的 session。**兩者缺一不可**：只有上限而仍是 `allkeys-lru`，灌滿者會讓**別人**的 session 消失 |
| **E — Elevation of Privilege** | 以別人的識別碼取得作業對象 | `BR4.6` 委派 `K-07`，而 `K-07` 的 `BR6.1` 對不屬請求者的目標回「查不到」。`BR4.7` 把這道檢查擴到每一段 |

## ADR-0006 Security Baseline 四面向

承 `functional-spec.md §七` 的判定，**不重判適用性**，只列 NFR 層的增量。

| 面向 | 判定 | 本檔的落點 |
|---|---|---|
| **IAM** | 適用 | `NFR4.46`（不判權、不取身分、不對外）＋ `NFR4.47`（逐段驗證，含其唯一例外）＋ `NFR4.44`（ACL 使用者） |
| **Encryption** | 適用，無新增演算法 | Redis 憑證以 ACL 承載，`K-01` 逐字要求 `REDIS_PASSWORD` **不得含 `$`** 且以 `openssl rand -hex 32` 產生。傳輸在 compose 內部網路。**不寫「不適用」** |
| **Network exposure** | 適用，**零增量** | `NFR4.46` 第三項（不暴露端點）＋ Redis 本身無 `ports:`。本單元是該服務的第一個真實消費者，故該約束自本單元起才有實際後果 |
| **Audit logging** | 適用 | 正向：無（見上方 Repudiation 的宣告）。**反向是禁令**：`NFR4.45` 禁止內容進入任何 log |

**四面向皆適用，無不適用項。**

## 本站查出、須回報上游的兩項（`[N1]`=A 的直接後果）

### `OPEN-N10-1`：已核可線框的兩個分組在現行儲存設計下永不可達

`mockups.md:833-836`（`M16`）畫出 `今天`／`7 天內`；`interaction-spec.md:736` 的
`default` 狀態逐字「依時間分組（今天／**7 天內**／**30 天內**）」。而
`ADR-005` 逐字「TTL 24 小時…三者一起消失」、`ADR-016` 逐字把對話歷史的實體落點
定在 `SessionContext`。**兩者不能同時成立**，`7 天內` 與 `30 天內` 永不可達。

`[N1]`=A 定案維持 24 小時，故本項**回報而不自行修改已核可線框**。
**承接**：`refined-mockups`（2.5，CONDITIONAL，且**已完成且在游標之前**）——
故實務承接站為 `units-generation`（2.7，`ALWAYS`，亦在游標之前）。
**兩者皆在游標之前，意即本項沒有有效的下游承接站**，依 `project.md` 的規則
如實記為「**無自然承接站**」並在本站的完成摘要重新提交使用者裁決。

### `OPEN-N10-2`：`RecentConversations` 沒有任何單元擁有它

以 `grep -rl` 掃全 record：它只出現在 `refined-mockups` 的四份產出、
`domain-design/decisions.md`（`ADR-016` 的理由段），以及本單元的兩份問題檔。
**`units-generation`／`contract-design`／`delivery-planning` 三處合計 0 命中。**
`U14 entry-page-ui` 的交付清單（`unit-of-work.md:180`）逐字不含它。
且**全部 FR 與全部 AC 中沒有任何一條**要求「列出最近的對話」。

**這一項與 `OPEN-N10-1` 必須一併看**：`ADR-016` 把對話歷史的保存參數指派給本站，
理由之一逐字是「`RecentConversations.hidden` 在使用者送出第一則訊息之後就永遠
不可達，除非對話歷史有清除端」——**但那個元件本身沒有實作落點**。為一個沒有需求、
沒有單元、沒有契約的畫面元素設定保存參數，是在為不存在的消費端做設計。
**承接**：同 `OPEN-N10-1`，**無自然承接站**，於完成摘要重新提交。

## 本單元**不**負責的安全面（明列）

| 項目 | 歸屬 |
|---|---|
| WebSocket 握手的 token 驗證與 subprotocol | `U13 brain-gateway`（`K-12`） |
| 記憶內容的可見範圍與稽核 | `U8 memory-service`（已完成） |
| per-project 授權判定 | `U19 membership-service`（`ADR-012`） |
| Redis 容器本身的 ACL 建立與憑證產生 | `U1 brain-infra`（已完成） |
