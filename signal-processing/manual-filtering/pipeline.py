import numpy as np
from filters import apply_filters
from artifacts import remove_artifacts_mne, reject_epochs
from features import extract_features, AdaptiveClassifier


class EEGPipeline:
    def __init__(self, fs: float = 250.0, n_channels: int = 8,
                 notch_freq: float = 60.0, use_ica: bool = True,
                 epoch_reject_uv: float = 100e-6):
        self.fs = fs
        self.n_channels = n_channels
        self.notch_freq = notch_freq
        self.use_ica = use_ica
        self.epoch_reject_uv = epoch_reject_uv
        self.classifier = AdaptiveClassifier()

    def process(self, raw: np.ndarray) -> np.ndarray:
        """raw: (n_samples, n_channels) → CAR + filtered signal"""
        out = apply_filters(raw, self.fs, self.notch_freq)
        if self.use_ica and raw.shape[0] > self.fs * 10:
            out = remove_artifacts_mne(out, self.fs)
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

    def calibrate(self, labeled_epochs: dict[str, np.ndarray]) -> None:
        """
        Calibrate the adaptive classifier from labelled recording segments.
        labeled_epochs: {'RELAX': (n_samples, 8), 'FOCUS': (n_samples, 8)}
        Each value is a continuous recording that gets processed and epoched internally.
        """
        labeled_features = {}
        for label, recording in labeled_epochs.items():
            clean = self.process(recording)
            epoch_len = int(self.fs * 2)
            epochs = np.array([clean[i:i + epoch_len]
                                for i in range(0, len(clean) - epoch_len, epoch_len // 2)])
            good = reject_epochs(epochs, self.epoch_reject_uv)
            feats = np.array([extract_features(ep, self.fs) for ep in epochs[good]])
            labeled_features[label] = feats
        self.classifier.calibrate(labeled_features)

    def classify(self, raw: np.ndarray) -> str:
        """Classify a single window. raw: (n_samples, n_channels)"""
        clean = self.process(raw)
        feats = extract_features(clean, self.fs)
        return self.classifier.predict(feats)

    def save_calibration(self, path: str) -> None:
        self.classifier.save(path)

    def load_calibration(self, path: str) -> None:
        self.classifier.load(path)
