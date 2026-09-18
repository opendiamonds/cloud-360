#!/usr/bin/env python3
"""把 AI-DLC 的 user stories 推送到 GitHub Issues（ADR-0012 階段 1）。

單向：repo → Issues。每個 `## US-n` 對應一則 issue，內容寫在 issue 內文的
**受管區塊**內；區塊之外的內容是協作者寫的，本腳本永不觸碰。

    python3 scripts/aidlc_sync_push.py --intent <slug> --dry-run
    python3 scripts/aidlc_sync_push.py --intent <slug>
    python3 scripts/aidlc_sync_push.py --all-intents          # 所有 in-flight intent

隔離約束（ADR-0012 Decision 6）：本檔**不得**讀取或 import `.claude/` 下的
任何東西。它只讀 `aidlc/` 工作區的 artifact 與 GitHub API——那是升級時不會被
覆蓋的區域。移走 `.claude/` 後本腳本仍須能完整執行，這是可驗收的。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPACES = ROOT / "aidlc" / "spaces"

MANAGED_OPEN = "<!-- aidlc:managed intent={intent} story={story} hash={hash} -->"
MANAGED_OPEN_RE = re.compile(
    r"<!--\s*aidlc:managed\s+intent=(?P<intent>\S+)\s+story=(?P<story>\S+)\s+hash=(?P<hash>\w+)\s*-->"
)
MANAGED_CLOSE = "<!-- /aidlc:managed -->"
MANAGED_BLOCK_RE = re.compile(
    r"<!--\s*aidlc:managed\b.*?-->.*?<!--\s*/aidlc:managed\s*-->", re.DOTALL
)

STORY_HEADING = re.compile(r"^##\s+(?P<id>US-\d+)\s+(?P<title>.+?)\s*$")
# unit-of-work.md 的實際形狀（實測）：標題是 `## U1 `slug`（kind）`，而
# unit ↔ story 的對應寫在「單元清單」表格的列裡，例如
#   | U1 | **9 條**（US-1 六、US-2 三） | ... |
# 兩者都要讀：標題給名稱，表格給歸屬。
UNIT_HEADING = re.compile(r"^##\s+(?P<id>U\d+)\s+(?P<title>.+?)\s*$")
UNIT_TABLE_ROW = re.compile(r"^\|\s*(?P<id>U\d+)\s*\|")
STORY_REF = re.compile(r"\bUS-\d+\b")
# 有些單元以 AC 編號而非 US 編號標示歸屬（實測 U2 是
# 「3 條（AC-1.5、AC-1.6…、AC-2.1 的輸出面）」）。AC-<n>.<m> 屬於 US-<n>，
# 這在 stories.md 的編號慣例下成立（US-1 底下是 AC-1.1～AC-1.6）。
# 不做這層推導，U2 會靜默地不出現在任何 issue 的實作單元清單裡。
AC_REF = re.compile(r"\bAC-(\d+)\.\d+")

SYNC_FOOTER = """
---
> 🤖 本區塊由 AI-DLC 自動同步自 `{source}`。
> **區塊內的修改會被下次同步覆蓋**；要改需求請走 AI-DLC 流程。
> 區塊之外的內容不會被觸碰，歡迎在下方補充討論與脈絡。
"""


@dataclass
class Story:
    story_id: str
    title: str
    body: str = ""
    units: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        # issue 標題是純文字欄位，markdown 不會被渲染——`**Revision 1 新增**`
        # 會原樣顯示出星號。實測 US-5 的標題就帶著它。
        title = re.sub(r"(\*\*|__|`)", "", self.title).strip()
        return f"{self.story_id} {title}"

    def managed_block(self, intent: str, source: str) -> tuple[str, str]:
        """回傳 (受管區塊全文, 內容雜湊)。雜湊只涵蓋內容，不含開頭標記本身。"""
        parts = [self.body.strip()]
        if self.units:
            parts.append("## 實作單元\n\n" + "\n".join(f"- [ ] {u}" for u in self.units))
        parts.append(SYNC_FOOTER.format(source=source).strip())
        content = "\n\n".join(parts)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
        opener = MANAGED_OPEN.format(intent=intent, story=self.story_id, hash=digest)
        return f"{opener}\n\n{content}\n\n{MANAGED_CLOSE}", digest


# --- 解析 -------------------------------------------------------------------


def parse_stories(path: Path) -> list[Story]:
    """把 stories.md 切成 Story。整個 `## US-n` 區塊原樣保留。

    刻意不拆解驗收標準的內部結構：AC 的格式由 user-stories stage 決定，
    這裡多做一層轉譯只會在格式演進時悄悄壞掉。原樣搬運永遠正確。
    """
    text = path.read_text(encoding="utf-8")
    stories: list[Story] = []
    current: Story | None = None
    buf: list[str] = []

    for line in text.splitlines():
        m = STORY_HEADING.match(line)
        if m:
            if current:
                current.body = "\n".join(buf).strip()
                stories.append(current)
            current = Story(story_id=m.group("id"), title=m.group("title"))
            buf = []
            continue
        if current is None:
            continue
        # 下一個同級標題（非 US）結束目前 story
        if line.startswith("## ") and not STORY_HEADING.match(line):
            current.body = "\n".join(buf).strip()
            stories.append(current)
            current = None
            buf = []
            continue
        buf.append(line)

    if current:
        current.body = "\n".join(buf).strip()
        stories.append(current)

    return [s for s in stories if s.body]


def parse_units(path: Path) -> dict[str, list[str]]:
    """unit-of-work.md → {story_id: [unit 描述]}。

    檔案不存在時回空 dict——units-generation 尚未執行是正常狀態，
    此時 issue 只有需求沒有實作單元。
    """
    if not path.exists():
        return {}

    lines = path.read_text(encoding="utf-8").splitlines()

    # 第一遍：標題 → 單元名稱
    names: dict[str, str] = {}
    for line in lines:
        m = UNIT_HEADING.match(line)
        if m:
            title = m.group("title").replace("`", "").strip()
            names[m.group("id")] = f"{m.group('id')} {title}"

    # 第二遍：表格列 → 單元歸屬哪些 story
    mapping: dict[str, list[str]] = {}
    for line in lines:
        row = UNIT_TABLE_ROW.match(line)
        if not row:
            continue
        unit_id = row.group("id")
        label = names.get(unit_id, unit_id)
        refs = list(STORY_REF.findall(line))
        refs += [f"US-{n}" for n in AC_REF.findall(line)]
        for story_id in dict.fromkeys(refs):  # 去重且保序
            if label not in mapping.setdefault(story_id, []):
                mapping[story_id].append(label)
    return mapping


# --- GitHub ------------------------------------------------------------------


def gh(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} 失敗：{proc.stderr.strip()}")
    return proc.stdout


def find_issue(summary: str) -> dict | None:
    """以標題精確比對既有 issue。搜尋限定 aidlc 標籤，避開 200+ 筆 digest 噪音。"""
    out = gh(
        "issue", "list", "--label", "aidlc", "--state", "all", "--limit", "200",
        "--json", "number,title,body,state",
    )
    for row in json.loads(out or "[]"):
        if row["title"] == summary:
            return row
    return None


def upsert_issue(story: Story, intent: str, source: str, *, dry_run: bool) -> tuple[str, int | None, str]:
    """建立或更新 issue。回傳 (動作, issue 編號, 雜湊)。"""
    block, digest = story.managed_block(intent, source)
    existing = find_issue(story.summary)

    if existing is None:
        if dry_run:
            return "create", None, digest
        body = block
        out = gh(
            "issue", "create", "--title", story.summary, "--body", body,
            "--label", "aidlc", "--label", f"intent:{intent}", "--label", "user-story",
        )
        number = int(out.strip().rsplit("/", 1)[-1])
        return "created", number, digest

    old_body = existing.get("body") or ""
    if not MANAGED_BLOCK_RE.search(old_body):
        # 受管標記被刪掉了。不自動修復、不覆寫整份內文——那會吃掉人寫的內容。
        return "conflict", existing["number"], digest

    new_body = MANAGED_BLOCK_RE.sub(lambda _: block, old_body, count=1)
    if new_body == old_body:
        return "unchanged", existing["number"], digest
    if dry_run:
        return "update", existing["number"], digest
    gh("issue", "edit", str(existing["number"]), "--body", new_body)
    return "updated", existing["number"], digest


# --- 同步狀態 ----------------------------------------------------------------


def state_path(record: Path) -> Path:
    # 檔名刻意不以 `.aidlc-` 開頭：AI-DLC 出貨的 .gitignore 有
    # `aidlc/spaces/*/intents/*/.aidlc-*`（排除 recovery、hooks-health 等
    # 機器本地暫存），而這個檔**必須**進版控——跨 runner 的雜湊比對靠它。
    return record / "aidlc-sync-state.json"


def load_state(record: Path, intent: str) -> dict:
    p = state_path(record)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"version": 1, "intent": intent, "stories": {}}


def save_state(record: Path, state: dict) -> None:
    state_path(record).write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# --- 主流程 ------------------------------------------------------------------


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
            if all_intents and row.get("status") != "in-flight":
                continue
            out.append((slug, space / "intents" / dirname))
    return out


def sync_record(slug: str, record: Path, *, dry_run: bool) -> int:
    stories_md = record / "inception" / "user-stories" / "stories.md"
    if not stories_md.exists():
        print(f"  {slug}: 尚無 stories.md（user-stories stage 未執行），略過")
        return 0

    units = parse_units(record / "inception" / "units-generation" / "unit-of-work.md")
    stories = parse_stories(stories_md)
    source = stories_md.relative_to(ROOT).as_posix()
    state = load_state(record, slug)
    prefix = "[dry-run] " if dry_run else ""

    print(f"  {slug}: 解析到 {len(stories)} 個 story（{source}）")
    conflicts = 0
    for story in stories:
        story.units = units.get(story.story_id, [])
        recorded = state["stories"].get(story.story_id, {})
        _, digest = story.managed_block(slug, source)

        if recorded.get("content_hash") == digest and recorded.get("issue"):
            print(f"    = {story.story_id} 內容未變（hash {digest}），跳過")
            continue

        action, number, digest = upsert_issue(story, slug, source, dry_run=dry_run)
        if action == "conflict":
            conflicts += 1
            print(f"    ! {story.story_id} #{number} 受管標記已被移除——不覆寫，需人工處理")
            continue
        label = {"create": "將建立", "created": "已建立", "update": "將更新",
                 "updated": "已更新", "unchanged": "無變更"}[action]
        print(f"    {prefix}{label} {story.story_id} #{number or '?'}（hash {digest}）")

        if not dry_run and number:
            state["stories"][story.story_id] = {
                "issue": number,
                "content_hash": digest,
                "summary": story.summary,
            }

    if not dry_run:
        save_state(record, state)
    return conflicts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--intent", help="intent slug（例如 last-login-column）")
    ap.add_argument("--all-intents", action="store_true", help="所有 in-flight intent")
    ap.add_argument("--dry-run", action="store_true", help="只列出將做什麼，不寫入")
    args = ap.parse_args()

    if not args.intent and not args.all_intents:
        raise SystemExit("需要 --intent <slug> 或 --all-intents")

    targets = records_for(args.intent, args.all_intents)
    if not targets:
        raise SystemExit("找不到符合的 intent")

    print(f"同步 {len(targets)} 個 intent{'（dry-run）' if args.dry_run else ''}：")
    conflicts = sum(sync_record(slug, rec, dry_run=args.dry_run) for slug, rec in targets)

    if conflicts:
        print(f"\n⚠️  {conflicts} 則 issue 的受管標記已被移除，未被覆寫。")
        print("   處置：人工確認後補回標記，或以 sync-conflict 標籤開 issue 討論。")
        return 1
    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
