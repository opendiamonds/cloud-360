import { test, expect, type Page, type WebSocketRoute } from '@playwright/test';
import * as F from '../../src/brain/testing/wsFrames';

// U14 entry page — 攔截層（BR98.4）。
//
// `page.routeWebSocket('**/api/brain/ws')` 扮演大腦伺服器；`page.route` 攔截全部 HTTP（`/api/auth/me` 控制
// 權限、子頁面既有的圖清單／bootstrap／圖讀取）與 draw.io 內嵌頁（以一個最小替身回應 init／load／autosave）。
// 不碰真實後端、Redis、LLM 或 n8n。
//
// **伺服器訊框只由 `src/brain/testing/wsFrames.ts` 的建構器產生**（受 tsc -b 檢查；本檔內不得出現同時含
// type 與 payload 鍵的物件字面量，eslint 的 tests 區塊機械化擋下，EPN-19）。
//
// 執行方式：前端以同源方式被服務（`BASE_URL`；API 與 WS 皆指向同一個 origin，由本檔攔截）。真實 stack 層
// 見 entry-page-live.spec.ts。

const M = 'e2e-u14';
const VIEW_EDIT = { view: true, edit: true, review: false };

type ClientFrame = { type: string; payload: Record<string, unknown> };

interface BrainConn {
  ws: WebSocketRoute;
  url: string;
  frames: ClientFrame[];
  closed: boolean;
}

interface Target {
  pid: string | null;
  sid: string | null;
  did: string | null;
}

const NO_TARGET: Target = { pid: null, sid: null, did: null };

/**
 * 有狀態的假大腦伺服器：hello → 快照；set_work_target／set_sharing_mode → 更新狀態並扇出到全部存活連線
 * （與 `brain_gateway` 的語意相同，讓跨頁一致性可被觀察）。名稱以 `names`（p1／s2／d3 為鍵）查得。
 */
class BrainServer {
  conns: BrainConn[] = [];
  /** accept：正常握手；reject：建立即以 rejectCode 關閉（模擬握手未被接受）。 */
  mode: 'accept' | 'reject' = 'accept';
  rejectCode = 1011;
  /** false 時收到 hello 不自動送快照（由測試呼叫 sendSnapshot，模擬「快照後到」）。 */
  autoSnapshot = true;
  /** 非 null 時 ready 改送這個協定版本（BR92.2 的版本不符）。 */
  readyVersion: number | null = null;
  echo = true;
  shared: Target = { ...NO_TARGET };
  isolated: { workspace: Target; assessment: Target } = { workspace: { ...NO_TARGET }, assessment: { ...NO_TARGET } };
  modes: { workspace: 'shared' | 'isolated'; assessment: 'shared' | 'isolated' } = { workspace: 'shared', assessment: 'shared' };
  items = [] as ReturnType<typeof F.workItem>[];
  names: Record<string, string> = {};

