# Delivery Planning — 問題檔

<!-- Stage: delivery-planning（Inception 2.9）· Record: 260920-orchestration-brain
     lead: aidlc-delivery-agent · support: aidlc-architect-agent -->

## 這一站在決定什麼

`units-generation`（2.7）產出了依賴圖——**什麼可以依賴什麼**，那是幾何，機械地算得出來。
本站決定的是**走哪一條路**：哪一批先做、哪一批證明什麼、哪一批把最大的不確定性提早攤開。
這是經濟判斷，算不出來，所以要問。

本站的產物是 **Bolt 序列**。一個 Bolt 就是**一次建置通過，做完一個或多個工作單元，結束時
有東西能跑、能展示**——它帶一份「怎樣算做完」、一個「做完會證明什麼」的假說、以及誰負責。
Bolt 不是 sprint，也不是一個功能；它是下一個階段的工作單位。

---

## 上游已定案、本站不重問

| 事項 | 已定案於 | 不重問的依據 |
|---|---|---|
| **不走 walking skeleton**（不先做一個「打通全部架構層的最小端到端切片」再加功能） | `team.md` `## Walking Skeleton` Q3 定案 `skeleton: off`；`scope-document.md:164` 覆述 | 逐字「本專案自 baseline 起已有可運行的 backend／frontend、CI、自動部署……管線成熟度已超過需要走 skeleton 驗證的階段」。`project.md` 的 `delivery-planning:c20` 亦明文「不重問 practices-discovery 已核可的 walking-skeleton 立場」 |
| Bolt 分支走 **squash-merge**，base 與 target 皆為 `ut` | `team.md` `## Way of Working` PR 合併方式 Q2 定案 | 逐字「Construction Bolt 分支：走 squash-merge，每個 Bolt 對應 `ut` 上一個 commit」 |
| 合併進 `ut` 即部署到自有 staging | `org.md` `## Deployment`、ADR-0007 | deploy-on-merge |
| **所有 Bolt 由 AI 執行**（無人類 mob 分工） | `team-formation`（1.5）**未執行**——本輪查證 `ideation/` 下只有 intent-capture／feasibility／scope-definition／rough-mockups／approval-handoff | stage 檔逐字：「When 1.5 is SKIP，states that all Bolts are executed by aidlc-developer-agent (AI)」 |
| 破壞性契約變更與其消費端**不得分批** | `project.md` `delivery-planning:c6` | deploy-on-merge 之下每個 Bolt 邊界都是一次真實部署，故這條「同批次」約束**比 DAG 邊更強**。本 intent 的落點：`U2 brain-ws-contract` 與其兩個消費端 `U13`／`U14` |
| 合併判準是「分開後每個都湊得出有意義的信心假說嗎」，不是單元數平均 | `project.md` `delivery-planning:c3` | 逐字 |
| 排序理由要寫「這個位置由什麼決定」，不是「因為它是 Must／Should」 | `project.md` `scope-definition` 的 2026-09-22 教訓 | 逐字 |

---

## 出題前的查證（**非來源**，供題幹與選項引用）

以下數字皆由腳本從已核可的上游產出實算，非目測。

### V-1　17 個單元中，**只有 4 個**在自身與整條上游都沒有未決事項

把 `contract-design` 的 15 條 Open Questions 與 `domain-design` 的三處缺口（`DG-1`／
`DG-2`／`DG-3`）對應回單元，再算遞移閉包：

| 可立即動工（4） | 自身乾淨但繼承上游未決（3） | 自身帶未決（10） |
|---|---|---|
| `U1` brain-infra<br>`U2` brain-ws-contract<br>`U3` rbac-story-ids<br>`U6` embedding-port | `U14` entry-page-ui（繼承 8 個）<br>`U16` object-picker-ui（繼承 8 個）<br>`U17` a11y-gate（繼承 9 個） | `U4`、`U5`、`U7`、`U8`、`U9`、`U10`、`U11`、`U12`、`U13`、`U15` |

### V-2　未決事項依影響單元數排序

