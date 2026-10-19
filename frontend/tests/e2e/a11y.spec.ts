import { test, expect, type Locator, type Page, type Route, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import * as F from '../../src/brain/testing/wsFrames';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// U17 a11y gate — 本 intent 新頁面的 WCAG 2.1 AA 自動掃描閘門（N-9；`[DM:D6]`=A：違規即讓 ui-regression 變紅）。
//
// 每個掃描 test() 依序走四層（`security-design.md` 第一節）：
//   隔離層 isolate()  → 兜底 HTTP／WebSocket 最先註冊，未被具體 handler 接管的請求一律記錄並中止（C-01、D-05）
//   狀態層 stage      → 只註冊該畫面用得到的端點，再導航與互動（A11Y-S10、C-04、C-07、D-01、D-02）
//   就緒層 ready()    → 就緒 test-id 可見、排除項為 0；不以任何 axe 結果欄位當作「有掃到」的證據（C-02）
//   掃描層 scan()     → withTags 限 WCAG 2.1 AA、先寫檔再斷言、只附 violations 與 incomplete（A11Y-S8、S9、C-03、D-03、D-04）
//
// **全部走攔截，不打真實後端**：不需要資料庫、後端、claude CLI 或 n8n。token 為固定假值（A11Y-S6）。
// **資料形狀**複製自 entry-page／memory-page／project-pages／member-pages 四支 spec 的最小必要部分，刻意不抽
// 共用模組（不改已交付單元的 spec；漂移的後果是就緒層大聲失敗，不是靜默放行）。
//
// **名稱穩定性（合併後不可改）**：TCMS 案例名稱為 `<describe> › <test>`，`U17 a11y gate` 與每個 test 字串
// 一旦合併就不得再改。
//
// **檔內順序是設計的一部分**：「基準清單沒有過期條目」必須是最後一個 test，且依賴 playwright.config.ts 的
// fullyParallel: false 與 workers: 1。改動該設定須同步改這裡的寫檔式過期檢查（`security-design.md` 第五節）。

// ---------------------------------------------------------------------------
// 常數
// ---------------------------------------------------------------------------

/** 固定假 token（A11Y-S6）：與既有 spec 的 stub 同形狀，不是任何真實憑證。 */
const FAKE_TOKEN = 'a11y-fake-token';
const SELF_ID = 1701;
const OTHER_ID = 1702;
const PROJECT_ID = 17;
const SYSTEM_ID = 170;

/** A11Y-S8：規則集逐字限定為 WCAG 2.1 AA。 */
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

/**
 * C-03 規則 5：跨元件結構類規則一律不得進基準。Step 12 以 axe-core 4.13.0 的 axe.getRules(WCAG_TAGS) 實查過：
 * 清單中只有 `duplicate-id-aria`、`list`、`listitem` 會在上列標籤下執行，其餘屬 best-practice、不會執行（見 code-summary.md）。
 * 清單仍完整保留，因為它擋的是「有人手動把這類條目寫進基準」，與該規則當下是否執行無關。
 */
const BOUNDARY_RULES = [
  'landmark-unique',
  'landmark-no-duplicate-banner',
  'landmark-no-duplicate-main',
  'landmark-one-main',
  'region',
  'heading-order',
  'page-has-heading-one',
  'duplicate-id-aria',
  'list',
  'listitem',
];

/**
 * C-03 規則 1：本 intent 新元件的根節點。基準條目的選擇器字串含其中任一者即違規（靜態檢查）；
 * 執行期另以 DOM 的 closest() 判定節點是否落在根節點子樹內（NEW_ROOT_DOM_SELECTOR）。
 *
 * `[data-slot="reselection-banner"]` 是 D-01 查出的橫幅真正外層——C-03 只列了 host，但確認、展開、專案清單
 * 都在 host 之外的兄弟節點，只收 host 會讓那些新元件節點被當成頁殼收進基準。此處刻意比 C-03 更嚴。
 */
const NEW_ROOT_TESTIDS = [
  'brain-entry-page',
  'memory-page',
  'projects-list-page',
  'project-create-page',
  'project-detail-page',
  'members-list-page',
  'member-detail-page',
  'invite-dialog',
  'remove-confirm-dialog',
  'reselection-banner-host',
];
/** Sidebar 三個新增 <nav> 的可定位特徵（入口、專案以 aria-label；我的記憶的 <nav> 無 aria-label，以其連結 test-id）。 */
const NEW_SIDEBAR_MARKERS = [
  'aria-label="入口"',
  'aria-label="專案"',
  'sidebar-entry-link',
  'sidebar-projects-link',
  'sidebar-memory-link',
];
/**
 * 新元件子孫的 test-id 前綴（U14／U15／U23／U24 的全部 test-id 都落在這些前綴下；2026-10-17 實查既有頁面與
 * Sidebar／Layout 的既有部分皆無此前綴）。只比對根節點字串擋不住「新元件子孫」的條目（例如角色下拉），
 * 故靜態檢查一併比對前綴；以 role＋名稱表達的子孫仍只能由掃描層的執行期 closest() 判定擋下。
 */
const NEW_TESTID_PREFIXES = [
  'brain-',
  'memory-',
  'project-',
  'projects-',
  'member-',
  'members-',
  'invite-',
  'remove-confirm-',
  'reselection-banner',
  'requirements-',
];
const NEW_ROOT_STRING_MARKERS = [
  ...NEW_ROOT_TESTIDS,
  ...NEW_SIDEBAR_MARKERS,
  'data-slot="reselection-banner"',
  ...NEW_TESTID_PREFIXES.map((prefix) => `data-testid="${prefix}`),
];
const NEW_ROOT_DOM_SELECTOR = [
  ...NEW_ROOT_TESTIDS.map((id) => `[data-testid="${id}"]`),
  '[data-slot="reselection-banner"]',
  'nav[aria-label="入口"]',
  'nav[aria-label="專案"]',
  'nav:has([data-testid="sidebar-memory-link"])',
].join(', ');

const BASELINE_PATH = fileURLToPath(new URL('./a11y-baseline.json', import.meta.url));
/** 每個掃描點的實際所見寫成一檔；同名覆寫，重試後留下的就是最後一次嘗試（C-03 規則 2、D-03）。 */
const RESULTS_SUBDIR = 'a11y-scan-results';

// ---------------------------------------------------------------------------
// 型別
// ---------------------------------------------------------------------------

type Perm = { view: boolean; edit: boolean; review: boolean };
const FULL: Perm = { view: true, edit: true, review: false };
const VIEW_ONLY: Perm = { view: true, edit: false, review: false };

/** 就緒／排除項：test-id、精確文字定位器（D-02），或精確可及標籤（例如只有 aria-label 的連線中骨架）。 */
type Probe = string | { text: string } | { label: string };

interface ScanDef {
  id: string;
  /** 狀態層：註冊具體端點並導航（兜底已由隔離層註冊）。 */
  stage: (page: Page) => Promise<void>;
  /** 掃描前的互動（D-02）。 */
  interact?: (page: Page) => Promise<void>;
  ready: Probe[];
  absent: Probe[];
  /** 須成立的屬性（例如 aria-selected／aria-expanded）。 */
  attrs?: { testid: string; name: string; value: string }[];
  /** 須停留的 pathname（D-02 第 1 列：入口頁以路徑排除 /login、/403；第 18 點以路徑證明落在非入口頁）。 */
  pathname?: string;
  /** 限縮掃描範圍（D-01）。就緒 test-id 必須都在這個根節點之內。 */
  include?: string;
}

interface Baseline {
  version: number;
  entries: { rule: string; selector: string; reason: string }[];
}

interface SeenEntry {
  rule: string;
  /** 穩定選擇器；null 表示取不到（D-04：不得進基準）。 */
  selector: string | null;
  /** 節點是否落在本 intent 新元件的根節點子樹內（C-03 規則 1 的執行期判定）。 */
  inNewRoot: boolean;
  impact: string | null;
  target: string;
}

interface Isolation {
  leakedHttp: string[];
  leakedWs: string[];
}

// ---------------------------------------------------------------------------
// 隔離層（A11Y-S5、C-01、D-05）
// ---------------------------------------------------------------------------

/**
 * 兜底**最先**註冊（Playwright 以後註冊者優先）：
 * - HTTP：兜底樣式（任何 /api 路徑）不回看起來正常的值，一律記錄並 abort——「看起來正常的回應等於掩護」（security-design.md 第二節）。
 * - WebSocket：萬用正規式兜底在連線前關閉並記錄，故未被具體樣式接管的連線**不會**連到真實閘道（D-05）。
 * 其後才註冊兩條具體 WebSocket 樣式（空 handler：不連到伺服器、也不送任何訊框）。
 */
async function isolate(page: Page): Promise<Isolation> {
  const iso: Isolation = { leakedHttp: [], leakedWs: [] };
  await page.route('**/api/**', (route) => {
    iso.leakedHttp.push(`${route.request().method()} ${new URL(route.request().url()).pathname}`);
    return route.abort();
  });
  await page.routeWebSocket(/.*/, (ws) => {
    iso.leakedWs.push(ws.url());
    void ws.close();
  });
  await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, () => undefined);
  await page.routeWebSocket(/\/api\/collab\/ws\/.*/, () => undefined);
  await page.addInitScript((token) => {
    sessionStorage.setItem('token', token);
  }, FAKE_TOKEN);
  return iso;
}

