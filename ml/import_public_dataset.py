"""Converts a public YOLO-format dataset (for example a Roboflow Universe "YOLOv8" download or
a converted RDD2022) into NeceCity's six classes, so you can add it to your own photos.

A downloaded dataset usually looks like:
    some_dataset/data.yaml          (lists the class names)
    some_dataset/train/images, train/labels,  valid/images, valid/labels, test/...

FIRST look at the class names inside the download (no files are copied):
    python import_public_dataset.py --source ~/Downloads/rdd_india --show-classes

Then run the real import from the ml folder (one command per downloaded dataset):
    python import_public_dataset.py --source ~/Downloads/rdd_india --tag rdd \
        --map "D40=pothole,D00=road_damage,D10=road_damage,D20=road_damage" \
        --output ../photos --max-images 300

--map     "their class name = our class name". Classes you do not list are ignored.
          Our names: pothole, road_damage, garbage, waterlogging, damaged_road_sign, open_drain
--tag     a short prefix added to every file name, so names from different datasets never clash
--output  the folder where photos + .txt labels are copied (use the same folder for all datasets,
          together with your own photos, then run prepare_dataset.py on it)
--max-images  stop after this many photos from this dataset (keeps the classes balanced)

Photos that end up with no box of a mapped class are skipped (use --keep-empty to keep them as negatives).
Check each dataset's licence before using it, and mention it in your report.
"""
import argparse
import random
import shutil
from pathlib import Path

import yaml

OUR_CLASSES = ["pothole", "road_damage", "garbage", "waterlogging", "damaged_road_sign", "open_drain"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def read_names(source: Path) -> list[str]:
    data_yaml = next(iter(sorted(source.rglob("data.yaml"))), None)
    if data_yaml is None:
        raise SystemExit(f"No data.yaml found in {source}. This script needs a YOLO-format download.")
    names = yaml.safe_load(data_yaml.read_text()).get("names")
    if isinstance(names, dict):
        return [names[k] for k in sorted(names, key=int)]
    return list(names)


def parse_mapping(text: str) -> dict[str, int]:
    mapping = {}
    for pair in text.split(","):
        theirs, ours = (x.strip() for x in pair.split("="))
        if ours not in OUR_CLASSES:
            raise SystemExit(f"'{ours}' is not one of our classes: {', '.join(OUR_CLASSES)}")
        mapping[theirs] = OUR_CLASSES.index(ours)
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a public YOLO dataset to NeceCity's classes.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--map", help='e.g. "D40=pothole,D00=road_damage"')
    parser.add_argument("--tag", help="prefix for the copied file names")
    parser.add_argument("--output")
    parser.add_argument("--show-classes", action="store_true", help="only print the dataset's class names and box counts")
    parser.add_argument("--max-images", type=int, default=0, help="0 = no limit")
    parser.add_argument("--keep-empty", action="store_true", help="keep photos without any mapped box as negatives")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output) if args.output else None
    their_names = read_names(source)

    if args.show_classes:
        counts = [0] * len(their_names)
        for label_file in source.rglob("*.txt"):
            if "labels" not in label_file.parts:
                continue
            for line in label_file.read_text().splitlines():
                parts = line.split()
                if parts and int(float(parts[0])) < len(counts):
                    counts[int(float(parts[0]))] += 1
        print(f"Classes in {source.name}:")
        for i, (name, n) in enumerate(zip(their_names, counts)):
            print(f"  {i:2d}  {name:25s} {n:7d} boxes")
        print("\nNow choose which of them become pothole, road_damage, garbage, waterlogging, damaged_road_sign or open_drain,"
              " and use --map \"name=ourclass,name2=ourclass\".")
        return

    if not (args.map and args.tag and args.output):
        raise SystemExit("--map, --tag and --output are required (or use --show-classes to look first).")
    mapping = parse_mapping(args.map)
    unknown = [n for n in mapping if n not in their_names]
    if unknown:
        raise SystemExit(f"These names are not in the dataset's data.yaml: {unknown}. It has: {their_names}")
    id_map = {their_names.index(n): ours for n, ours in mapping.items()}

    photos = sorted(p for p in source.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS and "images" in p.parts)
    random.Random(42).shuffle(photos)
    output.mkdir(parents=True, exist_ok=True)

    copied = skipped = 0
    for photo in photos:
        if args.max_images and copied >= args.max_images:
            break
        label_file = Path(str(photo.with_suffix(".txt")).replace("/images/", "/labels/").replace("\\images\\", "\\labels\\"))
        rows = []
        if label_file.exists():
            for line in label_file.read_text().splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                class_id = int(float(parts[0]))
                if class_id in id_map:
                    # keep only class + the 4 box numbers (drops polygon points if the dataset has them)
                    rows.append(" ".join([str(id_map[class_id])] + parts[1:5]))
        if not rows and not args.keep_empty:
            skipped += 1
            continue
        name = f"{args.tag}_{photo.stem}"
        shutil.copy2(photo, output / f"{name}{photo.suffix.lower()}")
        (output / f"{name}.txt").write_text("\n".join(rows))
        copied += 1

    print(f"Copied {copied} photos from {source.name} (skipped {skipped} without a mapped class) into {output}")
    if copied and args.keep_empty:
        print("Photos without boxes were kept: they have empty .txt files. Move those into your --negatives folder if you prefer.")


if __name__ == "__main__":
    main()
