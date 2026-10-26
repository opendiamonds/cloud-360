-- verify_memory_schema.sql — `U5 memory-data` 的 12 條斷言（`S1`–`S12`）
--                           ＋ `U9 memory-purge` 的 seed 斷言 `S13`
--
-- 由 CI job `memory-schema`（交付物 `N-2`）對**真實 PostgreSQL** 執行。
--
-- **為什麼不是 Python 測試**：契約 `K-05` 的 `verification.why_not_existing_tests`
-- 逐字——既有測試在 `backend/tests/helpers.py` 換掉驅動、改走 in-memory SQLite，
-- 而 **SQLite 沒有 schema 概念**，故現有測試基礎設施對本契約沒有任何驗證路徑。
--
-- 每條斷言不成立即 RAISE EXCEPTION，使 psql 以非零碼結束、job 紅燈。
-- 以 `psql -v ON_ERROR_STOP=1 -f` 執行。

\set ON_ERROR_STOP on

DO $$
DECLARE
  n int;
  v text;
BEGIN
  -- =====================================================================
  -- A 群：schema 隔離與可重跑
  -- =====================================================================

  -- S1：memory schema 存在，且兩張表都在它裡面（不是 public）。
  SELECT count(*) INTO n FROM information_schema.schemata
   WHERE schema_name = 'memory';
  IF n <> 1 THEN
    RAISE EXCEPTION 'S1 FAILED (BR1.1): schema "memory" 不存在';
  END IF;

  SELECT count(*) INTO n FROM information_schema.tables
   WHERE table_schema = 'memory'
     AND table_name IN ('memory_records', 'memory_audit_events');
  IF n <> 2 THEN
    RAISE EXCEPTION
      'S1 FAILED (BR1.1): memory schema 內應有 2 張表，實際 %', n;
  END IF;

  SELECT count(*) INTO n FROM information_schema.tables
   WHERE table_schema = 'public'
     AND table_name IN ('memory_records', 'memory_audit_events');
  IF n <> 0 THEN
    RAISE EXCEPTION
      'S1 FAILED (BR1.1): 兩張表不得出現在 public（實際 % 張）——'
      '落在 public 會讓 BR1.2 的 grant 邊界完全失效而功能上看不出來', n;
  END IF;

  -- S3：vector 擴充可用，且 embedding 為 1024 維。
  SELECT count(*) INTO n FROM pg_extension WHERE extname = 'vector';
  IF n <> 1 THEN
    RAISE EXCEPTION 'S3 FAILED (BR3.2): vector 擴充不存在';
  END IF;

  SELECT format_type(a.atttypid, a.atttypmod) INTO v
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace ns ON ns.oid = c.relnamespace
   WHERE ns.nspname = 'memory' AND c.relname = 'memory_records'
     AND a.attname = 'embedding';
  IF v IS DISTINCT FROM 'vector(1024)' THEN
    RAISE EXCEPTION
      'S3 FAILED (BR3.2): embedding 型別應為 vector(1024)，實際 %', v;
  END IF;

  -- =====================================================================
  -- B 群：欄位與約束
  -- =====================================================================

  -- S4：memory_records 的欄位集合恰為 9 欄（多一欄或少一欄皆紅）。
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'memory' AND table_name = 'memory_records';
  IF n <> 9 THEN
    RAISE EXCEPTION
      'S4 FAILED: memory_records 應有 9 欄，實際 % ——'
      '欄位集合變動須先更新 entities.md', n;
  END IF;

  -- S5：embedding_model 為 NOT NULL；embedding 為 nullable。
  SELECT is_nullable INTO v FROM information_schema.columns
   WHERE table_schema = 'memory' AND table_name = 'memory_records'
     AND column_name = 'embedding_model';
  IF v <> 'NO' THEN
    RAISE EXCEPTION 'S5 FAILED (BR3.1): embedding_model 必須為 NOT NULL';
  END IF;

  SELECT is_nullable INTO v FROM information_schema.columns
   WHERE table_schema = 'memory' AND table_name = 'memory_records'
     AND column_name = 'embedding';
  IF v <> 'YES' THEN
    RAISE EXCEPTION
      'S5 FAILED (BR3.3): embedding 必須可為空——fulltext 模式的列沒有 embedding，'
      '收緊為 NOT NULL 會破壞該降級路徑';
  END IF;

  -- =====================================================================
  -- C 群：稽核表與 DG-1 的處置
  -- =====================================================================

  -- S8：memory_audit_events 對 memory_records **沒有任何外鍵**。
  SELECT count(*) INTO n
    FROM information_schema.table_constraints tc
    JOIN information_schema.constraint_column_usage ccu
      ON ccu.constraint_name = tc.constraint_name
     AND ccu.constraint_schema = tc.constraint_schema
   WHERE tc.table_schema = 'memory'
     AND tc.table_name = 'memory_audit_events'
     AND tc.constraint_type = 'FOREIGN KEY'
     AND ccu.table_name = 'memory_records';
  IF n <> 0 THEN
    RAISE EXCEPTION
      'S8 FAILED (BR2.1／DG-1): 稽核表不得對 memory_records 設外鍵。'
      '設了就必須在兩個壞結果中選一個，而兩者都違反已核可需求——'
      'CASCADE 使 FR4.7 在 90 天後失效，RESTRICT 使 FR4.5 無法執行';
  END IF;

  -- S9：稽核表不含 content、不含 embedding。
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'memory' AND table_name = 'memory_audit_events'
     AND column_name IN ('content', 'embedding');
  IF n <> 0 THEN
    RAISE EXCEPTION
      'S9 FAILED (BR2.2): 稽核表不得含記憶內容。這是 BR2.1 能成立的前提——'
      '稽核比記憶活得久，若它含內容則「保留稽核」等於「保留被刪除的使用者資料」，'
      '使用者以為刪了而它還在，FR4.5 形同虛設';
  END IF;

  -- S12：occurred_at 有索引（否則 NFR7.2 的清除查詢是全表掃描）。
  SELECT count(*) INTO n FROM pg_indexes
   WHERE schemaname = 'memory' AND tablename = 'memory_audit_events'
     AND indexdef LIKE '%occurred_at%';
  IF n < 1 THEN
    RAISE EXCEPTION
      'S12 FAILED (NFR7.2): memory_audit_events 需要 occurred_at 索引。'
      '失敗模式是**效能而非正確性**，故沒有這條斷言就永遠不會被發現；'
      '且本輪該表無讀取端，不會有人順手建它';
  END IF;

  RAISE NOTICE '結構類斷言（S1／S3／S4／S5／S8／S9／S12）全部通過';
