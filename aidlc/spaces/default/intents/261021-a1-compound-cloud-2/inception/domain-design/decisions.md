# Architecture Decision Records (ADRs) — A1 混合雲繪圖功能

> Stage: domain-design (2.6) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [requirements](../requirements-analysis/requirements.md)
> - [stories](../user-stories/stories.md)
> - [architecture](../../../codekb/cloud-360/architecture.md)
> - [component-inventory](../../../codekb/cloud-360/component-inventory.md)
> - [team-practices](../practices-discovery/team-practices.md)
> - [components](components.md)

---

## 1. 架構決策記錄總覽 (ADR Register)

| ADR 編號 | 決策標題 | 狀態 | 核心關聯元件 |
| :--- | :--- | :--- | :--- |
| **ADR-001** | 混合雲 4 大領域元件邊界切分與單向無環依賴 | **Accepted** | 全部元件 |
| **ADR-002** | 圖示查詢外部 I/O 隔離與本地灰底向量 SVG 容錯架構 | **Accepted** | `CompoundDiagramBuilderComponent`, `IconServiceGatewayComponent` |
| **ADR-003** | 混合雲視覺樣式、幾何座標與協議字串之常數模組化宣告 | **Accepted** | `CompoundDiagramBuilderComponent`, `WorkspaceCanvasToolbarComponent` |

---

## 2. ADR-001: 混合雲 4 大領域元件邊界切分與單向無環依賴

### Context (背景脈絡)
混合雲繪圖功能橫跨使用者介面（React）、AI 代理人協調（FastAPI / LangChain Tool）、空間幾何組裝（mxGraph XML）與外部第三方服務通訊（n8n Webhook）。若缺乏嚴格的邏輯邊界，容易導致前端與後端狀態脫節、幾何運算與網路 I/O 混雜，使得單元測試必須啟動真實 HTTP 伺服器，進而大幅增加系統脆弱性。

### Decision (決策內容)
將混合雲功能嚴格切分為 4 個獨立領域元件：
1. `WorkspaceCanvasToolbarComponent`（前端 UI 互動與視角）
2. `DesignAgentComponent`（AI 代理人與提示詞指引）
3. `CompoundDiagramBuilderComponent`（純無狀態幾何佈局與 XML 生成）
4. `IconServiceGatewayComponent`（外部圖示 HTTP 通訊與降級）
依賴關係嚴格維持單向無環：`UI -> Agent -> Builder -> Gateway`。

### Consequences (決策後果)
- **正面影響 (Positive)**：
  - `CompoundDiagramBuilderComponent` 成為純函式幾何引擎，無任何網路或資料庫依賴，可在毫秒級別進行 100% 自動化單元測試。
  - Prompt 調優與幾何算法生命週期完全解耦，維護風險降低。
- **負面影響 (Negative)**：
  - 需要在 `DesignAgentComponent` 與 `CompoundDiagramBuilderComponent` 之間定義明確的中介資料合約 (`AgentToolCallRequest`)。

### Alternatives Rejected (排除之替代方案)
- **方案 A（巨型一體化 Builder）**：將 n8n 圖示發送與 Agent Prompt 解析直接寫在 `diagram_builder.py` 函式內部。
  - *排除原因*：造成幾何計算與網路 I/O 嚴重耦合，單元測試極難 Mock，違反單一職責原則。

---

## 3. ADR-002: 圖示查詢外部 I/O 隔離與本地灰底向量 SVG 容錯架構

### Context (背景脈絡)
外部 n8n 圖示微服務為第三方依賴，可能遭遇網路延遲、服務抖動或無對應圖示。若圖示服務請求掛起超過 10 秒，將直接癱瘓後端 Worker 執行緒並導致前端逾時報錯。

### Decision (決策內容)
1. 建立獨立的 `IconServiceGatewayComponent`，統一管理 `fetch_icon_from_n8n()`。
2. 請求上行參數唯一指定 `provider = "compound"`，單次呼叫嚴格設置 `timeout = 5.0` 秒。
3. 一旦遭遇逾時或 HTTP 狀態碼非 200，立刻於本地記憶體動態合成包含服務名稱縮寫之 40x40 灰底文字向量 SVG（`#F1F5F9` 底色 + `#475569` 字體），絕不拋出阻斷式例外。

### Consequences (決策後果)
- **正面影響 (Positive)**：
  - 產圖流程可用性達 99.99%，外部微服務停擺時依然能完整輸出三雲架構圖與直角連線。
  - 符合 NFR1（總體產圖耗時不超過 8.0 秒）與 NFR5（零新外部依賴）。
- **負面影響 (Negative)**：
  - 降級狀態下的節點圖示為灰底文字方塊，視覺上不如官方彩色向量圖標豐富，需於日誌記錄 Warning。

### Alternatives Rejected (排除之替代方案)
- **方案 A（前端直連 n8n）**：由前端瀏覽器發起對 n8n 的圖示抓取。
  - *排除原因*：直接暴露內部 Webhook URL，且面臨跨來源資源共享 (CORS) 與瀏覽器網路不穩定限制。
- **方案 B（圖示失敗時留空）**：若 n8n 失敗則節點不繪製任何圖示。
  - *排除原因*：在 Draw.io 畫布上會呈現無圖標空盒，破壞拓撲視覺美感與辨識度。

---

## 4. ADR-003: 混合雲視覺樣式、幾何座標與協議字串之常數模組化宣告

### Context (背景脈絡)
依據 Refined Mockups 階段之審查建議 R-02，三雲色彩樣式（`GROUP_STYLES`）、Hub-and-Spoke 尺寸（480px / 360px / 120px）以及跨雲連線協議清單若硬編碼 (Hardcode) 於各個函式中，容易在後續多雲擴充時產生不一致與樣式漂移。

### Decision (決策內容)
在後端領域中將所有混合雲設計與幾何參數收斂為專屬常數：
1. **尺寸常數**：`AWS_HUB_WIDTH = 480`、`WING_CLOUD_WIDTH = 360`、`CORRIDOR_SPACER_WIDTH = 120`。
2. **連線路由**：`CROSS_CLOUD_EDGE_STYLE = "orthogonalEdgeStyle"`。
3. **協議清單**：宣告標準協議列舉 `SUPPORTED_PROTOCOLS = ["Direct Connect", "ExpressRoute", "Cloud Interconnect", "VPN Tunnel", "HTTPS API"]`。
4. **色彩對齊**：直接映射並沿用既有 `GROUP_STYLES` 中的 `aws_cloud`、`azure_cloud` 與 `gcp_cloud`。

### Consequences (決策後果)
- **正面影響 (Positive)**：
  - 未來調整緩衝走廊或容器加寬時，僅需修改頂部常數，全局幾何運算自動重繪。
  - 符合 Clean Code 與開放封閉原則 (OCP)。
- **負面影響 (Negative)**：
  - 初期需建立與重構常數宣告模組。

### Alternatives Rejected (排除之替代方案)
- **方案 A（動態讀取外部配置檔）**：將尺寸與顏色寫入外部 JSON/YAML 設定檔。
  - *排除原因*：過度工程化，幾何與渲染樣式屬核心業務契約，以 Python 內建常數維護更為精準且具編譯期保護。

