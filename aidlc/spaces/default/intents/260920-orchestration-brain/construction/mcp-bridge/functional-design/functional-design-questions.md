# Functional Design 問題檔 — `U21 mcp-bridge`

> 單元類型 **`service`**（`unit-of-work.md`，L；部署模型 standalone，獨立進程、僅供同主機連接）。產出 `entities.md`、`rules.md`、
> `functional-spec.md`、`traceability.json`。Depth `Minimal`。本單元承接的未決項多（`OQ-15`、`[F16]` 的 client 無人承接、
> `on_behalf_of` 與工具參數的衝突），故出五題；每一題都是「預設錯了會造成真實重工或安全缺口」的事。

## 一、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 傳輸 | HTTP／SSE；compose 第七個服務、`internal` 網段、**不發佈 `ports:`**、不對外暴露 | `brain-infra` infrastructure-design `[I6]`=A；`requirements.md:619` |
| 工具來源 | 由 `openapi.json` 產生（REST→MCP），以 allowlist 管暴露面；產生器為 PBT 標的；漂移檢查為新閘門 | `brain-infra` `[I7]`=A；`cicd-pipeline.md:314-360` |
| 憑證白名單 | 每個工具 `inputSchema.properties` 採白名單，黑名單底線 `token`／`key`／`secret`／`authorization` 不分大小寫；斷言排除根目錄 `.mcp.json` | `X-04` `:2064-2075`；`AC11.4.2` |
| 授權 | 每次以使用者身分呼叫既有 API（`require_story_action`／facade 照常執行），不得同進程繞過 | `FR11.6`；`X-04` `:2114-2121` |
| 稽核主體 | 使用者本人，非服務帳號 | `requirements.md:620`；`X-04` `:2086-2095` |
| 健康檢查 | 不需認證的 liveness 端點；啟動初期 backend 回 502 時不得死掉 | `brain-infra` monitoring-design `:170-188` |
| 代寫溯源（U20 交接） | 代寫一律帶 `on_behalf_of`、清空走 `DELETE`、不得繞過 facade | `requirement-field-service` code-summary `:145-152` |

## 二、本單元承載的故事

`US11.4`（`AC11.4.1`–`AC11.4.3`）。注意 `stories.md:732` 自述「本故事的 Given 今天不可構造」——見 MB1。

## 三、問題

### MB1. 誰是 MCP 的呼叫端？

範圍定案 `[F16]`=B 寫「新增 MCP server ＋ **在大腦側加 MCP client**」，但查遍已設計的單元，**沒有任何一個承接 client**：
`U13` 明確不呼叫需求欄位（`NFR13.16`），`U11`／`U12` 對 MCP 命中為 0。沒有 client，`AC11.4.1`／`AC11.4.3` 的「agent 經 MCP 通道」在系統內沒有發起者。

A) **本單元交付 server ＋ 一支最小的測試用 client；大腦側 client 列為開放項交回範圍定義**（建議）：`AC11.4.x` 以測試 client 經真實
   HTTP／SSE 驗證（allow／deny 雙向、白名單），server 可獨立上線；代價是這一版沒有任何 agent 實際使用它，能力 11 的「agent 取用欄位」
   要等後續 intent 補上 client。
B) **本單元同時交付大腦側 client，並接進 `U11`／`U12` 的流程**：能力完整，但要重開 `U11`／`U12`／`U13` 的設計（它們已完成、已 commit），
   並決定「哪個意圖會觸發讀寫欄位」——這是新的產品決定。
C) **呼叫端是外部 agent（例如開發者的 IDE 或 Claude Code）**：不符「不得對外暴露、僅同主機」的已定約束，需新 ADR。

[Answer]: A <!-- 2026-10-13T22:54:10Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### MB2. 使用者的 token 怎麼到達 MCP server？（`OQ-15`）

A) **每次 MCP 請求由 client 在 HTTP `Authorization: Bearer` 標頭帶上使用者 token，bridge 逐次原樣轉給既有 API、用完即棄、不儲存**（建議）：
   與 `[I6]` 收窄的方向一致；token 永不進工具參數、不進 LLM context、不落地；生命週期等於使用者的 JWT（8 小時）。
