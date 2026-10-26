import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * U15 memory-page-ui — 「我的記憶」頁（`/memory`）。
 *
 * **全部走 `page.route()` 攔截，不打真實後端**（`unit-test-instructions.md §五`）：
 * 本檔測的是前端對 `U8` 記憶 API 的消費；後端的授權與過濾由
 * `backend/tests/test_memory_authz.py` 與 `test_memory_pending_authz.py` 負責。
 * 故本檔**不需要資料庫、後端、`claude` CLI 或 n8n webhook**，只需要前端被服務於
 * `BASE_URL`，且**不碰任何 LLM 路徑**。
 *
 * **記憶 API 以一份「會位移 offset 的伺服器」模擬**：`MemoryServerStub` 以程式
 * 維護一份記憶陣列，`GET` 依 `offset`／`limit` 切片、`DELETE` 從陣列移除。少了這個，
 * 案例 6–8 要防的「offset 位移漏列」根本構造不出來。
 *
 * **延遲由測試持有的 promise 控制，不用 `waitForTimeout`**：flaky 會被 CI 的
 * `retries: 1` 掩蓋，而本檔要驗的正是時序。
 *
 * **計數類斷言必須對生產建置執行**：`main.tsx` 的 `StrictMode` 在開發模式會重複
 * 呼叫 effect（`U24` code-summary §五之二實測）。本機以 `npm run build` ＋
 * `vite preview` 執行；`ui-regression` 跑的是 nginx 服務的建置產物，兩者一致。
 *
 * **名稱穩定性（落地後不可改）**：TCMS 案例名稱為 `<describe> › <test>`，
 * `ui-regression.lock.yml` 的 Kiwi 回報註解逐字「changing it orphans the old cases」。
 * `describe`（`U15 memory page`）與各 `test` 字串**一經合併不得再改**。
 */

// ---------------------------------------------------------------------------
// 測試資料
// ---------------------------------------------------------------------------

const SELF_ID = 501;
const OTHER_ID = 777;
const SELF_NAME = 'e2e-memory-user';

/** 記憶內容一律帶這個前綴：案例 10 要斷言 console **不含**它（`SEC-U15-5`）。 */
const CONTENT_PREFIX = 'e2e-memory-';

type Kind = 'semantic' | 'procedure' | 'episodic';

interface MemoryStub {
  memory_id: string;
  kind: Kind;
  owner_user_id: number;
  visibility_scope: 'owner' | 'platform';
  content: string;
  embedding_model: string;
  created_at: string;
  expires_at: string | null;
}

let nextId = 1;

function memory(
  kind: Kind,
  content: string,
  opts: { owner?: number; scope?: 'owner' | 'platform' } = {}
): MemoryStub {
  const id = nextId++;
  const created = new Date(Date.UTC(2026, 8, 1) - id * 60_000);
  const expires = new Date(created.getTime() + 90 * 24 * 3600 * 1000);
  return {
    memory_id: String(id),
    kind,
    owner_user_id: opts.owner ?? SELF_ID,
    visibility_scope: opts.scope ?? 'owner',
    content,
    embedding_model: 'stub-v1',
    created_at: created.toISOString(),
    expires_at: kind === 'episodic' ? expires.toISOString() : null,
  };
}

/** `count` 則自己的情節記憶，內容為 `e2e-memory-ep-01`…，陣列順序即伺服器排序。 */
function episodes(count: number): MemoryStub[] {
  return Array.from({ length: count }, (_, i) =>
    memory('episodic', `${CONTENT_PREFIX}ep-${String(i + 1).padStart(2, '0')}`)
  );
}

interface GetQuery {
  kind: string | null;
  offset: string | null;
  limit: string | null;
}

/** `GET` 的攔截掛鉤：可延遲（回傳前 await）或改寫狀態碼。 */
type GetHook = (q: GetQuery, stub: MemoryServerStub) => Promise<number | void> | number | void;

/**
 * `DELETE` 的攔截掛鉤：在**刪除生效之前** await。延遲期間伺服器陣列仍含該列，
 * 與真實後端「交易尚未提交」的狀態一致。
 */
type DeleteHook = (memoryId: string) => Promise<void> | void;

class MemoryServerStub {
  records: MemoryStub[];
  readonly gets: GetQuery[] = [];
  readonly deletes: string[] = [];
  getHook: GetHook | null = null;
  deleteHook: DeleteHook | null = null;
  deleteStatus: number | null = null;

  constructor(records: MemoryStub[]) {
    this.records = [...records];
  }

  episodicGets(): GetQuery[] {
    return this.gets.filter((g) => g.kind === 'episodic');
  }

  async handle(route: Route): Promise<void> {
    const req = route.request();
    const url = new URL(req.url());
    const method = req.method();

    if (method === 'GET' && url.pathname.endsWith('/api/memory/records')) {
      const q: GetQuery = {
        kind: url.searchParams.get('kind'),
        offset: url.searchParams.get('offset'),
        limit: url.searchParams.get('limit'),
      };
      this.gets.push(q);
      const override = this.getHook ? await this.getHook(q, this) : undefined;
      if (typeof override === 'number' && override !== 200) {
        await route.fulfill({
          status: override,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'stub failure' }),
        });
        return;
      }
      const offset = Number(q.offset ?? '0');
      const limit = Math.min(Number(q.limit ?? '50'), 200);
      const body = this.records
        .filter((r) => !q.kind || r.kind === q.kind)
        .slice(offset, offset + limit);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
      return;
    }

    const del = url.pathname.match(/\/api\/memory\/records\/([^/]+)$/);
    if (method === 'DELETE' && del) {
      const id = decodeURIComponent(del[1]);
      this.deletes.push(id);
      if (this.deleteHook) await this.deleteHook(id);
      if (this.deleteStatus) {
        await route.fulfill({
          status: this.deleteStatus,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'stub failure' }),
        });
        return;
      }
      const before = this.records.length;
      this.records = this.records.filter((r) => r.memory_id !== id);
      await route.fulfill({ status: before === this.records.length ? 404 : 204, body: '' });
      return;
    }

    await route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"no stub"}' });
  }
}

/** 一個由測試釋放的閘門（取代 `waitForTimeout`）。 */
function gate(): { wait: Promise<void>; open: () => void } {
  let open = () => {};
  const wait = new Promise<void>((resolve) => {
    open = resolve;
  });
  return { wait, open };
}

