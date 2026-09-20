# Functional Design — 釐清問題（cost-api）

> Stage: functional-design（Construction 3.1，inline）· Unit: `cost-api` · Kind: **service**
> 上游：`unit-of-work.md`、`unit-of-work-story-map.md`、`requirements.md`、`components.md`、`component-methods.md`、`services.md`。
> 依賴 unit：`cost-schema-rbac`（表）、`cost-calculator`（純函式）。
> **成本揭露**：5 題。答完產出 business-logic-model／business-rules／domain-entities。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 第一段 HTTP 清單；不註冊 `PUT budget`／`GET /banner` | ADR-C1-08、B1 DoD |
| 403／404／422 語意 | `component-methods.md`、`team-practices` |
| `PriceHit`／`PriceMiss`／`PriceUnsupported` | `component-methods.md` |
| 快照欄位與 `lines[].status` 四值 | `component-methods.md` |
| 禁止 `parse_diagram_summary`、WA 摘要 | `components.md`、FR-1 |
| 快取 TTL 24h | ADR-C1-04 |
| calculator 簽名與捨入 | `cost-calculator` FD（READY） |

協作故事：C1-1～C1-5 主責；C1-6／C1-7 第二段（本 unit 第一段不掛 budget／banner 路由）。

---

## Q1. `pricing_client` 逾時與重試？

> `services.md` 留給本站。NFR-4 5 秒是整包 snapshot，不是單 SKU。

A. **單次 HTTP：connect+read 各 3s；不重試**；逾時／非 2xx／解析失敗 → `PriceMiss`。**（建議）**  
B. 3 次指數退避。代價：snapshot 易超 5s。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **單次 HTTP connect+read 各 3s；不重試 → PriceMiss**

---

## Q2. 圖可見性與 404／403 順序？

A. **先載入 diagram_id**；不存在或 `_user_can_access_diagram` 為 false → **404**；可見但無 `C1.view` → **403**（沿用 `collab_router._user_can_access_diagram`）。**（建議）**  
B. 無 C1.view 一律 403（即使圖不存在）。代價：洩漏存在。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **404 再 403；重用 collab 可見性 helper**

---

## Q3. 列 `status` 判定優先序？

A. **`hourly_override` 非空 → `manual_override`**；否則 `sku_override` 或 mapper 唯一命中後：有 region 且 `PriceHit` → `priced`；`PriceMiss` → `price_fetch_failed`；`PriceUnsupported` 或無 SKU → `unpriced`。**（建議）**  
B. 有 override 仍先打官方價。代價：違 FR-1.4／C1-5。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **override 優先；三態定價結果映射如上**

---

## Q4. `coverage` 欄來源？

> `component-methods.md`：雲別清單 + `official_list`｜`manual_override_only`。

A. **啟動載入 `backend/cost/pricing_coverage.yaml`**（靜態；改檔需部署）；GET snapshot 原樣回傳。**（建議）**  
B. 執行期依本次 lines 推算。代價：與「定價假設凍結清單」不一致。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **pricing_coverage.yaml 靜態清單**

---

## Q5. 第一段未註冊路由行為？

A. **`PUT .../budget` 與 `GET /banner` 不在 router 註冊** → TestClient 得 **404**；快照 `budget=null`、`overspent=false`（calculator `is_overspent`）。**（建議，對齊 B1 DoD）**  
B. 註冊但恒 403。代價：與 ADR-C1-08「不 include」字面衝突。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **未註冊 → 404；快照欄位恒 null/false**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q5=A）
