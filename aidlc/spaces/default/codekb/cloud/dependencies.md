# 相依關係（Dependencies）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan**
> 外部套件的**版本**記在 `technology-stack.md`，本檔只記相依邊與其後果。

## 跨套件相依方向

```
backend/main.py ──► backend/cost/ ──► backend/services/ ──► models.py / database.py
                └─► backend/services/ ─────────────────────► models.py / database.py
```

**`backend/services/` 之中沒有任何一支模組 import `cost.*`**（已全域比對）。相依方向單向為 `main → cost → services`，`backend/cost/` 只有**一條進入邊**：`backend/main.py:13`。

## `backend/cost/` 套件內部有向邊

`A → B` 表示 A import B：

| 模組 | import 的套件內模組 |
|---|---|
| `cost_router` | `cost_service` |
| `cost_service` | `config`、`cost_calculator`、`azure_calculator_runner`、`gcp_calculator_runner`、`cost_pricing_agent`、`diagram_extractor`、`price_cache`、`pricing_client`、`sku_mapper`、`sku_ai_resolver` |
| `cost_pricing_agent` | `azure_calculator_runner`、`config`、`diagram_extractor`、`gcp_calculator_runner`、`pricing_client`、`sku_mapper`、`sku_ai_resolver` |
| `pricing_client` | `config`、`pricing_gcp`、`pricing_azure`、`pricing_offer_parser`、`pricing_sdk` |
| `pricing_sdk` | `config`、`pricing_query_parser` |
| `pricing_azure` | `config`、`pricing_units` |
| `pricing_gcp` | `config`、`pricing_units` |
| `pricing_offer_parser` | `pricing_units` |
| `pricing_query_parser` | `pricing_units` |
| `sku_ai_resolver` | `config`、`sku_mapper` |
| `sku_mapper` | `config` |
| `azure_calculator_runner` | `config` |
| `gcp_calculator_runner` | `config`、`gcp_calculator_product_resolver`、`sku_ai_resolver` |
| `gcp_calculator_product_resolver` | `config`、`sku_ai_resolver` |
| `price_cache` | 套件內無（只依賴 `models.PricingCache`） |
| `cost_calculator` | 無（純函式，零相依、零 I/O） |
| `config` | 無（葉節點；import 時讀 9 份 YAML） |

**無循環引用。** 圖形化呈現與說明在 `architecture.md`。

## 反向索引（誰被誰引用）

| 模組 | 套件內引用者 | 套件外引用者 |
|---|---|---|
| `config.py` | 12 個模組 | `scripts/warm_aws_pricing_cache.py` |
| `pricing_units.py` | `pricing_azure`、`pricing_gcp`、`pricing_offer_parser`、`pricing_query_parser` | `tests/test_pricing_units.py` |
| `pricing_offer_parser.py` | `pricing_client` | `tests/test_pricing_client.py` |
| `pricing_query_parser.py` | `pricing_sdk` | 無 |
| `pricing_sdk.py` | `pricing_client` | `tests/test_pricing_sdk.py` |
| `pricing_azure.py` | `pricing_client` | `tests/test_pricing_azure.py` |
| `pricing_gcp.py` | `pricing_client` | `tests/test_pricing_gcp.py` |
| `pricing_client.py` | `cost_service`、`cost_pricing_agent` | `scripts/warm_aws_pricing_cache.py`、`tests/test_pricing_client.py`、`tests/test_pricing_azure.py` |
| `price_cache.py` | `cost_service` | `scripts/warm_aws_pricing_cache.py` |
| `sku_mapper.py` | `sku_ai_resolver`、`cost_service`、`cost_pricing_agent` | `tests/test_sku_mapper.py`、`tests/test_sku_ai_resolver.py` |
| `sku_ai_resolver.py` | `cost_service`、`cost_pricing_agent`、`gcp_calculator_product_resolver`、`gcp_calculator_runner` | `tests/test_sku_ai_resolver.py` |
| `diagram_extractor.py` | `cost_service`、`cost_pricing_agent` | `tests/test_diagram_extractor.py` |
| `cost_calculator.py` | `cost_service` | `tests/test_cost_calculator.py`、**`scripts/validate_cost_calculator_boundary.py`（CI 關卡，以路徑讀檔）** |
| `azure_calculator_runner.py` | `cost_service`、`cost_pricing_agent` | `tests/test_azure_calculator_runner.py`、`tests/test_azure_calculator_live.py` |
| `gcp_calculator_runner.py` | `cost_service`、`cost_pricing_agent` | `tests/test_gcp_calculator_runner.py` |
| `gcp_calculator_product_resolver.py` | `gcp_calculator_runner` | `tests/test_gcp_calculator_product_resolver.py` |
| `cost_pricing_agent.py` | `cost_service` | `tests/test_cost_pricing_agent.py` |
| `cost_service.py` | `cost_router` | `tests/test_cost_api*.py`（3 檔，透過 TestClient） |
| `cost_router.py` | 無 | **`backend/main.py:13`** |

