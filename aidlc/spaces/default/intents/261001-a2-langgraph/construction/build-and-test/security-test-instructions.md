# Security Test Instructions

> Minimal；安全面以既有單元斷言 + ADR-0006 判定為主。

本階段驗證：
- 應用程式碼零 `ClaudeSDKClient`（`test_a3_langgraph_migration`）
- 錯誤路徑不洩漏 API key（`test_langgraph_runtime` secret redaction + auth_error_message）
- Dockerfile 移除 CLI 攻擊面

**不新增**獨立 SAST／DAST 指令；repo-contract 仍由 CI 執行。
