#!/usr/bin/env python3
"""fixture 斷言 runner — U-1「映射與解析」composite action。

用法：
    python3 .github/actions/aidlc-sync-map/run-fixtures.py

非零 exit 表失敗。

這支腳本是 U-1 完成判準（`unit-of-work.md`）的執行器：
「給定 record 文字，輸出的 Decision 三元組正確；`get_field` 的四條行為（第一個 match／
存在但空／缺席／縮排不算）**各有反例通過**；對照表為總函式（[US:S-2 AC 15]）」。

**讀檔的是這支 runner，不是受測邏輯。** map.sh 只從環境變數讀輸入、只往 stdout 寫，
自身零 I/O——這正是 [US:S-10 AC 1] 的 fixture 驅動前提，也是 U-1 的驗證方式所要求的
「不得在此單元的驗證中出現任何網路或檔案系統 I/O」在受測面上的落實。

**R-1 群直接斷言 `get_field` 的回傳值，不只斷言最終 Decision。**
理由（`business-rules.md` R-1 群明文）：R-1.2（存在但空）與 R-1.3（缺席）在 map 的
第 1 條判定上**結論相同**，把 null 誤實作成空字串**不會被 Decision 暴露**。
本檔的 `test_r1_3_decision_cannot_expose_the_difference` 就是把這件事變成可執行的證據。
"""

from __future__ import annotations

import concurrent.futures
import itertools
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
MAP_SH = HERE / "map.sh"
FIXTURES = HERE / "fixtures"

# map.sh 以 bash 3.2（macOS 內建）可執行為底線，實際跑在 GitHub runner 的 bash 5 上。
# 設 AIDLC_MAP_BASH 可指定直譯器，用來在同一台機器上覆驗兩個版本。
BASH = os.environ.get("AIDLC_MAP_BASH", "bash")

# 固定的測試 record 座標。intent_id 由 record_path 相對 record_root 推導（[F1=A]）。
RECORD_ROOT = "fixtures-root"
RECORD_PATH = "fixtures-root/demo-intent"
INTENT_ID = "demo-intent"

REASON_CODES = {
    "mapped",
    "parked",
    "suppressed",
    "undecidable",
    "unparseable",
    "whitelisted",
}
STATUSES = {"", "Ready", "In progress", "In review", "Done"}

_FAILURES: list[str] = []
_CHECKS = 0


