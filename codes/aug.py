import cv2
import numpy as np
import os
import glob

def batch_augment(input_folder):
    # Create an output directory so we don't overwrite originals
    output_folder = os.path.join(input_folder, "augmented_results")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Find all common image files
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(input_folder, ext)))

    print(f"Found {len(image_files)} images. Starting augmentation...")

    for img_path in image_files:
        img = cv2.imread(img_path)
        if img is None: continue
        
        base_name = os.path.basename(img_path).split('.')[0]
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)

        # --- Transformations ---
        
        # 1 & 2. Rotations
        m_p15 = cv2.getRotationMatrix2D(center, 15, 1.0)
        m_m15 = cv2.getRotationMatrix2D(center, -15, 1.0)
        augs = {
            "rot_p15": cv2.warpAffine(img, m_p15, (w, h)),
            "rot_m15": cv2.warpAffine(img, m_m15, (w, h)),
            "flip_h": cv2.flip(img, 1),
            "flip_v": cv2.flip(img, 0),
            "bright": cv2.convertScaleAbs(img, alpha=1.2, beta=30),
            "dark": cv2.convertScaleAbs(img, alpha=0.7, beta=0)
        }

        # 3. CLAHE
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l_final = clahe.apply(l)
        augs["clahe"] = cv2.cvtColor(cv2.merge((l_final, a, b)), cv2.COLOR_LAB2BGR)

        # 4. Saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype("float32")
        h_chan, s_chan, v_chan = cv2.split(hsv)
        s_chan = np.clip(s_chan * 1.5, 0, 255)
        augs["sat"] = cv2.cvtColor(cv2.merge([h_chan, s_chan, v_chan]).astype("uint8"), cv2.COLOR_HSV2BGR)

        # Save all versions
        for suffix, processed in augs.items():
            save_path = os.path.join(output_folder, f"{base_name}_{suffix}.jpg")
            cv2.imwrite(save_path, processed)

    print(f"Done! Check the folder: {output_folder}")

# JUST CHANGE THIS PATH:
path_to_my_images = r'C:\Users\ossam\Documents\fyp\final dataset\Seborrheic Keratoses'
batch_augment(path_to_my_images)