import { test, expect, type Page, type Route, type WebSocketRoute } from '@playwright/test';
import * as F from '../../src/brain/testing/wsFrames';

// U16 object picker — 「切換對象」選單的 e2e（US9.2）。
//
// **全部走攔截層**：`page.routeWebSocket` 扮演大腦伺服器、`page.route` 樁化全部 HTTP（`/api/auth/me` 控制權限與
// 身分、`/api/hierarchy` 四支端點控制清單與建立）。不碰真實後端、Redis、LLM 或 n8n；token 為固定假值。
//
// **伺服器訊框只由 `src/brain/testing/wsFrames.ts` 的建構器產生**（eslint tests 區塊擋下手寫訊框，EPN-19）。
//
// **請求計數類案例必須對正式建置執行**（`vite preview`；開發模式 StrictMode 的雙掛載會讓 listProjects 計為 2，
// nfr-design-corrections D-01）。計數以 route handler 記錄，與 page.on('request') 無關。
//
// **名稱穩定性（合併後不可改）**：TCMS 案例名稱為 `<describe> › <test>`；`U16 object picker` 與每個 test 字串
// 一旦合併就不得再改。

const M = 'e2e-u16';
const FAKE_TOKEN = 'e2e-u16-fake-token';
const SELF_ID = 1601;
const OTHER_ID = 1602;
const VIEW_EDIT = { view: true, edit: true, review: false };
const VIEW_ONLY = { view: true, edit: false, review: false };

type Perm = typeof VIEW_EDIT;
type ClientFrame = { type: string; payload: Record<string, unknown> };

interface ProjectStub {
  id: number;
  name: string;
  owner_user_id: number;
  is_default: boolean;
  created_at: string;
}
interface SystemStub {
  id: number;
  project_id: number;
  name: string;
  is_default: boolean;
  created_at: string;
}

const proj = (id: number, name: string, owner = SELF_ID): ProjectStub => ({
  id,
  name,
  owner_user_id: owner,
  is_default: false,
  created_at: '2026-10-01T00:00:00Z',
});
const sys = (id: number, projectId: number, name: string): SystemStub => ({
  id,
  project_id: projectId,
  name,
  is_default: false,
  created_at: '2026-10-02T00:00:00Z',
});

// ---------------------------------------------------------------------------
// 假大腦伺服器（形狀沿用 entry-page.spec.ts 的 BrainServer，刻意不抽共用模組：不改已交付單元的 spec）
// ---------------------------------------------------------------------------

interface BrainConn {
  ws: WebSocketRoute;
  frames: ClientFrame[];
  closed: boolean;
}

interface Target {
  pid: string | null;
  sid: string | null;
  did: string | null;
}

class BrainServer {
  conns: BrainConn[] = [];
  echo = true;
  shared: Target = { pid: null, sid: null, did: null };
  isolated: { workspace: Target; assessment: Target } = {
    workspace: { pid: null, sid: null, did: null },
    assessment: { pid: null, sid: null, did: null },
  };
  modes: { workspace: 'shared' | 'isolated'; assessment: 'shared' | 'isolated' } = { workspace: 'shared', assessment: 'shared' };
  names: Record<string, string> = {};

  async install(page: Page): Promise<void> {
    await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, (ws) => {
      const conn: BrainConn = { ws, frames: [], closed: false };
      this.conns.push(conn);
      ws.onClose(() => {
        conn.closed = true;
      });
      ws.onMessage((raw) => {
        const data = JSON.parse(String(raw)) as ClientFrame;
        conn.frames.push(data);
        if (data.type === 'hello') this.sendSnapshot(conn);
        if (data.type === 'set_work_target' && this.echo) {
          const p = data.payload as { projectId: string | null; systemId: string | null; diagramId: string | null; segment: string };
          const t: Target = { pid: p.projectId, sid: p.systemId, did: p.diagramId };
          if (p.segment === 'shared') this.shared = t;
          else this.isolated[p.segment as 'workspace' | 'assessment'] = t;
          this.broadcast(this.targetFrame(p.segment as 'shared' | 'workspace' | 'assessment'));
        }
      });
    });
  }

  name(prefix: string, id: string | null): string | null {
    return id === null ? null : this.names[`${prefix}${id}`] ?? null;
  }

  targetFrame(segment: 'shared' | 'workspace' | 'assessment'): string {
    const t = segment === 'shared' ? this.shared : this.isolated[segment];
    return F.encodeFrame(
      F.workTargetFrame(segment, t.pid, t.sid, t.did, this.name('p', t.pid), this.name('s', t.sid), this.name('d', t.did)),
    );
  }

  sendSnapshot(conn: BrainConn): void {
    const iso = (['workspace', 'assessment'] as const)
      .filter((s) => this.modes[s] === 'isolated')
      .map((s) => {
        const t = this.isolated[s];
        return F.workTargetFrame(s, t.pid, t.sid, t.did, this.name('p', t.pid), this.name('s', t.sid), this.name('d', t.did));
      });
    const t = this.shared;
    const sharedFrame = F.workTargetFrame('shared', t.pid, t.sid, t.did, this.name('p', t.pid), this.name('s', t.sid), this.name('d', t.did));
    for (const f of F.snapshotFrames(sharedFrame, [], this.modes.workspace, this.modes.assessment, iso)) conn.ws.send(f);
  }

  get last(): BrainConn {
    return this.conns[this.conns.length - 1];
  }

  broadcast(frame: string): void {
    for (const c of this.conns.filter((x) => !x.closed)) c.ws.send(frame);
  }

  send(frame: string): void {
    this.last.ws.send(frame);
  }

  framesOf(type: string): ClientFrame[] {
    return this.conns.flatMap((c) => c.frames.filter((f) => f.type === type));
  }
}

// ---------------------------------------------------------------------------
// HTTP 攔截：/api/auth/me 與 /api/hierarchy
// ---------------------------------------------------------------------------

interface Hierarchy {
  projects: ProjectStub[];
  systems: Record<number, SystemStub[]>;
  projectsStatus: number;
  /** 依呼叫次序（0 起）決定專案清單回應前的延遲與內容覆寫。 */
  projectsHook?: (call: number) => Promise<ProjectStub[] | void> | void;
  systemsStatus: Record<number, number>;
  /** 系統清單回應前的閘門（依專案 id 與該專案的呼叫次序）。 */
  systemsGate?: (pid: number) => Promise<void> | void;
  postProjectStatus: number;
  postSystemStatus: number;
  postDelayMs: number;
  nextProjectId: number;
  nextSystemId: number;
  /** `METHOD pathname?search`，依到達順序。 */
  log: string[];
  inFlightSystems: number;
  maxInFlightSystems: number;
}

interface SetupOptions {
  perms?: Record<string, Perm>;
  /** /me 依呼叫次序的回應：'ok'＝200 帶 id、'no-id'＝200 不帶 id、'fail'＝500（用完沿用最後一個）。 */
  meSequence?: Array<'ok' | 'no-id' | 'fail'>;
  hierarchy?: Partial<Hierarchy>;
}

interface Harness {
  server: BrainServer;
  hier: Hierarchy;
  meCalls: () => number;
}

const DEFAULT_PERMS: Record<string, Perm> = { K1: VIEW_EDIT, K2: VIEW_EDIT, A1: VIEW_EDIT, A3: VIEW_EDIT };

