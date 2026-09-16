# Units Generation — 分解計畫與問題

<!-- Stage: units-generation（Inception 2.7）· Record: 260822-gh-projects-sync
     來源標籤：[ad:*] 指 application-design 的五份產出；[req:*] 指 requirements.md；
     [US:S-n AC m] 指 stories.md；[Qn] 指本站問題檔。
     **本站只產出拓撲，不建議實作順序、不指出關鍵路徑**——那是 2.8 delivery-planning 的經濟決策。 -->

## 上游輸入

- **application-design 五份**（已核可，reviewer iteration 3 判 READY）：`components.md`（7 元件 C-1～C-7、4 支 workflow）、`component-methods.md`（方法簽章、共用型別、7 種 `reason_code`）、`services.md`（4 個執行單元 S-A～S-D、concurrency 配置、服務契約）、`component-dependency.md`（依賴矩陣、資料流、碰撞面、55 條 FR／NFR 雙向對照）、`decisions.md`（ADR-A1～A10、ADR-0006 四面向重跑、CAP-11 可行性補評估、PRE-1-a）。
- **requirements.md**（Revision 1）：40 FR、15 NFR。
- **stories.md**（Revision 1）：11 則故事、65 條 AC、全域 DoD、PRE-1、US-OQ-1～7。

## 本站的邊界（stage 檔明文）

- 產出**拓撲**（誰可以依賴誰），**不產出**實作順序或關鍵路徑。
- **不問**價值優先／風險優先／walking-skeleton-first 這類問題——它們是 2.8 的經濟決策。
- `unit-of-work-dependency.md` 必須含一個**機器可讀的 fenced `yaml` edge block**，well-formed 且無環；下游的批次 fan-out 由它計算，不由散文計算。
- 每個單元標 `kind`：`service`｜`spec`｜`ui`｜`packaging`｜`library`，決定它在 Construction 帶哪些設計 artifact。

## 已由上游定案、不重問

| 事項 | 出處 |
| --- | --- |
| 承載形式：純 Actions，不用 gh-aw；映射落在 composite action | [ad:ADR-A1] |
| 憑證：單一 GitHub App ＋ 分支保護收斂 | [ad:ADR-A2]，[Q2=A] |
| 選取演算法：registry 驅動（無綁定者首建、已綁定者比對漂移） | [ad:services.md] S-A |
| concurrency：事件路徑以分支為界、對帳與反向自成一組 | [ad:services.md]，[req:NFR-P3] |
| 可重用性：設計性質而非交付能力，本次只交付本 repo 安裝 | [ad:ADR-A10]，[F1=A] |
| 元件邊界：7 個元件，C-1／C-2 共用一個 composite action | [ad:components.md] |
| 測試基礎設施：獨立測試 Project ＋ registry 外的 fixture | [ad:ADR-A3]，[Q4=A] |

## 本站的切分判準

依 `project.md ## Corrections`：**工作單元的切分判準是「驗證方式與失敗模式是否同類」，不是元件該怎麼分配**。本設計的驗證方式實際上有六種，彼此不可互相替代：

| 驗證方式 | 失敗長什麼樣 | 涉及的元件／需求 |
| --- | --- | --- |
| ①**純文字 fixture 斷言**（零 I/O、零 API） | 輸出錯的 Status／讀到錯的欄位值 | C-1 `sync-map`、C-2 `record-reader` |
| ②**純文字渲染與雜湊**（零 I/O） | 雜湊誤判導致反向同步全面誤報 | C-6 `managed-block` |
| ③**真實 Projects v2 API 讀寫**（需憑證、網路、測試看板） | API 錯誤碼、item 狀態不符、分頁漏讀 | C-3 `board-client` |
| ④**git 與 repo 行為**（需分支、分支保護、CI 觀察） | push 被拒、既有 CI run 被取消 | C-4 `binding-store` |
| ⑤**Issues REST 行為**（需 issue 搜尋與建立） | 重複開 issue、找不到既有 issue | C-5 `notifier` |
| ⑥**workflow 執行期行為**（需真實事件、佇列、排程） | 事件沒觸發、並行取消、排程撞期 | 4 支 workflow ＋ C-7 編排 |

---

## 問題

### Q1. 單元邊界要用哪一種切法？