function assertIsolated(iso: Isolation): void {
  expect(iso.leakedHttp, '[隔離層] 有未被具體 handler 接管的 /api 請求').toEqual([]);
  expect(iso.leakedWs, '[隔離層] 有未被具體樣式接管的 WebSocket').toEqual([]);
}

// ---------------------------------------------------------------------------
// 狀態層的共用片段（資料形狀複製自既有 spec，見檔頭）
// ---------------------------------------------------------------------------

async function json(route: Route, status: number, body: unknown): Promise<void> {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: status === 204 ? '' : JSON.stringify(body),
  });
}

/** `/api/auth/me`（形狀沿用 member-pages.spec.ts:115-129）。 */
async function login(page: Page, permissions: Record<string, Perm>): Promise<void> {
  await page.route('**/api/auth/me', (route) =>
    json(route, 200, {
      id: SELF_ID,
      username: 'a11y-user-self',
      role: 'Project_Admin',
      is_active: true,
      authorization_status: 'approved',
      permissions,
      pending_request: null,
    })
  );
}

interface ReselectionStub {
  id: number;
  project_id: number;
  cause: string;
  promoted_user_id: number;
  new_role: string;
}

const reselection = (id: number, projectId: number): ReselectionStub => ({
  id,
  project_id: projectId,
  cause: 'auto_reselection',
  promoted_user_id: SELF_ID,
  new_role: 'project_admin',
});

/** Layout 的改選橫幅查詢（具 K3 view 時每次落地打一次）。 */
async function reselections(page: Page, events: ReselectionStub[] = []): Promise<void> {
  await page.route(/\/api\/membership\/reselections\/pending(\?.*)?$/, (route) => json(route, 200, events));
}

const project = (id: number, name: string) => ({
  id,
  name,
  owner_user_id: SELF_ID,
  is_default: false,
  created_at: '2026-09-01T00:00:00Z',
});

const system = (id: number, projectId: number, name: string) => ({
  id,
  project_id: projectId,
  name,
  is_default: false,
  created_at: '2026-09-02T00:00:00Z',
});

/** 專案清單（GET /api/hierarchy/projects）與每個專案的系統扇出。 */
async function projectsApi(
  page: Page,
  opts: { projects?: ReturnType<typeof project>[]; status?: number } = {}
): Promise<void> {
  const projects = opts.projects ?? [];
  const status = opts.status ?? 200;
  await page.route(/\/api\/hierarchy\/projects(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return json(route, status, status === 200 ? projects : { detail: '讀取失敗' });
  });
  await page.route(/\/api\/hierarchy\/projects\/(\d+)\/systems(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const pid = Number(/projects\/(\d+)\/systems/.exec(route.request().url())?.[1]);
    return json(route, 200, pid === PROJECT_ID ? [system(SYSTEM_ID, PROJECT_ID, 'a11y-system-1')] : []);
  });
}

/** 詳情頁的需求欄位（形狀沿用 project-pages.spec.ts 的 fieldSetBody）與最近變更。 */
async function detailApi(page: Page): Promise<void> {
  await page.route(/\/api\/hierarchy\/diagram-changes(\?.*)?$/, (route) => json(route, 200, []));
  await page.route(/\/api\/requirements\/systems\/(\d+)\/fields(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const field = (key: string, label: string, value: string | null) => ({
      group_key: 'cost',
      field_key: key,
      label,
      value,
      filled_state: value === null ? 'never_filled' : 'filled',
      updated_at: value === null ? null : '2026-09-27T00:00:00Z',
      updated_by: value === null ? null : SELF_ID,
      updated_on_behalf_of: null,
      cleared_at: null,
    });
    return json(route, 200, {
      system_id: SYSTEM_ID,
      unfilled_count: 1,
      input_hint: 'a11y-input-hint：請填寫架構假設',
      groups: [
        {
          group_key: 'cost',
          title: 'a11y 成本組',
          filled_count: 1,
          total_count: 2,
          fields: [field('sla', 'a11y-SLA', '99.9%'), field('tps', 'a11y-尖峰 TPS', null)],
        },
      ],
    });
  });
}

interface MemberStub {
  user_id: number;
  display_name: string;
  role: string;
  joined_at: string;
}

