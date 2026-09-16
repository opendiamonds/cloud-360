import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import bcrypt
from sqlalchemy.orm import Session
from database import get_db
from models import User
from services.activity import record_activity

# Security Configurations
INSECURE_DEV_SECRET = "cloud360_secret_key_change_me_in_production"
LOCAL_APP_ENVS = {"local", "test", "ci"}


def _env_allows_insecure_defaults() -> bool:
    return os.environ.get("APP_ENV", "local").strip().lower() in LOCAL_APP_ENVS


def _resolve_secret_key() -> str:
    secret = os.environ.get("JWT_SECRET", "").strip()
    if secret:
        return secret
    if _env_allows_insecure_defaults():
        return INSECURE_DEV_SECRET
    raise RuntimeError("JWT_SECRET is required outside local/test environments")


SECRET_KEY = _resolve_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 預設 8 小時

security_bearer = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_from_token(token: str, db: Session, *, record: bool = True) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="身分驗證失敗，憑證無效或已過期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="該帳號已被停用"
        )
    if record:
        # PU-1：任何以有效憑證發出的請求都更新該帳號的最後活動時間（節流見 C-1）。
        # record_activity 自行管理交易並吞掉自身的失敗——記錄失敗不得讓使用者請求失敗。
        record_activity(db, user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    return get_user_from_token(credentials.credentials, db)

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"權限不足：此操作需要角色類型 {self.allowed_roles}，但您的身分為 {current_user.role}"
            )
        return current_user

# 快捷權限防護 Guard（角色 allowlist；細項請用 services.rbac.require_story_action）
require_admin = RoleChecker(["Project_Admin", "Platform_Admin"])
require_architect = RoleChecker(["Project_Admin", "Platform_Admin", "Project_Architect"])
require_any_user = RoleChecker([
    "Project_Admin", "Platform_Admin", "Project_Architect",
    "SRE", "FinOps_Analyst", "Platform_Engineer",
    "Security_Reviewer", "Ops_Lead", "Project_Editor", "Developer", "Platform_Owner",
])
