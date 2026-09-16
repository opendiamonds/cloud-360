#!/usr/bin/env python3
"""One-off spike: probe Azure Pricing Calculator DOM for Playwright selectors."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

URL = "https://azure.microsoft.com/en-us/pricing/calculator/"


def main() -> int:
    findings: dict = {"url": URL, "steps": []}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(3000)

        # Cookie / consent banners
        for label in ("Accept", "Accept all", "I accept", "Agree"):
            btn = page.get_by_role("button", name=re.compile(label, re.I))
            if btn.count() > 0:
                try:
                    btn.first.click(timeout=3000)
                    findings["steps"].append(f"dismissed consent: {label}")
                    page.wait_for_timeout(1000)
                    break
                except Exception:
                    pass

        # Catalog search inputs
        inputs = page.locator("input").all()
        input_info = []
        for inp in inputs[:30]:
            try:
                if not inp.is_visible():
                    continue
                input_info.append(
                    {
                        "placeholder": inp.get_attribute("placeholder"),
                        "aria_label": inp.get_attribute("aria-label"),
                        "type": inp.get_attribute("type"),
                        "name": inp.get_attribute("name"),
                        "id": inp.get_attribute("id"),
                    }
                )
            except Exception:
                pass
        findings["visible_inputs"] = input_info

        # Try common search patterns
        search_candidates = [
            'input[placeholder*="Search" i]',
            'input[aria-label*="Search" i]',
            'input[type="search"]',
            "#products-search",
            '[data-testid*="search" i]',
        ]
        search_sel = None
        for sel in search_candidates:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                search_sel = sel
                findings["search_selector"] = sel
                break

        if not search_sel:
            findings["error"] = "no search box found"
            print(json.dumps(findings, indent=2, ensure_ascii=False))
            browser.close()
            return 1

        search = page.locator(search_sel).first
        search.click()
        search.fill("Virtual Machines")
        page.wait_for_timeout(2000)

        # Result cards / add buttons
        add_patterns = [
            ('role button name Add', page.get_by_role("button", name=re.compile(r"^Add$", re.I))),
            ('role button name add to estimate', page.get_by_role("button", name=re.compile(r"add", re.I))),
            ('text Add', page.locator('button:has-text("Add")')),
            ('aria Add', page.locator('[aria-label*="Add" i]')),
        ]
        for name, loc in add_patterns:
            cnt = loc.count()
            vis = 0
            for i in range(min(cnt, 5)):
                try:
                    if loc.nth(i).is_visible():
                        vis += 1
                except Exception:
                    pass
            findings["steps"].append(f"{name}: count={cnt} visible~={vis}")

        # Click first visible Add near Virtual Machines
        clicked = False
        vm_add = page.locator(
            'xpath=//*[contains(translate(normalize-space(.),"VIRTUAL MACHINES","virtual machines"),"virtual machines")]/ancestor::*[self::div or self::li][1]//button[contains(translate(normalize-space(.),"ADD","add"),"add")]'
        )
        if vm_add.count() > 0:
            vm_add.first.click(timeout=10_000)
            clicked = True
            findings["steps"].append("clicked VM card Add via xpath")
        else:
            add_btn = page.get_by_role("button", name=re.compile(r"^Add$", re.I))
            if add_btn.count() > 0:
                add_btn.first.click(timeout=10_000)
                clicked = True
                findings["steps"].append("clicked first Add button")

        if not clicked:
            findings["error"] = "could not click Add"
            print(json.dumps(findings, indent=2, ensure_ascii=False))
            browser.close()
            return 1

        page.wait_for_timeout(4000)

        # Estimate panel text
        body_text = page.locator("body").inner_text()
        for phrase in (
            "Estimated monthly cost",
            "Your estimate",
            "Estimate",
            "Total",
            "Upfront",
        ):
            if phrase.lower() in body_text.lower():
                findings["steps"].append(f"body contains: {phrase}")

        # Money-like elements
        money_els = page.locator("text=/\\$[\\d,]+\\.\\d{2}/").all()
        money_samples = []
        for el in money_els[:15]:
            try:
                if el.is_visible():
                    t = el.inner_text().strip()
                    if t and t not in money_samples:
                        money_samples.append(t)
            except Exception:
                pass
        findings["visible_money_texts"] = money_samples

        # Region controls
        selects = page.locator("select").all()
        select_info = []
        for sel in selects[:20]:
            try:
                if not sel.is_visible():
                    continue
                select_info.append(
                    {
                        "name": sel.get_attribute("name"),
                        "aria_label": sel.get_attribute("aria-label"),
                        "id": sel.get_attribute("id"),
                        "options": sel.locator("option").count(),
                    }
                )
            except Exception:
                pass
        findings["visible_selects"] = select_info

        # Screenshot for manual review
        shot = Path(__file__).resolve().parent.parent / "cost" / "fixtures" / "azure_calculator_live_spike.png"
        page.screenshot(path=str(shot), full_page=False)
        findings["screenshot"] = str(shot)

        browser.close()

    print(json.dumps(findings, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
