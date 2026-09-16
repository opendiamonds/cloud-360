"""Playwright runner for Azure Pricing Calculator (ADR-C1-10)."""

from __future__ import annotations

import io
import logging
import os
import re
import time
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cost.config import CALCULATOR_AZURE_PRODUCTS, CALCULATOR_AZURE_REGIONS

logger = logging.getLogger(__name__)

AZURE_CALCULATOR_URL = "https://azure.microsoft.com/en-us/pricing/calculator/"
ALLOWED_HOSTS = frozenset({"azure.microsoft.com"})
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "azure_calculator_stub.html"

OFFICIAL_EXPORT_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
OFFICIAL_EXPORT_FILENAME = "ExportedEstimate.xlsx"

PRODUCT_SEARCH_SELECTOR = 'input[aria-label="Search products"]'
ESTIMATE_TOTAL_SELECTOR = ".estimate-total"
REGION_SELECT_SELECTOR = 'select[name="region"]'

_TOTAL_RE = re.compile(r"[\$€£]?\s*([\d,]+(?:\.\d{2})?)")
_MONTHLY_LINE_RE = re.compile(r"Monthly:\s*(\$[\d,]+\.\d{2})", re.I)
_SAVED_ESTIMATES_TAB_RE = re.compile(r"saved estimates?", re.I)
_GO_TO_PRODUCT_SELECTOR_RE = re.compile(r"go to product selector", re.I)
_PRODUCTS_TAB_RE = re.compile(r"^Products$", re.I)
_EXPORT_BUTTON_RE = re.compile(r"^Export$", re.I)


class AzureCalculatorError(Exception):
    """Calculator automation failed (selector, navigation, parse)."""


@dataclass(frozen=True)
class CalculatorLineItem:
    map_key: str
    quantity: int = 1
    mxcell_id: str | None = None
    label: str | None = None


@dataclass
class AzureCalculatorResult:
    total_usd: Decimal
    currency: str = "USD"
    assumptions: list[str] = field(default_factory=list)
    source_url: str = AZURE_CALCULATOR_URL
    line_items: list[dict[str, Any]] = field(default_factory=list)
    calculator_lines: list[dict[str, Any]] = field(default_factory=list)
    export_bytes: bytes | None = None
    export_filename: str | None = None
    export_mime: str | None = None
    export_source_url: str | None = None


def calculator_stub_enabled() -> bool:
    return os.environ.get("COST_AZURE_CALCULATOR_STUB", "").strip() == "1"


def calculator_region_value(arm_region: str) -> str:
    """Map armRegionName → Calculator `<select name=region>` value."""
    key = (arm_region or "").strip()
    mapped = CALCULATOR_AZURE_REGIONS.get(key)
    if not mapped:
        raise AzureCalculatorError(
            f"region {key!r} 無 Calculator 對照（見 calculator_azure_regions.yaml）"
        )
    return mapped


