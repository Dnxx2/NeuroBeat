import numpy as np
from scipy.signal import butter, filtfilt, iirnotch


def common_average_reference(eeg: np.ndarray) -> np.ndarray:
    """Subtract the mean across channels from every sample. (n_samples, n_channels)"""
    return eeg - eeg.mean(axis=1, keepdims=True)


def notch(signal: np.ndarray, fs: float = 250.0, freq: float = 60.0, Q: float = 30.0) -> np.ndarray:
    b, a = iirnotch(freq, Q, fs)
    return filtfilt(b, a, signal)


def bandpass(signal: np.ndarray, fs: float = 250.0, lowcut: float = 0.5,
             highcut: float = 40.0, order: int = 4) -> np.ndarray:
    nyq = fs / 2
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return filtfilt(b, a, signal)


def apply_filters(eeg: np.ndarray, fs: float = 250.0, notch_freq: float = 60.0) -> np.ndarray:
    """CAR → notch → bandpass.  eeg: (n_samples, n_channels)"""
    out = common_average_reference(eeg.astype(np.float64))
    result = np.empty_like(out)
    for ch in range(out.shape[1]):
        s = notch(out[:, ch], fs, notch_freq)
        result[:, ch] = bandpass(s, fs)
    return result
