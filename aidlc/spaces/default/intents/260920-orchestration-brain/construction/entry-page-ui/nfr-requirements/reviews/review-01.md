## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-17T03:12:48Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-requirements/security-requirements.md > 一、資料分類（專案／系統／圖的名稱列）與 二、EPN-11 | 既存漏審。資料分類宣稱名稱「只經授權與可見性判定後推送」，但 U13 還有第二條推送名稱的路徑未被 EPN-11 涵蓋：`brain_gateway.py:1215-1228` 的 `_build_catalog` 用 `facade.list_projects`／`list_systems`（`hierarchy_facade.py:366-379`，只做 `owner_user_id` 範圍，無 `project_visible`），名稱經 `rules.target_label`（`brain_gateway_rules.py:475-479`）寫進 `clarify` 候選標籤；`brain_gateway.py:1292` 的唯一命中還會直接 `_set_target_confirmed` 把被移出建立者仍擁有的專案設成作業對象並交辦。被移出的建立者因此能由反問標籤取得專案改名後的名稱，R-01 裁決要關的洞在另一條路徑仍開著，EPN-12 的防探測也不涵蓋它 | 二選一並寫進 §〇 與 §六 IAM 列：(a) 把 EPN-11 的可見性判定擴及目錄建構與唯一命中的設定（同樣經 EPN-11a／11b 的注入形狀），補被移出建立者說出專案名稱的案例；(b) 明列為已接受的殘留並開 OPEN 項，同時更正資料分類列與 §六「擴充」的措辭（現在讀起來像名稱路徑已封閉） | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-requirements/performance-requirements.md > EPN-06 與 三、EPN-06 的推導 | 新設計問題。每組 SQL 語句數 ≤ 4（快照 ≤ 12）在誠實實作下不可達：`describe_work_target` 首行 `_authorize(view)` 會經 `user_can` → `get_permission_row`（`rbac.py:124-132`，一條 `role_permissions` 查詢；`hierarchy_facade.py:194-202`），推導表只算了「可見性 1 加三層主鍵 3」。完整三元組最少為 1＋1＋3 ＝ 5。EPN-23 的 `before_cursor_execute` 計數會把授權查詢算進去，測試會對正確實作變紅，逼出遷就上界的實作（例如跳過授權或合併查詢） | 把上界改為 ≤ 5、快照 ≤ 15（或明寫授權查詢每次 `_names_for` 只付一次的實作約束，並說明 facade 如何不在每個三元組重付），推導表加入授權這一列；保留「1 個與 50 個專案語句數相同」的判準 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-requirements/security-requirements.md > EPN-11a、EPN-11b | 新設計問題。EPN-11a 要求擴充既有 S3（`test_project_visibility_static.py:135-160` 要求每個呼叫點的值是 `<…>.project_visibility(...)` 的呼叫），EPN-11b 又要求注入點在組裝處、U13 不得 import `membership_facade`（`test_brain_gateway_limits.py:380-381`）。`build_brain_gateway(app)`（`brain_gateway.py:1569`）定義在 U13 模組內，且 `_HierarchyResolver`（`:566-577`）每次自開 DB session，閉包必須綁同一個 session，所以注入物必須是「可產生 `.project_visibility` 的 factory」而不是現成閉包，並需改 `build_brain_gateway` 簽章與 `main.py` 的呼叫。文件把形狀全部留給後續站，S3 擴充能否成立取決於這個形狀 | 在 EPN-11b 寫明約束：注入物須暴露名為 `project_visibility` 的屬性（使 S3 的呼叫點形狀成立），且由 `main.py` 組裝；S3 擴充的呼叫點允許清單同步註明 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-requirements/performance-requirements.md > EPN-01 | 新設計問題。「開發模式 StrictMode 的雙重 effect 不留下殭屍連線」無法被所列量測方式驗證：`playwright.config.ts` 的 e2e 跑在 docker-compose.test.yml 的 nginx 正式建置上，StrictMode 的雙重 effect 只存在於開發建置。檢查欄的 5 次換頁只覆蓋正式建置 | 刪除該子句的「可量測」宣稱，改列為 code review 檢查（cleanup 必關閉連線、不依賴 ref 去重），或另寫以 vite dev 跑的單一案並說明其不進 CI | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-requirements/performance-requirements.md > EPN-03 | 既存漏審。BR92.5 規定 4403 → Navigate 到 `/`；在子頁面收到 4403 後 `DefaultRedirect`（`App.tsx:24-34`）會依前端快取的權限渲染入口頁，入口頁掛載即開新連線，與「4403 後自動發起的新連線 0 條」的計數字面衝突。權限快取（`AuthContext.tsx` 只在登入與初始化打 `/me`）若仍是 K1 為真，入口頁又被 4403 關閉，停在無法恢復的畫面 | EPN-03 限定計數範圍（同一頁面實例的自動重連）並加一案：子頁面收到 4403 後的落點與是否重取權限，寫進 nfr-design 待決項 | New |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-requirements/security-requirements.md > EPN-18 | 新設計問題。(1) 「沿用既有判定式、不另寫第二份」實際上要求把 `WorkspacePage.tsx:118-121` 內聯在 `handleCanvasExit` 的運算式抽成共用函式，文件沒有寫明這個重構；(2) `/assessment` 只有「判定式由 nfr-design 定案」，檢查欄與突變欄都只涵蓋畫布，R-02 裁決點名的未存檔上傳沒有任何二元可判的檢查 | 寫明抽出共用判定函式的要求；為 `/assessment` 補一個晚到 `work_target` 加未存檔上傳的 e2e 與必須紅燈的突變 | New |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-requirements/performance-requirements.md > EPN-02 | 新設計問題。抖動的理由是保護每 key 每分鐘 30 次握手（`brain_gateway_rules.py:79`），但 1、2、4、8、15、15 秒的排程在 60 秒內約 8 次嘗試，只往下抖 0.8–1.0 幾乎不分散同秒重連；4 個分頁即約 32 次超過上限，而 EPN-01 允許至 10 個分頁。文件沒有量化這個預算，也沒有說明被限流的握手如何被前端處置（BR92.5 將其視為「其他」續退避） | 寫出分頁數與握手預算的關係（例如宣告支援的同時分頁數），或把抖動範圍放寬並以預算計算佐證；否則把理由改述為「降低同步」而非「保護限流」 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| traceability.json 以 python 解析 | upstream_ids 11、coverage OK 6、N/A 5、reverse 29 | 與 tech-stack-decisions §五 第 6 項一致 |
| 三份產出粗體定義的 EPN 編號計數 | performance 9、security 13、tech-stack 7，合計 29 | 與 reverse 的 29 條相符；需求總數 9＋29＝38 成立 |
| 引用抽查 | `membership_facade.py:518`、`membership_service.py:367-379`、`test_brain_gateway_limits.py:380-381`、`test_project_visibility_static.py:112／135／162`、`brain_gateway.py:130-149／1292`、`WorkspacePage.tsx:118-121`、`AuthContext.tsx:56／82`、`auth-context.ts:29`、`brain_gateway_rules.py:79`、`eslint.config.js` 的 WsSubprotocol 規則均與敘述相符 | 事實與定位皆正確；Playwright 1.61.1 滿足 routeWebSocket 與 page.clock 版本需求 |
| `describe_work_target` 撞名 | backend 僅 `intent_routing.py:155` 的私有 `_describe_work_target` | EPN-25 的處置（不改名、以 Attribute.attr 錨定）成立 |
| ADR-0006 四面向與 PBT | 逐格對照存在，PBT 判不適用的理由與上游一致 | IAM 面的缺口見 R-01 |

### Summary

無 Critical、2 個 Major（R-01 名稱可見性在目錄與反問路徑仍外洩；R-02 SQL 上界 ≤ 4 因授權查詢而不可達），故判 READY（advisory），建議兩個 Major 在 nfr-design 前處理。EPN-11 的六案本身設計紮實，EPN-15（綁 login／logout 事件）與 EPN-18 的 e2e 構造可達。分類計數：新引入 0、既存漏審 2（R-01、R-05）、新設計問題 5（R-02、R-03、R-04、R-06、R-07）。
