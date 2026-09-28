#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U-9 的行為測試：把三支檢查器與 workflow 的守衛**實際跑起來**，斷言它們的判定。

為什麼是行為測試而不是文字斷言
------------------------------
本 intent 反覆記載的同一個失誤是「**斷言看起來在守、實際守不到**」。U-10a 的
`check-ci-yml.py` 被 reviewer 用「不動任何字串、只改邏輯方向」攻破兩次，收斂方式不是再多
加幾條文字斷言（那是同一個錯誤再犯一次），而是換一種東西：**不要斷言腳本長什麼樣，直接
執行它，斷言它對給定輸入吐出什麼判定**。

本檔因此對每一條檢查都**合成一棵暫存 repo 樹**（把違規真的做出來），跑檢查器，斷言 rc
與訊息內容。三支檢查器的 `--repo-root` 參數就是為了這件事存在的。

每條測試都有**前提斷言**
----------------------
先確認要製造的情境真的發生了，再斷言後果。U-6 曾經因為 stub 計畫的鍵名寫錯（用 `"rc"`
而 stub 只認 `"exit"`）讓整條測試在空前提上恆真通過。這裡的做法是：每個「應該紅」的測試
都配一個 baseline（同一棵樹、不做那個突變）先斷言它是綠的——沒有綠的對照組，紅就不能歸因
於那個突變。

用法
----
    python3 .github/actions/aidlc-sync-selftest/run-selftest-tests.py
    python3 .github/actions/aidlc-sync-selftest/run-selftest-tests.py -k paths   # 只跑名稱含 paths 的

非零 exit 表失敗。相依：PyYAML、bash。
"""

from __future__ import annotations

import argparse
import ast
import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ACTIONS = REPO_ROOT / ".github" / "actions"

CHECK_AGENTIC = HERE / "check-agentic-steps.py"
CHECK_PATHS = HERE / "check-paths-relations.py"
RUN_FIXTURES = HERE / "run-selftest-fixtures.py"
SELFTEST_YML = WORKFLOWS / "aidlc-sync-selftest.yml"

FIXTURE_REL = "aidlc/spaces/default/intents/260822-gh-projects-sync/.test-fixtures"

# U-10b 要改的四支 gh-aw。與 check-paths-relations.py 同一份清單——那裡是正本，這裡 import
# 它而不是抄第二份。
sys.path.insert(0, str(HERE))
import importlib.util as _ilu


def _load(path, name):
    spec = _ilu.spec_from_file_location(name, str(path))
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_cpr = _load(CHECK_PATHS, "aidlc_selftest_cpr")
GH_AW_CARRIERS = _cpr.GH_AW_CARRIERS
_cas = _load(CHECK_AGENTIC, "aidlc_selftest_cas")
ASSERT_PREFIX = _cas.ASSERT_PREFIX
EXTERNAL_PREFIX = _cas.EXTERNAL_PREFIX

# 被禁字樣按名字從資料檔取，**本檔不寫字面值**（reviewer iteration 2 的 M-2）。
# 本檔要構造違規樹才能證明檢查器真的會紅，但它自己也在 R-1.2 的掃描面上——寫字面值等於
# 需要一個整檔豁免，而那個豁免正是 M-2 判為 Major 的東西。
#
# 為什麼不是把字串拆開寫（`c = "cop"; d = "ilot"`）：拆字正是本檢查宣告擋不住的那種刻意
# 混淆，在自己的測試裡示範它會讓「這是規避手法」這句話失去說服力。具名查表沒有這個問題。
TOK = _cas.NAMED_TOKENS
AGENT_CLI = TOK["agent_cli"]
AGENT_ACTION_REPO = TOK["agent_action_repo"]
AGENT_ACTION_ORG = TOK["agent_action_org"]
AGENT_ACTION_SETUP = TOK["agent_action_setup"]
AGENT_COMPILE_CMD = TOK["agent_compile_cmd"]

FAILURES: list[str] = []
CHECKS = 0

# 同步回寫的寫入 glob。**不寫死**——從 U-4 的 record.sh 推導，與受測的檢查器同一個來源。
WRITE_GLOB, _ = _cpr.derive_write_glob(REPO_ROOT)


# ==========================================================================
# 斷言工具
# ==========================================================================
def check(label, actual, expected):
    global CHECKS
    CHECKS += 1
    if actual != expected:
        FAILURES.append("%s\n    expected: %r\n    actual:   %r" % (label, expected, actual))


def check_true(label, cond, detail=""):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append("%s%s" % (label, ("\n    " + detail) if detail else ""))


def check_in(label, needle, haystack):
    global CHECKS
    CHECKS += 1
    if needle not in haystack:
        FAILURES.append(
            "%s\n    expected 輸出含: %r\n    actual 輸出:\n%s"
            % (label, needle, _indent(haystack))
        )


def check_not_in(label, needle, haystack):
    global CHECKS
    CHECKS += 1
    if needle in haystack:
        FAILURES.append(
            "%s\n    expected 輸出**不**含: %r\n    actual 輸出:\n%s"
            % (label, needle, _indent(haystack))
        )


def _indent(text):
    return "\n".join("      " + line for line in text.splitlines()[:40])


class Run:
    """一次檢查器執行的結果。"""

    def __init__(self, proc):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.all = proc.stdout + proc.stderr

    def failed_ids(self):
        """報告中判為 [失敗] 的檢查代號。"""
        return re.findall(r"^\[失敗\] (\S+)", self.stdout, re.M)


# 逾時上界（F6，iteration 3）。理由與 run-selftest-fixtures.py 那份相同：job 的
# `timeout-minutes: 10` 是有效上界，但它只說得出「job timed out」，說不出是哪一支掛住。
# 這裡的每一個呼叫都是「跑一支檢查器／一段抽出來的腳本」，正常路徑是秒級。
CHECKER_TIMEOUT_S = 180
SHELL_TIMEOUT_S = 60


class _Timeout:
    """逾時的替身結果：讓呼叫端照常拿到 rc／stdout，而不是在半途拋例外。

    逾時走的是 `EXIT_EXTERNAL`（2）而不是斷言失敗（1）——`reliability-requirements.md`
    的三值退出慣例：外部錯誤與斷言失敗必須在第一行就分得出來。
    """

    def __init__(self, what, limit):
        self.returncode = _cas.EXIT_EXTERNAL
        self.stdout = ""
        self.stderr = ("%s %s 超過 %d 秒沒有結束——**它掛住了，不是斷言失敗**。"
                       % (EXTERNAL_PREFIX, what, limit))


def run_checker(script, repo_root, *args):
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--repo-root", str(repo_root), *args],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=CHECKER_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        proc = _Timeout("檢查器 %s" % Path(script).name, CHECKER_TIMEOUT_S)
    return Run(proc)


# ==========================================================================
# 合成 repo 樹
# ==========================================================================
def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


CLEAN_SYNC_WF = """name: Synthetic sync workflow
# 註解裡刻意提到 %(cli)s、%(repo)s 與 .lock.yml —— 這幾支 workflow 的真實註解正是在
# 解釋「為什麼不用它們」。掃文字的檢查器會把這幾行判成違規，那不是嚴格而是壞掉。
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  deterministic:
    name: Deterministic mapping
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Map
        run: |
          # 這一行是註解，裡面寫 %(cli)s 與 %(compile)s 與 x.lock.yml
          echo "純 Actions 的決定性步驟"
""" % {"cli": AGENT_CLI, "repo": AGENT_ACTION_REPO, "compile": AGENT_COMPILE_CMD}

SELFTEST_WF_TEMPLATE = """name: Synthetic selftest
on:
  pull_request:
    paths:
%(paths)s
  workflow_dispatch:
permissions:
  contents: read
jobs:
  fixtures:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo stage-1
"""

# 本單元的觸發 allowlist。**九條承載體路徑由 GH_AW_CARRIERS 產生，不手抄第二份**——
# reviewer iteration 1 的 F7：A-6 斷言的九個檔案（ci.yml ＋ 四支 gh-aw 的 .md／.lock.yml）
# 一個都不在原本的 allowlist 內，於是 U-10b 上線後任何人把 paths-ignore 拿掉都不會觸發
# U-9。真實 workflow 的那份是手寫的 YAML，兩者的一致性由 check-paths-relations.py 的
# COVERAGE-1 斷言（它同樣從 GH_AW_CARRIERS 產生要求清單）。
CARRIER_PATHS = (".github/workflows/ci.yml",) + tuple(
    ".github/workflows/%s.%s" % (name, ext)
    for name in GH_AW_CARRIERS for ext in ("md", "lock.yml")
)

DEFAULT_SELFTEST_PATHS = (
    ".github/workflows/aidlc-sync-*.yml",
    ".github/actions/aidlc-sync-*/**",
    "aidlc/spaces/*/intents/*/.test-fixtures/**",
) + CARRIER_PATHS


def synth_workflows(root: Path, *, logical=("forward", "reconcile", "reverse", "selftest"),
                    selftest_paths=DEFAULT_SELFTEST_PATHS) -> None:
    """四個邏輯 workflow 的乾淨版本。selftest 那支帶 allowlist（A-6 關係 2 要讀它）。"""
    for name in logical:
        if name == "selftest":
            body = SELFTEST_WF_TEMPLATE % {
                "paths": "\n".join("      - '%s'" % p for p in selftest_paths)
            }
        else:
            body = CLEAN_SYNC_WF
        write(root / ".github" / "workflows" / ("aidlc-sync-%s.yml" % name), body)


# 合成 lock 首行要寫的 compiler_version。**刻意寫死，不從 check-paths-relations.py 的
# PINNED_COMPILER_VERSION 推導**：從那裡推導的話，有人改了那個常數，合成樹會跟著改，
# 兩邊一起漂移而 baseline 照樣綠。寫死之後，改常數會讓 baseline 紅——那正是我們要的
# 提醒（與下方 EXPECTED_CARRIERS 是同一條紀律）。
# 2026-09-06：釘值隨 `ut` 的 PR #532 升為 v0.86.2，本常數同步改為同值（刻意的兩行 diff）。
SYNTH_LOCK_COMPILER = "v0.86.2"


def synth_carriers(root: Path, *, ci_ignore=True, md_ignore=True, lock_ignore=True,
                   skip_carrier=None, ci_extra_ignore=(),
                   lock_compiler=SYNTH_LOCK_COMPILER) -> None:
    """五個 paths-ignore 承載體。skip_carrier 指定的那一支不加排除（其餘照常）。

    `ci_extra_ignore` 讓測試把額外的 glob 塞進 ci.yml 的 paths-ignore——F3 的迴歸就是靠
    它把本單元 allowlist 的樣式逐字加進排除集合。
    """
    ci_globs = ([WRITE_GLOB] if ci_ignore else []) + list(ci_extra_ignore)
    write(root / ".github" / "workflows" / "ci.yml",
          "name: CI\non:\n  push:\n%s  pull_request:\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ci\n"
          % ("    paths-ignore:\n%s" % "".join("      - '%s'\n" % g for g in ci_globs)
             if ci_globs else ""))
    for name in GH_AW_CARRIERS:
        want_md = md_ignore and name != skip_carrier
        want_lock = lock_ignore and name != skip_carrier
        write(root / ".github" / "workflows" / ("%s.md" % name),
              "---\ndescription: synthetic\non:\n  pull_request:\n    types: [opened]\n%sengine: %s\n---\n\n# body\n"
              % ("    paths-ignore:\n      - '%s'\n" % WRITE_GLOB if want_md else "",
                 AGENT_CLI))
        # 首行的 metadata 註解是真實 lock 的形狀，COMPILER: 檢查讀的就是它。前綴按名字
        # 到 agentic-tokens.json 取（本檔也在掃描面上，不能寫字面值）。
        meta = '%s{"schema_version":"v4","compiler_version":"%s"}\n' % (
            _cas.NAMED_TOKENS["lock_metadata_prefix"], lock_compiler)
        write(root / ".github" / "workflows" / ("%s.lock.yml" % name),
              meta
              + "name: %s\non:\n  pull_request:\n    types: [opened]\n%sjobs:\n  agent:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo agent\n"
              % (name, "    paths-ignore:\n      - '%s'\n" % WRITE_GLOB if want_lock else ""))


def synth_deploy_yml(root: Path) -> None:
    """`deploy.yml` 的觸發形狀。

    PR-TRIGGER-1 釘住的集合含它（`types: [closed], branches: [ut]`、**無 paths**），
    所以合成樹少了它，基準線會以「少掉的」那一側紅——那是 fixture 不完整，不是 repo
    違規。只複製 `on:` 的形狀，不複製 job 本體：本檢查看的只有觸發設定。
    """
    write(root / ".github" / "workflows" / "deploy.yml",
          "name: Deploy\non:\n  pull_request:\n    types: [closed]\n    branches: [ut]\n"
          "  workflow_dispatch:\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
          "    steps:\n      - run: echo deploy\n")


def synth_forward_pr_trigger(root: Path) -> None:
    """把合成的 `aidlc-sync-forward.yml` 換成帶 `on: pull_request`（無 paths）的形狀。

    `CLEAN_SYNC_WF` 只宣告 `workflow_dispatch`，對 R-1.2 的代理式檢查夠用，但 PR-TRIGGER-1
    看的是觸發設定——真實的 forward 薄外層是 `on.pull_request` 無 paths、無 branches
    （U-10b 的 MAJOR-4），少了這一點，基準線會以「少掉的」那一側紅。

    **只改 `on:`，不動 `CLEAN_SYNC_WF` 本身**——那個常數被代理式那一族的測試共用。
    """
    write(root / ".github" / "workflows" / "aidlc-sync-forward.yml",
          "name: Forward sync\non:\n  push:\n  pull_request:\n    types: [opened, synchronize, closed]\n"
          "jobs:\n  forward:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo forward\n")


def synth_record_sh(root: Path, *, real=True, broken=False) -> None:
    """U-4 的 record.sh。A-6 的 glob 從它推導，所以合成樹一定要有一份。"""
    dst = root / ".github" / "actions" / "aidlc-sync-record" / "record.sh"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if broken:
        # 常數還在但驗證 regex 不見了 —— 推導不出 glob。
        dst.write_text('#!/usr/bin/env bash\nSTATE_FILE_NAME="sync-state.json"\nSYNC_MARKER="[aidlc-sync]"\n',
                       encoding="utf-8")
    elif real:
        shutil.copy2(ACTIONS / "aidlc-sync-record" / "record.sh", dst)


def synth_ci_guard(root: Path) -> None:
    """A-6 的 glob 推導 import 這一支。合成樹放的是**真實檔案的複本**，不是另一份實作。"""
    dst = root / ".github" / "actions" / "aidlc-sync-ci-guard" / "check-ci-yml.py"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ACTIONS / "aidlc-sync-ci-guard" / "check-ci-yml.py", dst)


def synth_paths_repo(root: Path, **kw) -> Path:
    synth_workflows(root, selftest_paths=kw.pop("selftest_paths", DEFAULT_SELFTEST_PATHS))
    synth_record_sh(root, broken=kw.pop("broken_record", False))
    synth_ci_guard(root)
    synth_deploy_yml(root)
    synth_forward_pr_trigger(root)
    synth_carriers(root, **kw)
    return root


# ==========================================================================
# R-1.2：check-agentic-steps.py 的行為
# ==========================================================================
def test_agentic_baseline_is_green() -> None:
    """@purpose **對照組**：四個邏輯 workflow 齊備、無代理式步驟、註解裡照樣提到 gh-aw／copilot／.lock.yml ⇒ 綠。沒有這一條，後面每一條「應該紅」都無法歸因於它自己製造的那個突變。
    @given 合成樹只有乾淨的四支 aidlc-sync-*.yml
    @step 跑 check-agentic-steps.py | rc=0
    @pass 註解中的關鍵字**不會**造成假紅燈（這是 MARKER-1 第一版的教訓）
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        r = run_checker(CHECK_AGENTIC, root)
        check("baseline rc", r.rc, 0)
        check_true("baseline 前提：四支都被列舉到",
                   all(("aidlc-sync-%s.yml" % n) in r.stdout for n in
                       ("forward", "reconcile", "reverse", "selftest")), r.stdout)
        check_not_in("baseline 不得因為註解提到代理式字樣就紅", "[失敗]", r.stdout)


