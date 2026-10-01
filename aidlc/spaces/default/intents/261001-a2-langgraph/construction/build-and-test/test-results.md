# Test Results — Build and Test

**Timestamp**: 2026-10-01T09:00:00Z（約）
**Python**: `backend/.venv`（3.13）

## Build

| Check | Command | Result |
|---|---|---|
| Import smoke | `backend/.venv/bin/python -c 'from main import app'` | **success** (`app_ok`) |
| Dockerfile CLI residual | `rg claude-code\|nodesource backend/Dockerfile` | **clean** |
| SDK residual（應用） | `rg ClaudeSDKClient backend --glob '*.py'` | 僅測試 assert 字串 |

## Unit tests（計畫義務）

```bash
cd backend && .venv/bin/python -m unittest \
  tests.test_langgraph_runtime \
  tests.test_review_agent \
  tests.test_wa_lens_engine \
  tests.test_a3_langgraph_migration \
  -v
```

- **Ran 25 · OK**

## Full backend suite（既有綠燈義務）

```bash
cd backend && .venv/bin/python -m unittest discover -s tests -v
```

- **Ran 375 · OK**

## Coverage

本 repo 無 coverage 量測工具；不以覆蓋率百分比作為本階段 Met／Not Met 依據。

## Target Verification Matrix（定稿）

見 `build-and-test-summary.md`。
