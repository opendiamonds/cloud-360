import { test, expect, type Browser, type Page } from '@playwright/test';

/**
 * U24 member-pages-ui — 專案成員清單／詳情／邀請對話框／交棒橫幅。
 *
 * **全部走 `page.route()` 攔截，不打真實後端**：本單元測的是前端對 `U19` 既有
 * 契約的消費，不是 `U19` 的正確性（`unit-test-instructions.md` §五）。因此本檔
 * **不需要資料庫、不需要後端、不需要 `claude` CLI 或 n8n webhook**，只需要前端
 * 被服務於 `BASE_URL`。
 *
 * **名稱穩定性（落地後不可改）**：`ui-regression.lock.yml` 的 Kiwi 回報步驟逐字
 * 註解「The template must stay stable — it is the key the plugin reuses cases by;
 * **changing it orphans the old cases**」。TCMS 案例名稱為 `<describe> › <test>`，
 * 故本檔的 `describe`（`U24 member pages`）與每個 `test` 字串**一旦合併就不得再改**。
 *
 * 8 個案例逐一對應 `infrastructure-design/cicd-pipeline.md` §五 的斷言標的表。
 */

// ---------------------------------------------------------------------------
// 測試資料。顯示名稱與 email 用**明顯的假值且可搜尋的獨特字串**——案例 7 要
// 斷言 console **不含**它們（`SEC-U24-1`），故它們必須是獨特的（§六）。
// ---------------------------------------------------------------------------

const PROJECT_ID = 7;
const SELF_ID = 1001;
const OTHER_ID = 2002;

const SELF_NAME = 'e2e-user-self';
const OTHER_NAME = 'e2e-user-other';
const INVITEE_NAME = 'e2e-user-invitee';
const SELF_EMAIL = 'e2e-01@example.invalid';

/** 本檔斷言「不得出現在 console」的全部使用者文字與識別字（`SEC-U24-1`）。 */
const USER_TEXT_FORBIDDEN_IN_CONSOLE = [SELF_NAME, OTHER_NAME, INVITEE_NAME, SELF_EMAIL];

type Perm = { view: boolean; edit: boolean; review: boolean };

/**
 * 四個 per-project 管理者控件（`SEC-U24-5`／`canManage` 兩段式）。
 * 兩個在清單頁、兩個在詳情頁，案例 5／6 要求**全部不存在**。
 */
const MANAGER_CONTROLS_ON_LIST = ['member-list-invite-button', 'member-list-row-detail-link'];
const MANAGER_CONTROLS_ON_DETAIL = ['member-detail-role-select', 'member-detail-remove'];

interface MemberStub {
  user_id: number;
  display_name: string;
  role: string;
  joined_at: string;
}

function member(user_id: number, display_name: string, role: string): MemberStub {
  return { user_id, display_name, role, joined_at: '2026-01-01T00:00:00Z' };
}

interface StubConfig {
  /** `can("K3", …)` 的來源：伺服器下發的 `user.permissions`。 */
  k3: Perm;
  /** 其他 story 的權限（例如 `C1`），預設不給。 */
  extraPermissions?: Record<string, Perm>;
  /** `list_members` 的回應。 */
  members?: MemberStub[];
  /** `list_members` 改回這個狀態碼（測失敗路徑）。 */
  membersStatus?: number;
  /** `membersStatus` 非 200 時的回應本體（預設 `{ detail: '讀取失敗' }`）。 */
  membersErrorBody?: unknown;
  /** `GET /reselections/pending` 的回應。 */
  reselections?: unknown[];
  /** `GET /reselections/pending` 改回這個狀態碼。 */
  reselectionsStatus?: number;
}

/** 收集到的 `/api/membership` 請求（`method` ＋ `url`），供請求數斷言使用。 */
interface Recorder {
  all: { method: string; url: string }[];
  membersGets: () => number;
  reselectionGets: () => number;
}

/**
 * 佈置一個已登入的前端：seed token、攔截 `/api/auth/me` 以控制全域權限、
 * 攔截六個 `/api/membership` 端點。
 *
 * 權限與 per-project 角色是**兩個獨立的旋鈕**，這正是 `canManage` 兩段式所需：
 * `k3` 控制全域 `can("K3", …)`，`members` 裡自己那一列的 `role` 控制 per-project。
 */
/**
 * 被 Layout 包覆、且**沒有** CapabilityRoute 的中性落地頁。原本是 DEMO 的 `/brain`，該頁已隨 U13 移除
 * （`[IG2]`=A）；`/memory` 是剩下唯一同形的頁面。它會打 `/api/memory/records`，故 `setupApp` 一併以空清單攔截，
 * 使本檔的計數與 console 斷言不受記憶頁影響。
 */
const NEUTRAL_LANDING = '/memory';

async function setupApp(page: Page, cfg: StubConfig): Promise<Recorder> {
  const recorder: Recorder = {
    all: [],
    membersGets: () =>
      recorder.all.filter((r) => r.method === 'GET' && /\/members(\?|$)/.test(r.url)).length,
    reselectionGets: () =>
      recorder.all.filter((r) => r.method === 'GET' && r.url.includes('/reselections/pending'))
        .length,
  };

  // 以 request 事件計數，與 route 攔截互相獨立——攔截順序不影響計數。
  page.on('request', (req) => {
    const url = req.url();
    if (url.includes('/api/membership/')) {
      recorder.all.push({ method: req.method(), url });
    }
  });

  await page.addInitScript(() => {
    // AuthProvider 由 sessionStorage 的 token 啟動初始化並打 /api/auth/me。
    sessionStorage.setItem('token', 'e2e-token');
  });

  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: SELF_ID,
        username: SELF_NAME,
        role: 'Project_Admin',
        is_active: true,
        authorization_status: 'approved',
        permissions: { K3: cfg.k3, ...(cfg.extraPermissions ?? {}) },
        pending_request: null,
      }),
    });
  });

  // 中性落地頁（記憶頁）的讀取：一律空清單，不打到真後端。
  await page.route('**/api/memory/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });

  // 單一 dispatcher 處理全部六個端點：避免 Playwright 的「後註冊者優先」造成
  // 的比對順序歧義，也讓每個端點的回應在同一處可讀。
  await page.route('**/api/membership/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method();

    if (method === 'GET' && path.endsWith('/reselections/pending')) {
      if (cfg.reselectionsStatus && cfg.reselectionsStatus !== 200) {
        await route.fulfill({
          status: cfg.reselectionsStatus,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'nope' }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'Cache-Control': 'no-store' },
        body: JSON.stringify(cfg.reselections ?? []),
      });
      return;
    }

    if (method === 'GET' && /\/members$/.test(path)) {
      if (cfg.membersStatus && cfg.membersStatus !== 200) {
        await route.fulfill({
          status: cfg.membersStatus,
          contentType: 'application/json',
          body: JSON.stringify(cfg.membersErrorBody ?? { detail: '讀取失敗' }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(cfg.members ?? []),
      });
      return;
    }

    // 未被個別案例覆寫的寫入端點：回 500，讓「不該被呼叫」的路徑明顯失敗
    // 而不是靜默成功。
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'not stubbed' }),
    });
  });

  return recorder;
}

/** 收集 console 輸出（案例 7 用）。必須在導航**之前**掛上。 */
function collectConsole(page: Page): string[] {
  const lines: string[] = [];
  page.on('console', (msg) => lines.push(msg.text()));
  return lines;
}

const K3_FULL: Perm = { view: true, edit: true, review: false };
/** `FinOps_Analyst`／`Security_Reviewer`／`Platform_Owner` 的實測形狀（view 有、edit 無）。 */
const K3_VIEW_ONLY: Perm = { view: true, edit: false, review: false };
/** `SRE`／`Ops_Lead`／`Platform_Engineer` 的實測形狀（三旗標皆 False）。 */
const K3_NONE: Perm = { view: false, edit: false, review: false };

