# Code Summary — pricing-lookup-port（U5）

> Unit: `pricing-lookup-port` · kind: **library**  
> 計畫：同目錄 `code-generation-plan.md`（5 步，全數完成）  
> Plan Approval：`Approve Plan`（fingerprint `sha256:7b6c11970013b8e6f5494792462e92daae3cfaafe36e1d0e04bc175fc6804666`）

## 變更檔案

| 檔案 | 變更 | 對應 |
|---|---|---|
| `backend/cost/pricing_client.py` | docstring 標 PricingLookup／AH-6／無 DB 快取寫入 | Step 1 |
| `backend/cost/pricing_sdk.py` | SDK 失敗 log 僅 error code（NFR9.1） | Step 1／3 |
| `scripts/validate_pricing_lookup_boundary.py` | **新增** intake 禁 import＋禁 Port 外 host 字面 | Step 2 |
| `.github/workflows/ci.yml` | 掛邊界腳本步驟 | Step 2 |
| `backend/tests/test_pricing_client.py` | unsupported／降級／密鑰遮罩／快取無憑證 | Step 3 |

**確認未重建**：Postgres `pricing_cache`；`warm_aws_pricing_cache.py`／`price_cache.py` 維持 U3 刪除。

## 關鍵實作決定

1. **Brownfield**：既有 `fetch_hourly` 鏈路保留；本 unit 加固邊界與密鑰面。
2. **邊界 CI**：intake 四模組 AST／regex 禁 `pricing_client`／`pricing_sdk`；`backend/` 非存活集禁 allowlist host 字串（tests 豁免）。
3. **SDK log**：`ClientError` 只記 `Error.Code`，不記完整 exception 字串。

## 測試

| 指令 | 結果 |
|---|---|
| `cd backend && python3.13 -m unittest tests.test_pricing_client tests.test_pricing_sdk -v` | 16 OK |
| `python3 scripts/validate_pricing_lookup_boundary.py` | exit 0 |
| `python3 scripts/validate_cost_calculator_boundary.py` | exit 0 |

## 與計畫的偏離

無實質偏離。未另建 warm 腳本（U3 已刪；BR5.10 以刪除滿足）。

## 不做（交其他 unit）

建議正文／SSE（U7）、SPA（U8／U9）、TCMS 手寫。
