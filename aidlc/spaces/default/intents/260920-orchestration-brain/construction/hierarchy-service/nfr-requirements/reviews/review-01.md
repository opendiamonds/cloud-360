## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary
本單元以「引用上游代替重寫」的精簡形式交付 nfr-requirements，對安全面與契約閘門的承接是足夠的：安全需求落在 functional-design 的 BR1.x／BR6.x，並額外給出四項可驗證的 NFR（NFR4.1／5.1／5.2／7.1／8.1）。但「效能不適用」的判定有兩處前提與已落地程式不符：resolve_work_target 實際位在閘道每回合呼叫的路徑上，且列舉規模已非僅限擁有者自有的專案。另有數處引用行號漂移與重複章節標題，皆不阻擋。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/hierarchy-service/nfr-requirements/performance-requirements.md 一、二；nfr-requirements/traceability.json 的 NFR3 列 | 判定「本單元不在 NFR3（首字延遲）的串流路徑上」與程式矛盾：backend/services/brain_gateway.py:600-604 的 resolve_work_target 由閘道呼叫並每次開 DB session 後委派 facade，functional-design 亦把它定為判定唯一入口（BR1.2）。同步 DB 查詢位於 WebSocket 回合的首字之前，故本單元對 NFR3 有貢獻。程式是對的，產出的「不在路徑上」是錯的。 | 把 NFR3 列由 N/A 改為對 resolve_work_target 設一個可二元判定的延遲預算（或明寫其預算由 U13 分攤的比例），並說明它是同步 DB 讀取；同時在 performance-requirements.md 刪去「同步 CRUD router、不在該路徑上」的敘述。 | New |
| R-02 | Major | nfr-requirements/performance-requirements.md 一；observability-requirements.md 三；scalability-requirements.md | 規模前提「列舉只限 ownerUserId 等於請求者、量級為個位數」已不成立：backend/services/hierarchy_service.py:238 有 list_projects_by_ids，membership_facade 亦以成員範圍列舉。「個位數」沒有來源、不是可量的判準；失效觸發條件寫的是「變成全體使用者的專案數」，但成員可見範圍這個已發生的變化並未列入。 | 將規模前提改為「擁有或受邀的專案數」並給出上限假設與其來源；把成員範圍列舉納入觸發重開條件；列舉端點補一個有數字的延遲或筆數判準。 | New |
| R-03 | Minor | nfr-requirements/security-requirements.md 四（NFR7.1）；traceability.json NFR7.1 列 | 引用 schema_rbac.sql:416／:418 逐字內容不符：這兩行實為 requirement_summary 等欄位定義，diagram_change_records 的註解在 :433-437（含 "read source before presenting anything (BR3.1)"）。事實存在、定位錯誤。 | 改正為實際行號，並重核同檔其他 file:line 引用。 | New |
| R-04 | Minor | nfr-requirements/security-requirements.md 四（NFR5.2）；traceability.json NFR5.2 列 | 以 unit-of-work.md:447 作為 409 必須顯式宣告的依據；該行是 U19 的列而非 U7 的列。論點對 U7 的四條衝突型規則仍成立，但歸屬應說明是借用 U19 的實測，並指名 U7 自己的端點與 BR 編號對應。 | 補一句「借用 U19 列的實測」，並列出 U7 端點與 409 規則（BR3.2／BR4.2／BR4.3／BR4.4）的對照。 | New |
| R-05 | Minor | nfr-requirements/observability-requirements.md；performance／reliability／scalability-requirements.md | 四檔皆有重複的「二、為什麼本單元沒有這一類需求」整段樣板文字，observability 檔更有兩個「二」節；樣板內容（唯一新增對外網路面等）與可觀測性無關。 | 去除重複樣板，修正節號。 | New |
| R-06 | Minor | nfr-requirements/observability-requirements.md 一 | 判定「無新增監控目標」，但授權拒絕（403）與衝突拒絕（409）是 ADR-0006 稽核面的可觀察事件，本檔把稽核全推給 functional-spec 而未規定拒絕事件是否記 log。該單元已有 logger（hierarchy_service.py:30、hierarchy_facade.py:65），命名義務已滿足。 | 補一條拒絕事件是否記 log、記哪些欄位（不含 token）的需求，或明寫不記並說明理由。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| 抽查 logger 命名 | PASS（兩處皆為 "cloud360.hierarchy_*"） | 沿用義務已落地 |
| 抽查 unit-of-work.md:43／:248／:249 | PASS | embedded、Encryption、Network exposure 引用正確 |
| 抽查 schema_rbac.sql:416／:418 | FAIL | 見 R-03 |
| 逐列 grep 未跳脫 \| 數 | 已自行檢查 | 每列 7 個分隔符 |
