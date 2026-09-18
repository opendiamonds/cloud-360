import os
import logging
import bcrypt
from env_bootstrap import load_backend_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User

logger = logging.getLogger("cloud360.database")

# 自動判斷環境：如果有設定 APP_ENV，或是預設為 local，就去抓對應的 .env 檔案
app_env = os.environ.get("APP_ENV", "local")
if app_env == "local":
    # 這裡確保只在 local 開發時強制讀取 .env
    # 部署到正式環境 (如 production) 時，通常由平台 (AWS/Vercel) 直接注入環境變數
    # 路徑必須是明確的 backend/.env：這行比 main.py 的載入更早執行（main 在
    # 匯入本模組時就會觸發），所以它決定了整個 process 第一次看到的 .env 是哪
    # 一份。留著無參數的 load_dotenv() 會讓 main 那邊的修正完全失效。
    load_backend_dotenv()

# Database configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cloud360"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

LOCAL_APP_ENVS = {"local", "test", "ci"}


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _current_app_env() -> str:
    return os.environ.get("APP_ENV", app_env).strip().lower()


def _allow_insecure_default_users() -> bool:
    """Fixed demo credentials are only acceptable in local/test, or by opt-in."""
    if _current_app_env() in LOCAL_APP_ENVS:
        return True
    return _truthy_env("ALLOW_INSECURE_DEFAULT_USERS")


def _allow_insecure_default_personas() -> bool:
    """Seed the multi-persona demo catalog only where it is intentionally useful."""
    if _current_app_env() == "local":
        return True
    return _truthy_env("ALLOW_INSECURE_DEFAULT_PERSONAS")


