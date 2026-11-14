# Security Design — `U10 session-store`

> 本檔是本站的 **review artifact**。設計階段產出：描述架構與策略，不是實作。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `security-requirements.md` | `NFR4.44`（ACL 使用者）、`NFR4.45`（日誌白名單）、`NFR4.46`（不判權／不取身分／不對外）、`NFR4.47`（逐段授權驗證）、`NFR4.48`（寫入時點驗證）、STRIDE 表、ADR-0006 四面向 |
| `reliability-requirements.md` | `NFR4.50` 的 `noeviction`——它同時是一條 DoS 面的設計 |
| `observability-requirements.md` | `NFR4.61`–`NFR4.63` 的日誌要求與白名單 |
| `performance-requirements.md` | `NFR3.42` 的 150ms 預算——它涵蓋 `K-07` 的授權往返 |
| `scalability-requirements.md` | `NFR4.41` 的硬上界要求——它是 DoS 面的另一半 |
| `tech-stack-decisions.md` | `NFR8.41` 的客戶端選型條件 |
| `functional-spec.md` | `W6` 的授權呼叫順序、§七的四面向判定 |
| `contract-summary.md`（`K-09`／`K-07`） | `authorization_responsibility` 與 `resolve_work_target` 的契約 |

## 一、授權架構：本單元是**委派者**，不是判定者

```
U13 (握手已驗證)  --principal 由參數傳入-->  SessionStore.set_work_target
                                                   |
                                                   | 1. 以該 principal 呼叫
                                                   v
                                          K-07 HierarchyFacade.resolve_work_target
                                                   |  BR6.1：不屬請求者 → 查不到
                                                   v
                                          2. 只寫解析後的結果進該段
```

**三個不可省的設計點**：

1. **`principal` 一律由參數傳入**（`NFR4.46`／`BR5.2`）。本單元**不 import** 任何
   request／websocket 型別——這是可機械檢查的形狀，不是口頭約定。
2. **解析在前、寫入在後**，且寫入的是**解析結果**而非呼叫方傳入的原始識別碼
   （`W6` 第 6 步）。若寫入原始值，`K-07` 的檢查就只是一道裝飾。
3. **每一段各自驗證**（`NFR4.47`／`BR4.7`）。`[S3]`=A 把作業對象從一組變成每段一組，
   驗證若仍只跑一次，段數一多就有 N−1 組未驗的值。**唯一例外**是 `BR4.2` 的
   初始化複製（來源是已驗證的共享段值），該例外已在 `rules.md` 逐字寫出。

### 設計上的對齊修正：`EC6` 與 `NFR4.61`／`NFR4.63` 的字面衝突

**這是對齊修正，不是本站的新定案。** `nfr-requirements` 審查 `R-01`（Major）指出：
`entities.md` 的 `EC6` 逐字「本實體的**任何欄位**都不得出現在任何 log 或錯誤訊息中」，
而 `BrainSession` 的欄位清單含 `sessionKey`；但 `NFR4.61` 要求每次拋出都記
`sessionKey`、`NFR4.63` 的白名單第一項就是它。照 `EC6` 的字面實作會違反 `NFR4.61`，
反之亦然。

**操作性的規則是 `BR3.6`**，它的範圍正確地限於 `SessionMessage.text` 與整個
`ConversationSegment`——**識別碼不是內容**。本檔據此設計：

| 可入日誌 | 不可入日誌 |
|---|---|
| `sessionKey`、`segmentId`、方法名、筆數、耗時、錯誤原因碼 | `SessionMessage.text`、整個 `ConversationSegment`、整個 `BrainSession`、三層作業對象的識別碼組合 |

**最後一項是本檔新增的收窄**：`NFR4.63` 的白名單沒有提到作業對象識別碼，而
`security-requirements.md` 的資料分級把「三層識別碼的**組合**」列為 Internal 並
逐字註明「組合起來會洩漏某人正在看哪個專案」。故本檔明訂它**不入日誌**——
白名單原本就不含它，此處是把「不在白名單內」這件事講明白，避免被讀成未定。

**上游檔案不回改**（`entities.md` 與 `security-requirements.md` 的收據皆已 terminal）。
`EC6` 的措辭修正承接：`U10` 的 `code-generation`（3.5，**ALWAYS**，游標之後）。
**可執行的通則**：全稱禁令（「任何欄位」）在跨站引用時會超出作者原意；
寫 `EC`／`BR` 類禁令時改為逐項列舉或明寫排除項。

## 二、Lua 腳本的安全面（`[D1]`=A 新引入）

