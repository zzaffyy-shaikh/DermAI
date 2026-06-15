"""Specialty rules. This is DermAI: only dermatologists may take online consults."""
from __future__ import annotations

# substrings that mark a dermatology specialty (case-insensitive)
_DERM_MARKERS = ("derma", "skin", "cutaneous", "venereo")


def is_dermatologist(specialization: str | None) -> bool:
    if not specialization:
        return False
    s = specialization.lower()
    return any(m in s for m in _DERM_MARKERS)
