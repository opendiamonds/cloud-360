-- verify_purge_sql.sql — `U9 memory-purge` 的 10 條行為斷言（`R1`–`R10`）
--
-- 由 CI job `memory-schema` 對**真實 PostgreSQL** 執行，**須於 repo 根目錄**：
--
--     psql -v ON_ERROR_STOP=1 -f backend/scripts/verify_purge_sql.sql
--
-- 本檔以 `\i backend/scripts/purge_expired_memory.sql` 引入**生產用的那一份**
-- 清除 SQL，而 `\i` 的相對路徑是相對於 `psql` 的工作目錄。`ci.yml` 的
-- `memory-schema` job 沒有 `working-directory` 覆寫，故預設即為根目錄。
--
-- **`\i` 是刻意的**：CI 與生產因此跑同一份文字，不可能漂移。若改成在本檔重寫
-- 一份等價的 SQL，那就變成兩份會各自演化的副本，而這整個檔案存在的理由
-- （驗「清除會選到哪些列」）就只驗到副本。
--
-- =============================================================================
-- 警告：本檔會**真的刪除資料**，且**無法回滾**
-- =============================================================================
--
-- `verify_memory_schema.sql` 的行為類斷言以 `BEGIN; … ROLLBACK;` 包起來，所以它
-- 不留痕跡。**本檔做不到那件事**：它引入的清除 SQL 自己帶 `COMMIT`。
--
-- 故 **只能對可丟棄的資料庫執行**（CI 的 service container、或本機一個拋棄式
-- 資料庫）。為了讓「對錯的資料庫執行」不是一個只靠讀註解避免的錯誤，下方
-- 「前置守衛」會在引入清除 SQL **之前**檢查：若資料庫內存在**不屬於本檔
-- fixture** 的逾期 episodic 記憶、或不屬於 fixture 的逾期稽核列，就
-- `RAISE EXCEPTION` 並中止——那些列會被真的刪掉，而它們可能是真實資料。
--
-- =============================================================================
-- 檔案結構（三段，順序不可換）
-- =============================================================================
--
--   1. 清理前次殘留 → 建立 fixture（六類邊界列）→ 前置守衛 → 快照
--   2. `\i backend/scripts/purge_expired_memory.sql`
--   3. 斷言 `R1`–`R10` → 清理本次 fixture
--
-- 斷言形狀沿用 `verify_memory_schema.sql` 既有的
-- `DO $$ BEGIN IF NOT … THEN RAISE EXCEPTION … END IF; END $$;` 樣板。
-- `-v ON_ERROR_STOP=1` 使任一條 `RAISE EXCEPTION` 讓整個 `psql` 以非零碼結束。

\set ON_ERROR_STOP on

-- =====================================================================
-- 第 1 段：fixture
--
-- fixture 的時間戳一律相對於 `now()`，不寫死日期——寫死日期的 fixture 會在
-- 某個未來日期無聲地改變語意。
-- fixture 的 `content` 一律帶固定前綴 `__u9_fixture__`，清理時依該前綴刪除，
-- 不碰同一座資料庫上的其他資料（**不得** TRUNCATE：一個會清空整張表的清理
-- 動作，在本單元的語境下與被測的缺陷長得一樣）。
-- =====================================================================

BEGIN;

-- 前次殘留的清理（可重跑）。順序：稽核 → 記憶 → owner。
-- 稽核列對 memory_records **沒有外鍵**（`DG-1`），故必須自己刪。
DELETE FROM memory.memory_audit_events
 WHERE memory_id IN (
   SELECT id FROM memory.memory_records WHERE content LIKE '\_\_u9\_fixture\_\_%'
 );
DELETE FROM memory.memory_audit_events
 WHERE actor_user_id IN (
   SELECT id FROM users WHERE username = '__verify_purge_sql__'
 );
DELETE FROM memory.memory_records WHERE content LIKE '\_\_u9\_fixture\_\_%';
DELETE FROM users WHERE username = '__verify_purge_sql__';

-- fixture 的 owner。**不得重用哨符列當 owner**——`R7` 正是要驗兩者不同。
INSERT INTO users (username, password_hash, role, is_active)
VALUES ('__verify_purge_sql__', 'unused', 'Project_Architect', true)
ON CONFLICT (username) DO NOTHING;