def test_agentic_step_in_a_deterministic_job_is_red() -> None:
    """@purpose **必測 #1**：某支 workflow 的決定性 job 被塞進代理式步驟 ⇒ 紅，且訊息指出是哪一支、哪一個 job。這是本單元存在的理由。
    @given 合成樹的 aidlc-sync-forward.yml 多一個 uses: github/gh-aw-actions/setup 的步驟
    @step 跑檢查器 | rc=1 且失敗代號為 USES-1
    @step 讀訊息 | 含檔名與 job 名
    @pass 「有人把判定搬進 agent step」會被機械攔下，不是靠 code review
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        target = root / ".github" / "workflows" / "aidlc-sync-forward.yml"
        target.write_text(
            CLEAN_SYNC_WF.replace(
                "      - name: Map\n",
                "      - name: Ask the agent\n"
                + "        uses: %s@ba6380cc6e5be5d21677bebe04d52fb48e3abec7\n"
                % AGENT_ACTION_SETUP
                + "      - name: Map\n"),
            encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check_true("前提：突變真的寫進去了",
                   AGENT_ACTION_SETUP in target.read_text(encoding="utf-8"))
        check("rc", r.rc, 1)
        check_true("失敗代號含 USES-1", any(i.startswith("USES-1") for i in r.failed_ids()),
                   str(r.failed_ids()))
        check_in("訊息指出是哪一支", "aidlc-sync-forward.yml", r.stdout)
        check_in("訊息指出是哪一個 job", "job deterministic", r.stdout)
        check_in("訊息說得出它命中已知代理式承載", AGENT_ACTION_REPO, r.stdout)
        check_in("第一行可分辨為斷言失敗", ASSERT_PREFIX, r.stderr)


def test_agentic_engine_key_is_red() -> None:
    """@purpose gh-aw 的 `engine:` frontmatter 鍵出現在 .yml 頂層 ⇒ 紅。改承載形式最省事的手法就是把 md 的 frontmatter 直接搬過來。
    @given 合成樹的 aidlc-sync-reverse.yml 頂層多一行 engine: copilot
    @step 跑檢查器 | rc=1 且失敗代號含 ENGINE-1
    @pass 承載形式的變更不會靜默通過
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        target = root / ".github" / "workflows" / "aidlc-sync-reverse.yml"
        target.write_text("engine: %s\n" % AGENT_CLI + CLEAN_SYNC_WF, encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_true("失敗代號含 ENGINE-1", any(i.startswith("ENGINE-1") for i in r.failed_ids()),
                   str(r.failed_ids()))


def test_a_lock_yml_among_the_sync_workflows_is_red() -> None:
    """@purpose **必測 #2（上半）· N:C-3 的釘子**：workflows 目錄出現 aidlc-sync-x.lock.yml ⇒ 紅。檢查器**不得因為它存在就轉綠**（那是「改檢 .lock.yml」的實作會有的行為）。
    @given 乾淨的四支 ＋ 一份無害的 aidlc-sync-x.lock.yml
    @step 跑檢查器 | rc=1 且失敗代號含 LOCK-1
    @pass 有人把實作改回 .lock.yml 時這一條會紅
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        lock = root / ".github" / "workflows" / "aidlc-sync-x.lock.yml"
        lock.write_text(CLEAN_SYNC_WF, encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check_true("前提：假的 lock 真的在那裡", lock.is_file())
        check("rc", r.rc, 1)
        check_true("失敗代號含 LOCK-1", "LOCK-1" in r.failed_ids(), str(r.failed_ids()))


def test_the_check_reads_the_yml_not_the_lock() -> None:
    """@purpose **必測 #2（下半）· N:C-3 的釘子**：違規寫在 `.yml` 而 `.lock.yml` 是乾淨的 ⇒ 仍然紅，且紅的是 `.yml` 那一項。一個「檢 .lock.yml」的實作在這棵樹上只會看到乾淨的 lock。
    @given aidlc-sync-forward.yml 有代理式步驟；同名的 aidlc-sync-forward.lock.yml 乾淨
    @step 跑檢查器 | 失敗代號同時含 USES-1（來自 .yml）與 LOCK-1
    @step 讀 USES-1 的訊息 | 指的是 aidlc-sync-forward.yml 而不是 .lock.yml
    @pass 檢查對象確實是原始檔
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        yml = root / ".github" / "workflows" / "aidlc-sync-forward.yml"
        yml.write_text(
            CLEAN_SYNC_WF.replace(
                "      - name: Map\n",
                "      - name: Ask the agent\n        uses: githubnext/agent-action@v1\n      - name: Map\n"),
            encoding="utf-8")
        (root / ".github" / "workflows" / "aidlc-sync-forward.lock.yml").write_text(
            CLEAN_SYNC_WF, encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        uses_ids = [i for i in r.failed_ids() if i.startswith("USES-1")]
        check_true("有一項 USES-1 失敗（來自 .yml）", bool(uses_ids), str(r.failed_ids()))
        check_true("USES-1 指的是 .yml 不是 .lock.yml",
                   any("aidlc-sync-forward.yml：" in line for line in r.stdout.splitlines()
                       if "USES-1" in line) or "aidlc-sync-forward.yml：" in r.stdout,
                   r.stdout)


def test_missing_logical_workflow_is_red() -> None:
    """@purpose **必測 #3**：四個邏輯名稱缺一 ⇒ 紅。只靠 glob 列舉的檢查在某支被刪掉時會少檢一支而且全綠。
    @given 合成樹只有 forward／reconcile／selftest 三支
    @step 跑檢查器 | rc=1 且失敗代號含 LOGICAL-1，訊息指名缺的是 reverse
    @pass 「靜默地少檢一支」不可能發生
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root, logical=("forward", "reconcile", "selftest"))
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_true("失敗代號含 LOGICAL-1", "LOGICAL-1" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息指名缺的是哪一支", "aidlc-sync-reverse", r.stdout)


def test_impl_suffix_is_not_a_fifth_logical_workflow() -> None:
    """@purpose ADR-A10 的兩檔拆分（`-impl`）不得被當成第五個邏輯 workflow，否則加一支 impl 就會讓 LOGICAL-1 誤判。
    @given 合成樹的四支 ＋ 一支 aidlc-sync-forward-impl.yml
    @step 跑檢查器 | rc=0
    @pass 檔數與邏輯數解耦
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        (root / ".github" / "workflows" / "aidlc-sync-forward-impl.yml").write_text(
            CLEAN_SYNC_WF, encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 0)


def test_unknown_third_party_action_is_red() -> None:
    """@purpose 允許清單而非禁止清單：一個名字裡沒有任何代理式字樣的第三方 action 同樣要紅。禁止清單只擋得住它認得的名字。
    @given aidlc-sync-reconcile.yml 用了 someorg/some-action@v3
    @step 跑檢查器 | rc=1 且訊息說明「不在允許清單內」
    @pass 未來新增的 agent action 不需要本檔先認得它
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        (root / ".github" / "workflows" / "aidlc-sync-reconcile.yml").write_text(
            CLEAN_SYNC_WF.replace("      - uses: actions/checkout@v4\n",
                                  "      - uses: someorg/some-action@v3\n"),
            encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_in("訊息說明是允許清單擋的", "不在允許清單內", r.stdout)


def test_agentic_cli_in_a_run_script_is_red() -> None:
    """@purpose 代理式呼叫也可能寫在 `run:` 裡而不是 `uses:`。**且它必須逃不過註解剝除**——寫在真正會執行的位置才算。
    @given run: 腳本裡有一行真的執行 `copilot -p ...`（不是註解）
    @step 跑檢查器 | rc=1 且失敗代號含 RUN-1
    @pass 換一種承載寫法達成同樣的事，一樣被攔
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        (root / ".github" / "workflows" / "aidlc-sync-selftest.yml").write_text(
            SELFTEST_WF_TEMPLATE % {"paths": "\n".join("      - '%s'" % p for p in DEFAULT_SELFTEST_PATHS)}
            + "      - run: |\n          %s -p \"判斷這個 intent 該對應哪個 Status\"\n" % AGENT_CLI,
            encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_true("失敗代號含 RUN-1", any(i.startswith("RUN-1") for i in r.failed_ids()),
                   str(r.failed_ids()))


def test_missing_workflows_dir_is_an_external_error_not_a_pass() -> None:
    """@purpose fail closed：workflow 目錄不存在時**不得靜默通過**——那會是一個對空集合成立的斷言。且它是「外部錯誤」而非「斷言失敗」，第一行要分得出來。
    @given 空的暫存樹
    @step 跑檢查器 | rc=2 且 stderr 第一行是 EXTERNAL-ERROR:
    @pass 兩類紅燈可分辨（reliability-requirements.md）
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        r = run_checker(CHECK_AGENTIC, Path(td))
        check("rc", r.rc, 2)
        check_true("stderr 第一行是外部錯誤",
                   r.stderr.splitlines()[0].startswith(EXTERNAL_PREFIX) if r.stderr else False,
                   r.stderr)


def test_unparsable_workflow_is_an_external_error() -> None:
    """@purpose YAML 解析不了時 fail closed，且歸類為外部錯誤。
    @given 其中一支 workflow 是壞掉的 YAML
    @step 跑檢查器 | rc=2、stderr 第一行 EXTERNAL-ERROR:
    @pass 解析失敗不會被當成「沒有違規」
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        (root / ".github" / "workflows" / "aidlc-sync-reverse.yml").write_text(
            "name: broken\non:\n  - [unclosed\n", encoding="utf-8")
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 2)
        check_in("第一行可分辨為外部錯誤", EXTERNAL_PREFIX, r.stderr)


# ==========================================================================
# R-1.2 的第二與第三個掃描面：composite action 與它們的腳本
#
# reviewer iteration 1 的 F1（Critical）：`scan()` 原本只 glob
# `.github/workflows/aidlc-sync-*.yml`，於是同一個 repo 裡的**五份 composite action**
# 從頭到尾沒被開過。它實測構造了兩個繞過，兩個都 rc=0、「0 失敗」：
#
#   (a) `uses: githubnext/gh-aw@v1` ＋ `run: copilot --prompt "decide the Status"`
#       藏進 `.github/actions/aidlc-sync-map/action.yml`
#   (b) 判定搬進 `map.sh`：`status="$(copilot -p "which Status?")"`
#
# 而三支 `*-impl.yml` 的決定性邏輯**全部**在 `.sh` 檔內——本單元原本檢的那一層，剛好是
# 唯一沒有放判定邏輯的一層。
# ==========================================================================
CLEAN_ACTION_YML = """name: Synthetic composite action
description: >-
  決定性的映射，零判斷。這段說明刻意提到 %(repo)s 與 %(cli)s 與 .lock.yml——
  真實的 action.yml 說明段也在解釋「為什麼不用它們」。
runs:
  using: composite
  steps:
    - name: Map
      shell: bash
      run: |
        # 這一行是註解，裡面寫 %(cli)s 與 %(compile)s 與 x.lock.yml
        bash "${{ github.action_path }}/map.sh"
""" % {"cli": AGENT_CLI, "repo": AGENT_ACTION_REPO, "compile": AGENT_COMPILE_CMD}

CLEAN_ACTION_SH = """#!/usr/bin/env bash
# 這一行註解提到 %s 與 %s，剝註解之後不該留下任何命中。
set -euo pipefail
echo "status=Ready"
""" % (AGENT_CLI, AGENT_ACTION_REPO)

CLEAN_ACTION_PY = '''#!/usr/bin/env python3
"""這份 docstring 提到 %s 與 %s —— 敘述不是執行。"""
# 這一行註解也提到同一個字樣。
print("ok")
''' % (AGENT_CLI, AGENT_ACTION_REPO)


def synth_actions(root: Path, *, names=("aidlc-sync-map", "aidlc-sync-board"),
                  yml=None, sh=None, py=None) -> None:
    """合成 composite action 目錄：action.yml ＋ 一支 .sh ＋ 一支 .py。"""
    for name in names:
        base = root / ".github" / "actions" / name
        write(base / "action.yml", yml if yml is not None else CLEAN_ACTION_YML)
        write(base / ("%s.sh" % name.replace("aidlc-sync-", "")),
              sh if sh is not None else CLEAN_ACTION_SH)
        write(base / "run-fixtures.py", py if py is not None else CLEAN_ACTION_PY)


def test_composite_action_baseline_is_green() -> None:
    """@purpose **對照組（F1）**：乾淨的 composite action ＋ 乾淨的腳本 ⇒ 綠，且說明段／註解／docstring 裡的 gh-aw／copilot 字樣不得造成假紅燈。
    @given 四支乾淨 workflow ＋ 兩個乾淨的 composite action（含 .sh 與 .py）
    @step 跑 check-agentic-steps.py | rc=0
    @pass 後面兩條繞過測試可歸因於它自己的突變
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        r = run_checker(CHECK_AGENTIC, root)
        check("baseline rc", r.rc, 0)
        check_in("前提：composite action 真的被掃到", "aidlc-sync-map/action.yml", r.stdout)
        check_in("前提：腳本也真的被掃到", "map.sh", r.stdout)


def test_agentic_step_hidden_in_a_composite_action_is_red() -> None:
    """@purpose **F1 繞過 (a)**：把 `uses: githubnext/gh-aw@v1` 與 `run: copilot --prompt` 藏進 composite action 的 `runs.steps` ⇒ 紅。原實作只 glob workflows 目錄，這個檔從頭到尾沒被開過而檢查回報「0 失敗」。
    @given aidlc-sync-map/action.yml 的 runs.steps 多兩個代理式步驟
    @step 跑檢查器 | rc=1，失敗代號同時含 USES-1 與 RUN-1
    @step 讀訊息 | 指出是 aidlc-sync-map/action.yml
    @pass composite action 與 workflow 套用同一份可執行面判定
    @story S-10
    """
    dirty = CLEAN_ACTION_YML.replace(
        "    - name: Map\n",
        "    - name: Ask the agent\n"
        "      uses: %s@v1\n" % AGENT_ACTION_ORG
        + "    - name: Decide\n"
        "      shell: bash\n"
        "      run: %s --prompt \"decide the Status\"\n" % AGENT_CLI
        + "    - name: Map\n")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        write(root / ".github" / "actions" / "aidlc-sync-map" / "action.yml", dirty)
        r = run_checker(CHECK_AGENTIC, root)
        check_true("前提：突變真的寫進去了", AGENT_ACTION_ORG in dirty)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("USES-1 紅", any(i.startswith("USES-1") for i in ids), str(ids))
        check_true("RUN-1 紅", any(i.startswith("RUN-1") for i in ids), str(ids))
        check_in("訊息指出是哪一個 action.yml", "aidlc-sync-map/action.yml", r.stdout)


def test_agentic_call_hidden_in_a_composite_action_script_is_red() -> None:
    """@purpose **F1 繞過 (b)**：判定搬進 `map.sh`（`status="$(copilot -p "which Status?")"`）⇒ 紅。三支 `*-impl.yml` 的決定性邏輯全部在 `.sh` 檔內，這是判定最可能真的被搬進去的地方。
    @given aidlc-sync-map/map.sh 有一行真的呼叫 copilot（不是註解）
    @step 跑檢查器 | rc=1，失敗代號含 SCRIPT-1
    @step 讀訊息 | 指出是哪一支腳本、命中哪個字樣
    @pass 「換一層承載」達成同一件事，一樣被攔
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        write(root / ".github" / "actions" / "aidlc-sync-map" / "map.sh",
              '#!/usr/bin/env bash\nset -euo pipefail\n'
              'status="$(%s -p "which Status?")"\necho "status=${status}"\n' % AGENT_CLI)
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("SCRIPT-1 紅", any(i.startswith("SCRIPT-1") for i in ids), str(ids))
        check_in("訊息指出是哪一支腳本", "map.sh", r.stdout)
        check_in("訊息指出命中哪個字樣", AGENT_CLI, r.stdout)


def test_a_comment_only_mention_in_a_script_is_not_red() -> None:
    """@purpose 腳本的**註解**提到 copilot 不算違規——`check-ci-yml.py` 的 MARKER-1 第一版就是被「標記寫在註解裡」攻破的，反方向的錯（把註解判成違規）同樣會讓閘門失去作用。
    @given map.sh 只在註解裡提到 copilot 與 gh-aw
    @step 跑檢查器 | rc=0
    @pass 剝註解之後才比對
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        write(root / ".github" / "actions" / "aidlc-sync-map" / "map.sh",
              '#!/usr/bin/env bash\n# 決定不用 %s，也不用 %s。\necho "status=Ready"\n'
              % (AGENT_CLI, AGENT_ACTION_REPO))
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 0)


def test_python_docstring_mention_is_not_red_but_a_call_is() -> None:
    """@purpose `.py` 的敘述（docstring／註解）提到禁用字樣不算違規，真的呼叫算。本 repo 的 `run-reverse-tests.py`／`run-reconcile-tests.py` 各有一句 docstring 提到 gh-aw，把它們判紅是壞掉而不是嚴格。
    @given 同一棵樹，先放只在 docstring 提到 copilot 的 .py，再換成真的 subprocess 呼叫
    @step 跑檢查器（docstring 版） | rc=0
    @step 跑檢查器（呼叫版） | rc=1 且 SCRIPT-1 紅
    @pass 剝的是敘述，不是字串值
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        r = run_checker(CHECK_AGENTIC, root)
        check("docstring 版 rc", r.rc, 0)
        write(root / ".github" / "actions" / "aidlc-sync-map" / "run-fixtures.py",
              'import subprocess\nsubprocess.run(["%s", "-p", "which Status?"])\n' % AGENT_CLI)
        r2 = run_checker(CHECK_AGENTIC, root)
        check("呼叫版 rc", r2.rc, 1)
        check_true("SCRIPT-1 紅", any(i.startswith("SCRIPT-1") for i in r2.failed_ids()),
                   str(r2.failed_ids()))


def test_a_referenced_local_action_that_does_not_exist_is_red() -> None:
    """@purpose fail closed：workflow 以 `uses: ./.github/actions/aidlc-sync-x` 參照一個不存在的 composite action ⇒ 紅。沒有這一條，「把 action 改名／搬走」會讓那一份可執行面靜默地不再被掃。
    @given workflow 參照 aidlc-sync-ghost，但該目錄不存在
    @step 跑檢查器 | rc=1，失敗代號含 LOCALREF-1
    @pass 掃描集合的完整性由參照關係鎖住，不是靠 glob 剛好掃得到
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        write(root / ".github" / "workflows" / "aidlc-sync-forward.yml",
              CLEAN_SYNC_WF.replace("      - uses: actions/checkout@v4\n",
                                    "      - uses: ./.github/actions/aidlc-sync-ghost\n"))
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_true("LOCALREF-1 紅", any(i.startswith("LOCALREF-1") for i in r.failed_ids()),
                   str(r.failed_ids()))


def test_a_non_composite_action_is_red() -> None:
    """@purpose `runs.using` 不是 composite（node20／docker）⇒ 紅。docker action 的執行面是一個任意映像，本檢查看不進去；那是一次要有人看過的承載形式變更。
    @given aidlc-sync-board/action.yml 改成 using: docker
    @step 跑檢查器 | rc=1，失敗代號含 USING-1
    @pass 承載形式變更不會靜默通過
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        write(root / ".github" / "actions" / "aidlc-sync-board" / "action.yml",
              "name: x\ndescription: y\nruns:\n  using: docker\n  image: docker://example/agent:latest\n")
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_true("USING-1 紅", any(i.startswith("USING-1") for i in r.failed_ids()),
                   str(r.failed_ids()))


# ==========================================================================
# C-1（iteration 2，Critical）：掃描集合＝執行可達閉包，不是「檔案放在哪個目錄」
#
# iteration 2 的邊界是「workflow ＋ .github/actions/aidlc-sync-*/ 底下的 .sh／.py」。
# reviewer 構造五個繞過，每一個單獨都 rc=0，其中 B1 **完全不需要惡意**：把 helper 放
# `scripts/`（本 repo 的慣用落點，ci.yml 有三個呼叫點）就掃不到了。
# ==========================================================================
def _wf_with_run(root: Path, name: str, script_line: str) -> None:
    """把一行 run: 掛進某支合成 workflow 的決定性 job。"""
    write(root / ".github" / "workflows" / ("aidlc-sync-%s.yml" % name),
          CLEAN_SYNC_WF.replace(
              '          echo "純 Actions 的決定性步驟"\n',
              "          %s\n" % script_line))


def test_a_helper_outside_the_action_dirs_is_reachable_and_scanned() -> None:
    """@purpose **C-1 繞過 B1**：workflow `run: python3 scripts/decide-status.py`，而該檔真的呼叫代理式 CLI ⇒ 必須紅。iteration 2 對這個構造是 rc=0「0 失敗」，而它不是規避技巧——`scripts/` 就是本 repo 放 helper 的地方。這條測試釘住「掃描集合由執行可達性決定」，不是由目錄清單決定。
    @given 合成樹的 aidlc-sync-forward.yml 呼叫 scripts/decide-status.py，該檔有真的 subprocess 呼叫
    @step 跑檢查器 | rc=1 且 SCRIPT-1 紅
    @step 讀報告 | 掃描面列出該檔，且指出它是被誰帶進來的
    @pass 「把 helper 放到別的目錄」不再繞得過；下一次有人放 tools/ 也一樣
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        _wf_with_run(root, "forward", "python3 scripts/decide-status.py")
        write(root / "scripts" / "decide-status.py",
              'import subprocess\n'
              'subprocess.run(["%s", "-p", "which Status for this row?"])\n' % AGENT_CLI)
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("SCRIPT-1 紅", any(i.startswith("SCRIPT-1") for i in ids), str(ids))
        check_in("報告指出是哪一支 helper", "scripts/decide-status.py", r.stdout)
        check_in("報告說得出它是被誰帶進掃描面的", "aidlc-sync-forward.yml", r.stdout)


def test_a_transitively_reached_helper_is_scanned() -> None:
    """@purpose 可達閉包要**遞迴**：workflow → 一層 helper → 二層 helper。只走一層的話，「把判定再往下推一格」就又繞過去了。
    @given forward.yml 呼叫 scripts/outer.sh，outer.sh 再呼叫 scripts/inner.sh，判定在 inner.sh
    @step 跑檢查器 | rc=1 且 SCRIPT-1 指向 inner.sh
    @pass 閉包是走到不動點，不是走一步
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        _wf_with_run(root, "forward", "bash scripts/outer.sh")
        write(root / "scripts" / "outer.sh",
              '#!/usr/bin/env bash\nset -euo pipefail\nbash scripts/inner.sh\n')
        write(root / "scripts" / "inner.sh",
              '#!/usr/bin/env bash\nstatus="$(%s -p "which Status?")"\n' % AGENT_CLI)
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_true("SCRIPT-1 紅",
                   any(i.startswith("SCRIPT-1") and "inner.sh" in i for i in r.failed_ids()),
                   str(r.failed_ids()))


def test_an_unresolvable_invocation_target_is_red() -> None:
    """@purpose C-1 的 fail-closed：解析不出呼叫目標時**必須判紅並指名是哪一行**，不得靜默略過。靜默略過等於閉包在那裡斷掉而報告仍宣稱掃過了——那正是 iteration 1／2 兩次都踩到的形狀。
    @given forward.yml 的 run: 呼叫 `bash "$MYSTERY_SCRIPT"`，該變數在本體內沒有賦值
    @step 跑檢查器 | rc=1 且 REACH-1 紅
    @step 讀訊息 | 指出解不開的是哪一個目標
    @pass 閉包斷掉是一件會紅的事，不是一件沒人知道的事
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        _wf_with_run(root, "forward", 'bash "$MYSTERY_SCRIPT"')
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("REACH-1 紅", any(i.startswith("REACH-1") for i in ids), str(ids))
        check_in("訊息指出解不開的目標", "MYSTERY_SCRIPT", r.stdout)


def test_resolvable_shell_indirection_does_not_go_red() -> None:
    """@purpose fail-closed 的另一半：**解得開的一律要解開**，否則真實 repo 會恆紅而閘門會被關掉。本 repo 三支 `*-impl.yml` 的呼叫全長成 `VAR="${OTHER}/x.sh"` ＋ 續行 ＋ `bash "$VAR"`，中間還隔著一個包裝函式。
    @given forward.yml 用變數鏈、續行與包裝函式呼叫一支乾淨的 helper
    @step 跑檢查器 | rc=0（解得開，且 helper 是乾淨的）
    @step 讀報告 | helper 出現在掃描面上（真的解開了，不是略過了）
    @pass 這一條是 REACH-1 不會變成假紅燈的保證
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        write(root / ".github" / "workflows" / "aidlc-sync-forward.yml",
              CLEAN_SYNC_WF.replace(
                  '          echo "純 Actions 的決定性步驟"\n',
                  '          WORKSPACE="${GITHUB_WORKSPACE:-$PWD}"\n'
                  '          HELPERS="${WORKSPACE}/scripts"\n'
                  '          MAP_SH="${HELPERS}/map-helper.sh"\n'
                  '          run_pure() { env -u GH_TOKEN "$@"; }\n'
                  '          run_pure \\\n'
                  '            AIDLC_X="1" \\\n'
                  '            bash "$MAP_SH"\n'))
        write(root / "scripts" / "map-helper.sh",
              '#!/usr/bin/env bash\nset -euo pipefail\necho "status=Ready"\n')
        r = run_checker(CHECK_AGENTIC, root)
        check("rc（解得開就不該紅）", r.rc, 0)
        check_in("helper 真的進了掃描面", "scripts/map-helper.sh", r.stdout)


def test_scripts_are_scanned_regardless_of_suffix() -> None:
    """@purpose **M-1**（iteration 2，Major）：副檔名原本是允許清單 `(".sh", ".py")`，於是 `.bash` 與**無副檔名**的檔案都掃不到（reviewer 實測兩者都 rc=0）。改成排除清單之後，只有已知不可執行的副檔名被跳過。
    @given 同一個判定分別放進 decide.bash 與無副檔名的 decider，兩者都被 map.sh 呼叫
    @step 跑檢查器（.bash） | rc=1
    @step 跑檢查器（無副檔名） | rc=1
    @pass 「換個副檔名」不再是一條路
    @story S-10
    """
    # **兩條進入掃描面的路都要測**：
    #   (a) 被呼叫到（可達閉包帶進來的）——這條由 C-1 的閉包負責，與副檔名無關；
    #   (b) 只是躺在 action 目錄裡、沒有人呼叫（目錄種子 glob 帶進來的）——**這條才是
    #       M-1 真正管的那一條**，因為只有它會過 `is_scannable_file()` 的副檔名判定。
    # 少了 (b)，把副檔名改回允許清單這條測試照樣綠（實測過），M-1 的迴歸保護等於零。
    for label, fname, invoked in (
        ("有副檔名 .bash／被呼叫", "decide.bash", True),
        ("無副檔名／被呼叫", "decider", True),
        ("有副檔名 .bash／沒有人呼叫", "decide.bash", False),
        ("無副檔名／沒有人呼叫", "decider", False),
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            synth_workflows(root)
            synth_actions(root)
            base = root / ".github" / "actions" / "aidlc-sync-map"
            if invoked:
                write(base / "map.sh",
                      '#!/usr/bin/env bash\nset -euo pipefail\n'
                      'bash "${GITHUB_ACTION_PATH}/%s"\n' % fname)
            write(base / fname,
                  '#!/usr/bin/env bash\nstatus="$(%s -p "which Status?")"\n' % AGENT_CLI)
            r = run_checker(CHECK_AGENTIC, root)
            check("%s：rc" % label, r.rc, 1)
            check_true("%s：SCRIPT-1 紅" % label,
                       any(i.startswith("SCRIPT-1") and fname in i for i in r.failed_ids()),
                       str(r.failed_ids()))

    # 反向：已知不可執行的副檔名**不該**被掃——action 目錄裡有 38 個 `.md` fixture，
    # 把它們掃進來只會製造噪音與假紅燈。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        write(root / ".github" / "actions" / "aidlc-sync-map" / "fixtures" / "sample.md",
              "# 這是測試資料，裡面提到 %s 與 %s\n" % (AGENT_CLI, AGENT_ACTION_REPO))
        r = run_checker(CHECK_AGENTIC, root)
        check("`.md` fixture 不進掃描面（rc）", r.rc, 0)


def test_ci_yml_is_on_the_scan_surface() -> None:
    """@purpose **M-5**（iteration 2，Major）：`ci.yml` 承載 U-10a 的同步判定（gate/probe），但它不在 R-1.2 原本的 glob 內，而 `check-ci-yml.py` 對代理式承載零檢查——reviewer 把 `is_sync="$(copilot -p …)"` 注入 probe step，兩道守衛同時綠燈。
    @given 合成樹放一份 ci.yml，其 gate job 的 run: 呼叫代理式 CLI
    @step 跑檢查器 | rc=1 且 RUN-1 紅、訊息指名 ci.yml
    @pass 判定搬進 ci.yml 也攔得住
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        write(root / ".github" / "workflows" / "ci.yml",
              "name: CI\non:\n  pull_request:\njobs:\n  gate:\n"
              "    runs-on: ubuntu-latest\n    steps:\n"
              "      - id: probe\n        run: |\n"
              '          is_sync="$(%s -p \'is this a sync writeback?\')"\n' % AGENT_CLI)
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("RUN-1 紅", any(i.startswith("RUN-1") for i in ids), str(ids))
        check_in("訊息指名 ci.yml", "ci.yml", r.stdout)


def test_ci_yml_third_party_actions_do_not_go_red() -> None:
    """@purpose M-5 的另一半，也是本輪對 brief 的一處刻意偏離：`judge_surface()` 的 `uses:` **允許清單**是為同步資產量身訂做的，而 `ci.yml` 合法使用 `docker/build-push-action`。照搬允許清單會讓真實 repo 立刻恆紅，而恆紅的閘門等於沒有閘門。所以 ci.yml 走禁止清單。
    @given 合成樹的 ci.yml 使用第三方 docker action（非代理式）
    @step 跑檢查器 | rc=0
    @step 換成代理式 action | rc=1
    @pass 納入 ci.yml 沒有把它變成一道假紅燈的來源，但代理式承載照樣攔
    @story S-10
    """
    tmpl = ("name: CI\non:\n  pull_request:\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n      - uses: %s\n")
    for label, uses, want_rc in (
        ("第三方 docker action", "docker/build-push-action@v6", 0),
        ("代理式 action", "%s@v1" % AGENT_ACTION_ORG, 1),
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            synth_workflows(root)
            write(root / ".github" / "workflows" / "ci.yml", tmpl % uses)
            r = run_checker(CHECK_AGENTIC, root)
            check("%s：rc" % label, r.rc, want_rc)


def test_an_action_referencing_a_missing_action_is_red() -> None:
    """@purpose **m-1**（iteration 2，Minor）：LOCALREF-1 原本只回填 workflow 層的 `uses:`，於是 action → action 這條邊上，模組說明宣稱的「搬走／改名不可能靜默地少掃一份」不成立。reviewer 實測在 map/action.yml 加一個指向不存在 action 的 `uses:` ⇒ rc=0。
    @given aidlc-sync-map/action.yml 參照 ./.github/actions/aidlc-sync-ghost（不存在）
    @step 跑檢查器 | rc=1 且 LOCALREF-1 紅
    @pass 參照得到卻掃不到的可執行面會被指名
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root)
        write(root / ".github" / "actions" / "aidlc-sync-map" / "action.yml",
              CLEAN_ACTION_YML.replace(
                  "  steps:\n",
                  "  steps:\n    - uses: ./.github/actions/aidlc-sync-ghost\n", 1))
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("LOCALREF-1 紅", any(i.startswith("LOCALREF-1") for i in ids), str(ids))
        check_in("訊息指名缺的是哪一個", "aidlc-sync-ghost", r.stdout)


def test_the_scan_exemption_is_one_pure_data_file() -> None:
    """@purpose 掃描面的豁免是這道檢查唯一的洞，所以它必須是**逐檔具名、可數、可審**的。iteration 2 的 M-2：原本是整檔豁免三支 `.py`，其中兩支每個 pull_request 都在 CI 執行 PR head 的程式碼——reviewer 實測把真的 `subprocess.run` 呼叫加進被豁免的檔，rc=0。現在只剩一份沒有可執行語意的 `.json`。
    @given check-agentic-steps.py 的 SCAN_EXEMPT
    @step 比對集合 | 恰好是那一份資料檔
    @step 檢查它的副檔名 | 是 .json（資料，不是程式）
    @step 檢查三支 selftest .py | 全部**不在**豁免內
    @pass 「把判定藏進被豁免的檔」不再是一條可走的路
    @story S-10
    """
    exempt = set(_cas.SCAN_EXEMPT)
    check("豁免恰為一份資料檔", sorted(exempt),
          [".github/actions/aidlc-sync-selftest/agentic-tokens.json"])
    for rel in exempt:
        check_true("%s 是純資料（.json）" % rel, rel.endswith(".json"), rel)
        check_true("%s 真的存在" % rel, (REPO_ROOT / rel).is_file(), rel)
    for name in ("check-agentic-steps.py", "check-paths-relations.py",
                 "run-selftest-tests.py"):
        rel = ".github/actions/aidlc-sync-selftest/%s" % name
        check_true("%s 不在豁免內（它回到掃描面上了）" % name, rel not in exempt, rel)
        body = _cas.script_body(REPO_ROOT / rel).lower()
        check("%s 剝除敘述後不含任何被禁字樣" % name,
              [tok for tok in _cas.AGENTIC_TOKENS if tok in body], [])


def test_an_agentic_call_added_to_a_selftest_checker_is_red() -> None:
    """@purpose M-2 的突變驗證：把真正的代理式呼叫加進**過去被整檔豁免**的 `check-paths-relations.py` ⇒ 紅。reviewer 對舊版實測這一步是 rc=0，因為那份豁免是整檔的、而且不逐行區分「提到 token」與「呼叫 token」。
    @given 合成樹裡放一支與被豁免檔同名的腳本，內含真的 subprocess 呼叫
    @step 跑檢查器 | rc=1 且 SCRIPT-1 紅
    @pass 豁免縮到資料檔之後，三支 .py 的任何一支被塞進判定都攔得住
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        synth_actions(root, names=("aidlc-sync-selftest",))
        write(root / ".github" / "actions" / "aidlc-sync-selftest" / "check-paths-relations.py",
              'import subprocess\nsubprocess.run(["%s", "-p", "which Status?"])\n' % AGENT_CLI)
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("SCRIPT-1 紅", any(i.startswith("SCRIPT-1") for i in ids), str(ids))
        check_in("訊息指出是哪一支", "check-paths-relations.py", r.stdout)


def test_the_unresolvable_invocation_list_is_pinned() -> None:
    """@purpose C-1 的 fail-closed 需要一個逃生門（真的解不開的呼叫目標），而逃生門必須是**具名、可數、附理由**的，否則下一個人會直接把整道檢查關掉。交付時它是空的——那不是預設值，是實跑真實 repo 的結果。
    @given check-agentic-steps.py 的 UNRESOLVABLE_INVOCATIONS
    @step 比對大小 | 0 條
    @step 檢查每一項的形狀 | (來源, 目標, 為什麼解不開) 三欄俱全且理由非空
    @pass 加一條進去是一個會讓這條測試紅燈的動作，不是一個安靜的改動
    @story S-10
    """
    entries = tuple(_cas.UNRESOLVABLE_INVOCATIONS)
    check("交付時解不開的呼叫目標為 0 條", len(entries), 0)
    for entry in entries:
        check("每一項是三欄", len(entry), 3)
        check_true("理由非空（不得只列路徑）", bool(str(entry[2]).strip()), str(entry))


def test_deliberate_obfuscation_is_out_of_scope_and_says_so() -> None:
    """@purpose reviewer 的 B4（`c=cop; d=ilot; "$c$d"`）與 B5（`eval` ＋ base64）**確實繞得過**本檢查。這條測試把那個邊界寫成可執行的斷言而不是一句免責聲明：執行面用的是禁止清單，它防的是無意的搬移，不是對抗性規避（模組 docstring 的 m-2 段）。**這條測試斷言的是「已知且已載明」，不是「已修好」**——哪天有人改成允許清單，它會紅，那時該更新的是這條測試與那段說明。
    @given 合成樹的 map.sh 用拆字與 eval 兩種手法呼叫代理式 CLI
    @step 跑檢查器 | rc=0（本檢查看不出來）
    @step 讀模組說明 | 它逐字寫明擋不住刻意混淆
    @pass 邊界是寫下來的、可查的，不是被忽略的
    @story S-10
    """
    half = len(AGENT_CLI) // 2
    for label, script in (
        ("拆字", '#!/usr/bin/env bash\nc="%s"\nd="%s"\n"$c$d" -p "which Status?"\n'
                 % (AGENT_CLI[:half], AGENT_CLI[half:])),
        ("eval ＋ base64", '#!/usr/bin/env bash\neval "$(echo %s | base64 -d)"\n'
                          % base64.b64encode((AGENT_CLI + " -p x").encode()).decode()),
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            synth_workflows(root)
            synth_actions(root)
            write(root / ".github" / "actions" / "aidlc-sync-map" / "map.sh", script)
            r = run_checker(CHECK_AGENTIC, root)
            check("%s：本檢查已載明看不出來" % label, r.rc, 0)
    doc = CHECK_AGENTIC.read_text(encoding="utf-8")
    check_in("模組說明逐字載明這個邊界", "擋不住刻意的混淆", doc)
    check_in("模組說明說得出它防的是什麼", "無意的搬移", doc)


# ==========================================================================
# A-6：check-paths-relations.py 的行為
# ==========================================================================
def test_paths_baseline_is_green() -> None:
    """@purpose **對照組**：五個承載體都有 paths-ignore、selftest 的 allowlist 與它無交集 ⇒ 綠。
    @given 合成樹備齊 ci.yml ＋ 四支 gh-aw（md ＋ lock）＋ record.sh ＋ check-ci-yml.py
    @step 跑 check-paths-relations.py | rc=0
    @pass 後面每一條「應該紅」都可歸因於它自己的突變
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        r = run_checker(CHECK_PATHS, root)
        check("baseline rc", r.rc, 0)
        check_in("前提：glob 真的是從 record.sh 推導出來的", WRITE_GLOB, r.stdout)
        check_in("前提：DISJOINT-1 有跑到", "DISJOINT-1", r.stdout)


def test_a_gh_aw_carrier_without_paths_ignore_is_red() -> None:
    """@purpose **必測 #4**：某個承載體缺 paths-ignore ⇒ 紅（含 gh-aw 四支）。U-10b 漏做必須有紅燈。
    @given ui-regression 的 md 與 lock 都沒有 paths-ignore，其餘四個承載體正常
    @step 跑檢查器 | rc=1，失敗代號含 IGNORE:ui-regression.md 與 IGNORE:ui-regression.lock.yml
    @step 檢視其他三支 | 不受影響（訊息指得出是哪一支）
    @pass 「把 gh-aw 四支寫成可選」會讓這一條失去作用，所以它們不是可選的
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), skip_carrier="ui-regression")
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("md 那一項紅", "IGNORE:ui-regression.md" in ids, str(ids))
        check_true("lock 那一項紅", "IGNORE:ui-regression.lock.yml" in ids, str(ids))
        check_true("其他三支不受影響",
                   not any(c in i for c in ("pr-reviewer", "lint-fix", "contract-guard") for i in ids),
                   str(ids))


def test_md_updated_but_lock_not_recompiled_is_red() -> None:
    """@purpose **必測 #17**：`.md` 有 paths-ignore 但 `.lock.yml` 沒有 ⇒ 紅，且訊息含「未重新編譯」。GitHub 執行的是 lock，這種漂移下排除完全沒生效而且沒有任何錯誤訊息（open-items.md 的 N:M-5）。
    @given 四支 gh-aw 的 md 都有 paths-ignore，lock 都沒有
    @step 跑檢查器 | rc=1，失敗代號含 COMPILED:<name>
    @step 讀訊息 | 含「未重新編譯」
    @pass 漏掉 `gh aw compile` 這一步會被指名
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), lock_ignore=False)
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("四支的 COMPILED 都紅",
                   all(("COMPILED:%s" % n) in ids for n in GH_AW_CARRIERS), str(ids))
        check_in("訊息說得出是沒有重新編譯", "未重新編譯", r.stdout)
        check_true("前提：md 那一側是綠的（所以紅的確實是編譯漂移）",
                   not any(i.endswith(".md") for i in ids), str(ids))


