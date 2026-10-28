# Model files

| File | What it is |
|---|---|
| `nececity_yolo.pt` | The trained YOLOv8n model (PyTorch format). Used for evaluating and exporting. |
| `nececity_yolo.onnx` | The same model in ONNX format. **This is the file the web app loads.** |

The web app shows "Model not trained" in the top bar until `nececity_yolo.onnx` exists in this folder.

Create both files by running `NeceCity_Training_Colab.ipynb` (see `ml/README.md`), or on your own computer with
`python train.py` and `python export_onnx.py`. Commit the `.onnx` file (about 12 MB) to GitHub, because Render
reads it from the repository.

## Training details

- Model: YOLOv8n, starting from COCO-pretrained weights, trained with Ultralytics 8.3.28 (transfer learning)
- Data: `ml/data/real_dataset` - 30 photos (24 training, 6 validation) with 65 labelled boxes in 6 classes
- The dataset is small. That is the main limitation of the model, and the reason every detection must be confirmed by a person.
