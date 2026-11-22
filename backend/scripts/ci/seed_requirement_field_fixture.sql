-- seed_requirement_field_fixture.sql — 只給 CI 的 `memory-schema` job 用（U20 步驟 C）
--
-- 在**已收斂**的資料庫上寫入一列帶代寫標示的需求欄位值，並**明確 COMMIT**。
-- 步驟 D 再跑一次 `run_meta_schema_migration.py` 之後斷言這一列的
-- `updated_on_behalf_of` 仍為 'cost'——那是 `NFR20.23` 的「重跑不清資料」。
--
-- **不得放進 verify_meta_schema.sql**：那支檔以 ROLLBACK 結尾，寫入不會留下，
-- 步驟 D 就會面對一張空表而「通過」。
--
-- fixture 的四列（user／project／system／requirement field）以固定名稱
-- `__u20_ci_fixture__` 識別，步驟 E 依外鍵順序清除，並在刪除 system 時順便斷言
-- `ON DELETE CASCADE`（`NFR20.16`）。
--
-- 以 `psql -v ON_ERROR_STOP=1 -f` 執行。

\set ON_ERROR_STOP on

BEGIN;

INSERT INTO public.users (username, password_hash, role, is_active)
VALUES ('__u20_ci_fixture__', 'unused', 'Project_Architect', true);

INSERT INTO public.projects (name, owner_user_id, is_default)
SELECT '__u20_ci_fixture__', id, false
  FROM public.users WHERE username = '__u20_ci_fixture__';

INSERT INTO public.systems (name, project_id, is_default)
SELECT '__u20_ci_fixture__', id, false
  FROM public.projects WHERE name = '__u20_ci_fixture__';

INSERT INTO public.system_requirement_fields
  (system_id, agent_group, field_key, value, updated_by, updated_on_behalf_of)
SELECT s.id, 'cost', 'sla', '99.9%', u.id, 'cost'
  FROM public.systems s
  JOIN public.projects p ON p.id = s.project_id
  JOIN public.users u ON u.id = p.owner_user_id
 WHERE s.name = '__u20_ci_fixture__' AND u.username = '__u20_ci_fixture__';

-- 自我確認：恰好一列帶代寫標示的值已寫入（否則步驟 D 的斷言會面對空集合）。
DO $$
DECLARE
  n int;
BEGIN
  SELECT count(*) INTO n
    FROM public.system_requirement_fields f
    JOIN public.systems s ON s.id = f.system_id
   WHERE s.name = '__u20_ci_fixture__' AND f.updated_on_behalf_of = 'cost';
  IF n <> 1 THEN
    RAISE EXCEPTION 'fixture 寫入失敗：預期 1 列帶 updated_on_behalf_of = cost，實際 %', n;
  END IF;
END $$;

COMMIT;