-- 快照表：`R5`／`R6` 要比對的是「本次清除**新增**的稽核列」與「本次清除
-- **刪除**的記憶列」，兩者都必須在清除之前先記下來，否則只能靠「資料庫裡剛好
-- 沒有別的列」這個假設——而那個假設本身就是本檔要防的錯誤之一。
CREATE TEMP TABLE u9_fixture_memory (label text PRIMARY KEY, memory_id int NOT NULL);
CREATE TEMP TABLE u9_fixture_audit (label text PRIMARY KEY, audit_id int NOT NULL);
CREATE TEMP TABLE u9_audit_before (audit_id int PRIMARY KEY);
CREATE TEMP TABLE u9_ids (label text PRIMARY KEY, value int NOT NULL);

DO $$
DECLARE
  owner_id int;
  sentinel_id int;
  mid int;
  aid int;
  stray int;
BEGIN
  SELECT id INTO owner_id FROM users WHERE username = '__verify_purge_sql__';
  SELECT id INTO sentinel_id FROM users WHERE username = 'SYSTEM.retention-purge';
  IF sentinel_id IS NULL THEN
    RAISE EXCEPTION
      'fixture 無法建立：保留系統 actor（SYSTEM.retention-purge）不存在。'
      '它是 schema_rbac.sql 的 K) 區塊 seed 的；目標資料庫沒有套用過該區塊。'
      '這不是本檔的斷言失敗，是前置條件不足——清除本身也會在這個資料庫上失敗';
  END IF;
  INSERT INTO u9_ids (label, value) VALUES ('owner', owner_id), ('sentinel', sentinel_id);

  -- a：episodic ＋ 已逾期 → **應被刪除**，並產生 1 筆 purged_by_retention
  INSERT INTO memory.memory_records
    (kind, owner_user_id, visibility_scope, content, embedding_model, expires_at)
  VALUES ('episodic', owner_id, 'private', '__u9_fixture__a expired episodic',
          'bge-m3', now() - interval '1 day')
  RETURNING id INTO mid;
  INSERT INTO u9_fixture_memory (label, memory_id) VALUES ('a', mid);

  -- b：episodic ＋ 未逾期 → 應保留（邊界的另一側）
  INSERT INTO memory.memory_records
    (kind, owner_user_id, visibility_scope, content, embedding_model, expires_at)
  VALUES ('episodic', owner_id, 'private', '__u9_fixture__b future episodic',
          'bge-m3', now() + interval '1 day')
  RETURNING id INTO mid;
  INSERT INTO u9_fixture_memory (label, memory_id) VALUES ('b', mid);

  -- c：**semantic ＋ 已逾期** → 應保留。這是本單元最嚴重缺陷的陷阱列：
  --    `ck_memory_records_episodic_has_expiry` 只要求「episodic ⇒ 非 NULL」，
  --    不禁止非 episodic 帶 expires_at，所以這種列是資料庫允許的真實狀態；
  --    而 `FR4.5` 的 90 天**只**約束 episodic。清除少了 kind 條件就會刪掉它。
  INSERT INTO memory.memory_records
    (kind, owner_user_id, visibility_scope, content, embedding_model, expires_at)
  VALUES ('semantic', owner_id, 'private', '__u9_fixture__c expired semantic TRAP',
          'bge-m3', now() - interval '1 day')
  RETURNING id INTO mid;
  INSERT INTO u9_fixture_memory (label, memory_id) VALUES ('c', mid);

  -- d：procedure ＋ expires_at IS NULL → 應保留
  INSERT INTO memory.memory_records
    (kind, owner_user_id, visibility_scope, content, embedding_model, expires_at)
  VALUES ('procedure', owner_id, 'private', '__u9_fixture__d procedure no expiry',
          'bge-m3', NULL)
  RETURNING id INTO mid;
  INSERT INTO u9_fixture_memory (label, memory_id) VALUES ('d', mid);

  -- e：稽核列，91 天前 → **應被刪除**（交易二）
  INSERT INTO memory.memory_audit_events
    (memory_id, actor_user_id, action, occurred_at)
  VALUES (-991, owner_id, 'deleted_by_user', now() - interval '91 days')
  RETURNING id INTO aid;
  INSERT INTO u9_fixture_audit (label, audit_id) VALUES ('e', aid);

  -- f：稽核列，89 天前 → 應保留（邊界的另一側）
  INSERT INTO memory.memory_audit_events
    (memory_id, actor_user_id, action, occurred_at)
  VALUES (-989, owner_id, 'deleted_by_user', now() - interval '89 days')
  RETURNING id INTO aid;
  INSERT INTO u9_fixture_audit (label, audit_id) VALUES ('f', aid);

  -- ---------------------------------------------------------------
  -- 前置守衛：本檔即將執行一個**不可回滾**的刪除。
  -- ---------------------------------------------------------------
  SELECT count(*) INTO stray
    FROM memory.memory_records
   WHERE kind = 'episodic' AND expires_at < now()
     AND id NOT IN (SELECT memory_id FROM u9_fixture_memory);
  IF stray > 0 THEN
    RAISE EXCEPTION
      '前置守衛中止（這不是斷言失敗）：目標資料庫有 % 列不屬於本檔 fixture 的'
      '逾期 episodic 記憶。本檔引入的清除 SQL 自己帶 COMMIT，**無法回滾**，'
      '所以繼續執行會真的刪掉那些列。請改對一個可丟棄的資料庫執行'
      '（CI 的 service container，或本機一個拋棄式資料庫）', stray;
  END IF;

  SELECT count(*) INTO stray
    FROM memory.memory_audit_events
   WHERE occurred_at < now() - interval '90 days'
     AND id NOT IN (SELECT audit_id FROM u9_fixture_audit);
  IF stray > 0 THEN
    RAISE EXCEPTION
      '前置守衛中止（這不是斷言失敗）：目標資料庫有 % 列不屬於本檔 fixture 的'
      '逾期稽核事件。理由同上——本檔無法回滾', stray;
  END IF;

  -- 清除之前的稽核列快照，供 `R5`／`R6` 判定「哪些是新增的」。
  INSERT INTO u9_audit_before (audit_id)
  SELECT id FROM memory.memory_audit_events;

  RAISE NOTICE 'fixture 就緒：4 列記憶（a 逾期 episodic／b 未逾期 episodic／'
               'c 逾期 semantic 陷阱列／d procedure 無到期）＋ 2 列稽核'
               '（e 91 天前／f 89 天前）；前置守衛通過';
