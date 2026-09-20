# Reverse Engineering 時間戳

> Freshness marker for space-level codekb｜repo `cloud`｜mode **Full rescan（9 份 artifacts 整組取代）**

## 掃描元資料

| 欄位 | 值 |
|---|---|
| 執行時刻（UTC） | `2026-09-16T09:47:32Z` |
| Commit（full） | `cd2754d291eb37086646d80f1fed2abf209e9805` |
| Commit（short） | `cd2754d` |
| 分支脈絡 | `luojingting/feat/cost-estimation-finops` |
| 來源 fingerprint（工具計算） | `git:37b327b8bdc49dac2a2e0974270f8944f2abd9c8` |
| Intent | `260916-estimate-upload-rework`（C1 成本估算改版：改為上傳官方估價表） |
| 模式 | **Full rescan**：全 repo 重新掃描，9 份 artifacts 整批取代 2026-08-19（`c3de2c8`）版本；不合併舊敘述 |
| Active space | `default` |
| Codekb 目錄 | `aidlc/spaces/default/codekb/cloud/` |
| 專案類型 | brownfield（workspace root 即單一 repo `cloud`） |
| Pipeline | reverse-engineering link 2／FINAL（architect synthesis） |
| 上游輸入 | `<record>/inception/reverse-engineering/developer-scan.md`（2026-09-16） |

### 關於 fingerprint 與 HEAD 不同的說明

`git:37b327b8bdc49dac2a2e0974270f8944f2abd9c8` 是工具對**來源樹內容**計算的 fingerprint，**不是 HEAD commit hash**（HEAD 為 `cd2754d`）。兩者本來就不會相等。本次在合成階段重新執行 `codekb-scope-diff --mint --paths ./`，得到的值與掃描前 snapshot 完全相同，確認掃描期間來源樹未變動。

### 本 codekb 描述的是工作樹，不是版控歷史

掃描當下有 **5 個應用面檔案處於未提交狀態**（`git status` 為 ` M`）：

`deploy/render-env.sh`、`deploy/docker-compose.deploy.yml`、`.github/workflows/deploy.yml`、`DEPLOY.md`、`LOCAL-DEV.md`

變更內容為 2026-09-16 移除 AWS 帳號憑證的部署傳遞，並把 `COST_PRICING_USE_SDK` 預設改為 `0`。**查 git 歷史的讀者不會看到這些改動**；本 codekb 的相關敘述以工作樹為準，不要因為歷史對不上而誤判為錯誤記載。

## 與前一版 codekb 的關係

前一版（2026-08-19、`c3de2c8`、intent `260819-cost-finops`）在本次 rerun guard 中回傳 `UNKNOWN_SCOPE`——它沒有可機讀的覆蓋宣告，因此**不帶任何已驗證覆蓋**。本次為 full rescan，9 份 artifacts 全部以本輪結果重寫，未保留任何本輪未查證的舊敘述。

前一版已失效的主要敘述（供讀過舊版的人對照）：C1「cost calculator ABSENT」「pricing client ABSENT」「無 `/cost` 路由」「無成本 API」「無 cost 表」——**全部不再成立**。C1 現為完整可運行的功能域。

## 深度分佈

本次為全 repo 廣度掃描，但**深度並不均勻**。下列區域只做了檔名、行數與介面面的盤點，**沒有**逐行閱讀，引用它們的細節時請自行複驗：

- `backend/services/` 的大檔（`diagram_builder.py`、`wa_rule_engine.py`、`wa_collab_orchestrator.py` 等）
- `frontend/src/pages/` 的實作細節（含 `CostPage.tsx` 的非 API 段落）
- 43 支測試檔的個別內容
- `.claude/`（272 檔）與 `aidlc/`（776 檔）——依指派單排除深度分析

若後續 stage 需要 WorkspacePage／AssessmentPage 與成本頁之間的資料流細節，需另行補掃。

## 本輪重點發現索引

| 發現 | 所在 artifact |
|---|---|
| `backend/cost/` 只有一條進入邊（`main.py:13`），`services` 不反向依賴 cost | `dependencies.md`、`architecture.md` |
| 八類套件外掛鉤，其中三類會讓 CI 紅燈 | `dependencies.md` |
| `backend/Dockerfile` 缺 `playwright install chromium`，Calculator 路徑在部署環境不可用 | `code-quality-assessment.md` |
| `pricing_client` 的最小存活集合為 8 個檔案（比預期大） | `dependencies.md` |
| `claude-agent-sdk` 有 3 個非 cost 消費者，不可隨 C1 移除 | `technology-stack.md`、`dependencies.md` |
| `App.tsx:24` 根導向以 C1 為第一順位 | `api-documentation.md`、`component-inventory.md` |
| 5 個部署面檔案為未提交的工作樹修改 | 本檔、`code-quality-assessment.md` |

## Scope of Analysis

```yaml
scope_version: 1
kind: full
intent: 260916-estimate-upload-rework
fingerprint: 37b327b8bdc49dac2a2e0974270f8944f2abd9c8
analyzed:
  paths:
    - ./
    - backend/cost/
    - backend/main.py
    - backend/models.py
    - backend/database.py
    - backend/Dockerfile
    - backend/requirements.txt
    - .github/workflows/ci.yml
    - scripts/validate_repo_contract.py
    - scripts/validate_env_contract.py
    - scripts/validate_cost_calculator_boundary.py
    - openapi.json
    - deploy/docker-compose.deploy.yml
    - frontend/package.json
    - frontend/src/App.tsx
    - frontend/src/cost/
  components:
    - backend-app-shell
    - persistence-orm
    - cost-domain
    - openapi-contract
    - frontend-routing
    - frontend-cost-support
    - contract-validators
    - ci-core
    - deployment-compose
shallow:
  paths:
    - backend/services/
    - backend/tests/
    - backend/prompts/
    - backend/lenses/
    - backend/scripts/
    - backend/.env.example
    - frontend/src/pages/
    - frontend/src/components/
    - frontend/src/utils/
    - frontend/tests/e2e/
    - deploy/render-env.sh
    - deploy/.env.example
    - deploy/docker-compose.test.yml
    - .github/workflows/
    - schema.sql
    - schema_rbac.sql
    - .claude/
    - aidlc/
    - README.md
    - DEPLOY.md
    - LOCAL-DEV.md
    - TESTING.md
    - CLAUDE.md
    - AGENTS.md
```
