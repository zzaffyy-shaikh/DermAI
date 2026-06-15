"""Builds the LLM system prompt from a ClinicalBrief. The LLM never sees the image —
only this structured brief — so it behaves like a doctor who has already examined the
patient and asks clinical (not visual) questions."""
from __future__ import annotations

from ..schemas import ClinicalBrief, Mode
from .question_bank import questions_for

_BASE_RULES = (
    "You are DermAI, a careful dermatology screening assistant. You are NOT a doctor and "
    "must never give a definitive diagnosis or prescribe treatment. The image has ALREADY "
    "been analysed by a vision model, so you already know what it looks like. "
    "NEVER ask about appearance — colour, size, shape, edges, borders, texture, or location. "
    "Ask only clinical questions: history, duration, triggers, symptoms, family history, "
    "medications, lifestyle. Ask exactly ONE question per turn. Keep it short and plain. "
    "Take the patient's age and sex into account and NEVER ask sex-inappropriate questions "
    "(e.g. do not ask a male about menstrual cycles or pregnancy). Do not repeat a question. "
    "Use the patient's medical history below to guide which questions are worth asking and in "
    "your final assessment (e.g. don't re-ask things already known)."
)

_HISTORY_LABELS = [
    ("fitzpatrick_type", "Skin phototype (Fitzpatrick)"),
    ("previous_skin_conditions", "Previous skin conditions"),
    ("atopy_history", "Atopy (eczema/asthma/hay fever)"),
    ("family_history", "Family history"),
    ("skin_cancer_history", "Skin cancer history"),
    ("sun_exposure", "Sun exposure"),
    ("sunscreen_use", "Sunscreen use"),
    ("chronic_conditions", "Chronic conditions"),
    ("current_medications", "Medications"),
    ("allergies", "Allergies"),
    ("smoking", "Smoking"),
    ("alcohol", "Alcohol"),
    ("notes", "Other notes"),
]


def _demographics_line(brief: "ClinicalBrief") -> str:
    bits = []
    if brief.patient_age:
        bits.append(f"{brief.patient_age}y")
    if brief.patient_sex:
        bits.append(brief.patient_sex)
    occ = (brief.medical_history or {}).get("occupation")
    if occ:
        bits.append(str(occ))
    return f"- Patient: {', '.join(bits)}\n" if bits else ""


def _history_block(brief: "ClinicalBrief") -> str:
    h = brief.medical_history or {}
    lines = [f"  - {label}: {h[key]}" for key, label in _HISTORY_LABELS if h.get(key)]
    if not lines:
        return ""
    return "- Patient medical history:\n" + "\n".join(lines) + "\n"


def _region_line(brief: ClinicalBrief) -> str:
    if brief.body_region:
        return f"- Location (patient-reported): {brief.body_region}"
    return "- Location: not provided"


def _quality_line(brief: ClinicalBrief) -> str:
    if brief.image_quality == "blurry":
        return "- Image quality: BLURRY — be slightly more cautious about the prediction."
    return "- Image quality: clear"


def _insights_line(brief: ClinicalBrief) -> str:
    if brief.insights and brief.insights.get("summary"):
        return f"- Visual analysis of the lesion: {brief.insights['summary']}\n"
    return ""


def system_for(brief: ClinicalBrief) -> str:
    if brief.mode == Mode.HEALTHY:
        return (
            _BASE_RULES
            + "\n\nVision model findings:\n"
            + _demographics_line(brief)
            + _history_block(brief)
            + _insights_line(brief)
            + f"- Result: no visible signs of a skin disease were detected "
            f"('healthy' at {brief.confidence:.0%} confidence).\n"
            + _region_line(brief) + "\n"
            + "\nA photo can miss things, so do NOT conclude immediately. Briefly acknowledge the "
            "reassuring result, then ask focused safety-net questions about symptoms that are NOT "
            "visible in the image (itching, pain, burning, recent changes, duration, spread, fever), "
            "taking the medical history above into account. In your final summary: if the patient "
            "reports concerning symptoms, recommend seeing a dermatologist; otherwise reassure. "
            "Do not diagnose."
        )

    if brief.mode == Mode.OOD:
        return (
            _BASE_RULES
            + "\n\n"
            + _demographics_line(brief)
            + _history_block(brief)
            + _insights_line(brief)
            + f"The vision model could NOT confidently identify the condition "
            f"(top guess {brief.disease} at {brief.confidence:.0%}, high uncertainty). "
            "Do NOT commit to a diagnosis. Ask broad triage questions about duration, "
            "spread, and symptoms, then strongly recommend an in-person dermatologist visit. "
            f"Suggested areas to cover: {questions_for('__triage__')}"
        )

    # NORMAL
    severity = f" (severity estimate: {brief.severity})" if brief.severity else ""
    urgent = (
        "\nThis may be a serious lesion (e.g. melanoma): be supportive but clearly urge "
        "prompt in-person evaluation by a dermatologist."
        if brief.urgent else ""
    )
    bank = questions_for(brief.disease, brief.patient_sex)
    return (
        _BASE_RULES
        + f"\n\nVision model findings:\n"
        + _demographics_line(brief)
        + _history_block(brief)
        + f"- Most likely condition: {brief.disease} ({brief.confidence:.0%} confidence){severity}\n"
        + _region_line(brief) + "\n"
        + _quality_line(brief) + "\n"
        + _insights_line(brief)
        + (f"- Differential to keep in mind: {brief.second_guess.disease}\n" if brief.second_guess else "")
        + f"\nTailor your questions to {brief.disease}. Good lines of questioning: {bank}"
        + urgent
    )


def fuse_instruction(brief: ClinicalBrief) -> str:
    """Instruction appended when asking the LLM to produce the final summary."""
    return (
        "Now summarise for the patient. Using the vision findings and their answers, give: "
        "(1) a brief, plain-language explanation of the likely condition and confidence, "
        "(2) general self-care guidance, and (3) a clear recommendation on whether to see a "
        "doctor. Remind them this is a preliminary screening, not a diagnosis. "
        "Keep it under 120 words."
    )
