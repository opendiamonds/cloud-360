#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U-9 第一段的 fixture 驅動：A-1／A-3 的自有斷言 ＋ 轉呼上游既有驅動（A-2／A-4／A-5）。

六項繼承斷言，本檔各自的承接方式
--------------------------------
`functional-design/domain-entities.md` 把六項散在四個單元的「規則已定但沒有斷言」指向本
單元。它們不是同一種東西，承接方式也不該一樣：

| 斷言 | 內容 | 本檔怎麼承接 |
| --- | --- | --- |
| A-1 | U-1 的 output 不含憑證樣式 | **自己寫**（既有 38 條 map 測試無一條涉及憑證樣式） |
| A-2 | 同一個 Block 兩次獨立執行序列化逐位元相同 | **轉呼** `aidlc-sync-block/run-fixtures.py` |
| A-3 | 受管區塊在無漂移時不重寫（連續兩輪） | **自己寫**（fixture 層）＋ **轉呼** `aidlc-sync-forward/run-orchestration-tests.py`（閘門層） |
| A-4 | 反向 PR 的 diff 不含 `aidlc-state.md` 任何一行 | **轉呼** `aidlc-sync-reverse/run-reverse-tests.py` |
| A-5 | PR 建立失敗 ⇒ 分支被刪；刪除也失敗 ⇒ 孤兒分支，兩者都在同一次執行內紅燈 | **轉呼** 同上 |
| A-6 | 寫入路徑 ⊆ paths-ignore glob 集合，且該集合 ∩ 本單元 allowlist ＝ ∅ | 不在本檔——靜態跨檔比對，由 `check-paths-relations.py` 承接 |

**為什麼轉呼而不是重寫**：重寫會產生第二份斷言同一件事的程式，兩份必有一份先過期。
轉呼是 `team.md ## Code Style` 的「單一真實來源」在測試層的體現。

**但轉呼必須斷言它真的跑了**——只看 rc＝0 不夠：一個被改成空殼的驅動（刪光測試、直接
`return 0`）會讓 rc＝0 而本檔完全不紅。所以每一次轉呼都額外解析它自己印出的測試數與斷言
數，兩者都必須 > 0，解析不到就判紅（fail closed）。

A-4／A-5 的承接方式是**轉呼**，不是規格指定的注入（對已核可計畫的兩處偏離）
------------------------------------------------------------------------
兩處偏離，都已逐條記入 `code-summary.md` 的交還清單（第 9 項），指派 Bolt gate：

**偏離①：落在第一段而不是第二段。** `business-logic-model.md` 的兩段圖把 A-4／A-5 放在
第二段（需要憑證與真實 PR）。實測後發現 **U-8 的 `run-reverse-tests.py` 已經以 stub 涵蓋
這兩項**（`test_r2_1_diff_never_contains_aidlc_state_md`、
`test_r6_3_outcome_2_pr_fails_branch_deleted`、
`test_r6_3_outcome_3_pr_fails_and_delete_fails_leaves_an_orphan`），而且是**離線**的。把它
們留在第二段的後果是：第二段目前沒有憑證、從未執行過，於是這兩項在本 intent 的實際狀態
會是「零斷言」。

**偏離②：`domain-entities.md:15`／`:28` 逐字指定 U-9 自己「注入一次必然失敗的 PR 建立
呼叫」並斷言 (1) 分支被刪除、(2) 該次執行紅燈且訊息含 intent id 與分支名。本檔改為轉呼
上游測試並比對兩條具名測試。**

**這兩者的偵測力不相等，差別必須寫在這裡而不是只寫在交還報告裡**（iteration 3 的 F4）：

| 失效方式 | 轉呼＋具名證據＋斷言數下限 | 規格指定的注入 |
| --- | --- | --- |
| 上游把那幾條測試**刪掉** | 偵測得到（具名證據不見了） | 偵測得到 |
| 上游把它們**清空本體、留著名字** | 偵測得到（斷言數掉到基準以下） | 偵測得到 |
| 上游的斷言**寫錯**（照樣跑、照樣綠，但驗的不是那件事） | **偵測不到** | 偵測得到 |

最後一列不是假設。本 intent 內已實證：U-8 的孤兒分支那一支曾有**三條假斷言**，而同期
U-9 全綠、CI log 逐字印著「承接：A-4…；A-5：PR 開不成的三種結局」。轉呼的「單一真實
來源」理由對**產品程式**成立，對**獨立驗證層**是類別錯誤——本單元交付的是「機制壞了會
有人知道」，而知識來源若完全等於受測單元自己的測試，A-2／A-4／A-5 的**獨立偵測力是
零**，只剩下防「刪除」與「掏空」。

**「要不要改成規格指定的注入」不在本輪處置範圍**：那要改 `domain-entities.md:28`（已通過
reviewer 的上游產出），屬 Bolt gate 的裁決。本輪做的是**登錄與寫明邊界**，不是自行改變
承接方式。

用法與 exit code
----------------
    python3 .github/actions/aidlc-sync-selftest/run-selftest-fixtures.py
    python3 .github/actions/aidlc-sync-selftest/run-selftest-fixtures.py --repo-root <某棵樹>
    python3 .github/actions/aidlc-sync-selftest/run-selftest-fixtures.py --skip-upstream

    0  全數通過
    1  斷言失敗（第一行 `ASSERTION-FAILED:`）
    2  外部錯誤（第一行 `EXTERNAL-ERROR:`）