| 未決事項 | 影響 | 單元 | 落點 |
|---|---|---|---|
| **`OQ-N3`** | **4** | `U5`、`U8`、`U9`、`U15` | `functional-design`（3.1，CONDITIONAL；skip 轉 `code-generation`，ALWAYS）＋ 若需新邊則 `delivery-planning` |
| `DG-1` | 3 | `U5`、`U8`、`U9` | 同上 |
| `DG-2` | 2 | `U4`、`U7` | 同上 |
| `OQ-N2` | 2 | `U7`、`U8` | 同上 |
| `OQ-N1` | 2 | `U11`、`U12` | 同上 ＋ `delivery-planning` |
| `OQ-4`／`OQ-10` | 1（同一個單元） | `U11` | `nfr-requirements`（3.2，CONDITIONAL，**無自然承接站**） |
| `OQ-13` | 1（**單元層級阻塞**） | `U9` | `infrastructure-design`（3.4，CONDITIONAL；轉 `deployment-pipeline`，**亦 CONDITIONAL**） |
| `OQ-3`／`DG-3`／`OQ-1`／`OQ-N4`／`H-3`／`OQ-5`／`OQ-8` | 各 1 | `U5`／`U7`／`U10`／`U10`／`U12`／`U13`／`U13` | 多數為 `functional-design` |

**`OQ-N3` 的性質與其他不同**：它不是「細節待定」，而是**記憶功能沒有寫入端**——沒有它，
`U5`／`U8`／`U9`／`U15` 四個單元做出來也是惰性的（檢索永遠回空、記憶頁永遠空白、
清除沒有東西可清），`FR4.1`／`FR4.5`／`FR4.6`／`FR4.7` 四條需求失去機制。

### V-3　DAG 的層與並行根

四個可平行根為 `U1`／`U2`／`U3`／`U4`（`depends_on: []`），共 7 層，25 條邊，
56 對單元完全互相獨立。**注意四個根裡有一個（`U4`）帶未決事項 `DG-2`。**

### V-4　Inception → Construction 的追溯完整性

三份 `traceability.json` 皆無 `GAP`、無 `ORPHAN`、無 invalid target：
`user-stories` 70 列（61 `OK`／8 `Deferred`／1 `N/A`）、`domain-design` 20 列全 `OK`、
`units-generation` 20 列全 `OK`。8 筆 `Deferred` 全部指向 `build-and-test`（3.6，ALWAYS）
或 CONDITIONAL 站並已附轉移目標；1 筆 `N/A`（`NFR9`）是已核可的範圍決定而非缺口。

### V-5　外部或跨團隊的可能阻擋項（本站盤點，待你確認與補充）

| 項目 | 現況 | 阻擋哪些單元 |
|---|---|---|
| `OPENROUTER_API_KEY` | staging 已有（既有 A1／A3／C1 在用）；但 `build-and-test` 跑的 `ci.yml` backend job **沒有金鑰** | `U11` 的準確率量測（`NFR1`）、`NFR3` 的首字計時 |
| Ollama 跑在自有 staging 主機 | 模型約 1.2GB、RAM 需求約 2GB，**domain-design 明記未在該主機實測**，且 `DEPLOY.md`／`LOCAL-DEV.md` 未記載主機餘裕 | `U1`、`U6` |
| GitHub Actions → 自有 staging 資料庫的連線 | **未定**（`OQ-13`）。workflow 跑在 GitHub，資料庫在自架主機後面 | `U9`（單元層級阻塞） |
| DB image 由 `postgres:16-alpine` 換為 `pgvector/pgvector:pg16` | 兩個 compose 檔都要改 | `U5` |
| Redis 作為第 5 個服務 | 新增服務 ＋ 新增環境變數，須同批更新 `render-env.sh`／`.env.example`／`LOCAL-DEV.md` | `U1`、`U10` |

---

## 問題

### D1. 那 13 個帶著（或繼承）未決事項的單元怎麼排？

這是本站最重要的一題。V-1 顯示只有 `U1`／`U2`／`U3`／`U6` 四個單元能在零未決事項下動工；
其餘 13 個都在等某個問題定案，而多數問題的落點是 `functional-design`（3.1，**CONDITIONAL**，
可能被 skip，skip 則轉 `code-generation`——即由寫 code 的人當場決定）。

