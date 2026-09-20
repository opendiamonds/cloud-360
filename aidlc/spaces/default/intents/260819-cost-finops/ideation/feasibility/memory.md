<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-19T05:25:47Z — CONDITIONAL 適用：本 stage 的 condition 為整合約束／法規要求／顯著技術不確定性。本 intent 同時滿足 (1) 必須接雲端官方報價 API 且不得使用 production credentials（整合約束＋與 Scope Overrides 的張力）；(2) repo 尚無 cost calculator、尚無站內通知原語、Sidebar 尚無 C 柱；(3) C1 權限矩陣與 Manual Override 觸及 ADR-0006 的 IAM／audit logging。故執行 feasibility，不 skip。
- 2026-08-19T05:25:47Z — intent-capture Q16 已定「進入產品時站內通知」的送達形態，但產品今日零通知原語；本題只問持久化／inbox 能力邊界，不重開「要不要站內通知」。
- 2026-08-19T05:25:47Z — Manual Override 與超支收件人已由 intent-capture 定案；未對應到價目表 SKU 的圖形節點視為同一失敗家族（缺價），不另開題，預設走 Q15 路徑。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-19T05:25:47Z — 省略 stage 範例題「What AWS services and accounts are currently in use?」：本 repo 僅自有 staging，雲端供應商 production 與 production credentials 為 Scope Overrides 排除項；盤點 AWS 帳號與本 intent 無關。
- 2026-08-19T05:25:47Z — 省略「current tech stack」：`project.md` Tech Stack 已定 FastAPI／React／PostgreSQL；本輪不引入新執行期語言。
- 2026-08-19T05:25:47Z — 省略 PCI／HIPAA／SOC2 專題：估價資料為公開價目表與架構圖資源清單，平台為內部 staging，無持卡人資料或受監管工作負載；合規面改由既有 security baseline（IAM、audit logging）覆蓋，不另問外部法規框架。
- 2026-08-19T05:25:47Z — 不重問 intent-capture 已核可項：官方報價 API 必做、本輪只做 C1、時數／缺價覆寫、預算＋超支警告、收件人、Sidebar C＋CTA、本輪不做核准流、不得使用 production credentials。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-19T05:25:47Z — Standard 深度目標 5–8 題；寫 8 題，優先解鎖官方 API 憑證策略、本輪雲別、C1 AC 含 egress 與 Q9 排除 C3 的張力、預算掛載粒度、誰能改數字、通知原語。價目表 freshness 併入 Q2 的公開端點 vs staging 憑證選擇之後果，不另開題。
- 2026-08-19T05:35:43Z — Q1=A 與 Q2=A 字面衝突，加開 Q1a；使用者選 A，將「三雲都要能報價」定錨為成本畫面可用，官方 API 僅限公開免帳號價目。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-19T05:25:47Z — 哪些雲的官方價目表實際提供公開免帳號端點，本 stage 不預判；Q1a=A 把「無公開端點」的雲導向 Manual Override，具體雲別清單留設計階段查證。
