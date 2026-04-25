# Model Fine-Tuning Pipeline

Fine-tuning de **EEGNetv4** sobre datos del sujeto de prueba.

> **Para enviar a Unity junto con el pipeline manual** usa `../stream.py` — corre ambos en paralelo y manda un solo paquete UDP con todos los valores.
> Este README cubre el entrenamiento y uso **standalone** del modelo.

**Output `focus_score()`:** `float 0.0–1.0` — probabilidad de estado FOCUS.
**Output `stream()`:** JSON por UDP `{"focus": 0.73}` cada ~250 ms.

---

## Cómo funciona

### El modelo base — EEGNetv4

EEGNetv4 es una CNN compacta diseñada para BCI con pocos datos. Tiene dos bloques:

1. **Depthwise temporal convolution** — aprende filtros de frecuencia del EEG (equivalente al bandpass del pipeline manual, pero aprendido de datos reales)
2. **Separable spatial convolution** — aprende qué combinación de los 8 canales maximiza la separabilidad entre clases

El modelo descargado fue preentrenado en **Motor Imagery** (imaginería de mano izquierda vs derecha, Lee 2019). No clasifica FOCUS/RELAX directamente, pero sus capas inferiores ya saben extraer features temporales y espaciales de EEG real. Eso es lo que se transfiere.

### Fine-tuning en dos fases

Con solo 2 minutos de datos, entrenar desde cero sobreajustaría antes de aprender algo útil. El pretrained backbone resuelve esto:

**Fase 1 — backbone congelado (10 epochs, LR=1e-3)**
Solo el clasificador final entrena. El objetivo es redirigir los features existentes hacia FOCUS/RELAX sin tocar los filtros aprendidos. Converge rápido porque es un problema casi lineal.

**Fase 2 — todas las capas (20 epochs, LR=1e-4)**
Con el clasificador ya orientado, se descongelan todas las capas con LR 10× más bajo. Los filtros espaciales se ajustan al sujeto específico sin destruir el preentrenamiento. El LR bajo es crítico: cambios grandes en esta fase arruinarían los pesos base.

### Output del modelo — focus score

La salida principal para el juego es `focus_score()`, que devuelve `predict_proba()[1]` — la probabilidad de que el estado sea FOCUS. Es un float entre 0.0 y 1.0:

- `0.0` — completamente relajado
- `0.5` — estado neutro / transición
- `1.0` — concentración máxima

Unity recibe este valor por UDP y lo mapea a velocidad de tiles, multiplicadores de puntos, efectos visuales, etc.

### Data augmentation

Con ~2 minutos de datos el dataset es pequeño. Durante el entrenamiento cada epoch pasa por:
- **Ruido gaussiano leve** (σ = 0.5 µV) — variabilidad natural de la señal
- **Shift temporal aleatorio** (±100 ms) — invariancia a pequeñas variaciones de timing

---

## ¿Necesito descargar algo manualmente?

**No.** La primera vez que corres `train.py`, braindecode descarga ~10 MB desde Hugging Face (`PierreGtch/EEGNetv4`) y los cachea en `~/.cache/huggingface/`. Las siguientes ejecuciones usan el caché local.

---

## Flujo completo: de cero a tiempo real

```
[1] pip install -r requirements.txt
[2] python calibrate.py   →  graba 2 min con el Unicorn
[3] python train.py       →  descarga HF + fine-tune + guarda modelo
[4] clf.stream(...)       →  loop UDP al juego
```

---

## Paso 1 — Instalar

```bash
cd signal-processing/model-finetuning
pip install -r requirements.txt
```

`braindecode[hub]` incluye el soporte de Hugging Face. Sin el `[hub]` el `from_pretrained()` no existe.

---

## Paso 2 — Grabar calibración

```bash
# Con el Unicorn Black conectado
python calibrate.py --output data/subject_01.npz

# Sin hardware (señal aleatoria — para probar el pipeline)
python calibrate.py --output data/subject_01.npz --mock
```

El script hace esto:
1. Muestra instrucciones en pantalla ("cierra los ojos", "concéntrate")
2. Graba 30 s × 2 clases × 2 rondas = **2 minutos totales**
3. Divide cada grabación en ventanas de 2 s con 50% de solapamiento
4. Guarda `data/subject_01.npz` con arrays `epochs (n, 500, 8)` y `labels (n,)`