def test_a_new_unfiltered_pull_request_workflow_is_red() -> None:
    """@purpose **tcms-test-cases Q2=A**：新增一支無 paths 過濾的 `on: pull_request` workflow ⇒ 紅。`IGNORE:` 那一族驗的是「這五個承載體被排除了」，**不是**「沒有別的跑起來」——兩者不等價，而 [US:S-6 AC 7]（反向 PR 不觸發高成本 workflow）要的是後者。在這條斷言之前，那個事實只寫在本檔絆線訊息的一段註解裡。
    @given 合成樹已有正常的五個承載體，另加一支 `on: pull_request` 無 paths 的 workflow
    @step 跑檢查器 | rc=1，失敗代號含 PR-TRIGGER-1
    @step 讀訊息 | 「多出來的」逐字列出那支新 workflow 的檔名
    @step 對照組：把那支拿掉 | rc=0
    @pass 有人新增一支無過濾的 PR workflow 時，反向同步每天多觸發它一次這件事會紅燈
    @story S-6
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        probe = root / ".github" / "workflows" / "zz-probe.yml"
        probe.write_text(
            "name: probe\non:\n  pull_request:\njobs:\n  x:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: echo probe\n", encoding="utf-8")
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("PR-TRIGGER-1 紅", "PR-TRIGGER-1" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息指名那支新 workflow", "zz-probe.yml", r.stdout)

        probe.unlink()
        r2 = run_checker(CHECK_PATHS, root)
        check("對照組 rc（拿掉之後）", r2.rc, 0)


def test_an_unreadable_workflow_counts_as_triggering() -> None:
    """@purpose 解析不開的 workflow **一律計入會觸發的集合**（fail closed）。讀不到不等於安全——一個「解析失敗就跳過」的實作會讓「把檔案寫壞」變成繞過這道檢查最省事的方法。
    @given 合成樹多一支語法壞掉的 .yml
    @step 跑檢查器 | rc=1，失敗代號含 PR-TRIGGER-READ:<檔名>
    @step 讀訊息 | 逐字寫「讀不到不等於安全」
    @pass 壞掉的 workflow 不會讓這道檢查靜默放行
    @story S-6
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        bad = root / ".github" / "workflows" / "zz-broken.yml"
        bad.write_text("name: broken\non:\n  pull_request:\n    types: [\n", encoding="utf-8")
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("PR-TRIGGER-READ 紅",
                   any(i.startswith("PR-TRIGGER-READ") for i in r.failed_ids()),
                   str(r.failed_ids()))
        check_in("訊息逐字寫明 fail-closed 的立場", "讀不到不等於安全", r.stdout)


