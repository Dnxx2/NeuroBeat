# Manual Filtering Pipeline

Pipeline clásico de DSP para limpiar, extraer features y clasificar EEG de 8 canales del Unicorn Black en tiempo real.

---

## Cómo funciona — de la señal cruda al estado mental

### El problema

El Unicorn Black usa electrodos secos, lo que significa más ruido que un sistema de laboratorio cableado. La señal cruda contiene:

- **Ruido de línea eléctrica** — pico de 60 Hz (o 50 Hz en Europa) de la red eléctrica del cuarto
- **Ruido de baja frecuencia** — drift de electrodos, movimiento lento del cuerpo
- **Artefactos de parpadeo** — cada parpadeo genera un pulso de ~100–200 µV en los electrodos frontales que enmascara la señal cerebral
- **Ruido compartido entre canales** — variaciones de impedancia comunes a todos los electrodos

El pipeline aplica un filtro por etapa, en orden, para eliminar cada tipo de ruido antes de extraer información útil.

### Etapa 1 — Common Average Reference (CAR)

```
señal_ch[n] = señal_ch[n] - promedio(todos_los_canales)[n]
```

En cada instante de tiempo, se resta el promedio de los 8 canales a cada canal individualmente. Esto elimina cualquier ruido que sea idéntico en todos los electrodos al mismo tiempo (variaciones del amplificador, interferencia electromagnética ambiental). Es el paso más barato y uno de los más efectivos para EEG de electrodos secos.

### Etapa 2 — Filtro Notch (60 Hz)

Elimina el pico exacto de 60 Hz que introduce la red eléctrica. Se usa un filtro IIR notch con factor de calidad Q=30, lo que significa que solo elimina una banda estrecha de ±2 Hz alrededor de 60 Hz sin distorsionar el resto de la señal.

### Etapa 3 — Filtro Bandpass (0.5–40 Hz)

Las bandas cerebrales de interés están todas por debajo de 40 Hz. Todo lo que está fuera de ese rango es ruido o artefacto:
- Por debajo de 0.5 Hz: drift lento del electrodo, sudor
- Por encima de 40 Hz: ruido muscular (EMG), artefactos de alta frecuencia

Se usa un filtro Butterworth de orden 4 aplicado con `filtfilt` (fase cero) para no desplazar los eventos temporalmente.

### Etapa 4 — ICA con detección de parpadeos (solo offline)

ICA (Independent Component Analysis) descompone los 8 canales en 8 fuentes independientes. Algunas de esas fuentes son parpadeos, movimientos musculares o ruido de electrodo. Para identificarlas automáticamente:

- MNE entrena la ICA sobre la grabación completa
- `find_bads_eog()` correlaciona cada componente con el canal **FZ**, que es el electrodo más cercano a los ojos en el layout del Unicorn (frontal central). Los parpadeos generan un patrón muy característico en FZ.
- Los componentes identificados se ponen a cero y la señal se reconstruye sin ellos

**Por qué se omite en tiempo real:** ICA necesita ajustarse sobre un bloque largo de datos (>10 s). En streaming muestra por muestra no es viable sin introducir latencia de segundos. El tiempo real usa solo CAR + notch + bandpass, que son instantáneos.

### Etapa 5 — Rechazo de epochs (offline)

Cualquier ventana de 2 segundos donde algún canal tenga una amplitud pico-a-pico mayor a 100 µV se descarta antes de extraer features. Esto elimina epochs con artefactos severos que ICA no pudo limpiar completamente (p.ej. el sujeto se movió bruscamente).

### Etapa 6 — Extracción de features (bandpower)

Por cada canal se calcula la potencia en 4 bandas de frecuencia usando la densidad espectral de potencia (Welch PSD):

| Banda | Rango | Asociado a |
|-------|-------|-----------|
| Delta | 0.5–4 Hz | Sueño profundo, drift |
| Theta | 4–8 Hz | Somnolencia, meditación |
| **Alpha** | **8–12 Hz** | **Relajación, ojos cerrados** |
| **Beta** | **13–30 Hz** | **Concentración activa, alerta** |

El resultado es un vector de **32 features** (8 canales × 4 bandas).

### Etapa 7 — Clasificador Adaptativo (nearest centroid)

En vez de usar umbrales fijos (ratio α/β > 2.0 = RELAX), el `AdaptiveClassifier` aprende los centroides del sujeto específico:

1. Durante la calibración, procesa grabaciones etiquetadas (RELAX y FOCUS) y calcula el vector promedio de features para cada clase.
2. Normaliza todos los features con z-score (media 0, varianza 1) para que ninguna banda domine por escala.
3. En tiempo real, clasifica cada ventana por distancia euclidiana al centroide más cercano.

Esto es crítico porque los rangos absolutos de α/β varían enormemente entre personas. Lo que es "mucho alpha" para una persona puede ser normal para otra.

---

## Flujo completo de uso

```
[1] Instalar
[2] Grabar calibración (offline, con Unicorn)
[3] Calibrar el clasificador
[4] Guardar calibración
[5] Cargar calibración en tiempo real
[6] Streaming al juego
```

