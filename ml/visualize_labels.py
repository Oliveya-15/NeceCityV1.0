"""Draws every label box on its photo so you can SEE whether the labels are right.

Run from the ml folder:
    python visualize_labels.py --source ../photos --output ../label_check

For every photo it saves a copy with the boxes drawn and the class NAME written on each box, plus one
overview sheet (label_check/_overview.jpg). Open them and look: does the box named "open_drain" really
surround a drain? Does the box named "damaged_road_sign" surround a damaged sign? A single wrong class number in a
.txt file is enough to make a model confuse two things, and it is the most common mistake in small datasets.
It also prints a warning for photos that have no label file or an empty one.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CLASS_NAMES = ["pothole", "road_damage", "garbage", "waterlogging", "damaged_road_sign", "open_drain"]
COLOURS = ["#E53935", "#FB8C00", "#43A047", "#1E88E5", "#8E24AA", "#00897B"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def draw_photo(photo: Path, label_file: Path, size: int = 640) -> Image.Image:
    img = Image.open(photo).convert("RGB")
    img.thumbnail((size, size))
    w, h = img.size
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    if label_file.exists():
        for line in label_file.read_text().splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            c = int(float(parts[0]))
            xc, yc, bw, bh = (float(v) for v in parts[1:5])
            box = [(xc - bw / 2) * w, (yc - bh / 2) * h, (xc + bw / 2) * w, (yc + bh / 2) * h]
            colour = COLOURS[c % len(COLOURS)]
            d.rectangle(box, outline=colour, width=4)
            name = f"{c}: {CLASS_NAMES[c]}" if c < len(CLASS_NAMES) else f"{c}: ???"
            tw = d.textlength(name, font=font)
            d.rectangle([box[0], box[1] - 22, box[0] + tw + 8, box[1]], fill=colour)
            d.text((box[0] + 4, box[1] - 21), name, fill="white", font=font)
    return img


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw label boxes on photos to check them by eye.")
    parser.add_argument("--source", required=True, help="folder with photos and .txt files (searched recursively)")
    parser.add_argument("--output", default="label_check")
    args = parser.parse_args()

    source, output = Path(args.source), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    photos = sorted(p for p in source.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS and "label_check" not in p.parts)
    if not photos:
        raise SystemExit(f"No photos found in {source}")

    tiles = []
    for photo in photos:
        label_file = photo.with_suffix(".txt")
        if not label_file.exists():
            label_file = Path(str(photo.with_suffix(".txt")).replace("images", "labels"))
        if not label_file.exists() or not label_file.read_text().strip():
            print(f"WARNING: {photo.name} has no boxes (it counts as a negative photo)")
        img = draw_photo(photo, label_file)
        img.save(output / f"{photo.stem}.jpg", quality=90)
        tiles.append(img.copy())
        classes = sorted({int(float(l.split()[0])) for l in label_file.read_text().splitlines() if l.strip()}) if label_file.exists() else []
        print(f"{photo.name:25s} -> {[CLASS_NAMES[c] for c in classes if c < len(CLASS_NAMES)]}")

    # overview sheet: 4 photos per row
    cell = 360
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), "white")
    for i, t in enumerate(tiles):
        t.thumbnail((cell, cell))
        sheet.paste(t, ((i % cols) * cell, (i // cols) * cell))
    sheet.save(output / "_overview.jpg", quality=85)
    print(f"\nSaved {len(tiles)} checked photos and _overview.jpg into {output}. Open them and look.")


if __name__ == "__main__":
    main()
