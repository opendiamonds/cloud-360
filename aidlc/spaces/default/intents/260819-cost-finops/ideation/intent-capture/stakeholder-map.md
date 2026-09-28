# Stakeholder Map — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: intent-capture（Ideation 1.1）· 來源標籤定義見 intent-capture-questions.md 的 ## Sources。
     每一列都掛有來源標籤。未被選取的選項不會被轉寫成排除或需求 —— 未列出的角色僅代表本階段未確認，不代表已排除。 -->

## Key Stakeholders

| Stakeholder | 在意什麼 | Source |
|---|---|---|
| FinOps 分析師 | 數字可重算、可拆解；能設定預算上限；官方 API 缺價或失敗時可覆寫單價並標記 Manual Override；超支時看得到畫面標示與站內通知 | [Q5] [Q10] [Q11] [Q15] [Q16] |
| 工程主管 | 改圖時預算變化可見、超支時看得到畫面標示與站內通知 | [Q5] [Q11] [Q16] |
| 雲端架構師 | 成本數字能對到圖上的資源；超支時看得到畫面標示與站內通知 | [Q2] [Q5] [Q11] [Q16] |
| 開發／維運 | 實作與維護成本；估價過程不要碰到雲端供應商 production | [Q5] [memory:M2] |

## Decision-makers vs. Influencers

| 角色 | 權責 | Source |
|---|---|---|
| 你（本 intent 發起人） | 決定範圍與優先序 | [Q6] |
| FinOps 角色 | 否決權被定義為核准流（核准後數字才對外）；本輪不實作該核准流 | [Q6] [Q14] |

- 決策不需團隊共識 [Q6]

## Communication Requirements

| 需求 | 內容 | Source |
|---|---|---|
| 回報節奏 | 無額外節奏；做完在 PR 說明即可 | [Q7] |
| 決議紀錄 | 本階段未要求寫入 decisions-log，亦未要求開 ADR | [Q7] |
| 超支警告 | 成本畫面視覺標示（總額變色或橫幅），加上進入產品時可見的站內通知；收件人為 FinOps 分析師、工程主管與雲端架構師 | [Q11] [Q16] |

- 每個 stage 完成後須產出 stage-completion summary，附 extension compliance（compliant / non-compliant / N/A 與理由），等使用者確認再進下一階段 [memory:M6]

## Assumptions & Open Questions

None.
