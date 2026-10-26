# Unit Test Instructions — `U24 member-pages-ui`

> **本單元沒有 unit test，只有 Playwright e2e**，這不是省略而是既成事實：
> `frontend/package.json` 的 `devDependencies` **只有** `@playwright/test`，
> 無 vitest、無 jest、無 `@testing-library/*`；`scripts` 只有 `test:e2e`。
> 引入前端 unit 框架是 `team.md` Q4 定案的 **D 項不採用**（屬獨立工具鏈決策，
> 不由本 feature 夾帶）。前端的唯一自動化驗證層就是 e2e。
>
> Test strategy 為 **standard**（每元件 5–8 個測試），方法論為 **`test-after`**。
> 本單元以**一支 spec 檔、8 個案例**滿足該量級——理由見 §四。

## 一、測試框架與設定

| 項目 | 內容 |
|---|---|
| 框架 | `@playwright/test`（既有，**不新增依賴**） |
| 設定檔 | `frontend/playwright.config.ts`；`:10` 的 `testDir: './tests/e2e'` |
| 瀏覽器 | chromium 單一 project |
| 重試 | `retries: 1`（既有設定；`ui-regression` 容忍 `stats.flaky`、不容忍 `stats.unexpected`） |
| 新增設定 | **無**。新 spec 檔丟進 `frontend/tests/e2e/` 即被自動收集（`ui-regression.lock.yml:558` 跑裸 `npx playwright test`） |

## 二、如何只跑本單元的測試（**精確到檔**，不是專案層指令）

```bash
cd frontend && npx playwright test tests/e2e/member-pages.spec.ts
```

- 這是 `unit-test-instructions.md` 要求的「scoped to this unit only」形式：
  **指定確切檔案路徑**，不是 `npm test` 或 `npx playwright test`。
  Build and Test 會逐單元執行各自的指令，未限定範圍的指令會讓整個套件被重跑 24 次。
- 第一次測試步驟之前先驗執行器可用：

```bash
cd frontend && npx playwright test tests/e2e/member-pages.spec.ts --list
```

  檔案尚不存在時應回報 0 個測試（而非設定錯誤）；若回報設定錯誤，
  則 `test-after` 的第一個測試步驟無效，須先修設定。

- 需要本機完整 stack 時（e2e 對短生命週期 stack 執行）：
  依 `LOCAL-DEV.md` 的 Docker 模式（`deploy/docker-compose.test.yml`，入口 `:8090`）。
  **本單元不需要 `claude` CLI 或 n8n webhook**（那兩個隱性依賴屬 A1／A3 路徑）。

## 三、覆蓋目標

| 目標 | 本單元的立場 |
|---|---|
| `org.md` 的「最低 80% line coverage」 | **目前無法量測也無法強制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step——`team.md` 逐字記載為「宣告而非閘門」）。本單元**不聲稱**達成它，也不在本檔弱化它的宣稱 |
| 實際門檻 | `team.md` 的 **C 規則**：前端資料形狀變更需 e2e 斷言。本單元的資料形狀全新（`MemberView` 四欄、`ReselectionOut` 九欄），故 C 規則適用且由 §四 的 8 個案例承擔 |
| 二元可判的覆蓋面 | `cicd-pipeline.md` §五 的 8 個斷言標的，缺一即視為未覆蓋 |

## 四、8 個案例與 standard 量級的對應

standard 要求「每元件 5–8 個測試」。本單元有 6 個邏輯元件，但它們**無法各自獨立
測試**——沒有 component 測試框架，唯一的測試介面是整頁的 DOM 與網路請求。
故量級以**可觀察行為**而非元件計：

