# Build and Test Summary — A3 LangGraph refactor

- Intent：`261001-a2-langgraph`
- Test Strategy：**Minimal** · Scope：**refactor** · Depth：**Minimal**
- 上游：`construction/code-generation/{code-generation-plan,unit-test-instructions,code-summary}.md`

## 建置狀態與前置

**建置就緒、測試就緒。** 使用 `backend/.venv` 安裝 `requirements.txt`（含 `langchain-openai`）。映像不再含 Claude CLI。

## 測試類型清單

| 類型 | 狀態 |
|---|---|
| Unit（code-generation 指令） | **已執行 · 25 OK** |
| Full discover | **已執行 · 375 OK** |
| Integration instructions | 產出為 Minimal 跳過說明 |
| Performance instructions | 跳過 |
| Security instructions | 產出為既有斷言說明（無獨立 SAST） |

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| T-UNIT-SCOPED | code-generation/unit-test-instructions.md | exit 0 · ≥25 tests | 25 OK | test-results.md | build-and-test | Met |
| T-FULL-SUITE | Testing Contract / refactor floor | existing suite green | 375 OK | test-results.md | build-and-test | Met |
| T-NO-SDK | FR4.1／BR1.1 | 應用無 ClaudeSDKClient | 僅測試 assert | rg + migration tests | build-and-test | Met |
| T-NO-CLI-IMAGE | FR4.2／BR4.1 | Dockerfile 無 claude-code／Node | clean | Dockerfile | build-and-test | Met |
| T-IMPORT-SMOKE | build-instructions.md | `from main import app` | app_ok | test-results.md | build-and-test | Met |
| T-REVIEW-STREAM | FR5.1／BR5.1 | Review mock 串流測試 | pass | test_a3_langgraph_migration | build-and-test | Met |
| T-LENS-SHAPE | FR5.2／BR5.1 | Lens 結構化答案測試 | pass | test_a3_langgraph_migration | build-and-test | Met |
| T-SECRET-REDACT | NFR2.1／BR3.2 | 錯誤不含 API key | pass | test_langgraph_runtime | build-and-test | Met |

## 就緒評估

| 面向 | 狀態 |
|---|---|
| build-ready | 是 |
| test-ready | 是 |
| deployment-ready | 是（後續 deployment-pipeline／execution；TCMS 仍為下一 EXECUTE） |

## 已知限制

- 真 LLM／OpenRouter 端到端未在本機跑（單元 mock）；需 `OPENROUTER_API_KEY` 的手動冒煙可在部署後做。
- 前端零變更，未跑 Playwright（BR2.2）。
