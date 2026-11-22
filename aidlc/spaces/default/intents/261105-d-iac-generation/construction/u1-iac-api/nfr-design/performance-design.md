# Performance Design — u1-iac-api

> Q1=A／Q2=A · 對齊 NFR-PERF-1.1–1.3。設計層；≤15 行示意。

## 延遲預算分配

| 路徑 | 預算 | 設計手段 |
|---|---|---|
| `POST /generate` | p95＜60s；硬 90s | LLM port 單一呼叫；asyncio／thread 逾時取消；不串多輪無界 agent |
| `/session`／`/scan`／`/secrets/rewrite` | p95＜2s | 純記憶體＋Checkov 子行程（見 reliability／Q2） |
| `/download` | p95＜5s | 記憶體內 zip；串流寫入 response；不落地明文臨時檔 |

## Bulkhead（Q1=A）

- **Generate 池**：每進程最多 **2** 個 in-flight generate；超出 → 429／明確碼或排隊拒絕（code-gen 釘一種並測）。
- **短路徑**：session／scan／rewrite／download **不**與 generate 共用該併發計數。
- **禁止自動重試** LLM／執行 POST（契約）。

## 快取

- **不**快取 LLM 產出跨請求（圖變更／密文風險）。
- Session 槽本身即工作集；LRU 見 scalability-design。

## 示意（介面級）

```text
generate(req):
  acquire(generate_sem, timeout=0) or fail busy
  try: call_llm(deadline=now+90s)
  finally: release(generate_sem)
```

<!-- confirmed: Looks correct -->
