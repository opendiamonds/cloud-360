# 閘門發現彙整 — `260920-orchestration-brain`（跨單元）

> **這不是 stage artifact，也不在任何 `produces` 清單內**，故不受 review freeze 約束。
>
> **為什麼它放在這個目錄**：`code-generation` 的 `plan-approval-guard` 目前是啟動狀態，
> 它擋下所有 mutation-capable 的 shell 指令**以及** `construction/progress-channel/code-generation/`
> 之外的全部檔案寫入（我試過 `construction/` 層，被拒）。這是 guard 允許的唯一位置。
> 它正確的家是 `construction/gate-findings-consolidated.md`——guard 解除後請移過去。
>
> 建立時間：2026-10-04，本 session 第 11 輪審查之後。使用者於 Plan Approval 之前
> 選擇「先收閘門發現」。
>
> 本 session 共跑 **11 輪 advisory 審查，全部 NOT-READY**（advisory 兩種結論皆終局，
> NOT-READY 是給閘門的決策輸入，不是退回要求）。下表按**可行動性**分組而非按審查輪次
> ——後者對修復沒有幫助。

---

## A. 不受收據約束、現在就能修的（純 repo 缺陷）

### A-1 `DEPLOY.md` 記載的遷移程序照字面執行連不上資料庫 ★最高優先

**來源**：`hierarchy-data` `nfr-design` 審查 `R-01`（Critical）。**我已自行逐項複驗。**

| 查證 | 結果 |
|---|---|
| `db` 是否發佈 port | **沒有**。`deploy/docker-compose.deploy.yml` 的 `db`（`:35`）無 `ports:`、無 `expose:`；全檔唯一 `ports:` 在 `:319` 的 frontend |
| `DATABASE_URL` 住在哪 | `:85`，**backend 容器的**環境變數；主機名 `db` 只在 compose 內部網路解析 |
| `DEPLOY.md` 怎麼說 | `:321`／`:381`／`:702` 逐字 `cd backend && python scripts/run_hierarchy_migration.py`，在**宿主機** |
| 有記載容器內執行嗎 | **沒有**。全 repo 無 `docker compose exec`／`docker exec` 搭配該指令（兩處命中無關：`deploy.yml:149` 是無 TTY 的註解、`DEPLOY.md:205` 是被註解掉的 psql 行） |
| runner 需要什麼 | `run_hierarchy_migration.py:12` 逐字要求「於 `backend/` 目錄，且 `DATABASE_URL` **已指向**目標資料庫」 |

**後果**：操作者必須自備 DSN（權限等級自選），或走未被記載的容器內執行，或發佈 `db`
的 port——而最後一項正是該單元 `nfr-design` 的 Encryption 判定自己寫下的**界線失效
條件**。ADR-0006 四面向有兩個的前提在交付現況上未被建立。

**修法（需人決定）**：
- (a) 把 `DEPLOY.md` 三處改為容器內執行（`docker compose exec backend python scripts/run_hierarchy_migration.py`），並確認容器內有該腳本與 `DATABASE_URL`；
- (b) 保留宿主機形式，但明寫操作者須自備 DSN、其最小權限集合、以及「不得為此發佈 `db` 的 port」。
- **不建議 (c) 發佈 port** —— 它推翻已寫下的加密界線。

### A-2 全 record 77 處失效的上游行號引用

以 `difflib.SequenceMatcher` 對 `9e14145` 與 HEAD 逐行比對後實算：

| | 相異行號 | 引用處 |
|---|---|---|
| 仍正確（插入點前的穩定前綴：`requirements.md:9`–`:177`、`stories.md:107`） | 25 | 48 |
| **已位移** | **26** | **77** |
| 行號在出貨當下還不存在（上游修訂後才寫，本身正確） | 6 | 7 |

成因：`stories.md` 666 → **1371** 行（+705）、`requirements.md` 622 → **813** 行（+191），
而多數產出凍結於 2026-09-29。**跨 48 個檔案。**

**位移表**（`舊 → 新`）：
`requirements.md` `275→421`、`373→519`、`377→523`、`385→531`、`391→537`、`413→559`、
`425→571`、`451→597`、`475→645`、`484→654`、`520→690`、`523→693`、`529→699`、
`557→727`、`592→779`、`597→784`、`598→785`、`605→792`；
`stories.md` `365→385`、`405→425`、`407→427`、`413→432`、`426→445`、`432→451`、
`445→464`、`655→1269`。

