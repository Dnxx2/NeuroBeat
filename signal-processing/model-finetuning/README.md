# Model Fine-Tuning Pipeline

Fine-tunes **EEGNetv4** (via braindecode) on subject-specific data from the Unicorn Black.

## ¿Necesito descargar el modelo manualmente?

**No.** Hay dos rutas y ninguna requiere descarga manual:

| Ruta | Cuándo usarla | Descarga automática |
|------|--------------|---------------------|
| **A) Desde cero** *(hackathon default)* | Tienes ≥ 2 min de datos del sujeto. EEGNet fue diseñado para datos limitados. | — nada — |
| **B) Desde pretrained (Hugging Face)** | Quieres mejor accuracy de arranque. Congela el backbone, solo reentrena el clasificador. | ~10 MB desde `PierreGtch/EEGNetv4` al primer uso; se cachea en `~/.cache/huggingface/` |

**Para el hackathon, la ruta A es suficiente.** 2 min de calibración + EEGNet desde cero supera fácilmente un clasificador de umbral porque el modelo aprende la varianza específica del sujeto.

---

## Workflow

```
1. calibrate.py  →  graba 2 min de EEG etiquetado  →  data/subject_01.npz
2. train.py      →  fine-tune EEGNet               →  models/subject_01.pt
3. predict.py    →  inferencia en tiempo real       →  'FOCUS' | 'RELAX'
```

## Install

```bash
pip install -r requirements.txt
# instala braindecode[hub] — incluye soporte Hugging Face
```

## Step 1 — Calibrar al sujeto

```bash
# Con hardware
python calibrate.py --output data/subject_01.npz

# Sin hardware (señal aleatoria — para probar el pipeline)
python calibrate.py --output data/subject_01.npz --mock
```

El script alterna bloques de 30 s: RELAX → FOCUS × 2 rondas ≈ 2 minutos.
Los archivos `.npz` están en `.gitignore`; guárdalos en `data/` local.

## Step 2 — Entrenar desde Hugging Face (descarga automática ~10 MB)

```bash
python train.py --data data/subject_01.npz --output models/subject_01.pt --hub
```

**El flag `--hub` activa fine-tuning en dos fases:**

| Fase | Epochs | Qué entrena | LR |
|------|--------|------------|-----|
| 1 | 10 | Solo clasificador (backbone congelado) | 1e-3 |
| 2 | 20 | Todas las capas | 1e-4 |

La fase 1 redirige rápido los features de Motor Imagery → FOCUS/RELAX.
La fase 2 ajusta los filtros espaciales al sujeto específico sin destruir lo aprendido.

## Step 3 — Inferencia

```python
from predict import EEGClassifier

clf = EEGClassifier('models/subject_01.pt')

# epoch: (500 samples, 8 channels) — ventana de 2 s @ 250 Hz
state = clf.predict(epoch)          # 'FOCUS' | 'RELAX'
probs = clf.predict_proba(epoch)    # [p_relax, p_focus]
```

## Module overview

| Archivo | Responsabilidad |
|---------|----------------|
| `calibrate.py` | Sesión guiada de grabación; exporta `.npz` |
| `dataset.py` | `torch.Dataset` + data augmentation (ruido gaussiano + time shift) |
| `model.py` | EEGNetv4, `build_model()` (local/scratch), `from_pretrained_hub()` (HF auto-download) |
| `train.py` | Loop de entrenamiento con checkpoint por mejor val_acc |
| `predict.py` | `EEGClassifier.predict()` / `predict_proba()` |

## Pretrained model info

El checkpoint `PierreGtch/EEGNetv4 / EEGNetv4_Lee2019_MI.ckpt` fue entrenado en Motor Imagery (izquierda vs derecha) — no en FOCUS/RELAX. El fine-tuning lo redirige a tu tarea, pero si tus clases son de imaginería motora la transferencia será más directa.

## Extender a más clases

1. Agregar entradas a `CLASSES` en `calibrate.py`
2. Actualizar `LABEL_MAP` en `predict.py`
3. Re-grabar datos y re-entrenar
