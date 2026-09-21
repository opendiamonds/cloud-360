# Intent Capture — 問題檔

本檔為 `intent-capture` 階段的正式決策紀錄。所有 `[Answer]:` 由使用者填答，
AI 不得代答。回答格式為選項字母（可複選者以逗號分隔），或 `X` 並附文字說明。

## Sources

- [desc] Initial description: "做一個統一入口的大腦，用來編排其他子功能agent，框架請用langgraph，在local開發可以用claude code，在server上用openrouter的gemini flash 3.7，這個大腦要有session層，紀錄session重要資訊，用redis，例如存儲該對話識別意圖後的cloud-360中的專案、系統或是系統架構id，Cloud-360是一個專案有多個系統，一個系統可以有一個drawio，多個sheet的架構圖，但也有該自己的成本，跨雲分析（by專案），用來識別目前在改動的對象是誰，他可以編排不同工作給不同的功能agent，例如管理及畫架構圖的架構設計agent，或者是管理成本及FinOps的agent等，在不同頁面功能都是共享context，可以自動切換，另外也有長短期記憶，semantic memory、procedure memory(working plan design)、Episodic memory(by user)等，使用postgresdb，除了入口頁的大腦，每個功能頁面都會共享session，也可以在每個子頁面去new session，實踐多意圖識別、多輪對話、主動通知推播，並利用streaming架構，做到快速回覆"
- [scope] Workflow-selected scope: `agent-orchestration-brain`.
- [memory:M1] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "✅ **In scope**：SRS、architecture diagrams、user stories、ADRs、IaC generator design、agent routing design、MCP/skill management spec、validation scripts、baseline CI、自有 staging 的部署與維運。"
- [memory:M2] `aidlc/spaces/default/memory/project.md#Scope Overrides`: "❌ **Out of scope（除非經新 ADR 核可）**：雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app。"
- [memory:M3] `aidlc/spaces/default/memory/project.md#Decided`: "DECIDED: 專案定位為 AI-native multi-cloud architecture & operations platform，方法論基礎為 Spec-Driven Development（SRS、user stories、architecture、ADRs）。(ADR-0001)"

## 查證紀錄（非來源，不得作為 artifact 的依據）

出題前對 repo 現況做的唯讀查證，只用於讓題目與選項貼合事實。這些**不是**
來源，不得被引用進 `intent-statement.md` 或 `stakeholder-map.md`；任何需要
進入產出的事實，必須經由下列 `[Q<n>]` 的作答確認。

- V1 — **「專案 → 系統 → 架構圖」階層在資料庫中不存在**。`schema_rbac.sql`
  目前的實體為 `users`、`user_diagrams`、`diagram_shares`、
  `user_diagram_chats`、`architecture_reviews`、`wa_lenses`、
  `role_permissions`。`user_diagrams` 的欄位只有
  `id / user_id / title / xml_data / updated_at`，直接掛在使用者底下，沒有
  專案或系統的中介層。backend 全樹中 `system_id` 命中 0 次。
- V2 — **成本／FinOps 能力不存在**。`FinOps_Analyst` 只是 `database.py`
  的一個 RBAC 角色種子與測試對象，沒有任何成本資料表、成本服務或
  FinOps 模組；`wa_lens_engine` 中的 `cost_storage` 是 Well-Architected
  檢視的欄位名，不是成本數據。
- V3 — **既有前端頁面**（`frontend/src/App.tsx`）：`/login`、`/403`、
  `/waiting-approval`、`/workspace`、`/assessment`、`/admin/users`、
  `/admin/authorization-requests`、`/admin/role-permissions`，
  以及 `/` 導向。沒有入口頁（大腦頁）。
- V4 — **既有的 LLM 路徑已具雙模式**。`backend/services/llm_provider.py`
  以 `claude-agent-sdk` 啟動 `claude` CLI 子行程，並可在 `openrouter`
  （設定 `ANTHROPIC_BASE_URL`／`ANTHROPIC_AUTH_TOKEN`）與 `cli`
  （本機 `claude login`）兩種模式間切換，預設 `openrouter`。
- V5 — **既有 agent 端點**：`agent_router.py` 提供 `POST /generate` 與
  `POST /generate-wa-collab`，具備拒答用的 SSE 回應與 `prompt_guard`
  前置檢查。既有的 agent 類模組為 `design_agent.py`、`review_agent.py`、
  `review_orchestrator.py`、`wa_collab_orchestrator.py`。
- V6 — repo 內 **Redis 與 LangGraph 的引用為 0**（由編排階段的掃描確認）。

