"""Doctor-consultation cases (in-memory reference implementation).

Lifecycle: a patient picks a dermatologist and books one of the doctor's open
slots -> case is 'pending' (awaiting the doctor). The doctor 'confirms' (->
'confirmed') or 'declines' (-> 'declined', slot released). After the call the
doctor records a solution and 'closes' it. User/doctor data lives in the DB.
"""
from __future__ import annotations

import datetime
import uuid
from threading import Lock

from ..schemas import ClinicalBrief, ConsultCase


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


class ConsultStore:
    def __init__(self) -> None:
        self._cases: dict[str, ConsultCase] = {}
        self._lock = Lock()

    def create(self, *, patient_id: str, patient_name: str | None, session_id: str,
               doctor_id: str, doctor_name: str | None, slot_id: str,
               appointment_time: str | None, mode: str,
               brief: ClinicalBrief | None, note: str | None) -> ConsultCase:
        cid = uuid.uuid4().hex
        case = ConsultCase(
            id=cid, patient_id=patient_id, patient_name=patient_name, session_id=session_id,
            mode=mode, status="pending", brief=brief, note=note, room=f"DermAI-{cid}",
            doctor_id=doctor_id, doctor_name=doctor_name, slot_id=slot_id,
            appointment_time=appointment_time, created_at=_now_iso(),
        )
        with self._lock:
            self._cases[case.id] = case
        return case

    def get(self, case_id: str) -> ConsultCase | None:
        return self._cases.get(case_id)

    def all(self) -> list[ConsultCase]:
        return list(self._cases.values())

    def set_status(self, case_id: str, status: str) -> ConsultCase | None:
        case = self._cases.get(case_id)
        if case:
            case.status = status
        return case

    def confirm(self, case_id: str, doctor_id: str) -> ConsultCase | None:
        case = self._cases.get(case_id)
        if case and case.doctor_id == doctor_id:
            case.status = "confirmed"
            case.accepted_by = doctor_id
            return case
        return None

    def decline(self, case_id: str, doctor_id: str) -> ConsultCase | None:
        case = self._cases.get(case_id)
        if case and case.doctor_id == doctor_id:
            case.status = "declined"
            return case
        return None

    def cancel(self, case_id: str, patient_id: str) -> ConsultCase | None:
        """Patient cancels their own pending/confirmed appointment."""
        case = self._cases.get(case_id)
        if case and case.patient_id == patient_id and case.status in ("pending", "confirmed"):
            case.status = "cancelled"
            return case
        return None

    def set_solution(self, case_id: str, text: str) -> ConsultCase | None:
        case = self._cases.get(case_id)
        if case:
            case.solution = text
        return case

    # ---- queries ----
    def pending_for_doctor(self, doctor_id: str) -> list[ConsultCase]:
        return [c for c in self._cases.values()
                if c.doctor_id == doctor_id and c.status == "pending"]

    def for_doctor(self, doctor_id: str) -> list[ConsultCase]:
        """All cases addressed to this doctor (any status)."""
        return [c for c in self._cases.values() if c.doctor_id == doctor_id]

    def for_patient(self, patient_id: str) -> list[ConsultCase]:
        return [c for c in self._cases.values() if c.patient_id == patient_id]

    def has_case_for_patient(self, patient_id: str, doctor_id: str | None = None) -> bool:
        return any(
            c.patient_id == patient_id and (doctor_id is None or c.doctor_id == doctor_id)
            for c in self._cases.values()
        )

    def has_case_for_session(self, session_id: str, doctor_id: str | None = None) -> bool:
        return any(
            c.session_id == session_id and (doctor_id is None or c.doctor_id == doctor_id)
            for c in self._cases.values()
        )


consult_store = ConsultStore()
