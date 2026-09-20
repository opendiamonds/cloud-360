# Scalability Requirements — cost-advice-agent

## NFR-SC.1 — 並行上限（Q1=A）

同 process 最多 **2** 個並行建議 job；其餘 FIFO 排隊。不水平擴充多 replica 協調（本期單實例）。
