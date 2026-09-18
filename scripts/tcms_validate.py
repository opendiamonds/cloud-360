#!/usr/bin/env python3
"""驗證測試案例的完整性與正確性，在同步進 TCMS 之前。

這是 `tcms-test-cases` stage 的機械驗證層。它只做**可判定**的檢查——欄位在
不在、路徑存不存在、端點對不對得上。語意層面（規格是否真的描述了需求、步驟
是否可執行）由 `/tcms-verify` skill 承擔，工具過了不等於案例是對的。

    python3 scripts/tcms_validate.py --file <manual-test-cases.md>
    python3 scripts/tcms_validate.py --spec <regression.spec.ts>
    python3 scripts/tcms_validate.py --all          # 兩者都驗

四類檢查：

1. **必填欄位與格式** —— 缺段落、步驟表格壞掉、欄數不對。
2. **空洞預期結果** —— 「正常」「成功」這類無法判定的預期；以及整個案例找不到
   任何一個帶具體證據的預期結果。
3. **追溯目標存在** —— 引用的檔案路徑與測試名稱回 repo 核對。指向不存在目標
   的追溯等於沒有追溯。
4. **API/UI 規格比對實作** —— API 端點比對 `openapi.json`（含 method 與 status
   code），UI 路徑比對 `frontend/src/App.tsx` 的路由表。

退出碼 0 = 全數通過；1 = 有 ERROR。WARNING 不影響退出碼但一律列出。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENAPI = ROOT / "openapi.json"
ROUTES_FILE = ROOT / "frontend" / "src" / "App.tsx"
DEFAULT_MANUAL = (
    ROOT
    / "aidlc/spaces/default/intents/260802-last-login-column"
    / "construction/tcms-test-cases/manual-test-cases.md"
)
DEFAULT_SPEC = ROOT / "frontend/tests/e2e/regression.spec.ts"

TESTING_DOC = ROOT / "TESTING.md"
# 後備值：只在 TESTING.md 不存在或標記被刪時使用。正常情況下必要欄位由
# TESTING.md 第 2 節的標記決定——契約寫在文件裡，程式讀它，兩者不會分歧。
_FALLBACK_SECTIONS = ("目的", "受測介面", "前置條件", "測試步驟", "通過條件", "追溯")
REQUIRED_MARKER = re.compile(r"<!--\s*required-sections:\s*(?P<list>[^>]+?)\s*-->")


def required_sections() -> tuple[str, ...]:
    """必要欄位清單，來源是 TESTING.md 的 `required-sections` 標記。

    刻意不把清單寫死在程式裡：欄位定義是給人看的契約，而人會去讀
    TESTING.md。兩邊各存一份的話，改了文件沒改程式（或反過來）不會有任何
    東西發出聲音——這個 repo 已經在別的地方吃過這種虧。
    """
    if not TESTING_DOC.exists():
        return _FALLBACK_SECTIONS
    m = REQUIRED_MARKER.search(TESTING_DOC.read_text(encoding="utf-8"))
    if not m:
        return _FALLBACK_SECTIONS
    names = tuple(n.strip() for n in m.group("list").split(",") if n.strip())
    return names or _FALLBACK_SECTIONS

# 單獨出現時無法判定的預期結果。執行的人看到這些，不知道要比對什麼。
HOLLOW = {
    "正常", "成功", "失敗", "無異常", "正確", "ok", "OK", "通過", "沒問題",
    "如預期", "符合預期", "顯示正常", "運作正常", "無誤", "正確顯示",
}
# 帶具體證據的預期結果會有這些特徵之一。
CONCRETE = re.compile(r"[0-9]|`|「|」|不得|出現|等於|包含|導向|回 |→")

STEP_ROW = re.compile(r"^\|\s*(?P<n>[^|]+?)\s*\|\s*(?P<action>[^|]+?)\s*\|\s*(?P<expect>[^|]+?)\s*\|\s*$")
API_LINE = re.compile(
    r"^-\s*API\s*[:：]\s*`(?P<method>[A-Z]+)\s+(?P<path>[^`]+)`\s*(?:->|→)\s*(?P<status>\d{3})"
)
UI_LINE = re.compile(r"^-\s*UI\s*[:：]\s*`(?P<path>[^`]+)`")
TRACE_PATH = re.compile(r"`(?P<path>(?:backend|frontend|scripts|deploy|aidlc|\.claude)/[^`\s]+?)(?:::(?P<test>[^`]+))?`")


@dataclass
class Finding:
    level: str  # ERROR / WARN
    case: str
    message: str


@dataclass
class Target:
    """一個待驗證的案例（手動或自動化，正規化後長一樣）。"""

    summary: str
    sections: dict[str, str] = field(default_factory=dict)
    steps: list[tuple[str, str]] = field(default_factory=list)
    apis: list[tuple[str, str, str]] = field(default_factory=list)  # method, path, status
    uis: list[str] = field(default_factory=list)
    traces: list[tuple[str, str | None]] = field(default_factory=list)
    story: str = ""
    origin: str = ""


# --- repo 事實來源 -----------------------------------------------------------


def load_api_index() -> dict[str, dict[str, set[str]]]:
    """openapi.json → {path_regex: {method: {status codes}}}"""
    if not OPENAPI.exists():
        return {}
    spec = json.loads(OPENAPI.read_text(encoding="utf-8"))
    index: dict[str, dict[str, set[str]]] = {}
    for path, ops in spec.get("paths", {}).items():
        index[path] = {
            m.upper(): set(op.get("responses", {}).keys()) for m, op in ops.items()
        }
    return index


def load_routes() -> set[str]:
    """App.tsx 的 <Route path="..."> 集合。"""
    if not ROUTES_FILE.exists():
        return set()
    return set(re.findall(r'path="([^"]+)"', ROUTES_FILE.read_text(encoding="utf-8")))


def api_matches(index: dict[str, dict[str, set[str]]], path: str) -> str | None:
    """把案例寫的具體路徑對應回 OpenAPI 的樣板路徑（處理 {param}）。"""
    if path in index:
        return path
    for template in index:
        if "{" not in template:
            continue
        pattern = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", re.escape(template).replace(r"\{", "{").replace(r"\}", "}")) + "$"
        pattern = re.sub(r"\{[^}]+\}", r"[^/]+", pattern)
        if re.match(pattern, path):
            return template
    return None


# --- 解析 --------------------------------------------------------------------


def parse_manual(path: Path) -> list[Target]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from tcms_sync import parse as parse_manual_cases

    targets = []
    for case in parse_manual_cases(path):
        t = Target(summary=case.summary, origin=path.name)
        current = ""
        for line in case.text.splitlines():
            heading = re.match(r"^###\s+(?P<name>.+?)\s*$", line)
            if heading:
                current = re.sub(r"（.*?）", "", heading.group("name")).strip()
                t.sections.setdefault(current, "")
                continue
            if current:
                t.sections[current] += line + "\n"
        _extract_common(t)
        targets.append(t)
    return targets


def parse_spec_file(path: Path) -> list[Target]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from tcms_sync import parse_spec

    targets = []
    for summary, spec in parse_spec(path):
        t = Target(summary=summary, origin=path.name, story=spec.story)
        t.steps = list(spec.steps)
        t.apis = list(getattr(spec, "apis", []))
        t.uis = [p for p, _ in getattr(spec, "uis", [])]
        t.sections = {
            "目的": " ".join(spec.purpose),
            # @note 在自動化案例裡承載的就是背景（這個斷言在防什麼），
            # 渲染進 TCMS 時也是寫成「### 背景」。
            "背景": " ".join(spec.note),
            "前置條件": " ".join(spec.given),
            "通過條件": " ".join(spec.passes),
            "受測介面": "有" if (t.apis or t.uis) else "",
            "測試步驟": "有" if t.steps else "",
            "追溯": path.as_posix(),
        }
        t.traces = [(path.as_posix(), None)]
        targets.append(t)
    return targets


def _extract_common(t: Target) -> None:
    """從已切段的 sections 抽出步驟、API、UI、追溯、story。"""
    for line in t.sections.get("測試步驟", "").splitlines():
        row = STEP_ROW.match(line.strip())
        if not row:
            continue
        n = row.group("n").strip()
        if n in ("#", "") or set(n) <= set("-: "):
            continue  # 表頭與分隔列
        t.steps.append((row.group("action").strip(), row.group("expect").strip()))

    for line in t.sections.get("受測介面", "").splitlines():
        line = line.strip()
        a = API_LINE.match(line)
        if a:
            t.apis.append((a.group("method"), a.group("path"), a.group("status")))
            continue
        u = UI_LINE.match(line)
        if u:
            t.uis.append(u.group("path"))

    trace_text = t.sections.get("追溯", "")
    for m in TRACE_PATH.finditer(trace_text):
        t.traces.append((m.group("path"), m.group("test")))
    story = re.search(r"User story[：:]\s*(?P<id>[A-Za-z0-9]+)", trace_text)
    if story:
        t.story = story.group("id")


# --- 檢查 --------------------------------------------------------------------


def check(targets: list[Target]) -> list[Finding]:
    api_index = load_api_index()
    routes = load_routes()
    sections = required_sections()
    findings: list[Finding] = []

    def err(t: Target, msg: str) -> None:
        findings.append(Finding("ERROR", t.summary, msg))

    def warn(t: Target, msg: str) -> None:
        findings.append(Finding("WARN", t.summary, msg))

    for t in targets:
        # 1. 必填欄位
        for section in sections:
            if not t.sections.get(section, "").strip():
                err(t, f"缺少「{section}」段落或該段落是空的")

        # 條件式必填：回歸案例沒有背景，一年後沒人知道它在防什麼。
        is_regression = "回歸" in t.summary or "回歸" in t.sections.get("目的", "")
        if is_regression and not t.sections.get("背景", "").strip():
            err(
                t,
                "回歸案例必須有「背景」段落——寫出症狀、錯誤訊息逐字、"
                "以及既有自動化層為何沒抓到",
            )

        # 2. 步驟與空洞預期
        if not t.steps:
            err(t, "測試步驟表格沒有任何一列（表頭與分隔列不算）")
        for i, (action, expect) in enumerate(t.steps, 1):
            if not action:
                err(t, f"步驟 {i} 沒有操作")
            if not expect:
                err(t, f"步驟 {i} 沒有預期結果")
            elif expect.strip(" 。.，,、") in HOLLOW:
                err(t, f"步驟 {i} 的預期結果「{expect}」無法判定——要寫出它長什麼樣子")
        if t.steps and not any(CONCRETE.search(e) for _, e in t.steps):
            err(t, "所有步驟的預期結果都沒有具體證據（數字、引號、backtick、「不得」等）")

        # 3. 追溯目標存在
        if not t.traces:
            err(t, "追溯段落沒有任何可核對的檔案路徑")
        for rel, test_name in t.traces:
            target = ROOT / rel
            if not target.exists():
                err(t, f"追溯指向不存在的路徑：{rel}")
                continue
            if test_name:
                content = target.read_text(encoding="utf-8", errors="replace")
                leaf = test_name.split("::")[-1]
                if leaf and leaf not in content:
                    err(t, f"追溯指向 {rel} 中不存在的測試：{leaf}")
        if not t.story:
            warn(t, "追溯沒有標註 User story")

        # 4. API / UI 比對實作
        if not t.apis and not t.uis:
            err(t, "「受測介面」沒有列出任何 API 端點或 UI 路徑")
        for method, path, status in t.apis:
            if not api_index:
                warn(t, "找不到 openapi.json，略過 API 比對")
                break
            matched = api_matches(api_index, path)
            if matched is None:
                err(t, f"API 端點不存在於 openapi.json：{method} {path}")
                continue
            methods = api_index[matched]
            if method not in methods:
                err(t, f"{matched} 不支援 {method}（實際支援：{'、'.join(sorted(methods))}）")
                continue
            if status not in methods[method]:
                # 只警告不阻擋：`raise HTTPException(401)` 與未處理的 500 都不會
                # 出現在 OpenAPI（除非端點顯式寫 responses=），所以「未宣告」多半
                # 代表文件不完整，而不是案例寫錯。硬錯誤留給 path 與 method——
                # 那兩者寫錯就是真的指向了不存在的東西。
                warn(
                    t,
                    f"{method} {matched} 的 OpenAPI 未宣告 {status}"
                    f"（已宣告：{'、'.join(sorted(methods[method]))}）"
                    "；若這確實是實作行為，考慮在端點補上 responses= 宣告",
                )
        for ui in t.uis:
            if not routes:
                warn(t, "找不到前端路由表，略過 UI 比對")
                break
            if ui not in routes:
                err(t, f"UI 路徑不在 App.tsx 的路由表中：{ui}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", type=Path, help="手動案例 markdown")
    parser.add_argument("--spec", type=Path, help="Playwright spec 檔")
    parser.add_argument("--all", action="store_true", help="驗證兩者的預設路徑")
    args = parser.parse_args()

    targets: list[Target] = []
    if args.all:
        targets += parse_manual(DEFAULT_MANUAL)
        targets += parse_spec_file(DEFAULT_SPEC)
    else:
        if args.file:
            targets += parse_manual(args.file)
        if args.spec:
            targets += parse_spec_file(args.spec)
    if not targets:
        raise SystemExit("沒有要驗證的對象。用 --file／--spec／--all 指定。")

    print(f"驗證 {len(targets)} 個案例……\n")
    findings = check(targets)

    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]

    by_case: dict[str, list[Finding]] = {}
    for f in findings:
        by_case.setdefault(f.case, []).append(f)
    for case, items in by_case.items():
        print(f"● {case[:66]}")
        for f in items:
            mark = "✗" if f.level == "ERROR" else "!"
            print(f"    {mark} {f.message}")
        print()

    ok = len(targets) - len({f.case for f in errors})
    print(f"{'─' * 60}")
    print(f"通過 {ok}/{len(targets)}　ERROR {len(errors)}　WARN {len(warns)}")
    if errors:
        print("\n未通過。修正上列 ERROR 後重跑；在修好之前不得同步進 TCMS。")
        return 1
    print("\n機械檢查全數通過。語意正確性仍需 /tcms-verify 的人工審查關卡。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
