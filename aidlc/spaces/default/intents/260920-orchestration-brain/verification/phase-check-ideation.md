# Phase Boundary Check — Ideation → Inception

<!-- 由 approval-handoff（Ideation 1.7）Step 4 產出。
     Record: 260920-orchestration-brain
     檢查項目依 `.claude/knowledge/aidlc-shared/verification.md` 的
     「Ideation → Inception」列：Intent → Scope → Intent Backlog 一致性、
     所有 scope 項目是否都有 feasibility 背書。
     本檔的每個數字都由實際比對得出，不由印象估計。 -->

## 檢查 1 — Intent → Scope → Intent Backlog 的項數與名稱一致性

| 來源 | 位置 | 能力項數 |
|---|---|---|
| `intent-statement.md` | Initial Scope Signal（8 項條列 ＋ 階層 ＋ 成本編排） | **10** |
| `scope-document.md` | Must 9 ＋ Should 1 ＋ Could 0 ＋ Won't 0 | **10** |
| `intent-backlog.md` | proto-Unit 序 1–10 | **10** |

**結果：PASS。** 三份文件的能力集合為同一組 10 項，逐項對照如下（能力編號
沿用 `scope-document.md` 的編號）：

| 能力 | scope 分級 | backlog 序位 |
|---|---|---|
| 1 統一入口的意圖識別與工作交辦 | Must | 2 |
| 2 跨功能共享的對話脈絡與自動切換 | Must | 5 |
| 3 可在子功能各自開啟新對話 | Must | 8 |
| 4 長短期記憶（語意／程序／情節） | Must | 4 |
| 5 多意圖識別 | Must | 7 |
| 6 多輪對話 | Must | 6 |
| 7 主動通知推播 | **Should** | 10 |
| 8 串流式互動 | Must | 3 |
| 9 專案 → 系統 → 架構圖 階層 | Must | 1 |
| 10 成本／FinOps 能力的編排 | Must | 9 |

無孤兒能力（scope 有而 backlog 無）、無孤兒 proto-Unit（backlog 有而 scope 無）。

## 檢查 2 — 所有 scope 項目是否都有 feasibility 背書

比對方式：對 `feasibility-assessment.md` 的「技術可行性逐項」表（9 列）逐一
對應到能力編號，再對三份 feasibility 產出（assessment、constraint-register、
raid-log）做關鍵詞計數，確認沒有能力是「完全沒被提到」。

| 能力 | feasibility 背書 | 判定 |
|---|---|---|
| 1 意圖識別與工作交辦 | 「統一入口的意圖識別與工作交辦」專列，判定可行 | OK |
| 2 跨功能共享的對話脈絡 | 「跨功能共享的對話脈絡」專列，判定可行 | OK |
| 3 可在子功能各自開啟新對話 | **無任何一列；三份產出中「新對話」「子功能」關鍵詞計數皆為 0** | **WARN** |
| 4 長短期記憶 | 「三種長短期記憶」＋「記憶層的授權」兩列 | OK |
| 5 多意圖識別 | 無專列；僅在收窄後的 P-1 試探描述中出現 1 次（「多意圖識別的分支結構」） | **WARN（部分）** |
| 6 多輪對話 | **無任何一列；三份產出中「多輪」關鍵詞計數為 0** | **WARN** |
| 7 主動通知推播 | 「串流回覆與主動推播」列，判定可行（通道即 WebSocket） | OK |
| 8 串流式互動 | 同上列；三份產出共 11 次提及 | OK |
| 9 專案→系統→架構圖 階層 | 「專案 → 系統 → 架構圖 階層」專列，並為 RAID R-1 的主體 | OK |
| 10 成本／FinOps 能力的編排 | 「編排既有的成本／FinOps 能力」＋「成本回覆的串流交接」兩列 | OK |

**結果：PASS WITH WARNINGS（3 項）。**

三項 WARN 全部是 **Must** 能力：能力 3、5、6。它們共同的性質是「建立在
能力 1（意圖識別）與能力 2（共享脈絡）之上的延伸行為」，因此 feasibility
很可能把它們**隱含在**那兩列裡。但隱含不等於背書——`verification.md` 要求
的是「所有 scope 項目都有 feasibility 背書」，而這三項在三份 feasibility
產出中的關鍵詞計數分別為 0、1、0。