END $$;

-- =====================================================================
-- Seed 類斷言：`U9 memory-purge` 的保留系統 actor（`S13`）
--
-- 為什麼它驗在這裡：`memory_audit_events.actor_user_id` 是
-- `NOT NULL REFERENCES public.users (id)`，而清除的稽核 INSERT 用的就是這一列。
-- 它**不存在**的後果不是「少一列資料」，是從那一刻起每一次清除的整個交易中止
-- （稽核與刪除同一交易），於是 90 天保存期停在原地。
--
-- **既有的 Python 測試路徑看不到它**：`backend/tests/helpers.py` 的
-- `make_session()` 以 `Base.metadata.create_all()` 建表，**不執行 `schema_rbac.sql`
-- 的 seed**。故這一列的存在只能在真實 PostgreSQL 上驗（`OPEN-ID9-3`）。
--
-- 唯讀，故不需要獨立交易。
-- =====================================================================

DO $$
DECLARE
  n int;
  v_role text;
  v_active boolean;
  v_hash text;
BEGIN
  SELECT count(*) INTO n FROM public.users
   WHERE username = 'SYSTEM.retention-purge';
  IF n <> 1 THEN
    RAISE EXCEPTION
      'S13 FAILED (U9/NFR7.11): 保留系統 actor 的列應恰有 1 列，實際 %。'
      '沒有它，清除的稽核 INSERT 會因 actor_user_id 的外鍵違反而讓整個清除'
      '交易中止——90 天保存期不會前進一列。seed 來源為 schema_rbac.sql 的 K) '
      '區塊；既有環境見 backend/scripts/seed_retention_system_actor.py', n;
  END IF;

  SELECT role, is_active, password_hash
    INTO v_role, v_active, v_hash
    FROM public.users WHERE username = 'SYSTEM.retention-purge';

  -- 鎖 4：is_active = FALSE（auth.py 與登入路徑的同一條檢查據此拒絕）。
  IF v_active IS DISTINCT FROM false THEN
    RAISE EXCEPTION
      'S13 FAILED (U9/鎖 4): 系統 actor 的 is_active 應為 false，實際 %。'
      '為 true 時這一列是一個可被嘗試登入的帳號', v_active;
  END IF;

  -- 鎖 3：role 不是被授權的角色。以**資料庫內的實際權限矩陣**判定：
  -- role_permissions 內出現過的 role 就是矩陣實際授權的那些，而 rbac.py 的
  -- CANONICAL_ROLES 與它一一對應（程式層的字面比對由
  -- backend/tests/test_retention_purge_contract.py 承載）。
  SELECT count(*) INTO n FROM role_permissions WHERE role = v_role;
  IF n <> 0 THEN
    RAISE EXCEPTION
      'S13 FAILED (U9/鎖 3): 系統 actor 的 role "%" 在 role_permissions 內有 % 列，'
      '故它是一個被授權的角色', v_role, n;
  END IF;

  -- 鎖 2：password_hash 是**格式合法**的 bcrypt hash。
  -- 非 bcrypt 格式才是危險的那一種：bcrypt.checkpw 對它拋 ValueError
  -- （實測 `ValueError: Invalid salt`）而不是回 False，而 verify_password()
  -- 沒有 try/except，於是 401 變成**未經驗證即可遠端觸發的 500**。
  IF v_hash !~ '^\$2[aby]\$' THEN
    RAISE EXCEPTION
      'S13 FAILED (U9/鎖 2): 系統 actor 的 password_hash 不符合 bcrypt 格式'
      '（應以 $2a$／$2b$／$2y$ 開頭）。非 bcrypt 格式的值會讓 bcrypt.checkpw '
      '拋 ValueError 而非回 False——詳見 nfr-design/security-design.md §1.4';
  END IF;

  RAISE NOTICE 'Seed 類斷言（S13：保留系統 actor ＋ 三道可在資料庫層查證的鎖）通過';
