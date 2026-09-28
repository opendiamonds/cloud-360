# Performance Test Instructions — C1 估價上傳改版

> NFR performance 文件存在於多個 unit；本機 Build-and-Test 僅能做輕量健全性。

## 本機可執行

```bash
cd frontend && npm run build   # 建置時間／bundle 體積觀察
```

## 延後（需類正式環境）

| 目標 | 擁有階段 | 說明 |
|---|---|---|
| 上傳／解析延遲 | performance-validation | 需真實檔案與 DB |
| SSE 串流延遲 | performance-validation | 需運行中 backend＋OpenRouter |
| 定價查找延遲 | performance-validation | 需供應商 API 或錄製 fixture |

本階段不將延後目標標為 Met；矩陣記 `Unverified` 並標 owning stage。
