# NFR Requirements 問題檔 — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T22:52:51Z（`date -u` 取值）。
>
> 單元類型 **`ui`**，但 `[PP1]`=A 使本單元多了後端變更（兩支列舉端點的可見範圍放寬），使用者於
> 2026-10-15T22:46:22Z 又裁決把 `U7` 的三條寫入路徑一併收緊（`carried-review-items.md` 的 R-01）。
> `produces_kinds` 使本站只產出四份：`performance-requirements`（`[service, ui]`）、`security-requirements`、
> `tech-stack-decisions`、`traceability`。**`scalability`／`reliability`／`observability` 三份為 `[service]`，
> 不適用本單元**——判定理由見 `tech-stack-decisions.md` §三（後端變更沒有新增進程、新增狀態或新增外部依賴）。
>
> **識別字**：題號為 `[PPN1]`（方括號、無連字號）；本單元的需求編號為 `PPN-01` 起（連字號、兩位數），
> 可繼承 inception NFR 者用 `NFR<父條>.100` 起。`.100` 區段以
> `grep -rhoE "\bNFR[0-9]+\.[0-9]+\b" <record>` 實查：`NFR8` 已用 1–10／20／40–42／60／61／80／90／120，
> `NFR11` 已用 80／81，`.100` 在兩者皆為空。
>
> Depth **Minimal**：只問「預設錯了會造成真實重工或真實缺陷，且會改寫已核可上游字面」的題目。

**本站出題數為 1（`[PPN1]`）。**

## 〇、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 兩支列舉端點放寬為成員可見 | `[PP1]`=A | `functional-design-questions.md`；`rules.md` `BR87.1`／`BR87.2` |
| 擁有者那一半只在零成員列時生效 | `[PP3]`=A | 同上；`BR87.1` |
| 三籤結構、無來源者顯示「尚無法取得」 | `[PP2]`=A | `BR83.3`、`BR86.1`、`BR86.3` |
| `U7` 的建立系統、刪除專案、刪除系統套用同一可見性判準，被移出的建立者回 404 | 使用者 2026-10-15T22:46:22Z 裁決「帶進寫程式並修 R-01」 | `carried-review-items.md` R-01 |
| 驗證方式：後端 `unittest`＋`TestClient`；前端僅 Playwright e2e；零新依賴 | `team.md` Testing Posture（A／B／C 採用、D 不採） | `team.md ## Testing Posture` |
| 兩支端點的路徑、回應模型、狀態碼不變；只有 description 漂移 | `BR87.4` | `functional-spec.md` §二之一 |

## 一、刻意不出成題目的事（附理由）

1. **`OPEN-PP23-5` 的並行上限數字**：功能設計已給暫定預設 4（`BR88.3`），並指派本站「確認或定案」。本站**確認為 4**，
   理由可由 repo 現況直接推得（`database.py:37` 的 `create_engine(db_url)` 未設 pool 參數，即 SQLAlchemy 預設
   `pool_size=5`；backend 為單一 uvicorn 進程，`backend/Dockerfile:30`），推導寫在 `performance-requirements.md`
   的 `PPN-01`。它是前端一個模組常數，改值是一行 diff，不構成重工；無任何已核可文字對它有字面要求。
   先例：`U21 mcp-bridge` 同站「全域常數不出題」。
2. **`OPEN-PP23-5` 的請求數「上界」**：本站定為**不設硬上界**。設上界只有兩種做法：截斷（`BR88.3` 已核可「不截斷」，
   理由是會把部分和呈現成完整值）或拒絕渲染（`U24` 的 `OPEN-MP24-6` 已示範其代價：專案清單是進入專案的**唯一入口**，
   拒絕渲染等於鎖門）。兩者一個被已核可規則排除、一個製造已知斷崖，剩下的「不設上界、以並行上限控制瞬間負載」
   是唯一不改寫上游的做法——依 `project.md` 的 `requirements-analysis:260822-ra-c5`，單一可行解不出成假選擇，
   改在核可關卡揭露其代價（`performance-requirements.md` §三）。
3. **佇列內的發出優先序**（帶入項 R-04）：本站定為「需求欄位全部先於變更紀錄，各自依系統 id 遞增；儲存後重讀與
   `[重新整理]` 不進佇列」。這是 R-04 的建議方向，且直接由 `BR85.1`「需求籤與總覽讀同一份狀態」推得，
   沒有第二個不違反 `BR85.1` 初衷的選項。
