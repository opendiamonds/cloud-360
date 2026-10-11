# CI/CD Pipeline — `U24 member-pages-ui`

> 本單元對管線的改動是 **0 行**，而本檔的工作是把那個 0 寫成下游可複驗的形式，
> 並誠實指出六道既有閘門中哪幾道**抓不到**本單元的失敗路徑。
>
> **本站未派審查員**（依 2026-10-06 核可的精簡做法），故本檔的主張未經獨立複驗；
> 每一條都附可複驗指令以彌補。此事於核可關卡一併揭露。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/member-pages-ui/nfr-design/performance-design.md` | `UIP-1`–`UIP-5` 的量測方式（全為 Playwright e2e） |
| `construction/member-pages-ui/nfr-design/security-design.md` | `SEC-U24-6` 的 `page.on('console')` 斷言、`canManage` 兩段式前置 |
| `construction/member-pages-ui/nfr-design/logical-components.md` | §三之一 的 `Layout.tsx` 改動範圍 |
| `construction/member-pages-ui/functional-design/functional-spec.md` | 六個 API 消費點 |
| `inception/contract-design/contract-summary.md` | `K-16` 的契約面 |

## 一、新 e2e spec 不需任何管線改動（**實測，非推論**）

| 查證 | 結果 |
|---|---|
| `ui-regression` 怎麼挑測試 | `.github/workflows/ui-regression.lock.yml:558` 逐字 `run: timeout 15m npx playwright test`——**裸指令，無檔案清單、無 `--grep`** |
| Playwright 的收集範圍 | `frontend/playwright.config.ts:10` 逐字 `testDir: './tests/e2e',` |
| 既有 spec 檔 | `frontend/tests/e2e/` 下兩支：`regression.spec.ts`、`estimate-workspace.spec.ts` |
| 結論 | 新 spec 檔**丟進 `frontend/tests/e2e/` 即被自動撿到**，`ui-regression.lock.yml` 與 `package.json` 皆零改動 |

## 二、`ui-regression` 是真閘門，且它是本單元唯一能碰到畫面的自動化層

| 面向 | 內容 |
|---|---|
| 閘門機制 | `post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`；容忍 `stats.flaky`，`retries: 1`（`team.md` 記載） |
| 執行對象 | 每個 PR 自動起的短生命週期 stack（`deploy/docker-compose.test.yml`，前端對外 `8090:80`） |
| 瀏覽器 | chromium 單一 project |
| 本單元的依賴 | **全部** `UIP-*`／`SEC-U24-*`／`BR2x.y` 的驗證都落在這一層——前端無 unit／component 測試框架（`TS-U24-2`） |

## 三、**名稱穩定性是一條硬約束**（改了會製造孤兒案例）

`ui-regression.lock.yml` 的 Kiwi 回報步驟逐字註解：

> `--summary-template '${name}'` drops the "regression.spec.ts." classname prefix
> so the Kiwi case name is just the test title. … **The template must stay stable
> — it is the key the plugin reuses cases by; changing it orphans the old cases.**

對本單元的直接後果：**新 e2e 的 `describe › test` 字串一旦落地就不能再改**，
否則既有案例會變成沒有執行結果的孤兒。決定名稱的時點是 `code-generation`，
而不是 `tcms-test-cases`——該站只做同步，名稱那時已經固定。
此約束與 `project.md` 的 `tcms-test-cases` 規則一致（「TCMS 案例名稱是
`<describe> › <test>`……改動 describe／test 字串會讓既有案例變成孤兒」）。

## 四、六道既有閘門對本單元失敗路徑的逐道判定（**誠實記載哪幾道無效**）

本單元最可能的失敗路徑：**前端把伺服器回傳的 `role` 讀錯或漏讀，導致管理控件
在不該出現時出現（或反之）**。逐道判定：

| # | 閘門 | 對上述路徑有效？ | 理由 |
|---|---|---|---|
| 1 | `repo-contract`（`validate_repo_contract.py`） | ❌ | 檢查必要文件、禁止路徑與禁止內容；其 secret 掃描只讀 `contract_files()`，**結構上看不到 `frontend/`**（`team.md` 已記載） |
| 2 | frontend lint（`eslint .`） | ❌ 對此路徑 | 它擋的是 hook 規則與不可變性（16 條 error 級）；讀錯欄位不違反任何 lint 規則。現況 `0 errors, 3 warnings` 且 CI 未加 `--max-warnings 0` |
| 3 | `tsc -b` typecheck | ❌ | `team.md` 逐字記載它對前後端 schema 落差**無效**：`AdminPage.tsx` 的 `DbUser` 是手寫 interface，`const data = await res.json(); return data;` 把 `any` 放行。本單元若也手寫 `MemberView` 型別，同一個缺口原樣適用 |
| 4 | OpenAPI drift 檢查（`dump_openapi.py --check`） | ⚠️ 部分 | 它擋的是「後端回應 schema 改了但 `openapi.json` 沒重 dump」。本單元**不改後端**，故這道對本單元不觸發；但它保護的是反向——若 `U19` 之後改 `MemberView`，這道會紅，前端的 `gen:types` 產物隨之更新 |
| 5 | backend `unittest` | ❌ | 本單元零後端程式 |
| 6 | **`ui-regression`（Playwright e2e）** | ✅ **唯一有效的一道** | `BR22.3` 的 observable、`SEC-U24-5`（四控件在一般成員身分下全部不存在）、`UIP-1`–`UIP-4` 的請求數斷言都在這一層 |

**這張表的用途**：讓「本單元的品質完全押在第 6 道」成為一個被寫下來的事實。
若 `ui-regression` 因任何原因被停用或變成非阻擋，本單元**沒有任何替代防護**。

## 五、本單元需要新增的 e2e 案例（供 `code-generation` 與 `tcms-test-cases` 承接）

| 斷言標的 | 來源 | 為什麼它會真的失敗 |
|---|---|---|
| 清單 100 列上限 ＋ 超過時的提示 | `UIP-1` | 構造 101 位成員 → 斷言清單不存在且提示存在；構造 100 位 → 斷言清單存在 |
| 橫幅查詢的請求數 | `UIP-2` | 攔截 `GET /reselections/pending`；有 `K3 view` 者換頁 N 次＝N 次，缺 `K3 view` 者＝**0** 次（前置 `can()` 判定，非 `BR21.3`） |
| 三種操作後不整份重抓 | `UIP-3` | 攔截 `GET .../members`，三操作後請求數不增加 |
| 首次可互動前請求數 | `UIP-4` | 進入成員頁後對 `/api/membership/**` 的請求數為 1 |
| **四控件在「per-project admin 但缺 `K3.edit`」下全部不存在** | `canManage` 兩段式（`security-design.md` §一之三） | 這是審查 `R-01` 查出的可達壞狀態；缺此斷言則死循環不會被任何閘門抓到 |
| 四控件在一般成員身分下全部不存在 | `SEC-U24-5` | 同上，另一個角色面 |
| 三條失敗路徑各有 console 訊號、且不含使用者文字 | `SEC-U24-6`／`SEC-U24-1` | `page.on('console')` 收集後比對 |
| 橫幅宿主無條件渲染 ＋ `role="status"` | `BR21.1` | 選擇器命中**＋** `role` 屬性等於 `status`（兩者缺一不可——只驗選擇器時把 `role` 拿掉仍會綠燈） |

**突變驗證義務**（`project.md` 的 `tcms-test-cases` 必做 3）：每支腳本都要把修正
改回錯的行為、確認紅燈、還原複驗。本表最值得突變的是最後一條與 `canManage` 那條。

## 六、部署與回滾

| 面向 | 內容 |
|---|---|
| 部署路徑 | 不變：merge 進 `ut` → `deploy.yml` → 自架 staging（`192.168.10.10`）。本單元不改 `deploy.yml` |
| 建置 | 不變：`docker-build` job 以 buildx 建兩個 image（`push: false`） |
| 回滾 | 不變：`deploy.yml` 的 `rollback` job 還原 last-good ＋ 開 revert PR ＋ dispatch Deploy Doctor。本單元的改動是純前端單檔與新 spec 檔，`git revert` 即完整回滾——**無 schema、無設定、無資料遷移** |
| 新增的部署前置 | **無**。`TS-U24-7` 的零新環境變數使 `render-env.sh` 與 `deploy/.env.example` 的同步義務為空集合 |
