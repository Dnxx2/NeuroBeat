import torch
from braindecode.models import EEGNetv4

N_CHANNELS = 8
INPUT_SAMPLES = 500    # 2 sec @ 250 Hz
N_CLASSES = 2          # 0=RELAX, 1=FOCUS  (extend as needed)


def build_model(n_classes: int = N_CLASSES, pretrained_path: str | None = None) -> EEGNetv4:
    model = EEGNetv4(
        in_chans=N_CHANNELS,
        n_classes=n_classes,
        input_window_samples=INPUT_SAMPLES,
        final_conv_length='auto',
    )
    if pretrained_path:
        state_dict = torch.load(pretrained_path, map_location='cpu')
        model_state = model.state_dict()
        # Only load layers whose shapes match — safe across different n_classes
        compatible = {k: v for k, v in state_dict.items()
                      if k in model_state and v.shape == model_state[k].shape}
        model_state.update(compatible)
        model.load_state_dict(model_state)
    return model


def freeze_backbone(model: EEGNetv4) -> None:
    """
    Freeze all layers except the final classifier.
    Use when fine-tuning from a pretrained base — faster convergence,
    less risk of overfitting on the small subject dataset.
    """
    for name, param in model.named_parameters():
        param.requires_grad = any(k in name for k in ('classifier', 'final_layer', 'softmax'))
