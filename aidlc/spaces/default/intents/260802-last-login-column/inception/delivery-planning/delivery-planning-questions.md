# Delivery Planning — 釐清問題

> Stage: delivery-planning（Inception 2.8）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> **每題均附建議選項**，建議理由與代價寫在選項描述內。
> **成本揭露**：本題組共 3 題。本站**無 reviewer**（stage 檔未宣告），故流程為出題 → 產出 4 份 artifact + 階段邊界驗證 → §13 learnings → 核可 gate。這是 Inception 的最後一站。

## 已由既有規則定案、不重問

| 事項 | 定案來源 |
|---|---|
| **不做 WSJF／RICE 數值評分** | `project.md`：單一決策者、全 Must、依賴序已定的 backlog，沒有真實輸入的相對分數是虛假精確；以 MoSCoW＋依賴序表達優先即足 |
| **`skeleton: off`** | `team.md` Q3 定案。第一個 Bolt 照常跑，不需額外的 gate 與儀式 |
| **Bolt 分支走 squash-merge** | `team.md` PR 合併方式（Construction Bolt 分支 squash，一般 PR 維持 merge commit） |
| **部署模型** | `org.md`／`project.md`：deploy-on-merge 至自有 staging，Construction 與 Operations 連續 |
| **外部依賴：無** | 本 intent 全部落在自有 repo 與自有 staging。無外部 API、無資料可得性窗口、無審批前置期、無外部團隊交接。`external-dependency-map.md` 將如實記為近空白，不虛構條目 |
| **團隊配置：單人** | `team-formation`（1.5）在本 workflow 為 `[S]` skipped；本專案單一決策者 |

## 上游拓樸（本站排序的輸入，不重新推導）

- **DAG 四條邊**：U2→U1、U5→U2、U3→U2、U3→U5。**U4 在程式碼依賴上與所有單元零關係**。
- **非 DAG 的驗收依賴**：`Security_Reviewer`（主要 persona）要親自驗收 U1／U2／U3 交付的「看得到最後活動時間」，**需要 U4 已到位** —— 否則進不了管理頁。
- **複雜度**：U3=L（13 條 AC、整頁響應式改造、repo 第一個管理頁 e2e）；U1／U2／U4／U5 皆為 M。
- **失敗模式隱蔽度最高的兩個**：U4（順序錯會清空 308 列權限矩陣且無測試發現）、U1（交易契約與補欄皆無自動化驗證）。

---

## 一個你應該先知道的成本數字

Construction 的 **3.1〜3.5 五個 stage 全部是 `for_each: unit-of-work`**（逐單元執行），且每個 per-unit 執行都有自己的 reviewer 與 iteration 預算。

以已核可的 **5 個單元**計：

| Stage | Execution | 逐單元？ | 本 intent 的執行次數 |
|---|---|---|---|
| 3.1 functional-design | CONDITIONAL | 是 | 至多 5 |
| 3.2 nfr-requirements | CONDITIONAL | 是 | 至多 5 |
| 3.3 nfr-design | CONDITIONAL | 是 | 至多 5 |
| 3.4 infrastructure-design | CONDITIONAL | 是 | 至多 5 |
| 3.5 code-generation | ALWAYS | 是 | **5** |
| 3.6 build-and-test | ALWAYS | 否 | 1 |
| 3.7 ci-pipeline | CONDITIONAL | 否 | 至多 1 |

**這個數字由單元數決定，不由 Bolt 數決定** —— Bolt 粒度影響的是部署次數與交付節奏，不是設計階段的執行次數。5 單元的切分已在 2.7 核可，本站不重開。

**但有一個可能的收斂點值得你知道**：3.3（NFR 設計）與 3.4（基礎設施設計）都是 CONDITIONAL，而本 intent 依 AD-5 **不新增服務、不新增執行單元、不新增部署單元**，基礎設施完全不動。若判定這兩站對本 intent 不適用，逐單元的執行次數可從至多 25 降到至多 15。這屬於 workflow plan 的重塑（`/aidlc compose` 或直接指名要 skip 哪些 stage），**不是本站的決定** —— 我只是把它擺在你看得到的地方。

---

## Q1. Bolt 粒度與序列

> Bolt 的定義是「一次通過 Construction 3.1〜3.7 的可部署工作單位」，可包一或多個 Unit。本專案 deploy-on-merge，**每個 Bolt 合併即部署**。
>
> 序列**必須尊重 DAG**（U2 在 U1 後、U5 在 U2 後、U3 在 U2 與 U5 後），但 U4 的位置完全自由 —— 那正是本站要決定的經濟選擇。

