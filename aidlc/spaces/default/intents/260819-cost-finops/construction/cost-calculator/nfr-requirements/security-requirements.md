# Security Requirements — cost-calculator

> Unit: `cost-calculator` · library · Q1–Q2=A  
> 上游：`../functional-design/business-rules.md`、`requirements.md` NFR-3／NFR-5／ADR-0006。

## ADR-0006 四面向（本 unit）

| 面向 | 判定 | 處置 |
|---|---|---|
| IAM | **不適用** | 無 HTTP／無 RBAC；授權在 `cost-api` router |
| Encryption | **不適用** | 無持久化；不處理 credential |
| Network exposure | **不適用** | 無 socket；禁止 import `httpx`（BR-C-1） |
| Audit logging | **不適用** | 無 side effect；稽核在 service 層 |

## SEC-C-1 模組邊界（NFR-3 hard constraint）

**需求**：`backend/cost/cost_calculator.py`（或同 package 純函式模組）**不得** import `httpx`、`sqlalchemy.orm.Session`、`fastapi.HTTPException`。

**驗證**：CI 腳本或 grep 契約（與 `validate_repo_contract` 同 PR）；違反即 fail。

## SEC-C-2 輸入不可信時的行為

**需求**：非法 `hours`／`hourly` 丟 `ValueError`，不 silent clamp（FD Q3=A）。避免 service 誤把 bug 當合法 0。

**驗證**：Hypothesis `@given` 非法域期望 `ValueError`。

## SEC-C-3 無秘密處理

**需求**：模組不讀 env 價目 API key（定價在 `pricing_client`）；calculator 常數僅 `30`／`730`。

**依據**：FR-2.5、分層決策 ADR-C1-01。