B) **bridge 以使用者 token 換一張短效的委派憑證**：需要新的簽發機制與金鑰，屬新增 IAM 面，需新 ADR。

[Answer]: A <!-- 2026-10-13T22:54:10Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### MB3. 代寫標示（`on_behalf_of`）怎麼填？

既有 `PUT /api/requirements/.../fields/...` 的本體含 `on_behalf_of`，照 `openapi.json` 直接產生工具，它會變成工具參數——agent 就能
自填任何代寫組（`X-04` 明文禁止；`OPEN-RF20-1`）。

A) **產生器把 `on_behalf_of` 從工具 schema 剝除；agent 身分由 client 在連線層宣告（例如 MCP 初始化時的 client 名稱或一個請求標頭），
   bridge 對照已宣告的代寫組白名單後自行填入**（建議）：工具參數無法冒充；但連線層宣告仍是 client 自報，**真偽無法驗證**——
   在本單元揭露為已知限制（與 `OPEN-RF20-1` 同性質），留待有 client 簽章機制時收緊。
B) **每個 agent 一組 bridge 簽發的憑證**：可驗證真偽，但需金鑰管理與發放流程，屬新 IAM 面、需新 ADR。
C) **本版不提供寫入工具，只開放讀取**：沒有代寫就沒有冒充問題；`AC11.4.3` 仍成立，但能力 11 的「agent 寫回欄位」延後。

[Answer]: A <!-- 2026-10-13T22:54:10Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### MB4. 第一版開放哪些工具？

`[I7]` 寫 allowlist 初始值為 `U19`＋`U20` 的端點；`X-04` 只列兩個工具（讀、寫需求欄位）。

A) **只開需求欄位的讀、寫、清空三個工具**（建議）：與 `X-04` 一致、暴露面最小；成員管理類（邀請、移出、改角色）屬高風險寫入，
   依 ADR-0004「高風險工具需核准」不在第一版開放。
B) **依 `[I7]` 開放 `U19`＋`U20` 全部端點**：含成員邀請／移出／改角色；需先補 ADR-0004 的工具 registry 與高風險核准流程。
C) **只開讀取**（需求欄位與成員清單唯讀）。

[Answer]: A <!-- 2026-10-13T22:54:10Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### MB5. 用什麼語言與套件實作 server？

repo 內目前沒有任何 MCP 程式或依賴（`requirements.txt` 對 `mcp` 零命中），`A-7`（MCP 能否在本 repo 運作）尚未實測。

A) **Python ＋ 官方 `mcp` SDK，沿用 backend 映像另起一個 compose 服務**（建議）：與既有後端同語言、同工具鏈（`unittest`／`hypothesis`）、
   產生器可直接讀 `openapi.json`；代價是新增一個 Python 依賴（需釘版）。
B) **Node／TypeScript ＋ 官方 SDK**：MCP 生態最成熟，但後端測試工具鏈與 CI job 要另起一套。

[Answer]: A <!-- 2026-10-13T22:54:10Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### MB6. `X-04` 的允許清單與黑名單底線互相牴觸，怎麼處置？

> 設計中途浮現的追問（architect 起草 `rules.md` 時發現）：`X-04` 允許寫入工具有參數 `field_key`，而 `AC11.4.2` 的黑名單底線要求工具屬性名
> 不含 `token`／`key`／`secret`／`authorization`（不分大小寫）——`field_key` 命中 `key`。兩條已核可的約束不能同時成立。

A) **工具屬性改名為 `field`，底線維持不分大小寫的子字串比對**（建議；本站設計預設，`BR72.5`）：檢查維持最嚴，`access_token`／`api_key`
   這類名稱一定被擋。代價：工具參數名與 API 路徑參數名不同（產生器做對應），需追認 `X-04`（C-2）。
B) **保留 `field_key`，切段後逐段比對並為 `field_key` 設單一豁免**：工具名與 API 一致；代價是豁免清單本身要審核，且切段比對比子字串寬。
C) **保留 `field_key`，只比對完整名稱相等**：最簡單；代價是 `access_token`、`api_key`、`client_secret` 都能通過這道檢查，只剩白名單一道防線。

[Answer]: A <!-- 2026-10-13T23:08:40Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->
