## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-06T23:59:40Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `scalability-design.md` §三／`reliability-design.md` §四（NFR12.14 的「永久保留」設計）／承接自 `functional-design` 的審查 `R-01`（Critical，仍為 `New`）與 `nfr-requirements` 的審查 `R-03`（Major，要求本單元明寫這個依賴） | `functional-design` 的 `entities.md`／`functional-spec.md`（本單元，同站可查）反覆宣告 `reselection_events.project_id` **對 `projects` 刻意不設外鍵**，但本案被授權查核的共享契約 `inception/contract-design/contract-summary.md` 的 `K-15` 逐字宣告 `"reselection_events.project_id → projects.id"`，**沒有任何例外**——這正是 `functional-design` 審查 `R-01`（Critical）指出、至今仍是 `New` 狀態、未見任何處置記錄的矛盾。`nfr-requirements` 的審查 `R-03`（Major）進一步要求：本單元必須在 `scalability-requirements.md` 或 `traceability.json` 明寫 `NFR12.14`（「只增不減、永久保留」）依賴這個矛盾以「無外鍵／不級聯」收斂，若最終定案為有外鍵且會級聯刪除，`NFR12.14` 必須重新評估。經查證，`nfr-requirements` 的四份產出對「外鍵」「FK」「cascade」「R-01」零命中（未履行該要求），而本站（`nfr-design`）六份產出同樣零命中——`reliability-design.md` §四把「備份／復原」與永久保留的稽核事件寫成既定事實，`scalability-design.md` §三把 `reselection_events` 的成長模型建立在「只增不減」之上，兩者都**完全沒有揭露**它們依賴一個仍未解決、分類為 Critical 的上游契約矛盾。本站對照 `schema_rbac.sql:592-598` 的實際 DDL（確實無外鍵子句，且有一行逐字「`[ND1]=A：刻意不對 projects 設外鍵`」的註解），與 `functional-design` 的立場一致、與 `K-15` 不一致——但這個「哪一份對」的裁決從未在任何站被記錄，本站只是沿用了一方而對矛盾本身保持沉默，連續第二站落空同一個被明文要求的揭露義務。 | 在 `scalability-design.md` 或 `traceability.json` 補上一條，明寫 `NFR12.14`／本站的「永久保留、不設計歸檔」依賴 `functional-design` 審查 `R-01` 以「`reselection_events` 確無外鍵」收斂；若裁決結果相反（`K-15` 為準，且外鍵帶 `ON DELETE CASCADE`），本站的設計需重新評估（例如改為 `ON DELETE SET NULL` 或刪除專案前封存事件列）。在裁決落地前，不應視本站對 `NFR12.14` 的設計為已站穩。 | New |
| R-02 | Major | `security-design.md` §三之二／`nfr-design-questions.md`（作答後更正段） | 本站在更正 `[ND1]`=A 的代價描述時，提出一項「好消息」：移動建立專案端點會改到 `openapi.json` 的 path，而**漂移閘門對 path 變更有效**（對 `BR6.2` 的「新增 409 狀態碼」無效，因為「該檔的 55 個 operation 宣告的狀態碼只有 `{200, 422, 201, 204}`」，是狀態碼層級而非 path 層級的盲區）。**經直接開檔核對，這個支撐數字是錯的**：`openapi.json` 當前共有 **4 處**明確宣告的 `"409":` 回應（其中之一正是 `/api/hierarchy/projects` 的 `post`，即本案 `[ND1]`=A 要搬動的那個端點本身，描述文字為「衝突：名稱重複、預設組不可刪除，或底下仍有系統／架構圖」）與 **1 處** `"404":`，`"responses": {` 的出現次數為 62 非 55。這個「{200,422,201,204}，非 2xx/422 宣告數為 0」的計數最早見於 `functional-design/rules.md` 的 `BR6.2`，本站沿用並在此基礎上新增了一個推論（「故本變更會被 CI 機械抓到」），但**沒有重新核對這個數字**——而本站在同一份文件的其他地方（§3.2 的 `frontend/src` 命中數、`AdminPage.tsx:163`）都示範了「作答後實地查證」的紀律，這一處卻沒有做。底層的架構論點（FastAPI 的 `openapi()` 不會自動把「未在 `responses=` 宣告但程式碼確實會 raise」的狀態碼放進 schema，故遺漏宣告不會被 `dump_openapi.py --check` 的全文比對抓到）在技術上仍可成立，但用來支撐它的具體數字——以及由此導出的「55 個 operation 全部只有 4 種狀態碼」這個印象——是假的，而這正是 `project.md` 反覆記載、本 intent 自身屢次犯過的「可以被計算的數字先算再寫」失誤的同一形狀。 | 更正 `security-design.md` §三之二（與上游 `functional-design/rules.md` `BR6.2` 的 `violation_behaviour`，若在本次送審範圍內可觸及）的狀態碼計數：`openapi.json` 現況為 `409` 出現 4 次（含建立專案端點自身）、`404` 出現 1 次、`200` 56 次、`422` 51 次、`201`／`204` 各 3 次，`"responses": {` 62 次。保留「遺漏 `responses=` 宣告不會觸發漂移檢查」這一核心論點，但不得用一個與現有檔案內容相反的計數去支撐它。 | New |
| R-03 | Minor | `logical-components.md` §三之一（跨單元鎖互動表） | 表格只列 `U7` 的三個操作（`list_projects`／`create_project`／`delete_project`）與本單元鎖的互動，但 `hierarchy_service.py` 另有三個同樣讀取 `projects` 表的函式（`assert_project_owned_by`、`project_exists`、`get_project_owner`，皆為唯讀 `SELECT`，無 `FOR UPDATE`）未被列入。這三者的結論與已列的 `list_projects` 相同（唯讀不受 `FOR UPDATE` 阻塞），故不影響本節的任何結論，但表格宣稱覆蓋「`U7` 的操作」卻只窮舉了寫入類與唯讀類各一個代表，不是全部。 | 可選擇在表格下方加一行概括「`U7` 的其餘唯讀查詢（`assert_project_owned_by`／`project_exists`／`get_project_owner`）同 `list_projects`，不受影響」，使覆蓋聲明與實際列舉的範圍一致；不影響本站任何設計結論。 | New |

