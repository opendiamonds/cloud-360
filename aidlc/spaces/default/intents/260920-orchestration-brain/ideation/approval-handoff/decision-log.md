# Decision Log — Ideation（統一入口大腦）

<!-- Stage: approval-handoff（Ideation 1.7）· Record: 260920-orchestration-brain
     本文件逐條記錄 Ideation 五個執行站所做的全部決議，供 Inception 之後的
     任何一站查證「這件事是誰、在哪一站、以什麼理由定下來的」。
     決議內容一律取自各站問題檔的 [Answer] 與其選項原文，不改寫、不概括。
     這不是 team.md 所規範的 decisions-log.md（那份只在使用者明確要求時寫）。 -->

## 這份紀錄涵蓋什麼

| 站 | 問題檔 | 題數 | 狀態 |
|---|---|---|---|
| intent-capture（1.1） | `intent-capture-questions.md` | Q1–Q14 | 全部已答；含修訂 1 與 iteration 2 修正 |
| market-research（1.2） | — | — | **SKIP**（`competitive-analysis.md` 不存在） |
| feasibility（1.3） | `feasibility-questions.md` | F1–F15（F12 由 F13 取代，不作答） | 全部已答；含修訂 1 |
| scope-definition（1.4） | `scope-definition-questions.md` | S1–S11 | 全部已答；含修訂 1 |
| team-formation（1.5） | — | — | **SKIP**（`team-assessment.md` 不存在） |
| rough-mockups（1.6） | `rough-mockups-questions.md` | R1–R8 | 全部已答；經一次人工退回與兩輪審查 |
| approval-handoff（1.7） | `approval-handoff-questions.md` | H1–H5 | 全部已答（本站） |

五站的核可關卡全部由同一位決策者通過（[Q8] 確認單一決策者）。工作流程的
`Revision Count` 為 1，唯一一次人工退回發生在 rough-mockups。

---

## intent-capture（1.1）— 產品邊界與意圖

產出：`intent-statement.md`、`stakeholder-map.md`

| # | 決議 | 選擇 |
|---|---|---|
| Q1 | 核心問題為三項並存：使用者要自己決定用哪個功能、上下文在頁面之間斷掉、AI 能力無法組合 | A, B, C |
| Q2 | 四類使用者全部納入：架構設計者、評估／稽核者、成本／FinOps 關注者、管理者／平台維運者 | A, B, C, D |
| Q3 | 三項成功指標：意圖識別準確率、跨頁面上下文保留率、首字回應時間 | A, B, C |
| Q4 | 現在做的理由：既有 AI 功能路徑已達極限，再加功能就是第三、第四個孤島 | A |
| Q5 | 作業對象**本次一併建立「專案 → 系統 → 架構圖」正式階層**，而非只綁既有架構圖 | B |
| Q6 | （原題：第一版要編排哪些功能 agent）**已由 Q12 取代**，其前提「成本能力不存在」被推翻 | C（失效） |
| Q7 | 共享工作階段涵蓋**入口頁 ＋ `/workspace` ＋ `/assessment`** 三處，不含管理頁面與 `/cost` | A |
| Q8 | **單一決策者、無其他關係人、不需對外回報節奏** | A |
| Q9 | 沿用 `agent-orchestration-brain` 的工作計畫，產品邊界即 intent-statement 所述能力集合，不增不減 | A |
| Q10 | 管理者／平台維運者改列**間接服務對象**（其需求由長期記憶或既有稽核紀錄承載） | C |
| Q11 | （原題：成本空殼要交付什麼）**已由 Q12 取代** | B（失效） |
| Q12 | 大腦把成本類問題**路由到既有 `/api/cost/v1`**，使用者真的問得到成本答案；不新建成本能力 | A |
| Q13 | 大腦**自建獨立的 LangGraph runtime**，與既有 `services/langgraph_runtime.py` 並行 | B |
| Q14 | 成本答案**就地在入口頁呈現**，使用者不需離開入口頁 | A |

**本站的兩次方向性更正**（皆已在產出中就地記載，不回改已核可的上游）：

1. **修訂 1（2026-09-21）**：上游前提「成本／FinOps 能力完全不存在」在
   intent-capture 執行當下為真，但 `ut` 已於 2026-09-20 合併 PR #647
   （cost-estimation-finops），成本能力現已存在且規模不小。使用者裁決**跳回
   intent-capture 以 Modify 模式修訂**；Q6／Q11 由新增的 Q12 取代，受影響的
   8 處落點逐一更新。
