# Security Requirements — u2-iac-ui

> Unit: `u2-iac-ui`（ui）· Q2=A／Q3=A · 上游 NFR1／NFR3／NFR5。

## ADR-0006（UI 面）

| 面向 | 判定 | 處置 |
|---|---|---|
| **IAM** | **適用（消費後端 403）** | 無權入口 disabled＋說明；不繞過 API 自造授權。 |
| **Encryption** | **沿用** | HTTPS 瀏覽；不把草稿持久化到 localStorage／IndexedDB（本輪）。 |
| **Network exposure** | **適用** | 只打 `/api/iac`；MSW 僅測試／平行開發，不得指向真實雲端 apply。 |
| **Audit logging** | **薄適用** | 瀏覽器不另建密文日誌；診斷靠 UI 狀態＋`error.code`（Q5=A）。 |

## NFR3 — 客戶端保密（Q2=A）

| ID | 需求 |
|---|---|
| NFR3.UI.1 | toast／console／錯誤 UI **不得**傾印完整 HCL、改寫前後明文 secret、完整 response body、stack。 |
| NFR3.UI.2 | 下載經 blob／物件 URL；**不**把密文放進可分享的 query string。 |
| NFR3.UI.3 | 顯示文案以 `error.code` 對照表為準（對齊 FD Q3）。 |

## NFR5 — 無障礙（Q3=A）

| ID | 需求 |
|---|---|
| NFR5.1 | 步驟、findings、下載、確認 modal **可鍵盤**完成主路徑。 |
| NFR5.2 | 嚴重度除顏色外有**文字標籤**。 |
| NFR5.3 | 下載確認 modal：dialog 語意、Esc／取消、開啟時初始 focus；還原焦點於關閉後（盡力）。 |
| NFR5.4 | 關鍵控件保留 mockups／FD 既定 test-id，供 Playwright。 |

## 明確禁止

- Apply／destroy UI。
- 開發模式「圖方便」把密文打进 console（Q2≠B）。

<!-- confirmed: Looks correct -->
