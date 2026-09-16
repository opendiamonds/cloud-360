#!/usr/bin/env python3
"""Spike: full Azure Calculator flow — search, add, region, read total."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

URL = "https://azure.microsoft.com/en-us/pricing/calculator/"
PRODUCT_SEARCH = 'input[aria-label="Search products"]'


def _dismiss_consent(page) -> None:
    for label in ("Accept", "Accept all", "I accept", "Agree"):
        btn = page.get_by_role("button", name=re.compile(label, re.I))
        if btn.count() > 0:
            try:
                btn.first.click(timeout=3000)
                page.wait_for_timeout(800)
                return
            except Exception:
                pass


def _add_product(page, product_name: str) -> None:
    search = page.locator(PRODUCT_SEARCH).first
    search.wait_for(state="visible", timeout=30_000)
    search.click()
    search.fill("")
    search.fill(product_name)
    page.wait_for_timeout(1500)

    # Card in product list with matching title
    title_pat = re.compile(re.escape(product_name.split("(")[0].strip()), re.I)
    card = page.locator("li, div").filter(has=page.get_by_text(title_pat)).first
    add = card.locator('button:has-text("Add")').first
    if add.count() == 0 or not add.is_visible():
        add = page.locator('button:has-text("Add")').filter(has_not=page.locator(":scope")).first
        # fallback: first visible Add in main catalog area
        adds = page.locator('button:has-text("Add")')
        for i in range(adds.count()):
            b = adds.nth(i)
            if b.is_visible():
                add = b
                break
    add.click(timeout=15_000)
    page.wait_for_timeout(2000)


def _read_monthly_total(page) -> dict:
    out = {}
    # Estimate sidebar — look for Monthly label + sibling value
    monthly_row = page.locator('text=/^Monthly:/i').first
    if monthly_row.count() > 0 and monthly_row.is_visible():
        out["monthly_line"] = monthly_row.inner_text().strip()

    # Broader: section with "Estimated monthly cost"
    header = page.get_by_text(re.compile(r"Estimated monthly cost", re.I))
    if header.count() > 0:
        try:
            container = header.first.locator("xpath=ancestor::*[self::div or self::section][1]")
            out["header_section"] = container.inner_text()[:500]
        except Exception:
            pass

    # select[name=region] nearby estimate totals
    for sel in (
        '[class*="estimate" i] >> text=/\\$[\\d,]+\\.\\d{2}/',
        'aside >> text=/Monthly:\\s*\\$/',
        'text=/Your Estimate/i >> xpath=following::*[contains(text(),"$")][1]',
    ):
        loc = page.locator(sel).first
        try:
            if loc.count() > 0 and loc.is_visible():
                out[f"sel:{sel[:40]}"] = loc.inner_text().strip()
        except Exception:
            pass

    return out


def main() -> int:
    result = {"region": "eastus", "products": ["Virtual Machines"]}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(2000)
        _dismiss_consent(page)

        _add_product(page, "Virtual Machines")

        region_sel = page.locator('select[name="region"]').first
        region_sel.wait_for(state="visible", timeout=15_000)
        region_sel.select_option(value="eastus")
        page.wait_for_timeout(2000)

        result["totals_before_qty"] = _read_monthly_total(page)

        # Try set VM instances quantity if present
        qty = page.locator('input[type="number"]').first
        if qty.count() > 0 and qty.is_visible():
            qty.fill("2")
            page.wait_for_timeout(1500)
            result["qty_set"] = "2"

        result["totals_after"] = _read_monthly_total(page)

        shot = Path(__file__).resolve().parent.parent / "cost" / "fixtures" / "azure_calculator_live_flow.png"
        page.screenshot(path=str(shot))
        result["screenshot"] = str(shot)

        browser.close()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