Los `.npz` están en `.gitignore`. Verificar que se grabó bien:
```python
import numpy as np
d = np.load('data/subject_01.npz')
print(d['epochs'].shape)   # ej. (240, 500, 8)
print(d['labels'])          # [0,0,...,1,1,...]  0=RELAX, 1=FOCUS
```

---

## Paso 3 — Entrenar

```bash
python train.py --data data/subject_01.npz --output models/subject_01.pt
```

Salida esperada:
```
Descargando weights desde Hugging Face (~10 MB, primera vez)...
── Fase 1/30: backbone congelado ──
Epoch   1/30  val_acc=0.541
Epoch   2/30  val_acc=0.623
  -> checkpoint guardado  (mejor=0.623)
...
── Fase 2/30: todas las capas, LR=1.0e-04 ──
Epoch  11/30  val_acc=0.741
  -> checkpoint guardado  (mejor=0.741)
...
Listo. Mejor val_acc: 0.821  →  models/subject_01.pt
```

Parámetros opcionales:
```bash
python train.py \
  --data data/subject_01.npz \
  --output models/subject_01.pt \
  --phase1-epochs 10 \
  --phase2-epochs 20 \
  --lr 1e-3 \
  --batch-size 16
```

---

## Paso 4 — Streaming en tiempo real al juego

### Opción A — usando `stream()` (recomendado)

```python
from predict import EEGClassifier

clf = EEGClassifier('models/subject_01.pt')

# Conectar Unicorn y definir get_sample
import UnicornPy, numpy as np
unicorn = UnicornPy.Unicorn(UnicornPy.Unicorn.GetAvailableDevices()[0])
unicorn.StartAcquisition(TestSignalEnabled=False)
frame = np.zeros((1, 13), dtype=np.float32)

def get_sample():
    unicorn.GetData(1, frame)
    return frame[0, :8].copy()

# Stream — envía {"focus": 0.73} por UDP cada ~250 ms
clf.stream(get_sample, host='127.0.0.1', port=5005)
```

En la terminal verás:
```
Streaming focus score → udp://127.0.0.1:5005  (Ctrl+C para detener)
focus=0.731  ██████████████░░░░░░
```

### Opción B — control manual del loop

```python
from collections import deque
import numpy as np
from predict import EEGClassifier

clf    = EEGClassifier('models/subject_01.pt')
buffer = deque(maxlen=500)
tick   = 0

while True:
    sample = get_sample()       # ndarray (8,)
    buffer.append(sample)
    tick += 1

    if len(buffer) == 500 and tick % 62 == 0:
        score = clf.focus_score(np.array(buffer))   # float 0.0–1.0
        # usar score como quieras antes de enviarlo
        send_to_game(score)
```

### Recibir en Unity (C#)

```csharp
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class EEGReceiver : MonoBehaviour
{
    UdpClient udp;
    public float focusScore = 0f;

    void Start()
    {
        udp = new UdpClient(5005);
        udp.BeginReceive(OnReceive, null);
    }

    void OnReceive(System.IAsyncResult result)
    {
        IPEndPoint ep = null;
        byte[] data   = udp.EndReceive(result, ref ep);
        string json   = Encoding.UTF8.GetString(data);
        // parse {"focus": 0.73}  →  focusScore
        focusScore = SimpleJSON.Parse(json)["focus"].AsFloat;
        udp.BeginReceive(OnReceive, null);
    }
}
```

Luego en tu game loop:
```csharp
tileSpeed = Mathf.Lerp(minSpeed, maxSpeed, eegReceiver.focusScore);
```

---

## Referencia de módulos

| Archivo | Responsabilidad |
|---------|----------------|
| `calibrate.py` | Sesión guiada 2 min → `.npz` con epochs etiquetados |
| `dataset.py` | `torch.Dataset` + augmentation (ruido + time shift) |
| `model.py` | EEGNetv4, `from_pretrained_hub()`, `freeze_backbone()` |
| `train.py` | Fine-tuning en dos fases, checkpoint por mejor val_acc |
| `predict.py` | `focus_score()` → float, `stream()` → UDP loop, `predict_proba()` → array |

---

## Extender a más clases

1. Agregar entradas a `CLASSES` en `calibrate.py`
2. Actualizar `LABEL_MAP` en `predict.py`
3. Re-grabar calibración y re-entrenar
