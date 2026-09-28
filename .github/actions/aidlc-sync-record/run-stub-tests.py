#!/usr/bin/env python3
"""stub 斷言 runner — U-4「record 回寫與同步狀態」composite action（離線層）。

用法：
    python3 .github/actions/aidlc-sync-record/run-stub-tests.py

非零 exit 表失敗。

**完全離線**：每個 commit_and_push 案例都在暫存目錄建一個**本機 bare repo 當 origin**
＋ 一個（或兩個）clone 當呼叫端工作樹；bare repo 的 pre-receive hook 由測試安裝，
用來計次與模擬伺服器端拒絕（GH006 文字、非快轉文字）。**真實的**非快轉（client
side 的 `! [rejected] … (fetch first)`）以 PATH 上的 git shim 製造：攔截受測物的第一次
`push`、先讓第二個 clone 推上去、再把原 push 交給真的 git——這才是「fetch 之後、
push 之前有人先推了」的時序，hook 模擬不出來。

record.sh 本身是**真的**（不偽裝）：jq 合併、worktree、stderr 分類全部走實際路徑。
唯一被替換的是 origin 的位置（本機 bare repo）——這正是 U-4 驗證方式「④git 與 repo
行為」的離線半邊；真實 GitHub 的半邊在 run-live-tests.py。

R-2.3（未知欄位保留）是本檔最重要的一條 fixture：它反直覺、且只在跨版本情境才會
暴露，沒有這條 fixture 它會在第一次有人重構 JSON 處理時無聲消失。

規格正本：
    ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
      U-4-binding-store/functional-design/business-rules.md         （R-1〜R-4 群）
      U-4-binding-store/functional-design/domain-entities.md        （schema／相容規則）
      U-4-binding-store/nfr-requirements/security-requirements.md   （SEC-1〜SEC-4）
      U-4-binding-store/code-generation/code-generation-plan.md     （Step 6 的案例清單）
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
RECORD_SH = HERE / "record.sh"
ACTION_YML = HERE / "action.yml"

BASH = os.environ.get("AIDLC_RECORD_BASH", "bash")
REAL_GIT = shutil.which("git") or "git"

RECORD_DIR = "aidlc/spaces/default/intents/aidlc-sync-test"
STATE_PATH = f"{RECORD_DIR}/sync-state.json"
MARKER = "[aidlc-sync]"
GOOD_MESSAGE = f"雜項(aidlc-sync): 回寫同步狀態 {MARKER}"

EXPECTED_KEYS = [
    "schema_version", "binding", "last_status", "last_field_value",
    "last_reason_code", "managed_block_hash", "last_synced_at", "pending_reverse",
]

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
# git 小工具（測試自己的 commit 用固定身分，不依賴機器上的 git config）
# ==========================================================================

HARNESS_IDENTITY = {
    "GIT_AUTHOR_NAME": "harness", "GIT_AUTHOR_EMAIL": "harness@example.com",
    "GIT_COMMITTER_NAME": "harness", "GIT_COMMITTER_EMAIL": "harness@example.com",
}


def git(*args: str, cwd: pathlib.Path | str | None = None, check_rc: bool = True) -> str:
    env = dict(os.environ)
    env.update(HARNESS_IDENTITY)
    proc = subprocess.run([REAL_GIT, "-c", "commit.gpgsign=false", *args],
                          cwd=cwd, capture_output=True, text=True, env=env)
    if check_rc and proc.returncode != 0:
        raise RuntimeError(f"harness git {' '.join(args)} 失敗：{proc.stderr.strip()}")
    return proc.stdout


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_tree(root: pathlib.Path) -> dict[str, str]:
    """工作樹全部檔案的雜湊（排除 .git），用來斷言「呼叫端一個檔案都沒動」。"""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        out[str(p.relative_to(root))] = sha256_of(p)
    return out


# ==========================================================================
# 本機 origin（bare repo ＋ pre-receive hook）
# ==========================================================================

HOOK_TEMPLATE = """#!/bin/sh
# 測試安裝的 pre-receive hook：計次 ＋（有 reject 檔時）以其內容拒絕。
cat >/dev/null
printf 'push\\n' >> "%(log)s"
if [ -f "%(ctrl)s/reject" ]; then
  cat "%(ctrl)s/reject" >&2
  exit 1
