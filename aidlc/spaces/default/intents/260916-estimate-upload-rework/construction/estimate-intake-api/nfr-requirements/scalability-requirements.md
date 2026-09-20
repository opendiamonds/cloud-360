# Scalability Requirements — estimate-intake-api

> Unit: `estimate-intake-api`（U2）· Q4=A。

## 部署形態

- **單一 FastAPI process**＋既有 Postgres（與現況 shared service 一致）。
- **不**引入 Redis／Celery／外部分佈式佇列（建議 enqueue 為 in-process `BackgroundTasks`）。

## 清單與寫入

| 項目 | 決策 |
|---|---|
| `GET /sets` 分頁 | `page_size` 上限 **≤ 50**（預設建議 20） |
| 併發上傳 | 依 DB 與 process 自然上限；**不做**應用內 per-user rate limit（交邊緣／後續） |
| 水平擴展 | 本 unit 不設計多 replica 協調；若日後多 worker，BackgroundTasks 語意須另開 ADR |

## 明確不做

- 不在本 unit 引入訊息中介或物件儲存。
- 不以快取機械檢查結果換擴展（BR2.4：每次重算）。

<!-- confirmed: Looks correct -->
