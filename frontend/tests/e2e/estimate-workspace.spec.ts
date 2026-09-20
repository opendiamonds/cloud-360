import { test, expect, Page } from '@playwright/test';
import path from 'path';

/**
 * U8 estimate-workspace-ui — C1 估價工作區上傳與明細呈現。
 * 對 ephemeral stack（APP_ENV=test）的 seed admin 執行；需後端已掛 /api/cost/v1。
 */

const ADMIN = { username: 'admin', password: 'admin123' };
const FIXTURE = path.join(process.cwd(), 'tests/fixtures/aws-estimate.csv');

async function login(page: Page, username: string, password: string) {
  await page.goto('/');
  await page.getByPlaceholder('請輸入您的帳號').fill(username);
  await page.getByPlaceholder('請輸入密碼').fill(password);
  await page.getByRole('button', { name: '登入系統' }).click();
}

test.describe('估價工作區（U8）', () => {
  /**
   * @purpose 具 C1 權限的使用者可進入 /cost、上傳 AWS CSV，並看到雲別明細卡與機械檢查面板。
   * @api POST /api/cost/v1/sets -> 201 | 上傳估價表並回傳明細
   * @api GET /api/cost/v1/sets/{set_id} -> 200 | 讀取估價表明細
   * @ui /cost | 估價工作區：上傳區、雲別明細卡、機械檢查、隱私徽章
   * @given seed 帳號 admin / admin123，角色 Platform_Admin（具 C1 view/edit）
   * @step 以 admin 登入並前往 /cost | 顯示 data-testid=cost-page 與上傳區
   * @step 選擇 fixtures/aws-estimate.csv 並按「開始上傳」 | 後端接受並回傳明細
   * @step 檢視明細區 | 出現 estimate-cloud-card 與 estimate-checks-panel
   * @pass 雲別卡與檢查面板皆可見，且頁面仍在 /cost
   * @story C1
   */
  test('上傳 AWS CSV 後顯示明細與檢查', async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page).toHaveURL(/\/(workspace|cost)/);
    await page.goto('/cost');
    await expect(page.getByTestId('cost-page')).toBeVisible();
    await expect(page.getByTestId('estimate-upload-zone')).toBeVisible();

    await page.locator('input[type="file"]').setInputFiles(FIXTURE);
    await expect(page.getByText('aws-estimate.csv')).toBeVisible();
    await page.getByTestId('estimate-upload-submit').click();

    await expect(page.getByTestId('estimate-cloud-card')).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByTestId('estimate-checks-panel')).toBeVisible();
    await expect(page.getByTestId('advice-slot')).toBeVisible();
    // U9：建議區進入產生中、完成或失敗其一即可辨識（LLM 環境不一定產出完成）
    await expect(
      page
        .getByTestId('advice-pending')
        .or(page.getByTestId('advice-category-saving'))
        .or(page.getByTestId('advice-failed'))
    ).toBeVisible({ timeout: 20_000 });
    await expect(page).toHaveURL(/\/cost/);
  });
});
