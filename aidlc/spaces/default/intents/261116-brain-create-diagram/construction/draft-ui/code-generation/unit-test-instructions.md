# Unit Test Instructions — U3 draft-ui

> 測試框架、mock 與測試資料的規則見 stage 層級的 `../../code-generation/unit-test-instructions.md`；本檔只列本單元的精確指令。

## 執行本單元的測試

```bash
cd frontend && npx playwright test tests/e2e/diagram-drafts.spec.ts && npm run lint && npm run build
```

- 本機 `python` 不在 PATH，後端一律用 `backend/.venv/bin/python`（CI 上的 `python` 即同一個直譯器）。
- 測試只用本機 SQLite 與替身，不連任何共享的資料庫或 Redis。
