# Functional Design — 釐清問題 · U3 `admin-page-column`

> Stage: functional-design（Construction 3.1）· Unit: `admin-page-column`（kind: ui）· Depth: Standard
> **每題均附建議選項**。**成本揭露**：本題組 3 題。本站有 reviewer（`reviewer_max_iterations: 2`）。本單元為 `unit-of-work.md` 唯一的 **L 級**單元（13 條 AC），與 U5 同屬 **B3**。

## 已由上游定案、不重問

| 事項 | 定案來源 |
|---|---|
| **時間格式 `YYYY-MM-DD HH:MM`** | `refined-mockups-questions.md` 前言列為「已由上游定案、不重問」 |
| 逾期門檻 90 天（**嚴格大於**，不含恰為 90 天） | 同上；判定邏輯屬 U1 |
| 欄位位置：角色之後、操作之前（全表共 6 欄） | 同上 |
| 無紀錄態為**可聚焦破折號** `—`，帶說明文字 | 同上 |
| 逾期標示**非僅以顏色傳達**（圖示 + 變色，圖示帶文字替代） | 同上 |
| 響應式斷點 **768px（Tailwind `md`）以下切換卡片** | `refined-mockups-questions.md` Q3 |
| 五種狀態的完整視覺規格與可及性屬性 | `refined-mockups/interaction-spec.md`、`design-system-mapping.md` |
| **不引入等寬字體** | `design-system-mapping.md` |
| 載入態與錯誤態**沿用既有整塊替換模式**，不做骨架 | stories AC-1.9 |
| 逾期旗標由 **API 傳入**，元件不自行計算 | `component-methods.md` C-5；U2 已定案來源 |
| 使用者物件型別改採 **U5 產生的型別**，不再手寫 | `component-methods.md` C-6（Revision 1） |

## Sources（出題前的唯讀查證）

| # | 查證 | 結果 |
|---|---|---|
| S1 | 前端既有時間顯示實務 | **4 處**，全部為 `new Date(iso).toLocaleString()` 或 `.toLocaleDateString()`，**皆無參數** |
| S2 | i18n／日期函式庫 | **零** —— `package.json` 無 i18n、date-fns、dayjs、luxon、moment |
| S3 | Playwright config | **既未設 `locale` 也未設 `timezoneId`**；單一 chromium project |
| S4 | 既有 e2e | 單一 `regression.spec.ts`、6 個 case（身分驗證 4、RBAC 2），**無一導覽至 Admin 頁** |
| S5 | `AdminPage.tsx` 既有表頭 | 5 欄：使用者／授權狀態／角色／操作／啟用 —— 新欄插在「角色」之後為第 4 欄，合計 6 欄 |
| S6 | `AdminPage.tsx` responsive class | **幾乎沒有**（僅 `md:p-`）；卡片佈局是全新的 |
| S7 | 全前端 `matchMedia`／`innerWidth`／`useMediaQuery` | **零使用**，無先例可循 |
| S8 | 空值佔位先例 | `AuthorizationRequestsPage.tsx:163` 已用 `'—'` 作為空值佔位 |
| S9 | 既有 lint 規則 | `react-hooks/set-state-in-effect` 為 **error 級**（`team.md` 已載明） |

---

## Q1. 顯示端的在地化與時區策略

> `bolt-plan.md` 的 B3 Definition of Done 明列「顯示端的在地化策略已定案（AC-1.6 的驗收面 —— 上游未定，屬本 Bolt 必答）」。

A. **沿用既有實務，並釘住測試環境** — **（建議）**
   - 依 S1，全前端 4 處時間顯示一致採用瀏覽器在地時區。稽核者看到的是**自己所在時區**的時間 —— 對「這個帳號多久沒動了」這種判斷通常正是想要的。
   - 依 S3，Playwright config 既未設 locale 也未設 timezone。**e2e 的不確定性不在顯示選擇，而在未釘住的測試環境**；正確的修法是在 config 釘住兩者，而非為了遷就測試而改產品行為。
   - 代價：要動 Playwright config（小且隱含於測試層的改動）。

B. **固定格式 + 固定 UTC** — 代價：與 4 處既有實務不一致；稽核者須自行換算時區。

C. **固定 zh-TW locale + 固定 Asia/Taipei** — 代價：硬編時區；同樣與既有實務不一致。

D. Not yet defined
X. Other (please specify)

[Answer]: A