  async install(page: Page): Promise<void> {
    // 以正規式比對（含查詢字串）：token 若被放進網址，連線仍被攔下，由網址斷言抓到（F4）。
    await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, (ws) => {
      const conn: BrainConn = { ws, url: ws.url(), frames: [], closed: false };
      this.conns.push(conn);
      ws.onClose(() => {
        conn.closed = true;
      });
      if (this.mode === 'reject') {
        conn.closed = true;
        void ws.close({ code: this.rejectCode });
        return;
      }
      ws.onMessage((raw) => {
        const data = JSON.parse(String(raw)) as ClientFrame;
        conn.frames.push(data);
        if (data.type === 'hello' && this.autoSnapshot) this.sendSnapshot(conn);
        if (data.type === 'set_work_target' && this.echo) {
          const p = data.payload as { projectId: string | null; systemId: string | null; diagramId: string | null; segment: string };
          const t: Target = { pid: p.projectId, sid: p.systemId, did: p.diagramId };
          if (p.segment === 'shared') this.shared = t;
          else this.isolated[p.segment as 'workspace' | 'assessment'] = t;
          this.broadcast(this.targetFrame(p.segment as 'shared' | 'workspace' | 'assessment'));
        }
        if (data.type === 'set_sharing_mode' && this.echo) {
          const p = data.payload as { mode: 'shared' | 'isolated'; scope: 'workspace' | 'assessment' };
          this.modes[p.scope] = p.mode;
          this.broadcast(F.encodeFrame(F.sharingModeFrame(p.scope, p.mode)));
          this.broadcast(this.targetFrame(p.mode === 'isolated' ? p.scope : 'shared'));
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

  sendSnapshot(conn: BrainConn = this.last): void {
    if (this.readyVersion !== null) {
      conn.ws.send(F.readyWithVersionFrame(this.readyVersion));
      return;
    }
    const iso = (['workspace', 'assessment'] as const)
      .filter((s) => this.modes[s] === 'isolated')
      .map((s) => {
        const t = this.isolated[s];
        return F.workTargetFrame(s, t.pid, t.sid, t.did, this.name('p', t.pid), this.name('s', t.sid), this.name('d', t.did));
      });
    const t = this.shared;
    const sharedFrame = F.workTargetFrame('shared', t.pid, t.sid, t.did, this.name('p', t.pid), this.name('s', t.sid), this.name('d', t.did));
    for (const f of F.snapshotFrames(sharedFrame, this.items, this.modes.workspace, this.modes.assessment, iso)) conn.ws.send(f);
  }

  get last(): BrainConn {
    return this.conns[this.conns.length - 1];
  }

  open(): BrainConn[] {
    return this.conns.filter((c) => !c.closed);
  }

  send(frames: string | string[], conn: BrainConn = this.last): void {
    for (const f of Array.isArray(frames) ? frames : [frames]) conn.ws.send(f);
  }

  broadcast(frame: string): void {
    for (const c of this.open()) c.ws.send(frame);
  }

  framesOf(type: string): ClientFrame[] {
    return this.conns.flatMap((c) => c.frames.filter((f) => f.type === type));
  }
}

interface DiagramStub {
  id: number;
  title: string;
  owner?: boolean;
}

interface SetupOptions {
  perms?: string[];
  pending?: boolean;
  meOmitId?: boolean;
  /** 依呼叫次序回應 /api/auth/me 的權限（用完後沿用最後一個）。 */
  permsSequence?: string[][];
  loggedIn?: boolean;
  diagrams?: DiagramStub[];
  listStatus?: number;
  bootstrapId?: number | null;
  /** bootstrap 回應在這個 promise 完成前不送出（控制快照先到／後到）。 */
  bootstrapGate?: Promise<void>;
}

interface Harness {
  server: BrainServer;
  apiRequests: string[];
  canvasLoads: () => Promise<string[]>;
  editCanvas: (xml: string) => Promise<void>;
}

const ALL_PERMS = ['K1', 'A1', 'A3', 'C1', 'K2', 'J3a'];

function permissions(ids: string[]): Record<string, typeof VIEW_EDIT> {
  return Object.fromEntries(ids.map((id) => [id, VIEW_EDIT]));
}

function diagramXml(id: number): string {
  return `<mxGraphModel><root><mxCell id="${M}-d${id}"/></root></mxGraphModel>`;
}

const FAKE_DRAWIO = `<!doctype html><html><body><script>
window.__loads = [];
window.addEventListener('message', function (e) {
  try { var d = JSON.parse(e.data); if (d.action === 'load') window.__loads.push(d.xml); } catch (err) {}
});
window.__edit = function (xml) { parent.postMessage(JSON.stringify({ event: 'autosave', xml: xml }), '*'); };
parent.postMessage(JSON.stringify({ event: 'init' }), '*');
</script></body></html>`;

async function setup(page: Page, opts: SetupOptions = {}): Promise<Harness> {
  const server = new BrainServer();
  const apiRequests: string[] = [];
  const diagrams = opts.diagrams ?? [];
  let meCalls = 0;

  page.on('request', (req) => {
    const url = new URL(req.url());
    if (url.pathname.startsWith('/api/')) apiRequests.push(`${req.method()} ${url.pathname}`);
  });
  if (opts.loggedIn !== false) {
    await page.addInitScript(() => {
      sessionStorage.setItem('token', 'e2e-u14-token');
    });
  }
  // 後註冊者優先：先放兜底，再放具體端點。
  await page.route('**/api/**', async (route) => {
    const method = route.request().method();
    await route.fulfill({ status: 200, contentType: 'application/json', body: method === 'GET' ? '[]' : '{}' });
  });
  await page.route('**/api/auth/me', async (route) => {
    const seq = opts.permsSequence;
    const ids = seq ? seq[Math.min(meCalls, seq.length - 1)] : opts.perms ?? ALL_PERMS;
    meCalls += 1;
    const body: Record<string, unknown> = {
      username: `${M}-alice`,
      role: 'Platform_Admin',
      is_active: true,
      authorization_status: opts.pending ? 'pending' : 'approved',
      permissions: permissions(ids),
      pending_request: null,
    };
    if (!opts.meOmitId) body.id = 7;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  const detail = (d: DiagramStub) => ({
    id: d.id,
    title: d.title,
    xml_data: diagramXml(d.id),
    is_owner: d.owner !== false,
    shared_user_ids: [],
    updated_at: '2026-10-17T00:00:00Z',
  });
  await page.route('**/api/collab/diagrams', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    if (opts.listStatus && opts.listStatus !== 200) {
      await route.fulfill({ status: opts.listStatus, contentType: 'application/json', body: '{"detail":"nope"}' });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(diagrams.map(detail)) });
  });
  await page.route(/\/api\/collab\/diagrams\/\d+$/, async (route) => {
    const id = Number(new URL(route.request().url()).pathname.split('/').pop());
    const d = diagrams.find((x) => x.id === id);
    if (route.request().method() === 'GET' && d) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(detail(d)) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
  await page.route('**/api/collab/workspace/bootstrap', async (route) => {
    if (opts.bootstrapGate) await opts.bootstrapGate;
    const d = diagrams.find((x) => x.id === opts.bootstrapId);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ diagram: d ? detail(d) : null, messages: [] }),
    });
  });
  await page.route('https://embed.diagrams.net/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'text/html', body: FAKE_DRAWIO });
  });
  await page.routeWebSocket('**/api/collab/ws/**', () => undefined);
  await server.install(page);

  const drawioFrame = () => page.frames().find((f) => f.url().includes('embed.diagrams.net'));
  return {
    server,
    apiRequests,
    canvasLoads: async () => {
      const frame = drawioFrame();
      if (!frame) return [];
      return frame.evaluate(() => (window as unknown as { __loads: string[] }).__loads.slice());
    },
    editCanvas: async (xml: string) => {
      const frame = drawioFrame();
      if (!frame) throw new Error('draw.io frame not found');
      await frame.evaluate((x) => (window as unknown as { __edit: (v: string) => void }).__edit(x), xml);
    },
  };
}

async function waitReady(page: Page): Promise<void> {
  await expect(page.getByTestId('brain-context-bar').first()).not.toHaveAttribute('data-state', 'connecting');
}

/** 對話區（LiveRegion 會重複完成的全文，文字查詢一律限定在對話區內）。 */
function conv(page: Page) {
  return page.getByTestId('brain-conversation');
}

async function say(page: Page, text: string): Promise<void> {
  await page.getByTestId('brain-input').fill(text);
  await page.getByTestId('brain-send').click();
}

test.describe('U14 entry page', () => {
  /**
   * @purpose 具 K1 的已核准使用者造訪 / 直接看到入口頁；未核准帳號即使權限表帶 K1 也必須先到等待授權頁（AC1.4.3 要防的形狀）。
   * @ui / | 入口頁 brain-entry-page
   * @ui /waiting-approval | 等待授權頁
   * @given 兩種 /api/auth/me：已核准且具 K1；authorization_status=pending 且權限表帶 K1
   * @step 已核准者開啟 / | 網址停在 /、brain-entry-page 可見
   * @step pending 者開啟 / | 導向 /waiting-approval，brain-entry-page 不存在
   * @pass 已核准者落在入口頁、pending 者落在等待授權頁
   * @story US1.4
   */
  test('K1 使用者落在入口頁且 isPending 優先', async ({ page, browser }) => {
    await setup(page);
    await page.goto('/');
    await expect(page.getByTestId('brain-entry-page')).toBeVisible();
    await expect(page).toHaveURL(/\/$/);

    const ctx = await browser.newContext();
    const pending = await ctx.newPage();
    await setup(pending, { pending: true });
    await pending.goto('/');
    await expect(pending).toHaveURL(/\/waiting-approval$/);
    await expect(pending.getByTestId('brain-entry-page')).toHaveCount(0);
    await ctx.close();
  });

  /**
   * @purpose 不具 K1 者的落地與 Sidebar 與本單元上線前相同；全無權限仍落 /403（BR91.2）。
   * @ui /workspace | 既有工作區
   * @ui /403 | 無權限頁
   * @given 只有 A1 的使用者；以及沒有任何權限的使用者
   * @step 只有 A1 者開啟 / | 導向 /workspace，Sidebar 無 sidebar-entry-link，大腦連線 0 條
   * @step 全無權限者開啟 / | 導向 /403
   * @pass 兩案落點與既有瀑布相同
   * @story US1.4
   */
  test('無 K1 走既有瀑布且全無權限落 403', async ({ page, browser }) => {
    const h = await setup(page, { perms: ['A1'] });
    await page.goto('/');
    await expect(page).toHaveURL(/\/workspace$/);
    await expect(page.getByTestId('sidebar-entry-link')).toHaveCount(0);
    expect(h.server.conns.length).toBe(0);

    const ctx = await browser.newContext();
    const none = await ctx.newPage();
    await setup(none, { perms: [] });
    await none.goto('/');
    await expect(none).toHaveURL(/\/403$/);
    await ctx.close();
  });

  /**
   * @purpose 打錯的網址導回 /，再由落地判斷決定落點（網址列與畫面一致，BR91.3）。
   * @ui / | 入口頁
   * @given 具 K1 的使用者
   * @step 開啟 /e2e-u14-not-a-page | 網址被改寫為 /
   * @step 檢視畫面 | brain-entry-page 可見
   * @pass 不存在的路徑導回 / 並顯示入口頁
   * @story US1.4
   */
  test('不存在的路徑導回入口', async ({ page }) => {
    await setup(page);
    await page.goto(`/${M}-not-a-page`);
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByTestId('brain-entry-page')).toBeVisible();
  });

  /**
   * @purpose Sidebar 的「入口」為置頂的第一層獨立項並標示目前頁；入口頁的記憶捷徑與 Sidebar 用同一判定（BR91.4、BR91.5）。
   * @ui / | Sidebar「入口」、入口頁頁首「我的記憶」捷徑
   * @given 全權限使用者
   * @step 開啟 / | sidebar-entry-link 的 aria-current 為 page
   * @step 比較位置 | 「入口」在「專案」與各群組之上
   * @step 檢視記憶入口 | brain-memory-shortcut 與 sidebar-memory-link 皆可見，捷徑連到 /memory
   * @pass 入口置頂且標示目前頁、兩個記憶入口同時出現
   * @story US1.4
   */
  test('Sidebar 入口置頂並帶 aria-current', async ({ page }) => {
    await setup(page);
    await page.goto('/');
    const entry = page.getByTestId('sidebar-entry-link');
    await expect(entry).toHaveAttribute('aria-current', 'page');
    const entryBox = await entry.boundingBox();
    const projectsBox = await page.getByTestId('sidebar-projects-link').boundingBox();
    const archBox = await page.getByRole('button', { name: '架構', exact: true }).boundingBox();
    expect(entryBox && projectsBox && archBox).toBeTruthy();
    expect(entryBox!.y).toBeLessThan(projectsBox!.y);
    expect(entryBox!.y).toBeLessThan(archBox!.y);
    await expect(page.getByTestId('brain-memory-shortcut')).toHaveAttribute('href', '/memory');
    await expect(page.getByTestId('sidebar-memory-link')).toBeVisible();
  });

  /**
   * @purpose 連線網址不帶任何查詢參數與 token、開啟後先送 hello；ready 的協定版本不符時顯示「版本不相容」且不重試（BR92.1、BR92.2、AC8.1.3）。
   * @ui / | 入口頁 brain-connection-notice
   * @given /api/brain/ws 由測試扮演；第一次正常、第二次 ready 帶 protocolVersion=2
   * @step 開啟 / | 大腦連線網址以 /api/brain/ws 結尾、不含 ? 與 token；第一則客戶端訊框為 hello{v:1}
   * @step 改為版本不符後重新載入 | 出現「版本不相容，請重新整理頁面」
   * @step 快轉 20 秒 | 沒有新的大腦連線
   * @pass 網址乾淨、先送 hello、版本不符即終止
   * @story US8.1
   */
  test('連線網址不含 token、先送 hello、版本不符不重試', async ({ page }) => {
    const h = await setup(page);
    await page.clock.install();
    await page.goto('/');
    await waitReady(page);
    const conn = h.server.conns[0];
    expect(conn.url).toMatch(/\/api\/brain\/ws$/);
    expect(conn.url).not.toContain('?');
    expect(conn.url).not.toContain('token');
    expect(conn.frames[0].type).toBe('hello');
    expect(conn.frames[0].payload).toMatchObject({ v: 1 });

    h.server.readyVersion = 2;
    await page.reload();
    await expect(page.getByTestId('brain-connection-notice')).toContainText('版本不相容，請重新整理頁面');
    const count = h.server.conns.length;
    await page.clock.runFor(20_000);
    expect(h.server.conns.length).toBe(count);
  });

  /**
   * @purpose 每頁至多一條大腦連線；換頁即關閉舊頁的連線（EPN-01）。
   * @ui / | 入口頁
   * @ui /workspace | 工作區脈絡列
   * @ui /assessment | 評核頁脈絡列
   * @given 全權限使用者，三頁各自掛大腦連線
   * @step 經 Sidebar 在入口、工作區、評核頁之間切換 5 次 | 每次換頁後連線數穩定
   * @step 計算未關閉的大腦連線 | 恰 1 條
   * @pass 切換 5 次後未關閉的連線恰 1 條
   * @story US8.1
   */
  test('三頁切換後未關閉的大腦連線恰一條', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    const hops = ['/workspace', '/assessment', '/', '/workspace', '/'];
    for (const path of hops) {
      const before = h.server.conns.length;
      if (path === '/') await page.getByTestId('sidebar-entry-link').click();
      else await page.locator(`a[href="${path}"]`).first().click();
      await expect(page).toHaveURL(new RegExp(`${path === '/' ? '/' : path}$`));
      await expect.poll(() => h.server.conns.length, { message: `hop ${path}` }).toBe(before + 1);
      await waitReady(page);
    }
    await expect.poll(() => h.server.open().length).toBe(1);
    expect(h.server.conns.length).toBe(hops.length + 1);
  });

  /**
   * @purpose 4401 與 4400 是終止碼：顯示對應提示且不自動重連（BR92.5、EPN-03）。
   * @ui / | 入口頁 brain-connection-notice
   * @given /api/brain/ws 握手完成後以 4401 關閉；另一次以 4400 關閉
   * @step 伺服器以 4401 關閉 | 出現「連線已失效，請重新登入」與「重新登入」鈕
   * @step 快轉 20 秒 | 新連線 0 條
   * @step 重新載入後伺服器以 4400 關閉 | 出現「版本不相容」；快轉 20 秒新連線 0 條
   * @pass 兩個終止碼皆不重連
   * @story US8.1
   */
  test('4401 與 4400 不重連', async ({ page }) => {
    const h = await setup(page);
    await page.clock.install();
    await page.goto('/');
    await waitReady(page);
    await h.server.last.ws.close({ code: 4401 });
    await expect(page.getByTestId('brain-connection-notice')).toContainText('連線已失效，請重新登入');
    await expect(page.getByTestId('brain-relogin')).toBeVisible();
    let count = h.server.conns.length;
    await page.clock.runFor(20_000);
    expect(h.server.conns.length).toBe(count);

    await page.reload();
    await waitReady(page);
    await h.server.last.ws.close({ code: 4400 });
    await expect(page.getByTestId('brain-connection-notice')).toContainText('版本不相容');
    count = h.server.conns.length;
    await page.clock.runFor(20_000);
    expect(h.server.conns.length).toBe(count);
  });

  /**
   * @purpose 全部握手被拒時以有上限的退避重連：每次間隔落在排程 ×[0.8, 1.0]、累計 60 秒才放棄、放棄後零自動嘗試，只由「重新連線」重來（EPN-02）。
   * @ui / | 入口頁 brain-connection-notice
   * @given /api/brain/ws 每次建立即以 1011 關閉；頁面時鐘由 page.clock 控制
   * @step 逐次快轉 0.8×排程 | 期間沒有新連線
   * @step 再快轉 0.2×排程 | 恰出現一條新連線（直到累計滿 60 秒）
   * @step 首次失敗後 60 秒內 | 不出現「無法連線到大腦」
   * @step 放棄後快轉 60 秒 | 新連線 0 條；按「重新連線」 | 恰一條新連線
   * @pass 間隔、放棄判準與放棄後行為皆符合排程
   * @story US8.1
   */
  test('退避重連依排程且累計六十秒後放棄', async ({ page }) => {
    const h = await setup(page);
    h.server.mode = 'reject';
    // 時鐘暫停：只由 runFor 推進，避免真實時間讓第一次重試提早發生。
    const t0 = new Date('2026-10-17T00:00:00Z');
    await page.clock.install({ time: t0 });
    await page.clock.pauseAt(new Date(t0.getTime() + 1000));
    await page.goto('/');
    await expect.poll(() => h.server.conns.length).toBe(1);
    const base = [1, 2, 4, 8, 15, 15, 15, 15, 15];
    let elapsed = 0;
    let n = 0;
    while (true) {
      const b = base[Math.min(n, base.length - 1)] * 1000;
      const before = h.server.conns.length;
      await page.clock.runFor(Math.floor(b * 0.8) - 20);
      expect(h.server.conns.length).toBe(before);
      if (elapsed < 60_000) await expect(page.getByTestId('brain-connection-notice')).toHaveCount(0);
      await page.clock.runFor(Math.ceil(b * 0.2) + 40);
      elapsed += b;
      const gaveUp = await page.getByTestId('brain-connection-notice').count();
      if (gaveUp) break;
      await expect.poll(() => h.server.conns.length).toBe(before + 1);
      n += 1;
      expect(n).toBeLessThan(12);
    }
    await expect(page.getByTestId('brain-connection-notice')).toContainText('無法連線到大腦');
    expect(h.server.conns.length).toBeGreaterThanOrEqual(8);
    expect(h.server.conns.length).toBeLessThanOrEqual(9);
    const settled = h.server.conns.length;
    await page.clock.runFor(60_000);
    expect(h.server.conns.length).toBe(settled);
    h.server.mode = 'accept';
    await page.getByTestId('brain-reconnect').click();
    await expect.poll(() => h.server.conns.length).toBe(settled + 1);
  });

  /**
   * @purpose 入口頁收到 4403 時不導航、只刷新一次權限；K1 已被撤銷 → 依既有瀑布落到 /workspace，且該頁不開大腦連線（security-design §六之二 案 1）。
   * @api GET /api/auth/me -> 200 | 第二次回應不含 K1
   * @ui / | 入口頁
   * @ui /workspace | 工作區
   * @given 第一次 /me 具 K1＋A1；第二次只有 A1；/api/brain/ws 握手後以 4403 關閉
   * @step 開啟 / 並等連線就緒 | 入口頁可見
   * @step 伺服器以 4403 關閉 | 頁面落到 /workspace
   * @step 檢視工作區 | 無 brain-context-bar，大腦連線總數仍為 1
   * @pass 4403 後依新權限落地、無新連線
   * @story US1.4
   */
  test('入口頁 4403 且 K1 已撤銷時落到工作區', async ({ page }) => {
    const h = await setup(page, { permsSequence: [['K1', 'A1'], ['A1']] });
    await page.goto('/');
    await waitReady(page);
    await h.server.last.ws.close({ code: 4403 });
    await expect(page).toHaveURL(/\/workspace$/);
    await expect(page.getByTestId('brain-context-bar')).toHaveCount(0);
    expect(h.server.conns.length).toBe(1);
  });

  /**
   * @purpose 子頁面收到 4403 不得導航（照 BR92.5 字面會形成無限迴圈並丟掉畫布）；K1 撤銷後大腦掛點卸載、頁面本身與畫布不變（security-design §六之二 案 2）。
   * @api GET /api/auth/me -> 200 | 第二次回應不含 K1
   * @ui /workspace | 工作區脈絡列與「問大腦」面板
   * @given 第一次 /me 具 K1＋A1；第二次只有 A1；bootstrap 開啟自有圖 11
   * @step 開啟 /workspace 並等連線就緒 | 脈絡列與面板可見、畫布載入圖 11
   * @step 伺服器以 4403 關閉 | pathname 仍為 /workspace
   * @step 檢視掛點、導航紀錄與畫布 | 脈絡列與面板消失；4403 之後沒有任何 history 變更、沒有新的大腦連線；畫布載入紀錄不變
   * @pass 不導航、掛點卸載、畫布不受影響
   * @story US3.1
   */
  test('工作區 4403 且 K1 撤銷時不導航並卸載掛點', async ({ page }) => {
    const h = await setup(page, {
      permsSequence: [['K1', 'A1'], ['A1']],
      diagrams: [{ id: 11, title: `${M}-圖11` }],
      bootstrapId: 11,
    });
    await page.goto('/workspace');
    await waitReady(page);
    await expect(page.getByTestId('brain-subpage-panel')).toBeVisible();
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d11`);
    const loadsBefore = await h.canvasLoads();
    // 記錄 4403 之後的每一次 history 變更：最終回到 /workspace 不足以證明沒有導航過。
    await page.evaluate(() => {
      const w = window as unknown as { __paths: string[] };
      w.__paths = [];
      for (const fn of ['pushState', 'replaceState'] as const) {
        const orig = history[fn].bind(history);
        history[fn] = (...args: Parameters<History['pushState']>) => {
          orig(...args);
          w.__paths.push(location.pathname);
        };
      }
    });
    await h.server.last.ws.close({ code: 4403 });
    await expect(page.getByTestId('brain-context-bar')).toHaveCount(0);
    await expect(page.getByTestId('brain-subpage-panel')).toHaveCount(0);
    await expect(page).toHaveURL(/\/workspace$/);
    expect(await page.evaluate(() => (window as unknown as { __paths: string[] }).__paths)).toEqual([]);
    expect(h.server.conns.length).toBe(1);
    expect(await h.canvasLoads()).toEqual(loadsBefore);
  });

  /**
   * @purpose 子頁面 4403 而伺服器與 /me 不一致（/me 仍有 K1）時，顯示終止提示且不重連（security-design §六之二 案 3、EPN-03）。
   * @api GET /api/auth/me -> 200 | 仍具 K1
   * @ui /workspace | 工作區脈絡列
   * @given /me 一直具 K1＋A1；/api/brain/ws 握手後以 4403 關閉
   * @step 開啟 /workspace 並等連線就緒 | 脈絡列可見
   * @step 伺服器以 4403 關閉 | 脈絡列 data-state 為 unavailable 並顯示「你目前沒有使用大腦的權限」
   * @step 快轉 20 秒 | 新連線 0 條
   * @pass 提示出現且不重連
   * @story US3.1
   */
  test('工作區 4403 而仍有 K1 時顯示提示且不重連', async ({ page }) => {
    const h = await setup(page, { perms: ['K1', 'A1'] });
    await page.clock.install();
    await page.goto('/workspace');
    await waitReady(page);
    await h.server.last.ws.close({ code: 4403 });
    const bar = page.getByTestId('brain-context-bar');
    await expect(bar).toHaveAttribute('data-state', 'unavailable');
    await expect(bar).toContainText('你目前沒有使用大腦的權限');
    const count = h.server.conns.length;
    await page.clock.runFor(20_000);
    expect(h.server.conns.length).toBe(count);
  });

  /**
   * @purpose token 收到即顯示、不緩衝到 done；串流中 aria-busy 為真；done 後 LiveRegion 恰被寫入一次（NFR3.140、EPN-09、AC8.1.1）。
   * @ui / | 入口頁 brain-stream-message、LiveRegion
   * @given /api/brain/ws；入口頁已就緒，LiveRegion 掛有 MutationObserver 計數
   * @step 送出一句後，伺服器送兩個 token、不送 done | 兩段文字皆已可見；該則 aria-busy="true"；LiveRegion 為空
   * @step 伺服器送 done | aria-busy 消失；LiveRegion 文字等於全文、被寫入恰 1 次
   * @pass 收到即呈現、播報一次
   * @story US8.1
   */
  test('token 收到即呈現且完成時播報一次', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="brain-live"] [data-testid="live-region"]');
      const w = window as unknown as { __liveWrites: number };
      w.__liveWrites = 0;
      if (el) new MutationObserver(() => { w.__liveWrites += 1; }).observe(el, { childList: true, characterData: true, subtree: true });
    });
    await say(page, `${M}-hello`);
    h.server.send([F.encodeFrame(F.tokenFrame('t-12', `${M}-第一段`)), F.encodeFrame(F.tokenFrame('t-12', `${M}-第二段`))]);
    const msg = page.locator('[data-testid="brain-stream-message"][data-turn-id="t-12"]');
    await expect(msg).toContainText(`${M}-第一段${M}-第二段`);
    await expect(msg).toHaveAttribute('aria-busy', 'true');
    const live = page.getByTestId('brain-live').getByTestId('live-region');
    await expect(live).toHaveText('');
    h.server.send(F.encodeFrame(F.doneFrame('t-12')));
    await expect(msg).not.toHaveAttribute('aria-busy', 'true');
    await expect(live).toHaveText(`${M}-第一段${M}-第二段`);
    expect(await page.evaluate(() => (window as unknown as { __liveWrites: number }).__liveWrites)).toBe(1);
  });

  /**
   * @purpose 使用者偏好減少動態時，串流游標不得閃爍（EPN-09、BR93.6）。
   * @ui / | 入口頁 brain-stream-cursor
   * @given 以 reducedMotion: 'reduce' 模擬偏好；/api/brain/ws 送 token 不送 done
   * @step 送出一句、伺服器送一個 token | 游標可見
   * @step 讀游標的 computed animation-name | 為 none
   * @pass 減少動態時游標無動畫
   * @story US8.1
   */
  test('減少動態時游標不閃爍', async ({ page }) => {
    const h = await setup(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-motion`);
    h.server.send(F.encodeFrame(F.tokenFrame('t-13', `${M}-串流中`)));
    const cursor = page.getByTestId('brain-stream-cursor');
    await expect(cursor).toBeVisible();
    expect(await cursor.evaluate((el) => getComputedStyle(el).animationName)).toBe('none');
  });

