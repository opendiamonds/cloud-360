"""Unit tests for prompt_guard platform self-modification detection."""

from __future__ import annotations

import unittest

from tests.helpers import backend_dir  # noqa: F401

from services.prompt_guard import (
    REFUSAL_MESSAGE,
    is_platform_self_modification,
    latest_user_text,
)


class TestPromptGuard(unittest.TestCase):
    def test_refusal_message_constant(self):
        self.assertEqual(REFUSAL_MESSAGE, "此需求毫無相關，請重新輸入")

    def test_blocks_cloud360_db_change(self):
        self.assertTrue(
            is_platform_self_modification("請修改 Cloud-360 資料庫的連線字串")
        )

    def test_blocks_our_api_key(self):
        self.assertTrue(
            is_platform_self_modification("把我們的 API key 寫進系統設定")
        )

    def test_blocks_platform_credentials(self):
        self.assertTrue(
            is_platform_self_modification("變更本系統 credentials 與金鑰")
        )

    def test_blocks_rbac_matrix(self):
        self.assertTrue(
            is_platform_self_modification("幫我更新 Cloud360 的權限矩陣變更表")
        )

    def test_allows_customer_aws_rds_diagram(self):
        self.assertFalse(
            is_platform_self_modification(
                "請在 AWS 架構圖加入 RDS 與 ALB，畫出高可用連線"
            )
        )

    def test_allows_gcp_key_in_architecture(self):
        self.assertFalse(
            is_platform_self_modification(
                "在 GCP 架構圖標示服務帳號金鑰的使用位置與 Cloud SQL"
            )
        )

    def test_allows_empty(self):
        self.assertFalse(is_platform_self_modification(""))
        self.assertFalse(is_platform_self_modification("   "))

    def test_latest_user_text_concatenates_recent_user(self):
        text = latest_user_text(
            [
                {"role": "assistant", "content": "ok"},
                {"role": "user", "content": "第一句"},
                {"role": "user", "content": "第二句"},
            ]
        )
        self.assertIn("第一句", text)
        self.assertIn("第二句", text)


if __name__ == "__main__":
    unittest.main()
