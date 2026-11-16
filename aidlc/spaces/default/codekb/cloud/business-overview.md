# Business Overview — Cloud-360

> **基準**：`34aeef3`（2026-10-02）、branch `danniel/docs/orchestration-brain-ideation`。
> **新鮮度等級與證據標記的定義在 `reverse-engineering-timestamp.md`**；本檔每節標 A／B／C／D／E。
> 本檔由 `codekb/cloud-360@2026-09-22`（主線一～五 ＋ 業務邊界 ＋ 詞彙表）與
> `codekb/cloud@2026-10-01`（產品定位 ＋ 使用者旅程表）合併，並加入本輪新發現。

---

## 系統定位 〔B〕

Cloud-360 是一個 **AI-native 多雲（AWS／GCP／Azure）架構與維運平台**，以對話驅動的方式
協助團隊產出、評核、共編與估價雲端架構。核心價值鏈為「以自然語言描述需求 →
產生可編輯的 draw.io 架構圖 → 以 Well-Architected lens 審核 → 由同一份架構圖推導成本」，
並以**故事級 RBAC** 控制誰可檢視、編輯、審核與改價。

執行環境限於自有 staging（`cloud360.danniel.cc`，ADR-0007）；雲端供應商 production
仍在範圍外（ADR-0001／ADR-0002）。方法論基礎為 Spec-Driven Development 與 AI-DLC v2（ADR-0011）。

| 能力線 | 故事代號 | 對外介面 | 現況 | 等級 |
|---|---|---|---|---|
| 對話產出架構圖（drawio） | A1 | SSE | 已上線 | C |
| Well-Architected 評核與改善建議 | A3 | SSE | 已上線；**agent 框架已於 2026-10-01 改走 LangGraph**（commit `b4f0cdc`） | A |
| 架構圖共編與聊天持久化 | A4 | WebSocket | 已上線 | C |
| 成本／估價（上傳官方估價表 → 檢查 → LLM 建議） | C1 | HTTP ＋ SSE | 已上線，**10 個 HTTP operation** | B |
| 帳號授權、角色權限治理、帳號活動稽核 | J3a／J3b／J5 | HTTP | 已上線 | B |
| **統一入口「大腦」編排** | — | WebSocket | **只有一支 demo-scope 的垂直切片在跑**（見下） | A |

專案方法論的工作區（`aidlc/`）與框架殼（`.claude/`）同住此 repo，但**不是應用程式碼**，
兩輪皆未掃描。

---

## 使用者可見的入口（前端路由，本輪複驗行號）〔B〕

`[讀:link1]` `frontend/src/App.tsx`，**13 條路由**：

| 路由 | 頁面 | 功能 |
|---|---|---|
| `/login`（`:36`） | `LoginPage.tsx` | 登入 |
| `/403`（`:37`） | `ForbiddenPage.tsx` | 無權限 |
| `/waiting-approval`（`:39`） | `WaitingApprovalPage.tsx` | 待核准 |
| `/workspace`（`:48`） | `WorkspacePage.tsx` | **A1 對話產圖**（draw.io 畫布 ＋ 聊天） |
| `/assessment`（`:61`） | `AssessmentPage.tsx` | **A3 架構評核**（Well-Architected） |
| `/cost`（`:74`） | `CostPage.tsx` | **C1 估價與成本建議** |
| **`/brain`（`:88`）** | **`BrainPage.tsx`** | **大腦入口（DEMO SCOPE，見下節）** |
| `/admin/users`（`:99`） | `AdminPage.tsx` | 帳號管理 |
| `/admin/authorization-requests`（`:112`） | `AuthorizationRequestsPage.tsx` | 授權申請 |
| `/admin/role-permissions`（`:125`） | `RolePermissionsPage.tsx` | 權限矩陣 |
| `/admin`（`:137`） | → redirect `/admin/users` | |
| `/`（`:139`） | | 首頁 |
| `*`（`:147`） | | catch-all |

