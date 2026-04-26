# NeuroBeat

A Brain.io hackathon project: a real-time game controlled entirely by brainwave signals captured via the **Unicorn Black** EEG headset.

## Overview

NeuroBeat translates raw EEG signals into game inputs. The player controls a Unity rhythm game using brain activity and head movement — deliberate blinks trigger in-game actions while the gyroscope moves the OS cursor. The pipeline covers EEG acquisition, signal processing, real-time UDP streaming, and OS-level control.

## Repository Structure

```
NeuroBeat/
├── api/                    # Hardware verification scripts (BrainFlow or Propietary Unicorn PythonAPI)
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

| Sub-pipeline | What it does | Output |
|---|---|---|
| `manual-filtering/` | Notch → Bandpass → ICA → bandpower α/β/θ | Normalized scores 0–1 |
| `model-finetuning/` | EEGNet trained to detect deliberate blinks | `focus` float 0–1 (saturated to 1.0 on blink detection) |

## UDP Stream — unified format

`signal-processing/stream.py` broadcasts a JSON on **UDP:5005** every ~250 ms:

```json
{
  "focus": 0.0,   "alpha": 0.41,  "beta": 0.62,  "theta": 0.18,  "engagement": 0.60,
  "accel_x": 12.4,  "accel_y": -8.1,  "accel_z": 998.3,
  "gyro_x": -0.5,   "gyro_y":  1.2,   "gyro_z":   0.3
}
```

`focus` is a float 0–1: rises with deliberate blink probability and saturates to 1.0 above 0.7. Unity consumes it via `EEGMouseClicker.cs` (threshold 0.95) to fire actions only when a blink is detected with high confidence.

Multiple consumers can bind to the same port (SO_REUSEADDR — all receive the same datagram):
- **Unity** `game/Assets/Scripts/Data_Receiver/EEGReceiver.cs` — game input (blink trigger, bandpower available)
- **gyro_mouse** `control/gyro_mouse.py` — moves OS cursor with gyroscope, clicks on blink

## Quick Start

```bash
# 1. Install all dependencies
pip install -r requirements.txt

# 2. Calibrate subject (--mock = no hardware needed)
python signal-processing/model-finetuning/calibrate_api.py \
    --output signal-processing/model-finetuning/data/calibration.npz --mock

# 3. Train model
python signal-processing/model-finetuning/train.py \
    --data signal-processing/model-finetuning/data/calibration.npz \
    --output signal-processing/model-finetuning/models/calibrated.pt

# 4. Start the streamer (Terminal 1) — --model is required
cd signal-processing
python stream.py --model model-finetuning/models/calibrated.pt --mock

# 5a. Open Unity and press Play  →  game receives signal over UDP
# 5b. Or control the mouse with your head + blinks (Terminal 2)
python control/gyro_mouse.py --mock
```

See the `README.md` in each subfolder for detailed instructions.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
