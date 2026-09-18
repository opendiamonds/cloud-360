"""優化前後 findings 比對摘要（A3 協作草稿）。"""

from __future__ import annotations

from typing import Any

PILLAR_LABELS = {
    "operational_excellence": "Operational Excellence",
    "security": "Security",
    "reliability": "Reliability",
    "performance_efficiency": "Performance Efficiency",
    "cost_optimization": "Cost Optimization",
}


def _finding_key(f: dict[str, Any]) -> str:
    return str(f.get("code") or f.get("title") or "").strip()


def _risk_rank(f: dict[str, Any]) -> int:
    lens_risk = str(f.get("lens_risk") or "").upper()
    severity = str(f.get("severity") or "").lower()
    if lens_risk == "HIGH_RISK" or severity in ("high", "critical"):
        return 3
    if lens_risk == "MEDIUM_RISK" or severity in ("warn", "medium"):
        return 2
    if lens_risk == "LOW_RISK" or severity == "low":
        return 1
    return 0


def _risk_label(rank: int) -> str:
    if rank >= 3:
        return "HIGH_RISK"
    if rank >= 2:
        return "MEDIUM_RISK"
    return "LOW_RISK"


def _count_high_risk(findings: list[dict[str, Any]]) -> int:
    return sum(1 for f in findings if _risk_rank(f) >= 3)


def finding_advice(
    f: dict[str, Any],
    baseline_by_code: dict[str, dict[str, Any]] | None = None,
) -> str:
    direct = str(f.get("recommendation_hint") or f.get("hint") or "").strip()
    if direct:
        return direct
    base = (baseline_by_code or {}).get(_finding_key(f)) or {}
    base_hint = str(base.get("recommendation_hint") or base.get("hint") or "").strip()
    if base_hint:
        return base_hint
    msg = str(f.get("message") or base.get("message") or "").strip()
    if msg and not msg.startswith("Custom Lens 風險等級："):
        return msg
    title = str(f.get("title") or f.get("code") or "此項目")
    code = str(f.get("code") or "—")
    risk = str(f.get("lens_risk") or _risk_label(_risk_rank(f)))
    if risk == "HIGH_RISK":
        return (
            f"請優先消除「{title}」（{code}）之高風險：調整架構圖元件、補上對應 "
            f"Well-Architected 控制項，並重新評核確認。"
        )
    if risk == "MEDIUM_RISK":
        return (
            f"建議針對「{title}」（{code}）補強中風險缺口，參考 Lens 改善計畫並更新圖面後再評核。"
        )
    return f"請檢視「{title}」（{code}）並依 Well-Architected 實務補強。"


def build_optimize_suggestions_summary(
    baseline_findings: list[dict[str, Any]],
    new_findings: list[dict[str, Any]],
    *,
    baseline_score: float | None = None,
    new_score: float | None = None,
    baseline_high_risk: int | None = None,
    new_high_risk: int | None = None,
) -> str:
    baseline_map = {_finding_key(f): f for f in baseline_findings if _finding_key(f)}
    new_map = {_finding_key(f): f for f in new_findings if _finding_key(f)}

    resolved: list[dict[str, Any]] = []
    for _, baseline in baseline_map.items():
        br = _risk_rank(baseline)
        if br < 2:
            continue
        nxt = new_map.get(_finding_key(baseline))
        nr = _risk_rank(nxt) if nxt else 0
        if not nxt or nr < br:
            resolved.append(baseline)
    resolved.sort(key=_risk_rank, reverse=True)

    remaining = sorted(
        [f for f in new_findings if _risk_rank(f) >= 2],
        key=_risk_rank,
        reverse=True,
    )

    lines: list[str] = ["## 本次優化摘要", ""]
    parts: list[str] = []
    if baseline_score is not None and new_score is not None:
        parts.append(f"總分 {int(round(baseline_score))} → {int(round(new_score))}")
    before_hr = baseline_high_risk if baseline_high_risk is not None else _count_high_risk(baseline_findings)
    after_hr = new_high_risk if new_high_risk is not None else _count_high_risk(new_findings)
    parts.append(f"高風險 {before_hr} → {after_hr} 項")
    if parts:
        lines.append("；".join(parts) + "。")
        lines.append("")

    lines.extend(["### 已改善項目", ""])
    if not resolved:
        lines.append(
            "- 本次未偵測到可對照的 findings 改善（可能圖面已調整但規則代碼未變，或僅有低風險變動）。"
        )
        lines.append("")
    else:
        for f in resolved:
            pillar = PILLAR_LABELS.get(str(f.get("pillar") or ""), f.get("pillar") or "")
            was = f.get("lens_risk") or _risk_label(_risk_rank(f))
            lines.append(f"- **{pillar} · {f.get('title')}** (`{f.get('code')}`，原 {was})")
            advice = finding_advice(f, baseline_map)
            if advice:
                lines.append(f"  - 原問題／建議：{advice}")
            lines.append("  - 狀態：已消除或降級")
        lines.append("")

    lines.extend(["### 剩餘風險與建議", ""])
    if not remaining:
        lines.append(
            "- 目前無中／高風險剩餘項目。儲存後可再執行評核確認細部建議。"
        )
        lines.append("")
    else:
        for f in remaining:
            label = f.get("lens_risk") or _risk_label(_risk_rank(f))
            pillar = PILLAR_LABELS.get(str(f.get("pillar") or ""), f.get("pillar") or "")
            lines.append(f"- **[{label}] {pillar} · {f.get('title')}** (`{f.get('code')}`)")
            msg = str(f.get("message") or "").strip()
            if msg:
                lines.append(f"  - **問題**：{msg}")
            lines.append(f"  - **建議**：{finding_advice(f, baseline_map)}")
        lines.append("")

    return "\n".join(lines).strip()
