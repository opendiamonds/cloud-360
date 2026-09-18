# Bolt Plan — Bolt 序列與交付計畫

> Stage: delivery-planning（Inception 2.8）· Intent: 260802-last-login-column
> 上游來源：`../requirements-analysis/requirements.md`（下稱 requirements）、`../user-stories/stories.md`（下稱 stories）、`../refined-mockups/mockups.md`（下稱 mockups）、`../application-design/components.md`（下稱 components）、`../units-generation/unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`、`../practices-discovery/team-practices.md`（下稱 team-practices）。
> 問答定案：Q1=A（三個 Bolt）、Q2=A（嚴格序列）、Q3=A（stage-major）。

## 適用的既有實務（自 memory 層解析，非本站新定）

| 事項 | 定案 | 來源層 |
|---|---|---|
| Construction worktree 的 base 與 merge target | `ut` | `org.md ## Way of Working` |
| Bolt 分支的合併策略 | **squash-merge**（每個 Bolt 對應 `ut` 上一個 commit） | `team.md`（Construction Bolt 分支走 squash；一般 PR 維持 merge commit） |
| Walking skeleton | **`skeleton: off`** —— 第一個 Bolt 照常跑，無額外 gate 與儀式 | `team.md ## Walking Skeleton` |
| 部署 | **deploy-on-merge** 至自有 staging（`ut` 合併觸發） | `org.md ## Deployment` |
| Bolt 執行 | **嚴格序列**（Q2=A） | 本站定案 |
| Construction 設計階段迭代 | **`stage-major`**（預設，不寫入狀態） | 本站定案（Q3=A） |

## 序列總覽

```
B1  U4  security-reviewer-permission        → 部署 → 驗收
B2  U1  backend-activity-policy             → 部署 → 驗收
    U2  user-object-serialization
B3  U5  api-type-contract                   → 部署 → 驗收
    U3  admin-page-column
```

**DAG 相容性**：本序列**完全尊重** `unit-of-work-dependency.md` 的四條邊 —— U2 在 U1 之後（同 Bolt 內先後）、U5 在 U2 之後、U3 在 U2 與 U5 之後。**無拓樸順序的偏離**，故 `risk-and-sequencing-rationale.md` 無須記載偏離理由（僅記載為何在多條合法序中選這一條）。

---

## B1 — 權限開通

**包含單元**：U4 `security-reviewer-permission`（元件 C-7）

**Walking skeleton 標記**：否（`team.md` 定案 `skeleton: off`；且本 Bolt 不打通新架構）

**Definition of Done**：

- 兩處預設值來源（種子資料模組、初始化腳本）皆已翻轉為開啟，且一致
- 啟動補丁已實作，**位於既有權限種子之後**，且**只更新不插入**
- 條件式套用以既有的「最後異動者」欄位為標記
- 授權矩陣的 **allow/deny 雙向測試**通過（requirements NFR-4、team-practices 規則 A）
- 依 requirements C-4 同步 schema 檔與部署文件
- 啟動時記錄三態：已套用／已跳過／**未命中目標列**
- 部署後**人工核對**目標角色確實能進入管理頁（stories AC-3.1a 在現行 e2e 無可執行驗收路徑，此為承接方式）

**信心假說**：*「權限資料的變更能在既有環境真的生效，而不是只改了預設值。」*

這是本 intent 最容易靜默落空的一條 —— 種子函式只在空表寫入、requirements C-3 又禁止重跑整份腳本，若沒有專屬的套用機制，改了預設值在 staging 上完全沒有效果而 CI 全綠。先做這個 Bolt 就是要**先證偽這件事**。

**預期展示**：以目標角色登入 staging，導覽出現使用者管理入口，能進入頁面並看到完整清單；另以未獲授權角色登入，確認看不到。

**已知風險**（見 `risk-and-sequencing-rationale.md`）：順序或插入行為錯誤會清空整份權限矩陣，且**沒有任何測試會發現**。

---