const member = (user_id: number, display_name: string, role: string): MemberStub => ({
  user_id,
  display_name,
  role,
  joined_at: '2026-01-01T00:00:00Z',
});

/** GET 成員清單；其他方法交給個別掃描點覆寫，未覆寫者落入兜底被記錄。 */
async function membersApi(page: Page, selfRole: string): Promise<void> {
  const members = [member(SELF_ID, 'a11y-user-self', selfRole), member(OTHER_ID, 'a11y-user-other', 'member')];
  await page.route(/\/api\/membership\/projects\/\d+\/members(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return json(route, 200, members);
  });
}

/** 入口頁（K1 view 時 DefaultRedirect 直接渲染）。大腦 WebSocket 由隔離層的空 handler 接管。 */
async function stageEntry(page: Page, events: ReselectionStub[] = []): Promise<void> {
  await login(page, { K1: FULL, K3: VIEW_ONLY });
  await reselections(page, events);
  await page.goto('/');
}

async function stageProjectDetail(page: Page, tab: 'overview' | 'requirements' | 'memory'): Promise<void> {
  await login(page, { K2: FULL, K3: VIEW_ONLY, K4: FULL });
  await reselections(page);
  await projectsApi(page, { projects: [project(PROJECT_ID, 'a11y-project-detail')] });
  await detailApi(page);
  // 先落在另一籤，再點目標籤切換（D-02：掃描前的互動是「點 project-tab-<key>」）。
  await page.goto(`/projects/${PROJECT_ID}?tab=${tab === 'overview' ? 'memory' : 'overview'}`);
}

async function stageMembers(page: Page, opts: { k3: Perm; selfRole: string }): Promise<void> {
  await login(page, { K3: opts.k3 });
  await reselections(page);
  await membersApi(page, opts.selfRole);
  await page.goto(`/projects/${PROJECT_ID}/members`);
}

async function stageMemberDetail(page: Page): Promise<void> {
  await login(page, { K3: FULL });
  await reselections(page);
  await membersApi(page, 'project_admin');
  await page.goto(`/projects/${PROJECT_ID}/members/${OTHER_ID}`);
}

/**
 * 已連線的入口頁（審查 review-01 R-01）：以後註冊者優先的規則，覆寫隔離層的空 handler，收到 hello 時送出握手
 * 快照，使 ContextBar 進入 `default`。訊框一律由 src/brain/testing/wsFrames.ts 的建構器產生（形狀沿用
 * entry-page.spec.ts:58 的 BrainServer；不得手寫訊框，EPN-19）。快照帶一個專案＋系統作業對象與一個進行中的工作項，
 * 讓脈絡列的名稱節點與工作項面板一起被掃描。
 */
function connectedSnapshot(): string[] {
  return F.snapshotFrames(
    F.workTargetFrame('shared', String(PROJECT_ID), String(SYSTEM_ID), null, 'a11y-project-connected', 'a11y-system-connected', null),
    [F.workItem('a11y-wi-1', 'a11y 工作項', 'running')]
  );
}

async function stageEntryConnected(page: Page): Promise<void> {
  await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, (ws) => {
    ws.onMessage((raw) => {
      const frame = JSON.parse(String(raw)) as { type?: string };
      if (frame.type === 'hello') for (const f of connectedSnapshot()) ws.send(f);
    });
  });
  await stageEntry(page);
}

/**
 * U16（logical-components §二、N-06）：已連線的入口頁開啟「切換對象」選單。/me 帶 K2 view＋edit；選單的全部
 * /api/hierarchy 請求都在此樁化（隔離層會中止未樁化的 /api 請求）。三個專案：作業對象所在的 17（自有，預設展開、
 * 系統 170）、他人擁有的 18（停用＋說明）、自有的 19。
 */
async function stagePicker(page: Page, opts: { createStatus?: number } = {}): Promise<void> {
  await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, (ws) => {
    ws.onMessage((raw) => {
      const frame = JSON.parse(String(raw)) as { type?: string };
      if (frame.type === 'hello') for (const f of connectedSnapshot()) ws.send(f);
    });
  });
  await login(page, { K1: FULL, K2: FULL, K3: VIEW_ONLY });
  await reselections(page);
  await projectsApi(page, {
    projects: [
      project(PROJECT_ID, 'a11y-picker-own'),
      { ...project(PROJECT_ID + 1, 'a11y-picker-other'), owner_user_id: OTHER_ID },
      project(PROJECT_ID + 2, 'a11y-picker-own-2'),
    ],
  });
  if (opts.createStatus !== undefined) {
    const status = opts.createStatus;
    await page.route(/\/api\/hierarchy\/projects(\?.*)?$/, (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      return json(route, status, { detail: 'a11y-duplicate' });
    });
  }
  await page.goto('/');
}

async function openPicker(page: Page): Promise<void> {
  await expect(page.getByTestId('brain-context-switch-object')).toBeVisible();
  await page.getByTestId('brain-context-switch-object').click();
}

const PROJECT_DETAIL_LOADING: Probe[] = [
  'project-detail-error',
  'project-not-found',
  { text: '正在載入專案…' },
  { text: '正在載入需求欄位…' },
];

// ---------------------------------------------------------------------------
// 21 個掃描點（C-02 表第 1–17 列 ＋ C-07 第 18 點；互動與定位器依 D-02；第 20 點為 review-01 R-01 增列的已連線入口頁；
// 第 21、22 點為 U16 增列的切換對象選單兩態，logical-components §二）
// ---------------------------------------------------------------------------

