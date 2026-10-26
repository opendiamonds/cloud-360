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


REVERT_STEP = "Open a revert PR for the bad merge"
RESTORE_STEP = "Restore the last-good deployment"
DOCTOR_STEP = "Hand the failure to the Deploy Doctor agent"


class BrainWsProbeRollbackRoutingTest(unittest.TestCase):
    """合併前必修第 26 項（review-03 R-01）：6a 失敗只回滾、不開 revert PR，其他失敗來源照舊。

    三件事必須同時成立，缺一即裁決失效：6a 的結果要能離開 deploy job（job outputs）；revert 步驟要讀它並在
    6a 失敗時略過；還原 last-good 與 Deploy Doctor **不得**讀它（否則 6a 失敗時站台會停在壞版本）。
    """

    def setUp(self):
        workflow = yaml.safe_load(DEPLOY_WF.read_text(encoding="utf-8"))
        self.jobs = workflow["jobs"]
        deploy_steps = self.jobs["deploy"]["steps"]
        names = [s.get("name") for s in deploy_steps]
        self.assertIn(PROBE_STEP, names)
        self.probe = deploy_steps[names.index(PROBE_STEP)]
        self.rollback_steps = {s.get("name"): s for s in self.jobs["rollback"]["steps"]}
        for name in (REVERT_STEP, RESTORE_STEP, DOCTOR_STEP):
            self.assertIn(name, self.rollback_steps)

    def _probe_output_key(self):
        """回傳 deploy job 中以 6a 的 outcome／conclusion 為值的 output 名稱；找不到回 None。"""
        probe_id = self.probe.get("id")
        if not probe_id:
            return None
        pattern = re.compile(
            r"steps\." + re.escape(probe_id) + r"\.(outcome|conclusion)\s*==\s*'failure'"
        )
        for key, value in (self.jobs["deploy"].get("outputs") or {}).items():
            if pattern.search(str(value)):
                return key
        return None

    def test_probe_result_leaves_the_deploy_job_via_outputs(self):
        """
        @purpose 6a 必須有 id，且 deploy job 的 outputs 以該步驟的 outcome（或 conclusion）== 'failure' 傳出——
                 6a 以 exit 1 結束，步驟自己寫的值不可靠；沒有這個 output，rollback job 無從分辨失敗來源（R3 突變）。
        @given .github/workflows/deploy.yml 的 deploy job
        @step 檢視 6a 的 id | 存在
        @step 檢視 deploy job 的 outputs | 恰有一個 output 的值為 steps.<6a id>.outcome == 'failure'
        @pass 6a 的結果可被下游 job 以 needs.deploy.outputs 讀取
        @story US8.1
        """
        self.assertTrue(self.probe.get("id"), "6a 必須有 id")
        self.assertIsNotNone(self._probe_output_key(), "deploy job outputs 未傳出 6a 的結果")

    def test_revert_pr_step_is_skipped_when_probe_failed(self):
        """
        @purpose rollback 的「Open a revert PR」必須在 6a 失敗時略過（環境性失敗 revert 修不了，且會連同 U13 一起還原），
                 其他失敗來源照舊開——條件仍以 always() 起頭，且排除的是 6a 的 output 為 'true'（R1 突變）。
        @given deploy.yml 的 rollback job 與 deploy job outputs
        @step 檢視 revert 步驟的 if | 含 always()
        @step 檢視 revert 步驟的 if | 含 needs.deploy.outputs.<6a output> != 'true'
        @pass 6a 失敗不開 revert PR；其他失敗照舊
        @story US8.1
        """
        key = self._probe_output_key()
        self.assertIsNotNone(key, "deploy job outputs 未傳出 6a 的結果")
        cond = str(self.rollback_steps[REVERT_STEP].get("if") or "")
        self.assertIn("always()", cond)
        self.assertRegex(
            cond,
            r"needs\.deploy\.outputs\." + re.escape(key) + r"\s*!=\s*'true'",
            "revert 步驟的 if 未排除 6a 失敗",
        )

    def test_restore_and_doctor_still_run_when_probe_failed(self):
        """
        @purpose 雙向：6a 失敗時仍須還原 last-good 並交 Deploy Doctor——還原步驟、Doctor 步驟與 rollback job 本身的
                 if 都不得引用 6a 的 output，否則 6a 失敗時站台停在未通過探測的版本（R2 突變）。
        @given deploy.yml 的 rollback job 與 deploy job outputs
        @step 檢視 rollback job 的 if | 不含 6a 的 output 名稱
        @step 檢視還原步驟與 Doctor 步驟的 if | 不含 6a 的 output 名稱
        @pass 6a 失敗仍回滾、仍交 Deploy Doctor
        @story US8.1
        """
        key = self._probe_output_key()
        self.assertIsNotNone(key, "deploy job outputs 未傳出 6a 的結果")
        self.assertNotIn(key, str(self.jobs["rollback"].get("if") or ""))
        for name in (RESTORE_STEP, DOCTOR_STEP):
            self.assertNotIn(key, str(self.rollback_steps[name].get("if") or ""), name)

    def test_slack_message_does_not_report_skipped_revert_as_conflict(self):
        """
        @purpose 6a 失敗時 revert_pr 為空是刻意的；notify 必須讀 6a 的 output 並另給說明，
                 不得沿用「未建立（衝突或建立失敗）」誤導維運者去手動 revert。
        @given deploy.yml 的 notify job
        @step 檢視組訊息步驟的 env | 有一個值為 needs.deploy.outputs.<6a output>
        @step 檢視其 run | 含「刻意未開」分支
        @pass Slack 訊息區分 6a 略過與衝突
        @story US8.1
        """
        key = self._probe_output_key()
        self.assertIsNotNone(key, "deploy job outputs 未傳出 6a 的結果")
        compose = next(
            s for s in self.jobs["notify"]["steps"] if s.get("name") == "Compose the Slack payload"
        )
        env_values = [str(v) for v in (compose.get("env") or {}).values()]
        self.assertTrue(
            any(f"needs.deploy.outputs.{key}" in v for v in env_values),
            "notify 未讀 6a 的 output",
        )
        self.assertIn("刻意未開", compose["run"])


if __name__ == "__main__":
    unittest.main()
