# A4 Frontend Components


### 行為對照

| 元件 | A4 行為 |
|---|---|
| `WorkspacePage` | 進場 bootstrap；切圖載入 chat；對話結束 PUT；存檔後綁定；清空確認後 DELETE |
| `ChatBox` | 「清空對話」文案與確認；顯示還原之 messages |

### 回饋

| 情境 | UI |
|---|---|
| 還原成功 | 歷史訊息出現於聊天區（可選 Toast） |
| 無法還原 | 歡迎訊息 + 提示，不擋產圖 |
| 清空成功 | Toast；歡迎訊息；XML 不變 |
| 403 | 錯誤提示 |
