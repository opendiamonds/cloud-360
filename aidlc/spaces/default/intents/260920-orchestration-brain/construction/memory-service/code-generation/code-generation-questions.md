# Code Generation 問題檔 — `U8 memory-service`

> 本站只有一個關卡：Plan Approval。設計層的待決項已在四個前置站定案
> （`[FD1]`–`[FD4]`、`[N1]`–`[N2]`、`[D1]`），本站不重問。

## 計畫寫作期間查出的四項事實（其中兩項改變設計）

| # | 事實 | 影響 |
|---|---|---|
| 1 | **記憶表沒有 ORM 模型。** `backend/models.py` 內 `class Memory*` 零命中；而 `backend/tests/helpers.py:50` 的 `Base.metadata.create_all()` **只建有 ORM 模型的表**。故 SQLite 測試環境裡**根本沒有那兩張表** | 我在 `infrastructure-design/cicd-pipeline.md §三` 寫「授權判定、過濾、交易邊界在 SQLite 上的語意與 PostgreSQL 一致」——**那句話只有在 ORM 模型存在時才成立，而我當時沒查**。處置：**補上兩個 ORM 模型 ＋ 一條鎖住 ORM↔SQL 一致的測試**（依 `team.md` 的「單一真實來源」規則，先例為 `U18`／`U19` 的 `ProjectMember`／`ReselectionEvent`） |
| 2 | **`embedding` 欄位不能進 ORM 模型。** 宣告 `vector(1024)` 需要 `pgvector` Python 套件，而 `NFR8.20` 的第一項判準逐字是「`requirements.txt` 的 diff 為空」 | ORM 成為**八欄的部分鏡像**；一致性測試斷言的是「ORM 欄位 ∪ `{embedding}` ＝ SQL 欄位」而非兩者相等。省略是刻意且可機械判定的 |
| 3 | 向量檢索**必須**走原生 `text()` SQL（同一理由：無 `pgvector` 套件則距離運算子無法以 SQLAlchemy 表達） | 確認既有設計，非新決定。這也是 `S15` 存在的理由——該查詢在 SQLite 上**編不出來** |
| 4 | router 註冊形狀（`main.py:62-81`）與 `K-08` 的 `/api/memory/records` 路徑 | prefix 為 `/api/memory`，照既有形狀不自創 |

**第 1 項是本輪唯一的設計變更，而它是依規則決定而非出成題目**：
`team.md` 逐字要求新增第二份物化時「同一個 PR 必須一併新增鎖住兩者一致的測試；
無法寫測試的副本不新增」——三項條件（先例、機制、可測性）皆滿足，故規則本身
給出了答案。

## 計畫摘要

| 項目 | 值 |
|---|---|
| 交付物 | **19 個檔：9 新、10 改**（含兩個「刻意不動」作為 `NFR8.20` 與「不新增 CI job」的可驗證面） |
| 步驟數 | **11 步**（含 6 項突變驗證） |
| 四層形狀 | `memory_router` → `MemoryFacade`（`K-08` 的 `sole_entry`）→ `memory_service` → `memory_ranking`（純函式） |
| 新依賴 | **零**（`requirements.txt` diff 為空——這同時是 ORM 省略 `embedding` 的原因） |
| 新 CI job | **零**（`S14`／`S15` 進既有 `verify_memory_schema.sql`，`memory-schema` job 已執行它） |
| 新部署設定 | **零**（不動 `deploy/`、`render-env.sh`、任一 `.env.example`） |
| `backend/database.py` | diff **必須為空** |
| 結構變更 | **一項**：HNSW 索引 ＋ 其四項 blocking 連帶義務 |
| 契約變更 | **三處**：新增 `POST`；`DELETE` 去掉 403（`[D1]`=A）；`GET /records` 加分頁 → 觸發 OpenAPI drift，須重 dump ＋ 重跑前端型別 |

## 測試摘要（24 條斷言，三個載體）

| 載體 | 條數 | 執行者 |
|---|---|---|
| `test_memory_contract.py`（靜態，零 DB） | 5 | 既有 `backend` job |
| `test_memory_ranking.py`（PBT） | 3 個 property | 既有 `backend` job |
| `test_memory_authz.py`（TestClient ＋ SQLite） | 12 | 既有 `backend` job |
| `verify_memory_schema.sql` 的 `S14`／`S15` | 4 | 既有 `memory-schema` job |

**分界線由「SQLite 能不能跑那段 SQL」決定**，不是由測試型態決定。
向量檢索的組合正確性只能在真實 PostgreSQL 上驗（`S15`）。

**三條斷言值得特別指出，它們各自是某個缺陷的唯一偵測面**：

| 斷言 | 它是什麼的唯一偵測面 |
|---|---|
| `S15` ③（過濾後候選數 < `LIMIT` 時回傳筆數等於過濾後數量） | 「先查 `LIMIT n` 再於應用層過濾」這個錯誤實作——①② **也會通過** |
| `test_memory_authz` 第 5＋6 條（他人／不存在皆 404，差異只在日誌） | `[D1]`=A 是否真的關閉枚舉 oracle 而非連日誌一起收斂 |
| `test_memory_authz` 第 7 條（`Platform_Admin` 刪他人記憶 → 404） | 兩套授權模型不可互換——只測第 8 條（放寬）的話，用角色判刪除的實作也會通過 |

## 覆蓋率的誠實限定

`org.md` 宣告 80%；repo **無量測機制**（`team.md` 逐字「是宣告而非閘門」）。
計畫不宣稱滿足、也不弱化，改以 24 條斷言 ＋ 6 項突變驗證作為實際門檻。

## 承接自上游而本站不解決的 13 項

`D8-1`（`[D1]`=A 偏離 `K-08` 的 403）、`D8-4`（分頁偏離 `K-08`）、
**`D8-5`（`semantic`／`procedure` 無保存期上界——**無自然承接站**，須於本站
核可關卡重新提交使用者）**、`D8-6`（correlation id → `U13`）、
`D8-7`（`U12`／`U13` 寫入失敗時的行為未定）、
**`FD8-1`（兩條新依賴邊須回報 `bolt-plan.md` 並重審 Bolt 順序——
`delivery-planning` 已在游標之前，故承接者是該文件本身）**、
`I8-1`（枚舉偵測需日誌聚合）、`I8-2`（索引失效在生產無偵測面）、
`I8-4`（`git revert` 不刪索引）、`N8-1`（`NFR10` → `U11`）、
`N8-9`（無備份策略記載）、`N8-10`（metrics 承載機制——**無承接站**）、
以及 **`tcms-test-cases`（blocking，至今未對本 intent 任何單元執行過）**。

## Plan Approval

[Approval Fingerprint]: sha256:v3:ab10febc0effc3ec7d3e72ec11e1077e4cacb04877f8617f442294dd018b5d27
[Planned Source]: c288b69717bf4a2f6d04c5be28eef072d13bc033daea65db437eff8ee8d5fe2f

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
