#!/usr/bin/env python3
"""live 斷言 runner — U-4「record 回寫與同步狀態」composite action（真實 origin 層）。

用法：
    python3 .github/actions/aidlc-sync-record/run-live-tests.py

非零 exit 表失敗或**不完整**：拿不到 gh 憑證、或憑證對 repo 無 push 權時，本 runner 以
exit 3 明確聲明「live 層未執行」——不靜默跳過（計畫 Step 7 的逐字要求）。

**寫入對象只有一次性分支 aidlc-sync/test/<utc-ts>**（Plan Approval 裁決 4）。三層防呆：
  1. 進場即斷言目標分支名以 aidlc-sync/test/ 開頭，harness 自己的每一次 push／delete
     都先過 assert_test_branch()，不符即 exit 4；
  2. 受測物 record.sh 的所有 live 呼叫都在 git shim 之下執行，shim 對每一個 `push`
     斷言 argv 含 refs/heads/aidlc-sync/test/，不含即 exit 97——這是對 R-3.1 介面層
     防線的**外部**兜底：`ut` 的 branch protection 為 enforce_admins: false 而本機
     憑證為 admin，直推 ut 會成功，平台不會救；
  3. 步驟 (c) 的 ut 拒絕案在 origin URL 被改指向不存在路徑的 clone 內執行——即使前
     兩層都失效，push 也到不了 GitHub。
**不對 main 發出任何真實 push 來驗 GH006**：換到的資訊（GH006 逐字文字）stub 的
hook 就有，而保護設定若有任何閃失，落地的是一則機器 commit 在 main 上。main 半邊的
平台拒絕因此**只有 stub 涵蓋、無 live 反例**——如實記載。

covers（code-generation-plan.md Step 7 的 (a)〜(d)）：
    (a) 對一次性分支 commit_and_push → pushed；gh api 查得到該 commit，訊息含
        [aidlc-sync]、files 只有 sync-state.json、作者為同步身分、parent 為分叉點
    (b) 第二個 clone 在受測物 fetch 之後、push 之前先推一筆（git shim 製造真實的
        GitHub 非快轉）→ 重試後 pushed、attempts=2、對方欄位保留
    (c) branch=ut → rejected／policy，gh api 證明 ut（與 main）的 HEAD 前後相同
    (d) 測畢 git push --delete 清除分支並確認 gh api 回 404

測試殘留：public repo 上會短暫出現一個 aidlc-sync/test/<ts> 分支與其 push 事件；
測畢刪除。cleanup 失敗要大聲——殘留要被看見。
"""

from __future__ import annotations

import base64
import datetime
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
RECORD_SH = HERE / "record.sh"
REPO_ROOT = HERE.parents[2]

BASH = os.environ.get("AIDLC_RECORD_BASH", "bash")
REAL_GIT = shutil.which("git") or "git"

REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "opendiamonds/cloud-360")
FORK_BRANCH = os.environ.get("AIDLC_LIVE_FORK_BRANCH", "main")
TEST_PREFIX = "aidlc-sync/test/"

RECORD_DIR = "aidlc/spaces/default/intents/aidlc-sync-test"
STATE_PATH = f"{RECORD_DIR}/sync-state.json"
MARKER = "[aidlc-sync]"
MESSAGE = f"雜項(aidlc-sync): U-4 live 測試回寫 {MARKER}"

FAILURES: list[str] = []
CHECKS = 0
STATE: dict = {}


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


