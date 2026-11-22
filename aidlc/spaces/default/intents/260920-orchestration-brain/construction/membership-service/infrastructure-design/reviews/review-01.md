## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-07T07:40:00Z
**Iteration:** 1

### 覆蓋範圍

本輪為 advisory、僅此一輪。以下逐項交代實際查了什麼、查到什麼結果，以及哪些完全沒查。

**(a) `ut` 的 branch protection 與 `[ID1]`=A 的核心理由是否經得起自己查出的事實**
已查。`gh api repos/opendiamonds/cloud-360/branches/ut/protection` 回應中 `required_status_checks` 這個 key **不存在**；`branches/main/protection` 只有一條（`Repository contract`，`app_id: 15368`）；`gh api repos/opendiamonds/cloud-360/rulesets` 回應 `[]`。三項與產出逐字宣稱完全一致。據此推論：選 A 而非 C 的理由（「覆蓋面不可能靜默消失」）在 branch protection 不存在的情況下，實際效力窄化為「一個會變紅、容易被人看到的 check」，而不是「不可被繞過的硬閘門」——因為紅燈本身不擋合併。產出已以 `OPEN-ID19-6` 自行揭露此事並正確判定為 repo 層設定、非本 stage 可定，但首次在 `cicd-pipeline.md §二.1` 寫下「覆蓋面不可能靜默消失」時沒有就地加註限定詞，見 R-02。A 與 C 的相對優勢（紅燈可視 vs. skip 與 pass 在輸出上無法分辨）本身仍然成立，不受此影響。

**(b) `Base.metadata.create_all()` 與兩條建表路徑是否為真**
已查。`backend/database.py:90` 確有 `Base.metadata.create_all(bind=engine)`；`backend/main.py:51-59` 的 `@app.on_event("startup")` 確實呼叫 `init_db()`。`backend/models.py` 的 `Project.__table_args__` 上方確有產出引用的那段「約束必須與 DDL 逐條對齊」註解（逐字核對，產出為摘述但語意一致）。`backend/tests/test_hierarchy_service.py` 的 `T25`（`test_T25_orm_columns_match_the_authoritative_ddl`）確實只比對 `{c.name for c in model.__table__.columns}`。機制屬實，非本站編造的風險。

**(c) 十一列對齊清單逐列核對 `schema_rbac.sql` 的 `J)` 區塊**
已查，逐行開檔核對（`schema_rbac.sql:556-637`）。十一列全部準確：`ON DELETE CASCADE`、`user_id` 無 `ON DELETE`、`invited_by` nullable、`ck_project_members_role`、`uq_project_members_project_user`、刻意無額外索引、`reselection_events.project_id` 刻意無外鍵、`ix_reselection_events_unack` 為 partial、`ix_reselection_events_project_id` 為一般索引、`previous_role`/`new_role` 刻意無 CHECK、兩表皆有完整 COMMENT。另查 `backend/scripts/verify_meta_schema.sql`：`obj_description` 僅出現一次（:191），且確實只驗 `system_requirement_fields`（對應 `P12`）——`project_members`／`reselection_events` 的 COMMENT 確實無任何斷言，`OPEN-ID19-1` 屬實。同時查了 `memory-schema` job 的 `P6`／`P8`：它們確實驗「`reselection_events` 不得對 `projects` 設外鍵」與「partial index」——但這個 job 全程走 `psql -f schema_rbac.sql`（`.github/workflows/ci.yml:344-348` 起），從未經過 `Base.metadata.create_all()` 路徑，故產出的「P 斷言驗的是 `schema_rbac.sql` 建的表，看不到 ORM 路徑」這句話查證為真，不是自相矛盾。

**(d) 全部可計算數字重算**
已查，全部吻合：`backend/tests/` 恰 51 個測試檔；匯入 `tests.helpers` 的三種寫法恰為 10／20／2（合 29）；`ci.yml` 恰 6 個 job，除 `gate` 外 5 個全部且僅 `needs: gate`；`backend` job 的兩個早期步驟確有 `DATABASE_URL`、「Run unit tests」步驟確**無** `DATABASE_URL`（僅 `JWT_SECRET`），與產出「該 job 的測試步驟只設 `JWT_SECRET`」逐字相符；`openapi.json` 以 `python3` 重新解析得 47 paths／62 operations／`{200:56,201:3,204:3,404:1,409:4,422:51}`，409 恰好宣告在 `POST /api/hierarchy/projects`、`DELETE /api/hierarchy/projects/{project_id}`、`POST /api/hierarchy/projects/{project_id}/systems`、`DELETE /api/hierarchy/systems/{system_id}` 四處，與產出逐字相符。另跑了引擎的 `aidlc-sensor-traceability.ts` 與 `aidlc-sensor-upstream-coverage.ts`：前者對 `traceability.json` 回 `pass:true, findings_count:0`；後者對三份 `.md` 分別以 `--consumes` 餵全部九個上游 artifact、`--deliverables` 餵四個本站產出，三次呼叫均 `pass:true, unreferenced:[]`。

**(e) 部署視窗論證（`hierarchy_facade.list_projects` owner-scoped；`assertCanDeactivate` 的 `HAVING count(*)=1` 在零成員列時放行）**
部分查。`backend/services/hierarchy_facade.py:231-236` 的 `list_projects` 確實 `owner_user_id=principal.user_id`，owner-scoped 為真。但 `assertCanDeactivate` 本身**尚未落地**（`grep` 全 `backend/` 僅命中兩處散文提及，無函式定義）——它是本單元待在 `code-generation` 才寫出的方法。產出在兩處使用「本站實查」描述其零成員列時的行為，但這其實是從 `nfr-design/performance-design.md §二`（`GROUP BY project_id HAVING count(*) = 1`，查詢對象限定在「該使用者具 `project_admin` 的專案」子查詢內）**推導**出來的，不是對已存在程式的實際執行驗證。我核對了該 SQL 形狀：若某使用者在某專案零成員列，則內層子查詢對該專案不回傳任何列，外層 `GROUP BY ... HAVING` 自然找不到該專案，故「不擋」的方向判斷正確——結論成立，但「實查」一詞對尚不存在的函式是用詞過當，見 R-01。

