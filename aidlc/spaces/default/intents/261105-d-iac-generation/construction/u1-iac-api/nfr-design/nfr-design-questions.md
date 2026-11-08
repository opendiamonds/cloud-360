# NFR Design 問答：U1 `u1-iac-api`

> Stage: nfr-design · Unit: `u1-iac-api`（service）  
> 設計層：模式／策略／邏輯元件；禁止完整實作碼。  
> **成本揭露**：本題組共 5 題。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 延遲：D1 p95＜60s／90s；非 LLM＜2s；zip＜5s | [nfr-req] Q1–Q2 |
| Checkov CLI；缺 CLI→明確失敗；無 CI scan job | [nfr-req] Q3 |
| ≤3 槽／16MiB；同槽單 in-flight；best-effort memory | [nfr-req] Q4–Q5 |
| 結構化 log＋request_id；暫無 metrics／OTel | [nfr-req] Q6 |
| `backend/iac/`；禁 apply／SM 寫入；PBT 三核心 | [fd]／[req] |
| 執行 POST 不自動重試 | [cd] |

## Sources

- [nfr-req] `../nfr-requirements/*`
- [fd] `../functional-design/functional-spec.md`、`rules.md`
- [cd] `../../../inception/contract-design/contract-summary.md`
- [dd] `../../../inception/domain-design/components.md`

---

## Q1. D1 LLM 呼叫的隔離與逾時？

> 避免慢 LLM 拖垮同進程的 scan／rewrite／session。

A. **邏輯 bulkhead**：generate 專用逾時 90s＋獨立併發上限（例如每進程 ≤2 in-flight generate）；scan／rewrite 走短逾時池；LLM 失敗**不**重試（契約已禁自動重試），直接錯誤碼。**（建議）**
B. 全路由共用單一全域逾時與併發池。
C. 為 D1 另起 worker 進程／佇列（本輪範圍過大）。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. Checkov 子行程策略？

A. **同步 subprocess**：釘版可執行檔；總逾時對齊非 LLM 預算（＜2s 目標內盡力，硬上限例如 10s 防掛死）；stdout／stderr 截斷；非 0 或超時 → 明確失敗，不產空成功報告。**（建議）**
B. 非同步佇列＋輪詢（本輪不做）。
C. 內嵌 Python SDK 取代 CLI。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. Session 槽淘汰演算法？

> NFR 已定 ≤3 槽；需釘死實作語意供測試。

A. **LRU**：超出 3 時淘汰最久未存取槽（讀／寫皆更新 recency）。**（建議）**
B. FIFO：超出淘汰最早建立槽。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. `request_id` 傳播？

A. **入站有 `X-Request-ID`（或既有平台慣例頭）則沿用，否則後端生成 UUID**；寫入 log 與（可選）錯誤回應延伸欄；不強制前端必送。**（建議）**
B. 僅後端自生成，忽略入站頭。
C. 強制客戶端必送，缺則 400。
X. Other (please specify)

[Answer]:Ａ

---

## Q5. 邏輯元件邊界（給 Infrastructure／code-gen）？

A. **五邏輯元件**：`IacRouter`｜`IacSessionStore`｜`IacGenerator`（含 LLM port）｜`IacScanner`（Checkov port）｜`IacRedactor`；失敗域：Generator 慢失敗不阻塞 Scanner／Redactor 短路徑；Store 為單進程單例。**（建議）**
B. 合併 Scanner＋Redactor 為單一 `IacTransform`。
C. Router 內聯全部邏輯（不拆 port）。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — generate bulkhead：90s＋≤2 in-flight；短路徑獨立；失敗不重試。
2. **Q2=A** — Checkov 同步 subprocess；硬上限防掛死；非 0／超時→明確失敗。
3. **Q3=A** — Session 槽 LRU 淘汰。
4. **Q4=A** — request_id：有入站頭則沿用，否則後端 UUID。
5. **Q5=A** — 五邏輯元件 Router｜Store｜Generator｜Scanner｜Redactor。

**將產出**：performance／security／scalability／reliability／observability／logical-components／traceability。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
