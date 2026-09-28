#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U-9 的 A-6 靜態檢查：反向 PR 的寫入路徑與各 workflow 觸發設定的兩個集合關係。

A-6 逐字（`functional-design/domain-entities.md`）
------------------------------------------------
「U-8 實際寫入的路徑集合 ⊆ U-10a／U-10b 的 `paths-ignore` glob 集合」，而
`business-rules.md` R-3 補上第二半：「且該 glob 集合 ∩ 本單元的 allowlist ＝ ∅。
**兩個條件必須一起斷言**——只驗前者，某天有人把機制檔加進 `paths-ignore` 時不會有東西
失敗，而那會讓自我測試對機制變更靜默失效。」

所以本檔檢兩個關係，其中關係 2 有兩半：

  關係 1   推導出的寫入 glob ∈ 五個承載體各自的 paths-ignore 集合
  關係 2a  五個承載體**實際宣告**的整個 glob 集合 ∩ `aidlc-sync-selftest.yml` 的觸發
           allowlist ＝ ∅（DISJOINT-1）
  關係 2b  該 allowlist **涵蓋** A-6 斷言的那九個承載體檔案（COVERAGE-1）

關係 2a／2b 是 reviewer iteration 1 的 F3／F7
--------------------------------------------
**F3**：R-3:33 逐字要求的是「該 **glob 集合** ∩ 本單元的 allowlist ＝ ∅」，而第一版只跟
`derive_write_glob()` 回傳的**單一字串**比。reviewer 把本單元 allowlist 的兩條逐字加進
`ci.yml` 的 `paths-ignore`，得到 rc=0、15 項 0 失敗——那個設定下改機制的 PR 完全不跑 CI，
而自我測試對機制變更靜默失效，正是 R-3 那句話要防的事。

**F7**：A-6 斷言的九個檔案（`ci.yml` ＋ 四支 gh-aw 的 `.md`／`.lock.yml`）原本一個都不在
本單元的觸發 allowlist 內。後果是 **U-10b 上線後任何人把 `paths-ignore` 拿掉都不會觸發
U-9**——這道斷言只在沒人動它的時候才會執行，而把排除拿掉的那個 PR 正好是它唯一該紅的
時候。COVERAGE-1 的要求清單由 `GH_AW_CARRIERS` 產生，與關係 1 同一個來源。

寫入 glob 從哪裡來
------------------
**不在本檔寫死路徑字面值。** `check-ci-yml.py:110` 的 `derive_glob_from_record_sh()` 已經
從 U-4 `record.sh` 的白名單常數推導出這條 glob，本檔 import 它——同一個事實存兩份，其中
一份遲早會過期而沒人發現（本 intent 的 `[aidlc-sync]` 標記已經付過一次這個代價，見
U-10a 的 MARKER-1）。推導失敗時**一律非零退出**，不得靜默放行：推導不出來代表白名單的
形狀變了，需要人看過才能決定新的 glob 該長什麼樣。

五個承載體，檢查對象不是同一種檔案
--------------------------------
| 承載體 | 檢查對象 | 理由 |
| --- | --- | --- |
| `ci.yml`（U-10a） | `.yml` 本身 | 純 Actions，GitHub 直接執行它 |
| `ui-regression`／`pr-reviewer`／`lint-fix`／`contract-guard`（U-10b） | **`.lock.yml`（決定性）＋ `.md`（來源）** | 這四支是 gh-aw。**GitHub 執行的是編譯後的 `.lock.yml`，不是 `.md`** |

那四支因此各斷言三件事：lock 有、md 有、**兩者一致**。只檢 `.md` 會被「改了 `.md` 沒重新
編譯」這條漂移繞過——那正是 `open-items.md` 的 **N:M-5**（Major）逐字警告的形狀：「缺
`gh aw compile` ＋ commit `.lock.yml` 這一步（GitHub 執行的是 lock）；漏了則排除完全不
生效且無紅燈」。

**這與 N:C-3 不矛盾，兩者講的是不同的檔案集合。** N:C-3 講同步機制自己那四個邏輯
workflow（`aidlc-sync-*`）——它們是純 Actions、沒有 `.lock.yml`，所以 `check-agentic-steps.py`
的檢查對象是 `.yml`。本檔講的是**被排除的**那四支 gh-aw——它們有 lock，而 GitHub 跑的是
lock。

它對真實 repo 跑現在是綠的（U-10b 交付後翻面）
--------------------------------------------
**寫這段時 U-10b 尚未交付**，四支 gh-aw 的 `paths-ignore` 還不存在，所以本檢查器對本 repo
跑是紅的——那在當時是誠實的狀態（U-10b 未上線 ⇒ 反向 PR 真的會發動那四支）。

**U-10b 已交付**（四支的 `.md` 與 `.lock.yml` 都有那條 glob），所以它現在對真實 repo 跑
是**綠**的，16 項 0 失敗。`run-selftest-tests.py::test_the_real_repo_state_is_what_we_say_it_is`
的預期值已隨之翻面，並補上「通過代號逐項比對」以擋住「把檢查刪掉也是綠」。

**不得**為了讓它綠而把那四支寫成可選：那會讓 U-10b 被回退時沒有紅燈，正是 N:M-5 警告
的形狀。「對真實 repo 跑轉綠」是 **U-10b 的完成判準**，不是本單元的。

