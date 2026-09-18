# Code Summary — user-object-serialization（U2）

## 實際產出

`backend/services/user_router.py` **+109／-**：兩個新欄位、`UserListPage`、兩個常數、`_to_user_schema()` 工廠、清單端點改寫。
`backend/tests/test_user_list_endpoint.py` **新增 282 行 / 16 個測試**。

## 四個實作決定

**1. 欄位無預設值 ＋ 共用工廠，兩者兼具**（設計允許擇一）。理由：envelope 讓構造點由三處變四處，數量上升則分歧風險上升。無預設值讓漏傳在構造當下就是 `ValidationError`；工廠讓三處不可能分歧。

> **這是對已核可 Q1 的刻意偏離**（Q1 選了「三處各自手寫」）。依據：application-design C-4 明文把工廠列為兩個合法手段之一，且 Q1 駁回工廠的具體理由（會被迫處理範圍外的 `requested_role` 缺陷）在實作中未發生 —— 兩個 PUT 端點呼叫工廠時單純不傳該參數，行為與駁回前逐字相同。理由記於 `../functional-design/business-logic-model.md`。

**2. 查詢參數用框架原生範圍約束，不在函式內檢查**。四個理由見 NFR 文件 T-1。**已以探針實測**：合法回 200；`page=0`／`-1`／`abc`／`page_size=1000` 皆回 422；422 body 不含帳號資料；`minimum`／`maximum` 確實出現在 OpenAPI 規格的 parameter schema 中（因此被兩道漂移 gate 覆蓋）。

**3. `total` 為獨立計數查詢**。由 `len(items)` 導出的實作在「總數少於一頁」時完全正確，只在多頁時錯 —— 而目前只有 12 個帳號。`test_three_pagination_values_correct_when_fewer_than_one_page` 就是為了讓那個錯誤在測試中露餡。

**4. 序列化前正規化為 UTC aware**。原本漏了這一步（reviewer 在 doc-vs-code 比對時查出）。後果比看起來嚴重：不帶位移的字串會被瀏覽器的 `new Date()` 當成本地時間，顯示時間整體偏移一個時區位移量，**而畫面上完全正常**。已補上並以 `test_serialised_timestamp_carries_a_utc_offset` 釘住（在 SQLite 上跑，即最會露餡的環境）。

## 驗證結果

**17** 個端點測試通過（`UserListEndpointTest` 15 ＋ `UserMutationEndpointTest` 2；reviewer 實作審查 Minor 7 更正原記的 16）；後端全套 **140** 通過；OpenAPI 規格 dump 一致（36 paths／29 schemas）。
