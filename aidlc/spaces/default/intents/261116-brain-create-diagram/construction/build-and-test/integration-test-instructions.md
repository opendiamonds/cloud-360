# 整合測試說明（261116-brain-create-diagram）

> 測試策略 Standard：本檔涵蓋跨單元邊界。三個單元（`diagram-drafts` → `brain-create-flow` → `draft-ui`）同批合併進 `ut`。

## 1. 跨單元邊界與承載測試

| 邊界 | 承載測試 | 指令 |
|---|---|---|
| 大腦閘道 → 建圖端點（同進程 ASGI，`as_draft=true`）→ 資料庫草稿 | `tests/test_brain_diagram_creation_flow.py`（真實 FastAPI app ＋ in-memory SQLite，只替換 LLM 路由與工作編排） | `cd backend && .venv/bin/python -m unittest tests.test_brain_diagram_creation_flow -v` |
| 工作編排產圖存回 → `finalize=True` → 草稿轉正式 | 同上 ＋ `tests/test_work_orchestrator_flow.py` | `.venv/bin/python -m unittest tests.test_work_orchestrator_flow` |
| 草稿 → 評核／WA 共編／估價／分享 回 409（`DRAFT_REJECTED_DETAIL`）→ `CapabilityError.draft_rejected` | `tests/test_diagram_drafts_api.py`、`tests/test_work_orchestrator_rules.py` | `.venv/bin/python -m unittest tests.test_diagram_drafts_api tests.test_work_orchestrator_rules` |
| 後端回應 `diagram_status` → OpenAPI → 前端產生型別 | `dump_openapi.py --check`、`npm run check:types`、`tsc -b` | 見 `build-instructions.md` §3 |
| WS `ClarifyPayload` 四種新 kind → 前端 `ClarifyCandidates` | `dump_ws_contract.py --check` ＋ Playwright `diagram-drafts.spec.ts` | 見 §2 |
| 啟動路徑 `init_db()` → `_ensure_diagram_status_schema()` | `tests/test_diagram_drafts_schema.py`（含失敗必須往外拋的兩案） | `.venv/bin/python -m unittest tests.test_diagram_drafts_schema` |

## 2. 前端 e2e（Playwright）

- 本機：先 `npm run build`，再 `npx vite preview --port 4173 --strictPort`，以 `BASE_URL=http://localhost:4173 npx playwright test tests/e2e/diagram-drafts.spec.ts tests/e2e/project-pages.spec.ts tests/e2e/entry-page.spec.ts tests/e2e/object-picker.spec.ts tests/e2e/brain-assistant.spec.ts` 執行。所有 API 與 WebSocket 都由 spec 內的 route 替身回應。
- **限制**：本機跑的是替身版，**不是** CI 的 `docker-compose.test.yml` stack；CI 的 `ui-regression` 才是真閘門（`team.md`）。

## 3. 資料庫遷移在真實 PostgreSQL 上的驗證

腳本：`/Users/jiangzhengdao/.claude/jobs/f9292dcf/tmp/pg-check.sh`（一次性，不進版控）。以 Homebrew PostgreSQL 17 在 job tmp 起一個只聽 Unix socket 的叢集（port 55437），跑完即停機並刪除。**不連任何共用資料庫。**

步驟：
1. 建出 HEAD 版 `schema_rbac.sql` 的 `users`／`user_diagrams` 形狀（無 `status`），放三張既有圖（其一 `updated_at` 為 NULL）。
2. 逐字執行 `hierarchy_migration._ensure_diagram_status_column` 的 DDL（啟動補丁實際送出的敘述）。
3. 對補完的表連跑兩次新版 `schema_rbac.sql` 的 status 區塊（可重跑性）。
4. 對空表只跑 schema 區塊（空 volume 路徑）。
5. 寫入非法狀態值，確認被 CHECK 擋下。
6. 比對 `ORDER BY updated_at DESC, id DESC` 與加上 `NULLS LAST` 的結果。

限制：本機 PostgreSQL 沒有 pgvector、venv 也沒有 psycopg2，因此**沒有**跑完整 `schema_rbac.sql`，也沒有透過 SQLAlchemy 呼叫 Python 函式；驗證的是送出的 SQL 敘述本身。

## 4. 測試資料

全部由測試內建立（`tests/helpers.py` 的 `make_session`／`make_user`／`make_diagram`），不需外部種子。
