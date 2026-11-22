# External Dependency Map — 外部依賴

> Stage: delivery-planning · Intent: `261105-d-iac-generation`

## 結論：無外部團隊閘；LLM／掃描 CLI 可 stub

沒有跨組織審批、沒有外部團隊交接窗、沒有必須等待的資料窗口。完成條件以可 stub 契約為準。

| 類別 | 本 intent | 判定 |
|---|---|---|
| 外部 API | OpenRouter（LLM） | **不擋** B1 合閘：agent 可 stub |
| 外部 CLI | IaC 靜態掃描工具（品牌未釘） | **不擋**：Scanner stub 友善；品牌∈契約 OQ |
| 資料 | 既有圖公開 API（`diagram_id`） | 無等待窗；缺公開包裝則圖域加最小端點（ADR-005） |
| 審批前置 | 無雲端 SM 寫入／無 platform apply | 無 |
| 外部團隊 | team-formation：無 PS／承包商 | 無 |

## 執行期外部呼叫（可降級）

| 項目 | 擁有者 | 前置期 | 擋住哪個 Bolt | 緩解 |
|---|---|---|---|---|
| OpenRouter | `langgraph_runtime`／環境變數 | 演示若要用真模型需本機／staging 密鑰（不進版控） | **不擋** B1／B2 合閘 | stub 圖／固定回應 |
| 掃描 CLI | U1 Scanner | 品牌未釘（契約 OQ） | **不擋** | stub findings 形狀 |
| 既有圖 list／get／upload | 圖域公開 API | 無 | 缺端點時擋選圖路徑 | 加最小公開包裝；禁挖 collab 私函 |

## 內部門控（非外部，記此對照）

| 門控 | 記於 |
|---|---|
| R-01／R-02 關閉 | `bolt-plan.md` B1 DoD |
| US6.1 成對 403／2xx | B1 DoD |
| HIGH／CRITICAL 下載確認在 UI | B2 DoD；API 不閘 |
| OpenAPI drift CI | B1／既有管線 |
