# Infrastructure Design — 釐清問題（cost-calculator）

> Stage: infrastructure-design（3.4）· Unit: `cost-calculator` · kind: **library**  
> 上游：`../nfr-design/`。本 unit 僅產 `cicd-pipeline`（`produces_kinds`）。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| 無獨立 runtime／容器 | unit-of-work embedded |
| PBT 進 CI unittest | nfr-design SEC-C-1 |
| 禁用 import 靜態 gate | nfr-design |

---

## Q1. CI 如何掛載 calculator 測試？

A. **`backend/tests/test_cost_calculator*.py` 隨既有 `python -m unittest discover -s tests` 執行**；另加 repo-contract 腳本檢查禁用 import。**（建議）**  
B. 獨立 workflow。代價：與 team-practices 不一致。  
C. Not yet defined  

[Answer]: A. **unittest discover + grep gate**

---

## Plan Approval

- [x] 計畫已核可（Q1=A）