const SCANS = {
  entry: {
    id: '01-entry',
    stage: (page) => stageEntry(page),
    ready: ['brain-entry-page'],
    absent: [],
    pathname: '/',
  },
  memory: {
    id: '02-memory',
    stage: async (page) => {
      await login(page, { K3: VIEW_ONLY });
      await reselections(page);
      await page.route(/\/api\/memory\/records(\?.*)?$/, (route) => {
        const kind = new URL(route.request().url()).searchParams.get('kind');
        const rows =
          kind === 'semantic'
            ? [
                {
                  memory_id: '1',
                  kind: 'semantic',
                  owner_user_id: SELF_ID,
                  visibility_scope: 'owner',
                  content: 'a11y-memory-semantic-01',
                  embedding_model: 'stub-v1',
                  created_at: '2026-09-01T00:00:00Z',
                  expires_at: null,
                },
              ]
            : [];
        return json(route, 200, rows);
      });
      await page.goto('/memory');
    },
    // D-02：固定片段而非萬用字元；片段依 memory-page-ui 的映射表（OPEN-MP15-4：procedure → procedural）。
    ready: ['memory-page', 'memory-zone-semantic'],
    absent: ['memory-page-identity-error'],
  },
  projectsList: {
    id: '03-projects-list',
    stage: async (page) => {
      await login(page, { K2: FULL, K3: VIEW_ONLY });
      await reselections(page);
      await projectsApi(page, {
        projects: [project(PROJECT_ID, 'a11y-project-a'), project(PROJECT_ID + 1, 'a11y-project-b')],
      });
      await page.goto('/projects');
    },
    ready: ['projects-list-page', 'project-list'],
    absent: ['project-list-skeleton', 'project-list-error'],
  },
  detailOverview: {
    id: '04-project-detail-overview',
    stage: (page) => stageProjectDetail(page, 'overview'),
    interact: (page) => page.getByTestId('project-tab-overview').click(),
    ready: ['project-detail-page', 'project-tab-overview', 'project-count-systems'],
    absent: PROJECT_DETAIL_LOADING,
    attrs: [{ testid: 'project-tab-overview', name: 'aria-selected', value: 'true' }],
  },
  detailRequirements: {
    id: '05-project-detail-requirements',
    stage: (page) => stageProjectDetail(page, 'requirements'),
    interact: (page) => page.getByTestId('project-tab-requirements').click(),
    ready: ['project-detail-page', 'project-tab-requirements', 'requirements-group-cost'],
    absent: PROJECT_DETAIL_LOADING,
    attrs: [{ testid: 'project-tab-requirements', name: 'aria-selected', value: 'true' }],
  },
  detailMemory: {
    id: '06-project-detail-memory',
    stage: (page) => stageProjectDetail(page, 'memory'),
    interact: (page) => page.getByTestId('project-tab-memory').click(),
    ready: ['project-detail-page', 'project-tab-memory', 'memory-summary-unavailable'],
    absent: PROJECT_DETAIL_LOADING,
    attrs: [{ testid: 'project-tab-memory', name: 'aria-selected', value: 'true' }],
  },
  projectCreate: {
    id: '07-project-create',
    stage: async (page) => {
      await login(page, { K2: FULL, K3: VIEW_ONLY });
      await reselections(page);
      await page.goto('/projects/new');
    },
    ready: ['project-create-page', 'project-create-name'],
    absent: ['project-create-error'],
  },
  membersAdmin: {
    id: '08-members-admin-view',
    stage: (page) => stageMembers(page, { k3: FULL, selfRole: 'project_admin' }),
    ready: ['members-list-page', 'member-list-table', 'member-list-invite-button'],
    absent: [{ text: '載入中…' }, 'member-list-error'],
  },
  membersMember: {
    id: '09-members-member-view',
    // 視角的旋鈕是 /me 的 K3 edit：自身仍是 project_admin，但缺 K3 edit 時 canManage 為 false（兩段式）。
    // 這讓突變 M4（把 /me 改成 admin 權限）能直接讓 member-list-invite-button 出現。
    stage: (page) => stageMembers(page, { k3: VIEW_ONLY, selfRole: 'project_admin' }),
    ready: ['members-list-page', 'member-list-table'],
    absent: ['member-list-invite-button', { text: '載入中…' }, 'member-list-error'],
  },
  memberDetail: {
    id: '10-member-detail',
    stage: (page) => stageMemberDetail(page),
    ready: ['member-detail-page', 'member-detail-role-select'],
    absent: [{ text: '載入中…' }, 'member-detail-error'],
  },
  inviteDefault: {
    id: '11-invite-dialog-default',
    stage: (page) => stageMembers(page, { k3: FULL, selfRole: 'project_admin' }),
    interact: (page) => page.getByTestId('member-list-invite-button').click(),
    ready: ['invite-dialog', 'invite-dialog-user-id'],
    absent: ['invite-dialog-rejection-reason'],
  },
  inviteDenied: {
    id: '12-invite-dialog-denied',
    stage: async (page) => {
      await stageMembers(page, { k3: FULL, selfRole: 'project_admin' });
      // U24 既有 e2e 的造法：422 且 detail 為字串＝受邀者缺全域功能權限（InviteRejectedError）。
      await page.route(/\/api\/membership\/projects\/\d+\/members(\?.*)?$/, (route) => {
        if (route.request().method() !== 'POST') return route.fallback();
        return json(route, 422, { detail: '受邀者缺少必要的全域功能權限' });
      });
    },
    interact: async (page) => {
      await page.getByTestId('member-list-invite-button').click();
      await page.getByTestId('invite-dialog-user-id').fill('4444');
      await page.getByTestId('invite-dialog-submit').click();
    },
    ready: ['invite-dialog', 'invite-dialog-rejection-reason'],
    absent: [],
  },
  bannerSingle: {
    id: '13-reselection-banner-single',
    stage: (page) => stageEntry(page, [reselection(11, 71)]),
    ready: ['reselection-banner-host', 'reselection-banner-acknowledge'],
    absent: ['reselection-banner-projects'],
    pathname: '/',
  },
  bannerMulti: {
    id: '14-reselection-banner-multi-expanded',
    stage: (page) => stageEntry(page, [reselection(11, 71), reselection(12, 72)]),
    interact: (page) => page.getByTestId('reselection-banner-expand').click(),
    ready: ['reselection-banner-host', 'reselection-banner-projects'],
    absent: [],
    attrs: [{ testid: 'reselection-banner-expand', name: 'aria-expanded', value: 'true' }],
    pathname: '/',
  },
  removeConfirm: {
    id: '15-remove-confirm-dialog',
    stage: (page) => stageMemberDetail(page),
    interact: (page) => page.getByTestId('member-detail-remove').click(),
    ready: ['remove-confirm-dialog'],
    absent: [],
  },
  projectsEmpty: {
    id: '16-projects-empty',
    stage: async (page) => {
      await login(page, { K2: FULL, K3: VIEW_ONLY });
      await reselections(page);
      await projectsApi(page, { projects: [] });
      await page.goto('/projects');
    },
    ready: ['project-list-empty', 'project-list-empty-create'],
    absent: ['project-list', 'project-list-error', 'project-list-skeleton'],
  },
  projectsError: {
    id: '17-projects-error',
    stage: async (page) => {
      await login(page, { K2: FULL, K3: VIEW_ONLY });
      await reselections(page);
      await projectsApi(page, { status: 500 });
      await page.goto('/projects');
    },
    ready: ['project-list-error'],
    absent: ['project-list-skeleton'],
  },
  bannerOffEntry: {
    id: '18-reselection-banner-non-entry-landing',
    // C-07 最低義務：落地頁不是入口頁。實作上入口頁的閘是 K1 view（App.tsx DefaultRedirect，非 C-07 寫的 C1），
    // 故 /me 不帶 K1、只帶 C1 view：DefaultRedirect 落在 /cost——它是 API 面最小的既有落地頁（只打一支
    // GET /api/cost/v1/sets）。該頁是本 intent 不管的既有頁，所以這一點以 include() 限縮到橫幅外層（D-01）。
    stage: async (page) => {
      await login(page, { C1: VIEW_ONLY, K3: VIEW_ONLY });
      await reselections(page, [reselection(11, 71)]);
      await page.route(/\/api\/cost\/v1\/sets(\?.*)?$/, (route) => json(route, 200, []));
      await page.goto('/');
    },
    include: '[data-slot="reselection-banner"]',
    ready: ['reselection-banner-host', 'reselection-banner-acknowledge'],
    absent: [],
    pathname: '/cost',
  },
  entryConnected: {
    id: '20-entry-connected',
    stage: (page) => stageEntryConnected(page),
    ready: ['brain-entry-page', 'brain-context-bar', 'brain-context-name-project'],
    // 已連線的證據：連線中骨架（只有 aria-label、沒有 test-id）不存在，且脈絡列為 default。
    absent: [{ label: '連線中' }, 'brain-context-none'],
    attrs: [{ testid: 'brain-context-bar', name: 'data-state', value: 'default' }],
    pathname: '/',
  },
  pickerDefault: {
    id: '21-object-picker-default',
    stage: (page) => stagePicker(page),
    interact: (page) => openPicker(page),
    include: '[data-testid="brain-object-picker"]',
    ready: ['brain-object-search', 'brain-object-item-170', 'brain-object-not-owned-18', 'brain-object-create-project'],
    absent: ['brain-object-loading', 'brain-object-error'],
    attrs: [{ testid: 'brain-object-expand-17', name: 'aria-expanded', value: 'true' }],
    pathname: '/',
  },
  pickerCreateError: {
    id: '22-object-picker-create-error',
    stage: (page) => stagePicker(page, { createStatus: 409 }),
    interact: async (page) => {
      await openPicker(page);
      await page.getByTestId('brain-object-create-project').click();
      await page.getByTestId('brain-object-create-name').fill('a11y-picker-duplicate');
      await page.getByTestId('brain-object-create-submit').click();
    },
    include: '[data-testid="brain-object-picker"]',
    ready: ['brain-object-create-name', 'brain-object-create-error'],
    absent: ['brain-object-loading'],
    pathname: '/',
  },
} satisfies Record<string, ScanDef>;

