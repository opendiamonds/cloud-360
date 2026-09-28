# Refined Mockups — 釐清問題

> Stage: refined-mockups（Inception 2.5，inline）· Depth: Standard · Scope: mvp
> Intent: `260819-cost-finops`（C1 第一輪）
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。
> **成本揭露**：本題組共 5 題。答完後產出中高保真 mockups、interaction-spec、design-system-mapping、accessibility-checklist。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 資訊層級：總額置頂 → 圓餅 → 資源列；時數只在列上 | [rm:Q1] [stories C1-2／C1-4] |
| 產圖成功卡加「查看預估成本」，與既有 CTA 並列 | [rm:Q2] [stories C1-3] |
| 成本頁「已超支」文字＋變色；進產品一條橫幅，無 inbox | [rm:Q3] [stories C1-7] |
| 時數與（允許時）單價就地編輯；覆寫列標 Manual Override | [rm:Q4] [stories C1-4／C1-5] |
| WCAG 2.1 AA、桌面優先、窄視窗靠捲動 | [rm:Q5] [stories AC-1.15] |
| 第一段不渲染預算欄／「已超支」／橫幅 | [rm:Q6] [stories AC-1.16] |
| 每日時數整數 0–24；Sidebar 可見標籤「系統管理」 | [stories Q6／AC-1.1] |
| 不寫 C2／C3、egress、核准流、inbox | [stories Won't Have] |

## Sources

- [rm] `../../ideation/rough-mockups/wireframes.md`、`user-flow.md`
- [stories] `../user-stories/stories.md`、`personas.md`
- [req] `../requirements-analysis/requirements.md`
- [tp] `../practices-discovery/team-practices.md`
- [code] `frontend/src/components/Sidebar.tsx`、`Layout.tsx`、`pages/WorkspacePage.tsx`（HEAD 無 chart 函式庫、無 Cost 頁）

---

## Q1. 圓餅怎麼畫？（HEAD 沒有 chart 套件）

> FR-3.4 要圓餅另附文字清單。現有 frontend 沒有 recharts／Chart.js。本輪要能被 Playwright 讀到四類金額，也要滿足「不只靠顏色」。

A. **本輪自畫 SVG 圓餅**（或等價向量），旁附四類文字清單（類別名＋已定價金額）；色塊同時出現在圖例文字旁。不新增 npm 依賴。**（建議）**
B. **引入一個輕量圖表套件** 畫圓餅，文字清單仍必備。代價：新依賴要進 CI／lockfile，超出「沿用既有前端驗證層」的慣例。
C. **本輪只做文字清單＋色點圖例**，幾何圓餅留下一輪。代價：字面上不滿足 FR-3.4「圓餅」。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 本輪自畫 SVG 圓餅＋四類文字清單，不新增 npm 依賴。

---

## Q2. 每日時數的就地控件長什麼樣子？

> 合法值整數 0–24；非法不送出並有列旁文字錯誤；改完就地重算總額（`aria-live`）。

A. **數字輸入框**：可鍵入；失焦或 Enter 送出；非法時保留焦點並顯示錯誤，不打 API。**（建議）** 對齊「就地改」與鍵盤操作。
B. **僅 stepper（+/-）**：只走合法整數，沒有自由鍵入。代價：從 24 改到 8 要連點，FinOps 對帳時也不便貼上數字。
C. **數字框 + stepper** 並存。代價：兩套焦點路徑，窄視窗更擠。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 數字輸入框：可鍵入；失焦或 Enter 送出；非法時保留焦點並顯示錯誤，不打 API。

---

## Q3. 進產品超支橫幅釘在哪裡？

> 每次進入受保護頁都看到一條；可鍵盤啟動「前往成本畫面」。現有 Layout 是 Sidebar + 主區。

A. **主區最上方、Sidebar 右側**（在頁面標題／內容之上），登入後各受保護頁共用同一條。**（建議）** 不擋 Sidebar 導覽，橫幅寬度跟主內容走。
B. **視窗最頂、跨 Sidebar 全寬**。代價：會壓到「Cloud-360」品牌列，與既有 header 搶高。
C. **只在成本頁頂** 再做一條，進產品改用主區橫幅但較矮。代價：兩種橫幅樣式，AC-7.3 的「任一受保護頁」仍要有一條。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 主區最上方、Sidebar 右側（在頁面標題／內容之上），登入後各受保護頁共用同一條。

---

## Q4. FinOps 指定 SKU 與覆寫小時價，就地編輯的密度？

> Q 已定就地編輯。未定價列要指定 SKU；官方價失敗列要覆寫小時 list price。HEAD 表格列很密。

A. **同一列表格內**：未定價列出現 SKU 文字欄（可輸入或選唯一碼）；失敗列出現小時價欄。列上狀態文字切換「N 項尚未定價」／「官方價取得失敗」／「Manual Override」。**（建議）** 對齊線框與 C1-5。
B. **列上只有「補價」按鈕，點開列內展開列（accordion）再編**。代價：多一次點擊，但主表較乾淨。
C. **列上就地，SKU 用小型 combobox**（可搜尋對照表）。代價：combobox 無障礙比文字欄難，設計規格較長。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 同一列表格內：未定價列出現 SKU 文字欄；失敗列出現小時價欄。列上狀態文字切換「N 項尚未定價」／「官方價取得失敗」／「Manual Override」。

---

## Q5. 成本頁與既有畫面的視覺契約？

> 新頁，但產品已有 Sidebar、表格、按鈕、空狀態。Playwright 只認得出穩定標籤與文字。

A. **沿用現有 Tailwind 與按鈕／下拉／表格樣式**；成本頁特化只限：數字右對齊、總額字級大於列、超支用既有危險色 token 加「已超支」文字。不另做 Cost 品牌色。**（建議）**
B. **成本頁用更密的財務表**（等寬數字、較小 gutter），其餘控件仍用現有元件。
C. **新開一套 Cost 視覺語言**（獨立色票、卡片儀表板）。代價：與 Workspace／Admin 不一致，超出本輪 Must。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 沿用現有 Tailwind 與按鈕／下拉／表格樣式；成本頁特化只限：數字右對齊、總額字級大於列、超支用既有危險色 token 加「已超支」文字。不另做 Cost 品牌色。

---

## Consolidated Summary Confirmation

1. **Q1=A** — 自畫 SVG 圓餅＋四類文字清單，不新增 npm 依賴。
2. **Q2=A** — 每日時數用數字輸入框；失焦／Enter 送出；非法不打 API。
3. **Q3=A** — 超支橫幅在主區最上方、Sidebar 右側，各受保護頁共用。
4. **Q4=A** — SKU／小時價在同一列表格內就地編；狀態文字三分。
5. **Q5=A** — 沿用既有 Tailwind／控件；只特化數字對齊、總額字級、危險色＋「已超支」。

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
