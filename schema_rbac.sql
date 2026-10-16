-- =============================================================================
-- Cloud-360 Full Schema + RBAC Seed
-- Branch: luojingting/feat/role-permission-redesign（＋後續 A3 DDL 增量）
--
-- 單一腳本涵蓋：
--   A) 核心：users / user_diagrams / diagram_shares（架構圖儲存與分享）
--   B) A4：user_diagram_chats（聊天持久化）+ users.last_opened_diagram_id
--      另含 users.last_activity_at（最後活動時間欄位）
--   E) A3：architecture_reviews（評核結果）+ wa_lenses（Offline Lens 現行標準）
--   H) U4：projects / systems / diagram_change_records 三表
--      ＋ user_diagrams.system_id（歸屬的權威來源）＋ 兩個部分唯一索引
--   J) U18：project_members / reselection_events / system_requirement_fields 三表
--      （per-project 成員與角色、改選稽核、系統層需求欄位值）
--      ＋ U23：project_members 的 user_id 索引 ix_project_members_user_id
--   K) U9：保留系統 actor 的 seed（users 的一列，90 天記憶清除的稽核 actor）
--   C) RBAC：role_permissions + 預設矩陣（352 列）
--   D) 不建立固定密碼管理員；bootstrap admin 由後端依環境變數建立
--   X) 擴充：pgvector（`vector` 型別；U5 記憶表的 vector(1024) 欄位需要）
--
-- 執行（新環境可只跑這支）：
--   psql "$DATABASE_URL" -f schema_rbac.sql
--
-- 注意：
--   - 表使用 IF NOT EXISTS，可重複執行
--   - role_permissions 會 DELETE 後重播預設（Admin UI 調過請先備份）
--   - 不覆寫既有 admin 密碼
--   - 矩陣來源：aidlc-docs/construction/plans/role-permission-design.md
--   - A3：評核內容在 architecture_reviews；可編輯 Lens 在 wa_lenses.body_json
--   - H)：本檔只在**空 volume** 執行，故既有環境不會經過它。既有環境取得 H) 的
--     結構與資料遷移的唯一路徑是
--       cd backend && python scripts/run_hierarchy_migration.py
--     它自己以可重跑安全的方式建同一組物件（DDL 兩處並存，改一處必須改另一處）。
--     詳見 DEPLOY.md 第 2.2.7 節。
--   - J)：同樣只在空 volume 執行。既有環境的建立路徑是
--       cd backend && python scripts/run_meta_schema_migration.py
--     而它**直接解析本檔的 X)／I)／J) 三個區塊並執行**，所以那三個區塊
--     的 DDL 只有這一份（與 H) 的「DDL 兩處並存」刻意不同）。詳見 DEPLOY.md 第 2.2.9 節。
--   - K)：既有環境取得這一列的路徑是
--       cd backend && python3 scripts/seed_retention_system_actor.py
--     它 import run_meta_schema_migration.extract_blocks() 解析本檔的 K) 區塊，
--     所以 SQL 只有這一份。**不要為了取得它而重跑整支本檔**——下方 C) RBAC
--     區塊開頭那條逐字為 `DELETE FROM role_permissions;` 的敘述會清掉
--     任何經 Admin UI 調整過的權限矩陣
--     （下一條注意事項已警告過，但「重跑整支檔」在既有環境聽起來像安全操作，
--     所以在這裡再寫一次）。K) **刻意不在** run_meta_schema_migration.py 的
--     BLOCKS_TO_RUN 內：那支腳本的輸出逐字宣告「不塞任何資料」（契約 K-15 的
--     observable_side_effects）。詳見 DEPLOY.md 第 2.2.11 節。
--   - 本檔是**單一交易**（BEGIN … COMMIT）。伺服器沒有安裝 pgvector 時，
--     下面那行 CREATE EXTENSION 會是硬 ERROR（could not open extension
--     control file），整個交易中止 → 一張表都不會建。本機請先確認：
--       psql "$DATABASE_URL" -c "SELECT * FROM pg_available_extensions WHERE name='vector'"
--     必須有一列。詳見 LOCAL-DEV.md §2。
-- =============================================================================

BEGIN;

-- ###########################################################################
-- X) Extensions — 必須是 BEGIN 之後的第一條敘述
-- ###########################################################################
-- `vector` 型別必須先存在，任何宣告 vector 欄位的表才建得起來。後端啟動時的
-- database._ensure_vector_extension() 涵蓋「既有非空 volume」那條路徑；本行
-- 涵蓋「空 data volume 初始化」與「本機 psql」兩條路徑。兩者互補，不是二選一。
CREATE EXTENSION IF NOT EXISTS vector;

-- ###########################################################################
-- A) Core: users + architecture diagrams + shares
-- ###########################################################################

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR NOT NULL,
  password_hash VARCHAR NOT NULL,
  role VARCHAR NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  last_opened_diagram_id INTEGER,
  last_activity_at TIMESTAMP WITH TIME ZONE
);

-- 既有資料庫補欄（本檔可重跑；後端啟動時的 _ensure_last_activity_schema 亦會補）
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN users.last_activity_at IS
  '最後活動時間（UTC）。任何以有效憑證發出的請求都更新它，同一帳號至多每 5 分鐘寫一次。NULL = 從未活動，不套用逾期標示。刻意無預設值。';

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);

CREATE TABLE IF NOT EXISTS user_diagrams (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users (id),
  title VARCHAR NOT NULL DEFAULT '未命名架構圖',
  xml_data TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_user_diagrams_id ON user_diagrams (id);

-- 延後加 FK，避免 users ↔ user_diagrams 循環建立問題
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_last_opened_diagram'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT fk_users_last_opened_diagram
      FOREIGN KEY (last_opened_diagram_id)
      REFERENCES user_diagrams (id)
      ON DELETE SET NULL;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS diagram_shares (
  user_id INTEGER NOT NULL REFERENCES users (id),
  diagram_id INTEGER NOT NULL REFERENCES user_diagrams (id),
  PRIMARY KEY (user_id, diagram_id)
);

COMMENT ON TABLE user_diagrams IS 'A2: per-user architecture diagram drafts (draw.io XML)';
COMMENT ON TABLE diagram_shares IS 'A2: many-to-many share ACL for diagrams';

-- ###########################################################################
-- B) A4: chat persistence per user × diagram
-- ###########################################################################

CREATE TABLE IF NOT EXISTS user_diagram_chats (
  user_id INTEGER NOT NULL REFERENCES users (id),
  diagram_id INTEGER NOT NULL REFERENCES user_diagrams (id) ON DELETE CASCADE,
  messages_json TEXT NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, diagram_id)
);

COMMENT ON TABLE user_diagram_chats IS 'A4: chat messages keyed by user × diagram';

-- ###########################################################################
-- E) A3: Well-Architected review persistence
--    對應 backend/models.py ArchitectureReview、database._ensure_a3_schema()
-- ###########################################################################

