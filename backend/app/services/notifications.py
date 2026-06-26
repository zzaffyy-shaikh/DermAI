"""In-app notification center + Expo phone push (in-memory reference implementation).

In-app notifications are delivered by polling (GET /notifications). When an event
fires we ALSO send a real phone push to the user's registered Expo push token(s)
via Expo's free push service, so the app shows a system banner like other apps.
"""
from __future__ import annotations

import datetime
import json
import urllib.request
import uuid
from threading import Lock, Thread

from ..schemas import Notification

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _post_expo(tokens: list[str], text: str) -> None:
    """Fire-and-forget POST to Expo's push service (runs in a background thread)."""
    try:
        messages = [{"to": t, "title": "DermAI", "body": text, "sound": "default"}
                    for t in tokens if str(t).startswith("ExponentPushToken")]
        if not messages:
            return
        data = json.dumps(messages).encode("utf-8")
        req = urllib.request.Request(
            _EXPO_PUSH_URL, data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as exc:  # noqa: BLE001 — push is best-effort, never break the request
        print(f"[push] Expo send failed: {exc}")


class NotificationStore:
    def __init__(self) -> None:
        self._items: dict[str, list[Notification]] = {}
        self._tokens: dict[str, set[str]] = {}    # user_id -> Expo push tokens
        self._lock = Lock()

    def register_token(self, user_id: str, token: str) -> None:
        if token:
            with self._lock:
                self._tokens.setdefault(user_id, set()).add(token)

    def push(self, user_id: str, text: str, kind: str = "info",
             case_id: str | None = None) -> Notification:
        note = Notification(
            id=uuid.uuid4().hex, user_id=user_id, text=text, kind=kind,
            case_id=case_id, read=False, created_at=_now_iso(),
        )
        with self._lock:
            self._items.setdefault(user_id, []).append(note)
            tokens = list(self._tokens.get(user_id, ()))
        if tokens:   # also deliver as a phone push, off the request thread
            Thread(target=_post_expo, args=(tokens, text), daemon=True).start()
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
