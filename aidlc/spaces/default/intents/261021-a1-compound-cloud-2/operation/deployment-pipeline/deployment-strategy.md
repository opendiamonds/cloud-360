# Deployment Strategy — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: deployment-pipeline (4.1) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 部署發布策略

- **部署模式**: **Rolling Update (滾動更新 / 容器即時重啟)**。
- **無狀態特性**:
  - 本次「畫混合雲」功能為純運算與視圖層擴充（`diagram_builder.py` 幾何組裝、`DrawioCanvas.tsx` 畫布渲染）。
  - 無資料庫 Schema 結構遷移或變更。
- **快取機制**:
  - 本地向量圖示快取 `_ICON_CACHE` 於後端啟動時初始化為記憶體字典，部署重啟自動清理，無跨版本髒資料殘留。
- **優雅降級**:
  - 當 n8n 圖示伺服器離線或回應逾時（> 5.0s）時，自動平滑降級為 40x40 灰底向量 SVG，維持服務 100% 可用性。

