"""Lightweight visual analysis of the uploaded image (no heavy model needed).

Extracts human-readable descriptors — dominant colour, redness, surface texture,
how much of the image stands out from surrounding skin, and border regularity —
so the LLM and the PDF report have real visual context (color/patch/edges/curves).

This is a pragmatic stand-in for full lesion segmentation (FastSAM); it can be
swapped/augmented later without changing callers.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def _color_name(r: float, g: float, b: float) -> str:
    if r > 185 and g > 185 and b > 185:
        return "pale / light"
    if r < 80 and g < 80 and b < 80:
        return "dark"
    if r > 120 and g < 105 and b < 105:
        return "red / inflamed"
    if r > 140 and 90 < g < 150 and b < 110:
        return "reddish-brown"
    if r > 120 and g > 90 and b > 70 and abs(r - g) < 35 and g > b:
        return "brown / tan"
    if r > 150 and g > 120 and b > 110:
        return "pink"
    return "mixed / uneven"


def extract_insights(img: Image.Image) -> dict:
    small = img.convert("RGB").resize((128, 128))
    arr = np.asarray(small).astype(np.float32)

    r, g, b = (float(arr[..., i].mean()) for i in range(3))
    brightness = float(arr.mean() / 255.0)
    contrast = float(arr.std() / 255.0)
    redness = float(r / (g + b + 1e-6))            # > ~0.52 => reddish

    # surface texture / "scaliness" via edge density
    edges = np.asarray(small.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    edge_density = float((edges > 40).mean())
    texture = "smooth" if edge_density < 0.06 else "moderately rough" if edge_density < 0.16 else "rough / scaly"

    # how much of the region deviates from the surrounding skin tone (the "patch")
    flat = arr.reshape(-1, 3)
    median = np.median(flat, axis=0)
    dist = np.linalg.norm(arr - median, axis=2)
    affected_area_pct = float((dist > (dist.mean() + dist.std())).mean() * 100.0)

    border = "irregular / uneven" if edge_density > 0.13 else "fairly regular"
    color = _color_name(r, g, b)

    parts = [
        f"{color} colouring",
        f"{texture} surface",
        f"the affected patch covers ~{affected_area_pct:.0f}% of the image",
        f"{border} borders",
    ]
    if redness > 0.52:
        parts.append("appears red/inflamed")
    summary = ", ".join(parts) + "."

    return {
        "dominant_color": color,
        "redness": round(min(redness, 1.5), 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "texture": texture,
        "edge_density": round(edge_density, 3),
        "affected_area_pct": round(affected_area_pct, 1),
        "border": border,
        "summary": summary,
    }
