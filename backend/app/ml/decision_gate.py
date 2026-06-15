"""Decision gate: turns raw model output into a routed ClinicalBrief.

Routes to one of three modes:
  HEALTHY  -> top class is the healthy class
  OOD      -> low confidence OR high entropy (likely outside the 8 classes)
  NORMAL   -> a confident disease prediction
"""
from __future__ import annotations

from ..config import Settings
from ..schemas import ClinicalBrief, Mode, Prediction


def decide(
    preds: list[Prediction],
    entropy: float,
    settings: Settings,
    *,
    healthy_display: str,
    is_urgent,
    body_region: str | None = None,
    severity: str | None = None,
    lesion_area_pct: float | None = None,
    image_quality: str = "clear",
) -> ClinicalBrief:
    top = preds[0]
    second = preds[1] if len(preds) > 1 else None

    if top.disease == healthy_display:
        mode = Mode.HEALTHY
    elif top.confidence < settings.confidence_threshold or entropy > settings.entropy_threshold:
        mode = Mode.OOD
    else:
        mode = Mode.NORMAL

    urgent = mode == Mode.NORMAL and bool(is_urgent(top.disease))

    return ClinicalBrief(
        mode=mode,
        disease=top.disease,
        confidence=round(top.confidence, 3),
        entropy=round(entropy, 3),
        second_guess=second,
        top_k=preds,
        body_region=body_region,
        severity=severity,
        lesion_area_pct=lesion_area_pct,
        image_quality=image_quality,
        urgent=urgent,
    )
