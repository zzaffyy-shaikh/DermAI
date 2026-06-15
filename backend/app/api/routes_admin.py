"""Management (admin) panel: verification queue for doctors & management, with
their credentials + license, plus system stats. All endpoints require a *verified*
admin (management accounts must themselves be approved by another admin)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuthToken, User
from ..schemas import DoctorVerifyRequest, Role
from ..services.consult import consult_store
from ..services.sessions import session_store
from .deps import CurrentUser, require_verified_role

router = APIRouter(prefix="/admin", tags=["admin"])


def _count(db: Session, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0


def _doctor_dict(d: User) -> dict:
    return {
        "uid": d.id, "username": d.username, "name": d.name, "email": d.email,
        "specialization": d.specialization, "qualification": d.qualification,
        "graduation": d.graduation, "house_job": d.house_job, "pmdc_number": d.pmdc_number,
        "has_license": bool(d.license_path), "verified": d.verified,
    }


def _admin_dict(a: User) -> dict:
    return {"uid": a.id, "username": a.username, "name": a.name, "email": a.email, "verified": a.verified}


@router.get("/stats")
async def stats(
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "patients": _count(db, User.role == "patient"),
        "doctors": _count(db, User.role == "doctor"),
        "doctors_pending": _count(db, User.role == "doctor", User.verified.is_(False)),
        "management": _count(db, User.role == "admin"),
        "management_pending": _count(db, User.role == "admin", User.verified.is_(False)),
        "total_sessions": len(session_store._data),       # noqa: SLF001 (reference impl)
        "open_consults": sum(1 for c in consult_store.all() if c.status == "pending"),
    }


@router.get("/doctors")
async def list_doctors(
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> list[dict]:
    docs = db.scalars(select(User).where(User.role == "doctor")).all()
    return [_doctor_dict(d) for d in docs]


@router.get("/pending")
async def pending(
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    docs = db.scalars(select(User).where(User.role == "doctor", User.verified.is_(False))).all()
    admins = db.scalars(select(User).where(User.role == "admin", User.verified.is_(False))).all()
    return {"doctors": [_doctor_dict(d) for d in docs], "management": [_admin_dict(a) for a in admins]}


def _set_verified(db: Session, uid: str, approved: bool) -> dict:
    u = db.get(User, uid)
    if not u or u.role == "patient":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    u.verified = approved
    db.commit()
    return {"uid": u.id, "username": u.username, "role": u.role, "verified": u.verified}


@router.post("/verify")
async def verify(
    body: DoctorVerifyRequest,
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    return _set_verified(db, body.uid, body.approved)


@router.post("/doctors/verify")     # kept for existing clients
async def verify_doctor(
    body: DoctorVerifyRequest,
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    return _set_verified(db, body.uid, body.approved)


@router.delete("/users/{uid}")
async def delete_user(
    uid: str,
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    """Reject = permanently delete a doctor/management account (and its tokens)."""
    if uid == user.uid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete your own account")
    u = db.get(User, uid)
    if not u or u.role == "patient":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    for t in db.scalars(select(AuthToken).where(AuthToken.user_id == uid)).all():
        db.delete(t)
    db.delete(u)
    db.commit()
    return {"ok": True, "deleted": uid}


@router.get("/patients")
async def list_patients(
    q: str | None = None,
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> list[dict]:
    """All patients, optionally filtered by id / username / name / email."""
    patients = db.scalars(select(User).where(User.role == "patient")).all()
    if q:
        ql = q.strip().lower()
        patients = [p for p in patients if ql in (p.id or "").lower()
                    or ql in (p.username or "").lower()
                    or ql in (p.name or "").lower()
                    or ql in (p.email or "").lower()]
    out = []
    for p in patients:
        cases = consult_store.for_patient(p.id)
        out.append({
            "uid": p.id, "username": p.username, "name": p.name, "email": p.email,
            "age": p.age, "gender": p.gender,
            "history_completed": bool(p.history_completed),
            "screenings": len(session_store.list_for_user(p.id)),
            "consultations": len(cases),
        })
    return out


@router.get("/patients/{uid}")
async def patient_detail(
    uid: str,
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    """Full record for one patient: profile, history, screenings and what happened."""
    p = db.get(User, uid)
    if not p or p.role != "patient":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    sessions = []
    for s in session_store.list_for_user(uid):
        r = s.result
        sessions.append({
            "session_id": s.id,
            "disease": (s.brief.disease if s.brief else None),
            "mode": (s.brief.mode.value if s.brief else None),
            "confidence": (s.brief.confidence if s.brief else None),
            "urgent": bool(s.brief.urgent) if s.brief else False,
            "done": s.done,
            "outcome": (r.summary if r else None),
            "recommendation": (r.recommendation if r else None),
        })

    consults = [{
        "id": c.id, "status": c.status, "doctor_name": c.doctor_name,
        "appointment_time": c.appointment_time, "note": c.note,
        "disease": (c.brief.disease if c.brief else None),
        "solution": c.solution,
    } for c in consult_store.for_patient(uid)]

    return {
        "uid": p.id, "username": p.username, "name": p.name, "email": p.email,
        "age": p.age, "gender": p.gender,
        "history_completed": bool(p.history_completed),
        "medical_history": p.medical_history or {},
        "screenings": sessions,
        "consultations": consults,
    }


@router.get("/doctors/{uid}/license")
async def doctor_license(
    uid: str,
    user: CurrentUser = Depends(require_verified_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    u = db.get(User, uid)
    if not u or not u.license_path or not Path(u.license_path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No license uploaded")
    return FileResponse(u.license_path)