def _assert_url_allowed(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS and not url.startswith("file:"):
        raise AzureCalculatorError(f"URL host not allowlisted: {host}")


def _parse_money(text: str) -> Decimal:
    match = _TOTAL_RE.search((text or "").replace("\u00a0", " "))
    if not match:
        raise AzureCalculatorError(f"無法解析 Estimate 金額：{text!r}")
    try:
        return Decimal(match.group(1).replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise AzureCalculatorError(f"無法解析 Estimate 金額：{text!r}") from exc


def _normalize_line_items(raw_items: list[dict[str, Any]]) -> list[CalculatorLineItem]:
    if not raw_items:
        raise AzureCalculatorError("line_items 不可為空")
    merged: dict[str, CalculatorLineItem] = {}
    for row in raw_items:
        key = str(row.get("map_key") or row.get("sku") or "").strip()
        if not key or key not in CALCULATOR_AZURE_PRODUCTS:
            raise AzureCalculatorError(f"未知 map_key：{key!r}")
        qty = int(row.get("quantity") or CALCULATOR_AZURE_PRODUCTS[key].get("default_quantity") or 1)
        if qty < 1:
            raise AzureCalculatorError(f"quantity 必須 >= 1：{key}")
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
    calc_region = calculator_region_value(region)
    lines = [f"Region: {region} → calculator={calc_region}", f"Products: {len(items)}"]
    for item in items:
        spec = CALCULATOR_AZURE_PRODUCTS[item.map_key]
        lines.append(
            f"{spec.get('calculator_search')} × {item.quantity} ({spec.get('quantity_unit', 'unit')})"
        )
    return lines


def run_azure_calculator_estimate(
    region: str,
    line_items: list[dict[str, Any]],
    *,
    stub: bool | None = None,
) -> AzureCalculatorResult:
    """
    模擬使用者在 Azure Pricing Calculator 填寫並讀取 Estimate 總價。

    stub=True 或 COST_AZURE_CALCULATOR_STUB=1 時讀取本機 fixture（CI 用）。
    """
    region = (region or "").strip()
    if not region:
        raise AzureCalculatorError("region 必填")

    items = _normalize_line_items(line_items)
    assumptions = _assumptions_for(region, items)
    use_stub = calculator_stub_enabled() if stub is None else stub

    if use_stub:
        return _run_stub(region, items, assumptions)

    return _run_live(region, items, assumptions)


def export_azure_calculator_excel(
    region: str,
    line_items: list[dict[str, Any]],
    *,
    stub: bool | None = None,
) -> tuple[bytes, str, str]:
    """
    依 line_items 在 Azure Pricing Calculator 填表後，點官方 Export 下載 Excel。

    與估價使用相同 map_key／quantity，確保匯出內容與上方總價一致。
    """
    region = (region or "").strip()
    if not region:
        raise AzureCalculatorError("region 必填")

    items = _normalize_line_items(line_items)
    use_stub = calculator_stub_enabled() if stub is None else stub
    safe_region = re.sub(r"[^\w\-]+", "-", region).strip("-") or "region"
    default_name = f"ExportedEstimate-{safe_region}.xlsx"

    if use_stub:
        if not FIXTURE_PATH.is_file():
            raise AzureCalculatorError(f"找不到 stub fixture：{FIXTURE_PATH}")
        total = _parse_stub_total(FIXTURE_PATH.read_text(encoding="utf-8"))
        export_bytes, filename = _stub_official_export(region, items, total)
        return (
            export_bytes,
            filename,
            "https://azure.microsoft.com/pricing/calculator/exportestimate/",
        )

    return _export_live_excel(region, items, default_name)


def _run_stub(
    region: str,
    items: list[CalculatorLineItem],
    assumptions: list[str],
) -> AzureCalculatorResult:
    if not FIXTURE_PATH.is_file():
        raise AzureCalculatorError(f"找不到 stub fixture：{FIXTURE_PATH}")
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    total = _parse_stub_total(html)
    calculator_lines = _stub_calculator_lines(items, total)
    return AzureCalculatorResult(
        total_usd=total,
        assumptions=assumptions + ["mode: stub fixture"],
        source_url=f"file://{FIXTURE_PATH}",
        line_items=[{"map_key": i.map_key, "quantity": i.quantity} for i in items],
        calculator_lines=calculator_lines,
    )


def _stub_calculator_lines(items: list[CalculatorLineItem], total: Decimal) -> list[dict[str, Any]]:
    if not items:
        return []
    share = (total / len(items)).quantize(Decimal("0.01"))
    lines: list[dict[str, Any]] = []
    running = Decimal("0")
    for idx, item in enumerate(items):
        monthly = share if idx < len(items) - 1 else (total - running).quantize(Decimal("0.01"))
        running += monthly
        spec = CALCULATOR_AZURE_PRODUCTS[item.map_key]
        lines.append(
            {
                "map_key": item.map_key,
                "mxcell_id": item.mxcell_id,
                "label": item.label,
                "product_name": str(spec.get("calculator_search") or item.map_key),
                "specification": (
                    f"{spec.get('calculator_search')} × {item.quantity} "
                    f"({spec.get('quantity_unit', 'unit')}) — stub"
                ),
                "monthly_usd": float(monthly),
            }
        )
    return lines


def _parse_stub_total(html: str) -> Decimal:
    marker = 'data-testid="estimate-total"'
    idx = html.find(marker)
    if idx >= 0:
        snippet = html[idx : idx + 200]
        close = snippet.find(">")
        end = snippet.find("<", close + 1)
        if close >= 0 and end > close:
            return _parse_money(snippet[close + 1 : end])
    raise AzureCalculatorError("stub fixture 缺少 estimate-total")


def _fill_calculator_page(
    page,
    region: str,
    items: list[CalculatorLineItem],
    timeout_ms: int,
) -> None:
    """在 Saved estimates 分頁檢視估價；產品由 Product selector 加入。"""
    _open_saved_estimates_tab(page, timeout_ms)
    _ensure_product_selector_visible(page, timeout_ms)
    calc_region = calculator_region_value(region)
    for item in items:
        spec = CALCULATOR_AZURE_PRODUCTS[item.map_key]
        search = str(spec.get("calculator_search") or item.map_key)
        _add_product_to_estimate(page, search, timeout_ms)
        _set_product_region(page, calc_region, timeout_ms)
        _set_product_quantity(page, item, timeout_ms)
    _open_saved_estimates_tab(page, timeout_ms)
    _wait_for_estimate_ready(page, len(items), timeout_ms)


def _open_saved_estimates_tab(page, timeout_ms: int) -> None:
    tab = page.get_by_role("tab", name=_SAVED_ESTIMATES_TAB_RE).first
    tab.wait_for(state="visible", timeout=min(timeout_ms, 20_000))
    tab.click()
    page.wait_for_timeout(1000)


def _ensure_product_selector_visible(page, timeout_ms: int) -> None:
    search = page.locator(PRODUCT_SEARCH_SELECTOR).first
    try:
        if search.is_visible():
            return
    except Exception:
        pass

    go_btn = page.get_by_role("button", name=_GO_TO_PRODUCT_SELECTOR_RE).first
    if go_btn.count() > 0:
        try:
            if go_btn.is_visible():
                go_btn.click()
                page.wait_for_timeout(1200)
                search.wait_for(state="visible", timeout=min(timeout_ms, 20_000))
                return
        except Exception:
            pass

    products_tab = page.get_by_role("tab", name=_PRODUCTS_TAB_RE).first
    if products_tab.count() > 0:
        products_tab.click()
        page.wait_for_timeout(1000)
        search.wait_for(state="visible", timeout=min(timeout_ms, 20_000))
        return

    raise AzureCalculatorError("找不到 Calculator 產品選擇器（Saved estimates / Products）")


def _scroll_to_export_button(page) -> None:
    page.evaluate(
        """() => {
          const buttons = [...document.querySelectorAll('button')].filter(
            (b) => /^Export$/i.test((b.innerText || '').trim())
          );
          if (!buttons.length) return false;
          buttons[buttons.length - 1].scrollIntoView({ block: 'center' });
          return true;
        }"""
    )
    page.wait_for_timeout(800)


def _find_export_button(page):
    _scroll_to_export_button(page)
    candidates = page.locator("button").filter(has_text=_EXPORT_BUTTON_RE)
    for i in range(candidates.count()):
        btn = candidates.nth(i)
        try:
            if btn.is_visible():
                return btn
        except Exception:
            continue
    return None


def _click_official_export_button(page, timeout_ms: int) -> None:
    _open_saved_estimates_tab(page, timeout_ms)
    _scroll_to_export_button(page)
    export_btn = _find_export_button(page)
    if export_btn is not None:
        export_btn.click(timeout=min(timeout_ms, 30_000))
        return

    clicked = page.evaluate(
        """() => {
          const buttons = [...document.querySelectorAll('button')].filter(
            (b) => /^Export$/i.test((b.innerText || '').trim())
          );
          if (!buttons.length) return false;
          const btn = buttons[buttons.length - 1];
          btn.scrollIntoView({ block: 'center' });
          btn.click();
          return true;
        }"""
    )
    if not clicked:
        raise AzureCalculatorError(
            "找不到 Calculator 官方 Export 按鈕（請確認 Saved estimates 分頁估價已就緒）"
        )


def _download_official_export(page, timeout_ms: int) -> tuple[bytes, str, str, str]:
    """
    在 Saved estimates 分頁捲動至頁底，點選官方 Export（.xlsx）。
    """
    with page.expect_download(timeout=min(timeout_ms, 60_000)) as download_info:
        _click_official_export_button(page, timeout_ms)
    download = download_info.value
    path = download.path()
    if not path:
        raise AzureCalculatorError("Calculator 官方 Export 下載失敗")
    data = Path(path).read_bytes()
    filename = download.suggested_filename or OFFICIAL_EXPORT_FILENAME
    source_url = download.url or ""
    if not data.startswith(b"PK"):
        raise AzureCalculatorError(f"官方 Export 非預期格式：{filename!r}")
    return data, filename, OFFICIAL_EXPORT_MIME, source_url


def _minimal_xlsx_bytes(*rows: str) -> bytes:
    """CI stub 用最小合法 xlsx（ZIP 結構）。"""
    shared = "".join(f"<si><t>{text}</t></si>" for text in rows)
    sheet_rows = "".join(
        f'<row r="{idx}"><c t="inlineStr"><is><t>{text}</t></is></c></row>'
        for idx, text in enumerate(rows, start=1)
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Estimate" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{sheet_rows}</sheetData></worksheet>',
        )
        if shared:
            zf.writestr(
                "xl/sharedStrings.xml",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(rows)}" uniqueCount="{len(rows)}">{shared}</sst>',
            )
    return buf.getvalue()


def _stub_official_export(
    region: str,
    items: list[CalculatorLineItem],
    total: Decimal,
) -> tuple[bytes, str]:
    rows = [
        "Azure Pricing Calculator Estimate (stub export)",
        f"Region: {region}",
        f"Estimated monthly cost: ${total}",
    ]
    for item in items:
        spec = CALCULATOR_AZURE_PRODUCTS[item.map_key]
        rows.append(f"{spec.get('calculator_search')} x {item.quantity}")
    safe_region = re.sub(r"[^\w\-]+", "-", region).strip("-") or "region"
    return _minimal_xlsx_bytes(*rows), f"ExportedEstimate-{safe_region}.xlsx"


def _export_live_excel(
    region: str,
    items: list[CalculatorLineItem],
    default_filename: str,
) -> tuple[bytes, str, str]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AzureCalculatorError(
            "Playwright 未安裝；本機請 pip install playwright && playwright install chromium"
        ) from exc

    _assert_url_allowed(AZURE_CALCULATOR_URL)
    timeout_ms = int(float(os.environ.get("COST_AZURE_CALCULATOR_TIMEOUT", "120")) * 1000)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1440, "height": 900},
            )
            page = context.new_page()
            page.goto(AZURE_CALCULATOR_URL, wait_until="networkidle", timeout=timeout_ms)
            _dismiss_consent_banners(page)
            _fill_calculator_page(page, region, items, timeout_ms)
            export_bytes, filename, _mime, source_url = _download_official_export(
                page, timeout_ms
            )
        except PlaywrightTimeout as exc:
            raise AzureCalculatorError("Calculator Excel 匯出逾時") from exc
        finally:
            browser.close()

    return export_bytes, filename or default_filename, source_url


