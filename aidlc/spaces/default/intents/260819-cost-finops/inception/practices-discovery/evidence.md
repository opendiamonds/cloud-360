# 查證證據（Evidence）

> practices-discovery 產物｜intent `260819-cost-finops`｜HEAD `c3de2c8`｜2026-08-19
>
> 記錄本輪 practices-discovery 查閱的來源，以及從 codekb C1 overlay 識別的 gap。

---

## 查閱來源清單

| 來源 | 路徑 | 用途 |
|---|---|---|
| 團隊規則層 | `aidlc/spaces/default/memory/team.md` | 五個 H2 基線（Branch、Commit、Skeleton、Testing、Deployment、Code Style）|
| 專案規則層 | `aidlc/spaces/default/memory/project.md` | Testing Posture（PBT hard constraint）、Deployment（ADR-0007/0008）、Mandated（schema sync、env contract、security）、Corrections |
| 程式碼品質評估 | `aidlc/spaces/default/codekb/cloud/code-quality-assessment.md` | HEAD `c3de2c8` 測試現況、C1 新 hotspot、A1/A3 已關閉債項 |
| 技術棧 | `aidlc/spaces/default/codekb/cloud/technology-stack.md` | 套件版本、Pin 狀態、C1 相關技術缺席清單 |
| 相依關係 | `aidlc/spaces/default/codekb/cloud/dependencies.md` | 外部相依、C1 假相依風險（COST-* vs TCO）、測試相依現況 |
| 系統架構 | `aidlc/spaces/default/codekb/cloud/architecture.md` | 架構風格、C1 缺席 bounded context、現況 vs 意圖路徑對比圖 |
| 程式碼結構 | `aidlc/spaces/default/codekb/cloud/code-structure.md` | 模組分類、ABSENT 搜尋結果（0 個 `*cost*` 檔）、Frontend 頁面清單 |
| CI workflow | `.github/workflows/ci.yml`（head 查閱） | 管線 job 順序、OpenAPI drift 檢查確認、觸發條件、concurrency |
| 業務概覽 | `aidlc/spaces/default/codekb/cloud/business-overview.md` | 專案定位、C 支柱（FinOps）描述 |

---

## 訪談定案紀錄（2026-08-19 Final Integration）

| 問題 | 答案 | 定案內容 | 寫入位置 |
|---|---|---|---|
| Q1（Walking Skeleton） | A | 本 intent 維持 `skeleton: off`；C1 雖屬 greenfield，無需額外 skeleton gate | `team-practices.md ## Walking Skeleton` |
| Q2（計價 API 限制） | A | 只准公開免帳號計價端點；禁止 Cost Explorer／Billing API／雲端帳號憑證 | `discovered-rules.md ## Forbidden ## C1 計價 API`；`team-practices.md` 交叉參照 |
| Q3（C1 HTTP 最小授權測試） | A | 即使 RBAC seed 不變，第一個 C1 HTTP 消費者須有 allow/deny（含 403）TestClient | `discovered-rules.md ## Mandated`；`team-practices.md ## Testing Posture` |
| Q4（C1 三層架構與 calculator 純函式約束） | A | 三層 `cost_router` → `cost_service` → `cost_calculator` + `pricing_client`；calculator 禁止 httpx/DB/HTTPException | `discovered-rules.md ## Mandated`；`team-practices.md ## Code Style` |

---

## C1 Overlay 識別的 Gap

以下為 reverse-engineering codekb overlay（HEAD `c3de2c8`）對 `260819-cost-finops` intent 識別的結構性缺口。這些是**證據紀錄**，不是新政策。對應的政策含義已依「既有規則的適用」記入 `team-practices.md` 與 `discovered-rules.md`。

### Gap 1：Cost Calculator 模組完全缺席（PBT 暫 N/A）

**觀察**：全 repo `*cost*`、`*calculator*`、`*pricing*`、`*tco*`、`*finops*` 文件搜尋結果為 0 個 backend / frontend 執行時檔案。`backend/tests/` 無 `test_cost*`；`'C1'`／`"C1"` 在 tests 目錄 0 命中。

**政策含義**（既有規則，非新規則）：`project.md ## Testing Posture` 的 ADR-0006 PBT hard constraint 要求 cost calculator 使用 Hypothesis。模組不存在時，約束為 N/A。模組一旦建立（本 intent 或後續 intent），PBT 約束立即由 N/A 轉為 blocking。

**勿混淆**：`wa_rule_engine.py` 的 `COST-*` findings（`COST-OVERSIZE-HINT`、`COST-NO-LIFECYCLE`、`COST-NAT-HINT`、`GCP-COST-NO-COMMIT`、`AZ-COST-NO-COMMIT`）是關鍵字啟發式，無金額、無 SKU、連 example-based 測試都沒有——不是任何意義下的 cost calculator。

---

### Gap 2：HTTP 層 TestClient 僅一例（無 Cost Router 可測）

**觀察**：HEAD `c3de2c8` 的 `backend/tests/test_user_list_endpoint.py` 用 `starlette.testclient.TestClient` 測 `/api/auth/list` 分頁欄位，是全 repo **唯一** TestClient 使用例（`test_user_list_endpoint.py` 為 2026-08-06 以後引入的新增檔，此前「零 HTTP 層測試」記載已過時）。無任何 cost router、cost endpoint 或 C1 相關 HTTP 測試。

