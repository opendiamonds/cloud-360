-- purge_expired_memory.sql — `U9 memory-purge` 的清除本體（`FR4.5`／`NFR7.10`）
--
-- 由 `.github/workflows/memory-retention-purge.yml` 以**單一** `psql` 呼叫執行，
-- 並由 `backend/scripts/verify_purge_sql.sql` 以 `\i` 引入後在 CI 斷言
-- ——**CI 與生產跑的是同一份文字**，不可能漂移。
--
-- =============================================================================
-- 兩個交易，都寫在這個檔案裡
-- =============================================================================
--
-- `infrastructure-design/cicd-pipeline.md §三之一` 要求「步 1＋2 必須在**同一次
-- `psql` 呼叫**內」，並逐字警告那個錯誤「在 YAML 上看起來很自然（『一個步驟做一件
-- 事』）」。把交易邊界寫進**檔案**而不是 workflow，使那個要求**結構上不可能被
-- 拆步驟破壞**：無論呼叫端怎麼切 Actions step，邊界都在這裡。
--
-- =============================================================================
-- 絕對禁令：只許 `RETURNING id`
-- =============================================================================
--
-- 本 repo 為 public，**Actions log 公開可讀**，而本檔處理的是**個人對話歷程**。
-- 把 `RETURNING id` 的欄位清單換成「全部欄位」的那個星號寫法，會把 `content`
-- 印進公開 log
-- （本檔刻意不寫出那個字面樣式。靜態斷言其實已經不會被註解誤導——它比對的是
-- **剝掉註解與 psql 元指令之後的可執行 SQL**，理由見該測試檔的說明——但
-- 一個「示範禁令」的註解仍然沒有存在的價值，而它會讓任何改用整檔比對的人
-- 立刻得到一條永遠紅燈的斷言。）
-- （`monitoring-design.md §五之一`：「一個單字之差、CI 不會抓、而後果是公開發布
-- 使用者的私人對話歷程」）。
-- **CI 現在會抓了**：`backend/tests/test_retention_purge_contract.py` 的
-- `test_purge_sql_never_returns_all_columns` 是一條靜態斷言。
--
-- =============================================================================
-- 連線身分
-- =============================================================================
--
-- 本檔**不含任何連線參數**（無身分覆寫、無連線字串、無密碼）。連線由呼叫端以
-- `docker compose exec -T db` 進入容器後建立，身分固定為 `POSTGRES_USER`
-- （`NFR6.10`；該需求目前的實質內容是「不得顯式以更高權限覆寫」，見
-- `nfr-design/security-design.md §二`）。
--
-- =============================================================================
-- 冪等且自我收斂，故不需要重試
-- =============================================================================
--
-- 選取條件是 `expires_at < now()`：已刪除的列不會再被選到，未刪除的下次仍會。
-- 任一交易失敗則該交易整個回滾，`psql` 以非零碼結束（下方 `ON_ERROR_STOP`），
-- 下一次排程自然重試。**不設 retry／backoff**（`security-design.md §三之三`）。

\set ON_ERROR_STOP on

