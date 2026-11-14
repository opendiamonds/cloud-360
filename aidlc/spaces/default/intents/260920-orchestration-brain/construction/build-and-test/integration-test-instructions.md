# 整合測試說明（build-and-test，Standard）

- 撰寫時間（`date -u`）：`2026-11-14T02:19:24Z`
- 測試策略：**Standard**（`aidlc-state.md`）——本檔涵蓋「關鍵邊界測試、跨單元互動」
- 前置：`build-instructions.md` 的相依、環境變數與副本做法

## 測試框架與設定

| 層 | 框架 | 位置 | 隔離方式 |
|---|---|---|---|
| 後端單元＋HTTP 邊界 | `unittest` ＋ `hypothesis` ＋ `starlette.testclient.TestClient` | `backend/tests/`（131 支 `.py`） | `tests/helpers.py`：psycopg 未安裝時才 stub、in-memory SQLite、每 session 重新 seed 角色權限 |
| 真實 PostgreSQL 邊界 | `unittest` | `backend/tests_pg/`（5 支：成員併發 C1–C4、記憶 V1／D1–D2、清除原子性、需求欄位 G1–G4、語意記憶寫入後預取） | `DATABASE_URL` 缺值即失敗（不得退回 SQLite） |
| 真實 PostgreSQL schema 斷言 | `psql -v ON_ERROR_STOP=1 -f` | `backend/scripts/verify_memory_schema.sql`（S1、S3–S15）、`verify_meta_schema.sql`（P1–P17）、`verify_purge_sql.sql`（R1–R10）、`verify_memory_role.sql`（R0–R3） | `verify_purge_sql.sql` **會真的刪資料**，只能對拋棄式 DB 執行 |
| 真實 Redis Lua 一致性 | `unittest` | `backend/tests_redis/test_work_item_lua.py`（opt-in，**不是 CI 閘門**） | 只用 `REDIS_URL` 指定的 DB 與隨機前綴 key |
| 前端 e2e（攔截層） | Playwright（chromium） | `frontend/tests/e2e/` 七支 mock spec：`a11y`、`entry-page`、`member-pages`、`memory-page`、`object-picker`、`project-pages`、`sidebar-landmarks` | `page.route`／`routeWebSocket` 攔截，不打後端；須對**正式建置**（`vite preview`）執行，開發模式 StrictMode 雙掛載會讓請求計數類案例失準 |
| 前端 e2e（真實 stack） | Playwright | `regression`、`entry-page-live`、`estimate-workspace` 三支 | 需要 `deploy/docker-compose.test.yml` 起的 nginx＋backend＋db＋redis；由 CI `ui-regression` 執行 |

## 跨單元關鍵邊界（本 intent）

| 邊界 | 參與單元 | 主要測試 |
|---|---|---|
| WS 契約 ↔ 閘道 ↔ 前端 | brain-ws-contract、brain-gateway、entry-page-ui | `test_ws_contract`、`test_dump_ws_contract`、`test_brain_gateway_*`、`entry-page.spec.ts`、`check:ws-types` |
| 閘道 → 意圖路由 → 工作編排 | brain-gateway、intent-router、work-orchestrator、progress-channel | `test_intent_routing_structure`、`test_work_orchestrator_flow`、`test_referent_current_target`、`test_progress_channel` |
| session 外部化 | session-store、work-orchestrator | `test_session_store_behaviour`、`test_session_contract`、`tests_redis.test_work_item_lua` |
| 記憶層 | memory-data、memory-service、embedding-port、memory-purge、memory-page-ui | `test_memory_*`、`test_embedding_port`、`tests_pg.test_memory_service_pg`、`test_purge_atomicity`、`test_semantic_memory_prefetch_pg`、`verify_memory_*.sql`、`verify_purge_sql.sql`、`memory-page.spec.ts` |
| 專案／系統／成員授權 | hierarchy-data、hierarchy-service、membership-service、rbac-story-ids、project-pages-ui、member-pages-ui、object-picker-ui | `test_project_visibility_*`、`test_project_write_guard`、`test_membership_*`、`test_rbac_story_ids_seed`、`tests_pg.test_membership_concurrency`、`project-pages.spec.ts`、`member-pages.spec.ts`、`object-picker.spec.ts` |
| 需求欄位 ↔ MCP 橋接 | project-meta-data、requirement-field-service、mcp-bridge | `test_requirement_field_*`、`test_mcp_bridge_*`、`tests_pg.test_requirement_field_pg`、`verify_meta_schema.sql`、ci.yml 的 U20 步驟 A–E |
| 架構圖掛系統（F1，本站新增） | hierarchy-service、collab | `test_diagram_system_attach`（11 案）、`project-pages.spec.ts`／`object-picker.spec.ts` 新增 3 案 |
| 對話寫入語意記憶（本站新增） | brain-gateway、memory-service | `test_brain_gateway_semantic_memory`（15 案，含 3 個 Hypothesis 性質）、`tests_pg.test_semantic_memory_prefetch_pg` |
| 本機 Claude Code provider（code-generation 新增） | intent-router、llm_provider、langgraph_runtime | `test_claude_code_chat`、`test_llm_provider` |

