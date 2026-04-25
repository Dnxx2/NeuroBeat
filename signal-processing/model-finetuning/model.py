import torch
from braindecode.models import EEGNetv4

N_CHANNELS = 8
INPUT_SAMPLES = 500    # 2 sec @ 250 Hz
N_CLASSES = 2          # 0=RELAX, 1=FOCUS  (extend as needed)

# Public pretrained checkpoint (Motor Imagery, Lee 2019, 2-class)
# Auto-downloaded from Hugging Face on first use — no manual download needed.
HF_REPO = 'PierreGtch/EEGNetv4'
HF_WEIGHTS = 'EEGNetv4_Lee2019_MI.ckpt'


def build_model(n_classes: int = N_CLASSES, pretrained_path: str | None = None) -> EEGNetv4:
    """
    pretrained_path: local .pt file path, or None for random init.
    For Hugging Face weights, use from_pretrained_hub() instead.
    """
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


def from_pretrained_hub(n_classes: int = N_CLASSES) -> EEGNetv4:
    """
    Downloads EEGNetv4 pretrained on Motor Imagery (Lee 2019) from Hugging Face.
    Requires: pip install braindecode[hub]
    First call downloads ~10 MB and caches in ~/.cache/huggingface/
    """
    model = EEGNetv4.from_pretrained(
        HF_REPO,
        sfreq=250,
        n_chans=N_CHANNELS,
        n_outputs=n_classes,
        weights_filename=HF_WEIGHTS,
    )
    return model


def freeze_backbone(model: EEGNetv4) -> None:
    """
    Freeze all layers except the final classifier.
    Use when fine-tuning from a pretrained base — faster convergence,
    less risk of overfitting on the small subject dataset.
    """
    for name, param in model.named_parameters():
        param.requires_grad = any(k in name for k in ('classifier', 'final_layer', 'softmax'))
