## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元設計大致自洽：BR87 的可見範圍謂詞單一來源、K2 先行、ast 靜態鎖與五身分雙向測試皆可實作，契約端點三問（fieldsBySystem、drafts、systemsByProject 與四個新 facade 方法）都能指名擁有者與呼叫端，ADR-0006 四面向各有落點。主要問題是凍結的產出仍把「被移出建立者的三支擁有者寫入」記為無承接站的殘留，但已落地的程式（hierarchy_facade.py 的 create_system、delete_project、delete_system）已在擁有者檢查之前加入 project_visible 守門，程式是對的、設計文字過時。其餘為前次 review-02 已提而凍結產出未修的四項 Minor。Critical 0、Major 1、Minor 4。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/functional-spec.md > 八 OPEN-PP23-10 與 九之一 IAM 殘留；rules.md > BR87.6；functional-design-questions.md > PP3 題幹第 7 點 | 前次 review-02 R-01 已提。產出凍結仍把被移出建立者的 create_system、delete_project、delete_system 寫入權記為「本 intent 內無自然承接站」的已知殘留，且描述為「刪除空專案」，低估爆炸半徑：delete_project 後 schema_rbac.sql 的 project_members.project_id 為 ON DELETE CASCADE（約 :596），整專案成員列一併消失；delete_system 後 system_requirement_fields.system_id 為 ON DELETE CASCADE（約 :689），他人填的需求欄位資料永久消失。設計與程式矛盾：已落地的 hierarchy_facade.py:244-300 在三支寫入方法都先 _authorize、再 project_visible 為假回 404、最後才擁有者檢查與 409，註解直引「functional-design R-01 使用者裁決」，hierarchy_router.py:255-320 以 MembershipFacade.project_visibility 注入。程式一側是對的（殘留已被消除），設計文字（OPEN-PP23-10、IAM 列殘留、PP3 題幹描述）已過時，會讓後續讀者以為仍有授權缺口並錯誤重開 PP3 選項 C | 在補審關卡的紀錄中註明：OPEN-PP23-10 已由程式的 project_visible 守門處置（hierarchy_facade.py:244-300），以程式為準，下游文件不得再引用該殘留。若有後續修訂，改寫 OPEN-PP23-10 與 BR87.6，並補明兩條級聯（刪專案刪成員列、刪系統刪需求欄位）作為守門存在的理由 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/rules.md > BR86.2 | 前次 review-02 R-02 已提。標示「只含經大腦、且為你自己擁有之圖的變更」與空態「你擁有的圖尚無經大腦的變更」未寫「已歸屬系統」。依 OPEN-PP23-2 與 OPEN-H11，system_id 為空的圖一律查不到，故有變更但未歸屬系統的圖會被空態說成沒有變更，與 R-10 要消除的過度宣稱同形 | 標示與空態文字納入「已歸屬系統」限制，空態改為不宣稱絕對無的措辭；e2e 備註補上此限制 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/rules.md > BR87.5 | 前次 review-02 R-03 已提。身分③「非擁有者亦非成員」未要求構造為另一專案的成員，可見性子句漏寫 project_id 條件時③不一定變紅；突變 M1 至 M4 沒有「拿掉 list_projects_by_ids 或 list_systems_unscoped 第一行 K2 判定」的 M5，只靠缺 K2 案隱含涵蓋 | ③ 明定構造為另一專案的成員並斷言兩支端點；新增 M5：拿掉兩支新方法第一行 K2 判定，缺 K2 案（含可見集合為空）須紅 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/rules.md > BR88.3；frontend-components.md > 六 | 前次 review-02 R-04 已提。詳情頁的 S 次需求欄位 GET 與 S 次變更紀錄 GET 共用並行 4 的佇列，只寫依 id 遞增，未定兩類請求先後；變更紀錄排前會讓需求籤多等約 2S 個請求，違背 BR85.1 的初衷。儲存後重讀與 BR85.6 的重新整理是否進佇列也未寫 | BR88.3 明定優先序（需求欄位先於變更紀錄、目前選取的系統優先），並寫明重讀與重新整理的 GET 是否繞過佇列 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/functional-spec.md > 十之一 | 前次 review-02 R-05 已提，實測仍在（約 :352-358）。§十之一 開頭有一個只有表頭與分隔列、沒有資料列的空表，接一行散文，再接第二個完整表；渲染為空殼，工具解析可能誤判 | 刪除重複的表頭與分隔列，保留散文後的單一表格 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 舊審查複驗（review-01、review-02 對照凍結產出） | review-02 在產出最後編輯（2026-10-16 06:39）之後才寫成（06:45），其 R-01 至 R-05 全數仍存在於產出 | 五項皆為前次已提，列為本審查 R-01 至 R-05 |
| 設計對程式抽查（hierarchy_facade.py:205-300、hierarchy_router.py:255-320、hierarchy_service.py:182-220） | 三支寫入路徑已有 project_visible 守門且早於擁有者檢查與 409；delete_project、delete_system 本身不級聯 | 程式比設計文字更安全，R-01 以程式為準 |
| 級聯 DDL 抽查（schema_rbac.sql 約 :596、:689） | project_members.project_id 與 system_requirement_fields.system_id 均為 ON DELETE CASCADE | 支持 R-01 對爆炸半徑的描述 |
| 新方法呼叫端抽查（membership_facade.py:475-500、hierarchy_facade.py list_projects_by_ids 與 list_systems_unscoped） | 唯一呼叫端為 MembershipFacade，K2 判定在 HierarchyFacade 第一行，與 BR87.2、BR87.3 一致 | 契約端點三問無懸空方法 |
| 測試與建置 | 依 brief 規定未執行 | 結論僅基於讀檔，未獨立重跑測試 |
