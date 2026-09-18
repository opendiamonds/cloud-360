import { test, expect, Page } from '@playwright/test';

// Core UI regression — the flows that must never silently break. Deliberately
// LLM-free: none of these touch A1 architecture generation (that path calls
// OpenRouter, costs money, and is externally flaky). They exercise auth, RBAC
// visibility, and navigation against the ephemeral stack's seeded data.
//
// Seeded by the ephemeral backend running with APP_ENV=test: one user,
// admin / admin123, role Platform_Admin. New registrations start pending.

const ADMIN = { username: 'admin', password: 'admin123' };

async function login(page: Page, username: string, password: string) {
  await page.goto('/');
  await page.getByPlaceholder('請輸入您的帳號').fill(username);
  await page.getByPlaceholder('請輸入密碼').fill(password);
  await page.getByRole('button', { name: '登入系統' }).click();
}

test.describe('身分驗證', () => {
  /**
   * @purpose 未登入者開啟站台時看得到可用的登入介面。這是其他所有流程的入口，
   * @ui / | 登入頁：帳號／密碼輸入框、「登入系統」按鈕
   *          它壞掉等於整站不可用。
   * @given 瀏覽器未持有有效 token
   * @step 開啟站台根路徑 `/` | 顯示登入頁
   * @step 檢視頁面標題 | 出現 heading「Cloud-360」
   * @step 檢視主要動作 | 出現「登入系統」按鈕
   * @pass 標題與按鈕皆可見
   * @story J1
   */
  test('登入頁正常顯示', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Cloud-360' })).toBeVisible();
    await expect(page.getByRole('button', { name: '登入系統' })).toBeVisible();
  });

  /**
   * @purpose 錯誤憑證必須被拒絕，且使用者留在登入頁看得到原因。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @ui / | 登入頁：帳號／密碼輸入框、「登入系統」按鈕
   * @given seed 帳號 admin 存在
   * @step 以 admin 與一組錯誤密碼送出登入 | 後端回 401「帳號或密碼錯誤」
   * @step 檢視頁面 | 出現「帳號或密碼錯誤」
   * @step 檢視當前路徑 | 未被導向 `/workspace`
   * @pass 錯誤訊息可見，且 URL 不含 `/workspace`
   * @story J1
   * @note 「不得導向 workspace」是關鍵斷言：只驗錯誤訊息無法排除「顯示了錯誤
   *       但仍然放行」這種更嚴重的實作。
   */
  test('錯誤密碼被拒並停留在登入頁', async ({ page }) => {
    await login(page, ADMIN.username, 'definitely-wrong-password');
    // Backend returns 401 "帳號或密碼錯誤"; the page shows it and does not navigate.
    await expect(page.getByText('帳號或密碼錯誤')).toBeVisible();
    await expect(page).not.toHaveURL(/\/workspace/);
  });

  /**
   * @purpose 正確憑證能登入，且落在具備該角色功能的工作區。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @api GET /api/auth/me -> 200 | 取得目前登入者與其權限
   * @ui / | 登入頁：帳號／密碼輸入框、「登入系統」按鈕
   * @ui /workspace | 工作區：側邊導覽、「架構」按鈕、「登出系統」控制項
   * @given test seed 帳號 admin / admin123，角色 Platform_Admin
   * @step 以 admin / admin123 送出登入 | 登入成功
   * @step 檢視當前路徑 | 導向 `/workspace`
   * @step 檢視工作區介面 | 出現「架構」按鈕
   * @pass URL 為 `/workspace` 且「架構」按鈕可見
   * @story J1
   */
  test('管理員登入後進入工作區', async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page).toHaveURL(/\/workspace/);
    await expect(page.getByRole('button', { name: '架構', exact: true })).toBeVisible();
  });

  /**
   * @purpose 登出確實結束 session 並回到登入頁，不是只換了畫面。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @ui / | 登入頁：帳號／密碼輸入框、「登入系統」按鈕
   * @ui /workspace | 工作區：側邊導覽、「架構」按鈕、「登出系統」控制項
   * @given 已以 admin 登入並停留在 `/workspace`
   * @step 點擊標題為「登出系統」的控制項 | 觸發登出
   * @step 檢視頁面 | 回到登入頁，出現「登入系統」按鈕
   * @pass 「登入系統」按鈕可見
   * @story J1
   */
  test('登出後返回登入頁', async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page).toHaveURL(/\/workspace/);
    await page.getByTitle('登出系統').click();
    await expect(page.getByRole('button', { name: '登入系統' })).toBeVisible();
  });
});

