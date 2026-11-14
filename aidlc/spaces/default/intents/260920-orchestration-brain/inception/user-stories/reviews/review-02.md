## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-product-lead-agent
**Iteration:** 1
**Date:** 2026-10-02T05:00:23Z

### 先說通過查證的部分（都是實測，不是印象）

引用定位這一輪幾乎全對，而定位是本專案最近才吃過苦頭的那一項。逐一開檔比對：
`user_router.py:85`＝`"H3": "MCP／Skill 生命週期"`、`:213`＝`_audit_append` 定義、
`:673`＝「系統必須保留至少一位可編輯使用者角色的管理員」、`:291-307`＝
`_hard_delete_user` 且確實不碰 `projects`；`schema_rbac.sql:330`＝
`owner_user_id INTEGER NOT NULL REFERENCES users (id)`（上游曾誤寫 `:328`，本檔已改對）、
`:64-65`＝`last_activity_at` 的 COMMENT；`design_agent.py:163`＝`queue.get_nowait()`；
`agent_router.py:125`＝`thread_id=f"user-{current_user.id}-design"`；
`wa_collab_orchestrator.py:79`＝`run_design_agent(messages, current_xml)`（確實不傳
`thread_id`）；`playwright.config.ts:17`＝`retries: process.env.CI ? 1 : 0`；
`AdminPage.tsx:104`＝`setTimeout(..., 4000)`、`:299-302`＝整塊純文字載入／錯誤態、
`:327-332`＝六個 `<th>`；品質 contribution 第 759 行確實逐字為「我指不出能讓它變紅的
突變」。`cost/advice_orchestrator.py:23-24` 亦精確命中 `_progress` dict ＋
`_progress_lock`（檔案實際在 `backend/cost/`，以 backend 為 import root 時路徑成立）。

機械事實也對：線框實算 **27** 個編號節、contribution 編號發現實算 **47**（18／13／16）、
處置表實算 **47 列且無一列空白**、`traceability.json` 100 筆 upstream_ids 對 100 列
coverage 且所有 target 都指向存在的 `US`／`AC`、`requirements.md` 的 89 個 FR 識別字與
upstream_ids 完全互相覆蓋（雙向零差集）、`backend/` 對 `mcp` 僅 1 處命中、
`project_members` 全 repo 零程式命中。`personas.md` 的 `P-4` 第二面（D-01）是乾淨的
落點，`AC12.4.4`「換一台裝置」確實擋掉 `localStorage` 實作，`AC13.1.1` 的「且各自非空」
確實是擋住真空成立的那一半 —— 這幾項是本輪最好的工作。

問題在別處：**最核心的那個新實體，它的寫入端與清除端一條 AC 都沒有**；而三處 hard
constraint 判定與剛核可的 `requirements.md` 直接對撞。

### Findings

