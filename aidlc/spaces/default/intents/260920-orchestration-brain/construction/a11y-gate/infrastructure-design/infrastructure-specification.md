# Infrastructure Specification — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: infrastructure-design（Construction 3.4）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 本單元的基礎設施足跡

`U17` 不新增任何執行期基礎設施。它是一個 devDependency 加一支 Playwright spec，**跑在既有的 `ui-regression` 工作流程與它每個 PR 起的短生命週期 stack 上**（`unit-of-work.md:53` 登記為 `standalone（CI 步驟 ＋ devDependency）`）。本檔逐項寫明「沒有」，並寫出每個「沒有」在什麼情況下會失效。

上游：`../nfr-design/security-design.md` ＋ `../nfr-design/security-design-corrections.md`（衝突時以後者為準），以及其上游的 `nfr-requirements` 兩份文件。`components.md` 與 `contract-summary.md` 中與本單元有關的只有 `K-13`／`K-14`／`K-19`／`K-20` 四份 `test-target` 契約；它們定的是掃描對象，不定任何基礎設施。

本站**不提問**：唯一的基礎設施選擇（在哪裡跑）已由 `tech-stack-decisions.md` T-6 定案為既有 `ui-regression`，其餘面向皆不適用。

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute model | 無新增。spec 在 `ui-regression` 的 GitHub-hosted runner 上以 `npx playwright test` 執行 | T-6：不新增 CI job |
| Networking | 無新增。spec 對 `BASE_URL=http://localhost:8090`（`ui-regression.md` 的 compose stack nginx）導航，但所有 `/api/**` 與 WebSocket 皆在瀏覽器端攔截（`C-01`／`D-05`），不對 stack 的後端發出業務請求 | 隔離層的設計目的就是讓掃描結果不依賴後端狀態 |
| Storage | 無新增。過期檢查的中間檔寫在 `testInfo.project.outputDir` 下，隨 runner 銷毀 | `security-design.md` 第五節 |
| Environments | 只在 CI（每個 PR 的短生命週期 stack）與開發者本機。**不進 staging、不進部署** | devDependency 不進產品 bundle（`A11Y-S1`）；`deploy.yml` 不跑 e2e |
| IaC | 不適用 | 無基礎設施資源 |
| Sizing | 無新增資源；新增的是 CI 時間，見下節 | — |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| — | — | — | 本單元不使用任何資料庫、快取、佇列、搜尋、CDN、DNS 或負載平衡器 |

## CI 資源成本（唯一真實的增量）

| 項目 | 增量 | 依據 | 未知處 |
|---|---|---|---|
| `npm ci` 時間 | 多兩個套件（`@axe-core/playwright` ＋ `axe-core`） | `ui-regression.md` 的 `timeout 3m npm ci` | 套件大小未量測；3 分鐘上限與現況的差距未量測 |
| 測試時間 | 21 個 `test()`，其中 18 次 axe 掃描 | `security-design.md` 第一節 | 單次掃描耗時未量測；`ui-regression` 的 `timeout 15m` 與 `U14` 新增的 54 案合計是否超過，交 `build-and-test` 實測（`security-requirements.md` 交接 H-2） |

## Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| `ui-regression` 工作流程與其 compose stack | 既有（非本 intent 單元） | 全部有 e2e 的單元，含本單元 | 本單元**不修改**該工作流程；只新增一支被它自動撿到的 spec |
| `frontend/package.json`／`package-lock.json` | 既有 | 全部前端單元 | 本單元只新增一個 devDependency |
| `frontend/playwright.config.ts` | 既有 | 全部 e2e | 本單元**預設不改**。唯一可能的例外是 `D-03` 的備案（重試排程實證不符時以 project `dependencies` 拆出過期檢查），屆時須在 `code-generation` 計畫中揭露 |

## 「沒有」的失效條件

| 判定 | 何時失效 |
|---|---|
| 不新增執行期基礎設施 | 若有人把掃描改成對 staging 跑（例如部署後檢查），它就變成部署管線的一環，須重做本站 |
| 不改 `ui-regression` | 若 `D-03` 備案或下方 `cicd-pipeline.md` 的證據保留需求被採納，就會改到該工作流程（gh-aw，改後須重新編譯 `.lock.yml`） |
| 不需要 secret | spec 用的 token 是攔截層的假值（`A11Y-S6`）。若有人改成登入真實 stack，就需要測試帳密，而那屬於 `ui-regression` 既有的設定範圍 |
