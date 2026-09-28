#!/usr/bin/env python3
"""stub 斷言 runner — U-5「通報」composite action（離線層）。

用法：
    python3 .github/actions/aidlc-sync-notify/run-stub-tests.py

非零 exit 表失敗。

**完全離線**：以 PATH shim 偽裝 `gh`（見 GH_SHIM），notify.sh 的每一次 API 呼叫都被
攔下並記錄到 calls.jsonl。與 U-3 的 route 表 shim 不同，本檔的 shim 是**有狀態**的
——它以一份暫存 JSON 當 issue 存放區，實作 `issue list／create／comment／edit／
close／view` 與 `label list／create` 的最小子集。理由：本單元的行為是**生命週期**
（開了之後再呼叫一次會追加而不是再開一則），route 表回放不出「第二次呼叫看到的是
第一次的結果」，而 [ug:unit-of-work.md] 的 U-5 完成判準（同一鍵連續兩輪失敗後開啟中
issue 數為 1、comment 數 +1）正是這種形狀。

notify.sh 本身是**真的**（不偽裝）：鍵的比對、標題計數、清洗、分流全部走實際路徑。
唯一被替換的是 GitHub 的位置。真實 GitHub 的半邊在 run-live-tests.py。

本檔最重要的兩條 fixture 是 R-2.1 的兩面：**標題被改過仍命中**、**標題像但內文鍵
不同則不命中也不關閉**。它們鎖的是本單元僅有的破壞性動作的判準——判準一鬆，後果是
關掉別人的 issue，而那不可自動復原（security-requirements.md SEC-1）。

規格正本：
    ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
      U-5-notifier/functional-design/business-rules.md        （R-1〜R-4 群）
      U-5-notifier/functional-design/domain-entities.md       （issue 的可搜尋形狀）
      U-5-notifier/functional-design/business-logic-model.md  （四支分流／邊界情形）
      U-5-notifier/nfr-requirements/security-requirements.md  （SEC-1／SEC-2）
      U-5-notifier/code-generation/code-generation-plan.md    （Step 6 的案例清單）
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
NOTIFY_SH = HERE / "notify.sh"
ACTION_YML = HERE / "action.yml"

BASH = os.environ.get("AIDLC_NOTIFY_BASH", "bash")

REPO = "opendiamonds/cloud-360"
LABEL = "aidlc-sync-alert"
INTENT = "aidlc-sync-test-alpha"
OTHER_INTENT = "aidlc-sync-test-beta"

FAILURE_CODES = ["ExternalError", "Rejected", "Aborted", "CannotCreate", "Failed"]
NORMAL_CODES = ["suppressed", "parked", "unparseable", "whitelisted", "undecidable"]

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


def marker(intent: str, reason: str) -> str:
    return f"<!-- aidlc-alert: intent={intent} reason={reason} -->"


def title_of(intent: str, reason: str, n: int) -> str:
    return f"[aidlc-sync] {intent} / {reason} (×{n})"


# ==========================================================================
# gh 的有狀態 PATH shim
# ==========================================================================
# state.json 是 issue 存放區：{labels: [...], issues: [...], next_number: N,
# fail_on: [{contains: [...], exit: N, stderr: "..."}]}。每次呼叫都追加一筆
# {argv} 到 calls.jsonl。fail_on 在**記錄之後、處理之前**比對，所以「失敗的那一次
# 呼叫」也在 calls.jsonl 裡（R-4 的斷言要數 create 的次數，漏記會讓斷言變寬鬆）。
# 無對應處理器 → exit 9（測試會大聲失敗，不會靜默打到真實網路——PATH 上的 gh 就是
# 這支 shim）。

GH_SHIM = r'''#!/usr/bin/env python3
import json, os, pathlib, sys

d = pathlib.Path(os.environ["AIDLC_STUB_DIR"])
argv = sys.argv[1:]
hay = " ".join(argv)
with open(d / "calls.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps({"argv": argv}) + "\n")

state = json.loads((d / "state.json").read_text())


def save():
    (d / "state.json").write_text(json.dumps(state))


def die(msg, code=1):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


for rule in state.get("fail_on", []):
    if all(sub in hay for sub in rule["contains"]):
        sys.stderr.write(rule.get("stderr", "stub-gh: injected failure\n"))
        sys.exit(rule.get("exit", 1))


def flag(name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def flag_all(name):
    return [argv[i + 1] for i, a in enumerate(argv) if a == name and i + 1 < len(argv)]


def find(num):
    for it in state["issues"]:
        if it["number"] == num:
            return it
    die("HTTP 404: Could not resolve to an Issue with the number of %d." % num)


def project(it, fields):
    out = {}
    for f in fields:
        if f == "comments":
            out[f] = it.get("comments", [])
        else:
            out[f] = it.get(f)
    return out


head = argv[:2]

if head == ["label", "list"]:
    print(json.dumps([{"name": n} for n in state["labels"]]))
elif head == ["label", "create"]:
    name = argv[2]
    if name in state["labels"]:
        die("HTTP 422: Validation Failed (label already exists)")
    state["labels"].append(name)
    save()
    print("https://github.com/%s/labels/%s" % (state["repo"], name))
elif head == ["issue", "list"]:
    lab = flag("--label")
    st = flag("--state", "open")
    fields = [f for f in (flag("--json") or "").split(",") if f]
    out = []
    for it in state["issues"]:
        if lab is not None and lab not in it.get("labels", []):
            continue
        if st != "all" and it.get("state") != st:
            continue
        out.append(project(it, fields))
    print(json.dumps(out))
elif head == ["issue", "create"]:
    labels = flag_all("--label")
    for lab in labels:
        if lab not in state["labels"]:
            die("HTTP 422: could not add label: '%s' not found" % lab)
    num = state["next_number"]
    state["next_number"] = num + 1
    state["issues"].append({
        "number": num, "title": flag("--title", ""), "body": flag("--body", ""),
        "state": "open", "labels": labels, "comments": [], "createdAt": flag("--createdAt", ""),
    })
    save()
    print("https://github.com/%s/issues/%d" % (state["repo"], num))
elif head == ["issue", "comment"]:
    it = find(int(argv[2]))
    it.setdefault("comments", []).append({"body": flag("--body", "")})
    save()
    print("https://github.com/%s/issues/%d#issuecomment-1" % (state["repo"], it["number"]))
elif head == ["issue", "edit"]:
    it = find(int(argv[2]))
    t = flag("--title")
    if t is not None:
        it["title"] = t
    b = flag("--body")
    if b is not None:
        it["body"] = b
    save()
    print("https://github.com/%s/issues/%d" % (state["repo"], it["number"]))
elif head == ["issue", "close"]:
    it = find(int(argv[2]))
    c = flag("--comment")
    if c is not None:
        it.setdefault("comments", []).append({"body": c})
    it["state"] = "closed"
    save()
    print("Closed issue #%d" % it["number"])
elif head == ["issue", "view"]:
    it = find(int(argv[2]))
    fields = [f for f in (flag("--json") or "").split(",") if f]
    print(json.dumps(project(it, fields)))
else:
    die("stub-gh: no handler for: " + hay[:2000], 9)
'''


class Result:
    def __init__(self, proc, stub_dir: pathlib.Path, gh_output_file: pathlib.Path):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.gh_output = gh_output_file.read_text() if gh_output_file.exists() else ""
        self.state = json.loads((stub_dir / "state.json").read_text())
        self.calls = []
        calls_file = stub_dir / "calls.jsonl"
        if calls_file.exists():
            for line in calls_file.read_text().splitlines():
                if line.strip():
                    self.calls.append(json.loads(line))
        self.outputs: dict[str, str] = {}
        for line in self.stdout.splitlines():
            if "=" in line:
                name, _, value = line.partition("=")
                self.outputs[name] = value

    def calls_matching(self, *subs: str) -> list[dict]:
        out = []
        for call in self.calls:
            hay = " ".join(call["argv"])
            if all(s in hay for s in subs):
                out.append(call)
        return out

    def issue(self, number: int) -> dict:
        for it in self.state["issues"]:
            if it["number"] == number:
                return it
        raise AssertionError(f"state 內找不到 issue #{number}")

    def open_issues_with_marker(self, mk: str) -> list[dict]:
        return [it for it in self.state["issues"]
                if it["state"] == "open" and (it.get("body") or "").split("\n")[0] == mk]


class Stub:
    """一個暫存目錄：state.json（issue 存放區）＋ calls.jsonl ＋ gh shim。

    同一個 Stub 可以連續跑多次 notify.sh——狀態會累積，這正是驗證生命週期
    （完成判準：連續兩輪）所需要的。
    """

    def __init__(self, issues=None, labels=None, next_number=100, fail_on=None):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-notify-stub-"))
        self.stub_dir = self.root / "stub"
        self.stub_dir.mkdir()
        (self.stub_dir / "state.json").write_text(json.dumps({
            "repo": REPO,
            "labels": list(labels if labels is not None else [LABEL, "aidlc"]),
            "issues": list(issues or []),
            "next_number": next_number,
            "fail_on": list(fail_on or []),
        }))
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        exe = bin_dir / "gh"
        exe.write_text(GH_SHIM)
        exe.chmod(0o755)
        self.bin_dir = bin_dir

    def run(self, operation: str, env=None, argv=None, reset_calls: bool = True) -> Result:
        if reset_calls:
            (self.stub_dir / "calls.jsonl").unlink(missing_ok=True)
        gh_output_file = self.root / f"github_output_{operation}"
        gh_output_file.unlink(missing_ok=True)

        full_env = dict(os.environ)
        for key in list(full_env):
            if key.startswith("AIDLC_"):
                del full_env[key]
        full_env["GITHUB_REPOSITORY"] = REPO
        full_env.update(env or {})
        full_env["AIDLC_OPERATION"] = operation
        full_env["PATH"] = f"{self.bin_dir}:{full_env['PATH']}"
        full_env["AIDLC_STUB_DIR"] = str(self.stub_dir)
        full_env["GITHUB_OUTPUT"] = str(gh_output_file)

        proc = subprocess.run([BASH, str(NOTIFY_SH)] + (argv or []),
                              capture_output=True, text=True, env=full_env)
        return Result(proc, self.stub_dir, gh_output_file)

    def run_raw(self, argv: "list[str | bytes]") -> subprocess.CompletedProcess:
        """跑一個診斷子命令並回傳**未解碼的位元組**。

        Result 走的是 text=True，Python 會用 UTF-8 嚴格模式解碼 stdout——而
        truncate 診斷子命令的整個測試目的就是「輸出會不會是無效 UTF-8」，交給
        Python 先解碼一次等於把要驗的東西吃掉（無效輸入會變成 UnicodeDecodeError
        或替代字元，兩者都讓斷言看不見真正的位元組）。故本方法不解碼。
        """
        full_env = dict(os.environ)
        for key in list(full_env):
            if key.startswith("AIDLC_"):
                del full_env[key]
        full_env.pop("GITHUB_OUTPUT", None)
        full_env["GITHUB_REPOSITORY"] = REPO
        full_env["PATH"] = f"{self.bin_dir}:{full_env['PATH']}"
        full_env["AIDLC_STUB_DIR"] = str(self.stub_dir)
        # argv 允許夾帶 bytes：畸形（非 UTF-8）的測試輸入沒有 str 表示法，而
        # POSIX 上 subprocess 接受 bytes 參數並原樣交給 execve（本站實測）。
        head: "list[str | bytes]" = [BASH, str(NOTIFY_SH)]
        return subprocess.run(head + argv, capture_output=True, env=full_env)

    def notify(self, reason=FAILURE_CODES[0], intent=INTENT, stage="forward-sync",
               detail="看板寫入失敗", **kw) -> Result:
        env = {"AIDLC_INTENT_ID": intent, "AIDLC_REASON_CODE": reason,
               "AIDLC_STAGE": stage, "AIDLC_DETAIL": detail}
        env.update(kw.pop("env", {}))
        return self.run("notify", env=env, **kw)

    def resolve(self, keys: str, **kw) -> Result:
        env = {"AIDLC_KEYS": keys}
        env.update(kw.pop("env", {}))
        return self.run("resolve_if_open", env=env, **kw)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def alert_issue(number: int, intent: str, reason: str, count: int = 1,
                title: str | None = None, state: str = "open",
                comments: int = 0, created: str = "2026-09-01T00:00:00Z",
                body_first_line: str | None = None) -> dict:
    first = marker(intent, reason) if body_first_line is None else body_first_line
    return {
        "number": number,
        "title": title if title is not None else title_of(intent, reason, count),
        "body": first + "\n\nAI-DLC 同步機制回報一則需要人處理的失敗。\n",
        "state": state,
        "labels": [LABEL],
        "comments": [{"body": f"既有 comment {i}"} for i in range(comments)],
        "createdAt": created,
    }


# ==========================================================================
# notify：四支分流（business-rules.md R-2 群）
# ==========================================================================

def test_create_when_no_open_alert_matches() -> None:
    """@purpose 同鍵零筆時開一則新的通報 issue，且內文第一行就是機器可讀鍵、內含 [req:FR-E3] 的三要素——鍵不在第一行則下一輪找不到它，三要素缺一則人拿不到定位資訊。
    @given 存放區有一則**別的鍵**的開啟中通報 issue（證明過濾真的在比對鍵，不是「只要有 issue 就算命中」）
    @step 以 (aidlc-sync-test-alpha, ExternalError) 呼叫 notify | action=created、result=ok、count=1、closed=0
    @step 檢查新 issue 的內文第一行 | 逐字等於 <!-- aidlc-alert: intent=… reason=… -->
    @step 檢查新 issue 的內文其餘部分 | 同時含 intent 識別字、stage 標識、ISO 8601 時間戳
    @step 數 gh issue create 的呼叫次數 | 恰好 1 次
    @pass 以上全部成立，且新 issue 的標題為 [aidlc-sync] <intent> / <reason> (×1)
    @api gh issue list --label --state open --json number,title,body
    @api gh issue create --title --body --label
    @story S-8
    """
    stub = Stub(issues=[alert_issue(41, OTHER_INTENT, "Rejected")])
    try:
        r = stub.notify(detail="Projects v2 mutation 回 502")
        check("created：rc", r.rc, 0)
        check("created：result", r.outputs.get("result"), "ok")
        check("created：action", r.outputs.get("action"), "created")
        check("created：count", r.outputs.get("count"), "1")
        check("created：closed", r.outputs.get("closed"), "0")
        check("created：closed_numbers 為空", r.outputs.get("closed_numbers"), "")
        num = int(r.outputs["issue_number"])
        it = r.issue(num)
        check("created：內文第一行是機器可讀鍵",
              it["body"].split("\n")[0], marker(INTENT, FAILURE_CODES[0]))
        check("created：標題", it["title"], title_of(INTENT, FAILURE_CODES[0], 1))
        body = it["body"]
        check_true("FR-E3：內文含 intent 識別字", INTENT in body, body[:300])
        check_true("FR-E3：內文含 stage 標識", "forward-sync" in body, body[:300])
        check_true("FR-E3：內文含 ISO 8601 時間戳",
                   re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", body) is not None, body[:300])
        check_true("created：detail 有進內文", "502" in body, body[:300])
        check("created：gh issue create 恰好一次", len(r.calls_matching("issue create")), 1)
        check("created：別的鍵那則沒被動到", r.issue(41)["state"], "open")
        check("created：別的鍵那則沒被留言", len(r.issue(41)["comments"]), 0)
    finally:
        stub.close()


def test_comment_and_increment_when_exactly_one() -> None:
    """@purpose 同鍵一筆時追加 comment 並把標題計數 +1，而**不是**再開一則——這是 ADR-A8 「不重複叫」的主要路徑。
    @given 存放區有一則同鍵、標題為 (×1) 的開啟中通報 issue
    @step 呼叫 notify | action=commented、issue_number 為既有那一則、count=2
    @step 檢查該 issue | comment 數由 0 變 1，標題變成 (×2)
    @step 數 gh issue create 的呼叫次數 | **零次**
    @pass 以上全部成立，且開啟中的同鍵 issue 仍然只有一則
    @api gh issue list --label --state open --json number,title,body
    @api gh issue comment --body
    @api gh issue edit --title
    @story S-8
    """
    stub = Stub(issues=[alert_issue(41, INTENT, FAILURE_CODES[0], count=1)])
    try:
        r = stub.notify(detail="第二次也失敗")
        check("commented：rc", r.rc, 0)
        check("commented：action", r.outputs.get("action"), "commented")
        check("commented：issue_number", r.outputs.get("issue_number"), "41")
        check("commented：count", r.outputs.get("count"), "2")
        it = r.issue(41)
        check("commented：comment 數 +1", len(it["comments"]), 1)
        check("commented：標題計數 +1", it["title"], title_of(INTENT, FAILURE_CODES[0], 2))
        check_true("commented：comment 含本輪細節", "第二次也失敗" in it["comments"][0]["body"],
                   it["comments"][0]["body"])
        check("commented：零次 create", len(r.calls_matching("issue create")), 0)
        check("commented：開啟中同鍵仍只有一則",
              len(r.open_issues_with_marker(marker(INTENT, FAILURE_CODES[0]))), 1)
    finally:
        stub.close()


def test_deduplicate_keeps_lowest_number_not_earliest_created() -> None:
    """@purpose 同鍵多筆時取**編號最小者**保留、其餘關閉（R-2.2）——編號單調遞增且不受時區或 API 回傳格式影響，建立時間不是。fixture 刻意讓較新編號的 createdAt 較早，兩種判準會給出不同答案。
    @given 三則同鍵開啟中 issue：#12（createdAt 最晚）、#30（createdAt 最早）、#45；另有一則別的鍵的 issue
    @step 呼叫 notify | issue_number=12（不是 createdAt 最早的 #30）、action=deduplicated
    @step 檢查 #30 與 #45 | 兩者皆 state=closed，且各有一則含「與 #12 重複」的 comment
    @step 檢查 notify.sh 向 gh issue list 要求的 --json 欄位 | **不含 createdAt**（結構上就拿不到建立時間）
    @step 檢查別的鍵那則 | 未被關閉、未被留言
    @pass closed_numbers 為 "30 45"、closed=2，且 #12 收到 comment、標題計數 +1
    @api gh issue list --label --state open --json number,title,body
    @api gh issue comment --body
    @api gh issue edit --title
    @api gh issue close --comment
    @story S-8
    """
    stub = Stub(issues=[
        alert_issue(12, INTENT, FAILURE_CODES[0], count=1, created="2026-09-03T00:00:00Z"),
        alert_issue(30, INTENT, FAILURE_CODES[0], count=1, created="2026-09-01T00:00:00Z"),
        alert_issue(45, INTENT, FAILURE_CODES[0], count=1, created="2026-09-02T00:00:00Z"),
        alert_issue(50, OTHER_INTENT, FAILURE_CODES[0]),
    ])
    try:
        r = stub.notify()
        check("dedup：rc", r.rc, 0)
        check("dedup：action", r.outputs.get("action"), "deduplicated")
        check("dedup：保留編號最小者", r.outputs.get("issue_number"), "12")
        check("dedup：closed_numbers", r.outputs.get("closed_numbers"), "30 45")
        check("dedup：closed", r.outputs.get("closed"), "2")
        check("dedup：#12 仍開啟", r.issue(12)["state"], "open")
        check("dedup：#12 收到 comment", len(r.issue(12)["comments"]), 1)
        check("dedup：#12 標題計數 +1", r.issue(12)["title"], title_of(INTENT, FAILURE_CODES[0], 2))
        for n in (30, 45):
            check(f"dedup：#{n} 已關閉", r.issue(n)["state"], "closed")
            bodies = " ".join(c["body"] for c in r.issue(n)["comments"])
            check_true(f"dedup：#{n} 的關閉 comment 註明與 #12 重複",
                       "重複" in bodies and "#12" in bodies, bodies)
        check("dedup：別的鍵未被關閉", r.issue(50)["state"], "open")
        check("dedup：別的鍵未被留言", len(r.issue(50)["comments"]), 0)
        list_calls = r.calls_matching("issue list")
        check_true("dedup：至少有一次 issue list", len(list_calls) >= 1, str(r.calls))
        for call in list_calls:
            argv = call["argv"]
            fields = argv[argv.index("--json") + 1] if "--json" in argv else ""
            check_true("R-2.2：--json 不要 createdAt（結構上拿不到建立時間）",
                       "createdAt" not in fields and "created" not in fields, fields)
    finally:
        stub.close()


# ==========================================================================
# R-2.1：比對只用內文首行的鍵，逐字相符（兩面）
# ==========================================================================

def test_edited_title_still_matches_by_body_key() -> None:
    """@purpose 標題被人編輯過**仍然命中**——標題同時當摘要與搜尋鍵時，任何一次人為編輯都會讓機制以為沒開過而再開一則（domain-entities.md 新增內文鍵的理由）。
    @given 一則同鍵 issue，標題被改成完全不像通報格式的文字，內文第一行的鍵不變；它已有 3 則既有 comment
    @step 呼叫 notify | action=commented（不是 created）
    @step 數 gh issue create | 零次
    @step 檢查 count | 標題解析不出 ×N，改以既有 comment 數（3）＋1 重算 ⇒ 4
    @step 檢查標題 | 被改回 [aidlc-sync] <intent> / <reason> (×4)
    @pass 以上全部成立
    @api gh issue list --label --state open --json number,title,body
    @api gh issue view --json comments
    @api gh issue comment --body
    @api gh issue edit --title
    @story S-8
    """
    stub = Stub(issues=[alert_issue(
        41, INTENT, FAILURE_CODES[0], title="有人把標題改成這樣了", comments=3)])
    try:
        r = stub.notify()
        check("edited-title：rc", r.rc, 0)
        check("edited-title：仍然命中", r.outputs.get("action"), "commented")
        check("edited-title：零次 create", len(r.calls_matching("issue create")), 0)
        check("edited-title：以既有 comment 數重算計數", r.outputs.get("count"), "4")
        check("edited-title：標題被寫回正規形式",
              r.issue(41)["title"], title_of(INTENT, FAILURE_CODES[0], 4))
        check("edited-title：有讀 comment 數", len(r.calls_matching("issue view", "comments")), 1)
    finally:
        stub.close()


def test_titlelike_decoy_with_different_key_is_never_touched() -> None:
    """@purpose 標題長得一模一樣但內文鍵不同的 issue **不得**被命中、更不得被關閉（R-2.1／SEC-1）——標題可被任何有 issue 權限的人編輯，以標題比對時一次複製貼上就會讓機制關掉別人的 issue，而那不可自動復原。
    @given 一則誘餌 issue：標題逐字等於本鍵的通報標題，但內文第一行是**別的 intent** 的鍵
    @step 呼叫 notify | action=created（誘餌不算命中，所以開了新的）
    @step 檢查誘餌 | state 仍為 open、comment 數仍為 0、標題未被改寫
    @step 數 gh issue close 的呼叫次數 | 零次
    @pass 以上全部成立
    @api gh issue list --label --state open --json number,title,body
    @api gh issue create --title --body --label
    @story S-8
    """
    decoy_title = title_of(INTENT, FAILURE_CODES[0], 7)
    stub = Stub(issues=[alert_issue(
        41, OTHER_INTENT, FAILURE_CODES[0], title=decoy_title)])
    try:
        r = stub.notify()
        check("decoy：rc", r.rc, 0)
        check("decoy：不算命中，開了新的", r.outputs.get("action"), "created")
        check("decoy：誘餌仍開啟", r.issue(41)["state"], "open")
        check("decoy：誘餌未被留言", len(r.issue(41)["comments"]), 0)
        check("decoy：誘餌標題未被改寫", r.issue(41)["title"], decoy_title)
        check("decoy：零次 close", len(r.calls_matching("issue close")), 0)
    finally:
        stub.close()


# ==========================================================================
# R-1：五種正常判斷碼根本不該呼叫 notify
# ==========================================================================

def test_normal_reason_codes_rejected_with_zero_api_calls() -> None:
    """@purpose suppressed／parked／unparseable／whitelisted／undecidable 屬機制的正常判斷，不通報也不紅燈（R-1）；靜默接受它們等於把呼叫端的 bug 變成一則假告警，而假告警比沒有告警更難發現。
    @given 存放區有一則同鍵的開啟中 issue（若誤走通報路徑會留下痕跡）
    @step 對五個正常判斷碼各呼叫一次 notify | 每次都 exit 2
    @step 檢查每次的 API 呼叫紀錄 | **零次**（連 issue list 都沒發）
    @step 檢查 stdout | 不寫 result（介面誤用不是判定結果）
    @pass 五個碼全部如此，且 stderr 說得出「屬機制的正常判斷」
    @story S-8
    """
    for code in NORMAL_CODES:
        stub = Stub(issues=[alert_issue(41, INTENT, code)])
        try:
            r = stub.notify(reason=code)
            check(f"R-1：{code} exit 2", r.rc, 2)
            check(f"R-1：{code} 零次 API 呼叫", len(r.calls), 0)
            check(f"R-1：{code} 不寫 result", r.outputs.get("result"), None)
            check_true(f"R-1：{code} 的訊息說得出理由", "正常判斷" in r.stderr, r.stderr)
        finally:
            stub.close()


def test_interface_misuse_exits_2_with_zero_api_calls() -> None:
    """@purpose 介面誤用（未知 reason_code、缺 intent_id／stage、intent_id 含會破壞機器可讀鍵的字元）一律 exit 2 且零 API 呼叫——這不是判定結果，是呼叫端 bug，不該在 GitHub 上留下任何痕跡。
    @given 空的 issue 存放區
    @step 未知 reason_code | exit 2、零呼叫
    @step 空的 intent_id | exit 2、零呼叫
    @step intent_id 含空白 | exit 2、零呼叫
    @step intent_id 含 <（會提前關掉內文的 HTML 註解鍵） | exit 2、零呼叫
    @step 缺 stage（FR-E3 三要素之一） | exit 2、零呼叫
    @step 未知 operation | exit 2、零呼叫
    @pass 六種誤用全部 exit 2 且完全沒有碰到 GitHub
    @story S-8
    """
    cases = [
        ("未知 reason_code", dict(reason="Boom")),
        ("空 intent_id", dict(intent="")),
        ("intent_id 含空白", dict(intent="aidlc-sync-test a")),
        ("intent_id 含 <", dict(intent="aidlc-sync-test-<x")),
        ("缺 stage", dict(stage="")),
    ]
    for label, kw in cases:
        stub = Stub()
        try:
            r = stub.notify(**kw)
            check(f"介面誤用（{label}）：exit 2", r.rc, 2)
            check(f"介面誤用（{label}）：零次 API 呼叫", len(r.calls), 0)
        finally:
            stub.close()
    stub = Stub()
    try:
        r = stub.run("push_commit")
        check("未知 operation：exit 2", r.rc, 2)
        check("未知 operation：零次 API 呼叫", len(r.calls), 0)
        check_true("未知 operation：訊息列出有效值",
                   "notify" in r.stderr and "resolve_if_open" in r.stderr, r.stderr)
    finally:
        stub.close()


# ==========================================================================
# resolve_if_open（R-3 群，批次鍵）
# ==========================================================================

def test_resolve_closes_only_keys_in_the_set() -> None:
    """@purpose 只關閉鍵**在 keys 內**的通報 issue；鍵不在 keys 內的一律不動（R-3.2）——那一類涵蓋「本輪仍失敗」與「不屬本輪」兩種，關掉它就是關掉一則仍然成立的告警。
    @given 四則開啟中通報 issue：alpha/ExternalError、alpha/Rejected、beta/ExternalError，以及一則內文首行不是鍵的雜訊 issue
    @step 以 keys = "alpha/ExternalError\\nbeta/ExternalError" 呼叫 resolve_if_open | closed=2、closed_numbers 為那兩則
    @step 檢查 alpha/Rejected（本輪仍失敗，不在 keys 內） | 仍 open、零 comment
    @step 檢查雜訊 issue（帶同一個 label 但沒有機器可讀鍵） | 仍 open、零 comment
    @step 檢查被關閉者的 comment | 含「本輪未再發生」
    @pass 以上全部成立，rc=0
    @api gh issue list --label --state open --json number,body
    @api gh issue close --comment
    @story S-8
    """
    stub = Stub(issues=[
        alert_issue(11, INTENT, "ExternalError"),
        alert_issue(12, INTENT, "Rejected"),
        alert_issue(13, OTHER_INTENT, "ExternalError"),
        alert_issue(14, INTENT, "ExternalError", body_first_line="有人手動開的 issue，沒有鍵"),
    ])
    try:
        r = stub.resolve(f"{INTENT}/ExternalError\n{OTHER_INTENT}/ExternalError\n")
        check("resolve：rc", r.rc, 0)
        check("resolve：result", r.outputs.get("result"), "ok")
        check("resolve：closed", r.outputs.get("closed"), "2")
        check("resolve：closed_numbers", r.outputs.get("closed_numbers"), "11 13")
        for n in (11, 13):
            check(f"resolve：#{n} 已關閉", r.issue(n)["state"], "closed")
            bodies = " ".join(c["body"] for c in r.issue(n)["comments"])
            check_true(f"resolve：#{n} 的 comment 說明本輪未再發生",
                       "本輪未再發生" in bodies, bodies)
        check("R-3.2：仍失敗的鍵不動（#12 仍開啟）", r.issue(12)["state"], "open")
        check("R-3.2：仍失敗的鍵不動（#12 零 comment）", len(r.issue(12)["comments"]), 0)
        check("R-3.2：沒有機器可讀鍵的 issue 不動（#14 仍開啟）", r.issue(14)["state"], "open")
        check("R-3.2：沒有機器可讀鍵的 issue 不動（#14 零 comment）",
              len(r.issue(14)["comments"]), 0)
    finally:
        stub.close()


def test_resolve_batch_issues_exactly_one_list_call() -> None:
    """@purpose 批次鍵的整個理由：n 個鍵仍然只發**一次**列舉查詢（[Q2=A]）。被否決的 [Q2=B] 在 6 個 intent × 5 個 reason_code 下是 30 次額外呼叫，而 [req:FR-I4] 的單次操作上限是已知未定值。
    @given 三則開啟中通報 issue，鍵各不相同
    @step 以三個鍵一次呼叫 resolve_if_open | closed=3
    @step 數 gh issue list 的呼叫次數 | 恰好 1 次
    @pass 兩者皆成立
    @api gh issue list --label --state open --json number,body
    @api gh issue close --comment
    @story S-8
    """
    stub = Stub(issues=[
        alert_issue(11, INTENT, "ExternalError"),
        alert_issue(12, INTENT, "Rejected"),
        alert_issue(13, OTHER_INTENT, "Aborted"),
    ])
    try:
        r = stub.resolve(f"{INTENT}/ExternalError\n{INTENT}/Rejected\n{OTHER_INTENT}/Aborted")
        check("batch：rc", r.rc, 0)
        check("batch：closed", r.outputs.get("closed"), "3")
        check("batch：issue list 恰好一次", len(r.calls_matching("issue list")), 1)
    finally:
        stub.close()


def test_resolve_key_without_issue_is_noop() -> None:
    """@purpose keys 中沒有對應開啟中 issue 的鍵是 no-op（[ad:component-methods.md] §C-5 逐字）——U-6 的 R-6.1b 正是靠這一點才敢「對每個 intent 逐一試全部失敗值」，若不存在的鍵會出錯，那個做法就不成立。
    @given 存放區只有一則**已關閉**的同鍵 issue（已關閉者不在列舉範圍內）
    @step 以兩個都沒有開啟中 issue 的鍵呼叫 resolve_if_open | rc=0、closed=0、closed_numbers 為空
    @step 數 gh issue close 的呼叫次數 | 零次
    @pass 以上全部成立，且已關閉那則沒有被重新碰過
    @api gh issue list --label --state open --json number,body
    @story S-8
    """
    stub = Stub(issues=[alert_issue(11, INTENT, "ExternalError", state="closed")])
    try:
        r = stub.resolve(f"{INTENT}/ExternalError\n{OTHER_INTENT}/Failed")
        check("noop：rc", r.rc, 0)
        check("noop：closed", r.outputs.get("closed"), "0")
        check("noop：closed_numbers 為空", r.outputs.get("closed_numbers"), "")
        check("noop：零次 close", len(r.calls_matching("issue close")), 0)
        check("noop：已關閉那則未被重新留言", len(r.issue(11)["comments"]), 0)
    finally:
        stub.close()


def test_resolve_rejects_malformed_keys_before_any_api_call() -> None:
    """@purpose keys 的格式檢查在任何 API 呼叫**之前**——格式不合是呼叫端 bug，此時已經沒有可靠的判準決定該關哪一則，繼續往下走等於在猜。
    @given 一則開啟中通報 issue（若誤走關閉路徑會留下痕跡）
    @step keys 缺 / 分隔 | exit 2、零呼叫
    @step keys 的 reason_code 是正常判斷碼 | exit 2、零呼叫
    @step keys 的 reason_code 未知 | exit 2、零呼叫
    @step keys 全為空白 | exit 2、零呼叫
    @step 完全不給 keys | exit 2、零呼叫
    @pass 五種皆 exit 2 且 issue 仍為 open
    @story S-8
    """
    bad_keys = [
        ("缺 / 分隔", "aidlc-sync-test-alpha"),
        ("正常判斷碼", f"{INTENT}/suppressed"),
        ("未知 reason_code", f"{INTENT}/Boom"),
        ("全為空白", "   \n  \n"),
    ]
    for label, keys in bad_keys:
        stub = Stub(issues=[alert_issue(11, INTENT, "ExternalError")])
        try:
            r = stub.resolve(keys)
            check(f"keys 格式（{label}）：exit 2", r.rc, 2)
            check(f"keys 格式（{label}）：零次 API 呼叫", len(r.calls), 0)
            check(f"keys 格式（{label}）：issue 未被動到", r.issue(11)["state"], "open")
        finally:
            stub.close()
    stub = Stub(issues=[alert_issue(11, INTENT, "ExternalError")])
    try:
        r = stub.run("resolve_if_open", env={"AIDLC_KEYS": ""})
        check("keys 缺席：exit 2", r.rc, 2)
        check("keys 缺席：零次 API 呼叫", len(r.calls), 0)
    finally:
        stub.close()


def test_resolve_tolerates_indented_and_crlf_keys() -> None:
    """@purpose keys 是 YAML 多行字串的常見產物，縮排與 CRLF 是它的常態；容忍它們不會擴大破壞性動作的命中面（鍵本身仍逐字比對），但不容忍會讓呼叫端在 workflow YAML 裡踩到一個看不見的空白而靜默少關一則。
    @given 兩則開啟中通報 issue
    @step 以帶前置縮排、CRLF 行尾與空行的 keys 呼叫 resolve_if_open | closed=2
    @pass 兩則都被關閉
    @api gh issue list --label --state open --json number,body
    @api gh issue close --comment
    @story S-8
    """
    stub = Stub(issues=[
        alert_issue(11, INTENT, "ExternalError"),
        alert_issue(12, OTHER_INTENT, "Failed"),
    ])
    try:
        r = stub.resolve(f"\n  {INTENT}/ExternalError\r\n\n    {OTHER_INTENT}/Failed  \n\n")
        check("keys 容忍縮排／CRLF：rc", r.rc, 0)
        check("keys 容忍縮排／CRLF：closed", r.outputs.get("closed"), "2")
    finally:
        stub.close()


# ==========================================================================
# label 冪等建立（Plan Approval 裁決 3）
# ==========================================================================

def test_label_created_when_absent() -> None:
    """@purpose label 由本 action 冪等建立，不列為部署前置條件——repo 目前沒有 aidlc-sync-alert，若列為前置，第一次真實通報會因 --label 不存在而失敗，而那正是需要通報的時刻。
    @given 存放區的 label 清單沒有 aidlc-sync-alert（shim 的 issue create 對不存在的 label 回 422，與真實 GitHub 一致）
    @step 呼叫 notify | rc=0、action=created
    @step 數 gh label create 的呼叫次數 | 恰好 1 次
    @step 檢查建立順序 | label create 出現在 issue create 之前
    @pass 以上全部成立
    @api gh label list --json name
    @api gh label create --color --description
    @api gh issue create --title --body --label
    @story S-8
    """
    stub = Stub(labels=["aidlc"])
    try:
        r = stub.notify()
        check("label 缺席：rc", r.rc, 0)
        check("label 缺席：action", r.outputs.get("action"), "created")
        check("label 缺席：建立一次", len(r.calls_matching("label create")), 1)
        order = [" ".join(c["argv"][:2]) for c in r.calls]
        check_true("label 缺席：先建 label 再開 issue",
                   order.index("label create") < order.index("issue create"), str(order))
        check_true("label 缺席：label 已在存放區內", LABEL in r.state["labels"], str(r.state["labels"]))
    finally:
        stub.close()


def test_label_not_created_when_present_and_never_on_resolve_path() -> None:
    """@purpose label 已存在時零次 create；resolve_if_open 完全不走 label 的寫入路徑——gh issue list 對不存在的 label 回空陣列且 exit 0（本站實測），只有 issue create 需要它先存在，為讀取路徑多發一次寫入呼叫是沒有理由的權限使用。
    @given label 已存在，且存放區有一則同鍵的開啟中 issue
    @step 呼叫 notify（走 commented 分支） | 零次 label create、零次 label list（不進 0 筆分支就不需要）
    @step 呼叫 resolve_if_open | 零次 label create、零次 label list
    @pass 兩者皆成立
    @api gh issue list --label --state open --json number,title,body
    @api gh issue close --comment
    @story S-8
    """
    stub = Stub(issues=[alert_issue(11, INTENT, "ExternalError")])
    try:
        r = stub.notify()
        check("label 已存在：零次 label create", len(r.calls_matching("label create")), 0)
        check("label 已存在：commented 分支零次 label list", len(r.calls_matching("label list")), 0)
        r2 = stub.resolve(f"{INTENT}/ExternalError")
        check("resolve：零次 label create", len(r2.calls_matching("label create")), 0)
        check("resolve：零次 label list", len(r2.calls_matching("label list")), 0)
    finally:
        stub.close()


# ==========================================================================
# R-4：通報本身失敗 → 拋，不遞迴通報
# ==========================================================================

def test_api_failure_on_create_exits_1_without_recursive_notify() -> None:
    """@purpose 通報本身失敗時**拋**，且**不再開一則「通報失敗」的 issue**（R-4）——在 GitHub API 持續失敗的情況下，遞迴通報會產生無限迴圈。這是本單元唯一會拋例外的路徑。
    @given shim 對 issue create 注入 HTTP 502 失敗
    @step 呼叫 notify | exit 1
    @step 檢查 stdout | result=external_error、message 非空（供 if failure() 的步驟取用）
    @step 數 gh issue create 的呼叫次數 | 恰好 1 次（**沒有第二次**）
    @step 數 gh issue comment／close 的呼叫次數 | 各零次
    @pass 以上全部成立，且存放區沒有多出任何 issue
    @api gh issue list --label --state open --json number,title,body
    @api gh issue create --title --body --label
    @story S-8
    """
    stub = Stub(fail_on=[{"contains": ["issue create"], "exit": 1,
                          "stderr": "HTTP 502: Bad gateway (https://api.github.com/repos/x/y/issues)\n"}])
    try:
        r = stub.notify()
        check("R-4：exit 1", r.rc, 1)
        check("R-4：result", r.outputs.get("result"), "external_error")
        check_true("R-4：message 非空", bool(r.outputs.get("message")), r.stdout)
        check_true("R-4：message 帶 HTTP 狀態碼", "502" in (r.outputs.get("message") or ""),
                   r.outputs.get("message") or "")
        check("R-4：issue create 恰好一次（無第二次通報）",
              len(r.calls_matching("issue create")), 1)
        check("R-4：零次 comment", len(r.calls_matching("issue comment")), 0)
        check("R-4：零次 close", len(r.calls_matching("issue close")), 0)
        check("R-4：存放區沒有多出 issue", len(r.state["issues"]), 0)
    finally:
        stub.close()


def test_api_failure_on_list_exits_1_before_any_write() -> None:
    """@purpose 列舉失敗時不得往下走——此時「同鍵有幾筆」是未知的，繼續往下會在 0 筆分支開出重複、或在去重分支關掉不該關的 issue。
    @given shim 對 issue list 注入 HTTP 403 失敗；存放區有一則同鍵開啟中 issue
    @step 呼叫 notify | exit 1、result=external_error
    @step 數寫入類呼叫（create／comment／edit／close） | 全部零次
    @step 檢查既有 issue | 未被動到
    @pass 以上全部成立
    @api gh issue list --label --state open --json number,title,body
    @story S-8
    """
    stub = Stub(issues=[alert_issue(11, INTENT, "ExternalError")],
                fail_on=[{"contains": ["issue list"], "exit": 1,
                          "stderr": "HTTP 403: Resource not accessible by integration\n"}])
    try:
        r = stub.notify()
        check("list 失敗：exit 1", r.rc, 1)
        check("list 失敗：result", r.outputs.get("result"), "external_error")
        for sub in ("issue create", "issue comment", "issue edit", "issue close"):
            check(f"list 失敗：零次 {sub}", len(r.calls_matching(sub)), 0)
        check("list 失敗：既有 issue 未被動到", r.issue(11)["state"], "open")
        check("list 失敗：既有 issue 未被留言", len(r.issue(11)["comments"]), 0)
    finally:
        stub.close()


def test_api_failure_on_close_during_resolve_exits_1() -> None:
    """@purpose resolve_if_open 關閉失敗時非零 exit（呼叫端 U-6 的 R-6.1c：只記 log 與紅燈，不回滾已寫入看板的內容），**同樣不遞迴通報**。
    @given shim 對 issue close 注入失敗；兩則開啟中通報 issue 的鍵都在 keys 內
    @step 呼叫 resolve_if_open | exit 1、result=external_error
    @step 數 gh issue create 的呼叫次數 | 零次（不會為了「關不掉」而開一則新的通報）
    @pass 兩者皆成立
    @api gh issue list --label --state open --json number,body
    @api gh issue close --comment
    @story S-8
    """
    stub = Stub(issues=[alert_issue(11, INTENT, "ExternalError"),
                        alert_issue(12, OTHER_INTENT, "Rejected")],
                fail_on=[{"contains": ["issue close"], "exit": 1,
                          "stderr": "HTTP 410: Gone\n"}])
    try:
        r = stub.resolve(f"{INTENT}/ExternalError\n{OTHER_INTENT}/Rejected")
        check("close 失敗：exit 1", r.rc, 1)
        check("close 失敗：result", r.outputs.get("result"), "external_error")
        check("close 失敗：零次 create（不遞迴通報）", len(r.calls_matching("issue create")), 0)
    finally:
        stub.close()


# ==========================================================================
# SEC-2：detail 的防禦性清洗
# ==========================================================================

def test_detail_is_scrubbed_before_it_reaches_a_public_issue() -> None:
    """@purpose 通報 issue 在 public repo 上公開可讀（SEC-2）。呼叫端不得傳入完整回應 body 或標頭，本 action 另做一層兜底：遮罩 GitHub token 形狀字串與 Authorization 行、單行化、截斷。這層擋的是「不小心把 stderr 原樣轉貼」，擋不掉刻意洩漏。
    @given detail 內含四種 token 前綴、一行 Authorization 標頭與換行
    @step 呼叫 notify | rc=0
    @step 檢查新 issue 的內文 | 四種 token 字串都不在裡面，取而代之的是 [REDACTED]
    @step 檢查新 issue 的內文 | 不含 "Authorization: token"，含 "Authorization: [REDACTED]"
    @step 檢查 message output | 是單行（stdout 的 name=value 形式不容許換行）
    @pass 以上全部成立
    @api gh issue create --title --body --label
    @story S-8
    """
    secrets = ["ghp_AAAABBBBCCCCDDDDEEEE", "gho_1111222233334444",
               "github_pat_11ABCDE_zzzzzzzzzz", "ghs_9999888877776666"]
    detail = ("回應內容：\nAuthorization: token %s\n第二個 %s\n第三個 %s\n第四個 %s\n"
              % tuple(secrets))
    stub = Stub()
    try:
        r = stub.notify(detail=detail)
        check("SEC-2：rc", r.rc, 0)
        body = r.issue(int(r.outputs["issue_number"]))["body"]
        for s in secrets:
            check_true(f"SEC-2：{s[:8]}… 未出現在公開 issue 內文", s not in body, body[:600])
        check_true("SEC-2：有實際遮罩（出現 [REDACTED]）", "[REDACTED]" in body, body[:600])
        check_true("SEC-2：Authorization 標頭被遮罩",
                   "Authorization: token" not in body and "Authorization: [REDACTED]" in body,
                   body[:600])
        check_true("SEC-2：message 是單行", "\n" not in (r.outputs.get("message") or ""),
                   r.outputs.get("message") or "")
    finally:
        stub.close()


def test_error_message_is_scrubbed_too() -> None:
    """@purpose gh 的 stderr 也會被寫進 message，而 message 會被呼叫端交給人看、也可能被寫進別的地方（SEC-2 的同一條規則）——只守 detail 那一邊時，另一邊仍會洩漏。
    @given shim 對 issue create 注入一個 stderr 內含 token 與 Authorization 標頭的失敗
    @step 呼叫 notify | exit 1
    @step 檢查 message output | 不含 token 字串、不含 "Authorization: token"
    @pass 兩者皆成立
    @api gh issue create --title --body --label
    @story S-8
    """
    secret = "ghp_LEAKLEAKLEAKLEAK1234"
    stub = Stub(fail_on=[{"contains": ["issue create"], "exit": 1,
                          "stderr": f"HTTP 401: Bad credentials\nAuthorization: token {secret}\n"}])
    try:
        r = stub.notify()
        check("errmsg 清洗：exit 1", r.rc, 1)
        msg = r.outputs.get("message") or ""
        check_true("errmsg 清洗：token 不在 message 內", secret not in msg, msg)
        check_true("errmsg 清洗：Authorization 被遮罩", "Authorization: token" not in msg, msg)
        check_true("errmsg 清洗：仍保留可定位的資訊", "401" in msg, msg)
    finally:
        stub.close()


def _tail_is_a_valid_sequence(data: bytes) -> bool:
    """尾端是否為一個**合法**的 UTF-8 序列（空字串視為是）。

    以 **Python 自己的 UTF-8 解碼器**判定，刻意不重用 `notify.sh` 的分類表——
    reviewer iteration 3 指出前一版 oracle 與受測邏輯共用同一張「只數長度」的表，
    於是兩邊對 overlong／surrogate／超界序列**一起誤判**，測試結構上無法揭穿自己。
    Python 的解碼器會拒絕那三類，所以它是獨立的權威。
    """
    if not data:
        return True
    for k in range(1, 5):
        if k > len(data):
            break
        try:
            if len(data[-k:].decode("utf-8")) == 1:
                return True
        except UnicodeDecodeError:
            continue
    return False


def test_truncate_bytes_survives_malformed_input() -> None:
    """@purpose 畸形（本身已不是合法 UTF-8 的）輸入不得讓 truncate_bytes 在**尾端**留下非法序列。呼叫端的 detail 與 gh 的 stderr 都可能挾帶位元組碎片，而本函式是那些位元組寫進**公開** issue 前的最後一關。兩個獨立的缺陷都由本案抓：iteration 2 的「回看窗 4 個位元組用盡時剝不乾淨」，以及 iteration 3 的「分類表只數長度、放行 overlong／surrogate／超界序列」——後者在生產常數（DETAIL_MAX=2000、ERRMSG_MAX=300）上實測重現過。**斷言的是責任邊界內的契約**：輸出必為輸入的位元組前綴、不超過上限、且尾端為**合法**序列；輸入自己中間就有的畸形位元組不在本函式責任內（見 `notify.sh` 的函式註解）。
    @given 十二種畸形輸入：尾端 10 個與恰好 5 個連續 continuation byte、非法 lead 0xF8、0xFF 夾在中間、整串以 continuation byte 開頭、單一孤立 continuation byte、overlong 0xC0 0x80、surrogate 0xED 0xA0 0x80、已停用的 4-byte lead 0xF7，以及三組**差一格**的條件式邊界（E0 9F BF、F0 8F BF BF、F4 90 80 80）
    @step 逐個輸入把上限掃過每一個可能的切點，經 truncate 診斷子命令取原始位元組 | rc=0
    @step 對每一格檢查三條性質 | 是輸入的位元組前綴；不超過上限；尾端經 Python 解碼器判定為合法序列
    @pass 沒有任何 (輸入, 上限) 組合在尾端留下非法序列
    @story S-8
    """
    ellipsis = "…".encode("utf-8")
    cases = [
        ("尾端 10 個連續 continuation byte", b"A" + b"\x80" * 10),
        ("尾端 5 個連續 continuation byte（剛跨過 4 位元組回看窗）", b"AB" + b"\x80" * 5),
        ("非法 lead byte 0xF8", b"AB\xf8"),
        ("非法 lead byte 0xFF 夾在中間", b"A\xffB\xff"),
        ("整串以 continuation byte 開頭", b"\x80\x80\x80ABC"),
        ("單一孤立 continuation byte", b"\xbf"),
        ("overlong 編碼 C0 80", b"AB\xc0\x80XY"),
        ("surrogate 編碼 ED A0 80", b"AB\xed\xa0\x80XY"),
        ("已停用的 4-byte lead F7", b"\xf7\xbf\xbf\xbfZZ"),
        # 以下三組是**差一格**的邊界（reviewer iteration 4 Major：E0／F0／F4 三條
        # 條件式限制先前只有 ED 有對稱測試，放寬它們時測試抓不到）。每一組都恰好
        # 落在合法範圍外一格，故只有完整的合法性表擋得住、只數長度的表會放行。
        ("overlong 3-byte：E0 9F BF（E0 之後須 A0-BF）", b"AB\xe0\x9f\xbfXY"),
        ("overlong 4-byte：F0 8F BF BF（F0 之後須 90-BF）", b"AB\xf0\x8f\xbf\xbfXY"),
        ("超出 U+10FFFF：F4 90 80 80（F4 之後須 80-8F）", b"AB\xf4\x90\x80\x80XY"),
    ]
    stub = Stub()
    violations: "list[str]" = []
    try:
        for label, raw_in in cases:
            for max_bytes in range(0, len(raw_in) + 2):
                proc = stub.run_raw([b"truncate", raw_in, str(max_bytes).encode()])
                if proc.returncode != 0:
                    violations.append(f"{label} max={max_bytes}: rc={proc.returncode} "
                                      f"stderr={proc.stderr[:200]!r}")
                    continue
                out = proc.stdout
                if len(raw_in) <= max_bytes:
                    # 不需截斷：原樣回傳（本函式不清洗輸入，見函式註解）
                    if out != raw_in:
                        violations.append(f"{label} max={max_bytes}: 不需截斷卻改了內容 "
                                          f"{out!r}")
                    continue
                if not out.endswith(ellipsis):
                    violations.append(f"{label} max={max_bytes}: 需截斷卻沒有省略號 {out!r}")
                    continue
                kept = out[: -len(ellipsis)]
                if not raw_in.startswith(kept):
                    violations.append(f"{label} max={max_bytes}: 輸出不是輸入的位元組前綴 "
                                      f"{kept!r}")
                    continue
                if len(kept) > max_bytes:
                    violations.append(f"{label} max={max_bytes}: 保留了 {len(kept)} 個位元組")
                    continue
                if not _tail_is_a_valid_sequence(kept):
                    violations.append(f"{label} max={max_bytes}: 尾端不是合法序列 "
                                      f"{kept[-6:]!r}（本函式自己切出來的，非輸入既有）")
    finally:
        stub.close()
    check("畸形輸入掃描：截斷後尾端皆為合法序列", violations, [])


def test_truncate_bytes_rejects_invalid_sequences_at_production_limits() -> None:
    """@purpose reviewer iteration 3 的三個反例在**生產常數**上重現過（DETAIL_MAX=2000、ERRMSG_MAX=300），不是只在玩具上限下才成立——把它們釘成獨立案例，避免日後有人以「只在小 max 出現」為由放寬分類表。
    @given overlong C0 80 落在 max=2000 的切點上；surrogate ED A0 80 落在 max=300 的切點上；已停用的 lead F7 於 max=4
    @step 逐個經 truncate 診斷子命令取原始位元組 | rc=0
    @step 以 bytes.decode("utf-8") 解碼整個輸出 | 三者皆須解得開
    @pass 三個歷史反例皆不再產出非法序列
    @story S-8
    """
    stub = Stub()
    try:
        for label, raw_in, max_bytes in [
            ("overlong C0 80 @ DETAIL_MAX", b"A" * 1998 + b"\xc0\x80XYZ", 2000),
            ("surrogate ED A0 80 @ ERRMSG_MAX", b"B" * 297 + b"\xed\xa0\x80XYZ", 300),
            ("已停用的 lead F7", b"\xf7\xbf\xbf\xbfZZ", 4),
        ]:
            proc = stub.run_raw([b"truncate", raw_in, str(max_bytes).encode()])
            check(f"{label}：rc", proc.returncode, 0)
            decode_or_fail(f"{label}：輸出須為合法 UTF-8", proc.stdout)
    finally:
        stub.close()


def test_secret_scrubbing_is_not_defeated_by_a_line_break() -> None:
    """@purpose 遮罩用的 sed 是**行導向**的：正則不跨行。清洗順序若是 scrub_secrets → single_line，被換行切開的 Authorization 標頭只會遮到標頭那一行，續行裡的 token 原樣寫進**公開** issue，而等 single_line 把它接成單行時遮罩早已跑完。此案例鎖住修正後的順序（single_line 先跑）。
    @given 兩種被換行切開的形狀：(a) `Authorization:` 與其值分屬兩行；(b) 標頭在同一行但 token 被換行切成 `ghp_AB` ＋ 續行的尾段（前段短於正則的 {6,} 下限，所以前綴規則自己接不住）
    @step 對 (a) 呼叫 notify | rc=0，且 token 字串不在新 issue 內文
    @step 對 (b) 呼叫 notify | rc=0，且 token 尾段不在新 issue 內文
    @step 檢查兩則內文 | 都含 `Authorization: [REDACTED]`
    @pass 以上全部成立
    @api gh issue create --title --body --label
    @story S-8
    """
    # 誠實記載本層擋不住的形狀（**刻意不寫成斷言**——把弱點斷言成「預期行為」會讓
    # 日後真的把它補強的人看到紅燈）：任意切割仍可逃逸。實測 `ghp_ABC DEFGHIJKLMNOP`
    # 在兩種順序下都不會被遮（兩段各自短於 {6,}）；`ghp_AAAABBBB\nCCCCDDDD` 則是前段
    # 被遮、後段照樣留下。遮罩式清洗防的是「不小心貼上」，不是「刻意規避」。
    cases = [
        ("換行切開標頭與其值", "Authorization:\ntoken ghp_ABCDE\n", "ghp_ABCDE"),
        ("換行切開 token 本身",
         "HTTP 401: Bad credentials\nAuthorization: Bearer ghp_AB\nCDEFGHIJKLMNOPQRSTUV\n",
         "CDEFGHIJKLMNOPQRSTUV"),
    ]
    for label, detail, leak in cases:
        stub = Stub()
        try:
            r = stub.notify(detail=detail)
            check(f"換行遮罩逃逸（{label}）：rc", r.rc, 0)
            body = r.issue(int(r.outputs["issue_number"]))["body"]
            check_true(f"換行遮罩逃逸（{label}）：{leak} 未出現在公開 issue 內文",
                       leak not in body, body[:600])
            check_true(f"換行遮罩逃逸（{label}）：Authorization 被遮罩",
                       "Authorization: [REDACTED]" in body, body[:600])
        finally:
            stub.close()


def test_error_message_scrubbing_is_not_defeated_by_a_line_break() -> None:
    """@purpose 清洗順序的修正同時落在 scrub_detail 與 scrub_errmsg 兩支，而 gh 的 stderr 是**多行**的常態來源（HTTP 狀態一行、標頭一行、提示一行）。只鎖 detail 那一邊時，errmsg 這邊的同型逃逸沒有任何案例守著——這正是「契約有一端懸空」的形狀。
    @given shim 對 issue create 注入一個 stderr：`Authorization:` 與其值分屬兩行，值裡的 token 短於前綴規則的 {6,} 下限
    @step 呼叫 notify | exit 1（R-4：通報失敗就拋，不遞迴通報）
    @step 檢查 message output | 不含 token 字串
    @step 檢查 message output | 仍保留可定位的 401（遮罩沒有把整段吃掉）
    @pass 以上全部成立
    @api gh issue create --title --body --label
    @story S-8
    """
    secret = "ghp_ABCDE"
    stub = Stub(fail_on=[{"contains": ["issue create"], "exit": 1,
                          "stderr": f"HTTP 401: Bad credentials\nAuthorization:\ntoken {secret}\n"}])
    try:
        r = stub.notify()
        check("errmsg 換行遮罩逃逸：exit 1", r.rc, 1)
        msg = r.outputs.get("message") or ""
        check_true("errmsg 換行遮罩逃逸：token 不在 message 內", secret not in msg, msg)
        check_true("errmsg 換行遮罩逃逸：仍保留可定位的資訊", "401" in msg, msg)
    finally:
        stub.close()


def test_token_prefix_rules_still_fire_without_an_authorization_header() -> None:
    """@purpose single_line 移到 scrub_secrets 之前後，`Authorization:` 規則的 `.*` 會吃到**整段 detail 的結尾**而不只是該行結尾——於是既有的 SEC-2 案例（detail 以 Authorization 行開頭）其實是被那一條規則整段吞掉，四個 token 前綴規則不再被它實際執行。此案例補回那份覆蓋：detail 內**沒有** Authorization 標頭，每個前綴規則必須各自命中。
    @given detail 含 ghp_／gho_／ghs_／github_pat_ 四種前綴的 token，且全文不含 Authorization 字樣
    @step 呼叫 notify | rc=0
    @step 檢查新 issue 內文 | 四個 token 字串都不在裡面
    @step 檢查新 issue 內文 | 前後的中文敘述仍在（遮罩沒有把整段吃掉）
    @pass 以上全部成立
    @api gh issue create --title --body --label
    @story S-8
    """
    secrets = ["ghp_AAAABBBBCCCC", "gho_1111222233",
               "github_pat_11ABCDE_zzzz", "ghs_99998888"]
    detail = ("前綴一 %s\n前綴二 %s\n前綴三 %s\n前綴四 %s\n收尾敘述" % tuple(secrets))
    stub = Stub()
    try:
        r = stub.notify(detail=detail)
        check("前綴規則：rc", r.rc, 0)
        body = r.issue(int(r.outputs["issue_number"]))["body"]
        for s in secrets:
            check_true(f"前綴規則：{s} 未出現在公開 issue 內文", s not in body, body[:600])
        check_true("前綴規則：遮罩沒有把整段吃掉（首尾敘述仍在）",
                   "前綴一" in body and "收尾敘述" in body, body[:600])
    finally:
        stub.close()


# ==========================================================================
# truncate_bytes：UTF-8 邊界（純函式，走 truncate 診斷子命令）
# ==========================================================================
# 本組是唯一直接驗 truncate_bytes 的地方。它為什麼值得單獨一組：這支函式的輸出會
# 逐字進入**公開** issue 的內文，而它唯一的失敗模式（切出半個字元）在 Python 端會
# 被 text=True 的解碼吃掉、在 GitHub 上會顯示成替代字元——兩邊都不會有人報錯。
# 因此斷言的第一層一律是「原始位元組解得開」，第二層才比對字串。

# (label, text, max_bytes, expected)
TRUNCATE_CASES = [
    ("4-byte 字元剛好完整落在切點內", "😀ABC", 4, "😀…"),
    ("4-byte 字元被切在中間（只剩 3 個位元組）", "😀ABC", 3, "…"),
    ("4-byte 字元之後再切在 ASCII 上", "😀ABC", 5, "😀A…"),
    ("3-byte 字元剛好完整落在切點內", "測試ABC", 6, "測試…"),
    ("3-byte 字元被切在第 1 個位元組後", "測試ABC", 4, "測…"),
    ("3-byte 字元被切在第 2 個位元組後", "測試ABC", 5, "測…"),
    ("切在 ASCII 上", "測試ABC", 7, "測試A…"),
    ("2-byte 字元剛好完整落在切點內", "café!", 5, "café…"),
    ("2-byte 字元被切在中間", "café!", 4, "caf…"),
    ("純 ASCII", "abcdef", 3, "abc…"),
    ("不需截斷（長度等於上限）", "測試", 6, "測試"),
    ("不需截斷（長度小於上限）", "測試", 99, "測試"),
]


def decode_or_fail(label: str, raw: bytes) -> "str | None":
    """把原始位元組解成 UTF-8。解不開就是本組案例要抓的那個缺陷，記一筆失敗回 None。"""
    global CHECKS
    CHECKS += 1
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        FAILURES.append(f"{label}\n    輸出不是合法 UTF-8：{exc}\n    bytes: {raw!r}")
        return None


def test_truncate_bytes_never_emits_invalid_utf8() -> None:
    """@purpose truncate_bytes 在 LC_ALL=C 下做位元組切割，切點落在多位元組字元中間時必須把那個**不完整**的序列砍掉，但切點剛好落在字元邊界時**不得**砍——完整字元的尾端本來就是 continuation byte，把它當成「序列不完整」的證據會同時造成兩種錯：4-byte 字元只剩孤立 lead byte（無效 UTF-8，寫進公開 issue 變亂碼），與完整的中文字被誤刪一個。
    @given 12 組 (文字, 上限, 預期輸出)，涵蓋 2／3／4 位元組字元各自「切在邊界上」與「切在中間」、切在 ASCII 上、純 ASCII、以及不需截斷
    @step 逐組透過 truncate 診斷子命令取得**原始位元組** | rc=0
    @step 把原始位元組以 bytes.decode("utf-8") 解碼 | 每一組都必須解得開（本案例的核心斷言）
    @step 比對解碼後的字串 | 逐組等於預期輸出
    @step 檢查不需截斷的兩組 | 原樣輸出、不得補上省略號
    @pass 以上全部成立
    @story S-8
    """
    stub = Stub()
    try:
        for label, text, max_bytes, expected in TRUNCATE_CASES:
            proc = stub.run_raw(["truncate", text, str(max_bytes)])
            check(f"truncate（{label}）：rc", proc.returncode, 0)
            got = decode_or_fail(f"truncate（{label}）：輸出須為合法 UTF-8", proc.stdout)
            if got is None:
                continue
            check(f"truncate（{label}）：輸出字串", got, expected)
            if len(text.encode("utf-8")) <= max_bytes:
                check_true(f"truncate（{label}）：不需截斷時不得補省略號",
                           "…" not in got, repr(got))
    finally:
        stub.close()


def test_truncate_bytes_output_is_always_a_maximal_valid_prefix() -> None:
    """@purpose 逐格掃過所有可能的切點，鎖住 truncate_bytes 的完整語意而不只是十來個手挑的點：輸出永遠是合法 UTF-8、永遠是原字串的**字元前綴**、永遠不超過位元組上限，且是該上限下**最長**的那個前綴（砍多了會靜默丟字，砍少了會留半個字元；兩種錯都不會有工具報錯）。
    @given 一段混合 1／2／3／4 位元組字元的文字，上限從 0 掃到位元組長度 +2
    @step 逐個上限透過 truncate 診斷子命令取得原始位元組 | rc=0
    @step 以 bytes.decode("utf-8") 解碼 | 每一格都必須解得開
    @step 對每一格檢查四條性質 | 前綴、不超過上限、最長、以及「需截斷才有省略號」
    @pass 全部上限皆無違反
    @story S-8
    """
    text = "測試😀café!ABC。"
    assert "…" not in text  # 省略號的剝除靠尾字元判定，原文不得自帶省略號
    raw_len = len(text.encode("utf-8"))
    violations: list[str] = []
    stub = Stub()
    try:
        for max_bytes in range(0, raw_len + 3):
            proc = stub.run_raw(["truncate", text, str(max_bytes)])
            if proc.returncode != 0:
                violations.append(f"max={max_bytes}: rc={proc.returncode} "
                                  f"stderr={proc.stderr[:200]!r}")
                continue
            got = decode_or_fail(f"truncate 掃描 max={max_bytes}：輸出須為合法 UTF-8",
                                 proc.stdout)
            if got is None:
                continue
            if raw_len <= max_bytes:
                if got != text:
                    violations.append(f"max={max_bytes}: 不需截斷卻改了內容 {got!r}")
                continue
            if not got.endswith("…"):
                violations.append(f"max={max_bytes}: 需截斷卻沒有省略號 {got!r}")
                continue
            body = got[:-1]
            if not text.startswith(body):
                violations.append(f"max={max_bytes}: 輸出不是原字串的字元前綴 {body!r}")
                continue
            used = len(body.encode("utf-8"))
            if used > max_bytes:
                violations.append(f"max={max_bytes}: 前綴用掉 {used} 位元組，超過上限")
                continue
            # 最長性：再多收一個字元就必定超過上限（否則代表砍過頭、靜默丟字）。
            nxt = text[len(body)]
            if used + len(nxt.encode("utf-8")) <= max_bytes:
                violations.append(
                    f"max={max_bytes}: 砍過頭，還放得下 {nxt!r}（已用 {used} 位元組）")
        check("truncate 掃描：所有上限皆無違反", violations, [])
    finally:
        stub.close()


# ==========================================================================
# 完成判準（[ug:unit-of-work.md] U-5，離線半邊）
# ==========================================================================

def test_completion_criterion_two_consecutive_rounds() -> None:
    """@purpose [ug:unit-of-work.md] 的 U-5 完成判準逐字：同一個鍵連續失敗兩輪後，該鍵的**開啟中通報 issue 數為 1** 且 **comment 數增加 1**。這條在真實 GitHub 上的另一半在 run-live-tests.py。
    @given 空的 issue 存放區（第一輪之前什麼都沒有）
    @step 第一輪：呼叫 notify | action=created
    @step 第二輪：對**同一個存放區**再呼叫一次 notify | action=commented、issue_number 與第一輪相同
    @step 數該鍵的開啟中 issue | 恰好 1 則
    @step 數該則的 comment | 恰好 1 則（由 0 增加 1）
    @pass 以上全部成立，且標題為 (×2)
    @api gh issue create --title --body --label
    @api gh issue comment --body
    @api gh issue edit --title
    @story S-8
    """
    stub = Stub()
    try:
        r1 = stub.notify(detail="第一輪")
        check("完成判準：第一輪 action", r1.outputs.get("action"), "created")
        n1 = r1.outputs["issue_number"]
        r2 = stub.notify(detail="第二輪")
        check("完成判準：第二輪 action", r2.outputs.get("action"), "commented")
        check("完成判準：第二輪落在同一則", r2.outputs.get("issue_number"), n1)
        mk = marker(INTENT, FAILURE_CODES[0])
        check("完成判準：開啟中同鍵 issue 數為 1", len(r2.open_issues_with_marker(mk)), 1)
        it = r2.issue(int(n1))
        check("完成判準：comment 數增加 1", len(it["comments"]), 1)
        check("完成判準：標題為 ×2", it["title"], title_of(INTENT, FAILURE_CODES[0], 2))
    finally:
        stub.close()


def test_deduplicated_state_converges_on_the_next_round() -> None:
    """@purpose R-2 第 4 步修的是 ADR-A8 一條走不通的路徑：該 ADR 說重複「由下輪的 resolve_if_open 收斂」，但 resolve_if_open 只在**失敗不再發生時**被呼叫，而重複正是在失敗持續時產生的。改由 notify 自己收斂後，下一次失敗發生時重複即被清掉。
    @given 兩則同鍵開啟中 issue（模擬並行 run 各開了一則）
    @step 第一輪 notify | action=deduplicated、開啟中同鍵剩 1 則
    @step 第二輪 notify（同一個存放區） | action=commented（已經沒有重複可收斂）
    @pass 兩輪之後開啟中同鍵 issue 數為 1
    @api gh issue list --label --state open --json number,title,body
    @api gh issue close --comment
    @story S-8
    """
    stub = Stub(issues=[alert_issue(21, INTENT, "Aborted"), alert_issue(22, INTENT, "Aborted")])
    try:
        mk = marker(INTENT, "Aborted")
        r1 = stub.notify(reason="Aborted")
        check("收斂：第一輪 action", r1.outputs.get("action"), "deduplicated")
        check("收斂：第一輪後開啟中剩 1 則", len(r1.open_issues_with_marker(mk)), 1)
        r2 = stub.notify(reason="Aborted")
        check("收斂：第二輪 action", r2.outputs.get("action"), "commented")
        check("收斂：第二輪後開啟中仍為 1 則", len(r2.open_issues_with_marker(mk)), 1)
    finally:
        stub.close()


# ==========================================================================
# 介面層的機械斷言
# ==========================================================================

def test_sec1_action_yml_no_credential_input() -> None:
    """@purpose action.yml 不得宣告任何憑證型 input——input 是公開介面，憑證只能走 env GH_TOKEN（SEC-1，與 U-3 同一條規則）。
    @given 本 action 的 action.yml 原始文字
    @step 掃描 inputs: 區塊的全部 input 名稱 | 無任何名稱含 token / secret / password / credential / apikey
    @step 掃描全檔 | GH_TOKEN 不從 inputs 取值
    @pass 兩項掃描皆零命中
    @story S-8
    """
    text = ACTION_YML.read_text()
    input_names: list[str] = []
    in_inputs = False
    for line in text.splitlines():
        if line.startswith("inputs:"):
            in_inputs = True
            continue
        if in_inputs and line and not line.startswith(" ") and not line.startswith("#"):
            in_inputs = False
        if in_inputs and line.startswith("  ") and not line.startswith("   ") \
                and line.rstrip().endswith(":"):
            input_names.append(line.strip().rstrip(":"))
    check_true("SEC-1：有掃到 input 清單（掃描器沒壞）", len(input_names) >= 5, f"掃到：{input_names}")
    # 沿用 U-3 的禁用詞組。**keys 不在其中且不該在**：它是 FailureIdentity 的鍵
    # 清單，不是憑證；禁用詞組鎖的是憑證形狀的名稱（apikey／api_key 仍會被擋）。
    banned = ("token", "secret", "password", "credential", "passwd", "apikey", "api_key", "api-key")
    offenders = [n for n in input_names if any(b in n.lower() for b in banned)]
    check("SEC-1：無憑證型 input 名稱", offenders, [])
    check_true("SEC-1：GH_TOKEN 不從 inputs 映射", "GH_TOKEN: ${{ inputs" not in text,
               "action.yml 把 GH_TOKEN 接到了 input 上")


def test_action_yml_env_mapping_matches_script() -> None:
    """@purpose action.yml 的 env 映射與 notify.sh 實際讀取的 AIDLC_* 變數集合完全相等——多一個是死接線，少一個是 input 進不去（介面轉接層唯一會壞的方式，而且壞了不會有錯誤訊息）。
    @given action.yml 與 notify.sh 原始文字
    @step 從 notify.sh 抓所有 ${AIDLC_…} 引用 | 得到集合 S
    @step 從 action.yml 的 env: 區塊抓所有 AIDLC_… 鍵 | 得到集合 Y
    @pass S == Y
    @story S-8
    """
    sh = NOTIFY_SH.read_text()
    yml = ACTION_YML.read_text()
    used = set(re.findall(r"\$\{(AIDLC_[A-Z_]+)", sh))
    mapped = set(re.findall(r"^\s+(AIDLC_[A-Z_]+):\s+\$\{\{ inputs\.", yml, flags=re.M))
    check_true("env 映射：兩邊都掃到東西", len(used) >= 5 and len(mapped) >= 5,
               f"used={sorted(used)} mapped={sorted(mapped)}")
    check("env 映射：notify.sh 讀的 == action.yml 映射的", sorted(used), sorted(mapped))


def test_reason_code_sets_are_declared_in_one_place() -> None:
    """@purpose R-1 的分界（哪些碼該通報、哪些碼根本不該呼叫）在 notify.sh 內只有一份，測試從 codes 診斷子命令讀它而不是自己抄——抄一份的話，改了程式而忘了改測試時，測試會繼續綠燈。
    @given notify.sh 的 codes 診斷子命令
    @step 讀 failure_codes | 恰為 ExternalError / Rejected / Aborted / CannotCreate / Failed 五個
    @step 讀 normal_codes | 恰為 suppressed / parked / unparseable / whitelisted / undecidable 五個
    @step 交叉比對 | 兩個集合沒有交集
    @step 比對 action.yml 的 description | 五個失敗碼逐字出現在介面文件裡
    @pass 以上全部成立
    @story S-8
    """
    stub = Stub()
    try:
        r = stub.run("codes")
        check("codes：rc", r.rc, 0)
        failure = (r.outputs.get("failure_codes") or "").split()
        normal = (r.outputs.get("normal_codes") or "").split()
        check("codes：失敗碼集合", sorted(failure), sorted(FAILURE_CODES))
        check("codes：正常判斷碼集合", sorted(normal), sorted(NORMAL_CODES))
        check("codes：兩個集合無交集", sorted(set(failure) & set(normal)), [])
        yml = ACTION_YML.read_text()
        missing = [c for c in failure if c not in yml]
        check("codes：五個失敗碼都寫進 action.yml 的介面文件", missing, [])
    finally:
        stub.close()


def test_stdout_and_github_output_agree() -> None:
    """@purpose emit 同時寫 stdout 的 name=value 與 $GITHUB_OUTPUT 的 heredoc。呼叫端讀後者、測試 harness 讀前者——兩邊若不一致，測試會在一個沒有人在用的通道上綠燈。
    @given 一次走 deduplicated 分支的 notify（output 最多的一支）
    @step 解析 stdout 的 name=value | 得到 dict A
    @step 解析 $GITHUB_OUTPUT 的 heredoc | 得到 dict B
    @pass A == B，且兩者都含 result／issue_number／action／count／closed／closed_numbers／message 七個鍵
    @api gh issue list --label --state open --json number,title,body
    @story S-8
    """
    stub = Stub(issues=[alert_issue(21, INTENT, "Failed"), alert_issue(22, INTENT, "Failed")])
    try:
        r = stub.notify(reason="Failed")
        check("output 一致：rc", r.rc, 0)
        parsed: dict[str, str] = {}
        lines = r.gh_output.splitlines()
        i = 0
        while i < len(lines):
            name, sep, delim = lines[i].partition("<<")
            if not sep:
                i += 1
                continue
            buf = []
            i += 1
            while i < len(lines) and lines[i] != delim:
                buf.append(lines[i])
                i += 1
            i += 1
            parsed[name] = "\n".join(buf)
        check("output 一致：stdout 與 GITHUB_OUTPUT 相同", parsed, r.outputs)
        expected_keys = ["action", "closed", "closed_numbers", "count",
                         "issue_number", "message", "result"]
        check("output 一致：七個鍵齊全", sorted(parsed.keys()), expected_keys)
    finally:
        stub.close()


def test_every_test_carries_spec_annotations() -> None:
    """@purpose §4.4 的規格註解是自動化案例在 TCMS 上**唯一**的描述來源（`project.md` 的 tcms 必做 3b：不得直接在 TCMS 手寫描述，手抄的必定過期而無人察覺）。少一個註解就是 TCMS 上少一份可信描述，而那不會有任何工具報錯——所以由本案例機械地擋住。
    @given run-stub-tests.py 與 run-live-tests.py 的原始文字
    @step 抓出兩檔的每一個 def test_… / def step_… | 逐一取其 docstring
    @step 檢查每個 docstring | 含 @purpose、@given、至少一個 @step、@pass、@story
    @step 檢查每個 @api 的值 | 以 gh 子命令或 REST 路徑（METHOD /path）起頭，不得是空的
    @pass 兩檔的全部案例皆齊全
    @story S-8
    """
    import ast
    required = ["@purpose", "@given", "@step", "@pass", "@story"]
    for path in (HERE / "run-stub-tests.py", HERE / "run-live-tests.py"):
        tree = ast.parse(path.read_text())
        names = [n for n in tree.body
                 if isinstance(n, ast.FunctionDef)
                 and (n.name.startswith("test_") or n.name.startswith("step_")
                      or n.name == "cleanup")]
        check_true(f"{path.name}：有掃到案例", len(names) >= 4, f"掃到 {len(names)} 個")
        for node in names:
            doc = ast.get_docstring(node) or ""
            missing = [tag for tag in required if tag not in doc]
            check(f"{path.name}::{node.name} 的 §4.4 註解齊全", missing, [])
            for line in doc.splitlines():
                line = line.strip()
                if not line.startswith("@api"):
                    continue
                value = line[len("@api"):].strip()
                ok = value.startswith("gh ") or bool(
                    re.match(r"^(GET|POST|PATCH|PUT|DELETE) /", value))
                check_true(f"{path.name}::{node.name} 的 @api 形式正確（gh 子命令或 REST 路徑）",
                           ok, repr(value))


def test_list_truncation_is_reported_not_swallowed() -> None:
    """@purpose 列舉命中上限時**不靜默**。兩種操作的降級方向都是安全的（resolve 少關幾則、notify 多開一則而下輪由 R-2 第 4 步收斂），但「安全地降級」不等於「可以不說」——一個只在通報 issue 累積到上限時才出現、且出現時什麼都不講的分支，正是最不會有人發現的那種。
    @given 存放區有 500 則（＝ notify.sh 的 LIST_LIMIT）帶 label 的開啟中 issue，鍵各不相同
    @step 以一個不在其中的鍵呼叫 notify | rc=0、action=created（比對本身仍正確）
    @step 檢查 message output | 含「命中列舉上限」與上限值
    @step 檢查 stderr | 有一行警告
    @pass 以上全部成立
    @api gh issue list --label --state open --json number,title,body
    @api gh issue create --title --body --label
    @story S-8
    """
    stub = Stub()
    try:
        limit = int(stub.run("codes").outputs["list_limit"])
        crowd = [alert_issue(1000 + i, f"{OTHER_INTENT}-{i}", "Rejected") for i in range(limit)]
        stub2 = Stub(issues=crowd, next_number=9000)
        try:
            r = stub2.notify()
            check("truncation：rc", r.rc, 0)
            check("truncation：比對本身仍正確", r.outputs.get("action"), "created")
            msg = r.outputs.get("message") or ""
            check_true("truncation：message 說出命中上限",
                       "命中列舉上限" in msg and str(limit) in msg, msg)
            check_true("truncation：stderr 有警告", "警告" in r.stderr and "上限" in r.stderr,
                       r.stderr[:300])
        finally:
            stub2.close()
    finally:
        stub.close()


def test_action_yml_declares_every_non_diagnostic_output() -> None:
    """@purpose notify.sh emit 的每一個 output 名稱，除了 codes 診斷子命令那組之外，都必須在 action.yml 的 outputs 宣告——沒宣告的 output 寫進 $GITHUB_OUTPUT 之後呼叫端**取不到**，而且沒有任何工具會報錯（契約有一端懸空的典型形狀）。
    @given notify.sh 與 action.yml 原始文字
    @step 抓 notify.sh 的所有 emit <name> | 得到集合 E
    @step 抓 action.yml 的 outputs 區塊鍵名 | 得到集合 Y
    @step 從 E 扣掉 codes 診斷子命令印的四個名稱 | 剩下的必須逐一在 Y 內
    @step 反向檢查 | Y 內每一個名稱都必須有 emit（宣告了卻沒人寫＝死接線）
    @pass 兩個方向皆無差集
    @story S-8
    """
    sh = NOTIFY_SH.read_text()
    yml = ACTION_YML.read_text()
    emitted = set(re.findall(r"^\s+emit ([a-z_]+)", sh, flags=re.M))
    block = yml.split("\noutputs:\n", 1)[1].split("\nruns:\n", 1)[0]
    declared = set(re.findall(r"^  ([a-z_]+):$", block, flags=re.M))
    diagnostic = {"failure_codes", "normal_codes", "list_limit", "detail_max"}
    check_true("output 契約：兩邊都掃到東西", len(emitted) >= 7 and len(declared) >= 7,
               f"emitted={sorted(emitted)} declared={sorted(declared)}")
    check("output 契約：emit 了卻沒宣告（呼叫端取不到）",
          sorted((emitted - diagnostic) - declared), [])
    check("output 契約：宣告了卻沒人 emit（死接線）", sorted(declared - emitted), [])


TESTS = [
    test_create_when_no_open_alert_matches,
    test_comment_and_increment_when_exactly_one,
    test_deduplicate_keeps_lowest_number_not_earliest_created,
    test_edited_title_still_matches_by_body_key,
    test_titlelike_decoy_with_different_key_is_never_touched,
    test_normal_reason_codes_rejected_with_zero_api_calls,
    test_interface_misuse_exits_2_with_zero_api_calls,
    test_resolve_closes_only_keys_in_the_set,
    test_resolve_batch_issues_exactly_one_list_call,
    test_resolve_key_without_issue_is_noop,
    test_resolve_rejects_malformed_keys_before_any_api_call,
    test_resolve_tolerates_indented_and_crlf_keys,
    test_label_created_when_absent,
    test_label_not_created_when_present_and_never_on_resolve_path,
    test_api_failure_on_create_exits_1_without_recursive_notify,
    test_api_failure_on_list_exits_1_before_any_write,
    test_api_failure_on_close_during_resolve_exits_1,
    test_detail_is_scrubbed_before_it_reaches_a_public_issue,
    test_error_message_is_scrubbed_too,
    test_secret_scrubbing_is_not_defeated_by_a_line_break,
    test_error_message_scrubbing_is_not_defeated_by_a_line_break,
    test_token_prefix_rules_still_fire_without_an_authorization_header,
    test_truncate_bytes_never_emits_invalid_utf8,
    test_truncate_bytes_output_is_always_a_maximal_valid_prefix,
    test_truncate_bytes_survives_malformed_input,
    test_truncate_bytes_rejects_invalid_sequences_at_production_limits,
    test_completion_criterion_two_consecutive_rounds,
    test_deduplicated_state_converges_on_the_next_round,
    test_sec1_action_yml_no_credential_input,
    test_action_yml_env_mapping_matches_script,
    test_reason_code_sets_are_declared_in_one_place,
    test_stdout_and_github_output_agree,
    test_list_truncation_is_reported_not_swallowed,
    test_action_yml_declares_every_non_diagnostic_output,
    test_every_test_carries_spec_annotations,
]


def main() -> int:
    if not NOTIFY_SH.exists():
        print(f"找不到 {NOTIFY_SH}", file=sys.stderr)
        return 2
    if shutil.which("jq") is None:
        print("找不到 jq（notify.sh 的硬依賴）", file=sys.stderr)
        return 2
    for test in TESTS:
        before = len(FAILURES)
        try:
            test()
        except Exception as exc:  # 測試框架自身的錯誤也要大聲失敗
            FAILURES.append(f"{test.__name__} 擲出例外：{exc!r}")
        status = "ok" if len(FAILURES) == before else "FAIL"
        print(f"[{status}] {test.__name__}")
    print(f"\n{len(TESTS)} tests, {CHECKS} checks, {len(FAILURES)} failures")
    if FAILURES:
        print("\n---- failures ----")
        for f in FAILURES:
            print(f"* {f}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