/**
 * 佈置：攔截 `/api/auth/*` 與 `/api/memory/**`，再以登入頁的表單登入
 * （形狀沿用 `regression.spec.ts` 的 `login()`）。
 */
async function setup(page: Page, records: MemoryStub[]): Promise<MemoryServerStub> {
  const stub = new MemoryServerStub(records);

  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'e2e-token',
        token_type: 'bearer',
        username: SELF_NAME,
        role: 'Project_Architect',
        authorization_status: 'approved',
      }),
    });
  });
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: SELF_ID,
        username: SELF_NAME,
        role: 'Project_Architect',
        is_active: true,
        authorization_status: 'approved',
        permissions: {},
        pending_request: null,
      }),
    });
  });
  await page.route('**/api/memory/**', (route) => stub.handle(route));

  await page.goto('/');
  await page.getByPlaceholder('請輸入您的帳號').fill(SELF_NAME);
  await page.getByPlaceholder('請輸入密碼').fill('e2e-password');
  await page.getByRole('button', { name: '登入系統' }).click();
  await expect(page).not.toHaveURL(/\/login$/);
  return stub;
}

/**
 * 不重新載入頁面的 SPA 導覽：推入歷史紀錄並送出 popstate，React Router 的 BrowserRouter 據以換頁。
 * 用於「離開再回來」的情境——整頁重載會掩蓋模組層快取的缺陷。
 */