> **`/brain` 路由在兩份 store 都沒有記載。** `cloud/` 的 `App.tsx` 雖在其 deep 集合內，
> 但掃描 commit `5fd8f14` 早於 `BrainPage` 落地。
> `cloud-360/` 記「11 條路由」`[承:cloud-360@2026-09-22]`——**HEAD 是 13**。

Sidebar 導覽依 user story 大類分層（例如 A、J），故事層（A1／A3、J3a／J3b）為第二層
——這是 `project.md` `## Way of Working` 的既有規則，新功能比照。

---

## 服務對象與角色 〔B〕

`services/rbac.py:23–35` 的 `CANONICAL_ROLES` 是角色清單的正本，共 **11 個角色** `[跑]`
（本輪以 Python import 該模組實算）；權限矩陣為 **11 角色 × 28 個 story id = 308 列** `[跑]`
（import `services.rbac_seed_data` 實算 `DEFAULT_ROLE_PERMISSIONS` 長度）。

每個 `(角色, story)` 格有 `view` / `edit` / `review` 三個旗標
（元組形狀如 `('Project_Architect', 'A1', True, True, False)` `[跑]`）。
以 C1 為例 `[承:cloud-360@2026-09-22]`：具 `edit` 者為 `Project_Architect`、`Project_Editor`、
`Project_Admin`、`FinOps_Analyst`、`Platform_Admin`；`Developer`、`Platform_Engineer`、
`Security_Reviewer` 三者 C1 三旗標全 false，Sidebar 與 `/cost` 路由對他們隱藏或 403。

> **既有教訓（仍有效）**：**RBAC 種子可以早於產品面存在。** 看到某個 story id 出現在
> 權限矩陣，不代表對應的 router、頁面或資料表存在。C1 曾長期處於此狀態。
>
> **本輪新增一個同型但方向相反的陷阱**：`user_router.py:85` 的
> `"H3": "MCP／Skill 生命週期"` 是**全 `backend/` 唯一的 `mcp` 命中** `[跑]`，
> 它是**權限頁上那一欄的中文顯示名**，不是任何 MCP 實作。
> 下一個人 grep `MCP` 命中它就會得到「已經有了」的反向結論——而 repo 內
> **零 MCP 基礎設施**（見 `architecture.md` 約束十二）。

---

## 核心業務流程主線

### 主線一：取得帳號與授權 〔C〕
註冊 → `authorization_status` 待審 → 管理者於授權審核頁核可 → 取得角色。
`require_story_action` 在**任何** story 授權檢查之前先擋 `authorization_status != "approved"`
並直接 403 `[承:cloud-360@2026-09-22]` `rbac.py:262–267`。

### 主線二：對話產圖（A1）〔B〕
使用者在 Workspace 輸入需求 → `prompt_guard` 前置檢查（平台自我竄改預檢）→
`design_agent` 以 **LangGraph（`StateGraph` ＋ `ToolNode` ＋ `ChatAnthropic`）** 產出 →
`diagram_builder` 轉成 drawio XML（n8n webhook 取 icons）→ SSE 逐步回送。

> **更正** 〔A〕：`cloud-360/` 原文寫「`design_agent` **以子行程驅動 `claude` CLI**」
> `[承:cloud-360@2026-09-22]`。**那在 HEAD 上已不成立**：
> `[跑:link1]` `grep -rn "create_subprocess_exec|Popen|subprocess" backend/` → **零個實際呼叫**
> （5 處命中全是 docstring／註解字串）；`backend/Dockerfile` 已移除 Node 與
> `@anthropic-ai/claude-code` CLI `[讀]`。A1 走的是 LangGraph ＋ OpenRouter HTTP。

> ⚠️ **本主線有一個已查證的高嚴重度缺陷** 〔A〕：
> **兩個重疊的產圖請求會導致使用者 A 收到使用者 B 產生的架構圖 XML**，
> 或某一方的事件（含錯誤訊息）被靜默丟棄。原因是 `design_agent.py:31` 的
> `_progress_queue` 是模組層單槽全域。業務影響：**這是跨使用者的內容外洩**，
> 不只是「進度看不到」。詳見 `architecture.md` 約束四與 `code-quality-assessment.md` T-14。

