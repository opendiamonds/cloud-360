<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-19T07:12:02Z — Standard 深度、brownfield。上游已鎖 C1 兩段增量、公開免帳號價目、未定價列、權限語意、橫幅、三層模組與測試底線；本站不重問。
- 2026-08-19T07:00:00Z — 預算／時數／覆寫必須伺服器持久化：超支橫幅「每次進入產品都看到」在無 inbox 的前提下，只能靠持久化的每圖估價與預算。不另開題。
- 2026-08-19T07:00:00Z — 單價覆寫與預算變更的稽核紀錄已由 feasibility 合規掃描定為必須；本站寫成可測 FR，不重問要不要稽核。
- 2026-08-19T07:12:02Z — reviewer iteration 1 F1：估價區域與每日時數同屬架構假設，由架構師設定／修改；非架構師 403。OQ-1 射程改為四種變更權。
- 2026-08-19T07:12:02Z — reviewer iteration 1 F2：跟圖走＝每次開啟／重算成本頁以目前 XML 重擷取；列以 mxCell id 對齊；該 id 的時數與 FinOps SKU／單價覆寫保留；已刪節點列移除。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-19T07:00:00Z — 省略「要不要做圓餅／CTA／C2／inbox／核准流／憑證」：皆已由 ideation 定案。價目快取／重試手段承 feasibility R5 留設計，不預選。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-19T07:00:00Z — 6 題：SKU 對應、區域／幣別假設、預設時數、圓餅切法、多圖橫幅、時數→月費公式。這些是 codekb 證明的缺口與 calculator 不變量所需，上游沒有可測答案。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
