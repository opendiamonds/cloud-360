# Unit Test Instructions — `U15 memory-page-ui`

> 本單元有兩個測試層：**後端 `unittest` ＋ `TestClient`**（已核准檢查，Step 3–6）
> 與 **前端 Playwright e2e**（記憶頁，Step 7–10）。前端沒有 unit／component 測試框架
> （`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`；引入是
> `team.md` Q4 的 D 項不採用），故前端的唯一自動化層是 e2e。
>
> Test strategy **standard**、方法論 **`test-after`**。

## 一、測試框架與設定

| 層 | 框架 | 設定 | 新增設定 |
|---|---|---|---|
| 後端 | Python `unittest` ＋ `starlette.testclient.TestClient`，in-memory SQLite（`backend/tests/helpers.py`） | 既有 | 無 |
| 前端 | `@playwright/test`，chromium 單一 project | `frontend/playwright.config.ts:10` `testDir: './tests/e2e'` | 無；新 spec 丟進該目錄即被收集 |

## 二、如何只跑本單元的測試（精確到檔）

後端（本機一律用 `python3`；裸 `python` 在本 worktree 為 command not found）：

```bash
cd backend && python3 -m unittest tests.test_memory_pending_authz -v
```

後端回歸（本單元改了 `U8` 的 facade 與 router，以下兩檔必須仍全綠）：

```bash
cd backend && python3 -m unittest tests.test_memory_authz tests.test_memory_contract -v
```

OpenAPI 漂移：

```bash
python3 backend/scripts/dump_openapi.py --check
```

前端 e2e：

```bash
cd frontend && npx playwright test tests/e2e/memory-page.spec.ts
```

第一個測試步驟之前先驗執行器（Step 2）：

```bash
cd backend && python3 -m unittest tests.test_memory_authz -v
cd frontend && npx playwright test tests/e2e/memory-page.spec.ts --list
```

前者應全綠；後者在檔案尚不存在時應回報 0 個測試而非設定錯誤。

## 三、覆蓋目標

| 目標 | 立場 |
|---|---|
| `org.md` 的 80% line coverage | **目前無法量測也無法強制**（`team.md` 逐字記為「宣告而非閘門」）。本單元不聲稱達成，也不弱化其宣稱 |
| 實際門檻 | `team.md` A＋B（授權變更的雙向 `TestClient`）與 C（前端新資料形狀的 e2e 斷言），兩者皆由下表承擔 |

## 四、案例清單

### 四之一、後端 `tests/test_memory_pending_authz.py`（7 個）

| # | 案例 | 會真的失敗的條件 |
|---|---|---|
| B1 | pending 帳號 `GET /api/memory/records` → 403 | 移除 facade 的已核准檢查即回 200 |
| B2 | pending 帳號 `POST /api/memory/records` → 403 | 同上（回 201） |
| B3 | pending 帳號 `DELETE` **不存在**的 id → 403 而非 404 | 檢查若放在取列之後即回 404，證明判定先於取列 |
| B4 | pending 帳號 `PUT .../scope` 與 `GET /audit-events` → 403 | 同 B1 |
| B5 | approved 帳號上述五條 → 對應 2xx（雙向的 allow 側） | 檢查若誤判 approved 為 pending 即紅 |
| B6 | 同進程：pending principal 直呼 `MemoryFacade.list_records` → raise `MemoryForbidden` | 檢查若放在 router 即不 raise（`intent_routing.py` 的路徑） |
| B7 | `mint_principal` 對 pending／rejected／approved 三種 `User` 的 `is_approved` 正確 | 欄位填錯即紅 |

### 四之二、前端 `tests/e2e/memory-page.spec.ts`（`describe`：`U15 memory page`，10 個）

| # | 案例 | 會真的失敗的條件 |
|---|---|---|
| E1 | Sidebar 出現「我的記憶」，點擊進入 `/memory`，三區依序存在 | 判定或路由錯誤 |
| E2 | 開頁恰 3 個 `GET`，參數為 `semantic`/200、`procedure`/200、`episodic`/0/21 | 請求數或參數錯誤（`UIP-1`／`UIP-2`／`UIP-5`） |
| E3 | 單一區失敗只有該區出現 `-error`、不出現 `-empty` | `empty` 與 `error` 共用畫面（`BR32.3`） |
| E4 | 自己的列：擁有者「你」＋ `data-owner-user-id`＝自己 id；他人 `platform` 列：無 `-delete`、可見文字不含數字、仍在 DOM | 前端過濾或渲染刪除鍵（`SEC-U15-1`／`-4`、`BR35.2`） |
| E5 | 刪除流程：確認列、Escape 取消不發請求、確認後該列消失並播報；確認文字含「記錄」 | `BR34.1`／`BR34.2`／`NFR7.91` |
| E6 | **offset 位移**：第 1 頁刪一則後，原第 21 筆出現在第 1 頁；翻到第 2 頁無漏列 | 不做背景重抓即漏列（審查 R-01） |
| E7 | **重抓中翻頁**：延遲背景重抓的回應，期間翻到第 2 頁；重抓回來後畫面仍是第 2 頁 | 以 `cancelled` flag 而非序號防亂序即被舊頁覆蓋 |
| E8 | **重抓失敗**：背景重抓回 500 → 出現「清單同步失敗」提示；刪空第 2 頁 → 退回第 1 頁且只退一次 | 靜默或連退兩頁（審查 R-02／R-03） |
| E9 | 內容為 `<img src=x onerror=window.__xss=1>` 的記憶以文字顯示、`window.__xss` 未定義 | 引入 `dangerouslySetInnerHTML` |
| E10 | 進頁→離開→再進，再次發出 3 個 `GET`；`localStorage`／`sessionStorage` 鍵集合無新增；console 不含種子記憶內容 | 跨頁快取或落地（`NFR4.90`／`NFR7.90`／`SEC-U15-5`） |

## 五、Mock／Stub 指引

| 對象 | 做法 |
|---|---|
| `/api/memory/records` | 以 `page.route()` 攔截並以程式維護一份記憶陣列，`GET` 依 `offset`／`limit` 切片、`DELETE` 從陣列移除——這樣才模擬得出 E6 的 offset 位移。**不打真實後端**（後端正確性由四之一負責） |
| 延遲與失敗 | `route.fulfill` 前 `await` 一個由測試控制的 promise，**不用 `waitForTimeout`**（避免 flaky 被 `retries: 1` 掩蓋） |
| 登入 | 沿用 `regression.spec.ts` 的登入形狀（`請輸入您的帳號`／`請輸入密碼`／`登入系統`） |
| 後端測試的 pending 帳號 | 以 `User(authorization_status="pending")` 建立；`get_current_user` 以 `app.dependency_overrides` 覆寫，**不**覆寫 facade |

## 六、測試資料管理

| 項目 | 做法 |
|---|---|
| e2e 記憶資料 | 在 `page.route` handler 內以程式產生；內容用可搜尋的獨特字串（`e2e-memory-NN`），E10 要斷言 console 不含它們 |
| 後端資料 | 每個測試以 SQLite session 自建，`tearDown` 清除，沿用 `MemoryAuthzTestBase` |

## 七、名稱穩定性（落地後不可改）

TCMS 案例名稱為 `<describe> › <test>`（`ui-regression.lock.yml` 的 Kiwi 回報註解逐字「changing it orphans the old cases」）。`describe` 固定為 `U15 memory page`，各 `test` 字串一經合併不得再改。
