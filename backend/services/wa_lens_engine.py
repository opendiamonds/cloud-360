"""
wa_lens_engine.py — Offline Custom Lens loader + riskRules evaluation (POC).

Lens JSON format compatible with AWS WA Custom Lens schemaVersion 2021-11-01
(see AWS WA Tool User Guide lens format specification). Does NOT call AWS APIs.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from services.wa_rule_engine import WEIGHTS, parse_diagram_summary

logger = logging.getLogger("cloud360.wa_lens_engine")

DEFAULT_LENS_PATH = (
    Path(__file__).resolve().parent.parent / "lenses" / "cloud360-core-mvp-lens.json"
)
LENS_DIR = DEFAULT_LENS_PATH.parent
LENS_PATH_BY_PROVIDER = {
    "aws": DEFAULT_LENS_PATH,
    "gcp": LENS_DIR / "cloud360-core-mvp-lens-gcp.json",
    "azure": LENS_DIR / "cloud360-core-mvp-lens-azure.json",
}

LENS_ID = "cloud360-core-mvp"

# Map lens pillar ids → scoring weight keys used by WaRuleEngine
PILLAR_ALIAS = {
    "security": "security",
    "reliability": "reliability",
    "cost_optimization": "cost_optimization",
    "performance_efficiency": "performance_efficiency",
    "operational_excellence": "operational_excellence",
}

RISK_TO_SCORE = {
    "NO_RISK": 100.0,
    "MEDIUM_RISK": 70.0,
    "HIGH_RISK": 40.0,
}

# Q2=A: HIGH→high, MEDIUM→warn
RISK_TO_SEVERITY = {
    "HIGH_RISK": "high",
    "MEDIUM_RISK": "warn",
    "NO_RISK": "info",
}

# Q1=B: show HIGH + MEDIUM in findings
DEFAULT_FINDING_RISKS = frozenset({"HIGH_RISK", "MEDIUM_RISK"})


def load_lens(path: Path | None = None, provider: str | None = None) -> dict[str, Any]:
    """Load offline lens JSON. Prefer explicit path; else provider-specific file; else AWS default."""
    if path is None and provider:
        p_norm = (provider or "aws").lower().strip()
        path = LENS_PATH_BY_PROVIDER.get(p_norm, DEFAULT_LENS_PATH)
        if not path.exists():
            logger.warning("Lens file missing for provider=%s path=%s; using default", p_norm, path)
            path = DEFAULT_LENS_PATH
    p = path or DEFAULT_LENS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "2021-11-01":
        logger.warning("Unexpected lens schemaVersion=%s", data.get("schemaVersion"))
    return data


def list_questions(lens: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pillar in lens.get("pillars") or []:
        for q in pillar.get("questions") or []:
            out.append(
                {
                    "pillar_id": pillar.get("id"),
                    "pillar_name": pillar.get("name"),
                    "question_id": q.get("id"),
                    "title": q.get("title"),
                    "description": q.get("description"),
                    "choices": q.get("choices") or [],
                    "riskRules": q.get("riskRules") or [],
                }
            )
    return out


def _eval_condition(condition: str, selected: set[str]) -> bool:
    cond = (condition or "").strip()
    if cond == "default":
        return True
    # Replace choice ids with True/False then evaluate && || !
    tokens = re.findall(r"[A-Za-z0-9_]+|&&|\|\||!|\(|\)", cond)

    def replace_id(tok: str) -> str:
        if tok in ("&&", "||", "!", "(", ")"):
            return tok
        return "True" if tok in selected else "False"

    expr = " ".join(replace_id(t) for t in tokens)
    expr = expr.replace("&&", " and ").replace("||", " or ").replace("!", " not ")
    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 — controlled DSL
    except Exception:
        logger.warning("Invalid riskRules condition: %s", condition)
        return False


def risk_for_question(question: dict[str, Any], selected_choice_ids: list[str]) -> str:
    selected = set(selected_choice_ids or [])
    for rule in question.get("riskRules") or []:
        cond = rule.get("condition") or ""
        if _eval_condition(cond, selected):
            return rule.get("risk") or "HIGH_RISK"
    return "HIGH_RISK"


def score_answers(
    lens: dict[str, Any], answers: dict[str, list[str]]
) -> dict[str, Any]:
    """
    answers: { question_id: [choice_id, ...] }
    Returns risk_counts, per-question risks, pillar_scores, overall_score.
    """
    questions = list_questions(lens)
    per_q: list[dict[str, Any]] = []
    risk_counts = {"HIGH_RISK": 0, "MEDIUM_RISK": 0, "NO_RISK": 0}
    pillar_accum: dict[str, list[float]] = {}

    for q in questions:
        qid = q["question_id"]
        selected = answers.get(qid) or []
        risk = risk_for_question(q, selected)
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
        score = RISK_TO_SCORE.get(risk, 40.0)
        pid = PILLAR_ALIAS.get(q["pillar_id"] or "", q["pillar_id"] or "security")
        pillar_accum.setdefault(pid, []).append(score)
        per_q.append(
            {
                "question_id": qid,
                "pillar_id": pid,
                "title": q["title"],
                "selected_choice_ids": selected,
                "risk": risk,
                "score": score,
            }
        )

    pillar_scores = {k: 100.0 for k in WEIGHTS}
    for pid, vals in pillar_accum.items():
        if pid in pillar_scores and vals:
            pillar_scores[pid] = round(sum(vals) / len(vals), 2)

    overall = round(sum(pillar_scores[p] * WEIGHTS[p] for p in WEIGHTS), 2)
    return {
        "lens_id": LENS_ID,
        "lens_name": lens.get("name"),
        "answers": answers,
        "questions": per_q,
        "risk_counts": risk_counts,
        "pillar_scores": pillar_scores,
        "overall_score": overall,
        "weights": dict(WEIGHTS),
    }


def findings_from_lens_score(
    lens: dict[str, Any],
    score_block: dict[str, Any],
    *,
    include_risks: set[str] | frozenset[str] | None = None,
    source: str = "offline_lens",
) -> list[dict[str, Any]]:
    """
    Build Finding-shaped dicts from lens risk outcomes (same answers / riskRules as scores).
    Q1=B: HIGH + MEDIUM; Q2=A: severity high / warn.
    """
    risks = include_risks or DEFAULT_FINDING_RISKS
    by_id = {q["question_id"]: q for q in list_questions(lens)}
    out: list[dict[str, Any]] = []

    for item in score_block.get("questions") or []:
        risk = item.get("risk") or "HIGH_RISK"
        if risk not in risks:
            continue
        qid = item.get("question_id") or ""
        qmeta = by_id.get(qid) or {}
        selected = set(item.get("selected_choice_ids") or [])
        hints: list[str] = []
        for c in qmeta.get("choices") or []:
            cid = c.get("id")
            if cid and cid not in selected:
                plan = (c.get("improvementPlan") or {}).get("displayText")
                if plan:
                    hints.append(str(plan))
        if not hints:
            for c in qmeta.get("choices") or []:
                plan = (c.get("improvementPlan") or {}).get("displayText")
                if plan:
                    hints.append(str(plan))
        code = f"LENS-{qid}".upper().replace("_", "-")
        out.append(
            {
                "code": code,
                "pillar": item.get("pillar_id")
                or PILLAR_ALIAS.get(qmeta.get("pillar_id") or "", "security"),
                "severity": RISK_TO_SEVERITY.get(risk, "warn"),
                "title": item.get("title") or qid,
                "message": (
                    f"Custom Lens 風險等級：{risk}。"
                    f"{(qmeta.get('description') or '').strip()}"
                ).strip(),
                "node_ids": [],
                "recommendation_hint": " ".join(hints[:2]) if hints else "",
                "source": source,
                "lens_risk": risk,
                "question_id": qid,
            }
        )
    return out


def enrich_findings_recommendations(
    findings: list[dict[str, Any]], lens: dict[str, Any]
) -> list[dict[str, Any]]:
    """補齊 findings 的 recommendation_hint（含 compact 的 hint 欄位）。"""
    by_id = {q["question_id"]: q for q in list_questions(lens)}
    enriched: list[dict[str, Any]] = []
    for raw in findings or []:
        f = dict(raw)
        hint = str(f.get("recommendation_hint") or f.get("hint") or "").strip()
        if not hint:
            qid = str(f.get("question_id") or "")
            if not qid:
                code = str(f.get("code") or "")
                if code.upper().startswith("LENS-"):
                    qid = code[5:].lower().replace("-", "_")
            qmeta = by_id.get(qid) or {}
            plans: list[str] = []
            for c in qmeta.get("choices") or []:
                plan = (c.get("improvementPlan") or {}).get("displayText")
                if plan:
                    plans.append(str(plan).strip())
            if plans:
                f["recommendation_hint"] = "；".join(plans[:3])
        else:
            f["recommendation_hint"] = hint
        enriched.append(f)
    return enriched


def heuristic_answers_from_diagram(xml: str, lens: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """
    Deterministic POC filler when Agent is unavailable: keyword match on diagram summary.
    Still offline — no cloud provider APIs. Covers AWS / GCP / Azure vocabulary.
    """
    lens = lens or load_lens()
    summary = parse_diagram_summary(xml or "")
    blob = " ".join(
        f"{n.get('label', '')} {n.get('style', '')}" for n in summary.get("nodes") or []
    ).lower()

    def has(*keys: str) -> bool:
        return any(k in blob for k in keys)

    answers: dict[str, list[str]] = {}
    # sec_edge
    sel: list[str] = []
    if has(
        "waf",
        "cloud armor",
        "cloudarmor",
        "application gateway",
        "front door",
        "frontdoor",
        "azure firewall",
    ):
        sel.append("sec_edge_waf")
    if has("https", "tls", "acm", "certificate", "ssl"):
        sel.append("sec_edge_tls")
    answers["sec_edge"] = sel

    sel = []
    if has(
        "kms",
        "encrypt",
        "sse",
        "加密",
        "key vault",
        "keyvault",
        "cmek",
        "customer-managed",
    ):
        sel.append("sec_data_encrypt")
    if has(
        "private",
        "private_subnet",
        "private endpoint",
        "privateendpoint",
        "private service connect",
        "psc",
    ) and not has("0.0.0.0"):
        sel.append("sec_data_private")
    answers["sec_data"] = sel

    sel = []
    if has(
        "az-",
        "availability zone",
        "availabilityzone",
        "multi-az",
        "multiaz",
        "multi-zone",
        "multizone",
        "zone redundant",
        "zone-redundant",
    ):
        sel.append("rel_ha_multiaz")
    if has(
        "standby",
        "replica",
        "secondary",
        "multi-az",
        "failover",
        "geo-replica",
        "zone redundant",
        "zone-redundant",
        "regional mig",
    ):
        sel.append("rel_ha_standby")
    answers["rel_ha"] = sel

    # GCP GCAF: horizontal scalability (ignored if lens has no such question)
    sel = []
    if has(
        "mig",
        "managed instance group",
        "autoscal",
        "auto-scale",
        "auto scale",
        "hpa",
        "horizontal",
        "vmss",
        "scale set",
    ):
        sel.append("rel_scale_mig")
    answers["rel_scale"] = sel

    # Azure WARA / GCP GCAF DR extras (ignored if lens has no such questions)
    sel = []
    if has(
        "paired region",
        "secondary region",
        "geo-replica",
        "geo replication",
        "asr",
        "site recovery",
        "multi-region",
        "multiregion",
        "cross-region",
    ):
        sel.append("rel_dr_geo")
    if has(
        "backup",
        "recovery vault",
        "recovery services",
        "pitr",
        "point-in-time",
    ):
        sel.append("rel_dr_backup")
    answers["rel_dr"] = sel

    sel = []
    if has("health probe", "health check", "health endpoint", "readiness", "liveness"):
        sel.append("rel_health_probe")
    if has("auto-heal", "auto heal", "autoscale", "auto-scale", "vmss", "scale set"):
        sel.append("rel_health_heal")
    answers["rel_health"] = sel

    answers["cost_storage"] = (
        ["cost_lifecycle"]
        if has(
            "lifecycle",
            "glacier",
            "intelligent-tiering",
            "cool tier",
            "archive",
            "nearline",
            "coldline",
            "reserved",
        )
        else []
    )
    answers["perf_cache"] = (
        ["perf_cache_present"]
        if has(
            "cache",
            "elasticache",
            "redis",
            "cloudfront",
            "cdn",
            "memorystore",
            "front door",
        )
        else []
    )

    sel = []
    if has(
        "cloudwatch",
        "monitor",
        "grafana",
        "prometheus",
        "x-ray",
        "application insights",
        "app insights",
        "log analytics",
        "cloud monitoring",
        "cloud logging",
    ):
        sel.append("oe_monitor")
    if has(
        "alarm",
        "sns",
        "pager",
        "alert",
        "action group",
        "notification channel",
        "alerting",
    ):
        sel.append("oe_alarm")
    answers["oe_observe"] = sel

    # Drop unknown question ids if lens subset changes
    valid = {q["question_id"] for q in list_questions(lens)}
    return {k: v for k, v in answers.items() if k in valid}


async def answer_lens_with_agent(
    diagram_summary: dict[str, Any],
    lens: dict[str, Any],
) -> dict[str, list[str]]:
    """
    Ask ReviewAgent-style LLM to pick choices. Falls back to heuristic on failure.
    POC: prefer heuristic first if no API key (fast + testable); try agent when key present.
    """
    from services.llm_provider import (
        auth_error_message,
        configure_provider_env,
        get_model_name,
        llm_auth_ready,
    )
    from services.llm_limits import agent_sdk_env, get_xml_context_max_chars

    configure_provider_env()
    if not llm_auth_ready():
        # Falling back silently would look identical to a real LLM answer; say so.
        logger.warning("A3 lens 改用規則啟發式（未呼叫 LLM）：%s", auth_error_message())
        # Caller should pass xml for heuristic; here we only have summary → empty-ish
        blob = json.dumps(diagram_summary, ensure_ascii=False).lower()
        # Minimal map from summary text
        fake_xml = f"<mxGraphModel><root><mxCell id='1' value='{blob[:2000]}'/></root></mxGraphModel>"
        return heuristic_answers_from_diagram(fake_xml, lens)

    # Agent path: reuse Claude SDK briefly
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        TextBlock,
        create_sdk_mcp_server,
        tool,
    )

    questions = list_questions(lens)
    catalog = [
        {
            "question_id": q["question_id"],
            "title": q["title"],
            "choices": [{"id": c["id"], "title": c["title"]} for c in q["choices"]],
        }
        for q in questions
    ]
    collected: dict[str, list[str]] = {}

    @tool(
        "emit_lens_answers",
        "Submit selected best-practice choice ids per question for the offline lens.",
        {
            "type": "object",
            "properties": {
                "answers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_id": {"type": "string"},
                            "selected_choice_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["question_id", "selected_choice_ids"],
                    },
                }
            },
            "required": ["answers"],
        },
    )
    async def emit_lens_answers(args: dict[str, Any]) -> dict[str, Any]:
        for item in args.get("answers") or []:
            qid = item.get("question_id")
            ids = item.get("selected_choice_ids") or []
            if qid:
                collected[qid] = list(ids)
        return {"content": [{"type": "text", "text": "answers recorded"}]}

    mcp = create_sdk_mcp_server(
        name="cloud360-lens", version="1.0.0", tools=[emit_lens_answers]
    )
    model_name = get_model_name()
    diagram_cap = get_xml_context_max_chars()
    prompt = (
        "你是離線 Well-Architected 評核助理。根據架構圖摘要，為每題勾選適用的 best practice "
        "choice id（可多選或空陣列）。完成後必須呼叫 emit_lens_answers。\n"
        f"題目目錄：\n```json\n{json.dumps(catalog, ensure_ascii=False)}\n```\n"
        f"圖摘要：\n```json\n{json.dumps(diagram_summary, ensure_ascii=False)[:diagram_cap]}\n```"
    )
    options = ClaudeAgentOptions(
        system_prompt="Offline WA custom-lens answering. Only use emit_lens_answers tool.",
        model=model_name,
        mcp_servers={"cloud360-lens": mcp},
        tools=[],
        allowed_tools=["mcp__cloud360-lens__emit_lens_answers"],
        disallowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"],
        permission_mode="bypassPermissions",
        max_turns=4,
        env=agent_sdk_env(),
    )
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            pass
        if collected:
            return collected
    except Exception:
        logger.exception("lens agent failed; caller should fallback")
        raise
    raise RuntimeError("lens agent returned no answers")
