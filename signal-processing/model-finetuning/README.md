# Model Fine-Tuning Pipeline

Fine-tunes **EEGNet** (via braindecode) on subject-specific data from the Unicorn Black.
EEGNet is a compact CNN purpose-built for BCI with limited training data — 20–30 min bastan.

## Workflow

```
1. calibrate.py  →  graba 2 min de EEG etiquetado  →  data/subject_01.npz
2. train.py      →  fine-tune EEGNet               →  models/subject_01.pt
3. predict.py    →  inferencia en tiempo real       →  'FOCUS' | 'RELAX'
```

## Install

```bash
pip install -r requirements.txt
```

## Step 1 — Calibrar al sujeto

```bash
# Con hardware
python calibrate.py --output data/subject_01.npz

# Sin hardware (señal aleatoria — para probar el pipeline)
python calibrate.py --output data/subject_01.npz --mock
```

El script alterna bloques: 30 s RELAX → 30 s FOCUS × 2 rondas ≈ 2 minutos.
Los archivos `.npz` están gitignoreados; guárdalos en la carpeta `data/` local.

## Step 2 — Entrenar

```bash
# Desde cero
python train.py --data data/subject_01.npz --output models/subject_01.pt

# Desde weights preentrenados (recomendado — converge en ~30 epochs)
python train.py --data data/subject_01.npz \
                --pretrained models/pretrained_base.pt \
                --output models/subject_01.pt \
                --epochs 30
```

## Step 3 — Inferencia

```python
from predict import EEGClassifier
import numpy as np

clf = EEGClassifier('models/subject_01.pt')

# epoch: (500 samples, 8 channels) — ventana de 2 s @ 250 Hz
state = clf.predict(epoch)          # 'FOCUS' | 'RELAX'
probs = clf.predict_proba(epoch)    # [p_relax, p_focus]
```

## Module overview

| Archivo | Responsabilidad |
|---------|----------------|
| `calibrate.py` | Sesión guiada de grabación; exporta `.npz` |
| `dataset.py` | `torch.Dataset` + data augmentation |
| `model.py` | EEGNetv4 (braindecode), carga de weights, freeze de backbone |
| `train.py` | Loop de entrenamiento con early-stopping por val_acc |
| `predict.py` | `EEGClassifier` — predict / predict_proba |

## Estrategia de fine-tuning

- **Sin pretrained:** todas las capas se entrenan. Funciona pero necesita más epochs y más datos.
- **Con pretrained:** `freeze_backbone()` congela depthwise/separable conv y solo entrena la capa clasificadora. Converge mucho más rápido con pocos datos de sujeto.

Para obtener un base model preentrenado puedes usar PhysioNet Motor Imagery (109 sujetos) con braindecode y guardar los weights en `models/pretrained_base.pt`.

## Extender a más clases

1. Agregar entradas a `CLASSES` en `calibrate.py`
2. Actualizar `LABEL_MAP` en `predict.py`
3. Re-grabar datos y re-entrenar