已知範圍限制（U-10b 交付時登錄）
------------------------------
`COMPILED:<名>` 的判定式是 `not (md_has and not lock_has)`，而兩個布林值都只是「**這一條
glob** 在不在 `on.pull_request.paths-ignore` 裡」——`paths_ignore_on_pull_request()` 從
frontmatter 只取那一個清單。因此本檢查器**偵測不到一般性的 lock 過期**：改 `types`／
`permissions`／`engine`／`tools`／`timeout-minutes`／`network` 或 prompt 本文而不重編，
GitHub 會跑一份過期的 lock，而這裡是綠的（實測：把 `ui-regression.md` 的 `types` 多加兩個
值、lock 不重編 ⇒ rc=0、16 項 0 失敗）。這是已登錄的缺口，不是本檔的 bug；收斂手段與
「為什麼不能靠 lock 的 `frontmatter_hash` 重現」見 U-10b 的 `code-summary.md` 交還清單
第 5 項。

用法與 exit code
----------------
    python3 .github/actions/aidlc-sync-selftest/check-paths-relations.py
    python3 .github/actions/aidlc-sync-selftest/check-paths-relations.py --repo-root <某棵樹>

    0  全數通過
    1  斷言失敗（第一行 `ASSERTION-FAILED:`）
    2  外部錯誤（第一行 `EXTERNAL-ERROR:`）——含「glob 推導不出來」

