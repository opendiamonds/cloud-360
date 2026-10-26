-- verify_meta_schema.sql — `U18 project-meta-data` 的 12 條斷言（`P1`–`P12`）
-- ＋ `U19 membership-service` 回補的 2 條（`P13`／`P14`，`[FD3]`=A 的 `cause` 欄）
-- ＋ `U20 requirement-field-service` 的 2 條（`P15`／`P16`，`[FD1]`=A 的
--   `updated_on_behalf_of` 欄型別與外鍵缺席，`BR47.3`）
--
-- **`P15`／`P16` 在全新資料庫上必然通過**——新的 `J)` 區塊直接建出 varchar(64)。
-- 它們真正要擋的是「舊定義資料庫的收斂沒發生」，所以 CI 的 `memory-schema` job
-- 在步驟 A（把欄位改回舊定義）→ B（跑 `run_meta_schema_migration.py`）之後
-- **再跑一次本檔**，讓這兩條面對的是一個真的經過收斂的資料庫。
--
-- 由 CI job `memory-schema` 對**真實 PostgreSQL** 執行（該 job 的名稱比它的內容窄，
-- 理由見 `.github/workflows/ci.yml` 內該 job 的註解）。
--
-- **為什麼不是 Python 測試**：既有測試在 `backend/tests/helpers.py` 換掉驅動、改走
-- in-memory SQLite，而本單元要驗的是 **PostgreSQL 的約束、外鍵缺席、partial index
-- 與 CASCADE 行為**——SQLite 對這些的語意不同（外鍵預設關閉、`ON DELETE` 行為需
-- `PRAGMA`、無 partial index 的同等查詢計畫）。在 SQLite 上「通過」不構成任何保證。
--
-- 每條斷言不成立即 RAISE EXCEPTION，使 psql 以非零碼結束、job 紅燈。
-- 以 `psql -v ON_ERROR_STOP=1 -f` 執行。
--
-- 斷言分佈 4／4／4（三張表＝三個 component，`standard` 策略要求每個 5–8 個測試；
-- 本單元是 DDL，可觀察行為少於一般 component，故落在區間下緣）。
--
-- **`U19` 回補的兩條**（`P13`／`P14`）使 `reselection_events` 那一群成為 6 條。
-- 它們驗的是 `[FD3]`=A 的 `cause` 欄：存在且 NOT NULL（`P13`）、CHECK 恰含那
-- 兩個值（`P14`）。**為什麼它們不能只靠 ORM 側的一致性測試**：ORM 測試比對的是
-- 「ORM 宣告 vs DDL 文字」，而這兩條驗的是「**真實 PostgreSQL 上實際建出來的
-- 東西**」——`create_all()` 那條建表路徑建出的表沒有 COMMENT 也不經本檔，
-- 兩條路徑不等價（`OPEN-ID19-1`）。

\set ON_ERROR_STOP on

-- =====================================================================
-- 結構類斷言：只讀系統目錄，不寫入任何資料
-- =====================================================================

DO $$
DECLARE
  n int;
  v text;
