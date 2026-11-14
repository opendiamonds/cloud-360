# ADR 0021（草案）：MCP bridge 工具面（`X-04`）的契約增量與 `K-16` 消費者更正

- Status: Proposed（隨 `U21 mcp-bridge` code-generation 的 Plan Approval 一併核可；核可後於該單元 Step 1 原樣移入 `inception/decisions/0021-mcp-bridge-x04-contract-increments.md`，只改本行與標題的「草案」字樣）
- Date: 2026-10-15
- Amends:
  - `X-04`（`contract-summary.md:2049-2124`）的工具清單、屬性名、未定項與授權責任。
  - `K-16`（`contract-summary.md:1538`、`:1611`、`:1622`、`:1639-1640`、`:1659`）的消費者。
  - `components.md` 的 `McpBridge → ProjectMembership` 邊。
  - `unit-of-work.md`／`unit-of-work-dependency.md` 的 `U21 → U19` 邊。
- 觸發來源：
  - `U21` functional-design 的 `[MB2]`、`[MB3]`、`[MB4]`、`[MB6]`（皆 A）。
  - 該站的 `OPEN-MB21-6`。
  - functional-design review-01 的 R-07、review-02 的 R-16。
- 依據全文：`construction/mcp-bridge/functional-design/functional-spec.md` §九、§十一，以及 `rules.md` 的 `BR72.5`、`BR73.1`–`BR73.3`、`BR74.1`、`BR75.1`–`BR75.3`。

## Context

`X-04` 在 contract-design 階段**刻意只寫了一部分**（`contract-summary.md:2051-2052`）。`U21` 的設計完成後，有五件事必須回寫進契約。

1. **工具清單少了清空**。`K-17` 已把 `U21` 列為 `clear_field` 的呼叫端（`contract-summary.md:1841`），但 `X-04` 的 `tools` 只有讀與寫（`:2076-2085`）。如果 agent 用「`PUT` 空值」代替清空，會被 `U20` 的空值檢查擋下（本單元在 `BR74.6` 也這樣擋）。
2. **允許清單與黑名單底線互相牴觸**。`write_requirement_field` 的允許清單逐字含 `field_key`（`:2082`），而黑名單底線以不分大小寫的子字串比對 `key`（`:2067-2068`）；`AC11.4.2`（`stories.md:728`）也逐字要求同一條底線。兩條已核可的約束不能同時成立。`[MB6]`=A 已裁決改名。
3. **兩個未定項已有答案**：`how_token_reaches_this_process`（`:2092-2095`，`OQ-15`）與 `transport`（`:2097-2098`，`OQ-16`）。`authorization_responsibility`（`:2114-2117`）寫「全域層由被呼叫的既有 API 的 `require_story_action` 承擔」，與實作相反：需求欄位的三條路由不掛 `require_story_action`，全域的 `K4` 判定在 facade 內進行。
4. **allowlist 的初始範圍**。`[I7]` 與 `brain-infra` `cicd-pipeline.md` 第 24 項寫的是「`U19` ＋ `U20` 兩塊」，但 `[MB4]`=A 第一版不開放成員管理類工具。
5. **bridge 不依賴成員層**。per-project 判定由 `U20` 的 facade 在 backend 內呼叫 `U19` 完成，對 bridge 只是傳遞依賴。但 `K-16` 把 `U21` 列為 `resolve_project_role` 的消費者，`components.md` 與單元依賴圖也有 `McpBridge → ProjectMembership`／`U21 → U19` 的直接邊。保留這些邊，會讓下游讀 `depends_on` 時以為 bridge 直接呼叫成員層，與 `BR75.3` 正面相撞。

## Decision

