# Monitoring Design — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T23:44:13Z（`date -u` 取值）。
>
> 本單元**不交付任何 metrics 收集、告警規則或 SLI／SLO**。本 intent 至今沒有任何告警通道或 dashboard
> （`U10` 登記的 `OPEN-N10-4`，本站沿用、不另立同義缺口）。把「有 log」寫成「有監控」是本 repo 已記過的失敗形狀，
> 本檔只列**今天實際存在**的可觀測面，並逐項寫明可量測與不可量測者。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-design/security-design.md` | §五之一（既有刪除 INFO log 的更正）、§五之三（`[PPD1]`=A 的 actor log 與其測法）、§五 末點（被拒寫入不記 log，上游定案）、§六（前端 `console.` 規則） |
| `../nfr-design/performance-design.md` | §三（連線池耗盡條件：本 repo 無量測） |
| `../nfr-design/nfr-design-questions.md` | `[PPD1]`=A |

## 一、今日的可觀測面（完整清單）

| # | 訊號 | 產生點 | 去向與保留 | 誰消費 |
|---|---|---|---|---|
| 1 | 既有 INFO：「刪除專案 %s」「刪除系統 %s」（只含 id） | `backend/services/hierarchy_service.py:192`、`:214`（logger `cloud360.hierarchy_service`，`:28`） | stdout（`backend/main.py:25` `logging.basicConfig(level=logging.INFO)`）→ docker `json-file`，每服務 `50m × 5` 依大小輪替（`deploy/docker-compose.deploy.yml:62-68`） | 人工 `docker compose ... logs backend` |
| 2 | **新增**（`[PPD1]`=A）：「刪除專案 project_id=%s actor_user_id=%s」、系統同形 | `HierarchyFacade.delete_project`／`delete_system` 在 service 成功返回後；logger `cloud360.hierarchy_facade`（`backend/services/hierarchy_facade.py:47`，既有但目前未使用） | 同第 1 項 | 同上；回答「是誰刪的」 |
| 3 | uvicorn access log（方法、路徑、狀態碼） | uvicorn 預設開啟（`backend/Dockerfile:30` 未加 `--no-access-log`） | 同第 1 項 | 人工查詢。**被守門拒絕的寫入在這裡會留下一行 `DELETE /api/hierarchy/projects/<id>` ＋ `404`**，但不含請求者身分 |
| 4 | 前端 `console.` 固定字串 | 既有頁面的失敗路徑；`fanoutQueue.ts` **不得**有 `console.`（`security-design.md` §六） | 不保留（瀏覽器 session） | 開發者 devtools、e2e |
| 5 | CI 結果：`unittest`、`memory-schema` 的遷移後條件、`ui-regression` → Kiwi TCMS | `ci.yml`、`ui-regression.lock.yml` | GitHub Actions log；Kiwi 保留 per-run 結果 | 開發者；見 `cicd-pipeline.md` |

**被拒絕的寫入不加應用層 log**：nfr-requirements §五 已定、nfr-design §五 不重開，本站照實沿用。第 3 項 access log
是既有行為而不是新增的稽核——它記得到「有一次被拒的刪除請求」，記不到「是誰」。

**log 內容的最小化**：第 2 項只記整數 id，不記專案名、系統名或使用者名（`PPN-18` 的精神；`security-design.md` §五之三）。
後端 log 不進公開 repo，也不進 Actions log（部署 job 只在失敗時印 `logs --tail=80`，`deploy.yml:143`、`:355`——
**這一點要注意**：部署失敗時 backend 的最後 80 行會出現在**公開可讀**的 Actions log 中，若當時恰有刪除事件，
專案／系統 id 與刪除者的使用者 id 會隨之公開。三者皆為整數 id、不含名稱，風險低，記為已知事實而非缺口）。

## 二、Metrics & KPIs — **本單元不交付任何 metrics 收集**

| 候選指標 | Source | Threshold | 為什麼不交付 |
|---|---|---|---|
| 專案清單端點延遲（驗證索引效果） | — | — | 無 metrics 收集機制；本 repo 無 APM／Prometheus。索引是否被選用只能人工 `EXPLAIN`（`cicd-pipeline.md` §二） |
| 連線池等待次數／逾時 | — | — | `performance-design.md` §三：本 repo 沒有連線等待的量測；耗盡條件（約 3 位使用者同時進系統數多的專案）**不會被自動發現** |
| 守門拒絕率（404） | 第 3 項 access log | — | 可人工 grep 計數，但 404 也包含真正不存在的 id，無法區分「被移出者的嘗試」 |
| 成功刪除次數／刪除者分布 | 第 2 項 | — | 可人工 grep；無彙整、無保留期保證 |

## 三、Alerts — **本單元不交付任何告警規則**

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| （無） | — | — | 通道不存在（`OPEN-N10-4`） |

值得告警但目前無處可送的訊號：① 短時間內同一 `actor_user_id` 大量刪除（誤操作或帳號遭濫用）；② 專案清單端點 5xx。
登記在此供 `OPEN-N10-4` 關閉時一併接上，**不在本站新開缺口編號**。

## 四、SLIs／SLOs — **本單元不交付**

| SLI | SLO target | Measurement window |
|---|---|---|
| （無） | — | — |

`phases/operation.md` 要求 SLO 量化到百分比與時間窗，而本單元既無量測來源也無告警通道；寫一個量不到的 SLO 只會
製造「已定義」的假象。上游 `performance-requirements.md` §五 已明定不設毫秒級延遲目標。

## 五、可量測與不可量測（照實）

| 事項 | 可量測？ | 方式／原因 |
|---|---|---|
| staging 上索引是否存在 | **只能人工** | `cicd-pipeline.md` §二 的 `pg_indexes` 查詢；部署流程無任何步驟查它 |
| 部署後 hierarchy 端點是否正常 | **部署流程量不到** | `deploy.yml` 的冒煙檢查只打 `/`（`:135`）與 `/api/auth/login` 預期 401（`:335-345`）與公開網址 `/`（`:362`）；**沒有任何一步碰 `/api/hierarchy/*`**，故專案清單壞掉不會讓部署失敗、也不會觸發 rollback |
| 是誰刪了專案／系統 | 可（`[PPD1]`=A 之後） | 第 2 項 log；保留量受 `50m × 5` 輪替限制，舊事件可能已被覆蓋 |
| 刪除連帶消失了幾筆成員列／需求欄位值 | **不可** | `security-design.md` §八 殘留第 2 項：計數需讀他單元的表，違反 §四 的方向檢查 |
| 被拒寫入是誰嘗試的 | **不可** | 上游定案不記；access log 只有狀態碼 |
| 前端扇出在途數（上限 4） | 只在 CI | `ui-regression` 的 e2e 以路由攔截量測（`performance-design.md` §一之四）；正式環境無收集 |

## 六、Logs & Tracing

- **彙整**：無集中式 log 彙整；每台主機的 docker `json-file`，依大小輪替。查詢方式為在 `192.168.10.10` 上
  `docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env logs backend | grep "actor_user_id="`。
- **Tracing**：無。本單元不引入 request id 或分散式追蹤；第 2 項與第 3 項之間只能以時間戳人工對齊。
- **Dashboard**：無。