async function json(route: Route, status: number, body: unknown): Promise<void> {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

async function setup(page: Page, opts: SetupOptions = {}): Promise<Harness> {
  const server = new BrainServer();
  const hier: Hierarchy = {
    projects: [],
    systems: {},
    projectsStatus: 200,
    systemsStatus: {},
    postProjectStatus: 200,
    postSystemStatus: 200,
    postDelayMs: 0,
    nextProjectId: 900,
    nextSystemId: 9000,
    log: [],
    inFlightSystems: 0,
    maxInFlightSystems: 0,
    ...opts.hierarchy,
  };
  let meCalls = 0;
  let projectCalls = 0;

  await page.addInitScript((token) => {
    sessionStorage.setItem('token', token);
    const w = window as unknown as { __announcements: { src: string | null; text: string }[] };
    w.__announcements = [];
    const SEL = '[data-testid="brain-live"] [data-testid="live-region"], [data-testid="brain-object-picker-live"]';
    const observer = new MutationObserver((mutations) => {
      const regions = new Set<Element>();
      for (const m of mutations) {
        const node = m.target;
        const el = node.nodeType === 1 ? (node as Element) : node.parentElement;
        const region = el ? el.closest(SEL) : null;
        if (region) regions.add(region);
        m.addedNodes.forEach((added) => {
          if (added.nodeType !== 1) return;
          const a = added as Element;
          if (a.matches(SEL)) regions.add(a);
          a.querySelectorAll(SEL).forEach((x) => regions.add(x));
        });
      }
      regions.forEach((r) => {
        const text = (r.textContent ?? '').trim();
        if (text) w.__announcements.push({ src: r.getAttribute('data-testid'), text });
      });
    });
    document.addEventListener('DOMContentLoaded', () => {
      observer.observe(document.body, { subtree: true, childList: true, characterData: true });
    });
  }, FAKE_TOKEN);

  // 後註冊者優先：先放兜底（GET 回 []、其他回 {}），再放具體端點。
  await page.route('**/api/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: route.request().method() === 'GET' ? '[]' : '{}' }),
  );
  await page.route('**/api/auth/me', async (route) => {
    const seq = opts.meSequence ?? ['ok'];
    const kind = seq[Math.min(meCalls, seq.length - 1)];
    meCalls += 1;
    if (kind === 'fail') return json(route, 500, { detail: 'boom' });
    const body: Record<string, unknown> = {
      username: `${M}-alice`,
      role: 'Project_Architect',
      is_active: true,
      authorization_status: 'approved',
      permissions: opts.perms ?? DEFAULT_PERMS,
      pending_request: null,
    };
    if (kind === 'ok') body.id = SELF_ID;
    return json(route, 200, body);
  });
  await page.route(/\/api\/hierarchy\/projects(\?.*)?$/, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    hier.log.push(`${req.method()} ${url.pathname}${url.search}`);
    if (req.method() === 'GET') {
      const call = projectCalls;
      projectCalls += 1;
      const override = hier.projectsHook ? await hier.projectsHook(call) : undefined;
      if (hier.projectsStatus !== 200) return json(route, hier.projectsStatus, { detail: 'nope' });
      return json(route, 200, override ?? hier.projects);
    }
    const name = (JSON.parse(req.postData() ?? '{}') as { name?: string }).name ?? '';
    if (hier.postDelayMs) await sleep(hier.postDelayMs);
    if (hier.postProjectStatus !== 200) return json(route, hier.postProjectStatus, { detail: 'nope' });
    const created = proj(hier.nextProjectId, name);
    hier.nextProjectId += 1;
    hier.projects = [...hier.projects, created];
    return json(route, 200, created);
  });
  await page.route(/\/api\/hierarchy\/projects\/\d+\/systems(\?.*)?$/, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    hier.log.push(`${req.method()} ${url.pathname}${url.search}`);
    const pid = Number(/projects\/(\d+)\/systems/.exec(url.pathname)?.[1]);
    if (req.method() === 'GET') {
      hier.inFlightSystems += 1;
      hier.maxInFlightSystems = Math.max(hier.maxInFlightSystems, hier.inFlightSystems);
      try {
        if (hier.systemsGate) await hier.systemsGate(pid);
        const status = hier.systemsStatus[pid] ?? 200;
        if (status !== 200) return await json(route, status, { detail: 'nope' });
        return await json(route, 200, hier.systems[pid] ?? []);
      } finally {
        hier.inFlightSystems -= 1;
      }
    }
    const name = (JSON.parse(req.postData() ?? '{}') as { name?: string }).name ?? '';
    if (hier.postDelayMs) await sleep(hier.postDelayMs);
    if (hier.postSystemStatus !== 200) return json(route, hier.postSystemStatus, { detail: 'nope' });
    const created = sys(hier.nextSystemId, pid, name);
    hier.nextSystemId += 1;
    hier.systems = { ...hier.systems, [pid]: [...(hier.systems[pid] ?? []), created] };
    return json(route, 200, created);
  });
  await page.route('**/api/collab/workspace/bootstrap', (route) => json(route, 200, { diagram: null, messages: [] }));
  await page.route('https://embed.diagrams.net/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><html><body></body></html>' }),
  );
  await page.routeWebSocket('**/api/collab/ws/**', () => undefined);
  await server.install(page);
  return { server, hier, meCalls: () => meCalls };
}

// ---------------------------------------------------------------------------
// 共用操作
// ---------------------------------------------------------------------------

const picker = (page: Page) => page.getByTestId('brain-object-picker');
const switchBtn = (page: Page) => page.getByTestId('brain-context-switch-object');

async function gotoReady(page: Page, path = '/'): Promise<void> {
  await page.goto(path);
  await expect(switchBtn(page)).toBeVisible();
}

async function openPicker(page: Page): Promise<void> {
  await switchBtn(page).click();
  await expect(picker(page)).toBeVisible();
  await expect(picker(page)).not.toHaveAttribute('data-state', 'loading');
}

const count = (hier: Hierarchy, entry: string) => hier.log.filter((l) => l === entry).length;
const getProjects = 'GET /api/hierarchy/projects';
const getSystems = (pid: number) => `GET /api/hierarchy/projects/${pid}/systems`;

async function announcements(page: Page): Promise<{ src: string | null; text: string }[]> {
  return page.evaluate(() => (window as unknown as { __announcements: { src: string | null; text: string }[] }).__announcements.slice());
}

/** 去掉重唸用的零寬空白（R-09：相同文案的第二次寫入以它造成內容變更）。 */
const stripMark = (text: string) => text.split(String.fromCharCode(0x200b)).join('');

async function activeTestId(page: Page): Promise<string | null> {
  return page.evaluate(() => (document.activeElement as HTMLElement | null)?.getAttribute('data-testid') ?? null);
}

/**
 * 讓送出端判定「連線不是 OPEN」而連線狀態仍為 ready，使 setWorkTarget 回 false：把頁面全域 `WebSocket.OPEN`
 * 改成不可能的值（`useBrainConnection` 的 sendFrame 以 `ws.readyState !== WebSocket.OPEN` 判定）。routeWebSocket
 * 會換掉頁面的 WebSocket 類別，覆寫原型上的 readyState 無效，故改寫比較基準。
 */
async function breakSocketSend(page: Page): Promise<void> {
  await page.evaluate(() => {
    Object.defineProperty(window.WebSocket, 'OPEN', { configurable: true, get: () => 99 });
  });
}

async function identityScenario(page: Page, meSequence: Array<'ok' | 'no-id' | 'fail'>): Promise<void> {
  const h = await setup(page, { meSequence });
  await gotoReady(page);
  await page.waitForLoadState('networkidle');
  const before = h.meCalls();
  await switchBtn(page).click();
  await expect(page.getByTestId('brain-object-identity-error')).toContainText('無法確認你的身分，請重新整理頁面');
  await expect(picker(page)).toHaveAttribute('data-state', 'error');
  await page.waitForTimeout(500);
  expect(h.meCalls() - before).toBe(1);
  expect(h.hier.log).toEqual([]);
  await page.getByTestId('brain-object-identity-retry').click();
  await expect.poll(() => h.meCalls() - before).toBe(2);
  await expect(page.getByTestId('brain-object-identity-error')).toBeVisible();
  await page.waitForTimeout(500);
  expect(h.meCalls() - before).toBe(2);
}

