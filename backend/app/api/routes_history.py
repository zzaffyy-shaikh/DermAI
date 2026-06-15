"""Session history for the logged-in user."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas import Role, SessionSummary
from ..services.sessions import session_store
from .deps import CurrentUser, require_role

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[SessionSummary])
async def history(
    user: CurrentUser = Depends(require_role(Role.PATIENT, Role.DOCTOR)),
) -> list[SessionSummary]:
    return [
        SessionSummary(
            session_id=s.id, disease=s.brief.disease, mode=s.brief.mode.value,
            confidence=s.brief.confidence, done=s.done, urgent=s.brief.urgent,
        )
        for s in session_store.list_for_user(user.uid)
    ]
