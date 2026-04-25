import numpy as np
from sklearn.decomposition import FastICA


def remove_artifacts_ica(eeg: np.ndarray, n_components: int = 8,
                          variance_thresh_factor: float = 3.0) -> np.ndarray:
    """
    eeg: (n_samples, n_channels)

    Removes ICA components whose variance exceeds median * thresh_factor.
    Requires n_samples >> n_components; skip for short windows (use realtime path instead).
    """
    ica = FastICA(n_components=n_components, random_state=42, max_iter=1000, tol=1e-4)
    sources = ica.fit_transform(eeg)            # (n_samples, n_components)

    variances = np.var(sources, axis=0)
    threshold = np.median(variances) * variance_thresh_factor
    sources[:, variances > threshold] = 0.0

    return sources @ ica.mixing_.T + ica.mean_  # reconstruct


def reject_epochs(epochs: np.ndarray, threshold_uv: float = 100e-6) -> np.ndarray:
    """
    epochs: (n_epochs, n_samples, n_channels)
    Returns boolean mask — True for clean epochs.
    """
    peak_to_peak = epochs.max(axis=1) - epochs.min(axis=1)  # (n_epochs, n_channels)
    return np.all(peak_to_peak < threshold_uv, axis=1)
