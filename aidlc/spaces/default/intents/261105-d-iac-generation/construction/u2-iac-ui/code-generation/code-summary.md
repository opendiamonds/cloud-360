# 程式碼摘要：U2 `u2-iac-ui`

側邊選單新增可收合的「基礎建設」，底下三項依 view 權限顯示：`/iac/generate`（D1，Terraform 產出）、`/iac/scan`（D2，IaC 安全掃描）、`/iac/secrets`（D3，Secret／敏感值）。點進去是同一個工作區，步驟跟網址一起換。`WorkspacePage` 工具列的「生成 IaC 代碼」仍是 `iac-entry`。沒有 D1 view 時該入口 disabled，並顯示「缺少 D1 view 權限，無法進入 IaC 工作區。」

工作區是畫布欄上的覆層。步驟可自由點；footer 只換步驟。Aside 顯示活躍圖、`iac-diagram-select`、`iac-diagram-upload`。無圖時主區阻擋，並有回到 Workspace 的控制項，D1 不能送出。切圖會中止進行中的請求、清掉本機檢視，並顯示清空文字。上傳非 `.drawio`／`.xml` 或 HTTP 失敗時，不改目前的 `diagram_id`。

產生、掃描、改寫、下載都走 `apiUrl()` 與手寫 `Authorization: Bearer`。抓取函式不碰 state。D1 失敗只顯示 `error.code` 對照文案與重試，不清掉先前預覽。403 顯示缺權說明。掃描嚴重度以 `HIGH`／`CRITICAL` 等文字呈現。HIGH／CRITICAL 不阻止進入改寫步驟；下載則先開 `role="dialog"` 的確認框，Esc 與取消不下載，關閉後焦點回到下載按鈕。下載用 blob 物件 URL，完成或卸載時 revoke。畫面沒有 apply 或 destroy。改寫清單只渲染路徑，不渲染正文。沒有把 HCL、改寫正文或完整 fetch body 寫進 `console.log`。

## 逾時（數字未調降）

| 呼叫 | 實作 | 下限 |
|---|---|---|
| `POST /api/iac/generate` | 90_000 ms | ≥ 90s |
| `GET /api/iac/session`、`POST /api/iac/scan`、`POST /api/iac/secrets/rewrite` | 10_000 ms | > 2s |
| `GET /api/iac/download` | 15_000 ms | > 5s |

常數在 `frontend/src/iac/iacApi.ts` 的 `IAC_TIMEOUT_MS`。切圖與卸載會 `abort()`，過期回應不寫入 state。打開工作區不等待 D1，也不為 session 擋住 Workspace 首屏。

## 80% 行覆蓋率缺口

`org.md` 的 feature 下限仍是 **80%**。本 repo 前端沒有 coverage 工具，也沒有 `fail_under`。這次沒有把 80 改成 0，也沒有新增 vitest 或 jest 來假裝能量測。前端唯一的自動化層是既有 Playwright；`frontend/tests/e2e/iac-workspace.spec.ts` 落在 `playwright.config.ts` 的 `testDir: ./tests/e2e`，會被既有 `ui-regression` 的 `playwright test` 撿到。那是 e2e 閘，不是行覆蓋率閘。

## 驗證

- `npx eslint`（專案內 `frontend/node_modules/.bin/eslint`）對本單元碰過的檔案：**0 errors**。`WorkspacePage.tsx:306` 有 1 則既有 `react-hooks/exhaustive-deps` warning（bootstrap effect 的 `fetchDiagrams`）。這則 warning 原本在第 279 行；本輪只因檔案變長而位移，沒有新增 warning。
- `frontend/` 的 `tsc -b --pretty false`：**通過**（exit 0）。
- 單元指令 `npx playwright test tests/e2e/iac-workspace.spec.ts --project=chromium`：**沒有執行**。`http://localhost:8090` 連線失敗（curl HTTP `000`）。規格已寫好，不能把這次記成通過。
- `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/iac-workspace.spec.ts`：8/8，ERROR 0，WARN 0。

## 行為與計畫

行為照核准計畫。步驟面板放在 `IacWorkspace.tsx`，沒有另開一個面板檔；設計允許微調檔名，test id 沒有改。沒有改 `role_permissions`、U1 閘、PBT、OpenAPI、Checkov 或 Postgres。

## ADR-0006 四面向

| 面向 | 處置 |
|---|---|
| IAM | 入口看 D1 view；產生與下載看 D1 edit；掃描看 D2 edit；改寫看 D3 edit。403 只顯示缺權短語。種子沒有改。 |
| Encryption | 不下載密文 query。zip 走 blob 物件 URL，完成或卸載 revoke。 |
| Network exposure | 只打既有 `/api/iac` 與既有建圖 API。沒有新的對外暴露。 |
| Audit logging | 瀏覽器不記錄 HCL、改寫正文或完整 body。伺服器稽核仍在 U1。 |
