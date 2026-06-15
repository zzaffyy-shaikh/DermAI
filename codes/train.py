import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from tqdm import tqdm

# ==========================================
# CONFIGURATION
# ==========================================
ROOT_DATA_DIR = r"C:\Users\ossam\Documents\fyp\final dataset\Augmented dataset\splitted" 
BATCH_SIZE = 48  # Keep at 48 for RTX 4050 6GB VRAM
NUM_EPOCHS = 20
LEARNING_RATE = 1e-4

def train_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Training on: {torch.cuda.get_device_name(0)}")

    # 1. DATA TRANSFORMATIONS
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.ColorJitter(brightness=0.1, contrast=0.1), # Added for robustness
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    # 2. DATA LOADERS
    image_datasets = {x: datasets.ImageFolder(os.path.join(ROOT_DATA_DIR, x), data_transforms[x]) for x in ['train', 'val']}
    
    # DYNAMIC CLASS DETECTION
    class_names = image_datasets['train'].classes
    num_classes = len(class_names)
    print(f"✅ Detected {num_classes} classes: {class_names}")

    dataloaders = {x: DataLoader(image_datasets[x], batch_size=BATCH_SIZE, shuffle=True, 
                                num_workers=4, pin_memory=True) for x in ['train', 'val']}

    # 3. MODEL (Dynamic Output Layer)
    model = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    
    # Change from 6 to num_classes (9) automatically
    model.classifier[2] = nn.Linear(model.classifier[2].in_features, num_classes) 
    model = model.to(device)

    # 4. OPTIMIZER & SCALER
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    scaler = torch.amp.GradScaler('cuda') 

    # 5. TRAINING LOOP
    for epoch in range(NUM_EPOCHS):
        print(f"\nEpoch {epoch+1}/{NUM_EPOCHS}")
        
        for phase in ['train', 'val']:
            model.train() if phase == 'train' else model.eval()
            running_loss, y_true, y_pred = 0.0, [], []
            
            pbar = tqdm(dataloaders[phase], desc=f"{phase.upper()}", leave=False)

            for inputs, labels in pbar:
                inputs, labels = inputs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    with torch.amp.autocast('cuda'): 
                        outputs = model(inputs)
                        loss = criterion(outputs, labels)
                    
                    if phase == 'train':
                        scaler.scale(loss).backward()
                        scaler.step(optimizer)
                        scaler.update()

                _, preds = torch.max(outputs, 1)
                running_loss += loss.item() * inputs.size(0)
                y_true.extend(labels.cpu().numpy())
                y_pred.extend(preds.cpu().numpy())
                
                # Update progress bar with loss
                if phase == 'train':
                    pbar.set_postfix({'loss': f"{loss.item():.4f}"})

            epoch_loss = running_loss / len(image_datasets[phase])
            acc = accuracy_score(y_true, y_pred)
            f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
            
            print(f"📊 {phase.upper()} Loss: {epoch_loss:.4f} | Acc: {acc:.2%} | F1: {f1:.4f}")

    # Save the model
    torch.save(model.state_dict(), "convnext_skin_fyp_new.pth")
    print(f"✅ Model Saved with {num_classes} classes!")

if __name__ == "__main__":
    # Optimize CUDA for the 4050
    torch.backends.cudnn.benchmark = True 
    train_model()