# Signal Processing

Dos pipelines de EEG que corren en paralelo y envían sus salidas a Unity por UDP.

---

## Paquete UDP — formato unificado

Puerto **5005**, un JSON cada **~250 ms**:

```json
{
  "focus":      0.73,
  "alpha":      0.41,
  "beta":       0.62,
  "theta":      0.18,
  "engagement": 0.60
}
```

| Campo | Fuente | Rango | Qué representa |
|-------|--------|-------|----------------|
| `focus` | EEGNet (modelo) | 0–1 | Probabilidad de estado FOCUS |
| `alpha` | DSP manual | 0–1 | Potencia alpha frontal normalizada (relajación) |
| `beta` | DSP manual | 0–1 | Potencia beta frontal normalizada (concentración) |
| `theta` | DSP manual | 0–1 | Potencia theta frontal normalizada (somnolencia) |
| `engagement` | DSP manual | 0–1 | `beta / (alpha + beta)` — índice de concentración clásico |

Todos los valores flotan entre 0 y 1. `alpha + beta + theta ≈ 1.0` (son proporciones relativas).

---

## Uso — stream combinado (recomendado)

```bash
cd signal-processing

# Con hardware
python stream.py --model model-finetuning/models/subject_01.pt

# Con calibración del clasificador manual
python stream.py --model model-finetuning/models/subject_01.pt \
                 --calibration manual-filtering/calibration.npz

# Sin hardware (señal sintética para probar Unity)
python stream.py --model model-finetuning/models/subject_01.pt --mock
```

Salida en terminal:
```
Streaming → udp://127.0.0.1:5005  (Ctrl+C para detener)

focus=0.73 [██████████████░░░░░░] α=0.41 β=0.62 eng=0.60
```

---

## Uso — pipelines independientes

Si el equipo de juego quiere solo un pipeline mientras el otro se desarrolla:

```bash
# Solo el modelo (foco puro)
cd model-finetuning
python -c "
from predict import EEGClassifier
clf = EEGClassifier('models/subject_01.pt')
clf.stream(get_sample, port=5005)
"

# Solo el filtrado manual (bandpower)
cd manual-filtering
python -c "
from realtime import RealtimeProcessor
proc = RealtimeProcessor()
proc.stream_to_unity(get_sample, port=5006)
"
```

---

## Unity — receptor C#

Pegar este script en un `GameObject` vacío llamado `EEGReceiver`:

```csharp
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class EEGReceiver : MonoBehaviour
{
    [Header("Valores EEG — leer desde otros scripts")]
    public float focus      = 0f;   // 0-1, del modelo
    public float alpha      = 0f;   // 0-1, relajación
    public float beta       = 0f;   // 0-1, concentración
    public float theta      = 0f;   // 0-1, somnolencia
    public float engagement = 0f;   // 0-1, beta/(alpha+beta)

    [Header("Config")]
    public int port = 5005;

    UdpClient  _udp;
    Thread     _thread;
    bool       _running;

    // Buffer thread-safe
    float _tFocus, _tAlpha, _tBeta, _tTheta, _tEngagement;
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
                // Parseo manual — sin dependencias externas
                lock (_lock)
                {
                    _tFocus      = ParseFloat(json, "focus");
                    _tAlpha      = ParseFloat(json, "alpha");
                    _tBeta       = ParseFloat(json, "beta");
                    _tTheta      = ParseFloat(json, "theta");
                    _tEngagement = ParseFloat(json, "engagement");
                }
            }
            catch { /* ignorar errores de red */ }
        }
    }

    // Copiar al main thread en Update (Unity solo permite tocar variables en main thread)
    void Update()
    {
        lock (_lock)
        {
            focus      = _tFocus;
            alpha      = _tAlpha;
            beta       = _tBeta;
            theta      = _tTheta;
            engagement = _tEngagement;
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

### Usarlo en el game loop

```csharp
public class TileController : MonoBehaviour
{
    public EEGReceiver eeg;
    public float minSpeed = 3f;
    public float maxSpeed = 12f;

    void Update()
    {
        // Velocidad de tiles controlada por concentración del modelo
        float speed = Mathf.Lerp(minSpeed, maxSpeed, eeg.focus);
        MoveTiles(speed);

        // Multiplicador de puntos por concentración sostenida (DSP manual)
        float multiplier = eeg.engagement > 0.7f ? 2f : 1f;
        ApplyMultiplier(multiplier);
    }
}
```

---

## Arquitectura interna de `stream.py`

```
Thread adquisición  →  fan-out  →  Queue manual  →  Thread manual  ─┐
                                →  Queue modelo  →  Thread modelo  ─┤
                                                                     ↓
                                              results dict (con lock)
                                                                     ↓
                                                    Thread sender → UDP → Unity
```

- Cada worker lee de su propia cola. Si un worker se atrasa, las muestras extras se descartan (`put_nowait`) — no bloquea la adquisición.
- El sender duerme 250 ms entre envíos independientemente de cuándo actualicen los workers. Unity siempre recibe el valor más reciente disponible.

---

## Archivos

```
signal-processing/
├── stream.py                    ← ENTRADA PRINCIPAL — corre ambos pipelines
├── manual-filtering/            ← Pipeline DSP clásico
│   ├── filters.py               CAR + notch + bandpass
│   ├── artifacts.py             ICA con MNE (offline)
│   ├── features.py              Bandpower + AdaptiveClassifier
│   ├── pipeline.py              Orquestador + calibración
│   └── realtime.py              RealtimeProcessor + stream_to_unity()
└── model-finetuning/            ← Pipeline EEGNet
    ├── calibrate.py             Sesión de grabación etiquetada
    ├── train.py                 Fine-tuning en dos fases
    └── predict.py               EEGClassifier + stream() standalone
```

Cada sub-carpeta tiene su propio `README.md` con instrucciones detalladas de entrenamiento y uso independiente.
