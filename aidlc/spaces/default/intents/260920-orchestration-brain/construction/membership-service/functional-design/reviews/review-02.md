## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U19 membership-service 的功能設計在自我稽核、行號重驗、三個定案（FD1/FD2/FD3）上相當扎實，且已落地的程式（membership_service.py、membership_facade.py、user_router.py）與設計大致一致。但設計本身有一個結構性矛盾：[FD1]=A 把停用守門收緊為「最後一位管理者」，使 §2.7 的自動改選在 BR2.1 成立的前提下幾乎不可達（只有不變量已被破壞時才會觸發），AC12.4.1 因此無法端到端滿足，設計與程式皆未揭露。另有兩項前次 review-01 已提、仍留在凍結產出裡的缺口（既有專案回填、三條路徑共用守門函式）。其餘為文件缺口。已落地程式能解決的項目都已逐一標明哪一邊是對的。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Critical | functional-spec.md §2.7／§四／BR2.1／BR4.3／BR4.4；已落地：backend/services/user_router.py:725-756、backend/services/membership_service.py:752-790 | 自動改選在 BR2.1 成立時不可達（本次新查出）。逐步代入：停用端點先呼叫 assert_can_deactivate，守門條件是「被停用者是某專案唯一的 project_admin」則回 409（user_router.py:728-736）；只有守門通過才會寫 is_active 並跑 run_auto_reselection。而 reselect_for_project 的觸發條件是「排除被停用 owner 之後，該專案沒有任何其他 project_admin」（membership_service.py:765-777，即 BR4.3 的冪等檢查）。兩個條件互斥：(a) owner 是唯一管理者 → 被守門擋下，改選不會跑；(b) owner 是管理者且另有管理者 → 冪等檢查命中而跳過；(c) owner 已被降為 member 且另有管理者 → 同樣跳過；(d) 專案沒有任何管理者 → 只有 BR2.1 已被破壞（例如既有專案未回填，見 R-02）時才發生。也就是說 FR12.4 / AC12.4.1 的主情境「owner 帳號被停用，系統把管理權交給最早加入者」在不變量成立時永遠被 409 擋下或被冪等跳過，橫幅（FR12.4c）與 manual/auto 稽核裡的 auto_reselection 列在正常資料下都不會產生。這是 project.md 的 functional-design:c10 規則（先驗證 X 狀態可達）要防的形狀，且 [FD1]=A 的對齊修正（§四）只討論了守門變嚴對 AC12.3.3 字面的影響，沒有檢查它對 AC12.4.1 的影響。設計與程式一致地錯，錯的一邊是設計：FD1 的守門與 FD3/BR4 的改選互相抵銷。 | 在設計層明確裁決兩者的關係並寫入 BR 與 §2.6/§2.7：選項之一是「停用 owner 時，若該專案另有成員，守門不擋、改為先改選再停用」（守門只擋改選也無人可選的情形，即專案只有該 owner 一人）；選項之二是承認改選只服務於不變量被破壞的遺留資料，並下修 AC12.4.1 與 FR12.4 的範圍。不論選哪個，須指派 stories.md 與 requirements.md 的措辭回補，並要求 code-generation 補一條端到端測試：以兩位成員（owner 為唯一管理者）停用 owner，斷言結果（409 或改選成功）與選定規則一致，現況沒有任何測試會抓到這個矛盾。 | New |
| R-02 | Major | functional-spec.md §九 風險清單（缺項）／entities.md ProjectMember.entity_constraints；前次 review-01 R-02 已提 | 既有專案的 project_admin 回填義務在凍結產出裡仍未出現：§九風險 7 只談新建路徑的寫入端，沒有談遷移前已存在的專案其 project_members 為空。K-15 明寫三張表全新、無資料寫入，故 BR2.1 宣稱的不變量在上線當天對全部既有專案為假，且 resolveProjectRole 對這些專案的 owner 也回 None（BR1.6 視為拒絕）。已落地程式其實已補上：backend/scripts/backfill_project_members.py（檔頭引用 K-15 的 observable_side_effects），所以實作這一邊是對的，設計文件這一邊缺漏。該腳本由人手動執行、不是無人值守機制，不違反 project.md 的 scripts 禁令，但上線次序（腳本須在任何消費端上線前跑完）沒有寫進任何功能設計產出。 | 在 functional-spec.md 風險清單新增獨立一項「既有專案回填」，指名 scripts/backfill_project_members.py 為承載者，寫明執行次序與 dry-run 驗證，並與風險 7 分開；同時把它列為 R-01 所述 (d) 情形的來源。 | New |
| R-03 | Major | functional-spec.md §2.4／§2.5／§2.6；前次 review-01 R-03 已提 | BR2.1 要求三條路徑經過同一個守門判定，但凍結的工作流程只讓 §2.4 命名 assertStillHasAdmin，§2.5 changeRole 用散文描述同一條件，§2.6 assertCanDeactivate 是跨專案掃描的另一個簽章，文件沒有說明三者共用什麼。已落地程式的做法是：remove_member 與 change_role 共用 admin_count_after（membership_service.py:382-414），停用路徑用 HAVING count 等於 1 的集合版 projects_losing_last_admin（:416-465），並以 NFR12.11/NFR12.12 的等價測試維繫。這代表實作上仍是兩份實作（單專案版與集合版）靠測試對齊，不是單一函式；設計文件從未交代這個取捨。程式這一邊的做法可接受，缺的是設計層的明文與其可驗證性。 | 在 §2.4-§2.6 補寫共用的單一謂詞名稱（admin_count_after）與集合版的關係，並把等價性測試列為 BR2.1 的驗證項；若要堅持單一函式，改由 assertCanDeactivate 逐專案呼叫同一函式，並評估效能代價。 | New |
| R-04 | Minor | rules.md BR1.x／entities.md ReselectionEvent.projectId／functional-spec.md §六；contract-summary.md:1570 | 前次 review-01 R-01 的事實部分已查清：schema_rbac.sql:636-640 與 :676 的 COMMENT 明確指出 reselection_events.project_id 刻意不設外鍵（[ND1]=A），本單元設計正確；錯的是共享契約 K-15 的 foreign_keys 區塊仍列「reselection_events.project_id → projects.id」。[ND1] 的決定記錄屬 U18，在本單元可查範圍內只能看到 DDL 結果，故本單元對 [ND1] 的引用無法在本站內逐字驗證。 | 在契約層更正 K-15 的 foreign_keys（或加註 ND1 例外）；本單元在 entities.md 補一句「此處以 schema_rbac.sql 為準，K-15 該行已過期」，避免下一位實作者被契約誤導而補上外鍵（那會讓 CASCADE 抹掉稽核）。 | New |
| R-05 | Minor | functional-spec.md §九 風險 5（「20 條 AC 中 19 條 Given 不可構造」）；前次 review-01 R-05 已提 | 數字 19 沒有逐條列舉，且與 stories.md 對 US12.6 的註記（九條）相差一倍，兩者的差異來源（是「無任何成員資料」還是「無第二位成員」）沒有說明。部分 AC（如 AC12.1.1、AC12.1.2、AC12.3.1）看不出需要第二位成員才能構造。這是違反 project.md「可算的數字先算再寫」的文件缺口，不影響實作。 | 逐條列出各 AC 的不可構造原因與解除條件，或改寫成與上游一致的九條並說明其餘為何可構造。 | New |
| R-06 | Minor | traceability.json AC12.3.3 的 target；functional-spec.md §2.7 步驟 2；entities.md MemberSnapshot.role | 三個小缺口：(1) AC12.3.3 的 target 為 BR6.1/BR6.2，沒有 BR2.1，與 AC12.3.1/AC12.3.2 的追溯方式不一致（前次 review-01 R-04 已提，BR6.2 已補、BR2.1 仍缺）；(2) MemberSnapshot.role 在 §2.8 的排序鍵中不被讀取，已落地程式在 reselect_for_project 用它做冪等檢查（membership_service.py:766-770），但 §2.7 步驟 2 與步驟 3 的次序（先檢查冪等、後取快照）沒有接上這條讀取端；(3) changeRole 對「新舊角色相同」的呼叫是否仍寫一列 manual_role_change 稽核，設計未規定，會留下不曾發生變更的紀錄。 | 把 BR2.1 併入 AC12.3.3 的 target；在 §2.7 把冪等檢查改為讀 MemberSnapshot.role 並與步驟 3 對齊；在 BR3.5 或 BR5.1 明文規定相同角色的 changeRole 為無操作且不寫稽核（或寫明寫稽核的理由）。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| 直接比對 schema_rbac.sql（:636-690） | reselection_events 無對 projects 的外鍵、cause 欄含 CHECK | 設計的 [ND1]/[FD3] 與 DDL 一致；contract-summary.md:1570 的 K-15 過期（R-04） |
| 直接閱讀 membership_service.py、user_router.py:720-756 | 停用端點守門先於寫入，改選在寫入之後；改選的前提是無其他管理者 | 兩個條件互斥，確認 R-01 |
| 直接閱讀 scripts/backfill_project_members.py 檔頭 | 回填腳本存在，引用 K-15 | 實作補上了 R-02 的缺口，設計文件仍缺 |
| grep 每列 7 個未跳脫的管線符 | 表格各列符合 | 格式檢查通過 |
