"""LLM providers behind a common async interface.

- ScriptedProvider: no external API. Pulls questions from the question bank and
  builds a deterministic summary. Lets the whole system run/demoed offline.
- OpenAIProvider: uses the OpenAI API with the prompt builder; falls back to the
  scripted provider on any error.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Settings
from ..schemas import ChatMessage, ClinicalBrief, FinalResult, Mode
from . import prompt_builder
from .question_bank import HEALTHY_QUESTIONS, TRIAGE_QUESTIONS, questions_for


class BaseProvider(ABC):
    @abstractmethod
    async def ask(self, brief: ClinicalBrief, history: list[ChatMessage], asked: int) -> str:
        """Return the next question given how many have already been asked."""

    @abstractmethod
    async def reassure(self, brief: ClinicalBrief) -> str:
        """Return a reassuring message for the healthy case."""

    @abstractmethod
    async def fuse(self, brief: ClinicalBrief, history: list[ChatMessage]) -> FinalResult:
        """Produce the final result from the brief + collected answers."""


def _recommendation(brief: ClinicalBrief) -> str:
    if brief.urgent:
        return ("This lesion has features that warrant prompt evaluation. Please see a "
                "dermatologist as soon as possible.")
    if brief.mode == Mode.OOD:
        return ("We could not confidently identify this. Please consult a dermatologist "
                "for an in-person assessment.")
    if brief.mode == Mode.HEALTHY:
        return ("No skin condition was detected. If symptoms persist or appear, consult a "
                "dermatologist.")
    return ("This is a preliminary screening, not a diagnosis. If it persists or worsens, "
            "consult a dermatologist.")


class ScriptedProvider(BaseProvider):
    async def ask(self, brief: ClinicalBrief, history: list[ChatMessage], asked: int) -> str:
        if brief.mode == Mode.HEALTHY:
            pool = HEALTHY_QUESTIONS
        elif brief.mode == Mode.OOD:
            pool = TRIAGE_QUESTIONS
        else:
            pool = questions_for(brief.disease, brief.patient_sex)
        # never repeat a question already asked this session
        asked_texts = {m.content for m in history if m.role == "assistant"}
        for q in pool:
            if q not in asked_texts:
                return q
        return "Is there anything else about your symptoms you'd like to add?"

    async def reassure(self, brief: ClinicalBrief) -> str:
        return ("Good news — the analysis didn't detect signs of a skin condition in this "
                "image. If you're feeling discomfort that isn't visible here, or it persists, "
                "consider seeing a dermatologist.")

    async def fuse(self, brief: ClinicalBrief, history: list[ChatMessage]) -> FinalResult:
        if brief.mode == Mode.OOD:
            summary = (f"Based on the image, the system could not confidently identify the "
                       f"condition (top guess {brief.disease}, {brief.confidence:.0%}). Your "
                       f"answers were noted, but an in-person check is recommended.")
        elif brief.mode == Mode.HEALTHY:
            summary = ("The image doesn't show visible signs of a skin condition. A photo can't capture "
                       "everything, so if you reported any symptoms above, or they persist or change, "
                       "please see a dermatologist.")
        else:
            sev = f", {brief.severity} severity" if brief.severity else ""
            summary = (f"The analysis most likely indicates {brief.disease} "
                       f"({brief.confidence:.0%} confidence{sev}). Your symptom answers are "
                       f"consistent with this preliminary screening.")
        return FinalResult(
            session_id="",
            disease=brief.disease,
            confidence=brief.confidence,
            summary=summary,
            recommendation=_recommendation(brief),
            urgent=brief.urgent,
        )


class OpenAIProvider(BaseProvider):
    def __init__(self, settings: Settings) -> None:
        from openai import AsyncOpenAI  # imported lazily so it's an optional dep
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self._fallback = ScriptedProvider()

    def _msgs(self, system: str, history: list[ChatMessage], extra: str | None = None):
        msgs = [{"role": "system", "content": system}]
        msgs += [{"role": m.role, "content": m.content} for m in history]
        if extra:
            msgs.append({"role": "system", "content": extra})
        return msgs

    async def _complete(self, messages) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.4, max_tokens=300,
        )
        return resp.choices[0].message.content.strip()

    async def ask(self, brief: ClinicalBrief, history: list[ChatMessage], asked: int) -> str:
        try:
            system = prompt_builder.system_for(brief)
            kick = "Ask your next single clinical question now." if history else \
                   "Greet briefly, then ask your first clinical question."
            return await self._complete(self._msgs(system, history, kick))
        except Exception as exc:  # noqa: BLE001
            print(f"[openai] ask() failed, using scripted fallback: {exc}")
            return await self._fallback.ask(brief, history, asked)

    async def reassure(self, brief: ClinicalBrief) -> str:
        try:
            return await self._complete(self._msgs(prompt_builder.system_for(brief), []))
        except Exception as exc:  # noqa: BLE001
            print(f"[openai] reassure() failed, using scripted fallback: {exc}")
            return await self._fallback.reassure(brief)

    async def fuse(self, brief: ClinicalBrief, history: list[ChatMessage]) -> FinalResult:
        try:
            messages = self._msgs(prompt_builder.system_for(brief), history,
                                  prompt_builder.fuse_instruction(brief))
            summary = await self._complete(messages)
            return FinalResult(
                session_id="", disease=brief.disease, confidence=brief.confidence,
                summary=summary, recommendation=_recommendation(brief), urgent=brief.urgent,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[openai] fuse() failed, using scripted fallback: {exc}")
            return await self._fallback.fuse(brief, history)


class GeminiProvider(BaseProvider):
    """Google Gemini via the official google-genai SDK. Falls back to scripted on error.
    Uses a single-user-turn prompt (full transcript + instruction) to avoid Gemini's
    role-alternation constraints; all context lives in the system instruction."""

    def __init__(self, settings: Settings) -> None:
        from google import genai  # lazy optional dependency
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self._fallback = ScriptedProvider()

    @staticmethod
    def _transcript(history: list[ChatMessage]) -> str:
        return "\n".join(
            ("Question" if m.role == "assistant" else "Patient") + ": " + m.content
            for m in history
        )

    async def _generate(self, system: str, user_text: str) -> str:
        from google.genai import types
        resp = await self.client.aio.models.generate_content(
            model=self.model,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0.4, max_output_tokens=400,
            ),
        )
        return (resp.text or "").strip()

    async def ask(self, brief: ClinicalBrief, history: list[ChatMessage], asked: int) -> str:
        try:
            system = prompt_builder.system_for(brief)
            transcript = self._transcript(history)
            user = (transcript + "\n\n" if transcript else "") + (
                "Ask your next single clinical question now. Do NOT repeat any earlier question."
                if history else "Greet the patient briefly, then ask your first clinical question."
            )
            out = await self._generate(system, user)
            return out or await self._fallback.ask(brief, history, asked)
        except Exception as exc:  # noqa: BLE001
            print(f"[gemini] ask() failed, using scripted fallback: {exc}")
            return await self._fallback.ask(brief, history, asked)

    async def reassure(self, brief: ClinicalBrief) -> str:
        try:
            return await self._generate(prompt_builder.system_for(brief), "Reassure the patient now.") \
                or await self._fallback.reassure(brief)
        except Exception as exc:  # noqa: BLE001
            print(f"[gemini] reassure() failed, using scripted fallback: {exc}")
            return await self._fallback.reassure(brief)

    async def fuse(self, brief: ClinicalBrief, history: list[ChatMessage]) -> FinalResult:
        try:
            system = prompt_builder.system_for(brief)
            user = self._transcript(history) + "\n\n" + prompt_builder.fuse_instruction(brief)
            summary = await self._generate(system, user)
            if not summary:
                return await self._fallback.fuse(brief, history)
            return FinalResult(
                session_id="", disease=brief.disease, confidence=brief.confidence,
                summary=summary, recommendation=_recommendation(brief), urgent=brief.urgent,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[gemini] fuse() failed, using scripted fallback: {exc}")
            return await self._fallback.fuse(brief, history)


def get_provider(settings: Settings) -> BaseProvider:
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        try:
            return GeminiProvider(settings)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] Gemini init failed, using scripted provider: {exc}")
    if settings.llm_provider == "openai" and settings.openai_api_key:
        try:
            return OpenAIProvider(settings)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] OpenAI init failed, using scripted provider: {exc}")
    return ScriptedProvider()
