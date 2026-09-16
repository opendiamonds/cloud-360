#!/usr/bin/env python3
"""stub 斷言 runner — U-7「每日對帳 workflow 與編排器」的編排層（離線層）。

用法：
    python3 .github/actions/aidlc-sync-reconcile/run-reconcile-tests.py

非零 exit 表失敗。相依：PyYAML、jq、bash。**不打任何真實 API**（gh 與 git 都是
PATH shim，未預期的呼叫一律非零 exit，不會靜默落到真實網路）。

為什麼是**行為**測試
------------------
本單元幾乎全是編排：六份清單的成員身分、一致率的兩類排除、三條回寫路徑**各寫哪
幾欄**、批次上限、單一 intent 失敗不中止整輪。這些東西「改個寫法達成同樣邏輯」的
變體無窮多，文字／結構斷言必然漏。本檔把 `aidlc-sync-reconcile-impl.yml` 裡
`id: reconcile` 那個 step 的 `run:` 腳本抽出來**實際執行**，以 stub 取代四支
composite action，斷言**實際發生的呼叫序列**、**每次回寫的欄位集合**與**報告的
數字**。

U-6 在同一個 stage 被打回兩輪的教訓，本檔逐條照做
--------------------------------------------
1. **每條測試都有「前提斷言」**——先確認該測試要製造的情境**真的發生了**，再斷言
   後果。U-6 的 Major #2 就是少了這一條：計畫鍵名寫成 `"rc"`（stub 只認 `"exit"`）
   被靜默忽略，其餘斷言在空前提上恆真通過，而作者還跑了突變「證明」它有效。
   **本檔的計畫鍵名一律是 `"exit"`。**
2. **跨單元多輪測試**——`test_q1_cross_unit_last_written_status_round_trip` 直接
   載入 U-6 的 runner 並執行 U-6 的真實編排腳本，把 U-7 修復後的狀態餵回去。
   Q1=A 的正確性沒有別的東西守著：單輪測試看不到它。
3. **常數一律從來源推導**——同步標記取自 `record.sh`、反向 PR label 取自 U-6 的
   impl、終局 Status 取自 `map.sh` 的 R-3.3 那一列、三個既有 cron 取自全部
   workflow 檔。本檔一個字面都不抄第二份。

結構斷言（YAML 解析）只用於三件沒有行為層可驗的事：cron 不碰撞（平台在 job 跑起來
之前就消化掉了）、`workflow_call` 的 input 集合、checkout 釘 `trunk_ref`。

規格正本：
    ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
      U-7-reconcile-workflow/functional-design/business-rules.md        （R-1〜R-8 群）
      U-7-reconcile-workflow/functional-design/business-logic-model.md  （序列圖／錯誤表）
      U-7-reconcile-workflow/functional-design/domain-entities.md       （ReconcileReport）
      U-7-reconcile-workflow/nfr-requirements/security-requirements.md  （SEC-1〜SEC-4）
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("找不到 PyYAML。本檔用它解析 workflow；請先 pip install pyyaml\n")
    raise SystemExit(2)

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
IMPL_YML = WORKFLOWS / "aidlc-sync-reconcile-impl.yml"
OUTER_YML = WORKFLOWS / "aidlc-sync-reconcile.yml"
FORWARD_IMPL_YML = WORKFLOWS / "aidlc-sync-forward-impl.yml"
REAL_RECORD_SH = REPO_ROOT / ".github" / "actions" / "aidlc-sync-record" / "record.sh"
REAL_MAP_SH = REPO_ROOT / ".github" / "actions" / "aidlc-sync-map" / "map.sh"
U6_RUNNER = REPO_ROOT / ".github" / "actions" / "aidlc-sync-forward" / "run-orchestration-tests.py"

# GitHub Actions 對未指定 `shell:` 的 `run:` 步驟一律用 `bash -e {0}` 啟動，而受測
# 的 impl workflow **沒有** `shell:`、也沒有 `defaults.run.shell`——所以 `-e` 是從外
# 面帶進來的，腳本內的 `set -uo pipefail` 加不掉它。本 harness 因此必須以同一組旗標
# 啟動受測腳本，否則測試環境與 CI 環境對 `rc=$?` 之後的每一條分支判定相反。
# 以 shlex 切開，讓覆寫值（AIDLC_RECONCILE_BASH）也能帶旗標。
BASH = shlex.split(os.environ.get("AIDLC_RECONCILE_BASH", "bash -e"))
RECORD_ROOT = "aidlc/spaces/default/intents"
TRUNK_REF = "ut"
TRUNK_SHA = "0123456789abcdef0123456789abcdef01234567"
BRANCH_PREFIX = "aidlc-sync/reconcile"

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, actual, expected) -> None:
    global CHECKS
    CHECKS += 1
    if actual != expected:
        FAILURES.append(f"{label}\n    expected: {expected!r}\n    actual:   {actual!r}")


def check_true(label: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append(f"{label}\n    {detail}")


# ==========================================================================
# 常數的推導（一個字面都不在本檔抄第二份）
# ==========================================================================

def sync_marker() -> str:
    m = re.search(r'^SYNC_MARKER="([^"]+)"', REAL_RECORD_SH.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("在 record.sh 找不到 SYNC_MARKER 常數。")
    return m.group(1)


def reverse_pr_label() -> str:
    """D-1 的反向 PR label。U-6 的 impl 是它在程式中的第一個物化點。"""
    m = re.search(r'^ *REVERSE_PR_LABEL="([^"]+)"', FORWARD_IMPL_YML.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("在 U-6 的 impl 找不到 REVERSE_PR_LABEL 常數。")
    return m.group(1)


def done_status() -> str:
    """[US:S-9 AC 5] 的終局 Status。由 map.sh 的 R-3.3 那一列推導。"""
    m = re.search(r'^\s*status="([^"]*)"; reason_code="mapped"; traceable_row="R-3\.3 ',
                  REAL_MAP_SH.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("在 map.sh 推導不出終局 Status（R-3.3 那一列）。")
    return m.group(1)


MARKER = sync_marker()
REVERSE_LABEL = reverse_pr_label()
DONE = done_status()
# map.sh 的 R-3.3 那一列同時給出「終局 Status」與它的 traceable_row 字面，後者是
# 本檔用來驗 SEC-2（報告只放 id 與數字）的探針。
TRACEABLE_PROBE = "R-9.9 secret-probe-row-must-not-reach-the-report"


def impl_doc() -> dict:
    return yaml.safe_load(IMPL_YML.read_text(encoding="utf-8"))


def outer_doc() -> dict:
    return yaml.safe_load(OUTER_YML.read_text(encoding="utf-8"))


def reconcile_script() -> str:
    doc = impl_doc()
    job = (doc.get("jobs") or {}).get("reconcile")
    if not isinstance(job, dict):
        raise SystemExit("aidlc-sync-reconcile-impl.yml 裡找不到 reconcile job。")
    for step in job.get("steps") or []:
        if isinstance(step, dict) and step.get("id") == "reconcile" and isinstance(step.get("run"), str):
            return step["run"]
    raise SystemExit(
        "reconcile job 裡找不到 id: reconcile 的 step。本檔靠這個 id 定位受測腳本；"
        "若 step 被改名，請同步改這裡，不要讓測試靜默地什麼都沒測。"
    )


SCRIPT = reconcile_script()


def load_u6_runner():
    """載入 U-6 的 runner，供跨單元多輪測試直接執行 U-6 的真實編排腳本。"""
    spec = importlib.util.spec_from_file_location("aidlc_u6_runner", U6_RUNNER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"載入不了 U-6 的 runner：{U6_RUNNER}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ==========================================================================
# 四支 composite action 的 stub
# ==========================================================================
# 受測腳本以 `bash <path>/<tool>.sh` 呼叫四支 action 的實作檔（那是 action.yml
# 自述的同一條介面）。stub 因此也是一個 <tool>.sh，內容只轉呼一支 python。
#
# 每一次呼叫都追加一筆 {tool, op, env, gh_token} 到 calls.jsonl。回應由 plan.json
# 決定，key 的解析順序為 `tool:op@限定詞` → `tool:op#序號` → `tool:op` → 內建預設。
# **計畫的 exit code 鍵名一律是 "exit"**（U-6 的 Major #2：寫成 "rc" 會被靜默忽略）。

STUB_PY = r'''#!/usr/bin/env python3
import json, os, pathlib, sys

TOOL = "@TOOL@"
env = dict(os.environ)
op = env.get("AIDLC_OPERATION", "")
calls_path = pathlib.Path(env["STUB_CALLS"])
plan = json.loads(pathlib.Path(env["STUB_PLAN"]).read_text(encoding="utf-8"))

if TOOL in ("map", "record"):
    qual = pathlib.PurePosixPath(env.get("AIDLC_RECORD_PATH", "")).name
elif TOOL == "board":
    qual = env.get("AIDLC_BINDING", "") or env.get("AIDLC_INTENT_ID", "")
else:
    qual = env.get("AIDLC_INTENT_ID", "")

key_base = TOOL if TOOL == "map" else "%s:%s" % (TOOL, op)

prior = 0
if calls_path.exists():
    for line in calls_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        rec_key = rec["tool"] if rec["tool"] == "map" else "%s:%s" % (rec["tool"], rec["op"])
        if rec_key == key_base:
            prior += 1
seq = prior + 1

entry = {
    "tool": TOOL,
    "op": op,
    "qual": qual,
    "seq": seq,
    "env": {k: v for k, v in env.items() if k.startswith("AIDLC_")},
    "gh_token": "GH_TOKEN" in env,
    "github_token": "GITHUB_TOKEN" in env,
}
with calls_path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

DEFAULTS = json.loads(pathlib.Path(env["STUB_DEFAULTS"]).read_text(encoding="utf-8"))
resp = None
for key in ("%s@%s" % (key_base, qual), "%s#%d" % (key_base, seq), key_base):
    if key in plan:
        resp = plan[key]
        break
resp = resp or {}
outputs = dict(DEFAULTS.get(key_base, {}))
for k, v in resp.get("outputs", {}).items():
    outputs[k] = v

out_file = env.get("GITHUB_OUTPUT", "")
if out_file:
    with open(out_file, "a", encoding="utf-8") as fh:
        for name, value in outputs.items():
            if TOOL == "map":
                # U-1 用 name=value 單行形式（map.sh 的 emit()）。
                fh.write("%s=%s\n" % (name, str(value).replace("\n", " ")))
            else:
                fh.write("%s<<__AIDLC_STUB_EOF__\n%s\n__AIDLC_STUB_EOF__\n" % (name, value))

sys.exit(int(resp.get("exit", 0)))
'''

GH_STUB = r'''#!/usr/bin/env python3
"""gh 的 PATH shim：只認 `pr list`，其餘一律 exit 9（不會靜默打到真實網路）。"""
import json, os, pathlib, sys

argv = sys.argv[1:]
calls = pathlib.Path(os.environ["STUB_CALLS"])
with calls.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({"tool": "gh", "op": " ".join(argv[:2]), "qual": "", "seq": 0,
                         "env": {}, "argv": argv, "gh_token": "GH_TOKEN" in os.environ,
                         "github_token": False}, ensure_ascii=False) + "\n")

if argv[:2] != ["pr", "list"]:
    sys.stderr.write("gh shim: 未預期的呼叫 %r\n" % (argv,))
    sys.exit(9)

if os.environ.get("GH_PR_LIST_FAIL") == "1":
    sys.stderr.write("gh shim: 模擬 API 失敗（HTTP 502）\n")
    sys.exit(1)

sys.stdout.write(os.environ.get("GH_PR_LIST_JSON", "[]"))
'''

GIT_STUB = r'''#!/usr/bin/env python3
"""git 的 PATH shim：只認受測腳本用到的 `-C <ws> rev-parse HEAD`（R-7.3）。"""
import os, sys

argv = sys.argv[1:]
if "rev-parse" not in argv:
    sys.stderr.write("git shim: 未預期的呼叫 %r\n" % (argv,))
    sys.exit(9)
if os.environ.get("GIT_REV_PARSE_FAIL") == "1":
    sys.stderr.write("fatal: 模擬讀不到 HEAD\n")
    sys.exit(128)
sys.stdout.write(os.environ["GIT_HEAD_SHA"] + "\n")
'''


# ==========================================================================
# 一輪執行的沙箱
# ==========================================================================

DEFAULT_STATE = {
    "schema_version": 1,
    "binding": 12,
    "last_status": "In progress",
    "last_written_status": "In progress",
    "last_field_value": "code-generation (x)",
    "last_reason_code": "mapped",
    "managed_block_hash": "hash-on-record",
    "last_synced_at": "2026-09-01T00:00:00Z",
    "pending_reverse": None,
}


def state_of(overrides: dict) -> str:
    base = dict(DEFAULT_STATE)
    base.update(overrides)
    return json.dumps(base)


def stub_defaults() -> dict:
    """stub 的內建預設。**基準情境是「已綁定、看板與判定一致、SyncState 相符」**
    ——本單元是對帳，那才是常態；每個測試各自覆寫它要製造的偏離。"""
    return {
        "map": {"status": "In progress", "field_value": "code-generation (x)",
                "reason_code": "mapped",
                "traceable_row": TRACEABLE_PROBE,
                "scope_note": "skipped-in-scope: none; out-of-scope: none"},
        "record:read_sync_state": {"state_json": state_of({}), "binding": "12"},
        "record:write_sync_state": {"result": "written"},
        "record:commit_and_push": {"result": "pushed", "attempts": "1",
                                   "commit_sha": "c0ffee", "reason": "", "message": ""},
        "board:read_item": {"status": "In progress", "field_value": "code-generation (x)",
                            "managed_block_hash": "hash-from-readback",
                            "issue_number": "12", "issue_state": "open"},
        "board:read_issue_state": {"issue_state": "open"},
        "board:write_status": {"result": "written", "actual_status": "",
                               "expected_status": "", "message": ""},
        "notify:notify": {"result": "ok", "issue_number": "77", "action": "created",
                          "count": "1", "message": ""},
        "notify:resolve_if_open": {"result": "ok", "closed": "0",
                                   "closed_numbers": "", "message": ""},
    }


class Round:
    def __init__(self, rc: int, stdout: str, calls: list[dict], report: str):
        self.rc = rc
        self.stdout = stdout
        self.calls = calls
        self.report = report

    def seq(self) -> list[str]:
        out = []
        for c in self.calls:
            if c["tool"] not in ("map", "board", "record", "notify"):
                continue
            out.append(c["tool"] if c["tool"] == "map" else "%s:%s" % (c["tool"], c["op"]))
        return out

    def of(self, tool: str, op: str | None = None, qual: str | None = None) -> list[dict]:
        res = []
        for c in self.calls:
            if c["tool"] != tool:
                continue
            if op is not None and c["op"] != op:
                continue
            if qual is not None and c["qual"] != qual:
                continue
            res.append(c)
        return res

    def mentions(self, needle: str) -> list[dict]:
        return [c for c in self.calls if needle in json.dumps(c, ensure_ascii=False)]

    def metric(self, name: str) -> str | None:
        """從報告的指標表取一格。找不到回 None（讓斷言看得出是缺格而不是值不同）。"""
        for line in self.report.splitlines():
            if line.startswith("|") and name in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2:
                    return cells[-1]
        return None

    def list_cell(self, name: str) -> tuple[str, str] | None:
        """從報告的清單表取（筆數, intent）。"""
        for line in self.report.splitlines():
            if line.startswith("|") and name in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) == 3:
                    return cells[1], cells[2]
        return None


DEFAULT_REGISTRY = [{"dirName": "260899-alpha"}]


def run_round(plan: dict | None = None,
              registry: list[dict] | None = None,
              missing_dirs: tuple[str, ...] = (),
              extra_dirs: tuple[str, ...] = (),
              whitelist: str = "",
              batch_size: str = "50",
              trunk_ref: str = TRUNK_REF,
              head_sha: str = TRUNK_SHA,
              rev_parse_fail: bool = False,
              pr_list_json: str = "[]",
              pr_list_fail: bool = False,
              defaults: dict | None = None,
              bash_argv: list[str] | None = None) -> Round:
    plan = plan or {}
    registry = registry if registry is not None else DEFAULT_REGISTRY
    defaults = defaults if defaults is not None else stub_defaults()
    with tempfile.TemporaryDirectory() as td:
        ws = pathlib.Path(td) / "ws"
        bindir = pathlib.Path(td) / "bin"
        bindir.mkdir(parents=True)

        for tool, action in (("map", "aidlc-sync-map"), ("board", "aidlc-sync-board"),
                             ("record", "aidlc-sync-record"), ("notify", "aidlc-sync-notify")):
            d = ws / ".github" / "actions" / action
            d.mkdir(parents=True)
            sh = d / f"{tool}.sh"
            head = "#!/usr/bin/env bash\n"
            if tool == "record":
                # 受測腳本從這裡 sed 出同步標記。值由真實 record.sh 推導。
                head += f'SYNC_MARKER="{MARKER}"\n'
            if tool == "map":
                # 受測腳本從這裡 sed 出終局 Status。整行的形狀與真實 map.sh 的
                # R-3.3 那一列相同（純變數指派，對 stub 沒有副作用），值由真實
                # map.sh 推導——本檔不抄第二份字面。
                head += f'      status="{DONE}"; reason_code="mapped"; traceable_row="R-3.3 runtime-status-completed"\n'
            sh.write_text(head + 'exec python3 "${BASH_SOURCE[0]}.py" "$@"\n', encoding="utf-8")
            (d / f"{tool}.sh.py").write_text(STUB_PY.replace("@TOOL@", tool), encoding="utf-8")

        # 受測腳本從 U-6 的 impl 推導反向 PR 的 label（D-1 的唯一物化點）。
        wf = ws / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "aidlc-sync-forward-impl.yml").write_text(
            f'          REVERSE_PR_LABEL="{REVERSE_LABEL}"\n', encoding="utf-8")

        root = ws / RECORD_ROOT
        root.mkdir(parents=True)
        (root / "intents.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
        for row in registry:
            if row["dirName"] in missing_dirs:
                continue
            rd = root / row["dirName"]
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "aidlc-state.md").write_text("- **Current Stage**: code-generation\n", encoding="utf-8")
        for extra in extra_dirs:
            rd = root / extra
            rd.mkdir(parents=True, exist_ok=True)
            (rd / "aidlc-state.md").write_text("- **Current Stage**: code-generation\n", encoding="utf-8")

        calls = pathlib.Path(td) / "calls.jsonl"
        calls.touch()
        plan_file = pathlib.Path(td) / "plan.json"
        plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        defaults_file = pathlib.Path(td) / "defaults.json"
        defaults_file.write_text(json.dumps(defaults, ensure_ascii=False), encoding="utf-8")
        summary = pathlib.Path(td) / "step_summary.md"
        summary.touch()

        (bindir / "gh").write_text(GH_STUB, encoding="utf-8")
        (bindir / "git").write_text(GIT_STUB, encoding="utf-8")
        for name in ("gh", "git"):
            (bindir / name).chmod(0o755)

        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)
        env.update({
            "PATH": f"{bindir}:{env.get('PATH', '')}",
            "GITHUB_WORKSPACE": str(ws),
            "GITHUB_REPOSITORY": "opendiamonds/cloud-360",
            "GITHUB_OUTPUT": str(pathlib.Path(td) / "step_output"),
            "GITHUB_STEP_SUMMARY": str(summary),
            "GH_TOKEN": "ghs_stub_token",
            "AIDLC_PROJECT_OWNER": "opendiamonds",
            "AIDLC_PROJECT_NUMBER": "23",
            "AIDLC_FIELD_NAME": "AI-DLC Stage",
            "AIDLC_RECORD_ROOT": RECORD_ROOT,
            "AIDLC_WHITELIST": whitelist,
            "AIDLC_FIELD_MAX_LENGTH": "50",
            "AIDLC_TRUNK_REF": trunk_ref,
            "AIDLC_BATCH_SIZE": batch_size,
            "AIDLC_BRANCH_PREFIX": BRANCH_PREFIX,
            "STUB_CALLS": str(calls),
            "STUB_PLAN": str(plan_file),
            "STUB_DEFAULTS": str(defaults_file),
            "GH_PR_LIST_JSON": pr_list_json,
            "GH_PR_LIST_FAIL": "1" if pr_list_fail else "0",
            "GIT_HEAD_SHA": head_sha,
            "GIT_REV_PARSE_FAIL": "1" if rev_parse_fail else "0",
        })
        # bash_argv 讓個別測試**自己釘住**啟動旗標，不受模組層 BASH 預設值影響——
        # F5 的迴歸測試靠它在「有人把預設值改回不帶 -e 的 bash」時仍然生效。
        proc = subprocess.run([*(bash_argv or BASH), "-c", SCRIPT], cwd=str(ws), env=env,
                              capture_output=True, text=True)
        recs = [json.loads(l) for l in calls.read_text(encoding="utf-8").splitlines() if l.strip()]
        return Round(proc.returncode, proc.stdout + proc.stderr, recs,
                     summary.read_text(encoding="utf-8"))


def patch_of(round_: Round, seq: int = 1) -> dict:
    calls = round_.of("record", "write_sync_state")
    if len(calls) < seq:
        return {}
    return json.loads(calls[seq - 1]["env"]["AIDLC_STATE_JSON"])


def map_out(status: str = "", field_value: str = "", reason_code: str = "mapped",
            row: str = TRACEABLE_PROBE) -> dict:
    return {"outputs": {"status": status, "field_value": field_value,
                        "reason_code": reason_code, "traceable_row": row,
                        "scope_note": ""}}


BOARD_WRITE_OPS = ("write_status",)


# ==========================================================================
# R-6 群：三條回寫路徑的欄位集合（差異就是「哪幾欄」）
# ==========================================================================

def test_r6_4_push_rejected_is_red_and_notified() -> None:
    """@purpose R-6.4 ＋ R-4.1：`commit_and_push` 回 Rejected（exit 3）時必須**紅燈 ＋ 通報 Rejected**，且不中止整輪。
    @given 補平成功、隨後的 commit_and_push 以 exit 3 回 rejected
    @step 跑一輪 | **前提**：commit_and_push 確實被呼叫且確實失敗（否則下面都是空的）
    @step 檢視整輪 rc 與通報 | rc≠0；通報的 reason_code 為 Rejected
    @pass **這條分支先前零覆蓋**——reviewer iteration 1 把整段失敗處理改成 `return 0`
          （無條件視為成功、不通報、不紅燈），35 條測試全綠、零命中。推送被靜默吞掉
          意謂看板已改而 record 沒跟上，且沒有任何人會知道。
    @story S-8
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "code-generation (x)", "mapped"),
        "record:commit_and_push": {"exit": 3, "outputs": {
            "result": "rejected", "reason": "non_fast_forward", "message": "! [rejected]"}},
    }
    r = run_round(plan=plan)
    cp = r.of("record", "commit_and_push")
    check_true("R-6.4 **前提**：commit_and_push 被呼叫", len(cp) >= 1,
               f"實得 {len(cp)} 次——沒走到推送，下面的斷言全部是空的。stdout：{r.stdout}")
    check_true("R-6.4 **前提**：本輪確實有推送失敗（stdout 出現被拒）",
               "被拒" in r.stdout or "rejected" in r.stdout, r.stdout)
    check_true("R-6.4：推送被拒必須**紅燈**", r.rc != 0,
               f"整輪 rc={r.rc}——推送失敗被靜默吞掉了")
    ns = [n for n in r.of("notify", "notify")
          if n["env"].get("AIDLC_REASON_CODE") == "Rejected"]
    check_true("R-6.4：必須通報 reason_code=Rejected", len(ns) == 1,
               f"實得 {len(ns)} 則 Rejected 通報（全部通報："
               f"{[n['env'].get('AIDLC_REASON_CODE') for n in r.of('notify','notify')]}）")