相依：PyYAML。
"""

import argparse
import fnmatch
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(path, name):
    """以路徑載入一支腳本當模組。三處 import 都走這裡，形狀一致。"""
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise SystemExit("EXTERNAL-ERROR: 無法載入 %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 失敗語意與 Checker 的單一真實來源（見 check-agentic-steps.py 的說明）。
_shared = _load(HERE / "check-agentic-steps.py", "aidlc_selftest_shared")
Checker = _shared.Checker
ExternalError = _shared.ExternalError
run_checker = _shared.run_checker
load_yaml = _shared.load_yaml
yaml = _shared.yaml

# U-10b 要改的四支 gh-aw workflow。清單來自該單元 `tech-stack-decisions.md` 的實測表
# （六支吃 pull_request，其中 code-drift-alert／local-dev-drift 已被自己的 paths allowlist
# 排除，剩下這四支無 paths 過濾）。
GH_AW_CARRIERS = ("ui-regression", "pr-reviewer", "lint-fix", "contract-guard")

SELFTEST_WORKFLOW = "aidlc-sync-selftest.yml"

# 反向同步 PR 仍然會觸發的 workflow（ci-pipeline stage，Q2=A）。
#
# 由來：U-10b 把四支 gh-aw 加上 `paths-ignore` 之後，「還剩幾個會跑」這件事只寫在
# `run-selftest-tests.py` 絆線訊息的一段**註解**裡，沒有任何斷言。後果是有人新增一支
# 無 paths 過濾的 `on: pull_request` workflow 時，反向 PR 會靜默地多觸發一個，而
# `IGNORE:` 那一族只看得到它列舉的五個承載體——**它驗的是「這幾個被排除了」，
# 不是「沒有別的跑起來」**。這兩件事不等價，而後者才是 [US:S-6 AC 7] 要的。
#
# 逐項理由（改這個清單就是在做一個決定，那一行 diff 就是紀錄）：
#   ci.yml               —— `pull_request` 側刻意不放 paths（`check-ci-yml.py` 的 SEC-1d
#                           明文禁止）。改由 U-10a 的 `gate` job 在 job 層跳過。
#   aidlc-sync-forward.yml — `on.pull_request` 無 paths、無 branches（U-10b 的 MAJOR-4）。
#                           它自己的兩道防線會讓該輪立刻跳出，成本是一個空轉的 run。
#   deploy.yml           —— `types: [closed], branches: [ut]`、**無 paths**：反向 PR
#                           **合併**時會觸發自架 runner 上 `timeout-minutes: 30` 的完整
#                           部署，為的是一個 JSON 欄位。處置涉及 ADR-0008 的部署模型，
#                           已登錄給 gate；在它被決定之前，這裡至少讓它可見。
REVERSE_PR_TRIGGERS = ("aidlc-sync-forward.yml", "ci.yml", "deploy.yml")


def _pr_config(doc):
    """一支 workflow 的 `on.pull_request` 設定；沒有宣告則回 None。"""
    trig = triggers_of(doc)
    if not isinstance(trig, dict) or "pull_request" not in trig:
        return None
    pr = trig.get("pull_request")
    return pr if isinstance(pr, dict) else {}


def reverse_pr_triggered(workflows, glob, base="ut"):
    """反向同步 PR 會觸發哪些 workflow。

    反向 PR 的變更集合**只有**同步狀態檔（`business-rules.md` R-2：diff 不含
    `aidlc-state.md` 任何一行），所以用一個代表性路徑代入 GitHub 的過濾語意即可：
    `paths-ignore` 全數命中即不觸發、`paths` allowlist 不命中即不觸發、`branches`
    不含 base 即不觸發。

    解析不開的檔一律**算它會觸發**（fail closed）——讀不到不等於安全。
    """
    changed = [glob.replace("*", "x")]
    fired, unreadable = [], []
    for path in sorted(workflows.glob("*.yml")):
        try:
            doc = load_yaml(path)
        except Exception:
            unreadable.append(path.name)
            fired.append(path.name)
            continue
        if not isinstance(doc, dict):
            continue
        pr = _pr_config(doc)
        if pr is None:
            continue
        branches = pr.get("branches")
        if branches and not any(fnmatch.fnmatch(base, b) for b in branches):
            continue
        ignore = pr.get("paths-ignore")
        if ignore and all(any(fnmatch.fnmatch(c, pat) for pat in ignore) for c in changed):
            continue
        allow = pr.get("paths")
        if allow and not any(fnmatch.fnmatch(c, pat) for pat in allow for c in changed):
            continue
        fired.append(path.name)
    return fired, unreadable


# 四支承載體的 `.lock.yml` 必須由**這個版本**的 gh-aw 編出（ci-pipeline stage，Q4=A）。
#
# 由來：U-10b 的 `code-summary.md` 逐字「**沒有任何機械檢查會擋下「用較新版本重編」**
# ——`COMPILED:` 只驗那一條 glob，不驗 `compiler_version`」。它同時實測了代價：用本機
# 預設的 v0.86.2 重編，每檔 diff 從 4 行變成 526 行，且 `gh-aw-manifest` 會換掉
# `actions/cache` v5.0.5→v6.1.0、`actions/checkout` v7.0.0→v7.0.1、
# `actions/setup-node` v6.4.0→v7.0.0、防火牆容器 0.27.11→0.27.44、
# `gh-aw-mcpg` v0.3.30→v0.4.9、`github-mcp-server` v1.4.0→v1.9.0——**六個新 SHA 與映像，
# 依 ADR-0006 每一個都需要安全審查**。
#
# 升級 gh-aw 本身沒有問題，問題是它**夾帶在一個看起來無關的 PR 裡**而沒有人看見。
# 這條斷言不禁止升級，它只讓升級變成一個必須被明講的決定：改這個常數的那一行 diff
# 就是那個決定。
#
# **範圍限於四支承載體**（與本檔其餘檢查同一個 GH_AW_CARRIERS）。本 repo 另有 7 支
# gh-aw workflow 當時也都是 v0.81.6，同樣暴露在這個風險上，但它們不是 U-10b 的交付物
# ——擴大到 11 支是獨立決定，登錄於 ci-pipeline 的 `quality-gates.md`。
#
# 2026-09-06：`ut` 已在 PR #532「建置(ci): gh-aw 由 v0.81.6 升級至 v0.86.2 並重新編譯全部
# workflow」**明講地**完成那次升級（11 支全部重編，四支承載體在內）；本分支併入 `ut` 後，
# 四支 lock 以 v0.86.2 對合併後的 `.md` 重編。本常數改為同值——這一行 diff 就是上文所說
# 「必須被明講的決定」的紀錄；上文列出的 action SHA 與映像差異已由 #532 承擔審查，
# 不是夾帶在本 PR 裡。
PINNED_COMPILER_VERSION = "v0.86.2"

# lock 首行 metadata 註解的前綴。**按名字到 agentic-tokens.json 取，不寫字面值**——
# 那個前綴含 R-1.2 的被禁字樣，而本檔在掃描面上（`aidlc-sync-selftest.yml` job fixtures
# 的 step 5）。這與 run-selftest-tests.py 取 agent_cli／agent_action_repo 是同一條路：
# 具名查表，不是把字串拆開寫——後者正是本檢查宣告擋不住的那種刻意混淆。
_LOCK_METADATA_PREFIX = _shared.NAMED_TOKENS["lock_metadata_prefix"]

# 訊息裡要印出編譯器的名字給讀的人看，但**同樣不能寫成字面值**（同一個被禁字樣）。
# 從具名表的 agent_action_repo（"<org>/<tool>"）取尾段，輸出的字是真的那個名字，
# 原始碼裡卻不出現它——與上面同一條路。
_COMPILER_NAME = _shared.NAMED_TOKENS["agent_action_repo"].split("/")[-1]


def gh_aw_compiler_version(path):
    """從 `.lock.yml` 第一行的 `# gh-aw-metadata: {...}` 取出 compiler_version。

    讀不到、解不開、或欄位缺席時一律 raise——**不得回 None 讓呼叫端當成通過**。
    這與本檔其餘的 fail-closed 立場一致：推導不出來代表判定基準不存在，而不是
    「沒問題」。
    """
    with open(path, "r", encoding="utf-8") as fh:
        first = fh.readline().rstrip("\n")
    if not first.startswith(_LOCK_METADATA_PREFIX):
        raise ExternalError(
            "%s 的第一行不是 `%s…`，取不到 compiler_version。\n  實得首行：%r"
            % (path, _LOCK_METADATA_PREFIX.strip(), first[:120]))
    try:
        meta = json.loads(first[len(_LOCK_METADATA_PREFIX):])
    except ValueError as exc:
        raise ExternalError("%s 首行的 %s metadata 不是合法 JSON：%s"
                            % (path, _COMPILER_NAME, exc))
    if "compiler_version" not in meta:
        raise ExternalError(
            "%s 的 gh-aw-metadata 沒有 compiler_version 欄位。\n  實得鍵：%r"
            % (path, sorted(meta)))
    return meta["compiler_version"]



# ==========================================================================
# glob 交集判定
# ==========================================================================
def _tokenize_segment(seg):
    """把一個路徑片段拆成 token：`*`、`?`、或單一字面字元。片段內不含 `/`。"""
    return list(seg)


def _segments_may_intersect(x, y):
    """兩個**不含 `/` 也不含 `**`** 的 glob 片段是否存在共同字串。

    這是一個標準的雙 pattern 交集判定（product automaton 的 DP 版）：
    `go(i, j)` ＝「x[i:] 與 y[j:] 是否存在共同的可產生字串」。

    - 任一邊是 `*` 時，它可以吃掉 0 個字元（跳過自己），也可以吸收對面產生的一個字元
      （對面往前一格，自己留在原地由下一輪再決定）——後者在 `*` 的語意下等價於
      `go(i, j+1)`，因為「以 `*` 開頭的樣式能配 c+s'」⟺「它能配 s'」。
    - 兩邊都產生剛好一個字元時（字面／`?`），字元類必須相交。

    手工驗過的四組：`*a` vs `*b` → 否；`*a` vs `*a` → 是；`a*` vs `*b` → 是（"ab"）；
    `abc` vs `a?c` → 是。
    """
    xs, ys = _tokenize_segment(x), _tokenize_segment(y)
    memo = {}

    def go(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if i == len(xs) and j == len(ys):
            memo[key] = True
            return True
        if i == len(xs):
            memo[key] = all(t == "*" for t in ys[j:])
            return memo[key]
        if j == len(ys):
            memo[key] = all(t == "*" for t in xs[i:])
            return memo[key]
        a, b = xs[i], ys[j]
        result = False
        if a == "*":
            result = go(i + 1, j) or go(i, j + 1)
        if not result and b == "*":
            result = go(i, j + 1) or go(i + 1, j)
        if not result and a != "*" and b != "*":
            same = a == "?" or b == "?" or a == b
            result = same and go(i + 1, j + 1)
        memo[key] = result
        return result

    return go(0, 0)


DSTAR = "**"


def _split_pattern(pattern):
    """把一條 glob 拆成片段串列，`**` 自成一個片段。

    `**` 若與別的字元混在同一個片段裡（`a/x**y/b`），本檢查**拒絕判定**並丟 ExternalError
    ——那種樣式的涵蓋範圍需要人看過，而猜錯的兩個方向都很貴（猜寬 ⇒ 假紅燈、猜窄 ⇒ 靜默
    放行）。目前 repo 內沒有這種樣式；哪天有了，紅燈會指名是哪一條。
    """
    segments = pattern.split("/")
    for seg in segments:
        if DSTAR in seg and seg != DSTAR:
            raise ExternalError(
                "路徑樣式 %r 的片段 %r 把 `**` 與其他字元混在一起。本檢查只判定 `**` 自成"
                "一個片段的形式；混寫的涵蓋範圍請人工判定後再改本檔（fail closed，不猜）。"
                % (pattern, seg)
            )
    return segments


def globs_may_intersect(a, b):
    """兩條 GitHub 路徑過濾 glob 是否可能同時命中某個路徑。

    GitHub 的語意：`*` 配任意個非 `/` 字元、`**` 配任意個字元（含 `/`）、`?` 配一個非 `/`
    字元。

    做法是**片段層級的 DP**，與片段內的 DP 同一個形狀，只是把 `**` 當成「吃掉 0 個以上的
    片段」：

      go(i, j) ＝ X 的第 i 個片段之後與 Y 的第 j 個片段之後是否存在共同路徑

      - 一邊耗盡：另一邊剩下的必須全是 `**`
      - 任一邊是 `**`：它可以吃 0 個片段（`go(i+1, j)`），也可以吸收對面的一個片段
        （`go(i, j+1)`——`**` 開頭的樣式能配 `c/s'` ⟺ 它能配 `s'`）
      - 兩邊都是普通片段：片段本身要能相交，且其後也要能相交

    手工驗過的四組（本檔的實際輸入形狀）：

      `aidlc/spaces/*/intents/*/.test-fixtures/**` vs `aidlc/spaces/*/intents/*/sync-state.json`
          → **否**（第 6 段 `.test-fixtures` 與 `sync-state.json` 不相交）
      `aidlc/**`        vs 同上 glob → **是**
      `**/sync-state.json` vs 同上 glob → **是**
      `.github/actions/aidlc-sync-*/**` vs 同上 glob → **否**（第 1 段就不相交）

    **早期版本對含 `**` 的樣式改用「比對字面前綴」的保守判定，那是錯的**：`.test-fixtures`
    的 allowlist 與寫入 glob 的字面前綴都是 `aidlc/spaces/`，會被判成相交而讓 DISJOINT-1
    在一個實際無交集的設定上假紅燈。假紅燈與漏放行一樣會讓閘門失去作用，所以這裡做的是
    精確判定而不是更保守的判定。

    `!` 開頭的否定樣式與 `+` 量詞都不支援——遇到就丟 ExternalError（fail closed）。
    """
    for pattern in (a, b):
        if pattern.startswith("!"):
            raise ExternalError(
                "路徑樣式 %r 使用了否定語法。本檢查不支援否定樣式——它會反轉集合關係的方向，"
                "而 A-6 的兩個關係都建立在「這條 glob 涵蓋哪些路徑」上。請人工判定後再改本檔。"
                % pattern
            )
        # GitHub 的路徑過濾語法有 `+`（配一個以上的前一個字元）。第一版把它當成字面字元，
        # 與同函式對 `!` 與混寫 `**` 的 fail-closed 處理不一致（reviewer iteration 1 的
        # F11）。猜錯的兩個方向都很貴：猜寬是假紅燈、猜窄是靜默放行——所以不猜。
        if "+" in pattern:
            raise ExternalError(
                "路徑樣式 %r 使用了 `+` 量詞（GitHub 的路徑過濾語法支援它，本交集判定不支"
                "援）。把它當成字面字元會讓判定悄悄地算錯一邊，所以這裡拒絕判定。請人工判"
                "定該樣式的涵蓋範圍後再改本檔。" % pattern
            )
    xs, ys = _split_pattern(a), _split_pattern(b)
    memo = {}

    def go(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if i == len(xs) and j == len(ys):
            memo[key] = True
            return True
        if i == len(xs):
            memo[key] = all(s == DSTAR for s in ys[j:])
            return memo[key]
        if j == len(ys):
            memo[key] = all(s == DSTAR for s in xs[i:])
            return memo[key]
        sx, sy = xs[i], ys[j]
        result = False
        if sx == DSTAR:
            result = go(i + 1, j) or go(i, j + 1)
        if not result and sy == DSTAR:
            result = go(i, j + 1) or go(i + 1, j)
        if not result and sx != DSTAR and sy != DSTAR:
            result = _segments_may_intersect(sx, sy) and go(i + 1, j + 1)
        memo[key] = result
        return result

    return go(0, 0)


# ==========================================================================
# 讀取觸發設定
# ==========================================================================
def triggers_of(doc):
    """取 workflow 的 `on:` 區塊。YAML 1.1 把裸 `on` 當布林，鍵會是 True。"""
    return doc.get("on", doc.get(True))


def paths_ignore_anywhere(doc):
    """一份 workflow 在**任何**觸發器上宣告的 paths-ignore 的聯集。

    刻意不指定觸發器，因為五個承載體的形狀本來就不同：`ci.yml` 把它放在 `on.push`（它的
    `pull_request` 側刻意不放——`check-ci-yml.py` 的 SEC-1d 明文禁止，理由是一般開發者的
    PR 永遠還有別的檔案、過濾永遠不成立），四支 gh-aw 放在 `on.pull_request`（反向 PR 只
    改一個檔，過濾才成立）。A-6 問的是「這條 glob 在不在它的排除集合裡」，不是「放在哪個
    觸發器上」——後者由各單元自己的檢查負責，本檔重複指定只會與 SEC-1d 打架。
    """
    trig = triggers_of(doc)
    out = []
    if isinstance(trig, dict):
        for event, spec in trig.items():
            if isinstance(spec, dict) and isinstance(spec.get("paths-ignore"), list):
                out.extend(str(p) for p in spec["paths-ignore"])
    return out


def paths_ignore_on_pull_request(doc):
    trig = triggers_of(doc)
    if not isinstance(trig, dict):
        return []
    pr = trig.get("pull_request")
    if not isinstance(pr, dict) or not isinstance(pr.get("paths-ignore"), list):
        return []
    return [str(p) for p in pr["paths-ignore"]]


def load_gh_aw_frontmatter(path):
    """讀 gh-aw `.md` workflow 的 frontmatter（第一組 `---` 之間的 YAML）。"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ExternalError(
            "%s 沒有以 `---` 開頭的 frontmatter。gh-aw workflow 的觸發設定全部在 "
            "frontmatter 裡，讀不到它就無法判定排除設定——**不得因此視為通過**。" % path
        )
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            body = "\n".join(lines[1:idx])
            break
    else:
        raise ExternalError("%s 的 frontmatter 沒有結束的 `---`。" % path)
    try:
        doc = yaml.safe_load(body)
    except yaml.YAMLError as exc:
        raise ExternalError("%s 的 frontmatter 不是合法 YAML：%s" % (path, exc))
    if not isinstance(doc, dict):
        raise ExternalError("%s 的 frontmatter 不是一個 mapping。" % path)
    return doc