**政策含義**（既有規則 B）：`team.md Testing Posture` 的 B 規則要求新增 HTTP 端點時補 `TestClient` 測試。本 intent 若新增 `/api/cost*` router，須仿 `test_user_list_endpoint.py` 的形狀補測試。`get_db` 與 `get_current_user` 可用 `app.dependency_overrides` 覆寫，不需真實 DB。

---

### Gap 3：RBAC Seed 領先執行期（C1 種子存在但無 router 守衛）

**觀察**：
- `backend/services/rbac_seed_data.py` 含 `FinOps_Analyst` 角色與 C1 相關 seed 欄位。
- `RolePermissionsPage.tsx` 已顯示 C1 欄（「C1 TCO 與流量預算」）。
- `App.tsx` 無 `/cost` 路由；`CapabilityRoute` 從未以 C1 守衛任何頁面；`backend/services/` 無 `cost_router.py`。
- `test_rbac.py` 不覆蓋 C1 permission（`'C1'`、`"C1"` 在 tests 0 命中）。

**政策含義**（既有規則 A）：若本 intent 修改 C1 相關 `role_permissions` 預設值（例如讓 `Architecture_Lead` 取得 C1 view 或 edit），屬 `team.md` A 規則的觸發條件，須補 allow/deny 雙向測試。RBAC seed 領先實作是已知現況，不是 bug，但文件與設計必須標明「種子領先實作」，不得把 seed 存在當成 router 或頁面已實作的證據。

---

### Gap 4：Frontend Cost 頁面完全缺席（e2e 須從零建）

**觀察**：
- `frontend/src/pages/` 目前 8 個頁面：Login、Forbidden、WaitingApproval、Workspace、Assessment、Admin、AuthorizationRequests、RolePermissions——無 `CostPage.tsx`。
- `frontend/tests/e2e/regression.spec.ts`：現有 case 涵蓋登入、RBAC Sidebar 可視性、Admin 最後活動與分頁，**無成本頁 e2e**。
- `Sidebar.tsx`：可收合，已有「架構」與「系統管理」兩組，**無 C / FinOps 組**。

**政策含義**（既有規則 C）：若本 intent 新建 `CostPage.tsx`，資料形狀為全新，須補至少一個 Playwright case 斷言頁面可到達且核心欄位可見。若新增 Sidebar C 組入口，斷言入口可見。Playwright 是目前**唯一**能碰到前端頁面的自動化層（frontend 無 unit test runner）。

---

### Gap 5：無 Inbox / Budget / Overspend Primitive

**觀察**：全 repo 無 inbox、notification、budget、overspend 相關模組、表、或 API（`architecture.md` C1 現況 vs 意圖對比圖明確標示「ABSENT: cost calculator / pricing client / Cost page」；`dependencies.md` 確認「無 inbox／budget／overspend primitive」）。

**政策含義**（既有規則）：若本 intent 新增 budget／cost 表，即觸發 `project.md ## Mandated` 的 schema 同步規則（`schema_rbac.sql`、`DEPLOY.md`、`database.py` `_ensure_*`）。目前無增量義務（HEAD 無 C1 DDL）。

---

### Gap 6：OpenAPI Drift 檢查（C1 新端點的 CI 影響）

**觀察**：`ci.yml` 在 `c3de2c8` 後新增 OpenAPI spec drift 檢查 job（`backend/scripts/dump_openapi.py --check`），在 frontend build 與 backend unittest 之間執行。若後端新增 `/api/cost*` 端點但未重新 dump `openapi.json`，CI 即紅燈。

**政策含義**（既有規則）：C1 新增 HTTP 端點的 PR 必須在同一個 commit 重跑 `python backend/scripts/dump_openapi.py` 並提交更新後的 `openapi.json`。搭配 `npm run gen:types`（`openapi-typescript`）更新 `frontend/src/types/api.d.ts`，縮窄前後端型別缺口。

---

## 查證結果：不構成新規則的條目

下列觀察在查證中出現，但不構成新的團隊規則，附說明以利後續 practices-promote 時判斷：

- **`tsc -b` 不保護前後端 schema 一致性**：`AdminPage.tsx` 的 `DbUser` 是手寫 interface，`fetchUserList` 的回傳型別為 `any`，`tsc -b` 對「後端加欄、前端漏接」無效。這是**已知機制缺口**（已在 `team.md Deployment` 如實記載），非新發現。OpenAPI drift 檢查部分補上此缺口，但手寫 interface 仍可繞過。
- **WA `COST-*` findings 無測試**：5 個 COST findings code 定義於 `wa_rule_engine.py`，連 example-based 測試都沒有。這是 A3 技術債，非 C1 責任範圍，記為現況紀錄。若 C1 引入新的 cost analysis 路徑，不得依賴 WA findings 作為計算輸入。
- **FastAPI 0.141.1 + Pydantic 2.13.4 精確釘選**：這是 OpenAPI dump 位元決定性的要求（`technology-stack.md`）。升版時必須在同一個 PR 重 dump `openapi.json` 並重產前端型別。本 intent 不觸及此。