2. **iteration 2 修正 R-05（Critical）**：成本關注者由間接服務改為直接服務後，
   與 [Q7] 產生同型張力，原先由 conductor 自行寫一句推論句化解並掛 `[Q7]`
   標籤。審查抓出後比照 [Q10] 的先例**加開 Q14** 由使用者定案，推論句移除、
   標籤改掛 `[Q14]`。

## feasibility（1.3）— 技術可行性與約束

產出：`feasibility-assessment.md`、`constraint-register.md`、`raid-log.md`

| # | 決議 | 選擇 |
|---|---|---|
| F1 | **沿用既有 LLM 切換層，但大腦要能獨立指定模型**（編排層與功能 agent 可用不同模型） | B |
| F2 | Redis 以**新增第 5 個容器**的形式進入 `docker-compose.deploy.yml` | A |
| F3 | 三種記憶放**同一個 database、獨立 schema**（保留原生 join；DB 權限鎖到記憶 schema） | B |
| F4 | 串流**改用 WebSocket**（雙向，可承載主動通知推播）；既有 3 個 SSE 端點不動 | B |
| F5 | episodic memory：**設保存期限 ＋ 使用者可自行刪除自己的記憶** | C |
| F6 | 做**兩個**技術試探：LangGraph 編排模型、記憶層資料模型 | A, B |
| F7 | 三個成功指標的門檻值**留到 `requirements-analysis`** 定案 | B |
| F8 | 有成本上限（無硬性時程） | C |
| F9 | 記憶層**內建最小權限模型**（記憶列帶擁有者與可見範圍欄位），介接系統映射自身角色 | B |
| F10 | 遷移風險**交給設計階段處理，不做第三個試探**；要求產出遷移步驟與回復方式 | A |
| F11 | 成本上限**沒有硬數字，原則是「盡量省」**（編排層一律選便宜快速的模型） | B |
| F12 | （硬性月費上限是多少）**已由 F13 取代，不作答** | — |
| F13 | 成本上限**不由本系統承載**，改在 OpenRouter 後台設定；本 intent 不做計量與 admin 設定 | A |
| F14 | 大腦以 **HTTP 呼叫自己的 `/api/cost/v1` 並帶使用者的 token**，使既有授權 dependency 照常執行 | A |
| F15 | 成本 job 的狀態事件**轉譯進大腦的訊息流**，不等 job 完成才回覆 | A |

**本站的兩項更正**（記於 `raid-log.md` 的 Issues）：

- **I-1**：`team.md ## Code Style` 記載「Backend 依賴 100% 未 pin」，實測
  `requirements.txt` 已有兩項精確釘選（`fastapi[standard]==0.141.1`、
  `pydantic==2.13.4`）。規則層敘述已過期，待下一輪 practices-discovery 更正。
- **I-2**：F11 的作答曾被轉錄錯誤（使用者實選 A，被記為 C），原因是提問時
  選項順序與問題檔不同而**依位置而非依內容**對應。已就地更正；最終答案為
  使用者其後改選的 B。

**修訂 1 帶來的信心上調**（不是只會下調）：重新查證後 `langgraph==1.2.11`
已釘選並在部署環境運行，`A-3`「LangGraph 與 Python 3.12 相容」由假設**升為
既成事實**；`P-1` 試探因 repo 已有可運行前例（`cost/cost_advice_agent.py`）
而**收窄**為本 intent 獨有的部分。

## scope-definition（1.4）— 能力分級與交付序

產出：`scope-document.md`、`intent-backlog.md`

