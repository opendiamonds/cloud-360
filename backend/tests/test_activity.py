"""C-1 活動時間政策的邊界與性質測試（PU-1／PU-3）。

兩個判定都是純函式，可直接斷言邊界；`project.md` 的 ADR-0006（property-based
為 hard constraint）在本 intent 的落點就是這裡。
"""

import unittest
from datetime import datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.helpers import close_session, make_session, make_user
from services.activity import (
    ACTIVITY_WRITE_THROTTLE,
    OVERDUE_THRESHOLD,
    is_overdue,
    record_activity,
    should_record_activity,
)

NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


class ShouldRecordActivityTest(unittest.TestCase):
    def test_no_previous_activity_always_writes(self):
        self.assertTrue(should_record_activity(None, NOW))

    def test_just_under_five_minutes_does_not_write(self):
        last = NOW - timedelta(minutes=4, seconds=59)
        self.assertFalse(should_record_activity(last, NOW))

    def test_exactly_five_minutes_writes(self):
        """邊界含等於：距上次寫入滿 5 分鐘（含）之後的下一次活動會寫入。"""
        last = NOW - ACTIVITY_WRITE_THROTTLE
        self.assertTrue(should_record_activity(last, NOW))

    def test_over_five_minutes_writes(self):
        last = NOW - timedelta(minutes=5, seconds=1)
        self.assertTrue(should_record_activity(last, NOW))

    def test_naive_datetime_is_normalised_not_crashed(self):
        """測試環境（SQLite）讀回的時間戳不帶時區，不得因此拋 TypeError。"""
        last = (NOW - timedelta(minutes=10)).replace(tzinfo=None)
        self.assertTrue(should_record_activity(last, NOW))

    def test_future_timestamp_does_not_write(self):
        """時鐘回撥或資料異常時，寧可不寫也不要重複寫。"""
        self.assertFalse(should_record_activity(NOW + timedelta(hours=1), NOW))

    @settings(max_examples=50, deadline=None)
    @given(st.integers(min_value=0, max_value=4 * 60 + 59))
    def test_property_never_writes_within_the_window(self, seconds_ago):
        last = NOW - timedelta(seconds=seconds_ago)
        self.assertFalse(should_record_activity(last, NOW))

    @settings(max_examples=50, deadline=None)
    @given(st.integers(min_value=300, max_value=60 * 60 * 24 * 365))
    def test_property_always_writes_at_or_after_the_window(self, seconds_ago):
        last = NOW - timedelta(seconds=seconds_ago)
        self.assertTrue(should_record_activity(last, NOW))


class IsOverdueTest(unittest.TestCase):
    def test_no_record_is_not_overdue(self):
        """無活動紀錄不套用逾期標示 —— 上線前的既有帳號全部落在此態。"""
        self.assertFalse(is_overdue(None, NOW))

    def test_eighty_nine_days_is_not_overdue(self):
        self.assertFalse(is_overdue(NOW - timedelta(days=89), NOW))

    def test_exactly_ninety_days_is_not_overdue(self):
        """邊界為嚴格大於：恰為 90 天者不逾期。"""
        self.assertFalse(is_overdue(NOW - OVERDUE_THRESHOLD, NOW))

    def test_ninety_days_and_one_second_is_overdue(self):
        self.assertTrue(is_overdue(NOW - OVERDUE_THRESHOLD - timedelta(seconds=1), NOW))

    def test_naive_datetime_is_normalised_not_crashed(self):
        last = (NOW - timedelta(days=100)).replace(tzinfo=None)
        self.assertTrue(is_overdue(last, NOW))

    @settings(max_examples=50, deadline=None)
    @given(st.integers(min_value=0, max_value=90 * 24 * 60 * 60))
    def test_property_never_overdue_within_threshold(self, seconds_ago):
        self.assertFalse(is_overdue(NOW - timedelta(seconds=seconds_ago), NOW))

    @settings(max_examples=50, deadline=None)
    @given(
        st.integers(
            min_value=90 * 24 * 60 * 60 + 1, max_value=10 * 365 * 24 * 60 * 60
        )
    )
    def test_property_always_overdue_beyond_threshold(self, seconds_ago):
        self.assertTrue(is_overdue(NOW - timedelta(seconds=seconds_ago), NOW))


class RecordActivityTest(unittest.TestCase):
    def setUp(self):
        self.db = make_session()

    def tearDown(self):
        close_session(self.db)

    def test_first_activity_is_written_and_committed(self):
        user = make_user(self.db, username="alice", role="Developer")
        self.assertIsNone(user.last_activity_at)

        self.assertTrue(record_activity(self.db, user, NOW))

        # 重新讀出來確認**真的提交了** —— C-2 自行提交是契約，不是實作細節。
        self.db.expire_all()
        reloaded = self.db.query(type(user)).filter_by(username="alice").one()
        self.assertIsNotNone(reloaded.last_activity_at)

    def test_second_activity_within_window_is_skipped(self):
        user = make_user(self.db, username="bob", role="Developer")
        record_activity(self.db, user, NOW)
        self.assertFalse(record_activity(self.db, user, NOW + timedelta(minutes=1)))

    def test_second_activity_after_window_is_written(self):
        user = make_user(self.db, username="carol", role="Developer")
        record_activity(self.db, user, NOW)
        later = NOW + ACTIVITY_WRITE_THROTTLE
        self.assertTrue(record_activity(self.db, user, later))

    def test_only_the_latest_value_is_kept(self):
        """只留最後一次，不留歷史（AC-1.2）。"""
        user = make_user(self.db, username="dave", role="Developer")
        record_activity(self.db, user, NOW)
        later = NOW + timedelta(hours=1)
        record_activity(self.db, user, later)
        self.db.expire_all()
        reloaded = self.db.query(type(user)).filter_by(username="dave").one()
        stored = reloaded.last_activity_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        self.assertEqual(stored, later)


if __name__ == "__main__":
    unittest.main()