## 選項收斂說明

初版問題檔每題為 A–E（5 個語意選項）＋ X。提問介面每題上限為 4 個選項，
依 `project.md` 的 `requirements-analysis:260822-ra-c2`（問題檔本身須先收斂
成 4 個並記明合併方式，不得提問時臨時換一組），本檔已改為每題 A–D ＋ X。
逐題合併方式如下，供下游與 reviewer 複驗：

- **Q1**：原 D「以上皆是」刪除，改以**複選**承接（可答 `A, B, C`）。
- **Q2**：原 E「以上多者皆是」刪除，改以**複選**承接；「尚未定義」由 X 承接。
- **Q3**：原 D「減少手動切換次數」併入 B，B 的定義擴為「跨頁面上下文保留率
  （含完成一個跨功能任務所需的頁面切換次數下降）」；原 E 成為新 D。
- **Q4**：原 D「外部驅動」刪除，改由 X 承接（題幹已點明此可能）；原 E 併入
  新 D，成為「沒有特定觸發點／尚未定義」。
- **Q5**：原 D「階層由其他工作先行建立」併入 C，C 的定義擴為「先以抽象的
  作業對象設計，階層由後續 intent 或其他工作補上」；原 E 成為新 D。
- **Q6**：原 D「只做大腦本身、不接任何功能 agent」刪除，改由 X 承接
  （題幹已點明此可能）；原 E 成為新 D。
- **Q7**：原 D「依功能於設計階段逐頁決定」與原 E「尚未定義」合併為新 D。
- **Q8**：原 C「有共同決策者」與原 D「有外部利害關係人」合併為新 C；
  原 E 成為新 D。
- **Q9**：原 B「產品邊界要縮小」與原 C「要擴大」合併為新 B（以 X 說明方向）；
  原 D 成為新 C，原 E 成為新 D。

---

## Q1. 這個統一入口大腦要解決的核心問題是什麼？（可複選）

Cloud-360 目前的 LLM 能力散在各頁面各自的端點上（V5）。這個大腦要收斂的
是哪一種痛？此題決定整份需求的主軸，其餘題目都會被它框住。

- A. **使用者要自己決定用哪個功能**：想做的事跨多個頁面時，使用者得先知道
  該去哪一頁、該找哪個功能，系統沒有一個「說出需求就會被帶到對的地方」的入口。
- B. **上下文在頁面之間斷掉**：在某一頁講過的對象與意圖，換頁後要重講一次，
  對話與工作狀態不連續。
- C. **AI 能力無法組合**：一個需求需要多個功能接力（例如先改架構圖再看成本）
  時，沒有東西能把它拆成幾件工作並分派出去。
- D. 尚未定義／想先探索再定調。
- X. Other（請說明）

[Answer]: A, B, C  <!-- 2026-09-20T17:42:20Z | Mode: guided -->

## Q2. 這個大腦的主要使用者是誰？他們現在實際卡在哪裡？（可複選）

- A. **架構設計者**（在 `/workspace` 畫圖、改圖的人）：需求從對話變成圖的
  過程要反覆切換工具與頁面。
- B. **評估／稽核者**（使用 `/assessment` 的 Well-Architected 檢視者）：
  看完檢視結果後，要自己把發現帶回架構圖或成本討論。
- C. **成本／FinOps 關注者**：想問「這個系統花多少、跨雲怎麼比」，但目前
  系統沒有這個能力（V2）。
- D. **管理者／平台維運者**（`/admin/*`）：關心誰在改什麼、有沒有紀錄。
- X. Other（請說明；包含「尚未定義」）

[Answer]: A, B, C, D  <!-- 2026-09-20T17:42:20Z | Mode: guided -->

## Q3. 成功長什麼樣子？要用什麼可量測的結果判斷這件事做對了？（可複選）

`phases/ideation.md` 要求成功指標必須可量測，不得是「體驗更好」這類無法
驗證的敘述。請選出**第一版**要證明的那一個（或兩個）。

- A. **意圖識別準確率**：使用者在入口說一句話，系統選對功能 agent 的比例
  達到某個門檻（門檻值於後續階段定案）。
- B. **跨頁面上下文保留率**：切換頁面後，系統仍正確指向同一個作業對象
  （不需要使用者重講）的比例；一併涵蓋「完成一個跨功能任務所需的頁面切換
  次數下降」。
- C. **首字回應時間**：串流架構下，從送出到畫面出現第一個字的時間低於某個
  秒數（值於後續階段定案）。
- D. 尚未定義——先做出可用的版本，指標下一輪再定。
- X. Other（請說明）

