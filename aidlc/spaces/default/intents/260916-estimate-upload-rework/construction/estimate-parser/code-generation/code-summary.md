# Code Summary — estimate-parser（U1）

> Unit: `estimate-parser` · kind: **library**  
> 計畫：同目錄 `code-generation-plan.md`（6 步，全數完成）  
> Plan Approval：`Approve Plan`（session 已記錄）

## 變更檔案

| 檔案 | 變更 | 對應 |
|---|---|---|
| `backend/requirements.txt` | 新增 `openpyxl==3.1.5` | Step 1、NFR7.1 |
| `backend/cost/estimate_readers.py` | **新增** CSV／XLSX 讀取、雲別標頭分數、欄位對應、32 MiB／5 萬列上限 | BR1.*、NFR3.1 |
| `backend/cost/estimate_parser.py` | **新增** `parse(file_bytes, filename?) → ParseResult` | FR2.*、BR2.*、BR3.1、NFR3.2 |
| `backend/cost/estimate_validator.py` | **新增** `validate(parse_result) → MechanicalCheckResult` | FR4.*、BR4.1–4.4 |
| `scripts/validate_cost_calculator_boundary.py` | 改掃 parser／validator／readers；禁 httpx／requests／sqlalchemy／fastapi | FR2.3、FR9.6、NFR6.1 |
| `backend/tests/test_estimate_parser.py` | **新增** example＋2 Hypothesis PBT | FR2.4、NFR4.1 |
| `backend/tests/test_estimate_validator.py` | **新增** BR4 案例＋1 Hypothesis PBT（合計 ≥3） | FR4.*、NFR4.1 |

**未變更（刻意）**：HTTP／上傳／DB（U2）、查價（U5）、LLM／建議（U7）、前端（U8／U9）、TCMS 手寫。

## 關鍵實作決定

1. **讀取器拆檔** `estimate_readers.py`，由邊界腳本種子目標＋AST 追蹤同套件 import。
2. **NFR3.1**：CSV 以 UTF-8 編碼後位元組長度；XLSX 以 ZIP `file_size` 加總；超出 → `ambiguous`＋空 lines，不 raise。
3. **NFR3.2**：對外例外／reason 僅型別名或固定短語，不含路徑／traceback。
4. **BR1.1 過濾**：CSV 路徑將 azure 分數歸零；XLSX 將 aws／gcp 歸零。
5. **BR4.3**：`statedTotal=0` 採精確相等；否則相對誤差 ≤ 0.5%。

## 測試

| 指令 | 結果 |
|---|---|
| `python3 scripts/validate_cost_calculator_boundary.py` | exit 0（3 檔） |
| `python3 scripts/validate_repo_contract.py` | exit 0 |
| `python3 scripts/validate_env_contract.py` | exit 0 |
| `cd backend && PYTHONPATH=. python3 -m unittest tests.test_estimate_parser tests.test_estimate_validator -v` | 16 OK（含 3 `@given`；R-01～R-03 補測） |

## 與計畫的偏離

無實質偏離。讀取器獨立成 `estimate_readers.py`（計畫允許「同套件讀取器」）。

## 不做（交其他 unit）

上傳魔數／5 MB HTTP、DB 持久化、查價、建議 agent、TCMS 手寫案。
