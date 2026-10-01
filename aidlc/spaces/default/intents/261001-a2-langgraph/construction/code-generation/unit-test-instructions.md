# Unit Test Instructions — A3 LangGraph 迁徙

> Zero-Unit · Minimal · test-after · unittest（非 pytest）

## Runner readiness（Step 2 前必須可跑）

```bash
cd backend && python3 -m unittest tests.test_langgraph_runtime tests.test_review_agent tests.test_wa_lens_engine -v
```

## 本 unit 精確指令（實作完成後）

```bash
cd backend && python3 -m unittest \
  tests.test_langgraph_runtime \
  tests.test_review_agent \
  tests.test_wa_lens_engine \
  tests.test_a3_langgraph_migration \
  -v
```

結果（本輪）：25 tests，OK。

## 覆蓋目標（Minimal + FR5／BR5.1）

- Review 路徑 ≥1：經 `langgraph_runtime`／`openrouter_chat_model`，不 import `claude_agent_sdk`
- Lens 路徑 ≥1：同上；結構化答案形狀可被既有消費路徑使用
- 既有 `fallback_suggestions_from_findings`／lens heuristic／score 測試保持綠燈

## Mock／資料

- Mock：`openrouter_chat_model`、graph `ainvoke`／`astream`、或節點內 Chat 呼叫；禁止 CI 使用真實 `OPENROUTER_API_KEY`
- 不啟真實 DB（沿用 `tests/helpers.py` 既有策略，若測案觸及）

## 預期

- 上述 unit-scoped 指令 exit 0
- 全 suite 在 build-and-test 再跑；本階段至少 unit-scoped 綠燈