## `backend/cost/` → 套件外的相依

| 來源 | 目標 | 備註 |
|---|---|---|
| `cost_router.py` | `database.get_db`、`models.User`、`services.auth.get_current_user` | 標準 FastAPI 依賴 |
| `cost_service.py` | `models.CostAuditEvent`／`DiagramCost`／`DiagramCostLine`／`User`／`UserDiagram` | 4 張 C1 表 |
| `cost_service.py:43` | **`services.collab_router._user_can_access_diagram`、`_visible_diagrams`** | **跨模組引用私有函式**，破壞封裝；改寫時需重新決定授權來源 |
| `cost_service.py` | `services.rbac.user_can` | `C1`／`C1h`／`C1r`／`C1o` 權限檢查 |
| `diagram_extractor.py` | `services.wa_rule_engine.sanitize_mxgraph_xml` | 新的上傳解析路徑若仍讀 mxGraph XML 會需要它 |
| `sku_ai_resolver.py` | `services.llm_provider`（4 個符號） | OpenRouter／CLI provider 切換 |
| `gcp_calculator_product_resolver.py`、`gcp_calculator_runner.py` | `services.llm_provider.llm_auth_ready` | |
| `cost_pricing_agent.py` | `claude_agent_sdk`、`services.llm_limits.agent_sdk_env`、`services.llm_provider` | agent 框架遷移的正面戰場 |
| `cost_pricing_agent.py` | `backend/prompts/cost_pricing_agent_system.md` | **以路徑載入**，拆除後會成為孤兒檔 |
| `price_cache.py` | `models.PricingCache` | |
| `config.py` | 同目錄 9 份 YAML | import 時載入，保留 `config.py` 即不能刪這些 YAML |

## 八類套件外掛鉤（退役時最易遺漏的部分）

只盤點「9 個端點 + 4 張表 + Playwright runners + spike scripts」會漏掉下列八類。**前三類會直接讓 CI 紅燈。**

