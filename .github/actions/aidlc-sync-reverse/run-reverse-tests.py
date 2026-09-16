#!/usr/bin/env python3
"""stub 斷言 runner — U-8「反向同步 workflow」的編排層（離線層）。

用法：
    python3 .github/actions/aidlc-sync-reverse/run-reverse-tests.py

非零 exit 表失敗。相依：PyYAML、jq、bash。**不打任何真實 API**（gh 與 git 都是
PATH shim，未預期的呼叫一律非零 exit，不會靜默落到真實網路）。**本檔不會開出任何
真實 PR**——`gh pr create` 只會走到 shim，本 repo 為 public、PR 編號是永久的，這一點
不能靠自律，靠的是 shim 對未預期子命令一律 exit 9。

為什麼是**行為**測試
------------------
本單元幾乎全是編排：雜湊比對的三種分流（不受管／未變／已變）、R-6.1 的即時查詢
抑制、PR 的內容邊界、以及 R-6.3 的**三種結局**。這些東西「改個寫法達成同樣邏輯」
的變體無窮多，文字／結構斷言必然漏。本檔把 `aidlc-sync-reverse-impl.yml` 裡
`id: reverse` 那個 step 的 `run:` 腳本抽出來**實際執行**，以 stub 取代三支 composite
action，斷言**實際發生的呼叫序列**、**每次寫入的欄位集合**、**PR 的參數**與**報告
的數字**。

U-6／U-7 在同一個 stage 累計被打回四輪的教訓，本檔逐條照做
--------------------------------------------------------
1. **每條測試都有「前提斷言」**——先確認該測試要製造的情境**真的發生了**，再斷言
   後果。U-6 的 Major #2 就是少了這一條：計畫鍵名寫成 `"rc"`（stub 只認 `"exit"`）
   被靜默忽略，其餘斷言在空前提上恆真通過，而作者還跑了突變「證明」它有效。
   **本檔的計畫鍵名一律是 `"exit"`。**
2. **每一條錯誤處理分支都有測試**——U-7 有兩條零覆蓋的錯誤分支，是 reviewer 用
   「整段拿掉仍全綠」才抓到的。本單元的 **R-6.3 有三種結局**（PR 開成／PR 開不成但
   刪分支成功／刪分支也失敗留孤兒），**三種各一條**。
3. **常數一律從來源推導**——反向 PR 的 label 取自 U-6 的 impl（[Q1=A]）、同步標記
   取自 `record.sh`、四個既有 cron 取自全部 workflow 檔。本檔一個字面都不抄第二份。
4. **突變驗證要打中「對應的那一條」**——見同目錄 code-summary 的突變表。
5. **stub 不得替受測程式作答**（reviewer 第一輪的 Critical ＋ Major #1 的共同根因）。
   兩種形狀，本檔各修過一次：
   - **stub 不看 argv**：`gh pr list` 原本無條件回一份固定 JSON，於是「拿掉
     `--label`」「`--json` 少要 `files`」「jq 少了 record_root 過濾」三個各只改一個
     token 的突變全部存活，而任何一個都足以讓 R-6.1 的防重複開 PR 整條失效。現在
     shim 照 `--label`／`--state`／`--json` 產生回應，**外加**對那一次查詢的完整
     argv 斷言——斷言的對象是**那一次呼叫的 argv**，不是 impl 的原始碼文字，因為
     後者分不出 `pr list` 與 `pr create` 兩個呼叫點。
   - **stub 的輸出滿足了本該由 impl 滿足的斷言**：`git push --delete` 的模擬錯誤訊息
     原本含分支名，於是「孤兒通報 detail 含分支名」是被 stub 自己餵的（突變 M5
     存活）。現在改成不含分支名的認證失敗。
6. **斷言不得被包含關係吞掉**。分支名構造上就含 intent id，所以「清單含 intent id
   **且**含分支名」的前半永遠不可能獨立失敗（突變 A5-4 存活）。凡是被斷言的字串構
   造上就含另一個的，本檔一律改成**逐字相等**或把表格逐列拆開比對。

結構斷言（YAML 解析）只用於四件沒有行為層可驗的事：cron 不碰撞、`workflow_call`
的 input 集合、checkout 釘 `trunk_ref`、concurrency 群組（三者都由平台在 job 跑
起來之前就消化掉了）。

規格正本：
    ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
      U-8-reverse-workflow/functional-design/business-rules.md        （R-1〜R-6 群）
      U-8-reverse-workflow/functional-design/business-logic-model.md  （序列／錯誤表）
      U-8-reverse-workflow/functional-design/domain-entities.md       （pending_reverse／D-1）
      U-8-reverse-workflow/nfr-requirements/*.md                      （P-1〜P-3、SEC）
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
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
IMPL_YML = WORKFLOWS / "aidlc-sync-reverse-impl.yml"
OUTER_YML = WORKFLOWS / "aidlc-sync-reverse.yml"
FORWARD_IMPL_YML = WORKFLOWS / "aidlc-sync-forward-impl.yml"
RECONCILE_OUTER_YML = WORKFLOWS / "aidlc-sync-reconcile.yml"
REAL_RECORD_SH = REPO_ROOT / ".github" / "actions" / "aidlc-sync-record" / "record.sh"

# GitHub Actions 對未指定 `shell:` 的 `run:` 步驟一律用 `bash -e {0}` 啟動，而受測
# 的 impl workflow **沒有** `shell:`、也沒有 `defaults.run.shell`——所以 `-e` 是從外
# 面帶進來的，腳本內的 `set -uo pipefail` 加不掉它。本 harness 因此必須以同一組旗標
# 啟動受測腳本，否則測試環境與 CI 環境對 `rc=$?` 之後的每一條分支判定相反。
# 以 shlex 切開，讓覆寫值（AIDLC_REVERSE_BASH）也能帶旗標。
BASH = shlex.split(os.environ.get("AIDLC_REVERSE_BASH", "bash -e"))
RECORD_ROOT = "aidlc/spaces/default/intents"
TRUNK_REF = "ut"
TRUNK_SHA = "0123456789abcdef0123456789abcdef01234567"
BRANCH_PREFIX = "aidlc-sync/reverse"
# 沙箱注入的 GITHUB_REPOSITORY。`gh` 的每一次寫入都必須帶 `--repo` 指到它——沒有
# `--repo` 時 gh 會回退到 cwd 的 git remote，而受測腳本的 cwd 是 harness 的暫存目錄，
# 在 CI 上則是 checkout 出來的 repo：兩者剛好都「看起來對」，所以少了它不會有症狀，
# 直到有人把這支 workflow 抄到別的地方為止。
REPO_FULL = "opendiamonds/cloud-360"
TOKEN = "ghs_stub_token_must_not_reach_any_report"
# read_item 回的 field_value 本單元**完全不讀**。拿它當 SEC 探針：它若出現在報告
# 或 PR 內文裡，代表有人「順手」把看板內容帶進了公開可讀的地方。
FIELD_PROBE = "SECRET-PROBE-field-value-must-not-be-published"

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
    """D-1 的反向 PR label（[Q1=A]）。U-6 的 impl 是它在程式中的第一個物化點。"""
    m = re.search(r'^ *REVERSE_PR_LABEL="([^"]+)"', FORWARD_IMPL_YML.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("在 U-6 的 impl 找不到 REVERSE_PR_LABEL 常數。")
    return m.group(1)


MARKER = sync_marker()
REVERSE_LABEL = reverse_pr_label()


def impl_doc() -> dict:
    return yaml.safe_load(IMPL_YML.read_text(encoding="utf-8"))


def outer_doc() -> dict:
    return yaml.safe_load(OUTER_YML.read_text(encoding="utf-8"))


def reverse_script() -> str:
    doc = impl_doc()
    job = (doc.get("jobs") or {}).get("reverse")
    if not isinstance(job, dict):
        raise SystemExit("aidlc-sync-reverse-impl.yml 裡找不到 reverse job。")
    for step in job.get("steps") or []:
        if isinstance(step, dict) and step.get("id") == "reverse" and isinstance(step.get("run"), str):
            return step["run"]
    raise SystemExit(
        "reverse job 裡找不到 id: reverse 的 step。本檔靠這個 id 定位受測腳本；"
        "若 step 被改名，請同步改這裡，不要讓測試靜默地什麼都沒測。"
    )


SCRIPT = reverse_script()


def code_only(script: str = "") -> str:
    """去掉整行註解後的腳本。

    「某個字面不得出現在腳本裡」這類斷言必須看**程式碼**，不能看註解——本檔的
    impl 有一大段註解正是在解釋「為什麼不呼叫 block.sh」，把它算成命中會逼實作
    刪掉那段說明，而那段說明正是 ADR-0015 §10 唯一寫下來的地方。
    只剝整行註解（本 impl 沒有行尾註解；行尾 `#` 剝除會誤傷字串內容）。
    """
    src = script or SCRIPT
    return "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))


CODE = code_only()


# ==========================================================================
# 三支 composite action 的 stub
# ==========================================================================
# 受測腳本以 `bash <path>/<tool>.sh` 呼叫三支 action 的實作檔（那是 action.yml
# 自述的同一條介面）。stub 因此也是一個 <tool>.sh，內容只轉呼一支 python。
#
# 每一次呼叫都追加一筆 {tool, op, qual, seq, env} 到 calls.jsonl。回應由 plan.json
# 決定，key 的解析順序為 `tool:op@限定詞` → `tool:op#序號` → `tool:op` → 內建預設。
# **計畫的 exit code 鍵名一律是 "exit"**（U-6 的 Major #2：寫成 "rc" 會被靜默忽略）。

STUB_PY = r'''#!/usr/bin/env python3
import json, os, pathlib, sys

TOOL = "@TOOL@"
env = dict(os.environ)
op = env.get("AIDLC_OPERATION", "")
calls_path = pathlib.Path(env["STUB_CALLS"])
plan = json.loads(pathlib.Path(env["STUB_PLAN"]).read_text(encoding="utf-8"))

if TOOL == "record":
    qual = pathlib.PurePosixPath(env.get("AIDLC_RECORD_PATH", "")).name
elif TOOL == "board":
    qual = env.get("AIDLC_BINDING", "")
else:
    qual = env.get("AIDLC_INTENT_ID", "")

key_base = "%s:%s" % (TOOL, op)

prior = 0
if calls_path.exists():
    for line in calls_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("tool") == TOOL and rec.get("op") == op:
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
outputs = dict(DEFAULTS.get("%s@%s" % (key_base, qual)) or DEFAULTS.get(key_base, {}))
for k, v in resp.get("outputs", {}).items():
    outputs[k] = v

out_file = env.get("GITHUB_OUTPUT", "")
if out_file:
    with open(out_file, "a", encoding="utf-8") as fh:
        for name, value in outputs.items():
            fh.write("%s<<__AIDLC_STUB_EOF__\n%s\n__AIDLC_STUB_EOF__\n" % (name, value))

sys.exit(int(resp.get("exit", 0)))
'''

# gh 的 PATH shim。只認受測腳本用到的四個子命令，其餘一律 exit 9——**這是「本檔
# 絕不開出真實 PR」的機械保證**，不是自律。
GH_STUB = r'''#!/usr/bin/env python3
import json, os, pathlib, sys

argv = sys.argv[1:]
calls = pathlib.Path(os.environ["STUB_CALLS"])
sub = " ".join(argv[:2])
with calls.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({"tool": "gh", "op": sub, "qual": "", "seq": 0,
                         "env": {}, "argv": argv,
                         "gh_token": "GH_TOKEN" in os.environ}, ensure_ascii=False) + "\n")


def arg_of(flag):
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
    return ""


if sub == "pr list":
    if os.environ.get("GH_PR_LIST_FAIL") == "1":
        sys.stderr.write("gh shim: 模擬 pr list 失敗（HTTP 502）\n")
        sys.exit(1)
    # **依 argv 產生回應**，不是無條件回一份固定 JSON。理由見本檔 R-6.1 段的說明：
    # 只回固定值時，`--label`／`--json` 兩個 token 的突變全部存活，而它們各自都足以
    # 讓 R-6.1 整條抑制鏈失效（拿掉 --label ⇒ 任何人為 PR 都會抑制；--json 少了
    # files ⇒ 抑制集合恆為空）。stub 不模擬這兩個旗標，就等於沒有人在測它們。
    data = json.loads(os.environ.get("GH_PR_LIST_JSON", "[]"))
    want_label = arg_of("--label")
    if want_label:
        data = [p for p in data
                if want_label in [l.get("name") for l in (p.get("labels") or [])]]
    want_state = (arg_of("--state") or "open").lower()
    if want_state != "all":
        data = [p for p in data if str(p.get("state", "open")).lower() == want_state]
    fields = [f for f in arg_of("--json").split(",") if f]
    if not fields:
        # 真實的 gh 少了 --json 時輸出表格而不是 JSON，下游 jq 會解析失敗。照樣模擬，
        # 讓「把 --json 整個拿掉」也落在會被抓到的改動裡。
        for p in data:
            sys.stdout.write("#%s\tOPEN\t%s\n" % (p.get("number", "?"), p.get("title", "")))
        sys.exit(0)
    sys.stdout.write(json.dumps([{k: v for k, v in p.items() if k in fields}
                                 for p in data], ensure_ascii=False))
    sys.exit(0)

if sub == "pr create":
    head = arg_of("--head")
    fail = os.environ.get("GH_PR_CREATE_FAIL", "")
    if fail == "all" or (fail and head in fail.split(",")):
        sys.stderr.write("gh shim: 模擬 pr create 失敗（GraphQL: Resource not accessible）\n")
        sys.exit(1)
    sys.stdout.write("https://github.com/opendiamonds/cloud-360/pull/999\n")
    sys.exit(0)

if sub == "label list":
    if os.environ.get("GH_LABEL_LIST_FAIL") == "1":
        sys.stderr.write("gh shim: 模擬 label list 失敗\n")
        sys.exit(1)
    sys.stdout.write(os.environ.get("GH_LABEL_LIST_JSON", "[]"))
    sys.exit(0)

if sub == "label create":
    mode = os.environ.get("GH_LABEL_CREATE_FAIL", "")
    if mode == "1":
        sys.stderr.write("gh shim: 模擬 label create 失敗（HTTP 403）\n")
        sys.exit(1)
    if mode == "exists":
        sys.stderr.write("gh: label already exists\n")
        sys.exit(1)
    sys.stdout.write("label created\n")
    sys.exit(0)

sys.stderr.write("gh shim: 未預期的呼叫 %r —— 本檔不得打到真實 API\n" % (argv,))
sys.exit(9)
'''

GIT_STUB = r'''#!/usr/bin/env python3
"""git 的 PATH shim：只認 `-C <ws> rev-parse HEAD` 與 `-C <ws> push origin --delete <b>`。"""
import json, os, pathlib, sys

argv = sys.argv[1:]
calls = pathlib.Path(os.environ["STUB_CALLS"])


def rec(op, extra=None):
    entry = {"tool": "git", "op": op, "qual": "", "seq": 0, "env": {}, "argv": argv,
             "gh_token": False}
    if extra:
        entry.update(extra)
    with calls.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


if "rev-parse" in argv:
    rec("rev-parse")
    if os.environ.get("GIT_REV_PARSE_FAIL") == "1":
        sys.stderr.write("fatal: 模擬讀不到 HEAD\n")
        sys.exit(128)
    sys.stdout.write(os.environ["GIT_HEAD_SHA"] + "\n")
    sys.exit(0)

if "push" in argv and "--delete" in argv:
    branch = argv[-1]
    rec("push --delete", {"branch": branch})
    fail = os.environ.get("GIT_PUSH_DELETE_FAIL", "")
    if fail == "all" or (fail and branch in fail.split(",")):
        sys.stderr.write(os.environ["GIT_DELETE_FAIL_MSG"] + "\n")
        sys.exit(1)
    sys.stdout.write("deleted %s\n" % branch)
    sys.exit(0)

sys.stderr.write("git shim: 未預期的呼叫 %r\n" % (argv,))
sys.exit(9)
'''

# 刪除遠端分支失敗時 stub 印的訊息。**刻意不含分支名**。
#
# 先前的版本是 `unable to delete '<branch>': remote ref does not exist`，於是 R-6.3 第
# 三種結局的「通報 detail 含分支名」那條斷言**是被 stub 自己的輸出滿足的**——impl 把
# 分支名從 detail 拿掉，測試照樣全綠（reviewer 的突變 M5）。真實的 `git push --delete`
# 認證／網路失敗不會回分支名，所以這裡改成認證失敗，讓那條斷言只能由 impl 自己的字
# 串滿足。**stub 的輸出不得替受測程式作答**——這是本檔第二次踩到同一形狀（第一次是
# 突變 M19 的 PR 內文比對）。
GIT_DELETE_FAIL_MSG = "fatal: Authentication failed for 'https://github.com/'"

# `date` 的 PATH shim。受測腳本整輪只該取一次時刻（ROUND_AT 同時是 pending_reverse
# 的 observed_at、分支名的日期、PR 內文與報告的偵測時刻）——「整輪一個值」是一條
# 不變式，而真實的 date 在同一秒內連取兩次會回同一個值，**測不出**逐 intent 重算。
# shim 每次呼叫回一個遞增的秒數並記錄呼叫，於是「取了幾次」與「值有沒有分裂」都變成
# 可斷言的事實。格式字串則以「未預期的 argv 一律 exit 9」守住（與 gh shim 同一手法）。
STUB_DATE = "2026-09-06"
STUB_ROUND_AT = f"{STUB_DATE}T00:00:00Z"
DATE_ARGV = ["-u", "+%Y-%m-%dT%H:%M:%SZ"]

DATE_STUB = r'''#!/usr/bin/env python3
import json, os, pathlib, sys

argv = sys.argv[1:]
calls = pathlib.Path(os.environ["STUB_CALLS"])
prior = 0
if calls.exists():
    for line in calls.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line).get("tool") == "date":
            prior += 1
value = "@STUB_DATE@T00:00:%02dZ" % prior
with calls.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({"tool": "date", "op": "date", "qual": "", "seq": prior + 1,
                         "env": {}, "argv": argv, "value": value,
                         "gh_token": False}, ensure_ascii=False) + "\n")

if argv != json.loads(os.environ["DATE_EXPECTED_ARGV"]):
    sys.stderr.write("date shim: 未預期的呼叫 %r —— 格式字串改了就要同步改 harness\n" % (argv,))
    sys.exit(9)

sys.stdout.write(value + "\n")
sys.exit(0)
'''


# ==========================================================================
# 一輪執行的沙箱
# ==========================================================================
# **基準情境是「已綁定、看板受管區塊的雜湊與記錄相同」**——本單元是反向偵測，
# 「沒有人動看板」才是常態（多數日子如此）。每個測試各自覆寫它要製造的偏離。

HASH_ON_RECORD = "sha256-recorded-by-forward-sync"
HASH_HUMAN_EDITED = "sha256-after-a-human-edited-the-board"

DEFAULT_STATE = {
    "schema_version": 1,
    "binding": 12,
    "last_status": "In progress",
    "last_written_status": "In progress",
    "last_field_value": "code-generation (x)",
    "last_reason_code": "mapped",
    "managed_block_hash": HASH_ON_RECORD,
    "last_synced_at": "2026-09-01T00:00:00Z",
    "pending_reverse": None,
}


def state_of(overrides: dict) -> str:
    base = dict(DEFAULT_STATE)
    base.update(overrides)
    return json.dumps(base)


def stub_defaults() -> dict:
    return {
        "record:read_sync_state": {"state_json": state_of({}), "binding": "12"},
        # 第二個 intent 的 binding 必須與第一個**不同**，否則 stub 的 `@限定詞` 對
        # board 就分不出兩者（board 的限定詞是 binding），而「只讓 X 的 read_item
        # 失敗」這種測試會靜默地把兩個都弄失敗——正是前提斷言要擋的那種空測試。
        "record:read_sync_state@260898-beta": {"state_json": state_of({"binding": 13}),
                                               "binding": "13"},
        "record:write_sync_state": {"result": "written"},
        "record:commit_and_push": {"result": "pushed", "attempts": "1",
                                   "commit_sha": "c0ffee", "reason": "", "message": ""},
        "board:read_item": {"status": "In progress", "field_value": FIELD_PROBE,
                            "managed_block_hash": HASH_ON_RECORD,
                            "issue_number": "12", "issue_state": "open", "message": ""},
        "notify:notify": {"result": "ok", "issue_number": "77", "action": "created",
                          "count": "1", "message": ""},
    }


class Round:
    def __init__(self, rc: int, stdout: str, calls: list[dict], report: str):
        self.rc = rc
        self.stdout = stdout
        self.calls = calls
        self.report = report

    def seq(self) -> list[str]:
        return ["%s:%s" % (c["tool"], c["op"]) for c in self.calls
                if c["tool"] in ("board", "record", "notify")]

    def of(self, tool: str, op: str | None = None, qual: str | None = None) -> list[dict]:
        res = []
        for c in self.calls:
            if c["tool"] != tool:
                continue
            if op is not None and c["op"] != op:
                continue
            if qual is not None and c.get("qual") != qual:
                continue
            res.append(c)
        return res

    def gh(self, sub: str) -> list[dict]:
        return [c for c in self.calls if c["tool"] == "gh" and c["op"] == sub]

    def git(self, sub: str) -> list[dict]:
        return [c for c in self.calls if c["tool"] == "git" and c["op"] == sub]

    def notifies(self, reason: str | None = None) -> list[dict]:
        out = self.of("notify", "notify")
        if reason is None:
            return out
        return [n for n in out if n["env"].get("AIDLC_REASON_CODE") == reason]

    def metric(self, name: str) -> str | None:
        for line in self.report.splitlines():
            if line.startswith("|") and name in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2:
                    return cells[-1]
        return None

    def dates(self) -> list[dict]:
        return [c for c in self.calls if c["tool"] == "date"]

    def open_reverse(self) -> set[str] | None:
        """R-6.1 的抑制集合——受測腳本自己印出來的那一行。

        `None` 代表那一行根本沒印（例如整輪在查詢之前就中止），與「印了但集合是空的」
        是兩件事，不能都當成空集合。
        """
        head = "已有開啟中反向 PR 的 intent"
        for line in self.stdout.splitlines():
            if line.startswith(head) and "：" in line:
                return {t for t in line.split("：", 1)[1].split() if t}
        return None

    def list_cell(self, name: str) -> tuple[str, str] | None:
        for line in self.report.splitlines():
            if line.startswith("|") and name in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) == 3:
                    return cells[1], cells[2]
        return None


ALPHA = "260899-alpha"
BETA = "260898-beta"
DEFAULT_REGISTRY = [{"dirName": ALPHA}]
TWO_REGISTRY = [{"dirName": ALPHA}, {"dirName": BETA}]


def pr_obj(*record_dirs: str, extra_paths: tuple[str, ...] = (),
           number: int = 501, state: str = "open",
           labels: tuple[str, ...] = (REVERSE_LABEL,)) -> dict:
    """一則 PR 的 stub 資料。

    `labels=()` 代表**人為開的 PR**（沒有反向 label）——gh shim 會照 `--label` 過濾，
    所以它只有在 impl 漏掉那個旗標時才會進到抑制集合裡。
    """
    files = [{"path": f"{RECORD_ROOT}/{d}/sync-state.json"} for d in record_dirs]
    files += [{"path": p} for p in extra_paths]
    return {"number": number, "state": state, "files": files,
            "labels": [{"name": n} for n in labels],
            "title": f"stub PR #{number}"}


def prs_json(*prs: dict) -> str:
    return json.dumps(list(prs), ensure_ascii=False)


def open_pr_json(*record_dirs: str, extra_paths: tuple[str, ...] = ()) -> str:
    """一則**掛著反向 label 的**開啟中 PR，diff 含這些 intent 的 sync-state.json。"""
    return prs_json(pr_obj(*record_dirs, extra_paths=extra_paths))


def branch_of(intent_id: str) -> str:
    """本單元為某個 intent 建的反向分支名（R-2.3）。日期由 date shim 釘死。"""
    return f"{BRANCH_PREFIX}/{intent_id}-{STUB_DATE}"


def body_rows(body: str) -> dict[str, str]:
    """PR 內文的 `| 欄 | 值 |` 表格 → dict（分隔列與非兩欄列略過）。

    逐列取出而不是整檔 `in`：`分支` 那一格的值**構造上就含 intent id**，所以
    「內文含 intent id」寫成 `ALPHA in body` 時，即使 `intent` 那一列整列被刪掉也
    仍會通過——就是 reviewer 在孤兒清單抓到的同一種包含關係吞掉斷言。
    """
    rows: dict[str, str] = {}
    for line in body.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) != 2 or set(cells[0]) <= set("- "):
            continue
        rows[cells[0]] = cells[1]
    return rows


def run_round(plan: dict | None = None,
              registry: list[dict] | None = None,
              missing_dirs: tuple[str, ...] = (),
              no_registry: bool = False,
              bad_registry: bool = False,
              trunk_ref: str = TRUNK_REF,
              head_sha: str = TRUNK_SHA,
              rev_parse_fail: bool = False,
              pr_list_json: str = "[]",
              pr_list_fail: bool = False,
              pr_create_fail: str = "",
              push_delete_fail: str = "",
              label_list_json: str = "[]",
              label_list_fail: bool = False,
              label_create_fail: str = "",
              forward_impl_body: str | None = None,
              record_sh_head: str | None = None,
              missing_tools: tuple[str, ...] = (),
              defaults: dict | None = None,
              bash_argv: list[str] | None = None) -> Round:
    plan = plan or {}
    registry = registry if registry is not None else DEFAULT_REGISTRY
    defaults = defaults if defaults is not None else stub_defaults()
    with tempfile.TemporaryDirectory() as td:
        ws = pathlib.Path(td) / "ws"
        bindir = pathlib.Path(td) / "bin"
        bindir.mkdir(parents=True)

        for tool, action in (("board", "aidlc-sync-board"),
                             ("record", "aidlc-sync-record"),
                             ("notify", "aidlc-sync-notify")):
            d = ws / ".github" / "actions" / action
            d.mkdir(parents=True)
            # `missing_tools` 讓「三支 composite action 沒跟著 checkout 進來」成為一個
            # 可製造的情境（受測腳本開頭那個存在性迴圈的唯一測試落點）。
            if tool in missing_tools:
                continue
            sh = d / f"{tool}.sh"
            head = "#!/usr/bin/env bash\n"
            if tool == "record":
                # 受測腳本從這裡 sed 出同步標記。值由真實 record.sh 推導。
                head += (record_sh_head if record_sh_head is not None
                         else f'SYNC_MARKER="{MARKER}"\n')
            sh.write_text(head + 'exec python3 "${BASH_SOURCE[0]}.py" "$@"\n', encoding="utf-8")
            (d / f"{tool}.sh.py").write_text(STUB_PY.replace("@TOOL@", tool), encoding="utf-8")

        # 受測腳本從 U-6 的 impl 推導反向 PR 的 label（D-1 的唯一物化點，[Q1=A]）。
        wf = ws / ".github" / "workflows"
        wf.mkdir(parents=True)
        if "forward" not in missing_tools:
            (wf / "aidlc-sync-forward-impl.yml").write_text(
                forward_impl_body if forward_impl_body is not None
                else f'          REVERSE_PR_LABEL="{REVERSE_LABEL}"\n', encoding="utf-8")

        root = ws / RECORD_ROOT
        root.mkdir(parents=True)
        if not no_registry:
            body = "{ not json" if bad_registry else json.dumps(registry, ensure_ascii=False)
            (root / "intents.json").write_text(body, encoding="utf-8")
        for row in registry:
            if row["dirName"] in missing_dirs:
                continue
            (root / row["dirName"]).mkdir(parents=True, exist_ok=True)

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
        (bindir / "date").write_text(DATE_STUB.replace("@STUB_DATE@", STUB_DATE),
                                     encoding="utf-8")
        for name in ("gh", "git", "date"):
            (bindir / name).chmod(0o755)

        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)
        env.update({
            "PATH": f"{bindir}:{env.get('PATH', '')}",
            "GITHUB_WORKSPACE": str(ws),
            "GITHUB_REPOSITORY": REPO_FULL,
            "GITHUB_OUTPUT": str(pathlib.Path(td) / "step_output"),
            "GITHUB_STEP_SUMMARY": str(summary),
            "GH_TOKEN": TOKEN,
            "AIDLC_PROJECT_OWNER": "opendiamonds",
            "AIDLC_PROJECT_NUMBER": "23",
            "AIDLC_FIELD_NAME": "AI-DLC Stage",
            "AIDLC_RECORD_ROOT": RECORD_ROOT,
            "AIDLC_TRUNK_REF": trunk_ref,
            "AIDLC_BRANCH_PREFIX": BRANCH_PREFIX,
            "STUB_CALLS": str(calls),
            "STUB_PLAN": str(plan_file),
            "STUB_DEFAULTS": str(defaults_file),
            "GH_PR_LIST_JSON": pr_list_json,
            "GH_PR_LIST_FAIL": "1" if pr_list_fail else "0",
            "GH_PR_CREATE_FAIL": pr_create_fail,
            "GH_LABEL_LIST_JSON": label_list_json,
            "GH_LABEL_LIST_FAIL": "1" if label_list_fail else "0",
            "GH_LABEL_CREATE_FAIL": label_create_fail,
            "GIT_HEAD_SHA": head_sha,
            "GIT_REV_PARSE_FAIL": "1" if rev_parse_fail else "0",
            "GIT_PUSH_DELETE_FAIL": push_delete_fail,
            "GIT_DELETE_FAIL_MSG": GIT_DELETE_FAIL_MSG,
            "DATE_EXPECTED_ARGV": json.dumps(DATE_ARGV),
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


def pr_arg(call: dict, flag: str) -> str:
    argv = call["argv"]
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
    return ""


def changed_board(hash_value: str = HASH_HUMAN_EDITED, status: str = "Done") -> dict:
    """讓 read_item 回一個「人改過」的看板現況。"""
    return {"outputs": {"managed_block_hash": hash_value, "status": status}}


# ==========================================================================
# R-1 群：何時開 PR
# ==========================================================================

def test_r1_2_unchanged_hash_opens_no_pr_and_writes_nothing() -> None:
    """@purpose R-1.2（防迴圈第一道防線在反向側）：受管區塊雜湊與 `sync-state.json` 記錄的相同 ⇒ **零 PR、零寫入**。機制自己寫的區塊不得被誤判為人為變更。
    @given read_item 回的 managed_block_hash 與記錄的逐字相同（基準情境）
    @step 跑一輪 | **前提**：read_item 確實被呼叫一次、且腳本確實走到雜湊比對（stdout 出現「雜湊未變」）
    @step 檢視寫入與 PR | write_sync_state 零次、commit_and_push 零次、gh pr create 零次
    @step 檢視整輪 | 不紅燈；報告的「雜湊未變」計數為 1
    @pass 這條若失效，機制每天為每個受管 intent 開一則反向 PR——ADR-A6 點名的最危險失效模式
    @story S-6
    @api n/a（workflow 編排層，無 HTTP 端點）
    """
    r = run_round()
    ri = r.of("board", "read_item")
    check_true("R-1.2 **前提**：read_item 被呼叫一次", len(ri) == 1,
               f"實得 {len(ri)} 次——沒走到看板讀取，下面全部是空的。stdout：{r.stdout}")
    check_true("R-1.2 **前提**：確實走到雜湊比對且判為未變",
               "雜湊未變" in r.stdout, r.stdout)
    check("R-1.2：零寫入", len(r.of("record", "write_sync_state")), 0)
    check("R-1.2：零推送", len(r.of("record", "commit_and_push")), 0)
    check("R-1.2：零 PR", len(r.gh("pr create")), 0)
    check("R-1.2：不紅燈", r.rc, 0)
    check("R-1.2：報告的未變計數", r.metric("受管區塊雜湊未變"), "1")


def test_r4c_parse_null_is_skipped_not_a_human_change() -> None:
    """@purpose R-4c：`parse` 回 `null`（read_item 的 managed_block_hash 為空）代表該 item 不受管 ⇒ **跳過，不視為人為變更**。把不受管的 item 當成人為變更會製造大量假 PR。
    @given 記錄有雜湊，而看板回的 managed_block_hash 為空字串
    @step 跑一輪 | **前提**：read_item 被呼叫、且回的雜湊確實是空的（stdout 出現「無可解析的受管區塊」）
    @step 檢視寫入與 PR | 零寫入、零推送、零 PR
    @step 檢視報告 | 該 intent 進「不受管」清單，不進失敗清單
    @pass 若改成「空雜湊 ≠ 記錄雜湊 ⇒ 開 PR」，每個尚未被 U-6 寫過受管區塊的 item 都會天天被開 PR，而 observed_status 記的還會是空值
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": {"outputs": {"managed_block_hash": ""}}})
    ri = r.of("board", "read_item")
    check_true("R-4c **前提**：read_item 被呼叫一次", len(ri) == 1, f"實得 {len(ri)} 次")
    check_true("R-4c **前提**：確實走到「不受管」分支",
               "無可解析的受管區塊" in r.stdout, r.stdout)
    check("R-4c：零寫入", len(r.of("record", "write_sync_state")), 0)
    check("R-4c：零 PR", len(r.gh("pr create")), 0)
    check("R-4c：不紅燈（不是錯誤）", r.rc, 0)
    check("R-4c：進「不受管」清單", r.list_cell("不受管，跳過"), ("1", ALPHA))
    # 清單與計數器是兩個獨立的累計器（`list_add L_UNMANAGED` 與 `UNMANAGED=$((…))`），
    # 只驗清單時「計數器永遠不增加」的突變存活——報告上會出現 0 個不受管卻列著一個 id。
    check("R-4c：報告的不受管計數", r.metric("無可解析的受管區塊"), "1")
    check("R-4c：不進失敗清單", r.list_cell("本輪失敗"), ("0", "（無）"))