def test_a_lock_compiled_by_another_compiler_version_is_red() -> None:
    """@purpose **ci-pipeline Q4=A**：`.lock.yml` 由**別的**編譯器版本編出 ⇒ 紅。`COMPILED:` 只驗一條 glob 的一致性，完全不看是誰編的——U-10b 的 code-summary 逐字登錄了這個缺口，並實測用較新版本重編會一併換掉 `gh-aw-manifest` 裡的 action SHA、防火牆容器與 MCP server 映像（六項，依 ADR-0006 每一個都需安全審查）。這條斷言不禁止升級，它讓升級變成一個必須被明講的決定。
    @given 合成樹的四支 lock 首行 metadata 寫著一個不等於釘住值的 compiler_version
    @step 跑檢查器 | rc=1，失敗代號含四支的 COMPILER:<name>
    @step 讀訊息 | 說得出預期與實得的版本
    @step 對照組：把版本改回釘住值 | rc=0
    @pass 「順手用本機較新的編譯器重編」不再是一條沒有紅燈的路
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), lock_compiler="v9.99.9-not-the-pinned-one")
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("四支的 COMPILER 都紅",
                   all(("COMPILER:%s" % n) in ids for n in GH_AW_CARRIERS), str(ids))
        check_in("訊息帶得出實得的版本", "v9.99.9-not-the-pinned-one", r.stdout)
        check_in("訊息帶得出預期的版本", SYNTH_LOCK_COMPILER, r.stdout)
        check_true("前提：paths-ignore 那一側是綠的（紅的確實是編譯器版本）",
                   not any(i.startswith("IGNORE:") or i.startswith("COMPILED:") for i in ids),
                   str(ids))

    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        r = run_checker(CHECK_PATHS, root)
        check("對照組 rc（版本正確時是綠的）", r.rc, 0)


def test_a_lock_without_metadata_is_red_not_a_vacuous_pass() -> None:
    """@purpose 讀不到 `compiler_version` 時**不得視為通過**（fail closed）。這是本檔其餘檢查一致的立場：推導不出來代表判定基準不存在，而不是「沒問題」。一個回 `None` 就當綠的實作，會讓「把首行刪掉」變成繞過這道檢查最省事的方法。
    @given 合成樹的四支 lock 被拿掉 metadata 首行
    @step 跑檢查器 | rc=1，失敗代號含 COMPILER:<name>
    @step 讀訊息 | 逐字說「不得因為讀不到而視為通過」
    @pass 刪掉 metadata 首行不會讓這道檢查靜默消失
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        for name in GH_AW_CARRIERS:
            lock = root / ".github" / "workflows" / ("%s.lock.yml" % name)
            lines = lock.read_text(encoding="utf-8").split("\n")
            lock.write_text("\n".join(lines[1:]), encoding="utf-8")
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        ids = r.failed_ids()
        check_true("四支的 COMPILER 都紅",
                   all(("COMPILER:%s" % n) in ids for n in GH_AW_CARRIERS), str(ids))
        check_in("訊息逐字寫明 fail-closed 的立場", "不得因為讀不到而視為通過", r.stdout)


def test_lock_missing_paths_ignore_is_red_even_when_md_has_it() -> None:
    """@purpose **必測 #18**：`.lock.yml` 缺 paths-ignore ⇒ 紅（即使 `.md` 有）。這一條與 #17 是同一棵樹的兩個不同斷言：#17 看「一致性」那一項，本條看「lock 本身」那一項——只驗一致性的話，兩邊**都**缺時反而會綠。
    @given 同 #17 的樹（md 有、lock 沒有）
    @step 跑檢查器 | 失敗代號含 IGNORE:<name>.lock.yml
    @pass 決定性的那一份被獨立斷言
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), lock_ignore=False)
        r = run_checker(CHECK_PATHS, root)
        ids = r.failed_ids()
        check_true("四支的 lock 那一項都紅",
                   all(("IGNORE:%s.lock.yml" % n) in ids for n in GH_AW_CARRIERS), str(ids))
        check_in("訊息說明 GitHub 跑的是 lock", "GitHub 執行的是這一份", r.stdout)


def test_ci_yml_without_paths_ignore_is_red() -> None:
    """@purpose 第五個承載體（U-10a 的 ci.yml）同樣不是可選的。
    @given ci.yml 沒有 paths-ignore
    @step 跑檢查器 | rc=1，失敗代號含 IGNORE:ci.yml
    @pass 五個承載體逐一要求，缺一即紅
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), ci_ignore=False)
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("IGNORE:ci.yml 紅", "IGNORE:ci.yml" in r.failed_ids(), str(r.failed_ids()))


def test_sync_state_in_the_selftest_allowlist_is_red() -> None:
    """@purpose **必測 #5**：把 sync-state.json 加進本單元 allowlist ⇒ 紅。R-3 逐字「兩個條件必須一起斷言」——只驗關係 1 的話，這個改動不會讓任何東西失敗，而它會讓反向 PR 觸發自我測試。
    @given selftest 的 allowlist 多一條與寫入 glob 相同的樣式
    @step 跑檢查器 | rc=1，失敗代號含 DISJOINT-1
    @pass 關係 2 真的在運作
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td),
                                selftest_paths=DEFAULT_SELFTEST_PATHS + (WRITE_GLOB,))
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("DISJOINT-1 紅", "DISJOINT-1" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息指出相交的是哪一條", WRITE_GLOB, r.stdout)


def test_a_broader_glob_in_the_allowlist_is_also_red() -> None:
    """@purpose 交集判定不是字串相等：`aidlc/**` 沒有與寫入 glob 逐字相同，但它涵蓋它。把判定寫成字串比對就會漏掉這一類。
    @given selftest 的 allowlist 多一條 aidlc/**
    @step 跑檢查器 | DISJOINT-1 紅
    @pass 涵蓋關係而非字面相同
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), selftest_paths=DEFAULT_SELFTEST_PATHS + ("aidlc/**",))
        r = run_checker(CHECK_PATHS, root)
        check_true("DISJOINT-1 紅", "DISJOINT-1" in r.failed_ids(), str(r.failed_ids()))


def test_fixture_allowlist_does_not_false_positive() -> None:
    """@purpose 反面：fixture 集的 allowlist（`aidlc/spaces/*/intents/*/.test-fixtures/**`）與寫入 glob **不**相交，不得假紅燈。兩者的字面前綴同為 `aidlc/spaces/`，用「比對字面前綴」的保守判定會在這裡誤報。
    @given 預設 allowlist（含 .test-fixtures/**）
    @step 跑檢查器 | DISJOINT-1 綠
    @pass 一個會誤報的閘門，比沒有閘門更快失去作用
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        r = run_checker(CHECK_PATHS, root)
        check_true("DISJOINT-1 不在失敗清單裡", "DISJOINT-1" not in r.failed_ids(), str(r.failed_ids()))
        check_true("前提：allowlist 真的含 .test-fixtures/**",
                   ".test-fixtures/**" in r.stdout, r.stdout)


def test_missing_selftest_workflow_is_red_not_silently_disjoint() -> None:
    """@purpose 讀不到 selftest workflow 時**不得視為無交集**——那會讓關係 2 在檔案被改名時靜默消失。
    @given 合成樹沒有 aidlc-sync-selftest.yml
    @step 跑檢查器 | DISJOINT-1 紅
    @pass fail closed
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        (root / ".github" / "workflows" / "aidlc-sync-selftest.yml").unlink()
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("DISJOINT-1 紅", "DISJOINT-1" in r.failed_ids(), str(r.failed_ids()))


def test_selftest_without_allowlist_is_red() -> None:
    """@purpose 沒有 allowlist ＝ 每個 PR 都觸發，關係 2 會以最壞的方式被違反。
    @given selftest 的 on.pull_request 沒有 paths
    @step 跑檢查器 | ALLOWLIST-1 紅
    @pass 「刪掉 allowlist」不是一個安靜的改動
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        write(root / ".github" / "workflows" / "aidlc-sync-selftest.yml",
              "name: s\non:\n  pull_request:\n  workflow_dispatch:\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo x\n")
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("ALLOWLIST-1 紅", "ALLOWLIST-1" in r.failed_ids(), str(r.failed_ids()))


def test_glob_derivation_failure_is_an_external_error() -> None:
    """@purpose **必測 #6**：`derive_glob_from_record_sh()` 推導失敗 ⇒ 紅，不得靜默放行。推導不出來代表白名單的形狀變了，需要人看過。
    @given record.sh 少了 record_path 的驗證 regex
    @step 跑檢查器 | rc=2、stderr 第一行 EXTERNAL-ERROR:
    @step 讀訊息 | 說明失去比對基準
    @pass fail closed；且分類為外部錯誤而非斷言失敗
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), broken_record=True)
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 2)
        check_in("第一行可分辨為外部錯誤", EXTERNAL_PREFIX, r.stderr)
        check_in("訊息說明失去比對基準", "比對基準", r.stderr)


def test_missing_ci_guard_is_an_external_error() -> None:
    """@purpose 推導函式的來源檔不在時 fail closed——**不得改用寫死的字面值**，那正是這個 import 要避免的事。
    @given 合成樹沒有 check-ci-yml.py
    @step 跑檢查器 | rc=2
    @pass 單一真實來源不會在來源消失時退化成第二份副本
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        (root / ".github" / "actions" / "aidlc-sync-ci-guard" / "check-ci-yml.py").unlink()
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 2)
        check_in("第一行可分辨為外部錯誤", EXTERNAL_PREFIX, r.stderr)


def test_a_carrier_that_ignores_the_selftest_allowlist_is_red() -> None:
    """@purpose **F3 迴歸**：R-3:33 逐字要求「該 **glob 集合** ∩ 本單元的 allowlist ＝ ∅」，而原實作只跟 `derive_write_glob()` 回傳的**單一字串**比。reviewer 把本單元 allowlist 的兩條逐字加進 ci.yml 的 paths-ignore，15 項檢查 0 失敗——那個設定下改機制的 PR 完全不跑 CI，而自我測試對機制變更靜默失效。
    @given ci.yml 的 paths-ignore 除了寫入 glob 之外，還逐字含本單元 allowlist 的兩條
    @step 跑 check-paths-relations.py | rc=1，DISJOINT-1 紅
    @step 讀訊息 | 指名相交的是哪一條 allowlist、來自哪一個承載體
    @pass 比對的是承載體**實際宣告**的整個 glob 集合，不是推導出來的那一條
    @story S-10
    """
    swallow = (".github/workflows/aidlc-sync-*.yml", ".github/actions/aidlc-sync-*/**")
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), ci_extra_ignore=swallow)
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("DISJOINT-1 紅", "DISJOINT-1" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息指名是哪一個承載體宣告的", "ci.yml", r.stdout)
        check_in("訊息指名相交的 allowlist 條目", ".github/actions/aidlc-sync-*/**", r.stdout)


def test_a_gh_aw_carrier_that_ignores_the_selftest_allowlist_is_red() -> None:
    """@purpose 同 F3，但排除寫在 gh-aw 的 `.lock.yml` 上——**GitHub 執行的是 lock**，所以把機制檔吞掉的那一份最可能出現在那裡。只跟 ci.yml 比會漏掉這一類。
    @given ui-regression.lock.yml 的 paths-ignore 多一條 `.github/**`
    @step 跑檢查器 | DISJOINT-1 紅，訊息指名 ui-regression.lock.yml
    @pass 五個承載體宣告的 glob 一視同仁地進入交集判定
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        lock = root / ".github" / "workflows" / "ui-regression.lock.yml"
        lock.write_text(
            lock.read_text(encoding="utf-8").replace(
                "      - '%s'\n" % WRITE_GLOB,
                "      - '%s'\n      - '.github/**'\n" % WRITE_GLOB),
            encoding="utf-8")
        r = run_checker(CHECK_PATHS, root)
        check_true("DISJOINT-1 紅", "DISJOINT-1" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息指名是哪一個承載體", "ui-regression.lock.yml", r.stdout)


def test_the_allowlist_must_cover_every_carrier_file() -> None:
    """@purpose **F7 迴歸**：A-6 斷言的九個檔案（ci.yml ＋ 四支 gh-aw 的 .md／.lock.yml）必須都在本單元的觸發 allowlist 內。少了它們，U-10b 上線後任何人把 paths-ignore 拿掉都**不會觸發 U-9**——這道斷言只在沒人動它的時候才會執行。
    @given selftest 的 allowlist 只有三條機制路徑（沒有承載體檔案）
    @step 跑檢查器 | rc=1，COVERAGE-1 紅，訊息逐一列出沒被涵蓋的檔案
    @step 換成含九條承載體路徑的 allowlist | COVERAGE-1 綠
    @pass 要求清單由 GH_AW_CARRIERS 產生，與承載體清單同一個來源
    @story S-10
    """
    bare = (".github/workflows/aidlc-sync-*.yml", ".github/actions/aidlc-sync-*/**",
            "aidlc/spaces/*/intents/*/.test-fixtures/**")
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), selftest_paths=bare)
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("COVERAGE-1 紅", "COVERAGE-1" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息列出沒被涵蓋的 ci.yml", ".github/workflows/ci.yml", r.stdout)
        check_in("訊息列出沒被涵蓋的 lock", "ui-regression.lock.yml", r.stdout)
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        r = run_checker(CHECK_PATHS, root)
        check_true("COVERAGE-1 綠", "COVERAGE-1" not in r.failed_ids(), str(r.failed_ids()))


def test_a_plus_quantifier_in_a_path_pattern_is_fail_closed() -> None:
    """@purpose **F11 迴歸**：GitHub 的路徑過濾語法有 `+`（配一個以上的前一個字元），而交集判定把它當成字面字元——與同檔對 `!` 與混寫 `**` 的 fail-closed 處理不一致。猜錯的兩個方向都很貴：猜寬是假紅燈、猜窄是靜默放行。
    @given selftest 的 allowlist 多一條含 `+` 的樣式
    @step 跑檢查器 | rc=2、stderr 第一行 EXTERNAL-ERROR:，訊息指名那一條樣式
    @pass 不支援的語法一律拒絕判定，不假裝算得出來
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(
            Path(td), selftest_paths=DEFAULT_SELFTEST_PATHS + (".github/workflows/a+.yml",))
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 2)
        check_in("第一行可分辨為外部錯誤", EXTERNAL_PREFIX, r.stderr)
        check_in("訊息指名那一條樣式", "a+.yml", r.stderr)


# ==========================================================================
# 第一段驅動：run-selftest-fixtures.py 的行為
# ==========================================================================
def _synth_fixture_repo(root: Path, *, leak=False, drift_round_2=False,
                        shell_driver=None, drop_token=False,
                        drop_output=None, extra_output=None,
                        fixture_rel=None, extra_fixture_rel=None) -> Path:
    """複製真實的 map／block／fixture 到暫存樹，再依參數做突變。

    複製而不是重寫：突變測試要驗的是「真實實作壞掉時本檔會不會紅」，用一份自己寫的假
    map.sh 只能驗到自己寫的東西。
    """
    for name in ("aidlc-sync-map", "aidlc-sync-block"):
        shutil.copytree(ACTIONS / name, root / ".github" / "actions" / name)
    shutil.copytree(REPO_ROOT / FIXTURE_REL, root / (fixture_rel or FIXTURE_REL))
    if extra_fixture_rel:
        shutil.copytree(REPO_ROOT / FIXTURE_REL, root / extra_fixture_rel)
    if drop_output or extra_output:
        # 改的是 map.sh 的 **output 集合**（不是值）：CRED-1 原本用 decision.get(name, "")
        # 取值，缺席的 output 取到空字串然後判「不含憑證樣式」而通過——一條被刪掉的
        # output 於是變成一條恆真的斷言（reviewer iteration 1 的 F6）。
        base = root / ".github" / "actions" / "aidlc-sync-map"
        (base / "map.sh").rename(base / "map-real.sh")
        body = ['#!/usr/bin/env bash',
                'here="$(cd "$(dirname "$0")" && pwd)"',
                'out="$(bash "$here/map-real.sh" "$@")"']
        if drop_output:
            body.append('out="$(printf "%%s\\n" "$out" | grep -v "^%s=")"' % drop_output)
        body.append('printf "%s\\n" "$out"')
        if extra_output:
            body.append('echo "%s=whatever"' % extra_output)
        write(base / "map.sh", "\n".join(body) + "\n")
    if leak:
        # 把 Parked 的理由漏進 scope_note —— U-1 security-requirements SEC-1 逐字點名的
        # 殘留風險（「本單元會原樣把它搬進 log」）。用包裝器而不是改 map.sh 內部：包裝器
        # 的洩漏路徑與真實實作可能出現的洩漏在 output 上不可分辨，而它可控得多。
        real = root / ".github" / "actions" / "aidlc-sync-map" / "map-real.sh"
        (root / ".github" / "actions" / "aidlc-sync-map" / "map.sh").rename(real)
        write(root / ".github" / "actions" / "aidlc-sync-map" / "map.sh",
              '#!/usr/bin/env bash\n'
              'here="$(cd "$(dirname "$0")" && pwd)"\n'
              'out="$(bash "$here/map-real.sh" "$@")"\n'
              'parked="$(printf "%s" "${AIDLC_STATE_MD:-}" | sed -n "s/^- \\*\\*Parked\\*\\*: //p")"\n'
              'printf "%s\\n" "$out" | sed "s|^scope_note=.*|scope_note=leaked: ${parked}|"\n')
    if drift_round_2:
        # 第二輪的 record 語意被改掉 —— 於是「連續兩輪無漂移」不成立。
        target = root / FIXTURE_REL / "a3-round-2-record.md"
        target.write_text((root / FIXTURE_REL / "a3-drift-record.md").read_text(encoding="utf-8"),
                          encoding="utf-8")
    if drop_token:
        target = root / FIXTURE_REL / "a1-credential-shaped-record.md"
        text = target.read_text(encoding="utf-8")
        for token in _fixtures_mod.FAKE_CREDENTIAL_TOKENS:
            text = text.replace(token, "（已被移除）")
        target.write_text(text, encoding="utf-8")
    if shell_driver is not None:
        rel, body = shell_driver
        write(root / rel, body)
    return root


