# Tech Stack Decisions — `U4 hierarchy-data`（`spec`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: hierarchy-data · kind: spec -->

## 〇、本檔的定位

本單元**不引入任何新的執行期依賴**。本檔記錄的是四個選擇：遷移放哪裡、用什麼形式執行、
用不用 migration 框架、驗證在哪裡跑。前三個在本 repo 都有既成事實或既有禁令要對照，
第四個由 `Q1=A` 定案。

技術棧的既成事實（`codekb` 與 `team.md`）：Python／FastAPI、PostgreSQL、
測試框架為內建 `unittest` ＋ `hypothesis`（**不是 pytest**）、
CI 以 `python -m unittest discover -s tests -v` 執行。

---

## 一、決策表

| # | 決策 | 選定 | 理由 | 可逆性 |
|---|---|---|---|---|
| D-1 | 資料庫 | **PostgreSQL（既有）** | 本單元加三張表與一個欄位，沒有任何理由引入第二種儲存。`vector(1024)` 等 pgvector 需求屬 `U5`，不影響本單元 | 不需要 |
| D-2 | 遷移的程式形式 | **一個可被 `unittest` 匯入並呼叫的模組層函式**，放在 `backend/` 之下（具體檔名留 `code-generation`） | `K-04` `migration.entrypoint` 逐字要求：「不得只存在於 `init_db()` 的副作用或只在空 volume 執行的 SQL 檔中」。`BR2.4` 是它的規則形式 | 易 |
| D-3 | 遷移的執行方式 | **獨立指令，不掛啟動路徑**（`Q2=A`） | 掛啟動路徑等於把它放進 `database.py` 的 `_ensure_*` 家族所在的那條路徑，而該家族的既有形狀是**全部吞掉失敗**（`K-04` 逐字）。獨立指令讓失敗就是部署失敗 | 易（可後續加掛啟動路徑，但那會買回 B 的失敗面） |
| D-4 | 是否引入 migration 框架（Alembic 等） | **不引入** | 本 repo 今天零 migration 框架；引入一個會同時牽動既有 `_ensure_*` 補丁的去留、`schema_rbac.sql` 的定位與部署流程，那是一個獨立的工具鏈決策，不由一個加三張表的單元夾帶。`K-04` 只要求「可被匯入呼叫的入口」，一個模組層函式就滿足 | 易，且**建議未來重新評估**——見 `§二` |
| D-5 | 驗證環境 | **共用那個真實 PostgreSQL service container job**（`Q1=A`）；映像 **`pgvector/pgvector:pg18`**，沿用 `brain-infra` 的 `NFR6.1` | 不另開第二份 service container 設定；`U4-V2` 要求該 job 先寫入前置狀態、`U4-V5` 要求再跑一次。**映像不照抄 `NFR6` 的 `postgres:16-alpine`**——`K-01` `images_and_services` 逐字要求「db image 由 `postgres:16-alpine` 改為 `pgvector/pgvector:pg16`」，理由是 `U5` 的 `vector(1024)` 需要 pgvector，而 `U5` 正是這個共用 job 的同居者。該映像對本單元的三張表是超集。**但本站不釘死它（iteration 2 審查 R-10）**：`K-01` 那句話帶著一個 `scope` 子句——「`deploy/docker-compose.deploy.yml` 與 `deploy/docker-compose.test.yml` 兩處」——講的是部署與測試 compose，沒提 CI job。**關係更正（iteration 3 審查 R-15）**：不是三方矛盾——`requirements.md:377` 與 `K-05` 的 `verification.carrier` 彼此一致，而 `K-01` 被自己的 `scope` 子句排除在 CI job 之外。**更正（nfr-design 站查出）**：本段初版寫「沒有任何一份上游說過這個共用 job 該用哪個映像」，**那句話是錯的**。`brain-infra` 的 `nfr-requirements` 自己的 `NFR6.1` 逐字把「`N-2` 的真實 PG CI job service container」列為映像必須一致的四個落點之一，映像為 **`pgvector/pgvector:pg18`**；`deploy/docker-compose.deploy.yml:40` 現況也已是 `pgvector/pgvector:pg18`。我讀了 `K-01`（它只講 deploy／test 兩處的 `pg16`）卻沒讀兄弟單元自己的 NFR 產出——而閱讀範圍限制是給審查者的，不是給 conductor 的。**結論改為：映像已由 `brain-infra` 定為 `pgvector/pgvector:pg18`，`U4` 沿用，不由 `S-6` 決定。** | 易 |
| D-6 | 測試框架 | **內建 `unittest`**，測試檔放 `backend/tests/` | `team.md` 的既成事實；新檔放進該目錄即被 `discover` 撿到。**`TestClient` 不適用**——本單元交付零端點 | 不需要 |
| D-7 | 是否用 `hypothesis` 寫 property-based 測試 | **不適用於本單元（但理由換過一次）** | **判定依據是範圍，不是分類計數**：`project.md ## Testing Posture` 把 PBT hard constraint 綁在 IaC generator、cost calculator、agent routing 三個模組上，本單元不是其中任何一個。<br>**初版的理由是錯的**（iteration 1 審查 R-04）：它寫「`calculation` 為 0……沒有值域性質可寫成 property」。計數本身正確（`constraint` 8／`validation` 1／`policy` 3／`calculation` 0，本輪再次由 `rules.md` 的 yaml 實算複驗），但推論不成立——PBT 適用於狀態變換而非只適用於計算，而 `BR2.2` 的冪等正是教科書等級的代數性質 `f(f(x)) == f(x)`，值域就是產生出來的使用者與架構圖。<br>**已考慮並不採用**：改以 `U4-V5` 的例子式重跑斷言承載同一個性質（CI job 跑第二次並斷言沒有第二組預設、沒有重新指派）。理由是它與 `U4-V1`–`U4-V3` 共用同一個 job 與同一份夾具，零新增工具；採 `hypothesis` 則需要一套能產生使用者／圖狀態的 strategy，成本不成比例。**若日後遷移邏輯變複雜，這個取捨應重評** | — |