-- =============================================================================
-- 交易一：刪除逾期的 episodic 記憶，並為每一列寫一筆 `purged_by_retention` 稽核
-- =============================================================================
--
-- **為什麼是一條敘述，而不是上游 §3.1 的兩步（先寫稽核、再刪記憶）**
--
-- 上游那個順序的理由逐字是「稽核必須先於它描述的對象消失落地」，要防的是
-- **中途失敗留下「記憶已消失而稽核不存在」**。在單一交易內兩者同時於 COMMIT
-- 落地，那個中間狀態**不存在**，所以兩步的順序在這裡沒有可觀察的差別。
--
-- 而 data-modifying CTE 的形式**比兩步更強一層**，有兩個具體理由：
--
--   1. 稽核列的來源是 DELETE 自己的 `RETURNING`，故「刪 N 列 ⇒ N 筆稽核」
--      （`NFR7.11`）是**結構上的恆等**，不是兩條敘述碰巧選到同一批列。
--   2. 兩條獨立敘述之間的謂詞會被**重新求值**，而 `now()` 在同一交易內雖然固定，
--      但「兩個 WHERE 子句必須逐字一致」這件事沒有任何機制保證——改了一邊忘了
--      另一邊，就會得到「稽核數 ≠ 刪除數」，而那是靜默的。
--
-- PostgreSQL 保證 `WITH` 內的 data-modifying 敘述**各執行恰好一次並且跑到完成**，
-- 與主查詢是否讀取它們的輸出無關，所以 `logged` 不會因為只被 count() 讀到而被略過。
--
-- **這是對已核可上游（`security-design.md §3.1`）的步驟順序的偏離**，理由如上，
-- 並由 `verify_purge_sql.sql` 的 `R6`（集合相等）鎖住恆等性。
--
-- 哨符 username 必須與 `schema_rbac.sql` 的 `K)` 區塊、以及
-- `backend/scripts/seed_retention_system_actor.py` 的 `SENTINEL_USERNAME`
-- **三者逐字相同**（由 `test_sentinel_username_has_one_source` 鎖住）。
-- 以 username 查 id 而不寫死整數：`users.id` 是 `SERIAL`，值因環境而異，
-- 寫死會在某個環境指到**另一個真實使用者**，使稽核說謊。查不到時子查詢回 NULL
-- → `actor_user_id` 的 `NOT NULL` 違反 → 整個交易中止，而**大聲失敗是這裡要的行為**。
BEGIN;

WITH purged AS (
  DELETE FROM memory.memory_records
   -- `kind = 'episodic'` 不可省。`FR4.5` 逐字只約束 episodic memory
   -- （`requirements.md:157`），`schema_rbac.sql` 的 `expires_at` COMMENT 也逐字
   -- 「FR4.5 scopes the 90-day retention to episodic memory ONLY」。
   -- 而 `ck_memory_records_episodic_has_expiry` 只要求「episodic ⇒ expires_at
   -- 非 NULL」，**沒有**反向要求「非 episodic ⇒ NULL」——所以一列
   -- `kind = 'semantic'` 而恰好帶了過去 `expires_at` 的記憶，在少了這個條件時
   -- **會被刪除**，而那是 `FR4.5` 明文不約束的永久資料損失。
   -- 驗於 `verify_purge_sql.sql` 的 `R4`（fixture 內刻意放了那樣一列）。
   WHERE kind = 'episodic'
     AND expires_at < now()
  RETURNING id
), logged AS (
  INSERT INTO memory.memory_audit_events (memory_id, actor_user_id, action)
  SELECT p.id,
         (SELECT id FROM users WHERE username = 'SYSTEM.retention-purge'),
         'purged_by_retention'
    FROM purged p
  RETURNING id
)
SELECT (SELECT count(*) FROM purged) AS memories_purged,
       (SELECT count(*) FROM logged) AS audit_rows_written;

COMMIT;

-- =============================================================================
-- 交易二（獨立）：刪除逾期的稽核事件列（`NFR7.2` 的 90 天保存）
-- =============================================================================
--
-- **獨立交易**：它與交易一沒有資料依賴（刪的是 90 天前的舊稽核）。綁在同一交易
-- 只會讓一個無關的失敗把整次清除回滾（`security-design.md §三之二`）。
--
-- **不會刪到交易一剛寫的那些列**：它們的 `occurred_at` 是 `now()`，不可能落在
-- 90 天前。這與兩個交易的先後**無關**，是 90 天的時間差保證的。
-- 驗於 `verify_purge_sql.sql` 的 `R10`。
--
-- **本動作自己不留稽核**（`NFR7.15`）：這裡只有 DELETE，沒有 INSERT。
-- 理由是無終止遞迴——`FR4.7` 約束的對象是**記憶**的刪除，不是稽核本身。
-- 故本交易執行後 `memory_audit_events` 的列數**只減不增**。
BEGIN;

WITH purged_audit AS (
  DELETE FROM memory.memory_audit_events
   WHERE occurred_at < now() - interval '90 days'
  RETURNING id
)
SELECT count(*) AS audit_rows_purged FROM purged_audit;

COMMIT;