def _run_live(
    region: str,
    items: list[CalculatorLineItem],
    assumptions: list[str],
) -> AzureCalculatorResult:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AzureCalculatorError(
            "Playwright 未安裝；本機請 pip install playwright && playwright install chromium"
        ) from exc

    _assert_url_allowed(AZURE_CALCULATOR_URL)
    timeout_ms = int(float(os.environ.get("COST_AZURE_CALCULATOR_TIMEOUT", "120")) * 1000)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(AZURE_CALCULATOR_URL, wait_until="networkidle", timeout=timeout_ms)
            _dismiss_consent_banners(page)
            _fill_calculator_page(page, region, items, timeout_ms)
            total_text = _read_estimate_total(page, timeout_ms)
            total = _parse_money(total_text)
            raw_lines = _read_estimate_lines(page)
            calculator_lines = _attach_item_metadata(raw_lines, items)
        except PlaywrightTimeout as exc:
            raise AzureCalculatorError("Calculator 頁面操作逾時") from exc
        finally:
            browser.close()

    return AzureCalculatorResult(
        total_usd=total,
        assumptions=assumptions + ["mode: live playwright"],
        source_url=AZURE_CALCULATOR_URL,
        line_items=[{"map_key": i.map_key, "quantity": i.quantity} for i in items],
        calculator_lines=calculator_lines,
    )