## 執行方式

```bash
# 1. 後端全套（含 HTTP 邊界、跨單元整合、Hypothesis 性質）
cd backend
PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_STORAGE_DIRECTORY=<scratch>/hyp JWT_SECRET=ci_only_not_a_real_secret \
  .venv/bin/python -B -m unittest discover -s tests -v

# 2. 真實 PostgreSQL（另起拋棄式 pg18，只綁 127.0.0.1）
docker run -d --name <tmp-pg> -e POSTGRES_PASSWORD=<[REDACTED]> -e POSTGRES_DB=cloud360 \
  -p 127.0.0.1:<埠>:5432 pgvector/pgvector:pg18
psql ... -v ON_ERROR_STOP=1 -f schema_rbac.sql          # 套兩次：第二次驗可重跑（BR1.3）
psql ... -v ON_ERROR_STOP=1 -f backend/scripts/verify_memory_schema.sql
psql ... -v ON_ERROR_STOP=1 -f backend/scripts/verify_meta_schema.sql
psql ... -v ON_ERROR_STOP=1 -f backend/scripts/verify_purge_sql.sql   # 在 repo 根執行（\i 相對路徑）
MEMORY_DB_PASSWORD=<[REDACTED]> bash deploy/initdb/02-memory-role-password.sh   # psql ≥ 15
PGPASSWORD=<[REDACTED]> psql -U cloud360_memory -v uid=<id> -f backend/scripts/verify_memory_role.sql
cd backend && DATABASE_URL=postgresql+psycopg://... .venv/bin/python -B -m unittest discover -s tests_pg -v
# U20 收斂步驟 A–E：照 ci.yml memory-schema job 的同名步驟
docker rm -f <tmp-pg>

# 3. 真實 Redis Lua（opt-in；必須是 redis:8）
docker run -d --name <tmp-redis> -p 127.0.0.1:<埠>:6379 redis:8-alpine
REDIS_URL=redis://127.0.0.1:<埠>/15 .venv/bin/python -B -m unittest tests_redis.test_work_item_lua -v

# 4. 前端 e2e（攔截層；對正式建置）
cd frontend && npm run build && npx vite preview --host 127.0.0.1 --port <埠> --strictPort &
BASE_URL=http://127.0.0.1:<埠> npx playwright test
# 真實 stack 三支（regression／entry-page-live／estimate-workspace）在此模式必然失敗——
# 它們打的是 nginx 後的真實 backend，由 CI ui-regression 執行
```

## 覆蓋期望（Standard）

- 後端：既有全套維持綠燈（各單元 Testing Contract 的 `scope_floor`）；新增或修改的 HTTP 端點各有 `TestClient` 測試（`team.md` B 規則），授權矩陣變更有 allow／deny 雙向測試（A 規則）。
- 前端：資料形狀變更有 Playwright 斷言（C 規則）。
- agent routing 屬 ADR-0006 PBT hard constraint：意圖路由、指涉判定、語意記憶分流皆須含 `@given` 性質測試。
- 行覆蓋率 80%（`org.md`）**無法量測**：repo 無 coverage 工具（`team.md` 如實記載），本站不宣稱達成。

## 測試資料管理

- 後端：每個 `TestCase` 自建資料（factory 形狀就地建立，不引入 factory 套件），SQLite in-memory 每測試重建。
- 真實 PG：fixture 由各 verify 腳本自建自清（如 `__verify_purge_sql__`、`__u20_ci_fixture__`）；`verify_purge_sql.sql` 有前置守衛，偵測到非 fixture 的逾期列即中止。
- e2e：全部攔截層 fixture 在 spec 內；真實 stack 版本依 `deploy/docker-compose.test.yml` 的 seed。
