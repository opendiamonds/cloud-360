# Security Test Instructions — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: build-and-test (3.6) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 安全與權限控制規範 (Security Baseline)

- **ADR-0006 授權防護**: 僅具備架構編輯權限（RBAC `A1.edit` / `can_edit=True`）之使用者能夠調用 Agent 觸發繪圖與產生架構圖 XML。
- **輸入邊界防禦**:
  - 防止 XML / SVG 惡意代碼注入（XSS / XXE）：圖示名稱、協定文字與雲端供應商標籤均需經由正規安全轉義。
  - n8n 圖示服務上行通訊隔離：禁止在 payload 中攜帶任何機敏憑證或金鑰。

---

## 2. 安全驗證測試指引

執行單元測試中的安全權限斷言：
```bash
PYTHONPATH=backend .venv/bin/python3 -m unittest backend.tests.test_design_agent.TestDesignAgentCompound.test_unauthorized_user_blocked_by_can_edit
```

### 驗收標準
- 當 `can_edit=False` 時，`draw_architecture_diagram` 立即返回防護阻擋訊息（`您目前僅具備檢視權限，無法變更或重新產生架構圖。`）。
- 繪圖模組完全不被調用，確保零未授權之圖形寫入操作。

