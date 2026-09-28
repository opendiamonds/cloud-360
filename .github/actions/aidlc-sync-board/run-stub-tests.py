#!/usr/bin/env python3
"""stub 斷言 runner — U-3「看板客戶端」composite action（離線層）。

用法：
    python3 .github/actions/aidlc-sync-board/run-stub-tests.py

非零 exit 表失敗。

**完全離線**：以 PATH shim 偽裝 `gh`（見 GH_SHIM），board.sh 的每一次 API 呼叫都被
route 表接住並記錄到 calls.jsonl，測試據此斷言「發了什麼」「沒發什麼」——後者
（例如 Aborted 時不得送出 mutation、R-3.1 攔截時零 API 呼叫）只有 stub 層能誠實
斷言。U-2 的 block.sh 是**真的**（不偽裝）：受管標記萃取、parse＋hash 委派這兩條
單一真實來源的鎖，偽裝了就鎖不住。

錯誤分類的 fixture **逐字**取自 ADR-0016 §4 的錯誤分類法四列（PRE-1 第五輪實測的
逐字訊息）。R-1.4（同 Project 多筆 → ExternalError）依 ADR-0016 §6 為「防禦性斷言、
無可構造的 live 反例」——stub 能誠實構造 live 構造不出的狀態，該分支只在這裡驗。

規格正本：
    ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
      U-3-board-client/functional-design/business-rules.md         （R-1〜R-6 群）
      U-3-board-client/nfr-requirements/security-requirements.md   （SEC-1〜SEC-4）
      ../decisions/0016-credential-topology-and-pre1-amendments.md （錯誤分類法）
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BOARD_SH = HERE / "board.sh"
ACTION_YML = HERE / "action.yml"
BLOCK_SH = HERE.parent / "aidlc-sync-block" / "block.sh"

BASH = os.environ.get("AIDLC_BOARD_BASH", "bash")

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
# gh 的 PATH shim
# ==========================================================================
# route 表（routes.json）逐項比對：argv 以空白串接後，`contains` 的每個子字串都
# 命中才算 match，**先者優先**（PATCH 路由要排在 GET 之前）。每次呼叫都追加一筆
# {argv, stdin} 到 calls.jsonl；`--input <file>` 的 payload 讀進 stdin 欄，
# 供 write_body 的 PATCH 內容斷言。無 route 命中 → exit 9（測試會大聲失敗，
# 不會靜默打到真實網路——PATH 上的 gh 就是這支 shim）。

GH_SHIM = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
stub_dir = pathlib.Path(os.environ["AIDLC_STUB_DIR"])
argv = sys.argv[1:]
stdin_data = ""
if "--input" in argv:
    src = argv[argv.index("--input") + 1]
    stdin_data = sys.stdin.read() if src == "-" else pathlib.Path(src).read_text()
with open(stub_dir / "calls.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps({"argv": argv, "stdin": stdin_data}) + "\n")
hay = " ".join(argv)
for route in json.loads((stub_dir / "routes.json").read_text()):
    if all(sub in hay for sub in route["contains"]):
        sys.stdout.write(route.get("stdout", ""))
        sys.stderr.write(route.get("stderr", ""))
        sys.exit(route.get("exit", 0))
sys.stderr.write("stub-gh: no route for: " + hay[:2000] + "\n")
sys.exit(9)
'''


class BoardResult:
    def __init__(self, proc: subprocess.CompletedProcess, stub_dir: pathlib.Path,
                 gh_output_file: pathlib.Path):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.gh_output = gh_output_file.read_text() if gh_output_file.exists() else ""
        calls_file = stub_dir / "calls.jsonl"
        self.calls = []
        if calls_file.exists():
            for line in calls_file.read_text().splitlines():
                if line.strip():
                    self.calls.append(json.loads(line))
        self.outputs: dict[str, str] = {}
        for line in self.stdout.splitlines():
            if "=" in line:
                name, _, value = line.partition("=")
                self.outputs[name] = value

    def calls_matching(self, *subs: str):
        out = []
        for call in self.calls:
            hay = " ".join(call["argv"])
            if all(s in hay for s in subs):
                out.append(call)
        return out


BASE_ENV = {
    "AIDLC_PROJECT_OWNER": "opendiamonds",
    "AIDLC_PROJECT_NUMBER": "23",
    "AIDLC_FIELD_NAME": "AIDLC Stage",
    "GITHUB_REPOSITORY": "opendiamonds/cloud-360",
}


def run_board(operation: str, routes=None, env=None, argv=None) -> BoardResult:
    """在 PATH shim 之下執行 board.sh 一次。routes=None 代表「預期零 API 呼叫」
    （仍鋪 shim——若意外呼叫會走 exit 9 而非打到真實網路）。"""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-board-stub-"))
    try:
        stub_dir = tmp / "stub"
        stub_dir.mkdir()
        (stub_dir / "routes.json").write_text(json.dumps(routes or []))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        shim = bin_dir / "gh"
        shim.write_text(GH_SHIM)
        shim.chmod(0o755)
        gh_output_file = tmp / "github_output"

        full_env = dict(os.environ)
        # 隔離：清掉外部可能殘留的介面 env，逐測試明確給值。
        for key in list(full_env):
            if key.startswith("AIDLC_"):
                del full_env[key]
        full_env.update(BASE_ENV)
        full_env.update(env or {})
        full_env["AIDLC_OPERATION"] = operation
        full_env["PATH"] = f"{bin_dir}:{full_env['PATH']}"
        full_env["AIDLC_STUB_DIR"] = str(stub_dir)
        full_env["GITHUB_OUTPUT"] = str(gh_output_file)

        proc = subprocess.run(
            [BASH, str(BOARD_SH)] + (argv or []),
            capture_output=True, text=True, env=full_env,
        )
        return BoardResult(proc, stub_dir, gh_output_file)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ==========================================================================
# GraphQL 回應建構器
# ==========================================================================

def item_node(project_number=23, owner="opendiamonds", item_id="PVTI_STUB_1",
              project_id="PVT_STUB", status=None, text=None):
    return {
        "id": item_id,
        "project": {"id": project_id, "number": project_number, "owner": {"login": owner}},
        "statusValue": None if status is None else {"name": status},
        "customValue": None if text is None else {"text": text},
    }


def read_item_response(nodes, state="OPEN", body=""):
    return json.dumps({"data": {"repository": {"issue": {
        "state": state, "body": body,
        "projectItems": {"totalCount": len(nodes), "nodes": nodes},
    }}}})


def fields_response(fields):
    return json.dumps({"data": {"user": {"projectV2": {"fields": {
        "pageInfo": {"hasNextPage": False, "endCursor": None},
        "nodes": fields,
    }}}}})


STATUS_OPTIONS = [
    {"id": "aa000001", "name": "Backlog"},
    {"id": "aa000002", "name": "Nice to have"},
    {"id": "aa000003", "name": "Ready"},
    {"id": "aa000004", "name": "In progress"},
    {"id": "aa000005", "name": "In review"},
    {"id": "aa000006", "name": "Done"},
]

STATUS_FIELD = {"id": "F_status", "name": "Status", "dataType": "SINGLE_SELECT",
                "options": STATUS_OPTIONS}
TEXT_FIELD = {"id": "F_text", "name": "AIDLC Stage", "dataType": "TEXT"}


def errors_response(*rows, data=None):
    return json.dumps({"data": data, "errors": [
        {"type": t, "message": m} for (t, m) in rows
    ]})


ROUTE_READ = ["api", "graphql", "projectItems"]
ROUTE_FIELDS = ["fields(first:50"]
ROUTE_PROJECT = ["viewerCanUpdate"]
ROUTE_SELECT_MUTATION = ["updateProjectV2ItemFieldValue", "singleSelectOptionId"]
ROUTE_TEXT_MUTATION = ["updateProjectV2ItemFieldValue", "value:{text:"]
ROUTE_CREATE_FIELD = ["createProjectV2Field"]
ROUTE_ADD_ITEM = ["addProjectV2ItemById"]


def call_indices(res: BoardResult, subs) -> list[int]:
    """回傳 calls 中命中 subs（全部子字串）的索引，供**呼叫順序**斷言——calls_matching
    只能數「有幾次」，數不出「誰先誰後」。"""
    return [i for i, call in enumerate(res.calls)
            if all(s in " ".join(call["argv"]) for s in subs)]


def render_block(status="Ready", traceable_row="| S-3 | stub |", scope_note="none",
                 reason_code="", decided_at="") -> str:
    """以**真的** block.sh 產一段受管區塊（受管區塊格式的單一真實來源在 U-2，
    本 runner 不得手寫區塊文字）。"""
    env = dict(os.environ)
    env.update({
        "AIDLC_STATUS": status, "AIDLC_TRACEABLE_ROW": traceable_row,
        "AIDLC_REASON_CODE": reason_code, "AIDLC_SCOPE_NOTE": scope_note,
        "AIDLC_DECIDED_AT": decided_at, "AIDLC_REJECTION_CLOSED_AT": "",
        "GITHUB_OUTPUT": "",
    })
    proc = subprocess.run([BASH, str(BLOCK_SH), "render"],
                          capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"block.sh render 失敗：{proc.stderr}")
    return proc.stdout


def u2_hash_of_body(body: str) -> str:
    """以真的 block.sh 走 parse → hash（U-8 的同一條路），供委派斷言比對。"""
    env = dict(os.environ)
    env["AIDLC_ISSUE_BODY"] = body
    env["GITHUB_OUTPUT"] = ""
    parse = subprocess.run([BASH, str(BLOCK_SH), "parse"],
                           capture_output=True, text=True, env=env)
    fields = dict(line.partition("=")[::2] for line in parse.stdout.splitlines())
    if fields.get("found") != "true":
        return ""
    env2 = dict(os.environ)
    env2["GITHUB_OUTPUT"] = ""
    for key in ("format_version", "status", "traceable_row", "reason_category",
                "decided_at", "scope_note", "rejection_closed_at"):
        env2[f"AIDLC_BLOCK_{key.upper()}"] = fields.get(f"block_{key}", "")
    hashed = subprocess.run([BASH, str(BLOCK_SH), "hash"],
                            capture_output=True, text=True, env=env2)
    return dict(line.partition("=")[::2] for line in hashed.stdout.splitlines()).get("content_hash", "")


# ==========================================================================
# SEC-1 ／ R-5 ／ 標記萃取（介面層的機械斷言）
# ==========================================================================

def test_sec1_action_yml_no_credential_input() -> None:
    """@purpose action.yml 不得宣告任何憑證型 input——input 是公開介面，憑證只能走 env GH_TOKEN（SEC-1）。
    @given 本 action 的 action.yml 原始文字
    @step 掃描 inputs: 區塊的全部 input 名稱 | 無任何名稱含 token / secret / password / credential / key
    @step 掃描 runs 步驟的 env 映射 | GH_TOKEN 不從 inputs 取值
    @pass 兩項掃描皆零命中
    @story S-10
    """
    text = ACTION_YML.read_text()
    lines = text.splitlines()
    input_names: list[str] = []
    in_inputs = False
    for line in lines:
        if line.startswith("inputs:"):
            in_inputs = True
            continue
        if in_inputs and line and not line.startswith(" ") and not line.startswith("#"):
            in_inputs = False
        if in_inputs and line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            input_names.append(line.strip().rstrip(":"))
    check_true("SEC-1：有掃到 input 清單（掃描器沒壞）", len(input_names) >= 5,
               f"掃到：{input_names}")
    banned = ("token", "secret", "password", "credential", "passwd", "apikey", "api_key", "api-key")
    offenders = [n for n in input_names if any(b in n.lower() for b in banned)]
    check("SEC-1：無憑證型 input 名稱", offenders, [])
    check_true("SEC-1：GH_TOKEN 不從 inputs 映射", "GH_TOKEN: ${{ inputs" not in text,
               "action.yml 把 GH_TOKEN 接到了 input 上")


def test_r5_unknown_operation_rejected() -> None:
    """@purpose R-5 權限邊界的介面面：不存在「推 commit／改檔案」的 operation，未知值一律非零 exit、不靜默。
    @given 無任何 API route（意外呼叫會 exit 9）
    @step 以 operation=commit_and_push 執行 | 非零 exit，stderr 指明未知的 operation
    @step 以 operation=push 執行 | 同上
    @step 以 operation 空值執行 | 非零 exit，stderr 指明未指定
    @pass 三者皆被拒且零 API 呼叫
    @story S-10
    """
    for op in ("commit_and_push", "push"):
        res = run_board(op)
        check_true(f"R-5：operation={op} 被拒", res.rc != 0, f"rc={res.rc}")
        check_true(f"R-5：operation={op} 的 stderr 指明未知", "未知的 operation" in res.stderr,
                   res.stderr)
        check(f"R-5：operation={op} 零 API 呼叫", len(res.calls), 0)
    res = run_board("")
    check_true("R-5：operation 空值被拒", res.rc != 0 and "operation 未指定" in res.stderr,
               f"rc={res.rc} stderr={res.stderr}")


def test_r5_seven_operations_dispatch() -> None:
    """@purpose 七個契約 operation 都真的接在分派表上（缺一個就是介面缺口，不是「未知」）。
    @given 各 operation 以缺必要輸入的方式執行（不需要任何 API route）
    @step 逐一執行七個 operation | 每個都以 exit 2 失敗於**輸入驗證**，stderr 不含「未知的 operation」
    @pass 七個 operation 無一落入未知分支
    @story S-3
    """
    for op in ("read_item", "create_item", "write_status", "write_field",
               "ensure_field", "read_issue_state", "write_body"):
        env = {"AIDLC_PROJECT_OWNER": ""} if op == "ensure_field" else {"AIDLC_BINDING": ""}
        if op == "create_item":
            env = {"AIDLC_INTENT_ID": "", "AIDLC_EXISTING_BINDING": ""}
        res = run_board(op, env=env)
        check_true(f"dispatch：{op} 有接上（非未知）", "未知的 operation" not in res.stderr,
                   res.stderr)
        check_true(f"dispatch：{op} 在輸入驗證層失敗", res.rc == 2, f"rc={res.rc} stderr={res.stderr}")


def test_marker_extraction_matches_render() -> None:
    """@purpose 受管標記的執行期萃取值必須與 U-2 render 實際輸出的首尾行一致——萃取是 R-6.2 單一真實來源的實現方式，萃取錯了 write_body 會拿著錯的標記去改 body。
    @given 真的 block.sh（不偽裝）
    @step board.sh markers 取萃取值 | 得到 MARKER_SIGIL 與 MARKER_END
    @step block.sh render 產一段區塊 | 首行以 MARKER_SIGIL 開頭、末行等於 MARKER_END
    @pass 兩兩一致
    @story S-6
    """
    res = run_board("read_item", argv=["markers"])  # argv 覆寫 env 的 operation
    check("markers：exit 0", res.rc, 0)
    sigil = res.outputs.get("MARKER_SIGIL", "")
    end = res.outputs.get("MARKER_END", "")
    check_true("markers：萃取到非空 MARKER_SIGIL", bool(sigil), res.stdout)
    check_true("markers：萃取到非空 MARKER_END", bool(end), res.stdout)
    block = render_block()
    block_lines = block.rstrip("\n").splitlines()
    check_true("markers：render 首行以萃取的 MARKER_SIGIL 開頭",
               block_lines[0].startswith(sigil),
               f"sigil={sigil!r} first={block_lines[0]!r}")
    check("markers：render 末行等於萃取的 MARKER_END", block_lines[-1], end)


# ==========================================================================
# 錯誤分類（ADR-0016 §4 四列逐字）與兩層檢查
# ==========================================================================

ERR_ROW_1 = ("NOT_FOUND", "Could not resolve to a node with the global id of 'PVTI_FAKE'")
ERR_ROW_2 = ("VALIDATION", "The item does not exist in the project")
ERR_ROW_3 = ("VALIDATION", "Did not receive a single select option Id to update a field of type single_select")
ERR_ROW_4 = ("VALIDATION", "The single select option Id does not belong to the field")


def test_errclass_row1_notfound_is_external_error() -> None:
    """@purpose ADR-0016 §4.3：NOT_FOUND 同時涵蓋「不存在」與「無權限」，**不得**對應成「卡不在板上」——誤對應的後果是權限退化時靜默走上補建分支且不紅燈。
    @given read_item 的查詢 route 回 GraphQL NOT_FOUND（訊息逐字取自錯誤分類法第 1 列），exit 1
    @step 執行 read_item | 非零 exit（ExternalError 例外式），result=external_error
    @step 檢視 message | 含逐字的 NOT_FOUND 訊息
    @step 檢視輸出 | **沒有** R-1.3 零筆分支的全 null ItemState（issue_number 未被寫出）
    @pass ExternalError 且未走零筆分支
    @api Issue.projectItems
    @story S-3
    """
    res = run_board("read_item", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ROUTE_READ, "exit": 1,
         "stdout": errors_response(ERR_ROW_1),
         "stderr": "gh: GraphQL: Could not resolve to a node\n"},
    ])
    check_true("錯誤分類第 1 列：非零 exit", res.rc != 0, f"rc={res.rc}")
    check("錯誤分類第 1 列：result=external_error", res.outputs.get("result"), "external_error")
    check_true("錯誤分類第 1 列：message 逐字含 NOT_FOUND 訊息",
               ERR_ROW_1[1] in res.outputs.get("message", ""), res.outputs.get("message", ""))
    check_true("錯誤分類第 1 列：未走零筆分支（issue_number 未寫出）",
               "issue_number" not in res.outputs, res.stdout)


def test_errclass_rows_2_3_4_validation_on_mutation() -> None:
    """@purpose 錯誤分類法第 2〜4 列（VALIDATION 家族）落在 Status 寫入路徑時必須紅燈——主寫入失敗不是 Failed 的不連坐通道，是 ExternalError。
    @given write_status 的回讀與欄位解析 route 正常，mutation route 逐字回三列 VALIDATION 之一
    @step 對三列各執行一次 write_status（回讀相符，走到 mutation） | 非零 exit，result=external_error
    @step 檢視 message | 含該列逐字訊息，http_status=200（GraphQL 層錯誤）
    @pass 三列皆 ExternalError
    @api updateProjectV2ItemFieldValue
    @story S-3
    """
    for row in (ERR_ROW_2, ERR_ROW_3, ERR_ROW_4):
        res = run_board("write_status", env={
            "AIDLC_BINDING": "538", "AIDLC_EXPECTED_STATUS": "Ready",
            "AIDLC_DESIRED_STATUS": "Done",
        }, routes=[
            {"contains": ROUTE_READ,
             "stdout": read_item_response([item_node(status="Ready")])},
            {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
            {"contains": ROUTE_SELECT_MUTATION, "exit": 1,
             "stdout": errors_response(row), "stderr": "gh: GraphQL error\n"},
        ])
        check_true(f"錯誤分類（{row[1][:24]}…）：非零 exit", res.rc != 0, f"rc={res.rc}")
        check(f"錯誤分類（{row[1][:24]}…）：result", res.outputs.get("result"), "external_error")
        check_true(f"錯誤分類（{row[1][:24]}…）：message 逐字",
                   row[1] in res.outputs.get("message", ""), res.outputs.get("message", ""))
        check(f"錯誤分類（{row[1][:24]}…）：http_status=200（GraphQL 層）",
              res.outputs.get("http_status"), "200")


def test_two_layer_check_catches_errors_with_exit_zero() -> None:
    """@purpose 兩層錯誤檢查（tech-stack-decisions.md 定案）：GraphQL 在錯誤時仍可回 HTTP 200／exit 0 並把錯誤放在 body 的 .errors——只看 exit code 會把失敗當成功。
    @given read_item 的 route 回 exit **0**，但 body 帶非空 .errors
    @step 執行 read_item | 仍判為失敗：非零 exit，result=external_error
    @pass exit code 層放行、.errors 層攔下
    @api Issue.projectItems
    @story S-3
    """
    res = run_board("read_item", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ROUTE_READ, "exit": 0,
         "stdout": errors_response(("SOME_TYPE", "partial failure while resolving"))},
    ])
    check_true("兩層檢查：exit 0 帶 .errors 仍判失敗", res.rc != 0, f"rc={res.rc} stdout={res.stdout}")
    check("兩層檢查：result=external_error", res.outputs.get("result"), "external_error")
    check_true("兩層檢查：message 取自 errors[].message",
               "partial failure while resolving" in res.outputs.get("message", ""),
               res.outputs.get("message", ""))


def test_sec4_message_scrubbed() -> None:
    """@purpose SEC-4：交給 C-5 的 message 只得含 GraphQL errors[].message 與 HTTP 狀態碼——完整 body 與標頭可能挾帶憑證片段，而通報會開公開 issue。
    @given read_item 的 route 失敗，回應 body 與 stderr 都夾帶假憑證字串（Authorization 標頭 ＋ token 樣式）
    @step 執行 read_item | 非零 exit
    @step 檢視 board.sh 的 stdout、stderr 與 GITHUB_OUTPUT 全文 | 皆不含假憑證字串、不含 Authorization
    @step 檢視 message | 含 errors[].message；http_status 取自 stderr 的 HTTP 502
    @pass 機敏內容零外洩且有效訊息保留
    @story S-10
    """
    secret = "ghp_FAKE_SECRET_MARKER_12345"
    body = json.dumps({
        "errors": [{"type": "NOT_FOUND", "message": ERR_ROW_1[1]}],
        "request_echo": f"Authorization: token {secret}",
    })
    res = run_board("read_item", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ROUTE_READ, "exit": 1, "stdout": body,
         "stderr": f"gh: server error (HTTP 502)\nAuthorization: token {secret}\n"},
    ])
    check_true("SEC-4：非零 exit", res.rc != 0, f"rc={res.rc}")
    surface = res.stdout + res.stderr + res.gh_output
    check_true("SEC-4：假憑證未外洩", secret not in surface, "憑證字串出現在輸出面")
    check_true("SEC-4：標頭未外洩", "Authorization" not in surface, "Authorization 出現在輸出面")
    check_true("SEC-4：errors[].message 保留",
               ERR_ROW_1[1] in res.outputs.get("message", ""), res.outputs.get("message", ""))
    check("SEC-4：http_status 取自 stderr", res.outputs.get("http_status"), "502")


# ==========================================================================
# R-1 群：查找、過濾、零筆、多筆
# ==========================================================================

def test_r12_filter_picks_configured_project() -> None:
    """@purpose R-1.2：反查會拿到 issue 所屬的**全部** Project，必須過濾出 Config 指定的那個——這是 [Q1=A] 引入的必要責任，不是防禦性程式碼。
    @given 反查回兩筆 item：一筆屬 Config 的 Project #23（Ready），一筆屬別的 Project #99（Done）
    @step 執行 read_item | exit 0
    @step 檢視 status | Ready（#23 那筆），不是 Done（#99 那筆）
    @pass 過濾命中 Config 指定的 Project
    @api Issue.projectItems
    @story S-3
    """
    res = run_board("read_item", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ROUTE_READ, "stdout": read_item_response([
            item_node(project_number=99, item_id="PVTI_other", status="Done"),
            item_node(project_number=23, item_id="PVTI_ours", status="Ready",
                      text="construction"),
        ])},
    ])
    check("R-1.2：exit 0", res.rc, 0)
    check("R-1.2：status 取自 Config 的 Project", res.outputs.get("status"), "Ready")
    check("R-1.2：field_value 取自 Config 的 Project", res.outputs.get("field_value"),
          "construction")


def test_r13_zero_items_all_null() -> None:
    """@purpose R-1.3：查詢成功且過濾後為零筆＝issue 尚未在看板上，回全 null 的 ItemState——這是正常判定結果，不是錯誤。
    @given 反查成功、nodes 為空
    @step 執行 read_item | exit 0
    @step 檢視五欄 | status／field_value／managed_block_hash 皆空（null）；issue_number=538；issue_state=open
    @pass 零筆分支只由「查詢成功且零筆」進入且不紅燈
    @api Issue.projectItems
    @story S-3
    """
    res = run_board("read_item", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ROUTE_READ, "stdout": read_item_response([], state="OPEN")},
    ])
    check("R-1.3：exit 0", res.rc, 0)
    check("R-1.3：status 為 null", res.outputs.get("status"), "")
    check("R-1.3：field_value 為 null", res.outputs.get("field_value"), "")
    check("R-1.3：managed_block_hash 為 null", res.outputs.get("managed_block_hash"), "")
    check("R-1.3：issue_number", res.outputs.get("issue_number"), "538")
    check("R-1.3：issue_state", res.outputs.get("issue_state"), "open")


def test_r14_multiple_items_external_error() -> None:
    """@purpose R-1.4：同一 Project 內多於一筆 item＝看板狀態已壞，ExternalError、不猜哪一筆——防禦性斷言，無可構造的 live 反例（ADR-0016 §6：addProjectV2ItemById 冪等），本分支只有 stub 能誠實驗證。
    @given 反查回兩筆 item **都**屬 Config 的 Project #23
    @step 執行 read_item | 非零 exit，result=external_error
    @step 檢視 message | 指明 R-1.4 與筆數
    @pass 多筆走 ExternalError 而非取第一筆
    @api Issue.projectItems
    @story S-3
    """
    res = run_board("read_item", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ROUTE_READ, "stdout": read_item_response([
            item_node(item_id="PVTI_a", status="Ready"),
            item_node(item_id="PVTI_b", status="Done"),
        ])},
    ])
    check_true("R-1.4：非零 exit", res.rc != 0, f"rc={res.rc}")
    check("R-1.4：result=external_error", res.outputs.get("result"), "external_error")
    check_true("R-1.4：message 指明規則與筆數",
               "R-1.4" in res.outputs.get("message", "") and "2" in res.outputs.get("message", ""),
               res.outputs.get("message", ""))


def test_read_item_delegates_hash_to_u2() -> None:
    """@purpose managed_block_hash 必須由 U-2 的 parse＋hash 產生（domain-entities.md：自算即第二份格式物化，違反單一真實來源）。
    @given 反查回一筆 item，issue body 內含一段真的 block.sh render 出的受管區塊
    @step 執行 read_item | exit 0
    @step 以 runner 自己走 block.sh parse→hash 重算 | 兩值相等且為 64 位十六進位
    @step 檢視 GITHUB_OUTPUT | 不含 block.sh 內部呼叫外洩的 found=／block_* 行
    @pass 委派一致且 output 無污染
    @api Issue.projectItems
    @story S-6
    """
    block = render_block(status="In progress", traceable_row="| S-3 | delegate |")
    body = "人寫的敘述\n\n" + block
    res = run_board("read_item", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ROUTE_READ,
         "stdout": read_item_response([item_node(status="In progress")], body=body)},
    ])
    check("hash 委派：exit 0", res.rc, 0)
    expected = u2_hash_of_body(body)
    check_true("hash 委派：期望值非空（runner 的重算路徑沒壞）", len(expected) == 64, expected)
    check("hash 委派：與 U-2 重算值一致", res.outputs.get("managed_block_hash"), expected)
    check_true("hash 委派：GITHUB_OUTPUT 無 block.sh 內部輸出污染",
               "found" not in res.gh_output and "block_status" not in res.gh_output,
               res.gh_output)


def test_read_issue_state() -> None:
    """@purpose read_issue_state 是 [US:S-9 AC 5] 的 issue 開關偵測——輕量投影，回小寫 open/closed。
    @given issue 查詢 route 回 state=CLOSED
    @step 執行 read_issue_state | exit 0，issue_state=closed
    @pass 大寫 enum 正規化為契約的小寫值
    @api Issue.state
    @story S-9
    """
    res = run_board("read_issue_state", env={"AIDLC_BINDING": "538"}, routes=[
        {"contains": ["issue(number:$number){ state }"],
         "stdout": json.dumps({"data": {"repository": {"issue": {"state": "CLOSED"}}}})},
    ])
    check("read_issue_state：exit 0", res.rc, 0)
    check("read_issue_state：closed", res.outputs.get("issue_state"), "closed")


# ==========================================================================
# R-2 群：write_status 的回讀比對
# ==========================================================================

def test_write_status_aborted_no_mutation() -> None:
    """@purpose R-2.1〜R-2.3：回讀不符 → Aborted{actual, expected}，**不送出寫入**、不開 issue、exit 0 不紅燈——[req:FR-C1] 的主動中止是機制的正常判斷；message 說明「回讀不符」供 C-5 直接引用。
    @given 欄位 route 給 Status 選項表；回讀 route 回 status=In review；expected=Ready
    @step 執行 write_status desired=Done | exit 0，result=aborted，actual_status=In review，expected_status=Ready，message 含「回讀不符」
    @step 檢視 calls.jsonl | **零** mutation 呼叫、零開 issue 呼叫；恰兩次呼叫（欄位列舉＋回讀），且回讀是最後一次——回讀之後沒有任何呼叫
    @pass Aborted 是回傳值且未產生任何寫入
    @api ProjectV2.fields
    @api Issue.projectItems
    @story S-3
    """
    res = run_board("write_status", env={
        "AIDLC_BINDING": "538", "AIDLC_EXPECTED_STATUS": "Ready",
        "AIDLC_DESIRED_STATUS": "Done",
    }, routes=[
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
        {"contains": ROUTE_READ,
         "stdout": read_item_response([item_node(status="In review")])},
    ])
    check("Aborted：exit 0", res.rc, 0)
    check("Aborted：result", res.outputs.get("result"), "aborted")
    check("Aborted：actual_status", res.outputs.get("actual_status"), "In review")
    check("Aborted：expected_status", res.outputs.get("expected_status"), "Ready")
    check_true("Aborted：message 含「回讀不符」",
               "回讀不符" in res.outputs.get("message", ""), res.outputs.get("message", ""))
    check("Aborted：零 mutation", len(res.calls_matching("updateProjectV2ItemFieldValue")), 0)
    check("Aborted：零開 issue", len(res.calls_matching("-X", "POST")), 0)
    check("Aborted：恰兩次呼叫（欄位列舉＋回讀）", len(res.calls), 2)
    check_true("Aborted：回讀是最後一次呼叫（回讀之後零呼叫）",
               bool(res.calls) and all(s in " ".join(res.calls[-1]["argv"]) for s in ROUTE_READ),
               str([c["argv"][:3] for c in res.calls]))


def test_write_status_written_uses_resolved_option_id() -> None:
    """@purpose R-4.4／R-4.5：Status 寫入必須用**執行期解析**的 option id（大小寫敏感精確比對），不得寫死——實測 #16 與 #23 的同名選項 id 不同。
    @given 回讀相符（Ready）；欄位 route 給 Status 選項表（Done → aa000006）；mutation route 成功
    @step 執行 write_status desired=Done | exit 0，result=written
    @step 檢視 mutation 呼叫的 argv | optionId 恰為欄位表回的 aa000006
    @step 檢視 calls.jsonl 的順序 | 欄位列舉全部在回讀之前；回讀之後緊接著就是 mutation，兩者之間沒有任何其他呼叫（R-2.4 視窗內只有一次 mutation 往返）
    @pass 解析值貫穿到 mutation，且欄位解析落在 R-2.4 視窗之外
    @api ProjectV2.fields
    @api Issue.projectItems
    @api updateProjectV2ItemFieldValue
    @story S-3
    """
    res = run_board("write_status", env={
        "AIDLC_BINDING": "538", "AIDLC_EXPECTED_STATUS": "Ready",
        "AIDLC_DESIRED_STATUS": "Done",
    }, routes=[
        {"contains": ROUTE_READ,
         "stdout": read_item_response([item_node(status="Ready")])},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
        {"contains": ROUTE_SELECT_MUTATION,
         "stdout": json.dumps({"data": {"updateProjectV2ItemFieldValue":
                                        {"projectV2Item": {"id": "PVTI_STUB_1"}}}})},
    ])
    check("written：exit 0", res.rc, 0)
    check("written：result", res.outputs.get("result"), "written")
    muts = res.calls_matching("updateProjectV2ItemFieldValue")
    check("written：恰一次 mutation", len(muts), 1)
    check_true("written：optionId 為執行期解析值 aa000006",
               any("optionId=aa000006" in a for a in muts[0]["argv"]),
               str(muts[0]["argv"]))
    # R-2.4 視窗寬度的機制鎖（reviewer iteration 1 Major）：欄位解析必須在回讀之前，
    # 回讀與 mutation 之間不得有任何其他呼叫。
    fields_idx = call_indices(res, ROUTE_FIELDS)
    read_idx = call_indices(res, ROUTE_READ)
    mut_idx = call_indices(res, ROUTE_SELECT_MUTATION)
    order = str([c["argv"][:3] for c in res.calls])
    check("written：恰一次回讀", len(read_idx), 1)
    check_true("written：欄位列舉全部在回讀之前（R-2.4 視窗外）",
               bool(fields_idx) and bool(read_idx) and max(fields_idx) < read_idx[0], order)
    check_true("written：回讀之後緊接著就是 mutation（視窗內只有一次往返）",
               bool(read_idx) and mut_idx == [read_idx[0] + 1], order)
    check_true("written：mutation 是最後一次呼叫",
               bool(mut_idx) and mut_idx[-1] == len(res.calls) - 1, order)


def test_write_status_expected_empty_means_unset() -> None:
    """@purpose Plan Approval 定案：AIDLC_EXPECTED_STATUS 空值＝期望「未設值」——item 在板上但 Status 未設時，空 expected 應判定相符並寫入，不是 Abort。
    @given 回讀回一筆 item 且 statusValue 為 null；expected 為空字串
    @step 執行 write_status desired=Ready | exit 0，result=written
    @step 檢視 mutation 呼叫 | 恰一次
    @pass 空值語意是「未設值」而非萬用不符
    @api updateProjectV2ItemFieldValue
    @story S-3
    """
    res = run_board("write_status", env={
        "AIDLC_BINDING": "538", "AIDLC_EXPECTED_STATUS": "",
        "AIDLC_DESIRED_STATUS": "Ready",
    }, routes=[
        {"contains": ROUTE_READ,
         "stdout": read_item_response([item_node(status=None)])},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
        {"contains": ROUTE_SELECT_MUTATION,
         "stdout": json.dumps({"data": {"updateProjectV2ItemFieldValue":
                                        {"projectV2Item": {"id": "PVTI_STUB_1"}}}})},
    ])
    check("expected 空值：exit 0", res.rc, 0)
    check("expected 空值：result=written", res.outputs.get("result"), "written")
    check("expected 空值：恰一次 mutation",
          len(res.calls_matching("updateProjectV2ItemFieldValue")), 1)


def test_write_status_item_absent_aborted() -> None:
    """@purpose item 不在 Config 指定的 Project 上（R-1.3 零筆：綁定過期或 item 已被人移出看板）→ Aborted，**不是 Failed**——上游契約把 Failed 限定為 write_field／write_body，U-6 的 R-5.12 只認得 write_status 的 Aborted；且此檢查先於 status 比對，不論 expected 為何都走同一條、訊息才準確。
    @given 欄位 route 給 Status 選項表；回讀 route 回零筆 projectItems（查詢成功、過濾後為零）
    @step (a) expected 空、desired=Ready | exit 0，result=aborted，actual_status 空，expected_status 空，message 含「不在 Project #23」與「無寫入對象」
    @step (b) expected=Ready、desired=Done | 同上，expected_status=Ready 原樣回照——不在板上的檢查先於 status 比對，不會被判成「回讀不符」
    @step 檢視 calls.jsonl（兩次） | 零 mutation、零開 issue；result 不是 failed
    @pass 兩種 expected 都以 Aborted 收場且未產生任何寫入
    @api ProjectV2.fields
    @api Issue.projectItems
    @story S-3
    """
    for label, expected, desired in (("(a)", "", "Ready"), ("(b)", "Ready", "Done")):
        res = run_board("write_status", env={
            "AIDLC_BINDING": "538", "AIDLC_EXPECTED_STATUS": expected,
            "AIDLC_DESIRED_STATUS": desired,
        }, routes=[
            {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
            {"contains": ROUTE_READ, "stdout": read_item_response([])},
        ])
        msg = res.outputs.get("message", "")
        check(f"不在板上{label}：exit 0", res.rc, 0)
        check(f"不在板上{label}：result=aborted", res.outputs.get("result"), "aborted")
        check_true(f"不在板上{label}：result 不是 failed（Failed 為 write_field／write_body 專屬）",
                   res.outputs.get("result") != "failed", res.stdout)
        check(f"不在板上{label}：actual_status 空", res.outputs.get("actual_status"), "")
        check(f"不在板上{label}：expected_status 原樣回照", res.outputs.get("expected_status"), expected)
        check_true(f"不在板上{label}：message 含「不在 Project #23」", "不在 Project #23" in msg, msg)
        check_true(f"不在板上{label}：message 含「無寫入對象」", "無寫入對象" in msg, msg)
        check(f"不在板上{label}：零 mutation",
              len(res.calls_matching("updateProjectV2ItemFieldValue")), 0)
        check(f"不在板上{label}：零開 issue", len(res.calls_matching("-X", "POST")), 0)


# ==========================================================================
# R-3 群：create_item
# ==========================================================================

def test_create_item_existing_binding_no_api_calls() -> None:
    """@purpose R-3.1（[US:S-1 AC 6]）：record 已有綁定編號 → 不建、原值回傳——這是「每 push 一次多一張卡」的唯一攔截，且必須**零 API 呼叫**（連查詢都不必發）。
    @given AIDLC_EXISTING_BINDING=538，無任何 API route
    @step 執行 create_item | exit 0，binding=538，created=false
    @step 檢視 calls.jsonl | 完全為空
    @pass 攔截發生在任何網路呼叫之前
    @story S-1
    """
    res = run_board("create_item", env={"AIDLC_EXISTING_BINDING": "538"})
    check("R-3.1：exit 0", res.rc, 0)
    check("R-3.1：binding 原值回傳", res.outputs.get("binding"), "538")
    check("R-3.1：created=false", res.outputs.get("created"), "false")
    check("R-3.1：零 API 呼叫", len(res.calls), 0)


def test_create_item_first_build_checks_project_writable() -> None:
    """@purpose R-3.2（[req:FR-C2]）：首建前必須解析 Config 指定的 Project 並驗證可寫，不符即中止（ExternalError 紅燈）——Config 錯誤或權限退化不能靜默。
    @given Project route 回 viewerCanUpdate=false
    @step 執行 create_item intent_id=260822 | 非零 exit，result=external_error，message 指明 R-3.2
    @step 檢視 calls.jsonl | 零開 issue、零 addProjectV2ItemById
    @pass 中止發生在任何寫入之前
    @api ProjectV2.viewerCanUpdate
    @story S-1
    """
    res = run_board("create_item", env={"AIDLC_INTENT_ID": "260822-gh-projects-sync"}, routes=[
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": False}}}})},
    ])
    check_true("R-3.2：非零 exit", res.rc != 0, f"rc={res.rc}")
    check("R-3.2：result=external_error", res.outputs.get("result"), "external_error")
    check_true("R-3.2：message 指明檢查", "R-3.2" in res.outputs.get("message", ""),
               res.outputs.get("message", ""))
    check("R-3.2：零開 issue", len(res.calls_matching("-X", "POST", "issues")), 0)
    check("R-3.2：零加入看板", len(res.calls_matching("addProjectV2ItemById")), 0)


def test_create_item_happy_path() -> None:
    """@purpose 首建路徑：R-3.2 檢查 → 開 issue → addProjectV2ItemById → 回 binding；標題預設 intent_id 原文（Plan Approval 定案）；**不回寫綁定編號**（R-3.3——本 operation 的呼叫面沒有任何 record 寫入，這由「無此類 API 呼叫」佐證）。
    @given Project 可寫；POST issues 回 #999；addProjectV2ItemById 成功
    @step 執行 create_item intent_id=260822-gh-projects-sync | exit 0，binding=999，created=true
    @step 檢視 POST 呼叫 | title 為 intent_id 原文
    @step 檢視 calls.jsonl | 恰三次呼叫（project／POST／add），無其他寫入
    @pass 首建完成且不越權
    @api addProjectV2ItemById
    @story S-1
    """
    res = run_board("create_item", env={"AIDLC_INTENT_ID": "260822-gh-projects-sync"}, routes=[
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": True}}}})},
        {"contains": ["-X", "POST", "repos/opendiamonds/cloud-360/issues"],
         "stdout": json.dumps({"number": 999, "node_id": "I_kwSTUB"})},
        {"contains": ROUTE_ADD_ITEM,
         "stdout": json.dumps({"data": {"addProjectV2ItemById": {"item": {"id": "PVTI_new"}}}})},
    ])
    check("首建：exit 0", res.rc, 0)
    check("首建：binding=999", res.outputs.get("binding"), "999")
    check("首建：created=true", res.outputs.get("created"), "true")
    posts = res.calls_matching("-X", "POST", "issues")
    check("首建：恰一次開 issue", len(posts), 1)
    check_true("首建：標題預設 intent_id 原文",
               any(a == "title=260822-gh-projects-sync" for a in posts[0]["argv"]),
               str(posts[0]["argv"]))
    check("首建：恰三次 API 呼叫", len(res.calls), 3)


# ==========================================================================
# R-4 群：ensure_field 與 write_field
# ==========================================================================

def test_ensure_field_existing_text_field() -> None:
    """@purpose ensure_field 對既有同名 TEXT 欄位回 FieldRef、不重建——重建會清掉既有值。
    @given 欄位 route 回含 'AIDLC Stage'（TEXT）的欄位表
    @step 執行 ensure_field | exit 0，result=ok，field_id=F_text，field_created=false
    @step 檢視 calls.jsonl | 零 createProjectV2Field
    @pass 既有欄位原樣沿用
    @api ProjectV2.fields
    @story S-5
    """
    res = run_board("ensure_field", routes=[
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": True}}}})},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD, TEXT_FIELD])},
    ])
    check("ensure_field 既有：exit 0", res.rc, 0)
    check("ensure_field 既有：result=ok", res.outputs.get("result"), "ok")
    check("ensure_field 既有：field_id", res.outputs.get("field_id"), "F_text")
    check("ensure_field 既有：field_created=false", res.outputs.get("field_created"), "false")
    check("ensure_field 既有：零建立呼叫", len(res.calls_matching("createProjectV2Field")), 0)


def test_ensure_field_same_name_different_type() -> None:
    """@purpose CannotCreate 可達前提之二（ADR-0016 §1 收斂後僅剩兩種）：同名欄位型別不同——不覆蓋、不重建，交 C-5 通報「需人工建立欄位」，exit 0 不紅燈。
    @given 欄位表含同名 'AIDLC Stage' 但型別 SINGLE_SELECT
    @step 執行 ensure_field | exit 0，result=cannot_create，reason 指明型別
    @pass CannotCreate 是回傳值且不動既有欄位
    @api ProjectV2.fields
    @story S-5
    """
    wrong = {"id": "F_wrong", "name": "AIDLC Stage", "dataType": "SINGLE_SELECT",
             "options": []}
    res = run_board("ensure_field", routes=[
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": True}}}})},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([wrong])},
    ])
    check("ensure_field 型別不同：exit 0", res.rc, 0)
    check("ensure_field 型別不同：result=cannot_create", res.outputs.get("result"), "cannot_create")
    check_true("ensure_field 型別不同：reason 指明型別",
               "型別不同" in res.outputs.get("reason", "") and "SINGLE_SELECT" in res.outputs.get("reason", ""),
               res.outputs.get("reason", ""))
    check("ensure_field 型別不同：零建立呼叫", len(res.calls_matching("createProjectV2Field")), 0)


def test_ensure_field_create_forbidden_cannot_create() -> None:
    """@purpose CannotCreate 可達前提之一：憑證缺 Projects 寫入權（FORBIDDEN／INSUFFICIENT_SCOPES）——回 cannot_create 而非紅燈，交 C-5 通報。
    @given 欄位表缺該欄位；createProjectV2Field route 回 FORBIDDEN
    @step 執行 ensure_field | exit 0，result=cannot_create，reason 指明寫入權
    @pass 權限失敗被分類為 CannotCreate 而非 ExternalError
    @api createProjectV2Field
    @story S-5
    """
    res = run_board("ensure_field", routes=[
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": True}}}})},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
        {"contains": ROUTE_CREATE_FIELD, "exit": 1,
         "stdout": errors_response(("FORBIDDEN", "Resource not accessible by personal access token"))},
    ])
    check("ensure_field FORBIDDEN：exit 0", res.rc, 0)
    check("ensure_field FORBIDDEN：result=cannot_create", res.outputs.get("result"), "cannot_create")
    check_true("ensure_field FORBIDDEN：reason 指明寫入權",
               "寫入權" in res.outputs.get("reason", ""), res.outputs.get("reason", ""))


def test_ensure_field_creates_when_missing() -> None:
    """@purpose [US:S-5 AC 2] 的「可自動建立」支（PRE-1 第五輪實測 createProjectV2Field 可用）：缺欄位時自動以 TEXT 建立。
    @given 欄位表缺該欄位；createProjectV2Field route 成功回新欄位 id
    @step 執行 ensure_field | exit 0，result=ok，field_id=F_new，field_created=true
    @pass 自動建立支可達且回報建立事實
    @api createProjectV2Field
    @story S-5
    """
    res = run_board("ensure_field", routes=[
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": True}}}})},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
        {"contains": ROUTE_CREATE_FIELD,
         "stdout": json.dumps({"data": {"createProjectV2Field":
                                        {"projectV2Field": {"id": "F_new", "name": "AIDLC Stage"}}}})},
    ])
    check("ensure_field 建立：exit 0", res.rc, 0)
    check("ensure_field 建立：result=ok", res.outputs.get("result"), "ok")
    check("ensure_field 建立：field_id", res.outputs.get("field_id"), "F_new")
    check("ensure_field 建立：field_created=true", res.outputs.get("field_created"), "true")


def test_write_field_item_absent_failed() -> None:
    """@purpose write_field 對不在板上的 issue 無寫入對象——回 Failed（回傳值、exit 0），不紅燈、不連坐 Status 寫入（R-4.1）。
    @given 回讀 route 回零筆
    @step 執行 write_field | exit 0，result=failed，message 指明無寫入對象
    @pass Failed 是回傳值
    @api Issue.projectItems
    @story S-5
    """
    res = run_board("write_field", env={"AIDLC_BINDING": "538",
                                        "AIDLC_FIELD_VALUE": "construction"}, routes=[
        {"contains": ROUTE_READ, "stdout": read_item_response([])},
    ])
    check("write_field 無對象：exit 0", res.rc, 0)
    check("write_field 無對象：result=failed", res.outputs.get("result"), "failed")
    check_true("write_field 無對象：message 指明",
               "無寫入對象" in res.outputs.get("message", ""), res.outputs.get("message", ""))


def test_write_field_create_failure_failed_not_red() -> None:
    """@purpose R-4.1（[US:S-5 AC 2] 的不連坐）：欄位不存在時嘗試建立、建立失敗 → Failed（exit 0）——欄位寫入的失敗**不得**讓 Status 寫入所在的 workflow 紅燈。
    @given 回讀正常、欄位表缺該欄位、createProjectV2Field route 失敗
    @step 執行 write_field | exit 0，result=failed，message 含建立失敗與 errors[].message
    @pass 建立失敗走 Failed 而非 ExternalError
    @api createProjectV2Field
    @story S-5
    """
    res = run_board("write_field", env={"AIDLC_BINDING": "538",
                                        "AIDLC_FIELD_VALUE": "construction"}, routes=[
        {"contains": ROUTE_READ,
         "stdout": read_item_response([item_node(status="Ready")])},
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": True}}}})},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD])},
        {"contains": ROUTE_CREATE_FIELD, "exit": 1,
         "stdout": errors_response(("FORBIDDEN", "Resource not accessible by personal access token"))},
    ])
    check("write_field 建立失敗：exit 0", res.rc, 0)
    check("write_field 建立失敗：result=failed", res.outputs.get("result"), "failed")
    check_true("write_field 建立失敗：message 保留 errors[].message",
               "Resource not accessible" in res.outputs.get("message", ""),
               res.outputs.get("message", ""))


def test_write_field_happy_path() -> None:
    """@purpose write_field 的正常路徑：欄位既存（TEXT）、item 在板上 → 以 value:{text:} 寫入。
    @given 回讀、Project、欄位表、text mutation 四條 route 皆正常
    @step 執行 write_field value=construction/code-generation | exit 0，result=written
    @step 檢視 mutation 呼叫 | text 值原樣傳遞且 fieldId=F_text
    @pass 寫入貫穿
    @api updateProjectV2ItemFieldValue
    @story S-5
    """
    res = run_board("write_field", env={"AIDLC_BINDING": "538",
                                        "AIDLC_FIELD_VALUE": "construction/code-generation"}, routes=[
        {"contains": ROUTE_READ,
         "stdout": read_item_response([item_node(status="Ready")])},
        {"contains": ROUTE_PROJECT,
         "stdout": json.dumps({"data": {"user": {"projectV2":
                                                 {"id": "PVT_STUB", "viewerCanUpdate": True}}}})},
        {"contains": ROUTE_FIELDS, "stdout": fields_response([STATUS_FIELD, TEXT_FIELD])},
        {"contains": ROUTE_TEXT_MUTATION,
         "stdout": json.dumps({"data": {"updateProjectV2ItemFieldValue":
                                        {"projectV2Item": {"id": "PVTI_STUB_1"}}}})},
    ])
    check("write_field：exit 0", res.rc, 0)
    check("write_field：result=written", res.outputs.get("result"), "written")
    muts = res.calls_matching("value:{text:")
    check("write_field：恰一次 text mutation", len(muts), 1)
    check_true("write_field：text 值原樣傳遞",
               any(a == "text=construction/code-generation" for a in muts[0]["argv"]),
               str(muts[0]["argv"]))
    check_true("write_field：fieldId 為既有欄位",
               any(a == "fieldId=F_text" for a in muts[0]["argv"]), str(muts[0]["argv"]))


# ==========================================================================
# R-6 群：write_body 的附加／替換／損壞三態
# ==========================================================================

def _write_body_routes(old_body: str, patch_exit: int = 0):
    return [
        {"contains": ["-X", "PATCH", "repos/opendiamonds/cloud-360/issues/538"],
         "exit": patch_exit, "stdout": json.dumps({"number": 538})},
        {"contains": ["repos/opendiamonds/cloud-360/issues/538"],
         "stdout": json.dumps({"number": 538, "body": old_body})},
    ]


def _patched_body(res: BoardResult) -> str:
    patches = res.calls_matching("-X", "PATCH")
    if len(patches) != 1:
        return f"<PATCH 呼叫數={len(patches)}>"
    return json.loads(patches[0]["stdin"])["body"]


def test_write_body_append_no_marker() -> None:
    """@purpose R-6.3 前半：body 無受管標記 → 區塊**附加**於既有內容之後，人寫的敘述一字不動（R-6.2）。
    @given issue body 為兩行人寫敘述（無標記）；block_text 為真的 render 輸出
    @step 執行 write_body | exit 0，result=written
    @step 檢視 PATCH payload | 原敘述逐位元保留 ＋ 空行 ＋ 區塊（不含 render 的尾端換行）
    @pass 附加語意逐位元正確
    @api PATCH /repos/{owner}/{repo}/issues/{issue_number}
    @story S-6
    """
    old_body = "人寫的第一行\n\n人寫的第二段。"
    block = render_block()
    res = run_board("write_body", env={"AIDLC_BINDING": "538",
                                       "AIDLC_BLOCK_TEXT": block},
                    routes=_write_body_routes(old_body))
    check("write_body 附加：exit 0", res.rc, 0)
    check("write_body 附加：result=written", res.outputs.get("result"), "written")
    check("write_body 附加：PATCH payload 逐位元",
          _patched_body(res), old_body + "\n\n" + block.rstrip("\n"))


def test_write_body_replace_existing_block() -> None:
    """@purpose R-6.3 後半：有標記 → 替換 BEGIN〜END **整段**（含兩者），前後的人寫內容一字不動——附加會產生第二個 BEGIN，使下一輪定位更不確定。
    @given body＝前言＋舊區塊（render status=Ready）＋後記；新 block_text 為 render status=Done
    @step 執行 write_body | exit 0，result=written
    @step 檢視 PATCH payload | 前言與後記逐位元保留；舊區塊整段換成新區塊；全文恰一個 BEGIN 標記
    @pass 替換而非附加
    @api PATCH /repos/{owner}/{repo}/issues/{issue_number}
    @story S-6
    """
    old_block = render_block(status="Ready")
    new_block = render_block(status="Done")
    prefix = "前言：這段是人寫的。\n\n"
    suffix = "\n後記：這段也是人寫的。"
    old_body = prefix + old_block.rstrip("\n") + suffix
    res = run_board("write_body", env={"AIDLC_BINDING": "538",
                                       "AIDLC_BLOCK_TEXT": new_block},
                    routes=_write_body_routes(old_body))
    check("write_body 替換：exit 0", res.rc, 0)
    check("write_body 替換：result=written", res.outputs.get("result"), "written")
    patched = _patched_body(res)
    check("write_body 替換：PATCH payload 逐位元",
          patched, prefix + new_block.rstrip("\n") + suffix)
    check("write_body 替換：恰一個 BEGIN 標記", patched.count("<!-- aidlc-sync:begin"), 1)


def test_write_body_corrupted_marker_failed() -> None:
    """@purpose R-6.6：有 BEGIN 無 END、順序顛倒、或標記不成行 ⇒ body 已損壞——回 Failed（exit 0）**不猜、不附加**；附加會讓下一輪的定位更不確定。
    @given 三種損壞 body：缺 END／END 在 BEGIN 之前／sigil 只出現在行中
    @step 對三者各執行 write_body | exit 0，result=failed，message 指明 R-6.6 或損壞
    @step 檢視 calls.jsonl | **零** PATCH 呼叫
    @pass 三種損壞形態皆拒寫
    @api PATCH /repos/{owner}/{repo}/issues/{issue_number}
    @story S-6
    """
    block = render_block()
    begin_line = block.splitlines()[0]
    end_line = block.rstrip("\n").splitlines()[-1]
    cases = {
        "缺 END": f"前言\n{begin_line}\n- **Status**: Ready\n（結束標記被人刪了）",
        "順序顛倒": f"前言\n{end_line}\n中間\n{begin_line}\n殘段",
        "標記不成行": f"前言 {begin_line} 同一行的其他字",
    }
    for name, old_body in cases.items():
        res = run_board("write_body", env={"AIDLC_BINDING": "538",
                                           "AIDLC_BLOCK_TEXT": block},
                        routes=_write_body_routes(old_body))
        check(f"write_body 損壞（{name}）：exit 0", res.rc, 0)
        check(f"write_body 損壞（{name}）：result=failed", res.outputs.get("result"), "failed")
        check_true(f"write_body 損壞（{name}）：message 指明損壞",
                   "R-6.6" in res.outputs.get("message", "") or "損壞" in res.outputs.get("message", ""),
                   res.outputs.get("message", ""))
        check(f"write_body 損壞（{name}）：零 PATCH", len(res.calls_matching("-X", "PATCH")), 0)


def test_write_body_get_failure_is_failed() -> None:
    """@purpose R-6.4：write_body 的一切失敗（含取回 body 的讀取步）都走 Failed 回傳值——不連坐 Status 寫入、不紅燈。
    @given GET issue 的 route 回 HTTP 404
    @step 執行 write_body | exit 0，result=failed，http_status=404
    @pass 讀取失敗也不紅燈
    @api GET /repos/{owner}/{repo}/issues/{issue_number}
    @story S-6
    """
    block = render_block()
    res = run_board("write_body", env={"AIDLC_BINDING": "538",
                                       "AIDLC_BLOCK_TEXT": block}, routes=[
        {"contains": ["repos/opendiamonds/cloud-360/issues/538"], "exit": 1,
         "stdout": json.dumps({"message": "Not Found"}),
         "stderr": "gh: Not Found (HTTP 404)\n"},
    ])
    check("write_body GET 失敗：exit 0", res.rc, 0)
    check("write_body GET 失敗：result=failed", res.outputs.get("result"), "failed")
    check("write_body GET 失敗：http_status=404", res.outputs.get("http_status"), "404")


# ==========================================================================
# 進入點
# ==========================================================================

TESTS = [
    test_sec1_action_yml_no_credential_input,
    test_r5_unknown_operation_rejected,
    test_r5_seven_operations_dispatch,
    test_marker_extraction_matches_render,
    test_errclass_row1_notfound_is_external_error,
    test_errclass_rows_2_3_4_validation_on_mutation,
    test_two_layer_check_catches_errors_with_exit_zero,
    test_sec4_message_scrubbed,
    test_r12_filter_picks_configured_project,
    test_r13_zero_items_all_null,
    test_r14_multiple_items_external_error,
    test_read_item_delegates_hash_to_u2,
    test_read_issue_state,
    test_write_status_aborted_no_mutation,
    test_write_status_written_uses_resolved_option_id,
    test_write_status_expected_empty_means_unset,
    test_write_status_item_absent_aborted,
    test_create_item_existing_binding_no_api_calls,
    test_create_item_first_build_checks_project_writable,
    test_create_item_happy_path,
    test_ensure_field_existing_text_field,
    test_ensure_field_same_name_different_type,
    test_ensure_field_create_forbidden_cannot_create,
    test_ensure_field_creates_when_missing,
    test_write_field_item_absent_failed,
    test_write_field_create_failure_failed_not_red,
    test_write_field_happy_path,
    test_write_body_append_no_marker,
    test_write_body_replace_existing_block,
    test_write_body_corrupted_marker_failed,
    test_write_body_get_failure_is_failed,
]


def main() -> int:
    if not BOARD_SH.exists():
        print(f"找不到 {BOARD_SH}", file=sys.stderr)
        return 2
    if not BLOCK_SH.exists():
        print(f"找不到 U-2 的 {BLOCK_SH}（標記萃取與 hash 委派的測試需要它）", file=sys.stderr)
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