def test_r6_1_writeback_failure_is_red_and_notified() -> None:
    """@purpose R-6.1 的「看板已補平但回寫 sync-state.json 失敗」分支必須**紅燈 ＋ 通報 ExternalError**。
    @given write_status 成功補平、隨後的 write_sync_state 以 exit 1 失敗
    @step 跑一輪 | **前提**：補平確實成功、write_sync_state 確實被呼叫且失敗
    @step 檢視整輪 rc 與通報 | rc≠0；通報 ExternalError
    @step 檢視推送 | **不推送**（沒有東西寫成功，推了會是一個空 commit）
    @pass **這條分支先前零覆蓋**——reviewer iteration 1 整段拿掉、強制視為成功，
          35 條測試全綠、零命中。這正是 R-6.5 下一輪要修的那個狀態（看板已改而
          SyncState 沒跟上），失敗必須大聲，否則沒有人知道要等它被修。
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "code-generation (x)", "mapped"),
        "record:write_sync_state": {"exit": 1, "outputs": {"result": "failed"}},
    }
    r = run_round(plan=plan)
    check_true("R-6.1 **前提**：補平成功", "補平成功" in r.stdout, r.stdout)
    wss = r.of("record", "write_sync_state")
    check_true("R-6.1 **前提**：write_sync_state 被呼叫", len(wss) >= 1,
               f"實得 {len(wss)} 次。stdout：{r.stdout}")
    check_true("R-6.1：回寫失敗必須**紅燈**", r.rc != 0,
               f"整輪 rc={r.rc}——回寫失敗被靜默吞掉了")
    ns = [n for n in r.of("notify", "notify")
          if n["env"].get("AIDLC_REASON_CODE") == "ExternalError"]
    check_true("R-6.1：必須通報 ExternalError", len(ns) == 1,
               f"實得 {len(ns)} 則（全部："
               f"{[n['env'].get('AIDLC_REASON_CODE') for n in r.of('notify','notify')]}）")
    check("R-6.1：回寫失敗時**不推送**", len(r.of("record", "commit_and_push")), 0)


def test_r6_1_backfill_writeback_field_set() -> None:
    """@purpose R-6.1 ＋ 人工裁決 Q1=A ＋ **C-7.1**：補平成功後回寫的欄位集合恰為四欄，且**不含 managed_block_hash 也不含 last_synced_at**（兩者同源：本單元只寫 Status 欄、一個字都沒寫進受管區塊）。
    @given 看板 Status 為 Ready、本輪判定為 In progress（有落差），write_status 回 written
    @step 跑一輪 | **前提**：write_status 被呼叫一次且未回 aborted（否則下面每一條都是空的）
    @step 檢視 write_sync_state 收到的部分物件 | 恰為 last_status／last_written_status／last_field_value／last_reason_code（**四欄**）
    @step 檢視 last_written_status | 逐字等於本輪寫進看板的 Status
    @pass 兩個方向都會壞：少了 last_written_status，U-6 下一輪的 expected 停在補平前的舊值 ⇒ Aborted ＋ 假通報（R-6 存在的唯一理由）；**多了 last_synced_at，[US:S-6 AC 5] 的告示會永久靜默且無紅燈**（C-7.1）
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready",
                                    "last_field_value": "old"}), "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "code-generation (x)", "mapped"),
    }
    r = run_round(plan=plan)
    ws = r.of("board", "write_status")
    check_true("R-6.1 **前提**：write_status 被呼叫一次", len(ws) == 1,
               f"實得 {len(ws)} 次——沒有進補平路徑，下面的欄位斷言全部是空的。stdout：{r.stdout}")
    check_true("R-6.1 **前提**：補平真的成功（stdout 出現補平成功）",
               "補平成功" in r.stdout, r.stdout)
    patch = patch_of(r)
    check("R-6.1＋Q1=A：補平路徑回寫的欄位集合", sorted(patch.keys()),
          ["last_field_value", "last_reason_code", "last_status", "last_written_status"])
    # C-7.1（U-6 functional-design iteration 7 的 Critical，open-items.md:137，
    # deadline「Bolt 1 開工前」）：R-5.13 把 last_synced_at 的語意釘死在「受管區塊
    # 上一次成功寫入的時刻」，而補平不碰受管區塊。推進它會讓 U-6 的 R-5.6 把一則
    # **尚未送出**的告示判為已送 ⇒ [US:S-6 AC 5] 永久靜默且**無紅燈**。
    check_true("**C-7.1**：補平路徑**不得**推進 last_synced_at",
               "last_synced_at" not in patch,
               f"實得的 patch 鍵：{sorted(patch)}——補平一個字都沒寫進受管區塊，"
               "推進該欄會讓 [US:S-6 AC 5] 的告示永久靜默")
    check("Q1=A：last_written_status 為本輪寫進看板的值", patch.get("last_written_status"), "In progress")
    check("R-6.2：補平路徑**不動** managed_block_hash", "managed_block_hash" in patch, False)
    check("R-6.1：backfilled_count 為 1", r.metric("backfilled_count"), "1")


