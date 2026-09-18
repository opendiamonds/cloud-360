"""帳號最後活動時間的政策與記錄（C-1、C-2）。

C-1 活動時間政策：兩個時間門檻的判定，純函式、零 I/O、零框架依賴，
因此可被單元測試與 property-based 測試直接驗證（ADR-0006 在本 intent 的落點）。

C-2 活動時間記錄器：請求路徑上的條件式寫入。**自行管理交易邊界**（AD-8）——
`get_db()` 供應器不提交，唯讀端點本身也不提交，不自行提交則寫入被整個丟棄；
失敗時**先復原再記錄**，不復原則後續的權限檢查查詢會拋錯、使用者請求照樣失敗。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import User

logger = logging.getLogger("cloud360.activity")

# 同一帳號的活動時間更新，寫入頻率不得高於每 5 分鐘一次（requirements FR-1.3）。
# 計時基準為「上一次成功寫入的時刻」——滑動視窗，非固定時間桶。
ACTIVITY_WRITE_THROTTLE = timedelta(minutes=5)

# 超過 90 天未活動即為逾期（requirements FR-3.1）。邊界為**嚴格大於**：
# 恰為 90 天者不逾期。
OVERDUE_THRESHOLD = timedelta(days=90)


def as_aware_utc(value: datetime) -> datetime:
    """把可能不帶時區的時間值正規化為 UTC aware。

    **公開函式，兩個消費端**：本模組的兩個判定，以及 `user_router` 的回應序列化。

    測試環境（SQLite）讀回的時間戳不帶時區，PostgreSQL 讀回的帶時區。除了比較時
    會拋 TypeError 之外，**序列化的後果更隱蔽**：不帶時區的值會被序列化成沒有
    位移的字串，而瀏覽器的 `new Date()` 會把它當成**本地時間**解讀 —— 顯示時間
    整體偏移一個時區位移量，AC-1.6 直接失敗，而且畫面上看起來完全正常。
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def should_record_activity(
    last_activity_at: Optional[datetime],
    now: datetime,
    throttle: timedelta = ACTIVITY_WRITE_THROTTLE,
) -> bool:
    """本次活動是否應觸發一次寫入。

    - 從未活動（`None`）→ 一律寫入。
    - 距上次寫入**未滿** throttle → 不寫入。
    - 距上次寫入**滿** throttle（含等於）→ 寫入。

    未來時間（時鐘回撥或資料異常）視為「剛寫過」，不寫入——這比據以重複寫入安全。
    """
    if last_activity_at is None:
        return True
    return as_aware_utc(now) - as_aware_utc(last_activity_at) >= throttle


def is_overdue(
    last_activity_at: Optional[datetime],
    now: datetime,
    threshold: timedelta = OVERDUE_THRESHOLD,
) -> bool:
    """該帳號是否逾期未活動。

    無活動紀錄（`None`）**不套用**逾期標示（requirements FR-2.3）——
    上線前的既有帳號全部落在此態，把它們標成逾期會讓標示失去訊號價值。

    邊界為**嚴格大於**：距今恰為 threshold 者不逾期（stories AC-2.1）。
    """
    if last_activity_at is None:
        return False
    return as_aware_utc(now) - as_aware_utc(last_activity_at) > threshold


def record_activity(db: Session, user: User, now: Optional[datetime] = None) -> bool:
    """依 C-1 的判定，在需要時寫入一次最後活動時間。回傳是否真的寫入。

    交易契約（AD-8）：本函式**自行提交**；失敗時**先 rollback 再記錄 log**。
    呼叫端在請求路徑上，本函式的任何失敗都不得讓使用者的請求失敗。
    """
    moment = now or datetime.now(timezone.utc)
    try:
        # 判定本身也在 try 內：它理論上可因非預期的欄位型別拋出，而本函式在
        # `get_current_user` 的路徑上 —— 任何逃逸的例外會讓**每一個**已認證端點
        # 回 500，直接牴觸 AD-8「任何失敗都不得讓使用者的原始請求失敗」。
        if not should_record_activity(user.last_activity_at, moment):
            return False
        user.last_activity_at = moment
        db.commit()
        return True
    except Exception as exc:  # noqa: BLE001 — 請求路徑上不得因記錄失敗而中斷
        # 先復原：不復原則 session 停在失敗狀態，後續的權限檢查查詢會一併拋錯。
        db.rollback()
        logger.warning(
            "記錄使用者 %s 的最後活動時間失敗，已復原：%s", user.username, exc
        )
        return False
