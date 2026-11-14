"""`backend/tests_redis/` — 需要**真實 Redis** 的測試根目錄（opt-in）。

為什麼另開一個測試根
====================

`backend/tests/` 的 Redis 測試全部跑在手寫的 in-memory 替身上
（`tests/test_session_store_behaviour.py` 的 `FakeRedis`），而替身以
`session_types` 的 Python 參考實作模擬 Lua 腳本的效果。替身是單執行緒 Python
物件，「原子」在它身上是免費的——**它證明不了 Lua 在真實 Redis 上的行為**
（`U12` nfr-requirements 審查 `R-03`；`U12` nfr-design `scalability-design.md`
第三節）。本目錄放的是**對真實 Redis 執行兩支 Lua 腳本、並與參考實作逐案比對**
的一致性測試。

它**不是 CI 閘門**（如實記載）
==============================

`ci.yml` 的 backend job 沒有 Redis service，`python -m unittest discover -s tests`
也看不到本目錄。`deploy/docker-compose.test.yml` 的 Redis 只供 `ui-regression`
的 Playwright stack 使用。故真實 Redis 上的一致性只由本機 opt-in 執行與 code
review 承擔——**不宣稱已被 CI 鎖住**。

怎麼跑
======

需要一個可連線的 Redis 與已安裝的 `redis` 套件（`requirements.txt` 已列）::

    cd backend
    REDIS_URL=redis://localhost:6379/15 PYTHONDONTWRITEBYTECODE=1 \\
      python3 -B -m unittest tests_redis.test_work_item_lua -v

**`REDIS_URL` 未設定或 `redis` 套件不可匯入時，測試以 skip 結束並印出原因**
（`code-generation-plan.md` §二 第 9 項）。`unittest` 的 skip 與通過在摘要上
只差 `skipped=N`，故 skip 原因一律寫進 skip 訊息，執行者看得到它沒有真的跑。
測試只使用 `REDIS_URL` 指定的那個 DB，並只動自己以隨機前綴建立的 key。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
for _path in (BACKEND_DIR, BACKEND_DIR / "services"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def redis_skip_reason() -> Optional[str]:
    """回傳 skip 原因；可以跑時回 `None`。"""
    if not os.environ.get("REDIS_URL", "").strip():
        return (
            "REDIS_URL 未設定：tests_redis 是 opt-in 的真實 Redis 一致性測試，"
            "不在 CI（見 tests_redis/__init__.py）"
        )
    try:
        import redis  # noqa: F401  延遲匯入：未安裝時 skip 而非 ImportError
    except ImportError:
        return "redis 套件無法匯入：請先安裝 backend/requirements.txt"
    return None
