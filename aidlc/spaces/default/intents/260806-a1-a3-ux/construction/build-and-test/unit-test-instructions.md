# Unit Test Instructions — Minimal

> Strategy: **Minimal** · Upstream: `code-generation-plan.md` / `code-summary.md`

## Scope

本期要求驅動單元測試（已實作）：

| 需求 | 測試檔 |
|---|---|
| FR-GUARD | `backend/tests/test_prompt_guard.py` |
| FR-EDGE | `backend/tests/test_diagram_builder_edges.py` |
| 回歸 | 既有 `backend/tests/` 全套須維持綠色 |

## How to Run

```bash
cd backend
python3 -m unittest discover -s tests -q
# 定向
python3 -m unittest tests.test_prompt_guard tests.test_diagram_builder_edges -v
```

## Coverage Expectations（Minimal）

- 每項關鍵 FR 至少 happy-path＋1 個未命中／邊界
- 不強制 coverage % gate（與專案 CI 現況一致）

## Frontend

Minimal 策略不強制新增 React 單元測試；以 `tsc`／`lint`／`build` 與手動／既有 Playwright 回歸為輔。
