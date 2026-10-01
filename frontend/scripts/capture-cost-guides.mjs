/**
 * Capture calculator screenshots and draw rectangular highlights on key buttons.
 * Run: node scripts/capture-cost-guides.mjs
 */
import { chromium } from 'playwright';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(__dirname, '../public/cost-guides');
const VIEWPORT = { width: 1440, height: 900 };

async function dismissCookies(page) {
  for (const sel of [
    '#onetrust-accept-btn-handler',
    'button:has-text("Accept all")',
    'button:has-text("Accept All")',
    'button:has-text("I agree")',
    'button:has-text("Accept")',
  ]) {
    const btn = page.locator(sel).first();
    if (await btn.isVisible({ timeout: 700 }).catch(() => false)) {
      await btn.click({ timeout: 1500 }).catch(() => {});
      await page.waitForTimeout(250);
      break;
    }
  }
}

function annotateRects(image, marks) {
  // marks: [{x, y, w, h, label}]
  if (!marks.length) return;
  const py = `
from PIL import Image, ImageDraw, ImageFont
import json, sys
path = sys.argv[1]
marks = json.loads(sys.argv[2])
im = Image.open(path).convert('RGBA')
overlay = Image.new('RGBA', im.size, (0,0,0,0))
draw = ImageDraw.Draw(overlay)
try:
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 15)
except Exception:
    font = ImageFont.load_default()
pad = 5
for m in marks:
    x, y, w, h = int(m['x']), int(m['y']), int(m['w']), int(m['h'])
    label = m.get('label') or ''
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(im.size[0]-1, x + w + pad), min(im.size[1]-1, y + h + pad)
    # sharp rectangle: amber outer + red inner
    draw.rectangle((x0-3, y0-3, x1+3, y1+3), outline=(245,158,11,255), width=3)
    draw.rectangle((x0, y0, x1, y1), outline=(220,38,38,255), width=3)
    if label:
        tw = draw.textlength(label, font=font) if hasattr(draw, 'textlength') else len(label)*9
        bx = max(8, min(im.size[0] - int(tw) - 24, x0))
        by = y0 - 30
        if by < 4:
            by = y1 + 6
        draw.rectangle((bx, by, bx+tw+14, by+24), fill=(245,158,11,255))
        draw.text((bx+7, by+3), label, fill=(69,26,3,255), font=font)
Image.alpha_composite(im, overlay).convert('RGB').save(path, optimize=True)
print('annotated', path, len(marks))
`;
  const r = spawnSync('python3', ['-c', py, image, JSON.stringify(marks)], {
    encoding: 'utf-8',
  });
  if (r.status !== 0) throw new Error(r.stderr || r.stdout);
  console.log(r.stdout.trim());
}

async function rectOf(locator) {
  try {
    if (!(await locator.isVisible({ timeout: 4000 }).catch(() => false))) return null;
    const b = await locator.boundingBox();
    if (!b || b.width < 4 || b.height < 4) return null;
    return { x: b.x, y: b.y, w: b.width, h: b.height };
  } catch {
    return null;
  }
}

async function shot(page, name) {
  const file = path.join(OUT, name);
  await page.screenshot({ path: file, fullPage: false });
  console.log('wrote', name);
  return file;
}

