"""Doctor availability slots (in-memory reference implementation).

A dermatologist publishes time slots; a patient books one when requesting a
consult. Booking flips a slot from 'open' to 'booked' and ties it to a case.
"""
from __future__ import annotations

import uuid
from threading import Lock

from ..schemas import Slot


class SlotStore:
    def __init__(self) -> None:
        self._slots: dict[str, Slot] = {}
        self._lock = Lock()

    def add(self, doctor_id: str, starts: list[str]) -> list[Slot]:
        created: list[Slot] = []
        with self._lock:
            existing = {s.start for s in self._slots.values() if s.doctor_id == doctor_id}
            for start in starts:
                if not start or start in existing:
                    continue
                slot = Slot(id=uuid.uuid4().hex, doctor_id=doctor_id, start=start, status="open")
                self._slots[slot.id] = slot
                existing.add(start)
                created.append(slot)
        return created

    def get(self, slot_id: str) -> Slot | None:
        return self._slots.get(slot_id)

    def for_doctor(self, doctor_id: str, *, open_only: bool = False) -> list[Slot]:
        items = [s for s in self._slots.values() if s.doctor_id == doctor_id
                 and (not open_only or s.status == "open")]
        return sorted(items, key=lambda s: s.start)

    def remove(self, slot_id: str, doctor_id: str) -> bool:
        with self._lock:
            s = self._slots.get(slot_id)
            if s and s.doctor_id == doctor_id and s.status == "open":
                del self._slots[slot_id]
                return True
        return False

    def book(self, slot_id: str, case_id: str) -> Slot | None:
        with self._lock:
            s = self._slots.get(slot_id)
            if s and s.status == "open":
                s.status = "booked"
                s.case_id = case_id
                return s
        return None

    def release(self, slot_id: str) -> None:
        with self._lock:
            s = self._slots.get(slot_id)
            if s:
                s.status = "open"
                s.case_id = None


slot_store = SlotStore()
