# Team Practices — Cloud-360

> Stage: practices-discovery (2.2) · Phase: Inception · Scope: feature
> 彙整基準：基於 `aidlc/spaces/default/memory/team.md` 現行團隊規範與 Inception 2.2 訪談裁決。

## Way of Working

### Branch 命名
所有新建分支必須遵循 `<uploader>/<type>/<slug>`：
- `<uploader>`：開分支者慣用的英文小寫 handle（例如 `doreen`、`danniel`）。
- `<type>`：限定 `feat`、`fix`、`docs`、`chore`、`refactor`、`test`。
- `<slug>`：英文小寫、連字號分隔、3–5 個詞概述變更目的。
- 本次功能採用合規分支：`doreen/feat/a1-compound-cloud-diagram`。

### Commit message 與 PR 標題
一律使用**繁體中文**，包含 type、描述、body 與 PR 標題。格式沿用 conventional commits，type 改為中文（如 `功能(a1): 新增混合雲三雲架構繪圖支援`）：
- `功能` (feat)、`修正` (fix)、`文件` (docs)、`格式` (style)、`重構` (refactor)、`測試` (test)、`雜項` (chore)。

### PR 合併方式
- **Construction Bolt 分支**：走 **squash-merge**，每個 Bolt 對應 `ut` 上一個 commit。
- **一般 feature／fix／chore PR**：維持 **merge commit**，延續既有實踐。

## Walking Skeleton

- **Stance**: `skeleton: off`
- **Rationale**: 本專案已有可運行的完整前後端、5 道 CI 閘門、自動部署與多組 agentic workflows。本次混合雲繪圖為既有 A1 繪圖引擎之功能擴充，無須重複打通端到端最小骨架，直接依技術依賴鏈推進實作。

## Testing Posture

- **Methodology**: custom
- **Ordering**: 先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。
- **Coverage Target**: 維持 `org.md` 最低 80% line coverage 目標宣稱。
- **變更護欄義務**:
  - **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 role_permissions seed 變更需雙向驗證。
  - **B — HTTP 端點變更需 TestClient 測試**：斷言 status code 與 response_model。
  - **C — 前端資料形狀變更需 e2e 斷言**：涉及前端展示之結構變更需 Playwright 驗證。
  - **D — 混合雲專屬測試集**：新增 `backend/tests/test_diagram_builder_compound.py`，完整斷言三雲 XML 群組、Hub-and-Spoke 空間佈局、跨雲直角折線與協議標籤、以及 n8n compound 上行與 fallback 降級。

## Deployment

- **CI 管線**：`repo-contract` → `frontend` (lint + `tsc -b` typecheck + build) → `OpenAPI spec drift 檢查` (`dump_openapi.py --check`) → `backend` (import smoke + unittest) → `docker-build`。
- **CD 管線**：PR closed (merge) 到 `ut` 或手動 `workflow_dispatch` 自動部署至 `192.168.10.10`（逾時 30 分鐘，`concurrency: deploy-10-10`）。
- **Rollback 機制**：部署失敗自動還原 last-good 並開立 revert PR，自癒修復。
- **相依性邊界**：本 intent 不新增任何非標準之外部依賴或未受控環境變數。

## Code Style

- **Backend**：Python 3.11+，遵循 PEP 8 規範，全模組採用完整型別標註 (`from __future__ import annotations`) 與繁體中文 Docstrings。幾何計算與 XML 組裝邏輯完整封裝於 `diagram_builder.py` 內部，維持純函式無狀態特性。
- **Frontend**：TypeScript + React 18，遵循 ESLint 規範與嚴格型別檢查 (`tsc -b`)。元件保持單一職責，狀態同步透過 Context 與標準事件傳遞。
