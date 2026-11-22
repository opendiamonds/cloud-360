# Smoke Test Results — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: deployment-execution (4.3) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 冒煙測試執行結果

| 測試項目 | 驗測對象 | 預期結果 | 執行狀態 |
| :--- | :--- | :--- | :---: |
| **ST-01: 工作區導覽與選單載入** | `GET /workspace` | 頂部工具列出現「✨ 混合雲 (Compound)」選項 | ✅ PASS |
| **ST-02: 畫布 postMessage 通訊** | `DrawioCanvas.tsx` | 畫布初始化成功，支援 autoFit 與 triggerFitWindow 縮放 | ✅ PASS |
| **ST-03: 後端多雲幾何生成** | `build_compound_diagram_xml` | 產生正確包含 AWS、Azure、GCP 之 mxGraph XML | ✅ PASS |
| **ST-04: n8n 圖示上行協議與降級** | `fetch_icon_from_n8n` | 上行 payload `provider="compound"`，逾時自動降級本地 SVG | ✅ PASS |
| **ST-05: RBAC 權限攔截** | `can_edit=False` | 非授權使用者調用繪圖工具被即時攔截並提示 | ✅ PASS |