fi
exit 0
"""


class Origin:
    """一個暫存目錄：origin.git（bare）＋ 若干 clone。branch 固定為 feature。"""

    def __init__(self, seed_state: dict | None = None, seed_extra: dict[str, str] | None = None):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-record-stub-"))
        self.bare = self.root / "origin.git"
        self.hook_log = self.root / "hook.log"
        self.hook_ctrl = self.root / "hook-ctrl"
        self.hook_ctrl.mkdir()
        git("init", "-q", "--bare", "--initial-branch=feature", str(self.bare))

        seed = self.root / "seed"
        git("init", "-q", "--initial-branch=feature", str(seed))
        (seed / "README.md").write_text("seed\n")
        (seed / RECORD_DIR).mkdir(parents=True)
        (seed / RECORD_DIR / "aidlc-state.md").write_text("# fixture record\n")
        if seed_state is not None:
            (seed / STATE_PATH).write_text(json.dumps(seed_state, indent=2) + "\n")
        for rel, text in (seed_extra or {}).items():
            (seed / rel).parent.mkdir(parents=True, exist_ok=True)
            (seed / rel).write_text(text)
        git("add", "-A", cwd=seed)
        git("commit", "-q", "-m", "seed", cwd=seed)
        git("push", "-q", str(self.bare), "HEAD:refs/heads/feature", cwd=seed)
        shutil.rmtree(seed)

        hook = self.bare / "hooks" / "pre-receive"
        hook.write_text(HOOK_TEMPLATE % {"log": self.hook_log, "ctrl": self.hook_ctrl})
        hook.chmod(0o755)

    def set_reject(self, text: str | None) -> None:
        f = self.hook_ctrl / "reject"
        if text is None:
            if f.exists():
                f.unlink()
        else:
            f.write_text(text)

    def clone(self, name: str) -> pathlib.Path:
        dst = self.root / name
        git("clone", "-q", "-b", "feature", str(self.bare), str(dst))
        return dst

    def head(self, branch: str = "feature") -> str | None:
        proc = subprocess.run([REAL_GIT, "-C", str(self.bare), "rev-parse", "--verify",
                               "--quiet", f"refs/heads/{branch}"], capture_output=True, text=True)
        return proc.stdout.strip() or None

    def branches(self) -> list[str]:
        out = git("for-each-ref", "--format=%(refname:short)", "refs/heads/", cwd=self.bare)
        return sorted(out.split())

    def file_json(self, path: str, branch: str = "feature"):
        proc = subprocess.run([REAL_GIT, "-C", str(self.bare), "show", f"refs/heads/{branch}:{path}"],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        return json.loads(proc.stdout)

    def commit_files(self, sha: str) -> list[str]:
        return git("show", "--format=", "--name-only", sha, cwd=self.bare).split()

    def commit_identity(self, sha: str) -> str:
        return git("log", "-1", "--format=%an|%ae|%cn|%ce", sha, cwd=self.bare).strip()

    def commit_message(self, sha: str) -> str:
        return git("log", "-1", "--format=%B", sha, cwd=self.bare).strip()

    def commit_parent(self, sha: str) -> str:
        return git("log", "-1", "--format=%P", sha, cwd=self.bare).strip()

    def hook_pushes(self) -> int:
        if not self.hook_log.exists():
            return 0
        return len(self.hook_log.read_text().splitlines())

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


# ==========================================================================
# git 的 PATH shim（製造真實的 client side 非快轉）
# ==========================================================================
# 只攔 `push` 子命令：第一次 push 之前先執行 config.json 的 before_first_push
# （另一個 clone 用真 git 推上去），然後把原 push 原封不動交給真 git——受測物於是
# 在「已 fetch、尚未 push」的視窗內被人插隊，得到真的 `! [rejected] … (fetch first)`。
# 其餘 git 子命令直接 exec 真 git。push-count 記錄受測物實際發出的 push 次數。

GIT_SHIM = '''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
REAL_GIT = %r
ctrl = pathlib.Path(os.environ["AIDLC_GIT_SHIM_DIR"])
argv = sys.argv[1:]
i = 0
while i < len(argv):
    a = argv[i]
    if a in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
        i += 2
        continue
    if a.startswith("-"):
        i += 1
        continue
    break
sub = argv[i] if i < len(argv) else ""
if sub == "push":
    cfg = json.loads((ctrl / "config.json").read_text())
    required = cfg.get("required_substring")
    if required and required not in " ".join(argv):
        sys.stderr.write("git-shim: REFUSE push without required substring %%r\\n" %% required)
        sys.exit(97)
    counter = ctrl / "push-count"
    n = int(counter.read_text()) if counter.exists() else 0
    if n == 0 and cfg.get("before_first_push"):
        subprocess.run(cfg["before_first_push"], check=True)
    counter.write_text(str(n + 1))
os.execv(REAL_GIT, [REAL_GIT] + argv)
''' % REAL_GIT


class Result:
    def __init__(self, proc: subprocess.CompletedProcess, gh_output_file: pathlib.Path,
                 tmpdir: pathlib.Path, shim_dir: pathlib.Path | None):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.gh_output = gh_output_file.read_text() if gh_output_file.exists() else ""
        self.outputs: dict[str, str] = {}
        self.stray: list[str] = []
        for line in proc.stdout.splitlines():
            if "=" in line:
                name, _, value = line.partition("=")
                self.outputs[name] = value
            elif line.strip():
                self.stray.append(line)
        # 受測物必須把自己的暫存目錄清乾淨（trap）。
        self.tmp_leftover = sorted(p.name for p in tmpdir.iterdir()) if tmpdir.exists() else []
        self.shim_pushes = 0
        if shim_dir is not None and (shim_dir / "push-count").exists():
            self.shim_pushes = int((shim_dir / "push-count").read_text())


def run_record(operation: str, cwd: pathlib.Path, env: dict | None = None,
               shim: dict | None = None, argv: list[str] | None = None) -> Result:
    """執行 record.sh 一次。cwd 為呼叫端工作樹；env 為 AIDLC_* 介面變數；
    shim 非 None 時在 PATH 前面鋪 git shim（見 GIT_SHIM）。"""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-record-run-"))
    try:
        tmpdir = tmp / "tmpdir"
        tmpdir.mkdir()
        gh_output_file = tmp / "github_output"
        full_env = dict(os.environ)
        for key in list(full_env):
            if key.startswith("AIDLC_"):
                del full_env[key]
        full_env.update(env or {})
        full_env["AIDLC_OPERATION"] = operation
        full_env["TMPDIR"] = str(tmpdir)
        full_env["GITHUB_OUTPUT"] = str(gh_output_file)
        shim_dir = None
        if shim is not None:
            shim_dir = tmp / "shim"
            shim_dir.mkdir()
            (shim_dir / "config.json").write_text(json.dumps(shim))
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            exe = bin_dir / "git"
            exe.write_text(GIT_SHIM)
            exe.chmod(0o755)
            full_env["PATH"] = f"{bin_dir}:{full_env['PATH']}"
            full_env["AIDLC_GIT_SHIM_DIR"] = str(shim_dir)
        proc = subprocess.run([BASH, str(RECORD_SH)] + (argv or []), cwd=cwd,
                              capture_output=True, text=True, env=full_env)
        return Result(proc, gh_output_file, tmpdir, shim_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def read_state(clone: pathlib.Path):
    p = clone / STATE_PATH
    return json.loads(p.read_text()) if p.exists() else None


def write_state_raw(clone: pathlib.Path, text: str) -> None:
    (clone / STATE_PATH).write_text(text)


def cap_env(branch: str = "feature", message: str = GOOD_MESSAGE, paths: str = STATE_PATH,
            **extra) -> dict:
    env = {"AIDLC_RECORD_PATH": RECORD_DIR + "/", "AIDLC_BRANCH": branch,
           "AIDLC_PATHS": paths, "AIDLC_MESSAGE": message}
    env.update(extra)
    return env


def worktree_count(clone: pathlib.Path) -> int:
    out = git("worktree", "list", "--porcelain", cwd=clone)
    return sum(1 for line in out.splitlines() if line.startswith("worktree "))


# ==========================================================================
# 介面層的機械斷言（SEC-1／分派／schema 鎖）
# ==========================================================================

def test_sec1_action_yml_no_credential_input() -> None:
    """@purpose action.yml 不得宣告任何憑證型 input——input 是公開介面，本 action 根本不讀 token（SEC-1；push 沿用呼叫端 checkout 的憑證）。
    @given 本 action 的 action.yml 原始文字
    @step 掃描 inputs: 區塊的全部 input 名稱 | 無任何名稱含 token / secret / password / credential / key
    @step 掃描 runs 步驟的 env 映射 | 不存在 GH_TOKEN／GITHUB_TOKEN 的映射
    @pass 兩項掃描皆零命中
    @story S-10
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
        if in_inputs and line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            input_names.append(line.strip().rstrip(":"))
    check_true("SEC-1：有掃到 input 清單（掃描器沒壞）", len(input_names) >= 5, f"掃到：{input_names}")
    banned = ("token", "secret", "password", "credential", "passwd", "apikey", "api_key", "api-key")
    offenders = [n for n in input_names if any(b in n.lower() for b in banned)]
    check("SEC-1：無憑證型 input 名稱", offenders, [])
    check_true("SEC-1：env 不映射任何 token", "TOKEN:" not in text, "action.yml 出現了 TOKEN 映射")


def test_action_yml_env_mapping_matches_record_sh() -> None:
    """@purpose action.yml 的 env 映射與 record.sh 實際讀取的 AIDLC_* 變數集合完全相等——多一個是死接線，少一個是 input 進不去（介面轉接層唯一會壞的方式）。
    @given action.yml 與 record.sh 原始文字
    @step 從 record.sh 抓所有 ${AIDLC_…} 引用 | 得到集合 S
    @step 從 action.yml 的 env: 區塊抓所有 AIDLC_… 鍵 | 得到集合 Y
    @pass S == Y
    @story S-1
    """
    sh = RECORD_SH.read_text()
    yml = ACTION_YML.read_text()
    used = set(re.findall(r"\$\{(AIDLC_[A-Z_]+)", sh))
    mapped = set(re.findall(r"^\s+(AIDLC_[A-Z_]+):\s+\$\{\{ inputs\.", yml, flags=re.M))
    check("env 映射：record.sh 讀的變數集合 == action.yml 映射的集合", sorted(used), sorted(mapped))


