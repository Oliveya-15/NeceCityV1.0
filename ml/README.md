# Training the detector (ml folder)

The web app only needs one file from here: `weights/nececity_yolo.onnx`. This folder explains how that file is made
and how to make it better.

## The golden rule: the model only learns what the labels say

If a label is wrong or inconsistent, the model learns the mistake. Small datasets are especially sensitive: one wrong
class number or one huge sloppy box is enough to teach "every stretch of tarmac is road damage". **Before you train,
LOOK at your labels:**

```
python visualize_labels.py --source ../photos --output ../label_check
```

It saves every photo with its boxes and class names drawn on it (plus `_overview.jpg`). Open them and check each box.

### Mistakes found in a first dataset (so you can avoid them)

| What was wrong | What the model learned | Fix |
|---|---|---|
| The class `damaged_road_sign` was used for **ordinary** warning and information signs | "A sign = damaged sign", so any sign is reported | Label only signs that are really bent, fallen, broken or defaced. Put photos of normal and road-works signs in the **negatives** folder |
| `road_damage` boxes covered the **whole road**, including normal tarmac | "Grey road surface = road damage" (this is why lane markings and clean roads got flagged) | Draw `road_damage` tightly around the cracked or broken patch only |
| The same pothole labelled `pothole` in one photo and `road_damage` in another; big `road_damage` boxes around small `pothole` boxes | The model cannot tell the two apart | Follow the rules below for every photo |
| Tiny boxes on vehicles or far-away objects | Random noise | Do not label what you cannot clearly see |
| Several boxes for one drain | Several boxes for one drain at prediction time | One tight box per drain |

## Labelling rules (keep them the same for every photo)

| Class | Label it when you see | Do NOT use it for |
|---|---|---|
| `pothole` | A distinct hole in the road, **even if it is full of water** | Long cracks, the whole road |
| `road_damage` | A cracked, crumbling or broken patch of road with no distinct hole | Normal tarmac, lane markings, a clear pothole |
| `garbage` | A pile or scattered heap of waste or dumped rubbish (one box around the whole pile) | A single small item, plants, clean bins |
| `waterlogging` | Standing water covering a stretch of the road or lane | A single pothole with water in it |
| `damaged_road_sign` | A road sign that is **visibly** bent, fallen, broken or defaced | A healthy sign, a road-works sign |
| `open_drain` | An uncovered or broken drain or drain channel (one box per drain) | A drain with a proper cover |

**Negative photos** (none of the six problems: clean roads, lane markings, trees, plants, **healthy signs, road-works
signs, traffic cones**, walls) are just as important as problem photos. They teach the model what NOT to flag.

## More photos: step by step

Aim for **100 or more labelled photos per class** plus 50 to 200 negatives, and always keep 15 to 20 photos aside that
the model is never trained on, to test it honestly.

### A. Road damage and potholes: RDD (Road Damage Dataset)

RDD2022 has about 47,000 road photos from six countries including India, labelled D00 / D10 (cracks), D20 (alligator
cracks) and D40 (potholes). It is published by the Sekimoto Lab (https://github.com/sekilab/RoadDamageDetector). The easiest
way to get it in the right format is a ready-made version on Roboflow Universe:

1. Create a free account at https://universe.roboflow.com .
2. Open an RDD dataset, for example https://universe.roboflow.com/road-damage-detection-b5a1c/rdd-india .
3. Click **Download Dataset**, choose the format **YOLOv8**, choose **download zip to computer**.
4. Unzip it into a folder `downloads/rdd_india` next to the `ml` folder (so the folder contains `data.yaml`).
5. Look at the class names (nothing is copied yet):
   ```
   python import_public_dataset.py --source ../downloads/rdd_india --show-classes
   ```
6. Import it, mapping their names to ours (use the names printed in step 5; this example uses the RDD names).
   Map **all** classes in ONE command, so a photo is never copied twice with half of its labels:
   ```
   python import_public_dataset.py --source ../downloads/rdd_india --tag rdd ^
       --map "D40=pothole,D00=road_damage,D10=road_damage,D20=road_damage" ^
       --output ../photos --max-images 400
   ```
   (On Mac/Linux use `\` instead of `^` at the end of a line, or write it on one line.)

### B. Garbage

1. On https://universe.roboflow.com search for "garbage detection" or "litter detection" and choose a dataset with
   a few thousand images of **piles of waste in streets** (not close-ups of single bottles).
2. Download it in **YOLOv8** format and unzip it to `downloads/garbage1`.
3. `python import_public_dataset.py --source ../downloads/garbage1 --show-classes`
4. Import, for example (use the names you saw):
   ```
   python import_public_dataset.py --source ../downloads/garbage1 --tag garb1 ^
       --map "garbage=garbage,trash=garbage" --output ../photos --max-images 200
   ```

### C. Open drains, waterlogging, damaged signs

There is no large public dataset that I can point you to for these. Search Roboflow Universe for "drain", "manhole",
"flood road", "waterlogging", "damaged sign"; check the photos really match the labelling rules above. Otherwise take
your own photos (100 per class is a realistic goal: about two hours of photographing and two hours of labelling). If you
cannot get enough damaged-sign photos, **remove that class from training for now**: delete those boxes from the `.txt`
files and move the photos to the negatives folder. The app needs no change; the model simply never predicts that class.

### D. Your own photos and the negatives

Put your own photos and their `.txt` files into the same `../photos` folder as the imported ones. Put the negative
photos (no `.txt` files needed) into `../negatives`. Every file name must be different.

Check **every folder** again with `visualize_labels.py` (imported labels can disagree with your rules).

## Train

1. Check and split the data:
   ```
   python prepare_dataset.py --source ../photos --negatives ../negatives --output data/real_dataset
   ```
   It prints the number of photos and boxes of every class and warns about classes with too few photos.
2. Zip `photos` as `NeceCity_Train_Photos.zip` and `negatives` as `negatives.zip`.
3. Open `NeceCity_Training_Colab.ipynb` in https://colab.research.google.com , set **Runtime > Change runtime type > T4 GPU**
   and run the cells from top to bottom. The notebook trains, **checks which epoch is really best**, tests the model on
   its own training photos, measures precision and recall, **suggests the confidence value for the app**, and downloads
   `nececity_yolo.onnx` and `nececity_yolo.pt`.
4. Put both files in `ml/weights/`, commit the `.onnx`, push, and set `MODEL_MIN_CONFIDENCE` to the suggested value.

## When a detection is wrong: find out why

Run one photo through three paths (the trained model, the exported ONNX, and the app's own code):

```
python check_model.py --photo ../photos/P3.jpg --pt weights/nececity_yolo.pt ^
    --onnx weights/nececity_yolo.onnx --runner ../backend/app/ml/onnx_runtime.py --conf 0.25
```

- Path 1 (the `.pt`) is wrong too: the problem is the **training** (labels, too few photos, wrong epoch). Fix the data.
- Path 1 is right but 2 or 3 differ: the problem is the **export or the app code**.
- All three agree: the app is faithful to the model; improve the model with better data.

Use a photo from the training set first: a model must recognise its own training photos.

## How good is it?

Read the notebook output or run `python evaluate.py` for precision, recall and mAP. The honest test is always on photos
the model has **never seen**.
