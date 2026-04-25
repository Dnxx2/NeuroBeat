"""
gyro_mouse.py — controla el cursor del mouse con el giroscopio del Unicorn Black.

Mapping de ejes:
  GyrY (yaw,   girar cabeza izq/der) → movimiento X del cursor
  GyrX (pitch, asentir arriba/abajo) → movimiento Y del cursor
  GyrZ (roll)                        → no usado

Uso:
  python gyro_mouse.py                         # con hardware en COM5
  python gyro_mouse.py --port COM3             # otro puerto
  python gyro_mouse.py --mock                  # sin hardware
  python gyro_mouse.py --sensitivity 6 --deadzone 3

Detener: Ctrl+C  o  mover el mouse a la esquina superior izquierda (failsafe).
"""

import argparse
import math
import time

import numpy as np
import pyautogui
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

# ── Constantes del board ──────────────────────────────────────────────────────
BOARD_ID = BoardIds.UNICORN_BOARD.value
FS       = BoardShim.get_sampling_rate(BOARD_ID)          # 250 Hz
GYRO_CH  = BoardShim.get_gyro_channels(BOARD_ID)          # [11, 12, 13]: pitch, yaw, roll

# Deshabilitar el pause entre llamadas de pyautogui (default = 0.1 s, demasiado lento)
pyautogui.FAILSAFE = True   # mover mouse a esquina superior izquierda = stop de emergencia
pyautogui.PAUSE    = 0.0


class GyroMouse:
    """
    Convierte velocidad angular del giroscopio en movimiento de cursor.

    Parámetros:
      sensitivity  Factor °/s → píxeles por tick. Subir para movimientos más amplios.
      deadzone     Umbral en °/s bajo el cual se ignora la señal (filtra deriva en reposo).
      smoothing    Coeficiente EMA [0, 1]. 0 = sin suavizado, valores altos = más inercia.
      rate_hz      Frecuencia de actualización del cursor en Hz.
    """

    def __init__(self, sensitivity: float = 4.0, deadzone: float = 2.0,
                 smoothing: float = 0.35, rate_hz: float = 30.0):
        self.sensitivity = sensitivity
        self.deadzone    = deadzone
        self.alpha       = smoothing
        self.dt          = 1.0 / rate_hz
        self._vx         = 0.0   # velocidad suavizada en X
        self._vy         = 0.0   # velocidad suavizada en Y

    # ── Procesamiento de señal ────────────────────────────────────────────────

    def _deadzone(self, v: float) -> float:
        return v if abs(v) > self.deadzone else 0.0

    def step(self, gyro_pitch: float, gyro_yaw: float) -> tuple[int, int]:
        """
        Recibe una lectura de giroscopio y mueve el cursor.
        Devuelve (dx, dy) en píxeles aplicados.

        gyro_pitch: GyrX en °/s — asentir arriba/abajo  → Y del cursor
        gyro_yaw:   GyrY en °/s — girar izq/der         → X del cursor
        """
        raw_x = self._deadzone(gyro_yaw)
        raw_y = self._deadzone(gyro_pitch)

        # EMA: suaviza el jitter de alta frecuencia manteniendo la respuesta
        self._vx = self.alpha * raw_x + (1 - self.alpha) * self._vx
        self._vy = self.alpha * raw_y + (1 - self.alpha) * self._vy

        dx = int(self._vx * self.sensitivity)
        dy = int(self._vy * self.sensitivity)

        if dx != 0 or dy != 0:
            pyautogui.moveRel(dx, dy)

        return dx, dy

    # ── Loops de ejecución ────────────────────────────────────────────────────

    def run(self, board: BoardShim) -> None:
        """Loop principal con hardware — lee del buffer BrainFlow."""
        _print_header("hardware")
        samples_per_tick = max(1, int(FS * self.dt))
        try:
            while True:
                t0   = time.perf_counter()
                data = board.get_board_data(samples_per_tick)
                if data.shape[1] > 0:
                    pitch = float(data[GYRO_CH[0]].mean())
                    yaw   = float(data[GYRO_CH[1]].mean())
                    dx, dy = self.step(pitch, yaw)
                    _print_status(pitch, yaw, dx, dy)
                elapsed = time.perf_counter() - t0
                time.sleep(max(0.0, self.dt - elapsed))
        except pyautogui.FailSafeException:
            print("\nFailsafe activado — cursor en esquina superior izquierda.")
        except KeyboardInterrupt:
            print("\nDetenido.")

    def run_mock(self) -> None:
        """Loop de prueba sin hardware — genera movimiento circular sintético."""
        _print_header("mock")
        t = 0.0
        try:
            while True:
                t0    = time.perf_counter()
                pitch = math.sin(t) * 20.0   # oscila ±20 °/s
                yaw   = math.cos(t) * 20.0
                dx, dy = self.step(pitch, yaw)
                _print_status(pitch, yaw, dx, dy)
                t += self.dt * 1.5
                elapsed = time.perf_counter() - t0
                time.sleep(max(0.0, self.dt - elapsed))
        except pyautogui.FailSafeException:
            print("\nFailsafe activado.")
        except KeyboardInterrupt:
            print("\nDetenido.")


# ── Helpers de display ────────────────────────────────────────────────────────

def _print_header(mode: str) -> None:
    print(f"GyroMouse activo [{mode}]  "
          f"Detener: Ctrl+C  o  mueve el mouse a la esquina superior izquierda.\n")

def _print_status(pitch: float, yaw: float, dx: int, dy: int) -> None:
    print(f"\rpitch={pitch:+6.1f}°/s  yaw={yaw:+6.1f}°/s  "
          f"→ dx={dx:+4d}px  dy={dy:+4d}px",
          end='', flush=True)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Unicorn Black gyroscope → mouse cursor')
    parser.add_argument('--mock',
                        action='store_true',
                        help='Señal sintética — sin hardware')
    parser.add_argument('--port',
                        default='COM5',
                        help='Puerto serie del Unicorn (default: COM5)')
    parser.add_argument('--sensitivity',
                        type=float, default=4.0,
                        help='Escala °/s → píxeles (default: 4.0)')
    parser.add_argument('--deadzone',
                        type=float, default=2.0,
                        help='Umbral mínimo °/s antes de mover cursor (default: 2.0)')
    parser.add_argument('--smoothing',
                        type=float, default=0.35,
                        help='Coeficiente EMA 0-1 (default: 0.35)')
    parser.add_argument('--rate',
                        type=float, default=30.0,
                        help='Frecuencia de actualización Hz (default: 30)')
    args = parser.parse_args()

    mouse = GyroMouse(
        sensitivity=args.sensitivity,
        deadzone=args.deadzone,
        smoothing=args.smoothing,
        rate_hz=args.rate,
    )

    if args.mock:
        mouse.run_mock()
        return

    params = BrainFlowInputParams()
    params.serial_port = args.port
    board = BoardShim(BOARD_ID, params)

    try:
        board.prepare_session()
        board.start_stream()
        print(f"Unicorn conectado en {args.port}  ({FS} Hz)\n")
        mouse.run(board)
    except Exception as e:
        print(f"Error de conexión: {e}")
    finally:
        if board.is_prepared():
            board.stop_stream()
            board.release_session()
            print(f"Puerto {args.port} liberado.")


if __name__ == '__main__':
    main()