## B2 — 後端寫入與回應契約

**包含單元**：U1 `backend-activity-policy`（C-1、C-2、C-3）＋ U2 `user-object-serialization`（C-4）

**為何合併**：U2 在 DAG 上只依賴 U1，兩者共同交付「資料真的被記錄，且真的出現在 API 回應裡」這一個可驗證的整體。分開會讓 U1 單獨部署時只有「欄位存在但沒有任何讀取路徑」的中間態 —— 那湊不出有意義的信心假說。

**Walking skeleton 標記**：否

**Definition of Done**：

- C-1 的兩個判定為純函式，邊界可直接斷言（5 分鐘含等於、90 天不含等於、無紀錄態）；含 property-based 測試
- C-2 **自行提交**，失敗**先復原再記錄**（契約，非實作細節）
- C-3 的欄位可為空、帶時區、無資料庫層預設值；補欄補丁可重複執行
- 依 requirements C-4 同步 schema 檔與部署文件
- **三個構造點**（清單、啟停用、角色調整）皆帶出兩個新欄位；兩欄不得設可靜默通過的預設值，或改走共用工廠函式
- 測試客戶端測試斷言 status code 與回應欄位集合（requirements NFR-5、team-practices 規則 B）
- 部署後完成一次服務重啟（requirements C-2、stories AC-1.7），並確認欄位已存在

**信心假說**：*「任何認證請求都會被記錄，且所有回傳使用者物件的端點都帶得出這兩個欄位。」*

**預期展示**：以測試帳號發任一認證請求後查詢資料庫，該帳號的最後活動時間為該時刻；連續請求 5 分鐘內只寫一次；對三個端點各發一次請求，回應皆含兩個新欄位。

**已知的驗證缺口**：C-2 的交易契約與 C-3 的補欄**皆無自動化驗證**（純函式測試不碰資料庫、端點測試只斷言回應欄位）。承接方式為部署後重啟與人工核對。

---

## B3 — 型別契約與前端呈現

**包含單元**：U5 `api-type-contract`（C-8）＋ U3 `admin-page-column`（C-5、C-6）

**為何合併**：U3 在 DAG 上依賴 U5，且 U5 **沒有對應的使用者故事** —— 單獨部署一個型別產生機制沒有可展示的東西，也湊不出使用者可驗證的假說。合併後 B3 的展示就是本 intent 的核心價值：稽核者在管理頁看到最後活動時間。

**Walking skeleton 標記**：否

**Definition of Done**：

- 規格 dump 腳本、committed 規格檔（repo 根目錄）、committed 型別檔（前端原始碼目錄）皆到位
- **兩道 CI 漂移檢查**：規格檔的在 backend job、型別檔的在 frontend job
- 兩支關鍵函式庫以**精確等值**釘選；依賴鎖定檔已重產並 commit
- 產生器**只輸出型別宣告**，不輸出進入 bundle 的執行期程式碼
- 型別檔的 lint 作用域已定案（納入或明文排除）
- 表格新增欄位，位置為角色之後、操作之前；無紀錄態為可聚焦破折號；逾期標示含圖示且非僅色彩傳達
- 小螢幕斷點以下改用卡片佈局，標示語彙跨佈局一致
- **顯示端的在地化策略已定案**（AC-1.6 的驗收面 —— 上游未定，屬本 Bolt 必答）
- Playwright e2e 斷言表頭出現該欄位、且至少一列顯示時間值或無紀錄態（requirements NFR-6、team-practices 規則 C）
- 依 mockups 的規格呈現五種狀態

**信心假說**：*「稽核者能在管理頁一眼看出哪些帳號已逾期未活動，且後端改欄位形狀時前端會在建置時失敗而非執行期靜默。」*

**預期展示**：以目標角色登入，管理頁出現「最後活動時間」欄；有活動的帳號顯示絕對時間、逾期者帶 `(!)` 圖示且變色、無紀錄者顯示可聚焦破折號；縮小視窗至斷點以下改為卡片；另刻意改一個後端欄位名而不重新 dump 規格，確認兩道 gate 變紅。

