"""Convert the trained model to ONNX so the web app can run it without PyTorch.

Run from the ml folder:   python export_onnx.py
Creates  weights/nececity_yolo.onnx  (the file the backend loads).
"""
from ultralytics import YOLO

model = YOLO("weights/nececity_yolo.pt")
path = model.export(format="onnx", imgsz=640, opset=12)
print("Saved:", path)
