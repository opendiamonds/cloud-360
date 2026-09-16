#!/usr/bin/env python3
"""stub 斷言 runner — U-6「正向同步 workflow」的編排層（離線層）。

用法：
    python3 .github/actions/aidlc-sync-forward/run-orchestration-tests.py

非零 exit 表失敗。相依：PyYAML、jq、bash。

為什麼是**行為**測試而不是文字／結構斷言
--------------------------------------
U-10a 在同一個 stage 連續兩輪被 reviewer 打回，兩次都是同一個病：拿文字斷言去抓
行為缺陷。第一次加了一個檢查、有洞；第二次修那個檢查、仍有洞。問題不在斷言寫得
不夠細，而在**種類選錯了**。

U-6 的規則絕大多數是**行為**——分流順序、R-3.0 閘門的位置、R-5.12 四種失敗各回寫
哪幾欄。這些東西「改個寫法達成同樣邏輯」的變體無窮多，文字斷言必然漏。所以本檔
把 `aidlc-sync-forward-impl.yml` 裡 `id: orchestrate` 那個 step 的 `run:` 腳本抽
出來**實際執行**，以 stub 取代五支 composite action，斷言**實際發生的呼叫序列**
與**回寫的欄位集合**。

stub 與 live 的分工（交給 gate 看的東西）
--------------------------------------
本檔（stub，離線）驗**構造得出來但 live 構造不出來**的東西：R-5.12 的四種失敗
分支、R-3.0 的排除閘門（要求「一個看板呼叫都沒有」——只有攔得住呼叫的那一層能
誠實斷言）、R-2.5 的 fail-closed、R-6.1 的鍵來源、SEC-1 的憑證不外流。
`run-live-tests.py`（live）驗**只有真實 API 答得出來**的東西：GraphQL 回應形狀、
首建路徑、R-5.4 回讀雜湊的等價性。

結構斷言（YAML 解析）在本檔只用於三件二元可判的事：concurrency group 逐字、
`cancel-in-progress: false`、`workflow_call` 的 input 集合。它們不是行為，
沒有行為層可以驗。

規格正本：
    ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
      U-6-forward-workflow/functional-design/business-rules.md        （R-1〜R-7 群）
      U-6-forward-workflow/functional-design/business-logic-model.md  （序列圖／錯誤表）
      U-6-forward-workflow/nfr-requirements/security-requirements.md  （SEC-1〜SEC-3）
"""

from __future__ import annotations

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
IMPL_YML = REPO_ROOT / ".github" / "workflows" / "aidlc-sync-forward-impl.yml"
OUTER_YML = REPO_ROOT / ".github" / "workflows" / "aidlc-sync-forward.yml"
REAL_RECORD_SH = REPO_ROOT / ".github" / "actions" / "aidlc-sync-record" / "record.sh"

# GitHub Actions 對未指定 `shell:` 的 `run:` 步驟一律用 `bash -e {0}` 啟動，而受測
# 的 impl workflow **沒有** `shell:`、也沒有 `defaults.run.shell`——所以 `-e` 是從外
# 面帶進來的，腳本內的 `set -uo pipefail` 加不掉它。本 harness 因此必須以同一組旗標
# 啟動受測腳本，否則測試環境與 CI 環境對 `rc=$?` 之後的每一條分支判定相反。
# 以 shlex 切開，讓覆寫值（AIDLC_FORWARD_BASH）也能帶旗標。
BASH = shlex.split(os.environ.get("AIDLC_FORWARD_BASH", "bash -e"))
RECORD_ROOT = "aidlc/spaces/default/intents"

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
# 受測物的取得
# ==========================================================================

