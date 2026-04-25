# Model Fine-Tuning Pipeline

Fine-tuning de **EEGNetv4** sobre datos del sujeto de prueba para clasificar estados mentales (FOCUS / RELAX) con el Unicorn Black.

---

## Cómo funciona

### El modelo base — EEGNetv4

EEGNetv4 es una red neuronal convolucional compacta diseñada específicamente para BCI con pocos datos. Su arquitectura tiene dos bloques principales:

1. **Depthwise convolution temporal** — aprende filtros de frecuencia específicos del EEG (equivalente al bandpass manual, pero aprendido de los datos)
2. **Separable convolution espacial** — aprende cómo combinar los 8 canales para maximizar la separabilidad entre clases (equivalente a seleccionar los electrodos más informativos)

El modelo descargado fue preentrenado en **Motor Imagery** (imaginería de movimiento de mano izquierda vs derecha, dataset Lee 2019). No clasifica FOCUS/RELAX directamente, pero sus capas inferiores ya saben cómo extraer features temporales y espaciales de señal EEG real. Eso es lo que se transfiere.

### Por qué fine-tuning en dos fases

La tarea cambia (Motor Imagery → FOCUS/RELAX) pero la estructura de la señal es la misma (EEG de 8 canales a 250 Hz). El problema es que si se descongelan todas las capas desde el inicio con pocos datos, el modelo sobreajusta antes de redirigir los features.

**Fase 1 — backbone congelado (10 epochs, LR=1e-3)**

Solo el clasificador final entrena. El backbone ya extrae features de EEG; el objetivo aquí es aprender a qué espacio de features pertenece cada clase (RELAX vs FOCUS) sin tocar los filtros aprendidos. Converge rápido porque es un problema lineal sobre features ya estables.

**Fase 2 — todas las capas (20 epochs, LR=1e-4)**

Con el clasificador ya orientado hacia la tarea correcta, se descongelan todas las capas y se entrena con un learning rate 10 veces más bajo. Esto permite que los filtros espaciales y temporales se ajusten al sujeto específico sin destruir lo aprendido en el preentrenamiento. El LR bajo es clave: cambios grandes en esta fase arruinarían los pesos preentrenados.

### Data augmentation

Con ~2 minutos de datos el dataset es pequeño. Cada epoch pasa por dos transformaciones aleatorias durante el entrenamiento:
- **Ruido gaussiano leve** (σ = 0.5 µV) — simula variabilidad natural de la señal
- **Shift temporal aleatorio** (±100 ms) — el modelo aprende a ser invariante a pequeñas variaciones de timing

Esto multiplica la variabilidad efectiva del dataset sin necesidad de grabar más datos.

---

## ¿Necesito descargar algo manualmente?

**No.** La primera vez que corres `train.py`, braindecode descarga automáticamente ~10 MB desde Hugging Face (`PierreGtch/EEGNetv4`) y los cachea en `~/.cache/huggingface/`. Las siguientes ejecuciones usan el caché.

---

## Flujo completo de uso

```
[1] Instalar
[2] Grabar calibración con el Unicorn (calibrate.py)
[3] Entrenar el modelo (train.py)  ← descarga HF automático aquí
[4] Inferencia en tiempo real (predict.py)
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

El script `calibrate.py` guía al sujeto a través de bloques alternados de RELAX y FOCUS, graba la señal del Unicorn y guarda los epochs etiquetados.

```bash
# Con el Unicorn Black conectado
python calibrate.py --output data/subject_01.npz

