#!/usr/bin/env python3
"""live 斷言 runner — U-3「看板客戶端」composite action（真實 API 層）。

用法：
    GH_TOKEN="$(gh auth token)" python3 .github/actions/aidlc-sync-board/run-live-tests.py

非零 exit 表失敗或**不完整**：GH_TOKEN 缺席且 `gh auth token` 也拿不到時，本 runner
以 exit 3 明確聲明「live 層未執行」——不靜默跳過（計畫 Step 8 的逐字要求）。

**寫入對象只有測試看板 #23**（ADR-A3 ＋ ADR-0016 §3 的兩個限定條件：與 repo 同
擁有者、Status 選項與 #16 同名）。SEC-3 防呆：進場即斷言 AIDLC_PROJECT_NUMBER
!= 16，不符即 exit 4——同一份憑證同時能寫 #16，隔離只靠這個設定值。

covers（unit-of-work.md 的 U-3 完成判準，經 code-generation plan 逐條）：
    (a) 回讀不符 → Aborted 且看板值未變
    (b) 以 existing_binding 重跑首建不產生第二則 issue／第二筆 item
    (c) read_item 反查 issue #538 回 #23 的 item
    (d) name→id 解析對六個 Status 選項全數命中且非硬編碼
    (e) write_body round-trip（managed_block_hash 非 null 且等於 U-2 hash 重算值）
    (f) ensure_field 對既有欄位回 FieldRef 不重建
    (g)（加測）write_field round-trip

測試殘留：自訂欄位用 `aidlc-sync-test-` 前綴建立、測畢刪除；issue #538 的 body 與
Status 測畢還原；**issue #538 保持開啟**（PRE-1 待清理表：留到 U-3 驗完）。
R-1.4 的多筆分支**不在本檔**——它無可構造的 live 反例（ADR-0016 §6），只在 stub
層驗，不發明假的觸發途徑。R-2.4 的競態視窗**沒有任何測試涵蓋**（重現需精準時序，
已由 ADR-0015 §2 綁進 Bolt 1 gate 的揭露項）——這是如實記載的已知缺口。
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BOARD_SH = HERE / "board.sh"
BLOCK_SH = HERE.parent / "aidlc-sync-block" / "block.sh"

BASH = os.environ.get("AIDLC_BOARD_BASH", "bash")

PROJECT_OWNER = os.environ.get("AIDLC_PROJECT_OWNER", "opendiamonds")
PROJECT_NUMBER = os.environ.get("AIDLC_PROJECT_NUMBER", "23")

# SEC-3 的唯一禁區。具名常數而非散落的字面值——這道防線是使用者明示的硬約束
# （「用測試看板 #23，不要碰 #16」），它的值不該要靠 grep 才找得到。
LIVE_FORBIDDEN_PROJECT = 16
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "opendiamonds/cloud-360")
BINDING = os.environ.get("AIDLC_LIVE_BINDING", "538")
TEST_FIELD = "aidlc-sync-test-ensure"

STATUS_NAMES = ["Backlog", "Nice to have", "Ready", "In progress", "In review", "Done"]

FAILURES: list[str] = []
CHECKS = 0
TOKEN = ""


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


def base_env() -> dict:
    env = dict(os.environ)
    env.update({
        "GH_TOKEN": TOKEN,
        "AIDLC_PROJECT_OWNER": PROJECT_OWNER,
        "AIDLC_PROJECT_NUMBER": PROJECT_NUMBER,
        "AIDLC_FIELD_NAME": TEST_FIELD,
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_OUTPUT": "",
    })
    return env


class Result:
    def __init__(self, proc: subprocess.CompletedProcess):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.outputs: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if "=" in line:
                name, _, value = line.partition("=")
                self.outputs[name] = value


def board(operation: str, **extra_env) -> Result:
    env = base_env()
    env["AIDLC_OPERATION"] = operation
    for key, value in extra_env.items():
        env[key] = value
    return Result(subprocess.run([BASH, str(BOARD_SH)], capture_output=True,
                                 text=True, env=env))


def board_argv(*argv: str) -> Result:
    env = base_env()
    env["AIDLC_OPERATION"] = ""
    return Result(subprocess.run([BASH, str(BOARD_SH), *argv], capture_output=True,
                                 text=True, env=env))


# ---- 本 runner 自己的獨立查證通道（不經 board.sh，避免拿受測物驗受測物）----

def gh(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True,
                          env=base_env(), input=input_text)


def gql_raw(query: str, **variables) -> dict:
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        flag = "-F" if isinstance(value, int) else "-f"
        args += [flag, f"{key}={value}"]
    proc = gh(*args)
    if proc.returncode != 0:
        raise RuntimeError(f"harness gql 失敗：{proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def harness_item(field_name: str = "Status") -> dict | None:
    """從 issue 側反查 #23 上的 item（獨立於 board.sh 的同型查詢）。"""
    owner, name = REPOSITORY.split("/", 1)
    data = gql_raw(
        '''query($owner:String!,$name:String!,$number:Int!){
             repository(owner:$owner,name:$name){
               issue(number:$number){
                 state body
                 projectItems(first:50){
                   nodes{ id
                     project{ id number owner{ ... on User{ login } } }
                     statusValue: fieldValueByName(name:"Status"){
                       ... on ProjectV2ItemFieldSingleSelectValue{ name } }
                     customValue: fieldValueByName(name:"''' + field_name + '''"){
                       ... on ProjectV2ItemFieldTextValue{ text } }
                   }
                 }
               }
             }
           }''',
        owner=owner, name=name, number=int(BINDING))
    issue = data["data"]["repository"]["issue"]
    nodes = [n for n in issue["projectItems"]["nodes"]
             if n["project"]["number"] == int(PROJECT_NUMBER)]
    if not nodes:
        return None
    node = dict(nodes[0])
    node["issue_state"] = issue["state"].lower()
    node["issue_body"] = issue["body"] or ""
    return node


