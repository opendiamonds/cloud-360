#!/usr/bin/env python3
"""live 斷言 runner — U-6「正向同步 workflow」的編排層（真實 API 層）。

用法：
    GH_TOKEN="$(gh auth token)" python3 .github/actions/aidlc-sync-forward/run-live-tests.py

非零 exit 表失敗或**不完整**：GH_TOKEN 缺席且 `gh auth token` 也拿不到時，本 runner
以 exit 3 明確聲明「live 層未執行」——不靜默跳過。

**寫入對象只有測試看板 #23**（ADR-A3 ＋ ADR-0016 §3 的兩個限定條件：與 repo 同
擁有者、Status 選項與 #16 同名）。SEC-3 防呆：進場即斷言 AIDLC_PROJECT_NUMBER
!= 16，不符即 exit 4——同一份憑證同時寫得了 #16，**隔離只靠這個設定值、不靠權限**。

git 的那一半刻意是**本機的**：沙箱的 origin 是一個本機 bare repo（file://），
所以 U-4 的 commit_and_push 走的是真實 git 但推不到 GitHub。理由有二——(1) 對真實
origin 的 push 已由 U-4 自己的 run-live-tests.py 涵蓋（一次性分支 ＋ 三層防呆），
在此重跑只是把同一個風險再擔一次；(2) 本單元 live 層的價值在 **Projects v2 /
Issues 那一側**。**不對 ut／main 發出任何 push**（U-4 run-live-tests.py:19-20 的
既有判準），連本機 origin 上的分支名也用 aidlc-sync/test/<utc-ts>。

stub 與 live 的分工
------------------
只有 live 驗得到（本檔）：
    (L1) `gh pr list --json number,state,closedAt,mergedAt,files` 的欄位集合在
         真實 gh 上合法——寫錯欄位名會讓 R-2.5 的 fail-closed 每一輪都觸發，而
         stub 的 gh shim 永遠不會反對任何欄位名。
    (L2) 真實 GraphQL 回應形狀跑得完整條寫入鏈（write_status → write_field →
         write_body → read_item），且看板上真的變了。
    (L3) **R-5.4 的雜湊等價性**（ADR-0015 §10 點名最危險的失敗模式）：本單元回寫
         的 managed_block_hash，必須等於 U-8 日後對**GitHub 實際存下來的 body**
         走 read_item → parse → content_hash 算出的值。差一個位元組（換行、CRLF、
         markdown 轉義）就會讓 U-8 每天為每個 intent 開一則反向 PR，而這種差異
         只有真的存進 GitHub 再讀回來才會顯現——stub 結構上驗不到。
    (L4) 首建路徑 create_item → write_binding → 同一輪寫 Status（[US:S-1 AC 1]）。

只有 stub 驗得到（run-orchestration-tests.py）：R-5.12 的四種失敗分支（真實 API
構造不出「write_body 成功但回讀拋 ExternalError」）、R-3.0 閘門的「一個看板呼叫
都沒有」（要攔得住呼叫才數得出零）、R-2.5 的 fail-closed、SEC-1 的憑證不外流、
R-6.1 的鍵來源。

測試殘留：#538 的 Status 與 body 測畢還原；(L4) 建立的 issue 測畢以 deleteIssue
刪除（刪不掉就大聲失敗，不留一則沒人認得的 issue）；測試自訂欄位
aidlc-sync-test-stage 測畢刪除。cleanup 失敗要大聲——殘留要被看見。
"""

from __future__ import annotations

import datetime
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
    sys.stderr.write("找不到 PyYAML。本檔用它抽出受測腳本；請先 pip install pyyaml\n")
    raise SystemExit(2)

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
IMPL_YML = REPO_ROOT / ".github" / "workflows" / "aidlc-sync-forward-impl.yml"
ACTIONS_SRC = REPO_ROOT / ".github" / "actions"
BLOCK_SH = ACTIONS_SRC / "aidlc-sync-block" / "block.sh"
BOARD_SH = ACTIONS_SRC / "aidlc-sync-board" / "board.sh"