_fixtures_mod = _load(RUN_FIXTURES, "aidlc_selftest_fixtures")


def test_fixtures_baseline_is_green() -> None:
    """@purpose **對照組**：真實的 map／block ＋ 真實的 fixture ⇒ 綠（不轉呼上游）。
    @given 複製出來的暫存樹未做任何突變
    @step 跑 run-selftest-fixtures.py --skip-upstream | rc=0
    @pass 後面兩條突變測試可歸因
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td))
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("baseline rc", r.rc, 0)
        check_in("前提：A-1 有跑到", "CRED-1:field_value", r.stdout)
        check_in("前提：A-3 有跑到", "ROUND-1", r.stdout)


def test_a1_is_red_when_u1_leaks_the_credential() -> None:
    """@purpose **必測 #7**：U-1 的 output 含憑證樣式 ⇒ 紅。本 repo 是 public，Actions log 公開可讀。
    @given map.sh 被包裝成會把 Parked 理由漏進 scope_note
    @step 跑第一段驅動 | rc=1，失敗代號含 CRED-1:scope_note
    @step 讀訊息 | 含預期與實得
    @pass 六條防線之一真的會失敗
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), leak=True)
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("rc", r.rc, 1)
        check_true("CRED-1:scope_note 紅", "CRED-1:scope_note" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息含預期", "預期：不含", r.stdout)
        check_in("訊息含實得", "實得：", r.stdout)
        check_true("前提：其餘四個 output 沒被波及（洩漏確實只在 scope_note）",
                   [i for i in r.failed_ids() if i.startswith("CRED-1:")] == ["CRED-1:scope_note"],
                   str(r.failed_ids()))


def test_a1_premise_guard_fires_when_the_fixture_loses_its_tokens() -> None:
    """@purpose **必測 #8 的另一半**：fixture 裡的假憑證樣式被拿掉 ⇒ 紅（CRED-0）。沒有這道前提斷言，A-1 會變成一條掃不到東西的恆真斷言——output 當然不含它從來沒看過的字串。
    @given fixture 的四個假樣式被換成「（已被移除）」
    @step 跑第一段驅動 | CRED-0 紅
    @pass 空前提上的恆真通過不可能發生
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), drop_token=True)
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("rc", r.rc, 1)
        check_true("CRED-0 紅", "CRED-0" in r.failed_ids(), str(r.failed_ids()))


def test_a3_is_red_when_round_2_drifts() -> None:
    """@purpose **必測 #9**：第二輪產生漂移 ⇒ 紅。跨輪行為，既有的單輪驅動測不到。
    @given 第二輪的 record 被換成語意不同的那一份
    @step 跑第一段驅動 | ROUND-1 紅
    @step 檢視 ROUND-2 | 仍綠（比對本身在運作）
    @pass 「三欄相同」不是因為比對什麼都比不出來
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), drift_round_2=True)
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("rc", r.rc, 1)
        check_true("ROUND-1 紅", "ROUND-1" in r.failed_ids(), str(r.failed_ids()))
        check_true("ROUND-2 仍綠", "ROUND-2" not in r.failed_ids(), str(r.failed_ids()))


def test_an_empty_shell_upstream_driver_is_red() -> None:
    """@purpose **必測 #10**：被轉呼的驅動被換成「rc＝0 但零測試」的空殼 ⇒ 紅。只看 rc 會被空殼騙過，而空殼正是「刪光測試讓 CI 變綠」最省事的做法。
    @given aidlc-sync-map/run-fixtures.py 被換成 `sys.exit(0)`
    @step 跑第一段驅動（**不帶** --skip-upstream） | UPSTREAM:aidlc-sync-map/run-fixtures 紅
    @step 讀訊息 | 說明「解析不到它跑了幾條測試」
    @pass 轉呼是有斷言的轉呼
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(
            Path(td),
            shell_driver=(".github/actions/aidlc-sync-map/run-fixtures.py",
                          "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"))
        # 其餘三支不存在於這棵樹 —— 它們自己會以「找不到上游驅動」判紅，那是另一回事。
        r = run_checker(RUN_FIXTURES, root)
        ids = r.failed_ids()
        check("rc", r.rc, 1)
        check_true("UPSTREAM:aidlc-sync-map/run-fixtures 紅", "UPSTREAM:aidlc-sync-map/run-fixtures" in ids, str(ids))
        check_in("訊息說明解析不到測試數", "解析不到它跑了幾條測試", r.stdout)


def test_a_zero_test_upstream_driver_is_red() -> None:
    """@purpose 空殼的第二種寫法：格式對、數字是 0。`0 tests, 0 checks, 0 failures` 在「只看 rc」與「只看有沒有收尾行」兩種檢查下都會過。
    @given 被轉呼的驅動印出 0 tests, 0 checks, 0 failures 並 exit 0
    @step 跑第一段驅動 | UPSTREAM:aidlc-sync-map/run-fixtures 紅，訊息說明數字不足基準
    @pass 數字本身被斷言（M-3 起是「≥ 實跑取得的基準」，不再只是「> 0」）
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(
            Path(td),
            shell_driver=(".github/actions/aidlc-sync-map/run-fixtures.py",
                          "#!/usr/bin/env python3\nprint('0 tests, 0 checks, 0 failures')\n"))
        r = run_checker(RUN_FIXTURES, root)
        ids = r.failed_ids()
        check_true("UPSTREAM:aidlc-sync-map/run-fixtures 紅", "UPSTREAM:aidlc-sync-map/run-fixtures" in ids, str(ids))
        check_in("訊息說明數字不對", "預期：單元數 ≥", r.stdout)
        check_in("訊息指出實得低於基準", "< 基準", r.stdout)


