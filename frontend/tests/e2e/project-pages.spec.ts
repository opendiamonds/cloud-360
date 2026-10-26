import { test, expect, type Browser, type Page } from '@playwright/test';

/**
 * U23 project-pages-ui — 專案清單／建立／詳情（總覽、需求、記憶摘要三籤）。
 *
 * **全部走 `page.route()` 攔截，不打真實後端**（形狀沿用 `member-pages.spec.ts` 的
 * `setupApp`）：本檔測的是前端對 7 個既有端點的消費與畫面行為；伺服器的授權與可見性由
 * `backend/tests/test_project_visibility_*.py`／`test_project_write_guard.py` 的
 * `TestClient` 承擔，前後端形狀一致由 `openapi.json` 漂移閘門與 `check:types` 承擔。
 * 因此本檔**不需要資料庫、後端、`claude` CLI 或 n8n webhook**，只需要前端被服務於
 * `BASE_URL`。
 *
 * **名稱穩定性（合併後不可改）**：TCMS 案例名稱為 `<describe> › <test>`；`describe`
 * （`U23 project pages`）與每個 `test` 字串一旦合併就不得再改，改名即成孤兒案例。
 *
 * 21 個案例逐一對應 `code-generation/unit-test-instructions.md` §三之二。
 */

// ---------------------------------------------------------------------------
// 測試資料。專案名、系統名、欄位值一律為**獨特的假字串**——案例 21 斷言 console
// 不含它們（`PPN-18`）。
// ---------------------------------------------------------------------------

const SELF_ID = 5001;
const OTHER_ID = 5002;
const SELF_NAME = 'e2e-u23-self';

type Perm = { view: boolean; edit: boolean; review: boolean };
const FULL: Perm = { view: true, edit: true, review: false };
const VIEW_ONLY: Perm = { view: true, edit: false, review: false };
const NONE: Perm = { view: false, edit: false, review: false };

interface ProjectStub {
  id: number;
  name: string;
  owner_user_id: number;
  is_default: boolean;
  created_at: string | null;
}

interface SystemStub {
  id: number;
  project_id: number;
  name: string;
  is_default: boolean;
  created_at: string | null;
}

type FilledState = 'never_filled' | 'filled' | 'cleared';

interface FieldStub {
  group_key: string;
  field_key: string;
  label: string;
  value: string | null;
  filled_state: FilledState;
  updated_at: string | null;
  updated_by: number | null;
  updated_on_behalf_of: string | null;
  cleared_at: string | null;
}

interface ChangeStub {
  id: number;
  diagram_id: number;
  source: string;
  actor_user_id: number;
  requirement_summary: string;
  requirement_label: string;
  created_at: string | null;
}

/** 兩組、五欄。組標題與欄位標籤刻意是**本檔獨有**的字串，用來證明畫面取自回應（`BR84.3`）。 */
const GROUPS: { key: string; title: string; fields: { key: string; label: string }[] }[] = [
  {
    key: 'cost',
    title: 'e2e 成本組',
    fields: [
      { key: 'sla', label: 'e2e-SLA 標籤' },
      { key: 'tps', label: 'e2e-尖峰 TPS 標籤' },
      { key: 'users', label: 'e2e-使用客群 標籤' },
    ],
  },
  {
    key: 'arch',
    title: 'e2e 架構組',
    fields: [
      { key: 'avail', label: 'e2e-可用性 標籤' },
      { key: 'retention', label: 'e2e-保存年限 標籤' },
    ],
  },
];
const INPUT_HINT = 'e2e-input-hint：請填寫架構假設';

const project = (id: number, name: string, owner = SELF_ID): ProjectStub => ({
  id,
  name,
  owner_user_id: owner,
  is_default: false,
  created_at: '2026-09-01T00:00:00Z',
});

const system = (id: number, projectId: number, name: string): SystemStub => ({
  id,
  project_id: projectId,
  name,
  is_default: false,
  created_at: '2026-09-02T00:00:00Z',
});

/** 建立一個系統的欄位表；`filled` 中的欄位視為已由「你」填過。 */
function freshFields(filled: Record<string, string> = {}): Map<string, FieldStub> {
  const map = new Map<string, FieldStub>();
  for (const g of GROUPS) {
    for (const f of g.fields) {
      const id = `${g.key}.${f.key}`;
      const value = filled[id];
      map.set(id, {
        group_key: g.key,
        field_key: f.key,
        label: f.label,
        value: value ?? null,
        filled_state: value !== undefined ? 'filled' : 'never_filled',
        updated_at: value !== undefined ? '2026-09-27T00:00:00Z' : null,
        updated_by: value !== undefined ? SELF_ID : null,
        updated_on_behalf_of: null,
        cleared_at: null,
      });
    }
  }
  return map;
}

/** 伺服器端的欄位表 → `FieldSetView` 回應本體（組數與 x/y 由此推導，與後端同一判準）。 */
function fieldSetBody(systemId: number, fields: Map<string, FieldStub>) {
  let unfilled = 0;
  const groups = GROUPS.map((g) => {
    const rows = g.fields.map((f) => fields.get(`${g.key}.${f.key}`) as FieldStub);
    const filledCount = rows.filter((r) => r.filled_state === 'filled').length;
    unfilled += rows.length - filledCount;
    return {
      group_key: g.key,
      title: g.title,
      filled_count: filledCount,
      total_count: rows.length,
      fields: rows,
    };
  });
  return { system_id: systemId, unfilled_count: unfilled, input_hint: INPUT_HINT, groups };
}

// ---------------------------------------------------------------------------
// 攔截層：一份可變的伺服器狀態，handler 在**請求當下**讀它，故案例可在中途改變行為。
// ---------------------------------------------------------------------------

interface ApiState {
  perms: { K2: Perm; K3: Perm; K4: Perm };
  projects: ProjectStub[];
  projectsStatus: number;
  systems: Map<number, SystemStub[]>;
  systemsStatus: Map<number, number>;
  systemsDelayMs: (projectId: number) => number;
  createProject: (name: string) => { status: number; body: unknown };
  createSystemStatus: number;
  createSystemDelayMs: number;
  nextSystemId: number;
  fields: Map<number, Map<string, FieldStub>>;
  fieldsStatus: Map<number, number>;
  fieldsDelayMs: (systemId: number) => number;
  putStatus: (fieldId: string) => number;
  changes: Map<number, ChangeStub[]>;
  changesStatus: Map<number, number>;
  changesDelayMs: (systemId: number) => number;
}

function defaultState(): ApiState {
  return {
    perms: { K2: FULL, K3: FULL, K4: FULL },
    projects: [],
    projectsStatus: 200,
    systems: new Map(),
    systemsStatus: new Map(),
    systemsDelayMs: () => 0,
    createProject: () => ({ status: 500, body: { detail: 'not stubbed' } }),
    createSystemStatus: 201,
    createSystemDelayMs: 0,
    nextSystemId: 900,
    fields: new Map(),
    fieldsStatus: new Map(),
    fieldsDelayMs: () => 0,
    putStatus: () => 200,
    changes: new Map(),
    changesStatus: new Map(),
    changesDelayMs: () => 0,
  };
}

const RE_SYSTEMS = /\/api\/hierarchy\/projects\/(\d+)\/systems$/;
const RE_FIELDS = /\/api\/requirements\/systems\/(\d+)\/fields$/;
const RE_FIELD = /\/api\/requirements\/systems\/(\d+)\/fields\/([^/]+)\/([^/]+)$/;
const RE_CHANGES = /\/api\/hierarchy\/diagram-changes$/;

interface Recorded {
  method: string;
  path: string;
  search: string;
  body: string | null;
}

