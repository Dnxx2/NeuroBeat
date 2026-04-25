"""
gyro_mouse.py — cursor del mouse via giroscopio + click via concentración EEG.

Fuente de datos: paquete UDP de signal-processing/stream.py (puerto 5005).
  gyro_x / gyro_y  → movimiento del cursor (pitch / yaw de la cabeza)
  focus            → click izquierdo cuando la concentración supera el umbral

Lógica de click (Schmitt trigger + confirmación):
  1. focus debe superar el umbral durante N paquetes consecutivos → click
  2. Después del click, focus debe bajar de (umbral - histéresis) para re-armarse
  Esto filtra picos de ruido y requiere una desconcentración real entre clicks.

Uso:
  # Requiere stream.py corriendo en otra terminal:
  cd signal-processing
  python stream.py --model model-finetuning/models/subject_01.pt [--mock]

  # Luego en otra terminal:
  python control/gyro_mouse.py

  # Sin hardware ni stream (todo sintético):
  python control/gyro_mouse.py --mock

Detener: Ctrl+C  o  mover el mouse a la esquina superior izquierda (failsafe).
"""

import argparse
import json
import math
import socket
import threading
import time

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.0

STREAM_PORT = 5005


# ── Click controller ──────────────────────────────────────────────────────────

class ClickController:
    """
    Schmitt trigger para disparar un click por concentración sostenida.

    Estados:
      ARMED  → contando paquetes sobre upper_threshold
               cuando llega a confirm_n → CLICK y pasa a WAITING
      WAITING → el jugador debe bajar focus por debajo de lower_threshold
                para re-armarse (ARMED)

    Esto asegura que:
      - Ruido de un solo paquete no dispara click (necesita confirm_n consecutivos)
      - No hay clicks múltiples sin desconcentración real de por medio
    """

    def __init__(self, threshold: float = 0.70, hysteresis: float = 0.25,
                 confirm_n: int = 3):
        self.upper     = threshold
        self.lower     = threshold - hysteresis   # punto de re-armado
        self.confirm_n = confirm_n
        self._count    = 0
        self._armed    = True

    @property
    def armed(self) -> bool:
        return self._armed

    @property
    def count(self) -> int:
        return self._count

    def update(self, focus: float) -> bool:
        """
        Procesa un valor de focus.
        Devuelve True exactamente el frame en que se dispara el click.
        """
        if not self._armed:
            # Esperando que baje para re-armarse
            if focus < self.lower:
                self._armed = True
                self._count = 0
            return False

        if focus >= self.upper:
            self._count += 1
            if self._count >= self.confirm_n:
                self._armed = False
                self._count = 0
                return True          # CLICK
        else:
            self._count = 0         # reset si baja antes de confirmar

        return False


# ── Gyro mouse ────────────────────────────────────────────────────────────────

