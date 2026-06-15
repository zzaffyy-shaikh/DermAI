"""Evaluate the trained model on the CLEAN test split and suggest decision-gate
thresholds (confidence + entropy) for the backend.

Produces:
  - confusion_matrix_test.png
  - classification report (printed)
  - suggested DERMAI_CONFIDENCE_THRESHOLD and DERMAI_ENTROPY_THRESHOLD

Run:  python evaluate_and_calibrate.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

MODEL_PATH = Path(r"C:\Users\ossam\Documents\fyp\codes\convnext_skin_best.pth")
TEST_DIR = Path(r"C:\Users\ossam\Documents\fyp\final dataset\prepared\test")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def main() -> None:
    tfm = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224),
        transforms.ToTensor(), transforms.Normalize(MEAN, STD),
    ])
    ds = datasets.ImageFolder(TEST_DIR, tfm)
    dl = DataLoader(ds, batch_size=32, shuffle=False, num_workers=4)
    classes = ds.classes

    model = models.convnext_tiny()
    model.classifier[2] = nn.Linear(model.classifier[2].in_features, len(classes))
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True))
    model.to(DEVICE).eval()

    y_true, y_pred, confidences, entropies, correct = [], [], [], [], []
    with torch.inference_mode():
        for inputs, labels in dl:
            probs = F.softmax(model(inputs.to(DEVICE)), dim=1)
            conf, pred = probs.max(1)
            ent = -(probs * torch.log(probs + 1e-9)).sum(1)
            y_true += labels.tolist()
            y_pred += pred.cpu().tolist()
            confidences += conf.cpu().tolist()
            entropies += ent.cpu().tolist()
            correct += (pred.cpu() == labels).tolist()

    # confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=classes, yticklabels=classes)
    plt.title("DermAI Confusion Matrix (clean test set)")
    plt.ylabel("Actual"); plt.xlabel("Predicted"); plt.tight_layout()
    plt.savefig("confusion_matrix_test.png")
    print("Saved confusion_matrix_test.png")

    print("\n" + classification_report(y_true, y_pred, target_names=classes, zero_division=0))

    # threshold suggestion: separate correct vs incorrect predictions
    confidences = np.array(confidences); entropies = np.array(entropies); correct = np.array(correct)
    if (~correct).any():
        # set confidence threshold near the 10th percentile of CORRECT confidences
        tau = float(np.percentile(confidences[correct], 10))
        h = float(np.percentile(entropies[correct], 90))
    else:
        tau, h = 0.60, 1.60
    print("\n--- Suggested decision-gate thresholds ---")
    print(f"DERMAI_CONFIDENCE_THRESHOLD={tau:.2f}")
    print(f"DERMAI_ENTROPY_THRESHOLD={h:.2f}")
    print("(Set these in backend/.env, then sanity-check on a few out-of-class images.)")

    Path("calibration.json").write_text(json.dumps(
        {"confidence_threshold": round(tau, 3), "entropy_threshold": round(h, 3)}, indent=2))


if __name__ == "__main__":
    main()
