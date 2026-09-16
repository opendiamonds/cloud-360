#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U-10a 的靜態檢查：確認 .github/workflows/ci.yml 的回寫排除設定沒有走樣。

為什麼需要這支腳本
------------------
U-10a 交付的是 YAML 設定，沒有可以單元測試的程式。它的真實完成判準（推一顆含
[aidlc-sync] 的 commit，觀察四道關卡有沒有跑）只有在真的推送時才觀察得到，屬 Bolt 1
的整合驗證。這支腳本補的是中間那一段：把「設定應該長什麼樣」寫成機械可判的斷言，讓
之後任何人改壞 ci.yml 的這幾處時，不必等到真的推一次同步回寫才發現。

它檢查七件事
------------
1. on.push 有 paths-ignore，而且恰好一條。
2. 那一條逐字等於「由 U-4 record.sh 的白名單常數推導出來」的 glob——不是本檔自抄一份
   路徑字面值。record.sh 若哪天放寬白名單，推導值就會變、這裡就會紅。
3. on.pull_request 沒有 paths-ignore（有的話是假保證，見 ci.yml 的註解）。
4. 四個既有 job 都有 needs: gate 與正確的 if:，且 gate job 有 is_sync output。
5. gate job grep 的標記與 record.sh 的 SYNC_MARKER 是同一個字串。第 2 條是路徑那一半
   的漂移防護，這條是標記那一半——兩邊漂移時 gate 對每一顆同步回寫都判 false，排除
   完全失效且不紅燈。（本條為計畫六項之外的第七項，見 code-summary 的偏離說明。）
6. concurrency.group 不含 github.actor（加它的前提已被查證為假）。
7. 四個既有 job 的 name / runs-on / steps 與變更前逐字相同（NFR-C1）。

用法
----
    python3 .github/actions/aidlc-sync-ci-guard/check-ci-yml.py
    python3 .github/actions/aidlc-sync-ci-guard/check-ci-yml.py --emit-golden <某份 ci.yml>

--emit-golden 會從指定的 ci.yml 產生 ci-jobs-golden.json（本檔旁）。golden 的保護力
來自它是被 commit 進版控的：重新產生它是一個會出現在 diff 裡、需要有人解釋的動作，
不是這支腳本能自己防的事。

本檔**只做文字／結構斷言，不驗行為**——這是它結構性的盲區，不是暫時的不足。
「不動任何字串、只改邏輯方向」的修改（分支互換、grep -qFv、! grep、輸入源換成常數）
本檔一律看不到，而它們的後果比標記漂移更嚴重（四道關卡對**所有**正常 commit 永久失效）。
那一類由旁邊的 run-probe-tests.py 承接：它把 gate 的 probe 腳本抽出來實際執行、斷言
判定值，對「換個寫法達成同樣邏輯」免疫。**兩支要一起跑，只跑本檔是不夠的。**

本檔不被 ci.yml 呼叫（刻意）：接進 repo-contract job 會變成 ci.yml 檢查自己——把
if: 改壞的那一次修改，同時就讓檢查自己被 skip 掉。正確落點是 Bolt 1 的整合驗證或另一
支獨立 workflow，不在 U-10a 範圍內。這是已知缺口，如實記載。

