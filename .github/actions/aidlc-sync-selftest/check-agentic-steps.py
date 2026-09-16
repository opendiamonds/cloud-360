#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U-9 的 R-1.2 靜態檢查：同步機制的決定性步驟不含代理式引擎。

掃描集合＝**執行可達閉包**，不是「檔案放在哪個目錄」（iteration 2 的 C-1，Critical）
------------------------------------------------------------------------------
這條邊界已經被推過兩次，兩次都是「往外挪一格」而不是換原則：

  iteration 1：只 glob `.github/workflows/aidlc-sync-*.yml` ⇒ 五份 composite action
               從頭到尾沒被開過。
  iteration 2：補上 `.github/actions/aidlc-sync-*/` 底下的 `.sh`／`.py`。

reviewer 對 iteration 2 構造了五個繞過，**每一個單獨都 rc=0、「0 失敗」**，其中最要命的
那個**完全不需要惡意**：

    # aidlc-sync-forward-impl.yml
    run: python3 scripts/decide-status.py
    # scripts/decide-status.py
    subprocess.run(["copilot", "-p", "which Status for this row?"], ...)

`scripts/` 本來就是本 repo 的慣用落點（`ci.yml` 有三個呼叫點）。把 helper 放那裡不是繞過
技巧，是照著既有形狀寫程式。目錄清單再加一格只會把同一個洞往外挪一格——下一次有人放
`tools/`。

**所以本檔改用「執行可達性」定義掃描集合**：

  種子 ＝ 四支同步 workflow 的全部原始檔 ＋ `ci.yml`（M-5，見下）
  展開 ＝ 對每一個已在掃描面上的 `run:` 本體或腳本本體，解析出它呼叫的**本 repo 檔案**
         （`python3 X`／`python X`／`bash X`／`sh X`／`source X`／`. X`／`./X`），
         遞迴加入掃描集合，直到不動點。

「判定被搬到哪個目錄」因此不再是一個問題——只要它會被執行到，它就在掃描面上；不會被執行
到的東西，本來就不需要檢查。

**解析不出來的呼叫目標 fail-closed**（回非零並指名是哪一行）。與同 repo 既有處置一致：
`check-paths-relations.py` 對 `+` 量詞、`check-ci-yml.py` 的 glob 推導失敗都是這個形狀。
先解得開的一律解開再談（見 `expand_vars`）：

  - Actions 內建變數 `GITHUB_ACTION_PATH`（該 action 的目錄）與 `GITHUB_WORKSPACE`
    （checkout 根）先展開；
  - 同一段腳本裡的字面賦值（`ACTIONS_DIR="${WORKSPACE}/.github/actions"`）遞迴展開——
    本 repo 三支 `*-impl.yml` 的 `bash "$MAP_SH"` 全部靠這一步才解得開；
  - `defaults.run.working-directory`（workflow 層與 job 層）與 step 層的
    `working-directory` 決定相對路徑的基準。**這一條不是可選的**：`ci.yml` 的 backend job
    有 `working-directory: backend`，它的 `python scripts/dump_openapi.py` 指的是
    `backend/scripts/dump_openapi.py`——不看 working-directory 就會對一個真實存在的檔案
    報「找不到」，而那種假紅燈會讓整道閘門在第一天就被關掉。

真的解不開的逐一具名在 `UNRESOLVABLE_INVOCATIONS`，每一項附「為什麼解不開」，清單大小由
`run-selftest-tests.py` 釘住。**交付時該清單為空**——真實 repo 的每一個呼叫目標都解得開。

掃描面有三區，fail-closed 只適用於其中一區（iteration 3 的 F1／F7）
----------------------------------------------------------------
iteration 2 的報告把三種來路平鋪成一張表，抬頭寫「執行可達閉包」，於是那句 fail-closed
看起來適用於全部 34 支。實際上：

  ① **shell 呼叫位置**（workflow／action 的 `run:`、某支 `.sh` 的命令位置）
     ——解不開即 `REACH-1` 紅。fail-closed 只在這一區。
  ② **Python 的 subprocess argv 位置**——best-effort。Python 的引數可能是
     `sys.executable`、`str(path)`、f-string，拿不到值是常態而不是缺口。
  ③ **同步機制自有目錄的全掃種子**——不經呼叫位置，未必會被執行；補的是「放進 action
     目錄卻沒人呼叫」那一類。

②區在 iteration 2 收的是**任何長得像路徑而且真的存在**的字串字面值，於是三份**資料**清
單（`validate_repo_contract.py` 的必要檔、`validate_env_contract.py` 的環境範本、
`tcms_validate.py` 的 spec 路徑）被當成三組呼叫，把 11 個從不執行的檔拉進掃描面——而它們
不在本單元的觸發 allowlist 內，改它們的 PR 不跑自我測試，紅燈會落在下一個改同步機制的
PR 上。iteration 3 把②區收窄成「只收 subprocess／os.exec 系列呼叫的字面引數」，並由
`check-paths-relations.py` 的 `COVERAGE-2` 每次執行機械比對「掃描面 ⊆ allowlist ∪
SCAN_EXEMPT」——沒有那道比對的話，下一次擴掃描面又會靜默打開同一個洞。

`ci.yml` 也在掃描面上（iteration 2 的 M-5，Major）
------------------------------------------------
`ci.yml` 現在承載同步判定（U-10a 的 gate/probe：判斷一顆 commit 是不是同步回寫），但它
既不在 R-1.2 原本的 workflow glob 內，`check-ci-yml.py` 對代理式承載也**零檢查**。reviewer
把 `is_sync="$(copilot -p ...)"` 注入 `ci.yml` 的 probe step，兩道守衛同時綠燈。

它已經在 U-9 的觸發 allowlist 內（`check-paths-relations.py` 的 COVERAGE-1），所以納入掃描
面不需要新規則、也不改變觸發條件。

**但 `uses:` 那一面不能照搬**（本檔對 brief 的一處刻意偏離，理由如下）：同步資產用的是
**允許清單**（見 USES-1），而 `ci.yml` 合法地使用 `docker/setup-buildx-action@v3` 與
`docker/build-push-action@v6`——照搬允許清單會讓真實 repo 立刻恆紅，而恆紅的閘門等於沒有
閘門。所以 `ci.yml` 走 `strict_uses=False`：`engine:` 鍵、`run:` 本體的 token 掃描、以及
`uses:` 的**已知代理式禁止清單**照樣適用，只有那份為同步資產量身訂做的允許清單不適用。
M-5 要攔的是「判定被搬進 agent step」，那三件事就攔得住。

執行面是禁止清單，`uses:` 面是允許清單——這個落差是刻意的（iteration 2 的 m-2）
--------------------------------------------------------------------------
USES-1 底下逐字論證了為什麼 `uses:` 必須用允許清單（禁止清單只擋得住它認得的名字）。
**執行面（`run:` 與腳本本體）用的卻是禁止清單**，這是一個要寫下來的不對稱：

  - 它防的是**無意的搬移**——把判定寫進 `map.sh`、把 helper 放進 `scripts/`、把 action
    改名搬走。這一類是真實會發生的，C-1 的 B1 就是照著既有形狀寫程式寫出來的。
  - 它**擋不住刻意的混淆**。`c=cop; d=ilot; "$c$d" -p …`、`eval "$(base64 -d <<<…)"`
    這一類拆字與間接執行，本檔看不出來。要擋它得對執行面也用允許清單（列舉「只准呼叫這
    幾個命令」），那個成本在一個有 7 支 workflow、5 支 shell、18 支 Python 的 repo 裡遠高
    於收益，而且每加一個命令就要改一次這裡。
  - 所以本檔的定位是**閘門，不是沙箱**。刻意規避需要有人寫下拆字的程式碼，那是 code
    review 看得見的東西；無意的搬移看不見，本檔補的是後者。

`run-selftest-tests.py` 有 `test_deliberate_obfuscation_is_out_of_scope` 把這個邊界釘成
可執行的斷言，而不是只寫在這段說明裡。

檢查對象是 `.yml` 原始檔，不是 `.lock.yml`（N:C-3）
--------------------------------------------------
`functional-design/business-rules.md:25`、`:29` 與 `business-logic-model.md:22`、`:83`
仍寫「解析編譯後的 `.lock.yml`」。**那是過期的敘述**，已由
`nfr-requirements/tech-stack-decisions.md:32-34` 於 2026-08-30T06:11:59Z 更正（reviewer
判 Critical，登錄為 `open-items.md` 的 **N:C-3**）：四支 workflow 已全數定案為**純
Actions**，`.lock.yml` 根本不存在，指向它會讓這個唯一的機械化閘門**恆綠**。

本檔依更正版實作，並把更正**釘住**：`aidlc-sync-*.lock.yml` 一旦出現即判紅（見 LOCK-1）。

**注意本檔與 `check-paths-relations.py` 檢的是兩組不同的檔案。** 那一支要看的是被排除的
四支 gh-aw workflow（`ui-regression` 等），GitHub 執行的是它們編譯後的 `.lock.yml`，所以
它必須讀 lock。兩者不矛盾——同步機制自己沒有 lock，被排除的那四支有。

