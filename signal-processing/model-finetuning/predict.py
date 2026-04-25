import json
import socket
from collections import deque

import numpy as np
import torch

from model import build_model, N_CLASSES

LABEL_MAP = {0: 'RELAX', 1: 'FOCUS'}


class EEGClassifier:
    def __init__(self, model_path: str, n_classes: int = N_CLASSES):
        self.model = build_model(n_classes=n_classes, pretrained_path=model_path)
        self.model.eval()

    def focus_score(self, epoch: np.ndarray) -> float:
        """
        Primary output for the game.
        epoch: (n_samples, n_channels) → float 0.0–1.0
        0.0 = completamente relajado, 1.0 = concentración máxima
        """
        return float(self._forward(epoch).softmax(dim=1)[0, 1])

    def predict(self, epoch: np.ndarray) -> str:
        """epoch: (n_samples, n_channels) → 'FOCUS' | 'RELAX'"""
        return LABEL_MAP.get(self._forward(epoch).argmax(dim=1).item(), 'UNKNOWN')

    def predict_proba(self, epoch: np.ndarray) -> np.ndarray:
        """Softmax probabilities, shape (n_classes,): [p_relax, p_focus]"""
        return self._forward(epoch).softmax(dim=1).detach().numpy()[0]

    def stream(self, get_sample_fn, host: str = '127.0.0.1', port: int = 5005,
               window: int = 500, step: int = 62) -> None:
        """
        Loop de adquisición en tiempo real. Envía {"focus": 0.73} por UDP cada ~250 ms.

        get_sample_fn : callable sin argumentos → ndarray (n_channels,)
        window        : muestras por ventana de clasificación (500 = 2 s @ 250 Hz)
        step          : muestras entre clasificaciones (62 ≈ 250 ms)
        Detener con Ctrl+C.
        """
        sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        buffer = deque(maxlen=window)
        tick   = 0

        print(f"Streaming focus score → udp://{host}:{port}  (Ctrl+C para detener)")
        try:
            while True:
                buffer.append(get_sample_fn())
                tick += 1
                if len(buffer) == window and tick % step == 0:
                    score   = self.focus_score(np.array(buffer))
                    payload = json.dumps({"focus": round(score, 3)}).encode()
                    sock.sendto(payload, (host, port))
                    print(f"\rfocus={score:.3f}  {'█' * int(score * 20):<20}", end='', flush=True)
        except KeyboardInterrupt:
            print("\nStreaming detenido.")
        finally:
            sock.close()

    def _forward(self, epoch: np.ndarray) -> torch.Tensor:
        x = torch.from_numpy(epoch.T.astype(np.float32)).unsqueeze(0)
        with torch.no_grad():
            return self.model(x)