相依：PyYAML（本機開發環境已有）。
"""

import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path, PurePosixPath

try:
    import yaml
except ImportError:  # 相依缺席要講清楚是缺什麼，不要丟 traceback
    sys.stderr.write("找不到 PyYAML。這支腳本用它解析 ci.yml；請先 pip install pyyaml\n")
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
RECORD_SH = REPO_ROOT / ".github" / "actions" / "aidlc-sync-record" / "record.sh"
GOLDEN = Path(__file__).resolve().parent / "ci-jobs-golden.json"

# 變更前就存在、且 NFR-C1 要求一字不動的四個 job。
GUARDED_JOBS = ["repo-contract", "frontend", "backend", "docker-build"]
GOLDEN_KEYS = ["name", "runs-on", "steps"]
GATE_JOB = "gate"
EXPECTED_IF = "needs.gate.outputs.is_sync != 'true'"

# record.sh 的 record_path regex 裡，代表「一個路徑片段」的那個 capture group。
# 它的字元集不含 /，所以它與 GitHub glob 的 * 是等價的（* 同樣不跨 /）——這個等價
# 關係就是下面把 regex 機械轉成 glob 的依據。
RECORD_PATH_GROUP = "([A-Za-z0-9._-]+)"
GLOB_SAFE = re.compile(r"^[A-Za-z0-9._/-]*$")


class Checker:
    """收集檢查結果。每個失敗訊息都要說明「這條為什麼重要」，不只是不相符。"""

    def __init__(self):
        self.results = []

    def check(self, cid, ok, ok_msg, fail_msg):
        self.results.append((cid, bool(ok), ok_msg if ok else fail_msg))
        return bool(ok)

    def failed(self):
        return [r for r in self.results if not r[1]]

    def report(self):
        for cid, ok, msg in self.results:
            print("%s %-6s %s" % ("[通過]" if ok else "[失敗]", cid, msg))
        bad = self.failed()
        print("")
        print("%d 項檢查，%d 失敗。" % (len(self.results), len(bad)))
        return 0 if not bad else 1


def load_ci(path):
    """讀 ci.yml。YAML 1.1 把裸 on 當布林，所以觸發區塊的鍵是 True 不是 'on'。"""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit("ci.yml 的頂層不是一個 mapping，無法檢查：%s" % path)
    triggers = doc.get("on", doc.get(True))
    return doc, triggers


def derive_glob_from_record_sh():
    """從 U-4 的 record.sh 推導出「同步回寫唯一寫得到的路徑」對應的 glob。

    刻意不在本檔寫死路徑字面值：寫死等於在兩個地方各存一份同一個事實，其中一份遲早
    會過期而沒人發現。回傳 (glob, 說明)；推導不出來就丟 SystemExit，因為那代表白名單
    的形狀變了，需要人看過才能決定新的 glob 該長什麼樣。
    """
    if not RECORD_SH.exists():
        raise SystemExit(
            "找不到 %s。這支腳本靠它推導白名單；U-4 尚未落地或路徑改了的話，"
            "請先確認 ci.yml 的 paths-ignore 是否仍與同步機制的寫入範圍一致。" % RECORD_SH
        )
    text = RECORD_SH.read_text(encoding="utf-8")

    m_name = re.search(r'^STATE_FILE_NAME="([^"]+)"', text, re.M)
    if not m_name:
        raise SystemExit(
            "在 record.sh 找不到 STATE_FILE_NAME 常數。它是同步回寫唯一允許的檔名，"
            "推導 paths-ignore 的 glob 必須以它為準。"
        )
    state_file_name = m_name.group(1)

    m_re = re.search(r"local re='\^([^']+)\$'", text)
    if not m_re:
        raise SystemExit(
            "在 record.sh 找不到 record_path 的驗證 regex。它界定了同步回寫可以寫到"
            "哪些目錄，是 glob 的另一半來源。"
        )
    body = m_re.group(1)

    parts = body.split(RECORD_PATH_GROUP)
    for part in parts:
        if not GLOB_SAFE.match(part):
            raise SystemExit(
                "record.sh 的 record_path regex 出現無法機械轉成 glob 的片段：%r。"
                "白名單形狀變了，請人工確認 ci.yml 的 paths-ignore 該怎麼跟著改。" % part
            )
    glob = "*".join(parts).rstrip("/") + "/" + state_file_name
    why = "由 record.sh 的 STATE_FILE_NAME=%r 與 record_path regex %r 推導" % (
        state_file_name,
        "^" + body + "$",
    )
    return glob, why


def derive_marker_from_record_sh():
    """從 U-4 的 record.sh 取出同步回寫 commit 訊息會帶的標記。

    與 derive_glob_from_record_sh 同一個理由：不在本檔寫死字面值。gate job 是拿這個
    字串去 grep commit 訊息的，兩邊若漂移，gate 會對每一顆同步回寫都判 is_sync=false
    ——四道關卡照跑，這個單元等於沒做，而且完全不紅燈。
    """
    text = RECORD_SH.read_text(encoding="utf-8")
    m = re.search(r'^SYNC_MARKER="([^"]+)"', text, re.M)
    if not m:
        raise SystemExit(
            "在 record.sh 找不到 SYNC_MARKER 常數。它是 gate job 判斷「這顆 commit 是"
            "同步回寫」的唯一依據，兩邊必須是同一個字串。"
        )
    return m.group(1)


def gate_grep_patterns(gate):
    """抽出 gate job 的 run 腳本裡**實際傳給 grep 的**字面樣式。

    為什麼不是對整段 run 文字做子字串搜尋（本檔第一版就是，被 reviewer 攻破）
    ----------------------------------------------------------------------
    子字串比對只證明「這個字串出現在腳本的某處」，不證明「它是被拿去比對的東西」。
    實測三種反例都能讓子字串版通過而機制實際失效：

      A. grep 換成錯的標記，同一行加一句含正確標記的註解
      B. grep 換成錯的標記，另一行的 echo 訊息裡含正確標記
      C. 整段 grep 拿掉，只留 UNUSED_MARKER='[aidlc-sync]' 這種沒人用的賦值

    C 最能說明問題：連比對動作本身都不存在了，檢查還是綠的。這正是 MARKER-1
    被引入要防的那種靜默失效，第一版的它自己就能被同一種手法騙過。

    改法：逐行 shlex 斷詞（`comments=True` 讓 `#` 之後的內容自動消失，反例 A 因此
    失效），找出 `grep`，取它第一個非選項引數當樣式（`-e`／`-f` 的話取其後一個）。
    只有真的被送進 grep 的東西才會進回傳值——反例 B、C 因此失效。

    已知且刻意接受的限制（寫出來，不假裝沒有）
    ----------------------------------------
    1. 樣式若寫成變數（`grep -qF "$M"`），這裡拿到的是 `$M` 字面而非它的值，會判紅。
       方向是安全的（fail closed，逼人改回字面值或改這支檢查），不是漏放。
    2. grep 存在且樣式正確、但它的結果**怎麼被用**——比對方向（`-v`／`!`）、
       兩個分支哪個設 true、輸入是 `$message` 還是常數——本檢查一概不看。
       reviewer iteration 2 實測四種不動標記字串就能反轉判定的手法，本檢查對
       它們**全部失明**。這一類**不是**用更多文字斷言去補的（那是同一個錯誤再犯
       一次）：由 `run-probe-tests.py` 的行為測試承接，它直接執行 probe 腳本並
       斷言判定值，對「換個寫法達成同樣邏輯」免疫。
    3. `grep` 呼叫若以 `\` 續行拆成多個物理行，該行斷詞會拋 ValueError 而被跳過，
       這裡偵測不到那次呼叫、判紅。方向安全（fail closed），但對一個功能正確、
       只是換了折行風格的修改是假紅燈；下面的 except 分支會印出行號提示，讓維護者
       分辨得出「真的標記漂移」與「斷詞限制」。
    """
    pats = []
    if not isinstance(gate, dict):
        return pats
    steps = gate.get("steps")
    if not isinstance(steps, list):
        return pats
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("run"), str):
            continue
        for line in step["run"].splitlines():
            try:
                # punctuation_chars=True 是必要的，不是講究：預設的 shlex.split 不把
                # ; | & 當分隔符，於是 `grep -qF '[aidlc-sync]'; then` 會斷出
                # '[aidlc-sync];'（尾巴多一個分號），永遠比不到正確的標記。
                lex = shlex.shlex(line, posix=True, punctuation_chars=True)
                lex.whitespace_split = True
                toks = list(lex)
            except ValueError as exc:
                # 未閉合的引號、或以 \ 續行的一行——斷不了詞就跳過，不要因此讓整支
                # 檢查掛掉。但要出聲：靜默跳過會讓「這行有個 grep」變成看不見的事實，
                # 而 MARKER-1 判紅時維護者無從分辨是標記真的漂移還是斷詞限制。
                sys.stderr.write(
                    "註：gate job 的這一行無法斷詞（%s），MARKER-1 看不到它裡面的 grep："
                    "%s\n" % (exc, line.strip())
                )
                continue
            for i, tok in enumerate(toks):
                if PurePosixPath(tok).name != "grep":
                    continue
                j = i + 1
                while j < len(toks) and toks[j].startswith("-") and toks[j] != "--":
                    # -e/--regexp/-f/--file 會把樣式放在下一個 token
                    if toks[j] in ("-e", "--regexp", "-f", "--file"):
                        j += 1
                        if j < len(toks):
                            pats.append(toks[j])
                    j += 1
                if j < len(toks) and toks[j] == "--":
                    j += 1
                if j < len(toks):
                    pats.append(toks[j])
    return pats


def collect_golden(doc):
    jobs = doc.get("jobs") or {}
    out = {}
    for name in GUARDED_JOBS:
        job = jobs.get(name)
        if not isinstance(job, dict):
            raise SystemExit("ci.yml 裡找不到 job %r，無法產生 golden。" % name)
        out[name] = {k: job.get(k) for k in GOLDEN_KEYS}
    return out


def emit_golden(source):
    src = Path(source)
    doc, _ = load_ci(src)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    payload = {
        "_comment": (
            "U-10a 的 NFR-C1 快照：四個既有 job 的 name / runs-on / steps 在變更前的樣子。"
            "由 check-ci-yml.py --emit-golden 產生，不要手改。"
        ),
        # 記來源檔的 sha256 而不是它的路徑：路徑是產生它的那台機器的事，sha 才可以被
        # 任何人複驗（git show <commit>:.github/workflows/ci.yml | shasum -a 256）。
        "_source_sha256": digest,
        "jobs": collect_golden(doc),
    }
    GOLDEN.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("已寫出 %s\n  來源：%s\n  來源 sha256：%s" % (GOLDEN, source, digest))
    return 0


def norm(value):
    """把值正規化成可逐字比對的字串。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def main():
    ap = argparse.ArgumentParser(description="U-10a：檢查 ci.yml 的回寫排除設定")
    ap.add_argument("--emit-golden", metavar="CI_YML",
                    help="從指定的 ci.yml 產生 NFR-C1 的 golden 快照後結束")
    args = ap.parse_args()

    if args.emit_golden:
        return emit_golden(args.emit_golden)

    if not CI_YML.exists():
        raise SystemExit("找不到 %s" % CI_YML)

    doc, triggers = load_ci(CI_YML)
    jobs = doc.get("jobs") or {}
    c = Checker()

    # ---- 1／2／3／4：paths-ignore 的存在、窄度與來源一致性 ------------------
    push = triggers.get("push") if isinstance(triggers, dict) else None
    ignores = push.get("paths-ignore") if isinstance(push, dict) else None
    has_one = isinstance(ignores, list) and len(ignores) == 1

    c.check(
        "SEC-1a", has_one,
        "on.push.paths-ignore 恰有一條：%s" % (ignores[0] if has_one else ""),
        "on.push.paths-ignore 必須恰好一條（目前：%r）。少了它，同步回寫的每一次推送都"
        "會建立一個新的 CI run 並取消開發者手上正在跑的那一個；多一條就是多一條讓程式碼"
        "繞過四道關卡的路。" % (ignores,),
    )

    expected_glob, why = derive_glob_from_record_sh()
    actual_glob = ignores[0] if has_one else None
    c.check(
        "SEC-1b", actual_glob == expected_glob,
        "glob 與同步機制的寫入白名單一致（%s）" % why,
        "paths-ignore 的 glob 是 %r，但同步機制實際只寫得到 %r（%s）。兩者不一致有兩種"
        "後果，都不能接受：glob 比白名單寬，代表有檔案能以「同步」為名繞過 CI；比白名單窄，"
        "代表同步回寫仍會觸發 CI，這個單元等於沒做。" % (actual_glob, expected_glob, why),
    )

    c.check(
        "SEC-1c", actual_glob is not None and "**" not in actual_glob,
        "glob 不含 ** ——沒有跨目錄的萬用比對",
        "paths-ignore 的 glob %r 含有 **，它會跨越目錄層級。aidlc/** 會讓所有 AIDLC 產出"
        "繞過 repo contract 檢查，**/*.json 會讓 package-lock.json、"
        ".github/aw/actions-lock.json 這類供應鏈檔案繞過 CI。" % (actual_glob,),
    )

    pr = triggers.get("pull_request") if isinstance(triggers, dict) else None
    c.check(
        "SEC-1d", not (isinstance(pr, dict) and "paths-ignore" in pr),
        "on.pull_request 沒有 paths-ignore",
        "on.pull_request 出現了 paths-ignore。GitHub 對 pull_request 事件的路徑過濾比對的"
        "是整個 PR 的檔案集合、不是這一次推送的 commit，所以它永遠不會成立——留著只會讓人"
        "以為 PR 側也被擋掉了，而實際上沒有。",
    )

    # ---- 5：gate job 存在且輸出 is_sync ------------------------------------
    gate = jobs.get(GATE_JOB)
    gate_out = gate.get("outputs") if isinstance(gate, dict) else None
    c.check(
        "GATE-1",
        isinstance(gate, dict) and isinstance(gate_out, dict) and "is_sync" in gate_out,
        "gate job 存在並宣告 is_sync output",
        "找不到 job %r 或它沒有宣告 is_sync output。四個既有 job 的 if: 讀的就是這個值，"
        "沒有它時 needs.gate.outputs.is_sync 恆為空字串——條件永遠成立、排除完全失效，"
        "而且不會有任何錯誤訊息。" % GATE_JOB,
    )

    expected_marker = derive_marker_from_record_sh()
    grep_pats = gate_grep_patterns(gate)
    c.check(
        "MARKER-1", expected_marker in grep_pats,
        "gate job 拿去 grep 的樣式含 record.sh 的 SYNC_MARKER=%r" % (expected_marker,),
        "gate job **實際傳給 grep 的**樣式是 %r，其中沒有 record.sh 定義的標記 %r。"
        "（這裡看的是 grep 的引數，不是整段腳本的文字——標記出現在註解、echo 訊息或"
        "沒人用的變數賦值裡都不算數，那三種都能讓機制實際失效而檢查照樣綠。）"
        "兩邊漂移時 gate 會對每一顆同步回寫都判 is_sync=false——四道關卡照跑、排除"
        "完全失效，而且不會有任何錯誤訊息。若確實要改標記，record.sh 與 ci.yml 必須"
        "在同一個 PR 一起改。" % (grep_pats, expected_marker),
    )

    # ---- 6：concurrency.group 不含 github.actor ----------------------------
    group = ((doc.get("concurrency") or {}).get("group") or "") if isinstance(doc.get("concurrency"), dict) else ""
    c.check(
        "CONC-1", "github.actor" not in group,
        "concurrency.group 不含 github.actor",
        "concurrency.group 出現了 github.actor：%r。它的前提（同步以另一個身分推送）已經"
        "被查證為假——ADR-0016 §1 把同步身分定為擁有者帳號的 token，實測開發者與同步機制的"
        "github.actor 相同。加上去不會讓任何 run 免於被取消，只會讓下一個讀的人以為問題"
        "已經解決。" % group,
    )

    # ---- 7：四個既有 job 的 needs / if -------------------------------------
    for name in GUARDED_JOBS:
        job = jobs.get(name)
        if not isinstance(job, dict):
            c.check("NEEDS:" + name, False, "", "ci.yml 裡找不到 job %r。" % name)
            c.check("IF:" + name, False, "", "ci.yml 裡找不到 job %r。" % name)
            continue

        needs = job.get("needs")
        needs_list = [needs] if isinstance(needs, str) else (needs or [])
        c.check(
            "NEEDS:" + name, GATE_JOB in needs_list,
            "%s needs: %s" % (name, GATE_JOB),
            "job %r 沒有 needs: %s。沒有這條依賴，它會與 gate 同時開跑，if: 讀到的 output"
            "還不存在，排除等於沒生效。" % (name, GATE_JOB),
        )

        cond = " ".join(str(job.get("if", "")).split())
        c.check(
            "IF:" + name, cond == EXPECTED_IF,
            "%s if: %s" % (name, EXPECTED_IF),
            "job %r 的 if: 是 %r，應為 %r。這一行就是「同步回寫不跑這道關卡」的全部實作，"
            "缺了或寫錯，這個 job 在每一次同步回寫的 PR 事件上都會照跑。" % (name, cond, EXPECTED_IF),
        )

    # ---- 8：NFR-C1 —— 四個 job 的 name / runs-on / steps 與 golden 逐字相同 --
    if not GOLDEN.exists():
        c.check("NFR-C1", False, "", "找不到 golden 快照 %s，無法驗證四個既有 job 未被改動。" % GOLDEN)
    else:
        golden = json.loads(GOLDEN.read_text(encoding="utf-8")).get("jobs", {})
        for name in GUARDED_JOBS:
            job = jobs.get(name)
            if not isinstance(job, dict):
                c.check("NFR-C1:" + name, False, "", "ci.yml 裡找不到 job %r。" % name)
                continue
            actual = {k: job.get(k) for k in GOLDEN_KEYS}
            want = golden.get(name)
            if actual == want:
                c.check("NFR-C1:" + name, True,
                        "%s 的 name / runs-on / steps 與變更前逐字相同" % name, "")
                continue
            drift = [k for k in GOLDEN_KEYS if actual.get(k) != (want or {}).get(k)]
            c.check(
                "NFR-C1:" + name, False, "",
                "job %r 的 %s 與變更前不同。U-10a 只被允許對這四個 job 加 needs: 與 if: 兩行"
                "（NFR-C1：既有四道關卡不得因本變更而破壞）——其他任何差異都代表這次改動越界了。"
                "\n  變更前：%s\n  現在：%s"
                % (name, "／".join(drift) or "內容", norm(want), norm(actual)),
            )

    return c.report()


if __name__ == "__main__":
    sys.exit(main())