**這不構成 No-Go。** 理由：三項都不引入新服務、新依賴或新技術層（能力 3 與
6 是 session 層的使用方式，能力 5 是意圖識別機制的擴充），且能力 5 已部分
由收窄後的 P-1 試探涵蓋。它們的風險型態是「需求寫不清楚」而非「做不出來」。

**處置（指派，寫入本檔即生效）**：`requirements-analysis`（2.3，
`execution: ALWAYS`，無 skip 風險）在撰寫可驗收需求時，必須為能力 3、5、6
各自寫出可測的不變量，不得以「已隱含在能力 1／2 的需求裡」帶過。選這一站
是因為它是本 scope 內下一個 `execution: ALWAYS` 的站，指派不會無聲落空。

## 檢查 3 — 上游 artifact 的產出完整性

| 站 | 宣告的產出 | 實際存在 | 判定 |
|---|---|---|---|
| intent-capture（1.1） | `intent-statement.md`、`stakeholder-map.md` | 皆存在 | OK |
| market-research（1.2） | `competitive-analysis.md` | 不存在 | **預期缺席**（SKIP） |
| feasibility（1.3） | `feasibility-assessment.md`、`constraint-register.md`、`raid-log.md` | 皆存在 | OK |
| scope-definition（1.4） | `scope-document.md`、`intent-backlog.md` | 皆存在 | OK |
| team-formation（1.5） | `team-assessment.md` | 不存在 | **預期缺席**（SKIP） |
| rough-mockups（1.6） | `wireframes.md`、`user-flow.md` | 皆存在 | OK |
| approval-handoff（1.7） | `initiative-brief.md`、`decision-log.md`、`approval-handoff-questions.md` | 皆存在 | OK |

**結果：PASS。** 兩項缺席皆為 scope 設計的結果（`Stages to Skip` 逐字列出
`1.2 (market-research)`、`1.5 (team-formation)`），非產出遺漏。

## 檢查 4 — 跨階段矛盾偵測

| 檢查 | 結果 |
|---|---|
| 成本能力的定位在四站之間是否一致？ | **一致**。intent-capture 修訂 1 後全面改為「編排既有能力」，feasibility、scope-definition、rough-mockups 皆承接此前提；已失效的 Q6／Q11 在各檔中均有就地標註 |
| 共享工作階段的頁面範圍是否一致？ | **一致**。四站皆為入口頁 ＋ `/workspace` ＋ `/assessment`，不含 `/cost` 與管理頁 |
| 能力 10 的分級在 scope 與 backlog 之間是否一致？ | **一致**。兩處皆為 Must（修訂 1 由 Should 升回），且兩處都寫明其序位由技術依賴決定、非由分級決定 |
| feasibility 的指派對象是否都存在於本工作流程？ | **否 —— 已處置**。[F10] 指派的 `application-design` 不存在於編譯後的 34 站中；已由 [H3] 改指派 `domain-design`（2.6），並記入 `initiative-brief.md` 的交接表 |
| 指派對象是否有 `CONDITIONAL` 而可能被 skip 者？ | **有 —— 已處置**。`domain-design`（2.6）與 `contract-design`（2.8）皆為 CONDITIONAL；已由本站訂定轉移規則（見 `initiative-brief.md`） |

**結果：PASS。** 兩項不一致皆已在本站處置並記入交接表，無殘留矛盾。

## 總結

| 檢查 | 結果（**修訂 5 重驗，2026-10-01T23:03:08Z**；修訂 3 的重驗為 2026-10-01T14:58:51Z） |
|---|---|
| 1. Intent → Scope → Backlog 一致性 | **PASS**（**12 = 12 = 12**，無孤兒；本輪以腳本實算三份文件的能力集合並比對，非目視） |
| 2. Scope 項目的 feasibility 背書 | **PASS WITH WARNINGS（警告範圍已擴大，見下）** |
| 3. 上游產出完整性 | **PASS**（兩項缺席為 SKIP 的預期結果） |
| 4. 跨階段矛盾偵測 | **PASS WITH WARNINGS**（修訂 5 逐項重掃，見下） |