# Sin hardware (señal aleatoria — para probar que el pipeline funciona)
python calibrate.py --output data/subject_01.npz --mock
```

El script hace esto:
1. Muestra instrucciones en pantalla ("cierra los ojos", "concéntrate")
2. Graba 30 s por bloque × 2 clases × 2 rondas = **2 minutos totales**
3. Divide cada grabación en ventanas de 2 s con 50% de solapamiento
4. Guarda el archivo `.npz` con dos arrays: `epochs` shape `(n, 500, 8)` y `labels` shape `(n,)`

Los `.npz` están en `.gitignore`. Guárdalos localmente en la carpeta `data/`.

Para verificar que se grabó bien:
```python
import numpy as np
d = np.load('data/subject_01.npz')
print(d['epochs'].shape)   # ej. (240, 500, 8)
print(d['labels'])          # [0, 0, ..., 1, 1, ...]  (0=RELAX, 1=FOCUS)
```

---

## Paso 3 — Entrenar

```bash
python train.py --data data/subject_01.npz --output models/subject_01.pt
```

Lo que sucede al correr esto:
1. Descarga EEGNetv4 preentrenado de Hugging Face (~10 MB, primera vez)
2. Aplica data augmentation al dataset
3. **Fase 1** (10 epochs): congela el backbone, entrena solo el clasificador
4. **Fase 2** (20 epochs): descongela todo, LR = 1e-4, ajusta el modelo al sujeto
5. Guarda un checkpoint cada vez que la `val_acc` mejora
6. El mejor modelo queda guardado en `models/subject_01.pt`

Salida esperada:
```
Descargando weights desde Hugging Face...
── Fase 1/30: backbone congelado ──
Epoch   1/30  val_acc=0.541
Epoch   2/30  val_acc=0.612
  -> checkpoint guardado  (mejor=0.612)
...
── Fase 2/30: todas las capas, LR=1.0e-04 ──
Epoch  11/30  val_acc=0.708
  -> checkpoint guardado  (mejor=0.708)
...
Listo. Mejor val_acc: 0.821  →  models/subject_01.pt
```

Parámetros opcionales:
```bash
python train.py \
  --data data/subject_01.npz \
  --output models/subject_01.pt \
  --phase1-epochs 10 \   # default 10
  --phase2-epochs 20 \   # default 20
  --lr 1e-3 \            # default 1e-3
  --batch-size 16        # default 16
```

---

## Paso 4 — Inferencia en tiempo real

```python
from predict import EEGClassifier
import numpy as np

clf = EEGClassifier('models/subject_01.pt')

# En tu loop de adquisición del Unicorn:
buffer = []
while True:
    sample = unicorn.get_sample()   # (8,)
    buffer.append(sample)

    if len(buffer) == 500:          # ventana de 2 s completa
        epoch = np.array(buffer)    # (500, 8)
        state = clf.predict(epoch)  # 'FOCUS' o 'RELAX'
        send_to_game(state)
        buffer = buffer[62:]        # avanzar 0.25 s (ventana deslizante)
```

Para obtener probabilidades en vez de solo la clase:
```python
probs = clf.predict_proba(epoch)
# probs[0] = P(RELAX),  probs[1] = P(FOCUS)
print(f"RELAX={probs[0]:.2f}  FOCUS={probs[1]:.2f}")
```

---

## Referencia de módulos

### `calibrate.py`
Sesión guiada de grabación. Lee el Unicorn muestra por muestra, alterna bloques RELAX/FOCUS con instrucciones en pantalla, exporta `.npz` listo para `train.py`. `--mock` simula el hardware con ruido gaussiano.

### `dataset.py`
`EEGDataset(epochs, labels, augment=True)` — convierte el `.npz` en un `Dataset` de PyTorch. Transpone los ejes para que EEGNet reciba `(batch, canales, muestras)`. Con `augment=True` aplica ruido gaussiano y shift temporal en cada batch.

### `model.py`
- `from_pretrained_hub(n_classes)` — descarga EEGNetv4 de Hugging Face y lo retorna listo para fine-tuning
- `freeze_backbone(model)` — congela todas las capas excepto el clasificador final
- `build_model(n_classes, pretrained_path)` — crea el modelo desde cero o carga un `.pt` local (uso interno)

### `train.py`
Orquesta el fine-tuning en dos fases. Lee el `.npz`, crea los DataLoaders, descarga el modelo base, corre las dos fases y guarda el mejor checkpoint por `val_acc`.

### `predict.py`
`EEGClassifier(model_path)` — carga el `.pt` y expone `predict(epoch)` y `predict_proba(epoch)`. Maneja internamente la transposición de ejes y la conversión a tensor.

---

## Modelo preentrenado

`PierreGtch/EEGNetv4` · `EEGNetv4_Lee2019_MI.ckpt`

Entrenado en Motor Imagery (imaginería de mano izquierda vs derecha, 2 clases). La tarea es diferente a FOCUS/RELAX, pero las capas de filtrado temporal y espacial generalizan bien entre paradigmas de EEG. El fine-tuning redirige la salida a la tarea correcta.

## Extender a más clases

1. Agregar entradas a `CLASSES` en `calibrate.py`
2. Actualizar `LABEL_MAP` en `predict.py`
3. Re-grabar la calibración y re-entrenar
