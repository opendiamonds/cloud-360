# 技術選型 — `U5 memory-data`

## 一、本單元引入的唯一新技術層：pgvector

| 項 | 決定 | 來源 |
|---|---|---|
| 向量型別 | `vector(1024)`（pgvector 擴充） | 契約 `K-05` 的 `tables[].vector_column` 逐字 |
| 維度 | **1024**，與 `bge-m3` 的 dense 維度一致 | 契約 `K-01` 對 `OLLAMA_EMBED_MODEL` 的 validation 逐字 |
| schema 形式 | 同一 database 內的**獨立 schema**，非獨立 database | 契約 `K-05` 的 `schema_isolation.form` 逐字（保留原生跨 schema join） |
| 資料庫版本 | 既有 compose 的 PG（volume 名為 `db_pg18`，即 PG 18 系） | `deploy/docker-compose.deploy.yml:52` |

**pgvector 是否已可用是一個未查證的前提**：本站**沒有**確認既有 PG image
是否含 `vector` 擴充。這不是細節——`CREATE EXTENSION vector` 需要該擴充
存在於 image 內，而標準 `postgres:*-alpine` **不含**它。
記為 `OPEN-N5-3`，承接站 `infrastructure-design`（CONDITIONAL，
轉移目標 `code-generation`）。本站刻意不猜，也不寫成「已確認」。

## 二、沿用而不新增的部分

| 層 | 採用 | 本單元的增量 |
|---|---|---|
| 資料庫 | PostgreSQL（既有 compose 服務 `db`） | 零——新增 schema 不是新服務 |
| 驅動 | `psycopg`（v3，`postgresql+psycopg://`） | 零 |
| ORM | 本單元**不決定**是否用 ORM——它交付 DDL；讀寫屬 `U8` | 零 |
| 測試框架 | `unittest`（本 repo 未使用 pytest） | **本單元無法沿用**，見 §三 |
| 部署 | 既有 `deploy/` compose ＋ `render-env.sh` | 零新變數（`REDIS_*`／`EMBEDDING_*` 屬 `U1`／`U6`） |

## 三、測試基礎設施：本單元**無法沿用既有路徑**

這是本單元與其他單元最大的差別，且是契約逐字記載的：

> `verification.why_not_existing_tests`：既有測試在 `tests/helpers.py` 以
> `sys.modules.setdefault('psycopg2', MagicMock())` 換掉驅動、改走
> in-memory SQLite，而 **SQLite 沒有 schema 概念**——現有測試基礎設施
> **對本契約沒有任何驗證路徑**。

故驗證載體是 **`N-2`：一個對真實 PostgreSQL 執行的新 CI job**
（`postgres:16-alpine` service container 或等效，且**須含 pgvector**——
見 §一 的 `OPEN-N5-3`）。

**`N-2` 本身是交付物，不是既有能力。** 在它落地之前，
`BR1.1`／`BR1.2`／`BR3.1` 三條**完全無法自動化驗證**（`OPEN-M6`）。

## 四、刻意不引入的東西

- **不新增任何 Python 套件**。本單元交付 DDL 與 grant，無程式碼。
- **不引入 schema 遷移工具**（Alembic 等）。契約 `K-05` 的
  `retry_and_idempotency` 要求以 `IF NOT EXISTS` 形狀承載可重跑性，
  且本單元**無資料遷移**（與 `U4` 的關鍵差別），不需要版本化遷移鏈。
- **不引入 `pgcrypto`**。`[M2]`=A 已把靜態加密定在主機層；
  引入欄位層加密會破壞已核可的 `fulltext` 模式（見 `security-requirements.md` §二）。
