"""
@purpose IaC scanner：報告形狀、Checkov 結束碼、CLI 缺失與未知嚴重度
@story US3.1 BR1.3
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from hypothesis import given, settings
from hypothesis import strategies as st

from iac.iac_limits import CHECKOV_VERSION
from iac.iac_scan import (
    SEVERITY_RANK,
    default_checkov_runner,
    findings_from_checkov_payload,
    max_severity,
    run_checkov,
)
from iac.iac_types import FileEntry, Finding

_REPO = Path(__file__).resolve().parents[2]


def _completed(returncode: int, payload) -> SimpleNamespace:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(returncode=returncode, stdout=text)


class IacScannerTests(unittest.TestCase):
    def test_zero_findings_are_succeeded_none(self):
        """
        @purpose 零 finding 的成功掃描 max_severity 為 NONE
        @given Checkov exit 0 且 failed_checks 為空
        @step 呼叫 run_checkov
        @pass status 為 succeeded 且 max_severity 為 NONE
        @story US3.1
        """
        outcome = run_checkov(
            [],
            runner=lambda files, timeout: _completed(0, {"results": {"failed_checks": []}}),
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.findings, [])
        self.assertEqual(outcome.max_severity, "NONE")

    def test_known_severity_stays_in_enum(self):
        """
        @purpose 已知嚴重度只落在 INFO/LOW/MEDIUM/HIGH/CRITICAL
        @given 一筆 LOW
        @step 解析 payload 並計算 max
        @pass 嚴重度屬於列舉且 max 為 LOW
        @story US3.1
        """
        findings = findings_from_checkov_payload(
            {"results": {"failed_checks": [{"check_id": "CKV_1", "check_name": "open", "severity": "LOW"}]}}
        )
        self.assertEqual(findings[0].severity, "LOW")
        self.assertIn(findings[0].severity, ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"))
        self.assertEqual(max_severity(findings), "LOW")

    def test_missing_cli_fails(self):
        """
        @purpose CLI 不存在時 D2 失敗，而不是空的成功報告
        @given runner 丟 FileNotFoundError
        @step 呼叫 run_checkov
        @pass status 為 failed
        @story US3.1
        """
        def _missing(files, timeout):
            raise FileNotFoundError("checkov")

        outcome = run_checkov([], runner=_missing)
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(outcome.findings, [])

    def test_cli_timeout_fails(self):
        """
        @purpose CLI 逾時是失敗
        @given runner 丟 TimeoutError
        @step 呼叫 run_checkov
        @pass status 為 failed
        @story US3.1
        """
        def _slow(files, timeout):
            raise TimeoutError("checkov")

        outcome = run_checkov([], runner=_slow)
        self.assertEqual(outcome.status, "failed")

    def test_exit_one_with_json_is_succeeded(self):
        """
        @purpose Checkov exit 1 且 JSON 可解析時，報告成功並帶 finding
        @given returncode 1 與一筆 HIGH
        @step 呼叫 run_checkov
        @pass status 為 succeeded 且 max_severity 為 HIGH
        @story US3.1
        """
        payload = {
            "results": {
                "failed_checks": [
                    {"check_id": "CKV_AWS_1", "check_name": "wide", "severity": "HIGH", "file_path": "main.tf"}
                ]
            }
        }
        outcome = run_checkov([], runner=lambda files, timeout: _completed(1, payload))
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.max_severity, "HIGH")
        self.assertEqual(outcome.findings[0].id, "CKV_AWS_1")

    def test_passed_and_failed_checks_are_both_listed(self):
        """
        @purpose 通過與未通過的檢查都留在報告裡，finding 仍只含未通過
        @given 一筆 failed_checks 與一筆 passed_checks
        @step 呼叫 run_checkov
        @pass checks 先列未通過再列通過，findings 只有未通過那筆
        @story US3.1
        """
        payload = {
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_1",
                        "check_name": "bucket is public",
                        "severity": "HIGH",
                        "file_path": "/main.tf",
                        "resource": "aws_s3_bucket.logs",
                    }
                ],
                "passed_checks": [
                    {
                        "check_id": "CKV_AWS_18",
                        "check_name": "logging enabled",
                        "file_path": "/main.tf",
                        "resource": "aws_s3_bucket.logs",
                    }
                ],
            }
        }
        outcome = run_checkov([], runner=lambda files, timeout: _completed(1, payload))
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual([item.id for item in outcome.findings], ["CKV_AWS_1"])
        self.assertEqual(
            [(item.id, item.status, item.resource) for item in outcome.checks],
            [("CKV_AWS_1", "failed", "aws_s3_bucket.logs"), ("CKV_AWS_18", "passed", "aws_s3_bucket.logs")],
        )

    def test_runner_asks_for_the_full_json_report(self):
        """
        @purpose CLI 必須回傳通過的檢查，不能用 quiet 把它們拿掉
        @given 一份 main.tf
        @step 呼叫 default_checkov_runner，並攔截 subprocess
        @pass 參數含 json、不含 --quiet
        @story US3.1
        """
        from unittest.mock import patch

        with patch("subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="{}")) as run:
            default_checkov_runner([FileEntry("main.tf", 'resource "aws_s3_bucket" "logs" {}')], 5)
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], "checkov")
        self.assertIn("json", argv)
        self.assertNotIn("--quiet", argv)

    def test_unknown_severity_fails(self):
        """
        @purpose 未知嚴重度字串不得被改寫成合法值
        @given severity HUGE
        @step 呼叫 run_checkov
        @pass status 為 failed
        @story US3.1
        """
        payload = {"results": {"failed_checks": [{"check_id": "X", "check_name": "x", "severity": "HUGE"}]}}
        outcome = run_checkov([], runner=lambda files, timeout: _completed(1, payload))
        self.assertEqual(outcome.status, "failed")

    def test_checkov_pin_and_no_ci_job(self):
        """
        @purpose Checkov 釘在 requirements，workflow 不呼叫它
        @given requirements.txt 與 .github/workflows
        @step 讀檔
        @pass 版本字串存在，workflow 檔不含 checkov
        @story US3.1
        """
        requirements = (_REPO / "backend" / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn(f"checkov=={CHECKOV_VERSION}", requirements)
        workflows = _REPO / ".github" / "workflows"
        for path in list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml")):
            self.assertNotIn("checkov", path.read_text(encoding="utf-8").lower())


class IacScannerProperties(unittest.TestCase):
    @given(st.lists(st.sampled_from(["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]), max_size=8))
    @settings(max_examples=30, deadline=None)
    def test_max_severity_is_the_highest_rank(self, severities):
        """
        @purpose max_severity 等於最高階
        @given 零到八個合法嚴重度
        @step 呼叫 max_severity
        @pass 空清單為 NONE，否則等於 rank 最大者
        @story US3.1
        """
        findings = [Finding(id=str(index), severity=value, title="t") for index, value in enumerate(severities)]
        got = max_severity(findings)
        if not severities:
            self.assertEqual(got, "NONE")
        else:
            self.assertEqual(got, max(severities, key=lambda value: SEVERITY_RANK[value]))


if __name__ == "__main__":
    unittest.main()