def test_r6_5_repair_writeback_field_set() -> None:
    """@purpose R-6.5 ＋ R-6.8 ＋ Q1=A：判定一致而 SyncState 落後（U-6 遺失的回寫）時的修復，欄位集合恰為六欄——比補平路徑**多** managed_block_hash（R-6.8，R-6.2 的唯一例外）。
    @given 看板 Status == 本輪判定，但 SyncState 三欄停在更早的一輪
    @step 跑一輪 | **前提**：write_status **零次**（確認走的是修復路徑而不是補平路徑）
    @step 檢視 write_sync_state 收到的部分物件 | 恰為六欄
    @step 檢視 managed_block_hash | 逐字取自本輪 read_item 的回傳
    @pass 漏掉 managed_block_hash 的後果是 U-8 每天拿舊雜湊比新區塊 ⇒ 在沒有任何人為變更下每天開一則反向 PR（ADR-A6 點名的最危險失效模式）
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready",
                                    "last_field_value": "old", "last_reason_code": "mapped",
                                    "managed_block_hash": "stale-hash"}), "binding": "12"}},
        "board:read_item": {"outputs": {"status": "In progress",
                                        "managed_block_hash": "sha256-from-readback"}},
        "map": map_out("In progress", "code-generation (x)", "mapped"),
    }
    r = run_round(plan=plan)
    check_true("R-6.5 **前提**：write_status 零次（判定一致，不是補平）",
               len(r.of("board", "write_status")) == 0,
               f"實得 {len(r.of('board', 'write_status'))} 次——走到補平路徑了，本測試量的不是 R-6.5")
    check_true("R-6.5 **前提**：stdout 說出「已修復遺失的回寫」",
               "已修復遺失的回寫" in r.stdout, r.stdout)
    patch = patch_of(r)
    check("R-6.5＋R-6.8＋Q1=A：修復路徑回寫的欄位集合", sorted(patch.keys()),
          ["last_field_value", "last_reason_code", "last_status",
           "last_synced_at", "last_written_status", "managed_block_hash"])
    check("R-6.8：雜湊取自本輪 read_item", patch.get("managed_block_hash"), "sha256-from-readback")
    check("Q1=A：last_written_status 為看板此刻真的是什麼", patch.get("last_written_status"), "In progress")
    check("R-6.5：這不是補平，backfilled_count 為 0", r.metric("backfilled_count"), "0")


def test_r6_5_repair_with_null_status_does_not_claim_a_write() -> None:
    """@purpose R-6.5 對「判定的 Status 為 null」（parked／suppressed／undecidable，U-6 依 R-5.10 (a) 跳過 write_status）**全無規定**，本檔的推導是：修復其餘五欄，但**不動 last_written_status**。理由：那條規則的安全論證（「人為改動不會恰好把看板改成 record 的值」）只在看板 == 判定時成立；判定為 null 時看板上的值可能是任何人放上去的，記進去會讓 U-6 下一輪的 expected 與人為值相符而**靜默覆寫**掉它——[req:FR-G3] 要保護的正是這一類 item 的 Status。
    @given 一個判為 parked 的已綁定 intent（dec_status 為空），SyncState 的判定三欄落後，看板 Status 停在一個舊值
    @step 跑一輪 | **前提**：write_status 零次，且確實走到修復（stdout 說出「已修復遺失的回寫」）
    @step 檢視回寫的部分物件 | 恰為五欄，**不含 last_written_status**
    @step 檢視 last_status | 為 null（判定就是判定，null 也是判定）
    @pass 代價如實記載：該欄可能停在舊值、日後產生一次假 Aborted ＋ 通報——那是**大聲**的失敗；靜默覆寫人為改動不可
    @story S-6
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready",
                                    "last_field_value": "v0", "last_reason_code": "mapped"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready", "managed_block_hash": "h-now"}},
        "map": map_out("", "parked @ x", "parked"),
    }
    r = run_round(plan=plan)
    check_true("**前提**：write_status 零次", len(r.of("board", "write_status")) == 0, r.stdout)
    check_true("**前提**：確實走到 R-6.5 的修復", "已修復遺失的回寫" in r.stdout, r.stdout)
    patch = patch_of(r)
    check("判定為 null 時的修復欄位集合", sorted(patch.keys()),
          ["last_field_value", "last_reason_code", "last_status",
           "last_synced_at", "managed_block_hash"])
    check_true("**不宣稱一次沒發生的寫入**：不含 last_written_status",
               "last_written_status" not in patch, f"實得 {sorted(patch)}")
    check("last_status 為 null（判定就是判定）", patch.get("last_status"), None)
    check("R-2.1：parked 排除於分母", r.metric("consistency.denominator"), "0")


