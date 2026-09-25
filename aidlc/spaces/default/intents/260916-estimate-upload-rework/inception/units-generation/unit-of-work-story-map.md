# 工作單元 ↔ 需求對應：C1 估價表上傳

本 scope 的 `user-stories` 為 SKIP，無 `stories.md`。依 units-generation stage 檔 fallback：**以 `requirements.md` 的每一條 FR 作為上游 ID**，對應到 Unit ID 與 construction 目錄。

「Story implementation order within each unit」改為該單元內 FR 的建議實作關注序（非跨單元建置序）。

## 對應表

| FR | Unit ID | Directory | 備註 |
|---|---|---|---|
| FR1.1 | U8 | `u8-estimate-workspace-ui` | 上傳介面 |
| FR1.2 | U1 | `u1-estimate-parser` | 三格式 |
| FR1.3 | U2 | `u2-estimate-intake-api` | 大小／檔數限制 |
| FR1.4 | U2 | `u2-estimate-intake-api` | 副檔名＋魔數 |
| FR1.5 | U1 | `u1-estimate-parser` | 雲別判定（互動由 U2／U8） |
| FR1.6 | U2 | `u2-estimate-intake-api` | 即用即棄 |
| FR2.1 | U1 | `u1-estimate-parser` | |
| FR2.2 | U1 | `u1-estimate-parser` | 無法辨識列 |
| FR2.3 | U1 | `u1-estimate-parser` | 純函式 |
| FR2.4 | U1 | `u1-estimate-parser` | PBT |
| FR3.1 | U8 | `u8-estimate-workspace-ui` | 明細呈現 |
| FR3.2 | U8 | `u8-estimate-workspace-ui` | |
| FR3.3 | U8 | `u8-estimate-workspace-ui` | `/cost` 路徑 |
| FR4.1 | U1 | `u1-estimate-parser` | Validator |
| FR4.2 | U1 | `u1-estimate-parser` | |
| FR4.3 | U1 | `u1-estimate-parser` | |
| FR4.4 | U1 | `u1-estimate-parser` | |
| FR4.5 | U8＋U9 | `u8-…`／`u9-…` | 跨單元：檢查區 U8、建議區 U9 |
| FR5.1 | U7 | `u7-cost-advice-agent` | |
| FR5.2 | U9（主）＋U7 | `u9-…`／`u7-…` | 呈現與「產生中／本期未提供」為 U9 主責；狀態持久化在 U7 |
| FR5.3 | U7 | `u7-cost-advice-agent` | |
| FR5.4 | U7 | `u7-cost-advice-agent` | |
| FR5.5 | U5 | `u5-pricing-lookup-port` | 執行期可被 U7 呼叫；非單元相依 |
| FR5.6 | U5 | `u5-pricing-lookup-port` | |
| FR5.7 | U5 | `u5-pricing-lookup-port` | |
| FR5.8 | U4 | `u4-credential-pipeline` | |
| FR5.9 | U5 | `u5-pricing-lookup-port` | |
| FR5.10 | U5＋U7 | `u5-…`／`u7-…` | 降級：Port 實作＋agent 行為約束 |
| FR6.1 | U2 | `u2-estimate-intake-api` | EstimateSet.diagramId |
| FR6.2 | U2 | `u2-estimate-intake-api` | |
| FR6.3 | U8 | `u8-estimate-workspace-ui` | 歷史抽屜 |
| FR6.4 | U2 | `u2-estimate-intake-api` | |
| FR6.5 | U2＋U8 | `u2-…`／`u8-…` | 授權 U2、徽章 U8 |
| FR6.6 | U2＋U8 | `u2-…`／`u8-…` | API U2、分享 UI U8 |
| FR7.1 | U2 | `u2-estimate-intake-api` | |
| FR7.2 | U2 | `u2-estimate-intake-api` | |
| FR7.3 | U2 | `u2-estimate-intake-api` | |
| FR8.1 | U2 | `u2-estimate-intake-api` | |
| FR8.2 | U2 | `u2-estimate-intake-api` | |
| FR8.3 | U2 | `u2-estimate-intake-api` | |
| FR9.1 | U3 | `u3-legacy-cost-retirement` | |
| FR9.2 | U3 | `u3-legacy-cost-retirement` | |
| FR9.3 | U3 | `u3-legacy-cost-retirement` | |
| FR9.4 | U5 | `u5-pricing-lookup-port` | 保留 |
| FR9.5 | U5 | `u5-pricing-lookup-port` | 保留 |
| FR9.6 | U1 | `u1-estimate-parser` | CI 路徑改寫 |
| FR9.7 | U3 | `u3-legacy-cost-retirement` | |
| FR9.8 | U3＋U4 | `u3-…`／`u4-…` | 減舊參數／增憑證變數 |
| FR9.9 | U3 | `u3-legacy-cost-retirement` | |
| FR9.10 | U3 | `u3-legacy-cost-retirement` | OpenAPI 重產；contract-design 亦相關 |
| FR9.11 | U3 | `u3-legacy-cost-retirement` | |
| FR10.1 | U6＋U7 | `u6-…`／`u7-…` | 骨架／具體 agent |
| FR10.2 | U6 | `u6-langgraph-runtime` | |
| FR10.3 | U6 | `u6-langgraph-runtime` | 不得移除 sdk |
| FR10.4 | — | GAP | 其餘 agent 遷移不在本期 |
| FR11.1 | U4 | `u4-credential-pipeline` | |
| FR11.2 | U4 | `u4-credential-pipeline` | |
| FR11.3 | U4 | `u4-credential-pipeline` | |
| FR11.4 | U4 | `u4-credential-pipeline` | |
| FR12.1–12.5 | U8 | `u8-estimate-workspace-ui` | 官方估價教學彈窗 |
| FR13.1–13.3／13.5–13.6 | U2 | `u2-estimate-intake-api` | SKU 描述補齊與落庫 |
| FR13.4 | U5 | `u5-pricing-lookup-port` | 邊界腳本放行 sku_catalog |