def harness_fields() -> list[dict]:
    data = gql_raw(
        '''query($owner:String!,$number:Int!){
             user(login:$owner){ projectV2(number:$number){
               fields(first:100){ nodes{
                 ... on ProjectV2FieldCommon{ id name dataType }
                 ... on ProjectV2SingleSelectField{ options{ id name } }
               } } } } }''',
        owner=PROJECT_OWNER, number=int(PROJECT_NUMBER))
    return data["data"]["user"]["projectV2"]["fields"]["nodes"]


def harness_item_count() -> int:
    data = gql_raw(
        '''query($owner:String!,$number:Int!){
             user(login:$owner){ projectV2(number:$number){
               items(first:1){ totalCount } } } }''',
        owner=PROJECT_OWNER, number=int(PROJECT_NUMBER))
    return data["data"]["user"]["projectV2"]["items"]["totalCount"]


def harness_get_body() -> str:
    owner, name = REPOSITORY.split("/", 1)
    proc = gh("api", f"repos/{owner}/{name}/issues/{BINDING}")
    if proc.returncode != 0:
        raise RuntimeError(f"harness GET issue 失敗：{proc.stderr.strip()[:200]}")
    return json.loads(proc.stdout).get("body") or ""


def harness_patch_body(body: str) -> None:
    owner, name = REPOSITORY.split("/", 1)
    payload = json.dumps({"body": body})
    proc = gh("api", "-X", "PATCH", f"repos/{owner}/{name}/issues/{BINDING}",
              "--input", "-", input_text=payload)
    if proc.returncode != 0:
        raise RuntimeError(f"harness PATCH issue 失敗：{proc.stderr.strip()[:200]}")


def u2_render(status: str, traceable_row: str) -> str:
    env = dict(os.environ)
    env.update({"AIDLC_STATUS": status, "AIDLC_TRACEABLE_ROW": traceable_row,
                "AIDLC_REASON_CODE": "", "AIDLC_SCOPE_NOTE": "none",
                "AIDLC_DECIDED_AT": "", "AIDLC_REJECTION_CLOSED_AT": "",
                "GITHUB_OUTPUT": ""})
    proc = subprocess.run([BASH, str(BLOCK_SH), "render"], capture_output=True,
                          text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"block.sh render 失敗：{proc.stderr}")
    return proc.stdout


