# Manual Filtering Pipeline

Pipeline clásico de DSP para limpiar señal EEG del Unicorn Black en tiempo real.

> **Para enviar a Unity junto con el modelo** usa `../stream.py` — corre ambos pipelines en paralelo y manda un solo paquete UDP con todos los valores.
> Este README cubre el uso **standalone** del pipeline manual.

**Output `push()`:** `ndarray (500, 8)` — señal limpia, z-score normalizada por canal.
**Output `stream_to_unity()`:** JSON por UDP `{"alpha": 0.41, "beta": 0.62, "theta": 0.18, "engagement": 0.60}`

---

## Cómo funciona — de la señal cruda al output limpio

### El problema

El Unicorn Black usa electrodos secos, lo que introduce más ruido que un sistema de laboratorio:

- **Ruido de línea eléctrica** — pico de 60 Hz de la red eléctrica del cuarto
- **Drift de baja frecuencia** — movimiento lento de electrodos, sudor
- **Artefactos de parpadeo** — cada parpadeo genera ~100–200 µV en FZ que enmascara la señal cerebral
- **Ruido compartido entre canales** — interferencia electromagnética que llega igual a todos los electrodos

El pipeline elimina cada tipo de ruido en orden.

### Paso 1 — Common Average Reference (CAR)

```
canal[n] = canal[n] − promedio(todos los canales)[n]
```

En cada instante de tiempo se resta el promedio de los 8 canales a cada canal. Elimina cualquier ruido que sea idéntico en todos los electrodos simultáneamente: variaciones del amplificador, interferencia ambiental. Es el paso más barato y uno de los más efectivos para electrodos secos.

### Paso 2 — Filtro Notch (60 Hz)

Elimina el pico exacto de 60 Hz de la red eléctrica. Filtro IIR notch con Q=30: elimina solo ±2 Hz alrededor de 60 Hz sin distorsionar el resto.

### Paso 3 — Filtro Bandpass (0.5–40 Hz)

Todo lo que está fuera del rango de interés cerebral se corta:
- Por debajo de 0.5 Hz: drift de electrodos, sudor
- Por encima de 40 Hz: ruido muscular (EMG), artefactos de alta frecuencia

Butterworth orden 4 con `filtfilt` (fase cero — no desplaza eventos temporalmente).

### Paso 4 — ICA con detección de parpadeos (solo offline)

ICA descompone los 8 canales en 8 fuentes independientes. MNE identifica automáticamente cuáles son parpadeos correlacionando cada componente con **FZ** (el electrodo más cercano a los ojos en el Unicorn). Los componentes de parpadeo se zerean y la señal se reconstruye.

**Por qué se omite en tiempo real:** ICA necesita ajustarse sobre un bloque largo (>10 s). En streaming muestra por muestra introduciría segundos de latencia. En tiempo real solo corre CAR + notch + bandpass, que son instantáneos.

### Paso 5 — Z-score normalización por canal (tiempo real)

`RunningNormalizer` mantiene la media y varianza acumuladas de cada canal usando el algoritmo de Welford (online, sin almacenar el historial). Después de un warmup de 5 s, normaliza cada ventana para que cada canal tenga media ≈ 0 y varianza ≈ 1.

Esto es necesario porque:
- La amplitud absoluta del EEG varía entre sesiones, sujetos y niveles de impedancia
- Sin normalización, un canal con mala conexión dominaría el análisis
- Con z-score todos los canales contribuyen por igual independientemente de su escala

### Output final

Cada 250 ms `push()` devuelve `ndarray (500, 8)` — ventana de 2 s, 8 canales, limpia y normalizada. El equipo de juego puede usarla directamente, extraer features adicionales, o pasarla a cualquier clasificador propio.

---

## Flujo completo: de cero a tiempo real

```
[1] pip install -r requirements.txt
[2] Grabar calibración offline (para el clasificador adaptativo, opcional)
[3] Calibrar el clasificador y guardar
[4] Correr el loop de tiempo real
```

---

## Paso 1 — Instalar

```bash
cd signal-processing/manual-filtering
pip install -r requirements.txt
```

---

## Paso 2 — Grabar calibración offline (opcional)

Si quieres usar el `AdaptiveClassifier` (nearest-centroid calibrado al sujeto), necesitas una grabación etiquetada de ~2 min. Si solo necesitas la señal limpia para procesarla tú mismo, salta al Paso 4 directamente.

```python
import numpy as np

# Graba con el Unicorn — sustituye con tu loop de adquisición real
relax_samples, focus_samples = [], []

print("RELAX — cierra los ojos, respira lento (2 min)")
for _ in range(250 * 120):
    relax_samples.append(unicorn.get_sample())   # ndarray (8,)

print("FOCUS — concéntrate, cuenta de 3 en 3 (2 min)")
for _ in range(250 * 120):
    focus_samples.append(unicorn.get_sample())

relax_rec = np.array(relax_samples)   # (30000, 8)
focus_rec = np.array(focus_samples)   # (30000, 8)
```

---

## Paso 3 — Calibrar y guardar (opcional)

```python
from pipeline import EEGPipeline

pipeline = EEGPipeline(fs=250, use_ica=True)

pipeline.calibrate({
    'RELAX': relax_rec,
    'FOCUS': focus_rec,
})

pipeline.save_calibration('calibration.npz')
```

Esto procesa cada grabación con el pipeline completo, divide en epochs de 2 s, descarta los ruidosos (>100 µV), extrae el vector de 32 features (bandpower δθαβ × 8 canales) de cada epoch y calcula el centroide z-normalizado de cada clase. El archivo `.npz` pesa unos KB.

