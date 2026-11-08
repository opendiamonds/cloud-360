import { expect, test, type Page, type Route } from '@playwright/test';

/**
 * U2 IaC workspace. API calls are page.route stubs. This file does not call a model.
 */

const ADMIN = { username: 'admin', password: 'admin123' };
const FIXTURE_PLAINTEXT = 'fixture-plaintext-do-not-render';
const PREVIEW = 'resource "aws_s3_bucket" "fixture" {}';
const KEEP = 'preview-keep-marker';

type StoryPermission = {
  view: boolean;
  edit: boolean;
  review: boolean;
  can_view: boolean;
  can_edit: boolean;
  can_review: boolean;
};

function storyPermission(view: boolean, edit: boolean): StoryPermission {
  return {
    view: view || edit,
    edit,
    review: false,
    can_view: view,
    can_edit: edit,
    can_review: false,
  };
}

const NO_D1: StoryPermission = {
  view: false,
  edit: false,
  review: false,
  can_view: false,
  can_edit: false,
  can_review: false,
};

async function login(page: Page, username: string, password: string) {
  await page.goto('/');
  await page.getByPlaceholder('請輸入您的帳號').fill(username);
  await page.getByPlaceholder('請輸入密碼').fill(password);
  await page.getByRole('button', { name: '登入系統' }).click();
  await expect(page).toHaveURL(/\/(workspace|cost)/);
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

async function stubMe(page: Page, stories: Record<string, StoryPermission>) {
  await page.route('**/api/auth/me', async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.permissions = { ...(json.permissions ?? {}), ...stories };
    await fulfillJson(route, json);
  });
}

async function stubCollab(page: Page, diagram: { id: number; title: string } | null) {
  await page.route('**/api/collab/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    if (path.endsWith('/workspace/bootstrap') && method === 'GET') {
      await fulfillJson(route, {
        diagram: diagram
          ? {
              id: diagram.id,
              title: diagram.title,
              xml_data: '<mxGraphModel><root></root></mxGraphModel>',
              is_owner: true,
            }
          : null,
        messages: [],
      });
      return;
    }
    if (path.endsWith('/diagrams') && method === 'GET') {
      await fulfillJson(
        route,
        diagram
          ? [
              {
                id: diagram.id,
                title: diagram.title,
                is_owner: true,
                updated_at: '2026-01-01T00:00:00Z',
              },
            ]
          : [],
      );
      return;
    }
    await fulfillJson(route, { messages: [], id: diagram?.id ?? null });
  });
}

function draft(content: string, diagramId = 42) {
  return {
    draft_id: 'draft-fixture',
    diagram_id: diagramId,
    status: 'succeeded',
    created_at: '2026-01-01T00:00:00Z',
    module_tree: {
      files: [
        { path: 'main.tf', content },
        { path: 'variables.tf', content: 'variable "name" {}' },
        { path: 'outputs.tf', content: 'output "id" { value = "fixture" }' },
      ],
    },
  };
}

function scanReport(severity: 'HIGH' | 'LOW') {
  return {
    report_id: 'report-fixture',
    draft_id: 'draft-fixture',
    diagram_id: 42,
    status: 'succeeded',
    max_severity: severity,
    created_at: '2026-01-01T00:00:00Z',
    findings: [
      {
        id: 'finding-fixture',
        severity,
        title: 'fixture-finding',
        detail: 'checked',
        path: 'main.tf',
      },
    ],
  };
}

async function stubEmptySession(page: Page) {
  await page.route('**/api/iac/session*', async (route) => {
    const id = Number(new URL(route.request().url()).searchParams.get('diagram_id') || 0);
    await fulfillJson(route, {
      diagram_id: id,
      draft: null,
      latest_scan: null,
      latest_rewrite: null,
    });
  });
}

async function openWorkspace(page: Page) {
  await page.getByTestId('iac-entry').click();
  await expect(page.getByTestId('iac-workspace')).toBeVisible();
}

