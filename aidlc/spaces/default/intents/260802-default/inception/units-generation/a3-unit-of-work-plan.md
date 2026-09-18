# A3 Unit of Work Plan

> Units Generation for story A3 → `U-A3` (2026-07-23).  
> Incremental update to existing `unit-of-work*.md` (brownfield monolith).


### 背景

- Application Design for A3 approved  
- Existing units: U-J, U-A1, U-A2, U-A4, U-A5  
- Goal: add **U-A3** and remap A3 from「未指派」

### 已採納決策（預設；與既有單元模型一致）

| 題目 | 決策 |
|---|---|
| Unit 粒度 | 單一 Module **`U-A3`**（整條 A3 MVP：規則＋ReviewAgent＋API＋FE） |
| 不拆子 unit | PDF／SPOF 為同 unit 下期 AC，不另開 unit |
| 硬相依 | U-J、U-A2 |
| 軟／peer | U-A1（CTA + Agent SDK 家族） |
| Construction 目錄 | `aidlc-docs/construction/a3/` |

### Generation checklist

- [x] 更新 `unit-of-work.md`（含 U-A3）  
- [x] 更新 `unit-of-work-dependency.md`  
- [x] 更新 `unit-of-work-story-map.md`  
- [x] A3 僅映射至 U-A3  
- [x] 使用者確認 Units Generation 完成  
