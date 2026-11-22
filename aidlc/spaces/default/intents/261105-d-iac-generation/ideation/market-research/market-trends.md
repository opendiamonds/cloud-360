# Market Trends

## Relevant Trends

下列趨勢經確認對本 intent 有意義（非「純內部、無關外部」）。[Q3]

### Policy-as-Code and Shift-Left Scanning

IaC 交付預期內建或附帶靜態掃描／策略檢查，已接近 table-stakes。[Q3][Q4]

對 Cloud-360 的意涵：D2 不是加分項敘事，而是「可交付草稿」的必要配套；產出若只有 HCL、沒有掃描結果，相對市場期待偏弱。[Q4]

### Secrets Outside Source and Manager References

Secret 不得進版控、應以 Secret Manager 引用，已成預設期待。[Q3]

對 Cloud-360 的意涵：D3 與「不內嵌 production secrets」成功標準對齊；生成器不得把真實密文寫進草稿。[intent]

### AI-Assisted IaC Growth vs Trust

AI 輔助產生 IaC 快速增加，但可信度與可審核性仍是主要疑慮。[Q3]

對 Cloud-360 的意涵：差異化不能只靠「會生成」；需可檢視草稿、掃描證據、與既有設計圖可追溯，才能回應審核疑慮。[Q4][intent]

## Implications for Differentiation

| Trend | Table-stakes response | Cloud-360 differentiator |
|---|---|---|
| Shift-left 掃描 | 草稿＋基本靜態掃描 [Q4] | 掃描結果出現在與 A／C 同一工作區流程 [Q4] |
| Secret Manager | 不內嵌 production secrets [intent] | D3 與生成同一次交付意圖 [intent] |
| AI 可信度疑慮 | 可下載／可檢視產出 [intent] | 輸入是既有架構圖（非僅 NL），便於人工對圖審核 [Q4] |

## Audience Framing

本能力定位為平台內建功能，服務既有／預期租戶角色，不做對外 TAM／SAM／SOM 模型。[Q6][Q7]

## Not Researched (Standard Depth)

- 各雲合規框架條款級對照、區域法規差異。[Q7]
- 競品財報／市佔數據。[Q7]
