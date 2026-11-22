# Infrastructure Specification — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T02:25:30Z（`date -u` 取值）。精簡版（by-reference）：本單元為 `ui`、**無後端、無部署元件、無環境變數變更**
> （`nfr-requirements/tech-stack-decisions.md` 的 `NFR8.160`；`nfr-design/logical-components.md` §一）。依 2026-10-06 核可的「不適用的 design 階段改跑精簡
> by-reference、不派審查員」處置執行。綁定 `functional-spec-corrections.md`（`F-*`）、`nfr-requirements-corrections.md`（`N-*`）、`nfr-design/nfr-design-corrections.md`（`D-*`）。

## Deployment

| 項 | 值 | 依據 |
|---|---|---|
| 部署單位 | 既有前端 SPA bundle（`unit-of-work.md:52` 的「embedded（同一 SPA bundle）」） | 無新容器、無新服務 |
| 運算 | 瀏覽器分頁內；伺服器端零新增程式 | `logical-components.md` §一 |
| 網路 | 只用既有 `/api/hierarchy` 四支端點與既有大腦 WebSocket；零新端點 | `security-design.md` §七 Network exposure |
| 儲存 | 無；選單不寫任何瀏覽器儲存（lint 承載） | `OPN-15`；`security-design.md` §一 |
| 部署路徑 | 合併進 `ut` 後由既有 `deploy.yml` 隨前端 image 上線；與 `U15` 同屬 B7（`bolt-plan.md:338`、`:509`） | `org.md ## Deployment` |

## Services

| 服務 | 本單元的使用 | 變更 |
|---|---|---|
| backend（FastAPI） | 呼叫既有 `GET /api/hierarchy/projects`、`GET …/projects/{id}/systems`、`POST …/projects`、`POST …/projects/{id}/systems`；送出既有 `set_work_target` 訊框 | 無 |
| PostgreSQL | 經後端間接讀寫（建立專案／系統） | 無 DDL、無 seed 變更；`schema_rbac.sql`／`DEPLOY.md` 同步規則不觸發 |
| Redis | 作業對象正本（經 `U13`／`U10`） | 無 |

## Shared Infrastructure

| 共用資源 | 影響 | 處置 |
|---|---|---|
| 後端 SQLAlchemy 連線池（預設共 15 條） | 搜尋補抓同時最多 4 個請求；開啟 1～2 個 | `performance-design.md` §一之三、`D-03` |
| `frontend/eslint.config.js` | 新增選單檔案集合的 lint 區塊（共用設定檔） | `security-design.md` §一、`D-06`；code-summary 揭露 |
| `frontend/tests/e2e/a11y.spec.ts`（`U17` 的檔） | 新增兩個掃描點 | `logical-components.md` §二；code-summary 揭露並跑 `U17` 全部測試 |
| `frontend/src/components/brain/ContextBar.tsx`（`U14` 的檔） | 加鈕與 `pickerOpen` | `OPEN-OP16-4`；跑全部既有 brain e2e |

## Environments

| 環境 | 差異 |
|---|---|
| 本機 dev | 無新設定；`LOCAL-DEV.md` 不需更新（不動 `database.py`、`nginx.conf`、`.env.example`、`render-env.sh`） |
| CI（`ui-regression` 短生命週期 stack） | 無新變數；選單 e2e 以 `page.route`／`routeWebSocket` 樁化，請求計數類對正式建置執行（`D-01`） |
| staging（`192.168.10.10`） | 隨既有前端 image 更新，無額外步驟 |

`python3 scripts/validate_env_contract.py` 的六項檢查本單元皆不觸及。
