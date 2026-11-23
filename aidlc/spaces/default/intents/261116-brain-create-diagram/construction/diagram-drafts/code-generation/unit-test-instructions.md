# Unit Test Instructions — U1 diagram-drafts

> 測試框架、mock 與測試資料的規則見 stage 層級的 `../../code-generation/unit-test-instructions.md`；本檔只列本單元的精確指令。

## 執行本單元的測試

```bash
cd backend && .venv/bin/python -m unittest -v tests.test_diagram_drafts_schema tests.test_diagram_drafts_hierarchy tests.test_diagram_drafts_api tests.test_diagram_system_attach tests.test_work_orchestrator_store
```

- 本機 `python` 不在 PATH，後端一律用 `backend/.venv/bin/python`（CI 上的 `python` 即同一個直譯器）。
- 測試只用本機 SQLite 與替身，不連任何共享的資料庫或 Redis。
