## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary
本站以「引用上游代替重寫」的精簡形式交付：五個面向中，安全面有實質增量（呼叫邊界圖、K-07 約束、NFR5.1／5.2 的落點），其餘四面向以「無待設計 pattern 加失效條件」承接上游 nfr-requirements，引用足以承載本站內容，不因精簡而列為缺口。主要問題是產出停在單元首次交付時的前提：後續 U23／U14 已在已落地程式加入成員可見性守門與成員範圍列舉，使「擁有者範圍、個位數規模、不在 NFR3 路徑上」三項前提與程式矛盾，而程式碼反過來引用了設計檔裡不存在的章節（security-design.md 二之二）。前次 nfr-requirements review-01 的 R-01、R-02 在本站原樣沿用、未處置。Major 共 2 項，未達 NOT-READY 門檻。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/hierarchy-service/nfr-design/security-design.md（無「二之二」節）；nfr-design/logical-components.md 一（hierarchy_router／HierarchyFacade 列）；程式 backend/services/hierarchy_facade.py:44、:248；backend/services/hierarchy_router.py:54-55 | 程式碼兩處以 security-design.md 二之二 作為「K2 之後、擁有者檢查與一切 409 之前做可見性守門」的設計依據，但該檔只有「一、一之二、二、二」且無二之二，引用懸空。更實質的是：logical-components 只允許 router「取身分、呼叫 facade、轉譯例外」，並把 facade 的判定限於 K2、BR6.1、BR6.4、BR6.5；實際 router 已 import membership_facade 與 MembershipNotFound（hierarchy_router.py:54-55），facade 的 describe_work_target、list_projects、list_systems、resolve_work_target、create_system、delete_project、delete_system 皆多一個 project_visible 注入參數（hierarchy_facade.py:25-60），brain_gateway.py:600-611 也在同一 session 注入 membership 判定。授權順序（K2、可見性、擁有者、409）與「facade 不 import 成員關係符號」這條邊界，是安全面的真實設計，卻不在本站任何產出內。程式是對的（有 ast 靜態測試鎖定，tests/test_project_visibility_static.py），設計產出是過時的。 | 在 security-design.md 補上實際存在的「二之二」：寫明授權順序、project_visible 由呼叫端注入、本模組不 import 成員符號、BR87.3／BR87.7 的鎖定方式；同步更新 logical-components 的 router 與 facade 兩列與呼叫邊界圖，使兩邊引用一致。 | New |
| R-02 | Major | construction/hierarchy-service/nfr-design/performance-design.md 一、二；scalability-design.md 二；traceability.json 的 NFR3 列（N/A）；前次 nfr-requirements review-01 的 R-01、R-02 已提 | 兩項前提與已落地程式矛盾。第一，performance-design 以「列舉限 ownerUserId 等於請求者、查詢量級為個位數」為由不設任何效能 pattern；但 hierarchy_service.py:238 的 list_projects_by_ids 已提供成員範圍列舉，facade 文件明言其唯一呼叫端是 MembershipFacade（hierarchy_facade.py:37-42），規模變成「擁有或受邀的專案數」，且「個位數」沒有任何來源或量測。第二，traceability 把 NFR3（首字延遲）判 N/A，但 brain_gateway.py:600-614 的 resolve_work_target 每次開 DB session、同步查詢後才有回應，位於串流回合首字之前。失效條件三項（拆進程、外部呼叫、全體使用者專案數）也沒有涵蓋「成員範圍」這個已發生的變化，因此重開條件實際上已被跳過而無人察覺。 | 把規模前提改為「擁有或受邀的專案數」並寫出假設上限與來源；NFR3 列改為對 resolve_work_target 指名其同步 DB 讀取，並說明預算由 U13 分攤或本站給二元判準（例如每次呼叫的查詢次數上限）；把成員範圍列舉納入失效條件。 | New |
| R-03 | Minor | construction/hierarchy-service/nfr-design/security-design.md 二（呼叫邊界圖）；traceability.json open_items 的 OPEN-ND7-2 | BR1.5「無任何單元繞過 facade」被明寫為整個授權強度的唯一防線，本站卻只說「本單元無法自驗」並推給四個呼叫端的 code-generation。實際上 U23 已用 ast 靜態測試鎖定成員列舉的唯一呼叫端（hierarchy_facade.py:40-41），證明同一種機械防線可行。本站是設計站，應把「用 ast 靜態測試鎖定 facade 為 service 層唯一 import 者」寫成設計 pattern，而不只是登錄成 open item。 | 在 security-design.md 加一個設計決定：以靜態 import 檢查鎖定 hierarchy_service 只被 hierarchy_facade 引用，並指名測試檔落點；或明寫不採用及理由。 | New |
| R-04 | Minor | nfr-design/security-design.md 二（第二個「二」節）；observability／performance／reliability／scalability-design.md 二 | 五個檔的結尾樣板文字逐字相同，且重複「二」節編號。更糟的是 security-design 的樣板寫「本面向不適用且無新增需求，本站沒有待設計的 pattern」，緊鄰上方卻有一張實際設計的呼叫邊界圖，兩段互相矛盾。 | 去除重複節號；security-design 的樣板改為只涵蓋「確實不適用」的部分，或刪除。 | New |
| R-05 | Minor | nfr-design/traceability.json 的 NFR7.1 列（目標為 observability-design.md 二）；observability-design.md 二 | NFR7.1（變更紀錄回應不得被呈現為完整歷史）的承接目標是 observability-design 二，但該節只寫「稽核不等於觀測」，沒有設計回應形狀。實際落點在 router 回應模型：hierarchy_router.py:96-99 宣告 source 欄位、:347-349 的 docstring。 | 將 NFR7.1 的落點改指 diagram-changes 回應模型的 source 欄位，並在 observability-design 或 security-design 寫一句設計決定。 | New |
| R-06 | Minor | nfr-design/observability-design.md 一；reliability-design.md 一 | 前次 nfr-requirements review-01 的 R-06 已提：403 與 409 拒絕事件是 ADR-0006 audit logging 面的可觀察事件，本站只確認 logger 命名，沒有規定拒絕事件是否記 log、記哪些欄位（不含 token）。logger 已存在（hierarchy_facade.py:65、hierarchy_router.py:57）。 | 補一句拒絕事件的記錄決定，或明寫不記並說明理由。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| 抽查 openapi.json 的 hierarchy path | PASS：diagram-changes、projects、projects/{project_id}、projects/{project_id}/systems、systems/{system_id} 共 5 個 | NFR5.1 已落地，與設計宣稱的五個 path 一致 |
| 抽查 hierarchy_router.py 409 宣告 | PASS：CONFLICT_RESPONSE 於 :115，並用於 :174、:241、:277、:303 | NFR5.2 已落地 |
| 抽查 logger 命名 | PASS：cloud360.hierarchy_router、cloud360.hierarchy_service、cloud360.hierarchy_facade | 沿用義務已落地 |
| 抽查模組級可變狀態（NFR4.1） | PASS：hierarchy_service.py、hierarchy_facade.py 無模組級 dict／list 賦值 | 進程內零狀態成立 |
| grep 設計檔「二之二」 | FAIL：程式引用的章節不存在 | 見 R-01 |
| 逐列 pipe 數檢查 | 已自行檢查，Findings 每列 7 個未跳脫分隔符 | 格式合規 |