# ==========================================================================
# 主體
# ==========================================================================
def derive_write_glob(repo_root):
    """從 U-4 的 record.sh 推導同步回寫唯一寫得到的路徑 glob。

    **import `check-ci-yml.py` 的既有推導，不自抄一份。** 它的模組層常數 RECORD_SH 指向
    真實 repo，這裡就地改指到 `repo_root` 之下——行為測試要能用合成的暫存樹驅動本檔，而
    「換一棵樹」不該變成「換一份推導邏輯」。
    """
    guard_path = repo_root / ".github" / "actions" / "aidlc-sync-ci-guard" / "check-ci-yml.py"
    if not guard_path.is_file():
        raise ExternalError(
            "找不到 %s。本檔 import 它的 derive_glob_from_record_sh() 來推導寫入 glob；"
            "它不在時**不得改用寫死的字面值**——那正是這個 import 要避免的事。" % guard_path
        )
    guard = _load(guard_path, "aidlc_sync_ci_guard")
    guard.RECORD_SH = repo_root / ".github" / "actions" / "aidlc-sync-record" / "record.sh"
    try:
        return guard.derive_glob_from_record_sh()
    except SystemExit as exc:
        # check-ci-yml.py 以 SystemExit 表達「推導不出來」。轉成本檔的外部錯誤語意，
        # 訊息原樣轉述——它已經寫明缺的是哪一個常數。**不得吞掉改為通過**（fail closed）。
        raise ExternalError(
            "從 record.sh 推導寫入 glob 失敗，A-6 的兩個關係都失去比對基準：%s" % (exc,)
        )


