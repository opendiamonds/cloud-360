"""
@purpose IaC session：槽隔離、失敗保留草稿、報告選取、16 MiB、同時產生上限
@story US2.3 BR1.5 BR1.9 BR1.13
"""

from __future__ import annotations

import threading
import time
import unittest
from types import SimpleNamespace

from iac.iac_generate import generate_module_tree
from iac.iac_limits import SLOT_LIMIT_BYTES
from iac.iac_session import IacWorkspaceSession
from iac.iac_types import FileEntry, IacGateError, Resource

_WEB = [Resource("web", "aws", "node")]


def _ok_runner(files, timeout):
    return SimpleNamespace(returncode=0, stdout='{"results":{"failed_checks":[]}}')


def _high_runner(files, timeout):
    payload = (
        '{"results":{"failed_checks":[{"check_id":"CKV_1","check_name":"wide",'
        '"severity":"HIGH","file_path":"main.tf"}]}}'
    )
    return SimpleNamespace(returncode=1, stdout=payload)


class IacSessionTests(unittest.TestCase):
    def setUp(self):
        self.session = IacWorkspaceSession()
        self.session.agent_invoke = lambda summary: "note"

    def test_slots_are_isolated_and_empty_snapshot_is_null(self):
        """
        @purpose (user, diagram) 隔離；沒有產物時快照欄位是 None
        @given 兩個使用者各產生一次，第三人沒有產物
        @step snapshot
        @pass 兩份 draft_id 不同；空快照三個產物欄位都是 None
        @story US2.2
        """
        first = self.session.generate(1, 1, _WEB)
        second = self.session.generate(2, 1, [Resource("fn", "gcp", "node")])
        empty = self.session.snapshot(3, 5)
        self.assertNotEqual(first.draft_id, second.draft_id)
        self.assertEqual(self.session.snapshot(1, 1).draft.draft_id, first.draft_id)
        self.assertEqual(self.session.snapshot(2, 1).draft.draft_id, second.draft_id)
        self.assertEqual(empty.diagram_id, 5)
        self.assertIsNone(empty.draft)
        self.assertIsNone(empty.latest_scan)
        self.assertIsNone(empty.latest_rewrite)

    def test_failure_keeps_previous_draft_and_does_not_retry(self):
        """
        @purpose 產生失敗或逾時保留上一份成功草稿，且只呼叫一次
        @given 已有成功草稿
        @step 注入丟例外的 generator，再注入睡眠超過 timeout 的 generator
        @pass 錯誤碼為 generate_failed 與 generate_timeout；draft_id 不變；呼叫次數各為 1
        @story US2.3 BR1.9
        """
        kept = self.session.generate(1, 1, _WEB)
        calls = {"n": 0}

        def _boom(resources):
            calls["n"] += 1
            raise RuntimeError("generator failed")

        self.session.generator = _boom
        with self.assertRaises(IacGateError) as failed:
            self.session.generate(1, 1, _WEB, timeout_s=2)
        self.assertEqual(failed.exception.code, "generate_failed")
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self.session.snapshot(1, 1).draft.draft_id, kept.draft_id)

        calls["n"] = 0

        def _slow(resources):
            calls["n"] += 1
            time.sleep(0.4)
            return generate_module_tree(resources)

        self.session.generator = _slow
        with self.assertRaises(IacGateError) as timed:
            self.session.generate(1, 1, _WEB, timeout_s=0.05)
        self.assertEqual(timed.exception.code, "generate_timeout")
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self.session.snapshot(1, 1).draft.draft_id, kept.draft_id)

    def test_scan_and_download_without_draft(self):
        """
        @purpose 沒有成功草稿時 scan 與 download 都是 missing_draft
        @given 空 session
        @step scan 與 download
        @pass 兩次錯誤碼都是 missing_draft
        @story US3.1
        """
        with self.assertRaises(IacGateError) as scanned:
            self.session.scan(1, 9, runner=_ok_runner)
        with self.assertRaises(IacGateError) as downloaded:
            self.session.download(1, 9)
        self.assertEqual(scanned.exception.code, "missing_draft")
        self.assertEqual(downloaded.exception.code, "missing_draft")

    def test_rewrite_without_succeeded_report(self):
        """
        @purpose 沒有成功掃描時 rewrite 是 missing_scan_report
        @given 只有草稿，以及一筆失敗掃描
        @step rewrite
        @pass 兩次錯誤碼都是 missing_scan_report
        @story US4.1
        """
        self.session.generate(1, 1, _WEB)
        with self.assertRaises(IacGateError) as missing:
            self.session.rewrite(1, 1)
        self.assertEqual(missing.exception.code, "missing_scan_report")

        def _missing_cli(files, timeout):
            raise FileNotFoundError("checkov")

        with self.assertRaises(IacGateError) as failed:
            self.session.scan(1, 1, runner=_missing_cli)
        self.assertEqual(failed.exception.code, "scan_failed")
        self.assertEqual(failed.exception.reason, "checkov_missing")
        with self.assertRaises(IacGateError) as still:
            self.session.rewrite(1, 1)
        self.assertEqual(still.exception.code, "missing_scan_report")

    def test_omitted_report_id_uses_latest_succeeded(self):
        """
        @purpose 省略 report_id 時用最新一筆成功報告
        @given 兩次成功掃描
        @step rewrite 不帶 report_id
        @pass rewrite.report_id 等於第二筆
        @story BR1.13
        """
        self.session.generate(1, 1, _WEB)
        first = self.session.scan(1, 1, runner=_ok_runner)
        second = self.session.scan(1, 1, runner=_high_runner)
        result, _draft = self.session.rewrite(1, 1)
        self.assertNotEqual(first.report_id, second.report_id)
        self.assertEqual(result.report_id, second.report_id)

    def test_diagram_change_stales_old_report(self):
        """
        @purpose 換 diagram 後舊 report_id 是 stale_report_id，舊圖下載是 missing_draft
        @given diagram 1 已掃描，再對 diagram 2 產生
        @step 用舊 report_id 改寫 diagram 2，再下載 diagram 1
        @pass 錯誤碼依序為 stale_report_id、missing_draft
        @story BR1.5
        """
        self.session.generate(1, 1, _WEB)
        report = self.session.scan(1, 1, runner=_ok_runner)
        self.session.generate(1, 2, _WEB)
        with self.assertRaises(IacGateError) as stale:
            self.session.rewrite(1, 2, report.report_id)
        self.assertEqual(stale.exception.code, "stale_report_id")
        with self.assertRaises(IacGateError) as missing:
            self.session.download(1, 1)
        self.assertEqual(missing.exception.code, "missing_draft")

    def test_slot_over_16_mib_keeps_previous_draft(self):
        """
        @purpose 超過 16 MiB 拒絕寫入，不截斷，舊草稿還在
        @given 一份小草稿，接著 generator 回傳超過上限的 main.tf
        @step 第二次 generate
        @pass 錯誤碼 slot_too_large，draft_id 不變
        @story NFR-SCALE-1.2
        """
        kept = self.session.generate(1, 1, _WEB)

        def _huge(resources):
            return [
                FileEntry("main.tf", "x" * (SLOT_LIMIT_BYTES + 1)),
                FileEntry("variables.tf", "variable \"n\" {}\n"),
                FileEntry("outputs.tf", "output \"o\" { value = true }\n"),
            ]

        self.session.generator = _huge
        with self.assertRaises(IacGateError) as too_big:
            self.session.generate(1, 1, _WEB, timeout_s=5)
        self.assertEqual(too_big.exception.code, "slot_too_large")
        self.assertEqual(self.session.snapshot(1, 1).draft.draft_id, kept.draft_id)

    def test_third_in_flight_generate_is_busy(self):
        """
        @purpose 同一進程第三個進行中的 generate 是 generate_busy
        @given 兩個不同使用者的 generate 停在 generator 裡
        @step 第三個使用者再 generate
        @pass 錯誤碼 generate_busy；前兩個執行緒在放開後結束
        @story NFR-SCALE-1.1
        """
        release = threading.Event()
        entered: list[int] = []
        lock = threading.Lock()

        def _hold(resources):
            with lock:
                entered.append(1)
            if not release.wait(5):
                raise TimeoutError("test stall")
            return generate_module_tree(resources)

        self.session.generator = _hold
        errors: list[str] = []

        def _run(user_id: int) -> None:
            try:
                self.session.generate(
                    user_id,
                    user_id,
                    _WEB,
                    timeout_s=5,
                )
            except IacGateError as exc:
                errors.append(exc.code)

        threads = [threading.Thread(target=_run, args=(user_id,)) for user_id in (1, 2)]
        for thread in threads:
            thread.start()
        deadline = time.time() + 3
        while time.time() < deadline and len(entered) < 2:
            time.sleep(0.01)
        self.assertEqual(len(entered), 2)
        try:
            with self.assertRaises(IacGateError) as busy:
                self.session.generate(3, 3, _WEB, timeout_s=5)
            self.assertEqual(busy.exception.code, "generate_busy")
        finally:
            release.set()
            for thread in threads:
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_fourth_diagram_evicts_the_oldest_slot(self):
        """
        @purpose 同一使用者第四個 diagram 會清掉最久未用的槽
        @given 依序產生 diagram 1、2、3、4
        @step 檢查槽鍵
        @pass 最多三個槽，且不含 diagram 1、含 diagram 4
        @story NFR-SCALE-1.1
        """
        for diagram_id in (1, 2, 3, 4):
            self.session.generate(1, diagram_id, _WEB, timeout_s=5)
        keys = [key for key in self.session._slots if key[0] == 1]
        self.assertLessEqual(len(keys), 3)
        self.assertNotIn((1, 1), self.session._slots)
        self.assertIn((1, 4), self.session._slots)

    def test_same_slot_second_writer_is_busy(self):
        """
        @purpose 同一槽第二個寫入不等候，直接 generate_busy
        @given 使用者 1 的 generate 停在 generator
        @step 同一使用者同一 diagram 再 generate
        @pass 錯誤碼 generate_busy
        @story NFR-SCALE-1.3
        """
        release = threading.Event()
        entered: list[int] = []

        def _hold(resources):
            entered.append(1)
            if not release.wait(5):
                raise TimeoutError("test stall")
            return generate_module_tree(resources)

        self.session.generator = _hold
        thread = threading.Thread(
            target=lambda: self.session.generate(4, 4, _WEB, timeout_s=5)
        )
        thread.start()
        deadline = time.time() + 3
        while time.time() < deadline and not entered:
            time.sleep(0.01)
        self.assertEqual(len(entered), 1)
        try:
            with self.assertRaises(IacGateError) as busy:
                self.session.generate(4, 4, _WEB, timeout_s=5)
            self.assertEqual(busy.exception.code, "generate_busy")
        finally:
            release.set()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