# 兩個啟動器，因為受測物有兩種、真實 CI 給它們的旗標不同：
#   · BASH ——直接跑 *.sh（block.sh／board.sh）。真實 CI 走 action.yml 的
#     `shell: bash` ＋ `run: bash "${GITHUB_ACTION_PATH}/block.sh"`，而**巢狀的
#     `bash <file>` 不繼承父 shell 的 errexit**，所以這裡就是不帶旗標的 bash。
#   · IMPL_BASH ——跑從 impl workflow 抽出來的 orchestrate 腳本。那個 step 沒有
#     `shell:`，GitHub 以 `bash -e {0}` 啟動它，故此處必須帶 `-e` 才與 CI 同語意
#     （F5：`set -uo pipefail` 加不掉已生效的 `-e`）。
# shlex 兩者皆用，覆寫值才能帶旗標而不會被當成單一檔名。
BASH = shlex.split(os.environ.get("AIDLC_FORWARD_BASH", "bash"))
IMPL_BASH = shlex.split(os.environ.get("AIDLC_FORWARD_IMPL_BASH", "bash -e"))
RECORD_ROOT = "aidlc/spaces/default/intents"

PROJECT_OWNER = os.environ.get("AIDLC_PROJECT_OWNER", "opendiamonds")
PROJECT_NUMBER = os.environ.get("AIDLC_PROJECT_NUMBER", "23")

# SEC-3 的唯一禁區。具名常數而非散落的字面值——這道防線是使用者明示的硬約束
# （「用測試看板 #23，不要碰 #16」），它的值不該要靠 grep 才找得到。
LIVE_FORBIDDEN_PROJECT = 16
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "opendiamonds/cloud-360")
BINDING = os.environ.get("AIDLC_LIVE_BINDING", "538")
TEST_FIELD = "aidlc-sync-test-stage"
LIVE_INTENT = "aidlc-sync-fwd-live"
NEW_INTENT = "aidlc-sync-fwd-live-new"

FAILURES: list[str] = []
CHECKS = 0
TOKEN = ""
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


# ==========================================================================
# 受測物與獨立查證通道
# ==========================================================================

def orchestrate_script() -> str:
    doc = yaml.safe_load(IMPL_YML.read_text(encoding="utf-8"))
    for step in doc["jobs"]["forward"]["steps"]:
        if step.get("id") == "orchestrate":
            return step["run"]
    raise SystemExit("找不到 id: orchestrate 的 step。")


SCRIPT = orchestrate_script()

REPO_OWNER, REPO_NAME = REPOSITORY.split("/", 1)