### Validation Tool Results

No validation tooling is listed for this stage in the dispatch brief. Verification performed by direct inspection, respecting the "no Python/no test suite" constraint:
- `grep`／`sed -n` 直讀 `backend/services/hierarchy_service.py`：確認 `create_project`（`:98`–`:118`，`db.add` 於 `:117`、`db.commit()` 於 `:118`）、`delete_project`（`:147`–`:163`）、`list_projects`（`:193`–`:199`）的實際行為，與 `security-design.md`／`reliability-design.md`／`logical-components.md` 的引用一致（除 R-03 指出的覆蓋不完整）。
- `grep -rn with_for_update backend/`：零命中，確認「本單元是唯一使用者」的宣稱。
- `grep` `schema_rbac.sql` 的 `project_members`／`reselection_events` 區塊：確認 `uq_project_members_project_user (project_id, user_id)` 為唯一索引且**不含** `role`（支持 `OPEN-ND19-3`）；確認 `ix_reselection_events_unack` 為 **partial**（`WHERE acknowledged_at IS NULL`）且另一索引只含 `project_id`（支持 `OPEN-ND19-4`：`WHERE promoted_user_id = ? ORDER BY occurred_at DESC` 確實無覆蓋索引）；確認 DDL **無**對 `projects` 的外鍵子句，且有明文「`[ND1]=A：刻意不對 projects 設外鍵`」的註解（與 `functional-design` 立場一致、與 `K-15` 文字不一致，見 R-01）。
- `grep -n '"[0-9]{3}": {'` 與逐一開檔核對 `openapi.json` 的 `/api/hierarchy/projects`：確認 `get`／`post` 存在，`post` 含 `201`／`409`／`422`；全檔狀態碼計數與 `security-design.md` 的「{200,422,201,204}」宣稱不符（見 R-02）。
- `grep -rln "projects" frontend/src`：零命中，確認「本輪新建端點零前端消費端」的宣稱為真。
- `sed -n` 直讀 `frontend/src/pages/AdminPage.tsx:155`–`170`：確認 `:163` 呼叫 `/api/auth/<id>/active`（停用端點），印證 `BR6.4` 真正適用於停用端點而非建立端點這一判斷。
- 直讀 `nfr-requirements/reviews/review-01.md`（本單元同站產出）：確認其 R-01／R-02／R-03 的原文內容，並以此為基準核對本站（`nfr-design`）六份產出的回應（R-01、R-02 已處置且有揭露；R-03 未被提及，見本審查 R-01）。
- 直讀 `functional-design/reviews/review-01.md` 與 `functional-design/entities.md`／`functional-spec.md`（本單元同站產出，依共享契約 `K-15` 的指向開啟，非跨單元瀏覽）：確認 R-01（外鍵矛盾）的原文仍為 `New`，且下游產出未見處置記錄。

### Summary

本站（`nfr-design`）在它自己選定的設計面上扎實：死鎖軌跡推導正確、`projects.id` 遞增排序是標準且必要的防死鎖手法、`SELECT ... FOR UPDATE` 配 `IN (...)` 不保證取鎖順序的技術判斷準確、`[ND1]`=A 的交易邊界缺口（`OPEN-ND19-5`）與跨單元鎖阻塞（`OPEN-ND19-9`）都是本站自行查出且未見於上游的真實發現，兩個「不加索引」的決定（`OPEN-ND19-3`／`OPEN-ND19-4`）背後的查證（索引不含 `role`；`unack` 索引為 partial）也都核對無誤。但本站繼承了一個被上游審查明確標記為「必須揭露此依賴」的義務（`reselection_events` 是否真有指向 `projects` 的外鍵，直接決定 `NFR12.14` 的「永久保留」設計是否站得住）卻完全沒有履行，且本站自己提出的一項「好消息」（CI 的 OpenAPI 漂移閘門對狀態碼變更無效）所引用的具體計數與現有 `openapi.json` 的實際內容相反。兩者都是 Major；沒有 Critical，且 Major 數在閘值內，故判定 READY，但這兩項在核可前值得人工權衡。
