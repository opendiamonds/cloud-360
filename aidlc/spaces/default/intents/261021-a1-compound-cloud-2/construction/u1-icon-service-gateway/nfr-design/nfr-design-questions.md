# NFR Design Questionnaire — U1: u1-icon-service-gateway

> Stage: nfr-design (3.3) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [security-requirements](../nfr-requirements/security-requirements.md)
> - [tech-stack-decisions](../nfr-requirements/tech-stack-decisions.md)
> - [functional-spec](../functional-design/functional-spec.md)

---

## 1. 單元非功能設計邊界說明 (NFR Design Scope for Library Unit)

依據 `produces_kinds`，`u1-icon-service-gateway` 作為 `library` 類型單元，其 NFR 設計重點產物為：
1. **security-design.md**: HTTPS 連線逾時設定、環境變數讀取隔離與 XSS-Safe SVG 消毒器設計。
2. **logical-components.md**: 模組結構、`IconServiceGateway` 類別設計、LRU 快取裝飾器與例外捕捉流程。

---

## 2. 非功能設計關鍵問卷 (Clarifying Questions)

### Q1. XSS-Safe SVG 標籤消毒演算法 (SVG Label Sanitization Pattern)
在組裝本地 40x40 灰底文字 SVG 時，如何落實消毒機制？
- [A] **正則白名單過濾 `re.sub(r'[^A-Z0-9]', '', raw_name.upper()[:4])`**：嚴格僅允許英文字母與數字，徹底杜絕 `<script>`、CDATA 或特殊 XML 實體注入。（推薦）
- [B] **HTML Entity 轉義**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `security-design.md`、`logical-components.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **SVG 消毒演算法 (Q1)**: [A] 正則白名單僅保留大寫英數字前 4 碼，杜絕任何注入風險。

Does this all look correct before I generate the NFR design artifacts for U1?
- Looks correct
- Request changes

[Answer]: Looks correct
