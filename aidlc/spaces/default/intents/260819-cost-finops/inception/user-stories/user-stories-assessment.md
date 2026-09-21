# User Stories 評估 — 成本估算與 FinOps（C1 第一輪）

> Stage: user-stories（Inception 2.4）· Intent: `260819-cost-finops` · Scope: mvp

## 決策

**Execute** — 本階段產出 personas、stories、本評估檔。

## 理由

C1 是使用者可見的新產品面：成本頁、Sidebar 入口、產圖 CTA、超支橫幅；不是純重構、不是單一後端欄位、不是開發者工具。intent 已確認三個受益者（雲端架構師、FinOps 分析師、工程主管），且 scope 鎖定兩段皆 Must、第一段可單獨上線。故事能把 FR 轉成可排程的垂直切片，並讓 design／developer／quality 盲審 AC 可測性。

## 考量因素

| 因素 | 判定 |
|---|---|
| 使用者可見 | 是（Cost 頁、入口、橫幅） |
| 多 persona | 是（三種變更權不同） |
| 業務規則 | 是（月費公式、未定價排除、跟圖走、超支） |
| 跨團隊 | FinOps 與架構／工程主管 |
| 可 skip 條件 | 不符（非純重構／孤立 bug／純基礎設施） |

## 故事最能加值的區塊

- 第一段可單獨上線的價值切片（擷取＋報價＋總額／圓餅／時數／入口）
- 第二段預算與超支橫幅（仍為本輪 Must）
- 角色差異：架構師改時數／區域、FinOps 覆寫單價、FinOps＋工程主管設預算
- 失敗與空狀態（未定價、官方價失敗、無圖）寫進 AC，避免偽「系統故事」
