"""Shared test helpers: path setup, psycopg mock, in-memory SQLite session."""

from __future__ import annotations

import importlib.util
import sys
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

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from models import Base, User, UserDiagram
from services.rbac import ensure_role_permissions_seeded


def make_session() -> Session:
    # StaticPool：所有連線共用同一個 in-memory 資料庫。預設的 SingletonThreadPool
    # 會讓每個執行緒拿到各自的空資料庫，而 TestClient 在另一個執行緒裡跑 app，
    # 沒有 StaticPool 時端點測試會看到 "no such table"。
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
    return db


def close_session(db: Session) -> None:
    engine = getattr(db, "_test_engine", None)
    db.close()
    if engine is not None:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


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