CREATE TABLE IF NOT EXISTS architecture_reviews (
  id SERIAL PRIMARY KEY,
  diagram_id INTEGER REFERENCES user_diagrams (id) ON DELETE CASCADE,
  created_by INTEGER NOT NULL REFERENCES users (id),
  provider VARCHAR(16) NOT NULL DEFAULT 'aws',
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  overall_score INTEGER,
  scores_json TEXT,
  findings_json TEXT DEFAULT '[]',
  suggestions_text TEXT,
  error_message TEXT,
  rule_pack_version VARCHAR(64),
  xml_snapshot TEXT,
  archived BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_architecture_reviews_diagram_id
  ON architecture_reviews (diagram_id);

CREATE INDEX IF NOT EXISTS ix_architecture_reviews_created_by
  ON architecture_reviews (created_by);

COMMENT ON TABLE architecture_reviews IS
  'A3: WA review rows — overall_score + scores_json (lens/heuristic) + findings_json + suggestions_text';
COMMENT ON COLUMN architecture_reviews.scores_json IS
  'JSON: source_of_truth, pillar_scores, risk_counts, lens, heuristic, findings_source, …';
COMMENT ON COLUMN architecture_reviews.findings_json IS
  'JSON array of findings (Lens HIGH/MEDIUM preferred; heuristic fallback on lens failure)';
COMMENT ON COLUMN architecture_reviews.status IS
  'pending | rules_complete | complete | rules_only | unsupported';
COMMENT ON COLUMN architecture_reviews.diagram_id IS
  'Nullable when review runs from uploaded XML without saving a workspace diagram';
COMMENT ON COLUMN architecture_reviews.xml_snapshot IS
  'XML snapshot at review time (required for ephemeral / audit)';

CREATE TABLE IF NOT EXISTS wa_lenses (
  id SERIAL PRIMARY KEY,
  lens_id VARCHAR(64) NOT NULL DEFAULT 'cloud360-core-mvp',
  provider VARCHAR(16) NOT NULL DEFAULT 'aws',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  body_json TEXT NOT NULL,
  updated_by INTEGER REFERENCES users (id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_wa_lenses_lens_id ON wa_lenses (lens_id);
CREATE INDEX IF NOT EXISTS ix_wa_lenses_is_active ON wa_lenses (is_active);
CREATE INDEX IF NOT EXISTS ix_wa_lenses_provider ON wa_lenses (provider);

COMMENT ON TABLE wa_lenses IS
  'A3: per-cloud Offline Custom Lens JSON; one active row per provider (aws/gcp/azure)';
COMMENT ON COLUMN wa_lenses.body_json IS
  'Full Custom Lens JSON (schemaVersion 2021-11-01, five pillars)';
COMMENT ON COLUMN wa_lenses.provider IS
  'aws | gcp | azure — active lens resolved per provider';

-- 既有庫升級（IF NOT EXISTS / DROP NOT NULL 可重複執行）
ALTER TABLE architecture_reviews ALTER COLUMN diagram_id DROP NOT NULL;
ALTER TABLE architecture_reviews ADD COLUMN IF NOT EXISTS xml_snapshot TEXT;
ALTER TABLE wa_lenses ADD COLUMN IF NOT EXISTS provider VARCHAR(16) NOT NULL DEFAULT 'aws';

-- ###########################################################################
-- C1 Cost / FinOps tables — RETIRED (U3 legacy-cost-retirement)
-- Live tables renamed to archive_*；應用零讀寫；保留 ≥90 天後另開 chore DROP。
-- ###########################################################################

CREATE TABLE IF NOT EXISTS archive_diagram_cost (
  diagram_id INTEGER PRIMARY KEY REFERENCES user_diagrams (id) ON DELETE CASCADE,
  pricing_region VARCHAR(64),
  monthly_budget NUMERIC(12, 2),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS archive_diagram_cost_line (
  diagram_id INTEGER NOT NULL REFERENCES user_diagrams (id) ON DELETE CASCADE,
  mxcell_id VARCHAR(128) NOT NULL,
  hours INTEGER NOT NULL DEFAULT 24,
  sku_override VARCHAR(128),
  hourly_override NUMERIC(12, 2),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (diagram_id, mxcell_id)
);

CREATE TABLE IF NOT EXISTS archive_pricing_cache (
  cloud VARCHAR(16) NOT NULL,
  sku VARCHAR(128) NOT NULL,
  region VARCHAR(64) NOT NULL,
  hourly NUMERIC(12, 6) NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (cloud, sku, region)
);

CREATE TABLE IF NOT EXISTS archive_cost_audit_event (
  id SERIAL PRIMARY KEY,
  diagram_id INTEGER NOT NULL REFERENCES user_diagrams (id) ON DELETE CASCADE,
  field VARCHAR(32) NOT NULL,
  mxcell_id VARCHAR(128),
  old_value TEXT,
  new_value TEXT NOT NULL,
  actor_username VARCHAR(128) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_archive_cost_audit_event_diagram_created
  ON archive_cost_audit_event (diagram_id, created_at DESC);

COMMENT ON TABLE archive_diagram_cost IS 'C1 retired: archived per-diagram pricing region/budget; app must not read/write; drop after >=90d';
COMMENT ON TABLE archive_diagram_cost_line IS 'C1 retired: archived hours/overrides; app must not read/write; drop after >=90d';
COMMENT ON TABLE archive_pricing_cache IS 'C1 retired: archived price cache; app must not read/write; drop after >=90d';
COMMENT ON TABLE archive_cost_audit_event IS 'C1 retired: archived cost audit; app must not read/write; drop after >=90d';

-- ###########################################################################
-- C1 Estimate intake (U2 /api/cost/v1) — EstimateSet tree + Advice shell
-- ###########################################################################

CREATE TABLE IF NOT EXISTS estimate_sets (
  id SERIAL PRIMARY KEY,
  owner_user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  diagram_id INTEGER,
  note TEXT,
  workload_context_json TEXT,
  is_saved BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_estimate_sets_owner
  ON estimate_sets (owner_user_id);

CREATE TABLE IF NOT EXISTS estimates (
  id SERIAL PRIMARY KEY,
  estimate_set_id INTEGER NOT NULL REFERENCES estimate_sets (id) ON DELETE CASCADE,
  cloud VARCHAR(16) NOT NULL,
  stated_total NUMERIC(18, 6),
  currency VARCHAR(16),
  parsed_line_count INTEGER NOT NULL DEFAULT 0,
  unparsed_line_count INTEGER NOT NULL DEFAULT 0,
  source_format VARCHAR(8) NOT NULL,
  CONSTRAINT uq_estimates_set_cloud UNIQUE (estimate_set_id, cloud)
);

CREATE INDEX IF NOT EXISTS ix_estimates_set
  ON estimates (estimate_set_id);

CREATE TABLE IF NOT EXISTS estimate_line_items (
  id SERIAL PRIMARY KEY,
  estimate_id INTEGER NOT NULL REFERENCES estimates (id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  item_name TEXT,
  spec TEXT,
  spec_description TEXT,
  quantity NUMERIC(18, 6),
  amount NUMERIC(18, 6),
  currency VARCHAR(16),
  parse_status VARCHAR(32) NOT NULL,
  raw_text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_estimate_line_items_estimate
  ON estimate_line_items (estimate_id);

CREATE TABLE IF NOT EXISTS estimate_shares (
  estimate_set_id INTEGER NOT NULL REFERENCES estimate_sets (id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  shared_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (estimate_set_id, user_id)
);

CREATE TABLE IF NOT EXISTS estimate_audit_events (
  id SERIAL PRIMARY KEY,
  actor_user_id INTEGER NOT NULL REFERENCES users (id),
  estimate_set_id INTEGER NOT NULL REFERENCES estimate_sets (id) ON DELETE CASCADE,
  event_type VARCHAR(64) NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  cloud VARCHAR(16),
  parsed_line_count INTEGER,
  unparsed_line_count INTEGER
);

CREATE INDEX IF NOT EXISTS ix_estimate_audit_events_set
  ON estimate_audit_events (estimate_set_id);

CREATE TABLE IF NOT EXISTS advice (
  estimate_set_id INTEGER PRIMARY KEY
    REFERENCES estimate_sets (id) ON DELETE CASCADE,
  status VARCHAR(32) NOT NULL DEFAULT 'generating',
  saving_text TEXT,
  comparison_text TEXT,
  quality_text TEXT,
  unavailable_reasons_json TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

COMMENT ON TABLE estimate_sets IS 'U2: upload batch root; diagram_id is label only';
COMMENT ON TABLE advice IS 'U7 owns advice body; U2 creates shell + thin GET';

-- ###########################################################################
-- H) U4 hierarchy-data: projects / systems / diagram_change_records
--    對應 backend/services/hierarchy_migration.py 的 _ensure_hierarchy_schema()
--    （該函式是既有非空 volume 的唯一演進路徑；本檔只在空 volume 執行）
-- ###########################################################################

CREATE TABLE IF NOT EXISTS projects (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  owner_user_id INTEGER NOT NULL REFERENCES users (id),
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_projects_name_not_blank CHECK (length(trim(name)) > 0)
);

CREATE INDEX IF NOT EXISTS ix_projects_owner_user_id ON projects (owner_user_id);

-- BR1.3 (1)：每位使用者至多一個 is_default 為真的專案。
-- 範圍只引用本表欄位（owner_user_id）——唯一性約束無法以另一張表 join 來的值
-- 為範圍，所以 systems 那一層只能以 project_id 為範圍（見下方），不是以擁有者。
CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_default_per_owner
  ON projects (owner_user_id) WHERE is_default;

COMMENT ON COLUMN projects.is_default IS
  'U4/BR1.3: migration-idempotency carrier. At most one TRUE row per owner (uq_projects_default_per_owner). Written ONLY by services/hierarchy_migration.py; not a user-editable attribute.';
COMMENT ON COLUMN projects.owner_user_id IS
  'U4: who owns this project. Deletion behaviour of the referenced user is deliberately NOT decided (OQ-H1, landing U7) — no ON DELETE clause, same as user_diagrams.user_id.';

CREATE TABLE IF NOT EXISTS systems (
  id SERIAL PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE RESTRICT,
  name VARCHAR(255) NOT NULL,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_systems_name_not_blank CHECK (length(trim(name)) > 0)
);

CREATE INDEX IF NOT EXISTS ix_systems_project_id ON systems (project_id);

-- BR1.3 (2)：每個專案至多一個 is_default 為真的系統。範圍為 project_id。
-- 「每位使用者至多一組預設專案／系統」是兩層的**遞移**結果，不是單一約束；
-- 它另外依賴「預設 System 總是建在該使用者的預設 Project 底下」，而**沒有任何
-- 約束擋住這一點**——那個耦合由遷移程序（BR2.5，唯一寫入端）供應。
CREATE UNIQUE INDEX IF NOT EXISTS uq_systems_default_per_project
  ON systems (project_id) WHERE is_default;

COMMENT ON COLUMN systems.is_default IS
  'U4/BR1.3: migration-idempotency carrier. At most one TRUE row per project (uq_systems_default_per_project). The composite "one default pair per user" also needs BR2.5 exclusive-writer discipline; no constraint enforces it.';

-- BR1.2：user_diagrams.system_id —— 歸屬的權威來源（decisions.md ADR-002）。
-- 可為空，因為欄位必須先加上去、再由遷移填滿；遷移跑完的那一刻它必須全部非空
-- （BR2.1／AC9.1.4）。收成 NOT NULL 與 AC9.1.3 衝突，故不做（OQ-H2）。
ALTER TABLE user_diagrams ADD COLUMN IF NOT EXISTS system_id INTEGER;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_diagrams_system'
  ) THEN
    ALTER TABLE user_diagrams
      ADD CONSTRAINT fk_user_diagrams_system
      FOREIGN KEY (system_id)
      REFERENCES systems (id)
      ON DELETE RESTRICT;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_user_diagrams_system_id ON user_diagrams (system_id);

COMMENT ON COLUMN user_diagrams.system_id IS
  'U4/ADR-002: AUTHORITATIVE source of ownership (which system this diagram belongs to). user_id answers "who created it", NOT belonging. Nullable by design; ON DELETE RESTRICT so deleting a System cannot orphan a diagram (BR1.2) — SET NULL would itself create the BR2.1 violation. Filled by services/hierarchy_migration.py.';

CREATE TABLE IF NOT EXISTS diagram_change_records (
  id SERIAL PRIMARY KEY,
  diagram_id INTEGER NOT NULL REFERENCES user_diagrams (id) ON DELETE CASCADE,
  source VARCHAR(32) NOT NULL,
  actor_user_id INTEGER NOT NULL REFERENCES users (id),
  requirement_summary TEXT NOT NULL,
  requirement_label VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_diagram_change_records_source
    CHECK (source IN ('brain_orchestration')),
  CONSTRAINT ck_diagram_change_records_summary_not_blank
    CHECK (length(trim(requirement_summary)) > 0)
);

CREATE INDEX IF NOT EXISTS ix_diagram_change_records_diagram_id
  ON diagram_change_records (diagram_id);

-- U4-R1：90 天保存期的清除查詢以 created_at 為截止欄位；沒有這個索引它是全表掃描，
-- 而這張表**沒有任何讀取端**會順手建索引（本輪只寫不讀，Q2=A）。
CREATE INDEX IF NOT EXISTS ix_diagram_change_records_created_at
  ON diagram_change_records (created_at);

COMMENT ON TABLE diagram_change_records IS
  'U4: change records for diagrams. WRITE-ONLY this round (no reader exists). Coverage is declared by the source column, NOT by the table name — read source before presenting anything (BR3.1). Retention 90 days keyed on created_at (U4-R1); the purge mechanism itself is not in this repo (U4-R2).';
COMMENT ON COLUMN diagram_change_records.source IS
  'U4/BR3.1: closed enum declaring this table COVERAGE. Only legal value this round: brain_orchestration (brain-delegated changes). Edits made through the existing A1 page do NOT pass through the writer, so rows here are NOT a complete change history. Adding a future writer = add an enum value, no schema migration.';
COMMENT ON COLUMN diagram_change_records.actor_user_id IS
  'U4/SEC-4: WHO caused this change. NOT NULL on purpose — a record that says "the diagram changed" but not "who changed it" fails the audit-logging face. The writer (U12) must store the user who actually caused the change and must NOT default to the session owner (OQ-H3 still open).';

-- ###########################################################################
-- I) U5 memory-data: memory schema (semantic / procedure / episodic)
--    獨立 schema，**非 public**（BR1.1）。本 repo 的第一個 CREATE SCHEMA——
--    在此之前全樹無 CREATE SCHEMA、無 search_path（契約 K-05 的 precedent）。
--    `vector` 擴充由上方 X) 區塊建立，本區塊只使用它。
--    全部敘述為可重跑形狀（BR1.3）；本單元**無資料遷移**，故無 K-04 那類風險。
-- ###########################################################################

CREATE SCHEMA IF NOT EXISTS memory;

COMMENT ON SCHEMA memory IS
  'U5/BR1.1: isolated schema for the brain memory layer. Deliberately NOT public — the grant boundary (BR1.2) works by opening ONLY this schema, so moving these tables to public silently removes the boundary while everything keeps working. Cross-schema references to public.users are intentional (K-05 schema_isolation.form: keeps native cross-schema join).';

CREATE TABLE IF NOT EXISTS memory.memory_records (
  id SERIAL PRIMARY KEY,
  kind VARCHAR(16) NOT NULL,
  owner_user_id INTEGER NOT NULL REFERENCES public.users (id),
  visibility_scope VARCHAR(32) NOT NULL,
  content TEXT NOT NULL,
  -- 1024 維與 OLLAMA_EMBED_MODEL 預設 bge-m3 的 dense 維度一致（契約 K-01）。
  -- 可為空是刻意的：fulltext 模式下的列沒有 embedding（BR3.3）。
  embedding vector(1024),
  embedding_model VARCHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  CONSTRAINT ck_memory_records_kind
    CHECK (kind IN ('semantic', 'procedure', 'episodic')),
  CONSTRAINT ck_memory_records_content_not_blank
    CHECK (length(trim(content)) > 0),
  -- BR4.1：只有 episodic 受 90 天保存期約束，而它的 expires_at **必填**。
  -- 這條不是潔癖：清除作業**依 expires_at 選列**，所以 NULL 的 episodic 列
  -- 永遠不會被選中——漏填的後果是永久保留且沒有任何跡象。
  CONSTRAINT ck_memory_records_episodic_has_expiry
    CHECK (kind <> 'episodic' OR expires_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ix_memory_records_owner_user_id
  ON memory.memory_records (owner_user_id);
-- 清除作業以 expires_at 為截止欄位；沒有索引即全表掃描。
CREATE INDEX IF NOT EXISTS ix_memory_records_expires_at
  ON memory.memory_records (expires_at);
-- BR3.1：相似度檢索一律附 embedding_model 過濾，故該欄是查詢條件之一。
CREATE INDEX IF NOT EXISTS ix_memory_records_embedding_model
  ON memory.memory_records (embedding_model);

-- U8/NFR3.22（[N2]=B）：相似度檢索的向量索引。
--
-- **HNSW 而非 ivfflat**：ivfflat 的 `lists` 參數需要先有資料才能選得合理，
-- 而本表在建立索引時是空的；HNSW 可在空表上建立且不需要該類參數。
--
-- **opclass 與查詢的距離運算子必須成對**，而不成對的後果是**靜默的**：
-- 索引被忽略、查詢仍然正確（仍回精確最近鄰）、延遲在空表上看起來一樣好。
-- 本 repo 的那一對是 `vector_cosine_ops` ↔ `<=>`
-- （`backend/services/memory_service.py` 的 `SEARCH_SQL`），由兩道斷言鎖住：
--   * `S14`（本檔下游的 `verify_memory_schema.sql`）在真實 PostgreSQL 上以
--     `SET enable_seqscan = off` ＋ `EXPLAIN` 斷言計畫真的用到本索引；
--   * `tests/test_memory_contract.py` 的 `C6` 鎖住 Python 側的運算子與
--     本行的 opclass 是同一對。
-- 實測（PostgreSQL 17.7 ＋ pgvector 0.8.1）：`<=>` 得 `Index Scan`，
-- `<->` 對同一個索引得 `Seq Scan`，即使 `enable_seqscan = off`。
--
-- cosine 的理由：`embedding` 的維度對齊 `OLLAMA_EMBED_MODEL` 預設 bge-m3，
-- 而該模型的慣用度量是 cosine 相似度。
CREATE INDEX IF NOT EXISTS ix_memory_records_embedding_hnsw
  ON memory.memory_records USING hnsw (embedding vector_cosine_ops);

COMMENT ON COLUMN memory.memory_records.embedding_model IS
  'U5/BR3.1: NOT NULL on purpose, and similarity search MUST filter on it. Same dimensionality is NOT the same vector space — omitting this filter makes cross-model retrieval return garbage AND report no error (decisions.md ADR-008). This is the only failure mode in this unit that is completely silent: type, dimension, index and query all stay valid.';
COMMENT ON COLUMN memory.memory_records.embedding IS
  'U5/BR3.3: nullable BY DESIGN. Rows created under EMBEDDING_PROVIDER=fulltext carry NULL here and are invisible to vector search until re-embedded. NULL is a meaningful state, not a defect — backfilling it or tightening to NOT NULL breaks the fulltext fallback. embedding_model stays NOT NULL even then.';
COMMENT ON COLUMN memory.memory_records.expires_at IS
  'U5/BR4.1: required when kind = episodic (createdAt + 90 days), NULL otherwise. FR4.5 scopes the 90-day retention to episodic memory ONLY. Enforced by ck_memory_records_episodic_has_expiry because the purge selects BY this column: a NULL episodic row is never selected, i.e. kept forever with no trace.';

CREATE TABLE IF NOT EXISTS memory.memory_audit_events (
  id SERIAL PRIMARY KEY,
  -- BR2.1／DG-1：**刻意不對 memory_records 設外鍵。** 見下方 COMMENT。
  memory_id INTEGER NOT NULL,
  actor_user_id INTEGER NOT NULL REFERENCES public.users (id),
  action VARCHAR(32) NOT NULL,
  previous_scope VARCHAR(32),
  new_scope VARCHAR(32),
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_memory_audit_events_action
    CHECK (action IN ('deleted_by_user', 'purged_by_retention', 'scope_changed'))
);

-- NFR7.2：稽核保存期為 90 天，以**自身** occurred_at 為鍵（不是 join 記憶的時間）。
-- 沒有這個索引，清除查詢是全表掃描——而這張表本輪**沒有任何讀取端**
-- （US4.3 的查詢面是回補項 N-8，屬 U8），所以不會有人順手建它。
-- U4 對 diagram_change_records 踩過同一個洞並逐字記下同樣的理由。
CREATE INDEX IF NOT EXISTS ix_memory_audit_events_occurred_at
  ON memory.memory_audit_events (occurred_at);
CREATE INDEX IF NOT EXISTS ix_memory_audit_events_memory_id
  ON memory.memory_audit_events (memory_id);

COMMENT ON TABLE memory.memory_audit_events IS
  'U5/DG-1: audit trail for memory deletion and visibility-scope changes. Deliberately holds NO foreign key to memory_records so the trail OUTLIVES the memory it describes. With an FK both options break an approved requirement: CASCADE makes FR4.7 (deletion leaves an audit record) vacuous after 90 days, RESTRICT makes FR4.5 (automatic expiry) impossible. Cost, stated plainly: memory_id has NO referential integrity. Retention is 90 days keyed on occurred_at (NFR7.2) — its own clock, NOT the memory''s.';
COMMENT ON COLUMN memory.memory_audit_events.memory_id IS
  'U5/BR2.1: opaque identifier, NOT a foreign key. The sole writer is the K-08 facade, which is an application-layer guarantee rather than a database one.';
COMMENT ON COLUMN memory.memory_audit_events.action IS
  'U5/BR2.3: closed enum. deleted_by_user and purged_by_retention are kept APART on purpose — the first is FR4.6 (the user exercising deletion), the second is FR4.5 (retention expiry). Collapsing them into one "deleted" value makes those two indistinguishable in the audit, and their compliance meaning differs.';
COMMENT ON COLUMN memory.memory_audit_events.actor_user_id IS
  'U5/BR2.4: for purged_by_retention there is NO natural user — the purge is schedule-triggered with nobody in the loop (FR4.5a), so a reserved system actor is used. Filling in the memory owner would make the audit LIE about who deleted it; leaving it NULL would weaken "who did this" on every event.';
-- BR2.2：本表**刻意不含** content 與 embedding。這不是省略——稽核比記憶活得久
-- （BR2.1），若它含記憶內容，「保留稽核」就等於「保留被刪除的使用者資料」，
-- 使用者以為刪了而它還在，FR4.5 的 90 天刪除形同虛設。

-- ---------------------------------------------------------------------------
-- BR1.2：grant 邊界——只開放記憶 schema。
--
-- 角色由部署環境提供（POSTGRES_USER）；此處以 DO 區塊保持可重跑且不假設角色名。
-- **本輪未被 CI 驗證**（OPEN-CG5-1）：驗它需要第二個資料庫角色並以該角色嘗試
-- 越界，而 N-2 的 service container 只有 superuser。這是資料庫層的唯一邊界，
-- 故此缺口如實記載而非以註解帶過。
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  EXECUTE format('GRANT USAGE ON SCHEMA memory TO %I', current_user);
  EXECUTE format(
    'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA memory TO %I',
    current_user
  );
  EXECUTE format(
    'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA memory TO %I', current_user
  );
END $$;

-- ###########################################################################
-- J) U18 project-meta-data: project_members / reselection_events /
--    system_requirement_fields
--
--    三張表皆在 public schema、皆為全新。契約 K-15 的 observable_side_effects
--    逐字「**不含任何資料寫入**」——與 H) 的關鍵差別是本區塊**沒有資料遷移**，
--    沒有既有資料要搬。全部敘述為可重跑形狀（BR2.1）。
--
--    **U20 之後的一處例外（OPEN-RF20-8，如實記載）**：system_requirement_fields
--    之後的條件式 DO 區塊會把舊定義的 updated_on_behalf_of（integer ＋ 指向 users
--    的外鍵）收斂為 VARCHAR(64)、無外鍵。只在欄位仍為 integer 時執行，型別轉換會
--    重寫該欄並把舊值轉為 NULL——在沒有任何程式寫過舊欄位的前提下不改變資料內容，
--    但它不再是純 DDL。已收斂的資料庫上整段不做任何事。
--
--    既有非空 volume 的唯一建立路徑是
--      cd backend && python scripts/run_meta_schema_migration.py
--    該腳本**直接解析本檔的 X)／I)／J) 三個區塊並執行**，所以這三個區塊的 DDL
--    只有這一份——改這裡就等於改了那條路徑。**這與 H) 刻意不同**：H) 的 DDL
--    在 services/hierarchy_migration.py 另有一份物化，改一處必須記得改另一處。
--    詳見 DEPLOY.md 第 2.2.9 節。
--
--    **本區塊的欄位集合取自 domain-design 的 Entity Ownership 表
--    （components.md:819-820），不是取自本單元的 entities.md**——後者比它少九個
--    欄位（ReselectionEvent 五個、SystemRequirementField 四個），其中六個正是
--    FR12.4b 與 ADR-015 點名的稽核事實，而 AC12.2.2 的 Then（顯示誰在何時把角色
--    由什麼改為什麼）需要其中四個。缺口與回補指派見 OPEN-ND18-1。
-- ###########################################################################

CREATE TABLE IF NOT EXISTS project_members (
  id SERIAL PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
  -- [ND1]=A：使用者硬刪除的行為**上游刻意未決**（OQ-H1），故**無 ON DELETE 子句**
  -- ——沿用 projects.owner_user_id 的同一個慣例（本檔 H) 區塊），不自行決定。
  user_id INTEGER NOT NULL REFERENCES users (id),
  role VARCHAR(32) NOT NULL,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  invited_by INTEGER REFERENCES users (id),
  CONSTRAINT ck_project_members_role
    CHECK (role IN ('project_admin', 'member')),
  CONSTRAINT uq_project_members_project_user UNIQUE (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_project_members_user_id ON project_members (user_id);

-- 本表的索引，兩個方向：
--   project_id 側不需另建——uq_project_members_project_user 以它為前導欄，同時
--   覆蓋 K-16 的 resolve_project_role（最熱路徑）、list_members、FR12.4 的挑選
--   過濾，以及上面那條 ON DELETE CASCADE 的子側掃描。
--   user_id 側由 U23 建立（ix_project_members_user_id，[PPN1]=A）：原本「刻意不建」
--   的兩個條件中，條件 ① 已成立（專案清單改讀成員列，[PP1]=A——可見性查詢的成員
--   那一半以 user_id 為條件從本表出發）；條件 ② 仍未決（使用者硬刪除行為是 OQ-H1），
--   與本索引無關。
--   **不加 schema 前綴、維持單行**：test_membership_data.py 的 ddl_indexes 正規式以
--   `ON project_members` 擷取，寫成 `ON public.project_members` 會讓 test_M3 認不出。
--   既有環境由 backend/scripts/run_meta_schema_migration.py 重跑建立（DEPLOY.md 2.2.9）。

COMMENT ON TABLE project_members IS
  'U18/K-15: per-project membership and role — the data basis for per-project authorization (K-16 MembershipFacade). This unit delivers DDL ONLY: no read, no write, no endpoint (K-15 authorization_responsibility is verbatim "none — DDL runs on the deploy/startup path and is not subject to user authorization"). Access authorization to these rows belongs to the K-16 facade.';
COMMENT ON COLUMN project_members.project_id IS
  'U18/[ND1]=A: ON DELETE CASCADE. A membership row is meaningless once its project is gone, and CASCADE additionally keeps already-shipped code working: hierarchy_service.delete_project() guards ONLY on is_default (:153) and on remaining systems (:156) — there is NO member guard — while every project gets at least one member row once U19 lands. RESTRICT would turn db.delete(project) (:161) into an uncaught IntegrityError at commit, i.e. a 500 instead of the message-carrying HierarchyConflictError that BR4.4 produces.';
COMMENT ON COLUMN project_members.user_id IS
  'U18/[ND1]=A: deletion behaviour of the referenced user is deliberately NOT decided (OQ-H1, landing U19) — no ON DELETE clause, same as projects.owner_user_id and user_diagrams.user_id.';
COMMENT ON COLUMN project_members.role IS
  'U18/OPEN-P2: per-project role, closed enum (project_admin | member) per the K-16 ProjectRole type. SAME NAME, DIFFERENT MEANING from the global role in users.role / role_permissions — see services/rbac.py CANONICAL_ROLES, which contains a global Project_Admin that is NOT this. The database cannot enforce that distinction, so this comment is the only place it is written down; FR12.6 requires BOTH layers to pass and neither substitutes for the other.';
COMMENT ON COLUMN project_members.joined_at IS
  'U18/BR1.1: NOT NULL on purpose. FR12.4 automatic reselection picks the earliest joiner and reads this column DIRECTLY; ties are broken deterministically together with user_id. Nullable would make the pick UNORDERED over NULLs — a different person selected each time, with no error whatsoever. Among this unit''s column constraints this is the only completely silent failure mode.';
COMMENT ON COLUMN project_members.invited_by IS
  'U18: who invited this member. Nullable because rows created by the system (automatic write on project creation, components.md:886) have no inviter.';

CREATE TABLE IF NOT EXISTS reselection_events (
  id SERIAL PRIMARY KEY,
  -- [ND1]=A：**刻意不對 projects 設外鍵。** 見下方 COMMENT ON TABLE。
  -- 形狀與 I) 區塊的 memory.memory_audit_events.memory_id 一對一對照。
  project_id INTEGER NOT NULL,
  -- U19/[FD3]=A：本欄由 U19 membership-service 定義、在此回補（跨單元 DDL 回補）。
  -- 它讓**人工角色變更**（FR12.2）與**自動改選**（FR12.4）寫同一張表，
  -- 關閉本區塊原本留下的 OPEN-ND18-3。兩個值是定案而非未決事項，所以本欄
  -- **有** CHECK ——這正是它與下面 previous_role／new_role（刻意無 CHECK）的分野。
  -- 既有環境尚未跑過 run_meta_schema_migration.py，故可直接寫進 CREATE TABLE
  -- 而不需 ALTER TABLE；**這個便宜只在腳本尚未執行時成立**，一旦跑過就得改走
  -- ALTER TABLE ... ADD COLUMN IF NOT EXISTS。
  cause VARCHAR(32) NOT NULL,
  promoted_user_id INTEGER NOT NULL REFERENCES users (id),
  previous_owner_user_id INTEGER REFERENCES users (id),
  previous_role VARCHAR(32),
  new_role VARCHAR(32) NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  acknowledged_at TIMESTAMPTZ,
  CONSTRAINT ck_reselection_events_cause
    CHECK (cause IN ('auto_reselection', 'manual_role_change'))
);

-- FR12.4c／[M1]=B：橫幅必須在**每次進入產品**時都看得到，故每一次落地頁載入都要
-- 查一次「這個人有沒有未確認的改選事件」——WHERE promoted_user_id = ?
-- AND acknowledged_at IS NULL。partial 的理由不只是省空間：**已確認的列會離開索引**，
-- 所以這個索引的大小是「目前未確認的改選事件數」而非「歷來總數」，前者在正常運作
-- 下趨近於零。同一慣用法在本檔 H) 區塊已有先例（uq_projects_default_per_owner）。
-- 拿掉 WHERE 子句之後索引仍然存在、查詢仍然正確，失敗模式是**效能而非正確性**
-- ——所以它需要一條驗 partial 的斷言（P8），否則永遠不會有人發現。
CREATE INDEX IF NOT EXISTS ix_reselection_events_unack
  ON reselection_events (promoted_user_id) WHERE acknowledged_at IS NULL;

