# Code Generation 問題檔 — `U18 project-meta-data`

## 計畫摘要（供 Plan Approval 判讀）

`spec` 單元：**三張新表的 DDL** ＋ 兩份部署資產的 blocking 同步
＋ `[P1]`=A 的獨立遷移腳本（涵蓋 `U5` ＋ `U18`）＋ 真實 PostgreSQL 的 CI 斷言。
**零應用程式碼、零端點、零畫面、零 ORM model。**

### 要寫的五個檔案

| # | 檔案 | 內容 |
|---|---|---|
| 1 | `schema_rbac.sql` | 新增 `J) U18 project-meta-data` 區塊：三表 ＋ 索引 ＋ CHECK ＋ **三條**外鍵 ＋ COMMENT |
| 2 | `backend/scripts/run_meta_schema_migration.py` | `[P1]`=A：一支腳本建 `U5` ＋ `U18` 的全部新物件，單一交易、自我終檢、非零碼結束 |
| 3 | `backend/scripts/verify_meta_schema.sql` | 12 條純 SQL 斷言（`P1`–`P12`） |
| 4 | `.github/workflows/ci.yml` | 擴充既有 `memory-schema` job 一個步驟 |
| 5 | `DEPLOY.md` | `BR3.3` 的 blocking 同步：表清單 ＋ `psql` 驗證 ＋ 腳本執行步驟 |

### 測試策略與方法論

Testing Contract 解析為 **`test-after`**、策略 `standard`、`brownfield`。
五個可測層中**只有 Data model / database behavior 適用**（本單元零程式碼、零端點、
零畫面），其餘四層的步驟據此省略。12 條斷言分佈 4／4／4（三張表＝三個 component），
落在 `standard` 的 5–8 區間內。**不寫 Python 測試**：既有測試走 in-memory SQLite，
而本單元要驗的是 PostgreSQL 的外鍵缺席、`ON DELETE` 行為與 partial index
——SQLite 對這些語意不同，在它上面「通過」不構成任何保證。

### 三件要請你注意的事

1. **本計畫會補上 `entities.md` 缺的九個欄位。** `nfr-design` 查出 `entities.md`
   比 `components.md:819`／`:820` 少九個欄位（`ReselectionEvent` 5、
   `SystemRequirementField` 4），其中六個正是 `FR12.4b` 與 `ADR-015` 點名的稽核
   事實，而 `AC12.2.2` 的 Then（「顯示**誰在何時把角色由什麼改為什麼**」）需要
   其中四個。該站已把回補指派給本站（`OPEN-ND18-1`）。**不補的後果**：成員詳情頁
   的變更紀錄沒有內容可顯示，`AC12.2.2` 永遠紅燈，而這**不會被任何斷言抓到**
   ——因為斷言是依 `entities.md` 寫的。**不回改 `entities.md`**，以 summary 揭露落差。

2. **CI job 刻意不改名。** 擴充既有 `memory-schema` job（它已有 pgvector service
   與「套用兩次」步驟），但**不改 `id` 也不改 `name:`**——GitHub 的 check name 取自
   job 的 `name:`，改它會改掉 check 名稱，而 branch protection 若引用舊名就會變成
   「缺少必要檢查」。代價是 job 名稱比它實際涵蓋的範圍窄，會以註解在 job 內說明。
   若你希望改名或另開獨立 job，請選 Request Changes。

3. **`[ND1]`=A 之後，兩處已核可文件仍寫「四條外鍵」。** `rules.md` 的 `BR2.3`
   與**契約 `K-15` 的 `foreign_keys`** 都列了第四條（`reselection_events.project_id
   → projects.id`）。DDL 會建三條，兩處落差在 `code-summary.md` 一併揭露。
   第二處是 `nfr-design` 的審查發現 `R-01`（Major）——該站只對 `rules.md` 開了
   修訂指派而漏了 `K-15`，而 `K-15` 是 `U19`／`U20` 讀的跨單元契約。

### 選項

| 選項 | 內容 |
|---|---|
| **Approve Plan** | 八個步驟與三個決定如上，開始實作。 |
| **Request Changes** | 某項要改。例如 CI job 改名與否、九欄是否該先回上游修 `entities.md`、`project_members.user_id` 的索引是否現在就建。 |

## Plan Approval

[Approval Fingerprint]: sha256:v3:4c47afcb681d51559ae476fc1e16cd332547ee2241b547d9d5a421e6dba213bf
[Planned Source]: 3c00129d7fa538e599015b7680f64747bc1f1dd919e326adcbafb3df5ff6fcf8

[Answer]: Approve Plan
