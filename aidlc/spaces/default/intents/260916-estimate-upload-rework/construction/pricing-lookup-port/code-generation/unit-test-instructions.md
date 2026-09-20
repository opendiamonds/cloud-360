# Unit Test Instructions — pricing-lookup-port（U5）

## Framework

- Python `unittest` + `unittest.mock`（repo 標準；不用 pytest）
- 本 unit **無** HTTP／DB／前端層

## Exact commands（僅本 unit）

```bash
cd backend && python -m unittest tests.test_pricing_client tests.test_pricing_sdk tests.test_pricing_gcp tests.test_pricing_azure tests.test_pricing_units -v
```

邊界腳本：

```bash
python3 scripts/validate_pricing_lookup_boundary.py
python3 scripts/validate_cost_calculator_boundary.py
```

## Coverage targets

- Standard：PricingLookup 行為 5–8 條以上（既有＋本 unit 補強）
- NFR9.1：至少一條密鑰遮罩／突變斷言
- BR5.7–5.8：邊界腳本 exit 0（含負向可選：暫存違規檔驗證失敗後還原）

## Mocking

- SDK：`patch` `fetch_hourly_via_sdk`／`use_sdk_enabled`
- Bulk：`patch` `_download_offer`
- **禁止** CI 注入真 AWS／GCP 金鑰

## Test data

- 既有 `backend/tests/fixtures/aws_ec2_offer_snippet.json`
- 假密鑰僅用於「不得出現在字串」斷言，不得寫入版控真值樣式賦值檔