**修法**：一支腳本可全部套用。**但分兩批**——不在 `produces` 內的（`memory.md`、問題檔）
可直接修；**`reviews/` 下是審查員的紀錄，不得修改**；`produces` 路徑那批帶著終局收據，
留到各單元閘門一併處置。

> **附帶**：這份位移表同時抓到 `hierarchy-data` `functional-design` 審查
> （`review-05.md`）的一個**錯誤 PASS**——它宣稱「逐字重驗 `requirements.md:784`」並判
> accurate，而 HEAD 的 `:597` 是 ADR-0006 四面向表的 **IAM** 列；它引述的文字是出貨當下
> 的 `:597`，現在在 `:784`。它驗了**事實**卻把結果寫成驗過了**定位**。已記入兩個 diary。

---

## B. 需要設計決定、沒有站可以承接（**必須人裁決**）

### B-1 `DuplicateChannelKey` 沒有被設計的出口 ★最高優先

**來源**：`progress-channel` `nfr-design` 審查 `R-02`（Critical）。**我已自行複驗。**

`BR1.2` 要求 `open()` 對已存在的鍵拋 `DuplicateChannelKey`。這個例外在哪裡被接住，
從 `functional-design` 到 `nfr-design` 一路是**假設而非設計**——`nfr-design §二` 寫它
「會被 `design_agent.py:214` 的 `except Exception` 接住」。

實測 `agent_router.py:124-128`：

```python
async def event_generator():                       # :124
    async for event in run_design_agent(...):      # :125  ← 沒有 try/except
        chunk = json.dumps(event, ensure_ascii=False)
        yield f"data: {chunk}\n\n"
return StreamingResponse(event_generator(), media_type="text/event-stream")   # :129
```

而 `functional-spec.md:34` 把 `open` 指派給**入口端**。所以在最可能的接線下該例外
**不經** `:214`——使用者得到**無聲中止的 SSE 串流**，連 `error` 事件都沒有。

**為什麼沒有站能收**：`U22` 三個設計站都有終局收據；`infrastructure-design` 是 CI 閘門的
站，而**沒有任何 grep 能斷言「這個例外有被接住且轉成正確的 `error` 事件」**。

**待決**：入口端（`U12`／`U13`）要不要把 `open()` 包在 `try/except DuplicateChannelKey`
裡並 yield 一個固定訊息的 `error` 事件？若要，訊息是什麼？

> 審查 `infrastructure-design` `R-05` 的收窄有用：`DuplicateChannelKey` 是**具名類別**，
> 所以 handler 的**存在性**可 grep——不能 grep 的只有「轉成了正確的 `error` 事件」。
> 故 `GAP` 可縮小到語意那一半。

### B-2 `U22-V3` 的 1e 沒有指定「從哪裡數出呼叫點」

**來源**：`infrastructure-design` 審查 `R-02`（Major）。硬寫三個路徑，第四個呼叫點會
靜默逃掉——**正是 `BR5.1` 只列一個呼叫點的那個失敗模式，在修補裡重現一次**。

### B-3 `U22-V7` 只覆蓋 2／3 呼叫點

**來源**：`infrastructure-design` 審查 `R-04`（Major）。覆蓋 `agent_router.py` 與
`wa_collab_orchestrator.py`，漏 `backend/test_agent.py:41`。**同一個子集覆蓋形狀，
在為它而生的修補裡又出現一次。**

### B-4 `S-1`：buffer 上界的數值

性質已定、數值未定。已核可要求：`code-generation` 定值前須實跑一次典型產圖、記下
`progress` 實際則數、上界取其倍數、測量值與倍數寫進程式註解。

---

## C. 已凍結產出的範圍／措辭缺陷（閘門裁決後由 `code-generation` 承接）

