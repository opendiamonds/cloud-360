# 邏輯元件 — `U7 hierarchy-service`

## 一、三層形狀（`team.md` 對新模組的規定）

| 層 | 元件 | 職責 | 可以做什麼 | 禁止什麼 |
|---|---|---|---|---|
| HTTP | `hierarchy_router` | 取身分 → 呼叫 facade → 轉譯例外 | 把 facade 例外轉成 HTTP 狀態碼（含 `BR6.6` 的 409 顯式宣告） | **不得自行呼叫底層 service**（契約 K-07 逐字，否則 facade 不再是唯一授權入口）；不得自行做授權判定（`BR1.1`：判定在 facade） |
| 授權門面 | `HierarchyFacade` | **唯一授權入口**（K-07 `sole_entry`） | `K2` 判定、列範圍判定（`BR6.1`／`BR6.4`／`BR6.5`）、鑄造不可偽造的 `principal`（`BR1.4`） | 不得自行從 request 取身分（K-07 `identity_passing`：`principal` 由呼叫端傳入且為第一參數）；拒絕時不得 raise `HTTPException` |
| 服務 | `hierarchy_service` | 業務協調，可讀寫 DB | 名稱驗證、衝突檢查、刪除前置條件 | **不設第二道角色檢查**（`BR1.3` 的誠實宣告——這是 K-07 選的模型，不是遺漏） |

**沒有純函式計算層**，且這是誠實判定而非遺漏：本單元的邏輯全是授權判定與
存在性檢查，沒有可下沉的數值運算。故 ADR-0006 的 PBT hard constraint 對本單元
判為 **N/A**（已於 `functional-spec.md` §七之三 逐項對照：PBT 的適用對象為
IaC generator、cost calculator／估價表解析器、agent routing，
`unit-of-work.md` 全檔對 `U7` 無 PBT 指派，而 `:448` 明確只指派給 `U19` 的挑選函式）。

## 二、本單元不擁有的東西（避免下游誤讀）

| 不擁有 | 擁有者 | 狀態 |
|---|---|---|
| 三個實體的 DDL | `U4 hierarchy-data` | 已交付並登記完成 |
| `role_permissions` 的 `K1`／`K2` 種子 | `U3 rbac-story-ids` | 已交付 |
| `require_story_action` 本身 | 既有機制（契約 `K-04`） | 本站只規定如何**使用**它 |
| per-project 授權判定 | 契約 `K-16`（`U19`） | 未交付；`BR6.2` 說明本輪收窄的理由 |
| 架構圖的建立路徑 | `collab_router`／`review_router`（既有） | **`OPEN-H11`：新圖從未被指派系統歸屬，本單元修不了** |
