# NFR Requirements Questionnaire — U2: u2-compound-diagram-builder

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)
> - [requirements](../../../inception/requirements-analysis/requirements.md) (NFR1, NFR2, NFR3)

---

## 1. 單元非功能需求邊界說明 (NFR Scope for Library Unit)

本單元 `u2-compound-diagram-builder` 作為幾何核心函式庫，其 NFR 著重於：
1. **安全性 (Security)**: 生成之 mxGraph XML 結構合法性與 XML 注入防護 (XML Entity Injection Prevention)。
2. **技術選型決策 (Tech Stack Decisions)**: 採用 Python 標準庫 `xml.etree.ElementTree` 或防護型字串建構，零第三方套件依賴。
3. **效能約束 (Performance)**: 幾何計算與 XML 組裝耗時嚴格 $\le 200\text{ms}$，為端到端 8.0s 保留極充裕餘裕。

---

## 2. 非功能性需求關鍵問卷 (Clarifying Questions)

### Q1. XML 產生防護與轉義策略 (XML Security & Escaping)
在組裝三雲節點標籤與協議文字時，如何防範 XML 注入？
- [A] **原生字符轉義 (Native XML Escaping)**：對所有使用者或節點傳入文字強制套用 `xml.sax.saxutils.escape()`（轉義 `&`, `<`, `>`, `"`, `'`），杜絕畸形 XML 破壞畫布解析。（推薦）
- [B] **原始字串拼接**。

[Answer]: [A]

### Q2. 記憶體開銷與空間複雜度 (Memory Budget)
本單元幾何計算與 XML 生成在面對大架構圖時之記憶體上限為何？
- [A] **控制在 10MB 記憶體以內**：純串流/樹狀節點產生，空間複雜度 $O(N)$，確保在輕量容器或微服務環境下無壓力運行。（推薦）
- [B] **不設記憶體限制**。

[Answer]: [A]

---

## Consolidated Summary Confirmation

在依據上述答案產出 `security-requirements.md`、`tech-stack-decisions.md` 與 `traceability.json` 前，請確認以下彙整摘要正確無誤：

- **XML 安全 (Q1)**: [A] 強制 XML 字符轉義，防止 XML 注入與解析崩潰。
- **記憶體預算 (Q2)**: [A] 空間複雜度 $O(N)$，常駐記憶體 $\le 10\text{MB}$。

Does this all look correct before I generate the NFR requirements artifacts for U2?
- Looks correct
- Request changes

[Answer]: Looks correct
