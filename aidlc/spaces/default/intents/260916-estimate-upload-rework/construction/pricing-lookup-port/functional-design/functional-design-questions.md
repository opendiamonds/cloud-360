# Functional Design 問答：U5 `pricing-lookup-port`

本 Unit 是 **library**：唯讀目錄價查詢 Port（`PricingLookup`，改造自既有 `pricing_client`）。  
**不含**建議正文／LangGraph 節點（U7）、上傳 API（U2）、憑證注入管線（U4 已做）。

本站釘**行為與邊界**，不寫實作碼。library → 產出 entities／rules／functional-spec／traceability（無 frontend-components）。

## Sources

- **[S1]** U5：`unit-of-work.md` — 擁有 PricingLookup；保留 pricing_sdk／query_parser／YAML 最小集；唯讀（AH-6）；httpx 不得他處直打
- **[S2]** FR5.5–5.7、FR5.9–5.10、FR9.4–9.5、FR9.7；ADR-0018；domain Q8=C／AH-6
- **[S3]** 既有 `pricing_client.fetch_hourly` → `PriceHit|PriceMiss|PriceUnsupported`；磁碟快取 `.pricing_offer_cache/`（24h）；DB `pricing_cache` 已隨 U3 archive
- **[S4]** U4 已就緒：IAM／API key 注入與缺憑證可啟動；執行期查價／降級屬本 Unit
- **[S5]** OQ-DD2：磁碟快取去留交本站定案

---

## Q1 公開 API 形狀（供 U7 按需呼叫）

- **A.** **保留** `cost.pricing_client.fetch_hourly(cloud, sku, region) → PriceHit|PriceMiss|PriceUnsupported` 為正式 Port；文件／邊界腳本稱其為 PricingLookup；必要時加薄 facade／型別別名，不強制改檔名（建議；改動面最小）
- **B.** **更名／新建** `PricingLookup` 類或模組（例：`pricing_lookup.py`），`pricing_client` 變內部或轉發棄用
- **C.** 改成批次 API（一次多 SKU）為唯一入口；單筆查詢刪除
- **X.** Other (please specify)

[Answer]: A — 保留 fetch_hourly 為正式 Port；文件／邊界稱 PricingLookup
---

## Q2 磁碟 offer 快取（OQ-DD2；DB `pricing_cache` 已退場）

- **A.** **保留** `backend/cost/.pricing_offer_cache/` 24h 磁碟快取（僅公開 Bulk／下載路徑）；gitignore 維持；不重建 Postgres 快取（建議；符合 FR9.2 退表、保留既有效能）
- **B.** **移除**磁碟快取；每次查價打上游（簡化，但變慢、易撞 rate limit）
- **C.** 改為**行程內** LRU／TTL 記憶體快取，不寫磁碟
- **X.** Other (please specify)

[Answer]: A — 保留 24h 磁碟 offer 快取；不重建 Postgres pricing_cache
---

## Q3 AWS 查價優先序與 `COST_PRICING_USE_SDK`（FR5.6／FR9.4／FR5.10）

- **A.** SDK（Query API）**預設可啟用**（FR9.4：自 `0` 改為可啟用）；有 IAM 憑證且開關開 → SDK；失敗或無憑證 → **降級**公開 Bulk；再失敗 → `PriceMiss`／`unsupported`（不得 raise 讓 U7 崩潰）（建議）
- **B.** 永遠只用公開 Bulk；SDK 程式碼保留但不在執行期啟用
- **C.** 有憑證時 SDK 失敗則**硬失敗**（違反 FR5.10，不建議）
- **X.** Other (please specify)

[Answer]: A — SDK 可啟用；失敗／無憑證降級 Bulk → miss；不讓 U7 崩潰
---

## Q4 `warm_aws_pricing_cache.py`（FR9.7）

U3 後退場後，repo 內可能已無此腳本或仍殘引用。

- **A.** **本 Unit 盤點**：若腳本／文件仍引用 `price_cache`／DB 快取 → 改為暖磁碟快取或呼叫 Port，或刪除死腳本並清引用；以「缺憑證可跑、不阻啟動」為準（建議）
- **B.** 強制重建 warm 腳本（即使目前已刪）
- **C.** 本 Unit 不碰腳本／文件，只改 Port 本體
- **X.** Other (please specify)

[Answer]: A — 本 Unit 盤點 warm 腳本／死引用並修或刪
---

## Q5 AH-6「不得回寫明細」如何結構性守住

- **A.** **邊界腳本／import 規則**：禁止 `estimate_intake_*`／ORM 寫入路徑 import PricingLookup；允許 `cost_advice`／U7 與測試 import；CI 擋違規（建議；與 FR2.3／calculator boundary 同形）
- **B.** 僅文件＋code review 約定，無機電檢查
- **C.** Port 回傳型別刻意不含可寫入 ORM 的欄位，並在 service 層 assert 無寫回（執行期）
- **X.** Other (please specify)

[Answer]: A — CI 邊界腳本擋 intake 寫入路徑 import PricingLookup
---

## Q6 GCP／Azure 與「禁帳單 API」執行期界線

- **A.** GCP：Catalog＋API key（缺 key → miss／略過）；Azure：Retail 公開；**程式碼與設定不得新增** Cost Explorer／Cost Management／Billing Export 客戶端；allowlist host／API 名稱寫進規則＋測試（建議）
- **B.** 僅文件禁止，不測 allowlist
- **C.** 本 Unit 只做 AWS；GCP／Azure 查價延後
- **X.** Other (please specify)

[Answer]: A — GCP Catalog／Azure Retail＋禁帳單 API allowlist 測試
---

## Consolidated Summary Confirmation


**U5 `pricing-lookup-port` 行為定案**

| 項 | 定案 |
|---|---|
| 範圍 | **library**：唯讀目錄價 Port；無 SPA／建議正文 |
| 公開 API | 保留 `fetch_hourly`；稱 PricingLookup（Q1=A） |
| 快取 | 保留 24h `.pricing_offer_cache/`；不重建 DB（Q2=A） |
| AWS | SDK 可啟用；降級 Bulk；失敗不崩 U7（Q3=A） |
| warm 腳本 | 本 Unit 盤點修／刪死引用（Q4=A） |
| AH-6 | CI 邊界擋 intake 寫入路徑 import（Q5=A） |
| 三雲／禁令 | Catalog／Retail＋帳單 API allowlist 測（Q6=A） |

**將產出**：entities.md、rules.md、functional-spec.md、traceability.json（無 frontend-components）。

**後果**：code-gen 強化 Port／降級／SDK 預設、邊界腳本、快取與 warm 清理；不得讓查價失敗中止建議流程。

[Answer]: Looks correct
