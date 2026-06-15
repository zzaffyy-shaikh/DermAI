"""Diagnosis session store (in-memory). Swap for Firestore in production."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from threading import Lock

from ..schemas import ChatMessage, ClinicalBrief, FinalResult


@dataclass
class Session:
    id: str
    user_id: str
    brief: ClinicalBrief
    history: list[ChatMessage] = field(default_factory=list)
    asked: int = 0
    done: bool = False
    result: FinalResult | None = None
    report_path: str | None = None
    image_path: str | None = None


class SessionStore:
    def __init__(self) -> None:
        self._data: dict[str, Session] = {}
        self._lock = Lock()

    def create(self, user_id: str, brief: ClinicalBrief) -> Session:
        session = Session(id=uuid.uuid4().hex, user_id=user_id, brief=brief)
        with self._lock:
            self._data[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._data.get(session_id)

    def list_for_user(self, user_id: str) -> list[Session]:
        return [s for s in self._data.values() if s.user_id == user_id]


# module-level singleton
session_store = SessionStore()
