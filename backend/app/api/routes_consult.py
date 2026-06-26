"""Doctor consultation — appointment based.

Patient flow: browse dermatologists -> book one of their open slots -> case is
'pending'. Doctor flow: see incoming requests with full context (brief + medical
history + report) -> confirm or decline -> after the call, record a solution.
Only verified *dermatologists* can publish availability or take consults.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import (
    ConsultCase, ConsultCaseDetail, ConsultRequest, ConsultSolution, DoctorPublic,
    Role, Slot, SlotCreate,
)
from ..services.appointments import slot_store
from ..services.consult import consult_store
from ..services.notifications import notification_store
from ..services.sessions import session_store
from ..services.specialties import is_dermatologist
from .deps import CurrentUser, require_role, require_verified_role

router = APIRouter(prefix="/consult", tags=["consult"])


def _fmt_time(iso: str | None) -> str:
    return iso or "the scheduled time"


def _require_dermatologist(user: CurrentUser, db: Session) -> User:
    """Verified-doctor dependency already ran; enforce the dermatology specialty."""
    db_user = db.get(User, user.uid)
    if not db_user or not is_dermatologist(db_user.specialization):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Online consultations on DermAI are limited to dermatologists.",
        )
    return db_user


# ---------------- patient: pick a doctor & book ----------------

@router.get("/doctors", response_model=list[DoctorPublic])
async def list_dermatologists(
    user: CurrentUser = Depends(require_role(Role.PATIENT)),
    db: Session = Depends(get_db),
) -> list[DoctorPublic]:
    docs = db.scalars(select(User).where(User.role == "doctor", User.verified.is_(True))).all()
    out: list[DoctorPublic] = []
    for d in docs:
        if not is_dermatologist(d.specialization):
            continue
        out.append(DoctorPublic(
            uid=d.id, name=d.name or d.username, specialization=d.specialization,
            qualification=d.qualification, slots=slot_store.for_doctor(d.id, open_only=True),
        ))
    return out


@router.post("/request", response_model=ConsultCase)
async def request_consult(
    body: ConsultRequest,
    user: CurrentUser = Depends(require_role(Role.PATIENT)),
    db: Session = Depends(get_db),
) -> ConsultCase:
    session = session_store.get(body.session_id)
    if session is None or session.user_id != user.uid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    doctor = db.get(User, body.doctor_id)
    if not doctor or doctor.role != "doctor" or not doctor.verified \
            or not is_dermatologist(doctor.specialization):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please choose a verified dermatologist.")

    slot = slot_store.get(body.slot_id)
    if not slot or slot.doctor_id != body.doctor_id or slot.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "That appointment slot is no longer available.")

    patient = db.get(User, user.uid)
    case = consult_store.create(
        patient_id=user.uid, patient_name=(patient.name if patient else None) or user.username,
        session_id=body.session_id, doctor_id=doctor.id, doctor_name=doctor.name or doctor.username,
        slot_id=slot.id, appointment_time=slot.start, mode="video",
        brief=session.brief, note=body.note,
    )
    slot_store.book(slot.id, case.id)
    notification_store.push(
        doctor.id, kind="consult", case_id=case.id,
        text=f"New consult request from {case.patient_name} for {_fmt_time(slot.start)}.",
    )
    return case


@router.get("/my", response_model=list[ConsultCase])
async def my_appointments(
    user: CurrentUser = Depends(require_role(Role.PATIENT)),
) -> list[ConsultCase]:
    cases = consult_store.for_patient(user.uid)
    return sorted(cases, key=lambda c: c.created_at or "", reverse=True)


@router.post("/{case_id}/cancel", response_model=ConsultCase)
async def cancel(
    case_id: str,
    user: CurrentUser = Depends(require_role(Role.PATIENT)),
) -> ConsultCase:
    case = consult_store.cancel(case_id, user.uid)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Appointment not found, not yours, or can't be cancelled.")
    if case.slot_id:
        slot_store.release(case.slot_id)   # free the time so others (or they) can rebook
    if case.doctor_id:
        notification_store.push(
            case.doctor_id, kind="appointment", case_id=case.id,
            text=f"{case.patient_name} cancelled their {_fmt_time(case.appointment_time)} appointment.",
        )
    return case


# ---------------- doctor: availability ----------------

@router.get("/availability", response_model=list[Slot])
async def get_availability(
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> list[Slot]:
    _require_dermatologist(user, db)
    return slot_store.for_doctor(user.uid)


@router.post("/availability", response_model=list[Slot])
async def add_availability(
    body: SlotCreate,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> list[Slot]:
    _require_dermatologist(user, db)
    slot_store.add(user.uid, body.slots)
    return slot_store.for_doctor(user.uid)


@router.delete("/availability/{slot_id}", response_model=list[Slot])
async def remove_availability(
    slot_id: str,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> list[Slot]:
    _require_dermatologist(user, db)
    if not slot_store.remove(slot_id, user.uid):
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot not found, booked, or not yours.")
    return slot_store.for_doctor(user.uid)


# ---------------- doctor: requests & cases ----------------

@router.get("/requests", response_model=list[ConsultCase])
async def incoming_requests(
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> list[ConsultCase]:
    _require_dermatologist(user, db)
    return sorted(consult_store.pending_for_doctor(user.uid),
                  key=lambda c: c.appointment_time or "")


@router.get("/mine", response_model=list[ConsultCase])
async def mine(
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> list[ConsultCase]:
    _require_dermatologist(user, db)
    return sorted(consult_store.for_doctor(user.uid),
                  key=lambda c: c.appointment_time or "")


@router.get("/{case_id}", response_model=ConsultCaseDetail)
async def case_detail(
    case_id: str,
    user: CurrentUser = Depends(require_role(Role.PATIENT, Role.DOCTOR, Role.ADMIN)),
    db: Session = Depends(get_db),
) -> ConsultCaseDetail:
    case = consult_store.get(case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    # access control: the patient who owns it, the assigned doctor, or an admin
    if user.role == Role.PATIENT and case.patient_id != user.uid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your case")
    if user.role == Role.DOCTOR and case.doctor_id != user.uid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This case is assigned to another doctor")

    session = session_store.get(case.session_id)
    history = (case.brief.medical_history if case.brief else None)
    if not history:
        pt = db.get(User, case.patient_id)
        history = pt.medical_history if pt else None
    result = session.result if session else None
    return ConsultCaseDetail(
        **case.model_dump(),
        medical_history=history,
        final_summary=result.summary if result else None,
        final_recommendation=result.recommendation if result else None,
        transcript=session.history if session else [],
        report_url=f"/report/{case.session_id}",
    )


@router.post("/{case_id}/confirm", response_model=ConsultCase)
async def confirm(
    case_id: str,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> ConsultCase:
    _require_dermatologist(user, db)
    case = consult_store.confirm(case_id, user.uid)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found or not assigned to you")
    notification_store.push(
        case.patient_id, kind="appointment", case_id=case.id,
        text=f"Dr. {case.doctor_name} confirmed your appointment for {_fmt_time(case.appointment_time)}.",
    )
    return case


@router.post("/{case_id}/decline", response_model=ConsultCase)
async def decline(
    case_id: str,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> ConsultCase:
    _require_dermatologist(user, db)
    case = consult_store.decline(case_id, user.uid)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found or not assigned to you")
    if case.slot_id:
        slot_store.release(case.slot_id)
    notification_store.push(
        case.patient_id, kind="appointment", case_id=case.id,
        text=f"Dr. {case.doctor_name} couldn't take your {_fmt_time(case.appointment_time)} "
             "appointment. Please pick another doctor or time.",
    )
    return case


@router.post("/{case_id}/solution", response_model=ConsultCase)
async def add_solution(
    case_id: str,
    body: ConsultSolution,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> ConsultCase:
    _require_dermatologist(user, db)
    case = consult_store.get(case_id)
    if case is None or case.doctor_id != user.uid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found or not assigned to you")
    consult_store.set_solution(case_id, body.solution)
    notification_store.push(
        case.patient_id, kind="solution", case_id=case.id,
        text=f"Dr. {case.doctor_name} added advice to your consultation.",
    )
    return case


@router.post("/{case_id}/close", response_model=ConsultCase)
async def close(
    case_id: str,
    user: CurrentUser = Depends(require_verified_role(Role.DOCTOR)),
    db: Session = Depends(get_db),
) -> ConsultCase:
    _require_dermatologist(user, db)
    case = consult_store.get(case_id)
    if case is None or case.doctor_id != user.uid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found or not assigned to you")
    return consult_store.set_status(case_id, "closed")
