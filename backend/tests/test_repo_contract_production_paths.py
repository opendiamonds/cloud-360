"""Regression tests for the repo contract's forbidden-path check (issue #509).

The code under test is ``scripts/validate_repo_contract.py`` at the REPOSITORY
ROOT -- it is not a backend module. It is tested from ``backend/tests/`` because
that is the only Python test path CI discovers: ``.github/workflows/ci.yml``
runs ``python -m unittest discover -s tests`` with ``working-directory:
backend``. A test placed next to the script (``scripts/tests/``) would satisfy
"a regression test exists" while never running on a PR -- which is precisely
the failure shape this bug had, so it is not an acceptable location here.

The bug: ``validate_no_production_config_added()`` compared against the working
-tree diff (``git diff --cached`` union ``git diff``). CI checks out a clean
tree, so both sets are empty, the loop never runs, and the check passed
unconditionally on every PR. It only ever fired on a dirty local working tree.

Each test therefore builds an isolated git repo in a temp dir and COMMITS the
fixture files, so the worktree is clean -- reproducing the CI condition rather
than a local dirty tree -- then points the module's ``ROOT`` at that temp repo.

Nothing is ever written into the real repository: creating an actual file whose
path contains ``prod``/``production``/``secrets`` would trip the very check
under test and would write that path into shared git history.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from collections.abc import Iterator, Sequence
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_repo_contract.py"


def _load_contract_module():
    """Load the script by file path, without putting ``scripts/`` on sys.path."""
    spec = importlib.util.spec_from_file_location(
        "cloud360_validate_repo_contract_under_test", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module spec from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = _load_contract_module()

# Config passed per-invocation so the fixtures never read or write the
# developer's global git config:
#   user.*            -- commits need an identity; do not assume one is set.
#   commit.gpgsign    -- a globally enabled signing key would break the commit.
#   core.excludesFile -- a personal ignore pattern could silently drop a fixture
#                        file from the commit and make a test pass vacuously.
#   init.defaultBranch-- silences git's default-branch advice on `git init`.
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


def _write_files(repo: Path, files: Sequence[str]) -> None:
    for relative_path in files:
        target = repo / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture\n", encoding="utf-8")


@contextlib.contextmanager
def clean_git_repo(files: Sequence[str]) -> Iterator[Path]:
    """Yield an isolated git repo tracking ``files``, with a CLEAN worktree.

    Committing is the point, not an incidental step: an uncommitted fixture
    would leave the old diff-based implementation something to find, and the
    test would pass against the very bug it exists to catch.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        _git(repo, "init")
        _write_files(repo, files)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "fixture")
        yield repo


