# CI/CD — `U8 memory-service`

> 本單元交付進程內的四個模組 ＋ 一個索引。本檔逐一指出**哪些既有閘門會被它
> 觸發**、**各需要什麼才會綠**，並如實記載那些閘門在合併路徑上的實際強度。

## 〇、既有管線的機械事實（沿用前站實測，不重新推導）

`ci.yml` 有 **7 個 job key**（`gate`、`repo-contract`、`frontend`、`backend`、
`memory-schema`、`concurrency`、`docker-build`）；除 `gate` 外的 **6 個**全部且僅
`needs: gate`，故彼此並行。
`ut` **沒有任何必要狀態檢查**，`main` 只有一個（`Repository contract`）。

**本數字已於本站重新對照目前的 `ci.yml` 實數（承審查 `R-02`）。**
初稿寫「6 個 job／非 gate 5 個」並註明「沿用前站實測」——那是
`membership-service` 在**它自己提案新增 `concurrency` job 之前**的基準數，
而該提案已落地。更難看的是：本檔 §三 自己就列出 `concurrency` job
（說明本單元不觸發它），**同一份檔案的兩節因此互相矛盾**。
`project.md` 已記過「引用『既有為 N 條』這類基準數時，那個 N **也要重數**」
——本站初稿逐字複製了一個被自己後續段落推翻的數字。
引用其他單元的「前站實測」時，一律附一句本站是否重新核對過。

**對本單元的意義**：下文所說的「閘門」在合併進 `ut` 這條路徑上是
**訊號而非阻擋**。本單元不改變這一點。

## 一、本單元會觸發的既有閘門（五項，逐項附義務）

| # | 閘門 | 本單元為什麼觸發它 | 需要什麼才會綠 |
|---|---|---|---|
| 1 | **`repo-contract`** | `schema_rbac.sql` 與 `DEPLOY.md` 的 blocking 同步 | 兩檔同一個 PR 更新；`validate_repo_contract.py` ＋ `validate_env_contract.py` 綠燈 |
| 2 | **OpenAPI spec drift**（`backend` job 的 `:289`，`dump_openapi.py --check`） | **三處契約變更**：① 新增 `POST /api/memory/records`；② `DELETE` 的回應集合去掉 403（`[D1]`=A）；③ `GET /records` 新增分頁參數 | 重 dump `openapi.json` 並 commit |
| 3 | **`frontend`**（lint ＋ `tsc -b`） | `frontend/src/types/api.d.ts` 由 `openapi.json` 產生 | 重跑 `gen:types` 並 commit；`tsc -b` 綠燈 |
| 4 | **`backend`**（import smoke ＋ `unittest`） | 四個新模組 ＋ 新測試檔 | 既有 523+ 測試維持綠燈 ＋ 新測試綠燈 |
| 5 | **`memory-schema`**（真實 PostgreSQL） | 新增 HNSW 索引 ＋ 新 `S14` 斷言 | `S14` 綠燈；且**第二次套用**（可重跑性）仍綠 |

**本單元不觸發**：`docker-build`（零 image 變更）、`concurrency` job
（本單元無列鎖需求——`U19` 的 `FOR UPDATE` 情形不適用於這裡）、
WS contract drift（本單元無 WebSocket 面）。

### 1.1 第 2、3 項是連鎖的，漏一半比全漏更糟

`openapi.json` → `api.d.ts` 是單向產生鏈。若只重 dump 前者而不重跑
`gen:types`，**`backend` job 綠而 `frontend` job 的型別與實際契約不一致**
——而 `team.md` 已逐字記載 `tsc -b` 對前後端落差「實際無效」
（`AdminPage.tsx` 的手寫 `DbUser` 把 `any` 直接放行）。

故這兩項必須在**同一個 PR 內**一起做。記為 `code-generation` 的 blocking 檢查項。

## 二、`S14`：本單元唯一的新 CI 斷言

