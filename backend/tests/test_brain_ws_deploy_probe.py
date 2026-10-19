"""`U14 entry-page-ui` 的部署步驟 6a 靜態鎖（`[EPI1]`=A；infrastructure-design R-03）。

以 `yaml.safe_load` 讀 `.github/workflows/deploy.yml`，鎖住「大腦 WS 子協定經 tunnel 透傳」探測步驟的
位置、形狀與診斷輸出。形狀比照 `test_mcp_bridge_deploy.py` 的 `DeployWorkflowTest`。

這些都是「改錯了不會有任何錯誤、只會沒有檢查」的那一類：步驟被挪到 last-good 之後，壞版本會成為下次回滾
的目標；加上 `continue-on-error` 等於不擋部署；複製進 rollback job 會讓回滾到早於 `U13` 的版本時失敗；
失敗時不印診斷，維運者分不出是請求方向被剝、回應方向被剝還是 tunnel 斷了。

受測對象是 workflow 檔、沒有 HTTP 端點，故規格註解不寫 `@api`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_WF = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
PROBE_STEP = "Verify the brain WS subprotocol survives the tunnel"


class BrainWsDeployProbeTest(unittest.TestCase):
    def setUp(self):
        workflow = yaml.safe_load(DEPLOY_WF.read_text(encoding="utf-8"))
        self.jobs = workflow["jobs"]
        steps = self.jobs["deploy"]["steps"]
        self.names = [s.get("name") for s in steps]
        self.assertIn(PROBE_STEP, self.names)
        self.step = steps[self.names.index(PROBE_STEP)]

    def test_position_between_redis_restart_check_and_last_good(self):
        """
        @purpose 6a 必須在 Redis 重啟驗證之後、記錄 last-good 之前：失敗時壞版本不成為下次回滾的目標，
                 且不插進 test_mcp_bridge_deploy 釘住的兩步之間（D3 突變）。
        @given .github/workflows/deploy.yml 的 deploy job
        @step 找出 6a 的索引 | 前一步名稱以「Verify sessions survive a Redis restart」開頭
        @step 檢視後一步 | 為「Record this commit as the last-good deployment」
        @pass 位置正確
        @story US8.1
        """
        i = self.names.index(PROBE_STEP)
        self.assertTrue(self.names[i - 1].startswith("Verify sessions survive a Redis restart"))
        self.assertEqual(self.names[i + 1], "Record this commit as the last-good deployment")

    def test_blocking_shape_without_token_or_secret(self):
        """
        @purpose 6a 必須擋部署且不碰任何憑證：無 continue-on-error、run 不含 set -e（101 後 curl 以 28 結束屬正常）、
                 只帶協定名項（不含 bearer. 與 secrets 參照）——本 repo 的 Actions log 公開可讀（D2 突變）。
        @given 6a 的 step 定義
        @step 檢視 continue-on-error | 不存在
        @step 檢視 run | 不含 set -e 形式；含 Sec-WebSocket-Protocol: cloud360.brain.v1；不含 bearer. 與 ${{ secrets.
        @step 檢視 env | 不含 ${{ secrets.
        @pass 擋部署、零憑證
        @story US8.1
        """
        self.assertNotIn("continue-on-error", self.step)
        run = self.step["run"]
        self.assertFalse(re.search(r"set -[a-z]*e", run), "6a 不得 set -e")
        self.assertIn("Sec-WebSocket-Protocol: cloud360.brain.v1", run)
        self.assertNotIn("bearer.", run)
        self.assertNotIn("${{ secrets.", run)
        for value in (self.step.get("env") or {}).values():
            self.assertNotIn("secrets.", str(value))
        self.assertIn("exit 1", run)

    def test_not_copied_into_rollback_job(self):
        """
        @purpose 6a 不得出現在 rollback job：last-good 可能早於 U13、沒有 /api/brain/ws，回滾本身會因此失敗（D4 突變）。
        @given deploy.yml 的 rollback job
        @step 列出 rollback job 的全部步驟名稱與 run 內容 | 皆不含 6a 的名稱與協定名探測
        @pass rollback job 不含 6a
        @story US8.1
        """
        rollback_steps = self.jobs["rollback"]["steps"]
        self.assertNotIn(PROBE_STEP, [s.get("name") for s in rollback_steps])
        for s in rollback_steps:
            self.assertNotIn("Sec-WebSocket-Protocol: cloud360.brain.v1", s.get("run") or "")

    def test_failure_branch_prints_three_diagnostics(self):
        """
        @purpose 失敗時必須印出最後一輪的 HTTP 狀態列、協定標頭有無與 curl 結束碼，使 403／101 無協定標頭／網路失敗
                 三種失敗可區分（infrastructure-design R-03）；且結束碼以 || RC=$? 取得而非被吞掉。
        @given 6a 的 run 內容
        @step 檢視失敗分支（最後一個 exit 1 之前） | 含狀態列、「協定標頭：」與「curl exit=」三行
        @step 檢視 curl 呼叫 | 以 || RC=$? 取得結束碼
        @pass 三項診斷齊全
        @story US8.1
        """
        run = self.step["run"]
        failure = run[run.rindex("done") : run.rindex("exit 1")]
        self.assertIn("status line: ${STATUS_LINE}", failure)
        self.assertIn("協定標頭：${HAS_PROTO}", failure)
        self.assertIn("curl exit=${RC}", failure)
        self.assertIn("|| RC=$?", run)


if __name__ == "__main__":
    unittest.main()
