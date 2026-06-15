"""In-app notification center (in-memory reference implementation).

Notifications are delivered by polling: clients call GET /notifications and
GET /notifications/unread_count. Swap the store for a table/queue in production.
"""
from __future__ import annotations

import datetime
import uuid
from threading import Lock

from ..schemas import Notification


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


class NotificationStore:
    def __init__(self) -> None:
        self._items: dict[str, list[Notification]] = {}
        self._lock = Lock()

    def push(self, user_id: str, text: str, kind: str = "info",
             case_id: str | None = None) -> Notification:
        note = Notification(
            id=uuid.uuid4().hex, user_id=user_id, text=text, kind=kind,
            case_id=case_id, read=False, created_at=_now_iso(),
        )
        with self._lock:
            self._items.setdefault(user_id, []).append(note)
        return note

    def list_for(self, user_id: str) -> list[Notification]:
        # newest first
        return sorted(self._items.get(user_id, []), key=lambda n: n.created_at, reverse=True)

    def unread_count(self, user_id: str) -> int:
        return sum(1 for n in self._items.get(user_id, []) if not n.read)

    def mark_read(self, user_id: str, ids: list[str] | None = None) -> int:
        changed = 0
        with self._lock:
            for n in self._items.get(user_id, []):
                if (ids is None or n.id in ids) and not n.read:
                    n.read = True
                    changed += 1
        return changed


notification_store = NotificationStore()