END $$;

-- =====================================================================
-- 行為類斷言：需要實際寫入／刪除，故以獨立交易逐條驗，最後一律 ROLLBACK
-- =====================================================================

BEGIN;

-- 建一個臨時使用者以滿足兩表的 public.users 外鍵。
INSERT INTO public.users (username, password_hash, role, is_active)
VALUES ('__verify_memory_schema__', 'unused', 'Project_Architect', true);

DO $$
DECLARE
  uid int;
  mid int;
  n int;
  failed boolean;
BEGIN
  SELECT id INTO uid FROM public.users
   WHERE username = '__verify_memory_schema__';

  -- S6：kind 的 CHECK 只允許三個值。
  failed := false;
  BEGIN
    INSERT INTO memory.memory_records
      (kind, owner_user_id, visibility_scope, content, embedding_model)
    VALUES ('telepathic', uid, 'private', 'x', 'bge-m3');
  EXCEPTION WHEN check_violation THEN failed := true;
  END;
  IF NOT failed THEN
    RAISE EXCEPTION 'S6 FAILED: kind 的第四個值應被 CHECK 拒絕';
  END IF;

  -- S7：episodic 必須有 expires_at；semantic 可以沒有。
  failed := false;
  BEGIN
    INSERT INTO memory.memory_records
      (kind, owner_user_id, visibility_scope, content, embedding_model, expires_at)
    VALUES ('episodic', uid, 'private', 'x', 'bge-m3', NULL);
  EXCEPTION WHEN check_violation THEN failed := true;
  END;
  IF NOT failed THEN
    RAISE EXCEPTION
      'S7 FAILED (BR4.1): episodic ＋ expires_at NULL 應被拒絕。'
      '清除作業依 expires_at 選列，故 NULL 的 episodic 列永遠不會被選中'
      '——漏填的後果是永久保留且沒有任何跡象';
  END IF;

  INSERT INTO memory.memory_records
    (kind, owner_user_id, visibility_scope, content, embedding_model, expires_at)
  VALUES ('semantic', uid, 'private', 'x', 'bge-m3', NULL);
  -- semantic ＋ NULL 必須成功（反方向：不得把 90 天套到長期記憶）

  -- S10：action 的 CHECK 只允許三個值。
  INSERT INTO memory.memory_records
    (kind, owner_user_id, visibility_scope, content, embedding_model, expires_at)
  VALUES ('episodic', uid, 'private', 'to be deleted', 'bge-m3', now())
  RETURNING id INTO mid;

  failed := false;
  BEGIN
    INSERT INTO memory.memory_audit_events (memory_id, actor_user_id, action)
    VALUES (mid, uid, 'quietly_vanished');
  EXCEPTION WHEN check_violation THEN failed := true;
  END;
  IF NOT failed THEN
    RAISE EXCEPTION 'S10 FAILED (BR2.3): action 的未定義值應被 CHECK 拒絕';
  END IF;

  -- S11：**行為面**斷言 DG-1 的處置——刪掉記憶之後，稽核列仍然存在。
  --      S8 只驗 schema 形狀（沒有外鍵），S11 驗目的（稽核存活）。
  INSERT INTO memory.memory_audit_events (memory_id, actor_user_id, action)
  VALUES (mid, uid, 'purged_by_retention');

  DELETE FROM memory.memory_records WHERE id = mid;

  SELECT count(*) INTO n FROM memory.memory_audit_events
   WHERE memory_id = mid;
  IF n <> 1 THEN
    RAISE EXCEPTION
      'S11 FAILED (BR2.1／DG-1／FR4.7): 記憶被刪除後其稽核列必須仍然存在，'
      '實際剩 % 列。沒有外鍵只是手段，稽核存活才是目的', n;
  END IF;

  RAISE NOTICE '行為類斷言（S6／S7／S10／S11）全部通過';
