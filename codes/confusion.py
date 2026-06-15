import torch
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
import os

# --- CONFIG ---
MODEL_PATH = r"C:\Users\ossam\Documents\fyp\codes\convnext_skin_fyp_new.pth"
DATA_DIR = r"C:\Users\ossam\Documents\fyp\final dataset\Augmented dataset\splitted\val"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 1. Load Model
model = models.convnext_tiny()
model.classifier[2] = torch.nn.Linear(model.classifier[2].in_features, 8)
model.load_state_dict(torch.load(MODEL_PATH))
model.to(DEVICE).eval()

# 2. Prepare Data
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])
val_dataset = datasets.ImageFolder(DATA_DIR, transform=transform)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
class_names = val_dataset.classes

# 3. Collect Predictions
all_preds, all_labels = [], []
with torch.no_grad():
    for inputs, labels in val_loader:
        inputs = inputs.to(DEVICE)
        outputs = model(inputs)
        _, preds = torch.max(outputs, 1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

# 4. Plot Heatmap
cm = confusion_matrix(all_labels, all_preds)
plt.figure(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=class_names, yticklabels=class_names)
plt.title('Skin Disease Confusion Matrix')
plt.ylabel('Actual Disease')
plt.xlabel('Predicted Disease')
plt.savefig('confusion_matrix.png')
plt.show()

print("\nDetailed Report:\n", classification_report(all_labels, all_preds, target_names=class_names))