- A. **先做那 4 個乾淨的，其餘照 DAG 順序推進，每個 Bolt 把自己的未決事項列為「開工前必須先答」的進入條件**。
  好處：立刻有東西可動工，且不需要先開一輪額外的設計會。
  代價：`functional-design` 是 per-unit 的 CONDITIONAL 站，若被 skip，這些問題會在
  `code-generation` 當場被實作者決定——而其中 `OQ-N3` 與 `OQ-N4` 是**跨單元的語意選擇**，
  由單一單元的實作者決定很可能得出不自洽的結果。
- B. **先插一個「把未決事項打掉」的前置 Bolt**（不產生使用者可見功能，只定案 `OQ-N3`／
  `OQ-N4`／`DG-1`／`DG-2`／`OQ-N1` 這幾個跨單元的），之後所有 Bolt 都在已定案的地基上跑。
  好處：跨單元的語意選擇集中做一次、彼此自洽；後面每個 Bolt 的進入條件都乾淨。
  代價：第一個 Bolt **沒有可展示的成果**，而 `project.md` 的 `delivery-planning:c3` 逐字說
  「湊不出信心假說的 Bolt 沒有可展示的成果，也就沒有部署它的理由」——選這個等於為此開一次例外。
- C. **只把「影響最多單元」的那幾項前置，其餘留在各自的 Bolt**。
  具體是 `OQ-N3`（4 個單元）、`DG-1`（3 個）、`DG-2`／`OQ-N2`／`OQ-N1`（各 2 個）這五項
  併進**第一個有產出的 Bolt** 一起決定（該 Bolt 同時交付 `U1`／`U2`／`U3`／`U6`），
  其餘 10 項單一單元的留在各自 Bolt。
  好處：不需要一個空的 Bolt，跨單元的語意仍集中決定。
  代價：第一個 Bolt 的範圍變大，它的「做完」判準要同時涵蓋交付與定案兩件事。
- D. **先把整份未決清單送回上游站重跑**（`domain-design` 修 `DG-*` 與 `OQ-N3`／`OQ-N4`
  牽涉的元件責任與實體形狀），再回來做 Bolt 計畫。
  代價最高但從根解決：那些問題的根確實在 `components.md` 的責任句與互動宣告之間。
- X. Other（請說明）

[Answer]: C
<!-- 作答時間 2026-09-26T10:34:44Z（`date -u`）。選 C：把影響最多單元的五項——`OQ-N3`（4 個）、
     `DG-1`（3 個）、`DG-2`／`OQ-N2`／`OQ-N1`（各 2 個）——併進第一個**有產出**的
     Bolt 一起定案，該 Bolt 同時交付 `U1`／`U2`／`U3`／`U6`；其餘 10 項單一單元的
     未決事項留在各自的 Bolt。

     後果（寫入 bolt-plan.md 與 risk-and-sequencing-rationale.md）：
     - 第一個 Bolt 的「做完」判準**同時涵蓋交付與定案兩件事**，須分開列清楚，
       不得讓「交付完成」被誤讀為「五項未決事項也已定案」。
     - 選 C 而非 B 的理由：B 的前置 Bolt 沒有可展示成果，而 `delivery-planning:c3`
       逐字說那樣的 Bolt「沒有部署它的理由」；C 把定案掛在一個有產出的 Bolt 上，
       不需要為此開例外。
     - 選 C 而非 A 的理由：`OQ-N3`／`OQ-N4` 是**跨單元的語意選擇**，A 會讓它們在
       per-unit 的 `functional-design`（CONDITIONAL，skip 轉 `code-generation`）
       被單一單元的實作者各自決定，很可能不自洽。 -->

---

### D2. 用什麼順序原則排 Bolt？

`skeleton: off` 已定案，所以「先做一個打通全架構的最小切片」這個選項不在檯面上。

- A. **風險優先**：把不確定性最大的先做，讓後面的決定建立在已校準的基礎上。
  以本 intent 而言，最大的不確定性是**路由層能不能產出可比較的信心值**（`OQ-10`，
  它若不成立，`U11` 的責任敘述與其 property-based 測試都要改寫）與**記憶的寫入端**（`OQ-N3`）。
