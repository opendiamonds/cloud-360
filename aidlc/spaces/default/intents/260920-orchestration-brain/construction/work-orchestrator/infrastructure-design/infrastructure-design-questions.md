# Infrastructure Design 問題檔 — `U12 work-orchestrator`

> **本站問 0 題，不派審查員。** 本單元的基礎設施面為空：零新服務、零新監聽埠、零新環境變數、零新資料表或欄位。
> 依 2026-10-06 核可的精簡形狀（不適用的 design 站改跑 by-reference），逐項寫出判定理由。與 `U20` 不同，本站沒有
> CI 變更或部署順序以外的真實標的，故不派審查員。

## 一、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據（本站實測） |
|---|---|---|
| 部署策略 | **有一個標的：同批上線** | 本單元依賴 `U10` 的三個新方法與兩支 Lua、`U7` 的 `list_diagrams_of_system`（皆為本單元在 code-generation 一併做的跨單元修改）；三者必須同一次合併。見 `infrastructure-specification.md` 第二節 |
| 運算／儲存／網路 | **無新資源** | embedded（`unit-of-work.md:48`）；工作項存在既有 Redis 工作階段 key 內（`[WO3]`=A）；呼叫既有端點走行程內 ASGI 傳輸，不經網路 |
| 監控 | **無新管線** | 只有應用 log（`../nfr-design/observability-design.md`）；repo 無指標或告警管線 |
| CI/CD | **無新 job** | 新測試落在既有 backend `unittest` 探索範圍；真 Redis 的 Lua 一致性測試為 opt-in，不進 CI（`../nfr-design/scalability-design.md` 第三節已揭露） |
| Secrets | **無標的** | 零新環境變數；使用者 token 只在記憶體內（`BR51.2`） |
| 擴縮 | **無標的** | 隨既有後端；多 worker 正確性由比對後寫入承擔（`NFR12.12`），不依賴黏著工作階段 |

## 二、問題

（無）
