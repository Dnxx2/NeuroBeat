"""
Fine-tune EEGNet on subject-specific calibration data.

Usage:
    # From scratch
    python train.py --data data/subject_01.npz --output models/subject_01.pt

    # From pretrained weights (recommended — needs fewer epochs)
    python train.py --data data/subject_01.npz \\
                    --pretrained models/pretrained_base.pt \\
                    --output models/subject_01.pt --epochs 30
"""
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from dataset import EEGDataset
from model import build_model, freeze_backbone


def train(epochs_data: np.ndarray, labels: np.ndarray,
          pretrained_path: str | None = None,
          output_path: str = 'model.pt',
          n_epochs: int = 50,
          lr: float = 1e-3,
          batch_size: int = 16,
          val_split: float = 0.2) -> None:

    dataset = EEGDataset(epochs_data, labels, augment=True)
    n_val = max(1, int(len(dataset) * val_split))
    train_ds, val_ds = random_split(dataset, [len(dataset) - n_val, n_val])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size)

    n_classes = int(labels.max()) + 1
    model = build_model(n_classes=n_classes, pretrained_path=pretrained_path)
    if pretrained_path:
        freeze_backbone(model)

    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=lr
    )
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    for epoch in range(1, n_epochs + 1):
        model.train()
        for X, y in train_loader:
            optimizer.zero_grad()
            criterion(model(X), y).backward()
            optimizer.step()

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for X, y in val_loader:
                correct += (model(X).argmax(dim=1) == y).sum().item()
                total += len(y)
        val_acc = correct / total if total else 0.0

        print(f"Epoch {epoch:3d}/{n_epochs}  val_acc={val_acc:.3f}")
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), output_path)
            print(f"  -> checkpoint saved  (best={best_val_acc:.3f})")

    print(f"\nDone. Best val accuracy: {best_val_acc:.3f}  Saved to: {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',       required=True)
    parser.add_argument('--pretrained', default=None)
    parser.add_argument('--output',     default='model.pt')
    parser.add_argument('--epochs',     type=int,   default=50)
    parser.add_argument('--lr',         type=float, default=1e-3)
    parser.add_argument('--batch-size', type=int,   default=16)
    args = parser.parse_args()

    data = np.load(args.data)
    train(data['epochs'], data['labels'],
          pretrained_path=args.pretrained,
          output_path=args.output,
          n_epochs=args.epochs,
          lr=args.lr,
          batch_size=args.batch_size)
