# Unit of Work Plan

> Retrospective plan for Units Generation (developed scope: A1 / A2 / A4 / A5 / J).  
> 因功能已先落地，本計畫採 **補文件** 模式：記錄已採納的拆分決策，不再重跑問答。


### 背景

- Project type: Brownfield monolith  
- User request: 補齊 `unit-of-work*.md` + story map，將 A1／A2／A4／A5／J 對到 unit  
- 依據：`stories.md`、`frontend-backend-specification.md`、`aidlc-state.md`、既有 `construction/a1|a4` 與 RBAC plans  

### 已採納決策（視同 [Answer]）

| 題目 | 決策 |
|---|---|
| 部署模型 | Monolith；Unit = Module |
| Story 分組 | A1→U-A1；A2→U-A2；A4→U-A4；A5→U-A5；J1–J4→U-J |
| 與 RBAC 矩陣關係 | 產品上 A1＝A2＝A4 合併；開發 unit 仍分開 |
| A3／B–H | A3 → 見 `a3-unit-of-work-plan.md`（已建 U-A3）；B–H 仍暫不建 |

### Generation checklist

- [x] 產出 `application-design/unit-of-work.md`
- [x] 產出 `application-design/unit-of-work-dependency.md`
- [x] 產出 `application-design/unit-of-work-story-map.md`
- [x] 驗證已開發 stories 皆有且僅有一個 unit
- [ ] 使用者審查後確認 Units Generation 完成（見 aidlc-state）

### 後續建議（非本計畫強制）

- 補 `construction/a2/`、`construction/a5/`、`construction/j/` 的 code summary  
- 擴充 B–H 時再跑完整 Units Generation Part 1 問答  
