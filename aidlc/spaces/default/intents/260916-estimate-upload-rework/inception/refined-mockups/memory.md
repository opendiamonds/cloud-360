<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations

- 2026-09-16T11:10Z — CONDITIONAL stage 適用性：condition 要求「存在使用者介面且 Ideation 產出過 rough mockups」。前半成立（本 intent 重寫 `/cost` 頁），後半不成立——`rough-mockups` 在本 scope 為 SKIP，directive 的 `consumes_absent` 明列 `wireframes.md` 與 `user-flow.md` 皆缺席且 `expected: true`。依 stage 檔 Step 1 的明文指示（classic scope 的同型情境）「直接由需求設計，絕不虛構缺席 artifact 的內容」執行本 stage。`user-stories` 亦為 SKIP，故 `stories` 輸入同樣缺席。
- 2026-09-16T11:10Z — 唯一的必需上游是 `requirements.md`。八題全部可回溯到具體 FR／NFR 條款或既有前端的實測事實，不引用任何虛構的 wireframe。
- 2026-09-16T11:10Z — ensemble mode 為 `inline`，support agent `aidlc-product-agent` 不另行派工，其視角（需求對應、優先度張力）由本 stage 內部承擔。
- 2026-09-16T11:10Z — Q4 與 Q7 不是設計偏好題而是需求層的硬要求：FR4.5 明文要求機械檢查與 AI 建議可區分；FR6.6 指定沿用 `ShareModal`，而該元件無任何無障礙標記，沿用即繼承缺口。兩題的選項因此都包含「不做」的後果而非只列做法。

## Deviations

- 2026-09-16T11:25Z — stage 檔 Step 1 要求讀 `<record>/ideation/rough-mockups/` 與 `<record>/inception/user-stories/`，兩者皆不存在（該兩站在本 scope 為 SKIP）。依同段的明文出口「直接由 user stories 與 requirements 設計，絕不虛構缺席 artifact 的內容」執行，實際上只有 `requirements.md` 一個上游。`upstream-coverage` sensor 的 `wireframes`／`user-flow`／`stories` 三個目標因此無法覆蓋——這是 scope 設計的結果，不是本站的遺漏。
- 2026-09-16T11:25Z — 未依 `stage_validity.warning` 的建議重跑 `scope-definition`。drift 來源已知（requirements-analysis 的四處 scope 漂移與 ADR-0018），且已於 commit `1a26c8f` 回補進 `scope-document.md` 與 `intent-backlog.md`。重跑會重問已裁定的問題。此與 approval-handoff Q4 的既有裁決一致。

## Tradeoffs

- 2026-09-16T11:25Z — Q2=C（明細預設全摺疊）與 FR3.2（無法辨識列須可見）存在直接張力。取捨為：摺疊態的卡片標頭**強制**顯示「N 列無法辨識」徽章與「總額未經核對」，列本身展開才見。代價是使用者需多一次點擊才能看到問題列；換得的是三雲併陳時的版面可讀性。此取捨已在彙整確認中明示後果並經使用者接受。若日後發現使用者實際上不會展開，這個決定是第一個該被推翻的。
- 2026-09-16T11:25Z — Q3=A（三類建議一次填入）而非 Q3=D（各自填入）。一次填入的版面較簡單，但它假設後端以單一回應交付三類建議。LangGraph 的實作若最終為串流或分段，版面須改回 D。此假設記於 `mockups.md` A-M3，須在 domain-design 對齊——這是本站與後續階段最可能脫鉤的一點。
- 2026-09-16T11:25Z — 不引入元件庫。需要的元件不超過七個且四個可由既有組合改造，引入會產生第二套視覺語彙。代價是表格、抽屜、骨架三者要自行實作並自行負責無障礙。
- 2026-09-16T11:25Z — 新畫面**沒有圖表**，舊 `CostPage` 有圓餅圖。這是能力的淨減少，非疏漏：需求未要求，且三雲併陳時圓餅圖的資訊密度低於摺疊卡片的總額列。記於 `design-system-mapping.md` §5 作為日後查證依據。

- 2026-09-16T11:40Z — 審閱（advisory，READY）提出三個 minor，三項皆在收到 verdict 後就地補完，未留給下游：R-01 補上 FR4.2 數量正值檢查在「檢查結果」區段的呈現範例，並明訂三類機械檢查皆同時在摘要層與明細列層呈現；R-02 把 FR6.1 綁定架構圖的 UI 缺席明記為刻意延遲（`mockups.md` A-M4），避免 construction 誤判為遺漏；R-03 新增 `PrivacyBadge`，讓 FR6.5 的「預設私密」在畫面上留下痕跡。三項皆為加法，不推翻任何既有版面決定。

- 2026-09-16T11:52Z — 複審（iteration 2，NOT-READY）在 R-01 的補丁本身抓到兩個實質錯誤，證明「補審閱意見」這個動作本身需要被審。R-04：補充段落把 FR4.1（幣別一致）與 FR4.3（總額對帳）的編號寫反。R-05（Major）：宣稱「三類機械檢查皆同時在摘要層與明細列層呈現」是錯的——FR4.3 比對的是全表加總與表上總額，這個結論不屬於任何一列，硬要列層標示等於要求實作者發明需求沒有的概念。修正為分層表格，明訂 FR4.1／FR4.2 兩層皆呈現、FR4.3 只在摘要層與表尾。這個錯誤的成因是為了讓句子工整而過度概括，是撰寫 artifact 時的常見失誤型態。
- 2026-09-16T11:52Z — R-06：`PrivacyBadge` 與頁首「分享」按鈕都開同一個 modal，形成語意不明的雙入口。裁決為徽章降為**純展示、不進 Tab 序**，分享按鈕維持唯一入口——徽章說出現況、按鈕改變現況，職責不重疊。連帶少一個互動元件與其無障礙負擔。

## Open questions

- 2026-09-16T11:25Z — **第五處 scope 漂移**：Q7=A 要求修補 `ShareModal` 的六項無障礙缺口（`accessibility-checklist.md` A11）。此工作不在任何既有 PU 內，掛於 PU-13（分享）之下但未計入其原始估算。前四處漂移見 requirements-analysis OQ1。落點與工作量交由 delivery-planning。
- 2026-09-16T11:25Z — 抽屜（drawer）為程式庫中不存在的元件型別（`mockups.md` OQ-M2）。本站依 Q6=A 定案為抽屜，但是否值得為單一用途新增一個元件型別、或改以既有 modal 承載，交由 functional-design 在看過實作成本後複核。
- 2026-09-16T11:25Z — 既有 `text-gray-400` 圖示鈕對白底約 2.8:1，**低於 WCAG 1.4.11 的 3:1**（`accessibility-checklist.md` OQ-A1）。改為 `gray-500` 會影響所有沿用此組合的既有元件。是新畫面局部改（兩套語彙）或全域改（擴大影響面），交由 functional-design。
- 2026-09-16T11:25Z — 摺疊態標頭的檢查摘要在「同時有無法辨識列與幣別不一致」時空間不足，FR4 未定義優先序（`mockups.md` OQ-M3）。交由 functional-design。
- 2026-09-16T11:25Z — 無障礙驗證的自動化涵蓋率僅約三成；A4（不倚賴顏色）與 A6（播報時機）本質上無法由靜態掃描判定。這與 `CLAUDE.md` §3 記載的三塊結構性盲區同型。是否逐條進 TCMS 手動測案交由 `tcms-test-cases` 階段（OQ-A3）。
