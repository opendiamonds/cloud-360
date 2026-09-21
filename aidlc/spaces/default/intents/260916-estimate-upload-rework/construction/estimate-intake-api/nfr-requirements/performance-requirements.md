# Performance Requirements — estimate-intake-api

> Unit: `estimate-intake-api`（U2）· Q2=A。

## 同步路徑（本 unit）

| 操作 | 目標 | 超標行為 |
|---|---|---|
| `POST /api/cost/v1/sets`（含 parse＋寫庫，**不含**建議） | p95 ≤ **10s** | 仍回 **201**；寫 warning 日誌（含 set id／耗時） |
| `GET /api/cost/v1/sets/{id}`（含當場重算 checks） | p95 ≤ **10s** | 仍回 200；warning 日誌 |

## 與 NFR1 的邊界

- **NFR1**（上傳完成→建議產出 3–5 分）＝本 unit 上傳時窗 **＋** U7 背景建議；本 unit **不**單獨承擔端到端 SLA。
- 建議產生**不得**阻塞 201（FD Q2=A／BR2.8）。

## 測量

- code-gen／測試以單元與契約為主；正式負載測試非本 unit 必交付。
- 日誌欄位建議：`duration_ms`、`estimate_set_id`、`file_count`（不得含檔名路徑敏感值）。

## 不做

- 不為達 10s 而跳過魔數／parse。
- 不定 POST ≤3s 硬失敗（避免誤殺合法大表）。

<!-- confirmed: Looks correct -->