---

## Paso 4 — Tiempo real

### Loop básico — señal limpia para procesamiento libre

```python
from pipeline import EEGPipeline
from realtime import RealtimeProcessor

pipeline = EEGPipeline(fs=250, use_ica=False)
proc     = RealtimeProcessor(pipeline=pipeline)

while True:
    sample = unicorn.get_sample()       # ndarray (8,)
    window = proc.push(sample)

    if window is not None:
        # window: ndarray (500, 8) — señal limpia, z-score por canal
        # Los primeros ~5 s devuelve None mientras calienta el normalizador
        pass
```

### Extraer bandpower de la señal limpia

```python
from features import extract_features, BANDS
import numpy as np

if window is not None:
    feats = extract_features(window)   # ndarray (32,)
    # Orden: [FZ_delta, FZ_theta, FZ_alpha, FZ_beta, C3_delta, ...]

    # Alpha frontal promedio (canales FZ, C3, CZ, C4 = índices 0-3)
    alpha_frontal = np.mean([feats[ch*4 + 2] for ch in range(4)])
    beta_frontal  = np.mean([feats[ch*4 + 3] for ch in range(4)])
    focus_ratio   = beta_frontal / (alpha_frontal + beta_frontal + 1e-9)
```

### Enviar a Unity directamente (standalone, sin el modelo)

```python
from pipeline import EEGPipeline
from realtime import RealtimeProcessor

pipeline = EEGPipeline(fs=250, use_ica=False)
proc     = RealtimeProcessor(pipeline=pipeline)

# Envía {"alpha":0.41,"beta":0.62,"theta":0.18,"engagement":0.60} por UDP cada ~250 ms
# Puerto 5006 para no chocar con el stream combinado (5005)
proc.stream_to_unity(get_sample, host='127.0.0.1', port=5006)
```

---

### Usar el clasificador adaptativo (si se calibró)

```python
from pipeline import EEGPipeline
from realtime import RealtimeProcessor
from features import extract_features

pipeline = EEGPipeline(fs=250, use_ica=False)
pipeline.load_calibration('calibration.npz')
proc = RealtimeProcessor(pipeline=pipeline)

while True:
    sample = unicorn.get_sample()
    window = proc.push(sample)

    if window is not None:
        feats = extract_features(window)
        state = pipeline.classifier.predict(feats)   # 'FOCUS' | 'RELAX'
```

### Procesamiento offline (batch sobre una grabación completa)

```python
from pipeline import EEGPipeline
import numpy as np

pipeline = EEGPipeline(fs=250, use_ica=True)   # ICA activado en offline

raw = np.loadtxt('session.csv', delimiter=',')[:, :8]   # (n_samples, 8)

# Procesar ventana única
clean = pipeline.process(raw[:500])   # (500, 8)

# Procesar y extraer features de epochs
epochs = raw.reshape(-1, 500, 8)
clean_epochs, features = pipeline.process_epochs(epochs)
# features: (n_epochs_limpios, 32)
```

---

## Referencia de módulos

### `filters.py`
- `common_average_reference(eeg)` — resta el promedio entre canales en cada muestra
- `notch(signal, fs, freq, Q)` — filtro notch IIR, elimina pico de línea eléctrica
- `bandpass(signal, fs, lowcut, highcut, order)` — Butterworth fase cero
- `apply_filters(eeg, fs, notch_freq)` — aplica CAR → notch → bandpass a todos los canales

### `artifacts.py`
- `remove_artifacts_mne(eeg, fs)` — ICA con MNE + detección automática de parpadeos via FZ. Solo offline (>10 s de señal).
- `reject_epochs(epochs, threshold_uv)` — máscara booleana; descarta epochs con pico-a-pico > umbral

### `features.py`
- `extract_features(eeg, fs)` — Welch PSD → bandpower δθαβ por canal → vector (32,)
- `AdaptiveClassifier` — nearest centroid z-normalizado. Métodos: `calibrate()`, `predict()`, `save()`, `load()`

### `pipeline.py`
- `EEGPipeline` — orquesta todo. Métodos: `process()`, `process_epochs()`, `calibrate()`, `classify()`, `save_calibration()`, `load_calibration()`

### `realtime.py`
- `RunningNormalizer` — z-score online (Welford). Propiedades: `ready`, `normalize(signal)`
- `RealtimeProcessor` — buffer circular + ventana deslizante. `push(sample)` → `ndarray (500, 8)` limpio y normalizado cada 250 ms, o `None`

---

## Layout del Unicorn Black

| Índice | Canal | Región |
|--------|-------|--------|
| 0 | FZ | Frontal central — proxy EOG (más cercano a los ojos) |
| 1 | C3 | Motor izquierdo |
| 2 | CZ | Motor central |
| 3 | C4 | Motor derecho |
| 4 | PZ | Parietal |
| 5 | PO7 | Occipital izquierdo |
| 6 | OZ | Occipital central |
| 7 | PO8 | Occipital derecho |

## Bandas de frecuencia

| Banda | Rango | Índice en features | Asociado a |
|-------|-------|--------------------|------------|
| Delta | 0.5–4 Hz | `ch*4 + 0` | Sueño, drift |
| Theta | 4–8 Hz | `ch*4 + 1` | Somnolencia |
| **Alpha** | **8–12 Hz** | **`ch*4 + 2`** | **Relajación, ojos cerrados** |
| **Beta** | **13–30 Hz** | **`ch*4 + 3`** | **Concentración activa** |
