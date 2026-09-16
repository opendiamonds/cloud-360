#!/usr/bin/env python3
"""fixture 斷言 runner — U-2「受管區塊渲染與雜湊」composite action。

用法：
    python3 .github/actions/aidlc-sync-block/run-fixtures.py

非零 exit 表失敗。

這支腳本是 U-2 完成判準（`unit-of-work.md`）的執行器，三條各有具名測試：

    相同輸入產生相同雜湊      → test_completion_1_same_input_same_hash
    格式變更使雜湊改變        → test_completion_2_format_change_changes_hash
    parse 對無標記 body 回 null → test_completion_3_parse_unmarked_body_returns_null

**讀檔的是這支 runner，不是受測邏輯。** block.sh 只從環境變數讀輸入、只往 stdout 寫，
自身零 I/O——與 U-1 的 map.sh 同一形狀，也是 [US:S-10 AC 1] 的 fixture 驅動前提。

fixture 分兩類，刻意用不同的承載方式：

  fixtures/golden-*.md   **快照**。render 的輸出，逐位元比對（R-4.1）。要更新它們
                         必須是一次刻意的動作，指令逐字記在下方 GOLDEN_CASES 的註解。
  fixtures/body-*.md     **輸入**。parse 要吃的 issue body，人可讀、可手工編輯。

render 的**輸入**（Decision ＋ Context 的值）不放檔案而寫在本檔的常數裡：它們是短的
單行值，放進檔案只會讓「這個 golden 是用什麼輸入產生的」變成要跨兩個檔案才回答得出來
的問題。
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import itertools
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BLOCK_SH = HERE / "block.sh"
FIXTURES = HERE / "fixtures"
MIGRATIONS = HERE / "format-migrations.md"

# block.sh 以 bash 3.2（macOS 內建）可執行為底線，實際跑在 GitHub runner 的 bash 5 上。
# 設 AIDLC_BLOCK_BASH 可指定直譯器，用來在同一台機器上覆驗兩個版本。
BASH = os.environ.get("AIDLC_BLOCK_BASH", "bash")

# Block 的七欄，順序逐字沿用 domain-entities.md 的 `Block` 表。序列化的欄序與這裡
# 相同——要核對「雜湊涵蓋範圍有沒有漏欄位」時把兩份並排即可。
BLOCK_FIELDS = (
    "format_version",
    "status",
    "traceable_row",
    "reason_category",
    "decided_at",
    "scope_note",
    "rejection_closed_at",
)

# render 的輸入鍵（Decision 的三欄 ＋ Context 的三欄）。
RENDER_KEYS = (
    "status",
    "traceable_row",
    "reason_code",
    "scope_note",
    "decided_at",
    "rejection_closed_at",
)

_FAILURES: list[str] = []
_CHECKS = 0


# --------------------------------------------------------------------------
# 驅動
# --------------------------------------------------------------------------
def run_block(op: str, **kw: str) -> subprocess.CompletedProcess:
    """呼叫 block.sh。kw 的鍵直接對應 AIDLC_<大寫> 環境變數。"""
    env = dict(os.environ)
    # 清掉可能從外層漏進來的同名變數，讓每次呼叫的輸入面完全由 kw 決定。
    for key in list(env):
        if key.startswith("AIDLC_"):
            del env[key]
    env.pop("GITHUB_OUTPUT", None)  # 測試只讀 stdout，不寫 runner 的 output 檔
    for key, value in kw.items():
        env["AIDLC_" + key.upper()] = value
    return subprocess.run(
        [BASH, str(BLOCK_SH), op],
        env=env,
        capture_output=True,
    )


def render_bytes(**kw: str) -> bytes:
    """render 的 stdout（原始位元組，不解碼——golden 是逐位元比對）。"""
    filled = {key: kw.get(key, "") for key in RENDER_KEYS}
    proc = run_block("render", **filled)
    if proc.returncode != 0:
        raise AssertionError(
            f"render 以非零 exit 結束（{proc.returncode}）：{proc.stderr.decode()}"
        )
    return proc.stdout


def render(**kw: str) -> str:
    return render_bytes(**kw).decode("utf-8")


def render_expect_failure(**kw: str) -> subprocess.CompletedProcess:
    filled = {key: kw.get(key, "") for key in RENDER_KEYS}
    return run_block("render", **filled)


def parse(issue_body: str) -> dict[str, str]:
    proc = run_block("parse", issue_body=issue_body)
    if proc.returncode != 0:
        raise AssertionError(
            "parse 以非零 exit 結束，但本單元對『讀不出來』的表達方式只有 found=false，"
            f"不得設 exit code。stderr: {proc.stderr.decode()}"
        )
    out: dict[str, str] = {}
    for line in proc.stdout.decode("utf-8").split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            out[key] = value
    return out


def parsed_block(issue_body: str) -> dict[str, str]:
    """把 parse 的 output 收斂成 Block 七欄（去掉 block_ 前綴）。"""
    out = parse(issue_body)
    return {field: out["block_" + field] for field in BLOCK_FIELDS}


def read_fixture_text_from_action_dir(name: str) -> str:
    """讀 action 目錄下（非 fixtures/）的檔案。serialize-golden.txt 用。"""
    return (BLOCK_SH.parent / name).read_text(encoding="utf-8")


def block_hash(**block: str) -> str:
    filled = {"block_" + key: block.get(key, "") for key in BLOCK_FIELDS}
    proc = run_block("hash", **filled)
    if proc.returncode != 0:
        raise AssertionError(
            f"hash 以非零 exit 結束（{proc.returncode}）：{proc.stderr.decode()}"
        )
    line = proc.stdout.decode("utf-8").strip()
    assert line.startswith("content_hash="), line
    return line[len("content_hash=") :]


def serialize_bytes(env_extra: dict[str, str] | None = None, **block: str) -> bytes:
    filled = {"block_" + key: block.get(key, "") for key in BLOCK_FIELDS}
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("AIDLC_"):
            del env[key]
    env.pop("GITHUB_OUTPUT", None)
    for key, value in filled.items():
        env["AIDLC_" + key.upper()] = value
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [BASH, str(BLOCK_SH), "serialize"], env=env, capture_output=True
    )
    if proc.returncode != 0:
        raise AssertionError(f"serialize 失敗：{proc.stderr.decode()}")
    return proc.stdout


def has_marker(issue_body: str) -> str:
    proc = run_block("has_marker", issue_body=issue_body)
    if proc.returncode != 0:
        raise AssertionError(f"has_marker 失敗：{proc.stderr.decode()}")
    return proc.stdout.decode("utf-8").strip().split("=", 1)[1]


def format_version() -> str:
    proc = subprocess.run(
        [BASH, str(BLOCK_SH), "format_version"], capture_output=True, text=True
    )
    return proc.stdout.strip()


def known_versions() -> list[str]:
    proc = subprocess.run(
        [BASH, str(BLOCK_SH), "known_versions"], capture_output=True, text=True
    )
    return proc.stdout.split()


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def read_fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# --------------------------------------------------------------------------
# derive：Block 由 Decision ＋ Context 推導的**測試側預期值**
# --------------------------------------------------------------------------
# 這是 block.sh 的 derive_block_from_decision 在測試側的對照實作。兩份實作是刻意的：
# 測試若直接呼叫受測程式來算預期值，就只證明了它等於自己。
#
# 規則（domain-entities.md）：status 非空 → reason_category 與 decided_at 皆為 null；
#                             status 為空 → traceable_row 為 null。
def derive(fv: str, **kw: str) -> dict[str, str]:
    status = kw.get("status", "")
    if status:
        return {
            "format_version": fv,
            "status": status,
            "traceable_row": kw.get("traceable_row", ""),
            "reason_category": "",
            "decided_at": "",
            "scope_note": kw.get("scope_note", ""),
            "rejection_closed_at": kw.get("rejection_closed_at", ""),
        }
    return {
        "format_version": fv,
        "status": "",
        "traceable_row": "",
        "reason_category": kw.get("reason_code", ""),
        "decided_at": kw.get("decided_at", ""),
        "scope_note": kw.get("scope_note", ""),
        "rejection_closed_at": kw.get("rejection_closed_at", ""),
    }


# --------------------------------------------------------------------------
# golden 快照的產生輸入
# --------------------------------------------------------------------------
# 要重新產生 golden（改格式時的必要動作，見 format-migrations.md 的第 3 步），在
# .github/actions/aidlc-sync-block/ 底下逐一執行：
#
#   AIDLC_STATUS=... AIDLC_TRACEABLE_ROW=... AIDLC_REASON_CODE=... \
#   AIDLC_SCOPE_NOTE=... AIDLC_DECIDED_AT=... AIDLC_REJECTION_CLOSED_AT=... \
#   bash block.sh render > fixtures/<檔名>
#
# **刻意不提供 --update-golden 旗標**：R-4.1 存在的理由就是讓「改了 render」變成一個
# 必須被看見的動作。一鍵重生會讓它退化成一次 tab 補全。
GOLDEN_CASES = {
    # G1：mapped 支（最常走的一支）。rejection = null。
    "golden-mapped.md": dict(
        status="Ready",
        traceable_row="R-3.6 no-in-scope-stage-touched",
        reason_code="mapped",
        scope_note="skipped-in-scope: none; out-of-scope: none",
        # 刻意傳入非空 decided_at：mapped 支**不得**渲染它（[US-OQ-3] 的「或」）。
        decided_at="2026-08-30T07:00:00Z",
        rejection_closed_at="",
    ),
    # G2：與 G1 **只差 rejection_closed_at 一欄**（R-1.5 的可判定方式）。
    "golden-mapped-with-rejection.md": dict(
        status="Ready",
        traceable_row="R-3.6 no-in-scope-stage-touched",
        reason_code="mapped",
        scope_note="skipped-in-scope: none; out-of-scope: none",
        decided_at="2026-08-30T07:00:00Z",
        rejection_closed_at="2026-08-29T10:11:12Z",
    ),
    # G3：status = null 支。刻意傳入非空 traceable_row：該支**不得**渲染它
    # （Block.traceable_row 在 status 為 null 時是 null）。
    "golden-unmapped.md": dict(
        status="",
        traceable_row="R-3.1 parked",
        reason_code="parked",
        scope_note=(
            "skipped-in-scope: functional-design; "
            "out-of-scope: market-research, team-formation"
        ),
        decided_at="2026-08-30T07:00:00Z",
        rejection_closed_at="",
    ),
}

# R-1.3／R-1.4 的兩段固定說明，**逐字**引自 business-rules.md（不含句末句號——實作
# 為了行文加了句號，這裡斷言的是規則原文為子字串）。
FIXED_NOTE_AUTHORITY = "Status 欄位為權威來源；本 issue 依 OOS-2 不自動關閉，其開／關狀態不表示進度"
FIXED_NOTE_EMPTY_FIELD = "自訂欄位為空的 item 不由本機制維護"


# --------------------------------------------------------------------------
# 斷言
# --------------------------------------------------------------------------
def check(label: str, actual, expected) -> None:
    global _CHECKS
    _CHECKS += 1
    if actual != expected:
        _FAILURES.append(f"{label}\n    expected: {expected!r}\n    actual:   {actual!r}")


def check_not(label: str, actual, forbidden) -> None:
    global _CHECKS
    _CHECKS += 1
    if actual == forbidden:
        _FAILURES.append(f"{label}\n    must NOT be: {forbidden!r}\n    actual:      {actual!r}")


def check_true(label: str, condition: bool, detail: str = "") -> None:
    global _CHECKS
    _CHECKS += 1
    if not condition:
        _FAILURES.append(f"{label}{(chr(10) + '    ' + detail) if detail else ''}")


# ==========================================================================
# U-2 的完成判準三條（[ug:unit-of-work.md]）——各自具名
# ==========================================================================
def test_completion_1_same_input_same_hash() -> None:
    """完成判準 1：相同輸入產生相同雜湊。"""
    block = derive("1", **GOLDEN_CASES["golden-mapped.md"])
    first = block_hash(**block)
    second = block_hash(**block)
    check("完成判準 1：同一個 Block 兩次呼叫得到相同雜湊", first, second)
    check_true(
        "完成判準 1：雜湊為 64 位十六進位",
        len(first) == 64 and all(c in "0123456789abcdef" for c in first),
        f"actual: {first!r}",
    )


def test_completion_2_format_change_changes_hash() -> None:
    """完成判準 2：格式變更使雜湊改變。

    「格式變更」在本設計裡有一個明確的載體：format_version 內嵌於區塊文字且在
    content_hash 涵蓋範圍內（R-2.4）。bump 版本 ⇒ 所有既有 item 的雜湊必然改變——
    這正是 ADR-A6 要求「bump 與重新基準化落在同一個 PR」的原因。
    """
    base = derive("1", **GOLDEN_CASES["golden-mapped.md"])
    bumped = dict(base, format_version="2")
    check_not(
        "完成判準 2：bump format_version 之後雜湊必須改變",
        block_hash(**bumped),
        block_hash(**base),
    )


def test_completion_3_parse_unmarked_body_returns_null() -> None:
    """完成判準 3：parse 對無標記的 issue body 回 null（R-3.1）。"""
    body = read_fixture("body-no-marker.md")
    out = parse(body)
    check("完成判準 3：無標記的 body → found=false", out["found"], "false")
    check("完成判準 3：無標記的 body → has_marker=false", out["has_marker"], "false")
    # 反例：fixture 內有一行長得像受管欄位的 `- **Status**: ...`，但它不在標記內。
    # 若 parse 沒有先定位標記就開始抓欄位，這一行會被讀進來。
    check("R-3.1 反例：不得讀到標記外的欄位行", out["block_status"], "")


# ==========================================================================
# R-1 群：區塊必載內容
# ==========================================================================
def test_r1_1_mapped_branch() -> None:
    """R-1.1 前半支：含目前 Status 與其 traceable_row。"""
    text = render(**GOLDEN_CASES["golden-mapped.md"])
    check_true(
        "R-1.1 mapped 支含 Status",
        "- **Status**: Ready" in text,
        text,
    )
    check_true(
        "R-1.1 mapped 支含 traceable_row",
        "- **對照表列**: R-3.6 no-in-scope-stage-touched" in text,
        text,
    )
    check_true("R-1.1 mapped 支不含未寫入原因", "未寫入 Status 的原因" not in text, text)


def test_r1_1_unmapped_branch() -> None:
    """R-1.1 後半支：含機制決定不寫的原因類別與 ISO 8601 時間戳。"""
    text = render(**GOLDEN_CASES["golden-unmapped.md"])
    check_true("R-1.1 不寫支含原因類別", "- **未寫入 Status 的原因**: parked" in text, text)
    check_true("R-1.1 不寫支含時間戳", "- **判定時間**: 2026-08-30T07:00:00Z" in text, text)
    check_true("R-1.1 不寫支不含 Status 行", "- **Status**: " not in text, text)
    # Block.traceable_row 在 status 為 null 時是 null（domain-entities.md），故即使
    # 呼叫端傳了非空的 traceable_row（本 fixture 傳的是 "R-3.1 parked"），也不渲染。
    check_true("R-1.1 不寫支不渲染 traceable_row", "R-3.1 parked" not in text, text)


def test_decided_at_only_in_null_status_branch() -> None:
    """[US-OQ-3] 的「或」：decided_at 只掛在「決定不寫」那一支。

    這是 functional-design iteration 4 的 Critical（C-3）：先前 Block.decided_at 宣告
    為非空，但 render 只在 status = null 的分支輸出它，於是**最常走的 mapped 分支上
    parse 取不回來**，型別與行為直接矛盾。值域已改為 `ISO 8601 | null`。
    """
    case = GOLDEN_CASES["golden-mapped.md"]
    text = render(**case)
    check_true(
        "mapped 支不得渲染 decided_at（即使呼叫端傳了值）",
        case["decided_at"] not in text,
        text,
    )
    block = parsed_block(text)
    check("mapped 支 parse 回來的 decided_at 為 null", block["decided_at"], "")
    # 附帶收益（domain-entities.md 明記）：mapped 支的 Block 不含隨輪變動的時間戳，
    # 因此語意相同的兩輪**必得相同雜湊**。這裡把它變成可執行的證據。
    later = dict(case, decided_at="2026-12-31T23:59:59Z")
    check(
        "mapped 支：只有 decided_at 不同的兩輪得到相同雜湊（churn 隱憂不作用於此支）",
        block_hash(**derive("1", **later)),
        block_hash(**derive("1", **case)),
    )


def test_r1_2_scope_note_difference_is_visible() -> None:
    """R-1.2：兩個只在 scope_note 不同的 Context 產生**可區分**的區塊文字。

    U-1 決定 Status（且 [S]／— SKIP 對 Status 無影響，[req:FR-B3]），U-2 負責讓那個
    差別在別處看得見——兩者合起來才滿足 FR-B3 的兩個要求。
    """
    base = dict(GOLDEN_CASES["golden-mapped.md"])
    bracket_s = dict(base, scope_note="skipped-in-scope: functional-design; out-of-scope: none")
    suffix_skip = dict(base, scope_note="skipped-in-scope: none; out-of-scope: functional-design")

    text_s = render(**bracket_s)
    text_skip = render(**suffix_skip)
    check_not("R-1.2 兩種 scope_note 的區塊文字必須可區分", text_s, text_skip)
    check(
        "R-1.2 [S] 類的 scope_note 原樣可讀",
        parsed_block(text_s)["scope_note"],
        bracket_s["scope_note"],
    )
    check(
        "R-1.2 — SKIP 類的 scope_note 原樣可讀",
        parsed_block(text_skip)["scope_note"],
        suffix_skip["scope_note"],
    )
    # 兩者的 Status 相同（U-1 的職責），差別只在區塊裡——這是 FR-B3 的兩個要求。
    check_not(
        "R-1.2 兩者的雜湊必須不同（否則 U-8 看不見這個差別）",
        block_hash(**derive("1", **bracket_s)),
        block_hash(**derive("1", **suffix_skip)),
    )


def test_r1_3_fixed_note_authority_verbatim() -> None:
    """R-1.3：固定說明逐字出現（字串比對）。"""
    for name, case in GOLDEN_CASES.items():
        text = render(**case)
        check_true(f"R-1.3 {name} 含權威來源固定說明（逐字）", FIXED_NOTE_AUTHORITY in text, text)


def test_r1_4_fixed_note_empty_field_verbatim() -> None:
    """R-1.4：固定說明逐字出現（[Q6=A] 的規則落點）。"""
    for name, case in GOLDEN_CASES.items():
        text = render(**case)
        check_true(f"R-1.4 {name} 含空欄位固定說明（逐字）", FIXED_NOTE_EMPTY_FIELD in text, text)


def test_r1_5_rejection_notice() -> None:
    """R-1.5：rejection_notice 非 null 時額外載明「該次人工改動未被採納」與其
    closed_at；為 null 時**不渲染該段**。且兩者 parse 回來分別為該值與 null。"""
    without = GOLDEN_CASES["golden-mapped.md"]
    with_notice = GOLDEN_CASES["golden-mapped-with-rejection.md"]
    # 這兩個 case 必須只差一欄，否則本測試證明不了 R-1.5 想證明的東西。
    diff_keys = [k for k in RENDER_KEYS if without[k] != with_notice[k]]
    check("R-1.5 兩個 case 恰只差 rejection_closed_at 一欄", diff_keys, ["rejection_closed_at"])

    text_without = render(**without)
    text_with = render(**with_notice)
    check_not("R-1.5 兩者的區塊文字必須可區分", text_without, text_with)
    check_true(
        "R-1.5 非 null 時載明「該次人工改動未被採納」",
        "該次人工改動未被採納" in text_with,
        text_with,
    )
    check_true(
        "R-1.5 非 null 時載明 closed_at",
        with_notice["rejection_closed_at"] in text_with,
        text_with,
    )
    check_true(
        "R-1.5 為 null 時完全不渲染該段",
        "該次人工改動未被採納" not in text_without,
        text_without,
    )
    check(
        "R-1.5 parse 回來為該值",
        parsed_block(text_with)["rejection_closed_at"],
        with_notice["rejection_closed_at"],
    )
    check("R-1.5 parse 回來為 null", parsed_block(text_without)["rejection_closed_at"], "")
    check_not(
        "R-1.5 告示進雜湊涵蓋範圍（否則 U-8 會把機制自己寫的告示誤讀為人為變更）",
        block_hash(**derive("1", **with_notice)),
        block_hash(**derive("1", **without)),
    )


# ==========================================================================
# R-2 群：雜湊
# ==========================================================================
def test_r2_1_hash_is_sha256_of_the_canonical_serialization() -> None:
    """R-2.1：輸出是 sha256，且輸入是正規化序列化的位元組。

    這裡用 Python 的 hashlib 獨立算一次——若只比對 block.sh 自己算兩次，就只證明了
    它是決定性的，證明不了它算的是 sha256、也證明不了序列化就是雜湊的實際輸入。
    """
    block = derive("1", **GOLDEN_CASES["golden-unmapped.md"])
    raw = serialize_bytes(**block)
    check(
        "R-2.1 content_hash 等於序列化位元組的 sha256",
        block_hash(**block),
        hashlib.sha256(raw).hexdigest(),
    )
    lines = raw.decode("utf-8").split("\n")
    check("R-2.1 序列化以 LF 結尾（最後一段為空）", lines[-1], "")
    check("R-2.1 序列化恰好七行（Block 七欄）", len(lines) - 1, len(BLOCK_FIELDS))
    check(
        "R-2.1 序列化的欄序等於 domain-entities.md 的 Block 表順序",
        [line.split("=", 1)[0] for line in lines[:-1]],
        list(BLOCK_FIELDS),
    )


def test_r2_2_every_field_changes_the_hash() -> None:
    """R-2.2：任一欄位不同必得不同雜湊——**逐欄位**各一個斷言。

    每一對都刻意選成兩個**合法**的 Block（互斥不變式成立），所以 status／traceable_row
    這兩欄用 mapped 支當基準，reason_category／decided_at 用不寫支當基準。
    """
    mapped = derive("1", **GOLDEN_CASES["golden-mapped.md"])
    unmapped = derive("1", **GOLDEN_CASES["golden-unmapped.md"])

    pairs = {
        "format_version": (mapped, dict(mapped, format_version="2")),
        "status": (mapped, dict(mapped, status="Done")),
        "traceable_row": (mapped, dict(mapped, traceable_row="R-3.3 runtime-status-completed")),
        "reason_category": (unmapped, dict(unmapped, reason_category="suppressed")),
        "decided_at": (unmapped, dict(unmapped, decided_at="2026-08-31T00:00:00Z")),
        "scope_note": (
            mapped,
            dict(mapped, scope_note="skipped-in-scope: none; out-of-scope: feasibility"),
        ),
        "rejection_closed_at": (
            mapped,
            dict(mapped, rejection_closed_at="2026-08-29T10:11:12Z"),
        ),
    }
    check("R-2.2 逐欄位斷言覆蓋 Block 的全部七欄", sorted(pairs), sorted(BLOCK_FIELDS))
    for field, (before, after) in pairs.items():
        check_not(
            f"R-2.2 只改 {field} 一欄，雜湊必須不同",
            block_hash(**after),
            block_hash(**before),
        )


def test_r2_3_decided_at_is_in_coverage() -> None:
    """R-2.3：decided_at **在**涵蓋範圍內（[Q2=A]）。

    這一條與 R-2.2 的逐欄位斷言重疊，仍然獨立具名——它是 [Q2=A] 這個人工裁定在程式碼
    裡唯一的可執行痕跡，而突變驗證（把 decided_at 移出序列化）要打的就是這一條。
    """
    base = derive("1", **GOLDEN_CASES["golden-unmapped.md"])
    later = dict(base, decided_at="2026-09-01T12:00:00Z")
    check_not("R-2.3 decided_at 在雜湊涵蓋範圍內", block_hash(**later), block_hash(**base))
    raw = serialize_bytes(**base).decode("utf-8")
    check_true(
        "R-2.3 decided_at 出現在序列化中",
        "decided_at=2026-08-30T07:00:00Z" in raw,
        raw,
    )


def test_r2_4_format_version_is_in_coverage() -> None:
    """R-2.4：format_version 在涵蓋範圍內——它是 Block 的欄位。"""
    raw = serialize_bytes(**derive("1", **GOLDEN_CASES["golden-mapped.md"])).decode("utf-8")
    check_true("R-2.4 format_version 出現在序列化中", raw.startswith("format_version=1\n"), raw)


def test_serialization_is_deterministic_and_locale_independent() -> None:
    """tech-stack-decisions.md 指定的序列化 fixture：同一個 Block 在兩次獨立執行中
    必得**逐位元相同**的序列化字串，且涵蓋它列的三種 bash 特有風險各一例。"""
    tricky = {
        "format_version": "1",
        "status": "",
        "traceable_row": "",
        # 風險 1：欄位值含分隔符（= 與換行的跳脫序列長相）
        "reason_category": "undecidable",
        "decided_at": "2026-08-30T07:00:00Z",
        "scope_note": "skipped-in-scope: a=1, b\\c; out-of-scope: none",
        # 風險 2：尾端空白（$( ) 只吃尾端換行不吃空白，但兩種寫法容易搞混）
        "rejection_closed_at": "2026-08-29T10:11:12Z  ",
    }
    first = serialize_bytes(**tricky)
    second = serialize_bytes(**tricky)
    check("序列化在兩次獨立執行中逐位元相同", first, second)
    check_true(
        "序列化把反斜線跳脫成 \\\\（否則含反斜線的值會與含跳脫序列的值撞在一起）",
        b"b\\\\c" in first,
        first.decode("utf-8"),
    )
    check_true(
        "序列化保留尾端空白（$( ) 只剝尾端換行）",
        first.decode("utf-8").endswith("10:11:12Z  \n"),
        repr(first.decode("utf-8")),
    )
    # 風險 3：locale。block.sh 檔頭 export LC_ALL=C，外層設什麼都不該影響結果。
    other_locale = serialize_bytes(
        env_extra={"LC_ALL": "en_US.UTF-8", "LANG": "en_US.UTF-8", "LC_COLLATE": "de_DE.UTF-8"},
        **tricky,
    )
    check("序列化不受外層 locale 影響", other_locale, first)


# ==========================================================================
# R-3 群：parse 的行為
# ==========================================================================
def test_r3_2_corrupt_version_returns_null() -> None:
    """R-3.2：有標記但版本標記不可解析 → 回 null。"""
    out = parse(read_fixture("body-corrupt-version.md"))
    check("R-3.2 版本不可解析 → found=false", out["found"], "false")
    check("R-3.2 但標記確實存在 → has_marker=true", out["has_marker"], "true")
    check("R-3.2 不得吐出半個 Block", out["block_status"], "")


def test_r3_2_missing_end_marker_returns_null() -> None:
    """R-3.2：有起始標記但區塊被截斷（沒有結束標記）→ 回 null。"""
    out = parse(read_fixture("body-missing-end.md"))
    check("R-3.2 區塊被截斷 → found=false", out["found"], "false")
    check("R-3.2 區塊被截斷但標記存在 → has_marker=true", out["has_marker"], "true")
    check("R-3.2 截斷時不得吐出半個 Block", out["block_status"], "")


def test_r3_3_known_version_parses() -> None:
    """R-3.3：有標記且版本在已知版本集合內 → 套用該版本的解析器，回 Block。"""
    out = parse(read_fixture("golden-mapped.md"))
    check("R-3.3 已知版本 → found=true", out["found"], "true")
    check("R-3.3 取回版本", out["block_format_version"], "1")
    check(
        "R-3.3 取回 Block",
        parsed_block(read_fixture("golden-mapped.md")),
        derive("1", **GOLDEN_CASES["golden-mapped.md"]),
    )


def test_r3_4_future_version_returns_null() -> None:
    """R-3.4：有標記且版本高於當前渲染器 → 回 null（保守：不用舊規則猜新格式）。"""
    out = parse(read_fixture("body-future-version.md"))
    check("R-3.4 未來版本 → found=false", out["found"], "false")
    check("R-3.4 不得用舊解析器猜出欄位", out["block_status"], "")


def test_r3_4_has_marker_distinguishes_absent_from_future() -> None:
    """ADR-0015 §6 修法 (b)：讓呼叫端在 parse 回 null 時能分辨兩種 null。

    這是 functional-design iteration 1 的 Critical：parse 的簽章
    (issue_body) -> Block | null 讓「完全沒有標記」（R-3.1）與「版本較新」（R-3.4）
    回**同一個 null**，於是呼叫端最自然的實作「parse 回 null ⇒ 渲染一個寫進去」
    恰恰是 R-3.4 要防的覆寫。has_managed_marker 是 Plan Approval 裁定採用的修法。

    **本測試證明的是能力，不是保護已生效。** 保護要真正成立，還取決於 U-6 在寫入前
    確實呼叫它並在 true 時跳過——那條斷言的落點在 U-6，不在這裡。
    """
    absent = read_fixture("body-no-marker.md")
    future = read_fixture("body-future-version.md")

    absent_out = parse(absent)
    future_out = parse(future)
    check("兩者的 found 相同（這正是問題所在）", absent_out["found"], future_out["found"])
    check("兩者的 found 都是 false", future_out["found"], "false")
    check_not(
        "但 has_marker 必須把它們分開",
        absent_out["has_marker"],
        future_out["has_marker"],
    )
    check("無標記 → has_marker=false（可以安全渲染）", absent_out["has_marker"], "false")
    check("版本較新 → has_marker=true（不得覆寫）", future_out["has_marker"], "true")

    # 獨立的 operation 也要給同一個答案（U-6 可能只想問這一件事，不想跑完整 parse）。
    check("has_marker operation 與 parse 的 has_marker 一致（無標記）", has_marker(absent), "false")
    check("has_marker operation 與 parse 的 has_marker 一致（未來版本）", has_marker(future), "true")
    # 壞掉的版本標記也算「有人的區塊在這裡」——這正是它刻意不看版本的理由。
    check("has_marker 對壞掉的版本仍回 true", has_marker(read_fixture("body-corrupt-version.md")), "true")


def test_parse_ignores_content_outside_the_markers() -> None:
    """區塊夾在人寫的內容之間（真實 issue 的常態）時仍正確取回，且不吃到區塊外的文字。"""
    body = read_fixture("body-embedded.md")
    check(
        "夾在人寫內容之間的區塊可被正確取回",
        parsed_block(body),
        derive("1", **GOLDEN_CASES["golden-mapped.md"]),
    )
    check(
        "區塊內容與獨立 golden 的 parse 結果相同（前後文不影響）",
        parsed_block(body),
        parsed_block(read_fixture("golden-mapped.md")),
    )


# ==========================================================================
# round-trip（ADR-0015 §10 的雜湊等價不變式在本單元這一段）
# ==========================================================================
def _round_trip_case(args) -> str | None:
    status, traceable_row, reason_code, scope_note, decided_at, rejection = args
    kw = dict(
        status=status,
        traceable_row=traceable_row,
        reason_code=reason_code,
        scope_note=scope_note,
        decided_at=decided_at,
        rejection_closed_at=rejection,
    )
    label = repr(kw)
    try:
        text = render(**kw)
    except AssertionError as exc:
        return f"round-trip：{label} 的 render 失敗\n    {exc}"
    got = parsed_block(text)
    want = derive("1", **kw)
    if got != want:
        return f"round-trip：{label}\n    expected: {want!r}\n    actual:   {got!r}"
    return None


def test_round_trip_render_parse() -> None:
    """render → parse 取回等價的 Block，對含分隔符、前後空白、反斜線的值亦然。

    這是 ADR-0015 §10（render → GitHub → parse 的雜湊等價）在本單元可驗的那一段。
    跨 GitHub 的那一段由 U-9 的端到端驗證承接，本站不冒充。
    """
    statuses = ["", "Ready", "Done"]
    rows = ["", "R-3.6 no-in-scope-stage-touched", "  前後有空白  ", "含 = 與 ; 與 , 的值"]
    reasons = ["mapped", "parked", "undecidable"]
    notes = [
        "skipped-in-scope: none; out-of-scope: none",
        "skipped-in-scope: a, b; out-of-scope: c",
        "含反斜線 \\ 與 = 的 scope_note",
    ]
    stamps = ["", "2026-08-30T07:00:00Z"]
    rejections = ["", "2026-08-29T10:11:12Z"]

    combos = list(itertools.product(statuses, rows, reasons, notes, stamps, rejections))
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(_round_trip_case, combos))

    global _CHECKS
    _CHECKS += len(combos)
    failures = [r for r in results if r is not None]
    if failures:
        _FAILURES.extend(failures[:10])
        if len(failures) > 10:
            _FAILURES.append(f"round-trip：另有 {len(failures) - 10} 筆失敗未列出")
    print(f"  round-trip: {len(combos)} 組組合，失敗 {len(failures)}")


def test_round_trip_hash_equivalence() -> None:
    """hash(derive(x)) == hash(parse(render(x)))。

    這是上一個測試的雜湊面：round-trip 若在任何一欄上有損，兩個雜湊就會永久不相等，
    而後果是「在沒有任何人為變更的情況下，U-8 每天為每個受管 intent 各開一則反向 PR」
    （ADR-0015 §10 逐字）。
    """
    for name, case in GOLDEN_CASES.items():
        text = render(**case)
        check(
            f"{name}：render→parse 之後雜湊不變",
            block_hash(**parsed_block(text)),
            block_hash(**derive("1", **case)),
        )


# ==========================================================================
# R-4 群：格式契約的互鎖（[Q1=C] 定案三道，2026-08-30T12:49:35Z 擴為五道，ADR-A6 指派）
# ==========================================================================
def test_r4_1_golden_snapshots_byte_identical() -> None:
    """R-4.1：golden fixture 快照與當前渲染器輸出**逐位元**一致。

    觸發紅燈的情形：改了 render 而沒更新快照。
    """
    for name, case in GOLDEN_CASES.items():
        check(f"R-4.1 {name} 與當前渲染器輸出逐位元一致", render_bytes(**case), read_fixture_bytes(name))


def _migration_rows() -> tuple[list[str], list[list[str]]]:
    """解析 format-migrations.md 的登錄表。

    **只讀 `## 登錄表` 標題之後**的表格——檔案上半部那張 R-4 對照表也以 `|` 開頭，
    不加這個限制就會讀到它（而且會安靜地讀錯，這正是本檔案格式最容易出的錯）。
    """
    lines = MIGRATIONS.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## 登錄表":
            start = i
            break
    if start is None:
        raise AssertionError("format-migrations.md 找不到 `## 登錄表` 標題")
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue  # markdown 的分隔列
        rows.append(cells)
    if not rows:
        raise AssertionError("format-migrations.md 的登錄表沒有任何資料列")
    return rows[0], rows[1:]


def test_r4_5_golden_fingerprint_matches_registry() -> None:
    """R-4.5：golden 集合的合併指紋等於登錄表最後一列的 `golden_fingerprint`。

    來源：修正 reviewer Critical 時**實測發現的第二個缺口**，2026-08-30T12:32:26Z。

    `format-migrations.md` 對 R-4.2 寫的觸發情形是「更新了快照但沒 bump 版本」，
    **但 R-4.2 機制上做不到**：它只比對「`FORMAT_VERSION` 等於本表最後一列」，
    而「改 render → 更新 golden → 不 bump」這條路徑上**兩者都沒動**，故恆綠。
    實測重現：把 `render_block` 的標題文字改一個字 → `test_r4_1` 紅 → 照著紅燈
    更新 golden → **全部 549 個斷言重新變綠**，`FORMAT_VERSION` 仍是 1、登錄表未動。

    本測試把 golden 集合（三個 `golden-*.md` ＋ `serialize-golden.txt` 的資料列）
    的內容指紋釘進登錄表，使「更新快照」必須連帶更新登錄表；而更新登錄表的最後
    一列又必須讓版本等於 `FORMAT_VERSION`（R-4.2）並附非空說明（R-4.3）。
    **連鎖至此才真的閉合**——這正是 ADR-A6 指派的「機制而非流程紀律」。

    指紋的計算方式與 `format-migrations.md` §「改格式時要做的五件事」第 4 步逐字相同；
    兩處不一致時以本測試為準（它是機械執行的那一份）。

    （撰寫時本測試第一版呼叫了不存在的 `migration_rows()`——實際的 helper 是
    `_migration_rows()` 且回傳 `(header, data)`。憑印象寫 helper 名稱是本 session
    第二次同型失誤，前一次是 U-1 的 `r["slug"]`。）
    """
    import hashlib
    import pathlib

    h = hashlib.sha256()
    for path in sorted((BLOCK_SH.parent / "fixtures").glob("golden-*.md")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    sg = (BLOCK_SH.parent / "serialize-golden.txt").read_text(encoding="utf-8")
    body = "".join(
        line
        for line in sg.split("\n")
        if not line.startswith("<!--") and not line.startswith(" ") and line.strip()
    )
    h.update(body.encode())

    _header, data = _migration_rows()
    recorded = data[-1][2].strip().strip("`")
    check("R-4.5 golden 指紋等於登錄表最後一列所記", h.hexdigest(), recorded)


def test_r4_4_serialization_golden_byte_identical() -> None:
    """R-4.4：`content_hash` 的**實際輸入**（canonical serialization）逐位元鎖住。

    來源：reviewer(code-generation) 的 Critical，2026-08-30T12:29:25Z。

    **R-4.1～R-4.3 只看 `render()` 的 markdown 輸出**，完全沒有涵蓋
    `serialize_block`／`escape_value`——而後者才是 `content_hash` 吃的東西。
    reviewer 實測示範：把 `serialize_block` 的兩個欄位對調（一次真正的雜湊演算法
    變更），三道鎖一道都不紅，`FORMAT_VERSION` 仍是 1、`format-migrations.md`
    未動，而 `golden-mapped.md` 的雜湊從 `2f1712e6…` 變成 `ed2c69b2…`。

    那正是 ADR-A6 點名為**最危險**的失敗模式：全部既有 item 的雜湊一次改變 ⇒
    下一輪反向同步把它們全部誤判為人為變更。

    **為什麼這個表面會被漏掉**：三份 functional-design 文件中 `serialize`／
    `escape` 出現 **0 次**（實測 grep）——它是 code-generation 為了實作
    `content_hash(Block)` 而發明的中介表示，從未被納入 ADR-A6 的紀律。

    本測試把它納入：序列化輸出與其 sha256 一起釘在 `serialize-golden.txt`，
    改動任一欄序、分隔符或跳脫規則都會紅燈。**與 R-4.2／R-4.3 的連動一致**：
    要讓它變綠就得更新 golden，而那是一次刻意的動作，理應同時 bump 版本並補登錄。
    """
    import hashlib

    text = read_fixture_text_from_action_dir("serialize-golden.txt")
    expected = {}
    current_name = None
    for line in text.split("\n"):
        if line.startswith("=== ") and line.endswith(" ==="):
            current_name = line[4:-4]
        elif line.startswith("sha256: ") and current_name:
            expected[current_name] = {"sha256": line[8:].strip()}
        elif current_name and line and not line.startswith("<!--") and not line.startswith(" "):
            if current_name in expected and "raw" not in expected[current_name]:
                expected[current_name]["raw"] = line

    check("R-4.4 golden 涵蓋全部 GOLDEN_CASES", sorted(expected), sorted(GOLDEN_CASES))

    for name in sorted(GOLDEN_CASES):
        block = derive("1", **GOLDEN_CASES[name])
        raw = serialize_bytes(**block)
        check(
            f"R-4.4 {name} 的 canonical serialization 逐位元一致",
            raw.decode("utf-8").replace("\n", "\\n"),
            expected[name]["raw"],
        )
        check(
            f"R-4.4 {name} 的 sha256 未變",
            hashlib.sha256(raw).hexdigest(),
            expected[name]["sha256"],
        )


def test_r4_2_format_version_matches_last_migration_row() -> None:
    """R-4.2：FORMAT_VERSION 等於登錄表最後一列的版本。

    觸發紅燈的情形：更新了快照但沒 bump 版本。
    """
    header, data = _migration_rows()
    check(
        "R-4.2 登錄表的欄位名稱未被改動（互鎖靠欄序解析）",
        header,
        ["format_version", "生效日期", "golden_fingerprint", "變更內容", "重新基準化說明", "執行方式"],
    )
    check_true("R-4.2 登錄表至少有一列", len(data) >= 1, repr(data))
    check("R-4.2 FORMAT_VERSION 等於登錄表最後一列的版本", format_version(), data[-1][0])

    versions = [row[0] for row in data]
    check_true(
        "R-4.2 版本嚴格遞增（append-only，不得插隊或重號）",
        all(int(a) < int(b) for a, b in zip(versions, versions[1:])),
        repr(versions),
    )
    known = known_versions()
    check_true(
        "R-4.2 KNOWN_VERSIONS 沒有幽靈版本（每一個都要在登錄表裡）",
        set(known) <= set(versions),
        f"KNOWN_VERSIONS={known} 登錄表={versions}",
    )
    check(
        "R-4.2 KNOWN_VERSIONS 的最大值等於 FORMAT_VERSION",
        max(known, key=int),
        format_version(),
    )


def test_r4_3_last_row_has_rebaseline_note() -> None:
    """R-4.3：登錄表最後一列含**非空**的重新基準化說明與其執行方式。

    觸發紅燈的情形：bump 了版本但沒加登錄。

    **天花板（誠實記載，不要試圖修掉）**：這一列可以被寫成空殼——填滿說明但不真的
    執行基準化。互鎖保證作者無法「忘記」，**不保證他「做了」**。這是 [Q1=C]
    選項本文即已載明的取捨；唯一能保證「做了」的形狀是 [Q1=B]，但它把 ADR-A6 的
    單一 PR 遷移改成逐 item 惰性遷移，屬對已核可 ADR 的實質變更，已由人裁定不採。
    """
    _, data = _migration_rows()
    last = data[-1]
    check_true("R-4.3 最後一列有六欄（含 golden_fingerprint）", len(last) == 6, repr(last))
    for index, name in ((4, "重新基準化說明"), (5, "執行方式")):
        value = last[index] if len(last) > index else ""
        check_true(f"R-4.3 最後一列的「{name}」非空", bool(value.strip()), repr(last))
        check_true(
            f"R-4.3 最後一列的「{name}」不得是佔位符",
            value.strip().lower() not in {"-", "n/a", "na", "tbd", "todo", "待補"},
            repr(value),
        )


# ==========================================================================
# 錯誤路徑與邊界
# ==========================================================================
def test_operation_invalid_exits_nonzero() -> None:
    """[Q1=A] 的承接方式：operation 不合法時**立即非零 exit**，不得靜默回空值。

    單一 action 的 inputs／outputs 是三種操作的聯集，YAML 層看不出哪些組合合法；
    這個非零 exit 是唯一擋得住錯誤組合的地方。
    """
    proc = run_block("frobnicate", issue_body="")
    check_not("不合法的 operation 必須非零 exit", proc.returncode, 0)
    check_true(
        "不合法的 operation 必須有可讀的錯誤訊息",
        b"operation" in proc.stderr,
        proc.stderr.decode(),
    )
    check("不合法的 operation 不得靜默回空值", proc.stdout, b"")


def test_operation_missing_exits_nonzero() -> None:
    """operation 完全沒給時同樣立即失敗（`required: true` 只在 workflow 層生效，
    直接呼叫 block.sh 時擋不住）。"""
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("AIDLC_"):
            del env[key]
    env.pop("GITHUB_OUTPUT", None)
    proc = subprocess.run([BASH, str(BLOCK_SH)], env=env, capture_output=True)
    check_not("缺少 operation 必須非零 exit", proc.returncode, 0)
    check("缺少 operation 不得靜默回空值", proc.stdout, b"")


def test_render_rejects_newline_in_values() -> None:
    """render 的輸入含換行 → 立即失敗。

    值裡的換行會多出一整行，可以注入假的欄位行甚至假的結束標記；而且它會直接破壞
    scope_note 的逐字 round-trip，而 ADR-0015 §10 的雜湊等價不變式依賴那個 round-trip。

    render 的輸入來自機制自己（U-1 的 Decision ＋ U-6 組出的 Context），不可能來自
    人為編輯，所以在這裡失敗是介面誤用而非判定結果——與 parse／hash 的全函式性不衝突。
    """
    for field in ("scope_note", "traceable_row", "reason_code"):
        kw = dict(
            status="Ready",
            traceable_row="r",
            reason_code="mapped",
            scope_note="s",
            decided_at="",
            rejection_closed_at="",
        )
        kw[field] = "第一行\n- **Status**: 被注入的值"
        proc = render_expect_failure(**kw)
        check_not(f"render 拒絕 {field} 中的換行", proc.returncode, 0)
        check(f"render 拒絕 {field} 中的換行時不得吐出區塊", proc.stdout, b"")
    # CR 同理（CRLF 的來源不只人手打字，也可能是某個工具鏈轉換）。
    proc = render_expect_failure(
        status="Ready", traceable_row="r", reason_code="mapped",
        scope_note="含 CR 的值\r後半",
    )
    check_not("render 拒絕值中的 CR", proc.returncode, 0)


def test_render_rejects_marker_injection() -> None:
    """render 的輸入含受管標記字首 → 立即失敗（縱深防禦）。

    目前所有值都被寫在 `- **X**: ` 之後、不可能出現在行首，故 parse 不會誤判；但格式
    一旦改動（例如某個值改成獨立成行），這條就從「多餘」變成唯一的防線。
    """
    proc = render_expect_failure(
        status="Ready",
        traceable_row="R-1 <!-- aidlc-sync:begin v=9 -->",
        reason_code="mapped",
        scope_note="s",
    )
    check_not("render 拒絕值中的起始標記", proc.returncode, 0)
    proc = render_expect_failure(
        status="Ready",
        traceable_row="R-1",
        reason_code="mapped",
        scope_note="s <!-- aidlc-sync:end -->",
    )
    check_not("render 拒絕值中的結束標記", proc.returncode, 0)


def test_hash_is_total_on_human_edited_block() -> None:
    """hash 對**人為編輯過、違反互斥不變式**的 Block 仍然成功。

    這一條看起來像在測「沒有驗證」，實際上它鎖住的是一個會被後人好意破壞的設計決定：
    parse 的輸入是人可以編輯的 issue body，人編出來的 Block 完全可能同時有 Status 與
    「未寫入原因」。而那正是**反向同步要偵測的情形**——U-8 的流程是
    read_item → parse → content_hash → 比對。若 hash 在此非零 exit，一次正常的人為
    編輯就會讓 workflow 紅燈，而不是開出反向 PR，直接違反 [ad:services.md] 的
    「機制的正常判斷不使 workflow 紅燈」。
    """
    body = read_fixture("body-human-edited.md")
    block = parsed_block(body)
    check_true(
        "這個 fixture 的確違反互斥不變式（否則本測試沒測到東西）",
        bool(block["status"]) and bool(block["reason_category"]),
        repr(block),
    )
    digest = block_hash(**block)
    check_true("hash 對違反不變式的 Block 仍成功", len(digest) == 64, digest)
    check_not(
        "而且它與機制自己寫的那一版雜湊不同（U-8 才偵測得到這次人為編輯）",
        digest,
        block_hash(**derive("1", **GOLDEN_CASES["golden-mapped.md"])),
    )


def test_empty_issue_body_returns_null() -> None:
    """空的 issue body（新開的 issue 常見）→ 回 null，不得失敗。"""
    out = parse("")
    check("空 body → found=false", out["found"], "false")
    check("空 body → has_marker=false", out["has_marker"], "false")


# ==========================================================================
# main
# ==========================================================================
def main() -> int:
    if not BLOCK_SH.is_file():
        print(f"找不到 {BLOCK_SH}", file=sys.stderr)
        return 2
    if not MIGRATIONS.is_file():
        print(f"找不到 {MIGRATIONS}", file=sys.stderr)
        return 2

    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    print(f"run-fixtures: {len(tests)} 組測試，fixture 目錄 {FIXTURES}")
    for test in tests:
        before = len(_FAILURES)
        try:
            test()
        except Exception as exc:  # noqa: BLE001 — runner 自己不得靜默失敗
            _FAILURES.append(f"{test.__name__} 執行時拋出例外：{exc!r}")
        mark = "FAIL" if len(_FAILURES) > before else "ok"
        print(f"  [{mark}] {test.__name__}")

    print(f"\n斷言數：{_CHECKS}　失敗：{len(_FAILURES)}")
    if _FAILURES:
        print("\n失敗明細：")
        for failure in _FAILURES:
            print(f"  - {failure}")
        return 1
    print("全數通過。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