`--skip-upstream` 只給 `run-selftest-tests.py` 的行為測試用：那些測試要驗的是本檔對
「空殼驅動」的反應，不需要每次都把四支上游驅動重跑一遍。**它不是給 CI 用的旗標**，
workflow 裡的呼叫沒有帶它。
"""

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise SystemExit("EXTERNAL-ERROR: 無法載入 %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_shared = _load(HERE / "check-agentic-steps.py", "aidlc_selftest_shared")
Checker = _shared.Checker
ExternalError = _shared.ExternalError
run_checker = _shared.run_checker

# fixture 目錄以 **glob** 解析，不寫死單一 intent record（reviewer iteration 1 的 F10）。
#
# 這條 glob 與 workflow 觸發 allowlist 的 `aidlc/spaces/*/intents/*/.test-fixtures/**`
# 是同一個形狀。寫死 `260822-gh-projects-sync` 的後果是兩者不一致：改 record 名稱時觸發
# 照舊（allowlist 是通用的），驅動卻找不到 fixture。
#
# 恰好一個才通過：找不到與找到兩個都是外部錯誤。找到兩個時**不猜哪一個是本尊**——猜錯
# 會讓 A-1／A-3 在一份不是它要驗的 fixture 上跑，而且完全看不出來。
FIXTURE_DIR_GLOB = "aidlc/spaces/*/intents/*/.test-fixtures"


def resolve_fixture_dir(repo_root):
    matches = sorted(p for p in repo_root.glob(FIXTURE_DIR_GLOB) if p.is_dir())
    if not matches:
        raise ExternalError(
            "在 %s 之下用 %r 找不到 fixture 目錄。**不得因此視為通過**——沒有 fixture 就"
            "沒有 A-1／A-3。\n  預期：恰好 1 個\n  實得：0" % (repo_root, FIXTURE_DIR_GLOB)
        )
    if len(matches) > 1:
        raise ExternalError(
            "用 %r 找到 %d 個 fixture 目錄：%s。本檢查**不猜哪一個是本尊**——猜錯會讓 "
            "A-1／A-3 在一份不是它要驗的 fixture 上跑，而且完全看不出來。\n"
            "  預期：恰好 1 個\n  實得：%d"
            % (FIXTURE_DIR_GLOB, len(matches),
               "、".join(str(p) for p in matches), len(matches))
        )
    return matches[0]

# A-1 的假憑證樣式。**憑空構造、不使用任何真實前綴**，理由見 fixture 目錄的 README：
# `validate_repo_contract.py` 的 FORBIDDEN_CONTENT_PATTERNS 與 GitHub 的 push protection
# 都不分辨「示範」與「洩漏」。這裡的字串必須與 fixture 檔內的逐字相同——CRED-0 會先驗這
# 件事，所以改了一邊而忘了另一邊會紅燈，不會靜默地變成一條掃不到東西的斷言。
FAKE_CREDENTIAL_TOKENS = (
    "-----BEGIN ZZTEST KEY-----",
    "AWS_ZZTEST_TOKEN=ZZTESTZZTESTZZTEST0000",
    "AZURE_ZZTEST_TOKEN=zztest-not-real-0000",
    "GOOGLE_ZZTEST_TOKEN=/zztest/not/real.json",
)

# map.sh 的五個 output（U-1 的介面表；第五個 scope_note 於 functional-design iteration 4
# 增設）。A-1 掃的是**全部**五個，不是挑幾個——漏掉一個就是那一個沒有防線。
MAP_OUTPUTS = ("status", "field_value", "reason_code", "traceable_row", "scope_note")

# Decision 的三欄。U-6 的寫入理由判定（`aidlc-sync-forward-impl.yml` 的 R-5.2 ∪ R-5.6）
# 逐字比的就是這三欄：任一不同即為有漂移。
DRIFT_COLUMNS = ("status", "field_value", "reason_code")

# ==========================================================================
# 逾時上界（F6，iteration 3）
# ==========================================================================
# 每一個外部呼叫都要有自己的上界，理由不是怕跑太久（job 已經有 `timeout-minutes: 10`），
# 而是**掛住的時候要說得出是哪一支**。job 層逾時給的訊息是「job timed out」，看的人得自己
# 回頭比對 log 才知道卡在哪；本層逾時給的是「上游驅動 X 超過 N 秒沒有結束」。
#
# 數值取自實測留餘裕：本機最慢的一支（`run-reverse-tests.py`）約 42 s，六支合計約 170 s，
# 而 runner 比本機慢。300 s 給單支、60 s 給單次 shell 呼叫（map.sh／block.sh 是毫秒級），
# 六支即使全部貼著上界也仍在 job 的 10 分鐘內。**上界不是效能目標**：它只在真的掛住時
# 才會生效，正常路徑碰不到它。
DRIVER_TIMEOUT_S = 300
SHELL_TIMEOUT_S = 60


def timeout_message(what, path, limit):
    return ("%s 超過 %d 秒沒有結束（%s）。**這不是斷言失敗，是它掛住了**——"
            "常見原因是該腳本在等一個不會來的輸入（stdin、網路、互動式提示）。"
            "job 層的 timeout-minutes 也擋得住，但它只會說「job timed out」，"
            "不會說是哪一支。" % (what, limit, path))


# ==========================================================================
# 轉呼的上游驅動
# ==========================================================================
# 每一項是 (相對路徑, 這一次轉呼承接哪些斷言, **必須真的跑過的證據**, 收尾格式標籤)。
#
# 第三欄是 reviewer iteration 1 的 F2 補上的。原本只斷言「總數 > 0」，reviewer 把
# `run-reverse-tests.py` 中**逐字宣稱承接 A-4／A-5 的那三條**測試移除並清空本體，rc 仍為
# 0，而 CI log 那一行**仍逐字宣稱它承接了 A-4／A-5**。承接關係若不指名到測試名稱，它就
# 只是一句文件上的宣稱——總數擋得住「刪光」，擋不住「刪掉我要的那幾條」。
#
# 名稱以 `[ok] <name>` 的形式比對（四支測試驅動逐條印它）。兩支檢查器型的驅動不印
# `[ok] test_x`，它們印 `[通過] <檢查代號>`——證據字串因此照它們的實際輸出寫，這是
# **對 reviewer 建議的偏離**，理由是「照抄一個它不會印的字串」等於一條永遠紅的假斷言。
# `run-selftest-tests.py` 的 `test_every_named_upstream_test_actually_exists_upstream`
# 會回上游原始碼逐一核對這些名稱，改名時那裡先紅。
UPSTREAM_DRIVERS = (
    (".github/actions/aidlc-sync-map/run-fixtures.py",
     "U-1 的七條判定順序與 get_field 四行為",
     ("[ok] test_r1_1_first_match_wins",
      "[ok] test_r1_2_present_but_empty_returns_empty_string",
      "[ok] test_r1_3_absent_returns_null_not_empty",
      "[ok] test_r1_4_indented_is_not_a_match",
      "[ok] test_r3_1_parked_beats_completed"),
     "組測試", (38, 2707)),
    (".github/actions/aidlc-sync-block/run-fixtures.py",
     "A-2：Block 序列化逐位元相同",
     ("[ok] test_serialization_is_deterministic_and_locale_independent",
      "[ok] test_r4_4_serialization_golden_byte_identical"),
     "組測試", (34, 550)),
    (".github/actions/aidlc-sync-forward/run-orchestration-tests.py",
     "A-3 的閘門層：無漂移 ⇒ 零看板寫入、零 commit（含多輪收斂）",
     ("[ok] test_r5_5_no_drift_no_write",
      "[ok] test_multi_round_suppressed_converges"),
     "tests", (40, 154)),
    (".github/actions/aidlc-sync-reverse/run-reverse-tests.py",
     "A-4：diff 不含 aidlc-state.md；A-5：PR 開不成的三種結局",
     ("[ok] test_r2_1_diff_never_contains_aidlc_state_md",
      "[ok] test_r6_3_outcome_2_pr_fails_branch_deleted",
      "[ok] test_r6_3_outcome_3_pr_fails_and_delete_fails_leaves_an_orphan"),
     # 基準於 2026-09-06 由 (39, 246) 提高到 (46, 308)：U-8 的 reviewer 以 76 條突變
     # 查出 14 條真實未覆蓋行為（其中 R-6.1 的查詢參數幾乎完全沒有斷言，三條單 token
     # 突變讓防重複開 PR 整條失效而 39 條全綠），修正輪加了 7 條測試。下限沒跟著提高
     # 的話，有人把那 7 條刪掉不會讓本檢查紅——下限的用意正是擋這件事。
     "tests", (46, 308)),
    # ---- reviewer iteration 1 的 F7 補上的兩支 --------------------------
    # U-10a 交付了 `check-ci-yml.py`，但對 `.github/` 全樹 grep 顯示**它沒有被任何
    # workflow 執行**（唯一命中是 `ci.yml:24` 的一行註解）——那道守衛是死的。U-9 是同步
    # 機制的自我測試 workflow，這正是它們該有的家。
    (".github/actions/aidlc-sync-ci-guard/check-ci-yml.py",
     "U-10a 的 ci.yml 守衛：SEC-1a〜1d、MARKER-1、CONC-1、四個 job 的 needs／if／NFR-C1",
     ("[通過] SEC-1a", "[通過] SEC-1c", "[通過] SEC-1d", "[通過] MARKER-1"),
     "項檢查", (19, None)),
    (".github/actions/aidlc-sync-ci-guard/run-probe-tests.py",
     "U-10a 的 probe 腳本行為：標記偵測的十一種情境",
     ("[通過] push／訊息含標記 → true",
      "[通過] pull_request／PR head 訊息含標記 → true",
      "[通過] probe 腳本以 exit 0 結束"),
     "項行為測試", (13, None)),
)

# 本 repo 現存的四種收尾格式。**解析不到就判紅**，不猜。
#
# 前兩種帶「測試數」與「斷言數」兩個數字，後兩種只有一個數字（檢查項數）——所以解析結果
# 用具名的欄位表達而不是硬塞進 (tests, checks, failures)：把 19 項檢查寫成「19 tests,
# 19 checks」會在報告上長得像一個算出來的數字，而它是複製的。
_TESTS_CHECKS_RE = re.compile(r"^\s*(\d+)\s+tests,\s*(\d+)\s+checks,\s*(\d+)\s+failures\s*$", re.M)
_RUN_FIXTURES_UNITS_RE = re.compile(r"^run-fixtures:\s*(\d+)\s*組測試", re.M)
_RUN_FIXTURES_CHECKS_RE = re.compile(r"^斷言數：(\d+)　失敗：(\d+)", re.M)
_CHECKER_RE = re.compile(r"^(?:.*：)?(\d+) 項檢查，(\d+) 失敗。\s*$", re.M)
_BEHAVIOUR_RE = re.compile(r"^(\d+) 項行為測試，(\d+) 失敗。\s*$", re.M)


def parse_driver_summary(stdout):
    """從上游驅動的 stdout 取出收尾數字，回傳 dict 或 None。

    回傳 `{"unit_label": …, "units": n, "checks": n 或 None, "failures": n}`。
    `checks` 為 None 代表該驅動的收尾行只有一個數字——那不是零，是「它沒說」，兩者在報告
    上必須分得出來。

    **新增第五種格式時要改這裡**，但改不到的後果是判紅而不是靜默通過：一個轉呼若連「它
    跑了幾條」都說不出來，就沒有資格當成本單元的斷言依據。
    """
    m = _TESTS_CHECKS_RE.search(stdout)
    if m:
        return {"unit_label": "tests", "units": int(m.group(1)),
                "checks": int(m.group(2)), "failures": int(m.group(3))}
    mt = _RUN_FIXTURES_UNITS_RE.search(stdout)
    mc = _RUN_FIXTURES_CHECKS_RE.search(stdout)
    if mt and mc:
        return {"unit_label": "組測試", "units": int(mt.group(1)),
                "checks": int(mc.group(1)), "failures": int(mc.group(2))}
    m = _BEHAVIOUR_RE.search(stdout)
    if m:
        return {"unit_label": "項行為測試", "units": int(m.group(1)),
                "checks": None, "failures": int(m.group(2))}
    m = _CHECKER_RE.search(stdout)
    if m:
        return {"unit_label": "項檢查", "units": int(m.group(1)),
                "checks": None, "failures": int(m.group(2))}
    return None


# ==========================================================================
# 受測物的驅動
# ==========================================================================
def run_map(repo_root, state_md, *args, **env_extra):
    """呼叫 U-1 的 map.sh。**讀檔的是本 runner，不是受測邏輯**——map.sh 自身零 I/O。"""
    map_sh = repo_root / ".github" / "actions" / "aidlc-sync-map" / "map.sh"
    if not map_sh.is_file():
        raise ExternalError("找不到 %s（U-1 尚未落地或路徑改了）。" % map_sh)
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("AIDLC_"):
            del env[key]
    env.update(
        AIDLC_STATE_MD=state_md,
        AIDLC_INTENTS_JSON="",
        AIDLC_RECORD_PATH="fixtures-root/demo-intent",
        AIDLC_RECORD_ROOT="fixtures-root",
        AIDLC_FIELD_MAX_LENGTH="50",
        AIDLC_WHITELIST="",
        AIDLC_REVERSE_PENDING="",
    )
    env.update(env_extra)
    env.pop("GITHUB_OUTPUT", None)
    try:
        return subprocess.run(
            [os.environ.get("AIDLC_SELFTEST_BASH", "bash"), str(map_sh), *args],
            env=env, capture_output=True, text=True, timeout=SHELL_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise ExternalError(timeout_message("map.sh", map_sh, SHELL_TIMEOUT_S))


def decide(repo_root, state_md):
    proc = run_map(repo_root, state_md)
    if proc.returncode != 0:
        raise ExternalError(
            "map.sh 以非零 exit 結束（%d）——本單元對錯誤的表達方式只有 reason_code，"
            "不得設 exit code。stderr：%s" % (proc.returncode, proc.stderr)
        )
    out = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key] = value
    return out


def run_block(repo_root, op, **kw):
    """呼叫 U-2 的 block.sh。鍵直接對應 AIDLC_<大寫> 環境變數。"""
    block_sh = repo_root / ".github" / "actions" / "aidlc-sync-block" / "block.sh"
    if not block_sh.is_file():
        raise ExternalError("找不到 %s（U-2 尚未落地或路徑改了）。" % block_sh)
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("AIDLC_"):
            del env[key]
    for key, value in kw.items():
        env["AIDLC_" + key.upper()] = value
    env.pop("GITHUB_OUTPUT", None)
    try:
        proc = subprocess.run(
            [os.environ.get("AIDLC_SELFTEST_BASH", "bash"), str(block_sh), op],
            env=env, capture_output=True, timeout=SHELL_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise ExternalError(timeout_message("block.sh %s" % op, block_sh, SHELL_TIMEOUT_S))
    if proc.returncode != 0:
        raise ExternalError("block.sh %s 以非零 exit 結束（%d）：%s"
                            % (op, proc.returncode, proc.stderr.decode("utf-8", "replace")))
    return proc.stdout


def render_block(repo_root, **kw):
    keys = ("status", "traceable_row", "reason_code", "scope_note", "decided_at", "rejection_closed_at")
    return run_block(repo_root, "render", **{k: kw.get(k, "") for k in keys})


def hash_of_rendered(repo_root, body_bytes):
    """把渲染出來的區塊 parse 回 Block 再算 content_hash。

    **走的是 parse → hash 這條回讀路徑，不是拿 render 的輸入直接算**——ADR-0015 §10 的等價
    不變式（U-6 寫入後回讀取得的雜湊，必須等於日後對 GitHub 存下來的 body 算出來的值）
    正是由「兩端走同一條路徑」在構造上保證的。自己另算一條就是製造第二條路徑。
    """
    body = body_bytes.decode("utf-8")
    parsed = {}
    for line in run_block(repo_root, "parse", issue_body=body).decode("utf-8").split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            parsed[key] = value
    fields = ("format_version", "status", "traceable_row", "reason_category",
              "decided_at", "scope_note", "rejection_closed_at")
    block_kw = {"block_" + f: parsed.get("block_" + f, "") for f in fields}
    out = run_block(repo_root, "hash", **block_kw).decode("utf-8").strip()
    if not out.startswith("content_hash="):
        raise ExternalError("block.sh hash 的輸出不是 content_hash=…：%r" % out)
    return out[len("content_hash="):], parsed


# ==========================================================================
# 斷言
# ==========================================================================
def check_a1(repo_root, fixtures, c):
    """A-1：U-1 的 output 不含憑證樣式。

    fixture 把四個假憑證放進 `Parked` 的理由裡——那是 U-1 `security-requirements.md` SEC-1
    逐字點名的殘留風險：「若未來有人把機敏內容寫進 record（例如 `Parked` 理由含 token），
    本單元會原樣把它搬進 log——而它是**離 log 最近的一層**」。
    """
    path = fixtures / "a1-credential-shaped-record.md"
    if not path.is_file():
        raise ExternalError(
            "找不到 A-1 的 fixture %s。**不得因為 fixture 不存在就跳過**——那會讓這條斷言"
            "在檔案被刪掉時靜默消失。" % path
        )
    text = path.read_text(encoding="utf-8")

    # 前提 1：fixture 真的含那四個樣式。少了它，下面的「output 不含」會在一個空前提上恆真。
    absent = [t for t in FAKE_CREDENTIAL_TOKENS if t not in text]
    c.check(
        "CRED-0", not absent,
        "fixture 含全部 %d 個假憑證樣式" % len(FAKE_CREDENTIAL_TOKENS),
        "fixture %s 少了假憑證樣式 %r。**這條前提失守時，A-1 會變成一條掃不到東西的恆真"
        "斷言**——output 當然不含它從來沒看過的字串。\n  預期：fixture 含 %r\n  實得：缺 %r"
        % (path, absent, list(FAKE_CREDENTIAL_TOKENS), absent),
    )

    decision = decide(repo_root, text)

    # 前提 2：map.sh 真的把那一行讀進去了（它據此判 parked），不是整段沒解析到。
    c.check(
        "CRED-0b", decision.get("reason_code") == "parked",
        "map.sh 真的讀到了含假憑證的 Parked 行（reason_code=parked）",
        "map.sh 對這份 fixture 判 reason_code=%r，不是 parked——代表它**沒有**讀到那一行，"
        "於是 A-1 掃的是一個 map.sh 從未接觸過的輸入。\n  預期：parked\n  實得：%r"
        % (decision.get("reason_code"), decision.get("reason_code")),
    )

    # 前提 3：**五個 output 真的都在**（reviewer iteration 1 的 F6）。
    #
    # 本體用 `decision.get(name, "")` 取值，所以一個**缺席**的 output 會取到空字串然後判
    # 「不含憑證樣式」而通過——reviewer 把 map.sh 的 `emit scope_note` 換成 `:`，得到的是
    # `[通過] CRED-1:scope_note`。一條被刪掉的防線長得跟守住了一樣，這是最壞的一種。
    missing_outputs = [n for n in MAP_OUTPUTS if n not in decision]
    c.check(
        "CRED-0c", not missing_outputs,
        "map.sh 吐出了 U-1 介面表的全部 %d 個 output" % len(MAP_OUTPUTS),
        "map.sh 沒有吐出這些 output：%r。**它們的 CRED-1 會在缺席時取到空字串而通過**——"
        "掃不到東西的斷言長得跟守住了一樣。\n  預期：%r\n  實得：%r"
        % (missing_outputs, list(MAP_OUTPUTS), sorted(decision)),
    )

    # 反向：多出來的 output 同樣要紅。U-1 日後增設第六個 output 時，A-1 的掃描範圍必須
    # **大聲地**少一項而不是安靜地少一項——這裡是它唯一會被發現的地方。
    unexpected = sorted(set(decision) - set(MAP_OUTPUTS))
    c.check(
        "CRED-0d", not unexpected,
        "map.sh 沒有吐出 U-1 介面表之外的 output",
        "map.sh 吐出了 MAP_OUTPUTS 之外的 output：%r。A-1 只掃本檔列出的那幾個，所以新增"
        "的 output **沒有任何防線**。修法是把它加進 MAP_OUTPUTS（並確認它同樣不該含憑證"
        "樣式），不是把這條斷言拿掉。\n  預期：output 集合 ⊆ %r\n  實得：多出 %r"
        % (unexpected, list(MAP_OUTPUTS), unexpected),
    )

    # 本體：五個 output 全掃。
    for name in MAP_OUTPUTS:
        value = decision.get(name, "")
        hits = [t for t in FAKE_CREDENTIAL_TOKENS if t in value]
        # 樣式的**片段**也要抓：真實洩漏未必是整串照抄，截斷過的一半同樣是洩漏。
        fragments = [f for f in ("ZZTESTZZTEST", "zztest-not-real", "/zztest/not/real",
                                 "BEGIN ZZTEST") if f in value]
        c.check(
            "CRED-1:" + name, not hits and not fragments,
            "output %s 不含任何憑證樣式" % name,
            "U-1 的 output `%s` 把 record 裡的憑證樣式搬了出來。本 repo 是 public，"
            "Actions log 公開可讀——一次意外 echo 即等同公開發布。\n"
            "  預期：不含 %r（含其片段 %r）\n  實得：%r（命中整串 %r、片段 %r）"
            % (name, list(FAKE_CREDENTIAL_TOKENS),
               ["ZZTESTZZTEST", "zztest-not-real", "/zztest/not/real", "BEGIN ZZTEST"],
               value, hits, fragments),
        )


def check_a3(repo_root, fixtures, c):
    """A-3：受管區塊在無漂移時不重寫（連續兩輪）。

    這條斷言分兩層，兩層都必須有東西：

    **輸入層（本函式）**——連續兩輪對**語意相同、位元組不同**的 record，U-1 產生的三欄
    Decision 必須逐欄相同；語意真的變了的那一份必須至少一欄不同。三欄是 U-6 寫入理由判定
    （`aidlc-sync-forward-impl.yml` 的 R-5.2 ∪ R-5.6）逐字比對的東西。

    **閘門層**——「三欄相同 ⇒ 零看板寫入、零 commit」由 `run-orchestration-tests.py` 的
    `test_r5_5_no_drift_no_write` 與 `test_multi_round_suppressed_converges` 承接，本檔
    轉呼它。**不在這裡重寫一份**。

    另外把 U-2 的 R-2.3 隱含依賴變成可執行的事實：`decided_at` 在雜湊涵蓋範圍內，所以
    「兩次語意相同的判定會有不同的 decided_at ⇒ 不同雜湊」。該檔逐字寫「**這條依賴不在
    任何依賴圖上，也沒有任何測試會在它被破壞時失敗**」——下面的 HASH-2 就是那個測試。
    """
    names = ("a3-round-1-record.md", "a3-round-2-record.md", "a3-drift-record.md")
    texts = {}
    for name in names:
        path = fixtures / name
        if not path.is_file():
            raise ExternalError("找不到 A-3 的 fixture %s。" % path)
        texts[name] = path.read_text(encoding="utf-8")

    # 前提：兩輪的檔案內容**真的不同**。相同的話這條斷言只證明了「同一個字串跑兩次結果
    # 一樣」，那是 subprocess 的性質不是 U-1 的性質。
    c.check(
        "ROUND-0", texts[names[0]] != texts[names[1]],
        "兩輪 fixture 的位元組不同（語意相同、寫法不同）",
        "兩輪 fixture 的內容逐位元相同。這樣的「連續兩輪無漂移」只證明了同一個字串跑兩次"
        "結果一樣。\n  預期：兩份檔案內容不同\n  實得：完全相同",
    )

    r1 = decide(repo_root, texts[names[0]])
    r2 = decide(repo_root, texts[names[1]])
    drift = decide(repo_root, texts[names[2]])

    # 前提：三份都是實際會寫看板的判定（reason_code=mapped）。都是 undecidable 的話，
    # 「三欄相同」會因為三欄都是空值而恆真。
    for name, dec in ((names[0], r1), (names[1], r2), (names[2], drift)):
        c.check(
            "ROUND-0b:" + name, dec.get("reason_code") == "mapped",
            "%s 的判定是 mapped（會真的走到寫入鏈）" % name,
            "%s 的 reason_code 是 %r 而非 mapped。非 mapped 的判定三欄多為空值，"
            "「三欄相同」會在空值上恆真。\n  預期：mapped\n  實得：%r"
            % (name, dec.get("reason_code"), dec.get("reason_code")),
        )

    same = {k: (r1.get(k), r2.get(k)) for k in DRIFT_COLUMNS if r1.get(k) != r2.get(k)}
    c.check(
        "ROUND-1", not same,
        "連續兩輪的三欄 Decision 逐欄相同 ⇒ U-6 的寫入理由判定為「無漂移」",
        "連續兩輪對語意相同的 record 產生了不同的三欄 Decision，於是 U-6 每一輪都會判有"
        "漂移並重寫看板 item——看板上每個 item 每輪都會變一次，而**反向同步會把它讀成人為"
        "變更**。\n  預期：status／field_value／reason_code 三欄逐欄相同\n  實得：%r" % same,
    )

    differs = [k for k in DRIFT_COLUMNS if r1.get(k) != drift.get(k)]
    c.check(
        "ROUND-2", bool(differs),
        "語意真的變了時三欄至少一欄不同（%s）⇒ 比對確實在運作" % "、".join(differs),
        "語意變了（Current Stage 前進一站）但三欄 Decision 完全相同——**比對根本沒在區分"
        "任何東西**，於是 ROUND-1 的「無漂移」不是因為沒有漂移，是因為它什麼都比不出來。\n"
        "  預期：三欄至少一欄不同\n  實得：三欄全同（%r）" % r1,
    )

    # ---- U-2 層：R-2.3 的隱含依賴 -----------------------------------------
    fixed_at = "2026-09-06T00:00:00Z"
    body_1 = render_block(repo_root, decided_at=fixed_at, **{k: r1.get(k, "") for k in
                                                             ("status", "traceable_row", "reason_code", "scope_note")})
    body_2 = render_block(repo_root, decided_at=fixed_at, **{k: r2.get(k, "") for k in
                                                             ("status", "traceable_row", "reason_code", "scope_note")})
    c.check(
        "RENDER-1", body_1 == body_2,
        "同一個語意判定 ＋ 同一個 decided_at ⇒ 渲染出的區塊逐位元相同",
        "兩輪渲染出的區塊位元組不同。\n  預期：逐位元相同（%d bytes）\n  實得：%d vs %d bytes"
        % (len(body_1), len(body_1), len(body_2)),
    )

    h1, parsed_1 = hash_of_rendered(repo_root, body_1)
    h2, _ = hash_of_rendered(repo_root, body_2)
    c.check(
        "HASH-1", h1 == h2,
        "兩輪的 content_hash 相同（%s…）" % h1[:12],
        "兩輪的 content_hash 不同。\n  預期：相同\n  實得：%r vs %r" % (h1, h2),
    )

    # 前提：parse 真的認出了這是一個受管區塊。found=false 的話上面兩個雜湊會是「兩個空
    # Block 的雜湊相同」——同樣恆真。
    c.check(
        "HASH-1b", parsed_1.get("found") == "true" and parsed_1.get("has_marker") == "true",
        "渲染出的區塊真的被 parse 認出來（found=true、has_marker=true）",
        "parse 沒有把渲染出來的區塊認成受管區塊（found=%r、has_marker=%r）。此時兩邊算的"
        "都是空 Block 的雜湊，HASH-1 會恆真。\n  預期：found=true、has_marker=true\n"
        "  實得：found=%r、has_marker=%r"
        % (parsed_1.get("found"), parsed_1.get("has_marker"),
           parsed_1.get("found"), parsed_1.get("has_marker")),
    )

    # ---- HASH-2：mapped 支的區塊文字裡不得出現任何時間戳 --------------------
    #
    # 這一條是 HASH-1 為什麼成立的**理由**，而理由值得單獨斷言：`render` 對 mapped 支
    # 刻意不渲染 `decided_at`（U-2 的 functional-design iteration 4 Critical C-3），所以
    # 區塊文字裡沒有任何隨輪變動的值，兩輪的回讀雜湊才會相同。
    #
    # **本站實測更正了一個上游敘述**：U-2 `business-rules.md` R-2.3 的說明段寫「兩次語意
    # 相同的判定會有不同的 `decided_at` ⇒ 不同雜湊」。那對 mapped 支**不成立**——本檔實測
    # 同一個判定配兩個不同的 `decided_at`，回讀雜湊逐字相同（block.sh:284 只在 null-status
    # 支寫入 `LABEL_DECIDED_AT`）。U-2 自己的 `test_decided_at_only_in_null_status_branch`
    # 已經記載這件事（「churn 隱憂不作用於此支」），只是 R-2.3 的說明段沒有跟著改。
    # 這是**敘述過期**不是實作缺陷，登錄在交還報告，不由本單元回改上游。
    #
    # 為什麼不直接斷言「不含某個特定的 decided_at 字串」（U-2 的做法）：那擋不住有人把
    # `date -u` 的輸出寫進區塊。這裡掃的是**任何** ISO 8601 形狀的東西。
    timestamp_like = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    body_text = body_1.decode("utf-8")
    found_ts = timestamp_like.findall(body_text)
    c.check(
        "HASH-2", not found_ts,
        "mapped 支的區塊文字不含任何時間戳 ⇒ 兩輪的回讀雜湊在構造上就會相同",
        "mapped 支的區塊文字出現了時間戳 %r。區塊裡只要有一個隨輪變動的值，回讀雜湊每輪"
        "都會變，於是**反向同步每天會為每個受管 intent 各開一則 PR**（ADR-A6 點名的最危險"
        "失效模式）。\n  預期：區塊文字不含 ISO 8601 形狀的子字串\n  實得：%r\n  區塊全文：\n%s"
        % (found_ts, found_ts, body_text),
    )

    # 上面幾條合起來是 R-2.3 那段警告的可執行版本，但**結論與該段的字面相反**：mapped 支
    # 的雜湊本來就不會因 decided_at 而變，所以「無漂移不重寫」是**兩層**撐著的——構造上
    # 區塊不含時間戳（HASH-2），加上 U-6 的三欄比對（ROUND-1）。誰把 U-6 改成「每輪都蓋
    # 一次以自癒」，ROUND-1 不會紅（三欄還是相同），紅的會是轉呼的
    # run-orchestration-tests.py——這也是那次轉呼不能省的理由。


def check_upstream(repo_root, c):
    """轉呼上游既有驅動，並斷言它們**真的跑了、而且跑了指名的那幾條**。"""
    for rel, covers, required, label_hint, floors in UPSTREAM_DRIVERS:
        path = repo_root / rel
        # 代號帶檔名：`aidlc-sync-ci-guard` 之下有兩支驅動（F7 補上的），只用目錄名會讓
        # 兩者在報告上撞在一起。
        cid = "UPSTREAM:%s/%s" % (Path(rel).parent.name, Path(rel).stem)
        if not path.is_file():
            c.check(cid, False, "",
                    "找不到上游驅動 %s（承接：%s）。**不得因為它不在就跳過**——那會讓這些"
                    "斷言在檔案被移走時靜默消失。\n  預期：檔案存在\n  實得：不存在"
                    % (path, covers))
            continue
        try:
            proc = subprocess.run([sys.executable, str(path)], cwd=str(repo_root),
                                  capture_output=True, text=True, timeout=DRIVER_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            # **逾時是外部錯誤，不是斷言失敗**，而且必須指名是哪一支：job 的
            # `timeout-minutes: 10` 是有效上界，但它給的訊息是「job timed out」——診斷
            # 成本高一個量級，而診斷成本高的閘門會被當成雜訊。本 repo 已有這個形狀的
            # 實例（reviewer 注入代理式 CLI 之後測試掛住直到 pkill）。
            raise ExternalError(timeout_message("上游驅動 %s" % rel, path, DRIVER_TIMEOUT_S))
        summary = parse_driver_summary(proc.stdout)
        if proc.returncode != 0:
            tail = "\n".join(proc.stdout.splitlines()[-12:])
            c.check(cid, False, "",
                    "上游驅動 %s 以 rc=%d 結束（承接：%s）。\n  預期：rc=0\n  實得：rc=%d\n"
                    "  尾段輸出：\n%s" % (rel, proc.returncode, covers, proc.returncode, tail))
            continue
        if summary is None:
            c.check(cid, False, "",
                    "上游驅動 %s 的 rc＝0，但**解析不到它跑了幾條測試**（承接：%s）。只看 "
                    "rc 會被一個「刪光測試、直接 return 0」的空殼騙過，所以這裡判紅。\n"
                    "  預期：輸出含收尾行（%s）\n  實得：\n%s"
                    % (rel, covers, label_hint,
                       "\n".join(proc.stdout.splitlines()[-6:]) or "（無輸出）"))
            continue

        units, checks_n = summary["units"], summary["checks"]
        counted = (
            "%d %s、%d 失敗" % (units, summary["unit_label"], summary["failures"])
            if checks_n is None else
            "%d %s、%d 項斷言、%d 失敗"
            % (units, summary["unit_label"], checks_n, summary["failures"])
        )
        # ---- 斷言數基準：M-3 ------------------------------------------
        # 舊版只要求「> 0」，於是**清空一支測試的本體、保留名字與 docstring** 全綠——
        # 具名證據看的是名字在不在（在），總數看的是有沒有大於零（有）。reviewer 實跑：
        # 清空 `test_r5_5_no_drift_no_write` 的本體之後，CI log 上的斷言數由 154 掉到
        # **151**，數字就印在那一行，而同一行仍逐字宣稱它承接了「無漂移 ⇒ 零看板寫入、
        # 零 commit」。
        #
        # 基準值**由實跑取得**（每支都會印自己的收尾行），不是憑印象填的。斷言的是
        # 「實得 ≥ 基準」而不是「＝ 基準」：加測試不該讓這裡紅，減測試才該。
        units_floor, checks_floor = floors
        shortfalls = []
        if units < units_floor:
            shortfalls.append("%s %d < 基準 %d" % (summary["unit_label"], units, units_floor))
        if checks_floor is not None and (checks_n is None or checks_n < checks_floor):
            shortfalls.append("斷言數 %s < 基準 %d" % (checks_n, checks_floor))
        numbers_ok = (units > 0 and summary["failures"] == 0
                      and (checks_n is None or checks_n > 0)
                      and not shortfalls)
        if not numbers_ok:
            c.check(cid, False, "",
                    "上游驅動 %s 的 rc＝0 但數字不對（承接：%s）。**斷言數掉下去代表有測試"
                    "被刪掉或被清空**——那不會讓 rc 變成非 0，也不會讓具名證據消失。\n"
                    "  預期：單元數 ≥ %d、（若有）斷言數 ≥ %s、失敗數 ＝ 0\n  實得：%s%s"
                    % (rel, covers, units_floor,
                       checks_floor if checks_floor is not None else "不適用", counted,
                       ("\n  不足：" + "、".join(shortfalls)) if shortfalls else ""))
            continue

        # ---- 具名證據：F2 -------------------------------------------------
        # 「總數 > 0」擋得住把驅動刪光，擋不住把**這一次轉呼所宣稱承接的那幾條**刪掉——
        # 而 CI log 上那一行仍會逐字宣稱它承接了 A-4／A-5。
        missing = [m for m in required if m not in proc.stdout]
        c.check(
            cid, not missing,
            "%s：%s，且指名的 %d 條證據都出現在輸出（承接：%s）"
            % (rel, counted, len(required), covers),
            "上游驅動 %s 的數字看起來正常（%s），但**缺少這一次轉呼所宣稱承接的具名證據**"
            "：%r。承接關係若不指名，刪掉那幾條測試不會讓任何東西紅，而本檔仍會逐字宣稱"
            "它承接了「%s」。\n  預期：輸出含 %r\n  實得：缺 %r"
            % (rel, counted, missing, covers, list(required), missing),
        )


def main():
    ap = argparse.ArgumentParser(description="U-9 第一段：A-1／A-3 的 fixture 驅動 ＋ 轉呼上游驅動")
    ap.add_argument("--repo-root", default=None,
                    help="要驅動的 repo 樹根目錄（預設：由本檔位置推導）")
    ap.add_argument("--skip-upstream", action="store_true",
                    help="不轉呼四支上游驅動。**只給行為測試用**，CI 的呼叫不帶它")
    args = ap.parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[3]
    fixtures = resolve_fixture_dir(repo_root)
    print("repo 樹：%s\nfixture 目錄（由 %r 解析）：%s" % (repo_root, FIXTURE_DIR_GLOB, fixtures))

    c = Checker("第一段 fixture 驅動")
    check_a1(repo_root, fixtures, c)
    check_a3(repo_root, fixtures, c)
    if args.skip_upstream:
        print("（--skip-upstream：本次不轉呼上游驅動）")
    else:
        check_upstream(repo_root, c)
    return c.report()


if __name__ == "__main__":
    sys.exit(run_checker(main))
