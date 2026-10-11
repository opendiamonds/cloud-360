# Code Generation 問題檔 — `U10 session-store`

> 本站只有一個關卡：Plan Approval。設計層的待決項已在四個前置站定案
> （`[S1]`–`[S3]`、`[N1]`–`[N3]`、`[D1]`–`[D2]`、`[I1]`），本站不重問。

## 計畫摘要

| 項目 | 值 |
|---|---|
| 交付物 | **20 個檔：9 新、11 改**（另含四個「刻意不動」作為可驗證面） |
| 步驟數 | **12 步**（含 6 項突變驗證） |
| 四層形狀 | `session_store` → `redis_gateway` → `session_types`（純函式）＋ `session_scripts/*.lua` |
| 新依賴 | **一個**（Redis 客戶端）。`NFR8.41` 授權，且實讀確認 `requirements.txt` 目前無任何 Redis 客戶端 |
| 新 CI job | **零**（`[I1]`=B 的直接目的） |
| 新 HTTP 端點 | **零**（`BR5.3`）。故 `openapi.json` 與 `api.d.ts` 的 diff 必須為空 |
| schema 變更 | **零**。故 `project.md` 的 `schema_rbac.sql` ＋ `DEPLOY.md` 同步 blocking 規則**不觸發** |
| 部署設定變更 | **三項**：`maxmemory-policy` → `noeviction`、新環境變數、部署後還原驗證步驟 |
| **`LOCAL-DEV.md`** | **必須同步**（blocking）——本計畫動到兩份 `.env.example` 與 `render-env.sh` |

## 本計畫關掉的七項上游承接（含一個 Critical）

| 來源 | 嚴重度 | 本計畫的落點 |
|---|---|---|
| `infrastructure-design` `R-01` | **Critical** | Step 9.2：還原驗證的等待條件由 healthcheck 改為**實際讀回 fixture 成功**。原設計依賴的 healthcheck 在 AOF 載入期間會通過，而本單元自己早已記載它不可信 |
| `nfr-requirements` `R-02` ＋ `nfr-design` `R-02` | Major ×2 | Step 2.2 ＋ 4.2：新增 `SessionMessageTooLong` 例外型別與入口長度檢查（`OPEN-N10-6`）。`K-09` 原本只有一個例外型別，承載不了「訊息太長」 |
| `infrastructure-design` `R-02` | Major | Step 9.3：刪掉假緩解。改為**明確宣告**該步驟會中斷當下使用者的 session，並置於部署序列最後 |
| `nfr-requirements` `R-01` | Major | Step 5.4：日誌白名單做成**建構函式簽章**而非文件約定；`EC6` 的對齊依 `BR3.6`（識別碼不是內容） |
| `nfr-design` `R-01` | Major | 不重決儲存結構（`[D1]`=A 已定），Step 1.3 記錄對齊 |
| `infrastructure-design` `R-03` | Minor | Step 12.1：`traceability.json` 的 id 來源改為上游 `traceability.json` ∪ markdown |

## 三件本計畫**無法**在 CI 驗證的事（如實記載，非遺漏）

1. **Lua 的實際行為與原子性**——backend 測試不連 Redis，而新增連 Redis 的 CI job 已於 `[I1]` 否決。
2. **`noeviction` 的 OOM 行為**——需要把 Redis 灌到 256MB。
3. **重啟還原五項**——CI 測試 stack 無 AOF、無 volume（實讀確認）。

三者的真實驗證點都是 `[I1]`=B 的部署後步驟。**把它們列出來，使「三個指令全綠」
不會被讀成「Redis 行為已驗證」。**

## 承接自上游而本站不解決的四項

- **`OPEN-N10-3`**（工作項集合共用同一個 key 但不在本單元的記憶體上界內）→ `U12`
- **`OPEN-N10-7`**（`U12` 的 Hash 欄位命名空間不得與 `seg:`／`tgt:`／`meta` 衝突）→ `U12`
- **`OPEN-N10-1`／`OPEN-N10-2`**（線框的 `7 天內`／`30 天內` 不可達；`RecentConversations` 無擁有單元）→ **無自然承接站**，已於前站閘門重新提交
- **`OPEN-N10-4`**（`NFR4.60` 的訊號無告警管道消費）→ **無自然承接站**
- **`tcms-test-cases`**（`project.md ## Mandated` 的 blocking stage）→ 至今未對本 intent 任何單元執行過

## Plan Approval

[Approval Fingerprint]: sha256:v3:454e1846d80a6fb690d1e1b505ddf9c6f7fb58e273f43ff09e5d340dcb240050
[Planned Source]: 257cdacdb3845a4bcd35333adcd66d2dc4e2e2b11aa500547a0dd2d30802f20a

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