### 檢查 2 的警告範圍在修訂 3 擴大 —— 如實記載，不美化

原警告為能力 3／5／6 在 feasibility 三份產出中的關鍵詞計數分別為 0／1／0。
**修訂 3 重驗時查出能力 11 與能力 12 的情況更徹底**：以八個關鍵詞（`需求頁`、
`需求欄位`、`成員管理`、`project_admin`、`project_owner`、`MCP`、`能力 11`、
`能力 12`）對 `feasibility-assessment.md`、`constraint-register.md`、
`raid-log.md` 三檔合併搜尋，**全部 0 命中**。

**原因是結構性的，不是疏漏**：這兩項能力都在 feasibility 跑完之後才新增（能力
11 於 scope 修訂 2、能力 12 於修訂 3），而 feasibility 從未重跑。引擎自己也標
示 `Directly stale: feasibility` 並建議 `/aidlc --stage feasibility`。

**兩項的風險型態不同，必須分開判定**：

| 能力 | 風險型態 | 判定 |
|---|---|---|
| **12 成員管理** | 「需求寫不清楚」而非「做不出來」 | 其可行性已由本站 Go／No-Go 的逐項表以**查證過的事實**覆蓋（不引入新服務／新暴露面／新依賴／新技術層；`[M3]`=A 與 `schema_rbac.sql:330` 的現況一致，不需改 schema 約束）。**此項的缺口為形式缺口** |
| **11 專案系統資訊需求頁** | **可能是「做不出來」** | `[S13]`=A 定案「agent 經**大腦端 MCP 封裝**取用欄位，底下走 HTTP 帶使用者 token」——這是一個**全新的整合機制**，repo 內無前例，且沒有任何一份 feasibility 產出評估過它。**此項的缺口是實質缺口，不是形式缺口** |

**本檔不自行決定它是否阻擋**。能力 11 的 MCP 封裝缺少可行性評估，是一個
approval gate 上應由決策者裁決的事項（接受為殘留風險並指派，或重跑
feasibility），已在本輪的核可關卡上提出。

#### 修訂 5 的結果（2026-10-02）：此缺口已補，檢查 2 的警告範圍收回

使用者於修訂 3 的核可關卡選 `[H11]`=B **重跑 feasibility**。該站修訂 2 已為能力 11
與能力 12 各立一列技術可行性判定，並新增 `C-T11`／`C-R3`／`R-12`／`R-13`／`A-7`。
**以同一組八個關鍵詞重新搜尋 feasibility 的三份產出，不再是 0 命中。**

**而那次重跑查出一件八站都沒碰到的事**，使這個回跳的價值不只是補一張表：
既有 `design_agent.py` 的工具脈絡是模組層全域 `_progress_queue`，**已實測**兩個
併發請求會讓使用者 A 收到使用者 B 產生的架構圖 XML。這是跨使用者資料暴露，屬
ADR-0006 的授權面，而它坐在能力 1 與能力 8 的地基上。`[F17]`=A 已列為實作前置
（交接第 21 列）。

**檢查 2 現狀（逐項重算，不宣稱全過）**：以同一組八個關鍵詞重算 feasibility 三份
產出的合併命中：

| 關鍵詞 | 修訂 3 | 修訂 5 | 判定 |
|---|---|---|---|
| `能力 11` | 0 | **7** | 已背書 |
| `能力 12` | 0 | **6** | 已背書 |
| `MCP` | 0 | **20** | 已背書 |
| `需求頁` | 0 | **1** | 已背書（能力 11 自成一列判定） |
| `成員管理` | 0 | **1** | 已背書（能力 12 自成一列判定） |
| `project_admin` | 0 | **1** | 已背書 |
| `project_owner` | 0 | **0** | **關鍵詞假象，非缺口**——feasibility 以 `owner_user_id` 與 `[M3]`=A 指稱同一件事（「被移除的 owner 是唯一成員」正是 `project_owner` 的移除情境），只是沒用這個角色名 |
| `需求欄位` | 0 | **0** | **殘留的真缺口，但很窄**——feasibility 評估了能力 11 的**通道**（MCP 獨立進程、token 傳遞、`A-7` 的待驗假設），**沒有**評估欄位本身（欄位形狀、數量上限、驗證規則、`[R12]`=D 的「按 agent 分組」是否有技術限制）。風險型態是「需求寫不清楚」而非「做不出來」，與能力 3／5／6 同類 |

