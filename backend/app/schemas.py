"""Pydantic models shared across the API and services."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Mode(str, Enum):
    HEALTHY = "healthy"
    OOD = "ood"          # out-of-distribution / low confidence
    NORMAL = "normal"


class Role(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class Prediction(BaseModel):
    disease: str
    confidence: float = Field(ge=0, le=1)
    index: int


class ClinicalBrief(BaseModel):
    """Structured summary the LLM receives — it never sees the raw image."""
    mode: Mode
    disease: str
    confidence: float
    entropy: float
    second_guess: Prediction | None = None
    top_k: list[Prediction] = []
    body_region: str | None = None          # from the patient's UI tap
    severity: str | None = None             # from MobileSAM lesion area (if available)
    lesion_area_pct: float | None = None
    image_quality: str = "clear"            # clear | blurry
    urgent: bool = False                    # e.g. suspected melanoma
    insights: dict | None = None            # visual analysis (color/texture/area/borders)
    patient_sex: str | None = None          # from the patient's profile
    patient_age: int | None = None
    medical_history: dict | None = None     # patient's stored medical history


class ChatMessage(BaseModel):
    role: str                               # "assistant" | "user"
    content: str


class DiagnoseResponse(BaseModel):
    session_id: str
    brief: ClinicalBrief
    message: str
    awaiting_answer: bool


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class ChatTurn(BaseModel):
    session_id: str
    message: str
    awaiting_answer: bool
    done: bool


class FinalResult(BaseModel):
    session_id: str
    disease: str
    confidence: float
    summary: str
    recommendation: str
    urgent: bool


# ---- consultation / admin ----

class ConsultRequest(BaseModel):
    session_id: str
    doctor_id: str                          # patient chooses the dermatologist
    slot_id: str                            # the appointment slot they booked
    mode: str = "video"                     # video only
    note: str | None = None


class ConsultCase(BaseModel):
    id: str
    patient_id: str
    patient_name: str | None = None
    session_id: str
    mode: str
    status: str                            # pending | confirmed | declined | closed
    brief: ClinicalBrief | None = None
    note: str | None = None
    room: str | None = None                # shared video-call room name
    doctor_id: str | None = None           # the dermatologist the patient chose
    doctor_name: str | None = None
    slot_id: str | None = None
    appointment_time: str | None = None    # ISO datetime of the booked slot
    accepted_by: str | None = None         # doctor uid who confirmed (== doctor_id)
    solution: str | None = None            # doctor's advice / outcome note
    created_at: str | None = None


class ConsultCaseDetail(ConsultCase):
    """Full hand-off context shown to the confirming doctor."""
    medical_history: dict | None = None
    final_summary: str | None = None
    final_recommendation: str | None = None
    transcript: list[ChatMessage] = []
    report_url: str | None = None


class ConsultSolution(BaseModel):
    solution: str


# ---- appointments / availability ----

class Slot(BaseModel):
    id: str
    doctor_id: str
    start: str                             # ISO datetime
    status: str = "open"                   # open | booked
    case_id: str | None = None


class SlotCreate(BaseModel):
    slots: list[str]                       # ISO datetimes the doctor is available


class DoctorPublic(BaseModel):
    """A bookable dermatologist shown to patients."""
    uid: str
    name: str | None = None
    specialization: str | None = None
    qualification: str | None = None
    slots: list[Slot] = []                  # open slots only


# ---- notifications ----

class Notification(BaseModel):
    id: str
    user_id: str
    text: str
    kind: str = "info"                     # info | consult | appointment | solution
    case_id: str | None = None
    read: bool = False
    created_at: str


class DoctorVerifyRequest(BaseModel):
    uid: str
    approved: bool


class SessionSummary(BaseModel):
    session_id: str
    disease: str
    mode: str
    confidence: float
    done: bool
    urgent: bool


# ---- auth ----

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "patient"               # patient | doctor | admin
    name: str | None = None
    email: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str | None = None
    # doctor / management credentials (required for verification)
    specialization: str | None = None
    qualification: str | None = None
    graduation: str | None = None
    house_job: str | None = None
    pmdc_number: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str        # the Google ID token (JWT) from the client


class UserPublic(BaseModel):
    uid: str
    username: str
    role: str
    name: str | None = None
    email: str | None = None
    verified: bool = True


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


# ---- medical history ----

class MedicalHistory(BaseModel):
    """Dermatological history modelled on the Rook's / Fitzpatrick examination
    framework (demographics, skin phototype, atopy, sun exposure, drugs, social)."""
    # demographics
    full_name: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = None                          # Male | Female | Other
    occupation: str | None = None
    # dermatology-specific
    fitzpatrick_type: str | None = None             # Fitzpatrick skin phototype I-VI
    previous_skin_conditions: str | None = None
    atopy_history: str | None = None                # eczema / asthma / hay fever
    family_history: str | None = None               # family skin disease
    skin_cancer_history: str | None = None          # personal/family melanoma or skin cancer
    sun_exposure: str | None = None                 # High | Moderate | Low (incl. sunbed)
    sunscreen_use: str | None = None                # Regular | Sometimes | Never
    # general medical
    chronic_conditions: str | None = None           # diabetes, thyroid, autoimmune, immunosuppression
    current_medications: str | None = None
    allergies: str | None = None                    # drug / contact allergies
    # social
    smoking: str | None = None                      # never | former | current
    alcohol: str | None = None                      # none | occasional | regular
    notes: str | None = None


class MedicalHistoryResponse(BaseModel):
    history: MedicalHistory
    completed: bool