A. **依驗證方式切**（上表六類，加上不屬任何一類的收尾項）：每個單元的「完成了嗎」只用一種判準回答。看得到的效果：單元內部的測試策略單一，Construction 的每個單元帶的設計 artifact 種類一致；符合 `project.md` 明文的切分判準。代價：與元件邊界不是一對一（C-1／C-2 合為一個單元、4 支 workflow 依編排對象散進不同單元），追溯要靠對照表而非直覺。

B. **依元件切**（C-1～C-7 各一個，workflow 另計）：與 `components.md` 一對一，追溯最直接。代價：C-1 與 C-2 共用一個 composite action、共用一套 fixture、共用一次部署，拆成兩個單元會讓「這個單元完成了嗎」重複問兩次同一件事；而 C-7 `reconciler` 與對帳 workflow 是同一個東西的兩面，拆開後兩者都無法獨立驗收。

C. **依部署目標切**（4 支 workflow ＋ 1 個 composite action ＋ 既有檔案調整 ＝ 6 個）：每個單元對應一個可獨立部署的檔案群。看得到的效果：部署邊界最清楚。代價：單一 workflow 單元內同時含執行期契約與建置期資產兩種驗證方式（例如自我測試 workflow 既要跑 fixture 斷言、又要對真實看板寫入），正是 `project.md` 判準要避免的形狀。

D. **依需求群組切**（FR-A 綁定／FR-B 映射／FR-C 回讀／…）：與 requirements 一對一。代價：FR 群組是依機制的內部結構分的，不是依可獨立交付的東西分的；FR-J（解析語意）不構成任何可部署的單元。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-27T22:45:21Z（讀自 date -u，即時寫入） -->

### Q2. 單元粒度取哪一檔？

A. **約 8–10 個**：六類驗證方式各成一個單元，加上「既有檔案調整」與「README 指路」兩個收尾項，視 workflow 是否再分而落在 8–10。看得到的效果：每個單元有單一驗證判準且規模相近；與 11 則故事大致同量級，2.8 不必再細切。代價：workflow 類單元之間有共用的實作（都要呼叫同一組元件），單元間的介面契約要寫清楚。

B. **約 4–5 個粗顆粒**（正向／對帳／反向／驗證／收尾）：單元數少、易讀。代價：每個單元內含多種驗證方式（正向單元同時要驗純函式映射、真實 API 寫入、git 回寫），「這個單元完成了嗎」同時指涉三種不可互相替代的判準。

C. **約 14 個以上細顆粒**（每個元件 ＋ 每支 workflow ＋ 每項既有檔案調整各一）：追溯最細。代價：其中數個湊不出可展示成果（例如「受管區塊渲染器」單獨完成時沒有任何讀取端），而 `project.md` 明文說湊不出信心假說的單元沒有部署它的理由。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-27T22:45:21Z（讀自 date -u，即時寫入） -->

### Q3. 部署模型：這些單元是各自獨立部署，還是綁在一起？

本 repo 是 deploy-on-merge（合併進 `ut` 即部署），且 `stories.md` 已定案三處**同批次約束**（S-2↔S-3、S-6↔S-2 的 FR-G3 分支、S-1 不得單獨上線）。

A. **混合：技術上獨立部署，但同批次約束以 DAG 邊標明**：每個單元可獨立合併，但 `unit-of-work-dependency.md` 明確標出哪幾對「不得分批」（承接 `stories.md` 已定案的三處）。看得到的效果：2.8 有最大的排序自由度，同時看得到不可拆的組合。代價：同批次約束在 DAG 上長得像依賴邊，需要額外欄位區分兩者。

B. **全部一次部署**：所有單元合併進同一個 PR。看得到的效果：不會有任何中間態被人看到，三處同批次約束自動滿足。代價：與 `org.md` 的短生命週期分支（1–2 天內解決）直接衝突；且一個含 4 支 workflow ＋ composite action ＋ 既有檔案調整的 PR 幾乎不可能被有效 review。

C. **嚴格依 DAG 拓撲逐一部署**：一個單元一個 PR，順序完全由拓撲決定。看得到的效果：每次變更最小。代價：**會違反已定案的同批次約束**——S-1 單獨上線會讓看板出現永遠停在 `Ready` 的卡片，那對 P3 就是一格謊（`stories.md` G3 已定案）。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-27T22:45:21Z（讀自 date -u，即時寫入） -->

### Q4. 單元的 `kind` 怎麼標？

`kind` 決定該單元在 Construction 帶哪些設計 artifact（例如 spec 不需要 scalability 文件、packaging 不需要商業邏輯模型）。可選 `service`｜`spec`｜`ui`｜`packaging`｜`library`，也可留空（留空者收到完整矩陣）。

