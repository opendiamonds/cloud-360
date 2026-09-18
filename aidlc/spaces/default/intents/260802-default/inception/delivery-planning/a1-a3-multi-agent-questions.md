# A1 ↔ A3 Multi-Agent 協作 — 需求澄清問題

請回答下列問題，確認「Design Agent 與 WA Review 協作，使架構圖 Well-Architected 分數 ≥ 80」的範圍與行為。

現況摘要（供對齊）：

- A1：`design_agent` 產 draw.io XML（單向，無評分回饋）
- A3：規則引擎 + lens 打分（0–100）+ LLM 建議文案；**沒有**把 findings 餵回 Design Agent
- 「≥ 80」目前**尚未**寫入規格或程式門檻
- ADR-0002 規劃了 Routing／多 agent，但尚未實作 A1↔A3 對話迴圈

---

## Question 1

觸發時機：何時啟動 A1 ↔ A3 協作迴圈？

A) 使用者在 Workspace 聊天產圖時**自動**進入協作（產圖完成後立刻評核並迭代）

B) 使用者明確點「優化至 WA ≥ 80」或類似按鈕才啟動（預設仍是單次產圖）

C) 兩者皆有：自動跑一輪輕量評核提示；完整多輪迭代需使用者確認

X) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

## Question 2

對話／迭代模式：兩個 agent 如何「互相討論」？

A) **Orchestrator 中介**（推薦 MVP）：評核結果（分數 + 結構化 findings）寫入共用 context → Design Agent 依 findings 改圖 → 再評核；agent 之間不直接互聊，由後端 FSM 驅動

B) **真正雙 agent 對話**：同一 session 內 Design 與 Review 輪流發言（transcript 可見），再呼叫繪圖／評核工具

C) **單 agent + WA 工具**：仍用 Design Agent，但多給它「呼叫 WA 評核」工具，自己讀分數後改圖（Review Agent 不當獨立對話方）

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｂ

## Question 3

達標門檻：`overall_score >= 80` 的行為？

A) **硬門檻**：未達 80 繼續迭代，直到達標或打到最大輪數；未達標則標示失敗／需人工介入

B) **軟目標**：盡力優化；未達 80 仍回傳目前最佳圖 + 分數與剩餘 findings，不阻擋使用者使用

C) **硬門檻 + 人工確認**：達 80 前每輪改圖需使用者 Accept 才寫入畫布

X) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

## Question 4

最大迭代輪數（成本／延遲控制）？

A) 最多 **2** 輪（初產 + 一次依 findings 改圖）

B) 最多 **3** 輪

C) 最多 **5** 輪

D) 可設定（預設 3，UI／環境變數可改）

X) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

## Question 5

分數來源（迴圈用哪個分數當「達標」依據）？

A) 與 A3 正式評核相同：**lens 加權分數**為準（規則引擎僅輔助 findings）

B) **僅規則引擎**分數（較快、較穩；與 Assessment 頁正式分數可能略有差異）

C) 兩者都算：迴圈用規則引擎快速閘門；結束時再跑一次完整 lens 評核寫入 Assessment

X) Other (please describe after [Answer]: tag below)

[Answer]:Ａ

## Question 6

畫布更新策略：迭代過程中如何呈現？

A) 每輪改圖都**即時推到畫布**（SSE `xml`），使用者看得到演進

B) 只在**最終達標或結束**時更新畫布；過程僅顯示對話／進度

C) 過程顯示預覽；最終圖需使用者按「套用」才寫入畫布／儲存

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｃ

## Question 7

本期範圍（MVP）？

A) **僅 Workspace 產圖路徑**：聊天產圖時可啟用協作；Assessment 仍維持獨立評核

B) Workspace + Assessment「依建議改圖」一鍵回到協作迴圈

C) 先做後端 orchestrator + API／SSE，前端只做最小進度與最終圖（UI 精簡）

X) Other (please describe after [Answer]: tag below)

[Answer]:Ｂ

## Question 8

多雲：協作迴圈是否沿用 A3 的 provider（aws／gcp／azure）？

A) 是：沿用使用者選擇或自動偵測的 provider 與對應規則／lens

B) MVP 只做 AWS；GCP／Azure 下一期

X) Other (please describe after [Answer]: tag below)

[Answer]:Ａ
