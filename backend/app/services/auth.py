"""Authentication service: password hashing (stdlib pbkdf2), tokens, registration."""
from __future__ import annotations

import hashlib
import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AuthToken, User

_ITERATIONS = 200_000


def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _ITERATIONS).hex()


def hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16).hex()
    return _hash(password, salt), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    return secrets.compare_digest(_hash(password, salt), password_hash)


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def register_user(db: Session, *, username: str, password: str, role: str,
                  name: str | None = None, email: str | None = None,
                  age: int | None = None, gender: str | None = None,
                  specialization: str | None = None, qualification: str | None = None,
                  graduation: str | None = None, house_job: str | None = None,
                  pmdc_number: str | None = None) -> User:
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("Username and password are required")
    if get_by_username(db, username):
        raise ValueError("Username already taken")

    pwd_hash, salt = hash_password(password)
    # patients are active immediately; doctors AND management await verification
    verified = role == "patient"
    user = User(
        username=username, password_hash=pwd_hash, password_salt=salt, role=role,
        name=name, email=email, age=age, gender=gender,
        specialization=specialization, qualification=qualification,
        graduation=graduation, house_job=house_job, pmdc_number=pmdc_number,
        verified=verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_by_username(db, username)
    if not user or not verify_password(password, user.password_hash, user.password_salt):
        return None
    return user


def create_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthToken(token=token, user_id=user.id))
    db.commit()
    return token


def get_user_by_token(db: Session, token: str) -> User | None:
    at = db.get(AuthToken, token)
    return db.get(User, at.user_id) if at else None


def delete_token(db: Session, token: str) -> None:
    at = db.get(AuthToken, token)
    if at:
        db.delete(at)
        db.commit()


def ensure_admin(db: Session) -> None:
    s = get_settings()
    if not get_by_username(db, s.seed_admin_username):
        admin = register_user(db, username=s.seed_admin_username, password=s.seed_admin_password,
                              role="admin", name="Administrator")
        admin.verified = True   # the seeded super-admin is trusted
        db.commit()
        print(f"[startup] seeded admin account '{s.seed_admin_username}'")
