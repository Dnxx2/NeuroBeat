# Model Fine-Tuning Pipeline

Fine-tuning **EEGNet** on test subject data.

> **To send to Unity alongside the manual pipeline** use `../stream.py` — it runs both in parallel and sends a single UDP packet with all values.
> This README covers training and **standalone** use of the model.

**`focus_score()` output:** `float 0.0–1.0` — raw model output for the FOCUS class.
**`stream()` output:** JSON over UDP `{"focus": 0.73}` every ~250 ms.

---

## How it works

### The model — EEGNet

EEGNet is a compact CNN designed for BCI with limited data. It has two blocks:

1. **Depthwise temporal convolution** — learns EEG frequency filters (equivalent to the manual bandpass, but learned from real data)
2. **Separable spatial convolution** — learns which combination of the 8 channels maximizes class separability

The model is initialized with random weights and trained from scratch on the subject's calibration data. `from_pretrained_hub()` in `model.py` exists as a utility for loading pre-trained weights from Hugging Face (`PierreGtch/EEGNetv4`, `EEGNetv4_Lee2019_MI/model-params.pkl`), but it is not the default workflow — the standard flow calls `build_model()` directly.

### Two-phase training

With only 2 minutes of data, training is split into two phases:

**Phase 1 — frozen backbone (10 epochs, LR=1e-3)**
Only the final classifier trains. Converges quickly because it is nearly a linear problem.

**Phase 2 — all layers (20 epochs, LR=1e-4)**
With the classifier oriented, all layers are unfrozen at 10× lower LR. Spatial filters adapt to the subject without destroying what was learned in phase 1.

### Inference — focus score and blink inversion

`focus_score()` returns `predict_proba()[1]` — the FOCUS class probability.

In `stream.py`, the model output is inverted before sending as `focus`:
```python
prob_parpadeo = 1.0 - raw_score      # invert model output
if prob_parpadeo > 0.7:
    score_filtrado = 1.0             # blink detected with high confidence
else:
    score_filtrado = prob_parpadeo   # continuous value 0–0.7
```
`focus` is a float 0–1. Values ≥ 0.7 are saturated to 1.0 (blink detected with certainty). Below 0.7 the value is continuous. Unity uses `EEGMouseClicker` with threshold 0.95 to fire actions only when `focus = 1.0`.

### Data augmentation

With ~2 minutes of data the dataset is small. Each epoch passes through:
- **Light Gaussian noise** (σ = 0.5 µV) — natural signal variability
- **Random time shift** (±100 ms) — invariance to small timing variations

---

## Full workflow: from zero to real time

```
[1] pip install -r requirements.txt   (from repo root)
[2] python calibrate_api.py     →  record 2 min with the Unicorn (proprietary g.tec API)
    python calibrate_generic.py →  alternative with standard UnicornPy SDK
[3] python train.py             →  train + save model as models/calibrated.pt
[4] cd .. && python stream.py --model model-finetuning/models/calibrated.pt
```

---

## Step 1 — Install

```bash
pip install -r requirements.txt   # from repo root
```

---

## Step 2 — Record calibration

Two calibration scripts are available depending on which API is installed:

| Script | API | When to use |
|--------|-----|-------------|
| `calibrate_api.py` | Proprietary UnicornPy (`api/Lib`) | g.tec hardware with full SDK |
| `calibrate_generic.py` | Standard UnicornPy SDK | Standard UnicornPy installation |

```bash
# With Unicorn Black connected (proprietary API — recommended)
python calibrate_api.py --output data/calibration.npz

# With standard SDK
python calibrate_generic.py --output data/calibration.npz

# Without hardware (random signal — for testing the pipeline)
python calibrate_api.py --output data/calibration.npz --mock
```

The script does:
1. Displays on-screen cues
2. Records 30 s × 2 classes × 2 rounds = **2 minutes total**
   - Class 0 — RELAX: "Keep your eyes open"
   - Class 1 — FOCUS: "Blink for 30 seconds"
3. Splits each recording into 2 s windows with 50% overlap
4. Saves `data/calibration.npz` with arrays `epochs (n, 500, 1)` and `labels (n,)`

> **Note:** The `data/` directory is created automatically if it does not exist.

`.npz` files are in `.gitignore`. Verify a good recording:
```python
import numpy as np
d = np.load('data/calibration.npz')
print(d['epochs'].shape)   # e.g. (240, 500, 1)
print(d['labels'])          # [0,0,...,1,1,...]  0=RELAX, 1=FOCUS
```

---

## Step 3 — Train

```bash
# From repo root
python signal-processing/model-finetuning/train.py \
    --data signal-processing/model-finetuning/data/calibration.npz \
    --output signal-processing/model-finetuning/models/calibrated.pt
```

Or from inside the folder:
```bash
cd signal-processing/model-finetuning
python train.py --data data/calibration.npz --output models/calibrated.pt
```

Expected output:
```
── Phase 1/30: frozen backbone ──
Epoch   1/30  val_acc=0.541
Epoch   2/30  val_acc=0.623
  -> checkpoint saved  (best=0.623)
...
── Phase 2/30: all layers, LR=1.0e-04 ──
Epoch  11/30  val_acc=0.741
  -> checkpoint saved  (best=0.741)
...
Done. Best val_acc: 0.821  →  models/calibrated.pt
```

> **Note:** The `models/` directory is created automatically if it does not exist.

Optional parameters:
```bash
python train.py \
  --data data/calibration.npz \
  --output models/calibrated.pt \
  --phase1-epochs 10 \
  --phase2-epochs 20 \
  --lr 1e-3 \
  --batch-size 16
```

---

## Step 4 — Real-time streaming to the game

### Recommended — combined stream

```bash
cd signal-processing
python stream.py --model model-finetuning/models/calibrated.pt
```

This is the recommended method: runs both pipelines (EEGNet + manual filtering) in parallel and sends a single UDP packet with all values.

### Standalone — model only

```python
from predict import EEGClassifier
clf = EEGClassifier('models/calibrated.pt')

# focus_score returns float 0.0–1.0 (raw, before stream.py inversion)
score = clf.focus_score(window_500x1)

# Autonomous stream — sends {"focus": 0.73} over UDP every ~250 ms
clf.stream(get_sample, host='127.0.0.1', port=5005)
```

---

## Module reference

| File | Responsibility |
|------|---------------|
| `calibrate_api.py` | Guided 2-min session → `.npz` — uses proprietary g.tec API (`api/Lib`) |
| `calibrate_generic.py` | Guided 2-min session → `.npz` — uses standard UnicornPy SDK |
| `dataset.py` | `torch.Dataset` + augmentation (noise + time shift) |
| `model.py` | EEGNet, `build_model()`, `from_pretrained_hub()`, `freeze_backbone()` |
| `train.py` | Two-phase fine-tuning, checkpoint on best val_acc |
| `predict.py` | `focus_score()` → float, `stream()` → UDP loop |

---

## Data and model files

`.npz` (data) and `.pt` (weights) files are in `.gitignore`. Expected structure:

```
signal-processing/model-finetuning/
├── data/
│   └── calibration.npz     ← generated by calibrate_api.py / calibrate_generic.py
└── models/
    └── calibrated.pt       ← generated by train.py
```

---

## Loading pre-trained Hugging Face weights (optional)

To start from pre-trained weights instead of random initialization:

```python
from model import from_pretrained_hub
model = from_pretrained_hub(n_classes=2)
# Weights: PierreGtch/EEGNetv4 → EEGNetv4_Lee2019_MI/model-params.pkl
```

Then pass the model to `train()` or save it as a starting point for fine-tuning.
