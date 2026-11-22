"""
system_accounts — 系統保留帳號的單一辨識點（合併前必修第 11 項）

契約：
- `RETENTION_SYSTEM_ACTOR_USERNAME` 是 90 天記憶清除的稽核 actor 的 username，
  與 `schema_rbac.sql` 的 `K)` 區塊 seed、`backend/scripts/purge_expired_memory.sql`
  的子查詢、`backend/scripts/seed_retention_system_actor.py` 的 `SENTINEL_USERNAME`
  **逐字相同**。後三者之間的一致性由 `tests/test_retention_purge_contract.py`
  鎖住；本常數與 seed 腳本常數的一致性由 `tests/test_system_account_protection.py`
  的 A5 鎖住（seed 腳本刻意不 import 應用模組，故以測試而非 import 連結兩者）。
- `is_reserved_system_account(user)` 是應用程式辨識保留帳號的**唯一**判定；
  `user_router.py` 的刪除、改角色、啟停用、授權申請處理與清單查詢都經此判定
  （清單在查詢層以同一常數排除）。

為什麼要擋：`memory.memory_audit_events.actor_user_id` 是
`NOT NULL REFERENCES users (id)`，而清除的稽核 INSERT 與記憶 DELETE 在同一個
交易內。這一列一旦被刪除，自那一刻起**每一次**清除都因外鍵違反而整個中止，
90 天保存期不再前進；被改成 canonical 角色或被啟用則拆掉它四道鎖中的兩道。

本模組不讀 DB、不連外、不 raise `HTTPException`——它只回答「這是不是保留帳號」，
HTTP 形狀由呼叫端決定。
"""

from __future__ import annotations

from typing import Any, Optional

RETENTION_SYSTEM_ACTOR_USERNAME = "SYSTEM.retention-purge"

RESERVED_SYSTEM_USERNAMES = frozenset({RETENTION_SYSTEM_ACTOR_USERNAME})

RESERVED_ACCOUNT_CONFLICT_DETAIL = (
    "此帳號是系統保留帳號（90 天記憶清除的稽核操作者），不得刪除、改角色或啟停用；"
    "刪改它會讓 90 天記憶清除整個停擺"
)


def is_reserved_system_account(user: Optional[Any]) -> bool:
    """`user` 是否為系統保留帳號。以 username **逐字**比對（大小寫敏感）。

    大小寫敏感是刻意的：保留帳號的 username 含大寫字母，正是為了讓登入與註冊
    的 `.lower()` 永遠產生不出它（`schema_rbac.sql` `K)` 區塊的第一道鎖）；
    一般帳號因此不可能與它同名。`None` 回 False。
    """
    if user is None:
        return False
    return getattr(user, "username", None) in RESERVED_SYSTEM_USERNAMES