| id | 單元／站 | 內容 | 嚴重度 |
|---|---|---|---|
| C-1 | `progress-channel` `nfr-requirements` `R-01` | `SEC-2` 寫 `:216` 是「**唯一**」洩漏點，實為兩處（`:103` ＋ `:216`）。`:102` 在同一 `except` 區塊已是固定字串，故 `:103` 是刻意的不一致。**`nfr-design §二` 的設計已涵蓋兩處**，但凍結的需求本文仍寫「唯一」 | Critical |
| C-2 | `progress-channel` `nfr-design` `R-01` | 三處產出宣告 `infrastructure-design` 對 `library` kind-vacuous——假的。`produces_kinds` 四條中 `cicd-pipeline`／`traceability` 含 `library`，前者還是該 stage 的 `review_artifact`。**該站已實際執行，即為證據** | Critical |
| C-3 | `progress-channel` `infrastructure-design` `R-01` | **我用一條不適用的規則勸退選項 B，使用者在錯誤前提下作答。** 該 `## Forbidden` 的客體是「無人值守的流程自動化**與外部系統同步**」，處方是「以 gh-aw 或 **Actions workflow 承載**」——由 `ci.yml` 呼叫的 `scripts/*.py` 本來就滿足處方。先例**六處**（`ci.yml:154`／`:159`／`:162`／`:167`／`:280`／`:291`），其中 `dump_ws_contract.py --check` 是**本 intent 自己**在 `c619c3f` 交付的。決定 A 仍站得住，**該改的是理由** | Major |
| C-4 | `progress-channel` `infrastructure-design` `R-05` | 同一份產出自相矛盾：用「伸進入口檔做斷言」收起 `S-5`，卻對風險最高的 `B-1` 宣告同樣方法不可能 | Major |
| C-5 | `progress-channel` `infrastructure-design` `R-07` | 我宣稱「只有 AST 層才能完整」——**假的**。斷言 `except ... as` 綁定數等於 2 且都綁 `e`，第三個 `except` 就會紅。安靜腐化變大聲腐化，成本零 | Major |
| C-6 | `progress-channel` `infrastructure-design` `R-06` | **兩支 sensor 都回 `pass:false` 而我產出零揭露**（我沒去看）。`traceability` 回「本 stage 產出不含任何 `NFRx.y` id」——意即**什麼都沒驗證**；`upstream-coverage` 回 9 項未引用，實測 9 中 0 命中 | Major |
| C-7 | `hierarchy-data` `nfr-design` `R-02` | 被撤回的過度宣稱仍以生效中的判定活在**正式作答紀錄**裡：`nfr-design-questions.md:104` 仍寫 `SEC-4` 被「變強了」，而 `security-design.md:34` 稱它「過度宣稱」、`traceability.json` 已改 `Deferred`。作答紀錄與設計產出在一個 ADR-0006 判定上直接對撞 | Critical |
| C-8 | `hierarchy-data` `nfr-design` `R-06` | `created_at` 截止欄位與 `ix_diagram_change_records_created_at` **已出貨**（`schema_rbac.sql:412-413`），但 `:410` 與 `DEPLOY.md:310` 歸屬給 `U4-R1`，而 `U4-R1`（`security-requirements.md:86`）一字未提截止欄位與索引。真正來源是 `nfr-design §三之二`。**三站審查各見一面，無人認領** | Major |
| C-9 | `hierarchy-data` `functional-design` `R-01` | 四份產出共**十處**把 `user_diagrams` 的擁有者欄位叫 `owner_user_id`，實體欄位是 `user_id`（`owner_user_id` 在 `projects`／`estimate_sets` 存在但語意不同）。**錯名已傳播進已合併的程式註解**（`hierarchy_migration.py:464`），而同模組 SQL 與測試用正確的 `user_id`——**沒有自動化會發現它** | Major |
| C-10 | `hierarchy-data` `functional-design` `R-03` | `§八` 把「遷移也掛啟動路徑」留成可選，而 `BR2.4` 只禁「**只**存在於啟動路徑」。已出貨 runner 明文否決：`init_db()` 包在 `except Exception: logger.error` 裡，掛上去等於失敗變一行日誌加一個看起來正常的服務 | Major |
| C-11 | `hierarchy-data` `functional-design` `R-04` | `diagram_change_records.diagram_id` 已出貨為 `ON DELETE CASCADE`（兩份 DDL），四份產出**零字交代**。`§六` 把該表定位為稽核資料，CASCADE 使稽核列隨圖消失。另兩個 FK 各有規則且 `BR1.2.source` 論證過「為何不選 CASCADE」，第三個沒有 | Major |
| C-12 | `hierarchy-data` `functional-design` `R-05` | `OQ-H1` 記成未定案，而 `projects.owner_user_id` 無 `ondelete` 的預設**已上線**。「曾持有圖、現已刪光」的使用者留下預設專案，硬刪除撞 FK 變 500——正是 `BR3.2` 要消除的失敗，而其範圍不含這條路 | Major |
| C-13 | `hierarchy-data` `nfr-requirements` `R-01` | `U4-V1`–`U4-V6` **全部無 CI 承載者**：`ci.yml` 的 `services:` 區塊數 **0**，`backend` job 設 `DATABASE_URL` 指 `localhost:5432` 卻無容器在聽。`code-summary.md:218` 已逐字寫「本單元無法關閉」，但**沒有回流到擁有殘餘風險表的站** | Major |
| C-14 | `hierarchy-data` `nfr-requirements` `R-02` | `U4-R1`（90 天保存期）唯一驗證路徑指向「`rules.md` 的消費端義務」，而 `rules.md` 對 `90`／`保存`／`清除` 命中 **0**。90 天是 3.2 才定案，`functional-design` 在 3.1——**指向更早階段的前向引用，從寫下當天就為假** | Major |
| C-15 | `brain-ws-contract` `functional-design` `R-28` | `entities.md:167-170` 的更正註**反了**（`replace` 只命中帶前綴的字串，裸的 `:220` 存活），且 `traceability.json` 宣稱「兩處已更正」——字串層為真、語意層為假。**該輪 recovery 已用盡，無法修** | Major |
| C-16 | `brain-ws-contract` `nfr-requirements` `R-03` | `NFR5.7` 措辭描述**已被推翻**的 denylist。設計（`security-design.md §五`）已明文以 `ADR-0019 §6` 白名單覆寫——**設計與實作都對，只有需求措辭過時** | Major |
| C-17 | `brain-infra` `infrastructure-design` `R-19` | 約 190–230 行的引用漂移進 `deploy.yml`／`docker-compose.deploy.yml` | Major |