-- 成員詳情頁的變更紀錄讀取端（components.md:886 逐字把本實體的讀取端列為
-- 「橫幅、成員詳情的變更紀錄」）。本表無外鍵，所以這個索引不會被 FK 順手帶出來。
CREATE INDEX IF NOT EXISTS ix_reselection_events_project_id
  ON reselection_events (project_id);

COMMENT ON TABLE reselection_events IS
  'U18/FR12.4b: audit trail for the automatic reselection of a project_admin, and the carrier of the banner acknowledgement state. Deliberately holds NO foreign key to projects so the trail OUTLIVES the project it describes — FR12.4b exists precisely so that "how did this person get project_admin" can still be answered afterwards, and CASCADE would erase the answer while RESTRICT would block project deletion. Cost, stated plainly: project_id has NO referential integrity. There is deliberately NO retention period here (unlike memory.memory_audit_events, NFR7.2): components.md:886 is verbatim that "clear" means setting acknowledged_at and the event row itself is never deleted. Do NOT add a 90-day purge by analogy with U5 — it would delete the FR12.4b audit. U19/[FD3]=A CLOSED OPEN-ND18-3 in the affirmative: this table ALSO carries manual FR12.2 role changes, distinguished by the `cause` column (see its comment). That is why the table has grown a ninth column and why TWO of the existing columns now mean different things depending on cause.';
