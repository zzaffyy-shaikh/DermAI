import splitfolders
import os

# 1. PATHS
# input_folder: Where your 6 folders currently are
# output_folder: Where the new train/val folders will be created
input_folder = r"C:\Users\ossam\Documents\fyp\final dataset\Augmented dataset" 
output_folder = r"C:\Users\ossam\Documents\fyp\final dataset\Augmented dataset\splitted"

# 2. PERFORM THE SPLIT
# ratio=(.8, .2) means 80% for training, 20% for validation
# seed=1337 ensures the split is reproducible every time you run it
splitfolders.ratio(input_folder, output=output_folder, seed=1337, ratio=(.8, .2), group_prefix=None, move=False)

print(f"✅ Split complete! Your data is now at: {output_folder}")
print(f"Classes found: {len(os.listdir(input_folder))}")