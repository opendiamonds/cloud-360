# A2 Frontend Components


### 承載

| 元件 | 職責 |
|---|---|
| `WorkspacePage` | 圖選單、儲存、切圖、串接 Chat／Canvas |
| `DrawioCanvas` | 嵌入 draw.io、載入／匯出 XML、手動編輯 |
| `ChatBox` | 觸發局部 AI（帶 current_xml） |

### 互動要點

1. 儲存成功 Toast；失敗可重試。
2. 無編輯權：畫布唯讀、儲存／AI disabled。
3. 多圖切換：切換前可提示未存檔（若已實作）；內容隔離。

### 已知 UI 缺口

- 框選節點群組後自動抽取 selection 給 AI：未做。
- AI 變更歷史時間軸／一鍵 Undo：未做。