COMMENT ON COLUMN reselection_events.project_id IS
  'U18/[ND1]=A: opaque identifier, NOT a foreign key — same shape and same reason as memory.memory_audit_events.memory_id. The sole writer is the K-16 facade, which is an application-layer guarantee rather than a database one.';
COMMENT ON COLUMN reselection_events.cause IS
  'U19/[FD3]=A: which kind of role change this row records — auto_reselection (the system promoted someone because the project owner was deactivated) or manual_role_change (an admin changed someone''s role). Added by U19, which is the sole writer, and it CLOSES OPEN-ND18-3 in the affirmative: both kinds live in THIS table so that AC12.2.2 reads the change log with ONE query against ONE source. Two columns change meaning with it and both are deliberate: previous_owner_user_id is the deactivated owner under auto_reselection but the ACTING ADMIN under manual_role_change (BR5.4 — both answer "who caused this change"), and acknowledged_at is meaningful ONLY under auto_reselection (BR5.5 — the banner says "the system handed ownership to you", which is the wrong message for a manual change). CONSEQUENCE, stated plainly: the banner query MUST filter on cause = ''auto_reselection'' AS WELL AS acknowledged_at IS NULL. Omitting the cause filter pops a banner with that wrong wording on EVERY manual role change. Unlike previous_role/new_role this column DOES carry a CHECK, because its two values are a decision ([FD3]=A) rather than an open question.';
