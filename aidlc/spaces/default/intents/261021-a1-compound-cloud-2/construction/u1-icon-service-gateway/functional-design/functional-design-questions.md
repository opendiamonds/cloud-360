# Functional Design Questionnaire — U1: u1-icon-service-gateway

> Stage: functional-design (3.1) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [unit-of-work](../../../inception/units-generation/unit-of-work.md)
> - [contract-summary](../../../inception/contract-design/contract-summary.md) (Contract C1, C2)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (FR4.1, FR4.2, NFR3, CON2)
> - [stories](../../../inception/user-stories/stories.md) (US4.1, US4.2)

---

## 1. 單元實作職責與實體邊界說明 (Functional Scope & Entities)

本單元 `u1-icon-service-gateway` 封裝與外部 n8n 圖示服務之網路通訊，其核心技術規格與行為邊界如下：
- **主要函式**: `fetch_icon_from_n8n(service: str, provider: Literal["compound"] = "compound") -> str`
- **對外上行呼叫 (Contract C1)**: `POST ${N8N_WEBHOOK_URL}`，上行 JSON payload 必須精確固定為 `{"service": service_name, "provider": "compound"}`。
- **嚴格逾時防護 (NFR3 / CON2)**: 呼叫端設置 5.0 秒逾時（`timeout=5.0`）。
- **保證降級防護 (Fallback Guarantee)**: 當遇到 HTTP 404、500、連線拒絕、DNS 失敗或 5.0s 逾時，動態合成 40x40 灰底文字向量 SVG（底色 `#F1F5F9`、邊框 `#CBD5E1`、文字 `#475569`），絕不拋出任何異常中斷上層流程。

---

## 2. 功能細部設計關鍵問卷 (Clarifying Questions)

### Q1. 圖示快取機制 (In-Memory Icon Caching)
在繪製包含多個相同服務節點（如 3 個 EC2 或 2 個 BigQuery）的架構圖時，是否在記憶體中建立圖示查詢快取？
- [A] **啟用程序內快取 (LRU Cache)**：在 `fetch_icon_from_n8n` 套用 `@lru_cache(maxsize=128)`，相同 `(service, provider)` 僅呼叫外部 n8n 一次，顯著提升繪圖速度並減輕外部服務負載。（推薦）
- [B] **不啟用快取**：每次節點請求皆真實發送 HTTP 呼叫。

[Answer]: [A]

### Q2. Fallback SVG 標籤字串截斷規則 (Fallback Label Truncation)
當降級產生 40x40 向量 SVG 時，若雲端服務名稱過長（例如 `cloud_interconnect` 或 `application_gateway`），SVG 內部顯示之文字應如何呈現？
- [A] **取首字大寫縮寫或前 4 字元**：字串過長時截取前 4 個英文字元並轉為大寫居中呈現（例如 `CLOU`、`EC2`、`BIGQ`），確保在 40x40 小尺寸畫布上排版美觀不溢出。（推薦）
- [B] **完整縮放字體顯示**：以極小字體完整輸出所有文字。

[Answer]: [A]

### Q3. 日誌與監控紀錄層級 (Logging & Observability)
當發生 n8n 逾時或降級至 Fallback SVG 時，日誌的記錄策略為何？
- [A] **記錄 WARNING 等級日誌**：輸出包含服務名稱、耗時與降級原因之結構化日誌（含 `[ICON_FALLBACK]` 標籤），但不提升至 ERROR，以避免對警報系統產生誤報。（推薦）
- [B] **記錄 ERROR 等級日誌**：視為系統錯誤發出警報。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `entities.md`、`rules.md`、`functional-spec.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **快取機制 (Q1)**: [A] 啟用 `@lru_cache(maxsize=128)` 程序內快取，避免重複呼叫外部 n8n。
- **Fallback 呈現 (Q2)**: [A] 截取前 4 字元大寫置中，保證 40x40 灰底向量排版不溢出。
- **日誌策略 (Q3)**: [A] 記錄 WARNING 等級 `[ICON_FALLBACK]` 結構化日誌，優雅降級不造成誤警報。

Does this all look correct before I generate the functional design artifacts for U1?
- Looks correct
- Request changes

[Answer]: Looks correct
