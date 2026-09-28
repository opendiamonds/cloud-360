# Infrastructure Design — 釐清問題（cost-budget-banner）

> Stage: infrastructure-design（3.4）· Unit: `cost-budget-banner` · B2 · kind 省略 → 全套

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| B2 Bolt 才 merge 路由／register | ADR-C1-08 |
| 同容器 embedded | unit-of-work |
| session dismiss only | nfr-design |

---

## Q1. B2 deploy 策略？

A. **同 staging 一次 deploy**；feature flag 用「是否 import register」+ 路由註冊，非 env toggle。**（建議）**  
B. 第二 frontend 版本。代價：違 embedded。  
C. Not yet defined  

[Answer]: A. **B2 merge 同 deploy**

---

## Plan Approval

- [x] 計畫已核可（Q1=A）
