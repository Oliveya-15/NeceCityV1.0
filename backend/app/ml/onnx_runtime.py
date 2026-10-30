"""Runs the YOLOv8 model with ONNX Runtime (no PyTorch needed).

Steps for one photo:
  1. letterbox: resize the photo to 640x640 without stretching it (grey padding)
  2. run the ONNX model
  3. decode: turn the raw numbers into boxes, drop weak ones, remove duplicate boxes (NMS)
  4. convert the boxes back to fractions (0 to 1) of the ORIGINAL photo size

The model file is made once from the trained weights with:
    yolo export model=nececity_yolo.pt format=onnx imgsz=640 opset=12
The raw output of a YOLOv8 model has the shape (1, 4 + number_of_classes, 8400):
the first 4 rows are the box (centre x, centre y, width, height), the other rows are
one score per class.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:  # pragma: no cover
    ort = None
    ONNX_AVAILABLE = False


@dataclass
class OnnxBox:
    class_id: int
    confidence: float
    x_min: float  # normalized 0-1 (relative to the ORIGINAL image)
    y_min: float
    x_max: float
    y_max: float


def letterbox(img: Image.Image, size: int) -> tuple[np.ndarray, float, float, float]:
    """Resize keeping aspect ratio and pad to size x size (grey 114, like YOLO)."""
    w, h = img.size
    scale = min(size / w, size / h)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    resized = img.resize((new_w, new_h), Image.BILINEAR)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    pad_x, pad_y = (size - new_w) / 2, (size - new_h) / 2
    canvas.paste(resized, (int(round(pad_x - 0.1)), int(round(pad_y - 0.1))))
    arr = np.asarray(canvas, dtype=np.float32) / 255.0  # HWC
    arr = np.transpose(arr, (2, 0, 1))[None]  # 1,3,H,W
    return np.ascontiguousarray(arr), scale, pad_x, pad_y


def _iou_one_to_many(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (box[2] - box[0]) * (box[3] - box[1])
    area_b = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / np.maximum(area_a + area_b - inter, 1e-9)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        ious = _iou_one_to_many(boxes[i], boxes[order[1:]])
        order = order[1:][ious <= iou_thr]
    return keep


def drop_contained_boxes(
    boxes: np.ndarray, class_ids: np.ndarray, keep: list[int], containment_thr: float = 0.8
) -> list[int]:
    """NMS only removes boxes that overlap a lot compared with their combined area.
    A small box sitting INSIDE a big box of the same class has a low overlap score, so NMS keeps both
    (for example one open drain drawn twice). Here we also drop such a box.

    `keep` is ordered from the most confident box to the least confident one."""
    final: list[int] = []
    for i in keep:
        x1, y1, x2, y2 = boxes[i]
        area_i = max((x2 - x1) * (y2 - y1), 1e-9)
        inside_a_better_box = False
        for j in final:
            if class_ids[j] != class_ids[i]:
                continue
            ix1, iy1 = max(x1, boxes[j][0]), max(y1, boxes[j][1])
            ix2, iy2 = min(x2, boxes[j][2]), min(y2, boxes[j][3])
            overlap = max(ix2 - ix1, 0) * max(iy2 - iy1, 0)
            if overlap / area_i >= containment_thr:   # 80% or more of this box is inside the better one
                inside_a_better_box = True
                break
        if not inside_a_better_box:
            final.append(i)
    return final


def decode_output(
    output: np.ndarray,
    *,
    scale: float,
    pad_x: float,
    pad_y: float,
    orig_w: int,
    orig_h: int,
    conf_thr: float,
    iou_thr: float,
    max_det: int,
) -> list[OnnxBox]:
    """Turn raw (1, 4+nc, N) model output into normalized, NMS-filtered boxes."""
    preds = np.squeeze(output, axis=0)  # (4+nc, N)
    if preds.shape[0] < preds.shape[1]:
        preds = preds.T  # -> (N, 4+nc)
    boxes_cxcywh = preds[:, :4]
    class_scores = preds[:, 4:]
    class_ids = class_scores.argmax(axis=1)
    confs = class_scores.max(axis=1)

    mask = confs >= conf_thr
    if not mask.any():
        return []
    boxes_cxcywh, class_ids, confs = boxes_cxcywh[mask], class_ids[mask], confs[mask]

    xyxy = np.empty_like(boxes_cxcywh)
    xyxy[:, 0] = boxes_cxcywh[:, 0] - boxes_cxcywh[:, 2] / 2
    xyxy[:, 1] = boxes_cxcywh[:, 1] - boxes_cxcywh[:, 3] / 2
    xyxy[:, 2] = boxes_cxcywh[:, 0] + boxes_cxcywh[:, 2] / 2
    xyxy[:, 3] = boxes_cxcywh[:, 1] + boxes_cxcywh[:, 3] / 2

    # Per-class NMS (same as ultralytics default): shift each class far apart.
    offset = class_ids[:, None].astype(np.float32) * 10000.0
    keep = nms(xyxy + offset, confs, iou_thr)
    keep = drop_contained_boxes(xyxy, class_ids, keep)[:max_det]

    results: list[OnnxBox] = []
    for i in keep:
        x1 = (xyxy[i, 0] - pad_x) / scale
        y1 = (xyxy[i, 1] - pad_y) / scale
        x2 = (xyxy[i, 2] - pad_x) / scale
        y2 = (xyxy[i, 3] - pad_y) / scale
        results.append(
            OnnxBox(
                class_id=int(class_ids[i]),
                confidence=float(confs[i]),
                x_min=float(np.clip(x1 / orig_w, 0, 1)),
                y_min=float(np.clip(y1 / orig_h, 0, 1)),
                x_max=float(np.clip(x2 / orig_w, 0, 1)),
                y_max=float(np.clip(y2 / orig_h, 0, 1)),
            )
        )
    return results


class OnnxYolo:
    def __init__(self, model_path: str) -> None:
        if not ONNX_AVAILABLE:
            raise ImportError("onnxruntime is not installed")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1  # free tiers have ~1 CPU; avoids thread overhead
        opts.enable_mem_pattern = False  # lowers peak memory a little
        self._session = ort.InferenceSession(
            model_path, sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name
        shape = self._session.get_inputs()[0].shape  # [1,3,H,W] (may be dynamic)
        self._fixed_size = int(shape[2]) if isinstance(shape[2], int) else None

    def predict(
        self, image_path: str, *, conf: float, iou: float, imgsz: int, max_det: int
    ) -> list[OnnxBox]:
        size = self._fixed_size or imgsz
        with Image.open(image_path) as im:
            img = im.convert("RGB")
        orig_w, orig_h = img.size
        tensor, scale, pad_x, pad_y = letterbox(img, size)
        output = self._session.run(None, {self._input_name: tensor})[0]
        return decode_output(
            output,
            scale=scale,
            pad_x=pad_x,
            pad_y=pad_y,
            orig_w=orig_w,
            orig_h=orig_h,
            conf_thr=conf,
            iou_thr=iou,
            max_det=max_det,
        )