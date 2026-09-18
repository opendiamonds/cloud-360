<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-09T05:00:00Z — 出題前先讀 `AdminPage.tsx` 取得既有樣式的實際 class 與語意色（深色玻璃擬態容器、`text-slate-300` 的角色欄破折號、待授權 amber／已核准 emerald、載入與錯誤皆為 `p-20 text-center`），使 design-system-mapping 能對應真實既有值而非發明新的設計語彙。
- 2026-08-09T05:00:00Z — 載入／錯誤態不出題：user-stories 的 AC-1.9 已依 design 實測定案為「沿用既有整塊替換模式、不做骨架」，且該定案已回答 requirements 的 OQ-5；本站只需在 artifact 中落實，不重開已定案項。
- 2026-08-11T00:00:00Z — Revision 1 只補分頁相關規格，既有四項定案（無紀錄文案、破折號區分、768px 斷點、amber-300）與五態表的既有五列一字不改；分頁需要的是新增一個態與一個元件，不是重審既有決定。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-09T05:30:00Z — 卡片欄位順序相對已核可線框做了對齊調整（角色→授權 改為 授權狀態→角色）：線框自身的卡片順序與其桌面表格欄序不一致，屬線框階段的既有瑕疵。初版**未說明就改**，被 reviewer 判為靜默變更（Major）；修正方式是補上明確的對齊修正說明，不回改上游 artifact。
- 2026-08-11T00:00:00Z — 定案 5（分頁控制移出容器）**更正了已核可線框的版位**。判定為「對齊修正」而非新範圍決定：線框畫控制項在容器內時，尚未與 AC-1.9 的「載入／錯誤時整塊替換、且與變更前完全相同」對照過；兩者放在一起看，容器內是唯一會讓 AC-5.10 必然失敗的版位。依 `project.md` 的 correction 在本站 artifact 明記其為對齊修正並說明原瑕疵，上游 `wireframes.md` 不回改。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-09T05:30:00Z — 「已知風險」不以文字帶過，而是把最壞情境**實際畫出來**再判定：初版只在 assumptions 寫「雙 amber 同列可能難辨識，屬樣式微調」，reviewer 查證 auth 流程後指出該組合真實可達（待授權帳號可先登入再逾期），且三列範例無一涵蓋它。補畫 dave 列後，判定依據從推論變成可從圖本身驗證的事實（隔一整欄、僅一者帶圖示）。
- 2026-08-09T05:30:00Z — 設計決策的量化佐證優於語氣強度：Q3 初版用「必然需要大量橫向捲動」的高確定性措辭但無數字，reviewer 判為缺佐證；改以既有 `px-6` 內距推算（6 欄內距 288px、768px 下每欄均分約 80px、時間欄需約 150px），使斷點選擇可被檢驗。
- 2026-08-11T00:00:00Z — Q6／Q7 都選「停用而非隱藏」，代價是單頁時畫面多一列無作用元素。選它的決定性理由不是美感而是**可驗證性**：user-stories 的 DoD 已指出，若定案為隱藏，e2e 斷言「控制項可見」會在實作正確時紅燈；而「呈現但停用」讓 e2e 不需對資料量做條件分支。
- 2026-08-11T00:00:00Z — 目前頁碼用 `blue`（既有「目前登入」標籤的語意色）而非 `amber`：本頁的 amber 已被「待授權」與「逾期」兩個真正需要注意的訊號佔用，把「你在這裡」也塗成 amber 會稀釋它們。這是沿用既有語意色盤而非新增色票。
- 2026-08-11T00:00:00Z — 四張 ASCII box 以腳本產生並以 `len()` 逐行驗證字元數一致（桌面 75、小螢幕 42／44），未手寫。這是 `project.md` 明文要求的既有慣例（含 CJK 的 box 手寫必然數錯），也依 `cid:rough-mockups:rev1-c15` 採 `len()` 字元數而非顯示寬度。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-09T05:30:00Z — reviewer iteration 2 的新 Minor：`design-system-mapping.md` 有一處與已修正項同類的來源標籤誤植（`[st]` 指向 stories.md，實際內容出自未登記的 personas.md）。內容有據非捏造，READY 後不回改（會使 review receipt 失效且 iteration 已用罄），留待下游觸碰該檔時一併修正。
- 2026-08-09T05:30:00Z — `amber-300` 在既有深色背景的對比度仍未實測，為上線前必須完成的人工驗證（accessibility-checklist 已列 P-2 為必驗項）。
- 2026-08-11T00:00:00Z — accessibility-checklist 新增的 P-7／U-4／R-5 三項都只驗「屬性存在」，一個把 `aria-current="page"` 寫死在第一個頁碼上的實作會通過 U-4。已在該檔如實標示此弱點並建議 Construction 改為比對「帶該屬性的元素」與「回應的目前頁次」；但本站無法強制，若 Construction 照最低標準做，該項的實質保護接近零。
- 2026-08-11T00:00:00Z — `min-w-11`（44px）假設 Tailwind 預設 spacing scale 未被專案覆寫。既有設定未自訂斷點，故推定 spacing 亦未自訂，但**本站未實際讀取 Tailwind 設定檔驗證**；已列為 Construction 開工時的查證項。
- 2026-08-11T00:00:00Z — reviewer 指出本站（與更早的 Q3）都以 `frontend/tailwind.config.js` 作為 Tailwind 設定的查證依據，但專案是 **Tailwind v4**、實際生效的是 `src/index.css` 的 `@theme`，那支 config 未被任何 `@config` 載入、是死碼。數字結論碰巧成立（`min-w-11` 確為 44px，已用專案自身的 Tailwind 實際編譯驗證），但查證鏈是錯的 —— 下次引用任何 Tailwind 數值前，先確認哪一份設定真的生效。
