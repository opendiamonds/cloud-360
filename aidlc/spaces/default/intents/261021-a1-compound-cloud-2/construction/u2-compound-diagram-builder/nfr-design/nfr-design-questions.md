# NFR Design Questionnaire — U2: u2-compound-diagram-builder

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md) (NFR3.2, NFR4.2)
> - [functional-spec](../functional-design/functional-spec.md)

---

## 1. 單元非功能設計邊界說明 (NFR Design Scope for Library Unit)

本單元 `u2-compound-diagram-builder` 為幾何核心函式庫，其 NFR 設計產物包含：
1. **security-design.md**: XML 安全轉義架構與 500-node 邊界校驗。
2. **logical-components.md**: `CompoundDiagramBuilder` 類別設計、幾何計算管線與 XML 序列化器。

---

## 2. 非功能設計關鍵問卷 (Clarifying Questions)

### Q1. XML 字符轉義函式選型 (XML Escaping Implementation)
在組裝節點與連線 XML cell 時採用何種轉義實作？
- [A] **使用 `xml.sax.saxutils.escape(val, entities={'"': "&quot;", "'": "&apos;"})`**：Python 標準庫原生效能最高且覆蓋雙引號與單引號轉義。（推薦）
- [B] **自製 replace 替換**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `security-design.md`、`logical-components.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **XML 轉義 (Q1)**: [A] 使用 `saxutils.escape` 執行完整 XML 字符與引號轉義。

Does this all look correct before I generate the NFR design artifacts for U2?
- Looks correct
- Request changes

[Answer]: Looks correct