def test_a_missing_upstream_driver_is_red() -> None:
    """@purpose 被轉呼的驅動整支被移走 ⇒ 紅，不得跳過。**不得因為它不在就跳過**——那會讓 A-2／A-4／A-5 在檔案被移走時靜默消失。
    @given 合成樹只有 map／block，沒有 forward／reverse 的驅動
    @step 跑第一段驅動 | UPSTREAM:aidlc-sync-forward/run-orchestration-tests 與 UPSTREAM:aidlc-sync-reverse/run-reverse-tests 都紅
    @pass 承接關係是可驗證的，不是文件上的宣稱
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td))
        r = run_checker(RUN_FIXTURES, root)
        ids = r.failed_ids()
        check_true("forward 那一項紅", "UPSTREAM:aidlc-sync-forward/run-orchestration-tests" in ids, str(ids))
        check_true("reverse 那一項紅", "UPSTREAM:aidlc-sync-reverse/run-reverse-tests" in ids, str(ids))
        check_in("訊息說明不得跳過", "不得因為它不在就跳過", r.stdout)


def test_a_missing_map_output_is_red_not_a_vacuous_pass() -> None:
    """@purpose **F6 迴歸**：`map.sh` 少吐一個 output ⇒ 紅。原實作用 `decision.get(name, "")` 取值，缺席的 output 取到空字串然後判「不含憑證樣式」而**通過**——reviewer 把 `emit scope_note` 換成 `:`，得到的是 `[通過] CRED-1:scope_note`。一條被刪掉的防線於是長得跟守住了一樣。
    @given map.sh 被包成不再吐出 scope_note
    @step 跑第一段驅動 | rc=1，CRED-0c 紅
    @step 讀訊息 | 指名缺的是 scope_note
    @step 檢視 CRED-1:scope_note | 它已經沒有存在的前提，但缺席本身有被指名
    @pass 存在性是本體斷言的前提，不是預設成立的東西
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), drop_output="scope_note")
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("rc", r.rc, 1)
        check_true("CRED-0c 紅", "CRED-0c" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息指名缺的是 scope_note", "scope_note", r.stdout)


def test_an_unexpected_map_output_is_red() -> None:
    """@purpose F6 的反向：`map.sh` 多吐一個 MAP_OUTPUTS 之外的 output ⇒ 紅。U-1 日後新增第六個 output 時，A-1 的掃描範圍必須大聲地少一項，而不是安靜地少一項。
    @given map.sh 被包成額外吐出一個 new_output
    @step 跑第一段驅動 | rc=1，CRED-0d 紅，訊息指名多出來的鍵
    @pass 掃描範圍與 U-1 的介面表綁在一起，兩邊漂移就紅
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), extra_output="new_output")
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("rc", r.rc, 1)
        check_true("CRED-0d 紅", "CRED-0d" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息指名多出來的鍵", "new_output", r.stdout)


def test_an_upstream_driver_missing_its_named_tests_is_red() -> None:
    """@purpose **F2 迴歸**：轉呼原本只斷言「總數 > 0」。reviewer 把 `run-reverse-tests.py` 中**逐字宣稱承接 A-4／A-5 的那三條**測試移除並清空本體，rc 仍為 0，而 CI log 那一行仍逐字宣稱它承接了 A-4／A-5。承接關係若不指名，就只是文件上的宣稱。
    @given map 的驅動被換成「數字漂亮、但沒有那幾條具名測試」的版本
    @step 跑第一段驅動（不帶 --skip-upstream） | UPSTREAM:aidlc-sync-map/run-fixtures 紅
    @step 讀訊息 | 逐一列出缺席的測試名稱
    @pass 「它真的跑了那幾條」是被斷言的，不是被假設的
    @story S-10
    """
    # 數字**取自 UPSTREAM_DRIVERS 的基準**（M-3 起有 floor 檢查）。寫死一組小數字的話，
    # floor 會先紅，這條測試就再也走不到它要驗的具名證據那一段——測試還是紅的，但紅的
    # 原因換了一個，而「它到底有沒有在驗具名證據」沒有人會發現。
    _map_floor = next(e[4] for e in _fixtures_mod.UPSTREAM_DRIVERS
                      if e[0].endswith("aidlc-sync-map/run-fixtures.py"))
    gutted = ("#!/usr/bin/env python3\n"
              "print('run-fixtures: %d 組測試，fixture 目錄 /tmp/x')\n"
              "print('  [ok] test_something_unrelated')\n"
              "print('')\n"
              "print('斷言數：%d　失敗：0')\n" % _map_floor)
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(
            Path(td),
            shell_driver=(".github/actions/aidlc-sync-map/run-fixtures.py", gutted))
        r = run_checker(RUN_FIXTURES, root)
        ids = r.failed_ids()
        check("rc", r.rc, 1)
        check_true("UPSTREAM:aidlc-sync-map/run-fixtures 紅", "UPSTREAM:aidlc-sync-map/run-fixtures" in ids, str(ids))
        check_in("訊息指名缺席的測試", "test_r1_1_first_match_wins", r.stdout)
        check_in("訊息說明缺的是具名測試", "缺少", r.stdout)


def test_every_named_upstream_test_actually_exists_upstream() -> None:
    """@purpose 具名清單若指向一個**不存在**的測試名稱，它會永遠紅——那是誤報而不是防線；若指向一個被改名的測試，同樣。所以清單本身要對著上游的真實檔案核對一次。
    @given UPSTREAM_DRIVERS 的每一項具名測試
    @step 在對應驅動的原始碼找 `def <name>(` | 全部找得到
    @pass 具名清單與上游同步，改名時這裡先紅
    @story S-10
    """
    for entry in _fixtures_mod.UPSTREAM_DRIVERS:
        rel, _covers, required, _summary_hint, _floors = entry
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for marker in required:
            name = marker.strip()
            if name.startswith("[ok]"):
                name = name[len("[ok]"):].strip()
                check_true("%s 有 def %s" % (rel, name),
                           re.search(r"^def %s\(" % re.escape(name), source, re.M) is not None,
                           name)
            else:
                check_in("%s 的證據字串在該驅動的輸出格式內" % rel, name.split()[-1], source)


def test_the_map_test_count_in_the_docstring_is_the_real_count() -> None:
    """@purpose **F9 迴歸**：`run-selftest-fixtures.py` 的說明寫「既有 39 條 map 測試無一條涉及憑證樣式」，實跑是 **38**。那個數字是本檔「A-1 為什麼要自己寫」的唯一依據——它沒被算過，而沒算過的數字與算過的數字在文件上長得一模一樣。
    @given run-selftest-fixtures.py 的說明段
    @step 抽出「N 條 map 測試」的 N | 與 aidlc-sync-map/run-fixtures.py 的 `def test_` 實數相同
    @pass 可以被計算的數字，由計算得到
    @story S-10
    """
    doc = RUN_FIXTURES.read_text(encoding="utf-8")
    claimed = re.findall(r"(\d+)\s*條 map 測試", doc)
    check("說明段恰好宣稱一次 map 測試數", len(claimed), 1)
    real = len(re.findall(r"^def test_", (ACTIONS / "aidlc-sync-map" / "run-fixtures.py")
                          .read_text(encoding="utf-8"), re.M))
    check_true("前提：真的數得到測試", real > 0, str(real))
    if claimed:
        check("宣稱的 map 測試數 ＝ 實數", int(claimed[0]), real)


def test_the_fixture_dir_is_resolved_by_glob_not_a_hardcoded_intent() -> None:
    """@purpose **F10 迴歸**：fixture 目錄原本寫死單一 intent record（`260822-gh-projects-sync`），與 workflow 觸發 allowlist 的通用 glob（`aidlc/spaces/*/intents/*/.test-fixtures/**`）不一致。改 record 名稱時，觸發照舊而驅動找不到 fixture。
    @given fixture 放在一個**不同名**的 intent record 之下
    @step 跑第一段驅動 | rc=0（照樣找得到）
    @step 再放第二份 fixture 到另一個 record | rc=2，訊息指名兩個都找到、拒絕猜
    @pass 解析方式與觸發設定同一條 glob
    @story S-10
    """
    other = "aidlc/spaces/default/intents/990101-somewhere-else/.test-fixtures"
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), fixture_rel=other)
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("改了 record 名稱仍找得到", r.rc, 0)
        check_in("訊息說出它用的是哪一個目錄", "990101-somewhere-else", r.stdout)
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), extra_fixture_rel=other)
        r = run_checker(RUN_FIXTURES, root, "--skip-upstream")
        check("兩個都找到時拒絕猜", r.rc, 2)
        check_in("第一行可分辨為外部錯誤", EXTERNAL_PREFIX, r.stderr)


def test_missing_fixture_dir_is_an_external_error() -> None:
    """@purpose fixture 目錄不存在 ⇒ 外部錯誤，不得視為通過。
    @given 空的暫存樹
    @step 跑第一段驅動 | rc=2、第一行 EXTERNAL-ERROR:
    @pass 沒有 fixture 就沒有 A-1／A-3，這件事要說出來
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        r = run_checker(RUN_FIXTURES, Path(td), "--skip-upstream")
        check("rc", r.rc, 2)
        check_in("第一行可分辨為外部錯誤", EXTERNAL_PREFIX, r.stderr)


def test_the_a1_fixture_passes_the_repo_contract() -> None:
    """@purpose **必測 #8**：A-1 的 fixture 不得觸發 `validate_repo_contract.py`。fixture 本身讓 CI 紅會讓整件事倒過來——一個為了防洩漏而存在的檔案變成紅燈的原因。
    @given repo 現況（fixture 已在版控路徑下）
    @step 跑 scripts/validate_repo_contract.py | rc=0
    @step 逐一比對 FORBIDDEN_CONTENT_PATTERNS | fixture 檔內容不含任何一個
    @pass 假樣式結構相同但不觸發掃描器
    @story S-10
    """
    try:
        proc = subprocess.run([sys.executable, "scripts/validate_repo_contract.py"],
                              cwd=str(REPO_ROOT), capture_output=True, text=True,
                              timeout=CHECKER_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        proc = _Timeout("scripts/validate_repo_contract.py", CHECKER_TIMEOUT_S)
    check("validate_repo_contract.py rc（rc=2 代表它掛住了，見 stderr）",
          proc.returncode, 0)
    contract = _load(REPO_ROOT / "scripts" / "validate_repo_contract.py", "aidlc_repo_contract")
    patterns = contract.FORBIDDEN_CONTENT_PATTERNS
    check_true("前提：掃描器真的有樣式可比對", len(patterns) > 0, str(patterns))
    for path in sorted((REPO_ROOT / FIXTURE_REL).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        hits = [p for p in patterns if p in text]
        check_true("%s 不含任何 FORBIDDEN_CONTENT_PATTERNS" % path.name, not hits, str(hits))


# ==========================================================================
# workflow 的靜態斷言（對**真實**的 aidlc-sync-selftest.yml）
# ==========================================================================
def _selftest_doc():
    import yaml
    return yaml.safe_load(SELFTEST_YML.read_text(encoding="utf-8"))


def _selftest_triggers(doc):
    return doc.get("on", doc.get(True))


def test_stage_2_cannot_run_when_stage_1_is_red() -> None:
    """@purpose **必測 #11**：第一段紅 ⇒ 第二段不跑。`performance-requirements.md` 的核心設計——一個 fixture 級的錯誤若以「端到端失敗」的面貌出現，診斷成本高一個量級。
    @given 真實的 aidlc-sync-selftest.yml
    @step 讀第二段的 needs | 含第一段的 job id
    @step 讀第二段 job 層的 if | 不存在，或不含 always()／!cancelled()（那兩者會覆寫 needs 的跳過語意）
    @pass 兩段順序不是靠註解維持的
    @story S-10
    """
    doc = _selftest_doc()
    jobs = doc.get("jobs") or {}
    check_true("前提：兩個 job 都在", {"fixtures", "endtoend"} <= set(jobs), str(sorted(jobs)))
    needs = jobs["endtoend"].get("needs")
    needs_list = [needs] if isinstance(needs, str) else list(needs or [])
    check_true("第二段 needs 第一段", "fixtures" in needs_list, str(needs_list))
    cond = str(jobs["endtoend"].get("if", "")).lower()
    check_true("第二段 job 層沒有會覆寫 needs 的條件",
               "always()" not in cond and "cancelled()" not in cond, repr(cond))


def test_cleanup_runs_on_the_failure_path() -> None:
    """@purpose **必測 #12** ＋ R-4：清理必須以 `if: always()` 宣告。殘留的後果不是髒資料而是**假紅燈**——下一次執行會因為看到不屬於自己的 item 而失敗，於是有人開始把自我測試的紅燈當成雜訊。
    @given 真實的 workflow
    @step 找第二段裡名稱含 Clean up 的 step | 它的 if 是 always()
    @step 檢視它的腳本 | 清理失敗是紅燈（exit 1）且訊息含殘留 item 的識別資訊
    @pass 一個會誤報的閘門，比沒有閘門更快失去作用
    @story S-10
    """
    jobs = _selftest_doc()["jobs"]
    steps = jobs["endtoend"]["steps"]
    cleanup = [s for s in steps if "clean up" in str(s.get("name", "")).lower()]
    check("清理步驟恰有一個", len(cleanup), 1)
    if cleanup:
        check("清理步驟的 if", str(cleanup[0].get("if", "")).strip(), "always()")
        body = cleanup[0].get("run", "")
        check_true("清理失敗是紅燈", "exit 1" in body, body[:400])
        check_true("訊息含殘留 item 的識別資訊",
                   "${BINDING}" in body and "${INTENT_ID}" in body, body[:400])
        check_true("動手前先核對是本次執行建立的那一則",
                   "拒絕清理" in body, body[:800])


def test_allowlist_excludes_sync_state_json() -> None:
    """@purpose **必測 #15**：真實 workflow 的 allowlist 不含 sync-state.json。這是關係 2 的前提，也是「反向 PR 不觸發自我測試」的全部實作。
    @given 真實的 workflow
    @step 讀 on.pull_request.paths | 沒有任何一條與寫入 glob 相交
    @step 讀 allowlist | 涵蓋四支 workflow 的 .yml、composite action、fixture 集
    @pass 觸發集合與排除集合無交集
    @story S-10
    """
    trig = _selftest_triggers(_selftest_doc())
    paths = list((trig.get("pull_request") or {}).get("paths") or [])
    check_true("前提：allowlist 非空", bool(paths), str(paths))
    overlaps = [p for p in paths if _cpr.globs_may_intersect(p, WRITE_GLOB)]
    check("allowlist 與寫入 glob 無交集", overlaps, [])
    check_true("allowlist 指向 .yml 而不是 .md／.lock.yml（N:C-3 的更正）",
               any(p.endswith("aidlc-sync-*.yml") for p in paths), str(paths))
    # N:C-3 的釘子只約束**同步機制自己**那幾條：它們是純 Actions，指向 `.md`／`.lock.yml`
    # 會讓觸發永遠不成立。四支 gh-aw 承載體的 `.md`／`.lock.yml` 是 F7 刻意加進來的、指向
    # 真實存在的檔案，不在這條約束內——這兩件事講的是不同的檔案集合（與
    # check-agentic-steps.py 對 LOCK-1 的說明同一個道理）。
    sync_own = [p for p in paths if "aidlc-sync" in p]
    check_true("前提：allowlist 真的有同步機制自己的條目", bool(sync_own), str(paths))
    check_true("同步機制自己的條目不指向 .md／.lock.yml",
               not any(p.endswith(".md") or p.endswith(".lock.yml") for p in sync_own),
               str(sync_own))
    check_true("allowlist 涵蓋 fixture 集（改壞 fixture 等於改壞斷言）",
               any(".test-fixtures" in p for p in paths), str(paths))


def test_no_concurrency_group() -> None:
    """@purpose **必測 #16**：本單元刻意沒有 concurrency group（`scalability-requirements.md:42`）。這與 U-8 的 P-2 相反，容易被「對齊其他同步 workflow」順手加回去。
    @given 真實的 workflow
    @step 讀頂層鍵 | 沒有 concurrency
    @pass 測試 item 是本次執行專屬的，並行的兩個 PR 寫的是不同的 item
    @story S-10
    """
    doc = _selftest_doc()
    check_true("沒有頂層 concurrency", "concurrency" not in doc, str(sorted(str(k) for k in doc)))
    for name, job in (doc.get("jobs") or {}).items():
        check_true("job %s 也沒有 concurrency" % name, "concurrency" not in job, str(sorted(job)))


def test_both_jobs_have_a_timeout() -> None:
    """@purpose 沒有上界的預設是 GitHub 的 360 分鐘，而這個 repo 已經被那個預設咬過一次（PR #510，單一 PR 約七小時 runner、零測試執行）。
    @given 真實的 workflow
    @step 讀兩個 job 的 timeout-minutes | 都存在且 ≤ 10
    @pass 純 Actions 讓 timeout-minutes 正常生效（gh-aw v0.81.6 會靜默丟棄它）
    @story S-10
    """
    for name, job in (_selftest_doc().get("jobs") or {}).items():
        value = job.get("timeout-minutes")
        check_true("job %s 有 timeout-minutes" % name, isinstance(value, int), repr(value))
        if isinstance(value, int):
            check_true("job %s 的 timeout-minutes ≤ 10（實得 %d）" % (name, value), value <= 10)


def test_stage_1_uses_no_credential() -> None:
    """@purpose 第一段「不發任何 API 寫入請求」（[ad:services.md] S-D），也是它必須先跑的理由之一——**沒有憑證就沒有洩漏面**。
    @given 真實的 workflow
    @step 掃第一段所有 step 的 env 與 run | 不出現 secrets. 參照
    @pass 憑證只在第二段
    @story S-10
    """
    jobs = _selftest_doc()["jobs"]
    blob = ""
    for step in jobs["fixtures"]["steps"]:
        blob += str(step.get("env", "")) + str(step.get("run", "")) + str(step.get("with", ""))
    check_true("第一段不參照任何 secrets", "secrets." not in blob, blob[:400])
    check_true("前提：第一段真的有步驟", len(jobs["fixtures"]["steps"]) >= 3,
               str(len(jobs["fixtures"]["steps"])))


def test_second_stage_preflight_names_the_missing_dependency() -> None:
    """@purpose `business-logic-model.md` 的錯誤表逐字要求「訊息須指出是哪一個」。這裡把它提前到進場：與其讓它在更深的地方以更難懂的方式失敗，不如第一步就講清楚缺的是憑證還是測試 Project。
    @given 真實 workflow 的 preflight step
    @step 抽出它的腳本以 bash 執行，兩個變數都給空值 | proceed=false，且輸出同時指名兩個
    @step 只缺 Project 編號 | proceed=false，輸出指名 Project 編號、不指名 token
    @step 兩者都給 | proceed=true
    @pass 「缺哪一個」是可觀察的，不是要人去猜
    @story S-10
    """
    script = _step_script("endtoend", "preflight")
    both = _bash(script, SYNC_TOKEN="", TEST_PROJECT_NUMBER="")
    check("兩者皆缺 → proceed=false", both["outputs"].get("proceed"), "false")
    check_in("指名 token", "AIDLC_SYNC_TOKEN", both["summary"])
    check_in("指名 Project 編號", "AIDLC_SELFTEST_PROJECT_NUMBER", both["summary"])

    only_project = _bash(script, SYNC_TOKEN="tok", TEST_PROJECT_NUMBER="")
    check("只缺 Project → proceed=false", only_project["outputs"].get("proceed"), "false")
    check_in("指名 Project 編號", "AIDLC_SELFTEST_PROJECT_NUMBER", only_project["summary"])
    check_not_in("不指名 token（它沒缺）", "AIDLC_SYNC_TOKEN", only_project["summary"])

    ok = _bash(script, SYNC_TOKEN="tok", TEST_PROJECT_NUMBER="23")
    check("兩者皆有 → proceed=true", ok["outputs"].get("proceed"), "true")
    check("兩者皆有時不寫 summary", ok["summary"].strip(), "")


# ==========================================================================
# SEC-3：把守衛腳本抽出來實際執行
# ==========================================================================
def _step_script(job_id, step_id):
    """從真實 workflow 抽出某個 step 的 run 腳本。

    以 `id:` 定位而不是位置：step 被搬動時測試仍指得到同一段腳本；step 被改名時
    這裡會丟例外而不是靜默地什麼都沒測。
    """
    jobs = _selftest_doc()["jobs"]
    for step in jobs[job_id]["steps"]:
        if step.get("id") == step_id and isinstance(step.get("run"), str):
            return step["run"]
    raise AssertionError(
        "在 job %r 找不到 id: %r 的 step。這支測試靠它的 id 定位受測腳本；"
        "若 step 被改名，請同步改這裡，不要讓測試靜默地什麼都沒測。" % (job_id, step_id)
    )


def _bash(script, *, cwd=None, path_prefix=None, **env_extra):
    """跑一段 workflow step 腳本，回傳 rc、stdout/stderr、$GITHUB_OUTPUT 與 summary。

    **`bash -e`，不是 `bash`。** 這一點是這個 helper 最重要的細節：GitHub Actions 的
    `run:` 預設 shell 是 `bash -e {0}`（`shell:` 未指定、`defaults.run.shell` 未指定時），
    而本 workflow 全檔兩者皆未指定。腳本裡的 `set -uo pipefail` **關不掉 `-e`**——`set -o`
    只能開，關要用 `set +e`。

    用 `bash -c`（無 `-e`）驅動測試等於在一個與 CI **相反**的環境下驗證：`cmd; rc=$?` 這種
    寫法在測試裡拿得到 rc、在 CI 上整個 step 當場結束。reviewer iteration 1 的 F4 就是這個
    落差——三段腳本的診斷訊息與 R-1.3 的斷言在 CI 上全部不可達，而測試全綠。
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out_file = td / "gh_output"
        sum_file = td / "gh_summary"
        out_file.touch()
        sum_file.touch()
        env = dict(os.environ)
        env.update({"GITHUB_OUTPUT": str(out_file), "GITHUB_STEP_SUMMARY": str(sum_file)})
        if path_prefix is not None:
            env["PATH"] = "%s%s%s" % (path_prefix, os.pathsep, env.get("PATH", ""))
        env.update({k: v for k, v in env_extra.items()})
        try:
            proc = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True,
                                  text=True, cwd=str(cwd) if cwd is not None else None,
                                  timeout=SHELL_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            # 這一支以**真實 shell** 執行從 workflow 抽出來的腳本，而那些腳本會呼叫假的
            # `gh`。假 `gh` 若等一個不會來的輸入，整套測試會掛住到 job 逾時為止。
            proc = _Timeout("抽出腳本（bash -e -c）", SHELL_TIMEOUT_S)
        outputs = {}
        for line in out_file.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                outputs[key] = value
        return {"rc": proc.returncode, "out": proc.stdout + proc.stderr,
                "outputs": outputs, "summary": sum_file.read_text(encoding="utf-8")}


def test_sec3_refuses_the_production_board_in_every_normalised_form() -> None:
    """@purpose **必測 #14**：SEC-3 的守衛以整數正規化後比對。同一份憑證同時寫得了 #16，**隔離只靠這個設定值、不靠權限**——`016`／` 16`／`0016`／`+16` 在 int() 之下全部等於 16、在字串比對之下全部不等於 "16"，於是守衛放行、查詢卻打到正式看板。
    @given 真實 workflow 的 sec3-guard step 腳本
    @step 以五種等價寫法各跑一次 | 全部 exit 4 且訊息含 REFUSE
    @step 以測試看板編號跑 | exit 0
    @step 以無法解析的值跑 | exit 4（fail closed）
    @pass 這道防線擋得住它唯一要擋的那件事
    @story S-10
    """
    script = _step_script("endtoend", "sec3-guard")
    check_true("前提：守衛不是用 bash 算術正規化的（$((016)) 是八進位 14）",
               "python3" in script, script[:200])
    for value in ("16", "016", " 16", "16 ", "0016", "+16"):
        r = _bash(script, AIDLC_PROJECT_NUMBER=value)
        check("AIDLC_PROJECT_NUMBER=%r 必須被拒絕（exit 4）" % value, r["rc"], 4)
        check_in("拒絕訊息含 REFUSE（%r）" % value, "REFUSE", r["out"])
    for value in ("23", "1", "999"):
        r = _bash(script, AIDLC_PROJECT_NUMBER=value)
        check("AIDLC_PROJECT_NUMBER=%r 應通過" % value, r["rc"], 0)
    for value in ("", "abc", "16a", "1.6", "０１６"):
        r = _bash(script, AIDLC_PROJECT_NUMBER=value)
        check("無法解析的 %r 必須 fail closed（exit 4）" % value, r["rc"], 4)


def test_sec3_forbidden_number_is_a_named_constant() -> None:
    """@purpose 這道防線是使用者明示的硬約束，它的值不該要靠 grep 才找得到——形式沿用 `aidlc-sync-forward/run-live-tests.py` 已修正的那一份，不自創第二種寫法。
    @given sec3-guard 的腳本
    @step 掃腳本 | 含具名常數 LIVE_FORBIDDEN_PROJECT 且它的值是 16
    @pass 兩處寫法一致，未來要改只有一個地方
    @story S-10
    """
    script = _step_script("endtoend", "sec3-guard")
    check_in("具名常數存在", "LIVE_FORBIDDEN_PROJECT", script)
    check_true("常數值是 16",
               re.search(r"LIVE_FORBIDDEN_PROJECT\s*=\s*16\b", script) is not None, script[:600])
    live = (ACTIONS / "aidlc-sync-forward" / "run-live-tests.py").read_text(encoding="utf-8")
    check_true("前提：U-6 的 live runner 用的是同一個常數名與值",
               re.search(r"LIVE_FORBIDDEN_PROJECT\s*=\s*16\b", live) is not None, "")


# ==========================================================================
# 第二段的腳本：實際跑起來（reviewer iteration 1 的 F4／F13）
#
# 這一整節在 iteration 1 之前**不存在**：第二段除了 preflight 與 SEC-3 之外沒有任何一行
# 被執行過，於是「建立 item 失敗的診斷」「往返不符的 ASSERTION-FAILED」「R-1.3 的 403」
# 三段在 `bash -e` 之下全部不可達，而沒有東西會發現。
# ==========================================================================
FAKE_BOARD_SH = """#!/usr/bin/env bash
# 假的 board.sh：由環境變數決定成功或失敗，以及回讀要回什麼值。
case "${AIDLC_OPERATION}" in
  create_item)
    [ "${FAKE_CREATE_RC:-0}" = "0" ] || exit "${FAKE_CREATE_RC}"
    echo "binding=${FAKE_BINDING:-4242}" >> "${GITHUB_OUTPUT}"
    ;;
  write_status)
    [ "${FAKE_WRITE_RC:-0}" = "0" ] || exit "${FAKE_WRITE_RC}"
    ;;
  read_item)
    [ "${FAKE_READ_RC:-0}" = "0" ] || exit "${FAKE_READ_RC}"
    echo "status=${FAKE_READ_STATUS:-In progress}" >> "${GITHUB_OUTPUT}"
    ;;
  *)
    echo "unexpected operation ${AIDLC_OPERATION}" >&2
    exit 9
    ;;
