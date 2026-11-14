"""`backend/tests_pg/` — 需要**真實 PostgreSQL** 的測試根目錄。

為什麼有兩個測試根，以及為什麼新增的真實 PG 測試**不能**放回 `backend/tests/`
=============================================================================

`backend/tests/` 的 51 個測試檔**全部**走 in-memory SQLite 或 mock
（`tests/helpers.py` 在任何 DB import 之前就把驅動換掉），而 CI 的 `backend`
job **沒有 PostgreSQL service**（其測試步驟只設 `JWT_SECRET`）。把一支需要真實
連線的測試放進那個目錄，它會在 `backend` job 連線失敗。

用 env guard 跳過是可行的，但 **`unittest` 的「跳過」與「通過」在輸出上無法
分辨**（`OK (skipped=1)`）：環境變數哪天從 job 裡掉了，覆蓋面會**靜默消失而
CI 全綠**。本目錄是**結構性**隔離——`python -m unittest discover -s tests`
看不到它，所以不需要任何條件式邏輯，也沒有東西可以忘記設。

而它必須存在的理由只有一個，但那個理由是決定性的
------------------------------------------------

`[N1]`=A 選的機制在既有測試環境中**靜默消失**。實測（`sqlalchemy 2.1.1`）：
`select(Project.id).where(...).with_for_update()` 在 **SQLite dialect** 下編譯出
的 SQL 是 `SELECT projects.id FROM projects WHERE projects.id = ?`
——**鎖子句整段不見，且無錯誤、無警告**。

所以危險不是「測試會失敗」，而是**「測試會通過而鎖根本不存在」**：
在 SQLite 路徑上寫一個併發測試，它會綠燈（SQLAlchemy 把鎖拿掉了，而兩個
「交易」在 in-memory SQLite 的整庫鎖之下本來就不會真的並行），於是產生一個
**假的覆蓋證據**。把它放在那裡比不寫它更糟。

怎麼跑
------

CI：新的 `concurrency` job（`.github/workflows/ci.yml`），自帶
`pgvector/pgvector:pg18` service container ＋ `psql -f schema_rbac.sql`。

本機（需要一個**真實的** PostgreSQL，含 `pgvector`——`schema_rbac.sql` 的第一條
敘述是 `CREATE EXTENSION vector`，標準 `postgres:*-alpine` 跑不過）::

    cd backend
    DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cloud360 \\
      python -m unittest discover -s tests_pg

**`DATABASE_URL` 必須顯式帶 `+psycopg` 後綴**——裸 `postgresql://` 會回頭依賴
SQLAlchemy 的隱含預設，而該預設在 2.1 由 `psycopg2` 改為 `psycopg`。
**讀不到 `DATABASE_URL` 時本目錄的測試必須大聲失敗，不得退回 SQLite 預設**：
退回 SQLite 會讓整個 job 綠燈而鎖從未存在（見 `pg_engine()`）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
for _path in (BACKEND_DIR, BACKEND_DIR / "services"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def require_pg_url() -> str:
    """回傳 `DATABASE_URL`，**缺值或非 PostgreSQL 時大聲失敗**。

    這是本目錄唯一不可接受的失敗方式的防線：若測試在讀不到 `DATABASE_URL` 時
    悄悄退回 `backend/database.py` 的預設或 SQLite，整個 job 會綠燈而鎖從未
    存在——而那正是本目錄存在的理由所要防的事。
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "tests_pg 需要 DATABASE_URL 指向一個真實的 PostgreSQL，"
            "而它未設定。**本處刻意不退回任何預設**：退回 SQLite 會讓整個 job "
            "綠燈而 FOR UPDATE 從未存在（with_for_update() 在 SQLite dialect 下"
            "被靜默丟棄）。正確值形如 "
            "postgresql+psycopg://postgres:postgres@localhost:5432/cloud360"
        )
    if not url.startswith("postgresql"):
        raise RuntimeError(
            f"tests_pg 需要 PostgreSQL，而 DATABASE_URL 的 scheme 不是它。"
            f"（已遮罩的 scheme：{url.split('://', 1)[0]}://…）"
        )
    if not url.startswith("postgresql+"):
        raise RuntimeError(
            "DATABASE_URL 必須顯式帶驅動後綴（postgresql+psycopg://）："
            "裸 postgresql:// 會回頭依賴 SQLAlchemy 的隱含預設，而該預設在 "
            "2.1 由 psycopg2 改為 psycopg。"
        )
    return url