COMMENT ON COLUMN reselection_events.promoted_user_id IS
  'U18/FR12.4b ("who"): the user who received project_admin. NOT NULL on purpose — a row saying "a reselection happened" without saying who was promoted answers none of the five facts FR12.4b requires, and AC12.2.2 renders exactly those facts on the member detail page. Also the leading column of ix_reselection_events_unack.';
COMMENT ON COLUMN reselection_events.previous_owner_user_id IS
  'U18/FR12.4b ("to whom"), WIDENED BY U19/[FD3]=A/BR5.4: this column points at a DIFFERENT PERSON depending on `cause`, and that is deliberate — under auto_reselection it is the deactivated owner whose deactivation triggered the reselection, under manual_role_change it is the ACTING ADMIN who performed the change (AC12.2.2''s "who"). Both answer the same question, "who caused this change". Before splitting it into two columns, read BR5.4: a split would make the AC12.2.2 change-log query read a different column per cause. Still nullable — a row may have neither.';
COMMENT ON COLUMN reselection_events.previous_role IS
  'U18/FR12.4b ("from what role"): the role before the change. Nullable — the promoted user may not have been a member at all. Deliberately NOT a closed enum, same as memory.memory_audit_events.previous_scope. The DECISION stands; its original REASON (OPEN-ND18-3 had not decided whether manual FR12.2 changes land here) was settled by U19/[FD3]=A — they do. The decision now rests on BR5.4/entities.md instead: the closed enum for ROLES is carried at the application layer (membership_types.ProjectRole), and infrastructure-specification.md 4.2 is verbatim that the ORM must NOT add a CheckConstraint here either. Contrast `cause`, which DOES have a CHECK because its value set is a decision rather than an open question.';
COMMENT ON COLUMN reselection_events.new_role IS
  'U18/FR12.4b ("to what role"): the role after the change. NOT NULL. See previous_role for why there is no CHECK constraint.';
COMMENT ON COLUMN reselection_events.occurred_at IS
  'U18/FR12.4b ("when"). Unlike memory.memory_audit_events.occurred_at this is NOT a purge key — this table has no retention period (see the table comment).';
COMMENT ON COLUMN reselection_events.acknowledged_at IS
  'U18/BR1.2: banner-read state keyed on the EVENT, not a per-user boolean. A per-user flag would hide the banner the SECOND time the same person is reselected — exactly the situation FR12.4c exists to prevent (K-15 verbatim). NULL = not yet acknowledged, so show the banner; non-NULL = acknowledged. Setting this column is what "clearing" an event means; the row is never deleted. U19/[FD3]=A/BR5.5 NARROWS ITS SCOPE: it is meaningful ONLY for cause = ''auto_reselection''. Rows with cause = ''manual_role_change'' are always NULL here and must NEVER raise a banner, because the banner wording is "the system handed ownership to you" — wrong for a manual change. The banner query therefore filters on BOTH cause AND acknowledged_at IS NULL.';

CREATE TABLE IF NOT EXISTS system_requirement_fields (
  id SERIAL PRIMARY KEY,
  system_id INTEGER NOT NULL REFERENCES systems (id) ON DELETE CASCADE,
  agent_group VARCHAR(64) NOT NULL,
  field_key VARCHAR(64) NOT NULL,
  value TEXT,
  cleared_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by INTEGER NOT NULL REFERENCES users (id),
  -- U20/[FD1]=A／BR47.1：agent 組識別字（例如 'cost'），**刻意不帶外鍵**。
  -- U18 原定義為 INTEGER REFERENCES users (id)；已用舊定義建過表的資料庫由下方
  -- 的條件式 DO 區塊收斂（BR47.2），本行只決定全新建表時的形狀。
  updated_on_behalf_of VARCHAR(64),
  -- 三欄（不是兩欄）：同一個 field_key 字串在不同 agent 組之下是**不同的欄位**，
  -- 因為 K-17 的 read_fields 回傳「按 agentGroup 分組、每組含 fieldKey」。
  -- 兩欄鍵會讓兩組共用的欄位名互相排擠。entities.md 的 entity_constraints 仍寫
  -- 兩欄形式——這裡是**刻意加寬**而非筆誤（nfr-design 審查 R-02，回補同 OPEN-ND18-1）。
  CONSTRAINT uq_system_requirement_fields_group_key
    UNIQUE (system_id, agent_group, field_key),
  -- BR1.4：鎖住三態模型的第三態——「清空」必須 value 為 NULL **且** cleared_at
  -- 有值。沒有這條，一列可以同時「有值」又「已清空」，而那種列的兩種讀法都說得通，
  -- 於是三態退化成「看寫入端當時想的是哪一種」。
  CONSTRAINT ck_system_requirement_fields_cleared_has_null_value
    CHECK (cleared_at IS NULL OR value IS NULL)
);

-- system_id 側不需另建索引：uq_system_requirement_fields_group_key 以它為前導欄，
-- 同時覆蓋 K-17 的 read_fields（WHERE system_id = ?）與上面那條 CASCADE 的子側掃描。

-- U20/BR47.2：把「已用 U18 舊定義建過表」的資料庫收斂成上面的定義。
--
-- CREATE TABLE IF NOT EXISTS 不會改既有欄位，故需要這一段。它**以欄位現況為條件**，
-- 而這個條件是整段的重點（functional-design review-02 R-01）：
--   - 只有 updated_on_behalf_of 仍為 integer 時才做任何事。已收斂的資料庫（或全新
--     建立的表）在第一個 IF 就返回——**重跑不改動任何資料**，也不取任何鎖。
--     無條件轉型會在每次重跑時把已寫入的代寫溯源（'cost' 等）清成 NULL，而且
--     不會有任何錯誤。
--   - 外鍵名稱以 pg_constraint.conkey 比對**這一欄**查得，不寫死自動產生的名稱，
--     也不會碰到同表 updated_by 那條合法的 users 外鍵。
--   - 舊值一律轉 NULL：舊定義下它是 users.id，轉成字串（例如 '123'）不屬於任何
--     agent 組，也無法還原成它代表的 agent。被清掉的非空值筆數以 NOTICE 回報
--     （實際上沒有任何程式寫過舊欄位，預期為 0）。
--   - lock_timeout 只在真的要轉型時設定、轉型後還原：DROP CONSTRAINT 也會對
--     users 取 ACCESS EXCLUSIVE 鎖，等不到就大聲失敗，而不是讓登入排隊。
-- 這段不再是純 DDL（型別轉換會重寫該欄，OPEN-RF20-8），故 run_meta_schema_migration.py
-- 的輸出與 DEPLOY.md 2.2.9 都如實寫明它。
DO $$
DECLARE
  current_type text;
  previous_lock_timeout text;
  fk_name text;
  cleared_rows bigint;
BEGIN
  SELECT c.data_type INTO current_type
    FROM information_schema.columns c
   WHERE c.table_schema = 'public'
     AND c.table_name = 'system_requirement_fields'
     AND c.column_name = 'updated_on_behalf_of';

  IF current_type IS DISTINCT FROM 'integer' THEN
    RETURN;
  END IF;

  previous_lock_timeout := current_setting('lock_timeout');
  PERFORM set_config('lock_timeout', '5s', true);

  FOR fk_name IN
    SELECT con.conname
      FROM pg_constraint con
      JOIN pg_class t ON t.oid = con.conrelid
      JOIN pg_namespace ns ON ns.oid = t.relnamespace
      JOIN pg_attribute a
        ON a.attrelid = con.conrelid AND a.attnum = ANY (con.conkey)
     WHERE ns.nspname = 'public'
       AND t.relname = 'system_requirement_fields'
       AND con.contype = 'f'
       AND a.attname = 'updated_on_behalf_of'
  LOOP
    EXECUTE format(
      'ALTER TABLE public.system_requirement_fields DROP CONSTRAINT %I', fk_name);
    RAISE NOTICE 'U20 收斂：已移除 updated_on_behalf_of 的外鍵 %', fk_name;
  END LOOP;

  SELECT count(*) INTO cleared_rows
    FROM public.system_requirement_fields
   WHERE updated_on_behalf_of IS NOT NULL;

  ALTER TABLE public.system_requirement_fields
    ALTER COLUMN updated_on_behalf_of TYPE VARCHAR(64) USING NULL;

  PERFORM set_config('lock_timeout', previous_lock_timeout, true);

  RAISE NOTICE
    'U20 收斂：updated_on_behalf_of 已由 integer 轉為 varchar(64)，清掉的非空舊值 % 筆',
    cleared_rows;
END $$;

COMMENT ON TABLE system_requirement_fields IS
  'U18/BR2.2/[UG:G9]=A — READ THIS BEFORE DELETING ANY ROW HERE. Field definitions (agentGroup -> fieldKey) are constants in CODE, not data (K-17 field_definition_source). When a definition is removed because an agent goes away, three things follow. They are written down here because not writing them down is exactly how these rows get mistaken for dirty data and deleted, and what gets deleted is a value a user once typed: (1) the value rows of the removed definition are RETAINED, never purged; (2) the screen does NOT render that group, so a retained row is invisible in the UI and that is correct rather than a bug; (3) the unfilled count counts only the fields CURRENTLY DECLARED in code, so removing a definition makes the count go DOWN instead of leaving a ghost field. Consequence accepted by ADR-015: the row count only ever grows. Three distinguishable states: never filled = NO ROW; filled = row with value; cleared = row with value NULL and cleared_at set.';
COMMENT ON COLUMN system_requirement_fields.system_id IS
  'U18/[ND1]=A: ON DELETE CASCADE — the requirement-field values of a system are meaningless once the system is gone. This does NOT contradict [UG:G9]=A: that rule is about a FIELD DEFINITION being removed (values retained), not about the system itself being deleted.';