**處置**：`需求欄位` 一項併入交接表第 12 列的同一類（可測不變量由
`requirements-analysis` 定義），不另立交接列——它與既有三項的風險型態、承接站、
處置方式完全相同，另立一列只會讓交接表更長而不更清楚。

**原三項警告（能力 3／5／6）不變**，仍指派 `requirements-analysis`（交接第 12 列）。
能力 11／12 的**實質缺口已解除**；`project_owner` 為關鍵詞假象，`需求欄位` 為同類
的窄殘留並已歸入第 12 列。

**附帶記載**：八個關鍵詞的計數是**代理指標而非證明**。本輪有兩個 0 命中，逐一判讀
後一個是假象、一個是真殘留——若只看總數（6/8 有命中）會把兩者混成同一件事。

### 檢查 4 的修訂 5 逐項重掃（2026-10-01T23:02:28Z）

三站重跑（`feasibility` 修訂 2、`scope-definition` 修訂 4、`rough-mockups` 修訂 5）
之後，對四類可能的矛盾各掃一次：

| 掃查項 | 方法 | 結果 |
|---|---|---|
| **4a 能力 11 的通道形狀** | 五份文件各數「獨立進程」與舊「MCP 封裝」的命中 | **一致**。五份皆有「獨立進程」；僅存的兩處「MCP 封裝」各為**引述舊原文的更正註記**（`scope-document` 1 處、`feasibility-assessment` 1 處），已逐處開檔確認 |
| **4b 行號 `:328` → `:330`** | 全 intent 遞迴掃查 | **7 處殘留，逐處判讀後 5 處正確、2 處為真殘留**。正確的 5 處：3 個 `memory.md`（日記，引述錯誤本身）、2 個 `reviews/*.md`（審查員紀錄，**不得編輯**）。真殘留 2 處：`scope-definition-questions.md:374`／`:480`（已核可，於 `initiative-brief` 記為對齊修正，上游不回改） |
| **4c 能力總數與分級** | 三份文件的「12 項」「11 Must」「0.9167」命中 | **一致**。`scope-document` 與 `initiative-brief` 的「11 Must」以表格形式呈現（`\| **Must** \| 11 \|`）而非連續字串，故關鍵詞比對未命中——**這是比對方式的限制，非文件不一致**；已以欄位解析實算複驗：12 列、Must 11、Should 1、11/12 = 0.9167 |
| **4d `FR10.2` 是否被宣稱推翻** | 全 ideation 掃「FR10.2」＋ 推翻／失效類詞 | **無任何文件宣稱它被推翻**。兩處命中各為 `[S13]` 選項 B 的原文（該選項會推翻它，**但未被選**）與作答後果的「維持有效、不推翻」。已由 rough-mockups 修訂 5 的審查員獨立核對選項 A 與 C 的原文 |

**4c 的附帶教訓如實記載**：第一次以關鍵詞比對「11 Must」時得到 0 命中，看起來像
文件不一致；改以欄位解析實算才確認一致。**關鍵詞比對對表格形式的陳述無效**——
若當時直接判為矛盾並去「修正」，會改壞三份正確的文件。

**階段邊界判定：檢查 1、3 PASS；檢查 2 與檢查 4 PASS WITH WARNINGS。**
檢查 2 的能力 11／12 實質缺口已由 feasibility 修訂 2 解除，`需求欄位` 一項併入
交接表第 12 列；檢查 4 的 2 處真殘留為引用定位問題，已於 `initiative-brief` 記為
對齊修正，不產生下游工作。**可進入 Inception。** 原有三項 WARN（能力 3／5／6）的指派不變，仍在
`requirements-analysis`（2.3）。

人工核可：由 approval-handoff 的 approval gate 承載（見 `<record>/audit/`
的 `GATE_APPROVED` 紀錄），本檔不另設勾選欄。
