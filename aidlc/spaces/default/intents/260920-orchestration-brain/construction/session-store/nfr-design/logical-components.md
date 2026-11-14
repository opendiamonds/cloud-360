# Logical Components — `U10 session-store`

> 本檔是 NFR 設計與 Infrastructure Design 之間的橋：給出**元件層**的視圖，
> 說明上述 NFR 模式各自落在哪裡、失敗域如何劃分、爆炸半徑有多大。
> 設計階段產出，不是實作。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `functional-spec.md` | `W1`–`W8` 的流程與 §二 的狀態機——模組邊界由它們切出 |
| `security-requirements.md`／`security-design.md` | `NFR4.46` 的三項禁令（不判權／不取身分／不對外）——它直接決定哪些模組**不得存在** |
| `reliability-requirements.md` | `NFR4.50`–`NFR4.57`；原子性要求決定 Lua 的職責 |
| `performance-requirements.md` | `NFR3.40`–`NFR3.43` 的預算；連線池屬哪一層 |
| `scalability-requirements.md` | `NFR4.41` 的硬上界；本單元無狀態故可多 worker |
| `observability-requirements.md` | `NFR4.63` 的白名單須有單一建構點 |
| `tech-stack-decisions.md` | `NFR8.41`：Redis 客戶端為新增依賴 |
| `contract-summary.md`（`K-09`） | 對外只有五個方法；consumers 為 `U11`／`U12`／`U13` |

## 一、模組分解

`team.md` 逐字要求新模組走三層形狀（router → service → 純函式），
但**本單元沒有 router**（`BR5.3`：不暴露端點）。故形狀為：

```
  U11 / U12 / U13（同進程呼叫端）
            |
            v
  [ session_store ]      ← K-09 的五個方法；唯一對外面
            |
    +-------+--------+
    v                v
 [ session_types ]  [ redis_gateway ]   ← 連線池、逾時、重試、原因碼分類
   純資料形狀             |
   零 I/O                v
                    [ scripts/*.lua ]   ← 原子操作的唯一載體
```

| 模組 | 職責 | 不得做什麼 |
|---|---|---|
| **`session_store`** | `K-09` 的五個方法；組裝參數、呼叫 `K-07`、委派 `redis_gateway` | 不得判權（`NFR4.46`）、不得自取身分、不得直接組 Redis 指令字串 |
| **`session_types`** | `BrainSession`／`ConversationSegment`／`SessionMessage` 的形狀與序列化；段識別的封閉集合（`EC4`） | **零 I/O、零 Redis import** —— 它是本單元唯一可做 property-based 測試的層 |
| **`redis_gateway`** | 連線池、逾時、`[D2]`=A 的重試、Lua 腳本載入、**三種原因碼的分類**（`NFR4.62`） | 不得認識 `BrainSession` 的語意（它只處理鍵、欄位、位元組） |
| **`scripts/*.lua`** | `append+trim+expire`、`switch_to_isolated`（建段＋複製作業對象＋改 `pageModes`，見 `reliability-design.md` §三第 3 列） | 不得做與 session 數量相關的工作（會阻塞 Redis 單執行緒） |

**`session_types` 的零 I/O 是刻意的**：`project.md` 的 PBT hard constraint 對本單元
判為 N/A（非 IaC generator／cost calculator／agent routing），但
`nfr-requirements` 已指出 `BR3.4` 的修剪是天然的 PBT 標的。**修剪邏輯的真實載體
是 Lua**（`performance-design.md` 的唯一載體原則），所以 `session_types` 裡放的是
**修剪的參考實作**，用於 PBT 與對 Lua 行為的交叉驗證——**不是**第二個生產載體。
這個區別必須在 `code-generation` 保持，否則就變成 `team.md` 禁止的「第二份物化」。

## 二、失敗域與爆炸半徑

