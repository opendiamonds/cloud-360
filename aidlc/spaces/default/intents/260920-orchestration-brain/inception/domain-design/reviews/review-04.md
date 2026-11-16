## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 2

### Findings

| ID | Severity | Location | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| R-01 | Major | `components.md` — `### Part A'' — 既有元件的邊補充`（第 711–750 行） | 作者新增一個獨立的 `component_edge_supplement:` YAML 區塊取代原本的散文表，並訂出合併規則（同名元件的 `depends_on`／`dependents` 取聯集，其餘欄位以 Part A 為準）。我獨立以 Python 解析全部三個 YAML 區塊（Part A、Part A'、Part A''）並套用該合併規則：節點數 10、`depends_on` 邊 17、`dependents` 邊 17，**兩集合完全相等**（`depends_on - dependents` 與 `dependents - depends_on` 皆為空集合），DFS 三色法確認**無環**——與作者宣稱的「17 條邊、10 個節點、完全相等、無環」逐數字一致。回答 dispatch 的核心問題：第二個頂層鍵（`component_edge_supplement`）**確實把機讀契約從「需要人工合併 YAML 與 Markdown 散文」降格為「需要合併兩個 YAML 區塊」**——不再有任何邊只存在於散文裡，任何依合併規則實作的讀者都能機械重建出與我獨立算出的同一張圖，這正是 `review-02` 建議的修法（補一個只含新增邊的附加 YAML 區塊）被逐字採納的結果。但誠實地說，這**沒有把問題完全消除，只是把它移到一個較小、較可控的位置**：若下游工具或未來 sensor 只知道解析 `components:` 這個鍵、不知道還要讀 `component_edge_supplement` 並套用聯集規則，它仍會得到不對稱的圖（我獨立驗證：只解析兩個 `components:` 區塊會得到 `depends_on` 13 條、`dependents` 15 條，與 `review-02` 原始發現逐字一致）。這個殘留風險是「不回改已核可的 Part A」這條既有規則（`refined-mockups:c3`）下的必然代價，而不是作者沒做到位——沒有更好的解法能同時滿足「不回改 Part A」與「單一頂層鍵」兩個約束。 | 目前的解法已是在既定約束下的最佳折衷，不需要再改；若本 intent 未來有第二次修訂，建議把合併規則本身也寫成一小段可執行的腳本樣板（本審查用的十餘行 Python 已可直接複用），放進檔案或 `codekb`，讓下游工具不必重新發明同一套聯集邏輯。 | Resolved |
| R-02 | Major | `components.md` 第 890 行「修訂 1 的七項自檢逐項結果」第 6 項 | 自檢現在聲稱「`depends_on` 與 `dependents` 各 **17** 條邊、兩集合完全相等……以腳本解析本檔全部三個 `yaml` 區塊的聯集實算」。我獨立重算（見 R-01）得到完全一致的數字：17／17／相等／無環。且自檢文字誠實保留了更正軌跡（「原文寫『對 14 條邊實算』……那代表這一項我是手寫了一組邊清單」），更正說明與實際修正動作一致，沒有 `functional-design:c17` 那種「自述與實際改動不符」的落差。元件（6→10）、實體（7→10）、ADR（9→16）、追溯表（20→31，0 GAP）四項數字我也逐一獨立核對（分別以 YAML 區塊解析、`entities:` 子區塊解析、`grep -c "^## ADR"`、直讀 `traceability.json`），全部與宣稱一致。 | 無；此項已完全修復且可重複驗證。 | Resolved |
| R-03 | Major | `decisions.md` ADR-010（第 452–456 行補入段）、ADR-011（第 507–511 行補入段）、`components.md` 第 897 行 `DG-9` | `ADR-010` 與 `ADR-011` 現在都明確點名三張新表（`project_members`、`reselection_events`、`system_requirement_fields`）觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 **blocking** 同步，且逐字引用 `project.md ## Mandated` 的必做 1／必做 2；`ADR-011` 的補入段額外把 `ADR-015` 的清空語意（`value` 可為 null ＋ 獨立 `clearedAt`）明訂為 `system_requirement_fields` 的 DDL 要求，理由完整（否則「從未填過」與「清空」在資料層不可區分）。`components.md` 第 897 行的 `DG-9` 交接項完整重述這三張表與兩項 blocking 義務，轄給 `code-generation`（對照 `.claude/tools/data/stage-graph.json` 確認 `execution: ALWAYS`，且位於 `aidlc-state.md` 的 `Current Stage: domain-design` 之後），不是落空指派。三處交叉引用（`decisions.md` 兩處 ADR 补入段 ↔ `components.md` 的 `DG-9`）彼此一致。 | 無；此項已完全修復。 | Resolved |
| R-04 | Minor | `domain-design-questions.md` 第 348–353 行（編號更正說明）、第 407–521 行（`E11`–`E15` 標題） | 修訂 1 的五個新問題已從 `E6`–`E10` 改為 `E11`–`E15`。逐一核對：(a) `components.md`／`decisions.md` 全文**零筆**裸 `[E6]`–`[E10]` 殘留；(b) 全部裸 `[E11]`–`[E15]` 引用（`components.md` 四處、`decisions.md` 八處）都指向本輪新問題（成員管理邊界、`ADR-009` 衝突、per-project 授權、`McpBridge`、`ProgressChannel`）；(c) 全部 `[DD:E6]`–`[DD:E9]` 引用（`components.md` 兩處、`decisions.md` 兩處）都仍指向原輪問題（Redis session、pgvector、`DiagramChangeRecord`、embedding 切換），無一誤指向新輪內容；(d) `domain-design-questions.md` 的五個新標題確認為 `## E11.`–`## E15.`，原輪 `## E6.`–`## E9.` 標題與內容原樣保留、未被誤改。這條修法本身完全消除了編號碰撞，追溯不會再指向錯誤的問題。 | 無；碰撞已消除。見 R-05 關於「來源標籤慣例」表本身未同步更新的獨立記載。 | Resolved |
| R-05 | Minor | `domain-design-questions.md` 第 7–18 行 `## 來源標籤慣例` 表 vs `memory.md` 第 25 行 | `memory.md` 的日記寫下「已改為 `E11`–`E15` **並在慣例表補記兩套編號空間的事**」，但我逐行核對 `## 來源標籤慣例` 表（第 9–18 行，8 列），表內**仍只有原本那一行** `[DD:E<n>]` ──**本站新增**……用 `E` 避開既有 D／DM 撞號」，沒有任何新增或修改的行說明「`[DD:E<n>]`（原輪）與裸 `[E<n>]`（修訂輪）是兩套不同編號空間」。實際完成的只是第 348–353 行一段**獨立的歷史更正說明**（放在修訂 1 區段開頭，而非表格本身），內容足以讓人事後推敲出兩套空間的存在，但它不是「慣例表」，且不是前瞻性的使用規則（例如若有修訂 2，讀者仍須自己往回數到 `E15` 才知道下一個可用號碼是 `E16`）。這是 `project.md` 的 `functional-design:c17`（「存檔註記的自述必須與實際改動一致」）點名過的同一種落差——發生在這次審查要我驗證的同一個細項上。不影響本輪的正確性（碰撞已消除，追溯不會指錯），純屬文件完整性缺口。 | 在 `## 來源標籤慣例` 表補一行（或在 `[DD:E<n>]` 那一行的說明文字內加註），明確寫出「原輪用到 `E9`，修訂輪自 `E11` 起另編、不帶 `DD:` 前綴」，使該表本身（不只是歷史敘述段）成為下一次修訂時唯一要查的地方；同時訂正 `memory.md` 第 25 行的自述，使其與實際改動一致。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `bun .claude/tools/aidlc.ts engine sensor-required-sections`（`components.md`） | `pass: true, h2_count: 14, findings_count: 0` | 新增的 `### Part A''` 是 H3，不影響 H2 計數；本檔只套用通用 ≥2-H2 門檻（domain-design 的 `components.md` 未被任何模板或 `## Sensors` 覆寫鎖定特定標題集），故新的頂層 YAML 鍵不會被此 sensor 拒絕——目前框架對這份檔案的機讀契約沒有結構化驗證，「單一真實來源」是作者自我課的約束，不是 sensor 強制的約束 |
| `bun .claude/tools/aidlc.ts engine sensor-traceability`（`traceability.json`） | `pass: true, gaps: [], orphans: [], findings_count: 0` | 31/31 覆蓋、0 GAP、0 孤兒，與作者宣稱一致；本輪的編號更正與邊補充未產生任何追溯斷裂 |
| 獨立 Python 腳本：解析 Part A ＋ Part A' ＋ Part A'' 並套用聲明的合併規則 | 節點 10、`depends_on` 17、`dependents` 17、兩集合相等、DFS 確認無環 | 與作者 R-02 更正後的自檢數字逐項一致；證實 R-01／R-02 的修復可由任何依合併規則實作的讀者獨立重現 |
| 同一腳本，只解析兩個 `components:` 區塊（不含 `component_edge_supplement`） | `depends_on` 13、`dependents` 15、不相等 | 證實若下游工具不知道合併規則，仍會得到 `review-02` 原始發現的那個不對稱圖——這是 R-01 分析中點名的殘留風險，不是新發現 |
| `grep` 核對 `[E6]`–`[E10]`（裸）、`[DD:E6]`–`[DD:E9]`、`[E11]`–`[E15]` 在 `components.md`／`decisions.md`／`domain-design-questions.md` 的全部出現位置 | 零筆錯誤指向 | 支撐 R-04 Resolved 的判定 |
| `grep` 核對「14 條邊」「13 vs 15」等舊數字在全檔的殘留 | 僅出現在更正說明本身（歷史敘述），無任何處把舊數字當成現行結論引用 | 無跨檔傳播殘留 |