def _bootstrap_admin_password() -> str | None:
    password = os.environ.get("CLOUD360_BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    if password:
        return password
    if _allow_insecure_default_users():
        return "admin123"
    return None

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    logger.info("正在初始化資料庫與資料表...")
    Base.metadata.create_all(bind=engine)
    # A4／J5：既有 DB 補欄位／新表（create_all 不會 ALTER 舊表）
    _ensure_a4_schema()
    _ensure_j5_schema()
    _ensure_a3_schema()
    _ensure_last_activity_schema()

    db = SessionLocal()
    try:
        # 檢查是否已存在使用者
        user_count = db.query(User).count()
        if user_count == 0 and _allow_insecure_default_personas():
            logger.info("資料庫為空，開始從 personas.md 初始化 11 位預設使用者...")

            default_personas = [
                {"username": "catherine", "role": "Project_Admin", "password": "catherine123"},
                {"username": "jack", "role": "Platform_Admin", "password": "jack123"},
                {"username": "alex", "role": "Project_Architect", "password": "alex123"},
                {"username": "ben", "role": "SRE", "password": "ben123"},
                {"username": "david", "role": "FinOps_Analyst", "password": "david123"},
                {"username": "elena", "role": "Platform_Engineer", "password": "elena123"},
                {"username": "fiona", "role": "Security_Reviewer", "password": "fiona123"},
                {"username": "george", "role": "Ops_Lead", "password": "george123"},
                {"username": "hannah", "role": "Project_Editor", "password": "hannah123"},
                {"username": "ian", "role": "Developer", "password": "ian123"},
                {"username": "karen", "role": "Platform_Owner", "password": "karen123"},
            ]

            for persona in default_personas:
                hashed_pw = hash_password(persona["password"])
                db_user = User(
                    username=persona["username"],
                    password_hash=hashed_pw,
                    role=persona["role"],
                    is_active=True,
                    authorization_status="approved",
                )
                db.add(db_user)

            db.commit()
            logger.info("預設使用者初始化完成！")
        elif user_count == 0:
            logger.warning(
                "資料庫為空，但 APP_ENV=%s 未允許 demo persona seed；略過 persona 建立。",
                _current_app_env(),
            )
        else:
            logger.info(f"資料庫已存在 {user_count} 位使用者，跳過初始化。")

        # 確保預設 admin 帳號存在（與 schema_rbac.sql 對齊）
        admin = db.query(User).filter(User.username == "admin").first()
        bootstrap_admin_password = _bootstrap_admin_password()
        if admin is None:
            if bootstrap_admin_password:
                db.add(
                    User(
                        username="admin",
                        password_hash=hash_password(bootstrap_admin_password),
                        role="Platform_Admin",
                        is_active=True,
                        authorization_status="approved",
                    )
                )
                db.commit()
                logger.info("已建立 bootstrap admin / Platform_Admin")
            else:
                logger.warning(
                    "未設定 CLOUD360_BOOTSTRAP_ADMIN_PASSWORD；APP_ENV=%s 不建立固定密碼 admin。",
                    _current_app_env(),
                )
        elif bootstrap_admin_password and getattr(admin, "authorization_status", None) != "approved":
            admin.authorization_status = "approved"
            if not admin.role:
                admin.role = "Platform_Admin"
            db.commit()

        # RBAC 矩陣：空表時 seed（不覆寫 Admin UI 已調過的資料）
        from services.rbac import ensure_role_permissions_seeded

        seeded = ensure_role_permissions_seeded(db, force=False)
        if seeded:
            logger.info("role_permissions 已 seed %d 列", seeded)
        else:
            from models import RolePermission

            logger.info(
                "role_permissions 已有 %d 列，略過 seed",
                db.query(RolePermission).count(),
            )

        # PU-4：既有環境的目標式權限套用。**必須在 seed 之後**——種子函式只在空表
        # 寫入，既有環境不會經過它，改了預設值也不會生效（requirements C-3 另禁止
        # 以重跑整份初始化腳本作為套用手段）。
        _apply_security_reviewer_j3a_view(db)
    except Exception as e:
        logger.error(f"初始化資料庫時發生錯誤: {e}")
        db.rollback()
    finally:
        db.close()


def _ensure_a4_schema():
    """為既有資料庫補上 A4 欄位與 user_diagram_chats 表。"""
    from sqlalchemy import text

    statements = [
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS last_opened_diagram_id INTEGER
        """,
        """
        CREATE TABLE IF NOT EXISTS user_diagram_chats (
            user_id INTEGER NOT NULL REFERENCES users(id),
            diagram_id INTEGER NOT NULL REFERENCES user_diagrams(id) ON DELETE CASCADE,
            messages_json TEXT NOT NULL DEFAULT '[]',
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (user_id, diagram_id)
        )
        """,
    ]
    with engine.begin() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning("A4 schema 補丁略過/失敗: %s — %s", sql[:60], e)
    logger.info("A4 schema 檢查完成")


def _ensure_j5_schema():
    """為既有資料庫補上 J5 authorization_status 與 role_authorization_requests。"""
    from sqlalchemy import text

    statements = [
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS authorization_status VARCHAR(32) DEFAULT 'approved'
        """,
        """
        UPDATE users SET authorization_status = 'approved'
        WHERE authorization_status IS NULL OR authorization_status = ''
        """,
        """
        ALTER TABLE users ALTER COLUMN role DROP NOT NULL
        """,
        """
        CREATE TABLE IF NOT EXISTS role_authorization_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            requested_role VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            decided_by VARCHAR(128),
            decided_at TIMESTAMP WITH TIME ZONE,
            note TEXT
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_role_auth_req_user_id
        ON role_authorization_requests (user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_role_auth_req_status
        ON role_authorization_requests (status)
        """,
    ]
    with engine.begin() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning("J5 schema 補丁略過/失敗: %s — %s", sql[:60], e)
    logger.info("J5 schema 檢查完成")


def _ensure_a3_schema():
    """為既有資料庫補上 architecture_reviews／wa_lenses（A3）。"""
    from sqlalchemy import text

    statements = [
        """
        CREATE TABLE IF NOT EXISTS architecture_reviews (
            id SERIAL PRIMARY KEY,
            diagram_id INTEGER NOT NULL REFERENCES user_diagrams(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(id),
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
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_architecture_reviews_diagram_id
        ON architecture_reviews (diagram_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_architecture_reviews_created_by
        ON architecture_reviews (created_by)
        """,
        """
        CREATE TABLE IF NOT EXISTS wa_lenses (
            id SERIAL PRIMARY KEY,
            lens_id VARCHAR(64) NOT NULL DEFAULT 'cloud360-core-mvp',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            body_json TEXT NOT NULL,
            updated_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_wa_lenses_lens_id ON wa_lenses (lens_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_wa_lenses_is_active ON wa_lenses (is_active)
        """,
        """
        ALTER TABLE architecture_reviews ALTER COLUMN diagram_id DROP NOT NULL
        """,
        """
        ALTER TABLE architecture_reviews ADD COLUMN IF NOT EXISTS xml_snapshot TEXT
        """,
        """
        ALTER TABLE wa_lenses ADD COLUMN IF NOT EXISTS provider VARCHAR(16) NOT NULL DEFAULT 'aws'
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_wa_lenses_provider ON wa_lenses (provider)
        """,
    ]
    with engine.begin() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning("A3 schema 補丁略過/失敗: %s — %s", sql[:60], e)
    logger.info("A3 schema 檢查完成")

def _ensure_last_activity_schema():
    """為既有資料庫補上 users.last_activity_at（PU-1／C-3）。

    `create_all` 不會 ALTER 既有表，因此新欄位在既有環境需要這支補丁。
    **不補則 staging 上每個已認證的請求都會失敗，而 CI 全綠** —— 測試以
    in-memory SQLite 直接建表、從不經過本流程。
    """
    from sqlalchemy import text

    statements = [
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE
        """,
    ]
    with engine.begin() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning(
                    "last_activity schema 補丁略過/失敗: %s — %s", sql[:60], e
                )
    logger.info("last_activity schema 檢查完成")


# 本補丁的識別字。與使用者帳號共用同一個欄位，而帳號無格式約束，故理論上可能
# 撞名；以帶點號的形式降低碰撞機率（帳號正規化只做去空白與轉小寫，不會產生點號
# 以外的區隔，但實務上不會有人取這個名字）。
J3A_PATCH_MARKER = "system_patch.j3a_view"


def _apply_security_reviewer_j3a_view(db) -> None:
    """開通 Security_Reviewer 對 J3a 的檢視權限（PU-4／C-7）。

    契約（缺一不可）：

    1. **只更新、不插入** —— 目標列不存在時記錄「未命中目標列」並結束。插入會在
       空表情境下建立孤兒列，而後續的 seed 會因表非空而整份跳過，導致 308 列預設
       矩陣不被建立、全系統 RBAC 端點盡數拒絕存取，且沒有任何測試會發現。
    2. **條件式套用** —— 僅在該列仍為系統種子所寫（`updated_by == "system_seed"`）
       時才翻轉，避免覆蓋管理者在 Admin UI 上的人工調整。
    3. **自行管理交易** —— 沿用既有 `_ensure_*` 的提交慣例；不提交則寫入被靜默丟棄
       而日誌仍報「已套用」，與「無自動化驗證」疊加成雙重靜默。
    4. **四態日誌**（承 U4 的 business-rules R4，該站把上游的三態拆為四態）——
       已套用／已跳過（無需動作）／**未套用：該列已被管理員異動**／**未命中目標
       列**。**後兩態同級，皆為 warning、皆需人工處置** —— R2 的死角恰好落在
       「已被管理員異動」，若把它併進常態的「已跳過」，這個唯一的執行期訊號就
       正好在最該照亮的地方關掉。部署後人工核對是本變更唯一的驗證方式。
    """
    from models import RolePermission

    try:
        row = (
            db.query(RolePermission)
            .filter(
                RolePermission.role == "Security_Reviewer",
                RolePermission.story_id == "J3a",
            )
            .first()
        )
        if row is None:
            logger.warning(
                "J3a 權限套用：未命中目標列（Security_Reviewer/J3a 不存在），不插入"
            )
            return
        if row.can_view:
            logger.info("J3a 權限套用：已跳過（Security_Reviewer/J3a 已為可檢視）")
            return
        # 「尚未被人工調整」有**兩種**合法形態，缺一會讓套用在真實環境失靜默失敗：
        #   - `system_seed`：由 ensure_role_permissions_seeded() 寫入（空表 seed）
        #   - NULL／空字串：由 schema_rbac.sql 的 INSERT 寫入（該 INSERT 不含此欄）
        # Admin UI 的人工調整會把它設成該管理者的 username（user_router.py:834/841），
        # 只有那種情況才不覆寫。實測：以 schema_rbac.sql 建立的資料庫，本欄全為 NULL。
        seeded_markers = {"", "system_seed", J3A_PATCH_MARKER}
        if (row.updated_by or "") not in seeded_markers:
            # 第三態。**與「未命中目標列」同級（warning，需人工處置）**，不是
            # 常態跳過：管理者可能是刻意撤銷（應予尊重），也可能是本元件該做而
            # 做不成。把該欄實際值帶進日誌供部署後判讀。
            logger.warning(
                "J3a 權限套用：未套用 —— 該列已被管理員異動（最後異動者=%r），"
                "需人工核對是刻意撤銷還是套用失敗",
                row.updated_by,
            )
            return
        row.can_view = True
        # 寫入本補丁的識別字：讓第二次以後的啟動落在「已跳過（無需動作）」而非
        # 被誤判為管理員異動，也讓部署後的人工核對看得出這一列是誰改的。
        row.updated_by = J3A_PATCH_MARKER
        db.commit()
        logger.info("J3a 權限套用：已套用（Security_Reviewer 取得 J3a 檢視權限）")
    except Exception as e:
        db.rollback()
        logger.error("J3a 權限套用失敗，已復原：%s", e)
