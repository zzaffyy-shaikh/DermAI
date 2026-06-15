"""Diagnosis endpoint: image in -> ClinicalBrief + first LLM message out."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import BACKEND_DIR, Settings, get_settings
from ..db import get_db
from ..models import User
from ..llm.orchestrator import Orchestrator
from ..llm.providers import get_provider
from ..ml import decision_gate
from ..ml.classifier import SkinClassifier
from ..ml.preprocess import blur_score, pil_from_bytes
from ..ml.segmentation import LesionSegmenter
from ..ml.insights import extract_insights
from ..schemas import DiagnoseResponse, Role
from ..services.sessions import session_store
from .deps import CurrentUser, require_role

router = APIRouter(tags=["diagnose"])


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    image: UploadFile = File(...),
    body_region: str | None = Form(default=None),
    user: CurrentUser = Depends(require_role(Role.PATIENT, Role.DOCTOR)),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> DiagnoseResponse:
    # require a completed medical history before a patient can be diagnosed
    db_user = db.get(User, user.uid)
    if user.role == Role.PATIENT and not (db_user and db_user.history_completed):
        raise HTTPException(
            status.HTTP_428_PRECONDITION_REQUIRED,
            "Please complete your medical history before running a diagnosis.",
        )

    raw = await image.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty image upload")
    try:
        img = pil_from_bytes(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid image: {exc}") from exc

    clf = SkinClassifier.get()
    seg = LesionSegmenter.get()

    # Classification + segmentation are independent; run the blocking work in threads.
    preds_task = asyncio.to_thread(clf.predict, img)
    seg_task = asyncio.to_thread(seg.segment, img)
    blur_task = asyncio.to_thread(blur_score, img)
    insights_task = asyncio.to_thread(extract_insights, img)
    (preds, entropy), seg_result, focus, insights = await asyncio.gather(
        preds_task, seg_task, blur_task, insights_task)

    quality = "blurry" if focus < settings.blur_threshold else "clear"

    brief = decision_gate.decide(
        preds, entropy, settings,
        healthy_display=clf.display(settings.healthy_class),
        is_urgent=clf.is_urgent,
        body_region=body_region,
        severity=seg_result["severity"],
        lesion_area_pct=seg_result["lesion_area_pct"],
        image_quality=quality,
    )
    brief.insights = insights

    # attach patient demographics + medical history so questions are context-aware
    if db_user:
        mh = db_user.medical_history or {}
        brief.patient_sex = mh.get("sex") or db_user.gender
        brief.patient_age = mh.get("age") or db_user.age
        brief.medical_history = db_user.medical_history

    session = session_store.create(user.uid, brief)

    # Persist the uploaded photo so the consulting doctor can see the affected area.
    try:
        uploads = BACKEND_DIR / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        image_path = uploads / f"{session.id}.jpg"
        img.convert("RGB").save(image_path, "JPEG", quality=88)
        session.image_path = str(image_path)
    except Exception as exc:  # noqa: BLE001 — a failed save must not break diagnosis
        print(f"[diagnose] could not store image for session {session.id}: {exc}")

    orchestrator = Orchestrator(get_provider(settings), settings)
    message, awaiting = await orchestrator.begin(session)

    return DiagnoseResponse(
        session_id=session.id, brief=brief, message=message, awaiting_answer=awaiting,
    )
