"""Train the YOLOv8n detector on our own photos.

Run from the ml folder:   python train.py
(On a laptop without a graphics card this is slow. NeceCity_Training_Colab.ipynb does the same
job on a free Google Colab GPU and is the recommended way.)

How it learns: we start from YOLOv8n weights that were already trained on the large COCO dataset
(so it already knows edges, textures and shapes) and keep training them on OUR labelled photos until
they recognise our six problem types. This is called transfer learning. Training from completely random
weights would need many thousands of photos.

When it finishes it prints where best.pt is. Copy that file to  weights/nececity_yolo.pt
and run  python export_onnx.py  to make the file the web app loads.
"""
from ultralytics import YOLO

model = YOLO("yolov8n.pt")   # the first run downloads these starting weights

model.train(
    data="dataset.yaml",
    epochs=150,       # how many times it goes through all the training photos
    imgsz=640,        # photos are resized to 640 x 640
    batch=8,          # photos looked at together (small, because we have few photos)
    patience=40,      # stop early if the validation score has not improved for 40 epochs
    seed=42,
    # augmentation: each epoch the photos are randomly rotated, flipped, shifted in colour and brightness
    # and mixed together, which makes a small dataset behave like a bigger one
    degrees=10, fliplr=0.5, hsv_s=0.7, hsv_v=0.4, scale=0.5, mosaic=1.0,
    project="runs",
    name="nececity_yolo",
)

print("\nBest model saved at:", model.trainer.best)
