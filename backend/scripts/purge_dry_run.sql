-- purge_dry_run.sql — `U9 memory-purge` 的不可逆操作前置驗證（`OPEN-ID9-4`）
--
-- **這不是測試建議，是一個不可逆操作的前置驗證。**
-- `cicd-pipeline.md §五之一` 逐字：workflow 檔的變更可 `git revert`、系統 actor
-- seed 可重建，但**已執行的清除不可回滾**——刪除的記憶與稽核列無法復原。
-- 故首次啟用排程之前，必須先以
--   `workflow_dispatch` ＋ `dry_run=true`
-- 跑本檔，人工核對選取條件。
--
-- =============================================================================
-- 唯讀，而且這件事是被機械檢查的
-- =============================================================================
--
-- 本檔**只有 SELECT**：零 DELETE、零 INSERT、零 UPDATE。
-- `backend/tests/test_retention_purge_contract.py` 的 `test_dry_run_sql_is_read_only`
-- 以不分大小寫的子字串比對鎖住這一點——一個名不副實的 dry-run 比沒有 dry-run
-- 更糟，因為操作者會據它按下啟用。
--
-- =============================================================================
-- 為什麼不只印計數（審查 `R-02`）
-- =============================================================================
--
-- `OPEN-ID9-4` 原本只要求 `SELECT count(*)`。審查 `R-02` 指出那驗證的是
-- 「有沒有命中」而不是「**命中的是不是對的那批列**」：一個把 `expires_at` 與
-- `created_at` 寫反、或時區換算錯誤的選取條件，仍可能回一個看起來合理的非零
-- 數字而通過人工目視——**而那正是 `OPEN-ID9-4` 自己點名要防的那類錯誤**。
--
-- 故本檔除計數外，對兩個集合各印出**選取範圍的邊界**（最舊與最新的時間戳）
-- 與**最多 10 筆 id ＋ 其時間戳**，讓人工核對看到「選到的是哪些列」。
--
-- =============================================================================
-- 不得印出的內容
-- =============================================================================
--
-- **`content`、`embedding`、`owner_user_id`，或任何可識別資料一律不印。**
-- 本 repo 為 public、Actions log 公開可讀，而本檔描述的是個人對話歷程
-- （`monitoring-design.md §五`）。下方每一個 SELECT 的欄位清單都只有
-- `id`／`kind`／時間戳／計數——沒有 `*`，沒有 `content`。
-- `kind` 會被印出是刻意的：它是本單元最嚴重那個缺陷（刪到非 episodic 的列）
-- 的唯一可見判別欄，而它本身不含任何使用者資料。

\set ON_ERROR_STOP on

\echo '=== dry run: 本檔只讀取，不刪除任何一列 ==='
\echo ''
\echo '--- [1] 逾期 episodic 記憶（清除的交易一會刪除這些，並各寫一筆稽核） ---'

SELECT count(*) AS would_delete_memories,
       min(expires_at) AS oldest_expires_at,
       max(expires_at) AS newest_expires_at,
       now() AS cutoff_now
  FROM memory.memory_records
 WHERE kind = 'episodic'
   AND expires_at < now();

\echo '--- [1b] 上述集合的前 10 筆（最舊優先）：只有 id、kind、時間戳 ---'

SELECT id, kind, created_at, expires_at
  FROM memory.memory_records
 WHERE kind = 'episodic'
   AND expires_at < now()
 ORDER BY expires_at ASC, id ASC
 LIMIT 10;

\echo ''
\echo '--- [2] 對照組：**不該**被刪的逾期列（kind 不是 episodic） ---'
\echo '    這一欄應該是 0 以外的值也沒關係——重點是清除之後它們必須還在。'
\echo '    `FR4.5` 只約束 episodic；少了 kind 條件時這些列會被誤刪。'

SELECT kind,
       count(*) AS must_be_kept,
       min(expires_at) AS oldest_expires_at,
       max(expires_at) AS newest_expires_at
  FROM memory.memory_records
 WHERE kind <> 'episodic'
   AND expires_at IS NOT NULL
   AND expires_at < now()
 GROUP BY kind
 ORDER BY kind;

\echo ''
\echo '--- [3] 逾期稽核事件（清除的交易二會刪除這些；本動作自己不留稽核） ---'

SELECT count(*) AS would_delete_audit_rows,
       min(occurred_at) AS oldest_occurred_at,
       max(occurred_at) AS newest_occurred_at,
       (now() - interval '90 days') AS cutoff_occurred_at
  FROM memory.memory_audit_events
 WHERE occurred_at < now() - interval '90 days';

\echo '--- [3b] 上述集合的前 10 筆（最舊優先）：只有 id、action、時間戳 ---'

SELECT id, action, occurred_at
  FROM memory.memory_audit_events
 WHERE occurred_at < now() - interval '90 days'
 ORDER BY occurred_at ASC, id ASC
 LIMIT 10;

\echo ''
\echo '--- [4] 前置條件：保留系統 actor 必須存在，否則清除的稽核 INSERT 會讓整個交易中止 ---'

SELECT count(*) AS system_actor_rows,
       bool_and(is_active IS FALSE) AS all_inactive
  FROM users
 WHERE username = 'SYSTEM.retention-purge';

\echo ''
\echo '=== dry run 結束：一列都沒有被刪除 ==='
