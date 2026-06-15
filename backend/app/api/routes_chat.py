"""Cross-questioning chat: REST answer endpoint + a streaming WebSocket."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from ..config import get_settings
from ..llm.orchestrator import Orchestrator
from ..llm.providers import get_provider
from ..schemas import AnswerRequest, ChatTurn, FinalResult, Role
from ..services.sessions import session_store
from .deps import CurrentUser, require_role

router = APIRouter(tags=["chat"])


def _orchestrator() -> Orchestrator:
    settings = get_settings()
    return Orchestrator(get_provider(settings), settings)


@router.post("/chat/answer", response_model=ChatTurn)
async def answer(
    body: AnswerRequest,
    user: CurrentUser = Depends(require_role(Role.PATIENT, Role.DOCTOR)),
) -> ChatTurn:
    session = session_store.get(body.session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if session.user_id != user.uid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your session")
    return await _orchestrator().reply(session, body.answer)


@router.get("/chat/{session_id}/result", response_model=FinalResult)
async def result(
    session_id: str,
    user: CurrentUser = Depends(require_role(Role.PATIENT, Role.DOCTOR)),
) -> FinalResult:
    session = session_store.get(session_id)
    if session is None or session.user_id != user.uid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if not session.result:
        raise HTTPException(status.HTTP_409_CONFLICT, "Session not finalized yet")
    return session.result


@router.websocket("/chat/ws/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str) -> None:
    """Bidirectional chat. Client sends plain-text answers; server replies with
    JSON ChatTurn objects until `done` is true. (Dev auth: pass ?uid= in query.)"""
    await websocket.accept()
    session = session_store.get(session_id)
    if session is None:
        await websocket.send_json({"error": "session not found"})
        await websocket.close()
        return

    orchestrator = _orchestrator()
    try:
        while not session.done:
            answer_text = await websocket.receive_text()
            turn = await orchestrator.reply(session, answer_text)
            await websocket.send_json(turn.model_dump())
    except WebSocketDisconnect:
        return
