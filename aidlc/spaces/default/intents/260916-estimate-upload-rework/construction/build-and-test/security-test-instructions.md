# Security Test Instructions — C1 估價上傳改版

> 對齊各 unit `nfr-requirements/security-requirements.md` 與 ADR-0006。

## 本機可執行

```bash
python3 scripts/validate_repo_contract.py
# 含：禁 path parts、禁 credential 字串、secret pattern（credential-pipeline）
cd backend && PYTHONPATH=. .venv/bin/python -m unittest tests.test_repo_contract_secret_patterns -v
cd backend && PYTHONPATH=. .venv/bin/python -m unittest tests.test_estimate_intake_api -v
# RBAC allow／deny 於 intake API tests
```

## 涵蓋

| 檢查 | 期望 |
|---|---|
| Repo contract secrets | exit 0 |
| Secret pattern mutation | unittest OK |
| Intake RBAC | 未授權 403；授權路徑 2xx／業務錯誤非 5xx |
| Credential 不明文入庫 | 見 credential-pipeline NFR／測試 |

## 延後

| 目標 | 擁有階段 |
|---|---|
| DAST／滲透 | performance-validation／operation |
| 正式雲端 IAM 稽核 | 範圍外（ADR-0001） |