為什麼是「解析 YAML 的值」而不是「搜尋整份檔案的文字」
--------------------------------------------------
本 repo 已經付過這個學費：`check-ci-yml.py` 的 MARKER-1 第一版用整段 `run:` 文字做子字串
搜尋，被 reviewer 用三種手法攻破（標記寫在註解裡、寫在 echo 訊息裡、寫在沒人用的變數
賦值裡）。**子字串出現不等於它被執行。**

本檔因此只掃**可執行面**：`uses:` 的值、`run:` 的值（先剝掉 shell 註解）、`with:` 底下的
多行字串（`actions/github-script` 的 `script:` 這類）、以及頂層與 job 層的 `engine:` 鍵。
`name:`／`description:`／YAML 註解一概不看——這幾支 workflow 的註解裡本來就大量提到
`gh-aw`、`copilot`、`.lock.yml`（它們正在解釋為什麼不用那些東西）。

腳本副檔名用**排除清單**（iteration 2 的 M-1，Major）
--------------------------------------------------
原本是允許清單 `(".sh", ".py")`。reviewer 實測 `.bash`（由 `map.sh` 以 `bash` 呼叫）與
無副檔名的 `decider` 都 rc=0；`.js`／`.mjs` 同樣落空，而 `actions/github-script` 是
Actions 的一級公民。改為排除已知的非執行副檔名（`.md`／`.json`／`.yml` 這些），其餘一律
當腳本掃——與 USES-1 對允許清單的論證同一個方向（那段逐字寫「禁止清單只擋得住它認得的
名字」，這裡剛好用反了）。

用法
----
    python3 .github/actions/aidlc-sync-selftest/check-agentic-steps.py
    python3 .github/actions/aidlc-sync-selftest/check-agentic-steps.py --repo-root <某棵樹>

`--repo-root` 存在的理由是**行為測試**：`run-selftest-tests.py` 用合成的暫存 repo 樹驅動
本檔並斷言 rc 與訊息。沒有它，這支檢查器只能對真實 repo 跑一次，「它在該紅的時候真的會
紅嗎」就沒有答案。

exit code（`reliability-requirements.md` 要求兩類在第一行即可分辨）
--------------------------------------------------------------
    0  全數通過
    1  **斷言失敗**——同步機制真的違規了。第一行為 `ASSERTION-FAILED:`。修 code，不得重跑
    2  **外部錯誤**——檔案不存在、YAML 解析失敗、相依缺席。第一行為 `EXTERNAL-ERROR:`。
       修環境或重跑

