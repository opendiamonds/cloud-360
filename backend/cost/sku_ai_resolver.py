"""Fuzzy + LLM fallback when sku_mapper cannot match a diagram cell label."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal

import httpx

from cost.config import CALCULATOR_AZURE_PRODUCTS, CALCULATOR_GCP_PRODUCTS, SKU_MAP
from cost.sku_mapper import MapCandidate, MapResult, map_cell
from services.llm_provider import configure_provider_env, get_model_name, get_provider, llm_auth_ready

logger = logging.getLogger(__name__)

InferenceSource = Literal["fuzzy", "ai"]

_SPACE_RE = re.compile(r"[\s_\-]+")
_FUZZY_MIN_SCORE = 0.68
_FUZZY_MIN_GAP = 0.06
_LLM_MIN_CONFIDENCE = 0.55
_LLM_TIMEOUT_S = 45.0

# 圖上常見口語／變體 label → 額外比對別名（不寫進 sku_map 以免過寬）
_EXTRA_FUZZY_ALIASES: dict[tuple[str, str], list[str]] = {
    ("azure", "AzureCDN"): [
        "Content Delivery Network",
        "Azure Content Delivery",
        "Microsoft CDN",
        "CDN edge",
    ],
    ("azure", "AzureKubernetesService"): [
        "Kubernetes",
        "Kubernetes cluster",
        "K8s",
        "Container orchestration",
    ],
    ("azure", "VirtualMachines"): ["VM", "Virtual Machine", "Compute instance", "IaaS VM"],
    ("azure", "AzureBlobStorage"): ["Blob", "Object storage", "Storage account"],
    ("azure", "AzureSQLDatabase"): ["SQL", "Managed SQL", "Relational database"],
    ("aws", "AmazonCloudFront"): ["CDN", "Edge cache", "Content delivery"],
    ("gcp", "CloudCDN"): ["CDN", "Edge cache", "Content delivery"],
    ("gcp", "Networking"): [
        "Load Balancer",
        "Load Balancing",
        "External HTTP(S) Load Balancing",
        "Application Load Balancer",
    ],
    ("gcp", "CloudObservability"): ["Monitoring", "Observability", "Cloud Logging"],
}


@dataclass(frozen=True)
class InferenceResult:
    candidate: MapCandidate
    source: InferenceSource
    note: str


def sku_ai_infer_enabled() -> bool:
    raw = os.environ.get("COST_SKU_AI_INFER", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _normalize_label(label: str) -> str:
    return _SPACE_RE.sub(" ", (label or "").casefold()).strip()


def _compact_label(label: str) -> str:
    return _normalize_label(label).replace(" ", "")


def detect_cloud_from_style(style: str) -> str | None:
    s = (style or "").casefold()
    if "aws4" in s or "mxgraph.aws" in s:
        return "aws"
    if "azure" in s or "mxgraph.azure" in s:
        return "azure"
    if "gcp" in s or "mxgraph.gcp" in s or "google" in s:
        return "gcp"
    return None


def _label_aliases(row: dict) -> list[str]:
    aliases: list[str] = []
    single = row.get("match_label", "")
    if isinstance(single, str) and single.strip():
        aliases.append(single.strip())
    multi = row.get("match_labels", [])
    if isinstance(multi, list):
        aliases.extend(str(x).strip() for x in multi if str(x).strip())
    return aliases


def _catalog_rows(cloud_hint: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in SKU_MAP.get("mappings", []):
        cloud = str(row.get("cloud") or "")
        sku = str(row.get("sku") or "")
        if not cloud or not sku:
            continue
        if cloud_hint and cloud != cloud_hint:
            continue
        key = (cloud, sku)
        if key in seen:
            continue
        seen.add(key)
        alias_list = (
            _label_aliases(row)
            + _EXTRA_FUZZY_ALIASES.get((cloud, sku), [])
            + (
                [str(CALCULATOR_AZURE_PRODUCTS[sku].get("calculator_search") or "")]
                if cloud == "azure" and sku in CALCULATOR_AZURE_PRODUCTS
                else [str(CALCULATOR_GCP_PRODUCTS[sku].get("calculator_search") or "")]
                if cloud == "gcp" and sku in CALCULATOR_GCP_PRODUCTS
                else []
            )
        )
        rows.append(
            {
                "sku": sku,
                "cloud": cloud,
                "category": row.get("category", "other"),
                "aliases": [a for a in alias_list if a],
            }
        )
    return rows


def _score_label_to_alias(label: str, alias: str) -> float:
    norm_l = _normalize_label(label)
    norm_a = _normalize_label(alias)
    compact_l = _compact_label(label)
    compact_a = _compact_label(alias)
    if not norm_l or not norm_a:
        return 0.0
    if norm_l == norm_a or compact_l == compact_a:
        return 1.0
    if f" {norm_a} " in f" {norm_l} " or f" {norm_l} " in f" {norm_a} ":
        return 0.88
    if compact_a in compact_l or compact_l in compact_a:
        return 0.82
    tokens_l = set(norm_l.split())
    tokens_a = set(norm_a.split())
    jaccard = 0.0
    if tokens_l and tokens_a:
        jaccard = len(tokens_l & tokens_a) / len(tokens_l | tokens_a)
        # 單字根重合（kubernetes ↔ kubernetes service）
        stem_hits = sum(
            1
            for tl in tokens_l
            for ta in tokens_a
            if len(tl) >= 4 and len(ta) >= 4 and (tl.startswith(ta[:4]) or ta.startswith(tl[:4]))
        )
        if stem_hits:
            jaccard = max(jaccard, min(0.85, 0.55 + 0.08 * stem_hits))
    ratio = SequenceMatcher(None, compact_l, compact_a).ratio()
    return max(ratio, 0.45 + 0.5 * jaccard)


def _fuzzy_infer(label: str, style: str, cloud_hint: str | None) -> InferenceResult | None:
    style_cloud = detect_cloud_from_style(style)
    cloud = cloud_hint or style_cloud
    best: tuple[float, MapCandidate, str] | None = None
    second_score = 0.0

    for row in _catalog_rows(cloud):
        aliases = list(row.get("aliases") or [])
        aliases.append(str(row.get("sku") or ""))
        best_alias_score = max((_score_label_to_alias(label, alias) for alias in aliases), default=0.0)
        if best_alias_score <= 0:
            continue
        cand = MapCandidate(
            sku=str(row["sku"]),
            cloud=str(row["cloud"]),
            category=str(row.get("category") or "other"),
        )
        if best is None or best_alias_score > best[0]:
            if best is not None:
                second_score = max(second_score, best[0])
            best = (best_alias_score, cand, str(row["sku"]))
        else:
            second_score = max(second_score, best_alias_score)

    if best is None or best[0] < _FUZZY_MIN_SCORE:
        return None
    if best[0] - second_score < _FUZZY_MIN_GAP and second_score >= _FUZZY_MIN_SCORE - 0.05:
        return None

    _, candidate, sku = best
    note = f"模糊比對：「{label}」→ {sku}（{candidate.cloud}，相似度 {best[0]:.0%}）"
    return InferenceResult(candidate=candidate, source="fuzzy", note=note)


def _openrouter_chat(system: str, user: str) -> str | None:
    configure_provider_env()
    if get_provider() == "cli":
        return None
    token = (
        os.environ.get("OPENROUTER_API_KEY", "").strip()
        or os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
    )
    if not token:
        return None
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://openrouter.ai/api").rstrip("/")
    model = get_model_name()
    url = f"{base}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=_LLM_TIMEOUT_S) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("SKU AI 推斷 LLM 呼叫失敗")
        return None
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        logger.warning("SKU AI 推斷 LLM 回應格式異常：%r", data)
        return None


def _parse_llm_mapping(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("SKU AI 推斷 JSON 解析失敗：%r", raw[:300])
        return None
    return parsed if isinstance(parsed, dict) else None


def _llm_infer_batch(
    cells: list[dict[str, str]],
    cloud_hint: str | None,
) -> dict[str, InferenceResult]:
    if not cells or not sku_ai_infer_enabled() or not llm_auth_ready():
        return {}

    catalog = _catalog_rows(cloud_hint)
    if not catalog:
        catalog = _catalog_rows(None)
    sku_index = {(str(r["cloud"]), str(r["sku"])): r for r in catalog}

    system = (
        "你是 Cloud-360 架構圖元件對照助理。依 label 與 style 線索，從 catalog 中選最合理的 sku。"
        "只能輸出 catalog 內存在的 sku；不確定時該列 sku 填 null。"
        "回覆單一 JSON：{\"mappings\":[{\"mxcell_id\":\"...\",\"sku\":\"...或null\","
        "\"cloud\":\"aws|gcp|azure\",\"confidence\":0-1,\"reason_zh\":\"繁中一句\"}]}"
    )
    user = json.dumps(
        {
            "cloud_hint": cloud_hint,
            "cells": cells,
            "catalog": catalog,
        },
        ensure_ascii=False,
    )
    parsed = _parse_llm_mapping(_openrouter_chat(system, user))
    if not parsed:
        return {}

    out: dict[str, InferenceResult] = {}
    rows = parsed.get("mappings") or parsed.get("results") or []
    if not isinstance(rows, list):
        return out

    for row in rows:
        if not isinstance(row, dict):
            continue
        mxcell_id = str(row.get("mxcell_id") or "").strip()
        sku = str(row.get("sku") or "").strip()
        cloud = str(row.get("cloud") or cloud_hint or "").strip()
        if not mxcell_id or not sku or not cloud:
            continue
        try:
            confidence = float(row.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < _LLM_MIN_CONFIDENCE:
            continue
        meta = sku_index.get((cloud, sku))
        if not meta:
            continue
        reason = str(row.get("reason_zh") or row.get("reason") or "語意相近").strip()
        label = next((c["label"] for c in cells if c["mxcell_id"] == mxcell_id), mxcell_id)
        note = f"AI 判斷：「{label}」→ {sku}（{cloud}，信心 {confidence:.0%}）— {reason}"
        out[mxcell_id] = InferenceResult(
            candidate=MapCandidate(
                sku=sku,
                cloud=cloud,
                category=str(meta.get("category") or "other"),
            ),
            source="ai",
            note=note,
        )
    return out


def resolve_cell(
    label: str,
    style: str,
    *,
    cloud_hint: str | None = None,
    mxcell_id: str | None = None,
    llm_batch: dict[str, InferenceResult] | None = None,
) -> tuple[MapResult, str | None]:
    """Exact map → fuzzy → optional AI batch result."""
    mapped = map_cell(label, style)
    if mapped.kind == "unique":
        return mapped, None
    if mapped.kind == "ambiguous" and mapped.candidates:
        style_cloud = detect_cloud_from_style(style) or cloud_hint
        if style_cloud:
            filtered = [c for c in mapped.candidates if c.cloud == style_cloud]
            if len(filtered) == 1:
                return MapResult(kind="unique", candidate=filtered[0]), None

    if mxcell_id and llm_batch and mxcell_id in llm_batch:
        inf = llm_batch[mxcell_id]
        return MapResult(kind="unique", candidate=inf.candidate), inf.note

    fuzzy = _fuzzy_infer(label, style, cloud_hint)
    if fuzzy:
        return MapResult(kind="unique", candidate=fuzzy.candidate), fuzzy.note

    if mxcell_id and llm_batch is None and sku_ai_infer_enabled() and llm_auth_ready():
        batch = _llm_infer_batch(
            [{"mxcell_id": mxcell_id, "label": label, "style": style}],
            cloud_hint or detect_cloud_from_style(style),
        )
        if mxcell_id in batch:
            inf = batch[mxcell_id]
            return MapResult(kind="unique", candidate=inf.candidate), inf.note

    return mapped, None


def infer_unmapped_cells(
    cells: list[Any],
    *,
    cloud_hint: str | None = None,
) -> dict[str, InferenceResult]:
    """Batch LLM inference for cells that exact+fuzzy cannot map."""
    if not sku_ai_infer_enabled() or not llm_auth_ready():
        return {}

    pending: list[dict[str, str]] = []
    for cell in cells:
        mapped = map_cell(cell.label_plain, cell.style)
        if mapped.kind == "unique":
            continue
        fuzzy = _fuzzy_infer(cell.label_plain, cell.style, cloud_hint)
        if fuzzy:
            continue
        pending.append(
            {
                "mxcell_id": cell.mxcell_id,
                "label": cell.label_plain,
                "style": (cell.style or "")[:240],
            }
        )
    if not pending:
        return {}
    return _llm_infer_batch(pending, cloud_hint or detect_cloud_from_style(cells[0].style if cells else ""))
