import { test, expect, type Page, type WebSocketRoute } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import * as F from '../../src/brain/testing/wsFrames';

// ---------------------------------------------------------------------------
// 部署後追加（2026-11-15）：全站大腦小助手與全站一條大腦連線。
//
// **本階段新增、已核可 requirements／user-stories 尚未涵蓋**（使用者以選單選定「全站統一用小助手」）。它取代
// `[EP1]`=A 的子頁面「問大腦」收合面板；工作區與評估頁既有的設計／評核對話區不動。回補項見
// `aidlc/spaces/default/intents/260920-orchestration-brain/operation/followups/global-brain-assistant.md`；
// 2026-11-16 已回補為 `FR14.5`／`US14.5`，規格註解改指 `US14.5`。
//
// 全部走攔截層：`page.routeWebSocket` 扮演大腦伺服器（形狀沿用 `object-picker.spec.ts` 的 BrainServer，刻意不抽
// 共用模組：不改已交付單元的 spec），`page.route` 樁化 HTTP。伺服器訊框只由 `src/brain/testing/wsFrames.ts`
// 產生（EPN-19）。
// ---------------------------------------------------------------------------

const M = 'e2e-assistant';
const FULL = { view: true, edit: true, review: false };
const ALL_PERMS = ['K1', 'K2', 'K3', 'K4', 'A1', 'A3', 'C1'];

type ClientFrame = { type: string; payload: Record<string, unknown> };

class AssistantBrainServer {
  conns: { ws: WebSocketRoute; frames: ClientFrame[] }[] = [];
  shared = { pid: null as string | null, sid: null as string | null, did: null as string | null };

  async install(page: Page): Promise<void> {
    await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, (ws) => {
      const conn = { ws, frames: [] as ClientFrame[] };
      this.conns.push(conn);
      ws.onMessage((raw) => {
        const data = JSON.parse(String(raw)) as ClientFrame;
        conn.frames.push(data);
        if (data.type === 'hello') {
          const t = this.shared;
          const target = F.workTargetFrame('shared', t.pid, t.sid, t.did, t.pid ? `${M}-專案` : null, null, null);
          for (const f of F.snapshotFrames(target)) ws.send(f);
        }
      });
    });
  }

  get last() {
    return this.conns[this.conns.length - 1];
  }

  send(frames: string[]): void {
    for (const f of frames) this.last.ws.send(f);
  }

  framesOf(type: string): ClientFrame[] {
    return this.conns.flatMap((c) => c.frames.filter((f) => f.type === type));
  }
}

interface Harness {
  server: AssistantBrainServer;
  /**
   * 頁面內 `new WebSocket(<大腦路徑>)` 的次數（含已關閉者），以 init script 包住 `window.WebSocket` 計得。
   * 不用 `page.on('websocket')`：連線被 `page.routeWebSocket` 攔下、不連到真實伺服器時，該事件不會觸發
   * （本輪實測恆為 0，見 followups/global-brain-assistant.md），以它計數會讓斷言永遠通過或永遠失敗。
   */
  brainSockets: () => Promise<number>;
}

async function setup(page: Page, perms: string[] = ALL_PERMS): Promise<Harness> {
  const server = new AssistantBrainServer();
  await page.addInitScript(() => {
    sessionStorage.setItem('token', 'e2e-assistant-token');
    const w = window as unknown as { __brainSockets: number };
    w.__brainSockets = 0;
    // routeWebSocket 也會替換 window.WebSocket（在本 script 之後）：以 accessor 接住每一次替換，取用時回傳
    // 包住「目前那一個」實作的子類別，使計數不受安裝順序影響。
    const wrap = (Impl: typeof WebSocket): typeof WebSocket =>
      class extends Impl {
        constructor(url: string | URL, protocols?: string | string[]) {
          super(url, protocols);
          if (/\/api\/brain\/ws/.test(String(url))) w.__brainSockets += 1;
        }
      };
    let current = window.WebSocket;
    let wrapped = wrap(current);
    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      get: () => wrapped,
      set: (next: typeof WebSocket) => {
        current = next;
        wrapped = wrap(current);
      },
    });
  });
  // 後註冊者優先：先放兜底，再放具體端點。
  await page.route('**/api/**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: route.request().method() === 'GET' ? '[]' : '{}',
    })
  );
  await page.route('**/api/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 7,
        username: `${M}-alice`,
        role: 'Platform_Admin',
        is_active: true,
        authorization_status: 'approved',
        permissions: Object.fromEntries(perms.map((p) => [p, FULL])),
        pending_request: null,
      }),
    })
  );
  await page.route('**/api/hierarchy/projects', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 10, name: `${M}-專案`, owner_user_id: 7, is_default: false, created_at: '2026-09-01T00:00:00Z' },
      ]),
    })
  );
  await page.route('**/api/collab/workspace/bootstrap', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ diagram: null, messages: [] }) })
  );
  await page.route('https://embed.diagrams.net/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><html><body></body></html>' })
  );
  await page.routeWebSocket('**/api/collab/ws/**', () => undefined);
  await server.install(page);
  return {
    server,
    brainSockets: () => page.evaluate(() => (window as unknown as { __brainSockets: number }).__brainSockets),
  };
}

