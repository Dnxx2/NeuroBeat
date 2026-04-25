"""
2-minute subject calibration session.

Alternates RELAX / FOCUS blocks, saves labelled epochs as .npz for fine-tuning.

Usage:
    python calibrate.py --output data/subject_01.npz          # real hardware
    python calibrate.py --output data/subject_01.npz --mock   # no device needed
"""
import argparse
import time
from pathlib import Path
import numpy as np



FrameLength = 1          # 1 muestra por llamada → 250 samples/s, sin pérdida de datos
FS = 250
N_CHANNELS = 8
EPOCH_SAMPLES = 500    # 2 sec @ 250 Hz
EPOCH_STEP    = 125    # 50 % overlap
BLOCK_SEC = 30         # 30 s per class × 2 classes × 2 rounds = 2 min
N_ROUNDS  = 2
CLASSES = {0: 'RELAX', 1: 'FOCUS'}


def record_block(label_id: int, duration_sec: int, get_sample) -> np.ndarray:
    cue = "Cierra los ojos, respira profundo" if label_id == 0 \
          else "Concéntrate — cuenta mentalmente de 3 en 3"
    print(f"\n[{CLASSES[label_id]}]  {cue}")
    print(f"  Grabando {duration_sec}s... ", end='', flush=True)

    samples = []
    deadline = time.time() + duration_sec
    while time.time() < deadline:
        samples.append(get_sample())

    print("listo.")
    return np.array(samples, dtype=np.float32)   # (n_samples, N_CHANNELS)


def segment(recording: np.ndarray) -> np.ndarray:
    epochs = []
    for start in range(0, len(recording) - EPOCH_SAMPLES + 1, EPOCH_STEP):
        epochs.append(recording[start:start + EPOCH_SAMPLES])
    return np.array(epochs)


def run_calibration(get_sample, output_path: str) -> None:
    all_epochs, all_labels = [], []

    for round_i in range(N_ROUNDS):
        print(f"\n=== Ronda {round_i + 1}/{N_ROUNDS} ===")
        for label_id in CLASSES:
            rec    = record_block(label_id, BLOCK_SEC, get_sample)
            epochs = segment(rec)
            all_epochs.append(epochs)
            all_labels.append(np.full(len(epochs), label_id, dtype=np.int64))
            if not (round_i == N_ROUNDS - 1 and label_id == max(CLASSES)):
                # Drenar el buffer durante el descanso — si se hace time.sleep() el buffer
                # interno del Unicorn se llena (250 Hz × 5 s = 1250 muestras) y la
                # siguiente llamada a GetData lanza UNICORN_ERROR_BUFFER_OVERFLOW.
                print("  Descansa 5 s...")
                drain_end = time.time() + 5
                while time.time() < drain_end:
                    get_sample()

    epochs_arr = np.concatenate(all_epochs)
    labels_arr = np.concatenate(all_labels)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, epochs=epochs_arr, labels=labels_arr)
    dist = np.bincount(labels_arr)
    print(f"\nGuardado en '{output_path}'")
    print(f"Total epochs: {len(labels_arr)}  |  " +
          "  ".join(f"{CLASSES[i]}={dist[i]}" for i in range(len(dist))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data/calibration.npz')
    parser.add_argument('--mock', action='store_true',
                        help='Signal sintética — no necesita hardware')
    args = parser.parse_args()

    if args.mock:
        rng = np.random.default_rng(0)
        get_sample = lambda: rng.standard_normal(N_CHANNELS).astype(np.float32) * 50e-6
    else:
        try:
            from api.Lib import UnicornPy
            devices = UnicornPy.GetAvailableDevices(True)
            if not devices:
                raise RuntimeError("No se encontró ningún Unicorn Black.")
            unicorn = UnicornPy.Unicorn(devices[0])
            numberOfAcquiredChannels = unicorn.GetNumberOfAcquiredChannels()
            receiveBufferBufferLength = FrameLength * numberOfAcquiredChannels * 4
            receiveBuffer = bytearray(receiveBufferBufferLength)
            unicorn.StartAcquisition(True)

            def get_sample():
                unicorn.GetData(FrameLength, receiveBuffer, receiveBufferBufferLength)
                # frombuffer parsea los bytes como float32; con FrameLength=1 hay
                # exactamente numberOfAcquiredChannels valores (17 para el Unicorn Black)
                data = np.frombuffer(receiveBuffer, dtype=np.float32)
                return data[:N_CHANNELS].copy()

        except Exception as exc:
            print(f"Error de hardware: {exc}")
            print("Usa --mock para probar sin dispositivo.")
            raise

    run_calibration(get_sample, args.output)