test.describe('U16 object picker', () => {
  /**
   * @purpose 選定系統即送出三層字串 id 的 set_work_target；伺服器回推前脈絡列不變，回推後才更新，換頁後三元組相同（AC9.2.2、BR11.2、NFR2.160、OPN-21）。
   * @ui / | 入口頁 brain-context-bar、brain-context-switch-object、brain-object-picker
   * @ui /workspace | 工作區脈絡列
   * @given 自有專案 7（系統 70）；作業對象尚未選定；假大腦不自動回推
   * @step 開啟選單、展開專案 7、點系統 70 | 送出 {projectId:'7', systemId:'70', diagramId:null, segment:'shared'}，選單關閉、焦點回切換鈕
   * @step 回推前檢視脈絡列 | data-state 仍為 no-object
   * @step 伺服器回推專案 7／系統 70 | 兩個名稱節點的 data-id 為 7 與 70
   * @step 重開選單 | 專案 7 預設展開，系統 70 標「目前」（aria-current）
   * @step 換到 /workspace | 脈絡列的專案與系統 data-id 仍為 7 與 70
   * @pass 送出值為字串、回推前不變、回推後相同、換頁後相同
   * @story US9.2
   * @note 字串 id 斷言擋的是「數字 id 被 as never 送出」（突變 M8）；回推前不變擋的是本地樂觀更新（NFR2.160）。
   */
  test('選系統送出字串三層 id 且回推前脈絡列不變', async ({ page }) => {
    const h = await setup(page, {
      hierarchy: { projects: [proj(7, `${M}-專案七`)], systems: { 7: [sys(70, 7, `${M}-系統七十`)] } },
    });
    h.server.echo = false;
    h.server.names = { p7: `${M}-專案七`, s70: `${M}-系統七十` };
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-expand-7').click();
    await page.getByTestId('brain-object-item-70').click();
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    expect(h.server.framesOf('set_work_target')[0].payload).toEqual({
      projectId: '7',
      systemId: '70',
      diagramId: null,
      segment: 'shared',
    });
    await expect(picker(page)).toHaveCount(0);
    expect(await activeTestId(page)).toBe('brain-context-switch-object');
    await expect(page.getByTestId('brain-context-bar')).toHaveAttribute('data-state', 'no-object');

    h.server.shared = { pid: '7', sid: '70', did: null };
    h.server.send(h.server.targetFrame('shared'));
    await expect(page.getByTestId('brain-context-name-project')).toHaveAttribute('data-id', '7');
    await expect(page.getByTestId('brain-context-name-system')).toHaveAttribute('data-id', '70');

    await openPicker(page);
    await expect(page.getByTestId('brain-object-expand-7')).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByTestId('brain-object-item-70')).toHaveAttribute('aria-current', 'true');
    await expect(page.getByTestId('brain-object-item-70')).toContainText('目前');

    await page.goto('/workspace');
    await expect(page.getByTestId('brain-context-name-project')).toHaveAttribute('data-id', '7');
    await expect(page.getByTestId('brain-context-name-system')).toHaveAttribute('data-id', '70');
  });

  /**
   * @purpose 零系統的專案本身可被選為作業對象（AC9.2.1、BR13.1）。
   * @ui / | brain-object-project-8、brain-object-group-empty-8
   * @given 自有專案 8，系統清單為空
   * @step 開啟選單並展開專案 8 | 顯示「尚無系統」，專案列 data-selectable=true
   * @step 點專案 8 | 送出 {projectId:'8', systemId:null, diagramId:null, segment:'shared'}
   * @pass 送出 systemId 為 null 的 set_work_target
   * @story US9.2
   */
  test('選零系統的專案送出 systemId 為 null', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(8, `${M}-空專案`)], systems: { 8: [] } } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-expand-8').click();
    await expect(page.getByTestId('brain-object-group-empty-8')).toHaveText('尚無系統');
    await expect(page.getByTestId('brain-object-project-8')).toHaveAttribute('data-selectable', 'true');
    await page.getByTestId('brain-object-project-8').click();
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    expect(h.server.framesOf('set_work_target')[0].payload).toEqual({
      projectId: '8',
      systemId: null,
      diagramId: null,
      segment: 'shared',
    });
  });

  /**
   * @purpose 具 K2 edit 者在選單內建立專案：恰一次 POST、成功即切過去並以頁面播報區告知，再開時新專案可選且標「目前」（AC9.2.1、BR14.2、BR14.5、F-04）。
   * @ui / | brain-object-create-project、brain-object-create-name、brain-object-create-submit
   * @given 具 K2 view＋edit；清單為空
   * @step 開啟選單 | empty 態且「+ 新增專案」可見
   * @step 點「+ 新增專案」、輸入名稱、送出 | POST /api/hierarchy/projects 恰 1 次
   * @step 檢視送出的訊框 | set_work_target 指向新專案 900（字串）、systemId 為 null
   * @step 檢視播報 | 頁面 live-region 出現「已建立並切換到 <名稱>」，選單內播報區沒有這句
   * @step 再開選單 | 新專案列 data-selectable=true 並標「目前」
   * @pass 建立一次、切換一次、關閉後才播報、再開可選
   * @story US9.2
   */
  test('具建立權限者建立專案後切過去且再開可選', async ({ page }) => {
    const h = await setup(page);
    await gotoReady(page);
    await openPicker(page);
    await expect(picker(page)).toHaveAttribute('data-state', 'empty');
    await page.getByTestId('brain-object-create-project').click();
    await expect(page.getByTestId('brain-object-create-name')).toBeFocused();
    await page.getByTestId('brain-object-create-name').fill(`${M}-新專案`);
    await page.getByTestId('brain-object-create-submit').click();
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    expect(count(h.hier, 'POST /api/hierarchy/projects')).toBe(1);
    expect(h.server.framesOf('set_work_target')[0].payload).toMatchObject({ projectId: '900', systemId: null, diagramId: null });
    await expect(picker(page)).toHaveCount(0);
    await expect.poll(async () => (await announcements(page)).filter((a) => a.text === `已建立並切換到 ${M}-新專案`)).toEqual([
      { src: 'live-region', text: `已建立並切換到 ${M}-新專案` },
    ]);
    await openPicker(page);
    await expect(page.getByTestId('brain-object-project-900')).toHaveAttribute('data-selectable', 'true');
    await expect(page.getByTestId('brain-object-project-900')).toHaveAttribute('aria-current', 'true');
  });

  /**
   * @purpose 擁有者在自己專案的群組旁建立系統：系統歸屬該專案、恰一次 POST、成功即切到新系統（AC9.2.2、BR14.3、BR14.5）。
   * @ui / | brain-object-create-system-7
   * @given 自有專案 7（無系統）；具 K2 view＋edit
   * @step 點專案 7 旁的「+ 新增系統」、輸入名稱、送出 | POST /api/hierarchy/projects/7/systems 恰 1 次
   * @step 檢視送出的訊框 | set_work_target 為 {projectId:'7', systemId:'9000'}
   * @pass 系統建在群組專案下並切過去
   * @story US9.2
   */
  test('擁有者在群組旁建立系統後切到新系統', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`)], systems: { 7: [] } } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-create-system-7').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-新系統`);
    await page.getByTestId('brain-object-create-submit').click();
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    expect(count(h.hier, 'POST /api/hierarchy/projects/7/systems')).toBe(1);
    expect(h.server.framesOf('set_work_target')[0].payload).toMatchObject({ projectId: '7', systemId: '9000', diagramId: null });
    await expect(picker(page)).toHaveCount(0);
  });

  /**
   * @purpose 無 K2 edit 者看不到任何建立入口；空清單只顯示請同事邀請的說明（BR14.2、BR14.6、OPN-11；AC9.2.3 的畫面面）。
   * @ui / | brain-object-empty、brain-object-create-project、brain-object-create-system-*
   * @given 具 K1 與 K2 view、無 K2 edit；第一輪清單為空，第二輪有自有專案 7
   * @step 開啟選單 | empty 態，說明為「你還沒有任何專案。需要具備建立權限的同事邀請你加入，或請管理者調整你的權限。」，無「+ 新增專案」
   * @step 清單改為有自有專案 7，重開選單 | 專案 7 可選，但群組旁無「+ 新增系統」、底部無「+ 新增專案」
   * @pass 兩種建立入口在無 K2 edit 時都不存在
   * @story US9.2
   * @note 擋的是「拿掉 can('K2','edit') 條件」（突變 M1）。
   */
  test('無建立權限者看不到建立入口且空清單只有說明', async ({ page }) => {
    const h = await setup(page, { perms: { K1: VIEW_EDIT, K2: VIEW_ONLY } });
    await gotoReady(page);
    await openPicker(page);
    await expect(picker(page)).toHaveAttribute('data-state', 'empty');
    await expect(page.getByTestId('brain-object-empty')).toHaveText(
      '你還沒有任何專案。需要具備建立權限的同事邀請你加入，或請管理者調整你的權限。',
    );
    await expect(page.getByTestId('brain-object-create-project')).toHaveCount(0);
    await page.keyboard.press('Escape');
    h.hier.projects = [proj(7, `${M}-專案七`)];
    await openPicker(page);
    await expect(page.getByTestId('brain-object-project-7')).toHaveAttribute('data-selectable', 'true');
    await expect(page.getByTestId('brain-object-create-system-7')).toHaveCount(0);
    await expect(page.getByTestId('brain-object-create-project')).toHaveCount(0);
  });

  /**
   * @purpose 建立被伺服器以 403／409 拒絕時，表單就地顯示對應文案、名稱保留、表單不收，並寫入選單內播報區（BR14.4、F-04；AC9.2.3 的畫面面）。
   * @ui / | brain-object-create-error、brain-object-picker-live
   * @given 具 K2 edit；POST /api/hierarchy/projects 先回 403、後回 409
   * @step 建立專案送出 | 顯示「你沒有建立專案的權限，請聯絡管理者」，名稱欄仍為原名稱，表單仍在
   * @step 再送出（伺服器改回 409） | 顯示「已有同名的專案，請換一個名稱」
   * @step 檢視播報 | 兩句都只出現在選單內播報區
   * @pass 文案正確、名稱保留、播報只寫選單內
   * @story US9.2
   */
  test('建立被拒時就地顯示文案且名稱保留', async ({ page }) => {
    const h = await setup(page, { hierarchy: { postProjectStatus: 403 } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-create-project').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-被拒`);
    await page.getByTestId('brain-object-create-submit').click();
    await expect(page.getByTestId('brain-object-create-error')).toHaveText('你沒有建立專案的權限，請聯絡管理者');
    await expect(page.getByTestId('brain-object-create-name')).toHaveValue(`${M}-被拒`);
    h.hier.postProjectStatus = 409;
    await page.getByTestId('brain-object-create-submit').click();
    await expect(page.getByTestId('brain-object-create-error')).toHaveText('已有同名的專案，請換一個名稱');
    await expect(page.getByTestId('brain-object-create-name')).toHaveValue(`${M}-被拒`);
    await expect(picker(page)).toBeVisible();
    const a = await announcements(page);
    const failures = a.filter((x) => x.text.includes('權限') || x.text.includes('同名'));
    expect(failures.length).toBeGreaterThanOrEqual(2);
    for (const x of failures) expect(x.src).toBe('brain-object-picker-live');
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 非擁有者的專案照列但不可選：停用、附說明、點擊不送訊框，且群組旁沒有「+ 新增系統」；自有專案可選且有入口（BR13.2、BR14.3、OPN-12）。
   * @ui / | brain-object-project-5、brain-object-not-owned-5、brain-object-item-50、brain-object-create-system-7
   * @given 專案 5（他人擁有，系統 50）與自有專案 7；具 K2 edit
   * @step 開啟選單並展開專案 5 | 專案 5 與系統 50 的 data-selectable=false、aria-disabled=true，說明「大腦目前只能以你建立的專案為作業對象」可見
   * @step 點專案 5 與系統 50 | set_work_target 0 則，選單仍開
   * @step 檢視建立入口 | 專案 5 旁沒有「+ 新增系統」，專案 7 旁有
   * @pass 停用、不送出、入口與可選性一致
   * @story US9.2
   * @note 擋的是「建立入口另寫一份方向相反的比較」（突變 M2）。
   */
  test('非擁有者專案照列但不可選且無新增系統入口', async ({ page }) => {
    const h = await setup(page, {
      hierarchy: {
        projects: [proj(5, `${M}-他人專案`, OTHER_ID), proj(7, `${M}-專案七`)],
        systems: { 5: [sys(50, 5, `${M}-他人系統`)], 7: [] },
      },
    });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-expand-5').click();
    for (const id of ['brain-object-project-5', 'brain-object-item-50']) {
      await expect(page.getByTestId(id)).toHaveAttribute('data-selectable', 'false');
      await expect(page.getByTestId(id)).toHaveAttribute('aria-disabled', 'true');
    }
    await expect(page.getByTestId('brain-object-not-owned-5')).toHaveText('大腦目前只能以你建立的專案為作業對象');
    // aria-disabled 的列 Playwright 視為不可啟用，故以 force 點擊（實際送出點擊事件）並另以鍵盤 Enter 觸發一次。
    await page.getByTestId('brain-object-project-5').click({ force: true });
    await page.getByTestId('brain-object-item-50').click({ force: true });
    await page.getByTestId('brain-object-item-50').focus();
    await page.keyboard.press('Enter');
    await expect(picker(page)).toBeVisible();
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
    await expect(page.getByTestId('brain-object-create-system-5')).toHaveCount(0);
    await expect(page.getByTestId('brain-object-create-system-7')).toBeVisible();
    await expect(page.getByTestId('brain-object-project-7')).toHaveAttribute('data-selectable', 'true');
  });

  /**
   * @purpose 專案清單失敗進 error 態且可重試；403 顯示權限文案；單一群組的系統清單失敗只影響該群組（BR12.2、F-05）。
   * @ui / | brain-object-error、brain-object-retry、brain-object-group-error-7、brain-object-group-retry-7
   * @given 專案清單先回 500；之後改回 200（專案 7、8）；專案 7 的系統清單先回 500
   * @step 開啟選單 | data-state=error、「無法載入清單」、不渲染任何群組，「+ 新增專案」仍在
   * @step 按重試 | 清單出現專案 7 與 8
   * @step 展開專案 7 | 只有該群組顯示「無法載入系統清單」與重試；專案 8 可照常展開
   * @step 按該群組的重試（伺服器改回 200） | 系統 71 出現
   * @step 專案清單改回 403 並重開 | 顯示「你沒有檢視專案的權限」
   * @pass 錯誤與空清單可區分、群組失敗不擴散、可重試
   * @story US9.2
   */
  test('清單失敗可重試且群組失敗只影響該群組', async ({ page }) => {
    const h = await setup(page, {
      hierarchy: {
        projects: [proj(7, `${M}-專案七`), proj(8, `${M}-專案八`)],
        systems: { 7: [sys(71, 7, `${M}-系統七一`)], 8: [sys(81, 8, `${M}-系統八一`)] },
        projectsStatus: 500,
        systemsStatus: { 7: 500 },
      },
    });
    await gotoReady(page);
    await openPicker(page);
    await expect(picker(page)).toHaveAttribute('data-state', 'error');
    await expect(page.getByTestId('brain-object-error')).toContainText('無法載入清單');
    await expect(page.getByTestId('brain-object-list')).toHaveCount(0);
    await expect(page.getByTestId('brain-object-create-project')).toBeVisible();
    h.hier.projectsStatus = 200;
    await page.getByTestId('brain-object-retry').click();
    await expect(picker(page)).toHaveAttribute('data-state', 'default');
    await page.getByTestId('brain-object-expand-7').click();
    await expect(page.getByTestId('brain-object-group-error-7')).toContainText('無法載入系統清單');
    await page.getByTestId('brain-object-expand-8').click();
    await expect(page.getByTestId('brain-object-item-81')).toBeVisible();
    await expect(page.getByTestId('brain-object-group-error-8')).toHaveCount(0);
    h.hier.systemsStatus = {};
    await page.getByTestId('brain-object-group-retry-7').click();
    await expect(page.getByTestId('brain-object-item-71')).toBeVisible();
    await page.keyboard.press('Escape');
    h.hier.projectsStatus = 403;
    await switchBtn(page).click();
    await expect(page.getByTestId('brain-object-error')).toHaveText('你沒有檢視專案的權限');
  });

  /**
   * @purpose 鍵盤：開啟時焦點在搜尋框；Tab／Shift+Tab 不離開選單；方向鍵在列間移動；Escape 先收表單、再關選單，焦點回到開啟它的控件（BR15.1、BR15.2、BR15.3）。
   * @ui / | brain-object-search、brain-object-project-*、brain-context-switch-object
   * @given 自有專案 7、8；具 K2 edit
   * @step 開啟選單 | 焦點在 brain-object-search，dialog 有 aria-modal=true 與可見標題「切換作業對象」
   * @step 連按 Tab 二十次 | 焦點始終在選單內
   * @step 在搜尋框按 Shift+Tab | 焦點跳到選單最後一個可聚焦控件（仍在選單內）
   * @step 聚焦專案 7 後按下方向鍵 | 焦點移到專案 8；再按下方向鍵不循環
   * @step 開「+ 新增專案」表單後按 Escape | 表單收起，焦點回「+ 新增專案」，選單仍開
   * @step 再按 Escape | 選單關閉，焦點回切換鈕
   * @pass 焦點不離開選單且每條關閉路徑都還給正確控件
   * @story US9.2
   */
  test('鍵盤焦點陷阱方向鍵與 Escape 返還焦點', async ({ page }) => {
    await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`), proj(8, `${M}-專案八`)] } });
    await gotoReady(page);
    await openPicker(page);
    await expect(page.getByTestId('brain-object-search')).toBeFocused();
    await expect(picker(page)).toHaveAttribute('aria-modal', 'true');
    await expect(page.getByRole('dialog', { name: '切換作業對象' })).toBeVisible();
    for (let i = 0; i < 20; i += 1) {
      await page.keyboard.press('Tab');
      expect(await page.evaluate(() => !!document.activeElement?.closest('[data-testid="brain-object-picker"]'))).toBe(true);
    }
    await page.getByTestId('brain-object-search').focus();
    await page.keyboard.press('Shift+Tab');
    expect(await activeTestId(page)).toBe('brain-object-create-project');
    await page.getByTestId('brain-object-project-7').focus();
    await page.keyboard.press('ArrowDown');
    expect(await activeTestId(page)).toBe('brain-object-project-8');
    await page.keyboard.press('ArrowDown');
    expect(await activeTestId(page)).toBe('brain-object-project-8');
    await page.keyboard.press('ArrowUp');
    expect(await activeTestId(page)).toBe('brain-object-project-7');
    await page.getByTestId('brain-object-create-project').click();
    await expect(page.getByTestId('brain-object-create-name')).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('brain-object-create-name')).toHaveCount(0);
    expect(await activeTestId(page)).toBe('brain-object-create-project');
    await expect(picker(page)).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(picker(page)).toHaveCount(0);
    expect(await activeTestId(page)).toBe('brain-context-switch-object');
  });

  /**
   * @purpose 子頁面上由選單發出的切換帶本頁所讀的段，伺服器回推後沿用 U14 的「作業對象已改為」提示（BR11.4、OPEN-OP16-6）。
   * @ui /workspace | 工作區脈絡列、brain-sync-notice
   * @given 工作區已切為獨立對話；自有專案 7
   * @step 在 /workspace 開啟選單並選專案 7 | set_work_target.payload 為 {projectId:'7', systemId:null, diagramId:null, segment:'workspace'}
   * @step 伺服器回推 | brain-sync-notice 出現「作業對象已改為」
   * @pass segment 為本頁所讀的段，且提示出現
   * @story US9.2
   */
  test('子頁面選取帶本頁所讀段並出現已改為提示', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`)] } });
    h.server.modes.workspace = 'isolated';
    h.server.names = { p7: `${M}-專案七` };
    await gotoReady(page, '/workspace');
    await openPicker(page);
    await page.getByTestId('brain-object-project-7').click();
    await expect.poll(() => h.server.framesOf('set_work_target').filter((f) => f.payload.projectId === '7').length).toBe(1);
    expect(h.server.framesOf('set_work_target').find((f) => f.payload.projectId === '7')?.payload).toEqual({
      projectId: '7',
      systemId: null,
      diagramId: null,
      segment: 'workspace',
    });
    await expect(page.getByTestId('brain-sync-notice')).toContainText(`作業對象已改為 ${M}-專案七`);
  });

  /**
   * @purpose 無系統歸屬的既有圖在 /workspace 照常開啟，脈絡列只顯示圖名（D-7 附帶；AC9.1.3 的既有頁面行為不變）。
   * @ui /workspace | 工作區脈絡列 brain-context-name-diagram
   * @given 作業對象只有圖 31（無專案、無系統）
   * @step 開啟 /workspace | `brain-context-name-diagram` 文字為圖名，`brain-context-name-project` 與 `brain-context-name-system` 數量為 0
   * @pass 只顯示圖名
   * @story US9.2
   * @note 非本單元 AC；functional-spec §八之四 D-7 的附帶承接。
   */
  test('無系統歸屬的圖在工作區只顯示圖名', async ({ page }) => {
    const h = await setup(page);
    h.server.shared = { pid: null, sid: null, did: '31' };
    h.server.names = { d31: `${M}-圖31` };
    await gotoReady(page, '/workspace');
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveText(`${M}-圖31`);
    await expect(page.getByTestId('brain-context-name-project')).toHaveCount(0);
    await expect(page.getByTestId('brain-context-name-system')).toHaveCount(0);
  });

  /**
   * @purpose 身分未決不得無限載入：/me 一律回 200 但不含 id 時，開啟選單只多呼叫一次 refreshMe，之後顯示身分錯誤與重試；重試再呼叫一次（OPN-04、N-01 情境 a）。
   * @ui / | brain-object-identity-error、brain-object-identity-retry
   * @given /api/auth/me 一律回 200、權限齊全、但主體不含 id
   * @step 開啟選單 | /me 只多 1 次，data-state=error，出現「無法確認你的身分，請重新整理頁面」，不發 /api/hierarchy 請求
   * @step 按重試 | /me 再多 1 次，仍為身分錯誤，之後不再增加
   * @pass 補呼叫恰 1 次、重試恰 1 次、不無限載入
   * @story US9.2
   * @note 不得讓第一次 /me 回 500：權限會變空、路由守衛把使用者導走，選單根本不渲染（N-01）。擋突變 M14。
   */
  test('身分未決時只補呼叫一次 refreshMe（缺 id）', async ({ page }) => {
    await identityScenario(page, ['no-id']);
  });

  /**
   * @purpose 身分未決且 refreshMe 拋錯時同樣只補呼叫一次並顯示身分錯誤與重試（OPN-04、N-01 情境 b）。
   * @ui / | brain-object-identity-error、brain-object-identity-retry
   * @given /api/auth/me 第一次回 200 不含 id（權限齊全），之後回 500
   * @step 開啟選單 | /me 只多 1 次，data-state=error，出現「無法確認你的身分，請重新整理頁面」，不發 /api/hierarchy 請求
   * @step 按重試 | /me 再多 1 次，仍為身分錯誤，之後不再增加
   * @pass 拋錯被接住、不無限載入
   * @story US9.2
   */
  test('身分未決時只補呼叫一次 refreshMe（refreshMe 失敗）', async ({ page }) => {
    await identityScenario(page, ['no-id', 'fail']);
  });

  /**
   * @purpose 請求數有常數上界：30 個專案時開啟只發 2 個請求（專案清單＋目前所在專案），搜尋第一次輸入才補抓其餘 29 個、同時最多 4 個，之後輸入不再發請求（OPN-01、OPN-06、N-02）。
   * @ui / | brain-object-search、brain-object-backfill-status、brain-object-item-200
   * @given 30 個自有專案（1–30），每個各一個系統；作業對象為專案 7 的系統 70；系統清單回應延遲 100ms
   * @step 開啟選單 | /api/hierarchy 請求 2 次，專案 7 展開且系統 70 標「目前」
   * @step 收起再展開專案 7 | 請求仍為 2
   * @step 連續輸入兩個字 | 補抓只在第一個字觸發，完成後總請求為 31，同時在途的系統請求最多 4 個
   * @step 輸入專案 20 底下系統的名稱 | 系統 200 可見且其群組自動展開
   * @step 再輸入 10 個字元 | 總請求仍為 31
   * @pass 開啟 2、補抓後 31、之後恆為 31，並行上限 4
   * @story US9.2
   * @note 並行上限斷言擋的是「拿掉 backfillStarted、每次輸入都另起佇列」（突變 M13）：登記簿讓請求數不增，但並行數會超過 4。
   */
  test('三十個專案時請求數有上界且搜尋只補抓一次', async ({ page }) => {
    const projects = Array.from({ length: 30 }, (_, i) => proj(i + 1, `${M}-專案${String(i + 1).padStart(2, '0')}`));
    const systems: Record<number, SystemStub[]> = {};
    for (const p of projects) systems[p.id] = [sys(p.id * 10, p.id, `${M}-sys-${p.id * 10}-x`)];
    const h = await setup(page, { hierarchy: { projects, systems, systemsGate: () => sleep(100) } });
    h.server.shared = { pid: '7', sid: '70', did: null };
    h.server.names = { p7: `${M}-專案07`, s70: `${M}-sys-70-x` };
    await gotoReady(page);
    await openPicker(page);
    await expect(page.getByTestId('brain-object-item-70')).toHaveAttribute('aria-current', 'true');
    expect(h.hier.log).toEqual([getProjects, getSystems(7)]);
    await page.getByTestId('brain-object-expand-7').click();
    await page.getByTestId('brain-object-expand-7').click();
    await expect(page.getByTestId('brain-object-item-70')).toBeVisible();
    expect(h.hier.log).toHaveLength(2);

    // 兩個字連續輸入：第二個字落在補抓進行中，只有第一個字可以起補抓（並行上限斷言的前提）。
    await page.getByTestId('brain-object-search').pressSequentially('sy');
    await expect(page.getByTestId('brain-object-backfill-status')).toHaveCount(0, { timeout: 15_000 });
    expect(h.hier.log).toHaveLength(31);
    expect(h.hier.maxInFlightSystems).toBeLessThanOrEqual(4);
    await page.getByTestId('brain-object-search').fill('');
    await page.getByTestId('brain-object-search').pressSequentially('sys-200');
    await expect(page.getByTestId('brain-object-item-200')).toBeVisible();
    await expect(page.getByTestId('brain-object-expand-20')).toHaveAttribute('aria-expanded', 'true');
    await page.getByTestId('brain-object-search').pressSequentially('abcdefghij');
    await expect(picker(page)).toHaveAttribute('data-state', 'no-match');
    expect(h.hier.log).toHaveLength(31);
    expect(h.hier.maxInFlightSystems).toBeLessThanOrEqual(4);
  });

  /**
   * @purpose 補抓中單一群組失敗只讓該群組顯示錯誤與重試，其他群組照常命中（N-02 第 3 點、F-05）。
   * @ui / | brain-object-group-error-12、brain-object-item-30
   * @given 自有專案 1–5、12；專案 12 的系統清單回 500；專案 3 有系統 30「target-hit」
   * @step 開啟選單並輸入「target」 | 系統 30 可見、群組 12 顯示「無法載入系統清單」與重試，data-state 不是 error
   * @pass 失敗不擴散
   * @story US9.2
   */
  test('補抓時單一群組失敗不影響其他命中', async ({ page }) => {
    const projects = [1, 2, 3, 4, 5, 12].map((id) => proj(id, `${M}-p${id}`));
    const systems: Record<number, SystemStub[]> = { 3: [sys(30, 3, `${M}-target-hit`)] };
    const h = await setup(page, { hierarchy: { projects, systems, systemsStatus: { 12: 500 } } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-search').pressSequentially('target');
    await expect(page.getByTestId('brain-object-item-30')).toBeVisible();
    await expect(page.getByTestId('brain-object-group-error-12')).toContainText('無法載入系統清單');
    await expect(page.getByTestId('brain-object-group-retry-12')).toBeVisible();
    await expect(picker(page)).not.toHaveAttribute('data-state', 'error');
    expect(count(h.hier, getSystems(12))).toBe(1);
  });

  /**
   * @purpose 補抓佇列中尚未發出的群組被展開時，該群組的系統清單只被抓一次（D-01：冪等登記簿為同步 ref，佇列工作在執行時才檢查）。
   * @ui / | brain-object-expand-10
   * @given 自有專案 1–12；專案 1–4 的系統清單回應被擋住直到放行（使 5 以後留在佇列）
   * @step 開啟選單並輸入一個字 | 專案 1–4 的系統請求在途，其餘在佇列
   * @step 按專案 10 的展開鈕 | 專案 10 的系統請求立即發出
   * @step 放行並等補抓結束 | 專案 10 的系統請求總數恰 1，每個專案至多 1
   * @pass 展開與補抓的競態不造成重複請求
   * @story US9.2
   * @note 擋的是「ensureSystems 改讀 state 的 idle」（突變 M12）：佇列工作閉包住入列當下的 state，會再抓一次。
   */
  test('補抓佇列中展開同一群組只抓一次', async ({ page }) => {
    const projects = Array.from({ length: 12 }, (_, i) => proj(i + 1, `${M}-q${i + 1}`));
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const h = await setup(page, {
      hierarchy: { projects, systemsGate: (pid) => (pid <= 4 ? gate : undefined) },
    });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-search').pressSequentially('q');
    await expect.poll(() => h.hier.log.filter((l) => l.endsWith('/systems')).length).toBe(4);
    await page.getByTestId('brain-object-search').fill('');
    await page.getByTestId('brain-object-expand-10').click();
    await expect.poll(() => count(h.hier, getSystems(10))).toBe(1);
    release();
    await expect(page.getByTestId('brain-object-backfill-status')).toHaveCount(0);
    await page.waitForTimeout(300);
    expect(count(h.hier, getSystems(10))).toBe(1);
    for (const p of projects) expect(count(h.hier, getSystems(p.id))).toBeLessThanOrEqual(1);
  });

  /**
   * @purpose 選單關閉期間不發出任何新的 /api/hierarchy 請求，再開啟是一次全新的掛載、只發自己的一個專案清單請求並呈現它的回應（一次開啟＝一次掛載）。
   * @ui / | brain-object-picker
   * @given 第一次專案清單延遲 2 秒並回「舊名稱」；第二次即時回「新名稱」
   * @step 開啟選單後立即按 Escape 關閉 | 關閉期間 /api/hierarchy 請求數不增加（仍為 1）
   * @step 立刻再開啟 | 清單出現「新名稱」，請求總數為 2
   * @step 等 3 秒（第一次的晚到回應已抵達） | 清單仍為「新名稱」，請求總數仍為 2
   * @pass 關閉期間零新請求、再開只有一個新請求
   * @story US9.2
   * @note **本案不能證明「晚到結果被丟棄」**（review-01 R-03）：元件卸載後 React 不會把 setState 渲染出來，移除 mountedRef／cancelled 守衛本案仍綠，「舊名稱從未出現」的斷言因此只是附帶觀察、不是證據。OPN-02 的守衛由程式碼審查承載；BR12.4 的「關閉即取消補抓」證據是「補抓進行中關閉後不再發出系統請求」。不以主控台警告判定：React 19 已移除卸載後更新的警告，那同樣恆真。
   */
  test('關閉後晚到的舊回應永不出現', async ({ page }) => {
    const h = await setup(page, {
      hierarchy: {
        projectsHook: async (call) => {
          if (call === 0) {
            await sleep(2000);
            return [proj(1, `${M}-舊名稱`)];
          }
          return [proj(1, `${M}-新名稱`)];
        },
      },
    });
    await page.addInitScript((marker) => {
      const w = window as unknown as { __sawOld: boolean };
      w.__sawOld = false;
      const watch = new MutationObserver(() => {
        if (document.body && document.body.textContent?.includes(marker)) w.__sawOld = true;
      });
      document.addEventListener('DOMContentLoaded', () => watch.observe(document.body, { subtree: true, childList: true, characterData: true }));
    }, `${M}-舊名稱`);
    await gotoReady(page);
    await switchBtn(page).click();
    await expect.poll(() => h.hier.log.length).toBe(1);
    await page.keyboard.press('Escape');
    await expect(picker(page)).toHaveCount(0);
    await page.waitForTimeout(200);
    expect(h.hier.log).toHaveLength(1);
    await switchBtn(page).click();
    await expect(page.getByTestId('brain-object-project-1')).toHaveText(`${M}-新名稱`);
    await page.waitForTimeout(3000);
    await expect(page.getByTestId('brain-object-project-1')).toHaveText(`${M}-新名稱`);
    expect(await page.evaluate(() => (window as unknown as { __sawOld: boolean }).__sawOld)).toBe(false);
    expect(h.hier.log).toEqual([getProjects, getProjects]);
  });

  /**
   * @purpose 同一個 JS 任務內連續兩次送出只發一個建立請求（OPN-03、D-02；objectCreateAction 非冪等，擋重複觸發是呼叫端責任）。
   * @ui / | brain-object-create-submit、brain-object-create-form-project
   * @given 具 K2 edit；POST 延遲 1 秒
   * @step 在同一任務內對送出鈕呼叫兩次 click() | POST /api/hierarchy/projects 恰 1 次
   * @step 重開選單、在同一任務內呼叫兩次 form.requestSubmit() | POST 總數為 2（每案各 1）
   * @pass 每次送出恰一個請求
   * @story US9.2
   * @note 必須在同一任務內觸發：分開的兩次點擊之間 React 已更新停用狀態，會讓只靠 state 的實作也通過（突變 M9）。
   */
  test('同一任務內連續送出只發一個建立請求', async ({ page }) => {
    const h = await setup(page, { hierarchy: { postDelayMs: 1000 } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-create-project').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-連點`);
    await page.getByTestId('brain-object-create-submit').evaluate((el) => {
      (el as HTMLButtonElement).click();
      (el as HTMLButtonElement).click();
    });
    await expect(picker(page)).toHaveCount(0, { timeout: 5000 });
    expect(count(h.hier, 'POST /api/hierarchy/projects')).toBe(1);

    await openPicker(page);
    await page.getByTestId('brain-object-create-project').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-雙送`);
    await page.getByTestId('brain-object-create-form-project').evaluate((form) => {
      (form as HTMLFormElement).requestSubmit();
      (form as HTMLFormElement).requestSubmit();
    });
    await expect(picker(page)).toHaveCount(0, { timeout: 5000 });
    expect(count(h.hier, 'POST /api/hierarchy/projects')).toBe(2);
  });

  /**
   * @purpose 選單開啟中連線離開 ready：選單同一次更新內關閉、焦點移到脈絡列、頁面播報一次；重連後選單不會自己出現；連續兩次斷線各播報一次（OPN-05、F-02、D-05）。
   * @ui / | brain-context-bar、live-region
   * @given 自有專案 7；假大腦可由伺服器端關閉連線並接受重連
   * @step 開啟選單後伺服器以 1011 關閉連線 | 選單不存在，焦點在 brain-context-bar，頁面 live-region 出現「連線中斷，已關閉作業對象選單」恰 1 次
   * @step 等重連完成（切換鈕再出現） | 選單不存在，set_work_target 0 則
   * @step 再開選單並再斷線一次 | 該播報累計 2 次
   * @pass 斷線即關、焦點不落到 body、重連不復現、每次斷線都播報
   * @story US9.2
   * @note 擋的是「斷線時不清 pickerOpen」（突變 M11）與「斷線時不移焦點或不播報」（突變 M16）。
   */
  test('斷線時選單關閉焦點移到脈絡列且重連不復現', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`)] } });
    await gotoReady(page);
    await openPicker(page);
    void h.server.last.ws.close({ code: 1011 });
    await expect(picker(page)).toHaveCount(0);
    await expect.poll(() => activeTestId(page)).toBe('brain-context-bar');
    const lost = '連線中斷，已關閉作業對象選單';
    await expect.poll(async () => (await announcements(page)).filter((a) => a.text === lost)).toEqual([{ src: 'live-region', text: lost }]);
    await expect(switchBtn(page)).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(300);
    await expect(picker(page)).toHaveCount(0);
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);

    await openPicker(page);
    void h.server.last.ws.close({ code: 1011 });
    await expect(picker(page)).toHaveCount(0);
    await expect.poll(async () => (await announcements(page)).filter((a) => a.text === lost).length).toBe(2);
  });

  /**
   * @purpose 惡意名稱以純文字呈現，不被當成 HTML 解析（OPN-13）。
   * @ui / | brain-object-project-3
   * @given 自有專案 3 的名稱為 `<img src=x onerror="window.__xss=1">`
   * @step 開啟選單 | `brain-object-project-3` 的文字為該字串原文
   * @step 檢查 `window.__xss` | 為 `undefined`（不得被設為 1）
   * @pass 名稱未被解析成 HTML
   * @story US9.2
   * @note 擋的是「改用 dangerouslySetInnerHTML」（突變 M3，lint 亦擋）。
   */
  test('惡意名稱以純文字呈現', async ({ page }) => {
    const evil = '<img src=x onerror="window.__xss=1">';
    await setup(page, { hierarchy: { projects: [proj(3, evil)] } });
    await gotoReady(page);
    await openPicker(page);
    await expect(page.getByTestId('brain-object-project-3')).toHaveText(evil);
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => (window as unknown as { __xss?: number }).__xss)).toBeUndefined();
  });

  /**
   * @purpose 搜尋輸入正規表示式特殊字元不拋例外、畫面不崩潰（OPN-14）。
   * @ui / | brain-object-search、brain-object-no-match
   * @given 自有專案 1「abc」
   * @step 分別輸入 `(`、`[`、`\` | 每次都出現「沒有符合的對象」，頁面沒有未捕捉例外
   * @pass 三個字元皆安全
   * @story US9.2
   * @note 擋的是「改用 new RegExp(query)」（突變 M4，lint 亦擋）。
   */
  test('搜尋特殊字元不拋例外', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await setup(page, { hierarchy: { projects: [proj(1, 'abc')], systems: { 1: [] } } });
    await gotoReady(page);
    await openPicker(page);
    for (const ch of ['(', '[', '\\']) {
      await page.getByTestId('brain-object-search').fill(ch);
      await expect(page.getByTestId('brain-object-no-match')).toHaveText('沒有符合的對象');
    }
    expect(errors).toEqual([]);
  });

  /**
   * @purpose 全形字搜尋可命中半形名稱（NFKC 正規化）。
   * @ui / | brain-object-search、brain-object-project-1
   * @given 自有專案 1「abc-tools」
   * @step 輸入全形「ＡＢＣ」 | 專案 1 仍顯示，data-state 不是 no-match
   * @pass 全形與半形視為相同
   * @story US9.2
   * @note 擋的是「normalize 拿掉 NFKC」（突變 M15）。
   */
  test('全形搜尋命中半形名稱', async ({ page }) => {
    await setup(page, { hierarchy: { projects: [proj(1, 'abc-tools')], systems: { 1: [] } } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-search').fill('ＡＢＣ');
    await expect(page.getByTestId('brain-object-project-1')).toBeVisible();
    await expect(picker(page)).toHaveAttribute('data-state', 'default');
  });

  /**
   * @purpose 選單一輪操作期間不產生任何主控台訊息、不改變瀏覽器儲存的鍵集合，請求網址不帶查詢字串（OPN-15、N-03）。
   * @ui / | brain-object-picker
   * @given 自有專案 1（系統 10）；具 K2 edit
   * @step 記錄開啟前的主控台訊息數與兩種儲存的鍵集合 | 基準
   * @step 開啟、搜尋、建立一個專案 | 期間新增的主控台訊息 0 則
   * @step 比對儲存鍵集合 | 與基準相同
   * @step 檢查 /api/hierarchy 請求 | 網址皆不含「?」
   * @pass 零主控台、零儲存、token 不進網址
   * @story US9.2
   * @note 不比對名稱字串：console.log(groups) 的文字不含名稱，會是恆綠（N-03）；擋突變 M5／M6。
   */
  test('選單一輪不輸出主控台且不寫儲存', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(1, `${M}-p1`)], systems: { 1: [sys(10, 1, `${M}-s10`)] } } });
    const consoleMessages: string[] = [];
    page.on('console', (msg) => consoleMessages.push(msg.text()));
    await gotoReady(page);
    await page.waitForLoadState('networkidle');
    const keys = () =>
      page.evaluate(() => ({
        local: Object.keys(localStorage).sort(),
        session: Object.keys(sessionStorage).sort(),
      }));
    const baselineKeys = await keys();
    const baselineConsole = consoleMessages.length;
    await openPicker(page);
    await page.getByTestId('brain-object-search').pressSequentially('s10');
    await expect(page.getByTestId('brain-object-item-10')).toBeVisible();
    await page.getByTestId('brain-object-search').fill('');
    await page.getByTestId('brain-object-create-project').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-新`);
    await page.getByTestId('brain-object-create-submit').click();
    await expect(picker(page)).toHaveCount(0);
    expect(consoleMessages.slice(baselineConsole)).toEqual([]);
    expect(await keys()).toEqual(baselineKeys);
    for (const l of h.hier.log) expect(l).not.toContain('?');
  });

  /**
   * @purpose 在入口頁、/workspace、/assessment 三處完成「換作業對象」與「建立並切過去」都不發生頁面切換（NFR11.160）。
   * @ui / | 入口頁
   * @ui /workspace | 工作區
   * @ui /assessment | 評核頁
   * @given 自有專案 7；具 K2 edit
   * @step 在每一頁開啟選單並選專案 7 | 主框架 pathname 變更 0 次
   * @step 在每一頁開啟選單並建立專案 | 主框架 pathname 變更 0 次
   * @pass 三頁 × 兩情境的頁面切換皆為 0
   * @story US9.2
   */
  test('三個頁面內換對象與建立都不切頁', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`)] } });
    for (const path of ['/', '/workspace', '/assessment']) {
      await gotoReady(page, path);
      const navs: string[] = [];
      const onNav = (frame: import('@playwright/test').Frame) => {
        if (frame === page.mainFrame()) navs.push(new URL(frame.url()).pathname);
      };
      page.on('framenavigated', onNav);
      await openPicker(page);
      await page.getByTestId('brain-object-project-7').click();
      await expect(picker(page)).toHaveCount(0);
      await openPicker(page);
      await page.getByTestId('brain-object-create-project').click();
      await page.getByTestId('brain-object-create-name').fill(`${M}-${path}-新`);
      await page.getByTestId('brain-object-create-submit').click();
      await expect(picker(page)).toHaveCount(0);
      page.off('framenavigated', onNav);
      expect(navs, `${path} 發生頁面切換`).toEqual([]);
      expect(new URL(page.url()).pathname).toBe(path);
    }
    expect(h.server.framesOf('set_work_target').length).toBeGreaterThanOrEqual(6);
  });

  /**
   * @purpose 建立者在選單開啟後被移出專案時，建立系統回 404 顯示「其他」文案、名稱保留、表單不收、不崩潰（OPN-16、N-04；文案是否可接受為關卡事項 G-6）。
   * @ui / | brain-object-create-system-7、brain-object-create-error
   * @given 自有專案 7；POST /api/hierarchy/projects/7/systems 回 404
   * @step 在專案 7 旁建立系統 | 顯示「建立系統失敗，請稍後再試」，名稱仍在欄位內
   * @pass 404 被呈現為其他錯誤且不崩潰
   * @story US9.2
   */
  test('建立系統回 404 顯示其他錯誤文案', async ({ page }) => {
    await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`)], postSystemStatus: 404 } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-create-system-7').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-系統`);
    await page.getByTestId('brain-object-create-submit').click();
    await expect(page.getByTestId('brain-object-create-error')).toHaveText('建立系統失敗，請稍後再試');
    await expect(page.getByTestId('brain-object-create-name')).toHaveValue(`${M}-系統`);
    await expect(picker(page)).toBeVisible();
  });

  /**
   * @purpose setWorkTarget 回 false 時選單不關、就地顯示切換失敗並寫選單內播報；建立成功但切不過去時提示「已建立，但目前無法切換」且不重抓清單（BR11.2、BR14.5、D-03）。
   * @ui / | brain-object-switch-error、brain-object-picker-live
   * @given 自有專案 7；開啟選單後讓 WebSocket 的 readyState 讀成 CLOSED（連線狀態仍為 ready）
   * @step 點專案 7 | 選單仍開，顯示「目前無法切換：與大腦的連線中斷」，選單內播報區出現同一句
   * @step 建立專案 | 顯示「已建立，但目前無法切換」，專案清單請求數不變
   * @pass 失敗就地呈現、不重抓
   * @story US9.2
   */
  test('切換送不出時就地顯示且不重抓清單', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`)] } });
    await gotoReady(page);
    await openPicker(page);
    await breakSocketSend(page);
    await page.getByTestId('brain-object-project-7').click();
    await expect(picker(page)).toBeVisible();
    await expect(page.getByTestId('brain-object-switch-error')).toHaveText('目前無法切換：與大腦的連線中斷');
    await expect(page.getByTestId('brain-object-picker-live')).toHaveText('目前無法切換：與大腦的連線中斷');
    const before = count(h.hier, getProjects);
    await page.getByTestId('brain-object-create-project').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-切不過去`);
    await page.getByTestId('brain-object-create-submit').click();
    await expect(page.getByTestId('brain-object-switch-error')).toHaveText('已建立，但目前無法切換');
    await page.waitForTimeout(300);
    expect(count(h.hier, getProjects)).toBe(before);
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 使用者在專案清單回來之前就輸入只存在於系統名的字串，清單一回來即補抓並命中，不需要再多打一個字；補抓期間不顯示「沒有符合的對象」（N-02 第 3 點；review-01 R-01）。
   * @ui / | brain-object-search、brain-object-item-50、brain-object-no-match
   * @given 自有專案 1–6，名稱都不含「zeta」；只有專案 5 的系統 50 叫「zeta-only」；作業對象未選定；專案清單回應被擋住直到放行
   * @step 開啟選單，在 data-state=loading 時於搜尋框輸入「zeta」 | /api/hierarchy 只有 1 個專案清單請求，沒有任何系統請求
   * @step 放行專案清單，不再做任何輸入 | 系統 50 可見、其群組展開；六個專案的系統各被請求 1 次
   * @step 檢視 data-state | 不是 no-match
   * @pass 清單回來後自行補抓並命中
   * @story US9.2
   * @note 擋的是「補抓只掛在輸入事件上」（突變 M17：刪除專案清單 .then 內的補抓觸發）——那時清單回來後沒有任何補抓，畫面顯示「沒有符合的對象」。
   */
  test('清單載入前輸入的搜尋在清單回來後即補抓', async ({ page }) => {
    const projects = [1, 2, 3, 4, 5, 6].map((id) => proj(id, `${M}-r${id}`));
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const h = await setup(page, {
      hierarchy: {
        projects,
        systems: { 5: [sys(50, 5, `${M}-zeta-only`)] },
        projectsHook: async () => {
          await gate;
        },
      },
    });
    await gotoReady(page);
    await switchBtn(page).click();
    await expect(picker(page)).toHaveAttribute('data-state', 'loading');
    await expect.poll(() => h.hier.log).toEqual([getProjects]);
    await page.getByTestId('brain-object-search').pressSequentially('zeta');
    await expect(picker(page)).toHaveAttribute('data-state', 'loading');
    expect(h.hier.log).toEqual([getProjects]);
    release();
    await expect(page.getByTestId('brain-object-item-50')).toBeVisible();
    await expect(page.getByTestId('brain-object-expand-5')).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByTestId('brain-object-backfill-status')).toHaveCount(0);
    await expect(picker(page)).toHaveAttribute('data-state', 'default');
    for (const p of projects) expect(count(h.hier, getSystems(p.id))).toBe(1);
  });

  /**
   * @purpose 補抓進行中關閉選單即取消佇列：尚未發出的系統請求永不發出（BR12.4、OPN-24；review-01 R-02）。
   * @ui / | brain-object-search、brain-object-picker
   * @given 自有專案 1–12；專案 1–4 的系統清單回應被擋住直到放行（使 5–12 留在佇列）
   * @step 開啟選單並輸入一個字 | 系統請求在途 4 個
   * @step 按 Escape 關閉 | 選單不存在
   * @step 放行在途的 4 個請求並等 800ms | 系統請求總數仍為 4，專案 5–12 一個都沒有被請求
   * @pass 關閉後佇列不再發出請求
   * @story US9.2
   * @note 擋的是「卸載時不取消佇列」（突變 M18：刪除 holder.queue?.cancel()）——那時放行後佇列繼續補發其餘 8 個。
   */
  test('補抓進行中關閉後不再發出系統請求', async ({ page }) => {
    const projects = Array.from({ length: 12 }, (_, i) => proj(i + 1, `${M}-c${i + 1}`));
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const h = await setup(page, { hierarchy: { projects, systemsGate: () => gate } });
    const systemsCount = () => h.hier.log.filter((l) => l.endsWith('/systems')).length;
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-search').pressSequentially('c');
    await expect.poll(systemsCount).toBe(4);
    await page.keyboard.press('Escape');
    await expect(picker(page)).toHaveCount(0);
    release();
    await page.waitForTimeout(800);
    expect(systemsCount()).toBe(4);
    for (let id = 5; id <= 12; id += 1) expect(count(h.hier, getSystems(id))).toBe(0);
  });

  /**
   * @purpose 點選單外的頁面區域等同取消：選單關閉，焦點落在仍在文件內的節點（不留在已卸載的選單節點），之後鍵盤仍可操作（F-06；review-01 R-02）。
   * @ui / | brain-object-picker、brain-context-switch-object
   * @given 自有專案 7
   * @step 開啟選單 | 焦點在 `brain-object-search`
   * @step 以滑鼠點視窗左下角 (8, 高度−8) 的頁面區域（選單與切換鈕之外） | `brain-object-picker` 數量為 0、切換鈕 `aria-expanded="false"`
   * @step 檢視 document.activeElement | `{ exists: true, connected: true, inPicker: false }`
   * @pass 點外部即關閉且焦點未懸空
   * @story US9.2
   * @note 擋的是「刪除點選單外的 mousedown 監聽」（突變 M19）——那時點外部選單仍開。
   */
  test('點選單外關閉且焦點不留在已卸載節點', async ({ page }) => {
    await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`)] } });
    await gotoReady(page);
    await openPicker(page);
    await expect(page.getByTestId('brain-object-search')).toBeFocused();
    const vp = page.viewportSize() ?? { width: 1280, height: 720 };
    await page.mouse.click(8, vp.height - 8);
    await expect(picker(page)).toHaveCount(0);
    await expect(switchBtn(page)).toHaveAttribute('aria-expanded', 'false');
    const focus = await page.evaluate(() => {
      const el = document.activeElement;
      return { exists: el !== null, connected: el?.isConnected ?? false, inPicker: !!el?.closest('[data-testid="brain-object-picker"]') };
    });
    expect(focus).toEqual({ exists: true, connected: true, inPicker: false });
  });

  /**
   * @purpose 點到選單內的非控件區域（標題）之後，Escape 仍關閉選單、Tab 仍不離開選單（BR15.2；review-01 R-04）。
   * @ui / | brain-object-picker、brain-context-switch-object
   * @given 自有專案 7、8
   * @step 開啟選單並點標題「切換作業對象」 | activeElement 的 data-testid 為 `brain-object-picker`（不是 `brain-context-bar`）
   * @step 按 Tab | activeElement 為 `brain-object-search`
   * @step 再點標題後按 Escape | `brain-object-picker` 數量為 0，activeElement 為 `brain-context-switch-object`
   * @pass 點非控件區域不讓鍵盤處理失效
   * @story US9.2
   * @note 擋的是「dialog 根節點不可聚焦」（突變 M20：拿掉根節點 tabIndex 與 mousedown 收回焦點）——那時焦點落到脈絡列 section，Escape 不經過選單。
   */
  test('點選單標題後按 Escape 仍關閉', async ({ page }) => {
    await setup(page, { hierarchy: { projects: [proj(7, `${M}-專案七`), proj(8, `${M}-專案八`)] } });
    await gotoReady(page);
    await openPicker(page);
    const heading = page.getByRole('heading', { name: '切換作業對象' });
    await heading.click();
    expect(await activeTestId(page)).toBe('brain-object-picker');
    await page.keyboard.press('Tab');
    expect(await activeTestId(page)).toBe('brain-object-search');
    await heading.click();
    await page.keyboard.press('Escape');
    await expect(picker(page)).toHaveCount(0);
    expect(await activeTestId(page)).toBe('brain-context-switch-object');
  });

  /**
   * @purpose 選單座標只在點擊時量測一次：開啟後視窗尺寸改變、或脈絡列所在的捲動容器捲動使切換鈕移位時，選單關閉而不是與脈絡列脫離（review-01 R-05）；選單自身的捲動不關閉。
   * @ui / | brain-object-picker、brain-context-switch-object
   * @given 自有專案 1–40（使選單內容可捲動）；脈絡列所在的捲動容器被加高到可捲動
   * @step 開啟選單並把選單自身的 scrollTop 設為 200 | 選單 scrollTop > 0，200ms 後 `brain-object-picker` 仍可見
   * @step 視窗只改高度：1280×720 改為 1280×500（模擬虛擬鍵盤升起） | 200ms 後 `brain-object-picker` 仍可見
   * @step 視窗改寬度：1280×500 改為 1100×500 | `brain-object-picker` 數量為 0
   * @step 重新開啟選單並把脈絡列所在的捲動容器向下捲 200px | 容器 scrollTop > 0，`brain-object-picker` 數量為 0
   * @pass 寬度或錨點改變即關閉；只改高度與選單內捲動不關閉
   * @story US9.2
   * @note 擋的是「刪除 resize 監聽」（突變 M21a）、「刪除捲動監聽」（突變 M21b）與「resize 仍比對高度」（突變 M21c，review-02 R-09）。
   */
  test('開啟後視窗縮放或錨點捲動即關閉選單', async ({ page }) => {
    const projects = Array.from({ length: 40 }, (_, i) => proj(i + 1, `${M}-w${i + 1}`));
    await setup(page, { hierarchy: { projects } });
    await page.setViewportSize({ width: 1280, height: 720 });
    await gotoReady(page);
    await openPicker(page);
    const menuScrolled = await picker(page).evaluate((el) => {
      el.scrollTop = 200;
      return el.scrollTop;
    });
    expect(menuScrolled).toBeGreaterThan(0);
    await page.waitForTimeout(200);
    await expect(picker(page)).toBeVisible();
    await page.setViewportSize({ width: 1280, height: 500 });
    await page.waitForTimeout(200);
    await expect(picker(page)).toBeVisible();
    await page.setViewportSize({ width: 1100, height: 500 });
    await expect(picker(page)).toHaveCount(0);

    await openPicker(page);
    const scrolled = await page.getByTestId('brain-context-bar').evaluate((bar) => {
      // 由內而外找第一個「加高後真的能捲」的祖先（overflow-y 為 auto／scroll），捲它；找不到即回 false 使本案紅燈。
      for (let el = bar.parentElement; el; el = el.parentElement) {
        const oy = getComputedStyle(el).overflowY;
        if (oy !== 'auto' && oy !== 'scroll') continue;
        const spacer = document.createElement('div');
        spacer.style.height = '3000px';
        spacer.style.flexShrink = '0';
        el.appendChild(spacer);
        el.scrollTop = 200;
        if (el.scrollTop > 0) return true;
        spacer.remove();
      }
      return false;
    });
    expect(scrolled).toBe(true);
    await expect(picker(page)).toHaveCount(0);
  });

  /**
   * @purpose 同一種建立錯誤連續發生兩次時，選單內播報區兩次都播報（相同文案的第二次以零寬空白造成一次內容變更；F-04、BR14.4；review-01 R-06、review-02 R-09）。
   * @ui / | brain-object-create-error、brain-object-picker-live
   * @given 具 K2 edit；清單為空；POST /api/hierarchy/projects 一律回 409
   * @step 建立專案送出 | 顯示「已有同名的專案，請換一個名稱」，選單內播報區播報 1 次
   * @step 不改名稱再送出一次 | 播報區對同一句累計播報 2 次
   * @pass 相同的失敗文案第二次仍被播報
   * @story US9.2
   * @note 擋的是「相同文案第二次寫入不造成內容變更」——第二次的文字與第一次相同時播報區不變、不重唸。播報比對前去掉零寬空白（review-02 R-09 起的重唸機制）。
   */
  test('連續兩次同樣的建立失敗都被播報', async ({ page }) => {
    const h = await setup(page, { hierarchy: { postProjectStatus: 409 } });
    await gotoReady(page);
    await openPicker(page);
    await page.getByTestId('brain-object-create-project').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-同名`);
    const dup = '已有同名的專案，請換一個名稱';
    const dupAnnouncements = async () =>
      (await announcements(page)).filter((a) => stripMark(a.text) === dup && a.src === 'brain-object-picker-live').length;
    await page.getByTestId('brain-object-create-submit').click();
    await expect(page.getByTestId('brain-object-create-error')).toHaveText(dup);
    await expect.poll(dupAnnouncements).toBe(1);
    await expect(page.getByTestId('brain-object-create-submit')).toBeEnabled();
    await page.getByTestId('brain-object-create-submit').click();
    await expect.poll(() => count(h.hier, 'POST /api/hierarchy/projects')).toBe(2);
    await expect.poll(dupAnnouncements).toBe(2);
    await expect(page.getByTestId('brain-object-create-error')).toHaveText(dup);
  });

  /**
   * @purpose 重試建立時選單內播報區不得在兩次失敗之間退回清單狀態文字：螢幕報讀器使用者每次重試只聽到錯誤，不會多聽到一句與建立無關的「已載入 N 個專案」；同一句錯誤仍兩次都播報（F-04、BR14.4；review-02 R-09——舊實作每輪送出先清空失敗文案，播報區因此先唸清單狀態再唸錯誤）。
   * @ui / | brain-object-create-error、brain-object-picker-live
   * @given 具 K2 edit；清單有 1 個自有專案；POST /api/hierarchy/projects 一律回 409；選單內播報區的每次內容變更被記錄
   * @step 開啟選單並開啟建立專案表單 | 選單內播報區為「已載入 1 個專案」
   * @step 送出 | 顯示「已有同名的專案，請換一個名稱」
   * @step 不改名稱再送出一次 | 送出 2 次 POST；自第一次送出起，播報區沒有任何一次內容含「已載入」，且（去掉零寬空白後）等於該錯誤的播報恰 2 次
   * @pass 重試之間不播報清單狀態，相同錯誤仍各播報一次
   * @story US9.2
   */
  test('重試建立時播報區不在兩次失敗之間退回清單狀態', async ({ page }) => {
    const h = await setup(page, { hierarchy: { projects: [proj(7, `${M}-r9-專案七`)], postProjectStatus: 409 } });
    await gotoReady(page);
    await openPicker(page);
    const live = page.getByTestId('brain-object-picker-live');
    await expect(live).toHaveText('已載入 1 個專案');
    await page.getByTestId('brain-object-create-project').click();
    await page.getByTestId('brain-object-create-name').fill(`${M}-r9-同名`);
    const dup = '已有同名的專案，請換一個名稱';
    const before = (await announcements(page)).length;
    const since = async () =>
      (await announcements(page)).slice(before).filter((a) => a.src === 'brain-object-picker-live');
    await page.getByTestId('brain-object-create-submit').click();
    await expect(page.getByTestId('brain-object-create-error')).toHaveText(dup);
    await expect(page.getByTestId('brain-object-create-submit')).toBeEnabled();
    await page.getByTestId('brain-object-create-submit').click();
    await expect.poll(() => count(h.hier, 'POST /api/hierarchy/projects')).toBe(2);
    await expect.poll(async () => (await since()).filter((a) => stripMark(a.text) === dup).length).toBe(2);
    expect((await since()).filter((a) => a.text.includes('已載入'))).toEqual([]);
  });
});
