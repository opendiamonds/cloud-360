# NFR Requirements Questionnaire — U3: u3-design-agent-compound

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (NFR1, NFR2, NFR4)

---

## 1. 單元非功能需求邊界說明 (NFR Scope for Service Unit)

依據 `produces_kinds`，`u3-design-agent-compound` 作為 `service` 單元，需要完整評估：
1. **Performance**: SSE 事件首字延遲 $\le 1.0\text{s}$。
2. **Security**: RBAC `A1.edit` 授權檢驗與 Prompt 注入防護。
3. **Scalability**: FastAPI 非同步事件串流與高並發支援。
4. **Reliability**: LLM 輸出 JSON 格式錯誤自動重試 (Max 1 次)。
5. **Observability**: 記錄包含 `session_id`、`provider="compound"` 與耗時之結構化日誌。
6. **Tech Stack**: 採用 FastAPI, Pydantic, Python 3.11。

---

## 2. 非功能性需求關鍵問卷 (Clarifying Questions)

### Q1. LLM 輸出格式失敗之容錯機制 (LLM Parsing Fault Tolerance)
當 LLM 回傳之 JSON 工具參數解析失敗時之處理策略為何？
- [A] **自動修正重試 1 次 (One-time Repair Retry)**：若首次 JSON 解析失敗，立即以修正提示詞重新呼叫模型 1 次；若依然失敗則優雅返回友善繁中錯誤說明，不中斷 SSE 串流。（推薦）
- [B] **不重試直接中斷**。

[Answer]: [A]

### Q2. 結構化日誌與追蹤識別碼 (Distributed Tracing & Logging)
在 SSE 串流過程中，日誌如何與前端 Session 關聯？
- [A] **帶入 `X-Session-ID` 與結構化標籤**：所有日誌均包含 `session_id`, `provider: "compound"`, `stage`，利於排查連線問題。（推薦）
- [B] **標準文字日誌**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出全套 Service NFR 產物前，請確認以下彙整摘要正確無誤：

- **容錯重試 (Q1)**: [A] JSON 解析失敗自動重試 1 次，超額優雅報錯。
- **可觀測性 (Q2)**: [A] 結構化日誌帶入 `session_id` 與 `provider: compound`。

Does this all look correct before I generate the NFR requirements artifacts for U3?
- Looks correct
- Request changes

[Answer]: Looks correct