| ID | Severity | Location | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `stories.md` US12（§US12.1–US12.5，行 733–886） | **`project_members` 的「誰寫（非建立者）」與「誰清」兩腿零 AC，而 US12 有九條 AC 的 Given 依賴它們。** 逐條核對 15 條 US12 AC：`AC12.1.2` 只斷言「邀請動作**可用**」，`AC12.5.1`／`AC12.5.3` 斷言邀請**被拒**與拒絕不留列，**沒有任何一條斷言成功邀請後該人出現在成員清單且角色正確**——而那正是已核可 `user-flow.md` Flow 8 第 3 步（搜尋使用者 → 選角色 → 送出）與線框 §24 的主路徑。成功「移出專案」同樣零 AC，只有 `AC12.3.2`（最後一位時被拒）。後果不是美觀問題：`AC12.2.1`（Given「一位一般成員」）、`AC12.2.2`、`AC12.2.3`、`AC12.2.4`（Given「另一位成員」）、`AC12.3.1`、`AC12.3.2`、`AC12.4.1`／`.2`／`.3`（Given「該專案另有成員」）全部預設了第二位成員存在，而本檔與 `requirements.md` 都沒有任何條文或 AC 產生他。`requirements.md` 的 FR12.0–FR12.6b 亦無「成功邀請」與「移出成員」的 FR（`邀請` 在全檔僅 FR12.6a 的拒絕條款命中）。本檔自述跑過契約端點三問，但在 `project_members` 上只跑了建立者那一腿（`[V-09]` 註記），**「其他成員怎麼進來」與「誰把他移掉」兩問沒問** | 補一則（或兩條 AC）涵蓋成功邀請：Given 一位具備對應全域權限的使用者，When 我以成員頁邀請他並指定角色，Then 成員清單新增一列且角色為我指定的那個；再補成功移出的 AC（非最後一位時移出成功且清單少一列）。同時把兩者缺少 FR 這件事依既有形狀標為「本站查出的上游缺口」回報，與 FR12.0 同一處置 | New |
| R-02 | Major | `stories.md` 行 1094–1108「修訂 1 的 ADR-0006 四面向」表，encryption 列 | **判定欄寫「不成立（無新敏感欄位）」，而已核可的 `requirements.md:606` 逐字寫「**適用（新增一處）**」，同檔 `:611` 更逐字寫「**四面向皆適用，無不適用項。**」** 同一格的內文又自己承認「唯一的張力在 MCP 的憑證路徑：`C-T11` 禁止把使用者 token 當成工具引數傳遞……處置為 `AC11.4.2` ＋ 共同 DoD 的白名單斷言」——有張力、有處置，卻判「不成立」，判定欄與內文自相矛盾。看得出來源是 `scope-document.md:75` 的 encryption「不適用」，但那一格的宣告範圍只有**能力 12**，本表的宣告範圍是 FR11＋FR12＋FR13 三組。`project.md` 要求這張表存在的理由正是「讓『是否漏項』成為可一眼核對的事實」，一個與上游相反的「不成立」把這道檢查反過來用 | 把判定改為「適用（一處：`FR11.5`／`C-T11` 的 MCP token 通道）」，並在理由欄註明「能力 12 自身無新敏感欄位（承 `scope-document` 的能力 12 判定），適用性來自能力 11」 | New |
| R-03 | Major | `stories.md` 行 1094–1108 同表，network exposure 列 | **把 MCP server 寫成「本 intent 新增的**唯一對外介面**」，並寫「本站不預選傳輸或認證手段」——兩句都與已核可上游相反。** `requirements.md:607` 逐字：「**MCP server 是本 intent 的第二個新增進程邊界（第一個是 Redis）**。它**不得對外暴露**，僅供同主機的大腦進程連接。」即（a）不是「唯一」，Redis 才是第一個；（b）上游已經鎖了「不得對外暴露／僅同主機」，而本檔把它描述成「對外介面」並宣告本站不預選認證手段，等於把一條已核可的網路暴露面約束從下游視野裡拿掉。下游若只讀 `stories.md`（delivery-planning 與 functional-design 都會讀）會得到相反的邊界 | 改寫該格：MCP server 為本 intent 的第二個新增進程邊界，**不得對外暴露、僅供同主機連接**（承 `requirements.md:607`）；本站不預選的只有傳輸形式（`OQ-16`）與認證機制（`OQ-15`），不包含暴露範圍 | New |
| R-04 | Major | `stories.md` AC12.4.3（行 826）與其註記 vs `requirements.md` FR12.4c（行 310） | **`[D-17]` 這個 Critical 只修了一半。** 本檔把落點由入口頁改為落地頁並寫明理由，但 `requirements.md` 的 `FR12.4c` 仍逐字為「新任管理者**下次進入產品時**，在**入口頁頂部**看到一則橫幅」，且全檔 `落地頁` 零命中（我已 grep 複驗）。FR 才是 `functional-design`／`code-generation` 讀的需求來源，照它實作就會重新引入 D-17 指出的那個 Critical（只有 `C1 view` 的合法成員被授予 `project_admin` 而永遠看不到通知）。本輪已把 **5 項**就地更正推進 `requirements.md`（FR12.0、FR12.5b、FR12.5c…），獨漏這一項——而這一項改的是行為落點，比其中幾項更實質 | 比照 FR12.0／FR12.5c 的形狀，在 `requirements.md` 的 FR12.4c 就地加一段「**2026-10-02 更正（user-stories 的 `[D-17]`）**：落點由入口頁改為使用者的落地頁，理由為 FR1.8／Flow 4 的 `DefaultRedirect`」，並在本檔註記交叉指向該更正 | New |
| R-05 | Major | `stories.md` AC12.2.4（行 777）vs `contributions/aidlc-quality-agent.md` 行 760 | **新補的 `AC12.2.4` 正是品質 agent 當場警告為「接近恆真」的那個形狀，而那條警告沒進處置表。** 它逐字寫：「`FR12.3`「可同時有多位 admin」｜突變＝加一條「至多一位」的限制。但若實作從未加過這種限制，這條 AC 驗的是「沒有某個不存在的限制」——**接近恆真**。建議改寫為可觸發的形式：「指定第二位 admin 後，**兩位都能執行** admin 動作」，突變＝讓第二位的指定靜默覆寫第一位」。本檔的 `AC12.2.4` 的 Then 逐字為「兩人**同時**都是專案管理者——角色不互斥、不發生替換」，就是它說會恆真的那一版。本檔第 787–792 行自己寫下「**沒有編號的觀察不會進處置表**」並據此救回第 759 行那條，卻漏了**緊鄰的下一行**，而這一行針對的恰好是本輪新建的 AC | 照該 agent 給的形式改寫 `AC12.2.4`：Given 我已把第二位成員改為專案管理者，When **他**在該專案執行一項僅管理者可做的動作（例如改第三人的角色），Then 該動作成功——使「靜默替換第一位」成為可觸發的紅燈 | New |
| R-06 | Major | `stories.md` 行 969（`D-02` 處置列）vs AC12.4.1（行 824） | **處置自述與 artifact 不符。** 表格逐字寫「US12.4 的 Given 指名「某專案的 owner 帳號**被停用**」，即指名造成它的動作與**行為者**（`[P-4]`）」。實際 `AC12.4.1` 的 Given 逐字為「某專案的 owner 帳號**被停用**且該專案另有成員」——純被動語態，沒有行為者；全檔 `P-4` 僅 6 處命中（行 86、230、261、742、803、1126），**US12.4 整則零命中**。而 `D-02`（Major）要求的正是「Given 必須把前置動作寫進去、以**另一個 actor** 的既成事實形式表達，不能寫成被動語態（會讓實作者不知道誰觸發）」，並附了現成文字「已被平台管理者停用」。這正是 `project.md` 點名的「選擇性整合在產出上看不出來」——只有把處置表當 checklist 逐列開檔才看得到 | 把 `AC12.4.1` 的 Given 改為「某專案的 owner 帳號**已被系統管理者 `[P-4]` 停用**且該專案另有成員」；`AC12.4.3` 的 Given 同形 | New |
| R-07 | Major | `stories.md` 行 1148–1156、行 1202–1208、行 1076 | **三處自稱腳本輸出的計數都錯，而且錯因可定位。** 實算（`^### US\d+\.\d+` 取 30 則；以 `^\|\s*\*\*AC…\*\*\s*\|` 取表列定義、按故事分組去重）為 **103 條 AC**，分佈 **3 條×19、4 條×9、5 條×2**；本檔寫「102 條」與「3 條 × 20 則、4 條 × 8 則、5 條 × 2 則」。差異可精確定位：若把追溯自檢最後補入的 `AC12.2.4` 排除，US12.2 退回 3 條，得到的正是 102 與 3×20／4×8——**收尾計數是在最後一條 AC 加入之前跑的，加完沒有重跑**。另行 1076 寫「逐條比對 `requirements.md` 的 **29 個** FR11／FR12／FR13 識別字」，實為 **27**（`traceability.json` 自己的 note 寫 FR11「6 條」＋FR12「17 條」＋FR13「4 條」；含三個群組 id 才是 30，29 不對應任何分法）。這是同一份檔在同一條規則上第三次（`review-01` 的 `R-10` 已指出「十則」實為十一則） | 重跑一次並以同一支腳本同時輸出三處數字；把「3–6 條指引」那句的依據改成輸出檔而非行內數字，避免下次再脫鉤 | New |
| R-08 | Major | `traceability.json` FR13.4 列 vs `stories.md` 行 927–931 與兩份 contribution | **同一站的兩份產出對 FR13.4 說相反的話，而機械可讀的那一份說的是錯的。** `traceability.json` 把 FR13.4 記為 `status: "Deferred"`，note 逐字「需求本文逐字寫「待查，非本輪斷言」——**本輪未獨立複驗** `wa_collab_orchestrator.py:79` 是否使 A4 共編使用者共用同一 checkpointer thread」。但 `stories.md` 逐字寫「**`[V-03]`／`[Q-09]` 證實 `FR13.4` 為真且是獨立缺陷**」，`aidlc-developer-agent.md:154` 的標題逐字「FR13.4 **證實為真**」並附三處逐行實讀證據，`aidlc-quality-agent.md:422` 逐字「另外 FR13.4 我已複驗為真」、`:240` 逐字「我已複驗」。下游（`units-generation`／`delivery-planning`）機械讀 JSON 時會把一個**已實測確認的獨立缺陷**讀成未查證的待查項，而它正是 US13 DoD 的第二個修復對象 | 把 FR13.4 改為 `OK`（target 為 US13 的 Definition of Done），note 改寫為「需求本文原記「待查」，本輪 mob 由開發與品質兩位**獨立複驗為真**（`V-03`／`Q-09`），已列入 US13 DoD 的修復範圍」 | New |
| R-09 | Major | `stories.md` AC11.2.2（行 690） | **這條 AC 的 When 在本 intent 沒有任何觸發面，任何層都驗不出。** 逐字為「**Given** 欄位按 agent 分組，**When** **新增一個 agent**，**Then** 畫面多一組，組內欄位固定」。「新增一個 agent」不是使用者動作也不是測試可執行的操作——本 intent 沒有 agent 註冊畫面或端點（`FR11.2` 只說「組內固定、**可隨新 agent 增組**」，那是一條結構性質而非行為）。品質 agent 把 FR11.2 的可驗證層判為「Playwright e2e（唯一）」，而 e2e 無法新增一個 agent。它既不是可構造的 Given／When，也不會因實作錯誤而紅燈。本檔跑了可達性自檢並誠實記下 `AC12.4.2`（時間戳相同不可構造）與 `US11.4`（零 MCP 基礎設施）兩處，漏了這一處 | 改寫為可觀察行為：Given 需求籤有 N 個 agent 分組，When 我檢視它，Then 每一組的標題為該 agent 名稱、組內欄位集合與該 agent 的宣告一致（錯綁欄位到別組即紅燈）；「可隨新 agent 增組」屬擴充性，移進 DoD | New |
| R-10 | Major | `stories.md` 行 981（`D-15`）、行 973（`D-10`）、行 1022（`Q-13`）與 Assumptions 對應三條 | **三處轉移目標往回指到一個已完成的站，且其中一處的 OQ 交叉引用指錯題。** `aidlc-state.md:162` 的 `Last Completed Stage` 就是 `requirements-analysis`、`:156` 的 `Current Stage` 是 `user-stories`——`D-15`／`D-10`／`Q-13` 全部寫「轉 `requirements-analysis`（**ALWAYS**）」，是往游標之前指的死指派，正是 `project.md` 記過的同形（「`[H6]` 的目標站是 ALWAYS 但已完成且在游標之前」）。另 `D-15` 兩處（處置表與 Assumptions）寫「與 **OQ-18**（需求欄位的誰清）同一落點」——`requirements.md:787` 的 OQ-18 實為「FR12.6b 的入職順序約束是否可接受」，承接站欄逐字「**無承接站——刻意如此**……上線後覆核（非 stage）」。既不是需求欄位的誰清，也沒有任何 stage 落點，所以「同一落點」是假的，而這條缺口因此在交接表上看起來有人接、實際沒有 | 把三處的轉移目標改成游標之後的 `ALWAYS` 站（`code-generation` 3.5 是本工作流程上第一個保證會跑的）；`D-15` 的 OQ 交叉引用改為新開一個 OQ（或指向 `OQ-14`，`projects`／`systems` 的讀寫刪角色集合），不要指向 OQ-18 | New |
| R-11 | Minor | `stories.md` AC11.4.2（行 715） | Then 逐字「其中**不含**任何承載憑證的欄位」，把上游 `FR11.5` 已經寫好的可機械判定形式稀釋掉了：`requirements.md:265-269` 逐字給出「其 properties 不含任何名稱匹配 `token`／`key`／`secret`／`authorization`（**不分大小寫**）的欄位」。「承載憑證的欄位」不是可二元判定的集合，QA 無從判斷某個欄位算不算。這與本檔作者自己在上一站落盤的規則（措辭不得被稀釋）同形 | 把上游的匹配清單逐字搬進 AC 的 Then；白名單版本（DoD 已有）可一併寫成第二句 | New |
| R-12 | Minor | `stories.md` 行 1026–1040「處置型態統計（實算）」 | 表自稱「（實算）」且合計恰為 47，但 47 項處置不構成單桶分割：以關鍵詞掃 47 列，提及 `DoD` 的有 **16** 列（表寫 9）、提及某條 `AC` 的有 **16** 列（表寫 14），且至少 9 項明顯同時落在兩桶以上（`D-06` AC＋DoD、`V-07` AC＋DoD、`V-11` AC＋DoD、`V-12` AC＋DoD、`Q-05` AC＋DoD、`D-10` DoD＋Assumption＋回報、`V-08` DoD＋requirements 更正、`Q-02` DoD＋回報、`Q-10` Assumption＋requirements 更正）。合計 47 是靠強制單桶得到的，不是算出來的——而相鄰的 R-07 顯示本檔的「實算」標籤本身已不可靠 | 改成「主要落點（單桶）」並加一欄「次要落點」，或直接移除合計欄，只保留「47 列皆有落點、無空白」這個真的實算得到的事實 | New |
| R-13 | Minor | `traceability.json` FR12.4a 列 | `target` 為 `"US12.4, US13.1"`，但 `US13.1` 是併發事件隔離，與自動改選的挑選決定性無關；`stories.md` 全檔 `[FR12.4a]` 僅一處命中（`AC12.4.2`，行 825），US13 群無任何 FR12.4a 標籤。下游以 traceability 做單元↔故事對映時會多出一條假邊 | 把 target 改為 `"US12.4"` | New |
| R-14 | Minor | `stories.md` AC4.3.1（行 266） | `review-01` 的 `R-07` 指出的懸空前指標仍在：Given 逐字「某筆記憶的可見範圍被放寬過（**該操作的觸發面見下方註**）」，而全檔 `觸發面` 只有這一處命中（我已 grep 複驗），那個註不存在。revision 1 動過 US4.3 這一節（27 格線框的更正就寫在它裡面），所以不是沒機會修 | 補上該註（說明放寬可見範圍的觸發面由 `OQ-12` 定、本 intent 無畫面），或刪掉括號內的前指標並把缺口寫進 Assumptions | Unresolved |
| R-15 | Minor | `stories.md` 行 417–418 | `review-01` 的 `R-09` 仍在：第 417 行是空白行，把 US9.1 的表切成「有表頭的三列」＋「第 418 行的孤列 `AC9.1.4`」。多數 Markdown 算繪器會讓 `AC9.1.4` 脫離 `AC` ／ `Given / When / Then` 欄標題，而它正是本檔最強的那條不變量（`system_id IS NULL` 列數須為 0 且必須大聲失敗） | 刪掉第 417 行的空白行 | Unresolved |
| R-16 | Minor | `traceability.json` FR9.4 列 | `review-01` 的 `R-08` 仍在：`status: "OK", target: "US9.1"`，而 `stories.md` 行 445 自己寫 FR9.4「在本群**刻意無 AC**：它是一個明確的範圍排除項」，全檔亦無 `[FR9.4]` 標籤。同類的 `NFR9` 誠實記為 `N/A` 並附完整理由，FR9.4 卻記 OK，高報了一則故事滿足它 | 改為 `N/A` 並比照 NFR9 附理由 | Unresolved |

