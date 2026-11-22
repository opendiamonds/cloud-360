# 單元測試說明：U2 `u2-iac-ui`

本檔只涵蓋 `u2-iac-ui`。U1 的 unittest 不在本單元重跑。

## 框架

- 沿用既有 Playwright（`@playwright/test`），project 為 `chromium`。不新增 vitest、jest 或 `@testing-library`。
- 測試檔放在 `frontend/tests/e2e/iac-workspace.spec.ts`，由既有 `npm run test:e2e` 的 `playwright test` 撿到。
- API 以 `page.route` stub `/api/iac/*`，回傳符合 U1 契約的 JSON。不呼叫 OpenRouter，不要求 Checkov。
- 登入沿用既有 e2e 的登入方式。無權與有權用兩種使用者，或 stub 權限回應；不改 `role_permissions` seed。

## 執行本單元（核准前已核對 runner）

工作目錄 `frontend/`。下列指令只點名本單元的規格檔，不是全專案 `playwright test`：

```bash
npx playwright test tests/e2e/iac-workspace.spec.ts --project=chromium
```

Brownfield：第一步先確認 `frontend/package.json` 的 `test:e2e` 仍是 `playwright test`，且 `playwright.config.ts` 的 `testDir` 為 `./tests/e2e`。上面這條才是本單元的執行指令。需要與既有 e2e 相同的 `BASE_URL`（預設 `http://localhost:8090`）。

## 覆蓋目標（不調降）

- 策略 Standard：這個畫面元件 8 則測試，涵蓋入口、選圖、三步驟與下載確認。
- 範圍 feature：行覆蓋率目標 80%，且測試在 CI 合併前會被既有 `ui-regression` 撿到。
- 現況前端沒有 unit coverage 閘。本單元不把門檻改成 0。若無法在不新增未決工具的前提下強制 80%，於 `code-summary.md` 如實寫出缺口，數字維持 80。
- 團隊規則 C：Coming Soon 換成真畫面後，至少一則斷言入口不再是 Coming Soon，且生成成功時預覽區出現 stub 回傳的檔名。

## 案例

| # | 斷言 |
|---|---|
| 1 | 無 D1 view：`iac-entry` disabled，可見缺權說明，點擊不打開步驟殼 |
| 2 | 有 D1 view：進入殼，可見 `iac-diagram-select` |
| 3 | 無圖：主區阻擋文案與回 Workspace 的控制項可見，`iac-run-d1` disabled |
| 4 | 有圖且有 D1 edit：按 `iac-run-d1` 後，送出的 POST `/api/iac/generate` 帶 `diagram_id`；`iac-file-tree` 與 `iac-hcl-preview` 出現 stub 檔名與內容 |
| 5 | 生成回錯誤碼時，可見對應錯誤文案；若先前已有預覽，預覽文字仍在 |
| 6 | 掃描步驟可直接打開；無草稿時 `iac-run-d2` disabled；有報告時 `iac-findings` 含嚴重度文字 |
| 7 | 無成功掃描時改寫執行鈕 disabled；改寫成功後 `iac-rewrite-list` 不含注入的明文樣式 |
| 8 | 報告為 HIGH 時按 `iac-download` 出現 `iac-download-confirm`；Esc 後沒有 download 請求；確認後才出現 GET `/api/iac/download`。畫面沒有 apply 或 destroy 控制項 |

## Mock 與測試資料

- `/api/iac/session`、`/generate`、`/scan`、`/secrets/rewrite`、`/download` 都由 `page.route` 回應。
- 明文樣式用測試專用假字串，不使用真實雲端金鑰。
- 圖只傳 `diagram_id`。不在這個測試檔建立圖的生命週期。

## 不在本單元

- `python -m unittest`、Hypothesis、後端 TestClient。
- 全專案 `npx playwright test` 或 `npm run test:e2e` 當作本單元指令。
- 新的 Playwright config 或 CI job。
