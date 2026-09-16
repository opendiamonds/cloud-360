#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""U-10a 的行為測試：把 ci.yml 的 gate/probe 腳本抽出來**實際執行**，斷言它的判定。

為什麼需要這一支，而 check-ci-yml.py 不夠
----------------------------------------
`check-ci-yml.py` 是**文字斷言**：它讀 YAML、比對字串與結構。它抓得到「標記漂移」
「if: 被拿掉」「job 內容被改」這類**形狀**的問題。

但 reviewer iteration 2 示範了它抓不到的一整類：**不動任何字串、只動邏輯方向**。
最簡單的反例是把

    if printf '%s\\n' "$message" | grep -qF '[aidlc-sync]'; then
      is_sync=true
    else
      is_sync=false
    fi

的兩個分支對調。`grep` 呼叫一個字元都沒動，19 項文字檢查全綠——但判定完全反轉：
**每一顆正常開發者 commit 都會被當成同步回寫而跳過全部四道關卡**，每一顆真正的
同步回寫反而照跑。同類的還有 `grep -qFv`、`! grep`、把輸入從 `"$message"` 換成
常數字面值——四種都不動標記字串。

這裡的教訓不是「再多加幾條文字斷言」——那是同一個錯誤再犯一次，而且每加一條就
多一個可以繞過的邊界（iteration 1 與 iteration 2 各證明了一次）。**正確的修法是
換一種東西：不要斷言腳本長什麼樣，直接執行它，斷言它對給定輸入吐出什麼判定。**
行為測試對「換個寫法達成同樣邏輯」是免疫的，因為它量的就是邏輯本身。

做法
----
從 ci.yml 解析出 gate job 裡 `id: probe` 那個 step 的 `run:` 腳本，以 bash 執行，
用環境變數餵不同輸入，讀回它寫進 $GITHUB_OUTPUT 的 is_sync 值並斷言。

- `push` 事件的路徑只讀 $PUSH_HEAD_MESSAGE，不需要 git，可直接跑。
- 非 push 事件會呼叫 `git log`；用 PATH 前置一個假的 git 腳本來控制它的輸出與
  回傳值，藉此測到「讀得到訊息」與「讀不到訊息（fail-open）」兩條分支。

標記字串本身**從 record.sh 推導**（與 check-ci-yml.py 的 SEC-1b／MARKER-1 同一個
理由：不在第三個地方再抄一份）。

⚠ 這支測試會**以真實 shell 執行從 ci.yml 抽出來的腳本**
------------------------------------------------------
那正是它相對於文字比對的價值所在（見上），但也代表：**ci.yml 的 probe step 裡有什麼，
跑這支測試就會在你的機器上執行什麼。**

reviewer iteration 2 實地撞到這一點：它為了驗證 M-5（`ci.yml` 不在 R-1.2 的視野內）把
一個代理式 CLI 呼叫注入 probe step，然後跑這支測試——那個 CLI **真的被啟動並等待輸入**，
測試就這樣掛住，直到被 `pkill` 才結束。

這是「行為測試執行受測資料」的固有性質，不是缺陷，本檔**刻意不加逾時或沙箱**：那會削弱
它「照 GitHub 的方式（`bash -e`）真的跑一次」的保證，而那個保證是它存在的理由。風險僅限
於本機手動執行——CI 上跑的是 PR head 的 ci.yml，與該 workflow 自己會執行的內容同一份。

實務建議：在本機改 `ci.yml` 的 gate/probe 之後跑這支測試前，先看一眼你加了什麼。它掛住
時多半不是測試壞了，是你注入的東西正在等 stdin。

相依：PyYAML、bash。用法：python3 .github/actions/aidlc-sync-ci-guard/run-probe-tests.py
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("找不到 PyYAML。這支腳本用它解析 ci.yml；請先 pip install pyyaml\n")
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
RECORD_SH = REPO_ROOT / ".github" / "actions" / "aidlc-sync-record" / "record.sh"


