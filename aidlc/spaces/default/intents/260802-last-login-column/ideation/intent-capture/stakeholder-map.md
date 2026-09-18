# Stakeholder Map — Admin 使用者最後登入時間

<!-- Stage: intent-capture（Ideation 1.1）· 來源標籤定義見 intent-capture-questions.md 的 ## Sources。
     每一列都掛有來源標籤。未被選取的選項不會被轉寫成排除或需求 —— 未列出的角色僅代表本階段未確認，不代表已排除。 -->

## Key Stakeholders

| Stakeholder | 在意什麼 | Source |
|---|---|---|
| `Platform_Admin` | 日常帳號管理效率 | [Q5] |
| `Security_Reviewer` | 稽核軌跡的完整性與正確性 | [Q13] |

## Decision-makers vs. Influencers

| 角色 | 權責 | Source |
|---|---|---|
| Danniel | 單獨決定範圍與優先序 | [Q6] |
| 影響者（非決策者） | Unknown（開放問題，見 Assumptions A5） | [Q6] |

- 決策不需團隊共識 [Q6]

## Communication Requirements

| 需求 | 內容 | Source |
|---|---|---|
| 決議紀錄 | 將本工作的決議記錄至 `decisions-log` | [Q7] |
| 回報節奏 | Unknown（開放問題，見 Assumptions A6） | [Q7] |

- 本階段只確認了決議紀錄需求；是否需要開立 ADR 未於本階段評估 [Q7]
- 每個 stage 完成後須產出 stage-completion summary，附 extension compliance（compliant / non-compliant / N/A 與理由），等使用者確認再進下一階段 [memory:M3]

## Assumptions & Open Questions

- [assumption] `Project_Admin` 與 `Platform_Owner` 具備使用者管理介面的可見性 [Q11] [Q12]，但兩者在本工作中的利益均未被指認 —— `Q5` 的已選選項只涵蓋 `Platform_Admin`。本階段不推定其利益內容，亦不將其列為受益者或排除 [Q5] [Q11] [Q12]
- [assumption] 「影響者但非決策者」未被指認；本階段不推定任何角色具影響力 [Q6]
- [assumption] 除決議紀錄外的回報節奏未被指認；本階段不推定任何節奏需求 [Q7]
- [assumption] `Security_Reviewer` 被確認為 stakeholder，但其在稽核欄位上的權責（是否具否決權、是否參與 N 值決定）未被界定 [Q13] [Q6]
- [assumption] （開放問題）`Security_Reviewer` 將取得使用者管理介面的完整檢視權限 [Q10]，其作為 stakeholder 的利益範圍是否僅限稽核欄位，本階段未釐清 [Q13]