def test_r1_3_changed_hash_writes_pending_reverse_and_opens_one_pr() -> None:
    """@purpose R-1.3 ＋ E-1：雜湊已變 ⇒ 寫 `pending_reverse` 並開一則 PR。寫入的**欄位集合恰為 pending_reverse 一個鍵**，其值為 {observed_status, observed_at} 物件。
    @given read_item 回的雜湊與記錄不同，Status 為 Done
    @step 跑一輪 | **前提**：確實偵測到人為變更（stdout 出現「雜湊已變」），且 write_sync_state 被呼叫一次
    @step 檢視 patch | 頂層鍵恰為 ["pending_reverse"]；observed_status 為看板上的值
    @step 檢視 PR | gh pr create 一次，base 為 trunk_ref、head 為反向分支、label 由 U-6 推導
    @pass patch 若多帶任何一個鍵，反向 PR 的 diff 就不只是「人改了什麼」；[req:FR-G2] 的寫入邊界靠這一條
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()})
    check_true("R-1.3 **前提**：確實偵測到人為變更", "雜湊已變" in r.stdout, r.stdout)
    wss = r.of("record", "write_sync_state")
    check_true("R-1.3 **前提**：write_sync_state 被呼叫一次", len(wss) == 1,
               f"實得 {len(wss)} 次。stdout：{r.stdout}")
    patch = patch_of(r)
    check("E-1：patch 的頂層鍵恰為 pending_reverse", sorted(patch.keys()), ["pending_reverse"])
    check("E-1：observed_status 取自看板", patch["pending_reverse"].get("observed_status"), "Done")
    check_true("E-1：observed_at 為 ISO 8601 UTC",
               bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                                 patch["pending_reverse"].get("observed_at", ""))),
               str(patch))
    prs = r.gh("pr create")
    check_true("R-1.4：恰好開一則 PR", len(prs) == 1, f"實得 {len(prs)} 則")
    check("R-1.5：PR 的 base 為 trunk_ref", pr_arg(prs[0], "--base"), TRUNK_REF)
    check("D-1：PR 掛上反向 label", pr_arg(prs[0], "--label"), REVERSE_LABEL)
    check("R-1.3：報告的 PR 計數", r.metric("本輪開出的反向 PR"), "**1**")
    check("R-1.3：成功開出 PR 不紅燈", r.rc, 0)


def test_unbound_intent_is_skipped() -> None:
    """@purpose 未綁定（尚未首建）的 intent 看板上沒有對應 item ⇒ 跳過，**不是錯誤**、不讀看板。
    @given read_sync_state 回的 binding 為空
    @step 跑一輪 | **前提**：read_sync_state 被呼叫一次
    @step 檢視後續 | read_item 零次、零寫入、零 PR、不紅燈
    @pass 未綁定者若進入 read_item，U-3 會以介面誤用失敗，整輪每天紅燈一次
    @story S-6
    @api n/a
    """
    r = run_round(plan={"record:read_sync_state": {"outputs": {"binding": ""}}})
    check_true("**前提**：read_sync_state 被呼叫一次",
               len(r.of("record", "read_sync_state")) == 1, r.stdout)
    check("未綁定：不讀看板", len(r.of("board", "read_item")), 0)
    check("未綁定：零寫入", len(r.of("record", "write_sync_state")), 0)
    check("未綁定：不紅燈", r.rc, 0)
    check("未綁定：報告計數", r.metric("未綁定"), "1")


# ==========================================================================
# R-2 群：PR 的內容邊界
# ==========================================================================

def test_r2_1_diff_never_contains_aidlc_state_md() -> None:
    """@purpose R-2.1／[US:S-6 AC 2]：PR 的 diff **不得含 `aidlc-state.md` 的任何一行**。在 E-1 之下這是結構性成立的（唯一寫的檔就是 sync-state.json），**但仍要有斷言**——否則未來有人擴大寫入範圍時沒有東西會失敗。
    @given 兩個 intent 都被人改過，兩則 PR 都會開出
    @step 跑一輪 | **前提**：commit_and_push 確實被呼叫兩次（否則 paths 斷言是空的）
    @step 檢視每一次的 AIDLC_PATHS | 恰為該 intent 的 sync-state.json，一個路徑
    @step 全域掃描 | 除了 PR 內文那句刻意寫給審閱者看的說明之外，`aidlc-state.md` 不出現在任何一次呼叫的參數裡
    @pass 這是 [US:S-6 AC 2] 唯一的自動化落點。**第三步的例外要寫明**：PR 內文有一句
          「diff 只含 …，不含 aidlc-state.md 的任何一行」，那是給人看的說明而不是寫入
          路徑；把它一起禁掉會逼實作把有用的說明拿掉，所以斷言逐一分辨兩者
    @story S-6
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY,
                  plan={"board:read_item": changed_board()})
    cps = r.of("record", "commit_and_push")
    check_true("R-2.1 **前提**：commit_and_push 被呼叫兩次", len(cps) == 2,
               f"實得 {len(cps)} 次。stdout：{r.stdout}")
    for c in cps:
        paths = c["env"].get("AIDLC_PATHS", "")
        rec = c["env"].get("AIDLC_RECORD_PATH", "")
        check("R-2.2：paths 只含該 intent 的 sync-state.json", paths, f"{rec}/sync-state.json")
    # R-2.1 的全域掃描：paths 之外的每一個參數也不得夾帶引擎擁有的狀態檔。
    offenders = []
    for c in r.calls:
        blob = json.dumps({k: v for k, v in c.items() if k in ("env", "argv")}, ensure_ascii=False)
        if "aidlc-state.md" not in blob:
            continue
        # 唯一合法的出現位置：gh pr create 的 --body（給審閱者看的說明）。
        if c["tool"] == "gh" and c["op"] == "pr create":
            body = pr_arg(c, "--body")
            if "aidlc-state.md" in body and "aidlc-state.md" not in json.dumps(
                    [a for a in c["argv"] if a != body], ensure_ascii=False):
                continue
        offenders.append(c)
    check("R-2.1：`aidlc-state.md` 不出現在任何寫入參數裡（PR 內文的說明除外）",
          [f'{c["tool"]}:{c["op"]}' for c in offenders], [])


