# Unit Test Instructions — cost-advice-agent（U7）

```bash
cd backend && python3.13 -m unittest tests.test_cost_advice_agent tests.test_estimate_intake_api -v
```

Mock：`invoke_graph`／`fetch_hourly`／OpenRouter。禁止 CI 真金鑰。