function toggle(page: Page) {
  return page.getByTestId('brain-assistant-toggle');
}

function assistantWindow(page: Page) {
  return page.getByTestId('brain-assistant-window');
}

async function openAssistant(page: Page): Promise<void> {
  await toggle(page).click();
  await expect(assistantWindow(page)).toBeVisible();
  await expect(assistantWindow(page).getByTestId('brain-assistant-context-bar')).toHaveAttribute('data-state', /no-object|default/);
}

async function say(page: Page, text: string): Promise<void> {
  const w = assistantWindow(page);
  await w.getByTestId('brain-input').fill(text);
  await w.getByTestId('brain-send').click();
}

test.describe('Global brain assistant', () => {
  /**
   * @purpose 浮動小助手只給有 K1 的使用者、只在入口頁以外出現：專案、記憶、成本頁都看得到按鈕；入口頁本身是整頁對話不顯示；沒有 K1 的使用者任何頁都看不到。
   * @ui / | 入口頁
   * @ui /projects/:projectId | 專案詳情頁右下角的小助手按鈕
   * @ui /memory | 我的記憶頁右下角的小助手按鈕
   * @ui /cost | 成本頁右下角的小助手按鈕
   * @given 具 K1 的使用者；另一個 browser context 是只有 K2／C1、沒有 K1 的使用者
   * @step 具 K1 者開啟 / | brain-entry-page 可見、brain-assistant-toggle 0 個
   * @step 依序開啟 /projects/10、/memory、/cost | 每頁都有 1 個 brain-assistant-toggle，aria-label 為「開啟大腦小助手」
   * @step 無 K1 者開啟 /projects/10、/memory、/cost | 三頁的 brain-assistant-toggle 都是 0 個，大腦連線 0 條
   * @pass 有 K1 時三頁皆有、入口頁沒有；無 K1 時都沒有
   * @story US14.5
   */
  test('shows the assistant button on non-entry pages only for K1 users', async ({ page, browser }) => {
    await setup(page);
    await page.goto('/');
    await expect(page.getByTestId('brain-entry-page')).toBeVisible();
    await expect(toggle(page)).toHaveCount(0);
    for (const path of ['/projects/10', '/memory', '/cost']) {
      await page.goto(path);
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await expect(toggle(page)).toHaveCount(1);
      await expect(toggle(page)).toHaveAttribute('aria-label', '開啟大腦小助手');
    }

    const ctx = await browser.newContext({ baseURL: test.info().project.use.baseURL });
    const other = await ctx.newPage();
    const h = await setup(other, ['K2', 'C1']);
    for (const path of ['/projects/10', '/memory', '/cost']) {
      await other.goto(path);
      await expect(other).toHaveURL(new RegExp(`${path}$`));
      await other.waitForLoadState('networkidle');
      await expect(toggle(other)).toHaveCount(0);
    }
    expect(h.server.conns.length).toBe(0);
    await ctx.close();
  });

  /**
   * @purpose 在專案頁從小助手送出：user_message 帶由路由推導的 page（專案頁＝entry，讀寫共享段），收到回覆後顯示在小助手內；展開時焦點在輸入框。
   * @ui /projects/:projectId | 專案詳情頁的小助手對話窗
   * @given 具 K1 的使用者；大腦連線就緒
   * @step 開啟 /projects/10，按小助手按鈕 | 對話窗出現、焦點在 brain-input、窗頂作業對象列可見
   * @step 輸入一句並送出 | 大腦連線收到 1 則 user_message，payload.page 為 entry、text 為原句
   * @step 伺服器回一輪 token＋done | 回覆文字出現在小助手的對話區
   * @pass page 為 entry 且回覆顯示在小助手內
   * @story US14.5
   */
  test('sends from the project page with the routed page and shows the reply', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/projects/10');
    await openAssistant(page);
    await expect(assistantWindow(page).getByTestId('brain-input')).toBeFocused();
    await say(page, `${M}-專案頁的話`);
    await expect.poll(() => h.server.framesOf('user_message').length).toBe(1);
    expect(h.server.framesOf('user_message')[0].payload).toEqual({ text: `${M}-專案頁的話`, page: 'entry' });
    h.server.send(F.turnFrames('t-a1', `${M}-專案頁的回覆`));
    await expect(assistantWindow(page).getByTestId('brain-conversation')).toContainText(`${M}-專案頁的回覆`);
  });

  /**
   * @purpose 換頁後小助手的對話與展開狀態都保留，入口頁與小助手讀同一段；整個過程只開過一條大腦 WebSocket（全站一條，不隨換頁重連）。
   * @ui /projects/:projectId | 專案詳情頁的小助手
   * @ui /memory | 我的記憶頁的小助手
   * @ui /cost | 成本頁的小助手
   * @ui / | 入口頁
   * @given 具 K1 的使用者；以包住 window.WebSocket 的 init script 計數頁面建立的大腦連線
   * @step 在 /projects/10 展開小助手、送一句並收到回覆 | 回覆出現在小助手
   * @step 經 Sidebar 換到 /memory、再換到 /cost | 小助手仍是展開的（對話窗可見、按鈕 aria-expanded=true），原句與回覆都還在
   * @step 換到入口頁 / | 小助手不顯示；入口頁對話區有同一句原句與回覆（同一段、只有一份）
   * @step 統計大腦 WebSocket | 頁面建立的大腦 WebSocket 1 條、攔截層收到 1 條、hello 1 則
   * @pass 狀態與紀錄跨頁保留，且全程只有一條連線
   * @story US14.5
   */
  test('keeps the conversation and open state across pages over a single websocket', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/projects/10');
    await openAssistant(page);
    await say(page, `${M}-留著的話`);
    await expect.poll(() => h.server.framesOf('user_message').length).toBe(1);
    h.server.send(F.turnFrames('t-a2', `${M}-留著的回覆`));
    await expect(assistantWindow(page).getByTestId('brain-conversation')).toContainText(`${M}-留著的回覆`);

    for (const path of ['/memory', '/cost']) {
      await page.locator(`a[href="${path}"]`).first().click();
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await expect(assistantWindow(page)).toBeVisible();
      await expect(toggle(page)).toHaveAttribute('aria-expanded', 'true');
      const conv = assistantWindow(page).getByTestId('brain-conversation');
      await expect(conv.getByText(`${M}-留著的話`, { exact: true })).toBeVisible();
      await expect(conv).toContainText(`${M}-留著的回覆`);
    }

    await page.getByTestId('sidebar-entry-link').click();
    await expect(page.getByTestId('brain-entry-page')).toBeVisible();
    await expect(toggle(page)).toHaveCount(0);
    const entryConv = page.getByTestId('brain-conversation');
    await expect(entryConv).toHaveCount(1);
    await expect(entryConv.getByText(`${M}-留著的話`, { exact: true })).toHaveCount(1);
    await expect(entryConv).toContainText(`${M}-留著的回覆`);

    expect(await h.brainSockets()).toBe(1);
    expect(h.server.conns.length).toBe(1);
    expect(h.server.framesOf('hello')).toHaveLength(1);
  });

  /**
   * @purpose 工作區不再有「問大腦」收合面板，改由小助手取代；作業對象列（含共享／獨立切換）仍在頁上；小助手在工作區送出的 user_message 帶 page=workspace。
   * @ui /workspace | 工作區的作業對象列與小助手
   * @given 具 K1／A1 的使用者；bootstrap 無上次的圖
   * @step 開啟 /workspace | brain-subpage-panel 0 個；頁上 brain-context-bar 1 個且有「改為獨立對話」；brain-assistant-toggle 1 個
   * @step 量測按鈕與畫布 iframe 的位置 | 按鈕不與畫布底部 32px 狀態列的右端 96px（縮放比例選單）重疊
   * @step 展開小助手並送出一句 | user_message.payload.page 為 workspace
   * @pass 面板已移除、作業對象列保留、小助手可用且帶本頁 page、不遮住畫布縮放控件
   * @story US14.5
   */
  test('replaces the workspace ask-brain panel with the assistant and keeps the target bar', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/workspace');
    await expect(page.getByTestId('brain-context-bar')).not.toHaveAttribute('data-state', 'connecting');
    await expect(page.getByTestId('brain-subpage-panel')).toHaveCount(0);
    await expect(page.getByTestId('brain-context-bar')).toHaveCount(1);
    await expect(page.getByTestId('brain-context-sharing-switch')).toHaveText('改為獨立對話');
    await expect(toggle(page)).toHaveCount(1);
    // draw.io（ui=min）的狀態列在畫布底部 32px，右端是縮放比例選單：按鈕不得與畫布右下角這一塊重疊。
    const canvas = await page.locator('iframe[title="draw.io diagram"]').boundingBox();
    const button = await toggle(page).boundingBox();
    expect(canvas).not.toBeNull();
    expect(button).not.toBeNull();
    const stripTop = canvas!.y + canvas!.height - 32;
    const overlapsCorner =
      button!.y + button!.height > stripTop && button!.x + button!.width > canvas!.x + canvas!.width - 96;
    expect(overlapsCorner, JSON.stringify({ canvas, button })).toBe(false);
    await openAssistant(page);
    await say(page, `${M}-工作區的話`);
    await expect.poll(() => h.server.framesOf('user_message').length).toBe(1);
    expect(h.server.framesOf('user_message')[0].payload).toMatchObject({ page: 'workspace' });
  });

  /**
   * @purpose 小助手可用 Esc 關閉：焦點在輸入框時按 Esc，對話窗關閉、焦點回到小助手按鈕；作業對象選單開著時 Esc 只關選單、不關小助手。收合期間有新回覆時按鈕帶未讀提示。
   * @ui /memory | 我的記憶頁的小助手
   * @given 具 K1 的使用者；在 /memory
   * @step 展開小助手，開啟窗頂的「切換對象」後按 Esc | 作業對象選單關閉，小助手對話窗仍在
   * @step 焦點移到輸入框後按 Esc | 對話窗消失；焦點在 brain-assistant-toggle，aria-expanded=false
   * @step 收合狀態下伺服器回一輪 | 按鈕 data-unread=true、aria-label「開啟大腦小助手（有新回覆）」
   * @step 再展開 | 未讀提示消失
   * @pass Esc 關閉且焦點正確；未讀提示只在收合期間出現
   * @story US14.5
   */
  test('closes with Escape, returns focus to the button and flags unread replies', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/memory');
    await openAssistant(page);
    await assistantWindow(page).getByTestId('brain-assistant-context-switch-object').click();
    await expect(page.getByTestId('brain-object-picker')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('brain-object-picker')).toHaveCount(0);
    await expect(assistantWindow(page)).toBeVisible();

    await assistantWindow(page).getByTestId('brain-input').focus();
    await page.keyboard.press('Escape');
    await expect(assistantWindow(page)).toHaveCount(0);
    await expect(toggle(page)).toBeFocused();
    await expect(toggle(page)).toHaveAttribute('aria-expanded', 'false');

    await expect(toggle(page)).toHaveAttribute('data-unread', 'false');
    h.server.send(F.turnFrames('t-a3', `${M}-收合時的回覆`));
    await expect(toggle(page)).toHaveAttribute('data-unread', 'true');
    await expect(toggle(page)).toHaveAttribute('aria-label', '開啟大腦小助手（有新回覆）');
    await toggle(page).click();
    await expect(assistantWindow(page)).toContainText(`${M}-收合時的回覆`);
    await expect(toggle(page)).toHaveAttribute('data-unread', 'false');
  });

  /**
   * @purpose 小助手展開時的無障礙掃描：對話窗（含作業對象列、對話區、輸入框）在 WCAG 2.1 A／AA 規則下沒有違規。
   * @ui /cost | 成本頁的小助手對話窗
   * @given 具 K1 的使用者；在 /cost 展開小助手且有一輪對話
   * @step 以 axe（`wcag2a`、`wcag2aa`、`wcag21a`、`wcag21aa`）只掃 `brain-assistant-window` | violations 為 0 個（空陣列 `[]`）
   * @pass 0 個違規
   * @story US14.5
   */
  test('passes an axe scan with the assistant open', async ({ page }) => {
    const h = await setup(page);
    await page.goto('/cost');
    await openAssistant(page);
    await say(page, `${M}-掃描用`);
    await expect.poll(() => h.server.framesOf('user_message').length).toBe(1);
    h.server.send(F.turnFrames('t-a4', `${M}-掃描用回覆`));
    await expect(assistantWindow(page)).toContainText(`${M}-掃描用回覆`);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .include('[data-testid="brain-assistant-window"]')
      .analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
  });
});
