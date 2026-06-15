"""Cross-questioning state machine. Provider-agnostic: it controls how many
questions to ask and when to fuse; the provider decides *what* to say."""
from __future__ import annotations

from ..config import Settings
from ..schemas import ChatMessage, ChatTurn, FinalResult, Mode
from ..services.sessions import Session
from .providers import BaseProvider


class Orchestrator:
    def __init__(self, provider: BaseProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    def _limit(self, mode: Mode) -> int:
        # normal diagnosis gets the full cap; healthy/OOD use the shorter safety-net set
        return self.settings.max_questions if mode == Mode.NORMAL else self.settings.max_triage_questions

    async def begin(self, session: Session) -> tuple[str, bool]:
        """Start a session. Returns (first_message, awaiting_answer)."""
        brief = session.brief
        # every mode (including healthy) now cross-questions before concluding
        question = await self.provider.ask(brief, session.history, asked=0)
        session.history.append(ChatMessage(role="assistant", content=question))
        session.asked = 1
        return question, True

    async def reply(self, session: Session, answer: str) -> ChatTurn:
        """Handle a patient answer; ask the next question or finalize."""
        if session.done:
            return ChatTurn(session_id=session.id, message="This session is already complete.",
                            awaiting_answer=False, done=True)

        session.history.append(ChatMessage(role="user", content=answer))

        if session.asked >= self._limit(session.brief.mode):
            return await self._finalize(session)

        question = await self.provider.ask(session.brief, session.history, asked=session.asked)
        session.history.append(ChatMessage(role="assistant", content=question))
        session.asked += 1
        return ChatTurn(session_id=session.id, message=question, awaiting_answer=True, done=False)

    async def _finalize(self, session: Session) -> ChatTurn:
        result: FinalResult = await self.provider.fuse(session.brief, session.history)
        result.session_id = session.id
        session.result = result
        session.done = True
        message = f"{result.summary}\n\n{result.recommendation}"
        session.history.append(ChatMessage(role="assistant", content=message))
        return ChatTurn(session_id=session.id, message=message, awaiting_answer=False, done=True)