**最後一項展示同時驗證了 U5 的 gate 本身有效** —— 那是自我驗證機制唯一的外部檢查方式。

---

## Bolt 間的交付約束

| 約束 | 說明 |
|---|---|
| **B1 必須在 B2／B3 之前** | 非 DAG 的**驗收依賴**：主要 persona（`Security_Reviewer`）要有權限才能親自驗收 B2／B3 的成果。deploy-on-merge 之下，若顯示鏈先上而權限未上，那次部署對主要 persona 不可驗收 |
| **B2 必須在 B3 之前** | DAG：U5 依賴 U2、U3 依賴 U2 |
| **B1 與 B2／B3 無程式碼耦合** | B1 動權限表、B2／B3 動使用者表。B1 的位置是經濟選擇，不是拓樸強制 |
| **B3 內部有合併順序約束** | US-1 的欄面、US-2 的標示、US-4 的卡片佈局**修改同一段前端程式碼**（stories 明載），須序列合併避免衝突 |
| **B1 與 B2 皆需部署後重啟** | 兩者的變更都在啟動流程（權限套用、補欄），requirements C-2 |

## 每個 Bolt 的分支與合併

依 `team.md` 的既有規則：

- **分支命名**：`danniel/feat/<slug>` —— 型別為英文小寫；本 intent 三個 Bolt 的 slug 建議沿用單元名（`security-reviewer-permission`、`backend-activity-policy`、`api-type-contract`），Construction 開工時確認
- **Commit message 與 PR 標題**：繁體中文、中文 type（`功能`／`測試`／`整合` 等），scope 維持英文
- **合併方式**：**squash-merge**（Bolt 分支專用）
- **合併目標**：`ut`

## 本計畫未涵蓋的事

| 事項 | 為何不在此 |
|---|---|
| 各 Bolt 的工時估計 | 本專案單一決策者、無工時追蹤實務；複雜度以 S/M/L 相對估計表達（見 `unit-of-work.md`） |
| WSJF／RICE 數值分數 | `project.md` 已定案不做 —— 沒有真實輸入的相對分數是虛假精確 |
| Construction 各 stage 的執行深度 | 屬 `/aidlc` 的 scope 解析，非本站決定（stage 檔明文） |
| 回滾程序 | 既有的 `deploy.yml` 已有 rollback job（還原 last-good、開 revert PR、dispatch 自癒 workflow），本 intent 不改變它 |

---

## Revision 1（2026-08-11）— PU-6 使用者清單分頁

**Bolt 數維持 3、嚴格序列維持、stage-major 維持**（Q1〜Q3 不變）。**Bolt 的內容改變**：依 Q4=A，U2 由 B2 移至 B3。

### 序列總覽（Revision 1）

```
B1  U4  security-reviewer-permission        → 部署 → 驗收
B2  U1  backend-activity-policy             → 部署 → 驗收
B3  U2  user-object-serialization           → 部署 → 驗收
    U5  api-type-contract
    U3  admin-page-column
```

**為何 U2 從 B2 移到 B3**：U2 現在包含 C-9 後端，它把 `/api/auth/list` 從裸陣列改為 envelope —— 這是**破壞性契約變更**，而本專案是 **deploy-on-merge**。若 U2 隨 B2 合併，staging 上後端回 envelope 而前端仍 `.map()` 一個物件，使用者管理頁會**壞掉並持續壞到 B3 合併為止**（`tsc -b` 抓不到、既有 e2e 也抓不到）。破壞性契約變更必須與它唯一的消費端在**同一次部署**內落地。

**DAG 相容性**：新序列仍完全尊重四條邊（U2 在 U1 之後、U5 在 U2 之後、U3 在 U2 與 U5 之後），無拓樸偏離。

---

### B1 — 權限開通（**內容不變**）

