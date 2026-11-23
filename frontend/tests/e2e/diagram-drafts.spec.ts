import { test, expect, type Page, type Route, type WebSocketRoute } from '@playwright/test';
import * as F from '../../src/brain/testing/wsFrames';
import type { components } from '../../src/types/api';

/**
 * 261116-brain-create-diagram U3 draft-ui — 架構圖草稿的前端標示、手動存檔轉正式、可點選的新反問。
 *
 * **全部走 `page.route()`／`page.routeWebSocket()` 攔截，不打真實後端**（形狀沿用
 * `project-pages.spec.ts` 與 `entry-page.spec.ts`；依該兩檔的先例刻意不抽共用模組）。本檔測的是
 * 前端對 `diagram_status`（契約 C3）、`finalize`（契約 C2）與四種新反問（契約 C6）的消費；伺服器行為
 * 由 `backend/tests/test_diagram_drafts_api.py` 與 `test_brain_diagram_creation_flow.py` 承擔。
 * WebSocket 訊框只由 `src/brain/testing/wsFrames.ts` 產生（EPN-19）。
 *
 * **名稱穩定性（合併後不可改）**：TCMS 案例名稱為 `<describe> › <test>`。
 */

const M = 'e2e-drafts';
const SELF_ID = 5101;
const FULL = { view: true, edit: true, review: false };
const PERMS = { K1: FULL, K2: FULL, K3: FULL, K4: FULL, A1: FULL, A3: FULL };

/**
 * 修訂 1（審查 draft-ui R-06）：stub 的形狀由產生的 `MyDiagramItem` 推導——後端改名或增刪欄位時
 * `tsc` 會讓本檔紅燈，不會出現「stub 與真實回應分歧、案例仍綠」。
 */
type DiagramStub = components['schemas']['MyDiagramItem'];

type ClientFrame = { type: string; payload: Record<string, unknown> };

const FAKE_DRAWIO = `<!doctype html><html><body><script>
window.addEventListener('message', function () {});
window.__edit = function (xml) { parent.postMessage(JSON.stringify({ event: 'autosave', xml: xml }), '*'); };
parent.postMessage(JSON.stringify({ event: 'init' }), '*');
</script></body></html>`;

async function json(route: Route, status: number, body: unknown) {
  try {
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
  } catch {
    // 頁面已離開：忽略。
  }
}

/** 假大腦伺服器：hello → 快照；記錄客戶端訊框；測試以 `send` 推送伺服器訊框。 */
class BrainServer {
  ws: WebSocketRoute | null = null;
  frames: ClientFrame[] = [];

  async install(page: Page): Promise<void> {
    await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, (ws) => {
      this.ws = ws;
      ws.onMessage((raw) => {
        const data = JSON.parse(String(raw)) as ClientFrame;
        this.frames.push(data);
        if (data.type === 'hello') {
          const target = F.workTargetFrame('shared', null, null, null, null, null, null);
          for (const f of F.snapshotFrames(target)) ws.send(f);
        }
      });
    });
  }

  send(frame: string): void {
    this.ws?.send(frame);
  }

  framesOf(type: string): ClientFrame[] {
    return this.frames.filter((f) => f.type === type);
  }
}

interface World {
  diagrams: DiagramStub[];
  puts: { id: number; body: Record<string, unknown> }[];
  reviewPosts: number;
  brain: BrainServer;
}

