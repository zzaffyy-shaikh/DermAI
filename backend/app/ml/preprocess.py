"""Image preprocessing — must mirror the *validation* transform used at training time:
Resize -> CenterCrop -> ToTensor -> ImageNet normalize."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter
from torchvision import transforms

from ..config import Settings

_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


def build_transform(settings: Settings) -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize(settings.resize_size),
        transforms.CenterCrop(settings.input_size),
        transforms.ToTensor(),
        transforms.Normalize(_IMAGENET_MEAN, _IMAGENET_STD),
    ])


def pil_from_bytes(data: bytes) -> Image.Image:
    """Decode raw upload bytes into an RGB PIL image."""
    return Image.open(io.BytesIO(data)).convert("RGB")


def blur_score(img: Image.Image) -> float:
    """Dependency-free focus measure: variance of an edge-detected grayscale image.
    Higher = sharper. Lower than settings.blur_threshold => treat as blurry."""
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    return float(np.asarray(edges, dtype=np.float32).var())
