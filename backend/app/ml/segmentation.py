"""MobileSAM wrapper — used ONLY for the visual overlay and a lesion-area/severity
estimate. It is NEVER fed to the classifier (which was trained on whole images).

Gracefully no-ops if MobileSAM isn't installed or no checkpoint is configured, so
the rest of the pipeline always works.
"""
from __future__ import annotations

import threading

import numpy as np
from PIL import Image

from ..config import Settings, get_settings


def _severity_from_area(area_pct: float) -> str:
    if area_pct < 5:
        return "mild"
    if area_pct < 20:
        return "moderate"
    return "severe"


class LesionSegmenter:
    """Singleton MobileSAM wrapper. `available` is False when SAM can't be loaded."""

    _instance: "LesionSegmenter | None" = None
    _lock = threading.Lock()

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.available = False
        self._predictor = None
        self._device = None
        self._try_load()

    def _try_load(self) -> None:
        ckpt = self.settings.sam_checkpoint
        if not ckpt:
            return
        try:
            import torch
            from mobile_sam import SamPredictor, sam_model_registry

            device = "cuda" if torch.cuda.is_available() and self.settings.device != "cpu" else "cpu"
            sam = sam_model_registry["vit_t"](checkpoint=ckpt)
            sam.to(device).eval()
            self._predictor = SamPredictor(sam)
            self._device = device
            self.available = True
        except Exception as exc:  # noqa: BLE001 - best-effort optional dependency
            print(f"[segmentation] MobileSAM unavailable, continuing without it: {exc}")
            self.available = False

    @classmethod
    def get(cls) -> "LesionSegmenter":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def segment(self, img: Image.Image) -> dict:
        """Return {available, severity, lesion_area_pct, mask}. Falls back to a
        neutral result when SAM isn't loaded."""
        if not self.available or self._predictor is None:
            return {"available": False, "severity": None, "lesion_area_pct": None, "mask": None}

        try:
            arr = np.asarray(img)
            h, w = arr.shape[:2]
            self._predictor.set_image(arr)
            # Prompt with the image centre — lesions in user uploads are usually centred.
            point = np.array([[w // 2, h // 2]])
            label = np.array([1])
            masks, scores, _ = self._predictor.predict(
                point_coords=point, point_labels=label, multimask_output=True
            )
            best = masks[int(np.argmax(scores))]
            area_pct = float(best.mean() * 100.0)
            return {
                "available": True,
                "severity": _severity_from_area(area_pct),
                "lesion_area_pct": round(area_pct, 1),
                "mask": best,
            }
        except Exception as exc:  # noqa: BLE001
            print(f"[segmentation] segment() failed: {exc}")
            return {"available": False, "severity": None, "lesion_area_pct": None, "mask": None}
