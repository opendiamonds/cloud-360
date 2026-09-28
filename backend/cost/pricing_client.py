"""PricingLookup Port — public catalog list-price fetch (``fetch_hourly``).

Call chain: AWS SDK (optional) → Bulk／disk cache; GCP Catalog; Azure Retail.
Results are for advice text only — never persist into estimate line items (AH-6).
No Postgres ``pricing_cache`` writes.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal, Mapping, Optional
from urllib.parse import urljoin, urlparse

import httpx

from cost.config import COVERAGE_BY_CLOUD, PRICING_URLS
from cost.pricing_gcp import fetch_hourly_via_gcp_catalog, supports_gcp_official
from cost.pricing_azure import fetch_hourly_via_azure_retail, supports_azure_official
from cost.pricing_offer_parser import parse_on_demand_hourly
from cost.pricing_sdk import fetch_hourly_via_sdk, use_sdk_enabled

PriceResultKind = Literal["hit", "miss", "unsupported"]

_CACHE_DIR = Path(__file__).resolve().parent / ".pricing_offer_cache"
_CACHE_TTL = timedelta(hours=24)


@dataclass(frozen=True)
class PriceHit:
    kind: Literal["hit"] = "hit"
    hourly: Decimal = Decimal("0")
    fetched_at: datetime = datetime.now(timezone.utc)
    source: str = "unknown"


@dataclass(frozen=True)
class PriceMiss:
    kind: Literal["miss"] = "miss"


@dataclass(frozen=True)
class PriceUnsupported:
    kind: Literal["unsupported"] = "unsupported"


def _host_allowed(url: str) -> bool:
    host = urlparse(url).hostname or ""
    allow = PRICING_URLS.get("allowlist_hosts", [])
    return host in allow


def _connect_timeout() -> float:
    return float(PRICING_URLS.get("offer_connect_timeout_seconds", 3))


def _read_timeout() -> float:
    env = os.environ.get("COST_PRICING_OFFER_READ_TIMEOUT", "").strip()
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return float(PRICING_URLS.get("offer_read_timeout_seconds", 180))


def _build_offer_url(service_code: str, region: str) -> str:
    aws = PRICING_URLS.get("aws", {})
    template = aws.get(
        "offer_path_template",
        "/offers/v1.0/aws/{service_code}/current/{region}/index.json",
    )
    base = aws.get("base_url", "https://pricing.us-east-1.amazonaws.com").rstrip("/")
    path = template.format(service_code=service_code, region=region)
    return urljoin(f"{base}/", path.lstrip("/"))


def _cache_path(service_code: str, region: str) -> Path:
    safe = f"{service_code}_{region}".replace("/", "_")
    return _CACHE_DIR / f"{safe}.json"


def _read_disk_cache(service_code: str, region: str, now: datetime) -> Optional[Decimal]:
    path = _cache_path(service_code, region)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched_raw = payload.get("fetched_at")
        hourly_raw = payload.get("hourly")
        if not fetched_raw or hourly_raw is None:
            return None
        fetched_at = datetime.fromisoformat(str(fetched_raw).replace("Z", "+00:00"))
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        if now - fetched_at >= _CACHE_TTL:
            return None
        return Decimal(str(hourly_raw))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _write_disk_cache(
    service_code: str,
    region: str,
    hourly: Decimal,
    fetched_at: datetime,
    *,
    source: str,
) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(service_code, region)
    payload = {
        "hourly": str(hourly),
        "fetched_at": fetched_at.isoformat(),
        "source": source,
        "service_code": service_code,
        "region": region,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _product_spec(service_code: str) -> Optional[Mapping[str, object]]:
    defaults = PRICING_URLS.get("default_products", {})
    spec = defaults.get(service_code)
    return spec if isinstance(spec, dict) else None


def supports_official_hourly(service_code: str) -> bool:
    """Whether official list-price lookup is configured for this service family."""
    return (
        _product_spec(service_code) is not None
        or supports_gcp_official(service_code)
        or supports_azure_official(service_code)
    )


def _spec_assumed_quantity(spec: Mapping[str, object]) -> Decimal:
    raw = spec.get("assumed_quantity", 1)
    return Decimal(str(raw))


def _parse_service_hourly(
    sku: str, offer: Mapping[str, object], region: str
) -> Optional[Decimal]:
    spec = _product_spec(sku)
    if spec is None:
        return None
    product_family = spec.get("product_family")
    if not isinstance(product_family, str):
        return None
    meta_keys = {
        "product_family",
        "location_optional",
        "assumed_quantity",
        "price_unit",
        "usagetype_template",
        "usagetype_bare_prefixes",
        "service_code",
    }
    filters = {
        key: str(value)
        for key, value in spec.items()
        if key not in meta_keys and value is not None
    }
    template = spec.get("usagetype_template")
    if isinstance(template, str) and template.strip():
        from cost.config import AWS_USAGE_TYPE_PREFIXES

        prefix = AWS_USAGE_TYPE_PREFIXES.get(region)
        if not prefix:
            return None
        bare = spec.get("usagetype_bare_prefixes") or []
        bare_list = [str(x) for x in bare] if isinstance(bare, list) else []
        if prefix in bare_list:
            filters["usagetype"] = template.replace("{prefix}-", "").replace("{prefix}", "")
        else:
            filters["usagetype"] = template.format(prefix=prefix)
    return parse_on_demand_hourly(
        offer,
        product_family=product_family,
        attribute_filters=filters,
        assumed_quantity=_spec_assumed_quantity(spec),
    )


def _download_offer(url: str) -> Optional[Mapping[str, object]]:
    if not _host_allowed(url):
        return None
    timeout = httpx.Timeout(_read_timeout(), connect=_connect_timeout())
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data if isinstance(data, dict) else None
    except (httpx.HTTPError, json.JSONDecodeError, ValueError):
        return None


def _api_service_code(sku: str) -> str:
    spec = _product_spec(sku) or {}
    raw = spec.get("service_code")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return sku


def _fetch_via_bulk_api(sku: str, region: str) -> Optional[Decimal]:
    now = datetime.now(timezone.utc)
    cached = _read_disk_cache(sku, region, now)
    if cached is not None:
        return cached

    api_code = _api_service_code(sku)
    offer_url = _build_offer_url(api_code, region)
    if not _host_allowed(offer_url):
        return None

    offer = _download_offer(offer_url)
    if offer is None:
        return None

    hourly = _parse_service_hourly(sku, offer, region)
    if hourly is None:
        return None

    spec = _product_spec(sku) or {}
    source_bits = ["bulk", api_code]
    if spec.get("instanceType"):
        source_bits.append(str(spec["instanceType"]))
    _write_disk_cache(sku, region, hourly, now, source="/".join(source_bits))
    return hourly


def fetch_hourly(cloud: str, sku: str, region: str) -> PriceHit | PriceMiss | PriceUnsupported:
    """
    Fetch hourly list price for a mapped service family + region.

    Call chain (U5 Port; no Postgres pricing_cache write):
      - aws → SDK ``get_products`` → Bulk API fallback
      - gcp → Cloud Billing Catalog API (cloudbilling.googleapis.com)
      - azure → Retail Prices API (prices.azure.com)
    """
    mode = COVERAGE_BY_CLOUD.get(cloud)
    if mode != "official_list":
        return PriceUnsupported()

    fetched_at = datetime.now(timezone.utc)

    if cloud == "gcp":
        if not supports_gcp_official(sku):
            return PriceMiss()
        gcp_hourly = fetch_hourly_via_gcp_catalog(sku, region)
        if gcp_hourly is not None:
            return PriceHit(hourly=gcp_hourly, fetched_at=fetched_at, source="gcp_catalog")
        return PriceMiss()

    if cloud == "azure":
        if not supports_azure_official(sku):
            return PriceMiss()
        azure_hourly = fetch_hourly_via_azure_retail(sku, region)
        if azure_hourly is not None:
            return PriceHit(hourly=azure_hourly, fetched_at=fetched_at, source="azure_retail")
        return PriceMiss()

    if cloud != "aws":
        return PriceUnsupported()

    if _product_spec(sku) is None:
        return PriceMiss()

    if use_sdk_enabled():
        sdk_hourly = fetch_hourly_via_sdk(sku, region)
        if sdk_hourly is not None:
            return PriceHit(hourly=sdk_hourly, fetched_at=fetched_at, source="aws_sdk")

    bulk_hourly = _fetch_via_bulk_api(sku, region)
    if bulk_hourly is not None:
        return PriceHit(hourly=bulk_hourly, fetched_at=fetched_at, source="bulk_api")

    return PriceMiss()
