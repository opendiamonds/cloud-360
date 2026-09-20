"""AWS Price List Query API via boto3 (``pricing.get_products``)."""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Mapping, Optional, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from cost.config import (
    AWS_PRICING_API_REGION,
    AWS_REGION_LOCATIONS,
    AWS_USAGE_TYPE_PREFIXES,
    PRICING_URLS,
)
from cost.pricing_query_parser import parse_price_list_items

logger = logging.getLogger(__name__)

_CLIENT = None


def _sdk_mode_raw() -> str:
    raw = os.environ.get("COST_PRICING_USE_SDK")
    if raw is None:
        raw = os.environ.get("COST_PRICING_USE_CLI", "auto")
    return (raw or "auto").strip().lower()


def use_sdk_enabled() -> bool:
    mode = _sdk_mode_raw()
    if mode in ("0", "false", "no"):
        return False
    return True


def _sdk_read_timeout() -> int:
    raw = (
        os.environ.get("COST_PRICING_SDK_TIMEOUT")
        or os.environ.get("COST_PRICING_CLI_TIMEOUT")
        or ""
    ).strip()
    if raw:
        try:
            return int(float(raw))
        except ValueError:
            pass
    return int(PRICING_URLS.get("sdk_timeout_seconds", 60))


def _product_spec(service_code: str) -> Optional[Mapping[str, object]]:
    defaults = PRICING_URLS.get("default_products", {})
    spec = defaults.get(service_code)
    return spec if isinstance(spec, dict) else None


_SPEC_META_KEYS = frozenset(
    {
        "product_family",
        "location_optional",
        "assumed_quantity",
        "price_unit",
        "usagetype_template",
        "usagetype_bare_prefixes",
        "service_code",
    }
)


def _resolve_usagetype(spec: Mapping[str, object], region: str) -> Optional[str]:
    """Build usagetype from template; us-east-1 NAT 等可省略 USE1 前綴。"""
    template = spec.get("usagetype_template")
    if not isinstance(template, str) or not template.strip():
        return None
    prefix = AWS_USAGE_TYPE_PREFIXES.get(region)
    if not prefix:
        raise ValueError(f"no usage_type_prefix for region {region}")
    bare = spec.get("usagetype_bare_prefixes") or []
    bare_list = [str(x) for x in bare] if isinstance(bare, list) else []
    if prefix in bare_list:
        # "{prefix}-NatGateway-Hours" → "NatGateway-Hours"（us-east-1 特例）
        return template.replace("{prefix}-", "").replace("{prefix}", "")
    return template.format(prefix=prefix)


def _api_service_code(sku: str, spec: Mapping[str, object]) -> str:
    raw = spec.get("service_code")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return sku


def _spec_meta(
    spec: Mapping[str, object], region: str
) -> Tuple[dict[str, str], Decimal, bool]:
    product_family = spec.get("product_family")
    if not isinstance(product_family, str):
        raise ValueError("product_family required")
    attribute_filters: dict[str, str] = {}
    for key, value in spec.items():
        if key in _SPEC_META_KEYS:
            continue
        if value is None:
            continue
        attribute_filters[key] = str(value)
    usagetype = _resolve_usagetype(spec, region)
    if usagetype:
        attribute_filters["usagetype"] = usagetype
    raw_qty = spec.get("assumed_quantity", 1)
    assumed_quantity = Decimal(str(raw_qty))
    location_optional = bool(spec.get("location_optional"))
    return attribute_filters, assumed_quantity, location_optional


def _location_for_region(region: str) -> Optional[str]:
    loc = AWS_REGION_LOCATIONS.get(region)
    return str(loc) if loc else None


def _get_pricing_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = boto3.client(
            "pricing",
            region_name=AWS_PRICING_API_REGION,
            config=Config(
                connect_timeout=3,
                read_timeout=_sdk_read_timeout(),
                retries={"max_attempts": 0},
            ),
        )
    return _CLIENT


def reset_client_for_tests() -> None:
    """Clear cached boto3 client (unit tests only)."""
    global _CLIENT
    _CLIENT = None


def fetch_hourly_via_sdk(sku: str, region: str) -> Optional[Decimal]:
    """Query On-Demand hourly USD via AWS SDK Pricing Query API.

    ``sku`` 是 ``default_products`` 的鍵；實際 Pricing API ServiceCode 可經
    ``service_code`` 覆寫（例如 NAT Gateway 掛在 AmazonEC2 之下）。
    """
    if not use_sdk_enabled():
        return None

    spec = _product_spec(sku)
    if spec is None:
        return None

    product_family = spec.get("product_family")
    if not isinstance(product_family, str):
        return None

    api_code = _api_service_code(sku, spec)

    try:
        attribute_filters, assumed_quantity, location_optional = _spec_meta(spec, region)
    except ValueError:
        return None

    filters = [{"Type": "TERM_MATCH", "Field": "productFamily", "Value": product_family}]
    if not location_optional:
        location = _location_for_region(region)
        if not location:
            return None
        filters.insert(0, {"Type": "TERM_MATCH", "Field": "location", "Value": location})
    for field, value in attribute_filters.items():
        filters.append({"Type": "TERM_MATCH", "Field": field, "Value": value})

    try:
        response = _get_pricing_client().get_products(
            ServiceCode=api_code,
            FormatVersion="aws_v1",
            Filters=filters,
        )
    except (BotoCoreError, ClientError) as exc:
        # NFR9.1: log type/code only — never raw exception text (may echo env).
        code = type(exc).__name__
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", code)
        logger.warning(
            "pricing SDK failed for %s(%s)@%s: %s",
            sku,
            api_code,
            region,
            code,
        )
        return None

    return parse_price_list_items(
        response.get("PriceList", []),
        product_family=product_family,
        attribute_filters=attribute_filters,
        assumed_quantity=assumed_quantity,
    )
