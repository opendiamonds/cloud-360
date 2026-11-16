# 安全測試說明（build-and-test）

- 撰寫時間（`date -u`）：`2026-11-14T02:19:24Z`
- 視角：品質工程（lead）兼 security engineer
- 依據：`project.md` ## Mandated 的 ADR-0006 四面向（hard constraint）、`team.md` 測試底線 A／B、各單元 `nfr-requirements/security-requirements.md` 與 `nfr-design/security-design.md`

## 測試框架與設定

本 repo 沒有 SAST／DAST 工具（無 Bandit、Semgrep、ZAP），也沒有應用程式碼層的 secret 掃描（`validate_no_obvious_secrets()` 只看 contract 檔，`team.md` 已如實記載）。本 intent 的安全驗證全部落在**既有測試框架內的斷言**：

| 類型 | 載體 | 範例 |
|---|---|---|
| 授權 allow／deny（A 規則） | `unittest` ＋ `TestClient` | `test_project_visibility_endpoints`、`test_membership_endpoints`、`test_memory_authz`、`test_requirement_field_http`、`test_diagram_system_attach`（F1）、`test_brain_gateway_semantic_memory`（P2：擁有者恆為已驗證身分） |
| 存在性預言機（不存在與不可見同回應） | `TestClient` | 成員四端點與需求欄位三端點的固定 404（合併前必修第 14 列） |
| 資料庫層角色邊界 | `verify_memory_role.sql`（以 `cloud360_memory` 本身連線） | R0–R3：讀不到 `public`、可寫 `memory` 兩表、不能在 `public` 建表 |
| 靜態結構鎖 | `unittest`（讀原始碼／ast） | `test_project_visibility_static`（寫入方法須注入可見性判定）、`test_mcp_bridge_static`（依賴釘選）、embedding-port 的 `SEC-1`（模組內禁 DB／授權） |
| 輸入防護 | `unittest` ＋ Hypothesis | `prompt_guard` 自我竄改預檢、語意記憶內容防護（M7 突變）、指涉名稱 `sanitize_target_name` |
| 日誌不洩漏 | `assertLogs` | 拒寫時 log 不含原文、embedding 例外訊息不含 `userinfo`、記憶拒絕日誌只記解析後 id |
| 部署設定 | `validate_env_contract.py` | `claude-code` 不得出現在任何部署設定（`test_llm_provider` 反案） |

## 執行方式

與 `integration-test-instructions.md` 相同：後端全套、`tests_pg`、四支 `verify_*.sql`、`validate_*_contract.py`。安全相關測試沒有獨立指令——它們是全套的一部分，本站不另拆。

## 覆蓋期望

- 每個新增或修改的 HTTP 端點：有 status code 與回應欄位集合的 `TestClient` 測試（B 規則）。
- 每個授權判定：allow 與 deny 兩向各至少一案（A 規則）；存在性不得從回應碼推得。
- 每個新的寫入路徑：擁有者與可見範圍不得由請求內容決定（性質測試）。

## ADR-0006 四面向逐項判定（本 intent 整體＋本站新增改動）

逐格先對照上游已核可的同名表（`requirements.md` ADR-0006 節、`local-verify-fixes.md` 兩輪的判定表），判定不同處寫明理由。

| 面向 | 判定 | 本站實跑證據 | 未驗／殘留 |
|---|---|---|---|
| IAM | **適用** | 後端全套（含上列 allow／deny）三輪全綠；`verify_memory_role.sql` R0–R3 於 pg18 以 `cloud360_memory` 連線通過；`tests_pg` 成員併發 C1–C4 通過；F1 的 11 案（擁有者可掛、非擁有者／非成員 404、缺 `K2 edit` 403）通過；語意記憶 P2（擁有者恆為說話者、範圍恆為 `owner`）通過 | **記憶專用資料庫角色只在 HTTP 路徑生效**：`memory_router.py` 五個端點經 `get_memory_db`，但閘道的 `_prefetch`（`brain_gateway.py:1755`）、情節記憶寫入、本站新增的語意記憶寫入（`_write_semantic`）與 `work_orchestrator.py:1081` 的程序記憶寫入都用主連線的 `session_factory`——合併前必修第 52 列「他單元三處呼叫端」仍開放，本站新增的語意寫入使呼叫端變成**四處**。應用層授權（facade）仍完整，缺的是資料庫層的第二道邊界 |
| encryption | **適用（同上游）** | 本站無新儲存欄位、無新通道、無金鑰；F2 把專案／系統名稱送進路由 prompt（`TARGET_NAME_MAX_CHARS`=60 限縮），與使用者原句同級外送 | `mcp-bridge` 的使用者 JWT 在 `internal` 網段明文往返，已由使用者裁決接受（合併前必修第 7 列）；容器間傳輸維持明文（`brain-infra` `D-2`）——皆既有裁決，本站不翻案 |
| network exposure | **適用** | F1 新增 `PUT /api/hierarchy/diagrams/{id}/system`（既有前綴、既有 JWT）；`dump_openapi.py --check` 一致；Redis／MCP bridge 不對外（compose 無 `ports:`，`validate_env_contract.py` 通過）；本機 Claude Code provider 由 `validate_env_contract.py` 與 `test_llm_provider` 鎖住「不得進部署設定、非 `APP_ENV=local` 自動退回 openrouter」 | 真實 stack 的對外面（nginx `location /api/`、WS upgrade、Cloudflare Tunnel）本站未起 stack 驗證，交 CI `ui-regression`／部署後探測（`brain-infra` 的 `PROBE-CONTRACT`） |
| audit logging | **適用** | 記憶刪除稽核 `deleted_by_user` 與清除稽核 `purged_by_retention` 由 `verify_memory_schema.sql`、`verify_purge_sql.sql` R1–R10 於真實 PG 驗過；需求欄位讀取的 `requirement_field.read` INFO（合併前必修第 8 列）由 `test_requirement_field_*` 驗過 | F1 的圖歸屬變更與語意記憶「建立」只有 INFO log，**無正式稽核列**（`memory_audit_events.action` 的 CHECK 封閉集合沒有建立用值；`diagram_change_records.source` 只允許 `brain_orchestration`）——列為回補項由上游決定 |

## PBT hard constraint（ADR-0006）

| 落點 | 判定 | 證據 |
|---|---|---|
| agent routing | **適用，已有性質測試** | 意圖路由的 `@given`（`test_intent_routing_*`）、指涉判定 P1／P2（`test_referent_current_target`，`max_examples=300`）、語意記憶分流 P0／P1／P2（`test_brain_gateway_semantic_memory`）；三輪全套全綠 |
| cost calculator | 本 intent 未新建（成本能力只做路由與狀態事件轉譯） | — |
| IaC generator | 本 intent 未觸及 | — |

## 本站觀察到的安全相關事項

1. **本機 Claude Code provider 的錯誤訊息**：`claude_code_chat.py:330`、`:342` 對任何非零結束都說「可能尚未登入」，會誤導排錯（intent-router Minor (e)，非安全缺陷，列待修）。
2. **語意記憶內容防護是樣式判定**：無關鍵字、無特定形狀的短密碼不會被擋（`local-verify-fixes.md` 未完成項 7）；屬已揭露的設計界線，不是本站新發現。
3. **`review_agent.py:49`** 的錯誤訊息仍教使用者設定 `OPENROUTER_API_KEY`，在 `claude-code` 模式下為錯誤指引（intent-router Minor (f)）。
