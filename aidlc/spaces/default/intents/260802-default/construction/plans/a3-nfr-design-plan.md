# U-A3 — NFR Design Plan

> Unit: `U-A3`  
> Status: **COMPLETE**（2026-07-23）— 已核准；下一階段 Code Generation


### Checklist

- [x] 釐清問題全部作答
- [x] 產出 `construction/a3/nfr-design/nfr-design-patterns.md`
- [x] 產出 `construction/a3/nfr-design/logical-components.md`
- [x] Stage completion + audit（使用者核准後勾）

### 決策摘要

| Q | 答案 |
|---|---|
| 1 | A — Agent 單次 60s；顯式重試 |
| 2 | A — SSE 斷 → GET 補齊 |
| 3 | B — lean mxCell；>2MB warn 仍試 |
| 4 | A — Python logging audit；無表 |
| 5 | C — `ReviewOrchestrator` 狀態機 |
| 6 | A — 無應用層並行上限 |

---

## Questions

### Question 1
**Resilience — Agent 逾時／失敗**時後端模式？

A) **單次嘗試**：`asyncio.wait_for(60s)`；失敗 → `rules_only` + SSE error；重試僅經顯式 `retry-suggestions` API（無自動 retry）

B) Agent 自動 **最多 2 次**（指數退避），仍失敗才 `rules_only`

C) 規則成功後若 Agent 失敗，**同步**阻塞重試一次（仍算同一 SSE 連線）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 2
**Resilience — SSE 中斷**後客戶端預期？

A) FE 以 `GET /reviews/{id}` **補齊**已持久化狀態；進行中建議不自動重連 SSE（使用者可重試建議或重整）

B) FE **自動重連**同一 review 的 SSE（需後端支援 resume token／從頭重播已完成事件）

C) 中斷即視為失敗；僅能「整次新建評核」

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 3
**Performance — 規則引擎**優化邊界？

A) **同步**在 request 內跑完即可；XML 過大（例 >2MB）直接 413／error，不特別優化解析

B) 同步跑；XML **截斷／只解析 mxCell** 必要屬性；>2MB 仍嘗試但記 warn

C) 規則改為 **thread pool** offload（仍同進程，無新服務）

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 4
**Security — audit log** 落地方式？

A) 使用標準 **Python logging**（JSON／key=value 一行）；與現有 backend logger 同級；**不**新建 audit 表

B) 新建 `audit_events` 表存評核 audit（仍不含 XML／建議全文）

C) 只打現有 access middleware log，A3 **不**加專用欄位（與 NFR Q3=A 衝突時勿選）

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 5
**Logical components — 逾時／隔離**放哪裡？

A) **ReviewService** 擁有 timeout、status 轉換、audit 呼叫；Router 只做 HTTP／SSE 轉接

B) Router 內直接管 timeout；Service 只做業務步驟

C) 獨立 `ReviewOrchestrator` 小模組（與 Service 分離檔）專管狀態機

X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 6
**Scalability — 多並行評核**（NFR 不限併發）資源保護？

A) **不做**應用層保護；依賴 Uvicorn worker／OS；文件註明風險即可

B) **全域**同時進行中 Agent 數軟上限（例 10）；超出回 503（請在 Answer 寫上限若改）

C) 僅限制 **每 diagram** 同時 1 個進行中（跨使用者）

X) Other (please describe after [Answer]: tag below)

[Answer]: A
