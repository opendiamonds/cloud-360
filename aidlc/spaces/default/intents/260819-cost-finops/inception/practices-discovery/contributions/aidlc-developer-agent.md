**Collaborator:** aidlc-developer-agent

## Contribution

盲評鏡頭：命名、分層邊界、錯誤處理、檔案組織、code-style 慣例。只讀 lead 草稿三檔、`team.md` Code Style、`code-structure.md`、`architecture.md`。未讀 sibling contributions，未改四份 lead artifacts。

### 核心挑戰：calculator 是純函式模組，還是塞進 `user_router`

草稿 Code Style 已寫「新模組一律三層」且「C1 新增 `cost_router` 與 calculator 須走三層形狀」。這句方向正確，但對 construction 仍太鬆：沒有點名反模式，也沒有把「像 `wa_rule_engine`」拆成可執行的邊界。本輪必須在訪談前釘死下列判斷，否則實作會走阻力最小的路徑——在既有胖 router 加幾個 handler。

**不應把 cost calculator 塞進 `user_router.py`。** 理由不是風格偏好，是既有規則與架構證據的交集：

1. **C1 是缺席的 bounded context，不是 auth 的延伸。** `architecture.md` 標示 Cost／FinOps 在 HEAD 無 calculator、無 pricing port、無 Cost UI；現行公開面只有 `/api/architecture`、`/api/collab`、`/api/auth` 三組 prefix。`user_router.py` 的職責是 auth／users／roles／permissions（`code-structure.md`）。把 TCO、SKU、hours、list price 寫進 `/api/auth` 會把 J 域與 C 域黏死，後續無法獨立測、獨立授權、獨立 dump OpenAPI。
2. **新業務邏輯已有分流規則，C1 落在「新模組」側。** 既有規則：新模組走 router → orchestrator/service → 不讀 DB 的純函式；修改 `user_router.py`／`collab_router.py` 才就地沿用胖 handler。C1 沒有既有 cost 檔（`*cost*`／`*pricing*`／`*tco*`／`*finops*` 在 `backend/`、`frontend/` 為 0），因此不是「改 `user_router`」，是「新建模組」。把 calculator 塞進 `user_router` 等於在這兩支之外新建「router 直寫商業邏輯」——這正是規則禁止的形狀。
3. **不得趁機抽取 `user_router` 的 service 層。** 同意草稿原句。`user_router.py` 831 LOC、0 個 `try/except`、同檔混用 `HTTPException` 具名／位置引數，且 HTTP 層測試仍極薄（全 repo 僅 `test_user_list_endpoint.py` 一例）。在同一個 PR 裡「加 C1 端點 + 順便抽 service」無法驗證重構沒改 auth 行為。Cost 落地只新增平行檔案，不重構 `user_router`／`collab_router`。
4. **ADR-0006 PBT 只落得進純函式。** 既有 `@given` 全在不讀 DB、不連外的模組（`wa_rule_engine`、`wa_lens_engine`、`diagram_builder` 等）。Calculator 一旦寫在 FastAPI handler 裡，Hypothesis 就要組裝 `Request`／`Depends`／DB session，PBT 會名存實亡，規則會從 N/A 變成「宣稱 blocking、實際測不到」。

**應做成與 `wa_rule_engine` 同形狀的純函式模組，但不要做成 `wa_rule_engine` 的延伸。** 「像 `wa_rule_engine`」指的是純度與可測性，不是檔案歸屬：

| 層 | 建議檔（flat `backend/services/`，與現況一致，不新開套件目錄） | 可做 | 不可做 |
|---|---|---|---|
| HTTP | `cost_router.py`（`*_router.py`） | 解析輸入、`user_can(..., "C1", ...)`、`raise HTTPException`、組 `response_model` | 金額運算、查價、讀價目表以外的領域公式 |
| 編排 | `cost_service.py`（或同等 orchestrator 名） | 讀 DB／override、呼叫 pricing port、呼叫 calculator、組回應 DTO | 把 TCO 公式內嵌於此，讓 PBT 測不到 |
| 純運算 | `cost_calculator.py` | 輸入價目＋用量＋覆寫 → 金額；不讀 DB、不 `httpx`、不碰 FastAPI | 當成 WA finding 產生器 |
| I/O port | `pricing_client.py`（獨立模組；見 discovered-rules Forbidden） | 查 public list 或靜態表 | 混進 `diagram_builder`／`review_router` 既有 `httpx` 呼叫點；也不可寫進 calculator |

`wa_rule_engine.py` 的 `COST-*` 是關鍵字啟發式（無金額、無 SKU）。比塞進 `user_router` **更誘人** 的反模式，是把 TCO 函式追加到同一檔，因為檔名已有 COST。草稿 Forbidden 禁止把 `COST-*` **當成** TCO 來源，但沒有禁止把 TCO **寫進** 該檔。建議訪談後升格為硬約束：NEVER 把 TCO／pricing 邏輯追加進 `wa_rule_engine.py`；calculator 用 `cost_*` 前綴，不用 `wa_*`（`wa_*` 專屬 WA 引擎）。

### 命名（追認草稿，補 C1 缺口）

