# 單元測試說明：U1 `u1-iac-api`

本檔只涵蓋 `u1-iac-api`。U2 的 Playwright 不在本單元。

## 框架

- 沿用既有 Python `unittest` + `hypothesis` + `unittest.mock`。不新增 pytest、vitest、jest。
- 測試檔放在 `backend/tests/`，檔名 `test_iac_*.py`，由既有 `python -m unittest discover -s tests` 撿到。
- DB 策略沿用 `backend/tests/helpers.py`（psycopg2 mock、SQLite）。本單元不新增 Postgres 表，HTTP 測試以 `TestClient` 與 `dependency_overrides` 覆寫 `get_current_user`。
- 純函式核心（generator、scanner、redactor）禁止在測試裡連真實 LLM、真實 Checkov 或雲端 API。agent／CLI 以 stub 注入。

## 執行本單元（核准前已核對 runner）

工作目錄 `backend/`，與 `ci.yml` backend job 相同。下列指令只點名本單元的測試模組，不是全專案 `discover`：

```bash
python -m unittest tests.test_iac_generator tests.test_iac_scanner tests.test_iac_redactor tests.test_iac_session tests.test_iac_http -v
```

Brownfield：第一步先確認既有 runner 可執行（`python -m unittest discover -s tests -v` 的入口仍是 `unittest`），再寫本單元測試。上面這條才是本單元的執行指令，Build and Test 會逐單元呼叫它。

## 覆蓋目標（不調降）

- 策略 Standard：每個元件 5–8 則測試，另加關鍵邊界的整合測試。
- 範圍 feature：`backend/iac/` 行覆蓋率目標 80%，且測試在 CI 合併前執行。
- 現況 repo 沒有 coverage 閘門。本單元不把門檻改成 0、也不關掉失敗條件來讓步驟通過。若本 PR 無法在不新增未決工具的前提下強制 80%，於 `code-summary.md` 如實寫出缺口，數字維持 80。
- ADR-0006／本輪 Affirm：generator、scanner、redactor 必須含 Hypothesis，不得只有 example-based。
- D3：注入明文樣式後，回應、log 抽樣與 zip 不得再出現該樣式；拿掉遮罩後對應測試必須變紅，還原後變綠。

## 元件與則數

| 檔案 | 元件 | 則數 | 內容 |
|---|---|---|---|
| `backend/tests/test_iac_generator.py` | `IacModuleGenerator` 純函式 | 6 + Hypothesis | 模組樹含 `main.tf`／`variables.tf`／`outputs.tf`；相對路徑不逃逸；非主要雲不靜默丟棄（BR1.8）；不 import `httpx`、DB session、`HTTPException` |
| `backend/tests/test_iac_scanner.py` | `IacStaticScanner` 報告形狀 | 6 + Hypothesis | 零 finding 時 `maxSeverity=NONE`；嚴重度列舉；CLI stub 失敗為 `failed`；不在本 PR 新增 CI scan job |
| `backend/tests/test_iac_redactor.py` | `IacSecretRedactor` 純函式 | 6 + Hypothesis + 突變 | 明文賦值被替換；輸出不含注入樣式；`rewrittenPaths` 只列改過的檔；拿掉遮罩應紅 |
| `backend/tests/test_iac_session.py` | 行程內 session | 8 | 鍵 `(userId, diagramId)`；generate 失敗保留舊成功草稿（BR1.9）；無草稿 scan／download 為 `missing_draft`；D3 無成功報告為 `missing_scan_report`；省略 `report_id` 取最新成功報告（BR1.13）；切圖後舊 `report_id` 為 `stale_report_id`（BR1.5）；槽 >16 MiB 拒絕；第 3 個 in-flight generate 為 429／busy |
| `backend/tests/test_iac_http.py` | `/api/iac` TestClient | 8 | 見下方成對授權 |

## HTTP 成對授權與閘（`test_iac_http.py`）

1. `POST /api/iac/generate` 無 D1 edit → 403
2. `POST /api/iac/generate` 有 D1 edit 且 `diagram_id` 有效（generator stub）→ 200，回應欄位集合與 schema 一致
3. `POST /api/iac/scan` 無 D2 edit → 403
4. `POST /api/iac/secrets/rewrite` 無 D3 edit → 403
5. `GET /api/iac/session` 無 D1 view → 403
6. `GET /api/iac/download` 僅 D1 view → 403
7. `GET /api/iac/download` 有 D1 edit 且草稿存在、報告 `maxSeverity=HIGH` → 200 `application/zip`（API 不因嚴重度拒絕，BR1.10）
8. `POST /api/iac/generate` 缺 `diagram_id` → 422，錯誤碼 `missing_diagram_id`

403 只用於 RBAC，不得改成 404。無產物的 `GET /session` 在 session 測試或本檔補斷言：200 且產物欄位為 null，不是 404。

## Mock 與測試資料

- 授權：覆寫 `get_current_user`，分別給有權與無權使用者。不改 `role_permissions` seed 也能做 2xx／403。
- 圖：只傳 `diagram_id`。圖內容用固定 fixture，不擁有 Diagram 生命週期。
- Generator／Scanner／Redactor：測試注入純函式或 stub，不呼叫 OpenRouter。
- Checkov：scanner 測試 stub 子行程 stdout。缺 CLI 時正式路徑回 D2 失敗，測試不要求映像內已安裝。
- 明文樣式用測試專用假字串，不使用真實雲端金鑰。

## 不在本單元

- 前端 e2e、vitest、新的 test runner 設定檔。
- 全專案 `python -m unittest discover` 當作本單元指令。
- CI 上的 Checkov／tfsec job。