---

## Paso 1 — Instalar

```bash
cd signal-processing/manual-filtering
pip install -r requirements.txt
```

---

## Paso 2 — Grabar una sesión de calibración

Necesitas ~5 minutos de EEG etiquetado: unos minutos con el sujeto relajado (ojos cerrados, respiración tranquila) y unos minutos concentrado (contando mentalmente, leyendo, resolviendo algo).

```python
import numpy as np

# Sustituye esto con tu loop de adquisición real del Unicorn
# Cada llamada devuelve un array (8,) con los 8 canales en voltios
relax_samples = []
focus_samples = []

# Graba 2 min RELAX
print("Cierra los ojos y respira lento — 2 minutos")
for _ in range(250 * 120):   # 250 Hz × 120 s
    relax_samples.append(unicorn.get_sample())

# Graba 2 min FOCUS
print("Concéntrate, cuenta de 3 en 3 — 2 minutos")
for _ in range(250 * 120):
    focus_samples.append(unicorn.get_sample())

relax_recording = np.array(relax_samples)   # (30000, 8)
focus_recording = np.array(focus_samples)   # (30000, 8)
```

---

## Paso 3 — Calibrar el clasificador

```python
from pipeline import EEGPipeline

pipeline = EEGPipeline(fs=250, use_ica=True)

pipeline.calibrate({
    'RELAX': relax_recording,
    'FOCUS': focus_recording,
})
```

Internamente esto hace:
1. Procesa cada grabación con el pipeline completo (CAR + notch + bandpass + ICA)
2. Divide cada grabación en epochs de 2 s con 50% de solapamiento
3. Descarta epochs ruidosos (peak-to-peak > 100 µV)
4. Extrae el vector de 32 features de cada epoch limpio
5. Calcula el centroide (promedio z-normalizado) para RELAX y para FOCUS

---

## Paso 4 — Guardar la calibración

```python
pipeline.save_calibration('calibration.npz')
```

Guarda los centroides y parámetros de normalización en un archivo `.npz`. Solo pesa unos KB. Cárgala en cualquier sesión futura sin tener que recalibrar.

---

## Paso 5 — Tiempo real (streaming al juego)

```python
from pipeline import EEGPipeline
from realtime import RealtimeProcessor

# Cargar pipeline con la calibración del sujeto
pipeline = EEGPipeline(fs=250, use_ica=False)   # ICA off en real-time
pipeline.load_calibration('calibration.npz')

proc = RealtimeProcessor(pipeline=pipeline, window_sec=2.0, step_sec=0.25)

# Loop de adquisición
while True:
    sample = unicorn.get_sample()    # ndarray (8,)
    state = proc.push(sample)
    if state:
        # state es 'FOCUS', 'RELAX', o 'NEUTRAL'
        # Enviar al juego — UDP, socket, variable compartida, lo que uses
        send_to_game(state)
```

`RealtimeProcessor` mantiene un buffer circular de 2 segundos (500 muestras). Cada 0.25 s (62 muestras nuevas) saca el buffer completo, corre el pipeline, y devuelve el estado. La latencia efectiva es ≤ 250 ms.

---

## Referencia de módulos

### `filters.py`
- `common_average_reference(eeg)` — resta el promedio entre canales en cada muestra
- `notch(signal, fs, freq, Q)` — filtro notch IIR
- `bandpass(signal, fs, lowcut, highcut, order)` — Butterworth bandpass fase cero
- `apply_filters(eeg, fs, notch_freq)` — aplica CAR → notch → bandpass a todos los canales

### `artifacts.py`
- `remove_artifacts_mne(eeg, fs)` — ICA con MNE y detección automática de parpadeos via FZ. Solo para offline (necesita >10 s de señal).
- `reject_epochs(epochs, threshold_uv)` — máscara booleana de epochs limpios

### `features.py`
- `extract_features(eeg, fs)` — Welch PSD → potencia en δ θ α β por canal → vector (32,)
- `AdaptiveClassifier` — nearest centroid calibrado al sujeto con z-score normalización. Métodos: `calibrate()`, `predict()`, `save()`, `load()`

### `pipeline.py`
- `EEGPipeline` — orquesta todo. Métodos: `process()`, `process_epochs()`, `calibrate()`, `classify()`, `save_calibration()`, `load_calibration()`

### `realtime.py`
- `RealtimeProcessor` — buffer circular + ventana deslizante. Método: `push(sample)` → devuelve estado cada `step_sec`

---

## Layout del Unicorn Black

| Índice | Canal | Región |
|--------|-------|--------|
| 0 | FZ | Frontal central — más cercano a los ojos, usado como proxy EOG |
| 1 | C3 | Motor izquierdo |
| 2 | CZ | Motor central |
| 3 | C4 | Motor derecho |
| 4 | PZ | Parietal |
| 5 | PO7 | Occipital izquierdo |
| 6 | OZ | Occipital central |
| 7 | PO8 | Occipital derecho |