---

## 二、`D-4` 的重新評估觸發條件（寫下來，不然沒人會回頭看）

不引入 migration 框架是一個**現在划算、未來未必**的決定。以下任一成立時應重新評估：

1. 本 repo 累積到**第三個**需要改既有資料的遷移（本單元是第一個帶資料寫入的）；
2. 出現需要**回滾**單一 schema 變更的需求。<br>**更正（iteration 1 審查 R-03）**：初版寫「現在的形狀沒有回滾路徑」，**那句話是錯的**。已核可的 `domain-design/decisions.md:90` 與 `:126` 兩處逐字定義了回復方式：「清空 `system_id` 並刪除新建的 `projects`／`systems` 列」，而 `stories.md:432` 正是把「遷移的歸屬規則與回復方式」指派給 domain-design，它交付了。現在的形狀**有**一條人工回復路徑，缺的是**框架級的自動回滾**（一個指令回到前一版 schema）；那才是引入框架的理由；
3. `database.py` 的 `_ensure_*` 家族要被整批移除時——那是引入框架的自然時機。

---

## 三、本單元**不**引入的東西（明列，避免下游誤補）

| 不引入 | 理由 |
|---|---|
| 任何新的 Python 套件 | 三張表與一個欄位不需要 |
| 任何新的環境變數 | `SEC-2` 明文禁止；遷移沿用部署既有的資料庫憑證 |
| 任何新的容器 | 本單元不是服務 |
| Alembic 或同類框架 | `D-4` |
| `TestClient` 測試 | `D-6`；零端點 |
| 前端任何改動 | 本單元交付零畫面；`AC9.1.3` 保證既有頁面不受影響 |

---

## 四、與 `project.md` blocking 規則的關係（`U4-D1`）

`Q2=A` 讓部署多一個明確步驟，於是 `DEPLOY.md` 的更新義務多了內容。本單元觸發的
blocking 同步完整清單（編號 `U4-D1`；**不再掛 `NFR8.1`**——`NFR8` 的前提子句是
「Redis 作為第 5 個容器引入時」，本單元不引入容器也不引入變數，掛不上去，
見 `security-requirements.md §〇` 的編號說明，iteration 1 審查 R-01）：

| 必做 | 內容 |
|---|---|
| `schema_rbac.sql` | 三張新表與 `user_diagrams.system_id` 的 DDL、必要的 `COMMENT`、`IF NOT EXISTS` 可重跑寫法、檔頭涵蓋清單更新 |
| `DEPLOY.md`（前進） | 「這支 SQL 會建立的表／欄位」表更新；**並新增遷移指令的執行步驟與它的預期輸出**（`Q2=A` 帶來的新內容） |
| `DEPLOY.md`（回復） | **與前進步驟並列寫出回復程序**：清空 `system_id` 並刪除新建的 `projects`／`systems` 列（`decisions.md:90`／`:126` 逐字）。理由：`Q2=A` 把它變成一次特權的部署期 DDL ＋ 跨使用者資料寫入，而 `org.md ## Deployment` 對任何 high-risk action 要求「plan ＋ impact ＋ rollback」。`team.md ## Deployment` 記載的 `deploy.yml` rollback job **只還原程式碼**，它碰不到這次資料寫入（iteration 1 審查 R-03） |
| `DEPLOY.md`（靜止前置） | **寫明遷移期間應用不得接流量**（`U4-V6`，人工裁決）。`S-8` 讓遷移跨越多個 commit，於是出現上游從未討論的「應用 vs 遷移」競爭：進行中新建的圖不帶 `system_id`，`BR2.1` 的終檢就不為 0——而那不是遷移的錯。**但這一行不是 `U4-V6` 的承載者**（iteration 3 審查 R-14）：`deploy.yml:121–124` 用單一 `up -d --build` 一次拉起整座 stack、`:126` 立刻等前端，沒有任何一點是 db 起來而 backend 沒起來的。承載者是 `S-9` 要求的**有序部署步驟**；本列只負責把前置條件講給讀 `DEPLOY.md` 的人聽 |
| `DEPLOY.md`（部分狀態） | 寫明**「部分使用者已遷移」是合法且可恢復的中間狀態**（逐使用者交易，見 `security-requirements.md §三`），重跑即補完。不寫的話，看到它的人會以為壞了（`S-8`） |
| 建議一併（非 blocking） | `schema.sql`、`<record>/construction/plans/schema-rbac-notes.md` |

functional-spec `§七` 已判定該規則的五個觸發條件命中四個；本站不重複判定，只補上
`Q2=A` 與 iteration 1 審查讓 `DEPLOY.md` 多出來的三項。
