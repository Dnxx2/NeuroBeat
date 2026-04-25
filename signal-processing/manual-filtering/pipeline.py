import numpy as np
from filters import apply_filters
from artifacts import remove_artifacts_ica, reject_epochs
from features import extract_features, classify_state


class EEGPipeline:
    def __init__(self, fs: float = 250.0, n_channels: int = 8,
                 notch_freq: float = 60.0, use_ica: bool = True,
                 epoch_reject_uv: float = 100e-6):
        self.fs = fs
        self.n_channels = n_channels
        self.notch_freq = notch_freq
        self.use_ica = use_ica
        self.epoch_reject_uv = epoch_reject_uv

    def process(self, raw: np.ndarray) -> np.ndarray:
        """raw: (n_samples, n_channels) → cleaned signal"""
        out = apply_filters(raw, self.fs, self.notch_freq)
        # ICA needs enough samples to be numerically stable
        if self.use_ica and raw.shape[0] > self.n_channels * 20:
            out = remove_artifacts_ica(out, self.n_channels)
        return out

    def process_epochs(self, epochs: np.ndarray):
        """
        epochs: (n_epochs, n_samples, n_channels)
        Returns: (clean_epochs, features) — only epochs that passed rejection.
        """
        cleaned = np.array([self.process(ep) for ep in epochs])
        good = reject_epochs(cleaned, self.epoch_reject_uv)
        features = np.array([extract_features(ep, self.fs) for ep in cleaned[good]])
        return cleaned[good], features

    def classify(self, raw: np.ndarray) -> str:
        """Classify a single window. raw: (n_samples, n_channels)"""
        clean = self.process(raw)
        feats = extract_features(clean, self.fs)
        return classify_state(feats)
