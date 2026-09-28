# 排序理由與風險：C1 估價表上傳

## 採用的啟發式

**Value-first**（對齊 scope-definition SD-7／Q1=A）：先讓使用者看到上傳與逐項明細，再補建議，壓縮「有明細沒建議」窗口。

**局部 risk 旁路**（Q5=A）：最擔心 LangGraph＋OpenRouter，故 **B2 與 B1／B3 平行**，不是把整條計畫改成 risk-first。這是對 value-first 的疊加，不是偏離 DAG。

未採用正式 WSJF 打分（Q1 未選 D）：單一決策者、多數 Must、依賴序已由 DAG 決定，分數會是虛假精確。

未採用 walking-skeleton 儀式：scope `skeleton: off`。B1→B4→B5 仍是可演示的薄切片。

## 與拓樸的關係

Bolt 順序**尊重** `unit-of-work-dependency.md` 的邊：

- U2 在 U1 之後；U7 在 U2＋U6 之後；U8 在 U2 之後；U9 在 U8＋U7 之後；U5 在 U4 之後
- **沒有**把 U7 排在 U5 之後（units Q3=A）
- U3＋U8 捆成 B5 是**部署約束**，不是伪造 depends_on

唯一「看起來像提前」的是 B2（U6）與 B1 同時——U6 本就無入邊，拓樸允許。

## 風險登錄（交付視角）

| 風險 | 與 Bolt | 緩解 |
|---|---|---|
| OpenRouter／LangGraph 不通或太慢 | B2 最早平行；B6 量測 5 分鐘 | 失敗時 B5 仍可單獨交付明細價值 |
| 解析靜默錯欄 | B1 機械檢查＋PBT；B6／B7 品質建議為 Should | RISK-01 已接受並加碼 |
| B5 同批改爆 OpenAPI／e2e | B5 DoD 含重產與 e2e；B4 先合降低 router 衝突 | 合同 PR 檢視清單 |
| FR9.8 環境變數中間態 | B3 在 B5 前完成 | contract 腳本 |
| 窗口期過長 | B5∥B6；B7 緊接 | 平行配置見 team-allocation |
| 分享 Must 被拖 | B4／B5 DoD 含分享（Q4=A） | 不另開延後 Bolt |

## 信心累積路徑

1. B1 證明解析  
2. B2 證明模型路徑  
3. B4＋B5 證明使用者可見價值（即使建議未好）  
4. B6＋B7 證明完整成功指標（上傳→建議≤5 分鐘）  
5. B8 證明 Should 查價
