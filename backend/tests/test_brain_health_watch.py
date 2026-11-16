"""`brain-health-watch.yml` 與 `brain-health-alert` action 的行為測試（observability-setup，[Q4]=C、[Q6]=B）。

判斷邏輯只存在於 workflow 的「Count events and decide」步驟與 action 的 issue 步驟——依 `project.md`
`## Forbidden`，無人值守的自動化不得放在 repo 內的腳本。故本檔以 `yaml.safe_load` 抽出那兩段 shell，
**實際以 bash 執行**：前者餵假日誌，後者以 PATH 上的假 `gh` 記錄它想對 GitHub 做什麼。

這些都是「寫錯了不會有任何錯誤、只會沒有告警」的那一類——2026-11-15 staging 大腦每一句都失敗、
卻沒有任何人被通知，正是本 workflow 要補的那一個洞。

受測對象是 workflow 檔、沒有 HTTP 端點與 UI，故規格註解不寫 `@api`／`@ui`。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCH_WF = REPO_ROOT / ".github" / "workflows" / "brain-health-watch.yml"
ALERT_ACTION = REPO_ROOT / ".github" / "actions" / "brain-health-alert" / "action.yml"
BASH = shutil.which("bash")


def turn(outcome: str, n: int = 1) -> str:
    return "".join(
        f"INFO:cloud360.brain_gateway:turn_end turnId=t{i} preClassifyMs=0 classifyMs=1 "
        f"toFirstContentMs=2 outcome={outcome} prefetch=empty\n"
        for i in range(n)
    )


def routed(error_kind: str = "None", degraded: str = "False", n: int = 1) -> str:
    return "".join(
        f"INFO:cloud360.intent_routing:intent routing turn=t{i} slots=1 scores_available=True "
        f"can_single_out=True elapsed_ms=500 error_kind={error_kind} memory_degraded={degraded} caps=()\n"
        for i in range(n)
    )


def _step(steps, name):
    for s in steps:
        if s.get("name") == name:
            return s
    raise AssertionError(f"找不到步驟：{name}")


class _Shell(unittest.TestCase):
    def setUp(self):
        if BASH is None:
            self.skipTest("沒有 bash")
        self.tmp = Path(tempfile.mkdtemp(prefix="brain-health-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def outputs(self, path: Path) -> dict:
        out = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k] = v
        return out


class DecideStepTest(_Shell):
    def setUp(self):
        super().setUp()
        wf = yaml.safe_load(WATCH_WF.read_text(encoding="utf-8"))
        self.script = _step(wf["jobs"]["scan"]["steps"], "Count events and decide")["run"]

    def decide(self, log_1h: str, log_7d: str = "", state: str = "running/healthy", missing: bool = False) -> dict:
        l1, l7 = self.tmp / "1h.log", self.tmp / "7d.log"
        if not missing:
            l1.write_text(log_1h, encoding="utf-8")
            l7.write_text(log_7d or log_1h, encoding="utf-8")
        out, summary = self.tmp / "out", self.tmp / "summary"
        out.write_text("")
        env = dict(os.environ, LOG_1H=str(l1), LOG_7D=str(l7), CONTAINER_STATE=state,
                   GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(summary))
        proc = subprocess.run([BASH, "-c", self.script], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return self.outputs(out)

    def alerts(self, o: dict) -> set:
        return set(o["alerts"].split())

    def test_healthy_hour_fires_nothing(self):
        """
        @purpose 正常的一小時（20 輪都正常結束、路由無錯）不得觸發任何告警——會誤報的告警會讓讀者學會忽略它。
        @given 1 小時日誌：20 個 turn_end outcome=done、20 次路由 error_kind=None；容器 running/healthy
        @step 執行「Count events and decide」 | alerts 為空字串；turns=20、turn_err=0
        @pass 無告警
        @story US8.1
        """
        o = self.decide(turn("done", 20) + routed(n=20))
        self.assertEqual(o["alerts"], "")
        self.assertEqual((o["turns"], o["turn_err"]), ("20", "0"))

    def test_2026_11_15_incident_fires_turn_errors_and_llm_unavailable(self):
        """
        @purpose 重現 2026-11-15 的實際事故：每一句都以錯誤結束、路由層全是 LlmUnavailable。
                 當時沒有任何告警，是使用者自己發現的；本案斷言同樣的日誌現在會觸發兩條告警。
        @given 1 小時日誌：6 個 turn_end outcome=error:BRAIN_UNAVAILABLE、6 次路由 error_kind=LlmUnavailable
        @step 執行「Count events and decide」 | alerts 含 TURN_ERRORS 與 LLM_UNAVAILABLE
        @pass 事故形狀會被通知
        @story US8.1
        """
        o = self.decide(turn("error:BRAIN_UNAVAILABLE", 6) + routed("LlmUnavailable", n=6))
        self.assertEqual(self.alerts(o), {"TURN_ERRORS", "LLM_UNAVAILABLE"})

    def test_single_error_in_a_quiet_hour_does_not_fire(self):
        """
        @purpose 低流量時單一一次錯誤就是 100%；「至少 2 次」的下限讓它不觸發，但第二次就要觸發。
        @given 1 小時日誌：1 個錯誤結束、0 個正常；另一組 2 個錯誤結束、10 個正常（16.7%）
        @step 執行第一組 | 無 TURN_ERRORS
        @step 執行第二組 | 有 TURN_ERRORS
        @pass 下限與比率同時生效
        @story US8.1
        """
        self.assertNotIn("TURN_ERRORS", self.alerts(self.decide(turn("error:X"))))
        self.assertIn("TURN_ERRORS", self.alerts(self.decide(turn("error:X", 2) + turn("done", 10))))

    def test_error_rate_at_exactly_five_percent_does_not_fire(self):
        """
        @purpose 門檻是「> 5%」：恰好 5%（2／40）不觸發，略高（3／40＝7.5%）觸發——鎖住比較方向。
        @given 1 小時日誌：2 錯 38 正；另一組 3 錯 37 正
        @step 執行兩組 | 前者無 TURN_ERRORS、後者有
        @pass 邊界正確
        @story US8.1
        """
        self.assertNotIn("TURN_ERRORS", self.alerts(self.decide(turn("error:X", 2) + turn("done", 38))))
        self.assertIn("TURN_ERRORS", self.alerts(self.decide(turn("error:X", 3) + turn("done", 37))))

    def test_one_malformed_routing_fires(self):
        """
        @purpose MalformedRouting 代表我們自己的 prompt／schema 壞了，任何一次都要看（intent-router monitoring-design §二）。
        @given 1 小時日誌：10 次正常路由＋1 次 error_kind=MalformedRouting
        @step 執行 | alerts 含 MALFORMED_ROUTING
        @pass 單次即觸發
        @story US8.1
        """
        self.assertIn("MALFORMED_ROUTING", self.alerts(self.decide(routed(n=10) + routed("MalformedRouting"))))

    def test_memory_degraded_and_prompt_guard_thresholds(self):
        """
        @purpose 記憶降級 ≥ 3 輪、prompt_guard 命中 ≥ 5 次各自觸發；低於門檻不觸發。
        @given 兩組日誌：2 輪降級＋4 次命中；3 輪降級＋5 次命中
        @step 執行第一組 | 兩者皆不觸發
        @step 執行第二組 | 觸發 MEMORY_DEGRADED 與 PROMPT_GUARD_SURGE
        @pass 門檻正確
        @story US8.1
        """
        low = self.alerts(self.decide(routed(degraded="True", n=2) + routed("PROMPT_GUARD_HIT", n=4)))
        self.assertFalse(low & {"MEMORY_DEGRADED", "PROMPT_GUARD_SURGE"})
        high = self.alerts(self.decide(routed(degraded="True", n=3) + routed("PROMPT_GUARD_HIT", n=5)))
        self.assertTrue({"MEMORY_DEGRADED", "PROMPT_GUARD_SURGE"} <= high)

    def test_backend_container_state(self):
        """
        @purpose 容器停了或 unhealthy 要觸發 BACKEND_DOWN；沒有 healthcheck 的 running 不觸發。日誌讀不到時不得讓步驟崩潰。
        @given 容器狀態 exited/none、running/unhealthy、running/none；另一次日誌檔不存在
        @step 依序執行 | 前兩者觸發 BACKEND_DOWN、第三者不觸發；日誌不存在時計數皆為 0 且步驟成功
        @pass 狀態判斷正確且對缺檔穩健
        @story US8.1
        """
        self.assertIn("BACKEND_DOWN", self.alerts(self.decide("", state="exited/none")))
        self.assertIn("BACKEND_DOWN", self.alerts(self.decide("", state="running/unhealthy")))
        self.assertNotIn("BACKEND_DOWN", self.alerts(self.decide("", state="running/none")))
        o = self.decide("", state="missing/none", missing=True)
        self.assertEqual((o["turns"], o["routed"], o["turns_7d"]), ("0", "0", "0"))

    def test_seven_day_slo(self):
        """
        @purpose 可用性 SLO（[Q6]=B）：7 天「非錯誤結束」≥ 99%，樣本至少 50 輪才判。恰好 99% 不觸發。
        @given 7 天日誌：100 輪 1 錯（99%）；100 輪 2 錯（98%）；40 輪 10 錯（樣本不足）
        @step 依序執行 | 只有第二組觸發 SLO_7D_BREACH；avail_7d 分別為 99.00% 與 98.00%
        @pass SLO 判定與樣本下限正確
        @story US8.1
        """
        ok = self.decide("", turn("error:X") + turn("done", 99))
        self.assertNotIn("SLO_7D_BREACH", self.alerts(ok))
        self.assertEqual(ok["avail_7d"], "99.00%")
        bad = self.decide("", turn("error:X", 2) + turn("done", 98))
        self.assertIn("SLO_7D_BREACH", self.alerts(bad))
        self.assertEqual(bad["avail_7d"], "98.00%")
        self.assertNotIn("SLO_7D_BREACH", self.alerts(self.decide("", turn("error:X", 10) + turn("done", 30))))


class WorkflowShapeTest(unittest.TestCase):
    def setUp(self):
        self.wf = yaml.safe_load(WATCH_WF.read_text(encoding="utf-8"))
        self.text = WATCH_WF.read_text(encoding="utf-8")

    def test_jobs_run_where_they_must_and_do_not_depend_on_each_other(self):
        """
        @purpose scan 必須在被監看的主機上（日誌只在那裡）；site-probe 必須在 GitHub 代管 runner 上且不依賴 scan——
                 主機離線時 scan 不會產生任何 run，串接會讓外部探測永遠等不到。
        @given brain-health-watch.yml
        @step 檢視 scan.runs-on | 含 self-hosted 與 cloud360
        @step 檢視 site-probe | runs-on 為 ubuntu-latest、沒有 needs
        @pass 兩條監看路徑互相獨立
        @story US8.1
        """
        jobs = self.wf["jobs"]
        self.assertIn("self-hosted", jobs["scan"]["runs-on"])
        self.assertIn("cloud360", jobs["scan"]["runs-on"])
        self.assertEqual(jobs["site-probe"]["runs-on"], "ubuntu-latest")
        self.assertNotIn("needs", jobs["site-probe"])
        self.assertNotIn("needs", jobs["scan"])

    def test_minimal_permissions_and_logs_never_printed(self):
        """
        @purpose 本 repo 為 public、Actions log 公開：權限只有 contents:read＋issues:write；
                 docker logs 一律導到 RUNNER_TEMP 的檔案，workflow 內沒有任何 cat／head／tail 印出日誌。
        @given brain-health-watch.yml 全文
        @step 檢視 permissions | 恰為 {contents: read, issues: write}
        @step 檢視每一行 docker logs | 皆以 > 導向檔案
        @step 搜尋 cat／head／tail 日誌檔 | 零命中
        @pass 不外洩日誌內容
        @story US8.1
        """
        self.assertEqual(self.wf["permissions"], {"contents": "read", "issues": "write"})
        lines = [ln for ln in self.text.splitlines() if "docker logs" in ln and not ln.strip().startswith("#")]
        self.assertTrue(lines)
        for ln in lines:
            self.assertIn("> ", ln, ln)
        for bad in ("cat \"${LOG", "head ", "tail -", "cat ${RUNNER_TEMP}"):
            self.assertNotIn(bad, self.text)


FAKE_GH = r"""#!/usr/bin/env bash
echo "$*" >> "$GH_CALLS"
case "$1 $2" in
  "issue list") cat "$GH_LIST" ;;
  "issue view") cat "$GH_VIEW" ;;
  "issue create") echo "https://github.com/o/r/issues/77" ;;
  *) : ;;