def u2_hash_of_body(body: str) -> str:
    env = dict(os.environ)
    env["AIDLC_ISSUE_BODY"] = body
    env["GITHUB_OUTPUT"] = ""
    parse = subprocess.run([BASH, str(BLOCK_SH), "parse"], capture_output=True,
                           text=True, env=env)
    fields = dict(line.partition("=")[::2] for line in parse.stdout.splitlines())
    if fields.get("found") != "true":
        return ""
    env2 = dict(os.environ)
    env2["GITHUB_OUTPUT"] = ""
    for key in ("format_version", "status", "traceable_row", "reason_category",
                "decided_at", "scope_note", "rejection_closed_at"):
        env2[f"AIDLC_BLOCK_{key.upper()}"] = fields.get(f"block_{key}", "")
    hashed = subprocess.run([BASH, str(BLOCK_SH), "hash"], capture_output=True,
                            text=True, env=env2)
    return dict(line.partition("=")[::2]
                for line in hashed.stdout.splitlines()).get("content_hash", "")


def u2_marker_sigil() -> str:
    res = board_argv("markers")
    if res.rc != 0:
        raise RuntimeError(f"board.sh markers 失敗：{res.stderr}")
    return res.outputs["MARKER_SIGIL"]


# ==========================================================================
# 測試主體（有序；共享狀態記錄於 STATE）
# ==========================================================================

STATE: dict = {}


def step_preflight() -> None:
    """@purpose 進場防呆與基準採樣：SEC-3 斷言目標非 #16；記下 #538 的原始 Status 與 body 供測畢還原；殘留的受管區塊（前次 run 中斷的產物）先清掉。
    @given 憑證已解析；測試看板 #23（opendiamonds 名下，ADR-0016 §3 的兩個限定條件已由 PRE-1 建立）
    @step 斷言 AIDLC_PROJECT_NUMBER != 16 | 不符即 exit 4，不進任何寫入
    @step 讀 #538 的 item、Status、body | issue 存在且 open
    @step body 若含受管標記（前次殘留）| 依本 runner 自己的附加形狀切除並還原
    @pass 基準記錄完成
    @api Issue.projectItems
    @story S-3
    """
    node = harness_item()
    check_true("preflight：issue #538 在 #23 上（PRE-1 第五輪建立的前提）",
               node is not None, "反查不到 item——測試前提不成立")
    if node is None:
        raise RuntimeError("preflight 失敗，不繼續")
    check("preflight：issue open", node["issue_state"], "open")
    body = node["issue_body"]
    sigil = u2_marker_sigil()
    if sigil in body:
        # 前次 run 中斷的殘留：本 runner 的附加形狀固定為「原文 + \n\n + 區塊」，
        # 依此切除。這是清理自己的殘留，不是猜測人寫的內容。
        pos = body.find("\n\n" + sigil)
        clean = body[:pos] if pos >= 0 else ("" if body.startswith(sigil) else body)
        check_true("preflight：殘留區塊可定位切除", sigil not in clean, "切除後仍有標記")
        harness_patch_body(clean)
        body = clean
    STATE["orig_body"] = body
    STATE["orig_status"] = (node.get("statusValue") or {}).get("name") or ""


def test_f_ensure_field_no_rebuild() -> None:
    """@purpose 完成判準 (f)：ensure_field 對既有欄位回 FieldRef 不重建——第一次呼叫建立（或沿用殘留），第二次必須回同一個 field_id 且欄位總數不變。
    @given 測試欄位名 aidlc-sync-test-ensure（前綴依計畫，測畢刪除）
    @step ensure_field 第一次 | result=ok，取得 field_id
    @step 記錄欄位總數；ensure_field 第二次 | result=ok，field_id 相同，field_created=false
    @step 再數欄位總數 | 與第二次呼叫前相同
    @pass 冪等且不重建
    @api createProjectV2Field
    @story S-5
    """
    res1 = board("ensure_field")
    check("(f) 第一次 ensure_field：exit 0", res1.rc, 0)
    check("(f) 第一次 ensure_field：result=ok", res1.outputs.get("result"), "ok")
    field_id = res1.outputs.get("field_id", "")
    check_true("(f) 第一次 ensure_field：field_id 非空", bool(field_id), res1.stdout)
    STATE["test_field_id"] = field_id

    count_before = len(harness_fields())
    res2 = board("ensure_field")
    check("(f) 第二次 ensure_field：exit 0", res2.rc, 0)
    check("(f) 第二次 ensure_field：result=ok", res2.outputs.get("result"), "ok")
    check("(f) 第二次 ensure_field：同一 field_id", res2.outputs.get("field_id"), field_id)
    check("(f) 第二次 ensure_field：field_created=false",
          res2.outputs.get("field_created"), "false")
    check("(f) 欄位總數不變", len(harness_fields()), count_before)


