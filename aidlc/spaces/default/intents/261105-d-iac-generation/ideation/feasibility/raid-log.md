# RAID Log

## Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Rsk-1 | 多雲架構圖語意 → Terraform／OpenTofu 草稿品質不足，使用者不採信 | Medium | High | 對齊 A／C 可檢視產出；requirements 訂可測 AC；PBT 覆蓋 generator 核心 | [Q7][intent] |
| Rsk-2 | 掃描 CLI／規則集未統一，D2 結果不一致或環境難重現 | Medium | Medium | requirements 選定預設引擎與版本；CI／本機契約寫清 | [Q1] |
| Rsk-3 | D3 成功標準模糊，導致 Secret Manager 整合做成過大或過空 | Medium | High | requirements 強制定義產出形狀（引用 vs 明文禁止）；承接 intent-capture R-01 | [intent] |
| Rsk-4 | 三 agent 編排增加延遲／失敗面，Workspace UX 不及 A／C | Low | Medium | 複用既有 LangGraph 模式；分 agent 但共享狀態契約 | [Q3][Q7] |

## Assumptions

| ID | Assumption | Status |
|---|---|---|
| Asm-1 | 既有 A／C LangGraph 模式可直接延伸為 D1／D2／D3 三 agent | Accepted for feasibility [Q3][Q7] |
| Asm-2 | 掃描與 SM 以整合既有工具為主，不自研引擎 | From build-vs-buy [Q1] |
| Asm-3 | 無外部合規專案夾帶本 intent | [Q2] |
| Asm-4 | 決策者身份待定錨不阻礙本階段「可行」結論 | [intent assumption][Q5] |

## Issues

| ID | Issue | Notes |
|---|---|---|
| Iss-1 | D3 尚無專屬成功指標（上游審閱 R-01） | 必須在 requirements-analysis 補齊 |
| Iss-2 | Workspace「生成 IaC」仍為 Coming Soon | 本 intent 要關閉此缺口 [intent] |

## Dependencies

| ID | Dependency | Needed by |
|---|---|---|
| Dep-1 | Workspace 架構圖可讀 API／資料模型 | D1 |
| Dep-2 | 既有 LangGraph／agent 執行與前端工作區元件 | D1–D3 UX |
| Dep-3 | RBAC 種子與 OpenAPI dump／前端 gen:types 管線 | 端點與 UI |
| Dep-4 | 選定之掃描 CLI（可執行二進位或容器） | D2 |
| Dep-5 | 雲端 Secret Manager 引用慣例（設計階段定） | D3 |
| Dep-6 | ADR-0006 PBT 測試能力（hypothesis 已在棧內） | IaC generator 模組 |