esac
exit 0
"""


def _stage2_sandbox(td: Path, *, gh_body=None) -> Path:
    """一棵能跑第二段腳本的暫存樹：假 board.sh ＋（可選）假 gh。"""
    board = td / ".github" / "actions" / "aidlc-sync-board" / "board.sh"
    write(board, FAKE_BOARD_SH)
    board.chmod(0o755)
    if gh_body is not None:
        gh = td / "bin" / "gh"
        write(gh, gh_body)
        gh.chmod(0o755)
    return td


def test_the_step_harness_matches_githubs_default_shell() -> None:
    """@purpose 這一節的每一條測試都建立在「`_bash` 跑的東西與 CI 跑的東西一樣」之上，而那**不是**自動成立的：iteration 1 的 `_bash` 用 `bash -c`（無 `-e`），於是三段腳本在測試裡拿得到 rc、在 CI 上整個 step 當場結束——測試全綠而斷言全部不可達。所以先把這個前提本身變成一條斷言。
    @given `_bash` 與真實 workflow
    @step 用 `_bash` 跑 `false; echo reached` | rc≠0 且「reached」沒有被印出來（＝`-e` 真的生效）
    @step 掃 workflow 的每一個 step | 沒有任何 `shell:`
    @step 掃 workflow 頂層與 job 層 | 沒有 `defaults.run.shell`
    @pass 「CI 的預設 shell 是 `bash -e {0}`」這件事，在兩端都被釘住
    @story S-10
    """
    r = _bash("false\necho reached\n")
    check_true("harness 的 -e 生效（rc 非零）", r["rc"] != 0, repr(r["rc"]))
    check_not_in("harness 的 -e 生效（後續指令沒有執行）", "reached", r["out"])

    doc = _selftest_doc()
    check_true("workflow 頂層沒有 defaults.run.shell",
               "shell" not in ((doc.get("defaults") or {}).get("run") or {}),
               str(doc.get("defaults")))
    for jname, job in (doc.get("jobs") or {}).items():
        check_true("job %s 沒有 defaults.run.shell" % jname,
                   "shell" not in ((job.get("defaults") or {}).get("run") or {}),
                   str(job.get("defaults")))
        for step in job.get("steps") or []:
            check_true("job %s 的 step %r 沒有自訂 shell"
                       % (jname, step.get("name") or step.get("id")),
                       "shell" not in step, str(step.get("shell")))


def test_stage_2_create_step_says_which_dependency_failed() -> None:
    """@purpose **F4 迴歸（建立 item）**：`business-logic-model.md` 的錯誤表逐字要求「第二段建立測試 item 失敗……訊息須指出是哪一個」。GitHub 的預設 shell 是 `bash -e {0}`，而腳本裡的 `set -uo pipefail` **關不掉 `-e`**——原本的 `bash "${BOARD_SH}"` 後接 `rc=$?` 在 CI 上根本走不到第二行，錯誤表要求的訊息一個字都印不出來。
    @given 假的 board.sh 對 create_item 回非零；以 `bash -e` 執行真實 workflow 的 create 腳本
    @step 跑腳本 | rc=1
    @step 讀輸出 | 含「建立測試 item 失敗」、目標 owner/number 與 intent_id
    @pass 診斷在 CI 的實際 shell 語意下可達
    @story S-10
    """
    script = _step_script("endtoend", "create")
    with tempfile.TemporaryDirectory() as td:
        root = _stage2_sandbox(Path(td))
        r = _bash(script, cwd=root, FAKE_CREATE_RC="7",
                  AIDLC_PROJECT_OWNER="opendiamonds", AIDLC_PROJECT_NUMBER="23",
                  AIDLC_FIELD_NAME="AI-DLC Stage",
                  GITHUB_RUN_ID="111", GITHUB_RUN_ATTEMPT="2")
        check("rc", r["rc"], 1)
        check_in("訊息說明建立失敗", "建立測試 item 失敗", r["out"])
        check_in("訊息指出目標 Project", "opendiamonds/projects/23", r["out"])
        check_in("訊息指出 intent_id", "aidlc-sync-selftest-111-2", r["out"])


def test_stage_2_create_step_publishes_the_binding_on_success() -> None:
    """@purpose 成功路徑同樣要在 `bash -e` 下走得完：binding 與 intent_id 必須真的寫進 `$GITHUB_OUTPUT`，否則後面兩個 step 的 `if:` 條件永遠為假、整段靜默空轉。
    @given 假 board.sh 回 binding=4242
    @step 跑 create 腳本 | rc=0
    @step 讀 $GITHUB_OUTPUT | binding=4242、intent_id 帶 run id 與 attempt
    @pass 成功與失敗兩條路徑都被執行過
    @story S-10
    """
    script = _step_script("endtoend", "create")
    with tempfile.TemporaryDirectory() as td:
        root = _stage2_sandbox(Path(td))
        r = _bash(script, cwd=root,
                  AIDLC_PROJECT_OWNER="opendiamonds", AIDLC_PROJECT_NUMBER="23",
                  AIDLC_FIELD_NAME="AI-DLC Stage",
                  GITHUB_RUN_ID="111", GITHUB_RUN_ATTEMPT="2")
        check("rc", r["rc"], 0)
        check("binding", r["outputs"].get("binding"), "4242")
        check("intent_id", r["outputs"].get("intent_id"), "aidlc-sync-selftest-111-2")


def test_stage_2_round_trip_separates_external_error_from_assertion_failure() -> None:
    """@purpose **F13**：第二段自己的 `EXTERNAL-ERROR:`／`ASSERTION-FAILED:` 前綴在 iteration 1 之前沒有任何測試碰過，而它們在 `bash -e` 之下全部不可達（`bash "${BOARD_SH}"` 非零即當場結束 step）。兩類紅燈的意義相反：一類要修 code，一類要修環境或重跑。
    @given 假 board.sh：①write_status 非零 ②寫入成功但回讀值不同 ③兩者皆正常
    @step 情境① | rc=1 且輸出以 EXTERNAL-ERROR: 標示
    @step 情境② | rc=1 且輸出以 ASSERTION-FAILED: 標示，含預期與實得
    @step 情境③ | rc=0，輸出「往返一致」
    @pass 兩類紅燈在 CI 上長得不一樣，且都真的印得出來
    @story S-10
    """
    script = _step_script("endtoend", "round-trip")
    with tempfile.TemporaryDirectory() as td:
        root = _stage2_sandbox(Path(td))
        external = _bash(script, cwd=root, BINDING="4242", FAKE_WRITE_RC="5",
                         AIDLC_PROJECT_OWNER="opendiamonds", AIDLC_PROJECT_NUMBER="23",
                         AIDLC_FIELD_NAME="AI-DLC Stage")
        check("外部錯誤 rc", external["rc"], 1)
        check_in("外部錯誤前綴", EXTERNAL_PREFIX, external["out"])
        check_not_in("外部錯誤不得被標成斷言失敗", ASSERT_PREFIX, external["out"])

        mismatch = _bash(script, cwd=root, BINDING="4242", FAKE_READ_STATUS="Ready",
                         AIDLC_PROJECT_OWNER="opendiamonds", AIDLC_PROJECT_NUMBER="23",
                         AIDLC_FIELD_NAME="AI-DLC Stage")
        check("斷言失敗 rc", mismatch["rc"], 1)
        check_in("斷言失敗前綴", ASSERT_PREFIX, mismatch["out"])
        check_in("含預期", "預期：In progress", mismatch["out"])
        check_in("含實得", "實得：Ready", mismatch["out"])

        ok = _bash(script, cwd=root, BINDING="4242",
                   AIDLC_PROJECT_OWNER="opendiamonds", AIDLC_PROJECT_NUMBER="23",
                   AIDLC_FIELD_NAME="AI-DLC Stage")
        check("往返一致 rc", ok["rc"], 0)
        check_in("往返一致訊息", "往返一致", ok["out"])


def test_r13_probe_asserts_403_instead_of_dying_on_it() -> None:
    """@purpose **F4 的第三處，方向是反的**：`gh api` 對 403 會 exit 1，於是在 `bash -e` 之下**通過路徑**（真的收到 403）當場殺掉 step，而寫入**成功**時才走得到 `ASSERTION-FAILED`。這條斷言在補上範圍外目標之後仍永遠不可能綠。
    @given 假 gh：①回 403 ②回 201
    @step 情境①（403，這是通過條件） | rc=0，輸出「R-1.3 通過」
    @step 情境②（201，寫入沒被拒絕） | rc=1，ASSERTION-FAILED 含預期 403 與實得 201
    @step 未設定範圍外目標 | rc=0 且 summary 說明為什麼沒執行
    @pass 斷言的方向與它宣稱的一致
    @story S-10
    """
    script = _step_script("endtoend", "r13-out-of-scope")
    forbidden = ("#!/usr/bin/env bash\n"
                 "printf 'HTTP/2.0 403 Forbidden\\r\\n'\n"
                 "echo 'gh: Resource not accessible' >&2\n"
                 "exit 1\n")
    allowed = ("#!/usr/bin/env bash\n"
               "printf 'HTTP/2.0 201 Created\\r\\n'\n"
               "exit 0\n")
    with tempfile.TemporaryDirectory() as td:
        root = _stage2_sandbox(Path(td), gh_body=forbidden)
        r = _bash(script, cwd=root, path_prefix=str(root / "bin"),
                  GH_TOKEN="tok", OUT_OF_SCOPE_REPO="someorg/somewhere-else")
        check("403 是通過條件，rc 必須是 0", r["rc"], 0)
        check_in("通過訊息", "R-1.3 通過", r["out"])
    with tempfile.TemporaryDirectory() as td:
        root = _stage2_sandbox(Path(td), gh_body=allowed)
        r = _bash(script, cwd=root, path_prefix=str(root / "bin"),
                  GH_TOKEN="tok", OUT_OF_SCOPE_REPO="someorg/somewhere-else")
        check("寫入沒被拒絕 ⇒ 斷言失敗", r["rc"], 1)
        check_in("斷言失敗前綴", ASSERT_PREFIX, r["out"])
        check_in("含預期", "預期：HTTP 403", r["out"])
        check_in("含實得", "201", r["out"])
    with tempfile.TemporaryDirectory() as td:
        root = _stage2_sandbox(Path(td), gh_body=forbidden)
        r = _bash(script, cwd=root, path_prefix=str(root / "bin"),
                  GH_TOKEN="tok", OUT_OF_SCOPE_REPO="")
        check("沒有已定案的範圍外目標 ⇒ 跳過而非假裝有斷言", r["rc"], 0)
        check_in("summary 說明為什麼沒執行", "R-1.3（403）未執行", r["summary"])


def test_stage_2_only_runs_on_workflow_dispatch() -> None:
    """@purpose **F8（安全）**：`paths` allowlist 涵蓋 `.github/actions/aidlc-sync-*/**`，而第二段 checkout PR head 之後 `bash board.sh`、環境帶 `secrets.AIDLC_SYNC_TOKEN`（組織層 Projects 讀寫 ＋ contents／issues／PR write）——**一個修改 `board.sh` 的 PR，會讓自我測試用那份憑證執行它自己改的腳本**。裁決為保守收窄：第二段只在 workflow_dispatch 執行；第一段維持 pull_request（它是閘門，且不碰憑證）。
    @given 真實 workflow
    @step 讀第二段 job 的 if | 含 github.event_name == 'workflow_dispatch'
    @step 讀第一段 job 的 if | 不存在（pull_request 照跑）
    @step 確認 needs 仍在 | 收窄沒有把兩段順序一起改掉
    @pass 收窄是減少能力，可由 gate 隨時放寬；反之不然
    @story S-10
    """
    jobs = _selftest_doc()["jobs"]
    cond = str(jobs["endtoend"].get("if", ""))
    check_true("第二段的 if 綁定 workflow_dispatch",
               "github.event_name" in cond and "workflow_dispatch" in cond, repr(cond))
    check_true("第一段沒有 if（pull_request 照跑）", "if" not in jobs["fixtures"],
               repr(jobs["fixtures"].get("if")))
    check_true("needs 仍在（兩段順序沒被一起改掉）",
               "fixtures" in ([jobs["endtoend"].get("needs")]
                              if isinstance(jobs["endtoend"].get("needs"), str)
                              else list(jobs["endtoend"].get("needs") or [])),
               repr(jobs["endtoend"].get("needs")))


def test_stage_1_pins_its_python_instead_of_trusting_the_runner_image() -> None:
    """@purpose **F14**：三支檢查器 `import yaml`，而「PyYAML 在 GitHub runner 上可用」這件事本 repo 從未驗證過（三個 `import yaml` 的檔沒有任何 workflow 執行過）。原本的 fallback `python3 -m pip install pyyaml` 在 ubuntu-24.04 的系統 Python（PEP 668）會以 `externally-managed-environment` 失敗——那是一個只在 runner 上才會出現、而且會讓整段第一段掛掉的失敗。
    @given 真實 workflow 的第一段
    @step 找 actions/setup-python | 存在且釘住 python-version
    @step 檢視安裝 PyYAML 的步驟 | 在 setup-python 之後
    @pass 相依的取得方式不靠猜 runner 映像有什麼
    @story S-10
    """
    steps = _selftest_doc()["jobs"]["fixtures"]["steps"]
    setup = [i for i, s in enumerate(steps)
             if str(s.get("uses", "")).startswith("actions/setup-python@")]
    check_true("第一段有 actions/setup-python", bool(setup),
               str([s.get("uses") or s.get("name") for s in steps]))
    if setup:
        with_block = steps[setup[0]].get("with") or {}
        check_true("釘住 python-version", bool(str(with_block.get("python-version", "")).strip()),
                   str(with_block))
    yaml_steps = [i for i, s in enumerate(steps) if "pyyaml" in str(s.get("run", "")).lower()]
    check_true("安裝／檢查 PyYAML 的步驟排在 setup-python 之後",
               bool(setup) and bool(yaml_steps) and min(yaml_steps) > setup[0],
               "setup=%r yaml=%r" % (setup, yaml_steps))


# ==========================================================================
# 失敗語意（reliability-requirements.md）
# ==========================================================================
def test_the_two_kinds_of_red_are_distinguishable_on_the_first_line() -> None:
    """@purpose **必測 #13**：斷言失敗與外部錯誤必須在 exit 訊息的**第一行**即可分辨。若兩者在 CI 上長得一樣，人會學會「紅了就重跑」——而那正是第一類紅燈最不該得到的反應。
    @given 兩種紅燈各造一次（同一支檢查器）
    @step 缺 workflow 目錄 | stderr 第一行以 EXTERNAL-ERROR: 開頭
    @step 邏輯 workflow 缺一支 | stderr 第一行以 ASSERTION-FAILED: 開頭
    @step 檢視斷言失敗的報告 | 含「預期：」與「實得：」
    @pass 兩類紅燈的意義相反，長相也必須不同
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        external = run_checker(CHECK_AGENTIC, Path(td))
    check_true("外部錯誤的第一行",
               external.stderr.splitlines()[0].startswith(EXTERNAL_PREFIX) if external.stderr else False,
               external.stderr)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root, logical=("forward", "reconcile", "selftest"))
        assertion = run_checker(CHECK_AGENTIC, root)
    check_true("斷言失敗的第一行",
               assertion.stderr.splitlines()[0].startswith(ASSERT_PREFIX) if assertion.stderr else False,
               assertion.stderr)
    check_true("兩者的第一行不同", external.stderr.splitlines()[0] != assertion.stderr.splitlines()[0])
    check_in("斷言失敗的報告含預期", "預期：", assertion.stdout)
    check_in("斷言失敗的報告含實得", "實得：", assertion.stdout)


def test_every_failure_message_carries_expected_and_actual() -> None:
    """@purpose R-1.1 逐字：「一個只印 FAILED 的斷言，在三個 Bolt 之後沒有人能從 CI log 判斷是映射改錯了還是 fixture 過期了」。**斷言訊息必須含預期值與實得值兩者**。
    @given 三支檢查器各造一次真實的斷言失敗
    @step 逐一檢視 [失敗] 之後的訊息 | 每一次失敗的報告都含「預期：」與「實得：」
    @pass 不是抽樣，是每一支都驗
    @story S-10
    """
    cases = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root, logical=("forward", "reconcile", "selftest"))
        cases.append(("check-agentic-steps", run_checker(CHECK_AGENTIC, root)))
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td), skip_carrier="lint-fix")
        cases.append(("check-paths-relations", run_checker(CHECK_PATHS, root)))
    with tempfile.TemporaryDirectory() as td:
        root = _synth_fixture_repo(Path(td), leak=True)
        cases.append(("run-selftest-fixtures", run_checker(RUN_FIXTURES, root, "--skip-upstream")))
    for name, r in cases:
        check_true("%s 前提：真的有失敗項" % name, bool(r.failed_ids()), r.stdout[-800:])
        check_in("%s 的失敗訊息含預期" % name, "預期：", r.stdout)
        check_in("%s 的失敗訊息含實得" % name, "實得：", r.stdout)


def test_every_check_step_after_the_first_runs_unconditionally() -> None:
    """@purpose **M-4**（iteration 2，Major）：A-6 今天對真實 repo 是紅的，而它後面的檢查步驟沒有 `if: always()` ⇒ 那些步驟在 CI 上**一次都不會執行**。實測後果是 `run-selftest-fixtures.py`（連同 A-1／A-2／A-3、F2 的具名證據、F7 剛接進來的兩支驅動）整組是死的，而 code-summary 逐字宣稱「加進來之後它每次第一段都跑」。
    @given aidlc-sync-selftest.yml 的 fixtures job
    @step 取出所有跑檢查器的 step | 第一個之後每一個都有 if: always()
    @step 確認 setup 步驟沒有 always() | 它們失敗時不該讓檢查步驟各自再失敗一次
    @pass 一道閘門紅了不會把它後面的閘門變成死碼
    @story S-10
    """
    doc = _selftest_doc()
    steps = doc["jobs"]["fixtures"]["steps"]
    # **以角色界定，不以位置界定。** 前一版寫的是 `"aidlc-sync-selftest/" in s["run"]`，
    # 於是 ci-pipeline stage 把 U-3／U-4／U-5／U-7 四支套件接進第一段時，那四個 step 被
    # 歸成「setup」，而 setup 的斷言是「不得帶 always()」——四條全紅，且紅的理由與它們
    # 實際做的事無關。這是本 intent 已重複三次的形狀（R-1.2 的掃描面兩次、此處一次）：
    # 位置型邊界每一輪都會有下一格。判準改為「這個 step 跑的是某個 aidlc-sync-* action
    # 目錄下的 .py」——那就是「檢查步驟」的定義本身。
    checkers = [s for s in steps
                if isinstance(s.get("run"), str)
                and re.search(r"\.github/actions/aidlc-sync-[a-z0-9-]+/\S+\.py", s["run"])]
    check_true("前提：第一段真的有多道檢查步驟", len(checkers) >= 3, str(len(checkers)))
    for step in checkers[1:]:
        check("「%s」帶 if: always()" % step.get("name", "?"), step.get("if"), "always()")
    setup = [s for s in steps if s not in checkers]
    for step in setup:
        check_true("setup 步驟「%s」不帶 always()" % (step.get("name") or step.get("uses")),
                   step.get("if") is None, repr(step.get("if")))


def test_the_checkers_own_behaviour_tests_run_in_ci() -> None:
    """@purpose orchestrator 裁決（iteration 2 的 m-3）：`run-selftest-tests.py` 過去不被任何 workflow 執行——`aidlc-sync-selftest.yml` 對它的四處命中**全部是註解**。後果是兩輪合計 24 項修正的迴歸保護在 CI 上等於零：每一句「由 test_X 釘住」的實際意思是「有人手動跑時會紅」。
    @given aidlc-sync-selftest.yml
    @step 取出 fixtures job 的 run: 指令（不是註解） | 其中一個真的執行 run-selftest-tests.py
    @pass 一套沒人跑的測試等於沒有
    @story S-10
    """
    doc = _selftest_doc()
    # **用受測檢查器自己的呼叫解析器**，不用文字比對：`echo "# … run-selftest-tests.py"`
    # 這種寫法會騙過任何「這一行不是以 # 開頭」的判斷（實測騙過了本測試的第一版），而
    # `invocation_targets()` 看的是命令位置——它是本 repo 對「這一行真的執行了什麼」的
    # 單一真實來源，也正是 C-1 那道可達閉包所依賴的東西。
    executed = set()
    for step in doc["jobs"]["fixtures"]["steps"]:
        if not isinstance(step.get("run"), str):
            continue
        body = _cas.strip_shell_comments(step["run"])
        for raw, _proven in _cas.invocation_targets(body):
            executed.add(Path(raw.strip('"\'')).name)
    check_true("run-selftest-tests.py 真的被某個 step 執行（不是只出現在註解或 echo 裡）",
               "run-selftest-tests.py" in executed, str(sorted(executed)))


