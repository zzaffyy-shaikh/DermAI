"""Account creation, login, logout, and current-user lookup."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import BACKEND_DIR, Settings, get_settings
from ..db import get_db
from ..models import User
from ..schemas import (AuthResponse, GoogleAuthRequest, LoginRequest,
                       RegisterRequest, Role, UserPublic)
from ..services import auth as auth_service
from .deps import CurrentUser, get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["auth"])


def _public(u: User) -> UserPublic:
    return UserPublic(uid=u.id, username=u.username, role=u.role,
                      name=u.name, email=u.email, verified=u.verified)


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if body.role not in ("patient", "doctor", "admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role")
    try:
        user = auth_service.register_user(
            db, username=body.username, password=body.password, role=body.role,
            name=body.name, email=body.email, age=body.age, gender=body.gender,
            specialization=body.specialization, qualification=body.qualification,
            graduation=body.graduation, house_job=body.house_job, pmdc_number=body.pmdc_number,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    token = auth_service.create_token(db, user)
    return AuthResponse(token=token, user=_public(user))


@router.post("/license")
def upload_license(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> dict:
    """A (pending) doctor uploads their license/registration image for review."""
    lic_dir = BACKEND_DIR / "licenses"
    lic_dir.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "img").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp", "pdf"):
        ext = "jpg"
    path = lic_dir / f"{user.uid}.{ext}"
    with open(path, "wb") as fh:
        fh.write(file.file.read())
    db_user = db.get(User, user.uid)
    db_user.license_path = str(path)
    db.commit()
    return {"ok": True}


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = auth_service.authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    token = auth_service.create_token(db, user)
    return AuthResponse(token=token, user=_public(user))


@router.get("/google-config")
def google_config(settings: Settings = Depends(get_settings)) -> dict:
    """Expose the Google client id so the frontend can render the Google button."""
    return {"client_id": settings.google_client_id or ""}


@router.post("/google", response_model=AuthResponse)
def google_login(
    body: GoogleAuthRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    allowed = {c for c in (settings.google_client_id, settings.google_android_client_id) if c}
    if not allowed:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Google sign-in not configured")
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
        # verify signature/issuer/expiry, then check audience against our client ids
        info = google_id_token.verify_oauth2_token(body.credential, google_requests.Request())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid Google token: {exc}") from exc
    if info.get("aud") not in allowed:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google token audience mismatch")

    email = info.get("email")
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google account has no email")

    user = auth_service.get_by_username(db, email)
    if not user:
        # new Google user -> create a patient with an unguessable random password
        user = auth_service.register_user(
            db, username=email, password=secrets.token_urlsafe(24),
            role="patient", name=info.get("name"), email=email)
    token = auth_service.create_token(db, user)
    return AuthResponse(token=token, user=_public(user))


@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> UserPublic:
    db_user = db.get(User, user.uid)
    if db_user:
        return _public(db_user)
    return UserPublic(uid=user.uid, username=user.username or user.uid, role=user.role.value, name=user.name)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    if authorization and authorization.lower().startswith("bearer "):
        auth_service.delete_token(db, authorization.split(" ", 1)[1])
    return {"ok": True}