interface Recorder {
  all: Recorded[];
  count: (method: string, re: RegExp) => number;
  /** 依 `re` 比對的請求的在途最大值（以 request ／ requestfinished／requestfailed 維護）。 */
  maxInFlight: (key: string) => number;
  console: string[];
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function fulfillJson(
  route: import('@playwright/test').Route,
  status: number,
  body: unknown,
  ms = 0
) {
  if (ms > 0) await delay(ms);
  try {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: status === 204 ? '' : JSON.stringify(body),
    });
  } catch {
    // 頁面已離開（卸載案例）：該回應無人接收，忽略。
  }
}

/** 在途計數的分類：清單頁扇出（端點 2）與詳情頁扇出（端點 5 ∪ 端點 7）。 */
const FANOUT_GROUPS: Record<string, (path: string) => boolean> = {
  systems: (p) => RE_SYSTEMS.test(p),
  detail: (p) => RE_FIELDS.test(p) || RE_CHANGES.test(p),
};

async function setupApp(page: Page, state: ApiState): Promise<Recorder> {
  const inFlight: Record<string, number> = { systems: 0, detail: 0 };
  const maxSeen: Record<string, number> = { systems: 0, detail: 0 };
  const recorder: Recorder = {
    all: [],
    count: (method, re) =>
      recorder.all.filter((r) => r.method === method && re.test(r.path)).length,
    maxInFlight: (key) => maxSeen[key],
    console: [],
  };

  page.on('console', (msg) => recorder.console.push(msg.text()));
  page.on('request', (req) => {
    const url = new URL(req.url());
    if (!url.pathname.startsWith('/api/')) return;
    recorder.all.push({
      method: req.method(),
      path: url.pathname,
      search: url.search,
      body: req.postData(),
    });
    if (req.method() !== 'GET') return;
    for (const [key, match] of Object.entries(FANOUT_GROUPS)) {
      if (match(url.pathname)) {
        inFlight[key] += 1;
        maxSeen[key] = Math.max(maxSeen[key], inFlight[key]);
      }
    }
  });
  const settle = (req: import('@playwright/test').Request) => {
    const url = new URL(req.url());
    if (req.method() !== 'GET') return;
    for (const [key, match] of Object.entries(FANOUT_GROUPS)) {
      if (match(url.pathname)) inFlight[key] -= 1;
    }
  };
  page.on('requestfinished', settle);
  page.on('requestfailed', settle);

  await page.addInitScript(() => {
    sessionStorage.setItem('token', 'e2e-token');
    // 記錄 SPA 導航（pushState／replaceState）的路徑序列，供「pathname 變更次數」斷言。
    const w = window as unknown as { __u23Paths: string[] };
    w.__u23Paths = [location.pathname];
    for (const name of ['pushState', 'replaceState'] as const) {
      const original = history[name].bind(history);
      history[name] = (...args: Parameters<History['pushState']>) => {
        original(...args);
        w.__u23Paths.push(location.pathname);
      };
    }
  });

  await page.route('**/api/auth/me', (route) =>
    fulfillJson(route, 200, {
      id: SELF_ID,
      username: SELF_NAME,
      role: 'Project_Editor',
      is_active: true,
      authorization_status: 'approved',
      permissions: { K2: state.perms.K2, K3: state.perms.K3, K4: state.perms.K4 },
      pending_request: null,
    })
  );
  // Layout 的改選橫幅（K3 view 時）與中性落地頁：一律空清單。
  await page.route('**/api/membership/**', (route) => fulfillJson(route, 200, []));
  await page.route('**/api/memory/**', (route) => fulfillJson(route, 200, []));

  await page.route('**/api/hierarchy/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    const method = req.method();
    if (method === 'GET' && path.endsWith('/api/hierarchy/projects')) {
      return fulfillJson(route, state.projectsStatus, state.projectsStatus === 200 ? state.projects : { detail: '讀取失敗' });
    }
    if (method === 'POST' && path.endsWith('/api/hierarchy/projects')) {
      const name = (JSON.parse(req.postData() ?? '{}') as { name?: string }).name ?? '';
      const result = state.createProject(name);
      return fulfillJson(route, result.status, result.body);
    }
    const sys = RE_SYSTEMS.exec(path);
    if (sys && method === 'GET') {
      const pid = Number(sys[1]);
      const status = state.systemsStatus.get(pid) ?? 200;
      return fulfillJson(
        route,
        status,
        status === 200 ? (state.systems.get(pid) ?? []) : { detail: '查不到專案' },
        state.systemsDelayMs(pid)
      );
    }
    if (sys && method === 'POST') {
      const pid = Number(sys[1]);
      const name = (JSON.parse(req.postData() ?? '{}') as { name?: string }).name ?? '';
      await delay(state.createSystemDelayMs);
      if (state.createSystemStatus !== 201) {
        return fulfillJson(route, state.createSystemStatus, { detail: 'nope' });
      }
      const created = system(state.nextSystemId++, pid, name);
      state.systems.set(pid, [...(state.systems.get(pid) ?? []), created]);
      state.fields.set(created.id, freshFields());
      return fulfillJson(route, 201, created);
    }
    if (RE_CHANGES.test(path) && method === 'GET') {
      const sid = Number(url.searchParams.get('system_id'));
      const status = state.changesStatus.get(sid) ?? 200;
      return fulfillJson(
        route,
        status,
        status === 200 ? (state.changes.get(sid) ?? []) : { detail: '讀取失敗' },
        state.changesDelayMs(sid)
      );
    }
    return fulfillJson(route, 500, { detail: 'not stubbed' });
  });

  await page.route('**/api/requirements/**', async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const method = req.method();
    const set = RE_FIELDS.exec(path);
    if (set && method === 'GET') {
      const sid = Number(set[1]);
      const status = state.fieldsStatus.get(sid) ?? 200;
      const fields = state.fields.get(sid) ?? freshFields();
      return fulfillJson(
        route,
        status,
        status === 200 ? fieldSetBody(sid, fields) : { detail: '讀取失敗' },
        state.fieldsDelayMs(sid)
      );
    }
    const one = RE_FIELD.exec(path);
    if (one && method === 'PUT') {
      const sid = Number(one[1]);
      const id = `${one[2]}.${one[3]}`;
      const status = state.putStatus(id);
      if (status !== 200) {
        return fulfillJson(route, status, { detail: '值超過允許的長度' });
      }
      const body = JSON.parse(req.postData() ?? '{}') as { value: string };
      const fields = state.fields.get(sid) ?? freshFields();
      const prev = fields.get(id) as FieldStub;
      const cleared = body.value.trim() === '';
      const next: FieldStub = {
        ...prev,
        value: cleared ? null : body.value,
        filled_state: cleared ? 'cleared' : 'filled',
        updated_at: '2026-10-16T00:00:00Z',
        updated_by: SELF_ID,
        updated_on_behalf_of: null,
        cleared_at: cleared ? '2026-10-16T00:00:00Z' : null,
      };
      fields.set(id, next);
      state.fields.set(sid, fields);
      return fulfillJson(route, 200, next);
    }
    return fulfillJson(route, 500, { detail: 'not stubbed' });
  });

  return recorder;
}

/** 單一專案（id 10）、可選系統的詳情頁世界。 */
function detailWorld(systemCount: number, owner = SELF_ID): ApiState {
  const state = defaultState();
  state.projects = [project(10, 'e2e-project-detail', owner)];
  const systems = Array.from({ length: systemCount }, (_, i) =>
    system(100 + i, 10, `e2e-system-${i + 1}`)
  );
  state.systems.set(10, systems);
  for (const s of systems) state.fields.set(s.id, freshFields());
  return state;
}