### 主線三：架構評核（A3）〔B〕
以 WA Lens 規則引擎（`wa_rule_engine`／`wa_lens_engine`，純函式、不碰 LLM）
加 LLM 評核，結果寫入 `architecture_reviews`，可匯出 PDF／PNG（`html2canvas` ＋ `jspdf`）。
SSE 三階段：`rules_done` → `lens_done` → `suggestion_delta` → `complete`
`[承:cloud@2026-10-01]`。

> **更正** 〔A〕：`cloud/` 原文寫「Review／Lens 仍 **Claude Agent SDK**」
> `[承:cloud@2026-10-01]`，並把「把 A3 改走 LangGraph」列為它那個 intent 的重構目標。
> **那件事已經做完了**（commit `b4f0cdc`，2026-10-01）：
> `review_agent.py` 的 docstring 逐字「A3 Review Agent（**LangGraph + OpenRouter**）」`[讀]`，
> 且 `claude_agent_sdk` 全樹零 import、`test_a3_langgraph_migration.py:33,40`
> 有**兩個 `assertNotIn` 斷言它不得回來** `[跑]`。
> **從業務面看：前端 SSE 契約未變，使用者不感知；但「映像還需要 Node／CLI」這個約束已消失。**

### 主線四：估價與成本建議（C1）〔B〕
上傳三雲官方估價表（AWS CSV／Azure XLSX／GCP CSV）→ 解析器（`estimate_parser`／
`estimate_readers`／`estimate_validator`，**純函式層**）轉為
`estimate_sets` / `estimates` / `estimate_line_items` → 檢查面板 →
LangGraph agent（`cost_advice_agent`）產生節費建議寫入 `advice` 表 →
前端以 SSE 取進度。

> **業務規則（兩輪皆確認）**：估價數字一律來自**使用者上傳的官方估價表**，
> 不由系統自動取價產生。計價 Port（`pricing_client`）只用於 agent 產生建議時確認現價，
> 結果寫入建議文字、**不得回寫明細**。此規則有兩支 CI validator 承載，
> 本輪實跑皆 exit 0 `[跑:link1]`。
>
> **帳單與用量類計價 API 全面禁止**（Cost Explorer、CUR、Cost Management、Billing Export）；
> **目錄價類已於 ADR-0018 解禁**（AWS Price List Query／IAM、GCP Cloud Billing Catalog／API key、
> Azure Retail Prices／免憑證）。

> **本輪的一處重要更正** 〔A〕：`cloud/` 的「C1 成本估算的業務行為」整段
> **描述的是已退役的舊實作**——它寫「估價來源為**自動取價**」、`sku_mapper`／`sku_ai_resolver`、
> `cost_pricing_agent` 建立 in-process MCP `cloud360-cost`、Azure／GCP Calculator runner
> 以 Playwright 驅動官方 Calculator、可調參數 `C1r`／`C1h`／`C1o` 寫入 `cost_audit_event`
> `[承:cloud@2026-10-01]`。
> **這些模組與那張表在 HEAD 上都不存在**：`schema_rbac.sql:191`／`:198`／`:208`／`:217`
> 的四張 `archive_*` 表就是它的遺骸 `[跑]`。
> **本檔刻意不保留那段**——保留它會讓下游誤以為兩套業務規則並存，而它們**方向相反**
> （自動取價 vs 一律用上傳的估價表）。要查舊實作請直接開 `codekb/cloud-360/`
> 或更早的 record。

### 主線五：權限治理與帳號稽核（J3a／J3b／J5）〔B〕
管理者頁面可改角色、停用帳號、逐格調整權限矩陣、檢視帳號最後活動時間。
`users.last_activity_at` 由 `activity.record_activity` 以 5 分鐘節流寫入
`[承:cloud-360@2026-09-22]`。
`[跑:link1]` 測試輸出顯示權限稽核 log 實際運作
（`INFO:cloud360.user_router:【權限稽核】User Privilege Re-assignment | ...`）。