def load_shim_source() -> str:
    """git shim 的原始碼與 stub runner 共用一份（避免兩份漂移）。"""
    spec = importlib.util.spec_from_file_location("aidlc_record_stub", HERE / "run-stub-tests.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GIT_SHIM


# ==========================================================================
# 防呆
# ==========================================================================

def assert_test_branch(name: str) -> None:
    if not name.startswith(TEST_PREFIX):
        print(f"REFUSE：目標分支 '{name}' 不以 {TEST_PREFIX} 開頭。live 測試只准碰一次性測試分支。exit 4。",
              file=sys.stderr)
        sys.exit(4)


# ==========================================================================
# git／gh 小工具（harness 自己的通道，不經 record.sh）
# ==========================================================================

HARNESS_IDENTITY = {
    "GIT_AUTHOR_NAME": "harness", "GIT_AUTHOR_EMAIL": "harness@example.com",
    "GIT_COMMITTER_NAME": "harness", "GIT_COMMITTER_EMAIL": "harness@example.com",
}


def git(*args: str, cwd=None, check_rc: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(HARNESS_IDENTITY)
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run([REAL_GIT, "-c", "commit.gpgsign=false", *args], cwd=cwd,
                          capture_output=True, text=True, env=env)
    if check_rc and proc.returncode != 0:
        raise RuntimeError(f"harness git {' '.join(args)} 失敗：{proc.stderr.strip()[:400]}")
    return proc


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def gh_json(path: str):
    proc = gh("api", path)
    if proc.returncode != 0:
        raise RuntimeError(f"harness gh api {path} 失敗：{proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout)


def branch_sha(branch: str) -> str | None:
    proc = gh("api", f"repos/{REPOSITORY}/branches/{branch}")
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)["commit"]["sha"]


def contents_json(path: str, ref: str) -> dict:
    data = gh_json(f"repos/{REPOSITORY}/contents/{path}?ref={ref}")
    return json.loads(base64.b64decode(data["content"]).decode("utf-8"))


class Result:
    def __init__(self, proc: subprocess.CompletedProcess, shim_dir: pathlib.Path):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.outputs: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if "=" in line:
                name, _, value = line.partition("=")
                self.outputs[name] = value
        counter = shim_dir / "push-count"
        self.shim_pushes = int(counter.read_text()) if counter.exists() else 0


def run_record(operation: str, cwd: pathlib.Path, env: dict, before_first_push=None) -> Result:
    """所有 live 呼叫都在 git shim 之下：shim 對每個 push 斷言目標是測試分支。"""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-record-live-run-"))
    try:
        shim_dir = tmp / "shim"
        shim_dir.mkdir()
        cfg = {"required_substring": f"refs/heads/{TEST_PREFIX}"}
        if before_first_push:
            cfg["before_first_push"] = before_first_push
        (shim_dir / "config.json").write_text(json.dumps(cfg))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        exe = bin_dir / "git"
        exe.write_text(STATE["shim_source"])
        exe.chmod(0o755)
        full_env = dict(os.environ)
        for key in list(full_env):
            if key.startswith("AIDLC_"):
                del full_env[key]
        full_env.update(env)
        full_env["AIDLC_OPERATION"] = operation
        full_env["GITHUB_OUTPUT"] = ""
        full_env["PATH"] = f"{bin_dir}:{full_env['PATH']}"
        full_env["AIDLC_GIT_SHIM_DIR"] = str(shim_dir)
        proc = subprocess.run([BASH, str(RECORD_SH)], cwd=cwd, capture_output=True, text=True, env=full_env)
        return Result(proc, shim_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cap_env(branch: str) -> dict:
    return {"AIDLC_RECORD_PATH": RECORD_DIR + "/", "AIDLC_BRANCH": branch,
            "AIDLC_PATHS": STATE_PATH, "AIDLC_MESSAGE": MESSAGE}


def make_clone(name: str, ref: str) -> pathlib.Path:
    """從本機 repo 物件庫開 clone（快、不佔網路），再把 origin 指回 GitHub 並以淺層
    fetch 取得 <ref> 的尖端後 detach——分叉點一定存在於 GitHub 上（不會把本機未推的
    commit 一併推上測試分支）。"""
    dst = STATE["root"] / name
    git("clone", "-q", "--no-checkout", str(REPO_ROOT), str(dst))
    git("remote", "set-url", "origin", STATE["origin_url"], cwd=dst)
    git("fetch", "-q", "--depth", "1", "origin", ref, cwd=dst)
    git("checkout", "-q", "--detach", "FETCH_HEAD", cwd=dst)
    return dst


# ==========================================================================
# 步驟（有序；共享狀態記錄於 STATE）
# ==========================================================================

def step_preflight() -> None:
    """@purpose 進場防呆與基準採樣：測試分支名合規；origin 是本 repo；記下 ut／main 的 HEAD 供步驟 (c) 比對；確認 origin 上沒有同名殘留分支。
    @given gh 憑證可用且對 repo 有 push 權（main() 已驗）
    @step 產生 aidlc-sync/test/<utc-ts> 並 assert_test_branch | 通過
    @step git ls-remote 該分支 | 不存在（無殘留）
    @step gh api branches/ut 與 branches/main | 記下 SHA
    @step 建立 clone A（detach 於 origin/main 尖端）| HEAD == gh api branches/main 的 SHA
    @pass 基準記錄完成
    @story S-1
    """
    assert_test_branch(STATE["branch"])
    proc = git("ls-remote", "--heads", "origin", f"refs/heads/{STATE['branch']}", cwd=REPO_ROOT)
    check("preflight：測試分支尚不存在於 origin", proc.stdout.strip(), "")
    STATE["ut_before"] = branch_sha("ut")
    STATE["main_before"] = branch_sha("main")
    check_true("preflight：取得 ut 的 SHA", bool(STATE["ut_before"]), "")
    check_true("preflight：取得 main 的 SHA", bool(STATE["main_before"]), "")
    a = make_clone("A", FORK_BRANCH)
    STATE["A"] = a
    STATE["fork_sha"] = git("rev-parse", "HEAD", cwd=a).stdout.strip()
    check("preflight：clone A 的 HEAD 是 GitHub 上 main 的尖端", STATE["fork_sha"], STATE["main_before"])
    (a / RECORD_DIR).mkdir(parents=True, exist_ok=True)


def step_a_push_creates_branch() -> None:
    """@purpose 完成判準 (a)：對一次性分支 commit_and_push → pushed；GitHub 上可查到該 commit，訊息含 [aidlc-sync]、files 只有 sync-state.json、作者／提交者為同步身分、parent 為分叉點（[US:S-1 AC 4]／[AC 5] 的身分半邊）。
    @given clone A 於 main 尖端；record 目錄只在工作樹（未追蹤）
    @step write_binding 1、write_sync_state {"last_status":"Ready"} | 皆 exit 0
    @step commit_and_push branch=aidlc-sync/test/<ts> | exit 0；result=pushed；attempts=1
    @step gh api commits/<sha> | message 含 [aidlc-sync]；files == [sync-state.json]；author/committer name=aidlc-sync；parents[0]=分叉點
    @step gh api branches/<ts> | commit.sha == commit_sha
    @step 檢視 clone A | HEAD 未動；git worktree list 只剩自己
    @pass 真實 GitHub 上的回寫形狀與 stub 一致
    @story S-1
    """
    a = STATE["A"]
    env = {"AIDLC_RECORD_PATH": RECORD_DIR}
    res0 = run_record("write_binding", a, dict(env, AIDLC_ISSUE_NUMBER="1"))
    check("(a) write_binding：exit 0", res0.rc, 0)
    res1 = run_record("write_sync_state", a, dict(env, AIDLC_STATE_JSON='{"last_status":"Ready"}'))
    check("(a) write_sync_state：exit 0", res1.rc, 0)

    res = run_record("commit_and_push", a, cap_env(STATE["branch"]))
    check("(a) commit_and_push：exit 0", res.rc, 0)
    check("(a) result=pushed", res.outputs.get("result"), "pushed")
    check("(a) attempts=1", res.outputs.get("attempts"), "1")
    sha = res.outputs.get("commit_sha", "")
    STATE["sha_a"] = sha
    check_true("(a) commit_sha 非空", len(sha) == 40, res.stdout + res.stderr)
    if len(sha) != 40:
        raise RuntimeError("(a) 沒拿到 commit_sha，不繼續")
    commit = gh_json(f"repos/{REPOSITORY}/commits/{sha}")
    check_true("(a) GitHub 上的訊息含 [aidlc-sync]", MARKER in commit["commit"]["message"], commit["commit"]["message"])
    check("(a) GitHub 上的 files 只有 sync-state.json", [f["filename"] for f in commit["files"]], [STATE_PATH])
    check("(a) author 為同步身分", (commit["commit"]["author"]["name"], commit["commit"]["author"]["email"]),
          ("aidlc-sync", "aidlc-sync@users.noreply.github.com"))
    check("(a) committer 為同步身分", (commit["commit"]["committer"]["name"], commit["commit"]["committer"]["email"]),
          ("aidlc-sync", "aidlc-sync@users.noreply.github.com"))
    check("(a) parent 為分叉點", [p["sha"] for p in commit["parents"]], [STATE["fork_sha"]])
    check("(a) 分支 HEAD == commit_sha", branch_sha(STATE["branch"]), sha)
    check("(a) 呼叫端 HEAD 未動", git("rev-parse", "HEAD", cwd=a).stdout.strip(), STATE["fork_sha"])
    wt = git("worktree", "list", "--porcelain", cwd=a).stdout
    check("(a) 暫存 worktree 已清", sum(1 for l in wt.splitlines() if l.startswith("worktree ")), 1)
    pushed = contents_json(STATE_PATH, STATE["branch"])
    check("(a) GitHub 上的檔案 binding=1", pushed.get("binding"), 1)
    check("(a) GitHub 上的檔案 last_status=Ready", pushed.get("last_status"), "Ready")


def step_b_real_github_non_fast_forward() -> None:
    """@purpose 完成判準 (b)：真實 GitHub 的非快轉——clone B 在受測物 fetch 之後、push 之前先推一筆帶未知欄位的檔案（git shim 製造時序）→ 第一次 push 被 GitHub 拒（fetch first）→ 重試後 pushed、attempts=2，對方欄位保留（R-3.5 ＋ R-2.3 ＋ 裁決 2）。
    @given clone B 於測試分支尖端，本機 commit {…,"x_concurrent":"from-B"}（未推）
    @given clone A 以 write_sync_state {"last_field_value":"live"} 更新工作樹（A 的 HEAD 仍是 main 尖端）
    @step A 在 shim 之下 commit_and_push（shim 於第一次 push 前先讓 B 推）| exit 0；pushed；attempts=2；shim 計 2 次 push；stderr 含 [rejected]
    @step gh api contents/<path>?ref=<ts> | x_concurrent=from-B 且 last_field_value=live 且 last_status=Ready
    @step gh api commits/<sha> | parents[0] == B 的 commit；files 只有 sync-state.json
    @pass 真實 GitHub 上的非快轉被重試且並行寫入者的欄位未被抹掉
    @story S-1
    """
    a = STATE["A"]
    b = make_clone("B", STATE["branch"])
    current = json.loads((b / STATE_PATH).read_text())
    current["x_concurrent"] = "from-B"
    (b / STATE_PATH).write_text(json.dumps(current, indent=2) + "\n")
    git("add", "-A", cwd=b)
    git("commit", "-q", "-m", f"harness：並行寫入者 {MARKER}", cwd=b)
    b_sha = git("rev-parse", "HEAD", cwd=b).stdout.strip()

    res1 = run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR,
                                              "AIDLC_STATE_JSON": '{"last_field_value":"live"}'})
    check("(b) write_sync_state：exit 0", res1.rc, 0)

    assert_test_branch(STATE["branch"])
    before = [REAL_GIT, "-C", str(b), "push", "-q", "origin", f"HEAD:refs/heads/{STATE['branch']}"]
    res = run_record("commit_and_push", a, cap_env(STATE["branch"]), before_first_push=before)
    check("(b) commit_and_push：exit 0", res.rc, 0)
    check("(b) result=pushed", res.outputs.get("result"), "pushed")
    check("(b) attempts=2", res.outputs.get("attempts"), "2")
    check("(b) shim 計 2 次 push", res.shim_pushes, 2)
    check_true("(b) 第一次 push 被 GitHub 以非快轉拒絕", "[rejected]" in res.stderr, res.stderr[-600:])
    sha = res.outputs.get("commit_sha", "")
    STATE["sha_b"] = sha
    merged = contents_json(STATE_PATH, STATE["branch"])
    check("(b) 對方欄位保留", merged.get("x_concurrent"), "from-B")
    check("(b) 本輪變更套用", merged.get("last_field_value"), "live")
    check("(b) 先前欄位仍在", merged.get("last_status"), "Ready")
    commit = gh_json(f"repos/{REPOSITORY}/commits/{sha}")
    check("(b) parent 是 B 的 commit", [p["sha"] for p in commit["parents"]], [b_sha])
    check("(b) files 只有 sync-state.json", [f["filename"] for f in commit["files"]], [STATE_PATH])
    STATE["sha_b_harness"] = b_sha


def step_c_ut_policy_rejected() -> None:
    """@purpose 完成判準 (c)：branch=ut → rejected／policy、exit 3，且 gh api 證明 ut 與 main 的 HEAD 前後相同。此步在 origin URL 被改指向不存在路徑的 clone 內執行——ut 的平台保護對本憑證不生效，不拿真實 origin 冒險。
    @given clone A；origin URL 暫改為不存在的路徑
    @step commit_and_push branch=ut | exit 3；result=rejected；reason=policy；attempts=0
    @step 還原 origin URL；gh api branches/ut、branches/main | SHA 與 preflight 相同
    @pass R-3.1 的介面層防線在 live 組態下成立且零副作用
    @story S-10
    """
    a = STATE["A"]
    git("remote", "set-url", "origin", str(STATE["root"] / "does-not-exist.git"), cwd=a)
    try:
        res = run_record("commit_and_push", a, cap_env("ut"))
        check("(c) ut：exit 3", res.rc, 3)
        check("(c) ut：result=rejected", res.outputs.get("result"), "rejected")
        check("(c) ut：reason=policy", res.outputs.get("reason"), "policy")
        check("(c) ut：attempts=0", res.outputs.get("attempts"), "0")
        check("(c) ut：shim 零次 push", res.shim_pushes, 0)
    finally:
        git("remote", "set-url", "origin", STATE["origin_url"], cwd=a)
    check("(c) ut 的 HEAD 前後相同", branch_sha("ut"), STATE["ut_before"])
    check("(c) main 的 HEAD 前後相同", branch_sha("main"), STATE["main_before"])


def step_d_delete_branch() -> None:
    """@purpose 完成判準 (d)：測畢刪除一次性分支並確認已不存在（gh api 回 404、ls-remote 為空）。
    @given 測試分支存在於 origin
    @step assert_test_branch；git push origin --delete <ts> | exit 0
    @step gh api branches/<ts> | 非零 exit 且 stderr 含 404
    @step git ls-remote --heads origin <ts> | 空
    @pass public repo 上無殘留分支
    @story S-1
    """
    assert_test_branch(STATE["branch"])
    proc = git("push", "-q", "origin", "--delete", STATE["branch"], cwd=STATE["A"])
    check("(d) 刪除分支：exit 0", proc.returncode, 0)
    STATE["deleted"] = True
    api = gh("api", f"repos/{REPOSITORY}/branches/{STATE['branch']}")
    check_true("(d) gh api 回 404", api.returncode != 0 and "404" in (api.stderr + api.stdout), api.stderr[:200])
    ls = git("ls-remote", "--heads", "origin", f"refs/heads/{STATE['branch']}", cwd=STATE["A"])
    check("(d) ls-remote 為空", ls.stdout.strip(), "")


def cleanup() -> None:
    """測畢清理（不是測試，是義務）：分支若仍在 origin 上就刪掉（過 assert_test_branch）；
    暫存目錄移除。清理失敗要大聲。"""
    try:
        if not STATE.get("deleted") and STATE.get("A") is not None:
            assert_test_branch(STATE["branch"])
            ls = git("ls-remote", "--heads", "origin", f"refs/heads/{STATE['branch']}", cwd=STATE["A"], check_rc=False)
            if ls.stdout.strip():
                proc = git("push", "-q", "origin", "--delete", STATE["branch"], cwd=STATE["A"], check_rc=False)
                if proc.returncode != 0:
                    FAILURES.append(f"cleanup：刪除分支失敗：{proc.stderr.strip()[:300]}")
                else:
                    STATE["deleted"] = True
    except SystemExit:
        raise
    except Exception as exc:
        FAILURES.append(f"cleanup：分支清理擲出例外：{exc!r}")
    finally:
        shutil.rmtree(STATE.get("root", "/nonexistent"), ignore_errors=True)


STEPS = [
    step_preflight,
    step_a_push_creates_branch,
    step_b_real_github_non_fast_forward,
    step_c_ut_policy_rejected,
    step_d_delete_branch,
]


def main() -> int:
    if not RECORD_SH.exists():
        print(f"找不到 {RECORD_SH}", file=sys.stderr)
        return 2
    # ---- 憑證與權限：拿不到就明確 skip（非零），不靜默 ----
    if shutil.which("gh") is None:
        print("SKIP：找不到 gh——live 層未執行（獨立查證通道需要它）。exit 3。", file=sys.stderr)
        return 3
    tok = gh("auth", "token")
    if tok.returncode != 0 or not tok.stdout.strip():
        print("SKIP：gh auth token 取不到憑證——live 層未執行，U-4 完成判準 (a)〜(d) 未被本次驗證。exit 3。",
              file=sys.stderr)
        return 3
    perms = gh("api", f"repos/{REPOSITORY}", "-q", ".permissions.push")
    if perms.returncode != 0 or perms.stdout.strip() != "true":
        print(f"SKIP：憑證對 {REPOSITORY} 無 push 權——live 層未執行。exit 3。", file=sys.stderr)
        return 3
    origin_url = git("remote", "get-url", "origin", cwd=REPO_ROOT).stdout.strip()
    if REPOSITORY not in origin_url:
        print(f"REFUSE：本 repo 的 origin（{origin_url}）不是 {REPOSITORY}。exit 4。", file=sys.stderr)
        return 4

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    STATE["branch"] = f"{TEST_PREFIX}{ts}"
    STATE["origin_url"] = origin_url
    STATE["root"] = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-record-live-"))
    STATE["shim_source"] = load_shim_source()
    assert_test_branch(STATE["branch"])

    print(f"live 對象：{REPOSITORY}，一次性分支 {STATE['branch']}（分叉自 {FORK_BRANCH}）")
    aborted = False
    try:
        for step in STEPS:
            before = len(FAILURES)
            try:
                step()
            except SystemExit:
                raise
            except Exception as exc:
                FAILURES.append(f"{step.__name__} 擲出例外：{exc!r}")
                if step is step_preflight:
                    aborted = True
            status = "ok" if len(FAILURES) == before else "FAIL"
            print(f"[{status}] {step.__name__}")
            if aborted:
                break
    finally:
        cleanup()

    print(f"\n{len(STEPS)} steps, {CHECKS} checks, {len(FAILURES)} failures")
    print(f"痕跡：分支 {STATE['branch']} 已刪除={STATE.get('deleted', False)}；"
          f"commit (a)={STATE.get('sha_a', '-')}；commit (b)={STATE.get('sha_b', '-')}；"
          f"harness 並行 commit={STATE.get('sha_b_harness', '-')}")
    if FAILURES:
        print("\n---- failures ----")
        for f in FAILURES:
            print(f"* {f}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