def gh(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["GH_TOKEN"] = TOKEN
    return subprocess.run(["gh", *args], capture_output=True, text=True, env=env)


def gql(query: str, **variables) -> dict:
    """本 runner **自己的**查證通道：不經 board.sh，避免拿受測物驗受測物。"""
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += (["-F", f"{k}={v}"] if isinstance(v, int) else ["-f", f"{k}={v}"])
    proc = gh(*args)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api graphql 失敗：{proc.stderr.strip()}")
    return json.loads(proc.stdout)


ITEM_QUERY = """
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){
    issue(number:$number){
      id title body state
      projectItems(first:20){ nodes {
        id project { number }
        fieldValues(first:60){ nodes {
          ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2SingleSelectField { name } } }
          ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon { name } } }
        } }
      } }
    }
  }
}
"""


def issue_snapshot(number: int | str) -> dict:
    data = gql(ITEM_QUERY, owner=REPO_OWNER, name=REPO_NAME, number=int(number))
    issue = data["data"]["repository"]["issue"]
    if issue is None:
        raise RuntimeError(f"issue #{number} 不存在")
    item = None
    for node in issue["projectItems"]["nodes"]:
        if node["project"]["number"] == int(PROJECT_NUMBER):
            item = node
            break
    status = ""
    field_value = ""
    if item:
        for fv in item["fieldValues"]["nodes"]:
            fname = (fv.get("field") or {}).get("name")
            if fname == "Status" and "name" in fv:
                status = fv["name"] or ""
            elif fname == TEST_FIELD and "text" in fv:
                field_value = fv["text"] or ""
    return {"id": issue["id"], "title": issue["title"], "body": issue["body"] or "",
            "state": issue["state"], "on_board": item is not None,
            "status": status, "field_value": field_value}


def patch_body(number: int | str, body: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump({"body": body}, fh)
        path = fh.name
    try:
        proc = gh("api", "-X", "PATCH", f"repos/{REPOSITORY}/issues/{number}", "--input", path)
        if proc.returncode != 0:
            raise RuntimeError(f"PATCH body 失敗：{proc.stderr.strip()}")
    finally:
        os.unlink(path)


def block_raw(operation: str, **env_extra) -> str:
    """block.sh 的原始 stdout。render 的輸出是**多行原文**而不是 name=value——
    那是四個 operation 中唯一的例外（block.sh 的註解逐字說明過），所以取 sigil
    這種事必須走這條，不能套 name=value 的解析。"""
    env = dict(os.environ)
    env.pop("GH_TOKEN", None)
    env["AIDLC_OPERATION"] = operation
    env["GITHUB_OUTPUT"] = ""
    env.update(env_extra)
    proc = subprocess.run([*BASH, str(BLOCK_SH)], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"block.sh {operation} 失敗：{proc.stderr.strip()}")
    return proc.stdout


def block_sh(operation: str, **env_extra) -> dict:
    out = {}
    for line in block_raw(operation, **env_extra).splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


def board_sh(operation: str, **env_extra) -> dict:
    env = dict(os.environ)
    env.update({
        "GH_TOKEN": TOKEN,
        "AIDLC_PROJECT_OWNER": PROJECT_OWNER,
        "AIDLC_PROJECT_NUMBER": PROJECT_NUMBER,
        "AIDLC_FIELD_NAME": TEST_FIELD,
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_OUTPUT": "",
        "AIDLC_OPERATION": operation,
    })
    env.update(env_extra)
    proc = subprocess.run([*BASH, str(BOARD_SH)], capture_output=True, text=True, env=env)
    out = {"__rc": str(proc.returncode)}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


# ==========================================================================
# 沙箱：真實五支 action ＋ 本機 bare origin
# ==========================================================================

def build_sandbox(td: pathlib.Path, records: dict[str, dict]) -> tuple[pathlib.Path, str]:
    """records: {dirName: {"binding": int|None}}；狀態檔取自本 intent 的真實 record。

    回傳 (workspace 路徑, 分支名)。
    """
    ws = td / "ws"
    ws.mkdir(parents=True)
    shutil.copytree(ACTIONS_SRC, ws / ".github" / "actions")

    root = ws / RECORD_ROOT
    root.mkdir(parents=True)
    registry = [{"dirName": name} for name in records]
    (root / "intents.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    # 狀態檔取自**真實引擎產生**的 record（本 intent 自己的），不手寫 fixture——
    # 手寫的會與引擎格式漂移，而本檔要驗的正是真實判定跑得完整條鏈。
    source_state = (REPO_ROOT / RECORD_ROOT / "260822-gh-projects-sync" / "aidlc-state.md")
    for name, cfg in records.items():
        rd = root / name
        rd.mkdir(parents=True)
        shutil.copyfile(source_state, rd / "aidlc-state.md")
        if cfg.get("binding") is not None:
            (rd / "sync-state.json").write_text(json.dumps({
                "schema_version": 1, "binding": cfg["binding"],
                "last_status": cfg.get("last_status"),
                "last_field_value": cfg.get("last_field_value"),
                "last_reason_code": cfg.get("last_reason_code"),
                "managed_block_hash": None, "last_synced_at": None, "pending_reverse": None,
            }, ensure_ascii=False), encoding="utf-8")

    # 本機 bare origin：真實 git，但推不到 GitHub。
    origin = td / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    branch = "aidlc-sync/test/" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    assert_test_branch(branch)
    run = lambda *a: subprocess.run(list(a), cwd=str(ws), check=True,
                                    capture_output=True, text=True)
    run("git", "init", "-q", "-b", branch)
    run("git", "config", "user.name", "aidlc-sync-live")
    run("git", "config", "user.email", "aidlc-sync-live@users.noreply.github.com")
    run("git", "remote", "add", "origin", f"file://{origin}")
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "測試(live): U-6 編排層的沙箱基準")
    run("git", "push", "-q", "origin", f"HEAD:refs/heads/{branch}")
    return ws, branch


def assert_test_branch(branch: str) -> None:
    """U-4 run-live-tests.py 的既有判準：不對 ut／main 發出任何 push。"""
    if branch in ("ut", "main") or not branch.startswith("aidlc-sync/test/"):
        sys.stderr.write(f"REFUSE：分支名 {branch!r} 不是一次性測試分支。exit 4。\n")
        raise SystemExit(4)


def run_orchestrator(ws: pathlib.Path, branch: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("GITHUB_TOKEN", None)
    env.update({
        "GITHUB_WORKSPACE": str(ws),
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_OUTPUT": str(ws / ".step_output"),
        "GH_TOKEN": TOKEN,
        "AIDLC_PROJECT_OWNER": PROJECT_OWNER,
        "AIDLC_PROJECT_NUMBER": PROJECT_NUMBER,
        "AIDLC_FIELD_NAME": TEST_FIELD,
        "AIDLC_RECORD_ROOT": RECORD_ROOT,
        "AIDLC_WHITELIST": "",
        "AIDLC_FIELD_MAX_LENGTH": "50",
        "AIDLC_SYNC_BRANCH": branch,
    })
    return subprocess.run([*IMPL_BASH, "-c", SCRIPT], cwd=str(ws), env=env,
                          capture_output=True, text=True)


# ==========================================================================
# 測試主體（有序；共享狀態記錄於 STATE）
# ==========================================================================

def step_preflight() -> None:
    """@purpose 進場防呆與基準採樣：SEC-3 斷言目標非 #16；記下 #538 的原始 Status 與 body 供測畢還原；殘留的受管區塊（前次 run 中斷的產物）先清掉。
    @given 憑證已解析；測試看板 #23（opendiamonds 名下，ADR-0016 §3 的兩個限定條件已由 PRE-1 建立）
    @step 讀 #538 的 item、Status、body | issue 存在、open、且在 #23 上
    @step body 若含受管標記（前次殘留）| 依本 runner 自己的附加形狀切除並還原
    @pass 基準記錄完成
    @story S-1
    """
    snap = issue_snapshot(BINDING)
    check_true(f"preflight：issue #{BINDING} 在 #{PROJECT_NUMBER} 上", snap["on_board"],
               "反查不到 item——測試前提不成立")
    check(f"preflight：issue #{BINDING} 是 open", snap["state"], "OPEN")
    sigil = block_raw("render", AIDLC_STATUS="Ready", AIDLC_TRACEABLE_ROW="x",
                      AIDLC_SCOPE_NOTE="n").splitlines()[0]
    body = snap["body"]
    if sigil in body:
        pos = body.find("\n\n" + sigil)
        clean = body[:pos] if pos >= 0 else ("" if body.startswith(sigil) else body)
        check_true("preflight：殘留區塊可定位切除", sigil not in clean, "切除後仍有標記")
        patch_body(BINDING, clean)
        body = clean
    STATE["sigil"] = sigil
    STATE["orig_body"] = body
    STATE["orig_status"] = snap["status"]


def test_l1_gh_pr_list_field_set_is_valid() -> None:
    """@purpose (L1) 受測腳本查反向 PR 用的欄位集合在真實 gh 上必須合法。欄位名寫錯時 gh 以非零 exit 收場 → R-2.5 的 fail-closed 每一輪都會觸發、整個機制永遠不寫任何東西，而 stub 的 gh shim 對任何欄位名都不會反對。
    @given 真實 gh 與真實 repo
    @step 以受測腳本逐字相同的欄位集合查一次 | exit 0 且輸出是合法 JSON 陣列
    @pass 欄位集合合法
    @story S-6
    """
    fields = re.search(r"--json ([a-zA-Z,]+)", SCRIPT)
    check_true("能從受測腳本抽出 --json 欄位集合", fields is not None, SCRIPT[:200])
    if not fields:
        return
    proc = gh("pr", "list", "--repo", REPOSITORY, "--label", "aidlc-sync-reverse",
              "--state", "all", "--limit", "1", "--json", fields.group(1))
    check("(L1) gh pr list 的欄位集合合法（exit 0）", proc.returncode, 0)
    if proc.returncode == 0:
        check_true("(L1) 輸出為 JSON 陣列", isinstance(json.loads(proc.stdout), list), proc.stdout[:200])


def test_l2_full_write_chain() -> None:
    """@purpose (L2) 真實 GraphQL 回應形狀跑得完整條寫入鏈，且看板上真的變了：已綁定 ＋ 三欄過期 → write_status → write_field → render → write_body → 回讀 → 回寫 → 推送。
    @given 沙箱 record 綁定 issue #538，sync-state.json 的三欄刻意過期（漂移必然成立）
    @step 跑一輪編排 | exit 0
    @step 獨立查證 #538 的 Status | 等於本輪判定的 Status
    @step 獨立查證自訂欄位 | 等於本輪判定的 field_value
    @step 獨立查證 issue body | 含受管標記
    @step 讀沙箱的 sync-state.json | 五欄都寫了，managed_block_hash 非 null
    @step 讀本機 origin 的 HEAD | 訊息含同步標記、變更只有 sync-state.json
    @pass 整條鏈在真實 API 上成立
    @story S-2
    """
    td = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-fwd-live-"))
    STATE["td_l2"] = td
    ws, branch = build_sandbox(td, {LIVE_INTENT: {
        "binding": int(BINDING), "last_status": STATE["orig_status"] or None,
        "last_field_value": "stale-value", "last_reason_code": "parked"}})
    proc = run_orchestrator(ws, branch)
    STATE["l2_log"] = proc.stdout + proc.stderr
    check("(L2) 編排 exit 0", proc.returncode, 0)

    state = json.loads((ws / RECORD_ROOT / LIVE_INTENT / "sync-state.json").read_text(encoding="utf-8"))
    STATE["l2_state"] = state
    snap = issue_snapshot(BINDING)
    STATE["l2_snap"] = snap
    check("(L2) 看板 Status 等於本輪判定", snap["status"], state["last_status"])
    check("(L2) 自訂欄位等於本輪判定", snap["field_value"], state["last_field_value"])
    check_true("(L2) issue body 含受管標記", STATE["sigil"] in snap["body"], snap["body"][:200])
    check_true("(L2) managed_block_hash 非 null", bool(state["managed_block_hash"]), str(state))
    check_true("(L2) last_synced_at 非 null", bool(state["last_synced_at"]), str(state))

    log = subprocess.run(["git", "log", "-1", "--format=%B", f"origin/{branch}"],
                         cwd=str(ws), capture_output=True, text=True)
    check_true("(L2) 回寫 commit 的訊息含 [aidlc-sync]", "[aidlc-sync]" in log.stdout, log.stdout)
    files = subprocess.run(["git", "show", "--name-only", "--format=", f"origin/{branch}"],
                           cwd=str(ws), capture_output=True, text=True)
    check("(L2) 回寫只碰 sync-state.json",
          sorted(x for x in files.stdout.split() if x),
          [f"{RECORD_ROOT}/{LIVE_INTENT}/sync-state.json"])


def test_l3_hash_equivalence_with_u8_path() -> None:
    """@purpose (L3) R-5.4／ADR-0015 §10 的等價不變式：本單元回寫的 managed_block_hash，必須等於 U-8 日後對 **GitHub 實際存下來的 body** 走 read_item → parse → content_hash 算出的值。差一個位元組（換行、CRLF、markdown 轉義）就會讓 U-8 在沒有任何人為變更的情況下每天為每個 intent 開一則反向 PR——而這種差異只有真的存進 GitHub 再讀回來才會顯現。
    @given (L2) 剛寫完的 #538
    @step 以 board.sh read_item 取 managed_block_hash | 等於狀態檔記的值
    @step 以本 runner 自己抓的 raw body 走 block.sh parse → hash | 同樣等於狀態檔記的值
    @pass 三條路徑算出同一個雜湊
    @story S-6
    """
    stored = (STATE.get("l2_state") or {}).get("managed_block_hash")
    check_true("(L3) 前提：(L2) 已寫入雜湊", bool(stored), str(STATE.get("l2_state")))
    if not stored:
        return
    read_back = board_sh("read_item", AIDLC_BINDING=str(BINDING))
    check("(L3) read_item 的 managed_block_hash 等於狀態檔記的值",
          read_back.get("managed_block_hash"), stored)

    body = STATE["l2_snap"]["body"]
    parsed = block_sh("parse", AIDLC_ISSUE_BODY=body)
    check("(L3) 自抓的 body 解析得到受管區塊", parsed.get("found"), "true")
    hashed = block_sh(
        "hash",
        AIDLC_BLOCK_FORMAT_VERSION=parsed.get("block_format_version", ""),
        AIDLC_BLOCK_STATUS=parsed.get("block_status", ""),
        AIDLC_BLOCK_TRACEABLE_ROW=parsed.get("block_traceable_row", ""),
        AIDLC_BLOCK_REASON_CATEGORY=parsed.get("block_reason_category", ""),
        AIDLC_BLOCK_DECIDED_AT=parsed.get("block_decided_at", ""),
        AIDLC_BLOCK_SCOPE_NOTE=parsed.get("block_scope_note", ""),
        AIDLC_BLOCK_REJECTION_CLOSED_AT=parsed.get("block_rejection_closed_at", ""),
    )
    check("(L3) 獨立重算的 content_hash 等於狀態檔記的值",
          hashed.get("content_hash"), stored)


def test_l2b_second_round_is_a_no_op() -> None:
    """@purpose 防線①（R-4.1／R-5.5）在真實 API 上成立：緊接著再跑一輪，三欄與雜湊都已與看板一致 ⇒ 判無漂移 ⇒ **零看板寫入、零回寫、零 commit**。這是整個自我排除機制的保底，不依賴任何判斷。
    @given (L2) 剛寫完、沙箱狀態檔已回寫
    @step 對同一個沙箱再跑一輪 | exit 0
    @step 檢視 log | 出現「無漂移」且沒有新的 commit
    @pass 回寫不會引發下一輪寫入
    @story S-1
    """
    td = STATE.get("td_l2")
    if td is None:
        check_true("(L2b) 前提：(L2) 的沙箱存在", False, "")
        return
    ws = td / "ws"
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ws),
                            capture_output=True, text=True).stdout.strip()
    before = subprocess.run(["git", "rev-parse", f"origin/{branch}"], cwd=str(ws),
                            capture_output=True, text=True).stdout.strip()
    proc = run_orchestrator(ws, branch)
    check("(L2b) 第二輪 exit 0", proc.returncode, 0)
    check_true("(L2b) 判為無漂移", "無漂移" in proc.stdout, proc.stdout[-800:])
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=str(ws), capture_output=True, text=True)
    after = subprocess.run(["git", "rev-parse", f"origin/{branch}"], cwd=str(ws),
                           capture_output=True, text=True).stdout.strip()
    check("(L2b) 沒有新的回寫 commit", after, before)