> ⚠️ **WebSocket 通道可能讓「最後活動時間」靜默失效**：`collab_router.py:257` 用
> `record=False`。業務影響：以 WS 為主要互動的使用者在稽核表上看起來像從未活動過，
> 而**沒有任何錯誤訊息**。詳見 `architecture.md` 約束三。

---

## 本輪新發現：大腦已有一支 demo-scope 的垂直切片在跑 〔A〕

**這是本輪對業務面最重要的更新，兩份 store 都沒有它。**

| 項目 | 現況 |
|---|---|
| 使用者可見入口 | `/brain` 路由（`App.tsx:88`）＋ `BrainPage.tsx`（403 LOC） |
| 後端 | `brain_router.py`（455 LOC）掛在 `/api/brain`，WS 端點 `/api/brain/ws` |
| 落地時間 | 2026-09-28（commit `f9c5bda`，訊息逐字「**供今晚展示用**」） |
| 它自己的定位 | docstring 逐字「**DEMO SCOPE，非 `U13` 的正式交付**」、「**不屬於任何已核可的 AI-DLC 工作單元**」 |

**從業務面看，它能做什麼與不能做什麼**（docstring 自述）：

| 能力 | 狀態 |
|---|---|
| 對話往返、版本協商、工作項目回傳、錯誤回報 | **能**（`ready`／`token`／`clarify`／`work_items`／`done`／`error` 六種訊息） |
| 跨頁／跨登入的脈絡還原 | **不能**——session 用行程內 dict，**重啟即失憶** |
| 依意圖路由到正確的子功能 | **只有關鍵詞計分**，不是信心值模型 |
| 專案／系統／架構圖階層 | **不能**（三表已在 DB，但應用層未消費） |
| 三層記憶 | **不能** |
| 成本卡、分享模式、多連線扇出、更正工作項目 | **不能** |

> **為什麼這件事對下游最要緊**：本 intent 的正式單元 `U11`／`U13`／`U14` **還沒開始**，
> 而使用者在 `/brain` 上**已經可以看到一個會回話的大腦**。
> 不知道這件事的 stage 會往兩個方向各錯一次：把工作當成 greenfield（低估已有的
> WS 契約、握手、訊息型別），或當成已經做完了（高估 session、路由、階層、記憶）。
> **它的正式交付方式是整支取代，不是逐段改寫。**

---

## 業務邊界與非目標 〔B〕

- ❌ 雲端供應商 production 環境、production credentials、直接對雲 IaC apply、
  破壞性雲端操作、原生行動 App（ADR-0001／ADR-0002）。
- ❌ **帳單與用量類計價 API 全面禁止**（Cost Explorer、CUR、Cost Management、Billing Export）
  ——此禁令是目錄價類得以解禁的對價（ADR-0018 §2），不得一併放寬。
- ✅ In scope：SRS、architecture diagrams、user stories、ADRs、IaC generator design、
  agent routing design、MCP/skill management spec、validation scripts、baseline CI、
  自有 staging 的部署與維運。
- ⚠️ **退役但仍在 schema 內的能力** 〔B〕：`archive_diagram_cost`、`archive_diagram_cost_line`、
  `archive_pricing_cache`、`archive_cost_audit_event` 四張表是 C1 舊實作的遺骸，
  在 `schema_rbac.sql:191`／`:198`／`:208`／`:217` `[跑]`。區塊標題逐字為
  `C1 Cost / FinOps tables — RETIRED (U3 legacy-cost-retirement)`、
  「應用零讀寫；保留 ≥90 天後另開 chore DROP」`[承:cloud-360@2026-09-22]`；
  `database.py` 的 `_ensure_cost_schema()`（`:379`）在啟動時把 live 表 RENAME 成 `archive_*`。
  **grep 到 `*_cost*` 表名不等於成本能力存在於該處**——現行成本資料在
  `estimate_sets` 等六張表（`schema_rbac.sql:240–306` `[跑]`）。

