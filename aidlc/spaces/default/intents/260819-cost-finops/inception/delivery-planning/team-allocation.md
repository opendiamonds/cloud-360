# Team Allocation — Bolt 與執行者

> Stage: delivery-planning（Inception 2.8）· Intent: `260819-cost-finops`
> 上游：`requirements.md`、`stories.md`、`mockups.md`、`components.md`、`unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`、`team-practices.md`。
> Bolt 定義見 `bolt-plan.md`。

## 結論：1.5 SKIP，全部 AI 執行 + 人工 gate

**`team-formation` 未執行**（mvp `[S]`）。stage 規定此情況全部 Bolt 由 `aidlc-developer-agent` 執行。不虛構多團隊 Program Board。

## 配置

| Bolt | 包含單元 | 執行者 | 人工決策點 |
|---|---|---|---|
| B1 | `cost-schema-rbac`、`cost-calculator`、`cost-api`、`cost-ui` | `aidlc-developer-agent` + 各 Construction stage 的 lead／gate | 第一段 staging 驗收（Sidebar、列、圓餅、時數、CTA、無橫幅）；OQ-3 真實價目 URL 若要在 B1 infra-design 定案 |
| B2 | `cost-budget-banner` | 同上 | 橫幅不可關閉與對比的人工／靜態驗收（NFR-1；`stories.md` AC-7.5） |

每個 Construction stage 仍有核可閘。AI 執行 ≠ 自動放行。

## 人工必須介入

| 類別 | 事項 | Bolt |
|---|---|---|
| 工具鏈無自動化 | 對比 ≥ 4.5:1、窄視窗捲動（NFR-1／NFR-2；`mockups.md` 無障礙） | B1、B2 |
| 無 inbox 靜態檢查 | AC-7.5 確認未引入通知中心 | B2 |
| 既有 DB 種子 | staging 表非空時，補缺失 `C1h`／`C1r`／`C1b`／`C1o` 列是否真的出現（CI SQLite `force=True` 看不到這條） | B1 |
| 公開價目 URL | infrastructure-design OQ-3；B1 可用 stub 合閘 | B1 |

## 未採用

| 選項 | 為何不採 |
|---|---|
| 多團隊平行 | 無第二執行者；Q4=A 嚴格序列 |
| 依 kind 換 agent | mvp 預設單一 `aidlc-developer-agent`；calculator PBT 仍由該 agent 在 build-and-test 落地 |