def test_r2_3_branch_name_and_label() -> None:
    """@purpose R-2.3 ＋ D-1 的擴充：分支名為 `<prefix>/<intent_id>-<YYYY-MM-DD>`、label 為 `aidlc-sync-reverse`。`<intent_id>` 是 E-2 的直接後果——同一天兩個 intent 被改動時 `<date>` 單獨會撞名。
    @given 兩個 intent 同日都被改動
    @step 跑一輪 | **前提**：兩次 commit_and_push
    @step 檢視分支名 | 兩者皆符合 `<prefix>/<intent_id>-<日期>` 且**逐字**等於各自 intent 的預期分支名
    @step 檢視 PR 的 --head | 與該次推送的分支逐字相同
    @step 檢視 PR 的 --repo 與 --label | 皆為沙箱注入的值（`gh pr create` 少了 `--repo` 會回退到 cwd 的 git remote，在 CI 上剛好也對，所以不會有症狀）
    @pass 撞名的後果是第二則 PR 的 diff 含第一個 intent 的變更，over-suppression 的結構性保證當場失效
    @story S-6
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY, plan={"board:read_item": changed_board()})
    cps = r.of("record", "commit_and_push")
    check_true("R-2.3 **前提**：兩次推送", len(cps) == 2, f"實得 {len(cps)} 次。{r.stdout}")
    branches = [c["env"]["AIDLC_BRANCH"] for c in cps]
    for b in branches:
        check_true(f"R-2.3：分支名形狀（{b}）",
                   bool(re.fullmatch(rf"{re.escape(BRANCH_PREFIX)}/[^/]+-\d{{4}}-\d{{2}}-\d{{2}}", b)), b)
    check("R-2.3：分支名逐字（含 intent_id 故不撞名）",
          sorted(branches), sorted([branch_of(ALPHA), branch_of(BETA)]))
    prs = r.gh("pr create")
    heads = sorted(pr_arg(c, "--head") for c in prs)
    check("R-2.3：PR 的 head 與推送的分支一致", heads, sorted(branches))
    check("R-2.3：每則 PR 都指名 --repo", [pr_arg(c, "--repo") for c in prs], [REPO_FULL] * 2)
    check("D-1：每則 PR 都掛上反向 label",
          [pr_arg(c, "--label") for c in prs], [REVERSE_LABEL] * 2)


def test_r1_5_never_pushes_to_the_trunk() -> None:
    """@purpose R-1.5／[req:FR-G1]：PR 的 base 為 `ut`，而**不得直接推 `ut`**。本單元推的一律是新建的反向分支。
    @given 一個 intent 被改動
    @step 跑一輪 | **前提**：commit_and_push 被呼叫一次
    @step 檢視 AIDLC_BRANCH | 不等於 trunk_ref、不等於 main、以反向前綴開頭
    @step 檢視 PR 的 base | 等於 trunk_ref
    @pass U-4 的 record.sh 有 PROTECTED_BRANCHES 硬檢查，但那是**第二道**；本單元傳錯值只會換到一個 rejected 而不是靜默直推，這條斷言守的是本單元自己的參數
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()})
    cps = r.of("record", "commit_and_push")
    check_true("R-1.5 **前提**：commit_and_push 被呼叫一次", len(cps) == 1, r.stdout)
    branch = cps[0]["env"]["AIDLC_BRANCH"]
    check_true("R-1.5：不推 trunk", branch != TRUNK_REF, branch)
    check_true("R-1.5：不推 main", branch != "main", branch)
    check_true("R-1.5：以反向分支前綴開頭", branch.startswith(BRANCH_PREFIX + "/"), branch)
    check("R-1.5：PR 的 base 為 trunk_ref", pr_arg(r.gh("pr create")[0], "--base"), TRUNK_REF)


# ==========================================================================
# R-1.4／E-2：一個 intent 一則 PR
# ==========================================================================

def test_e2_two_changed_intents_produce_two_prs() -> None:
    """@purpose R-1.4／E-2：**每個有變更的 intent 各開一個 PR**，不是單一 PR 含全部。這讓 over-suppression 的逐 intent 判定從「推導出來的」變成「結構上就是」。
    @given 兩個 intent 的雜湊都與記錄不同
    @step 跑一輪 | **前提**：兩個 intent 都確實被判為有變更（報告的「偵測到人為變更」為 2）
    @step 檢視 PR 數 | 恰為 2，且兩則的 head 不同
    @step 檢視每則 PR 的來源推送 | 每次 commit_and_push 的 paths 只含一個 intent 的檔
    @pass 上游先例（aidlc_sync_pull.py --all-intents）開單一 PR，於是一個開著的 PR 讓**全部** intent 一起被抑制——E-2 消掉的正是這個失敗模式
    @story S-6
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY, plan={"board:read_item": changed_board()})
    check("E-2 **前提**：兩個 intent 都判為有變更", r.metric("偵測到人為變更"), "2")
    prs = r.gh("pr create")
    check_true("E-2：兩則 PR", len(prs) == 2, f"實得 {len(prs)} 則。stdout：{r.stdout}")
    check_true("E-2：兩則 PR 的 head 不同",
               len({pr_arg(p, "--head") for p in prs}) == 2, str([pr_arg(p, "--head") for p in prs]))
    paths = sorted(c["env"]["AIDLC_PATHS"] for c in r.of("record", "commit_and_push"))
    check("E-2：每則 PR 的 diff 只含一個 intent",
          paths, sorted([f"{RECORD_ROOT}/{ALPHA}/sync-state.json",
                         f"{RECORD_ROOT}/{BETA}/sync-state.json"]))
    check("E-2：報告的 PR 清單", r.list_cell("本輪開出 PR"), ("2", f"{ALPHA}, {BETA}"))


# ==========================================================================
# R-6.1：防重複開 PR 用即時查詢
# ==========================================================================

def test_r6_1_open_pr_suppresses_a_second_one() -> None:
    """@purpose R-6.1：該 intent 已有**開啟中**的反向 PR ⇒ **不開第二個**。
    @given 開啟中的反向 PR 的 diff 含該 intent 的 sync-state.json，且該 intent 的雜湊又變了一次
    @step 跑一輪 | **前提**：本輪確實偵測到人為變更（stdout 出現「雜湊已變」）——沒有這一條，「不開 PR」會在「根本沒偵測到變更」上恆真通過
    @step 檢視 PR 與寫入 | 零 PR、零推送、**零 write_sync_state**（連 pending_reverse 都不覆寫）
    @step 檢視報告 | 進「已有開啟中反向 PR」清單，不紅燈
    @pass 少了這條，同一個人為改動每天各開一則 PR，而它們的內容一模一樣
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()},
                  pr_list_json=open_pr_json(ALPHA))
    check_true("R-6.1 **前提**：本輪確實偵測到人為變更", "雜湊已變" in r.stdout, r.stdout)
    check("R-6.1：不開第二則 PR", len(r.gh("pr create")), 0)
    check("R-6.1：不推送", len(r.of("record", "commit_and_push")), 0)
    check("R-6.1：不覆寫 pending_reverse", len(r.of("record", "write_sync_state")), 0)
    check("R-6.1：進「已有開啟中反向 PR」清單",
          r.list_cell("已有開啟中反向 PR"), ("1", ALPHA))
    check("R-6.1：不紅燈（機制的正常判斷）", r.rc, 0)


