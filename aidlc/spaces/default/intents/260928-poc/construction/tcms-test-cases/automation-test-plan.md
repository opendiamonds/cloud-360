# Automation Test Plan

## Bucket: To be automated
無。
這個 POC 中我們已經在 `code-generation` 與 `build-and-test` 階段撰寫並驗證了 `test_langgraph_migration.py`，因此目前的受測功能（LangGraph 初始化與 MemorySaver 驗證）已歸屬在「Already automated」清單中。

## Bucket: Already automated
- 行為：LangGraph state memory 能夠保留歷史 context。
- 自動化層級：Backend Unit / Behaviour (`unittest`)
- 測試檔案：`backend/tests/test_langgraph_migration.py`
- 執行指令：`cd backend && python3 -m unittest tests.test_langgraph_migration`
