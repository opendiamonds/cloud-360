# Contract Design Planning & Questionnaire — A1 混合雲繪圖功能

> Stage: contract-design (2.8) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [unit-of-work](../units-generation/unit-of-work.md)
> - [unit-of-work-dependency](../units-generation/unit-of-work-dependency.md)
> - [components](../domain-design/components.md)
> - [requirements](../requirements-analysis/requirements.md)

---

## 1. 介面合約清單與邊界規劃 (Contract Boundary Planning)

本專案依據建構單元相依圖，確立 4 個核心整合邊界合約（3 個單元間內部合約 + 1 個外部 API 合約）：

1. **C1 (U1 ➔ External n8n)**: 外部圖示通訊契約（HTTP POST，上行 `provider="compound"`，限時 5.0 秒，容錯 fallback SVG）。
2. **C2 (U1 ➔ U2)**: 圖示擷取函式呼叫契約（行程內 Python 函式簽章與型別定義）。
3. **C3 (U2 ➔ U3)**: 混合雲幾何 XML 組裝契約（輸入 `CloudContainerSpec` 與 `CrossCloudConnectionSpec`，輸出 mxGraph XML）。
4. **C4 (U3 ➔ U4)**: Agent 對話與繪圖 SSE 串流通訊契約（OpenAPI 3.0 / REST + SSE 事件串流）。

---

## 2. 契約設計問卷 (Contract Design Questions)

### Q1. 圖示介面型別簽章 (C2: U1 ➔ U2 Interface Signature)
依據 Units Generation 審查建議 R-01，U1 與 U2 之間的函式介面應採用何種型別簽章規範？
- [A] 採用 Python 3.11 嚴格型別註解：`def fetch_icon_from_n8n(service: str, provider: Literal["compound"] = "compound") -> str`，回傳值保證為合法向量 SVG 字串，永不為 None。（推薦）
- [B] 採用無型別標註的通用函式。
- [C] 尚未確定。

[Answer]: [A]

### Q2. 幾何組裝輸入合約 (C3: U2 ➔ U3 Data Contract)
U2 接收來自 Agent 之多雲定義時，資料契約應如何設計？
- [A] 採用標準 Dataclass / Pydantic 模型（`CloudContainerSpec` 定義 provider, vpc_name, subnets, nodes；`CrossCloudConnectionSpec` 定義 source, target, protocol），確保型別驗證與結構安全。（推薦）
- [B] 傳遞無格式的原始 Dictionary。
- [C] 尚未確定。

[Answer]: [A]

### Q3. 前後端通訊與版本控制策略 (C4: U3 ➔ U4 & Versioning)
前端 UI 與後端 Agent 之通訊契約版本與異常政策：
- [A] 維持既有 `/api/v1/` REST 與 SSE 串流通道，新增 `provider: "compound"` 欄位與 `diagram_generated` 事件；後端採嚴格 8.0 秒總體限時，前端遭遇連線中斷自動提示並允許重試。（推薦）
- [B] 新開 `/api/v2/` 獨立混合雲端點。
- [C] 尚未確定。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 contract-summary.md 前，請確認以下彙整摘要正確無誤：

- **圖示簽章 (Q1)**: [A] 嚴格型別 `fetch_icon_from_n8n(service: str, provider: Literal["compound"] = "compound") -> str`。
- **幾何合約 (Q2)**: [A] 定義結構化 `CloudContainerSpec` 與 `CrossCloudConnectionSpec` 模型。
- **前後端與版本 (Q3)**: [A] 沿用 `/api/v1/` 通道，向後相容擴充 `provider: "compound"`，8.0 秒整體限時保護。

Does this all look correct before I generate the contract design artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
