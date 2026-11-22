"""Shared test helpers: path setup, psycopg mock, in-memory SQLite session."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# 驅動由 DATABASE_URL 的 `postgresql+psycopg://` 顯式指定，故要處理的是 `psycopg`
# （v3，import 名為 `psycopg`；與第二代的 `psycopg2` 是兩個不同套件）。
#
# **只在真的沒裝時才 stub。** 無條件 `setdefault` 會在有裝驅動的環境把真模組遮掉，
# 而 SQLAlchemy 的 psycopg dialect 在建構時會 `from psycopg.adapt import AdaptersMap`
# ——MagicMock 不是 package，滿足不了子模組 import，於是 create_engine 直接炸。
# 這是本次遷移實跑時抓到的（21 個 error），不是推論。
if importlib.util.find_spec("psycopg") is None:  # pragma: no cover - 取決於環境
    _psycopg_stub = MagicMock()
    # dialect 建構時會對 `psycopg.__version__` 跑 re.match 取版號；MagicMock 對
    # dunder 名一律丟 AttributeError，不給它就是 21 個 loader error。
    _psycopg_stub.__version__ = "3.2.0"
    sys.modules.setdefault("psycopg", _psycopg_stub)
    # dialect 建構時會走到的子模組，需一併登錄才不會在 import 階段失敗。
    for _sub in ("adapt", "pq", "types", "rows"):
        sys.modules.setdefault(f"psycopg.{_sub}", getattr(_psycopg_stub, _sub))

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(backend_dir / "services") not in sys.path:
    sys.path.insert(0, str(backend_dir / "services"))

from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from models import Base, User, UserDiagram
from services.rbac import ensure_role_permissions_seeded


def make_session(*, threaded: bool = False) -> Session:
    # StaticPool：所有連線共用同一個 in-memory 資料庫。預設的 SingletonThreadPool
    # 會讓每個執行緒拿到各自的空資料庫，而 TestClient 在另一個執行緒裡跑 app，
    # 沒有 StaticPool 時端點測試會看到 "no such table"。
    #
    # threaded=True：改用暫存檔資料庫，每個連線各自一條 sqlite3 連線。StaticPool 的單一連線
    # 被兩個執行緒同時使用時會丟 InterfaceError（大腦閘道的定期重驗與收訊重驗都以
    # `asyncio.to_thread` 開 session，兩者可能同時查 DB），造成機率性失敗；檔案資料庫由
    # SQLite 自己的鎖序列化，沒有這個問題。
    tmpdir = None
    if threaded:
        tmpdir = tempfile.mkdtemp(prefix="cloud360-test-db-")
        engine = create_engine(
            f"sqlite:///{os.path.join(tmpdir, 'test.db')}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        # models.py 的全域 connect listener 對每條連線 ATTACH ':memory:' AS memory——在多連線下
        # 那是每條連線各一份空庫。改附加同目錄的檔案庫，讓 `memory.*` 兩張表跨連線共用。
        memory_path = os.path.join(tmpdir, "memory.db")

        @event.listens_for(engine, "connect")
        def _shared_memory_schema(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            try:
                try:
                    cursor.execute("DETACH DATABASE memory")
                except Exception:
                    pass  # 本 listener 先於全域 listener 執行時，memory 尚未附加
                cursor.execute(f"ATTACH DATABASE '{memory_path}' AS memory")
            finally:
                cursor.close()
    else:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    ensure_role_permissions_seeded(db, force=True)
    # Keep engine on session for tearDown drop_all
    db._test_engine = engine  # type: ignore[attr-defined]
    db._test_tmpdir = tmpdir  # type: ignore[attr-defined]
    return db


def close_session(db: Session) -> None:
    engine = getattr(db, "_test_engine", None)
    tmpdir = getattr(db, "_test_tmpdir", None)
    db.close()
    if engine is not None:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
    if tmpdir:
        shutil.rmtree(tmpdir, ignore_errors=True)


def make_user(
    db: Session,
    *,
    username: str,
    role: str | None,
    password_hash: str = "unused",
    is_active: bool = True,
    authorization_status: str = "approved",
) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
        authorization_status=authorization_status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_diagram(
    db: Session,
    *,
    owner: User,
    title: str = "test",
    xml_data: str = "<mxGraphModel/>",
) -> UserDiagram:
    diagram = UserDiagram(user_id=owner.id, title=title, xml_data=xml_data)
    db.add(diagram)
    db.commit()
    db.refresh(diagram)
    return diagram


def ALWAYS_VISIBLE(_project_id: int) -> bool:  # noqa: N802 - 以常數語意命名
    """`U23`：`HierarchyFacade` 三條寫入路徑的 `project_visible` 測試替身，恆為真。

    **只供「驗擁有者檢查等其他行為」的既有測試補參數用**——它們在 `U23` 之前
    沒有可見性守門，補上恆真的判定使語意與修改前完全相同。
    要驗守門本身的測試（`test_project_write_guard.py`）走 HTTP、由 router 注入
    真實判定，不用本替身。

    非測試程式**不得**傳這個形狀：`tests/test_project_visibility_static.py` 的第 3 條
    斷言每個非 service 層的寫入呼叫都帶 `project_visible=<…>.project_visibility(...)`。
    """
    return True
