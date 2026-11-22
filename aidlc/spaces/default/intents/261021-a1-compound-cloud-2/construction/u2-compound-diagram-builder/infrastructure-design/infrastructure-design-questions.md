# Infrastructure Design Questionnaire — U2: u2-compound-diagram-builder

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR3.2, NFR4.2)
> - [logical-components](../nfr-design/logical-components.md)

---

## 1. 基礎設施設計範疇說明 (Infrastructure Scope for Library Unit)

依據 `produces_kinds`，`u2-compound-diagram-builder` 作為 `library` 類型單元，其核心交付物為：
- `cicd-pipeline.md`: 定義幾何佈局、XML 產出與邊界測試在 CI 中的執行步驟。
- `traceability.json`: 追溯上游 `NFR3.2`, `NFR4.2`。

---

## 2. 關鍵確認問卷 (Clarifying Questions)

### Q1. 幾何演算法自動化測試標的 (Geometry Test Scope)
在 CI 中執行 `test_diagram_builder_compound.py` 時，重點驗收項目為何？
- [A] **斷言三雲容器 X 座標、120px 間距與 XML 語法**：包含中央 AWS 480px、兩翼各 360px、折線標籤與 XML 有效性斷言。（推薦）
- [B] **僅測試函式回傳值不為空**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `cicd-pipeline.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **測試驗收 (Q1)**: [A] CI 完整斷言 Hub-and-Spoke 座標、120px 間距與 XML 合法性。

Does this all look correct before I generate the infrastructure design artifacts for U2?
- Looks correct
- Request changes

[Answer]: Looks correct
