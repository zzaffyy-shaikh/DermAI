"""ConvNeXt-Tiny skin-disease classifier.

IMPORTANT: the model was trained on WHOLE images, so inference runs on the whole
image too (never on a MobileSAM crop) to avoid a train/inference mismatch.
"""
from __future__ import annotations

import json
import threading

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models

from ..config import Settings, get_settings
from ..schemas import Prediction
from .preprocess import build_transform


def _resolve_device(pref: str) -> torch.device:
    if pref == "cpu":
        return torch.device("cpu")
    if pref == "cuda" or (pref == "auto" and torch.cuda.is_available()):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device("cpu")


class SkinClassifier:
    """Singleton wrapper around the trained ConvNeXt-Tiny weights."""

    _instance: "SkinClassifier | None" = None
    _lock = threading.Lock()

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.device = _resolve_device(self.settings.device)

        meta = json.loads(self.settings.resolve_classes_file().read_text(encoding="utf-8"))
        self.classes: list[str] = meta["classes"]
        self._display: dict[str, str] = meta.get("display", {})
        self._urgent: set[str] = {self.display(c) for c in meta.get("urgent", [])}

        model = models.convnext_tiny()
        in_features = model.classifier[2].in_features
        model.classifier[2] = nn.Linear(in_features, len(self.classes))
        state = torch.load(self.settings.model_path, map_location=self.device, weights_only=True)
        model.load_state_dict(state)
        model.eval().to(self.device)
        self.model = model

        self.transform = build_transform(self.settings)

    # ---- helpers ----
    def display(self, raw: str) -> str:
        """Map a raw training-folder label to a clean display name."""
        return self._display.get(raw, raw)

    def is_urgent(self, display_name: str) -> bool:
        return display_name in self._urgent

    @classmethod
    def get(cls) -> "SkinClassifier":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- inference ----
    @torch.inference_mode()
    def predict(self, img: Image.Image, top_k: int = 3) -> tuple[list[Prediction], float]:
        """Return (top-k predictions with display names, softmax entropy in nats)."""
        x = self.transform(img).unsqueeze(0).to(self.device)
        logits = self.model(x)
        probs = F.softmax(logits, dim=1)[0]

        entropy = float(-(probs * torch.log(probs + 1e-9)).sum().item())

        k = min(top_k, len(self.classes))
        values, indices = torch.topk(probs, k)
        preds = [
            Prediction(disease=self.display(self.classes[int(i)]),
                       confidence=float(v.item()), index=int(i))
            for v, i in zip(values, indices)
        ]
        return preds, entropy
