# Manual Filtering Pipeline

Classical DSP pipeline for cleaning 8-channel EEG from the Unicorn Black.

## Signal flow

```
Raw EEG (250 Hz, 8 ch)
  → Notch filter     60 Hz / Q=30  (elimina ruido de línea eléctrica)
  → Bandpass         0.5–40 Hz, Butterworth order 4
  → ICA              offline — elimina parpadeo/movimiento  (omitido en tiempo real)
  → Epoch rejection  peak-to-peak > 100 µV → descartado
  → Feature extract  bandpower δ θ α β por canal  →  vector (32,)
  → Classify         ratio α/β frontal  →  FOCUS | RELAX | NEUTRAL
```

## Install

```bash
pip install -r requirements.txt
```

## Usage

### Offline (batch)

```python
from pipeline import EEGPipeline
import numpy as np

pipeline = EEGPipeline(fs=250, notch_freq=60.0, use_ica=True)

raw = np.loadtxt('session.csv', delimiter=',')[:, :8]  # (n_samples, 8)

# Classify a single 2-second window
state = pipeline.classify(raw[:500])   # 'FOCUS' | 'RELAX' | 'NEUTRAL'

# Process labelled epochs
epochs = raw.reshape(-1, 500, 8)
clean_epochs, features = pipeline.process_epochs(epochs)
```

### Real-time (streaming from Unicorn)

```python
from realtime import RealtimeProcessor

proc = RealtimeProcessor(window_sec=2, step_sec=0.25)

# In your acquisition loop:
while True:
    sample = unicorn.get_sample()   # ndarray shape (8,)
    state = proc.push(sample)
    if state:
        send_to_game(state)
```

## Module overview

| File | Responsibility |
|------|---------------|
| `filters.py` | Notch + bandpass (scipy) |
| `artifacts.py` | ICA artifact removal, epoch rejection |
| `features.py` | Bandpower per band/channel, α/β threshold classifier |
| `pipeline.py` | Orchestrates offline batch processing |
| `realtime.py` | Sliding-window real-time wrapper (ICA off) |

## Unicorn Black channel layout

| Index | Label | Region |
|-------|-------|--------|
| 0 | FZ | Frontal |
| 1 | C3 | Motor izq. |
| 2 | CZ | Motor central |
| 3 | C4 | Motor der. |
| 4 | PZ | Parietal |
| 5 | PO7 | Occipital izq. |
| 6 | OZ | Occipital central |
| 7 | PO8 | Occipital der. |

## Frequency bands

| Banda | Rango | Estado asociado |
|-------|-------|-----------------|
| Delta | 0.5–4 Hz | Sueño profundo / drift |
| Theta | 4–8 Hz | Somnolencia |
| Alpha | 8–12 Hz | Relajación / ojos cerrados |
| Beta | 13–30 Hz | Concentración activa |