| # | 決議 | 選擇 |
|---|---|---|
| S1–S3 | 十項能力**全部**被選為 Must | A,B,C,D / A,B,C,D / A,B |
| S4 | 沒被選為 Must 的統一放 Should（作答當下 Should 桶為空，無作用對象） | A |
| S5 | **沒有任何項目列入 Won't Have** | A |
| S6 | （交付排序偏好）由 S10 承接：使用者要求本站先提建議方案再確認 | D |
| S7 | **沒有綁定特定能力的硬期限** | A |
| S8 | 十項全為 Must —— 使用者選擇「我要降別的項目」，由 S9 點名 | X |
| S9 | 降為 Should 的是：**主動通知推播（能力 7）** 與 **成本／FinOps 交接介面（能力 10）** | G, J |
| S10 | 交付排序採**風險優先 ＋ 不可覆寫的技術依賴序** | A |
| S11 | **能力 10 由 Should 升回 Must**（修訂 1：原降級依據「只是個空殼」已不存在） | A |
| S12 | **新增能力 11「專案系統資訊需求頁」並列 Must**（修訂 2：2026-09-29 會議結論） | A |
| S13 | 專案／系統資訊的欄位由 agent 經**大腦端 MCP 封裝**取用，底下走 HTTP 帶使用者 token（修訂 2） | A |
| S14 | `project_admin` **不進** `CANONICAL_ROLES`（修訂 2；非管理者那一層叫什麼未定，見交接第 13 列） | A |
| S15 | `system_admin` 即既有的 `Platform_Admin`，不另立角色（修訂 2） | A |
| S16 | **新增能力 12「專案成員管理」並列 Must**（修訂 3；四項行為全數在範圍內） | A |
| S17 | 成員管理為**獨立一頁**，入口是專案詳情頁的動作，不在 Sidebar 新增第一層項（修訂 3） | B |

**本站的一次方向性更正**：S9 的初次作答與 [Q1]／[Q3]／[Q5] 有三處衝突，
conductor 先以矛盾清單提示「方向可能讀反」，使用者回覆「沒反，就是這樣」；
直到把後果具體化為「兩項 Must 各自依賴一項 Should，故 Must 集合無法獨立
交付」，使用者才主動更正為 8 Must／2 Should。修訂 1 後為 9 Must／1 Should；
修訂 2 新增能力 11（[S12]）後為 10 Must／1 Should；修訂 3 新增能力 12（[S16]）
後為 **11 Must／1 Should**（實算 11/12 = 0.9167，約 92%）。

**修訂 3 刻意不加的依賴邊**：能力 12 與能力 11 之間不列依賴。兩者都依賴能力 9
的階層，但「管誰能進這個專案」不需要「需求欄位已填好」才成立；依 `project.md`
的既有規則，依賴的判準是「B 沒有 A 就不成立」而非「B 有了 A 更完整」。

## rough-mockups（1.6）— 線框與流程

產出：`wireframes.md`（**27** 格線框 ＋ 能力覆蓋對照表）、`user-flow.md`（**9** 條流程）

| # | 決議 | 選擇 |
|---|---|---|
| R1 | 統一入口頁放進 Sidebar（依 user story 大類分層） | A |
| R2 | 入口頁骨架為**對話為主 ＋ 頂部脈絡列**（常駐但不佔寬度） | C |
| R3 | 目前作業對象在子頁面（`/workspace`、`/assessment`）以脈絡列呈現，切頁時跟著過去 | A |
| R4 | 成本答案在入口頁以**結構化卡片**呈現 | B |
| R5 | 成本 job 的 `progress` 事件以**單一則就地更新**的訊息呈現 | A |
| R6 | 子功能頁「另開新對話」的入口由**脈絡元件統一承載** | B |
| R7 | 裝置與無障礙底線：**桌機 ＋ 平板／手機響應式 ＋ WCAG 2.1 AA** | C |
| R8 | 入口頁權限落點走既有的 `DefaultRedirect` 瀑布（矛盾偵測加開的題） | A |
| R9 | Figma 設計檔為**視覺參考**，ASCII 線框仍是本站的正式產出（修訂 2） | A |
| R10 | 能力 11 切為**兩頁**：清單／建立頁 ＋ 詳情頁（內含總覽／需求／記憶摘要三籤）（修訂 2） | B |
| R11 | 能力 11 在 Sidebar 為**獨立第一層**，與「入口」並列（修訂 2） | A |
| R12 | 需求欄位為**按 agent 分組的固定欄位**（組內固定，可隨新 agent 增組）（修訂 2） | D |
| M1 | 自動改選後，橫幅給**新任管理者**；成員清單**不標示**「自動取得」與「被指定」的差別（修訂 3） | B |
| M2 | 成員角色在**成員詳情頁**變更，不在清單就地改（修訂 3） | C |
| M3 | 被移除的 `project_owner` 是專案唯一成員時，**擋下停用**並要求先指定接手人（修訂 3） | A |