def test_c_read_item_reverse_lookup() -> None:
    """@purpose 完成判準 (c)：read_item 以 Issue.projectItems 反查 issue #538，回 #23 的 item——與 harness 的獨立查詢逐欄一致。
    @given #538 在 #23 上（preflight 已驗）
    @step 執行 read_item | exit 0
    @step 與 harness 獨立反查的 Status 比對 | 一致；issue_number=538；issue_state=open
    @pass 反查路徑（R-1.0／[Q1=A]）在真實組態下成立
    @api Issue.projectItems
    @story S-3
    """
    res = board("read_item", AIDLC_BINDING=BINDING)
    check("(c) read_item：exit 0", res.rc, 0)
    check("(c) read_item：issue_number", res.outputs.get("issue_number"), BINDING)
    check("(c) read_item：issue_state=open", res.outputs.get("issue_state"), "open")
    node = harness_item()
    independent = (node.get("statusValue") or {}).get("name") or ""
    check("(c) read_item：status 與獨立查詢一致", res.outputs.get("status"), independent)


def test_d_status_name_resolution() -> None:
    """@purpose 完成判準 (d)：name→id 解析對六個 Status 選項全數命中且**非硬編碼**——解析值必須等於 harness 獨立列舉的選項表（#23 的 id 與 #16 不同，寫死任何一邊都會在此紅）。
    @given #23 的 Status 六選項已對齊 #16 的名稱（ADR-0016 §3 條件 2）
    @step 對六個名稱各跑 board.sh resolve_status | 各回一個 8 位十六進位 option id
    @step 與 harness 獨立列舉的 name→id 對照 | 逐一相等且六個 id 互異
    @pass 執行期解析、零硬編碼
    @api ProjectV2SingleSelectField.options
    @story S-3
    """
    status_field = next((f for f in harness_fields() if f.get("name") == "Status"), None)
    check_true("(d) harness 找得到 Status 欄位", status_field is not None, "")
    independent = {o["name"]: o["id"] for o in (status_field or {}).get("options", [])}
    check("(d) harness 的選項名集合",
          sorted(independent.keys()), sorted(STATUS_NAMES))
    resolved = {}
    for name in STATUS_NAMES:
        res = board_argv("resolve_status", name)
        check(f"(d) resolve_status '{name}'：exit 0", res.rc, 0)
        oid = res.outputs.get("option_id", "")
        check_true(f"(d) '{name}' 的 option id 為 8 位十六進位",
                   len(oid) == 8 and all(c in "0123456789abcdef" for c in oid), oid)
        resolved[name] = oid
    check("(d) 解析值與獨立列舉逐一相等", resolved, independent)
    check("(d) 六個 id 互異", len(set(resolved.values())), 6)


def test_roundtrip_write_status() -> None:
    """@purpose write_status 的 live round-trip：以正確的 expected 寫入新值，read_item 回讀到它——證明回讀、解析、mutation 三段在真實組態下串通。
    @given preflight 記下的原始 Status S0
    @step write_status expected=S0 desired=T（T≠S0）| result=written
    @step read_item | status=T
    @pass 寫入生效且回讀一致
    @api updateProjectV2ItemFieldValue
    @story S-3
    """
    s0 = STATE["orig_status"]
    target = "Ready" if s0 != "Ready" else "In progress"
    STATE["written_status"] = target
    res = board("write_status", AIDLC_BINDING=BINDING,
                AIDLC_EXPECTED_STATUS=s0, AIDLC_DESIRED_STATUS=target)
    check("roundtrip write_status：exit 0", res.rc, 0)
    check("roundtrip write_status：result=written", res.outputs.get("result"), "written")
    res2 = board("read_item", AIDLC_BINDING=BINDING)
    check("roundtrip read_item：status 已更新", res2.outputs.get("status"), target)


