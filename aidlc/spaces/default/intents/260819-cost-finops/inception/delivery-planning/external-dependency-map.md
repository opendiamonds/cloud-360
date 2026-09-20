# External Dependency Map — 外部依賴

> Stage: delivery-planning（Inception 2.8）· Intent: `260819-cost-finops`
> 上游：`requirements.md`、`stories.md`、`mockups.md`、`components.md`、`unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`、`team-practices.md`。

## 結論：無外部團隊閘；價目為可 stub 的執行期 Port

Q5=A。沒有跨組織審批、沒有外部團隊交接、沒有資料窗口要等。

| 類別 | 本 intent | 判定 |
|---|---|---|
| 外部 API | 公開免帳號雲價目（`pricing_client`）。禁止 Cost Explorer／帳單憑證（`requirements.md` FR-2.5） | **不擋 B1 完成**：stub 即可合 TestClient／e2e。真實 URL = infrastructure-design OQ-3 |
| 資料可得性 | 列來自既有 `user_diagrams` XML；價目可 Miss／Unsupported | 無等待窗 |
| 審批前置期 | 無 FinOps 價目核准流（Won't Have）；production 雲帳號 out of scope | 無 |
| 外部團隊交接 | 1.5 SKIP；單一決策者 | 無 |

## 價目 Port（唯一接近外部的執行期呼叫）

| 項目 | 擁有者 | 前置期 | 擋住哪個 Bolt | 緩解 |
|---|---|---|---|---|
| AWS／GCP／Azure 公開價目 HTTP | 本 repo `pricing_client`（URL 未決） | OQ-3 在 B1 infrastructure-design | **不擋** B1 合閘 | stub + `PriceHit`／`PriceMiss`／`PriceUnsupported`；無端點不發 HTTP |
| npm 新套件 | — | — | — | `mockups.md` 圓餅用 SVG，不新增 npm |

stage 說 fully AI-contained 時本檔可輕。價目列在此是因為它**會**打外網，但完成條件已降為契約而非真實 200。

## 內部門控（非本檔範圍）

| 門控 | 記於 |
|---|---|
| 種子只補缺失列 | `bolt-plan.md` B1 DoD |
| OpenAPI／`api.d.ts` 同批 | `bolt-plan.md` Bolt 間約束 |
| 對比與窄視窗人工驗 | `team-allocation.md` |
