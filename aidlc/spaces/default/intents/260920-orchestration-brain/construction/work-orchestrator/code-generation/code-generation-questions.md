# Code Generation 問題檔 — `U12 work-orchestrator`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（含其內嵌的 Testing Contract，`test-after`、`standard`）與
`unit-test-instructions.md`。計畫 §二 列出三次審查帶下來的 26 項殘留與處置，其中幾項是本站的設計選擇，在此明白揭露：

- **跨單元修改**：`U10` 的 `SessionStore`／`session_types` 與 `U7` 的 `HierarchyFacade` 各新增方法，與本單元同一次合併、不得拆分。
- **Lua 真實原子性不在 CI**：只有本機 opt-in 測試（需 `REDIS_URL`）；CI 驗的是替身與參考實作。
- **牆鐘上限自行判定**：三種能力都以注入的 `clock` 判定逾時，不用 `asyncio.wait_for`，以便測試控制時間。
- **在途存檔受保護**：使用者停掉或逾時後，已送出的存檔仍會跑完並如實寫變更紀錄；工作項狀態維持已停掉或失敗。
- **未在本計畫內處理**：`AC1.3.2`／`AC5.1.3`／`AC10.2.4` 的字面仍待使用者裁決（`OPEN-WO12-6`／`-7`）。

## Plan Approval

[Approval Fingerprint]: sha256:v3:62f89d64a21288c7705779fa228da82b8d4b2d5634f1a009c15ef43c645a3caf
[Planned Source]: 3f7857a243153e7b13b8c30a4f963e93caa5581d4644aa6bf12914c2c4cebe81
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan
