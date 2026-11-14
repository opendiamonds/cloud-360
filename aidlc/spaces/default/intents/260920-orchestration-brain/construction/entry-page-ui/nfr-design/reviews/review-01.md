## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-17T04:28:14Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-design/security-design.md > 二之一 步驟 ④' 與「所屬專案」定義、四 EPD1=A 定案設計、七 M8；nfr-design-questions.md > EPD1 選項 A 的「你會看到的」 | 新設計問題。EPD1=A 的使用者承諾是「被移出的建立者開自己的圖時，脈絡列只顯示圖名」，但設計做不到。resolve_work_target 回 {null, null, 圖} 之後，推送時 describe_work_target 收到的三元組只有 diagram_id，依 §二之一「只有圖時取圖所屬系統的 project_id」仍會推出前專案，該專案不可見，第 ③ 步把三名稱（含圖名）全部設為 null，與 §二之三 (b)「含他自己的圖名也 null」一致。結果是畫面顯示「（無法顯示名稱）」而不是圖名，使用者據以選 A 的描述為假。§四 測試 ② 只斷言作業對象為 {null, null, 圖} 與無 error，沒有斷言名稱，所以此矛盾不會被任何案例抓到 | 二選一並寫明：(a) 在 describe_work_target 對「只有 diagram_id 且圖屬請求者」的三元組不做 ④' 推導、直接回圖名（圖的擁有者是圖本身，專案與系統名仍為 null，與 (b) 的裁決不衝突）；或 (b) 維持現狀並更正 EPD1 選項 A 與 §四 的描述為「作業對象只有圖、脈絡列名稱為空」，並請使用者知情確認。不論哪個，§四 測試 ② 加上名稱斷言 | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-design/performance-design.md > 三之三 目錄路徑的成本變化；security-design.md > 十 殘留 4 | 新設計問題。文件稱「N 上限 50（CATALOG_PROJECT_MAX）時由 152 增為 252」，但 50 是截斷門檻而非 N 的上界。實查 brain_gateway.py _build_catalog：list_projects 回傳全部擁有的專案（無上限），len 大於 50 才標 truncated。新設計讓 list_projects 對每個擁有的專案都付一條可見性 SQL，所以擁有 500 個專案者在截斷前就是 2 加 500 條，而舊版這個情形只有 2 加 1 到 3 條。這段在交辦的關鍵路徑上（首字預算 NFR3），文件宣稱的上界不成立，「判定只有一份」的代價被低估 | 更正數字為 2 加 5N（N 未封頂），明寫「N 大於 50 時 list_projects 仍付 N 條」；至少在 facade 的 list_projects 加上截斷感知（超過 CATALOG_PROJECT_MAX 時的處置），或在 EPN-06 註記中接受並量化擁有 200 個專案時的額外語句數 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-design/security-design.md > 二之三 (b) 與 七 M2 | 新設計問題。M2（is_project_visible 拿掉外層 project_id 條件）宣稱 (b) 會紅，理由是「另一專案的成員被當成可見」。但 (b) 的構造只有「owner 是他、無他的成員列、專案另有一位成員」，被移出的建立者在該夾具裡沒有任何其他可見專案。拿掉外層條件後函式退化成「請求者有任何可見專案」，在此夾具中仍為假，(b) 不會紅，M2 存活 | (b) 的夾具加一個他仍是成員的第二專案（或另立 (b2)），使 M2 必須紅；code-generation 的突變結果才有意義 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-design/security-design.md > 二之二 _names_for 的失敗處置 與 二之三 (f) | 新設計問題。同一節同時寫「_names_for 捕捉全部例外（含 HierarchyForbidden）並記一筆 work_target_names_failed」與「被拒絕不另記 log」，(f) 又期望 K2 撤銷時有一筆 WARNING。K2 view 被撤銷的使用者每次推送都會產生一筆 WARNING，且與「被拒絕不記」字面矛盾 | 明寫 HierarchyForbidden 是否記 log（建議不記），並同步修改 (f) 的期望與 ADR-0006 audit 列 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-design/security-design.md > 六之二 子頁面列（K1 掛載條件） | 新設計問題。大腦掛點依 can(K1) 條件掛載，但 frontend-components.md 的同步掛點 useWorkspaceTargetSync 與 useAssessmentTargetSync 是頁面層 hook，onPageReady、markOrigin、onDiagramDeleted 由頁面無條件呼叫，連線卻在條件掛載的 BrainSession 內。設計未說明 K1 失效或本來就沒有 K1 時，頁面層 hook 的行為 | 補一句規則：無連線時同步 hook 的所有入口為 no-op，並加入 §六之二 第二案斷言（K1 撤銷後畫布不受影響且不送出任何 set_work_target） | New |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-design/security-design.md > 二之一「所屬專案」 | 新設計問題。所屬專案取「project_id 參數優先」，只對那一個專案判定可見性。儲存的三元組由 resolve_work_target 推導，通常一致；但圖後來被改掛到另一系統時，三元組的 project_id 與系統真實所屬專案可能不同，系統名稱可能來自不可見的專案。系統層已 join 取得所屬專案，補判成本小 | 對三元組中出現的每個相異專案 id 都判定可見性（至多多 1 條 SQL），或明寫此情形不可達的理由 | New |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/nfr-design/nfr-design-questions.md > 一 第 3 項；performance-design.md > 一之二 排程列 | 新設計問題。(1) 問題檔稱偏離 BR92.5 在 security-design.md「§五之二」揭露，實際章節為 §六之二，§五之二 不存在。(2) 排程公式 BASE[min(n,5)] 若 n 為 1 起算的失敗次數，第一次等待是 2 秒而不是文件推導的 1 秒；累計數列 1、3、7、15、30、45、60 只在 n 為 0 起算時成立（握手 8 或 9 次的結論兩種讀法相同，但實作者可能依字面寫錯） | 更正章節引用；排程列寫明 n 從 0 起算，或改寫為 BASE[min(n-1,5)] | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 依規範未執行任何測試或程式 | N/A | 全部以讀檔與 grep 查證 |
| grep 全 backend 應用程式碼的 list_projects、list_systems、resolve_work_target、describe_work_target 呼叫端 | 應用程式呼叫端只有 brain_gateway.py 的 _build_catalog（3 處）與 _HierarchyResolver（1 處）、session_store.py:387；hierarchy_service 的呼叫皆為模組接收者；intent_routing 的 _describe_work_target 為 Name 呼叫 | 支持 S3 擴充、讀取呼叫點下限 5、例外清單一筆的主張 |
| grep tests 中受簽章變更影響的呼叫端 | test_hierarchy_service.py 191、199、212-216；brain_gateway_fakes.py 的 FakeHierarchy 三方法與 BrainGateway、_HierarchyResolver 建構；test_brain_gateway_startup.py:60 的 lambda。其餘（test_session_store_behaviour 用 Mock、work_orchestrator 用 object()、test_hierarchy_service.py:171 只檢查第一參數名）不受影響 | 作者的受影響清單完整，未發現漏列 |
| 靜態鎖相容性 | test_brain_gateway_limits.py 禁止清單只擋模組匯入，參數名含 membership 不構成匯入；S4 的 project_visibility 只定義在 MembershipFacade，FakeVisibility 在 tests 內被排除掃描 | 注入形狀不違反既有鎖，S2、S3 的擴充可行 |
| 實算握手次數 | r 為 1.0 時失敗時刻 0、1、3、7、15、30、45、60 共 8 次；r 為 0.8 時 0、0.8、2.4、5.6、12、24、36、48、60 共 9 次；30 除以 9 取整為 3 | 與文件一致 |
| 實算 SQL 條數 | 完整三元組 1 加 1 加 1 加 1 加 1 為 5，快照 15；目錄 2 加 3N 為 152（N 為 50），2 加 5N 為 252 | 一致，但 N 未封頂的問題見 R-02 |
| esquery 版本與 :has(> ...) 語法 | node_modules/esquery 為 1.7.0，README 列有 :has(> ForStatement)；既有 eslint 區塊 files 為 **/*.{ts,tsx}，已涵蓋 tests；member-pages.spec.ts:573 的物件只有 loc、msg、type 三鍵，不含 payload | 收窄選擇器可行且不誤擋既有 spec；抽常數的理由成立 |
| 事實與定位抽查 | hierarchy_facade.py:107-108、194-202、366-405；hierarchy_service.py:291-323；brain_gateway.py:130-155、564-577、736-746、1226-1243、1403-1426、1569-1598；membership_facade.py:518-533；membership_service.py:367-379；AuthContext.tsx；App.tsx:24-34；eslint.config.js:36-66 | 內容與行號相符 |

### Summary

主要關切是 EPD1=A：使用者選 A 所依據的「脈絡列只顯示圖名」與設計自己的可見性推導互相抵觸（R-01），以及目錄成本的上界被誤述為 N 不超過 50（R-02）。其餘設計成立：factory 必填注入與就地閉包、S2 與 S3 擴充及例外清單一筆、4403 不導航改 refreshMe、事件式對話清除、turnId 改記段、lint 選擇器收窄與常數抽取、握手與語句數實算，帶入項落點抽查無缺漏。兩個 Major 未超過 2 個，故 READY（advisory，供核可關卡權衡）。分類計數：新引入 0、既存漏審 0、新設計問題 7。