def test_l4_first_creation_path() -> None:
    """@purpose (L4) R-3.1 ＋ [US:S-1 AC 1]：無綁定的新 intent 在**同一輪**內被建成 issue、加進看板、寫入 Status，並把綁定編號寫回 record。
    @given 沙箱多一個沒有 sync-state.json 的 record
    @step 跑一輪 | exit 0
    @step 讀該 record 的 sync-state.json | binding 為正整數
    @step 獨立查證該 issue | 在 #23 上、Status 等於本輪判定、標題為 intent 識別字
    @pass 「首次推送後看板出現 item 且有 Status」在真實 API 上成立
    @story S-1
    """
    td = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-fwd-live-new-"))
    STATE["td_l4"] = td
    ws, branch = build_sandbox(td, {NEW_INTENT: {"binding": None}})
    proc = run_orchestrator(ws, branch)
    STATE["l4_log"] = proc.stdout + proc.stderr
    check("(L4) 編排 exit 0", proc.returncode, 0)

    path = ws / RECORD_ROOT / NEW_INTENT / "sync-state.json"
    check_true("(L4) 綁定編號已回寫", path.exists(), STATE["l4_log"][-800:])
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding="utf-8"))
    number = state.get("binding")
    check_true("(L4) binding 為正整數", isinstance(number, int) and number > 0, str(state))
    if not isinstance(number, int):
        return
    STATE["created_issue"] = number
    snap = issue_snapshot(number)
    STATE["created_issue_id"] = snap["id"]
    check("(L4) 新 issue 的標題為 intent 識別字", snap["title"], NEW_INTENT)
    check_true(f"(L4) 新 issue 在 #{PROJECT_NUMBER} 上", snap["on_board"], str(snap))
    check("(L4) 同一輪就寫了 Status", snap["status"], state["last_status"])
    check_true("(L4) 同一輪就寫了受管區塊", STATE["sigil"] in snap["body"], snap["body"][:200])