def _dismiss_consent_banners(page) -> None:
    for label in ("Accept", "Accept all", "I accept", "Agree"):
        btn = page.get_by_role("button", name=re.compile(label, re.I))
        if btn.count() == 0:
            continue
        try:
            btn.first.click(timeout=3000)
            page.wait_for_timeout(800)
            return
        except Exception:
            continue


def _estimate_product_count(page) -> int:
    return page.locator(".products-holder .product-summary").count()


def _wait_for_estimate_ready(page, expected_products: int, timeout_ms: int) -> None:
    """等 Estimate 面板出齊所有產品列與 Monthly 金額後再讀總價。"""
    if expected_products < 1:
        return
    deadline = time.monotonic() + timeout_ms / 1000
    last_count = 0
    while time.monotonic() < deadline:
        count = _estimate_product_count(page)
        last_count = count
        if count >= expected_products:
            lines = _read_estimate_lines(page)
            if len(lines) >= expected_products:
                page.wait_for_timeout(800)
                return
        page.wait_for_timeout(500)
    raise AzureCalculatorError(
        f"Calculator Estimate 僅有 {last_count}/{expected_products} 個產品明細（或 Monthly 尚未就緒）"
    )


def _find_catalog_add_button(page, search: str, timeout_ms: int):
    """在產品目錄（非右側 Estimate 面板）找 Add to estimate。"""
    short = search.split("(")[0].strip()
    title_pat = re.compile(re.escape(short), re.I)
    add_pat = re.compile(r"Add to estimate", re.I)

    cards = page.locator("li, div").filter(has=page.get_by_text(title_pat))
    for i in range(cards.count()):
        card = cards.nth(i)
        try:
            if not card.is_visible():
                continue
            in_estimate = card.evaluate("el => !!el.closest('.products-holder')")
            if in_estimate:
                continue
            btn = card.get_by_role("button", name=add_pat).first
            if btn.count() > 0 and btn.is_visible():
                return btn
        except Exception:
            continue

    add_buttons = page.get_by_role("button", name=add_pat)
    for i in range(add_buttons.count()):
        candidate = add_buttons.nth(i)
        try:
            if not candidate.is_visible():
                continue
            in_estimate = candidate.evaluate("el => !!el.closest('.products-holder')")
            if in_estimate:
                continue
            return candidate
        except Exception:
            continue

    raise AzureCalculatorError(f"找不到可點擊的 Add to estimate：{search!r}")


