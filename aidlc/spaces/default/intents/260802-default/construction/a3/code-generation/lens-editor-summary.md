# A3 Lens Editor — Code Generation Summary

> Unit `U-A3` 增量 · FD: `construction/a3/functional-design/lens-editor-fd.md`


### 已實作

| 項目 | 說明 |
|---|---|
| DB | 表 `wa_lenses`；`models.WaLens`；`_ensure_a3_schema` 補建 |
| 部署 | `schema_rbac.sql` 區塊 E；`DEPLOY.md` §2.2.2；`schema-rbac-notes.md` |
| 引擎 | `resolve_active_lens(db)` DB 優先、檔案 fallback；`start_review` 已改用 |
| API | `GET/PUT /api/architecture/lens/active`；template／suggest；需 **A3.review** |
| 保護 | 既有題 `riskRules` 儲存時強制保留；每柱 ≥1 題驗證 |
| FE | Assessment「Lens 標準」分頁（`can('A3','review')`）+ `LensCriteriaEditor` |
| 測 | `backend/tests/test_lens_service.py` |

### 手動驗收

1. 以具 A3 **審核** 的帳號（預設 `fiona`／Security_Reviewer＝VER）登入 → Assessment → **Lens 標準**  
2. 改一題文案／新增題／刪題（每柱留 ≥1）→ 儲存  
3. 發起新評核，確認行為反映新標準；舊歷史分數不變  
4. 無 A3 審核權角色：無「Lens 標準」分頁；寫入 API 應 403（可在 Admin 矩陣勾選審核後開放）  

### Extension

| Extension | Status |
|---|---|
| bilingual-docs | compliant（本摘要） |
| security/baseline | compliant（A3.review 閘） |
| property-based | N/A 本期（unit 覆蓋驗證／preserve） |