def test_r6_1_uses_the_live_query_not_the_stored_field() -> None:
    """@purpose R-6.1 逐字：判定用**即時查詢**，**不看儲存欄位**。`pending_reverse` 是「PR 的內容」不是「PR 是否存在」的證據——把兩者混為一談正是 functional-design iteration 1 那個 Critical 的成因。
    @given `sync-state.json` 的 pending_reverse **非 null**（上一則 PR 已合併留下的紀錄），而即時查詢回空清單
    @step 跑一輪 | **前提**：傳進去的 state 確實帶著非 null 的 pending_reverse，且本輪偵測到雜湊已變
    @step 檢視查詢 | gh pr list 恰一次，且帶 `--state open`（不是 all）
    @step 檢視結果 | **照常開 PR**——儲存欄位非 null 不構成抑制
    @pass 若改看儲存欄位，第一則 PR 合併之後該 intent 就再也不會有第二則反向 PR，人的後續改動全部靜默消失
    @story S-6
    @api n/a
    """
    stale = state_of({"pending_reverse": {"observed_status": "Done",
                                          "observed_at": "2026-08-01T00:00:00Z"}})
    r = run_round(plan={"record:read_sync_state": {"outputs": {"state_json": stale, "binding": "12"}},
                        "board:read_item": changed_board()})
    rss = r.of("record", "read_sync_state")
    check_true("R-6.1 **前提**：read_sync_state 被呼叫", len(rss) == 1, r.stdout)
    check_true("R-6.1 **前提**：傳進去的 state 確實帶著非 null 的 pending_reverse",
               json.loads(stale)["pending_reverse"] is not None, stale)
    check_true("R-6.1 **前提**：本輪偵測到雜湊已變", "雜湊已變" in r.stdout, r.stdout)
    lists = r.gh("pr list")
    check_true("R-6.1：即時查詢恰一次（迴圈之前）", len(lists) == 1, str(lists))
    check_true("R-6.1：查的是**開啟中**的 PR",
               "--state" in lists[0]["argv"] and pr_arg(lists[0], "--state") == "open",
               str(lists[0]["argv"]))
    check("R-6.1：儲存欄位非 null 不構成抑制，照常開 PR", len(r.gh("pr create")), 1)


def test_r6_1_query_argv_is_complete() -> None:
    """@purpose R-6.1 的查詢是本單元**唯一**的防重複開 PR 連鎖，它的每一個參數各自都是單點失效：少了 `--repo` 會問錯 repo，少了 `--label` 會把任何人為 PR 當成反向 PR，少了 `--state open` 會把已關閉的 PR 也算進來，`--json` 少要 `files` 則抑制集合恆為空。逐一斷言**那一次呼叫的 argv**。
    @given 一則掛著反向 label 的開啟中 PR 含該 intent 的 sync-state.json
    @step 跑一輪 | **前提**：gh pr list 恰被呼叫一次（迴圈之前的那一次）
    @step 檢視 argv | `--repo` 為沙箱注入的 repo、`--label` 為 U-6 推導出的字面、`--state` 為 open
    @step 檢視 `--json` 的欄位清單 | 同時含 `number` 與 `files`——`files` 是路徑→intent id 推導的唯一原料
    @step 檢視每個旗標的出現次數 | 各恰一次（重複給值時 gh 取最後一個，兩份設定會靜默地只有一份生效）
    @pass **斷言的對象是 argv 而不是 impl 的原始碼文字**：`--label "$REVERSE_PR_LABEL"`
          在腳本裡出現兩次（`pr list` 與 `pr create`），整檔 grep 分不出是哪一處，所以
          reviewer 把 `pr list` 那一處拿掉之後文字斷言照樣通過。這一條是 [Q3=A] 的
          逐 intent 抑制、R-1.4 的一 intent 一 PR 在**查詢端**的唯一守衛
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()},
                  pr_list_json=open_pr_json(ALPHA))
    lists = r.gh("pr list")
    check_true("**前提**：gh pr list 恰被呼叫一次", len(lists) == 1, str(lists))
    argv = lists[0]["argv"]
    check("R-6.1 argv：--repo", pr_arg(lists[0], "--repo"), REPO_FULL)
    check("R-6.1 argv：--label 為 U-6 推導出的字面", pr_arg(lists[0], "--label"), REVERSE_LABEL)
    check("R-6.1 argv：--state open（不是 all）", pr_arg(lists[0], "--state"), "open")
    fields = [f for f in pr_arg(lists[0], "--json").split(",") if f]
    check("R-6.1 argv：--json 含 files（路徑→intent id 的唯一原料）", "files" in fields, True)
    check("R-6.1 argv：--json 含 number", "number" in fields, True)
    for flag in ("--repo", "--label", "--state", "--json"):
        check(f"R-6.1 argv：{flag} 恰出現一次", argv.count(flag), 1)


def test_r6_1_only_labelled_prs_suppress() -> None:
    """@purpose R-6.1 逐字：查的是**掛著反向 label** 的 PR。一則碰到同一個 `sync-state.json` 的**人為** PR（沒有那個 label）不得抑制反向同步。
    @given 一則開啟中的人為 PR，diff 含該 intent 的 sync-state.json，但沒有反向 label；該 intent 的雜湊已變
    @step 跑一輪 | **前提**：那則 stub PR 確實碰到該 intent 的檔、且確實沒有反向 label（否則本測試在測別的東西）
    @step 檢視抑制集合 | 腳本印出的「已有開啟中反向 PR 的 intent」為**空集合**
    @step 檢視結果 | 照常開出一則 PR
    @pass 少了 `--label`，查詢會變成「所有開啟中 PR」——任何人手動改過某個 intent 的
          `sync-state.json`（例如修 U-7 交還的缺口 (3)）都會靜默地讓那個 intent 的反向
          偵測停擺，而報告上看起來只是「已有開啟中反向 PR」的正常判斷
    @story S-6
    @api n/a
    """
    human = pr_obj(ALPHA, number=777, labels=())
    check_true("**前提**：stub 的人為 PR 確實碰到該 intent 的 sync-state.json",
               [f["path"] for f in human["files"]] == [f"{RECORD_ROOT}/{ALPHA}/sync-state.json"],
               str(human))
    check("**前提**：stub 的人為 PR 沒有任何 label", human["labels"], [])
    r = run_round(plan={"board:read_item": changed_board()}, pr_list_json=prs_json(human))
    check_true("**前提**：本輪確實偵測到人為變更", "雜湊已變" in r.stdout, r.stdout)
    check("人為 PR 不進抑制集合", r.open_reverse(), set())
    check("人為 PR 不抑制：照常開出 PR", len(r.gh("pr create")), 1)
    check("人為 PR 不抑制：不進「已有開啟中反向 PR」清單",
          r.list_cell("已有開啟中反向 PR"), ("0", "（無）"))


def test_r6_1_matches_intent_ids_whole_line_not_by_prefix() -> None:
    """@purpose R-6.1 的比對是**整行相等**（`grep -qxF`）而不是子字串。抑制集合裡有一個以該 intent id 為前綴的較長 id 時，該 intent **不得**被抑制。
    @given 開啟中的反向 PR 只碰 `<ALPHA>-extended` 的檔；registry 裡的 ALPHA 雜湊已變
    @step 跑一輪 | **前提**：抑制集合恰為那個較長的 id（前綴對確實被製造出來了）
    @step 檢視 ALPHA | 照常開出 PR、不進「已有開啟中反向 PR」清單
    @pass **這條目前在真實 repo 不可達**——現有 intent 目錄沒有任何一組互為前綴（reviewer
          已逐一查證）。所以這是一條**斷言而不是行為變更**：`-x` 已經在程式裡，本條只是
          讓「有人為了省事把它拿掉」變成會紅燈的動作。intent 目錄命名沒有任何機制保證
          不出現前綴對（`260899-alpha` 與 `260899-alpha-rev2` 完全合法），所以不可達是
          **當下的資料狀態**，不是結構性保證
    @story S-6
    @api n/a
    """
    longer = f"{ALPHA}-extended"
    r = run_round(plan={"board:read_item": changed_board()},
                  pr_list_json=open_pr_json(longer))
    check("**前提**：抑制集合恰為那個較長的 id", r.open_reverse(), {longer})
    check("前綴碰撞不抑制：照常開出 PR", len(r.gh("pr create")), 1)
    check("前綴碰撞不抑制：不進「已有開啟中反向 PR」清單",
          r.list_cell("已有開啟中反向 PR"), ("0", "（無）"))


def test_q3_over_suppression_counterexample_pr_with_x_but_not_y() -> None:
    """@purpose **[Q3=A]（人工裁決）**：over-suppression 的反例——一則開啟中的反向 PR 含 X 的路徑而**不含** Y 的，該 PR 只貢獻 X 一個 intent id：X 被抑制、Y 照常開 PR。這正是 [US:S-6 AC 3] 的反例要求在反向側的落點。
    @given 開啟中的 PR 的 files 只含 X 的 sync-state.json（另加一個 record_root 之外的路徑當雜訊），X 與 Y 的雜湊都變了
    @step 跑一輪 | **前提**：X 與 Y 都確實被判為有變更（報告的「偵測到人為變更」為 2）
    @step 檢視抑制集合 | **恰為 {X}**——record_root 之外的雜訊路徑不得變成一個假的 intent id
    @step 檢視 X | 零 PR、進「已有開啟中反向 PR」清單
    @step 檢視 Y | 開出一則 PR，其 head **逐字等於** Y 的反向分支名
    @pass **這條測試不能取代 Bolt 3 的實測。** 它證明的是「本單元從 PR 的 files 推導
          intent id 的那段 jq 邏輯正確」，證明不了「GitHub 真的會在 `--json files` 裡
          回這些路徑」「U-6 讀同一份資料時得到同一個集合」「U-10b 的排除真的生效」。
          CAP-11 的「未實測」標記**不因本測試消除**——它現在標的是「一個 PR 一個
          intent 的形狀在真實 API 上是否如預期運作」，仍需 Bolt 3 對真實看板實測。
          **第二步是 reviewer 補上的**：`README.md` 這個雜訊輸入原本沒有任何斷言讀得到
          它的差別，於是「jq 少了 record_root 前綴過濾」的突變存活——雜訊會被當成一個
          叫 `README.md` 的假 intent id 進入抑制集合，而抑制集合當時沒有人在看
    @story S-6
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY,
                  plan={"board:read_item": changed_board()},
                  pr_list_json=open_pr_json(ALPHA, extra_paths=("README.md",)))
    check("Q3 **前提**：兩個 intent 都判為有變更", r.metric("偵測到人為變更"), "2")
    check("Q3：抑制集合恰為 {X}（雜訊路徑不得變成假 intent id）", r.open_reverse(), {ALPHA})
    check("Q3：X 被抑制", r.list_cell("已有開啟中反向 PR"), ("1", ALPHA))
    prs = r.gh("pr create")
    check_true("Q3：Y 照常開出一則 PR", len(prs) == 1, f"實得 {len(prs)} 則。stdout：{r.stdout}")
    check("Q3：那則 PR 的 head 逐字為 Y 的反向分支", pr_arg(prs[0], "--head"), branch_of(BETA))
    check("Q3：X 沒有被推送", [c["env"]["AIDLC_RECORD_PATH"] for c in r.of("record", "commit_and_push")],
          [f"{RECORD_ROOT}/{BETA}"])


def test_r6_1_query_failure_is_fail_closed() -> None:
    """@purpose R-6.1 的 fail-closed：開啟中 PR 查詢失敗 ⇒ **整輪中止且未對任何 intent 寫入**，紅燈 ＋ 通報。
    @given gh pr list 以非零 exit 失敗
    @step 跑一輪 | **前提**：gh pr list 確實被呼叫且確實失敗（stdout 出現查詢失敗）
    @step 檢視後續 | read_sync_state 零次、read_item 零次、零寫入、零 PR
    @step 檢視紅燈與通報 | rc≠0；通報一則 ExternalError，intent 用整輪層級的合成身分
    @pass 查不出來就不知道該不該開。誤開會為同一個 intent 堆出多則內容相同的 PR，誤不開只是延到下一輪——兩個方向的代價不對稱
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()}, pr_list_fail=True)
    check_true("**前提**：gh pr list 被呼叫", len(r.gh("pr list")) == 1, str(r.calls))
    check_true("**前提**：確實走到查詢失敗分支", "查詢失敗" in r.stdout, r.stdout)
    check("fail-closed：不讀任何 record", len(r.of("record", "read_sync_state")), 0)
    check("fail-closed：不讀看板", len(r.of("board", "read_item")), 0)
    check("fail-closed：零寫入", len(r.of("record", "write_sync_state")), 0)
    check("fail-closed：零 PR", len(r.gh("pr create")), 0)
    check_true("fail-closed：紅燈", r.rc != 0, f"rc={r.rc}")
    ns = r.notifies("ExternalError")
    check_true("fail-closed：通報一則 ExternalError", len(ns) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check("fail-closed：以整輪層級的合成身分通報",
          ns[0]["env"].get("AIDLC_INTENT_ID"), "aidlc-sync-reverse")


# ==========================================================================
# R-6.3：三種結局各一條（U-7 的教訓：錯誤分支不得零覆蓋）
# ==========================================================================

def test_r6_3_outcome_1_pr_created_no_branch_deletion() -> None:
    """@purpose R-6.3 的**第一種結局**：PR 開成 ⇒ 不刪任何分支、不紅燈、不通報。這一條存在的理由是讓另外兩條的斷言有對照組——沒有它，「有刪分支」與「該刪而沒刪」分不出來。
    @given 一個 intent 被改動，gh pr create 成功
    @step 跑一輪 | **前提**：gh pr create 確實被呼叫一次且成功（報告的 PR 計數為 1）
    @step 檢視刪分支 | git push --delete 零次
    @step 檢視整輪 | 不紅燈、零通報、孤兒清單為空
    @pass 誤刪一個已經有 PR 指向它的分支會讓那則 PR 立刻失效
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()})
    check("R-6.3(1) **前提**：PR 開成", r.metric("本輪開出的反向 PR"), "**1**")
    check("R-6.3(1)：不刪分支", len(r.git("push --delete")), 0)
    check("R-6.3(1)：不紅燈", r.rc, 0)
    check("R-6.3(1)：零通報", len(r.notifies()), 0)
    check("R-6.3(1)：孤兒清單為空", r.list_cell("孤兒分支"), ("0", "（無）"))


