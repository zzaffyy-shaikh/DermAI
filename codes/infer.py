import torch
from torchvision import models, transforms
from PIL import Image
import torch.nn.functional as F
import os

# ==========================================
# 1. SET YOUR PATHS HERE
# ==========================================
MODEL_PATH = r"C:\Users\ossam\Documents\fyp\codes\convnext_skin_fyp_new.pth"
IMAGE_PATH = r"C:\Users\ossam\Documents\fyp\testing photos\download (1).jpg"
# Point this to your training folder to get the correct class order automatically
TRAIN_DIR = r"C:\Users\ossam\Documents\fyp\new dataset\Augmented\splitted\train"

# ==========================================
# 2. SETUP & DYNAMIC CLASS LOADING
# ==========================================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Get classes from folder (Ensures order and count are 100% correct)
if os.path.exists(TRAIN_DIR):
    class_names = sorted([f for f in os.listdir(TRAIN_DIR) if os.path.isdir(os.path.join(TRAIN_DIR, f))])
    num_classes = len(class_names)
    print(f"✅ Found {num_classes} classes: {class_names}")
else:
    # Fallback if folder isn't found - ensure this matches your training exactly!
    class_names = ['Acne', 'Atopic Dermatitis','Eczema','Healthy Skin', 'Hyper Pigmentation', 'Melanoma', 'Psoriasis', 'Seborrheic Keratosis']
    num_classes = len(class_names)

# ==========================================
# 3. MODEL LOADING
# ==========================================
model = models.convnext_tiny()
# Dynamic linear layer based on detected classes
model.classifier[2] = torch.nn.Linear(model.classifier[2].in_features, num_classes)

# Added weights_only=True to fix the warning we saw earlier
model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
model.to(device)
model.eval()

transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# ==========================================
# 4. PREDICTION FUNCTION
# ==========================================
def predict(img_path):
    if not os.path.exists(img_path):
        print(f"❌ Error: Image not found at {img_path}")
        return

    img = Image.open(img_path).convert('RGB')
    input_tensor = transform(img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        output = model(input_tensor)
        probabilities = F.softmax(output, dim=1)
        prob, pred = torch.max(probabilities, 1)
        
    print("\n--- Prediction Result ---")
    print(f"Disease: {class_names[pred.item()]}")
    print(f"Confidence: {prob.item()*100:.2f}%")
    print("-------------------------\n")

if __name__ == "__main__":
    predict(IMAGE_PATH)