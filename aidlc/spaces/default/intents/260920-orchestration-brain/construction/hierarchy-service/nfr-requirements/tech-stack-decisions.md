# 技術選型 — `U7 hierarchy-service`

## 一、本單元的技術選型增量為零

`nfr-requirements` 的 condition 逐字含「**or tech stack selection needed**。
Skip if no NFR requirements and **tech stack already determined**」。
本單元的技術堆疊**完全沿用既有決定**，無任何新選型：

| 層 | 採用 | 來源（非本站決定） |
|---|---|---|
| 執行形態 | 既有 FastAPI process 內的新 router，**embedded** | `unit-of-work.md:43` 逐字 `embedded（同一 FastAPI process 的新 router）` |
| Web 框架 | FastAPI（`fastapi[standard]==0.141.1` 精確釘選） | `team.md ## Code Style`；釘選原因是 OpenAPI dump 的位元決定性 |
| 資料庫 | PostgreSQL，schema 屬 `U4 hierarchy-data`（已交付） | `project.md ## Tech Stack`；本單元**不擁有 DDL** |
| 測試框架 | Python 內建 `unittest` ＋ `starlette.testclient.TestClient` | `team.md ## Testing Posture`（**未使用 pytest**） |
| 授權機制 | 既有 `require_story_action` dependency | 契約 `K-04`（`contract-summary.md`；既有機制，本站不改它） |
| 整體選型文件 | 見 `construction/brain-infra/nfr-requirements/tech-stack-decisions.md` | `U1 brain-infra`（已核可） |

## 二、刻意不引入的東西

- **不新增任何套件**。`starlette.testclient.TestClient` 的前置條件已滿足
  （`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`），
  故 B 規則的測試義務零採用成本。
- **不引入 ORM 層的新抽象**。三個實體的 DDL 屬 `U4`，本單元只讀寫既有形狀。
- **不引入新的例外基底**。`HierarchyForbidden`／`HierarchyNotFound`／
  `HierarchyValidationError`／`HierarchyConflictError` 為本單元自有的 facade 層
  例外，由 router 轉譯；**不是** `HTTPException`（契約 K-07 的 `on_denied`）。
- **不新增 linter／formatter／type checker**。`team.md` 如實記載 backend 側
  目前完全沒有這些工具，導入屬獨立的工具鏈決策，不由本單元夾帶。

## 三、須遵守的既有約束（非本站新增）

- **logger 命名**一律 `logging.getLogger("cloud360.<module>")`
  （`team.md` 已記載 5 支模組用 `__name__` 為已知不一致，新模組不沿用那個形狀）。
- **三層形狀**：router → service → 不讀 DB 的純函式。本單元為新模組，
  故走三層（`team.md ## Code Style` 對新模組的規定）。
- **OpenAPI drift 閘門**：新增端點須同步重 dump `openapi.json`
  （`ci.yml` 的 `dump_openapi.py --check`），漏 dump 即 CI 紅燈。

## 四、上游契約與既有技術棧的引用出處

- **`contract-summary.md`**：本單元的例外型別與呼叫形態全部由契約 `K-07`
  （`hierarchy-authorized-facade`）決定，不是本站的選型——`sole_entry`、
  `consumers.in_process`、`identity_passing`（`principal` 為第一參數）、
  `on_denied`（`HierarchyForbidden`，**不是** `HTTPException`）、
  `retry_and_idempotency`（已落為 `BR2.4`）。`contract-summary.md:361` 的 `K-04`
  `migration.invariant` 另定下遷移後空歸屬列數必須為 0，而本站查出它在遷移之後
  被流量持續打破（`OPEN-H11`）。`contract-summary.md:1551` 的消費端擴充表是
  本單元四個同進程呼叫端的來源。
- **`technology-stack`**：本 repo 為 brownfield，既有技術棧的正式記載在
  `aidlc/spaces/default/memory/project.md` 的 `## Tech Stack`
  （Python／FastAPI、TypeScript／React／Vite、PostgreSQL、GitHub Actions、
  自有 staging `192.168.10.10`）與 `team.md` 的 `## Code Style`／
  `## Testing Posture`（backend 無 linter／formatter／type checker；
  測試為 `unittest` ＋ `hypothesis`，**未使用 pytest**；
  `fastapi[standard]==0.141.1` 與 `pydantic==2.13.4` 精確釘選，其餘 10 個套件未 pin）。
  本單元**不新增、不變更**其中任何一項，故無獨立的 technology-stack 產出。
