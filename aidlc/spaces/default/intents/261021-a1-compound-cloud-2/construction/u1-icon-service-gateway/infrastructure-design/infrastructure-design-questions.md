# Infrastructure Design Questionnaire — U1: u1-icon-service-gateway

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u1-icon-service-gateway` (kind: `library`)
> 追溯上游基準：
> - [security-design](../nfr-design/security-design.md) (NFR3.1, NFR4.1, NFR5.1)
> - [logical-components](../nfr-design/logical-components.md)

---

## 1. 基礎設施設計範疇說明 (Infrastructure Scope for Library Unit)

依據 `produces_kinds`，`u1-icon-service-gateway` 作為 `library` 類型單元，其核心交付物為：
- `cicd-pipeline.md`: 定義 CI 測試自動化、Lint 檢查與環境變數注入規範。
- `traceability.json`: 追溯上游 `NFR3.1`, `NFR4.1`, `NFR5.1`。

---

## 2. 關鍵確認問卷 (Clarifying Questions)

### Q1. CI/CD Pipeline 測試執行方式
在 GitHub Actions CI 流程中，本單元的單元測試如何整合？
- [A] **於既有後端測試工作流執行 `pytest backend/tests/test_diagram_builder_compound.py`**：自動執行 Mock n8n 與 Fallback SVG 斷言，無需額外建立獨立工作流。（推薦）
- [B] **建立獨立的 CI Job**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `cicd-pipeline.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **CI/CD 整合 (Q1)**: [A] 於既有後端測試管線整合 `pytest backend/tests/test_diagram_builder_compound.py`。

Does this all look correct before I generate the infrastructure design artifacts for U1?
- Looks correct
- Request changes

[Answer]: Looks correct
