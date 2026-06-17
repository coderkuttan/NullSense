"""
NullSense — Phase 6: Indian Dataset & Custom Model Training
============================================================
Run on Google Colab (free GPU) for training.
Steps:
  1. Create free account at roboflow.com
  2. Download datasets listed below
  3. Upload this file + datasets to Google Colab
  4. Run each step in order

Owner: Friend 1 (Dataset + Training)
Status: IN PROGRESS

Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

# ============================================================
# STEP 0: Run in Google Colab — install dependencies
# ============================================================
# !pip install ultralytics roboflow pyyaml

# ============================================================
# STEP 1: Mount Google Drive
# ============================================================
# from google.colab import drive
# drive.mount('/content/drive')

# ============================================================
# STEP 2: Download Indian datasets from Roboflow
# ============================================================
"""
Manual download steps (free):
1. Go to universe.roboflow.com
2. Search each term below
3. Click dataset → Versions → Export → YOLOv8 → Download ZIP
4. Upload ZIPs to Google Colab

Datasets to download:
┌─────────────────────────────┬──────────────┬────────────┐
│ Search Term                 │ Min Images   │ Priority   │
├─────────────────────────────┼──────────────┼────────────┤
│ auto rickshaw detection     │ 500+         │ High       │
│ pothole detection india     │ 500+         │ High       │
│ cow road detection          │ 300+         │ High       │
│ stray dog detection         │ 300+         │ High       │
│ manhole detection           │ 200+         │ Medium     │
│ construction barrier        │ 200+         │ Medium     │
│ speed breaker india         │ 200+         │ Medium     │
└─────────────────────────────┴──────────────┴────────────┘
"""

import os
import shutil
import yaml


# ============================================================
# STEP 3: Merge all downloaded datasets
# ============================================================
def merge_datasets(dataset_folders, output='merged_dataset'):
    """
    Merges multiple YOLOv8 datasets into one.
    Each folder must have: train/images, train/labels,
    valid/images, valid/labels, data.yaml
    """
    os.makedirs(f'{output}/train/images', exist_ok=True)
    os.makedirs(f'{output}/train/labels', exist_ok=True)
    os.makedirs(f'{output}/valid/images', exist_ok=True)
    os.makedirs(f'{output}/valid/labels', exist_ok=True)

    all_classes   = []
    total_train   = 0
    total_valid   = 0

    for folder in dataset_folders:
        yaml_path = os.path.join(folder, 'data.yaml')
        if not os.path.exists(yaml_path):
            print(f"Skipping {folder} — no data.yaml found")
            continue

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        classes = data.get('names', [])
        print(f"\nProcessing: {folder}")
        print(f"  Classes: {classes}")

        for cls in classes:
            if cls not in all_classes:
                all_classes.append(cls)

        prefix = folder.replace('/', '_').replace(' ', '_')

        for split in ['train', 'valid']:
            img_dir = os.path.join(folder, split, 'images')
            lbl_dir = os.path.join(folder, split, 'labels')

            if not os.path.exists(img_dir):
                continue

            count = 0
            for img_file in os.listdir(img_dir):
                if not img_file.lower().endswith(
                        ('.jpg','.jpeg','.png')):
                    continue

                # Copy image
                src = os.path.join(img_dir, img_file)
                dst = os.path.join(output, split, 'images',
                    f'{prefix}_{img_file}')
                shutil.copy2(src, dst)

                # Copy + remap label
                lbl_file = os.path.splitext(img_file)[0] + '.txt'
                src_lbl  = os.path.join(lbl_dir, lbl_file)
                dst_lbl  = os.path.join(output, split, 'labels',
                    f'{prefix}_{lbl_file}')

                if os.path.exists(src_lbl):
                    with open(src_lbl) as f:
                        lines = f.readlines()
                    with open(dst_lbl, 'w') as f:
                        for line in lines:
                            parts = line.strip().split()
                            if parts:
                                old_cls = int(parts[0])
                                if old_cls < len(classes):
                                    new_cls = all_classes.index(
                                        classes[old_cls])
                                    f.write(f"{new_cls} " +
                                        " ".join(parts[1:]) + "\n")
                count += 1

            if split == 'train': total_train += count
            else:                total_valid += count
            print(f"  {split}: {count} images")

    # Write merged data.yaml
    merged = {
        'train': f'../{output}/train/images',
        'val':   f'../{output}/valid/images',
        'nc':    len(all_classes),
        'names': all_classes
    }
    with open(f'{output}/data.yaml', 'w') as f:
        yaml.dump(merged, f, default_flow_style=False)

    print(f"\n{'='*40}")
    print(f"Merge complete!")
    print(f"Total train images: {total_train}")
    print(f"Total valid images: {total_valid}")
    print(f"Total classes ({len(all_classes)}): {all_classes}")
    print(f"{'='*40}")
    return output


# ============================================================
# STEP 4: Train custom YOLOv8 model
# ============================================================
def train_model(data_yaml='merged_dataset/data.yaml'):
    from ultralytics import YOLO

    print("\nStarting NullSense custom model training...")
    print("This will take 30-60 minutes on Colab GPU\n")

    model = YOLO('yolov8n.pt')  # Start from pretrained

    results = model.train(
        data=data_yaml,
        epochs=50,
        imgsz=640,
        batch=16,
        name='nullsense_indian',
        pretrained=True,
        patience=10,
        save=True,
        device=0,        # GPU — use 'cpu' if no GPU
        verbose=True,
        plots=True,
    )

    best = 'runs/detect/nullsense_indian/weights/best.pt'
    print(f"\nTraining complete!")
    print(f"Best model: {best}")
    return best


# ============================================================
# STEP 5: Validate trained model
# ============================================================
def validate_model(model_path):
    from ultralytics import YOLO
    import numpy as np

    model = YOLO(model_path)

    print("\nModel classes:")
    for i, name in model.names.items():
        print(f"  {i}: {name}")

    # Test on dummy image
    dummy   = np.zeros((640, 640, 3), dtype='uint8')
    results = model(dummy, verbose=False)
    print(f"\nModel running OK")
    print(f"Use this path in config.py: MODEL_PATH = '{model_path}'")


# ============================================================
# STEP 6: Save to Google Drive
# ============================================================
def save_to_drive(model_path,
                  drive='/content/drive/MyDrive/NullSense/'):
    os.makedirs(drive, exist_ok=True)
    dst = os.path.join(drive, 'nullsense_best.pt')
    shutil.copy2(model_path, dst)
    print(f"\nModel saved to Google Drive: {dst}")
    print("Download it and place in NullSense/models/")
    print("Then update shared/config.py:")
    print("  MODEL_PATH = 'models/nullsense_best.pt'")


# ============================================================
# MAIN — Uncomment steps one by one on Colab
# ============================================================
if __name__ == '__main__':
    print("NullSense Phase 6 — Training Pipeline")
    print("Run on Google Colab with GPU for best results")
    print("="*50)

    # After downloading and unzipping datasets:
    # datasets = [
    #     'auto-rickshaw-1',
    #     'pothole-detection-3',
    #     'cow-road-1',
    #     'stray-dog-1',
    #     'manhole-1',
    # ]
    # merge_datasets(datasets)
    # model_path = train_model()
    # validate_model(model_path)
    # save_to_drive(model_path)

    print("Uncomment steps above and run on Google Colab")
