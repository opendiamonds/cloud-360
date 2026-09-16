# Delivery Planning — 排序問題

<!-- Stage: delivery-planning（Inception 2.8）· Record: 260822-gh-projects-sync
     來源標籤：[ug:*] 指 units-generation 三份產出；[ad:*] 指 application-design；
     [req:*]／[US:*] 指 requirements／stories；[Qn] 指本站問題檔。
     **Bolt 排序是經濟決策，不是拓撲推導**——本站用 2.7 的 DAG 選一條路徑，
     偏離拓撲順序時必須在 risk-and-sequencing-rationale.md 說明理由。 -->

## 上游輸入

- **units-generation 三份**（已核可 **Revision 1**，reviewer iteration 1 判 READY）：**12 個單元**（U-1～U-9、U-10a、U-10b、U-11）、21 條依賴邊的機器可讀 yaml block、**4 組同批次約束**、5 組平行機會、AC 層級的故事對應、兩個已標出的缺口（G-1、U-3 的 403 半邊）。Revision 1 由本站 [F1=A] 觸發，把原 U-10 拆為 U-10a／U-10b。
- **application-design 五份**：7 元件、4 支 workflow、ADR-A1～A10。
- **requirements.md**（40 FR、15 NFR）與 **stories.md**（11 故事、65 AC、全域 DoD、PRE-1）。
- **team-practices**：scope 跳過 `practices-discovery`，由 `memory/` 三層直接提供。

## Step 2 解析的三個 memory 段落（最具體的非空陳述）

| 段落 | 解析結果 | 來源 |
| --- | --- | --- |
| `## Way of Working` | Construction Bolt 分支 base／target 為 **`ut`**，走 **squash-merge**（每個 Bolt 對應 `ut` 上一個 commit） | `team.md`（最具體）＋ `org.md` |
| `## Walking Skeleton` | **`skeleton: off`** —— 第一個 Bolt 是一般 Bolt，不需額外一輪 gate 與儀式 | `team.md` Q3 定案（最具體） |
| `## Deployment` | **deploy-on-merge** 至自有 staging；Construction 與 Operations **連續**而非依序（ADR-0008） | `org.md` ＋ `project.md`（最具體） |

## 已由上游定案、本站不重問

| 事項 | 出處 |
| --- | --- |
| **不做 WSJF／RICE 數值評分** —— 單一決策者、全 Must、依賴序已定時，相對分數沒有真實輸入，屬虛假精確 | `scope-document`（逐字），`project.md ## Corrections` |
| `skeleton: off`，第一個 Bolt 不走 skeleton 儀式 | `team.md` Q3 |
| 團隊配置 —— **`team-formation` 未執行**（ideation 只有 intent-capture／feasibility／scope-definition／approval-handoff 四站），故所有 Bolt 由 `aidlc-developer-agent` 執行 | `ideation/` 目錄實測 |
| 12 個單元的邊界、kind、依賴 DAG、同批次約束 | `unit-of-work*.md`（2.7 Revision 1 已核可） |

## 本站出題前的機械計算

對 [ug:unit-of-work-dependency.md] 的 yaml edge block 跑拓撲分層與同批次傳遞閉包：

**拓撲層（層內可平行）**：
- L0：U-1、U-2、U-3、U-4、U-5、U-11（六個無入邊）
- L1：U-6、U-7、U-8
- L2：U-9、U-10

**同批次約束若當「雙向捆綁」讀，其傳遞閉包**：`{U-1, U-2, U-3, U-4, U-5, U-6, U-8, U-10}`（8 個）、`{U-7}`、`{U-9}`、`{U-11}`——**11 個單元中的 8 個被綁成一批**。

---

## 問題

### Q1. 2.7 的同批次約束要當「雙向捆綁」還是「方向性排序」讀？

這一題決定其餘所有題的可行解空間，必須先答。

[ug:unit-of-work-dependency.md] 的同批次表用的是**捆綁措辭**（「不得分批進入 `ut`」），但三條的**理由**寫的都是**方向性**的情境（「X 單獨上線會…」）。兩種讀法的後果差很多：

| 約束 | 方向性讀法 | 雙向嗎？ |
| --- | --- | --- |
| U-6 ＋ U-1～U-5 | U-6 需要五者已上線 | **否**——已是 DAG 邊，用順序即可滿足 |
| U-8 ＋ U-6 | U-8 需要 U-6 的 FR-G3 暫停覆寫分支已上線 | **否**——順序即可；但這**不是 DAG 邊**，是新的排序約束 |
| U-10 ＋ U-4 | U-4 需要 `ci.yml` 的 `paths-ignore` 已上線 | **是**——U-10 又依賴 U-4 才驗得完，互相需要，真捆綁 |