1. **`scripts/warm_aws_pricing_cache.py:42-44`** 直接 import `cost.config`／`cost.price_cache`／`cost.pricing_client`——刪 `price_cache.py` 會讓這支腳本壞掉。
2. **`scripts/validate_cost_calculator_boundary.py`** 是 CI `repo-contract` job 的**第三步**，以硬編碼路徑指向 `backend/cost/cost_calculator.py`，**檔案不存在就 `return 1`**。刪掉 `cost_calculator.py` 而不同時改 `ci.yml` 與這支腳本，CI 立刻紅燈。
3. **`validate_env_contract.py` 的 `validate_local_dev_template_is_complete()`** 反向強制 `backend/` 讀到的每個環境變數都必須記載於 `backend/.env.example`。移除 `COST_PRICING_STUB`／`COST_PRICING_USE_SDK`／`COST_PRICING_SDK_TIMEOUT`／`COST_PRICING_OFFER_READ_TIMEOUT`／`COST_PRICING_AGENT`／`COST_PRICING_AGENT_SKIP_LLM`／`GCP_BILLING_API_KEY` 這些讀取點時，六個設定檔必須一起改：`backend/.env.example`（94-124 行）、`deploy/.env.example`、`deploy/render-env.sh:92`、`deploy/docker-compose.deploy.yml:57`、`deploy/docker-compose.test.yml:40`、`.github/workflows/deploy.yml:101,201`。
4. **DDL 雙軌**：`backend/database.py::_ensure_cost_schema()`（329-395 行）與 `schema_rbac.sql:169-212`，加上 `DEPLOY.md:219-238` 的資料表對照表——`project.md` 的 schema↔deploy 同步是 **blocking** 規則。
5. **RBAC seed**：`backend/services/rbac_seed_data.py` 的 5 組 story id——`C1`、`C1h`、`C1r`、`C1b`、`C1o`（各 11 列）。程式實際使用 `C1.view` 與 `C1h`／`C1r`／`C1o` 的 `edit`；**`C1b` 已在 seed 裡但無任何程式引用**（B2 budget 遺留）。
6. **前端入口**：`frontend/src/App.tsx:24` 的根導向 `if (can('C1','view')) → /cost`，以及 `Sidebar.tsx:201` 的 `NavLink to="/cost"`。移除成本頁會改變所有 FinOps 角色登入後的落地頁。
7. **契約衍生物**：`openapi.json` 與 `frontend/src/types/api.d.ts`（2,751 行）。改動 9 個端點必須在同一 PR 重跑 dump 與 `gen:types`，否則兩道 drift 閘門都紅。
8. **測試**：17 支 C1 後端測試檔，加上 `frontend/tests/e2e/regression.spec.ts` 第 492 行起的成本頁回歸（依賴 test stack 內嵌的 `COST_PRICING_STUB=1` 與 `$86.40 / 月` 硬編碼期望值）。

## `pricing_client.py` 的最小存活集合

若決定保留 `pricing_client` 作為 agent 按需查價的 Port，以下 **8 個檔案必須一併保留**（比表面看起來多）：

`config.py` + 其 9 份 YAML（尤其 `pricing_urls.yaml` 307 行、`pricing_coverage.yaml`、`aws_region_locations.yaml`、`supported_regions.yaml`）、`pricing_units.py`、`pricing_offer_parser.py`、`pricing_gcp.py`、`pricing_azure.py`。

若要刪 `pricing_sdk.py`（唯一的 boto3 使用者），必須改寫 `pricing_client.py:20` 與 `:280-283` 的 `use_sdk_enabled()` 分支；`tests/test_pricing_client.py:73-74` 正好 patch 這兩個符號。

## 外部套件的共用關係

| 套件 | cost 消費者 | 非 cost 消費者 | 可否隨 C1 移除 |
|---|---|---|---|
| `claude-agent-sdk` | `cost_pricing_agent` | `services/design_agent.py`、`services/review_agent.py`、`services/wa_lens_engine.py` | **不可**（連帶 Dockerfile 的 Node 22 與 `@anthropic-ai/claude-code` 也不可拿掉） |
| `boto3` | `pricing_sdk` | 無 | 可（全 repo 唯一使用者） |
| `playwright` | `azure_calculator_runner`、`gcp_calculator_runner` | 前端 e2e 用的是獨立的 `@playwright/test` | Python 端可隨 Calculator 路徑移除 |
| `httpx` | `pricing_client` 家族 | `review_router`、`llm_provider` | 不可 |
| `PyYAML` | `cost/config.py` | 未見其他消費者 | 視 `config.py` 去留而定 |

## 建置期相依

| 產物 | 來源 | 守門 |
|---|---|---|
| `openapi.json` | `backend/scripts/dump_openapi.py` | CI backend job `--check` |
| `frontend/src/types/api.d.ts` | `openapi.json` → `npm run gen:types` | CI frontend job `npm run check:types` |
| `deploy/.env` | `deploy/render-env.sh` | `validate_env_contract.py` 禁止 workflow 繞過 |
| DB 初始 schema | `schema_rbac.sql`（initdb 掛載） | **僅空 volume 生效**；既有環境靠 `_ensure_*_schema()` |