COMMENT ON COLUMN system_requirement_fields.agent_group IS
  'U18/K-17: which agent group this field belongs to. It is part of the uniqueness key BECAUSE the same field_key string under a different agent group is a DIFFERENT field — read_fields returns values grouped by agentGroup. A two-column key (system_id, field_key) would make two groups that share a field name evict each other. entities.md entity_constraints still states the two-column form; the widening here is deliberate (OPEN-ND18-1).';
COMMENT ON COLUMN system_requirement_fields.field_key IS
  'U18/K-17: the field identifier within its agent group. UnknownFieldKey (K-17 raises, AC11.2.2) is decided against the in-code definitions, NOT against the rows of this table — a row may outlive its definition, see the table comment.';
COMMENT ON COLUMN system_requirement_fields.value IS
  'U18/BR1.3/ADR-015: nullable BY DESIGN — it is what makes the three states distinguishable. Tightening it to NOT NULL collapses "never filled" and "cleared" into one state in the data layer, while screen M12 requires telling them apart; the casualty is the audit trail of the clearing action.';
COMMENT ON COLUMN system_requirement_fields.cleared_at IS
  'U18/BR1.4: independent of value, so that the clearing action itself is auditable (who = updated_by, when = this column). Setting value to NULL without recording cleared_at degrades the row to the same meaning as "never filled". ck_system_requirement_fields_cleared_has_null_value enforces the pairing by rejecting a row that has BOTH a value and a cleared_at.';
COMMENT ON COLUMN system_requirement_fields.updated_at IS
  'U18/K-17: when this value was last written or cleared. Part of the shape read_fields returns.';
COMMENT ON COLUMN system_requirement_fields.updated_by IS
  'U18/ADR-015: WHO wrote or cleared this value. NOT NULL on purpose — K-17 clear_field is verbatim "keep the row, set value to null, record clearedAt AND updatedBy", so without this column the "who cleared it" half of that audit simply does not exist.';
COMMENT ON COLUMN system_requirement_fields.updated_on_behalf_of IS
  'U18/BR1.5, retyped by U20/[FD1]=A (BR47.1): the AGENT GROUP identifier (for example ''cost'') the brain wrote this value on behalf of; NULL means the user typed it themselves. It is a group key declared in code (backend/services/requirement_field_definitions.py), NOT a user id, so there is DELIBERATELY NO FOREIGN KEY. The person who actually made the write is always updated_by. Clearing a value always sets this column to NULL (BR45.3). It is a label, not an authorization: any user who may write may set it (BR45.4). Always filling it, or always leaving it empty, removes the user''s ability to tell which values are their own — which is the only reason this column exists (K-15 verbatim).';

-- ###########################################################################
-- K) U9 memory-purge: reserved system actor（NFR7.11）
--    memory_audit_events.actor_user_id 是 NOT NULL REFERENCES public.users (id)，
--    而 90 天保存期的清除是**排程觸發、無人在迴圈內**（FR4.5a）——沒有自然的
--    使用者可填。填記憶擁有者會讓稽核「對誰刪的」說謊（見 I) 區塊該欄的
--    COMMENT 逐字），留 NULL 則 NOT NULL 不允許。故保留一個不是人的 actor。
--
--    **本區塊刻意不在 run_meta_schema_migration.py 的 BLOCKS_TO_RUN 內**：
--    那支腳本的輸出逐字宣告「不塞任何資料」（契約 K-15 的
--    observable_side_effects）。既有環境取得本列的路徑是
--      cd backend && python3 scripts/seed_retention_system_actor.py
--    它 import 同一支腳本的 extract_blocks() 來解析本區塊，所以 SQL 只有這一份。
-- ###########################################################################

-- 四道鎖，全部落在**既有**程式上——本單元不新增任何需要被信任的驗證路徑：
--
--   1. username 含大寫字母。user_router.py 的登入查詢是
--      `.filter(User.username == request.username.lower())`，故**沒有任何輸入**
--      能讓它命中這一列 → 查詢回 None → 401。
--      這一道是刻意加的：verify_password()（auth.py）沒有 try/except，而
--      bcrypt.checkpw 對**非 bcrypt 格式**的 hash 會拋 ValueError（實測
--      `ValueError: Invalid salt`）而不是回 False；若哨符 username 可被命中、
--      而 password_hash 又是非 bcrypt 格式，那就是一個**未經驗證即可遠端觸發
--      的 500**，且 500／401 的差異構成帳號存在性 oracle。
--   2. password_hash 是**格式合法**的 bcrypt hash，其明文為一次性隨機值且未被
--      記錄於任何地方（無已知前像，故它不是憑證、不可反推）。因此
--      bcrypt.checkpw 會乾淨地回 False 而**不拋例外**——即使未來有別的路徑
--      找到這一列，失敗模式也是 401 而不是 500。
--   3. role = 'system' 不在 rbac.py 的 CANONICAL_ROLES 內，故
--      is_canonical_role() 回 False，全部 story × action 權限判定為拒；
--      auth.py 的 require_any_user 的字串 allowlist 同樣不含它。
--   4. is_active = FALSE，故 auth.py 的 `if not user.is_active:` 與
--      user_router.py 登入路徑的同一條檢查都會拒絕。
--
-- **刪掉這一列的後果**（它會出現在 Admin 使用者清單上，可能被誤認為髒資料）：
-- 自那一刻起，清除的稽核 INSERT 全部因 actor_user_id 的外鍵違反而失敗，
-- 而稽核與刪除在同一個交易內，所以**整個清除交易中止**、workflow 非零碼結束。
-- 那是大聲失敗而不是靜默跳過（這是刻意的，見 nfr-design/security-design.md §1.4），
-- 但在它被修好之前，90 天保存期不會前進一列。
--
-- ON CONFLICT (username) DO NOTHING 不是潔癖：本檔是**單一交易**（上方的 BEGIN），
-- 而 ix_users_username 是 UNIQUE。重跑整支檔時若這一行拋 unique violation，
-- 交易會從那一行起全部中止——包含其下方的整個 C) RBAC 區塊。
INSERT INTO users (username, password_hash, role, is_active)
VALUES (
  'SYSTEM.retention-purge',
  '$2b$12$wBoLtWP3GZETdhtbQVoD4eC47g8tHFrxLg8oRk.ISrFgdhA5JB98y',
  'system',
  FALSE
)
ON CONFLICT (username) DO NOTHING;

COMMENT ON TABLE users IS
  'Baseline: application accounts. ONE ROW IS NOT A PERSON: username SYSTEM.retention-purge is the reserved system actor for the 90-day memory retention purge (U9/NFR7.11), required because memory.memory_audit_events.actor_user_id is NOT NULL REFERENCES users(id) while the purge is schedule-triggered with nobody in the loop (FR4.5a). DO NOT DELETE IT: every purge audit INSERT then fails on the foreign key, and because the audit INSERT and the memory DELETE share one transaction, the WHOLE purge aborts and the retention period stops advancing. It cannot log in and holds no permission — four locks, all on pre-existing code: (1) the username contains UPPERCASE and the login query lowercases its input, so no input can ever match the row; (2) password_hash is a VALID bcrypt hash of a one-time random secret that was never recorded, so bcrypt.checkpw returns False CLEANLY instead of raising ValueError (a non-bcrypt sentinel would turn an unauthenticated request into a 500, see nfr-design/security-design.md §1.4); (3) role "system" is not in rbac.py CANONICAL_ROLES, so every permission check denies; (4) is_active is FALSE. Seeded here AND by backend/scripts/seed_retention_system_actor.py, which parses THIS block — the SQL exists only once.';

-- ###########################################################################
-- C) RBAC: role × story permissions (view / edit / review)
-- ###########################################################################