A. **三個 Bolt：`U4` → `U1+U2` → `U5+U3`** — **（建議）**
   - **B1 = U4（權限開通）**：先上的理由有三 —— ①它是**驗收依賴的前提**，主要 persona 要有權限才能驗收後續任何東西；②它是**失敗模式最隱蔽**的一個（順序錯會清空整份權限矩陣、既有環境套用無自動化驗證），最該早驗；③它與所有單元零耦合，先上不阻擋任何後續工作。
   - **B2 = U1+U2（後端寫入 + 回應契約）**：兩者相鄰於 DAG（U2 只依賴 U1），且共同交付「資料真的被記錄且真的出現在 API」這一個可驗證的整體。分開會讓 B 只有「欄位存在但沒人讀」的中間態。
   - **B3 = U5+U3（型別契約 + 前端呈現）**：U3 依賴 U5，且 U5 沒有獨立的使用者價值（無故事）—— 單獨部署一個型別產生機制沒有可展示的東西。合併後 B3 的展示就是「稽核者在管理頁看到時間欄」。
   - 代價：B2 部署後有一段「後端已記錄但前端還沒顯示」的中間態。可接受 —— 該態對使用者無害（沒有壞掉的東西，只是還沒有新東西）。

B. **五個 Bolt，一單元一個** — 順序 `U4 → U1 → U2 → U5 → U3`
   - 好處：每個 Bolt 最小，回滾粒度最細。
   - 代價：五次通過 3.6／3.7 與五次部署；且其中兩個 Bolt（U2 單獨、U5 單獨）**沒有可展示的成果** —— U2 交付「回應多兩個欄位但沒人看」、U5 交付「一個型別檔」。Bolt 的定義帶有「可部署 + 有信心假說」的意涵，這兩個湊不出有意義的假說。

C. **兩個 Bolt：`U4` → `U1+U2+U5+U3`**
   - 好處：儀式最少。
   - 代價：B2 把 L 級的 U3 與其他三個綁在一起，一次部署涵蓋 13+9+3+0 = 25 條 AC 的驗收面。若出問題，回滾粒度是整個功能。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. Bolt 能否並行通過 Construction

> 承 Q1。若允許並行，無依賴關係的 Bolt 可同時進行設計與實作。

A. **嚴格序列** — **（建議）**
   - 本專案是單人開發、單一整合主幹（`ut`）、deploy-on-merge。並行的前提是有多個執行者，而這裡沒有。
   - 且 U1／U2／U3 之間有 DAG 邊，本來就不能並行；唯一可並行的是 U4，而 Q1 的建議已把它排在最前。
   - 代價：無 —— 在單人情境下「並行」不是真實選項。

B. **允許並行** — 標示哪些 Bolt 可同時進行。
   - 代價：在單人開發下這只是名義上的並行，實際仍是序列執行；標了反而讓計畫與現實不符。

C. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. Construction 設計階段的迭代方式

> stage 檔 Step 7 要求本站判定 Construction 的四個 inline 設計階段（3.1〜3.4）如何逐單元迭代。兩種模式的 **gate 總數相同**（每個 stage 一次人工核可），差別在**順序與設計連貫性**。

A. **`stage-major`（預設）** — 每個設計階段跑完所有單元，再進下一個階段 — **（建議）**
   - 例：3.1 對 U1〜U5 各做一次 → gate → 3.2 對 U1〜U5 各做一次 → gate → ⋯
   - 好處：**同一個設計問題在五個單元間可橫向比較**，容易發現不一致（例如五個單元對錯誤處理的態度是否一致）。本 intent 的單元彼此形狀差異大（service／ui／packaging），橫向比較有實際價值。
   - 這是預設值，不需要額外寫入狀態。
   - 代價：單一單元的四份設計文件會分散在四個時間點產出，該單元的設計連貫性較弱。

B. **`unit-major`** — 一個單元的四份設計文件連續產出，再換下一個單元
   - 好處：單一單元的設計連貫性強。
   - 代價：四個 gate 會**延後並在設計區塊末尾串聯觸發**（stage 檔明文），也就是你會在很後面一次面對四個核可；且橫向比較的機會消失。

C. Not yet defined
X. Other (please specify)

[Answer]: A

---

# Revision 1（2026-08-11）— PU-6 使用者清單分頁

