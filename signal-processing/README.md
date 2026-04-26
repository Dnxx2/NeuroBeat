# Signal Processing

Two EEG pipelines running in parallel, sending their outputs to Unity over UDP.

---

## UDP Packet — unified format

Port **5005**, one JSON every **~250 ms**:

```json
{
  "focus":      0.73,
  "alpha":      0.41,
  "beta":       0.62,
  "theta":      0.18,
  "engagement": 0.60,
  "accel_x":    12.4,
  "accel_y":   -8.1,
  "accel_z":  998.3,
  "gyro_x":    -0.5,
  "gyro_y":     1.2,
  "gyro_z":     0.3
}
```

| Field | Source | Range | Description |
|-------|--------|-------|-------------|
| `focus` | EEGNet (model) | 0–1 | Blink probability; saturated to 1.0 when above 0.7 |
| `alpha` | Manual DSP | 0–1 | Normalized frontal alpha power (relaxation) |
| `beta` | Manual DSP | 0–1 | Normalized frontal beta power (concentration) |
| `theta` | Manual DSP | 0–1 | Normalized frontal theta power (drowsiness) |
| `engagement` | Manual DSP | 0–1 | `beta / (alpha + beta)` — classical concentration index |
| `accel_x/y/z` | IMU pass-through | mg | Accelerometer. At rest: X≈0, Y≈0, Z≈1000 (1g) |
| `gyro_x/y/z` | IMU pass-through | °/s | Gyroscope. At rest ≈ 0 |

`alpha + beta + theta ≈ 1.0` (relative proportions). IMU values are physical units, unfiltered.

> **Unicorn Black frame:** 17 channels total: `[0:8]` EEG, `[8:11]` accelerometer, `[11:14]` gyroscope, `[14:17]` battery/counter/validation. REF and GND electrodes are hardware only — no separate data channels.

---

## Usage — combined stream (recommended)

`--model` is **required**. Points to the `.pt` file produced by `train.py`.

```bash
cd signal-processing

# With hardware
python stream.py --model model-finetuning/models/calibrated.pt

# With manual classifier calibration
python stream.py --model model-finetuning/models/calibrated.pt \
                 --calibration manual-filtering/calibration.npz

# Without hardware (synthetic signal for testing Unity)
python stream.py --model model-finetuning/models/calibrated.pt --mock
```

Terminal output:
```
Streaming → udp://127.0.0.1:5005  (Ctrl+C to stop)

focus=0.00 [░░░░░░░░░░░░░░░░░░░░] α=0.41 β=0.62 eng=0.60
```

---

## Usage — standalone pipelines

If the game team needs only one pipeline while the other is being developed:

```bash
# Model only (blink detection)
cd signal-processing/model-finetuning
python -c "
from predict import EEGClassifier
clf = EEGClassifier('models/calibrated.pt')
clf.stream(get_sample, port=5005)
"

# Manual filtering only (bandpower)
cd signal-processing/manual-filtering
python -c "
from realtime import RealtimeProcessor
proc = RealtimeProcessor()
proc.stream_to_unity(get_sample, port=5006)
"
```

---

## Unity — C# receiver

Attach this script to an empty `GameObject` named `EEGReceiver`:

