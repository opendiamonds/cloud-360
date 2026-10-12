# CI/CD — `U12 work-orchestrator`

**無新 job、無既有 job 變更。**

| 檢查 | 落點 | 說明 |
|---|---|---|
| 單元測試、PBT、模型測試 | 既有 `ci.yml` backend `python -m unittest discover -s tests` | 新測試檔放 `backend/tests/` 即被撿到 |
| WebSocket 契約一致性 | 既有契約閘門（`U2` 交付） | 本單元以 `brain_ws_contract` 模型建構訊息（`NFR12.27`），不新增訊息型別 |
| OpenAPI 漂移 | 既有 `dump_openapi.py --check` | 本單元不新增 HTTP 端點，`openapi.json` 不變 |
| Lua 在真 Redis 上的一致性 | **不在 CI** | opt-in 本機測試；`ci.yml` 的 backend job 沒有 Redis 服務。加一個 Redis service 到 backend job 是可行的改進，但屬跨單元的 CI 決策，本單元不夾帶（`../nfr-design/scalability-design.md` 第三節） |

**判定失效條件**：若本單元在 code-generation 新增 HTTP 端點，須回到本站補 OpenAPI 與 `TestClient`（`team.md` 規則 B）。
