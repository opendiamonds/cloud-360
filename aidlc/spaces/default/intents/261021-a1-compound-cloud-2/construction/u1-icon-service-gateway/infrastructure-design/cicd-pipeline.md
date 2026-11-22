# CI/CD Pipeline — U1: u1-icon-service-gateway

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR3.1, NFR4.1, NFR5.1)

---

## 1. 構建與持續整合管線規範 (CI/CD Pipeline Specifications)

### 1.1 自動化測試作業 (CI Test Job)
- **環境**: Python 3.11 GitHub Actions Runner (`ubuntu-latest`)
- **前置**: 安裝既有依賴 `pip install -r backend/requirements.txt`
- **測試命令**: `pytest backend/tests/test_diagram_builder_compound.py -v`
- **覆蓋標的**:
  - `test_fetch_icon_n8n_success` (驗證 `provider="compound"`)
  - `test_fetch_icon_n8n_timeout_fallback` (驗證 5.0s 逾時後回傳 40x40 灰底 SVG)
  - `test_fetch_icon_n8n_404_fallback` (驗證異常狀態碼降級)
  - `test_fetch_icon_lru_cache` (驗證二次呼叫命中記憶體快取)

### 1.2 程式碼風格與型別校驗 (Linter & Type Checks)
- 執行 `black --check backend/` 與 `ruff check backend/`
- 執行 `mypy backend/services/diagram_builder.py` 確保 `Literal["compound"]` 型別健全

