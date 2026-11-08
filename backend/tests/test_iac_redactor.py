"""
@purpose IaC redactor：引號賦值改為 Secret Manager 參考，明文不進輸出、log、zip
@story US4.1 US5.2 BR1.6 BR1.7
"""

from __future__ import annotations

import unittest
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from iac.iac_generate import generate_module_tree
from iac.iac_log import log_event
from iac.iac_redact import SECRET_MANAGER_REFERENCE, redact_files
from iac.iac_session import IacWorkspaceSession
from iac.iac_types import FileEntry, Resource
from iac.iac_zip import build_module_zip

_TOKEN = "cloud360-fixture-plaintext-9f3a"
_IAC = Path(__file__).resolve().parents[1] / "iac"


def _ok_runner(files, timeout):
    from types import SimpleNamespace

    return SimpleNamespace(returncode=0, stdout='{"results":{"failed_checks":[]}}')


class IacRedactorTests(unittest.TestCase):
    def test_quoted_assignment_is_replaced(self):
        """
        @purpose 引號內的 password 賦值改成參考運算式
        @given password = "<plaintext>"
        @step 呼叫 redact_files
        @pass 內容含 Secret Manager 參考且不含明文
        @story US4.1
        """
        result = redact_files([FileEntry("main.tf", f'password = "{_TOKEN}"\n')])
        self.assertIn(SECRET_MANAGER_REFERENCE, result.files[0].content)
        self.assertNotIn(_TOKEN, result.files[0].content)
        self.assertEqual(result.rewritten_paths, ["main.tf"])

    def test_plaintext_absent_from_output_log_and_zip(self):
        """
        @purpose 改寫後的內容、log 樣本與 zip 都不含注入明文
        @given 草稿含 password 賦值，且已有成功掃描
        @step session.rewrite，並把草稿壓成 zip
        @pass 明文不在內容、log、zip
        @story US4.1 US5.2
        """
        session = IacWorkspaceSession()
        session.agent_invoke = lambda summary: "note"
        draft = session.generate(1, 1, [Resource("web", "aws", "node")])
        draft.files = [
            FileEntry("main.tf", f'password = "{_TOKEN}"\n'),
            FileEntry("variables.tf", 'variable "name_prefix" { default = "cloud360" }\n'),
            FileEntry("outputs.tf", 'output "module_ready" { value = true }\n'),
        ]
        session.scan(1, 1, runner=_ok_runner)
        with self.assertLogs("cloud360.iac", level="INFO") as captured:
            _result, updated = session.rewrite(1, 1)
        blob = build_module_zip(updated.files)
        joined = "\n".join(captured.output)
        self.assertNotIn(_TOKEN, updated.files[0].content)
        self.assertNotIn(_TOKEN, joined)
        self.assertNotIn(_TOKEN.encode("utf-8"), blob)

    def test_rewritten_paths_lists_only_changed_files(self):
        """
        @purpose rewritten_paths 只列有改到的檔
        @given 一個含密文、一個不含
        @step 呼叫 redact_files
        @pass 清單只有 main.tf，variables.tf 內容不變
        @story US4.1
        """
        untouched = 'variable "name_prefix" { default = "cloud360" }\n'
        result = redact_files(
            [
                FileEntry("main.tf", f'password = "{_TOKEN}"\n'),
                FileEntry("variables.tf", untouched),
            ]
        )
        self.assertEqual(result.rewritten_paths, ["main.tf"])
        self.assertEqual(result.files[1].content, untouched)

    def test_unchanged_file_is_omitted_from_rewritten_paths(self):
        """
        @purpose 完全沒有密文的檔不進 rewritten_paths
        @given 只有註解的 main.tf
        @step 呼叫 redact_files
        @pass rewritten_paths 為空且內容不變
        @story US4.1
        """
        original = "# no secret here\n"
        result = redact_files([FileEntry("main.tf", original)])
        self.assertEqual(result.rewritten_paths, [])
        self.assertEqual(result.files[0].content, original)

    def test_multiple_files_with_assignments(self):
        """
        @purpose 多個檔的賦值都會改
        @given main.tf 與 outputs.tf 各有一個 token
        @step 呼叫 redact_files
        @pass 兩個路徑都在 rewritten_paths，兩份內容都不含明文
        @story US4.1
        """
        result = redact_files(
            [
                FileEntry("main.tf", f'api_key = "{_TOKEN}"\n'),
                FileEntry("outputs.tf", f'token = "{_TOKEN}"\n'),
            ]
        )
        self.assertEqual(result.rewritten_paths, ["main.tf", "outputs.tf"])
        for entry in result.files:
            self.assertNotIn(_TOKEN, entry.content)

    def test_router_and_agent_have_no_apply_or_secret_write(self):
        """
        @purpose router 與 agent 原始碼沒有 apply、destroy、PutSecret、boto3
        @given iac_router.py 與 iac_agent.py
        @step 讀取原始碼
        @pass 四個禁用片段都不存在
        @story BR1.7
        """
        text = (_IAC / "iac_router.py").read_text(encoding="utf-8")
        text += (_IAC / "iac_agent.py").read_text(encoding="utf-8")
        for banned in ("/apply", "/destroy", "PutSecret", "boto3"):
            self.assertNotIn(banned, text)
        generate_module_tree([])

    def test_reference_is_not_a_cloud_call(self):
        """
        @purpose 遮罩結果是參考運算式，不是明文回聲
        @given 固定明文
        @step redact_files
        @pass 參考字串出現，明文字串不出現
        @story BR1.6
        """
        result = redact_files([FileEntry("main.tf", f'secret = "{_TOKEN}"\n')])
        self.assertEqual(
            result.files[0].content,
            f"secret = {SECRET_MANAGER_REFERENCE}\n",
        )


class IacRedactorProperties(unittest.TestCase):
    @given(st.from_regex(r"pw-[a-z0-9]{6,12}", fullmatch=True))
    @settings(max_examples=30, deadline=None)
    def test_random_token_is_absent(self, token):
        """
        @purpose 任意 password 字面值都不留在輸出，且該檔列入改寫路徑
        @given pw- 開頭的 token
        @step redact_files
        @pass 輸出不含 token，rewritten_paths 含 main.tf
        @story US4.1
        """
        result = redact_files([FileEntry("main.tf", f'password = "{token}"\n')])
        self.assertNotIn(token, result.files[0].content)
        self.assertIn("main.tf", result.rewritten_paths)


if __name__ == "__main__":
    unittest.main()
