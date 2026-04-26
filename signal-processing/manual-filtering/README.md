# Manual Filtering Pipeline

Classical DSP pipeline for cleaning Unicorn Black EEG signals in real time.

> **To send to Unity alongside the model** use `../stream.py` — it runs both pipelines in parallel and sends a single UDP packet with all values.
> This README covers **standalone** use of the manual pipeline.

**`push()` output:** `ndarray (500, 8)` — clean signal, z-score normalized per channel.
**`stream_to_unity()` output:** JSON over UDP `{"alpha": 0.41, "beta": 0.62, "theta": 0.18, "engagement": 0.60}`

---

## How it works — from raw signal to clean output

### The problem

The Unicorn Black uses dry electrodes, introducing more noise than a lab-grade system:

- **Power line noise** — 60 Hz spike from the room's electrical grid
- **Low-frequency drift** — slow electrode movement, sweat
- **Blink artifacts** — each blink generates ~100–200 µV at FZ, masking the brain signal
- **Shared noise across channels** — electromagnetic interference arriving equally at all electrodes

The pipeline removes each noise type in order.

### Step 1 — Common Average Reference (CAR)

```
channel[n] = channel[n] − mean(all channels)[n]
```

At each time step, the mean of all 8 channels is subtracted from each channel. Removes any noise that is identical across all electrodes simultaneously: amplifier variations, ambient interference. The cheapest and one of the most effective steps for dry electrodes.

### Step 2 — Notch filter (60 Hz)

Removes the exact 60 Hz power line peak. IIR notch filter with Q=30: eliminates only ±2 Hz around 60 Hz without distorting the rest of the spectrum.

### Step 3 — Bandpass filter (0.5–40 Hz)

Everything outside the brain signal range of interest is cut:
- Below 0.5 Hz: electrode drift, sweat
- Above 40 Hz: muscle noise (EMG), high-frequency artifacts

4th-order Butterworth with `filtfilt` (zero-phase — no temporal shift of events).

### Step 4 — ICA with blink detection (offline only)

ICA decomposes the 8 channels into 8 independent sources. MNE automatically identifies which are blinks by correlating each component with **FZ** (the electrode closest to the eyes on the Unicorn). Blink components are zeroed and the signal is reconstructed.

**Why it is skipped in real time:** ICA needs to fit on a long block (>10 s). Sample-by-sample streaming would introduce seconds of latency. In real time only CAR + notch + bandpass run — all instantaneous.

### Step 5 — Per-channel z-score normalization (real time)

`RunningNormalizer` maintains the running mean and variance for each channel using Welford's online algorithm (no history stored). After a 5 s warmup, it normalizes each window so every channel has mean ≈ 0 and variance ≈ 1.

This is necessary because:
- Absolute EEG amplitude varies across sessions, subjects, and impedance levels
- Without normalization, a poorly connected channel would dominate the analysis
- With z-score, all channels contribute equally regardless of their scale

### Final output

Every 250 ms `push()` returns `ndarray (500, 8)` — a 2 s window, 8 channels, clean and normalized. The game team can use it directly, extract additional features, or pass it to any custom classifier.

---

## Full workflow: from zero to real time

```
[1] pip install -r requirements.txt
[2] Record offline calibration (for the adaptive classifier, optional)
[3] Calibrate the classifier and save
[4] Run the real-time loop
```

---

## Step 1 — Install

```bash
pip install -r requirements.txt   # from repo root
```

---

## Step 2 — Record offline calibration (optional)

If you want to use the `AdaptiveClassifier` (subject-calibrated nearest-centroid), you need a labeled ~2-min recording. If you only need the clean signal to process yourself, skip directly to Step 4.

```python
import numpy as np

# Record with the Unicorn — replace with your actual acquisition loop
relax_samples, focus_samples = [], []

print("RELAX — close eyes, breathe slowly (2 min)")
for _ in range(250 * 120):
    relax_samples.append(unicorn.get_sample())   # ndarray (8,)

print("FOCUS — concentrate, count by 3s (2 min)")
for _ in range(250 * 120):
    focus_samples.append(unicorn.get_sample())

relax_rec = np.array(relax_samples)   # (30000, 8)
focus_rec = np.array(focus_samples)   # (30000, 8)
```

---

## Step 3 — Calibrate and save (optional)

```python
from pipeline import EEGPipeline

pipeline = EEGPipeline(fs=250, use_ica=True)

pipeline.calibrate({
    'RELAX': relax_rec,
    'FOCUS': focus_rec,
})

pipeline.save_calibration('calibration.npz')
```

This processes each recording through the full pipeline, splits into 2 s epochs, discards noisy ones (>100 µV peak-to-peak), extracts the 32-feature vector (bandpower δθαβ × 8 channels) from each epoch, and computes the z-normalized centroid of each class. The `.npz` file is a few KB.

---

## Step 4 — Real time

### Basic loop — clean signal for free processing

