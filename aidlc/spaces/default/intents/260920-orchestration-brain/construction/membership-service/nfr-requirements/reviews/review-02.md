## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U19 membership-service 的 nfr-requirements 七份產出自洽度高：29 條 NFR12.x 無跳號、每條有二元判準，[N1]=A（鎖父 projects 列）、[N2]=A、[N3]=C 的取捨寫得具體，且 SQLite 會靜默丟掉 with_for_update 的發現已被後續程式採納（membership_service.py:164-176 的 docstring 與 backend/tests_pg 的真實 PostgreSQL 併發測試）。前次 review-01 的三項發現（Critical 一項、Major 兩項）在凍結的產出裡全部仍在：NFR12.18 的前提仍是錯的、Network exposure 一格仍與 functional-spec 不一致、NFR12.14 仍未寫出對 FK 缺席的依賴。但實查後三者都已被下游站與程式吸收，故本輪降級重列：nfr-design 以 [ND1]=A 承接建立路徑（reliability-design.md 第二節），程式有 create_project_nocommit（hierarchy_service.py:104-143），schema_rbac.sql:675 的表 COMMENT 確認 reselection_events 刻意無 FK，security-design.md:115-122 已更正 Network exposure。另有本輪新發現的一項需求面缺口：多專案取鎖順序與死鎖在本站完全沒有 NFR，程式在 nfr-design 之後才補上 lock_projects_in_id_order。Critical 零項、Major 兩項，判 READY；兩項 Major 都請在關卡上由人裁決是否接受。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | nfr-requirements/reliability-requirements.md 第一節 NFR12.18 與第三節；functional-spec.md 風險 7 | 前次 review-01 R-01（原 Critical）已提：NFR12.18 把新建專案不再零成員當成自動成立，但建立專案的寫入端是 U7 的 create_project，原本只 commit 專案、不寫 project_members，本站四份產出沿用的前提（唯一寫入端是一次性遷移）是錯的，也沒有任何 OPEN 項登記。實查現況：nfr-design 以 [ND1]=A 承接，程式端 backend/services/hierarchy_service.py:104-156 新增 create_project_nocommit 讓兩個寫入同交易。故設計與程式的矛盾已消除，正確的一邊是下游與程式；但凍結的 nfr-requirements 本身仍把 NFR12.18 寫成沒有實現者的承諾，且其二元判準（不存在零成員專案）與括號限定互相拉扯。降為 Major 的理由是缺口已有下游承接，而非產出本身修好。 | 在關卡上註明 NFR12.18 的有效定義以 nfr-design 的 reliability-design.md 與 [ND1]=A 為準；若要修產出，補一條指名 U7 為寫入端的 OPEN 項。 | New |
| R-02 | Major | nfr-requirements/performance-requirements.md 第三節（不設鎖等待逾時）；scalability-requirements.md 第一節 NFR12.13；security-requirements.md 第一節 NFR12.1 | 全站沒有任何一條 NFR 涉及多專案取鎖順序、死鎖或鎖逾時。NFR12.1 與 NFR12.13 只描述單一專案單一把鎖；但自動改選發生在停用某位 owner 時，一位使用者可能是多個專案的 owner，需一次鎖多個 projects 列，兩個並行停用或停用加邀請的交叉順序會死鎖。這個缺口是下游才補的：membership_service.py 已有 lock_projects_in_id_order，其 docstring 自承死鎖軌跡為上游未涵蓋、由 nfr-design 推導。此為 repo 第一個列鎖，死鎖與無逾時的長等待（持有連線池連線）正是會無聲退化的類型，卻只在 performance 第三節被當作不需要而略過。程式比需求完整，正確的一邊是程式。 | 補一條可判定的 NFR：多專案取鎖一律按 projects.id 遞增、不得出現反向順序，並以真實 PostgreSQL 的併發測試覆蓋；另決定是否設 lock_timeout 或明寫為何不設。 | New |
| R-03 | Minor | nfr-requirements/security-requirements.md 第三節（ADR-0006 表，Network exposure 列） | 前次 review-01 R-02 已提：該列寫無新增暴露面，與同單元 functional-spec.md 第八節判定適用、有落點（新 HTTP 端點、既有端點契約擴充）不一致且未揭露。nfr-design/security-design.md:115-122 已明文更正並加上 [ND1]=A 的第三項，故下游已修；凍結產出仍未動。 | 在關卡註記以 security-design.md 的判定為準，不需再改本站產出。 | New |
| R-04 | Minor | nfr-requirements/scalability-requirements.md 第二節 NFR12.14 | 前次 review-01 R-03 已提：永久保留稽核的前提是 reselection_events 沒有指向 projects 的外鍵，但本站四份產出沒寫出這個依賴。實查 schema_rbac.sql:675 的 COMMENT 逐字寫明刻意不設 FK 以讓稽核比專案活得久，故前提在落地的 DDL 成立；唯獨不同單元的 K-15 契約文字是否仍寫外鍵，請由 contract 持有者確認。 | 在產出或 OPEN 項補一句：NFR12.14 依賴 reselection_events 無 FK，並引用 schema_rbac.sql 的表 COMMENT。 | New |
| R-05 | Minor | nfr-requirements/observability-requirements.md 第二節 NFR12.27 | 二元判準寫成該 log 點存在，但條件是等待若發生，沒有定義多久算等待，無法判定通過與否。程式自行選了 LOCK_WAIT_WARN_MS = 250.0（membership_service.py:98），這個數字沒有來源也沒有進入需求。 | 在 NFR12.27 補上門檻值與其依據，或明寫門檻由 nfr-design 決定。 | New |
| R-06 | Minor | nfr-requirements/traceability.json open_items 的 OPEN-N19-1；inception/requirements/ 下 requirements.md | OPEN-N19-1 把回補 NFR12 parent 指派給 code-generation，但 code-generation 不改已核可的 requirements.md；實查 inception 目錄全樹對 NFR12 零命中，所以 29 條 NFR12.x 到現在仍沒有上游 parent，指派已落空。 | 由人裁決：回跳 requirements-analysis 補 NFR12，或在關卡明確接受它是本單元自帶的 NFR。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 本站未列驗證工具；以 grep 與直接讀檔核對 | NFR12.1 至 NFR12.29 全部出現且無跳號；backend 內 with_for_update 現已落在 membership_service.py:179；reselection_events 在 schema_rbac.sql:640-675 無 FK；inception 目錄對 NFR12 零命中 | 支持 R-06 與 R-04 的結論，並證實 R-01 與 R-03 的缺口已被下游吸收 |