def _add_product_to_estimate(page, search: str, timeout_ms: int) -> None:
    """在產品目錄搜尋並 Add to estimate（非站內 azure.com 搜尋框）。"""
    before_count = _estimate_product_count(page)
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            search_box = page.locator(PRODUCT_SEARCH_SELECTOR).first
            search_box.wait_for(state="visible", timeout=timeout_ms)
            search_box.click()
            search_box.fill("")
            page.wait_for_timeout(300)
            search_box.fill(search)
            page.wait_for_timeout(1500)

            add_btn = _find_catalog_add_button(page, search, timeout_ms)
            add_btn.click(timeout=timeout_ms)

            deadline = time.monotonic() + min(timeout_ms, 30_000) / 1000
            while time.monotonic() < deadline:
                if _estimate_product_count(page) > before_count:
                    page.wait_for_timeout(1200)
                    return
                page.wait_for_timeout(400)
            last_error = AzureCalculatorError(
                f"Add to estimate 後 Estimate 列數未增加：{search!r}"
            )
        except AzureCalculatorError as exc:
            last_error = exc
        page.wait_for_timeout(800)

    raise last_error or AzureCalculatorError(f"無法加入產品：{search!r}")


def _set_product_region(page, calc_region: str, timeout_ms: int) -> None:
    region_select = page.locator(REGION_SELECT_SELECTOR).last
    if region_select.count() == 0:
        return
    try:
        region_select.wait_for(state="visible", timeout=min(timeout_ms, 8_000))
    except Exception:
        logger.info(
            "Calculator 產品無 region 選擇器，略過 region=%s",
            calc_region,
        )
        return
    region_select.select_option(value=calc_region, timeout=timeout_ms)
    page.wait_for_timeout(1000)