async function spaNavigate(page: Page, path: string): Promise<void> {
  await page.evaluate((target) => {
    window.history.pushState(null, '', target);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}

/** 開啟記憶頁並等三區的初次載入都結束（頁面播報「記憶已載入」）。 */
async function openMemoryPage(page: Page): Promise<void> {
  await page.goto('/memory');
  await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText('記憶已載入');
}

/**
 * 等某個被攔截的請求在瀏覽器端處理完：`requestfinished` 之後再跨兩個 frame，
 * 讓 `res.json()` 的 promise 與 React 的 commit 都跑完。用於斷言「某個回應**被丟棄**」
 * ——那種斷言沒有可以等待的畫面變化。
 */
async function settleAfter(page: Page, finished: Promise<unknown>): Promise<void> {
  await finished;
  await page.evaluate(
    () => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
  );
}

const zone = (page: Page, fragment: string) => page.getByTestId(`memory-zone-${fragment}`);
const item = (page: Page, id: string) => page.getByTestId(`memory-item-${id}`);

async function deleteViaUi(page: Page, id: string): Promise<void> {
  await page.getByTestId(`memory-item-${id}-delete`).click();
  await page.getByTestId(`memory-item-${id}-delete-confirm`).click();
}

// ---------------------------------------------------------------------------

test.describe('U15 memory page', () => {
  test.beforeEach(() => {
    nextId = 1;
  });

  /**
   * @purpose 「我的記憶」入口出現在 Sidebar，點擊進入記憶頁，且三區固定存在、順序固定。
   * @given 已登入的一般使用者（無任何 story 權限）；三區皆有至少一則記憶
   * @step 直接開啟 `/memory`（DEMO 的 `/brain` 已隨 U13 移除，無其他不需 story 權限的 Layout 頁） | Sidebar 出現「我的記憶」（`sidebar-memory-link`）
   * @step 點「我的記憶」 | 網址變為 `/memory`，出現 `memory-page`
   * @step 檢視區塊順序 | 依序為語意、程序、情節三個 region，各有 `h2`
   * @pass 入口可見、導向正確、三區順序為 semantic → procedural → episodic
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 每區一次，回傳該呼叫者可見的記憶
   * @ui /memory | 記憶頁：三個區塊（語意／程序／情節）
   * @note 入口的判定是 `canSeeMemoryEntry`（INV-3）；入口頁捷徑那一半屬 `U14`。
   *       使用者刻意不給任何 story 權限：`/memory` 不包 `CapabilityRoute`（BR31.1），
   *       若誤包會被導向 `/403`，本案即紅。
   */
  test('sidebar entry opens /memory with three zones in fixed order', async ({ page }) => {
    await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}s1`),
      memory('procedure', `${CONTENT_PREFIX}p1`),
      ...episodes(1),
    ]);
    await page.goto('/memory');
    const link = page.getByTestId('sidebar-memory-link');
    await expect(link).toBeVisible();
    await expect(link).toHaveText('我的記憶');
    await link.click();

    await expect(page).toHaveURL(/\/memory$/);
    await expect(page.getByTestId('memory-page')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1, name: '我的記憶' })).toBeVisible();
    const order = await page
      .locator('[data-testid^="memory-zone-"][role="region"]')
      .evaluateAll((els) => els.map((el) => el.getAttribute('data-testid')));
    expect(order).toEqual(['memory-zone-semantic', 'memory-zone-procedural', 'memory-zone-episodic']);
    for (const fragment of ['semantic', 'procedural', 'episodic']) {
      await expect(zone(page, fragment).getByRole('heading', { level: 2 })).toBeVisible();
    }
  });

  /**
   * @purpose 開頁恰發出三個 GET，每區一個，參數各自正確（UIP-1／UIP-2／UIP-5）。
   * @given 已登入；三區皆有記憶
   * @step 開啟 `/memory` 並等「記憶已載入」 | 三區載入完成
   * @step 檢視攔截到的 GET | 恰 3 個：semantic／limit=200、procedure／limit=200、episodic／offset=0／limit=21
   * @pass 請求數為 3，且三組參數完全相符
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 每區一次
   * @ui /memory | 記憶頁三區
   * @note `procedure` 是 API 值、`procedural` 是 test id（OPEN-MP15-4）：以 test id
   *       發請求會被伺服器的封閉集合拒絕，本案的參數斷言會抓到。語意／程序區不帶
   *       `offset`（BR33.3）；情節區以 21 探測下一頁（BR33.1）。
   */
  test('first load sends exactly three GETs with per-zone parameters', async ({ page }) => {
    const stub = await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}s1`),
      memory('procedure', `${CONTENT_PREFIX}p1`),
      ...episodes(2),
    ]);
    await openMemoryPage(page);

    expect(stub.gets).toHaveLength(3);
    const byKind = Object.fromEntries(stub.gets.map((g) => [g.kind, g]));
    expect(byKind.semantic).toEqual({ kind: 'semantic', offset: null, limit: '200' });
    expect(byKind.procedure).toEqual({ kind: 'procedure', offset: null, limit: '200' });
    expect(byKind.episodic).toEqual({ kind: 'episodic', offset: '0', limit: '21' });
  });

  /**
   * @purpose 單一區讀取失敗只讓該區進入錯誤態，且錯誤態與空態是不同的畫面（BR32.2／BR32.3）。
   * @given 已登入；程序記憶的 GET 回 500，語意區有一則，情節區為空
   * @step 開啟 `/memory` | 程序區出現 `-error` 與「重試」，**沒有** `-empty`
   * @step 檢視其他兩區 | 語意區列出記憶；情節區顯示 `-empty`，兩者皆無 `-error`
   * @step 讓程序區的 GET 恢復正常後點「重試」 | 程序區列出記憶，`-error` 消失
   * @pass 失敗只限於程序區，且從未以空態呈現
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 正常區
   * @api GET /api/memory/records -> 403 | 失敗區（以 500 模擬同一條錯誤路徑）
   * @ui /memory | 程序記憶區的錯誤態與重試鍵
   * @note 共用畫面時，讀取失敗會被使用者讀成「我的記憶被清空了」。
   */
  test('a failing zone shows its own error state and never the empty state', async ({ page }) => {
    let failProcedure = true;
    const stub = await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}s1`),
      memory('procedure', `${CONTENT_PREFIX}p1`),
    ]);
    stub.getHook = (q) => (q.kind === 'procedure' && failProcedure ? 500 : undefined);
    await openMemoryPage(page);

    await expect(page.getByTestId('memory-zone-procedural-error')).toBeVisible();
    await expect(page.getByTestId('memory-zone-procedural-empty')).toHaveCount(0);
    await expect(page.getByTestId('memory-zone-semantic-error')).toHaveCount(0);
    await expect(page.getByTestId('memory-zone-episodic-error')).toHaveCount(0);
    await expect(item(page, '1')).toBeVisible();
    await expect(page.getByTestId('memory-zone-episodic-empty')).toBeVisible();

    failProcedure = false;
    await page.getByTestId('memory-zone-procedural-retry').click();
    await expect(item(page, '2')).toBeVisible();
    await expect(page.getByTestId('memory-zone-procedural-error')).toHaveCount(0);
  });

  /**
   * @purpose 每則顯示擁有者與可見範圍；他人設為平台可見的記憶照樣出現但沒有刪除鍵（BR35.1／BR35.2／BR31.3）。
   * @given 已登入（id 501）；語意區有一則自己的（僅你可見）與一則他人（id 777）的平台可見記憶
   * @step 檢視自己的那則 | 擁有者顯示「你」，`data-owner-user-id`＝501；可見範圍「僅你可見」；有 `-delete`
   * @step 檢視他人的那則 | 仍在畫面上；擁有者顯示「其他使用者」且可見文字不含任何數字；可見範圍「平台可見」；**沒有** `-delete`，改顯示「平台可見（他人的記憶）」
   * @pass 兩則皆渲染，欄位文字與刪除控件的有無皆如上
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 回傳含他人 platform 列的清單
   * @ui /memory | 條目的擁有者欄位、可見範圍欄位、刪除鍵
   * @note 前端過濾（把他人的列移出畫面）或為他人的列渲染刪除鍵都會讓本案紅。
   *       數值 id 只進 `data-owner-user-id`，不進可見文字（SEC-U15-4）。
   */
  test('owner and scope fields render; a platform memory owned by another user has no delete control', async ({
    page,
  }) => {
    await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}mine`),
      memory('semantic', `${CONTENT_PREFIX}theirs`, { owner: OTHER_ID, scope: 'platform' }),
    ]);
    await openMemoryPage(page);

    const mineOwner = page.getByTestId('memory-item-1-owner');
    await expect(mineOwner).toContainText('你');
    await expect(mineOwner).toHaveAttribute('data-owner-user-id', String(SELF_ID));
    await expect(page.getByTestId('memory-item-1-scope')).toContainText('僅你可見');
    await expect(page.getByTestId('memory-item-1-delete')).toBeVisible();

    await expect(item(page, '2')).toBeVisible();
    const theirsOwner = page.getByTestId('memory-item-2-owner');
    await expect(theirsOwner).toContainText('其他使用者');
    await expect(theirsOwner).toHaveAttribute('data-owner-user-id', String(OTHER_ID));
    expect(await theirsOwner.innerText()).not.toMatch(/\d/);
    await expect(page.getByTestId('memory-item-2-scope')).toContainText('平台可見');
    await expect(page.getByTestId('memory-item-2-delete')).toHaveCount(0);
    await expect(item(page, '2')).toContainText('平台可見（他人的記憶）');
  });

  /**
   * @purpose 刪除經就地確認列；Escape 取消不發請求；確認後該則消失並播報（BR34.1／BR34.2／NFR7.91）。
   * @given 已登入；語意區只有一則自己的記憶
   * @step 點該則的「刪除」 | 就地確認列展開，文字含「不再依據它回答」與「記錄」，焦點在確認鍵
   * @step 按 Escape | 確認列收起，焦點回到「刪除」，**沒有** DELETE 請求
   * @step 再點「刪除」並點確認 | 發出 1 個 DELETE；該則消失；播報「已刪除：…」；語意區轉為空態
   * @pass 取消時請求數為 0、確認後為 1，且畫面與播報如上
   * @story US4.2
   * @api DELETE /api/memory/records/{memory_id} -> 204 | 刪除自己的記憶
   * @ui /memory | 條目的刪除鍵與就地確認列
   * @note 確認文案必須告知「此刪除會被記錄」（ADR-0006 audit logging 面）。
   */
  test('delete uses an inline confirm row; Escape cancels without a request; confirm removes and announces', async ({
    page,
  }) => {
    const stub = await setup(page, [memory('semantic', `${CONTENT_PREFIX}to-delete`)]);
    await openMemoryPage(page);

    await page.getByTestId('memory-item-1-delete').click();
    const confirm = page.getByTestId('memory-item-1-delete-confirm');
    await expect(confirm).toBeFocused();
    const row = page.getByRole('group', { name: '確認刪除' });
    await expect(row).toContainText('不再依據它回答');
    await expect(row).toContainText('記錄');

    await page.keyboard.press('Escape');
    await expect(confirm).toHaveCount(0);
    await expect(page.getByTestId('memory-item-1-delete')).toBeFocused();
    expect(stub.deletes).toHaveLength(0);

    await deleteViaUi(page, '1');
    await expect(item(page, '1')).toHaveCount(0);
    expect(stub.deletes).toEqual(['1']);
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText(
      `已刪除：${CONTENT_PREFIX}to-delete`
    );
    await expect(page.getByTestId('memory-zone-semantic-empty')).toBeVisible();
  });

  /**
   * @purpose 第 1 頁刪除後背景重抓目前頁，使伺服器端位移進來的列出現、下一頁不漏列（審查 R-01）。
   * @given 已登入；情節區 25 則（ep-01…ep-25，依序排列）
   * @step 在第 1 頁刪除 ep-01 與 ep-02 | 兩則消失；第 1 頁出現原第 21、22 則（ep-21、ep-22），範圍「第 1–20 則」
   * @step 點「下一頁」 | 第 2 頁為 ep-23…ep-25，範圍「第 21–23 則」
   * @step 彙整兩頁出現過的則數 | 剩下的 23 則全部出現過，沒有任何一則被跳過
   * @pass 第 1 頁含 ep-22，且兩頁合計涵蓋 23 則
   * @story US4.2
   * @api GET /api/memory/records -> 200 | 情節區分頁與刪除後的背景重抓
   * @api DELETE /api/memory/records/{memory_id} -> 204 | 刪除
   * @ui /memory | 情節記憶區與分頁控件
   * @note 刻意刪**兩**則：第 1 頁的請求是 limit=21，第 21 則已在本地陣列中，只刪
   *       一則時它不重抓也會補上——那樣的案例在「不做背景重抓」的實作下仍然綠。
   *       刪兩則才讓 ep-22 只能來自重抓。
   */
  test('deleting on page 1 resyncs so the shifted record is not skipped', async ({ page }) => {
    const stub = await setup(page, episodes(25));
    await openMemoryPage(page);
    const range = page.getByTestId('memory-pagination-range');
    await expect(range).toHaveText('第 1–20 則');

    await deleteViaUi(page, '1');
    await expect(item(page, '1')).toHaveCount(0);
    await expect(item(page, '21')).toBeVisible();
    await deleteViaUi(page, '2');
    await expect(item(page, '2')).toHaveCount(0);
    await expect(item(page, '22')).toBeVisible();
    await expect(range).toHaveText('第 1–20 則');
    expect(stub.deletes).toEqual(['1', '2']);

    const seen = new Set(
      await zone(page, 'episodic').locator('li[data-testid^="memory-item-"]').evaluateAll((els) =>
        els.map((el) => el.getAttribute('data-testid'))
      )
    );
    await page.getByTestId('memory-pagination-next').click();
    await expect(range).toHaveText('第 21–23 則');
    for (const id of await zone(page, 'episodic').locator('li[data-testid^="memory-item-"]').evaluateAll((els) =>
      els.map((el) => el.getAttribute('data-testid'))
    )) {
      seen.add(id);
    }
    expect(seen.size).toBe(23);
  });

  /**
   * @purpose 背景重抓延遲期間使用者翻頁，舊頁的重抓回應不得覆蓋新頁（序號防亂序，審查 R-02）。
   * @given 已登入；情節區 25 則；刪除後的背景重抓被測試持有的閘門延遲
   * @step 在第 1 頁刪除 ep-01 | 背景重抓發出但未回應
   * @step 點「下一頁」 | 第 2 頁載入，範圍「第 21–24 則」，含 ep-22
   * @step 放行延遲的重抓回應並等它處理完 | 畫面仍是第 2 頁，範圍仍為「第 21–24 則」，不出現 ep-02
   * @pass 舊頁回應被丟棄
   * @story US4.2
   * @api GET /api/memory/records -> 200 | 情節區翻頁與背景重抓
   * @api DELETE /api/memory/records/{memory_id} -> 204 | 刪除
   * @ui /memory | 情節記憶區與分頁控件
   * @note 以 effect 的 `cancelled` flag 防亂序的實作在此會紅：背景重抓不經 effect，
   *       翻頁不會讓它失效。
   */
  test('paging during a delayed resync keeps the newer page', async ({ page }) => {
    const stub = await setup(page, episodes(25));
    const hold = gate();
    stub.getHook = async (q, s) => {
      if (q.kind === 'episodic' && q.offset === '0' && s.deletes.length > 0) await hold.wait;
    };
    await openMemoryPage(page);
    const range = page.getByTestId('memory-pagination-range');

    const resyncFinished = page.waitForEvent(
      'requestfinished',
      (req) => req.method() === 'GET' && req.url().includes('kind=episodic') && req.url().includes('offset=0')
    );
    await deleteViaUi(page, '1');
    await expect(item(page, '1')).toHaveCount(0);
    await expect.poll(() => stub.episodicGets().length).toBe(2);

    await page.getByTestId('memory-pagination-next').click();
    await expect(range).toHaveText('第 21–24 則');
    await expect(item(page, '22')).toBeVisible();

    hold.open();
    await settleAfter(page, resyncFinished);
    await expect(range).toHaveText('第 21–24 則');
    await expect(item(page, '2')).toHaveCount(0);
    await expect(item(page, '22')).toBeVisible();
  });

  /**
   * @purpose 背景重抓失敗時就地提示而不靜默；刪空最後一頁時只退一頁（審查 R-02／R-03）。
   * @given 已登入；(a) 情節區 25 則且重抓回 500；(b) 情節區 41 則
   * @step (a) 在第 1 頁刪除 ep-01 | 該則消失；出現「清單同步失敗，畫面可能不是最新的」並經 live region 播報
   * @step (b) 翻到第 3 頁（只有 ep-41）並刪除它 | 情節區退回第 2 頁，範圍「第 21–40 則」
   * @step (b) 檢視刪除之後的情節區 GET | 恰兩個：offset=40（重抓）與 offset=20（退頁），沒有 offset=0
   * @pass 提示可見且已播報；退頁恰一次且停在第 2 頁
   * @story US4.2
   * @api GET /api/memory/records -> 200 | 重抓與退頁
   * @api GET /api/memory/records -> 403 | 重抓失敗（以 500 模擬同一條錯誤路徑）
   * @api DELETE /api/memory/records/{memory_id} -> 204 | 刪除
   * @ui /memory | 情節記憶區的同步失敗提示與分頁控件
   * @note 刪第 3 頁而非第 2 頁：從第 2 頁退回第 1 頁無法分辨「退一頁」與「退到底」。
   */
  test('resync failure shows a notice; emptying page 3 steps back exactly one page', async ({ page }) => {
    // (a) 重抓失敗
    const stub = await setup(page, episodes(25));
    stub.getHook = (q, s) => (q.kind === 'episodic' && s.deletes.length > 0 ? 500 : undefined);
    await openMemoryPage(page);
    await deleteViaUi(page, '1');
    await expect(item(page, '1')).toHaveCount(0);
    const notice = page.getByTestId('memory-zone-episodic-sync-failed');
    await expect(notice).toHaveText('清單同步失敗，畫面可能不是最新的');
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText(
      '清單同步失敗，畫面可能不是最新的'
    );

    // (b) 刪空第 3 頁：同一個已登入的 session，換一份伺服器資料後重新開頁。
    nextId = 100;
    stub.records = episodes(41);
    stub.getHook = null;
    await openMemoryPage(page);
    const range = page.getByTestId('memory-pagination-range');
    await page.getByTestId('memory-pagination-next').click();
    await expect(range).toHaveText('第 21–40 則');
    await page.getByTestId('memory-pagination-next').click();
    await expect(range).toHaveText('第 41–41 則');

    const before = stub.episodicGets().length;
    await deleteViaUi(page, '140'); // ep-41
    await expect(range).toHaveText('第 21–40 則');
    await expect(item(page, '120')).toBeVisible(); // ep-21
    const after = stub.episodicGets().slice(before).map((g) => g.offset);
    expect(after).toEqual(['40', '20']);
  });

  /**
   * @purpose 記憶內容以文字顯示，不被當成 HTML 執行（security-design §三）。
   * @given 已登入；語意區一則內容為 `<img src=x onerror=window.__xss=1>` 的記憶
   * @step 開啟 `/memory` | 該則以字面文字顯示該字串
   * @step 檢視 DOM 與全域變數 | 該則內沒有 `img` 元素；`window.__xss` 未定義
   * @pass 字串以文字呈現，且未執行
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 回傳含 HTML 字串的記憶
   * @ui /memory | 條目正文
   * @note 引入原始 HTML 注入的實作在此會紅。
   */
  test('memory content renders as text, never as HTML', async ({ page }) => {
    const payload = '<img src=x onerror=window.__xss=1>';
    await setup(page, [memory('semantic', payload)]);
    await openMemoryPage(page);

    await expect(item(page, '1')).toContainText(payload);
    await expect(item(page, '1').locator('img')).toHaveCount(0);
    expect(await page.evaluate(() => (window as unknown as { __xss?: number }).__xss)).toBeUndefined();
  });

  /**
   * @purpose 記憶不跨頁快取、不落地、不進 console（NFR4.90／NFR7.90／SEC-U15-5）。
   * @given 已登入；三區皆有記憶；一次刪除失敗（回 500）以觸發失敗路徑的 console 輸出
   * @step 記下 localStorage／sessionStorage 的鍵集合後開啟 `/memory` | 發出 3 個 GET
   * @step 刪除一則但伺服器回 500 | 該則仍在，顯示刪除失敗
   * @step 以 SPA 導覽離開到 `/403` 再以瀏覽器「上一頁」回來 | 再發出 3 個 GET（共 6 個）
   * @step 比對兩種儲存的鍵集合與 console 輸出 | 鍵集合與開頁前相同；console 不含任何記憶內容
   * @pass GET 共 6 個、儲存鍵無新增、console 不含 `e2e-memory-`
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 每次進頁各區一次
   * @api DELETE /api/memory/records/{memory_id} -> 404 | 失敗路徑（以 500 模擬）
   * @ui /memory | 記憶頁
   * @ui /403 | 離開記憶頁的落點（記憶頁卸載）
   * @note 以 SPA 導覽離開與回來（history.pushState ＋ popstate、再 goBack；不重新載入頁面），模組層快取
   *       才不會被整頁重載掩蓋。原本經 Sidebar 的 DEMO 頁 `/brain` 離開，該頁已隨 U13 移除（`[IG2]`=A），
   *       而無 story 權限的使用者沒有其他 Layout 頁可去。
   */
  test('re-entering the page refetches and leaves no browser storage or console trace', async ({ page }) => {
    const consoleLines: string[] = [];
    page.on('console', (msg) => consoleLines.push(msg.text()));
    const stub = await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}s1`),
      memory('procedure', `${CONTENT_PREFIX}p1`),
      ...episodes(2),
    ]);
    const storageKeys = () =>
      page.evaluate(() => ({
        local: Object.keys(localStorage).sort(),
        session: Object.keys(sessionStorage).sort(),
      }));

    await page.goto('/403');
    const before = await storageKeys();
    await spaNavigate(page, '/memory');
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText('記憶已載入');
    expect(stub.gets).toHaveLength(3);

    stub.deleteStatus = 500;
    await deleteViaUi(page, '1');
    await expect(item(page, '1')).toContainText('刪除失敗');
    await expect(page.getByTestId('memory-item-1-delete')).toBeVisible();

    await spaNavigate(page, '/403');
    await expect(page).toHaveURL(/\/403$/);
    await expect(page.getByTestId('memory-page')).toHaveCount(0);
    await page.goBack();
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText('記憶已載入');
    expect(stub.gets).toHaveLength(6);

    expect(await storageKeys()).toEqual(before);
    const leaked = consoleLines.filter((line) => line.includes(CONTENT_PREFIX));
    expect(leaked).toEqual([]);
    expect(consoleLines.some((line) => line.includes('memory.delete failed: 500'))).toBe(true);
  });

  /**
   * @purpose 刪除在途時翻頁，刪除完成後仍停在新頁、不被拉回舊頁、不搶焦點（審查 R-01，E11）。
   * @given 已登入；情節區 45 則；第 1 頁 ep-01 的 DELETE 被測試持有的閘門延遲
   * @step 在第 1 頁確認刪除 ep-01 | 伺服器收到 DELETE 但未回應
   * @step 點「下一頁」 | 第 2 頁載入，範圍「第 21–40 則」
   * @step 放行 DELETE 並等它處理完 | 背景重抓的是第 2 頁（offset=20），不是第 1 頁；位移進來的 ep-41 出現在第 2 頁
   * @step 檢視情節區 | 範圍仍為「第 21–40 則」，沒有載入骨架，焦點不在區標題
   * @pass 刪除完成後畫面仍是第 2 頁，且刪除之後的情節區 GET 恰為一個 offset=20
   * @story US4.2
   * @api GET /api/memory/records -> 200 | 情節區翻頁與刪除後的背景重抓
   * @api DELETE /api/memory/records/{memory_id} -> 204 | 刪除
   * @ui /memory | 情節記憶區與分頁控件
   * @note 舊實作以按下確認那一刻的頁次（1）重抓：重抓遞增序號而丟掉第 2 頁的回應，
   *       把使用者拉回第 1 頁並把焦點搬到區標題。本案在 ep-41 那一步即紅。
   */
  test('a delete that completes after paging keeps the user on the new page', async ({ page }) => {
    const stub = await setup(page, episodes(45));
    const hold = gate();
    stub.deleteHook = () => hold.wait;
    await openMemoryPage(page);
    const range = page.getByTestId('memory-pagination-range');
    await expect(range).toHaveText('第 1–20 則');

    await deleteViaUi(page, '1');
    await expect.poll(() => stub.deletes).toEqual(['1']);
    await expect(item(page, '1')).toHaveAttribute('aria-disabled', 'true');

    await page.getByTestId('memory-pagination-next').click();
    await expect(range).toHaveText('第 21–40 則');
    const before = stub.episodicGets().length;

    const deleteFinished = page.waitForResponse((res) => res.request().method() === 'DELETE');
    hold.open();
    await settleAfter(page, deleteFinished);

    await expect(item(page, '41')).toBeVisible();
    await expect(range).toHaveText('第 21–40 則');
    await expect(zone(page, 'episodic').locator('[aria-busy="true"]')).toHaveCount(0);
    await expect(page.getByTestId('memory-zone-episodic-error')).toHaveCount(0);
    await expect(zone(page, 'episodic').getByRole('heading', { level: 2 })).not.toBeFocused();
    expect(stub.episodicGets().slice(before).map((g) => g.offset)).toEqual(['20']);
  });

  /**
   * @purpose 刪除完成時翻頁仍在途、且後續的重抓失敗，該區以可重試的錯誤態結束，不停在載入骨架（審查 R-01，E12）。
   * @given 已登入；情節區 45 則；ep-01 的 DELETE 與第一次第 2 頁 GET 皆被閘門延遲；DELETE 放行後的情節區 GET 一律回 500
   * @step 在第 1 頁確認刪除 ep-01，再點「下一頁」 | 情節區進入載入骨架，第 2 頁 GET 在途
   * @step 放行 DELETE | 情節區發出一次後續 GET（offset=20，即使用者要去的那一頁），回 500
   * @step 放行先前在途的第 2 頁 GET | 該回應被丟棄
   * @step 檢視情節區 | 出現 `-error` 與「重試」，沒有載入骨架
   * @step 讓 GET 恢復正常後點「重試」 | 情節區列出記憶，ep-01 不在其中
   * @pass 該區以錯誤態加重試鍵結束，重試可恢復
   * @story US4.2
   * @api GET /api/memory/records -> 200 | 翻頁與重試
   * @api GET /api/memory/records -> 403 | 後續重抓失敗（以 500 模擬同一條錯誤路徑）
   * @api DELETE /api/memory/records/{memory_id} -> 204 | 刪除
   * @ui /memory | 情節記憶區的錯誤態與重試鍵
   * @note 舊實作在此重抓第 1 頁，失敗分支只設「同步失敗」而不離開 loading，第 2 頁的回應
   *       又已被序號丟棄——該區永遠停在骨架、沒有重試鍵，只能重整頁面。
   *       「重試」依既有規則（W3 第 5 步：失敗時頁次不前進）載入最後一次成功顯示的第 1 頁。
   */
  test('a failing refetch after a delete during paging ends in a retryable error', async ({ page }) => {
    const stub = await setup(page, episodes(45));
    const holdDelete = gate();
    const holdFirstPage2 = gate();
    let page2Seen = 0;
    let failAfterDelete = false;
    stub.deleteHook = () => holdDelete.wait;
    stub.getHook = async (q) => {
      if (q.kind !== 'episodic') return undefined;
      if (q.offset === '20' && page2Seen++ === 0) {
        await holdFirstPage2.wait;
        return undefined;
      }
      return failAfterDelete ? 500 : undefined;
    };
    await openMemoryPage(page);
    const episodic = zone(page, 'episodic');

    await deleteViaUi(page, '1');
    await expect.poll(() => stub.deletes).toEqual(['1']);
    await page.getByTestId('memory-pagination-next').click();
    await expect(episodic.locator('div[aria-busy="true"]').first()).toBeVisible();
    await expect.poll(() => stub.episodicGets().length).toBe(2);

    failAfterDelete = true;
    holdDelete.open();
    await expect.poll(() => stub.episodicGets().length).toBe(3);

    const staleFinished = page.waitForEvent(
      'requestfinished',
      (req) => req.method() === 'GET' && req.url().includes('kind=episodic') && req.url().includes('offset=20')
    );
    holdFirstPage2.open();
    await settleAfter(page, staleFinished);

    const retry = page.getByTestId('memory-zone-episodic-retry');
    await expect(retry).toBeVisible();
    await expect(episodic.locator('[aria-busy="true"]')).toHaveCount(0);
    // 後續那一次 GET 打的是使用者要去的第 2 頁，不是按下確認那一刻的第 1 頁。
    expect(stub.episodicGets()[2].offset).toBe('20');

    failAfterDelete = false;
    await retry.click();
    await expect(page.getByTestId('memory-zone-episodic-error')).toHaveCount(0);
    await expect(item(page, '2')).toBeVisible();
    await expect(item(page, '1')).toHaveCount(0);
  });

  /**
   * @purpose 三區的初次請求同時發出，且各自結束：情節區未回應時語意區已渲染（UIP-1，E13）。
   * @given 已登入；三區各一則；三區的初次 GET 都先被閘門擋住
   * @step 開啟 `/memory` | 三個 GET 都已送達伺服器，三區皆為載入骨架
   * @step 放行語意與程序區的 GET | 語意區列出記憶、程序區列出記憶，情節區仍為載入骨架
   * @step 放行情節區的 GET | 情節區列出記憶，頁面播報「記憶已載入」
   * @pass 三個請求在任何回應之前即已發出，且語意區的渲染不等情節區
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 每區一次
   * @ui /memory | 記憶頁三區
   * @note 以 `Promise.all` 等三區都回來才渲染的實作，在第二步即紅；逐區依序發請求的實作，
   *       在第一步（請求數為 3）即紅。
   */
  test('zones load in parallel and the semantic zone renders while the episodic zone is pending', async ({
    page,
  }) => {
    const stub = await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}s1`),
      memory('procedure', `${CONTENT_PREFIX}p1`),
      ...episodes(1),
    ]);
    const holdOthers = gate();
    const holdEpisodic = gate();
    stub.getHook = async (q) => {
      await (q.kind === 'episodic' ? holdEpisodic.wait : holdOthers.wait);
    };
    await page.goto('/memory');
    await expect.poll(() => stub.gets.length).toBe(3);
    for (const fragment of ['semantic', 'procedural', 'episodic']) {
      await expect(zone(page, fragment).locator('div[aria-busy="true"]')).toHaveCount(1);
    }

    holdOthers.open();
    await expect(item(page, '1')).toBeVisible();
    await expect(item(page, '2')).toBeVisible();
    await expect(zone(page, 'episodic').locator('div[aria-busy="true"]')).toBeVisible();
    await expect(item(page, '3')).toHaveCount(0);

    holdEpisodic.open();
    await expect(item(page, '3')).toBeVisible();
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText('記憶已載入');
  });

  /**
   * @purpose 第 2 頁載入在途時連按「下一頁」只發出一個請求，回應到達後停在第 2 頁（UIP-4，E14）。
   * @given 已登入；情節區 65 則；第 2 頁的 GET 被閘門延遲
   * @step 在第 1 頁快速連按兩次「下一頁」 | 「下一頁」在載入期間停用；只發出一個 offset=20 的 GET，沒有 offset=40
   * @step 放行第 2 頁的 GET | 範圍「第 21–40 則」
   * @pass 連按只產生一次翻頁請求，且最後畫面為第 2 頁
   * @story US4.4
   * @api GET /api/memory/records -> 200 | 情節區翻頁
   * @ui /memory | 情節記憶區的分頁控件
   * @note UIP-4 原文的情節是「第 2 頁的回應晚於第 3 頁到達」。那個交錯經由介面**構造不出來**：
   *       載入期間「下一頁」與「上一頁」都停用，且頁次只在回應到達後才前進，故第二次點擊
   *       不可能發出第 3 頁的請求。本案斷言的是讓它構造不出來的那道保護；兩個在途請求
   *       之間的晚到丟棄由序號負責，其可構造的形狀見 E7（重抓與翻頁）與 E11／E12（刪除與翻頁）。
   */
  test('double-clicking next while page 2 is loading sends one request and lands on page 2', async ({ page }) => {
    const stub = await setup(page, episodes(65));
    const hold = gate();
    stub.getHook = async (q) => {
      if (q.kind === 'episodic' && q.offset === '20') await hold.wait;
    };
    await openMemoryPage(page);
    const range = page.getByTestId('memory-pagination-range');
    const next = page.getByTestId('memory-pagination-next');

    await next.dblclick();
    await expect(next).toBeDisabled();
    await expect.poll(() => stub.episodicGets().length).toBe(2);

    const page2Finished = page.waitForEvent(
      'requestfinished',
      (req) => req.method() === 'GET' && req.url().includes('kind=episodic') && req.url().includes('offset=20')
    );
    hold.open();
    await settleAfter(page, page2Finished);
    await expect(range).toHaveText('第 21–40 則');
    expect(stub.episodicGets().map((g) => g.offset)).toEqual(['0', '20']);
  });

  /**
   * @purpose 同一區兩則同時刪除，兩次移除互不覆蓋：兩則都消失且不會回來（UIP-6，E15）。
   * @given 已登入；語意區三則自己的記憶；兩則的 DELETE 各被自己的閘門延遲
   * @step 先後確認刪除第 1、2 則 | 伺服器收到兩個 DELETE，皆未回應
   * @step 放行第 1 則的 DELETE | 第 1 則消失，第 2 則仍在（刪除中）
   * @step 放行第 2 則的 DELETE | 第 2 則消失，第 1 則沒有回來
   * @pass 兩則皆消失，只剩第 3 則，區標題為「1 則」
   * @story US4.2
   * @api DELETE /api/memory/records/{memory_id} -> 204 | 兩次並行的刪除
   * @ui /memory | 語意記憶區的條目與刪除鍵
   * @note 選語意區是因為它**沒有**背景重抓：情節區的重抓會以伺服器回應整份覆蓋，
   *       把移除時用的是 `prev` 還是點擊當下的舊陣列這個差別蓋掉。以舊陣列移除的實作
   *       在第三步會讓第 1 則回來。
   */
  test('two concurrent deletes in one zone both stay removed', async ({ page }) => {
    const stub = await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}a`),
      memory('semantic', `${CONTENT_PREFIX}b`),
      memory('semantic', `${CONTENT_PREFIX}c`),
    ]);
    const holds: Record<string, ReturnType<typeof gate>> = { '1': gate(), '2': gate() };
    stub.deleteHook = (id) => holds[id]?.wait;
    await openMemoryPage(page);

    await deleteViaUi(page, '1');
    await deleteViaUi(page, '2');
    await expect.poll(() => [...stub.deletes].sort()).toEqual(['1', '2']);

    holds['1'].open();
    await expect(item(page, '1')).toHaveCount(0);
    await expect(item(page, '2')).toBeVisible();

    const secondFinished = page.waitForResponse(
      (res) => res.request().method() === 'DELETE' && res.url().endsWith('/records/2')
    );
    holds['2'].open();
    await settleAfter(page, secondFinished);
    await expect(item(page, '2')).toHaveCount(0);
    await expect(item(page, '1')).toHaveCount(0);
    await expect(item(page, '3')).toBeVisible();
    await expect(page.getByTestId('memory-zone-semantic-count')).toHaveText('1 則');
  });

  // -------------------------------------------------------------------------
  // 合併前必修第 6 項（計畫 §四之一）：404 不等於已刪除，重讀清單確認。
  // 計畫與 unit-test-instructions §四之三把這三支編為 E11–E13，與修補輪既有的
  // E11–E15 撞號，故註解以 `MB6-E11`…`MB6-E13` 區分。
  // -------------------------------------------------------------------------

  /**
   * @purpose DELETE 回 404 時重讀該區清單，確認已不含該則才視同已刪除：該列消失並播報（合併前必修第 6 項 MB6-E11，BR34.5）。
   * @given 已登入；語意區兩則自己的記憶；開頁之後伺服器端已清除第 1 則（模擬 90 天清除）
   * @step 對第 1 則確認刪除 | 伺服器回 404；前端隨即再發 1 個語意區 GET（limit=200，不帶 offset）
   * @step 重讀結果不含第 1 則 | 第 1 則消失；播報「已刪除：e2e-memory-purged」；區標題為「1 則」
   * @pass 404 之後恰多 1 個與該區相同參數的 GET，且該列被移除並播報
   * @story US4.2
   * @api DELETE /api/memory/records/{memory_id} -> 404 | 該則已不在伺服器
   * @api GET /api/memory/records -> 200 | 404 之後的確認重讀
   * @ui /memory | 語意記憶區的條目與刪除鍵
   */
  test('a 404 delete counts as deleted only after a re-read no longer lists the record', async ({ page }) => {
    const stub = await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}purged`),
      memory('semantic', `${CONTENT_PREFIX}kept`),
    ]);
    await openMemoryPage(page);
    // 開頁後才從伺服器移除：畫面上仍有它，DELETE 會自然得到 404。
    stub.records = stub.records.filter((r) => r.memory_id !== '1');
    const getsBefore = stub.gets.filter((g) => g.kind === 'semantic').length;

    await deleteViaUi(page, '1');
    await expect(item(page, '1')).toHaveCount(0);
    expect(stub.deletes).toEqual(['1']);
    const semanticGets = stub.gets.filter((g) => g.kind === 'semantic');
    expect(semanticGets).toHaveLength(getsBefore + 1);
    expect(semanticGets[semanticGets.length - 1]).toEqual({ kind: 'semantic', offset: null, limit: '200' });
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText(
      `已刪除：${CONTENT_PREFIX}purged`
    );
    await expect(item(page, '2')).toBeVisible();
    await expect(page.getByTestId('memory-zone-semantic-count')).toHaveText('1 則');
  });

  /**
   * @purpose DELETE 回 404 但重讀該頁仍列出該則（例如路徑錯誤或代理回的 404）時，不得宣稱刪除成功（合併前必修第 6 項 MB6-E12）。
   * @given 已登入；情節區 25 則；伺服器的 DELETE 一律回 404 且不刪除任何東西
   * @step 翻到第 2 頁，對 ep-22 確認刪除 | 伺服器回 404；前端以第 2 頁的參數（offset=20、limit=21）重讀情節區
   * @step 重讀結果仍含 ep-22 | ep-22 仍在畫面上並顯示「刪除失敗」；播報「刪除失敗：e2e-memory-ep-22」
   * @pass ep-22 未被移除、條目內出現「刪除失敗」，確認重讀的 offset 為 20
   * @story US4.2
   * @api DELETE /api/memory/records/{memory_id} -> 404 | 伺服器實際沒有刪除
   * @api GET /api/memory/records -> 200 | 404 之後以當前頁參數重讀
   * @ui /memory | 情節記憶區的條目、刪除鍵與分頁控件
   * @note 突變「404 一律視同已刪除」會讓 ep-22 消失，本案即紅。
   */
  test('a 404 delete whose re-read still lists the record fails and keeps the row', async ({ page }) => {
    const stub = await setup(page, episodes(25));
    await openMemoryPage(page);
    await page.getByTestId('memory-pagination-next').click();
    await expect(page.getByTestId('memory-pagination-range')).toHaveText('第 21–25 則');
    stub.deleteStatus = 404;
    const getsBefore = stub.episodicGets().length;

    await deleteViaUi(page, '22');
    await expect(item(page, '22')).toContainText('刪除失敗');
    expect(stub.deletes).toEqual(['22']);
    const episodicGets = stub.episodicGets();
    expect(episodicGets).toHaveLength(getsBefore + 1);
    expect(episodicGets[episodicGets.length - 1]).toEqual({ kind: 'episodic', offset: '20', limit: '21' });
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText(
      `刪除失敗：${CONTENT_PREFIX}ep-22`
    );
    await expect(item(page, '22')).toBeVisible();
    await expect(page.getByTestId('memory-item-22-delete')).toBeVisible();
  });

  /**
   * @purpose DELETE 回 404 且確認重讀本身失敗時，保守視為未刪除：顯示刪除失敗、保留該列（合併前必修第 6 項 MB6-E13）。
   * @given 已登入；語意區兩則自己的記憶；伺服器的 DELETE 回 404，之後的語意區 GET 回 500
   * @step 對第 1 則確認刪除 | 伺服器回 404；前端重讀語意區，得到 500
   * @step 觀察條目 | 第 1 則仍在並顯示「刪除失敗」；區塊沒有進入錯誤態（其餘列照常顯示）
   * @pass 第 1 則未被移除且含「刪除失敗」，`memory-zone-semantic-error` 不存在
   * @story US4.2
   * @api DELETE /api/memory/records/{memory_id} -> 404 | 是否已刪除未知
   * @api GET /api/memory/records -> 500 | 確認重讀失敗
   * @ui /memory | 語意記憶區的條目與刪除鍵
   */
  test('a 404 delete whose re-read fails is reported as a failure and keeps the row', async ({ page }) => {
    const stub = await setup(page, [
      memory('semantic', `${CONTENT_PREFIX}unknown`),
      memory('semantic', `${CONTENT_PREFIX}other`),
    ]);
    await openMemoryPage(page);
    stub.deleteStatus = 404;
    stub.getHook = (q) => (q.kind === 'semantic' ? 500 : undefined);

    await deleteViaUi(page, '1');
    await expect(item(page, '1')).toContainText('刪除失敗');
    expect(stub.deletes).toEqual(['1']);
    await expect(page.getByTestId('memory-page').getByTestId('live-region')).toHaveText(
      `刪除失敗：${CONTENT_PREFIX}unknown`
    );
    await expect(item(page, '1')).toBeVisible();
    await expect(item(page, '2')).toBeVisible();
    await expect(page.getByTestId('memory-zone-semantic-error')).toHaveCount(0);
    await expect(page.getByTestId('memory-zone-semantic-count')).toHaveText('2 則');
  });
});