- B. **價值優先**：照使用者看得到的價值排，低風險時這樣最快見效。
  本 intent 的最高價值是入口頁能對話並交辦（`U14`＋`U13`＋`U11`＋`U12`），
  但那條鏈在 DAG 上最深（L3–L5）且繼承最多未決事項。
- C. **正式評分（WSJF 形狀）**：把價值、時間急迫性、風險削減三項加總後除以工作量，分數高的先做。
  代價：本 intent 的「價值」與「急迫性」沒有實證輸入（無使用者數據、無時程壓力），
  而 `project.md` 的 `scope-definition:c5` 逐字說過「沒有真實輸入的相對分數是虛假精確」。
- D. **混合：風險優先打頭，之後轉價值優先**。前段先把影響最多單元的未決事項與最不確定的
  技術面（路由層信心值、記憶寫入端）打掉，後段照使用者可見價值推進。
- X. Other（請說明）

[Answer]: D
<!-- 作答時間 2026-09-26T10:34:44Z（`date -u`）。選 D：混合——前段風險優先，後段轉價值優先。

     與 D1=C 的搭配：第一個 Bolt 既交付四個乾淨單元，又打掉五項高影響未決事項，
     正是「風險打頭且有產出」。之後的前段續打最不確定的技術面（路由層的信心值
     `OQ-10`／`OQ-4`、記憶寫入端落地），後段照使用者可見價值推進（入口頁對話與交辦）。

     不採 C（WSJF）的理由已寫在選項內並經採納：本 intent 的「價值」與「急迫性」
     沒有實證輸入，而 `project.md` 的 `scope-definition:c5` 逐字說「沒有真實輸入的
     相對分數是虛假精確」。**故 `risk-and-sequencing-rationale.md` 不做數值評分**，
     以風險與依賴的逐條論證表達排序，並依 `scope-definition` 的 2026-09-22 教訓，
     每一列排序理由都寫「這個位置由什麼決定」而非「因為它是 Must」。 -->

---

### D3. 一個 Bolt 多大？

- A. **一個 Bolt = 一個工作單元**。17 個單元 → 17 個 Bolt。
  好處：每個 Bolt 的「做完」判準最單純。
  代價：Bolt 數量多，且有些單元**單獨湊不出可展示的信心假說**——例如 `U2`
  （只產出一份型別來源與兩道 CI 檢查）、`U3`（只插 22 列權限種子），
  而 `delivery-planning:c3` 說湊不出假說的 Bolt 沒有部署它的理由。
- B. **一個 Bolt = 幾個相關單元綁在一起，以「能湊出一個有意義的信心假說」為判準**。
  例如把 `U2`＋`U13`＋`U14` 綁在一起（契約＋閘道＋入口頁），因為
  `delivery-planning:c6` 的「同批次」約束本來就要求破壞性契約變更與其消費端不得分批。
- C. **薄切片，橫跨多個單元**：每個 Bolt 取幾個單元各一部分，湊成一條端到端可展示的路徑。
  代價：與 `units-generation` 的單元邊界交叉，而那些邊界是照「驗證方式與失敗模式是否同類」
  切的——橫切會讓一個 Bolt 的「做完了嗎」同時指涉多種判準。
- X. Other（請說明）

[Answer]: B
<!-- 作答時間 2026-09-26T10:34:44Z（`date -u`）。選 B：以「分開後每個都湊得出有意義的信心假說嗎」
     為判準綁幾個單元（`delivery-planning:c3` 的逐字判準）。

     已知的硬性綁定（非本站選擇，是上游約束）：`delivery-planning:c6` 的「同批次」
     約束要求**破壞性契約變更與其消費端不得分批**，本 intent 的落點是
     `U2 brain-ws-contract` 與其兩個消費端 `U13`／`U14`——三者必須在同一個 Bolt。

     已知單獨湊不出假說的單元（故不單獨成 Bolt）：`U2`（只產出型別來源與兩道 CI 檢查）、
     `U3`（只插 22 列權限種子）。 -->