def test_unknown_operation_rejected() -> None:
    """@purpose 未知或空白 operation 一律非零 exit、不寫 result、不靜默回空值。
    @given 一個乾淨的 clone
    @step operation=push_commit（不存在）| exit 2，stdout 無 result=
    @step operation 為空 | exit 2
    @pass 兩者皆 exit 2 且無 output
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        res = run_record("push_commit", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("未知 operation：exit 2", res.rc, 2)
        check("未知 operation：無 result output", "result" in res.outputs, False)
        res2 = run_record("", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("空 operation：exit 2", res2.rc, 2)
    finally:
        o.cleanup()


def test_five_operations_dispatch() -> None:
    """@purpose 五個契約 operation 都真的接在分派表上（缺一個就是介面缺口，不是「未知」）。
    @given 各 operation 以缺 record_path 的方式執行
    @step 逐一執行五個 operation | 每個都以 exit 2 失敗於輸入驗證，stderr 不含「未知的 operation」
    @pass 五個 operation 無一落入未知分支
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        for op in ("read_binding", "write_binding", "read_sync_state", "write_sync_state",
                   "commit_and_push"):
            res = run_record(op, a, {"AIDLC_RECORD_PATH": ""})
            check_true(f"dispatch：{op} 有接上（非未知）", "未知的 operation" not in res.stderr, res.stderr)
            check(f"dispatch：{op} 在輸入驗證層失敗（exit 2）", res.rc, 2)
    finally:
        o.cleanup()


def test_record_path_shape_validation() -> None:
    """@purpose record_path 必須是 aidlc/spaces/<space>/intents/<slug>/ 且存在——絕對路徑、錯形狀、`..`、不存在的目錄都 exit 2，不會走到任何讀寫。
    @given 一個乾淨的 clone
    @step record_path=/etc | exit 2
    @step record_path=backend/ | exit 2
    @step record_path=aidlc/spaces/../intents/x | exit 2
    @step record_path=aidlc/spaces/default/intents/does-not-exist | exit 2
    @step record_path=aidlc/spaces/default/intents/aidlc-sync-test（無尾斜線）| exit 0（尾斜線可省）
    @pass 四個壞形狀全部 exit 2，合法形狀通過
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        for bad in ("/etc", "backend/", "aidlc/spaces/../intents/x",
                    "aidlc/spaces/default/intents/does-not-exist", "aidlc/spaces/default/intents/"):
            res = run_record("read_binding", a, {"AIDLC_RECORD_PATH": bad})
            check(f"record_path 形狀：'{bad}' → exit 2", res.rc, 2)
        res = run_record("read_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("record_path 無尾斜線：exit 0", res.rc, 0)
    finally:
        o.cleanup()


def test_defaults_schema_locked() -> None:
    """@purpose 鎖住 sync-state.json 的 schema：SCHEMA_VERSION=1、恰好八個鍵（domain-entities.md 的七個資料欄 ＋ schema_version）、MAX_RETRIES=3——任何一個變動都應該是有意識的（跨版本相容規則 C-1 只允許新增）。
    @given record.sh 的 defaults 診斷子命令
    @step 執行 record.sh defaults | schema_version=1；defaults_json 的鍵集合 == 八個已知鍵；max_retries=3
    @pass 三者相符
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        res = run_record("", a, {}, argv=["defaults"])
        check("defaults：exit 0", res.rc, 0)
        check("defaults：schema_version=1", res.outputs.get("schema_version"), "1")
        d = json.loads(res.outputs.get("defaults_json", "{}"))
        check("defaults：鍵集合鎖定", list(d.keys()), EXPECTED_KEYS)
        check("defaults：非 schema_version 的欄位預設皆 null",
              [v for k, v in d.items() if k != "schema_version"], [None] * 7)
        check("defaults：max_retries=3", res.outputs.get("max_retries"), "3")
    finally:
        o.cleanup()


# ==========================================================================
# 讀取層（R-1.1、R-2.2〜R-2.4）
# ==========================================================================

def test_read_absent_file_all_defaults() -> None:
    """@purpose sync-state.json 缺席時 read_sync_state 回全部預設值、不視為錯誤（R-2.2），read_binding 回空（R-1.1 觸發首建）。
    @given clone 內 record 目錄存在但無 sync-state.json
    @step read_sync_state | exit 0；state_json 等於預設值物件（八個鍵、schema_version=1、其餘 null）；binding 為空字串
    @step read_binding | exit 0；binding 為空字串
    @step 檢視 record 目錄 | 讀取不會產生檔案
    @pass 三項皆成立
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        res = run_record("read_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR + "/"})
        check("缺席：exit 0", res.rc, 0)
        state = json.loads(res.outputs.get("state_json", "null"))
        check("缺席：全部預設值", state, {k: (1 if k == "schema_version" else None) for k in EXPECTED_KEYS})
        check("缺席：binding 空字串", res.outputs.get("binding"), "")
        res2 = run_record("read_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("缺席：read_binding exit 0", res2.rc, 0)
        check("缺席：read_binding 空字串", res2.outputs.get("binding"), "")
        check("缺席：讀取不產生檔案", (a / STATE_PATH).exists(), False)
    finally:
        o.cleanup()


def test_read_missing_fields_filled() -> None:
    """@purpose 舊檔只有部分欄位時，讀取補預設值且既有值不變（R-2.2「新版讀舊檔」）。
    @given sync-state.json = {"schema_version":1,"binding":42}
    @step read_sync_state | state_json 有八個鍵；binding=42；其餘六欄為 null
    @step 檢視檔案 | 讀取不改寫檔案（內容逐位元相同）
    @pass 補預設只發生在輸出，不發生在磁碟
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        write_state_raw(a, '{"schema_version":1,"binding":42}')
        before = sha256_of(a / STATE_PATH)
        res = run_record("read_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("補預設：exit 0", res.rc, 0)
        state = json.loads(res.outputs.get("state_json", "null"))
        check("補預設：鍵集合", sorted(state.keys()), sorted(EXPECTED_KEYS))
        check("補預設：binding=42", state.get("binding"), 42)
        check("補預設：其餘為 null", [state[k] for k in EXPECTED_KEYS if k not in ("schema_version", "binding")],
              [None] * 6)
        check("補預設：binding output", res.outputs.get("binding"), "42")
        check("補預設：磁碟未動", sha256_of(a / STATE_PATH), before)
    finally:
        o.cleanup()


def test_r23_unknown_fields_survive_read_modify_write() -> None:
    """@purpose R-2.3 的必要 fixture：含未知欄位的檔案經一次 read-modify-write 後，**未知欄位仍在且值未變**——多數 JSON 處理寫法（jq -n 重建物件）會靜默丟掉它們，這條 fixture 是唯一鎖。
    @given sync-state.json 含 x_future（巢狀物件）與 y_keep（字串）兩個本版本不認得的欄位
    @step read_sync_state | state_json 內 x_future／y_keep 原樣在內（讀取半邊）
    @step write_sync_state {"last_status":"Ready"} | exit 0
    @step 重讀檔案 | x_future 與 y_keep 逐位元相同；last_status=Ready；binding 不變；八個已知鍵齊全
    @pass 未知欄位跨過一次寫入而不變
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        fixture = {"schema_version": 1, "binding": 42,
                   "x_future": {"nested": True, "list": [1, 2, 3]}, "y_keep": "keep-me"}
        write_state_raw(a, json.dumps(fixture))
        res = run_record("read_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        state = json.loads(res.outputs.get("state_json", "null"))
        check("R-2.3 讀取半邊：x_future 在輸出內", state.get("x_future"), fixture["x_future"])
        check("R-2.3 讀取半邊：y_keep 在輸出內", state.get("y_keep"), "keep-me")

        res2 = run_record("write_sync_state", a,
                          {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_STATE_JSON": '{"last_status":"Ready"}'})
        check("R-2.3 寫入：exit 0", res2.rc, 0)
        check("R-2.3 寫入：result=written", res2.outputs.get("result"), "written")
        after = read_state(a)
        check("R-2.3 寫入半邊：x_future 未變", after.get("x_future"), fixture["x_future"])
        check("R-2.3 寫入半邊：y_keep 未變", after.get("y_keep"), "keep-me")
        check("R-2.3 寫入：last_status 已套用", after.get("last_status"), "Ready")
        check("R-2.3 寫入：binding 不變", after.get("binding"), 42)
        check("R-2.3 寫入：八個已知鍵齊全", all(k in after for k in EXPECTED_KEYS), True)
    finally:
        o.cleanup()


def test_r24_higher_schema_version_not_rejected() -> None:
    """@purpose schema_version 高於本版本時不拒絕、原樣帶出（R-2.4，與 U-2 的 parse 刻意不同），且寫回不降版——即使 patch 帶了較低的 schema_version。
    @given sync-state.json = {"schema_version":99,"binding":1,"z_new":"v2-field"}
    @step read_sync_state | exit 0；state_json.schema_version=99；z_new 在內
    @step write_sync_state {"last_status":"Done","schema_version":1} | exit 0
    @step 重讀檔案 | schema_version 仍為 99；z_new 仍在；last_status=Done
    @pass 高版本檔案可讀可寫且版本只增不減
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        write_state_raw(a, '{"schema_version":99,"binding":1,"z_new":"v2-field"}')
        res = run_record("read_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("R-2.4 讀：exit 0", res.rc, 0)
        state = json.loads(res.outputs.get("state_json", "null"))
        check("R-2.4 讀：schema_version=99", state.get("schema_version"), 99)
        check("R-2.4 讀：z_new 在內", state.get("z_new"), "v2-field")
        res2 = run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR,
                                                  "AIDLC_STATE_JSON": '{"last_status":"Done","schema_version":1}'})
        check("R-2.4 寫：exit 0", res2.rc, 0)
        after = read_state(a)
        check("R-2.4 寫：schema_version 不降版（仍 99）", after.get("schema_version"), 99)
        check("R-2.4 寫：z_new 仍在", after.get("z_new"), "v2-field")
        check("R-2.4 寫：last_status=Done", after.get("last_status"), "Done")
    finally:
        o.cleanup()


