"""Pytest fixtures. Env vars are set BEFORE importing the app so it uses an
isolated test database and the offline scripted LLM."""
import os
import pathlib

os.environ["DERMAI_DATABASE_URL"] = "sqlite:///./test_dermai.db"
os.environ["DERMAI_AUTH_MODE"] = "dev"
os.environ["DERMAI_LLM_PROVIDER"] = "scripted"

import pytest
from fastapi.testclient import TestClient

_DB = pathlib.Path("test_dermai.db")


@pytest.fixture(scope="session")
def client():
    if _DB.exists():
        _DB.unlink()
    from app.main import app  # imported here so env is applied first
    with TestClient(app) as c:   # context manager runs startup (init_db + model load)
        yield c
    if _DB.exists():
        try:
            _DB.unlink()
        except OSError:
            pass
