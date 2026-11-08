# Team Allocation — Bolt 與執行者

> Stage: delivery-planning · Intent: `261105-d-iac-generation`  
> Bolt 定義見 `bolt-plan.md`。  
> **mob**＝負責一個 Bolt 的執行組合（人＋AI agent）。

## 結論：1.5 已跑＝Solo／pair＋AI；無多團隊 Program Board

`team-formation` 定案為 **Solo／pair＋AI-DLC**（`mob-composition.md`）：Driver＝luojingting；Navigator＝AI-DLC agents；審閱者按閘門介入。不虛構第二執行團隊。

Construction 預設由 `aidlc-developer-agent`（及各 stage lead）在同一工作階段執行；人工在每個 Construction stage 核可閘決策。關閘時再確認 staffing（solo vs 多團隊）。

## 配置

| Bolt | 包含單元 | 執行者 | 人工決策點 |
|---|---|---|---|
| B1 | U1 `u1-iac-api` | `aidlc-developer-agent`＋各 Construction stage lead／gate | R-01／R-02 落地形狀；US6.1 成對測試路徑選定；閘／PBT 紅燈處置 |
| B2 | U2 `u2-iac-ui` | 同上 | test-id／無障礙抽樣；下載 modal；與真實 API 的 e2e 時機（stub 或合併後） |

每個 Construction stage 仍有核可閘。AI 執行 ≠ 自動放行。

## 平行時（Q3=A）

| 模式 | 說明 |
|---|---|
| 單人雙 worktree | 允許；B2 e2e 延後至 U1 D1 2xx 可用 |
| 雙人各領一 Bolt | 需關閘改 unit-major＋team ownership（見 stage Step 6）；目前預設不啟用 |

## 人工必須介入

| 類別 | 事項 | Bolt |
|---|---|---|
| 契約凍結尾巴 | download 具名 RBAC；scan／rewrite 的 `diagram_id` 規則 | B1 |
| 多角色演示 | 種子無三角 edit → 用多帳號演示，不改種子（US6.2） | B1＋B2 |
| 對比／窄視窗 | 若 NFR 要求人工抽樣 | B2 |
| OpenRouter | 可 stub 合閘；真實金鑰不進版控 | B1 |

## 未採用

| 選項 | 為何不採 |
|---|---|
| 固定跨職能 mob sessions | team-formation Q5=A |
| 依 D1／D2／D3 輪值不同人主導 | 同上 |
| 多團隊 Program Board | 僅一 mob 標籤 |