def sync_marker() -> str:
    """同步標記從 U-4 的 record.sh 推導——本檔**不**再抄一份字面值。

    這是 `[aidlc-sync]` 在本 repo 的第三個使用點（U-4 定義、U-10a 的 ci.yml gate、
    U-6 的防線②），前兩次各抄一份的代價已經付過（U-10a 的 MARKER-1 就是為此而生）。
    """
    m = re.search(r'^SYNC_MARKER="([^"]+)"', REAL_RECORD_SH.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("在 record.sh 找不到 SYNC_MARKER 常數，無法推導測試輸入。")
    return m.group(1)


MARKER = sync_marker()


def impl_doc() -> dict:
    return yaml.safe_load(IMPL_YML.read_text(encoding="utf-8"))


def outer_doc() -> dict:
    return yaml.safe_load(OUTER_YML.read_text(encoding="utf-8"))


def orchestrate_script() -> str:
    doc = impl_doc()
    job = (doc.get("jobs") or {}).get("forward")
    if not isinstance(job, dict):
        raise SystemExit("aidlc-sync-forward-impl.yml 裡找不到 forward job。")
    for step in job.get("steps") or []:
        if isinstance(step, dict) and step.get("id") == "orchestrate" and isinstance(step.get("run"), str):
            return step["run"]
    raise SystemExit(
        "forward job 裡找不到 id: orchestrate 的 step。本檔靠這個 id 定位受測腳本；"
        "若 step 被改名，請同步改這裡，不要讓測試靜默地什麼都沒測。"
    )


SCRIPT = orchestrate_script()


# ==========================================================================
# 五支 composite action 的 stub
# ==========================================================================
# 受測腳本以 `bash <path>/<tool>.sh` 呼叫五支 action 的實作檔（那是 action.yml
# 自述的同一條介面：inputs → 環境變數 → *.sh → $GITHUB_OUTPUT）。stub 因此也是
# 一個 <tool>.sh，內容只轉呼一支 python——這樣「它收到什麼環境」才記得下來。
#
# 每一次呼叫都追加一筆 {tool, op, env, gh_token} 到 calls.jsonl。回應由 plan.json
# 決定，key 的解析順序為 `tool:op@限定詞` → `tool:op#序號` → `tool:op` → 內建預設。
# 限定詞讓測試指名「第 3 個 intent 的 read_sync_state」而不必數呼叫序號。

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

DEFAULT_STATE = {
    "schema_version": 1, "binding": None, "last_status": None,
    "last_field_value": None, "last_reason_code": None,
    "managed_block_hash": None, "last_synced_at": None, "pending_reverse": None,
}
DEFAULTS = {
    "map": {"status": "In progress", "field_value": "code-generation (x)",
            "reason_code": "mapped", "traceable_row": "R-3.5 in-scope-checkbox-in-progress",
            "scope_note": "skipped-in-scope: none; out-of-scope: none"},
    "record:read_sync_state": {"state_json": json.dumps(DEFAULT_STATE), "binding": ""},
    "record:write_sync_state": {"result": "written", "state_json": json.dumps(DEFAULT_STATE), "binding": ""},
    "record:write_binding": {"result": "written", "binding": env.get("AIDLC_ISSUE_NUMBER", "")},
    "record:commit_and_push": {"result": "pushed", "attempts": "1", "commit_sha": "c0ffee",
                               "reason": "", "message": ""},
    "board:create_item": {"binding": "901", "created": "true"},
    "board:write_status": {"result": "written", "actual_status": "", "expected_status": "", "message": ""},
    "board:write_field": {"result": "written", "http_status": "", "message": ""},
    "board:write_body": {"result": "written", "http_status": "", "message": ""},
    "board:read_item": {"status": "In progress", "field_value": "code-generation (x)",
                        "managed_block_hash": "hash-from-readback",
                        "issue_number": env.get("AIDLC_BINDING", ""), "issue_state": "open"},
    "block:render": {"block_text": "<!-- aidlc-sync:begin -->\nrendered\n<!-- aidlc-sync:end -->\n"},
    "notify:notify": {"result": "ok", "issue_number": "77", "action": "created",
                      "count": "1", "closed_numbers": "", "closed": "0", "message": ""},
    "notify:resolve_if_open": {"result": "ok", "closed": "0", "closed_numbers": "", "message": ""},
}

resp = None
for key in ("%s@%s" % (key_base, qual), "%s#%d" % (key_base, seq), key_base):
    if key in plan:
        resp = plan[key]
        break
resp = resp or {}
outputs = dict(DEFAULTS.get(key_base, {}))
outputs.update(resp.get("outputs", {}))

out_file = env.get("GITHUB_OUTPUT", "")
if out_file:
    with open(out_file, "a", encoding="utf-8") as fh:
        for name, value in outputs.items():
            if TOOL == "map":
                # U-1 用 name=value 單行形式（map.sh 的 emit()）。
                fh.write("%s=%s\n" % (name, str(value).replace("\n", " ")))
            else:
                # U-2／U-3／U-4／U-5 用 heredoc 形式（block_text 是多行的）。
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
"""git 的 PATH shim：只認受測腳本用到的 `-C <ws> log -1 --format=%B HEAD`。"""
import os, sys

if os.environ.get("GIT_LOG_FAIL") == "1":
    sys.stderr.write("fatal: 模擬讀不到 HEAD\n")
    sys.exit(128)
sys.stdout.write(os.environ.get("GIT_HEAD_MESSAGE", "功能(x): 一般的開發者 commit\n"))
'''


# ==========================================================================
# 一輪執行的沙箱
# ==========================================================================

class Round:
    """跑一輪受測腳本，把發生的事情蒐集起來供斷言。"""

    def __init__(self, rc: int, stdout: str, calls: list[dict]):
        self.rc = rc
        self.stdout = stdout
        self.calls = calls

    def seq(self, tools: tuple[str, ...] = ("map", "block", "board", "record", "notify")) -> list[str]:
        """呼叫序列，形如 ["record:read_sync_state", "map", "board:write_status", ...]。"""
        out = []
        for c in self.calls:
            if c["tool"] not in tools:
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


DEFAULT_REGISTRY = [{"dirName": "260899-alpha"}]


def run_round(plan: dict | None = None,
              registry: list[dict] | None = None,
              extra_dirs: tuple[str, ...] = (),
              missing_dirs: tuple[str, ...] = (),
              whitelist: str = "",
              head_message: str | None = None,
              git_log_fail: bool = False,
              pr_list_json: str = "[]",
              pr_list_fail: bool = False,
              sync_branch: str = "danniel/feat/whatever",
              bash_argv: list[str] | None = None) -> Round:
    plan = plan or {}
    registry = registry if registry is not None else DEFAULT_REGISTRY
    with tempfile.TemporaryDirectory() as td:
        ws = pathlib.Path(td) / "ws"
        bindir = pathlib.Path(td) / "bin"
        bindir.mkdir(parents=True)

        # 五支 action 的 stub
        for tool, action in (("map", "aidlc-sync-map"), ("block", "aidlc-sync-block"),
                             ("board", "aidlc-sync-board"), ("record", "aidlc-sync-record"),
                             ("notify", "aidlc-sync-notify")):
            d = ws / ".github" / "actions" / action
            d.mkdir(parents=True)
            sh = d / f"{tool}.sh"
            head = "#!/usr/bin/env bash\n"
            if tool == "record":
                # 受測腳本從這裡 sed 出同步標記。值由真實 record.sh 推導（見上）。
                head += f'SYNC_MARKER="{MARKER}"\n'
            sh.write_text(head + 'exec python3 "${BASH_SOURCE[0]}.py" "$@"\n', encoding="utf-8")
            (d / f"{tool}.sh.py").write_text(STUB_PY.replace("@TOOL@", tool), encoding="utf-8")

        # registry 與 record 目錄
        root = ws / RECORD_ROOT
        root.mkdir(parents=True)
        (root / "intents.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
        for row in registry:
            if row["dirName"] in missing_dirs:
                # registry 列了它但檔案系統上沒有——用來驗那條落差的處置。
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
            "GH_TOKEN": "ghs_stub_token",
            "AIDLC_PROJECT_OWNER": "opendiamonds",
            "AIDLC_PROJECT_NUMBER": "23",
            "AIDLC_FIELD_NAME": "AI-DLC Stage",
            "AIDLC_RECORD_ROOT": RECORD_ROOT,
            "AIDLC_WHITELIST": whitelist,
            "AIDLC_FIELD_MAX_LENGTH": "50",
            "AIDLC_SYNC_BRANCH": sync_branch,
            "STUB_CALLS": str(calls),
            "STUB_PLAN": str(plan_file),
            "GH_PR_LIST_JSON": pr_list_json,
            "GH_PR_LIST_FAIL": "1" if pr_list_fail else "0",
            "GIT_LOG_FAIL": "1" if git_log_fail else "0",
            "GIT_HEAD_MESSAGE": head_message if head_message is not None
                                else "功能(sync): 一般的開發者 commit\n",
        })
        # bash_argv 讓個別測試**自己釘住**啟動旗標，不受模組層 BASH 預設值影響——
        # F5 的迴歸測試靠它在「有人把預設值改回不帶 -e 的 bash」時仍然生效。
        proc = subprocess.run([*(bash_argv or BASH), "-c", SCRIPT], cwd=str(ws), env=env,
                              capture_output=True, text=True)
        recs = [json.loads(l) for l in calls.read_text(encoding="utf-8").splitlines() if l.strip()]
        return Round(proc.returncode, proc.stdout + proc.stderr, recs)


def state_of(read_state: dict) -> str:
    """把一份 SyncState 覆寫值包成 stub 的 read_sync_state 回應。"""
    base = {"schema_version": 1, "binding": None, "last_status": None,
            "last_field_value": None, "last_reason_code": None,
            "managed_block_hash": None, "last_synced_at": None, "pending_reverse": None}
    base.update(read_state)
    return json.dumps(base)


def patch_of(round_: Round, seq: int = 1) -> dict:
    """取第 seq 次 write_sync_state 收到的部分物件。"""
    calls = round_.of("record", "write_sync_state")
    if len(calls) < seq:
        return {}
    return json.loads(calls[seq - 1]["env"]["AIDLC_STATE_JSON"])


BOARD_WRITE_OPS = ("create_item", "write_status", "write_field", "write_body", "read_item")


# ==========================================================================
# 測試（有序無關；每一項獨立起一個沙箱）
# ==========================================================================

def test_r4_2_marker_skips_whole_round() -> None:
    """@purpose R-4.2 防線②：HEAD commit 訊息含同步標記時**整輪** skip——一個 action 都不呼叫、exit 0。
    @given registry 內有一個可寫的 intent；HEAD 訊息含由 record.sh 推導出的標記
    @step 跑一輪 | exit 0
    @step 檢視呼叫紀錄 | 五支 action 與 gh 全數零呼叫
    @pass 整輪 skip 且不留任何副作用
    @story S-1
    """
    r = run_round(head_message=f"雜項(aidlc-sync): 更新 x 的看板同步狀態 {MARKER}\n")
    check("R-4.2：整輪 skip 後 exit 0", r.rc, 0)
    check("R-4.2：零 action 呼叫", r.seq(), [])
    check("R-4.2：連反向 PR 查詢都沒發", len(r.of("gh")), 0)


def test_r4_2_normal_commit_proceeds() -> None:
    """@purpose R-4.2 的另一半：訊息不含標記時整輪照常執行——否則防線②會變成「永遠 skip」而無人察覺。
    @given HEAD 訊息為一般的開發者 commit
    @step 跑一輪 | 反向 PR 查詢與逐 record 迴圈都發生
    @pass 至少一次 map 呼叫
    @story S-1
    """
    r = run_round()
    check_true("R-4.2：一般 commit 會進入迴圈", len(r.of("map")) == 1, r.stdout)
    check_true("R-4.2：反向 PR 查詢發生了一次", len(r.of("gh")) == 1, r.stdout)


def test_r4_2_unreadable_message_proceeds() -> None:
    """@purpose 讀不到 HEAD 訊息時往「非同步回寫」保守判定——誤判為同步會讓整輪不處理且無人知道。
    @given git log 以非零 exit 收場
    @step 跑一輪 | 警告出現且迴圈照常進行
    @pass 有 map 呼叫且 stdout 含警告
    @story S-1
    """
    r = run_round(git_log_fail=True)
    check_true("讀不到訊息時仍進入迴圈", len(r.of("map")) == 1, r.stdout)
    check_true("讀不到訊息時出聲警告", "讀不到 HEAD commit 訊息" in r.stdout, r.stdout)


def test_r2_5_fail_closed_aborts_round() -> None:
    """@purpose R-2.5：反向 PR 查詢失敗 → 整輪中止、紅燈、通報，且**對任何 intent 都沒有看板動作**。
    @given gh pr list 以非零 exit 收場
    @step 跑一輪 | exit 非 0
    @step 檢視呼叫紀錄 | map／board／record 全數零呼叫；notify 一次且 reason_code=ExternalError
    @pass fail-closed 成立（不是 fail-open 退化為空集合）
    @story S-6
    """
    r = run_round(pr_list_fail=True)
    check_true("R-2.5：整輪中止且紅燈", r.rc != 0, r.stdout)
    check("R-2.5：零 map 呼叫", len(r.of("map")), 0)
    check("R-2.5：零 board 呼叫", len(r.of("board")), 0)
    check("R-2.5：零 record 呼叫", len(r.of("record")), 0)
    notifies = r.of("notify", "notify")
    check("R-2.5：通報一次", len(notifies), 1)
    if notifies:
        check("R-2.5：通報的 reason_code", notifies[0]["env"].get("AIDLC_REASON_CODE"), "ExternalError")


def test_r2_6_failure_not_disguised_as_suppressed() -> None:
    """@purpose R-2.6：查詢失敗**不得**偽裝成 suppressed——受管區塊寫下不存在的反向 PR 等於紀錄說謊。
    @given 同上（查詢失敗）
    @step 檢視呼叫紀錄 | 沒有任何 render／write_sync_state 帶 suppressed
    @pass 零 block 呼叫且零狀態回寫
    @story S-6
    """
    r = run_round(pr_list_fail=True)
    check("R-2.6：零 render 呼叫", len(r.of("block")), 0)
    check("R-2.6：零 write_sync_state", len(r.of("record", "write_sync_state")), 0)
    check("R-2.6：呼叫紀錄裡不出現 suppressed", len(r.mentions("suppressed")), 0)


def test_r2_1_r2_3_reverse_pending_reaches_map() -> None:
    """@purpose R-2.1〜R-2.3：一次查詢算出的 reverse_pending 逐字傳進 U-1 的 map；未被 PR 涵蓋的 intent 不在集合內（[US:S-6 AC 3] 的反例）。
    @given 一則開啟中的反向 PR 只碰 alpha 的 record 路徑
    @step 跑一輪 | 兩個 intent 各一次 map
    @step 檢視 map 收到的 AIDLC_REVERSE_PENDING | 含 alpha、不含 beta
    @pass 逐 intent 而非全域
    @story S-6
    """
    pr = json.dumps([{
        "number": 1, "state": "OPEN", "closedAt": None, "mergedAt": None,
        "files": [{"path": f"{RECORD_ROOT}/260899-alpha/aidlc-state.md"}],
    }])
    r = run_round(registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"}],
                  pr_list_json=pr)
    maps = r.of("map")
    check("R-2.3：兩個 intent 各一次 map", len(maps), 2)
    if len(maps) == 2:
        pending = maps[0]["env"].get("AIDLC_REVERSE_PENDING", "")
        check("R-2.3：reverse_pending 逐字為 alpha", pending.strip(), "260899-alpha")
        check("R-2.2：beta 的那次也拿到同一個集合（集合是整輪算一次的）",
              maps[1]["env"].get("AIDLC_REVERSE_PENDING", "").strip(), "260899-alpha")
    check("R-2.1：只查一次", len(r.of("gh")), 1)


def test_r3_0_gate_blocks_all_board_calls_unbound() -> None:
    """@purpose R-3.0（iteration 5 C-2 的修正）：whitelisted／unparseable 的 intent **一個看板呼叫都沒有**，含 create_item——閘門必須在綁定分流之前，放進寫入鏈裡首建路徑會繞過去。
    @given registry 內的 260802-default 判為 whitelisted 且無綁定（今日的真實狀態）
    @step 跑一輪 | 該 intent 的 map 有跑
    @step 檢視 board 呼叫 | create_item／write_status／write_field／write_body／read_item 全數零次
    @step 檢視 record 呼叫 | 未綁定者連狀態檔都不建（零 write_sync_state、零 write_binding）
    @pass [req:FR-J3] 的「不對其產生任何看板寫入」成立
    @story S-3
    """
    plan = {"map@260802-default": {"outputs": {
        "status": "", "field_value": "", "reason_code": "whitelisted",
        "traceable_row": "R-4.1 whitelisted (missing: stage-progress-section)",
        "scope_note": "skipped-in-scope: none; out-of-scope: none"}}}
    r = run_round(plan=plan, registry=[{"dirName": "260802-default"}], whitelist="260802-default")
    check("R-3.0：map 有跑（判定必須先算出來）", len(r.of("map")), 1)
    for op in BOARD_WRITE_OPS:
        check(f"R-3.0：零 board:{op}", len(r.of("board", op)), 0)
    check("R-3.0：未綁定者不建狀態檔", len(r.of("record", "write_sync_state")), 0)
    check("R-3.0：未綁定者不寫綁定", len(r.of("record", "write_binding")), 0)
    check("R-3.0：不推 commit", len(r.of("record", "commit_and_push")), 0)
    check("R-3.0：本輪不紅燈（這是正常判斷不是失敗）", r.rc, 0)


def test_r3_0_gate_bound_records_decision_only() -> None:
    """@purpose R-3.0 的另一支：已綁定的 whitelisted intent 僅回寫 SyncState 記錄本輪判定，仍**不做任何看板動作**。
    @given 同一個 intent 但 sync-state.json 已有 binding
    @step 跑一輪 | 零 board 呼叫
    @step 檢視 write_sync_state 的部分物件 | 只有三欄判定，不含 last_synced_at／managed_block_hash
    @pass 排除路徑不推進「受管區塊寫入時刻」（R-5.13）
    @story S-3
    """
    plan = {
        "map@260802-default": {"outputs": {
            "status": "", "field_value": "", "reason_code": "whitelisted",
            "traceable_row": "R-4.1 whitelisted", "scope_note": "n"}},
        "record:read_sync_state@260802-default": {"outputs": {
            "state_json": state_of({"binding": 55, "last_reason_code": "mapped",
                                    "last_status": "Ready"}), "binding": "55"}},
    }
    r = run_round(plan=plan, registry=[{"dirName": "260802-default"}], whitelist="260802-default")
    check("R-3.0：已綁定者仍零 board 呼叫", len(r.of("board")), 0)
    patch = patch_of(r)
    check("R-3.0：回寫的欄位集合", sorted(patch.keys()),
          ["last_field_value", "last_reason_code", "last_status"])
    check("R-3.0：記的是本輪判定", patch.get("last_reason_code"), "whitelisted")
    check("R-3.0：回寫後有推 commit", len(r.of("record", "commit_and_push")), 1)


def test_r3_1_first_creation_then_full_chain() -> None:
    """@purpose R-3.1 ＋ [US:S-1 AC 1]：無綁定者走首建，且**同一輪**繼續走完寫入鏈——AC 1 逐字要求「首次被推送、同步執行後 Status 為 Ready」。
    @given 一個 registry 內、無綁定、判定為 Ready 的新 intent
    @step 跑一輪 | 呼叫序列為 read_sync_state → map → create_item → write_binding → write_status → write_field → render → write_body → read_item → write_sync_state → commit_and_push
    @step 檢視 write_status 的 desired | 逐字為 Ready
    @pass 首建與 Status 落在同一輪
    @story S-1
    """
    plan = {"map": {"outputs": {"status": "Ready", "field_value": "intent-capture (260899-alpha)",
                                "reason_code": "mapped", "traceable_row": "R-3.6 no-in-scope-stage-touched",
                                "scope_note": "skipped-in-scope: none; out-of-scope: none"}}}
    r = run_round(plan=plan)
    check("R-3.1：呼叫序列", r.seq(), [
        "record:read_sync_state", "map", "board:create_item", "record:write_binding",
        "board:write_status", "board:write_field", "block:render", "board:write_body",
        "board:read_item", "record:write_sync_state", "record:commit_and_push",
        "notify:resolve_if_open",
    ])
    ws = r.of("board", "write_status")
    check("[US:S-1 AC 1]：desired_status 為 Ready", ws[0]["env"].get("AIDLC_DESIRED_STATUS") if ws else None, "Ready")
    check("R-3.1：首建時 expected 為空（＝期望未設值）",
          ws[0]["env"].get("AIDLC_EXPECTED_STATUS") if ws else None, "")
    wb = r.of("record", "write_binding")
    check("R-3.1：綁定編號取自 create_item 的回傳",
          wb[0]["env"].get("AIDLC_ISSUE_NUMBER") if wb else None, "901")


def test_r5_5_no_drift_no_write() -> None:
    """@purpose R-5.5／防線①：三欄與判定相同且無待送告示時，**零看板呼叫、零回寫、零 commit**。這道防線不依賴任何判斷，是正確性的保底。
    @given sync-state.json 的三欄與本輪 Decision 完全相同
    @step 跑一輪 | 只有 read_sync_state 與 map
    @pass 回寫 commit 不會引發下一輪寫入（自我排除的結構性防線）
    @story S-1
    """
    plan = {"record:read_sync_state": {"outputs": {
        "state_json": state_of({"binding": 12, "last_status": "In progress",
                                "last_field_value": "code-generation (x)",
                                "last_reason_code": "mapped",
                                "last_synced_at": "2026-09-01T00:00:00Z",
                                "managed_block_hash": "h"}), "binding": "12"}}}
    r = run_round(plan=plan)
    check("R-5.5：呼叫序列只剩讀取", r.seq(), ["record:read_sync_state", "map", "notify:resolve_if_open"])
    check("R-5.5：零 board 呼叫", len(r.of("board")), 0)
    check("R-5.5：零 commit", len(r.of("record", "commit_and_push")), 0)


def test_r5_2_drift_by_reason_code_alone() -> None:
    """@purpose R-5.2：三欄「任一不同即為有漂移」——只有 reason_code 變（Status 與欄位值都沒變）也必須進寫入鏈。只比 status 的自然實作會讓同一 Status 內的轉換靜默不寫。
    @given last_status／last_field_value 與判定相同，last_reason_code 不同
    @step 跑一輪 | 寫入鏈啟動
    @pass 有 write_status 呼叫
    @story S-5
    """
    plan = {"record:read_sync_state": {"outputs": {
        "state_json": state_of({"binding": 12, "last_status": "In progress",
                                "last_field_value": "code-generation (x)",
                                "last_reason_code": "parked"}), "binding": "12"}}}
    r = run_round(plan=plan)
    check_true("R-5.2：只有 reason_code 變也算漂移", len(r.of("board", "write_status")) == 1, r.stdout)


def test_r5_6_notice_due_is_second_write_reason() -> None:
    """@purpose R-5.6（iteration 2 Critical）：PR 被拒時 record 一個字都沒變 ⇒ 三欄比對必然判無漂移；若沒有第二個寫入理由，[US:S-6 AC 5] 的告示永遠沒有載體。
    @given 三欄與判定完全相同，但該 intent 在 reverse_rejected 內且 PR 關閉時刻晚於 last_synced_at
    @step 跑一輪 | 寫入鏈仍然啟動
    @step 檢視 render 收到的 rejection_closed_at | 逐字為該 PR 的關閉時刻
    @pass 告示有載體
    @story S-6
    """
    pr = json.dumps([{
        "number": 9, "state": "CLOSED", "closedAt": "2026-09-02T10:00:00Z", "mergedAt": None,
        "files": [{"path": f"{RECORD_ROOT}/260899-alpha/aidlc-state.md"}],
    }])
    plan = {"record:read_sync_state": {"outputs": {
        "state_json": state_of({"binding": 12, "last_status": "In progress",
                                "last_field_value": "code-generation (x)",
                                "last_reason_code": "mapped",
                                "last_synced_at": "2026-09-01T00:00:00Z"}), "binding": "12"}}}
    r = run_round(plan=plan, pr_list_json=pr)
    check_true("R-5.6：無漂移但有告示待送 → 仍進寫入鏈", len(r.of("block", "render")) == 1, r.stdout)
    rend = r.of("block", "render")
    check("R-6.2b：rejection_closed_at 逐字轉交",
          rend[0]["env"].get("AIDLC_REJECTION_CLOSED_AT") if rend else None, "2026-09-02T10:00:00Z")


def test_r5_6_notice_not_due_when_already_synced() -> None:
    """@purpose R-6.2c：告示只出現一次——PR 關閉時刻早於 last_synced_at 時不構成寫入理由。
    @given 同上但 last_synced_at 晚於 PR 關閉時刻
    @step 跑一輪 | 不進寫入鏈
    @pass 告示不重複出現
    @story S-6
    """
    pr = json.dumps([{
        "number": 9, "state": "CLOSED", "closedAt": "2026-09-02T10:00:00Z", "mergedAt": None,
        "files": [{"path": f"{RECORD_ROOT}/260899-alpha/aidlc-state.md"}],
    }])
    plan = {"record:read_sync_state": {"outputs": {
        "state_json": state_of({"binding": 12, "last_status": "In progress",
                                "last_field_value": "code-generation (x)",
                                "last_reason_code": "mapped",
                                "last_synced_at": "2026-09-03T00:00:00Z"}), "binding": "12"}}}
    r = run_round(plan=plan, pr_list_json=pr)
    check("R-6.2c：已送過就不再送", len(r.of("block", "render")), 0)


def test_merged_reverse_pr_is_not_rejected() -> None:
    """@purpose R-6.2a 的判定基準是「關閉而**未合併**」——已合併的反向 PR 不得被算成被拒，否則每一次成功的反向同步都會多送一則「未被採納」的告示。
    @given 一則已合併的反向 PR
    @step 跑一輪（三欄無漂移）| 不進寫入鏈
    @pass mergedAt 非 null 者被排除
    @story S-6
    """
    pr = json.dumps([{
        "number": 9, "state": "MERGED", "closedAt": "2026-09-02T10:00:00Z",
        "mergedAt": "2026-09-02T10:00:00Z",
        "files": [{"path": f"{RECORD_ROOT}/260899-alpha/aidlc-state.md"}],
    }])
    plan = {"record:read_sync_state": {"outputs": {
        "state_json": state_of({"binding": 12, "last_status": "In progress",
                                "last_field_value": "code-generation (x)",
                                "last_reason_code": "mapped",
                                "last_synced_at": "2026-09-01T00:00:00Z"}), "binding": "12"}}}
    r = run_round(plan=plan, pr_list_json=pr)
    check("已合併的反向 PR 不算被拒", len(r.of("block", "render")), 0)


def test_r5_7_expected_comes_from_sync_state() -> None:
    """@purpose R-5.7（Q5=A 定案）：write_status 的 expected 取自 SyncState，**不得**改取當下的 read_item——後者會讓 U-3 內部的回讀比對恆真，[req:FR-C3] 的守門變成死碼。
    @given SyncState.last_status 為 Ready，而 stub 的 read_item 會回一個不同的值（Done）
    @step 跑一輪 | write_status 收到的 expected_status 為 Ready
    @step 檢視 write_status 之前的呼叫 | 沒有任何 read_item（讀了就代表取的是當下值）
    @pass 守門的比對基準是「我們上次寫了什麼」而非「看板現在是什麼」
    @story S-3
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_field_value": "old", "last_reason_code": "mapped"}),
            "binding": "12"}},
        "board:read_item": {"outputs": {"status": "Done", "managed_block_hash": "h2"}},
    }
    r = run_round(plan=plan)
    ws = r.of("board", "write_status")
    check("R-5.7：expected 來自 SyncState", ws[0]["env"].get("AIDLC_EXPECTED_STATUS") if ws else None, "Ready")
    before = r.seq()[:r.seq().index("board:write_status")] if "board:write_status" in r.seq() else []
    check("R-5.7：write_status 之前沒有 read_item", "board:read_item" in before, False)


def test_r5_10a_null_status_skips_write_status_only() -> None:
    """@purpose R-5.10 (a)：status 為 null（parked／suppressed）時跳過 write_status，但 write_field／render／write_body／回讀／回寫**照常**——[req:FR-G3] 暫停的是 Status，不是整個 item。
    @given reason_code=suppressed、status 為空
    @step 跑一輪 | 零 write_status，其餘四步都在
    @pass 不寫的原因與時間戳有載體（[US-OQ-3]）
    @story S-6
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "mapped"}), "binding": "12"}},
        "map": {"outputs": {"status": "", "field_value": "frozen: code-generation (x)",
                            "reason_code": "suppressed", "traceable_row": "R-3.2 suppressed",
                            "scope_note": "n"}},
    }
    r = run_round(plan=plan)
    check("R-5.10 (a)：零 write_status", len(r.of("board", "write_status")), 0)
    check("R-5.10 (a)：write_field 照走", len(r.of("board", "write_field")), 1)
    check("R-5.10 (a)：render 照走", len(r.of("block", "render")), 1)
    check("R-5.10 (a)：write_body 照走", len(r.of("board", "write_body")), 1)
    check("R-5.10 (a)：回讀照走", len(r.of("board", "read_item")), 1)
    rend = r.of("block", "render")
    check_true("R-5.10 (a)：decided_at 有值（[US-OQ-3] 的時間戳）",
               bool(rend and rend[0]["env"].get("AIDLC_DECIDED_AT")), str(rend))


def test_q1_undecidable_skips_write_field() -> None:
    """@purpose 人工裁決 Q1=A 對 R-5.10 (a) 字面的收窄：undecidable 跳過 write_field。U-1 對它正確地回空字串（ADR-0015 §14 禁止猜前綴），而 U-3 的 write_field 對空值無守衛、會把欄位清空——清空是沒人核可過的可觀察行為。
    @given reason_code=undecidable、field_value 為空
    @step 跑一輪 | 零 write_field；render／write_body／回讀／回寫照走
    @step 檢視回寫的部分物件 | 不含 last_field_value（欄位維持原值）
    @pass 不猜、也不清空
    @story S-2
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_field_value": "keep-me",
                                    "last_reason_code": "mapped"}), "binding": "12"}},
        "map": {"outputs": {"status": "", "field_value": "", "reason_code": "undecidable",
                            "traceable_row": "R-3.7 undecidable", "scope_note": "n"}},
    }
    r = run_round(plan=plan)
    check("Q1=A：零 write_field", len(r.of("board", "write_field")), 0)
    check("Q1=A：其餘照走（render）", len(r.of("block", "render")), 1)
    check("Q1=A：其餘照走（write_body）", len(r.of("board", "write_body")), 1)
    patch = patch_of(r)
    check("Q1=A：last_field_value 不回寫（維持原值）", "last_field_value" in patch, False)


def test_r5_12_a_write_status_aborted_writes_nothing() -> None:
    """@purpose R-5.12 第一種：write_status 回 Aborted ⇒ 看板一個字都沒動 ⇒ **完全不回寫**、鏈中止；通報 Aborted 但不紅燈（錯誤表）。
    @given 已綁定 intent，write_status 回 aborted
    @step 跑一輪 | 零 write_field／render／write_body／read_item／write_sync_state／commit_and_push
    @step 檢視通報 | reason_code=Aborted
    @pass 此時回寫任何欄位都會是謊
    @story S-3
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "parked"}), "binding": "12"}},
        "board:write_status": {"outputs": {"result": "aborted", "actual_status": "Done",
                                           "message": "write_status：回讀不符"}},
    }
    r = run_round(plan=plan)
    check("R-5.12-a：鏈中止（零 write_field）", len(r.of("board", "write_field")), 0)
    check("R-5.12-a：零 render", len(r.of("block", "render")), 0)
    check("R-5.12-a：零 write_body", len(r.of("board", "write_body")), 0)
    check("R-5.12-a：零回讀", len(r.of("board", "read_item")), 0)
    check("R-5.12-a：**完全不回寫**", len(r.of("record", "write_sync_state")), 0)
    check("R-5.12-a：零 commit", len(r.of("record", "commit_and_push")), 0)
    ns = r.of("notify", "notify")
    check("R-5.12-a：通報 Aborted", ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "Aborted")
    check("R-5.12-a：Aborted 不紅燈（錯誤表）", r.rc, 0)


def test_r5_7a_first_write_retries_once_with_board_default() -> None:
    """@purpose R-5.7a：**首寫**（expected 為空＝機制從未寫入）撞到看板自動化給的預設 Status 而 Aborted 時，以回讀到的 actual 為 expected **重試一次**，鏈照常走完。Project #16 實測：item 加入即為 Backlog，沒有這條 260816-production-path-check 首建後每輪 Aborted、永遠寫不進第一筆 Status。
    @given 無綁定的新 intent（首建）；write_status 第一次回 aborted、actual=Backlog，第二次回 written
    @step 跑一輪 | write_status 恰兩次：第一次 expected=''、第二次 expected=Backlog
    @step 檢視鏈 | write_field／render／write_body／read_item／write_sync_state 照走，零 Aborted 通報
    @pass 首寫不再被看板預設值卡死，且例外只用掉一次重試
    @story S-1
    """
    plan = {
        "map": {"outputs": {"status": "Ready", "field_value": "intent-capture (260899-alpha)",
                            "reason_code": "mapped", "traceable_row": "R-3.6 no-in-scope-stage-touched",
                            "scope_note": "skipped-in-scope: none; out-of-scope: none"}},
        "board:write_status#1": {"outputs": {"result": "aborted", "actual_status": "Backlog",
                                             "expected_status": "", "message": "write_status：回讀不符"}},
        "board:write_status#2": {"outputs": {"result": "written", "actual_status": "Backlog",
                                             "expected_status": "Backlog", "message": ""}},
    }
    r = run_round(plan=plan)
    ws = r.of("board", "write_status")
    check("R-5.7a：write_status 恰兩次", len(ws), 2)
    check("R-5.7a：第一次 expected 為空（首寫）", ws[0]["env"].get("AIDLC_EXPECTED_STATUS") if ws else None, "")
    check("R-5.7a：第二次 expected 取回讀到的 actual",
          ws[1]["env"].get("AIDLC_EXPECTED_STATUS") if len(ws) > 1 else None, "Backlog")
    check("R-5.7a：兩次 desired 相同", [w["env"].get("AIDLC_DESIRED_STATUS") for w in ws], ["Ready", "Ready"])
    check("R-5.7a：鏈照常走完（write_field）", len(r.of("board", "write_field")), 1)
    check("R-5.7a：鏈照常走完（write_sync_state）", len(r.of("record", "write_sync_state")), 1)
    check("R-5.7a：零 Aborted 通報",
          len([n for n in r.of("notify", "notify") if n["env"].get("AIDLC_REASON_CODE") == "Aborted"]), 0)
    check("R-5.7a：不紅燈", r.rc, 0)


def test_r5_7a_retry_is_bounded_to_first_write() -> None:
    """@purpose R-5.7a 的邊界：例外**只**在 expected 為空且 actual 非空時成立一次。(a) 已寫過（expected 非空）的 Aborted 不重試——那正是 R-5.7 要守的人為變更；(b) 首寫但 actual 為空（item 不在板上）不重試——沒有寫入對象，重試只會再 Aborted；(c) 重試仍 Aborted 就照 R-5.12 中止，不第三次。
    @given 三個 intent 各對應上述一種情境
    @step 跑一輪 | (a) 與 (b) 各恰一次 write_status；(c) 恰兩次
    @step 檢視通報 | 三者皆 Aborted 通報一次、零回寫
    @pass 例外不會退化成「回讀比對恆真」
    @story S-3
    """
    plan = {
        "record:read_sync_state@260899-alpha": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "parked"}), "binding": "12"}},
        "board:write_status@12": {"outputs": {"result": "aborted", "actual_status": "Done",
                                              "message": "回讀不符"}},
        "record:read_sync_state@260899-beta": {"outputs": {
            "state_json": state_of({"binding": 13, "last_status": None,
                                    "last_reason_code": "parked"}), "binding": "13"}},
        "board:write_status@13": {"outputs": {"result": "aborted", "actual_status": "",
                                              "message": "不在板上"}},
        "record:read_sync_state@260899-gamma": {"outputs": {
            "state_json": state_of({"binding": 14, "last_status": None,
                                    "last_reason_code": "parked"}), "binding": "14"}},
        "board:write_status@14": {"outputs": {"result": "aborted", "actual_status": "Backlog",
                                              "message": "回讀不符"}},
    }
    r = run_round(plan=plan, registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"},
                                       {"dirName": "260899-gamma"}])
    by = {}
    for w in r.of("board", "write_status"):
        by.setdefault(w["qual"], []).append(w["env"].get("AIDLC_EXPECTED_STATUS"))
    check("(a) 已寫過者 Aborted 不重試", by.get("12"), ["Ready"])
    check("(b) 首寫但 item 不在板上不重試", by.get("13"), [""])
    check("(c) 首寫重試一次、仍 Aborted 不第三次", by.get("14"), ["", "Backlog"])
    ns = [n for n in r.of("notify", "notify") if n["env"].get("AIDLC_REASON_CODE") == "Aborted"]
    check("三者皆通報 Aborted 一次", len(ns), 3)
    check("零回寫", len(r.of("record", "write_sync_state")), 0)
    check("Aborted 不紅燈", r.rc, 0)


def test_r5_12_e_skipped_write_status_does_not_claim_last_status() -> None:
    """@purpose R-5.10 (a) 跳過 write_status 時，**last_written_status 不得被回寫**（看板 Status 一個字都沒動，回寫就是宣稱一次沒發生的寫入）；但 **last_status 照常回寫**——它記的是「這一輪的判定」，null 也是判定，不寫它 R-5.2 的比對永遠不回零、每輪重跑整條寫入鏈（reviewer iteration 2 Critical）。
    @given 已綁定 intent，判定為 suppressed（status 為 null，走 R-5.10 (a)）
    @step 跑一輪 | 零 write_status；render／write_body／read_item 照走
    @step 檢視回寫的部分物件 | **不含 last_written_status**，但**含 last_status**
    @pass 沒有這條，round-2 判定回 mapped 時 write_status 會拿到 expected='' 而看板仍是舊值，必然 Aborted，[US:S-6 AC 5] 的告示因此送不出去
    @story S-6
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "mapped"}), "binding": "12"}},
        "map": {"outputs": {"status": "", "field_value": "frozen: x",
                            "reason_code": "suppressed", "traceable_row": "R-3.1",
                            "scope_note": ""}},
    }
    r = run_round(plan=plan)
    check("R-5.12-e：零 write_status（R-5.10 (a)）", len(r.of("board", "write_status")), 0)
    ws = r.of("record", "write_sync_state")
    check("R-5.12-e：有回寫一次", len(ws), 1)
    patch = json.loads(ws[0]["env"]["AIDLC_STATE_JSON"]) if ws else {}
    check_true("R-5.12-e：回寫的物件**不含 last_written_status**",
               "last_written_status" not in patch,
               f"實得的 patch 鍵：{sorted(patch)}——write_status 沒跑，這一欄不該出現")
    # 收斂那一半：last_status 記的是**判定**，null 也是判定。不寫它，下一輪
    # R-5.2 拿舊的真實值去比恆為 null 的 dec_status，比對永遠不回零 ⇒ 每輪重跑
    # 整條寫入鏈；而 block.sh 在 status 為空時嵌入當輪新的 decided_at，雜湊也
    # 每輪不同 ⇒ 每次外部 push 都產生一個真實 commit。
    check_true("R-5.12-e：**含 last_status 且為 null**（判定，收斂所需）",
               "last_status" in patch and patch["last_status"] is None,
               f"實得的 patch：{patch}——判定為 null 也要記，否則比對不收斂")
    check("R-5.12-e：last_reason_code 仍照寫", patch.get("last_reason_code"), "suppressed")


def test_last_written_status_falls_back_for_legacy_state() -> None:
    """@purpose 舊狀態檔沒有 last_written_status 這一欄時，expected 必須回退到 last_status——而不是變成空字串。
    @given 狀態檔只有 last_status=Ready（本欄引入之前寫下的形狀），無 last_written_status
    @step 跑一輪，判定為 In progress（有漂移）| write_status 收到 expected=Ready
    @pass 回退不是將就：本欄引入之前，last_status 記的就是「上次寫進看板的值」。
          若回退成空字串，每一個既有 intent 的第一輪都會 expected='' vs 看板實際值
          ⇒ 必然 Aborted ＋ 假通報——把一次 schema 演進變成全面誤報。
    @story S-3
    """
    legacy = {"binding": 12, "last_status": "Ready", "last_field_value": "v1",
              "last_reason_code": "mapped", "last_synced_at": "2026-09-01T00:00:00Z",
              "managed_block_hash": "h1"}
    assert "last_written_status" not in legacy
    r = run_round(plan={
        "record:read_sync_state": {"outputs": {"state_json": state_of(legacy), "binding": "12"}},
        "map": {"outputs": {"status": "In progress", "field_value": "v2",
                            "reason_code": "mapped", "traceable_row": "R-3.2",
                            "scope_note": ""}},
    })
    ws = r.of("board", "write_status")
    check("回退：write_status 被呼叫一次", len(ws), 1)
    check("回退：expected 取自 last_status（非空字串）",
          ws[0]["env"].get("AIDLC_EXPECTED_STATUS") if ws else None, "Ready")


def test_multi_round_suppressed_converges() -> None:
    """@purpose **多輪收斂**：intent 連續停在 suppressed 時，第二輪起必須判無漂移、零看板寫入、零 commit。
    @given round-1 判定 mapped/Ready 寫入成功；round-2、round-3 判定轉為 suppressed 並停在那裡
    @step 把每一輪回寫的部分物件合併進狀態檔，餵給下一輪 | round-3 相對 round-2 無漂移
    @step 檢視 round-3 | 零 write_field／write_body／read_item／write_sync_state／commit_and_push
    @pass 這條是 reviewer iteration 2 Critical 的迴歸鎖。**單輪測試結構上看不到它**——
          iteration 1 的 last_status 條件式修法讓 37 條單輪斷言全綠，而每一次外部
          push 都會產生一個真實 commit，因為 R-5.2 的比對永遠不回零。
    @story S-6
    """
    suppressed_map = {"outputs": {"status": "", "field_value": "frozen: x",
                                  "reason_code": "suppressed", "traceable_row": "R-3.1",
                                  "scope_note": ""}}
    # round-2：由 mapped/Ready 轉入 suppressed。狀態檔是 round-1 成功寫入後的樣子。
    state = {"binding": 12, "last_status": "Ready", "last_written_status": "Ready",
             "last_field_value": "v1", "last_reason_code": "mapped",
             "last_synced_at": "2026-09-01T00:00:00Z", "managed_block_hash": "h1"}
    r2 = run_round(plan={
        "record:read_sync_state": {"outputs": {"state_json": state_of(state), "binding": "12"}},
        "map": suppressed_map,
    })
    check_true("多輪：round-2 有進寫入鏈（mapped → suppressed 是真漂移）",
               len(r2.of("record", "write_sync_state")) == 1,
               "轉入 suppressed 的那一輪本來就該寫")
    state.update(patch_of(r2))          # 把 round-2 實際回寫的部分合併進狀態檔

    # round-3：判定**沒有變**，仍是 suppressed。這一輪必須完全靜默。
    r3 = run_round(plan={
        "record:read_sync_state": {"outputs": {"state_json": state_of(state), "binding": "12"}},
        "map": suppressed_map,
    })
    check("多輪：round-3 零 write_status", len(r3.of("board", "write_status")), 0)
    check("多輪：round-3 零 write_field", len(r3.of("board", "write_field")), 0)
    check("多輪：round-3 零 write_body", len(r3.of("board", "write_body")), 0)
    check("多輪：round-3 零回讀", len(r3.of("board", "read_item")), 0)
    check_true("多輪：round-3 **零狀態回寫**（R-5.5 的不寫分支）",
               len(r3.of("record", "write_sync_state")) == 0,
               f"實得 {len(r3.of('record', 'write_sync_state'))} 次——判定沒變卻還在寫，"
               "代表 R-5.2 的比對不收斂")
    check("多輪：round-3 **零 commit**", len(r3.of("record", "commit_and_push")), 0)


def test_r6_1c_resolve_failure_does_not_roll_back_board_writes() -> None:
    """@purpose R-6.1c：關閉通報 issue 失敗時只記 log 與紅燈，**不回滾**已寫入看板的內容，也不影響本輪的同步結果。
    @given 一輪正常寫入成功，迴圈後的 resolve_if_open 失敗
    @step 跑一輪 | 看板寫入與狀態回寫都已發生且未被撤銷
    @step 檢視 resolve 之後 | 沒有任何補償性的看板呼叫
    @pass 這條規則先前零覆蓋（reviewer iteration 1 Major）——「不回滾」是承諾，不是自然成立的事
    @story S-8
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "parked"}), "binding": "12"}},
        "notify:resolve_if_open": {"exit": 1, "outputs": {"result": "failed"}},
    }
    r = run_round(plan=plan)
    check("R-6.1c：write_status 有發生", len(r.of("board", "write_status")), 1)
    check("R-6.1c：狀態檔有回寫", len(r.of("record", "write_sync_state")), 1)
    check("R-6.1c：resolve 有被呼叫", len(r.of("notify", "resolve_if_open")), 1)
    # **前提斷言**：確認 resolve 這一輪真的失敗了。少了這一條，若計畫的鍵名寫錯
    # （stub 只認 "exit"，寫成 "rc" 會被靜默忽略），resolve 會成功，而下面每一條
    # 「沒有回滾」的斷言都會**恆真通過**——測試看起來綠，實際什麼都沒測到。
    # reviewer iteration 2 Major 抓到的正是這個形狀。
    check_true("R-6.1c：**前提成立**——resolve 這一輪確實失敗（紅燈）", r.rc != 0,
               f"整輪 rc={r.rc}，代表 resolve 沒有失敗，本測試的其餘斷言全部是空的")
    calls = r.calls
    idx = next((i for i, c in enumerate(calls)
                if c["tool"] == "notify" and c.get("op") == "resolve_if_open"), None)
    check_true("R-6.1c：resolve 之後沒有任何看板呼叫（無回滾）",
               idx is not None and all(c["tool"] != "board" for c in calls[idx + 1:]),
               f"resolve 之後的呼叫：{[c['tool'] for c in calls[idx + 1:]] if idx is not None else 'resolve 未被呼叫'}")


def test_r5_12_b_write_field_failed_keeps_field_value() -> None:
    """@purpose R-5.12 第二種：write_field 回 Failed ⇒ **不連坐**（[US:S-5 AC 2]），續走其餘步驟；回寫四欄，last_field_value 維持原值。
    @given write_field 回 failed
    @step 跑一輪 | render／write_body／read_item 照走
    @step 檢視回寫的部分物件 | 恰為 last_status／last_written_status／last_reason_code／last_synced_at／managed_block_hash
    @pass 欄位失敗不連坐 Status，也不在狀態檔上宣稱一個沒發生的寫入
    @story S-5
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_field_value": "old-value",
                                    "last_reason_code": "parked"}), "binding": "12"}},
        "board:write_field": {"outputs": {"result": "failed", "message": "欄位型別不符"}},
    }
    r = run_round(plan=plan)
    check("R-5.12-b：不連坐，續走 render", len(r.of("block", "render")), 1)
    check("R-5.12-b：回寫的欄位集合", sorted(patch_of(r).keys()),
          ["last_reason_code", "last_status", "last_synced_at",
           "last_written_status", "managed_block_hash"])
    ns = r.of("notify", "notify")
    check("R-5.12-b：通報 Failed", ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "Failed")
    check("R-5.12-b：Failed 不紅燈", r.rc, 0)


def test_r5_12_c_write_body_failed_keeps_hash_and_synced_at() -> None:
    """@purpose R-5.12 第三種（iteration 6 的 C-6.1／C-6.2）：write_body 回 Failed ⇒ 受管區塊未被寫入 ⇒ managed_block_hash **與 last_synced_at** 皆維持原值。前者留舊雜湊是正確的；後者若前進，告示那一輪未送達卻讓 R-6.2c 次輪不再成立，[US:S-6 AC 5] 永久靜默。
    @given write_body 回 failed
    @step 跑一輪 | 不再回讀（區塊沒寫成功，回讀沒有意義）
    @step 檢視回寫的部分物件 | 恰為三欄，不含 managed_block_hash 與 last_synced_at
    @pass 兩個後果相反的失敗沒有被壓成同一種
    @story S-6
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "parked",
                                    "last_synced_at": "2026-09-01T00:00:00Z",
                                    "managed_block_hash": "old-hash"}), "binding": "12"}},
        "board:write_body": {"outputs": {"result": "failed", "message": "標記損壞"}},
    }
    r = run_round(plan=plan)
    check("R-5.12-c：不回讀", len(r.of("board", "read_item")), 0)
    check("R-5.12-c：回寫的欄位集合", sorted(patch_of(r).keys()),
          ["last_field_value", "last_reason_code", "last_status",
           "last_written_status"])
    ns = r.of("notify", "notify")
    check("R-5.12-c：通報 Failed", ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "Failed")


def test_r5_12_d_readback_external_error_writes_nothing() -> None:
    """@purpose R-5.12 第四種：R-5.4 的回讀拋 ExternalError ⇒ 受管區塊**已經寫成功**、只是算不出雜湊 ⇒ **完全不回寫**，讓 U-7 的 R-6.5（看板 == record 而 SyncState ≠ 兩者）成立。回寫三欄會讓 R-6.5 不觸發、R-6.8 不可達，U-8 便每天開一則無人為變更的反向 PR。
    @given read_item 以非零 exit 收場
    @step 跑一輪 | 零 write_sync_state、零 commit、紅燈
    @step 檢視通報 | reason_code=ExternalError
    @pass 與第三種（write_body Failed）明確分開
    @story S-8
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "parked"}), "binding": "12"}},
        "board:read_item": {"exit": 1, "outputs": {"result": "external_error",
                                                   "message": "GraphQL 502"}},
    }
    r = run_round(plan=plan)
    check("R-5.12-d：**完全不回寫**", len(r.of("record", "write_sync_state")), 0)
    check("R-5.12-d：零 commit", len(r.of("record", "commit_and_push")), 0)
    check_true("R-5.12-d：紅燈", r.rc != 0, r.stdout)
    ns = r.of("notify", "notify")
    check("R-5.12-d：通報 ExternalError",
          ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "ExternalError")


def test_r5_4_hash_comes_from_readback_not_render() -> None:
    """@purpose R-5.4（ADR-0015 §10）：managed_block_hash 必須取自**寫入後的 read_item**，不得對 render 的輸出自己算。等價性由「與 U-8 走同一條 read_item → parse → content_hash」構造保證；算錯的後果是 U-8 在沒有任何人為變更下每天為每個 intent 開一則反向 PR。
    @given read_item 回一個可辨識的雜湊值
    @step 跑一輪 | 回寫的 managed_block_hash 逐字等於該值
    @step 檢視 block 的呼叫 | 只有 render，沒有 hash（自己算就是第二條路徑）
    @pass 雜湊來源唯一
    @story S-6
    """
    plan = {
        "record:read_sync_state": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "parked"}), "binding": "12"}},
        "board:read_item": {"outputs": {"managed_block_hash": "sha256-from-readback"}},
    }
    r = run_round(plan=plan)
    check("R-5.4：雜湊取自回讀", patch_of(r).get("managed_block_hash"), "sha256-from-readback")
    check("R-5.4：本單元不呼叫 block 的 hash", len(r.of("block", "hash")), 0)
    check("R-5.4：回讀發生在 write_body 之後",
          r.seq().index("board:read_item") > r.seq().index("board:write_body"), True)


def test_r6_1_resolve_keys_are_failure_identities() -> None:
    """@purpose R-6.1b／R-6.1d：待關閉鍵以 U-5 的**失敗值域**逐一構成，**不得**用 SyncState.last_reason_code——那是 ReasonCode（mapped／parked／…）另一個命名空間，且只在寫入成功時才被寫，失敗那一輪根本不會留下記錄。
    @given 一輪處理成功的 intent
    @step 檢視 resolve_if_open 的 keys | 五個鍵，逐字為 <intent>/<五個失敗碼>
    @step 檢查 keys 內不出現任何 ReasonCode 值
    @pass 缺口 J-2 真的關上，而不是在文件上看起來關上
    @story S-8
    """
    r = run_round()
    calls = r.of("notify", "resolve_if_open")
    check("R-6.1a：迴圈之後呼叫一次", len(calls), 1)
    keys = sorted(k for k in (calls[0]["env"].get("AIDLC_KEYS", "").splitlines() if calls else []) if k)
    check("R-6.1b：五個失敗值域各一個鍵", keys, sorted([
        "260899-alpha/Aborted", "260899-alpha/CannotCreate", "260899-alpha/ExternalError",
        "260899-alpha/Failed", "260899-alpha/Rejected"]))
    joined = "\n".join(keys)
    for reason in ("mapped", "parked", "suppressed", "unparseable", "whitelisted", "undecidable"):
        check(f"R-6.1d：keys 不含 ReasonCode {reason}", reason in joined, False)


def test_r6_1_failed_intent_excluded_from_resolve() -> None:
    """@purpose R-6.1b 的「處理成功」是有內容的判準：本輪失敗的 intent 不得進待關閉鍵集合，否則剛開的通報 issue 會被同一輪關掉。
    @given 兩個 intent，第一個的 write_status 回 aborted
    @step 檢視 resolve_if_open 的 keys | 只含第二個 intent
    @pass 仍失敗者的通報留著
    @story S-8
    """
    plan = {
        "record:read_sync_state@260899-alpha": {"outputs": {
            "state_json": state_of({"binding": 12, "last_status": "Ready",
                                    "last_reason_code": "parked"}), "binding": "12"}},
        "board:write_status@12": {"outputs": {"result": "aborted", "actual_status": "Done",
                                              "message": "回讀不符"}},
    }
    r = run_round(plan=plan, registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"}])
    calls = r.of("notify", "resolve_if_open")
    keys = [k for k in (calls[0]["env"].get("AIDLC_KEYS", "").splitlines() if calls else []) if k]
    check("R-6.1b：失敗的 intent 不進鍵集合",
          any(k.startswith("260899-alpha/") for k in keys), False)
    check_true("R-6.1b：成功的 intent 有進鍵集合",
               any(k.startswith("260899-beta/") for k in keys), str(keys))


def test_r3_3_registry_drives_selection() -> None:
    """@purpose R-3.3：**不得依事件 diff 推導要處理哪些 record**。選取一律走 registry——fixture record 不註冊進去，因此永不被選中（[ad:ADR-A3] 的 fixture 隔離在事件路徑上的保護）。
    @given 檔案系統上有一個 record 目錄但不在 intents.json 內
    @step 跑一輪 | 任何一次呼叫都不提到它
    @pass fixture 不會變成第 N 個 intent
    @story S-10
    """
    r = run_round(extra_dirs=("260899-fixture-not-registered",))
    check("R-3.3：未註冊的 record 完全不被碰",
          len(r.mentions("260899-fixture-not-registered")), 0)


def test_single_intent_failure_does_not_abort_round() -> None:
    """@purpose 錯誤表：**單一 intent 的 ExternalError 不中止整輪**——計入報告後續跑 ＋ 通報 ＋ 紅燈。整輪中止只保留給 reverse_pending 這種全輪共用的前提。
    @given 兩個 intent，第一個的 read_sync_state 以非零 exit 收場
    @step 跑一輪 | 第二個 intent 照常被處理
    @step 檢視結束狀態 | 紅燈
    @pass 影響範圍判斷，不是強度判斷
    @story S-8
    """
    plan = {"record:read_sync_state@260899-alpha": {"exit": 1}}
    r = run_round(plan=plan, registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"}])
    check("續跑：第二個 intent 有跑 map", len(r.of("map", qual="260899-beta")), 1)
    check_true("ExternalError 紅燈", r.rc != 0, r.stdout)
    ns = r.of("notify", "notify")
    check("ExternalError 有通報（錯誤表原本漏寫的那一列）", len(ns), 1)


def test_f5_actions_bash_e_does_not_abort_the_round() -> None:
    """@purpose F5 迴歸：GitHub Actions 對未指定 `shell:` 的 `run:` 用 `bash -e {0}`，而 `set -uo pipefail` 關不掉已生效的 `-e`。本檔在此**自己釘住 `bash -e`**（不依賴模組層 BASH 預設值），驗證 `set +e` 真的在 rc 判讀之前生效——沒有它，第一個 intent 的外部錯誤會殺掉整個 step，其餘 intent 一個都不會被處理，而錯誤表的「單一 intent 的 ExternalError 不中止整輪」在真實 runner 上不成立。
    @given 明確以 `bash -e` 啟動受測腳本；兩個 intent，第一個的 read_sync_state 以非零 exit 收場
    @step 跑一輪 | **前提**：該失敗確實發生（stdout 有 read_sync_state 失敗）
    @step 檢視第二個 intent | 一路跑完 map → write_status → write_field → write_body → commit_and_push——證明控制流越過了 `rc=$?`
    @step 檢視通報 | 恰一則 ExternalError，且掛在第一個 intent 上（錯誤紀錄指名到 intent）
    @step 檢視結束狀態 | 紅燈（不中止整輪 ≠ 把失敗吞掉）
    @pass 行為斷言，不比對 `set +e` 字面——有 `set +e` 但位置放在 rc 判讀之後一樣會紅
    @story S-8
    """
    plan = {"record:read_sync_state@260899-alpha": {"exit": 1},
            "record:read_sync_state@260899-beta": {"outputs": {
                "state_json": state_of({"binding": 21, "last_status": "code-generation",
                                        "last_reason_code": "mapped"}), "binding": "21"}}}
    r = run_round(plan=plan,
                  registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-beta"}],
                  bash_argv=["bash", "-e"])
    check_true("**前提**：確實以 -e 啟動仍走完整輪（不是 shell 一開始就死）",
               r.stdout.strip() != "", "受測腳本沒有任何輸出——errexit 可能在第一個非零就殺掉了 step")
    check_true("**前提**：第一個 intent 的 read_sync_state 確實失敗",
               "read_sync_state 失敗" in r.stdout, r.stdout)
    check("bash -e 下續跑：第二個 intent 有跑 map", len(r.of("map", qual="260899-beta")), 1)
    check("bash -e 下續跑：第二個 intent 的看板寫入照走", len(r.of("board", "write_status", qual="21")), 1)
    check("bash -e 下續跑：第二個 intent 一路走到回寫推送",
          len(r.of("record", "commit_and_push", qual="260899-beta")), 1)
    ns = r.of("notify", "notify")
    check("bash -e 下仍有通報", len(ns), 1)
    check("錯誤紀錄指名到失敗的那個 intent", ns[0]["env"].get("AIDLC_INTENT_ID"), "260899-alpha")
    check("錯誤紀錄的 reason_code", ns[0]["env"].get("AIDLC_REASON_CODE"), "ExternalError")
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")


def test_sec1_credential_never_reaches_pure_actions() -> None:
    """@purpose SEC-1：本單元是憑證從 workflow secret 進入各 action 的唯一入口，而 U-1／U-2 是零 I/O 純函式，**不得收到它**——收到會讓 [US:S-10 AC 1] 的 fixture 驅動前提失效。
    @given step 層設有 GH_TOKEN
    @step 檢視每一次 map／render 呼叫看到的環境 | GH_TOKEN 與 GITHUB_TOKEN 皆不存在
    @step 檢視 board／record／notify 呼叫 | GH_TOKEN 存在（它們需要）
    @pass 分發面在此收斂且可被機械驗證
    @story S-10
    """
    plan = {"record:read_sync_state": {"outputs": {
        "state_json": state_of({"binding": 12, "last_status": "x", "last_reason_code": "y"}),
        "binding": "12"}}}
    r = run_round(plan=plan)
    for c in r.of("map") + r.of("block"):
        check(f"SEC-1：{c['tool']} 看不到 GH_TOKEN", c["gh_token"], False)
        check(f"SEC-1：{c['tool']} 看不到 GITHUB_TOKEN", c["github_token"], False)
    board_calls = r.of("board")
    check_true("SEC-1：board 拿得到 GH_TOKEN（它需要）",
               bool(board_calls) and all(c["gh_token"] for c in board_calls), str(board_calls[:1]))
    check_true("SEC-1：notify 拿得到 GH_TOKEN",
               all(c["gh_token"] for c in r.of("notify")), "")


def test_commit_and_push_contract() -> None:
    """@purpose U-4 的介面約束在呼叫端成立：paths 逐字只有 <record_path>/sync-state.json（R-3.2）、訊息必含同步標記（R-3.3——它就是防線②的依據）、branch 為觸發本次同步的分支（[US:S-1 AC 4]）。
    @given 一輪會回寫的執行
    @step 檢視 commit_and_push 收到的三個值
    @pass 標記字串與 record.sh 的常數同源
    @story S-1
    """
    r = run_round()
    calls = r.of("record", "commit_and_push")
    check("commit_and_push 呼叫一次", len(calls), 1)
    if calls:
        env = calls[0]["env"]
        check("R-3.2：paths 白名單", env.get("AIDLC_PATHS"),
              f"{RECORD_ROOT}/260899-alpha/sync-state.json")
        check_true("R-3.3：訊息含同步標記", MARKER in env.get("AIDLC_MESSAGE", ""),
                   env.get("AIDLC_MESSAGE", ""))
        check("[US:S-1 AC 4]：推回觸發分支", env.get("AIDLC_BRANCH"), "danniel/feat/whatever")


def test_commit_rejected_is_red_and_notified() -> None:
    """@purpose 錯誤表：Rejected（回寫被拒）→ 續跑 ＋ 通報 ＋ **紅燈**。這是 R-5.9 ② 的來源（看板已寫成功但記錄那次寫入的動作失敗），修復落點在 U-7 的 R-6.5。
    @given commit_and_push 以 exit 3 ＋ result=rejected 收場
    @step 跑一輪 | 紅燈且通報 Rejected
    @pass 不靜默
    @story S-8
    """
    plan = {"record:commit_and_push": {"exit": 3, "outputs": {
        "result": "rejected", "reason": "policy", "message": "branch 為 ut"}}}
    r = run_round(plan=plan)
    check_true("Rejected 紅燈", r.rc != 0, r.stdout)
    ns = r.of("notify", "notify")
    check("通報 Rejected", ns[0]["env"].get("AIDLC_REASON_CODE") if ns else None, "Rejected")


def test_render_context_assembly() -> None:
    """@purpose R-7 的 Context 表：三欄由本單元組裝——decided_at 為本輪當前時刻、scope_note 為 U-1 第五個 output **逐字轉交**、rejection_notice 依 R-6.2b。
    @given map 回一個可辨識的 scope_note
    @step 檢視 render 收到的三個值
    @pass 沒有任何一欄是本單元自己發明的
    @story S-2
    """
    plan = {"map": {"outputs": {"scope_note": "skipped-in-scope: a, b; out-of-scope: c"}}}
    r = run_round(plan=plan)
    rend = r.of("block", "render")
    check("Context.scope_note 逐字轉交",
          rend[0]["env"].get("AIDLC_SCOPE_NOTE") if rend else None,
          "skipped-in-scope: a, b; out-of-scope: c")
    check_true("Context.decided_at 為 ISO 8601 UTC",
               bool(rend) and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                                       rend[0]["env"].get("AIDLC_DECIDED_AT", "")) is not None,
               str(rend[:1]))
    check("未被拒時 rejection_closed_at 為空",
          rend[0]["env"].get("AIDLC_REJECTION_CLOSED_AT") if rend else None, "")


def test_write_body_receives_render_output_verbatim() -> None:
    """@purpose 受管區塊的**唯一**持久化路徑是 render → write_body：write_body 收到的文字必須逐字等於 render 的輸出（含尾端換行的格式契約），中間不得有任何加工。
    @given render 回一段多行區塊
    @step 檢視 write_body 收到的 block_text
    @pass 多行值跨過 $GITHUB_OUTPUT 的 heredoc 形式沒有被壓壞
    @story S-2
    """
    text = "<!-- aidlc-sync:begin -->\nline-1\nline-2\n<!-- aidlc-sync:end -->\n"
    plan = {"block:render": {"outputs": {"block_text": text}}}
    r = run_round(plan=plan)
    wb = r.of("board", "write_body")
    check("write_body 收到 render 的原文", wb[0]["env"].get("AIDLC_BLOCK_TEXT") if wb else None, text)


def test_registry_missing_dir_is_loud() -> None:
    """@purpose registry 指到一個不存在的目錄時要出聲並跳過，不得靜默——它是 registry 與檔案系統的落差，而 U-4 會以「呼叫端 bug」的 exit code 拒絕它。
    @given registry 多列一個沒有對應目錄的 dirName
    @step 跑一輪 | 該 intent 零呼叫、stdout 有警告、其餘 intent 照跑
    @pass 不靜默
    @story S-3
    """
    r = run_round(registry=[{"dirName": "260899-alpha"}, {"dirName": "260899-ghost"}],
                  missing_dirs=("260899-ghost",))
    check("缺目錄者零呼叫", len(r.mentions("260899-ghost")), 0)
    check_true("缺目錄時出聲警告", "260899-ghost 目錄不存在" in r.stdout, r.stdout)
    check("其餘 intent 照跑", len(r.of("map", qual="260899-alpha")), 1)
    check("缺目錄不算失敗（不紅燈）", r.rc, 0)


def test_structure_concurrency_group_verbatim() -> None:
    """@purpose R-1.1／R-1.2：concurrency group 逐字，且 cancel-in-progress 為 false。這兩件事沒有行為層可以驗（它們在 job 跑起來之前就被平台消化掉了），只能結構斷言。
    @given 薄外層 workflow
    @step 解析 YAML | group 逐字相符、cancel-in-progress 為 false
    @pass push 與同分支 PR 落在同一組且排隊不取消
    @story S-1
    """
    doc = outer_doc()
    conc = doc.get("concurrency") or {}
    check("R-1.1：concurrency group 逐字", conc.get("group"),
          "aidlc-sync-event-${{ github.repository }}-"
          "${{ github.event.pull_request.head.ref || github.ref_name }}")
    check("R-1.2：cancel-in-progress 為 false", conc.get("cancel-in-progress"), False)


def test_structure_triggers_and_workflow_call() -> None:
    """@purpose [ad:S-A] 的觸發設定（push 任一分支 ＋ pull_request 三種 type）與 ADR-A10 的參數化（impl 只認 workflow_call，六個 input ＋ 一個 secret）。
    @given 兩支 workflow
    @step 解析 YAML | 觸發與 input 集合相符
    @pass 可重用性是設計的性質——沒有任何值寫死在 impl 裡
    @story S-1
    """
    outer = outer_doc()
    on = outer.get(True) or outer.get("on")
    check_true("S-A：push 觸發且不加分支過濾", "push" in on and not on["push"], str(on))
    check("S-A：pull_request 的三種 type", sorted((on.get("pull_request") or {}).get("types", [])),
          ["closed", "opened", "synchronize"])

    impl = impl_doc()
    impl_on = impl.get(True) or impl.get("on")
    check_true("ADR-A10：impl 只認 workflow_call", list(impl_on.keys()) == ["workflow_call"], str(impl_on))
    check("ADR-A10：input 集合", sorted(impl_on["workflow_call"]["inputs"].keys()),
          ["field_max_length", "project_number", "project_owner", "record_root",
           "stage_field_name", "whitelist"])
    check("ADR-0016 §1：單一同步 token", sorted(impl_on["workflow_call"]["secrets"].keys()),
          ["sync_token"])
    # NFR-C2：新 workflow 的 name 須與現有的都不同。
    names = set()
    for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        if path.name in ("aidlc-sync-forward.yml", "aidlc-sync-forward-impl.yml"):
            continue
        m = re.search(r'^name:\s*(.+)$', path.read_text(encoding="utf-8"), re.M)
        if m:
            names.add(m.group(1).strip().strip('"'))
    check("NFR-C2：外層 name 不與既有重複", outer["name"] in names, False)
    check("NFR-C2：impl name 不與既有重複", impl["name"] in names, False)


def test_structure_impl_hardcodes_nothing() -> None:
    """@purpose [F1=A]／ADR-A10：Project 編號、擁有者、record 根目錄、自訂欄位名一律為 input，**不得寫死**在 impl 裡。
    @given impl 的全文
    @step grep 正式看板編號與擁有者字面 | 零命中
    @pass 抄到另一個 repo 只需改薄外層
    @story S-1
    """
    text = IMPL_YML.read_text(encoding="utf-8")
    doc = impl_doc()
    run = [s for s in doc["jobs"]["forward"]["steps"] if s.get("id") == "orchestrate"][0]["run"]
    for literal in ("opendiamonds", "projects/16"):
        check(f"impl 的編排腳本不含寫死的 {literal}", literal in run, False)
    check_true("impl 的 project_number 是 input 不是字面",
               "inputs.project_number" in text, "")


STEPS = [
    test_r4_2_marker_skips_whole_round,
    test_r4_2_normal_commit_proceeds,
    test_r4_2_unreadable_message_proceeds,
    test_r2_5_fail_closed_aborts_round,
    test_r2_6_failure_not_disguised_as_suppressed,
    test_r2_1_r2_3_reverse_pending_reaches_map,
    test_r3_0_gate_blocks_all_board_calls_unbound,
    test_r3_0_gate_bound_records_decision_only,
    test_r3_1_first_creation_then_full_chain,
    test_r5_5_no_drift_no_write,
    test_r5_2_drift_by_reason_code_alone,
    test_r5_6_notice_due_is_second_write_reason,
    test_r5_6_notice_not_due_when_already_synced,
    test_merged_reverse_pr_is_not_rejected,
    test_r5_7_expected_comes_from_sync_state,
    test_r5_10a_null_status_skips_write_status_only,
    test_q1_undecidable_skips_write_field,
    test_r5_12_a_write_status_aborted_writes_nothing,
    test_r5_7a_first_write_retries_once_with_board_default,
    test_r5_7a_retry_is_bounded_to_first_write,
    test_r5_12_b_write_field_failed_keeps_field_value,
    test_r5_12_c_write_body_failed_keeps_hash_and_synced_at,
    test_r5_12_d_readback_external_error_writes_nothing,
    test_r5_12_e_skipped_write_status_does_not_claim_last_status,
    test_r5_4_hash_comes_from_readback_not_render,
    test_r6_1_resolve_keys_are_failure_identities,
    test_r6_1_failed_intent_excluded_from_resolve,
    test_r6_1c_resolve_failure_does_not_roll_back_board_writes,
    test_last_written_status_falls_back_for_legacy_state,
    test_multi_round_suppressed_converges,
    test_r3_3_registry_drives_selection,
    test_single_intent_failure_does_not_abort_round,
    test_f5_actions_bash_e_does_not_abort_the_round,
    test_sec1_credential_never_reaches_pure_actions,
    test_commit_and_push_contract,
    test_commit_rejected_is_red_and_notified,
    test_render_context_assembly,
    test_write_body_receives_render_output_verbatim,
    test_registry_missing_dir_is_loud,
    test_structure_concurrency_group_verbatim,
    test_structure_triggers_and_workflow_call,
    test_structure_impl_hardcodes_nothing,
]


def main() -> int:
    if not shutil.which("jq"):
        sys.stderr.write("找不到 jq。受測腳本用它解析 registry 與 SyncState。\n")
        return 2
    print(f"受測物：{IMPL_YML.relative_to(REPO_ROOT)} 的 id: orchestrate（{len(SCRIPT.splitlines())} 行）")
    print(f"同步標記：{MARKER!r}（由 record.sh 的 SYNC_MARKER 推導）\n")
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
