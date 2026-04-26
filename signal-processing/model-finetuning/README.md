# Model Fine-Tuning Pipeline

Fine-tuning de **EEGNet** sobre datos del sujeto de prueba.

> **Para enviar a Unity junto con el pipeline manual** usa `../stream.py` — corre ambos en paralelo y manda un solo paquete UDP con todos los valores.
> Este README cubre el entrenamiento y uso **standalone** del modelo.

**Output `focus_score()`:** `float 0.0–1.0` — probabilidad de estado FOCUS.
**Output `stream()`:** JSON por UDP `{"focus": 0.73}` cada ~250 ms.

---

## Cómo funciona

### El modelo — EEGNet

EEGNet es una CNN compacta diseñada para BCI con pocos datos. Tiene dos bloques:

1. **Depthwise temporal convolution** — aprende filtros de frecuencia del EEG (equivalente al bandpass del pipeline manual, pero aprendido de datos reales)
2. **Separable spatial convolution** — aprende qué combinación de los 8 canales maximiza la separabilidad entre clases

El modelo se inicializa con pesos aleatorios y se entrena desde cero sobre los datos de calibración del sujeto. `from_pretrained_hub()` en `model.py` existe como utilidad para cargar pesos pre-entrenados de Hugging Face (`PierreGtch/EEGNetv4`, `EEGNetv4_Lee2019_MI/model-params.pkl`), pero no es el flujo por defecto — el flujo estándar usa `build_model()` directamente.

### Fine-tuning en dos fases

Con solo 2 minutos de datos, el entrenamiento se divide en dos fases:

**Fase 1 — backbone congelado (10 epochs, LR=1e-3)**
Solo el clasificador final entrena. Converge rápido porque es un problema casi lineal.

**Fase 2 — todas las capas (20 epochs, LR=1e-4)**
Con el clasificador orientado, se descongelan todas las capas con LR 10× más bajo. Los filtros espaciales se ajustan al sujeto sin destruir lo aprendido en fase 1.

### Inferencia — focus score e inversión de parpadeo

`focus_score()` devuelve `predict_proba()[1]` — probabilidad de FOCUS.

En `stream.py`, la salida del modelo se invierte y se envía como `focus`:
```python
prob_parpadeo = 1.0 - raw_score      # invierte la salida del modelo
if prob_parpadeo > 0.7:
    score_filtrado = 1.0             # blink detectado con alta confianza
else:
    score_filtrado = prob_parpadeo   # valor continuo 0–0.7
```
`focus` es un float 0–1. Valores ≥ 0.7 se saturan a 1.0 (parpadeo detectado con certeza). Por debajo de 0.7 el valor es continuo. Unity usa `EEGMouseClicker` con umbral 0.95 para disparar acciones solo cuando `focus = 1.0`.

### Data augmentation

Con ~2 minutos de datos el dataset es pequeño. Durante el entrenamiento cada epoch pasa por:
- **Ruido gaussiano leve** (σ = 0.5 µV) — variabilidad natural de la señal
- **Shift temporal aleatorio** (±100 ms) — invariancia a variaciones de timing

---

## Flujo completo: de cero a tiempo real

```
[1] pip install -r requirements.txt   (desde la raíz del repo)
[2] python calibrate_api.py     →  graba 2 min con el Unicorn (API propietaria g.tec)
    python calibrate_generic.py →  alternativa con SDK estándar de UnicornPy
[3] python train.py             →  fine-tune + guarda modelo como models/calibrated.pt
[4] cd .. && python stream.py --model model-finetuning/models/calibrated.pt
```

---

## Paso 1 — Instalar

```bash
pip install -r requirements.txt   # desde la raíz del repo
```

---

## Paso 2 — Grabar calibración

Hay dos scripts de calibración según la API disponible:

| Script | API usada | Cuándo usarlo |
|--------|-----------|---------------|
| `calibrate_api.py` | UnicornPy propietaria (`api/Lib`) | Hardware g.tec con SDK completo |
| `calibrate_generic.py` | UnicornPy SDK estándar | Instalación estándar de UnicornPy |

```bash
# Con el Unicorn Black conectado (API propietaria — recomendado)
python calibrate_api.py --output data/calibration.npz

# Con SDK estándar
python calibrate_generic.py --output data/calibration.npz

# Sin hardware (señal aleatoria — para probar el pipeline)
python calibrate_api.py --output data/calibration.npz --mock
```

