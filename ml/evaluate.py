"""Measure how good the trained model is on the validation photos.

Run from the ml folder:   python evaluate.py
Prints precision, recall and mAP (the usual scores for object detection) and the score of each class.
"""
from ultralytics import YOLO

model = YOLO("weights/nececity_yolo.pt")
results = model.val(data="dataset.yaml", imgsz=640)

print("\nOverall on the validation photos")
print("  Precision    :", round(float(results.box.mp), 3), " (of the boxes it drew, how many were right)")
print("  Recall       :", round(float(results.box.mr), 3), " (of the real problems, how many it found)")
print("  mAP@0.5      :", round(float(results.box.map50), 3))
print("  mAP@0.5-0.95 :", round(float(results.box.map), 3))

print("\nmAP@0.5 per class")
for class_id, score in zip(results.box.ap_class_index, results.box.ap50):
    print(f"  {model.names[int(class_id)]:20s} {float(score):.3f}")