def test_r6_3_outcome_2_pr_fails_branch_deleted() -> None:
    """@purpose R-6.3 的**第二種結局**：`pending_reverse` 已 commit 但 PR 開不成 ⇒ **刪除該分支**，紅燈 ＋ 通報（附 intent id 與分支名）。
    @given commit_and_push 成功、gh pr create 失敗、git push --delete 成功
    @step 跑一輪 | **前提**：推送確實成功（stdout 出現「已推送反向分支」）且 PR 建立確實被嘗試過
    @step 檢視刪分支 | git push --delete 恰一次，刪的是剛推的那個分支
    @step 檢視紅燈與通報 | rc≠0；通報一則 ExternalError，detail 同時含 intent id 與分支名
    @step 檢視孤兒清單 | **為空**（刪成功就不是孤兒）
    @pass 依 R-6.0 那個 commit 從未進入 `ut`，所以這是清理與可見性要求；不刪的話 repo 上每天多一個沒有 PR 的分支且沒有人知道
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()}, pr_create_fail="all")
    check_true("R-6.3(2) **前提**：推送確實成功", "已推送反向分支" in r.stdout, r.stdout)
    check_true("R-6.3(2) **前提**：PR 建立確實被嘗試", len(r.gh("pr create")) == 1, str(r.calls))
    dels = r.git("push --delete")
    check_true("R-6.3(2)：刪分支恰一次", len(dels) == 1, f"實得 {len(dels)} 次。stdout：{r.stdout}")
    pushed = r.of("record", "commit_and_push")[0]["env"]["AIDLC_BRANCH"]
    check("R-6.3(2)：刪的是剛推的那個分支", dels[0]["branch"], pushed)
    check_true("R-6.3(2)：紅燈", r.rc != 0, f"rc={r.rc}")
    ns = r.notifies("ExternalError")
    check_true("R-6.3(2)：通報一則 ExternalError", len(ns) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    detail = ns[0]["env"].get("AIDLC_DETAIL", "")
    check_true("R-6.3(2)：通報 detail 含分支名", pushed in detail, detail)
    check("R-6.3(2)：通報的 intent id", ns[0]["env"].get("AIDLC_INTENT_ID"), ALPHA)
    check("R-6.3(2)：孤兒清單為空", r.list_cell("孤兒分支"), ("0", "（無）"))


def test_r6_3_outcome_3_pr_fails_and_delete_fails_leaves_an_orphan() -> None:
    """@purpose R-6.3 的**第三種結局**：PR 開不成**且刪分支也失敗** ⇒ 保留孤兒分支，同樣在同一次執行內紅燈 ＋ 通報，並在報告的孤兒清單裡列出來讓人去清。
    @given commit_and_push 成功、gh pr create 失敗、git push --delete 也失敗
    @step 跑一輪 | **前提**：推送成功、PR 被嘗試過、刪分支被嘗試過且確實失敗；且 git stub 的失敗訊息本身**不含**分支名與 intent id
    @step 檢視報告 | 孤兒清單那一格**逐字**為 `<intent_id> (<branch>)`
    @step 檢視通報 | intent id 掛在該 intent 上；detail 含「孤兒」字樣與分支名（人要知道 repo 上多了一個要手動清的分支）
    @step 檢視紅燈 | rc≠0
    @pass **這一條先前沒有任何東西守著**——把 cleanup_branch 的失敗分支整段拿掉，第二種
          結局的測試仍會全綠，因為它只驗「有沒有嘗試刪」。
          **本輪 reviewer 又在這一條抓到三個存活突變，三個都是斷言形狀的問題而不是
          覆蓋範圍的問題**：(a) 「detail 含分支名」是被 git stub 自己的錯誤訊息滿足的
          （stub 把分支名寫進了模擬訊息）——已改成不含分支名的認證失敗；(b) 第二種結局
          有 `AIDLC_INTENT_ID` 斷言而第三種沒有，於是「孤兒通報掛錯 intent id」存活；
          (c) 清單的「含 intent id **且**含分支名」中，分支名構造上就是
          `<prefix>/<intent_id>-<date>`，前半**不可能獨立失敗**——已改成逐字相等
    @story S-8
    @api n/a
    """
    check_true("R-6.3(3) **前提**：git stub 的刪除失敗訊息不含分支名／intent id"
               "（否則 detail 的斷言會被 stub 自己滿足）",
               BRANCH_PREFIX not in GIT_DELETE_FAIL_MSG and ALPHA not in GIT_DELETE_FAIL_MSG,
               GIT_DELETE_FAIL_MSG)
    r = run_round(plan={"board:read_item": changed_board()},
                  pr_create_fail="all", push_delete_fail="all")
    check_true("R-6.3(3) **前提**：推送確實成功", "已推送反向分支" in r.stdout, r.stdout)
    check_true("R-6.3(3) **前提**：PR 建立確實被嘗試", len(r.gh("pr create")) == 1, str(r.calls))
    dels = r.git("push --delete")
    check_true("R-6.3(3) **前提**：刪分支確實被嘗試", len(dels) == 1, str(r.calls))
    pushed = r.of("record", "commit_and_push")[0]["env"]["AIDLC_BRANCH"]
    check("R-6.3(3) **前提**：刪的是剛推的那個分支", dels[0]["branch"], pushed)
    check("R-6.3(3)：孤兒清單逐字為 `<intent_id> (<branch>)`",
          r.list_cell("孤兒分支"), ("1", f"{ALPHA} ({pushed})"))
    ns = r.notifies("ExternalError")
    check_true("R-6.3(3)：通報一則 ExternalError", len(ns) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check("R-6.3(3)：通報的 intent id", ns[0]["env"].get("AIDLC_INTENT_ID"), ALPHA)
    detail = ns[0]["env"].get("AIDLC_DETAIL", "")
    check_true("R-6.3(3)：通報 detail 說明是孤兒分支", "孤兒" in detail, detail)
    check_true("R-6.3(3)：通報 detail 含分支名（由 impl 自己寫，不是 stub 餵的）",
               pushed in detail, detail)
    check_true("R-6.3(3)：紅燈", r.rc != 0, f"rc={r.rc}")


def test_r6_3_does_not_delete_when_the_push_itself_failed() -> None:
    """@purpose R-6.3 的邊界：**推送本身失敗時不刪分支**。R-6.3 針對的是「已 commit 但 PR 開不成」；推送失敗代表 origin 上沒有東西可刪，去刪一個不存在的分支只會製造第二則假的失敗訊息。
    @given commit_and_push 以 exit 3（Rejected）失敗
    @step 跑一輪 | **前提**：commit_and_push 確實被呼叫且確實失敗（stdout 出現被拒）
    @step 檢視後續 | gh pr create 零次、git push --delete 零次
    @step 檢視通報 | reason_code 為 **Rejected**（不是 ExternalError）——U-4 的錯誤模型把 exit 3 定為 Rejected
    @pass 通報碼寫錯會讓 U-5 的去重鍵落在錯的命名空間，同一個失敗在兩個鍵下各開一則 issue
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board(),
                        "record:commit_and_push": {"exit": 3, "outputs": {
                            "result": "rejected", "reason": "non_fast_forward_exhausted",
                            "message": "! [rejected]"}}})
    cps = r.of("record", "commit_and_push")
    check_true("**前提**：commit_and_push 被呼叫一次", len(cps) == 1, r.stdout)
    check_true("**前提**：確實走到被拒分支", "被拒" in r.stdout, r.stdout)
    check("推送失敗：不開 PR", len(r.gh("pr create")), 0)
    check("推送失敗：**不刪分支**", len(r.git("push --delete")), 0)
    ns = r.notifies("Rejected")
    check_true("推送失敗：通報 reason_code=Rejected", len(ns) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check_true("推送失敗：紅燈", r.rc != 0, f"rc={r.rc}")


def test_commit_and_push_external_error_is_red_and_notified() -> None:
    """@purpose U-4 錯誤模型的另一半：commit_and_push 以 **exit 1**（ExternalError）失敗時通報 ExternalError、紅燈、不刪分支。
    @given commit_and_push 以 exit 1 失敗
    @step 跑一輪 | **前提**：commit_and_push 被呼叫且確實失敗（stdout 出現外部錯誤）
    @step 檢視通報 | reason_code 為 ExternalError（與 exit 3 的 Rejected 分流）
    @step 檢視 PR 與刪分支 | 皆零次；紅燈
    @pass 兩個 exit code 若合成一條分支，U-5 的 issue 標題永遠說不出是「被拒」還是「連不上」，而兩者的處置完全不同
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board(),
                        "record:commit_and_push": {"exit": 1, "outputs": {
                            "result": "external_error", "message": "fatal: unable to access"}}})
    check_true("**前提**：commit_and_push 被呼叫一次",
               len(r.of("record", "commit_and_push")) == 1, r.stdout)
    check_true("**前提**：確實走到外部錯誤分支", "外部錯誤" in r.stdout, r.stdout)
    check_true("通報 ExternalError", len(r.notifies("ExternalError")) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check("不開 PR", len(r.gh("pr create")), 0)
    check("不刪分支", len(r.git("push --delete")), 0)
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")


# ==========================================================================
# 其餘錯誤分支（[Q2=A]：外部失敗 ⇒ 通報 issue，不只紅燈）
# ==========================================================================

def test_q2_read_item_failure_notifies_and_does_not_abort_the_round() -> None:
    """@purpose **[Q2=A]（人工裁決）＋ ADR-0015 §5**：read_item 失敗 ⇒ 紅燈**且開通報 issue**，且**單一 intent 失敗不中止整輪**。沒有 C-5 這一段，[req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」在反向路徑上不成立。
    @given 兩個 intent；X 的 read_item 以 exit 1 失敗，Y 正常且雜湊已變
    @step 跑一輪 | **前提**：X 的 read_item 確實被呼叫且確實失敗
    @step 檢視通報 | 恰一則 ExternalError，intent id 為 X（不是整輪合成身分）
    @step 檢視 Y | 仍然開出 PR——單一 intent 失敗不中止整輪
    @step 檢視紅燈 | rc≠0
    @pass 紅燈與通報是兩件事（U-5 的 R-1.1）：紅燈讓 workflow 失敗、通報讓人在 issue 上看到，[req:FR-E1] 要的是後者
    @story S-8
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY,
                  plan={"board:read_item": changed_board(),
                        "board:read_item@12": {"exit": 1, "outputs": {
                            "result": "external_error", "message": "HTTP 502"}}})
    ri = r.of("board", "read_item")
    check_true("**前提**：兩個 intent 的 read_item 都被呼叫", len(ri) == 2,
               f"實得 {len(ri)} 次。stdout：{r.stdout}")
    check_true("**前提**：X 的 read_item 確實失敗", "read_item 失敗" in r.stdout, r.stdout)
    ns = r.notifies("ExternalError")
    check_true("Q2=A：恰一則 ExternalError 通報", len(ns) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check("Q2=A：通報掛在該 intent 上", ns[0]["env"].get("AIDLC_INTENT_ID"), ALPHA)
    prs = r.gh("pr create")
    check_true("單一 intent 失敗不中止整輪：Y 仍開出 PR", len(prs) == 1,
               f"實得 {len(prs)} 則。stdout：{r.stdout}")
    check("Y 的 PR（head 逐字）", pr_arg(prs[0], "--head"), branch_of(BETA))
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")
    check("X 進失敗清單", r.list_cell("本輪失敗"), ("1", ALPHA))


def test_f5_actions_bash_e_does_not_abort_the_round() -> None:
    """@purpose F5 迴歸：GitHub Actions 對未指定 `shell:` 的 `run:` 用 `bash -e {0}`，而 `set -uo pipefail` 關不掉已生效的 `-e`。本檔在此**自己釘住 `bash -e`**（不依賴模組層 BASH 預設值），驗證 `set +e` 真的在 rc 判讀之前生效——本單元受害最深：R-6.3 的三種結局（PR 開不成 → 刪分支 → 刪不掉 → 孤兒）**每一種都在 `rc=$?` 之後**，errexit 之下整條清理路徑不存在。
    @given 明確以 `bash -e` 啟動受測腳本；兩個 intent，X 的 read_item 以非零 exit 失敗、Y 的雜湊已變
    @step 跑一輪 | **前提**：兩個 intent 的 read_item 都被呼叫且 X 確實失敗
    @step 檢視 Y | 仍然開出 PR——證明控制流越過了 `rc=$?`
    @step 檢視通報 | 恰一則 ExternalError，且掛在 X 上（錯誤紀錄指名到 intent）
    @step 檢視報告 | X 進本輪失敗清單
    @step 檢視結束狀態 | 紅燈（不中止整輪 ≠ 把失敗吞掉）
    @pass 行為斷言，不比對 `set +e` 字面——有 `set +e` 但位置放在 rc 判讀之後一樣會紅
    @story S-8
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY,
                  plan={"board:read_item": changed_board(),
                        "board:read_item@12": {"exit": 1, "outputs": {
                            "result": "external_error", "message": "HTTP 502"}}},
                  bash_argv=["bash", "-e"])
    check_true("**前提**：確實以 -e 啟動仍走完整輪（不是 shell 一開始就死）",
               r.stdout.strip() != "", "受測腳本沒有任何輸出——errexit 可能在第一個非零就殺掉了 step")
    ri = r.of("board", "read_item")
    check_true("**前提**：兩個 intent 的 read_item 都被呼叫", len(ri) == 2,
               f"實得 {len(ri)} 次。stdout：{r.stdout}")
    check_true("**前提**：X 的 read_item 確實失敗", "read_item 失敗" in r.stdout, r.stdout)
    prs = r.gh("pr create")
    check_true("bash -e 下續跑：Y 仍開出 PR", len(prs) == 1,
               f"實得 {len(prs)} 則。stdout：{r.stdout}")
    check("bash -e 下續跑：開的是 Y 的 PR（head 逐字）", pr_arg(prs[0], "--head"),
          branch_of(BETA))
    ns = r.notifies("ExternalError")
    check_true("bash -e 下仍有通報", len(ns) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check("錯誤紀錄指名到失敗的那個 intent", ns[0]["env"].get("AIDLC_INTENT_ID"), ALPHA)
    check("bash -e 下 X 仍進報告的失敗清單", r.list_cell("本輪失敗"), ("1", ALPHA))
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")


def test_read_sync_state_failure_is_red_notified_and_reads_no_board() -> None:
    """@purpose read_sync_state 失敗 ⇒ 紅燈 ＋ 通報 ExternalError，且**不讀看板**（沒有 binding 就沒有讀取對象）。
    @given read_sync_state 以 exit 1 失敗
    @step 跑一輪 | **前提**：read_sync_state 被呼叫且確實失敗
    @step 檢視後續 | read_item 零次、零寫入、零 PR
    @step 檢視紅燈與通報 | rc≠0；一則 ExternalError
    @pass 這條分支若被靜默吞掉，一個讀不到狀態檔的 intent 每天被跳過而沒有人知道
    @story S-8
    @api n/a
    """
    r = run_round(plan={"record:read_sync_state": {"exit": 1, "outputs": {"state_json": "", "binding": ""}}})
    check_true("**前提**：read_sync_state 被呼叫", len(r.of("record", "read_sync_state")) == 1, r.stdout)
    check_true("**前提**：確實走到失敗分支", "read_sync_state 失敗" in r.stdout, r.stdout)
    check("不讀看板", len(r.of("board", "read_item")), 0)
    check("零寫入", len(r.of("record", "write_sync_state")), 0)
    check_true("通報 ExternalError", len(r.notifies("ExternalError")) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")


def test_write_sync_state_failure_is_red_notified_and_pushes_nothing() -> None:
    """@purpose 寫 `pending_reverse` 失敗 ⇒ 紅燈 ＋ 通報，且**不推送、不開 PR**（沒有內容可以當 PR 的 payload）。
    @given 雜湊已變、write_sync_state 以 exit 1 失敗
    @step 跑一輪 | **前提**：偵測到人為變更、write_sync_state 被呼叫且確實失敗
    @step 檢視後續 | commit_and_push 零次、gh pr create 零次、git push --delete 零次
    @step 檢視紅燈與通報 | rc≠0；一則 ExternalError
    @pass 推一個沒有內容的 commit 會產生一則空 diff 的 PR，人打開會看不懂它在問什麼
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board(),
                        "record:write_sync_state": {"exit": 1, "outputs": {"result": "failed"}}})
    check_true("**前提**：偵測到人為變更", "雜湊已變" in r.stdout, r.stdout)
    check_true("**前提**：write_sync_state 被呼叫", len(r.of("record", "write_sync_state")) == 1, r.stdout)
    check_true("**前提**：確實走到失敗分支", "寫入 pending_reverse 失敗" in r.stdout, r.stdout)
    check("不推送", len(r.of("record", "commit_and_push")), 0)
    check("不開 PR", len(r.gh("pr create")), 0)
    check("不刪分支", len(r.git("push --delete")), 0)
    check_true("通報 ExternalError", len(r.notifies("ExternalError")) == 1,
               str([n["env"].get("AIDLC_REASON_CODE") for n in r.notifies()]))
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")