A. **方向性讀法**：三條都當「X 不得早於 Y 上線」，只有 U-4＋U-10 是真捆綁（互相需要）。看得到的效果：Bolt 可切到 5–7 個，每個都在 `org.md` 的短生命週期分支（1–2 天）範圍內；`ut` 上的歷史對應到有意義的增量。代價：安全性靠**排序紀律**而非結構——若有人調換 Bolt 順序（例如為了先做簡單的），中間態就會出現看板說謊。緩解方式是把順序約束寫進 `bolt-plan.md` 並標為不可覆寫。

B. **雙向捆綁讀法**：照字面，8 個單元同一批。看得到的效果：不可能出現任何有害中間態，安全性由結構保證。代價：一個含 8 個單元（含 4 支 workflow、composite action、既有檔案調整）的 Bolt，**與 `org.md` 的 1–2 天短生命週期分支直接衝突**，且該 PR 幾乎不可能被有效 review——這正是 [req:OQ-6] 當初指派本站要處理的張力。

C. **混合**：U-4＋U-10 捆綁（真互相需要），U-6 與 U-8 的約束改為方向性排序並明標為不可覆寫的排序邊。看得到的效果：安全性上，真正互相需要的被結構保證，其餘由明標的排序約束承擔；Bolt 數落在 5–6。代價：`bolt-plan.md` 要同時表達兩種約束（捆綁 vs 排序），下游讀者需分辨。

X. Other（請說明）

[Answer]: C  <!-- 2026-08-29T00:07:26Z（讀自 date -u，即時寫入） -->

### Q2. 排序啟發式用哪一種？（**不含** WSJF 數值評分，那已被上游排除）

A. **風險優先**：先送能最快證偽最大不確定性的 Bolt。本 intent 的最大不確定性有三個，全部集中在 U-3（看板客戶端）：Projects v2 GraphQL 本 repo 無先例、憑證是否真的帶組織層寫入權（PRE-1）、以及 `createProjectV2Field` 是否可用（決定 S-5 AC 2 走哪一支）。看得到的效果：如果憑證或 API 走不通，會在投入其餘十個單元之前就知道。代價：第一個 Bolt 交付的不是使用者看得到的價值，而是「我們確認這條路走得通」。

B. **價值優先**：先送 P1 開發者最有感的東西——「推送後看板自己更新」（S-1＋S-2，即 U-1～U-6）。看得到的效果：第一個 Bolt 就交付 `intent-statement` 的第一項成功指標（零人工更新）。代價：那一批已經包含全部五個 library 單元與 U-3，等於把最大的不確定性放進第一個 Bolt 卻不是為了證偽它——若 PRE-1 失敗，整批要重做。

C. **混合：PRE-1 先行，之後價值優先**：把 PRE-1（憑證與 API 實測，**不是單元**）當作 Bolt 0 的 exit criteria，之後依價值排序。看得到的效果：最大的不確定性在動工前就被證偽或確認，且不需要為它單獨做一個沒有可展示成果的 Bolt；其後的 Bolt 都交付使用者看得到的東西。代價：Bolt 0 的產出是一份實測結論，`scope-document` 明記 CAP-9「不構成交付批次」——需說明它是**前置關卡**而非 Bolt。

X. Other（請說明）

[Answer]: C  <!-- 2026-08-29T00:07:26Z（讀自 date -u，即時寫入） -->

### Q3. 多個 Bolt 能否平行通過 Construction？

A. **嚴格循序**：一次一個 Bolt 走完 3.1–3.7。看得到的效果：每個 Bolt 的 gate 都在前一個完成後才開，狀態單純；與 `deploy-on-merge` 相容（不會有兩個 Bolt 同時合併進 `ut`）。代價：總時程等於各 Bolt 之和；L0 那六個互無依賴的單元無法同時推進。

B. **層內平行**：同一拓撲層的 Bolt 可平行（L0 六個單元若切成多個 Bolt，可同時跑）。看得到的效果：縮短總時程。代價：`deploy.yml` 的 `concurrency: deploy-10-10` 是 `cancel-in-progress: false`，兩個 Bolt 同時合併會排隊部署；且平行的 Construction 需要多個 worktree，而 `org.md` 的 squash-merge 假設每個 Bolt 對應 `ut` 上一個 commit——平行合併時順序不確定。

C. **循序，但 library 類單元可合批**：不平行跑 Bolt，而是把 L0 的 library 單元合進同一個 Bolt 以減少 Bolt 數。看得到的效果：不引入平行的複雜度，也不會有 11 個 Bolt。代價：與 Q1 的答案交互——若 Q1 選 A（方向性），這裡的合批會讓 Bolt 變大。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T00:07:26Z（讀自 date -u，即時寫入） -->

### Q4. PRE-1（憑證與 API 實測）在計畫裡的身分是什麼？