const ALL_SCANS: ScanDef[] = Object.values(SCANS);

// ---------------------------------------------------------------------------
// 就緒層（A11Y-S7、C-02、D-01、D-02）
// ---------------------------------------------------------------------------

function locate(scope: Page | Locator, probe: Probe): Locator {
  if (typeof probe === 'string') return scope.getByTestId(probe);
  if ('text' in probe) return scope.getByText(probe.text, { exact: true });
  return scope.getByLabel(probe.label, { exact: true });
}

function describeProbe(probe: Probe): string {
  if (typeof probe === 'string') return probe;
  return 'text' in probe ? `text「${probe.text}」` : `label「${probe.label}」`;
}

async function ready(page: Page, def: ScanDef): Promise<void> {
  if (def.pathname) {
    await expect.poll(() => new URL(page.url()).pathname, { message: '[就緒層] pathname' }).toBe(def.pathname);
  }
  // D-01 通則：使用 include() 的掃描點，就緒 test-id 以 include 根節點為範圍定位。
  let scope: Page | Locator = page;
  if (def.include) {
    const root = page.locator(def.include);
    await expect(root, `[就緒層] include 根節點 ${def.include}`).toHaveCount(1);
    scope = root;
  }
  for (const probe of def.ready) {
    await expect(locate(scope, probe), `[就緒層] ${describeProbe(probe)} 須可見`).toBeVisible();
  }
  for (const probe of def.absent) {
    await expect(locate(page, probe), `[就緒層] ${describeProbe(probe)} 須不存在`).toHaveCount(0);
  }
  for (const a of def.attrs ?? []) {
    await expect(scope.getByTestId(a.testid), `[就緒層] ${a.testid} 的 ${a.name}`).toHaveAttribute(a.name, a.value);
  }
}

// ---------------------------------------------------------------------------
// 掃描層（A11Y-S8、A11Y-S9、C-03、D-03、D-04）
// ---------------------------------------------------------------------------

function loadBaseline(): Baseline {
  return JSON.parse(fs.readFileSync(BASELINE_PATH, 'utf-8')) as Baseline;
}

const keyOf = (rule: string, selector: string) => `${rule} :: ${selector}`;

function resultsDir(testInfo: TestInfo): string {
  return path.join(testInfo.project.outputDir, RESULTS_SUBDIR);
}

/**
 * 把 axe 回報的節點重新定位為穩定選擇器（C-03：不得用 nth-child 型）。依序嘗試元素自身的 id、data-testid、
 * aria-label，最後是 role ＋ 名稱（D-04：名稱取自 aria-label、aria-labelledby 指向的文字或文字內容）。
 * 四者皆取不到時回 null——該節點不得進基準。
 */
async function stabilize(page: Page, target: string, rootSelector: string): Promise<{ selector: string | null; inNewRoot: boolean }> {
  return page.evaluate(
    ([sel, roots]) => {
      const el = document.querySelector(sel);
      if (!el) return { selector: null, inNewRoot: false };
      const inNewRoot = el.closest(roots) !== null;
      const tag = el.tagName.toLowerCase();
      const id = el.getAttribute('id');
      // React useId 產生的 id（含「:」或「«」）每次 render 可能不同，不算穩定。
      if (id && !/[:«»]/.test(id) && document.querySelectorAll(`#${CSS.escape(id)}`).length === 1) {
        return { selector: `#${id}`, inNewRoot };
      }
      const testid = el.getAttribute('data-testid');
      if (testid) return { selector: `[data-testid="${testid}"]`, inNewRoot };
      const label = el.getAttribute('aria-label');
      if (label) return { selector: `${tag}[aria-label="${label}"]`, inNewRoot };
      const implicit: Record<string, string> = {
        a: 'link',
        button: 'button',
        nav: 'navigation',
        main: 'main',
        select: 'combobox',
        textarea: 'textbox',
        img: 'img',
        ul: 'list',
        ol: 'list',
        li: 'listitem',
        h1: 'heading',
        h2: 'heading',
        h3: 'heading',
        h4: 'heading',
        input: 'textbox',
      };
      const role = el.getAttribute('role') ?? implicit[tag];
      const labelledby = el.getAttribute('aria-labelledby');
      const byRef = labelledby
        ? labelledby
            .split(/\s+/)
            .map((ref) => document.getElementById(ref)?.textContent ?? '')
            .join(' ')
        : '';
      const name = (byRef || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80);
      if (role && name) return { selector: `role=${role}[name="${name}"]`, inNewRoot };
      return { selector: null, inNewRoot };
    },
    [target, rootSelector] as const
  );
}

