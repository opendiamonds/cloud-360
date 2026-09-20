"""GCP list price via Cloud Billing Catalog API (cloudbilling.googleapis.com)."""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any, Mapping, Optional

import httpx

from cost.config import PRICING_URLS
from cost.pricing_units import normalize_to_hourly

logger = logging.getLogger(__name__)

_HOURS_PER_MONTH = Decimal("730")


def _api_key() -> str:
    return os.environ.get("GCP_BILLING_API_KEY", "").strip()


def _gcp_cfg() -> Mapping[str, Any]:
    cfg = PRICING_URLS.get("gcp", {})
    return cfg if isinstance(cfg, dict) else {}


def _product_spec(sku: str) -> Optional[Mapping[str, object]]:
    defaults = PRICING_URLS.get("default_products_gcp", {})
    spec = defaults.get(sku) if isinstance(defaults, dict) else None
    return spec if isinstance(spec, dict) else None


def supports_gcp_official(sku: str) -> bool:
    return _product_spec(sku) is not None


def _money_to_decimal(money: Mapping[str, Any]) -> Optional[Decimal]:
    try:
        units = Decimal(str(money.get("units") or 0))
        nanos = Decimal(str(money.get("nanos") or 0)) / Decimal("1000000000")
        value = units + nanos
    except Exception:
        return None
    if not value.is_finite() or value < 0:
        return None
    return value


def _sku_matches_region(sku: Mapping[str, Any], region: str) -> bool:
    regions = sku.get("serviceRegions") or []
    if isinstance(regions, list) and region in regions:
        return True
    geo = sku.get("geoTaxonomy") or {}
    if isinstance(geo, dict):
        geo_type = str(geo.get("type") or "")
        if geo_type.endswith("GLOBAL") or geo_type == "GLOBAL":
            return True
        geo_regions = geo.get("regions") or []
        if isinstance(geo_regions, list) and region in geo_regions:
            return True
    return False


def _sku_matches_filters(sku: Mapping[str, Any], spec: Mapping[str, object]) -> bool:
    category = sku.get("category") or {}
    if not isinstance(category, dict):
        return False

    usage_type = spec.get("usage_type", "OnDemand")
    if usage_type and category.get("usageType") != usage_type:
        return False

    resource_family = spec.get("resource_family")
    if resource_family and category.get("resourceFamily") != resource_family:
        return False

    resource_group = spec.get("resource_group")
    if resource_group and category.get("resourceGroup") != resource_group:
        return False

    description = str(sku.get("description") or "")
    contains = spec.get("description_contains")
    if isinstance(contains, str) and contains:
        if contains.casefold() not in description.casefold():
            return False
    elif isinstance(contains, list):
        lowered = description.casefold()
        if not any(str(x).casefold() in lowered for x in contains if str(x).strip()):
            return False

    excludes = spec.get("description_excludes")
    if isinstance(excludes, list):
        lowered = description.casefold()
        if any(str(x).casefold() in lowered for x in excludes if str(x).strip()):
            return False

    return True


def _unit_price_from_sku(sku: Mapping[str, Any]) -> tuple[Optional[Decimal], Optional[str]]:
    pricing_info = sku.get("pricingInfo") or []
    if not isinstance(pricing_info, list) or not pricing_info:
        return None, None
    latest = pricing_info[-1]
    if not isinstance(latest, dict):
        return None, None
    expr = latest.get("pricingExpression") or {}
    if not isinstance(expr, dict):
        return None, None
    usage_unit = expr.get("usageUnit")
    rates = expr.get("tieredRates") or []
    if not isinstance(rates, list) or not rates:
        return None, None
    # Prefer the first paid tier (skip free startUsageAmount with $0 when possible)
    chosen = None
    for rate in rates:
        if not isinstance(rate, dict):
            continue
        money = rate.get("unitPrice") or {}
        if not isinstance(money, dict):
            continue
        price = _money_to_decimal(money)
        if price is None:
            continue
        if price > 0:
            chosen = price
            break
        if chosen is None:
            chosen = price
    return chosen, str(usage_unit) if usage_unit else None


