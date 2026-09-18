# A2 Domain Entities — Canvas Collaborative Editing

> Unit `U-A2` · Story A2  
> Retrospective FD（對齊 `a2/code/canvas-editing-summary.md`、`database-schema.md`）


### 實體關係

```text
User 1 ──* UserDiagram
              │
              └── xml_data（mxGraph XML）
```

分享與聊天屬 A5／A4；A2 擁有**圖表 CRUD 與畫布編輯語意**。

### UserDiagram

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | PK | |
| `user_id` | FK → users | Owner |
| `title` | string | 預設「未命名架構圖」 |
| `xml_data` | text | draw.io 相容 XML |
| `updated_at` | timestamp | |

### 虛擬／工作階段

| 名稱 | 說明 |
|---|---|
| `DiagramSelector` | 前端多圖下拉之目前 `diagramId` |
| `PartialUpdateContext` | 送 AI 時之 `current_xml`（與 A1 共用 API） |

### 權限

| 條件 | 可讀 XML | 可寫／AI 改 |
|---|---|---|
| Owner | ✅ | ✅（需 A2.edit） |
| 被分享且可編輯（A5） | ✅ | ✅ |
| 僅檢視／審核 | ✅ | ❌ |