END $$;

ROLLBACK;


-- ###########################################################################
-- `U8 memory-service` 的兩組斷言：`S14`（索引 ＋ opclass）與 `S15`（檢索查詢）
--
-- 兩者都在**既有** `memory-schema` job 內跑，**不新增 CI job**：它們需要的前置
-- 條件（真實 PostgreSQL ＋ 已套用的 `schema_rbac.sql`）與本檔上游的斷言完全
-- 相同，另開一個等於把同一座 service container 建第二次
-- （`infrastructure-design/cicd-pipeline.md §二`／`§三`）。
--
-- **為什麼這兩條只能在真實 PostgreSQL 上跑**：SQLite **無向量型別、無距離
-- 運算子**——這不是「語意不同」，是那條查詢**編不出來**
-- （`cicd-pipeline.md §三之一`，它更正了初稿「本單元沒有語意落差」那句錯話）。
-- ###########################################################################

DO $$
DECLARE
  n int;
  v text;
  vec text;
  plan text := '';
  r record;
BEGIN
  -- =====================================================================
  -- S14：HNSW 索引存在、型態正確、**opclass 與查詢的距離運算子相符**
  -- =====================================================================

  -- S14a：索引存在。
  SELECT count(*) INTO n FROM pg_indexes
   WHERE schemaname = 'memory'
     AND tablename = 'memory_records'
     AND indexname = 'ix_memory_records_embedding_hnsw';
  IF n <> 1 THEN
    RAISE EXCEPTION
      'S14 FAILED (U8/NFR3.22): memory_records 需要 embedding 的 HNSW 索引。'
      '缺它的後果是相似度檢索退化為循序掃描，而**查詢仍然正確**'
      '（仍回精確最近鄰）——故這個失敗模式在功能測試上完全看不見。';
  END IF;

  -- S14b：型態為 hnsw，且 opclass 為 vector_cosine_ops。
  --
  -- **opclass 是這一條的重點。** 不相符時索引被**靜默忽略**：型別、維度、
  -- 索引與查詢全部仍然合法，planner 只是用不到它，而在空表上延遲看起來
  -- 一樣好。`[N2]`=B 的整個投資會落空且沒有任何跡象。
  SELECT am.amname || '/' || opc.opcname INTO v
    FROM pg_index i
    JOIN pg_class ic ON ic.oid = i.indexrelid
    JOIN pg_namespace ns ON ns.oid = ic.relnamespace
    JOIN pg_am am ON am.oid = ic.relam
    JOIN pg_opclass opc ON opc.oid = i.indclass[0]
   WHERE ns.nspname = 'memory'
     AND ic.relname = 'ix_memory_records_embedding_hnsw';
  IF v IS DISTINCT FROM 'hnsw/vector_cosine_ops' THEN
    RAISE EXCEPTION
      'S14 FAILED (U8/NFR3.22): 索引應為 hnsw/vector_cosine_ops，實際 %。'
      'opclass 必須與 memory_service.SEARCH_SQL 的距離運算子 <=> 成對；'
      '不成對時索引被靜默忽略（Python 側的那一半由 '
      'tests/test_memory_contract.py 的 C6 鎖住）。', v;
  END IF;

  -- S14c：**行為面**斷言——planner 在 seqscan 關閉時真的用得到它。
  --
  -- `SET LOCAL enable_seqscan = off` 是刻意的（承 `nfr-requirements` 審查的
  -- `R-02`／`N8-12`）：planner 是 cost-based 的，在小表上幾乎**必定**選
  -- `Seq Scan` 即使索引完全正確——不關掉會產生假性失敗。
  --
  -- **誠實限定**（`cicd-pipeline.md §二之一` 已自承）：本斷言通過**不等於**
  -- 生產環境的 planner 會選用該索引，它只證明「索引可用且 opclass 相符」。
  -- 後者需要數百至數千列 fixture，而本表目前是空的（`I8-3`），
  -- 現在量它只會量到「空表上不選索引」這個正確但無用的結論。
  vec := '[' || array_to_string(array_fill(0.1::real, ARRAY[1024]), ',') || ']';
  SET LOCAL enable_seqscan = off;
  FOR r IN EXECUTE format(
    'EXPLAIN (COSTS OFF) SELECT id FROM memory.memory_records '
    'ORDER BY embedding <=> %L::vector(1024) LIMIT 5', vec)
  LOOP
    plan := plan || r."QUERY PLAN" || E'\n';
  END LOOP;

  IF position('ix_memory_records_embedding_hnsw' in plan) = 0 THEN
    RAISE EXCEPTION
      'S14 FAILED (U8/NFR3.22): enable_seqscan=off 之下，<=> 的查詢計畫仍未'
      '使用 ix_memory_records_embedding_hnsw。最可能的原因是 opclass 與運算子'
      '不成對（例如 opclass 為 vector_l2_ops 而查詢用 <=>）。計畫全文：%',
      E'\n' || plan;
  END IF;

  RAISE NOTICE 'S14（HNSW 索引存在／型態／opclass／planner 可用）通過';