def test_registry_missing_is_fail_closed_and_notified() -> None:
    """@purpose registry 不存在 ⇒ 整輪中止 ＋ 通報。選取來源不存在時「掃到 0 個 intent」與「沒有任何變更」在報告上長得一樣，必須出聲。
    @given `<record_root>/intents.json` 不存在
    @step 跑一輪 | **前提**：確實走到 registry 缺席分支（stdout 出現找不到 registry）
    @step 檢視後續 | read_sync_state 零次、零 PR
    @step 檢視紅燈與通報 | rc≠0；一則 ExternalError，以整輪合成身分
    @pass 靜默的空輪次會讓「機制沒在跑」看起來像「今天沒事」
    @story S-8
    @api n/a
    """
    r = run_round(no_registry=True)
    check_true("**前提**：確實走到 registry 缺席分支", "找不到 registry" in r.stdout, r.stdout)
    check("零讀取", len(r.of("record", "read_sync_state")), 0)
    check("零 PR", len(r.gh("pr create")), 0)
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")
    ns = r.notifies("ExternalError")
    check_true("通報 ExternalError", len(ns) == 1, str(r.notifies()))
    check("以整輪合成身分通報", ns[0]["env"].get("AIDLC_INTENT_ID"), "aidlc-sync-reverse")


def test_missing_record_dir_is_loud_but_not_fatal() -> None:
    """@purpose registry 列出的目錄不存在 ⇒ 警告並跳過該 intent，其餘照跑。
    @given 兩個 intent，X 的目錄不存在，Y 正常且雜湊已變
    @step 跑一輪 | **前提**：stdout 出現該目錄不存在的警告
    @step 檢視 X | 不讀狀態檔（read_sync_state 只被呼叫一次，屬於 Y）
    @step 檢視 Y | 照常開出 PR，且整輪不紅燈
    @pass 讓 registry 的漂移看得見，但不讓它擋住其他 intent
    @story S-6
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY, missing_dirs=(ALPHA,),
                  plan={"board:read_item": changed_board()})
    check_true("**前提**：出現目錄不存在的警告", "目錄不存在" in r.stdout, r.stdout)
    check("跳過的 intent 不讀狀態檔", len(r.of("record", "read_sync_state")), 1)
    check("其餘照跑", len(r.gh("pr create")), 1)
    check("不紅燈", r.rc, 0)


def test_head_sha_failure_aborts_the_round() -> None:
    """@purpose 讀不到 trunk HEAD SHA ⇒ 整輪中止。那個 SHA 是「本輪拿哪一版 record 的雜湊去比看板」的唯一查核依據（比照 U-7 的 R-7.3），缺了它整份報告與每一則 PR 都無法事後查核。
    @given git rev-parse HEAD 以非零 exit 失敗
    @step 跑一輪 | **前提**：git rev-parse 確實被呼叫且確實失敗
    @step 檢視後續 | 零查詢、零讀取、零 PR；rc≠0
    @pass 沒有這一條，一個 checkout 壞掉的 run 會照常開出一堆 PR，而沒有人知道它比的是哪一版
    @story S-6
    @api n/a
    """
    r = run_round(rev_parse_fail=True)
    check_true("**前提**：git rev-parse 被呼叫", len(r.git("rev-parse")) == 1, str(r.calls))
    check_true("**前提**：確實走到失敗分支", "讀不到 HEAD SHA" in r.stdout, r.stdout)
    check("零 PR", len(r.gh("pr create")), 0)
    check("零讀取", len(r.of("record", "read_sync_state")), 0)
    check_true("紅燈", r.rc != 0, f"rc={r.rc}")


def test_missing_composite_action_is_fail_closed() -> None:
    """@purpose 三支 composite action 與 U-6 的 impl **必須與本 workflow 同進 checkout**；任何一支缺席 ⇒ 整輪在動任何東西之前中止。
    @given 逐一讓 `board.sh`／`record.sh`／`notify.sh`／U-6 的 impl 各缺席一次
    @step 每一輪 | **前提**：stdout 出現指名該檔的中止訊息
    @step 檢視後續 | 零 gh 呼叫（連 R-6.1 的查詢都還沒發生）、零 record 呼叫
    @step 檢視結束狀態 | rc≠0
    @pass 缺席的後果不是「跳過那一支」而是**每個 `bash "$X_SH"` 都以 127 失敗**，而
          `set +e` 之下 127 會被當成「該工具回報失敗」——於是整輪對每個 intent 各開一則
          通報 issue，而真正的原因（checkout 少了東西）不會出現在任何一則裡面。
          reviewer 實測把這個存在性迴圈整段拿掉，全套測試無感
    @story S-8
    @api n/a
    """
    for tool, needle in (("board", "aidlc-sync-board/board.sh"),
                         ("record", "aidlc-sync-record/record.sh"),
                         ("notify", "aidlc-sync-notify/notify.sh"),
                         ("forward", "aidlc-sync-forward-impl.yml")):
        r = run_round(missing_tools=(tool,), plan={"board:read_item": changed_board()})
        check_true(f"**前提**：缺 {tool} 時確實走到中止分支且指名該檔",
                   needle in r.stdout and "同進 checkout" in r.stdout, r.stdout)
        check(f"缺 {tool}：零 gh 呼叫", [c["op"] for c in r.calls if c["tool"] == "gh"], [])
        check(f"缺 {tool}：零 record 呼叫", len(r.of("record")), 0)
        check_true(f"缺 {tool}：紅燈", r.rc != 0, f"rc={r.rc}")


def test_notify_failure_is_surfaced_not_swallowed() -> None:
    """@purpose 通報自身失敗時**必須出聲**（`construction.md`：Errors must be surfaced；U-5 的 R-1.1：紅燈與通報是兩件事）。原始失敗照常計入，但「連通報都沒開成」不得靜默。
    @given 雜湊已變、write_sync_state 失敗（原始失敗），且 notify 本身也以非零 exit 失敗
    @step 跑一輪 | **前提**：原始失敗確實發生、notify 確實被呼叫且確實失敗
    @step 檢視 stdout | 有一行 `::warning::通報失敗`，且指名 intent 與 reason_code
    @step 檢視原始失敗的處置 | 仍然紅燈、仍然進報告的失敗清單（通報失敗不得吃掉原始失敗）
    @pass 若把這個 rc 丟掉，「[req:FR-E1] 的 issue 沒開出來」在任何地方都看不到——人只會
          看到一次紅燈，然後去 issue 列表找一則不存在的通報
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board(),
                        "record:write_sync_state": {"exit": 1, "outputs": {"result": "failed"}},
                        "notify:notify": {"exit": 1, "outputs": {
                            "result": "failed", "message": "HTTP 500"}}})
    check_true("**前提**：原始失敗確實發生", "寫入 pending_reverse 失敗" in r.stdout, r.stdout)
    ns = r.notifies()
    check_true("**前提**：notify 確實被呼叫一次", len(ns) == 1, str(r.calls))
    warns = [l for l in r.stdout.splitlines() if l.startswith("::warning::通報失敗")]
    check_true("通報自身失敗會出聲（::warning::）", len(warns) == 1, r.stdout)
    check_true("該警告指名 intent 與 reason_code",
               len(warns) == 1 and ALPHA in warns[0] and "ExternalError" in warns[0], str(warns))
    check_true("原始失敗仍照常紅燈", r.rc != 0, f"rc={r.rc}")
    check("原始失敗仍進報告的失敗清單", r.list_cell("本輪失敗"), ("1", ALPHA))


def test_round_at_is_taken_once_and_used_everywhere() -> None:
    """@purpose `ROUND_AT` **整輪一個值**：它同時是 `pending_reverse.observed_at`、分支名的日期、PR 內文與報告的偵測時刻。逐 intent 重算會讓同一輪的紀錄在跨午夜時分裂成兩個日期，而事後沒有任何方法看得出那是同一輪。
    @given 兩個 intent 同輪都被改動；`date` 為 PATH shim，每次呼叫回一個遞增的秒數
    @step 檢視取值次數 | **前提**：`date` 恰被呼叫一次（真實的 date 在同一秒內連取兩次會回同一個值，**測不出**重算）
    @step 檢視取值參數 | 逐字為 `-u +%Y-%m-%dT%H:%M:%SZ`（shim 對未預期的 argv 一律 exit 9，所以格式改了會當場紅）
    @step 檢視兩個 intent 的 observed_at | 相同，且等於報告標題與兩則 PR 內文的偵測時刻
    @step 檢視兩個分支名的日期段 | 相同
    @pass 這是一條不變式而不是行為分支——沒有 shim 就沒有辦法斷言它，於是 reviewer 的
          「逐 intent 重算」突變存活
    @story S-6
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY, plan={"board:read_item": changed_board()})
    dates = r.dates()
    check("ROUND_AT：整輪只取一次時刻", len(dates), 1)
    check_true("ROUND_AT：取值參數逐字", dates and dates[0]["argv"] == DATE_ARGV, str(dates))
    observed = [json.loads(c["env"]["AIDLC_STATE_JSON"])["pending_reverse"]["observed_at"]
                for c in r.of("record", "write_sync_state")]
    check("ROUND_AT：兩個 intent 的 observed_at 皆為同一個值", observed,
          [STUB_ROUND_AT, STUB_ROUND_AT])
    check_true("ROUND_AT：報告標題用同一個值",
               f"AI-DLC 反向同步報告（{STUB_ROUND_AT}）" in r.report, r.report)
    times = sorted(body_rows(pr_arg(c, "--body")).get("偵測時刻（UTC）")
                   for c in r.gh("pr create"))
    check("ROUND_AT：兩則 PR 內文用同一個值", times, [STUB_ROUND_AT, STUB_ROUND_AT])
    check("ROUND_AT：兩個分支名的日期段相同",
          sorted(c["env"]["AIDLC_BRANCH"] for c in r.of("record", "commit_and_push")),
          sorted([branch_of(ALPHA), branch_of(BETA)]))


# ==========================================================================
# label 的冪等建立（沿用 U-5 的先例）
# ==========================================================================

def test_label_is_created_once_per_round_when_absent() -> None:
    """@purpose `gh pr create --label` 對不存在的 label 會失敗，而那會把每一次真實的人為改動都推進 R-6.3 的刪分支路徑（症狀：每天紅燈但永遠開不出 PR）。沿用 U-5 的先例做冪等建立，且**整輪只做一次**。
    @given repo 上沒有這個 label（label list 回空陣列），兩個 intent 都被改動
    @step 跑一輪 | **前提**：兩則 PR 都開出來了
    @step 檢視 label 呼叫 | label list 一次、label create 一次（不是兩次）
    @step 檢視建立的 label 名 | 與 U-6 推導出的字面逐字相同
    @pass 每則 PR 各查一次 label 是 U-5 的 [Q2=B] 被否決的那種浪費；一次都不查則第一則 PR 必失敗
    @story S-6
    @api n/a
    """
    r = run_round(registry=TWO_REGISTRY, plan={"board:read_item": changed_board()},
                  label_list_json="[]")
    check_true("**前提**：兩則 PR 都開出來", len(r.gh("pr create")) == 2, r.stdout)
    check("label list 整輪一次", len(r.gh("label list")), 1)
    check("label create 整輪一次", len(r.gh("label create")), 1)
    check_true("建立的是 D-1 推導出的那個 label",
               REVERSE_LABEL in r.gh("label create")[0]["argv"], str(r.gh("label create")[0]["argv"]))


def test_existing_label_is_not_recreated() -> None:
    """@purpose label 已存在時**不再建立**——冪等的另一半。
    @given label list 回的清單已含該 label
    @step 跑一輪 | **前提**：PR 開出來了、label list 被呼叫過
    @step 檢視 label create | 零次
    @pass 每天重建一次 label 會讓 repo 的 audit log 每天多一筆無意義的寫入
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()},
                  label_list_json=json.dumps([{"name": "bug"}, {"name": REVERSE_LABEL}]))
    check_true("**前提**：PR 開出來", len(r.gh("pr create")) == 1, r.stdout)
    check_true("**前提**：label list 被呼叫", len(r.gh("label list")) == 1, str(r.calls))
    check("label 已存在則不重建", len(r.gh("label create")), 0)


