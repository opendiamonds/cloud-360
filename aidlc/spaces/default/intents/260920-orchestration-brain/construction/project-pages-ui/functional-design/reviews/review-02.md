## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-15T22:44:49Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/functional-spec.md > 八 OPEN-PP23-10；aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/rules.md > BR87.6；aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/functional-design-questions.md > PP3 題幹第 7 點 | 既存漏審。OPEN-PP23-10 與 PP3 題幹把被移出建立者的殘留寫成「建立系統、刪除空專案」，低估了爆炸半徑。實測：hierarchy_service.delete_project 只擋 is_default 與底下仍有系統，db.delete(project) 後 schema_rbac.sql:596 的 project_members.project_id 為 ON DELETE CASCADE，整專案的成員列（含仍在的管理者）一併消失；delete_system 只擋 is_default 與有圖歸屬（hierarchy_service.py:195-204），而 OPEN-H11 使新建的圖從未被指派系統，故多數系統可刪，schema_rbac.sql:689 的 system_requirement_fields.system_id 為 ON DELETE CASCADE，其他成員填的需求欄位資料隨之永久消失。這三支只認 owner_user_id（hierarchy_facade.py:213-240），被移出者仍是 owner。使用者是在「刪除空專案」這個描述下回答 PP3=A 的，沒看到級聯破壞需求資料與成員列。另外「剩餘單元沒有一個擁有 U7 的寫入授權」不成立：本單元自己就要新增 HierarchyFacade 與 MembershipFacade 的方法，加一道只用既有 is_project_visible 的守門不需 schema 變更，也不需要 PP3 的選項 C | 改寫 OPEN-PP23-10 與 BR87.6：明寫兩條級聯（刪專案會刪全部成員列；刪系統會刪該系統的需求欄位資料），並在核可關卡摘要以此重新揭露、取得使用者對 PP3=A 殘留的知情確認；同時評估並擇一寫入：(a) 本單元對 create_system、delete_project、delete_system 三支加一道可見性守門（被移出者回 404，沿用 BR87.1 同一個私有謂詞，突變驗證：拿掉守門時被移出擁有者案須紅），或 (b) 明確保留殘留並把落點改成「交 conductor 重新提交」而非「無自然承接站」。無論哪種，BR87.5 或新規則須有對應斷言或明寫不受斷言 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/rules.md > BR86.2 | 新引入。第一輪 R-10 的修法把空態文字改為「你擁有的圖尚無經大腦的變更」，但實作逐系統以 system_id 查詢，而 hierarchy_service.list_diagram_changes 的 docstring 與 hierarchy_router.py:301-306 都寫明 system_id 為空的圖一律查不到（OPEN-H11，新建的圖從未被指派系統）。因此使用者擁有、有經大腦變更、但尚未歸屬系統的圖，會被這句空態文字說成「沒有變更」。標示文字「只含經大腦、且為你自己擁有之圖」同樣沒寫「且已歸屬系統」，OPEN-PP23-2 雖列了「查不到無系統歸屬的圖」，卻沒落到畫面文字，與 R-10 要消除的過度宣稱是同一形狀 | BR86.2 的標示與空態文字都納入「已歸屬系統」限制，例如標示「只含經大腦、已歸屬系統、且為你自己擁有之圖的變更」，空態改為「沒有符合條件的變更紀錄」之類不宣稱絕對無的文字；traceability 或 e2e 備註補上此限制 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/rules.md > BR87.5 | 新設計問題。五種身分與 M1 至 M4 已能抓住 PP3 的推論，但有兩處空洞：③「非擁有者亦非成員」沒要求該使用者是另一個專案的成員，故可見性子句漏寫 project_id 條件（任何有成員列者皆可見）時，③ 不一定變紅；M1 至 M4 也沒有「拿掉 HierarchyFacade 新方法第一行 K2 判定」的突變，只靠缺 K2 案隱含涵蓋，卻未明指 | ③ 明定構造為「另一專案的成員」並斷言兩支端點；新增突變 M5：拿掉 list_projects_by_ids 或 list_systems_unscoped 第一行的 K2 判定，缺 K2 案（含空集合）須紅 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/rules.md > BR88.3；aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/frontend-components.md > 六 | 新引入。R-11 的暫定預設讓詳情頁的 S 次需求欄位 GET 與 S 次變更紀錄 GET 共用同一個並行 4 的佇列，但只說「依 id 遞增」，沒定兩類請求的先後；變更紀錄若排在前面，需求籤要等 2S 個請求才可用，違反 BR85.1 要求需求籤與總覽讀同一份狀態的初衷。儲存後重讀與 BR85.6 的 [重新整理] 是否進佇列也未寫（§六只說 PUT 不進佇列） | BR88.3 明定優先序（建議：需求欄位先於變更紀錄；使用者目前選取的系統優先），並寫明重讀與 [重新整理] 的 GET 是否繞過佇列 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/project-pages-ui/functional-design/functional-spec.md > 十之一 | 新引入。修訂 1 在 §十之一 留下一個只有表頭與分隔列、沒有資料列的空表，緊接一行散文，再接第二個完整表；渲染時第一個表為空殼，工具解析表格也可能誤判 | 刪除重複的表頭與分隔列，保留散文後的單一表格 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 規則數實算（grep 對 rules.md 的 id 列） | 39 條；各組 4／5／4／7／6／3／7／3；policy 類 4 | 與 spec 十之一一致 |
| traceability 雙向（jq 加 comm） | coverage 指名 13 條、reverse 26 條、聯集 39、與 rules.md id 集合差集為空、無重複 | 無孤兒規則、無缺漏 |
| OPEN-PP23 唯一數（grep -o 加 sort -u） | 原始指令輸出 11，其中一筆是裸前綴 OPEN-PP23-；實際編號 1 至 10 共 10 個 | 與宣稱一致（宣稱用的指令含 [0-9][0-9]*，結果 10） |
| 他單元規則識別字字面掃描 | 四份產出對非 BR81 至 BR88 的 BR 識別字命中為 0 | 符合規定 |
| 上一輪 R-01 至 R-11 逐項複驗 | R-01、R-02、R-03、R-04、R-05、R-06、R-07、R-08、R-09 已修好；R-10、R-11 的修法各引出一個新瑕疵（本輪 R-02、R-04） | 修好的不再列 |
| PP3 推論實測（membership_facade.py、membership_service.py、backfill_project_members.py、hierarchy_migration.py） | 新專案必有建立者成員列（:453-461）；邀請需 project_admin（:243-247）；最後一位管理者不可被移除（:296-300）；成員列僅 remove_member 刪除，project_members.user_id 無 CASCADE；hierarchy_migration 只被一次性腳本呼叫；owner_user_id 無任何改寫路徑；自動改選只改角色 | 「有成員列而擁有者不在其中，只能由擁有者被移出產生」成立；零成員列只出現在回填前或回填後重跑遷移 |
| R-04 可行性實測（membership_facade.py:131、hierarchy_router.py:131-132、hierarchy_facade.py:384-387、tests/test_hierarchy_service.py:130） | HierarchyFacade.project_exists 第一行即 K2 判定，HierarchyForbidden 原樣上拋由既有 _translate 轉 403；_assert_project_exists 確會轉成 MembershipNotFound；T2b 斷言非 canonical role 的系統清單 403 | 設計可行，改走 _assert_project_exists 的確會讓 T2b 紅，BR87.2 與突變 M4 正確 |
| 引用定位抽樣（membership_facade.py:244-246／:296／:455-460、membership_service.py:299／:678-685、hierarchy_facade.py:213-240／:345-357、rbac_seed_data.py:349-359、requirement_field_facade.py:257-264、backfill_project_members.py:18-21／:150-154、DEPLOY.md:867／:894、stories.md:903） | 內容與定位皆相符；K4 view 為真且 edit 為假的角色確為 Developer、FinOps_Analyst、Security_Reviewer、Platform_Owner 四個 | 引用可信 |

### Summary

上一輪十一項大多已確實修好，PP3=A 的推論經實測成立，BR87.1 至 BR87.7 的可見範圍、判定順序、方法定名與 ast 靜態鎖都可實作；主要問題是 OPEN-PP23-10 低估了被移出建立者仍保有的擁有者寫入權：經 ON DELETE CASCADE，他能刪除其他成員的需求欄位資料與整專案的成員列，而使用者是在「刪除空專案」的描述下回答 PP3 的，且本單元既然要改這兩個 facade，「無自然承接站」的說法站不住腳。其餘四項為 Minor。分類計數：新引入 3（R-02、R-04、R-05）、既存漏審 1（R-01）、新設計問題 1（R-03）。
