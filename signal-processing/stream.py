"""
Combined EEG streamer — corre ambos pipelines en paralelo y envía todo a Unity por UDP.

Paquete UDP cada ~250 ms:
{
  "focus":      0.73,   ← EEGNet fine-tuneado  (float 0-1)
  "alpha":      0.41,   ← bandpower alpha frontal normalizado (float 0-1)
  "beta":       0.62,   ← bandpower beta  frontal normalizado (float 0-1)
  "theta":      0.18,   ← bandpower theta frontal normalizado (float 0-1)
  "engagement": 0.60,   ← beta/(alpha+beta), índice DSP de concentración (float 0-1)
  "accel_x":    0.02,   ← acelerómetro X (mg), pass-through sin filtro
  "accel_y":   -0.01,   ← acelerómetro Y (mg)
  "accel_z": 1001.3,    ← acelerómetro Z (mg, ~1000 = 1g en reposo)
  "gyro_x":    -0.5,    ← giroscopio X (°/s)
  "gyro_y":     1.2,    ← giroscopio Y (°/s)
  "gyro_z":     0.3     ← giroscopio Z (°/s)
}

Frame UnicornPy (17 canales):
  [0:8]   EEG    FZ C3 CZ C4 PZ PO7 OZ PO8  (µV)
  [8:11]  Accel  AccX AccY AccZ               (mg)
  [11:14] Gyro   GyrX GyrY GyrZ               (°/s)
  [14:17] Misc   Battery Counter Validation   (ignorados)

Usage:
    python stream.py --model model-finetuning/models/subject_01.pt
    python stream.py --model model-finetuning/models/subject_01.pt --calibration manual-filtering/calibration.npz
    python stream.py --model model-finetuning/models/subject_01.pt --mock
"""

import argparse
import json
import queue
import socket
import sys
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np

# Ambas carpetas usan imports relativos sin paquete — añadir ambas al path
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / 'manual-filtering'))
sys.path.insert(0, str(_HERE / 'model-finetuning'))
sys.path.insert(0, str(_HERE.parent))

from pipeline import EEGPipeline          # manual-filtering/pipeline.py
from realtime import RealtimeProcessor    # manual-filtering/realtime.py
from features import extract_features, BANDS, BAND_NAMES, FRONTAL_IDX
from predict  import EEGClassifier        # model-finetuning/predict.py

FS        = 250
N_CH      = 8    # canales EEG
N_FRAME   = 17   # frame completo UnicornPy: 8 EEG + 3 accel + 3 gyro + 3 misc
N_BANDS   = len(BANDS)
ALPHA_I   = BAND_NAMES.index('alpha')
BETA_I    = BAND_NAMES.index('beta')
THETA_I   = BAND_NAMES.index('theta')


def _band_scores(window: np.ndarray) -> dict:
    """window: (500, 8) limpio y normalizado → dict con scores 0-1."""
    feats = extract_features(window)
    alpha = float(np.mean([feats[ch * N_BANDS + ALPHA_I] for ch in FRONTAL_IDX]))
    beta  = float(np.mean([feats[ch * N_BANDS + BETA_I]  for ch in FRONTAL_IDX]))
    theta = float(np.mean([feats[ch * N_BANDS + THETA_I] for ch in FRONTAL_IDX]))
    total = alpha + beta + theta + 1e-9
    return {
        'alpha':      round(alpha / total, 3),
        'beta':       round(beta  / total, 3),
        'theta':      round(theta / total, 3),
        'engagement': round(beta / (alpha + beta + 1e-9), 3),
    }


