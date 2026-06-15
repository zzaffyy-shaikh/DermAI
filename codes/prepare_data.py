"""Leakage-free data preparation: SPLIT FIRST on originals, then augment TRAIN ONLY.

This fixes the critical bug where augmentation was applied before the split, leaking
variants of the same photo across train and val (which inflated accuracy).

Output layout:
    OUTPUT/
      train/<class>/   <- originals + their augmentations
      val/<class>/     <- clean originals only
      test/<class>/    <- clean originals only

Run:  python prepare_data.py
"""
from __future__ import annotations

import os
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

# ---- CONFIG ----
INPUT_DIR = Path(r"C:\Users\ossam\Documents\fyp\final dataset")   # holds the 8 class folders (originals)
OUTPUT_DIR = Path(r"C:\Users\ossam\Documents\fyp\final dataset\prepared")
CLASS_NAMES = ["Acne", "Atopic Dermatitis", "Eczema", "Healthy",
               "Hyper Pigmintation", "Melanoma", "Psoriasis", "Seborrheic Keratoses"]
SPLIT = (0.70, 0.15, 0.15)   # train / val / test
SEED = 1337
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def augment(img):
    """Return a dict of augmented variants (same ops as the original aug.py)."""
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    out = {
        "rot_p15": cv2.warpAffine(img, cv2.getRotationMatrix2D(center, 15, 1.0), (w, h)),
        "rot_m15": cv2.warpAffine(img, cv2.getRotationMatrix2D(center, -15, 1.0), (w, h)),
        "flip_h": cv2.flip(img, 1),
        "flip_v": cv2.flip(img, 0),
        "bright": cv2.convertScaleAbs(img, alpha=1.2, beta=30),
        "dark": cv2.convertScaleAbs(img, alpha=0.7, beta=0),
    }
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    out["clahe"] = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype("float32")
    hh, s, v = cv2.split(hsv)
    s = np.clip(s * 1.5, 0, 255)
    out["sat"] = cv2.cvtColor(cv2.merge([hh, s, v]).astype("uint8"), cv2.COLOR_HSV2BGR)
    return out


def collect_originals(class_dir: Path) -> list[Path]:
    """Image files directly inside a class folder (ignores any nested aug subfolders)."""
    return [p for p in class_dir.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS]


def main() -> None:
    random.seed(SEED)
    if OUTPUT_DIR.exists():
        print(f"Removing existing {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)

    totals = {"train": 0, "val": 0, "test": 0, "train_aug": 0}

    for cls in CLASS_NAMES:
        files = collect_originals(INPUT_DIR / cls)
        if not files:
            print(f"[!] No images for class '{cls}' - skipping")
            continue
        random.shuffle(files)

        n = len(files)
        n_tr = int(n * SPLIT[0])
        n_va = int(n * SPLIT[1])
        parts = {
            "train": files[:n_tr],
            "val": files[n_tr:n_tr + n_va],
            "test": files[n_tr + n_va:],
        }

        for split, items in parts.items():
            dst = OUTPUT_DIR / split / cls
            dst.mkdir(parents=True, exist_ok=True)
            for src in items:
                shutil.copy2(src, dst / src.name)
                totals[split] += 1
                # augment TRAIN only
                if split == "train":
                    img = cv2.imread(str(src))
                    if img is None:
                        continue
                    stem = src.stem
                    for suffix, aug in augment(img).items():
                        cv2.imwrite(str(dst / f"{stem}_{suffix}.jpg"), aug)
                        totals["train_aug"] += 1

        print(f"{cls:22s} total={n:5d} | train={len(parts['train'])} "
              f"val={len(parts['val'])} test={len(parts['test'])}")

    print("\n[OK] Done.")
    print(f"   train originals: {totals['train']}  (+{totals['train_aug']} augmented)")
    print(f"   val:   {totals['val']}  (clean)")
    print(f"   test:  {totals['test']}  (clean)")
    print(f"   output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