PRE-1 含四項實測（憑證是否帶組織層 Projects 寫入權、框架單次操作上限的實際值與超限行為、`createProjectV2Field` 是否可用、以及 **PRE-1-a** 的 Rulesets 路徑限制）。它**不是單元**（[Q5=A] 於 user-stories 定案：產出是實測結論，沒有可部署的東西），但 [US-OQ-2] 指派本站決定它在 Construction 的留痕形式。

A. **Bolt 0 的 exit criteria，不是 Bolt**：在 `bolt-plan.md` 設一個「Bolt 0：上線前置關卡」條目，明記它不產出程式碼、其完成判準是四項實測各有一份記錄，且**在 Bolt 1 開工前必須全綠**。看得到的效果：留痕形式具體（四份實測記錄）、有明確的 gate、且不假裝它是可交付的 Bolt。代價：`bolt-plan.md` 出現一個沒有 Unit 的條目，讀者需理解它的性質。

B. **併入 Bolt 1 的 Definition of Done**：不另設條目，把四項實測寫進第一個真正 Bolt 的 DoD。看得到的效果：Bolt 清單全部是真的 Bolt。代價：如果實測結果是「憑證拿不到組織層權限」，Bolt 1 已經投入了實作——而 PRE-1 存在的理由正是要在投入前知道。

C. **獨立於 Bolt 序列之外的前置清單**：寫在 `external-dependency-map.md` 而非 `bolt-plan.md`，因為其中兩項（組織層 App 安裝、Rulesets 設定）需要**組織管理權限**，屬外部相依而非本團隊可自行完成的工作。看得到的效果：正確歸類為外部相依（有 owner、有 lead time、阻擋哪些 Bolt）。代價：`bolt-plan.md` 不提它時，只讀該檔的人不會知道有前置關卡——需在 Bolt 1 的 DoD 交叉引用。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T01:21:36Z（讀自 date -u，即時寫入） -->

### Q5. Construction 的設計階段要逐單元跑，還是逐階段跑？

stage 檔 Step 7 要求本站分類。四個 inline 設計 stage（functional-design、nfr-requirements、nfr-design、infrastructure-design）有兩種迭代方式：

A. **`stage-major`（預設，不需寫入）**：每個設計 stage 對**全部**單元跑一遍，再進下一個 stage。看得到的效果：與先前行為位元組相同；每個 stage 的 gate 在該 stage 做完全部單元後才開，共 4 次人工核可。代價：單一單元的四份設計文件分散在四個時間點產出，該單元的設計連貫性較弱。

B. **`unit-major`（需執行 `set-construction-iteration unit-major`）**：一個單元的四份設計文件連續寫完，再進下一個單元。看得到的效果：每個單元的設計連貫性強——寫 U-3 的 NFR 時，它的 functional design 剛寫完還在手邊。代價：四個 per-stage gate 仍然存在，但會**延後並在設計區塊末端連續觸發**（一次 stage 一次人工核可，四次擠在一起）。

**本站的傾向**：11 個單元中有 5 個是 `library`、4 個是 `service`，性質差異大（純函式 vs 執行期行為），逐單元寫設計時「這個單元需要哪些設計文件」的答案差很多——`kind` 標註本來就是為此而設。但 gate 擠在末端是實質代價。

X. Other（請說明）

[Answer]: B  <!-- 2026-08-29T01:21:36Z（讀自 date -u，即時寫入） -->

---

## 追問（Step 4 的排序驗證觸發）

### F1. U-10 同時被綁綁與依賴拉扯，怎麼解？

**衝突的機械來源**（本站以腳本對 [ug:unit-of-work-dependency.md] 的 yaml block 驗證候選序列時發現）：

- [Q1=C] 定案 **U-4 ＋ U-10 綁綁**（U-4 需 `paths-ignore` 已上線、U-10 需 U-4 才驗得完，互相需要）。
- 但 yaml block 記載 **U-10 的 `depends_on` 是 `[U-4, U-8]`**——它還需要 U-8 產生反向 PR，才驗得了 [US:S-6 AC 7]。
- 而 **U-8 需 U-6 已上線**（[Q1=C] 保留的不可覆寫排序邊）。

傳遞下去：U-10 進 Bolt 1 ⇒ U-8 也要進 ⇒ U-6 也要進 ⇒ U-1～U-5 也要進 = **8 個單元同一批**，正是 [Q1=B] 被否決的形狀。

**根因**：U-10 內含**兩個消費端不同的變更**——`ci.yml` 的 `paths-ignore` 服務 U-4，高成本 workflow 排除服務 U-8。它們的驗證方式同類（建置與觸發設定），但**失敗模式不同**（開發者的 CI 被取消 vs 反向 PR 燒掉 6 小時 runner），consumers 也不同。2.7 依「驗證方式」切時把它們併成一個單元，直到本站代入部署順序才顯出問題。

