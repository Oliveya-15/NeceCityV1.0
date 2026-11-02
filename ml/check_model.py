"""Finds out WHERE a wrong detection comes from: the training, the ONNX export, or the app's own code.

It runs one photo through three paths and prints the boxes of each:
    1. the trained .pt model          (Ultralytics, the "truth" of what training produced)
    2. the exported .onnx model       (run by Ultralytics)
    3. the .onnx model run by NeceCity's own code (backend/app/ml/onnx_runtime.py)

How to read the result:
    1 is wrong too            -> the problem is the TRAINING (labels, too few photos, wrong epoch). Fix the data.
    1 is good, 2 or 3 differ  -> the problem is the EXPORT or NeceCity's decoding code. Send this output to your helper.
    1, 2 and 3 agree          -> the app is faithful to the model; improve the model with better data.

Use a photo that is IN your training set first: a model must recognise its own training photos.

Run (needs ultralytics, onnxruntime, pillow, numpy; Google Colab has them after  pip install ultralytics):
    python check_model.py --photo ../photos/P3.jpg --pt weights/nececity_yolo.pt --onnx weights/nececity_yolo.onnx \\
                          --runner ../backend/app/ml/onnx_runtime.py --conf 0.25
"""
import argparse
import importlib.util
import sys

NAMES = ["pothole", "road_damage", "garbage", "waterlogging", "damaged_road_sign", "open_drain"]


def show(title, rows):
    print(f"\n{title}")
    if not rows:
        print("   (no boxes)")
    for name, conf, box in rows:
        print(f"   {name:18s} {conf:5.2f}   box = {[round(v, 2) for v in box]}")


def ultralytics_boxes(model_path, photo, conf):
    from ultralytics import YOLO
    result = YOLO(model_path, task="detect").predict(photo, conf=conf, imgsz=640, verbose=False)[0]
    h, w = result.orig_shape
    rows = []
    for b in result.boxes:
        x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
        rows.append((NAMES[int(b.cls)], float(b.conf), [x1 / w, y1 / h, x2 / w, y2 / h]))
    return sorted(rows, key=lambda r: -r[1])


def our_runner_boxes(runner_path, onnx_path, photo, conf):
    spec = importlib.util.spec_from_file_location("onnx_runtime", runner_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["onnx_runtime"] = module   # needed so the dataclasses inside the file can be created
    spec.loader.exec_module(module)
    boxes = module.OnnxYolo(onnx_path).predict(photo, conf=conf, iou=0.45, imgsz=640, max_det=10)
    return [(NAMES[b.class_id], b.confidence, [b.x_min, b.y_min, b.x_max, b.y_max]) for b in boxes]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--photo", required=True)
    p.add_argument("--pt", required=True)
    p.add_argument("--onnx", required=True)
    p.add_argument("--runner", required=True, help="path to backend/app/ml/onnx_runtime.py")
    p.add_argument("--conf", type=float, default=0.25)
    a = p.parse_args()
    print(f"Photo: {a.photo}   confidence limit: {a.conf}   (boxes are fractions of the photo: x1, y1, x2, y2)")
    show("1) trained .pt model (Ultralytics)", ultralytics_boxes(a.pt, a.photo, a.conf))
    show("2) exported .onnx (Ultralytics)", ultralytics_boxes(a.onnx, a.photo, a.conf))
    show("3) exported .onnx run by NeceCity's code", our_runner_boxes(a.runner, a.onnx, a.photo, a.conf))


if __name__ == "__main__":
    main()
