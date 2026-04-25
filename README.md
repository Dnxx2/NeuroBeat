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

## Quick Start

See the `README.md` inside each sub-folder for setup and run instructions specific to that component.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
