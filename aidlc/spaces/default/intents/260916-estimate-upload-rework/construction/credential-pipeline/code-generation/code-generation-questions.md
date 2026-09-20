# Code Generation — 釐清問題（credential-pipeline）

> Unit: （U4／B3）· packaging

## 計畫要點（供核可）

1. **ADR-0018 已 Accepted** — 開頭確認＋關閉 OQ7（regex 定案），不重寫 ADR。
2. **`validate_repo_contract.py`** — 值樣式偵測（AWS 40／GCP `AIza…`）；放行變數名。
3. **單元測試** — `backend/tests/test_repo_contract_secret_patterns.py`（含突變）。
4. **重建 AWS 傳遞** — `deploy.yml`／`render-env.sh`／compose；test 不注入密鑰。
5. **文件** — `DEPLOY.md`／`LOCAL-DEV.md`。

詳見 `code-generation-plan.md` 與 `unit-test-instructions.md`。

---

## Plan Approval

請核可上述計畫、內嵌 Testing Contract（test-after／Standard）、與 unit-test-instructions。

[Approval Fingerprint]: sha256:8bf90c83edebad3281c7d08be0ef65ed9879167d7c5f2c7fc3d4cce6eb6a5ec9

- Approve Plan — 依計畫實作
- Request Changes — 修改計畫後再核可

[Answer]: Approve Plan
