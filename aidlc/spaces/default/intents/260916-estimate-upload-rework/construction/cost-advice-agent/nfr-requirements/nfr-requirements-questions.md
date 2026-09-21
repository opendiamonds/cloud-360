# NFR Requirements — 釐清問題（cost-advice-agent）

> Unit: `cost-advice-agent`（U7）· kind: **service**  
> 適用產物：performance／security／scalability／reliability／observability／tech-stack／traceability

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| FD Q1–Q6=A（模組／非同步／逾時 failed／去重／可選查價／SSE 進 OpenAPI） | FD |
| NFR1 3–5 分鐘端到端；SSE heartbeat | requirements／C3 |
| U6 60s 單次推論逾時；不自動重試 | U6 NFR |
| NFR7 TCMS 本 stage 不手寫 | 慣例 |
| 無新 Playwright／外置佇列 | NFR8 |

---

## Questions

### Question 1
**併發建議工作上限？**（scalability）

A. **同 process 最多 2 個並行建議 job**；其餘 enqueue 後排隊（FIFO）。**（建議）**

B. 無上限（風險打爆 OpenRouter／DB）

C. 嚴格串列（同時僅 1）

[Answer]: A — 最多 2 並行；其餘排隊

---

### Question 2
**Heartbeat 間隔？**（observability／NFR2）

A. **每 15 秒** SSE `heartbeat`；另可有 `progress` 階段事件。**（建議）**

B. 每 60 秒

C. 無 heartbeat，只靠 progress

[Answer]: A — 15 秒 heartbeat

---

### Question 3
**日誌紅線？**（security／NFR9）

A. **不得**記 OpenRouter／AWS／GCP 密鑰值、估價表全文、金額明細全文；可記 set_id、status、error code。unittest 覆蓋。**（建議）**

B. 僅文件聲明

[Answer]: A — 禁密鑰／全文／金額；有測試

---

### Question 4
**Tech — 背景執行機制？**

A. **`concurrent.futures.ThreadPoolExecutor`**（max_workers=2）實作 enqueue；不引入 Celery／Redis。**（建議）**

B. asyncio.create_task only

C. 外置 RQ

[Answer]: A — ThreadPoolExecutor max_workers=2

---

### Question 5
**單次建議內 LLM 呼叫次數預算？**（performance／cost）

A. **預設 ≤ 3 次** invoke（省錢／跨雲／品質可合併或分次）；超出則剩餘類別標 unavailable。**（建議）**

B. 無上限

C. 固定恰好 1 次大 prompt

[Answer]: A — ≤3 次 invoke

---

### Question 6
**本 stage TCMS？**

A. **否**——歸 `tcms-test-cases`。**（建議）**

B. 是

[Answer]: A — 否

---

## Consolidated Summary Confirmation

| 項 | 定案 |
|---|---|
| 並行 | 最多 2（Q1=A） |
| Heartbeat | 15s（Q2=A） |
| 日誌紅線 | 禁密鑰／全文／金額＋測試（Q3=A） |
| Worker | ThreadPoolExecutor(2)（Q4=A） |
| LLM 預算 | ≤3 invoke（Q5=A） |
| TCMS | 本 stage 不寫（Q6=A） |

[Answer]: Looks correct
