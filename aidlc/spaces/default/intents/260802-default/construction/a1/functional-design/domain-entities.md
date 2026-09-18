# A1 Domain Entities — Architecture Design Generation

> Unit `U-A1` · Story A1  
> Retrospective FD（對齊既有實作與 `a1/code/*-summary.md`）


### 實體關係

```text
（無專屬持久化實體）
User ──JWT──> POST /api/architecture/generate
                    │
                    ▼
              DesignAgent → DiagramBuilder → mxGraph XML（SSE）
                    │
                    └──（可選）寫入 UserDiagram（屬 U-A2 擁有）
```

A1 **不擁有**資料表；產出物為暫態 XML／串流事件。持久化由 A2／A4 承接。

### 虛擬實體／DTO

| 名稱 | 說明 |
|---|---|
| `GenerateRequest` | 自然語言 `prompt`、可選 `current_xml`（局部更新）、JWT user |
| `ArchitectureDraft` | `groups` / `nodes` / `edges` 中介結構（DiagramBuilder 輸入） |
| `MxGraphDocument` | draw.io 相容 `mxGraphModel` XML 字串 |
| `SSEEvent` | 進度／完成／錯誤事件（前端 ChatBox 消費） |

### 權限語意

| Story 細項 | 行為 |
|---|---|
| A1.view | 可進入工作區並檢視產圖結果 |
| A1.edit | 可呼叫 `POST /api/architecture/generate` |
| A1.review | 審核語意（與 A1/A2/A4 合併欄「架構圖生成」對齊 Admin 矩陣） |