---

### D4. Bolt 可以同時做幾個？

DAG 允許平行（56 對單元完全互相獨立、4 個可平行根），但允許不等於該這樣做。

- A. **一次一個，做完再做下一個**。deploy-on-merge 之下每個 Bolt 邊界都是一次真實部署，
  序列執行讓每次部署的變因單一、出事時好回溯。
- B. **允許平行，但同一層內才平行**（例如 `U1`／`U2`／`U3` 三個根同時做）。
  好處：前段的乾淨單元可以一起推進。
  代價：三個 Bolt 同時改 compose／CI／schema 時容易互相踩到，而它們都會觸發部署。
- C. **允許平行且不限層**，由依賴圖自行決定何時可並行。
  代價：最難預測同時間有幾次部署在跑，而 `deploy.yml` 的 `concurrency: deploy-10-10`
  且 `cancel-in-progress: false`——部署會排隊而不是取消，多個 Bolt 同時完成時會塞住。
- X. Other（請說明）

[Answer]: A
<!-- 作答時間 2026-09-26T10:42:26Z（`date -u`）。選 A：一次一個 Bolt，做完再做下一個。

     與 D1=C 的交互（本站補記，非新決定）：第一個 Bolt 要同時定案五項**跨單元**的
     未決事項，而那些決定會改變後續多個 Bolt 的地基（例如 `OQ-N3` 的寫入端一旦定在
     某個單元，該單元的責任與可能的新依賴邊就跟著定）。序列執行使後面的 Bolt 不會
     建立在尚未定案的地基上。
     另：`deploy.yml` 的 `concurrency: deploy-10-10` 且 `cancel-in-progress: false`
     ——部署會排隊而非取消，序列執行下這個設定不會成為瓶頸。 -->

---

### D5. V-5 的五項外部阻擋項，確認與補充

V-5 是本站盤點的結果（見上表）。請確認它們，並告訴我漏了什麼。

- A. **五項都對，沒有漏的**。我依表格內容寫進 `external-dependency-map.md`，
  每項標明擋哪些單元、以及它若沒到位時該 Bolt 怎麼辦。
- B. **五項都對，但還有別的**（請說明是什麼、誰擁有它、大概多久）。
- C. **其中某項判斷錯了**（請說明哪一項、實際情況為何）。
  例如你可能知道 staging 主機的實際 RAM 餘裕，或知道 GitHub Actions 連得到／連不到那台資料庫。
- X. Other（請說明）

[Answer]: A
<!-- 作答時間 2026-09-26T10:42:26Z（`date -u`）。選 A：五項外部阻擋項都對、沒有漏的。
     依此寫入 `external-dependency-map.md`，每項標明：擋哪些單元、誰擁有它、
     以及它若沒到位時該 Bolt 怎麼辦。

     **注意其中兩項仍是開放的、不是已解決**：
     - Ollama 在 staging 主機的 RAM 餘裕**未實測**（domain-design 明記），
       故 `U1`／`U6` 的 Bolt 必須把「實測主機餘裕」列為開工前的第一件事。
     - GitHub Actions 連不連得到自架 DB 仍是 `OQ-13`，且它是 `U9` 的**單元層級阻塞**
       ——未定案前 `U9` 無法完成，其落點 `infrastructure-design` 與轉移目標
       `deployment-pipeline` **皆為 CONDITIONAL**，兩者皆 skip 時須重新提交使用者。 -->

---

### D6. 這次建置你最擔心什麼？（可複選）

用來決定哪些風險要在前段的 Bolt 就攤開。

- A. **記憶功能做出來是空的**——`OQ-N3` 沒有寫入端，四個單元變惰性而 CI 全綠。
- B. **路由層判不準或給不出信心值**——`OQ-10` 若不成立，反問路徑會靜默永不觸發，
  文件上看起來卻是已解決。
- C. **新的 WebSocket 面**——三項硬約束（掛 `/api/` 之下、token 不進 query string、
  握手 `record=True`）任一項照抄既有前例就會出錯，而既有前例正好三項都反著做。
