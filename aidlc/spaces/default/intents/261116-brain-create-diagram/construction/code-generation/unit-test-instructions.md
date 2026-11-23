# Unit Test Instructions — 讓大腦直接建立新的架構圖

## 測試框架

- **後端**：Python 內建 `unittest` ＋ `hypothesis` ＋ `unittest.mock`（不使用 pytest）。測試 DB 走 `backend/tests/helpers.py` 的 SQLite（`make_session()`；跨執行緒情境用 `make_session(threaded=True)`）。HTTP 層用 `starlette.testclient.TestClient` 與 `app.dependency_overrides`。
- **前端**：只有 Playwright e2e（沒有 unit／component 框架，`team.md` D 不採）。
- 不新增任何測試依賴或設定檔；沿用既有設定。

## 執行本 intent 的測試（皆限定檔案，不跑全套）

後端（在 `backend/` 下執行）：

```bash
cd backend && python -m unittest -v \
  tests.test_diagram_drafts_schema \
  tests.test_diagram_drafts_hierarchy \
  tests.test_diagram_drafts_api \
  tests.test_brain_diagram_creation \
  tests.test_brain_diagram_creation_flow \
  tests.test_diagram_system_attach \
  tests.test_work_orchestrator_store \
  tests.test_work_orchestrator_flow
```

- 第一個 test-after 步驟（Step 4）之前，先以 `cd backend && python -m unittest tests.test_diagram_system_attach -v` 確認執行器可用（既有檔，應綠燈）。
- Step 2 實測（2026-11-17，本機 `python` 不在 PATH）：精確指令為 `cd backend && .venv/bin/python -m unittest tests.test_diagram_system_attach -v`（`Ran 11 tests … OK`）；全套基準 `cd backend && .venv/bin/python -m unittest discover -s tests` 為 `Ran 1542 tests … OK (skipped=3)`。前端 `cd frontend && npx playwright test --list` 列出 `Total: 226 tests in 11 files`。CI 上的 `python` 即上列指令的 `.venv/bin/python`。
- 新測試檔的名稱如上；若實作時拆分或改名，同步更新本節。

前端（在 `frontend/` 下執行，需要本機 stack，見 `LOCAL-DEV.md`）：

```bash
cd frontend && npx playwright test e2e/diagram-drafts.spec.ts
```

靜態檢查：`cd frontend && npm run lint && npm run build`。

## 預期數量與覆蓋

- 策略 Standard：每個元件 5～8 個測試，關鍵邊界加整合測試。
  - 資料模型與遷移：約 4 個
  - 列圖、刪除系統、清除預設專案：約 7 個
  - 架構圖 API（鍵集合、`as_draft`、`finalize`、四個 409、估價、權限雙向）：約 12 個
  - 判定與取名純函式：PBT 約 8 個性質＋判定表例子
  - 路由與 `CapabilityClient`：約 6 個
  - 閘道流程（新建、冪等三案、權限、四種反問、重新驗證）：約 10 個
  - Playwright：3 案
- 覆蓋率：repo 沒有量測工具（`team.md`），以 A／B／C 規則與上列數量為實際門檻；不降低任何既有門檻。
- PBT：判定純函式屬 ADR-0006 agent routing hard constraint，必須有 `@given`。

## Mock 與替身

- 外部 LLM、OpenRouter 一律 mock；路由題目以替身回固定的機率。
- `CapabilityClient` 走 ASGI transport 打真實 app；需要模擬 409 或逾時時以 `httpx.MockTransport` 替換。
- 閘道測試沿用 `tests/brain_gateway_fakes.py` 的 Redis／session 替身；工作編排沿用 `tests/work_orchestrator_fakes.py`（Step 5 同步其 `list_diagrams_of_system` 形狀）。

## 測試資料

- 每個測試自建使用者、專案、系統與圖，不依賴種子以外的共用資料；`ensure_role_permissions_seeded(db, force=True)` 提供角色權限。
- 草稿以 `UserDiagram(status="draft")` 直接建立，或經 `POST /api/collab/diagrams` 帶 `as_draft: true`。
- 不連接任何共享的資料庫或 Redis。