async function setup(page: Page, diagrams: DiagramStub[]): Promise<World> {
  const world: World = { diagrams, puts: [], reviewPosts: 0, brain: new BrainServer() };
  await page.addInitScript(() => {
    sessionStorage.setItem('token', 'e2e-drafts-token');
  });
  // 後註冊者優先：先放兜底，再放具體端點。
  await page.route('**/api/**', (route) =>
    json(route, 200, route.request().method() === 'GET' ? [] : {})
  );
  await page.route('**/api/auth/me', (route) =>
    json(route, 200, {
      id: SELF_ID,
      username: `${M}-alice`,
      role: 'Project_Architect',
      is_active: true,
      authorization_status: 'approved',
      permissions: PERMS,
      pending_request: null,
    })
  );
  await page.route('**/api/hierarchy/projects', (route) =>
    json(route, 200, [
      { id: 10, name: `${M}-project`, owner_user_id: SELF_ID, is_default: false, created_at: '2026-11-01T00:00:00Z' },
    ])
  );
  await page.route('**/api/hierarchy/projects/10/systems', (route) =>
    json(route, 200, [
      { id: 100, project_id: 10, name: `${M}-system`, is_default: false, created_at: '2026-11-01T00:00:00Z' },
    ])
  );
  await page.route(/\/api\/requirements\/systems\/\d+\/fields$/, (route) =>
    json(route, 200, { system_id: 100, unfilled_count: 0, input_hint: '', groups: [] })
  );
  await page.route('**/api/collab/diagrams', (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return json(route, 200, world.diagrams);
  });
  await page.route(/\/api\/collab\/diagrams\/\d+$/, (route) => {
    const req = route.request();
    const id = Number(new URL(req.url()).pathname.split('/').pop());
    const d = world.diagrams.find((x) => x.id === id);
    if (req.method() === 'PUT' && d) {
      const body = JSON.parse(req.postData() ?? '{}') as Record<string, unknown>;
      world.puts.push({ id, body });
      if (body.finalize === true) d.diagram_status = 'ready';
      return json(route, 200, { status: 'success', message: 'ok', diagram_status: d.diagram_status });
    }
    if (req.method() === 'GET' && d) {
      return json(route, 200, {
        ...d,
        xml_data: '<mxGraphModel><root/></mxGraphModel>',
        shared_user_ids: [],
        can_edit: true,
        can_review: false,
      });
    }
    return json(route, 404, { detail: 'Diagram not found' });
  });
  await page.route('**/api/collab/workspace/bootstrap', (route) => {
    const d = world.diagrams[0];
    return json(route, 200, {
      diagram: d
        ? { id: d.id, title: d.title, xml_data: '<mxGraphModel><root/></mxGraphModel>', updated_at: d.updated_at,
            is_owner: true, shared_user_ids: [] }
        : null,
      messages: [],
      can_edit: true,
      can_review: false,
    });
  });
  await page.route('https://embed.diagrams.net/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: FAKE_DRAWIO })
  );
  await page.route('**/api/architecture/reviews', (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    world.reviewPosts += 1;
    const body = JSON.parse(route.request().postData() ?? '{}') as { diagram_id?: number };
    const d = world.diagrams.find((x) => x.id === body.diagram_id);
    if (d?.diagram_status === 'draft') {
      // 與後端 DRAFT_REJECTED_DETAIL 同字（契約 C4）。
      return json(route, 409, { detail: '這張圖還是草稿，請先完成產圖' });
    }
    return json(route, 500, { detail: 'not stubbed' });
  });
  await page.routeWebSocket('**/api/collab/ws/**', () => undefined);
  await world.brain.install(page);
  return world;
}

const draft = (id: number, title: string): DiagramStub => ({
  id,
  title,
  is_owner: true,
  system_id: 100,
  updated_at: '2026-11-17T00:00:00Z',
  diagram_status: 'draft',
});

const ready = (id: number, title: string): DiagramStub => ({ ...draft(id, title), diagram_status: 'ready' });