U4 `security-reviewer-permission`。DoD、信心假說、預期展示、已知風險**全部不變** —— C-9 不觸及權限表。

---

### B2 — 後端活動記錄（**範圍縮小**）

**包含單元**：U1 `backend-activity-policy`（C-1、C-2、C-3）。**U2 已移出。**

**為何 U1 單獨成 Bolt 是合理的**（回答「這湊得出信心假說嗎」）：Revision 1 之前的計畫說 U1 單獨部署只有「欄位存在但沒有任何讀取路徑」的中間態、湊不出假說。加入分頁後這個判斷要更新 —— 不是因為 U1 變了，而是因為**替代方案會弄壞 staging**，且 U1 本身其實有一條**明確且高價值**的假說：

**信心假說**：*「任何認證請求都會被記錄，且既有環境的補欄在部署後重啟真的生效。」*

這正是本 intent **最容易靜默落空**的一條 —— C-2 的交易契約（自行提交）與 C-3 的補欄（AC-1.7）**皆無自動化驗證**，計畫既有記載的承接方式本來就是「部署後重啟 ＋ 人工核對」。把它單獨拉出來先證偽，比埋進一個更大的 Bolt 好。

**Definition of Done**（不變）：

- C-1 的兩個判定為純函式，邊界可直接斷言（5 分鐘含等於、90 天不含等於、無紀錄態）；含 property-based 測試
- C-2 **自行提交**，失敗**先復原再記錄**
- C-3 的欄位可為空、帶時區、無資料庫層預設值；補欄補丁可重複執行
- 依 requirements C-4 同步 `schema_rbac.sql` 與 `DEPLOY.md`（blocking）
- 部署後完成一次服務重啟，並確認欄位已存在

**預期展示**：以測試帳號發任一認證請求後查詢資料庫，該帳號的最後活動時間為該時刻；連續請求 5 分鐘內只寫一次；查詢既有帳號的資料表確認新欄位存在。**展示在資料庫層，不在 UI** —— 這是本 Bolt 的性質，如實記載。

**已知的驗證缺口**（不變）：C-2 的交易契約與 C-3 的補欄皆無自動化驗證。

---

### B3 — 回應契約、型別契約與前端呈現（**範圍擴大**）

**包含單元**：U2 `user-object-serialization`（C-4 ＋ C-9 後端）＋ U5 `api-type-contract`（C-8）＋ U3 `admin-page-column`（C-5、C-6 ＋ C-9 前端）

**為何三個單元同一個 Bolt**：不是為了湊大，是**部署模型逼出來的**。U2 的 envelope 是破壞性契約變更，必須與消費端同一次部署；U5 在 DAG 上依賴 U2、U3 依賴 U2 與 U5，三者無法拆到不同的部署批次而不製造壞掉的中間態。**這是本計畫最大的一塊（L ＋ M ＋ XL），如實記載，不粉飾。**

**Definition of Done**：

*U2 的部分：*
- 三個 `UserSchema` 構造點（清單、啟停用、角色調整）皆帶出兩個新欄位；兩欄**不得設可靜默通過的預設值**
- envelope `UserListPage` 的四欄**皆必填、皆無預設值**（它是第四個回應構造點）
- `total` 為**獨立的計數查詢**，不得由 `len(items)` 導出
- 保留既有的 `ORDER BY id`（AC-5.3 的結構前提）
- 兩個查詢參數以**框架原生範圍約束**宣告（頁次 ≥1；每頁筆數 1〜100，預設 20），非法值回 422 且不回傳帳號資料
- 超出範圍的頁次回 200＋空 `items`，`page` 回顯請求值不夾頁
- 端點測試斷言：欄位**值**（非存在性）、分頁三值、422、邊界、非分頁參數不改變結果集

