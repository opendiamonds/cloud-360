"""Resolve GCP Pricing Calculator product titles (label / AI first, YAML fallback)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from cost.config import CALCULATOR_GCP_PRODUCTS
from cost.sku_ai_resolver import _openrouter_chat, _parse_llm_mapping, sku_ai_infer_enabled
from services.llm_provider import llm_auth_ready

logger = logging.getLogger(__name__)

_SPACE_RE = re.compile(r"[\s_\-]+")
_FUZZY_MIN_SCORE = 0.62
_LLM_MIN_CONFIDENCE = 0.55
_GENERIC_SEARCH_TOKENS = frozenset(
    {
        "cloud",
        "load",
        "service",
        "google",
        "data",
        "network",
        "management",
        "platform",
        "engine",
        "storage",
        "balancer",
        "gateway",
    }
)

_NO_RESULT_TITLES = frozenset(
    {
        "no products matched your search",
        "no products matched",
    }
)


@dataclass(frozen=True)
class GcpCalculatorProductTarget:
    click_title: str
    service_type: str | None = None
    source: str = "yaml"
    note: str | None = None


def _normalize(text: str) -> str:
    return _SPACE_RE.sub(" ", (text or "").casefold()).strip()


def _compact(text: str) -> str:
    return _normalize(text).replace(" ", "")


def is_valid_calculator_product_title(title: str) -> bool:
    text = _normalize(title)
    if not text or text in _NO_RESULT_TITLES:
        return False
    if text.startswith("add to"):
        return False
    return True


def filter_visible_products(titles: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in titles:
        title = str(raw or "").strip()
        if not is_valid_calculator_product_title(title):
            continue
        key = _normalize(title)
        if key in seen:
            continue
        seen.add(key)
        out.append(title)
    return out


def label_search_variants(label: str | None) -> list[str]:
    """從架構元件 label 產生 Calculator 搜尋關鍵字（優先於 YAML）。"""
    text = (label or "").strip()
    if not text:
        return []
    variants = [text]
    first_token = text.split()[0].strip(" ,;:")
    if (
        len(first_token) >= 3
        and first_token not in variants
        and _normalize(first_token) not in _GENERIC_SEARCH_TOKENS
    ):
        variants.append(first_token)
    if " " in text:
        compact = re.sub(r"\s+", " ", text)
        for part in re.split(r"[\s/|]+", compact):
            part = part.strip(" ,;:")
            if len(part) >= 4 and part not in variants:
                if _normalize(part) in _GENERIC_SEARCH_TOKENS:
                    continue
                variants.append(part)
    return variants


def _score(a: str, b: str) -> float:
    norm_a = _normalize(a)
    norm_b = _normalize(b)
    compact_a = _compact(a)
    compact_b = _compact(b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b or compact_a == compact_b:
        return 1.0
    if norm_b in norm_a or norm_a in norm_b:
        return 0.9
    if compact_b in compact_a or compact_a in compact_b:
        return 0.84
    ratio = SequenceMatcher(None, compact_a, compact_b).ratio()
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    jaccard = 0.0
    if tokens_a and tokens_b:
        jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    return max(ratio, 0.45 + 0.55 * jaccard)


def _spec_hints(spec: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    for key in ("calculator_search", "calculator_product", "sku"):
        value = str(spec.get(key) or "").strip()
        if value and value not in hints:
            hints.append(value)
    aliases = spec.get("calculator_search_aliases") or []
    if isinstance(aliases, list):
        for alias in aliases:
            text = str(alias or "").strip()
            if text and text not in hints:
                hints.append(text)
    return hints


def _service_type_for_map_key(map_key: str) -> str | None:
    spec = CALCULATOR_GCP_PRODUCTS.get(map_key) or {}
    service_type = str(spec.get("calculator_service_type") or "").strip()
    return service_type or None


def _fuzzy_pick(
    hints: list[str],
    visible_products: list[str],
) -> tuple[str, float] | None:
    best_title: str | None = None
    best_score = 0.0
    second_score = 0.0
    for title in visible_products:
        title_score = max((_score(hint, title) for hint in hints), default=0.0)
        if title_score > best_score:
            second_score = best_score
            best_score = title_score
            best_title = title
        elif title_score > second_score:
            second_score = title_score
    if best_title is None or best_score < _FUZZY_MIN_SCORE:
        return None
    if second_score >= _FUZZY_MIN_SCORE - 0.05 and best_score - second_score < 0.05:
        return None
    return best_title, best_score


def _ai_pick_product(
    *,
    map_key: str,
    visible_products: list[str],
    diagram_label: str | None,
    yaml_service_type: str | None = None,
) -> GcpCalculatorProductTarget | None:
    if not sku_ai_infer_enabled() or not llm_auth_ready() or not visible_products:
        return None

    system = (
        "你是 Google Cloud Pricing Calculator 產品選擇助理。"
        "主要依據架構圖元件 label，在 Calculator 搜尋結果（visible_products）中選最相近的產品 title。"
        "只能輸出 visible_products 內存在的 click_title；不可臆造。"
        "若該產品在設定面板有 Service type 下拉選單，可填 service_type，否則填 null。"
        '回覆 JSON：{"click_title":"...","service_type":"...或null","confidence":0-1,"reason_zh":"繁中一句"}'
    )
    user = json.dumps(
        {
            "diagram_label": diagram_label,
            "map_key_hint": map_key,
            "visible_products": visible_products,
            "yaml_service_type_hint": yaml_service_type,
        },
        ensure_ascii=False,
    )
    parsed = _parse_llm_mapping(_openrouter_chat(system, user))
    if not parsed:
        return None
    click_title = str(parsed.get("click_title") or "").strip()
    if click_title not in visible_products:
        matches = [p for p in visible_products if _normalize(p) == _normalize(click_title)]
        if len(matches) == 1:
            click_title = matches[0]
        else:
            return None
    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < _LLM_MIN_CONFIDENCE:
        return None
    service_type = str(parsed.get("service_type") or "").strip() or yaml_service_type
    reason = str(parsed.get("reason_zh") or parsed.get("reason") or "語意相近").strip()
    note = (
        f"AI Calculator 產品：「{diagram_label or map_key}」→ {click_title}"
        f"（信心 {confidence:.0%}）— {reason}"
    )
    return GcpCalculatorProductTarget(
        click_title=click_title,
        service_type=service_type,
        source="ai",
        note=note,
    )


def ai_suggest_calculator_search_terms(
    *,
    diagram_label: str | None,
    map_key: str,
    tried_terms: list[str],
    catalog_titles: list[str],
    max_terms: int = 3,
) -> list[str]:
    """搜尋無結果時，由 AI 依 label + Calculator 產品目錄建議搜尋字串。"""
    if not sku_ai_infer_enabled() or not llm_auth_ready():
        return []

    system = (
        "你是 Google Cloud Pricing Calculator 搜尋助理。"
        "使用者搜尋某些字串後沒有任何產品（No products matched）。"
        "請依架構元件 label，從 catalog_titles 中挑選最可能出現的產品名稱，"
        "並回傳 1-3 個應在搜尋框輸入的關鍵字 search_terms（短而準，例如 Apigee 而非 Apigee API Management）。"
        "不要重複 tried_terms。"
        '回覆 JSON：{"search_terms":["..."],"confidence":0-1,"reason_zh":"繁中一句"}'
    )
    user = json.dumps(
        {
            "diagram_label": diagram_label,
            "map_key_hint": map_key,
            "tried_terms": tried_terms,
            "catalog_titles": catalog_titles[:120],
        },
        ensure_ascii=False,
    )
    parsed = _parse_llm_mapping(_openrouter_chat(system, user))
    if not parsed:
        return []

    out: list[str] = []
    rows = parsed.get("search_terms") or parsed.get("terms") or []
    if isinstance(rows, list):
        for row in rows:
            term = str(row or "").strip()
            if not term:
                continue
            if _normalize(term) in {_normalize(t) for t in tried_terms}:
                continue
            if term not in out:
                out.append(term)
            if len(out) >= max_terms:
                break
    if out:
        reason = str(parsed.get("reason_zh") or "").strip()
        if reason:
            logger.info("AI Calculator 搜尋建議（%s）：%s", diagram_label or map_key, reason)
    return out


def resolve_gcp_calculator_product(
    *,
    map_key: str,
    visible_products: list[str],
    diagram_label: str | None = None,
) -> GcpCalculatorProductTarget:
    """Pick the Calculator modal product title (+ optional service type)."""
    spec = CALCULATOR_GCP_PRODUCTS.get(map_key)
    if not spec:
        raise ValueError(f"未知 map_key：{map_key!r}")

    visible = filter_visible_products(visible_products)
    if not visible:
        raise ValueError("Calculator 搜尋結果為空")

    yaml_service_type = _service_type_for_map_key(map_key)
    label_hints = label_search_variants(diagram_label)

    if diagram_label:
        for title in visible:
            if _normalize(title) == _normalize(diagram_label):
                return GcpCalculatorProductTarget(
                    click_title=title,
                    service_type=yaml_service_type,
                    source="label",
                    note=f"Calculator 元件 label 對照：{diagram_label} → {title}",
                )
        label_fuzzy = _fuzzy_pick(label_hints, visible)
        if label_fuzzy:
            title, score = label_fuzzy
            return GcpCalculatorProductTarget(
                click_title=title,
                service_type=yaml_service_type,
                source="label",
                note=f"模糊比對元件 label：{diagram_label} → {title}（{score:.0%}）",
            )

    ai = _ai_pick_product(
        map_key=map_key,
        visible_products=visible,
        diagram_label=diagram_label,
        yaml_service_type=yaml_service_type,
    )
    if ai:
        return ai

    configured_product = str(spec.get("calculator_product") or "").strip()
    configured_search = str(spec.get("calculator_search") or "").strip()
    for preferred in (configured_product, configured_search):
        if not preferred:
            continue
        for title in visible:
            if _normalize(title) == _normalize(preferred):
                return GcpCalculatorProductTarget(
                    click_title=title,
                    service_type=yaml_service_type,
                    source="yaml",
                    note=f"Calculator YAML 對照：{preferred} → {title}",
                )

    yaml_fuzzy = _fuzzy_pick(_spec_hints(spec), visible)
    if yaml_fuzzy:
        title, score = yaml_fuzzy
        return GcpCalculatorProductTarget(
            click_title=title,
            service_type=yaml_service_type,
            source="fuzzy",
            note=f"模糊比對 YAML：{' / '.join(_spec_hints(spec)[:2])} → {title}（{score:.0%}）",
        )

    hint = diagram_label or configured_search or map_key
    raise ValueError(
        f"找不到 GCP Calculator 產品：{hint!r}（可見：{', '.join(visible[:5])}）"
    )


def search_terms_for_map_key(map_key: str) -> list[str]:
    spec = CALCULATOR_GCP_PRODUCTS.get(map_key) or {}
    terms: list[str] = []
    for key in ("calculator_product", "calculator_search"):
        value = str(spec.get(key) or "").strip()
        if value and value not in terms:
            terms.append(value)
    aliases = spec.get("calculator_search_aliases") or []
    if isinstance(aliases, list):
        for alias in aliases:
            text = str(alias or "").strip()
            if text and text not in terms:
                terms.append(text)
    if not terms:
        terms.append(map_key)
    return terms


def search_terms_for_item(map_key: str, diagram_label: str | None = None) -> list[str]:
    """搜尋順序：元件 label 變體 → YAML（YAML 僅作 fallback hint）。"""
    terms: list[str] = []
    seen: set[str] = set()
    for term in label_search_variants(diagram_label) + search_terms_for_map_key(map_key):
        key = _normalize(term)
        if not key or key in seen:
            continue
        seen.add(key)
        terms.append(term)
    return terms