> **觸發來源**：units-generation Revision 1 把 C-9 拆兩半併入 U2（後端）與 U3（前端），U2 複雜度 M→L、U3 L→XL。Q1〜Q3 的答案**一律不動**（三個 Bolt、嚴格序列、stage-major）—— 但 Bolt 的**內容**必須重審，理由見 Q4。
>
> **本節新增 1 題。**

## Q4. U2 的 envelope 是破壞性契約變更，而本專案是 deploy-on-merge —— B2／B3 的邊界要怎麼調？

> **這是本輪唯一真正的新問題，且它會讓 staging 壞掉。**
>
> 現行計畫是 B2 = U1 ＋ U2、B3 = U5 ＋ U3。加入 C-9 之後，U2 把 `/api/auth/list` 的回應從 `List[UserSchema]` 裸陣列改為 envelope（AD-10）。而 `org.md` 的部署模型是 **deploy-on-merge**：**每個 Bolt 合併進 `ut` 就會部署到 staging**。
>
> 於是 B2 合併的當下：後端回 envelope，而前端 `AdminPage.tsx:44-48` 仍把回應宣告為 `DbUser[]`、`:56` 直接 `.then(setUsers)`、`:178` 對它 `.map()` —— **`users` 變成一個物件，`.map` 不是函式，使用者管理頁在 staging 上直接壞掉**，並且會一直壞到 B3 合併為止。`tsc -b` 抓不到（`res.json()` 是 `any`），既有 e2e 也抓不到（六個 case 無一進管理頁）。
>
> 這不是理論風險，是 deploy-on-merge ＋ 破壞性契約變更 ＋ Bolt 邊界三者相加的算術結果。

A. **把 U2 移進 B3，B2 只留 U1** —— **（建議）** B1 = U4；**B2 = U1**；**B3 = U2 ＋ U5 ＋ U3**。破壞性契約變更與它唯一的消費端在**同一次部署**內落地，staging 不會出現壞掉的中間態。代價：①B3 變大（L ＋ M ＋ XL）；②B2 只剩 U1，其成果在 UI 上不可見 —— 但它**仍湊得出信心假說**：「任何認證請求都會被記錄，且既有環境的補欄在部署後重啟真的生效」，而這正是計畫既有記載中**最容易靜默落空**的一條（C-2 的交易契約與 C-3 的補欄皆無自動化驗證，承接方式本來就是「部署後重啟 ＋ 人工核對資料庫」）。B2 因此不是無法驗收的中間態，而是把那條缺口單獨拉出來先證偽。
B. 維持 B2 = U1 ＋ U2，接受 staging 在兩次部署之間壞掉 —— 代價：主要 persona 在那段期間完全無法使用管理頁；且 B2 的「預期展示」本來就包含對三個端點發請求驗證回應欄位，那時前端已壞，展示只能在 API 層做。不可接受。
C. 維持 B2 = U1 ＋ U2，但在 B2 內加一小段前端相容處理（同時接受兩種回應形狀）—— 代價：那段程式碼屬 C-9 前端＝U3，會把一個單元拆到兩個 Bolt；且相容層是必然要再刪掉的臨時碼，等於為了維持 Bolt 邊界而增加工作與風險。
D. 把 B2 與 B3 合併為單一 Bolt —— 代價：等於放棄 Q1=A 的三 Bolt 結構，且 U1 的「補欄在既有環境真的生效」這條高風險缺口會被埋進一個更大的 Bolt，失去單獨證偽的機會。
X. Other (please specify)

[Answer]: A. 把 U2 移進 B3，B2 只留 U1（採納建議：破壞性契約變更必須與其消費端同一次部署落地；B2 單獨證偽補欄缺口反而是收益）

## Consolidated Summary Confirmation — Revision 1

| # | 決定 | 影響 |
| --- | --- | --- |
| Q4 | B1 = U4；**B2 = U1**；**B3 = U2 ＋ U5 ＋ U3** | Bolt 數維持 **3**（Q1=A 不變）、嚴格序列不變（Q2=A）、stage-major 不變（Q3=A）。三個 Bolt 的 DoD、信心假說與預期展示全部重寫 |

**DAG 相容性複驗**：新序列 U4 → U1 → (U2 → U5 → U3) 仍**完全尊重** `unit-of-work-dependency.md` 的四條邊 —— U2 在 U1 之後、U5 在 U2 之後、U3 在 U2 與 U5 之後。無拓樸偏離。

**範圍影響**：不擴大範圍 —— 本站只調整交付邊界。

Does this look correct before I revise the Bolt plan?

A. Looks correct
B. Request changes

[Answer]: A. Looks correct（2026-08-11）
