# NeuroBeat

A Brain.io hackathon project: a real-time game controlled entirely by brainwave signals captured via the **Unicorn Black** EEG headset.

## Overview

NeuroBeat translates raw EEG signals into game inputs, letting a player control a Unity game using only their brain activity. The pipeline covers signal acquisition, processing/filtering, and real-time game integration.

## Repository Structure

```
NeuroBeat/
├── game/                   # Unity game project
├── api/                    # Python API — Unicorn Black data acquisition & streaming
└── signal-processing/      # EEG signal cleaning and classification
    ├── manual-filtering/   # Bandpass, artifact rejection, and manual feature extraction
    └── model-finetuning/   # Fine-tuning a pre-trained model to the test subject's data
```

## Hardware

- **Unicorn Black** — 8-channel EEG headset by g.tec
- Sampling rate: 250 Hz
- Unicorn Python API / Unicorn .NET SDK

## Signal Processing — quick summary

| Sub-pipeline | Qué hace | Modelo |
|---|---|---|
| `manual-filtering/` | Notch → Bandpass → ICA → bandpower α/β | Sin ML — thresholds calibrados |
| `model-finetuning/` | EEGNetv4 fine-tuneado al sujeto de prueba | **No requiere descarga manual** — entrena desde cero con 2 min de calibración, o auto-descarga (~10 MB) desde Hugging Face (`PierreGtch/EEGNetv4`) |

## Quick Start

```bash
# signal-processing (ambas sub-carpetas)
pip install -r requirements.txt

# Calibrar sujeto y entrenar modelo (sin hardware: agrega --mock)
python signal-processing/model-finetuning/calibrate.py --output data/s1.npz
python signal-processing/model-finetuning/train.py --data data/s1.npz --output models/s1.pt
```

Ver el `README.md` dentro de cada sub-carpeta para instrucciones detalladas.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
