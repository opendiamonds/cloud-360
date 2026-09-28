# 發現規則（Discovered Rules）

> practices-discovery 產物｜intent `260819-cost-finops`｜HEAD `c3de2c8`｜2026-08-19
>
> **來源說明**：本檔僅記錄人工已明確核可的 hard constraint，或明確提出供下次訪談確認的候選規則。
> 未列入「宣告」(ALWAYS / NEVER) 的待補承載機制條目以「待補（非阻擋）」標記。
> 所有 `[proposed — 待訪談]` 條目已於 2026-08-19 人工訪談後全數定案或移除。

---

## Mandated

- **ALWAYS** 第一個 C1 HTTP 端點落地時，即使 `role_permissions` seed 未改，也須有 allow/deny 雙向 TestClient：有 C1 權限 → 2xx，無 C1 權限 → 403（不得只測 happy path）
- **ALWAYS** cost 功能域採三層：`cost_router` → `cost_service` → 純函式 `cost_calculator`，另獨立 `pricing_client`；禁止把 cost 邏輯寫進 `user_router.py` 或 `wa_rule_engine.py`；`cost_calculator` 內禁止 httpx、DB session、`HTTPException`

## Forbidden

- **NEVER** 呼叫需要雲端供應商帳號憑證的計價 API（Cost Explorer、Billing、Cost Management 等）作為 C1 價目來源；`pricing_client` 只准公開免帳號價目端點
- **NEVER** 把 WA `COST-*` 啟發式 findings 當成已實作的 TCO／成本計算能力
- **NEVER** 把 Assessment 的雲端供應商下拉當成 pricing Manual Override
- **NEVER** 把 RBAC 種子或權限頁的 C1 欄當成已有 cost router／Cost 頁
- **NEVER** 在既有 n8n／PNG 呼叫點用 httpx 直接打雲端 Pricing API；新計價呼叫必須走獨立 `pricing_client`

## 待補承載機制（非本輪阻擋，但屬已識別缺口）

下列為已在 `team.md` 如實記載但尚未修復的機制缺口。本輪不逕自修復（未經訪談定案），但記為待補，以便下次 practices-discovery 或專項 intent 承接：

| 缺口 | 現況 | 建議修復方式 |
|---|---|---|
| Secret 掃描作用域 | `validate_no_obvious_secrets()` 只掃 12 個 contract 檔，看不到 `backend/`、`frontend/`、`.env.example` | 擴大 `contract_files()` 或加獨立 secret scan job（如 truffleHog / gitleaks） |
| Production 路徑檢查在 CI 恆為 no-op | `validate_no_production_config_added()` 用 `git diff --name-only`（unstaged + staged），CI 乾淨 checkout 兩者皆空 | 改用 `git diff HEAD~1 --name-only` 或 `git diff origin/ut --name-only` |
| Backend 無 linter / formatter | 無 Ruff、Black、mypy／pyright；`org.md` 宣告但 backend 側不成立 | 在 CI `backend` job 加 `ruff check` 與 `black --check`，從 no-error 基線開始 |
| Backend 依賴多數未 pin | 只有 FastAPI `==0.141.1`、Pydantic `==2.13.4` 精確釘選；其餘未 pin 且無 lockfile | 評估引入 `pip-tools` 產出 `requirements.lock`，或補全版本約束 |
| Coverage gate 缺失 | 無 `.coveragerc`、無 `coverage` / `pytest-cov`、CI 無 coverage step；`org.md` 80% 是宣告非閘門 | 引入 `coverage.py`，先量再訂門檻；從零開始量取存量，再以增量不回退作為漸進目標 |