def test_a_aborted_leaves_board_unchanged() -> None:
    """@purpose 完成判準 (a)：回讀不符 → Aborted 且**看板值未變**——R-2.1 的「不送出寫入」要在真實 API 上驗到底（不能只信 stub 的呼叫記錄）。
    @given 看板現值為 T（前一測寫入）；故意給一個錯的 expected
    @step write_status expected=WRONG desired=Backlog | exit 0，result=aborted，actual_status=T，expected_status=WRONG
    @step harness 獨立回讀看板 | 仍為 T（未被 Backlog 覆寫）
    @pass Aborted 不產生任何看板變更且不紅燈
    @api updateProjectV2ItemFieldValue
    @story S-3
    """
    current = STATE["written_status"]
    wrong = "Done" if current != "Done" else "Backlog"
    res = board("write_status", AIDLC_BINDING=BINDING,
                AIDLC_EXPECTED_STATUS=wrong, AIDLC_DESIRED_STATUS="Backlog")
    check("(a) Aborted：exit 0", res.rc, 0)
    check("(a) Aborted：result=aborted", res.outputs.get("result"), "aborted")
    check("(a) Aborted：actual_status", res.outputs.get("actual_status"), current)
    check("(a) Aborted：expected_status", res.outputs.get("expected_status"), wrong)
    node = harness_item()
    check("(a) Aborted：看板值未變",
          (node.get("statusValue") or {}).get("name") or "", current)


def test_e_write_body_roundtrip() -> None:
    """@purpose 完成判準 (e)：write_body round-trip——寫入後 read_item 的 managed_block_hash 非 null 且等於 U-2 parse→hash 的重算值；再寫一次走**替換**而非二次附加。
    @given #538 的 body 無受管標記（preflight 已清）；區塊由真的 block.sh render 產生
    @step write_body（區塊 1）| result=written
    @step read_item | managed_block_hash 非空，等於 harness 以 U-2 重算 body 的值，也等於區塊 1 自身的雜湊
    @step 檢視 body | 原文保留於前、恰一個 BEGIN 標記
    @step write_body（區塊 2，不同 Status）| result=written；body 仍恰一個 BEGIN；雜湊改為區塊 2 的值
    @pass 附加與替換都在真實 API 上成立且雜湊委派一致
    @api PATCH /repos/{owner}/{repo}/issues/{issue_number}
    @story S-6
    """
    sigil = u2_marker_sigil()
    block1 = u2_render(STATE["written_status"], "| live | U-3 (e) |")
    res = board("write_body", AIDLC_BINDING=BINDING, AIDLC_BLOCK_TEXT=block1)
    check("(e) write_body 第一次：exit 0", res.rc, 0)
    check("(e) write_body 第一次：result=written", res.outputs.get("result"), "written")

    read1 = board("read_item", AIDLC_BINDING=BINDING)
    hash1 = read1.outputs.get("managed_block_hash", "")
    check_true("(e) managed_block_hash 非 null", len(hash1) == 64, hash1)
    body_after = harness_get_body()
    check("(e) 雜湊等於 U-2 對 body 的重算值", hash1, u2_hash_of_body(body_after))
    check("(e) 雜湊等於區塊 1 自身的雜湊", hash1, u2_hash_of_body(block1))
    if STATE["orig_body"]:
        check_true("(e) 原文保留於前", body_after.startswith(STATE["orig_body"]),
                   body_after[:120])
    check("(e) 恰一個 BEGIN 標記", body_after.count(sigil), 1)

    other = "In review" if STATE["written_status"] != "In review" else "Done"
    block2 = u2_render(other, "| live | U-3 (e2) |")
    res2 = board("write_body", AIDLC_BINDING=BINDING, AIDLC_BLOCK_TEXT=block2)
    check("(e) write_body 第二次：exit 0", res2.rc, 0)
    check("(e) write_body 第二次：result=written", res2.outputs.get("result"), "written")
    body_after2 = harness_get_body()
    check("(e) 第二次後仍恰一個 BEGIN（替換非附加）", body_after2.count(sigil), 1)
    read2 = board("read_item", AIDLC_BINDING=BINDING)
    check("(e) 雜湊已改為區塊 2 的值",
          read2.outputs.get("managed_block_hash", ""), u2_hash_of_body(block2))


