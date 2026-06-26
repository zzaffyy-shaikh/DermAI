"""Rule-based differential refinement.

The image classifier gives a *prior* over the 8 trained classes. The patient's
answers to discriminating symptom questions then update that prior with a simple
naive-Bayes step, so the leading diagnosis AND its confidence can change based on
the history — not just the picture.

The per-disease P(symptom = yes | disease) values below are simplified clinical
heuristics (tunable), chosen to separate the trained classes — especially the
inflammatory look-alikes (Psoriasis / Atopic Dermatitis / Eczema). They are NOT a
substitute for a dermatologist; this only sharpens a screening estimate.

NOTE: "seborrheic dermatitis" is not a trained class — the model only knows
"Seborrheic Keratoses" (a benign growth). Refinement is limited to the 8 classes.
"""
from __future__ import annotations

from ..schemas import Prediction

# exact display strings emitted by the classifier
ACNE = "Acne"
ATOPIC = "Atopic Dermatitis"
ECZEMA = "Eczema"
HEALTHY = "Healthy"
HYPERPIG = "Hyper Pigmintation"
MELANOMA = "Melanoma"
PSORIASIS = "Psoriasis"
SEBK = "Seborrheic Keratoses"

DISEASES = [ACNE, ATOPIC, ECZEMA, HEALTHY, HYPERPIG, MELANOMA, PSORIASIS, SEBK]

_DEFAULT_P = 0.15   # P(yes|disease) for a disease not explicitly listed in a feature
_FLOOR, _CEIL = 0.03, 0.97


class Feature:
    __slots__ = ("id", "question", "p_yes")

    def __init__(self, fid: str, question: str, p_yes: dict[str, float]):
        self.id = fid
        self.question = question
        self.p_yes = p_yes

    def p(self, disease: str) -> float:
        v = self.p_yes.get(disease, _DEFAULT_P)
        return min(_CEIL, max(_FLOOR, v))


# Discriminating questions. Each maps to P(yes | disease) for the relevant classes.
FEATURES: list[Feature] = [
    Feature("silvery_plaques",
            "Are the patches covered with thick, silvery or whitish flaky scales?",
            {PSORIASIS: 0.85, ECZEMA: 0.25, ATOPIC: 0.25, SEBK: 0.35, HEALTHY: 0.05}),
    Feature("nail_changes",
            "Have you noticed nail changes such as pitting, ridging, or thickening?",
            {PSORIASIS: 0.6, ECZEMA: 0.12, ATOPIC: 0.12}),
    Feature("extensor_plaques",
            "Are the patches well-defined and mainly on the outer elbows, knees, or scalp?",
            {PSORIASIS: 0.7, ATOPIC: 0.2, ECZEMA: 0.2, SEBK: 0.1}),
    Feature("flexural_itch",
            "Is it very itchy and mainly in skin folds (inner elbows, behind the knees, neck)?",
            {ATOPIC: 0.8, ECZEMA: 0.6, PSORIASIS: 0.3}),
    Feature("childhood_atopy",
            "Have you had this on and off since childhood, or do you have asthma or hay fever?",
            {ATOPIC: 0.8, ECZEMA: 0.4}),
    Feature("oozing_weeping",
            "Does the area ooze, weep clear fluid, or form crusts?",
            {ECZEMA: 0.6, ATOPIC: 0.6, PSORIASIS: 0.15, ACNE: 0.2}),
    Feature("comedones_pustules",
            "Do you have blackheads, whiteheads, or pus-filled pimples?",
            {ACNE: 0.9, SEBK: 0.05, PSORIASIS: 0.05}),
    Feature("mole_changing",
            "Is it a mole or dark spot that has recently changed in size, shape, or colour, "
            "or has an irregular border?",
            {MELANOMA: 0.85, SEBK: 0.25, HYPERPIG: 0.2}),
    Feature("flat_dark_patches",
            "Are they flat, darker-than-normal patches with no itching, scaling, or pain?",
            {HYPERPIG: 0.8, SEBK: 0.3, HEALTHY: 0.2, MELANOMA: 0.2}),
    Feature("waxy_stuck_on",
            "Does it look like a waxy, raised, 'stuck-on' wart-like growth?",
            {SEBK: 0.8, MELANOMA: 0.2}),
    Feature("itchy",
            "Is the affected area itchy?",
            {ATOPIC: 0.85, ECZEMA: 0.8, PSORIASIS: 0.6, SEBK: 0.3, ACNE: 0.3,
             HYPERPIG: 0.1, MELANOMA: 0.15, HEALTHY: 0.1}),
]

_FEATURE_BY_ID = {f.id: f for f in FEATURES}
ANSWERS = ("yes", "no", "unsure")


def initial_posterior(top_k: list[Prediction]) -> dict[str, float]:
    """Build a prior over all classes from the classifier's top-k softmax."""
    post = {d: 1e-3 for d in DISEASES}
    for p in top_k:
        if p.disease in post:
            post[p.disease] = max(post[p.disease], float(p.confidence))
    return _normalise(post)


def update(posterior: dict[str, float], feature_id: str, answer: str) -> dict[str, float]:
    """Naive-Bayes update. answer ∈ {yes, no, unsure}; 'unsure' leaves it unchanged."""
    feat = _FEATURE_BY_ID.get(feature_id)
    if feat is None or answer == "unsure":
        return dict(posterior)
    out = {}
    for d, prob in posterior.items():
        py = feat.p(d)
        out[d] = prob * (py if answer == "yes" else (1.0 - py))
    return _normalise(out)


def next_feature(posterior: dict[str, float], asked: set[str]) -> Feature | None:
    """Pick the unasked question that best separates the two leading candidates."""
    ranked = sorted(posterior.items(), key=lambda kv: kv[1], reverse=True)
    top = [d for d, _ in ranked[:2]] or DISEASES[:2]
    d1, d2 = (top + top)[:2]
    best, best_gap = None, -1.0
    for f in FEATURES:
        if f.id in asked:
            continue
        gap = abs(f.p(d1) - f.p(d2))
        if gap > best_gap:
            best, best_gap = f, gap
    return best


def leading(posterior: dict[str, float]) -> tuple[str, float]:
    d, p = max(posterior.items(), key=lambda kv: kv[1])
    return d, round(p, 3)


def normalise_answer(text: str) -> str:
    """Map a structured value or free text to yes / no / unsure."""
    t = (text or "").strip().lower()
    if t in ANSWERS:
        return t
    if t in ("y", "yes", "yeah", "yep", "true", "correct"):
        return "yes"
    if t in ("n", "no", "nope", "false", "none", "not really"):
        return "no"
    return "unsure"


def _normalise(post: dict[str, float]) -> dict[str, float]:
    total = sum(post.values()) or 1.0
    return {d: v / total for d, v in post.items()}
