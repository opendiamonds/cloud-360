# Functional Design Questionnaire — U3: u3-design-agent-compound

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)
> 追溯上游基準：
> - [unit-of-work](../../../inception/units-generation/unit-of-work.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C3, C4)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR2.1~FR2.3, NFR4, CON3)
> - [stories](../../../inception/user-stories/stories.md) (US2.1, US2.2)

---

## 1. 單元實作職責與 Agent 介面說明 (Functional Scope & Agent Protocols)

本單元 `u3-design-agent-compound` 負責後端 AI Design Agent 與自然語言對話意圖之橋接：
- **主要檔案**: `backend/services/design_agent.py` 與 `backend/prompts/`
- **Tool 擴充**: `draw_architecture_diagram` 工具介面新增 `provider: Literal["AWS", "Azure", "GCP", "compound"] = "compound"`。
- **提示詞規範**: 注入多雲架構佈局規則（以核心雲居中、附屬雲分列兩側、連線標註金融/業務語義）。
- **權限防護**: 檢驗呼叫端具備 `A1.edit` RBAC 權限。

---

## 2. 功能細部設計關鍵問卷 (Clarifying Questions)

### Q1. 多雲意圖自動判斷門檻 (Multi-Cloud Intent Threshold)
當使用者輸入自然語言指令（如「畫一個跨 AWS 與 GCP 的雙活災備架構」）時，Agent 如何判定切換至 `compound`？
- [A] **關鍵字與實體聯合識別**：當使用者提示詞中同時出現 2 個（含）以上之雲端提供商關鍵字（AWS/Azure/GCP）或出現「混合雲/跨雲/多雲/hybrid/multi-cloud」時，自動標定 `provider="compound"`。（推薦）
- [B] **僅依據使用者明確指定**：必須使用者在 UI 明確勾選混合雲才啟用。

[Answer]: [A]

### Q2. RBAC 權限校驗失敗時之 Agent 反饋 (RBAC Failure Handling)
若未具備 `A1.edit` 權限的使用者發送繪製混合雲請求，Agent 如何處理？
- [A] **結構化錯誤反饋且不調用繪圖 Tool**：Agent 回傳清晰之繁體中文提示：「您目前僅具備唯讀權限，無法執行架構圖變更操作」，並終止 Tool 執行。（推薦）
- [B] **拋出 403 異常中斷連線**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `entities.md`、`rules.md`、`functional-spec.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **意圖識別 (Q1)**: [A] 出現 2 個以上雲商或混合雲關鍵字自動識別為 `compound` 模式。
- **權限防護 (Q2)**: [A] 嚴格校驗 `A1.edit`，權限不足時透過友好對話反饋阻擋 Tool 執行。

Does this all look correct before I generate the functional design artifacts for U3?
- Looks correct
- Request changes

[Answer]: Looks correct
