"""Patient medical history — a persistent record filled once and reused for every
diagnosis, and injected into the LLM."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import MedicalHistory, MedicalHistoryResponse, Role
from ..services.consult import consult_store
from .deps import CurrentUser, require_role, require_verified_role


def _ensure_doctor_relationship(user: CurrentUser, patient_uid: str) -> None:
    """A doctor may only access a patient's data if that patient has a consult case.
    Admins may access anyone."""
    if user.role == Role.DOCTOR and not consult_store.has_case_for_patient(patient_uid, user.uid):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "No consultation relationship with this patient")

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/medical-history", response_model=MedicalHistoryResponse)
def get_medical_history(
    user: CurrentUser = Depends(require_role(Role.PATIENT, Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> MedicalHistoryResponse:
    db_user = db.get(User, user.uid)
    data = (db_user.medical_history or {}) if db_user else {}
    return MedicalHistoryResponse(
        history=MedicalHistory(**data),
        completed=bool(db_user and db_user.history_completed),
    )


@router.put("/medical-history", response_model=MedicalHistoryResponse)
def update_medical_history(
    body: MedicalHistory,
    user: CurrentUser = Depends(require_role(Role.PATIENT)),
    db: Session = Depends(get_db),
) -> MedicalHistoryResponse:
    db_user = db.get(User, user.uid)
    if not db_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    db_user.medical_history = body.model_dump()
    db_user.history_completed = True
    db.commit()
    return MedicalHistoryResponse(history=body, completed=True)


# ---- doctor / admin: view & edit a specific patient's history ----

@router.get("/medical-history/{uid}", response_model=MedicalHistoryResponse)
def get_patient_history(
    uid: str,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR, Role.ADMIN)),
    db: Session = Depends(get_db),
) -> MedicalHistoryResponse:
    _ensure_doctor_relationship(user, uid)
    db_user = db.get(User, uid)
    if not db_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    data = db_user.medical_history or {}
    return MedicalHistoryResponse(history=MedicalHistory(**data), completed=bool(db_user.history_completed))


@router.put("/medical-history/{uid}", response_model=MedicalHistoryResponse)
def update_patient_history(
    uid: str,
    body: MedicalHistory,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR, Role.ADMIN)),
    db: Session = Depends(get_db),
) -> MedicalHistoryResponse:
    _ensure_doctor_relationship(user, uid)
    db_user = db.get(User, uid)
    if not db_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    db_user.medical_history = body.model_dump()
    db_user.history_completed = True
    db.commit()
    return MedicalHistoryResponse(history=body, completed=True)
