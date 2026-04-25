"""
Sliding-window real-time processor.
ICA omitido (latencia); aplica CAR + notch + bandpass + z-score por canal.

push()             → ndarray (500, 8) limpio y normalizado, o None
stream_to_unity()  → loop completo que envía features por UDP (uso standalone)

Para correr ambos pipelines simultáneamente usa ../stream.py
"""
import json
import socket
import numpy as np
from collections import deque
from pipeline import EEGPipeline


class RunningNormalizer:
    """
    Z-score por canal usando la media y varianza acumuladas (Welford online).
    No necesita calibración separada — aprende en los primeros `warmup_sec` de grabación.
    """
    def __init__(self, n_channels: int = 8, warmup_sec: float = 5.0, fs: float = 250.0):
        self._n      = 0
        self._mean   = np.zeros(n_channels, dtype=np.float64)
        self._M2     = np.zeros(n_channels, dtype=np.float64)
        self._warmup = int(warmup_sec * fs)

    def update(self, sample: np.ndarray) -> None:
        self._n += 1
        delta       = sample - self._mean
        self._mean += delta / self._n
        self._M2   += delta * (sample - self._mean)

    @property
    def ready(self) -> bool:
        return self._n >= self._warmup

    def normalize(self, signal: np.ndarray) -> np.ndarray:
        """signal: (n_samples, n_channels) → z-score normalizado por canal."""
        std = np.sqrt(self._M2 / max(self._n - 1, 1)) + 1e-9
        return (signal - self._mean) / std


class RealtimeProcessor:
    def __init__(self, pipeline: EEGPipeline | None = None,
                 window_sec: float = 2.0, step_sec: float = 0.25,
                 fs: float = 250.0, n_channels: int = 8):
        self.fs         = fs
        self.n_channels = n_channels
        self.window_len = int(window_sec * fs)
        self.step_len   = int(step_sec * fs)
        self.buffer     = deque(maxlen=self.window_len)
        self.pipeline   = pipeline or EEGPipeline(fs=fs, n_channels=n_channels, use_ica=False)
        self.normalizer = RunningNormalizer(n_channels=n_channels, fs=fs)
        self._tick      = 0

    def push(self, sample: np.ndarray) -> np.ndarray | None:
        """
        Recibe una muestra cruda (n_channels,).
        Devuelve ndarray (window_len, n_channels) limpio y z-score normalizado
        cada step_sec una vez que el warmup termina (~5 s), o None.
        Pipeline: CAR → notch 60 Hz → bandpass 0.5–40 Hz → z-score online
        """
        self.normalizer.update(sample)
        self.buffer.append(sample)
        self._tick += 1
        if (len(self.buffer) == self.window_len
                and self._tick % self.step_len == 0
                and self.normalizer.ready):
            raw_window = np.array(self.buffer)
            clean      = self.pipeline.process(raw_window)
            return self.normalizer.normalize(clean)
        return None

    def stream_to_unity(self, get_sample_fn,
                        host: str = '127.0.0.1', port: int = 5006) -> None:
        """
        Loop standalone — envía features de bandpower por UDP cada ~250 ms.
        Puerto 5006 por defecto para no colisionar con el stream combinado (5005).

        Paquete UDP:
        {
          "alpha":      0.41,   (float 0-1, normalizado sobre α+β+θ)
          "beta":       0.62,   (float 0-1)
          "theta":      0.18,   (float 0-1)
          "engagement": 0.60    (beta / (alpha+beta), índice 0-1)
        }

        Detener con Ctrl+C.
        """
        from features import extract_features, BANDS, BAND_NAMES, FRONTAL_IDX

        n      = len(BANDS)
        a_i    = BAND_NAMES.index('alpha')
        b_i    = BAND_NAMES.index('beta')
        th_i   = BAND_NAMES.index('theta')
        sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        print(f"Manual pipeline → udp://{host}:{port}  (Ctrl+C para detener)")
        try:
            while True:
                window = self.push(get_sample_fn())
                if window is not None:
                    feats = extract_features(window)
                    alpha = float(np.mean([feats[ch*n + a_i]  for ch in FRONTAL_IDX]))
                    beta  = float(np.mean([feats[ch*n + b_i]  for ch in FRONTAL_IDX]))
                    theta = float(np.mean([feats[ch*n + th_i] for ch in FRONTAL_IDX]))
                    total = alpha + beta + theta + 1e-9
                    payload = {
                        'alpha':      round(alpha / total, 3),
                        'beta':       round(beta  / total, 3),
                        'theta':      round(theta / total, 3),
                        'engagement': round(beta / (alpha + beta + 1e-9), 3),
                    }
                    sock.sendto(json.dumps(payload).encode(), (host, port))
                    print(f"\rα={payload['alpha']:.2f} β={payload['beta']:.2f} "
                          f"eng={payload['engagement']:.2f}", end='', flush=True)
        except KeyboardInterrupt:
            print("\nDetenido.")
        finally:
            sock.close()