test.describe('Diagram drafts', () => {
  /**
   * @purpose 專案頁「系統的架構圖」把草稿標示為「草稿」，頂端的架構圖計數不計草稿（FR6.4、FR6.4a）。
   * @api GET /api/collab/diagrams -> 200 | 我的圖，含 diagram_status
   * @ui /projects/:projectId | 總覽籤的架構圖計數與「系統的架構圖」區
   * @given 專案 10 的系統 100 下有我的一張草稿與一張正式圖
   * @step 開啟專案總覽 | 系統列兩張圖都列出；只有草稿那一列帶「草稿」標示
   * @step 檢視頂端計數 | 架構圖計數為 1（不含草稿）
   * @pass 草稿可見、可辨識，且不被當成已完成的圖計數
   * @story FR6.4
   */
  test('marks drafts on the project page and leaves them out of the count', async ({ page }) => {
    await setup(page, [draft(7, `${M}-草稿圖`), ready(8, `${M}-正式圖`)]);
    await page.goto('/projects/10?tab=overview');
    const row = page.getByTestId('system-diagrams-100');
    await expect(row.getByTestId('system-diagram-item')).toHaveCount(2);
    await expect(row.getByTestId('system-diagram-draft-7')).toHaveText('草稿');
    await expect(row.getByTestId('system-diagram-draft-8')).toHaveCount(0);
    await expect(page.getByTestId('project-count-diagrams-value')).toHaveText('1');
  });

  /**
   * @purpose 工作區只有「儲存架構圖」按鈕會把草稿轉為正式；自動存檔不會（FR6.2、契約 C2）。
   * @api PUT /api/collab/diagrams/{diagram_id} -> 200 | 自動存檔與手動存檔
   * @ui /workspace | 架構圖選單與「儲存架構圖」按鈕
   * @given 上次開啟的圖是一張草稿（id 7）
   * @step 開啟工作區 | 架構圖選單中該圖標示「（草稿）」
   * @step 在畫布上編輯觸發自動存檔 | PUT 本體不含 finalize；選單仍標示草稿
   * @step 按「儲存架構圖」 | PUT 本體含 finalize:true；選單中該圖不再標示草稿
   * @pass 只有手動存檔帶 finalize，且標示隨之消失
   * @story FR6.2
   */
  test('only the save button turns a draft into a finished diagram', async ({ page }) => {
    const world = await setup(page, [draft(7, `${M}-草稿圖`)]);
    await page.goto('/workspace');
    const option = page.locator('[data-testid="workspace-diagram-option"][value="7"]');
    await expect(option).toHaveAttribute('data-draft', 'true');
    await expect(option).toContainText('（草稿）');

    const frame = page.frameLocator('iframe[src*="embed.diagrams.net"]');
    await expect(frame.locator('body')).toBeAttached();
    const drawio = page.frames().find((f) => f.url().includes('embed.diagrams.net'));
    await drawio?.evaluate(() =>
      (window as unknown as { __edit: (v: string) => void }).__edit('<mxGraphModel><root><mxCell id="x"/></root></mxGraphModel>')
    );
    await expect.poll(() => world.puts.length, { timeout: 10_000 }).toBeGreaterThanOrEqual(1);
    expect(world.puts[0].body).not.toHaveProperty('finalize');
    await expect(option).toHaveAttribute('data-draft', 'true');

    await page.getByTestId('workspace-save-diagram-button').click();
    await expect.poll(() => world.puts.some((p) => p.body.finalize === true)).toBe(true);
    await expect(option).not.toHaveAttribute('data-draft', 'true');
    await expect(option).not.toContainText('（草稿）');
  });

  /**
   * @purpose 大腦送出 pick_system 反問時，候選是可點的按鈕，提示文字說明要選系統，點選只送 candidateId（FR3.4、契約 C6）。
   * @ui / | 入口頁 brain-clarify
   * @given /api/brain/ws；使用者送出一句畫圖請求
   * @step 伺服器送 kind=pick_system、一個帶 systemId 的候選 | 出現「新的架構圖要建在哪個系統底下？」與該系統名稱的按鈕
   * @step 點選候選 | 送出 select_clarify_candidate，payload 恰為 {candidateId}，不含 systemId
   * @pass 反問可點選並繼續，且客戶端不送識別碼
   * @story FR3.4
   */
  test('lets the user pick a system from the brain clarify', async ({ page }) => {
    const world = await setup(page, []);
    await page.goto('/');
    await expect(page.getByTestId('brain-context-bar').first()).not.toHaveAttribute('data-state', 'connecting');
    await page.getByTestId('brain-input').fill(`${M}-幫我畫一張電商架構圖`);
    await page.getByTestId('brain-send').click();
    world.brain.send(
      F.encodeFrame(
        F.clarifyFrame('t-pick', 'pick_system', [
          ['system-1', `${M}-system（專案：${M}-project）`, 'architecture-design', { systemId: '100' }],
        ])
      )
    );
    const group = page.locator('[data-testid="brain-clarify"][data-kind="pick_system"]');
    await expect(group).toContainText('新的架構圖要建在哪個系統底下？');
    // 修訂 1（R-08）：群組名稱依 kind 給，念出來的是「選系統」而不是泛稱「哪一個」。
    await expect(group).toHaveAttribute('aria-label', '請選擇新架構圖要建在哪個系統');
    await group.getByTestId('brain-clarify-candidate-system-1').click();
    await expect.poll(() => world.brain.framesOf('select_clarify_candidate').length).toBe(1);
    expect(world.brain.framesOf('select_clarify_candidate')[0].payload).toEqual({ candidateId: 'system-1' });
  });

  /**
   * @purpose 修訂 1（FR6.4，審查 draft-ui R-05）：專案頁「把架構圖掛到…」下拉也要標示草稿，
   *          避免使用者不知情地把草稿搬到別的系統。
   * @api GET /api/collab/diagrams -> 200 | 我的圖，含 diagram_status
   * @ui /projects/:projectId | 系統列的掛圖下拉
   * @given 我有一張未掛載的草稿（id 7）與一張未掛載的正式圖（id 8）
   * @step 開啟專案總覽 | 系統 100 的掛圖下拉出現兩個選項
   * @step 檢視選項文字 | 草稿的選項帶「（草稿）」且 data-draft=true；正式圖的不帶
   * @pass 掛圖下拉可辨識草稿
   * @story FR6.4
   */
  test('marks drafts in the attach-diagram dropdown', async ({ page }) => {
    await setup(page, [
      { ...draft(7, `${M}-草稿圖`), system_id: null },
      { ...ready(8, `${M}-正式圖`), system_id: null },
    ]);
    await page.goto('/projects/10?tab=overview');
    const draftOption = page.getByTestId('attach-candidate-7');
    const readyOption = page.getByTestId('attach-candidate-8');
    await expect(draftOption).toHaveAttribute('data-draft', 'true');
    await expect(draftOption).toHaveText(`${M}-草稿圖（草稿）`);
    await expect(readyOption).toHaveAttribute('data-draft', 'false');
    await expect(readyOption).toHaveText(`${M}-正式圖`);
  });

  /**
   * @purpose 修訂 1（FR6.4、FR6.4a，審查 R-04）：評核頁的架構圖下拉標示草稿；對草稿發起評核被 409 拒絕時，
   *          畫面顯示 detail 的句子而不是原始 JSON。
   * @api POST /api/architecture/reviews -> 409 | 草稿被拒
   * @ui /assessment | 架構圖下拉與錯誤訊息
   * @given 我有一張草稿（id 7）
   * @step 開啟評核頁 | 下拉中該圖帶「（草稿）」且 data-draft=true
   * @step 選該圖並按「執行評核」 | 送出一次評核請求，收到 409
   * @step 檢視錯誤訊息 | 顯示「這張圖還是草稿，請先完成產圖」，不含「{"detail"」
   * @pass 草稿可辨識，被拒時訊息可讀
   * @story FR6.4a
   */
  test('marks drafts on the assessment page and shows a readable rejection', async ({ page }) => {
    const world = await setup(page, [draft(7, `${M}-草稿圖`)]);
    await page.goto('/assessment');
    const option = page.getByTestId('assessment-diagram-option-7');
    await expect(option).toHaveAttribute('data-draft', 'true');
    await expect(option).toHaveText(`${M}-草稿圖（草稿）`);
    await page.locator('select:has([data-testid="assessment-diagram-option-7"])').selectOption('7');
    await page.getByRole('button', { name: '執行評核' }).click();
    await expect.poll(() => world.reviewPosts).toBe(1);
    await expect(page.getByText('這張圖還是草稿，請先完成產圖')).toBeVisible();
    await expect(page.getByText('{"detail"', { exact: false })).toHaveCount(0);
  });
});
