"""
NullSense - Phase 6: Pothole Fine-Tuning
=========================================
Fine-tunes the pretrained YOLOv8n model on the local pothole dataset.

Strategy:
  - Start from yolov8n.pt (pretrained on COCO 80 classes)
  - Train on the pothole dataset in 'training data/pothole/'
  - The resulting model detects BOTH original COCO classes AND potholes
  - Output saved to phase6_training/runs/pothole/ and models/

Usage:
  python phase6_training/train_potholes.py
  python phase6_training/train_potholes.py --epochs 100
  python phase6_training/train_potholes.py --validate-only models/nullsense_potholes.pt

Owner: Lead | Status: Phase 6
Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

import os
import sys
import shutil
import yaml

# ensure project root is on the path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

# paths
DATASET_DIR = os.path.join(ROOT, 'training data', 'pothole')
BASE_MODEL  = os.path.join(ROOT, 'yolov8n.pt')
OUTPUT_DIR  = os.path.join(ROOT, 'phase6_training', 'runs', 'pothole')
MODELS_DIR  = os.path.join(ROOT, 'models')
FIXED_YAML  = os.path.join(ROOT, 'phase6_training', 'pothole_data.yaml')


def fix_yaml():
    """Rewrite data.yaml with absolute paths so training works from any CWD."""
    src_yaml = os.path.join(DATASET_DIR, 'data.yaml')
    with open(src_yaml) as f:
        data = yaml.safe_load(f)

    data['train'] = os.path.join(DATASET_DIR, 'train', 'images').replace('\\', '/')
    data['val']   = os.path.join(DATASET_DIR, 'valid', 'images').replace('\\', '/')
    data['test']  = os.path.join(DATASET_DIR, 'test',  'images').replace('\\', '/')

    os.makedirs(os.path.dirname(FIXED_YAML), exist_ok=True)
    with open(FIXED_YAML, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)

    print(f"[Step 1] Fixed data.yaml -> {FIXED_YAML}")
    print(f"         train  : {data['train']}")
    print(f"         val    : {data['val']}")
    print(f"         nc     : {data['nc']}  classes: {data['names']}")
    return FIXED_YAML


def train(data_yaml, epochs=50, patience=10):
    from ultralytics import YOLO
    import torch

    device = 0 if torch.cuda.is_available() else 'cpu'
    device_label = 'GPU' if device == 0 else 'CPU (slow - use Google Colab for GPU)'

    print(f"\n[Step 2] Fine-tuning YOLOv8n on pothole dataset")
    print(f"         Base model : {BASE_MODEL}")
    print(f"         Epochs     : {epochs}")
    print(f"         Device     : {device_label}\n")

    if device == 'cpu':
        print("  WARNING: No GPU. Training on CPU will be very slow.")
        print("  Tip: Use Google Colab with free T4 GPU for 10x speed.\n")

    model = YOLO(BASE_MODEL)

    results = model.train(
        data       = data_yaml,
        epochs     = epochs,
        imgsz      = 640,
        batch      = 8 if device == 'cpu' else 16,
        name       = 'pothole',
        project    = OUTPUT_DIR,
        pretrained = True,
        patience   = patience,
        save       = True,
        device     = device,
        verbose    = True,
        plots      = True,
        # ── Advanced Augmentations for Fine-Tuning ──
        mosaic     = 1.0,   # Stitch 4 images together to learn scale variation
        mixup      = 0.1,   # Overlay images to improve robustness
        degrees    = 15.0,  # Rotate images slightly
        hsv_s      = 0.5,   # Adjust saturation for lighting changes
    )

    # Locate best.pt - YOLO appends numbers if run folder already exists
    best_src = os.path.join(OUTPUT_DIR, 'pothole', 'weights', 'best.pt')
    if not os.path.exists(best_src):
        for i in range(2, 20):
            alt = os.path.join(OUTPUT_DIR, f'pothole{i}', 'weights', 'best.pt')
            if os.path.exists(alt):
                best_src = alt
                break

    print(f"\n[Step 2] Training complete. Best weights -> {best_src}")
    return best_src


def validate(model_path, data_yaml):
    from ultralytics import YOLO

    print(f"\n[Step 3] Validating: {model_path}")
    model = YOLO(model_path)

    print("  Model classes:")
    for i, name in model.names.items():
        print(f"    {i}: {name}")

    metrics = model.val(data=data_yaml, verbose=False)
    map50   = metrics.box.map50
    map5095 = metrics.box.map
    target  = 0.65

    status = "MEETS" if map50 >= target else "BELOW"
    print(f"\n  mAP50    : {map50:.3f}  ({status} target {target})")
    print(f"  mAP50-95 : {map5095:.3f}")

    if map50 < target:
        print("\n  Suggestions: increase --epochs, check label quality, add images.")


def save_model(best_src):
    os.makedirs(MODELS_DIR, exist_ok=True)
    dst = os.path.join(MODELS_DIR, 'nullsense_potholes.pt')
    shutil.copy2(best_src, dst)
    print(f"\n[Step 4] Model saved -> {dst}")
    print(f"  Update shared/config.py:")
    print(f"    MODEL_PATH = 'models/nullsense_potholes.pt'")
    return dst


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='NullSense Phase 6 - Pothole Fine-Tuning')
    parser.add_argument('--epochs',        type=int, default=150)
    parser.add_argument('--patience',      type=int, default=10)
    parser.add_argument('--validate-only', type=str, default=None, metavar='MODEL_PATH',
                        help='Skip training, validate an existing model')
    args = parser.parse_args()

    print("=" * 55)
    print("  NullSense Phase 6 - Pothole Fine-Tuning")
    print("=" * 55)

    data_yaml = fix_yaml()

    if args.validate_only:
        validate(args.validate_only, data_yaml)
    else:
        best = train(data_yaml, epochs=args.epochs, patience=args.patience)

        if best and os.path.exists(best):
            validate(best, data_yaml)
            saved = save_model(best)
            print(f"\n{'='*55}")
            print(f"  Done! Pothole-aware model saved to:")
            print(f"  {saved}")
            print(f"{'='*55}")
        else:
            print("\nWARNING: best.pt not found. Check phase6_training/runs/pothole/")