END $$;

COMMIT;

-- =====================================================================
-- 第 2 段：引入**生產用的那一份**清除 SQL
-- =====================================================================

\echo '=== 執行 backend/scripts/purge_expired_memory.sql（生產用的同一份文字） ==='
\i backend/scripts/purge_expired_memory.sql
\echo '=== 清除完成，開始斷言 R1-R10 ==='

-- =====================================================================
-- 第 3 段：斷言 R1-R10
-- =====================================================================

DO $$
DECLARE
  n int;
  m int;
  id_a int;
  id_b int;
  id_c int;
  id_d int;
  id_e int;
  id_f int;
  owner_id int;
  sentinel_id int;
BEGIN
  SELECT memory_id INTO id_a FROM u9_fixture_memory WHERE label = 'a';
  SELECT memory_id INTO id_b FROM u9_fixture_memory WHERE label = 'b';
  SELECT memory_id INTO id_c FROM u9_fixture_memory WHERE label = 'c';
  SELECT memory_id INTO id_d FROM u9_fixture_memory WHERE label = 'd';
  SELECT audit_id  INTO id_e FROM u9_fixture_audit  WHERE label = 'e';
  SELECT audit_id  INTO id_f FROM u9_fixture_audit  WHERE label = 'f';
  SELECT value INTO owner_id    FROM u9_ids WHERE label = 'owner';
  SELECT value INTO sentinel_id FROM u9_ids WHERE label = 'sentinel';

  -- R1：逾期 episodic 列已不存在。
  SELECT count(*) INTO n FROM memory.memory_records WHERE id = id_a;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'R1 FAILED (FR4.5／NFR7.10): 逾期的 episodic 列（fixture a）應已被刪除，'
      '實際仍有 % 列。清除根本沒有選到它——90 天保存期沒有在運作', n;
  END IF;

  -- R2：未逾期 episodic 列仍存在。
  SELECT count(*) INTO n FROM memory.memory_records WHERE id = id_b;
  IF n <> 1 THEN
    RAISE EXCEPTION
      'R2 FAILED (FR4.5): 未逾期的 episodic 列（fixture b）必須保留，實際 % 列。'
      '選取條件把尚未到期的記憶一起刪了', n;
  END IF;

  -- R3：procedure ＋ expires_at IS NULL 列仍存在。
  SELECT count(*) INTO n FROM memory.memory_records WHERE id = id_d;
  IF n <> 1 THEN
    RAISE EXCEPTION
      'R3 FAILED (FR4.5): procedure ＋ expires_at IS NULL 的列（fixture d）'
      '必須保留，實際 % 列', n;
  END IF;

  -- R4：**semantic ＋ 過去 expires_at 的列仍存在**（本單元最嚴重的缺陷面）。
  SELECT count(*) INTO n FROM memory.memory_records WHERE id = id_c;
  IF n <> 1 THEN
    RAISE EXCEPTION
      'R4 FAILED (FR4.5 僅約束 episodic): kind = semantic 而帶有過去 expires_at '
      '的列（fixture c）**必須保留**，實際 % 列。'
      '清除的 WHERE 少了 kind = episodic 這個條件——那是永久資料損失，'
      '且 FR4.5 明文不約束這類列。'
      'NFR7.10 的二元判準文字漏了這個條件（OPEN-CG9-1），實作刻意收窄', n;
  END IF;

  -- R5：新增的 purged_by_retention 稽核列數 **等於** 被刪的 episodic 列數。
  SELECT count(*) INTO n
    FROM memory.memory_audit_events e
   WHERE e.id NOT IN (SELECT audit_id FROM u9_audit_before)
     AND e.action = 'purged_by_retention';
  IF n <> 1 THEN
    RAISE EXCEPTION
      'R5 FAILED (NFR7.11／FR4.7): 本次清除刪除了 1 列 episodic 記憶，'
      '故應新增恰好 1 筆 purged_by_retention 稽核列，實際 % 筆', n;
  END IF;

  -- R6：每一筆新稽核列的 memory_id 都在被刪的 id 集合內，且無重複、無遺漏。
  --     **這才是 NFR7.11 真正的斷言**：R5 只比對數量，而數量相等但對應錯亂
  --     （重複記同一個 memory_id、漏一個）仍會通過 R5。R6 比對的是集合相等，
  --     而那是 FR4.7「刪除留稽核」在**列層級**的實際內容。
  SELECT count(*) INTO n
    FROM (
      SELECT e.memory_id
        FROM memory.memory_audit_events e
       WHERE e.id NOT IN (SELECT audit_id FROM u9_audit_before)
         AND e.action = 'purged_by_retention'
      EXCEPT
      SELECT id_a
    ) x;
  SELECT count(*) INTO m
    FROM (
      SELECT id_a
      EXCEPT
      SELECT e.memory_id
        FROM memory.memory_audit_events e
       WHERE e.id NOT IN (SELECT audit_id FROM u9_audit_before)
         AND e.action = 'purged_by_retention'
    ) y;
  IF n <> 0 OR m <> 0 THEN
    RAISE EXCEPTION
      'R6 FAILED (NFR7.11／FR4.7): 新稽核列的 memory_id 集合必須與被刪除的'
      ' episodic id 集合相等。多出 % 個、少了 % 個。'
      '數量相等但對應錯亂（重複記同一個 id、或漏一個）會通過 R5 而被 R6 擋下', n, m;
  END IF;
  -- 無重複：集合相等 ＋ 列數相等（R5）才排除「同一個 memory_id 記兩次」。
  SELECT count(*) INTO n
    FROM (
      SELECT e.memory_id
        FROM memory.memory_audit_events e
       WHERE e.id NOT IN (SELECT audit_id FROM u9_audit_before)
         AND e.action = 'purged_by_retention'
       GROUP BY e.memory_id
      HAVING count(*) > 1
    ) z;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'R6 FAILED (NFR7.11): 有 % 個 memory_id 被記了超過一次的稽核列', n;
  END IF;

  -- R7：新稽核列的 actor_user_id 等於哨符 username 的 id，且**不等於**
  --     任何 fixture 記憶的 owner_user_id。
  --     填記憶擁有者會讓稽核「對誰刪的」說謊（schema_rbac.sql 的 actor_user_id
  --     COMMENT 逐字）。
  SELECT count(*) INTO n
    FROM memory.memory_audit_events e
   WHERE e.id NOT IN (SELECT audit_id FROM u9_audit_before)
     AND e.action = 'purged_by_retention'
     AND e.actor_user_id = sentinel_id;
  IF n <> 1 THEN
    RAISE EXCEPTION
      'R7 FAILED (NFR7.11): 新稽核列的 actor_user_id 應為保留系統 actor 的 id'
      '（%），符合的列數 % 而非 1', sentinel_id, n;
  END IF;
  IF sentinel_id = owner_id THEN
    RAISE EXCEPTION
      'R7 FAILED (NFR7.11): 哨符列的 id 與 fixture owner 的 id 相同（%）——'
      'fixture 建錯了，這條斷言本身失去意義', sentinel_id;
  END IF;
  SELECT count(*) INTO n
    FROM memory.memory_audit_events e
   WHERE e.id NOT IN (SELECT audit_id FROM u9_audit_before)
     AND e.action = 'purged_by_retention'
     AND e.actor_user_id = owner_id;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'R7 FAILED (NFR7.11): 有 % 筆新稽核列把 actor 記成記憶擁有者。'
      '那會讓稽核對「誰刪的」說謊——清除是排程觸發、無人在迴圈內', n;
  END IF;

  -- R8：91 天前的稽核列已不存在（交易二）。
  SELECT count(*) INTO n FROM memory.memory_audit_events WHERE id = id_e;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'R8 FAILED (NFR7.2／NFR7.10): 91 天前的稽核列（fixture e）應已被刪除，'
      '實際仍有 % 列。本單元是 memory_audit_events 唯一的 DELETE 端——'
      '少了它，該表無上界成長且沒有任何其他機制會清它', n;
  END IF;

  -- R9：89 天前的稽核列仍存在（邊界的另一側）。
  SELECT count(*) INTO n FROM memory.memory_audit_events WHERE id = id_f;
  IF n <> 1 THEN
    RAISE EXCEPTION
      'R9 FAILED (NFR7.2): 89 天前的稽核列（fixture f）必須保留，實際 % 列。'
      '保存期被算短了', n;
  END IF;

  -- R10：交易一剛寫的稽核列**未被**交易二刪除。
  --      它們的 occurred_at 是 now()，不可能落在 90 天前，故**與兩個交易的
  --      先後無關**——是 90 天的時間差保證的。這條存在的理由是「清除會不會刪掉
  --      自己剛寫的稽核」是讀者會問的問題（security-design.md §3.1 第 3 列）。
  SELECT count(*) INTO n
    FROM memory.memory_audit_events e
   WHERE e.id NOT IN (SELECT audit_id FROM u9_audit_before)
     AND e.action = 'purged_by_retention';
  IF n <> 1 THEN
    RAISE EXCEPTION
      'R10 FAILED (security-design.md §3.1): 交易一寫入的 purged_by_retention '
      '稽核列在交易二之後應仍有 1 筆，實際 %。'
      '若為 0，代表稽核清除刪掉了清除自己剛寫的紀錄——FR4.7 在那一刻形同虛設', n;
  END IF;

  RAISE NOTICE 'R1-R10 全部通過（清除選對了列、稽核與刪除一一對應、'
               '稽核的 actor 是系統 actor、稽核保存期的兩側邊界正確、'
               '清除沒有刪掉自己剛寫的稽核）';
END $$;

-- =====================================================================
-- 清理：本檔的 fixture 不留在資料庫裡。
--
-- 依固定前綴／固定 username 刪除，**不** TRUNCATE、**不**使用無 WHERE 的 DELETE。
-- 哨符列（SYSTEM.retention-purge）是 seed，**不在清理範圍內**。
-- =====================================================================

BEGIN;

DELETE FROM memory.memory_audit_events
 WHERE memory_id IN (SELECT memory_id FROM u9_fixture_memory)
    OR id IN (SELECT audit_id FROM u9_fixture_audit);
DELETE FROM memory.memory_records
 WHERE id IN (SELECT memory_id FROM u9_fixture_memory);
DELETE FROM memory.memory_audit_events
 WHERE actor_user_id IN (SELECT value FROM u9_ids WHERE label = 'owner');
DELETE FROM users WHERE username = '__verify_purge_sql__';

COMMIT;

\echo '=== verify_purge_sql.sql 完成：R1-R10 全綠，fixture 已清理 ==='