# --------------------------------------------------------------------------
# 驅動
# --------------------------------------------------------------------------
def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def invoke(
    state_md: str,
    *args: str,
    whitelist: str = "",
    reverse_pending: str = "",
    field_max_length: str = "50",
    record_path: str = RECORD_PATH,
    record_root: str = RECORD_ROOT,
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        AIDLC_STATE_MD=state_md,
        AIDLC_INTENTS_JSON="",
        AIDLC_RECORD_PATH=record_path,
        AIDLC_RECORD_ROOT=record_root,
        AIDLC_FIELD_MAX_LENGTH=field_max_length,
        AIDLC_WHITELIST=whitelist,
        AIDLC_REVERSE_PENDING=reverse_pending,
    )
    env.pop("GITHUB_OUTPUT", None)  # 測試只讀 stdout，不寫 runner 的 output 檔
    return subprocess.run(
        [BASH, str(MAP_SH), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def decide(state_md: str, **kw) -> dict[str, str]:
    """跑完整管線，回傳五個 output 的 dict。"""
    proc = invoke(state_md, **kw)
    if proc.returncode != 0:
        raise AssertionError(
            f"map.sh 以非零 exit 結束（{proc.returncode}），"
            f"但本單元的錯誤表達方式只有 reason_code，不得設 exit code。"
            f"\nstderr: {proc.stderr}"
        )
    out: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key] = value
    return out


def get_field(state_md: str, field: str) -> tuple[int, str]:
    """回傳 (exit_code, stdout)。exit 3 代表 R-1.3 的 null（與空字串是兩件事）。"""
    proc = invoke(state_md, "get_field", field)
    return proc.returncode, proc.stdout


def list_stages(state_md: str) -> tuple[int, list[tuple[str, str, str]], str]:
    proc = invoke(state_md, "list_stages")
    rows = [
        tuple(line.split("\t"))  # type: ignore[misc]
        for line in proc.stdout.split("\n")
        if line
    ]
    return proc.returncode, rows, proc.stderr.strip()


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
# R-1 群：get_field 的四條行為（各含反例）
# ==========================================================================
def test_r1_1_first_match_wins() -> None:
    """R-1.1 正式欄位之前另有同名行 → 回第一個 match。"""
    text = read_fixture("r1-1-duplicate-status.md")
    rc, value = get_field(text, "Status")
    check("R-1.1 get_field(Status) exit", rc, 0)
    check("R-1.1 get_field(Status) 取第一個 match", value, "Draft")
    # 反例：若實作成「最後一個 match」或「正則無 m 旗標而抓到別處」，就會是 Completed。
    check_not("R-1.1 反例：不得回最後一個 match", value, "Completed")


def test_r1_2_present_but_empty_returns_empty_string() -> None:
    """R-1.2 欄位存在但值為空 → 回空字串，不是下一行的內容。"""
    text = read_fixture("r1-2-empty-parked.md")
    rc, value = get_field(text, "Parked")
    check("R-1.2 get_field(Parked) exit 為 0（存在）", rc, 0)
    check("R-1.2 get_field(Parked) 回空字串", value, "")
    # 反例：引擎的正則用 [ \t]* 而非 \s* 正是為了這個——\s 會跨行吃到下一個 bullet。
    check_not("R-1.2 反例：不得回下一行的內容", value, "- **Revision Count**: 0")
    check_not("R-1.2 反例：不得回 Revision Count 的值", value, "0")


def test_r1_3_absent_returns_null_not_empty() -> None:
    """R-1.3 欄位完全缺席 → 回 null，且與空字串**走不同分支**。"""
    text = read_fixture("r1-3-absent-parked.md")
    rc, value = get_field(text, "Parked")
    check("R-1.3 get_field(Parked) 以 exit 3 表達 null", rc, 3)
    check("R-1.3 null 不帶任何 stdout", value, "")
    # 反例：若把缺席實作成空字串，exit 會是 0——與 R-1.2 無法分辨。
    check_not("R-1.3 反例：缺席不得與『存在但空』同 exit", rc, 0)


def test_r1_3_decision_cannot_expose_the_difference() -> None:
    """R-1.2 與 R-1.3 在 map 的第 1 條判定上結論相同 —— 這正是必須直接斷言
    get_field 的理由。本測試把該事實鎖住：兩個 fixture 的五個 output 完全相同。"""
    empty = decide(read_fixture("r1-2-empty-parked.md"))
    absent = decide(read_fixture("r1-3-absent-parked.md"))
    check("R-1.2/1.3 的 Decision 相同（故 Decision 驗不出這個區分）", empty, absent)
    check("R-1.2 的 Decision 為 Ready", empty["status"], "Ready")


def test_r1_4_indented_is_not_a_match() -> None:
    """R-1.4 縮排的 `  - **X**: ` 不視為 match。"""
    text = read_fixture("r1-4-indented-status.md")
    rc, value = get_field(text, "Status")
    check("R-1.4 get_field(Status) 跳過縮排行", (rc, value), (0, "Running"))
    # 反例：若行首錨點漏了，就會讀到縮排的 Foo。
    check_not("R-1.4 反例：不得讀到縮排行的值", value, "Foo")

    rc2, value2 = get_field(text, "Parked")
    # 只有縮排的 Parked 存在 ⇒ 對 get_field 而言等同缺席。
    check("R-1.4 只有縮排 Parked ⇒ 仍是 null", (rc2, value2), (3, ""))


# ==========================================================================
# R-2 群：stage 行的解析
# ==========================================================================
def test_r2_1_2_3_stage_line_shape_and_noise() -> None:
    """R-2.1 行樣式、R-2.2 in_scope 由尾綴定、R-2.3 不 match 的行靜默略過。"""
    rc, rows, _ = list_stages(read_fixture("r2-3-noise-in-section.md"))
    check("R-2.1 list_stages exit", rc, 0)
    check(
        "R-2.1/2.2/2.3 只有合格行入列，且 in_scope 由尾綴定",
        rows,
        [("x", "intent-capture", "EXECUTE"), (" ", "market-research", "SKIP")],
    )


def test_r2_4_zero_matching_lines() -> None:
    """R-2.4 區塊在但零行 match → Unparseable{missing:["stage-lines"]}。

    這條的存在理由：沒有它，引擎改變尾綴寫法會讓整批 stage 讀成非 stage 行 ⇒ stages
    為空 ⇒ 判定第 6 條命中 ⇒ **誤判為 Ready 且不報錯**。下方明確斷言它不是 Ready。
    """
    text = read_fixture("r2-4-zero-stage-lines.md")
    rc, rows, err = list_stages(text)
    check("R-2.4 list_stages exit 5", rc, 5)
    check("R-2.4 missing 識別字", err, "stage-lines")
    check("R-2.4 無任何 stage 入列", rows, [])

    d = decide(text)
    check("R-2.4 reason_code", d["reason_code"], "unparseable")
    check("R-2.4 status 為空字串（不寫）", d["status"], "")
    check_not("R-2.4 反例：不得靜默誤判為 Ready", d["status"], "Ready")
    check_true(
        "R-2.4 traceable_row 帶得出 missing 識別字",
        "stage-lines" in d["traceable_row"],
        d["traceable_row"],
    )


def test_r2_6_decoy_section_heading() -> None:
    """區塊標題必須**精確比對**，不得用前綴 glob。

    回歸來源：reviewer(code-generation) 的 Major。先前 map.sh 以
    `"## Stage Progress"*` 比對，使 `## Stage Progress Notes (deprecated…)`
    這類誘餌標題被當成真區塊，其 stage 行靜默併進真清單。

    **既有安全網為什麼抓不到**：R-2.4 檢的是「零行 match」、R-2.5 檢的是「無區塊」，
    而誤匹配的 match 數非零、區塊也存在——兩道下限檢查在這條路徑上都恆真。
    這正是需要一條專屬斷言的理由。
    """
    text = read_fixture("r2-6-decoy-section-heading.md")
    rc, rows, err = list_stages(text)
    check("誘餌標題：list_stages 成功", rc, 0)

    # rows 的形狀是 (checkbox, slug, EXECUTE|SKIP) 的 tuple，不是 dict。
    slugs = [r[1] for r in rows]
    check_not("誘餌區塊的 stage 不得入列", "ghost-stage-from-decoy" in slugs, True)
    check("只有真區塊的兩個 stage 入列", slugs, ["intent-capture", "scope-definition"])

    d = decide(text)
    check("誘餌不改變判定：仍為 Ready", d["status"], "Ready")
    check("誘餌不改變 reason_code", d["reason_code"], "mapped")


def test_r3_6_all_stages_out_of_scope() -> None:
    """in-scope 集合為空集合時的期望值（R-3.6）。

    來源：reviewer(code-generation) 的 Minor #3——總函式性測試只做結構與雙向蘊含
    斷言，這個分支的**期望值**先前沒有專屬 fixture 釘住。

    語意：`— SKIP` 的 stage 一律 in_scope=false，不參與任一條判定。in-scope 集合
    為空 ⇒ 「無任何 in-scope stage 動過」為真 ⇒ R-3.6 ⇒ Ready。注意 fixture 內
    的 `[x]`／`[-]` 都在 out-of-scope 行上，**不得**因此被讀成動過。
    """
    text = read_fixture("r3-6-all-out-of-scope.md")
    rc, rows, err = list_stages(text)
    check("全 out-of-scope：list_stages 成功", rc, 0)
    check("三行都解析出來", len(rows), 3)
    check_not(
        "沒有任何一行 in_scope（in_scope 由第 3 欄 == EXECUTE 判定）",
        any(r[2] == "EXECUTE" for r in rows),
        True,
    )

    d = decide(text)
    check("全 out-of-scope ⇒ Ready", d["status"], "Ready")
    check("reason_code 為 mapped", d["reason_code"], "mapped")
    check(
        "scope_note 兩段皆列出：skipped-in-scope 為 none",
        d["scope_note"],
        "skipped-in-scope: none; out-of-scope: market-research, team-formation, refined-mockups",
    )


def test_r2_5_no_stage_progress_section() -> None:
    """R-2.5 無 ## Stage Progress 區塊 → Unparseable{missing:["stage-progress-section"]}。"""
    text = read_fixture("r2-5-no-section.md")
    rc, rows, err = list_stages(text)
    check("R-2.5 list_stages exit 4", rc, 4)
    check("R-2.5 missing 識別字", err, "stage-progress-section")
    check("R-2.5 無任何 stage 入列", rows, [])

    d = decide(text)
    check("R-2.5 reason_code", d["reason_code"], "unparseable")
    check_true(
        "R-2.5 traceable_row 帶得出 missing 識別字",
        "stage-progress-section" in d["traceable_row"],
        d["traceable_row"],
    )


# ==========================================================================
# R-3 群：七條判定順序
# ==========================================================================
def test_r3_1_parked() -> None:
    d = decide(read_fixture("r3-1-parked.md"))
    check("R-3.1 status", d["status"], "")
    check("R-3.1 reason_code", d["reason_code"], "parked")
    check("R-3.1 traceable_row", d["traceable_row"], "R-3.1 parked")
    # 反例：該 record 有一個 in-scope 的 [-]，若少了 park 特判就會變成 In progress。
    check_not("R-3.1 反例：parked 必須壓過 R-3.5", d["status"], "In progress")


def test_r3_1_parked_beats_completed() -> None:
    """R-3.1 優先於 R-3.3（實務上互斥，但順序仍照上游寫明）。"""
    d = decide(read_fixture("r3-1-parked-beats-completed.md"))
    check("R-3.1 > R-3.3", d["reason_code"], "parked")
    check_not("R-3.1 > R-3.3 反例", d["status"], "Done")


def test_r3_2_suppressed() -> None:
    """R-3.2 intent_id ∈ Config.reverse_pending（換行分隔的集合）。"""
    text = read_fixture("r3-6-ready.md")
    d = decide(text, reverse_pending=f"other-intent\n{INTENT_ID}\n")
    check("R-3.2 status", d["status"], "")
    check("R-3.2 reason_code", d["reason_code"], "suppressed")
    check("R-3.2 traceable_row", d["traceable_row"], "R-3.2 suppressed")
    # 反例：同一份 record 不在集合內時是 Ready ⇒ 證明抑制真的來自集合成員身分。
    check("R-3.2 反例：不在集合內時不抑制", decide(text)["status"], "Ready")
    # 反例：集合非空但不含本 intent，不得誤抑制。
    check(
        "R-3.2 反例：集合含別人不影響本 intent",
        decide(text, reverse_pending="other-intent\n")["status"],
        "Ready",
    )


def test_r3_2_parked_wins_over_suppressed() -> None:
    d = decide(read_fixture("r3-1-parked.md"), reverse_pending=INTENT_ID)
    check("R-3.1 > R-3.2", d["reason_code"], "parked")


def test_r3_3_completed_beats_question() -> None:
    """R-3.3 讀 Status 欄位而非推導 checkbox，且先於第 4／5 條（不因殘留 [?] 回退）。"""
    d = decide(read_fixture("r3-3-completed-beats-question.md"))
    check("R-3.3 status", d["status"], "Done")
    check("R-3.3 reason_code", d["reason_code"], "mapped")
    check("R-3.3 traceable_row", d["traceable_row"], "R-3.3 runtime-status-completed")
    check_not("R-3.3 反例：不得因殘留 [?] 回退", d["status"], "In review")


def test_r3_4_in_review() -> None:
    d = decide(read_fixture("r3-4-in-review.md"))
    check("R-3.4 status", d["status"], "In review")
    check("R-3.4 traceable_row", d["traceable_row"], "R-3.4 in-scope-checkbox-question")
    # 反例：同一份 record 也有 [-]，[?] 必須優先。
    check_not("R-3.4 反例：[?] 必須壓過 [-]", d["status"], "In progress")


def test_r3_5_in_progress() -> None:
    for fixture in ("r3-5-in-progress-dash.md", "r3-5-in-progress-revising.md"):
        d = decide(read_fixture(fixture))
        check(f"R-3.5 status（{fixture}）", d["status"], "In progress")
        check(
            f"R-3.5 traceable_row（{fixture}）",
            d["traceable_row"],
            "R-3.5 in-scope-checkbox-in-progress",
        )


def test_r3_6_ready() -> None:
    d = decide(read_fixture("r3-6-ready.md"))
    check("R-3.6 status", d["status"], "Ready")
    check("R-3.6 traceable_row", d["traceable_row"], "R-3.6 no-in-scope-stage-touched")


def test_r3_6_bracket_s_does_not_count_as_touched() -> None:
    """R-3.6 的「動過」＝ in-scope checkbox 全落在 {" ", "S"}；"S" **不算動過**。"""
    d = decide(read_fixture("r5-skipped-prefix.md"))
    check("R-3.6 [S] 不算動過 ⇒ 仍是 Ready", d["status"], "Ready")
    check_not("R-3.6 反例：[S] 若算動過就會掉到 undecidable", d["reason_code"], "undecidable")


def test_r3_7_undecidable() -> None:
    d = decide(read_fixture("r3-7-undecidable.md"))
    check("R-3.7 status", d["status"], "")
    check("R-3.7 reason_code", d["reason_code"], "undecidable")
    check("R-3.7 traceable_row", d["traceable_row"], "R-3.7 undecidable")


# ==========================================================================
# [req:FR-B3] 的孿生 record —— R-3.6 的「S 不算動過」保護的就是這一條
# ==========================================================================
def test_frb3_twin_records_same_status_different_scope_note() -> None:
    """兩個只在 [S]／— SKIP 上不同的 record：Status **相同**，差別在 scope_note 可見。"""
    s = decide(read_fixture("frb3-twin-bracket-s.md"))
    k = decide(read_fixture("frb3-twin-suffix-skip.md"))

    check("FR-B3 孿生：[S] 側 status", s["status"], "Ready")
    check("FR-B3 孿生：— SKIP 側 status", k["status"], "Ready")
    check("FR-B3 孿生：兩者 Status 相同", s["status"], k["status"])
    check("FR-B3 孿生：兩者 reason_code 相同", s["reason_code"], k["reason_code"])

    check(
        "FR-B3 孿生：[S] 側 scope_note",
        s["scope_note"],
        "skipped-in-scope: feasibility; out-of-scope: none",
    )
    check(
        "FR-B3 孿生：— SKIP 側 scope_note",
        k["scope_note"],
        "skipped-in-scope: none; out-of-scope: feasibility",
    )
    check_not("FR-B3 孿生：差別不得被抹平", s["scope_note"], k["scope_note"])


# ==========================================================================
# R-4 群：Unparseable 與白名單
# ==========================================================================
def test_r4_1_whitelisted() -> None:
    d = decide(read_fixture("r2-5-no-section.md"), whitelist=f"260802-default\n{INTENT_ID}")
    check("R-4.1 reason_code", d["reason_code"], "whitelisted")
    check("R-4.1 status", d["status"], "")
    check_not("R-4.1 反例：白名單內不得回 unparseable", d["reason_code"], "unparseable")


def test_r4_2_unparseable() -> None:
    d = decide(read_fixture("r2-5-no-section.md"), whitelist="260802-default")
    check("R-4.2 reason_code", d["reason_code"], "unparseable")
    check_not("R-4.2 反例：不在白名單不得回 whitelisted", d["reason_code"], "whitelisted")


def test_r4_3_whitelist_only_applies_to_unparseable() -> None:
    """R-4.3 白名單只對 Unparseable 生效，不影響可解析 record 的判定。"""
    d = decide(read_fixture("r3-7-undecidable.md"), whitelist=INTENT_ID)
    check("R-4.3 可解析 record 的判定不受白名單影響", d["reason_code"], "undecidable")
    check_not("R-4.3 反例：白名單不得豁免判定結果", d["reason_code"], "whitelisted")

    d2 = decide(read_fixture("r3-6-ready.md"), whitelist=INTENT_ID)
    check("R-4.3 白名單不影響 Ready", d2["status"], "Ready")


# ==========================================================================
# R-5 群：自訂欄位值的格式與截斷
# ==========================================================================
def test_r5_no_prefix_and_no_truncation_when_within_limit() -> None:
    d = decide(read_fixture("r3-6-ready.md"))
    check("R-5 未超限時原樣輸出", d["field_value"], f"intent-capture ({INTENT_ID})")


def test_r5_1_truncates_slug_tail_only() -> None:
    """R-5.1 超出上限時只截斷 stage-slug 的尾端；R-5.2 (<編號>) 完整保留。"""
    d = decide(read_fixture("r5-long-stage.md"), field_max_length="50")
    check(
        "R-5.1 只截 slug 尾端",
        d["field_value"],
        "an-extremely-long-stage-slug-used-fo (demo-intent)",
    )
    check("R-5.1 結果剛好落在上限", len(d["field_value"]), 50)
    check_true(
        "R-5.2 (<編號>) 完整保留",
        d["field_value"].endswith(f" ({INTENT_ID})"),
        d["field_value"],
    )


def test_r5_2_prefix_never_truncated() -> None:
    d = decide(read_fixture("r5-parked-long-stage.md"), field_max_length="30")
    check_true(
        "R-5.2 前綴完整保留",
        d["field_value"].startswith("parked @ "),
        d["field_value"],
    )
    check_true(
        "R-5.2 編號完整保留",
        d["field_value"].endswith(f" ({INTENT_ID})"),
        d["field_value"],
    )
    check("R-5.2 長度收斂到上限", len(d["field_value"]), 30)


def test_r5_3_slug_can_be_truncated_to_zero_length() -> None:
    """R-5.3 slug 可被截到零長度；前綴與左括號之間留原本的空格。"""
    d = decide(read_fixture("r5-parked-long-stage.md"), field_max_length="23")
    check("R-5.3 slug 截到零長", d["field_value"], f"parked @  ({INTENT_ID})")
    check("R-5.3 仍等於上限", len(d["field_value"]), 23)


def test_r5_4_over_limit_is_deliberate() -> None:
    """R-5.4 前綴 ＋ 編號本身已超過上限時，**照寫且允許超過上限**。

    這是刻意違反上限，不是漏判——欄位的全部價值是狀態訊號（前綴）與可追溯的編號，
    截掉任一個，欄位就同時失去兩者。
    """
    d = decide(read_fixture("r5-parked-long-stage.md"), field_max_length="10")
    check("R-5.4 照寫", d["field_value"], f"parked @  ({INTENT_ID})")
    check_true(
        "R-5.4 刻意超過上限",
        len(d["field_value"]) > 10,
        f"len={len(d['field_value'])}",
    )
    check_not("R-5.4 反例：不得為了守上限而截掉前綴", d["field_value"][:9], "parked @ "[:9] + "X")
    check_true(
        "R-5.4 反例：不得截掉編號",
        d["field_value"].endswith(f"({INTENT_ID})"),
        d["field_value"],
    )


def test_r5_prefix_selection() -> None:
    skipped = decide(read_fixture("r5-skipped-prefix.md"))
    check("R-5 `skipped ` 前綴", skipped["field_value"], f"skipped feasibility ({INTENT_ID})")

    frozen = decide(read_fixture("r5-frozen-prefix.md"))
    check("R-5 `frozen: ` 前綴", frozen["field_value"], f"frozen: market-research ({INTENT_ID})")

    parked = decide(read_fixture("r3-1-parked.md"))
    check("R-5 `parked @ ` 前綴用 Parked At Stage", parked["field_value"], f"parked @ feasibility ({INTENT_ID})")


def test_r5_undecidable_has_no_defined_prefix() -> None:
    """`undecidable` 的自訂欄位行為在上游未定義（ADR-0015 §14 明文「實作不得自行猜」）。

    因此不寫值（Decision.field_value 的值域明訂可為空），而不是掰一個前綴。
    """
    d = decide(read_fixture("r3-7-undecidable.md"))
    check("undecidable 不寫自訂欄位值", d["field_value"], "")


def test_r5_unparseable_has_empty_field_value() -> None:
    check("unparseable 的 field_value 為空", decide(read_fixture("r2-5-no-section.md"))["field_value"], "")


# ==========================================================================
# scope_note 群（R-6.1–6.5）
# ==========================================================================
def test_scope_note_both_classes() -> None:
    d = decide(read_fixture("r6-both-classes.md"))
    check(
        "R-6.2/6.3 兩類都有",
        d["scope_note"],
        "skipped-in-scope: feasibility, scope-definition; out-of-scope: market-research, team-formation",
    )


def test_scope_note_one_class_empty_writes_none() -> None:
    check(
        "R-6.3 out-of-scope 為空寫 none",
        decide(read_fixture("r6-skipped-only.md"))["scope_note"],
        "skipped-in-scope: feasibility; out-of-scope: none",
    )
    check(
        "R-6.3 skipped-in-scope 為空寫 none",
        decide(read_fixture("r6-out-of-scope-only.md"))["scope_note"],
        "skipped-in-scope: none; out-of-scope: market-research",
    )


def test_scope_note_order_preserved_no_dedup() -> None:
    """R-6.4 依 record 內的出現順序，不排序、不去重、不截斷。

    順序必須是決定性的——本欄位進 Block 進而進 content_hash，順序一變雜湊就變。
    """
    d = decide(read_fixture("r6-order-and-duplicates.md"))
    check(
        "R-6.4 保序且保留重複",
        d["scope_note"],
        "skipped-in-scope: mike, bravo, mike; out-of-scope: zulu, alpha, zulu",
    )
    # 反例：若排序，skipped 會變成 bravo, mike, mike。
    check_not(
        "R-6.4 反例：不得排序",
        d["scope_note"],
        "skipped-in-scope: bravo, mike, mike; out-of-scope: alpha, zulu, zulu",
    )
    # 反例：若去重，會少掉第二個 mike／zulu。
    check_not(
        "R-6.4 反例：不得去重",
        d["scope_note"],
        "skipped-in-scope: mike, bravo; out-of-scope: zulu, alpha",
    )


def test_scope_note_both_empty_is_not_empty_string() -> None:
    """R-6.5 兩類皆空時是雙 none，**不是空字串**（空字串與「解析不出」在 parse 側無法分辨）。"""
    d = decide(read_fixture("r6-neither-class.md"))
    check("R-6.5 雙 none", d["scope_note"], "skipped-in-scope: none; out-of-scope: none")
    check_not("R-6.5 反例：不得為空字串", d["scope_note"], "")


def test_scope_note_on_unparseable_path() -> None:
    """Unparseable 路徑沒有 stages，依 R-6.5 給非空的雙 none。

    這是 functional-design `open-items.md` 的 **B:m-5**（Unparseable 路徑的 scope_note
    值未定義，而 R-6.5 又禁止空字串），落點為 Bolt 1 gate。此處採 R-6.5 的字面要求，
    **不是新裁決**——閘門若另有結論，改這裡與 map.sh 的 Unparseable 分支即可。
    """
    for fixture in ("r2-4-zero-stage-lines.md", "r2-5-no-section.md"):
        d = decide(read_fixture(fixture))
        check(
            f"B:m-5 Unparseable 的 scope_note（{fixture}）",
            d["scope_note"],
            "skipped-in-scope: none; out-of-scope: none",
        )
        check_not(f"B:m-5 不得為空字串（{fixture}）", d["scope_note"], "")


# ==========================================================================
# 總函式性（[US:S-2 AC 15]）
# ==========================================================================
CHECKBOXES = [" ", "-", "?", "R", "x", "S"]
SCOPES = ["EXECUTE", "SKIP"]
RUNTIME_STATUSES = ["", "Completed", "Running"]
PARKED_VARIANTS = [None, "", "held for review"]  # None = 欄位缺席（R-1.3）


def synth_state(cb1, sc1, cb2, sc2, runtime_status, parked) -> str:
    parked_line = "" if parked is None else f"- **Parked**: {parked}\n"
    return (
        "# AI-DLC State Tracking\n\n"
        "## Runtime State\n"
        f"{parked_line}"
        "- **Parked At Stage**: alpha\n"
        "- **Revision Count**: 0\n\n"
        "## Stage Progress\n"
        "### SYNTHETIC PHASE\n"
        f"- [{cb1}] alpha — {sc1}\n"
        f"- [{cb2}] bravo — {sc2}\n\n"
        "## Current Status\n"
        "- **Current Stage**: alpha\n"
        f"- **Status**: {runtime_status}\n"
    )


def _totality_case(args) -> str | None:
    cb1, sc1, cb2, sc2, runtime_status, parked, reverse = args
    text = synth_state(cb1, sc1, cb2, sc2, runtime_status, parked)
    label = (
        f"[{cb1}]{sc1} / [{cb2}]{sc2} / Status={runtime_status!r} / "
        f"Parked={parked!r} / reverse={reverse}"
    )
    try:
        d = decide(text, reverse_pending=(INTENT_ID if reverse else ""))
    except AssertionError as exc:
        return f"總函式性：{label} 拋出例外／非零 exit\n    {exc}"

    if set(d) != {"status", "field_value", "reason_code", "traceable_row", "scope_note"}:
        return f"總函式性：{label} 的 output 集合不是恰好五個 —— {sorted(d)}"
    if d["reason_code"] == "":
        return f"總函式性：{label} 的 reason_code 為空"
    if d["reason_code"] not in REASON_CODES:
        return f"總函式性：{label} 的 reason_code {d['reason_code']!r} 不在值域內"
    if d["status"] not in STATUSES:
        return f"總函式性：{label} 的 status {d['status']!r} 不在值域內"
    if d["traceable_row"] == "":
        return f"總函式性：{label} 的 traceable_row 為空"
    if d["scope_note"] == "":
        return f"總函式性：{label} 的 scope_note 為空（違反 R-6.5）"
    # status != null **恰好蘊含** reason_code == "mapped"（雙向）
    if (d["status"] != "") != (d["reason_code"] == "mapped"):
        return (
            f"總函式性：{label} 破壞「status 非 null ⟺ reason_code == mapped」"
            f" —— status={d['status']!r} reason_code={d['reason_code']!r}"
        )
    return None


def test_totality() -> None:
    """對 (checkbox 組合 × in_scope 組合 × runtime_status × parked × reverse_pending)
    的窮舉：map 不拋例外、恰好產生一個 Decision、reason_code 非空且在值域內，
    且 status != null **恰好蘊含** reason_code == "mapped"。"""
    global _CHECKS
    combos = list(
        itertools.product(
            CHECKBOXES, SCOPES, CHECKBOXES, SCOPES,
            RUNTIME_STATUSES, PARKED_VARIANTS, [False, True],
        )
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(_totality_case, combos))

    _CHECKS += len(combos)
    failures = [r for r in results if r is not None]
    if failures:
        _FAILURES.extend(failures[:10])
        if len(failures) > 10:
            _FAILURES.append(f"總函式性：另有 {len(failures) - 10} 筆失敗未列出")
    print(f"  totality: {len(combos)} 組窮舉組合，失敗 {len(failures)}")


# ==========================================================================
# main
# ==========================================================================
def main() -> int:
    if not MAP_SH.is_file():
        print(f"找不到 {MAP_SH}", file=sys.stderr)
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
