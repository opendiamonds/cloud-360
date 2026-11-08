# Constraint Register

## Technical Constraints

| ID | Constraint | Source |
|---|---|---|
| T1 | 必須整合 Workspace 架構圖與 A／C 同一套 LangGraph／UI 工作區 | [Q1] |
| T2 | 必須接上 RBAC（含 D1／D2 相關權限）與 OpenAPI／前端型別管線 | [Q1] |
| T3 | 必須整合外部掃描 CLI 與雲端 Secret Manager API（整合不重寫引擎） | [Q1][build-vs-buy] |
| T4 | D1／D2／D3 各對應一個 agent（非單一 agent 包辦） | [project learning][Q7] |
| T5 | 平台不代 apply；使用者下載後自行 apply | [intent][Q6] |
| T6 | IaC generator 屬 ADR-0006 property-based testing hard constraint 落點 | [intent][memory] |
| T7 | 測試底線：HTTP 端點需 TestClient；前端資料形狀需 e2e；授權變更需 allow/deny | [team Testing Posture] |

## Organizational Constraints

| ID | Constraint | Source |
|---|---|---|
| O1 | 無變更凍結／已知並行阻礙 | [Q5] |
| O2 | 無硬性外部 deadline；正常 feature 節奏 | [Q4] |
| O3 | 決策者身份在 intent-capture 仍為假設／未識別 — 範圍拍板權威待定錨（不阻本次可行性判定） | [intent assumption] |

## Regulatory / Security Constraints

| ID | Constraint | Source |
|---|---|---|
| R1 | 無額外外部合規認證範圍；沿用 ADR-0006 baseline（IAM、encryption、network、audit） | [Q2] |
| R2 | 禁止未核准的 production write／IaC apply／IAM 變更 | [memory][intent] |
| R3 | 雲端供應商 production credentials、direct production IaC 預設 out of scope | [memory][Q6] |

## Explicit Non-Constraints (this round)

- 未要求綁定特定雲帳號才能開工掃描／SM。[Q6]=A
- 未要求分期砍掉 D3。[Q4]=A