4. **被拒絕的寫入要不要記 log**：`U7`／`U19` 家族**目前零處**記拒絕（`hierarchy_facade.py`、`hierarchy_router.py`、
   `membership_facade.py` 的 `logger.(info|warning|error|debug)` 呼叫皆為 0，以 grep 實查），本單元不為單一守門破例；
   理由與殘留寫在 `security-requirements.md` §五。
5. **回應時間的數字目標**：本 repo 沒有延遲量測機制；兩支端點的伺服器工作改以「SQL 語句數不隨 P／S 增長」這個可二元
   判定的形式約束（`PPN-06`），比一個量不到的毫秒數更能擋住 N+1 這個真實失敗模式。

## 二、問題

### [PPN1] 成員清單的「以使用者查成員列」要不要補索引？

**背景**：`[PP1]`=A 之後，專案清單要找出「請求者有成員列的全部專案」，查詢條件是
`project_members.user_id = 請求者`。這張表**刻意沒有**以 `user_id` 開頭的索引——`schema_rbac.sql:608-615` 逐字寫
「user_id 側**刻意不建**……它成為缺口的兩個條件本輪都不成立——① 以成員身分列出『我參與的專案』尚未存在（
hierarchy_facade.list_projects 目前 owner-scoped……）」，`U18` 的 `security-design.md` §4.3（`:316-329`）更逐字寫
「**該後繼落地時這個索引才需要**」，承接站寫 `U19`。`U19` 交付時清單仍是擁有者範圍，所以沒建；**本單元正是那個「後繼」**。

**現況量測**：不建索引時，每一次有人打開 `/projects`，資料庫就要把 `project_members` 整張表掃一遍（其他三條查詢——
系統清單的可見性判定、擁有者那一半、「零成員列」判定——都已被既有索引覆蓋：`uq_project_members_project_user`
以 `project_id` 為前導欄、`ix_projects_owner_user_id` 在 `schema_rbac.sql:353`）。今天 staging 的成員列數很小，
**使用者感受不到差別**；掃描成本隨「全部專案的成員總數」線性增加。

**為什麼要問而不是直接補**：`[PP3]` 的選項 A 原文含「**零 schema 變更**」（`functional-design-questions.md:172`），
你是在這句話之下作答的；補索引會改寫它，並觸發 `project.md` 的 blocking 同步（`schema_rbac.sql` ＋ `DEPLOY.md`）。

A. **（建議）本單元 code-generation 補 `ix_project_members_user_id ON project_members (user_id)`。**
   你會看到的：畫面與行為完全不變；`DEPLOY.md` 多一列索引與一條 `psql` 驗證指令；staging 部署後需重跑
   `schema_rbac.sql`（`CREATE INDEX IF NOT EXISTS`，可重跑安全）。
   代價：`[PP3]` 選項 A 的「零 schema 變更」改為「零資料表／欄位變更，新增一個索引」；同一個 PR 要同步
   `schema_rbac.sql`、`DEPLOY.md`、`models.py` 的 `Index`（`backend/tests/test_membership_data.py:139` 的
   `test_M3` 要求 ORM 與 DDL 的索引名稱集合相等，其 docstring `:145` 寫「刻意不建」也要改寫）；每次邀請或移出
   成員多寫一筆索引項（成員異動靠人工、頻率極低）。
   建議理由：上游自己寫下的觸發條件「該後繼落地時這個索引才需要」在本單元成立；不建，那段條件就成了一條
   沒有人執行的紀錄。
B. **不建，接受每次打開專案清單都掃整張成員表，維持「零 schema 變更」。**
   你會看到的：今天與 A 無差別。
   代價：`U18` 寫下的觸發條件成立而索引不存在；`schema_rbac.sql:608-615` 那段註解的「本輪都不成立」變成假的，
   本單元仍須改寫它（改成「條件 ① 已成立、經 `[PPN1]`=B 決定不建」）；日後成員總數變大時，沒有任何機制會提醒——
   本 repo 沒有查詢延遲監控。
C. **不建，但把「何時要建」寫成門檻（例如成員總列數超過某數），交 conductor 另開 intent。**
   你會看到的：今天與 A、B 無差別。
   代價：與 B 相同的註解改寫義務，外加一個**沒有任何機制會量測**的門檻——本 repo 無遙測，門檻只能靠人想起來去查，
   實質效果等同 B 加一份文件。

[Answer]: A <!-- 2026-10-15T22:59:34Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->
