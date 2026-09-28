#!/usr/bin/env python3
"""live 斷言 runner — U-5「通報」composite action（真實 GitHub Issues 層）。

用法：
    python3 .github/actions/aidlc-sync-notify/run-live-tests.py

非零 exit 表失敗或**不完整**：拿不到 gh 憑證、或憑證對 repo 無寫入權時，本 runner 以
exit 3 明確聲明「live 層未執行」——不靜默跳過（計畫 Step 7 的逐字要求）。exit 4 是
**拒絕執行**（防呆條件不成立），與失敗（exit 1）分開。

為什麼非跑不可：U-5 的完成判準（[ug:unit-of-work.md]）是「同一個鍵連續失敗兩輪後，
該鍵的開啟中通報 issue 數為 1 且 comment 數增加 1」。run-stub-tests.py 有這一條，但它
是在**我們自己寫的 shim** 上成立的。issue 的生命週期（建立後立刻能不能被
`gh issue list` 看到、關閉後會不會還在 --state open 裡）是 GitHub 的行為，不是我們
能斷言的——而本輪第一次真的打下去，就推翻了一句上游主張（見下）。

==========================================================================
本站實測推翻的一項上游主張（2026-09-05，opendiamonds/cloud-360）
==========================================================================
`nfr-requirements/tech-stack-decisions.md` 逐字寫著：搜尋索引有延遲，所以
「改用 `list --label` ＋ 本地比對後，**讀的是 issue 的即時狀態而非索引**」。

**這句話不成立。** 本 runner 的第一次執行（未加等待）留下三則 issue 而非兩則，
追查後以獨立探測複驗：建一則帶 label 的 issue 之後輪詢，
`gh issue list --repo … --label … --state open` 與 REST
`GET /repos/{owner}/{repo}/issues?state=open&labels=…` **兩者都在 t=3.6s 時看不到它、
t=5.9s 時才看到**。label 過濾的列舉同樣是最終一致的，不是即時狀態。

**對設計的影響（本檔只記載，不逕自改上游）**：
  - 產品行為**不需要改**。這正是缺口 J-1（並行 run 各看到 0 筆）的另一個入口，而
    ADR-A8 對它的處置——R-2 第 4 步由 `notify` 自己收斂——一字未變地涵蓋它：下一次
    失敗發生時重複即被清掉。`business-logic-model.md` 也已逐字寫明「這不消除 J-1」。
  - **但完成判準的成立有一個前提沒有被寫下來**：「連續兩輪」之間的間隔必須大於這個
    傳播窗口（實測 ~6s），否則第二輪會開出重複而不是追加。實務上 U-6 是 push／PR
    觸發、U-7 是每日排程，間隔遠大於 6s，所以這是**可接受的前提**而非缺陷——但它
    是前提，不是巧合，該被寫進 `tech-stack-decisions.md`。
  - 落點：`tech-stack-decisions.md` 的「不依賴搜尋索引」段落與 `business-rules.md`
    R-2 的成本段。確認人：Bolt 1 gate。

因此本 runner 在兩輪之間、以及每一個「關閉後查列舉」的斷言之前，都有一個**明寫且
有上限的等待**（wait_until），並把實測秒數印在痕跡行——那個數字是本輪 live 測試的
產出之一，不是被藏起來的 sleep。

**寫入對象的三層防呆**（Plan Approval 裁決 4：沒有 sandbox repo，只能在 cloud-360
本身開真 issue）：
  1. 進場即斷言 intent_id 以 aidlc-sync-test- 開頭、目標 repo 為 opendiamonds/cloud-360
     且本機 origin 指向它，不符即 exit 4；
  2. 受測物 notify.sh 的所有 live 呼叫都在 **gh shim** 之下執行：shim 對每一個
     `issue close`／`comment`／`edit` 斷言目標編號在**本輪建立的 issue 允許清單**內，
     不在即 exit 97。這是對 R-2.1（以內文鍵比對）的**外部**兜底——萬一鍵比對寫錯，
     平台不會救，而被關掉的 issue 不可自動復原（security-requirements.md SEC-1）。
     shim 在 `issue create` 成功後自動把新編號加進允許清單，所以清單不會漏掉受測物
     自己開的那些；
  3. cleanup 在 finally 內執行（等同 trap），關閉本輪建立的全部 issue，且**關閉前
     再驗一次該 issue 的內文首行是本輪的鍵**——harness 自己也不准關不是自己開的。

**痕跡**：每次執行會在 public repo 留下 2〜3 個**已關閉** issue 的永久編號（裁決 4，
PRE-1 的 #538 為既有先例）。label aidlc-sync-alert 若不存在會被本輪建立並**保留**
——它是機制正式運行時本來就需要的物件，刪掉它反而是多做一次破壞性動作。

covers（code-generation-plan.md Step 7 的 (a)〜(d)）：
    (a) 同鍵 notify 兩次 → 第二次 action=commented、REST 的 comments 為 1、
        標題 ×2、開啟中同鍵 issue 數為 1（**U-5 完成判準逐字**）
    (b) harness 手動再開一則同鍵 issue（模擬並行重複）→ notify →
        action=deduplicated、編號最小者保留、新者已關閉且 comment 含「重複」
    (c) resolve_if_open 帶**不存在的鍵** → no-op 且開啟中那則不動（R-3.2 的 live
        反例）；再帶該鍵 → 關閉
    (d) 清理並確認本輪 intent_id 的開啟中 issue 為空

規格正本見 run-stub-tests.py 的同名段落。
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
NOTIFY_SH = HERE / "notify.sh"
REPO_ROOT = HERE.parents[2]

BASH = os.environ.get("AIDLC_NOTIFY_BASH", "bash")
REAL_GH = shutil.which("gh") or "gh"

REPOSITORY = "opendiamonds/cloud-360"
LABEL = "aidlc-sync-alert"
TEST_PREFIX = "aidlc-sync-test-"
REASON = "ExternalError"
STAGE = "u5-live"

FAILURES: list[str] = []
CHECKS = 0
STATE: dict = {"created": [], "label_pre_existed": None}


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
# 防呆
# ==========================================================================

def assert_test_intent(intent: str) -> None:
    if not intent.startswith(TEST_PREFIX):
        print(f"REFUSE：intent_id '{intent}' 不以 {TEST_PREFIX} 開頭。"
              f"live 測試只准以測試前綴的鍵開 issue。exit 4。", file=sys.stderr)
        sys.exit(4)


def marker(intent: str, reason: str) -> str:
    return f"<!-- aidlc-alert: intent={intent} reason={reason} -->"


def title_of(intent: str, reason: str, n: int) -> str:
    return f"[aidlc-sync] {intent} / {reason} (×{n})"


# ==========================================================================
# gh shim：對受測物的破壞性呼叫做外部兜底
# ==========================================================================
# config.json = {"repo": ..., "real_gh": ..., "allow_file": ...}
# allow_file 是每行一個 issue 編號的允許清單；shim 在 issue create 成功後自動追加。
GH_SHIM = r'''#!/usr/bin/env python3
import json, os, pathlib, re, subprocess, sys

d = pathlib.Path(os.environ["AIDLC_LIVE_SHIM_DIR"])
cfg = json.loads((d / "config.json").read_text())
allow_file = pathlib.Path(cfg["allow_file"])
argv = sys.argv[1:]
hay = " ".join(argv)

with open(d / "calls.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps({"argv": argv}) + "\n")


def refuse(msg):
    sys.stderr.write("live-gh-shim REFUSE: " + msg + "\n")
    sys.exit(97)


def allowed():
    if not allow_file.exists():
        return set()
    return {int(x) for x in allow_file.read_text().split() if x.strip()}


if "--repo" in argv:
    got = argv[argv.index("--repo") + 1]
    if got != cfg["repo"]:
        refuse("--repo 是 %s，只准 %s" % (got, cfg["repo"]))

if argv[:2] in (["issue", "close"], ["issue", "comment"], ["issue", "edit"]):
    try:
        num = int(argv[2])
    except (IndexError, ValueError):
        refuse("破壞性／寫入子命令的目標編號解析不出來：" + hay)
    if num not in allowed():
        refuse("issue #%d 不在本輪建立的允許清單 %s 內，拒絕 %s"
               % (num, sorted(allowed()), " ".join(argv[:2])))

proc = subprocess.run([cfg["real_gh"]] + argv, capture_output=True, text=True)
sys.stdout.write(proc.stdout)
sys.stderr.write(proc.stderr)

if argv[:2] == ["issue", "create"] and proc.returncode == 0:
    m = re.search(r"/issues/(\d+)\s*$", proc.stdout.strip())
    if m:
        with open(allow_file, "a", encoding="utf-8") as f:
            f.write(m.group(1) + "\n")

sys.exit(proc.returncode)
'''


class Result:
    def __init__(self, proc, gh_output_file: pathlib.Path, shim_dir: pathlib.Path):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.gh_output = gh_output_file.read_text() if gh_output_file.exists() else ""
        self.outputs: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if "=" in line:
                name, _, value = line.partition("=")
                self.outputs[name] = value
        self.calls = []
        calls_file = shim_dir / "calls.jsonl"
        if calls_file.exists():
            for line in calls_file.read_text().splitlines():
                if line.strip():
                    self.calls.append(json.loads(line))

    def calls_matching(self, *subs: str) -> list[dict]:
        return [c for c in self.calls if all(s in " ".join(c["argv"]) for s in subs)]


def run_notify(operation: str, env: dict) -> Result:
    """所有 live 呼叫都在 gh shim 之下：shim 對每個破壞性呼叫斷言目標在允許清單內。"""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-notify-live-run-"))
    try:
        shim_dir = tmp / "shim"
        shim_dir.mkdir()
        (shim_dir / "config.json").write_text(json.dumps({
            "repo": REPOSITORY, "real_gh": REAL_GH, "allow_file": str(STATE["allow_file"]),
        }))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        exe = bin_dir / "gh"
        exe.write_text(GH_SHIM)
        exe.chmod(0o755)
        gh_output_file = tmp / "github_output"

        full_env = dict(os.environ)
        for key in list(full_env):
            if key.startswith("AIDLC_"):
                del full_env[key]
        full_env["GITHUB_REPOSITORY"] = REPOSITORY
        full_env.update(env)
        full_env["AIDLC_OPERATION"] = operation
        full_env["PATH"] = f"{bin_dir}:{full_env['PATH']}"
        full_env["AIDLC_LIVE_SHIM_DIR"] = str(shim_dir)
        full_env["GITHUB_OUTPUT"] = str(gh_output_file)

        proc = subprocess.run([BASH, str(NOTIFY_SH)], capture_output=True, text=True, env=full_env)
        r = Result(proc, gh_output_file, shim_dir)
        # shim 的 refuse 走 exit 97；notify.sh 會把它當成一次 gh 失敗而以 exit 1 收場，
        # 所以不能只看 r.rc——REFUSE 的字樣才是判準。
        if r.rc == 97 or "live-gh-shim REFUSE" in r.stderr:
            FAILURES.append(f"gh shim 拒絕了受測物的一次呼叫（這是防呆生效，代表實作違反了"
                            f"允許清單）：\n    {r.stderr.strip()[:500]}")
        return r
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ==========================================================================
# harness 自己的通道（真 gh，不經 shim；harness 的動作是明寫的，不是受測物）
# ==========================================================================

def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([REAL_GH, *args], capture_output=True, text=True)


def gh_json(path: str):
    proc = gh("api", path)
    if proc.returncode != 0:
        raise RuntimeError(f"harness gh api {path} 失敗：{proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout)


def issue_state(number: int) -> dict:
    return gh_json(f"repos/{REPOSITORY}/issues/{number}")


def open_alerts() -> list[dict]:
    proc = gh("issue", "list", "--repo", REPOSITORY, "--label", LABEL,
              "--state", "open", "--json", "number,title,body", "--limit", "200")
    if proc.returncode != 0:
        raise RuntimeError(f"harness gh issue list 失敗：{proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout)


def open_with_our_marker() -> list[dict]:
    mk = marker(STATE["intent"], REASON)
    return [it for it in open_alerts() if (it.get("body") or "").split("\n")[0].strip() == mk]


# --------------------------------------------------------------------------
# label 過濾的列舉是**最終一致**的（本站實測，見檔頭「本站實測推翻的一項上游主張」）
# --------------------------------------------------------------------------
# 下面兩個等待不是在掩蓋缺陷，是在**重現真實的輪次間隔並量出那個窗口**：
# U-6 是 push／PR 觸發、U-7 是每日排程，兩輪之間隔的是分鐘到小時，而本 runner 的
# 兩輪之間隔的是毫秒。不等的話，量到的是「六秒內連按兩次會怎樣」（答案：開出重複，
# 而那正是 R-2 第 4 步存在的理由，且 stub 已有 test_deduplicated_state_converges…
# 覆蓋），不是完成判準要問的「連續兩輪失敗之後，開啟中的通報 issue 是不是只有一則」。
#
# 每一次等待都**把實測秒數記進 STATE 並印在痕跡行**——這個數字本身就是本輪 live
# 測試的產出之一。

LIST_SETTLE_TIMEOUT = 90.0


def wait_until(label: str, predicate, timeout: float = LIST_SETTLE_TIMEOUT) -> float:
    """輪詢到 predicate() 為真為止，回傳耗時秒數。逾時即記一筆 failure（不是靜默放行）。"""
    t0 = time.time()
    while True:
        try:
            if predicate():
                elapsed = round(time.time() - t0, 2)
                STATE.setdefault("settle", []).append((label, elapsed))
                return elapsed
            ok_err = None
        except Exception as exc:
            ok_err = exc
        elapsed = time.time() - t0
        if elapsed > timeout:
            STATE.setdefault("settle", []).append((label, f">{timeout}"))
            FAILURES.append(f"等待「{label}」逾時（{timeout}s）"
                            + (f"，最後一次查詢擲出 {ok_err!r}" if ok_err else ""))
            return elapsed
        time.sleep(1.0)


def wait_listed(number: int) -> float:
    return wait_until(f"#{number} 出現在 label 列舉中",
                      lambda: number in [it["number"] for it in open_alerts()])


def wait_unlisted(number: int) -> float:
    return wait_until(f"#{number} 從 label 列舉中消失",
                      lambda: number not in [it["number"] for it in open_alerts()])


def remember(number: int) -> None:
    """把一個**本輪建立**的 issue 編號記進允許清單與清理清單。"""
    n = int(number)
    if n not in STATE["created"]:
        STATE["created"].append(n)
    with open(STATE["allow_file"], "a", encoding="utf-8") as f:
        f.write(f"{n}\n")


# ==========================================================================
# 步驟
# ==========================================================================

def step_preflight() -> None:
    """@purpose 記下 label 的執行前狀態（痕跡報告需要），並確認本輪的鍵在 repo 上是全新的——若已有殘留，後續每一條計數斷言都建立在別人的資料上，綠燈也沒有意義。
    @given 真實的 opendiamonds/cloud-360，本輪鍵以 UTC 時間戳為前綴故必為全新
    @step 讀 repo 的 label 清單 | 記下 aidlc-sync-alert 是否已存在（本輪不刪除它）
    @step 以本輪的機器可讀鍵過濾開啟中的通報 issue | 恰好 0 則
    @pass 起始狀態乾淨
    @api gh label list --repo --json name
    @api gh issue list --repo --label --state open --json number,title,body
    @story S-8
    """
    proc = gh("label", "list", "--repo", REPOSITORY, "--json", "name", "--limit", "200")
    if proc.returncode != 0:
        raise RuntimeError(f"harness gh label list 失敗：{proc.stderr.strip()[:300]}")
    names = [x["name"] for x in json.loads(proc.stdout)]
    STATE["label_pre_existed"] = LABEL in names
    check("preflight：本輪的鍵在 repo 上沒有既有的開啟中 issue", len(open_with_our_marker()), 0)


def step_a_two_rounds() -> None:
    """@purpose [ug:unit-of-work.md] 的 U-5 完成判準在**真實 GitHub** 上成立：同一個鍵連續失敗兩輪後，該鍵的開啟中通報 issue 數為 1 且 comment 數增加 1。stub 的同名案例是在我們自己寫的 shim 上成立的，issue 的生命週期只有真的打一次才算數。
    @given 全新的鍵、真實 repo
    @step 第一輪 notify | action=created，REST 讀回該 issue：state=open、標題 ×1、內文首行為機器可讀鍵、帶 label、comments=0
    @step 等 label 列舉看得到它（重現真實輪次間隔，並量出傳播延遲） | 有限時間內出現
    @step 第二輪 notify | action=commented、issue_number 與第一輪相同、count=2、零次 issue create
    @step 以 REST 讀回該 issue | comments=1（由 0 增加 1）、標題 ×2
    @step 以 label 列舉過濾本輪的鍵 | 開啟中 issue 數為 1
    @pass 以上全部成立
    @api gh issue create --repo --title --body --label
    @api gh issue comment --repo --body
    @api gh issue edit --repo --title
    @api GET /repos/{owner}/{repo}/issues/{number}
    @story S-8
    """
    env = {"AIDLC_INTENT_ID": STATE["intent"], "AIDLC_REASON_CODE": REASON,
           "AIDLC_STAGE": STAGE, "AIDLC_DETAIL": "live 第一輪：模擬看板寫入失敗"}
    r1 = run_notify("notify", env)
    check("(a) 第一輪 rc", r1.rc, 0)
    check("(a) 第一輪 action", r1.outputs.get("action"), "created")
    n1 = r1.outputs.get("issue_number")
    check_true("(a) 第一輪回傳 issue_number", bool(n1 and n1.isdigit()), r1.stdout + r1.stderr)
    if not (n1 and n1.isdigit()):
        raise RuntimeError("第一輪沒有拿到 issue 編號，後續步驟無法進行")
    remember(int(n1))
    STATE["primary"] = int(n1)

    created = issue_state(int(n1))
    check("(a) 新 issue 為 open", created["state"], "open")
    check("(a) 新 issue 標題為 ×1", created["title"], title_of(STATE["intent"], REASON, 1))
    check("(a) 新 issue 內文第一行是機器可讀鍵",
          (created["body"] or "").split("\n")[0].strip(), marker(STATE["intent"], REASON))
    check("(a) 新 issue 帶 label", [l["name"] for l in created["labels"]], [LABEL])
    check("(a) 第一輪的 comment 數為 0", created["comments"], 0)

    # 重現真實輪次間隔（見上方 wait_until 的註解）：等 label 列舉看得到 #n1 再跑第二輪。
    STATE["settle_create"] = wait_listed(int(n1))

    env2 = dict(env)
    env2["AIDLC_DETAIL"] = "live 第二輪：同一個鍵再度失敗"
    r2 = run_notify("notify", env2)
    check("(a) 第二輪 rc", r2.rc, 0)
    check("(a) 第二輪 action", r2.outputs.get("action"), "commented")
    check("(a) 第二輪落在同一則 issue", r2.outputs.get("issue_number"), n1)
    check("(a) 第二輪 count", r2.outputs.get("count"), "2")

    after = issue_state(int(n1))
    # ---- 完成判準逐字：開啟中同鍵 issue 數為 1，且 comment 數增加 1 ----
    check("完成判準：comment 數為 1（由 0 增加 1）", after["comments"], 1)
    check("完成判準：標題為 ×2", after["title"], title_of(STATE["intent"], REASON, 2))
    check("完成判準：開啟中同鍵 issue 數為 1", len(open_with_our_marker()), 1)
    check_true("(a) 第二輪沒有再開 issue",
               len(r2.calls_matching("issue create")) == 0, str(r2.calls))


def step_b_deduplicate() -> None:
    """@purpose 缺口 J-1（並行的兩個 run 各看到 0 筆而各開一則）在真實環境下的收斂：notify 命中多筆時取編號最小者追加、其餘關閉（R-2 第 4 步，[Q1=A]）。這條路徑修的是 ADR-A8 原本交給 resolve_if_open 的一條走不通的路——resolve_if_open 只在失敗不再發生時被呼叫，而重複正是在失敗持續時產生的。
    @given 步驟 (a) 留下的那則開啟中 issue
    @step harness 以 gh issue create 手動再開一則同鍵 issue（編號必然較大） | 開啟中同鍵變成 2 則
    @step 呼叫 notify | action=deduplicated、issue_number 為編號最小者、closed_numbers 為新開那則、closed=1
    @step 以 REST 讀回最舊者 | 仍為 open、comments=2、標題 ×3
    @step 以 REST 讀回新者及其 comments | state=closed，且 comment 含「重複」與 #<最舊>
    @step 等關閉傳播後重新列舉 | 開啟中同鍵回到 1 則
    @pass 以上全部成立
    @api gh issue create --repo --title --body --label
    @api gh issue close --repo --comment
    @api GET /repos/{owner}/{repo}/issues/{number}
    @api GET /repos/{owner}/{repo}/issues/{number}/comments
    @story S-8
    """
    body = (marker(STATE["intent"], REASON) +
            "\n\nlive 測試以手動方式製造的重複（模擬並行 run）。可直接關閉。\n")
    proc = gh("issue", "create", "--repo", REPOSITORY,
              "--title", title_of(STATE["intent"], REASON, 1),
              "--body", body, "--label", LABEL)
    if proc.returncode != 0:
        raise RuntimeError(f"harness 開重複 issue 失敗：{proc.stderr.strip()[:300]}")
    dup = int(proc.stdout.strip().rstrip("/").split("/")[-1])
    remember(dup)
    STATE["dup"] = dup
    check_true("(b) 手動重複的編號大於原本那則", dup > STATE["primary"],
               f"dup={dup} primary={STATE['primary']}")
    wait_listed(dup)
    check("(b) 製造重複後開啟中同鍵為 2 則", len(open_with_our_marker()), 2)

    env = {"AIDLC_INTENT_ID": STATE["intent"], "AIDLC_REASON_CODE": REASON,
           "AIDLC_STAGE": STAGE, "AIDLC_DETAIL": "live 第三輪：此時同鍵有兩則"}
    r = run_notify("notify", env)
    check("(b) rc", r.rc, 0)
    check("(b) action", r.outputs.get("action"), "deduplicated")
    check("(b) 保留編號最小者", r.outputs.get("issue_number"), str(STATE["primary"]))
    check("(b) closed_numbers", r.outputs.get("closed_numbers"), str(dup))
    check("(b) closed", r.outputs.get("closed"), "1")

    kept = issue_state(STATE["primary"])
    check("(b) 最舊者仍為 open", kept["state"], "open")
    check("(b) 最舊者 comment 數為 2", kept["comments"], 2)
    check("(b) 最舊者標題為 ×3", kept["title"], title_of(STATE["intent"], REASON, 3))

    closed = issue_state(dup)
    check("(b) 新者已關閉", closed["state"], "closed")
    comments = gh_json(f"repos/{REPOSITORY}/issues/{dup}/comments")
    joined = " ".join(c["body"] for c in comments)
    check_true("(b) 新者的關閉 comment 註明重複並指向最舊者",
               "重複" in joined and f"#{STATE['primary']}" in joined, joined[:400])
    wait_unlisted(dup)
    check("(b) 收斂後開啟中同鍵為 1 則", len(open_with_our_marker()), 1)


def step_c_resolve() -> None:
    """@purpose resolve_if_open 在真實環境下的兩面：鍵不在 keys 內的通報 issue **一律不動**（R-3.2 的 live 反例——此時 repo 上確實有一則開啟中的通報 issue，若實作把 keys 當裝飾就會關掉它），以及批次仍只發一次列舉查詢（[Q2=A]）。
    @given 步驟 (b) 之後仍開啟的那則通報 issue
    @step 以一個**不存在**的鍵呼叫 resolve_if_open（並顯式給 alert_repo） | rc=0、closed=0、零次 issue close
    @step 以 REST 讀回本輪那則 | 仍為 open（沒有被誤關）
    @step 以「本輪的鍵 ＋ 那個不存在的鍵」呼叫 resolve_if_open | closed=1、closed_numbers 為本輪那則、issue list 恰好一次
    @step 以 REST 讀回它與其 comments | state=closed，comment 含「本輪未再發生」
    @pass 以上全部成立，且等傳播後開啟中同鍵為 0 則
    @api gh issue list --repo --label --state open --json number,body
    @api gh issue close --repo --comment
    @api GET /repos/{owner}/{repo}/issues/{number}
    @api GET /repos/{owner}/{repo}/issues/{number}/comments
    @story S-8
    """
    absent_key = f"{STATE['intent']}-absent/Failed"
    r0 = run_notify("resolve_if_open", {
        "AIDLC_KEYS": absent_key,
        "AIDLC_ALERT_REPO": REPOSITORY,   # 同時驗 alert_repo 的顯式路徑
    })
    check("(c) 不存在的鍵：rc", r0.rc, 0)
    check("(c) 不存在的鍵：closed", r0.outputs.get("closed"), "0")
    check("(c) 不存在的鍵：零次 issue close", len(r0.calls_matching("issue close")), 0)
    check("R-3.2 live：本輪那則仍為 open", issue_state(STATE["primary"])["state"], "open")

    r1 = run_notify("resolve_if_open", {
        "AIDLC_KEYS": f"{STATE['intent']}/{REASON}\n{absent_key}\n",
    })
    check("(c) 本輪的鍵：rc", r1.rc, 0)
    check("(c) 本輪的鍵：closed", r1.outputs.get("closed"), "1")
    check("(c) 本輪的鍵：closed_numbers", r1.outputs.get("closed_numbers"), str(STATE["primary"]))
    check("(c) 本輪的鍵：issue list 恰好一次", len(r1.calls_matching("issue list")), 1)

    resolved = issue_state(STATE["primary"])
    check("(c) 該 issue 已關閉", resolved["state"], "closed")
    comments = gh_json(f"repos/{REPOSITORY}/issues/{STATE['primary']}/comments")
    joined = " ".join(c["body"] for c in comments)
    check_true("(c) 關閉 comment 說明本輪未再發生", "本輪未再發生" in joined, joined[-400:])
    wait_unlisted(STATE["primary"])
    check("(c) 關閉後開啟中同鍵為 0 則", len(open_with_our_marker()), 0)


def cleanup() -> None:
    """@purpose (d) 清理：關閉本輪建立的全部 issue（在 finally 內執行，等同 trap，中途失敗也會跑），並確認本輪 intent_id 在開啟中的通報 issue 裡完全不存在。關閉前**再驗一次**該 issue 的內文首行是本輪的鍵——harness 自己也不准關不是自己開的（SEC-1 對受測物與對 harness 是同一條規則）。
    @given STATE["created"] 記錄的本輪 issue 編號
    @step 逐一以 REST 讀回 | 已關閉者跳過；內文首行不是本輪鍵者拒絕關閉並記為 failure
    @step 對仍開啟且確認是本輪的 | gh issue close 並留一則說明 comment
    @step 以 label 列舉過濾本輪 intent_id | 空清單
    @pass 無殘留、無拒絕項
    @api gh issue close --repo --comment
    @api gh issue list --repo --label --state open --json number,title,body
    @api GET /repos/{owner}/{repo}/issues/{number}
    @story S-8
    """
    mk = marker(STATE["intent"], REASON)
    leftovers = []
    for n in STATE["created"]:
        try:
            it = issue_state(n)
        except Exception as exc:
            FAILURES.append(f"cleanup：讀 issue #{n} 失敗：{exc!r}")
            leftovers.append(n)
            continue
        if it["state"] == "closed":
            continue
        first = (it.get("body") or "").split("\n")[0].strip()
        if first != mk:
            FAILURES.append(f"cleanup REFUSE：issue #{n} 的內文首行不是本輪的鍵，不關閉。"
                            f"first={first!r}")
            leftovers.append(n)
            continue
        proc = gh("issue", "close", str(n), "--repo", REPOSITORY,
                  "--comment", "live 測試結束，關閉本輪建立的測試 issue。")
        if proc.returncode != 0:
            FAILURES.append(f"cleanup：關閉 issue #{n} 失敗：{proc.stderr.strip()[:300]}")
            leftovers.append(n)
    STATE["leftovers"] = leftovers

    # (d) 最終確認：本輪 intent_id 在開啟中的通報 issue 裡完全不存在。
    try:
        remaining = [it["number"] for it in open_alerts()
                     if STATE["intent"] in (it.get("title") or "") + (it.get("body") or "")]
    except Exception as exc:
        FAILURES.append(f"cleanup：最終確認查詢失敗：{exc!r}")
        remaining = ["<查詢失敗>"]
    check("(d) 本輪 intent_id 的開啟中通報 issue 為空", remaining, [])


STEPS = [step_preflight, step_a_two_rounds, step_b_deduplicate, step_c_resolve]


def main() -> int:
    if not NOTIFY_SH.exists():
        print(f"找不到 {NOTIFY_SH}", file=sys.stderr)
        return 2
    if shutil.which("jq") is None:
        print("找不到 jq（notify.sh 的硬依賴）", file=sys.stderr)
        return 2

    # ---- 憑證與權限：拿不到就明確 skip（非零），不靜默 ----
    if shutil.which("gh") is None:
        print("SKIP：找不到 gh——live 層未執行。exit 3。", file=sys.stderr)
        return 3
    tok = gh("auth", "token")
    if tok.returncode != 0 or not tok.stdout.strip():
        print("SKIP：gh auth token 取不到憑證——live 層未執行，U-5 完成判準未被本次驗證。exit 3。",
              file=sys.stderr)
        return 3
    perms = gh("api", f"repos/{REPOSITORY}", "-q", ".permissions.push")
    if perms.returncode != 0 or perms.stdout.strip() != "true":
        print(f"SKIP：憑證對 {REPOSITORY} 無寫入權——live 層未執行。exit 3。", file=sys.stderr)
        return 3

    # ---- 防呆：目標必須是這個 repo，且本機 origin 就指向它 ----
    origin = subprocess.run(["git", "remote", "get-url", "origin"], cwd=REPO_ROOT,
                            capture_output=True, text=True)
    if origin.returncode != 0 or REPOSITORY not in origin.stdout:
        print(f"REFUSE：本 repo 的 origin（{origin.stdout.strip()}）不是 {REPOSITORY}。exit 4。",
              file=sys.stderr)
        return 4

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    STATE["intent"] = f"{TEST_PREFIX}{ts}"
    assert_test_intent(STATE["intent"])
    root = pathlib.Path(tempfile.mkdtemp(prefix="aidlc-notify-live-"))
    STATE["root"] = root
    STATE["allow_file"] = root / "allowed-issues.txt"
    STATE["allow_file"].write_text("")

    print(f"live 對象：{REPOSITORY}，label {LABEL}，本輪鍵 {STATE['intent']} / {REASON}")
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
        shutil.rmtree(root, ignore_errors=True)

    print(f"\n{len(STEPS)} steps, {CHECKS} checks, {len(FAILURES)} failures")
    print(f"痕跡：本輪建立的 issue = {STATE['created']}；未能關閉的 = "
          f"{STATE.get('leftovers', '?')}；label {LABEL} 執行前已存在 = "
          f"{STATE['label_pre_existed']}（本輪不刪除它）")
    print("實測的 label 列舉傳播延遲（秒）：" +
          "；".join(f"{k}={v}" for k, v in STATE.get("settle", [])) or "（無）")
    if FAILURES:
        print("\n---- failures ----")
        for f in FAILURES:
            print(f"* {f}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