# ==========================================================================
# 清理
# ==========================================================================

def cleanup() -> None:
    problems: list[str] = []

    # 1) #538 的 body 與 Status 還原
    try:
        patch_body(BINDING, STATE.get("orig_body", ""))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"還原 #{BINDING} 的 body 失敗：{exc!r}")
    orig_status = STATE.get("orig_status") or ""
    if orig_status:
        res = board_sh("write_status", AIDLC_BINDING=str(BINDING),
                       AIDLC_EXPECTED_STATUS="", AIDLC_DESIRED_STATUS=orig_status)
        # expected 空字串只在原本未設值時相符；先試一次，不符就用現值當 expected。
        if res.get("result") != "written":
            current = issue_snapshot(BINDING)["status"]
            res = board_sh("write_status", AIDLC_BINDING=str(BINDING),
                           AIDLC_EXPECTED_STATUS=current, AIDLC_DESIRED_STATUS=orig_status)
        if res.get("result") != "written":
            problems.append(f"還原 #{BINDING} 的 Status 失敗：{res}")

    # 2) (L4) 建立的 issue 刪除。只刪「標題逐字等於本檔的測試識別字」那一則。
    number = STATE.get("created_issue")
    node_id = STATE.get("created_issue_id")
    if number and node_id:
        try:
            snap = issue_snapshot(number)
            if snap["title"] != NEW_INTENT:
                problems.append(f"拒絕刪除 issue #{number}：標題 {snap['title']!r} 不是本檔建立的")
            else:
                gql("mutation($id:ID!){ deleteIssue(input:{issueId:$id}){ clientMutationId } }",
                    id=node_id)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"刪除 issue #{number} 失敗（**殘留一則 issue，需人工清理**）：{exc!r}")

    # 3) 測試自訂欄位刪除
    try:
        fields = gql("""
          query($owner:String!,$number:Int!){
            user(login:$owner){ projectV2(number:$number){
              fields(first:60){ nodes { ... on ProjectV2FieldCommon { id name } } } } } }
        """, owner=PROJECT_OWNER, number=int(PROJECT_NUMBER))
        for node in fields["data"]["user"]["projectV2"]["fields"]["nodes"]:
            if node.get("name") == TEST_FIELD:
                gql("mutation($id:ID!){ deleteProjectV2Field(input:{fieldId:$id}){ clientMutationId } }",
                    id=node["id"])
    except Exception as exc:  # noqa: BLE001
        problems.append(f"刪除測試欄位 {TEST_FIELD} 失敗（**殘留一個欄位**）：{exc!r}")

    for td_key in ("td_l2", "td_l4"):
        td = STATE.get(td_key)
        if td:
            shutil.rmtree(td, ignore_errors=True)

    for p in problems:
        FAILURES.append(f"cleanup：{p}")