async function scan(page: Page, testInfo: TestInfo, def: ScanDef): Promise<void> {
  let builder = new AxeBuilder({ page }).withTags(WCAG_TAGS);
  if (def.include) builder = builder.include(def.include);
  const results = await builder.analyze();

  const seen: SeenEntry[] = [];
  for (const v of results.violations) {
    for (const node of v.nodes) {
      const raw = node.target.length === 1 && typeof node.target[0] === 'string' ? node.target[0] : null;
      const located = raw ? await stabilize(page, raw, NEW_ROOT_DOM_SELECTOR) : { selector: null, inNewRoot: false };
      seen.push({
        rule: v.id,
        selector: located.selector,
        inNewRoot: located.inNewRoot,
        impact: node.impact ?? null,
        target: JSON.stringify(node.target),
      });
    }
  }

  // D-03：任何斷言之前先寫檔（寫實際看到的條目），否則一個真實的新違規會讓過期檢查因檔數不足而紅、混淆紅燈原因。
  const dir = resultsDir(testInfo);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, `${def.id}.json`),
    JSON.stringify({ scan: def.id, retry: testInfo.retry, entries: seen }, null, 2)
  );
  // A11Y-S6／A11Y-S8：附件只放 violations 與 incomplete，不附整頁 HTML。
  await testInfo.attach(`axe-${def.id}`, {
    body: JSON.stringify({ violations: results.violations, incomplete: results.incomplete }, null, 2),
    contentType: 'application/json',
  });

  // 基準只在三個條件同時成立時豁免一筆：有穩定選擇器、不在新元件根節點內、規則不屬交界類。
  const baseline = new Set(loadBaseline().entries.map((e) => keyOf(e.rule, e.selector)));
  const fresh = seen.filter(
    (e) =>
      !(e.selector !== null && !e.inNewRoot && !BOUNDARY_RULES.includes(e.rule) && baseline.has(keyOf(e.rule, e.selector)))
  );
  expect(fresh, `[掃描層] ${def.id} 有基準以外的 WCAG 2.1 AA 違規`).toEqual([]);
}

/** 一個掃描 test() 的完整流程：隔離 → 狀態 → 互動 → 就緒 → 隔離斷言 → 掃描 → 隔離斷言。 */
async function runScan(page: Page, testInfo: TestInfo, def: ScanDef): Promise<void> {
  const iso = await isolate(page);
  await def.stage(page);
  try {
    if (def.interact) await def.interact(page);
    await ready(page, def);
  } catch (err) {
    // 漏接的端點常讓頁面停在錯誤態、使就緒層先紅；此時把紅燈歸因到真正的原因（隔離層）。
    if (iso.leakedHttp.length > 0 || iso.leakedWs.length > 0) assertIsolated(iso);
    throw err;
  }
  // 掃描前先斷言一次：漏接已發生時，掃到的是一個降級畫面，掃描結果不具意義。
  assertIsolated(iso);
  await scan(page, testInfo, def);
  assertIsolated(iso);
}

// ---------------------------------------------------------------------------
// 測試
// ---------------------------------------------------------------------------