*U5 的部分（不變，範圍略增）：*
- 規格 dump 腳本、committed 規格檔（repo 根）、committed 型別檔（前端原始碼目錄）
- **兩道 CI 漂移檢查**：規格檔在 backend job、型別檔在 frontend job
- 兩支關鍵函式庫**精確等值**釘選；依賴鎖定檔重產並 commit
- 型別檔的 lint 作用域已定案
- **規格現含 `UserListPage` schema 與兩個查詢參數的範圍約束**

*U3 的部分：*
- 表格新增欄位（角色之後、操作之前）；無紀錄態可聚焦破折號；逾期標示含圖示且非僅色彩
- 小螢幕斷點以下改卡片佈局，標示語彙跨佈局一致
- **顯示端的在地化策略已定案**（AC-1.6 的驗收面）
- **分頁控制**：頁碼式、渲染於表格／卡片容器**之外**、單頁與邊界皆「呈現但停用」、目前頁碼以**方括號＋字重**為非色彩線索
- **三種抓取路徑對應三種畫面行為、互不共用旗標**：初次載入＝既有 `isLoading`；切頁＝新設 `isBusy`；**刪除後重抓＝無旗標**（不得沿用 `fetchUsers()`）
- **`:113`（啟停用）、`:129`（刪除）、`:91-94`（失敗路徑）三處現行整份重抓皆須改**
- 逾期旗標的正規化**收斂在抓取函式內**（切頁是第三個呼叫點）
- 重疊重抓的併發保護（序號或 `AbortController` 擇一）
- e2e：以公開註冊端點造超過一頁的帳號；斷言表頭與列值、分頁控制、切頁、處置後維持頁次；小螢幕 viewport

**信心假說**：*「稽核者能在管理頁逐頁看完所有帳號、一眼看出哪些逾期，且在任一頁做完處置後仍停在那一頁；後端改欄位形狀時前端會在建置時失敗而非執行期靜默。」*

**預期展示**：以目標角色登入 staging，管理頁出現「最後活動時間」欄；有活動的帳號顯示絕對時間、逾期者帶 `(!)` 且變色、無紀錄者顯示可聚焦破折號；**清單分頁，可跳頁，總筆數正確**；**在第 2 頁停用一個帳號後仍在第 2 頁**；縮小視窗至斷點以下改為卡片且分頁控制簡化呈現；另刻意改一個後端欄位名而不重新 dump 規格，確認兩道 gate 變紅。

**已知風險**：這是三個 Bolt 中唯一同時動後端契約、建置資產與前端的一塊。**若它出問題，回滾的是整條顯示鏈**（B1 的權限與 B2 的記錄不受影響 —— 這也是把它們排在前面的附帶收益）。

---

## Bolt 間的交付約束（Revision 1 更新）

| 約束 | 說明 |
|---|---|
| **B1 必須在 B2／B3 之前** | 非 DAG 的驗收依賴（不變）：主要 persona 要有權限才能親自驗收 |
| **B2 必須在 B3 之前** | DAG：U2 依賴 U1 |
| **U2 不得單獨部署** | **Revision 1 新增**：envelope 是破壞性契約變更，deploy-on-merge 下若與消費端分屬兩次部署，staging 的管理頁會壞在中間 |
| **B3 內部有合併順序約束** | US-1／US-2／US-4／US-5 動同一段 JSX，**四則**須序列合併（Revision 1：由三則增為四則）。具體排法屬實作時的選擇，`stories.md` 只建立集合層級的約束 |
| **B1 與 B2 皆需部署後重啟** | 不變（權限套用、補欄皆在啟動流程）。**B3 不需要** —— 純程式碼變更，隨映像部署即生效 |

## 每個 Bolt 的分支與合併（Revision 1 更新）

- **分支命名**：`danniel/feat/<slug>`。三個 Bolt 的建議 slug：`security-reviewer-permission`、`backend-activity-policy`、**`user-list-column-and-pagination`**（B3 已含三個單元，沿用單一單元名會誤導）
- **Commit message 與 PR 標題**：繁體中文、中文 type，scope 維持英文
- **合併方式**：squash-merge（Bolt 分支專用）
- **合併目標**：`ut`
