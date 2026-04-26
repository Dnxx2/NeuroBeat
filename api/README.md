# Data Acquisition — Unicorn Black

Scripts for connecting the Unicorn Black via BrainFlow, verifying the signal, and visualizing it in real time.

> These scripts are for **hardware verification and exploration**. The processing pipeline that feeds Unity is in `signal-processing/stream.py`, which uses the proprietary g.tec API (`api/Lib/UnicornPy`) instead of BrainFlow.

---

## Scripts

| File | What it does |
|------|-------------|
| `connection_test.py` | Connects, records 5 s, and reports how many samples arrived — first check that the hardware works |
| `plot_raw.py` | Records 5 s and plots the 8 raw EEG channels with matplotlib |
| `scope.py` | Live oscilloscope — shows all 8 channels updating at 30 fps with a 5 s sliding window |

---

## Install

```bash
pip install -r requirements.txt   # from repo root
```

---

## Serial port configuration

All scripts use `params.serial_port`. Change the value for your system:

| OS | Example |
|----|---------|
| Windows | `COM5` (check in Device Manager) |
| Linux | `/dev/ttyUSB0` |
| macOS | `/dev/tty.usbserial-XXXX` |

---

## Step 1 — Verify connection

Before anything else, run the connection test with the Unicorn powered on and paired:

```bash
python api/connection_test.py
```

Expected output:
```
--- Attempting connection ---
CONNECTION SUCCESSFUL!
Receiving data for 5 seconds...
--- RESULT ---
Samples received: 1250
Full shape: (25, 1250)
Expected sampling rate: 250 Hz
```

- `1250 samples` = 5 s × 250 Hz ✓
- `shape (25, 1250)` = 25 BrainFlow channels (8 EEG + accelerometer + gyroscope + counters)
- If sample count is 0 or an error occurs, check the port and that the Unicorn is powered on

---

## Step 2 — View raw signal (matplotlib)

```bash
python api/plot_raw.py
```

Records 5 s and opens a window with the 8 EEG channels (FZ, C3, CZ, C4, PZ, PO7, OZ, PO8). Useful for verifying good electrode contact before a session.

---

## Step 3 — Live oscilloscope

```bash
python api/scope.py
```

Opens a PyQtGraph window with all 8 channels updating at 30 fps. The signal is automatically centered (mean subtracted) so it is readable regardless of DC offset.

- Neon green trace, last 5 s per channel
- Close the window or Ctrl+C to exit (port is released in `finally`)

---

## Relation to the rest of the repo

```
api/scope.py                 →  confirm signal is arriving correctly (BrainFlow)
signal-processing/stream.py  →  process + classify + send to Unity (proprietary UnicornPy)
```

The calibration and training pipeline (`signal-processing/model-finetuning/calibrate_api.py`) also uses the proprietary API, whose module is at `api/Lib/UnicornPy`.

---

## Unicorn Black channels

| EEG Index | Name | Region |
|-----------|------|--------|
| 0 | FZ | Frontal central |
| 1 | C3 | Left motor |
| 2 | CZ | Central motor |
| 3 | C4 | Right motor |
| 4 | PZ | Parietal |
| 5 | PO7 | Left occipital |
| 6 | OZ | Central occipital |
| 7 | PO8 | Right occipital |

Full frame (proprietary API, 17 float32 channels): `[0:8]` EEG (µV) · `[8:11]` Accel (mg) · `[11:14]` Gyro (°/s) · `[14:17]` Battery/Counter/Validation.
