# Quality Gates — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: ci-pipeline (3.7) · Phase: Construction · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 核心品質門檻 (Quality Gates)

在合併至 `ut` 整合主幹前，必須完全通過以下 4 道品質關卡：

### 關卡 1: 合約與安全防護 (Contract & Security Gate)
- **判定依據**: `scripts/validate_repo_contract.py`
- **門檻標準**:
  - 零 Production / Secret 檔案外洩。
  - 零硬編碼三雲憑證或私鑰。
  - 遵循 Conventional Commits 繁體中文 type 格式。

### 關卡 2: 後端單元與整合測試門檻 (Backend Unit & Integration Gate)
- **判定依據**: `test_diagram_builder_compound.py`, `test_design_agent.py`, `test_diagram_icons.py`
- **門檻標準**:
  - 測試成功率 100%（目前共 40 案例全數 PASS）。
  - Hub-and-Spoke 幾何佈局、直角折線、膠囊標籤渲染正確無誤。
  - n8n 圖示上行 payload 必須為 `provider="compound"`。
  - 圖示請求 5.0 秒逾時保護及 SVG fallback 機制 100% 覆蓋。
  - RBAC `can_edit=False` 權限阻擋攔截率 100%。

### 關卡 3: 前端建置與型別安全 (Frontend Build & Typecheck Gate)
- **判定依據**: `tsc -b && vite build`
- **門檻標準**:
  - TypeScript 零型別錯誤 (0 type errors)。
  - 打包建置零警告中斷 (0 build errors)。

### 關卡 4: 追溯性完整度 (Traceability Gate)
- **判定依據**: AIDLC Traceability Sensor
- **門檻標準**:
  - 需求條款 AC1.1.1 ～ AC4.2.3 覆蓋率 100%（Zero gaps, zero orphans）。

