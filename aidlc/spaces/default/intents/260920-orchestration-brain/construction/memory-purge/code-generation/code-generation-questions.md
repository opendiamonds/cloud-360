# Code Generation 問題檔 — `U9 memory-purge`

> 本站只有一個關卡：Plan Approval。設計層的全部待決項已在
> `nfr-requirements`（`[N1]`）、`nfr-design`（`[ND1]`／`[ND2]`）與
> `infrastructure-design`（`[ID1]`）定案，本站不重問。

## 計畫寫作期間查出的五項事實（其中三項改變了設計，兩項與已核可上游不一致）

**這五項全部以開檔核對取得，不是推論。** 核可之前請先看這一節——
其中兩項是對已核可上游的偏離，依 `project.md` 必須在關卡上揭露而非靜默覆蓋。

| # | 事實 | 對設計的影響 |
|---|---|---|
| 1 | **上游的清除條件會刪錯列。** `NFR7.10` 的二元判準逐字是 `WHERE expires_at < now()`，**沒有 `kind` 過濾**；而 `FR4.5`（`requirements.md:157`）與 schema 自己（`schema_rbac.sql:478` 逐字「episodic memory **ONLY**」）都把保存期限定在 episodic，且 CHECK（`:460-461`）**不禁止**非 episodic 帶 `expires_at` | 清除條件收窄為 `kind = 'episodic' AND expires_at < now()`，並以 `R4` 斷言鎖住（fixture 內刻意放一列 `semantic` ＋ 過去 `expires_at`，斷言它**仍存在**）。**照上游字面實作的後果是永久刪錯使用者資料，而現有 CI 一條都抓不到** |
| 2 | **「重跑 `schema_rbac.sql`」是破壞性操作。** 我在 `infrastructure-specification.md §五` 寫它是「既有環境取得 seed 的唯一路徑」，但沒查它的代價：`:715` 是 `DELETE FROM role_permissions;`，`:717` 起重播預設矩陣；檔頭 `:23` 自己警告過「Admin UI 調過請先備份」 | 改以**新增的專用腳本**取得 seed；`DEPLOY.md` 明文寫「**不要**為此重跑整支檔」 |
| 3 | **既有的遷移腳本不能承載這個 seed。** `run_meta_schema_migration.py` 解析 `schema_rbac.sql` 的區塊執行（故 DDL 只有一份），看似該把 seed 掛上去——**但它被契約禁止**：該腳本 `:446-448` 的輸出逐字宣告「也不塞任何資料（契約 `K-15` 的 `observable_side_effects` 逐字「不含任何資料寫入」）」 | seed SQL **只有一份**，放在 `schema_rbac.sql` 的新 `K)` 區塊；新腳本 `import` 既有的 `extract_blocks` 解析它。三條路徑（空 volume／既有環境／CI）因此不可能漂移，而 `K-15` 不被破壞 |
| 4 | **（與上游不一致）系統 actor 的 `password_hash` 若照上游寫成「非 bcrypt 格式」，會製造一個未經驗證即可遠端觸發的 500。** `user_router.py:406` 的 `verify_password` 在 `:408` 的 `is_active` 檢查**之前**；`verify_password`（`auth.py:37-40`）**沒有 `try/except`**；而 `bcrypt` 對非 bcrypt 格式的 hash **拋 `ValueError`** 而非回 `False` | 兩項零成本處置：哨符 username **含大寫**（`SYSTEM.retention-purge`，而 `:403` 會 `.lower()`，故永不可能命中 → 乾淨回 401）；`password_hash` 改為**格式合法、明文為一次性隨機值且不記錄**的 bcrypt hash（即使被命中也乾淨回 `False`）。鎖由三道變四道。**`security-design.md §1.2` 的「非 bcrypt 格式」被取代**，理由是上游把「不可能回 True」與「會回 False」當成同一件事 |
| 5 | **（不照審查建議做）`R-01` 建議的「與 `deploy.yml` 共用 concurrency 群組」會製造更糟的後果。** GitHub 在同一群組只允許一個 pending run，新的排入會**取消先前那個 pending run**——每日排程的清除因此可能取消一個正在排隊的部署 | 清除用**自己的**群組；`R-01` 的第一半（固定 compose 呼叫）照做；而「連線在 COMMIT 前中斷是安全的」這個結論**改以可執行測試證明**（`tests_pg` 雙連線 ＋ `pg_terminate_backend`），不是補一段敘述 |

**另一處對上游的偏離（第 6 項，與上表同等揭露）**：
`security-design.md §3.1` 的步驟順序是「1. 先寫稽核 → 2. 再刪記憶」。
本計畫改以**單一 data-modifying CTE**（`DELETE ... RETURNING` 餵給 `INSERT`）。
理由：§3.1 要防的中間狀態（記憶已消失而稽核不存在）在單一交易內**不存在**，
而 CTE 形式額外使 `NFR7.11` 的「刪 N 列 ⇒ N 筆稽核」**結構上恆等**——
兩條獨立敘述之間的謂詞會被重新求值（兩次 `now()` 不同值）。以 `R6` 鎖住集合相等。

