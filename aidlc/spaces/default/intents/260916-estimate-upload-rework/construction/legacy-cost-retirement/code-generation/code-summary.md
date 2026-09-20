# Code Summary — legacy-cost-retirement（U3）

> Unit: `legacy-cost-retirement` · kind: **service**（退場）  
> 計畫：同目錄 `code-generation-plan.md`（6 步，全數完成）  
> Plan Approval：`Approve Plan`（session `cursor-dda1653e-8198-4f07-9792-97a2d6a7d904`；fingerprint `sha256:9c9b3b71…957a`）

## 變更檔案（摘要）

| 檔案／群組 | 變更 | 對應 |
|---|---|---|
| `backend/main.py`、`cost_router.py` 等 | 取消掛載並刪除舊 diagrams HTTP／service／agent | Step 1、FR9.1 |
| `database.py`、`schema_rbac.sql`、`DEPLOY.md` | 四表 rename → `archive_*`；保留期 ≥90 天（最早 DROP 不早於 2026-12-18） | Step 2、FR9.2 |
| Calculator runners／YAML／`playwright`／spikes | 整包刪除；`requirements.txt` 無 playwright | Step 3、FR9.3 |
| warm cache、orphan prompt、e2e、`openapi.json`／`api.d.ts` | 刪／改／重產 | Step 4、FR9.7–9.11 |
| `.env.example`、compose test、`COST_PRICING_STUB` | 舊 stub／calculator env 減項；U4 憑證保留 | Step 5、FR9.8 |
| `test_legacy_cost_retirement.py` | 6 案：404、存活 import、無 archive ORM、無 playwright、e2e 無 `$86.40` | Step 6 |

**刻意保留（U5）**：`pricing_sdk`／`pricing_client`／`config`＋定價 YAML／`pricing_units`／offer／gcp／azure／query_parser 與對應測試。

**刻意未改（U8）**：`CostPage.tsx` 仍呼叫舊路徑（已知壞）；僅修編譯錯誤 `setExportReady`；**不得單獨合進 `ut`／部署**。

## 關鍵實作決定

1. **HTTP**：舊 `/api/cost/diagrams*` 整包消失（OpenAPI 已無 `/api/cost`）；不新增 v1 stub。
2. **表**：啟動時 `ALTER … RENAME TO archive_*`；應用零讀寫；物理 DROP 另開 chore。
3. **查價**：移除 `COST_PRICING_STUB` 捷徑與 Postgres `pricing_cache` 寫入語意；存活 Port 走 SDK／Bulk／Catalog／Retail。
4. **合併閘門**：`DEPLOY.md` 檢查清單明示須與 U8 同批。

## 測試

| 指令 | 結果 |
|---|---|
| `cd backend && PYTHONPATH=. python3 -m unittest discover -s tests -v` | **315 OK** |
| `python3 scripts/validate_repo_contract.py` | exit 0 |
| `python3 scripts/validate_env_contract.py` | exit 0 |
| `python3 scripts/validate_cost_calculator_boundary.py` | exit 0 |
| `dump_openapi.py --check`／`npm run check:types`／`tsc -b` | 通過 |

## 與計畫的偏離

- `CostPage.tsx` 最小編譯修補（刪無效 `setExportReady`）— 屬讓 CI `tsc` 綠，非 U8 功能改寫。
- Calculator 相關 YAML／`sku_map` 一併刪（僅被已刪模組載入）。

## 不做（交其他 unit）

新 `/api/cost/v1`（U2）、新 Cost UI（U8）、查價強化（U5）、DROP `archive_*`、TCMS 手寫。

## PR 檢查清單（合併閘門）

- [ ] **須與 U8 同批**合併／部署；本 unit **單獨不合** `ut`
- [ ] staging 確認四表為 `archive_*`、舊 diagrams API 404、新 UI 可用
