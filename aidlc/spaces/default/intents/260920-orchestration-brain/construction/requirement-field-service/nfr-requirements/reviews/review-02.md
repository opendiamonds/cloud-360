## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U20 requirement-field-service 的 NFR Requirements 補審。五個類別皆有二元判準，ADR-0006 四面向各有落點且與 functional-spec 第七節一致；K4 種子列（rbac_seed_data.py:349-359）逐列核對：view 為真者 8 個、edit 為真者 4 個，與 security-requirements.md 第〇節相符，unit-of-work.md:308 的 U20 列也相符。前次 review-01 的 R-01 至 R-08 全部仍留在凍結的 nfr-requirements 產出裡（產出檔 mtime 早於 review-01）。已落地的程式多半已超前吸收這些發現（見各列的「程式」說明），所以風險在於文件與程式分歧，不是實作缺口。仍有一項 Major（授權矩陣缺寫入側非成員列），其餘為 Minor，未發現 Critical，故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/requirement-field-service/nfr-requirements/security-requirements.md > NFR20.8 七列矩陣與突變驗證 | 前次 review-01 R-01 已提。矩陣中「非該專案成員 → 403」只出現在列 2 且明寫為 GET，寫入側（PUT／DELETE）的成員判定（BR41.4）沒有任何一列；突變驗證也只要求拿掉 BR41.4 時列 2 變紅。STRIDE 的 T 與 E 兩格宣稱由 NFR20.8 處置，但寫入路徑漏了成員判定時七列仍全綠。列 7（不存在的系統 → 404）未指明角色，角色無 K4.view 時 BR41.2 先於存在性檢查，會得 403 而非 404。程式：backend/tests/test_requirement_field_http.py:81 的 test_H1_twelve_row_allow_deny_matrix 為十二列，test_H7（第 274 行）涵蓋 project_admin 與 member，實作側看來已補；但設計文件仍是七列，下游照文件驗收會漏。 | 把 NFR20.8 改為與 test_H1 的十二列一致，至少新增：有 K4.edit 但非該專案成員 → PUT 與 DELETE 皆 403 且寫入敘述數為 0；project_admin 與 member 各一例 PUT 為 200；列 7 註明角色為有 K4.view 的成員；突變驗證加上只拿掉寫入路徑成員判定時該列變紅。 | New |
| R-02 | Minor | construction/requirement-field-service/nfr-requirements/performance-requirements.md > NFR20.4、NFR20.5 | 前次 review-01 R-02 已提。NFR20.4 的判準「INSERT／UPDATE 敘述各寫入請求恰為 1」字面不可滿足：單一 upsert 只是一條 INSERT ... ON CONFLICT 敘述，UPDATE 計數為 0。NFR20.4／20.5 要求寫入無 SELECT 並回傳 FieldView，隱含必須用 RETURNING（SQLite 須 3.35 以上），文件未寫；BR43.2 的空字串即清空會讓同一個 PUT 走 clear 路徑而多一次讀取。程式：requirement_field_service.py:15 的表格已寫成 upsert 為 1 條敘述並用 RETURNING，clear 為單一條件式 UPDATE，與設計文字不同。 | 改為「對該表恰 1 條寫入敘述」；寫明以 RETURNING 取回列與 SQLite 版本前提；判準限定非空值寫入，空值寫入另列為走 clear 語意。以程式為準。 | New |
| R-03 | Minor | construction/requirement-field-service/nfr-requirements/security-requirements.md > NFR20.11；reliability-requirements.md > NFR20.26 | 前次 review-01 R-03 已提。兩條判準要求 mock 拋例外後請求非 2xx／回 5xx，但 TestClient 預設 raise_server_exceptions=True，例外會直接在測試中重拋，無法斷言回應本體。程式：test_requirement_field_http.py:255-270 已用 raise_server_exceptions=False，測試端已正確。 | 在兩條判準加註以 TestClient(app, raise_server_exceptions=False) 取得 500 回應。 | New |
| R-04 | Minor | construction/requirement-field-service/nfr-requirements/scalability-requirements.md > NFR20.16、NFR20.18；reliability-requirements.md > NFR20.24、NFR20.25 | 前次 review-01 R-04 已提。測試走 in-memory SQLite，無 foreign_keys pragma，NFR20.16「系統刪除後列數為 0」在 SQLite 不會級聯；NFR20.18 依賴 CHECK 約束，須由 BR47.4 的 ORM 模型宣告才有效，文件只提唯一鍵；NFR20.24 的轉型、pg_constraint 檢查是 PostgreSQL 專屬，條文只寫「一個測試或 CI 步驟」而未指名載體；DEPLOY.md 的 psql -f 路徑不跑腳本後條件，NFR20.25 只覆蓋腳本。 | NFR20.16 指明需啟用 foreign_keys pragma 或改由 CI 的 PostgreSQL 步驟驗證；BR47.4 一致性測試明列 CHECK；NFR20.24 指名載體；說明 psql 路徑的後條件由誰承擔。 | New |
| R-05 | Minor | construction/requirement-field-service/nfr-requirements/performance-requirements.md 檔頭；traceability.json > upstream_ids | 前次 review-01 R-05 已提。檔頭稱比照 U19「以單元號命名」另立 parent id，但先例被誤述（U19 取下一個整數 NFR12）。對 inception 目錄全文搜尋 NFR20 命中為 0，requirements.md 沒有回補 NFR20 與 NFR8.120，也沒有 OPEN 項指派。traceability.json 的 upstream_ids 把本單元自己新增的 NFR20.1 至 NFR20.32 列為上游。 | 更正先例敘述；新增 OPEN 項指派回補 NFR20 與 NFR8.120 到 requirements.md；upstream_ids 只留 NFR1 至 NFR11 與 NFR8。 | New |
| R-06 | Minor | construction/requirement-field-service/nfr-requirements/security-requirements.md > NFR20.10 | 前次 review-01 R-06 已提。把「請求本體帶 updated_by 時拒絕或忽略」留給 code-generation，會改變 OpenAPI 契約與 BR46.4 的 422 形狀。程式：requirement_field_types.py:86、95 已選定 extra="forbid" 加 strict，帶 updated_by 回 422；文件仍寫二擇一，兩邊不一致。 | 文件改為單一分支（程式為準：未宣告欄位回 422），並把測試寫成單一分支。 | New |
| R-07 | Minor | construction/requirement-field-service/nfr-requirements/security-requirements.md > 第一節資料分類 | 前次 review-01 R-07 已提。「不含 PII、憑證或 token」是對人填自由文字（至多 2000 字、無內容過濾）的斷言而非保證；「at rest 沿用既有 volume」未建立 encryption 結論，對照 ADR-0006 encryption 面向等於沿用既有帶過。 | 改為「預期不含但不強制」，明言 log 與錯誤回應不含值是唯一洩漏緩解；at rest 一句如實描述現況。 | New |
| R-08 | Minor | construction/requirement-field-service/nfr-requirements/reliability-requirements.md > NFR20.22；scalability-requirements.md > NFR20.18 | 前次 review-01 R-08 已提。清空若為先讀再更新，兩個併發 DELETE 會重設 cleared_at 與 updated_by，違反冪等；NFR20.18 的不加鎖只論證清空對寫入，未涵蓋清空對清空。程式：requirement_field_service.py:182 已用 WHERE value IS NOT NULL 的單一條件式 UPDATE，實作正確，文件未記載。 | 在 NFR20.22 明寫清空必須是帶 value IS NOT NULL 條件的單一 UPDATE，並補併發清空的判準。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| rbac_seed_data.py:349-359 K4 列計數 | view 為真 8、edit 為真 4 | 與 security-requirements.md 第〇節一致，引用與事實皆正確 |
| unit-of-work.md:308 | U20 列，embedded | 與 NFR 檔「零新進程」引用一致 |
| grep NFR20 於 inception 目錄 | 0 命中 | 證實 R-05：NFR20 未回補上游 requirements |
| 程式抽查（service／types／http 測試） | 多數前次發現已在程式落地 | 風險為文件與程式分歧，不是實作缺口 |