const membersUrl = (projectId = PROJECT_ID) => `/projects/${projectId}/members`;
const memberDetailUrl = (userId: number, projectId = PROJECT_ID) =>
  `/projects/${projectId}/members/${userId}`;

test.describe('U24 member pages', () => {
  /**
   * @purpose 成員超過 100 位時清單仍渲染並以每頁 50 位分頁，最後一位成員可翻頁到達且可管理（合併前必修第 9 項）。
   * @api GET /api/membership/projects/{project_id}/members -> 200 | 回傳全部 101 位成員
   * @ui /projects/:projectId/members | 成員清單頁：表格、分頁列（上一頁／下一頁、第 N／M 頁、共 K 位）
   * @ui /projects/:projectId/members/:userId | 由第 3 頁的詳情連結進入的成員詳情頁
   * @given 以具 K3 view+edit 的帳號登入，自身在該專案的 role 為 project_admin，list_members 回 101 位
   * @step 開啟成員頁 | 表格存在，本頁 50 列，分頁列顯示「第 1／3 頁、共 101 位」，上一頁停用
   * @step 按兩次下一頁 | 分頁列顯示「第 3／3 頁、共 101 位」，本頁 1 列且為第 101 位，下一頁停用
   * @step 點第 101 位那一列的詳情連結 | 進入該成員的詳情頁，角色下拉可見
   * @pass 101 位時清單存在且第 101 位可經翻頁到達並進入其管理頁；整個過程 list_members 只被請求一次
   * @story US12.1
   */
  test('paginates more than 100 members 50 per page so every member stays reachable', async ({
    page,
  }) => {
    // 先前的 100 列整表隱藏閘讓 101 人的專案**整張表**不渲染——本頁是管理成員
    // 的唯一入口，於是連「移除成員回到 100 以下」都做不到（merge-blockers #9）。
    // 還原該閘時，本案例的第一個斷言（表格存在）即紅燈。
    const over = [
      member(SELF_ID, SELF_NAME, 'project_admin'),
      ...Array.from({ length: 100 }, (_, i) => member(3000 + i, `e2e-user-${i}`, 'member')),
    ];
    expect(over).toHaveLength(101);
    const lastId = over[100].user_id;
    const rec = await setupApp(page, { k3: K3_FULL, members: over });
    await page.goto(membersUrl());

    const table = page.getByTestId('member-list-table');
    const rows = table.locator('tbody tr');
    await expect(table).toBeVisible();
    await expect(rows).toHaveCount(50);
    await expect(page.getByTestId('member-list-page-info')).toHaveText('第 1／3 頁、共 101 位');
    await expect(page.getByTestId('member-list-prev-page')).toBeDisabled();
    await expect(page.getByTestId(`member-list-row-${lastId}`)).toHaveCount(0);

    await page.getByTestId('member-list-next-page').click();
    await expect(page.getByTestId('member-list-page-info')).toHaveText('第 2／3 頁、共 101 位');
    await expect(rows).toHaveCount(50);
    await page.getByTestId('member-list-next-page').click();
    await expect(page.getByTestId('member-list-page-info')).toHaveText('第 3／3 頁、共 101 位');
    await expect(rows).toHaveCount(1);
    await expect(page.getByTestId('member-list-next-page')).toBeDisabled();

    // 第 101 位在畫面上，且其管理控件（具 canManage 時的詳情連結）可用。
    const lastRow = page.getByTestId(`member-list-row-${lastId}`);
    await expect(lastRow).toBeVisible();
    // 切頁不發請求：整個翻頁過程對 members 端點只有掛載時那一次（`UIP-4`）。
    expect(rec.membersGets()).toBe(1);
    await lastRow.getByTestId('member-list-row-detail-link').click();
    await expect(page).toHaveURL(new RegExp(`${memberDetailUrl(lastId)}$`));
    await expect(page.getByTestId('member-detail-role-select')).toBeVisible();
  });

  /**
   * @purpose 恰 100 位成員時分頁為 2 頁——頁數計算的邊界不得 off-by-one。
   * @api GET /api/membership/projects/{project_id}/members -> 200 | 回傳 100 位成員
   * @ui /projects/:projectId/members | 成員清單頁的分頁列
   * @given 以具 K3 view+edit 的帳號登入，自身 role 為 project_admin，list_members 回 100 位
   * @step 開啟成員頁 | 表格存在，本頁 50 列，分頁列顯示「第 1／2 頁、共 100 位」
   * @step 按下一頁 | 分頁列顯示「第 2／2 頁、共 100 位」，本頁 50 列，下一頁停用
   * @pass 100 位恰為 2 頁、每頁 50 列；不出現第 3 頁
   * @story US12.1
   */
  test('splits exactly 100 members into two pages of 50', async ({ page }) => {
    const exact = [
      member(SELF_ID, SELF_NAME, 'project_admin'),
      ...Array.from({ length: 99 }, (_, i) => member(3000 + i, `e2e-user-${i}`, 'member')),
    ];
    expect(exact).toHaveLength(100);
    await setupApp(page, { k3: K3_FULL, members: exact });
    await page.goto(membersUrl());

    const rows = page.getByTestId('member-list-table').locator('tbody tr');
    await expect(rows).toHaveCount(50);
    await expect(page.getByTestId('member-list-page-info')).toHaveText('第 1／2 頁、共 100 位');
    await page.getByTestId('member-list-next-page').click();
    await expect(page.getByTestId('member-list-page-info')).toHaveText('第 2／2 頁、共 100 位');
    await expect(rows).toHaveCount(50);
    await expect(page.getByTestId('member-list-next-page')).toBeDisabled();
  });

  /**
   * @purpose 橫幅查詢每次 Layout 掛載恰一次且不快取；缺 K3 view 的角色完全不發出該請求。
   * @api GET /api/membership/reselections/pending -> 200 | 回傳自己未確認的改選事件
   * @ui /memory | 任何被 Layout 包覆的落地頁（本案例用不需 K3 的 /memory 以隔離變數）
   * @given 兩個瀏覽器環境，唯一差異是 K3 的 view 旗標（其餘設定完全相同）
   * @step 以具 K3 view 的帳號連續落地兩次 | 對 reselections/pending 的請求數為 2
   * @step 以 K3 三旗標皆 false 的帳號連續落地兩次 | 對 reselections/pending 的請求數為 0
   * @pass 有權限者請求數等於落地次數；無權限者為 0（前置 can() 判定，非 BR21.3 的重試語意）
   * @story US12.4
   */
  test('queries pending reselections once per landing and not at all without K3 view', async ({
    browser,
  }: {
    browser: Browser;
  }) => {
    // 兩個分支都落在中性頁 `/memory`——它由 Layout 包覆但**沒有** CapabilityRoute，
    // 故兩個分支唯一的差異就是 K3 旗標。若用成員頁，缺 K3 view 者會被
    // CapabilityRoute 導去 /403（不含 Layout），那樣的 0 是「橫幅沒渲染」
    // 而不是「渲染了但沒發請求」——兩者在計數上長得一樣，但只有後者是 `UIP-2`。
    //
    // **同步點不可以用「宿主已出現」**：宿主是**無條件**渲染的（`BR21.1`），
    // 它在 `/api/auth/me` 回來之前就在 DOM 裡了，所以 `toBeAttached()` 完全
    // 不代表那一次落地的橫幅請求已經發出。實測（本輪的診斷 spec）：以它作為
    // 同步點時，第二次 `goto` 會在第一次的請求發出前就把它取消
    // （`net::ERR_ABORTED`）或直接搶先，總數因此停在 1，案例以約 50% 的機率
    // 偽紅。改以**每次落地各自等到該次請求被記錄**為同步點。
    const withView = await browser.newContext();
    const pageA = await withView.newPage();
    const recA = await setupApp(pageA, { k3: K3_FULL, reselections: [] });
    for (const landing of [1, 2]) {
      const mePromise = pageA.waitForResponse('**/api/auth/me');
      await pageA.goto(NEUTRAL_LANDING);
      await mePromise;
      await expect(pageA.getByTestId('reselection-banner-host')).toBeAttached();
      // 等到第 N 次落地的請求真的被記錄，才進行下一次落地。
      await expect.poll(() => recA.reselectionGets()).toBe(landing);
    }
    expect(recA.reselectionGets()).toBe(2);
    await withView.close();

    const withoutView = await browser.newContext();
    const pageB = await withoutView.newPage();
    const recB = await setupApp(pageB, { k3: K3_NONE, reselections: [] });
    for (const landing of [1, 2]) {
      const mePromise = pageB.waitForResponse('**/api/auth/me');
      await pageB.goto(NEUTRAL_LANDING);
      // 兩個 happens-after 訊號，使「0」不是「還沒來得及發」的假 0：
      //   ① `/api/auth/me` 的回應已到（權限已送達）；
      //   ② 側欄已顯示使用者名稱——它來自 `user?.username`，故這一格只在
      //      `applyUser` 的那次 commit 之後才會出現，而該 commit 的 effect
      //      就是橫幅決定要不要發請求的地方。
      await mePromise;
      await expect(pageB.getByText(SELF_NAME)).toBeVisible();
      await expect(pageB.getByTestId('reselection-banner-host')).toBeAttached();
      // 宿主有渲染，但請求數必須是 0。若實作改用 `BR21.3` 的重試語意
      // （先發一次、收到 403 才停），這裡會是 landing 次而紅燈。
      expect(recB.reselectionGets()).toBe(0);
      expect(landing).toBeLessThanOrEqual(2);
    }
    await withoutView.close();
  });

  /**
   * @purpose 邀請、改角色、移出三種操作成功後，處理器都不整份重抓成員清單。
   * @api POST /api/membership/projects/{project_id}/members -> 201 | 邀請成員
   * @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 200 | 變更角色
   * @api DELETE /api/membership/projects/{project_id}/members/{user_id} -> 204 | 移出成員
   * @ui /projects/:projectId/members | 清單頁（邀請）與詳情頁（改角色、移出）
   * @given 以 project_admin 且具 K3 view+edit 的帳號開啟成員頁
   * @step 邀請一位成員並等新列出現 | list_members 的請求數不增加，清單多一列
   * @step 進入詳情頁改角色並儲存 | list_members 的請求數不增加，角色就地更新
   * @step 在詳情頁移出該成員 | DELETE 之後只有一次 list_members（清單頁自己的掛載抓取），不是兩次
   * @pass 三種操作都沒有讓處理器呼叫清單抓取函式
   * @story US12.6
   */
  test('updates the list in place after invite, role change and removal without refetching it', async ({
    page,
  }) => {
    const initial = [
      member(SELF_ID, SELF_NAME, 'project_admin'),
      member(OTHER_ID, OTHER_NAME, 'member'),
    ];
    // 審查 `R-06`：`BR25.2` 的 observable 是「204 後清單少一列」，而固定回同一份
    // `members` 的夾具**與該宣稱相反**——導回清單頁重抓到的清單仍含被移出者，
    // 於是「移出的結果會呈現在清單上」只是預測而非已驗證。改為可變夾具。
    let removed = false;
    const rec = await setupApp(page, {
      k3: K3_FULL,
      get members() {
        return removed ? initial.filter((m) => m.user_id !== OTHER_ID) : initial;
      },
    } as never);

    // 三個寫入端點各自覆寫（在 dispatcher 之後註冊 → 優先比對）。
    await page.route('**/api/membership/projects/*/members', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(member(3333, INVITEE_NAME, 'member')),
      });
    });
    await page.route('**/api/membership/projects/*/members/*', async (route) => {
      const m = route.request().method();
      if (m === 'PATCH') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(member(OTHER_ID, OTHER_NAME, 'project_admin')),
        });
        return;
      }
      if (m === 'DELETE') {
        removed = true;
        await route.fulfill({ status: 204, body: '' });
        return;
      }
      return route.fallback();
    });

    await page.goto(membersUrl());
    await expect(page.getByTestId('member-list-table')).toBeVisible();
    const afterLoad = rec.membersGets();
    expect(afterLoad).toBe(1);

    // ① 邀請：停在清單頁，故「不重抓」可嚴格斷言為 0 差額。
    await page.getByTestId('member-list-invite-button').click();
    await page.getByTestId('invite-dialog-user-id').fill('3333');
    await page.getByTestId('invite-dialog-submit').click();
    await expect(page.getByTestId('member-list-row-3333')).toBeVisible();
    expect(rec.membersGets()).toBe(afterLoad);

    // ② 改角色：停在詳情頁，同樣可嚴格斷言 0 差額。
    await page.goto(memberDetailUrl(OTHER_ID));
    await expect(page.getByTestId('member-detail-role-select')).toBeVisible();
    const afterDetailLoad = rec.membersGets();
    await page.getByTestId('member-detail-role-select').selectOption('project_admin');
    await page.getByTestId('member-detail-save').click();
    await expect(page.getByTestId('member-detail-role-select')).toHaveValue('project_admin');
    expect(rec.membersGets()).toBe(afterDetailLoad);

    // ③ 移出：成功後導回清單頁，而清單頁掛載時**本來就會**抓一次（那是
    // `UIP-4` 的那一次請求）。所以這裡斷言的不是「0 差額」而是**差額恰為 1**
    // ——若 `handleRemove` 自己也呼叫了清單抓取函式，DELETE 之後會有**兩次**
    // GET 而非一次，此斷言即紅燈。這是「處理器不得重抓」真正的可失敗面。
    const beforeRemove = rec.membersGets();
    await page.getByTestId('member-detail-remove').click();
    await page.getByTestId('remove-confirm-accept').click();
    await expect(page).toHaveURL(new RegExp(`${membersUrl()}$`));
    await expect(page.getByTestId('member-list-table')).toBeVisible();

    // `BR25.2` 的 observable：被移出者的那一列**不再存在**（審查 `R-06`）。
    await expect(page.getByTestId(`member-list-row-${OTHER_ID}`)).toHaveCount(0);

    // **不用 `expect.poll`**（審查 `R-05`）：poll 在**第一次**觀測到相符值時就
    // 通過，所以它不是 settled-count 斷言——突變下的序列是「重抓 +1」再「清單頁
    // 掛載 +2」，若取樣落在兩者之間就會看到 1 而綠燈。先等到可判定的終點
    // （網路靜止＝兩次 GET 都已落地），再以一般 `expect` 斷言終值。
    await page.waitForLoadState('networkidle');
    expect(rec.membersGets()).toBe(beforeRemove + 1);
  });

  /**
   * @purpose 成員清單首次可互動前只呼叫 list_members 一次——canManage 不另發請求。
   * @api GET /api/membership/projects/{project_id}/members -> 200 | 回傳成員清單
   * @ui /projects/:projectId/members | 成員清單頁
   * @given 以 project_admin 且具 K3 view+edit 的帳號開啟成員頁
   * @step 開啟成員頁並等到管理者控件可互動 | 對 members 端點的請求數為 1
   * @step 檢視同期的全部 /api/membership 請求 | 共 2 次：members 1 次 ＋ 橫幅 1 次（UIP-2 所要求）
   * @pass canManage 由 list_members 的同一份回應推得，不產生第二次 members 請求
   * @story US12.1
   */
  test('issues exactly one member-list request before the page is interactive', async ({
    page,
  }) => {
    const rec = await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
      reselections: [],
    });
    await page.goto(membersUrl());
    // 可互動的判準：管理者控件已渲染（即 `canManage` 已算出）。
    await expect(page.getByTestId('member-list-invite-button')).toBeEnabled();
    expect(rec.membersGets()).toBe(1);

    // `BR27.1`：載入／錯誤態一律經**帶 `role` 的** live region 播報，
    // 不得沿用 `AdminPage.tsx:104` 的 4 秒 toast（實測無 `role`／`aria-live`）。
    // 本單元自建該元件（`[N4]`=A／`HO-U24-1`），`U23` 之後沿用同一個形狀。
    const live = page.getByTestId('live-region').first();
    await expect(live).toHaveAttribute('role', 'status');
    await expect(live).not.toHaveText('');

    // `performance-requirements.md` §二 的 `UIP-4` 字面寫「對 `/api/membership/**`
    // 的請求數為 1」，但橫幅宿主在 `Layout` 裡且 `UIP-2` 要求它**每次掛載恰 1 次**
    // ——兩條要求在同一個前綴下不可能同時為 1。此處如實斷言 2（members 1 ＋
    // 橫幅 1），`UIP-4` 的實質內容（canManage 不另發請求）由上一個斷言承擔。
    // 同 `R-05`：先等網路靜止再斷言終值，不用首次命中即通過的 poll。
    await page.waitForLoadState('networkidle');
    expect(rec.all.length).toBe(2);
    expect(rec.reselectionGets()).toBe(1);
  });

  /**
   * @purpose per-project 為 project_admin 但缺全域 K3.edit 時，四個管理者控件全部不存在。
   * @api GET /api/membership/projects/{project_id}/members -> 200 | 自身那列的 role 為 project_admin
   * @ui /projects/:projectId/members | 清單頁的邀請鈕與詳情連結
   * @ui /projects/:projectId/members/:userId | 詳情頁的角色下拉與移出鈕
   * @given 以 K3 view=true／edit=false 的帳號登入（FinOps_Analyst 等三個角色的實測形狀），自身 per-project role 為 project_admin
   * @step 開啟成員頁 | 邀請鈕與詳情連結皆 0 命中，清單本身仍可見（唯讀）
   * @step 直接以 URL 開啟成員詳情頁 | 角色下拉與移出鈕皆 0 命中
   * @pass 四個控件全部不存在——缺 K3.edit 時不渲染永久會 403 的控件
   * @story US12.2
   */
  test('hides all four manager controls for a project admin lacking global K3 edit', async ({
    page,
  }) => {
    // 這是審查 R-01 查出的**可達壞狀態**：受邀者把關只要求 K3 view
    // （`membership_service.py:72` 的 `REQUIRED_INVITEE_ACTION = "view"`），
    // 且自動改選直接設 project_admin 而**無任何 K3.edit 過濾**。缺此斷言，
    // 「控件渲染後每次寫入永久 403」的死循環不會被任何閘門抓到。
    await setupApp(page, {
      k3: K3_VIEW_ONLY,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
    });
    await page.goto(membersUrl());
    await expect(page.getByTestId('member-list-table')).toBeVisible();
    for (const id of MANAGER_CONTROLS_ON_LIST) {
      await expect(page.getByTestId(id)).toHaveCount(0);
    }

    await page.goto(memberDetailUrl(OTHER_ID));
    await expect(page.getByTestId('member-detail-page')).toBeVisible();
    for (const id of MANAGER_CONTROLS_ON_DETAIL) {
      await expect(page.getByTestId(id)).toHaveCount(0);
    }
  });

  /**
   * @purpose 本專案的一般成員看到唯讀清單——四個管理者控件全部不存在，即使全域 K3.edit 為真。
   * @api GET /api/membership/projects/{project_id}/members -> 200 | 自身那列的 role 為 member
   * @ui /projects/:projectId/members | 清單頁的邀請鈕與詳情連結
   * @ui /projects/:projectId/members/:userId | 詳情頁的角色下拉與移出鈕
   * @given 以具 K3 view+edit 的帳號登入，但自身在該專案的 per-project role 為 member
   * @step 開啟成員頁 | 清單可見，邀請鈕與詳情連結皆 0 命中
   * @step 直接以 URL 開啟成員詳情頁 | 角色下拉與移出鈕皆 0 命中
   * @pass 全域權限充足但 per-project 非管理者時四個控件皆不存在——證明前端沒有改用全域角色推導
   * @story US12.1
   */
  test('shows a read-only list to a plain project member even with global K3 edit', async ({
    page,
  }) => {
    // 全域 edit **刻意給足**：這樣四個控件消失的唯一原因只能是 per-project
    // 那一段。若前端改用全域角色推導 per-project 結論（違反不變量 I-5），
    // 控件會出現而此案例紅燈——這是 `BR22.3` 的 observable。
    await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'member'), member(OTHER_ID, OTHER_NAME, 'project_admin')],
    });
    await page.goto(membersUrl());
    await expect(page.getByTestId('member-list-table')).toBeVisible();
    await expect(page.getByTestId(`member-list-row-${OTHER_ID}`)).toBeVisible();
    for (const id of MANAGER_CONTROLS_ON_LIST) {
      await expect(page.getByTestId(id)).toHaveCount(0);
    }
    // 清單列上不得有任何可直接改角色的控件（`AC12.2.3`／`BR22.2`）。
    await expect(page.getByTestId('member-list-table').locator('select')).toHaveCount(0);

    await page.goto(memberDetailUrl(OTHER_ID));
    await expect(page.getByTestId('member-detail-page')).toBeVisible();
    for (const id of MANAGER_CONTROLS_ON_DETAIL) {
      await expect(page.getByTestId(id)).toHaveCount(0);
    }
  });

  /**
   * @purpose 三條對使用者無聲的失敗路徑各輸出一筆 console 訊號，且訊號不含任何使用者文字或識別字。
   * @api GET /api/membership/projects/{project_id}/members -> 500 | 清單抓取失敗
   * @api GET /api/membership/reselections/pending -> 403 | 橫幅查詢被拒（永久失敗）
   * @api POST /api/membership/projects/{project_id}/members -> 422 | detail 為物件陣列的驗證錯誤
   * @ui /projects/:projectId/members | 清單頁與邀請對話框
   * @given 以具 K3 view+edit 的帳號登入，逐一構造三條失敗路徑並以 page.on('console') 收集輸出
   * @step 令 list_members 回 500 並開啟成員頁 | console 出現 members-fetch-failed 訊號
   * @step 令 reselections/pending 回 403 後重新落地 | console 出現 banner-forbidden 訊號
   * @step 令 reselections/pending 回 500 後重新落地 | console 出現 banner-fetch-failed 訊號
   * @step 令邀請回 422 且 detail 為物件陣列並送出 | console 出現 invite-validation-failed，畫面不出現 [object Object]
   * @pass 四種失敗各有相符訊號，且全部 console 輸出不含測試帳號的顯示名稱或 email
   * @story US12.4
   */
  test('emits a console signal for every user-silent failure path without leaking user text', async ({
    page,
  }) => {
    const lines = collectConsole(page);

    // ① 清單抓取失敗（500）。使用者看得到錯誤文字，但例外的來源無聲 → 仍須訊號。
    await setupApp(page, { k3: K3_FULL, membersStatus: 500 });
    await page.goto(membersUrl());
    await expect(page.getByTestId('member-list-error')).toBeVisible();
    await expect
      .poll(() => lines.some((l) => l.includes('members-fetch-failed')))
      .toBe(true);

    // ② 橫幅查詢的 403（永久失敗）。整條路徑對使用者完全無聲（`BR21.3`：
    // 宿主保持空、不顯示錯誤），故訊號是它唯一的可觀察面。
    await page.unrouteAll();
    await setupApp(page, { k3: K3_FULL, members: [], reselectionsStatus: 403 });
    await page.goto(NEUTRAL_LANDING);
    await expect.poll(() => lines.some((l) => l.includes('banner-forbidden'))).toBe(true);

    // ③ 橫幅查詢的 500。`SEC-U24-6` 的兜底規則逐字要求「任何非 2xx 與網路失敗」
    // 都有訊號——**不只 403**。只為 403 訂義務會讓 5xx 與網路錯誤成為新的靜默面。
    await page.unrouteAll();
    await setupApp(page, { k3: K3_FULL, members: [], reselectionsStatus: 500 });
    await page.goto(NEUTRAL_LANDING);
    await expect.poll(() => lines.some((l) => l.includes('banner-fetch-failed'))).toBe(true);

    // ④ 邀請的 422＋**物件陣列** detail（pydantic 驗證錯誤）。使用者只看到一句
    // 通用文案，真實原因無聲 → 須訊號；且畫面**不得**把陣列當文案渲染。
    await page.unrouteAll();
    await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin')],
    });
    await page.route('**/api/membership/projects/*/members', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: [{ loc: ['body', 'role'], msg: 'value is not a valid enumeration member', type: 'enum' }],
        }),
      });
    });
    await page.goto(membersUrl());
    await page.getByTestId('member-list-invite-button').click();
    await page.getByTestId('invite-dialog-user-id').fill('4444');
    await page.getByTestId('invite-dialog-submit').click();
    await expect(page.getByTestId('invite-dialog-error')).toBeVisible();
    // 對話框**停在開啟態**且清單不新增任何列（`AC12.5.3`）。
    await expect(page.getByTestId('invite-dialog')).toBeVisible();
    await expect(page.getByTestId('member-list-row-4444')).toHaveCount(0);
    // `SEC-U24-4`：不得把非字串 detail 當文案渲染。
    await expect(page.locator('body')).not.toContainText('[object Object]');
    await expect(page.locator('body')).not.toContainText('enumeration member');
    await expect
      .poll(() => lines.some((l) => l.includes('invite-validation-failed')))
      .toBe(true);

    // `SEC-U24-1`：本 repo 為 public、Actions log 公開可讀，一次意外輸出即等同
    // 公開發布。全部 console 輸出不得含任何使用者文字或識別字。
    const joined = lines.join('\n');
    for (const secret of USER_TEXT_FORBIDDEN_IN_CONSOLE) {
      expect(joined).not.toContain(secret);
    }
  });

  /**
   * @purpose 交棒橫幅的宿主無條件渲染且帶 role="status"，即使查詢失敗、即使零筆事件。
   * @api GET /api/membership/reselections/pending -> 500 | 橫幅查詢失敗
   * @ui /memory | Layout 內的常駐橫幅宿主
   * @given 以具 K3 view 的帳號落地，橫幅查詢分別構造為失敗與回傳兩筆事件
   * @step 令 reselections/pending 回 500 並落地 | 宿主存在、role 屬性等於 status、textContent 為空、畫面無錯誤文字
   * @step 改為回兩筆事件並落地 | 宿主出現彙總文案，role 仍為 status
   * @step 展開專案清單再收合 | 宿主的 textContent 前後不變（動作列在宿主之外）
   * @pass 宿主在三種情況下都存在且 role 為 status；可互動內容不在宿主之內
   * @story US12.4
   */
  test('always renders the reselection banner host with role status', async ({ page }) => {
    // 兩個斷言**缺一不可**：只驗選擇器命中時，把 `role` 屬性整個拿掉仍會綠燈，
    // 而 `role="status"` 正是 `BR21.1` 自述的結構前提——`aria-live` 掛在稍後
    // 才插入的元素上不會被朗讀。
    await setupApp(page, { k3: K3_FULL, reselectionsStatus: 500 });
    await page.goto(NEUTRAL_LANDING);
    const host = page.getByTestId('reselection-banner-host');
    await expect(host).toBeAttached();
    await expect(host).toHaveAttribute('role', 'status');
    // 抓取失敗時宿主保持空、且**不對使用者顯示錯誤**（`BR21.3`／`BR21.2`：
    // 載入中也不渲染骨架——橫幅是通知不是內容，骨架會變成一則假通知）。
    await expect(host).toHaveText('');
    await expect(page.getByTestId('reselection-banner-acknowledge')).toHaveCount(0);

    // 有事件時：宿主帶文案，且 role 不變。
    await page.unrouteAll();
    await setupApp(page, {
      k3: K3_FULL,
      reselections: [
        { id: 11, project_id: 71, cause: 'auto_reselection', promoted_user_id: SELF_ID, new_role: 'project_admin' },
        { id: 12, project_id: 72, cause: 'auto_reselection', promoted_user_id: SELF_ID, new_role: 'project_admin' },
      ],
    });
    await page.goto(NEUTRAL_LANDING);
    const host2 = page.getByTestId('reselection-banner-host');
    await expect(host2).toHaveAttribute('role', 'status');
    await expect(host2).toContainText('2 個專案');

    // 展開／收合**不改變宿主的 textContent**（審查 R-06）：`role="status"`
    // 隱含 `aria-atomic="true"`，若把可展開清單與兩個動作鈕巢在宿主之內，
    // 每按一次就會把整則橫幅重讀一次。axe 不會回報這一類問題。
    const before = await host2.textContent();
    await page.getByTestId('reselection-banner-expand').click();
    await expect(page.getByTestId('reselection-banner-projects')).toBeVisible();
    expect(await host2.textContent()).toBe(before);
    await page.getByTestId('reselection-banner-expand').click();
    await expect(page.getByTestId('reselection-banner-projects')).toHaveCount(0);
    expect(await host2.textContent()).toBe(before);
  });

  /**
   * @purpose 確認交棒事件時，404 視為成功（事件消失）；而真正的失敗不得被當成成功。
   * @api POST /api/membership/reselections/{event_id}/acknowledge -> 204 | 404 | 500
   * @ui /memory | Layout 內的交棒橫幅與「知道了」按鈕
   * @given 以具 K3 view 的帳號落地，橫幅回兩筆未確認事件
   * @step 令其中一筆 acknowledge 回 404、另一筆回 204，按「知道了」 | 兩筆都被清掉，橫幅文案消失
   * @step 重新落地並令其中一筆回 500，按「知道了」 | 回 500 的那一筆仍在，橫幅文案仍在
   * @pass 404 等價於成功（事件消失）；500 不等價（事件保留），兩個方向缺一不可
   * @story US12.4
   */
  test('treats a 404 acknowledge as success and keeps genuinely failed ones pending', async ({
    page,
  }) => {
    // `BR26.3`。端點**不冪等**：404 的語意是「查不到／不屬於你／**已被確認**」，
    // 三者都代表這筆不該再出現，故必須等價於成功。這條規則是先前審查 `R-02`
    // 修掉「橫幅永遠清不掉」那條 Critical 的規則本身，而在本案例之前它的迴歸
    // 保護是零——`team.md` 記載前端唯一的自動化層就是 Playwright e2e。
    const events = [
      { id: 11, project_id: 71, cause: 'auto_reselection', promoted_user_id: SELF_ID, new_role: 'project_admin' },
      { id: 12, project_id: 72, cause: 'auto_reselection', promoted_user_id: SELF_ID, new_role: 'project_admin' },
    ];

    // ① 404 ＋ 204 → 兩筆都該消失。
    await setupApp(page, { k3: K3_FULL, reselections: events });
    await page.route('**/api/membership/reselections/*/acknowledge', async (route) => {
      const id = new URL(route.request().url()).pathname.split('/').at(-2);
      await route.fulfill({ status: id === '11' ? 404 : 204, body: '' });
    });
    await page.goto(NEUTRAL_LANDING);
    const host = page.getByTestId('reselection-banner-host');
    await expect(host).not.toHaveText('');
    await page.getByTestId('reselection-banner-acknowledge').click();
    // 兩筆都被視為已處置 → 宿主回空、按鈕消失。
    await expect(page.getByTestId('reselection-banner-acknowledge')).toHaveCount(0);
    await expect(host).toHaveText('');

    // ② 500 → **不得**被當成成功，該筆必須留著。
    await page.unrouteAll();
    await setupApp(page, { k3: K3_FULL, reselections: events });
    await page.route('**/api/membership/reselections/*/acknowledge', async (route) => {
      const id = new URL(route.request().url()).pathname.split('/').at(-2);
      await route.fulfill({ status: id === '11' ? 500 : 204, body: '' });
    });
    await page.goto(NEUTRAL_LANDING);
    const host2 = page.getByTestId('reselection-banner-host');
    await expect(host2).not.toHaveText('');
    await page.getByTestId('reselection-banner-acknowledge').click();
    // 失敗的那一筆仍未處置 → 宿主仍有文案、按鈕仍在。
    await expect(page.getByTestId('reselection-banner-acknowledge')).toBeVisible();
    await expect(host2).not.toHaveText('');
  });

  /**
   * @purpose 寫入失敗後，主內容與管理控件仍在畫面上——寫入錯誤不得閘住已取得的資料。
   * @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 500 | 變更角色失敗
   * @ui /projects/:projectId/members/:userId | 成員詳情頁：角色下拉、移出鈕、寫入錯誤訊息
   * @given 以具 K3 view+edit 的帳號登入、自身為 project_admin，PATCH 構造為 500
   * @step 開啟詳情頁、改選角色並按儲存 | 出現寫入錯誤訊息
   * @step 檢查主內容 | 成員姓名區塊、角色下拉與移出鈕**仍然存在**，使用者可重試
   * @pass 寫入失敗後四個管理控件與主內容皆未被卸載；抓取錯誤訊息未出現
   * @story US12.2
   */
  test('keeps the member block and its controls mounted after a failed write', async ({ page }) => {
    // 審查 `R-01`（Major）的回歸案例。原本抓取錯誤與寫入錯誤共用同一個 `error`
    // state，而主內容閘在 `!error` 上——於是一次暫時性的儲存失敗會卸載整個成員
    // 區塊（含角色下拉與移出鈕），而唯一能清掉該 state 的 handler 就掛在那些剛
    // 被卸載的控件上，形成只能靠離開頁面脫離的死狀態。
    await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
    });
    await page.goto(memberDetailUrl(OTHER_ID));

    const roleSelect = page.getByTestId('member-detail-role-select');
    await expect(roleSelect).toBeVisible();

    // PATCH 未被本案例個別覆寫，故走 dispatcher 的預設 500。
    await roleSelect.selectOption('project_admin');
    await page.getByTestId('member-detail-save').click();

    // 寫入錯誤要**看得見**（不得靜默）……
    await expect(page.getByTestId('member-detail-action-error')).toBeVisible();
    // ……但**不得**把抓取錯誤的閘門一起觸發。
    await expect(page.getByTestId('member-detail-error')).toHaveCount(0);

    // 主內容與兩個管理控件仍在，使用者可以直接重試。
    await expect(page.getByText(OTHER_NAME)).toBeVisible();
    for (const id of MANAGER_CONTROLS_ON_DETAIL) {
      await expect(page.getByTestId(id)).toBeVisible();
    }
  });

  /**
   * @purpose 成員清單 404（專案不存在，或存在但你不是成員——後端兩者回同一個回應）顯示固定句，不顯示伺服器訊息、不出現專案編號（合併前必修第 14 項）。
   * @api GET /api/membership/projects/{project_id}/members -> 404 | 本體刻意構造成舊形狀「查不到專案 <id>」以抓回歸
   * @ui /projects/:projectId/members | 成員清單頁的抓取錯誤區塊
   * @ui /projects/:projectId/members/:userId | 成員詳情頁的抓取錯誤區塊
   * @given 以具 K3 view+edit 的帳號登入；list_members 回 404，本體 detail 含專案編號
   * @step 開啟成員清單頁 | 抓取錯誤區塊顯示「查不到這個專案」；成員表格不存在
   * @step 開啟同一專案的成員詳情頁 | 抓取錯誤區塊同樣顯示「查不到這個專案」
   * @pass 兩頁的錯誤文字皆恰為「查不到這個專案」，且頁面可見文字不含專案編號與伺服器 detail
   * @story US12.5
   */
  test('shows a fixed not-found sentence without the project id when the member list is 404', async ({
    page,
  }) => {
    // 刻意用一個在頁面其他地方不會出現的專案編號，讓「不含編號」的斷言有意義。
    const hiddenProjectId = 48213;
    const legacyDetail = `查不到專案 ${hiddenProjectId}`;
    await setupApp(page, {
      k3: K3_FULL,
      membersStatus: 404,
      membersErrorBody: { detail: legacyDetail },
    });

    await page.goto(membersUrl(hiddenProjectId));
    const listError = page.getByTestId('member-list-error');
    await expect(listError).toHaveText('查不到這個專案');
    await expect(page.getByTestId('member-list-table')).toHaveCount(0);
    const listText = await page.locator('body').innerText();
    expect(listText).not.toContain(String(hiddenProjectId));
    expect(listText).not.toContain(legacyDetail);

    await page.goto(memberDetailUrl(OTHER_ID, hiddenProjectId));
    const detailError = page.getByTestId('member-detail-error');
    await expect(detailError).toHaveText('查不到這個專案');
    const detailText = await page.locator('body').innerText();
    expect(detailText).not.toContain(String(hiddenProjectId));
    expect(detailText).not.toContain(legacyDetail);
  });

  /**
   * @purpose 成員清單 403（只剩缺全域 K3 view 一種）仍顯示權限句，不被誤當成「查不到」。
   * @api GET /api/membership/projects/{project_id}/members -> 403 | 本體不帶 detail
   * @ui /projects/:projectId/members | 成員清單頁的抓取錯誤區塊
   * @given 以具 K3 view+edit 的帳號登入；list_members 回 403 且本體無 detail
   * @step 開啟成員清單頁 | 抓取錯誤區塊顯示「你沒有檢視這個專案成員的權限」
   * @pass 錯誤文字恰為權限句，且不是「查不到這個專案」
   * @story US12.5
   */
  test('keeps the permission sentence when the member list is 403', async ({ page }) => {
    await setupApp(page, { k3: K3_FULL, membersStatus: 403, membersErrorBody: {} });
    await page.goto(membersUrl());
    const listError = page.getByTestId('member-list-error');
    await expect(listError).toHaveText('你沒有檢視這個專案成員的權限');
    await expect(listError).not.toHaveText('查不到這個專案');
  });

  /**
   * @purpose 寫入途中專案變成查不到（被移出或專案被刪，後端回 404）時，寫入錯誤顯示與清單相同的固定句，不顯示伺服器訊息、不出現專案編號（審查 review-02 R-07）。
   * @api PATCH /api/membership/projects/{project_id}/members/{user_id} -> 404 | 本體刻意構造成舊形狀「查不到專案 <id>」以抓回歸
   * @ui /projects/:projectId/members/:userId | 成員詳情頁：角色下拉、儲存鈕、寫入錯誤訊息
   * @given 以具 K3 view+edit 的帳號登入、自身為 project_admin；PATCH 回 404，本體 detail 含專案編號
   * @step 開啟成員詳情頁、改選角色並按儲存 | 寫入錯誤區塊顯示「查不到這個專案」
   * @pass 寫入錯誤文字恰為「查不到這個專案」，且頁面可見文字不含專案編號與伺服器 detail
   * @story US12.5
   */
  test('shows the fixed not-found sentence without the project id when a role change is 404', async ({
    page,
  }) => {
    const hiddenProjectId = 59317;
    const legacyDetail = `查不到專案 ${hiddenProjectId}`;
    await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
    });
    // 在 dispatcher 之後註冊 → 優先比對；只覆寫 PATCH。
    await page.route('**/api/membership/projects/*/members/*', async (route) => {
      if (route.request().method() !== 'PATCH') return route.fallback();
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: legacyDetail }),
      });
    });

    await page.goto(memberDetailUrl(OTHER_ID, hiddenProjectId));
    const roleSelect = page.getByTestId('member-detail-role-select');
    await expect(roleSelect).toBeVisible();
    await roleSelect.selectOption('project_admin');
    await page.getByTestId('member-detail-save').click();

    const actionError = page.getByTestId('member-detail-action-error');
    await expect(actionError).toHaveText('查不到這個專案');
    const text = await page.locator('body').innerText();
    expect(text).not.toContain(String(hiddenProjectId));
    expect(text).not.toContain(legacyDetail);
  });

  /**
   * @purpose 網址的專案編號不是數字時，成員清單頁顯示與 404 相同的固定句並發出一筆失敗訊號，而不是永遠停在「載入中…」（合併前必修第 23 項 (a)(b)、SEC-U24-6）。
   * @ui /projects/:projectId/members | 成員清單頁的抓取錯誤區塊與載入提示（:projectId 為非數字字串）
   * @given 以具 K3 view+edit 的帳號登入；開啟 /projects/abc/members（abc 不是數字）
   * @step 開啟該網址 | 抓取錯誤區塊顯示「查不到這個專案」；「載入中…」不存在；成員表格不存在
   * @step 檢視 console 與網路請求 | 恰有一筆「[membership] members-fetch-failed GET /projects/:id/members」，且不含網址中的 abc；對 members 端點的請求數為 0
   * @pass 固定句可見、載入提示不存在、失敗訊號恰一筆且不含網址原字串、未發出任何成員清單請求
   * @story US12.1
   */
  test('shows the fixed not-found sentence instead of loading forever when the project id is not a number', async ({
    page,
  }) => {
    const consoleLines = collectConsole(page);
    const rec = await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin')],
    });

    await page.goto('/projects/abc/members');
    await expect(page.getByTestId('members-list-page')).toBeVisible();
    await expect(page.getByTestId('member-list-error')).toHaveText('查不到這個專案');
    await expect(page.getByText('載入中…')).toHaveCount(0);
    await expect(page.getByTestId('member-list-table')).toHaveCount(0);

    // 等到網路靜止再取終值：訊號由 effect 發出，須在渲染之後才落地。
    await page.waitForLoadState('networkidle');
    const signals = consoleLines.filter((l) => l.startsWith('[membership] '));
    expect(signals).toEqual(['[membership] members-fetch-failed GET /projects/:id/members']);
    for (const line of signals) expect(line).not.toContain('abc');
    expect(rec.membersGets()).toBe(0);
  });

  /**
   * @purpose 邀請對話框在鍵盤上真的是 modal：Tab／Shift+Tab 不離開對話框、Escape 關閉、關閉後焦點回到「邀請成員」鈕（合併前必修第 23 項 (c)、AC-A11Y.1）。
   * @api GET /api/membership/projects/{project_id}/members -> 200 | 自身為 project_admin 的兩位成員
   * @ui /projects/:projectId/members | 成員清單頁的「邀請成員」鈕與邀請對話框
   * @given 以具 K3 view+edit 的帳號登入，自身在該專案的 role 為 project_admin
   * @step 按「邀請成員」 | 對話框出現，焦點在使用者 ID 欄位
   * @step 連按 Tab 六次，每次檢查焦點 | 焦點每次都在對話框內
   * @step 在第一個欄位按 Shift+Tab | 焦點仍在對話框內（移到最後一個可聚焦元素「取消」）
   * @step 按 Escape | 對話框消失，焦點在「邀請成員」鈕
   * @step 再開一次並按「取消」 | 對話框消失，焦點在「邀請成員」鈕
   * @pass 六次 Tab 與一次 Shift+Tab 後焦點皆在對話框內；Escape 與取消兩條關閉路徑後焦點都在「邀請成員」鈕
   * @story US12.6
   */
  test('keeps keyboard focus inside the invite dialog, closes it on Escape and returns focus to the invite button', async ({
    page,
  }) => {
    await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
    });
    await page.goto(membersUrl());
    const inviteButton = page.getByTestId('member-list-invite-button');
    await expect(inviteButton).toBeVisible();

    const focusInsideDialog = () =>
      page.evaluate(() => {
        const dialog = document.querySelector('[data-testid="invite-dialog"]');
        return !!dialog && dialog.contains(document.activeElement);
      });

    await inviteButton.click();
    const dialog = page.getByTestId('invite-dialog');
    await expect(dialog).toBeVisible();
    await expect(page.getByTestId('invite-dialog-user-id')).toBeFocused();

    for (let i = 0; i < 6; i += 1) {
      await page.keyboard.press('Tab');
      expect(await focusInsideDialog(), `第 ${i + 1} 次 Tab 後焦點離開了對話框`).toBe(true);
    }

    await page.getByTestId('invite-dialog-user-id').focus();
    await page.keyboard.press('Shift+Tab');
    expect(await focusInsideDialog(), 'Shift+Tab 後焦點離開了對話框').toBe(true);
    await expect(page.getByTestId('invite-dialog-cancel')).toBeFocused();

    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(inviteButton).toBeFocused();

    await inviteButton.click();
    await expect(dialog).toBeVisible();
    await page.getByTestId('invite-dialog-cancel').click();
    await expect(dialog).toHaveCount(0);
    await expect(inviteButton).toBeFocused();
  });

  /**
   * @purpose 移出確認框在鍵盤上真的是 modal：Tab／Shift+Tab 不離開確認框、Escape 關閉且不移出、關閉後焦點回到「移出專案」鈕（合併前必修第 23 項 (c)、AC-A11Y.1）。
   * @api GET /api/membership/projects/{project_id}/members -> 200 | 自身為 project_admin、目標為一般成員
   * @ui /projects/:projectId/members/:userId | 成員詳情頁的「移出專案」鈕與移出確認框
   * @given 以具 K3 view+edit 的帳號登入，自身在該專案的 role 為 project_admin，開啟另一位成員的詳情頁
   * @step 按「移出專案」 | 確認框出現，焦點在「取消」
   * @step 連按 Tab 四次，每次檢查焦點 | 焦點每次都在確認框內
   * @step 在「取消」上按 Shift+Tab | 焦點移到「確認移出」，仍在確認框內
   * @step 按 Escape | 確認框消失，焦點在「移出專案」鈕，且沒有發出任何 DELETE 請求
   * @pass 四次 Tab 與一次 Shift+Tab 後焦點皆在確認框內；Escape 後確認框消失、焦點在「移出專案」鈕、DELETE 請求數為 0
   * @story US12.6
   */
  test('keeps keyboard focus inside the remove confirmation, closes it on Escape and returns focus to the remove button', async ({
    page,
  }) => {
    const rec = await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
    });
    await page.goto(memberDetailUrl(OTHER_ID));
    const removeButton = page.getByTestId('member-detail-remove');
    await expect(removeButton).toBeVisible();

    const focusInsideDialog = () =>
      page.evaluate(() => {
        const dialog = document.querySelector('[data-testid="remove-confirm-dialog"]');
        return !!dialog && dialog.contains(document.activeElement);
      });

    await removeButton.click();
    const dialog = page.getByTestId('remove-confirm-dialog');
    await expect(dialog).toBeVisible();
    await expect(page.getByTestId('remove-confirm-cancel')).toBeFocused();

    for (let i = 0; i < 4; i += 1) {
      await page.keyboard.press('Tab');
      expect(await focusInsideDialog(), `第 ${i + 1} 次 Tab 後焦點離開了確認框`).toBe(true);
    }

    await page.getByTestId('remove-confirm-cancel').focus();
    await page.keyboard.press('Shift+Tab');
    await expect(page.getByTestId('remove-confirm-accept')).toBeFocused();

    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(removeButton).toBeFocused();
    expect(rec.all.filter((r) => r.method === 'DELETE')).toHaveLength(0);
  });

  /**
   * @purpose 網址的專案編號不是數字時，成員詳情頁顯示與 404 相同的固定句並發出一筆失敗訊號，而不是永遠停在「載入中…」（合併前必修第 23 項補修、審查 R-11、SEC-U24-6）。
   * @ui /projects/:projectId/members/:userId | 成員詳情頁的抓取錯誤區塊與載入提示（:projectId 為非數字字串）
   * @given 以具 K3 view+edit 的帳號登入；開啟 /projects/abc/members/1（abc 不是數字）
   * @step 開啟該網址 | 抓取錯誤區塊顯示「查不到這個專案」；「載入中…」不存在；「找不到這位成員」不存在
   * @step 檢視 console 與網路請求 | 恰有一筆「[membership] members-fetch-failed GET /projects/:id/members」，且不含網址中的 abc；對 members 端點的請求數為 0
   * @pass 固定句可見、載入提示不存在、失敗訊號恰一筆且不含網址原字串、未發出任何成員清單請求
   * @story US12.2
   */
  test('shows the fixed not-found sentence instead of loading forever when the detail page project id is not a number', async ({
    page,
  }) => {
    const consoleLines = collectConsole(page);
    const rec = await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin')],
    });

    await page.goto('/projects/abc/members/1');
    await expect(page.getByTestId('member-detail-page')).toBeVisible();
    await expect(page.getByTestId('member-detail-error')).toHaveText('查不到這個專案');
    await expect(page.getByText('載入中…')).toHaveCount(0);
    await expect(page.getByText('找不到這位成員。')).toHaveCount(0);

    // 等到網路靜止再取終值：訊號由 effect 發出，須在渲染之後才落地。
    await page.waitForLoadState('networkidle');
    const signals = consoleLines.filter((l) => l.startsWith('[membership] '));
    expect(signals).toEqual(['[membership] members-fetch-failed GET /projects/:id/members']);
    for (const line of signals) expect(line).not.toContain('abc');
    expect(rec.membersGets()).toBe(0);
  });

  /**
   * @purpose 邀請送出中按 Escape 不會關閉對話框（與停用的「取消」一致）；請求完成後對話框才關閉，並把焦點還給「邀請成員」鈕（合併前必修第 23 項補修、審查 R-15）。
   * @api POST /api/membership/projects/{project_id}/members -> 201 | 以 route 延遲回應，直到測試放行
   * @ui /projects/:projectId/members | 成員清單頁的「邀請成員」鈕與邀請對話框
   * @given 以具 K3 view+edit 的帳號登入，自身在該專案的 role 為 project_admin；邀請請求被延遲
   * @step 開啟邀請對話框、填入使用者 ID 並按「送出邀請」 | 送出鈕顯示「送出中…」
   * @step 送出中按 Escape | 對話框仍在
   * @step 放行邀請請求（回 201） | 對話框消失，新成員出現在清單上，焦點在「邀請成員」鈕
   * @pass 送出中 Escape 後對話框數為 1；請求完成後對話框數為 0 且「邀請成員」鈕取得焦點
   * @story US12.6
   */
  test('ignores Escape while an invite is in flight and returns focus to the invite button once it completes', async ({
    page,
  }) => {
    await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
    });
    let release: () => void = () => {};
    const released = new Promise<void>((resolve) => {
      release = resolve;
    });
    let postSeen = false;
    // 在 dispatcher 之後註冊 → 優先比對；只延遲 POST。
    await page.route('**/api/membership/projects/*/members', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      postSeen = true;
      await released;
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(member(3333, INVITEE_NAME, 'member')),
      });
    });

    await page.goto(membersUrl());
    const inviteButton = page.getByTestId('member-list-invite-button');
    await expect(inviteButton).toBeVisible();
    await inviteButton.click();
    const dialog = page.getByTestId('invite-dialog');
    await expect(dialog).toBeVisible();
    await page.getByTestId('invite-dialog-user-id').fill('3333');
    await page.getByTestId('invite-dialog-submit').click();

    // 確認請求已送出且仍懸著，才按 Escape——否則測到的是「尚未送出」的 Escape。
    await expect(page.getByTestId('invite-dialog-submit')).toHaveText('送出中…');
    await expect.poll(() => postSeen).toBe(true);
    await page.keyboard.press('Escape');
    // 給 Escape 的處理一次渲染機會再斷言，避免在關閉發生前就取樣而誤判綠燈。
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r(null))));
    await expect(dialog).toHaveCount(1);

    release();
    await expect(dialog).toHaveCount(0);
    await expect(page.getByTestId('member-list-table')).toContainText(INVITEE_NAME);
    await expect(inviteButton).toBeFocused();
  });

  /**
   * @purpose 移出被最後管理者守門擋下（409）時，確認框關閉後焦點回到「移出專案」鈕，鍵盤使用者不必從頁首重新 Tab（合併前必修第 23 項補修、審查 R-15）。
   * @api DELETE /api/membership/projects/{project_id}/members/{user_id} -> 409 | 本體為 LastAdminGuardReport（一個專案）
   * @ui /projects/:projectId/members/:userId | 成員詳情頁的「移出專案」鈕、移出確認框與守門回報
   * @given 以具 K3 view+edit 的帳號登入，自身在該專案的 role 為 project_admin，開啟另一位成員的詳情頁；DELETE 回 409
   * @step 按「移出專案」再按「確認移出」 | 確認框消失，守門回報列出一個專案
   * @step 檢查焦點 | 焦點在「移出專案」鈕
   * @pass 409 之後確認框數為 0、守門回報可見、「移出專案」鈕取得焦點
   * @story US12.6
   */
  test('returns focus to the remove button after the remove confirmation is closed by a last-admin 409', async ({
    page,
  }) => {
    await setupApp(page, {
      k3: K3_FULL,
      members: [member(SELF_ID, SELF_NAME, 'project_admin'), member(OTHER_ID, OTHER_NAME, 'member')],
    });
    await page.route('**/api/membership/projects/*/members/*', async (route) => {
      if (route.request().method() !== 'DELETE') return route.fallback();
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ projects: [{ project_id: PROJECT_ID, name: 'e2e-project' }] }),
      });
    });

    await page.goto(memberDetailUrl(OTHER_ID));
    const removeButton = page.getByTestId('member-detail-remove');
    await expect(removeButton).toBeVisible();
    await removeButton.click();
    const dialog = page.getByTestId('remove-confirm-dialog');
    await expect(dialog).toBeVisible();
    await page.getByTestId('remove-confirm-accept').click();

    await expect(dialog).toHaveCount(0);
    await expect(page.getByTestId('guard-report')).toBeVisible();
    await expect(removeButton).toBeFocused();
  });
});