| 失敗 | 爆炸半徑 | 偵測面 |
|---|---|---|
| Redis 實例不可用 | **全部使用者的全部 session**（單點，已接受） | `redis_unreachable` ERROR 日誌；使用者立即可見 |
| Redis 記憶體耗盡 | **全部使用者的寫入**；讀取不受影響（`NFR4.51`） | `redis_oom` ERROR 日誌 ＋ `NFR4.60` 的使用率訊號 |
| Lua 腳本錯誤 | **全部 `append_message`**（腳本是靜態的，錯就全錯） | `redis_command_error`；**會在第一次呼叫就出現**，不是漸進 |
| ACL 拒絕 `EVAL` | 同上 | 同上。這是 `security-design.md` 列為部署時查核項的那一條 |
| 單一 session 的資料損毀（如 JSON 解碼失敗） | **一個使用者** | 解碼例外。設計處置：**不自動刪除該 key**——無聲修復會讓損毀的成因永遠查不到；回 `SessionBackendUnavailable` 並記 `sessionKey` |
| `K-07` 不可用（PostgreSQL 掛） | 只有 `set_work_target`；其餘四個方法**不受影響** | `HierarchyError` 原樣上傳 |

**最後一列是本單元的分層收益**：作業對象的授權走 `K-07`，而歷程與模式不走。
PostgreSQL 掛掉時使用者仍能對話，只是不能切換作業對象。這不是刻意設計出來的
降級，是分層的自然結果——但值得寫下來，因為它是真的。

## 三、共用資源

| 資源 | 共用者 | 本單元的約束 |
|---|---|---|
| **Redis 實例** | 本單元 ＋ `U12` 的工作項集合（`K-11`，同一個 session key） | `OPEN-N10-3`：工作項集合**不在**本單元的記憶體上界內；容量算式的前提沒有人保證 |
| **同一個 session key** | 本單元的 Hash 欄位 ＋ `U12` 的工作項欄位 | **欄位命名空間必須分開**：本單元用 `seg:`／`tgt:`／`meta` 前綴。`U12` 的前綴由該單元定，但**不得**與這三個衝突——本檔把這一點記為對 `U12` 的介面約束 |
| **PostgreSQL** | 經 `K-07`，與全 repo 共用 | 本單元只讀、不寫（`K-07` 逐字唯讀冪等） |
| **連線池** | 本單元獨有 | 不與其他 Redis 使用者共用——目前**沒有其他使用者**（`technology-stack.md:206` 實測：`backend/` 應用程式碼零 Redis import） |

### 新增的介面約束（本站產出，須回報）

> **`U12` 在同一個 session key 上使用的 Hash 欄位，不得與 `seg:`／`tgt:`／`meta`
> 三個前綴衝突。** 上游 `K-09.data_shape` 的 note 只說「工作項集合亦放在同一個
> session key 之下」，**沒有說它們怎麼共存**——在 `[D1]`=A 把值改成 Hash 之前，
> 這個問題不存在（兩者各自是什麼形狀未定）；之後它變成一個真實的命名空間問題。
>
> **承接**：`U12 work-orchestrator` 的 `nfr-design`（3.3，CONDITIONAL、per-unit；
> 轉移目標 `U12` 的 `code-generation`，3.5，**ALWAYS**）。**已查證 `U12` 在游標之後**
> （`construction/` 下無 `work-orchestrator/`）。記為 `OPEN-N10-7`。

## 四、本單元**不存在**的元件（逐項附禁止來源）

| 不存在 | 禁止來源 |
|---|---|
| HTTP router／WebSocket 端點 | `BR5.3`／`NFR4.46` |
| 權限判定模組 | `BR5.1`；授權一律委派 `K-07` |
| 行程內 session 快取 | `BR1.2`／`NFR4` 逐字「不得放行程記憶體」 |
| 熔斷器 | `[D2]`=A 的否決，理由見 `reliability-design.md` §一 |
| 稽核寫入模組 | `functional-spec.md` §七 的 Audit logging 格：本單元刻意不寫稽核列 |
| 背景清除排程 | `BR1.5`：TTL 是唯一清除機制，`ADR-005` 拒絕第二條路徑 |
| 連線登錄（socket registry） | `K-12` 的 `fanout_mechanism_and_its_assumption.registry` 逐字指定它為**行程內**且屬 `U13` |

**這張表比上面那張更有用**：它讓「為什麼沒有 X」有答案，而不是讓下一個人
憑好意加回來。
