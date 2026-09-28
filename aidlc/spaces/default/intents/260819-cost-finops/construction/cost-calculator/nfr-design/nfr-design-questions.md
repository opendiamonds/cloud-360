# NFR Design — 釐清問題（cost-calculator）

> Stage: nfr-design（3.3）· Unit: `cost-calculator` · kind: **library**  
> 上游：`../nfr-requirements/`、`../functional-design/`。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| 純函式；禁 httpx／Session／HTTPException | SEC-C-1、BR-C-1 |
| 非法輸入 → `ValueError` | SEC-C-2 |
| Hypothesis PBT 進 CI | nfr-requirements Q2=A |
| NFR-4 不適用本 unit | nfr-requirements Q1=A |

---

## Q1. 邏輯元件圖要拆幾層？

A. **單模組 `cost_calculator.py`**：五個公開函式 + 常數；無子 package。**（建議，對齊 library 邊界）**  
B. 拆 `decimal_utils` / `pie_allocator` 子模組。代價：過早抽象。  
C. Not yet defined  

[Answer]: A. **單模組五函式**

---

## Q2. 安全設計的 CI 具體化？

A. **`validate_repo_contract` 或同 PR 腳本 grep 禁用 import**；unittest Hypothesis 覆蓋 SEC-C-2。**（建議）**  
B. 僅文件宣告。代價：無機械關卡。  
C. Not yet defined  

[Answer]: A. **grep + PBT**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q2=A）
