"""Central configuration. All settings are overridable via env vars (prefix DERMAI_)
or a .env file placed in the backend/ directory."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (parent of the app/ package) — used to resolve relative paths.
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="DERMAI_",
        extra="ignore",
    )

    # --- paths ---
    model_path: str = str(BACKEND_DIR.parent / "codes" / "convnext_skin_fyp_new.pth")
    classes_file: str = "classes.json"          # relative -> resolved against BACKEND_DIR
    sam_checkpoint: str | None = None           # None disables MobileSAM

    # --- inference ---
    device: str = "auto"                        # auto | cuda | cpu
    input_size: int = 224
    resize_size: int = 256
    blur_threshold: float = 90.0                # edge-variance below this => "blurry"

    # --- decision gate (CALIBRATE these on a leakage-free validation set!) ---
    confidence_threshold: float = 0.60          # below => out-of-distribution
    entropy_threshold: float = 1.60             # above => out-of-distribution (max ln8≈2.08)
    healthy_class: str = "Healthy"

    # --- LLM ---
    llm_provider: str = "scripted"              # scripted | openai | gemini
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    max_questions: int = 4                       # normal-diagnosis cross-questioning cap
    max_triage_questions: int = 3               # out-of-distribution triage cap

    # --- database ---
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'dermai.db').as_posix()}"

    # --- auth ---
    auth_mode: str = "dev"                      # dev = also accept X-Role/X-User-Id headers
    firebase_credentials: str | None = None
    seed_admin_username: str = "admin"          # auto-created on first startup
    seed_admin_password: str = "admin123"
    google_client_id: str | None = None          # web "Sign in with Google"
    google_android_client_id: str | None = None   # mobile (Android) Google sign-in

    # --- server ---
    cors_origins: list[str] = ["*"]

    def resolve_classes_file(self) -> Path:
        p = Path(self.classes_file)
        return p if p.is_absolute() else BACKEND_DIR / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
