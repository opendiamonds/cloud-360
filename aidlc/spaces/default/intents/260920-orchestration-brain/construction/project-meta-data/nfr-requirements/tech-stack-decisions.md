# 技術選型 — `U18 project-meta-data`

## 一、技術選型增量為零

| 層 | 採用 | 本單元的增量 |
|---|---|---|
| 資料庫 | PostgreSQL（既有 compose 服務 `db`，image `pgvector/pgvector:pg18`） | **零**——三張表不需要任何擴充（不含向量欄位，與 `U5` 的差別） |
| DDL 載體 | `schema_rbac.sql`（空 volume）＋ **一支新的獨立腳本**（既有環境） | 腳本本身是新檔，但**形狀完全沿用** `U4` 的 `run_hierarchy_migration.py` |
| ORM | **不建 model**，理由同 `U5`（見 §二） | 零 |
| 測試 | 真實 PostgreSQL CI job（沿用 `U5` 建立的 `memory-schema` job 形狀） | 可能新增一個 job 或擴充既有者，`code-generation` 決定 |
| 部署 | 既有 `deploy/` compose | **零新環境變數** |

**不新增任何 Python 套件。** 獨立腳本只用既有的 SQLAlchemy ＋ `psycopg`。

## 二、不建 ORM model（與 `U5` 同，但理由不完全相同）

`U5` 不建 model 的理由是 SQLite 沒有 schema 概念，故那條測試路徑不可用。
**本單元的三張表在 `public` schema**，所以 SQLite 理論上建得起來——
但仍不建，理由有兩個：

1. **本單元是 `spec`，不讀寫資料。** 讀寫屬 `U19`（契約 `K-16`）與
   `U20`（契約 `K-17`）；**它們**在需要時建 model，並承擔
   `U7` 那輪學到的「兩份物化需要鎖住一致性的測試」義務。
2. **避免重演 `U7` 的建表權威問題。** 把三張表放進 `Base.metadata` 會讓
   `create_all()` 在每個既有測試中建立它們；而 `schema_rbac.sql` 與獨立腳本
   都用 `IF NOT EXISTS`，於是**建表的權威會悄悄換成 ORM**——
   `U7` 正是這樣讓 `U4` 的四條 CHECK 在測試環境中消失的。
   本單元的 DDL 有 CHECK（三態模型的約束），同一個洞會重演。

**若 `U19`／`U20` 日後建 model，它們必須把本單元 DDL 的全部約束逐條對齊**
——這是 `U7` 的教訓，寫在此處以免下一個人重新學一次。

## 三、驗證載體

沿用 `U5` 在 `ci.yml` 建立的 `memory-schema` job 形狀：
`pgvector/pgvector:pg18` service container、套用 `schema_rbac.sql` **兩次**
（驗 `BR2.1` 可重跑）、執行純 SQL 斷言。

`code-generation` 可選擇擴充該 job 或新增一個；**本站不預選**，
但要求斷言必須涵蓋三態模型（`BR1.3`／`BR1.4`）與四條外鍵（`BR2.3`）
——那是本單元最容易實作錯的部分。
