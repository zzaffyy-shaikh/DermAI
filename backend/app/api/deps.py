"""Auth dependencies.

- Primary: `Authorization: Bearer <token>` issued by /auth/login or /auth/register,
  validated against the database.
- Fallback (when DERMAI_AUTH_MODE=dev): trust `X-User-Id` / `X-Role` headers. This
  keeps the lightweight /ui test console and Swagger usable without logging in.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..schemas import Role
from ..services import auth as auth_service


@dataclass
class CurrentUser:
    uid: str
    role: Role
    username: str | None = None
    name: str | None = None
    verified: bool = True


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    # 1) real token auth
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        user = auth_service.get_user_by_token(db, token)
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
        return CurrentUser(uid=user.id, role=Role(user.role), username=user.username,
                           name=user.name, verified=bool(user.verified))

    # 2) dev-header fallback
    if settings.auth_mode == "dev" and x_role:
        role = x_role.lower()
        if role not in {r.value for r in Role}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown role: {role}")
        return CurrentUser(uid=x_user_id or "dev-user", role=Role(role), username=x_user_id or "dev-user")

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


def require_role(*allowed: Role):
    """Dependency factory restricting an endpoint to specific roles."""
    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{user.role.value}' not allowed; requires one of {[r.value for r in allowed]}",
            )
        return user
    return _checker


def require_verified_role(*allowed: Role):
    """Like require_role, but the account must also be verified (doctors / management)."""
    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{user.role.value}' not allowed; requires one of {[r.value for r in allowed]}",
            )
        if not user.verified:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Account pending verification by an administrator.",
            )
        return user
    return _checker
