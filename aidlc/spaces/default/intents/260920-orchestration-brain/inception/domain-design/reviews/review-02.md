## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-02T23:24:07Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| R-01 | Major | `components.md` — Part A（`BrainGateway`／`WorkOrchestrator`／`ProjectHierarchy` 的既有 YAML 區塊）vs Part A'（`ProjectMembership`／`RequirementRegistry`／`ProgressChannel`）vs 「既有元件的 `dependents` 對稱性補充」散文表 | 本檔第 0 節自稱「下方 YAML 是這份檔的單一真實來源……不是手抄」，stage 檔的 8 條 well-formedness 規則之一是 `depends_on`／`dependents` 對稱。逐段機械解析兩個 YAML 區塊（非憑印象）：`depends_on` 欄位的邊總數為 **13**，`dependents` 欄位的邊總數為 **15**，兩者不相等，且具體缺口如下——(a) `ProjectMembership→ProjectHierarchy`、`RequirementRegistry→ProjectHierarchy` 兩條邊只出現在新元件的 `depends_on`，`ProjectHierarchy`（Part A，本輪刻意不回改）的 `dependents` 清單裡沒有對應項；(b) `BrainGateway→ProjectMembership`、`BrainGateway→RequirementRegistry`、`BrainGateway→ProgressChannel`、`WorkOrchestrator→ProgressChannel` 四條邊只出現在新元件（`ProjectMembership`／`RequirementRegistry`／`ProgressChannel`）的 `dependents` 清單，`BrainGateway`／`WorkOrchestrator`（Part A，同樣不回改）的 `depends_on` 清單裡沒有對應項。作者在「既有元件的 `dependents` 對稱性補充」一節**已經誠實列出這六處缺口**並說明理由（`refined-mockups:c3`：不回改已核可的 Part A），但解法是一張**散文表**，不是把對稱關係寫回任何 YAML 結構。結果是：這份檔案宣稱的「單一機讀真實來源」事實上在 6 條邊上**分裂成兩份**——一份在 YAML、一份在 Markdown 表——而任何照字面只解析 `components:` YAML 區塊的下游工具或未來 sensor，都會在這 6 條邊上得到不對稱的圖，看不到散文表的存在。這不是「對稱性被違反」（作者已證明聯集後無環、無矛盾），而是「單一真實來源的契約被打破」：對稱性現在需要人工合併兩種格式才能恢復，而 stage 檔要求的是機讀目錄本身自洽。 | 把六條缺的邊**寫回 YAML**，而不是只寫進散文表——即使這代表要以「附加區塊」的方式對 Part A 的 `BrainGateway`／`WorkOrchestrator`／`ProjectHierarchy` 補上缺的 `depends_on`／`dependents` 項（例如一個獨立的 `Part A''：既有元件的邊補充` YAML 區塊，只含新增的邊，而不觸碰 Part A 原有的其他欄位），使「Part A ＋ Part A' ＋ Part A''」的 YAML 聯集本身對稱，不需要讀者先讀一張 Markdown 表才能重建真正的圖。 | New |
| R-02 | Major | `components.md` 第 845 行「修訂 1 的七項自檢逐項結果」第 6 項（可算的數字先算再寫） | 自檢聲稱「無環（以 DFS 三色法對 **14** 條邊實算，拓樸排序存在）」。獨立機械核對：YAML `depends_on` 欄位的邊總數為 13，`dependents` 欄位暗示的邊總數為 15，兩者聯集（真正的邏輯邊集合）為 **17**。13、15、17 都不等於 14，且沒有任何一種合理的計數方式（僅新邊、僅舊邊、僅一欄）會得出 14——9 條新邊 ＋ 8 條舊邊 ＝ 17，不是 14。這代表這一項自檢**沒有真的對完整圖跑過**，而「可算的數字先算再寫」正是 `project.md` 在本 intent 的 `delivery-planning`／`domain-design`／`units-generation` 等多個學習條目反覆點名、且本站自己在 ADR-0006 判定一節也引用過的規則。我用上面 R-01 查出的 17 條邊集合獨立跑了 DFS 三色法，確認**無環**（拓樸排序確實存在）——所以本站的結論是對的，但支撐它的那個數字是錯的，意味著這個檢查項目的「已跑過」宣稱不可信。 | 重新以腳本對 Part A ＋ Part A' 的 YAML 聯集（或聯集 ＋ R-01 修復後的完整對稱 YAML）跑一次 DFS 無環檢查，並把實際邊數（17，或 R-01 修好後的新數字）寫進自檢表，取代「14」。 | New |
| R-03 | Major | `decisions.md` ADR-010（`ProjectMembership`，新增 `project_members`／`reselection_events` 兩表）、ADR-011（`RequirementRegistry`，新增 `system_requirement_fields` 一表） | `project.md ## Mandated` 逐字要求：新增表時**必做 1**（`schema_rbac.sql` 同步）與**必做 2**（`DEPLOY.md` 同步）為 blocking，未完成不得標示相關階段完成。本檔自己在同一份文件的 `ADR-009`（新增 `DiagramChangeRecord` 一表）明確寫下「並觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步（本 intent 已因 `projects`／`systems` 觸發同一條規則，故邊際成本低）」，在 N-11（pgvector image／Ollama 服務）也同樣點名了 blocking 同步。但 ADR-010／ADR-011 新增的三張表（`project_members`、`reselection_events`、`system_requirement_fields`）在 `components.md`／`decisions.md` 全文裡**沒有任何一處**提到 `schema_rbac.sql` 或 `DEPLOY.md`（已用 grep 核對），revision 1 的交接事項 `DG-4`–`DG-8` 也沒有這一項。這是同一份文件對同一條已知規則的不一致套用——不是沒注意到這條規則（文中兩處引用過），而是對這一輪新增的三張表漏套用。 | 在 ADR-010／ADR-011 的 Consequences 或 revision 1 的交接事項補一項，明確點名三張新表觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步，與 ADR-009／N-11 的待辦並列，避免下游（`units-generation`／`code-generation`）在切單元或寫碼時才發現這個 blocking 義務。 | New |
| R-04 | Minor | `domain-design-questions.md` 第 48–279 行（本輪前，`[DD:E6]`–`[DD:E9]`）vs 第 400–521 行（修訂 1，`[E6]`–`[E9]`） | 本檔「來源標籤慣例」表明文規定 `[DD:E<n>]` 是「本站新增——domain-design 的作答（用 E 避開既有 D／DM 撞號）」，刻意設計成不與其他階段撞號。但修訂 1 把同一份問題檔裡的四個新問題同樣編號為 `E6`–`E9`（不帶 `DD:` 前綴），而這四個號碼在本輪之前已被用於完全不同的問題（原 `E6`＝Redis session 存活期、`E7`＝語意記憶檢索方式、`E8`＝「需求」實體承載、`E9`＝本機 embedding 切換）。`decisions.md`／`components.md` 內以 `[DD:E#]` 與裸 `[E#]` 兩種形式分別引用這兩組問題（已用 grep 核對：所有 `[DD:E#]` 引用都指向原 E6–E9，所有裸 `[E#]` 引用都指向修訂 1 的新 E6–E9），目前靠「有無 `DD:` 前綴」這個未明文的慣例區分，一旦有人誤刪前綴或誤加前綴，追溯就會指向錯誤的問題。 | 修訂 1 的四個新問題改用未使用過的編號（如 `E10`–`E13`，注意 `E10` 已被原處答案使用，故应從 `E11` 起），或在「來源標籤慣例」表補一行明確說明「修訂輪的 `[E<n>]`（無 `DD:` 前綴）與原輪的 `[DD:E<n>]` 是兩套不同的編號空間」，使慣例本身自洽。 | New |