```python
from pipeline import EEGPipeline
from realtime import RealtimeProcessor

pipeline = EEGPipeline(fs=250, use_ica=False)
proc     = RealtimeProcessor(pipeline=pipeline)

while True:
    sample = unicorn.get_sample()       # ndarray (8,)
    window = proc.push(sample)

    if window is not None:
        # window: ndarray (500, 8) — clean, z-score per channel
        # Returns None for the first ~5 s while the normalizer warms up
        pass
```

### Extract bandpower from the clean signal

```python
from features import extract_features, BANDS
import numpy as np

if window is not None:
    feats = extract_features(window)   # ndarray (32,)
    # Order: [FZ_delta, FZ_theta, FZ_alpha, FZ_beta, C3_delta, ...]

    # Average frontal alpha (channels FZ, C3, CZ, C4 = indices 0-3)
    alpha_frontal = np.mean([feats[ch*4 + 2] for ch in range(4)])
    beta_frontal  = np.mean([feats[ch*4 + 3] for ch in range(4)])
    focus_ratio   = beta_frontal / (alpha_frontal + beta_frontal + 1e-9)
```

### Send directly to Unity (standalone, without the model)

```python
from pipeline import EEGPipeline
from realtime import RealtimeProcessor

pipeline = EEGPipeline(fs=250, use_ica=False)
proc     = RealtimeProcessor(pipeline=pipeline)

# Sends {"alpha":0.41,"beta":0.62,"theta":0.18,"engagement":0.60} over UDP every ~250 ms
# Port 5006 to avoid conflict with the combined stream (5005)
proc.stream_to_unity(get_sample, host='127.0.0.1', port=5006)
```

---

### Using the adaptive classifier (if calibrated)

```python
from pipeline import EEGPipeline
from realtime import RealtimeProcessor
from features import extract_features

pipeline = EEGPipeline(fs=250, use_ica=False)
pipeline.load_calibration('calibration.npz')
proc = RealtimeProcessor(pipeline=pipeline)

while True:
    sample = unicorn.get_sample()
    window = proc.push(sample)

    if window is not None:
        feats = extract_features(window)
        state = pipeline.classifier.predict(feats)   # 'FOCUS' | 'RELAX'
```

### Offline processing (batch over a full recording)

```python
from pipeline import EEGPipeline
import numpy as np

pipeline = EEGPipeline(fs=250, use_ica=True)   # ICA enabled for offline use

raw = np.loadtxt('session.csv', delimiter=',')[:, :8]   # (n_samples, 8)

# Process a single window
clean = pipeline.process(raw[:500])   # (500, 8)

# Process and extract features from epochs
epochs = raw.reshape(-1, 500, 8)
clean_epochs, features = pipeline.process_epochs(epochs)
# features: (n_clean_epochs, 32)
```

---

## Module reference

### `filters.py`
- `common_average_reference(eeg)` — subtracts the cross-channel mean at each sample
- `notch(signal, fs, freq, Q)` — IIR notch filter, removes power line peak
- `bandpass(signal, fs, lowcut, highcut, order)` — zero-phase Butterworth
- `apply_filters(eeg, fs, notch_freq)` — applies CAR → notch → bandpass to all channels

### `artifacts.py`
- `remove_artifacts_mne(eeg, fs)` — ICA with MNE + automatic blink detection via FZ. Offline only (>10 s of signal required).
- `reject_epochs(epochs, threshold_uv)` — boolean mask; discards epochs with peak-to-peak > threshold

### `features.py`
- `extract_features(eeg, fs)` — Welch PSD → bandpower δθαβ per channel → vector (32,)
- `AdaptiveClassifier` — z-normalized nearest centroid. Methods: `calibrate()`, `predict()`, `save()`, `load()`

### `pipeline.py`
- `EEGPipeline` — orchestrates everything. Methods: `process()`, `process_epochs()`, `calibrate()`, `classify()`, `save_calibration()`, `load_calibration()`

### `realtime.py`
- `RunningNormalizer` — online z-score (Welford). Properties: `ready`, `normalize(signal)`
- `RealtimeProcessor` — circular buffer + sliding window. `push(sample)` → `ndarray (500, 8)` clean and normalized every 250 ms, or `None`

---

## Unicorn Black channel layout

| Index | Channel | Region |
|-------|---------|--------|
| 0 | FZ | Frontal central — EOG proxy (closest to eyes) |
| 1 | C3 | Left motor |
| 2 | CZ | Central motor |
| 3 | C4 | Right motor |
| 4 | PZ | Parietal |
| 5 | PO7 | Left occipital |
| 6 | OZ | Central occipital |
| 7 | PO8 | Right occipital |

## Frequency bands

| Band | Range | Feature index | Associated with |
|------|-------|---------------|-----------------|
| Delta | 0.5–4 Hz | `ch*4 + 0` | Sleep, drift |
| Theta | 4–8 Hz | `ch*4 + 1` | Drowsiness |
| **Alpha** | **8–12 Hz** | **`ch*4 + 2`** | **Relaxation, eyes closed** |
| **Beta** | **13–30 Hz** | **`ch*4 + 3`** | **Active concentration** |