[Answer]: A, B, C  <!-- 2026-09-20T17:42:20Z | Mode: guided -->

## Q4. 為什麼是現在做這件事？

若觸發點是外部驅動（展示、稽核要求、使用者反饋等），請用 X 說明來源。

- A. **既有 agent 路徑已到極限**：`/generate` 與 `/generate-wa-collab`
  是兩個彼此獨立的端點（V5），再加功能就會變成第三、第四個孤島。
- B. **要先有大腦，後續功能才有地方掛**：成本／FinOps 等尚未存在的能力
  （V2）需要一個統一的編排層才值得開工。
- C. **技術條件成熟**：既有的 LLM 供應商切換層已經可用（V4），現在接編排
  框架的成本比以前低。
- D. 沒有特定觸發點／尚未定義——是既定規劃的下一步。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-20T17:42:20Z | Mode: guided -->

## Q5. 「識別目前在改動的對象是誰」要綁定到哪一層？

這是本階段最關鍵的一題。描述中寫的是「Cloud-360 是一個專案有多個系統，
一個系統可以有一個 drawio、多個 sheet 的架構圖，也有自己的成本與跨雲分析」，
但**這個階層目前在系統中不存在**（V1）：資料庫只有「使用者 → 架構圖」，
沒有專案，也沒有系統。你的選擇會決定這個 intent 的大小。

- A. **只綁既有的架構圖**：大腦記住「現在在處理哪一張架構圖」，專案與系統
  階層留給未來。範圍最小，能最快看到端到端跑通。
- B. **本次一併建立專案／系統階層**：把「專案 → 系統 → 架構圖」做成正式
  資料模型，大腦綁到這三層。範圍顯著變大，會動到資料庫結構與既有頁面。
- C. **大腦先以抽象的「作業對象」設計**：現在只定義介面與記錄方式，不承諾
  具體階層，等階層由後續 intent 或其他工作落地再接上。
- D. 尚未定義——需要先討論再決定。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-20T17:49:16Z | Mode: guided -->

## Q6. 第一版要讓大腦編排哪些功能 agent？

描述點名了「架構設計 agent」與「成本及 FinOps agent」。事實是：架構設計
相關的能力已經存在（`design_agent.py`、`review_agent.py`、
`wa_collab_orchestrator.py`，V5），**但成本／FinOps 能力完全不存在**
（V2，`FinOps_Analyst` 只是一個角色名）。若第一版只做大腦本身、不接任何
功能 agent（純意圖識別與 session／記憶層），請用 X 說明。

- A. **只編排既有能力**：架構圖生成、Well-Architected 檢視、協作建議。
  成本 agent 留到它真的存在之後。
- B. **既有能力 ＋ 新建成本／FinOps agent**：本 intent 同時要做出成本能力，
  包含它的資料從哪來。
- C. **既有能力 ＋ 成本 agent 的空殼**：先定義成本 agent 的介面與交接方式，
  但不實作真正的成本計算。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: C  <!-- 2026-09-20T17:49:16Z | Mode: guided -->

## Q7. 「每個功能頁面都會共享 session」涵蓋哪些頁面？

既有頁面為 `/workspace`、`/assessment`、`/admin/users`、
`/admin/authorization-requests`、`/admin/role-permissions`，以及登入、
待審、403 等（V3）；目前**沒有**入口頁。

- A. **只有入口頁 ＋ `/workspace` ＋ `/assessment`**：實際會用到 AI 的頁面。
- B. **全部已登入後的頁面**（含 `/admin/*`）。
- C. **入口頁 ＋ `/workspace`**：第一版只打通這一條路徑。
- D. 尚未定義——共享範圍依功能而定，於設計階段逐頁決定。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-20T17:49:16Z | Mode: guided -->

## Q8. 關鍵關係人、決策者與溝通需求為何？

- A. **單一決策者（你），無其他關係人**：範圍、優先順序、驗收皆由你決定，
  不需要對外回報節奏。
- B. **單一決策者，但有需要被告知的對象**（請在 X 說明是誰、要知道什麼）。
- C. **有共同決策者或外部利害關係人**（客戶、稽核、管理層等；請在 X 說明
  是誰、哪些決定需要他們同意）。
- D. 尚未定義。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-20T17:49:16Z | Mode: guided -->

## Q9. 這個工作計畫的範圍是否符合你設想的產品邊界？

本工作流以 `[scope]` 的 `agent-orchestration-brain` 啟動（28 站執行、
6 站跳過、25 道核可關卡）。另需注意 [memory:M2] 已把雲端供應商 production
環境與 production credentials 排除在 repo 範圍外；[memory:M1] 的 in-scope
清單則涵蓋 architecture diagrams 與 agent routing design。