A. **workflow 類標 `service`、composite action 標 `library`、既有檔案調整標 `packaging`、README 留空**：判準是「它是什麼」——workflow 是被執行的東西（有執行期行為、有並行與排程特性）；composite action 是被呼叫的可重用碼、無獨立執行期；既有檔案調整（`ci.yml` 的 `paths-ignore`、高成本 workflow 排除）是建置與觸發設定；README 段落五類皆不合，留空收完整矩陣。看得到的效果：每個單元帶的設計 artifact 與它實際的性質相符。代價：`service` 一詞在本 repo 通常指後端服務，用在 workflow 上需要在文件裡說明白。

B. **全部留空，收完整設計矩陣**：不冒標錯的險。代價：composite action 會被要求產出 scalability 與商業邏輯文件，而它是個純函式；`ci.yml` 調整會被要求產出領域模型。多出的都是空文件。

C. **workflow 與 composite action 都標 `service`**：簡化為兩類。代價：composite action 沒有獨立執行期，標 `service` 會讓 Construction 對它要求部署與擴縮設計，那些對它不存在。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-27T22:45:21Z（讀自 date -u，即時寫入） -->

---

## Step 4 — 矛盾與模糊分析（本站判定）

1. **無模糊語言**：四題皆為單一選項字母。
2. **無跨題矛盾**：[Q1=A]（依驗證方式切）與 [Q2=A]（8–10 個）相容——六類驗證方式各一，加兩個收尾項為 8。[Q3=A] 的「同批次約束另標」與 [Q1=A] 不衝突：驗證方式決定**單元邊界**，同批次約束決定**能不能分開部署**，兩者是正交的維度。[Q4=A] 的 kind 標註與 [Q1=A] 一致——依驗證方式切出來的單元，其性質（被執行／被呼叫／建置設定）恰好與 kind 的分類對齊。
3. **一項需在產出中特別處理**：[Q3=A] 要求同批次約束「在 DAG 上與依賴邊區分」。`unit-of-work-dependency.md` 的 fenced yaml edge block 只有 `depends_on` 一個欄位，**放不下第二種關係**。處置：yaml block 只放真正的技術依賴（下游 fan-out 依它計算），同批次約束寫在散文的獨立表格並明標「這不是 DAG 邊」。本站不擴充 yaml schema——那是引擎契約。
4. **本站不產出的東西**（stage 檔明文，逐項自查）：不建議實作順序、不指出關鍵路徑、不問價值／風險優先。`unit-of-work-dependency.md` 的「平行開發機會」段只陳述「哪些單元之間沒有依賴」，不排序。

無需追問。

---

## Step 5 — 分解計畫（待核可）

| # | 單元 | kind | 驗證方式（唯一判準） | 涵蓋 | 複雜度 |
| --- | --- | --- | --- | --- | --- |
| U-1 | 映射與解析 composite action | `library` | ①純文字 fixture 斷言，零 I/O 零 API | C-1、C-2 | M |
| U-2 | 受管區塊渲染與雜湊 | `library` | ②純文字渲染與雜湊，零 I/O | C-6 | S |
| U-3 | 看板客戶端 | `library` | ③真實 Projects v2 API 讀寫（需憑證、測試看板） | C-3 | L |
| U-4 | record 回寫與同步狀態 | `library` | ④git 與 repo 行為（分支保護、CI 觸發觀察） | C-4 | M |
| U-5 | 通報 | `library` | ⑤Issues REST 行為（搜尋、建立、去重） | C-5 | S |
| U-6 | 正向同步 workflow | `service` | ⑥workflow 執行期（事件、並行、佇列） | S-A ＋ 編排 | M |
| U-7 | 對帳 workflow 與編排器 | `service` | ⑥workflow 執行期（排程、報告產出） | S-B ＋ C-7 | L |
| U-8 | 反向同步 workflow | `service` | ⑥workflow 執行期（排程、開 PR、防迴圈） | S-C | M |
| U-9 | 自我測試 workflow | `service` | ⑥workflow 執行期（CI 紅綠、突變驗證） | S-D | M |
| U-10 | 既有檔案調整 | `packaging` | 建置與觸發設定（`ci.yml` `paths-ignore`、高成本 workflow 排除） | [US:S-1 AC 7]、[US:S-6 AC 7] | S |
| U-11 | README 指路段落 | （留空） | 文字比對（`git diff --numstat` 刪除行數為 0） | FR-H1 | XS |

