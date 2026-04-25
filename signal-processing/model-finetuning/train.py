"""
Fine-tune EEGNet on subject-specific calibration data.

Usage:
    # Opción A — desde cero
    python train.py --data data/subject_01.npz --output models/subject_01.pt

    # Opción B — desde Hugging Face (auto-descarga, recomendado)
    python train.py --data data/subject_01.npz --output models/subject_01.pt --hub

    # Opción B — desde checkpoint local
    python train.py --data data/subject_01.npz --pretrained models/base.pt --output models/subject_01.pt
"""
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from dataset import EEGDataset
from model import build_model, from_pretrained_hub, freeze_backbone


def _val_acc(model: nn.Module, loader: DataLoader) -> float:
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for X, y in loader:
            correct += (model(X).argmax(dim=1) == y).sum().item()
            total += len(y)
    return correct / total if total else 0.0


def _save_if_best(model: nn.Module, val_acc: float, best: float, path: str) -> float:
    if val_acc > best:
        torch.save(model.state_dict(), path)
        print(f"  -> checkpoint saved  (best={val_acc:.3f})")
        return val_acc
    return best


def train(epochs_data: np.ndarray, labels: np.ndarray,
          pretrained_path: str | None = None,
          use_hub: bool = False,
          output_path: str = 'model.pt',
          phase1_epochs: int = 10,
          phase2_epochs: int = 20,
          lr: float = 1e-3,
          batch_size: int = 16,
          val_split: float = 0.2) -> None:
    """
    Two-phase fine-tuning when starting from pretrained weights:
      Phase 1 — backbone frozen, only classifier trains  (fast convergence)
      Phase 2 — all layers unfreeze with LR/10           (adapts spatial filters to subject)

    When training from scratch, both phases run with full gradients at the same LR.
    """
    dataset = EEGDataset(epochs_data, labels, augment=True)
    n_val = max(1, int(len(dataset) * val_split))
    train_ds, val_ds = random_split(dataset, [len(dataset) - n_val, n_val])
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size)

    n_classes = int(labels.max()) + 1
    use_pretrained = use_hub or pretrained_path is not None

    if use_hub:
        print("Cargando weights desde Hugging Face (primera vez ~10 MB)...")
        model = from_pretrained_hub(n_classes=n_classes)
    else:
        model = build_model(n_classes=n_classes, pretrained_path=pretrained_path)

    criterion = nn.CrossEntropyLoss()
    best_val_acc = 0.0
    n_total = phase1_epochs + phase2_epochs

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    if use_pretrained:
        freeze_backbone(model)
        print(f"\n── Fase 1/{n_total}: clasificador únicamente (backbone congelado) ──")
    else:
        print(f"\n── Entrenando desde cero ({n_total} epochs) ──")

    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=lr
    )
    for epoch in range(1, phase1_epochs + 1):
        model.train()
        for X, y in train_loader:
            optimizer.zero_grad()
            criterion(model(X), y).backward()
            optimizer.step()
        acc = _val_acc(model, val_loader)
        print(f"Epoch {epoch:3d}/{n_total}  val_acc={acc:.3f}")
        best_val_acc = _save_if_best(model, acc, best_val_acc, output_path)

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    if use_pretrained:
        print(f"\n── Fase 2/{n_total}: todas las capas, LR={lr/10:.2e} ──")
        for param in model.parameters():
            param.requires_grad = True
        optimizer = torch.optim.Adam(model.parameters(), lr=lr / 10)

    for epoch in range(phase1_epochs + 1, n_total + 1):
        model.train()
        for X, y in train_loader:
            optimizer.zero_grad()
            criterion(model(X), y).backward()
            optimizer.step()
        acc = _val_acc(model, val_loader)
        print(f"Epoch {epoch:3d}/{n_total}  val_acc={acc:.3f}")
        best_val_acc = _save_if_best(model, acc, best_val_acc, output_path)

    print(f"\nListo. Mejor val_acc: {best_val_acc:.3f}  →  {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',          required=True)
    parser.add_argument('--output',        default='model.pt')
    parser.add_argument('--hub',           action='store_true',
                        help='Auto-descarga weights de Hugging Face (recomendado)')
    parser.add_argument('--pretrained',    default=None,
                        help='Ruta local a un .pt preentrenado')
    parser.add_argument('--phase1-epochs', type=int,   default=10)
    parser.add_argument('--phase2-epochs', type=int,   default=20)
    parser.add_argument('--lr',            type=float, default=1e-3)
    parser.add_argument('--batch-size',    type=int,   default=16)
    args = parser.parse_args()

    data = np.load(args.data)
    train(data['epochs'], data['labels'],
          pretrained_path=args.pretrained,
          use_hub=args.hub,
          output_path=args.output,
          phase1_epochs=args.phase1_epochs,
          phase2_epochs=args.phase2_epochs,
          lr=args.lr,
          batch_size=args.batch_size)