**R12 選 D 而非更有彈性的 B（自由鍵值對）的理由**：自由欄位會把欄位語意交給
LLM 解析，而 `project.md` 記載本 repo 的三塊結構性盲區之一正是「所有 LLM
路徑」——那是這個 repo 已經付過代價的地方。此代價在選項原文逐字揭露，不是只
寫「比較不好維護」。

**M3 選 A 的依據是查證而非偏好**：`schema_rbac.sql:328` 的 `owner_user_id` 為
`NOT NULL` 且無 `ON DELETE` 子句——資料庫今天就會擋下刪除唯一成員的 owner。
A 是四個選項裡唯一不留壞資料、且**不需改 schema** 的一個；B／C／D 都得先放寬
那個約束。

**M1=B 的已揭露代價**：其他成員在成員清單上看不到自動改選發生過。授權變更的
紀錄仍存在（成員詳情頁的變更紀錄與後端稽核），但需主動查看。

**本站經歷一次人工退回與一次重跑**：

1. 第一次核可關卡上，使用者選 **Request Changes**，要求補「意圖識別錯誤／
   不確定」的畫面狀態。原稿四條流程全為成功面，而 `ux-guide.md` 的 user flow
   格式明文要求 `Error paths`，且「意圖識別準確率」是三個成功指標之一——
   會失敗且被量測的能力，流程上必須有可救回的路徑。補上的是 `wireframes.md`
   第 12、13 節與 `user-flow.md` 的 Flow 5。
2. 補完後因 conductor 的**送審順序錯誤**（記錄送審請求之後又改了產出），
   審查結論記不進去，走 redo 重跑整站（以 Modify 模式保留既有產出）。

**重跑後的審查（advisory，一輪）結果**：6 項發現，5 項 Resolved、1 項 New。

- **R-06（Minor，New，已接受）**：第 13 節 ASCII 框內「這件沒有產生任何
  變更，不需要你回頭清理」為無條件語氣，其限定（這是該情境的文案、非普遍
  承諾）寫在 30 行外的本文。核可時以**已接受風險**放行，帶進 `refined-mockups`
  （2.5）。
- 已解決的 5 項中，兩項 Major 是補正時**自己新引入**的：第 13 節狀態徽章與
  對話不一致（已改為 `[已停掉 (x)]` 並補齊狀態值集合）、以及一句越權的實作層
  保證「不得留下半成品」（已改為只承諾畫面把實情講出來，不承諾系統原子性）。

**本站另記一項待辦**：使用者在核可關卡上提出路由層模型候選
`typesafe/jev-1.13`，指定列入正式待辦，落點為 `nfr-requirements`（3.2）。

## approval-handoff（1.7）— 指派釘死與 Go/No-Go

產出：`initiative-brief.md`、本文件

| # | 決議 | 選擇 |
|---|---|---|
| H1 | 兩個技術試探（P-1、P-2）**併入 `domain-design`（2.6）**執行，不另立時段 | A |
| H2 | 兩項「待指定」的上線前置依賴（推播觸發情境與接收對象、episodic memory 保存期限值）**都在 `requirements-analysis`（2.3）定案** | A |
| H3 | R-1 既有架構圖遷移的設計交給 **`domain-design`（2.6）**，取代 feasibility 原本指向的 `application-design` | A |
| H4 | R-8 兩份 runtime 的一致性驗證交給 **`contract-design`（2.8）**，把兩套串流事件語意收斂成共用契約 | A |
| H5 | **GO**，R-1／A-4／R-8 三項全部以已知殘留風險帶進 Inception，不額外設前置條件 | A |
| H6 | 成員管理的範圍決定**回跳 `scope-definition` 正式定案**（修訂 2；原指派為死指派——目標站雖 `ALWAYS` 卻已完成且在游標之前） | B |
| H7 | 維持 **GO**，D-8／D-9 列為能力 10 與 Assessment 路由的**端到端驗收前置**，不作為進入 Inception 的前置條件（修訂 2） | A |
| H8 | R-11（`LLM_PROVIDER=cli` 靜默失敗）**由本 intent 直接修**（修訂 3；AI 推薦指派 `ut` 側，使用者選擇自行修） | D |
| H9 | rough-mockups 的兩個殘留 Minor 在**本站 artifact 明記為對齊修正**，上游檔不回改（修訂 3） | A |
| H10 | 新角色命名與 RBAC story id 指派 **`domain-design`，並附轉移目標 `requirements-analysis`**（修訂 3） | A |