def test_r6_3_no_writeback_when_aborted() -> None:
    """@purpose R-6.3 的第一半（補平失敗）：write_status 回 Aborted ⇒ 看板一個字都沒動 ⇒ **完全不回寫**、不推送；進 aborted 清單、計入分子；通報但**不紅燈**。
    @given 有落差，write_status 回 aborted
    @step 跑一輪 | **前提**：write_status 被呼叫且 stdout 說出「補平回 aborted」
    @step 檢視回寫與推送 | 零 write_sync_state、零 commit_and_push
    @step 檢視報告 | aborted 清單含該 intent；分母 1／分子 1
    @pass 此時回寫任何欄位都會是一個沒發生過的寫入
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "v", "mapped"),
        "board:write_status": {"outputs": {"result": "aborted", "actual_status": "Done",
                                           "message": "write_status：回讀不符"}},
    }
    r = run_round(plan=plan)
    check_true("R-6.3 **前提**：補平確實回 aborted", "補平回 aborted" in r.stdout, r.stdout)
    check("R-6.3：**完全不回寫**", len(r.of("record", "write_sync_state")), 0)
    check("R-6.3：不推送", len(r.of("record", "commit_and_push")), 0)
    check("R-1：進 aborted 清單", r.list_cell("aborted（回讀不符已中止）"), ("1", "260899-alpha"))
    check("R-2.2：aborted 計入分母", r.metric("consistency.denominator"), "1")
    check("R-2.2：aborted 計入分子", r.metric("consistency.numerator"), "1")
    ns = r.of("notify", "notify")
    check("通報 Aborted", ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "Aborted")
    check("Aborted 不紅燈（機制的正常判斷）", r.rc, 0)


def test_r6_3_no_writeback_when_backfill_external_error() -> None:
    """@purpose R-6.3 的第一半（另一種補平失敗）：write_status 拋 ExternalError ⇒ 不回寫、不推送、紅燈、通報 ExternalError。
    @given 有落差，write_status 以非零 exit 收場
    @step 跑一輪 | **前提**：整輪紅燈（否則代表 exit 沒生效，其餘斷言恆真）
    @step 檢視回寫 | 零 write_sync_state、零 commit_and_push
    @pass 與 Aborted 分開：一個是機制的正常判斷、一個是真的失敗
    @story S-8
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "v", "mapped"),
        "board:write_status": {"exit": 1, "outputs": {"result": "external_error",
                                                      "message": "GraphQL 502"}},
    }
    r = run_round(plan=plan)
    check_true("R-6.3 **前提**：整輪紅燈（write_status 的非零 exit 真的生效了）",
               r.rc != 0, f"rc={r.rc}——exit 沒生效，本測試的其餘斷言全部是空的。{r.stdout}")
    check("R-6.3：**完全不回寫**", len(r.of("record", "write_sync_state")), 0)
    check("R-6.3：不推送", len(r.of("record", "commit_and_push")), 0)
    ns = r.of("notify", "notify")
    check("通報 ExternalError", ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "ExternalError")
    check("R-2：無法判定一致性者計入分子（ADR-A5 的「機制放棄擔保」原則）",
          r.metric("consistency.numerator"), "1")


def test_r6_3_no_writeback_when_consistent_and_state_matches() -> None:
    """@purpose R-6.3 的第二半（跳過）：看板 == 判定**且** SyncState 相符 ⇒ 什麼都不寫。這是對帳的常態，也是「重跑一輪結果相同」的來源。
    @given 三者一致（stub 的基準情境）
    @step 跑一輪 | 零 write_status、零 write_sync_state、零 commit_and_push
    @step 檢視報告 | 分母 1、分子 0、backfilled_count 0
    @pass 冪等：無落差時零寫入
    @story S-9
    """
    r = run_round()
    check("R-6.3：零 write_status", len(r.of("board", "write_status")), 0)
    check("R-6.3：零回寫", len(r.of("record", "write_sync_state")), 0)
    check("R-6.3：零推送", len(r.of("record", "commit_and_push")), 0)
    check_true("R-6.3 **前提**：stdout 說出「一致且 SyncState 相符」",
               "一致且 SyncState 相符" in r.stdout, r.stdout)
    check("一致者計入分母", r.metric("consistency.denominator"), "1")
    check("一致者**不**計入分子", r.metric("consistency.numerator"), "0")
    check("沒有補平", r.metric("backfilled_count"), "0")