---

## D. 零爭議小修

| id | 內容 | 位置 |
|---|---|---|
| D-1 | 「取消歸屮」→「取消歸屬」 | `progress-channel` `functional-spec.md:292` |

（`hierarchy-data` 的 `§〇` 兩層刪除、`§六`→`§八` 交叉引用、`OQ-H3` 升格三項**已在
2026-09-29 那批編輯中修好**，本 session 的審查逐處複驗確認。）

---

## E. 本 session 我自己的流程缺陷（供改進）

| # | 缺陷 | 已記入 |
|---|---|---|
| E-1 | 用一條不適用的規則勸退選項，使用者在錯誤前提下作答。**補強：以「這違反規則 X」勸退任何選項之前，先 grep 該規則的既有先例數；先例不為零即代表我的讀法要重新核對** | `infrastructure-design/memory.md` |
| E-2 | 把自檢與 `log review` 串在同一個 shell 指令，請求在自檢未通過時就被記錄。**補強：兩者永遠分兩次呼叫** | 同上 |
| E-3 | 計數寫在算之前（規則數 11 vs 實算 13，兩數相加連 12 都不對）。**補強：數字由產生它的腳本直接輸出** | `functional-design/memory.md` |
| E-4 | 引用定位錯三次（`:101`→`:102`、`requirements.md:805`→`:619`、`:379-380`→`:378`＋`:379`），**另有一次直接採用審查員給的 `:493`（應為 `:494`）而未複驗** | `nfr-design/memory.md` |
| E-5 | 把四條的 `produces_kinds` map 只讀前兩條就概括，並把錯前提寫進派工 brief | `infrastructure-design/memory.md` |
| E-6 | 驗證工具三次誤導我（多分支 `grep -oE` 只回最先匹配的分支、`cut -c1-80` 截掉關鍵字、`^  [a-z]+:$` 把 network 算成 service）。**三次共同形狀：工具行為與我以為的不同，而輸出看起來正常** | 多處 |

---

## 下一步的機械限制（給接手的人）

`code-generation` 的 `plan-approval-guard` 目前**啟動中**，是 Bash 的 PreToolUse hook，
擋下所有 mutation-capable shell 指令（含唯讀的 `sed`、引擎自己的 `bolt set-autonomy`、
`orchestrate park`）**以及** `construction/progress-channel/code-generation/` 之外的全部
檔案寫入。

