# Unit ↔ Story Map — Story D IaC

> Stage: units-generation · 每則 Must 故事對到 Unit ID＋目錄。  
> 跨 unit 故事列於「Cross-cutting」。**不定**跨 unit 施工順序。

## 對照表

| Story | 主責 Unit | Directory | 次責／備註 |
|---|---|---|---|
| US1.1 | U2 | `u2-iac-ui` | U1：入口權限 API／capabilities 若由後端提供 |
| US1.2 | U2 | `u2-iac-ui` | U1：上傳／圖參照若經 `/api/iac` 或圖域代理 |
| US1.3 | U1 | `u1-iac-api` | U2：清空提示與 disabled 態 |
| US1.4 | U2 | `u2-iac-ui` | 上傳失敗 UI；圖域錯誤透傳 |
| US2.1 | U1 | `u1-iac-api` | U2：檔案樹／預覽 |
| US2.2 | U1 | `u1-iac-api` | 實驗性標記在產物內 |
| US2.3 | U1 | `u1-iac-api` | U2：錯誤＋重試 |
| US3.1 | U1 | `u1-iac-api` | U2：findings／空狀態 |
| US3.2 | U2 | `u2-iac-ui` | 嚴重度文字；U1 報告形狀 |
| US4.1 | U1 | `u1-iac-api` | 閘＋redactor；U2：disabled 說明 |
| US4.2 | U2 | `u2-iac-ui` | 自由開 Secrets；U1 執行仍閘 |
| US5.1 | U1＋U2 | 見下 | 下載／modal 跨切 |
| US5.2 | U1 | `u1-iac-api` | U2：下載消費改寫後 zip |
| US6.1 | U1 | `u1-iac-api` | TestClient 403／2xx |
| US6.2 | U1＋U2 | 見下 | 多角色演示端到端 |
| US7.1 | — | — | Should／本輪不建 unit（GAP） |

## Cross-cutting

| Story | Units | 拆法 |
|---|---|---|
| US5.1 | U1, U2 | U1：zip 位元組＋無 apply；U2：下載鈕、HIGH modal 確認／取消 |
| US6.2 | U1, U2 | 兩 unit 皆需可觀察成功態；演示編排屬交付／測試，非 DAG 邊 |

## Unit 內故事群集（非施工順序）

| Unit | 故事群集 |
|---|---|
| U1 `u1-iac-api` | US1.3, US2.*, US3.1, US4.1, US5.1（API）, US5.2, US6.1, US6.2（API） |
| U2 `u2-iac-ui` | US1.1, US1.2, US1.4, US3.2, US4.2, US5.1（UI）, US6.2（UI） |

## 覆蓋檢查

- Must 故事 US1.1–US6.2：皆已指派。  
- US7.1：未指派（Should／Deferred）。  
- 每個 unit 至少有一則故事。
