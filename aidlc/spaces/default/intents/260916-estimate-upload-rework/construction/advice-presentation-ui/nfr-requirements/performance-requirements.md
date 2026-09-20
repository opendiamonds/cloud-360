# Performance Requirements — U9

- **NFR2**：建議 pending 顯示骨架；SSE `progress` 可更新文案；完成前不渲染假建議。
- 切換 estimate／離開頁面必須 `AbortController.abort()`，避免幽靈訂閱。
- 建議失敗不得阻塞明細區（U8 已獨立渲染）。
