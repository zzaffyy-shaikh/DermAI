"""PDF diagnosis report: generate on demand, store, and serve to the patient
(their own) or any doctor/admin. Accepts the token via header OR ?token= so the
file can be opened directly from a link in the app."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import Role
from ..services import auth as auth_service
from ..services.consult import consult_store
from ..services.report import generate_report
from ..services.sessions import session_store

router = APIRouter(tags=["report"])


def _authorized_session(session_id: str, token: str | None, authorization: str | None, db: Session):
    """Resolve the caller (bearer header or ?token=) and authorize access to the
    session: the owning patient, a verified doctor with a consult for it, or admin."""
    tok = None
    if authorization and authorization.lower().startswith("bearer "):
        tok = authorization.split(" ", 1)[1]
    elif token:
        tok = token
    user = auth_service.get_user_by_token(db, tok) if tok else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    if user.role == Role.PATIENT.value and session.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your session")
    if user.role == Role.DOCTOR.value:
        if not user.verified or not consult_store.has_case_for_session(session_id, user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "No consultation relationship with this session")
    return session


@router.get("/image/{session_id}")
def get_image(
    session_id: str,
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    from pathlib import Path
    session = _authorized_session(session_id, token, authorization, db)
    if not session.image_path or not Path(session.image_path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No image for this session")
    return FileResponse(session.image_path, media_type="image/jpeg")


@router.get("/report/{session_id}")
def get_report(
    session_id: str,
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    session = _authorized_session(session_id, token, authorization, db)

    path = None
    if session.report_path:
        from pathlib import Path
        if Path(session.report_path).exists():
            path = session.report_path
    if path is None:
        path = str(generate_report(session))
        session.report_path = path

    return FileResponse(path, media_type="application/pdf",
                        filename=f"DermAI-{session_id}.pdf")
