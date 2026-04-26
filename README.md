# NeuroBeat

A Brain.io hackathon project: a real-time game controlled entirely by brainwave signals captured via the **Unicorn Black** EEG headset.

## Overview

NeuroBeat translates raw EEG signals into game inputs. The player controls a Unity rhythm game using brain activity and head movement — deliberate blinks trigger in-game actions while the gyroscope moves the OS cursor. The pipeline covers EEG acquisition, signal processing, real-time UDP streaming, and OS-level control.

## Repository Structure

```
NeuroBeat/
├── api/                    # Hardware verification scripts (BrainFlow)
├── control/                # OS-level control: mouse cursor (gyroscope) + click (EEG focus)
├── game/                   # Unity game — receives EEG commands via UDP
└── signal-processing/      # EEG signal cleaning, classification, and unified UDP stream
    ├── manual-filtering/   # Bandpass, artifact rejection, bandpower features
    └── model-finetuning/   # EEGNet fine-tuned to the test subject
```

## Hardware

- **Unicorn Black** — 8-channel EEG headset by g.tec, 250 Hz
- Channels: FZ, C3, CZ, C4, PZ, PO7, OZ, PO8 + accelerometer (mg) + gyroscope (°/s)
- Frame layout (17 values): `[0:8]` EEG · `[8:11]` Accel · `[11:14]` Gyro · `[14:17]` Battery/Counter/Validation

## Signal Processing — quick summary

| Sub-pipeline | Qué hace | Salida |
|---|---|---|
| `manual-filtering/` | Notch → Bandpass → ICA → bandpower α/β/θ | Scores normalizados 0–1 |
| `model-finetuning/` | EEGNet entrenado para detectar parpadeos deliberados | `focus` float 0–1 (saturado a 1.0 al detectar parpadeo) |

## UDP Stream — formato unificado

`signal-processing/stream.py` emite un JSON en **UDP:5005** cada ~250 ms:

```json
{
  "focus": 0.0,   "alpha": 0.41,  "beta": 0.62,  "theta": 0.18,  "engagement": 0.60,
  "accel_x": 12.4,  "accel_y": -8.1,  "accel_z": 998.3,
  "gyro_x": -0.5,   "gyro_y":  1.2,   "gyro_z":   0.3
}
```

El campo `focus` es un float 0–1: sube con la probabilidad de parpadeo deliberado y se satura a 1.0 cuando supera 0.7. Unity lo usa vía `EEGMouseClicker.cs` (umbral 0.95) para disparar acciones solo cuando el parpadeo es detectado con alta certeza.

Múltiples consumidores pueden escuchar el mismo puerto (SO_REUSEADDR — todos reciben el mismo datagrama):
- **Unity** `game/Assets/Scripts/Data_Receiver/EEGReceiver.cs` — input del juego (blink trigger, bandpower disponible)
- **gyro_mouse** `control/gyro_mouse.py` — mueve el cursor con el giroscopio y hace click por blink

## Quick Start

```bash
# 1. Instalar todo
pip install -r requirements.txt

# 2. Calibrar sujeto (--mock = sin hardware)
python signal-processing/model-finetuning/calibrate_api.py \
    --output signal-processing/model-finetuning/data/calibration.npz --mock

# 3. Entrenar modelo
python signal-processing/model-finetuning/train.py \
    --data signal-processing/model-finetuning/data/calibration.npz \
    --output signal-processing/model-finetuning/models/calibrated.pt

# 4. Arrancar el streamer (Terminal 1) — --model es obligatorio
cd signal-processing
python stream.py --model model-finetuning/models/calibrated.pt --mock

# 5a. Abrir Unity y dar Play  →  game recibe señal por UDP
# 5b. O controlar el mouse con la cabeza + concentración (Terminal 2)
python control/gyro_mouse.py --mock
```

Ver el `README.md` dentro de cada carpeta para instrucciones detalladas.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
