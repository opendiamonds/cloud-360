# Security Design — cost-calculator

> Unit: `cost-calculator` · library · 承接 `../nfr-requirements/security-requirements.md`

## 1. 威脅模型

| 威脅 | 評估 | 設計回應 |
|---|---|---|
| 模組被誤用為 HTTP 客戶端 | 低（分層） | **編譯期／CI 邊界**：禁止 import `httpx`、`sqlalchemy.orm.Session`、`fastapi.HTTPException` |
| 非法輸入 silent 通過 | 中（service 信任） | 公開函式對非法域 **`ValueError`**，不 clamp |
| 秘密外洩 | 不適用 | 不讀 env；常數僅 `30`／`730` |
| IAM 繞過 | 不適用 | 授權在 `cost-api` router／service |

## 2. 模組邊界（SEC-C-1 具體化）

```
backend/cost/cost_calculator.py   # 唯一允許的 calculator 入口
  ├── 允許：decimal.Decimal, typing, math（若需）
  └── 禁止：httpx, requests, sqlalchemy*, fastapi*
```

**CI 契約**（同 PR 與 `validate_repo_contract` 類腳本）：

```bash
# 伪示意 — code-generation 實作為 Python 腳本或 ripgrep gate
rg '^(import|from)\s+(httpx|sqlalchemy|fastapi)' backend/cost/cost_calculator.py && exit 1
```

## 3. 輸入驗證設計

| 函式 | 拒絕條件 | 行為 |
|---|---|---|
| `hourly_from_monthly` | `M < 0` 或非有限 | `ValueError` |
| `line_subtotal` | `hourly < 0` 或非有限；`hours` 非 int 或 `< 0` | `ValueError` |
| `total_priced` / `pie_buckets` | 列內 hourly 非法（若提供） | 由呼叫端保證；calculator 只過濾 status |

**不**在此層做 HTTP 422 映射——`cost_service` 在 router 前驗 hours 0–24。

## 4. PBT 作為安全關卡

Hypothesis 性質（FD business-rules §PBT）：

- 覆寫列與官方價列加總規則一致
- `pie_buckets` 四類之和 **等於** `total_priced`（量化後）
- 非法 `@given` 域期望 `ValueError`

失敗 = CI 紅（`python -m unittest discover`）。

## 5. 稽核與網路

| ADR-0006 面向 | 設計 |
|---|---|
| IAM | N/A — 無端點 |
| Encryption | N/A — 無持久化 |
| Network | N/A — 無 socket |
| Audit | N/A — 無 side effect |

## 6. Code Gen 檢查清單

- [ ] 五函式簽名與 FD `business-logic-model.md` 一致
- [ ] 檔案頂部無禁用 import
- [ ] `test_cost_calculator*.py` 含 PBT + 非法輸入案例