### Validation Tool Results

本站未列出可透過 shell 直接執行的 stage-specific validation tool（`sensor-upstream-coverage`／`sensor-traceability`／`sensor-required-sections`），故以等價的手動機械核對取代，結果如下：

| 檢查 | 結果 | 說明 |
|---|---|---|
| 元件計數（6→10） | **準確** | 逐 YAML 區塊解析 `^  - name:`，Part A 6 個 ＋ Part A' 4 個 ＝ 10 |
| 實體計數（7→10） | **準確** | 逐元件解析 `entities:` 子區塊的 `- name:`（非整檔 grep；整檔 grep 確認會得到作者警告的錯數字 30，因為把 `external_dependencies` 的名字一起算了進去） |
| ADR 計數（9→16） | **準確** | `grep -c "^## ADR"` ＝ 16 |
| 追溯表（20→31，0 GAP） | **準確** | `traceability.json` 的 31 個 `upstream_ids` 與 `stories.md` 的 `grep -oE "^### US[0-9]+\.[0-9]+"` 31 個標題**逐一比對完全一致**（無遺漏、無多餘）；`coverage` 陣列 31 筆、`status=GAP` 計數為 0 |
| `depends_on`／`dependents` 對稱性（declared ✓） | **不準確——見 R-01** | 機械解析結果為 13 vs 15，不對稱；作者的「✓」驗證結果表（第 291–306 行）是 Part A 單獨跑的舊結果，未對 Part A ＋ Part A' 的聯集重跑 |
| 無環宣稱（「14 條邊」） | **結論正確、過程數字錯誤——見 R-02** | 以真實聯集 17 條邊獨立跑 DFS 三色法，確認無環；但作者宣稱的「14」無法由任何子集合或聯集算出 |
| 程式碼引用逐字核對（6 處） | **全部準確** | `backend/cost/advice_orchestrator.py:23-24`（`_progress`／`_progress_lock` 字面一致）、`backend/cost/estimate_readers.py:247-251`（`best_clouds` 的 `key=lambda item: (-item[1], item[0])` 一致）、`backend/services/design_agent.py:160/163/203/211`（`_drain_progress` 定義、`get_nowait()`、兩個呼叫點，且確認 `_progress_queue` 為模組層全域、`finally` 區塊重設為 `None`，佐證「A 收到 B 的 XML」的競態說法成立）、`backend/services/wa_collab_orchestrator.py:79`（`run_design_agent(messages, current_xml)` 未傳 `thread_id`，確認原樣）、`backend/services/user_router.py:213`（`_audit_append` docstring 確認寫入標準 logger，UI 讀不到）、`requirements.md:613/614/617`（encryption／network exposure／「四面向皆適用」三處字面一致） |
| `schema_rbac.sql:328`／`:330` 一類舊教訓 | **本輪未見相同錯誤** | 本輪新增的三張表未引用任何 `schema_rbac.sql` 行號（因為完全沒提到 `schema_rbac.sql`，見 R-03），故此類行號誤引風險在本輪不適用 |
| ADR-0006 四面向表（revision 1 專屬） | **準確，且與 `requirements.md:612-615` 的判定逐字一致** | 本站「不重判適用性，只判新落點」的立場誠實且可查核：IAM 三處、encryption 一處、network exposure 一處（已正確寫成「第二個新增進程邊界」，未重複 review-01 之後 `user-stories` 階段記錄過的「唯一對外介面」誤述）、audit logging 兩處 |
| 交接目標的 `execution` 值（`DG-4`–`DG-8`） | **全部準確** | 對照 `.claude/tools/data/stage-graph.json`：`units-generation`＝ALWAYS、`nfr-requirements`＝CONDITIONAL、`contract-design`＝CONDITIONAL、`code-generation`＝ALWAYS，與聲稱一致；且所有轉移目標皆在 `aidlc-state.md` 的 `Current Stage: domain-design` 之後，無「指派到已過游標的站」的既有失誤形狀 |

