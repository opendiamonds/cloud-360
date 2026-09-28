# Tech Stack Decisions — cost-calculator

> Unit: `cost-calculator` · library · Q1–Q2=A  
> 上游：`requirements.md` DoD、`project.md` Tech Stack、`../functional-design/`。

## 決策：零新增 runtime 依賴

| 面向 | 決策 | 依據 |
|---|---|---|
| 語言 | Python 3（與 backend 一致） | brownfield |
| 數值 | **`decimal.Decimal`** 全程；出口 `quantize(2, ROUND_HALF_UP)` | ADR-C1-07 |
| 測試 | **`hypothesis`** + `unittest`（已於 `requirements.txt`） | NFR-3、DoD-1 |
| 新 PyPI 套件 | **無** | ADR-C1-01 嵌入式模組 |

## 不引入

| 項目 | 理由 |
|---|---|
| numpy／float 快路 | 違 FR-3 金額精確與 PBT 可比性 |
| pydantic 在 library 內 | 驗證在 API 層；library 用 ValueError |
| 獨立 package 發佈 | embedded library；同 repo import |

## 目錄

`backend/cost/cost_calculator.py`（或 `backend/cost/calculator/` 若 code-gen 拆檔）；測試 `backend/tests/test_cost_calculator*.py`。
