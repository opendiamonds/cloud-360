# Performance Requirements — legacy-cost-retirement

> Unit: `legacy-cost-retirement`（U3）· **N/A**

本 unit 為破壞性退場（刪 HTTP／rename 表），不新增熱路徑或延遲目標。NFR1（端到端 3–5 分鐘）屬 U7／整體流程，非本 unit 獨責。

rename 遷移應在部署視窗內完成；無獨立 p95 指標。

<!-- confirmed: Looks correct -->