- A. **確認**：沿用這個工作計畫，產品邊界就是我描述的那些能力。
- B. **確認工作計畫，但產品邊界要調整**（縮小或擴大；請在 X 說明方向與內容，
  並理解擴大可能需要回頭調整計畫）。
- C. **工作計畫本身要改**（站別增減；請在 X 說明）。
- D. 尚未定義——需要先看到前面幾題的結果再判斷。
- X. Other（請說明）

[Answer]: A  <!-- 2026-09-20T17:55:05Z | Mode: guided -->

## Q10. 「管理者／平台維運者」是第一版的服務對象，但管理頁面不在共享範圍內——哪一個才是你要的？

偵測到跨題不一致，需當場定錨。Q2 把**管理者／平台維運者**（`/admin/*`，
關心誰在改什麼、有沒有紀錄）列為主要使用者之一；Q7 卻把共享 session 的範圍
定為**入口頁 ＋ `/workspace` ＋ `/assessment`**，不含 `/admin/*`。兩者並存時，
這個角色在第一版拿不到大腦提供的任何東西。

- A. **管理者不是第一版的服務對象**：Q2 的 D 改為「未來的服務對象」，
  第一版不為他們設計任何能力。共享範圍維持 Q7 的答案。
- B. **把 `/admin/*` 納入共享範圍**：修正 Q7，管理頁面也共享 session。
  代價：管理頁目前沒有任何 AI 互動，納入等於要為它們設計新的互動。
- C. **管理者的需求由別的途徑滿足**：他們要的是「誰改了什麼」的紀錄，
  由長期記憶（episodic memory）或既有稽核紀錄提供，不需要共享 session。
- D. 尚未定義——需要先討論再決定。
- X. Other（請說明）

[Answer]: C  <!-- 2026-09-20T17:55:05Z | Mode: guided -->

## Q11. 「成本／FinOps 關注者」是第一版的服務對象，但成本能力只做空殼——第一版要交給他們什麼？

偵測到跨題不一致，需當場定錨。Q2 把**成本／FinOps 關注者**列為主要使用者，
其痛點逐字為「想問這個系統花多少、跨雲怎麼比」；Q6 卻選了**只做成本 agent
的空殼**（定義介面但不實作成本計算）。兩者並存時，這個角色在第一版問不到
任何成本答案。

- A. **第一版明確不服務這個角色**：空殼只是為了驗證編排層的抽象夠不夠通用，
  成本能力留待後續 intent。Q2 的 C 改為「未來的服務對象」。
- B. **空殼要能回「我還不知道」**：大腦能正確把成本問題**路由**到成本 agent，
  由它回覆一個明確的「尚未提供」而非答錯或沉默。這本身就是可驗證的行為。
- C. **改為實作最小成本能力**：修正 Q6，第一版要能回答至少一種真實成本問題
  （資料來源待定）。代價：範圍顯著變大。
- D. 尚未定義——需要先討論再決定。
- X. Other（請說明）

[Answer]: B  <!-- 2026-09-20T17:55:05Z | Mode: guided -->


## Consolidated Summary Confirmation

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct

## Assumption Confirmation

兩份產出的 `## Assumptions & Open Questions` 共列出 6 項未確認事項。請選擇
處置方式。

`intent-statement.md`：

1. 三項成功指標的**具體門檻值**（意圖識別準確率的百分比、首字回應時間的
   秒數、上下文保留率的百分比）尚未定案，留待後續階段決定。
2. 使用者的原始描述提到「跨雲分析（by 專案）」是專案層級的一個面向，但
   本階段未確認它是否屬於第一版要交付的能力、或僅是層級模型要預留的位置。
3. 使用者的原始描述提到「主動通知推播」，但本階段未確認推播的觸發情境與
   接收對象。
4. 「專案 → 系統 → 架構圖」層級一旦建立，既有以單張架構圖為單位的使用
   方式將如何銜接（既有資料的歸屬、既有頁面的呈現）尚未確認。

`stakeholder-map.md`：

5. 四類關係人為**角色**，非具名個人；本階段未確認每個角色實際對應哪些人、
   共有多少人。
6. 「成本／FinOps 關注者」與「管理者／平台維運者」在第一版為間接服務對象；
   本階段未確認他們在哪一個後續階段會變成直接服務對象。

- A. Accept assumptions
- B. Convert to follow-up questions

[Answer]: A. Accept assumptions