### Summary

**獨立重算的結果**：元件 10、實體 10、ADR 16、追溯表 31/31（0 GAP）、程式碼引用 6 處全部逐字準確——這些數字全部與作者宣稱一致，判定為**準確**。但圖的對稱性（13 條 `depends_on` 邊 vs 15 條 `dependents` 邊，6 條邊只在一個方向出現）與無環自檢引用的邊數（「14」，無法由 13、15 或聯集 17 推出）兩項**不準確**，這是本輪最核心的技術發現。

**Part A' 拆分與機讀契約的判斷**：拆分本身（新元件獨立 YAML 區塊、既有元件的新邊改用散文表）是為了遵守「不回改已核可的 Part A」這條既有規則而做的合理權衡，而且作者**誠實揭露**了這六處缺口（沒有隱藏）。但這個權衡的代價是機讀契約本身被打破——這份檔案第 0 節自稱的「單一真實來源」現在需要人工合併 YAML 與 Markdown 才能恢復對稱，這正是 dispatch 要求我重點判斷的問題，結論是：**不成立**。建議的修法是用一個只含新邊的附加 YAML 區塊取代散文表，而不是放棄「不回改 Part A」這個原則（兩者並不互斥）。

**ADR-011 的判斷**：「兩個『需求』並存且改名」不是粗糙的文字遊戲，而是經得起查核的真實區分——我逐字核對了 `ADR-009` 的 Context／Decision 與 `FR11.2`／`[R12]`=D／線框 §17 的內容，兩者在基數（一次架構圖變更可能由多個需求驅動，需求欄位是每系統一組固定欄位）、讀寫清三問的落點、以及驅動它們的變更理由上**確實不同**，且 `ADR-009` 本身是使用者在 `[DD:E2]` 重新框定後自己定案的，依 `project.md` 的既有規則不能被 AI 逕自推翻——保留它並界定其適用範圍是正確處置，不是迴避衝突的合理化。這一項判斷**成立**。