def _set_product_quantity(page, item: CalculatorLineItem, timeout_ms: int) -> None:
    spec = CALCULATOR_AZURE_PRODUCTS[item.map_key]
    unit = spec.get("quantity_unit", "")
    field_name = str(spec.get("quantity_field") or "count")
    if item.quantity <= 0:
        return
    if unit in ("vm_instance", "node"):
        if item.quantity <= 1:
            return
    elif unit in ("gb",):
        pass
    else:
        return
    qty_input = page.locator(f'input[name="{field_name}"]').last
    if qty_input.count() == 0 or not qty_input.is_visible():
        logger.warning(
            "Calculator %s input 未找到，略過 quantity=%s",
            field_name,
            item.quantity,
        )
        return
    qty_input.fill(str(item.quantity), timeout=timeout_ms)
    page.wait_for_timeout(1000)


def _read_estimate_total(page, timeout_ms: int) -> str:
    panel = page.locator(ESTIMATE_TOTAL_SELECTOR).first
    panel.wait_for(state="visible", timeout=min(timeout_ms, 30_000))
    text = panel.inner_text(timeout=5000)
    lines = [ln.strip() for ln in text.splitlines()]
    for idx, line in enumerate(lines):
        if line.lower() == "estimated monthly cost" and idx + 1 < len(lines):
            nxt = lines[idx + 1]
            if _TOTAL_RE.search(nxt):
                return nxt

    monthly = page.get_by_text(_MONTHLY_LINE_RE)
    if monthly.count() > 0:
        match = _MONTHLY_LINE_RE.search(monthly.first.inner_text())
        if match:
            return match.group(1)

    raise AzureCalculatorError("無法讀取 Calculator Estimated monthly cost")


def _read_estimate_lines(page) -> list[dict[str, Any]]:
    """Parse `.products-holder .product-summary` rows from Calculator UI."""
    raw = page.evaluate(
        """() => {
          const holder = document.querySelector('.products-holder');
          if (!holder) return [];
          const rows = [];
          holder.querySelectorAll('.product-summary').forEach((el) => {
            const text = el.innerText || '';
            const monthly = text.match(/Monthly:\\s*(\\$[\\d,]+\\.\\d{2})/i);
            const lines = text.split('\\n').map(s => s.trim()).filter(Boolean);
            const title = lines[0] || '';
            const spec = lines.find(l =>
              /Hours|cluster|Standard|GB RAM|vCPUs|managed disk|Pay as you go/i.test(l)
            ) || lines.slice(1, 4).join(' | ');
            if (!monthly) return;
            rows.push({
              product_name: title,
              specification: spec,
              monthly_text: monthly[1],
            });
          });
          return rows;
        }"""
    )
    parsed: list[dict[str, Any]] = []
    for row in raw or []:
        parsed.append(
            {
                "product_name": str(row.get("product_name") or ""),
                "specification": str(row.get("specification") or ""),
                "monthly_usd": float(_parse_money(str(row.get("monthly_text") or ""))),
            }
        )
    return parsed


def _map_key_for_product_name(product_name: str) -> str | None:
    name = (product_name or "").casefold()
    for key, spec in CALCULATOR_AZURE_PRODUCTS.items():
        search = str(spec.get("calculator_search") or "").casefold()
        if not search:
            continue
        if search in name or name in search:
            return key
        short = search.split("(")[0].strip()
        if short and short in name:
            return key
    return None


def _attach_item_metadata(
    estimate_lines: list[dict[str, Any]],
    items: list[CalculatorLineItem],
) -> list[dict[str, Any]]:
    """Correlate Calculator rows with planned map_key / diagram labels."""
    if not estimate_lines:
        return []

    used_items: set[int] = set()
    enriched: list[dict[str, Any]] = []

    for row in estimate_lines:
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
        elif map_key:
            out["map_key"] = map_key

        enriched.append(out)

    return enriched