## 計畫摘要

| 項目 | 值 |
|---|---|
| 交付物 | **14 個檔，7 新 7 改**：2 個 workflow、3 個 `.sql`（清除／dry-run／驗證）、1 個 seed 腳本、2 個測試檔、`schema_rbac.sql` 的新 `K)` 區塊、`ci.yml` 一個步驟、`DEPLOY.md` 新 §2.2.11 |
| 步驟數 | **12 步**（含 6 項突變驗證） |
| 零 Python 應用程式邏輯 | 本單元是 `packaging`：零端點、零前端面、零 ORM 模型。`openapi.json` 與 `api.d.ts` 不動 |
| `backend/database.py` | diff **必須為空**（開工前記錄基準，收尾複驗） |
| 新依賴 | **零**。`requirements.txt` 不變 |
| 新 GitHub secret | **零**。watchdog 只用內建 `GITHUB_TOKEN` |
| 新部署設定 | **零**（`NFR8.10`）。不動 `deploy/`、`render-env.sh`、任一 `.env.example` |
| 新權限 | **一項**：watchdog 的 `issues: write`，本 repo **無先例**（`OPEN-ID9-2`，替代方案已寫明且不需重新設計） |
| `LOCAL-DEV.md` | **不觸發**（四個觸發條件皆不涉及） |
| `DEPLOY.md` | **觸發，blocking**（seed 是對 baseline 表的變更） |

## 測試摘要

| 載體 | 條數 | 執行者 | 本單元是否新建基礎設施 |
|---|---|---|---|
| `backend/tests/test_retention_purge_contract.py`（靜態契約） | 8 | 既有 `backend` job | 否，沿用 |
| `backend/tests_pg/test_purge_atomicity.py`（真實 PG、雙連線） | 3 | 既有 `concurrency` job（`U19` 交付），**不需改 `ci.yml`** | 否，沿用 |
| `backend/scripts/verify_purge_sql.sql`（`R1`–`R10`）＋ `verify_memory_schema.sql` 的 `S13` | 11 | 既有 `memory-schema` job ＋ **一個新步驟** | 否，沿用 job |
| **合計** | **22 條二元可判斷言** | | **零新 job、零新依賴** |

**三個載體缺一都會留下一塊 CI 完全看不到的失敗面**：靜態契約擋 `RETURNING *`
與刪錯列的條件；`verify_purge_sql.sql` 驗「選到的是哪些列」（而非只有幾列）；
`tests_pg` 驗交易在連線中斷下的原子性。

**本計畫把三道原本「CI 不會抓」的禁令變成 CI 會抓**：`RETURNING *`（公開 log
洩漏個人對話歷程）、缺 `kind = 'episodic'`（刪錯列）、缺 `status=success`
（每天都失敗被判為新鮮）。

## 覆蓋率的誠實限定

`org.md` 宣告 80% line coverage。本 repo **沒有覆蓋率量測機制**
（`team.md` 逐字「既無法量測也無法強制，是宣告而非閘門」），而本單元交付的是
SQL 與 YAML——Python 覆蓋率工具量不到它們。
**計畫不宣稱滿足該數字、也不弱化它**，改以上述 22 條斷言 ＋ 6 項突變驗證
作為本單元的實際門檻，並如實記載落差。

## 承接自上游而本站不解決的開放項（9 項）

`OPEN-CG9-1`（上游 `NFR7.10` 判準文字仍漏 `kind`）、
`OPEN-CG9-2`（`verify_password` 應捕捉 `ValueError`——**既有**的潛在 500，
非本單元引入，且 `auth.py` 不屬本 `packaging` 單元）、
`OPEN-ND9-1`（哨符列會讓 `/api/auth/list` 的 `total` +1）、
`OPEN-ND9-2`（是否新增受限資料庫角色）、
`OPEN-ID9-1`（沒有人監看監看者）、
`OPEN-ID9-2`（`issues: write` 無先例）、
`OPEN-ID9-3`（本計畫以 `S13` ＋ `verify_purge_sql.sql` **部分關閉**）、
`OPEN-ID9-4`（不可逆操作的前置 dry-run，已依 `R-02` 強化為印出選取範圍邊界而非只有計數）、
`OPEN-CG5-1`（grant 邊界未被 CI 驗證）。

**另外：`tcms-test-cases` 是 blocking 且至今未對本 intent 的任何單元執行過。**

## Plan Approval

[Approval Fingerprint]: sha256:v3:82aa0febc127e6fd8c94cdd06b75a981f56c2ff54a982eab4b9668f5a1456870
[Planned Source]: 67208adabc43cf40e3b9d141cd975576935daa5128d643fd1ca7393208f120ca

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