def test_label_failure_goes_down_the_r6_3_cleanup_path() -> None:
    """@purpose label 無法確保存在 ⇒ **不嘗試開 PR**，直接走 R-6.3 的清理（刪掉剛推的分支）＋ 紅燈 ＋ 通報。
    @given label list 失敗；一個 intent 已被改動且分支已推出去
    @step 跑一輪 | **前提**：推送成功、label list 確實失敗
    @step 檢視 PR | gh pr create **零次**（沒有 label 就不送出去，省一次注定失敗的寫入）
    @step 檢視清理 | git push --delete 一次；紅燈；通報 ExternalError
    @pass 若不走清理，repo 上會留下一個沒有 PR 的分支且每天多一個
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()}, label_list_fail=True)
    check_true("**前提**：推送確實成功", "已推送反向分支" in r.stdout, r.stdout)
    check_true("**前提**：label list 確實失敗", "gh label list 失敗" in r.stdout, r.stdout)
    check("label 失敗：不嘗試開 PR", len(r.gh("pr create")), 0)
    check("label 失敗：走 R-6.3 清理", len(r.git("push --delete")), 1)
    check_true("label 失敗：通報 ExternalError", len(r.notifies("ExternalError")) == 1,
               str(r.notifies()))
    check_true("label 失敗：紅燈", r.rc != 0, f"rc={r.rc}")


def test_label_create_race_is_not_a_failure() -> None:
    """@purpose 競態：另一個並行 run 在 list 與 create 之間建好了 label（`already exists`）⇒ 目標狀態已達成，**不是失敗**，照常開 PR。
    @given label list 回空、label create 以 `already exists` 失敗
    @step 跑一輪 | **前提**：label create 確實被呼叫且確實回了失敗
    @step 檢視結果 | PR 照常開出、不紅燈、零通報
    @pass 把競態當失敗會讓兩個並行 run 之中的一個每次都白跑
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()},
                  label_list_json="[]", label_create_fail="exists")
    check_true("**前提**：label create 被呼叫", len(r.gh("label create")) == 1, str(r.calls))
    check("競態不算失敗：PR 照常開", len(r.gh("pr create")), 1)
    check("競態不算失敗：不刪分支", len(r.git("push --delete")), 0)
    check("競態不算失敗：不紅燈", r.rc, 0)
    check("競態不算失敗：零通報", len(r.notifies()), 0)


# ==========================================================================
# R-6.2：pending_reverse 的生命週期
# ==========================================================================

def test_r6_2_pending_reverse_is_never_written_back_to_null() -> None:
    """@purpose R-6.2：**本機制不清除 `pending_reverse`**，也沒有任何一條路徑把它寫回 `null`。它記的是「最近一次反向觀察」，隨下一次反向事件被覆寫（R-1.3）。
    @given 四種情境各跑一輪：雜湊未變／不受管／已有開啟中 PR／雜湊已變
    @step 逐輪蒐集全部 write_sync_state 的 patch | **前提**：至少有一輪確實寫過（否則「沒有寫成 null」恆真）
    @step 檢視每一個 patch | 凡含 pending_reverse 者，其值一律是物件，**沒有任何一次是 null**
    @pass 若有人「順手」加一條清除路徑，R-1.5 明訂本單元不得直推 `ut`——清除就得為每一次反向事件再開一則 PR，讓人審一個沒有任何讀者的欄位歸零
    @story S-6
    @api n/a
    """
    rounds = [
        run_round(),
        run_round(plan={"board:read_item": {"outputs": {"managed_block_hash": ""}}}),
        run_round(plan={"board:read_item": changed_board()}, pr_list_json=open_pr_json(ALPHA)),
        run_round(plan={"board:read_item": changed_board()}),
    ]
    patches = []
    for rd in rounds:
        for c in rd.of("record", "write_sync_state"):
            patches.append(json.loads(c["env"]["AIDLC_STATE_JSON"]))
    check_true("R-6.2 **前提**：至少有一輪確實寫過狀態檔（否則本測試恆真）",
               len(patches) >= 1, f"四輪合計 {len(patches)} 次寫入")
    nulls = [p for p in patches if "pending_reverse" in p and p["pending_reverse"] is None]
    check("R-6.2：沒有任何一次把 pending_reverse 寫回 null", nulls, [])
    objs = [p for p in patches if isinstance(p.get("pending_reverse"), dict)]
    check_true("R-6.2：有寫的那幾次都是物件", len(objs) == len(patches), str(patches))


# ==========================================================================
# 常數推導（[Q1=A]）與單一雜湊路徑（ADR-0015 §10）
# ==========================================================================

def test_q1_reverse_pr_label_is_derived_from_u6_not_copied() -> None:
    """@purpose **[Q1=A]（人工裁決）**：反向 PR 的 label 從 U-6 的 impl 推導，全 repo 只有一份字面。比照 U-7 在 reconcile-impl 的做法。
    @step 掃描本單元的編排腳本（去掉註解）| label 的字面值只出現在整輪層級通報的合成 intent id 上，不出現在任何賦值或 gh 參數位置
    @step 檢視 gh 參數 | `pr list`／`pr create`／`label create` 一律用 `$REVERSE_PR_LABEL` 變數
    @step 讓 U-6 的 impl 缺少該常數 | **前提**：那一輪確實走到推導失敗（stdout 出現找不到常數）
    @step 檢視結果 | 整輪中止（fail-closed），零查詢、零 PR
    @pass 各抄一份的代價本 intent 已經付過（U-10a 的 MARKER-1）。**這條裁決的代價**：
          真實來源落在**消費者**（U-6）而不是產生者（本單元）身上——本單元才是唯一把
          label 掛上 PR 的地方。已列入待 Bolt 3 gate 追認。
          **第一步的例外要寫明**：整輪層級失敗的合成 intent id 沿用 U-6／U-7 的形狀
          （`aidlc-sync-forward`／`aidlc-sync-reconcile`），到本單元恰好與 label 同字。
          那是兩個不同的東西剛好同名——若為了讓斷言好寫而改掉合成 id，反而會破壞三支
          workflow 之間的命名一致性。斷言因此**逐行分辨**，而不是整檔 grep
    @story S-6
    @api n/a
    """
    literal_lines = [l.strip() for l in CODE.splitlines() if REVERSE_LABEL in l]
    check_true("**前提**：label 字面確實出現在程式碼裡（否則本斷言是空的）",
               len(literal_lines) >= 1, "一次都沒出現——推導或合成 id 被改掉了？")
    bad = [l for l in literal_lines if not l.startswith("notify_failure ")]
    check("[Q1=A]：label 的字面值只出現在整輪層級通報的合成 intent id 上", bad, [])
    check_true("[Q1=A]：腳本以 sed 從 U-6 的 impl 推導",
               'REVERSE_PR_LABEL="$(sed' in CODE, "找不到推導用的 sed")
    # **這裡數的是出現次數而不是「有沒有出現」**：`--label "$REVERSE_PR_LABEL"` 在腳本
    # 裡有兩個呼叫點（R-6.1 的 `pr list` 與 R-1.4 的 `pr create`），整檔 `in CODE` 分不
    # 出是哪一處——reviewer 把 `pr list` 那一處整個拿掉，這條文字斷言仍被 `pr create`
    # 那一處滿足。真正守住兩個呼叫點的是行為層的 argv 斷言
    # （test_r6_1_query_argv_is_complete 與 test_r2_3_branch_name_and_label）；本條只
    # 保留「不得把 label 寫成字面值」這一件事。
    check("[Q1=A]：--label 的兩個呼叫點都用變數而非字面",
          CODE.count('--label "$REVERSE_PR_LABEL"'), 2)
    check_true('[Q1=A]：gh label create 用變數而非字面',
               'gh label create "$REVERSE_PR_LABEL"' in CODE,
               "找不到——label 可能被寫成字面值了")
    r = run_round(plan={"board:read_item": changed_board()},
                  forward_impl_body="# U-6 的 impl 被改寫，常數不見了\n")
    check_true("**前提**：確實走到推導失敗分支",
               "找不到 REVERSE_PR_LABEL 常數" in r.stdout, r.stdout)
    check("推導失敗：整輪中止，零查詢", len(r.gh("pr list")), 0)
    check("推導失敗：零 PR", len(r.gh("pr create")), 0)
    check_true("推導失敗：紅燈", r.rc != 0, f"rc={r.rc}")


def test_sync_marker_is_derived_from_record_sh() -> None:
    """@purpose 同步標記從 U-4 的 `record.sh` 推導，不在本檔抄第二份。它是 commit_and_push 的介面要求（R-3.3），也是 U-6 防線②的依據。
    @step 檢視 commit 訊息 | **前提**：commit_and_push 被呼叫；訊息含由 record.sh 推導出的標記
    @step 讓 record.sh 缺少該常數 | 整輪中止，零讀取、零 PR
    @pass 訊息缺標記時 commit_and_push 會以介面誤用（exit 2）拒絕，一輪反向同步全部白跑
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()})
    cps = r.of("record", "commit_and_push")
    check_true("**前提**：commit_and_push 被呼叫", len(cps) == 1, r.stdout)
    check_true(f"commit 訊息含同步標記 {MARKER!r}",
               MARKER in cps[0]["env"]["AIDLC_MESSAGE"], cps[0]["env"]["AIDLC_MESSAGE"])
    # **比對的是裸字面而不是帶引號的字面**（`in`-斷言掃描的順帶發現，非 reviewer 提出）：
    # 原本寫 f'"{MARKER}"'，於是把標記直接寫進 commit 訊息（`…人為改動 [aidlc-sync]"`）
    # 不會被命中——那正是這條要防的動作，而它同時通過上面那條「訊息含標記」的斷言，
    # 因為兩條都由同一份硬寫的字串滿足。裸字面沒有這個縫。
    check_true("編排腳本的程式碼不含同步標記的字面值",
               MARKER not in CODE, "腳本裡出現了同步標記的字面值")
    r2 = run_round(record_sh_head="# 常數不見了\n")
    check_true("**前提**：確實走到推導失敗分支",
               "找不到 SYNC_MARKER 常數" in r2.stdout, r2.stdout)
    check("推導失敗：零讀取", len(r2.of("record", "read_sync_state")), 0)
    check_true("推導失敗：紅燈", r2.rc != 0, f"rc={r2.rc}")


def test_adr0015_s10_hash_has_exactly_one_computation_path() -> None:
    """@purpose ADR-0015 §10 的等價不變式：U-6 記錄的雜湊與本單元比對用的雜湊必須逐位元組相等，而那是由「兩端走**同一條**回讀路徑」在構造上保證的。本單元因此**不得**自己呼叫 U-2 的 block.sh 再算一次。
    @step 掃描編排腳本的**程式碼**（去掉整行註解）| 不出現 `block.sh`、`BLOCK_SH`、sha256 工具
    @step 檢視雜湊來源 | **前提**：確實有一次 read_item；比對用的值取自它的 managed_block_hash output
    @pass 自己再算一次就是第二條路徑；兩條路徑一旦有任何正規化差異（換行、markdown
          轉義、HTML 註解排版），後果是**每天為每個受管 intent 各開一則反向 PR**
          ——ADR-A6 點名的最危險失效模式。附帶：`read_item` 也不回傳 issue body，所以
          R-4c 方法表裡的 `parse` 與 `content_hash` 兩列本單元**結構上無法直接呼叫**。
          **只掃程式碼不掃註解是刻意的**：impl 有一整段註解正是在解釋「為什麼不呼叫
          block.sh」，把它算成命中會逼實作刪掉那段說明，而那是這條不變式在程式裡唯一
          被寫下來的地方
    @story S-6
    @api n/a
    """
    for needle in ("block.sh", "BLOCK_SH", "sha256sum", "shasum"):
        check(f"ADR-0015 §10：編排腳本的程式碼不出現 {needle}", needle in CODE, False)
    check_true("ADR-0015 §10：註解裡確實留著「為什麼不呼叫 block.sh」的說明",
               "block.sh" in SCRIPT, "說明被刪掉了——這條不變式就沒有地方被寫下來")
    r = run_round(plan={"board:read_item": changed_board()})
    check_true("**前提**：read_item 被呼叫一次", len(r.of("board", "read_item")) == 1, r.stdout)
    check_true("雜湊比對確實用了 read_item 回的值",
               HASH_HUMAN_EDITED in r.stdout and HASH_ON_RECORD in r.stdout, r.stdout)


# ==========================================================================
# 報告與 SEC
# ==========================================================================

def test_report_holds_only_ids_and_numbers() -> None:
    """@purpose 比照 U-7 的 SEC-2：本 repo 為 public、job summary 與 PR 內文皆公開可讀。報告與 PR 只放 intent id、數字與分支名——不得夾帶憑證，也不得把本單元根本不讀的看板欄位值帶出去。
    @given read_item 回一個帶探針字串的 field_value（本單元完全不讀該欄）
    @step 跑一輪 | **前提**：PR 確實開出來（否則報告是空的）
    @step 掃描報告與 PR 內文 | 皆不含探針字串、皆不含 token
    @step 掃描 stdout | 不含 token
    @pass 憑證外洩一次即等同公開發布（`project.md` 對 Actions log 的記載）；看板欄位值本單元不讀，出現在公開處只可能是誤帶
    @story S-8
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()})
    prs = r.gh("pr create")
    check_true("**前提**：PR 確實開出來", len(prs) == 1, r.stdout)
    body = pr_arg(prs[0], "--body")
    check("報告不含 field_value 探針", FIELD_PROBE in r.report, False)
    check("PR 內文不含 field_value 探針", FIELD_PROBE in body, False)
    check("報告不含憑證", TOKEN in r.report, False)
    check("PR 內文不含憑證", TOKEN in body, False)
    check("stdout 不含憑證", TOKEN in r.stdout, False)


def test_report_renders_empty_lists_as_none() -> None:
    """@purpose 空清單渲染為「（無）」而非空白格：空白格看不出是「沒有」還是「壞了」。
    @given 一輪什麼都沒發生（雜湊未變）
    @step 檢視報告的五份清單 | **前提**：報告確實產生了（含標題）
    @step 逐格檢視 | 五份清單皆為 0 筆且顯示「（無）」
    @pass 一份看不出好壞的報告，跟沒有報告一樣
    @story S-6
    @api n/a
    """
    r = run_round()
    check_true("**前提**：報告確實產生", "AI-DLC 反向同步報告" in r.report, r.report)
    for name in ("本輪開出 PR", "已有開啟中反向 PR", "不受管，跳過", "本輪失敗", "孤兒分支"):
        check(f"空清單渲染（{name}）", r.list_cell(name), ("0", "（無）"))


