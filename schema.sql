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

-- RBAC 表與 seed、預設 admin：見 schema_rbac.sql