def marker():
    """同步回寫的標記，從 U-4 的 record.sh 推導——不在本檔再抄一份字面值。"""
    m = re.search(r'^SYNC_MARKER="([^"]+)"', RECORD_SH.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("在 record.sh 找不到 SYNC_MARKER 常數，無法推導測試輸入。")
    return m.group(1)


def probe_script():
    """抽出 gate job 裡 id: probe 那個 step 的 run 腳本。"""
    doc = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    gate = (doc.get("jobs") or {}).get("gate")
    if not isinstance(gate, dict):
        raise SystemExit("ci.yml 裡找不到 gate job——U-10a 的排除機制不存在。")
    for step in gate.get("steps") or []:
        if isinstance(step, dict) and step.get("id") == "probe" and isinstance(step.get("run"), str):
            return step["run"]
    raise SystemExit(
        "gate job 裡找不到 id: probe 的 step。這支測試靠它的 id 定位受測腳本；"
        "若 step 被改名，請同步改這裡，不要讓測試靜默地什麼都沒測。"
    )


def statement_lines(script):
    """腳本裡**會被執行**的行的索引（跳過空行與整行註解）。"""
    return [i for i, ln in enumerate(script.splitlines())
            if ln.strip() and not ln.strip().startswith("#")]


def inject_before_first_statement(script, line):
    """把 line 插在**第一個不是 `set` 的敘述**之前。

    為什麼不是「插在最後一行 `set` 之後」（reviewer iteration 2 的 M-6，Major）
    ---------------------------------------------------------------------
    舊版的錨點是「最後一行以 `set ` 開頭的指令」，也就是**從它所不信任的那段文字算出
    插入點**：注入永遠落在 `set +e` 之後的保護區內。reviewer 實跑四種 `set +e` 位置：

        V0 原位                                      → PASS（綠，正確）
        V1 set +e 移到最後一行                        → FAIL（紅，正確）
        V2 set +e 下移到判定邏輯之後、兩行 echo 之前   → PASS（綠）  ← 洞
        V3 set +e 埋進死的 if 分支                    → FAIL（紅，正確）

    V2 之下，`git log`／`printf | grep` 那整段——也就是「下一個人會加裸命令」的那一段
    ——全部在 errexit 下裸奔，而測試全綠。

    新的錨點與 `set` 的位置**無關**：它是「判定邏輯從哪裡開始」。要斷言的性質因此變成
    「**在第一個非 `set` 的敘述執行之前，errexit 必須已經關掉**」——`set +e` 寫在哪一行
    都逃不掉，因為只要它排在判定邏輯後面，這個注入點就會落在保護區外。

    對 brief 的一處刻意偏離：brief 寫「直接注入在整段腳本的第一行」。實測那會讓**正確的
    腳本也必死**——GitHub 用 `bash -e {0}`，errexit 從第 1 行就是開著的，而 `set +e` 再
    怎麼早也只能是第一個敘述，不可能早於「第一行」。照字面做出來的是一條恆紅的測試。
    這裡取它的意圖（注入點不得由 `set` 的位置推導）而不是它的字面。
    """
    lines = script.splitlines()
    for i in statement_lines(script):
        if lines[i].strip().startswith("set "):
            continue
        lines.insert(i, line)
        return "\n".join(lines) + "\n"
    raise SystemExit(
        "probe 腳本裡除了 `set` 之外找不到任何敘述，注入測試失去錨點。這支測試靠它定位"
        "插入點；若腳本結構改了，請同步改這裡，不要讓測試靜默地什麼都沒注入。"
    )


def inject_before_last_statement(script, line):
    """把 line 插在**最後一個敘述**之前（腳本尾段也要在保護區內）。

    只測開頭會漏掉「中途把 errexit 重新打開」——`set -e` 再開一次，前半段照樣綠。
    """
    lines = script.splitlines()
    idx = statement_lines(script)
    if not idx:
        raise SystemExit("probe 腳本裡找不到任何敘述，注入測試失去錨點。")
    lines.insert(idx[-1], line)
    return "\n".join(lines) + "\n"


def run_probe(script, event_name, push_message="", pr_head_sha="", git_stub=None):
    """跑一次 probe 腳本，回傳 (is_sync 字串或 None, stdout, returncode)。

    git_stub 為 (stdout, exit_code)；給了就在 PATH 前面放一個假的 git。
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out_file = td / "gh_output"
        out_file.touch()
        env = dict(os.environ)
        env.update({
            "EVENT_NAME": event_name,
            "PUSH_HEAD_MESSAGE": push_message,
            "PR_HEAD_SHA": pr_head_sha,
            "GITHUB_OUTPUT": str(out_file),
        })
        if git_stub is not None:
            stub_out, stub_rc = git_stub
            bindir = td / "bin"
            bindir.mkdir()
            git = bindir / "git"
            git.write_text(
                "#!/bin/sh\ncat <<'STUB_EOF'\n%s\nSTUB_EOF\nexit %d\n" % (stub_out, stub_rc),
                encoding="utf-8",
            )
            git.chmod(0o755)
            env["PATH"] = "%s:%s" % (bindir, env.get("PATH", ""))

        # **必須是 `bash -e <檔案>`，不是 `bash -c`**：GitHub Actions 對沒有寫
        # `shell:` 的 `run:` 一律用 `bash -e {0}`（{0} 是它寫出來的腳本檔）。若這裡
        # 用不帶 -e 的 bash，測試環境的 errexit 就與 CI 相反——腳本裡任何一行裸命令
        # 回非 0，在 CI 會中止整個 step，在這裡卻若無其事地跑完，於是這支測試會對
        # 「gate 中途死掉」這整類失敗**結構性失明**。這正是 U-6／U-7／U-8 三支
        # workflow 撞到的同一個盲區（F5）。
        script_file = td / "probe.sh"
        script_file.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            ["bash", "-e", str(script_file)], env=env, capture_output=True, text=True
        )
        val = None
        for line in out_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("is_sync="):
                val = line.split("=", 1)[1]
        return val, proc.stdout + proc.stderr, proc.returncode


def main():
    M = marker()
    script = probe_script()
    failures = []

    # (名稱, kwargs, 期望的 is_sync, 這條在防什麼)
    cases = [
        ("push／訊息含標記 → true",
         dict(event_name="push", push_message="雜項(sync): 更新看板狀態 %s" % M),
         "true", "同步回寫必須被認出來，否則四道關卡會對它照跑"),

        ("push／訊息不含標記 → false",
         dict(event_name="push", push_message="功能(rbac): 新增權限矩陣"),
         "false", "**最重要的一條**：正常開發者 commit 必須照跑 CI。分支互換、"
                  "grep -qFv、! grep、輸入換成常數——四種手法都會讓這條變 true"),

        ("push／標記在多行訊息的第二行 → true",
         dict(event_name="push", push_message="雜項(sync): 更新\n\n%s" % M),
         "true", "訊息是多行的，比對必須是「含有」而非「等於」"),

        ("push／空訊息 → false",
         dict(event_name="push", push_message=""),
         "false", "空訊息不是同步回寫"),

        ("push／標記大小寫不同 → false",
         dict(event_name="push", push_message="雜項: %s" % M.upper()),
         "false", "-F 是固定字串比對，不該把大小寫不同的當成命中"),

        ("pull_request／PR head 訊息含標記 → true",
         dict(event_name="pull_request", pr_head_sha="deadbeef",
              git_stub=("雜項(sync): 更新看板狀態 %s" % M, 0)),
         "true", "PR 事件拿不到 head_commit.message，必須走 git log 那條路"),

        ("pull_request／PR head 訊息不含標記 → false",
         dict(event_name="pull_request", pr_head_sha="deadbeef",
              git_stub=("功能(admin): 加一欄", 0)),
         "false", "PR 事件的正常 commit 同樣必須照跑 CI"),

        ("pull_request／git 讀不到（非 0）→ false（fail-open）",
         dict(event_name="pull_request", pr_head_sha="deadbeef",
              git_stub=("fatal: bad object deadbeef", 128)),
         "false", "讀不到就往「不是同步」判：誤判成同步會讓一顆真的開發者 commit "
                  "完全沒被檢查，誤判成非同步只是多跑一輪"),

        ("pull_request／沒有 head sha → false",
         dict(event_name="pull_request", pr_head_sha=""),
         "false", "既無 head_commit 也無 head.sha 時保守判定"),

        ("schedule／既無訊息也無 sha → false",
         dict(event_name="schedule", pr_head_sha=""),
         "false", "未預期的事件型別不該被當成同步回寫"),
    ]

    print("受測對象：ci.yml 的 gate job，id: probe 的 run 腳本（以 bash -e 實際執行，非文字比對）")
    print("標記：%r（由 record.sh 的 SYNC_MARKER 推導）\n" % M)

    checks = 0

    for name, kwargs, want, why in cases:
        got, output, rc = run_probe(script, **kwargs)
        checks += 1
        ok = got == want
        print("%s %s" % ("[通過]" if ok else "[失敗]", name))
        if not ok:
            print("        期望 is_sync=%r，實得 %r（腳本 exit %d）" % (want, got, rc))
            print("        這條在防：%s" % why)
            if output.strip():
                print("        腳本輸出：%s" % output.strip().replace("\n", "\n        "))
            failures.append(name)

    # probe 腳本永遠不該以非 0 結束——gate 一失敗，四個 job 全被 skip，CI 等於沒跑。
    got, output, rc = run_probe(script, event_name="push", push_message="任意訊息")
    checks += 1
    ok = rc == 0
    print("%s probe 腳本以 exit 0 結束（gate 非 0 會讓四個 job 全被 skip）" % ("[通過]" if ok else "[失敗]"))
    if not ok:
        print("        實得 exit %d；輸出：%s" % (rc, output.strip()))
        failures.append("probe exit code")

    # ------------------------------------------------------------------
    # errexit 迴歸（F5）：GitHub 對沒寫 shell: 的 run: 用 `bash -e {0}`，而
    # `set -uo pipefail` **關不掉**已經生效的 -e（set -<flags> 只開不關）。probe 的
    # 註解宣稱它「無論如何都走完並輸出一個判定」——這條測試驗那句話是不是真的。
    #
    # 為什麼不是文字比對 `set +e` 在不在：文字比對會被「有 set +e 但位置錯了」
    # （例如寫在腳本最後一行、或寫在某個 if 分支裡）整個繞過，那種寫法在文字上看起來
    # 已經修好，行為上完全沒修。所以這裡改成注入一行必然失敗的裸命令——模擬下一個人
    # 照著註解在這裡加的那一行（`git rev-parse --verify "$SHA"` 之類）——再斷言判定
    # 仍然有被寫進 $GITHUB_OUTPUT。用 `false` 而不用真的 git 指令，是因為它零相依且
    # 回傳值確定；受測的是 errexit，不是哪一個命令。
    #
    # 輸入刻意選「普通開發者 commit」：這個方向才是危險的那一邊——腳本若中途死掉，
    # gate 非 0、四道關卡全被 skip，而 skipped 對 required status check 視同通過。
    #
    # **兩個注入點，都與 `set` 的位置無關**（M-6）：判定邏輯的第一個敘述之前、以及最後
    # 一個敘述之前。前者抓「set +e 排在判定邏輯後面」（reviewer 的 V2，舊版對它全綠），
    # 後者抓「中途把 errexit 重新打開」。
    for label, inject in (
        ("判定邏輯的第一個敘述之前", inject_before_first_statement),
        ("最後一個敘述之前", inject_before_last_statement),
    ):
        injected = inject(script, "false  # 注入：模擬未來加進來的一行裸命令")
        got, output, rc = run_probe(
            injected, event_name="push", push_message="功能(rbac): 新增權限矩陣"
        )
        checks += 1
        ok = got == "false" and rc == 0
        print("%s 在%s注入一行必然失敗的裸命令後，probe 仍走完並輸出 is_sync=false"
              "（bash -e 下必須有 set +e，且它必須排在判定邏輯之前）"
              % ("[通過]" if ok else "[失敗]", label))
        if not ok:
            print("        期望 is_sync='false' 且 exit 0，實得 is_sync=%r、exit %d" % (got, rc))
            print("        這條在防：probe 因非預期的非 0 回傳值中途中止 → gate 非 0 →"
                  " 四道關卡全被 skip → 而 skipped 對 required status check 視同通過")
            if output.strip():
                print("        腳本輸出：%s" % output.strip().replace("\n", "\n        "))
            failures.append("errexit 迴歸（注入裸命令：%s）" % label)

    print("")
    print("%d 項行為測試，%d 失敗。" % (checks, len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
