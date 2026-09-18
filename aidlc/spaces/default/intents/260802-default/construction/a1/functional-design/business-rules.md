# A1 Business Rules — Architecture Design Generation


### BR-A1-01 授權

1. 未登入或 JWT 無效 → 401。
2. `authorization_status != approved`（J5 pending）→ 403。
3. 無 A1.edit（或矩陣合併欄之編輯權）→ 403。

### BR-A1-02 全量產圖

1. `prompt` 非空；系統以 Agent SDK（OpenRouter）呼叫單一 MCP tool `draw_architecture_diagram`。
2. 產出必須為 draw.io 相容 XML；含邏輯連線與網路邊界語意（VPC/AZ 等由 prompt／builder 表達）。
3. 禁用 Bash／Read／Write／Edit 等危險 tools（`allowed_tools` 白名單）。

### BR-A1-03 局部更新（與 A2 銜接）

1. 請求可帶 `current_xml`：Agent 須在既有圖上增刪改，**保留或重接**原有連線。
2. 合併失敗時回傳錯誤 SSE，不覆寫前端未確認之畫布。

### BR-A1-04 串流契約

1. 成功路徑以 SSE 推送進度與最終 XML。
2. 上游逾時／模型錯誤 → 可讀錯誤事件；不留下半套 DB 寫入（A1 本身不寫 DB）。

### BR-A1-05 安全與設定

1. OpenRouter：`ANTHROPIC_BASE_URL` + token 映射；`ANTHROPIC_API_KEY` 必須為空。
2. 不記錄完整 prompt 於公開 log（安全基線：避免敏感架構細節外洩）。

### Testable Properties（PBT）

| ID | 性質 |
|---|---|
| P-A1-01 | 無 A1.edit → generate 一律拒絕 |
| P-A1-02 | 合法 builder 輸出必含 `mxGraphModel` 根 |
| P-A1-03 | `current_xml` 路徑不得丟棄全部既有 edge（oracle：合併後 edge 數 ≥ 閾值或保留 ID） |
