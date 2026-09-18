# A4 Business Rules — Chat & Last-Opened Persistence


### BR-A4-01 鍵值隔離

1. 聊天鍵值嚴格為 **user_id × diagram_id**；不同圖互不共用訊息。
2. 切換 diagram 必須載入對應聊天；無紀錄 → 預設歡迎訊息。

### BR-A4-02 持久化時機

1. 使用者送出或助理回覆完成一輪後，須 PUT 寫回 `messages_json`。
2. 清空對話：DELETE 僅刪聊天，**不刪** `user_diagrams.xml_data`。

### BR-A4-03 上次開啟圖

1. 開啟／切換圖時更新 `last_opened_diagram_id`。
2. 進入工作區（bootstrap）自動選回該圖並載入 XML + messages。
3. 圖被刪 → FK SET NULL；bootstrap 退回合理預設（列表第一張或空狀態）。

### BR-A4-04 授權

1. 僅 Owner 或被分享且可開啟該圖者可讀寫聊天；否則 403。
2. pending（J5）使用者無業務權 → 不可使用工作區聊天 API。

### Testable Properties

| ID | 性質 |
|---|---|
| P-A4-01 | 同 user 兩 diagram 的 messages 互不出現 |
| P-A4-02 | clear chat 後 xml_data 不變 |
| P-A4-03 | bootstrap 回傳之 diagram.id == last_opened（若仍存在） |