---

## 與作用中 intent（`260920-orchestration-brain`）的關係 〔A〕

本 intent 要建一個統一入口的「大腦」，編排既有的子功能 agent。本輪查證後的實際交集：

1. **既有能力中只有 C1 具備完整的 HTTP 可編排面**（10 個 operation，授權全掛在
   FastAPI dependency 上）。A1／A3 的對外面是 SSE，A4 與大腦 demo 是 WebSocket。
   **而 C1 的「串流」是 DB 輪詢的狀態事件，不是 token 串流**
   ——大腦要「逐字轉送」成本查詢進度時，**來源端沒有逐字可轉**。
2. **`專案 → 系統 → 架構圖` 階層的狀態已改變** 〔A〕：三張表
   （`projects`／`systems`／`diagram_change_records`）**已在 `schema_rbac.sql`**
   且有一次性遷移與終檢斷言（`AC9.1.4`）；`user_diagrams.system_id` 已是歸屬的權威來源。
   **但 ORM model、router、service 都還沒有。**
   > 這**推翻 `project.md` 記載的「`schema_rbac.sql` 只有 users→user_diagrams、
   > backend 全樹 `system_id` 命中 0 次」**——那在 intent-capture 當時為真，在 HEAD 上已不為真。
3. **「成本關注者」在 RBAC 已有落點**（`FinOps_Analyst`）且 C1 能力已實作，
   故該 persona 在第一版有可驗證的行為。
4. **session 與記憶的基礎設施已就緒，但應用層零消費** 〔A〕：
   Redis 與 Ollama 兩個服務已在部署堆疊、`db` 已升 `pgvector/pgvector:pg18`、
   環境變數契約已完成；**但 `requirements.txt` 無 `redis` 套件、backend 零 import、
   全樹尚無任何 `vector` 欄位**。
   **所以相關單元的起點是「接線」，不是「建服務」。**
5. **MCP 是真正的零起點** 〔A〕：零套件、零跨進程 agent 通道；
   現行唯一的工具暴露機制是同進程的 LangChain `@tool` ＋ LangGraph `ToolNode`。
   而 `MCP` 這個字在本 repo 已被 RBAC story `H3` 佔用。
6. **已有一支 demo 在跑**（見上節），它不是正式交付。

---

## 詞彙表 〔B〕

| 詞 | 意義 |
|---|---|
| story id | RBAC 權限矩陣的欄位鍵（A1／A3／A4／C1／H3／J3a…共 28 個） |
| Lens | Well-Architected 評核用的規則集，存於 `wa_lenses` 表與 `backend/lenses/` |
| estimate set | 一次估價工作的根物件，底下掛 estimates → line items |
| advice | C1 的 LLM 節費建議，一列對應一個 estimate set |
| `archive_*` | C1 舊實作退役後改名保留的表，**應用不得讀寫** |
| slot registry | 前端成本頁的插槽註冊表（`frontend/src/cost/slotRegistry.tsx`），repo 內既有的「頁面內可擴充插槽」前例 |
| **DEMO SCOPE** | **本輪新增。** 指 `brain_router.py`／`BrainPage.tsx` 這組為展示而寫、不屬任何已核可工作單元、且**預計被整支取代**的程式 |
| **WS 契約** | **本輪新增。** `brain_ws_contract.py` 定義的訊息型別，dump 成 repo 根的 `ws-contract.json`，再產生 `frontend/src/types/ws-contract.d.ts`；有兩道 CI 漂移閘門。**只涵蓋大腦，不涵蓋 `/api/collab/ws/...`** |
| **階層三表** | **本輪新增。** `projects`／`systems`／`diagram_change_records`；schema ＋ 遷移已落地，ORM／router／service 未落地 |
