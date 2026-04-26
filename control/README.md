# Control

Scripts that translate EEG and IMU signals into OS-level control actions.

---

## Scripts

| File | What it does |
|------|-------------|
| `gyro_mouse.py` | Moves the cursor with the gyroscope and left-clicks on deliberate blink |

---

## `gyro_mouse.py`

### Data source

Reads the UDP packet emitted by `signal-processing/stream.py` on port **5005**.
Uses `SO_REUSEADDR` to share the port with Unity — both receive the same datagram simultaneously, no conflict.

```
stream.py → UDP:5005 ──┬── Unity  (EEGReceiver.cs)   game input
                       └── gyro_mouse.py              OS mouse control
```

Fields used from the packet:

| Field | Use |
|-------|-----|
| `gyro_x` | Pitch (nodding) → cursor Y movement |
| `gyro_y` | Yaw (head turn) → cursor X movement |
| `focus` | Blink probability (0–1, saturated to 1.0 when > 0.7) → triggers left click |

### Click logic — Schmitt trigger

A click **does not fire on a single focus spike**. It uses two thresholds:

```
focus
  1.0 ─────────────────────────────────────
  0.7 ─ ─ ─ ─ upper_threshold ─ ─ ─ ─ ─ ─  ← needs N packets here → CLICK
                                             ← after click: WAITING
  0.45 ─ ─ ─ lower_threshold ─ ─ ─ ─ ─ ─  ← drop here to re-arm
  0.0 ─────────────────────────────────────
```

1. **Armed** (`arm [0/N]`): counts consecutive packets with `focus ≥ threshold`
2. **Click**: when N packets reached → `pyautogui.click()` → enters WAITING
3. **Waiting** (`wait`): ignores focus until it drops below `threshold − hysteresis`
4. Returns to **Armed**

With defaults (threshold=0.70, hysteresis=0.25, confirm=3):
- **3 packets × 250 ms = 0.75 s** of sustained focus required to click
- Focus must then drop to **≤ 0.45** before the next click can fire

### Gyroscope processing

```
raw signal  →  deadzone (ignores < 2°/s)  →  EMA (smoothing)  →  moveRel(dx, dy)
```

- **Deadzone**: filters gyroscope drift at rest (jitter ≈ 0–1°/s)
- **EMA**: smooths sudden movements without adding perceptible latency

### Usage

**Prerequisites:**
```bash
pip install -r requirements.txt   # from repo root
```

**With hardware (normal mode):**
```bash
# Terminal 1 — process EEG and stream
cd signal-processing
python stream.py --model model-finetuning/models/calibrated.pt

# Terminal 2 — mouse control
python control/gyro_mouse.py
```

**Without hardware (full mock):**
```bash
python control/gyro_mouse.py --mock
```

Mock mode generates a synthetic circular gyroscope and a pulsing focus value that reaches the threshold every ~10 s, allowing verification that click works without connecting the Unicorn.

**Stop:** `Ctrl+C` or move the mouse to the **top-left corner** of the screen (pyautogui failsafe).

### Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--threshold` | `0.70` | Minimum focus to count toward a click |
| `--hysteresis` | `0.25` | How far focus must drop after a click to re-arm |
| `--confirm` | `3` | Consecutive packets above threshold = 0.75 s |
| `--sensitivity` | `1.0` | °/s → pixels scale factor |
| `--deadzone` | `2.0` | Minimum °/s to move cursor |
| `--smoothing` | `0.35` | EMA coefficient (0 = no smoothing) |
| `--rate` | `30` | Cursor update rate in Hz |
| `--port` | `5005` | UDP port of the streamer |

```bash
# Example: easier click, more sensitive movement
python control/gyro_mouse.py --threshold 0.60 --confirm 2 --sensitivity 3
```

### Terminal display

```
focus=0.73 [###########    ] arm [2/3]  dx=  +8 dy=  -3
focus=0.81 [############   ] arm [3/3]  dx=  +5 dy=  +1  *** CLICK ***
focus=0.78 [############   ] wait       dx=  +3 dy=  +0
focus=0.41 [######         ] arm [0/3]  dx=  +0 dy=  +0
```

- `arm [N/3]` — armed, N packets counted toward the click
- `wait` — waiting for focus to drop below the lower threshold to re-arm
- `*** CLICK ***` — click fired this frame
