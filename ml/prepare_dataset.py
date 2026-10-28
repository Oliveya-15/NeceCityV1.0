"""Turns a flat folder of photos + label files into the folder layout YOLO needs.

Input folder (what you have):          Output folder (what YOLO needs):
    P1.jpg  P1.txt                         images/train/...   labels/train/...
    G3.jpg  G3.txt                         images/val/...     labels/val/...
    ...

Each .txt file has one line per object:   class_number x_centre y_centre width height
(all five numbers after the class are fractions from 0 to 1 of the photo size).

Run from the ml folder:
    python prepare_dataset.py --source ../NeceCity_Train_Photos --output data/real_dataset

What it does:
  1. checks every label file (class number 0-5, five numbers, values between 0 and 1)
  2. splits the photos into 80% training and 20% validation
     - the split is "stratified": every problem type is represented in the validation set
     - the random seed is fixed (42), so you get the same split every time
  3. prints how many photos and boxes each class has
"""
import argparse
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

CLASS_NAMES = ["pothole", "road_damage", "garbage", "waterlogging", "damaged_road_sign", "open_drain"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VALIDATION_SHARE = 0.20
SEED = 42


def read_labels(label_file: Path) -> list[list[float]]:
    """Reads one label file and stops with a clear message if something is wrong."""
    rows = []
    for number, line in enumerate(label_file.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            raise SystemExit(f"{label_file.name} line {number}: expected 5 numbers, found {len(parts)}")
        class_id = int(float(parts[0]))
        values = [float(v) for v in parts[1:]]
        if not 0 <= class_id < len(CLASS_NAMES):
            raise SystemExit(f"{label_file.name} line {number}: class {class_id} is not between 0 and {len(CLASS_NAMES) - 1}")
        if any(v < 0 or v > 1 for v in values):
            raise SystemExit(f"{label_file.name} line {number}: box values must be between 0 and 1")
        rows.append([class_id] + values)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Split labelled photos into train and val folders.")
    parser.add_argument("--source", required=True, help="folder with the photos and the .txt label files")
    parser.add_argument("--output", default="data/real_dataset", help="folder to create")
    args = parser.parse_args()

    source, output = Path(args.source), Path(args.output)
    photos = sorted(p for p in source.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
    if not photos:
        raise SystemExit(f"No photos found in {source}")

    # read and check every photo's labels
    labels = {}
    for photo in photos:
        label_file = photo.with_suffix(".txt")
        if not label_file.exists():
            raise SystemExit(f"Missing label file for {photo.name} (expected {label_file.name})")
        rows = read_labels(label_file)
        if not rows:
            raise SystemExit(f"{label_file.name} is empty - every photo needs at least one box")
        labels[photo] = rows

    # group photos by their most common class, then pick validation photos from each group
    groups = defaultdict(list)
    for photo, rows in labels.items():
        most_common_class = Counter(int(r[0]) for r in rows).most_common(1)[0][0]
        groups[most_common_class].append(photo)

    rng = random.Random(SEED)
    validation = set()
    for class_id, members in sorted(groups.items()):
        rng.shuffle(members)
        take = max(1, round(len(members) * VALIDATION_SHARE))
        validation.update(members[:take])

    # write the folders
    if output.exists():
        shutil.rmtree(output)
    for photo in photos:
        part = "val" if photo in validation else "train"
        (output / "images" / part).mkdir(parents=True, exist_ok=True)
        (output / "labels" / part).mkdir(parents=True, exist_ok=True)
        shutil.copy2(photo, output / "images" / part / photo.name)
        shutil.copy2(photo.with_suffix(".txt"), output / "labels" / part / (photo.stem + ".txt"))

    # summary
    print(f"Photos: {len(photos)}  (train {len(photos) - len(validation)}, val {len(validation)})")
    print(f"{'class':20s} {'photos':>7s} {'boxes':>7s} {'boxes in val':>13s}")
    for class_id, name in enumerate(CLASS_NAMES):
        photo_count = sum(any(int(r[0]) == class_id for r in rows) for rows in labels.values())
        box_count = sum(int(r[0]) == class_id for rows in labels.values() for r in rows)
        val_boxes = sum(int(r[0]) == class_id for p in validation for r in labels[p])
        print(f"{name:20s} {photo_count:7d} {box_count:7d} {val_boxes:13d}")
    print(f"Done. Dataset written to {output}")


if __name__ == "__main__":
    main()