def test_read_binding_absent_or_null_is_empty() -> None:
    """@purpose binding 欄位缺席與明寫 null 都讓 read_binding 回空字串（＝null，觸發首建，R-1.1）。
    @given 兩份檔案：{"schema_version":1} 與 {"schema_version":1,"binding":null}
    @step 各執行 read_binding | exit 0；binding 皆為空字串
    @pass 兩者行為相同
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        for raw in ('{"schema_version":1}', '{"schema_version":1,"binding":null}'):
            write_state_raw(a, raw)
            res = run_record("read_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
            check(f"read_binding {raw}：exit 0", res.rc, 0)
            check(f"read_binding {raw}：空字串", res.outputs.get("binding"), "")
    finally:
        o.cleanup()


def test_write_binding_roundtrip_and_validation() -> None:
    """@purpose write_binding → read_binding round-trip；且 issue_number 非正整數（abc／0／-1／空）一律 exit 2 不寫檔。
    @given clone 內無 sync-state.json
    @step write_binding 12 | exit 0；result=written；binding=12；檔案出現且八個鍵齊全、schema_version=1
    @step read_binding | binding=12
    @step write_binding abc／0／-1／空 | 各 exit 2；檔案內容不變
    @pass round-trip 成立且壞輸入零副作用
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        res = run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "12"})
        check("write_binding 12：exit 0", res.rc, 0)
        check("write_binding 12：result=written", res.outputs.get("result"), "written")
        check("write_binding 12：binding output", res.outputs.get("binding"), "12")
        state = read_state(a)
        check("write_binding 12：檔案 binding=12", state.get("binding"), 12)
        check("write_binding 12：schema_version=1", state.get("schema_version"), 1)
        check("write_binding 12：八個鍵齊全", sorted(state.keys()), sorted(EXPECTED_KEYS))
        res2 = run_record("read_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("read_binding：12", res2.outputs.get("binding"), "12")
        before = sha256_of(a / STATE_PATH)
        for bad in ("abc", "0", "-1", "", "07", "1.5"):
            res3 = run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": bad})
            check(f"write_binding '{bad}'：exit 2", res3.rc, 2)
        check("壞 issue_number：檔案未變", sha256_of(a / STATE_PATH), before)
    finally:
        o.cleanup()


def test_corrupted_json_is_external_error() -> None:
    """@purpose sync-state.json 不是合法 JSON 時，讀與寫都以 ExternalError 收場（exit 1、result=external_error），且寫入**不覆蓋**損壞檔——那是損壞，不是舊格式（R-2.2 的邊界）。
    @given sync-state.json 內容為 `{not json`
    @step read_sync_state | exit 1；result=external_error；message 非空
    @step read_binding | exit 1
    @step write_sync_state {"binding":1} | exit 1；檔案內容逐位元不變
    @pass 三次呼叫都紅燈且零覆蓋
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        write_state_raw(a, "{not json")
        before = sha256_of(a / STATE_PATH)
        for op, extra in (("read_sync_state", {}), ("read_binding", {}),
                          ("write_sync_state", {"AIDLC_STATE_JSON": '{"binding":1}'})):
            env = {"AIDLC_RECORD_PATH": RECORD_DIR}
            env.update(extra)
            res = run_record(op, a, env)
            check(f"損壞 JSON：{op} exit 1", res.rc, 1)
            check(f"損壞 JSON：{op} result=external_error", res.outputs.get("result"), "external_error")
            check_true(f"損壞 JSON：{op} message 非空", bool(res.outputs.get("message")), res.stdout)
        check("損壞 JSON：檔案未被覆蓋", sha256_of(a / STATE_PATH), before)
        # 空檔案同樣是損壞（原子替換下不會自然出現）
        write_state_raw(a, "")
        res = run_record("read_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("空檔案：exit 1", res.rc, 1)
    finally:
        o.cleanup()


def test_typed_field_corruption_is_external_error() -> None:
    """@purpose 只做兩個欄位的型別檢查：binding 非整數（字串 "7"、1.5）與 schema_version 非正整數（0、"1"）→ ExternalError；其餘欄位不解讀（last_status 放任意值也可讀）。
    @given 四份型別損壞的檔案 ＋ 一份 last_status 為數字的檔案
    @step 逐一 read_sync_state | 四份損壞者 exit 1、result=external_error
    @step last_status=123 的檔案 | exit 0（本單元不驗證該欄位）
    @pass 型別檢查範圍恰好是 schema_version 與 binding
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        for raw in ('{"schema_version":1,"binding":"7"}', '{"schema_version":1,"binding":1.5}',
                    '{"schema_version":0,"binding":1}', '{"schema_version":"1","binding":1}',
                    '[1,2]'):
            write_state_raw(a, raw)
            res = run_record("read_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
            check(f"型別損壞 {raw}：exit 1", res.rc, 1)
            check(f"型別損壞 {raw}：external_error", res.outputs.get("result"), "external_error")
        write_state_raw(a, '{"schema_version":1,"binding":1,"last_status":123}')
        res = run_record("read_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR})
        check("last_status 不驗證：exit 0", res.rc, 0)
    finally:
        o.cleanup()


def test_readonly_dir_write_is_external_error() -> None:
    """@purpose record 目錄不可寫時，write_sync_state 以 ExternalError 收場（exit 1、result=external_error，R-1.2），既有檔案不變、不留暫存檔。
    @given 非 root 執行；record 目錄 chmod 0555；既有 sync-state.json
    @step write_sync_state {"binding":3} | exit 1；result=external_error
    @step 檢視目錄 | 檔案內容不變；無 .sync-state.json.tmp.* 殘留
    @pass 寫入失敗表面化且零副作用
    @story S-1
    """
    check_true("唯讀目錄測試需要非 root（root 會無視權限位元）", os.geteuid() != 0, "以 root 執行")
    o = Origin()
    rec = None
    try:
        a = o.clone("A")
        write_state_raw(a, '{"schema_version":1,"binding":1}')
        before = sha256_of(a / STATE_PATH)
        rec = a / RECORD_DIR
        rec.chmod(0o555)
        res = run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_STATE_JSON": '{"binding":3}'})
        check("唯讀目錄：exit 1", res.rc, 1)
        check("唯讀目錄：result=external_error", res.outputs.get("result"), "external_error")
        rec.chmod(0o755)
        check("唯讀目錄：檔案未變", sha256_of(a / STATE_PATH), before)
        check("唯讀目錄：無暫存檔殘留", [p.name for p in rec.iterdir() if p.name.startswith(".sync-state")], [])
    finally:
        if rec is not None and rec.exists():
            rec.chmod(0o755)
        o.cleanup()


def test_patch_must_be_object() -> None:
    """@purpose write_sync_state 的 state_json 必須是 JSON 物件：陣列、非 JSON、空字串、含壞型別的 binding 一律 exit 2（呼叫端 bug），檔案不變。
    @given 既有 sync-state.json
    @step state_json=[1]／`nope`／空／{"binding":"x"}／{"schema_version":0} | 各 exit 2
    @step 檢視檔案 | 逐位元不變
    @pass 壞 patch 零副作用
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        write_state_raw(a, '{"schema_version":1,"binding":1}')
        before = sha256_of(a / STATE_PATH)
        for bad in ("[1]", "nope", "", '{"binding":"x"}', '{"schema_version":0}'):
            res = run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_STATE_JSON": bad})
            check(f"壞 patch {bad!r}：exit 2", res.rc, 2)
        check("壞 patch：檔案未變", sha256_of(a / STATE_PATH), before)
    finally:
        o.cleanup()


def test_pending_reverse_whole_key_overwrite() -> None:
    """@purpose pending_reverse 以整個鍵為單位覆寫（物件層淺合併）：patch 給 {observed_status} 時，舊的 observed_at 不會被殘留合併進來；patch 給 null 則清為 null。
    @given sync-state.json 的 pending_reverse = {"observed_status":"Done","observed_at":"t1"}
    @step write_sync_state {"pending_reverse":{"observed_status":"Ready"}} | 檔案 pending_reverse 恰為 {"observed_status":"Ready"}
    @step write_sync_state {"pending_reverse":null} | 檔案 pending_reverse 為 null
    @pass 巢狀物件不做深合併
    @story S-6
    """
    o = Origin()
    try:
        a = o.clone("A")
        write_state_raw(a, '{"schema_version":1,"binding":1,"pending_reverse":{"observed_status":"Done","observed_at":"t1"}}')
        res = run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR,
                                                 "AIDLC_STATE_JSON": '{"pending_reverse":{"observed_status":"Ready"}}'})
        check("整鍵覆寫：exit 0", res.rc, 0)
        check("整鍵覆寫：observed_at 不殘留", read_state(a).get("pending_reverse"), {"observed_status": "Ready"})
        res2 = run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR,
                                                  "AIDLC_STATE_JSON": '{"pending_reverse":null}'})
        check("整鍵覆寫 null：exit 0", res2.rc, 0)
        check("整鍵覆寫 null：pending_reverse=null", read_state(a).get("pending_reverse"), None)
    finally:
        o.cleanup()


def test_write_is_atomic_no_temp_leftover() -> None:
    """@purpose 寫入走「同目錄暫存檔 → mv」：成功後目錄內不留暫存檔；輸出的 state_json 與磁碟內容等價；檔案以換行結尾（pretty JSON，diff 友善）。
    @given clone 內無 sync-state.json
    @step write_sync_state {"binding":5,"last_status":"Ready"} | exit 0
    @step 列目錄 | 只有 aidlc-state.md 與 sync-state.json
    @step 比對 state_json output 與磁碟 JSON | 相等；磁碟檔以換行結尾
    @pass 原子寫入無殘留
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        res = run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR,
                                                 "AIDLC_STATE_JSON": '{"binding":5,"last_status":"Ready"}'})
        check("原子寫入：exit 0", res.rc, 0)
        check("原子寫入：目錄無殘留", sorted(p.name for p in (a / RECORD_DIR).iterdir()),
              ["aidlc-state.md", "sync-state.json"])
        check("原子寫入：output 與磁碟等價", json.loads(res.outputs.get("state_json", "null")), read_state(a))
        check_true("原子寫入：檔案以換行結尾", (a / STATE_PATH).read_text().endswith("\n"), "")
    finally:
        o.cleanup()


# ==========================================================================
# commit_and_push（R-3 群；Plan Approval 裁決 1〜4）
# ==========================================================================

def test_cap_happy_path() -> None:
    """@purpose commit_and_push 的 happy path（[US:S-1 AC 4]）：origin 上該分支多一個 commit，diff 只含 sync-state.json，訊息含 [aidlc-sync]，作者與提交者皆為預設同步身分（SEC-4）；呼叫端工作樹一個檔案都不動、HEAD 不動、暫存 worktree 已清、TMPDIR 淨空。
    @given bare origin（feature 分支）＋ clone A；A 以 write_binding 42 產生 sync-state.json
    @step commit_and_push branch=feature | exit 0；result=pushed；attempts=1；commit_sha 等於 origin/feature HEAD
    @step 檢視該 commit | 檔案清單恰為 [sync-state.json]；訊息含 [aidlc-sync]；author/committer = aidlc-sync <aidlc-sync@users.noreply.github.com>
    @step 檢視 origin 上的檔案 | binding=42、schema_version=1
    @step 檢視呼叫端 A | 工作樹雜湊、git status、HEAD 皆與呼叫前相同；git worktree list 只剩自己；TMPDIR 無殘留
    @step 檢視 stdout／GITHUB_OUTPUT | 無非 name=value 的雜訊行；GITHUB_OUTPUT 含 result heredoc
    @pass 全部成立
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "42"})
        tree_before = snapshot_tree(a)
        status_before = git("status", "--porcelain", cwd=a)
        head_before = git("rev-parse", "HEAD", cwd=a).strip()
        origin_before = o.head()

        res = run_record("commit_and_push", a, cap_env())
        check("happy：exit 0", res.rc, 0)
        check("happy：result=pushed", res.outputs.get("result"), "pushed")
        check("happy：attempts=1", res.outputs.get("attempts"), "1")
        check("happy：reason 空", res.outputs.get("reason"), "")
        sha = res.outputs.get("commit_sha", "")
        check("happy：commit_sha == origin/feature HEAD", sha, o.head())
        check_true("happy：origin 前進了", o.head() != origin_before, "")
        check("happy：commit 只含 sync-state.json", o.commit_files(sha), [STATE_PATH])
        check_true("happy：訊息含 [aidlc-sync]", MARKER in o.commit_message(sha), o.commit_message(sha))
        check("happy：同步身分（SEC-4）", o.commit_identity(sha),
              "aidlc-sync|aidlc-sync@users.noreply.github.com|aidlc-sync|aidlc-sync@users.noreply.github.com")
        pushed = o.file_json(STATE_PATH)
        check("happy：origin 上 binding=42", pushed.get("binding"), 42)
        check("happy：origin 上 schema_version=1", pushed.get("schema_version"), 1)
        check("happy：commit 的 parent 是原 origin HEAD", o.commit_parent(sha), origin_before)

        check("happy：呼叫端工作樹未動", snapshot_tree(a), tree_before)
        check("happy：呼叫端 git status 未動", git("status", "--porcelain", cwd=a), status_before)
        check("happy：呼叫端 HEAD 未動", git("rev-parse", "HEAD", cwd=a).strip(), head_before)
        check("happy：暫存 worktree 已清", worktree_count(a), 1)
        check("happy：TMPDIR 淨空", res.tmp_leftover, [])
        check("happy：stdout 無雜訊行", res.stray, [])
        check_true("happy：GITHUB_OUTPUT 含 result heredoc",
                   "result<<__AIDLC_SYNC_RECORD_EOF__\npushed\n" in res.gh_output, res.gh_output)
        check("happy：hook 計 1 次 push", o.hook_pushes(), 1)
    finally:
        o.cleanup()


def test_cap_identity_override_and_empty_rejected() -> None:
    """@purpose 同步身分可由 git_user_name／git_user_email 覆寫（U-6 可換），但不得為空（SEC-4：顯式設定，不沿用任何預設 runner 身分）。
    @given clone A 含 sync-state.json
    @step commit_and_push 帶 git_user_name=bot-x、git_user_email=x@example.com | pushed；commit 的 author/committer 為該身分
    @step commit_and_push 帶 git_user_name 為空 | exit 2；origin 未變
    @pass 覆寫生效、空值被擋
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        res = run_record("commit_and_push", a, cap_env(AIDLC_GIT_USER_NAME="bot-x", AIDLC_GIT_USER_EMAIL="x@example.com"))
        check("身分覆寫：pushed", res.outputs.get("result"), "pushed")
        check("身分覆寫：identity", o.commit_identity(res.outputs.get("commit_sha", "")),
              "bot-x|x@example.com|bot-x|x@example.com")
        head = o.head()
        run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_STATE_JSON": '{"last_status":"Ready"}'})
        res2 = run_record("commit_and_push", a, cap_env(AIDLC_GIT_USER_NAME=""))
        check("身分為空：exit 2", res2.rc, 2)
        check("身分為空：origin 未變", o.head(), head)
    finally:
        o.cleanup()


def test_cap_message_without_marker_exit2_no_change() -> None:
    """@purpose message 缺 [aidlc-sync] → exit 2（R-3.3；標記是 U-6 整輪 skip 的唯一依據，缺了機制會自己觸發自己），且 origin 零變更、hook 零計次、無 worktree 殘留。
    @given clone A 含 sync-state.json
    @step commit_and_push message="雜項: 回寫" | exit 2；無 result output
    @step 檢視 origin | HEAD 不變；hook log 為空
    @pass 前置檢查在任何 git 動作之前
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        head = o.head()
        res = run_record("commit_and_push", a, cap_env(message="雜項(aidlc-sync): 回寫同步狀態"))
        check("缺標記：exit 2", res.rc, 2)
        check("缺標記：無 result", "result" in res.outputs, False)
        check("缺標記：origin 未變", o.head(), head)
        check("缺標記：hook 零計次", o.hook_pushes(), 0)
        check("缺標記：無 worktree 殘留", worktree_count(a), 1)
        check("缺標記：TMPDIR 淨空", res.tmp_leftover, [])
    finally:
        o.cleanup()


def test_cap_path_outside_whitelist_exit2() -> None:
    """@purpose paths 白名單（R-3.2、SEC-1）：任何不等於 <record_path>/sync-state.json 的路徑——README.md、另一個 record 的 sync-state.json、不存在的檔案、空清單——一律 exit 2 且 origin 零變更。
    @given clone A 含 sync-state.json 與 README.md
    @step paths=README.md | exit 2
    @step paths="<state> README.md"（混入）| exit 2
    @step paths=aidlc/spaces/default/intents/other/sync-state.json | exit 2
    @step paths 為空 | exit 2
    @step 檢視 origin | HEAD 不變；hook 零計次
    @pass 白名單逐字比對
    @story S-10
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        head = o.head()
        for paths in ("README.md", f"{STATE_PATH} README.md",
                      "aidlc/spaces/default/intents/other/sync-state.json", "",
                      f"{RECORD_DIR}/aidlc-state.md"):
            res = run_record("commit_and_push", a, cap_env(paths=paths))
            check(f"越界 paths={paths!r}：exit 2", res.rc, 2)
        check("越界：origin 未變", o.head(), head)
        check("越界：hook 零計次", o.hook_pushes(), 0)
        # 白名單內但檔案不存在（呼叫端忘了先寫）也是接線錯誤
        (a / STATE_PATH).unlink()
        res = run_record("commit_and_push", a, cap_env())
        check("白名單內但檔案不存在：exit 2", res.rc, 2)
    finally:
        o.cleanup()


def test_cap_ut_main_policy_rejected_before_any_git() -> None:
    """@purpose R-3.1 的介面層防線（Plan Approval 裁決 1）：branch=ut／main → result=rejected、reason=policy、exit 3、attempts=0，且發生在**任何 git 動作之前**——ut 的平台保護對同步憑證不生效，這是唯一防線。
    @given clone A 含 sync-state.json，且 origin URL 已改指向不存在的路徑（若受測物碰了網路會變成 external_error 而非 rejected）
    @step commit_and_push branch=ut | exit 3；result=rejected；reason=policy；attempts=0；commit_sha 空；message 非空
    @step commit_and_push branch=main | 同上
    @step 檢視 | hook 零計次；worktree 只剩自己；TMPDIR 淨空；GITHUB_OUTPUT 含 reason
    @pass 兩個分支都在介面層被擋、零 git 網路操作
    @story S-10
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        git("remote", "set-url", "origin", str(o.root / "does-not-exist.git"), cwd=a)
        for branch in ("ut", "main"):
            res = run_record("commit_and_push", a, cap_env(branch=branch))
            check(f"policy {branch}：exit 3", res.rc, 3)
            check(f"policy {branch}：result=rejected", res.outputs.get("result"), "rejected")
            check(f"policy {branch}：reason=policy", res.outputs.get("reason"), "policy")
            check(f"policy {branch}：attempts=0", res.outputs.get("attempts"), "0")
            check(f"policy {branch}：commit_sha 空", res.outputs.get("commit_sha"), "")
            check_true(f"policy {branch}：message 非空", bool(res.outputs.get("message")), res.stdout)
            check_true(f"policy {branch}：GITHUB_OUTPUT 含 reason",
                       "reason<<__AIDLC_SYNC_RECORD_EOF__\npolicy\n" in res.gh_output, res.gh_output)
            check(f"policy {branch}：TMPDIR 淨空", res.tmp_leftover, [])
        check("policy：hook 零計次", o.hook_pushes(), 0)
        check("policy：無 worktree 殘留", worktree_count(a), 1)
    finally:
        o.cleanup()


GH006_TEXT = ("error: GH006: Protected branch update failed for refs/heads/feature.\n"
              "error: Changes must be made through a pull request.\n")


def test_cap_branch_protection_immediate_no_retry() -> None:
    """@purpose 分支保護拒絕 → rejected／branch_protection、**立即**不重試（R-3.4／R-3.5：重試一百次也一樣）：attempts=1、hook 只計 1 次、origin 未變、exit 3；message 含伺服器的 remote: 行（清洗後）。
    @given bare origin 的 pre-receive hook 回 GitHub GH006 的逐字文字
    @step commit_and_push branch=feature | exit 3；result=rejected；reason=branch_protection；attempts=1
    @step 檢視 origin | HEAD 不變；hook 計 1 次
    @step 檢視 message | 含 GH006
    @pass 永久性失敗不重試
    @story S-10
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        head = o.head()
        o.set_reject(GH006_TEXT)
        res = run_record("commit_and_push", a, cap_env())
        check("GH006：exit 3", res.rc, 3)
        check("GH006：result=rejected", res.outputs.get("result"), "rejected")
        check("GH006：reason=branch_protection", res.outputs.get("reason"), "branch_protection")
        check("GH006：attempts=1", res.outputs.get("attempts"), "1")
        check("GH006：hook 計 1 次", o.hook_pushes(), 1)
        check("GH006：origin 未變", o.head(), head)
        check_true("GH006：message 含 GH006", "GH006" in res.outputs.get("message", ""), res.outputs.get("message"))
        check("GH006：TMPDIR 淨空", res.tmp_leftover, [])
        check("GH006：無 worktree 殘留", worktree_count(a), 1)
    finally:
        o.cleanup()


def test_cap_real_non_fast_forward_retry_merges() -> None:
    """@purpose R-3.5 ＋ R-2.3 ＋ 裁決 2 一次驗到：**真實的** client side 非快轉（第二個 clone 在受測物 fetch 之後、push 之前先推了一個帶未知欄位的 sync-state.json）→ 第一次 push 被拒（fetch first）→ 重試後 pushed、attempts=2，且 origin 上的檔案同時含對方的未知欄位與本輪的變更。
    @given origin 的 feature 已有 sync-state.json {"schema_version":1,"binding":7}；clone A 與 clone B
    @given B 本機 commit 了 {"schema_version":1,"binding":7,"x_from_b":"keep"}（尚未推）
    @given A 以 write_sync_state {"last_status":"Ready"} 更新工作樹
    @step A 在 git shim 之下 commit_and_push（shim 於第一次 push 前先讓 B 推上去）| exit 0；result=pushed；attempts=2；shim 計 2 次 push
    @step 檢視 origin/feature 的 sync-state.json | x_from_b=keep 且 last_status=Ready 且 binding=7
    @step 檢視 origin 歷史 | 受測物的 commit 的 parent 是 B 的 commit；該 commit 只含 sync-state.json
    @pass 非快轉被重試且並行寫入者的欄位未被抹掉
    @story S-1
    """
    o = Origin(seed_state={"schema_version": 1, "binding": 7})
    try:
        a = o.clone("A")
        b = o.clone("B")
        (b / STATE_PATH).write_text(json.dumps({"schema_version": 1, "binding": 7, "x_from_b": "keep"}, indent=2) + "\n")
        git("add", "-A", cwd=b)
        git("commit", "-q", "-m", "B 的並行寫入", cwd=b)
        b_sha = git("rev-parse", "HEAD", cwd=b).strip()

        run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_STATE_JSON": '{"last_status":"Ready"}'})
        shim = {"before_first_push": [REAL_GIT, "-C", str(b), "push", "-q", "origin", "HEAD:refs/heads/feature"]}
        res = run_record("commit_and_push", a, cap_env(), shim=shim)
        check("真實非快轉：exit 0", res.rc, 0)
        check("真實非快轉：result=pushed", res.outputs.get("result"), "pushed")
        check("真實非快轉：attempts=2", res.outputs.get("attempts"), "2")
        check("真實非快轉：shim 計 2 次 push", res.shim_pushes, 2)
        check_true("真實非快轉：第一次 push 的 stderr 是 client side 拒絕",
                   "[rejected]" in res.stderr and ("fetch first" in res.stderr or "non-fast-forward" in res.stderr),
                   res.stderr)
        merged = o.file_json(STATE_PATH)
        check("真實非快轉：對方欄位保留", merged.get("x_from_b"), "keep")
        check("真實非快轉：本輪變更套用", merged.get("last_status"), "Ready")
        check("真實非快轉：binding 不變", merged.get("binding"), 7)
        sha = res.outputs.get("commit_sha", "")
        check("真實非快轉：commit 的 parent 是 B 的 commit", o.commit_parent(sha), b_sha)
        check("真實非快轉：commit 只含 sync-state.json", o.commit_files(sha), [STATE_PATH])
        check("真實非快轉：hook 計 2 次（B 一次、A 重試一次；被拒的那次沒到伺服器）", o.hook_pushes(), 2)
        check("真實非快轉：TMPDIR 淨空", res.tmp_leftover, [])
        check("真實非快轉：無 worktree 殘留", worktree_count(a), 1)
    finally:
        o.cleanup()


def test_cap_non_fast_forward_exhausted() -> None:
    """@purpose 非快轉重試用罄：hook 每次都回非快轉文字 → 第 4 次放棄，rejected／non_fast_forward_exhausted、attempts=3、hook 計 3 次、exit 3、origin 未變。
    @given bare origin 的 pre-receive hook 每次都以 non-fast-forward 文字拒絕
    @step commit_and_push branch=feature | exit 3；result=rejected；reason=non_fast_forward_exhausted；attempts=3
    @step 檢視 origin | hook 計 3 次；HEAD 不變
    @pass 上限 MAX_RETRIES=3 生效
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        head = o.head()
        o.set_reject("error: simulated non-fast-forward update rejected\n")
        res = run_record("commit_and_push", a, cap_env())
        check("用罄：exit 3", res.rc, 3)
        check("用罄：result=rejected", res.outputs.get("result"), "rejected")
        check("用罄：reason=non_fast_forward_exhausted", res.outputs.get("reason"), "non_fast_forward_exhausted")
        check("用罄：attempts=3", res.outputs.get("attempts"), "3")
        check("用罄：hook 計 3 次", o.hook_pushes(), 3)
        check("用罄：origin 未變", o.head(), head)
        check("用罄：TMPDIR 淨空", res.tmp_leftover, [])
        check("用罄：無 worktree 殘留", worktree_count(a), 1)
    finally:
        o.cleanup()


def test_cap_branch_absent_created_from_head() -> None:
    """@purpose 分支不存在於 origin 時以呼叫端 HEAD 為分叉點建立並 pushed（U-8 的 aidlc-sync/reverse/* 與 U-7 的自建分支都走這條）。
    @given clone A（HEAD=feature 尖端）含 sync-state.json；origin 無 aidlc-sync/reverse/x
    @step commit_and_push branch=aidlc-sync/reverse/x | exit 0；pushed；attempts=1
    @step 檢視 origin | 新分支存在；其 HEAD 的 parent == 呼叫端 HEAD；只含 sync-state.json；feature 未變
    @pass 新分支正確分叉
    @story S-6
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "9"})
        head = git("rev-parse", "HEAD", cwd=a).strip()
        feature_before = o.head()
        res = run_record("commit_and_push", a, cap_env(branch="aidlc-sync/reverse/x"))
        check("新分支：exit 0", res.rc, 0)
        check("新分支：pushed", res.outputs.get("result"), "pushed")
        check("新分支：attempts=1", res.outputs.get("attempts"), "1")
        check("新分支：origin 有該分支", "aidlc-sync/reverse/x" in o.branches(), True)
        sha = o.head("aidlc-sync/reverse/x")
        check("新分支：commit_sha 相符", res.outputs.get("commit_sha"), sha)
        check("新分支：parent == 呼叫端 HEAD", o.commit_parent(sha), head)
        check("新分支：只含 sync-state.json", o.commit_files(sha), [STATE_PATH])
        check("新分支：feature 未變", o.head(), feature_before)
    finally:
        o.cleanup()


def test_cap_origin_ahead_first_attempt_merges() -> None:
    """@purpose origin 已領先呼叫端 HEAD（並行寫入者在本輪開始前就推了）時，**首次嘗試就做三方鍵層合併**、attempts=1，對方欄位保留——若只在重試時合併，這條路徑會靜默抹掉對方的欄位且永遠不觸發非快轉。
    @given origin 的 feature 已有 {"schema_version":1,"binding":7}；clone A 與 B；B 推了 {"schema_version":1,"binding":7,"x_from_b":"keep"}（A 未 fetch）
    @given A 以 write_sync_state {"last_status":"In progress"} 更新工作樹
    @step A commit_and_push | pushed；attempts=1
    @step 檢視 origin 的檔案 | x_from_b=keep 且 last_status=In progress
    @pass 首次即合併
    @story S-1
    """
    o = Origin(seed_state={"schema_version": 1, "binding": 7})
    try:
        a = o.clone("A")
        b = o.clone("B")
        (b / STATE_PATH).write_text(json.dumps({"schema_version": 1, "binding": 7, "x_from_b": "keep"}) + "\n")
        git("add", "-A", cwd=b)
        git("commit", "-q", "-m", "B 先推", cwd=b)
        git("push", "-q", "origin", "HEAD:refs/heads/feature", cwd=b)
        run_record("write_sync_state", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_STATE_JSON": '{"last_status":"In progress"}'})
        res = run_record("commit_and_push", a, cap_env())
        check("領先：exit 0", res.rc, 0)
        check("領先：pushed", res.outputs.get("result"), "pushed")
        check("領先：attempts=1", res.outputs.get("attempts"), "1")
        merged = o.file_json(STATE_PATH)
        check("領先：對方欄位保留", merged.get("x_from_b"), "keep")
        check("領先：本輪變更套用", merged.get("last_status"), "In progress")
    finally:
        o.cleanup()


def test_cap_idempotent_rerun_no_new_commit() -> None:
    """@purpose 同一輪重跑（[US:S-1 AC 6] 的精神）：工作樹內容與 origin 已一致時不產生新 commit——result=pushed、attempts=0、commit_sha 為既有 HEAD、origin 未變、hook 零計次。
    @given clone A 已成功 commit_and_push 一次
    @step 再次 commit_and_push（同內容）| exit 0；pushed；attempts=0；commit_sha == 第一次的 sha
    @step 檢視 origin | HEAD 不變；hook 計次仍為 1
    @pass 冪等
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        first = run_record("commit_and_push", a, cap_env())
        check("冪等：第一次 pushed", first.outputs.get("result"), "pushed")
        sha = first.outputs.get("commit_sha", "")
        second = run_record("commit_and_push", a, cap_env())
        check("冪等：第二次 exit 0", second.rc, 0)
        check("冪等：第二次 pushed", second.outputs.get("result"), "pushed")
        check("冪等：第二次 attempts=0", second.outputs.get("attempts"), "0")
        check("冪等：commit_sha 為既有 HEAD", second.outputs.get("commit_sha"), sha)
        check("冪等：origin 未變", o.head(), sha)
        check("冪等：hook 計次仍 1", o.hook_pushes(), 1)
    finally:
        o.cleanup()


def test_cap_unreachable_origin_is_external_error() -> None:
    """@purpose push 失敗成因不是非快轉也不是分支保護（網路、認證、遠端不存在）→ ExternalError（exit 1、result=external_error），不重試、不偽裝成 rejected。
    @given clone A 的 origin URL 指向不存在的路徑；branch=feature（非 ut／main）
    @step commit_and_push | exit 1；result=external_error；message 非空
    @pass 其他失敗表面化為紅燈
    @story S-8
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        git("remote", "set-url", "origin", str(o.root / "does-not-exist.git"), cwd=a)
        res = run_record("commit_and_push", a, cap_env())
        check("遠端不可達：exit 1", res.rc, 1)
        check("遠端不可達：result=external_error", res.outputs.get("result"), "external_error")
        check_true("遠端不可達：message 非空", bool(res.outputs.get("message")), res.stdout)
        check("遠端不可達：TMPDIR 淨空", res.tmp_leftover, [])
        check("遠端不可達：無 worktree 殘留", worktree_count(a), 1)
    finally:
        o.cleanup()


def test_cap_invalid_branch_name_exit2() -> None:
    """@purpose branch 不是合法的純分支名（refs/ 前綴、`..`、尾斜線、空）→ exit 2，零 git 動作。
    @given clone A 含 sync-state.json，origin URL 指向不存在的路徑
    @step branch=refs/heads/feature／bad..name／feature/／空 | 各 exit 2
    @pass 壞分支名在介面層被擋
    @story S-1
    """
    o = Origin()
    try:
        a = o.clone("A")
        run_record("write_binding", a, {"AIDLC_RECORD_PATH": RECORD_DIR, "AIDLC_ISSUE_NUMBER": "1"})
        git("remote", "set-url", "origin", str(o.root / "does-not-exist.git"), cwd=a)
        for bad in ("refs/heads/feature", "bad..name", "feature/", "", "-x"):
            res = run_record("commit_and_push", a, cap_env(branch=bad))
            check(f"壞分支名 {bad!r}：exit 2", res.rc, 2)
    finally:
        o.cleanup()


# ==========================================================================
# 清單與進入點
# ==========================================================================

TESTS = [
    test_sec1_action_yml_no_credential_input,
    test_action_yml_env_mapping_matches_record_sh,
    test_unknown_operation_rejected,
    test_five_operations_dispatch,
    test_record_path_shape_validation,
    test_defaults_schema_locked,
    test_read_absent_file_all_defaults,
    test_read_missing_fields_filled,
    test_r23_unknown_fields_survive_read_modify_write,
    test_r24_higher_schema_version_not_rejected,
    test_read_binding_absent_or_null_is_empty,
    test_write_binding_roundtrip_and_validation,
    test_corrupted_json_is_external_error,
    test_typed_field_corruption_is_external_error,
    test_readonly_dir_write_is_external_error,
    test_patch_must_be_object,
    test_pending_reverse_whole_key_overwrite,
    test_write_is_atomic_no_temp_leftover,
    test_cap_happy_path,
    test_cap_identity_override_and_empty_rejected,
    test_cap_message_without_marker_exit2_no_change,
    test_cap_path_outside_whitelist_exit2,
    test_cap_ut_main_policy_rejected_before_any_git,
    test_cap_branch_protection_immediate_no_retry,
    test_cap_real_non_fast_forward_retry_merges,
    test_cap_non_fast_forward_exhausted,
    test_cap_branch_absent_created_from_head,
    test_cap_origin_ahead_first_attempt_merges,
    test_cap_idempotent_rerun_no_new_commit,
    test_cap_unreachable_origin_is_external_error,
    test_cap_invalid_branch_name_exit2,
]


def main() -> int:
    if not RECORD_SH.exists():
        print(f"找不到 {RECORD_SH}", file=sys.stderr)
        return 2
    if shutil.which("jq") is None:
        print("找不到 jq（record.sh 的硬依賴）", file=sys.stderr)
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
