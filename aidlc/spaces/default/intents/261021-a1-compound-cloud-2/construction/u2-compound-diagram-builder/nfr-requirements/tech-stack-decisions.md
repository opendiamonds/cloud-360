# Tech Stack Decisions — U2: u2-compound-diagram-builder

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)

---

## 1. 技術選型與依賴決策 (Technology Selections & Rationale)

| 層次 (Layer) | 選定技術 (Technology) | 版本 / 規格 (Version) | 選型理由與決策依據 (Rationale) |
| :--- | :--- | :--- | :--- |
| **執行環境** | Python | 3.11+ | 專案後端統一標準環境。 |
| **XML 生成** | `xml.etree.ElementTree` / `saxutils` | Python 內建 | 原生支援樹狀 XML 節點建構與轉義，零第三方相依。 |
| **單元測試框架** | `pytest` | 7.x+ (既有) | 搭配既有後端測試鏈，提供幾何計算與 XML 結構之自動化驗證。 |