STEPS = [
    step_preflight,
    test_l1_gh_pr_list_field_set_is_valid,
    test_l2_full_write_chain,
    test_l3_hash_equivalence_with_u8_path,
    test_l2b_second_round_is_a_no_op,
    test_l4_first_creation_path,
]


def main() -> int:
    global TOKEN
    TOKEN = os.environ.get("GH_TOKEN", "")
    if not TOKEN:
        proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if proc.returncode == 0:
            TOKEN = proc.stdout.strip()
    if not TOKEN:
        sys.stderr.write(
            "SKIP：無 GH_TOKEN 且 gh auth token 取不到憑證——live 層未執行，"
            "(L1)〜(L4) 未被本次驗證。以 exit 3 聲明不完整，不靜默。\n")
        return 3

    # SEC-3 防呆：正式看板 #16 絕對不許寫入。同一份憑證同時寫得了它，
    # **隔離只靠這個設定值、不靠權限**。
    #
    # 比對**必須先正規化成整數再比**，不能比字串。理由是實測出來的，不是講究：
    # 下面每一個真正的查詢點（:161 的 items 過濾、:539 的 projectV2(number:)）
    # 用的都是 int(PROJECT_NUMBER)，而 "016"／" 16"／"16 "／"0016"／"+16" 這些
    # 值在 int() 之下**全部等於 16**、在字串比對之下**全部不等於 "16"**——
    # 於是守衛放行、查詢卻打到正式看板。這是這道防線唯一要擋的事情，卻正好從
    # 它的縫裡漏過去。（reviewer iteration 1 Critical，實測五種變體皆可繞過。）
    #
    # 無法解析成整數的值也一律拒絕（fail closed）：它不會是一個合法的看板編號，
    # 繼續往下走只會在某個更深的地方以更難懂的方式失敗。
    try:
        project_number_int = int(str(PROJECT_NUMBER).strip())
    except (TypeError, ValueError):
        sys.stderr.write(
            f"REFUSE：AIDLC_PROJECT_NUMBER={PROJECT_NUMBER!r} 不是整數，"
            "無法判定它是不是正式看板（SEC-3）。exit 4。\n")
        return 4
    if project_number_int == LIVE_FORBIDDEN_PROJECT:
        sys.stderr.write(
            f"REFUSE：AIDLC_PROJECT_NUMBER={PROJECT_NUMBER!r} 解析為 "
            f"#{project_number_int}，是正式看板（SEC-3）。"
            "live 測試只准寫測試看板。exit 4。\n")
        return 4

    print(f"live 對象：{PROJECT_OWNER}/projects/{PROJECT_NUMBER}，issue #{BINDING}"
          f"（repo {REPOSITORY}）")
    print(f"受測物：{IMPL_YML.name} 的 id: orchestrate（{len(SCRIPT.splitlines())} 行）\n")

    aborted = False
    try:
        for step in STEPS:
            before = len(FAILURES)
            try:
                step()
            except Exception as exc:  # noqa: BLE001
                FAILURES.append(f"{step.__name__} 擲出例外：{exc!r}")
                if step is step_preflight:
                    aborted = True
                    break
            status = "ok" if len(FAILURES) == before else "FAIL"
            print(f"[{status}] {step.__name__}")
    finally:
        if not aborted:
            cleanup()

    print(f"\n{len(STEPS)} steps, {CHECKS} checks, {len(FAILURES)} failures")
    if FAILURES:
        print("\n---- failures ----")
        for f in FAILURES:
            print(f"* {f}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
