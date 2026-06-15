"""Train ConvNeXt-Tiny on the LEAKAGE-FREE split from prepare_data.py.

Improvements over the original train.py:
  - trains on the clean split (train already augmented offline; val stays clean)
  - class-weighted loss to handle imbalance
  - saves the BEST checkpoint by validation macro-F1 (not just the last epoch)
  - writes classes.json (consumed by the backend)

Run:  python train_v2.py
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from tqdm import tqdm

DATA_DIR = Path(r"C:\Users\ossam\Documents\fyp\final dataset\prepared")
OUT_MODEL = Path(r"C:\Users\ossam\Documents\fyp\codes\convnext_skin_best.pth")
OUT_CLASSES = Path(r"C:\Users\ossam\Documents\fyp\backend\classes.json")
BATCH_SIZE = 32   # conservative for 6 GB VRAM (esp. if the backend is also loaded)
NUM_EPOCHS = 20
LR = 1e-4
URGENT = ["Melanoma"]
DISPLAY = {"Hyper Pigmintation": "Hyper Pigmentation"}

MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def build_loaders():
    tfm = {
        "train": transforms.Compose([
            transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]),
        "val": transforms.Compose([
            transforms.Resize(256), transforms.CenterCrop(224),
            transforms.ToTensor(), transforms.Normalize(MEAN, STD),
        ]),
    }
    ds = {x: datasets.ImageFolder(DATA_DIR / x, tfm[x]) for x in ["train", "val"]}
    dl = {x: DataLoader(ds[x], batch_size=BATCH_SIZE, shuffle=(x == "train"),
                        num_workers=4, pin_memory=True) for x in ["train", "val"]}
    return ds, dl


def class_weights(dataset) -> torch.Tensor:
    counts = [0] * len(dataset.classes)
    for _, label in dataset.samples:
        counts[label] += 1
    total = sum(counts)
    return torch.tensor([total / (len(counts) * c) if c else 0.0 for c in counts], dtype=torch.float32)


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.backends.cudnn.benchmark = True
    ds, dl = build_loaders()
    classes = ds["train"].classes
    print(f"Device: {device} | {len(classes)} classes: {classes}")

    model = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    model.classifier[2] = nn.Linear(model.classifier[2].in_features, len(classes))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights(ds["train"]).to(device))
    optimizer = optim.AdamW(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS)
    scaler = torch.amp.GradScaler("cuda")

    best_f1 = -1.0
    for epoch in range(NUM_EPOCHS):
        print(f"\nEpoch {epoch + 1}/{NUM_EPOCHS}")
        for phase in ["train", "val"]:
            model.train() if phase == "train" else model.eval()
            loss_sum, y_true, y_pred = 0.0, [], []
            for inputs, labels in tqdm(dl[phase], desc=phase.upper(), leave=False):
                inputs, labels = inputs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
                optimizer.zero_grad()
                with torch.set_grad_enabled(phase == "train"), torch.amp.autocast("cuda"):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                if phase == "train":
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                loss_sum += loss.item() * inputs.size(0)
                y_true += labels.cpu().tolist()
                y_pred += outputs.argmax(1).cpu().tolist()

            n = len(ds[phase])
            acc = accuracy_score(y_true, y_pred)
            f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
            print(f"  {phase.upper():5s} loss={loss_sum / n:.4f} acc={acc:.2%} f1={f1:.4f}")

            if phase == "val" and f1 > best_f1:
                best_f1 = f1
                torch.save(model.state_dict(), OUT_MODEL)
                print(f"  [*] new best (f1={f1:.4f}) saved -> {OUT_MODEL.name}")
        scheduler.step()

    OUT_CLASSES.parent.mkdir(parents=True, exist_ok=True)
    OUT_CLASSES.write_text(json.dumps({
        "_comment": "Order matches ImageFolder training order. Do not reorder.",
        "classes": classes, "display": DISPLAY, "urgent": URGENT,
    }, indent=2), encoding="utf-8")
    print(f"\nBest val macro-F1: {best_f1:.4f}\nclasses.json -> {OUT_CLASSES}")


if __name__ == "__main__":
    main()
