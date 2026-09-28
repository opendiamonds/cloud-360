"""Parse AWS Price List Bulk offer JSON — no I/O."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping, Optional

from cost.pricing_units import normalize_to_hourly


def _match_attributes(attrs: Mapping[str, Any], filters: Mapping[str, str]) -> bool:
    for key, expected in filters.items():
        if attrs.get(key) != expected:
            return False
    return True


def _on_demand_hourly_usd(
    offer: Mapping[str, Any],
    sku: str,
    *,
    assumed_quantity: Decimal = Decimal("1"),
) -> Optional[Decimal]:
    on_demand = offer.get("terms", {}).get("OnDemand", {})
    term = on_demand.get(sku)
    if not isinstance(term, dict):
        return None
    for offer_term in term.values():
        if not isinstance(offer_term, dict):
            continue
        dimensions = offer_term.get("priceDimensions", {})
        if not isinstance(dimensions, dict):
            continue
        for dimension in dimensions.values():
            if not isinstance(dimension, dict):
                continue
            unit = dimension.get("unit")
            usd = dimension.get("pricePerUnit", {}).get("USD")
            if usd is None or unit is None:
                continue
            try:
                hourly = normalize_to_hourly(
                    str(unit),
                    Decimal(str(usd)),
                    assumed_quantity=assumed_quantity,
                )
            except (InvalidOperation, ValueError):
                continue
            if hourly is not None:
                return hourly
    return None


def parse_on_demand_hourly(
    offer: Mapping[str, Any],
    *,
    product_family: str,
    attribute_filters: Mapping[str, str],
    assumed_quantity: Decimal = Decimal("1"),
) -> Optional[Decimal]:
    """Return first On-Demand USD rate matching product filters, normalized to hourly."""
    products = offer.get("products")
    if not isinstance(products, dict):
        return None

    for sku, product in products.items():
        if not isinstance(product, dict):
            continue
        if product.get("productFamily") != product_family:
            continue
        attrs = product.get("attributes")
        if not isinstance(attrs, dict):
            continue
        if not _match_attributes(attrs, attribute_filters):
            continue
        hourly = _on_demand_hourly_usd(
            offer,
            str(sku),
            assumed_quantity=assumed_quantity,
        )
        if hourly is not None:
            return hourly
    return None
