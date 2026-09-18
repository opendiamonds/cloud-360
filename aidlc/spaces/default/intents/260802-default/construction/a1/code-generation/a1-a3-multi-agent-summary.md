# A1↔A3 Multi-Agent — Code Summary

> Branch: `luojingting/feat/a1-ux-optimize`  
> Requirements: `inception/requirements/a1-a3-multi-agent-requirements.md`


### 實作摘要

| 項目 | 說明 |
|---|---|
| API | `POST /api/architecture/generate-wa-collab`（SSE） |
| Orchestrator | `wa_collab_orchestrator.run_wa_collab`：Design→lens→Review 發言→Design 改圖→再評（最多 2 輪） |
| 分數 | `wa_score_service.score_xml`（Active Lens，目標 ≥80） |
| Workspace | 產圖改走 collab；`xml_preview` **直接寫入畫布** |
| Assessment | 「優化至 WA ≥ 80」；評核中／分數≥80 反灰；產圖直接更新評估來源 |
| Chat UI | Design／Review speaker 標籤 |

### 驗收對照

| FR | 狀態 |
|---|---|
| FR-MA-01～06 | ✅ 後端 FSM |
| FR-MA-07 | ✅ Assessment 按鈕 |
| FR-MA-08 | ✅ provider 偵測／傳入 |
| FR-MA-09 | ✅ 結束寫入 `architecture_reviews` |
| FR-MA-10 | ✅ arch edit 啟動 |

### 手動驗收

1. Workspace 描述需求產圖 → 見 Design／Review 對話與分數 → 套用預覽  
2. 刻意簡陋架構 → 兩輪後未達標提示  
3. Assessment「優化至 WA ≥ 80」→ 套用後可再執行評核  