BEGIN
  -- -------------------------------------------------------------------
  -- A 群：project_members（BR1.1／BR2.1／[ND1]=A）
  -- -------------------------------------------------------------------

  -- P1：表存在於 public，且欄位集合**恰為** 6 欄（多一欄或少一欄皆紅）。
  SELECT count(*) INTO n FROM information_schema.tables
   WHERE table_schema = 'public' AND table_name = 'project_members';
  IF n <> 1 THEN
    RAISE EXCEPTION 'P1 FAILED: public.project_members 不存在';
  END IF;

  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'project_members';
  IF n <> 6 THEN
    RAISE EXCEPTION
      'P1 FAILED: project_members 應有 6 欄（id/project_id/user_id/role/'
      'joined_at/invited_by），實際 % —— 欄位集合變動須先更新 entities.md', n;
  END IF;

  -- P2：joined_at 為 NOT NULL。失敗模式是**靜默**的（見訊息）。
  SELECT is_nullable INTO v FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'project_members'
     AND column_name = 'joined_at';
  IF v <> 'NO' THEN
    RAISE EXCEPTION
      'P2 FAILED (BR1.1): joined_at 必須為 NOT NULL。FR12.4 的自動改選挑最早加入者'
      '並**直接讀它**；可為 null 會讓挑選在空值上無序——每次選出不同人而**沒有任何'
      '錯誤**。這是本單元唯一完全靜默的失敗模式';
  END IF;

  -- P3：project_id 的外鍵 ON DELETE 行為為 CASCADE（confdeltype = 'c'）。
  --     以 pg_constraint 查而非 constraint 名稱——名稱由 PostgreSQL 自動產生。
  SELECT con.confdeltype::text INTO v
    FROM pg_constraint con
    JOIN pg_class t ON t.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = t.relnamespace
    JOIN pg_class rt ON rt.oid = con.confrelid
   WHERE ns.nspname = 'public' AND t.relname = 'project_members'
     AND con.contype = 'f' AND rt.relname = 'projects';
  IF v IS NULL THEN
    RAISE EXCEPTION
      'P3 FAILED (BR2.3／[ND1]=A): project_members 缺少指向 projects 的外鍵';
  END IF;
  IF v <> 'c' THEN
    RAISE EXCEPTION
      'P3 FAILED ([ND1]=A): project_members.project_id 的 ON DELETE 應為 CASCADE'
      '（confdeltype = c），實際 confdeltype = %。RESTRICT／NO ACTION 會讓'
      'hierarchy_service.delete_project() 的 db.delete(project) 在 commit 丟出'
      '**未被捕捉的 IntegrityError**——該函式只守 is_default 與剩餘系統數，'
      '沒有任何一道關於成員', v;
  END IF;

  -- -------------------------------------------------------------------
  -- B 群：reselection_events（BR1.2／[ND1]=A／FR12.4b）
  -- -------------------------------------------------------------------

  -- P5：欄位集合恰為 8 欄，且 FR12.4b 的五個稽核欄位都在其中。
  --     兩半都要：只驗總數會讓「換掉一個欄位」通過；只驗具名會讓「多塞一欄」通過。
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'reselection_events';
  IF n <> 9 THEN
    RAISE EXCEPTION
      'P5 FAILED (FR12.4b): reselection_events 應有 9 欄，實際 %。'
      '**本單元的 entities.md 只宣告 2 欄**（projectId／acknowledgedAt）——'
      'DDL 依 components.md:819 的 Entity Ownership 表建全欄（OPEN-ND18-1）。'
      '第 9 欄是 U19/[FD3]=A 回補的 cause（原為 8 欄）', n;
  END IF;

  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'reselection_events'
     AND column_name IN ('promoted_user_id', 'previous_owner_user_id',
                         'previous_role', 'new_role', 'occurred_at');
  IF n <> 5 THEN
    RAISE EXCEPTION
      'P5 FAILED (FR12.4b／AC12.2.2): 五個稽核欄位（誰／對誰／舊角色／新角色／何時）'
      '應全部存在，實際只有 % 個。AC12.2.2 的 Then 逐字要求「顯示誰在何時把角色由'
      '什麼改為什麼」——少任何一個，成員詳情頁的變更紀錄就沒有內容可顯示', n;
  END IF;

  -- P6（= security-design 的 `P-FK0`）：本表對 projects **沒有任何外鍵**。
  --     兩種查法各跑一次：information_schema（設計指定的那一種）＋ pg_catalog。
  --     前者的視圖會依權限過濾，單獨使用時「回 0」可能是看不到而不是不存在。
  SELECT count(*) INTO n
    FROM information_schema.table_constraints tc
    JOIN information_schema.constraint_column_usage ccu
      ON ccu.constraint_name = tc.constraint_name
     AND ccu.constraint_schema = tc.constraint_schema
   WHERE tc.table_schema = 'public'
     AND tc.table_name = 'reselection_events'
     AND tc.constraint_type = 'FOREIGN KEY'
     AND ccu.table_name = 'projects';
  IF n <> 0 THEN
    RAISE EXCEPTION
      'P6 FAILED ([ND1]=A): reselection_events 不得對 projects 設外鍵（'
      'information_schema 查到 % 條）。改選稽核必須在專案被刪後**獨立存活**——'
      'FR12.4b 存在的理由正是事後查得出某人的 project_admin 是怎麼來的，'
      'CASCADE 會刪掉答案、RESTRICT 會擋住專案刪除', n;
  END IF;

  SELECT count(*) INTO n
    FROM pg_constraint con
    JOIN pg_class t ON t.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = t.relnamespace
    JOIN pg_class rt ON rt.oid = con.confrelid
   WHERE ns.nspname = 'public' AND t.relname = 'reselection_events'
     AND con.contype = 'f' AND rt.relname = 'projects';
  IF n <> 0 THEN
    RAISE EXCEPTION
      'P6 FAILED ([ND1]=A): reselection_events 不得對 projects 設外鍵'
      '（pg_constraint 查到 % 條）', n;
  END IF;

  -- P8：ix_reselection_events_unack 存在**且為 partial**。
  --     只驗存在會漏掉 WHERE 子句被拿掉的情形，而那會讓索引大小由「目前未確認數」
  --     變成「歷來總數」——失敗模式是效能而非正確性，不會有人發現。
  SELECT indexdef INTO v FROM pg_indexes
   WHERE schemaname = 'public' AND tablename = 'reselection_events'
     AND indexname = 'ix_reselection_events_unack';
  IF v IS NULL THEN
    RAISE EXCEPTION
      'P8 FAILED (security-design §四之二): ix_reselection_events_unack 不存在。'
      'FR12.4c／[M1]=B 要求橫幅每次進入產品都看得到，故每一次落地頁載入都查一次'
      '「這個人有沒有未確認的改選事件」';
  END IF;
  IF position('WHERE' in upper(v)) = 0
     OR position('acknowledged_at' in v) = 0 THEN
    RAISE EXCEPTION
      'P8 FAILED: ix_reselection_events_unack 必須是 partial index'
      '（WHERE acknowledged_at IS NULL），實際 indexdef = %。拿掉 WHERE 之後索引'
      '仍然存在、查詢仍然正確，只是大小變成歷來總數——所以沒有這條斷言就永遠不會'
      '被發現', v;
  END IF;

  -- P13（U19/[FD3]=A）：cause 存在且為 NOT NULL。
  --     沒有它，人工角色變更無處可寫——AC12.2.2 的變更紀錄只會有自動改選那一半，
  --     而 changeRole 的稽核寫入會以 NotNullViolation 失敗。
  SELECT is_nullable INTO v FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'reselection_events'
     AND column_name = 'cause';
  IF v IS NULL THEN
    RAISE EXCEPTION
      'P13 FAILED (U19/[FD3]=A): reselection_events 缺少 cause 欄。它是人工角色變更'
      '與自動改選共用同一張表的唯一區分依據（BR5.3），且 U19 的 changeRole 稽核'
      '寫入直接依賴它';
  END IF;
  IF v <> 'NO' THEN
    RAISE EXCEPTION
      'P13 FAILED (U19/[FD3]=A): cause 必須為 NOT NULL，實際 is_nullable = %。'
      '可為 null 會讓「這一列是哪一種變更」變成第三種狀態，而 BR5.5 的橫幅查詢'
      '以 cause = ''auto_reselection'' 過濾——null 的列會靜默地不出現在橫幅裡，'
      '也不出現在任何人預期的地方', v;
  END IF;

  -- P14（U19/[FD3]=A／BR5.3）：cause 為**封閉列舉**，且恰為那兩個值。
  --     與 previous_role／new_role 刻意無 CHECK 的分野：cause 的兩個值是定案
  --     （[FD3]=A），不是未決事項。
  SELECT pg_get_constraintdef(con.oid) INTO v
    FROM pg_constraint con
    JOIN pg_class t ON t.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = t.relnamespace
   WHERE ns.nspname = 'public' AND t.relname = 'reselection_events'
     AND con.conname = 'ck_reselection_events_cause';
  IF v IS NULL THEN
    RAISE EXCEPTION
      'P14 FAILED (U19/[FD3]=A／BR5.3): 缺少約束 ck_reselection_events_cause。'
      '沒有它，一個拼錯的 cause 值（例如 ''auto_reselect''）會寫入成功，而後果是'
      '**橫幅永遠不出現**——BR5.5 的查詢以字面值比對，拼錯即永不命中，且沒有任何'
      '錯誤';
  END IF;
  IF position('auto_reselection' in v) = 0
     OR position('manual_role_change' in v) = 0 THEN
    RAISE EXCEPTION
      'P14 FAILED (U19/[FD3]=A): ck_reselection_events_cause 必須同時允許'
      'auto_reselection 與 manual_role_change 兩個值，實際 constraintdef = %。'
      '少了前者則自動改選寫不進去，少了後者則人工角色變更寫不進去（BR5.3）', v;
  END IF;

  -- -------------------------------------------------------------------
  -- C 群：system_requirement_fields（BR1.3／BR1.4／BR2.2）
  -- -------------------------------------------------------------------

  -- P9：value 為 nullable；updated_by 為 NOT NULL。
  SELECT is_nullable INTO v FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'system_requirement_fields'
     AND column_name = 'value';
  IF v IS DISTINCT FROM 'YES' THEN
    RAISE EXCEPTION
      'P9 FAILED (BR1.3／ADR-015): value 必須可為 null。收緊為 NOT NULL 會讓'
      '「從未填過」（無列）與「清空」（有列而 value 為 null）在資料層**不可區分**，'
      '而畫面 M12 要求區分它們——代價是清空動作失去稽核軌跡。實際 is_nullable = %',
      coalesce(v, '<欄位不存在>');
  END IF;

  SELECT is_nullable INTO v FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'system_requirement_fields'
     AND column_name = 'updated_by';
  IF v IS DISTINCT FROM 'NO' THEN
    RAISE EXCEPTION
      'P9 FAILED (K-17 clear_field): updated_by 必須為 NOT NULL。該契約逐字為'
      '「保留列、value 設 null、記 clearedAt **與 updatedBy**」——沒有這一欄，'
      '「誰清的」那一半稽核根本不存在。實際 is_nullable = %',
      coalesce(v, '<欄位不存在>');
  END IF;

  -- P12：表的 COMMENT 非空，且含 [UG:G9]=A 的三個關鍵詞。
  --      BR2.2 的 violation_behaviour 逐字：不寫下來的話，「資料庫裡有、畫面上
  --      看不到」的列會被下一個人**當成髒資料清掉**——被清掉的是使用者曾經填過
  --      的值。故 COMMENT 是防呆機制而非文件義務，因此它需要一條斷言。
  SELECT obj_description('public.system_requirement_fields'::regclass, 'pg_class')
    INTO v;
  IF v IS NULL OR length(trim(v)) = 0 THEN
    RAISE EXCEPTION
      'P12 FAILED (BR2.2): system_requirement_fields 的表 COMMENT 不得為空';
  END IF;
  IF position('ug:g9' in lower(v)) = 0 THEN
    RAISE EXCEPTION 'P12 FAILED (BR2.2): COMMENT 須標明來源決定 [UG:G9]';
  END IF;
  IF position('retained' in lower(v)) = 0 THEN
    RAISE EXCEPTION
      'P12 FAILED (BR2.2 第 1 件事): COMMENT 須寫明欄位定義被移除後其值列**保留**'
      '（RETAINED）';
  END IF;
  IF position('not render' in lower(v)) = 0 THEN
    RAISE EXCEPTION
      'P12 FAILED (BR2.2 第 2 件事): COMMENT 須寫明畫面**不渲染**該組'
      '（does NOT render）';
  END IF;
  IF position('currently declared' in lower(v)) = 0 THEN
    RAISE EXCEPTION
      'P12 FAILED (BR2.2 第 3 件事): COMMENT 須寫明未填計數只算**當前已宣告**的'
      '欄位（CURRENTLY DECLARED）';
  END IF;

  -- P15（U20/[FD1]=A／BR47.1／BR47.3）：updated_on_behalf_of 是 agent 組識別字
  --      ——character varying(64)。仍為 integer 表示 J) 區塊的條件式收斂沒有發生，
  --      而那時每一筆帶代寫標示的寫入都會以型別錯誤失敗（500）。
  SELECT data_type || coalesce('(' || character_maximum_length || ')', '') INTO v
    FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'system_requirement_fields'
     AND column_name = 'updated_on_behalf_of';
  IF v IS DISTINCT FROM 'character varying(64)' THEN
    RAISE EXCEPTION
      'P15 FAILED (U20/BR47.1): updated_on_behalf_of 應為 character varying(64)'
      '（agent 組識別字），實際 %。仍為 integer 表示 schema_rbac.sql J) 區塊的'
      '收斂沒有執行——請跑 backend/scripts/run_meta_schema_migration.py',
      coalesce(v, '<欄位不存在>');
  END IF;

  -- P16（U20/BR47.3）：該欄上**沒有**任何外鍵，而同表 updated_by 指向 users 的
  --      外鍵**仍在**。兩半都要：只驗前者會讓「收斂時誤刪 updated_by 的外鍵」通過；
  --      以（表、被參照表）為鍵的查法（run_meta_schema_migration.py 的 FORBIDDEN_FKS）
  --      分辨不出這兩條，所以這裡以欄位（conkey）比對。
  SELECT count(*) INTO n
    FROM pg_constraint con
    JOIN pg_class t ON t.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = t.relnamespace
    JOIN pg_attribute a
      ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
   WHERE ns.nspname = 'public' AND t.relname = 'system_requirement_fields'
     AND con.contype = 'f' AND a.attname = 'updated_on_behalf_of';
  IF n <> 0 THEN
    RAISE EXCEPTION
      'P16 FAILED (U20/[FD1]=A): updated_on_behalf_of 不得有外鍵，實際 % 條。'
      '它存的是 agent 組識別字（例如 cost），指向 users 的外鍵會擋下每一筆代寫', n;
  END IF;

  SELECT count(*) INTO n
    FROM pg_constraint con
    JOIN pg_class t ON t.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = t.relnamespace
    JOIN pg_attribute a
      ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
    JOIN pg_class rt ON rt.oid = con.confrelid
   WHERE ns.nspname = 'public' AND t.relname = 'system_requirement_fields'
     AND con.contype = 'f' AND a.attname = 'updated_by' AND rt.relname = 'users';
  IF n <> 1 THEN
    RAISE EXCEPTION
      'P16 FAILED (ADR-015): updated_by 指向 users 的外鍵應恰有 1 條，實際 %。'
      '收斂只應移除 updated_on_behalf_of 的那一條', n;
  END IF;

  RAISE NOTICE '結構類斷言（P1／P2／P3／P5／P6／P8／P9／P12／P13／P14／P15／P16）全部通過';
