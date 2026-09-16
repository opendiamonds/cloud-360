#!/usr/bin/env python3
"""列出 GitHub 上待修的 bug，並把選定的一則交給 AI-DLC（ADR-0012 階段 2.5）。

這是 bug 路徑 B（半自動）：**人決定要修哪一個**，工具負責把 issue 的內容
準備成 AI-DLC 能直接吃的形狀，並在 GitHub 上留下「已接受」的痕跡。

    python3 scripts/aidlc_sync_buglist.py                # 列出待修的 bug
    python3 scripts/aidlc_sync_buglist.py --accept 510   # 接受一則，產生啟動指令

「待修」= 帶 `bug` 標籤、open、且尚未帶 `aidlc:accepted`。

為什麼「決定要修」要在 GitHub 留痕跡：那是一個狀態變更，而狀態歸 GitHub
（ADR-0012）。留言與標籤讓看板上的人知道這則 bug 已被接手，不必問。

bug issue 的內文**永遠不被修改** —— 它屬於回報者（ADR-0012 §7.2）。本工具
只留言、只貼標籤。

隔離約束（ADR-0012 Decision 6）：不讀取、不 import `.claude/` 下任何東西。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ACCEPTED_LABEL = "aidlc:accepted"
BUG_DIR = Path("/tmp")


def gh(*args: str) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} 失敗：{proc.stderr.strip()}")
    return proc.stdout


def pending_bugs() -> list[dict]:
    out = gh("issue", "list", "--label", "bug", "--state", "open", "--limit", "100",
             "--json", "number,title,author,createdAt,labels,url")
    rows = json.loads(out or "[]")
    return [r for r in rows
            if ACCEPTED_LABEL not in {l["name"] for l in r.get("labels") or []}]


def show_list() -> int:
    bugs = pending_bugs()
    if not bugs:
        print("目前沒有待修的 bug。")
        print(f"（條件：帶 `bug` 標籤、open、且未帶 `{ACCEPTED_LABEL}`）")
        return 0

    print(f"待修的 bug（{len(bugs)} 則）：\n")
    for b in bugs:
        labels = "、".join(l["name"] for l in b.get("labels") or [] if l["name"] != "bug")
        print(f"  #{b['number']}  {b['title']}")
        print(f"        回報者 {b['author']['login']}  ·  {b['createdAt'][:10]}"
              + (f"  ·  {labels}" if labels else ""))
        print(f"        {b['url']}")
        print()

    print("要處理哪一個，跑：")
    print(f"  python3 scripts/aidlc_sync_buglist.py --accept {bugs[0]['number']}")
    return 0


def accept(number: int) -> int:
    out = gh("issue", "view", str(number), "--json",
             "number,title,body,author,labels,url,state")
    issue = json.loads(out)

    if issue["state"].lower() != "open":
        raise SystemExit(f"#{number} 不是 open 狀態（目前 {issue['state']}），不接受。")
    names = {l["name"] for l in issue.get("labels") or []}
    if ACCEPTED_LABEL in names:
        print(f"#{number} 已經是 {ACCEPTED_LABEL}，無需重複接受。")
        return 0
    if "bug" not in names:
        print(f"⚠️  #{number} 沒有 `bug` 標籤（目前：{'、'.join(sorted(names)) or '無'}）。")
        print("   仍可繼續，但請確認這確實是要走 bugfix scope 的問題。")

    # issue 全文落地，讓 AI-DLC 讀得到完整脈絡而不是被截斷的摘要
    brief = BUG_DIR / f"aidlc-bug-{number}.md"
    brief.write_text(
        f"# Bug #{number}: {issue['title']}\n\n"
        f"- 回報者：{issue['author']['login']}\n"
        f"- 連結：{issue['url']}\n\n"
        f"## 回報內容（原文，未經改寫）\n\n{issue['body'] or '（回報者未填內文）'}\n",
        encoding="utf-8",
    )

    gh("issue", "edit", str(number), "--add-label", ACCEPTED_LABEL)
    gh("issue", "comment", str(number), "--body",
       "已接受，將以 AI-DLC `bugfix` scope 處理。\n\n"
       "修正會以 PR 形式提出並帶 `Closes #%d`，PR 合併後本 issue 自動關閉。\n"
       "本則 issue 的內文不會被機器修改——它屬於回報者。\n\n"
       "<sub>由 `scripts/aidlc_sync_buglist.py` 標記（ADR-0012 階段 2.5）</sub>" % number)

    print(f"✅ 已接受 #{number}：貼上 `{ACCEPTED_LABEL}`、已在 issue 留言")
    print(f"   完整內容：{brief}")
    print()
    print("接著在 Claude Code 執行（複製整行）：")
    print()
    print(f"  /aidlc-bugfix 修復 GitHub issue #{number}：{issue['title']}。"
          f"完整回報內容見 {brief}，請先讀它再開始。")
    print()
    print("流程跑完、開 PR 時記得在 PR 說明帶上：")
    print(f"  Closes #{number}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--accept", type=int, metavar="ISSUE",
                    help="接受一則 bug：留言、貼標籤、產生 AI-DLC 啟動指令")
    args = ap.parse_args()
    return accept(args.accept) if args.accept else show_list()


if __name__ == "__main__":
    sys.exit(main())