def check(repo_root):
    workflows = repo_root / ".github" / "workflows"
    if not workflows.is_dir():
        raise ExternalError("找不到 %s。" % workflows)

    glob, why = derive_write_glob(repo_root)
    c = Checker("A-6 路徑集合關係")
    print("推導出的同步回寫 glob：%s\n  %s" % (glob, why))

    # 五個承載體**實際宣告**的每一條 paths-ignore，附它來自哪一份檔案。
    #
    # reviewer iteration 1 的 F3：關係 2 原本只跟 `derive_write_glob()` 回傳的**單一字串**
    # 求交集，而 R-3:33 逐字要求的是「該 **glob 集合** ∩ 本單元的 allowlist ＝ ∅」。
    # reviewer 把本單元 allowlist 的兩條逐字加進 ci.yml 的 paths-ignore，15 項檢查 0 失敗
    # ——那個設定下改機制的 PR 完全不跑 CI，而自我測試對機制變更靜默失效。
    declared_all = []

    # ---- 關係 1：五個承載體 -----------------------------------------------
    ci_yml = workflows / "ci.yml"
    if not ci_yml.is_file():
        c.check("IGNORE:ci.yml", False, "",
                "找不到 %s。它是 U-10a 的承載體，缺席時反向 PR 會發動 CI 的四道關卡。\n"
                "  預期：檔案存在且 paths-ignore 含 %r\n  實得：檔案不存在" % (ci_yml, glob))
    else:
        declared = paths_ignore_anywhere(load_yaml(ci_yml))
        declared_all.extend(("ci.yml", g) for g in declared)
        c.check(
            "IGNORE:ci.yml", glob in declared,
            "ci.yml 的 paths-ignore 含 %r" % glob,
            "ci.yml 的 paths-ignore 不含同步回寫的寫入 glob。\n  預期：集合含 %r\n  實得：%r"
            % (glob, declared),
        )

    for name in GH_AW_CARRIERS:
        md = workflows / ("%s.md" % name)
        lock = workflows / ("%s.lock.yml" % name)

        md_has = None
        if not md.is_file():
            c.check("IGNORE:%s.md" % name, False, "",
                    "找不到 %s。\n  預期：檔案存在\n  實得：不存在" % md)
        else:
            md_declared = paths_ignore_on_pull_request(load_gh_aw_frontmatter(md))
            declared_all.extend(("%s.md" % name, g) for g in md_declared)
            md_has = glob in md_declared
            c.check(
                "IGNORE:%s.md" % name, md_has,
                "%s.md 的 frontmatter on.pull_request.paths-ignore 含 %r" % (name, glob),
                "%s.md 的 frontmatter 沒有把同步回寫的寫入 glob 排除掉。這是 U-10b 的交付"
                "物；缺了它，反向 PR 會發動這支 workflow。\n  預期：on.pull_request.paths-ignore"
                " 含 %r\n  實得：%r" % (name, glob, md_declared),
            )

        lock_has = None
        if not lock.is_file():
            c.check("IGNORE:%s.lock.yml" % name, False, "",
                    "找不到 %s。**GitHub 執行的是編譯後的 lock，不是 `.md`**——lock 不存在"
                    "等於這支 workflow 的排除設定不存在。\n  預期：檔案存在\n  實得：不存在"
                    % lock)
        else:
            lock_declared = paths_ignore_on_pull_request(load_yaml(lock))
            declared_all.extend(("%s.lock.yml" % name, g) for g in lock_declared)
            lock_has = glob in lock_declared
            c.check(
                "IGNORE:%s.lock.yml" % name, lock_has,
                "%s.lock.yml 的 on.pull_request.paths-ignore 含 %r（**這是決定性的那一條**）"
                % (name, glob),
                "%s.lock.yml 沒有把同步回寫的寫入 glob 排除掉。**GitHub 執行的是這一份**，"
                "所以無論 `.md` 寫了什麼，排除實際上都沒有生效。\n  預期：on.pull_request."
                "paths-ignore 含 %r\n  實得：%r" % (name, glob, lock_declared),
            )

        # 一致性：`.md` 有而 lock 沒有 ＝ 改了來源但沒有重新編譯（N:M-5）。
        if md_has is not None and lock_has is not None:
            c.check(
                "COMPILED:%s" % name, not (md_has and not lock_has),
                "%s 的 `.md` 與 `.lock.yml` 對這條 glob 的宣告一致" % name,
                "%s 的 `.md` 已經加上 paths-ignore，但 `.lock.yml` 沒有——**`.md` 改了但 "
                "`.lock.yml` 未重新編譯**（`gh aw compile %s` 之後要把 lock 一併 commit）。GitHub 跑的是 "
                "lock，所以這個排除目前完全沒有生效，而且不會有任何錯誤訊息。這正是 "
                "`open-items.md` N:M-5 逐字警告的形狀。\n  預期：md 有 ⇒ lock 也有\n"
                "  實得：md 有＝%s，lock 有＝%s" % (name, name, md_has, lock_has),
            )

        # 編譯器版本：lock 必須由釘住的 gh-aw 編出（ci-pipeline Q4=A）。
        # `COMPILED:` 驗的是 glob 一致性，完全不看是誰編的——這一條補的正是那個缺口。
        if lock.is_file():
            try:
                found = gh_aw_compiler_version(lock)
            except ExternalError as exc:
                c.check("COMPILER:%s" % name, False, "",
                        "讀不到 %s.lock.yml 的 compiler_version，無法判定它是不是由釘住的 "
                        "%s 編出。**不得因為讀不到而視為通過**。\n  %s"
                        % (name, _COMPILER_NAME, exc))
            else:
                c.check(
                    "COMPILER:%s" % name, found == PINNED_COMPILER_VERSION,
                    "%s.lock.yml 由釘住的 %s %s 編出"
                    % (name, _COMPILER_NAME, PINNED_COMPILER_VERSION),
                    "%s.lock.yml 是用**別的** gh-aw 版本編的。用較新的版本重編會一併換掉 "
                    "`gh-aw-manifest` 裡的 action SHA、防火牆容器與 MCP server 映像——依 "
                    "ADR-0006 每一個都需要安全審查，而它們此刻正夾帶在這個 PR 裡沒有被"
                    "看見。\n  若這次**確實是**刻意升級：改 check-paths-relations.py 的 "
                    "PINNED_COMPILER_VERSION，那一行 diff 就是這個決定的紀錄。\n"
                    "  預期：%s\n  實得：%s" % (name, PINNED_COMPILER_VERSION, found),
                )

    # ---- 關係 1b：反向 PR 的觸發閉包 ---------------------------------------
    fired, unreadable = reverse_pr_triggered(workflows, glob)
    for name in unreadable:
        c.check("PR-TRIGGER-READ:%s" % name, False, "",
                "讀不到 %s 的觸發宣告，無法判定反向 PR 會不會觸發它。**讀不到不等於"
                "安全**，故一律計入會觸發的集合。\n  預期：可解析\n  實得：解析失敗" % name)
    c.check(
        "PR-TRIGGER-1", sorted(fired) == sorted(REVERSE_PR_TRIGGERS),
        "反向同步 PR 會觸發的 workflow 恰為釘住的 %d 支：%s"
        % (len(REVERSE_PR_TRIGGERS), "、".join(sorted(REVERSE_PR_TRIGGERS))),
        "反向同步 PR 觸發的 workflow 集合與釘住的清單不符。**`IGNORE:` 那一族驗的是"
        "「這幾個被排除了」，不是「沒有別的跑起來」**——新增一支無 paths 過濾的 "
        "`on: pull_request` workflow 不會讓 IGNORE 任何一項變紅，但反向 PR 每天都會"
        "多觸發它一次。\n  多出來的：%s\n  少掉的：%s\n  預期：%s\n  實得：%s"
        % (sorted(set(fired) - set(REVERSE_PR_TRIGGERS)) or "（無）",
           sorted(set(REVERSE_PR_TRIGGERS) - set(fired)) or "（無）",
           sorted(REVERSE_PR_TRIGGERS), sorted(fired)),
    )

    # ---- 關係 2：glob 集合 ∩ 本單元 allowlist ＝ ∅ -------------------------
    selftest = workflows / SELFTEST_WORKFLOW
    if not selftest.is_file():
        c.check("DISJOINT-1", False, "",
                "找不到 %s，無法判定關係 2。**不得因為讀不到而視為無交集**——那會讓這半條"
                "斷言在檔案被改名時靜默消失。\n  預期：檔案存在\n  實得：不存在" % selftest)
    else:
        trig = triggers_of(load_yaml(selftest))
        pr = trig.get("pull_request") if isinstance(trig, dict) else None
        allowlist = [str(p) for p in (pr or {}).get("paths", [])] if isinstance(pr, dict) else []
        c.check(
            "ALLOWLIST-1", bool(allowlist),
            "%s 的 on.pull_request.paths 有 %d 條：%r" % (SELFTEST_WORKFLOW, len(allowlist), allowlist),
            "%s 沒有宣告 on.pull_request.paths。**沒有 allowlist ＝ 每個 PR 都觸發**，關係 2"
            "（與排除 glob 無交集）會以最壞的方式被違反。\n  預期：≥ 1 條\n  實得：%r"
            % (SELFTEST_WORKFLOW, allowlist),
        )
        # 比對對象＝推導出的寫入 glob ∪ 五個承載體**實際宣告**的每一條 paths-ignore。
        # 只比前者是 F3 的形狀：把機制檔加進某個承載體的排除集合不會讓任何東西失敗。
        targets = [("record.sh 推導的寫入 glob", glob)] + declared_all
        print("納入交集判定的排除 glob 共 %d 條：%s"
              % (len(targets), "、".join("%s←%s" % (g, label) for label, g in targets)))
        overlaps = [(p, label, g) for p in allowlist for label, g in targets
                    if globs_may_intersect(p, g)]
        c.check(
            "DISJOINT-1", not overlaps,
            "本單元的 allowlist 與全部 %d 條排除 glob 皆無交集" % len(targets),
            "本單元的 allowlist 與某個承載體宣告的排除 glob 有交集：%s。兩個後果都不能接受"
            "——反向 PR（只改資料不改機制）會觸發自我測試；而該 paths-ignore 又會讓改機制的 "
            "PR 被擋掉，自我測試對機制變更靜默失效（R-3 逐字：兩個條件必須一起斷言）。\n"
            "  預期：allowlist 的每一條都與全部 %d 條排除 glob 無交集\n  實得：%s"
            % ("；".join("allowlist %r ∩ %r（來自 %s）" % (p, g, label)
                         for p, label, g in overlaps),
               len(targets),
               "；".join("allowlist %r ∩ %r（來自 %s）" % (p, g, label)
                         for p, label, g in overlaps)),
        )

        # ---- 關係 2 的另一半：allowlist 必須涵蓋 A-6 斷言的那九個檔案 ------
        #
        # reviewer iteration 1 的 F7：A-6 斷言的九個檔案（ci.yml ＋ 四支 gh-aw 的
        # `.md`／`.lock.yml`）一個都不在本單元的觸發 allowlist 內。後果是 U-10b 上線後，
        # 任何人把 paths-ignore 拿掉都**不會觸發 U-9**——這道斷言只在沒人動它的時候才會
        # 執行。要求清單由 GH_AW_CARRIERS 產生，與上面關係 1 的檢查同一個來源。
        required = [".github/workflows/ci.yml"] + [
            ".github/workflows/%s.%s" % (name, ext)
            for name in GH_AW_CARRIERS for ext in ("md", "lock.yml")
        ]
        uncovered = [r for r in required
                     if not any(globs_may_intersect(p, r) for p in allowlist)]
        c.check(
            "COVERAGE-1", not uncovered,
            "本單元的 allowlist 涵蓋 A-6 斷言的全部 %d 個承載體檔案" % len(required),
            "本單元的 allowlist 沒有涵蓋 A-6 斷言的這些承載體檔案：%r。**改它們的 PR 不會"
            "觸發自我測試**，於是 A-6 這道斷言只在沒人動它的時候才會執行——把 paths-ignore "
            "拿掉的那一個 PR，正好是它唯一該紅的時候。\n  預期：allowlist 涵蓋 %r\n  實得："
            "沒涵蓋 %r" % (uncovered, required, uncovered),
        )

        # ---- 關係 2 的第三面：allowlist 必須涵蓋整個 R-1.2 掃描面 ----------
        #
        # reviewer iteration 3 的 F1（Major）。COVERAGE-1 與 COVERAGE-2 是**同一種缺口
        # 的兩個方向**：前者管「A-6 斷言的那九個檔案要在 allowlist 內」，後者管「R-1.2
        # 掃得到的每一個檔案要在 allowlist 內」。iteration 1 的 F7 關上前者，iteration 2
        # 的 C-1 把掃描面由 1 檔擴為 34 檔、又把後者打開了——其中 11 檔（`frontend/`、
        # `deploy/`、`.claude/` 底下的）不在 allowlist 內。
        #
        # 為什麼這是 Major 而不是潔癖：掃得到但不在 allowlist 內的檔案，**改它的那個 PR
        # 不會跑自我測試**，於是它引入的違規會讓「下一個改同步機制的 PR」紅。
        # `business-rules.md` R-4 逐字：「一個會誤報的閘門，比沒有閘門更快失去作用。」
        #
        # 掃描面由受測檢查器自己算（`_shared.scan_surface`），不在這裡抄第二份——抄一份
        # 就等於讓兩邊各自漂移，而漂移的那一天兩邊都是綠的。
        surface = _shared.scan_surface(repo_root)
        uncovered_surface = [
            rel for rel in surface
            if rel not in _shared.SCAN_EXEMPT
            and not any(globs_may_intersect(pat, rel) for pat in allowlist)
        ]
        c.check(
            "COVERAGE-2", not uncovered_surface,
            "本單元的 allowlist 涵蓋 R-1.2 掃描面的全部 %d 個檔案" % len(surface),
            "R-1.2 的掃描面有 %d 個檔案不在本單元的觸發 allowlist 內：%s。\n"
            "**改這些檔的 PR 不會觸發自我測試**，所以它們引入的違規不會讓那個 PR 紅——"
            "紅燈會落在下一個改同步機制的 PR 上，而那個 PR 的作者什麼都沒做錯。一個會誤報"
            "的閘門，比沒有閘門更快失去作用（R-4）。\n"
            "  兩條修法，二選一：把它們補進 `on.pull_request.paths`（若它們真的會被執行）；"
            "或讓它們根本不進掃描面（若它們只是被某支腳本**提到**而不是被呼叫）。\n"
            "  預期：掃描面 ⊆ allowlist ∪ SCAN_EXEMPT\n  實得：未涵蓋 %r"
            % (len(uncovered_surface), "、".join(uncovered_surface), uncovered_surface),
        )

    return c.report()


def main():
    ap = argparse.ArgumentParser(description="U-9 A-6：反向 PR 寫入路徑與觸發設定的集合關係")
    ap.add_argument("--repo-root", default=None,
                    help="要檢查的 repo 樹根目錄（預設：由本檔位置推導）。行為測試用它餵合成的暫存樹。")
    args = ap.parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[3]
    print("repo 樹：%s" % repo_root)
    return check(repo_root)


if __name__ == "__main__":
    sys.exit(run_checker(main))
