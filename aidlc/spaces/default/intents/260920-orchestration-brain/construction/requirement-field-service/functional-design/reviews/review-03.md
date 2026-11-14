## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U20 requirement-field-service 的功能設計大體自洽：授權順序（待核准、全域 K4、系統存在、專案成員）清楚，三態推導對任何列都有定義，契約端點三問（欄位誰寫、誰讀、誰清）可逐一指名，ADR-0006 四面向都有落點，已落地的 requirement_field_facade.py 與設計的授權順序、三態推導、BR42.5 與 BR46.4 的處置一致。這是補審：review-02 的多數發現（BR47.2、BR42.5 依賴呼叫端自律、框架 422 範圍、自檢 5 的舊數字、never_filled 的溯源欄位、契約追認清單）仍留在凍結的產出裡，本輪重新列出。其中只有一項 Major：rules.md 的 BR47.2 要求「既有值一律轉為 null」同時要求「重跑兩次結果相同」，字面互相矛盾。已落地的 schema_rbac.sql 在 726 行起以「只有欄位仍為 integer 時才做任何事」修掉了，所以程式一邊是對的。零 Critical、Major 1 項，判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/requirement-field-service/functional-design/rules.md 的 BR47.2（logic 與 note）；functional-spec.md 的 OPEN-RF20-8 | 前次 review-02 R-01 已提，產出仍未改。BR47.2 同時要求「欄位型別改為 VARCHAR(64)，既有值一律轉為 null」與「重跑兩次結果相同是硬要求」。run_meta_schema_migration.py 會重新執行整個 J) 區塊，若照字面把轉 null 寫成無條件 ALTER，第二次執行會把 facade 已寫入的 agent 組識別字全部清掉且不報錯，那正是 K-17 要保護的代寫溯源資料。已落地的 schema_rbac.sql 在 726 行起註明「只有 updated_on_behalf_of 仍為 integer 時才做任何事」，並於 750 行以 information_schema 判斷型別、769 行查外鍵，所以實作這一邊是對的，設計文字是錯的。 | 把 BR47.2 的收斂敘述改成以欄位目前型別為條件（僅 integer 時才轉型與清值、外鍵以 pg_constraint 查名稱），並把「第二次執行不改變任何已存資料」寫成可驗證的硬要求；或在凍結產出旁以 corrections 檔註明以 schema_rbac.sql 的條件式為準。 | New |
| R-02 | Minor | construction/requirement-field-service/functional-design/rules.md 的 BR42.5（note）；functional-spec.md 的 OPEN-RF20-1 | 前次 review-02 R-03 已提。BR42.5 只在呼叫端帶 on_behalf_of 時才擋空值；省略該標示的 U13 或 U21 呼叫仍走 BR43.2 變成清空，並被記成本人清空。設計沒有把「代寫路徑一律帶 on_behalf_of」寫成 U13 與 U21 的義務，也沒有誠實註明 BR42.5 只保護自報代寫身分的呼叫。已落地的 requirement_field_facade.py 在 360-366 行與設計一致，沒有補這個缺口。 | 在 OPEN-RF20-1 或新開放項指派 U21 的工具 schema 層（空值直接拒絕或強制帶標示）與 U13 承接，並在 BR42.5 的 note 寫明保護範圍。 | New |
| R-03 | Minor | construction/requirement-field-service/functional-design/functional-spec.md 的 2.2 表格；rules.md 的 BR46.4 | 前次 review-02 R-04 已提。BR46.4 只處理 PUT 本體的形狀錯誤；2.2 表中 GET 只宣告 403 與 404，DELETE 與 PUT 宣告 422，而路徑參數 system_id 非整數、超出 int4 範圍的情形設計沒有任何規則。已落地的 requirement_field_router.py 對三個路由一律套 ERROR_RESPONSES（含 422），facade 以 coerce_system_id（requirement_field_facade.py 115-129 行）把非法 system_id 收斂成 404，這兩點都是程式自行補的決定，設計與程式不一致，程式這邊較合理。 | 在 BR46.4 把範圍寫成三個路由的全部非授權錯誤，補一條 system_id 畸形值走 404 的規則，並讓 2.2 表三個路由的 responses 宣告與實作一致。 | New |
| R-04 | Minor | construction/requirement-field-service/functional-design/functional-spec.md 的第九節自檢 5 | 前次 review-02 R-05 已提。自檢 5 寫「規則數 33」，同檔第六節表格與自檢 6 是 37（6＋5＋7＋6＋5＋4＋4），同一份檔內兩處互相矛盾，屬 project.md 反覆記載的改完未重掃衍生計數。 | 改為 37 或刪去該處具體數字。 | New |
| R-05 | Minor | construction/requirement-field-service/functional-design/rules.md 的 BR44.1；functional-spec.md 的 2.3 與 entities.md 的 FieldView | 前次 review-02 R-06 已提。BR44.1 把第四種列（value 與 clearedAt 皆為 null）視為 never_filled，但該列的 updated_at 與 updated_by 為 NOT NULL，設計沒說 FieldView 的 updatedAt、updatedBy、updatedOnBehalfOf 在此情形回列上的值還是回 null。已落地的 build_field_view（requirement_field_facade.py 143-164 行）選擇一律回 null，那是對的選擇，但設計文字未載明，U23 與測試作者無從得知。 | 在 BR44.1 補一句：never_filled 的 FieldView 一律回 null 的溯源欄位（含第四種列），並要求 TestClient 直接插入第四種列驗證。 | New |
| R-06 | Minor | construction/requirement-field-service/functional-design/functional-spec.md 的 2.3 與 OPEN-RF20-5 | 契約追認清單仍不完整，前次 review-02 R-07 已提其中兩項。（a）K-17 的 own_responsibility 與 anti_double_check 兩處字面把全域層歸給 router，OPEN-RF20-5 只提 K-16 的矛盾；（b）K-17 的 returns 用 unfilled_count（snake_case），本單元回應為 unfilledCount；（c）本次補審新發現：已落地的 FieldSetView 多了 input_hint 欄位（requirement_field_facade.py 194-199 行與 requirement_field_definitions.py 40 行，來自 nfr-design 的 security-design），但 functional-spec.md 2.3 的回應形狀與 OPEN-RF20-5 的「四欄增量」都沒有它，U23 從設計文件讀不到這個欄位。 | 把（a）（b）（c）併入 OPEN-RF20-5 的追認清單，並在 2.3 的回應形狀補上 input_hint。 | New |
| R-07 | Minor | construction/requirement-field-service/functional-design/rules.md 的 BR41.6 與 BR45；functional-spec.md 第七節 Audit logging 列 | ADR-0006 audit logging 面的落點只有拒絕 log（BR41.6）與列上的 updatedBy、clearedAt。寫入與清空成功時沒有任何 log 規則，而欄位為單列覆寫，被覆寫的前一個值與前一位寫入者不可回復；代寫標示又可被自填（OPEN-RF20-1）。設計沒有把「只保留最後一位寫入者」記成已知限制。已落地的 facade 在 455-467 行自行加了 requirement_field.written 與 cleared 的 INFO log（來源為 nfr-design），所以實際稽核能力比設計文字強，但功能設計本身沒有這條規則。 | 在 BR45 補一條成功寫入與清空的 log 規則（欄位集合與不含值的限制），並在開放項記載「欄位表只保留最後寫入者、無歷史」為已知限制。 | New |
| R-08 | Minor | construction/requirement-field-service/functional-design/rules.md 的 BR41.3、BR47.4；functional-spec.md 第九節自檢 3 | 設計引用的行號已與目前程式不符：hierarchy_facade.py:374 的 get_project_of_system 現在位於 594 行起；membership_facade.py:93-111 的 _authorize_global 現在位於 98 行起（hierarchy_facade.py 與 membership_facade.py 在設計之後被修改過）。事實（get_project_of_system 不套列範圍、先授權 view；resolve_project_role 無授權檢查、回 None 代表非成員）經抽查仍成立，只有定位過期。 | 凍結產出不必改行號；請在 corrections 或下游引用處改以函式名稱定位，避免日後照行號查證時讀到別的東西。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 規則數計數（rules.md YAML 條目） | 37（BR41 6、BR42 5、BR43 7、BR44 6、BR45 5、BR46 4、BR47 4） | 與第六節表格一致，自檢 5 的 33 為殘留（R-04） |
| 對照 requirement_field_facade.py | 授權順序、coerce_system_id、三態推導、BR42.5、BR46.4（授權後才解析本體）與設計一致；never_filled 溯源欄位回 null、input_hint、成功寫入 log 為程式自行補的決定 | 支撐 R-02、R-03、R-05、R-06、R-07 |
| 對照 schema_rbac.sql 的 updated_on_behalf_of（576、705、726-806 行） | 欄位為 VARCHAR(64)，收斂區塊以 information_schema 判斷僅在 integer 時才轉型 | 實作已避開 BR47.2 的矛盾，設計文字仍錯（R-01） |
| 對照 hierarchy_facade.py 與 membership_facade.py 的跨單元整合點 | get_project_of_system 與 resolve_project_role 存在且形狀吻合；行號已漂移 | 整合點成立，僅定位過期（R-08） |
| 範圍限制 | 未開啟其他單元的 construction 目錄，只抽查設計點名的兩個整合點 | 符合審查範圍 |
