-- verify_memory_role.sql — 記憶專用角色 `cloud360_memory` 的邊界斷言（合併前必修第 20／29 列 (b)）
--
-- **必須以 `cloud360_memory` 本身連線執行**（CI 的 memory-schema job：先以擁有者帳號
-- 套用 schema_rbac.sql、以 deploy/initdb/02-memory-role-password.sh 設定密碼，再以該
-- 角色連線跑本檔）。以 superuser 跑本檔時 R0 會先擋下——superuser 讀得到一切，
-- R1 會恆真地「通過」。
--
-- 需要 psql 變數 `uid`：一個存在於 public.users 的 id（CI 以擁有者帳號先查出來傳入；
-- 本角色自己讀不到 users，所以無法自己查）。
--
--   R0 連線身分就是 cloud360_memory，且它不是 superuser
--   R1 讀不到 public schema 的**任一**表（逐表嘗試 SELECT，每一張都必須是 insufficient_privilege）
--   R2 寫得進 memory.memory_records、讀得回、刪得掉；寫得進 memory.memory_audit_events
--      （在交易內、最後 ROLLBACK，不留資料）
--   R3 不能在 public schema 建表
--
-- 每條不成立即 RAISE EXCEPTION，以 `psql -v ON_ERROR_STOP=1 -f` 執行時 job 紅燈。

\set ON_ERROR_STOP on

DO $$
DECLARE
  is_super boolean;
BEGIN
  SELECT rolsuper INTO is_super FROM pg_roles WHERE rolname = current_user;
  IF current_user <> 'cloud360_memory' THEN
    RAISE EXCEPTION 'R0 FAILED: 本檔必須以 cloud360_memory 連線執行，實際為 %', current_user;
  END IF;
  IF is_super THEN
    RAISE EXCEPTION 'R0 FAILED: cloud360_memory 是 superuser，邊界不存在';
  END IF;
END $$;

DO $$
DECLARE
  r record;
  n int := 0;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename LOOP
    n := n + 1;
    BEGIN
      EXECUTE format('SELECT 1 FROM public.%I LIMIT 1', r.tablename);
      RAISE EXCEPTION 'R1 FAILED: cloud360_memory 讀得到 public.%', r.tablename;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;  -- 預期：permission denied
    END;
  END LOOP;
  -- 沒有任何 public 表時 R1 恆真；schema_rbac.sql 套用後至少有 users 等十餘張。
  IF n = 0 THEN
    RAISE EXCEPTION 'R1 FAILED: public schema 沒有任何表，R1 無鑑別力（schema_rbac.sql 未套用？）';
  END IF;
  RAISE NOTICE 'R1 ok: % 張 public 表全部被拒', n;
END $$;

BEGIN;
INSERT INTO memory.memory_records (kind, owner_user_id, visibility_scope, content, embedding_model)
VALUES ('semantic', :uid, 'owner', 'ci-memory-role-probe', 'ci-probe');
INSERT INTO memory.memory_audit_events (memory_id, actor_user_id, action)
SELECT id, :uid, 'deleted_by_user' FROM memory.memory_records WHERE content = 'ci-memory-role-probe';
DO $$
DECLARE
  n int;
BEGIN
  SELECT count(*) INTO n FROM memory.memory_records WHERE content = 'ci-memory-role-probe';
  IF n <> 1 THEN
    RAISE EXCEPTION 'R2 FAILED: 寫入 memory.memory_records 後讀回 % 列（應為 1）', n;
  END IF;
  DELETE FROM memory.memory_records WHERE content = 'ci-memory-role-probe';
  RAISE NOTICE 'R2 ok: memory 兩表可寫、可讀、可刪';
END $$;
ROLLBACK;

DO $$
BEGIN
  BEGIN
    EXECUTE 'CREATE TABLE public.ci_memory_role_probe (id int)';
    RAISE EXCEPTION 'R3 FAILED: cloud360_memory 能在 public schema 建表';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'R3 ok: 不能在 public 建表';
  END;
END $$;