**實體形狀界線**：三個新實體（`ProjectMember`／`ReselectionEvent`／`SystemRequirementField`）的屬性清單只列名稱，不含型別、驗證約束或關係基數，符合 stage 檔「只記歸屬與形狀」的界線；`McpBridge`／`ProgressChannel` 擁有零實體有明確理由（前者的 schema 是程式宣告非資料，後者的佇列生命週期短於一次請求、寫成實體會暗示該被持久化），這兩個判斷我認為站得住。

**ProjectHierarchy 自相矛盾的重蹈**：review-01 的 R-01（`ProjectHierarchy.behaviour` 的「不得同進程繞過」與其自身 `sync` 入邊自相矛盾）在本輪沒有重演——`ProjectMembership.behaviour` 沒有對它自己的 `sync` 入邊（`BrainGateway`／`RequirementRegistry`／`McpBridge`）宣告任何「不得同進程呼叫」之類的禁令；真正的「不得同進程繞過」宣告只出現在 `McpBridge.behaviour` 裡，針對的是它呼叫既有 FastAPI API 的 HTTP 路徑，與 `McpBridge` 自己被同進程呼叫的事實不衝突。這是本輪對上一輪教訓的確實吸收。

**人需要外部視角才看得出來的部分 vs 作者自己機械檢查就該抓到的部分**：R-02（自檢宣稱的邊數與任何可能的機械算法都不符）與 R-03（同一份文件對同一條已知 blocking 規則的不一致套用）都是**作者自己的既有檢查程序原本就該抓到**的——前者違反的正是本 intent 反覆寫入 `project.md` 的「可算的數字先算再寫」，後者是同一份文件內部的自我矛盾（已在別處正確套用同一條規則）。R-01（YAML 對稱性契約被打破）則需要一個**獨立讀者**從「這份檔案自稱的機讀契約，和它實際提供的機讀內容是否一致」這個角度去看才會發現——作者的散文揭露讓人類讀者能重建完整圖，但沒有人會因為讀了散文表就認定 YAML 本身仍然對稱，這正是架構評審該補上的那一層。R-04（標籤編號撞號）介於兩者之間：機械 grep 能找到，但需要先讀懂「來源標籤慣例」這條規則的意圖才會意識到它被違反。

**給人核准關卡的建議**：三項 Major（R-01／R-02／R-03）依評審規則（NOT-READY if any Critical OR >2 Major）已越過門檻，建議 Request Changes。三項都不否定六至十個元件的拆分本身——拆分的架構判斷（`ProjectMembership`／`RequirementRegistry`／`McpBridge`／`ProgressChannel` 四個新元件的邊界、ADR-011 的「兩個需求」區分、ADR-012 的授權落點、ADR-014 的清除端擁有者）我認為都經得起查核且站得住；三項發現全部是**本檔自己宣稱的機讀契約與送審前自檢**（單一真實來源、對稱性、可算的數字、已知的 blocking 規則）沒有被完整兌現，修法成本都不高（補一個 YAML 區塊、重跑一次腳本、補一句交接事項），不需要重新考慮任何既有的元件邊界決定。
