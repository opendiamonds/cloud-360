# NFR Requirements — 釐清問題（estimate-intake-api）

> Unit: `estimate-intake-api`（U2）· kind: **service**  
> Stage: nfr-requirements · 適用產物：performance／security／scalability／reliability／observability／tech-stack-decisions／traceability  
> 作答：在每題 `[Answer]:` 後填選項字母（例如 `A`）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 模組 `estimate_intake_*`，掛 `/api/cost/v1`；無 SPA | FD Q1=A |
| POST 成功後同 request enqueue，立即 201 | FD Q2=A |
| diagram_id 純標籤；授權＝擁有者＋分享 | FD Q3=A、BR2.5 |
| 硬刪級聯 | FD Q4=A |
| GET advice 薄代理 | FD Q5=A |
| 本 Unit 更新 C1、移除 C1h～C1b＋allow／deny 測 | FD Q6=A |
| 單檔 ≤5MB、≤3 檔；魔數／副檔名；原始檔不落地 | FR1.3–1.6、BR2.1／2.3 |
| U1 已設列數／32MiB 解析界限；PBT 屬 U1 | U1 NFR |
| NFR1 端到端 3–5 分含建議＝上傳＋U7；NFR2 進度 UI＝U8／U9 | requirements |
| NFR7 TCMS 手寫延後（與他 unit 同策，除非本站另釘） | project／先前 Q6=A 慣例 |
| 三層形狀；禁把邏輯寫進 user_router／wa_rule_engine | NFR6、BR2.11 |

---

## Questions

### Question 1
**NFR3 — 上傳 API 錯誤訊息洩漏邊界？**（security）

A. **對外 `detail` 僅固定短語／錯誤碼**（例如副檔名不符、超過大小、雲別不明需 override）；**不得**含本機路徑、traceback、SQL、內部例外型別名。日誌可記例外型別，不得記檔案全文／金額。**（建議）**

B. 開發環境可回完整例外；staging／prod 才遮罩。

C. 允許回傳 Parser 的 `reason` 原文（可能含標頭片段）。

X) Other

[Answer]: A — 對外 detail 僅固定短語／錯誤碼；日誌禁檔案全文／金額
---

### Question 2
**同步上傳路徑的延遲目標？**（performance；與 NFR1 端到端區隔）

A. **POST／GET detail 目標 p95 ≤ 10s**（含 parse＋寫庫；不含建議）；超過仍回 201／200，但寫 warning 日誌。端到端建議時窗仍由 U7＋NFR1 負責。**（建議）**

B. POST 必須 ≤ 3s，否則 504（可能誤殺大表）。

C. 本 Unit 不定延遲數字，只保證「建議不阻塞 201」。

X) Other

[Answer]: A — POST／GET detail p95 ≤ 10s（不含建議）；超時仍成功並 warning
---

### Question 3
**enqueue 失敗時的可靠性？**（reliability）

A. **交易已 commit 的批次保留**；寫 `advice_enqueue_failed` AuditEvent；Advice 建 `status=failed` 或暫不建列（與 FD 一致擇一：**建 failed**）；HTTP 仍 **201**（上傳本身成功）。客戶可稍後由 U7／手動重試機制補（本 Unit 可不做重試 API）。**（建議）**

B. enqueue 失敗則整筆上傳 rollback 並 503。

C. 靜默忽略 enqueue 失敗，不寫 audit。

X) Other

[Answer]: A — 批次保留；Advice=failed＋audit；仍 201
---

### Question 4
**併發與清單負載？**（scalability）

A. **不引入佇列中介**（Redis 等）；依賴單一 FastAPI process＋DB；list 預設分頁上限（建議 page_size ≤ 50）；同一使用者短時間大量 POST 不做正式 rate limit（交邊緣／後續）。**（建議；brownfield）**

B. 本 Unit 引入 Redis／Celery 專管建議佇列。

C. 對 POST 做每使用者固定 rate limit（例如 10/min）寫死在 app。

X) Other

[Answer]: A — 無 Redis；page_size ≤ 50；不做 app 內 rate limit
---

### Question 5
**可觀測性最低限度？**（observability／NFR5）

A. **AuditEvent 必寫** upload／share_replace／delete／advice_enqueue（成功或失敗）；結構化應用日誌含 `estimate_set_id`、`user_id`、事件名；**禁止** log 金額／raw 列／檔案 bytes。不加新 APM 套件。**（建議）**

B. 另加 OpenTelemetry 必選依賴。

C. 僅靠 AuditEvent，不寫應用日誌。

X) Other

[Answer]: A — Audit＋結構化 log；禁金額／raw；不加 APM
---

### Question 6
**背景任務與 ORM／DDL 技術釘選？**（tech-stack）

A. **FastAPI `BackgroundTasks`（或等價 in-process）** enqueue；表／ORM 走既有 SQLAlchemy＋`database.py` 啟動補丁＋`schema_rbac.sql` 雙軌；**不**引入 Alembic／新訊息佇列。Advice 表可由本 Unit 建空殼（status 欄）供薄讀，正文欄位留給 U7 填。**（建議）**

B. 引入 Celery／RQ＋Redis。

C. 引入 Alembic 專管估價表 schema。

X) Other

[Answer]: A — BackgroundTasks＋SQLAlchemy／雙軌 DDL；Advice 空殼表可建
---

## Consolidated Summary Confirmation

**U2 `estimate-intake-api` NFR 定案**

| 項 | 定案 |
|---|---|
| 安全錯誤面 | detail 固定短語；無路徑／堆疊／SQL（Q1=A） |
| 同步延遲 | POST／GET detail p95 ≤ 10s；不含建議；超時仍成功＋warning（Q2=A） |
| enqueue 失敗 | 批次保留；Advice=`failed`＋audit；仍 201（Q3=A） |
| 擴展 | 無 Redis／Celery；list page_size ≤ 50（Q4=A） |
| 可觀測 | Audit＋結構化 log；禁金額／raw（Q5=A） |
| 技術 | BackgroundTasks＋既有 ORM／雙軌 DDL；Advice 空殼可建（Q6=A） |

**將產出**：performance／security／scalability／reliability／observability／tech-stack-decisions.md、traceability.json。

**後果**：code-gen 須落實錯誤遮罩、BackgroundTasks、Advice 表空殼、分頁上限、seed／授權測；不得引入 Redis／Alembic／APM；NFR1 端到端與進度 UI 仍屬 U7／U8。

[Answer]: Looks correct
