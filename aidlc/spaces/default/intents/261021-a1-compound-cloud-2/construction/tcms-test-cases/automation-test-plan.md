# Automation Test Plan — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: tcms-test-cases (3.8) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 自動化測試架構

本功能的所有核心邏輯、幾何運算、通訊協議與權限防護均納入自動化測試套件（`backend/tests/`）：
1. **後端單元與整合測試**:
   - `test_diagram_builder_compound.py`: 驗證混合雲 XML 建置、Hub-and-Spoke 佈局計算、直角折線與純白膠囊標籤渲染、n8n compound 上行與 5.0 秒逾時 fallback。
   - `test_design_agent.py`: 驗證 Design Agent 之 `draw_architecture_diagram` 支援 `provider="compound"`、提示詞包含混合雲空間幾何規範、以及 RBAC `can_edit=False` 阻擋攔截。
   - `test_diagram_icons.py`: 驗證圖示服務快取與本地 SVG 產生機制。
2. **CI 整合與報表發布**:
   - 經由 `unittest` 執行，產出 JUnit XML 格式供 Kiwi TCMS 自動收集與歸檔。

---

## 2. 自動化測試執行統計

- **測試套件數**: 3 套件
- **總測試案例數**: 40 案例
- **當前通過率**: 100% (40/40 PASS)
- **平均執行時間**: 0.097 秒

