import numpy as np
import torch
from model import build_model, N_CLASSES

LABEL_MAP = {0: 'RELAX', 1: 'FOCUS'}


class EEGClassifier:
    def __init__(self, model_path: str, n_classes: int = N_CLASSES):
        self.model = build_model(n_classes=n_classes, pretrained_path=model_path)
        self.model.eval()

    def predict(self, epoch: np.ndarray) -> str:
        """epoch: (n_samples, n_channels) → label string"""
        logits = self._forward(epoch)
        return LABEL_MAP.get(logits.argmax(dim=1).item(), 'UNKNOWN')

    def predict_proba(self, epoch: np.ndarray) -> np.ndarray:
        """Returns softmax probabilities, shape (n_classes,)."""
        logits = self._forward(epoch)
        return torch.softmax(logits, dim=1).detach().numpy()[0]

    def _forward(self, epoch: np.ndarray) -> torch.Tensor:
        # EEGNet expects (batch, n_channels, n_samples)
        x = torch.from_numpy(epoch.T.astype(np.float32)).unsqueeze(0)
        with torch.no_grad():
            return self.model(x)