| 項目 | 設計 |
|---|---|
| 落點 | **既有 `memory-schema` job**（`verify_memory_schema.sql`），**不新增 job** |
| 為什麼不新增 job | 該 job 的前置條件（真實 PostgreSQL ＋ 已套用的 `schema_rbac.sql`）完全相同；另開一個等於把同一座 service container 建第二次（沿用 `ci.yml:314-320` 既有註解的同一理由） |
| 編號 | 目前到 `S13`（`U9` 的系統 actor），本單元為 **`S14`** |
| 內容 | `SET enable_seqscan = off` → `EXPLAIN` → 斷言計畫使用該 HNSW 索引 |
| 為什麼是 `EXPLAIN` 而非延遲 | opclass 不符時索引被**靜默忽略**（查詢仍正確、仍回精確最近鄰），延遲在空表上看起來一樣好 |
| 為什麼要 `enable_seqscan = off` | planner 是 cost-based 的，小表上幾乎必定選 `Seq Scan` **即使索引正確**——不關掉會產生假性失敗（承 `nfr-requirements` 審查的 `R-02`／`N8-12`） |

### 2.1 `S14` 驗的是 opclass，不是 planner 的選擇傾向

**誠實限定**：`enable_seqscan = off` 之下通過，**不等於**生產環境的 planner
會選用該索引——它只證明「索引可用且 opclass 相符」。

| `S14` 能證明 | 索引存在、型態為 HNSW、opclass 與查詢的距離運算子相符 |
|---|---|
| `S14` **不能**證明 | 生產資料量下 planner 真的會選它 |
| 誰能證明後者 | 一條帶數百至數千列 fixture 的測試（`nfr-design/performance-design.md §二之一` 的做法 A），**本輪不做** |

**為什麼接受這個限定**：`S14` 擋的是本輪真正的風險
（opclass 寫錯 → 索引永遠不被用 → `[N2]`=B 的整個投資落空且無跡象）。
planner 的選擇傾向是資料量的函數，而本表目前是空的——
現在量它只會量到「空表上不選索引」這個正確但無用的結論。記為 `I8-3`。

## 三、本單元**不**新增任何 CI job

| 候選 | 為什麼不要 |
|---|---|
| 新 job 跑 `S14` | 前置條件與 `memory-schema` 相同（§二） |
| 新 job 跑 TestClient 測試 | 新測試檔放進 `backend/tests/` 即被既有 `discover -s tests` 撿到，**零設定** |
| 新 job 跑 `tests_pg` | **本單元不需要真實 PostgreSQL 的 Python 測試**——授權與契約面以 `TestClient` ＋ SQLite 可測。需要真實 PG 的兩項（索引 opclass ＝ `S14`、檢索查詢的組合正確性 ＝ `S15`）**都是純 psql**，落在既有 `memory-schema` job（見 §三之一、§三之二） |
| coverage job | `team.md` 已記載 repo 無覆蓋率量測機制，導入屬獨立的工具鏈決策，不由本單元夾帶 |

**這與 `U19` 的對照**：`U19` 新增了 `concurrency` job，理由是
`with_for_update()` 在 SQLite 下**靜默消失**，故併發測試必須在真實 PG。

### 3.1 初稿在這裡講錯了一件重要的事（承審查 `R-01`，Critical）

初稿寫「**本單元沒有同類的語意落差**——授權判定、過濾、交易邊界在 SQLite 上
的語意與 PostgreSQL 一致。**只有向量索引不是**，而它由 `S14` 以 psql 覆蓋。」

**那句話是錯的，而它掩蓋了本單元最核心的不變量沒有任何測試覆蓋。**

| 事實 | 依據 |
|---|---|
| 檢索必須是**一次 SQL**：`WHERE`（可見範圍 ＋ `embeddingModel`）與 `ORDER BY`（pgvector 距離）在同一個查詢內 | `nfr-design/performance-design.md §一` |
| 為什麼它是正確性而非效能 | 先查再於應用層過濾會讓 `LIMIT n` 作用在**未過濾**的集合上——回傳筆數錯，且不可見的列先進入進程（洩漏面擴大） |
| SQLite 能不能跑這條查詢 | **不能**。SQLite 無向量型別、無距離運算子——這不是「語意不同」，是**這條 SQL 編不出來** |
| `search` 有 HTTP 端點嗎 | **沒有**（本檔 §〇 第 2 列：同進程，`U11` 消費），故也不在「四條端點 allow/deny」桶內 |
| `S14` 覆蓋它嗎 | **不覆蓋**。`S14` 只斷言「索引可用且 opclass 相符」（§二之一 已自承） |