  /**
   * @purpose 零內容的 done 是契約違規：顯示「沒有收到回覆」與重試，不留空白訊息（BR93.2）。
   * @ui / | 入口頁 brain-stream-message、brain-stream-retry
   * @given /api/brain/ws 對一輪只送 done
   * @step 送出一句、伺服器送 done（無 token） | 出現一則 data-status=empty 的訊息，文字「沒有收到回覆」
   * @step 檢視重試鈕 | brain-stream-retry 可見
   * @pass 空回覆以說明與重試呈現
   * @story US8.1
   */
  test('零內容 done 顯示沒有收到回覆', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-empty`);
    h.server.send(F.encodeFrame(F.doneFrame('t-14')));
    const msg = page.locator('[data-testid="brain-stream-message"][data-turn-id="t-14"]');
    await expect(msg).toHaveAttribute('data-status', 'empty');
    await expect(msg).toContainText('沒有收到回覆');
    await expect(msg.getByTestId('brain-stream-retry')).toBeVisible();
  });

  /**
   * @purpose 送出後在任一輪終止前不能再送；斷線時該輪轉為中斷、不自動重送，重試只在使用者按下時送一次（BR93.3、BR92.7）。
   * @ui / | 入口頁 brain-input、brain-send、brain-stream-retry
   * @given /api/brain/ws；第二句送出後伺服器以 1011 關閉、隨後重連成功
   * @step 送出第一句後在輸入列再打字 | 送出鈕停用
   * @step 伺服器送 done | 送出鈕恢復可用
   * @step 送出第二句、伺服器以 1011 關閉 | 該句下出現「回覆中斷」與重試
   * @step 等重連完成 | user_message 仍只有 2 則（不自動重送）
   * @step 按重試 | user_message 變為 3 則，重試鈕消失
   * @pass 等待、終止解除、中斷與單次重試皆成立
   * @story US8.1
   */
  test('送出鈕在終止前停用且斷線不自動重送', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-第一句`);
    await page.getByTestId('brain-input').fill(`${M}-還想再說`);
    await expect(page.getByTestId('brain-send')).toBeDisabled();
    h.server.send(F.turnFrames('t-15a', `${M}-好的`));
    await expect(page.getByTestId('brain-send')).toBeEnabled();
    await page.getByTestId('brain-input').fill(`${M}-第二句`);
    await page.getByTestId('brain-send').click();
    await h.server.last.ws.close({ code: 1011 });
    const interrupted = page.getByTestId('brain-user-message').filter({ hasText: `${M}-第二句` });
    await expect(interrupted).toContainText('回覆中斷');
    await expect.poll(() => h.server.conns.length).toBe(2);
    await waitReady(page);
    await expect(page.getByTestId('brain-context-bar')).toHaveAttribute('data-state', 'no-object');
    expect(h.server.framesOf('user_message').length).toBe(2);
    await interrupted.getByTestId('brain-stream-retry').click();
    await expect.poll(() => h.server.framesOf('user_message').length).toBe(3);
    await expect(interrupted.getByTestId('brain-stream-retry')).toHaveCount(0);
  });

  /**
   * @purpose 工作項在常駐區與對話流讀同一份集合、狀態相同；五個狀態以文字呈現並各帶說明，sideEffect 的 none／unknown／其他三種語意不混淆（BR94.1、BR94.3、AC1.1.1、AC5.1.2）。
   * @ui / | 入口頁 brain-workitem-dock、brain-workitem-list
   * @given /api/brain/ws 推送七個工作項（處理中、等待中、完成、失敗、三種已停掉）
   * @step 推送 work_items | 常駐區只有處理中與等待中兩項，狀態文字與對話流中同 id 者相同
   * @step 檢視等待中與失敗 | 「在等：…」與失敗原因各自顯示
   * @step 檢視三個已停掉 | 分別為「沒有留下任何東西」「不確定有沒有留下東西」與原樣字串
   * @pass 兩處狀態一致、說明文字正確
   * @story US1.1
   */
  test('工作項兩處同步且五狀態文字正確', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    h.server.send(
      F.encodeFrame(
        F.workItemsFrame(
          F.workItem('w1', `${M}-架構設計`, '處理中'),
          F.workItem('w2', `${M}-檢視`, '等待中', 'architecture-design', `${M}-等你確認`),
          F.workItem('w3', `${M}-完成項`, '完成'),
          F.workItem('w4', `${M}-失敗項`, '失敗', 'architecture-design', null, `${M}-失敗原因`),
          F.workItem('w5', `${M}-停掉一`, '已停掉', 'architecture-design', null, null, 'none'),
          F.workItem('w6', `${M}-停掉二`, '已停掉', 'architecture-design', null, null, 'unknown'),
          F.workItem('w7', `${M}-停掉三`, '已停掉', 'architecture-design', null, null, `${M}-留下一份草稿`),
        ),
      ),
    );
    const dock = page.getByTestId('brain-workitem-dock');
    const list = page.getByTestId('brain-workitem-list');
    await expect(dock.locator('li')).toHaveCount(2);
    for (const id of ['w1', 'w2']) {
      await expect(dock.getByTestId(`brain-workitem-${id}-status`)).toHaveText(
        (await list.getByTestId(`brain-workitem-${id}-status`).textContent()) ?? '',
      );
    }
    await expect(list.getByTestId('brain-workitem-w1-status')).toHaveText('處理中');
    await expect(list.getByTestId('brain-workitem-w2')).toContainText(`在等：${M}-等你確認`);
    await expect(list.getByTestId('brain-workitem-w3-status')).toHaveText('完成');
    await expect(list.getByTestId('brain-workitem-w4')).toContainText(`${M}-失敗原因`);
    await expect(list.getByTestId('brain-workitem-w5')).toContainText('沒有留下任何東西');
    await expect(list.getByTestId('brain-workitem-w6')).toContainText('不確定有沒有留下東西');
    await expect(list.getByTestId('brain-workitem-w6')).not.toContainText('沒有留下任何東西');
    await expect(list.getByTestId('brain-workitem-w7')).toContainText(`${M}-留下一份草稿`);
  });

  /**
   * @purpose 常駐區只列處理中與等待中、空集合不渲染、窄螢幕預設收合（BR94.2）。
   * @ui / | 入口頁 brain-workitem-dock
   * @given 寬度 600px 的視窗；/api/brain/ws 先推送只有「完成」的集合，再推送含處理中的集合
   * @step 推送只有完成項的 work_items | 常駐區不存在
   * @step 推送含一個處理中的 work_items | 常駐區出現、收合鈕 aria-expanded=false、清單不顯示
   * @step 展開 | 出現該處理中項
   * @pass 過濾、空集合與窄螢幕收合皆成立
   * @story US1.1
   */
  test('常駐區過濾且窄螢幕預設收合', async ({ page }) => {
    const h = await setup(page);
    await page.setViewportSize({ width: 600, height: 900 });
    await page.goto('/');
    await waitReady(page);
    h.server.send(F.encodeFrame(F.workItemsFrame(F.workItem('w1', `${M}-完成項`, '完成'))));
    await expect(page.getByTestId('brain-workitem-list')).toBeVisible();
    await expect(page.getByTestId('brain-workitem-dock')).toHaveCount(0);
    h.server.send(F.encodeFrame(F.workItemsFrame(F.workItem('w1', `${M}-完成項`, '完成'), F.workItem('w2', `${M}-進行`, '處理中'))));
    const toggle = page.getByTestId('brain-workitem-dock-toggle');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(toggle).toHaveText('進行中 (1)');
    await expect(page.getByTestId('brain-workitem-dock').getByTestId('brain-workitem-w2')).toHaveCount(0);
    await toggle.click();
    await expect(page.getByTestId('brain-workitem-dock').getByTestId('brain-workitem-w2')).toBeVisible();
  });

  /**
   * @purpose 「不是這個」只送一次、停用到下一則 work_items；已停掉的項與更正後的新項同時可見（BR94.4、BR94.5、AC1.3.1–AC1.3.3）。
   * @ui / | 入口頁 brain-workitem-{id}-reject
   * @given /api/brain/ws；一個處理中的工作項 w1
   * @step 按 w1 的「不是這個」兩次 | 只送出 1 則 correct_work_item{workItemId:w1}；按鈕停用
   * @step 伺服器推送 w1 已停掉、新項 w8 處理中 | 對話流中 w1（已停掉）與 w8（處理中）同時可見；w1 不再有「不是這個」
   * @pass 單次送出、等伺服器才改畫面、更正前後可對照
   * @story US1.3
   */
  test('不是這個只送一次且已停掉與新項同時可見', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-畫架構圖`);
    h.server.send(F.turnFrames('t-18', `${M}-已交辦`));
    h.server.send(F.encodeFrame(F.workItemsFrame(F.workItem('w1', `${M}-架構設計`, '處理中'))));
    const list = page.getByTestId('brain-workitem-list');
    const reject = list.getByTestId('brain-workitem-w1-reject');
    await expect(reject).toHaveAttribute('aria-label', `不是這個：${M}-架構設計`);
    await reject.click();
    await expect(reject).toBeDisabled();
    await reject.click({ force: true });
    expect(h.server.framesOf('correct_work_item')).toHaveLength(1);
    expect(h.server.framesOf('correct_work_item')[0].payload).toMatchObject({ workItemId: 'w1' });
    await expect(list.getByTestId('brain-workitem-w1-status')).toHaveText('處理中');
    h.server.send(
      F.encodeFrame(F.workItemsFrame(F.workItem('w1', `${M}-架構設計`, '已停掉'), F.workItem('w8', `${M}-檢視`, '處理中'))),
    );
    await expect(list.getByTestId('brain-workitem-w1-status')).toHaveText('已停掉');
    await expect(list.getByTestId('brain-workitem-w8-status')).toHaveText('處理中');
    await expect(list.getByTestId('brain-workitem-w1-reject')).toHaveCount(0);
  });

  /**
   * @purpose 意圖反問與對象反問的提示不同、不顯示信心值；選定只在使用者按下時送一次（BR95.1–BR95.4、AC1.2.1、AC1.2.2）。
   * @ui / | 入口頁 brain-clarify
   * @given /api/brain/ws 送 kind=intent 的反問（兩個候選，信心值 0.42），之後送 kind=target 的反問
   * @step 檢視意圖反問 | 提示「我不確定你指的是哪一件事」；畫面不含 0.42
   * @step 按候選 c1 兩次 | 只送 1 則 select_clarify_candidate{candidateId:c1}；整組停用
   * @step 伺服器送對象反問 | 提示「你指的是哪一個？」，與意圖反問不同
   * @pass 兩種提示不同、不顯示信心、選定一次
   * @story US1.2
   */
  test('意圖與對象反問提示不同且選定只送一次', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-幫我看看`);
    h.server.send(F.encodeFrame(F.clarifyFrame('t-19', 'intent', [['c1', `${M}-建一張架構圖`, 'A1'], ['c2', `${M}-檢視架構`, 'A3']])));
    const intentGroup = page.locator('[data-testid="brain-clarify"][data-kind="intent"]');
    await expect(intentGroup).toContainText('我不確定你指的是哪一件事');
    await expect(page.getByTestId('brain-entry-page')).not.toContainText('0.42');
    const c1 = intentGroup.getByTestId('brain-clarify-candidate-c1');
    await c1.click();
    await expect(c1).toBeDisabled();
    await c1.click({ force: true });
    expect(h.server.framesOf('select_clarify_candidate')).toHaveLength(1);
    expect(h.server.framesOf('select_clarify_candidate')[0].payload).toMatchObject({ candidateId: 'c1' });
    h.server.send(F.encodeFrame(F.clarifyFrame('t-19', 'target', [['target-1', `${M}-訂單系統（專案：電商）`, 'A1']])));
    const targetGroup = page.locator('[data-testid="brain-clarify"][data-kind="target"]');
    await expect(targetGroup).toContainText('你指的是哪一個？');
    await expect(targetGroup).not.toContainText('我不確定你指的是哪一件事');
  });

  /**
   * @purpose 回絕送 candidateId:null、焦點回輸入列、脈絡列不變；候選未決時送新句，舊組轉 stale（BR95.5、AC1.2.3）。
   * @ui / | 入口頁 brain-clarify-restate、brain-input、brain-context-bar
   * @given /api/brain/ws；作業對象為專案 1；伺服器送只有一個候選的對象反問
   * @step 按「都不是」 | 送出 select_clarify_candidate{candidateId:null}；輸入列取得焦點；脈絡列仍為專案 1
   * @step 伺服器再送一組反問，使用者直接送出新句 | 前一組 data-state 為 stale
   * @pass 回絕與 stale 皆成立
   * @story US1.2
   */
  test('回絕後焦點回輸入列且未決候選轉 stale', async ({ page }) => {
    const h = await setup(page);
    h.server.shared = { pid: '1', sid: null, did: null };
    h.server.names = { p1: `${M}-專案甲` };
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-改那個`);
    h.server.send(F.encodeFrame(F.clarifyFrame('t-20', 'target', [['target-1', `${M}-唯一候選`, 'A1']])));
    await page.getByTestId('brain-clarify-restate').click();
    expect(h.server.framesOf('select_clarify_candidate')[0].payload).toMatchObject({ candidateId: null });
    await expect(page.getByTestId('brain-input')).toBeFocused();
    await expect(page.getByTestId('brain-context-name-project')).toHaveText(`${M}-專案甲`);
    h.server.send(F.encodeFrame(F.clarifyFrame('t-20b', 'intent', [['c1', `${M}-甲`, 'A1']])));
    const second = page.getByTestId('brain-clarify').last();
    await expect(second).toHaveAttribute('data-state', 'default');
    await say(page, `${M}-換個說法`);
    await expect(second).toHaveAttribute('data-state', 'stale');
  });

  /**
   * @purpose 成本完成：徽章就地轉完成、卡片附在其後、三段文字與無法取價原因、連結取 costPageUrl；全程不換頁（BR96.1、BR96.3、BR94.7、AC10.1.1–AC10.1.4、NFR11.140）。
   * @ui / | 入口頁 brain-cost-card
   * @given /api/brain/ws；交辦一個成本工作項，之後伺服器發起輪次送 cost_card
   * @step 送出成本問題，伺服器回處理中工作項與交辦回覆 | 工作項徽章「處理中」
   * @step 伺服器推送完成、cost_card 與 done | 徽章轉「完成」、卡片出現在其後，含三段文字與「部分項目無法取價：storage」
   * @step 檢視連結 | href 等於 /cost?estimateSetId=5，文字含估價表 #5
   * @step 檢視主框架導航紀錄 | 首次載入後 pathname 變更 0 次
   * @pass 卡片內容正確且全程停在入口頁
   * @story US10.1
   */
  test('成本卡片附在完成的工作項之後且不換頁', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    const paths: string[] = [];
    page.on('framenavigated', (frame) => {
      if (frame === page.mainFrame()) paths.push(new URL(frame.url()).pathname);
    });
    await say(page, `${M}-每月要花多少`);
    h.server.send(F.encodeFrame(F.workItemsFrame(F.workItem('wc', `${M}-成本分析`, '處理中', 'cost-finops'))));
    h.server.send(F.turnFrames('t-21', `${M}-已交辦成本分析`));
    const list = page.getByTestId('brain-workitem-list');
    await expect(list.getByTestId('brain-workitem-wc-status')).toHaveText('處理中');
    h.server.send(F.encodeFrame(F.workItemsFrame(F.workItem('wc', `${M}-成本分析`, '完成', 'cost-finops'))));
    h.server.send([
      F.encodeFrame(F.costCardFrame('t-21c', 5, `${M}-可省一成`, `${M}-比上月低`, `${M}-品質不變`, ['storage'], '/cost?estimateSetId=5')),
      F.encodeFrame(F.doneFrame('t-21c')),
    ]);
    await expect(list.getByTestId('brain-workitem-wc-status')).toHaveText('完成');
    const card = page.getByTestId('brain-cost-card');
    await expect(card.getByTestId('brain-cost-card-text')).toContainText(`${M}-可省一成`);
    await expect(card.getByTestId('brain-cost-card-text')).toContainText(`${M}-比上月低`);
    await expect(card.getByTestId('brain-cost-card-text')).toContainText(`${M}-品質不變`);
    await expect(card).toContainText('部分項目無法取價：storage');
    await expect(card.getByTestId('brain-cost-card-link')).toHaveAttribute('href', '/cost?estimateSetId=5');
    await expect(card.getByTestId('brain-cost-card-link')).toContainText('估價表 #5');
    const listBox = await list.boundingBox();
    const cardBox = await card.boundingBox();
    expect(cardBox!.y).toBeGreaterThan(listBox!.y);
    expect(paths).toEqual([]);
  });

  /**
   * @purpose 成本逾時與失敗以不同的原因文字呈現；無 C1 權限時以失敗與伺服器的權限說明呈現（BR96.2、BR96.4、AC10.1.5、AC10.2.1、AC10.2.2、AC10.2.4）。
   * @ui / | 入口頁 brain-workitem-list
   * @given /api/brain/ws 推送三個失敗的成本工作項：逾時、失敗、權限不足
   * @step 推送 work_items | 三項狀態皆「失敗」
   * @step 檢視原因 | 三項各自顯示伺服器給的不同原因字串，且互不相同
   * @pass 三種失敗可區分
   * @story US10.2
   */
  test('成本逾時、失敗與權限不足的原因不同', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    h.server.send(
      F.encodeFrame(
        F.workItemsFrame(
          F.workItem('wt', `${M}-成本一`, '失敗', 'cost-finops', null, `${M}-估價逾時，請稍後再試`),
          F.workItem('wf', `${M}-成本二`, '失敗', 'cost-finops', null, `${M}-估價失敗`),
          F.workItem('wp', `${M}-成本三`, '失敗', 'cost-finops', null, `${M}-你沒有成本分析的權限`),
        ),
      ),
    );
    const list = page.getByTestId('brain-workitem-list');
    for (const id of ['wt', 'wf', 'wp']) await expect(list.getByTestId(`brain-workitem-${id}-status`)).toHaveText('失敗');
    await expect(list.getByTestId('brain-workitem-wt')).toContainText(`${M}-估價逾時，請稍後再試`);
    await expect(list.getByTestId('brain-workitem-wf')).toContainText(`${M}-估價失敗`);
    await expect(list.getByTestId('brain-workitem-wf')).not.toContainText('逾時');
    await expect(list.getByTestId('brain-workitem-wp')).toContainText(`${M}-你沒有成本分析的權限`);
  });

  /**
   * @purpose 脈絡列以名稱顯示三層：有識別碼而名稱為 null 顯示「（無法顯示名稱）」、空字串顯示「（未命名）」、三層皆 null 顯示「尚未選定」；data-state 與 data-id 可機械比對（BR97.2、AC1.1.5、NFR2.140；functional-design R-06）。
   * @ui / | 入口頁 brain-context-bar
   * @given /api/brain/ws 依序推送四種共享段 work_target
   * @step 推送三層皆有名稱 | 三個名稱節點文字與 data-id（1、2、3）正確；data-state=default
   * @step 推送圖名為 null | 圖層顯示「（無法顯示名稱）」
   * @step 推送圖名為空字串 | 圖層顯示「（未命名）」
   * @step 推送三個識別碼皆 null | 顯示「尚未選定」、data-state=no-object
   * @pass 四種情形各自正確
   * @story US2.1
   */
  test('脈絡列三層名稱與兩種佔位文字', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    const bar = page.getByTestId('brain-context-bar');
    h.server.send(F.encodeFrame(F.workTargetFrame('shared', '1', '2', '3', `${M}-專案`, `${M}-系統`, `${M}-圖`)));
    await expect(bar).toHaveAttribute('data-state', 'default');
    await expect(page.getByTestId('brain-context-name-project')).toHaveText(`${M}-專案`);
    await expect(page.getByTestId('brain-context-name-project')).toHaveAttribute('data-id', '1');
    await expect(page.getByTestId('brain-context-name-system')).toHaveAttribute('data-id', '2');
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveAttribute('data-id', '3');
    h.server.send(F.encodeFrame(F.workTargetFrame('shared', '1', '2', '3', `${M}-專案`, `${M}-系統`, null)));
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveText('（無法顯示名稱）');
    h.server.send(F.encodeFrame(F.workTargetFrame('shared', '1', '2', '3', `${M}-專案`, `${M}-系統`, '')));
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveText('（未命名）');
    h.server.send(F.encodeFrame(F.emptyTargetFrame('shared')));
    await expect(bar).toHaveAttribute('data-state', 'no-object');
    await expect(bar).toContainText('尚未選定');
    await expect(page.getByTestId('brain-context-name-project')).toHaveCount(0);
  });

  /**
   * @purpose 入口頁忽略全部 sharing_mode，且只套用 shared 段的 work_target（BR92.4）。
   * @ui / | 入口頁 brain-context-bar
   * @given /api/brain/ws；共享段作業對象為專案 1
   * @step 伺服器推送 segment=workspace 的 work_target（專案 9） | 脈絡列仍為專案 1
   * @step 伺服器推送 workspace 的 sharing_mode=isolated | 脈絡列不變、data-state 仍為 default
   * @pass 入口頁只讀共享段
   * @story US2.1
   */
  test('入口頁只套用共享段的作業對象', async ({ page }) => {
    const h = await setup(page);
    h.server.shared = { pid: '1', sid: null, did: null };
    h.server.names = { p1: `${M}-共享專案` };
    await page.goto('/');
    await waitReady(page);
    await expect(page.getByTestId('brain-context-name-project')).toHaveText(`${M}-共享專案`);
    h.server.send(F.encodeFrame(F.workTargetFrame('workspace', '9', null, null, `${M}-別段專案`, null, null)));
    h.server.send(F.encodeFrame(F.sharingModeFrame('workspace', 'isolated')));
    h.server.send(F.encodeFrame(F.tokenFrame('t-24', `${M}-界標`)));
    await expect(conv(page).getByText(`${M}-界標`)).toBeVisible();
    await expect(page.getByTestId('brain-context-name-project')).toHaveText(`${M}-共享專案`);
    await expect(page.getByTestId('brain-context-bar')).toHaveAttribute('data-state', 'default');
  });

  /**
   * @purpose 子頁面「改為獨立對話」只在伺服器回推後才換徽章；獨立段的面板為空、脈絡列改為該段；切回共享時紀錄與作業對象與離開時相同（BR97.3、BR97.8、AC3.1.1、AC3.1.2、AC3.1.4）。
   * @ui /workspace | 工作區脈絡列與「問大腦」面板
   * @given /api/brain/ws；共享段作業對象專案 1、workspace 段作業對象專案 2；面板內已有一輪共享段對話
   * @step 關閉伺服器自動回推後按「改為獨立對話」 | 送出 set_sharing_mode{isolated, workspace}；徽章仍為「共享」
   * @step 伺服器推送 sharing_mode=isolated 與 workspace 段 work_target | 徽章「獨立」、面板沒有共享段的訊息、脈絡列為專案 2
   * @step 伺服器推送切回共享 | 徽章「共享」、面板再次出現原訊息、脈絡列為專案 1
   * @pass 不樂觀更新、段切換與還原皆正確
   * @story US3.1
   */
  test('子頁面切換獨立對話以伺服器回推為準', async ({ page }) => {
    const h = await setup(page, { diagrams: [], bootstrapId: null });
    h.server.shared = { pid: '1', sid: null, did: null };
    h.server.isolated.workspace = { pid: '2', sid: null, did: null };
    h.server.names = { p1: `${M}-共享專案`, p2: `${M}-獨立專案` };
    await page.goto('/workspace');
    await waitReady(page);
    await page.getByTestId('brain-subpage-panel-toggle').click();
    await say(page, `${M}-共享段的話`);
    h.server.send(F.turnFrames('t-25', `${M}-共享段的回覆`));
    const panel = page.getByTestId('brain-subpage-panel');
    await expect(panel).toContainText(`${M}-共享段的回覆`);
    h.server.echo = false;
    await page.getByTestId('brain-context-sharing-switch').click();
    await expect.poll(() => h.server.framesOf('set_sharing_mode').length).toBe(1);
    expect(h.server.framesOf('set_sharing_mode')[0].payload).toMatchObject({ mode: 'isolated', scope: 'workspace' });
    await expect(page.getByTestId('brain-context-sharing-badge')).toHaveText('共享');
    h.server.modes.workspace = 'isolated';
    h.server.send([F.encodeFrame(F.sharingModeFrame('workspace', 'isolated')), h.server.targetFrame('workspace')]);
    await expect(page.getByTestId('brain-context-sharing-badge')).toHaveText('獨立');
    await expect(panel).not.toContainText(`${M}-共享段的回覆`);
    await expect(page.getByTestId('brain-context-name-project')).toHaveText(`${M}-獨立專案`);
    h.server.modes.workspace = 'shared';
    h.server.send([F.encodeFrame(F.sharingModeFrame('workspace', 'shared')), h.server.targetFrame('shared')]);
    await expect(page.getByTestId('brain-context-sharing-badge')).toHaveText('共享');
    await expect(panel).toContainText(`${M}-共享段的回覆`);
    await expect(page.getByTestId('brain-context-name-project')).toHaveText(`${M}-共享專案`);
  });

  /**
   * @purpose 子頁面面板送出的 user_message 帶本頁 page；回寫的 set_work_target 帶本頁目前讀取的段（BR92.3、BR97.4、AC3.1.3）。
   * @ui /workspace | 工作區「問大腦」面板與架構圖下拉
   * @given /api/brain/ws；兩張自有圖 11、12；workspace 已切為獨立對話
   * @step 展開面板送出一句 | user_message.payload.page 為 workspace
   * @step 從下拉改選圖 12 | set_work_target.payload 為 {diagramId:'12', segment:'workspace'}
   * @pass page 與 segment 欄位皆為本頁的值
   * @story US3.1
   */
  test('子頁面送出帶本頁 page 與所讀段', async ({ page }) => {
    const h = await setup(page, { diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 12, title: `${M}-圖12` }], bootstrapId: 11 });
    h.server.modes.workspace = 'isolated';
    h.server.isolated.workspace = { pid: null, sid: null, did: '11' };
    await page.goto('/workspace');
    await waitReady(page);
    await expect(page.getByTestId('brain-context-sharing-badge')).toHaveText('獨立');
    await page.getByTestId('brain-subpage-panel-toggle').click();
    await say(page, `${M}-子頁面的話`);
    await expect.poll(() => h.server.framesOf('user_message').length).toBe(1);
    expect(h.server.framesOf('user_message')[0].payload).toMatchObject({ page: 'workspace' });
    await page.locator('select', { has: page.locator('option[value="12"]') }).first().selectOption('12');
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    expect(h.server.framesOf('set_work_target')[0].payload).toMatchObject({ diagramId: '12', segment: 'workspace' });
  });

  /**
   * @purpose 脈絡列只掛在入口頁、工作區與評核頁；成本頁與使用者管理頁不掛、不開大腦連線（BR97.1、AC2.1.3）。
   * @ui /cost | 成本頁
   * @ui /admin/users | 使用者管理頁
   * @given 全權限使用者
   * @step 開啟 /cost | 無 brain-context-bar
   * @step 開啟 /admin/users | 無 brain-context-bar
   * @step 計算大腦連線 | 0 條
   * @pass 兩頁皆不掛脈絡列、不開連線
   * @story US2.1
   */
  test('成本頁與使用者管理頁不掛脈絡列', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/cost');
    await expect(page).toHaveURL(/\/cost$/);
    await page.waitForLoadState('networkidle');
    await expect(page.getByTestId('brain-context-bar')).toHaveCount(0);
    await page.goto('/admin/users');
    await expect(page).toHaveURL(/\/admin\/users$/);
    await page.waitForLoadState('networkidle');
    await expect(page.getByTestId('brain-context-bar')).toHaveCount(0);
    expect(h.server.conns.length).toBe(0);
  });

  /**
   * @purpose 工作區的快照先於 bootstrap 到達時，首次對齊等頁面就緒才做：就緒後開啟作業對象的圖，不被 bootstrap 覆蓋（BR97.5、NFR2.141、AC1.1.4）。
   * @ui /workspace | 工作區畫布與脈絡列
   * @given /api/brain/ws 的共享段作業對象為自有圖 12；bootstrap 回上次開的自有圖 11，且回應被延到快照之後
   * @step 開啟 /workspace，等脈絡列顯示圖 12 後才放行 bootstrap | bootstrap 先載入圖 11
   * @step 等首次對齊 | 畫布最後載入圖 12、下拉選中 12；客戶端沒有送 set_work_target
   * @pass 快照先到時最終開啟的是作業對象的圖
   * @story US1.1
   */
  test('工作區快照先到時就緒後開啟作業對象的圖', async ({ page }) => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const h = await setup(page, {
      diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 12, title: `${M}-圖12` }],
      bootstrapId: 11,
      bootstrapGate: gate,
    });
    h.server.shared = { pid: null, sid: null, did: '12' };
    h.server.names = { d12: `${M}-圖12` };
    await page.goto('/workspace');
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveText(`${M}-圖12`);
    release();
    await expect.poll(async () => (await h.canvasLoads()).at(-1) ?? '').toContain(`${M}-d12`);
    await expect(page.locator('select', { has: page.locator('option[value="12"]') }).first()).toHaveValue('12');
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 快照晚於 bootstrap 到達時，最終三元組與快照先到相同（NFR2.141）。
   * @ui /workspace | 工作區畫布與脈絡列
   * @given 同上一案，但 bootstrap 立即回應、快照由測試在 bootstrap 完成後才送
   * @step 開啟 /workspace | 畫布先載入圖 11
   * @step 伺服器送快照（作業對象圖 12） | 畫布最後載入圖 12、下拉選中 12；客戶端沒有送 set_work_target
   * @pass 快照後到的結果與先到相同
   * @story US1.1
   */
  test('工作區快照後到時結果與先到相同', async ({ page }) => {
    const h = await setup(page, {
      diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 12, title: `${M}-圖12` }],
      bootstrapId: 11,
    });
    h.server.shared = { pid: null, sid: null, did: '12' };
    h.server.names = { d12: `${M}-圖12` };
    h.server.autoSnapshot = false;
    await page.goto('/workspace');
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d11`);
    await expect.poll(() => h.server.framesOf('hello').length).toBe(1);
    h.server.sendSnapshot();
    await expect.poll(async () => (await h.canvasLoads()).at(-1) ?? '').toContain(`${M}-d12`);
    await expect(page.locator('select', { has: page.locator('option[value="12"]') }).first()).toHaveValue('12');
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 晚到的首筆作業對象不得取代使用者未儲存的畫布：改顯示提示，按「開啟這張圖」並確認後才換圖；畫布乾淨時照常自動開啟（EPN-18；functional-design R-02 使用者裁決）。
   * @ui /workspace | 工作區畫布、brain-sync-notice
   * @given 工作區沒有上次開的圖；作業對象為自有圖 12；快照由測試控制送出時機
   * @step 使用者在畫布新增一個圖形後，伺服器才送快照 | 畫布沒有載入圖 12；提示「目前畫布有未儲存的變更，沒有自動開啟」；沒有送 set_work_target
   * @step 按「開啟這張圖」並在確認框按確定 | 畫布載入圖 12
   * @step 對照組：另一個分頁不編輯畫布，快照晚到 | 畫布自動載入圖 12、沒有提示
   * @pass 有未儲存內容時不自動換圖，乾淨時自動開啟
   * @story US1.1
   */
  test('工作區畫布未儲存時晚到的作業對象不自動換圖', async ({ page, browser }) => {
    const opts: SetupOptions = { diagrams: [{ id: 12, title: `${M}-圖12` }], bootstrapId: null };
    const h = await setup(page, opts);
    h.server.shared = { pid: null, sid: null, did: '12' };
    h.server.names = { d12: `${M}-圖12` };
    h.server.autoSnapshot = false;
    await page.goto('/workspace');
    await expect.poll(() => h.server.framesOf('hello').length).toBe(1);
    await expect.poll(() => page.frames().some((f) => f.url().includes('embed.diagrams.net'))).toBe(true);
    await h.editCanvas(`<mxGraphModel><root><mxCell id="${M}-user-shape"/></root></mxGraphModel>`);
    await expect(page.getByText('尚未建檔')).toBeVisible();
    h.server.sendSnapshot();
    const notice = page.getByTestId('brain-sync-notice');
    await expect(notice).toContainText('目前畫布有未儲存的變更，沒有自動開啟');
    expect((await h.canvasLoads()).join()).not.toContain(`${M}-d12`);
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
    page.once('dialog', (d) => void d.accept());
    await notice.getByTestId('brain-sync-open-diagram').click();
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d12`);

    const ctx = await browser.newContext();
    const clean = await ctx.newPage();
    const h2 = await setup(clean, opts);
    h2.server.shared = { pid: null, sid: null, did: '12' };
    h2.server.names = { d12: `${M}-圖12` };
    h2.server.autoSnapshot = false;
    await clean.goto('/workspace');
    await expect.poll(() => h2.server.framesOf('hello').length).toBe(1);
    await expect.poll(() => clean.frames().some((f) => f.url().includes('embed.diagrams.net'))).toBe(true);
    h2.server.sendSnapshot();
    await expect.poll(async () => (await h2.canvasLoads()).join()).toContain(`${M}-d12`);
    await expect(clean.getByTestId('brain-sync-notice')).toHaveCount(0);
    await ctx.close();
  });

  /**
   * @purpose 評核頁已上傳但未存檔的 .drawio 不得被晚到的作業對象清掉（EPN-18；nfr-requirements R-06）。
   * @ui /assessment | 評核頁上傳區、brain-sync-notice
   * @given 評核頁的圖清單含自有圖 12；作業對象為圖 12；快照由測試控制送出時機
   * @step 上傳 e2e-u14.drawio 後，伺服器才送快照 | 「已上傳：e2e-u14.drawio」仍在；提示「沒有自動開啟」出現
   * @step 檢視選定的圖 | 下拉仍未選圖 12，且沒有對圖 12 發出評核清單請求
   * @pass 未存檔上傳不被取代
   * @story US1.1
   */
  test('評核頁未存檔上傳時晚到的作業對象不自動換圖', async ({ page }) => {
    const h = await setup(page, { diagrams: [{ id: 12, title: `${M}-圖12` }] });
    h.server.shared = { pid: null, sid: null, did: '12' };
    h.server.names = { d12: `${M}-圖12` };
    h.server.autoSnapshot = false;
    await page.goto('/assessment');
    const select = page.locator('select', { has: page.locator('option[value="12"]') }).first();
    await expect(select).toBeAttached();
    await page.locator('input[type="file"]').setInputFiles({
      name: `${M}.drawio`,
      mimeType: 'application/xml',
      buffer: Buffer.from(`<mxGraphModel><root><mxCell id="${M}-upload"/></root></mxGraphModel>`),
    });
    await expect(page.getByText(`已上傳：${M}.drawio`)).toBeVisible();
    await expect.poll(() => h.server.framesOf('hello').length).toBe(1);
    h.server.sendSnapshot();
    await expect(page.getByTestId('brain-sync-notice')).toContainText('沒有自動開啟');
    await expect(page.getByText(`已上傳：${M}.drawio`)).toBeVisible();
    await expect(select).not.toHaveValue('12');
    expect(h.apiRequests.filter((r) => r.includes('/api/architecture/reviews') && r.includes('diagram_id=12'))).toHaveLength(0);
  });

  /**
   * @purpose 使用者自己開圖不得收到「作業對象已改為」：一個往返內連選 X、Y，X 的回聲到達時也不提示（BR97.5；functional-design R-05）。
   * @ui /workspace | 工作區架構圖下拉、brain-sync-notice
   * @given 三張自有圖 11、12、13；bootstrap 開 11、作業對象亦為 11；伺服器不自動回推
   * @step 從下拉連選 12、13 | 依序送出兩則 set_work_target
   * @step 伺服器推送 12 的回聲 | 脈絡列顯示圖 12，沒有提示
   * @step 伺服器推送 13 的回聲 | 脈絡列顯示圖 13，沒有提示
   * @step 伺服器再推送一則圖 12（非回聲） | 出現「作業對象已改為」
   * @pass 回聲不提示、真正的外部變更才提示
   * @story US2.2
   */
  test('連選兩張圖時自己的回聲不提示', async ({ page }) => {
    const h = await setup(page, {
      diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 12, title: `${M}-圖12` }, { id: 13, title: `${M}-圖13` }],
      bootstrapId: 11,
    });
    h.server.shared = { pid: null, sid: null, did: '11' };
    h.server.names = { d11: `${M}-圖11`, d12: `${M}-圖12`, d13: `${M}-圖13` };
    h.server.echo = false;
    await page.goto('/workspace');
    await waitReady(page);
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d11`);
    const select = page.locator('select', { has: page.locator('option[value="12"]') }).first();
    await select.selectOption('12');
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    await select.selectOption('13');
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(2);
    const notice = page.getByTestId('brain-sync-notice');
    h.server.send(F.encodeFrame(F.workTargetFrame('shared', null, null, '12', null, null, `${M}-圖12`)));
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveText(`${M}-圖12`);
    await expect(notice).toHaveCount(0);
    h.server.send(F.encodeFrame(F.workTargetFrame('shared', null, null, '13', null, null, `${M}-圖13`)));
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveText(`${M}-圖13`);
    await expect(notice).toHaveCount(0);
    h.server.send(F.encodeFrame(F.workTargetFrame('shared', null, null, '12', null, null, `${M}-圖12`)));
    await expect(notice).toContainText(`作業對象已改為 ${M}-圖12`);
  });

  /**
   * @purpose 開啟別人分享的圖不會成為大腦的作業對象：客戶端不送 set_work_target 並顯示說明（EPN-17a、BR97.6 ②）。
   * @ui /workspace | 工作區架構圖下拉、brain-sync-notice
   * @given 自有圖 11（bootstrap 開啟、亦為作業對象）與別人分享的圖 21
   * @step 從下拉改選圖 21 | 出現「這張圖是別人分享的，不會成為大腦的作業對象」
   * @step 檢視送出的訊框 | set_work_target 0 則
   * @pass 非自有圖不回寫
   * @story US2.2
   */
  test('別人分享的圖不回寫作業對象', async ({ page }) => {
    const h = await setup(page, {
      diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 21, title: `${M}-分享圖`, owner: false }],
      bootstrapId: 11,
    });
    h.server.shared = { pid: null, sid: null, did: '11' };
    await page.goto('/workspace');
    await waitReady(page);
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d11`);
    await page.locator('select', { has: page.locator('option[value="21"]') }).first().selectOption('21');
    await expect(page.getByTestId('brain-sync-notice')).toContainText('這張圖是別人分享的，不會成為大腦的作業對象');
    await page.waitForTimeout(300);
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 刪除作業對象所指的圖時送出保留上兩層、diagramId 為 null 的設定；新建空白畫布不送、作業對象維持（BR97.6 ③④）。
   * @ui /workspace | 工作區「刪除架構圖」「建立新架構圖」、brain-sync-notice
   * @given 作業對象為專案 1／系統 2／圖 11；bootstrap 開圖 11
   * @step 按「刪除架構圖」並確認 | 送出 set_work_target{projectId:'1', systemId:'2', diagramId:null}
   * @step 按「建立新架構圖」 | 不再送 set_work_target；提示「目前畫布未存檔，作業對象維持 e2e-u14-系統」
   * @pass 刪除保留上兩層、新建空白不回寫
   * @story US2.2
   */
  test('刪除作業對象的圖保留上兩層且新建空白不回寫', async ({ page }) => {
    const h = await setup(page, { diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 12, title: `${M}-圖12` }], bootstrapId: 11 });
    h.server.shared = { pid: '1', sid: '2', did: '11' };
    h.server.names = { p1: `${M}-專案`, s2: `${M}-系統`, d11: `${M}-圖11` };
    await page.goto('/workspace');
    await waitReady(page);
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d11`);
    page.once('dialog', (d) => void d.accept());
    await page.getByRole('button', { name: '刪除架構圖' }).click();
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    expect(h.server.framesOf('set_work_target')[0].payload).toMatchObject({ projectId: '1', systemId: '2', diagramId: null });
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveCount(0);
    await page.getByTitle('建立新架構圖').click();
    await expect(page.getByTestId('brain-sync-notice')).toContainText(`目前畫布未存檔，作業對象維持 ${M}-系統`);
    await page.waitForTimeout(300);
    expect(h.server.framesOf('set_work_target')).toHaveLength(1);
  });

  /**
   * @purpose 作業對象停在系統（diagramId 為 null）時進工作區，bootstrap 開的上次的圖不得回寫覆蓋它（functional-design R-08）。
   * @ui /workspace | 工作區脈絡列
   * @given 作業對象為專案 1／系統 2／圖 null；bootstrap 開自有圖 11
   * @step 開啟 /workspace 並等畫布載入圖 11 | 脈絡列仍顯示系統 2
   * @step 檢視送出的訊框 | set_work_target 0 則
   * @pass bootstrap 開的圖不回寫
   * @story US2.2
   */
  test('作業對象只到系統時 bootstrap 開的圖不回寫', async ({ page }) => {
    const h = await setup(page, { diagrams: [{ id: 11, title: `${M}-圖11` }], bootstrapId: 11 });
    h.server.shared = { pid: '1', sid: '2', did: null };
    h.server.names = { p1: `${M}-專案`, s2: `${M}-系統S` };
    await page.goto('/workspace');
    await waitReady(page);
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d11`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(300);
    await expect(page.getByTestId('brain-context-name-system')).toHaveText(`${M}-系統S`);
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 圖清單請求失敗時擁有者未知：兩個方向都不同步並顯示說明（BR97.5 末段；functional-design R-06）。
   * @ui /workspace | 工作區 brain-sync-notice
   * @given GET /api/collab/diagrams 回 500；作業對象為圖 12
   * @step 開啟 /workspace | 出現「無法確認這張圖的擁有者，未同步作業對象」
   * @step 檢視畫布與訊框 | 畫布未載入圖 12；set_work_target 0 則
   * @pass 擁有者未知時不同步
   * @story US2.2
   */
  test('圖清單失敗時兩向都不同步', async ({ page }) => {
    const h = await setup(page, { diagrams: [{ id: 12, title: `${M}-圖12` }], listStatus: 500, bootstrapId: null });
    h.server.shared = { pid: null, sid: null, did: '12' };
    await page.goto('/workspace');
    await waitReady(page);
    await expect(page.getByTestId('brain-sync-notice')).toContainText('無法確認這張圖的擁有者，未同步作業對象');
    await page.waitForTimeout(300);
    expect((await h.canvasLoads()).join()).not.toContain(`${M}-d12`);
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 由工作區帶 diagramId 進評核頁時回寫作業對象；回到入口頁時脈絡列的對象一致（BR97.6、AC2.2.1、AC2.2.2）。
   * @ui /workspace | 工作區
   * @ui /assessment | 評核頁
   * @ui / | 入口頁脈絡列
   * @given 自有圖 11、12；作業對象為圖 11；假伺服器會把 set_work_target 扇出回各頁
   * @step 開啟 /workspace 後前往 /assessment?diagramId=12 | 評核頁送出 set_work_target{diagramId:'12', segment:'shared'}
   * @step 經 Sidebar 回到入口頁 | 脈絡列的圖為 12（data-id=12、名稱 e2e-u14-圖12）
   * @pass 跨頁的作業對象一致
   * @story US2.2
   */
  test('由工作區帶圖進評核頁後入口頁對象一致', async ({ page }) => {
    const h = await setup(page, { diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 12, title: `${M}-圖12` }], bootstrapId: 11 });
    h.server.shared = { pid: null, sid: null, did: '11' };
    h.server.names = { d11: `${M}-圖11`, d12: `${M}-圖12` };
    await page.goto('/workspace');
    await waitReady(page);
    await page.evaluate(() => {
      window.history.pushState({}, '', '/assessment?diagramId=12');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    await expect(page).toHaveURL(/\/assessment\?diagramId=12$/);
    await expect.poll(() => h.server.framesOf('set_work_target').length).toBe(1);
    expect(h.server.framesOf('set_work_target')[0].payload).toMatchObject({ diagramId: '12', segment: 'shared' });
    await page.getByTestId('sidebar-entry-link').click();
    await waitReady(page);
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveAttribute('data-id', '12');
    await expect(page.getByTestId('brain-context-name-diagram')).toHaveText(`${M}-圖12`);
  });

  /**
   * @purpose 沒有 K1 時子頁面不掛脈絡列與面板，畫布操作也不送任何作業對象訊息（nfr-design R-05）。
   * @ui /workspace | 工作區
   * @given 只有 A1 的使用者；自有圖 11、12；bootstrap 開 11
   * @step 開啟 /workspace | 無 brain-context-bar、無 brain-subpage-panel
   * @step 從下拉改選圖 12 | 大腦連線 0 條、set_work_target 0 則
   * @pass 無 K1 時同步掛點全為 no-op
   * @story US3.1
   */
  test('無 K1 時子頁面不掛大腦且不送作業對象', async ({ page }) => {
    const h = await setup(page, { perms: ['A1'], diagrams: [{ id: 11, title: `${M}-圖11` }, { id: 12, title: `${M}-圖12` }], bootstrapId: 11 });
    await page.goto('/workspace');
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d11`);
    await expect(page.getByTestId('brain-context-bar')).toHaveCount(0);
    await expect(page.getByTestId('brain-subpage-panel')).toHaveCount(0);
    await page.locator('select', { has: page.locator('option[value="12"]') }).first().selectOption('12');
    await expect.poll(async () => (await h.canvasLoads()).join()).toContain(`${M}-d12`);
    await page.waitForTimeout(300);
    expect(h.server.conns.length).toBe(0);
    expect(h.server.framesOf('set_work_target')).toHaveLength(0);
  });

  /**
   * @purpose 串流中換頁：舊頁的該輪轉為中斷；新頁的連線收到同一 turnId 的後續時合併回原訊息、不另建一則（BR93.7、AC1.1.4）。
   * @ui / | 入口頁
   * @ui /workspace | 工作區「問大腦」面板
   * @given /api/brain/ws；入口頁一輪已收到第一個 token、尚未 done
   * @step 經 Sidebar 換到 /workspace 並展開面板 | 該輪顯示「你在回覆完成前離開了這一頁」
   * @step 伺服器在新連線送同一 turnId 的 token 與 done | 面板中該 turnId 的訊息恰 1 則，含兩段文字、狀態 done
   * @pass 換頁後同一輪只顯示一則
   * @story US1.1
   */
  test('串流中換頁後同一輪合併為一則', async ({ page }) => {
    const h = await setup(page, { diagrams: [], bootstrapId: null });
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-畫圖`);
    h.server.send(F.encodeFrame(F.tokenFrame('t-39', `${M}-前半`)));
    await expect(page.locator('[data-testid="brain-stream-message"][data-turn-id="t-39"]')).toContainText(`${M}-前半`);
    await page.locator('a[href="/workspace"]').first().click();
    await expect(page).toHaveURL(/\/workspace$/);
    await waitReady(page);
    await page.getByTestId('brain-subpage-panel-toggle').click();
    const msg = page.locator('[data-testid="brain-stream-message"][data-turn-id="t-39"]');
    await expect(msg).toContainText('你在回覆完成前離開了這一頁');
    h.server.send([F.encodeFrame(F.tokenFrame('t-39', `${M}-後半`)), F.encodeFrame(F.doneFrame('t-39'))]);
    await expect(msg).toHaveCount(1);
    await expect(msg).toContainText(`${M}-前半${M}-後半`);
    await expect(msg).toHaveAttribute('data-status', 'done');
  });

  /**
   * @purpose 換頁後回到入口頁，共享段的對話紀錄仍在（BR93.4）。
   * @ui / | 入口頁
   * @ui /workspace | 工作區
   * @given /api/brain/ws；入口頁完成一輪對話
   * @step 經 Sidebar 到 /workspace 再回到入口頁 | 原句與回覆仍可見
   * @pass 紀錄跨頁保留
   * @story US3.1
   */
  test('換頁後回入口頁紀錄仍在', async ({ page }) => {
    const h = await setup(page, { diagrams: [], bootstrapId: null });
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-留著`);
    h.server.send(F.turnFrames('t-40', `${M}-回覆留著`));
    await expect(conv(page).getByText(`${M}-回覆留著`)).toBeVisible();
    await page.locator('a[href="/workspace"]').first().click();
    await waitReady(page);
    await page.getByTestId('sidebar-entry-link').click();
    await waitReady(page);
    await expect(conv(page).getByText(`${M}-留著`, { exact: true })).toBeVisible();
    await expect(conv(page).getByText(`${M}-回覆留著`)).toBeVisible();
  });

  /**
   * @purpose 以 1011 關閉後重連，第二次 ready 推送與本地不同的作業對象與工作項時以伺服器為準覆蓋；對話紀錄保留（NFR4.140、AC2.1.4）。
   * @ui / | 入口頁脈絡列、常駐區與對話區
   * @given /api/brain/ws；第一次快照為專案 1、工作項 w1；重連後的快照為專案 2、工作項 w2
   * @step 完成一輪對話後伺服器以 1011 關閉 | 稍後自動重連
   * @step 第二次快照到達 | 脈絡列為專案 2；常駐區只有 w2、沒有 w1
   * @step 檢視對話區 | 先前的原句與回覆仍在
   * @pass 狀態被覆蓋、紀錄保留
   * @story US2.1
   */
  test('重連後以伺服器推送覆蓋狀態並保留紀錄', async ({ page }) => {
    const h = await setup(page);
    h.server.shared = { pid: '1', sid: null, did: null };
    h.server.names = { p1: `${M}-專案一`, p2: `${M}-專案二` };
    h.server.items = [F.workItem('w1', `${M}-舊工作`, '處理中')];
    await page.goto('/');
    await waitReady(page);
    await expect(page.getByTestId('brain-workitem-dock').getByTestId('brain-workitem-w1')).toBeVisible();
    await say(page, `${M}-重啟前`);
    h.server.send(F.turnFrames('t-41', `${M}-重啟前回覆`));
    await expect(conv(page).getByText(`${M}-重啟前回覆`)).toBeVisible();
    h.server.shared = { pid: '2', sid: null, did: null };
    h.server.items = [F.workItem('w2', `${M}-新工作`, '處理中')];
    await h.server.last.ws.close({ code: 1011 });
    await expect.poll(() => h.server.conns.length).toBe(2);
    await expect(page.getByTestId('brain-context-name-project')).toHaveText(`${M}-專案二`);
    await expect(page.getByTestId('brain-workitem-dock').getByTestId('brain-workitem-w2')).toBeVisible();
    await expect(page.getByTestId('brain-workitem-dock').getByTestId('brain-workitem-w1')).toHaveCount(0);
    await expect(conv(page).getByText(`${M}-重啟前回覆`)).toBeVisible();
  });

  /**
   * @purpose 每段最多 500 則：超過時移除最舊者並顯示「較早的對話已不在畫面上」；被移除那一輪再收到 token 時另建一則、不崩潰、不寫進別的訊息（EPN-04、EPN-05）。
   * @ui / | 入口頁 brain-transcript-truncated
   * @given /api/brain/ws 灌入 501 輪（每輪一個 token 與 done）
   * @step 灌完 501 輪 | 第 1 輪不可見、截斷說明出現、第 2 與第 501 輪可見、訊息數 500
   * @step 伺服器再送第 1 輪的 token | 末端另建一則含該文字；第 3 輪的內容不變；畫面仍可用
   * @pass 上限與對照同生同死
   * @story US8.1
   */
  test('每段五百則上限與被移除輪次的後續', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    const frames: string[] = [];
    for (let i = 1; i <= 501; i += 1) frames.push(...F.turnFrames(`t42-${i}`, `${M}-訊息-${i}-`));
    h.server.send(frames);
    await expect(page.getByTestId('brain-transcript-truncated')).toBeVisible();
    await expect(page.locator('[data-testid="brain-stream-message"][data-turn-id="t42-501"]')).toBeVisible();
    await expect(page.locator('[data-testid="brain-stream-message"][data-turn-id="t42-1"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="brain-stream-message"][data-turn-id="t42-2"]')).toHaveCount(1);
    await expect(page.getByTestId('brain-stream-message')).toHaveCount(500);
    h.server.send(F.encodeFrame(F.tokenFrame('t42-1', `${M}-遲到的後續`)));
    const late = page.locator('[data-testid="brain-stream-message"][data-turn-id="t42-1"]');
    await expect(late).toHaveText(new RegExp(`^${M}-遲到的後續`));
    await expect(page.locator('[data-testid="brain-stream-message"][data-turn-id="t42-3"]')).toHaveText(`${M}-訊息-3-`);
    await expect(page.getByTestId('brain-stream-message')).toHaveCount(500);
    await expect(page.getByTestId('brain-input')).toBeEnabled();
  });

  /**
   * @purpose 換人登入時對話紀錄一定清空——即使 /me 的回應缺 id（使用者物件沒有 id，依 id 作 key 的做法會讓兩人同 key）；入口頁與兩個子頁面的對話區皆空（EPN-15；functional-design R-03 使用者裁決）。
   * @api POST /api/auth/login -> 200 | 依帳號回不同 token
   * @api GET /api/auth/me -> 200 | 回應不含 id 欄位
   * @ui /login | 登入頁
   * @ui / | 入口頁
   * @ui /workspace | 工作區「問大腦」面板
   * @ui /assessment | 評核頁「問大腦」面板
   * @given 未登入；/me 對兩位使用者的回應皆缺 id
   * @step A 經登入頁登入並完成一輪對話 | 對話區有 A 的原句
   * @step 經 Sidebar 登出、B 經登入頁登入 | 入口頁對話區沒有 A 的原句與回覆
   * @step B 進 /workspace 與 /assessment 並展開面板 | 皆沒有 A 的對話
   * @pass 換人即清空，不依賴 user.id
   * @story US8.1
   */
  test('登出再換人登入時對話區清空', async ({ page }) => {
    const h = await setup(page, { loggedIn: false, meOmitId: true, diagrams: [], bootstrapId: null });
    await page.route('**/api/auth/login', async (route) => {
      const body = JSON.parse(route.request().postData() ?? '{}') as { username: string };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: `${body.username}-tok`, username: body.username, role: 'Platform_Admin', authorization_status: 'approved' }),
      });
    });
    const loginAs = async (name: string) => {
      await page.getByPlaceholder('請輸入您的帳號').fill(name);
      await page.getByPlaceholder('請輸入密碼').fill('pw');
      await page.getByRole('button', { name: '登入系統' }).click();
      await expect(page.getByTestId('brain-entry-page')).toBeVisible();
      await waitReady(page);
    };
    await page.goto('/login');
    await loginAs(`${M}-userA`);
    await say(page, `${M}-A的原句`);
    h.server.send(F.turnFrames('t-43', `${M}-A的回覆`));
    await expect(conv(page).getByText(`${M}-A的回覆`)).toBeVisible();
    await page.getByTitle('登出系統').click();
    await expect(page).toHaveURL(/\/login$/);
    await loginAs(`${M}-userB`);
    await expect(page.getByTestId('brain-entry-page')).not.toContainText(`${M}-A的原句`);
    await expect(page.getByTestId('brain-entry-page')).not.toContainText(`${M}-A的回覆`);
    for (const path of ['/workspace', '/assessment']) {
      await page.locator(`a[href="${path}"]`).first().click();
      await waitReady(page);
      await page.getByTestId('brain-subpage-panel-toggle').click();
      await expect(page.getByTestId('brain-subpage-panel')).not.toContainText(`${M}-A的`);
    }
  });

  /**
   * @purpose 不登出、不重新載入就直接換人登入時，對話紀錄也必須清空（EPN-15a；login() 第一行通知）。
   * @api POST /api/auth/login -> 200 | 依帳號回不同 token
   * @ui /login | 登入頁
   * @ui / | 入口頁
   * @given 未登入；A 經登入頁登入並完成一輪對話
   * @step 以 history.pushState 與 popstate 到 /login（不重新載入） | 登入頁出現
   * @step B 登入 | 入口頁對話區沒有 A 的原句與回覆
   * @pass 不經登出的換人也清空
   * @story US8.1
   */
  test('不登出直接換人登入時對話區清空', async ({ page }) => {
    const h = await setup(page, { loggedIn: false, diagrams: [], bootstrapId: null });
    await page.route('**/api/auth/login', async (route) => {
      const body = JSON.parse(route.request().postData() ?? '{}') as { username: string };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: `${body.username}-tok`, username: body.username, role: 'Platform_Admin', authorization_status: 'approved' }),
      });
    });
    const loginAs = async (name: string) => {
      await page.getByPlaceholder('請輸入您的帳號').fill(name);
      await page.getByPlaceholder('請輸入密碼').fill('pw');
      await page.getByRole('button', { name: '登入系統' }).click();
      await expect(page.getByTestId('brain-entry-page')).toBeVisible();
      await waitReady(page);
    };
    await page.goto('/login');
    await loginAs(`${M}-userA`);
    await say(page, `${M}-A的原句`);
    h.server.send(F.turnFrames('t-44', `${M}-A的回覆`));
    await expect(conv(page).getByText(`${M}-A的回覆`)).toBeVisible();
    await page.evaluate(() => {
      window.history.pushState({}, '', '/login');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    await expect(page.getByRole('button', { name: '登入系統' })).toBeVisible();
    await loginAs(`${M}-userB`);
    await expect(page.getByTestId('brain-entry-page')).not.toContainText(`${M}-A的原句`);
    await expect(page.getByTestId('brain-entry-page')).not.toContainText(`${M}-A的回覆`);
  });

  /**
   * @purpose 對話紀錄只在記憶體：完成一次對話後瀏覽器儲存的鍵集合不變、任何值都不含使用者原句（EPN-13、ADR-0006 加密面）。
   * @ui / | 入口頁
   * @given 已登入（sessionStorage 只有 token）
   * @step 記下 localStorage／sessionStorage 的鍵集合 | —
   * @step 送出含唯一標記的一句並完成一輪 | —
   * @step 再讀兩個儲存 | 鍵集合與對話前相同；全部值不含該句
   * @pass 使用者原句不落地
   * @story US8.1
   */
  test('對話後瀏覽器儲存不含原句', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    const snapshot = () =>
      page.evaluate(() => ({
        local: Object.keys(localStorage).sort(),
        session: Object.keys(sessionStorage).sort(),
        values: [...Object.values(localStorage), ...Object.values(sessionStorage)].join('|'),
      }));
    const before = await snapshot();
    await say(page, `${M}-不得落地的原句`);
    h.server.send(F.turnFrames('t-45', `${M}-回覆`));
    await expect(conv(page).getByText(`${M}-回覆`)).toBeVisible();
    const after = await snapshot();
    expect(after.local).toEqual(before.local);
    expect(after.session).toEqual(before.session);
    expect(after.values).not.toContain(`${M}-不得落地的原句`);
  });

  /**
   * @purpose 瀏覽器主控台不得出現使用者原句、作業對象名稱或 token 的任何部分（EPN-14、BR92.8）。
   * @ui / | 入口頁
   * @given page.on('console') 收集全部訊息；作業對象帶三個唯一名稱；伺服器另送未知 type、零內容 done 與 error
   * @step 完成一輪含唯一原句的對話並觸發上述三種會記 console 的情形 | —
   * @step 檢視收集到的訊息 | 不含原句、三個名稱與 token 子字串
   * @pass 主控台不洩漏內容
   * @story US8.1
   */
  test('主控台不含原句名稱與 token', async ({ page }) => {
    const lines: string[] = [];
    page.on('console', (msg) => lines.push(msg.text()));
    const h = await setup(page);
    h.server.shared = { pid: '1', sid: '2', did: '3' };
    h.server.names = { p1: `${M}-機密專案`, s2: `${M}-機密系統`, d3: `${M}-機密圖` };
    await page.goto('/');
    await waitReady(page);
    await say(page, `${M}-機密原句`);
    h.server.send(F.turnFrames('t-46', `${M}-回覆`));
    h.server.send(F.unknownTypeFrame(`${M}-mystery`, `${M}-機密負載`));
    h.server.send(F.encodeFrame(F.doneFrame('t-46b')));
    h.server.send(F.encodeFrame(F.errorFrame('t-46c', 'INTERNAL_ERROR', `${M}-錯誤訊息`)));
    await expect(conv(page).getByText(`${M}-錯誤訊息`)).toBeVisible();
    const joined = lines.join('\n');
    for (const secret of [`${M}-機密原句`, `${M}-機密專案`, `${M}-機密系統`, `${M}-機密圖`, `${M}-機密負載`, 'e2e-u14-token']) {
      expect(joined).not.toContain(secret);
    }
  });

  /**
   * @purpose 本單元新增的前端程式不發任何 HTTP：入口頁從掛載到完成一次交辦只有既有端點；子頁面掛上大腦面板前後請求相同（EPN-08、BR98.5）。
   * @ui / | 入口頁
   * @ui /workspace | 工作區
   * @given page.on('request') 收集 /api/ 請求
   * @step 開啟入口頁並完成一輪交辦 | 每個請求都屬既有端點 GET /api/auth/me、GET /api/membership/reselections/pending；交辦期間沒有新增請求
   * @step 分別以具 K1 與不具 K1 的帳號開啟 /workspace | 兩者的 /api/ 請求序列相同
   * @pass 大腦相關畫面零新增 HTTP
   * @story US8.1
   */
  test('入口頁與子頁面掛點不新增 HTTP 請求', async ({ page, browser }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    await page.waitForLoadState('networkidle');
    const allowed = ['GET /api/auth/me', 'GET /api/membership/reselections/pending'];
    for (const r of new Set(h.apiRequests)) expect(allowed).toContain(r);
    const countAtLoad = h.apiRequests.length;
    await say(page, `${M}-交辦`);
    h.server.send(F.encodeFrame(F.workItemsFrame(F.workItem('w47', `${M}-工作`, '處理中'))));
    h.server.send(F.turnFrames('t-47', `${M}-已交辦`));
    await expect(conv(page).getByText(`${M}-已交辦`)).toBeVisible();
    expect(h.apiRequests.length).toBe(countAtLoad);

    const runWorkspace = async (perms: string[]) => {
      const ctx = await browser.newContext();
      const p = await ctx.newPage();
      const hh = await setup(p, { perms, diagrams: [{ id: 11, title: `${M}-圖11` }], bootstrapId: 11 });
      await p.goto('/workspace');
      await expect.poll(async () => (await hh.canvasLoads()).join()).toContain(`${M}-d11`);
      await p.waitForLoadState('networkidle');
      const list = hh.apiRequests.slice().sort();
      await ctx.close();
      return list;
    };
    expect(await runWorkspace(['K1', 'A1'])).toEqual(await runWorkspace(['A1']));
  });

  /**
   * @purpose 空狀態只依權限顯示大腦能交辦的兩張卡；點卡片填入範例句、不送出；紀錄為空而作業對象非空時另顯示一行說明（BR98.1、BR93.4）。
   * @ui / | 入口頁 brain-empty-card-*
   * @given 三種權限：全權限、只有 K1＋C1、只有 K1；另一案作業對象非空
   * @step 全權限者 | 兩張卡皆在；點「架構設計與檢視」 | 輸入列填入範例句並取得焦點，user_message 0 則
   * @step 只有 K1＋C1 | 只有成本卡
   * @step 只有 K1 | 兩張卡皆無，顯示「或直接說出你要做什麼」
   * @step 作業對象為專案 1 而紀錄為空 | 顯示「先前的對話大腦仍記得，只是這裡不再顯示」
   * @pass 卡片依權限且不自動送出
   * @story US8.1
   */
  test('空狀態卡片依權限顯示且點擊不送出', async ({ page, browser }) => {
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    await expect(page.getByTestId('brain-empty-card-architecture')).toBeVisible();
    await expect(page.getByTestId('brain-empty-card-cost')).toBeVisible();
    await page.getByTestId('brain-empty-card-architecture').click();
    await expect(page.getByTestId('brain-input')).toHaveValue('幫我畫一張電商網站的雲端架構圖');
    await expect(page.getByTestId('brain-input')).toBeFocused();
    await page.waitForTimeout(200);
    expect(h.server.framesOf('user_message')).toHaveLength(0);

    const open = async (perms: string[], shared?: Target) => {
      const ctx = await browser.newContext();
      const p = await ctx.newPage();
      const hh = await setup(p, { perms });
      if (shared) {
        hh.server.shared = shared;
        hh.server.names = { p1: `${M}-專案` };
      }
      await p.goto('/');
      await waitReady(p);
      return { ctx, p };
    };
    const costOnly = await open(['K1', 'C1']);
    await expect(costOnly.p.getByTestId('brain-empty-card-cost')).toBeVisible();
    await expect(costOnly.p.getByTestId('brain-empty-card-architecture')).toHaveCount(0);
    await costOnly.ctx.close();
    const bare = await open(['K1']);
    await expect(bare.p.getByTestId('brain-empty-card-cost')).toHaveCount(0);
    await expect(bare.p.getByTestId('brain-empty-card-architecture')).toHaveCount(0);
    await expect(bare.p.getByText('或直接說出你要做什麼')).toBeVisible();
    await bare.ctx.close();
    const remembered = await open(ALL_PERMS, { pid: '1', sid: null, did: null });
    await expect(remembered.p.getByTestId('brain-transcript-remembered')).toHaveText('先前的對話大腦仍記得，只是這裡不再顯示');
    await remembered.ctx.close();
  });

  /**
   * @purpose 未知 type 安全忽略（畫面不變、console 只記 type）；四種 error.code 的 message 原樣顯示（BR92.6）。
   * @ui / | 入口頁
   * @given /api/brain/ws 送一個未知 type 的訊框，再送四種 code 的 error
   * @step 送未知 type | 畫面沒有新增訊息、輸入列仍可用；console 有一筆含該 type、不含負載
   * @step 送 EMPTY_RESPONSE／INTERNAL_ERROR／UNAUTHORIZED／INVALID_REQUEST 四則 error | 四段 message 皆原樣出現
   * @pass 未知訊息不崩潰、錯誤訊息原樣呈現
   * @story US8.1
   */
  test('未知 type 安全忽略且四種錯誤原樣顯示', async ({ page }) => {
    const lines: string[] = [];
    page.on('console', (msg) => lines.push(msg.text()));
    const h = await setup(page);
    await page.goto('/');
    await waitReady(page);
    h.server.send(F.unknownTypeFrame(`${M}-mystery`, `${M}-負載`));
    await expect.poll(() => lines.some((l) => l.includes(`${M}-mystery`))).toBe(true);
    expect(lines.join('\n')).not.toContain(`${M}-負載`);
    await expect(page.getByTestId('brain-stream-message')).toHaveCount(0);
    await expect(page.getByTestId('brain-input')).toBeEnabled();
    const codes = ['EMPTY_RESPONSE', 'INTERNAL_ERROR', 'UNAUTHORIZED', 'INVALID_REQUEST'] as const;
    codes.forEach((code, i) => h.server.send(F.encodeFrame(F.errorFrame(`t-49-${i}`, code, `${M}-錯誤-${code}`))));
    for (const code of codes) await expect(conv(page).getByText(`${M}-錯誤-${code}`)).toBeVisible();
  });
});