**(f) 本站自己沒抓到的缺口**
部分查，未窮盡。確認本站自檢 2（契約端點三問）只對「四個 log 事件名」跑過一次並得出 `OPEN-ID19-7`；我沒有時間對產出內其他候選契約端點（例如 `DATABASE_URL` 字串本身、`concurrency` job 的 `timeout-minutes` 值）系統性重跑同一套三問。就我查到的範圍，`DATABASE_URL` 的格式與既有兩個 step 逐字相同且有明確擁有者（job 層 env），不構成同類缺口。**未窮盡此項，不代表已排除其他未發現的孤兒契約。**

**(g) 範疇紀律（是否夾帶 code-generation 等級的實作細節）**
僅做了輕量檢查：四份受審檔案中唯一的程式碼圍欄區塊落在 *不受審* 的 `infrastructure-design-questions.md`（裸 SQL 編譯結果示例，屬問題檔的查證記錄，非設計產出）。四份受審文件本身沒有任何 fenced code block，全部以表格與散文呈現，與 stage 檔「≤15 行示意程式碼」的限制沒有衝突。**未逐句檢查是否有隱藏的完整 YAML／IAM policy 等級內容**；就目視掃過的範圍，`cicd-pipeline.md` 的 job 形狀全部以表格呈現參數（image、env、timeout 等），未見到可直接貼上即跑的完整 workflow YAML。

**完全未查的項目**：`frontend/src` 對 `projects` 的命中數宣稱為 0（本單元無前端面的佐證）未獨立複驗；`LOCAL-DEV.md` 對 `project_members`／`reselection_events`／`run_meta_schema_migration` 命中數為 0 的宣稱未獨立複驗；`DEPLOY.md §2.2.9` 現有欄位數（「8 欄」）未開檔核對；`tests_pg/` 套件實際如何把 `backend/`、`backend/services/` 掛上 `sys.path`（`cd backend && python -m unittest discover -s tests_pg` 在沒有專屬 `helpers` 模組時是否真的能 `import models`）未驗證，但判定這屬於 code-generation 的實作細節，不要求在本設計層落地。

### 發現

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `cicd-pipeline.md §五之三` 與 `infrastructure-specification.md §五之一`（「本站實查」字樣用於 `assertCanDeactivate` 的零成員列行為） | `assertCanDeactivate` 尚未落地（`code-generation` 才寫），本站對它「不取鎖時零成員列會放行」的結論是從 `nfr-design/performance-design.md` 已發布的 `HAVING count(*) = 1` SQL 形狀**推導**出來的，不是對既有程式的實際執行驗證。推導過程本身正確（已覆核：內層子查詢在零成員列時回空集合，外層自然找不到該專案），但「實查」一詞會讓讀者誤以為已有可執行測試證實這件事。 | 把兩處「本站實查」改為「本站依 `performance-design.md §二` 的查詢形狀推導」或同義措辭，結論與引用不必改動。 | New |
| R-02 | Minor | `cicd-pipeline.md §二.1`（`[ID1]`=A 選項表「覆蓋面不可能靜默消失」一句） | 該句首次出現時未加限定詞，而本站自己在 §一之二／`OPEN-ID19-6` 查出 `ut` 無任何必要狀態檢查——紅燈不擋合併。A 相對 C 的優勢（紅燈可視、不會把 skip 與 pass 混為一談）仍然成立且是真實優勢，但「不可能靜默消失」若脫離上下文單讀，會被誤解為「保證被擋」而非「保證對看 PR 的人可見」。 | 在該表格該句後加註「——對照 PR checks 的人可見，`ut` 目前無任何必要狀態檢查不擋合併，見 `OPEN-ID19-6`」，把限定詞提前到第一次宣稱的位置，不必等到 §一之二 才揭露。 | New |

### 摘要

- `new-design-problem`：0
- `pre-existing-unreviewed`：0
- `propagated-from-upstream`：0
- 本輪兩項發現（R-01、R-02）皆為同一類：**用詞精確度**問題，不影響結論或設計決定本身的正確性，分類介於以上三類之外，記為用詞層級的 Minor。

本站產出的查證密度異常高：十一項 DDL 對齊清單逐行核對無誤、`verify_meta_schema.sql` 的斷言射程判定無誤、branch protection 的 `gh api` 查證可重現、`openapi.json` 的 47/62/狀態碼分佈與 409 端點清單可重現、`ci.yml` 的 job 圖與 `DATABASE_URL` 掛載位置可重現、`backend/tests/` 的 51/29(10+20+2) 可重現。我沒有找到任何一項可計算或可查證的事實性宣稱是錯的。兩項發現都是用詞準確度而非設計缺陷，且都有明確、低成本的修法。零 Critical、零 Major、兩個 Minor，遠低於 READY 門檻（≤2 Major）。

本審查覆蓋範圍為**部分而非窮盡**（見上方「完全未查的項目」），但在實際查過的每一項上，產出都通過了逐字與逐行的對抗式核對；沒有理由相信未查項目會改變這個結論的方向。

VERDICT: READY
