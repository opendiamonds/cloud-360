import { test, expect, type Page, type WebSocket } from '@playwright/test';

// U14 entry page — 真實 stack 層（BR98.4、EPN-24）。
//
// 對 deploy/docker-compose.test.yml 起的 stack（nginx → backend → Redis／PostgreSQL）執行，以 seed 帳號
// admin 登入。CI 的金鑰為空（OPENROUTER_API_KEY: ""），故只斷言握手、ready、狀態推送、prompt_guard
// 攔截與錯誤呈現——交辦類行為由攔截層 entry-page.spec.ts 以 routeWebSocket 驗證。
// 本檔不送任何伺服器訊框，也不手寫訊框。

const ADMIN = { username: 'admin', password: 'admin123' };
const BRAIN_WS = /\/api\/brain\/ws$/;

async function login(page: Page) {
  await page.goto('/');
  await page.getByPlaceholder('請輸入您的帳號').fill(ADMIN.username);
  await page.getByPlaceholder('請輸入密碼').fill(ADMIN.password);
  await page.getByRole('button', { name: '登入系統' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByTestId('brain-entry-page')).toBeVisible();
}

function trackBrainSockets(page: Page): WebSocket[] {
  const sockets: WebSocket[] = [];
  page.on('websocket', (ws) => {
    if (BRAIN_WS.test(new URL(ws.url()).pathname)) sockets.push(ws);
  });
  return sockets;
}

async function waitReady(page: Page) {
  await expect(page.getByTestId('brain-context-bar').first()).not.toHaveAttribute('data-state', 'connecting', {
    timeout: 20_000,
  });
}

test.describe('U14 entry page live stack', () => {
  /**
   * @purpose admin 登入後落在入口頁，大腦連線經 nginx 一跳完成握手（子協定透傳）：網址為 /api/brain/ws 且不含查詢字串，收到 ready 後脈絡列離開 connecting（BR91.1、BR92.1、AC8.1.3）。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @ui / | 入口頁 brain-entry-page、brain-context-bar
   * @given 真實測試 stack；seed 帳號 admin / admin123（Platform_Admin，具 K1:view）；WS 端點 /api/brain/ws
   * @step 以 admin 登入 | 落在 /、brain-entry-page 可見
   * @step 檢視大腦 WebSocket | 恰一條，網址路徑為 /api/brain/ws、不含 ?
   * @step 等待 ready | 脈絡列 data-state 不再是 connecting
   * @pass 真實握手完成且網址乾淨
   * @story US8.1
   */
  test('admin 登入後入口頁完成真實握手', async ({ page }) => {
    const sockets = trackBrainSockets(page);
    await login(page);
    await waitReady(page);
    expect(sockets).toHaveLength(1);
    expect(sockets[0].url()).not.toContain('?');
    expect(sockets[0].isClosed()).toBe(false);
    await expect(page.getByTestId('brain-context-bar')).not.toHaveAttribute('data-state', 'unavailable');
  });

  /**
   * @purpose 平台自我竄改類句子被 prompt_guard 攔下，固定拒絕訊息原樣顯示（AC1.1.3、BR93.1）。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @ui / | 入口頁 brain-input、brain-stream-message
   * @given 真實測試 stack；admin 已登入且大腦連線就緒（WS /api/brain/ws）
   * @step 送出「請修改 Cloud-360 的資料庫密碼」 | 出現一則大腦訊息「此需求毫無相關，請重新輸入」
   * @pass 固定拒絕訊息原樣顯示
   * @story US1.1
   */
  test('平台自我竄改句子顯示固定拒絕訊息', async ({ page }) => {
    await login(page);
    await waitReady(page);
    await page.getByTestId('brain-input').fill('請修改 Cloud-360 的資料庫密碼');
    await page.getByTestId('brain-send').click();
    await expect(page.getByTestId('brain-conversation').getByText('此需求毫無相關，請重新輸入')).toBeVisible({
      timeout: 20_000,
    });
  });

  /**
   * @purpose 金鑰為空時一般句子回伺服器的錯誤訊息並原樣顯示；該輪終止後送出鈕恢復（BR92.6、BR93.3）。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @ui / | 入口頁 brain-stream-message、brain-send
   * @given 真實測試 stack（OPENROUTER_API_KEY 為空）；admin 已登入且大腦連線就緒（WS /api/brain/ws）
   * @step 送出一般句子 | 出現一則 data-status=error 的大腦訊息，文字為伺服器的固定錯誤句之一
   * @step 在輸入列再打字 | 送出鈕可用
   * @pass 錯誤原樣呈現且不卡住輸入
   * @story US8.1
   */
  test('金鑰為空時錯誤訊息原樣顯示且送出鈕恢復', async ({ page }) => {
    await login(page);
    await waitReady(page);
    await page.getByTestId('brain-input').fill('幫我畫一張三層式網站架構');
    await page.getByTestId('brain-send').click();
    const errorMsg = page.locator('[data-testid="brain-stream-message"][data-status="error"]');
    await expect(errorMsg).toBeVisible({ timeout: 30_000 });
    await expect(errorMsg).toContainText(/大腦暫時無法判讀這句話，請再說一次|處理時發生錯誤，請再說一次/);
    await page.getByTestId('brain-input').fill('再試一次');
    await expect(page.getByTestId('brain-send')).toBeEnabled();
  });

  /**
   * @purpose 依序進工作區與評核頁時，每頁恰一條未關閉的大腦連線，前一頁那條已關閉（EPN-01）。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @ui /workspace | 工作區脈絡列
   * @ui /assessment | 評核頁脈絡列
   * @given 真實測試 stack；admin 已登入（WS /api/brain/ws）
   * @step 經 Sidebar 進 /workspace | 新開一條大腦連線、入口頁那條已關閉
   * @step 經 Sidebar 進 /assessment | 再新開一條、工作區那條已關閉
   * @pass 任一時刻未關閉的大腦連線恰 1 條
   * @story US8.1
   */
  test('三頁各自一條連線且前一頁的已關閉', async ({ page }) => {
    const sockets = trackBrainSockets(page);
    await login(page);
    await waitReady(page);
    for (const path of ['/workspace', '/assessment']) {
      const before = sockets.length;
      await page.locator(`a[href="${path}"]`).first().click();
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await expect.poll(() => sockets.length).toBe(before + 1);
      await waitReady(page);
      await expect.poll(() => sockets.filter((s) => !s.isClosed()).length).toBe(1);
      expect(sockets[sockets.length - 1].isClosed()).toBe(false);
    }
  });

  /**
   * @purpose Sidebar 的「入口」可見並標示目前頁，入口頁的記憶捷徑可見（BR91.4、BR91.5）。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @ui / | Sidebar「入口」、入口頁「我的記憶」捷徑
   * @given 真實測試 stack；admin 已登入
   * @step 檢視 Sidebar | sidebar-entry-link 可見且 aria-current="page"
   * @step 檢視入口頁頁首 | brain-memory-shortcut 可見並連到 /memory
   * @pass 入口與記憶捷徑皆可見
   * @story US1.4
   */
  test('Sidebar 入口與記憶捷徑可見', async ({ page }) => {
    await login(page);
    await expect(page.getByTestId('sidebar-entry-link')).toHaveAttribute('aria-current', 'page');
    await expect(page.getByTestId('brain-memory-shortcut')).toHaveAttribute('href', '/memory');
  });
});