test.describe('U17 a11y gate', () => {
  /**
   * @purpose 入口頁在具 K1 的已核准帳號下通過 WCAG 2.1 AA 自動掃描，且掃到的確實是入口頁而非登入頁或 403。
   * @ui / | 入口頁 brain-entry-page（含頁殼 Sidebar 與改選橫幅宿主）
   * @given 攔截層：/api/auth/me 回 K1 view+edit、K3 view；改選事件為空；大腦 WebSocket 以空 handler 接管
   * @step 開啟 / | pathname 停在 /，brain-entry-page 可見
   * @step 以 wcag2a、wcag2aa、wcag21a、wcag21aa 規則集掃描整頁 | 基準清單以外的違規為 0
   * @step 檢查隔離記錄 | 沒有未接管的 /api 請求或 WebSocket
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note 以 pathname 判定而非 test-id：/login 與 /403 都沒有可用的 test-id（D-02 第 1 列）。
   */
  test('01 入口頁', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.entry);
  });

  /**
   * @purpose 我的記憶頁在有語意記憶時通過 WCAG 2.1 AA 自動掃描。
   * @ui /memory | 記憶頁 memory-page 與語意區 memory-zone-semantic
   * @given 攔截層：/api/memory/records 依 kind 回應，語意區一筆、其餘兩區為空
   * @step 開啟 /memory | memory-page 與 memory-zone-semantic 可見，memory-page-identity-error 不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note 區塊 test id 用固定片段 semantic，不用萬用字元（D-02）；片段與 API 值的映射見 OPEN-MP15-4。
   */
  test('02 我的記憶頁', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.memory);
  });

  /**
   * @purpose 專案清單在有兩個專案時通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects | 專案清單頁 projects-list-page 與 project-list
   * @given 攔截層：/api/auth/me 帶 K2 view+edit；專案清單回兩筆，系統扇出各自回應
   * @step 開啟 /projects | project-list 可見，骨架與錯誤態不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('03 專案清單', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.projectsList);
  });

  /**
   * @purpose 專案詳情的總覽籤通過 WCAG 2.1 AA 自動掃描，且掃描時總覽籤確實為選取狀態並已載入完成。
   * @ui /projects/:projectId | 專案詳情頁 project-detail-page，總覽籤
   * @given 攔截層：一個專案、一個系統、需求欄位與最近變更皆有回應；先落在記憶摘要籤
   * @step 點選 project-tab-overview | 該籤 aria-selected 為 true，project-count-systems 可見，載入文字不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('04 專案詳情總覽籤', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.detailOverview);
  });

  /**
   * @purpose 專案詳情的需求籤通過 WCAG 2.1 AA 自動掃描（含已填與未填欄位）。
   * @ui /projects/:projectId | 專案詳情頁需求籤 requirements-group-cost
   * @given 攔截層：/api/auth/me 帶 K4 view+edit；需求欄位一欄已填、一欄從未填；先落在總覽籤
   * @step 點選 project-tab-requirements | 該籤 aria-selected 為 true，requirements-group-cost 可見，載入文字不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note 未填欄位的文字標示由 U23 的 e2e 斷言行為面（C-04 第一列），本點只涵蓋結構面。
   */
  test('05 專案詳情需求籤', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.detailRequirements);
  });

  /**
   * @purpose 專案詳情的記憶摘要籤通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects/:projectId | 專案詳情頁記憶摘要籤 memory-summary-unavailable
   * @given 攔截層：同總覽籤；先落在總覽籤
   * @step 點選 project-tab-memory | 該籤 aria-selected 為 true，memory-summary-unavailable 可見
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('06 專案詳情記憶摘要籤', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.detailMemory);
  });

  /**
   * @purpose 專案建立頁通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects/new | 專案建立頁 project-create-page 與名稱欄 project-create-name
   * @given 攔截層：/api/auth/me 帶 K2 view+edit
   * @step 開啟 /projects/new | project-create-name 可見，project-create-error 不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note 此畫面只在契約 K-19 列為 axe 掃描標的，清單沒有列（A11Y-S10 的聯集）。
   */
  test('07 專案建立頁', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.projectCreate);
  });

  /**
   * @purpose 成員清單的管理者視角通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects/:projectId/members | 成員清單 member-list-table 與邀請鈕 member-list-invite-button
   * @given 攔截層：/api/auth/me 帶 K3 view+edit；自身在該專案為 project_admin
   * @step 開啟成員清單 | member-list-table 與 member-list-invite-button 可見，「載入中…」與錯誤態不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('08 成員清單管理者視角', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.membersAdmin);
  });

  /**
   * @purpose 成員清單的一般成員視角通過 WCAG 2.1 AA 自動掃描，且掃到的確實不是管理者視角。
   * @ui /projects/:projectId/members | 成員清單 member-list-table（無邀請鈕）
   * @given 攔截層：/api/auth/me 帶 K3 view（無 edit）；自身在該專案為 project_admin，故兩段式判定不可管理
   * @step 開啟成員清單 | member-list-table 可見，member-list-invite-button 不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note 視角的證據寫在排除項：管理者視角被誤掃成這一點時，邀請鈕會出現而讓就緒層紅（突變 M4）。
   */
  test('09 成員清單一般成員視角', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.membersMember);
  });

  /**
   * @purpose 成員詳情頁（角色下拉、移出專案、變更紀錄）通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects/:projectId/members/:userId | 成員詳情 member-detail-page 與角色下拉 member-detail-role-select
   * @given 攔截層：/api/auth/me 帶 K3 view+edit；自身為 project_admin，檢視另一位成員
   * @step 開啟成員詳情 | member-detail-role-select 可見，「載入中…」與錯誤態不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note 此畫面只在契約 K-20 列為 axe 掃描標的，清單沒有列（A11Y-S10 的聯集）。
   */
  test('10 成員詳情頁', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.memberDetail);
  });

  /**
   * @purpose 邀請對話框的初始狀態通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects/:projectId/members | 邀請對話框 invite-dialog
   * @given 同成員清單管理者視角
   * @step 點選 member-list-invite-button | invite-dialog 與 invite-dialog-user-id 可見，拒絕理由不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('11 邀請對話框初始狀態', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.inviteDefault);
  });

  /**
   * @purpose 邀請對話框的拒絕狀態（受邀者缺全域權限）通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects/:projectId/members | 邀請對話框拒絕理由 invite-dialog-rejection-reason
   * @given 同成員清單管理者視角，另攔截邀請 POST 回 422 且 detail 為字串
   * @step 開啟對話框、填入使用者 ID 並送出 | 對話框保持開啟，invite-dialog-rejection-reason 可見
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('12 邀請對話框拒絕狀態', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.inviteDenied);
  });

  /**
   * @purpose 入口頁上的單筆改選橫幅通過 WCAG 2.1 AA 自動掃描。
   * @ui / | 入口頁上的改選橫幅 reselection-banner-host 與確認鈕
   * @given 攔截層：/api/auth/me 帶 K1、K3 view；改選事件一筆
   * @step 開啟 / | reselection-banner-acknowledge 可見，展開清單不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('13 改選橫幅單筆', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.bannerSingle);
  });

  /**
   * @purpose 入口頁上的多筆改選橫幅在展開專案清單後通過 WCAG 2.1 AA 自動掃描。
   * @ui / | 入口頁上的改選橫幅與展開後的專案清單 reselection-banner-projects
   * @given 攔截層：/api/auth/me 帶 K1、K3 view；改選事件兩筆
   * @step 點選 reselection-banner-expand | 其 aria-expanded 為 true，reselection-banner-projects 可見
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('14 改選橫幅多筆展開', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.bannerMulti);
  });

  /**
   * @purpose 移出專案的二次確認對話框通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects/:projectId/members/:userId | 移出確認對話框 remove-confirm-dialog
   * @given 同成員詳情頁
   * @step 點選 member-detail-remove | remove-confirm-dialog 可見
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('15 移出確認對話框', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.removeConfirm);
  });

  /**
   * @purpose 專案清單的首次使用空狀態通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects | 專案清單空狀態 project-list-empty 與建立入口
   * @given 攔截層：專案清單回空陣列
   * @step 開啟 /projects | project-list-empty 與 project-list-empty-create 可見，清單與錯誤態不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('16 專案清單空狀態', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.projectsEmpty);
  });

  /**
   * @purpose 專案清單的錯誤態通過 WCAG 2.1 AA 自動掃描。
   * @ui /projects | 專案清單錯誤態 project-list-error
   * @given 攔截層：專案清單回 500
   * @step 開啟 /projects | project-list-error 可見，骨架不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   */
  test('17 專案清單錯誤態', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.projectsError);
  });

  /**
   * @purpose 改選橫幅在非入口頁的落地頁上也通過 WCAG 2.1 AA 自動掃描，且掃描範圍只含橫幅。
   * @ui /cost | 既有成本頁上的改選橫幅外層 data-slot="reselection-banner"
   * @given 攔截層：/api/auth/me 不帶 K1、只帶 C1 view 與 K3 view；改選事件一筆；成本頁的估價清單回空陣列
   * @step 開啟 / | DefaultRedirect 導向 /cost，橫幅外層內的 reselection-banner-host 與確認鈕可見
   * @step 以 include 限縮到橫幅外層並掃描 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立（就緒 test-id 皆在 include 子樹內）、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note include 目標是橫幅外層而非 host：確認、展開與專案清單都在 host 之外（D-01，突變 M11）。
   */
  test('18 改選橫幅非入口落地頁', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.bannerOffEntry);
  });

  /**
   * @purpose 手機寬度下入口頁沒有橫向捲動（AC-A11Y.2）；axe 不檢查橫向溢出，故以版面量測補上。
   * @ui / | 入口頁 brain-entry-page，視窗 375×812
   * @given 攔截層同第 01 點；視窗設為 375×812
   * @step 開啟 / | `brain-entry-page` 可見
   * @step 量測 document.documentElement 的 scrollWidth 與 clientWidth | `scrollWidth` 不得大於 `clientWidth`（375）
   * @pass 375px 寬度下文件寬度不超出視窗，且隔離記錄為空
   * @story N-9
   * @note 對應 stories.md 的 AC-A11Y.2（C-06）。不跑 axe。
   */
  test('19 手機寬度入口頁無橫向捲動', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    const iso = await isolate(page);
    await SCANS.entry.stage(page);
    await ready(page, SCANS.entry);
    const size = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(size.scrollWidth, `375px 寬度下文件橫向溢出：${JSON.stringify(size)}`).toBeLessThanOrEqual(size.clientWidth);
    assertIsolated(iso);
  });

  /**
   * @purpose 入口頁在大腦連線完成、脈絡列為 default 時通過 WCAG 2.1 AA 自動掃描（第 01 點只涵蓋連線中狀態）。
   * @ui / | 入口頁 brain-entry-page；脈絡列 brain-context-bar（data-state=default）與名稱節點、工作項
   * @given 攔截層同第 01 點；大腦 WebSocket 在收到 hello 後送出握手快照（ready、兩則 sharing_mode、帶專案與系統的 work_target、一個進行中的工作項）
   * @step 開啟 / | `brain-context-bar` 的 data-state 為 `default`，`brain-context-name-project` 可見
   * @step 檢查連線中骨架 | 標籤「連線中」的節點數為 0，`brain-context-none` 不存在
   * @step 以 WCAG 2.1 AA 規則集掃描整頁 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story N-9
   * @note 審查 review-01 R-01：第 01、13、14、19 點都停在連線中，已連線後的入口頁 UI 從未被掃過；排除項「連線中」
   *       讓握手快照沒送到時這一點在就緒層紅，而不是掃完降級畫面後綠。
   */
  test('20 入口頁已連線狀態', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.entryConnected);
  });

  /**
   * @purpose 已連線入口頁上開啟的「切換對象」選單（含預設展開的群組與停用的非擁有者群組）通過 WCAG 2.1 AA 自動掃描（U16 OPN-07、N-06）。
   * @ui / | 入口頁脈絡列上的切換對象選單 brain-object-picker
   * @given 攔截層同第 20 點；/api/auth/me 另帶 K2 view＋edit；/api/hierarchy 回三個專案（作業對象所在的 17 自有並有系統 170、他人擁有的 18、自有的 19）
   * @step 點 brain-context-switch-object | 選單內 brain-object-item-170、brain-object-not-owned-18 與「+ 新增專案」可見，專案 17 的展開鈕 aria-expanded 為 true
   * @step 以 include 限縮到選單並以 WCAG 2.1 AA 規則集掃描 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story US9.2
   * @note U16 新增（OPN-23：修改已交付的 U17 檔案，只加掃描點）。include 限縮到 dialog，頁面其餘部分已由第 20 點掃過。
   */
  test('21 切換對象選單預設態', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.pickerDefault);
  });

  /**
   * @purpose 「切換對象」選單內的建立表單在顯示錯誤時通過 WCAG 2.1 AA 自動掃描（U16 OPN-07、N-06）。
   * @ui / | 切換對象選單的建立表單 brain-object-create-name 與錯誤文字 brain-object-create-error
   * @given 同第 21 點；POST /api/hierarchy/projects 回 409
   * @step 開啟選單、點「+ 新增專案」、輸入名稱並送出 | brain-object-create-error 可見，名稱欄仍在
   * @step 以 include 限縮到選單並以 WCAG 2.1 AA 規則集掃描 | 基準清單以外的違規為 0
   * @pass 就緒斷言成立、基準以外違規為 0、隔離記錄為空
   * @story US9.2
   */
  test('22 切換對象選單建立錯誤態', async ({ page }, testInfo) => {
    await runScan(page, testInfo, SCANS.pickerCreateError);
  });

  /**
   * @purpose 基準清單只收頁殼既有違規：不得收新元件節點、不得收交界類規則、每筆須有說明；且每個掃描點都有就緒斷言。
   * @ui / | 不開瀏覽器頁面；檢查 tests/e2e/a11y-baseline.json 與本檔的掃描點定義
   * @given a11y-baseline.json 存在
   * @step 檢查每筆選擇器 | 不含新元件根節點的 test-id、新元件 test-id 前綴、Sidebar 三個新增項的特徵或橫幅外層（規則 1）
   * @step 檢查每筆 reason | 非空（規則 4）
   * @step 檢查每筆規則 id | 不在交界類規則清單內（規則 5）
   * @step 檢查每個掃描點的就緒清單 | 至少一項（M12）
   * @pass 四項檢查皆無違反
   * @story N-9
   * @note 選擇器字串比對只擋得住寫明根節點的條目；根節點子孫的條目由掃描層的執行期 closest() 判定擋下。
   */
  test('基準清單只收頁殼既有違規', async () => {
    const baseline = loadBaseline();
    expect(Array.isArray(baseline.entries), 'a11y-baseline.json 須有 entries 陣列').toBe(true);
    const problems: string[] = [];
    for (const e of baseline.entries) {
      const marker = NEW_ROOT_STRING_MARKERS.find((m) => e.selector.includes(m));
      if (marker) problems.push(`規則 1：${e.rule} ${e.selector} 落在新元件（${marker}）`);
      if (!e.reason || e.reason.trim() === '') problems.push(`規則 4：${e.rule} ${e.selector} 缺 reason`);
      if (BOUNDARY_RULES.includes(e.rule)) problems.push(`規則 5：${e.rule} 屬交界類規則，不得進基準`);
      if (/nth-child|nth-of-type/.test(e.selector)) problems.push(`C-03：${e.selector} 是位置型選擇器`);
    }
    for (const def of ALL_SCANS) {
      if (def.ready.length === 0) problems.push(`M12：掃描點 ${def.id} 的就緒清單為空`);
    }
    expect(problems).toEqual([]);
  });

  /**
   * @purpose 基準清單只准縮小：任何一筆在全部掃描點都沒有出現時判為過期並讓測試失敗。
   * @ui / | 不開瀏覽器頁面；讀回 21 個掃描點寫出的結果檔
   * @given 本檔前 21 個掃描 test 已執行完畢（fullyParallel: false 的檔內順序；本檔必須整檔執行，不得 -g 或 shard）
   * @step 讀回結果目錄中的掃描結果檔 | 恰為 21 檔
   * @step 對照 a11y-baseline.json | 每筆至少在一個掃描點出現
   * @pass 檔數為 21，且沒有過期條目
   * @story N-9
   * @note 寫檔而非記憶體集合：test 失敗後 worker 會被丟棄重啟，記憶體集合只剩後半段（security-design.md 第五節，突變 M7／M10）。
   */
  test('基準清單沒有過期條目', async () => {
    const dir = resultsDir(test.info());
    const files = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.json')) : [];
    const expected = ALL_SCANS.map((d) => `${d.id}.json`).sort();
    expect(files.sort(), '掃描結果檔不足：有掃描點沒跑完，過期判定無效').toEqual(expected);
    const seen = new Set<string>();
    for (const f of files) {
      const data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf-8')) as { entries: SeenEntry[] };
      for (const e of data.entries) if (e.selector) seen.add(keyOf(e.rule, e.selector));
    }
    const stale = loadBaseline().entries.filter((e) => !seen.has(keyOf(e.rule, e.selector)));
    expect(stale, '基準清單有過期條目（已不再出現），請刪除').toEqual([]);
  });
});
