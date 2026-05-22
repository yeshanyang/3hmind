"""
3hmind 用户认证模块 — JWT + 本地用户存储
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _load_users() -> dict:
    path = settings.users_file
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict):
    os.makedirs(os.path.dirname(settings.users_file), exist_ok=True)
    tmp = settings.users_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    os.replace(tmp, settings.users_file)


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hash: str) -> bool:
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.jwt_expire_days)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_user(username: str, password: str) -> tuple:
    """返回 (success: bool, message: str)"""
    username = username.strip().lower()
    if not username or len(username) < 2:
        return False, "用户名至少 2 个字符"
    if len(password) < 4:
        return False, "密码至少 4 个字符"
    users = _load_users()
    if username in users:
        return False, "用户名已存在"
    users[username] = {
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow().isoformat()
    }
    _save_users(users)
    return True, "注册成功"


def verify_user(username: str, password: str) -> str | None:
    """验证成功返回 token，失败返回 None"""
    username = username.strip().lower()
    users = _load_users()
    user = users.get(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return create_access_token(username)


def seed_default_admin():
    """首次启动：如果 DEFAULT_ADMIN_PASSWORD 已设置且无用户，创建 admin 账号"""
    if not settings.default_admin_password:
        return
    path = settings.users_file
    if os.path.exists(path):
        return
    print("[Auth] 首次启动，正在创建默认 admin 用户...")
    success, msg = create_user("admin", settings.default_admin_password)
    if success:
        print("[Auth] admin 用户创建成功")
    else:
        print(f"[Auth] admin 创建失败: {msg}")


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """FastAPI 依赖：从 Authorization Bearer 头解析 user_id"""
    if creds is None:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token 无效")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")


def list_users() -> list[str]:
    """列出所有注册用户（供 scheduler 使用）"""
    return list(_load_users().keys())
