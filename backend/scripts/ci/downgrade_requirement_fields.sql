-- downgrade_requirement_fields.sql — 只給 CI 的 `memory-schema` job 用（U20 步驟 A）
--
-- 把 `system_requirement_fields.updated_on_behalf_of` 改回 `U18` 的**舊定義**
-- （`INTEGER REFERENCES users (id)`），模擬「`U18` 先上線並跑過遷移、`U20` 後上線」
-- 的資料庫（`infrastructure-specification.md §二` 第二列）。之後的步驟 B 以
-- `run_meta_schema_migration.py` 收斂它，驗的就是 staging 實際會走的那條路。
--
-- **只能跑在可丟棄的 service container 上**：它改的是正式表的欄位定義。
-- 外鍵名稱刻意用 PostgreSQL 對舊定義自動產生的那一個，使這個資料庫與真的用舊
-- `J)` 區塊建出來的無法區分；收斂敘述本身不依賴這個名稱（以 conkey 查）。
--
-- 以 `psql -v ON_ERROR_STOP=1 -f` 執行。

\set ON_ERROR_STOP on

BEGIN;

-- 前置守衛：表必須是空的。步驟 A 的前提是「舊定義、尚無任何代寫值」，而
-- verify_meta_schema.sql 以 ROLLBACK 結尾、不留列。若這裡有列，表示步驟順序被
-- 改動了——繼續下去會把那些列的 updated_on_behalf_of 清成 NULL，而紅燈原因
-- 會出現在後面某一步、看不出根因。
DO $$
DECLARE
  n bigint;
BEGIN
  SELECT count(*) INTO n FROM public.system_requirement_fields;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'downgrade 前置條件不符：system_requirement_fields 應為空，實際 % 列。'
      '本腳本只應在 verify_meta_schema.sql（以 ROLLBACK 結尾）之後、'
      '寫入任何 fixture 之前執行', n;
  END IF;
END $$;

ALTER TABLE public.system_requirement_fields
  ALTER COLUMN updated_on_behalf_of TYPE INTEGER USING NULL;

ALTER TABLE public.system_requirement_fields
  ADD CONSTRAINT system_requirement_fields_updated_on_behalf_of_fkey
  FOREIGN KEY (updated_on_behalf_of) REFERENCES public.users (id);

-- 後置自我確認：舊定義確實已就位。否則步驟 B 的「收斂成功」可能只是「本來就
-- 不需要收斂」，而那兩種情形在結束碼上長得一樣。
DO $$
DECLARE
  v text;
  n int;
BEGIN
  SELECT data_type INTO v FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'system_requirement_fields'
     AND column_name = 'updated_on_behalf_of';
  IF v IS DISTINCT FROM 'integer' THEN
    RAISE EXCEPTION 'downgrade 未生效：updated_on_behalf_of 的型別為 %', v;
  END IF;

  SELECT count(*) INTO n
    FROM pg_constraint con
    JOIN pg_class t ON t.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = t.relnamespace
    JOIN pg_attribute a
      ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
   WHERE ns.nspname = 'public' AND t.relname = 'system_requirement_fields'
     AND con.contype = 'f' AND a.attname = 'updated_on_behalf_of';
  IF n <> 1 THEN
    RAISE EXCEPTION 'downgrade 未生效：updated_on_behalf_of 上的外鍵數為 %', n;
  END IF;

  RAISE NOTICE 'downgrade 完成：updated_on_behalf_of 已回到 U18 舊定義（integer ＋ 外鍵）';
END $$;

COMMIT;