esac
"""


class AlertActionIssueTest(_Shell):
    def setUp(self):
        super().setUp()
        action = yaml.safe_load(ALERT_ACTION.read_text(encoding="utf-8"))
        self.script = _step(action["runs"]["steps"], "Open, update or close the alert issue")["run"]
        bindir = self.tmp / "bin"
        bindir.mkdir()
        gh = bindir / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.path = f"{bindir}:{os.environ['PATH']}"

    def run_issue(self, alerts: str, open_issue: bool, last_sig: str = "") -> tuple:
        title = "[brain-health] 大腦服務告警"
        listing = [{"number": 12, "title": title}] if open_issue else []
        (self.tmp / "list.json").write_text(json.dumps(listing))
        view = {"body": "first\n<!-- brain-health-sig: OLD -->", "comments": []}
        if last_sig:
            view["comments"].append({"body": f"x\n<!-- brain-health-sig: {last_sig} -->\n"})
        (self.tmp / "view.json").write_text(json.dumps(view))
        calls, out = self.tmp / "calls", self.tmp / "out"
        calls.write_text("")
        out.write_text("")
        env = dict(os.environ, PATH=self.path, GH_CALLS=str(calls), GH_LIST=str(self.tmp / "list.json"),
                   GH_VIEW=str(self.tmp / "view.json"), TITLE_PREFIX=title, ALERTS=alerts,
                   DETAILS="計數", RUNBOOK="處置", RUN_URL="https://run", GITHUB_OUTPUT=str(out))
        proc = subprocess.run([BASH, "-c", self.script], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        verbs = [" ".join(c.split()[:2]) for c in calls.read_text().splitlines()]
        return self.outputs(out), verbs

    def test_new_alert_opens_an_issue(self):
        """
        @purpose 沒有開著的告警 issue 時，告警觸發要開一則新的。
        @given 無開啟中 issue；alerts=TURN_ERRORS LLM_UNAVAILABLE
        @step 執行 issue 步驟 | 呼叫 gh issue create；action=opened、issue_number=77
        @pass 告警有人看得到
        @story US8.1
        """
        o, verbs = self.run_issue("TURN_ERRORS LLM_UNAVAILABLE", open_issue=False)
        self.assertIn("issue create", verbs)
        self.assertEqual((o["action"], o["issue_number"]), ("opened", "77"))

    def test_same_alert_set_does_not_comment_again(self):
        """
        @purpose 告警組合沒變時不得每小時留言（也就不發 Slack）——洗版會讓讀者學會忽略告警。順序不同視為同一組。
        @given 開啟中 issue #12，最後一個簽章為 LLM_UNAVAILABLE,TURN_ERRORS；本次 alerts=TURN_ERRORS LLM_UNAVAILABLE
        @step 執行 issue 步驟 | 沒有 issue comment／create／close；action=unchanged
        @pass 去重正確
        @story US8.1
        """
        o, verbs = self.run_issue("TURN_ERRORS LLM_UNAVAILABLE", open_issue=True, last_sig="LLM_UNAVAILABLE,TURN_ERRORS")
        self.assertEqual(o["action"], "unchanged")
        self.assertFalse({"issue comment", "issue create", "issue close"} & set(verbs))

    def test_changed_alert_set_comments_on_the_open_issue(self):
        """
        @purpose 告警組合改變時在既有 issue 留言，不另開第二則。
        @given 開啟中 issue #12，最後簽章 TURN_ERRORS；本次 alerts=TURN_ERRORS MALFORMED_ROUTING
        @step 執行 issue 步驟 | 呼叫 gh issue comment、未呼叫 create；action=commented
        @pass 一事一則 issue
        @story US8.1
        """
        o, verbs = self.run_issue("TURN_ERRORS MALFORMED_ROUTING", open_issue=True, last_sig="TURN_ERRORS")
        self.assertEqual(o["action"], "commented")
        self.assertIn("issue comment", verbs)
        self.assertNotIn("issue create", verbs)

    def test_recovery_comments_and_closes(self):
        """
        @purpose 告警全部解除時留言「已恢復」並關閉 issue；沒有開著的 issue 時什麼都不做。
        @given 開啟中 issue #12、alerts 為空；另一次無開啟中 issue、alerts 為空
        @step 執行第一次 | 依序呼叫 issue comment 與 issue close；action=recovered
        @step 執行第二次 | 沒有任何寫入呼叫；action=none
        @pass 恢復有紀錄、平時不打擾
        @story US8.1
        """
        o, verbs = self.run_issue("", open_issue=True, last_sig="TURN_ERRORS")
        self.assertEqual(o["action"], "recovered")
        self.assertLess(verbs.index("issue comment"), verbs.index("issue close"))
        o, verbs = self.run_issue("", open_issue=False)
        self.assertEqual(o["action"], "none")
        self.assertFalse({"issue comment", "issue create", "issue close"} & set(verbs))


if __name__ == "__main__":
    unittest.main()