| 代號 | 契約 | 決定 |
|---|---|---|
| C-1 | `X-04` `tools` | 新增 `clear_requirement_field`：`inputSchema_properties_allowed: [system_id, agent_group, field]`，回傳 `FieldView`，經 `K-17` 的 `clear_field`（HTTP `DELETE …/fields/{agent_group}/{field_key}`，無本體）。需要 agent 宣告 |
| C-2 | `X-04` `tools.write_requirement_field`（並適用 C-1） | 工具屬性 `field_key` 改名為 **`field`**；黑名單底線維持不分大小寫的子字串比對。bridge 在組 backend 請求時反向映射回路徑參數 `field_key`。**已依 `[MB6]`=A 定案**（2026-10-13T23:08:40Z），本 ADR 追認的是 `X-04` 的字面 |
| C-3 | `X-04` 的未定項與授權責任 | (1) `how_token_reaches_this_process`：token 只來自每一次 MCP HTTP 請求的 `Authorization: Bearer` 標頭，原樣轉給 backend，只存在於該請求的 contextvar，用完即棄；bridge 不持有任何長效憑證、不解碼 JWT。(2) `transport`：MCP streamable HTTP，端點 `/mcp`，無狀態模式，回應以 JSON 為主；只在與 `backend` 共用的專屬網段，不發佈 ports。(3) 連線層新增標頭 `X-Cloud360-Agent`，用來宣告 agent 身分，bridge 依登錄表填入 `on_behalf_of`；它**不是**工具參數，也不是授權依據。(4) `authorization_responsibility` 改為：「每次呼叫都以使用者身分受權限檢查；全域層（`K4`）與 per-project 判定都由 `K-17` facade 在 backend 內承擔；bridge 不做任何授權判定」 |
| C-4 | `[I7]`／`brain-infra` `cicd-pipeline.md` 第 24 項 | allowlist 初始值收窄為 `U20` 的三個 operation（讀、寫、清空）。路徑前綴白名單第一版只有 `/api/requirements/`，成員管理類在結構上無法加入。**這是對已核可範圍的收窄**，不是擴充；日後擴充要改程式常數，並經程式碼審查 |
| C-5 | `K-16`、`components.md`、單元依賴 | **移除邊，不是加註保留**。完整落點見下方清單 |

**C-5 的移除落點**

- **`contract-summary.md`**：
  - `:1538`：契約總表的 K-16 消費者列移除 `U21`。
  - `:1611`：K-16 標題移除 `U21`。
  - `:1622`：`consumers.separate_process` 移除 `U21`。
  - `:1659`：`resolve_project_role.consumed_by` 移除 `U21`。連同 ADR-0020 已移除的 `U13`，實際值為 `[U20]`。
  - `:1639-1640`：`anti_double_check` 的字面改為與 facade 實作一致（全域層在 facade 內評估），與 `U20` 的 `OPEN-RF20-5` 同批。
- **`components.md`**：
  - `:664-666`：刪 `McpBridge.depends_on` 的 `ProjectMembership` 項。
  - `:567-568`：刪 `ProjectMembership.dependents` 的 `McpBridge` 項。
  - `:788`：刪 Part B' 圖的對應箭頭。
  - `:798-799`：文字 fallback 改為只呼叫 `RequirementRegistry`。
  - `:775`：無環驗證的邊清單同步移除。
  - `:779`、`:890`：邊數由 17 改為 16。
  - `:809`、`:811`：兩張摘要表同步移除。
  - 剩下的 `McpBridge → RequirementRegistry` 註明 `style: sync` 為「經 HTTP 的同步請求」。
- **單元依賴**：
  - `unit-of-work.md:392`：`U21` 的依賴只剩 `U20`。
  - `unit-of-work.md:369`：`U19` 的「被依賴」列移除 `U21`。
  - `unit-of-work-dependency.md:248`：刪 `U21 --> U19`。
  - `unit-of-work-dependency.md:266`：改為「`U21` 依賴 `U20`（經它傳遞依賴 `U19`）」。

已凍結的上游檔不回改，以本 ADR 為準。

## Consequences

