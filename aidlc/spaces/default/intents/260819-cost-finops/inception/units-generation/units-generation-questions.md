# Units Generation — 釐清問題

> Stage: units-generation（Inception 2.7，inline）· Depth: Standard · Scope: mvp
> Intent: `260819-cost-finops`
> 作答：在每題 `[Answer]:` 後填選項字母。
> **成本揭露**：本題組原 4 題，另加 Q5 解消 OpenAPI 矛盾。答完先核可拆分計畫，再產出 DAG。本站**不排施工順序**（那是 Delivery Planning）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 模組化單體；`backend/cost/` + `/api/cost` + `/cost` 頁 | [decisions] ADR-C1-01 |
| 四權 `C1`／`C1h`／`C1r`／`C1b`／`C1o`；須只補缺失種子列 | [decisions] ADR-C1-02 |
| 兩張狀態表＋快取表＋稽核表 | [decisions] ADR-C1-03／04／06 |
| 純函式 calculator；pricing_client 三分 Hit／Miss／Unsupported | [methods]／[services] |
| 第一段不註冊預算與 `/banner` | [decisions] ADR-C1-08 |
| 部署仍是既有 backend＋frontend 容器 | [kb] architecture |
| 不把 LLM 超支建議放進本輪 unit | [rm] 筆記 |

## Sources

- [components] `../application-design/components.md`
- [methods] `../application-design/component-methods.md`
- [services] `../application-design/services.md`
- [dep] `../application-design/component-dependency.md`
- [decisions] `../application-design/decisions.md`
- [req] `../requirements-analysis/requirements.md`
- [stories] `../user-stories/stories.md`

---

## Q1. Unit 邊界怎麼切？

> Construction 會為每個 unit 建 `construction/<name>/`。切太粗會讓第一段與第二段無法分開驗收；切太細會讓 OpenAPI 契約裂成很多小 PR。

A. **五個 unit（建議）**  
   1. `cost-schema-rbac`（spec）：四表＋種子＋只補缺失列  
   2. `cost-calculator`（library）：純函式＋PBT  
   3. `cost-api`（service）：router／service／extractor／mapper／pricing_client＋第一段 HTTP  
   4. `cost-ui`（ui）：Sidebar、`CostPage`、圓餅、時數、產圖 CTA  
   5. `cost-budget-banner`（省略 kind，完整設計矩陣）：第二段預算 API＋`GET /banner`＋Layout 橫幅＋成本頁「已超支」  
B. **三個 unit**：`cost-backend`（schema+calculator+api）、`cost-ui`、`cost-budget-banner`。代價：calculator 無法獨立合 PBT 閘。  
C. **一個 unit 包全部 C1**。代價：第一段無法單獨合 Construction 閘。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. 五個 unit（建議）

---

## Q2. 可平行的拓樸要不要顯式畫出來？

> 2.7 只描述「誰依賴誰」。`cost-schema-rbac` 與 `cost-calculator` 互不依賴，DAG 上可以是兩個根。

A. **顯式兩個根**：schema 與 calculator 的 `depends_on: []`；api 依賴兩者；ui 依賴 api；budget-banner 依賴 api 與 ui。**（建議）**  
B. **全部串成一條鏈**（schema→calculator→api→ui→banner）。代價：假裝有依賴，2.8 無法選擇平行。  
C. **不畫根節點，只寫「都依賴單體」**。代價：sensor 的 yaml 邊無法計算 fan-out。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. 顯式兩個根：schema 與 calculator 的 `depends_on: []`；api 依賴兩者；ui 依賴 api；budget-banner 依賴 api 與 ui。**（建議）**

---

## Q3. API 與 UI 之間的契約？

> ui unit 不能在沒有穩定 HTTP 形狀時實作 Playwright。

A. **以 `openapi.json` 的 `/api/cost*` 為契約**（methods.md 的 snapshot／PUT 形狀）；ui 用 generated `api.d.ts`。**（建議）**  
B. **手寫一份平行 TypeScript 型別，不綁 OpenAPI**。代價：與 CI drift 檢查對不上。  
C. **ui 直接 import Python 型別**。不可行。  
D. Not yet defined  
X. Other (please specify)

[Answer]: B（初選）。**Q5=A 覆寫為 A**：以 `openapi.json` 的 `/api/cost*` 為契約；ui 用 generated `api.d.ts`。

---

## Q4. 部署模型（邏輯 unit vs 執行期）？

A. **全部 embedded**：同一個 FastAPI process、同一個 SPA bundle；unit 只是邏輯 Module。**（建議，也是唯一與 ADR-C1-01 相容的選項）**  
B. **cost-api 獨立微服務**。違反已核可 application-design。  
C. **前端獨立 repo**。超出本 intent。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. **全部 embedded**：同一個 FastAPI process、同一個 SPA bundle；unit 只是邏輯 Module。**（建議，也是唯一與 ADR-C1-01 相容的選項）**

---

## Q5. 矛盾解消：Q3=B 與已核可的 OpenAPI 契約

> **偵測到的矛盾**（stage-protocol.md §3 強制檢查）：
>
> | 來源 | 內容 |
> |---|---|
> | Q3=B | cost-ui 手寫 TypeScript 型別，不綁 OpenAPI |
> | [methods] 慣例 | 「OpenAPI dump 與 `frontend/src/types/api.d.ts` 同步（CI `--check`）」 |
> | [components] | 「前端型別跟著 OpenAPI」 |
> | ADR-C1-01 | OpenAPI 新 tag `cost`；`dump_openapi.py --check` 為既有 CI |
>
> 若不釐清，DAG 會同時寫「ui 不綁 OpenAPI」與「Construction 必須通過 OpenAPI drift 閘」。

A. **改回 Q3=A**：cost-ui 用 generated `api.d.ts`；backend 仍 dump OpenAPI（與已核可設計一致）。**（建議）**
B. 維持 Q3=B：cost-ui 手寫型別對齊 `component-methods.md`；backend 仍 dump OpenAPI 給 CI，但不強制前端 generated types（接受漂移風險）
C. 維持 Q3=B 且 `/api/cost*` 不進 OpenAPI dump（違反既有 CI 與 ADR-C1-01）
D. Not yet defined
X. Other (please specify)

[Answer]: A. **改回 Q3=A**：cost-ui 用 generated `api.d.ts`；backend 仍 dump OpenAPI（與已核可設計一致）。

---

## Plan Approval

[Answer]: Approve Plan
