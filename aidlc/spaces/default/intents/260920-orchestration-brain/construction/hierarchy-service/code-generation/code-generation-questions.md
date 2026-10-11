# Code Generation 問題檔 — `U7 hierarchy-service`

## 計畫摘要（供 Plan Approval 判讀）

**產出已定稿，待核可後才開始產生程式**：

- `code-generation-plan.md` — 要寫的 7 個檔案、facade 的 11 個方法與其規則落點、
  13 項「不動的檔案」清單、二元完成判準
- `unit-test-instructions.md` — 26 項測試（A 授權／B 列可見範圍／C 建立與名稱／
  D 刪除／E 變更紀錄／F NFR 與契約）＋ 12 項突變驗證 ＋ 不寫的測試及其理由

### 三個需要你知道的實作決定

| # | 決定 | 理由 | 代價（如實記載） |
|---|---|---|---|
| 1 | **新增 ORM model，而非在服務層寫 raw SQL** | `tests/helpers.py` 的 in-memory SQLite 是由 **ORM metadata** 建表的——走 raw SQL 的程式**在測試環境裡沒有表可查**，故 ORM 是唯一能被 `TestClient` 測到的路徑。另：`U4` 用 raw SQL 的理由（只寫一個欄位、需要 `WHERE ... IS NULL` 批次語意）不適用於逐列 CRUD | ORM 欄位定義與 `schema_rbac.sql` 的 DDL 成為**兩份物化**。`team.md` 的「單一真實來源」規則要求此時必須有鎖住一致性的測試，故計畫內含 **`T25` schema 對齊測試**（解析該 SQL 檔的三個 `CREATE TABLE` 區塊，與 model 的 `__table__.columns` 比對）。**沒有那支測試，這個決定不合規** |
| 2 | **為既有 `UserDiagram` model 補 `system_id` 映射** | `W5` 的系統條件篩選與 `BR6.3` 的可見性判定都要讀該欄；它**在 DDL 中已存在**（`schema_rbac.sql:373`），缺的只是 ORM 映射 | **純加法**：三條建圖路徑（`collab_router.py:517`、`review_router.py:131`／`:327`）不傳該參數，故行為完全不變，仍留 `NULL`，**`OPEN-H11` 依然成立**。不改那三條路徑——`team.md` 明訂修改既有 router 不得夾帶重構，且那兩支目前沒有 HTTP 層測試保護 |
| 3 | **`Principal` 以模組私有 sentinel 實作 `BR1.4`「不可偽造」** | Python 沒有 package-private，故以建構子要求模組私有 sentinel 的標準做法實現「拿不到 principal 就呼叫不了 facade」 | **擋得住誤用，擋不住刻意的 `module._MINT` 存取**——Python 沒有真正的封裝。`BR1.4` 的 `violation_behaviour` 已如實記載這一點，本計畫**不升級該宣稱** |

### 兩件附帶確認

1. **DDL 零變更**，故 `project.md` 的 `schema_rbac.sql` ＋ `DEPLOY.md`
   **blocking 同步規則不觸發**——新增的 ORM model 全部對應既有欄位，
   無新增／刪除／更名表或欄位、無索引或約束變更、無 seed 語意變更。
2. **`M12`（移除 router 的 409 宣告）是刻意列出的已知缺口**：移除後 CI 全綠、
   契約不進 spec、前端產不出型別，而**沒有任何自動化會發現**
   （`unit-of-work.md:447` 逐字「非 2xx/422 的宣告數為 0」）。
   處置為列入完成判準的人工核對項，**不假裝它被測試覆蓋**。

### 選項

| 選項 | 內容 |
|---|---|
| **Approve Plan** | 計畫與測試指示如上，開始產生程式。 |
| **Request changes** | 其中某項決定要改。告訴我哪一項，我改完重新取得核可（收據綁定計畫內容，故改過之後必須重取）。 |

## Plan Approval

[Approval Fingerprint]: sha256:v3:3e1a0f8da560a3828076f26c9169324d96cfb23d96195489dfe5324b56654155
[Planned Source]: 6ac3307c83cc820906113da5761a25137a986db26f851ae40a3d50198bb471e3

[Answer]: Approve Plan
