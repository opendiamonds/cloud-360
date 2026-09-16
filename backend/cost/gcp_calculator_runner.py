"""Playwright runner for Google Cloud Pricing Calculator."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cost.config import CALCULATOR_GCP_PRODUCTS, CALCULATOR_GCP_REGIONS
from cost.gcp_calculator_product_resolver import (
    GcpCalculatorProductTarget,
    ai_suggest_calculator_search_terms,
    filter_visible_products,
    resolve_gcp_calculator_product,
    search_terms_for_item,
)
from cost.sku_ai_resolver import sku_ai_infer_enabled
from services.llm_provider import llm_auth_ready

logger = logging.getLogger(__name__)

GCP_CALCULATOR_URL = "https://cloud.google.com/products/calculator"
ALLOWED_HOSTS = frozenset({"cloud.google.com"})
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "gcp_calculator_stub.json"

OFFICIAL_EXPORT_MIME = "text/csv"
OFFICIAL_EXPORT_FILENAME = "gcp-calculator-estimate.csv"

_MAX_SEARCH_ATTEMPTS_PER_ITEM = 4


def _gcp_timeout_ms(item_count: int = 1) -> int:
    """總操作預算（ms）。多產品時依數量放寬（含搜尋重試），env 值為下限。"""
    base = int(float(os.environ.get("COST_GCP_CALCULATOR_TIMEOUT", "180")) * 1000)
    # 實測每產品約 15–25s（含 modal／搜尋重試）；預留 AI 重試與網路延遲
    per_item_ms = 28_000
    overhead_ms = 60_000
    needed = max(1, item_count) * per_item_ms + overhead_ms
    return max(base, needed)


def _calculator_ai_fallback_enabled() -> bool:
    if os.environ.get("COST_PRICING_AGENT_SKIP_LLM", "").strip() == "1":
        return False
    return sku_ai_infer_enabled() and llm_auth_ready()


def _remaining_ms(deadline: float) -> int:
    return max(5_000, int((deadline - time.monotonic()) * 1000))


def _playwright_timeout_message(item_count: int = 0) -> str:
    budget_s = _gcp_timeout_ms(max(1, item_count)) // 1000
    return (
        "GCP Calculator 頁面操作逾時"
        f"（目前預算約 {budget_s}s／{max(1, item_count)} 個產品；"
        "可將 COST_GCP_CALCULATOR_TIMEOUT 調大，例如 300 或 600）"
    )


def _timeout_incomplete_message(completed: int, total: int) -> str:
    budget_s = _gcp_timeout_ms(total) // 1000
    return (
        f"GCP Calculator 操作逾時（已完成 {completed}/{total} 個產品；"
        f"目前預算約 {budget_s}s；"
        "可將 COST_GCP_CALCULATOR_TIMEOUT 調大，例如 300 或 600）"
    )
_ADD_MODAL_SELECTOR = '[data-inject-content-controller="true"]'
_PRODUCT_SEARCH_PLACEHOLDER = "Search by product name"

_TOTAL_RE = re.compile(r"[\$€£]?\s*([\d,]+(?:\.\d{2})?)")
_LINE_PRICE_RE = re.compile(r"^\$[\d,]+\.\d{2}")


class GcpCalculatorError(Exception):
    """GCP Calculator automation failed."""


@dataclass(frozen=True)
class CalculatorLineItem:
    map_key: str
    quantity: int = 1
    mxcell_id: str | None = None
    label: str | None = None


@dataclass
class GcpCalculatorResult:
    total_usd: Decimal
    currency: str = "USD"
    assumptions: list[str] = field(default_factory=list)
    source_url: str = GCP_CALCULATOR_URL
    line_items: list[dict[str, Any]] = field(default_factory=list)
    calculator_lines: list[dict[str, Any]] = field(default_factory=list)


def calculator_stub_enabled() -> bool:
    return os.environ.get("COST_GCP_CALCULATOR_STUB", "").strip() == "1"


def calculator_region_value(region: str) -> str:
    key = (region or "").strip()
    mapped = CALCULATOR_GCP_REGIONS.get(key)
    if not mapped:
        raise GcpCalculatorError(
            f"region {key!r} 無 GCP Calculator 對照（見 calculator_gcp_regions.yaml）"
        )
    return mapped


def _assert_url_allowed(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise GcpCalculatorError(f"URL host not allowlisted: {host}")


def _parse_money(text: str) -> Decimal:
    match = _TOTAL_RE.search((text or "").replace("\u00a0", " "))
    if not match:
        raise GcpCalculatorError(f"無法解析 Estimate 金額：{text!r}")
    try:
        return Decimal(match.group(1).replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise GcpCalculatorError(f"無法解析 Estimate 金額：{text!r}") from exc


def _normalize_line_items(raw_items: list[dict[str, Any]]) -> list[CalculatorLineItem]:
    if not raw_items:
        raise GcpCalculatorError("line_items 不可為空")
    merged: dict[str, CalculatorLineItem] = {}
    for row in raw_items:
        key = str(row.get("map_key") or row.get("sku") or "").strip()
        if not key or key not in CALCULATOR_GCP_PRODUCTS:
            raise GcpCalculatorError(f"未知 map_key：{key!r}")
        qty = int(row.get("quantity") or CALCULATOR_GCP_PRODUCTS[key].get("default_quantity") or 1)
        if qty < 1:
            raise GcpCalculatorError(f"quantity 必須 >= 1：{key}")
        prev = merged.get(key)
        label = str(row.get("label") or "").strip() or None
        mxcell_id = row.get("mxcell_id")
        if prev:
            merged_label = prev.label or ""
            if label:
                parts = [p.strip() for p in merged_label.split(",") if p.strip()]
                if label not in parts:
                    parts.append(label)
                merged_label = ", ".join(parts)
            merged[key] = CalculatorLineItem(
                map_key=key,
                quantity=prev.quantity + qty,
                mxcell_id=prev.mxcell_id or mxcell_id,
                label=merged_label or None,
            )
        else:
            merged[key] = CalculatorLineItem(
                map_key=key,
                quantity=qty,
                mxcell_id=mxcell_id,
                label=label,
            )
    return list(merged.values())


def _assumptions_for(region: str, items: list[CalculatorLineItem]) -> list[str]:
    lines = [f"Region: {region}", f"Products: {len(items)}"]
    for item in items:
        spec = CALCULATOR_GCP_PRODUCTS[item.map_key]
        lines.append(
            f"{spec.get('calculator_search')} × {item.quantity} "
            f"({spec.get('quantity_unit', 'unit')})"
        )
    return lines


def run_gcp_calculator_estimate(
    region: str,
    line_items: list[dict[str, Any]],
    *,
    stub: bool | None = None,
) -> GcpCalculatorResult:
    region = (region or "").strip()
    if not region:
        raise GcpCalculatorError("region 必填")

    items = _normalize_line_items(line_items)
    assumptions = _assumptions_for(region, items)
    use_stub = calculator_stub_enabled() if stub is None else stub

    if use_stub:
        return _run_stub(region, items, assumptions)

    return _run_live(region, items, assumptions)


def export_gcp_calculator_csv(
    region: str,
    line_items: list[dict[str, Any]],
    *,
    stub: bool | None = None,
) -> tuple[bytes, str, str]:
    region = (region or "").strip()
    if not region:
        raise GcpCalculatorError("region 必填")

    items = _normalize_line_items(line_items)
    use_stub = calculator_stub_enabled() if stub is None else stub
    safe_region = re.sub(r"[^\w\-]+", "-", region).strip("-") or "region"
    default_name = f"gcp-calculator-estimate-{safe_region}.csv"

    if use_stub:
        result = _run_stub(region, items, _assumptions_for(region, items))
        return _stub_csv_export(region, items, result.total_usd), default_name, GCP_CALCULATOR_URL

    return _export_live_csv(region, items, default_name)


def _load_stub() -> dict[str, Any]:
    if not FIXTURE_PATH.is_file():
        raise GcpCalculatorError(f"找不到 stub fixture：{FIXTURE_PATH}")
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _run_stub(
    region: str,
    items: list[CalculatorLineItem],
    assumptions: list[str],
) -> GcpCalculatorResult:
    payload = _load_stub()
    total = Decimal(str(payload.get("total_usd") or 0)).quantize(Decimal("0.01"))
    stub_lines = payload.get("lines") or []
    calculator_lines: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        src = stub_lines[idx] if idx < len(stub_lines) else stub_lines[-1] if stub_lines else {}
        spec = CALCULATOR_GCP_PRODUCTS[item.map_key]
        calculator_lines.append(
            {
                "map_key": item.map_key,
                "mxcell_id": item.mxcell_id,
                "label": item.label,
                "product_name": str(src.get("product_name") or spec.get("calculator_search")),
                "specification": str(
                    src.get("specification")
                    or f"{spec.get('calculator_search')} × {item.quantity} (stub)"
                ),
                "monthly_usd": float(
                    src.get("monthly_usd")
                    or (total / len(items)).quantize(Decimal("0.01"))
                ),
            }
        )
    return GcpCalculatorResult(
        total_usd=total,
        assumptions=assumptions + ["mode: stub fixture"],
        source_url=f"file://{FIXTURE_PATH}",
        line_items=[{"map_key": i.map_key, "quantity": i.quantity} for i in items],
        calculator_lines=calculator_lines,
    )


def _stub_csv_export(
    region: str, items: list[CalculatorLineItem], total: Decimal
) -> bytes:
    rows = [
        "service_display_name,name,quantity,region,total_price_usd,notes",
        f"Estimate Total,,,,{total},stub",
    ]
    for item in items:
        spec = CALCULATOR_GCP_PRODUCTS[item.map_key]
        rows.append(
            f"{spec.get('calculator_search')},stub,{item.quantity},{region},,"
        )
    return "\n".join(rows).encode("utf-8")


def _dismiss_banners(page) -> None:
    for label in ("Dismiss", "Accept all", "Accept", "I agree"):
        btn = page.get_by_role("button", name=re.compile(label, re.I))
        if btn.count() == 0:
            continue
        try:
            if btn.first.is_visible():
                btn.first.click(timeout=3000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def _modal_is_open(page) -> bool:
    modal = page.locator(_ADD_MODAL_SELECTOR).first
    try:
        return modal.count() > 0 and modal.is_visible()
    except Exception:
        return False


def _ensure_modal_closed(page, timeout_ms: int) -> None:
    if not _modal_is_open(page):
        return
    for _ in range(3):
        _close_add_modal(page, timeout_ms)
        page.wait_for_timeout(250)
        if not _modal_is_open(page):
            return


def _open_add_product_modal(page, timeout_ms: int) -> None:
    _ensure_modal_closed(page, timeout_ms)
    page.evaluate(
        """() => {
          const btns = [...document.querySelectorAll('button')].filter(
            (b) => /add to estimate/i.test((b.innerText || ''))
          );
          if (btns.length) btns[btns.length - 1].click();
        }"""
    )
    page.wait_for_timeout(800)
    search = page.locator(f'input[placeholder="{_PRODUCT_SEARCH_PLACEHOLDER}"]').first
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            search.wait_for(state="visible", timeout=min(timeout_ms, 12_000))
            return
        except Exception as exc:
            last_error = exc
            page.evaluate(
                """() => {
                  const btns = [...document.querySelectorAll('button')].filter(
                    (b) => /add to estimate/i.test((b.innerText || ''))
                  );
                  if (btns.length) btns[btns.length - 1].click();
                }"""
            )
            page.wait_for_timeout(600)
    if last_error:
        raise last_error


def _close_add_modal(page, timeout_ms: int = 10_000) -> None:
    """關閉 Add to estimate 模態（可能需關閉多層：產品設定 → 搜尋列表）。"""
    for _ in range(3):
        if not _modal_is_open(page):
            return
        close_btn = page.get_by_role("button", name=re.compile(r"Close dialog", re.I))
        if close_btn.count():
            try:
                if close_btn.first.is_visible():
                    close_btn.first.click(timeout=min(timeout_ms, 5_000))
                    page.wait_for_timeout(350)
                    continue
            except Exception:
                pass
        page.keyboard.press("Escape")
        page.wait_for_timeout(350)


def _close_modal(page) -> None:
    _close_add_modal(page, 10_000)


def _config_panel_visible(page) -> bool:
    return bool(
        page.evaluate(
            """() => {
              const modal = document.querySelector('[data-inject-content-controller="true"]');
              const text = modal?.innerText || '';
              return /Service type|Service cost updated|Number of|Amount of/i.test(text);
            }"""
        )
    )


def _list_modal_product_titles(page) -> list[str]:
    titles = page.evaluate(
        """() => {
          const modal = document.querySelector('[data-inject-content-controller="true"]');
          if (!modal) return [];
          const skip = new Set([
            'Search by product name',
            'Products',
            'Add to this estimate',
            'Add to estimate',
            'Close dialog',
            'Sort by most popular',
            'arrow_drop_down',
            'search',
            'add',
          ]);
          const out = [];
          const seen = new Set();
          for (const el of modal.querySelectorAll('h2,h3')) {
            const t = (el.innerText || '').trim().split('\\n')[0].trim();
            if (!t || t.length > 60 || skip.has(t)) continue;
            if (!el.offsetParent) continue;
            if (seen.has(t)) continue;
            seen.add(t);
            out.push(t);
          }
          return out;
        }"""
    )
    return [str(t).strip() for t in (titles or []) if str(t).strip()]


def _list_visible_products(page) -> list[str]:
    return filter_visible_products(_list_modal_product_titles(page))


def _collect_calculator_catalog(page, timeout_ms: int) -> list[str]:
    """清空搜尋以取得 Calculator 產品目錄（供 AI 建議搜尋字串）。"""
    _search_product(page, "", timeout_ms)
    page.wait_for_timeout(600)
    return _list_visible_products(page)


def _search_shows_no_results(page) -> bool:
    return bool(
        page.evaluate(
            """() => {
              const modal = document.querySelector('[data-inject-content-controller="true"]');
              return /No products matched your search/i.test(modal?.innerText || '');
            }"""
        )
    )


def _estimate_line_item_count(page) -> int:
    """Estimate 面板上的產品列數（edit 列優先，較 Delete group 準確）。"""
    return int(
        page.evaluate(
            """() => {
              const text = document.body.innerText || '';
              const start = text.indexOf('Cost details');
              const end = text.indexOf('ESTIMATED COST');
              const section = start >= 0 && end > start ? text.slice(start, end) : text;
              const edits = (section.match(/edit\\s*\\n\\s*\\$[\\d,]+\\.\\d{2}/g) || []).length;
              if (edits > 0) return edits;
              const deleteGroups = (section.match(/Delete group/g) || []).length;
              if (deleteGroups > 0) return deleteGroups;
              const names = [
                'Compute Engine','Google Kubernetes Engine','Kubernetes Engine','Cloud Run',
                'Cloud SQL','Cloud Storage','Cloud DNS','Networking','Cloud Operations',
                'Cloud Load Balancing','Cloud CDN','BigQuery','Firestore','Vertex AI',
                'Cloud Monitoring','Secret Manager','Apigee'
              ];
              let count = 0;
              for (const name of names) {
                const re = new RegExp(
                  '^' + name.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') +
                  '\\\\s*\\\\n\\\\$[\\\\d,]+\\\\.\\\\d{2}', 'm'
                );
                if (re.test(text)) count += 1;
              }
              return count;
            }"""
        )
    )


def _wait_for_count_at_least(page, baseline: int, timeout_ms: int) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if _estimate_line_item_count(page) > baseline:
            return True
        page.wait_for_timeout(150)
    return False


def _click_product_title(page, title: str) -> bool:
    return bool(
        page.evaluate(
            """(name) => {
              const modal = document.querySelector('[data-inject-content-controller="true"]');
              if (!modal) return false;
              const matches = [...modal.querySelectorAll('h2,h3')].filter(
                (node) => (node.innerText || '').trim().split('\\n')[0].trim() === name && node.offsetParent
              );
              if (!matches.length) return false;
              matches.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
              matches[0].click();
              return true;
            }""",
            title,
        )
    )


def _search_product(page, calculator_search: str, timeout_ms: int) -> None:
    search = page.locator(f'input[placeholder="{_PRODUCT_SEARCH_PLACEHOLDER}"]').first
    search.wait_for(state="visible", timeout=min(timeout_ms, 15_000))
    search.fill("")
    page.wait_for_timeout(100)
    search.fill(calculator_search)
    poll_ms = min(timeout_ms, 4_000)
    deadline = time.monotonic() + poll_ms / 1000
    while time.monotonic() < deadline:
        if _list_visible_products(page) or _search_shows_no_results(page):
            return
        page.wait_for_timeout(150)


def _set_service_type_if_present(page, service_type: str | None, timeout_ms: int) -> None:
    if not service_type:
        return
    combos = page.locator('[role="combobox"]').filter(has_text=re.compile(r"Service type", re.I))
    target = combos.first if combos.count() else page.locator('[role="combobox"]').first
    try:
        if target.count() == 0 or not target.is_visible():
            return
    except Exception:
        return
    target.click(timeout=min(timeout_ms, 8_000))
    page.wait_for_timeout(350)
    option = page.locator('[role="option"]').filter(
        has_text=re.compile(re.escape(service_type), re.I)
    ).first
    if option.count() == 0:
        logger.warning("GCP Calculator 找不到 Service type：%s", service_type)
        page.keyboard.press("Escape")
        return
    option.click(timeout=min(timeout_ms, 8_000))
    page.wait_for_timeout(350)


def _open_product_config(
    page,
    item: CalculatorLineItem,
    timeout_ms: int,
) -> GcpCalculatorProductTarget:
    visible = _list_visible_products(page)
    if not visible:
        raise GcpCalculatorError(
            f"GCP Calculator 搜尋無結果：{search_terms_for_item(item.map_key, item.label)[0]!r}"
        )
    try:
        target = resolve_gcp_calculator_product(
            map_key=item.map_key,
            visible_products=visible,
            diagram_label=item.label,
        )
    except ValueError as exc:
        raise GcpCalculatorError(str(exc)) from exc
    if not _click_product_title(page, target.click_title):
        raise GcpCalculatorError(
            f"無法點擊 GCP Calculator 產品：{target.click_title!r}"
        )
    panel_deadline = time.monotonic() + 2.0
    while time.monotonic() < panel_deadline:
        if _config_panel_visible(page):
            break
        page.wait_for_timeout(150)
    if _config_panel_visible(page):
        _set_service_type_if_present(page, target.service_type, timeout_ms)
    if target.note:
        logger.info(target.note)
    return target


def _set_region_if_present(page, region_code: str, timeout_ms: int) -> None:
    combobox = page.locator('[role="combobox"]').filter(
        has_text=re.compile(r"Region|us-|europe-|asia-", re.I)
    )
    if combobox.count() == 0:
        return
    target = combobox.last
    try:
        if not target.is_visible():
            return
    except Exception:
        return
    target.click(timeout=min(timeout_ms, 8_000))
    page.wait_for_timeout(350)
    option = page.locator('[role="option"]').filter(
        has_text=re.compile(re.escape(f"({region_code})"), re.I)
    ).first
    if option.count() == 0:
        option = page.locator('[role="option"]').filter(
            has_text=re.compile(re.escape(region_code), re.I)
        ).first
    if option.count() == 0:
        logger.warning("GCP Calculator 找不到 region 選項：%s", region_code)
        page.keyboard.press("Escape")
        return
    option.click(timeout=min(timeout_ms, 8_000))
    page.wait_for_timeout(350)


def _set_quantity_inputs(page, item: CalculatorLineItem, timeout_ms: int) -> None:
    unit = CALCULATOR_GCP_PRODUCTS[item.map_key].get("quantity_unit", "")
    if unit not in ("vm_instance", "node"):
        return
    qty_inputs = page.locator('input[type="number"]:visible')
    if qty_inputs.count() == 0:
        return
    qty_inputs.first.fill(str(item.quantity), timeout=min(timeout_ms, 10_000))
    page.wait_for_timeout(500)


def _add_product_to_estimate(
    page,
    item: CalculatorLineItem,
    region: str,
    deadline: float,
) -> bool:
    calc_region = calculator_region_value(region)
    tried_terms: list[str] = []
    last_error: str | None = None
    search_terms = search_terms_for_item(item.map_key, item.label)

    def _attempt(search_term: str) -> bool:
        nonlocal last_error
        if search_term in tried_terms:
            return False
        if time.monotonic() >= deadline:
            last_error = "GCP Calculator 操作逾時（填寫產品階段）"
            return False
        tried_terms.append(search_term)
        step_timeout = _remaining_ms(deadline)
        before_count = _estimate_line_item_count(page)
        try:
            _open_add_product_modal(page, step_timeout)
            _search_product(page, search_term, step_timeout)
        except Exception as exc:
            last_error = str(exc)
            _close_add_modal(page, step_timeout)
            return False
        visible = _list_visible_products(page)
        if not visible:
            last_error = f"GCP Calculator 搜尋無結果：{search_term!r}"
            _close_add_modal(page, step_timeout)
            return False
        try:
            _open_product_config(page, item, step_timeout)
            if _config_panel_visible(page):
                _set_region_if_present(page, calc_region, step_timeout)
                _set_quantity_inputs(page, item, step_timeout)
            _close_add_modal(page, step_timeout)
            if _wait_for_count_at_least(page, before_count, min(step_timeout, 4_000)):
                return True
            last_error = f"產品已點選但未出現在 Estimate：{item.label or item.map_key}"
            return False
        except GcpCalculatorError as exc:
            last_error = str(exc)
            _close_add_modal(page, step_timeout)
            return False

    for search_term in search_terms[:_MAX_SEARCH_ATTEMPTS_PER_ITEM]:
        if _attempt(search_term):
            return True

    if _calculator_ai_fallback_enabled() and time.monotonic() < deadline:
        step_timeout = _remaining_ms(deadline)
        try:
            _open_add_product_modal(page, step_timeout)
            catalog = _collect_calculator_catalog(page, step_timeout)
            _close_add_modal(page, step_timeout)
        except Exception as exc:
            last_error = str(exc)
            catalog = []
        if catalog:
            ai_terms = ai_suggest_calculator_search_terms(
                diagram_label=item.label,
                map_key=item.map_key,
                tried_terms=tried_terms,
                catalog_titles=catalog,
            )
            for search_term in ai_terms[:_MAX_SEARCH_ATTEMPTS_PER_ITEM]:
                if _attempt(search_term):
                    return True

    for search_term in search_terms[_MAX_SEARCH_ATTEMPTS_PER_ITEM:]:
        if _attempt(search_term):
            return True

    label = item.label or item.map_key
    raise GcpCalculatorError(last_error or f"找不到 GCP Calculator 產品：{label!r}")


def _fill_calculator_page(
    page,
    region: str,
    items: list[CalculatorLineItem],
    deadline: float,
) -> None:
    failed: list[str] = []
    completed = 0
    total = len(items)
    logger.info(
        "GCP Calculator 開始填表：%s 個產品，總預算 %ss",
        total,
        int((deadline - time.monotonic())),
    )
    for item in items:
        if time.monotonic() >= deadline:
            raise GcpCalculatorError(_timeout_incomplete_message(completed, total))
        try:
            _add_product_to_estimate(page, item, region, deadline)
            completed += 1
            logger.info(
                "GCP Calculator 已加入 %s/%s：%s",
                completed,
                total,
                item.label or item.map_key,
            )
        except GcpCalculatorError as exc:
            failed.append(f"{item.label or item.map_key}（{exc}）")
    if failed:
        preview = "；".join(failed[:5])
        extra = f" 等 {len(failed)} 項" if len(failed) > 5 else ""
        raise GcpCalculatorError(f"GCP Calculator 無法加入部分產品：{preview}{extra}")
    _wait_for_estimate_total(page, _remaining_ms(deadline))


def _wait_for_estimate_total(page, timeout_ms: int) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if _try_read_estimate_total(page) is not None:
            page.wait_for_timeout(300)
            return
        page.wait_for_timeout(200)
    raise GcpCalculatorError("無法讀取 GCP Calculator Estimated cost")


def _estimate_product_count(page) -> int:
    return _estimate_line_item_count(page)


def _wait_for_estimate_ready(page, expected_products: int, timeout_ms: int) -> None:
    if expected_products < 1:
        return
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        total = _try_read_estimate_total(page)
        count = _estimate_line_item_count(page)
        if total is not None and count >= expected_products:
            page.wait_for_timeout(300)
            return
        page.wait_for_timeout(200)
    raise GcpCalculatorError(
        f"GCP Calculator Estimate 僅有 {_estimate_line_item_count(page)}/{expected_products} 個產品明細"
    )


def _try_read_estimate_total(page) -> Decimal | None:
    try:
        return _parse_money(_read_estimate_total_text(page))
    except GcpCalculatorError:
        return None


def _read_estimate_total_text(page) -> str:
    text = page.evaluate(
        """() => {
          const body = document.body.innerText || '';
          const idx = body.indexOf('ESTIMATED COST');
          if (idx < 0) return '';
          return body.slice(idx, idx + 80);
        }"""
    )
    for line in (text or "").splitlines():
        line = line.strip()
        if _TOTAL_RE.search(line) and line not in ("--", "-"):
            return line
    raise GcpCalculatorError("無法讀取 GCP Calculator Estimated cost")


def _read_estimate_lines(page) -> list[dict[str, Any]]:
    raw = page.evaluate(
        """() => {
          const body = document.body.innerText || '';
          const names = [
            'Compute Engine','Google Kubernetes Engine','Kubernetes Engine','Cloud Run','Cloud SQL','Cloud Storage','Cloud DNS','Networking','Cloud Operations','Cloud Load Balancing','Cloud CDN','BigQuery','Firestore','Vertex AI','Cloud Monitoring','Secret Manager','Apigee','Apigee API Management'
          ];
          const rows = [];
          for (const name of names) {
            const escaped = name.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
            const re = new RegExp('^' + escaped + '\\\\s*\\\\n\\\\$([\\\\d,]+\\\\.\\\\d{2})', 'm');
            const m = body.match(re);
            if (m) rows.push({ product_name: name, monthly_text: '$' + m[1] });
          }
          if (rows.length) return rows;
          const start = body.indexOf('Cost details');
          const end = body.indexOf('ESTIMATED COST');
          const section = start >= 0 && end > start ? body.slice(start, end) : body;
          const prices = [...section.matchAll(/edit\\s*\\n\\s*\\$([\\d,]+\\.\\d{2})/g)];
          return prices.map((m) => ({ product_name: '', monthly_text: '$' + m[1] }));
        }"""
    )
    parsed: list[dict[str, Any]] = []
    for row in raw or []:
        parsed.append(
            {
                "product_name": str(row.get("product_name") or ""),
                "specification": str(row.get("product_name") or ""),
                "monthly_usd": float(_parse_money(str(row.get("monthly_text") or ""))),
            }
        )
    return parsed


def _map_key_for_product_name(product_name: str) -> str | None:
    name = (product_name or "").casefold()
    if name == "kubernetes engine":
        name = "google kubernetes engine"
    if name == "networking":
        return "Networking"
    if name in ("cloud operations", "cloud monitoring"):
        return "CloudObservability"
    if name == "apigee":
        return "Apigee"
    for key, spec in CALCULATOR_GCP_PRODUCTS.items():
        search = str(spec.get("calculator_search") or "").casefold()
        if search and (search in name or name in search):
            return key
        short = search.split("(")[0].strip()
        if short and short in name:
            return key
    return None


def _attach_item_metadata(
    estimate_lines: list[dict[str, Any]],
    items: list[CalculatorLineItem],
) -> list[dict[str, Any]]:
    if not estimate_lines:
        return []

    used_items: set[int] = set()
    enriched: list[dict[str, Any]] = []

    for idx, row in enumerate(estimate_lines):
        out = dict(row)
        map_key = _map_key_for_product_name(out.get("product_name", ""))
        item_idx = None
        if map_key:
            for i, item in enumerate(items):
                if i in used_items:
                    continue
                if item.map_key == map_key:
                    item_idx = i
                    break
        elif not out.get("product_name") and idx < len(items):
            item_idx = idx
            map_key = items[idx].map_key
        elif len(used_items) < len(items):
            for i in range(len(items)):
                if i not in used_items:
                    item_idx = i
                    map_key = items[i].map_key
                    break

        if item_idx is not None:
            used_items.add(item_idx)
            item = items[item_idx]
            out["map_key"] = item.map_key
            out["mxcell_id"] = item.mxcell_id
            if item.label:
                out["label"] = item.label
            spec = CALCULATOR_GCP_PRODUCTS[item.map_key]
            if not out.get("product_name"):
                out["product_name"] = str(spec.get("calculator_search") or item.map_key)
            out["specification"] = (
                f"{spec.get('calculator_search')} × {item.quantity} "
                f"({spec.get('quantity_unit', 'unit')})"
            )
        elif map_key:
            out["map_key"] = map_key

        enriched.append(out)

    return enriched


def _download_official_csv(page, timeout_ms: int) -> tuple[bytes, str, str]:
    btn = page.get_by_role("button", name=re.compile(r"Download estimate as", re.I))
    btn.first.wait_for(state="visible", timeout=min(timeout_ms, 20_000))
    btn.first.scroll_into_view_if_needed()
    with page.expect_download(timeout=min(timeout_ms, 60_000)) as download_info:
        btn.first.click()
    download = download_info.value
    path = download.path()
    if not path:
        raise GcpCalculatorError("GCP Calculator CSV 下載失敗")
    data = Path(path).read_bytes()
    filename = download.suggested_filename or OFFICIAL_EXPORT_FILENAME
    source_url = download.url or GCP_CALCULATOR_URL
    if not data.strip():
        raise GcpCalculatorError(f"官方 CSV 為空：{filename!r}")
    return data, filename, source_url


def _export_live_csv(
    region: str,
    items: list[CalculatorLineItem],
    default_filename: str,
) -> tuple[bytes, str, str]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise GcpCalculatorError(
            "Playwright 未安裝；本機請 pip install playwright && playwright install chromium"
        ) from exc

    _assert_url_allowed(GCP_CALCULATOR_URL)
    timeout_ms = _gcp_timeout_ms(len(items))
    deadline = time.monotonic() + timeout_ms / 1000

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = context.new_page()
            page.goto(GCP_CALCULATOR_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)
            _dismiss_banners(page)
            _fill_calculator_page(page, region, items, deadline)
            export_bytes, filename, source_url = _download_official_csv(
                page, _remaining_ms(deadline)
            )
        except PlaywrightTimeout as exc:
            raise GcpCalculatorError(_playwright_timeout_message(len(items))) from exc
        finally:
            browser.close()

    return export_bytes, filename or default_filename, source_url


def _run_live(
    region: str,
    items: list[CalculatorLineItem],
    assumptions: list[str],
) -> GcpCalculatorResult:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise GcpCalculatorError(
            "Playwright 未安裝；本機請 pip install playwright && playwright install chromium"
        ) from exc

    _assert_url_allowed(GCP_CALCULATOR_URL)
    timeout_ms = _gcp_timeout_ms(len(items))
    deadline = time.monotonic() + timeout_ms / 1000

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, locale="en-US")
            page.goto(GCP_CALCULATOR_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)
            _dismiss_banners(page)
            _fill_calculator_page(page, region, items, deadline)
            total = _parse_money(_read_estimate_total_text(page))
            raw_lines = _read_estimate_lines(page)
            calculator_lines = _attach_item_metadata(raw_lines, items)
        except PlaywrightTimeout as exc:
            raise GcpCalculatorError(_playwright_timeout_message(len(items))) from exc
        finally:
            browser.close()

    return GcpCalculatorResult(
        total_usd=total,
        assumptions=assumptions + ["mode: live playwright"],
        source_url=GCP_CALCULATOR_URL,
        line_items=[{"map_key": i.map_key, "quantity": i.quantity} for i in items],
        calculator_lines=calculator_lines,
    )
