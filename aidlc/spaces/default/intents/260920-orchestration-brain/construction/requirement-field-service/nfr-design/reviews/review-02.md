## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元 nfr-design 六份設計在查詢次數、併發清空、九列授權矩陣、log 不記值與 ADR-0006 四面向上自洽，且承接 nfr-requirements 的 NFR20.x。主要問題是凍結的設計留有前次 review-01 已提、但設計本文未回改的缺口，而已落地的程式多半已修正且比設計正確。唯一需要人裁決的是 R-01：設計宣稱的「僅掛在本 router 的框架 422 處置」沒有指名機制，程式實際採另一條路徑，設計與程式不一致。其餘為 Minor，不阻擋。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | nfr-design/security-design.md 第五節；logical-components.md 的 requirement_field_router 列 | 前次 review-01 R-01 已提。設計寫「框架驗證錯誤以僅掛在本 router 的處置轉成同一形狀」，但 APIRouter 沒有 router 範圍的 exception handler，設計未指名可行機制（自訂 route_class 或函式內自行驗證）。已落地的 backend/services/requirement_field_router.py（第 33-48 行說明）改為在函式內自行驗證、讓本 router 的 422 都來自領域例外，並明寫不改全域 handler。程式這一邊是對的，設計本文仍是不可實作的陳述。 | 以修訂或 corrections 檔把第五節改寫成程式實際採用的機制，並說明路徑參數非整數等框架層 422 仍走框架預設形狀（若如此）。 | New |
| R-02 | Minor | nfr-design/performance-design.md 第二節（SQL 表與方言段） | 前次 review-01 R-04、R-07(2) 已提。設計仍寫 cleared_at 與 updated_at 取 now()，並以 session.bind.dialect.name 選方言。程式 requirement_field_service.py 第 33-35、90-91 行已改為呼叫端傳入 now、並用 session.get_bind()。程式是對的。 | 把設計改成「時間戳由 Python 端可注入傳入」與 session.get_bind()，避免下游依設計重蹈覆轍。 | New |
| R-03 | Minor | nfr-design/reliability-design.md 第三節（收斂敘述步驟 1-3）；logical-components.md 第三節爆炸半徑 | 前次 review-01 R-06 已提。設計未提 lock_timeout、users 表鎖，也沒說明非 NULL 舊值的處置。schema_rbac.sql 第 735-783 行已加 lock_timeout 5s，並以 NOTICE 回報被清掉的筆數，但 USING NULL 仍是靜默丟棄非空值（有 NOTICE，非大聲失敗）。設計與 NFR20.25「大聲失敗」的原則，與程式的實際取捨之間未對齊。 | 設計補寫 lock_timeout 與 users 鎖，並明寫「非空舊值清掉並以 NOTICE 回報」是刻意取捨（因無程式寫過舊欄位），或改成遇非空值即 RAISE EXCEPTION。 | New |
| R-04 | Minor | nfr-design/security-design.md 第二節（九列矩陣） | 前次 review-01 R-03 已提。矩陣仍缺：列 ② 未規定非成員須是「另一個專案的成員」；缺 project_admin 且有 K4.edit 的正向寫入列（列 ⑤ 只測被全域層擋下）；缺 Platform_Admin 非成員列以鎖住「無 bypass」。列 ② 與 ⑦ 並陳也等於允許有 K4 權限者以 403/404 差異枚舉 system id，設計未說明是否接受。 | 補三列矩陣或明寫不補的理由，並在 BR41.3 旁記下枚舉風險的處置。 | New |
| R-05 | Minor | nfr-design/reliability-design.md 第三節（驗證 A-D） | 前次 review-01 R-02 已提。設計 A-D 只走 psql -f 路徑，沒有執行 run_meta_schema_migration.py 的後條件。ci.yml 第 396-424 行已新增 U20 步驟並安裝 backend requirements，顯示程式端已補強，但設計文字仍描述 psql-only，且未說明 fixture 如何跨 verify_meta_schema.sql 的 ROLLBACK 保留列。 | 設計補上 CI 實際步驟與 fixture 做法。 | New |
| R-06 | Minor | nfr-design/reliability-design.md 第一節（另一個 session 重讀） | 前次 review-01 R-07(1) 已提。tests/helpers.py 以 StaticPool 讓所有 session 共用同一條連線，「換 session 才驗得出回滾」的理由不成立；測試能否變紅取決於是否真的呼叫 rollback。 | 把理由改為「斷言 rollback 被呼叫且重讀值不變」。 | New |
| R-07 | Minor | nfr-design/reliability-design.md 第三節；security-design.md 第七節 | 前次 review-01 R-05 已提。設計未寫部署順序：deploy.yml 合併即部署新後端，而收斂是手動步驟，收斂前帶 on_behalf_of 的寫入會因欄位仍為 integer 而 500。OPEN-RF20-8 也未帶入本站的開放項。 | 在設計與 DEPLOY.md 2.2.9 寫明先收斂、後上線，並把 OPEN-RF20-8 列入開放項。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀碼 requirement_field_service.py、requirement_field_router.py、schema_rbac.sql 735-783、ci.yml 396-424 | 程式已修正前次多項發現 | 設計與程式不一致，R-01 至 R-05 以程式為準，設計本文待回補 |
| 表格列管線數檢查（每列 7 個未跳脫 \|） | 目視確認通過 | 格式合規 |