def test_r6_7_expected_comes_from_this_round_read_item() -> None:
    """@purpose R-6.7：補平時 write_status 的 expected 取自**本輪剛做的 read_item**，不取自 SyncState。這與 U-6 的 R-5.7 **刻意相反**——兩者守的是不同的問題（U-6：我上次寫進去之後有沒有別人動過；本單元：我讀到當下狀態到我寫入之間有沒有人插隊，是單輪內的樂觀鎖）。**實作不得把兩者「對齊」。**
    @given SyncState.last_written_status 與看板現值**刻意不同**（Ready vs Blocked）
    @step 跑一輪 | write_status 收到的 expected 逐字為看板現值 Blocked
    @step 確認它不是 SyncState 的值 | expected != Ready
    @step 檢視呼叫序 | read_item 在 write_status **之前**
    @pass 取錯來源的後果不是報錯而是靜默——並行的 U-6 寫入插隊時不會被擋下
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Blocked"}},
        "map": map_out("In progress", "v", "mapped"),
    }
    r = run_round(plan=plan)
    ws = r.of("board", "write_status")
    check_true("R-6.7 **前提**：write_status 被呼叫一次", len(ws) == 1, r.stdout)
    check("R-6.7：expected 取自本輪 read_item", ws[0]["env"].get("AIDLC_EXPECTED_STATUS") if ws else None, "Blocked")
    check("R-6.7：desired 為本輪判定", ws[0]["env"].get("AIDLC_DESIRED_STATUS") if ws else None, "In progress")
    seq = r.seq()
    check_true("R-6.7：read_item 在 write_status 之前",
               "board:read_item" in seq and "board:write_status" in seq
               and seq.index("board:read_item") < seq.index("board:write_status"), str(seq))


def test_r6_6_at_most_one_push_per_intent() -> None:
    """@purpose R-6.6：回寫與補平走**同一個** commit_and_push——不因 R-6.1 與 R-6.5 是兩條規則就推兩次。
    @given 兩個 intent 都需要補平
    @step 跑一輪 | commit_and_push 恰為兩次（每個 intent 一次），不是四次
    @step 檢視 paths | 逐字只有該 intent 的 sync-state.json（U-4 的 R-3.2 白名單）
    @pass 每個 intent 至多一次推送
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "v", "mapped"),
    }
    r = run_round(plan=plan, registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"}])
    check_true("R-6.6 **前提**：兩個 intent 都補平了", r.metric("backfilled_count") == "2", r.stdout)
    check("R-6.6：每個 intent 至多一次推送", len(r.of("record", "commit_and_push")), 2)
    check("R-6.6：每個 intent 至多一次回寫", len(r.of("record", "write_sync_state")), 2)
    pushes = r.of("record", "commit_and_push")
    paths = sorted(c["env"].get("AIDLC_PATHS", "") for c in pushes)
    check("U-4 R-3.2：paths 白名單", paths,
          [f"{RECORD_ROOT}/260899-alpha/sync-state.json",
           f"{RECORD_ROOT}/260899-beta/sync-state.json"])


def test_commit_and_push_branch_and_message() -> None:
    """@purpose R-7.2 ＋ U-4 的介面約束：推送落點是從 trunk 分叉的自建分支（不推 ut／main），訊息必含同步標記（U-4 的 require_message 會擋，且它是 U-6 防線②的依據）。
    @given 一輪會回寫的執行
    @step 檢視 commit_and_push 收到的 branch | 前綴 ＋ 日期，且不是 ut／main
    @step 檢視 message | 含由 record.sh 推導出的同步標記
    @pass 標記字串與 record.sh 的常數同源；分支不落在受保護的整合主幹上
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "v", "mapped"),
    }
    r = run_round(plan=plan)
    pushes = r.of("record", "commit_and_push")
    check_true("**前提**：有推送發生", len(pushes) == 1, r.stdout)
    branch = pushes[0]["env"].get("AIDLC_BRANCH", "") if pushes else ""
    check_true("R-7.2：分支前綴", branch.startswith(BRANCH_PREFIX + "/"), branch)
    check_true("R-7.2：分支帶日期",
               re.match(rf"^{re.escape(BRANCH_PREFIX)}/\d{{4}}-\d{{2}}-\d{{2}}$", branch) is not None, branch)
    check("R-7.2：不推 trunk", branch == TRUNK_REF, False)
    check("R-7.2：不推 main", branch == "main", False)
    check_true("U-4 R-3.3：訊息含同步標記", MARKER in pushes[0]["env"].get("AIDLC_MESSAGE", ""),
               pushes[0]["env"].get("AIDLC_MESSAGE", "") if pushes else "")


# ==========================================================================
# Q1=A 的跨單元串接（單輪測試結構上看不到它）
# ==========================================================================

def test_q1_cross_unit_last_written_status_round_trip() -> None:
    """@purpose **跨 U-6／U-7 的多輪測試**：U-6 寫成功但回寫沒落地（commit_and_push 被拒，R-5.9 ②）→ U-7 依 R-6.5 修復 → **U-6 下一輪的 expected 必須是被修復後的值**。這條是 Q1=A 唯一的守門：少了 last_written_status，前兩輪照樣全綠，第三輪才會 Aborted ＋ 假通報。
    @given round-1 由 U-6 的**真實編排腳本**執行：判定 In progress、看板寫成功、commit_and_push 回 exit 3（Rejected）⇒ 狀態檔在 trunk 上仍是舊的 Ready
    @step round-1 | **前提**：U-6 的 write_status 真的跑了，且推送真的被拒（否則沒有「遺失的回寫」可修）
    @step round-2 由 U-7 執行 | **前提**：走的是修復路徑（write_status 零次）；斷言 last_written_status 被寫成 In progress
    @step round-3 再由 U-6 的真實腳本執行，record 又前進到 Done | write_status 收到的 expected 為 **In progress**（看板現值），不是 Ready
    @pass expected 若停在 Ready，U-3 的回讀比對會判不符 ⇒ Aborted ⇒ 一則沒有任何人為變更的假通報。**「補平愈成功、假通報愈多」正是 R-6 這一整群存在的唯一理由。**
    @story S-3
    """
    u6 = load_u6_runner()

    # ---- round-1：U-6 寫成功、回寫推送被拒 ----------------------------------
    stale = {"binding": 12, "last_status": "Ready", "last_written_status": "Ready",
             "last_field_value": "v0", "last_reason_code": "mapped",
             "managed_block_hash": "hash-round-0", "last_synced_at": "2026-09-01T00:00:00Z"}
    r1 = u6.run_round(plan={
        "record:read_sync_state": {"outputs": {"state_json": u6.state_of(stale), "binding": "12"}},
        "map": {"outputs": {"status": "In progress", "field_value": "v1",
                            "reason_code": "mapped", "traceable_row": "R-3.5",
                            "scope_note": ""}},
        "record:commit_and_push": {"exit": 3, "outputs": {
            "result": "rejected", "reason": "non_fast_forward_exhausted", "message": "推不上去"}},
    })
    u6_ws = r1.of("board", "write_status")
    check_true("跨單元 **前提 1**：U-6 的 write_status 真的跑了（看板確實被寫成 In progress）",
               len(u6_ws) == 1 and u6_ws[0]["env"].get("AIDLC_DESIRED_STATUS") == "In progress",
               f"實得 {u6_ws}")
    check_true("跨單元 **前提 2**：U-6 的推送真的被拒（否則沒有遺失的回寫可修）",
               r1.rc != 0 and any(c["env"].get("AIDLC_REASON_CODE") == "Rejected"
                                  for c in r1.of("notify", "notify")),
               f"rc={r1.rc}；通報={[c['env'].get('AIDLC_REASON_CODE') for c in r1.of('notify', 'notify')]}")
    # 推送被拒 ⇒ trunk 上的狀態檔沒變，仍是 stale。

    # ---- round-2：U-7 對帳，看板 == record 而 SyncState 落後 ----------------
    r2 = run_round(plan={
        "record:read_sync_state": {"outputs": {"state_json": state_of(stale), "binding": "12"}},
        "board:read_item": {"outputs": {"status": "In progress",
                                        "managed_block_hash": "hash-round-1"}},
        "map": map_out("In progress", "v1", "mapped"),
    })
    check_true("跨單元 **前提 3**：U-7 走的是 R-6.5 修復路徑（write_status 零次）",
               len(r2.of("board", "write_status")) == 0,
               f"實得 {len(r2.of('board', 'write_status'))} 次——走成補平了，本測試量的不是修復")
    repair = patch_of(r2)
    check("Q1=A：修復**確實寫了** last_written_status", repair.get("last_written_status"), "In progress")
    check("R-6.8：修復同時把雜湊追上", repair.get("managed_block_hash"), "hash-round-1")

    # ---- round-3：record 又前進，U-6 再跑一輪 -------------------------------
    repaired = dict(stale)
    repaired.update(repair)
    r3 = u6.run_round(plan={
        "record:read_sync_state": {"outputs": {"state_json": u6.state_of(repaired), "binding": "12"}},
        "map": {"outputs": {"status": "Done", "field_value": "v2",
                            "reason_code": "mapped", "traceable_row": "R-3.3",
                            "scope_note": ""}},
    })
    ws3 = r3.of("board", "write_status")
    check_true("跨單元 **前提 4**：round-3 有進寫入鏈（record 前進了，必有漂移）",
               len(ws3) == 1, f"實得 {len(ws3)} 次——沒進寫入鏈，expected 斷言是空的。{r3.stdout}")
    check("**Q1=A 的守門**：U-6 下一輪的 expected 是被修復後的值",
          ws3[0]["env"].get("AIDLC_EXPECTED_STATUS") if ws3 else None, "In progress")
    check_true("**Q1=A 的守門（反面）**：expected 不是補平前的舊值 Ready",
               (ws3[0]["env"].get("AIDLC_EXPECTED_STATUS") if ws3 else None) != "Ready",
               "expected 停在 Ready ⇒ U-3 回讀比對判不符 ⇒ Aborted ＋ 一則沒有任何人為變更的假通報")


# ==========================================================================
# R-1／R-2 群：清單成員身分與一致率
# ==========================================================================

def test_r2_1_two_exclusions_only() -> None:
    """@purpose R-2.1：分母 = 已綁定的 intent − awaiting_human − parked。**兩類排除，不多不少**（R-2.3 明文禁止擴為三類，ADR-A5 的 Alternatives Rejected）。
    @given 四個已綁定 intent：suppressed／parked／一致的 mapped／有落差的 mapped
    @step 跑一輪 | **前提**：四個 intent 各跑一次 map（都真的被處理了）
    @step 檢視報告 | 分母 2（兩個 mapped）、分子 1（只有有落差的那個）
    @step 檢視清單 | awaiting_human 與 parked 各一筆
    @pass 排除類別數未被擴大，也未被縮小
    @story S-9
    """
    plan = {
        "map@260899-sup": map_out("", "frozen: x", "suppressed"),
        "map@260899-park": map_out("", "parked @ x", "parked"),
        "map@260899-ok": map_out("In progress", "v", "mapped"),
        "map@260899-drift": map_out("In progress", "v", "mapped"),
        "record:read_sync_state@260899-drift": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item#4": {"outputs": {"status": "Ready"}},
    }
    reg = [{"dirName": n} for n in ("260899-sup", "260899-park", "260899-ok", "260899-drift")]
    r = run_round(plan=plan, registry=reg)
    check_true("R-2.1 **前提**：四個 intent 都被處理了", len(r.of("map")) == 4,
               f"實得 {len(r.of('map'))} 次 map；{r.stdout}")
    check_true("R-2.1 **前提**：有落差的那個真的補平了", r.metric("backfilled_count") == "1", r.stdout)
    check("R-2.1：分母排除 awaiting_human 與 parked", r.metric("consistency.denominator"), "2")
    check("R-2.2：分子只有那個有落差的", r.metric("consistency.numerator"), "1")
    check("R-1：awaiting_human 清單", r.list_cell("awaiting_human"), ("1", "260899-sup"))
    check("R-1：parked 清單", r.list_cell("parked（Parked 非空"), ("1", "260899-park"))


def test_r2_3_no_third_exclusion_class() -> None:
    """@purpose R-2.3：`unparseable`／`undecidable`／`whitelisted` **計入分母也計入分子**——它們是「機制放棄擔保」不是「機制刻意不動」，不得被當成第三類排除。
    @given 三個已綁定 intent 分別判為 unparseable／undecidable／whitelisted
    @step 跑一輪 | **前提**：三個 intent 各跑一次 map
    @step 檢視報告 | 分母 3、分子 3
    @pass 把它們排除於分母會讓一致率變成「只看有把握的那些」——那正是 ADR-A5 駁回的形狀
    @story S-9
    """
    plan = {
        "map@260899-unp": map_out("", "", "unparseable"),
        "map@260899-und": map_out("", "", "undecidable"),
        "map@260899-wl": map_out("", "", "whitelisted"),
    }
    reg = [{"dirName": n} for n in ("260899-unp", "260899-und", "260899-wl")]
    r = run_round(plan=plan, registry=reg, whitelist="260899-wl")
    check_true("R-2.3 **前提**：三個 intent 都被處理了", len(r.of("map")) == 3, r.stdout)
    check("R-2.3：三者全部計入分母", r.metric("consistency.denominator"), "3")
    check("R-2.3：三者全部計入分子", r.metric("consistency.numerator"), "3")


def test_r1_1_unparseable_and_undecidable_stay_separate() -> None:
    """@purpose R-1.1：`unparseable` 與 `undecidable` **不得合併成一個清單**——前者是 record 的必要區塊缺失（修 record），後者是 record 讀得出來但訊號不落在對照表任一列（修對照表）。合成一份會讓人看到一堆 id 卻不知道該修哪邊。`undecidable` 是缺口 G-1 的關閉點（[US:S-2 AC 4] 逐字要求「無法判定」清單）。
    @given 一個 unparseable、一個 undecidable
    @step 檢視報告的兩份清單 | 各一筆且**內容不同**
    @pass 兩個 reason_code 不能互相頂替
    @story S-2
    """
    plan = {
        "map@260899-unp": map_out("", "", "unparseable"),
        "map@260899-und": map_out("", "", "undecidable"),
    }
    r = run_round(plan=plan, registry=[{"dirName": "260899-unp"}, {"dirName": "260899-und"}])
    check_true("R-1.1 **前提**：兩個 intent 都被處理了", len(r.of("map")) == 2, r.stdout)
    check("R-1.1：unparseable 清單", r.list_cell("unparseable（白名單外"), ("1", "260899-unp"))
    check("R-1.1（G-1）：undecidable 清單", r.list_cell("undecidable（訊號不落在"), ("1", "260899-und"))


def test_us_s3_ac6_whitelisted_has_no_list() -> None:
    """@purpose [US:S-3 AC 6] 逐字：「白名單外者進『無法解析』清單、**白名單內者不進**」。whitelisted 刻意沒有清單——把它列進報告等於每天提醒一次一件已經決定不處理的事。
    @given 一個判為 whitelisted 的已綁定 intent
    @step 檢視 unparseable 清單 | 空
    @step 檢視分母分子 | 各 1（不進清單 ≠ 不計入）
    @pass 「不進任何清單」是 AC 的直接後果，不是遺漏
    @story S-3
    """
    r = run_round(plan={"map": map_out("", "", "whitelisted")}, whitelist="260899-alpha")
    check_true("**前提**：該 intent 真的判為 whitelisted", "reason_code='whitelisted'" in r.stdout, r.stdout)
    check("[US:S-3 AC 6]：不進 unparseable 清單", r.list_cell("unparseable（白名單外"), ("0", "（無）"))
    check("[US:S-3 AC 6]：不進 undecidable 清單", r.list_cell("undecidable（訊號不落在"), ("0", "（無）"))
    check("但仍計入分母", r.metric("consistency.denominator"), "1")
    check("也仍計入分子", r.metric("consistency.numerator"), "1")


def test_fr_j3_excluded_reason_codes_get_no_board_write() -> None:
    """@purpose [req:FR-J3]（同 U-6 的 R-3.0）：unparseable／whitelisted **一個看板寫入都沒有**、也不回寫狀態檔。讀取不在禁止之列——issue_status_mismatch 需要看板的 Status 才判得出來。
    @given 兩個已綁定 intent，分別判為 unparseable 與 whitelisted，且看板值與判定不同
    @step 跑一輪 | **前提**：兩者的 read_item 都跑了（確認流程真的走到了寫入前）
    @step 檢視寫入 | 零 write_status、零 write_sync_state、零 commit_and_push
    @step 檢視結束狀態 | 不紅燈（這是正常判斷不是失敗）
    @pass 「不對其產生任何看板寫入」是承諾，不該依賴 dec_status 為空這個副作用成立
    @story S-3
    """
    plan = {
        "map@260899-unp": map_out("", "", "unparseable"),
        "map@260899-wl": map_out("", "", "whitelisted"),
        "board:read_item": {"outputs": {"status": "Ready"}},
    }
    r = run_round(plan=plan, registry=[{"dirName": "260899-unp"}, {"dirName": "260899-wl"}],
                  whitelist="260899-wl")
    check("FR-J3 **前提**：兩者的 read_item 都跑了", len(r.of("board", "read_item")), 2)
    for op in BOARD_WRITE_OPS:
        check(f"FR-J3：零 board:{op}", len(r.of("board", op)), 0)
    check("FR-J3：零狀態回寫", len(r.of("record", "write_sync_state")), 0)
    check("FR-J3：零推送", len(r.of("record", "commit_and_push")), 0)
    check("FR-J3：不紅燈", r.rc, 0)


def test_unbound_intent_is_skipped_and_not_in_denominator() -> None:
    """@purpose [req:FR-D2]：對帳的處理清單是「已綁定」的 intent。未綁定＝尚未首建，屬 U-6 的首建路徑——**不是錯誤**、不進任何清單、**不計入分母**。過濾必須在 map() 之前：map 的七條判定規則沒有一條檢查 binding，而下一步的 read_item 需要 binding 卻沒有。
    @given 兩個 intent，其中一個的 sync-state.json 無 binding
    @step 跑一輪 | 未綁定者零 map、零 board 呼叫
    @step 檢視報告 | 分母 1；「registry 內未綁定」為 1
    @pass 過濾在 map() 之前，而不是靠 map 自己擋
    @story S-9
    """
    plan = {"record:read_sync_state@260899-new": {"outputs": {
        "state_json": state_of({"binding": None, "last_status": None,
                                "last_written_status": None, "last_field_value": None,
                                "last_reason_code": None}), "binding": ""}}}
    r = run_round(plan=plan, registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-new"}])
    check_true("**前提**：未綁定者的 read_sync_state 真的跑了",
               len(r.of("record", "read_sync_state", qual="260899-new")) == 1, r.stdout)
    check("FR-D2：未綁定者零 map（過濾在 map 之前）", len(r.of("map", qual="260899-new")), 0)
    check("FR-D2：未綁定者零 board 呼叫", len(r.of("board", qual="")), 0)
    check("FR-D2：不計入分母", r.metric("consistency.denominator"), "1")
    check("FR-D2：未綁定計數有出現在報告上", r.metric("registry 內未綁定"), "1")
    check("FR-D2：不是錯誤（不紅燈）", r.rc, 0)


# ==========================================================================
# R-8 群：read_issue_state 的承接
# ==========================================================================

def test_r8_issue_closed_with_non_done_status_is_listed() -> None:
    """@purpose R-8.1／R-8.2：對每個已綁定 intent 呼叫一次 `read_issue_state`；回 closed 而看板 Status 不為終局值者進 issue_status_mismatch 清單（[US:S-9 AC 5]）。這個方法先前是**沒有任何呼叫者的孤兒契約**，R-8 群就是為了承接它。
    @given issue 已關閉、看板 Status 為 In progress
    @step 跑一輪 | **前提**：read_issue_state 確實被呼叫了一次
    @step 檢視報告 | issue_status_mismatch 含該 intent
    @step 檢視分母分子（R-8.3 的正交性）| 一致者仍是分母 1／分子 0，不受 issue 開關影響
    @pass 把「issue 關了」算成不一致，會讓一個與同步正確性無關的人為動作污染 NFR-O2
    @story S-9
    """
    plan = {"board:read_issue_state": {"outputs": {"issue_state": "closed"}}}
    r = run_round(plan=plan)
    check("R-8.1 **前提**：read_issue_state 被呼叫一次", len(r.of("board", "read_issue_state")), 1)
    check("R-8.2：進 issue_status_mismatch 清單",
          r.list_cell("issue_status_mismatch"), ("1", "260899-alpha"))
    check("R-8.3：不影響分母", r.metric("consistency.denominator"), "1")
    check("R-8.3：不影響分子", r.metric("consistency.numerator"), "0")
    check("R-8.2：僅偵測與列出，不改 Status", len(r.of("board", "write_status")), 0)


def test_r8_issue_closed_with_done_status_is_not_a_mismatch() -> None:
    """@purpose R-8.2 的另一半：issue 已關閉**而 Status 就是終局值**時不算不相稱——這才是正常結案。終局值由 map.sh 的 R-3.3 那一列推導，不在受測腳本裡抄一份字面。
    @given issue 已關閉、看板 Status 為終局值
    @step 跑一輪 | **前提**：read_issue_state 回 closed（情境真的成立）
    @step 檢視報告 | issue_status_mismatch 為空
    @pass 若清單恆滿，這份報告每天會列出所有已結案的 intent，訊號被雜訊淹沒
    @story S-9
    """
    plan = {
        "board:read_issue_state": {"outputs": {"issue_state": "closed"}},
        "board:read_item": {"outputs": {"status": DONE}},
        "map": map_out(DONE, "v", "mapped"),
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": DONE, "last_written_status": DONE,
                                    "last_field_value": "v"}), "binding": "12"}},
    }
    r = run_round(plan=plan)
    ris = r.of("board", "read_issue_state")
    check_true("R-8.2 **前提**：issue 真的是 closed", len(ris) == 1, r.stdout)
    check_true("R-8.2 **前提**：看板 Status 真的是終局值", f"reason_code='mapped' status='{DONE}'" in r.stdout, r.stdout)
    check("R-8.2：不算不相稱", r.list_cell("issue_status_mismatch"), ("0", "（無）"))


# ==========================================================================
# R-3 群：處理量上限
# ==========================================================================

def test_r3_batch_limit_and_deferred_list() -> None:
    """@purpose R-3.1／R-3.2：上限以 input 宣告，改該值後**下一輪**處理量隨之改變（[US:S-7 AC 3] 的可驗證點）；R-3.4：超出上限而未處理者**必須可被辨識**，否則「今天沒處理到」與「今天處理了且一致」在報告上長得一樣。
    @given 三個已綁定 intent，batch_size 為 2
    @step 跑一輪 | **前提**：map 只跑兩次（上限真的生效了）
    @step 檢視報告 | deferred 清單為第三個 intent；分母 2（不含未處理者）
    @step 以 batch_size=3 再跑一次 | map 三次、deferred 空
    @pass 一致率偏高比偏低危險：偏低促使人去查，偏高讓人以為沒事
    @story S-7
    """
    reg = [{"dirName": n} for n in ("260899-a", "260899-b", "260899-c")]
    r = run_round(registry=reg, batch_size="2")
    check_true("R-3.1 **前提**：上限真的生效（map 只跑兩次）", len(r.of("map")) == 2,
               f"實得 {len(r.of('map'))} 次；{r.stdout}")
    check("R-3.4：未處理者進 deferred 清單", r.list_cell("deferred"), ("1", "260899-c"))
    check("R-3.4：未處理者不進分母", r.metric("consistency.denominator"), "2")
    check("R-3.1：未處理者零 board 呼叫", len(r.of("board", qual="")), 0)

    r2 = run_round(registry=reg, batch_size="3")
    check("R-3.2：改上限後處理量隨之改變", len(r2.of("map")), 3)
    check("R-3.2：不再有 deferred", r2.list_cell("deferred"), ("0", "（無）"))
    check("R-3.2：分母隨之變成 3", r2.metric("consistency.denominator"), "3")


def test_r3_batch_size_must_be_a_positive_integer() -> None:
    """@purpose 批次上限是介面契約。非正整數是呼叫端 bug，必須立刻中止——被當成 0 或空字串靜默略過的話，整輪會變成「什麼都沒對帳」而報告看起來正常。
    @given batch_size 為空字串／非數字／0
    @step 各跑一輪 | 三者皆非零 exit 且零 action 呼叫
    @pass 失敗要出聲
    @story S-7
    """
    for bad in ("", "abc", "0"):
        r = run_round(batch_size=bad)
        check_true(f"batch_size='{bad}' 應中止", r.rc != 0, r.stdout)
        check(f"batch_size='{bad}' 零 action 呼叫", len(r.of("map")) + len(r.of("board")), 0)


# ==========================================================================
# R-4 群：失敗的影響範圍
# ==========================================================================

def test_r4_2_reverse_pending_fail_closed() -> None:
    """@purpose R-4.2：反向 PR 查詢失敗 → **整輪中止**、紅燈、通報，且對任何 intent 都沒有動作。理由在本單元比 U-6 更硬：reverse_pending 決定 awaiting_human 清單，而該清單直接決定一致率的**分母**——**發布一份分母算錯的報告，比不發布更糟**。
    @given gh pr list 以非零 exit 收場
    @step 跑一輪 | **前提**：整輪非零 exit（fail-closed 真的觸發了）
    @step 檢視呼叫紀錄 | map／board／record 全數零呼叫
    @step 檢視報告 | 一個字都沒寫（分母算不出來就不發布）
    @pass 不得退化為 fail-open 的空集合
    @story S-9
    """
    r = run_round(pr_list_fail=True)
    check_true("R-4.2 **前提**：整輪中止且紅燈", r.rc != 0, r.stdout)
    check("R-4.2：零 map 呼叫", len(r.of("map")), 0)
    check("R-4.2：零 board 呼叫", len(r.of("board")), 0)
    check("R-4.2：零 record 呼叫", len(r.of("record")), 0)
    check("R-4.2：不發布報告", r.report.strip(), "")
    ns = r.of("notify", "notify")
    check("R-4.2：通報一次", len(ns), 1)
    check("R-4.2：通報 ExternalError",
          ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "ExternalError")


def test_reverse_pending_reaches_map_and_becomes_awaiting_human() -> None:
    """@purpose 一次查詢算出的 reverse_pending 逐字傳進 U-1 的 map，並由它的判定（suppressed）決定 awaiting_human 的成員身分——本單元不自己算「誰在等人」。
    @given 一則開啟中的反向 PR 只碰 alpha 的 record 路徑
    @step 跑一輪 | **前提**：只查一次 gh；兩個 intent 各一次 map
    @step 檢視 map 收到的 AIDLC_REVERSE_PENDING | 逐字為 alpha
    @pass 逐 intent 而非全域（[US:S-6 AC 3] 的反例）
    @story S-6
    """
    pr = json.dumps([{
        "number": 1, "state": "OPEN",
        "files": [{"path": f"{RECORD_ROOT}/260899-alpha/aidlc-state.md"}],
    }])
    r = run_round(registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"}],
                  pr_list_json=pr)
    check("只查一次", len(r.of("gh")), 1)
    maps = r.of("map")
    check_true("**前提**：兩個 intent 各一次 map", len(maps) == 2, r.stdout)
    check("reverse_pending 逐字為 alpha", maps[0]["env"].get("AIDLC_REVERSE_PENDING", "").strip(),
          "260899-alpha")
    check("beta 那次也拿到同一個集合（整輪算一次）",
          maps[1]["env"].get("AIDLC_REVERSE_PENDING", "").strip(), "260899-alpha")
    check_true("label 取自 U-6 的 impl（D-1 的唯一物化點）",
               any(REVERSE_LABEL in " ".join(c.get("argv", [])) for c in r.of("gh")),
               str([c.get("argv") for c in r.of("gh")]))


def test_r4_1_single_intent_failure_does_not_abort_round() -> None:
    """@purpose R-4.1：單一 intent 的失敗**不中止整輪**——計入報告後續跑。與 R-4.2 的分界是**影響範圍**不是嚴重度：reverse_pending 是全輪共用的前提，單一 intent 的 API 失敗只影響那一個。
    @given 三個 intent，第一個的 read_sync_state 失敗、第二個的 read_item 失敗
    @step 跑一輪 | **前提**：整輪紅燈（兩個失敗真的發生了）
    @step 檢視第三個 intent | 照常被處理（map ＋ read_item ＋ read_issue_state 都有）
    @step 檢視報告 | 有產出（部分完成是正常狀態，不是失敗）
    @pass 一輪對帳的「成功」是「掃過了、該補的補了、補不了的列進清單了」
    @story S-8
    """
    plan = {
        "record:read_sync_state@260899-a": {"exit": 1},
        "board:read_item#1": {"exit": 1, "outputs": {"message": "GraphQL 502"}},
        "record:read_sync_state@260899-b": {"outputs": {"state_json": state_of({}), "binding": "21"}},
        "record:read_sync_state@260899-c": {"outputs": {"state_json": state_of({}), "binding": "31"}},
    }
    reg = [{"dirName": n} for n in ("260899-a", "260899-b", "260899-c")]
    r = run_round(plan=plan, registry=reg)
    check_true("R-4.1 **前提**：整輪紅燈（兩個失敗真的發生了）", r.rc != 0, r.stdout)
    check_true("R-4.1 **前提**：read_sync_state 真的失敗了",
               "read_sync_state 失敗" in r.stdout, r.stdout)
    check("R-4.1：第三個 intent 照常跑 map", len(r.of("map", qual="260899-c")), 1)
    check("R-4.1：第三個 intent 照常跑 read_issue_state",
          len(r.of("board", "read_issue_state", qual="31")), 1)
    check_true("R-4.1：報告仍然產出（部分完成是正常狀態）",
               "AI-DLC 對帳報告" in r.report, r.report[:200])
    check("R-4.1：兩次失敗各通報一次", len(r.of("notify", "notify")), 2)


def test_f5_actions_bash_e_does_not_abort_the_round() -> None:
    """@purpose F5 迴歸：GitHub Actions 對未指定 `shell:` 的 `run:` 用 `bash -e {0}`，而 `set -uo pipefail` 關不掉已生效的 `-e`。本檔在此**自己釘住 `bash -e`**（不依賴模組層 BASH 預設值），驗證 `set +e` 真的在 rc 判讀之前生效——沒有它，R-4.1 的「單一 intent 失敗不中止整輪」在真實 runner 上不成立，而本 workflow 是每日排程的對帳，一次失敗等於當天整輪對帳沒做。
    @given 明確以 `bash -e` 啟動受測腳本；三個 intent，第一個的 read_sync_state 以非零 exit 收場
    @step 跑一輪 | **前提**：該失敗確實發生（stdout 有 read_sync_state 失敗）
    @step 檢視第二、三個 intent | 照常跑完 map ＋ read_issue_state——證明控制流越過了 `rc=$?`
    @step 檢視報告 | 仍然產出（部分完成是正常狀態）
    @step 檢視通報 | 恰一則 ExternalError，且掛在第一個 intent 上（錯誤紀錄指名到 intent）
    @step 檢視結束狀態 | 紅燈（不中止整輪 ≠ 把失敗吞掉）
    @pass 行為斷言，不比對 `set +e` 字面——有 `set +e` 但位置放在 rc 判讀之後一樣會紅
    @story S-8
    """
    plan = {
        "record:read_sync_state@260899-a": {"exit": 1},
        "record:read_sync_state@260899-b": {"outputs": {"state_json": state_of({}), "binding": "21"}},
        "record:read_sync_state@260899-c": {"outputs": {"state_json": state_of({}), "binding": "31"}},
    }
    reg = [{"dirName": n} for n in ("260899-a", "260899-b", "260899-c")]
    r = run_round(plan=plan, registry=reg, bash_argv=["bash", "-e"])
    check_true("**前提**：確實以 -e 啟動仍走完整輪（不是 shell 一開始就死）",
               r.stdout.strip() != "", "受測腳本沒有任何輸出——errexit 可能在第一個非零就殺掉了 step")
    check_true("**前提**：第一個 intent 的 read_sync_state 確實失敗",
               "read_sync_state 失敗" in r.stdout, r.stdout)
    check("bash -e 下續跑：第二個 intent 有跑 map", len(r.of("map", qual="260899-b")), 1)
    check("bash -e 下續跑：第三個 intent 有跑 map", len(r.of("map", qual="260899-c")), 1)
    check("bash -e 下續跑：第三個 intent 有讀看板",
          len(r.of("board", "read_issue_state", qual="31")), 1)
    check_true("bash -e 下報告仍然產出", "AI-DLC 對帳報告" in r.report, r.report[:200])
    ns = r.of("notify", "notify")
    check("bash -e 下仍有通報", len(ns), 1)
    check("錯誤紀錄指名到失敗的那個 intent", ns[0]["env"].get("AIDLC_INTENT_ID"), "260899-a")
    check("錯誤紀錄的 reason_code", ns[0]["env"].get("AIDLC_REASON_CODE"), "ExternalError")
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")


def test_registry_missing_dir_is_loud_and_not_fatal() -> None:
    """@purpose registry 指到一個不存在的目錄時要出聲並跳過，不得靜默——它是 registry 與檔案系統的落差。
    @given registry 多列一個沒有對應目錄的 dirName
    @step 跑一輪 | 該 intent 零呼叫、stdout 有警告、其餘照跑、不紅燈
    @pass 不靜默
    @story S-9
    """
    r = run_round(registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-ghost"}],
                  missing_dirs=("260899-ghost",))
    check("缺目錄者零呼叫", len(r.mentions("260899-ghost")), 0)
    check_true("缺目錄時出聲警告", "260899-ghost 目錄不存在" in r.stdout, r.stdout)
    check("其餘 intent 照跑", len(r.of("map", qual="260899-alpha")), 1)
    check("缺目錄不算失敗", r.rc, 0)


def test_registry_drives_selection() -> None:
    """@purpose 選取一律走 registry：檔案系統上存在但未註冊的 record 永不被碰（[ad:ADR-A3] 的 fixture 隔離）。
    @given 檔案系統上有一個 record 目錄但不在 intents.json 內
    @step 跑一輪 | 任何一次呼叫都不提到它
    @pass fixture 不會變成第 N 個 intent
    @story S-10
    """
    r = run_round(extra_dirs=("260899-fixture-not-registered",))
    check("未註冊的 record 完全不被碰", len(r.mentions("260899-fixture-not-registered")), 0)


# ==========================================================================
# [US:S-7 AC 5]／R-7.3／SEC
# ==========================================================================

def test_us_s7_ac5_successful_backfill_is_not_red() -> None:
    """@purpose [US:S-7 AC 5]：**補平成功不通報、不紅燈**。紅燈只留給真正的失敗——補平是本單元的工作成果，把它當成失敗會讓每天都有一支紅色的 workflow，紅燈因此失去意義。
    @given 兩個 intent 都有落差且都補平成功
    @step 跑一輪 | **前提**：backfilled_count 為 2（補平真的發生了）
    @step 檢視結束狀態 | exit 0
    @step 檢視通報 | 一則都沒有（只有迴圈後的 resolve_if_open）
    @pass 補平是成果不是事故
    @story S-7
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"last_status": "Ready", "last_written_status": "Ready"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Ready"}},
        "map": map_out("In progress", "v", "mapped"),
    }
    r = run_round(plan=plan, registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"}])
    check_true("[US:S-7 AC 5] **前提**：補平真的發生了", r.metric("backfilled_count") == "2", r.stdout)
    check("[US:S-7 AC 5]：**不紅燈**", r.rc, 0)
    check("[US:S-7 AC 5]：**不通報**", len(r.of("notify", "notify")), 0)


def test_r7_3_trunk_sha_in_report() -> None:
    """@purpose R-7.3：本輪讀到的 trunk HEAD SHA 必須寫進對帳報告。這讓「報告依據的是哪一版 record」可被事後查核，也讓 R-7.1 被繞過時看得出來（SHA 會是 main 的）。
    @given git rev-parse 回一個可辨識的 SHA
    @step 檢視報告 | 該 SHA 逐字出現，且該列指名 trunk_ref
    @step 讓 rev-parse 失敗 | 整輪中止（缺了它整份報告無法查核）
    @pass 沒有這一欄，一份失真的報告與一份正確的報告長得一模一樣
    @story S-9
    """
    r = run_round(head_sha="deadbeef" * 5)
    cell = r.metric("HEAD SHA，R-7.3")
    check("R-7.3：SHA 寫進報告", cell, "`" + "deadbeef" * 5 + "`")
    check_true("R-7.3：該列指名 trunk_ref", TRUNK_REF in
               next((l for l in r.report.splitlines() if "R-7.3" in l), ""), r.report[:400])
    r2 = run_round(rev_parse_fail=True)
    check_true("R-7.3：讀不到 SHA 就中止", r2.rc != 0, r2.stdout)
    check("R-7.3：中止時零 action 呼叫", len(r2.of("map")) + len(r2.of("board")), 0)


def test_sec1_credential_never_reaches_map() -> None:
    """@purpose SEC-1：本單元是憑證從 workflow secret 進入各 action 的入口，而 U-1 是零 I/O 純函式，**不得收到它**——收到會讓 [US:S-10 AC 1] 的 fixture 驅動前提失效。
    @given step 層設有 GH_TOKEN
    @step 檢視每一次 map 呼叫看到的環境 | GH_TOKEN 與 GITHUB_TOKEN 皆不存在
    @step 檢視 board／record／notify 呼叫 | GH_TOKEN 存在（它們需要）
    @pass env -u 讓變數真的不存在，而不是存在但為空
    @story S-10
    """
    r = run_round()
    maps = r.of("map")
    check_true("SEC-1 **前提**：map 真的被呼叫了", len(maps) >= 1, r.stdout)
    for c in maps:
        check("SEC-1：map 看不到 GH_TOKEN", c["gh_token"], False)
        check("SEC-1：map 看不到 GITHUB_TOKEN", c["github_token"], False)
    boards = r.of("board")
    check_true("SEC-1：board 拿得到 GH_TOKEN（它需要）",
               bool(boards) and all(c["gh_token"] for c in boards), str(boards[:1]))
    check_true("SEC-1：record 拿得到 GH_TOKEN", all(c["gh_token"] for c in r.of("record")), "")


def test_sec2_report_holds_only_ids_and_numbers() -> None:
    """@purpose SEC-2：報告發布在公開的 job summary 上（本 repo 為 public）。約束為二元可判：報告**不得**包含各 intent 的 `Decision.traceable_row` 全文、record 內容片段、或任何 API 回應 body。聚合視圖是最容易在除錯時被順手加上「多印一點細節」的地方。
    @given map 回一個可辨識的 traceable_row 探針字串
    @step 跑一輪 | **前提**：該探針確實被 map 回傳了（否則本測試量的是空集合）
    @step 檢視報告 | 探針**不出現**
    @pass 報告只放 id 與數字
    @story S-9
    """
    r = run_round()
    maps = r.of("map")
    check_true("SEC-2 **前提**：map 真的被呼叫（探針有機會流出去）", len(maps) == 1, r.stdout)
    check_true("SEC-2 **前提**：探針字串確實是本輪的 traceable_row",
               TRACEABLE_PROBE in json.dumps(stub_defaults(), ensure_ascii=False), "")
    check("SEC-2：traceable_row 不出現在報告上", TRACEABLE_PROBE in r.report, False)


def test_report_renders_empty_lists_as_none() -> None:
    """@purpose 空清單渲染為「（無）」而非空白格——空白格看不出是「沒有」還是「壞了」（`tech-stack-decisions.md` 的承接代價段逐字要求）。
    @given 一輪完全一致、六份清單全空
    @step 檢視報告的七列清單 | 每一列的筆數為 0 且 intent 欄為「（無）」
    @pass 讀報告的人分得出「沒有」與「壞了」
    @story S-9
    """
    r = run_round()
    for name in ("awaiting_human", "parked（Parked 非空", "aborted（回讀不符已中止）",
                 "unparseable（白名單外", "undecidable（訊號不落在", "issue_status_mismatch",
                 "deferred"):
        check(f"空清單渲染：{name}", r.list_cell(name), ("0", "（無）"))


def test_resolve_if_open_runs_after_loop_with_failure_identities() -> None:
    """@purpose 迴圈結束後呼叫 C-5 `resolve_if_open` 關閉已不再成立的通報 issue（U-5 的缺口 J-2；同 U-6 的 R-6.1）。鍵以 U-5 列舉的**失敗值域**逐一構成，**不得**用 SyncState.last_reason_code——那是 ReasonCode，另一個命名空間。
    @given 一輪處理成功的 intent
    @step 檢視呼叫序 | resolve_if_open 是最後一次 action 呼叫
    @step 檢視 keys | 五個鍵，逐字為 <intent>/<五個失敗碼>；不含任何 ReasonCode 值
    @pass 缺口 J-2 真的關上，而不是在文件上看起來關上
    @story S-8
    """
    r = run_round()
    calls = r.of("notify", "resolve_if_open")
    check("迴圈之後呼叫一次", len(calls), 1)
    check("是最後一次 action 呼叫", r.seq()[-1] if r.seq() else None, "notify:resolve_if_open")
    keys = sorted(k for k in (calls[0]["env"].get("AIDLC_KEYS", "").splitlines() if calls else []) if k)
    check("鍵為 U-5 的失敗值域", keys, sorted([
        "260899-alpha/Aborted", "260899-alpha/CannotCreate", "260899-alpha/ExternalError",
        "260899-alpha/Failed", "260899-alpha/Rejected"]))
    joined = "\n".join(keys)
    for reason in ("mapped", "parked", "suppressed", "unparseable", "whitelisted", "undecidable"):
        check(f"keys 不含 ReasonCode {reason}", reason in joined, False)


# ==========================================================================
# 結構斷言（沒有行為層可以驗的三件事）
# ==========================================================================

def existing_crons() -> dict[str, list[str]]:
    """全部既有 workflow 的 cron，逐檔重新抓——**不在本檔抄第二份**。"""
    found: dict[str, list[str]] = {}
    for path in sorted(WORKFLOWS.glob("*.yml")):
        if path.name == OUTER_YML.name:
            continue
        crons = re.findall(r'^\s*-?\s*cron:\s*["\']([^"\']+)["\']',
                           path.read_text(encoding="utf-8"), re.M)
        if crons:
            found[path.name] = crons
    return found


def test_r5_cron_does_not_collide() -> None:
    """@purpose R-5：對帳排程不得與既有排程碰撞。碰撞的後果不是失敗而是**資源競爭**——三支既有排程皆為 gh-aw（含 LLM agent step），同時起跑會拉長彼此的 runner 排隊。這是**建置期**檢查（`stories.md` 全域 DoD 如此分類），沒有執行期行為可驗。
    @given 全部既有 workflow 檔
    @step 掃出既有 cron | **前提**：至少掃到三支（掃到零支代表這條斷言是空的）
    @step 比對本單元的 cron | 與每一個既有 cron 的（分, 時）皆不同，故永不同分鐘起跑
    @pass 前提斷言在此特別重要：若 glob 或 regex 壞掉，「沒有碰撞」會恆真通過
    @story S-7
    """
    existing = existing_crons()
    flat = [c for lst in existing.values() for c in lst]
    check_true("R-5 **前提**：至少掃到三支既有排程（掃到零支代表本測試是空的）",
               len(flat) >= 3, f"實得 {existing}")
    outer = outer_doc()
    on = outer.get(True) or outer.get("on")
    ours = [row["cron"] for row in (on.get("schedule") or [])]
    check_true("R-5 **前提**：本單元確實有排程", len(ours) == 1, str(ours))
    mine = tuple(ours[0].split()[:2])
    for name, crons in existing.items():
        for c in crons:
            check(f"R-5：不與 {name} 的 '{c}' 同分鐘起跑", tuple(c.split()[:2]) == mine, False)


def test_structure_triggers_and_workflow_call() -> None:
    """@purpose [ad:S-B] 的觸發設定（每日 cron ＋ workflow_dispatch）與 ADR-A10 的參數化（impl 只認 workflow_call）。
    @given 兩支 workflow
    @step 解析 YAML | 外層為 schedule ＋ workflow_dispatch；impl 只有 workflow_call
    @step 檢視 input 集合 | 九個 input ＋ 一個 secret
    @step 檢視 concurrency | 自成一組（與 U-6 不同群，[req:NFR-P3] 允許並行）、排隊不取消
    @pass 可重用性是設計的性質
    @story S-7
    """
    outer = outer_doc()
    on = outer.get(True) or outer.get("on")
    check("S-B：外層的觸發集合", sorted(on.keys()), ["schedule", "workflow_dispatch"])
    conc = outer.get("concurrency") or {}
    check("concurrency group", conc.get("group"), "aidlc-sync-reconcile-${{ github.repository }}")
    check("排隊不取消", conc.get("cancel-in-progress"), False)
    forward_conc = yaml.safe_load(
        (WORKFLOWS / "aidlc-sync-forward.yml").read_text(encoding="utf-8")).get("concurrency") or {}
    check_true("[req:NFR-P3]：與 U-6 不同群（兩者可並行）",
               conc.get("group") != forward_conc.get("group"), str(conc.get("group")))

    impl = impl_doc()
    impl_on = impl.get(True) or impl.get("on")
    check_true("ADR-A10：impl 只認 workflow_call", list(impl_on.keys()) == ["workflow_call"], str(impl_on))
    check("ADR-A10：input 集合", sorted(impl_on["workflow_call"]["inputs"].keys()),
          ["field_max_length", "project_number", "project_owner", "reconcile_batch_size",
           "reconcile_branch_prefix", "record_root", "stage_field_name", "trunk_ref",
           "whitelist"])
    check("R-7.1／R-3.3：trunk_ref 與 reconcile_batch_size 皆為必填、無預設",
          [impl_on["workflow_call"]["inputs"][k].get("required") for k in
           ("trunk_ref", "reconcile_batch_size")], [True, True])
    check_true("R-3.3：reconcile_batch_size 不得有預設值（給預設等於在此替它定案）",
               "default" not in impl_on["workflow_call"]["inputs"]["reconcile_batch_size"], "")
    check("ADR-0016 §1：單一同步 token", sorted(impl_on["workflow_call"]["secrets"].keys()),
          ["sync_token"])

    names = set()
    for path in WORKFLOWS.glob("*.yml"):
        if path.name in (OUTER_YML.name, IMPL_YML.name):
            continue
        m = re.search(r'^name:\s*(.+)$', path.read_text(encoding="utf-8"), re.M)
        if m:
            names.add(m.group(1).strip().strip('"'))
    check("[req:NFR-C2]：外層 name 不與既有重複", outer["name"] in names, False)
    check("[req:NFR-C2]：impl name 不與既有重複", impl["name"] in names, False)


def test_r7_1_checkout_pins_the_trunk_ref() -> None:
    """@purpose R-7.1：`actions/checkout` **必須明訂 ref**，不得依賴預設行為。預設會 checkout 觸發 ref（`schedule` 只在預設分支 `main` 觸發），且**不會有任何錯誤**——失真是靜默的：對帳會拿落後於 `ut` 的 record 去比看板。
    @given impl 的 checkout step
    @step 解析 YAML | with.ref 為 inputs.trunk_ref、token 為 sync_token、persist-credentials 為 true
    @step 檢視薄外層 | trunk_ref 實際傳入 `ut`
    @pass 這是本單元唯一沒有行為層可驗的正確性條件——checkout 由平台執行
    @story S-9
    """
    doc = impl_doc()
    steps = doc["jobs"]["reconcile"]["steps"]
    co = [s for s in steps if isinstance(s.get("uses"), str) and s["uses"].startswith("actions/checkout")]
    check_true("R-7.1 **前提**：impl 確實有一個 checkout step", len(co) == 1, str(steps))
    with_ = co[0].get("with") or {}
    check("R-7.1：ref 釘在 trunk_ref 上", with_.get("ref"), "${{ inputs.trunk_ref }}")
    check("U-4：checkout 用同步身分", with_.get("token"), "${{ secrets.sync_token }}")
    check("U-4：persist-credentials 必須為 true（否則 push 會認證失敗）",
          with_.get("persist-credentials"), True)
    outer = outer_doc()
    check("R-7.1：薄外層傳入整合主幹", outer["jobs"]["reconcile"]["with"]["trunk_ref"], TRUNK_REF)


def test_structure_impl_hardcodes_nothing() -> None:
    """@purpose [ad:ADR-A10]：Project 編號、擁有者、record 根目錄、主幹名、批次上限一律為 input，**不得寫死**在 impl 的編排腳本裡。
    @given impl 的編排腳本全文
    @step grep 正式看板編號、擁有者、主幹名 | 零命中
    @pass 抄到另一個 repo 只需改薄外層
    @story S-7
    """
    doc = impl_doc()
    run = [s for s in doc["jobs"]["reconcile"]["steps"] if s.get("id") == "reconcile"][0]["run"]
    for literal in ("opendiamonds", "projects/16"):
        check(f"編排腳本不含寫死的 {literal}", literal in run, False)
    check_true("批次上限來自 input", "AIDLC_BATCH_SIZE" in run, "")
    check_true("主幹名來自 input", "AIDLC_TRUNK_REF" in run, "")
    text = IMPL_YML.read_text(encoding="utf-8")
    check_true("project_number 是 input 不是字面", "inputs.project_number" in text, "")


STEPS = [
    # R-6 群：三條回寫路徑的欄位集合
    test_r6_4_push_rejected_is_red_and_notified,
    test_r6_1_writeback_failure_is_red_and_notified,
    test_r6_1_backfill_writeback_field_set,
    test_r6_5_repair_writeback_field_set,
    test_r6_5_repair_with_null_status_does_not_claim_a_write,
    test_r6_3_no_writeback_when_aborted,
    test_r6_3_no_writeback_when_backfill_external_error,
    test_r6_3_no_writeback_when_consistent_and_state_matches,
    test_r6_7_expected_comes_from_this_round_read_item,
    test_r6_6_at_most_one_push_per_intent,
    test_commit_and_push_branch_and_message,
    # Q1=A 的跨單元串接
    test_q1_cross_unit_last_written_status_round_trip,
    # R-1／R-2 群
    test_r2_1_two_exclusions_only,
    test_r2_3_no_third_exclusion_class,
    test_r1_1_unparseable_and_undecidable_stay_separate,
    test_us_s3_ac6_whitelisted_has_no_list,
    test_fr_j3_excluded_reason_codes_get_no_board_write,
    test_unbound_intent_is_skipped_and_not_in_denominator,
    # R-8 群
    test_r8_issue_closed_with_non_done_status_is_listed,
    test_r8_issue_closed_with_done_status_is_not_a_mismatch,
    # R-3 群
    test_r3_batch_limit_and_deferred_list,
    test_r3_batch_size_must_be_a_positive_integer,
    # R-4 群與選取
    test_r4_2_reverse_pending_fail_closed,
    test_reverse_pending_reaches_map_and_becomes_awaiting_human,
    test_r4_1_single_intent_failure_does_not_abort_round,
    test_f5_actions_bash_e_does_not_abort_the_round,
    test_registry_missing_dir_is_loud_and_not_fatal,
    test_registry_drives_selection,
    # AC／R-7.3／SEC／報告
    test_us_s7_ac5_successful_backfill_is_not_red,
    test_r7_3_trunk_sha_in_report,
    test_sec1_credential_never_reaches_map,
    test_sec2_report_holds_only_ids_and_numbers,
    test_report_renders_empty_lists_as_none,
    test_resolve_if_open_runs_after_loop_with_failure_identities,
    # 結構斷言
    test_r5_cron_does_not_collide,
    test_structure_triggers_and_workflow_call,
    test_r7_1_checkout_pins_the_trunk_ref,
    test_structure_impl_hardcodes_nothing,
]


def main() -> int:
    if not shutil.which("jq"):
        sys.stderr.write("找不到 jq。受測腳本用它解析 registry 與 SyncState。\n")
        return 2
    print(f"受測物：{IMPL_YML.relative_to(REPO_ROOT)} 的 id: reconcile（{len(SCRIPT.splitlines())} 行）")
    print(f"同步標記：{MARKER!r}（由 record.sh 推導）")
    print(f"反向 PR label：{REVERSE_LABEL!r}（由 U-6 的 impl 推導）")
    print(f"終局 Status：{DONE!r}（由 map.sh 的 R-3.3 那一列推導）\n")
    for step in STEPS:
        before = len(FAILURES)
        try:
            step()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(f"{step.__name__} 擲出例外：{exc!r}")
        status = "ok" if len(FAILURES) == before else "FAIL"
        print(f"[{status}] {step.__name__}")

    print(f"\n{len(STEPS)} tests, {CHECKS} checks, {len(FAILURES)} failures")
    if FAILURES:
        print("\n---- failures ----")
        for f in FAILURES:
            print(f"* {f}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
