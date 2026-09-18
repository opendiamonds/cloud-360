# A5 Business Rules — Sharing & Real-time Collab


### BR-A5-01 分享

1. 僅 Owner（或政策允許之可編輯者）可建立／更新分享。
2. ShareModal 勾選協作者後持久化至 `diagram_shares`。
3. 被分享者依 view／edit／review 語意取得不同畫布與聊天體驗。

### BR-A5-02 權限隔離與歡迎詞

| 語意 | 畫布 | 聊天 |
|---|---|---|
| can_edit | 可寫 | `DEFAULT_WELCOME`，可與 AI 對話 |
| can_review | 唯讀 | `REVIEW_ONLY_WELCOME`，聊天唯讀 |
| can_view | 唯讀 | `VIEW_ONLY_WELCOME`，聊天唯讀 |

### BR-A5-03 WebSocket

1. 多名可編輯者同時開圖 → 自動連線 WS，XML 即時雙向廣播。
2. 狀態列：連線成功「協作中」；斷線「單機模式」。
3. **多人游標**：**未實作**。
4. **WS JWT 強化**：⏳ 待補（見 role-permission plan）。

### BR-A5-04 授權閘

1. 無分享且非 Owner → 不可開圖／入 WS（403／拒絕連線）。
2. J5 pending 使用者無業務權 → 不可分享／協作。

### Testable Properties

| ID | 性質 |
|---|---|
| P-A5-01 | 非成員不可 GET diagram／連 WS |
| P-A5-02 | view-only 不可成功 PUT xml |
| P-A5-03 | 一編輯者廣播後其他連線者收到相同 XML payload |
