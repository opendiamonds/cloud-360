# ADR 0020: 大腦 WebSocket 契約的頁面與範圍欄位、握手協定名

- Status: Accepted（隨 `U13 brain-gateway` code-generation 的 Plan Approval 一併核可；於該單元 Step 1 自 `construction/brain-gateway/code-generation/adr-0020-draft.md` 原樣移入，僅改本行與標題的「草案」字樣）
- Date: 2026-10-13
- Amends: `K-12`（`contract-summary.md:855-1015`）的訊息形狀；`U2 brain-ws-contract` 已交付的 `backend/services/brain_ws_contract.py`。
- 觸發來源：`U13` functional-design 的 `[GW1]`=A、`[GW4]`=A、review-02 R-05；`U10 session-store` functional-spec §六 預留的 ADR-0020 最小改動集。
- 依據全文：`construction/brain-gateway/functional-design/functional-spec.md` §十一（逐欄定義）。

## Context

`U2` 交付的 WebSocket 契約無法表達三件 `U13` 必須知道的事：

1. **握手時的協定名**：`[GW1]`=A 要求客戶端同時提供 `cloud360.brain.v1` 與 `bearer.<jwt>`，伺服器只回送前者，使 token 不出現在回應標頭。契約只有 `bearer.` 一種格式。
2. **訊息來自哪一頁**：`user_message` 只有 `text`，閘道無法選擇該頁的對話段，「各頁獨立對話」（`FR3.2`）失效（`[GW4]`=A）。
3. **狀態訊息屬於哪個範圍／段、反問屬於哪一種**：`sharing_mode`、`work_target` 沒有範圍或段，前端無法過濾；`clarify` 分不出「意圖反問」與「對象反問」（review-02 R-05）。

## Decision

在 `brain_ws_contract.py` 新增七個必填欄位，協定版本維持 `v: 1`：

| 代號 | 模型 | 方向 | 新欄位 | 型別 |
|---|---|---|---|---|
| C-1 | `WsSubprotocol` | 握手 | `protocolName` | `Literal["cloud360.brain.v1"]` |
| C-2 | `UserMessagePayload` | 客→伺 | `page` | `Literal["entry","workspace","assessment"]` |
| C-3 | `SharingModePayload` | 伺→客 | `scope` | `Literal["workspace","assessment"]` |
| C-4 | `WorkTargetPayload` | 伺→客 | `segment` | `Literal["shared","workspace","assessment"]` |
| C-5 | `SetWorkTargetPayload` | 客→伺 | `segment` | `Literal["shared","workspace","assessment"]` |
| C-6 | `SetSharingModePayload` | 客→伺 | `scope` | `Literal["workspace","assessment"]` |
| C-7 | `ClarifyPayload` | 伺→客 | `kind` | `Literal["intent","target"]` |

全部必填、無預設（預設值會讓產生的 TypeScript 欄位變成可選，且 `page` 預設為 entry 會靜默寫錯段）。

附帶更正：

- **`consumed_by` 更正**（`OPEN-GW13-12`）：`K-16`、`K-17`、`K-18` 把 `U13` 列為消費端，但 `U13` 的設計不呼叫 membership、requirement-field 與 progress-channel（進度通道由 `agent_router` 自行開關，`agent_router.py:131-162`）。三處 `consumed_by` 移除 `U13`。
- **`meta.userId` 寫入端**（`OPEN-GW13-3`）：`K-09` 沒有寫入方法、目前也沒有讀者；記為已知缺口，不在本 ADR 新增方法。

## Consequences

- 改 `brain_ws_contract.py` 六個模型（C-1..C-7）、`backend/scripts/dump_ws_contract.py` 的 `CLIENT_FIELD_WHITELIST`，重產 `ws-contract.json` 與 `frontend/src/types/ws-contract.d.ts`；既有兩道漂移閘門（ADR-0019）照常把關。
- 既有測試 `backend/tests/test_ws_contract.py` 須同步修改（`:47`、`:61`、`:62`、`:283`、`:288`、`:290`；細節見 functional-spec §十一之二）。
- DEMO 前端（不帶 `page`）在重產型別後 `tsc -b` 紅燈——與 DEMO 移除同批（`[IG2]`=A）。
- `U14 entry-page-ui` 必須：帶兩個子協定且以型別取值、每則 `user_message` 帶 `page`、依 `scope`／`segment` 過濾狀態訊息、依 `kind` 呈現反問、收到 4401 時重新取得 token 重連、遇拒絕時退避重試至少 60 秒（`[GWND1]`=A）。
- **`U14` 上線之後**，任何不相容的增量都必須升版 `v`。

## Alternatives Rejected

- **升版為 `v: 2`**：目前沒有已發布的客戶端（唯一客戶端是同批移除的 DEMO 頁），升版只增加協商成本。
- **`protocolName` 做成獨立常數**：需要第二道漂移閘門；放進既有格式描述模型可共用同一道閘門與 ADR-0019 §5 的 lint 規則。
- **`page` 以連線綁定（hello 宣告）**：同一分頁切換頁面需重連（`[GW4]` 選項 B，使用者未採）。
- **回送 `bearer.<jwt>`**：token 進回應標頭（`[GW1]` 選項 B，使用者未採）。

## Security（ADR-0006）

- **IAM**：不變；授權仍在握手與每則訊息的重驗（`BR62.1`）。
- **Encryption**：不變；token 只在請求標頭，經 TLS。
- **Network exposure**：端點不變（`/api/brain/ws`）；C-1 讓 token 不出現在回應標頭，縮小暴露面。
- **Audit logging**：不變。