class GyroMouse:
    """
    Controla el cursor con el giroscopio y hace click por concentración EEG.
    Lee ambas señales del paquete UDP emitido por signal-processing/stream.py.
    Comparte el puerto con Unity usando SO_REUSEADDR — ambos reciben el mismo datagrama.
    """

    def __init__(self, sensitivity: float = 1.0, deadzone: float = 2.0,
                 smoothing: float = 0.35, rate_hz: float = 30.0,
                 threshold: float = 0.70, hysteresis: float = 0.25,
                 confirm_n: int = 3):
        self.sensitivity = sensitivity
        self.deadzone    = deadzone
        self.alpha       = smoothing
        self.dt          = 1.0 / rate_hz
        self._vx         = 0.0
        self._vy         = 0.0
        self._clicker    = ClickController(threshold, hysteresis, confirm_n)
        self._latest: dict = {}
        self._lock       = threading.Lock()
        self._running    = False

    # ── Movimiento ────────────────────────────────────────────────────────────

    def _apply_deadzone(self, v: float) -> float:
        return v if abs(v) > self.deadzone else 0.0

    def _move(self, gyro_pitch: float, gyro_yaw: float) -> tuple[int, int]:
        """EMA + deadzone → moveRel. Devuelve (dx, dy) en píxeles."""
        raw_x = self._apply_deadzone(gyro_yaw)    # yaw   → X del cursor
        raw_y = self._apply_deadzone(gyro_pitch)  # pitch → Y del cursor
        self._vx = self.alpha * raw_x + (1 - self.alpha) * self._vx
        self._vy = self.alpha * raw_y + (1 - self.alpha) * self._vy
        dx = -int(self._vx * self.sensitivity)
        dy = -int(self._vy * self.sensitivity)
        if dx != 0 or dy != 0:
            pyautogui.moveRel(dx, dy)
        return dx, dy

    # ── Recepción UDP ─────────────────────────────────────────────────────────

    def _udp_listener(self, port: int) -> None:
        """Thread background: recibe paquetes de stream.py."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', port))
        sock.settimeout(0.5)
        while self._running:
            try:
                data, _ = sock.recvfrom(2048)
                with self._lock:
                    self._latest = json.loads(data.decode())
            except socket.timeout:
                continue
            except Exception:
                pass
        sock.close()

    # ── Display ───────────────────────────────────────────────────────────────

    def _print_status(self, focus: float, dx: int, dy: int, clicked: bool) -> None:
        bar    = '#' * int(focus * 15)
        n      = self._clicker.confirm_n
        count  = self._clicker.count
        state  = f'arm [{count}/{n}]' if self._clicker.armed else 'wait'
        marker = '  *** CLICK ***' if clicked else ''
        print(f"\rfocus={focus:.2f} [{bar:<15}] {state}  "
              f"dx={dx:+4d} dy={dy:+4d}{marker}",
              end='', flush=True)

    # ── Loops principales ─────────────────────────────────────────────────────

    def run(self, port: int = STREAM_PORT) -> None:
        """Escucha stream.py en `port` y controla cursor + click."""
        print(f"GyroMouse activo [stream udp:{port}]")
        print(f"  umbral click: focus > {self._clicker.upper:.2f} "
              f"durante {self._clicker.confirm_n} paquetes "
              f"({self._clicker.confirm_n * 0.25:.2f}s)")
        print(f"  re-armar en: focus < {self._clicker.lower:.2f}")
        print("Detener: Ctrl+C  o  mueve el mouse a la esquina superior izquierda.\n")

        self._running = True
        threading.Thread(target=self._udp_listener, args=(port,),
                         daemon=True, name='udp-listener').start()

        try:
            while True:
                t0 = time.perf_counter()
                with self._lock:
                    pkt = dict(self._latest)

                if pkt:
                    dx, dy   = self._move(pkt.get('gyro_x', 0.0),
                                          pkt.get('gyro_y', 0.0))
                    focus    = float(pkt.get('focus', 0.0))
                    do_click = self._clicker.update(focus)
                    if do_click:
                        pyautogui.click()
                    self._print_status(focus, dx, dy, do_click)

                elapsed = time.perf_counter() - t0
                time.sleep(max(0.0, self.dt - elapsed))
        except pyautogui.FailSafeException:
            print("\nFailsafe activado — cursor en esquina superior izquierda.")
        except KeyboardInterrupt:
            print("\nDetenido.")
        finally:
            self._running = False

    def run_mock(self) -> None:
        """Sin hardware ni stream — giroscopio circular + foco pulsante sintético."""
        print("GyroMouse activo [mock]")
        print(f"  umbral click: focus > {self._clicker.upper:.2f} "
              f"durante {self._clicker.confirm_n} paquetes")
        print("Detener: Ctrl+C  o  mueve el mouse a la esquina superior izquierda.\n")
        t = 0.0
        try:
            while True:
                t0    = time.perf_counter()
                pitch = math.sin(t) * 20.0
                yaw   = math.cos(t) * 20.0
                # focus sube lentamente de 0 a 1 y vuelve a bajar — simula concentración
                focus = (math.sin(t * 0.3) + 1) / 2
                dx, dy   = self._move(pitch, yaw)
                do_click = self._clicker.update(focus)
                if do_click:
                    pyautogui.click()
                self._print_status(focus, dx, dy, do_click)
                t += self.dt * 1.5
                elapsed = time.perf_counter() - t0
                time.sleep(max(0.0, self.dt - elapsed))
        except pyautogui.FailSafeException:
            print("\nFailsafe activado.")
        except KeyboardInterrupt:
            print("\nDetenido.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Unicorn Black gyroscope + EEG focus → mouse cursor + click')
    parser.add_argument('--mock',
                        action='store_true',
                        help='Señal sintética — sin hardware ni stream.py')
    parser.add_argument('--port',
                        type=int, default=STREAM_PORT,
                        help=f'Puerto UDP de stream.py (default: {STREAM_PORT})')
    parser.add_argument('--sensitivity',
                        type=float, default=4.0,
                        help='Escala °/s → píxeles (default: 4.0)')
    parser.add_argument('--deadzone',
                        type=float, default=2.0,
                        help='Umbral mínimo °/s para mover cursor (default: 2.0)')
    parser.add_argument('--smoothing',
                        type=float, default=0.35,
                        help='Coeficiente EMA movimiento 0-1 (default: 0.35)')
    parser.add_argument('--rate',
                        type=float, default=30.0,
                        help='Frecuencia de actualización Hz (default: 30)')
    parser.add_argument('--threshold',
                        type=float, default=0.70,
                        help='Focus mínimo para disparar click (default: 0.70)')
    parser.add_argument('--hysteresis',
                        type=float, default=0.25,
                        help='Cuánto debe bajar focus tras click para re-armarse (default: 0.25)')
    parser.add_argument('--confirm',
                        type=int, default=3,
                        help='Paquetes consecutivos sobre umbral antes de click (default: 3 = 0.75s)')
    args = parser.parse_args()

    mouse = GyroMouse(
        sensitivity=args.sensitivity,
        deadzone=args.deadzone,
        smoothing=args.smoothing,
        rate_hz=args.rate,
        threshold=args.threshold,
        hysteresis=args.hysteresis,
        confirm_n=args.confirm,
    )

    if args.mock:
        mouse.run_mock()
    else:
        mouse.run(port=args.port)


if __name__ == '__main__':
    main()
