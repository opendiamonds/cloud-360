#!/usr/bin/env python3
"""把 AI-DLC `tcms-test-cases` stage 產出的手動測案同步到 Kiwi TCMS。

輸入是該 stage 的 artifact `manual-test-cases.md`；輸出是 TCMS 上的測試案例。
以案例標題為鍵，可重複執行：已存在的更新、不存在的建立，不會產生重複案例。

    python3 scripts/tcms_sync.py --file <path> --dry-run   # 預覽，不寫入
    python3 scripts/tcms_sync.py --file <path>             # 實際寫入

兩種案例的來源不同，因此有兩個模式，不可混用：

    --file <manual-test-cases.md>   手動案例。TCMS 是主檔，本工具建立＋更新。
    --spec <regression.spec.ts>     自動化案例。**repo 的 spec code 是主檔**，
                                    案例本身由 kiwitcms-junit.xml-plugin 從測試
                                    結果建立；本工具只把 code 旁的規格註解渲染
                                    成描述寫回去，不建立案例、不碰 is_automated。

這個分工來自 operation/test-case-management-plan.md 的「每種測案有單一真實來源」：
把自動化案例的步驟手抄進 TCMS 會變成兩份維護，而被改的永遠是 code 那份。

前置：
    pip install tcms-api
    ~/.tcms.conf：
        [tcms]
        url = https://tcms.danniel.cc/xml-rpc/
        username = <帳號>
        password = <密碼>

格式契約見 `aidlc/spaces/<space>/knowledge/aidlc-quality-agent/test-case-authoring.md`。
本檔的解析器與該文件的「解析規則」一節必須一致；改其一就要改另一個。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PRODUCT_NAME = "Cloud-360"
TAG = "Cloud-360"
DEFAULT_PRIORITY = "P2"

CASE_HEADING = re.compile(r"^##\s+TC:\s*(?P<summary>.+?)\s*$")
META_LINE = re.compile(r"^-\s*(?P<key>plan|priority)\s*:\s*(?P<value>.+?)\s*$")
SECTION_HEADING = re.compile(r"^###\s+")


@dataclass
class Case:
    summary: str
    plan: str | None = None
    priority: str = DEFAULT_PRIORITY
    body_lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.body_lines).strip()


def parse(path: Path) -> list[Case]:
    """把 manual-test-cases.md 解析成案例清單。

    格式錯誤一律當場報錯而不是跳過：一個沒被解析到的案例，在 TCMS 上看起來
    就跟「沒寫過」一模一樣，而這正是本工具要防的失敗模式。
    """
    cases: list[Case] = []
    current: Case | None = None
    in_body = False

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        heading = CASE_HEADING.match(raw)
        if heading:
            current = Case(summary=heading.group("summary"))
            cases.append(current)
            in_body = False
            continue

        if current is None:
            continue  # 第一個案例標題之前的內容（檔案標題、前言）不屬於任何案例

        if SECTION_HEADING.match(raw):
            in_body = True

        if not in_body:
            meta = META_LINE.match(raw)
            if meta:
                key, value = meta.group("key"), meta.group("value")
                if key == "plan":
                    current.plan = value
                else:
                    if value not in ("P1", "P2", "P3"):
                        raise SystemExit(
                            f"{path}:{lineno}: priority 必須是 P1／P2／P3，得到 {value!r}"
                        )
                    current.priority = value
                continue
            if raw.strip():
                raise SystemExit(
                    f"{path}:{lineno}: 案例 {current.summary!r} 的標題與第一個 '###' 之間"
                    f"只能有 '- plan:' 與 '- priority:'，得到 {raw.strip()!r}"
                )
            continue

        current.body_lines.append(raw)

    problems = []
    for case in cases:
        if not case.text:
            problems.append(f"  案例 {case.summary!r} 沒有任何內容段落（缺 '###' 小節）")
        if not case.plan:
            problems.append(f"  案例 {case.summary!r} 缺 '- plan:'")
    if problems:
        raise SystemExit(f"{path} 格式有誤：\n" + "\n".join(problems))

    seen: dict[str, int] = {}
    for case in cases:
        seen[case.summary] = seen.get(case.summary, 0) + 1
    duplicates = [s for s, n in seen.items() if n > 1]
    if duplicates:
        raise SystemExit(
            "案例標題重複（標題是同步鍵，重複會讓其中一個覆寫另一個）：\n  "
            + "\n  ".join(duplicates)
        )

    return cases


# --- 自動化案例：規格來源是 spec 檔的註解，不是 TCMS ------------------------

DESCRIBE_LINE = re.compile(r"^test\.describe\(\s*'(?P<name>[^']+)'")
TEST_LINE = re.compile(r"^\s*test\(\s*'(?P<name>[^']+)'")
DOC_OPEN = re.compile(r"^\s*/\*\*\s*$")
DOC_CLOSE = re.compile(r"^\s*\*/\s*$")
DOC_TAG = re.compile(
    r"^\s*\*\s*@(?P<tag>purpose|given|step|pass|story|note|api|ui)\s*(?P<value>.*)$"
)
# @api POST /api/auth/login -> 200 | 說明
SPEC_API = re.compile(
    r"^(?P<method>[A-Z]+)\s+(?P<path>\S+)\s*(?:->|→)\s*(?P<status>\d{3})\s*(?:\|\s*(?P<note>.*))?$"
)
DOC_CONT = re.compile(r"^\s*\*\s?(?P<value>.*)$")

AUTOMATED_BANNER = (
    "> ⚠️ **本內容由 `{source}` 的規格註解自動產生，請勿在 TCMS 手動編輯。**\n"
    "> 這是**自動化**案例——執行主體是該檔的 Playwright test，由 `ui-regression`\n"
    "> workflow 在每個 PR 對短生命週期 stack 執行。要修改規格，請改 code 旁的\n"
    "> 註解後重新同步；在 TCMS 這邊改的內容會在下次同步時被覆蓋。\n"
)


@dataclass
class SpecCase:
    summary: str
    purpose: list[str] = field(default_factory=list)
    given: list[str] = field(default_factory=list)
    steps: list[tuple[str, str]] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    story: str = ""
    note: list[str] = field(default_factory=list)
    apis: list[tuple[str, str, str]] = field(default_factory=list)  # method, path, status
    api_notes: list[str] = field(default_factory=list)
    uis: list[tuple[str, str]] = field(default_factory=list)  # path, 關鍵元素

    def render(self, source: str, describe: str, test_name: str) -> str:
        out = [AUTOMATED_BANNER.format(source=source).rstrip(), ""]
        if self.purpose:
            out += ["### 目的", "", " ".join(self.purpose), ""]
        if self.apis or self.uis:
            out += ["### 受測介面", ""]
            for (method, path, status), note in zip(
                self.apis, self.api_notes + [""] * len(self.apis)
            ):
                suffix = f" — {note}" if note else ""
                out += [f"- API: `{method} {path}` → {status}{suffix}"]
            for path, elements in self.uis:
                suffix = f" — {elements}" if elements else ""
                out += [f"- UI: `{path}`{suffix}"]
            out += [""]
        if self.given:
            out += ["### 前置條件", "", " ".join(self.given), ""]
        if self.steps:
            out += ["### 測試步驟", "", "| # | 操作 | 預期結果 |", "|---|---|---|"]
            out += [f"| {i} | {a} | {e} |" for i, (a, e) in enumerate(self.steps, 1)]
            out += [""]
        if self.passes:
            out += ["### 通過條件", "", " ".join(self.passes), ""]
        if self.note:
            # 渲染成「背景」而非「備註」：@note 承載的正是「這個斷言為何長這樣、
            # 它在防哪個具體的錯誤實作」，與手動案例的「背景」是同一個角色。兩邊
            # 用同一個段落名，回歸案例的背景才驗得到。
            out += ["### 背景", "", " ".join(self.note), ""]
        out += [
            "### 追溯",
            "",
            f"- 自動化腳本：`{source}`",
            f"- 測試路徑：`{describe}` › `{test_name}`",
            f"- User story：{self.story or '（未標註）'}",
            "- 執行：`ui-regression` workflow（每個 PR，對短生命週期 stack）",
        ]
        return "\n".join(out).strip()


def parse_spec(path: Path) -> list[tuple[str, SpecCase]]:
    """解析 spec 檔，回傳 [(TCMS summary, SpecCase)]。

    TCMS summary 的組法必須與 junit plugin 一致：`<describe> › <test>`。plugin
    以 `--summary-template '${name}'` 產生案例名稱，改動任一邊都會讓既有案例
    變成孤兒。
    """
    source = path.as_posix()
    describe = ""
    pending: SpecCase | None = None
    current_tag = ""
    found: list[tuple[str, SpecCase]] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        d = DESCRIBE_LINE.match(raw)
        if d:
            describe = d.group("name")
            continue

        if DOC_OPEN.match(raw):
            pending = SpecCase(summary="")
            current_tag = ""
            continue

        if pending is not None and DOC_CLOSE.match(raw):
            current_tag = ""
            continue

        if pending is not None:
            tag = DOC_TAG.match(raw)
            if tag:
                current_tag = tag.group("tag")
                value = tag.group("value").strip()
                if current_tag == "step":
                    action, _, expected = value.partition("|")
                    pending.steps.append((action.strip(), expected.strip()))
                elif current_tag == "api":
                    m = SPEC_API.match(value)
                    if not m:
                        raise SystemExit(
                            f"@api 格式錯誤：{value!r}\n"
                            "正確格式：@api POST /api/auth/login -> 200 | 說明"
                        )
                    pending.apis.append((m.group("method"), m.group("path"), m.group("status")))
                    pending.api_notes.append((m.group("note") or "").strip())
                elif current_tag == "ui":
                    path, _, elements = value.partition("|")
                    pending.uis.append((path.strip(), elements.strip()))
                elif current_tag == "story":
                    pending.story = value
                elif current_tag == "purpose":
                    pending.purpose.append(value)
                elif current_tag == "given":
                    pending.given.append(value)
                elif current_tag == "pass":
                    pending.passes.append(value)
                elif current_tag == "note":
                    pending.note.append(value)
                continue
            cont = DOC_CONT.match(raw)
            if cont and current_tag:
                value = cont.group("value").strip()
                if value:
                    if current_tag == "step" and pending.steps:
                        action, expected = pending.steps[-1]
                        pending.steps[-1] = (action, f"{expected} {value}".strip())
                    elif current_tag == "purpose":
                        pending.purpose.append(value)
                    elif current_tag == "given":
                        pending.given.append(value)
                    elif current_tag == "pass":
                        pending.passes.append(value)
                    elif current_tag == "note":
                        pending.note.append(value)
                continue

        t = TEST_LINE.match(raw)
        if t and pending is not None:
            test_name = t.group("name")
            summary = f"{describe} › {test_name}"
            pending.summary = summary
            found.append((summary, pending))
            # render 需要 describe/test 名稱，先存起來供 sync 使用
            pending.__dict__["_source"] = source
            pending.__dict__["_describe"] = describe
            pending.__dict__["_test"] = test_name
            pending = None
            current_tag = ""

    return found


def sync_automated(specs: list[tuple[str, SpecCase]], *, dry_run: bool) -> int:
    """把規格註解寫進**既有**的自動化案例。

    只更新、不建立：自動化案例是 junit plugin 從測試結果建立的，由本工具建立
    會製造出永遠不會有執行結果的孤兒。找不到對應案例時明確列出——通常表示該
    測試還沒在 CI 跑過一次。
    """
    rpc = connect()
    prefix = "[dry-run] " if dry_run else ""

    products = rpc.Product.filter({"name": PRODUCT_NAME})
    if not products:
        raise SystemExit(f"TCMS 上找不到 Product {PRODUCT_NAME!r}")
    pid = products[0]["id"]
    existing = {c["summary"]: c for c in rpc.TestCase.filter({"category__product": pid})}

    updated, missing = 0, []
    for summary, spec in specs:
        found = existing.get(summary)
        if not found:
            missing.append(summary)
            continue
        text = spec.render(
            spec.__dict__["_source"], spec.__dict__["_describe"], spec.__dict__["_test"]
        )
        if dry_run:
            print(f"{prefix}case     將更新 TC-{found['id']} ({len(text)} 字元) {summary[:44]}")
        else:
            # 只寫 text：is_automated 與 case_status 由 junit plugin 維護，
            # 這裡不碰，避免兩個寫入者互相打架。
            rpc.TestCase.update(found["id"], {"text": text})
            print(f"case     已更新 TC-{found['id']} ({len(text)} 字元) {summary[:44]}")
        updated += 1

    print()
    print(f"{prefix}完成：更新 {updated} 筆，共 {len(specs)} 個規格註解")
    if missing:
        print(f"\n⚠️  TCMS 上找不到對應案例（{len(missing)} 筆）——該測試可能還沒在 CI 跑過：")
        for m in missing:
            print(f"  - {m}")
    return 0


def connect():
    """建立 TCMS 連線。缺設定檔時明確失敗，不靜默跳過。"""
    conf = Path.home() / ".tcms.conf"
    if not conf.exists():
        raise SystemExit(
            f"找不到 {conf}。同步不會被靜默跳過——請先建立設定檔：\n\n"
            "    umask 077\n"
            "    read -p 'TCMS 帳號: ' U && read -s -p 'TCMS 密碼: ' P && echo && \\\n"
            "    printf '[tcms]\\nurl = https://tcms.danniel.cc/xml-rpc/\\n"
            "username = %s\\npassword = %s\\n' \"$U\" \"$P\" > ~/.tcms.conf && \\\n"
            "    unset U P\n"
        )
    try:
        from tcms_api import TCMS
    except ImportError:
        raise SystemExit("缺少 tcms-api 套件。安裝：pip install tcms-api") from None
    return TCMS().exec


def sync(cases: list[Case], *, dry_run: bool) -> int:
    rpc = connect()
    prefix = "[dry-run] " if dry_run else ""

    products = rpc.Product.filter({"name": PRODUCT_NAME})
    if not products:
        raise SystemExit(f"TCMS 上找不到 Product {PRODUCT_NAME!r}")
    pid = products[0]["id"]

    versions = rpc.Version.filter({"product": pid})
    if not versions:
        raise SystemExit(f"Product {PRODUCT_NAME!r} 沒有任何 Version")
    version = versions[0]

    categories = rpc.Category.filter({"product": pid})
    if not categories:
        raise SystemExit(f"Product {PRODUCT_NAME!r} 沒有任何 Category")
    category = categories[0]

    priorities = {p["value"]: p["id"] for p in rpc.Priority.filter({})}
    statuses = rpc.TestCaseStatus.filter({})
    confirmed = next((s for s in statuses if s.get("is_confirmed")), statuses[0])
    plan_types = rpc.PlanType.filter({})
    plan_type = next(
        (t for t in plan_types if t["name"].lower() in ("function", "functional", "manual")),
        plan_types[0],
    )

    # --- TestPlan：需要哪些就建哪些 ---
    wanted_plans = sorted({c.plan for c in cases if c.plan})
    existing_plans = {p["name"]: p["id"] for p in rpc.TestPlan.filter({"product": pid})}
    plan_ids: dict[str, int | None] = {}
    for name in wanted_plans:
        if name in existing_plans:
            plan_ids[name] = existing_plans[name]
            print(f"{prefix}plan     已存在 {name} (id={existing_plans[name]})")
        elif dry_run:
            plan_ids[name] = None
            print(f"{prefix}plan     將建立 {name}")
        else:
            created = rpc.TestPlan.create(
                {
                    "name": name,
                    "product": pid,
                    "product_version": version["id"],
                    "type": plan_type["id"],
                    "is_active": True,
                }
            )
            plan_ids[name] = created["id"]
            print(f"plan     已建立 {name} (id={created['id']})")

    # --- TestCase ---
    existing_cases = {
        c["summary"]: c for c in rpc.TestCase.filter({"category__product": pid})
    }
    created_n = updated_n = 0

    for case in cases:
        payload = {
            "summary": case.summary,
            "category": category["id"],
            "priority": priorities.get(case.priority, priorities[DEFAULT_PRIORITY]),
            "case_status": confirmed["id"],
            # 手動案例必須是 False，才與 junit plugin 回寫的自動化案例區分得開。
            "is_automated": False,
            "text": case.text,
            "notes": "手動測案，來源為 AI-DLC tcms-test-cases stage 的 manual-test-cases.md。",
        }
        found = existing_cases.get(case.summary)

        if dry_run:
            verb = "將更新" if found else "將建立"
            print(f"{prefix}case     {verb} [{case.priority}] {case.summary[:56]}")
            created_n += 0 if found else 1
            updated_n += 1 if found else 0
            continue

        if found:
            rpc.TestCase.update(found["id"], payload)
            case_id = found["id"]
            updated_n += 1
            print(f"case     已更新 id={case_id} {case.summary[:50]}")
        else:
            case_id = rpc.TestCase.create(payload)["id"]
            created_n += 1
            print(f"case     已建立 id={case_id} {case.summary[:50]}")

        rpc.TestCase.add_tag(case_id, TAG)
        plan_id = plan_ids.get(case.plan or "")
        if plan_id:
            try:
                rpc.TestPlan.add_case(plan_id, case_id)
            except Exception as exc:  # 已在計畫內時 API 會報錯，視為冪等成功
                if "already" not in str(exc).lower():
                    print(f"    ! 加入計畫失敗 case={case_id} plan={plan_id}: {exc}")

    print()
    print(f"{prefix}完成：新增 {created_n} 筆，更新 {updated_n} 筆，共 {len(cases)} 筆")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--file",
        type=Path,
        help="manual-test-cases.md 的路徑（手動案例；tcms-test-cases stage 的 artifact）",
    )
    source.add_argument(
        "--spec",
        type=Path,
        help="Playwright spec 檔的路徑（自動化案例；讀取其規格註解，只更新既有案例）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只列出將要建立／更新的內容，不寫入",
    )
    args = parser.parse_args()

    if args.spec:
        if not args.spec.exists():
            raise SystemExit(f"找不到檔案：{args.spec}")
        specs = parse_spec(args.spec)
        if not specs:
            raise SystemExit(
                f"{args.spec} 沒有解析到任何規格註解。"
                "每個 test 前需要一個含 @purpose／@step 等標記的 /** */ 區塊。"
            )
        print(f"解析到 {len(specs)} 個規格註解：")
        for summary, spec in specs:
            print(f"  {summary[:62]}")
            print(f"        步驟 {len(spec.steps)} 個，story={spec.story or '（未標註）'}")
        print()
        return sync_automated(specs, dry_run=args.dry_run)

    if not args.file.exists():
        raise SystemExit(f"找不到檔案：{args.file}")

    cases = parse(args.file)
    if not cases:
        raise SystemExit(f"{args.file} 沒有解析到任何案例（案例標題格式為 '## TC: <標題>'）")

    print(f"解析到 {len(cases)} 個案例：")
    for case in cases:
        print(f"  [{case.priority}] {case.summary}")
        print(f"        plan={case.plan}  text={len(case.text)} 字元")
    print()

    return sync(cases, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
