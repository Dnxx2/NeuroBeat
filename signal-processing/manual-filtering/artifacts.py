import numpy as np

# Channel names matching Unicorn Black layout
_CH_NAMES = ['FZ', 'C3', 'CZ', 'C4', 'PZ', 'PO7', 'OZ', 'PO8']


def remove_artifacts_mne(eeg: np.ndarray, fs: float = 250.0) -> np.ndarray:
    """
    Offline ICA via MNE with automatic blink detection using FZ as EOG proxy.
    eeg: (n_samples, 8) — needs at least ~10 s of data to be stable.
    """
    import mne
    mne.set_log_level('WARNING')

    info = mne.create_info(_CH_NAMES, sfreq=fs, ch_types='eeg')
    raw = mne.io.RawArray(eeg.T * 1e6, info)   # MNE works in µV internally
    raw.set_montage('standard_1020')

    ica = mne.preprocessing.ICA(n_components=8, random_state=42)
    ica.fit(raw)

    # FZ is the closest electrode to the eyes in the Unicorn layout
    eog_idx, _ = ica.find_bads_eog(raw, ch_name='FZ', threshold=3.0)
    ica.exclude = eog_idx

    raw_clean = ica.apply(raw.copy())
    return (raw_clean.get_data().T) * 1e-6   # back to volts


def reject_epochs(epochs: np.ndarray, threshold_uv: float = 100e-6) -> np.ndarray:
    """
    epochs: (n_epochs, n_samples, n_channels)
    Returns boolean mask — True for clean epochs.
    """
    peak_to_peak = epochs.max(axis=1) - epochs.min(axis=1)
    return np.all(peak_to_peak < threshold_uv, axis=1)