def test_the_real_repo_state_is_what_we_say_it_is() -> None:
    """@purpose 把「對真實 repo 的實際狀態」寫成斷言而不是報告裡的一句話：R-1.2 綠、A-6 綠。U-10b 已交付（四支 gh-aw 的 `.md` 與 `.lock.yml` 都有 paths-ignore），所以 A-6 現在該全綠。**這條同時釘住「綠是真的」**——逐一比對通過的檢查代號，少一項就是有人把檢查刪掉而不是把問題修好。
    @given 真實 repo
    @step 跑 check-agentic-steps.py | rc=0
    @step 跑 check-paths-relations.py | rc=0，零失敗
    @step 比對**通過**的檢查代號集合 | 恰為 ci.yml 一項 ＋ 四支承載體各三項 ＋ ALLOWLIST-1／DISJOINT-1／COVERAGE-1／COVERAGE-2，共 17 項
    @pass 有人拿掉任一支的 paths-ignore、在 `.md` 增刪**這一條 glob** 而沒重編 `.lock.yml`、或把某項檢查整個移除，這條都紅。**偵測不到**的是一般性的 lock 過期（改 types／permissions／engine／tools／timeout-minutes／network 或 prompt 本文而不重編）——那些欄位不在 COMPILED: 的比對範圍內，已登錄為缺口，見下方 tripwire 第 (2) 條。
    @story S-10
    """
    agentic = run_checker(CHECK_AGENTIC, REPO_ROOT)
    check("真實 repo 的 R-1.2 檢查", agentic.rc, 0)

    paths = run_checker(CHECK_PATHS, REPO_ROOT)
    # ---- 這條絆線紅了怎麼辦（U-10b 交付後翻面）------------------------------
    # U-10b 交付前，這條斷言的是「A-6 紅、且失敗恰好是那八個承載體項目」——它刻意擋在每
    # 個 PR 上，用意是逼交付 U-10b 的人回來更新它。U-10b 已交付，所以預期值本輪起翻面。
    # **斷言沒有被放寬成恆真**：紅燈的觸發條件只是從「有人把 gh-aw 四支寫成可選」換成
    # 下面兩種，外加第三種（檢查項被整個拿掉）由通過集合的逐項比對接手。
    tripwire = (
        "\n\n  ⚠ 這條紅了代表下列其中之一，沒有一種是改這條測試能解決的："
        "\n    (1) 有人把某個承載體的 paths-ignore 拿掉了（`ci.yml`，或四支 gh-aw 的"
        "\n        `.md`／`.lock.yml`）⇒ 反向同步 PR 上被建立的 run 由 2 個回到 6 個。"
        "\n        （6 與 2 是逐檔解析 .github/workflows 下每一個 .yml／.lock.yml 的"
        "\n        on.pull_request 算出來的，**不是**數 *.md：GitHub 跑的是 .lock.yml，"
        "\n        而剩下的那 2 個——ci.yml 與 aidlc-sync-forward.yml——是純 Actions、"
        "\n        根本沒有 .md。）對應的失敗代號是 IGNORE:<檔名>。"
        "\n    (2) 有人在 gh-aw 的 `.md` **增刪了這一條 glob** 卻沒有重新編譯"
        "\n        `.lock.yml` ⇒ GitHub 跑的是 lock，排除實際上沒生效而且不會有任何"
        "\n        錯誤訊息（`open-items.md` 的 N:M-5）。對應的失敗代號是"
        "\n        COMPILED:<名稱>。重編要用**釘住的** gh-aw v0.86.2（＝ repo 內四支"
        "\n        lock 的 compiler_version），不是本機較新的 `gh aw`——版本不同會把"
        "\n        action SHA 與容器映像的供應鏈升級一起夾帶。"
        "\n        **這一條偵測不到一般性的 lock 過期。** COMPILED: 的判定式是"
        "\n        `not (md_has and not lock_has)`，兩個布林值都只是「這一條 glob 在不在"
        "\n        on.pull_request.paths-ignore 裡」。frontmatter 的其餘欄位（types、"
        "\n        permissions、engine、tools、timeout-minutes、network）與 prompt 本文"
        "\n        全都不在比對範圍內——改了它們而不重編，GitHub 會跑一份過期的 lock，"
        "\n        而 repo 裡沒有任何東西會紅。實測（把 ui-regression.md 的 types 由"
        "\n        [opened, synchronize, reopened] 改為多兩個值、lock 不重編）：本測試"
        "\n        `1 tests, 4 checks, 0 failures`，check-paths-relations.py rc=0。"
        "\n        這是已登錄的缺口，不是這條斷言的漏洞。"
        "\n    (3) 通過集合少了一項而不是有項目失敗 ⇒ 有人把檢查本身拿掉了（例如從"
        "\n        check-paths-relations.py 的 GH_AW_CARRIERS 移掉一支）。這比失敗更糟，"
        "\n        因為報告會是綠的。真的多了一支承載體時，改的是下面那個字面清單。"
        "\n    (4) **這是一條絆線，不是一條被檢查器保護的斷言。** 它在第一段的 step 7"
        "\n        （`run-selftest-tests.py`）裡跑，而 step 4／5 跑的就是它拿來斷言的那兩"
        "\n        支檢查器。所以 step 7 的紅有兩種來源，看的人必須自己分辨："
        "\n          (a) **repo 真的違規了**——某個承載體的 paths-ignore 被拿掉、lock 沒重"
        "\n              編、或有人在掃描面上的某支腳本裡加了代理式呼叫；"
        "\n          (b) **檢查器自己壞了**——期望集合寫死在這裡，改了 check-paths-"
        "\n              relations.py 的檢查代號、或改了 check-agentic-steps.py 的掃描面"
        "\n              定義，這條也會紅，而 repo 一個字都沒違規。"
        "\n        分辨方式：先單獨跑 step 4／5 那兩支檢查器對真實 repo，看它們自己說什麼。"
        "\n        兩支都綠而只有本測試紅 ⇒ 是 (b)；兩支之一自己就紅了 ⇒ 是 (a)。"
    )
    check("真實 repo 的 A-6 檢查（U-10b 已交付 ⇒ 綠是正確的）%s" % tripwire, paths.rc, 0)
    check("A-6 對真實 repo 零失敗%s" % tripwire, set(paths.failed_ids()), set())

    # 綠也可能是假的：把檢查項刪掉一樣得到 rc=0、零失敗。所以逐一比對**通過**的代號。
    #
    # 這裡的承載體清單**刻意是字面值，刻意不從 GH_AW_CARRIERS 產生**——本檔其餘各處都
    # 從那個常數產生要求清單（見 COVERAGE-1 與 allowlist 的建構），那在別處是對的，在
    # 這裡是致命的：受測物就是那個常數。實測過——把 "ui-regression" 從 GH_AW_CARRIERS
    # 移掉，檢查器 rc 仍是 0（它不再檢那一支），而由同一個常數產生的預期集合也跟著縮
    # 水，兩邊一起變小，斷言照樣通過。這是本測試唯一與受測物脫鉤的錨點，也就是
    # team.md「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試」裡的那個測試本身。
    EXPECTED_CARRIERS = ("ui-regression", "pr-reviewer", "lint-fix", "contract-guard")
    passed = set(re.findall(r"^\[通過\] (\S+)", paths.stdout, re.M))
    expected_passed = (
        {"IGNORE:ci.yml", "ALLOWLIST-1", "DISJOINT-1", "COVERAGE-1", "COVERAGE-2"}
        | {"IGNORE:%s.%s" % (n, ext) for n in EXPECTED_CARRIERS for ext in ("md", "lock.yml")}
        | {"COMPILED:%s" % n for n in EXPECTED_CARRIERS}
        | {"COMPILER:%s" % n for n in EXPECTED_CARRIERS}
        | {"PR-TRIGGER-1"}
    )
    check("A-6 通過的檢查代號恰為那 22 項（沒有哪一項被悄悄拿掉）%s" % tripwire,
          passed, expected_passed)


# ==========================================================================
# iteration 3（架構審查）：F1／F2／F6／F7
#
# 前兩輪的 reviewer 看的是**測試機制**，這一輪看的是**邊界**：這個單元實際碰到的東西，
# 比它的設計文件說它碰到的東西多。四項發現的共同形狀是「宣稱的範圍 ≠ 實際的範圍」。
# ==========================================================================
def test_a_path_shaped_literal_in_python_is_not_a_call_site() -> None:
    """@purpose **F1（iteration 3，Major）**：C-1 把掃描面由 1 檔擴為 34 檔，但 `_walk_python` 收的是**任何長得像路徑而且真的存在**的字串字面值——`validate_repo_contract.py` 的 REQUIRED_FILES 清單、`validate_env_contract.py` 的範本清單、`tcms_validate.py` 的 spec 路徑因此把 `frontend/`、`deploy/`、`.claude/` 底下 11 個檔拉進掃描面，而它們**不在觸發 allowlist 內**。後果不是漏檢而是**誤報落在無關的 PR 上**：改那些檔的 PR 不跑自我測試，紅燈落在下一個改同步機制的 PR 上。`business-rules.md` R-4 逐字：「一個會誤報的閘門，比沒有閘門更快失去作用。」
    @given 合成樹：workflow 呼叫 scripts/lister.py，該檔只是在一個清單裡**提到** tools/data.sh 的路徑，而 tools/data.sh 含代理式字樣
    @step 跑檢查器 | rc=0——「被某支 Python 提到」不是「被執行」
    @step 讀報告 | 掃描面不含 tools/data.sh
    @pass 掃描面＝真正的呼叫位置，不是「某個字串剛好等於一個存在的檔名」
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        _wf_with_run(root, "forward", "python3 scripts/lister.py")
        write(root / "scripts" / "lister.py",
              "REQUIRED_FILES = (\n"
              '    "tools/data.sh",\n'
              '    "tools/other.sh",\n'
              ")\n"
              "for name in REQUIRED_FILES:\n"
              "    print(name)\n")
        write(root / "tools" / "data.sh",
              '#!/usr/bin/env bash\nstatus="$(%s -p "which Status?")"\n' % AGENT_CLI)
        r = run_checker(CHECK_AGENTIC, root)
        check("rc（只是被提到，不該進掃描面）", r.rc, 0)
        check_not_in("掃描面不含只被提到的檔", "tools/data.sh", r.stdout)


def test_a_python_subprocess_call_site_is_still_followed() -> None:
    """@purpose F1 的**反向**斷言：收窄不得把真正的呼叫位置一起丟掉。`_walk_python` 縮成「只收 subprocess 系列呼叫的 argv 位置」之後，`subprocess.run(["bash", "tools/real.sh"])` 這種真的會執行的目標必須照樣進掃描面——否則 C-1 修掉的那個洞（把判定推到下一層）會從 Python 這一側重新打開。
    @given 合成樹：workflow 呼叫 scripts/caller.py，該檔以 subprocess.run 執行 tools/real.sh，判定在 tools/real.sh
    @step 跑檢查器 | rc=1 且 SCRIPT-1 指向 tools/real.sh
    @pass 收窄的是「路徑形狀的字面值」，不是「呼叫位置」
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        synth_workflows(root)
        _wf_with_run(root, "forward", "python3 scripts/caller.py")
        write(root / "scripts" / "caller.py",
              "import subprocess\n"
              'subprocess.run(["bash", "tools/real.sh"], check=True, timeout=60)\n')
        write(root / "tools" / "real.sh",
              '#!/usr/bin/env bash\nstatus="$(%s -p "which Status?")"\n' % AGENT_CLI)
        r = run_checker(CHECK_AGENTIC, root)
        check("rc", r.rc, 1)
        check_true("SCRIPT-1 指向 tools/real.sh",
                   any(i.startswith("SCRIPT-1") and "tools/real.sh" in i for i in r.failed_ids()),
                   str(r.failed_ids()))


def test_the_scan_report_separates_reachable_scripts_from_directory_seeds() -> None:
    """@purpose **F7（iteration 3，Minor）**：報告抬頭印「掃描面（**執行可達閉包**……）／腳本 34 支」，但 34 支之中有一部分**從未被任何步驟執行**——它們在掃描面上的理由是「躺在同步機制自己的目錄裡」。讀 CI log 的人會相信 fail-closed 的論證適用於全部 34 支，而 fail-closed 只適用於 shell 呼叫位置那一區。分區印出來，讓「這一支是怎麼進來的」在報告上就是一個可讀的事實。
    @given 真實 repo
    @step 跑檢查器 | 報告出現三個分區標題，且分區計數相加等於總數
    @step 檢視 ③ 區 | 同步機制自有目錄的種子（未必被執行）落在這一區，不與 ① 區混列
    @pass 報告說得出每一支腳本是「被呼叫到」還是「因為在那個目錄裡」
    @story S-10
    """
    r = run_checker(CHECK_AGENTIC, REPO_ROOT)
    check("rc", r.rc, 0)
    check_in("① 區標題", "① 執行可達 · shell 呼叫位置", r.stdout)
    check_in("② 區標題", "② 執行可達 · Python subprocess argv 位置", r.stdout)
    check_in("③ 區標題", "③ 同步機制自有目錄全掃", r.stdout)
    zone_counts = [int(n) for n in re.findall(r"^\s+[①②③][^\n]*?（(\d+) 支）", r.stdout, re.M)]
    check("三個分區都印了計數", len(zone_counts), 3)
    total = re.search(r"^  腳本 (\d+) 支", r.stdout, re.M)
    check_true("報告仍印總數", total is not None, r.stdout[:400])
    if total and len(zone_counts) == 3:
        check("分區計數相加＝總數", sum(zone_counts), int(total.group(1)))
    # ③ 區必須非空，否則這條測試會在「分區存在但沒東西」的狀態下假通過。
    seeds = re.search(r"③ 同步機制自有目錄全掃[^\n]*（(\d+) 支）", r.stdout)
    check_true("③ 區非空（真實 repo 的 action 目錄裡有沒被呼叫的腳本）",
               seeds is not None and int(seeds.group(1)) > 0, r.stdout[:400])


def test_the_trigger_allowlist_covers_the_whole_scan_surface() -> None:
    """@purpose **F1 的另一半**：掃描面 ⊆ 觸發 allowlist ∪ SCAN_EXEMPT，否則這道閘門的紅燈會落在無關的 PR 上。這與 COVERAGE-1 是同一種缺口的兩個方向——COVERAGE-1 管「A-6 斷言的檔案要在 allowlist 內」，COVERAGE-2 管「R-1.2 掃得到的檔案要在 allowlist 內」。iteration 1 的 F7 關上前者，iteration 2 的 C-1 打開後者，而 82 條測試裡沒有一條斷言得到它。
    @given 真實 repo
    @step 跑 check-paths-relations.py | COVERAGE-2 通過
    @pass 掃描面的每一支腳本都會讓一個改它的 PR 觸發本自我測試
    @story S-10
    """
    r = run_checker(CHECK_PATHS, REPO_ROOT)
    check("rc", r.rc, 0)
    passed = set(re.findall(r"^\[通過\] (\S+)", r.stdout, re.M))
    check_true("COVERAGE-2 存在且通過", "COVERAGE-2" in passed, str(sorted(passed)))


def test_a_scanned_file_outside_the_allowlist_is_red() -> None:
    """@purpose COVERAGE-2 的突變面：把一支**真的會被執行**的腳本放在 allowlist 涵蓋不到的路徑，必須紅並逐一列出沒被涵蓋的檔。只斷言真實 repo 綠是不夠的——那條在檢查被拿掉時也會綠。
    @given 合成樹：aidlc-sync-forward.yml 呼叫 tools/helper.sh，而 allowlist 只涵蓋 .github/ 與 fixture 集
    @step 跑 check-paths-relations.py | rc=1、COVERAGE-2 紅、訊息含 tools/helper.sh
    @step 把 tools/** 加進 allowlist | COVERAGE-2 綠
    @pass 「掃得到但改它不會觸發」這件事在 CI 上會紅
    @story S-10
    """
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td))
        _wf_with_run(root, "forward", "bash tools/helper.sh")
        write(root / "tools" / "helper.sh", '#!/usr/bin/env bash\necho ok\n')
        r = run_checker(CHECK_PATHS, root)
        check("rc", r.rc, 1)
        check_true("COVERAGE-2 紅", "COVERAGE-2" in r.failed_ids(), str(r.failed_ids()))
        check_in("訊息列出沒被涵蓋的檔", "tools/helper.sh", r.stdout)
    with tempfile.TemporaryDirectory() as td:
        root = synth_paths_repo(Path(td),
                                selftest_paths=DEFAULT_SELFTEST_PATHS + ("tools/**",))
        _wf_with_run(root, "forward", "bash tools/helper.sh")
        write(root / "tools" / "helper.sh", '#!/usr/bin/env bash\necho ok\n')
        r = run_checker(CHECK_PATHS, root)
        check_true("COVERAGE-2 綠", "COVERAGE-2" not in r.failed_ids(), str(r.failed_ids()))


def test_stage_2_cleanup_closes_the_issue_and_removes_the_board_item() -> None:
    """@purpose **F2（iteration 3，Major）**：清理用 GraphQL `deleteIssue`，而它需要 repo **admin**——fine-grained PAT／GitHub App 的 `issues: write` 只能建立／關閉／編輯，**沒有任何權限項可以刪除 issue**。已宣告的憑證權限（ADR-0015 §8：組織層 Projects 讀寫 ＋ contents write ＋ issues write ＋ PR write）做不到這件事。後果不是「清理失敗一次」，是 R-4 想防的螺旋反過來成真：清理失敗是紅燈 ⇒ **第二段永遠紅，且每跑一次殘留一則 item**。改為「關閉 issue ＋ `deleteProjectV2Item` 移出測試看板」，兩者都在已宣告的權限內。
    @given 真實 workflow 第二段的清理 step
    @step 檢視腳本 | 不含 deleteIssue
    @step 檢視腳本 | 含 `state=closed` 的關閉呼叫，且含 deleteProjectV2Item
    @pass 清理路徑落在已宣告的權限內；不為了保留真刪除而去要 repo admin
    @story S-10
    """
    steps = _selftest_doc()["jobs"]["endtoend"]["steps"]
    cleanup = [s for s in steps if "clean up" in str(s.get("name", "")).lower()]
    check("清理步驟恰有一個", len(cleanup), 1)
    if cleanup:
        body = cleanup[0].get("run", "")
        # **比對的是剝掉註解之後的本體**：那段腳本的註解逐字解釋了「為什麼不能用
        # deleteIssue」，拿原文做否定比對會把那段解釋判成違規——那不是嚴格，是壞掉。
        # 用的是受測檢查器自己的剝除器（R-1.2 的 `run:` 掃描用同一支）。
        executable = _cas.strip_shell_comments(body)
        check_in("前提：註解確實解釋了為什麼不用它（剝除前找得到）", "deleteIssue", body)
        check_not_in("不得用需要 repo admin 的 deleteIssue", "deleteIssue", executable)
        check_true("以 state=closed 關閉 issue", "state=closed" in executable, executable[:1200])
        check_true("以 deleteProjectV2Item 移出測試看板",
                   "deleteProjectV2Item" in executable, executable[:1200])
        check_true("兩種清理失敗都是紅燈", executable.count("exit 1") >= 2, executable[:1200])


def test_every_subprocess_call_in_the_selftest_scripts_has_a_timeout() -> None:
    """@purpose **F6（iteration 3，Minor）**：六支轉呼與兩處以真實 shell 執行抽出腳本的呼叫都沒有 `timeout=`。本 repo 已有這個形狀的實例——reviewer 注入代理式 CLI 之後測試掛住直到 `pkill`。job 的 `timeout-minutes: 10` 是有效上界，但失敗訊息會是「job timed out」而不是「driver X 掛住」，而診斷成本高的閘門會被當成雜訊。
    @given run-selftest-fixtures.py 與 run-selftest-tests.py 的原始碼
    @step 以 ast 找出每一個 subprocess.run／check_output／Popen 呼叫 | 每一個都帶 timeout= 關鍵字
    @pass 掛住的是哪一支，在第一行就說得出來
    @story S-10
    """
    families = {"run", "call", "check_call", "check_output", "Popen"}
    for rel in ("run-selftest-fixtures.py", "run-selftest-tests.py"):
        src = (HERE / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else "")
            if name not in families:
                continue
            if isinstance(func, ast.Attribute) and not (
                    isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
                continue
            if isinstance(func, ast.Name):
                continue
            calls.append(node)
        check_true("前提：%s 真的有 subprocess 呼叫可檢" % rel, len(calls) > 0, str(len(calls)))
        for node in calls:
            kwargs = {kw.arg for kw in node.keywords}
            check_true("%s:%d 的 subprocess 呼叫帶 timeout=" % (rel, node.lineno),
                       "timeout" in kwargs, str(sorted(kwargs)))


# ==========================================================================
# main
# ==========================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="U-9 自我測試的行為測試")
    ap.add_argument("-k", default=None, help="只跑名稱含此子字串的測試")
    args = ap.parse_args()

    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and (args.k is None or args.k in name)]
    print("受測物：check-agentic-steps.py／check-paths-relations.py／"
          "run-selftest-fixtures.py／aidlc-sync-selftest.yml")
    print("寫入 glob（由 record.sh 推導）：%s\n" % WRITE_GLOB)
    for test in tests:
        before = len(FAILURES)
        try:
            test()
        except Exception as exc:  # noqa: BLE001 — runner 自己不得靜默失敗
            FAILURES.append("%s 執行時拋出例外：%r" % (test.__name__, exc))
        print("[%s] %s" % ("FAIL" if len(FAILURES) > before else "ok", test.__name__))

    print("\n%d tests, %d checks, %d failures" % (len(tests), CHECKS, len(FAILURES)))
    if FAILURES:
        print("\n---- failures ----")
        for failure in FAILURES:
            print("  - %s" % failure)
        return 1
    print("全數通過。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