### Summary

**分類計數**：修訂 1 新引入 **9** 項（R-01、R-02、R-03、R-05、R-06、R-07、R-08、R-09、R-12）；
既存且上一輪未審到或已審未修 **4** 項（R-14、R-15、R-16 為 `review-01` 原樣殘留，
R-13 為既有 traceability 列）；新的設計問題 **3** 項（R-04 的上下游落點分歧、
R-10 的死指派、R-11 的措辭稀釋）。一項 Critical、九項 Major，遠超 READY 門檻。

**哪些需要獨立視角、哪些是自檢該抓到的**：我只有兩項算得上需要外部視角。
一是 **R-01**——它要把 15 條 AC 攤開，逐條問「這個 Given 由誰產生」，再回去對
`user-flow.md` Flow 8 第 3 步，才看得出主路徑零覆蓋；本檔的契約端點三問只對
`FR12.4c-i` 與 `FR13.1` 的「誰清」跑了，沒有對 `project_members` 的成員列跑，而那
正是 `project.md` 已經記過一次的教訓（「寫入端是三問中最容易漏的一問」）。二是
**R-05**——它要讀 contribution 第 760 行，而該行緊貼作者自己救回來的第 759 行。

**其餘七項都是作者自己的機械自檢應該攔下的**，所以「七項自檢抓到 11 個自己的問題」
這個自述只能算部分成立：自檢確實抓到真東西（四則低於 AC 指引、`FR12.3`／`FR12.4a`
的追溯落空、`FR12.4c-i` 與 `FR13.1` 的誰清、`AC12.4.2` 的不可構造 Given、第 759 行的
假標籤——這些沒有一項是我找到的，而且好幾項品質很高），但同一批自檢在它們各自宣稱
覆蓋的面上漏了：自檢 6（可算的先算）漏了 R-07 的三處計數，而且錯因是「加完最後一條
AC 沒重跑」，與 `review-01` 的 `R-10` 同形；自檢 1（可達性）漏了 R-09；自檢 3（引用
逐字核對）漏了 R-06 的自述不符與 R-10 的 OQ-18 指錯題；自檢 5（跨檔傳播）漏了 R-08
的 `traceability.json` 與 `stories.md` 對 FR13.4 互相矛盾、以及 R-04 的 FR12.4c 沒同步；
新加的自檢 7（hard constraint 逐項）本身產出了 R-02 與 R-03 —— 這一項不是漏跑，是
**跑出了與已核可上游相反的判定**，比沒跑更麻煩，因為表格的存在會讓下一個人以為查過了。

**我實測到什麼深度**：引用定位全部開檔核對（12 處程式行號、2 處 schema、1 處
contribution 行號，全中）；AC 與故事計數、線框節數、contribution 發現數、處置表列數、
traceability 的 100↔100 與 target 懸空、`requirements.md` 的 89 個 FR 雙向覆蓋，皆以
腳本實算；`mcp`／`project_members`／`落地頁`／`觸發面` 以 grep 複驗；47 列處置逐列
掃過並對 D-01／D-02／D-03／D-04／D-05／D-06／D-12／D-15／D-17／V-03／V-09／V-11／
V-12／Q-05／Q-09／Q-11／Q-13 開檔核對落點。**我沒有做到的**：US1–US10 的 AC 內容未
重新逐條審（依指派只在修訂 1 動過的 US4.3 一節複查）；`accessibility-checklist.md`
與 `ux-guide.md` 的原文未開（D-08／D-10／D-11／D-13 的事實基礎我採信 contribution 的
逐字引用，只核對了它們在本檔有落點）；`estimate_readers.py`／`parse_number`
（Q-03／Q-04）未自行實測，它們已由使用者裁決移出本站。
