"""Secret *value* pattern gate for ``scripts/validate_repo_contract.py`` (ADR-0018 §6).

The code under test lives at the repository root. Tests sit in ``backend/tests/``
so CI's ``python -m unittest discover -s tests`` (working-directory: backend)
actually runs them — same placement rule as
``test_repo_contract_production_paths.py``.

Fake credential strings exist only inside TemporaryDirectory fixtures and are
never committed to this repository.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import subprocess
import tempfile
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_repo_contract.py"

# Synthetic shapes that match SECRET_VALUE_REGEXES — not real cloud credentials.
FAKE_AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # 40 chars
FAKE_GCP_KEY = "AIza" + ("x" * 35)  # AIza + 35; fixture-only, never a real key


def _load_contract_module():
    spec = importlib.util.spec_from_file_location(
        "cloud360_validate_repo_contract_secrets_under_test", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module spec from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = _load_contract_module()

GIT_CONFIG: tuple[str, ...] = (
    "-c", "user.email=contract-test@example.invalid",
    "-c", "user.name=Contract Test",
    "-c", "commit.gpgsign=false",
    "-c", f"core.excludesFile={os.devnull}",
    "-c", "init.defaultBranch=main",
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *GIT_CONFIG, *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


@contextlib.contextmanager
def clean_git_repo(files: Mapping[str, str]) -> Iterator[Path]:
    """Yield an isolated git repo with ``files`` committed (clean worktree)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        _git(repo, "init")
        for relative_path, content in files.items():
            target = repo / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "fixture")
        yield repo


def run_secrets_check(repo: Path) -> tuple[int, str]:
    stderr = io.StringIO()
    with mock.patch.object(contract, "ROOT", repo):
        with contextlib.redirect_stderr(stderr):
            code = contract.validate_no_obvious_secrets()
    return code, stderr.getvalue()


class TestSecretValuePatterns(unittest.TestCase):
    def test_empty_aws_secret_assignment_passes(self):
        """Case 1: empty assignment is a name reference, not a leak."""
        with clean_git_repo(
            {"README.md": "ok\n", "deploy/render-env.sh": "AWS_SECRET_ACCESS_KEY=\n"}
        ) as repo:
            code, stderr = run_secrets_check(repo)
        self.assertEqual(code, 0, f"unexpected: {stderr}")

    def test_aws_secret_variable_name_without_value_passes(self):
        """Case 2: identifier / shell expansion without a 40-char value."""
        body = (
            "# optional catalog credentials (ADR-0018)\n"
            "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}\n"
        )
        with clean_git_repo({"README.md": "ok\n", "deploy/render-env.sh": body}) as repo:
            code, stderr = run_secrets_check(repo)
        self.assertEqual(code, 0, f"unexpected: {stderr}")

    def test_aws_secret_forty_char_value_fails(self):
        """Case 3: 40-char [A-Za-z0-9/+=] assignment is treated as a leak."""
        self.assertEqual(len(FAKE_AWS_SECRET), 40)
        body = f"AWS_SECRET_ACCESS_KEY={FAKE_AWS_SECRET}\n"
        with clean_git_repo({"README.md": "ok\n", "notes.env": body}) as repo:
            code, stderr = run_secrets_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("AWS_SECRET_ACCESS_KEY value", stderr)

    def test_gcp_billing_api_key_value_fails(self):
        """Case 4: AIza + 35 legal chars looks like a live GCP API key."""
        self.assertTrue(re.fullmatch(r"AIza[0-9A-Za-z\-_]{35}", FAKE_GCP_KEY))
        body = f"GCP_BILLING_API_KEY={FAKE_GCP_KEY}\n"
        with clean_git_repo({"README.md": "ok\n", "notes.env": body}) as repo:
            code, stderr = run_secrets_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("GCP_BILLING_API_KEY value", stderr)

    def test_begin_private_key_still_fails(self):
        """Case 5: PEM private-key marker remains a hard ban on contract files."""
        # REQUIRED_FILES entry so the literal FORBIDDEN_CONTENT_PATTERNS scan hits.
        body = "-----BEGIN PRIVATE KEY-----\nMIIE...\n"
        with clean_git_repo({"README.md": body}) as repo:
            code, stderr = run_secrets_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("BEGIN PRIVATE KEY", stderr)

    def test_clean_repo_without_secret_strings_passes(self):
        """Case 6: no related identifiers."""
        with clean_git_repo(
            {"README.md": "hello\n", "backend/main.py": "print('ok')\n"}
        ) as repo:
            code, stderr = run_secrets_check(repo)
        self.assertEqual(code, 0, f"unexpected: {stderr}")

    def test_mutation_name_ban_would_reject_variable_reference(self):
        """Case 7: restoring the old bare-name ban makes case 2 fail.

        Proves the new value-pattern gate is what allows name-only references;
        if someone reintroduces the substring ban, this test documents the
        breakage shape.
        """
        body = "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}\n"
        with clean_git_repo({"README.md": "ok\n", "deploy/render-env.sh": body}) as repo:
            code_new, _ = run_secrets_check(repo)
            self.assertEqual(code_new, 0)

            mutated = tuple(
                list(contract.FORBIDDEN_CONTENT_PATTERNS)
                + ["AWS_" + "SECRET_ACCESS_KEY"]
            )
            with mock.patch.object(contract, "FORBIDDEN_CONTENT_PATTERNS", mutated):
                code_old, stderr_old = run_secrets_check(repo)
            self.assertEqual(code_old, 1, "mutated name ban must fail name-only refs")
            self.assertIn("AWS_SECRET_ACCESS_KEY", stderr_old)


if __name__ == "__main__":
    unittest.main()
