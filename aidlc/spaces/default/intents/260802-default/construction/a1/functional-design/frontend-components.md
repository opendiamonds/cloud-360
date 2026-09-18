# A1 Frontend Components


### 路由／承載頁

| 路徑 | 元件 | 說明 |
|---|---|---|
| `/`（工作區） | `WorkspacePage` | 承載畫布與聊天；A1 產圖結果寫入畫布 |
| （嵌入） | `ChatBox` | 輸入 prompt、SSE 消費、觸發產圖／局部修改 |
| （嵌入） | `DrawioCanvas` | 顯示／套用回傳 XML |

A1 **無獨立路由**；能力閘道依 AuthContext `can('A1','edit')`（或合併架構圖生成語意）。

### ChatBox（A1 相關行為）

1. 送出自然語言 → `POST /api/architecture/generate`。
2. 局部修改：夾帶目前畫布 `current_xml`。
3. 成功：畫布載入 XML；失敗：錯誤提示，不強制清畫布。
4. 無編輯權：輸入／送出 disabled，顯示權限說明。

### 與其他 Unit 邊界

| 能力 | 歸屬 |
|---|---|
| 產圖／局部 AI | **A1** |
| 存檔／多圖切換 | A2 |
| 聊天持久化／上次開啟 | A4 |
| 分享／WS | A5 |
