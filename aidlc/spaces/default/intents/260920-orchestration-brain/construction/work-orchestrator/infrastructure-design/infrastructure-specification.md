# 基礎設施規格 — `U12 work-orchestrator`

## 一、資源清單：零新增

| 項目 | 現況 | 本單元的變化 |
|---|---|---|
| 服務／容器 | `deploy/docker-compose.deploy.yml` 的既有服務（含 `U1` 交付的 Redis） | 無 |
| 監聽埠 | 後端既有埠 | 無（本單元沒有 HTTP 端點；入口是 `U13` 的 WebSocket） |
| Redis | `U10` 的工作階段 key（24 小時 TTL） | 每個工作項多一個 `wi:<id>` 欄位；不改 TTL、不建新 key；新增兩支 Lua 腳本隨程式碼部署（`backend/services/session_scripts/`），由 `RedisGateway` 以 `SCRIPT LOAD`／`EVALSHA` 載入，不需部署步驟 |
| 資料表 | `diagram_change_records`（`U4`）、記憶表（`U5`） | 無 DDL 變更，只經 facade 寫入列 |
| 環境變數 | — | 無 |
| 加密 | 既有 Redis（compose 內部網路）、PostgreSQL volume | 無變化；新增的使用者內容落地併入上游 `OQ-3`（`../nfr-design/security-design.md` 第六節） |

## 二、部署順序

deploy-on-merge 之下，下列三者**必須同一次合併**，否則會出現「程式已上線、依賴未上線」的中間狀態：

| 依賴 | 缺少時的後果 |
|---|---|
| `U10 SessionStore` 的 `load_work_items`／`put_work_item`／`update_work_item` 與兩支 Lua | `dispatch` 在第一次寫入即 `AttributeError` → `U13` 的交辦全部失敗 |
| `U7 HierarchyFacade.list_diagrams_of_system` | 作業對象只指定系統的交辦全部失敗 |
| `U13 brain-gateway` 對本單元的呼叫 | 本單元無入口；先上線無害（死碼），後上線則 `U13` 無法交辦 |

因 `U10`／`U7` 的擴充由本單元在 code-generation 一併實作，同批合併是自然結果；寫在這裡是讓審查 PR 的人知道不得拆分。

## 三、回滾

| 回滾什麼 | 做法 |
|---|---|
| 程式 | 既有 `deploy.yml` 的 rollback job。舊程式不讀 `wi:*` 欄位，殘留欄位隨工作階段 24 小時到期，不需清理 |
| Redis 資料 | 不需回滾；Lua 腳本以 SHA 載入，舊程式不會呼叫新腳本 |
