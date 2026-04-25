import torch
from huggingface_hub import hf_hub_download

try:
    from braindecode.models import EEGNet as EEGNetv4   # braindecode >= 1.12
except ImportError:
    from braindecode.models import EEGNetv4              # braindecode < 1.12

N_CHANNELS    = 8
INPUT_SAMPLES = 500   # 2 sec @ 250 Hz
N_CLASSES     = 2     # 0=RELAX, 1=FOCUS

HF_REPO    = 'PierreGtch/EEGNetv4'
HF_WEIGHTS = 'EEGNetv4_Lee2019_MI/model-params.pkl'


def _make_model(n_classes: int) -> EEGNetv4:
    """Instancia EEGNet con la API correcta según la versión de braindecode instalada."""
    try:
        # braindecode >= 1.12: parámetros renombrados
        return EEGNetv4(
            n_chans=N_CHANNELS,
            n_outputs=n_classes,
            n_times=INPUT_SAMPLES,
            sfreq=250,
        )
    except TypeError:
        # braindecode < 1.12: parámetros originales
        return EEGNetv4(
            in_chans=N_CHANNELS,
            n_classes=n_classes,
            input_window_samples=INPUT_SAMPLES,
            final_conv_length='auto',
        )


def _load_state_dict_partial(model: EEGNetv4, state_dict: dict) -> None:
    """Carga solo los pesos cuya forma coincide — seguro con distinto n_classes."""
    own = model.state_dict()
    compatible = {k: v for k, v in state_dict.items()
                  if k in own and v.shape == own[k].shape}
    own.update(compatible)
    model.load_state_dict(own)


def from_pretrained_hub(n_classes: int = N_CLASSES) -> EEGNetv4:
    """
    Descarga el checkpoint de Hugging Face y lo carga manualmente.
    Evita la integración hub de braindecode que falla con versiones >= 1.12.
    Primera vez: ~10 MB descargados a ~/.cache/huggingface/ (luego usa caché).
    """
    print("Descargando weights desde Hugging Face (primera vez ~10 MB, luego caché)...")
    ckpt_path = hf_hub_download(repo_id=HF_REPO, filename=HF_WEIGHTS)

    model = _make_model(n_classes)

    # model-params.pkl es un state_dict plano guardado con torch.save
    raw = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    state_dict = raw

    _load_state_dict_partial(model, state_dict)
    return model


def build_model(n_classes: int = N_CLASSES, pretrained_path: str | None = None) -> EEGNetv4:
    """
    pretrained_path: ruta a un .pt local, o None para inicialización aleatoria.
    Para pesos de Hugging Face usa from_pretrained_hub().
    """
    model = _make_model(n_classes)
    if pretrained_path:
        state_dict = torch.load(pretrained_path, map_location='cpu', weights_only=True)
        _load_state_dict_partial(model, state_dict)
    return model


def freeze_backbone(model: EEGNetv4) -> None:
    for name, param in model.named_parameters():
        param.requires_grad = any(k in name for k in ('classifier', 'final_layer', 'softmax'))
