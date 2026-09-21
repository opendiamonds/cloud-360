"""Parse AWS Price List Query API ``get_products`` responses."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Optional

from cost.pricing_units import normalize_to_hourly


def parse_get_products_item(
    item: Mapping[str, object],
    *,
    product_family: str,
    attribute_filters: Mapping[str, str],
    assumed_quantity: Decimal = Decimal("1"),
) -> Optional[Decimal]:
    product = item.get("product")
    if not isinstance(product, dict):
        return None
    if product.get("productFamily") != product_family:
        return None
    attrs = product.get("attributes")
    if not isinstance(attrs, dict):
        return None
    for key, expected in attribute_filters.items():
        if attrs.get(key) != expected:
            return None
    terms = item.get("terms")
    if not isinstance(terms, dict):
        return None
    on_demand = terms.get("OnDemand")
    if not isinstance(on_demand, dict):
        return None
    for term in on_demand.values():
        if not isinstance(term, dict):
            continue
        dims = term.get("priceDimensions", {})
        if not isinstance(dims, dict):
            continue
        for dim in dims.values():
            if not isinstance(dim, dict):
                continue
            unit = dim.get("unit")
            usd = dim.get("pricePerUnit", {}).get("USD")
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


def parse_price_list_items(
    price_list: Iterable[object],
    *,
    product_family: str,
    attribute_filters: Mapping[str, str],
    assumed_quantity: Decimal = Decimal("1"),
) -> Optional[Decimal]:
    request_hit: Optional[Decimal] = None
    fallback: Optional[Decimal] = None
    for raw in price_list:
        item = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(item, dict):
            continue
        product = item.get("product")
        if not isinstance(product, dict):
            continue
        if product.get("productFamily") != product_family:
            continue
        attrs = product.get("attributes")
        if not isinstance(attrs, dict):
            continue
        for key, expected in attribute_filters.items():
            if attrs.get(key) != expected:
                break
        else:
            terms = item.get("terms")
            if not isinstance(terms, dict):
                continue
            on_demand = terms.get("OnDemand")
            if not isinstance(on_demand, dict):
                continue
            for term in on_demand.values():
                if not isinstance(term, dict):
                    continue
                dims = term.get("priceDimensions", {})
                if not isinstance(dims, dict):
                    continue
                for dim in dims.values():
                    if not isinstance(dim, dict):
                        continue
                    unit = dim.get("unit")
                    usd = dim.get("pricePerUnit", {}).get("USD")
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
                    if hourly is None or hourly <= 0:
                        continue
                    if unit in ("Request", "Requests"):
                        request_hit = hourly
                    elif fallback is None:
                        fallback = hourly
    return request_hit or fallback