test.describe('角色權限存取控制 (RBAC)', () => {
  /**
   * @purpose 具備管理權限的角色看得到系統管理入口。這是 RBAC 的 allow 方向。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @api GET /api/auth/me -> 200 | 取得目前登入者與其權限
   * @ui /workspace | 工作區：側邊導覽、「架構」按鈕、「登出系統」控制項
   * @given seed 帳號 admin，角色 Platform_Admin（具 J3a:view）
   * @step 以 admin 登入 | 進入 `/workspace`
   * @step 檢視側邊導覽 | 出現「系統管理」區塊
   * @step 檢視該區塊項目 | 出現「使用者角色」連結
   * @pass 兩者皆可見
   * @story J3a
   * @note 與「Developer 看不到系統管理區」成對，構成同一權限的雙向驗證。
   *       只驗 allow 方向無法證明權限有真的在把關。
   */
  test('Platform_Admin 看得到系統管理區', async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page).toHaveURL(/\/workspace/);
    await expect(page.getByText('系統管理')).toBeVisible();
    await expect(page.getByRole('link', { name: '使用者角色' })).toBeVisible();
  });

  /**
   * @purpose RBAC 的 deny 方向：不具管理權限的角色看不到系統管理入口。
   * @api POST /api/auth/register -> 200 | 公開註冊，新帳號為 pending
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @api GET /api/auth/authorization-requests -> 200 | 待審申請清單
   * @api POST /api/auth/authorization-requests/{request_id}/approve -> 200 | 核准註冊申請
   * @api GET /api/auth/me -> 200 | 取得目前登入者與其權限
   * @ui / | 登入頁：帳號／密碼輸入框、「登入系統」按鈕
   * @ui /workspace | 工作區：側邊導覽、「架構」按鈕、「登出系統」控制項
   * @ui /admin/authorization-requests | 授權申請審核頁：申請列表與「核准」按鈕
   * @given test seed 只有 admin；新註冊帳號申請 Developer，且需管理員核准
   * @step 以公開註冊建立一個唯一帳號（密碼 devpass123） | 註冊成功
   * @step 檢視當前路徑 | 導向 `/waiting-approval` 等待審核頁
   * @step 登出，改以 admin / admin123 登入 | 進入 `/workspace`
   * @step 前往 `/admin/authorization-requests` | 顯示待審清單
   * @step 在該帳號所在列點擊「核准」並接受確認對話框 | 出現「已核准」提示
   * @step 登出管理員，改以剛核准的 Developer 帳號登入 | 進入 `/workspace`
   * @step 檢視側邊導覽 | 「系統管理」出現次數為 0
   * @pass Developer 登入後畫面上不存在「系統管理」
   * @story J3a
   * @note 這個案例刻意走完整的註冊→核准→登入流程，而不是直接改資料庫角色：
   *       授權流程本身也在被驗證的範圍內。
   */
  test('Developer 看不到系統管理區', async ({ page }) => {
    // 1. 註冊新帳號 dev_xxx
    const rid = (process.env.PW_RUN_ID || '0').replace(/\D/g, '').slice(-4);
    const uniq = `dev_${rid}${Date.now().toString(36)}`.slice(0, 20);
    await page.goto('/');
    await page.getByRole('button', { name: /立即註冊新帳號/ }).click();
    await page.getByPlaceholder('請輸入您的帳號').fill(uniq);
    await page.getByPlaceholder('請輸入密碼').fill('devpass123');
    await page.getByPlaceholder('請再次輸入密碼').fill('devpass123');
    await page.getByRole('button', { name: '送出註冊申請' }).click();

    // 2. 註冊後會跳至 /waiting-approval 等待審核頁
    await expect(page).toHaveURL(/\/waiting-approval/);

    // 3. 登出並以系統管理員身分登入以審核該申請
    await page.getByRole('button', { name: '登出' }).click();
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page).toHaveURL(/\/workspace/);

    // 4. 前往審核頁面進行核准
    await page.goto('/admin/authorization-requests');
    // 監聽並自動接受 confirm 彈窗
    page.once('dialog', dialog => dialog.accept());
    // 定位含有該使用者帳號的表格列，點擊其核准按鈕
    const row = page.locator('tr').filter({ hasText: uniq });
    await row.getByRole('button', { name: '核准' }).click();
    // 等待 Toast 成功訊息出現
    await expect(page.getByText(/已核准/)).toBeVisible();

    // 5. 登出管理員，改用已核准的 Developer 登入
    await page.getByTitle('登出系統').click();
    await login(page, uniq, 'devpass123');
    await expect(page).toHaveURL(/\/workspace/);

    // 6. 驗證 Developer 權限：看不到系統管理區
    await expect(page.getByText('系統管理')).toHaveCount(0);
  });
});

