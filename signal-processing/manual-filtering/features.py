import numpy as np
from scipy.signal import welch

# Unicorn Black channel layout (index → label → region)
CHANNELS = ['FZ', 'C3', 'CZ', 'C4', 'PZ', 'PO7', 'OZ', 'PO8']
FRONTAL_IDX = [0, 1, 2, 3]   # FZ, C3, CZ, C4

BANDS = {
    'delta': (0.5, 4.0),
    'theta': (4.0, 8.0),
    'alpha': (8.0, 12.0),
    'beta':  (13.0, 30.0),
}
BAND_NAMES = list(BANDS.keys())


def bandpower(signal: np.ndarray, fs: float, band: tuple) -> float:
    f, psd = welch(signal, fs, nperseg=int(fs))
    mask = (f >= band[0]) & (f <= band[1])
    return float(np.trapz(psd[mask], f[mask]))


def extract_features(eeg: np.ndarray, fs: float = 250.0) -> np.ndarray:
    """
    eeg: (n_samples, n_channels)
    Returns flat feature vector: [ch0_delta, ch0_theta, ch0_alpha, ch0_beta, ch1_delta, ...]
    Shape: (n_channels * n_bands,)
    """
    feats = []
    for ch in range(eeg.shape[1]):
        for band in BANDS.values():
            feats.append(bandpower(eeg[:, ch], fs, band))
    return np.array(feats, dtype=np.float32)


def classify_state(features: np.ndarray) -> str:
    """Threshold classifier based on frontal alpha/beta ratio."""
    n_bands = len(BANDS)
    alpha_i = BAND_NAMES.index('alpha')
    beta_i  = BAND_NAMES.index('beta')

    alpha = np.mean([features[ch * n_bands + alpha_i] for ch in FRONTAL_IDX])
    beta  = np.mean([features[ch * n_bands + beta_i]  for ch in FRONTAL_IDX])

    ratio = alpha / (beta + 1e-9)
    if ratio > 2.0:
        return 'RELAX'
    if ratio < 0.5:
        return 'FOCUS'
    return 'NEUTRAL'
