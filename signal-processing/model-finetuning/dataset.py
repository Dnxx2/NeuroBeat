import numpy as np
from torch.utils.data import Dataset


class EEGDataset(Dataset):
    def __init__(self, epochs: np.ndarray, labels: np.ndarray, augment: bool = False):
        """
        epochs: (n, n_samples, n_channels)
        labels: (n,) integer class indices

        braindecode / EEGNet expects (n, n_channels, n_samples).
        """
        # 1. Transponer a formato (Batch, Canales, Tiempo)
        self.X = np.transpose(epochs, (0, 2, 1)).astype(np.float32)

        # 2. ¡LA SOLUCIÓN! Multiplicamos por 10,000.
        # Esto lleva los diminutos Voltios del Unicorn a una escala donde
        # la red neuronal puede verlos ([-1, 1] en reposo, y grandes picos en parpadeos)
        self.X = self.X * 10000.0

        self.y = labels.astype(np.int64)
        self.augment = augment

    def __len__(self) -> int:
        return len(self.y)

    def __getitem__(self, idx):
        x = self.X[idx].copy()
        if self.augment:
            x = _augment(x)
        return x, self.y[idx]


def _augment(epoch: np.ndarray) -> np.ndarray:
    """Light augmentation to expand small subject datasets."""
    # Como escalamos por 10,000, el ruido antiguo (0.5e-6) ya no hace nada.
    # Un ruido de 0.05 en esta nueva escala es equivalente e ideal.
    epoch += np.random.normal(0, 0.05, epoch.shape).astype(np.float32)
    shift = np.random.randint(-25, 26)  # ±100 ms at 250 Hz
    return np.roll(epoch, shift, axis=-1)