**H6 的由來值得記下**：rough-mockups 修訂 2 畫了 `[成員]` 按鈕後查出能力 11
的定義裡沒有成員管理，處置是**移除按鈕而非補畫面**（畫一個沒有範圍的
affordance 會讓使用者點了無處可去，也讓下游以為它被設計過），並把範圍決定回送
`scope-definition`。本站進一步查出那個回送是**死指派**。這是本 intent 在
「指派 `CONDITIONAL` 站必須附轉移目標」之外學到的第二種落空方式——**目標站是
`ALWAYS` 但已完成且在游標之前，一樣會無聲落空**。

**H8 的落實不照 AI 推薦**：AI 推薦 A（指派 `ut` 側判定），使用者選 D（本 intent
直接修）。依 `project.md` 的規則，選項會製造新正確性問題時須請其重選——本輪
判定**不構成**：D 的代價是協調成本（改 tina 正在改的模組），不是正確性問題，
且該代價已在選項原文逐字揭露。三種修法評估後選「移除 cli 模式」並已完成，含
突變驗證。詳見 RAID R-11。

**本站查出並處置的一項上游硬錯誤**：feasibility 的 [F10] 把遷移設計指派給
「`application-design` 或 `functional-design`」，但比對編譯後的 34 站清單，
**本工作流程不存在 `application-design` 這一站**。依 `units-generation:260822-ug-L2`，
這正是「指派指向不存在或可能被 skip 的站而無聲落空」的形狀。已由 [H3] 釘到
`domain-design`（2.6）。依 `team.md ## Corrections`，上游 artifact 不回改，
以本站的交接表向下游傳遞。

**本站訂定的轉移規則**：[H1]／[H3] 的目標 `domain-design`（2.6）與 [H4] 的
目標 `contract-design`（2.8）皆為 `CONDITIONAL`，非 ALWAYS。若該站在其執行
時被判定不適用而 skip，義務自動轉移——`domain-design` → `units-generation`
（2.7）、`contract-design` → `tcms-test-cases`（3.8，`execution: ALWAYS`）。
確認者是屆時執行該站的 conductor。

**[H4] 的取捨如實記載**：選項 C（`tcms-test-cases`）是四個選項中唯一
`execution: ALWAYS`、不可能被 skip 的落點，但它只偵測漂移、不預防；選項 A
（`contract-design`）是唯一能從結構上預防的，代價是 CONDITIONAL。此取捨已
在確認前向決策者完整揭露，決策者選 A。

**本站在階段邊界檢查中新增的一項指派（非問答產生）**：
`verification/phase-check-ideation.md` 的檢查 2 查出**能力 3（子功能各自開新
對話）、5（多意圖識別）、6（多輪對話）三項 Must 在三份 feasibility 產出中的
關鍵詞計數分別為 0、1、0**——沒有任何一列專門評估它們。三項都不引入新服務
或新技術層，風險型態是「需求寫不清楚」而非「做不出來」，故不阻擋進入
Inception；本站指派 `requirements-analysis`（2.3，`execution: ALWAYS`）為這
三項各自寫出可測的不變量，不得以「已隱含在能力 1／2 的需求裡」帶過。此項
列為 `initiative-brief.md` 交接表第 12 列。

---

## 已知會影響 Inception 的既存規則落差（非本 intent 造成）

如實記載，供下游不要把它們誤當成已有的護欄：

- `team.md ## Code Style` 的「Backend 依賴 100% 未 pin」敘述已過期（見 I-1）。
- `org.md` 宣告的「最低 80% line coverage」在本 repo **既無法量測也無法
  強制**（無 `.coveragerc`、無 coverage 工具、CI 無 coverage step）。
- `scripts/validate_repo_contract.py` 的 secret 掃描只讀 contract 檔，
  `backend/`、`frontend/`、`deploy/` 都不在其作用域內。

## Assumptions & Open Questions

- 本文件的決議內容取自各站問題檔的 `[Answer]` 與選項原文。凡標記「失效」
  者（Q6、Q11、F12）為其後被取代的決定，保留在表中是為了讓下游看得到取代
  關係，不得被當成現行決定引用 [assumption]
- 本文件不記錄各站的 `Consolidated Summary Confirmation` 與 approval gate
  的逐筆收據——那些在 `<record>/audit/` 的 per-clone shard 內，由引擎寫入 [assumption]