test.describe('IaC 工作區', () => {
  /**
   * @purpose 沒有 D1 view 的人看得到入口，但入口是 disabled，點了也不會打開步驟殼。
   * @given seed 帳號 admin / admin123；/api/auth/me 的 D1 view 與 edit 皆為 false
   * @api POST /api/auth/login -> 200 | 帳密驗證
   * @api GET /api/auth/me -> 200 | 權限被 stub 成沒有 D1 view
   * @ui /workspace | IaC 入口 iac-entry 與缺權說明
   * @step 登入後檢視工作區工具列 | 出現 `iac-entry`，且為 disabled，並出現「缺少 D1 view 權限」
   * @step 對 disabled 入口送出點擊 | `iac-step-generate` 的數量為 0
   * @pass 入口維持 disabled，步驟殼沒有打開
   * @story US1.1
   */
  test('無 D1 view 時入口不可進入工作區', async ({ page }) => {
    await stubMe(page, { D1: NO_D1 });
    await login(page, ADMIN.username, ADMIN.password);
    const entry = page.getByTestId('iac-entry');
    await expect(entry).toBeDisabled();
    await expect(page.getByText('缺少 D1 view 權限，無法進入 IaC 工作區。')).toBeVisible();
    await entry.click({ force: true });
    await expect(page.getByTestId('iac-step-generate')).toHaveCount(0);
  });

  /**
   * @purpose 有 D1 view 的人可以從 Workspace 進入 IaC 殼，並看到選圖控制項。
   * @given seed 帳號 admin / admin123，角色具 D1 view
   * @api POST /api/auth/login -> 200 | 帳密驗證
   * @api GET /api/auth/me -> 200 | 讀取權限
   * @ui /workspace | IaC 工作區選圖 iac-diagram-select
   * @step 登入後點 `iac-entry` | 出現 `iac-workspace`
   * @step 檢視畫面上方 | 出現 `iac-diagram-select`
   * @pass 選圖控制項可見，且網址仍含 /workspace
   * @story US1.2
   */
  test('有 D1 view 時可進入工作區並看到選圖', async ({ page }) => {
    await stubCollab(page, null);
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page.getByTestId('iac-entry')).toBeEnabled();
    await openWorkspace(page);
    await expect(page.getByTestId('iac-diagram-select')).toBeVisible();
    await expect(page.getByTestId('iac-diagram-upload')).toBeVisible();
    await expect(page).toHaveURL(/\/workspace/);
  });

  /**
   * @purpose 沒有架構圖時主區擋住產生，並提供回到 Workspace 的控制項。
   * @given 圖清單與 bootstrap 皆為空；使用者有 D1 view
   * @api GET /api/auth/me -> 200 | 讀取權限
   * @ui /workspace | 無圖阻擋與 iac-run-d1
   * @step 進入 IaC 工作區 | 出現「尚無架構圖，無法產生 IaC。」與 `iac-back-workspace`
   * @step 檢視產生按鈕 | `iac-run-d1` 為 disabled
   * @pass 無圖時不能按下產生，且看得到回 Workspace 的控制項
   * @story US1.2
   */
  test('無架構圖時主區阻擋且不能產生', async ({ page }) => {
    await stubCollab(page, null);
    await login(page, ADMIN.username, ADMIN.password);
    await openWorkspace(page);
    await expect(page.getByText('尚無架構圖，無法產生 IaC。')).toBeVisible();
    await expect(page.getByTestId('iac-back-workspace')).toBeVisible();
    await expect(page.getByTestId('iac-run-d1')).toBeDisabled();
  });

  /**
   * @purpose 有圖且有 D1 edit 時，產生請求帶 diagram_id，檔案樹與預覽出現 stub 內容。
   * @given 架構圖 id 為 42；/api/iac/generate 由 route stub 回傳 main.tf
   * @api POST /api/iac/generate -> 200 | 回傳草稿檔案樹
   * @api GET /api/iac/session -> 200 | 空的工作階段
   * @ui /workspace | iac-file-tree 與 iac-hcl-preview
   * @step 按 `iac-run-d1` | POST /api/iac/generate 的 diagram_id 為 42
   * @step 檢視檔案樹與預覽 | 出現 `main.tf` 與 stub 的 HCL 片段
   * @pass 檔名與預覽文字與 stub 相同，且沒有呼叫真實模型
   * @story US2.1
   */
  test('產生請求帶 diagram_id 並顯示檔案樹與預覽', async ({ page }) => {
    let diagramId: number | null = null;
    await stubMe(page, {
      D1: storyPermission(true, true),
      D2: storyPermission(true, true),
      D3: storyPermission(true, true),
    });
    await stubCollab(page, { id: 42, title: 'Fixture diagram' });
    await stubEmptySession(page);
    await page.route('**/api/iac/generate', async (route) => {
      const body = route.request().postDataJSON() as { diagram_id?: number };
      diagramId = body.diagram_id ?? null;
      await fulfillJson(route, { draft: draft(PREVIEW, diagramId ?? 42) });
    });
    await login(page, ADMIN.username, ADMIN.password);
    await openWorkspace(page);
    await expect(page.getByTestId('iac-diagram-select')).toHaveValue('42');
    await page.getByTestId('iac-run-d1').click();
    await expect(page.getByTestId('iac-file-tree')).toContainText('main.tf');
    await expect(page.getByTestId('iac-hcl-preview')).toContainText(PREVIEW);
    expect(diagramId).toBe(42);
  });

  /**
   * @purpose 產生回傳錯誤碼時顯示對照文案，且先前預覽文字仍在。
   * @given 第一次 generate 回傳含 preview-keep-marker 的草稿；第二次回 422 generate_failed
   * @api POST /api/iac/generate -> 200 | 第一次回傳可預覽草稿
   * @api POST /api/iac/generate -> 422 | 第二次 error.code 為 generate_failed
   * @ui /workspace | 預覽區與產生失敗文案
   * @step 第一次按產生 | 預覽出現 `preview-keep-marker`
   * @step 第二次按產生 | 出現「產生失敗，請重試」，且 `preview-keep-marker` 仍在
   * @pass 錯誤文案來自 error.code，舊預覽沒有被清掉
   * @story US2.3
   */
  test('產生失敗時保留先前預覽並顯示錯誤文案', async ({ page }) => {
    let calls = 0;
    await stubMe(page, { D1: storyPermission(true, true) });
    await stubCollab(page, { id: 42, title: 'Fixture diagram' });
    await stubEmptySession(page);
    await page.route('**/api/iac/generate', async (route) => {
      calls += 1;
      if (calls === 1) {
        await fulfillJson(route, { draft: draft(KEEP) });
        return;
      }
      await fulfillJson(route, { error: { code: 'generate_failed', message: 'raw-should-not-be-required' } }, 422);
    });
    await login(page, ADMIN.username, ADMIN.password);
    await openWorkspace(page);
    await expect(page.getByTestId('iac-diagram-select')).toHaveValue('42');
    await page.getByTestId('iac-run-d1').click();
    await expect(page.getByTestId('iac-hcl-preview')).toContainText(KEEP);
    await page.getByTestId('iac-run-d1').click();
    await expect(page.getByText('產生失敗，請重試')).toBeVisible();
    await expect(page.getByTestId('iac-hcl-preview')).toContainText(KEEP);
    await expect(page.getByTestId('iac-retry')).toBeVisible();
  });

  /**
   * @purpose 掃描頁由側邊選單進入；沒有草稿時不能掃架構圖；session 有草稿時嚴重度以文字出現。
   * @given session 一開始沒有草稿；之後回傳 main.tf；scan stub 回傳 severity HIGH
   * @api GET /api/iac/session -> 200 | 先空、後有草稿
   * @api POST /api/iac/scan -> 200 | 回傳含 HIGH 的 finding
   * @ui /iac/scan | iac-run-d2、iac-findings
   * @step 打開 IaC 安全掃描並選擇架構圖 42 | `iac-run-d2` 為 disabled，並出現「尚無草稿，無法掃描。」
   * @step session 改回傳草稿後重新載入 | `iac-findings` 出現文字 `HIGH`
   * @pass 嚴重度不只有顏色，空草稿時掃描鈕不可按，頁面沒有頁內步驟鈕
   * @story US3.1
   */
  test('掃描步驟可直接打開且嚴重度以文字顯示', async ({ page }) => {
    let includeDraft = false;
    await stubMe(page, {
      D1: storyPermission(true, true),
      D2: storyPermission(true, true),
    });
    await stubCollab(page, { id: 42, title: 'Fixture diagram' });
    await page.route('**/api/iac/session*', async (route) => {
      const id = Number(new URL(route.request().url()).searchParams.get('diagram_id') || 0);
      await fulfillJson(route, {
        diagram_id: id,
        draft: includeDraft ? draft(PREVIEW, id) : null,
        latest_scan: null,
        latest_rewrite: null,
      });
    });
    await page.route('**/api/iac/scan', async (route) => {
      await fulfillJson(route, { report: scanReport('HIGH') });
    });
    await login(page, ADMIN.username, ADMIN.password);
    await page.getByTestId('nav-iac-scan').click();
    await expect(page).toHaveURL(/\/iac\/scan$/);
    await expect(page.getByTestId('iac-step-scan')).toHaveCount(0);
    await page.getByTestId('iac-diagram-select').selectOption('42');
    await expect(page.getByTestId('iac-run-d2')).toBeDisabled();
    await expect(page.getByText('尚無草稿，無法掃描。')).toBeVisible();
    includeDraft = true;
    await page.reload();
    await expect(page.getByTestId('iac-run-d2')).toBeEnabled();
    await page.getByTestId('iac-run-d2').click();
    await expect(page.getByTestId('iac-findings')).toContainText('HIGH');
    await expect(page.getByTestId('iac-findings')).toContainText('fixture-finding');
  });

  /**
   * @purpose 沒有掃描報告時不能改寫；改寫結果清單不得出現測試注入的明文樣式。
   * @given rewrite stub 的 rewritten_paths 只有 main.tf，明文只放在未被畫面讀取的欄位
   * @api POST /api/iac/secrets/rewrite -> 200 | 回傳改寫路徑，不含畫面應顯示的明文
   * @ui /iac/secrets | iac-run-d3 與 iac-rewrite-list
   * @step 在沒有掃描報告時打開 Secret／敏感值 | `iac-run-d3` 為 disabled，並出現「需要已完成的掃描報告，才能改寫。」
   * @step session 帶掃描報告後執行改寫 | `iac-rewrite-list` 含 `main.tf`，且不含 `fixture-plaintext-do-not-render`
   * @pass 清單只顯示路徑，畫面沒有渲染注入的明文樣式
   * @story US4.1
   */
  test('改寫清單不包含注入的明文', async ({ page }) => {
    await stubMe(page, {
      D1: storyPermission(true, true),
      D2: storyPermission(true, true),
      D3: storyPermission(true, true),
    });
    let scanned = false;
    await stubCollab(page, { id: 42, title: 'Fixture diagram' });
    await page.route('**/api/iac/session*', async (route) => {
      const id = Number(new URL(route.request().url()).searchParams.get('diagram_id') || 0);
      await fulfillJson(route, {
        diagram_id: id,
        draft: draft(PREVIEW, id),
        latest_scan: scanned ? scanReport('LOW') : null,
        latest_rewrite: null,
      });
    });
    await page.route('**/api/iac/secrets/rewrite', async (route) => {
      await fulfillJson(route, {
        plaintext: FIXTURE_PLAINTEXT,
        rewrite: {
          rewrite_id: 'rewrite-fixture',
          draft_id: 'draft-fixture',
          report_id: 'report-fixture',
          status: 'succeeded',
          rewritten_paths: ['main.tf'],
          created_at: '2026-01-01T00:00:00Z',
        },
        draft: draft('secret_ref = "sm://fixture/reference"'),
      });
    });
    await login(page, ADMIN.username, ADMIN.password);
    await page.getByTestId('nav-iac-secrets').click();
    await expect(page).toHaveURL(/\/iac\/secrets$/);
    await page.getByTestId('iac-diagram-select').selectOption('42');
    await expect(page.getByTestId('iac-run-d3')).toBeDisabled();
    await expect(page.getByText('需要已完成的掃描報告，才能改寫。')).toBeVisible();
    scanned = true;
    await page.reload();
    await expect(page.getByTestId('iac-run-d3')).toBeEnabled();
    await page.getByTestId('iac-run-d3').click();
    const list = page.getByTestId('iac-rewrite-list');
    await expect(list).toContainText('main.tf');
    await expect(list).not.toContainText(FIXTURE_PLAINTEXT);
    await expect(page.getByTestId('iac-workspace')).not.toContainText(FIXTURE_PLAINTEXT);
  });

  /**
   * @purpose 掃描含 HIGH 時，下載要先確認；Esc 不下載，確認後才發出 GET。
   * @given scan stub 的 severity 為 HIGH；download 由 route 計數
   * @api GET /api/iac/download -> 200 | 確認後才取得 zip blob
   * @ui /iac/scan | iac-download 與 iac-download-confirm
   * @step 在掃描頁掃出 HIGH 後按 `iac-download` | 出現 role 為 dialog 的 `iac-download-confirm`，且 download 請求數為 0
   * @step 按 Esc | dialog 關閉，download 請求數仍為 0，焦點回到 `iac-download`
   * @step 再次開啟並按「確認下載」 | GET /api/iac/download 請求數為 1
   * @pass 工作區內沒有名稱含 apply 或 destroy 的按鈕
   * @story US5.1
   */
  test('HIGH 下載需確認且沒有 apply 或 destroy', async ({ page }) => {
    let downloads = 0;
    await stubMe(page, {
      D1: storyPermission(true, true),
      D2: storyPermission(true, true),
    });
    await stubCollab(page, { id: 42, title: 'Fixture diagram' });
    await page.route('**/api/iac/session*', async (route) => {
      const id = Number(new URL(route.request().url()).searchParams.get('diagram_id') || 0);
      await fulfillJson(route, {
        diagram_id: id,
        draft: draft(PREVIEW, id),
        latest_scan: null,
        latest_rewrite: null,
      });
    });
    await page.route('**/api/iac/scan', async (route) => {
      await fulfillJson(route, { report: scanReport('HIGH') });
    });
    await page.route('**/api/iac/download*', async (route) => {
      downloads += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/zip',
        body: 'PK-fixture',
      });
    });
    await login(page, ADMIN.username, ADMIN.password);
    await page.getByTestId('nav-iac-scan').click();
    await page.getByTestId('iac-diagram-select').selectOption('42');
    await page.getByTestId('iac-run-d2').click();
    await expect(page.getByTestId('iac-findings')).toContainText('HIGH');
    await page.getByTestId('iac-download').click();
    const dialog = page.getByTestId('iac-download-confirm');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('role', 'dialog');
    expect(downloads).toBe(0);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    expect(downloads).toBe(0);
    await expect(page.getByTestId('iac-download')).toBeFocused();
    await page.getByTestId('iac-download').click();
    await page.getByRole('button', { name: '確認下載' }).click();
    await expect.poll(() => downloads).toBe(1);
    await expect(
      page.getByTestId('iac-workspace').getByRole('button', { name: /apply|destroy/i }),
    ).toHaveCount(0);
  });

  /**
   * @purpose 側邊選單把 D 做成與架構、成本相同的可收合大類，底下三個故事各自進入對應步驟。
   * @given seed 帳號 admin / admin123；D1、D2、D3 皆有 view
   * @api POST /api/auth/login -> 200 | 帳密驗證
   * @api GET /api/auth/me -> 200 | 權限含 D1、D2、D3 view
   * @ui /workspace | 側邊選單 nav-iac 與三個子項
   * @ui /iac/:step | 掃描頁與改寫頁的主要按鈕
   * @step 登入後檢視側邊選單 | 出現「基礎建設」，以及「Terraform 產出」「IaC 安全掃描」「Secret／敏感值」三個連結
   * @step 點「IaC 安全掃描」 | 網址為 `/iac/scan`，出現 `iac-run-d2`，且沒有頁內步驟鈕
   * @step 點「Secret／敏感值」 | 網址為 `/iac/secrets`，出現 `iac-run-d3`
   * @pass 三個子項都在「基礎建設」底下，點了會進到該頁，網址含 `/iac/`
   * @story US1.1
   */
  test('側邊選單以基礎建設分層顯示三個 IaC 功能', async ({ page }) => {
    await stubMe(page, {
      D1: storyPermission(true, true),
      D2: storyPermission(true, true),
      D3: storyPermission(true, true),
    });
    await stubCollab(page, null);
    await login(page, ADMIN.username, ADMIN.password);
    const group = page.getByTestId('nav-iac');
    await expect(group).toBeVisible();
    await expect(group).toContainText('基礎建設');
    await expect(page.getByTestId('nav-iac-generate')).toHaveText('Terraform 產出');
    await expect(page.getByTestId('nav-iac-scan')).toHaveText('IaC 安全掃描');
    await expect(page.getByTestId('nav-iac-secrets')).toHaveText('Secret／敏感值');
    await page.getByTestId('nav-iac-scan').click();
    await expect(page).toHaveURL(/\/iac\/scan$/);
    await expect(page.getByTestId('iac-run-d2')).toBeVisible();
    await expect(page.getByTestId('iac-step-scan')).toHaveCount(0);
    await page.getByTestId('nav-iac-secrets').click();
    await expect(page).toHaveURL(/\/iac\/secrets$/);
    await expect(page.getByTestId('iac-run-d3')).toBeVisible();
  });
});