- Python：`snake_case.py`；router 必須 `cost_router.py`，不得叫 `cost.py` 或掛在 `user_router.py`。
- 純引擎：`cost_calculator.py`，**禁止** `wa_cost_engine.py`——避免與 WA 啟發式同名前綴。
- Logger：新模組一律 `logging.getLogger("cloud360.cost_router")` 這類 `"cloud360.<module>"`，不得用 `__name__`（該不一致只存在於舊檔）。
- Frontend：頁面必須 `CostPage.tsx`（`PascalCase` + `*Page.tsx`）。非元件 TS：hook 用 `use*.ts`，其餘 camelCase。Sidebar C 組標籤可中文，路由 path 維持 `/cost`。
- API prefix：新建 `/api/cost*`，由 `main.py` 另 mount；不要掛在 `/api/auth` 下「順便」暴露。

### 錯誤處理

同意草稿既成慣例：DB／驗證直接 `raise HTTPException`，不 `try/except` 吞掉；`try/except` 只在外部依賴邊界（此處即 pricing API／檔案價目），且必須記 log 或降級，不得靜默。

對**新檔**補一條草稿沒寫清的：`user_router.py`「沿用所在函式鄰近寫法」對全新 `cost_router.py` 無鄰近可循。新模組一律具名 `HTTPException(status_code=..., detail=...)`，不要把 831 LOC 檔內的混用風格複製過來。Pricing 失敗對使用者要表面化（4xx／5xx + `detail`），calculator 純函式則丟領域例外或回傳明確錯誤值，由 service 轉成 HTTP——不要在純函式裡 `raise HTTPException`（那會把 FastAPI 洩進 PBT 落點）。

### 檔案組織與前端結構約束

- 後端維持 `backend/services/` 扁平放置，與 `code-structure.md` 現況一致；本 intent 不順便引入 `services/cost/` 套件目錄（那是獨立重構）。
- 前端沿用頁面擁有資料流：`CostPage.tsx` 內純抓取函式 + `.then/.catch/.finally` 更新 state + `useEffect` 的 `cancelled` flag。新增 `fetchCost*` 必須走 `apiUrl()` + 手寫 `Authorization: Bearer` + `res.ok` + `data.detail`，不得單點自創 client 抽象，也不得為了 Cost 頁去抽全站 fetch wrapper。
- Context 若需要 Cost 專用狀態：Provider 在 `.tsx`、hook／型別在同名 `.ts`（`react-refresh/only-export-components`）。預設先不要新 Context——A1／A3 頁面都是頁內 fetch。
- SSOT：價目、角色、C1 權限旗標禁止在 `CostPage` 手寫第二份常數。跨語言副本必須同 PR 帶鎖一致測試。

### 建議 lead 整合進草稿的具體句子（可直接貼）

在 `team-practices.md` Code Style「後端分層」C1 句之後追加：

> C1 calculator 是新 bounded context：新建 `cost_router.py` + `cost_service.py` + `cost_calculator.py`（純函式，不讀 DB、不連外；PBT 落此）+ 獨立 `pricing_client.py`。NEVER 把 TCO／查價寫進 `user_router.py`、`collab_router.py` 或 `wa_rule_engine.py`。本 intent 不抽取既有胖 router 的 service 層。

在 `discovered-rules.md` Forbidden 追加候選（標 `[proposed — 待訪談]` 直至人工核可）：

> **NEVER** 將 cost calculator 或 `/api/cost*` handler 實作於 `user_router.py`／`collab_router.py`。
> **NEVER** 將 TCO／pricing 邏輯追加於 `wa_rule_engine.py`；`COST-*` findings 維持啟發式，不升格為金額來源。
> **NEVER** 在 `cost_calculator.py` 內呼叫 `httpx`／讀 DB／`raise HTTPException`。

### 訪談只需問草稿無法從證據推定的一題

證據已足夠推定「新模組三層 + 不抽 `user_router`」。若訪談要收斂 C1 落地形狀，建議只問：calculator 純函式與 pricing I/O 是否拆成兩個檔（如上表），或允許 service 內含靜態價目表、首版不做獨立 `pricing_client.py`。後者仍必須保持 calculator 純函式；前者才符合 discovered-rules 現有「不得無 port 直呼 Pricing API」。

## Positions

- AGREE: 新模組／新業務邏輯一律三層，純運算下沉到不讀 DB 的函式 — C1 無既有 cost 檔，落在「新模組」側，不是改胖 router。
- AGREE: 修改 `user_router.py`／`collab_router.py` 不趁機抽 service 層 — 缺 HTTP 測試保護時，重構與功能變更不可混 PR。
- AGREE: 命名（`*_router.py`、`*Page.tsx`、`cloud360.<module>` logger）、前端 fetch 兩層、錯誤在外部邊界才 `try/except` — 與 codekb／team Code Style 一致，C1 沿用即可。
- AGREE: cost calculator 一旦落地，ADR-0006 PBT 由 N/A 轉 blocking — 這要求計算核心必須是可直接呼叫的純函式，不能活在 handler 裡。
- OBJECT: 草稿未排除「把 TCO 追加進 `wa_rule_engine.py`」— Forbidden 只禁把 `COST-*` 當成 TCO，最誘人的檔案歸屬反模式仍開著。
- OBJECT: 「像 `wa_rule_engine`」未寫明純度契約 — 未禁止 calculator 內 `httpx`／DB／`HTTPException`，會讓 PBT 落點與 pricing port 黏在一起。
- OBJECT: 未明示 API／檔案反模式 — 未寫 NEVER 把 `/api/cost*` 或 calculator 塞進 `user_router.py`，construction 仍可能「在 auth 加三個 endpoint」抄 831 LOC 形狀。
- OBJECT: 新檔 `HTTPException` 風格無預設 — 「沿用鄰近寫法」對全新 `cost_router.py` 無鄰近；應指定具名 `status_code=`，勿複製 `user_router` 混用。