END $$;


-- =====================================================================
-- S15：**檢索查詢的組合正確性**（承 `infrastructure-design` 審查 `R-01`，Critical）
--
-- 這一組存在的理由，逐字取自 `cicd-pipeline.md §三之二`：本單元最核心的
-- 不變量——「檢索必須是**一次 SQL**：兩道過濾與距離排序在同一個查詢內」
-- ——在初稿的 CI 計畫裡**完全沒有覆蓋**（不在已自動化、不在待自動化、
-- 也不在只能手動）。`S14` 不覆蓋它（它只斷言索引可用）。
--
-- fixture 要求：跨**兩個擁有者**與**兩個 embeddingModel**，且總列數
-- **大於** `LIMIT`——否則第 ③ 條無法構造。
--
-- **本組斷言的射程，誠實寫下**：它驗的是「**這樣寫的 SQL** 在真實
-- PostgreSQL 上行為正確」，**不是**「`memory_service.search_records` 真的
-- 這樣查」。psql 無法 import Python。Python 那一側由
-- `tests/test_memory_contract.py` 的 `C6` 斷言（結構 ＋ 與本查詢的一致性）
-- ——兩者缺一，「單一 SQL」這個不變量就只被驗了一半。
-- =====================================================================

BEGIN;

-- 兩個擁有者。`ON CONFLICT DO NOTHING` 使本組可重跑（整段最後 ROLLBACK，
-- 但 BR1.3 的可重跑性要求 fixture 本身不依賴乾淨狀態）。
INSERT INTO public.users (username, password_hash, role, is_active)
VALUES ('__verify_u8_owner_a__', 'unused', 'Project_Architect', true)
ON CONFLICT (username) DO NOTHING;
INSERT INTO public.users (username, password_hash, role, is_active)
VALUES ('__verify_u8_owner_b__', 'unused', 'Project_Architect', true)
ON CONFLICT (username) DO NOTHING;

DO $$
DECLARE
  uid_a int;
  uid_b int;
  vec text;
  far text;
  limit_n int := 3;
  n int;
  expected int;
