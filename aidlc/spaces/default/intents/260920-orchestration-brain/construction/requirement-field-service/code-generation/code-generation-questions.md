# Code Generation 問題檔 — `U20 requirement-field-service`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（含其內嵌的 Testing Contract，
`test-after`、`standard`）與 `unit-test-instructions.md`。計畫 §二 列出四站審查帶下來的
殘留與處置，其中一項是本站的設計選擇，在此明白揭露：

- **ORM 模型不掛 `before_create` 守門**（沿用 `U19` 對兄弟表的先例）：掛了會讓後端在未遷移的
  資料庫上整個起不來；不掛的代價是表不存在時由 `create_all` 建出一張功能等價、只缺 COMMENT 的表。
- **請求本體在授權通過之後才解析**：使任何 422 都晚於授權判定，且不回顯輸入；本體帶
  `updated_by` 回 422（使用者 2026-10-12 已同意）。

## Plan Approval

[Approval Fingerprint]: sha256:v3:3401f192f1c687ad7126c21714d66eb4868899072bae03daf2fbed13069990f5
[Planned Source]: 4656dbeddd2a792509c0f603ead35c9da9a40015a1977319bbfbe39bcd986bbb
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan
