-- Cloud-360 Database Schema
--
-- 完整部署（含架構圖儲存／分享、A4 聊天、A3 評核、RBAC 預設矩陣、admin 帳號）請執行：
--   psql "$DATABASE_URL" -f schema_rbac.sql
--
-- 本檔保留為精簡核心 DDL 參考；與 schema_rbac.sql 的 A/B／E 段對齊。

CREATE TABLE IF NOT EXISTS users (
	id SERIAL NOT NULL,
	username VARCHAR NOT NULL,
	password_hash VARCHAR NOT NULL,
	role VARCHAR NOT NULL,
	is_active BOOLEAN,
	last_opened_diagram_id INTEGER,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS user_diagrams (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	title VARCHAR NOT NULL,
	xml_data TEXT NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_last_opened_diagram'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT fk_users_last_opened_diagram
      FOREIGN KEY (last_opened_diagram_id) REFERENCES user_diagrams (id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS diagram_shares (
	user_id INTEGER NOT NULL,
	diagram_id INTEGER NOT NULL,
	PRIMARY KEY (user_id, diagram_id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(diagram_id) REFERENCES user_diagrams (id)
);

CREATE TABLE IF NOT EXISTS user_diagram_chats (
	user_id INTEGER NOT NULL,
	diagram_id INTEGER NOT NULL,
	messages_json TEXT NOT NULL DEFAULT '[]',
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	PRIMARY KEY (user_id, diagram_id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(diagram_id) REFERENCES user_diagrams (id) ON DELETE CASCADE
);

-- A3: Well-Architected reviews（完整定義與索引見 schema_rbac.sql 區塊 E）
CREATE TABLE IF NOT EXISTS architecture_reviews (
	id SERIAL NOT NULL,
	diagram_id INTEGER NOT NULL,
	created_by INTEGER NOT NULL,
	provider VARCHAR(16) NOT NULL DEFAULT 'aws',
	status VARCHAR(32) NOT NULL DEFAULT 'pending',
	overall_score INTEGER,
	scores_json TEXT,
	findings_json TEXT DEFAULT '[]',
	suggestions_text TEXT,
	error_message TEXT,
	rule_pack_version VARCHAR(64),
	archived BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(diagram_id) REFERENCES user_diagrams (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id)
);

-- H) U4 專案／系統階層（完整定義、部分唯一索引與 COMMENT 見 schema_rbac.sql 區塊 H）
--    既有環境的演進路徑不是本檔也不是 schema_rbac.sql，而是一次性遷移指令：
--      cd backend && python scripts/run_hierarchy_migration.py
--    見 DEPLOY.md 第 2.2.7 節（含靜止前置條件與回復程序）。
CREATE TABLE IF NOT EXISTS projects (
	id SERIAL NOT NULL,
	name VARCHAR(255) NOT NULL,
	owner_user_id INTEGER NOT NULL,
	is_default BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(owner_user_id) REFERENCES users (id),
	CONSTRAINT ck_projects_name_not_blank CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS systems (
	id SERIAL NOT NULL,
	project_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	is_default BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE RESTRICT,
	CONSTRAINT ck_systems_name_not_blank CHECK (length(trim(name)) > 0)
);

-- BR1.3 的兩個部分唯一索引：各自只引用自己表內的欄位。
-- **少了它們，BR2.2 的冪等就不成立**——重跑會安靜地建出第二組預設專案／系統，
-- 而那正是 BR2.2 的 violation_behaviour 描述的「一個看起來成功的錯誤結果」。
-- 本段為 iteration 1 審查 R-01／R-04 補入：初版只建表不建索引，使這支 SQL 自己
-- 就能造出「表在、唯一索引不在」的狀態，而遷移模組的 create_all(checkfirst=True)
-- 是表層級判定、跳過整張表時連索引一起跳過，偵測不到也補不上。
-- 遷移模組現已在 create_all 之後逐一補建這三個索引，兩邊因此一致。
CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_default_per_owner
	ON projects (owner_user_id) WHERE is_default;

CREATE UNIQUE INDEX IF NOT EXISTS uq_systems_default_per_project
	ON systems (project_id) WHERE is_default;

-- 架構圖歸屬的權威來源（可為空；user_id 只回答「誰建的」）
ALTER TABLE user_diagrams ADD COLUMN IF NOT EXISTS system_id INTEGER;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_diagrams_system'
  ) THEN
    ALTER TABLE user_diagrams
      ADD CONSTRAINT fk_user_diagrams_system
      FOREIGN KEY (system_id) REFERENCES systems (id) ON DELETE RESTRICT;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS diagram_change_records (
	id SERIAL NOT NULL,
	diagram_id INTEGER NOT NULL,
	source VARCHAR(32) NOT NULL,
	actor_user_id INTEGER NOT NULL,
	requirement_summary TEXT NOT NULL,
	requirement_label VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(diagram_id) REFERENCES user_diagrams (id) ON DELETE CASCADE,
	FOREIGN KEY(actor_user_id) REFERENCES users (id),
	CONSTRAINT ck_diagram_change_records_source
		CHECK (source IN ('brain_orchestration')),
	CONSTRAINT ck_diagram_change_records_summary_not_blank
		CHECK (length(trim(requirement_summary)) > 0)
);

-- U4-R1：90 天保存期的截止欄位是 created_at，而清除查詢若無索引即全表掃描——
-- 這張表只寫不讀，沒有任何讀取端會順手建立它。同為 iteration 1 審查 R-04 補入。
CREATE INDEX IF NOT EXISTS ix_diagram_change_records_created_at
	ON diagram_change_records (created_at);

CREATE INDEX IF NOT EXISTS ix_diagram_change_records_diagram_id
	ON diagram_change_records (diagram_id);

-- RBAC 表與 seed、預設 admin：見 schema_rbac.sql