| 風險 | 處置 |
|---|---|
| **腳本注入**——若把使用者文字拼進腳本字串 | **腳本為靜態常數，使用者資料一律經 `ARGV` 傳入**，絕不以字串拼接組成腳本。這與既有的「SQL 一律參數化」同一條紀律（`code-generation-patterns.md` 逐字「Parameterize all database queries (no string concatenation)」） |
| **ACL 是否允許 `EVAL`** | app 使用者為 `+@all -@admin -@dangerous`（`deploy/docker-compose.deploy.yml:246-248` **實讀**）。依 Redis 文件的 ACL 分類，`EVAL`／`EVALSHA` 屬 `@slow @scripting`，**不在** `@admin` 或 `@dangerous`。**本結論是依文件推理，非實地執行**（本機無該實例），故列為 `code-generation` 的部署時查核項：以 app 身分實跑一次 `EVAL` 確認不被拒 |
| **腳本在 Redis 上以單執行緒執行，長腳本會阻塞全服務** | 腳本只做「解碼一個陣列 → 追加 → 修剪到 200 → 編碼寫回」，其成本上界由 `BR3.4` 的 200 與 `NFR4.41` 的欄位上界共同封住。**不得**在腳本內做迴圈掃描全部欄位或任何與 session 數量相關的工作 |
| **`cjson` 對超大字串的行為** | 受 `OPEN-N10-6`（見下）約束——目前沒有任何一層限制單則訊息長度 |

## 三、DoS 面：兩道缺一不可，而其中一道目前是破的

`security-requirements.md` 的 STRIDE 表已記：`BR3.4` 的筆數上限 ＋ `[N3]`=A 的
`noeviction` 兩者缺一不可。**但 `nfr-requirements` 審查 `R-02`（Major）查出第三件事**：

> 沒有任何一層限制 `SessionMessage.text` 的**長度**。`BR3.4` 只管筆數。
> 於是「200 則」這個上限對記憶體佔用**不構成上界**——一個 session 可以用
> 少數幾則巨大訊息吃掉遠超 300 KB。

### `OPEN-N10-6`：單則訊息長度上限（本站指定形狀，數值留下游）

**本檔的設計處置**：長度檢查必須放在 **`SessionStore.append_message` 進入時**，
而不是 Lua 內——理由是拒絕要能帶出一個明確的錯誤給呼叫方（`U13` 要能告訴使用者
「訊息太長」），而 Lua 的錯誤是字串、不利於型別化處置。

**數值不在本站定**：它是產品面的輸入長度限制（使用者可以貼多長的文字進對話框），
而 `requirements.md` 的 `FR1.1` 逐字接受自由文字輸入且**無長度上限**。
本站只定三件事：① 它**必須存在**；② 檢查點在 `append_message` 入口；
③ 超限的行為是**拒絕並回可辨識的錯誤**，不是截斷——截斷會讓使用者的訊息被默默
改掉。**承接**：`U10` 的 `code-generation`（3.5，**ALWAYS**，游標之後），
且若數值須由產品決定，該站須重新提交使用者。

## 四、STRIDE 的設計層處置（承 `security-requirements.md` 的威脅表）

| 類別 | 本檔新增的設計面 |
|---|---|
| Spoofing | 無新增。`principal` 的來源邊界即 `U13`，已於 §一 畫出 |
| Tampering | **新增**：Lua 腳本為靜態常數 ＋ `ARGV` 傳參（§二） |
| Repudiation | 無新增。本單元刻意不寫稽核列，理由已在 `security-requirements.md` |
| Information Disclosure | **新增**：作業對象識別碼組合明確排除於日誌白名單之外（§一） |
| Denial of Service | **新增**：`OPEN-N10-6` 的長度上限設計形狀（§三）；Lua 腳本的成本上界（§二） |
| Elevation of Privilege | **新增**：解析在前、寫入解析結果（§一 第 2 點）——寫入原始識別碼會讓 `K-07` 的檢查形同虛設 |

## 五、ADR-0006 四面向：設計層的落點

承 `security-requirements.md` 的判定，**不重判適用性**。

| 面向 | 本檔的設計落點 |
|---|---|
| **IAM** | §一 的三個不可省設計點；`NFR4.47` 的逐段驗證在 `W3` 第 5 步的例外已逐字寫明 |
| **Encryption** | 無新增。Redis 憑證由 ACL 承載，傳輸在 compose 內部網路。**不寫「不適用」** |
| **Network exposure** | 無新增。本單元不暴露端點；Lua 腳本不引入任何對外面 |
| **Audit logging** | §一 的日誌可／不可清單；§二 的腳本不記錄 `ARGV` 內容 |

**四面向皆有本檔可指的落點，無不適用項。**