BEGIN
  SELECT id INTO uid_a FROM public.users WHERE username = '__verify_u8_owner_a__';
  SELECT id INTO uid_b FROM public.users WHERE username = '__verify_u8_owner_b__';
  vec := '[' || array_to_string(array_fill(0.1::real, ARRAY[1024]), ',') || ']';
  -- **刻意與查詢向量反向**（cosine 距離 2，是 `<=>` 的最大值），給「應該被
  -- 過濾掉的列」與「應該留下的列」兩個**不同且有序**的距離。
  far := '[' || array_to_string(array_fill((-0.1)::real, ARRAY[1024]), ',') || ']';

  -- fixture：7 列，橫跨兩個擁有者 × 兩個模型 × 兩種可見範圍。
  --
  --                              距離   對 A 而言
  --   A/bge-m3/owner     × 2      2     命中
  --   A/bge-m3/platform  × 1      2     命中
  --   B/bge-m3/platform  × 1      2     命中
  --   B/bge-m3/owner     × 2      0     **不可見**（① 要擋下的）
  --   A/stub-v1/owner    × 1      0     **模型不同**（② 要擋下的）
  --
  -- 故 A 的過濾後候選數為 **4**，全表 fixture 為 **7**。
  --
  -- ## 距離的分配是 ③ 有鑑別力的前提，不是裝飾
  --
  -- 三個「應該被過濾掉」的列刻意**離查詢向量最近**（距離 0），
  -- 四個「應該留下」的列刻意最遠（距離 2）。於是：
  --
  --   * 正確實作（WHERE 先濾）：候選只有那 4 列，`LIMIT 5` 不生效 → 回 **4**。
  --   * 錯誤實作（先取 `LIMIT 5` 再於應用層過濾）：距離排序讓它先拿到 3 個
  --     壞列 ＋ 2 個好列，過濾後 → 回 **2**。
  --
  -- **若七列共用同一個向量，距離全部相同，排序就是任意的**——錯誤實作有相當
  -- 機率剛好把 4 個好列都取進那 5 筆而讓 ③ 通過（C(3,1)/C(7,5)＝3/21）。
  -- 那會是一個**偶爾變綠**的斷言，比沒有斷言更糟。故這裡把距離差做出來，
  -- 使 ③ 的紅燈是**決定性**的。
  INSERT INTO memory.memory_records
    (kind, owner_user_id, visibility_scope, content, embedding, embedding_model)
  VALUES
    ('semantic', uid_a, 'owner',    '__u8_fixture__ a1', far::vector(1024), 'bge-m3'),
    ('semantic', uid_a, 'owner',    '__u8_fixture__ a2', far::vector(1024), 'bge-m3'),
    ('semantic', uid_a, 'platform', '__u8_fixture__ a3', far::vector(1024), 'bge-m3'),
    ('semantic', uid_b, 'platform', '__u8_fixture__ b3', far::vector(1024), 'bge-m3'),
    ('semantic', uid_b, 'owner',    '__u8_fixture__ b1', vec::vector(1024), 'bge-m3'),
    ('semantic', uid_b, 'owner',    '__u8_fixture__ b2', vec::vector(1024), 'bge-m3'),
    ('semantic', uid_a, 'owner',    '__u8_fixture__ a4', vec::vector(1024), 'stub-v1');

  -- ---------------------------------------------------------------------
  -- S15 ①：結果不含他人擁有且 visibilityScope = owner 的列（BR2.2）
  --
  -- 以 limit_n（3）小於過濾後候選數（4）執行，使 LIMIT 真的在作用。
  -- ---------------------------------------------------------------------
  -- >>> S15_SEARCH_QUERY_BEGIN
  --     本區塊是 memory_service.SEARCH_SQL 的 psql 物化（:param 換成字面值）。
  --     兩份文字由 tests/test_memory_contract.py 的 C6 鎖住承載語意的子句。
  CREATE TEMP TABLE s15_result AS
  SELECT id,
         owner_user_id,
         visibility_scope,
         embedding_model,
         embedding <=> vec::vector(1024) AS distance
    FROM memory.memory_records
   WHERE (owner_user_id = uid_a OR visibility_scope = 'platform')
     AND embedding_model = 'bge-m3'
     AND embedding IS NOT NULL
     AND kind = ANY(ARRAY['semantic', 'procedure', 'episodic']::varchar[])
   ORDER BY embedding <=> vec::vector(1024)
   LIMIT limit_n;
  -- <<< S15_SEARCH_QUERY_END

  SELECT count(*) INTO n FROM s15_result
   WHERE owner_user_id <> uid_a AND visibility_scope = 'owner';
  IF n <> 0 THEN
    RAISE EXCEPTION
      'S15 ① FAILED (BR2.2): 結果含 % 列「他人擁有且範圍為 owner」的記憶。'
      '可見範圍過濾必須在同一個查詢的 WHERE 內——在應用層事後篩會讓不可見的'
      '列先進入進程（洩漏面擴大），且 LIMIT 的筆數會錯。', n;
  END IF;

  -- ---------------------------------------------------------------------
  -- S15 ②：結果不含不同 embeddingModel 的列（BR3.2）
  --
  -- **本單元唯一完全靜默的失敗模式**：少了這道過濾，型別、維度、索引與查詢
  -- 全部仍然合法，但結果是跨向量空間的垃圾**且不報錯**。同維度不等於同向量
  -- 空間——兩個提供者都是 1024 維，這正是陷阱所在。
  -- ---------------------------------------------------------------------
  SELECT count(*) INTO n FROM s15_result WHERE embedding_model <> 'bge-m3';
  IF n <> 0 THEN
    RAISE EXCEPTION
      'S15 ② FAILED (BR3.2): 結果含 % 列不同 embeddingModel 的記憶。', n;
  END IF;

  DROP TABLE s15_result;

  -- ---------------------------------------------------------------------
  -- S15 ③：過濾後候選數 < LIMIT 時，回傳筆數等於**過濾後的數量**
  --
  -- **這是唯一能區分「同查詢」與「先查再事後過濾」的斷言。** 一個先取
  -- LIMIT n 再於應用層過濾的錯誤實作**也會通過 ①②**——它確實把不該有的列
  -- 濾掉了，只是濾在錯的地方；只有 ③ 會紅。
  --
  -- 構造（兩個前提都在下方以斷言固定，不靠註解）：
  --   * 全表 fixture 7 列 **>** LIMIT 5 —— 否則「先查再過濾」與「同查詢」
  --     會回同一個結果，本條就沒有鑑別力。
  --   * 過濾後候選 4 列 **<** LIMIT 5 —— 否則 LIMIT 會截斷正確結果，
  --     「回傳筆數等於過濾後數量」就不再是正確實作的性質。
  --   * 三個壞列的距離（0）**小於**四個好列（2）—— 見上方 fixture 的說明。
  -- 於是：正確實作回 **4**，先查再過濾的實作回 **2**。
  -- ---------------------------------------------------------------------
  limit_n := 5;

  SELECT count(*) INTO expected
    FROM memory.memory_records
   WHERE (owner_user_id = uid_a OR visibility_scope = 'platform')
     AND embedding_model = 'bge-m3'
     AND embedding IS NOT NULL;
  IF expected <> 4 THEN
    RAISE EXCEPTION
      'S15 ③ 的 fixture 前提不成立：過濾後候選數應為 4，實際 %。'
      '（這是 fixture 本身的錯，不是被測行為的錯）', expected;
  END IF;

  SELECT count(*) INTO n
    FROM (
      SELECT id
        FROM memory.memory_records
       WHERE (owner_user_id = uid_a OR visibility_scope = 'platform')
         AND embedding_model = 'bge-m3'
         AND embedding IS NOT NULL
         AND kind = ANY(ARRAY['semantic', 'procedure', 'episodic']::varchar[])
       ORDER BY embedding <=> vec::vector(1024)
       LIMIT limit_n
    ) AS s15_third;

  IF n <> expected THEN
    RAISE EXCEPTION
      'S15 ③ FAILED (performance-design §一): 過濾後候選數為 %（< LIMIT %），'
      '故回傳筆數應等於 %，實際 %。這個差距的意思是 LIMIT 作用在**未過濾**的'
      '集合上——即「先查再於應用層過濾」。①② 對那種實作仍會通過，只有本條會紅。',
      expected, limit_n, expected, n;
  END IF;

  -- 全表列數必須大於 LIMIT，否則本條沒有鑑別力（fixture 前提）。
  SELECT count(*) INTO n FROM memory.memory_records
   WHERE content LIKE '__u8_fixture__%';
  IF n <= limit_n THEN
    RAISE EXCEPTION
      'S15 ③ 的 fixture 前提不成立：全表 fixture 列數（%）必須大於 LIMIT（%），'
      '否則「先查再過濾」與「同查詢」會回同一個結果。', n, limit_n;
  END IF;

  RAISE NOTICE
    'S15（檢索查詢的組合正確性：可見範圍／向量空間分群／LIMIT 作用在已過濾集合）通過';
END $$;

ROLLBACK;
