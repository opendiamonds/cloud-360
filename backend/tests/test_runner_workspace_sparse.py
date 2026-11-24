"""self-hosted runner 共用工作目錄被 sparse checkout 污染的回歸測試（#750、#756）。

症狀：2026-11-16 起每一次部署都在「Write deploy/.env from secrets」以
`bash: deploy/render-env.sh: 沒有此一檔案或目錄`（exit 127）失敗，rollback job 的
`cp deploy/render-env.sh` 也一樣找不到，但被部署的 commit 明明含有該檔。

根因：同一台 runner 上本 repo 的所有 workflow 共用一個 `$GITHUB_WORKSPACE`。
`brain-health-watch.yml` 每小時以 non-cone sparse checkout 寫下 `core.sparseCheckout=true`；
actions/checkout 在 deploy 的 `git sparse-checkout disable` 把 `false` 寫進 `config.worktree`，
隨即又 unset `extensions.worktreeConfig`，於是 git 忽略那份 `false`，deploy 只展開 sparse 路徑。

既有自動化層為何沒抓到：CI 跑在 GitHub 代管 runner、每次都是全新工作目錄，永遠不會出現
「別的 workflow 留下的 git 設定」；而部署失敗時 Deploy Doctor 的診斷把它推測成兩個 job 搶同一個目錄。

本檔兩組測試：
- 結構鎖：health watch 在 self-hosted job 上的 checkout 必須有獨立 `path:`；deploy 與 rollback 的
  checkout 後緊接修復步驟。
- 行為測試：在暫存 git repo 重現 actions/checkout 的確切指令序列，跑 deploy.yml 裡那段 `run:`，
  斷言檔案回來、工作目錄與 HEAD 一致。

受測對象是 workflow 檔與 git 狀態、沒有 HTTP 端點與 UI，故規格註解不寫 `@api`／`@ui`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_WF = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
HEALTH_WF = REPO_ROOT / ".github" / "workflows" / "brain-health-watch.yml"
REPAIR_STEP = "Restore a full working tree if another workflow left it sparse"
SPARSE_PATH = ".github/actions/brain-health-alert"


def _is_self_hosted(job: dict) -> bool:
    runs_on = job.get("runs-on")
    labels = runs_on if isinstance(runs_on, list) else [runs_on]
    return "self-hosted" in labels


def _repair_script() -> str:
    workflow = yaml.safe_load(DEPLOY_WF.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["deploy"]["steps"]
    return next(s["run"] for s in steps if s.get("name") == REPAIR_STEP)


class WorkflowShapeTest(unittest.TestCase):
    def test_health_watch_never_checks_out_into_the_shared_workspace(self):
        """
        @purpose 防止 self-hosted job 再把 sparse 設定留在共用工作目錄，讓下一次部署少檔案
        @given brain-health-watch.yml 的每個 self-hosted job
        @step 找出其中所有 actions/checkout 步驟
        @pass 每一個都帶非空的 `path:`，且引用 composite action 的 `uses:` 指向該子目錄
        @story #756
        """
        workflow = yaml.safe_load(HEALTH_WF.read_text(encoding="utf-8"))
        checked = 0
        for name, job in workflow["jobs"].items():
            if not _is_self_hosted(job):
                continue
            for step in job["steps"]:
                if step.get("uses", "").startswith("actions/checkout"):
                    path = (step.get("with") or {}).get("path")
                    self.assertTrue(path, f"{name}: self-hosted 上的 checkout 必須有獨立 path")
                    checked += 1
                    local_uses = [s["uses"] for s in job["steps"] if SPARSE_PATH in s.get("uses", "")]
                    for uses in local_uses:
                        self.assertEqual(uses, f"./{path}/{SPARSE_PATH}", name)
        self.assertGreater(checked, 0, "找不到任何 self-hosted checkout，測試前提已失效")

    def test_repair_step_directly_follows_checkout_in_deploy_and_rollback(self):
        """
        @purpose 確保 deploy 與 rollback 兩個 job 在用到 repo 檔案前都先修復工作目錄
        @given deploy.yml 的 deploy 與 rollback job
        @step 讀第 1、2 個步驟
        @pass 第 1 步是 actions/checkout，第 2 步是修復步驟
        @story #750
        """
        workflow = yaml.safe_load(DEPLOY_WF.read_text(encoding="utf-8"))
        for job in ("deploy", "rollback"):
            steps = workflow["jobs"][job]["steps"]
            self.assertTrue(steps[0].get("uses", "").startswith("actions/checkout"), job)
            self.assertEqual(steps[1].get("name"), REPAIR_STEP, job)


@unittest.skipUnless(shutil.which("git"), "需要 git")
class RepairBehaviourTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "ws"
        self.repo.mkdir()
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.invalid")
        self._git("config", "user.name", "t")
        for rel in ("deploy/render-env.sh", f"{SPARSE_PATH}/action.yml", "backend/app.py"):
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(rel + "\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "init")
        self._git("branch", "ut")

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True)

    def _break_like_the_runner(self):
        # brain-health-watch 的 actions/checkout（non-cone sparse）
        self._git("config", "core.sparseCheckout", "true")
        (self.repo / ".git" / "info").mkdir(exist_ok=True)
        (self.repo / ".git" / "info" / "sparse-checkout").write_text(SPARSE_PATH + "\n", encoding="utf-8")
        self._git("checkout", "-q", "--force", "-B", "main", "main")
        # deploy.yml 的 actions/checkout（ref: ut）
        self._git("sparse-checkout", "disable")
        self._git("config", "--local", "--unset-all", "extensions.worktreeConfig")
        self._git("checkout", "-q", "--force", "-B", "ut", "ut")

    def _run_repair(self) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", "-e", "-c", _repair_script()], cwd=self.repo, capture_output=True, text=True)

    def test_broken_workspace_is_restored(self):
        """
        @purpose 重現 #750／#756 的工作目錄狀態，確認部署前的修復步驟能把它救回來
        @given 一個依 actions/checkout 指令序列弄壞的 repo（render-env.sh 不在工作目錄）
        @step 執行 deploy.yml 修復步驟的 run 區塊
        @pass 結束碼 0、deploy/render-env.sh 存在、沒有 skip-worktree 項目、git status 為空
        @story #756
        """
        self._break_like_the_runner()
        self.assertFalse((self.repo / "deploy/render-env.sh").exists(), "前提：重現失敗，render-env.sh 應該不見")
        result = self._run_repair()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.repo / "deploy/render-env.sh").exists())
        self.assertNotIn("\nS ", "\n" + self._git("ls-files", "-t").stdout)
        self.assertEqual(self._git("status", "--short").stdout, "")
        # 下一次部署的 checkout（不經修復步驟）也必須是完整的：只救回這一次、
        # 卻把 core.sparseCheckout=true 留著，下次部署會再壞一次。
        self._git("sparse-checkout", "disable")
        self._git("config", "--local", "--unset-all", "extensions.worktreeConfig")
        self._git("checkout", "-q", "--force", "-B", "main", "main")
        self._git("checkout", "-q", "--force", "-B", "ut", "ut")
        self.assertTrue((self.repo / "deploy/render-env.sh").exists(), "修復後的下一次 checkout 又少了檔案")
        self.assertNotIn("\nS ", "\n" + self._git("ls-files", "-t").stdout)

    def test_clean_workspace_is_left_untouched(self):
        """
        @purpose 確認修復步驟在正常工作目錄上不做任何事、不發警告
        @given 一個完整 checkout 的 repo
        @step 執行修復步驟的 run 區塊
        @pass 結束碼 0、輸出不含 warning、git status 為空
        @story #750
        """
        self._git("checkout", "-q", "ut")
        result = self._run_repair()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("::warning::", result.stdout)
        self.assertEqual(self._git("status", "--short").stdout, "")

    def test_still_missing_file_fails_loudly(self):
        """
        @purpose 若檔案真的不在 commit 裡，修復步驟要以明確錯誤失敗而不是讓下一步 exit 127
        @given 一個刪掉並 commit 了 deploy/render-env.sh 的 repo
        @step 執行修復步驟的 run 區塊
        @pass 結束碼非 0，stderr 含 render-env.sh is missing
        @story #750
        """
        self._git("checkout", "-q", "ut")
        self._git("rm", "-q", "deploy/render-env.sh")
        self._git("commit", "-q", "-m", "drop")
        result = self._run_repair()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("render-env.sh is missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
