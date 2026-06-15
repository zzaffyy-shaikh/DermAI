"""Disease-specific clinical question banks.

Each entry is a dict with the question text and an optional `sex` restriction so we
never ask sex-inappropriate questions (e.g. menstrual cycle / pregnancy to a male).
Used directly by the scripted provider, and given to the LLM as guard-rails.
Keys use display names (see classes.json `display`).
"""
from __future__ import annotations

DISEASE_QUESTIONS: dict[str, list[dict]] = {
    "Acne": [
        {"q": "How long have you had these breakouts, and do they come and go in cycles?"},
        {"q": "Do you notice flare-ups around stress or diet?"},
        {"q": "Do your breakouts flare with your menstrual cycle?", "sex": "Female"},
        {"q": "What skincare or acne products are you currently using?"},
        {"q": "Have you tried any prescription treatments before, and did they help?"},
    ],
    "Atopic Dermatitis": [
        {"q": "Do you have a personal or family history of asthma, hay fever, or allergies?"},
        {"q": "How intense is the itching, and does it disturb your sleep?"},
        {"q": "Does it get worse in dry or cold weather, or with certain soaps/detergents?"},
        {"q": "How long have you had this, and does it flare in the same spots repeatedly?"},
    ],
    "Eczema": [
        {"q": "How severe is the itching, and is it worse at night?"},
        {"q": "Have you recently changed soaps, detergents, or skincare products?"},
        {"q": "Do you have a history of allergies, asthma, or sensitive skin?"},
        {"q": "Does the affected area weep, crack, or get worse in winter?"},
    ],
    "Hyper Pigmentation": [
        {"q": "How long have these darker patches been present?"},
        {"q": "Was there any prior injury, acne, or rash at the same spot before it darkened?"},
        {"q": "How much sun exposure does the area get, and do you use sunscreen?"},
        {"q": "Are you pregnant or recently been pregnant?", "sex": "Female"},
        {"q": "Are you taking any hormonal medication?"},
    ],
    "Melanoma": [
        {"q": "Has this spot changed in size, shape, or colour over recent weeks or months?"},
        {"q": "Has it ever bled, itched, crusted, or failed to heal?"},
        {"q": "Do you have a history of severe sunburns or a family history of skin cancer?"},
        {"q": "Roughly how long has this lesion been present?"},
    ],
    "Psoriasis": [
        {"q": "Do you have any family history of psoriasis?"},
        {"q": "Do you experience joint pain or stiffness along with the skin patches?"},
        {"q": "Have you noticed nail changes (pitting, thickening) or scalp involvement?"},
        {"q": "Do flare-ups follow stress, infections, or skin injury?"},
    ],
    "Seborrheic Keratoses": [
        {"q": "How long have these growths been present, and are they slowly enlarging?"},
        {"q": "Do you have one lesion or several in different areas?"},
        {"q": "Do they itch or get irritated by clothing or friction?"},
        {"q": "Have you noticed any rapid change in a single lesion recently?"},
    ],
}

# Broad triage questions for out-of-distribution cases (no sex restriction).
TRIAGE_QUESTIONS: list[str] = [
    "How long have you had this skin problem, and is it spreading?",
    "Are you experiencing pain, itching, bleeding, or any discharge?",
    "Have you had any fever, or do you have other symptoms alongside this?",
]

# Safety-net questions for a visually-healthy result — a photo can miss symptoms.
HEALTHY_QUESTIONS: list[str] = [
    "The photo doesn't show obvious signs of a skin condition. Are you having any itching, pain, "
    "burning, or discomfort that isn't visible here?",
    "Have you noticed any recent changes — a new spot, a colour change, or something that comes and goes?",
    "Any other symptoms, such as the area spreading, not healing, or fever?",
]


def questions_for(disease: str, sex: str | None = None) -> list[str]:
    """Return the question texts for a disease, filtered to the patient's sex.
    Sex-restricted questions are dropped when the sex doesn't match or is unknown."""
    items = DISEASE_QUESTIONS.get(disease)
    if items is None:
        return list(TRIAGE_QUESTIONS)
    out: list[str] = []
    for it in items:
        required = it.get("sex")
        if required and (sex is None or required.lower() != sex.lower()):
            continue
        out.append(it["q"])
    return out
