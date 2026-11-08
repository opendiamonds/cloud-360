import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * 合併前必修第 35 列 (c)：Sidebar 的 `<nav>` 地標都要有可存取名稱，且彼此不重複。
 *
 * 缺陷：「我的記憶」的 `<nav>`（`Sidebar.tsx`）沒有 `aria-label`，而同一側欄的「入口」「專案」
 * 兩個 `<nav>` 有。螢幕閱讀器的地標清單因此出現一個無名的「導覽」，使用者分不出它是哪一塊。
 * axe 的 `landmark-unique` 只在**同名**地標重複時報錯，一個無名地標與其他有名地標並存時不一定
 * 觸發，所以 `a11y.spec.ts` 的掃描不構成這一點的保證——本檔直接斷言名稱。
 *
 * **全部走 `page.route()` 攔截，不打真實後端**；兜底樣式先註冊、任何未被接管的 `/api` 請求都
 * abort 並記錄，案例結束時斷言記錄為空（形狀沿用 `a11y.spec.ts` 的隔離層）。
 *
 * **名稱穩定性（落地後不可改）**：TCMS 案例名稱為 `<describe> › <test>`，`describe` 與各 `test`
 * 字串一經合併不得再改。
 *
 * **突變驗證**（結果記於 `brain-infra` 的 `code-summary.md`）：
 *   M1 拿掉「我的記憶」`<nav>` 的 `aria-label` → 案例 1、2 紅；
 *   M2 把它改成與「專案」同名 → 案例 1、2 紅（案例 1 找不到名為「我的記憶」的地標，案例 2 名稱重複）。
 */

const SELF_ID = 601;
const FAKE_TOKEN = 'e2e-sidebar-landmarks-token';
const VIEW = { view: true, edit: false, review: false };

async function json(route: Route, status: number, body: unknown): Promise<void> {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

/** 具 K1／K2／K3 view 的已核准帳號：側欄同時出現「入口」「專案」「我的記憶」三個 `<nav>`。 */
async function stage(page: Page): Promise<string[]> {
  const leaked: string[] = [];
  await page.route('**/api/**', (route) => {
    leaked.push(`${route.request().method()} ${new URL(route.request().url()).pathname}`);
    return route.abort();
  });
  await page.routeWebSocket(/.*/, (ws) => void ws.close());
  await page.route('**/api/auth/me', (route) =>
    json(route, 200, {
      id: SELF_ID,
      username: 'e2e-sidebar-user',
      role: 'Project_Admin',
      is_active: true,
      authorization_status: 'approved',
      permissions: { K1: VIEW, K2: VIEW, K3: VIEW },
      pending_request: null,
    })
  );
  await page.route(/\/api\/membership\/reselections\/pending(\?.*)?$/, (route) => json(route, 200, []));
  await page.route(/\/api\/memory\/records(\?.*)?$/, (route) => json(route, 200, []));
  await page.addInitScript((token) => {
    sessionStorage.setItem('token', token);
  }, FAKE_TOKEN);
  await page.goto('/memory');
  await expect(page.getByTestId('sidebar-memory-link')).toBeVisible();
  return leaked;
}

test.describe('Sidebar landmarks', () => {
  /**
   * @purpose 「我的記憶」所在的 `<nav>` 有可存取名稱「我的記憶」，且該地標內含「我的記憶」連結
   * @ui /memory | 側欄 sidebar-memory-link 所在的導覽地標
   * @given 攔截層：/api/auth/me 帶 K1／K2／K3 view；記憶與改選查詢回空清單
   * @step 開啟 /memory | 側欄出現「我的記憶」連結
   * @step 以 role=navigation、name=我的記憶 定位地標 | 恰一個，且其中含 sidebar-memory-link
   * @pass 地標存在且包住該連結；沒有未被攔截的 /api 請求
   * @story US4.2
   * @note 以無障礙樹的名稱定位（getByRole），不是比對 DOM 屬性字串：aria-labelledby 等其他命名方式也會通過。
   */
  test('memory nav landmark is named', async ({ page }) => {
    const leaked = await stage(page);
    const nav = page.getByRole('navigation', { name: '我的記憶', exact: true });
    await expect(nav).toHaveCount(1);
    await expect(nav.getByTestId('sidebar-memory-link')).toBeVisible();
    expect(leaked).toEqual([]);
  });

  /**
   * @purpose 側欄裡含「入口」「專案」「我的記憶」三個連結的 `<nav>` 都有名稱，且三個名稱互不相同
   * @ui /memory | 側欄的三個導覽地標
   * @given 同上
   * @step 對三個連結各取最近的 `<nav>` 祖先，讀其可存取名稱（aria-label 或 aria-labelledby）
   * @pass 三個名稱皆非空且互不相同
   * @story US4.2
   * @note 只檢查這三個獨立項：可收合群組的 `<nav>` 由群組標題按鈕承擔辨識，不在本列範圍（第 35 列 (c) 只點名「我的記憶」）。
   */
  test('top-level sidebar nav landmarks have distinct names', async ({ page }) => {
    const leaked = await stage(page);
    const names: string[] = [];
    for (const testid of ['sidebar-entry-link', 'sidebar-projects-link', 'sidebar-memory-link']) {
      const name = await page.getByTestId(testid).evaluate((el) => {
        const nav = el.closest('nav');
        if (!nav) return '';
        const labelledby = nav.getAttribute('aria-labelledby');
        if (labelledby) return document.getElementById(labelledby)?.textContent?.trim() ?? '';
        return nav.getAttribute('aria-label')?.trim() ?? '';
      });
      names.push(name);
    }
    expect(names.every((n) => n.length > 0), `有無名的導覽地標：${JSON.stringify(names)}`).toBe(true);
    expect(new Set(names).size, `導覽地標名稱重複：${JSON.stringify(names)}`).toBe(names.length);
    expect(leaked).toEqual([]);
  });
});