- **程式**：`backend/mcp_bridge/allowlist.json` 宣告三個工具，`rename` 為 `{field_key: field}`，產物 `generated_tools.json` 由 `gen_mcp_tools.py` 產生，CI 的 `backend` job 以 `--check` 把關漂移。產生器以 PBT 鎖住「黑名單檢查在 rename 之後」與「白名單相等」。`AC11.4.2` 的結構斷言以測試檔內的字面白名單為期望值。
- **授權**：bridge 只經 HTTP 呼叫 `U20` 的三條路由。程式中 `require_story_action`／`user_can`／`resolve_project_role` 的出現次數為 0，由靜態測試鎖住。拒絕的理由與使用者直接存取時相同（`AC11.4.1`）。
- **邊的移除**：Bolt 排序不變。`U21 → U20 → U19` 的傳遞依賴仍在，`risk-and-sequencing-rationale.md:199` 已把 `U21` 與 `U20` 排在同一個 B13、位於 B11 之後。`K-16` 的契約端點三問不再懸空。
- **已知缺口**：
  - **清空沒有持久溯源**：`K-17` 的 `clear_field` 不收 `on_behalf_of`，agent 代清空時，持久列只記使用者，代寫溯源只在 bridge log（`OPEN-MB21-4`）。
  - **agent 宣告是自報的**（`OPEN-MB21-2`，與 `U20` 的 `OPEN-RF20-1` 合併追蹤）。
  - **成功的讀取沒有帶使用者身分的紀錄**（`OPEN-MB21-14`，`[MBN1]`=A）。
  - **token 以明文在專屬網段上傳輸**：使用者已接受此例外，上游條件「本機迴環或加密」不成立。
- **傳輸層的錯誤語意**：`:2100` 記載的「連線中斷、逾時、半開連線未定義」部分由本單元補上。逾時與連線失敗回 `backend_unavailable`、`retryable: true`；client 中途斷線時 backend 請求是否完成，以 `U21` code-generation Step 1 的實測（`OPEN-MB21-16`）為準，寫入與清空都是冪等的。
- **相關但不屬本 ADR 的契約增量**：bridge 由 `internal` 網段改掛只與 `backend` 共用的專屬網段（使用者 2026-10-15T00:38:42Z 裁決）。這使 `X-04` 的 `exposure`（`:2062-2063`）更嚴格地成立，屬 ADR-0006 network exposure 的收窄，記在 `U21` 的 code-summary。

## Alternatives Rejected

| 代號 | 未採方案 | 理由 |
|---|---|---|
| C-1 | 不提供清空工具，讓 agent 以 `PUT` 空值清空 | 空值會被拒；而且會把清空語意藏在寫入裡，「誰清的」的溯源更難 |
| C-2 | `[MB6]` 選項 B：切段比對，`field_key` 單一豁免 | 豁免清單會隨工具擴充增長，底線變得可協商 |
| C-2 | `[MB6]` 選項 C：完整名稱相等比對 | `api_key`、`access_token` 這類名稱不會命中，底線形同虛設 |
| C-3 | 以 MCP `initialize` 的 `clientInfo` 宣告 agent 身分 | 無狀態傳輸下沒有可綁定的 session；`clientInfo` 描述的是 client 實作，不是 agent |
| C-3 | `[MB2]`／`[MB3]` 選項 B：服務帳號或委派憑證 | 新增簽發機制與長效 secret；稽核主體會變成服務帳號，違反「稽核主體是使用者本人」 |
| C-3 | 舊式 HTTP ＋ SSE 或 stdio 傳輸 | 舊式 SSE 需要長駐連線與 session 對應，與逐請求身分相反；stdio 要求 client 與 bridge 同進程樹，與獨立進程、compose 服務的形狀不符 |
| C-3 | 保留「全域層由 `require_story_action` 承擔」的字面 | 與實作相反；下游若依字面在 bridge 補一次全域檢查，會形成第二份授權 |
| C-4 | 第一版同時開放 `U19` 的成員管理工具 | 讓 agent 能改成員與角色，風險與一個尚無 client 的通道不成比例；以路徑前綴白名單在結構上排除 |
| C-5 | 保留 `McpBridge → ProjectMembership` 邊並加註「傳遞依賴」 | 讀 `depends_on` 的下游不會讀註解；邊本身就是宣告，保留即與 `BR75.3` 互斥 |
