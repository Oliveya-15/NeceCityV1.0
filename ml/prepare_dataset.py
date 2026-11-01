"""Turns a flat folder of photos + label files into the folder layout YOLO needs.

Input folder (what you have):          Output folder (what YOLO needs):
    P1.jpg  P1.txt                         images/train/...   labels/train/...
    G3.jpg  G3.txt                         images/val/...     labels/val/...
    ...

Each .txt file has one line per object:   class_number x_centre y_centre width height
(all five numbers after the class are fractions from 0 to 1 of the photo size).

Run from the ml folder:
    python prepare_dataset.py --source ../photos --output data/real_dataset
    python prepare_dataset.py --source ../photos --negatives ../negatives --output data/real_dataset

NEGATIVE photos are photos that contain NONE of the six problems (a clean road, trees, plants, a wall...).
They teach the model what NOT to flag, which is the best cure for false alarms.
Put them in the --negatives folder (photos only, no .txt files needed). They get an empty label file.
A photo that has an EMPTY .txt file in the source folder is treated as a negative too.

What it does:
  1. checks every label file (class number 0-5, five numbers, values between 0 and 1)
  2. splits the photos into 80% training and 20% validation
     - the split is "stratified": every problem type (and the negatives) is represented in validation
     - the random seed is fixed (42), so you get the same split every time
  3. prints how many photos and boxes each class has, and warns about classes with too few photos
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
MIN_PHOTOS_PER_CLASS = 100   # below this the model usually gives many false alarms or misses


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


def list_photos(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Split labelled photos into train and val folders.")
    parser.add_argument("--source", required=True, help="folder with the photos and the .txt label files")
    parser.add_argument("--negatives", help="optional folder of photos that contain none of the problems")
    parser.add_argument("--output", default="data/real_dataset", help="folder to create")
    args = parser.parse_args()

    source, output = Path(args.source), Path(args.output)
    photos = list_photos(source)
    if not photos:
        raise SystemExit(f"No photos found in {source}")

    # photo path -> list of label rows ([] for a negative photo)
    labels: dict[Path, list[list[float]]] = {}
    for photo in photos:
        label_file = photo.with_suffix(".txt")
        if not label_file.exists():
            raise SystemExit(f"Missing label file for {photo.name} (expected {label_file.name}). "
                             f"If this photo has no problem, put it in the --negatives folder instead.")
        labels[photo] = read_labels(label_file)   # an empty label file means "no problem here" (a negative photo)

    negatives = list_photos(Path(args.negatives)) if args.negatives else []
    for photo in negatives:
        labels[photo] = []

    # file names must be unique, because all photos end up in the same folder
    names = Counter(p.name for p in labels)
    clashes = [n for n, c in names.items() if c > 1]
    if clashes:
        raise SystemExit(f"These file names are used more than once: {clashes[:5]}. Rename them so every name is unique.")

    # group photos by their most common class (negatives form their own group), then pick validation photos
    groups = defaultdict(list)
    for photo, rows in labels.items():
        key = Counter(int(r[0]) for r in rows).most_common(1)[0][0] if rows else -1
        groups[key].append(photo)

    rng = random.Random(SEED)
    validation = set()
    for key, members in sorted(groups.items()):
        members.sort()
        rng.shuffle(members)
        validation.update(members[:max(1, round(len(members) * VALIDATION_SHARE))])

    if output.exists():
        shutil.rmtree(output)
    for photo, rows in labels.items():
        part = "val" if photo in validation else "train"
        (output / "images" / part).mkdir(parents=True, exist_ok=True)
        (output / "labels" / part).mkdir(parents=True, exist_ok=True)
        shutil.copy2(photo, output / "images" / part / photo.name)
        text = "\n".join(" ".join(str(v) for v in row) for row in rows)
        if rows:
            shutil.copy2(photo.with_suffix(".txt"), output / "labels" / part / (photo.stem + ".txt"))
        else:
            (output / "labels" / part / (photo.stem + ".txt")).write_text("")   # empty file = background photo

    # summary
    total = len(labels)
    print(f"Photos: {total}  (train {total - len(validation)}, val {len(validation)}),  of which negatives: {len(negatives)}")
    print(f"{'class':20s} {'photos':>7s} {'boxes':>7s} {'boxes in val':>13s}")
    for class_id, name in enumerate(CLASS_NAMES):
        photo_count = sum(any(int(r[0]) == class_id for r in rows) for rows in labels.values())
        box_count = sum(int(r[0]) == class_id for rows in labels.values() for r in rows)
        val_boxes = sum(int(r[0]) == class_id for p in validation for r in labels[p])
        warning = "   <-- too few photos" if photo_count < MIN_PHOTOS_PER_CLASS else ""
        print(f"{name:20s} {photo_count:7d} {box_count:7d} {val_boxes:13d}{warning}")
    print(f"Done. Dataset written to {output}")
    if any(sum(any(int(r[0]) == c for r in rows) for rows in labels.values()) < MIN_PHOTOS_PER_CLASS for c in range(len(CLASS_NAMES))):
        print(f"\nTip: aim for at least {MIN_PHOTOS_PER_CLASS} photos per class. See ml/README.md for where to get more.")


if __name__ == "__main__":
    main()