**兩條合法出路**：
1. 完成 Steps 2–3（`code-generation-plan.md` ＋ `unit-test-instructions.md`，含逐字貼入的
   Testing Contract JSON）並取得 **Plan Approval**；
2. 由人在對話中直接下指示改變方向。

guard 有 off-switch（會記 `GUARD_DISABLED`），**本 session 刻意不用**——關掉安全閘門
來繞過它不是正當手段。

**Testing Contract 現況**（`bun .claude/tools/aidlc-testing-posture.ts render`）：
methodology **`test-after`**、strategy **`standard`**（每元件 5–8 測試 ＋ 關鍵邊界整合測試）、
`project_type: brownfield`、
`contract_sha256: sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77`。

**單元進度**：24 個單元中 5 個有設計產出（`brain-infra`、`brain-ws-contract`、
`hierarchy-data`、`rbac-story-ids` 為已出貨單元；`progress-channel` 為本 session 從零完成
四站）。**18 個單元完全沒有產出**，每個單元每一站需要 2–4 題人工作答。


---

## A 組結案（2026-10-04，使用者裁決後執行）

### A-1 — **已修**。裁決：對調兩者。

查證把問題的形狀改小了：`DEPLOY.md` 原本的可行指令**已經存在**，只是被降級成註解
（`# 若 DB 在 Docker 內，範例：`），而主要路徑 `psql "$DATABASE_URL"` 在部署 stack 上
連不到——`deploy/docker-compose.deploy.yml` 只有 `frontend` 一個服務發布 host port，
`db` 沒有。所以這不是「程序連不到資料庫」（我先前四次是這樣描述的，**過重**），
而是**主要路徑與備援路徑顛倒**。

已改：加一張「哪個環境用哪一種」的對照表；`docker exec` 形式升為部署主機的 **A**；
`psql "$DATABASE_URL"` 降為可直連環境的 **B**；並在該節末尾一次性定義
「下文所有 `psql "$DATABASE_URL" -c` 驗證指令在部署主機上的對應形式」，
不在每一處重複。**未發布 `db` 的 port**——選項 (c) 已被明確排除，理由寫進對照表。

兩支 contract validator 在改動後皆通過。

### A-2 — **已修 72 處**；而真實規模是 **163** 不是 77。

**先重算再動手，而重算的結果推翻了上表。** 上表寫於 2026-10-03；此後
`nfr-design`、`code-generation`、`rbac-story-ids`、`embedding-port` 等站又寫了新的引用，
故同一個 `difflib.SequenceMatcher` 方法在 2026-10-04 重跑的結果是：

| | 數 |
|---|---|
| `construction/` 下的全部引用 | 266 |
| 仍正確（未位移） | 84 |
| **已位移** | **163** |
| 行號在 base 當下不存在（上游修訂後才寫） | 19 |

**163 之中只改了 72**，其餘 91 處全部落在 `reviews/` 目錄——那是審查員的紀錄，
改它就不再是審查員寫的東西（`approval-handoff:894fae12` 記過同形：逐處判讀與一律替換
的差別在那一輪就是 5 處誤改）。

**判准不是位移表本身，而是內容同一性**——只有 `HEAD[新行] == base[舊行]` 逐字相同
才改。這道檢查擋掉的是一個真實的風險：一個**在上游修訂之後才寫**的引用，其行號
已經是新的，若照位移表硬套會被改錯。分類結果：72 筆內容逐字相同（改）、
0 筆該行至今未變（不需改）、0 筆兩者皆不符（需人判）。

**事後驗證**（三項皆機械判定）：
1. 72 筆改寫後，新行內容與 base 舊行**不**相同的：**0**。
2. 天真重掃回報「仍有 34 處位移」——實為**誤判**：改寫後的新行號若仍落在 base 的
   行數範圍內，重掃無法分辨「照 base 寫的舊引用」與「已更新到 HEAD 的新引用」。
   符合此條件的改寫數為 **34**，與重掃回報數相等，證明是誤判而非殘留。
3. 指向超出現有檔案行數的引用：**0**。

涵蓋 19 個相異行號、28 個檔案。最大的幾群：`requirements.md:597`→`:784`（29 處）、
`stories.md:413`→`:432`（20 處）、`stories.md:432`→`:451`（14 處）。
