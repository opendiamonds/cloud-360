# Security Requirements — U2: u2-compound-diagram-builder

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u2-compound-diagram-builder` (kind: `library`) · **Walking Skeleton**
> 追溯上游基準：
> - [functional-spec](../functional-design/functional-spec.md)
> - [rules](../functional-design/rules.md)

---

## 1. 安全需求與防護模型 (Security Specifications)

### 1.1 XML 實體注入與特殊字元過濾 (NFR4.2)
- 生成 mxGraph XML 時，嚴禁直接進行未消毒之字串拼接。所有節點 label、標籤與屬性值一律經過標準轉義函式處理，阻擋 XXE (XML External Entity) 與畸形 XML 注入。

### 1.2 記憶體耗盡 (DoS) 防護 (NFR3.2)
- 對傳入之節點總數設置上限驗證（單圖上限 500 個節點），防止惡意過大拓撲導致記憶體暴增或 CPU 密集運算造成 DoS。