## 跨單元 FR

| FR | 單元 | 切分理由 |
|---|---|---|
| FR4.5 | U8、U9 | 檢查區與建議區分屬兩個 UI 單元 |
| FR5.2 | U7、U9 | 狀態持久化 vs 呈現 |
| FR5.10 | U5、U7 | Port 降級＋agent 不得因查價失敗而中止 |
| FR6.5／FR6.6 | U2、U8 | API／ACL vs UI |
| FR9.8 | U3、U4 | 環境變數減與增 |
| FR10.1 | U6、U7 | runtime 骨架 vs 成本建議圖 |
| FR13 | U2、U5、U8 | 寫庫／邊界／規格欄呈現 |

## 各單元內關注序（單元內，非全域建置序）

| Unit | 建議關注序 |
|---|---|
| U1 | FR2.3／FR9.6 邊界 → FR1.2／FR2.1 讀取 → FR1.5 判定 → FR2.2 → FR4.* → FR2.4 PBT |
| U2 | Schema／實體 → 上傳限制 → 解析協調 → SKU 描述補齊 → ACL／分享 → 稽核 → 觸發建議 |
| U3 | 舊端點／表刪除 → Playwright → 工具鏈／e2e／OpenAPI → 孤兒檔 |
| U4 | repo contract 調整 → 憑證傳遞 → 文件 → 缺憑證可啟動驗證 |
| U5 | 保留最小集 → 目錄價包裝 → 降級 → 唯讀界線測試 |
| U6 | 相依引入 → OpenRouter 煙測 → 串流輔助 |
| U7 | Advice 實體／狀態 → Orchestrator 背景工作 → 省錢建議 → SSE → 跨雲／品質 |
| U8 | 空狀態／教學彈窗 → 上傳 → 明細（規格描述）與檢查 → 歷史 → 分享／無障礙 |
| U9 | SSE 訂閱 → 骨架／進度 → 三類建議呈現 |

## 覆蓋核對

- 上游 FR：70 條（含後補 FR12／FR13；與 `requirements.md`／domain-design `traceability.json` 一致）
- 每條均有 Unit 或明示 GAP（僅 FR10.4）
- 九個 Unit 皆至少承載一條 FR
