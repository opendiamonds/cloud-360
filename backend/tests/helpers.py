"""Shared test helpers: path setup, psycopg2 mock, in-memory SQLite session."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock psycopg2 before any database import (CI / hosts without the driver).
sys.modules.setdefault("psycopg2", MagicMock())

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
