# Performance Requirements — u1-iac-api

> Unit: `u1-iac-api`（service）· Q1=A／Q2=A。  
> 測量點：API 進程內（不含瀏覽器↔nginx 網路）。

## NFR 派生

| ID | 需求 | 目標 | 條件 |
|---|---|---|---|
| NFR-PERF-1.1 | D1 `POST /generate`（含 LLM） | **p95 ＜ 60s**；硬逾時 **90s** | 單圖典型規模；逾時 → 非 2xx＋明確 `error.code`（建議 `generate_timeout`，code-gen 補進契約） |
| NFR-PERF-1.2 | `GET /session`、`POST /scan`、`POST /secrets/rewrite` | **p95 ＜ 2s** | 單槽草稿／報告在 Q4 上限內；不含 LLM |
| NFR-PERF-1.3 | `GET /download` zip 組裝 | **p95 ＜ 5s** | 同上體積上限 |

## 超標行為

- Q1 硬逾時：中止 in-flight generate；**不**寫入部分 draft；回錯誤；保留先前成功 draft（若有）。
- Q2 路徑超 p95：視為缺陷（日誌 warning＋耗時）；本輪**不定**硬殺閾值（避免誤殺合法大圖）。

## 測量

- 日誌欄位：`duration_ms`、`request_id`、`diagram_id`、`route`（對齊 Q6=A）。
- 正式負載測試非本 Bolt 必交付；TestClient／單元以契約與超時計時為主。

## 不做

- 不把 D1 訂成互動級 ＜2s API。
- 執行 POST **不**自動重試（契約已定）。

<!-- confirmed: Looks correct -->
