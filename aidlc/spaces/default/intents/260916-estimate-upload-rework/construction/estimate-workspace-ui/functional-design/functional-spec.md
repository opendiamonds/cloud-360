# 功能規格：U8 `estimate-workspace-ui`

## 範圍
重寫 `/cost`：M1 空態、M2 上傳中、M3 主畫面（摺疊）、檢查結果、歷史 drawer、分享／隱私徽章。建議區僅占位（U9）。**與 U3 同批部署**。

## 工作流 W1 — 上傳
1. 拖放 ≤3 檔 → POST `/api/cost/v1/sets`（multipart＋可選 cloud_overrides／diagram_id）
2. 201 → 渲染明細＋checks；建議區顯示占位
3. 錯誤：固定 detail 字串顯示於上傳區

## 工作流 W2 — 歷史與分享
1. 「歷史」開 drawer → GET `/sets`
2. 選一筆 → GET `/sets/{id}` 載入主畫面
3. 擁有者可 PUT shares；徽章反映 privacy

## 工作流 W3 — 建議占位
1. 渲染 `#advice-slot`；文案「AI 建議載入區（U9）」
2. **不**連線 `/advice/stream`

## 工作流 W4 — 官方估價教學（FR12）
1. `EstimateOfficialCalculators` 顯示三雲按鈕（非裸外連）
2. 點擊開啟 `EstimateCalculatorGuideModal`：2–3 頁官網截圖＋匯出呼出（AWS CSV／GCP CSV／Azure XLSX）
3. 彈窗提供該雲官方計算機連結
4. 使用者匯出後回到本頁走 W1 上傳

## 工作流 W5 — 規格欄顯示（FR3.1／FR13）
1. `EstimateCloudCard` 規格欄優先 `spec_description`，否則 `spec`
2. 兩者皆有且不同時，SKU 以副標顯示

```mermaid
flowchart LR
  Guide --> Upload
  Upload --> Detail
  Detail --> History
  Detail --> Share
  Detail --> AdviceSlot
```

**文字：** 先教學再上傳得明細；歷史／分享獨立；建議僅占位。規格欄可顯示目錄描述。

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-19T19:45:00Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|

### Summary
READY after Request Changes; empty findings table (valid).
