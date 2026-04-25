import numpy as np
from scipy.signal import butter, filtfilt, iirnotch


def notch(signal: np.ndarray, fs: float = 250.0, freq: float = 60.0, Q: float = 30.0) -> np.ndarray:
    b, a = iirnotch(freq, Q, fs)
    return filtfilt(b, a, signal)


def bandpass(signal: np.ndarray, fs: float = 250.0, lowcut: float = 0.5,
             highcut: float = 40.0, order: int = 4) -> np.ndarray:
    nyq = fs / 2
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return filtfilt(b, a, signal)


def apply_filters(eeg: np.ndarray, fs: float = 250.0, notch_freq: float = 60.0) -> np.ndarray:
    """eeg: (n_samples, n_channels) → filtered copy"""
    out = np.empty_like(eeg, dtype=np.float64)
    for ch in range(eeg.shape[1]):
        s = notch(eeg[:, ch].astype(np.float64), fs, notch_freq)
        out[:, ch] = bandpass(s, fs)
    return out