CREATE TABLE IF NOT EXISTS role_permissions (
  role        VARCHAR(64)  NOT NULL,
  story_id    VARCHAR(16)  NOT NULL,
  can_view    BOOLEAN      NOT NULL DEFAULT FALSE,
  can_edit    BOOLEAN      NOT NULL DEFAULT FALSE,
  can_review  BOOLEAN      NOT NULL DEFAULT FALSE,
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_by  VARCHAR(128),
  PRIMARY KEY (role, story_id)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_story
  ON role_permissions (story_id);

COMMENT ON TABLE role_permissions IS
  'RBAC: per-role per-story flags view/edit/review';

DELETE FROM role_permissions;

INSERT INTO role_permissions (role, story_id, can_view, can_edit, can_review) VALUES
  ('Project_Architect', 'A1', true, true, false),
  ('Developer', 'A1', true, true, false),
  ('Project_Editor', 'A1', true, true, false),
  ('Project_Admin', 'A1', true, false, false),
  ('FinOps_Analyst', 'A1', true, false, false),
  ('SRE', 'A1', true, false, false),
  ('Ops_Lead', 'A1', true, false, false),
  ('Platform_Engineer', 'A1', true, false, false),
  ('Security_Reviewer', 'A1', true, false, false),
  ('Platform_Admin', 'A1', true, false, false),
  ('Platform_Owner', 'A1', true, false, false),
  ('Project_Architect', 'A2', true, true, false),
  ('Developer', 'A2', true, true, false),
  ('Project_Editor', 'A2', true, true, false),
  ('Project_Admin', 'A2', true, false, false),
  ('FinOps_Analyst', 'A2', true, false, false),
  ('SRE', 'A2', true, false, false),
  ('Ops_Lead', 'A2', true, false, false),
  ('Platform_Engineer', 'A2', true, false, false),
  ('Security_Reviewer', 'A2', true, false, false),
  ('Platform_Admin', 'A2', true, false, false),
  ('Platform_Owner', 'A2', true, false, false),
  ('Project_Architect', 'A3', true, true, false),
  ('Developer', 'A3', true, false, false),
  ('Project_Editor', 'A3', true, true, false),
  ('Project_Admin', 'A3', true, false, false),
  ('FinOps_Analyst', 'A3', false, false, false),
  ('SRE', 'A3', true, false, false),
  ('Ops_Lead', 'A3', true, false, false),
  ('Platform_Engineer', 'A3', true, false, false),
  ('Security_Reviewer', 'A3', true, true, true),
  ('Platform_Admin', 'A3', true, false, false),
  ('Platform_Owner', 'A3', true, false, false),
  ('Project_Architect', 'A4', true, true, false),
  ('Developer', 'A4', true, true, false),
  ('Project_Editor', 'A4', true, true, false),
  ('Project_Admin', 'A4', true, false, false),
  ('FinOps_Analyst', 'A4', true, false, false),
  ('SRE', 'A4', true, false, false),
  ('Ops_Lead', 'A4', true, false, false),
  ('Platform_Engineer', 'A4', true, false, false),
  ('Security_Reviewer', 'A4', true, false, false),
  ('Platform_Admin', 'A4', true, false, false),
  ('Platform_Owner', 'A4', true, false, false),
  ('Project_Architect', 'B1', true, false, false),
  ('Developer', 'B1', true, false, false),
  ('Project_Editor', 'B1', true, false, false),
  ('Project_Admin', 'B1', true, true, false),
  ('FinOps_Analyst', 'B1', true, true, false),
  ('SRE', 'B1', true, false, false),
  ('Ops_Lead', 'B1', true, false, false),
  ('Platform_Engineer', 'B1', true, false, false),
  ('Security_Reviewer', 'B1', true, false, false),
  ('Platform_Admin', 'B1', true, false, false),
  ('Platform_Owner', 'B1', true, false, false),
  ('Project_Architect', 'B2', true, true, false),
  ('Developer', 'B2', true, false, false),
  ('Project_Editor', 'B2', true, false, false),
  ('Project_Admin', 'B2', true, false, false),
  ('FinOps_Analyst', 'B2', true, false, false),
  ('SRE', 'B2', true, false, false),
  ('Ops_Lead', 'B2', true, true, false),
  ('Platform_Engineer', 'B2', true, false, false),
  ('Security_Reviewer', 'B2', true, false, false),
  ('Platform_Admin', 'B2', true, false, false),
  ('Platform_Owner', 'B2', true, false, false),
  ('Project_Architect', 'B3', true, false, false),
  ('Developer', 'B3', true, false, false),
  ('Project_Editor', 'B3', true, false, false),
  ('Project_Admin', 'B3', true, true, false),
  ('FinOps_Analyst', 'B3', true, false, false),
  ('SRE', 'B3', true, false, false),
  ('Ops_Lead', 'B3', true, false, false),
  ('Platform_Engineer', 'B3', true, false, false),
  ('Security_Reviewer', 'B3', true, true, false),
  ('Platform_Admin', 'B3', true, false, false),
  ('Platform_Owner', 'B3', true, false, false),
  -- C1: 上傳與檢視估價表（FR7.1；U2）。已移除 C1h／C1r／C1o／C1b。
  ('Project_Architect', 'C1', true, true, false),
  ('Developer', 'C1', false, false, false),
  ('Project_Editor', 'C1', true, true, false),
  ('Project_Admin', 'C1', true, true, false),
  ('FinOps_Analyst', 'C1', true, true, false),
  ('SRE', 'C1', true, false, false),
  ('Ops_Lead', 'C1', true, false, false),
  ('Platform_Engineer', 'C1', false, false, false),
  ('Security_Reviewer', 'C1', false, false, false),
  ('Platform_Admin', 'C1', true, true, false),
  ('Platform_Owner', 'C1', true, false, false),
  ('Project_Architect', 'C2', true, false, false),
  ('Developer', 'C2', false, false, false),
  ('Project_Editor', 'C2', true, false, false),
  ('Project_Admin', 'C2', true, false, false),
  ('FinOps_Analyst', 'C2', true, true, false),
  ('SRE', 'C2', true, true, false),
  ('Ops_Lead', 'C2', true, false, false),
  ('Platform_Engineer', 'C2', false, false, false),
  ('Security_Reviewer', 'C2', false, false, false),
  ('Platform_Admin', 'C2', true, false, false),
  ('Platform_Owner', 'C2', true, false, false),
  ('Project_Architect', 'C3', true, true, false),
  ('Developer', 'C3', false, false, false),
  ('Project_Editor', 'C3', true, false, false),
  ('Project_Admin', 'C3', true, false, false),
  ('FinOps_Analyst', 'C3', true, true, false),
  ('SRE', 'C3', true, false, false),
  ('Ops_Lead', 'C3', true, false, false),
  ('Platform_Engineer', 'C3', false, false, false),
  ('Security_Reviewer', 'C3', false, false, false),
  ('Platform_Admin', 'C3', true, false, false),
  ('Platform_Owner', 'C3', true, false, false),
  ('Project_Architect', 'D1', true, true, false),
  ('Developer', 'D1', true, true, false),
  ('Project_Editor', 'D1', true, false, false),
  ('Project_Admin', 'D1', true, false, false),
  ('FinOps_Analyst', 'D1', false, false, false),
  ('SRE', 'D1', true, false, false),
  ('Ops_Lead', 'D1', true, false, false),
  ('Platform_Engineer', 'D1', true, true, false),
  ('Security_Reviewer', 'D1', true, false, false),
  ('Platform_Admin', 'D1', true, false, false),
  ('Platform_Owner', 'D1', true, false, false),
  ('Project_Architect', 'D2', true, false, false),
  ('Developer', 'D2', true, false, false),
  ('Project_Editor', 'D2', true, false, false),
  ('Project_Admin', 'D2', true, false, false),
  ('FinOps_Analyst', 'D2', false, false, false),
  ('SRE', 'D2', true, false, false),
  ('Ops_Lead', 'D2', true, false, false),
  ('Platform_Engineer', 'D2', true, true, false),
  ('Security_Reviewer', 'D2', true, true, false),
  ('Platform_Admin', 'D2', true, false, false),
  ('Platform_Owner', 'D2', true, false, false),
  ('Project_Architect', 'D3', true, false, false),
  ('Developer', 'D3', true, true, false),
  ('Project_Editor', 'D3', true, false, false),
  ('Project_Admin', 'D3', true, false, false),
  ('FinOps_Analyst', 'D3', false, false, false),
  ('SRE', 'D3', true, false, false),
  ('Ops_Lead', 'D3', true, false, false),
  ('Platform_Engineer', 'D3', true, false, false),
  ('Security_Reviewer', 'D3', true, true, false),
  ('Platform_Admin', 'D3', true, false, false),
  ('Platform_Owner', 'D3', true, false, false),
  ('Project_Architect', 'E1', true, false, false),
  ('Developer', 'E1', false, false, false),
  ('Project_Editor', 'E1', true, true, false),
  ('Project_Admin', 'E1', true, false, false),
  ('FinOps_Analyst', 'E1', true, false, false),
  ('SRE', 'E1', true, false, false),
  ('Ops_Lead', 'E1', true, true, false),
  ('Platform_Engineer', 'E1', true, false, false),
  ('Security_Reviewer', 'E1', true, false, false),
  ('Platform_Admin', 'E1', true, false, false),
  ('Platform_Owner', 'E1', true, false, false),
  ('Project_Architect', 'E2', true, true, false),
  ('Developer', 'E2', true, false, false),
  ('Project_Editor', 'E2', true, false, false),
  ('Project_Admin', 'E2', true, true, false),
  ('FinOps_Analyst', 'E2', true, false, false),
  ('SRE', 'E2', true, false, false),
  ('Ops_Lead', 'E2', true, false, false),
  ('Platform_Engineer', 'E2', true, false, false),
  ('Security_Reviewer', 'E2', true, false, false),
  ('Platform_Admin', 'E2', true, false, false),
  ('Platform_Owner', 'E2', true, false, false),
  ('Project_Architect', 'E3', true, false, false),
  ('Developer', 'E3', false, false, false),
  ('Project_Editor', 'E3', true, false, false),
  ('Project_Admin', 'E3', true, false, false),
  ('FinOps_Analyst', 'E3', true, false, false),
  ('SRE', 'E3', true, true, false),
  ('Ops_Lead', 'E3', true, true, false),
  ('Platform_Engineer', 'E3', true, false, false),
  ('Security_Reviewer', 'E3', true, false, false),
  ('Platform_Admin', 'E3', true, false, false),
  ('Platform_Owner', 'E3', true, false, false),
  ('Project_Architect', 'F1', true, false, false),
  ('Developer', 'F1', false, false, false),
  ('Project_Editor', 'F1', true, false, false),
  ('Project_Admin', 'F1', true, false, false),
  ('FinOps_Analyst', 'F1', false, false, false),
  ('SRE', 'F1', true, true, false),
  ('Ops_Lead', 'F1', true, true, false),
  ('Platform_Engineer', 'F1', true, false, false),
  ('Security_Reviewer', 'F1', true, false, false),
  ('Platform_Admin', 'F1', true, false, false),
  ('Platform_Owner', 'F1', true, false, false),
  ('Project_Architect', 'F2', true, false, false),
  ('Developer', 'F2', false, false, false),
  ('Project_Editor', 'F2', true, false, false),
  ('Project_Admin', 'F2', true, false, false),
  ('FinOps_Analyst', 'F2', false, false, false),
  ('SRE', 'F2', true, true, false),
  ('Ops_Lead', 'F2', true, false, false),
  ('Platform_Engineer', 'F2', true, true, false),
  ('Security_Reviewer', 'F2', true, false, false),
  ('Platform_Admin', 'F2', true, false, false),
  ('Platform_Owner', 'F2', true, false, false),
  ('Project_Architect', 'F3', true, false, false),
  ('Developer', 'F3', false, false, false),
  ('Project_Editor', 'F3', false, false, false),
  ('Project_Admin', 'F3', true, false, false),
  ('FinOps_Analyst', 'F3', false, false, false),
  ('SRE', 'F3', true, true, false),
  ('Ops_Lead', 'F3', true, false, false),
  ('Platform_Engineer', 'F3', false, false, false),
  ('Security_Reviewer', 'F3', true, false, true),
  ('Platform_Admin', 'F3', true, false, false),
  ('Platform_Owner', 'F3', true, false, true),
  ('Project_Architect', 'G1', true, false, false),
  ('Developer', 'G1', true, false, false),
  ('Project_Editor', 'G1', true, false, false),
  ('Project_Admin', 'G1', true, false, false),
  ('FinOps_Analyst', 'G1', false, false, false),
  ('SRE', 'G1', true, false, false),
  ('Ops_Lead', 'G1', true, false, false),
  ('Platform_Engineer', 'G1', true, false, false),
  ('Security_Reviewer', 'G1', true, true, true),
  ('Platform_Admin', 'G1', true, false, false),
  ('Platform_Owner', 'G1', true, false, false),
  ('Project_Architect', 'G2', true, false, false),
  ('Developer', 'G2', true, true, false),
  ('Project_Editor', 'G2', true, false, false),
  ('Project_Admin', 'G2', true, false, false),
  ('FinOps_Analyst', 'G2', false, false, false),
  ('SRE', 'G2', true, false, false),
  ('Ops_Lead', 'G2', true, false, false),
  ('Platform_Engineer', 'G2', true, false, false),
  ('Security_Reviewer', 'G2', true, true, true),
  ('Platform_Admin', 'G2', true, false, false),
  ('Platform_Owner', 'G2', true, false, false),
  ('Project_Architect', 'G3', true, false, false),
  ('Developer', 'G3', true, false, false),
  ('Project_Editor', 'G3', true, false, false),
  ('Project_Admin', 'G3', true, false, false),
  ('FinOps_Analyst', 'G3', false, false, false),
  ('SRE', 'G3', true, false, false),
  ('Ops_Lead', 'G3', true, false, false),
  ('Platform_Engineer', 'G3', true, true, false),
  ('Security_Reviewer', 'G3', true, true, true),
  ('Platform_Admin', 'G3', true, false, false),
  ('Platform_Owner', 'G3', true, false, false),
  ('Project_Architect', 'H1', true, false, false),
  ('Developer', 'H1', true, false, false),
  ('Project_Editor', 'H1', true, false, false),
  ('Project_Admin', 'H1', true, false, false),
  ('FinOps_Analyst', 'H1', false, false, false),
  ('SRE', 'H1', true, false, false),
  ('Ops_Lead', 'H1', true, false, false),
  ('Platform_Engineer', 'H1', true, true, false),
  ('Security_Reviewer', 'H1', true, false, false),
  ('Platform_Admin', 'H1', true, true, true),
  ('Platform_Owner', 'H1', true, false, false),
  ('Project_Architect', 'H2', true, false, false),
  ('Developer', 'H2', true, false, false),
  ('Project_Editor', 'H2', true, false, false),
  ('Project_Admin', 'H2', true, false, false),
  ('FinOps_Analyst', 'H2', false, false, false),
  ('SRE', 'H2', true, true, false),
  ('Ops_Lead', 'H2', true, false, false),
  ('Platform_Engineer', 'H2', true, false, false),
  ('Security_Reviewer', 'H2', true, false, false),
  ('Platform_Admin', 'H2', true, true, true),
  ('Platform_Owner', 'H2', true, false, true),
  ('Project_Architect', 'H3', true, false, false),
  ('Developer', 'H3', true, false, false),
  ('Project_Editor', 'H3', true, false, false),
  ('Project_Admin', 'H3', true, false, false),
  ('FinOps_Analyst', 'H3', false, false, false),
  ('SRE', 'H3', true, false, false),
  ('Ops_Lead', 'H3', true, false, false),
  ('Platform_Engineer', 'H3', true, true, false),
  ('Security_Reviewer', 'H3', true, false, false),
  ('Platform_Admin', 'H3', true, true, true),
  ('Platform_Owner', 'H3', true, false, false),
  ('Project_Architect', 'J1', true, true, false),
  ('Developer', 'J1', true, true, false),
  ('Project_Editor', 'J1', true, true, false),
  ('Project_Admin', 'J1', true, true, false),
  ('FinOps_Analyst', 'J1', true, true, false),
  ('SRE', 'J1', true, true, false),
  ('Ops_Lead', 'J1', true, true, false),
  ('Platform_Engineer', 'J1', true, true, false),
  ('Security_Reviewer', 'J1', true, true, false),
  ('Platform_Admin', 'J1', true, true, true),
  ('Platform_Owner', 'J1', true, true, false),
  ('Project_Architect', 'J3a', false, false, false),
  ('Developer', 'J3a', false, false, false),
  ('Project_Editor', 'J3a', false, false, false),
  ('Project_Admin', 'J3a', true, true, true),
  ('FinOps_Analyst', 'J3a', false, false, false),
  ('SRE', 'J3a', false, false, false),
  ('Ops_Lead', 'J3a', false, false, false),
  ('Platform_Engineer', 'J3a', false, false, false),
  ('Security_Reviewer', 'J3a', true, false, false),   -- PU-4：稽核者可檢視使用者管理介面
  ('Platform_Admin', 'J3a', true, true, true),
  ('Platform_Owner', 'J3a', true, false, false),
  ('Project_Architect', 'J3b', false, false, false),
  ('Developer', 'J3b', false, false, false),
  ('Project_Editor', 'J3b', false, false, false),
  ('Project_Admin', 'J3b', true, true, true),
  ('FinOps_Analyst', 'J3b', false, false, false),
  ('SRE', 'J3b', false, false, false),
  ('Ops_Lead', 'J3b', false, false, false),
  ('Platform_Engineer', 'J3b', false, false, false),
  ('Security_Reviewer', 'J3b', false, false, false),
  ('Platform_Admin', 'J3b', true, true, true),
  ('Platform_Owner', 'J3b', true, false, false),
  ('Project_Architect', 'K1', true, false, false),
  ('Developer', 'K1', true, false, false),
  ('Project_Editor', 'K1', true, false, false),
  ('Project_Admin', 'K1', true, false, false),
  ('FinOps_Analyst', 'K1', true, false, false),
  ('SRE', 'K1', false, false, false),
  ('Ops_Lead', 'K1', false, false, false),
  ('Platform_Engineer', 'K1', false, false, false),
  ('Security_Reviewer', 'K1', true, false, false),
  ('Platform_Admin', 'K1', true, false, false),
  ('Platform_Owner', 'K1', true, false, false),
  ('Project_Architect', 'K2', true, true, false),
  ('Developer', 'K2', true, false, false),
  ('Project_Editor', 'K2', true, true, false),
  ('Project_Admin', 'K2', true, true, false),
  ('FinOps_Analyst', 'K2', true, false, false),
  ('SRE', 'K2', true, false, false),
  ('Ops_Lead', 'K2', true, false, false),
  ('Platform_Engineer', 'K2', true, false, false),
  ('Security_Reviewer', 'K2', true, false, false),
  ('Platform_Admin', 'K2', true, true, false),
  ('Platform_Owner', 'K2', true, false, false),
  ('Project_Architect', 'K3', true, true, false),
  ('Developer', 'K3', true, false, false),
  ('Project_Editor', 'K3', true, true, false),
  ('Project_Admin', 'K3', true, true, false),
  ('FinOps_Analyst', 'K3', true, false, false),
  ('SRE', 'K3', false, false, false),
  ('Ops_Lead', 'K3', false, false, false),
  ('Platform_Engineer', 'K3', false, false, false),
  ('Security_Reviewer', 'K3', true, false, false),
  ('Platform_Admin', 'K3', true, true, false),
  ('Platform_Owner', 'K3', true, false, false),
  ('Project_Architect', 'K4', true, true, false),
  ('Developer', 'K4', true, false, false),
  ('Project_Editor', 'K4', true, true, false),
  ('Project_Admin', 'K4', true, true, false),
  ('FinOps_Analyst', 'K4', true, false, false),
  ('SRE', 'K4', false, false, false),
  ('Ops_Lead', 'K4', false, false, false),
  ('Platform_Engineer', 'K4', false, false, false),
  ('Security_Reviewer', 'K4', true, false, false),
  ('Platform_Admin', 'K4', true, true, false),
  ('Platform_Owner', 'K4', true, false, false)
;

COMMIT;

-- 驗證範例：
-- \dt
-- SELECT count(*) FROM role_permissions;           -- 352
-- SELECT username, role FROM users WHERE username = 'admin';
-- SELECT count(*) FROM user_diagrams;
-- SELECT count(*) FROM diagram_shares;
-- SELECT count(*) FROM user_diagram_chats;
-- SELECT count(*) FROM architecture_reviews;
-- -- H) U4 hierarchy-data：
-- \d projects
-- \d systems
-- \d diagram_change_records
-- SELECT column_name, data_type, is_nullable FROM information_schema.columns
--   WHERE table_name = 'user_diagrams' AND column_name = 'system_id';
--   -- 應為：system_id | integer | YES
-- SELECT indexname FROM pg_indexes WHERE tablename IN ('projects', 'systems')
--   AND indexname LIKE 'uq_%';
--   -- 應有兩列：uq_projects_default_per_owner、uq_systems_default_per_project
-- SELECT count(*) FROM user_diagrams WHERE system_id IS NULL;   -- 遷移後應為 0
-- SELECT id, diagram_id, status, overall_score, archived FROM architecture_reviews ORDER BY id DESC LIMIT 5;
-- SELECT id, lens_id, is_active, updated_at FROM wa_lenses ORDER BY id DESC LIMIT 5;
-- -- J) U18 project-meta-data：
-- \d project_members
-- \d reselection_events
-- \d system_requirement_fields
-- SELECT count(*) FROM information_schema.columns
--   WHERE table_schema='public' AND table_name='project_members';          -- 6
-- SELECT count(*) FROM information_schema.columns
--   WHERE table_schema='public' AND table_name='reselection_events';       -- 8
-- SELECT count(*) FROM information_schema.columns
--   WHERE table_schema='public' AND table_name='system_requirement_fields';-- 9
-- SELECT confdeltype FROM pg_constraint WHERE conname='project_members_project_id_fkey';
--   -- 應為 c（CASCADE）
-- SELECT indexname FROM pg_indexes WHERE tablename='project_members'
--   AND indexname='ix_project_members_user_id';
--   -- 應回 1 列（U23；既有環境須重跑 run_meta_schema_migration.py 才會有）
-- SELECT count(*) FROM information_schema.table_constraints tc
--   JOIN information_schema.constraint_column_usage ccu
--     ON ccu.constraint_name = tc.constraint_name
--   WHERE tc.table_name='reselection_events' AND tc.constraint_type='FOREIGN KEY'
--     AND ccu.table_name='projects';
--   -- 應為 0（[ND1]=A：稽核列在專案被刪後独立存活）
-- SELECT indexdef FROM pg_indexes WHERE indexname='ix_reselection_events_unack';
--   -- 應含 WHERE (acknowledged_at IS NULL)（partial；拿掉它只是效能變差不會報錯）
-- SELECT obj_description('system_requirement_fields'::regclass, 'pg_class');
--   -- 應含 [UG:G9]、RETAINED、does NOT render、CURRENTLY DECLARED