| # | 案例 | 受測元件 | 它會真的失敗的條件 |
|---|---|---|---|
| 1 | 100 列上限與提示 | `MembersListPage` | 構造 101 位 → 清單不存在且提示存在；構造 100 位 → 清單存在 |
| 2 | 橫幅請求數（兩分支） | `ReselectionBannerHost` | 有 `K3 view` 換頁 N 次＝N 次；缺 `K3 view`＝**0** 次（前置 `can()` 判定；若誤用 `BR21.3` 的重試語意則為 1 次而紅燈） |
| 3 | 三操作後不整份重抓 | 清單頁＋詳情頁 | 攔截 `GET .../members`，邀請／改角色／移出後其請求數不增加 |
| 4 | 首次可互動前請求數為 1 | `MembersListPage` | `canManage` 若另發請求則為 2，紅燈 |
| 5 | per-project admin 但缺 `K3.edit` → 四控件全不存在 | `MembersListPage`＋詳情頁 | 這是審查 `R-01` 查出的可達壞狀態；缺此斷言則「控件渲染後每次寫入永久 403」的死循環不會被任何閘門抓到 |
| 6 | 一般成員身分 → 四控件全不存在 | 同上 | `SEC-U24-5` |
| 7 | 三條失敗路徑各有 console 訊號，且不含使用者文字 | `failureSignal`＋抓取層 | `page.on('console')` 收集後比對；完全不輸出即紅燈（這是 `R-07` 兜底規則的可失敗面） |
| 8 | 橫幅宿主無條件渲染**且** `role="status"` | `ReselectionBannerHost` | 選擇器命中**＋** `role` 屬性等於 `status`——**兩者缺一不可**：只驗選擇器時把 `role` 拿掉仍會綠燈，而 `role="status"` 正是 `BR21.1` 自述的結構前提 |

### 4.1 合併前必修第 9 項（Request Changes 修訂，計畫 §五之一）

案例 1 的語意改變：原「101 位 → 清單不存在且提示存在」是**缺陷本身**的斷言，改為：

| # | 案例 | 通過條件 | 會真的失敗的條件 |
|---|---|---|---|
| 1 | 101 位成員分頁顯示 | 清單存在、第 1 頁 50 列、顯示「共 3 頁／101 位」；翻到第 3 頁可見第 101 位，其管理控件（具權限時）存在且可操作 | 還原 100 列整表隱藏閘 → 清單不存在，紅燈 |
| 1b | 100 位成員 | 清單存在、共 2 頁 | 頁數計算錯誤（例如 off-by-one 成 3 頁）→ 紅燈 |

既有案例 3（三操作後不整份重抓）與 4（首次可互動前請求數為 1）在分頁下仍須綠。測試資料沿用 §六 的 `page.route()` 程式產生，不建 fixture 檔。

## 五、Mock／Stub 指引

| 對象 | 做法 |
|---|---|
| 六個 `/api/membership` 端點 | `page.route()` 攔截並回固定 payload。**不打真實後端**——本單元測的是前端對既有契約的消費，不是 `U19` 的正確性 |
| 角色與權限 | 以 stub 的 `list_members` 回應控制 per-project `role`；以登入帳號控制全域 `can("K3", …)`。**案例 5 的構造方式**：per-project 回 `project_admin`，但登入帳號用缺 `K3.edit` 的角色（`FinOps_Analyst`／`Security_Reviewer`／`Platform_Owner` 三者之一，`rbac_seed_data.py:342`／`:346`／`:348` 逐字 `True, False, False`） |
| 403／409／422／5xx | 以 `page.route()` 回對應狀態。422 要**兩種** `detail`：字串（缺全域權限）與物件陣列（pydantic 驗證錯誤） |
| console | `page.on('console')` 收集後比對，**不**用 `expect(page).toHaveLogged` 之類不存在的 API |

## 六、測試資料管理

| 項目 | 做法 |
|---|---|
| 101 位成員 | 在 `page.route()` 的 handler 內程式產生（`Array.from({length: 101})`），**不建 fixture 檔**——資料只有形狀重要，內容不重要 |
| 顯示名稱與 email | 用明顯的假值（`e2e-user-NN`／`e2e-NN@example.invalid`）。案例 7 要斷言 console **不含**它們，故它們必須是可搜尋的獨特字串 |
| 清理 | 無須清理：全部走 `page.route()` 攔截，不碰資料庫 |

## 七、名稱穩定性（**落地後不可改**）

`ui-regression.lock.yml` 的 Kiwi 回報步驟逐字註解：「The template must stay stable
— it is the key the plugin reuses cases by; **changing it orphans the old cases**」。
TCMS 案例名稱為 `<describe> › <test>`，故本 spec 的 `describe` 與每個 `test` 字串
**一旦合併就不得再改**，否則既有案例變成沒有執行結果的孤兒。

建議 `describe` 名稱：`U24 member pages`（固定）。
