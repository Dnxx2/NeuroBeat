import numpy as np
from torch.utils.data import Dataset


class EEGDataset(Dataset):
    def __init__(self, epochs: np.ndarray, labels: np.ndarray, augment: bool = False):
        """
        epochs: (n, n_samples, n_channels)
        labels: (n,) integer class indices

        braindecode / EEGNet expects (n, n_channels, n_samples).
        """
        self.X = np.transpose(epochs, (0, 2, 1)).astype(np.float32)
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
    epoch += np.random.normal(0, 0.5e-6, epoch.shape).astype(np.float32)
    shift = np.random.randint(-25, 26)   # ±100 ms at 250 Hz
    return np.roll(epoch, shift, axis=-1)