@contextlib.contextmanager
def shallow_clone(
    first_commit: Sequence[str], second_commit: Sequence[str]
) -> Iterator[Path]:
    """Yield a ``--depth 1`` clone of a two-commit repo.

    The split matters: ``first_commit`` files are only reachable through a
    commit the clone never fetches. They still exist in the checked-out tree,
    which is exactly the property under test. ``file://`` is required -- git
    silently ignores ``--depth`` for a plain local path clone and would hand
    back a full history, making the test vacuous.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source = root / "source"
        source.mkdir()
        _git(source, "init")
        _write_files(source, first_commit)
        _git(source, "add", "-A")
        _git(source, "commit", "-m", "first")
        _write_files(source, second_commit)
        _git(source, "add", "-A")
        _git(source, "commit", "-m", "second")

        clone = root / "clone"
        _git(root, "clone", "--depth", "1", source.as_uri(), str(clone))
        yield clone


def run_check(repo: Path) -> tuple[int, str]:
    """Run the check against ``repo``, returning (exit code, stderr text)."""
    stderr = io.StringIO()
    with mock.patch.object(contract, "ROOT", repo):
        with contextlib.redirect_stderr(stderr):
            code = contract.validate_no_production_config_added()
    return code, stderr.getvalue()


class TestForbiddenPathScan(unittest.TestCase):
    def assert_worktree_clean(self, repo: Path) -> None:
        status = _git(repo, "status", "--porcelain").strip()
        self.assertEqual(
            status,
            "",
            "fixture worktree must be clean to reproduce the CI condition",
        )

    def test_fixture_worktree_is_clean(self):
        """Guards the fixture itself: a dirty tree would invalidate every
        other test here, because the old diff-based check would then have
        something to find and would pass for the wrong reason."""
        with clean_git_repo(["README.md"]) as repo:
            self.assert_worktree_clean(repo)

    def test_detects_production_directory_on_clean_worktree(self):
        """AC-1: the defect itself. A committed ``production`` path part is
        caught even though nothing is staged or unstaged."""
        with clean_git_repo(["README.md", "deploy/production/config.yml"]) as repo:
            self.assert_worktree_clean(repo)
            code, stderr = run_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("deploy/production/config.yml", stderr)

    def test_detects_prod_directory_on_clean_worktree(self):
        """``prod`` is a separate entry in FORBIDDEN_NEW_PATH_PARTS; covering
        only ``production`` would leave two thirds of the rule unverified."""
        with clean_git_repo(["README.md", "config/prod/app.yml"]) as repo:
            self.assert_worktree_clean(repo)
            code, stderr = run_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("config/prod/app.yml", stderr)

    def test_detects_secrets_directory_on_clean_worktree(self):
        with clean_git_repo(["README.md", "infra/secrets/keys.yml"]) as repo:
            self.assert_worktree_clean(repo)
            code, stderr = run_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("infra/secrets/keys.yml", stderr)

    def test_detects_forbidden_part_as_filename(self):
        """The rule is about path parts, and a bare filename is one."""
        with clean_git_repo(["README.md", "deploy/secrets"]) as repo:
            code, stderr = run_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("deploy/secrets", stderr)

    def test_matching_is_case_insensitive(self):
        with clean_git_repo(["README.md", "deploy/Production/config.yml"]) as repo:
            code, stderr = run_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("deploy/Production/config.yml", stderr)

    def test_reports_every_violation_not_just_the_first(self):
        """FR-4: the message lists all offending paths, so one run tells the
        author everything to fix."""
        with clean_git_repo(
            ["README.md", "deploy/production/a.yml", "infra/secrets/b.yml"]
        ) as repo:
            code, stderr = run_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("deploy/production/a.yml", stderr)
        self.assertIn("infra/secrets/b.yml", stderr)

    def test_substring_matches_are_not_violations(self):
        """AC-2: matching stays part-exact. These are real paths from this
        repository -- ten tracked files contain ``prod``/``secret`` as a
        substring, and a substring check would block all of them."""
        with clean_git_repo(
            [
                "README.md",
                ".claude/agents/aidlc-product-agent.md",
                ".claude/agents/aidlc-product-lead-agent.md",
                ".claude/knowledge/aidlc-product-agent/product-guide.md",
                "docs/secrets-policy.md",
                "docs/production-notes.md",
                "docs/prod-runbook.md",
            ]
        ) as repo:
            self.assert_worktree_clean(repo)
            code, stderr = run_check(repo)
        self.assertEqual(code, 0, f"unexpected violations reported: {stderr}")
        self.assertEqual(stderr, "")

    def test_clean_repo_without_violations_passes(self):
        with clean_git_repo(["README.md", "backend/main.py"]) as repo:
            self.assert_worktree_clean(repo)
            code, stderr = run_check(repo)
        self.assertEqual(code, 0, f"unexpected violations reported: {stderr}")

    def test_untracked_file_is_not_scanned(self):
        """The rule governs what is in version control. An untracked scratch
        file is not part of the repository and must not fail a teammate's run."""
        with clean_git_repo(["README.md"]) as repo:
            scratch = repo / "production" / "scratch.yml"
            scratch.parent.mkdir(parents=True, exist_ok=True)
            scratch.write_text("local only\n", encoding="utf-8")
            code, _ = run_check(repo)
        self.assertEqual(code, 0)


class TestShallowCloneScan(unittest.TestCase):
    """CI checks out with ``fetch-depth: 1``; the scan must not depend on history.

    @purpose 在 CI 的 shallow checkout 下，git ls-files 仍列出全部追蹤檔，
             因此違規路徑照樣被擋——這個前提若不成立，#509 的修正會在 CI
             再次靜默無效。
    @given 一個兩次 commit 的來源 repo，違規路徑只存在於第一次 commit；
           以 git clone --depth 1 取得只有一個 commit 的 clone
    @step 確認 clone 的歷史真的被截斷 | git rev-list --count HEAD 為 `1`
    @step 確認 clone 的工作樹乾淨 | git status --porcelain 為空
    @step 對 clone 執行禁止路徑檢查 | 回傳 1，且 stderr 含
          `deploy/production/config.yml`
    @pass 回傳 1 且訊息點名該路徑；同時 rev-list 為 1（證明歷史確實被截斷，
          不是退化成完整 clone 而空洞通過）
    @story issue #509
    @note 無 @api／@ui：受測對象是 repo 根目錄的 CLI 腳本，既無端點也無 UI
          route。撰寫標準 §4.4 要求兩者至少有一個，這是格式契約對非 HTTP、
          非 UI 測試的已知缺口（見 automation-test-plan.md），捏造一個假端點
          比省略更糟。
    """

    def test_violation_in_unfetched_commit_is_still_detected(self):
        with shallow_clone(
            ["README.md", "deploy/production/config.yml"], ["docs/notes.md"]
        ) as repo:
            depth = _git(repo, "rev-list", "--count", "HEAD").strip()
            self.assertEqual(
                depth,
                "1",
                "fixture must be a truncated clone; a full history would make "
                "this test pass without exercising the shallow case",
            )
            status = _git(repo, "status", "--porcelain").strip()
            self.assertEqual(status, "", "clone worktree must be clean")
            code, stderr = run_check(repo)
        self.assertEqual(code, 1)
        self.assertIn("deploy/production/config.yml", stderr)


if __name__ == "__main__":
    unittest.main()