def _to_hourly(
    unit_price: Decimal, usage_unit: str, assumed_quantity: Decimal
) -> Optional[Decimal]:
    u = (usage_unit or "").strip()
    # Catalog shorthand → calculator units
    if u in ("h", "hour", "hours"):
        return normalize_to_hourly("Hrs", unit_price, assumed_quantity=Decimal("1"))
    if u in ("s", "sec", "second", "seconds"):
        # per-second → continuous hourly (×3600)
        return normalize_to_hourly(
            "Hrs", unit_price * Decimal("3600"), assumed_quantity=Decimal("1")
        )
    if u in ("mo", "month", "month_1"):
        return normalize_to_hourly("Mo", unit_price, assumed_quantity=assumed_quantity)
    if u in ("GiBy.mo", "GiBy.month", "GB-mo", "GBy.mo"):
        return normalize_to_hourly("GB-Mo", unit_price, assumed_quantity=assumed_quantity)
    if u in ("GiBy", "GBy", "By"):
        return normalize_to_hourly("GB", unit_price, assumed_quantity=assumed_quantity)
    if u in ("TiBy", "TBy"):
        # BigQuery on-demand analysis is typically $/TiBy processed → treat as monthly qty
        return normalize_to_hourly("Mo", unit_price, assumed_quantity=assumed_quantity)
    if u in ("count", "requests", "query"):
        return normalize_to_hourly("Request", unit_price, assumed_quantity=assumed_quantity)
    # Unknown unit: treat as monthly-ish if not hourly
    return None


def _list_skus(service_id: str, api_key: str) -> list[dict[str, Any]]:
    cfg = _gcp_cfg()
    base = str(cfg.get("base_url", "https://cloudbilling.googleapis.com")).rstrip("/")
    path_tmpl = str(cfg.get("skus_path_template", "/v1/services/{service_id}/skus"))
    url = f"{base}{path_tmpl.format(service_id=service_id)}"
    timeout = httpx.Timeout(
        float(PRICING_URLS.get("offer_read_timeout_seconds", 180)),
        connect=float(PRICING_URLS.get("offer_connect_timeout_seconds", 3)),
    )
    out: list[dict[str, Any]] = []
    page_token: Optional[str] = None
    max_pages = int(cfg.get("max_pages", 20))
    for _ in range(max_pages):
        params: dict[str, str | int] = {"key": api_key, "pageSize": 5000}
        if page_token:
            params["pageToken"] = page_token
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(
                    "GCP Catalog API %s failed: HTTP %s", service_id, resp.status_code
                )
                return []
            payload = resp.json()
        if not isinstance(payload, dict):
            return []
        skus = payload.get("skus") or []
        if isinstance(skus, list):
            for item in skus:
                if isinstance(item, dict):
                    out.append(item)
        page_token = payload.get("nextPageToken") or None
        if not page_token:
            break
    return out


def fetch_hourly_via_gcp_catalog(sku: str, region: str) -> Optional[Decimal]:
    """Return equivalent hourly USD for a mapped GCP sku family + region."""
    api_key = _api_key()
    if not api_key:
        logger.warning("GCP Catalog API skipped: set GCP_BILLING_API_KEY")
        return None

    spec = _product_spec(sku)
    if spec is None:
        return None

    service_id = spec.get("service_id")
    if not isinstance(service_id, str) or not service_id.strip():
        return None

    assumed = Decimal(str(spec.get("assumed_quantity", 1)))
    region_optional = bool(spec.get("region_optional"))

    try:
        skus = _list_skus(service_id.strip(), api_key)
    except httpx.HTTPError as exc:
        logger.warning("GCP Catalog API error for %s: %s", sku, exc)
        return None

    for item in skus:
        if not region_optional and not _sku_matches_region(item, region):
            continue
        if not _sku_matches_filters(item, spec):
            continue
        unit_price, usage_unit = _unit_price_from_sku(item)
        if unit_price is None or not usage_unit:
            continue
        hourly = _to_hourly(unit_price, usage_unit, assumed)
        if hourly is not None and hourly > 0:
            return hourly
        if hourly is not None:
            return hourly
    return None