> **Revision（本站產出 artifact 前，2026-08-09）**：選項 A 的字面描述「沿用既有實務（無參數 `toLocaleString()`）」**其中的格式部分不成立**，已修正。**原答案不改寫**，以本段向下游傳遞。
>
> - **衝突**：`refined-mockups-questions.md` 前言把**時間格式 `YYYY-MM-DD HH:MM`** 列為「已由上游定案、不重問」，而無參數的 `toLocaleString()` 產出的是 locale 相依格式（如 `8/7/2026, 2:52:52 PM`），不是該格式。上游已核可的決定，下游不得推翻。
> - **拆解後兩者正交**：格式（上游已定）與**時區政策**（本題真正在問的）是兩件事 —— 上游的格式字串沒有指定它是哪個時區的時間。
> - **本題實際定案的部分**：①時間以**瀏覽器在地時區**呈現（而非固定 UTC 或硬編 Asia/Taipei）；②**在 Playwright config 釘住 `locale` 與 `timezoneId`**，使 e2e 具決定性。
> - **未被本題定案、依上游執行的部分**：顯示格式為 `YYYY-MM-DD HH:MM`（補零、24 小時制）。實作上即「帶明確選項的格式化」而非無參數呼叫。
> - **選項 B／C 未被改選** —— 它們主張的是**固定時區**，而本站定案為在地時區。本題不重新作答。

---

## Q2. NFR-7「既有頁面功能不得退化」的桌面回歸落點

> requirements NFR-7 點名三項操作（角色調整、啟停用、授權），但 stories AC-4.3 的 Given 只限定小螢幕的卡片佈局 —— 桌面回歸無 AC 落點。此缺口自 refined-mockups 起追蹤，`phase-check-inception.md` 已標明由本單元承接。

A. **新增桌面 e2e 回歸，涵蓋三項操作** — **（建議）**
   - 依 S4，既有 e2e 只有一支檔案、6 個 case，**無一導覽至 Admin 頁**。本單元本來就要寫 repo 第一個 Admin 頁 e2e（team-practices 規則 C），把三項操作一併涵蓋是在同一支檔案裡多寫幾個 case，不是新建機制。
   - `ui-regression` 每 PR 起短生命週期 stack，變更型操作可安全執行。
   - 代價：本單元已是 L 級，這會再加實作量。

B. **只做最低要求，桌面回歸以人工核對承接**
   - 代價：B3 已有 AC-2.2 對比度靠人工，再加一項會讓這個 Bolt 的驗收大幅傾向人工；且 NFR-7 是 scope 定案的需求，不是選配。

C. **桌面與小螢幕各一支，兩邊都涵蓋三項**
   - 代價：實作量最大；小螢幕那支需 viewport 切換與觸控目標尺寸驗證，屬尚未存在的新測試形狀。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. 小螢幕斷點以下的佈局切換手段

A. **純 CSS：Tailwind responsive class** — **（建議）**
   - 表格與卡片兩份標記都在 DOM 裡，由 `md:` 斷點類別控制顯示。
   - **決定性理由**：依 S9，`react-hooks/set-state-in-effect` 為 **error 級**規則，而 JS 版斷點（掛載時量測視窗寬度並 `setState`）正好撞上它 —— CI 直接紅燈。且依 S7，全前端零 `matchMedia`／`innerWidth` 使用，**無先例可沿用**。
   - 代價：隱藏的那份標記仍在 DOM，須以 `aria-hidden` 避免螢幕閱讀器讀到重複內容（mockups 已定可及性規格，需一併滿足）。

B. **JS 判斷視窗寬度，只渲染一份**
   - 好處：無重複內容、無 `aria-hidden` 問題。
   - 代價：初始量測必須在 effect 內 `setState`，直接違反 error 級 lint 規則；且為 repo 第一個此類實作，無先例可循。

C. Not yet defined
X. Other (please specify)

[Answer]: A

---

# Revision 1（2026-08-11）— PU-6 使用者清單分頁

> **無新問題。** 分頁在本單元的所有設計決定皆已由上游定案，本站只做落地展開，不重問：
>
> - **回應形狀、每頁筆數（20／上限 100）、非法參數處置（框架原生約束→422）** —— application-design 的 AD-10／AD-11（該站問題檔 Revision 1 的 Q8〜Q10）
> - **刪除後的收斂策略、三種抓取路徑的畫面行為、併發保護** —— application-design 的 AD-12
> - **分頁控制的版位、單頁與邊界處置、空清單態、切頁進行中的呈現** —— refined-mockups Revision 1 的定案 5〜9；**44x44 觸控目標**的定案處是 `interaction-spec.md` 的 Accessibility 表 **O-9**（不在定案 5〜9 之內；reviewer Revision 1 Finding 5 更正）
> - **控制項的六個狀態與 props 契約** —— `refined-mockups/interaction-spec.md` 的 `PaginationControl`
> - **本單元擁有哪一半 C-9** —— units-generation Revision 1 的 Q4
>
> 依 `project.md` 的既有 correction（上游已確認的事項不重問，省題並記明清單），本站不新增問題。落地展開的內容見本單元的其他 artifact。
