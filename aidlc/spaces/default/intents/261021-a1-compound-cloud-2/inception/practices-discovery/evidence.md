# Evidence — Cloud-360 Practices Discovery

> Stage: practices-discovery (2.2) · Phase: Inception · Scope: feature
> 記錄本次實踐探索檢視之上游證據來源、查證事實驗證與代理人共識。

## 檢視之上游證據來源

- `aidlc/spaces/default/codekb/cloud-360/` — 包含架構圖 (architecture.md)、元件清單 (component-inventory.md) 與 API 規格。
- `backend/services/diagram_builder.py` — 檢視 `GROUP_STYLES` 樣式常數與 `fetch_icon_from_n8n` 實作。
- `backend/services/design_agent.py` — 檢視 `draw_architecture_diagram` tool 參數定義與權限邊界。
- `frontend/src/` — 檢視 WorkspacePage、ChatBox、DrawioCanvas 與前端型別檢查環境。
- `aidlc/spaces/default/memory/team.md`、`project.md` — 現有團隊與專案規範基準線。
- `contributions/` 三方代理人獨立查證：
  - `aidlc-quality-agent.md`
  - `aidlc-developer-agent.md`
  - `aidlc-devsecops-agent.md`

## 逐項查證與實作事實

| 領域 | 查證事實 | 依據來源 | 確定度 |
|---|---|---|---|
| **Way of Working** | 當前分支為 `doreen/feat/a1-compound-cloud-diagram`，符合 `<uploader>/<type>/<slug>` 慣例；PR 採 Bolt squash 與 feature merge 分流 | `git branch`、`team.md` | 高 |
| **Walking Skeleton** | 系統現有前後端、CI 閘門、CD 自動部署均成熟運作，本功能為既有模組擴充，`skeleton: off` 為最優選擇 | `team.md`、`ci.yml` | 高 |
| **Testing Posture** | 既有後端使用 `unittest` + `hypothesis`；本次功能需新增 `test_diagram_builder_compound.py` 專屬單元測試集 | `backend/tests/`、[Q:Contribution] | 高 |
| **Deployment** | 5 道 CI 閘門（含 OpenAPI drift 檢查）與 `192.168.10.10` 自動部署；本功能不增加新相依套件 | `ci.yml`、`deploy.yml` | 高 |
| **Code Style** | 後端 Python 3.11+ / PEP 8，幾何邏輯封裝於 `diagram_builder.py`；前端 React 18 + TS 嚴格型別 | codekb、[D:Contribution] | 高 |
| **Security** | A1 Design Agent 僅具備 `draw_architecture_diagram` 權限；n8n 請求帶有 5s 逾時與灰底 fallback | `design_agent.py`、[S:Contribution] | 高 |
