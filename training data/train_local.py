"""
NullSense -- Local YOLO11 Training Script
Trains a YOLO11s model on 2 datasets:
  - pothole/        -> class 0: pothole
  - zebra_crossing/ -> class 1: zebra_crossing

Run from the 'training data' folder:
  python train_local.py
"""

import os
import glob
import shutil
import yaml

# ── CONFIG (edit these if needed) ────────────────────────────────────────────

SOURCE_ROOT = os.path.dirname(os.path.abspath(__file__))   # "training data/"
MERGED_DIR  = os.path.join(SOURCE_ROOT, "merged_dataset")

# Final class list -- index = class ID written into label files
CLASS_NAMES = ["pothole", "zebra_crossing", "stray_animals"]

# Training hyperparams
MODEL_SIZE  = "yolo11s.pt"
EPOCHS      = 150
IMG_SIZE    = 640
BATCH       = 32      # raise to 64 if GPU util looks low (you have 51 GB VRAM)
WORKERS     = 8       # dataloader workers
PROJECT_DIR = os.path.join(SOURCE_ROOT, "runs")
RUN_NAME    = "nullsense_all_classes_v1"

# ── HELPERS ───────────────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def merge_datasets():
    NAME_TO_ID = {name: i for i, name in enumerate(CLASS_NAMES)}
    NORM_TO_ID = {normalize(k): v for k, v in NAME_TO_ID.items()}

    print(f"Target classes ({len(CLASS_NAMES)}): {CLASS_NAMES}")
    print(f"Source root: {SOURCE_ROOT}\n")

    for split in ["train", "valid", "test"]:
        os.makedirs(f"{MERGED_DIR}/{split}/images", exist_ok=True)
        os.makedirs(f"{MERGED_DIR}/{split}/labels", exist_ok=True)

    class_folders = [
        f for f in sorted(os.listdir(SOURCE_ROOT))
        if os.path.isdir(os.path.join(SOURCE_ROOT, f))
        and not f.startswith((".", "_", "merged", "runs"))
    ]
    print(f"Dataset folders found: {class_folders}\n")

    summary = []

    for folder in class_folders:
        folder_path     = os.path.join(SOURCE_ROOT, folder)
        local_yaml_path = os.path.join(folder_path, "data.yaml")

        if not os.path.exists(local_yaml_path):
            print(f"[SKIP] {folder}: no data.yaml")
            continue

        with open(local_yaml_path) as f:
            local_yaml = yaml.safe_load(f)

        local_names = local_yaml.get("names", [])
        if isinstance(local_names, dict):
            local_names = [local_names[i] for i in sorted(local_names)]

        print(f"[INFO] {folder}: local classes = {local_names}")

        local_id_to_global_id = {}
        for local_id, local_name in enumerate(local_names):
            norm = normalize(local_name)
            if norm in NORM_TO_ID:
                gid = NORM_TO_ID[norm]
                local_id_to_global_id[local_id] = gid
                print(f"       [{local_id}] '{local_name}' -> global [{gid}] '{CLASS_NAMES[gid]}'")
            elif normalize(folder) in NORM_TO_ID:
                gid = NORM_TO_ID[normalize(folder)]
                local_id_to_global_id[local_id] = gid
                print(f"       [{local_id}] '{local_name}' (folder match) -> global [{gid}] '{CLASS_NAMES[gid]}'")
            else:
                print(f"       [WARN] '{local_name}' -> no match, skipping")

        if not local_id_to_global_id:
            print(f"[SKIP] {folder}: no matchable classes\n")
            continue

        n_img = n_lbl = 0
        for split in ["train", "valid", "test"]:
            img_dir = os.path.join(folder_path, split, "images")
            lbl_dir = os.path.join(folder_path, split, "labels")
            if not os.path.isdir(img_dir):
                continue

            for img_path in glob.glob(os.path.join(img_dir, "*")):
                fname     = os.path.basename(img_path)
                stem, ext = os.path.splitext(fname)
                new_stem  = f"{folder}__{stem}"

                shutil.copy(img_path, os.path.join(MERGED_DIR, split, "images", new_stem + ext))
                n_img += 1

                src_lbl = os.path.join(lbl_dir, stem + ".txt")
                dst_lbl = os.path.join(MERGED_DIR, split, "labels", new_stem + ".txt")

                if os.path.exists(src_lbl):
                    out_lines = []
                    with open(src_lbl) as f:
                        for line in f:
                            parts = line.strip().split()
                            if not parts:
                                continue
                            local_id = int(parts[0])
                            if local_id in local_id_to_global_id:
                                new_id = local_id_to_global_id[local_id]
                                # Keep only the first 5 fields (detect format: id cx cy w h)
                                # This drops any segmentation polygon coords if present
                                detect_parts = parts[1:5]
                                if len(detect_parts) == 4:
                                    out_lines.append(" ".join([str(new_id)] + detect_parts))
                    with open(dst_lbl, "w") as f:
                        f.write("\n".join(out_lines) + ("\n" if out_lines else ""))
                    n_lbl += 1
                else:
                    open(dst_lbl, "w").close()

        summary.append((folder, n_img, n_lbl))
        print(f"[OK]  {folder}: {n_img} images, {n_lbl} label files\n")

    print("Merge complete:")
    for folder, n_img, n_lbl in summary:
        print(f"  {folder}: {n_img} images, {n_lbl} label files")
    print()