const detailUrl = (tab = 'overview', id = 10) => `/projects/${id}?tab=${tab}`;
const navPaths = (page: Page) =>
  page.evaluate(() => (window as unknown as { __u23Paths: string[] }).__u23Paths);
const pathnameChanges = (paths: string[]) =>
  paths.filter((p, i) => i > 0 && p !== paths[i - 1]).length;

// ---------------------------------------------------------------------------

test.describe('U23 project pages', () => {
  /**
   * @purpose Sidebar「專案」入口與 /projects 路由以 K2 view 把關，兩者同一判定。
   * @api GET /api/hierarchy/projects -> 200 | 可見的專案清單
   * @ui /projects | 專案清單頁；Sidebar 的「專案」項
   * @given 兩個瀏覽器環境，唯一差異是 K2 的 view 旗標
   * @step 以具 K2 view 的帳號開啟 /projects | Sidebar 有「專案」，清單頁的 h1 為「專案」
   * @step 以 K2 三旗標皆 false 的帳號開啟 /memory | Sidebar 沒有「專案」
   * @step 同一帳號直接開啟 /projects | 被導向 /403
   * @pass 有權者看得到入口與頁面；無權者既看不到入口、也進不了頁面
   * @story US11.1
   */
  test('gates the sidebar entry and the list route on K2 view', async ({ browser }: { browser: Browser }) => {
    const allowCtx = await browser.newContext();
    const allow = await allowCtx.newPage();
    const allowed = defaultState();
    await setupApp(allow, allowed);
    await allow.goto('/projects');
    await expect(allow.getByTestId('sidebar-projects-link')).toBeVisible();
    await expect(allow.getByRole('heading', { level: 1, name: '專案' })).toBeVisible();
    await allowCtx.close();

    const denyCtx = await browser.newContext();
    const deny = await denyCtx.newPage();
    const denied = defaultState();
    denied.perms.K2 = NONE;
    await setupApp(deny, denied);
    await deny.goto('/memory');
    await expect(deny.getByText(SELF_NAME)).toBeVisible();
    await expect(deny.getByTestId('sidebar-projects-link')).toHaveCount(0);
    await deny.goto('/projects');
    await expect(deny).toHaveURL(/\/403$/);
    await denyCtx.close();
  });

  /**
   * @purpose 清單的 empty 與 error 是兩種不同的呈現；列的「尚無系統」與「系統清單讀取失敗」不被讀成同一件事。
   * @api GET /api/hierarchy/projects -> 200 | 可見的專案清單（空或非空）
   * @api GET /api/hierarchy/projects/{project_id}/systems -> 200 | 各列的系統
   * @ui /projects | 清單頁四態與列的子狀態
   * @given 具 K2 view+edit 的帳號
   * @step 專案清單回空陣列並開啟 /projects | 出現 empty 說明與「建立第一個專案」，沒有 error
   * @step 專案清單回 500 並重新開啟 | 出現「讀不到專案清單」「這不是「你沒有專案」」與 [重試]，沒有 empty
   * @step 改為回兩個專案（一個 0 個系統、一個系統清單 500）後按 [重試] | 第一列為「尚無系統」，第二列為「系統清單讀取失敗」且不顯示「0 個系統」
   * @pass 三種畫面的文字互不相同，失敗不被呈現成 0 或空
   * @story US11.1
   */
  test('distinguishes the empty list, the failed list and the per-row failure', async ({ page }) => {
    const state = defaultState();
    await setupApp(page, state);
    await page.goto('/projects');
    await expect(page.getByTestId('project-list-empty')).toContainText('還沒有任何專案');
    await expect(page.getByTestId('project-list-empty-create')).toBeVisible();
    await expect(page.getByTestId('project-list-error')).toHaveCount(0);

    state.projectsStatus = 500;
    await page.goto('/projects');
    const error = page.getByTestId('project-list-error');
    await expect(error).toContainText('讀不到專案清單');
    await expect(error).toContainText('這不是「你沒有專案」');
    await expect(page.getByTestId('project-list-empty')).toHaveCount(0);

    state.projectsStatus = 200;
    state.projects = [project(1, 'e2e-project-empty'), project(2, 'e2e-project-broken')];
    state.systems.set(1, []);
    state.systemsStatus.set(2, 500);
    await page.getByTestId('project-list-retry').click();
    await expect(page.getByTestId('project-list-row-systems-1')).toHaveText('尚無系統');
    await expect(page.getByTestId('project-list-row-systems-2')).toHaveText('系統清單讀取失敗');
    await expect(page.getByTestId('project-list-row-2')).not.toContainText('0 個系統');
    await expect(page.getByTestId('project-list-row-count-1')).toHaveText('0 個系統');
  });

  /**
   * @purpose 建立專案：空白名稱送出前擋下；三類失敗文案不同且名稱保留；成功導向該專案總覽，pathname 只變一次。
   * @api POST /api/hierarchy/projects -> 201 | 建立專案（同交易寫入建立者成員列）
   * @ui /projects/new | 建立表單
   * @ui /projects/:projectId | 建立成功後的詳情頁總覽籤
   * @given 具 K2 edit 的帳號；建立端點依序回 409、403、500、201
   * @step 名稱只有空白並送出 | 顯示「請輸入名稱」，沒有任何 POST
   * @step 輸入名稱並送出三次 | 依序顯示名稱重複、無權限、其他三種不同文案，名稱欄保留原值
   * @step 第四次送出 | 導向 /projects/<回應 id>?tab=overview
   * @pass 共 4 次 POST、pathname 變更恰 1 次、文案三者互不相同
   * @story US11.1
   */
  test('validates, classifies failures and navigates once after creating a project', async ({ page }) => {
    const state = defaultState();
    const responses = [
      { status: 409, body: { detail: 'dup' } },
      { status: 403, body: { detail: 'no' } },
      { status: 500, body: { detail: 'boom' } },
    ];
    state.createProject = (name) => {
      const next = responses.shift();
      if (next) return next;
      const created = project(77, name);
      state.projects = [created];
      state.systems.set(77, []);
      return { status: 201, body: created };
    };
    const rec = await setupApp(page, state);
    await page.goto('/projects/new');

    await page.getByTestId('project-create-name').fill('   ');
    await page.getByTestId('project-create-submit').click();
    await expect(page.getByTestId('project-create-error')).toHaveText('請輸入名稱');
    expect(rec.count('POST', /\/api\/hierarchy\/projects$/)).toBe(0);

    const name = 'e2e-project-new';
    await page.getByTestId('project-create-name').fill(name);
    const texts: string[] = [];
    for (let i = 0; i < 3; i += 1) {
      await page.getByTestId('project-create-submit').click();
      await expect.poll(() => rec.count('POST', /\/api\/hierarchy\/projects$/)).toBe(i + 1);
      await expect(page.getByTestId('project-create-submit')).toHaveText('建立');
      texts.push((await page.getByTestId('project-create-error').textContent()) ?? '');
      await expect(page.getByTestId('project-create-name')).toHaveValue(name);
    }
    expect(texts[0]).toContain('同名');
    expect(texts[1]).toContain('權限');
    expect(texts[2]).toContain('建立專案失敗');
    expect(new Set(texts).size).toBe(3);

    await page.getByTestId('project-create-submit').click();
    await expect(page).toHaveURL(/\/projects\/77\?tab=overview$/);
    expect(rec.count('POST', /\/api\/hierarchy\/projects$/)).toBe(4);
    expect(pathnameChanges(await navPaths(page))).toBe(1);
  });

  /**
   * @purpose 建立系統只對擁有者且具 K2 edit 者出現；成功後系統數由重讀清單得出（0→1）且不換頁；pending 期間連點只發一次。
   * @api POST /api/hierarchy/projects/{project_id}/systems -> 201 | 建立系統
   * @api GET /api/hierarchy/projects/{project_id}/systems -> 200 | 建立後重讀系統清單
   * @ui /projects/:projectId | 總覽籤「系統 N」與建立系統動作
   * @given 擁有者的專案（0 個系統）與他人擁有的專案各一；建立端點延遲 600 ms
   * @step 開啟他人擁有的專案總覽 | 沒有「建立系統」
   * @step 開啟自己擁有的專案總覽 | 「系統 0」旁有「建立系統」
   * @step 輸入名稱後連點送出兩次 | 只發出一次 POST
   * @step 等待完成 | 「系統 1」，pathname 不變
   * @pass 擁有者條件成立才渲染；計數 0→1；POST 恰 1 次；pathname 變更 0 次
   * @story US11.1
   */
  test('shows the create-system action only to the owner and recounts systems after creating one', async ({
    page,
  }) => {
    const state = detailWorld(0);
    state.projects.push(project(11, 'e2e-project-not-mine', OTHER_ID));
    state.systems.set(11, []);
    state.createSystemDelayMs = 600;
    const rec = await setupApp(page, state);

    await page.goto(detailUrl('overview', 11));
    await expect(page.getByTestId('project-count-systems')).toHaveText('系統 0');
    await expect(page.getByTestId('system-create-action')).toHaveCount(0);

    await page.goto(detailUrl());
    await expect(page.getByTestId('project-count-systems')).toHaveText('系統 0');
    await page.getByTestId('system-create-action').click();
    await page.getByTestId('system-create-name').fill('e2e-system-created');
    const before = await navPaths(page);
    await page.getByTestId('system-create-submit').click();
    await page.getByTestId('system-create-submit').click({ force: true });
    await expect(page.getByTestId('project-count-systems')).toHaveText('系統 1');
    expect(rec.count('POST', /\/systems$/)).toBe(1);
    expect(pathnameChanges(await navPaths(page))).toBe(pathnameChanges(before));
    await expect(page).toHaveURL(/\/projects\/10\?tab=overview$/);
  });

  /**
   * @purpose 沒有系統的專案，需求籤是說明＋建立動作的空狀態，不是沒有選項的選擇器。
   * @api GET /api/hierarchy/projects/{project_id}/systems -> 200 | 空陣列
   * @ui /projects/:projectId | 需求籤空狀態
   * @given 擁有者且具 K4 的帳號；專案 0 個系統
   * @step 開啟 ?tab=requirements | 出現需求籤空狀態與建立系統動作
   * @pass requirements-empty 存在、requirements-system-select 不在 DOM
   * @story US11.1
   */
  test('renders the requirements empty state instead of an empty selector', async ({ page }) => {
    await setupApp(page, detailWorld(0));
    await page.goto(detailUrl('requirements'));
    await expect(page.getByTestId('requirements-empty')).toBeVisible();
    await expect(page.getByTestId('requirements-empty').getByTestId('system-create-action')).toBeVisible();
    await expect(page.getByTestId('requirements-system-select')).toHaveCount(0);
  });

  /**
   * @purpose 需求籤的組標題、欄位標籤、x/y 與提示文字全部取自回應；未填欄位有文字「未填」且為該欄位的可及描述。
   * @api GET /api/requirements/systems/{system_id}/fields -> 200 | 該系統的欄位與未填計數
   * @ui /projects/:projectId | 需求籤的欄位組
   * @given 單一系統，其中一欄已填
   * @step 開啟需求籤 | 兩組 legend 為回應的 title、x/y 為 1/3 與 0/2、提示文字為回應的 input_hint
   * @step 檢查一個未填欄位 | 旁有「未填」文字，輸入框的 aria-describedby 含該文字的 id
   * @step 檢查已填欄位 | 沒有「未填」
   * @pass 畫面上的組與標籤逐字等於回應；未填資訊以文字並經可及描述提供
   * @story US11.2
   */
  test('renders groups, labels and the unfilled text from the response', async ({ page }) => {
    const state = detailWorld(1);
    state.fields.set(100, freshFields({ 'cost.sla': 'e2e-value-sla' }));
    await setupApp(page, state);
    await page.goto(detailUrl('requirements'));

    await expect(page.getByTestId('requirements-group-cost').locator('legend')).toContainText('e2e 成本組');
    await expect(page.getByTestId('requirements-group-cost').locator('legend')).toContainText('1/3 已填');
    await expect(page.getByTestId('requirements-group-arch').locator('legend')).toContainText('0/2 已填');
    await expect(page.getByText('e2e-尖峰 TPS 標籤')).toBeVisible();
    await expect(page.getByTestId('requirements-input-hint')).toHaveText(INPUT_HINT);

    const unfilled = page.getByTestId('requirements-unfilled-cost-tps');
    await expect(unfilled).toHaveText('未填');
    const unfilledId = await unfilled.getAttribute('id');
    const describedBy = await page.getByTestId('requirements-field-cost-tps').getAttribute('aria-describedby');
    expect(describedBy?.split(' ')).toContain(unfilledId);
    await expect(page.getByTestId('requirements-unfilled-cost-sla')).toHaveCount(0);
    await expect(page.getByTestId('requirements-field-cost-sla')).toHaveValue('e2e-value-sla');
  });

  /**
   * @purpose 更新者顯示三種值；代寫者的標題取「請求組」而非欄位所屬組，比對不到時降級為「由大腦」。
   * @api GET /api/requirements/systems/{system_id}/fields -> 200 | 含 updated_by／updated_on_behalf_of
   * @ui /projects/:projectId | 需求籤的更新者標示
   * @given 五欄：從未更新、他組代寫、未知組代寫、自己填、他人填
   * @step 開啟需求籤並逐欄讀更新者 | 依序為「從未更新」「由大腦（e2e 架構組 請求）」「由大腦」「由你」「由其他成員」
   * @pass 代寫標題來自 updated_on_behalf_of 對應的組，而非 legend；比對不到時不顯示括號與原始 key
   * @story US11.2
   */
  test('shows the updater from the requesting group and degrades for unknown groups', async ({ page }) => {
    const state = detailWorld(1);
    const fields = freshFields({
      'cost.tps': 'e2e-value-tps',
      'cost.users': 'e2e-value-users',
      'arch.avail': 'e2e-value-avail',
      'arch.retention': 'e2e-value-retention',
    });
    fields.set('cost.tps', { ...(fields.get('cost.tps') as FieldStub), updated_on_behalf_of: 'arch' });
    fields.set('cost.users', { ...(fields.get('cost.users') as FieldStub), updated_on_behalf_of: 'e2e-ghost-group' });
    fields.set('arch.retention', { ...(fields.get('arch.retention') as FieldStub), updated_by: OTHER_ID });
    state.fields.set(100, fields);
    await setupApp(page, state);
    await page.goto(detailUrl('requirements'));

    await expect(page.getByTestId('requirements-updater-cost-sla')).toHaveText('從未更新');
    await expect(page.getByTestId('requirements-updater-cost-tps')).toContainText('由大腦（e2e 架構組 請求）');
    const unknown = page.getByTestId('requirements-updater-cost-users');
    await expect(unknown).toContainText('由大腦');
    await expect(unknown).not.toContainText('（');
    await expect(unknown).not.toContainText('e2e-ghost-group');
    await expect(page.getByTestId('requirements-updater-arch-avail')).toContainText('由你');
    await expect(page.getByTestId('requirements-updater-arch-retention')).toContainText('由其他成員');
  });

  /**
   * @purpose 有 K4 edit 者可編輯並看得到儲存；只有 K4 view 者為唯讀、沒有儲存、看得到說明，未填與更新者照常。
   * @api GET /api/requirements/systems/{system_id}/fields -> 200 | 欄位
   * @ui /projects/:projectId | 需求籤的可編輯與唯讀兩態
   * @given 兩個瀏覽器環境，唯一差異是 K4 的 edit 旗標
   * @step 以 K4 view+edit 開啟需求籤 | 欄位可編輯、有 requirements-save、沒有唯讀說明
   * @step 以 K4 view only 開啟需求籤 | 欄位 readOnly、沒有 requirements-save、有唯讀說明；「未填」與更新者存在
   * @pass allow 與 deny 兩側各自成立
   * @story US11.2
   */
  test('allows editing with K4 edit and renders read-only without it', async ({ browser }: { browser: Browser }) => {
    const allowCtx = await browser.newContext();
    const allow = await allowCtx.newPage();
    await setupApp(allow, detailWorld(1));
    await allow.goto(detailUrl('requirements'));
    await expect(allow.getByTestId('requirements-field-cost-sla')).toBeEditable();
    await expect(allow.getByTestId('requirements-save')).toBeVisible();
    await expect(allow.getByTestId('requirements-readonly-notice')).toHaveCount(0);
    await allowCtx.close();

    const denyCtx = await browser.newContext();
    const deny = await denyCtx.newPage();
    const state = detailWorld(1);
    state.perms.K4 = VIEW_ONLY;
    await setupApp(deny, state);
    await deny.goto(detailUrl('requirements'));
    await expect(deny.getByTestId('requirements-readonly-notice')).toHaveText(
      '你可以檢視需求欄位，但沒有編輯權限'
    );
    await expect(deny.getByTestId('requirements-field-cost-sla')).not.toBeEditable();
    await expect(deny.getByTestId('requirements-save')).toHaveCount(0);
    await expect(deny.getByTestId('requirements-unfilled-cost-sla')).toHaveText('未填');
    await expect(deny.getByTestId('requirements-updater-cost-sla')).toHaveText('從未更新');
    await denyCtx.close();
  });

  /**
   * @purpose 兩欄儲存其一失敗：失敗欄保留輸入並標「未儲存」與原因；成功欄呈現重讀值。
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 200 | 寫入成功的那一欄
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 422 | 寫入失敗的那一欄
   * @api GET /api/requirements/systems/{system_id}/fields -> 200 | 儲存後重讀
   * @ui /projects/:projectId | 需求籤的部分失敗
   * @given 單一系統；cost.tps 的 PUT 回 422
   * @step 改 cost.sla 與 cost.tps 後按 [儲存] | 發出兩次 PUT，其後一次 GET
   * @step 檢查 cost.tps | 輸入值仍是剛輸入的值，旁有「未儲存：<原因>」
   * @step 檢查 cost.sla | 呈現重讀值，沒有「未儲存」
   * @pass 失敗欄的輸入沒有被重讀結果覆蓋
   * @story US11.2
   */
  test('keeps the failed field input and applies the reloaded value to the saved one', async ({ page }) => {
    const state = detailWorld(1);
    state.putStatus = (id) => (id === 'cost.tps' ? 422 : 200);
    const rec = await setupApp(page, state);
    await page.goto(detailUrl('requirements'));
    await page.getByTestId('requirements-field-cost-sla').fill('e2e-value-sla-new');
    await page.getByTestId('requirements-field-cost-tps').fill('e2e-value-tps-new');
    await page.getByTestId('requirements-save').click();

    await expect(page.getByTestId('requirements-unsaved-cost-tps')).toContainText('未儲存');
    await expect(page.getByTestId('requirements-unsaved-cost-tps')).toContainText('值超過允許的長度');
    await expect(page.getByTestId('requirements-field-cost-tps')).toHaveValue('e2e-value-tps-new');
    await expect(page.getByTestId('requirements-field-cost-sla')).toHaveValue('e2e-value-sla-new');
    await expect(page.getByTestId('requirements-unsaved-cost-sla')).toHaveCount(0);
    await expect(page.getByTestId('requirements-unfilled-cost-sla')).toHaveCount(0);
    expect(rec.count('PUT', RE_FIELD)).toBe(2);
    expect(rec.count('GET', RE_FIELDS)).toBe(2);
  });

  /**
   * @purpose 儲存成功但其後的重讀失敗：成功欄保留送出值並標「已儲存、重新整理失敗」；總覽顯示無法取得；[重新整理] 成功後回到正常。
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 200 | 寫入成功
   * @api GET /api/requirements/systems/{system_id}/fields -> 500 | 儲存後的重讀失敗
   * @ui /projects/:projectId | 需求籤與總覽籤
   * @given 單一系統；進頁後把欄位 GET 改為 500
   * @step 改 cost.sla 並儲存 | 欄位仍顯示送出值，旁有「已儲存、重新整理失敗」
   * @step 切到總覽 | 未填需求欄位為「無法取得」
   * @step 切回需求籤，GET 恢復 200 後按 [重新整理] | [重新整理] 消失，欄位為伺服器值、沒有「未填」
   * @pass 送出的值在重讀失敗時沒有消失；總覽不停在舊數字
   * @story US11.2
   */
  test('keeps saved drafts when the reload fails and recovers on refresh', async ({ page }) => {
    const state = detailWorld(1);
    await setupApp(page, state);
    await page.goto(detailUrl('requirements'));
    await expect(page.getByTestId('requirements-field-cost-sla')).toBeVisible();
    state.fieldsStatus.set(100, 500);
    await page.getByTestId('requirements-field-cost-sla').fill('e2e-value-sla-stale');
    await page.getByTestId('requirements-save').click();
    await expect(page.getByTestId('requirements-saved-stale-cost-sla')).toHaveText('已儲存、重新整理失敗');
    await expect(page.getByTestId('requirements-field-cost-sla')).toHaveValue('e2e-value-sla-stale');
    await expect(page.getByTestId('requirements-reload')).toBeVisible();

    await page.getByTestId('project-tab-overview').click();
    await expect(page.getByTestId('project-count-unfilled')).toContainText('無法取得');

    await page.getByTestId('project-tab-requirements').click();
    state.fieldsStatus.delete(100);
    await page.getByTestId('requirements-reload').click();
    await expect(page.getByTestId('requirements-reload')).toHaveCount(0);
    await expect(page.getByTestId('requirements-field-cost-sla')).toHaveValue('e2e-value-sla-stale');
    await expect(page.getByTestId('requirements-unfilled-cost-sla')).toHaveCount(0);
    await page.getByTestId('project-tab-overview').click();
    await expect(page.getByTestId('project-count-unfilled')).toHaveText('未填需求欄位 4');
  });

  /**
   * @purpose 把有值的欄位改成空白並儲存即清空：送出空值 PUT、不帶代寫標示、不發 DELETE。
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 200 | 空值寫入＝清空
   * @ui /projects/:projectId | 需求籤
   * @given 單一系統，cost.sla 已有值
   * @step 清空 cost.sla 並儲存 | PUT 本體為 {"value":""}，沒有 on_behalf_of
   * @step 檢查請求紀錄與畫面 | 沒有任何 DELETE；該欄重讀後顯示「未填」
   * @pass 清空走空值 PUT，且不偽稱是代寫
   * @story US11.2
   */
  test('clears a field with an empty PUT and never sends DELETE', async ({ page }) => {
    const state = detailWorld(1);
    state.fields.set(100, freshFields({ 'cost.sla': 'e2e-value-to-clear' }));
    const rec = await setupApp(page, state);
    await page.goto(detailUrl('requirements'));
    await page.getByTestId('requirements-field-cost-sla').fill('');
    await page.getByTestId('requirements-save').click();
    await expect(page.getByTestId('requirements-unfilled-cost-sla')).toHaveText('未填');
    const puts = rec.all.filter((r) => r.method === 'PUT');
    expect(puts).toHaveLength(1);
    expect(JSON.parse(puts[0].body ?? '{}')).toEqual({ value: '' });
    expect(rec.all.filter((r) => r.method === 'DELETE')).toHaveLength(0);
  });

  /**
   * @purpose 單一系統專案：總覽未填數等於需求籤「未填」文字數；儲存一欄後為 N−1；全部已填時為 0 且沒有任何「未填」。
   * @api GET /api/requirements/systems/{system_id}/fields -> 200 | 未填計數與欄位（同一份回應）
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 200 | 寫入
   * @ui /projects/:projectId | 總覽籤與需求籤
   * @given 單一系統，五欄皆未填
   * @step 開啟總覽與需求籤 | 總覽為 5，需求籤「未填」文字 5 個
   * @step 在需求籤儲存一欄後切到總覽 | 總覽為 4，切籤沒有發出任何請求
   * @step 改為全部已填的專案並開啟 | 總覽為 0，需求籤「未填」文字 0 個
   * @pass 兩處讀同一份來源，數字一致且隨儲存更新
   * @story US11.3
   */
  test('keeps the overview unfilled count equal to the requirements tab', async ({ page }) => {
    const state = detailWorld(1);
    const rec = await setupApp(page, state);
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-count-unfilled')).toHaveText('未填需求欄位 5');
    await page.getByTestId('project-tab-requirements').click();
    await expect(page.locator('[data-testid^="requirements-unfilled-"]')).toHaveCount(5);

    await page.getByTestId('requirements-field-arch-avail').fill('e2e-value-avail');
    await page.getByTestId('requirements-save').click();
    await expect(page.locator('[data-testid^="requirements-unfilled-"]')).toHaveCount(4);
    const before = rec.all.length;
    await page.getByTestId('project-tab-overview').click();
    await expect(page.getByTestId('project-count-unfilled')).toHaveText('未填需求欄位 4');
    expect(rec.all.length).toBe(before);

    const full = detailWorld(1);
    full.fields.set(
      100,
      freshFields({
        'cost.sla': 'e2e-v1',
        'cost.tps': 'e2e-v2',
        'cost.users': 'e2e-v3',
        'arch.avail': 'e2e-v4',
        'arch.retention': 'e2e-v5',
      })
    );
    Object.assign(state, full);
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-count-unfilled')).toHaveText('未填需求欄位 0');
    await page.getByTestId('project-tab-requirements').click();
    await expect(page.getByTestId('requirements-field-cost-sla')).toHaveValue('e2e-v1');
    await expect(page.locator('[data-testid^="requirements-unfilled-"]')).toHaveCount(0);
  });

  /**
   * @purpose 不具 K4 view 者：沒有需求籤、tab=requirements 退回總覽、總覽沒有未填與待補兩區，且不發需求欄位請求。
   * @api GET /api/hierarchy/projects/{project_id}/systems -> 200 | 系統清單
   * @ui /projects/:projectId | 總覽籤
   * @given K4 三旗標皆 false 的帳號；專案有兩個系統
   * @step 開啟 ?tab=requirements | 選取的是總覽籤；籤列只有總覽與記憶摘要
   * @step 檢查總覽 | 沒有 project-count-unfilled 與 project-pending-requirements
   * @step 檢查請求紀錄 | 對 /api/requirements 的請求數為 0
   * @pass 沒有權限的資料不顯示 0、不發出必然被拒的請求
   * @story US11.3
   */
  test('hides the requirements tab and unfilled areas without K4 view', async ({ page }) => {
    const state = detailWorld(2);
    state.perms.K4 = NONE;
    const rec = await setupApp(page, state);
    await page.goto(detailUrl('requirements'));
    await expect(page.getByTestId('project-tab-overview')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('project-tab-requirements')).toHaveCount(0);
    await expect(page.getByTestId('project-count-systems')).toHaveText('系統 2');
    await expect(page.getByTestId('project-recent-changes-empty')).toBeVisible();
    await expect(page.getByTestId('project-count-unfilled')).toHaveCount(0);
    await expect(page.getByTestId('project-pending-requirements')).toHaveCount(0);
    expect(rec.all.filter((r) => r.path.startsWith('/api/requirements/'))).toHaveLength(0);
  });

  /**
   * @purpose 三籤是可用鍵盤操作的 tablist；切籤只改網址查詢參數、不新增歷史、不發請求。
   * @api GET /api/requirements/systems/{system_id}/fields -> 200 | 進頁時的唯一一次欄位讀取
   * @ui /projects/:projectId | 籤列（總覽／需求／記憶摘要）
   * @given 具 K4 的帳號；單一系統
   * @step 聚焦總覽籤並按右鍵 | 需求籤 aria-selected=true 且取得焦點
   * @step 按 End，再按 Home | 依序選到記憶摘要、總覽
   * @step 檢查切籤前後 | pathname 不變、history.length 不增、/api 請求數不增
   * @pass 方向鍵與 Home／End 生效；切籤沒有任何副作用
   * @story US11.3
   */
  test('switches tabs by keyboard without history entries or requests', async ({ page }) => {
    const rec = await setupApp(page, detailWorld(1));
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-count-unfilled')).toHaveText('未填需求欄位 5');
    await expect(page.getByTestId('project-recent-changes-empty')).toBeVisible();
    const requests = rec.all.length;
    const historyLength = await page.evaluate(() => history.length);
    const pathname = new URL(page.url()).pathname;

    await page.getByTestId('project-tab-overview').focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByTestId('project-tab-requirements')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('project-tab-requirements')).toBeFocused();
    await page.keyboard.press('End');
    await expect(page.getByTestId('project-tab-memory')).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('Home');
    await expect(page.getByTestId('project-tab-overview')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('project-tab-overview')).toHaveAttribute('tabindex', '0');
    await expect(page.getByTestId('project-tab-memory')).toHaveAttribute('tabindex', '-1');

    expect(new URL(page.url()).pathname).toBe(pathname);
    expect(await page.evaluate(() => history.length)).toBe(historyLength);
    expect(rec.all.length).toBe(requests);
  });

  /**
   * @purpose 無資料來源的三處誠實呈現：架構圖「尚無法取得」、記憶摘要籤固定說明且不打記憶 API、頁首只有 [成員]。
   * @api GET /api/hierarchy/projects -> 200 | 專案資料取自清單
   * @ui /projects/:projectId | 總覽籤計數、記憶摘要籤、頁首
   * @given 具 K3 view 的帳號；單一系統
   * @step 開啟總覽 | 架構圖計數為「尚無法取得」
   * @step 切到記憶摘要籤 | 顯示「專案記憶的彙整尚未提供」，對 /api/memory 的請求數為 0
   * @step 檢查頁首 | 有 [成員]、沒有 [設定]
   * @pass 沒有任何數字或內容是推估或冒充出來的
   * @story US11.3
   */
  test('renders honest placeholders for diagrams, memory summary and settings', async ({ page }) => {
    const rec = await setupApp(page, detailWorld(1));
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-count-diagrams')).toContainText('尚無法取得');
    await page.getByTestId('project-tab-memory').click();
    await expect(page.getByTestId('memory-summary-unavailable')).toContainText('專案記憶的彙整尚未提供');
    await expect(page.getByTestId('project-members-link')).toHaveAttribute('href', '/projects/10/members');
    await expect(page.getByRole('button', { name: '設定' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: '設定' })).toHaveCount(0);
    expect(rec.all.filter((r) => r.path.startsWith('/api/memory/'))).toHaveLength(0);
  });

  /**
   * @purpose 最近變更照實標示部分來源；最多 5 筆、null 時間排最後、同時間依 id 由大到小；某系統失敗時保留已取得的列並標示。
   * @api GET /api/hierarchy/diagram-changes -> 200 | 逐系統的變更紀錄
   * @api GET /api/hierarchy/diagram-changes -> 500 | 某系統的變更紀錄讀取失敗
   * @ui /projects/:projectId | 總覽籤「最近變更」
   * @given 兩個系統共 7 筆變更（含兩筆 created_at 為 null、兩筆同時間）
   * @step 開啟總覽 | 標示文字逐字為「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」；恰 5 列，順序為 6、5、4、3、2
   * @step 沒有任何變更的專案 | 顯示「沒有符合條件的變更紀錄」
   * @step 第二個系統的變更紀錄回 500 | 顯示「部分變更無法取得」，第一個系統的列仍在
   * @pass 部分來源不被呈現成完整歷史；排序決定性
   * @story US11.3
   */
  test('lists at most five recent changes with honest scope, ordering and partial failure', async ({ page }) => {
    const change = (id: number, at: string | null): ChangeStub => ({
      id,
      diagram_id: 40 + id,
      source: 'brain_orchestration',
      actor_user_id: SELF_ID,
      requirement_summary: `e2e-change-${id}`,
      requirement_label: '',
      created_at: at,
    });
    const state = detailWorld(2);
    state.changes.set(100, [
      change(1, null),
      change(2, '2026-09-20T00:00:00Z'),
      change(3, '2026-09-25T00:00:00Z'),
      change(4, '2026-09-25T00:00:00Z'),
    ]);
    state.changes.set(101, [
      change(5, '2026-09-26T00:00:00Z'),
      change(6, '2026-09-27T00:00:00Z'),
      change(7, null),
    ]);
    await setupApp(page, state);
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-recent-changes-scope')).toHaveText(
      '只含經大腦、已歸屬系統、且為你自己擁有之圖的變更'
    );
    const rows = page.locator('[data-testid^="project-recent-change-"]');
    await expect(rows).toHaveCount(5);
    const ids = await rows.evaluateAll((els) => els.map((el) => el.getAttribute('data-testid')));
    expect(ids).toEqual([
      'project-recent-change-6',
      'project-recent-change-5',
      'project-recent-change-4',
      'project-recent-change-3',
      'project-recent-change-2',
    ]);

    state.changes = new Map();
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-recent-changes-empty')).toHaveText('沒有符合條件的變更紀錄');

    state.changes.set(100, [change(8, null), change(9, null)]);
    state.changesStatus.set(101, 500);
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-recent-changes-partial')).toHaveText('部分變更無法取得');
    const after = await rows.evaluateAll((els) => els.map((el) => el.getAttribute('data-testid')));
    expect(after).toEqual(['project-recent-change-9', 'project-recent-change-8']);
    await expect(page.getByTestId('project-recent-changes-empty')).toHaveCount(0);
  });

  /**
   * @purpose 專案不在可見清單、或系統清單回 404 時呈現「查不到這個專案」，不呈現成空專案。
   * @api GET /api/hierarchy/projects/{project_id}/systems -> 404 | 非成員或被移出的建立者
   * @ui /projects/:projectId | not-found 態
   * @given 專案清單含專案 10，但它的系統清單回 404；另以不在清單內的專案 99 直接進入
   * @step 開啟 /projects/10 | 出現 project-not-found；沒有「尚無系統」、沒有需求籤空狀態
   * @step 開啟 /projects/99 | 出現 project-not-found
   * @pass 非成員看不到一個「像是空的」專案
   * @story US12.1
   */
  test('renders not-found when the project is invisible instead of an empty project', async ({ page }) => {
    const state = detailWorld(0);
    state.systemsStatus.set(10, 404);
    await setupApp(page, state);
    await page.goto(detailUrl('requirements'));
    await expect(page.getByTestId('project-not-found')).toContainText('查不到這個專案');
    await expect(page.getByTestId('requirements-empty')).toHaveCount(0);
    await expect(page.getByTestId('project-count-systems')).toHaveCount(0);
    await page.goto(detailUrl('overview', 99));
    await expect(page.getByTestId('project-not-found')).toBeVisible();
  });

  /**
   * @purpose 清單頁的系統清單扇出同時最多 4 個在途、不截斷；排隊中的列顯示載入子狀態而非「尚無系統」。
   * @api GET /api/hierarchy/projects/{project_id}/systems -> 200 | 6 個專案各一次
   * @ui /projects | 清單頁各列
   * @given 6 個專案；前 4 個的系統清單延遲 1 秒、第 5、6 個延遲 3 秒
   * @step 開啟 /projects 並等待第 5、6 個請求發出後 | 第 5、6 列為載入子狀態
   * @step 等待全部完成 | 6 列都是「N 個系統」
   * @pass 系統清單在途最大值恰為 4；6 個請求全部發出
   * @story US11.1
   */
  test('fans out the list page with at most four requests in flight and no truncation', async ({ page }) => {
    const state = defaultState();
    state.projects = Array.from({ length: 6 }, (_, i) => project(i + 1, `e2e-project-fan-${i + 1}`));
    for (let i = 1; i <= 6; i += 1) state.systems.set(i, [system(200 + i, i, `e2e-system-fan-${i}`)]);
    state.systemsDelayMs = (pid) => (pid <= 4 ? 1000 : 3000);
    const rec = await setupApp(page, state);
    await page.goto('/projects');
    await expect.poll(() => rec.count('GET', RE_SYSTEMS), { timeout: 5000 }).toBe(6);
    await expect(page.getByTestId('project-list-row-systems-5')).toHaveAttribute('data-state', 'loading');
    await expect(page.getByTestId('project-list-row-systems-6')).toHaveAttribute('data-state', 'loading');
    await expect(page.getByTestId('project-list-row-systems-5')).not.toHaveText('尚無系統');
    for (let i = 1; i <= 6; i += 1) {
      await expect(page.getByTestId(`project-list-row-count-${i}`)).toHaveText('1 個系統', { timeout: 6000 });
    }
    expect(rec.maxInFlight('systems')).toBe(4);
  });

  /**
   * @purpose 詳情頁扇出共用一個上限 4 的佇列，先全部需求欄位、再全部變更紀錄，各依系統 id 遞增。
   * @api GET /api/requirements/systems/{system_id}/fields -> 200 | 3 個系統各一次
   * @api GET /api/hierarchy/diagram-changes -> 200 | 3 個系統各一次
   * @ui /projects/:projectId | 總覽籤
   * @given 3 個系統；兩種端點皆延遲 800 ms
   * @step 開啟總覽並等待 6 個請求完成 | 前 3 個為需求欄位（系統 100、101、102），後 3 個為變更紀錄（同序）
   * @pass 在途最大值恰為 4；發出順序符合兩段入列
   * @story US11.3
   */
  test('fans out the detail page fields first and changes second with at most four in flight', async ({ page }) => {
    const state = detailWorld(3);
    state.fieldsDelayMs = () => 800;
    state.changesDelayMs = () => 800;
    const rec = await setupApp(page, state);
    await page.goto(detailUrl('overview'));
    await expect(page.getByTestId('project-count-unfilled')).toHaveText('未填需求欄位 15', { timeout: 6000 });
    await expect(page.getByTestId('project-recent-changes-empty')).toBeVisible({ timeout: 6000 });
    const order = rec.all
      .filter((r) => r.method === 'GET' && (RE_FIELDS.test(r.path) || RE_CHANGES.test(r.path)))
      .map((r) => (RE_FIELDS.test(r.path) ? `fields:${RE_FIELDS.exec(r.path)?.[1]}` : `changes:${new URLSearchParams(r.search).get('system_id')}`));
    expect(order).toEqual([
      'fields:100',
      'fields:101',
      'fields:102',
      'changes:100',
      'changes:101',
      'changes:102',
    ]);
    expect(rec.maxInFlight('detail')).toBe(4);
  });

  /**
   * @purpose 離開頁面後佇列中尚未發出的扇出請求不再發出。
   * @api GET /api/hierarchy/projects/{project_id}/systems -> 200 | 8 個專案的系統清單
   * @ui /projects | 清單頁（離開前）
   * @ui /memory | 離開後的落地頁
   * @given 8 個專案；系統清單延遲 2 秒
   * @step 開啟 /projects，0.5 秒後以 Sidebar 前往「我的記憶」 | 頁面換到 /memory（SPA 導航，非整頁重載）
   * @step 等待 3 秒 | 系統清單請求總數 ≤ 4
   * @pass 卸載之後沒有新的扇出請求
   * @story US11.1
   */
  test('stops sending queued fan-out requests after leaving the page', async ({ page }) => {
    const state = defaultState();
    state.projects = Array.from({ length: 8 }, (_, i) => project(i + 1, `e2e-project-leave-${i + 1}`));
    state.systemsDelayMs = () => 2000;
    const rec = await setupApp(page, state);
    await page.goto('/projects');
    await expect.poll(() => rec.count('GET', RE_SYSTEMS)).toBe(4);
    await page.waitForTimeout(500);
    await page.getByTestId('sidebar-memory-link').click();
    await expect(page).toHaveURL(/\/memory$/);
    await page.waitForTimeout(3000);
    expect(rec.count('GET', RE_SYSTEMS)).toBeLessThanOrEqual(4);
  });

  /**
   * @purpose 主控台輸出不含任何專案名、系統名或欄位值。
   * @api GET /api/hierarchy/projects -> 200 | 專案清單
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 422 | 一次失敗的儲存
   * @ui /projects | 清單頁
   * @ui /projects/:projectId | 總覽、需求、記憶摘要三籤
   * @given 名稱與值皆為獨特假字串；一欄的 PUT 回 422、一個專案的系統清單回 500
   * @step 走過清單頁、詳情頁三籤並做一次部分失敗的儲存 | 畫面照常
   * @step 檢查收集到的主控台訊息 | 不含任何一個獨特字串
   * @pass 使用者資料不會經主控台外洩（本 repo 為 public，CI log 可公開讀取）
   * @story US11.2
   */
  test('never writes project names, system names or field values to the console', async ({ page }) => {
    const state = detailWorld(1);
    state.projects.push(project(12, 'e2e-project-console-broken'));
    state.systemsStatus.set(12, 500);
    state.putStatus = () => 422;
    const rec = await setupApp(page, state);
    await page.goto('/projects');
    await expect(page.getByTestId('project-list-row-systems-12')).toHaveText('系統清單讀取失敗');
    await page.goto(detailUrl('requirements'));
    await page.getByTestId('requirements-field-cost-sla').fill('e2e-value-console-secret');
    await page.getByTestId('requirements-save').click();
    await expect(page.getByTestId('requirements-unsaved-cost-sla')).toBeVisible();
    await page.getByTestId('project-tab-overview').click();
    await page.getByTestId('project-tab-memory').click();
    const forbidden = [
      'e2e-project-detail',
      'e2e-project-console-broken',
      'e2e-system-1',
      'e2e-value-console-secret',
    ];
    for (const line of rec.console) {
      for (const text of forbidden) expect(line).not.toContain(text);
    }
  });

  /**
   * @purpose 儲存失敗或重讀失敗後切到其他籤再切回，輸入值與「未儲存」「已儲存、重新整理失敗」標記都還在。
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 200 | cost.sla 寫入成功
   * @api PUT /api/requirements/systems/{system_id}/fields/{agent_group}/{field_key} -> 422 | cost.tps 寫入失敗
   * @api GET /api/requirements/systems/{system_id}/fields -> 500 | 儲存後的重讀失敗
   * @ui /projects/:projectId | 需求籤與總覽籤
   * @given 單一系統；cost.tps 的 PUT 回 422；進頁後把欄位 GET 改為 500
   * @step 改 cost.sla 與 cost.tps 後按 [儲存] | cost.tps 標「未儲存」、cost.sla 標「已儲存、重新整理失敗」
   * @step 切到總覽，再切回需求籤 | 兩欄的輸入值與兩種標記都仍在
   * @pass 切籤不讓使用者的輸入與失敗狀態消失
   * @story US11.2
   * @note 程式審查 R-02：需求籤切走即卸載，若輸入狀態放在需求籤內，本案的第二步會紅。
   */
  test('keeps unsaved input and failure marks after switching tabs', async ({ page }) => {
    const state = detailWorld(1);
    state.putStatus = (id) => (id === 'cost.tps' ? 422 : 200);
    await setupApp(page, state);
    await page.goto(detailUrl('requirements'));
    await expect(page.getByTestId('requirements-field-cost-sla')).toBeVisible();
    state.fieldsStatus.set(100, 500);
    await page.getByTestId('requirements-field-cost-sla').fill('e2e-value-sla-kept');
    await page.getByTestId('requirements-field-cost-tps').fill('e2e-value-tps-kept');
    await page.getByTestId('requirements-save').click();
    await expect(page.getByTestId('requirements-unsaved-cost-tps')).toContainText('未儲存');
    await expect(page.getByTestId('requirements-saved-stale-cost-sla')).toBeVisible();

    await page.getByTestId('project-tab-overview').click();
    await expect(page.getByTestId('project-count-unfilled')).toContainText('無法取得');
    await page.getByTestId('project-tab-requirements').click();

    await expect(page.getByTestId('requirements-field-cost-tps')).toHaveValue('e2e-value-tps-kept');
    await expect(page.getByTestId('requirements-unsaved-cost-tps')).toContainText('未儲存');
    await expect(page.getByTestId('requirements-field-cost-sla')).toHaveValue('e2e-value-sla-kept');
    await expect(page.getByTestId('requirements-saved-stale-cost-sla')).toHaveText('已儲存、重新整理失敗');
  });

  /**
   * @purpose 非數字的專案網址呈現「查不到這個專案」，不會永遠停在載入中。
   * @ui /projects/:projectId | not-found 態
   * @given 具 K2 view 的帳號
   * @step 開啟 /projects/abc | 出現 project-not-found，沒有「正在載入專案」
   * @step 檢查請求紀錄 | 對 /api/hierarchy 的請求數為 0
   * @pass 不可能存在的專案 id 直接給出結論
   * @story US12.1
   */
  test('renders not-found for a non-numeric project address', async ({ page }) => {
    const rec = await setupApp(page, detailWorld(1));
    await page.goto('/projects/abc');
    await expect(page.getByTestId('project-not-found')).toContainText('查不到這個專案');
    await expect(page.getByText('正在載入專案…')).toHaveCount(0);
    expect(rec.all.filter((r) => r.path.startsWith('/api/hierarchy/'))).toHaveLength(0);
  });
});