def test_g_write_field_roundtrip() -> None:
    """@purpose （加測）write_field 的 live round-trip：對 (f) 建立的 TEXT 欄位寫值，read_item 的 field_value 回讀到它。
    @given aidlc-sync-test-ensure 欄位已由 (f) 建立
    @step write_field value=live-probe | result=written
    @step read_item | field_value=live-probe
    @pass 文字欄位寫入貫穿
    @api updateProjectV2ItemFieldValue
    @story S-5
    """
    res = board("write_field", AIDLC_BINDING=BINDING, AIDLC_FIELD_VALUE="live-probe")
    check("(g) write_field：exit 0", res.rc, 0)
    check("(g) write_field：result=written", res.outputs.get("result"), "written")
    res2 = board("read_item", AIDLC_BINDING=BINDING)
    check("(g) read_item：field_value 回讀", res2.outputs.get("field_value"), "live-probe")


def test_b_existing_binding_no_second_item() -> None:
    """@purpose 完成判準 (b)：以 existing_binding 重跑首建**不產生第二則 issue／第二筆 item**——R-3.1 是「每 push 一次多一張卡」的唯一攔截。
    @given #23 的 item 總數已採樣
    @step create_item existing_binding=538 | exit 0，binding=538，created=false
    @step harness 重數 #23 的 item 總數 | 不變
    @pass 攔截在真實組態下成立
    @api addProjectV2ItemById
    @story S-1
    """
    count_before = harness_item_count()
    res = board("create_item", AIDLC_EXISTING_BINDING=BINDING)
    check("(b) create_item：exit 0", res.rc, 0)
    check("(b) create_item：binding 原值回傳", res.outputs.get("binding"), BINDING)
    check("(b) create_item：created=false", res.outputs.get("created"), "false")
    check("(b) item 總數不變", harness_item_count(), count_before)


def cleanup() -> None:
    """測畢還原（不是測試，是義務）：body 還原、Status 還原（原為未設值則清除）、
    測試欄位刪除、issue 保持開啟的終驗。清理失敗要大聲——殘留要被看見。"""
    # 1. body 還原
    try:
        harness_patch_body(STATE.get("orig_body", ""))
        check("cleanup：body 已還原", harness_get_body(), STATE.get("orig_body", ""))
    except Exception as exc:
        FAILURES.append(f"cleanup：body 還原失敗：{exc!r}")

    # 2. Status 還原
    try:
        node = harness_item()
        current = (node.get("statusValue") or {}).get("name") or "" if node else ""
        orig = STATE.get("orig_status", "")
        if current != orig:
            if orig:
                res = board("write_status", AIDLC_BINDING=BINDING,
                            AIDLC_EXPECTED_STATUS=current, AIDLC_DESIRED_STATUS=orig)
                check("cleanup：Status 已還原", res.outputs.get("result"), "written")
            else:
                # 原為未設值：write_status 沒有「寫 null」的語意（「決定不寫」不經
                # 它），清除走 harness 自己的 clearProjectV2ItemFieldValue。
                status_field = next(f for f in harness_fields() if f["name"] == "Status")
                gql_raw(
                    '''mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!){
                         clearProjectV2ItemFieldValue(input:{
                           projectId:$projectId,itemId:$itemId,fieldId:$fieldId
                         }){ projectV2Item{ id } } }''',
                    projectId=node["project"]["id"],
                    itemId=node["id"], fieldId=status_field["id"])
    except Exception as exc:
        FAILURES.append(f"cleanup：Status 還原失敗：{exc!r}")

    # 3. 測試欄位刪除（aidlc-sync-test- 前綴，計畫的清理承諾）
    try:
        for field in harness_fields():
            if field.get("name", "").startswith("aidlc-sync-test-"):
                gql_raw(
                    '''mutation($fieldId:ID!){
                         deleteProjectV2Field(input:{fieldId:$fieldId}){
                           projectV2Field{ ... on ProjectV2FieldCommon{ id } } } }''',
                    fieldId=field["id"])
        leftover = [f["name"] for f in harness_fields()
                    if f.get("name", "").startswith("aidlc-sync-test-")]
        check("cleanup：測試欄位已刪除", leftover, [])
    except Exception as exc:
        FAILURES.append(f"cleanup：測試欄位刪除失敗：{exc!r}")

    # 4. issue #538 保持開啟（PRE-1 待清理表：留到 U-3 驗完，本 runner 不關它）
    try:
        node = harness_item()
        check("cleanup：issue #538 保持開啟", node["issue_state"] if node else "?", "open")
    except Exception as exc:
        FAILURES.append(f"cleanup：終驗失敗：{exc!r}")


