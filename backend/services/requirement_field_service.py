"""
requirement_field_service.py — `U20 requirement-field-service` 的資料存取層

**本層不做任何授權判定，也不驗證輸入。** 唯一的呼叫端是
`requirement_field_facade.RequirementFieldFacade`（契約 `K-17` 的 `sole_entry`）；
任何人直接呼叫本模組就繞過了全部授權，而繞過是靜默的（與 `U7`／`U19` 同一個
殘留缺口，無機械強制，靠 code review）。

本層只有四件事，每一件都是**單一 SQL 敘述**（`performance-design.md`）：

| 函式 | 敘述 | 對本表的往返 |
|---|---|---|
| `fetch_rows` | `SELECT … WHERE system_id = ?` | 1（`NFR20.1`） |
| `fetch_row` | `SELECT … WHERE` 三欄唯一鍵 | 1（只在清空為 no-op 時才呼叫） |
| `upsert_value` | `INSERT … ON CONFLICT (三欄) DO UPDATE … RETURNING` | 1（`NFR20.4`） |
| `clear_if_filled` | `UPDATE … WHERE … AND value IS NOT NULL RETURNING` | 1 |

設計重點（皆為審查帶入 code-generation 的處置）：

- **upsert 依連線方言產生**（`NFR20.31`）：`sqlalchemy.dialects.postgresql.insert`
  與 `sqlalchemy.dialects.sqlite.insert` 都提供 `on_conflict_do_update` 與
  `returning`，但由不同的建構式產生。方言取自 `session.get_bind().dialect.name`
  ——不是 `session.bind`，後者在 session 以其他方式建立時可能是 `None`
  （nfr-design `review-01` R-07）。**不得**退回先查後寫，也不得以捕捉
  `IntegrityError` 後重試代替：先查後寫在兩個併發首寫時會撞唯一鍵而回 500。
  衝突目標以**欄位物件**指定（`index_elements`），不寫約束名稱，故約束名稱拼錯
  不會只在 PostgreSQL 上才爆。
- **清空是單一條件式 `UPDATE`**（`NFR20.22`，nfr-requirements `review-01` R-08）：
  先讀後改在兩個併發清空下會兩者都讀到「已填」、都寫入，第二個覆寫
  `cleared_at`／`updated_by`；條件式 `UPDATE` 讓第二個在重新評估 `WHERE` 時得到
  0 列。0 列時呼叫端再以 `fetch_row` 取現況作為回傳。「從未填過」（無列）與第四種
  列（有列而 `value`、`cleared_at` 皆為 null）同樣得到 0 列，自然成為 no-op。
- **時間戳由呼叫端傳入**（nfr-design `review-01` R-04）：不用資料庫的 `now()`。
  SQLite 的 `CURRENT_TIMESTAMP` 只到秒，使「no-op 不更新時間」的測試在同一秒內
  無法變紅；PostgreSQL 的 `now()` 又是交易起始時間。由 Python 端產生、可注入，
  兩種方言行為一致。
- **全部走 SQLAlchemy 建構式與綁定參數**（`NFR20.13`），不組字串 SQL。

回傳值是 SQLAlchemy 的 `Row`（以屬性存取欄位），**不是** ORM 物件：本表的寫入
走 Core 敘述，回傳 ORM 物件會讓 identity map 裡留著寫入前的舊值。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from models import SystemRequirementField

TABLE = SystemRequirementField.__table__

# 回傳給 facade 的欄位。刻意不含 `id`：代理鍵不對外（`entities.md`）。
_RETURNED_COLUMNS = (
    TABLE.c.agent_group,
    TABLE.c.field_key,
    TABLE.c.value,
    TABLE.c.cleared_at,
    TABLE.c.updated_at,
    TABLE.c.updated_by,
    TABLE.c.updated_on_behalf_of,
)

# 三欄唯一鍵 `uq_system_requirement_fields_group_key` 的欄位，即 upsert 的衝突目標。
_CONFLICT_TARGET = (TABLE.c.system_id, TABLE.c.agent_group, TABLE.c.field_key)

_INSERT_BY_DIALECT = {
    "postgresql": postgresql.insert,
    "sqlite": sqlite.insert,
}


class UnsupportedDialect(RuntimeError):
    """連線方言不是 PostgreSQL 或 SQLite。大聲失敗，而不是退回先查後寫。"""


def _key_matches(system_id: int, agent_group: str, field_key: str):
    return and_(
        TABLE.c.system_id == system_id,
        TABLE.c.agent_group == agent_group,
        TABLE.c.field_key == field_key,
    )


def dialect_name(db: Session) -> str:
    """`session.get_bind().dialect.name`。"""
    return db.get_bind().dialect.name


def fetch_rows(db: Session, *, system_id: int) -> List[Row]:
    """該系統的**全部**列，一次查詢（`BR44.4`／`NFR20.1`）。

    **不在 SQL 層以定義清單過濾**：定義外的保留列（`BR44.3`）由 facade 在記憶體中
    忽略。以 `IN (…)` 過濾會讓查詢形狀隨定義變動，且不減少往返次數。
    """
    statement = select(*_RETURNED_COLUMNS).where(TABLE.c.system_id == system_id)
    return list(db.execute(statement).all())


def fetch_row(
    db: Session, *, system_id: int, agent_group: str, field_key: str
) -> Optional[Row]:
    """單一欄位的現況；無列回 `None`。只在清空為 no-op 時使用。"""
    statement = select(*_RETURNED_COLUMNS).where(
        _key_matches(system_id, agent_group, field_key)
    )
    return db.execute(statement).first()


def upsert_value(
    db: Session,
    *,
    system_id: int,
    agent_group: str,
    field_key: str,
    value: str,
    updated_by: int,
    on_behalf_of: Optional[str],
    now: datetime,
) -> Row:
    """以三欄唯一鍵 upsert 一個非空值，回傳寫入後的列（`BR43.5`／`BR43.6`）。

    無列則插入；有列則覆寫 `value`、把 `cleared_at` 設回 null、更新
    `updated_at`／`updated_by`／`updated_on_behalf_of`——包括新值與現值相同時
    （`BR43.6`：「最後一次確認者」本身就是有意義的溯源）。

    **不 commit**：交易邊界歸呼叫端（`BR46.2`）。
    """
    insert = _INSERT_BY_DIALECT.get(dialect_name(db))
    if insert is None:
        raise UnsupportedDialect(
            f"requirement_field_service 只支援 PostgreSQL 與 SQLite，實際為 "
            f"{dialect_name(db)}；upsert 不得退回先查後寫（NFR20.31）"
        )
    statement = insert(TABLE).values(
        system_id=system_id,
        agent_group=agent_group,
        field_key=field_key,
        value=value,
        cleared_at=None,
        updated_at=now,
        updated_by=updated_by,
        updated_on_behalf_of=on_behalf_of,
    )
    statement = statement.on_conflict_do_update(
        index_elements=list(_CONFLICT_TARGET),
        set_={
            "value": statement.excluded.value,
            "cleared_at": None,
            "updated_at": statement.excluded.updated_at,
            "updated_by": statement.excluded.updated_by,
            "updated_on_behalf_of": statement.excluded.updated_on_behalf_of,
        },
    ).returning(*_RETURNED_COLUMNS)
    return db.execute(statement).one()


def clear_if_filled(
    db: Session,
    *,
    system_id: int,
    agent_group: str,
    field_key: str,
    updated_by: int,
    now: datetime,
) -> Optional[Row]:
    """清空一個**已填**欄位；不是已填則什麼都不做並回 `None`（`BR43.3`／`BR43.4`／`BR43.7`）。

    保留列、`value` 設 null、`cleared_at` 與 `updated_at` 設為 `now`、
    `updated_by` 設為發起者、`updated_on_behalf_of` 設 null（`BR45.3`：清空沒有
    代寫參數，發起者以 `updated_by` 表達）。

    **不 commit**：交易邊界歸呼叫端（`BR46.2`）。
    """
    statement = (
        update(TABLE)
        .where(_key_matches(system_id, agent_group, field_key))
        .where(TABLE.c.value.is_not(None))
        .values(
            value=None,
            cleared_at=now,
            updated_at=now,
            updated_by=updated_by,
            updated_on_behalf_of=None,
        )
        .returning(*_RETURNED_COLUMNS)
    )
    return db.execute(statement).first()


__all__ = [
    "TABLE",
    "UnsupportedDialect",
    "clear_if_filled",
    "dialect_name",
    "fetch_row",
    "fetch_rows",
    "upsert_value",
]
