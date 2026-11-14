## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U19 membership-service 的 infrastructure-design 產出自洽，且與已落地的程式高度吻合。我抽查了 `ci.yml` 的 `concurrency` job（`:545`–`:626`，timeout 15 分鐘、`DATABASE_URL` 帶 `+psycopg`、結構性隔離的 `tests_pg`）、`models.py` 的兩張 ORM model、`schema_rbac.sql` 的 `cause` 欄、`DEPLOY.md §2.2.10`、`LOCAL-DEV.md` 的 `tests_pg` 小節、`test_membership_data.py` 的 M1 到 M4 和 M8，全部與設計主張一致，設計提出的補強也已實作。本輪沒有 Critical，有 2 項 Major（恰在 READY 門檻內）：一項是設計的部署窗口論證已被後續單元 U23 推翻，二項是資料庫連線池與鎖等待的基礎設施缺口。其餘為 Minor。前次 review-01 與 review-02（兩檔內容完全相同）提出的 R-01、R-02 兩項用詞問題仍留在凍結的產出裡，本輪不再重列。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | `construction/membership-service/infrastructure-design/infrastructure-specification.md` §5.1 表第 1 列，以及 `cicd-pipeline.md` §五之三「窗口的實際風險」列 | 設計寫「第一次部署不會鎖人在外」，依據是「`hierarchy_facade.list_projects` 目前是 owner-scoped，不讀 `project_members`」。這個前提已被 U23 推翻：`backend/models.py` 的 `ProjectMember` 註解寫明「專案清單改讀成員列（`[PP1]`=A、`[PPN1]`=A）」，`DEPLOY.md §2.2.10` 也已自行更正為「`U23` 起不再成立；需求籤與成員頁會拒絕擁有者」。以設計為準的讀者會得出錯誤的風險結論。回填仍是手動步驟，`deploy.yml` 不呼叫任何遷移腳本（`DEPLOY.md` 已自承），而 U23 已合併進分支，所以 `OPEN-ID19-2` 描述的窗口現在是真實存在的，不再是假設。**哪一邊對**：`DEPLOY.md` 與程式是對的，設計的 §5.1 與 §五之三 已過期。 | 在關卡上告知人：此窗口論證已過期，以 `DEPLOY.md §2.2.10` 為準。請 delivery-planning 或 build-and-test 確認「回填已在 staging 執行」確實是 U23 所在批次的前置條件，並指定一個可機械檢查的落點。至少要有部署後驗證指令的執行紀錄，因為目前沒有任何閘門擋住「程式已上線而回填未跑」。 | New |
| R-02 | Major | `infrastructure-specification.md` §三 PostgreSQL 列（「不改連線池」）與 §二「資源配額」列；對照 `backend/database.py:37` | 本單元是 repo 內第一個對 `projects` 取 `FOR UPDATE` 列鎖的消費者，而上游 `performance-design` 決定不設鎖等待逾時。基礎設施層卻同時宣告「不改連線池」。實查 `database.py:37` 為 `create_engine(db_url)`，沒有任何 pool 參數，使用 SQLAlchemy 預設的 5 加 10 溢出，共 15 條連線，且全部 router 共用。`services/*.py` 對 `lock_timeout` 與 `statement_timeout` 命中數為 0，這項為我的實查。一個持鎖不放的交易（例如卡住的 `delete_project`，設計自己列為 `OPEN-ND19-9`）會讓同專案的其他請求各占住一條連線無限等待，最終耗盡共用連線池，使整個 backend 不可用。故障影響範圍是全站，而不只是 membership。設計在 §三之一 說「交易短、無外部呼叫」，那只降低機率，不是保護。 | 在關卡上決定：要麼為本單元補一個鎖等待上限（交易層級 `SET LOCAL lock_timeout`，不動全域 `SessionLocal`，因此不違反 `NFR12.5`），要麼把「卡住的持鎖者會耗盡 15 條連線」明列為已接受風險並指派承接站。 | New |
| R-03 | Minor | `infrastructure-specification.md` §四之二 清單「`project_members` 的額外索引」列（「刻意沒有，不得自行補 `index=True` 在 `user_id` 上」） | 與已落地結果矛盾：`schema_rbac.sql:609` 現有 `CREATE INDEX IF NOT EXISTS ix_project_members_user_id`，`models.py` 也以具名 `Index("ix_project_members_user_id", "user_id")` 宣告，`test_membership_data.py` 的 M3b 還驗遷移腳本含它。**程式是對的**：U23 為可見性查詢建立該索引，設計寫作當時是對的，後來被取代。該列留在凍結產出裡會誤導下一個比對者。 | 在關卡上標註此列已被 U23 取代，以 DDL 為準。 | New |
| R-04 | Minor | `infrastructure-specification.md` §4.3 表第 1 列（「是否加 CHECK 需與上表分開判」） | 這一列沒有下結論，只說要分開判，而 `cause` 是否帶 CHECK 就是該欄 DDL 唯一的待決設計點。實作端已決定「有 CHECK」（`schema_rbac.sql:655` 的 `ck_reselection_events_cause`，`models.py` 同步宣告），且符合 `cause` 兩值已由 `[FD3]`=A 定案的理由。設計把決定留給下游而沒說清楚誰來判，屬契約不完整，但結果正確。 | 在關卡上記錄決定為「加 CHECK」，與已落地的程式一致。 | New |
| R-05 | Minor | `monitoring-design.md` §5 與 §5.1「保留期」列；ADR-0006 的 audit logging 面向 | 授權拒絕（`membership.denied`）是 IAM 面向唯一的執行期稽核痕跡，且只存在於 docker logs。設計只寫「沿用既有 docker logs 設定、`DEPLOY.md §5.6` 已設日誌上限」，沒有寫出實際的保留天數或容量，也沒有說明輪替之後稽核證據消失這件事。這是刻意的取捨，但沒有數字就無法判斷它是否滿足 audit logging 面向。四個事件名常數已落地（`membership_service.py:93`、`:94`），`OPEN-ID19-7` 的處置屬實。 | 補一句 `DEPLOY.md §5.6` 的實際日誌上限數字與其含義，或明寫「拒絕稽核不保證長期保留」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 逐項抽查設計主張與已落地程式（`ci.yml`、`models.py`、`schema_rbac.sql`、`DEPLOY.md`、`LOCAL-DEV.md`、`test_membership_data.py`） | `concurrency` job、`tests_pg`、`cause` 欄與 CHECK、`DEPLOY.md §2.2.10`、`LOCAL-DEV.md` 的 `tests_pg` 小節、M1 到 M4 與 M8 均存在且與設計一致 | 設計對程式的承接成立。矛盾僅限 R-01 和 R-03 兩處（都是後續單元 U23 造成的過期） |
| 契約端點三問（誰寫、誰讀、誰清）對本站新增的契約 | 四個 log 事件名常數已有擁有者與落點；`OPEN-ID19-1` 到 `OPEN-ID19-7` 皆已指派承接站 | 無新增孤兒契約。`OPEN-ID19-2` 的承接內容已過期，見 R-01 |
| 不跑測試、lint、建置 | 依 brief 約束未執行 | 未驗證測試實際通過；以讀碼與讀測試檔為限 |
