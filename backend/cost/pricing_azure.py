"""Azure list price via Retail Prices API (prices.azure.com) — public, no auth."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Mapping, Optional
from urllib.parse import urlencode

import httpx

from cost.config import PRICING_URLS
from cost.pricing_units import HOURS_PER_MONTH_LIST, normalize_to_hourly

logger = logging.getLogger(__name__)


def _azure_cfg() -> Mapping[str, Any]:
    cfg = PRICING_URLS.get("azure", {})
    return cfg if isinstance(cfg, dict) else {}


def _product_spec(sku: str) -> Optional[Mapping[str, object]]:
    defaults = PRICING_URLS.get("default_products_azure", {})
    spec = defaults.get(sku) if isinstance(defaults, dict) else None
    return spec if isinstance(spec, dict) else None


def supports_azure_official(sku: str) -> bool:
    return _product_spec(sku) is not None


def _odata_eq(field: str, value: str) -> str:
    escaped = value.replace("'", "''")
    return f"{field} eq '{escaped}'"


def _odata_contains(field: str, value: str) -> str:
    escaped = value.replace("'", "''")
    return f"contains({field}, '{escaped}')"


def _build_filter(spec: Mapping[str, object], region: str) -> str:
    parts: list[str] = []
    service_name = spec.get("service_name")
    if not isinstance(service_name, str) or not service_name.strip():
        raise ValueError("service_name required")
    parts.append(_odata_eq("serviceName", service_name.strip()))

    price_type = spec.get("price_type", "Consumption")
    if isinstance(price_type, str) and price_type.strip():
        parts.append(_odata_eq("priceType", price_type.strip()))

    region_optional = bool(spec.get("region_optional"))
    if not region_optional:
        parts.append(_odata_eq("armRegionName", region))

    for field, key in (
        ("productName", "product_name"),
        ("meterName", "meter_name"),
        ("skuName", "sku_name"),
        ("armSkuName", "arm_sku_name"),
    ):
        raw = spec.get(key)
        if isinstance(raw, str) and raw.strip():
            parts.append(_odata_eq(field, raw.strip()))

    for field, key in (
        ("productName", "product_name_contains"),
        ("meterName", "meter_name_contains"),
        ("skuName", "sku_name_contains"),
    ):
        raw = spec.get(key)
        if isinstance(raw, str) and raw.strip():
            parts.append(_odata_contains(field, raw.strip()))

    return " and ".join(parts)


def _item_matches_extra(item: Mapping[str, Any], spec: Mapping[str, object]) -> bool:
    """Client-side filters for excludes / preferred region zones."""
    excludes = spec.get("meter_name_excludes") or []
    meter = str(item.get("meterName") or "")
    if isinstance(excludes, list):
        lowered = meter.casefold()
        for x in excludes:
            if str(x).strip() and str(x).casefold() in lowered:
                return False

    prefer_region = spec.get("prefer_arm_region")
    if isinstance(prefer_region, str) and prefer_region.strip():
        # Soft preference handled in ranking, not hard reject.
        pass
    return True


def _normalize_azure_unit(unit: str, price: Decimal, qty: Decimal) -> Optional[Decimal]:
    u = (unit or "").strip()
    # Common Retail Prices shapes
    if u in ("1 Hour", "1/Hour", "Hour", "Hrs", "Hours"):
        return price
    if u in ("1/Day", "1 Day"):
        return (price * qty) / Decimal("24")
    if u in (
        "1/Month",
        "1 Month",
        "1 GB/Month",
        "1 GB",
        "10K",
        "1M/Month",
        "1K",
        "10M",
        "1",
    ):
        return (price * qty) / HOURS_PER_MONTH_LIST
    # Fall back to shared AWS-oriented helpers where units overlap
    mapped = {
        "1 Hour": "Hrs",
        "1/Hour": "Hrs",
        "1 GB/Month": "GB-Mo",
        "1 GB": "GB",
        "1/Month": "Mo",
        "1 Month": "Mo",
    }.get(u, u)
    return normalize_to_hourly(mapped, price, assumed_quantity=qty)


def _rank_item(item: Mapping[str, Any], spec: Mapping[str, object], region: str) -> tuple:
    """Lower tuple sorts first."""
    price = item.get("retailPrice")
    try:
        p = Decimal(str(price))
    except Exception:
        p = Decimal("0")
    prefer = str(spec.get("prefer_arm_region") or "").strip()
    arm_region = str(item.get("armRegionName") or "")
    prefer_hit = 0 if (prefer and arm_region == prefer) else 1
    region_hit = 0 if arm_region == region else 1
    zero_penalty = 0 if p > 0 else 1
    return (zero_penalty, prefer_hit, region_hit, p)


def _pick_hourly(items: list[dict[str, Any]], spec: Mapping[str, object], region: str) -> Optional[Decimal]:
    qty = Decimal(str(spec.get("assumed_quantity", 1)))
    candidates: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not _item_matches_extra(item, spec):
            continue
        price_raw = item.get("retailPrice")
        if price_raw is None:
            continue
        try:
            price = Decimal(str(price_raw))
        except Exception:
            continue
        if not price.is_finite() or price < 0:
            continue
        unit = str(item.get("unitOfMeasure") or "")
        hourly = _normalize_azure_unit(unit, price, qty)
        if hourly is None or hourly <= 0:
            continue
        item = {**item, "_hourly": hourly}
        candidates.append(item)
    if not candidates:
        return None
    candidates.sort(key=lambda it: _rank_item(it, spec, region))
    return candidates[0]["_hourly"]


def fetch_hourly_via_azure_retail(sku: str, region: str) -> Optional[Decimal]:
    """Return equivalent hourly USD for a mapped Azure sku + arm region."""
    spec = _product_spec(sku)
    if spec is None:
        return None

    cfg = _azure_cfg()
    base = str(cfg.get("base_url", "https://prices.azure.com")).rstrip("/")
    path = str(cfg.get("prices_path", "/api/retail/prices"))
    api_version = str(cfg.get("api_version", "2023-01-01-preview"))
    currency = str(cfg.get("currency_code", "USD"))

    try:
        filt = _build_filter(spec, region)
    except ValueError:
        return None

    params = {
        "api-version": api_version,
        "$filter": filt,
        "currencyCode": currency,
    }
    url = f"{base}{path}?{urlencode(params)}"

    timeout = httpx.Timeout(
        float(PRICING_URLS.get("offer_read_timeout_seconds", 60)),
        connect=float(PRICING_URLS.get("offer_connect_timeout_seconds", 3)),
    )
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(
                    "Azure Retail Prices HTTP %s for %s@%s",
                    resp.status_code,
                    sku,
                    region,
                )
                return None
            payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Azure Retail Prices error for %s@%s: %s", sku, region, exc)
        return None

    items = payload.get("Items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    return _pick_hourly([x for x in items if isinstance(x, dict)], spec, region)
