"""Generate a PDF diagnosis report (AI findings + visual analysis + questionnaire +
recommendation) and store it under backend/reports/. Used by patients and doctors."""
from __future__ import annotations

import datetime
from pathlib import Path

from fpdf import FPDF

from ..config import BACKEND_DIR

REPORTS_DIR = BACKEND_DIR / "reports"


def _s(text) -> str:
    """fpdf core fonts are latin-1; drop anything outside it."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


class _Report(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(37, 99, 235)
        self.multi_cell(0, 10, "DermAI - Skin Screening Report", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-18)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.multi_cell(0, 4, _s(
            "This is a preliminary AI screening, not a medical diagnosis. "
            "Please consult a qualified dermatologist for confirmation."),
            new_x="LMARGIN", new_y="NEXT")


def _para(pdf: _Report, text: str, *, bold: bool = False, size: int = 11, h: int = 7) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B" if bold else "", size)
    pdf.multi_cell(0, h, _s(text), new_x="LMARGIN", new_y="NEXT")


def _section(pdf: _Report, title: str) -> None:
    pdf.ln(2)
    pdf.set_text_color(15, 23, 42)
    _para(pdf, title, bold=True, size=12, h=8)
    pdf.set_text_color(30, 41, 59)


def _kv(pdf: _Report, key: str, value: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 11)
    key_s = _s(key)
    # Size the label column to the actual text width (min 40mm) so long labels —
    # e.g. "Skin phototype (Fitzpatrick):" — never overflow into / overlap the value.
    avail = pdf.w - pdf.l_margin - pdf.r_margin
    kw = min(max(40.0, pdf.get_string_width(key_s) + 4), avail - 30)
    pdf.cell(kw, 7, key_s)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, _s(value), new_x="LMARGIN", new_y="NEXT")


def generate_report(session) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{session.id}.pdf"

    brief = session.brief
    result = session.result
    pdf = _Report()
    pdf.add_page()

    # meta
    pdf.set_text_color(100, 100, 100)
    _para(pdf, f"Report ID: {session.id}", size=10, h=6)
    _para(pdf, f"Date: {datetime.datetime.now():%Y-%m-%d %H:%M}", size=10, h=6)
    _para(pdf, f"Patient ID: {session.user_id}", size=10, h=6)

    # diagnosis
    _section(pdf, "AI Diagnosis")
    _kv(pdf, "Condition:", f"{brief.disease}")
    _kv(pdf, "Confidence:", f"{brief.confidence * 100:.1f}%")
    _kv(pdf, "Assessment:", brief.mode.value if hasattr(brief.mode, "value") else str(brief.mode))
    if brief.urgent:
        _kv(pdf, "Priority:", "URGENT - prompt in-person evaluation advised")
    _kv(pdf, "Body region:", brief.body_region or "not provided")
    _kv(pdf, "Image quality:", brief.image_quality)

    # affected-area photo (so the consulting doctor sees what was screened)
    img_path = getattr(session, "image_path", None)
    if img_path and Path(img_path).exists():
        try:
            _section(pdf, "Affected Area Photo")
            pdf.image(str(img_path), w=70)
            pdf.ln(3)
        except Exception:  # noqa: BLE001 — never let an image break the report
            pass

    # visual analysis
    if brief.insights:
        _section(pdf, "Visual Analysis")
        _para(pdf, brief.insights.get("summary", ""))
        _kv(pdf, "Dominant colour:", str(brief.insights.get("dominant_color", "-")))
        _kv(pdf, "Surface texture:", str(brief.insights.get("texture", "-")))
        _kv(pdf, "Affected area:", f"~{brief.insights.get('affected_area_pct', '-')}%")
        _kv(pdf, "Borders:", str(brief.insights.get("border", "-")))

    # medical history
    mh = getattr(brief, "medical_history", None) or {}
    if mh:
        _section(pdf, "Medical History")
        labels = [
            ("full_name", "Name"),
            ("age", "Age"),
            ("sex", "Sex"),
            ("occupation", "Occupation"),
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
        shown = False
        for key, label in labels:
            if mh.get(key):
                _kv(pdf, f"{label}:", str(mh[key]))
                shown = True
        if not shown:
            _para(pdf, "Not provided.")

    # questionnaire
    _section(pdf, "Symptom Questionnaire")
    if session.history:
        for m in session.history:
            is_q = m.role == "assistant"
            _para(pdf, f"{'Q' if is_q else 'A'}: {m.content}", bold=is_q, h=6)
    else:
        _para(pdf, "No questionnaire recorded.", h=6)

    # recommendation
    _section(pdf, "Assessment & Recommendation")
    if result:
        _para(pdf, result.summary)
        _para(pdf, result.recommendation, bold=True)
    else:
        _para(pdf, "Screening not finalized.")

    pdf.output(str(path))
    return path
