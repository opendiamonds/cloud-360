"""Resolve catalog SKU identifiers to human-readable descriptions.

Uses only ADR-0018 catalog-price hosts (AWS Price List, GCP Catalog, Azure
Retail). Failures are silent — callers keep the raw SKU. Descriptions may be
shown on line items; hourly prices are never written here (AH-6).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from cost.config import AWS_PRICING_API_REGION, PRICING_URLS

logger = logging.getLogger("cloud360.sku_catalog")

_CACHE_DIR = Path(__file__).resolve().parent / ".sku_desc_cache"
_LOOKUP_TIMEOUT = httpx.Timeout(4.0, connect=2.0)
_MAX_UNIQUE = 20

_GCP_SKU = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$", re.I)
_AWS_SKU = re.compile(r"^[A-Z0-9]{12,20}$", re.I)
_AZURE_SKUID = re.compile(r"^DZH[A-Z0-9]{6,}$", re.I)
_AZURE_ARM = re.compile(r"^Standard_[A-Za-z0-9_]+$")
_REGION_LIKE = re.compile(
    r"^(us|eu|ap|sa|af|me|ca|cn|il)-[a-z0-9-]+$|^(eastus|westus|centralus|"
    r"northeurope|westeurope|eastus2|westus2|southeastasia|japaneast)",
    re.I,
)


def looks_like_catalog_sku(cloud: str, spec: str) -> bool:
    text = (spec or "").strip()
    if not text or _REGION_LIKE.match(text):
        return False
    if cloud == "gcp":
        return bool(_GCP_SKU.match(text))
    if cloud == "azure":
        return bool(_AZURE_SKUID.match(text) or _AZURE_ARM.match(text))
    if cloud == "aws":
        return bool(_AWS_SKU.match(text) and not text.isdigit())
    return False


def enrich_line_specs(cloud: str, lines: list[dict[str, Any]]) -> None:
    """Fill ``specDescription`` on lines that carry a catalog SKU. Never raises."""
    seen: dict[tuple[str, str], str | None] = {}
    lookups = 0
    for line in lines:
        spec = str(line.get("spec") or "").strip()
        if not looks_like_catalog_sku(cloud, spec):
            continue
        service_id = str(line.get("serviceId") or "").strip()
        key = (spec, service_id)
        if key not in seen:
            if lookups >= _MAX_UNIQUE:
                seen[key] = None
            else:
                lookups += 1
                seen[key] = _lookup(cloud, spec, service_id)
        desc = seen[key]
        if desc:
            line["specDescription"] = desc


def _lookup(cloud: str, sku: str, service_id: str) -> str | None:
    cached = _read_cache(cloud, sku, service_id)
    if cached is not None:
        return cached or None
    desc: str | None = None
    try:
        if cloud == "gcp":
            desc = _lookup_gcp(sku, service_id)
        elif cloud == "azure":
            desc = _lookup_azure(sku)
        elif cloud == "aws":
            desc = _lookup_aws(sku)
    except Exception as exc:  # noqa: BLE001 — catalog miss must not fail upload
        logger.info("sku lookup failed cloud=%s: %s", cloud, type(exc).__name__)
    _write_cache(cloud, sku, service_id, desc or "")
    return desc


def _cache_path(cloud: str, sku: str, service_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{cloud}_{sku}_{service_id}")
    return _CACHE_DIR / f"{safe}.json"


def _read_cache(cloud: str, sku: str, service_id: str) -> str | None:
    path = _cache_path(cloud, sku, service_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return str(payload.get("description") or "")
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _write_cache(cloud: str, sku: str, service_id: str, description: str) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(cloud, sku, service_id).write_text(
            json.dumps({"description": description}),
            encoding="utf-8",
        )
    except OSError:
        return


def _gcp_key() -> str:
    return os.environ.get("GCP_BILLING_API_KEY", "").strip()


def _lookup_gcp(sku: str, service_id: str) -> str | None:
    api_key = _gcp_key()
    if not api_key:
        return None
    cfg = PRICING_URLS.get("gcp", {}) if isinstance(PRICING_URLS.get("gcp"), dict) else {}
    base = str(cfg.get("base_url", "https://cloudbilling.googleapis.com")).rstrip("/")
    if service_id:
        path = str(cfg.get("skus_path_template", "/v1/services/{service_id}/skus")).format(
            service_id=quote(service_id, safe="")
        )
        url = f"{base}{path}?{urlencode({'key': api_key, 'pageSize': 5000})}"
        payload = _get_json(url)
        for item in _iter_gcp_skus(payload):
            if str(item.get("skuId") or "").upper() == sku.upper():
                return _gcp_description(item)
        return None
    # No service id: v1beta filter by skuId when available.
    url = (
        f"{base}/v1beta/skus?{urlencode({'key': api_key, 'pageSize': 20})}"
        f"&filter={quote(f'skuId=\"{sku}\"')}"
    )
    payload = _get_json(url)
    for item in _iter_gcp_skus(payload):
        if str(item.get("skuId") or "").upper() == sku.upper():
            return _gcp_description(item)
    return None


def _iter_gcp_skus(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("skus") or payload.get("skuPrices") or []
    return [x for x in rows if isinstance(x, dict)]


def _gcp_description(item: dict[str, Any]) -> str | None:
    for key in ("description", "displayName", "name"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip() and "/" not in raw[:12]:
            return raw.strip()
    geo = item.get("geoTaxonomy") if isinstance(item.get("geoTaxonomy"), dict) else {}
    category = item.get("category") if isinstance(item.get("category"), dict) else {}
    bits = [
        str(category.get("resourceFamily") or "").strip(),
        str(category.get("resourceGroup") or "").strip(),
        str(geo.get("type") or "").strip(),
    ]
    text = " / ".join(b for b in bits if b)
    return text or None


def _lookup_azure(sku: str) -> str | None:
    cfg = PRICING_URLS.get("azure", {}) if isinstance(PRICING_URLS.get("azure"), dict) else {}
    base = str(cfg.get("base_url", "https://prices.azure.com")).rstrip("/")
    path = str(cfg.get("prices_path", "/api/retail/prices"))
    api_version = str(cfg.get("api_version", "2023-01-01-preview"))
    if _AZURE_ARM.match(sku):
        filt = f"armSkuName eq '{sku}'"
    else:
        filt = f"skuId eq '{sku}'"
    params = {
        "api-version": api_version,
        "$filter": filt,
        "currencyCode": "USD",
    }
    url = f"{base}{path}?{urlencode(params)}"
    payload = _get_json(url)
    items = payload.get("Items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        return None
    first = items[0] if isinstance(items[0], dict) else None
    if not first:
        return None
    bits = [
        str(first.get("productName") or "").strip(),
        str(first.get("skuName") or "").strip(),
        str(first.get("meterName") or "").strip(),
    ]
    # Deduplicate while keeping order
    uniq: list[str] = []
    for bit in bits:
        if bit and bit not in uniq:
            uniq.append(bit)
    return " · ".join(uniq) or None


def _lookup_aws(sku: str) -> str | None:
    if not os.environ.get("AWS_ACCESS_KEY_ID", "").strip():
        return None
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return None
    client = boto3.client(
        "pricing",
        region_name=AWS_PRICING_API_REGION,
        config=Config(connect_timeout=2, read_timeout=4, retries={"max_attempts": 1}),
    )
    # ServiceCode is required; try common families that appear on calculator exports.
    for service in ("AmazonEC2", "AmazonRDS", "AmazonS3", "AWSLambda", "AmazonEKS"):
        try:
            resp = client.get_products(
                ServiceCode=service,
                Filters=[{"Type": "TERM_MATCH", "Field": "sku", "Value": sku}],
                MaxResults=1,
            )
        except (BotoCoreError, ClientError, ValueError):
            continue
        price_list = resp.get("PriceList") or []
        if not price_list:
            continue
        raw = price_list[0]
        try:
            doc = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            continue
        product = (doc or {}).get("product") if isinstance(doc, dict) else None
        attrs = (product or {}).get("attributes") if isinstance(product, dict) else None
        if not isinstance(attrs, dict):
            continue
        for key in ("instanceType", "usagetype", "servicename", "operation"):
            val = str(attrs.get(key) or "").strip()
            if val:
                family = str(attrs.get("servicename") or service)
                extra = str(attrs.get("instanceType") or attrs.get("usagetype") or "")
                return " · ".join(p for p in (family, extra) if p)
    return None


def _get_json(url: str) -> Any:
    with httpx.Client(timeout=_LOOKUP_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        if resp.status_code != 200:
            return None
        return resp.json()
