"""`U13 brain-gateway` 的部署必要 secret 檢查靜態鎖（合併前必修第 37 列 (b)；review-03 R-13／L2；`[IG1]`=A）。

以 `yaml.safe_load` 讀 `.github/workflows/deploy.yml`，鎖住 deploy job「Require the secrets that must not default」
步驟對 `OPENROUTER_API_KEY` 的三個落點：`env` 由 **secret**（不是 variable）注入、`run` 內的缺值判斷、缺值時的
說明訊息。形狀比照 `test_brain_ws_deploy_probe.py`。

這是「改錯了不會有任何錯誤、只會沒有檢查」的那一類：刪掉缺值判斷那一行，缺金鑰時部署照樣綠燈，而大腦入口頁
每一輪都回 `INTERNAL_ERROR`；只刪 `env` 那一行，`set -u` 之下該步驟會以未定義變數失敗、錯誤訊息卻不指名缺的
是哪一個 secret。`render-env.sh` 刻意不檢查它（rollback job 仍須能 render），所以這一步是唯一的守門。

本檔只讀檔：不執行 workflow、不觸發 CI、不讀任何 secret 值。受測對象是 workflow 檔、沒有 HTTP 端點，
故規格註解不寫 `@api`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_WF = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
REQUIRE_STEP = "Require the secrets that must not default"
KEY = "OPENROUTER_API_KEY"
CHECK_LINE = '[ -n "${OPENROUTER_API_KEY}" ] || missing="${missing} OPENROUTER_API_KEY"'
MISSING_GUARD = 'if [ -n "${missing}" ]; then'


class DeployRequiredSecretsTest(unittest.TestCase):
    def setUp(self):
        workflow = yaml.safe_load(DEPLOY_WF.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["deploy"]["steps"]
        matches = [s for s in steps if s.get("name") == REQUIRE_STEP]
        self.assertEqual(len(matches), 1, f"deploy job 應恰有一個「{REQUIRE_STEP}」步驟")
        self.step = matches[0]
        self.lines = [ln.strip() for ln in self.step.get("run", "").splitlines()]

    def test_env_injects_openrouter_key_from_a_secret(self):
        """
        @purpose 必要檢查讀得到 OPENROUTER_API_KEY，且來源是 repository secret 而非明文 variable（只刪 env 那一行即紅）。
        @given .github/workflows/deploy.yml 的 deploy job「Require the secrets that must not default」步驟
        @step 讀該步驟的 env | 取 OPENROUTER_API_KEY 的值
        @pass 值逐字為 `${{ secrets.OPENROUTER_API_KEY }}`
        @story US8.1
        """
        env = self.step.get("env") or {}
        self.assertIn(KEY, env)
        self.assertEqual(str(env[KEY]).replace(" ", ""), "${{secrets.OPENROUTER_API_KEY}}")

    def test_run_counts_an_empty_openrouter_key_as_missing_before_the_guard(self):
        """
        @purpose 缺 OPENROUTER_API_KEY 時必須讓部署失敗：缺值判斷存在、只出現一次，且位於 `if [ -n "${missing}" ]` 之前
                 （放在判斷之後等於永不生效；刪掉該行即紅）。
        @given 同一步驟的 run 腳本
        @step 逐行找缺值判斷行 | 找 missing 判斷的 if 行 | 比較兩者行序 | 確認 if 區塊內有 exit 1
        @pass 缺值判斷恰一行、行序在 if 之前、if 之後有 `exit 1`
        @story US8.1
        """
        self.assertEqual(self.lines.count(CHECK_LINE), 1, f"缺少或重複：{CHECK_LINE}")
        self.assertIn(MISSING_GUARD, self.lines)
        guard_at = self.lines.index(MISSING_GUARD)
        self.assertLess(self.lines.index(CHECK_LINE), guard_at)
        self.assertIn("exit 1", self.lines[guard_at:])
        self.assertIn("set -euo pipefail", self.lines)

    def test_missing_branch_explains_what_an_absent_openrouter_key_breaks(self):
        """
        @purpose 缺值時的錯誤輸出要指名 OPENROUTER_API_KEY 與其後果，維運者不必回頭讀程式就知道為何部署被擋。
        @given 同一步驟的 run 腳本
        @step 取 if 區塊內寫到 stderr 的 echo 行 | 找提到 OPENROUTER_API_KEY 的那一行
        @pass 至少一行 `echo "OPENROUTER_API_KEY: ..." >&2` 且說明含 `INTERNAL_ERROR`
        @story US8.1
        """
        guard_at = self.lines.index(MISSING_GUARD)
        block = self.lines[guard_at:]
        explains = [ln for ln in block if ln.startswith(f'echo "{KEY}:') and ln.endswith(">&2")]
        self.assertTrue(explains, "缺值分支沒有指名 OPENROUTER_API_KEY 的說明")
        self.assertIn("INTERNAL_ERROR", " ".join(block))


if __name__ == "__main__":
    unittest.main()