El script hace esto:
1. Muestra instrucciones en pantalla
2. Graba 30 s × 2 clases × 2 rondas = **2 minutos totales**
   - Clase 0 — RELAX: "Mantén los ojos abiertos"
   - Clase 1 — FOCUS: "Parpadea durante 30 segundos"
3. Divide cada grabación en ventanas de 2 s con 50% de solapamiento
4. Guarda `data/calibration.npz` con arrays `epochs (n, 500, 1)` y `labels (n,)`

> **Nota:** El directorio `data/` se crea automáticamente si no existe.

Los `.npz` están en `.gitignore`. Verificar que se grabó bien:
```python
import numpy as np
d = np.load('data/calibration.npz')
print(d['epochs'].shape)   # ej. (240, 500, 1)
print(d['labels'])          # [0,0,...,1,1,...]  0=RELAX, 1=FOCUS
```

---

## Paso 3 — Entrenar

```bash
# Desde la raíz del repo
python signal-processing/model-finetuning/train.py \
    --data signal-processing/model-finetuning/data/calibration.npz \
    --output signal-processing/model-finetuning/models/calibrated.pt
```

O desde dentro de la carpeta:
```bash
cd signal-processing/model-finetuning
python train.py --data data/calibration.npz --output models/calibrated.pt
```

Salida esperada:
```
── Fase 1/30: backbone congelado ──
Epoch   1/30  val_acc=0.541
Epoch   2/30  val_acc=0.623
  -> checkpoint guardado  (mejor=0.623)
...
── Fase 2/30: todas las capas, LR=1.0e-04 ──
Epoch  11/30  val_acc=0.741
  -> checkpoint guardado  (mejor=0.741)
...
Listo. Mejor val_acc: 0.821  →  models/calibrated.pt
```

> **Nota:** El directorio `models/` se crea automáticamente si no existe.

Parámetros opcionales:
```bash
python train.py \
  --data data/calibration.npz \
  --output models/calibrated.pt \
  --phase1-epochs 10 \
  --phase2-epochs 20 \
  --lr 1e-3 \
  --batch-size 16
```

---

## Paso 4 — Streaming en tiempo real al juego

### Recomendado — stream combinado

```bash
cd signal-processing
python stream.py --model model-finetuning/models/calibrated.pt
```

Este es el método recomendado: corre ambos pipelines (EEGNet + filtrado manual) en paralelo y envía un único paquete UDP con todos los valores.

### Standalone — solo el modelo

```python
from predict import EEGClassifier
clf = EEGClassifier('models/calibrated.pt')

# focus_score retorna float 0.0–1.0
score = clf.focus_score(window_500x1)

# Stream autónomo — envía {"focus": 0.73} por UDP cada ~250 ms
clf.stream(get_sample, host='127.0.0.1', port=5005)
```

---

## Referencia de módulos

| Archivo | Responsabilidad |
|---------|----------------|
| `calibrate_api.py` | Sesión guiada 2 min → `.npz` — usa API propietaria g.tec (`api/Lib`) |
| `calibrate_generic.py` | Sesión guiada 2 min → `.npz` — usa SDK estándar de UnicornPy |
| `dataset.py` | `torch.Dataset` + augmentation (ruido + time shift) |
| `model.py` | EEGNet, `build_model()`, `from_pretrained_hub()`, `freeze_backbone()` |
| `train.py` | Fine-tuning en dos fases, checkpoint por mejor val_acc |
| `predict.py` | `focus_score()` → float, `stream()` → UDP loop |

---

## Archivos de datos y modelos

Los archivos `.npz` (datos) y `.pt` (pesos) están en `.gitignore`. Estructuras esperadas:

```
signal-processing/model-finetuning/
├── data/
│   └── calibration.npz     ← generado por calibrate_api.py / calibrate_generic.py
└── models/
    └── calibrated.pt       ← generado por train.py
```

---

## Cargar pesos pre-entrenados de Hugging Face (opcional)

Si quieres partir desde pesos pre-entrenados en lugar de inicialización aleatoria:

```python
from model import from_pretrained_hub
model = from_pretrained_hub(n_classes=2)
# Pesos: PierreGtch/EEGNetv4 → EEGNetv4_Lee2019_MI/model-params.pkl
```

Luego pasa el modelo a `train()` o guárdalo como punto de partida para el fine-tuning.
