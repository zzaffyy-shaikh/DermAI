"""Cross-questioning state machine.

- NORMAL mode runs a **rule-based differential**: structured Yes/No/Not-sure
  questions chosen to separate the leading candidates, with a naive-Bayes update
  of the posterior after each answer. The final diagnosis + confidence come from
  the refined posterior (so answers actually move the result), and the provider
  only writes the closing summary.
- HEALTHY / OOD keep the provider's conversational safety-net questions.
"""
from __future__ import annotations

from ..config import Settings
from ..ml import differential
from ..schemas import ChatMessage, ChatTurn, FinalResult, Mode
from ..services.sessions import Session
from .providers import BaseProvider

_OPTIONS = ["Yes", "No", "Not sure"]


class Orchestrator:
    def __init__(self, provider: BaseProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    def _limit(self, mode: Mode) -> int:
        # normal diagnosis gets the full cap; healthy/OOD use the shorter safety-net set
        return self.settings.max_questions if mode == Mode.NORMAL else self.settings.max_triage_questions

    # ---------- start ----------
    async def begin(self, session: Session) -> tuple[str, bool]:
        """Start a session. Returns (first_message, awaiting_answer)."""
        brief = session.brief
        if brief.mode == Mode.NORMAL:
            session.posterior = differential.initial_posterior(brief.top_k)
            session.asked_features = set()
            feat = differential.next_feature(session.posterior, session.asked_features)
            if feat is not None:
                self._ask_feature(session, feat, first=True)
                return feat.question, True

        # HEALTHY / OOD (or no differential question available): provider flow
        session.options = None
        question = await self.provider.ask(brief, session.history, asked=0)
        session.history.append(ChatMessage(role="assistant", content=question))
        session.asked = 1
        return question, True

    # ---------- each answer ----------
    async def reply(self, session: Session, answer: str) -> ChatTurn:
        if session.done:
            return ChatTurn(session_id=session.id, message="This session is already complete.",
                            awaiting_answer=False, done=True)

        session.history.append(ChatMessage(role="user", content=answer))
        brief = session.brief

        # rule-based differential branch
        if brief.mode == Mode.NORMAL and session.pending_feature:
            ans = differential.normalise_answer(answer)
            session.posterior = differential.update(session.posterior, session.pending_feature, ans)
            session.pending_feature = None

            if session.asked >= self._limit(brief.mode):
                return await self._finalize(session)
            feat = differential.next_feature(session.posterior, session.asked_features)
            if feat is None:
                return await self._finalize(session)
            self._ask_feature(session, feat)
            return ChatTurn(session_id=session.id, message=feat.question,
                            awaiting_answer=True, done=False, options=_OPTIONS)

        # conversational branch (HEALTHY / OOD)
        if session.asked >= self._limit(brief.mode):
            return await self._finalize(session)
        question = await self.provider.ask(brief, session.history, asked=session.asked)
        session.history.append(ChatMessage(role="assistant", content=question))
        session.asked += 1
        session.options = None
        return ChatTurn(session_id=session.id, message=question, awaiting_answer=True, done=False)

    # ---------- helpers ----------
    def _ask_feature(self, session: Session, feat, *, first: bool = False) -> None:
        session.pending_feature = feat.id
        session.asked_features.add(feat.id)
        session.options = _OPTIONS
        session.history.append(ChatMessage(role="assistant", content=feat.question))
        session.asked = 1 if first else session.asked + 1

    async def _finalize(self, session: Session) -> ChatTurn:
        brief = session.brief
        # fold the refined posterior back into the brief so the summary, report,
        # and result confidence reflect the answers — not just the picture.
        if brief.mode == Mode.NORMAL and session.posterior:
            disease, conf = differential.leading(session.posterior)
            brief.disease = disease
            brief.confidence = conf
            brief.urgent = brief.urgent or (disease == differential.MELANOMA)

        result: FinalResult = await self.provider.fuse(brief, session.history)
        result.session_id = session.id
        session.result = result
        session.done = True
        session.options = None
        message = f"{result.summary}\n\n{result.recommendation}"
        session.history.append(ChatMessage(role="assistant", content=message))
        return ChatTurn(session_id=session.id, message=message, awaiting_answer=False, done=True)
