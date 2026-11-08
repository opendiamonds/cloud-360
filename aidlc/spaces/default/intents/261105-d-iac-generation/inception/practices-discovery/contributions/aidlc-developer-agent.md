**Collaborator:** aidlc-developer-agent

## Contribution

以 developer 視角覆核 lead drafts（`team-practices.md`／`discovered-rules.md`／`evidence.md`）對命名、分層、錯誤處理、檔案組織與程式風格的主張；並對照 `team.md`／`project.md`、codekb（`code-structure`／`architecture`／`technology-stack`）與現況抽查（`langgraph_runtime.py`、`agent_router.py`、`WorkspacePage.tsx`、`backend/cost/`）。

### 既有規則（同意沿用，非本輪新發明）

1. **新模組三層為硬約束**：`team.md` 已定案——新業務不得再走 `user_router`／`collab_router` 的「router 直寫商業邏輯」；純運算下沉到不讀 DB、不連外的函式。Story D 落地時 **必須** 套用此通則；lead 把 D 柱具名（`d1_*`／`iac_*` 等）標 `[proposed]` 而非逕寫 ALWAYS，形狀正確。
2. **純函式層禁令與 ADR-0006**：純核心禁止 `httpx`、DB session、`HTTPException`——與 C1 估價解析器／`langgraph_runtime.RuntimeAuthError`（domain error，非 HTTP）一致；IaC generator 一旦落地，PBT 由 N/A 轉 blocking。`discovered-rules` 只重申既有 ALWAYS，不發明工具選型 NEVER，正確。
3. **錯誤處理**：DB／驗證 → 直接 `raise HTTPException`；`try/except` 僅外部邊界（LLM／檔案／webhook）且須降級或 log。D agents 呼叫 `openrouter_chat_model` 時應像 `review_agent`／`wa_lens_engine` 捕獲 `RuntimeAuthError`，由 router／SSE 邊界轉成可觀察錯誤，不得靜默。
4. **命名／logger／docstring**：新 Python 檔 `snake_case`、router `*_router.py`、logger `"cloud360.<module>"`、router docstring 對齊 `agent_router.py` 契約段深度；前端頁面 `*Page.tsx`、hook `use*.ts`、API 呼叫沿用 `apiUrl()`＋手寫 Bearer＋`res.ok`／`data.detail`——同意 lead 沿用，不單點自創抽象。
5. **Workspace UI**：實讀確認「生成 IaC 代碼」→ `showComingSoon('IaC 代碼生成')`（約 L259–265、L966），**不**查 D1、**不**打 API；對照列 `goWellArchitected` 有 A3 權限閘。同意 lead：此為產品／設計待修，不在 practices 新造 NEVER；真 CTA 替換時必須接 D1 權限＋既有資料抓取兩層形狀（lint `set-state-in-effect`）。

### 查證後的修正／補強（訪談應納入）

1. **檔案組織先例已漂移**：C1 並未落成 `services/cost_router.py` 扁平檔，而是 **`backend/cost/` 套件**（`estimate_intake_router` → `estimate_intake_service` → `estimate_parser`／`pricing_client`；agent 為 `cost/cost_advice_agent.py`）。Lead 的 I5 選項若只列 `d1_*`／`d2_*`／`d3_*` 或扁平 `iac_*`，會偏離唯一 greenfield 功能域先例。訪談應加選項：**領域套件**（建議 `backend/iac/`，內含三層＋三 agent）vs 扁平 `services/`；**禁止**以 story id 當檔名前綴（`d1_router.py`）——權限用 `require_story_action("D1", …)`，模組名用領域語彙（如 `iac_generate_*`／`iac_scan_*`／`iac_secret_*`）。
2. **三層邊界用語**：`estimate_intake_service` **會** `raise HTTPException`（固定 detail 字串）；禁令只綁純函式核心。撰寫／訪談時勿把「整條呼叫鏈禁 HTTPException」寫進規則。
3. **Agent 底座**：同意「新 D agents 強制走 `langgraph_runtime`＋OpenRouter、禁止再增 Claude-SDK-only／Anthropic-only 路徑」；但須明寫 **不**要求本 intent 收斂既有 `design_agent`（仍 `ChatAnthropic`＋`llm_provider`，logger 仍 `__name__`）——那是獨立收斂議題（codekb `architecture.md` 亦如此標）。三 agent 檔應與領域套件同目錄，勿 router 在 `cost/` 形狀、agent 卻散落 `services/`。
4. **API 掛載**：C1 先例為 `main.py` `include_router(..., prefix="/api/cost/v1")`＋`require_story_action("C1", …)`。D 柱應預留獨立前綴（如 `/api/iac/...`），勿塞進 `agent_router`／`user_router`；權限用 story id，路徑用領域名。
5. **前端組織**：若僅擴充 Workspace CTA，不新建 `*Page.tsx` 亦可，但仍須遵守兩層 fetch 與 `apiUrl`；若另開頁，路徑必須進 `App.tsx` 路由表（TCMS／契約機械比對依賴）。I7 留設計階段可接受，但 practices 應鎖「不得繼續用無權限 stub 充當已交付」。

### 對 drafts 整體判斷

- Lead 對 **Code Style 基線逐字保留**、Story D 標 `[proposed]`、`discovered-rules` 不預選掃描工具——符合 practices-discovery:c1／認真找碴紀律。
- Developer 範圍內最大缺口是 **未把 `backend/cost/` 套件先例寫進 I5 檔案組織選項**；其餘三層、錯誤邊界、logger、Workspace 複用方向同意。

## Positions

- AGREE: 新 D routers／services／純核心必須遵守既有「新模組三層」；純函式禁 httpx／DB／HTTPException；logger 用 `cloud360.<module>`；Workspace 真 CTA 沿用 `apiUrl`＋權限閘＋兩層 fetch，Coming Soon 脫鉤屬設計債非新 NEVER。
- AGREE: 三個 LangGraph agents（D1／D2／D3 各一）新碼強制 `langgraph_runtime`＋OpenRouter，禁止再增 SDK-only 路徑；`discovered-rules` 不發明工具／skeleton 硬約束、留給訪談——正確。
- OBJECT: I5／Code Style 的 D 柱具名選項漏掉 C1 已落地的 **`backend/cost/` 套件組織**；應改問「領域套件（建議 `backend/iac/`）vs 扁平 services」，並反對 `d1_*` story-id 檔名前綴，以免與唯一 greenfield 先例分叉且混淆 RBAC id 與模組名。
- OBJECT: 若訪談採「一律三層＋禁 HTTPException」措辭，必須限定在純函式層——C1 的 service 層本來就 raise HTTPException；並明寫三 agent 與 router 同領域套件、不強制本輪收斂 `design_agent`。
