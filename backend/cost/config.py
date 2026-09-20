"""Load static YAML config at import time."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

_COST_DIR = Path(__file__).resolve().parent


def _load_yaml(name: str) -> Dict[str, Any]:
    path = _COST_DIR / name
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{name} must be a mapping")
    return data


COVERAGE_BY_CLOUD: Dict[str, str] = {
    row["cloud"]: row["mode"]
    for row in _load_yaml("pricing_coverage.yaml").get("coverage", [])
}

COVERAGE_LIST: List[Dict[str, str]] = _load_yaml("pricing_coverage.yaml").get(
    "coverage", []
)

PRICING_URLS = _load_yaml("pricing_urls.yaml")
_REGIONS_DOC = _load_yaml("supported_regions.yaml")
SUPPORTED_REGIONS: List[str] = list(_REGIONS_DOC.get("regions", []))
REGIONS_BY_CLOUD: Dict[str, List[str]] = {
    str(cloud): [str(r) for r in (regs or [])]
    for cloud, regs in (_REGIONS_DOC.get("by_cloud") or {}).items()
}
_AWS_LOC = _load_yaml("aws_region_locations.yaml")
AWS_REGION_LOCATIONS: Dict[str, str] = _AWS_LOC.get("locations", {})
AWS_USAGE_TYPE_PREFIXES: Dict[str, str] = _AWS_LOC.get("usage_type_prefixes", {})
AWS_PRICING_API_REGION: str = str(_AWS_LOC.get("pricing_api_region", "us-east-1"))