END $$;

-- =====================================================================
-- 行為類斷言：需要實際寫入／刪除，故包在一個交易內，最後一律 ROLLBACK
-- =====================================================================

BEGIN;

-- 建一個臨時使用者以滿足三張表的 public.users 外鍵。
INSERT INTO public.users (username, password_hash, role, is_active)
VALUES ('__verify_meta_schema__', 'unused', 'Project_Architect', true);

DO $$
DECLARE
  uid int;
  pid_cascade int;
  pid_survive int;
  pid_fields int;
  sid int;
  ev_id int;
  n int;
  failed boolean;
BEGIN
  SELECT id INTO uid FROM public.users
   WHERE username = '__verify_meta_schema__';

  -- ===================================================================
  -- P4（行為面，[ND1]=A／security-design §一之三）：刪除一個 projects 列後，
  --     其 project_members 列**一併消失**，且刪除本身不因外鍵而失敗。
  --
  -- **前置條件**：被刪的 projects 列必須是**非預設**專案且**底下無系統**，否則
  -- 紅燈的原因會是 U4 既有的兩道守門（hierarchy_service.py:153／:156）或
  -- systems.project_id 的 ON DELETE RESTRICT，而不是本表的外鍵。
  -- ===================================================================
  INSERT INTO projects (name, owner_user_id, is_default)
  VALUES ('__verify_meta_cascade__', uid, false)
  RETURNING id INTO pid_cascade;

  INSERT INTO project_members (project_id, user_id, role, invited_by)
  VALUES (pid_cascade, uid, 'project_admin', NULL);

  -- 前置條件自我確認：這個專案非預設、底下無系統。
  SELECT count(*) INTO n FROM systems WHERE project_id = pid_cascade;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'P4 SETUP FAILED: 構造的專案底下有 % 個系統，刪除會被 systems 的'
      'ON DELETE RESTRICT 擋住，紅燈原因就不是本表的外鍵了', n;
  END IF;

  failed := false;
  BEGIN
    DELETE FROM projects WHERE id = pid_cascade;
  EXCEPTION WHEN foreign_key_violation THEN failed := true;
  END;
  IF failed THEN
    RAISE EXCEPTION
      'P4 FAILED ([ND1]=A): 刪除專案被 project_members 的外鍵擋下。'
      'ON DELETE 若為 RESTRICT／NO ACTION，hierarchy_service.delete_project() 的'
      'db.delete(project) 會在 commit 丟出未被捕捉的 IntegrityError——'
      '使用者看到 500 而不是 BR4.4 那種帶訊息的 HierarchyConflictError。'
      '這是一條由新 DDL 引入既有程式的行為迴歸';
  END IF;

  SELECT count(*) INTO n FROM projects WHERE id = pid_cascade;
  IF n <> 0 THEN
    RAISE EXCEPTION 'P4 FAILED: 專案列未被刪除（實際剩 % 列）', n;
  END IF;

  SELECT count(*) INTO n FROM project_members WHERE project_id = pid_cascade;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'P4 FAILED ([ND1]=A): 專案被刪除後其成員列必須一併消失，實際剩 % 列。'
      '沒有級聯會留下指向不存在專案的成員列，而 K-16／K-17 的 facade 檢查的是'
      '授權、不是參照完整性', n;
  END IF;

  -- ===================================================================
  -- P7（= security-design 的 `P-SURV`）：插入一列 reselection_events →
  --     刪除其 projects 列 → 該稽核列**仍然存在**。
  --     P6 驗手段（沒有外鍵）、P7 驗目的（稽核存活），**缺一不可**：
  --     只有 P6 紅而 P7 綠表示 P7 寫錯了。
  --     前置條件同 P4（非預設、底下無系統），理由同上。
  -- ===================================================================
  INSERT INTO projects (name, owner_user_id, is_default)
  VALUES ('__verify_meta_survive__', uid, false)
  RETURNING id INTO pid_survive;

  -- `cause` 自 U19/[FD3]=A 起為 NOT NULL，故這個 INSERT 必須帶它
  -- （這一行是回補 cause 時實跑 verify_meta_schema.sql 才抓到的：原本的
  --  INSERT 省略 cause，而 NOT NULL 讓它變成 NotNullViolation——
  --  CI 的 memory-schema job 會因此紅燈，而紅燈原因會指向 P7 而非 cause）。
  INSERT INTO reselection_events
    (project_id, cause, promoted_user_id, previous_owner_user_id,
     previous_role, new_role)
  VALUES (pid_survive, 'auto_reselection', uid, uid, 'member', 'project_admin')
  RETURNING id INTO ev_id;

  SELECT count(*) INTO n FROM systems WHERE project_id = pid_survive;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'P7 SETUP FAILED: 構造的專案底下有 % 個系統，刪除會被 systems 的'
      'ON DELETE RESTRICT 擋住', n;
  END IF;

  failed := false;
  BEGIN
    DELETE FROM projects WHERE id = pid_survive;
  EXCEPTION WHEN foreign_key_violation THEN failed := true;
  END;
  IF failed THEN
    RAISE EXCEPTION
      'P7 FAILED ([ND1]=A): 刪除專案被擋下——若 reselection_events 對 projects'
      '設了 RESTRICT 外鍵，稽核列會變成「刪不掉專案」而不是「稽核存活」';
  END IF;

  SELECT count(*) INTO n FROM reselection_events WHERE id = ev_id;
  IF n <> 1 THEN
    RAISE EXCEPTION
      'P7 FAILED ([ND1]=A／FR12.4b): 專案被刪除後其改選稽核列必須仍然存在，'
      '實際剩 % 列。沒有外鍵只是手段，稽核存活才是目的——FR12.4b 存在的理由'
      '正是事後查得出某人的 project_admin 是怎麼來的', n;
  END IF;

  -- ===================================================================
  -- C 群的行為面：需要一個 system，而 system 需要一個 project。
  -- ===================================================================
  INSERT INTO projects (name, owner_user_id, is_default)
  VALUES ('__verify_meta_fields__', uid, false)
  RETURNING id INTO pid_fields;

  INSERT INTO systems (name, project_id, is_default)
  VALUES ('__verify_meta_system__', pid_fields, false)
  RETURNING id INTO sid;

  -- ===================================================================
  -- P10（BR1.4）：三態可區分。
  --   「已填」（value 有值、cleared_at NULL）成功；
  --   「清空」（value NULL、cleared_at 有值）成功；
  --   「value 有值而 cleared_at 也有值」被 CHECK 拒絕。
  --   三個案例用**不同的 field_key**，否則第三個會踩到唯一約束而不是 CHECK，
  --   紅燈原因就換成另一條規則了。
  -- ===================================================================
  INSERT INTO system_requirement_fields
    (system_id, agent_group, field_key, value, cleared_at, updated_by)
  VALUES (sid, 'sla', 'filled_key', 'p99 < 200ms', NULL, uid);

  INSERT INTO system_requirement_fields
    (system_id, agent_group, field_key, value, cleared_at, updated_by)
  VALUES (sid, 'sla', 'cleared_key', NULL, now(), uid);

  failed := false;
  BEGIN
    INSERT INTO system_requirement_fields
      (system_id, agent_group, field_key, value, cleared_at, updated_by)
    VALUES (sid, 'sla', 'both_key', 'still has a value', now(), uid);
  EXCEPTION WHEN check_violation THEN failed := true;
  END;
  IF NOT failed THEN
    RAISE EXCEPTION
      'P10 FAILED (BR1.4): value 有值而 cleared_at 也有值的列必須被 CHECK 拒絕。'
      '允許它等於讓同一列同時是「已填」與「清空」，兩種讀法都說得通，'
      '於是三態退化成「看寫入端當時想的是哪一種」——而 ADR-015 的清空語意'
      '（保留列、value 設 null、記 clearedAt）就不再是資料層的事實';
  END IF;

  -- ===================================================================
  -- P11（entity_constraints，本單元刻意由兩欄加寬為三欄）：
  --   UNIQUE (system_id, agent_group, field_key)。
  --   **兩半都要**：① 重複三元組被拒；② 同一個 field_key 在**不同** agent 組
  --   之下**可以**插入。只有 ① 的話，把唯一鍵改回兩欄（system_id, field_key）
  --   仍然會拒絕重複三元組——① 保持綠燈，只有 ② 會紅。
  -- ===================================================================
  failed := false;
  BEGIN
    INSERT INTO system_requirement_fields
      (system_id, agent_group, field_key, value, updated_by)
    VALUES (sid, 'sla', 'filled_key', 'duplicate triple', uid);
  EXCEPTION WHEN unique_violation THEN failed := true;
  END;
  IF NOT failed THEN
    RAISE EXCEPTION
      'P11 FAILED: (system_id, agent_group, field_key) 的重複三元組必須被拒絕';
  END IF;

  failed := false;
  BEGIN
    INSERT INTO system_requirement_fields
      (system_id, agent_group, field_key, value, updated_by)
    VALUES (sid, 'capacity', 'filled_key', 'same key, other group', uid);
  EXCEPTION WHEN unique_violation THEN failed := true;
  END;
  IF failed THEN
    RAISE EXCEPTION
      'P11 FAILED: 同一個 field_key 在**不同** agent 組之下被拒絕，表示唯一鍵'
      '只有兩欄（system_id, field_key）。K-17 的 read_fields 回傳「按 agentGroup'
      '分組、每組含 fieldKey」，故同一個 fieldKey 字串在不同組下是**不同的欄位**'
      '——兩欄鍵會讓兩組共用的欄位名互相排擠';
  END IF;

  RAISE NOTICE '行為類斷言（P4／P7／P10／P11）全部通過';
END $$;

ROLLBACK;
