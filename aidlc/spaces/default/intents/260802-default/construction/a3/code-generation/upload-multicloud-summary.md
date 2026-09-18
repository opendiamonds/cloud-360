# A3 上傳＋多雲 — Code Generation Summary

> Branch: `luojingting/feat/a3-feature-updates`  
> FD: `construction/a3/functional-design/upload-multicloud-fd.md`  
> Requirements: `inception/requirements/a3-upload-multicloud-requirements.md`


### 已實作

| 項目 | 說明 |
|---|---|
| 上傳評核 | Assessment 上傳 `.drawio`／`.xml`；可選建檔；未建檔寫入 `xml_snapshot`＋`diagram_id` NULL |
| Workspace 上傳 | 載入畫布 XML，再走既有儲存／WA |
| Provider 偵測 | `detect_provider`＋API；FE 可覆寫 |
| 多雲規則 | `wa-aws-mvp-1`／`wa-gcp-mvp-1`／`wa-azure-mvp-1`；移除 `unsupported` 短路 |
| Per-cloud Lens | `wa_lenses.provider`；GET/PUT `?provider=`；無 DB 列時 fallback 共用檔案 Lens |
| 架構圖預覽 | Assessment 選圖／上傳後以 diagrams.net viewer 唯讀預覽（`DiagramPreviewPanel`） |
| PDF 附圖 | 匯出時以 embed 匯出 PNG，獨立一頁「架構圖（對照）」；中文標題以 Canvas 繪製避免亂碼 |
| Schema／DEPLOY | `schema_rbac.sql`＋`_ensure_a3_schema`＋`DEPLOY.md` |

### 相關 A1 增量（同分支）

| 項目 | 說明 |
|---|---|
| 下載 `.drawio` | Workspace 畫布工具列「下載 .drawio」；包成 mxfile；唯讀亦可下載 |

### 主要程式路徑

| 層 | 路徑 |
|---|---|
| BE 規則 | `backend/services/wa_rule_engine.py` |
| BE 評核 | `backend/services/review_orchestrator.py`、`review_router.py` |
| BE Lens | `backend/services/lens_service.py`、`lens_router.py` |
| FE Assessment | `frontend/src/pages/AssessmentPage.tsx` |
| FE 預覽／PDF | `DiagramPreviewPanel.tsx`、`exportDiagramPng.ts`、`exportReviewPdf.ts`、`diagramViewer.ts` |
| FE 下載 | `frontend/src/utils/downloadDrawio.ts`、`DrawioCanvas.tsx` |

### 測試

- `tests/test_wa_rule_engine.py`：AWS 回歸＋GCP／Azure／detect

### 手動驗收建議

1. Assessment 上傳 AWS／GCP／Azure 風格 draw.io，確認偵測、預覽與評核可完成  
2. 不勾建檔 → 歷史可看、工作區無新圖  
3. Lens 標準切換雲別儲存後，新評核讀對應 Lens  
4. 下載 PDF：最後一頁有架構圖；標題中文正常  
5. Workspace「下載 .drawio」可被 diagrams.net／draw.io 開啟  
6. 既有 AWS 評核／PDF 文字報告不回歸  