- D. **部署設定的無聲降級**——新增 Redis／Ollama 的環境變數若沒同批寫進 `render-env.sh`，
  服務照常啟動但功能靜默失效（既有實例：n8n 的憑證從未被寫入，架構圖 icons 一直是灰底佔位圖）。
- X. Other（請說明）

[Answer]: A, B, C
<!-- 作答時間 2026-09-26T10:42:26Z（`date -u`）。三項全選：
     A 記憶做出來是空的（`OQ-N3`，本 intent 唯一的 Critical）
     B 路由層給不出信心值（`OQ-10`＋`OQ-4`，落點無自然承接站）
     C 新的 WebSocket 面（三項硬約束，既有前例三項都反著做）
     未選 D（部署設定的無聲降級）。

     對 Bolt 排序的直接後果（寫入 `risk-and-sequencing-rationale.md`）：
     - A 已由 D1=C 處理——`OQ-N3` 在第一個 Bolt 就定案。
     - B 必須在 `U11` 的 Bolt **之前**有答案，而其落點 `nfr-requirements` 是
       CONDITIONAL 且無自然承接站；故該 Bolt 的進入條件要明寫「若該站被 skip，
       須重新提交使用者裁決，不得由實作者當場決定」。
     - C 的三項硬約束全部落在 `U13`，故 `U13` 所在的 Bolt 要把「以 token 置於
       query string 的握手須被**拒絕**」寫成可執行的驗收，而不是「我們不那樣寫」。
     - D 未選，但它仍是 `U1` 的既有硬約束（`project.md ## Mandated` 的同批更新規則），
       不因未被選為「最擔心」而放寬。 -->

---

### D7. `U2` 的批次歸屬（`units-generation` 明確留給本站的決定）

`contract-summary.md` 與 `unit-of-work-dependency.md` 都標出 `delivery-planning:c6` 的
「同批次」約束落在 `U2 brain-ws-contract` 與其兩個消費端 `U13`／`U14`，並逐字寫
「**這是 2.9 必須代入的約束，本站只標出它的存在，不做批次決定**」。本站的排序把 `U2`
放在 B1、`U13`／`U14` 放在 B6，即**不同批**，故必須就地說明。

- A. **可以，`U2` 留在 B1。**
- B. **`U2` 移到 B6 與消費端同批。**
- C. 先看規則原文與由來再決定。
- X. Other（請說明）

[Answer]: A
<!-- 作答時間 2026-09-26T10:52:34Z（`date -u`）。選 A：`U2` 留在 B1。

     本站提出的理由（經使用者採納）：`delivery-planning:c6` 的逐字觸發條件是
     「**凡涉及既有端點回應形狀變更的 Bolt 切分**」，而 `U2` 是一份**全新**的
     WebSocket 訊息型別來源——沒有任何既存消費端會因它上線而壞掉。它單獨部署的內容
     是一個 committed 的 JSON 檔與兩道新 CI 檢查；該約束要防的「舊前端碰新後端」
     在這裡不存在。反方向（`U13`／`U14` 在沒有 `U2` 的情況下上線）被 DAG 邊擋住，
     不可能發生。

     **附帶好處**：那兩道 CI 閘門提早五個 Bolt 上線，使 B2–B5 期間任何動到 WS 訊息
     型別的改動都受漂移保護；若照 B 把 `U2` 押後，中間五個 Bolt 就沒有這層保護。

     `U13` 與 `U14` 仍同批（B6），但理由是 **D3=B 的信心假說判準**（閘道與其唯一
     消費端分開後，前者湊不出可展示的成果），不是 `c6` 的破壞性變更理由。
     兩者在本計畫中被明確區分，見 `risk-and-sequencing-rationale.md`。 -->

---

## Consolidated Summary Confirmation

<!-- 待所有問題作答後填入 -->

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- 作答時間 2026-09-26T10:57:43Z（以 `date -u` 取值）。確認範圍：D1–D7 共 7 題的定案，以及三項已揭露的後果（U15 的排序約束來自信心假說而非 DAG、B5 的進入條件是無自然承接站的 OQ-10／OQ-4、B9 為條件式且其落點與轉移目標皆為 CONDITIONAL）。 -->
