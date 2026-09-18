# A1 Phase 2 — User Story Core Gap Summary

### 結果

在 Agent SDK 產圖路徑之上，補齊 User Story A1 核心 UX／prompt：

| 項目 | 行為 |
|---|---|
| Prompt | 強制識別 WAF／Aurora／HA 等；VPC／AZ／subnet；edges 資料流；區域衝突語意 |
| 自動存檔 | **僅**既有 `diagram_id` 時 PUT XML + chat；無 id 只 Toast，需手動存 |
| 清空對話 | 只清 chat，保留畫布（A4） |
| 全部重置 | 清畫布 + 對話；有 id 則寫空白 XML + DELETE chat |
| 成功 CTA | IaC／Well-Architected →「即將推出」stub |
| 失敗 CTA | 對齊資源衝突文案；重試／聯絡架構師 stub |

### 檔案

- `backend/prompts/aws_architecture_system_prompt.md`
- `frontend/src/pages/WorkspacePage.tsx`
- `frontend/src/components/ChatBox.tsx`

### 手動驗收

見 `a1-agent-sdk-code-generation-plan.md` Step 8。