def test_pr_body_states_the_close_path_honestly() -> None:
    """@purpose [req:FR-G3]／[US:S-6] 的誠實邊界：PR **關閉（未合併）也會恢復覆寫**，人的改動最終被輾回去。PR 內文必須把這一條寫給審閱者看——benefit clause 是「送到人面前決定」而不是「我的判斷會被保留」。
    @given 一則反向 PR 被開出
    @step 檢視 PR 內文 | **前提**：PR 確實開出來且 --body 非空
    @step 抽出「- **…**：」形式的路徑條目 | 恰為「合併」與「關閉（不合併）」兩條
    @step 檢視關閉那一條的**同一行** | 同時說出「恢復覆寫」與「被輾回」
    @step 檢查可追溯欄位 | 內文的表格**逐列逐字**等於 intent／看板 Status／偵測時刻／比對基準 SHA／分支五列
    @pass 審閱者若不知道「關閉＝改動被輾回」，他會以為關閉是安全的「稍後再說」。
          **斷言鎖的是條目本身而不是「關閉」二字**——[req:FR-G3] 的逐字引用（「直到
          對應 PR 被合併或關閉」）在內文另一處也含這兩個字，第一版寫成整檔 `in body`
          時把那個順帶命中當成了通過：突變 M19 把條目標題改成「暫緩」，測試照樣全綠。
          **最後一步同理**：原本寫成四條 `X in body`，而「分支」那一格的值構造上就含
          intent id，於是「內文含 intent id」不可能獨立失敗；改成逐列比對整張表之後，
          刪掉任何一列、改動任何一格的值都會紅
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board(status="Done")})
    prs = r.gh("pr create")
    check_true("**前提**：PR 確實開出來", len(prs) == 1, r.stdout)
    body = pr_arg(prs[0], "--body")
    check_true("**前提**：--body 非空", len(body) > 100, body)
    bullets = [l.strip() for l in body.splitlines() if l.strip().startswith("- **")]
    check_true("**前提**：內文確實有「- **…**：」形式的路徑條目",
               len(bullets) == 2, str(bullets))
    labels = sorted(l.split("**")[1] for l in bullets)
    check("內文的兩條路徑條目", labels, ["合併", "關閉（不合併）"])
    closed_line = [l for l in bullets if l.split("**")[1] == "關閉（不合併）"]
    check_true("關閉那一條同時說出「恢復覆寫」與「被輾回」",
               len(closed_line) == 1 and "覆寫" in closed_line[0] and "輾回" in closed_line[0],
               str(closed_line))
    check("內文的可追溯表格逐列逐字", body_rows(body), {
        "項目": "值",
        "intent": f"`{ALPHA}`",
        "看板上目前的 Status": "`Done`",
        "偵測時刻（UTC）": STUB_ROUND_AT,
        f"比對基準（`{TRUNK_REF}` HEAD）": f"`{TRUNK_SHA}`",
        "分支": f"`{branch_of(ALPHA)}`",
    })


def test_pr_body_states_the_write_scope_and_the_per_intent_pause() -> None:
    """@purpose PR 內文另外兩段**給審閱者判斷用**的說明：①這則 PR 只動一個檔（[req:FR-G2] 的寫入邊界）②開啟期間正向同步對**這一個** intent 暫停。兩段都是審閱者按下合併之前需要知道的事實，而它們可被整段刪掉而不影響任何其他斷言。
    @given 一則反向 PR 被開出
    @step 檢視「只動一個檔」段 | **前提**：恰有一行是該小節標題；說明那一行含本 intent 的 sync-state.json 路徑、`pending_reverse` 欄位名、`aidlc-state.md` 與 [req:FR-G2]
    @step 檢視暫停說明 | 恰有一行提到暫停；同一行同時說出「正向同步」「本 intent 的 id」「逐 intent」
    @pass 少了①，審閱者無從判斷這則 PR 會不會動到引擎自己的狀態檔（[US:S-6 AC 2] 要人
          能「檢視其 diff」）；少了②，他不知道**不處理**的代價是那個 intent 的看板停止
          更新——兩段都是 reviewer 實測可整段刪除而全套 39 條測試無感的位置
    @story S-6
    @api n/a
    """
    r = run_round(plan={"board:read_item": changed_board()})
    prs = r.gh("pr create")
    check_true("**前提**：PR 確實開出來", len(prs) == 1, r.stdout)
    body = pr_arg(prs[0], "--body")
    lines = [l.strip() for l in body.splitlines()]
    check("**前提**：「只動一個檔」小節標題恰一行", lines.count("### 這個 PR 只動一個檔"), 1)
    scope = [l for l in lines if "[req:FR-G2]" in l]
    check_true("寫入邊界說明恰一行", len(scope) == 1, str(scope))
    for needle in (f"{RECORD_ROOT}/{ALPHA}/sync-state.json", "pending_reverse", "aidlc-state.md"):
        check_true(f"寫入邊界說明含 {needle}", len(scope) == 1 and needle in scope[0], str(scope))
    pause = [l for l in lines if "暫停" in l]
    check_true("逐 intent 暫停的說明恰一行", len(pause) == 1, str(pause))
    for needle in ("正向同步", ALPHA, "逐 intent"):
        check_true(f"暫停說明含 {needle}", len(pause) == 1 and needle in pause[0], str(pause))


# ==========================================================================
# 結構斷言（沒有行為層可驗的四件事）
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


def test_cron_does_not_collide_with_any_existing_schedule() -> None:
    """@purpose 排程不得與**四個**既有排程碰撞（三支 gh-aw ＋ 本 intent 的對帳）。碰撞的後果不是失敗而是**資源競爭**——三支既有排程皆含 LLM agent step，同時起跑會拉長彼此的 runner 排隊。這是建置期檢查，沒有執行期行為可驗。
    @given 全部既有 workflow 檔
    @step 掃出既有 cron | **前提**：至少掃到四支（掃到零支代表這條斷言是空的）
    @step 比對本單元的 cron | 與每一個既有 cron 的（分, 時）皆不同，故永不同分鐘起跑
    @pass 前提斷言在此特別重要：若 glob 或 regex 壞掉，「沒有碰撞」會恆真通過
    @story S-6
    @api n/a
    """
    existing = existing_crons()
    flat = [c for lst in existing.values() for c in lst]
    check_true("**前提**：至少掃到四支既有排程（掃到零支代表本測試是空的）",
               len(flat) >= 4, f"實得 {existing}")
    outer = outer_doc()
    on = outer.get(True) or outer.get("on")
    ours = [row["cron"] for row in (on.get("schedule") or [])]
    check_true("**前提**：本單元確實有排程", len(ours) == 1, str(ours))
    mine = tuple(ours[0].split()[:2])
    for name, crons in existing.items():
        for c in crons:
            check(f"不與 {name} 的 '{c}' 同分鐘起跑", tuple(c.split()[:2]) == mine, False)


def test_structure_triggers_concurrency_and_workflow_call() -> None:
    """@purpose [ad:S-C] 的觸發設定（cron ＋ workflow_dispatch）、ADR-A10 的參數化（impl 只認 workflow_call），以及 **concurrency 的落點**。
    @given 兩支 workflow
    @step 解析 YAML | 外層為 schedule ＋ workflow_dispatch；impl 只有 workflow_call
    @step 檢視 input／secret 集合 | 六個 input ＋ 一個 secret
    @step 檢視 concurrency | 群組與 U-7 的對帳**同一組**（`services.md:58`），且排隊不取消
    @step 檢視兩支的 permissions | **逐字**為 `{contents: read}`（ADR-0006 的 IAM 面向）
    @pass **第三步鎖的是一項刻意的偏離**：本單元 nfr 的 P-2 裁定「自成第三組」，而
          `open-items.md` 的 N:C-2（Critical）判定那推翻了已過 gate 的 `services.md:58`，
          處置逐字為「需 ADR 或回退」而本 intent 沒有為它開 ADR。這條斷言讓「改回
          第三組」變成一個會紅燈的動作，而不是靜默漂移——ADR 落地後同時改這兩處即可
    @story S-6
    @api n/a
    """
    outer = outer_doc()
    on = outer.get(True) or outer.get("on")
    check("S-C：外層的觸發集合", sorted(on.keys()), ["schedule", "workflow_dispatch"])
    conc = outer.get("concurrency") or {}
    reconcile_conc = yaml.safe_load(
        RECONCILE_OUTER_YML.read_text(encoding="utf-8")).get("concurrency") or {}
    check_true("`services.md:58`：與 S-B（對帳）同一組",
               conc.get("group") == reconcile_conc.get("group"),
               f"本單元={conc.get('group')!r} 對帳={reconcile_conc.get('group')!r}")
    check("排隊不取消", conc.get("cancel-in-progress"), False)

    impl = impl_doc()
    # ADR-0006 的 IAM 面向：本 workflow 自己的 GITHUB_TOKEN **只要讀**，所有寫入（狀態
    # 檔、push、PR、通報 issue）都走 sync_token。逐字比對整個 mapping 而不是只看
    # contents 一欄——多加一個 scope 與把 contents 提成 write 是同一類的擴權，兩者都必須
    # 是會紅燈的動作。reviewer 實測把 impl 提成 `contents: write` 時全套測試無感。
    for label, doc in (("外層", outer), ("impl", impl)):
        check(f"ADR-0006 IAM：{label} 的 GITHUB_TOKEN 只讀", doc.get("permissions"),
              {"contents": "read"})
    impl_on = impl.get(True) or impl.get("on")
    check_true("ADR-A10：impl 只認 workflow_call", list(impl_on.keys()) == ["workflow_call"], str(impl_on))
    check("ADR-A10：input 集合", sorted(impl_on["workflow_call"]["inputs"].keys()),
          ["project_number", "project_owner", "record_root", "reverse_branch_prefix",
           "stage_field_name", "trunk_ref"])
    check("A:M-5：trunk_ref 必填、無預設",
          impl_on["workflow_call"]["inputs"]["trunk_ref"].get("required"), True)
    check_true("A:M-5：trunk_ref 不得有預設值（給預設等於在本檔替另一個 repo 的主幹命名）",
               "default" not in impl_on["workflow_call"]["inputs"]["trunk_ref"], "")
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


def test_checkout_pins_the_trunk_ref() -> None:
    """@purpose A:M-5（U-7 的 R-7.1 對本單元的同一條規則）：`actions/checkout` **必須明訂 ref**。`schedule` 只在預設分支（本 repo 為 `main`）觸發，而 `main` 落後於 `ut`——不釘就會拿**過期的比對基準**去比看板，於是在沒有任何人為變更的情況下開出反向 PR，且**不會有任何錯誤**。
    @given impl 的 checkout step
    @step 解析 YAML | **前提**：impl 確實有一個 checkout step
    @step 檢視 with | ref 為 inputs.trunk_ref、token 為 sync_token、persist-credentials 為 true
    @step 檢視薄外層 | trunk_ref 實際傳入 `ut`
    @pass 這是本單元最危險的靜默失真——症狀是每天增生 PR，而每一則看起來都合理
    @story S-6
    @api n/a
    """
    doc = impl_doc()
    steps = doc["jobs"]["reverse"]["steps"]
    co = [s for s in steps if isinstance(s.get("uses"), str) and s["uses"].startswith("actions/checkout")]
    check_true("**前提**：impl 確實有一個 checkout step", len(co) == 1, str(steps))
    with_ = co[0].get("with") or {}
    check("ref 釘在 trunk_ref 上", with_.get("ref"), "${{ inputs.trunk_ref }}")
    check("U-4：checkout 用同步身分", with_.get("token"), "${{ secrets.sync_token }}")
    check("U-4：persist-credentials 必須為 true（否則 push 會認證失敗）",
          with_.get("persist-credentials"), True)
    outer = outer_doc()
    check("薄外層傳入整合主幹", outer["jobs"]["reverse"]["with"]["trunk_ref"], TRUNK_REF)


def test_impl_hardcodes_nothing() -> None:
    """@purpose [ad:ADR-A10]：Project 編號、擁有者、record 根目錄、主幹名、分支前綴一律為 input，**不得寫死**在 impl 的編排腳本裡。
    @given impl 的編排腳本全文
    @step grep 正式看板編號、擁有者 | 零命中
    @step 檢視取值方式 | 主幹名、record 根、分支前綴皆來自環境變數
    @pass 抄到另一個 repo 只需改薄外層
    @story S-6
    @api n/a
    """
    for literal in ("opendiamonds", "projects/16"):
        check(f"編排腳本的程式碼不含寫死的 {literal}", literal in CODE, False)
    for env_name in ("AIDLC_TRUNK_REF", "AIDLC_RECORD_ROOT", "AIDLC_BRANCH_PREFIX"):
        check_true(f"{env_name} 來自 input", env_name in CODE, "")
    text = IMPL_YML.read_text(encoding="utf-8")
    check_true("project_number 是 input 不是字面", "inputs.project_number" in text, "")


STEPS = [
    # R-1 群：何時開 PR
    test_r1_2_unchanged_hash_opens_no_pr_and_writes_nothing,
    test_r4c_parse_null_is_skipped_not_a_human_change,
    test_r1_3_changed_hash_writes_pending_reverse_and_opens_one_pr,
    test_unbound_intent_is_skipped,
    # R-2 群：PR 的內容邊界
    test_r2_1_diff_never_contains_aidlc_state_md,
    test_r2_3_branch_name_and_label,
    test_r1_5_never_pushes_to_the_trunk,
    # E-2
    test_e2_two_changed_intents_produce_two_prs,
    # R-6.1
    test_r6_1_open_pr_suppresses_a_second_one,
    test_r6_1_uses_the_live_query_not_the_stored_field,
    test_r6_1_query_argv_is_complete,
    test_r6_1_only_labelled_prs_suppress,
    test_r6_1_matches_intent_ids_whole_line_not_by_prefix,
    test_q3_over_suppression_counterexample_pr_with_x_but_not_y,
    test_r6_1_query_failure_is_fail_closed,
    # R-6.3 的三種結局 ＋ 邊界
    test_r6_3_outcome_1_pr_created_no_branch_deletion,
    test_r6_3_outcome_2_pr_fails_branch_deleted,
    test_r6_3_outcome_3_pr_fails_and_delete_fails_leaves_an_orphan,
    test_r6_3_does_not_delete_when_the_push_itself_failed,
    test_commit_and_push_external_error_is_red_and_notified,
    # 其餘錯誤分支（Q2=A）
    test_q2_read_item_failure_notifies_and_does_not_abort_the_round,
    test_f5_actions_bash_e_does_not_abort_the_round,
    test_read_sync_state_failure_is_red_notified_and_reads_no_board,
    test_write_sync_state_failure_is_red_notified_and_pushes_nothing,
    test_registry_missing_is_fail_closed_and_notified,
    test_missing_record_dir_is_loud_but_not_fatal,
    test_head_sha_failure_aborts_the_round,
    test_missing_composite_action_is_fail_closed,
    test_notify_failure_is_surfaced_not_swallowed,
    test_round_at_is_taken_once_and_used_everywhere,
    # label
    test_label_is_created_once_per_round_when_absent,
    test_existing_label_is_not_recreated,
    test_label_failure_goes_down_the_r6_3_cleanup_path,
    test_label_create_race_is_not_a_failure,
    # R-6.2
    test_r6_2_pending_reverse_is_never_written_back_to_null,
    # 常數推導與單一雜湊路徑
    test_q1_reverse_pr_label_is_derived_from_u6_not_copied,
    test_sync_marker_is_derived_from_record_sh,
    test_adr0015_s10_hash_has_exactly_one_computation_path,
    # 報告與 SEC
    test_report_holds_only_ids_and_numbers,
    test_report_renders_empty_lists_as_none,
    test_pr_body_states_the_close_path_honestly,
    test_pr_body_states_the_write_scope_and_the_per_intent_pause,
    # 結構斷言
    test_cron_does_not_collide_with_any_existing_schedule,
    test_structure_triggers_concurrency_and_workflow_call,
    test_checkout_pins_the_trunk_ref,
    test_impl_hardcodes_nothing,
]


def main() -> int:
    if not shutil.which("jq"):
        sys.stderr.write("找不到 jq。受測腳本用它解析 registry 與 SyncState。\n")
        return 2
    print(f"受測物：{IMPL_YML.relative_to(REPO_ROOT)} 的 id: reverse（{len(SCRIPT.splitlines())} 行）")
    print(f"同步標記：{MARKER!r}（由 record.sh 推導）")
    print(f"反向 PR label：{REVERSE_LABEL!r}（由 U-6 的 impl 推導，[Q1=A]）\n")
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