def sanity_check():
    from collections import Counter
    print("Dataset split summary:")
    for split in ["train", "valid", "test"]:
        img_dir = os.path.join(MERGED_DIR, split, "images")
        lbl_dir = os.path.join(MERGED_DIR, split, "labels")
        n_img = len(glob.glob(os.path.join(img_dir, "*")))
        n_lbl = len(glob.glob(os.path.join(lbl_dir, "*.txt")))
        print(f"  {split}: {n_img} images, {n_lbl} label files")

    class_counts = Counter()
    for split in ["train", "valid", "test"]:
        for lbl_file in glob.glob(os.path.join(MERGED_DIR, split, "labels", "*.txt")):
            with open(lbl_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        class_counts[int(parts[0])] += 1

    print("\nAnnotation count per class:")
    for i, name in enumerate(CLASS_NAMES):
        print(f"  [{i}] {name}: {class_counts.get(i, 0)}")

    missing = [CLASS_NAMES[i] for i in range(len(CLASS_NAMES)) if class_counts.get(i, 0) == 0]
    if missing:
        print(f"\n[WARN] Zero annotations for: {missing}")
    print()


def write_yaml():
    dataset_dir = os.path.abspath(MERGED_DIR)
    data_yaml = {
        "path"  : dataset_dir,
        "train" : "train/images",
        "val"   : "valid/images",
        "test"  : "test/images",
        "nc"    : len(CLASS_NAMES),
        "names" : CLASS_NAMES,
    }
    yaml_path = os.path.join(dataset_dir, "data.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(data_yaml, f, default_flow_style=False, sort_keys=False)
    print(f"Wrote {yaml_path}")
    print(open(yaml_path).read())
    return yaml_path


def train(yaml_path):
    import torch
    from ultralytics import YOLO

    print("=" * 60)
    print(f"CUDA : {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU  : {torch.cuda.get_device_name(0)}")
        print(f"VRAM : {round(torch.cuda.get_device_properties(0).total_memory/1e9,1)} GB")
    print(f"Model: {MODEL_SIZE}  Epochs: {EPOCHS}  Batch: {BATCH}  Img: {IMG_SIZE}")
    print("=" * 60)

    device = 0 if torch.cuda.is_available() else "cpu"
    model  = YOLO(MODEL_SIZE)

    results = model.train(
        data      = yaml_path,
        epochs    = EPOCHS,
        imgsz     = IMG_SIZE,
        batch     = BATCH,
        project   = PROJECT_DIR,
        name      = RUN_NAME,
        patience  = 30,
        device    = device,
        workers   = WORKERS,
        optimizer = "auto",
        cos_lr    = True,
        augment   = True,
        mosaic    = 1.0,
        mixup     = 0.1,
        plots     = True,
        task      = "detect",
    )

    print("\nTraining complete!")
    save_dir = str(results.save_dir)
    best = os.path.join(save_dir, "weights", "best.pt")
    print(f"Best weights: {best}")
    return best, save_dir


def validate(best_weights, yaml_path):
    from ultralytics import YOLO
    val_model = YOLO(best_weights)
    metrics   = val_model.val(data=yaml_path, imgsz=IMG_SIZE, split="val")
    print(f"\nmAP50    : {metrics.box.map50:.4f}")
    print(f"mAP50-95 : {metrics.box.map:.4f}")
    print("Per-class mAP50-95:")
    for i, name in enumerate(CLASS_NAMES):
        try:
            print(f"  {name}: {metrics.box.maps[i]:.4f}")
        except IndexError:
            pass
    return val_model


def export_onnx(val_model):
    onnx_path = val_model.export(format="onnx", imgsz=IMG_SIZE, opset=12, simplify=True)
    print(f"\nExported ONNX: {onnx_path}")
    print("\nAll done!")


# ── ENTRY POINT (required on Windows for multiprocessing) ────────────────────

if __name__ == "__main__":
    # Step 1: Merge datasets (skip if already done)
    merged_train = os.path.join(MERGED_DIR, "train", "images")
    if os.path.isdir(merged_train) and len(glob.glob(os.path.join(merged_train, "*"))) > 0:
        print(f"[INFO] Merged dataset already exists at {MERGED_DIR}, skipping merge.")
        print("       Delete the 'merged_dataset' folder to force a re-merge.\n")
    else:
        merge_datasets()

    # Step 2: Sanity check
    sanity_check()

    # Step 3: Write data.yaml
    yaml_path = write_yaml()

    # Step 4: Train
    best_weights, save_dir = train(yaml_path)

    # Step 5: Validate
    val_model = validate(best_weights, yaml_path)

    # Step 6: Export ONNX
    export_onnx(val_model)