async function captureAws(page) {
  await page.goto('https://calculator.aws/', { waitUntil: 'networkidle', timeout: 90000 }).catch(() =>
    page.goto('https://calculator.aws/', { waitUntil: 'domcontentloaded', timeout: 60000 }),
  );
  await dismissCookies(page);
  await page.waitForTimeout(2500);

  const create = page.locator('button:has-text("Create estimate"), a:has-text("Create estimate")').last();
  await create.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  const aws1 = await shot(page, 'aws-1-landing.png');
  const r1 = (await rectOf(create)) || { x: 980, y: 420, w: 220, h: 40 };
  annotateRects(aws1, [{ ...r1, label: 'Create estimate' }]);

  await page.goto('https://calculator.aws/#/addService', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await dismissCookies(page);
  await page.waitForTimeout(3000);
  const configure = page.locator('button:has-text("Configure")').first();
  await configure.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  const aws2 = await shot(page, 'aws-2-add-service.png');
  const r2 = (await rectOf(configure)) || { x: 360, y: 640, w: 100, h: 32 };
  annotateRects(aws2, [{ ...r2, label: 'Configure' }]);

  await page.goto('https://calculator.aws/#/estimate', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await dismissCookies(page);
  await page.waitForTimeout(3000);
  const exportBtn = page.locator('button:has-text("Export")').first();
  await exportBtn.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  const aws3 = await shot(page, 'aws-3-estimate.png');
  const r3 = (await rectOf(exportBtn)) || { x: 1140, y: 165, w: 90, h: 34 };
  annotateRects(aws3, [{ ...r3, label: 'Export -> CSV' }]);
}

async function captureGcp(page) {
  await page.goto('https://cloud.google.com/products/calculator', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await dismissCookies(page);
  await page.waitForTimeout(2500);

  const add = page.locator('button:has-text("Add to estimate")').first();
  await add.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  const gcp1 = await shot(page, 'gcp-1-landing.png');
  const g1 = (await rectOf(add)) || { x: 360, y: 530, w: 180, h: 44 };
  annotateRects(gcp1, [{ ...g1, label: 'Add to estimate' }]);

  await add.click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(2000);
  // Prefer the + on Compute Engine card
  const computeCard = page.locator('text=/^Compute Engine$/i').first();
  let g2 = null;
  if (await computeCard.isVisible().catch(() => false)) {
    // find + button near the card
    const card = computeCard.locator('xpath=ancestor::*[self::div or self::li][1]');
    const plus = card.locator('button').first();
    g2 = (await rectOf(plus)) || (await rectOf(computeCard));
  }
  if (!g2) {
    const plus = page.locator('[aria-label*="Add" i], button:has-text("+")').nth(1);
    g2 = await rectOf(plus);
  }
  const gcp2 = await shot(page, 'gcp-2-products.png');
  annotateRects(gcp2, [
    { ...(g2 || { x: 520, y: 340, w: 36, h: 36 }), label: 'Add product (+)' },
  ]);

  await page.goto('https://cloud.google.com/products/calculator', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await dismissCookies(page);
  await page.waitForTimeout(2000);
  const save =
    page.locator('[aria-label*="Save" i], [aria-label*="Download" i], [aria-label*="Export" i], button:has-text("SAVE")').first();
  const gcp3 = await shot(page, 'gcp-3-export.png');
  let g3 = await rectOf(save);
  if (!g3) {
    // footer action icons in Cost details — usually around bottom-right panel
    g3 = { x: 1010, y: 805, w: 40, h: 40 };
  }
  annotateRects(gcp3, [{ ...g3, label: 'SAVE / Download' }]);
}

async function captureAzure(page) {
  await page.goto('https://azure.microsoft.com/en-us/pricing/calculator/', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await dismissCookies(page);
  await page.waitForTimeout(3000);

  const azAdd = page.locator('button:has-text("Add to estimate")').first();
  await azAdd.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  await azAdd.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  const az1 = await shot(page, 'azure-1-landing.png');
  const a1 = (await rectOf(azAdd)) || { x: 330, y: 740, w: 140, h: 36 };
  annotateRects(az1, [{ ...a1, label: 'Add to estimate' }]);

  await azAdd.click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(2500);
  // Click toast View or scroll to estimate
  const view = page.locator('text=/Virtual Machines added/i').first();
  if (await view.isVisible().catch(() => false)) {
    await page.locator('text=/View/i').last().click().catch(() => {});
    await page.waitForTimeout(1000);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  const monthly = page.locator('text=/Estimated monthly cost/i').first();
  await monthly.scrollIntoViewIfNeeded().catch(() => {});
  const az2 = await shot(page, 'azure-2-configure.png');
  // Box the whole monthly cost chip in header if possible
  let a2 = await rectOf(monthly);
  if (a2) {
    // expand left to include the dollar amount nearby
    a2 = { x: Math.max(0, a2.x - 120), y: Math.max(0, a2.y - 8), w: a2.w + 140, h: a2.h + 16 };
  } else {
    a2 = { x: 1120, y: 70, w: 280, h: 40 };
  }
  annotateRects(az2, [{ ...a2, label: 'Estimate totals' }]);

  const exportAz = page.locator('button:has-text("Export")').first();
  if (await exportAz.isVisible().catch(() => false)) {
    await exportAz.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(500);
  } else {
    await page.evaluate(() => window.scrollBy(0, 900));
    await page.waitForTimeout(800);
  }
  const az3 = await shot(page, 'azure-3-export.png');
  const a3 = (await rectOf(exportAz)) || { x: 120, y: 430, w: 110, h: 40 };
  annotateRects(az3, [{ ...a3, label: 'Export' }]);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    locale: 'en-US',
    userAgent:
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  for (const [name, fn] of [
    ['aws', captureAws],
    ['gcp', captureGcp],
    ['azure', captureAzure],
  ]) {
    try {
      console.log('---', name);
      await fn(page);
    } catch (err) {
      console.error(name, 'failed:', err.message || err);
    }
  }

  await browser.close();
  console.log('done');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
