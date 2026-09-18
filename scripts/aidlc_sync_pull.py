#!/usr/bin/env python3
"""把 GitHub Issues 的狀態拉回 repo（ADR-0012 階段 2）。

反向：Issues → repo。只拉**狀態**（open/closed、assignee、labels），不碰內容
——內容的真實來源是 repo，這是 ADR-0012 逐欄位切分的另一半。

    python3 scripts/aidlc_sync_pull.py --intent <slug> --dry-run
    python3 scripts/aidlc_sync_pull.py --all-intents

輸出兩個檔案：

- `<record>/github-status.md`   人可讀的狀態鏡像
- `<record>/aidlc-sync-state.json` 的 `last_pulled_state`  機器比對基準

**刻意不寫 `aidlc-state.md`。** 藍圖初稿寫「更新 aidlc-state.md 的狀態欄」，
但那個檔案是 engine-owned（`aidlc-state.ts:575` 明文拒絕外部的生命週期寫入），
且有 `aidlc-state-transition-guard` 與 `aidlc-validate-state` 兩個 hook 守著。
外部寫入等於與引擎搶同一個檔案，遲早不一致。狀態鏡像自己一個檔，誰擁有誰
就寫，不重疊。

隔離約束（ADR-0012 Decision 6）：不讀取、不 import `.claude/` 下任何東西。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPACES = ROOT / "aidlc" / "spaces"

STATUS_HEADER = """# GitHub 狀態鏡像 — {intent}

> 🤖 由 `scripts/aidlc_sync_pull.py` 自動產生，**請勿手動編輯**。
> 狀態的真實來源是 GitHub（ADR-0012：狀態歸 GitHub、內容歸 repo）；
> 要改狀態請在 GitHub 上操作，下次同步會反映過來。
>
> 最後同步：{synced_at}

"""


def gh(*args: str) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} 失敗：{proc.stderr.strip()}")
    return proc.stdout


def fetch_issue(number: int) -> dict:
    out = gh("issue", "view", str(number), "--json",
             "number,title,state,assignees,labels,url")
    row = json.loads(out)
    return {
        "state": row["state"].lower(),
        "assignees": sorted(a["login"] for a in row.get("assignees") or []),
        "labels": sorted(l["name"] for l in row.get("labels") or []),
        "title": row["title"],
        "url": row["url"],
    }


def state_path(record: Path) -> Path:
    return record / "aidlc-sync-state.json"


def status_path(record: Path) -> Path:
    return record / "github-status.md"


def render_status(intent: str, rows: list[tuple[str, dict, dict]], synced_at: str) -> str:
    """rows: [(story_id, sync_entry, live_state)]"""
    out = [STATUS_HEADER.format(intent=intent, synced_at=synced_at)]

    total = len(rows)
    closed = sum(1 for _, _, live in rows if live["state"] == "closed")
    assigned = sum(1 for _, _, live in rows if live["assignees"])
    out.append(f"**{total} 個 story：{closed} 已關閉、{total - closed} 進行中、{assigned} 已指派**\n")

    out.append("| Story | Issue | 狀態 | 指派 | 標籤 |")
    out.append("|---|---|---|---|---|")
    for story_id, entry, live in rows:
        num = entry.get("issue")
        state = "✅ closed" if live["state"] == "closed" else "🔵 open"
        who = "、".join(live["assignees"]) or "—"
        # 三個由同步自己貼的標籤不列，它們對每一列都相同、沒有資訊量
        labels = [l for l in live["labels"]
                  if l not in ("aidlc", "user-story") and not l.startswith("intent:")]
        out.append(f"| {story_id} | [#{num}]({live['url']}) | {state} | {who} | {'、'.join(labels) or '—'} |")

    out.append("")
    out.append("> 標籤欄省略了 `aidlc`、`user-story` 與 `intent:*`——它們由同步機制固定貼上，每一列都相同。")
    return "\n".join(out) + "\n"


def pull_record(slug: str, record: Path, *, dry_run: bool) -> bool:
    """回傳 True 表示有變更。"""
    sp = state_path(record)
    if not sp.exists():
        print(f"  {slug}: 尚未推送過（無 aidlc-sync-state.json），略過")
        return False

    state = json.loads(sp.read_text(encoding="utf-8"))
    stories = state.get("stories", {})
    if not stories:
        print(f"  {slug}: sync-state 內無 story，略過")
        return False

    rows: list[tuple[str, dict, dict]] = []
    changed: list[str] = []

    for story_id in sorted(stories):
        entry = stories[story_id]
        number = entry.get("issue")
        if not number:
            continue
        live = fetch_issue(number)
        rows.append((story_id, entry, live))

        previous = entry.get("last_pulled_state")
        current = {k: live[k] for k in ("state", "assignees", "labels")}
        if previous != current:
            what = []
            if not previous:
                what.append("首次拉取")
            else:
                for field in ("state", "assignees", "labels"):
                    if previous.get(field) != current[field]:
                        what.append(f"{field}: {previous.get(field)} → {current[field]}")
            changed.append(f"{story_id} #{number}（{'；'.join(what)}）")
            entry["last_pulled_state"] = current

    if not changed:
        print(f"  {slug}: {len(rows)} 個 story，狀態皆無變更")
        return False

    print(f"  {slug}: {len(changed)} 項變更")
    for c in changed:
        print(f"    · {c}")

    if dry_run:
        return True

    synced_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status_path(record).write_text(render_status(slug, rows, synced_at), encoding="utf-8")
    state["last_pulled"] = synced_at
    sp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                  encoding="utf-8")
    return True


def records_for(intent: str | None, all_intents: bool) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for space in sorted(SPACES.glob("*")):
        registry = space / "intents" / "intents.json"
        if not registry.exists():
            continue
        rows = json.loads(registry.read_text(encoding="utf-8"))
        rows = rows if isinstance(rows, list) else rows.get("intents", [])
        for row in rows:
            slug, dirname = row.get("slug"), row.get("dirName")
            if not slug or not dirname:
                continue
            if intent and slug != intent:
                continue
            if not intent and not all_intents:
                continue
            out.append((slug, space / "intents" / dirname))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--intent")
    ap.add_argument("--all-intents", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.intent and not args.all_intents:
        raise SystemExit("需要 --intent <slug> 或 --all-intents")

    targets = records_for(args.intent, args.all_intents)
    if not targets:
        raise SystemExit("找不到符合的 intent")

    print(f"拉取 {len(targets)} 個 intent 的狀態{'（dry-run）' if args.dry_run else ''}：")
    any_changed = any(pull_record(s, r, dry_run=args.dry_run) for s, r in targets)

    print()
    if any_changed:
        print("有狀態變更。" + ("（dry-run，未寫入）" if args.dry_run else "已更新 github-status.md 與 sync-state。"))
        # workflow 用這個退出碼決定要不要開 PR
        return 10
    print("無變更，不需開 PR。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