**11 個單元**，略高於 [Q2=A] 的 8–10。差額來自：⑥類驗證方式對應**四支** workflow，而它們的失敗模式彼此不同（事件觸發 vs 排程 vs 開 PR vs CI 紅綠），合併會讓「這個單元完成了嗎」同時指涉四種情境；加上兩個收尾項。**本站判定 11 仍在 [Q2=A] 的意圖內**（每個單元單一驗證判準、規模相近），如實記載超出區間的理由而非硬併。

**同批次約束**（承接 `stories.md` 已定案三處，[Q3=A]）：U-6↔U-1／U-2／U-3／U-4（正向同步的中間態會讓看板說謊）、U-8↔U-6（反向 PR 開啟期間正向必須能暫停覆寫）。**這些不是 DAG 邊**，寫在獨立表格。

[Answer]: Approve Plan  <!-- 2026-08-27T23:01:04Z（讀自 date -u，即時寫入）· Step 5 計畫核可 -->

---

## §13 Learnings（stage 結束儀式）

下列兩項提請採納。第一項是本 intent **第三次**同型失誤，且是在既有教訓已寫入 `project.md` 之後仍再犯——那代表既有那條的**可執行性不足**，需要更具體的判準。

### L1. 要採納哪些學習寫進 `project.md`？（可複選）

A. **跨檔掃查要按「事實」列舉，不是按「改過的字串」grep**。既有的 `application-design:260822-ad-L1` 已要求「改動前先列主張清單、改完逐一 grep 全部產出檔」，本站照做了，仍漏——因為同一個事實在不同表格用**不同的表達形式**：主對照表寫「S-2 AC 4 → U-1 ＋ U-7」，跨單元表寫「S-2 橫跨 U-1、U-6」，覆蓋表寫「U-7 承載 S-2」。grep 我改過的字串查不到後兩者。**可執行的判準**：改動一個事實前，先問「這個事實在本站產出裡有幾種表達形式」，把每一種的**定位方式**（表格名或欄位名，而非字串）列出來，逐一開啟確認。

B. **上游契約缺口的處置形狀：標出、說明影響、指派具體落點與具體修法，不逕自修改已核可的上游**。本站發現 [US:S-2 AC 4] 的 Then 要求對帳報告有「無法判定」清單，而已核可的 `ReconcileReport` 沒有該欄位，兩個 `reason_code` 不能互相頂替。處置是記為 G-1、寫明「該 AC 目前不可滿足」、指派 functional-design 增設 `undecidable: [intent_id]`。**附帶檢查**：指派的目標 stage 若為 `CONDITIONAL`，必須額外註明「該 stage 可能被 skip」的風險，否則指派可能無聲落空。

C. **以上皆不採納**

[Answer]: A, B  <!-- 2026-08-28T15:34:13Z（讀自 date -u，即時寫入）· §13 -->

### L2. 還有什麼要補進來的嗎？

A. **Nothing to add** — 就上面選的那些
B. **Add a note** — 我有一項要自己寫

[Answer]: Nothing to add  <!-- 2026-08-28T15:34:13Z（讀自 date -u，即時寫入）· §13 -->

---

## Revision 1（2026-08-29T03:40:21Z）— delivery-planning 回跳觸發

**觸發**：2.8 Step 4 的排序驗證發現原 U-10 的綁綁與依賴衝突，會逼出 8 單元的巨型 Bolt。使用者於 [dp:F1=A] 裁決回本站以 Modify 模式拆分。引擎已執行 `aidlc-jump.ts execute --target units-generation --direction backward`（`stages_reset: ["units-generation","delivery-planning"]`）。

**Q1～Q4 的原答案與 Step 5 的計畫核可不重取**：拆分不改變切分軸（[Q1=A] 依驗證方式）、粒度區間的意圖（[Q2=A]）、部署模型（[Q3=A]）或 kind 標註原則（[Q4=A]）。**改動的是 rev0 對「U-10 的兩半是否同一個失敗模式」的判斷**——本站自己的判準（驗證方式**與失敗模式**是否同類）在 rev0 被只套用了前半。

**單元數 11 → 12**，仍高於 [Q2=A] 的 8–10，理由與 rev0 相同（第⑥類對應四支 workflow），拆分後多一個。此為 [Q2=A] 已知並接受的形狀，不重新取得核可。