**結果**：這個不變量在初稿的 CI 計畫裡**完全沒有覆蓋**——
不在「已自動化」、不在「待自動化」、也不在「只能手動」。

### 3.2 處置：新增 `S15`（仍在既有 `memory-schema` job，零新 job）

| 項目 | 設計 |
|---|---|
| 落點 | **既有 `memory-schema` job**（真實 PG ＋ 已套用 `schema_rbac.sql`，零新 service container） |
| 編號 | `S14` 之後，故 **`S15`** |
| fixture | 跨**兩個擁有者**與**兩個 `embeddingModel`** 各若干列，且列數**大於**查詢的 `LIMIT` |
| 斷言（三條，缺一不可） | ① 結果**不含**他人擁有且 `visibilityScope = owner` 的列；② 結果**不含**不同 `embeddingModel` 的列；③ 在過濾後的候選數小於 `LIMIT` 時，回傳筆數等於**過濾後**的數量（不是 `LIMIT`，也不是全表） |
| 為什麼第 ③ 條最關鍵 | 它是「`LIMIT` 作用在已過濾集合上」的直接斷言。若實作先查再過濾，①②可能仍然通過（事後過濾會把不該有的列濾掉），**只有 ③ 會紅** |

**第 ③ 條的設計理由值得寫下**：①② 是「結果裡不該有什麼」，
而一個「先查 `LIMIT n`、再於應用層過濾」的錯誤實作**也會通過它們**
——因為它確實把不該有的列濾掉了，只是濾在錯的地方。
③ 是唯一能區分兩種實作的斷言。

**§三 的表因此更正**：`tests_pg` 一列的理由不變（本單元不需要真實 PG 的
**Python** 測試），但「本單元沒有語意落差」這句話刪除——
語意落差存在，且由 `S15` 以 psql 覆蓋。

## 四、部署與回滾

| 項目 | 值 |
|---|---|
| 部署方式 | 隨 merge 進 `ut` 由 `deploy.yml` 部署（deploy-on-merge，ADR-0007） |
| `deploy.yml` 的變更 | **零** |
| 既有環境取得索引 | `run_meta_schema_migration.py` 解析 `I)` 區塊（**不需新腳本**） |
| 回滾 | 程式碼可 `git revert`；**索引需手動 `DROP INDEX`** |

### 4.1 回滾的不對稱

| 情境 | 可否回滾 |
|---|---|
| 四個新模組 | 可（git revert） |
| `openapi.json`／`api.d.ts` | 可 |
| **HNSW 索引** | **git revert 不會刪掉它**——DDL 已執行過。需手動 `DROP INDEX IF EXISTS` |
| 已寫入的記憶列 | **不適用**：本單元不做資料遷移，回滾不涉及既有資料 |

**索引留著的後果是無害的**（它只佔空間，不改變查詢正確性），
故本站**不要求**回滾程序包含 `DROP INDEX`——但要寫下來，
以免有人以為 revert 之後資料庫回到了原狀。記為 `I8-4`。

## 五、`tcms-test-cases` 的前置提醒（blocking，但不在本站）

`project.md ## Mandated` 要求每個 intent 的 construction 必經
`tcms-test-cases` 並完成四項產出，**未完成不得進入部署階段**。
本站只記前置與分桶**預判**：

| 桶 | 本單元的項目 |
|---|---|
| 待自動化 | 四條端點的 allow/deny（`TestClient`）；`[D1]`=A 的三案例（含「狀態碼相同、日誌可區分」）；`NFR7.20`／`NFR7.21` 的酬載忽略；`NFR3.24` 的排序決定性（PBT）；`S14` 的索引 opclass 斷言；**`S15` 的檢索查詢組合正確性斷言（承審查 `R-01`，見 §三之二）** |
| **只能手動** | **`NFR3.20` 的延遲實測**——它需要一個有真實資料量的環境，而 `NFR3.21` 要求記錄當時列數；CI 無此環境 |
| 已自動化 | 0 |

**該 stage 至今未對本 intent 的任何單元執行過，而它是 blocking。**
