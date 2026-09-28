# Code Generation — 釐清問題（langgraph-runtime）

> Unit: `langgraph-runtime`（U6）· library

## 計畫要點（供核可）

1. **依賴** — `langgraph==1.2.11`、`langchain-openai==1.6.2`；保留 `claude-agent-sdk`
2. **OpenRouter 客戶** — `OPENROUTER_API_KEY`、base_url、預設模型／60s 逾時、`RuntimeAuthError`
3. **執行 API** — `invoke_graph`／`stream_graph`／`astream_graph`
4. **測試** — unittest mock＋選跑 smoke；CI 不打真 API
5. **交付物** — source-manifest／code-summary／traceability

詳見 `code-generation-plan.md` 與 `unit-test-instructions.md`。

---

## Plan Approval

請核可上述計畫、內嵌 Testing Contract（test-after／Standard）、與 unit-test-instructions。

[Approval Fingerprint]: sha256:28b07d593566c35dc10b158fd9bb1f515764e75abe0f93bae33d9d830219d859

- Approve Plan — 依計畫實作
- Request Changes — 修改計畫後再核可

[Answer]: Approve Plan
