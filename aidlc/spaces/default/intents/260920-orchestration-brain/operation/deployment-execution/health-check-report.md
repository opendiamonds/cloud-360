# 健康檢查報告

## 部署 job 內建的驗證（run 43611880032，全部 success）

| 步驟 | 驗證內容 |
|---|---|
| Set the memory-only database role password | `cloud360_memory` 的密碼設定成功。角色本身由合併前的遷移建立 |
| Verify the Redis ACL actually took effect | Redis ACL 實際生效 |
| Pull the embedding model into the Ollama volume | embedding 模型可用 |
| Probe the data plane through /api (frontend -> backend -> db) | 資料面三段都通 |
| Wait for the public hostname to answer through the tunnel | Cloudflare Tunnel 公開網址可以連上 |
| Record mcp-bridge health (non-blocking) | MCP bridge 健康已記錄 |
| Verify sessions survive a Redis restart (NFR4.53-57) | Redis 重啟後 session 仍保留 |
| Verify the brain WS subprotocol survives the tunnel | 大腦 WebSocket 子協定能穿過 tunnel |
| Record this commit as the last-good deployment | last-good 記為 `186f3a6` |

## 部署後從外部探測（2026-11-14T15:51:11Z）

| 請求 | 結果 | 判讀 |
|---|---|---|
| `GET https://cloud360.danniel.cc/` | 200（0.25s） | 前端正常 |
| `GET /login` | 200 | 前端路由正常 |
| `POST /api/auth/login`（不存在的探測帳號） | **401** | 通過：401 同時證明 frontend → backend → db 都通（`DEPLOY.md` §5.7） |
| `GET /api/auth/me`（未帶 token） | 403 | 驗證層有作用 |
| `GET /openapi.json` | 200 `text/html` | 回的是 SPA fallback，不是 API 規格，符合「規格不得被靜態提供」 |

## 結論

基礎設施層全部健康。需要登入的功能（大腦對話、專案、記憶、成員）在部署 job 的 WS 驗證之外，還要靠手動測案確認，見 `smoke-test-results.md`。