STEPS = [
    step_preflight,
    test_f_ensure_field_no_rebuild,
    test_c_read_item_reverse_lookup,
    test_d_status_name_resolution,
    test_roundtrip_write_status,
    test_a_aborted_leaves_board_unchanged,
    test_e_write_body_roundtrip,
    test_g_write_field_roundtrip,
    test_b_existing_binding_no_second_item,
]


def main() -> int:
    global TOKEN
    # ---- 憑證解析：env GH_TOKEN → gh auth token → 明確 skip（非零 exit）----
    TOKEN = os.environ.get("GH_TOKEN", "")
    if not TOKEN:
        proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if proc.returncode == 0:
            TOKEN = proc.stdout.strip()
    if not TOKEN:
        print("SKIP：無 GH_TOKEN 且 gh auth token 取不到憑證——live 層未執行，"
              "U-3 的完成判準 (a)〜(f) 未被本次驗證。以 exit 3 聲明不完整，不靜默。",
              file=sys.stderr)
        return 3

    # ---- SEC-3 防呆：正式看板 #16 絕對不許寫入 ----
    #
    # 比對**必須先正規化成整數再比**，不能比字串。理由是實測出來的，不是講究：
    # 本檔每一個真正的查詢點（:153 的 items 過濾、:170／:179 的 projectV2）用的
    # 都是 int(PROJECT_NUMBER)，而 "016"／" 16"／"16 "／"0016"／"+16" 這些值在
    # int() 之下**全部等於 16**、在字串比對之下**全部不等於 "16"**——守衛放行、
    # 查詢卻打到正式看板。實測（U-6 的 reviewer iteration 1 Critical）把守衛改回
    # 字串比對後，AIDLC_PROJECT_NUMBER=016 會直接印出 "live 對象：…/projects/016"
    # 並繼續往下跑。這是這道防線唯一要擋的事，卻正好從它的縫裡漏過去。
    #
    # 無法解析成整數的值也一律拒絕（fail closed）。
    #
    # 【跨單元修正，2026-09-05】本檔屬 U-3（已交付），缺陷由 U-6 的同型守衛被
    # reviewer 攻破時連帶查出。經人工裁決一併修正——兩者守的是同一塊正式看板、
    # 同一條使用者硬約束。修法與 U-6 的 run-live-tests.py 逐字相同。
    try:
        project_number_int = int(str(PROJECT_NUMBER).strip())
    except (TypeError, ValueError):
        print(f"REFUSE：AIDLC_PROJECT_NUMBER={PROJECT_NUMBER!r} 不是整數，無法判定"
              "它是不是正式看板（SEC-3）。exit 4。", file=sys.stderr)
        return 4
    if project_number_int == LIVE_FORBIDDEN_PROJECT:
        print(f"REFUSE：AIDLC_PROJECT_NUMBER={PROJECT_NUMBER!r} 解析為 "
              f"#{project_number_int}，是正式看板（SEC-3）。live 測試只准寫測試"
              "看板。exit 4。", file=sys.stderr)
        return 4

    print(f"live 對象：{PROJECT_OWNER}/projects/{PROJECT_NUMBER}，issue #{BINDING}"
          f"（repo {REPOSITORY}）")
    aborted = False
    try:
        for step in STEPS:
            before = len(FAILURES)
            try:
                step()
            except Exception as exc:
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