// 使用者管理頁的回歸 —— 本專案**第一批**進入該頁的 e2e case（team-practices
// 測試底線 C）。這條路徑上原本沒有任何自動化斷言：`tsc -b` 對後端回應形狀無感、
// 既有六個 case 無一導覽至此，所以「後端漏欄位 → 前端渲染成空白」不會被發現。
//
// seed 只有 admin 一個帳號，湊不出第二頁；需要多頁的 case 以公開註冊端點自行
// 建立帳號（既有的「Developer 看不到系統管理區」已示範同一手法）。
test.describe('使用者管理頁 — 最後活動時間與分頁', () => {
  async function gotoAdmin(page: Page) {
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page).toHaveURL(/\/workspace/);
    await page.getByRole('link', { name: '使用者角色' }).click();
    await expect(page.getByRole('heading', { name: '使用者角色指派' })).toBeVisible();
  }

  /** 以公開註冊端點建立一個帳號（不經 UI，比逐次填表快得多）。 */
  async function registerUser(page: Page, username: string) {
    const res = await page.request.post('/api/auth/register', {
      data: { username, password: 'pagepass123', requested_role: 'Developer' },
    });
    if (!res.ok()) throw new Error(`註冊 ${username} 失敗：${res.status()} ${await res.text()}`);
  }

  /**
   * @purpose 使用者管理表格顯示「最後活動時間」欄，且欄內是真正的時間值。
   * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 以 admin 登入（登入本身會寫入一次最後活動時間）
   * @step 進入使用者角色指派頁 | 顯示「使用者角色指派」標題
   * @step 檢視表頭 | 出現「最後活動時間」欄
   * @step 檢視 admin 所在列 | 該欄顯示 `YYYY-MM-DD HH:MM` 格式的時間值
   * @pass 表頭存在，且 admin 列的值符合時間格式
   * @story J3a
   * @note 斷言的是**具體時間值**，不是「有值或破折號都算過」——後者對任何實作
   *       恆真，包括後端漏傳欄位、前端渲染成空白的情形。這條路徑先前沒有任何
   *       自動化斷言：`tsc -b` 對後端回應形狀無感（前端型別是手寫的本地
   *       interface，`res.json()` 的 any 直接放行）。
   */
  test('表格出現最後活動時間欄，且該欄有值或無紀錄破折號', async ({ page }) => {
    await gotoAdmin(page);
    await expect(
      page.getByRole('columnheader', { name: '最後活動時間' })
    ).toBeVisible();

    // admin 剛登入過，其最後活動時間必定已被記錄 —— 斷言的是**具體的時間值**，
    // 不是「有值或破折號都算過」（後者對任何實作都恆真）。
    const adminRow = page.getByRole('row').filter({ hasText: ADMIN.username }).first();
    await expect(adminRow.getByText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)).toBeVisible();
  });

  /**
   * @purpose 分頁控制存在，並揭露總筆數與目前頁次。
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 以 admin 登入並進入使用者角色指派頁
   * @step 檢視清單下方 | 出現名為「使用者清單分頁」的導覽區
   * @step 檢視該區文字 | 顯示「N 筆」總數
   * @step 檢視目前頁次標示 | `aria-current="page"` 的元素文字為 `[1]`
   * @pass 三者皆成立
   * @story J3a
   * @note 方括號是刻意的**非色彩線索**：目前頁次不能只靠顏色區分，否則色覺
   *       障礙使用者無從判斷自己在第幾頁。
   */
  test('分頁控制可見且顯示總筆數與目前頁次', async ({ page }) => {
    await gotoAdmin(page);
    const pager = page.getByRole('navigation', { name: '使用者清單分頁' });
    await expect(pager).toBeVisible();
    await expect(pager.getByText(/\d+ 筆/)).toBeVisible();
    // 目前頁次以 aria-current 標示，且**不只靠顏色** —— 方括號是非色彩線索。
    await expect(pager.locator('[aria-current="page"]')).toHaveText('[1]');
  });

  /**
   * @purpose 換頁真的換到不同資料，且在非第 1 頁做處置後不會被彈回第 1 頁。
   * @api POST /api/auth/register -> 200 | 公開註冊，新帳號為 pending
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @api PUT /api/auth/{user_id}/active -> 200 | 啟用／停用帳號
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 每頁 20 筆；seed 只有 admin，故先以公開註冊端點建立 21 個帳號
   * @step 進入使用者角色指派頁並記錄第 1 頁的列內容 | 取得基準
   * @step 點擊分頁的「2」 | 目前頁次標示變為 `[2]`
   * @step 比對第 2 頁與第 1 頁的列內容 | 兩者不相同
   * @step 對第 2 頁的第一個帳號點「停用」 | 出現「✔ 已停用 <帳號>」提示
   * @step 檢視目前頁次標示 | 仍為 `[2]`
   * @pass 兩頁內容不同，且處置後頁次不變
   * @story J3a
   * @note AC-5.6。若實作在處置後沿用「整份重抓」，使用者會被拉回第 1 頁，
   *       這條斷言就是為了抓它——字面通過但打斷工作流的實作。
   */
  test('切換到第 2 頁取得不重複的帳號，且處置後仍停在第 2 頁', async ({ page }) => {
    // 每頁 20 筆，故需要 21 個以上的帳號才會有第 2 頁（seed 已有 admin）。
    const rid = (process.env.PW_RUN_ID || '0').replace(/\D/g, '').slice(-3);
    const stamp = Date.now().toString(36);
    await page.goto('/');
    for (let i = 0; i < 21; i += 1) {
      await registerUser(page, `pg${rid}${stamp}${i.toString(36)}`.slice(0, 20));
    }

    await gotoAdmin(page);
    const pager = page.getByRole('navigation', { name: '使用者清單分頁' });

    const firstPageNames = await page.getByRole('row').allInnerTexts();
    await pager.getByRole('button', { name: '2', exact: true }).click();
    await expect(pager.locator('[aria-current="page"]')).toHaveText('[2]');

    const secondPageNames = await page.getByRole('row').allInnerTexts();
    expect(secondPageNames).not.toEqual(firstPageNames);

    // AC-5.6：在第 2 頁停用一個帳號後，畫面**仍在第 2 頁**。現行實作若沿用整份
    // 重抓（`fetchUsers()`），這條會紅 —— 那正是本斷言存在的理由。
    const firstToggle = page.getByRole('button', { name: '停用' }).first();
    await firstToggle.click();
    // 只斷言 toast（「✔ 已停用 <帳號>」），不要用會同時命中表格內狀態文字的
    // 寬鬆比對 —— 後者在 strict mode 下會撞到三個元素。
    await expect(page.getByText(/^✔ 已停用 /)).toBeVisible();
    await expect(pager.locator('[aria-current="page"]')).toHaveText('[2]');
  });

  /**
   * @purpose 調整角色後，該列的最後活動時間不得消失。
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @api PUT /api/auth/{user_id}/role -> 200 | 調整使用者角色
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 以 admin 登入並進入使用者角色指派頁
   * @step 將 admin 的角色切換為 Project_Admin | 出現「✔ 已更新 <帳號>」提示
   * @step 檢視該列的最後活動時間欄 | 仍顯示 `YYYY-MM-DD HH:MM` 格式的值
   * @step 將角色切回 Platform_Admin | 出現「✔ 已更新 <帳號>」提示
   * @pass 角色兩次都更新成功，且中間該列的時間值未變空白
   * @story J3a
   * @note NFR-7 回歸。既有的 `requested_role` 正是在這個端點漏傳的，新欄位若
   *       比照現行寫法會複製同一缺陷。只能在**保有 J3a:edit 的角色之間**切換：
   *       後端拒絕把最後一位可編輯使用者角色的管理員降權，而測試環境只有
   *       admin 一個已核准帳號。
   */
  test('角色調整仍可用且不影響最後活動時間欄（NFR-7 回歸）', async ({ page }) => {
    // reviewer Iteration 2 的新發現 N4：文件宣稱桌面 e2e 已涵蓋 NFR-7 的三項既有
    // 操作，實際只有「啟停用」。這裡補上「角色調整」——它是本 intent 動到的三個
    // 回應構造點之一，且既有的 requested_role 漏傳正是發生在這條路徑上。
    await gotoAdmin(page);
    const row = page.getByRole('row').filter({ hasText: ADMIN.username }).first();
    // 只能在**保有 J3a:edit 的角色之間**切換：後端拒絕把最後一位可編輯使用者
    // 角色的管理員降權（`user_router.py` 的 admin_edit_count 檢查），而 seed 的
    // 測試環境只有 admin 一個已核准帳號。Project_Admin 與 Platform_Admin 是預設
    // 矩陣中僅有的兩個 J3a:edit 角色，故在這兩者之間來回。
    await row.getByRole('combobox').selectOption('Project_Admin');
    await expect(page.getByText(/^✔ 已更新 /)).toBeVisible();
    // 關鍵斷言：角色調整後該列的最後活動時間**不得變成空白**。既有的
    // requested_role 就是在這個端點漏傳的，新欄位比照現行寫法會複製同一缺陷。
    await expect(row.getByText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)).toBeVisible();
    await row.getByRole('combobox').selectOption('Platform_Admin');
    await expect(page.getByText(/^✔ 已更新 /)).toBeVisible();
  });

  /**
   * @purpose 分頁控制可用鍵盤操作，且在資料載入期間不會從畫面上消失。
   * @api POST /api/auth/register -> 200 | 公開註冊，新帳號為 pending
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 先以公開註冊端點建立 21 個帳號，使清單有第 2 頁
   * @step 進入使用者角色指派頁，將焦點移到頁碼「2」 | 該按鈕取得焦點
   * @step 攔截清單 API 並延遲 1200ms 回應 | 模擬慢速載入
   * @step 對頁碼「2」按下 Enter | 觸發換頁
   * @step 在回應抵達前檢視分頁區 | 仍在畫面上，且 `aria-busy="true"`
   * @step 等待回應完成 | 目前頁次標示變為 `[2]`
   * @pass 鍵盤可聚焦並觸發；載入期間控制項不消失且標示忙碌狀態
   * @story J3a
   * @note AC-5.9／AC-5.10。刻意延遲回應是這條案例的核心：若分頁控制被放在
   *       會被整塊替換的容器內，它會在載入期間閃現消失——不延遲就看不到。
   */
  test('切頁期間分頁控制不消失，且鍵盤可達可觸發（AC-5.9／AC-5.10）', async ({ page }) => {
    const rid = (process.env.PW_RUN_ID || '0').replace(/\D/g, '').slice(-3);
    const stamp = Date.now().toString(36);
    await page.goto('/');
    for (let i = 0; i < 21; i += 1) {
      await registerUser(page, `kb${rid}${stamp}${i.toString(36)}`.slice(0, 20));
    }
    await gotoAdmin(page);
    const pager = page.getByRole('navigation', { name: '使用者清單分頁' });

    // AC-5.9：頁碼按鈕可用鍵盤到達並**觸發**（不只是可聚焦）。
    const pageTwo = pager.getByRole('button', { name: '2', exact: true });
    await pageTwo.focus();
    await expect(pageTwo).toBeFocused();

    // AC-5.10：切頁期間控制項**仍在畫面上**。刻意延遲清單回應，在回應抵達前
    // 斷言 nav 仍然存在 —— 若控制項被放在會被整塊替換的容器內，這裡會失敗。
    await page.route('**/api/auth/list**', async (route) => {
      await new Promise((r) => setTimeout(r, 1200));
      await route.continue();
    });
    await pageTwo.press('Enter');
    await expect(pager).toBeVisible();
    await expect(pager).toHaveAttribute('aria-busy', 'true');
    await page.unroute('**/api/auth/list**');
    await expect(pager.locator('[aria-current="page"]')).toHaveText('[2]');
  });

  /**
   * @purpose 在非第 1 頁刪除帳號後，頁次不變且總筆數同步遞減。
   * @api POST /api/auth/register -> 200 | 公開註冊，新帳號為 pending
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @api PUT /api/auth/{user_id}/active -> 200 | 啟用／停用帳號
   * @api DELETE /api/auth/{user_id} -> 200 | 刪除已停用的帳號
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 先以公開註冊端點建立 21 個帳號，使清單有第 2 頁
   * @step 進入使用者角色指派頁並切換到第 2 頁 | 目前頁次標示為 `[2]`
   * @step 記錄分頁區顯示的總筆數 | 取得基準值 N
   * @step 對第一個帳號點「停用」 | 出現「✔ 已停用 <帳號>」提示，刪除鈕出現
   * @step 點「刪除」並接受確認對話框 | 出現「✔ 已刪除 <帳號>」提示
   * @step 檢視目前頁次標示 | 仍為 `[2]`
   * @step 檢視總筆數 | 顯示 N-1 筆
   * @pass 頁次不變且總筆數正確遞減
   * @story J3a
   * @note AC-5.6 的刪除子句。刪除鈕只在帳號停用後才出現，故步驟必須先停用。
   *       停用沒有確認對話框、只有刪除有——為停用也掛 handler 會殘留到刪除時
   *       重複處理。
   */
  test('刪除後仍停在原頁次，且清單重新同步（AC-5.6 的刪除子句）', async ({ page }) => {
    const rid = (process.env.PW_RUN_ID || '0').replace(/\D/g, '').slice(-3);
    const stamp = Date.now().toString(36);
    await page.goto('/');
    for (let i = 0; i < 21; i += 1) {
      await registerUser(page, `dl${rid}${stamp}${i.toString(36)}`.slice(0, 20));
    }
    await gotoAdmin(page);
    const pager = page.getByRole('navigation', { name: '使用者清單分頁' });
    await pager.getByRole('button', { name: '2', exact: true }).click();
    await expect(pager.locator('[aria-current="page"]')).toHaveText('[2]');

    const totalBefore = Number(
      ((await pager.getByText(/\d+ 筆/).innerText()).match(/(\d+)/) || ['0'])[0]
    );

    // 刪除鈕只在帳號已停用後出現，故先停用再刪除。停用沒有確認對話框，只有
    // 刪除有 —— 為停用也掛一個 once handler 會讓它殘留到刪除時重複處理。
    await page.getByRole('button', { name: '停用' }).first().click();
    await expect(page.getByText(/^✔ 已停用 /)).toBeVisible();
    page.once('dialog', (d) => d.accept());
    await page.getByRole('button', { name: '刪除' }).first().click();
    await expect(page.getByText(/^✔ 已刪除 /)).toBeVisible();

    // AC-5.6：頁次不變（現行的整份重抓會把使用者拉回第 1 頁 —— 這條就是要抓它）。
    await expect(pager.locator('[aria-current="page"]')).toHaveText('[2]');
    // 總筆數本地遞減，且背景重抓完成後仍然一致。
    await expect(pager.getByText(new RegExp(`${totalBefore - 1} 筆`))).toBeVisible();
  });

  /**
   * @purpose 頁次超出範圍時顯示明確空態，且使用者有路可回。
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 以 admin 登入；seed 只有 admin，故第 5 頁必為空
   * @step 進入使用者角色指派頁，攔截清單 API 將頁次改為 5 並重新載入 | 請求第 5 頁
   * @step 檢視清單區 | 顯示「這一頁沒有資料。」
   * @step 檢視分頁控制 | 仍在畫面上（它在清單容器之外）
   * @step 點擊「回到第 1 頁」 | 空態訊息消失
   * @pass 空態可見、分頁控制不消失、回到第 1 頁後恢復正常
   * @story J3a
   * @note AC-5.4 的 UI 子句。重點是空態下**分頁控制仍在**——否則使用者會卡在
   *       一個沒有資料也沒有出路的畫面。
   */
  test('超出範圍的頁次顯示空態並可回到第 1 頁（AC-5.4 的 UI 子句）', async ({ page }) => {
    await gotoAdmin(page);
    // 直接讓清單端點回一個超出範圍的頁 —— seed 只有 admin，第 5 頁必為空。
    await page.route('**/api/auth/list**', async (route) => {
      const url = new URL(route.request().url());
      url.searchParams.set('page', '5');
      await route.continue({ url: url.toString() });
    });
    await page.reload();
    await expect(page.getByText('這一頁沒有資料。')).toBeVisible();
    const pager = page.getByRole('navigation', { name: '使用者清單分頁' });
    // 空態下**分頁控制仍在畫面上**（因為它在容器之外），且提供回到第 1 頁。
    await expect(pager).toBeVisible();
    await page.unroute('**/api/auth/list**');
    await page.getByRole('button', { name: '回到第 1 頁' }).click();
    await expect(page.getByText('這一頁沒有資料。')).toHaveCount(0);
  });

  /**
   * @purpose 小螢幕改用卡片佈局，且分頁能力不因此縮水。
   * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
   * @ui /admin/users | 使用者角色指派頁：使用者表格、「最後活動時間」欄、名為「使用者清單分頁」的分頁導覽區
   * @given 視窗尺寸設為 390×844（手機直向）
   * @step 進入使用者角色指派頁 | 顯示「使用者角色指派」標題
   * @step 檢視表格 | 表格被隱藏
   * @step 檢視卡片內容 | 出現「最後活動」欄位
   * @step 檢視分頁控制 | 仍在畫面上
   * @step 檢視目前頁次標示 | 可見且文字為 `[1]`
   * @step 檢視總筆數 | 顯示「N 筆」
   * @pass 表格隱藏、卡片顯示最後活動、分頁控制與總筆數皆可用
   * @story J3a
   * @note AC-5.7：小螢幕也必須能**跳至特定頁次**，不是只能逐頁前後移動。
   *       單頁時目前頁碼是唯一的頁碼按鈕，且呈現但停用。
   */
  test('小螢幕改為卡片佈局，分頁控制仍可用', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoAdmin(page);
    // 斷點以下：表格隱藏、卡片出現。
    await expect(page.getByRole('table')).toBeHidden();
    await expect(page.getByText('最後活動', { exact: true }).first()).toBeVisible();
    const pager = page.getByRole('navigation', { name: '使用者清單分頁' });
    await expect(pager).toBeVisible();
    // AC-5.7：小螢幕也必須能**跳至特定頁次**（不只逐頁前後移動），且呈現總筆數。
    // 目前頁碼帶方括號（非色彩線索）；單頁時它是唯一的頁碼按鈕，且**呈現但停用**。
    const currentPage = pager.locator('[aria-current="page"]');
    await expect(currentPage).toBeVisible();
    await expect(currentPage).toHaveText('[1]');
    await expect(pager.getByText(/\d+ 筆/)).toBeVisible();
  });
});
