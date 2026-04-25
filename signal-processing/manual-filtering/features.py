import numpy as np
from scipy.signal import welch

CHANNELS  = ['FZ', 'C3', 'CZ', 'C4', 'PZ', 'PO7', 'OZ', 'PO8']
FRONTAL_IDX = [0, 1, 2, 3]   # FZ, C3, CZ, C4

BANDS = {
    'delta': (0.5,  4.0),
    'theta': (4.0,  8.0),
    'alpha': (8.0, 12.0),
    'beta':  (13.0, 30.0),
}
BAND_NAMES = list(BANDS.keys())
N_FEATURES = len(CHANNELS) * len(BANDS)   # 32


def bandpower(signal: np.ndarray, fs: float, band: tuple) -> float:
    f, psd = welch(signal, fs, nperseg=int(fs))
    mask = (f >= band[0]) & (f <= band[1])
    return float(np.trapz(psd[mask], f[mask]))


def extract_features(eeg: np.ndarray, fs: float = 250.0) -> np.ndarray:
    """eeg: (n_samples, 8) → feature vector shape (32,): [ch0_δ, ch0_θ, ch0_α, ch0_β, ch1_δ, ...]"""
    feats = []
    for ch in range(eeg.shape[1]):
        for band in BANDS.values():
            feats.append(bandpower(eeg[:, ch], fs, band))
    return np.array(feats, dtype=np.float32)


class AdaptiveClassifier:
    """
    Nearest-centroid classifier calibrated to the subject.
    More robust than fixed thresholds because it learns the subject's
    actual alpha/beta distribution instead of assuming universal ratios.
    """

    def __init__(self):
        self._mean = None
        self._std  = None
        self._centroids: dict[str, np.ndarray] = {}

    def calibrate(self, labeled_features: dict[str, np.ndarray]) -> None:
        """
        labeled_features: {'RELAX': (n, 32), 'FOCUS': (n, 32), ...}
        Computes z-score params and per-class centroids.
        """
        all_feats = np.vstack(list(labeled_features.values()))
        self._mean = all_feats.mean(axis=0)
        self._std  = all_feats.std(axis=0) + 1e-9
        for label, feats in labeled_features.items():
            normed = (feats - self._mean) / self._std
            self._centroids[label] = normed.mean(axis=0)

    def predict(self, features: np.ndarray) -> str:
        """features: (32,) → class label string"""
        if not self._centroids:
            return _threshold_fallback(features)
        normed = (features - self._mean) / self._std
        distances = {label: np.linalg.norm(normed - c)
                     for label, c in self._centroids.items()}
        return min(distances, key=distances.get)

    def save(self, path: str) -> None:
        np.savez(path, mean=self._mean, std=self._std,
                 labels=list(self._centroids.keys()),
                 centroids=np.array(list(self._centroids.values())))

    def load(self, path: str) -> None:
        d = np.load(path, allow_pickle=True)
        self._mean = d['mean']
        self._std  = d['std']
        labels     = d['labels'].tolist()
        centroids  = d['centroids']
        self._centroids = dict(zip(labels, centroids))


def _threshold_fallback(features: np.ndarray) -> str:
    """Used before calibration — hardcoded frontal α/β ratio."""
    alpha_i = BAND_NAMES.index('alpha')
    beta_i  = BAND_NAMES.index('beta')
    n = len(BANDS)
    alpha = np.mean([features[ch * n + alpha_i] for ch in FRONTAL_IDX])
    beta  = np.mean([features[ch * n + beta_i]  for ch in FRONTAL_IDX])
    ratio = alpha / (beta + 1e-9)
    if ratio > 2.0:
        return 'RELAX'
    if ratio < 0.5:
        return 'FOCUS'
    return 'NEUTRAL'
