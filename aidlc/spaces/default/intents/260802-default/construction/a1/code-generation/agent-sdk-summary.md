# A1 Agent SDK Implementation Summary

### 結果

A1 已改為 **Anthropic Agent SDK（`claude-agent-sdk`）+ OpenRouter**。畫圖邏輯（文字座標指南、`groups/nodes/edges`、n8n icon、`mxGraphModel`、SSE 契約）維持不變。

### 模組

| 檔案 | 說明 |
|---|---|
| `backend/services/design_agent.py` | Agent SDK、OpenRouter env 映射、MCP tool |
| `backend/services/diagram_builder.py` | 巢狀座標 + n8n + XML |
| `backend/services/agent_router.py` | JWT + SSE 適配層 |
| `backend/prompts/aws_architecture_system_prompt.md` | system prompt |

### 環境

```bash
OPENROUTER_API_KEY=...
ANTHROPIC_BASE_URL=https://openrouter.ai/api
ANTHROPIC_AUTH_TOKEN=   # 可由 OPENROUTER_API_KEY 自動映射
ANTHROPIC_API_KEY=      # 必須為空
```

### 安全

`allowed_tools` 僅 `mcp__cloud360-design__draw_architecture_diagram`；禁用 Bash/Read/Write/Edit。

### 手動驗收

1. 設定 `.env` 後重啟 backend  
2. alex 登入 → 明確產圖需求 → 畫布出現 XML  
3. 局部修改（帶 current_xml）  
4. A2 存檔／分享／WS
