# NeuroBeat

A Brain.io hackathon project: a real-time game controlled entirely by brainwave signals captured via the **Unicorn Black** EEG headset.

## Overview

NeuroBeat translates raw EEG signals into game inputs, letting a player control a Unity game using only their brain activity. The pipeline covers signal acquisition, processing/filtering, real-time game integration, and OS-level control via head movement and concentration.

## Repository Structure

```
NeuroBeat/
├── api/                    # Unicorn Black data acquisition & hardware verification
├── control/                # OS-level control: mouse cursor (gyroscope) + click (EEG focus)
├── game/                   # Unity game — receives EEG commands via UDP
└── signal-processing/      # EEG signal cleaning, classification, and unified UDP stream
    ├── manual-filtering/   # Bandpass, artifact rejection, bandpower features
    └── model-finetuning/   # EEGNetv4 fine-tuned to the test subject
```

## Hardware

- **Unicorn Black** — 8-channel EEG headset by g.tec
- Sampling rate: 250 Hz
- Channels: FZ, C3, CZ, C4, PZ, PO7, OZ, PO8 + accelerometer + gyroscope

## Signal Processing — quick summary

| Sub-pipeline | Qué hace | Salida |
|---|---|---|
| `manual-filtering/` | Notch → Bandpass → ICA → bandpower α/β/θ | Scores normalizados 0–1 |
| `model-finetuning/` | EEGNetv4 fine-tuneado al sujeto | `focus` float 0–1 |

El modelo se auto-descarga (~10 MB) desde Hugging Face (`PierreGtch/EEGNetv4`). No requiere descarga manual.

## UDP Stream — formato unificado

`signal-processing/stream.py` emite un JSON en **UDP:5005** cada ~250 ms:

```json
{
  "focus": 0.73,  "alpha": 0.41,  "beta": 0.62,  "theta": 0.18,  "engagement": 0.60,
  "accel_x": 12.4,  "accel_y": -8.1,  "accel_z": 998.3,
  "gyro_x": -0.5,   "gyro_y":  1.2,   "gyro_z":   0.3
}
```

Consumers en el mismo puerto (SO_REUSEADDR — todos reciben el mismo datagrama):
- **Unity** `game/Assets/Scripts/EEGReceiver.cs` — input del juego
- **gyro_mouse** `control/gyro_mouse.py` — control del OS

## Quick Start

```bash
# 1. Instalar todo
pip install -r requirements.txt

# 2. Calibrar sujeto y entrenar modelo (--mock = sin hardware)
python signal-processing/model-finetuning/calibrate.py --output data/s1.npz --mock
python signal-processing/model-finetuning/train.py --data data/s1.npz --output models/s1.pt

# 3. Arrancar el streamer (Terminal 1)
cd signal-processing
python stream.py --model model-finetuning/models/s1.pt --mock

# 4a. Abrir Unity y dar Play  →  game recibe señal por UDP
# 4b. O controlar el mouse con la cabeza + concentración (Terminal 2)
python control/gyro_mouse.py --mock
```

Ver el `README.md` dentro de cada carpeta para instrucciones detalladas.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
