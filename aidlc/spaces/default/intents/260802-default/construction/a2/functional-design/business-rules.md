# A2 Business Rules — Canvas Collaborative Editing


### BR-A2-01 圖表 CRUD

1. 建立：登入且具架構編輯權 → 新 `UserDiagram`（可空／預設 XML）。
2. 更新標題／XML：僅 Owner 或具編輯分享權；否則 403。
3. 刪除：僅 Owner（或專案政策允許者）；刪除前須處理分享／聊天 cascade（見 DB FK／應用層）。

### BR-A2-02 儲存與載入

1. 「儲存架構圖」將畫布 XML 寫入 `xml_data`。
2. 進入工作區時載入目標圖 XML（自動選圖邏輯屬 A4 bootstrap；A2 負責提供圖內容）。

### BR-A2-03 AI 局部編輯

1. 使用者可基於現有 XML 請 AI 針對性修改（框選語意目前以文字描述為主）。
2. AI 替換／新增節點時須保留或重接邏輯連線（A1 BR-A1-03）。
3. **多人修改歷史 + 一鍵 Undo**：故事 AC 要求；**現況未實作**（僅 draw.io 內建 undo）→ 已知缺口。

### BR-A2-04 多檔切換

1. 下拉切換 `diagramId` 時，畫布與（A4）聊天必須切換到對應資料，互不污染。

### Testable Properties

| ID | 性質 |
|---|---|
| P-A2-01 | 非 Owner／非編輯分享 → PUT diagram 403 |
| P-A2-02 | 存檔後 GET 同 id 回傳相同 xml_data（round-trip） |
| P-A2-03 | 切換 diagramId 不覆蓋另一張圖之 xml |
