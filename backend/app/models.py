"""ORM models: users (credentials + patient/doctor profile) and auth tokens."""
import datetime
import uuid
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    password_salt: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)            # patient | doctor | admin

    # shared profile
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # patient profile
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # doctor / management profile + verification
    specialization: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String, nullable=True)      # e.g. MBBS, FCPS
    graduation: Mapped[Optional[str]] = mapped_column(String, nullable=True)         # institute / year
    house_job: Mapped[Optional[str]] = mapped_column(String, nullable=True)          # internship details
    pmdc_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)        # PMDC registration no.
    license_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)       # uploaded license image
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # patient medical history (filled once, reused for every diagnosis)
    medical_history: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    history_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
