# NFR Requirements — 釐清問題（cost-calculator）

> Stage: nfr-requirements（3.2）· Unit: `cost-calculator` · kind: **library**
> 上游：`../functional-design/`、`requirements.md` NFR-3／NFR-5。
> **成本揭露**：2 題。本 unit 不產 performance／scalability／reliability（`produces_kinds`）。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| 純函式；禁 httpx／Session／HTTPException | NFR-3、BR-C-1 |
| Hypothesis 性質清單 | functional-design business-rules §PBT |
| Decimal 兩位 HALF_UP | ADR-C1-07、FD Q1=A |
| 技術堆疊 Python + hypothesis | `project.md`、DoD item 1 |

---

## Q1. NFR-4（5 秒成本頁）本 unit 怎麼寫？

A. **標為不適用**；延遲預算由 `cost-api`（snapshot 編排）與 `cost-ui`（渲染）承接，calculator 只保證 O(n) 純 CPU。**（建議）**  
B. 為五函式訂 p99 微秒預算。代價：CI 無量測、虛假精確。  
C. Not yet defined  

[Answer]: A. **不適用；O(n) 註記即可**

---

## Q2. NFR-3 的 CI 關卡？

A. **`python -m unittest discover` 必須含 `test_cost_calculator*.py` Hypothesis 案例；失敗 = CI 紅**；另加靜態檢查模組內無禁用 import。**（建議，對齊 team-practices）**  
B. 僅手動跑 PBT。代價：違 ADR-0006 hard constraint。  
C. Not yet defined  

[Answer]: A. **unittest + Hypothesis 進 CI；禁用 import 靜態檢查**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q2=A）