```csharp
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class EEGReceiver : MonoBehaviour
{
    [Header("EEG values — updated every ~250 ms")]
    public float focus      = 0f;   // 0-1, deliberate blink
    public float alpha      = 0f;   // 0-1, relaxation
    public float beta       = 0f;   // 0-1, concentration
    public float theta      = 0f;   // 0-1, drowsiness
    public float engagement = 0f;   // 0-1, beta/(alpha+beta)

    [Header("IMU — unfiltered pass-through")]
    public float accelX = 0f;  // mg, at rest ≈ 0
    public float accelY = 0f;  // mg, at rest ≈ 0
    public float accelZ = 0f;  // mg, at rest ≈ 1000
    public float gyroX  = 0f;  // °/s
    public float gyroY  = 0f;  // °/s
    public float gyroZ  = 0f;  // °/s

    [Header("Config")]
    public int port = 5005;

    UdpClient  _udp;
    Thread     _thread;
    bool       _running;

    float _tFocus, _tAlpha, _tBeta, _tTheta, _tEngagement;
    float _tAccelX, _tAccelY, _tAccelZ, _tGyroX, _tGyroY, _tGyroZ;
    readonly object _lock = new object();

    void Start()
    {
        _udp     = new UdpClient(port);
        _running = true;
        _thread  = new Thread(ReceiveLoop) { IsBackground = true };
        _thread.Start();
    }

    void ReceiveLoop()
    {
        IPEndPoint ep = new IPEndPoint(IPAddress.Any, 0);
        while (_running)
        {
            try
            {
                byte[] data = _udp.Receive(ref ep);
                string json = Encoding.UTF8.GetString(data);
                lock (_lock)
                {
                    _tFocus      = ParseFloat(json, "focus");
                    _tAlpha      = ParseFloat(json, "alpha");
                    _tBeta       = ParseFloat(json, "beta");
                    _tTheta      = ParseFloat(json, "theta");
                    _tEngagement = ParseFloat(json, "engagement");
                    _tAccelX     = ParseFloat(json, "accel_x");
                    _tAccelY     = ParseFloat(json, "accel_y");
                    _tAccelZ     = ParseFloat(json, "accel_z");
                    _tGyroX      = ParseFloat(json, "gyro_x");
                    _tGyroY      = ParseFloat(json, "gyro_y");
                    _tGyroZ      = ParseFloat(json, "gyro_z");
                }
            }
            catch { /* ignore network errors */ }
        }
    }

    void Update()
    {
        lock (_lock)
        {
            focus      = _tFocus;
            alpha      = _tAlpha;
            beta       = _tBeta;
            theta      = _tTheta;
            engagement = _tEngagement;
            accelX     = _tAccelX;
            accelY     = _tAccelY;
            accelZ     = _tAccelZ;
            gyroX      = _tGyroX;
            gyroY      = _tGyroY;
            gyroZ      = _tGyroZ;
        }
    }

    void OnDestroy()
    {
        _running = false;
        _udp?.Close();
        _thread?.Join(200);
    }

    static float ParseFloat(string json, string key)
    {
        int i = json.IndexOf($"\"{key}\":");
        if (i < 0) return 0f;
        int start = json.IndexOf(':', i) + 1;
        int end   = json.IndexOfAny(new[] { ',', '}' }, start);
        return float.TryParse(json.Substring(start, end - start).Trim(),
                              System.Globalization.NumberStyles.Float,
                              System.Globalization.CultureInfo.InvariantCulture,
                              out float v) ? v : 0f;
    }
}
```

### Using it in the game loop

```csharp
public class TileController : MonoBehaviour
{
    public EEGReceiver eeg;
    public float minSpeed = 3f;
    public float maxSpeed = 12f;

    void Update()
    {
        // Tile speed driven by concentration (manual DSP)
        float speed = Mathf.Lerp(minSpeed, maxSpeed, eeg.engagement);
        MoveTiles(speed);

        // Deliberate blink triggers action
        if (eeg.focus > 0.5f)
            TriggerAction();
    }
}
```

---

## `stream.py` internal architecture

```
Acquisition thread  →  fan-out  →  Queue manual  →  Manual thread  ─┐
                                →  Queue model   →  Model thread   ─┤
                                                                     ↓
                                                  results dict (with lock)
                                                                     ↓
                                                   Sender thread → UDP → Unity
```

- Each worker reads from its own queue. If a worker falls behind, excess samples are dropped (`put_nowait`) — acquisition is never blocked.
- The sender sleeps 250 ms between sends regardless of when workers update. Unity always receives the latest available value.
- IMU (accel + gyro) is updated directly in the acquisition thread — bypasses queues, each sample overwrites the previous value.

---

## Files

```
signal-processing/
├── stream.py                    ← MAIN ENTRY POINT — runs both pipelines
├── manual-filtering/            ← Classical DSP pipeline
│   ├── filters.py               CAR + notch + bandpass
│   ├── artifacts.py             ICA with MNE (offline only)
│   ├── features.py              Bandpower + AdaptiveClassifier
│   ├── pipeline.py              Orchestrator + calibration
│   └── realtime.py              RealtimeProcessor + stream_to_unity()
└── model-finetuning/            ← EEGNet pipeline
    ├── calibrate_api.py         Recording session — proprietary g.tec API
    ├── calibrate_generic.py     Recording session — standard UnicornPy SDK
    ├── dataset.py               EEGDataset with augmentation
    ├── model.py                 build_model(), from_pretrained_hub(), freeze_backbone()
    ├── train.py                 Two-phase fine-tuning
    └── predict.py               EEGClassifier + standalone stream()
```

Each subfolder has its own `README.md` with detailed instructions.