class CombinedStreamer:
    """
    Arquitectura de threads:
      Adquisición  →  fan-out  →  Thread manual  ─┐
                              →  Thread model   ─┤→  results dict  →  Thread sender → UDP
    """

    def __init__(self, model_path: str, calibration_path: str | None = None,
                 host: str = '127.0.0.1', port: int = 5005):
        self.host = host
        self.port = port

        # Colas de fan-out — si un worker está atrasado se descartan muestras
        self._manual_q = queue.Queue(maxsize=100)
        self._model_q  = queue.Queue(maxsize=100)

        # Resultados compartidos entre threads
        self._results  = {
            'focus': 0.0, 'alpha': 0.0, 'beta': 0.0,
            'theta': 0.0, 'engagement': 0.0,
            'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 0.0,
            'gyro_x':  0.0, 'gyro_y':  0.0, 'gyro_z':  0.0,
        }
        self._lock     = threading.Lock()
        self._running  = False

        # Pipeline manual
        manual_pipe = EEGPipeline(fs=FS, use_ica=False)
        if calibration_path:
            manual_pipe.load_calibration(calibration_path)
        self._manual_proc = RealtimeProcessor(pipeline=manual_pipe)

        # Pipeline modelo
        self._clf = EEGClassifier(model_path)

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # ── Workers ───────────────────────────────────────────────────────────────

    def _manual_worker(self) -> None:
        while self._running:
            try:
                sample = self._manual_q.get(timeout=0.1)
                window = self._manual_proc.push(sample)
                if window is not None:
                    with self._lock:
                        self._results.update(_band_scores(window))
            except queue.Empty:
                continue

    def _model_worker(self) -> None:
        buf  = deque(maxlen=500)
        tick = 0
        while self._running:
            try:
                sample = self._model_q.get(timeout=0.1)
                buf.append(sample)
                tick += 1
                if len(buf) == 500 and tick % 62 == 0:
                    raw_score = self._clf.focus_score(np.array(buf) * 25000.0)
                    prob_parpadeo = 1.0 - raw_score
                    if prob_parpadeo > 0.7:
                        score_filtrado = 1.0
                    else:
                        score_filtrado = prob_parpadeo
                    with self._lock:
                        self._results['focus'] = score_filtrado
            except queue.Empty:
                continue

    def _sender_worker(self) -> None:
        while self._running:
            with self._lock:
                payload = dict(self._results)
            self._sock.sendto(json.dumps(payload).encode(), (self.host, self.port))
            f = payload['focus']
            print(f"\rfocus={f:.2f} [{'█'*int(f*20):<20}] "
                  f"α={payload['alpha']:.2f} β={payload['beta']:.2f} "
                  f"eng={payload['engagement']:.2f}  "
                  f"acc=({payload['accel_x']:+.0f},{payload['accel_y']:+.0f},{payload['accel_z']:+.0f}) "
                  f"gyr=({payload['gyro_x']:+.1f},{payload['gyro_y']:+.1f},{payload['gyro_z']:+.1f})",
                  end='', flush=True)
            time.sleep(0.25)

    # ── API pública ───────────────────────────────────────────────────────────

    def start(self, get_sample_fn) -> None:
        """
        Inicia todos los threads y entra al loop de adquisición.
        get_sample_fn: callable sin argumentos → ndarray (N_CH,)
        Detener con Ctrl+C.
        """
        self._running = True
        for target, name in [(self._manual_worker, 'manual'),
                             (self._model_worker,  'model'),
                             (self._sender_worker, 'sender')]:
            threading.Thread(target=target, daemon=True, name=name).start()

        print(f"Streaming → udp://{self.host}:{self.port}  (Ctrl+C para detener)\n")
        try:
            while True:
                frame = get_sample_fn()       # (17,): EEG[0:8] accel[8:11] gyro[11:14] misc[14:17]
                eeg_sample = frame[:N_CH]     # (8,) para los workers de EEG
                # IMU pasa directo al resultado — sin filtro, actualización por muestra
                with self._lock:
                    self._results['accel_x'] = round(float(frame[8]),  2)
                    self._results['accel_y'] = round(float(frame[9]),  2)
                    self._results['accel_z'] = round(float(frame[10]), 2)
                    self._results['gyro_x']  = round(float(frame[11]), 2)
                    self._results['gyro_y']  = round(float(frame[12]), 2)
                    self._results['gyro_z']  = round(float(frame[13]), 2)
                for q in (self._manual_q, self._model_q):
                    try:
                        q.put_nowait(eeg_sample)
                    except queue.Full:
                        pass
        except KeyboardInterrupt:
            self._running = False
            print("\nDetenido.")
        finally:
            self._sock.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Combined EEG streamer → Unity UDP')
    parser.add_argument('--model',       required=True,
                        help='Ruta al modelo entrenado, ej. model-finetuning/models/subject_01.pt')
    parser.add_argument('--calibration', default=None,
                        help='(Opcional) calibration.npz del clasificador manual')
    parser.add_argument('--host',        default='127.0.0.1')
    parser.add_argument('--port',        type=int, default=5005)
    parser.add_argument('--mock',        action='store_true',
                        help='Señal sintética — sin hardware')
    args = parser.parse_args()

    if args.mock:
        rng = np.random.default_rng(0)
        def get_sample():
            eeg   = (rng.standard_normal(N_CH) * 50e-6).astype(np.float32)
            accel = (rng.standard_normal(3) * 30 + [0, 0, 1000]).astype(np.float32)
            gyro  = (rng.standard_normal(3) * 3).astype(np.float32)
            misc  = np.zeros(3, dtype=np.float32)
            return np.concatenate([eeg, accel, gyro, misc])
    else:
        try:
            from api.Lib import UnicornPy
        except ImportError:
            from api.Lib import UnicornPy
        devices = UnicornPy.GetAvailableDevices(True)
        if not devices:
            raise RuntimeError("No se encontró ningún Unicorn Black conectado.")
        unicorn = UnicornPy.Unicorn(devices[0])
        numberOfAcquiredChannels  = unicorn.GetNumberOfAcquiredChannels()
        receiveBufferBufferLength = numberOfAcquiredChannels * 4  # FrameLength=1
        receiveBuffer             = bytearray(receiveBufferBufferLength)
        unicorn.StartAcquisition(True)
        def get_sample():
            unicorn.GetData(1, receiveBuffer, receiveBufferBufferLength)
            return np.frombuffer(receiveBuffer, dtype=np.float32).copy()

    CombinedStreamer(
        model_path=args.model,
        calibration_path=args.calibration,
        host=args.host,
        port=args.port,
    ).start(get_sample)