相依：PyYAML。與 `check-ci-yml.py`／`run-probe-tests.py`／`aidlc-sync-forward/run-live-tests.py`
同一個相依，不是本單元新增的。
"""

import argparse
import ast
import io
import json
import re
import sys
import tokenize
import warnings
from pathlib import Path

try:
    import yaml
except ImportError:  # 相依缺席要講清楚是缺什麼，不要丟 traceback
    sys.stderr.write(
        "EXTERNAL-ERROR: 找不到 PyYAML。這支腳本用它解析 workflow；請先 pip install pyyaml\n"
    )
    raise SystemExit(2)

# ==========================================================================
# 共用的失敗語意（`reliability-requirements.md`）
#
# 這兩個前綴與 Checker 是本單元三支腳本的**單一真實來源**：另外兩支以 importlib 從本檔
# 匯入，不各自再定義一份。理由是 `team.md ## Code Style` 的「單一真實來源」——三份逐字
# 相同的常數，遲早有一份會漂移，而漂移的後果正是這兩類紅燈變得分不出來。
# ==========================================================================
ASSERT_PREFIX = "ASSERTION-FAILED:"
EXTERNAL_PREFIX = "EXTERNAL-ERROR:"

EXIT_OK = 0
EXIT_ASSERTION = 1
EXIT_EXTERNAL = 2


class ExternalError(Exception):
    """環境／工具問題，不是同步機制違規。以 exit 2 表達。"""


class Checker:
    """收集檢查結果。

    每個失敗訊息都必須含**預期與實得**（`business-rules.md` R-1.1 逐字：「一個只印
    FAILED 的斷言，在三個 Bolt 之後沒有人能從 CI log 判斷是映射改錯了還是 fixture
    過期了」）。`check()` 的 fail_msg 參數因此不是可選的裝飾。
    """

    def __init__(self, title):
        self.title = title
        self.results = []

    def check(self, cid, ok, ok_msg, fail_msg):
        self.results.append((cid, bool(ok), ok_msg if ok else fail_msg))
        return bool(ok)

    def failed(self):
        return [r for r in self.results if not r[1]]

    def report(self):
        for cid, ok, msg in self.results:
            print("%s %-28s %s" % ("[通過]" if ok else "[失敗]", cid, msg))
        bad = self.failed()
        print("")
        print("%s：%d 項檢查，%d 失敗。" % (self.title, len(self.results), len(bad)))
        if not bad:
            return EXIT_OK
        sys.stderr.write(
            "%s %s 有 %d 項斷言失敗（共 %d 項）：%s\n"
            % (ASSERT_PREFIX, self.title, len(bad), len(self.results),
               "、".join(cid for cid, _, _ in bad))
        )
        return EXIT_ASSERTION


def run_checker(main_fn):
    """把 ExternalError 轉成 exit 2 並印出可分辨的第一行。三支腳本共用。"""
    try:
        return main_fn()
    except ExternalError as exc:
        sys.stderr.write("%s %s\n" % (EXTERNAL_PREFIX, exc))
        return EXIT_EXTERNAL


# ==========================================================================
# 被禁字樣：唯一正本是隔壁那份純資料檔（M-2）
# ==========================================================================
# 以前這三份清單就寫在本檔，於是本檔自己必然含被禁字樣，於是本檔必須被**整檔豁免**掃描，
# 於是「把 copilot 呼叫加進本檔」rc=0——reviewer 實測過。把資料搬出去之後，豁免的對象從
# 一支每個 PR 都在 CI 執行的 .py，縮成一份沒有任何可執行語意的 .json。
HERE = Path(__file__).resolve().parent
TOKENS_FILE = HERE / "agentic-tokens.json"


def _load_tokens():
    try:
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # fail-closed：讀不到就不是「沒有被禁字樣」，是這道檢查失去了定義。
        raise SystemExit(
            "%s 讀不到或不是合法 JSON：%s\n"
            "它是被禁字樣的唯一正本，缺了它這道檢查沒有定義，不得以空清單繼續。"
            % (TOKENS_FILE, exc)
        )
    try:
        run_tokens = tuple(data["agentic_run_tokens"])
        uses_tokens = tuple(data["known_agentic_uses"])
        lock = data["lock_token"]
        named = dict(data["named"])
    except (KeyError, TypeError) as exc:
        raise SystemExit("%s 缺少必要欄位：%s" % (TOKENS_FILE, exc))
    if not run_tokens or not uses_tokens or not lock or not named:
        raise SystemExit(
            "%s 的三份清單與具名表都不得為空——空清單會讓這道檢查恆綠。" % TOKENS_FILE
        )
    return run_tokens, uses_tokens, lock, named


# `run:`／`script:` 裡的代理式呼叫。剝掉 shell 註解之後才比對（見 strip_shell_comments）。
# 已知的代理式 `uses:` 承載。命中時給的是**更精確的訊息**，不是額外的防線——真正的防線是
# 下面的允許清單（不在清單內一律紅），這份只負責把「這是一個 agent」講出來。
# `.lock.yml` 是 gh-aw 的編譯產物，它出現在同步機制裡就代表承載形式漂移了（N:C-3 的反面）。
AGENTIC_TOKENS, KNOWN_AGENTIC_USES, LOCK_TOKEN, NAMED_TOKENS = _load_tokens()

# ==========================================================================
# 掃描面的唯一豁免 —— 一份純資料檔
# ==========================================================================
# iteration 1／2 的豁免是**整檔**豁免三支 `.py`，其中兩支每個 `pull_request` 都在 CI 執行
# PR head 的程式碼。現在只剩這一份 `.json`：它沒有任何可執行語意，被「搬判定進去」也不會
# 有人執行它。三支 `.py` 全部回到掃描面內——包含本檔自己。
SCAN_EXEMPT = frozenset({
    ".github/actions/aidlc-sync-selftest/agentic-tokens.json",
})

# ==========================================================================
# 本檔自己的設定
# ==========================================================================

# 四個**邏輯** workflow。ADR-A10 的兩檔拆分（薄外層 ＋ `-impl`）讓檔數不等於邏輯數：
# 實測 `ls .github/workflows/aidlc-sync-*.yml` 目前是 7 個檔，但邏輯名稱一直是四個。
# **檔案以 glob 列舉、邏輯名稱以本清單斷言**——只列舉不斷言的話，某支被刪掉時檢查會靜默
# 地少檢一支而且全綠。
REQUIRED_LOGICAL = (
    "aidlc-sync-forward",
    "aidlc-sync-reconcile",
    "aidlc-sync-reverse",
    "aidlc-sync-selftest",
)

# `uses:` 的**允許清單**。用允許清單而不是「代理式關鍵字禁止清單」的理由：禁止清單只擋得
# 住它認得的名字，而本檔要防的正是「有人引入了一個我沒想到的 agent action」。允許清單的
# 代價是引入任何新 action 都會紅一次、需要有人改這裡——那是刻意的，與 `check-ci-yml.py`
# 的 SEC-1c（禁止 `**`）同一種取捨：寧可讓人多看一眼，不要靜默放行。
#
# **只套用在同步資產上**（`strict_uses=True`）。`ci.yml` 走禁止清單，理由見模組說明。
USES_ALLOWLIST = (
    # GitHub 第一方 action。`actions/` 命名空間下沒有代理式引擎。
    re.compile(r"^actions/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*@[A-Za-z0-9._/-]+$"),
    # 本 repo 內的同步資產（薄外層對 `-impl` 的 workflow_call、composite action）。
    re.compile(r"^\./\.github/workflows/aidlc-sync-[A-Za-z0-9-]+\.yml$"),
    re.compile(r"^\./\.github/actions/aidlc-sync-[A-Za-z0-9-]+$"),
)

# workflow／action 以本地路徑參照的 composite action。用來確認掃描集合完整（LOCALREF-1）。
LOCAL_ACTION_REF = re.compile(r"^\./\.github/actions/(aidlc-sync-[A-Za-z0-9-]+)/?$")

# ---- M-1：腳本副檔名改為排除清單 -----------------------------------------
# 這裡列的是**已知不可執行**的副檔名。其餘一律當腳本掃——包含 `.bash`、`.js`、`.mjs`、
# 以及**完全沒有副檔名**的檔（reviewer 的 `decider`）。
NON_SCRIPT_SUFFIXES = frozenset({
    ".md", ".markdown", ".rst", ".txt", ".json", ".yml", ".yaml", ".toml",
    ".ini", ".cfg", ".conf", ".csv", ".tsv", ".xml", ".html", ".css",
    ".lock", ".pyc", ".pyo", ".pyd", ".so", ".dylib", ".dll", ".o", ".a",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".pdf",
    ".zip", ".gz", ".bz2", ".xz", ".tar", ".whl", ".woff", ".woff2", ".ttf",
})

# 這些目錄底下沒有人維護的程式碼，掃它們只會製造噪音（`__pycache__` 裡是 `.pyc`，
# 已被副檔名排除，但目錄整個跳過比較快也比較清楚）。
SKIP_DIR_NAMES = frozenset({"__pycache__", ".git", "node_modules", ".venv", "venv"})

# ==========================================================================
# 真的解不開的呼叫目標 —— 逐一具名，附「為什麼解不開」
# ==========================================================================
# 形狀比照舊的 VOCABULARY_OWNERS：**具名、可數、可審**，大小由
# `run-selftest-tests.py::test_the_unresolvable_invocation_list_is_pinned` 釘住。
#
# **交付時這份清單是空的。** 那不是預先假設，是實跑的結果：真實 repo 的每一個呼叫目標
# （含三支 `*-impl.yml` 的 `bash "$MAP_SH"` 這一類、五份 action.yml 的
# `${GITHUB_ACTION_PATH}/*.sh`、以及 `ci.yml` backend job 那個吃 working-directory 的
# `scripts/dump_openapi.py`）都解得開。清單留在這裡是因為「下一個解不開的呼叫」必須被迫
# 具名並附理由，而不是讓 fail-closed 逼著下一個人把整道檢查關掉。
#
# 每一項的形狀：(來源位置的子字串, 呼叫目標的原文, 為什麼解不開)
UNRESOLVABLE_INVOCATIONS = ()


def strip_shell_comments(text):
    """剝掉 bash 註解，保留字串內的 `#`。

    為什麼要這一步：這四支 workflow 的 `run:` 腳本裡有大量中文註解在解釋「為什麼不用
    gh-aw」「為什麼不引用 block.sh」。直接掃文字會把那些解釋判成違規——那不是嚴格，是
    壞掉。`check-ci-yml.py` 的 `gate_grep_patterns` 用 `shlex(comments=True)` 解同一個
    問題；本檔不能用 shlex，因為它對含正則的行（`sed -n 's/^ *X="\\(.*\\)"$/\\1/p'`）會
    拋 ValueError 而整行被跳過——被跳過的那一行正是最該看的那一行。

    這裡用逐字元的引號狀態機：只在**不在引號內、且前面是行首或空白**時把 `#` 之後的內容
    丟掉。這是 shell 對註解的實際規則。
    """
    out = []
    in_single = False
    in_double = False
    prev = "\n"
    i = 0
    while i < len(text):
        ch = text[i]
        if in_single:
            if ch == "'":
                in_single = False
            out.append(ch)
        elif in_double:
            if ch == "\\" and i + 1 < len(text):
                out.append(ch)
                i += 1
                out.append(text[i])
                i += 1
                prev = "x"
                continue
            if ch == '"':
                in_double = False
            out.append(ch)
        elif ch == "'":
            in_single = True
            out.append(ch)
        elif ch == '"':
            in_double = True
            out.append(ch)
        elif ch == "#" and (prev in ("\n", " ", "\t", ";", "(")):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue  # 不吃掉換行，prev 維持不變即可
        else:
            out.append(ch)
        prev = ch
        i += 1
    return "".join(out)


def _python_tokens(text):
    """tokenize 一段 Python，失敗時回 None（呼叫端 fail closed）。"""
    try:
        return [t for t in tokenize.generate_tokens(io.StringIO(text).readline)
                if t.type != tokenize.COMMENT]
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return None


def strip_python_comments_and_docstrings(text):
    """剝掉 Python 的註解與**敘述性字串**（docstring），保留其餘字串值。

    為什麼不能沿用 `strip_shell_comments`：它的引號狀態機會把 `\"\"\"…\"\"\"` 當成「空字串、
    空字串、然後一段裸文字」，docstring 的內容原樣留下。本 repo 的 `run-reverse-tests.py`
    與 `run-reconcile-tests.py` 各有一句 docstring 在解釋「三支既有排程皆為 gh-aw」——把
    那判成違規不是嚴格，是壞掉。

    為什麼**不能**連字串值一起剝：真正的繞過長成 `subprocess.run([\"copilot\", ...])`，
    那正是一個字串值。剝掉它等於把要抓的東西抓掉。

    判定 docstring 的方式是「一個自成陳述的字串」：前一個有意義的 token 是行首類
    （NEWLINE／NL／INDENT／DEDENT／ENCODING），下一個是換行類。這正是 Python 對
    docstring 的實際形狀。

    tokenize 失敗（語法錯誤、非 UTF-8）時**回傳原文**——fail closed：寧可假紅燈讓人看一
    眼，不要因為剝不掉而漏放行。
    """
    toks = _python_tokens(text)
    if toks is None:
        return text
    starters = {tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT,
                tokenize.ENCODING}
    enders = {tokenize.NEWLINE, tokenize.NL}
    keep = []
    for idx, tok in enumerate(toks):
        if tok.type == tokenize.STRING:
            prev = toks[idx - 1].type if idx else tokenize.ENCODING
            nxt = toks[idx + 1].type if idx + 1 < len(toks) else tokenize.NEWLINE
            if prev in starters and nxt in enders:
                continue
        keep.append(tok.string)
    # 以換行相接而不是空白：AGENTIC_TOKENS 有含空白的項目（`gh aw `），用空白相接會憑空
    # 製造出跨 token 的假命中。
    return "\n".join(keep)


# ==========================================================================
# Python 的呼叫位置 —— 只有這幾個函式的 argv 才是「它真的執行了什麼」（F1）
# ==========================================================================
# iteration 2 收的是**任何長得像路徑而且真的存在**的字串字面值。那一版把 11 個檔拉進掃描
# 面，其中沒有一個會被執行：`validate_repo_contract.py` 的必要檔清單、
# `validate_env_contract.py` 的範本清單、`tcms_validate.py` 的 spec 路徑——三份**資料**清
# 單，被當成了三組呼叫。後果不是漏檢而是**誤報落在無關的 PR 上**：那些路徑（`frontend/`、
# `deploy/`、`.claude/`）不在本單元的觸發 allowlist 內，所以改它們的 PR 不跑自我測試，
# 紅燈會落在下一個改同步機制的 PR 身上。`business-rules.md` R-4 逐字：「一個會誤報的閘
# 門，比沒有閘門更快失去作用。」
#
# 兩條路都試過，選了收窄而不是把那些路徑補進 allowlist：把 `frontend/`、`deploy/`、
# `.claude/` 拉進本單元的觸發面會讓自我測試在無關的 PR 上跑——那是同一個誤報換一個方向。
# 收窄之後真正被執行的三支（`scripts/validate_repo_contract.py`、
# `scripts/validate_env_contract.py`、`backend/scripts/dump_openapi.py`，都由 `ci.yml` 的
# `run:` 直接呼叫）仍在掃描面上，並已補進 allowlist——它們是**真的**會被執行的東西，
# 改它們的 PR 本來就該跑一次 R-1.2。掃描面 ⊆ allowlist 這件事由
# `check-paths-relations.py` 的 COVERAGE-2 每次執行機械比對。
SUBPROCESS_CALLEES = frozenset({
    "run", "call", "check_call", "check_output", "Popen", "getoutput", "getstatusoutput",
})
OS_EXEC_CALLEES = frozenset({
    "system", "popen", "execl", "execle", "execlp", "execv", "execve", "execvp",
    "execvpe", "spawnl", "spawnle", "spawnlp", "spawnv", "spawnve", "spawnvp",
})


def _is_exec_call(func):
    """這個 Call 的 func 是不是一個「執行別的程式」的呼叫位置。

    收 `subprocess.X(...)`／`os.X(...)`，以及 `from subprocess import run` 之後的裸
    `run(...)`。裸名字會多收一些同名的自訂函式——那是刻意的：本層 best-effort，
    **寧可多收也不要漏掉一個真的呼叫位置**（多收的代價只是多掃一支檔）。
    """
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name) and base.id == "subprocess":
            return func.attr in SUBPROCESS_CALLEES
        if isinstance(base, ast.Name) and base.id == "os":
            return func.attr in OS_EXEC_CALLEES
        return False
    if isinstance(func, ast.Name):
        return func.id in SUBPROCESS_CALLEES or func.id in OS_EXEC_CALLEES
    return False


def python_call_targets(text):
    """一段 Python 的**呼叫位置**上出現的字面目標。

    回傳的是候選字串（尚未解析成路徑）。三種形狀：

      subprocess.run(["bash", "x.sh"])       → argv list 的每一個字面元素
      subprocess.run("bash x.sh", shell=True) → 當成一行 shell，交給 invocation_targets
      os.system("bash x.sh")                  → 同上

    非字面的元素（`sys.executable`、`str(path)`、f-string）拿不到值，略過——這是本層
    **不 fail-closed** 的原因：Python 這一側解不開是常態而不是缺口，而 Python 檔本身早已
    在掃描面上（token 掃描直接看它的 `subprocess.run(["<agent>", …])`），這一層要補的只
    是「它又轉呼了誰」。
    """
    try:
        with warnings.catch_warnings():
            # 被掃的檔案裡有含 `\`` 之類的非 raw 字串，`ast.parse` 會為它發
            # SyntaxWarning。那是**被掃檔案**的風格問題，不是本檢查的發現——讓它印在
            # R-1.2 的報告最上面只會讓人以為閘門壞了。作用域只包住這一次 parse。
            warnings.simplefilter("ignore")
            tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None  # 解不開的 .py：呼叫方負責記錄，不假裝掃過了
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_exec_call(node.func):
            continue
        args = list(node.args)
        for kw in node.keywords:
            if kw.arg in ("args", "cmd", "popenargs"):
                args.insert(0, kw.value)
        if not args:
            continue
        first = args[0]
        if isinstance(first, (ast.List, ast.Tuple)):
            for element in first.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    out.append(element.value)
        elif isinstance(first, ast.Constant) and isinstance(first.value, str):
            # `shell=True` 或 `os.system` 的形狀：整串是一行 shell。
            out.extend(raw for raw, _ in invocation_targets(first.value))
            out.append(first.value)
    return out


def script_body(path):
    """一支腳本裡**會被執行**的部分（剝掉註解／敘述）。"""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ExternalError("讀不到 %s：%s" % (path, exc))
    if path.suffix == ".py":
        return strip_python_comments_and_docstrings(text)
    return strip_shell_comments(text)


def load_yaml(path):
    """讀一份 workflow。YAML 1.1 把裸 `on` 當布林，所以觸發區塊的鍵是 True 不是 'on'。"""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ExternalError("%s 不是合法的 YAML，無法檢查：%s" % (path, exc))
    if not isinstance(doc, dict):
        raise ExternalError("%s 的頂層不是一個 mapping，無法檢查。" % path)
    return doc


def logical_name(path):
    """由檔名推導邏輯 workflow 名稱。`-impl` 是 ADR-A10 的承載拆分，不是第五個邏輯。"""
    stem = path.name[: -len(".yml")]
    return stem[: -len("-impl")] if stem.endswith("-impl") else stem


# ==========================================================================
# 可達閉包：把「誰呼叫誰」解出來
# ==========================================================================

# 一個 word：帶引號的整段，或到下一個空白為止。
_WORD = re.compile(r'"[^"]*"|\'[^\']*\'|\S+')

# 行首的環境變數前綴，例如 `GITHUB_OUTPUT="$out" bash "$RECORD_SH"`。
_LEADING_ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|\'[^\']*\'|\S*)$')

# 腳本內的字面賦值，供變數展開使用。**逐行**取到行尾而不是切到第一個 `;&|`：值裡面本來
# 就可能有那些字元（`SCRIPT_DIR="$(cd … && pwd)"`），切一半會得到一個看起來像路徑、實際
# 是碎片的值——那正是 iteration 2 修 C-1 時第一版踩到的坑（board.sh 的 `$BLOCK_SH` 被展
# 開成 `$(cd /../aidlc-sync-block/block.sh`）。
_ASSIGN = re.compile(
    r'^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$',
    re.M,
)

# `VAR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`——「這支腳本自己的目錄」的標準寫法。
# 認得它才解得開 `board.sh` 的 `bash "$BLOCK_SH"`（本 repo 唯一的 action → action 呼叫）。
_SCRIPT_DIR_IDIOM = re.compile(r'^"?\$\(\s*cd\s+.*&&\s*pwd\s*\)"?$')

# 用副檔名或 shebang 確認「這真的是 shell」。**fail-closed 只對 shell 生效**：`bash X` 是
# 一個明確的呼叫位置，解不開就代表有東西沒被看到；而拿 shell 的切段規則去解 TypeScript 或
# JavaScript 只會把它們的正則與樣板字串判成「解不開的呼叫」——那是假紅燈，不是嚴格。
_SHELL_SUFFIXES = frozenset({".sh", ".bash", ".zsh", ".ksh", ".dash"})
_SHEBANG_SHELL = re.compile(r"^#!.*\b(?:ba|z|k|da)?sh\b")

# GitHub Actions 的表示式 `${{ github.action_path }}`。**與 shell 變數是兩套語法**，兩套
# 都要展開：本 repo 的五份 action.yml 用的是 shell 形式 `${GITHUB_ACTION_PATH}`，而
# `${{ github.action_path }}` 同樣合法且常見（合成 fixture 用的就是它）。只認一種的話，
# 另一種會變成一條假的「解不開的呼叫」。
_ACTIONS_EXPR = re.compile(r"\$\{\{\s*([A-Za-z_][A-Za-z0-9_.\-]*)\s*\}\}")

# `${VAR}`／`${VAR:-default}`／`$VAR`
_VAR = re.compile(
    r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::[-=?+][^}]*)?\}|\$([A-Za-z_][A-Za-z0-9_]*)'
)

# 展開之後還留著這些，就代表解不開。
_STILL_DYNAMIC = re.compile(r"[$`*?\[]")

# shell 的關鍵字與常見前綴命令：它們後面才是真正的命令。
_PREFIX_WORDS = frozenset({
    "if", "then", "else", "elif", "fi", "do", "done", "while", "until", "for",
    "case", "esac", "select", "function", "!", "time", "exec", "sudo",
    "command", "nohup", "builtin", "env", "local", "export", "then;",
})

_INTERPRETERS = frozenset({
    "python", "python2", "python3", "bash", "sh", "zsh", "ksh", "dash",
})

# `python -c`／`python -m` 之後沒有檔案目標；`-` 是 stdin。
_NO_FILE_FLAGS = frozenset({"-c", "-m", "-"})

# 「乾淨的變數參照開頭」：`$VAR`、`${VAR}`、`${VAR}/x`。用來把 `$/\1/p` 這類正則碎片擋在
# 「直接執行」的判定之外。
_VAR_HEAD = re.compile(r'^\$\{?[A-Za-z_][A-Za-z0-9_]*\}?(?:[/.][^\s]*)?$')

# 同一段腳本裡自己定義的 shell 函式。它們常常是**透明的包裝**——本 repo 的
# `run_pure() { env -u GH_TOKEN … "$@"; }` 就是，於是真正的呼叫長成
# `run_pure … bash "$MAP_SH"`。不認得它，`map.sh` 這一支就會整支從閉包裡消失
# （實測：14 個 `bash "$X"` 找到 13 個，唯一漏掉的正是包在 run_pure 裡的那個）。
# 只認**本體內有定義**的名字，不是任意 unknown 命令——後者會把 `grep -w bash x` 這種
# 誤判成呼叫。
_FUNC_DEF = re.compile(r'^[ \t]*(?:function[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(\)', re.M)


def is_shell_text(path, text):
    """這份檔案能不能用 shell 的規則解析（決定 fail-closed 適不適用）。"""
    if path.suffix.lower() in _SHELL_SUFFIXES:
        return True
    if path.suffix:
        return False
    return bool(_SHEBANG_SHELL.match(text.split("\n", 1)[0]))


def shell_segments(body):
    """把一段 shell 切成命令段。**引號要算數**，`$(…)` 要切開。

    為什麼不是一條 `re.split`：第一版是，然後 `sed -n 's/^SYNC_MARKER="\\(.*\\)"$/\\1/p'`
    的那段正則被當成命令切碎，碎片 `"$/\\1/p' "` 長得像一個「以變數開頭、含斜線」的命令，
    於是三支 `*-impl.yml` 各報一條假的「解不開」。單引號內什麼都不解析（bash 的實際規則），
    這一類就整批消失。

    反過來，`$(` **即使在雙引號內也要切**——`parse_out="$(… bash "$BLOCK_SH" parse)"` 是
    本 repo 真正呼叫 `block.sh` 的那一行，不切開就會漏掉它。
    """
    segments, cur = [], []
    i, n = 0, len(body)
    quote = None          # None／"'"／'"'
    substack = []         # 進入 `$(` 時保存外層的引號狀態
    while i < n:
        ch = body[i]
        if quote == "'":
            # 單引號內 bash 什麼都不解析——連反斜線都不是跳脫。
            if ch == "'":
                quote = None
            cur.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            if body[i + 1] == "\n":
                # 續行：bash 把 `\` ＋ 換行整個吃掉。**不折疊的後果**是續行處留下一個
                # 裸 `\` word，而本 repo 的呼叫幾乎全長成
                # `AIDLC_OPERATION=… \<換行>  GITHUB_OUTPUT="$out" bash "$RECORD_SH"`——
                # 那個 `\` 會卡在命令名的位置，於是 14 個真正的 `bash "$X"` 一個都認不出來。
                cur.append(" ")
                i += 2
                continue
            cur.append(ch)
            i += 1
            cur.append(body[i])
            i += 1
            continue
        if body.startswith("$(", i):
            # 命令替換即使在雙引號內也是新的命令脈絡。
            substack.append(quote)
            quote = None
            segments.append("".join(cur))
            cur = []
            i += 2
            continue
        if ch == ")" and substack:
            quote = substack.pop()
            segments.append("".join(cur))
            cur = []
            i += 1
            continue
        if quote == '"':
            # 雙引號內只有 `"` 與 `$(` 有意義；`'` 在這裡只是一個字元。**漏掉這一條**
            # 會讓 `echo "it's fine"` 的那個撇號開啟一段假的單引號，把整段腳本剩下的
            # 部分全部吞進同一個 segment——實測後果是三支 `*-impl.yml` 的
            # `bash "$MAP_SH"` 一個都找不到，而檢查看起來還是綠的。
            if ch == '"':
                quote = None
            cur.append(ch)
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            cur.append(ch)
            i += 1
            continue
        if body.startswith("&&", i) or body.startswith("||", i):
            segments.append("".join(cur))
            cur = []
            i += 2
            continue
        if ch in ";\n|&`(){}":
            segments.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    segments.append("".join(cur))
    return [s.strip() for s in segments if s.strip()]


def collect_assignments(body, script_dir=None):
    """一段腳本裡的字面賦值。後出現的覆蓋先出現的（與 shell 的實際語意一致）。"""
    env = {}
    for name, raw in _ASSIGN.findall(body):
        raw = raw.strip()
        if script_dir is not None and _SCRIPT_DIR_IDIOM.match(raw):
            env[name] = str(script_dir)
            continue
        env[name] = strip_quotes(raw)
    return env


def strip_quotes(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def expand_vars(value, env, rounds=8):
    """展開 Actions 表示式與 shell 變數；不認得的原樣留著（於是解不開）。"""
    for _ in range(rounds):
        new = _ACTIONS_EXPR.sub(
            lambda m: env.get(m.group(1).strip().lower(), m.group(0)), value
        )
        new = _VAR.sub(
            lambda m: env.get(m.group(1) or m.group(2), m.group(0)), new
        )
        if new == value:
            break
        value = new
    return value


def invocation_targets(body):
    """一段 **shell** 腳本裡被呼叫的檔案目標（原文，未展開）。

    做法是切成命令段之後看每一段的第一個 word，而不是拿正則在整段文字上撈——後者會把
    `for f in "$MAP_SH"` 的迴圈變數、`sed -n 's/…/p' "$RECORD_SH"` 的資料引數都當成呼叫，
    製造一堆假的「解不開」。
    """
    return _iter_invocations(body)


def _iter_invocations(body):
    """實作。回傳 `(目標原文, proven)`。

    `proven` 區分兩種確定性，而 fail-closed **只對 proven 生效**：

      True   語法本身就證明有一個檔案被執行：`bash X`、`python3 X`、`source X`、`./X`。
             解不開就代表可達閉包真的斷了一段，必須判紅。
      False  命令位置是一個變數（`"$MAP_SH"` 直接執行）。這在 shell 裡多半**不是**在跑
             腳本——`eval "cur=\\"\\${$__name}\\""`、`[ "$x" = y ]` 被跳脫字元切碎之後，
             首字都會長成一個變數。實測本 repo 有 10 條這種形狀，全部不是呼叫。對它們
             判紅等於製造假紅燈，而假紅燈會讓整道閘門在第一天就被關掉；所以這一支只在
             **解得開而且指到 repo 內既存檔案**時把目標收進閉包，解不開就略過。

    這條界線的代價要講清楚：`"$SOME_SCRIPT"` 直接執行且變數值算不出來時，本檔看不到它。
    那是本檔身為「閘門而非沙箱」的一部分（見模組說明的 m-2 段），不是漏掉的 bug。
    """
    out = []
    local_funcs = set(_FUNC_DEF.findall(body))
    transparent = _PREFIX_WORDS | local_funcs
    for segment in shell_segments(body):
        words = _WORD.findall(segment)
        # 丟掉前置的關鍵字、環境變數前綴、以及本體內自己定義的包裝函式
        stripped_func = False
        while words and (words[0] in transparent or _LEADING_ASSIGN.match(words[0])):
            if words[0] in local_funcs:
                stripped_func = True
            words.pop(0)
        if not words:
            continue
        head = strip_quotes(words[0])
        rest = words[1:]
        base = head.rsplit("/", 1)[-1]
        if base in _INTERPRETERS:
            target = None
            for word in rest:
                # 遇到重導向就停：`python3 <<'PY'` 的下一個 word 不是檔案。
                if word[0] in "<>" or re.match(r"^\d+[<>]", word):
                    break
                if word in _NO_FILE_FLAGS:
                    target = None
                    break
                if word.startswith("-"):
                    continue
                target = word
                break
            if target:
                out.append((target, True))
        elif head in (".", "source") and not stripped_func:
            # 剝掉包裝函式之後**不再**認 `.`／`source`／`./x`：那時候剩下的是該函式的
            # 引數，不是命令位置。本 repo 的實例是
            # `base="$(blob_or_empty_object . "HEAD:${rp}")"`——那個 `.` 是傳給函式的
            # 目錄引數，被當成 source 會讓 `"HEAD:${rp}"` 變成一條假的「解不開的呼叫」。
            # 包裝函式後面唯一還算數的是直譯器形狀（`run_pure … bash "$MAP_SH"`）。
            if rest:
                out.append((rest[0], True))
        elif head.startswith("./") and not stripped_func:
            out.append((words[0], True))
        elif _VAR_HEAD.match(head):
            # 變數開頭要求整個 head 是一個**乾淨的變數參照**（可再接路徑），否則正則
            # 碎片也會被當成命令——第一版就是這樣多報了五條假的「解不開」。
            # proven=False 的理由見本函式的 docstring。
            out.append((words[0], False))
    return out


def is_scannable_file(path):
    """這個檔案該不該進 token 掃描面（M-1：排除清單，不是允許清單）。"""
    if any(part in SKIP_DIR_NAMES for part in path.parts):
        return False
    return path.suffix.lower() not in NON_SCRIPT_SUFFIXES


class Closure:
    """從種子出發把可執行面展開到不動點，逐一判定。"""

    def __init__(self, repo_root, checker):
        self.root = repo_root
        self.c = checker
        self.actions_root = repo_root / ".github" / "actions"
        self.scanned_workflows = []
        self.scanned_actions = []
        # [(rel, 為什麼在掃描面上, origin)]。`origin` 是 iteration 3 的 F7：報告原本把
        # 三種來路混成一張表，於是「fail-closed」這個論證看起來適用於全部 34 支，而它只
        # 適用於 shell 呼叫位置那一區。三個值：
        #   "shell"  ← workflow／action 的 `run:` 或某支 .sh 的呼叫位置（解不開即 REACH-1）
        #   "python" ← 某支 .py 的 subprocess argv 位置（best-effort，解不開不判紅）
        #   "dir"    ← 同步機制自有目錄的全掃種子（不經呼叫位置，未必會被執行）
        self.scanned_scripts = []
        self.unresolved = []               # [(where, raw, reason)]
        self.unreadable = []
        self.unparsed = []                 # 解不開的 .py（rel）
        self._seen_scripts = set()
        self._seen_actions = set()
        self._pending_actions = []         # [(name, where)]
        self._pending_scripts = []         # [(path, where)]

    # ---- 種子 ------------------------------------------------------------
    def seed_workflow(self, path, strict_uses):
        doc = load_yaml(path)
        self.scanned_workflows.append(path.name)
        wf_wd = _default_wd(doc)
        for kind, loc, value, wd in workflow_surfaces(doc, wf_wd):
            where = "%s：%s" % (path.name, loc)
            self._judge_and_expand(where, kind, value, wd, strict_uses,
                                   action_dir=None)

    # ---- 展開 ------------------------------------------------------------
    def run(self):
        # 先把 workflow 參照到的 action 走完，再走腳本；兩者都可能再帶出新的東西，
        # 所以是一個交錯的不動點迴圈而不是兩個獨立的 for。
        while self._pending_actions or self._pending_scripts:
            while self._pending_actions:
                name, where = self._pending_actions.pop(0)
                self._process_action(name, where)
            while self._pending_scripts:
                path, where, origin = self._pending_scripts.pop(0)
                self._process_script(path, where, origin)

    def note_action(self, name, where):
        if name in self._seen_actions:
            return
        self._seen_actions.add(name)
        self._pending_actions.append((name, where))

    def note_script(self, path, where, origin="shell"):
        rel = path.relative_to(self.root).as_posix()
        if rel in self._seen_scripts:
            return
        self._seen_scripts.add(rel)
        self._pending_scripts.append((path, where, origin))

    # ---- 單一可執行面的判定 ＋ 展開 --------------------------------------
    def _judge_and_expand(self, where, kind, value, wd, strict_uses, action_dir):
        if kind == "uses":
            m = LOCAL_ACTION_REF.match(value)
            if m:
                # m-1：`uses:` 不只出現在 workflow，composite action 也能參照另一個
                # action。原本只在 workflow 那一層回填，於是模組說明宣稱的「搬走／改名
                # 不可能靜默少掃一份」在 action → action 這條邊上不成立。
                self.note_action(m.group(1), where)
            judge_surface(self.c, where, kind, value, strict_uses)
            return

        judge_surface(self.c, where, kind, value, strict_uses)

        if kind != "run":
            # `with:` 底下的字串（github-script 的 `script:` 是 JS）不是 shell，
            # 拿 shell 的切段規則去解只會製造假的「解不開」。token 掃描仍然適用。
            return

        body = strip_shell_comments(value)
        env = _actions_builtin_env(self.root, action_dir)
        env.update(collect_assignments(body))
        bases = _bases(self.root, wd, action_dir)
        for raw, proven in invocation_targets(body):
            self._resolve(raw, bases, env, where, fail_closed=proven)

    def _resolve(self, raw, bases, env, where, fail_closed=True):
        path, reason = resolve_invocation(raw, bases, env, self.root)
        if path is not None:
            self.note_script(path, where)
            return
        if reason is None:
            return  # 不是一個檔案目標（旗標之類）
        if not fail_closed:
            return  # 非 shell 的本體：best-effort，理由見 _walk_python／_walk_other
        if any(w in where and raw == r for w, r, _ in UNRESOLVABLE_INVOCATIONS):
            return
        self.unresolved.append((where, raw, reason))

    # ---- composite action ------------------------------------------------
    def _process_action(self, name, where):
        base = self.actions_root / name
        if not base.is_dir():
            self.c.check(
                "LOCALREF-1:" + name, False, "",
                "%s 被 `uses: ./.github/actions/%s` 參照（來源：%s），但 %s 不存在。"
                "**參照得到卻掃不到的可執行面，等於沒有被檢查過**。\n  預期：目錄存在"
                "\n  實得：不存在" % (name, name, where, base),
            )
            return
        action_yml = base / "action.yml"
        if action_yml.is_file():
            self.scanned_actions.append(name)
            doc = load_yaml(action_yml)
            where_file = "%s/action.yml" % name
            using = str((doc.get("runs") or {}).get("using", "")) \
                if isinstance(doc.get("runs"), dict) else ""
            self.c.check(
                "USING-1:" + where_file, using == "composite",
                "%s 是 composite action" % where_file,
                "%s 的 `runs.using` 是 %r 而不是 composite。node／docker action 的執行面是"
                "一個本檢查看不進去的映像或 bundle——那是一次要有人看過的承載形式變更。\n"
                "  預期：composite\n  實得：%r" % (where_file, using, using),
            )
            for kind, loc, value, wd in action_surfaces(doc):
                self._judge_and_expand("%s：%s" % (where_file, loc), kind, value,
                                       wd, True, action_dir=base)
        # 目錄內的檔案照樣全掃（M-1：排除清單）。可達閉包負責把**目錄外**的東西拉進來，
        # 這一層負責讓「放進 action 目錄但沒人呼叫」的東西也逃不掉——兩者互補，不是重複。
        for script in sorted(p for p in base.rglob("*") if p.is_file()):
            if is_scannable_file(script):
                self.note_script(script, "%s 目錄內" % name, origin="dir")

    # ---- 腳本 ------------------------------------------------------------
    def _process_script(self, path, where, origin="shell"):
        rel = path.relative_to(self.root).as_posix()
        if rel in SCAN_EXEMPT:
            return
        self.scanned_scripts.append((rel, where, origin))
        try:
            raw_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # 讀不到內容的檔案（二進位、壞編碼）不是違規，但也不能假裝掃過了。
            self.unreadable.append(rel)
            return
        body = script_body(path)
        hits = [t for t in AGENTIC_TOKENS if t in body.lower()]
        if hits:
            self.c.check(
                "SCRIPT-1:" + rel, False, "",
                "%s（已剝除註解與敘述性字串）出現代理式呼叫字樣 %s。它在掃描面上的理由："
                "%s。\n  預期：不含 %s\n  實得：命中 %s"
                % (rel, hits, where, list(AGENTIC_TOKENS), hits),
            )
        if path.suffix == ".py":
            self._walk_python(path, raw_text, rel)
        else:
            self._walk_shell(path, body, rel, is_shell_text(path, raw_text))

    def _walk_shell(self, path, body, rel, fail_closed):
        env = _actions_builtin_env(self.root, path.parent)
        env.update(collect_assignments(body, script_dir=path.parent))
        # 一支 `.sh` 的 cwd 由呼叫端決定，所以 repo 根與腳本自己的目錄都算候選基準。
        bases = [self.root, path.parent]
        for raw, proven in invocation_targets(body):
            self._resolve(raw, bases, env, rel,
                          fail_closed=fail_closed and proven)

    def _walk_python(self, path, raw_text, rel):
        """Python 檔的展開是 **best-effort，不 fail-closed**，且只看**呼叫位置**。

        理由：shell 的 `bash X` 是一個明確的呼叫位置，解不開就代表有東西沒被檢查到；而
        Python 的引數可能是 `sys.executable`、`str(path)`、f-string，拿不到值是常態。
        對每一個解不開的引數判紅會讓這道檢查對任何用 subprocess 的程式碼恆紅。

        **「呼叫位置」是 iteration 3 的 F1 收窄的那一刀**：iteration 2 收的是任何長得像
        路徑而且真的存在的字串字面值，於是三份**資料**清單（必要檔、環境範本、spec 路徑）
        被當成三組呼叫，把 11 個從不執行的檔拉進掃描面——而它們不在觸發 allowlist 內。
        詳見 `python_call_targets` 上方的說明。

        這不是一個洞：Python 檔本身已經在掃描面上（token 掃描直接看它的
        `subprocess.run([\"<agent>\", …])`），這一層要補的只是「它又轉呼了誰」。
        """
        candidates = python_call_targets(raw_text)
        if candidates is None:
            # 解不開的 `.py`。**不是違規，但也不能假裝掃過了**——它的 token 掃描仍然做過
            # （SCRIPT-1 在上面已經跑完），只有「它又轉呼了誰」這一層拿不到。
            self.unparsed.append(rel)
            return
        for cand in candidates:
            cand = strip_quotes(cand)
            # 呼叫位置上的字面值仍然什麼都可能是（旗標、訊息、整段 YAML）。這裡只要
            # 「長得像一條路徑」的，其餘一律略過——寧可少收也不要讓 `Path.resolve()`
            # 對一段測試資料拋例外而中止整道檢查。
            if (not cand or len(cand) > 512 or "/" not in cand
                    or _STILL_DYNAMIC.search(cand)
                    or any(ch in cand for ch in "\x00\n\r\t")):
                continue
            try:
                target = (self.root / cand).resolve()
            except (OSError, ValueError):
                continue
            if (target.is_file() and _within(target, self.root)
                    and is_scannable_file(target)):
                self.note_script(target, "%s 的 subprocess 呼叫位置" % rel, origin="python")

    # ---- 報告 ------------------------------------------------------------
    def report(self):
        for where, raw, reason in self.unresolved:
            self.c.check(
                "REACH-1:%s" % where, False, "",
                "%s 呼叫了 %r，但**解析不出它指向哪個檔案**（%s）。可達閉包因此在這裡斷掉"
                "——斷掉的那一段底下有什麼，這道檢查看不到。\n"
                "  預期：能解析成 repo 內的既存檔案，或列進 UNRESOLVABLE_INVOCATIONS "
                "並寫明為什麼解不開\n  實得：解不開" % (where, raw, reason),
            )

        print("掃描面（種子＝四支同步 workflow ＋ 五份 composite action ＋ ci.yml）")
        print("  workflow 原始檔 %d 份：%s"
              % (len(self.scanned_workflows), "、".join(self.scanned_workflows)))
        print("  composite action.yml %d 份：%s"
              % (len(self.scanned_actions), "、".join(self.scanned_actions) or "無"))
        # ---- F7（iteration 3）：三種來路分區印，不混成一張表 ----------------
        #
        # 抬頭原本寫「執行可達閉包」而底下一路平鋪 34 支，於是 fail-closed 的論證看起來
        # 適用於全部 34 支。它只適用於 ① 區：② 區的解不開不判紅（Python 的引數拿不到值
        # 是常態），③ 區根本不經呼叫位置——它們在掃描面上的理由是「躺在同步機制自己的
        # 目錄裡」，那是刻意的補網（放進去卻沒人呼叫的東西也要掃到），不是可達性推導。
        # 讀 CI log 的人應該一眼看得出自己在看哪一種。
        zones = (
            ("shell", "① 執行可達 · shell 呼叫位置",
             "解析自 workflow／action 的 `run:` 或某支 .sh；解不開即 REACH-1 紅（fail-closed）"),
            ("python", "② 執行可達 · Python subprocess argv 位置",
             "解析自 subprocess／os.exec 系列呼叫的字面引數；解不開不判紅（best-effort）"),
            ("dir", "③ 同步機制自有目錄全掃",
             "不經呼叫位置，未必會被執行；補的是「放進 action 目錄但沒人呼叫」"),
        )
        print("  腳本 %d 支，分三區：" % len(self.scanned_scripts))
        for key, title, note in zones:
            rows = sorted((rel, where) for rel, where, origin in self.scanned_scripts
                          if origin == key)
            print("    %s（%d 支）—— %s" % (title, len(rows), note))
            for rel, where in rows:
                print("      %-60s ← %s" % (rel, where))
            if not rows:
                print("      （無）")
        print("  解不開的呼叫目標 %d 條（具名豁免 %d 條）"
              % (len(self.unresolved), len(UNRESOLVABLE_INVOCATIONS)))
        if self.unparsed:
            # 解不開的 `.py` 不是違規（它的 token 掃描已經做過），但也不能不說——說不出
            # 「它又轉呼了誰」的檔案，可達閉包在它底下就是斷的。
            print("  解不開語法的 .py %d 支（token 掃描已做，轉呼那一層拿不到）：%s"
                  % (len(self.unparsed), "、".join(sorted(self.unparsed))))
        if self.unreadable:
            print("  讀不到內容的檔 %d 支：%s"
                  % (len(self.unreadable), "、".join(sorted(self.unreadable))))
        if SCAN_EXEMPT:
            print("  掃描面豁免（純資料檔）：%s" % "、".join(sorted(SCAN_EXEMPT)))

    # ---- 掃描面（給 COVERAGE-2 用，不做任何判定）--------------------------
    def surface_rel_paths(self):
        """掃描面的全部成員，以 repo 相對路徑表示。

        `check-paths-relations.py` 的 COVERAGE-2 拿它比對觸發 allowlist。回傳的是
        workflow ∪ composite action.yml ∪ 腳本——三者都是「改了它就該重跑一次 R-1.2」
        的東西，所以三者都必須落在 allowlist 內。
        """
        out = ["%s/%s" % (".github/workflows", name) for name in self.scanned_workflows]
        out += ["%s/%s/action.yml" % (".github/actions", name)
                for name in self.scanned_actions]
        out += [rel for rel, _where, _origin in self.scanned_scripts]
        return sorted(set(out))


def _within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _actions_builtin_env(repo_root, action_dir):
    """Actions 的內建變數。解得開的先解開，剩下的才叫解不開。"""
    env = {
        # shell 形式
        "GITHUB_WORKSPACE": str(repo_root),
        "PWD": str(repo_root),
        # Actions 表示式形式（鍵一律小寫，比對前先 lower）
        "github.workspace": str(repo_root),
    }
    if action_dir is not None:
        env["GITHUB_ACTION_PATH"] = str(action_dir)
        env["github.action_path"] = str(action_dir)
    return env


def _bases(repo_root, wd, action_dir):
    bases = []
    if wd:
        bases.append(repo_root / wd)
    bases.append(repo_root)
    if action_dir is not None:
        bases.append(action_dir)
    return bases


def _default_wd(node):
    """`defaults.run.working-directory`，workflow 層與 job 層同一個形狀。"""
    if not isinstance(node, dict):
        return None
    defaults = node.get("defaults")
    if not isinstance(defaults, dict):
        return None
    run = defaults.get("run")
    if not isinstance(run, dict):
        return None
    wd = run.get("working-directory")
    return wd if isinstance(wd, str) else None


def resolve_invocation(raw, bases, env, repo_root):
    """把一個呼叫目標解成 repo 內的檔案。

    回傳 `(Path, None)` 解開了；`(None, reason)` 解不開（fail-closed）；
    `(None, None)` 它根本不是一個檔案目標（旗標之類），略過即可。
    """
    value = expand_vars(strip_quotes(raw), env)
    if not value or value in _NO_FILE_FLAGS or value.startswith("-"):
        return None, None
    if _STILL_DYNAMIC.search(value):
        return None, "展開後仍含 shell 變數或萬用字元：%r" % value
    candidates = [Path(value)] if value.startswith("/") else [b / value for b in bases]
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved.is_file() and _within(resolved, repo_root):
            return resolved, None
    # 解析得出字面路徑但它不在 repo 內（例如系統工具），不是缺口。
    if not _looks_repo_relative(value):
        return None, None
    return None, "解析為 %r，但在 repo 內找不到這個檔案（基準：%s）" % (
        value, "、".join(str(b) for b in bases))


def _looks_repo_relative(value):
    """`./x`、`a/b.py` 這種才可能是 repo 內的檔案；`grep`、`/usr/bin/env` 不是。"""
    if value.startswith("/"):
        return False
    return "/" in value or value.startswith("./")


def step_surfaces(steps, loc, inherited_wd):
    """一串 `steps:` 的可執行面。workflow 的 job 與 composite action 的 `runs` 共用它。

    **共用是刻意的**：composite action 的步驟與 workflow 的步驟在 GitHub 眼中是同一種
    東西（同樣的 `uses:`／`run:`／`with:`），對其中一種嚴格、對另一種不看，就是 F1 的
    形狀。

    第四個回傳欄位是這個 step 的 working-directory——可達閉包用它決定相對路徑的基準。
    """
    out = []
    for idx, step in enumerate(steps or []):
        if not isinstance(step, dict):
            continue
        sloc = "%s / step %d（%s）" % (loc, idx + 1, step.get("name") or step.get("id") or "未命名")
        wd = step.get("working-directory")
        wd = wd if isinstance(wd, str) else inherited_wd
        if isinstance(step.get("uses"), str):
            out.append(("uses", sloc, step["uses"], wd))
        if isinstance(step.get("run"), str):
            out.append(("run", sloc, step["run"], wd))
        with_block = step.get("with")
        if isinstance(with_block, dict):
            for key, value in with_block.items():
                # 多行字串才是腳本；單行的 with 值是設定。`script:`（github-script）
                # 明確納入，即使它只有一行。
                if isinstance(value, str) and ("\n" in value or key in ("script", "args", "cmd", "run")):
                    out.append(("withscript", "%s / with.%s" % (sloc, key), value, wd))
    return out


def workflow_surfaces(doc, wf_wd):
    """列出一份 workflow 的**可執行面**，回傳 (kind, 位置, 值, working-directory)。

    刻意不含 `name:`／`description:`／YAML 註解——理由見模組 docstring。
    """
    out = []
    if "engine" in doc:
        out.append(("engine", "頂層", str(doc["engine"]), wf_wd))
    for jname, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        loc = "job %s" % jname
        job_wd = _default_wd(job) or wf_wd
        if "engine" in job:
            out.append(("engine", loc, str(job["engine"]), job_wd))
        if isinstance(job.get("uses"), str):
            out.append(("uses", loc, job["uses"], job_wd))
        out.extend(step_surfaces(job.get("steps"), loc, job_wd))
    return out


def action_surfaces(doc):
    """列出一份 composite action 的可執行面，形狀與 workflow 那一份相同。"""
    out = []
    if "engine" in doc:
        out.append(("engine", "頂層", str(doc["engine"]), None))
    runs = doc.get("runs")
    if not isinstance(runs, dict):
        raise ExternalError("action.yml 沒有 `runs:` 區塊，無法判定它的可執行面。")
    out.extend(step_surfaces(runs.get("steps"), "runs", None))
    return out


def judge_surface(c, where, kind, value, strict_uses=True):
    """對一個可執行面下判定。workflow 與 composite action 共用同一份規則。

    `strict_uses=False` 只鬆開 `uses:` 的允許清單（給 `ci.yml` 用），`engine:`、
    禁止清單與 `run:` 的 token 掃描一律照舊。理由見模組說明的 M-5 段。
    """
    if kind == "engine":
        c.check(
            "ENGINE-1:" + where, False, "",
            "%s 出現 `engine:` 鍵（值 %r）。那是 gh-aw 的 frontmatter 鍵，代表這一份"
            "被改成代理式承載。\n  預期：無 engine 鍵\n  實得：engine: %s"
            % (where, value, value),
        )
    elif kind == "uses":
        agentic = [t for t in KNOWN_AGENTIC_USES if t in value.lower()]
        allowed = (any(rx.match(value) for rx in USES_ALLOWLIST) if strict_uses
                   else not agentic)
        if allowed and not agentic:
            return
        if agentic:
            detail = "它命中已知的代理式承載樣式 %s——判定邏輯不得放在 agent step 裡" % agentic
        else:
            detail = (
                "它不在允許清單內。允許清單刻意很窄（`actions/*` 與本 repo 的 "
                "aidlc-sync 資產），因為本檢查要防的正是「有人引入了一個我沒想到的 "
                "agent action」——禁止清單只擋得住它認得的名字"
            )
        c.check(
            "USES-1:" + where, False, "",
            "%s 的 `uses: %s` 不被允許。%s。\n  預期：%s\n  實得：%s"
            % (where, value, detail,
               ("符合允許清單之一 %s" % [rx.pattern for rx in USES_ALLOWLIST])
               if strict_uses else ("不命中已知代理式承載 %s" % list(KNOWN_AGENTIC_USES)),
               value),
        )
    else:  # run / withscript
        body = strip_shell_comments(value)
        low = body.lower()
        hits = [t for t in AGENTIC_TOKENS if t in low]
        if LOCK_TOKEN in low:
            hits.append(LOCK_TOKEN)
        if not hits:
            return
        c.check(
            "RUN-1:" + where, False, "",
            "%s 的腳本（已剝除 shell 註解）出現代理式／編譯產物字樣 %s。\n"
            "  預期：不含 %s\n  實得：命中 %s"
            % (where, hits, list(AGENTIC_TOKENS) + [LOCK_TOKEN], hits),
        )


def scan(repo_root):
    workflows, all_yml, sources = sync_workflow_sources(repo_root)
    locks = [p for p in all_yml if p.name.endswith(".lock.yml")]

    c = Checker("R-1.2 代理式步驟靜態檢查")

    # ---- LOCK-1：N:C-3 的釘子 ---------------------------------------------
    c.check(
        "LOCK-1", not locks,
        "workflows 目錄下沒有 aidlc-sync-*.lock.yml（同步機制為純 Actions）",
        "workflows 目錄出現了 %s。四支同步 workflow 已全數定案為**純 Actions**"
        "（`tech-stack-decisions.md`，2026-08-30T06:11:59Z 更正 N:C-3）——`.lock.yml` 是 "
        "gh-aw 的編譯產物，它的出現代表有人把某支同步 workflow 改成代理式承載，正是 R-1.2 "
        "要攔的事。\n  預期：aidlc-sync-*.lock.yml 檔案數 0\n  實得：%d（%s）"
        % ([p.name for p in locks], len(locks), "、".join(p.name for p in locks)),
    )

    # ---- FILES-1：至少要有東西可檢 ----------------------------------------
    c.check(
        "FILES-1", bool(sources),
        "找到 %d 份 aidlc-sync-*.yml 原始檔：%s" % (len(sources), "、".join(p.name for p in sources)),
        "在 %s 找不到任何 aidlc-sync-*.yml。**零目標的檢查是恆綠的檢查**，這正是 N:C-3 "
        "判為 Critical 的失效形狀。\n  預期：≥ 1 份\n  實得：0" % workflows,
    )

    # ---- LOGICAL-1：四個邏輯名稱齊備 --------------------------------------
    found_logical = {logical_name(p) for p in sources}
    missing = [n for n in REQUIRED_LOGICAL if n not in found_logical]
    c.check(
        "LOGICAL-1", not missing,
        "四個邏輯 workflow 齊備：%s" % "、".join(REQUIRED_LOGICAL),
        "缺少邏輯 workflow：%s。檔案以 glob 列舉，**但邏輯名稱必須另外斷言**——某支被刪掉"
        "或改名時，只靠 glob 的檢查會少檢一支而且全綠。\n  預期：%s\n  實得：%s"
        % ("、".join(missing), "、".join(REQUIRED_LOGICAL),
           "、".join(sorted(found_logical)) or "（無）"),
    )

    # ---- 可達閉包 ---------------------------------------------------------
    closure = build_closure(repo_root, sources, c)
    closure.report()

    return c.report()


def build_closure(repo_root, sources, c):
    """把種子展開到不動點。`scan()` 與 `scan_surface()` 共用同一段，不寫兩份。

    「決定性 job」在這四支 workflow 裡是**全部的 job**，這不是省略判定而是判定本身：
    它們承載的全部是映射、解析與回寫（`business-rules.md` R-2），而 ADR-0013 把判斷性
    的工作放在**另一種承載**（gh-aw 的 `.md` workflow）上。所以「這支 workflow 裡有一個
    合法的代理式 job」在本設計下不成立——若哪天真的需要，那是一次要有人看過的承載形式
    變更，正好該讓本檢查紅一次。
    """
    closure = Closure(repo_root, c)
    for path in sources:
        closure.seed_workflow(path, strict_uses=True)

    # 五份 composite action 是同步機制自己的資產，所以它們**也是種子**，不是只有被
    # `uses:` 參照到才掃。可達閉包補的是「判定被搬到 repo 別處」，它不取代「同步機制自己
    # 的目錄一律全掃」——本 repo 三支 `*-impl.yml` 其實是直接 `bash "$MAP_SH"`、完全沒有
    # `uses: ./.github/actions/…`，只靠參照回填的話這五份 action.yml 會一份都掃不到，
    # 那正是 iteration 1 的 F1 原樣復發。
    actions_root = repo_root / ".github" / "actions"
    if actions_root.is_dir():
        for d in sorted(actions_root.glob("aidlc-sync-*")):
            if d.is_dir():
                closure.note_action(d.name, "aidlc-sync-* 目錄種子")

    # M-5：`ci.yml` 承載 U-10a 的同步判定，所以它也是種子。合成樹沒有 ci.yml 是正常的
    # （那些樹只在驗證本檔的其他行為），所以「不存在」不判紅；真實 repo 的 ci.yml 一定
    # 在，而它有沒有真的進掃描面由 `run-selftest-tests.py` 對真實 repo 斷言。
    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    if ci_yml.is_file():
        closure.seed_workflow(ci_yml, strict_uses=False)

    closure.run()
    return closure


def sync_workflow_sources(repo_root):
    """四支同步 workflow 的原始檔（排除 gh-aw 的編譯產物 `.lock.yml`）。"""
    workflows = repo_root / ".github" / "workflows"
    if not workflows.is_dir():
        raise ExternalError(
            "找不到 %s。本檢查以 workflow 目錄為輸入，目錄不存在時**不得靜默通過**"
            "——那會是一個對空集合成立的斷言。" % workflows
        )
    all_yml = sorted(workflows.glob("aidlc-sync-*.yml"))
    return workflows, all_yml, [p for p in all_yml if not p.name.endswith(".lock.yml")]


def scan_surface(repo_root):
    """掃描面的全部成員（repo 相對路徑），**不做任何判定、不印任何東西**。

    `check-paths-relations.py` 的 COVERAGE-2 用它比對觸發 allowlist：R-1.2 掃得到的每一
    個檔，都必須讓「改它的 PR」觸發本自我測試——否則這道閘門的紅燈會落在下一個改同步機
    制的無關 PR 上，而那正是 `business-rules.md` R-4 逐字警告的失效方式。

    這裡刻意把判定丟進一個用完就扔的 Checker：掃描面是一件事實，COVERAGE-2 只需要那件
    事實；R-1.2 自己的判定由 `check-agentic-steps.py` 那一支負責報告，不在這裡重複一份。
    """
    _workflows, _all_yml, sources = sync_workflow_sources(repo_root)
    closure = build_closure(repo_root, sources, Checker("（掃描面查詢，判定丟棄）"))
    return closure.surface_rel_paths()


def main():
    ap = argparse.ArgumentParser(
        description="U-9 R-1.2：aidlc-sync-* 的決定性 job 不得含代理式引擎步驟"
    )
    ap.add_argument(
        "--repo-root", default=None,
        help="要檢查的 repo 樹根目錄（預設：由本檔位置推導）。行為測試用它餵合成的暫存樹。",
    )
    args = ap.parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[3]
    print("repo 樹：%s" % repo_root)
    return scan(repo_root)


if __name__ == "__main__":
    sys.exit(run_checker(main))