### Summary

**獨立重算結果**：節點 10、`depends_on` 邊 17、`dependents` 邊 17，兩集合完全相等、DFS 三色法確認無環——與作者本輪自檢宣稱的每一個數字逐項一致。四項上一輪發現逐一核對：**R-01、R-02、R-03、R-04 全部 Resolved**。R-01 的判斷留有一個誠實的保留：新增的 `component_edge_supplement` 頂層鍵把「需要人工合併 YAML 與散文」降格為「需要合併兩個 YAML 區塊」，這確實恢復了機讀契約（不再有任何邊只存在散文裡），但若下游工具不知道這個合併規則，仍會得到與原始發現一樣的不對稱圖——這是「不回改已核可的 Part A」這條既有規則下無法完全消除的殘留風險，而不是修法本身的缺陷，故仍判定為 Resolved。

**本輪修正動作本身引入的新發現**：R-05（Minor）——`memory.md` 的日記宣稱已把兩套編號空間的說明寫進「來源標籤慣例」表，但實際只在修訂 1 區段開頭加了一段獨立的歷史敘述，表格本身 8 列原樣未動。編號碰撞本身已被消除（裸 `[E6]`–`[E10]` 零殘留、`[DD:E#]` 與新 `[E11]`–`[E15]` 互不誤指），所以這不影響追溯正確性，純屬「自述與實際改動不一致」的文件完整性缺口，且恰好落在本輪 dispatch 要求我逐項核對的那個細項上。

**此修正輪的來源分類**：四項上一輪發現全部確實修復，沒有一項是「看起來修了但其實沒修」；唯一的新發現（R-05）是修正動作遺漏的一個子項（表格未同步），不是修正過程中新引入的架構缺陷，也不是 renumbering 的 regex 誤改了其他內容（`E6`–`E9` 與新 `E11`–`E15` 的全部引用逐一核對皆正確指向各自的問題）。

**給人核准關卡的建議**：READY。無 Critical，Major 數為 0（四項原 Major 全部 Resolved），僅 1 項 Minor（R-05，文件完整性缺口，不影響正確性）。這是本 stage 唯一一次審查額度，建議在核可時將 R-05 記為 accepted risk（或由作者在送交下一階段前補一行慣例表說明，成本很低）；不建議再開一輪驗證，因為本輪查出的問題性質（表格未同步）不會因再審一輪而惡化，且 R-01 的殘留風險是結構性的、再審也無法消除，只能等下游真的需要機械解析時以腳本模板的方式緩解。