A. **回 2.7 以 Modify 模式把 U-10 拆為 U-10a／U-10b**：U-10a（`ci.yml` `paths-ignore`）與 U-4 綁綁進 Bolt 1；U-10b（高成本 workflow 排除）與 U-8 同批。看得到的效果：兩個綁綁都成立、無 8 單元巨型 Bolt、每個單元仍只有一種失敗模式——**這其實比原本的切法更符合 2.7 自己的判準**（驗證方式**與失敗模式**是否同類）。代價：要回跳 units-generation 走 Modify（歸檔既有 artifact、更新 yaml edge block 與三份產出、重走該站 gate 與 reviewer），本站隨後重跑排序驗證。

B. **U-10 整個延後到 U-8 那批，接受 U-4 先上線一段時間沒有 `paths-ignore`**：看得到的效果：不動 2.7，Bolt 切得開。代價：從 Bolt 1 上線到 Bolt 3 落地的整段期間，**每次同步回寫都會取消開發者當下正在跑的 CI run**（`ci.yml` 的 `cancel-in-progress: true` ＋ 無分支過濾）。這不是看板說謊，但會實際干擾日常開發，且 [US:S-1 AC 7] 在那段期間是紅的。

C. **接受 8 單元的 Bolt 1**（等同 [Q1=B]）：看得到的效果：所有約束由結構保證，零排序紀律需求。代價：與 `org.md` 的 1–2 天短生命週期分支直接衝突，且該 PR 含 4 支 workflow ＋ composite action ＋ 既有檔案調整，幾乎無法有效 review——[req:OQ-6] 指派本站處理的正是這個張力。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T03:37:35Z（讀自 date -u，即時寫入）· 回 2.7 以 Modify 模式拆 U-10 -->

---

## Revision 1（2026-08-29T04:11:15Z）— 2.7 修訂後重跑 Step 4

[F1=A] 已執行完畢：units-generation 走 Modify、U-10 拆為 U-10a／U-10b、reviewer 判 READY、gate 已核可。本站據修訂後的 yaml edge block 重跑排序驗證。

**Q1～Q5 與 F1 的題幹、選項與答案一律不改寫**——它們是作答當下的紀錄。下列是因 2.7 修訂而變動的**衍生數字**，就地標註而非回改題目：

| 出處 | 作答當下 | 修訂後 | 是否影響該題決定 |
| --- | --- | --- | --- |
| 「本站出題前的機械計算」的拓撲層 | L0 六個、L1 三個、L2 兩個 | L0 六個、**L1 四個**（多 U-10a）、L2 兩個（U-9、U-10b） | 否——Q1 問的是約束讀法，不是層數 |
| 同上的傳遞閉包 | 雙向讀法下 8 個綁成一批 | 雙向讀法下**變成 9 個**：`{U-1…U-5, U-6, U-8, U-10a, U-10b}`（union-find 實算，非估計。U-10a 經 U-4、U-10b 經 U-8 各自併入同一群組，兩個都在裡面而非一進一出） | 否，且**強化**了否決理由——[Q1=B] 的巨型 Bolt 在修訂後只會更大 |
| Q1 的約束表第三列「U-10 ＋ U-4」 | U-10 | **U-10a**（U-10b 另與 U-8 成一組，即第四組同批次約束） | 否——[Q1=C] 的「真捆綁 vs 方向性排序」二分不變 |
| Q5 傾向段的「11 個單元中有 5 個 library、4 個 service」 | 11 | **12**；library 5、service 4、packaging 2、未分類 1（U-11，`unit-of-work.md` 明記五類皆不合） | 否——[Q5=B] 的理由是 kind 性質差異大，該事實未變 |

**重跑的 Step 4 驗證結果**（對修訂後 yaml block 以腳本執行）：12 節點、21 條邊、DFS 無環、無懸空 `depends_on`、`kind` 合法（U-11 依設計留空）。候選序列 Bolt 1「U-1～U-6 ＋ U-10a」／Bolt 2「U-7」／Bolt 3「U-8 ＋ U-10b」／Bolt 4「U-9」／Bolt 5「U-11」**滿足全部 DAG 邊、兩組真捆綁（U-4＋U-10a、U-8＋U-10b）與 [Q1=C] 保留的不可覆寫排序邊（U-6 → U-8）**，且無任何 Bolt 超過 7 個單元。[F1] 描述的 8 單元巨型 Bolt 已消除。

**未因修訂而改變的事**：Bolt 1 仍為 7 個單元。這不是切分不足，而是兩條既有且本輪未動的同批次約束疊加（U-6 需 U-1～U-5 同批、U-10a 需與 U-4 同批），2.7 的 reviewer 已獨立複驗此歸因。
